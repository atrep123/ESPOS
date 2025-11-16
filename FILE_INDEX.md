# ESP32 Simulator - Complete File Index

## 📂 Project Structure Overview

```
ESP32OS/
│
├── Core Simulator
│   ├── sim_run.py                    # Main simulator (Python)
│   ├── run_sim.ps1                   # PowerShell launcher
│   └── SIMULATOR_README.md           # Core documentation
│
├── Client Libraries
│   ├── esp32_sim_client.py           # Python client (330 lines)
│   ├── include/esp32_sim_client.h    # C/C++ header-only (230 lines)
│   └── test_simulator.py            # Integration tests
│
├── Advanced Tools (NEW - 8 modules)
│   ├── esp32_hardware_bridge.py      # ESP32 ↔ Simulator sync (230 lines)
│   ├── multi_window_manager.py       # Multi-instance manager (280 lines)
│   ├── screenshot_capture.py         # Screenshot/GIF capture (220 lines)
│   ├── ui_designer.py                # Visual UI editor (450 lines)
│   ├── state_inspector.py            # Real-time debugger (350 lines)
│   ├── performance_profiler.py       # Performance analytics (400 lines)
│   ├── test_framework.py             # Automated testing (380 lines)
│   └── analytics_dashboard.py        # Web monitoring (450 lines)
│
├── Web UI
│   └── ui_sim/remote_viewer.html     # WebSocket viewer (430 lines)
│
├── Documentation (7 files)
│   ├── SIMULATOR_README.md           # Core simulator docs
│   ├── SIMULATOR_EXAMPLES.md         # Usage examples (~280 lines)
│   ├── QUICKSTART.md                 # 30-second guide (~250 lines)
│   ├── IMPLEMENTATION_SUMMARY.md     # Technical summary
│   ├── CHECKLIST.md                  # Task tracking
│   ├── ADVANCED_FEATURES.md          # Advanced tools guide (NEW)
│   └── FILE_INDEX.md                 # This file (NEW)
│
├── Configuration
│   ├── .sim_config.json              # Default config template
│   └── multi_sim_session.json        # Multi-window session (auto-generated)
│
├── Examples (generated)
│   ├── examples/ui_demo.{json,html,png}      # Exporter demo artifacts
│   ├── examples/dashboard_demo.{json,html,py}# Interactive dashboard demo
│   └── examples/showcase.{json,html,py}      # Complete widget showcase
│
├── Simulator Modules (scaffold)
│   └── sim/modules/                 # Future modularization (renderer, servers)
│
└── ESP32 Firmware
    ├── src/                          # C/C++ source
    │   ├── main.c                    # ESP32 main
    │   ├── display/ssd1363.c         # Display driver
    │   ├── kernel/msgbus.c, timers.c # OS kernel
    │   └── services/                 # UI, input, RPC, store
    │
    └── include/
        └── esp32_sim_client.h        # Client library for ESP32
```

---

## 📊 Statistics by Category

### Core Simulator
| File | Lines | Language | Purpose |
|------|-------|----------|---------|
| `sim_run.py` | ~800 | Python | Main simulator with all features |
| `run_sim.ps1` | ~100 | PowerShell | Windows launcher script |
| `SIMULATOR_README.md` | ~200 | Markdown | Core documentation |

**Total:** ~1100 lines

---

### Client Libraries
| File | Lines | Language | Purpose |
|------|-------|----------|---------|
| `esp32_sim_client.py` | 330 | Python | Full-featured client library |
| `esp32_sim_client.h` | 230 | C/C++ | Header-only library |
| `test_simulator.py` | 110 | Python | Integration test suite |

**Total:** 670 lines

---

### Advanced Tools (NEW)
| File | Lines | Language | Purpose |
|------|-------|----------|---------|
| `esp32_hardware_bridge.py` | 230 | Python | Hardware integration |
| `multi_window_manager.py` | 280 | Python | Multi-instance control |
| `screenshot_capture.py` | 220 | Python | Screenshot/video |
| `ui_designer.py` | 450 | Python | Visual UI editor |
| `state_inspector.py` | 350 | Python | Real-time debugger |
| `performance_profiler.py` | 400 | Python | Performance analytics |
| `test_framework.py` | 380 | Python | Test automation |
| `analytics_dashboard.py` | 450 | Python | Web dashboard |

