# 🚀 Jak spustit Designer - Rychlý návod

## ✅ Doporučený způsob (Python verze):

```bash
# Nejjednodušší - Workspace launcher
python esp32os_workspace.py
# → Klikni "🎨 UI Designer" nebo "🔗 Oba"

# Nebo přímo Designer
python ui_designer_pro.py
```

**Proč Python verze?**
- ✅ Okamžitě funguje (bez buildu)
- ✅ Vidíš chybové hlášky v terminálu
- ✅ Rychlejší start
- ✅ Žádné problémy s moduly

---

## 💿 .exe verze (jen pokud chceš distribuovat):

### Pokud máš chybu "_socket not found":

```bash
# Rebuild .exe s opravenou spec
pyinstaller build/ui_designer_pro.spec --clean
```

Nový .exe bude v: `dist/ui_designer_pro.exe`

### Kdy použít .exe:
- ❌ **NE** pro běžnou práci/vývoj
- ✅ Když chceš poslat aplikaci někomu bez Pythonu
- ✅ Pro finální distribuci projektu

---

## 🔧 Když něco nejde:

### "ModuleNotFoundError"
```bash
pip install pillow websockets reportlab watchdog
```

### "Tkinter nefunguje"
```bash
# Pro testování bez GUI:
set ESP32OS_HEADLESS=1
python ui_designer_pro.py
```

### Designer se nespustí
```bash
# Zkus workspace launcher místo toho:
python esp32os_workspace.py
```

---

## 💡 Doporučení:

**Pro běžnou práci:** `python esp32os_workspace.py` (Workspace)

**Pro vývoj:** `python ui_designer_pro.py` (Designer přímo)

**Pro distribuci:** `dist/ui_designer_pro.exe` (Build)

---

✅ **TL;DR:** Použij `python esp32os_workspace.py` - je to nejjednodušší!
