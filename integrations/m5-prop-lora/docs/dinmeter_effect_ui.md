# DinMeter effect-mechanics UI — spec (converged from 3 council rounds, unanimous GO)

The DinMeter (rectangular 240x135 ST7789, one rotary encoder + one side button, battery,
drives 4 WS2812 LEDs / Unit Puzzle) is the prop receiver. It **edits + stores + executes** the
LED EFFECT MECHANICS (the brightness-over-time animation played when a FIRE command arrives).

## Ownership
- **Dial** owns per-LED COLOUR + master BRIGHTNESS and ARM/FIRE. Over LoRa it sends only
  fire / colour / brightness. It never edits effect timing. (It may later display the effect
  version/checksum to detect mismatch — out of scope for this MVP.)
- **DinMeter == the prop here**: it edits the effect, persists it locally (NVS), and executes
  it on FIRE using the Dial's last-sent colour + brightness as the amplitude/colour.

## Effect model (REPLACES the old fadeInMs/holdMs/fadeOutMs envelope)
```
struct EffectConfig {
    bool     preTrigger;     // false = dark until fire (DEFAULT); true = GLOW (~10% of cached brightness)
    uint8_t  shape;          // 0 = SINE2 (only shape in MVP; byte reserved for full-sine/strobe later)
    uint16_t periodMs;       // duration of ONE hump, 100..5000
    uint8_t  repeat;         // 1..32, or 0 = INF (ends on disarm / next fire)
    uint16_t ledDelayMs[4];  // per-LED start stagger; default {0, 80, 160, 240} = chase
};
```
- Brightness of one hump at local time t in [0,periodMs):  `B(t) = sin^2(pi * t / periodMs)`
  i.e. `(1 - cos(2*pi*t/periodMs)) / 2`. Always in [0,1], zero slope at both ends (smooth joins,
  no flicker). Multiply by the Dial-cached colour*brightness.
- Per LED i, the effect starts at `ledDelayMs[i]`, plays `repeat` humps back to back.
- `total = max(ledDelayMs) + repeat * periodMs` (INF: no finite total).
- GLOW (preTrigger=true): before fire, LEDs sit at ~10% of cached brightness in their colour.
  Default preTrigger=false (dark until fire — the trigger is the drama, saves battery).

## Layout (240 x 135, rectangular — NOT the Dial's round look)
- **Top status bar (~16 px):** left = state (IDLE / ARMED / FIRING) + a small staged/SAVED
  indicator; right = **battery** (outline + fill bar + %, green >40 / amber 20-40 / red <20).
- **Live curve plot (full width, middle ~70 px):** draws the sin^2 humps x repeat over the time
  axis; per-LED offsets shown as small coloured tick marks on the X axis; a vertical PLAYHEAD
  sweeps during preview. Small "Total: 1.2s" readout in a corner (or "inf"). For repeat=INF draw
  ~8 humps then a "..inf" ellipsis. DIFF-RENDER: only redraw the plot + the changed row, not the
  whole screen every encoder tick.
- **Parameter rows (bottom, scrolling):** one row per field, selected row highlighted (inverted),
  value right-aligned. Rows: Pre, Period, Repeat, LED delays (-> sub-view), [Preview].
- **Per-LED offsets:** push-in SUB-VIEW with a mini timeline of L1..L4 and their offsets; encoder
  long-press / side-button exits back.
- **4-LED dots:** small indicators that animate brightness during preview.

## Navigation
- Encoder ROTATE = move selection through rows (wraps).
- Encoder PUSH = enter edit on the selected row (row inverts); ROTATE changes the value (with
  acceleration for periodMs); PUSH again confirms.
- Confirm = stage -> apply -> **atomic NVS save** (show brief "SAVED" in status bar). Edits while
  ARMED are not applied to a running effect; they apply to the next FIRE (define ACK/feedback).
- SIDE BUTTON (short) = LIVE PREVIEW: play the effect on the real LEDs now + sweep the plot
  playhead. Preview is VOLATILE (RAM only, no NVS write — protects flash from preview spam).
  Uses the cached Dial colour+brightness; if none yet, dim neutral WHITE (labelled, not saved).
  Rate-limit ~500 ms; disable preview if battery < 10%.
- SIDE BUTTON (long) = back / exit sub-view.

## Persistence
- Stage edits while browsing -> apply on confirm -> atomic NVS (ESP32 Preferences) write.
- Show staged-vs-saved clearly in the status bar. Config survives power-cycle.

## Implementation notes
- All LovyanGFX primitives (fillRect, drawRect, drawLine/drawFastVLine, fillCircle, drawString).
- Curve: sample x in plot width, y = baseline - B(t)*plotHeight; drawFastVLine fill or polyline.
- Keep redraws < 16 ms via dirty-region rendering.
- This refactors the existing prop_rx.cpp EffectSettings/LedTiming/UiField. Keep the LoRa frame
  handling (Preview/Fire/Stop/Ping) and the Adafruit_NeoPixel output path; only the effect curve
  math, the config struct, and the on-screen UI change.
