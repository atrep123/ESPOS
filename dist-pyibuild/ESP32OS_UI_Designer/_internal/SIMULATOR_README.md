# ESP32 UI Simulator

VylepĹˇenĂ˝ UI simulĂˇtor pro vĂ˝voj a testovĂˇnĂ­ uĹľivatelskĂ©ho rozhranĂ­ ESP32 bez nutnosti nahrĂˇvĂˇnĂ­ na hardware.

## đźŽŻ Funkce

### âś¨ VizuĂˇlnĂ­ vylepĹˇenĂ­

- **ANSI barvy** - barevnĂ˝ vĂ˝stup v terminĂˇlu s optimalizacĂ­ escape sekvencĂ­
- **Unicode rĂˇmeÄŤky** - profesionĂˇlnĂ­ vzhled
- **VelkĂ˝ displej** - aĹľ 100Ă—24 znakĹŻ (konfigurovatelnĂ©)
- **Real-time FPS** - zobrazenĂ­ vĂ˝konu simulĂˇtoru
- **RGB informace** - ĹľivĂ© zobrazenĂ­ barevnĂ˝ch hodnot
- **Progress bar** - animovanĂ˝ indikĂˇtor
- **EfektivnĂ­ rendering** - substring diff s ANSI-aware algoritmy

### âšˇ VĂ˝konnostnĂ­ optimalizace

- **Substring diff rendering** - pĹ™ekresluje jen zmÄ›nÄ›nĂ© ÄŤĂˇsti Ĺ™ĂˇdkĹŻ
- **ANSI optimalizace** - automatickĂ© odstraĹovĂˇnĂ­ redundantnĂ­ch reset sekvencĂ­
- **AdaptivnĂ­ pacing** - pĹ™esnĂ© dodrĹľenĂ­ cĂ­lovĂ©ho FPS
- **Periodic redraw** - konfigurovatelnĂ˝ interval pro prevenci driftu
- **TypedDict events** - type-safe event handling s lepĹˇĂ­ diagnostikou

### đźŽ® InteraktivnĂ­ ovlĂˇdĂˇnĂ­

- **A/B/C** - Simulace tlaÄŤĂ­tek (A pĹ™epĂ­nĂˇ scĂ©nu)
- **R** - ÄŚervenĂˇ barva pozadĂ­
- **G** - ZelenĂˇ barva pozadĂ­  
- **Y** - Ĺ˝lutĂˇ barva pozadĂ­
- **W** - BĂ­lĂˇ barva pozadĂ­
- **K** - ÄŚernĂˇ barva pozadĂ­
- **D** - ZapnutĂ­/vypnutĂ­ auto demo mĂłdu
- **Space/P** - Pauza/obnovenĂ­ (toggle), **C** - pokraÄŤuje z pauzy
- **S/N** - JednokrokovĂ© vykreslenĂ­ pĹ™i pauze
- **H** - Help overlay on/off
- **F10** - HUD on/off
- **F1** - TUI panel (HUD/help status + max-frames)
- **Q** - UkonÄŤenĂ­ simulĂˇtoru

### đź“Š ZobrazovanĂ© informace

- AktuĂˇlnĂ­ scĂ©na (HOME/SETTINGS/CUSTOM)
- Tick counter
- FPS (snĂ­mky za sekundu)
- RGB565 barva + hex hodnota
- Stav tlaÄŤĂ­tek (â—Ź/â—‹)
- ÄŚĂ­slo snĂ­mku

## đźš€ SpuĹˇtÄ›nĂ­

### âšˇ RychlĂ© VS Code Tasks

Ve VS Code jsou k dispozici pĹ™edpĹ™ipravenĂ© Ăşlohy pro rychlĂ© workflow (Ctrl+Shift+P â†’ Run Task):

