# Contributing to ESP32OS

Děkujeme za zájem přispívat do ESP32OS! Tato příručka ti pomůže začít.

## 🚀 Quick Start

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ESPOS.git
   cd ESPOS
   ```

2. **Nastav prostředí**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Spusť testy**
   ```powershell
   pytest -q
   ```

## 📋 CI/CD Pipeline

Při každém push/PR se automaticky spouští:

### Python Tests
- **OS**: Ubuntu + Windows
- **Python verze**: 3.11, 3.12
- **Testování**: `pytest` s headless režimem
- **Coverage**: Generováno na Ubuntu + Python 3.12

### Linting
- **Nástroj**: `flake8`
- **Kritické chyby**: E9, F63, F7, F82 (syntax errors, undefined names)
- **Warnings**: Maximální složitost 10, délka řádku 127

### ESP32 Firmware Build
- **Board**: esp32-s3-devkitm-1 (můžeš rozšířit matrix)
- **Nástroj**: PlatformIO
- **Artifacts**: Firmware binárky se ukládají 30 dní

## 🛠️ Development Workflow

1. **Vytvoř branch**
   ```bash
   git checkout -b feature/my-awesome-feature
   ```

2. **Proveď změny**
   - Dodržuj existující kódovací styl
   - Přidej testy pro novou funkcionalitu
   - Aktualizuj dokumentaci

3. **Spusť lokální testy**
   ```powershell
   # Všechny testy
   pytest -q

   # Specifický test
   pytest test_ui_designer_pro.py -v

   # S coverage
   coverage run -m pytest
   coverage report
   ```

4. **Zkontroluj lint**
   ```powershell
   flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

5. **Commit & Push**
   ```bash
   git add .
   git commit -m "feat: add awesome feature"
   git push origin feature/my-awesome-feature
   ```

6. **Vytvoř Pull Request**
   - GitHub automaticky spustí CI/CD
   - Zkontroluj, že všechny joby prošly ✅
   - Požádej o review

## 🧪 Testing Guidelines

### Headless Mode
Všechny UI testy musí fungovat v headless režimu (pro CI):
```python
os.environ["ESP32OS_HEADLESS"] = "1"
```

### Test Coverage
- Minimální coverage: 70% (doporučeno 80%+)
- Zahrň edge cases a error handling
- Testuj cross-platform (Windows/Linux)

### Performance Tests
Pro performance kritický kód používej `performance_profiler.py`:
```python
from performance_profiler import PerformanceProfiler

profiler = PerformanceProfiler(history_size=1000)
profiler.record_frame(fps, render_ms, frame_ms)
profiler.export_to_html("report.html")
```

## 📦 Build & Artifacts

### ESP32 Firmware
```powershell
# Build
pio run -e esp32-s3-devkitm-1

# Upload
pio run -e esp32-s3-devkitm-1 -t upload

# Monitor
pio device monitor
```

### Python Packages
```powershell
# Export UI
python ui_export_c.py

# Run simulator
python sim_run.py --rpc-port 8765
```

## 🐛 Reporting Bugs

1. Zkontroluj existující Issues
2. Vytvoř nový Issue s těmito informacemi:
   - **Popis**: Co se stalo vs. co jsi očekával
   - **Kroky k reprodukci**: Krok-za-krokem návod
   - **Prostředí**: OS, Python verze, ESP32 board
   - **Logy**: Error messages, screenshots

## 💡 Feature Requests

1. Popisuj use case a motivaci
2. Navrhni možnou implementaci
3. Přidej odkazy na relevantní dokumentaci

## 📖 Documentation

Při přidávání funkcí aktualizuj:
- `README.md` - hlavní dokumentace
- `QUICKSTART.md` - rychlý start
- `IMPLEMENTATION_SUMMARY.md` - technický přehled
- Docstringy v kódu

## ✅ Checklist před PR

- [ ] Všechny testy projdou (`pytest -q`)
- [ ] Lint bez kritických chyb (`flake8 ...`)
- [ ] Přidány testy pro novou funkcionalitu
- [ ] Dokumentace aktualizována
- [ ] CI/CD pipeline prošel (GitHub Actions)
- [ ] Changelog aktualizován (pokud je relevantní)

## 🤝 Code Review Process

1. **Automatická kontrola**: CI/CD musí projít
2. **Peer review**: Minimálně 1 approve
3. **Dokumentace**: Zkontroluj, že je kompletní
4. **Merge**: Squash commit do main

Děkujeme za tvůj příspěvek! 🎉