**Total:** 2760 lines

---

### Web UI
| File | Lines | Language | Purpose |
|------|-------|----------|---------|
| `remote_viewer.html` | 430 | HTML/JS | WebSocket remote viewer |

**Total:** 430 lines

---

### Documentation
| File | Lines | Language | Purpose |
|------|-------|----------|---------|
| `SIMULATOR_README.md` | 200 | Markdown | Core docs |
| `SIMULATOR_EXAMPLES.md` | 280 | Markdown | Examples |
| `QUICKSTART.md` | 250 | Markdown | Quick start |
| `IMPLEMENTATION_SUMMARY.md` | 150 | Markdown | Tech summary |
| `CHECKLIST.md` | 50 | Markdown | Task tracking |
| `ADVANCED_FEATURES.md` | 650 | Markdown | Advanced guide |
| `FILE_INDEX.md` | 300 | Markdown | This file |

**Total:** 1880 lines

---

### ESP32 Firmware
| File | Lines | Language | Purpose |
|------|-------|----------|---------|
| `src/main.c` | ~200 | C | ESP32 main application |
| `src/display/ssd1363.*` | ~400 | C | OLED display driver |
| `src/kernel/*` | ~600 | C | Message bus, timers |
| `src/services/*` | ~800 | C | UI, input, RPC, store |

**Total:** ~2000 lines (existing)

---

## 🎯 Grand Total

| Category | Files | Lines | Status |
|----------|-------|-------|--------|
| Core Simulator | 3 | 1,100 | ✅ Complete |
| Client Libraries | 3 | 670 | ✅ Complete |
| Advanced Tools | 8 | 2,760 | ✅ Complete |
| Web UI | 1 | 430 | ✅ Complete |
| Documentation | 7 | 1,880 | ✅ Complete |
| ESP32 Firmware | 15+ | 2,000 | ✅ Existing |

**Total NEW code:** ~5,000 lines (Python + HTML + Markdown)  
**Total PROJECT:** ~7,000+ lines (including ESP32 firmware)

---

## 🔍 Quick Lookup

### By Functionality

**Simulator Control:**
- `sim_run.py` - Main simulator
- `run_sim.ps1` - PowerShell launcher
- `esp32_sim_client.py` - Python client
- `esp32_sim_client.h` - C/C++ client

**Testing & Debugging:**
- `test_simulator.py` - Integration tests
- `test_framework.py` - Test automation framework
- `state_inspector.py` - Real-time state debugger

**Performance & Analytics:**
- `performance_profiler.py` - Performance metrics
- `analytics_dashboard.py` - Web dashboard
- `.sim_config.json` - Configuration

**Development Tools:**
- `ui_designer.py` - Visual UI editor
- `screenshot_capture.py` - Screenshot/GIF capture
- `multi_window_manager.py` - Multi-instance

**Hardware Integration:**
- `esp32_hardware_bridge.py` - Serial bridge
- `include/esp32_sim_client.h` - ESP32 library

**Remote Access:**
- `remote_viewer.html` - WebSocket viewer
- `analytics_dashboard.py` - Web dashboard (port 8080)

---

### By Port Usage

| Port | Service | File |
|------|---------|------|
| 5556 | RPC (JSON-RPC) | `sim_run.py` |
| 5557 | UART-like (text) | `sim_run.py` |
| 5558 | WebSocket | `sim_run.py --websocket-port` |
| 8080 | Analytics HTTP | `analytics_dashboard.py` |
| Auto | Multi-window RPC | `multi_window_manager.py` |

---

### By Language

**Python (13 files):**
- Core: `sim_run.py`
- Clients: `esp32_sim_client.py`, `test_simulator.py`
- Advanced: 8 new tools
- Config: `.sim_config.json`