- `Simulator: Start (AutoPorts, New Window)` â€“ novĂ˝ terminĂˇl, automatickĂ© porty.
- `Simulator: Start (AutoPorts, SameWindow)` â€“ bÄ›h v aktuĂˇlnĂ­m oknÄ› (snadnĂ© ÄŤtenĂ­ logu).
- `Simulator: UART set_bg ff0000 (auto)` â€“ odeĹˇle pĹ™Ă­kaz na UARTâ€‘like port z `sim_ports.json`.
- `Simulator: simctl set_bg red (auto)` â€“ RPC volĂˇnĂ­ pĹ™es `simctl.py` na aktivnĂ­ `rpc_port`.
- `Simulator: simctl icon_demo/icon_mode/icon_size/icon_bench` â€“ rychlĂ© ovÄ›Ĺ™enĂ­ ikonovĂ˝ch reĹľimĹŻ.
- `Tests: Run All` â€“ kompletnĂ­ sada Python testĹŻ.
- `Preview: Small Heights` â€“ headless export extrĂ©mnÄ› malĂ˝ch widgetĹŻ (PNG artefakt).
- Pozn.: Preview/PNG export pouĹľĂ­vĂˇ stejnĂ˝ renderer a cache je content-aware.
- `CI: Smoke` â€“ rychlĂˇ verifikace (designer + preview) a uloĹľenĂ­ artefaktĹŻ do `reports/`.

ManuĂˇlnĂ­ spuĹˇtÄ›nĂ­ smoke skriptu:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\ci_smoke.ps1
```

Unicode / kĂłdovĂˇnĂ­: pokud narazĂ­te na chyby `charmap codec`, nastavte pĹ™edem:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
```

nebo pouĹľĂ­vejte `python -X utf8` (jiĹľ zahrnuto ve skriptech).

### SpuĹˇtÄ›nĂ­ pĹ™es PowerShell launcher (doporuÄŤeno)

SpustĂ­ simulĂˇtor v novĂ©m oknÄ› nebo ve stejnĂ©m oknÄ›, bez potĹ™eby nĂˇstrojovĂ©ho Ĺ™etÄ›zce.

NovĂ© okno s automatickĂ˝m vĂ˝bÄ›rem portĹŻ:

```powershell
./run_sim.ps1 -AutoPorts -Fps 144
```

Ve stejnĂ©m oknÄ› (vhodnĂ© pro ladÄ›nĂ­/logy):

```powershell
./run_sim.ps1 -SameWindow -AutoPorts -Fps 144
```

PevnÄ› zvolenĂ© porty:

```powershell
./run_sim.ps1 -Port 8765 -UartPort 7777 -Fps 120
```

PĹ™epĂ­naÄŤe `run_sim.ps1`:

- `-Fps <int>`: cĂ­lovĂ© FPS (vĂ˝chozĂ­ 144)
- `-Port <int>`: RPC TCP port (JSON Ĺ™Ăˇdky); 0 = vypnuto
- `-UartPort <int>`: UARTâ€‘like textovĂ˝ TCP port; 0 = vypnuto
- `-AutoPorts`: zvolĂ­ volnĂ© porty pro ty, kterĂ© nejsou explicitnÄ› zadĂˇny
- `-SameWindow`: spustĂ­ simulĂˇtor v aktuĂˇlnĂ­m terminĂˇlu
- `-Width <int>` / `-Height <int>`: velikost UI v znacĂ­ch (vĂ˝chozĂ­ 100Ă—24)
- `-NoColor`: vypne ANSI barvy
- `-NoUnicode`: ASCII rĂˇmeÄŤky mĂ­sto Unicode
- `-Script <cesta>`: pĹ™ehrĂˇnĂ­ skriptu udĂˇlostĂ­ (viz nĂ­Ĺľe)
- `-FullRedrawInterval <int>`: perioda full redraw (snĂ­mky, vĂ˝chozĂ­ 300, 0=vypnuto)
- `-NoDiff`: vypne substring diff rendering (vĹľdy full redraw, debug)

### Python verze (doporuÄŤeno)

NevyĹľaduje C kompilĂˇtor, funguje okamĹľitÄ›:

```powershell
python sim_run.py
```

