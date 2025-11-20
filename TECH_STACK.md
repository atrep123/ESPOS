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
- **Tests:** Multi-OS (Windows, Ubuntu, macOS) matrix.
- **Release:** Automated packaging & artifacts.
- **Security Audit:** Weekly vulnerability scans (Python + Node).
- **CodeQL:** Advanced static analysis.

### Security Tools
- `secret_scan.py`: Custom regex-based secret detection.
- `license_policy_eval.py`: License compliance enforcement.
- `unify_sbom.py`: Unified Software Bill of Materials generator.

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

---
*This document is manually maintained. Update when adding new major dependencies.*
