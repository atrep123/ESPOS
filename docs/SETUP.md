# Setup Guide - ESP32OS

Quick setup instructions for different environments.

## Windows (PowerShell)

```powershell
# Quick setup
.\run\setup.ps1

# Or use tools version
.\tools\setup_env.ps1

# Or VS Code task
# Ctrl+Shift+P → Tasks: Run Task → "Setup: Python env (Windows)"
```

## Linux / macOS / WSL

```bash
# Run setup script
bash run/setup.sh

# Activate environment
source .venv/bin/activate
```

## Git Bash on Windows

```bash
# Note: Git Bash on Windows works, but setup.sh was updated to handle Windows paths
bash run/setup.sh
```

## What Gets Installed

The setup scripts will:

1. ✅ Create Python virtual environment (`.venv`)
2. ✅ Upgrade pip
3. ✅ Install project dependencies with extras: `ui,web,hw,metrics,input,dev`
4. ✅ Optionally install PlatformIO
5. ✅ Run self-check to verify installation

## Dependencies Breakdown

### Core (required)
- `pillow` - Image handling for UI designer
- `watchdog` - File watching for live preview  
- `websockets` - WebSocket server for live preview

### UI (optional)
- `tkinter` - GUI designer (usually bundled with Python)

### Development (optional)
- `pytest` - Test framework
- `hypothesis` - Property-based testing
- `pre-commit` - Git hooks

## Manual Installation

If automated setup fails:

```powershell
# Create venv
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install core dependencies
python -m pip install --upgrade pip
python -m pip install pillow watchdog websockets pytest

# Install project (editable mode with extras)
python -m pip install -e ".[ui,web,hw,metrics,input,dev]"
```

## Verification

```powershell
# Run self-check
python tools\self_check.py

# Run tests
python -m pytest -q

# Start simulator
python sim_run.py --auto-size

# Start UI designer GUI
python ui_designer_preview.py
```

## Troubleshooting

### `No Python at '"/usr/bin\python.exe'`

Your `.venv` was created in WSL/Linux but you're running on Windows. Fix:

```powershell
# Delete old venv
Remove-Item -Recurse -Force .venv

# Recreate with Windows Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
python -m pip install pillow watchdog websockets pytest
```

### ImportError: No module named 'PIL'

Dependencies not installed. Run:

```powershell
python -m pip install -r requirements.txt
```

### Pytest exit code 2

This is usually a false positive. Verify tests work:

```powershell
python -m pytest -q --tb=short
```

If tests pass (e.g., "26 passed, 1 skipped"), ignore the self-check pytest warning.

## VS Code Integration

After setup, you can use VS Code tasks:

- **Simulator: Start** - Launch simulator
- **Designer: Open GUI (Drag & Drop)** - Visual UI editor
- **UI Designer: Live Preview** - Auto-refresh browser preview
- **Tests: Run All** - Execute test suite
- **CI: Smoke** - Quick smoke test

Access via: `Ctrl+Shift+P` → `Tasks: Run Task`

## ESP-IDF Setup (Optional)

For ESP32 firmware development:

1. Install ESP-IDF extension in VS Code
2. Run: `ESP-IDF: Configure ESP-IDF Extension` (Command Palette)
3. Choose EXPRESS installation
4. Select version (v5.1 or v5.2 recommended)

Or use PlatformIO (simpler):

```powershell
# PlatformIO already configured
pio run -e esp32-s3-devkitm-1        # Build
pio run -e esp32-s3-devkitm-1 -t upload  # Upload
```
