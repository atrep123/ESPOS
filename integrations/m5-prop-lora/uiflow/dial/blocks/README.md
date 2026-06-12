# PropTx — UIFlow2 custom blocks

Custom UIFlow2 blocks that wrap the **proven** `prop_frame.py` protocol so the Dial UI
can be built **drag-and-drop** while the safety-critical framing stays a tested library.

```
 UIFlow2 block canvas
   ├─ standard blocks: Display / Rotary / Button / Setup / Loop   (the UI)
   └─ "PropTx" custom blocks   ──calls──▶  prop_frame.py   (proven == C++ firmware)
                                           prop_ui.py      (hue→rgb helper)
                                  ──UART FF/SEND──▶ C++ modem ▶ DinMeter (keeps ALL safety)
```

Why blocks call a library instead of *being* the protocol: UIFlow2 codegen is one-way
(blocks → Python; there is **no** Python → blocks import), and you never want HMAC framing
re-implemented in blocks. So the hard 20% stays `prop_frame.py`; the blocks are thin wrappers.

## The block set

Category **`PropTx`**, colour `#2E9E72`. `${x}` = the block's input named `x`.

| Block (display) | Type | Inputs | Block Code (MicroPython) |
|---|---|---|---|
| **Prop init  TX `tx` RX `rx`** | execute | `tx`,`rx` (number) | `global prop_uart, prop_tx, prop_frame, prop_ui`<br>`import prop_frame`<br>`import prop_ui`<br>`from hardware import UART`<br>`prop_uart = UART(1, baudrate=115200, bits=8, parity=None, stop=1, tx=${tx}, rx=${rx})`<br>`prop_uart.write('\n')`<br>`prop_tx = prop_frame.PropSender()` |
| **Prop PREVIEW colors `colors`** | execute | `colors` (variable) | `prop_uart.write(prop_tx.preview_line(${colors}))` |
| **Prop ODPAL colors `colors`** | execute | `colors` (variable) | `prop_uart.write(prop_tx.fire_line(${colors}))` |
| **Prop STOP** | execute | — | `prop_uart.write(prop_tx.stop_line())` |
| **Prop ARM** | execute | — | `prop_uart.write(prop_tx.arm_line())` |
| **Prop remote LED `which`** | execute | `which` (number: 3 or 5) | `prop_uart.write(prop_tx.remote_led_line(prop_frame.REMOTE_LED_BIT_LED3 if ${which} == 3 else prop_frame.REMOTE_LED_BIT_LED5))` |
| **Prop sync palette `colors`** | execute | `colors` (variable) | `prop_uart.write(prop_tx.palette_line(1, False, ${colors}, track_ack=False))` |
| **Prop reply** | value | — | `((prop_uart.read() or b'').decode() if prop_uart.any() else '')` |
| **Prop hue `deg` to color** | value | `deg` (number) | `prop_ui.hsv(${deg})` |
| **Prop default hues** | value | — | `[0, 120, 240, 210, 60]` |
| **Prop default colors** | value | — | `prop_ui.palette_from_hues([0, 120, 240, 210, 60])` |
| **Prop colors from hues `hues`** | value | `hues` (variable) | `prop_ui.palette_from_hues(${hues})` |
| **Prop set color `colors` LED `index` to `color`** | value | `colors`,`index`,`color` | returns a copied color list with one 1-based LED slot replaced |
| **Prop first four `colors`** | value | `colors` (variable) | `list(${colors})[:4]` |
| **Prop RGB `r` G `g` B `b`** | value | `r`,`g`,`b` (number) | `(r,g,b)` tuple with channels clamped to 0..255 |
| **Prop RGB888 `color`** | value | `color` (variable) | `prop_ui.rgb888(${color})` |
| **Prop remote LED3** | execute | — | `prop_uart.write(prop_tx.remote_led_line(prop_frame.REMOTE_LED_BIT_LED3))` |
| **Prop remote LED5** | execute | — | `prop_uart.write(prop_tx.remote_led_line(prop_frame.REMOTE_LED_BIT_LED5))` |

`colors` is a Python list of `(r,g,b)` tuples. Use **Prop default colors** for the standard
5-LED palette, **Prop set color** to replace one LED slot, and **Prop first four** when
sending PREVIEW/ODPAL. Palette sync sends up to 8 colors.

The exact per-block templates are also in [`code/`](code/) (one `<name>.py` per block) for the
generator route below.

> **Parameter order** when entering a block: the **Block (display)** column above shows it —
> the fixed words are `label` params, the `back-ticked` names are the inputs (`number` or
> `variable`). The exact ordered param list per block is in [`prop_tx.json`](prop_tx.json).

## Validated manual bundle

Before copying anything into M5Stack Block Designer, run the local bundle check:

```sh
python tools/validate_uiflow_blocks.py
```

The check proves that `prop_tx.json` and every `code/<name>.py` template agree on block
names, input parameters, and `${placeholder}` usage. It also checks that the two runtime
libraries that must be uploaded to the Dial, `prop_frame.py` and `prop_ui.py`, are present.

Manual import source of truth:

- Manifest / parameter order: `uiflow/dial/blocks/prop_tx.json`
- Pasteable block code: `uiflow/dial/blocks/code/<name>.py`
- Alpha-2 .m5b2 source: `uiflow/dial/blocks/alpha2/PropTx.py`
- Offline Alpha-2 import artefact: `uiflow/dial/blocks/dist/PropTx.m5b2`
- Alpha-2 artefact builder: `tools/build_uiflow_alpha2_artifact.py`
- Generated-code smoke example: `uiflow/dial/blocks/examples/prop_tx_smoke.py`
- Device libraries to upload: `uiflow/dial/prop_frame.py`, `uiflow/dial/prop_state.py`,
  `uiflow/dial/prop_ui.py`, and the Alpha-2 runtime wrapper
  `uiflow/dial/blocks/alpha2/PropTx.py` as `/flash/PropTx.py`.

