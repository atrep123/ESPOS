# UI Designer Pro - Changelog

## [1.2.0] - 2025-11-17

### ✨ Animation Timeline Editor

#### Timeline Window

- **AnimationEditorWindow** - Standalone editor for animation management
- **Timeline canvas** - Visual representation with keyframe markers
- **Easing curve preview** - Real-time visualization of easing functions
- **Properties panel** - Configure type, duration, easing, loop
- **Playback controls** - Play, pause, stop with preview integration

#### Keyframe System

- **Click to add** - Click timeline to create keyframe at position
- **Drag to move** - Drag keyframe markers to new time positions
- **Right-click to delete** - Remove keyframes with context menu
- **Visual markers** - Color-coded keyframe indicators (red circles)
- **Time labels** - 0%, 25%, 50%, 75%, 100% markers on timeline

#### Animation Management

- **➕ Create animations** - Dialog for new animation with custom name
- **🗑️ Delete animations** - Remove with confirmation dialog
- **Load properties** - Auto-populate UI from selected animation
- **Apply changes** - Save modifications to animation config
- **Sync with main window** - Updates reflected in preview dropdown

#### Easing Visualization

- **200x150px canvas** - Dedicated easing curve preview
- **6 easing functions** - linear, ease_in, ease_out, ease_in_out, quad variants
- **Grid overlay** - 25% interval reference lines
- **Labeled axes** - Time (x) and Progress (y) labels
- **Real-time update** - Curve updates on easing selection

#### Integration

- **✏ Edit button** - Opens timeline editor from preview toolbar
- **Preview sync** - Play/pause/stop controls affect main window
- **Widget selection** - Animations apply to selected widget
- **State persistence** - Window singleton pattern prevents duplicates

### 🧪 Testing

- **11 test cases** - Complete coverage of animation features
- **MockPreviewWindow** - Testing without Tkinter dependencies
- **Animation CRUD** - Create, read, update, delete operations
- **Keyframe operations** - Add, move, delete keyframe tests
- **Easing functions** - All 6 easing curves validated
- **Timeline rendering** - Canvas drawing and marker positioning

## [1.1.0] - 2025-11-17

### ✨ Nové funkce

#### Alignment Tools

- **6 alignment tlačítek** v toolbaru: Left, Right, Top, Bottom, Center H, Center V
- Zarovnání funguje na **2+ vybraných widgetech**
- První vybraný widget slouží jako reference
- Podporuje i velké množství widgetů (50+)

#### Distribute Tools

- **Horizontal & Vertical distribution** - rovnoměrné rozložení mezer
- Vyžaduje **minimálně 3 vybrané widgety**
- První a poslední widget definují rozsah
- Prostřední widgety jsou rovnoměrně rozloženy

#### Multi-Selection

- **Shift+Click** - přidání/odebrání widgetu z výběru
- **Ctrl+A** - výběr všech widgetů
- **Visual feedback** - všechny vybrané widgety zvýrazněny
- Click na prázdné místo ruší výběr (pokud Shift není stisknutý)

#### Copy/Paste System

- **Ctrl+C** - kopírovat vybrané widgety do clipboardu
- **Ctrl+V** - vložit widgety s offsetem (10,10)
- **Ctrl+D** - duplikovat vybrané widgety (zkratka pro Ctrl+C + Ctrl+V)
- Deep copy zajišťuje nezávislost kopií

#### Keyboard Shortcuts

- **Arrow keys** - posun widgetu o 1 pixel
- **Shift+Arrows** - posun o grid size (4px)
- **Axis-lock drag** - Shift během drag = pohyb jen v jedné ose
- **Ctrl+Z/Y** - Undo/Redo (již existovalo, ale nyní integrováno)
- **Delete** - smazání vybraného widgetu

#### Widget Palette

- **8 tlačítek** pro rychlé přidání widgetů:
  - Label, Button, Box, Panel
  - ProgressBar, Gauge, Checkbox, Slider
- Nové widgety jsou **automaticky centrovány** na canvas
- Automaticky **vybrány** pro okamžitou editaci
- Defaultní rozměry optimalizovány pro každý typ

### 🔧 Vylepšení

#### Drag & Drop

- **Shift during drag** aktivuje axis-lock
- Widget se pohybuje jen v ose s větším pohybem myši
- Ideální pro přesné horizontální/vertikální umístění

#### Selection Handles

- Vylepšený vizuál resize handles
- 8 handles: 4 rohy + 4 strany
- Kurzor se mění podle handle typu

#### Status Bar

- Zobrazuje počet vybraných widgetů
- Info o copy/paste operacích
- Pozice a velikost vybraného widgetu

