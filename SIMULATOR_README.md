# ESP32 UI Simulator

Vylepšený UI simulátor pro vývoj a testování uživatelského rozhraní ESP32 bez nutnosti nahrávání na hardware.

## 🎯 Funkce

### ✨ Vizuální vylepšení
- **ANSI barvy** - barevný výstup v terminálu
- **Unicode rámečky** - profesionální vzhled
- **Velký displej** - 64×16 znaků pro lepší čitelnost
- **Real-time FPS** - zobrazení výkonu simulátoru
- **RGB informace** - živé zobrazení barevných hodnot
- **Progress bar** - animovaný indikátor

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

### Python verze (doporučeno)
Nevyžaduje C kompilátor, funguje okamžitě:

```powershell
python sim_run.py
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
- **`platformio.ini`** - PlatformIO konfigurace (sekce `[env:ui-sim]`)

## 🎨 Příklad výstupu

```
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

## 🔧 Požadavky

### Python verze
- Python 3.6+
- Windows 10+ (podpora ANSI barev)

### C verze
- GCC/MinGW nebo MSVC kompilátor
- Windows 10+ nebo Linux

## 📝 Poznámky

Simulátor emuluje UI systém z `src/services/ui/` bez nutnosti ESP32 hardwaru. 
Ideální pro rychlý vývoj a testování UI logiky.