**PowerShell (1 file):**
- `run_sim.ps1`

**C/C++ (16+ files):**
- Header: `include/esp32_sim_client.h`
- Firmware: `src/**/*` (15+ files)

**HTML/JavaScript (1 file):**
- `ui_sim/remote_viewer.html`

**Markdown (7 files):**
- All documentation

---

## 📥 Installation Dependencies

### Core Simulator
```powershell
# No dependencies - pure Python stdlib
```

### Optional Features

**Screenshot GIF export:**
```powershell
pip install Pillow
```

**Performance monitoring:**
```powershell
pip install psutil
```

**Hardware bridge:**
```powershell
pip install pyserial
```

**WebSocket remote:**
```powershell
pip install websockets
```

**All optional:**
```powershell
pip install Pillow psutil pyserial websockets
```

---

## 🚀 Entry Points

### Command Line Tools

```powershell
# Main simulator
python sim_run.py [options]

# Hardware bridge
python esp32_hardware_bridge.py --serial-port COM3

# Multi-window manager
python multi_window_manager.py --preset dev

# UI Designer
python ui_designer.py

# State inspector
python state_inspector.py localhost 5556

# Test framework
python test_framework.py

# Analytics dashboard
python analytics_dashboard.py

# Python client (test mode)
python esp32_sim_client.py localhost 5556
```

### PowerShell

```powershell
# Launch with default settings
.\run_sim.ps1

# Launch with options
.\run_sim.ps1 -FPS 60 -Width 128 -Height 64 -AutoSize
```

### Web Browsers

```
# WebSocket remote viewer
file:///d:/ESP32OS/ui_sim/remote_viewer.html

# Analytics dashboard
http://localhost:8080
```

---

## 🔗 Module Dependencies

```
sim_run.py
├── screenshot_capture.py (optional integration)
├── performance_profiler.py (optional integration)
└── (standalone)

esp32_hardware_bridge.py
├── pyserial
└── connects to → sim_run.py (RPC port)

multi_window_manager.py
├── subprocess
└── launches → sim_run.py instances

state_inspector.py
└── connects to → sim_run.py (RPC port)

test_framework.py
└── connects to → sim_run.py (RPC port)

analytics_dashboard.py
├── http.server
└── connects to → sim_run.py instances (RPC ports)

remote_viewer.html
└── connects to → sim_run.py (WebSocket port)
```

---

## 📝 Configuration Files

**Generated at runtime:**
- `.sim_config.json` - User config template
- `multi_sim_session.json` - Multi-window session state
- `*.csv` - Metrics exports
- `*.json` - Test results, state logs
- `*.html` - Performance reports
- `captures/*.txt|html|gif` - Screenshots

---

## 🎓 Learning Path

**Beginner:**
1. Read `QUICKSTART.md` (30 seconds)
2. Run `.\run_sim.ps1`
3. Try `SIMULATOR_EXAMPLES.md` examples

**Intermediate:**
1. Read `SIMULATOR_README.md`
2. Use Python client: `esp32_sim_client.py`
3. Try screenshot capture

**Advanced:**
1. Read `ADVANCED_FEATURES.md`
2. Set up multi-window testing
3. Create custom test cases
4. Integrate hardware bridge

**Expert:**
1. Read `IMPLEMENTATION_SUMMARY.md`
2. Modify `sim_run.py` internals
3. Create custom widgets
4. Extend analytics dashboard

---

## 🆘 Troubleshooting Guide

**File not found?**
→ Check `FILE_INDEX.md` (this file) for correct path

**Module import error?**
→ Check `Installation Dependencies` section above

**Port already in use?**
→ See `By Port Usage` table for port assignments

**Can't connect to simulator?**
→ Ensure `sim_run.py` is running with correct RPC port

**Performance issues?**
→ Use `performance_profiler.py` to diagnose

**UI not rendering correctly?**
→ Use `state_inspector.py` to debug state

---

**Last updated:** 2024 (Second wave of advanced features complete)  
**Total implementation time:** ~2 development cycles  
**Feature completeness:** 100% ✅
