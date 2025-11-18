# Installer and Distribution Guide

## Overview

ESP32OS UI Designer can be distributed as a standalone executable for Windows, macOS, and Linux using PyInstaller.

## Quick Start

```bash
# Install PyInstaller
pip install pyinstaller

# Build standalone executable
python build_installer.py

# Build with options
python build_installer.py --onefile --windowed
```

## Build Options

| Option | Description | Default |
|--------|-------------|---------|
| `--onefile` | Single executable file (slower startup) | Multiple files |
| `--windowed` | Hide console window (GUI only) | True |
| `--debug` | Keep console for debugging | False |
| `--no-archive` | Skip ZIP/TAR.GZ creation | Create archive |
| `--clean` | Clean build artifacts only | Build |

## Build Modes

### Directory Mode (Default - Recommended)

Faster startup, multiple files in folder:

```bash
python build_installer.py
```

**Pros:**
- Fast startup (~1-2 seconds)
- Easier debugging
- Smaller update downloads

**Cons:**
- Multiple files to distribute
- Larger archive size

### One-File Mode

Single executable file:

```bash
python build_installer.py --onefile
```

**Pros:**
- Single file distribution
- Simpler for end users

**Cons:**
- Slower startup (~5-10 seconds)
- Larger file size
- Temp extraction on each run

## Platform-Specific Builds

### Windows

```bash
python build_installer.py --windowed
```

Creates:
- `dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer.exe`
- `dist/ESP32OS_UI_Designer_Windows.zip`

**Distribution:**
1. Upload ZIP to GitHub Releases
2. Users extract and run `.exe`
3. Optional: Create NSIS installer (see below)

### macOS

```bash
python build_installer.py --windowed
```

Creates:
- `dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer`
- `dist/ESP32OS_UI_Designer_macOS.zip`

**Distribution:**
1. Upload ZIP to GitHub Releases
2. Users extract and run
3. May need to bypass Gatekeeper: Right-click → Open

**Code Signing (Optional):**
```bash
codesign --force --deep --sign "Developer ID Application: Your Name" \
    dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer
```

### Linux

```bash
python build_installer.py
```

Creates:
- `dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer`
- `dist/ESP32OS_UI_Designer_Linux.tar.gz`

**Distribution:**
1. Upload TAR.GZ to GitHub Releases
2. Users extract: `tar -xzf ESP32OS_UI_Designer_Linux.tar.gz`
3. Make executable: `chmod +x ESP32OS_UI_Designer/ESP32OS_UI_Designer`
4. Run: `./ESP32OS_UI_Designer/ESP32OS_UI_Designer`

## Advanced Installers

### Windows - NSIS Installer

Install NSIS: https://nsis.sourceforge.io/

Create `installer.nsi`:

```nsis
!define APP_NAME "ESP32OS UI Designer"
!define VERSION "1.0.0"
!define PUBLISHER "ESP32OS"

Name "${APP_NAME}"
OutFile "ESP32OS_UI_Designer_Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"

Page directory
Page instfiles

Section
    SetOutPath "$INSTDIR"
    File /r "dist\ESP32OS_UI_Designer\*.*"
    
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\ESP32OS_UI_Designer.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\ESP32OS_UI_Designer.exe"
    
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\*.*"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\${APP_NAME}\*.*"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
SectionEnd
```

Build:
```bash
makensis installer.nsi
```

### macOS - DMG Installer

```bash
# Create DMG
hdiutil create -volname "ESP32OS UI Designer" \
    -srcfolder dist/ESP32OS_UI_Designer \
    -ov -format UDZO ESP32OS_UI_Designer.dmg
```

### Linux - .deb Package

Create `DEBIAN/control`:

```text
Package: esp32os-ui-designer
Version: 1.0.0
Architecture: amd64
Maintainer: Your Name <email@example.com>
Description: ESP32 UI Designer
 Visual UI designer for ESP32 displays
```

Create package:
```bash
mkdir -p esp32os-ui-designer/usr/bin
mkdir -p esp32os-ui-designer/usr/share/applications
mkdir -p esp32os-ui-designer/DEBIAN

cp dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer \
    esp32os-ui-designer/usr/bin/

# Create .desktop file
cat > esp32os-ui-designer/usr/share/applications/esp32os-ui-designer.desktop << EOF
[Desktop Entry]
Name=ESP32OS UI Designer
Exec=/usr/bin/ESP32OS_UI_Designer
Icon=esp32os
Type=Application
Categories=Development;
EOF

dpkg-deb --build esp32os-ui-designer
```

## File Size Optimization

### Exclude Unnecessary Modules

Edit `build_installer.py`, update `excludes` list:

```python
excludes=[
    'matplotlib', 
    'numpy', 
    'scipy', 
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
]
```

### UPX Compression

Install UPX: https://upx.github.io/

PyInstaller will use it automatically if available. Reduces size by ~40%.

### Remove Debug Symbols

In spec file, set:
```python
strip=True
```

## Auto-Update Mechanism

### 1. Version Check

Add to `ui_designer_pro.py`:

```python
import requests
from packaging import version

CURRENT_VERSION = "1.0.0"
UPDATE_URL = "https://api.github.com/repos/atrep123/ESPOS/releases/latest"

def check_for_updates():
    try:
        response = requests.get(UPDATE_URL, timeout=5)
        latest = response.json()["tag_name"].lstrip("v")
        
        if version.parse(latest) > version.parse(CURRENT_VERSION):
            return latest, latest["html_url"]
    except Exception:
        pass
    return None, None

# On startup
latest_version, download_url = check_for_updates()
if latest_version:
    show_update_dialog(latest_version, download_url)
```

### 2. GitHub Actions for Releases

`.github/workflows/release.yml`:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executable
      run: python build_installer.py --windowed
    
    - name: Upload Release Asset
      uses: actions/upload-release-asset@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        upload_url: ${{ github.event.release.upload_url }}
        asset_path: ./dist/*.zip
        asset_name: ESP32OS_UI_Designer_${{ matrix.os }}.zip
        asset_content_type: application/zip
```

## Testing Builds

### Windows

```bash
# Test executable
dist\ESP32OS_UI_Designer\ESP32OS_UI_Designer.exe

# Test with console (debug)
python build_installer.py --debug
dist\ESP32OS_UI_Designer\ESP32OS_UI_Designer.exe
```

### macOS/Linux

```bash
# Test executable
./dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer

# Check dependencies
ldd dist/ESP32OS_UI_Designer/ESP32OS_UI_Designer
```

## Troubleshooting

### Missing Modules

If runtime error "No module named X":

1. Add to `hiddenimports` in spec file
2. Rebuild: `python build_installer.py`

### Icon Not Showing

1. Create `assets/icon.ico` (Windows) or `assets/icon.icns` (macOS)
2. Update spec file `icon` path
3. Rebuild

### Large File Size

1. Enable UPX compression
2. Exclude unused modules
3. Use `--onedir` instead of `--onefile`

### Slow Startup (--onefile)

Switch to directory mode for faster startup:
```bash
python build_installer.py  # No --onefile flag
```

## Distribution Checklist

- [ ] Test on clean VM/container
- [ ] Verify all features work
- [ ] Check file size is reasonable
- [ ] Test on target OS versions
- [ ] Include README.txt
- [ ] Create release notes
- [ ] Upload to GitHub Releases
- [ ] Update download links
- [ ] Announce on social media

## Support

For build issues, check:
- PyInstaller logs in `build/`
- Console output with `--debug` flag
- GitHub Issues: https://github.com/atrep123/ESPOS/issues
