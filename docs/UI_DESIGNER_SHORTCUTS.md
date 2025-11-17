# UI Designer Pro - Keyboard Shortcuts & Alignment Tools

## ✨ Nové funkce (17. listopadu 2025)

### 🎯 Alignment Tools (Zarovnání widgetů)

Vyber **2 nebo více widgetů** (Shift+Click) a použij alignment tlačítka v toolbaru:

| Tlačítko | Funkce | Popis |
|----------|--------|-------|
| **←** | Align Left | Zarovná všechny widgety doleva (podle prvního vybraného) |
| **↑** | Align Top | Zarovná všechny widgety nahoru |
| **↓** | Align Bottom | Zarovná všechny widgety dolů |
| **→** | Align Right | Zarovná všechny widgety doprava |
| **↔** | Center Horizontal | Vycentruje horizontálně |
| **↕** | Center Vertical | Vycentruje vertikálně |

**Tip:** První vybraný widget slouží jako reference pro zarovnání.

---

### 📐 Distribute Tools (Rovnoměrné rozložení)

Vyber **3 nebo více widgetů** a použij distribute tlačítka:

| Tlačítko | Funkce | Popis |
|----------|--------|-------|
| **H** | Distribute Horizontal | Rovnoměrně rozloží mezery mezi widgety horizontálně |
| **V** | Distribute Vertical | Rovnoměrně rozloží mezery mezi widgety vertikálně |

**Použití:**

1. Vyber první a poslední widget (definují rozsah)
2. Vyber i prostřední widgety
3. Klikni na H nebo V
4. Mezery mezi widgety budou automaticky vyrovnány

---

### ⌨️ Keyboard Shortcuts (Klávesové zkratky)

#### Základní operace

| Zkratka | Funkce |
|---------|--------|
| `Ctrl+S` | Uložit design do JSON |
| `Ctrl+Z` | Undo (vrátit poslední změnu) |
| `Ctrl+Y` | Redo (znovu provést změnu) |
| `Delete` | Smazat vybraný widget |

#### Copy/Paste

| Zkratka | Funkce |
|---------|--------|
| `Ctrl+C` | Kopírovat vybrané widgety |
| `Ctrl+V` | Vložit widgety (s offsetem 10,10) |
| `Ctrl+D` | Duplikovat vybrané widgety |
| `Ctrl+A` | Vybrat všechny widgety |

#### Pohyb widgetů (Nudge)

| Zkratka | Funkce |
|---------|--------|
| `←` | Posunout doleva o 1 pixel |
| `→` | Posunout doprava o 1 pixel |
| `↑` | Posunout nahoru o 1 pixel |
| `↓` | Posunout dolů o 1 pixel |
| `Shift+←/→/↑/↓` | Posunout o grid size (default 4px) |

**Tip:** Při držení Shift během drag posune widget jen v jedné ose (axis-lock).

---

### 🖱️ Multi-Selection (Výběr více widgetů)

| Akce | Popis |
|------|-------|
| **Click** | Vyber jeden widget |
| **Shift+Click** | Přidej/odeber widget z výběru |
| **Ctrl+A** | Vyber všechny widgety |
| **Click na prázdno** | Zruš výběr (pokud Shift není stisknutý) |

**Použití:**

1. Klikni na první widget
2. Drž Shift a klikej na další widgety
3. Použij alignment nebo distribute tools
4. Nebo kopíruj/přesuň všechny najednou

---

### 🎨 Widget Palette (Rychlé přidávání)

Levý panel obsahuje tlačítka pro rychlé přidání widgetů:

| Tlačítko | Widget | Výchozí velikost |
|----------|--------|------------------|
| **➕ Label** | Text label | 60×10 |
| **➕ Button** | Tlačítko | 50×12 |
| **➕ Box** | Prázdný box | 60×40 |
| **➕ Panel** | Panel s rámečkem | 60×40 |
| **➕ Progress** | Progress bar | 80×8 |
| **➕ Gauge** | Kruhový gauge | 20×30 |
| **➕ Checkbox** | Checkbox s textem | 60×10 |
| **➕ Slider** | Posuvník | 80×8 |

**Všechny widgety jsou automaticky:**

- Umístěny na střed canvas
- Vybrány pro okamžitou editaci
- Připraveny k přesunu/resize

