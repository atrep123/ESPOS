# 🛠️ ESP32OS Tech Stack

> A consolidated overview of languages, frameworks, libraries, and tools used across the project.

## 🖥️ Core Languages

| Language | Usage | Version |
|----------|-------|---------|
| **Python** | Simulator, Tooling, Tests, Backend | 3.9+ |
| **C / C++** | ESP32 Firmware, Client Library | C99 / C++11 |
| **JavaScript / HTML** | Web Designer, Remote Viewer | ES6+ |
| **PowerShell** | Windows Automation Scripts | 5.1+ |
| **Rust** | Tauri Backend (Web Designer) | Stable |

---

## 🐍 Python Ecosystem

**Dependency File:** `requirements.txt` / `pyproject.toml`

### Core Libraries

- `websockets`: Real-time communication (Simulator ↔ Web).
- `pyserial`: Hardware bridge (ESP32 UART).
- `Pillow`: Image processing & screenshot capture.
- `psutil`: Performance monitoring & profiling.
- `tomli`: TOML parsing (config).

### Testing & Quality

- `pytest`: Test runner.
- `pytest-asyncio`: Async test support.
- `ruff`: Fast linter & formatter.
- `mypy`: Static type checker.
- `bandit`: Security static analysis.
- `pip-audit`: Vulnerability scanning.

### Packaging

- `pyinstaller`: Binary executable generation.
- `setuptools`: Package distribution.

---

## 🌐 Web & Node.js Ecosystem

**Dependency File:** `package.json` / `web_designer_frontend/package.json`

### Frontend

- `Vite`: Build tool & dev server.
- `Tauri`: Desktop app framework (Rust backend).
- `Canvas API`: High-performance rendering.

### Security & Tools

- `npm audit`: Vulnerability scanning.
- `license-checker`: License compliance.
- `CycloneDX`: SBOM generation.
- SARIF bundle from security-audit (pip-audit, npm audit, Bandit).

---

## 🔌 Firmware (ESP32)

**Dependency File:** `platformio.ini`

### Frameworks

- **ESP-IDF**: Official Espressif IoT Development Framework.
- **Arduino**: (Optional/Legacy support).

### Drivers & Protocols

- `SSD1363`: OLED display driver (custom implementation).
- `UART`: Serial communication.
- `JSON-RPC`: Remote control protocol.

---

## ⚙️ DevOps & CI/CD

**Config Files:** `.github/workflows/*.yml`

### GitHub Actions

- **Tests:** Multi-OS (Windows, Ubuntu, macOS) + Python matrix; tools tests isolated; plugins/capture disabled for reliability.
- **ESP32 Build:** PlatformIO build for `esp32-s3-devkitm-1`, publishes `esp32-firmware-esp32-s3-devkitm-1` (bin + elf).
- **Security Audit (weekly, manual):** pip-audit, npm audit → SARIF bundle, safety, SBOM (py/node/unified), license policy, secret scan; summary + `reports/security_dashboard.md` artifact.
- **Dependency Check (weekly, manual):** outdated pip/npm JSON artifacts (`outdated-pip`, `outdated-npm`).
- **CodeQL:** Static analysis (Python/JS) with SARIF upload (if code scanning enabled).
- **Markdown Lint / Release:** Markdown lint on PRs; release flow auto-generates changelog and attaches artifacts.

### Security Tools

- `secret_scan.py`: Custom regex-based secret detection.
- `license_policy_eval.py`: License compliance enforcement.
- `unify_sbom.py`: Unified Software Bill of Materials generator.
- SARIF bundle uploads from security-audit (pip-audit, npm audit, Bandit) for downstream code scanning.

---

## 📊 Data Formats

- **JSON**: Configuration, RPC, Export/Import, Metrics.
- **CSV**: Performance logs.
- **TOML**: Project metadata (`pyproject.toml`).
- **YAML**: CI/CD workflows.
- **SARIF**: Static analysis results.

---

## 🛠️ Development Tools

- **VS Code**: Primary IDE (Settings in `.vscode/`).
- **PowerShell Scripts**: `run_sim.ps1`, `build_sim.ps1`.
- **Simulator**: Custom Python-based terminal UI simulator.
- **UI Designer**: Visual editor for ESP32 UI layouts.
- **Unified launcher**: `python tools/esp32os_launcher.py` to start designer, simulator, exporter, web backend/frontend, and docs from one menu; configurable via `~/.esp32os/config.json` (ports, args).
- **Common logging/config**: `tools/common_logging.py` / `tools/common_config.py` shared across tools; honor `LOG_LEVEL`.
- **Simulator snapshots**: `sim_run.py --snapshot` supports txt/html/png for headless CI artifacts.
- **Launcher web status**: Menu shows backend/frontend port health and PIDs.
- **Web health check**: If `websockets` is installed, launcher also pings backend WebSocket to verify it responds.
- **Launcher config ops**: Menu supports status (`p`), reset (`r`), edit (`e`).
- **Launcher GUI**: Optional Tkinter GUI (`python tools/esp32os_launcher.py --gui`) with buttons for start/stop/status/config/docs.
- **Live widget placement preview**: Quick insert shows ghost overlay until click-to-place.
- **Placement cancel**: right-click or Esc cancels pending preview.
- **Snap toggle shortcut**: `G` toggles snap-to-grid during placement; overlay shows size/coords, auto-opens Properties panel after placing.

---
*This document is manually maintained. Update when adding new major dependencies.*