PokroÄŤilĂ© spuĹˇtÄ›nĂ­ s vysokĂ˝m FPS a RPC serverem:

```powershell
python sim_run.py --fps 144 --rpc-port 8765 --width 64 --height 16
```

PĹ™Ă­mĂ© pĹ™epĂ­naÄŤe `sim_run.py` jsou ekvivalentnĂ­ k tÄ›m v `run_sim.ps1`:
`--fps`, `--width`, `--height`, `--rpc-port`, `--uart-port`, `--no-color`, `--no-unicode`, `--script`, `--full-redraw-interval`, `--no-diff`.

RychlĂ© presety a pĹ™epĂ­naÄŤe ovlĂˇdĂˇnĂ­:
- `--preset dev|hud|quiet` (dev: auto-size + HUD + help overlay; hud: HUD on; quiet: ASCII/no-color, no diff, HUD/Help off)
- `--hud` / `--help-overlay` / `--tui-panel` nastavĂ­ poÄŤĂˇteÄŤnĂ­ stav pĹ™epĂ­naÄŤĹŻ (runtime toggle: F10/H/F1)

DalĹˇĂ­ pokroÄŤilĂ© parametry:

- `--com-port <port>`: pĹ™ipojit COM port (vyĹľaduje pyserial)
- `--baud <rate>`: rychlost COM portu (vĂ˝chozĂ­ 115200)
- `--config <path>`: naÄŤĂ­st konfiguraci ze souboru (JSON)
- `--export-metrics <path>`: exportovat timing metriky do CSV
- `--websocket-port <port>`: spustit WebSocket server pro remote viewer
- `--record <path>`: zaznamenat session do souboru
- `--playback <path>`: pĹ™ehrĂˇt zaznamenanĂ˝ session
- `--gamepad`: zapnout podporu gamepadu/joysticku pĹ™es pygame (mapuje tlaÄŤĂ­tka 0/1/2 â†’ A/B/C)
- `--input-overlay`: otevĹ™e malĂ© klikacĂ­ okno s tlaÄŤĂ­tky A/B/C (pygame)
- `--max-frames <N>`: ukonÄŤĂ­ simulĂˇtor po vykreslenĂ­ N snĂ­mkĹŻ (0 = bez limitu)

IkonovĂ© RPC pĹ™Ă­klady (pĹ™es `simctl.py <rpc_port> <cmd>`):

- `icon_demo` â€“ zobrazĂ­ grid ikon s aktuĂˇlnĂ­ velikostĂ­/mĂłdem.
- `icon_size 16|24` â€“ pĹ™epne velikost ikon (vĂ˝chozĂ­ 16).
- `icon_mode normal|invert|xor` â€“ pĹ™epne blit mĂłd.
- `icon_bench 200 size=24 mode=invert` â€“ zmÄ›Ĺ™Ă­ vykreslovĂˇnĂ­, vrĂˇtĂ­ JSON s klĂ­ÄŤi `count`, `size`, `mode`, `us_per_draw`, `fps`.

PoznĂˇmka k zĂˇvislostem pro vstupy: pro `--gamepad` a `--input-overlay` je potĹ™eba `pygame`. Nainstalujte napĹ™.:

```powershell
pip install pygame
# nebo pokud pouĹľĂ­vĂˇte projektovĂ© extras
pip install -e .[input]
```

### C verze

Pokud mĂˇte nainstalovanĂ˝ GCC, MinGW nebo MSVC:

```powershell
# PomocĂ­ build skriptu (automatickĂˇ detekce kompilĂˇtoru)
.\build_sim.ps1

# Nebo pĹ™Ă­mo s GCC
gcc -std=c11 -O2 -Wall -D_WIN32 -o build_sim/ui_simulator.exe sim/main.c
.\build_sim\ui_simulator.exe

# Nebo s MSVC
cl /nologo /W3 /O2 /D_WIN32 /Fe:build_sim\ui_simulator.exe sim\main.c
.\build_sim\ui_simulator.exe
```

