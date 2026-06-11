# M5 Dial — Control Architecture (Prop LoRa Controller)

Decided with Filip after the multi-model control-clarity council (Gemini, Codex,
Opus, Copilot 4.6, Copilot 5.5). This is the agreed control model + how it
resolves the council's findings.

## 1. Hardware inputs
- **Rotary encoder** — `ROTATE` (relative) + `PRESS` (click).
- **BACK button** (side) — mode toggle / cancel.
- **Dedicated FIRE button** (NEW, to be added) — physically separate, *only* for
  ODPAL/fire. Hardware separation is the first safety factor.
- Touchscreen exists but is **secondary** (must be fully operable without it —
  this fixes the council's P0 "send is touch-only").

## 2. Control grammar (input × mode)
| Input | SETUP (tune) | COMMAND (send) | When ARMED |
|-------|--------------|----------------|------------|
| ROTATE | change active field value | scroll action (PREVIEW/PING/STOP/ARM) | ignored (locked) |
| PRESS | next field (LED → HUE → JAS → …) | **send** selected action → sending → ACK | ignored (locked) |
| BACK | → COMMAND | → SETUP | **cancel / disarm** |
| FIRE button | (locked) | (locked until ARM) | **fire** → sending → ACK |

Press now *means* something per mode — the core P0 fix (`PRESS` in COMMAND must
call `_run_selected_action()`, not `_next_field()`).

## 3. The two modes (BACK toggles)
- **SETUP** — central **ORB** = the selected LED channel, filled with *that
  channel's actual colour*; the big value is the active field. Bottom arc = the 4
  channels, selected one brought forward + ringed. Fields cycle on PRESS:
  **LED** (which channel) → **HUE** (its colour °) → **JAS** (global brightness %).
- **COMMAND** — central **hollow transmit ring** + action label; left/right
  **chevrons** = rotate to scroll actions. PRESS sends the selected action.
- Mode is read from the **centre shape** (filled orb = tuning, hollow ring = sending)
  — no text caption (minimal), reinforced by the cues in §5.

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
- **Mode cue:** filled orb (a value you *hold/tune*) vs hollow ring + chevrons (a
  thing you *pick & send*). Distinct silhouettes — readable at a glance.
- **Active SETUP field via the value's UNIT** (no caption): `2` = LED index,
  `120°` = HUE, `80%` = JAS. The active element also gets a subtle accent.
- **Selection:** orb = the selected channel's real colour (fix: JAS orb must use
  the channel colour, not red); selected bottom dot ringed.
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

## 7. Firmware mapping (`app_prop_tx.cpp` / `gui_prop_tx.cpp`)
- **Encoder PRESS:** branch by mode — COMMAND → `_run_selected_action()`; SETUP →
  `_next_field()` (currently always `_next_field` — the P0 bug).
- **BACK:** toggle SETUP↔COMMAND; when armed → cancel/disarm.
- **FIRE button (new GPIO):** handler active only when `armed` → fire → UI sending
  → ACK; otherwise ignored.
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
- **HW:** pick the FIRE-button GPIO on the Dial (Port A/B free pin) — to confirm.
- Implement in two streams: firmware logic (encoder/back/fire routing, ARM flow,
  draw status) and UI (armed cue, status token, field accent, orb colour) — both
  mirrored in the ESPOS round widgets.