## Alpha-2 .m5b2 path (current Block Designer)

The current M5Stack Block Designer is **Alpha-2** and exports `.m5b2`, not the older `.m5b`
format. Use this path first:

1. Open **[block-designer.m5stack.com](https://block-designer.m5stack.com/)**.
2. Click **Load .py** and select `uiflow/dial/blocks/alpha2/PropTx.py`.
3. Confirm the preview shows the `PropTx` class and blocks such as `Prop init TX`.
4. Click **Save .m5b2** and export `PropTx.m5b2`.
5. In UIFlow2, use **Custom -> Open** and choose the exported `PropTx.m5b2`.

For offline use, skip the designer export and import `uiflow/dial/blocks/dist/PropTx.m5b2`
directly in UIFlow2.

To rebuild the tracked offline artefact from `alpha2/PropTx.py`, run:

```sh
python tools/build_uiflow_alpha2_artifact.py
python tools/validate_uiflow_blocks.py
```

That tracked `.m5b2` avoids the online Block Designer export step. The UIFlow2 canvas still needs UIFlow2 Web or an
already cached/available UIFlow2 app to edit the visual block graph;
the fully offline field path is uploading the Python runtime files with `mpremote`.

The Alpha-2 source is a class wrapper because the new designer builds custom blocks from
Python classes. The methods still only call `prop_frame.py` and `prop_ui.py`; the HMAC frame
logic remains in the tested library.

## Generated-code smoke example

`uiflow/dial/blocks/examples/prop_tx_smoke.py` shows the Python shape that the Alpha-2
blocks should generate: import `PropTx`, instantiate `proptx_0 = PropTx(13, 15)`, build
the default palette, override one LED color, send `preview`/remote LED/`stop`, and read
`reply`.

## Legacy `.m5b` path

The current recommended UIFlow2 path is the Alpha-2 `.m5b2` flow above. The older `.m5b`
route below is kept only for older Block Designer/generator experiments.

**Route A — legacy Block Designer:**
1. Open **[block-designer.m5stack.com](https://block-designer.m5stack.com/)**.
2. Set **Category** = `PropTx` and **Colour** = `#2E9E72` (shared by all blocks).
3. For **each row** in the table above, **Add a block** and fill in:
   - **Type** = `execute` or `value` (the Type column).
   - **Parameters** — click **Add** per param, enter its **name** + pick its **type**:
     `label` for each fixed word, **number** for numeric fields, **variable** for lists
     and color tuples. Order = the *Block (display)* column / `prop_tx.json`.
   - **Block Code** box — paste the MicroPython from the table; reference inputs as
     `${name}` (e.g. `${tx}`, `${colors}`). A space in a param name becomes `_` in the code.
4. **Download** → `prop_tx.m5b`. (Re-edit later via **Open .m5b**.)
5. In UIFlow2, use **Custom -> Open** and choose the downloaded `prop_tx.m5b`.

**Route B — generator (reproducible, needs the third-party tool):**
```sh
pip install "git+https://github.com/3110/uiflow-custom-block-generator"
python -m uiflow_custom_block_generator uiflow/dial/blocks/prop_tx.json
# -> prop_tx.m5b  (reads code/<name>.py for each block)
```

## Install on the Dial
1. Upload **`prop_frame.py`**, **`prop_state.py`**, **`prop_ui.py`**, and
   **`PropTx.py`** to the device `/flash` (UIFlow2 file manager / `mpremote` /
   `ampy`). The blocks import `PropTx`, which imports the helper modules.
2. In the UIFlow2 web IDE: **Custom → Open** → `PropTx.m5b2` for the current Alpha-2 flow.
   The blocks appear under the **PropTx** category.

## UI assembly map (rebuild main.py's UI as blocks)

[`../main.py`](../main.py) is the behavioural reference; reproduce it like this:

**Setup**
- `Prop init  TX 13 RX 15`
- a list variable `colors` = `Prop default colors`
- Display: `fillScreen`, an orb `Circle`, 5 LED swatch `Circle`s, a status `Label`
- create a `Rotary` object; init `last = rotary value`

**Loop** (`M5.update` first)
- read `rotary value`; on change, if command-mode → step the action index, else change the
  selected LED's hue (`hues[led] += delta*2`; refresh `colors` via `Prop set color` +
  `Prop hue→color`)
- on **button click**: command-mode → run the picked action block (`Prop PREVIEW/ODPAL/STOP/
  ARM/remote LED3/remote LED5`); setup-mode → next LED
- on **button hold**: toggle command ⇄ setup; on leaving setup → `Prop sync palette colors`
- set the status `Label` to `Prop reply` (shows `OK`/`ERR`/`RX` from the modem)
- redraw the orb + swatches

Safety unchanged: the Dial only *sends*; **ARM/Fire/STOP enforcement stays on the C++
DinMeter**. These blocks emit the exact same `FF`/`SEND` lines as the firmware (proven by
`tests/test_uiflow_prop_frame_parity.py`).

> Prefer no blocks at all? `main.py` already does all of the above in one file — run it in
> UIFlow2 **Python mode**. The blocks are for those who want the canvas to stay drag-and-drop.