### PlatformIO verze

VyĹľaduje nastavenĂ˝ native toolchain:

```powershell
pio run -e ui-sim
```

## đź“ Soubory

- **`sim_run.py`** - Python implementace (doporuÄŤeno pro vĂ˝voj)
- **`sim/main.c`** - C implementace (originĂˇlnĂ­ verze)
- **`build_sim.ps1`** - PowerShell build skript pro Windows
- **`run_sim.ps1`** - PowerShell launcher s rozĹˇĂ­Ĺ™enĂ˝mi parametry
- **`platformio.ini`** - PlatformIO konfigurace (sekce `[env:ui-sim]`)
- **`simctl.py`** - jednoduchĂ˝ RPC klient (TCP) pro ovlĂˇdĂˇnĂ­ simulĂˇtoru
- **`esp32_sim_client.py`** - kompletnĂ­ Python client library
- **`include/esp32_sim_client.h`** - C/C++ header-only client library
- **`events_example.json`** - ukĂˇzkovĂ˝ skript s ÄŤasovanĂ˝mi udĂˇlostmi
- **`.sim_config.json`** - ukĂˇzkovĂ˝ konfiguraÄŤnĂ­ soubor
- **`web/remote_viewer.html`** - WebSocket remote viewer (web UI)
- **`SIMULATOR_EXAMPLES.md`** - pĹ™Ă­klady pouĹľitĂ­ a integrace

## đź–Ľď¸Ź Headless preview (PNG export bez JSON)

Pro rychlĂ˝ nĂˇhled bez GUI a bez vstupnĂ­ho JSONu vyuĹľijte `ui_designer_preview.py` s pĹ™epĂ­naÄŤem `--headless`. VytvoĹ™Ă­ vĂ˝chozĂ­ scĂ©nu (320Ă—240) s nÄ›kolika widgety a uloĹľĂ­ PNG.

```powershell
# v aktivovanĂ©m venv
python .\ui_designer_preview.py --headless --out-png .\preview.png
```

PoznĂˇmky:

- Volba `--headless` nevyĹľaduje `--in-json`; renderer vygeneruje smysluplnou vĂ˝chozĂ­ scĂ©nu.
- VĂ˝stupnĂ­ PNG je zĂˇmÄ›rnÄ› â€žbohatĹˇĂ­â€ś (vÄ›tĹˇĂ­ neĹľ ~1 KB), aby obstĂˇl v CI smoke testech.
- StĂˇvajĂ­cĂ­ reĹľim `--headless-preview` s `--in-json` zĹŻstĂˇvĂˇ beze zmÄ›ny a je vhodnĂ˝ pro pĹ™esnĂ© exporty scĂ©n.

## đźŽ¨ PĹ™Ă­klad vĂ˝stupu

```text
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘ ESP32 UI SIMULATOR                                             â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•Ł
â•‘ Scene: HOME       â”‚ Tick:    142 â”‚ FPS: 29.8                   â•‘
â•‘ BG Color: RGB(  8,  4,  8) 0x0821                             â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•Ł
â•‘  HOME                                                          â•‘
â•‘  [â–â–â–â–â–â–â–â–â–â–â–â–â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘] â•‘
â•‘  Frame: 142                                                    â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•Ł
â•‘ Buttons: A:[â—‹]  B:[â—‹]  C:[â—‹]                                  â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•Ł
â•‘ Controls: [A] Button A  [B] Button B  [C] Button C  [Q] Quit  â•‘
â•‘           [R] Red  [G] Green  [Y] Yellow  [W] White  [K] Blackâ•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•ť
```

## đź’ˇ Tipy

1. **Windows Terminal** nebo **ConEmu** poskytujĂ­ nejlepĹˇĂ­ podporu ANSI barev
2. StisknÄ›te **D** pro automatickĂ© demo, kterĂ© ukazuje vĹˇechny funkce
3. Python verze funguje bez dalĹˇĂ­ch zĂˇvislostĂ­
4. Pro debug pouĹľijte **Q** k ÄŤistĂ©mu ukonÄŤenĂ­ se statistikami
5. SpuĹˇtÄ›nĂ­ v novĂ©m oknÄ› s parametry:

- PowerShell: `./run_sim.ps1 -Fps 144 -Port 8765 -Width 64 -Height 16`
- CMD: `run_sim.bat 144 8765 64 16`

## đź›°ď¸Ź RPC ovlĂˇdĂˇnĂ­

SpusĹĄte simulĂˇtor s RPC serverem (napĹ™. port 8765):

```powershell
python sim_run.py --rpc-port 8765
```

PosĂ­lejte JSON Ĺ™Ăˇdky ukonÄŤenĂ© `\n` na TCP 127.0.0.1:8765. PĹ™Ă­klady pomocĂ­ `simctl.py`:

```powershell
python simctl.py 8765 set_bg 255 0 0
python simctl.py 8765 btn A press
python simctl.py 8765 btn A release
python simctl.py 8765 scene 2
```

Struktura zprĂˇv:

- `{"method":"set_bg","rgb":[R,G,B]}` nebo `{"method":"set_bg","rgb565":4660}`
- `{"method":"btn","id":"A|B|C","pressed":true|false}`
- `{"method":"scene","value":0|1|2}`

## đź§Ş UARTâ€‘like text server

Pro kompatibilitu s firmware parserem lze posĂ­lat textovĂ© pĹ™Ă­kazy na TCP `UartPort` (127.0.0.1):

```powershell
$client = New-Object System.Net.Sockets.TcpClient
$client.Connect('127.0.0.1',7777)
$w = New-Object System.IO.StreamWriter($client.GetStream()); $w.AutoFlush = $true
$w.WriteLine('set_bg ff0000')
Start-Sleep -Milliseconds 100
$client.Close()
```

PodporovĂˇno:

- `set_bg <hexRGB888>` napĹ™. `set_bg ff0000`

## đź”Ś COM bridge (volitelnÄ›)

SimulĂˇtor mĹŻĹľe ÄŤĂ­st pĹ™Ă­kazy pĹ™Ă­mo z COM portu (stejnĂ˝ tvar jako UARTâ€‘like TCP: napĹ™. `set_bg ff0000`).

SpuĹˇtÄ›nĂ­ s COM bridge (vyĹľaduje pyserial):

```powershell
pip install pyserial
python sim_run.py --com-port COM3 --baud 115200 --fps 144
```

Informace o aktivnĂ­ch portech (vÄŤetnÄ› `com_port`) jsou dostupnĂ© v `sim_ports.json` po startu simulĂˇtoru.

## đźŽ¬ SkriptovanĂ© pĹ™ehrĂˇvĂˇnĂ­

NaÄŤte udĂˇlosti z JSON souboru (seĹ™azenĂ© podle `at_ms`):

```powershell
python sim_run.py --script events_example.json --fps 144
```

## đź“‰ StavovĂ˝ footer (vĂ˝kon)

Ve spodnĂ­ ÄŤĂˇsti UI je zobrazen prĹŻbÄ›ĹľnĂ˝ stav vĂ˝poÄŤtu: `compute Xms  sleep Yms  util Z%`.

- `compute` â€“ ÄŤas kreslenĂ­ a logiky na snĂ­mek
- `sleep` â€“ ÄŤekĂˇnĂ­ do cĂ­lovĂ©ho FPS
- `util` â€“ pĹ™ibliĹľnĂˇ zĂˇtÄ›Ĺľ: compute/(compute+sleep)

## đź§± WidgetovĂ˝ layout (modulĂˇrnĂ­ renderer)

Od teÄŹ je vykreslovĂˇnĂ­ sloĹľenĂ© z widgetĹŻ. PoĹ™adĂ­ a pĹ™Ă­tomnost prvkĹŻ mĹŻĹľete snadno mÄ›nit v souboru `sim_run.py` Ăşpravou seznamu widgetĹŻ v `render_frame`:

```python
widgets = [
  TitleBarWidget(),
  DividerWidget(),
  SceneStatusWidget(),
  ColorInfoWidget(),
  DividerWidget(),
  DisplayWidget(),
  DividerWidget(),
  ButtonsWidget(),
  TimingFooterWidget(),
  DividerWidget(),
  HelpWidget(),
  BottomBorderWidget(),
]
```

- PĹ™idĂˇnĂ­ novĂ©ho prvku: vytvoĹ™te tĹ™Ă­du `Widget` s metodou `render(self, ctx)` a vloĹľte ji do seznamu.
- ZmÄ›na poĹ™adĂ­/oddÄ›lovaÄŤĹŻ: pĹ™esouvejte poloĹľky nebo `DividerWidget()` dle potĹ™eby.
- Kontext `RenderContext` zpĹ™Ă­stupĹuje: `state`, `frame_num`, `fps`, `width`, `height`, `use_unicode`, `use_color`, `compute_ms`, `sleep_ms`, `util`.

## đź› ď¸Ź OdstraĹovĂˇnĂ­ problĂ©mĹŻ

- Port je obsazen / spojenĂ­ odmĂ­tnuto:

  ```powershell
  netstat -ano | findstr ":8765"
  netstat -ano | findstr ":7777"
  ```

  spusĹĄte s automatickĂ˝mi porty:

  ```powershell
  ./run_sim.ps1 -AutoPorts
  ```

- Chyby a vĂ˝jimky (log se vytvoĹ™Ă­ jen pĹ™i chybĂˇch):

  ```powershell
  Get-Content ./simulator.log -Tail 120
  ```

- LadÄ›nĂ­ ve stejnĂ©m oknÄ› a ukonÄŤenĂ­ klĂˇvesou `Q`:

  ```powershell
  ./run_sim.ps1 -SameWindow -AutoPorts
  ```

## đź”§ PoĹľadavky

### PoĹľadavky â€“ Python

- Python 3.6+
- Windows 10+ (podpora ANSI barev)

### PoĹľadavky â€“ C

- GCC/MinGW nebo MSVC kompilĂˇtor
- Windows 10+ nebo Linux

## đź“ť PoznĂˇmky

SimulĂˇtor emuluje UI systĂ©m z `src/services/ui/` bez nutnosti ESP32 hardwaru.
IdeĂˇlnĂ­ pro rychlĂ˝ vĂ˝voj a testovĂˇnĂ­ UI logiky.

### đź”— DalĹˇĂ­ zdroje

- **Client libraries**: `esp32_sim_client.py` (Python), `include/esp32_sim_client.h` (C/C++)
- **Remote viewer**: OtevĹ™ete `ui_sim/remote_viewer.html` v prohlĂ­ĹľeÄŤi (vyĹľaduje WebSocket server)
- **PĹ™Ă­klady**: Viz `SIMULATOR_EXAMPLES.md` pro pokroÄŤilĂ© use-cases
- **Config template**: `.sim_config.json` - zkopĂ­rujte a upravte dle potĹ™eby

### đź“Š ExportovanĂ© soubory

- `sim_ports.json` - aktuĂˇlnĂ­ porty a PID simulĂˇtoru (smazĂˇno pĹ™i ukonÄŤenĂ­)
- `simulator.log` - log chyb (vytvĂˇĹ™Ă­ se jen pĹ™i chybĂˇch)
- `metrics.csv` - performance metriky (pokud pouĹľito `--export-metrics`)
- `session.json` - zĂˇznam session (pokud pouĹľito `--record`)


Rychlé presety a přepínače ovládání:
- `--preset dev|hud|quiet` (dev: auto-size + HUD + help overlay; hud: HUD on; quiet: ASCII/no-color, no diff, HUD/Help off)
- `--tui-panel` zobrazí mini TUI řádek (F1 toggle) s HUD/help stavem a `max-frames`
- Klávesy: Space/P pauza, S/N krok, C continue, H help overlay, F10 HUD, F1 TUI panel