### 📚 Dokumentace

#### Nové soubory

- `docs/UI_DESIGNER_SHORTCUTS.md` - kompletní průvodce klávesovými zkratkami
- `test_ui_designer_alignment.py` - 6 testů pro nové funkce

#### Aktualizace

- README s odkazy na novou dokumentaci
- Příklady workflow pro běžné úkoly
- Troubleshooting sekce

### 🧪 Testování

#### Nové testy

- `test_alignment_tools()` - zarovnání widgetů
- `test_distribution()` - rovnoměrné rozložení
- `test_copy_paste()` - kopírování a vkládání
- `test_multi_selection()` - výběr více widgetů
- `test_undo_redo_exists()` - undo/redo mechanismus
- `test_nudge_with_grid()` - posun šipkami

### Výsledky testování

Všechny testy prošly: 6/6 ✅

### 🎨 UI Změny

#### Toolbar

- Nová sekce **"Align:"** s 6 tlačítky
- Nová sekce **"Distribute:"** s 2 tlačítky
- Visual separátory mezi sekcemi

#### Properties Panel

- Nyní v samostatném okně (Toplevel)
- Možnost nechat otevřený při práci

#### Canvas

- Vylepšené zobrazení multi-selection
- Handles jen pro primárně vybraný widget
- Grid a snap fungují i pro multi-selection drag

### 🐛 Opravy

- **Widget creation** - správné centrování nových widgetů
- **Drag offset** - fix smooth dragging z libovolného bodu
- **Multi-drag** - všechny vybrané widgety se pohybují současně
- **Clipboard isolation** - deep copy předchází nechtěným vazbám

### 📊 Performance

- **Alignment:** < 1ms i pro 50+ widgetů
- **Distribution:** O(n log n) díky efektivnímu sortování
- **Copy/Paste:** Instant i pro velké množství
- **Multi-selection:** Bez limitu počtu widgetů

### 🔄 Zpětná kompatibilita

- ✅ Všechny staré JSON designs se načtou bez problémů
- ✅ Single-selection workflow zůstal identický
- ✅ Export do PNG/JSON/HTML funguje stejně
- ✅ CLI parametry nezměněny

### 📦 Závislosti

**Žádné nové závislosti!** Všechny nové funkce používají:

- Tkinter (už bylo)
- PIL/Pillow (už bylo)
- Standard library (copy, dataclasses)

---

## [1.0.0] - 2025-11-15

### Původní release

- Visual preview window s Tkinter
- Drag & drop widgetů
- Resize handles
- Grid & snap
- Properties panel
- Export PNG, JSON, HTML
- Animation preview
- Widget palette základní verze

---

## Statistiky

### Kódová báze

- **Nových řádků:** ~300
- **Nových metod:** 7
- **Nových testů:** 6
- **Nových dokumentů:** 1

### Features matrix

| Feature | v1.0 | v1.1 |
|---------|------|------|
| Single selection | ✅ | ✅ |
| Multi-selection | ❌ | ✅ |
| Drag & drop | ✅ | ✅ |
| Axis-lock drag | ❌ | ✅ |
| Resize handles | ✅ | ✅ |
| Alignment tools | ❌ | ✅ |
| Distribution | ❌ | ✅ |
| Copy/Paste | ❌ | ✅ |
| Duplicate | ❌ | ✅ |
| Select all | ❌ | ✅ |
| Arrow keys nudge | ❌ | ✅ |
| Undo/Redo | ✅ | ✅ |
| Widget palette | ⚠️ | ✅ |
| Properties panel | ✅ | ✅ |
| Grid/Snap | ✅ | ✅ |
| Export PNG | ✅ | ✅ |
| Animation preview | ✅ | ✅ |

- ⚠️ = částečná implementace  
✅ = plně funkční

---

## Roadmap

### v1.2 (plánováno)

- [ ] Group/Ungroup widgetů
- [ ] Lock/Unlock widgetů
- [ ] Smart alignment guides
- [ ] Ruler & measurements
- [ ] Z-index management

### v1.3 (návrh)

- [ ] Template system
- [ ] Keyboard macro recording
- [ ] Batch operations
- [ ] Find & Replace
- [ ] Style brush (copy styling)

### v2.0 (budoucnost)

- [ ] Layer panel
- [ ] History viewer
- [ ] Plugin system
- [ ] Collaborative editing
- [ ] Cloud sync

---

**Kompletní dokumentaci najdeš v:**

- `docs/UI_DESIGNER_SHORTCUTS.md` - keyboard shortcuts
- `UI_DESIGNER_PRO_README.md` - celkový přehled
- `UI_DESIGNER_GUIDE.md` - tutorial
