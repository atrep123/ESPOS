# Native Tests on Windows – Toolchain Setup

Tento dokument popisuje, jak spustit nativní testy PlatformIO (`[env:native]`) na Windows systémech.

## Problém

PlatformIO nativní testy vyžadují GCC kompilátor, který není standardně dostupný na Windows. Při spuštění `pio test -e native` bez GCC se objeví chyba:

```text
Error: Command ['gcc.exe', ...] not found
```

## Řešení – 3 možnosti

### Možnost 1: MSYS2 (Doporučeno pro Windows)

MSYS2 poskytuje kompletní GNU toolchain včetně GCC pro Windows.

**Instalace:**

1. Stáhněte MSYS2 installer z https://www.msys2.org/
2. Nainstalujte MSYS2 (výchozí cesta: `C:\msys64`)
3. Otevřete MSYS2 MINGW64 terminál
4. Nainstalujte GCC toolchain:

```bash
pacman -Syu
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-gdb
```

5. Přidejte MSYS2 do PATH (systémová proměnná):
   - `C:\msys64\mingw64\bin`
   - Nebo dočasně v PowerShell:
     ```powershell
     $env:PATH = "C:\msys64\mingw64\bin;$env:PATH"
     ```

6. Ověřte instalaci:

```powershell
gcc --version
```

**Spuštění testů:**

```powershell
pio test -e native
```

### Možnost 2: WSL (Windows Subsystem for Linux)

WSL2 poskytuje plnohodnotné Linux prostředí na Windows.

**Instalace:**

1. Otevřete PowerShell jako Admin a spusťte:

```powershell
wsl --install
```

2. Restartujte počítač
3. Otevřete WSL (Ubuntu) terminál
4. Nainstalujte PlatformIO a závislosti:

```bash
# Python a pip
sudo apt update
sudo apt install python3 python3-pip python3-venv

# PlatformIO
pip3 install platformio

# Závislosti pro UI Designer
pip3 install pillow pytest pyserial
```

5. Navigujte do projektu (Windows disky jsou v `/mnt/`):

```bash
cd /mnt/c/Users/atrep/Desktop/ESP32OS
```

**Spuštění testů:**

```bash
pio test -e native
```

### Možnost 3: MinGW (Alternativa)

MinGW je lehčí distribuce GCC pro Windows.

**Instalace:**

1. Stáhněte MinGW-w64 z https://sourceforge.net/projects/mingw-w64/
2. Vyberte architecture: `x86_64`, threads: `posix`, exception: `seh`
3. Rozbalte do `C:\mingw64`
4. Přidejte do PATH: `C:\mingw64\bin`

**Spuštění testů:**

```powershell
pio test -e native
```

## Přeskočení nativních testů (pokud toolchain není potřeba)

Pokud nechcete instalovat GCC, můžete nativní testy přeskočit a testovat pouze ESP32 prostředí:

```powershell
# Pouze ESP32-S3 s inteligentním přeskočením HW
pio test -e esp32-s3-devkitm-1-nohw

# Nebo konkrétní test
pio test -e esp32-s3-devkitm-1-nohw -f test_ui_core
```

## Aktualizace platformio.ini (volitelné)

Pro automatické přeskočení nativních testů bez GCC můžete přidat check do `platformio.ini`:

```ini
[env:native]
platform = native
test_framework = unity
lib_deps = unity
# Přeskočit pokud GCC není dostupný
test_ignore = 
    ${env.test_ignore}
build_unflags = 
    -Werror
```

Nebo vytvořit wrapper skript `scripts/check_native_toolchain.py`:

```python
#!/usr/bin/env python3
import shutil
import sys

if not shutil.which("gcc"):
    print("⚠️  GCC not found, skipping native tests")
    print("See NATIVE_TESTS_WINDOWS.md for toolchain setup")
    sys.exit(0)

sys.exit(1)  # GCC found, proceed with tests
```

## Ověření konfigurace

Po instalaci toolchainu ověřte, že vše funguje:

```powershell
# Kontrola GCC
gcc --version

# Kontrola PlatformIO
pio --version

# Spuštění jednoho nativního testu
pio test -e native -f test_ui_core
```

## Troubleshooting

### GCC nalezen, ale testy selhávají s linker errors

Zkontrolujte, že používáte MinGW-w64 **posix threads** verzi, ne win32 threads.

### `undefined reference to WinMain`

Ujistěte se, že test soubory obsahují `app_main()` nebo Unity test funkce.

### Testy builduji, ale nespadnou s "cannot execute binary file"

Používáte WSL bash s Windows PlatformIO nebo naopak. Ujistěte se, že PlatformIO i GCC jsou ze stejného prostředí (buď oba Windows, nebo oba WSL).

## Doporučení

- **Pro development**: MSYS2 (nejrychlejší setup, nativní Windows binárky)
- **Pro CI/CD**: WSL2 nebo Linux runner (konzistentní s production prostředím)
- **Pro rychlé testování**: Přeskočit native, použít pouze `esp32-s3-devkitm-1-nohw`

---

**Poznámka:** Všechny Python testy (`pytest`) fungují bez GCC a nejsou tímto problémem dotčeny.
