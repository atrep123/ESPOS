# M5 Dial — Control Architecture (Prop LoRa Controller)

Decided with Filip after the multi-model control-clarity council (Gemini, Codex,
Opus, Copilot 4.6, Copilot 5.5). This is the agreed control model + how it
resolves the council's findings.

## 1. Hardware inputs
- **Rotary encoder** — `ROTATE` (relative) + `PRESS` (click).
- **BACK button** (side) — mode toggle / cancel.
- **Dedicated FIRE button / Chain Key** — M5Stack Chain Key on Port B via
  UART/M5Chain, physically separate, *only* for ODPAL/fire. Source routing is
  implemented and covered by tests; on-device Chain Key detection and press
  acceptance are **VERIFY ON DEVICE**.
- Touchscreen exists but is **secondary** (must be fully operable without it —
  this fixes the council's P0 "send is touch-only").

## 2. Control grammar (Dial fire controller)
Setup editing has moved to the M5StickS3 Terminal. Dial input is now limited to
radio fire-control actions and must not edit lane color, brightness/normal
on-off state, or fire-change participation.

| Input | Ready / command state | When ARMED |
|-------|-----------------------|------------|
| ROTATE | scroll action (PREVIEW/PING/STOP/ARM) | ignored (locked) |
| PRESS | **send** selected action -> sending -> ACK | ignored (locked) |
| BACK | show `SETUP NA TERMINALU` / cancel transient state | **cancel / disarm** |
| FIRE button | locked until ARM | **fire** -> sending -> ACK |

Press now *means* something per mode — the core P0 fix (`PRESS` in COMMAND must
call `_run_selected_action()`, not `_next_field()`).

## 3. Dial mode model
- **COMMAND only** — central hollow transmit ring + action label; left/right
  chevrons = rotate to scroll actions. PRESS sends the selected action.
- **Setup handoff** — BACK/long setup gestures do not open a Dial editor. They
  report `SETUP NA TERMINALU` and leave the fire-control state unchanged.
- **Terminal owns setup editing** — five physical Terminal lanes control named
  palette color, brightness/normal on-off state, and fire-change participation
  over the USB setup link.

## 4. Fire safety flow (2-factor: software ARM + hardware FIRE button)
1. In COMMAND, rotate to **ARM**, PRESS → **ARMED**:
   - the dedicated **FIRE button unlocks**,
   - UI shows an **armed indicator + countdown** of the arm window (≈10 s),
   - navigation is **hard-locked** (rotate/press ignored), **BACK = cancel/disarm**.
2. Press the **FIRE button** → UI immediately shows **"ODESÍLÁM"** (visible proof
   it registered + is sending) → **"POTVRZENO"** on ACK (or **"NO ACK"** on timeout).
   No extra confirm step (auto).
3. Window expires with no fire → **auto-disarm**, FIRE button re-locks.

This kills three council P0/P1s at once: accidental fire (2-factor + separate
button), invisible ARM→FIRE (explicit armed state + countdown + "FIRE live" cue),
and the **red-ring overload** — *armed is now its own button-unlocked state with a
countdown, so RED is freed to mean ERROR only.*

## 5. Minimal-but-common-sense UI (the clarity/cleanliness compromise)
No persistent caption text; instead the minimal design is made self-evident:
- **Mode cue:** hollow transmit ring + chevrons = a radio action you pick and
  send. There is no Dial setup editor state.
- **Setup handoff:** brief `SETUP NA TERMINALU` token when the operator tries to
  enter setup on Dial.
- **Selection:** bottom LED dots are indication only, derived from receiver or
  runtime state, not a local setup editor.
- **State:** outer-ring **colour only** (green ready / amber waiting / red error)
  plus a **brief transient token** on change (`✓ ACK`, `NO ACK`, `ODESÍLÁM`) that
  fades — informative without permanent clutter. (Fixes "status computed but never
  drawn".)
- **Affordances:** chevrons in COMMAND; when ARMED, a clear "**FIRE ready**" cue +
  countdown so the live physical button is obvious; `◀` back-hint shown only when
  back does something non-obvious (e.g. `◀ CANCEL` while armed).

## 6. State / status model
- Ring colour = link/op state. ARMED is the countdown/armed-cue state (not red
  ring) → RED = error/no-ack only (no ambiguity).
- The firmware already computes `status`; draw it **transiently** (top, fades),
  never as a permanent label.
- `KEY MISSING` is a safe boot/runtime state: C++ Dial/DinMeter authenticated
  frames require the runtime HMAC key in `prop_key/shared`; missing or mismatched
  key material must fail closed before ARM/FIRE can be accepted. This is the HMAC
  runtime-key diagnostic, separate from the physical Chain Key diagnostic
  `FIRE KEY MISSING`.

## 7. Firmware mapping (`app_prop_tx.cpp` / `gui_prop_tx.cpp`)
- **Encoder PRESS:** branch by mode — COMMAND → `_run_selected_action()`; SETUP →
  `_next_field()`. Keep this covered by tests because the old P0 bug routed every
  press to `_next_field()`.
- **BACK:** toggle SETUP↔COMMAND; when armed → cancel/disarm.
- **Chain Key (Port B UART/M5Chain):** handler active only when `armed` → fire →
  UI sending → ACK; otherwise ignored/fail-safe.
- **ARM action:** set armed, unlock FIRE button, start countdown, hard-lock nav;
  force the armed screen to read **ODPAL** (fix: ARM must set the fire target).
- Make `is_command_mode()` / input routing **respect `armed`** (hard lock).
- **Draw `status`** transiently; auto-disarm on window expiry.
- JAS orb uses the channel colour; brightness value lives in the orb + ring.

## 8. ESPOS widget implications (designer parity)
- `transmit_ring`: add an **armed/FIRE-live** treatment distinct from error.
- `orb`: consistent channel colour; unit-based field cue.
- `state_ring`: ERROR pattern can stay plain red (armed no longer competes).
- New small **status-token** element (transient).

## 9. Council findings → resolution
| Council finding (severity) | Resolved by |
|---|---|
| P0 PRESS doesn't send (Opus/Codex) | §2 PRESS=send in COMMAND; §7 |
| P0 red ARMED == ERROR (Copilot4.6/Codex) | §4 armed = button-unlock + countdown → RED = error only |
| P0 ARMED no escape (Copilot4.6/Opus) | §4 BACK=cancel, `◀ CANCEL` shown |
| P0 ARM→FIRE broken/invisible (Codex/Opus) | §4 explicit ARM→armed→FIRE-button + countdown |
| P1 SETUP field unlabeled (all) | §5 unit-as-field-cue + active accent |
| P1 status never drawn (Opus/Codex/CP55) | §5/§6 transient status token |
| P1 orb colour ≠ value in JAS (Gemini/Opus) | §5 orb = channel colour |
| P1 no mode/input affordance (CP55/Codex) | §5 silhouette mode cue + contextual back-hint |

## 10. Open / next
- **HW:** verify Chain Key on the actual Dial: no `FIRE KEY MISSING` when present,
  press ignored before ARM, ARM then physical Chain Key press fires, and missing
  or undetected key fails safe.
- Continue in two streams: on-device verification of firmware logic
  (encoder/back/fire routing, ARM flow, status drawing) and UI tuning (armed cue,
  status token, field accent, orb colour), both mirrored in the ESPOS round
  widgets.
