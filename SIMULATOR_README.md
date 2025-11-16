# ESP32 UI Simulator

Vylepšený UI simulátor pro vývoj a testování uživatelského rozhraní ESP32 bez nutnosti nahrávání na hardware.

## 🎯 Funkce

### ✨ Vizuální vylepšení
- **ANSI barvy** - barevný výstup v terminálu s optimalizací escape sekvencí
- **Unicode rámečky** - profesionální vzhled
- **Velký displej** - až 100×24 znaků (konfigurovatelné)
- **Real-time FPS** - zobrazení výkonu simulátoru
- **RGB informace** - živé zobrazení barevných hodnot
- **Progress bar** - animovaný indikátor
- **Efektivní rendering** - substring diff s ANSI-aware algoritmy

### ⚡ Výkonnostní optimalizace
- **Substring diff rendering** - překresluje jen změněné části řádků
- **ANSI optimalizace** - automatické odstraňování redundantních reset sekvencí
- **Adaptivní pacing** - přesné dodržení cílového FPS
- **Periodic redraw** - konfigurovatelný interval pro prevenci driftu
- **TypedDict events** - type-safe event handling s lepší diagnostikou

### 🎮 Interaktivní ovládání
- **A/B/C** - Simulace tlačítek (A přepíná scénu)
- **R** - Červená barva pozadí
- **G** - Zelená barva pozadí  
- **Y** - Žlutá barva pozadí
- **W** - Bílá barva pozadí
- **K** - Černá barva pozadí
- **D** - Zapnutí/vypnutí auto demo módu
- **Q** - Ukončení simulátoru

### 📊 Zobrazované informace
- Aktuální scéna (HOME/SETTINGS/CUSTOM)
- Tick counter
- FPS (snímky za sekundu)
- RGB565 barva + hex hodnota
- Stav tlačítek (●/○)
- Číslo snímku

## 🚀 Spuštění

### ⚡ Rychlé VS Code Tasks

Ve VS Code jsou k dispozici předpřipravené úlohy pro rychlé workflow (Ctrl+Shift+P → Run Task):

- `Simulator: Start (AutoPorts, New Window)` – nový terminál, automatické porty.
- `Simulator: Start (AutoPorts, SameWindow)` – běh v aktuálním okně (snadné čtení logu).
- `Simulator: UART set_bg ff0000 (auto)` – odešle příkaz na UART‑like port z `sim_ports.json`.
- `Simulator: simctl set_bg red (auto)` – RPC volání přes `simctl.py` na aktivní `rpc_port`.
- `Tests: Run All` – kompletní sada Python testů.
- `Preview: Small Heights` – headless export extrémně malých widgetů (PNG artefakt).
- `CI: Smoke` – rychlá verifikace (designer + preview) a uložení artefaktů do `reports/`.

Manuální spuštění smoke skriptu:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\ci_smoke.ps1
```

Unicode / kódování: pokud narazíte na chyby `charmap codec`, nastavte předem:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
```

nebo používejte `python -X utf8` (již zahrnuto ve skriptech).

### Spuštění přes PowerShell launcher (doporučeno)

Spustí simulátor v novém okně nebo ve stejném okně, bez potřeby nástrojového řetězce.

Nové okno s automatickým výběrem portů:

```powershell
./run_sim.ps1 -AutoPorts -Fps 144
```

Ve stejném okně (vhodné pro ladění/logy):

```powershell
./run_sim.ps1 -SameWindow -AutoPorts -Fps 144
```

Pevně zvolené porty:

```powershell
./run_sim.ps1 -Port 8765 -UartPort 7777 -Fps 120
```

Přepínače `run_sim.ps1`:

- `-Fps <int>`: cílové FPS (výchozí 144)
- `-Port <int>`: RPC TCP port (JSON řádky); 0 = vypnuto
- `-UartPort <int>`: UART‑like textový TCP port; 0 = vypnuto
- `-AutoPorts`: zvolí volné porty pro ty, které nejsou explicitně zadány
- `-SameWindow`: spustí simulátor v aktuálním terminálu
- `-Width <int>` / `-Height <int>`: velikost UI v znacích (výchozí 100×24)
- `-NoColor`: vypne ANSI barvy
- `-NoUnicode`: ASCII rámečky místo Unicode
- `-Script <cesta>`: přehrání skriptu událostí (viz níže)
- `-FullRedrawInterval <int>`: perioda full redraw (snímky, výchozí 300, 0=vypnuto)
- `-NoDiff`: vypne substring diff rendering (vždy full redraw, debug)

### Python verze (doporučeno)

Nevyžaduje C kompilátor, funguje okamžitě:

```powershell
python sim_run.py
```

