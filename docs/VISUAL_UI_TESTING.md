# Visual UI Testing Guide

## Overview

ESP32OS obsahuje **dva typy UI testů**:

### 1. Headless Unit Tests (Automatické v CI/CD)
- **Kde:** `test_ui_*.py` (kromě `test_visual_ui_*.py`)
- **Jak:** `pytest -k test_ui`
- **Co testuje:** Logiku, API, datové struktury bez GUI
- **Prostředí:** `ESP32OS_HEADLESS=1` (žádné GUI okno)

### 2. Visual Integration Tests (Manuální/Lokální)
- **Kde:** `test_visual_ui_*.py`
- **Jak:** `pytest test_visual_ui_real.py -v` 
- **Co testuje:** Skutečné GUI, interakce, drag&drop
- **Prostředí:** Vyžaduje grafický display

## Instalace závislostí pro vizuální testy

```bash
pip install -r requirements-dev.txt
```

Instaluje:
- `pyautogui` - Automatizace myši a klávesnice
- `pywinauto` - Windows UI automation API
- `mss` - Rychlé screenshoty
- `pytest-timeout` - Timeout pro UI testy

## Spuštění vizuálních testů

### Lokálně (s grafickým displejem)

```bash
# Vypnout headless mode
$env:ESP32OS_HEADLESS="0"

# Spustit všechny vizuální testy
pytest test_visual_ui_real.py -v -s

# Spustit pokročilé testy s pywinauto
pytest test_visual_ui_advanced.py -v -s

# Spustit konkrétní test
pytest test_visual_ui_real.py::test_ui_designer_launches -v -s
```

### V CI/CD (automaticky přeskočeno)

Vizuální testy jsou automaticky přeskočeny v headless prostředí:

```python
pytestmark = pytest.mark.skipif(
    os.environ.get("ESP32OS_HEADLESS") == "1",
    reason="Visual UI tests require display"
)
```

## Dostupné vizuální testy

### test_visual_ui_real.py (PyAutoGUI)

1. **test_ui_designer_launches** - Spuštění aplikace
2. **test_ui_designer_creates_widget** - Vytvoření widgetu
3. **test_ui_designer_drag_drop** - Drag & drop funkčnost
4. **test_ui_designer_keyboard_shortcuts** - Klávesové zkratky
5. **test_ui_designer_menu_navigation** - Navigace v menu
6. **test_ui_designer_export_functionality** - Export funkcionalita

### test_visual_ui_advanced.py (PyWinAuto)

1. **test_window_launches_and_connects** - Připojení k oknu
2. **test_window_has_expected_controls** - Kontrola UI prvků
3. **test_load_design_file** - Načtení souboru
4. **test_window_resize** - Změna velikosti okna
5. **test_window_focus_and_activate** - Focus a aktivace

## Výstupy testů

Testy generují screenshoty pro vizuální ověření:

- `test_ui_launch.png` - Screenshot při spuštění
- `test_ui_widget_create.png` - Po vytvoření widgetu
- `test_ui_drag_drop.png` - Po drag&drop operaci
- `test_ui_menu.png` - Screenshot menu
- `test_ui_export.png` - Screenshot exportu

## Bezpečnostní opatření

### Timeouts

Všechny vizuální testy mají timeout:

```python
@pytest.mark.timeout(30)
def test_ui_designer_launches(ui_app):
    ...
```

### Cleanup

Aplikace jsou vždy ukončeny po testu:

```python
@pytest.fixture
def ui_app():
    app = UIDesignerApp()
    yield app
    app.close()  # Vždy zavře aplikaci
```

## Debugging

### Pomalé přehrávání

Pro ladění můžete zpomalit PyAutoGUI:

```python
pyautogui.PAUSE = 1.0  # 1 sekunda mezi akcemi
```

### Fail-safe

PyAutoGUI má fail-safe - přesuňte myš do levého horního rohu pro zastavení:

```python
pyautogui.FAILSAFE = True  # Výchozí
```

### Verbose výstup

```bash
pytest test_visual_ui_real.py -v -s --log-cli-level=DEBUG
```

## Rozšíření testů

### Přidání nového vizuálního testu

```python
@pytest.mark.timeout(40)
def test_my_new_feature(ui_app):
    """Test nové funkce"""
    assert ui_app.launch(), "Should launch"
    time.sleep(2)
    
    # Váš test kód
    pyautogui.click(100, 200)
    
    # Screenshot pro ověření
    screenshot = ui_app.screenshot()
    screenshot.save('test_my_feature.png')
```

### Použití PyWinAuto pro pokročilé scénáře

```python
def test_advanced_interaction(ui_window):
    """Test s PyWinAuto"""
    assert ui_window.launch()
    
    # Přístup ke konkrétním kontrolám
    button = ui_window.main_window.child_window(
        title="Add Widget",
        control_type="Button"
    )
    button.click()
```

## Známá omezení

1. **Vyžaduje grafický display** - Nelze spustit v Docker/CI bez X server
2. **Závislé na rozlišení** - Souřadnice mohou být různé na různých monitorech
3. **Pomalé** - Vizuální testy jsou 10-100x pomalejší než unit testy
4. **Nestabilní** - Mohou selhat kvůli timing issues

## Best Practices

1. ✅ Vždy používejte timeouts
2. ✅ Použijte `time.sleep()` pro stabilitu
3. ✅ Generujte screenshoty pro debugging
4. ✅ Testujte na různých rozlišeních
5. ✅ Používejte fixtures pro cleanup
6. ❌ Nepoužívejte pevné souřadnice (pokud možno)
7. ❌ Nespouštějte v CI bez grafického serveru