---

### 🔧 Resize Handles (Úchyty pro změnu velikosti)

Každý vybraný widget má 8 resize handles:

```text
   nw    n    ne
    ●────●────●
    │         │
  w ●         ● e
    │         │
    ●────●────●
   sw    s    se
```

| Handle | Funkce |
|--------|--------|
| **nw, ne, sw, se** | Rohové - mění šířku i výšku |
| **n, s** | Horní/dolní - mění jen výšku |
| **w, e** | Levý/pravý - mění jen šířku |

**Kurzor se automaticky mění** podle handle pod myší.

---

### 📋 Properties Panel (Panel vlastností)

**Double-click** na widget otevře properties panel:

- **Text:** Upravit text widgetu
- **Position:** X, Y souřadnice
- **Size:** Width, Height
- **Enter** pro aplikaci změn

---

### 🎯 Grid & Snap

| Funkce | Popis |
|--------|-------|
| **Grid** checkbox | Zapne/vypne zobrazení mřížky (8px) |
| **Snap** checkbox | Zapne/vypne přichytávání k mřížce (4px) |

**Snap ovlivňuje:**

- Drag & drop widgetů
- Změnu velikosti (resize)
- Konverzi canvas → widget souřadnic

---

## 🚀 Workflow příklady

### Rychlé vytvoření menu

```text
1. Klikni "➕ Button" 3× (vytvoří 3 tlačítka)
2. Vyber všechny 3 (Shift+Click nebo Ctrl+A)
3. Klikni "←" (zarovná doleva)
4. Klikni "V" (rovnoměrně rozloží vertikálně)
5. Double-click na každé tlačítko a změň text
```

### Duplikace layoutu

```text
1. Vytvoř první panel s widgety
2. Vyber všechny widgety v panelu (Shift+Click)
3. Ctrl+D (duplikuj)
4. Přesuň duplikát na novou pozici
5. Uprav texty podle potřeby
```

### Pixel-perfect alignment

```text
1. Vytvoř widgety přibližně na správných místech
2. Vyber všechny v jedné řadě
3. "↑" (zarovnej top)
4. "H" (distribute horizontal)
5. Šipkami (←→↑↓) dolaď pozici po pixelech
```

---

## 🎨 Tipy & triky

### Multi-selection mastery

- **Shift+Click:** Přidej widget do výběru
- **Shift+Click znovu:** Odeber z výběru
- **Ctrl+A:** Vyber všechny
- **Click na prázdno:** Vymaž výběr

### Rychlé zarovnání

- První vybraný widget = reference
- Ostatní se zarovnají k němu
- Funkuje i s 10+ widgety najednou

### Distribute spacing

- Vždycky vyber **minimálně 3 widgety**
- První a poslední definují rozsah
- Prostřední jsou rovnoměrně rozloženy

### Axis-lock drag

- Drž **Shift během drag**
- Widget se pohybuje jen v ose, kde je větší pohyb myši
- Ideální pro přesné horizontální/vertikální zarovnání

### Grid snap sizing

- **Shift+šipky** = posun o grid_size (4px)
- **Normální šipky** = posun o 1px
- Kombinuj pro rychlé i přesné umístění

---

## 🐛 Troubleshooting

### Alignment nefunguje

- ✅ Zkontroluj, že máš vybrané **alespoň 2 widgety**
- ✅ Použij Shift+Click pro multi-selection

### Distribute nefunguje

- ✅ Potřebuješ **minimálně 3 widgety**
- ✅ Musí být dostatečná mezera mezi prvním a posledním

### Widget "skáče" při drag

- ✅ Vypni **Snap** checkbox
- ✅ Nebo uprav `snap_size` v nastavení (default 4px)

### Undo nevrací správnou pozici

- ✅ Undo/Redo funguje po `_save_state()`
- ✅ Automaticky voláno při mouse_up, resize_end, atd.

---

## 📊 Performance

- **Multi-selection:** Bez limitu widgetů
- **Copy/Paste:** Instant i pro 50+ widgetů
- **Alignment:** < 1ms i pro velké výběry
- **Distribute:** O(n log n) kvůli sortování

---

**Vytvořeno:** 17. listopadu 2025  
**Verze:** 1.0.0  
**Autor:** ESP32OS Team