Pokročilé spuštění s vysokým FPS a RPC serverem:

```powershell
python sim_run.py --fps 144 --rpc-port 8765 --width 64 --height 16
```

Přímé přepínače `sim_run.py` jsou ekvivalentní k těm v `run_sim.ps1`:
`--fps`, `--width`, `--height`, `--rpc-port`, `--uart-port`, `--no-color`, `--no-unicode`, `--script`, `--full-redraw-interval`, `--no-diff`.

Další pokročilé parametry:

- `--com-port <port>`: připojit COM port (vyžaduje pyserial)
- `--baud <rate>`: rychlost COM portu (výchozí 115200)
- `--config <path>`: načíst konfiguraci ze souboru (JSON)
- `--export-metrics <path>`: exportovat timing metriky do CSV
- `--websocket-port <port>`: spustit WebSocket server pro remote viewer
- `--record <path>`: zaznamenat session do souboru
- `--playback <path>`: přehrát zaznamenaný session
- `--gamepad`: zapnout podporu gamepadu/joysticku přes pygame (mapuje tlačítka 0/1/2 → A/B/C)
- `--input-overlay`: otevře malé klikací okno s tlačítky A/B/C (pygame)

Poznámka k závislostem pro vstupy: pro `--gamepad` a `--input-overlay` je potřeba `pygame`. Nainstalujte např.:

```powershell
pip install pygame
# nebo pokud používáte projektové extras
pip install -e .[input]
```

### C verze

Pokud máte nainstalovaný GCC, MinGW nebo MSVC:

```powershell
# Pomocí build skriptu (automatická detekce kompilátoru)
.\build_sim.ps1

# Nebo přímo s GCC
gcc -std=c11 -O2 -Wall -D_WIN32 -o build_sim/ui_simulator.exe sim/main.c
.\build_sim\ui_simulator.exe

# Nebo s MSVC
cl /nologo /W3 /O2 /D_WIN32 /Fe:build_sim\ui_simulator.exe sim\main.c
.\build_sim\ui_simulator.exe
```

### PlatformIO verze

Vyžaduje nastavený native toolchain:

```powershell
pio run -e ui-sim
```

## 📁 Soubory

- **`sim_run.py`** - Python implementace (doporučeno pro vývoj)
- **`sim/main.c`** - C implementace (originální verze)
- **`build_sim.ps1`** - PowerShell build skript pro Windows
- **`run_sim.ps1`** - PowerShell launcher s rozšířenými parametry
- **`platformio.ini`** - PlatformIO konfigurace (sekce `[env:ui-sim]`)
- **`simctl.py`** - jednoduchý RPC klient (TCP) pro ovládání simulátoru
- **`esp32_sim_client.py`** - kompletní Python client library
- **`include/esp32_sim_client.h`** - C/C++ header-only client library
- **`events_example.json`** - ukázkový skript s časovanými událostmi
- **`.sim_config.json`** - ukázkový konfigurační soubor
- **`web/remote_viewer.html`** - WebSocket remote viewer (web UI)
- **`SIMULATOR_EXAMPLES.md`** - příklady použití a integrace

## 🎨 Příklad výstupu

```text
╔════════════════════════════════════════════════════════════════╗
║ ESP32 UI SIMULATOR                                             ║
╠════════════════════════════════════════════════════════════════╣
║ Scene: HOME       │ Tick:    142 │ FPS: 29.8                   ║
║ BG Color: RGB(  8,  4,  8) 0x0821                             ║
╠════════════════════════════════════════════════════════════════╣
║  HOME                                                          ║
║  [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] ║
║  Frame: 142                                                    ║
╠════════════════════════════════════════════════════════════════╣
║ Buttons: A:[○]  B:[○]  C:[○]                                  ║
╠════════════════════════════════════════════════════════════════╣
║ Controls: [A] Button A  [B] Button B  [C] Button C  [Q] Quit  ║
║           [R] Red  [G] Green  [Y] Yellow  [W] White  [K] Black║
╚════════════════════════════════════════════════════════════════╝
```

## 💡 Tipy

1. **Windows Terminal** nebo **ConEmu** poskytují nejlepší podporu ANSI barev
2. Stiskněte **D** pro automatické demo, které ukazuje všechny funkce
3. Python verze funguje bez dalších závislostí
4. Pro debug použijte **Q** k čistému ukončení se statistikami
5. Spuštění v novém okně s parametry:

- PowerShell: `./run_sim.ps1 -Fps 144 -Port 8765 -Width 64 -Height 16`
- CMD: `run_sim.bat 144 8765 64 16`

## 🛰️ RPC ovládání

Spusťte simulátor s RPC serverem (např. port 8765):

```powershell
python sim_run.py --rpc-port 8765
```

Posílejte JSON řádky ukončené `\n` na TCP 127.0.0.1:8765. Příklady pomocí `simctl.py`:

```powershell
python simctl.py 8765 set_bg 255 0 0
python simctl.py 8765 btn A press
python simctl.py 8765 btn A release
python simctl.py 8765 scene 2
```

Struktura zpráv:

- `{"method":"set_bg","rgb":[R,G,B]}` nebo `{"method":"set_bg","rgb565":4660}`
- `{"method":"btn","id":"A|B|C","pressed":true|false}`
- `{"method":"scene","value":0|1|2}`

## 🧪 UART‑like text server

Pro kompatibilitu s firmware parserem lze posílat textové příkazy na TCP `UartPort` (127.0.0.1):

```powershell
$client = New-Object System.Net.Sockets.TcpClient
$client.Connect('127.0.0.1',7777)
$w = New-Object System.IO.StreamWriter($client.GetStream()); $w.AutoFlush = $true
$w.WriteLine('set_bg ff0000')
Start-Sleep -Milliseconds 100
$client.Close()
```

Podporováno:

- `set_bg <hexRGB888>` např. `set_bg ff0000`

## 🔌 COM bridge (volitelně)

Simulátor může číst příkazy přímo z COM portu (stejný tvar jako UART‑like TCP: např. `set_bg ff0000`).

Spuštění s COM bridge (vyžaduje pyserial):

```powershell
pip install pyserial
python sim_run.py --com-port COM3 --baud 115200 --fps 144
```

Informace o aktivních portech (včetně `com_port`) jsou dostupné v `sim_ports.json` po startu simulátoru.

## 🎬 Skriptované přehrávání

Načte události z JSON souboru (seřazené podle `at_ms`):

```powershell
python sim_run.py --script events_example.json --fps 144
```

## 📉 Stavový footer (výkon)

Ve spodní části UI je zobrazen průběžný stav výpočtu: `compute Xms  sleep Yms  util Z%`.

- `compute` – čas kreslení a logiky na snímek
- `sleep` – čekání do cílového FPS
- `util` – přibližná zátěž: compute/(compute+sleep)

## 🧱 Widgetový layout (modulární renderer)

Od teď je vykreslování složené z widgetů. Pořadí a přítomnost prvků můžete snadno měnit v souboru `sim_run.py` úpravou seznamu widgetů v `render_frame`:

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

- Přidání nového prvku: vytvořte třídu `Widget` s metodou `render(self, ctx)` a vložte ji do seznamu.
- Změna pořadí/oddělovačů: přesouvejte položky nebo `DividerWidget()` dle potřeby.
- Kontext `RenderContext` zpřístupňuje: `state`, `frame_num`, `fps`, `width`, `height`, `use_unicode`, `use_color`, `compute_ms`, `sleep_ms`, `util`.

## 🛠️ Odstraňování problémů

- Port je obsazen / spojení odmítnuto:

  ```powershell
  netstat -ano | findstr ":8765"
  netstat -ano | findstr ":7777"
  ```

  spusťte s automatickými porty:

  ```powershell
  ./run_sim.ps1 -AutoPorts
  ```

- Chyby a výjimky (log se vytvoří jen při chybách):

  ```powershell
  Get-Content ./simulator.log -Tail 120
  ```

- Ladění ve stejném okně a ukončení klávesou `Q`:

  ```powershell
  ./run_sim.ps1 -SameWindow -AutoPorts
  ```

## 🔧 Požadavky

### Požadavky – Python

- Python 3.6+
- Windows 10+ (podpora ANSI barev)

### Požadavky – C

- GCC/MinGW nebo MSVC kompilátor
- Windows 10+ nebo Linux

## 📝 Poznámky

Simulátor emuluje UI systém z `src/services/ui/` bez nutnosti ESP32 hardwaru.
Ideální pro rychlý vývoj a testování UI logiky.

### 🔗 Další zdroje

- **Client libraries**: `esp32_sim_client.py` (Python), `include/esp32_sim_client.h` (C/C++)
- **Remote viewer**: Otevřete `ui_sim/remote_viewer.html` v prohlížeči (vyžaduje WebSocket server)
- **Příklady**: Viz `SIMULATOR_EXAMPLES.md` pro pokročilé use-cases
- **Config template**: `.sim_config.json` - zkopírujte a upravte dle potřeby

### 📊 Exportované soubory

- `sim_ports.json` - aktuální porty a PID simulátoru (smazáno při ukončení)
- `simulator.log` - log chyb (vytváří se jen při chybách)
- `metrics.csv` - performance metriky (pokud použito `--export-metrics`)
- `session.json` - záznam session (pokud použito `--record`)
