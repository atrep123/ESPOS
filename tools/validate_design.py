#!/usr/bin/env python3
"""
Validate ESP32OS UI design JSON — comprehensive 151-rule checker.

Covers:
- required fields + basic types
- supported widget types (exportable to `UiWidget` in `src/ui_scene.h`)
- geometry sanity (within scene bounds, integer coords, positive dims, uint16 overflow)
- duplicate widget IDs, ID format
- text overflow (horizontal + vertical), min text height/width, text length
- value range sanity (gauge, slider, progressbar)
- value field type checks + firmware int16 overflow
- border consistency (border=True needs visible border_style, double border min size)
- color parseability, visibility, and contrast
- minimum widget sizes for gauge/slider/progressbar/checkbox/radiobutton/slider-height
- z_index type, runtime format + key validation, edge margins
- widget overlap detection
- empty text without runtime binding, invisible widget with runtime
- font charset compliance
- style field validation
- chart data_points validation
- icon widget requires icon_char
- non-negative padding/margin
- excessive widget count per scene
- scene name validation, animations field type
- locked field type, state_overrides structure
- scene dimension limits, textbox min size, panel border recommendation
- constraints & responsive_rules type, align-border, widget ID length
- font_size / corner_radius / border_width type, border_color parseability
- mostly-outside-scene detection, bold field type, duplicate geometry, disabled+no-runtime
- device profiles: every display-dependent number (font metrics, charset,
  contrast model, widget budget, edge margin, touch minimum) comes from the
  panel the design is drawn for, not from the 256x128 OLED it was written on
- collision detection announces when it skipped a scene instead of staying
  silent about it
- near-miss alignment: left edges 1-3 px apart are a typed coordinate that
  missed, not a design decision
- touch targets measured in millimetres: 44 px is 9.3 mm at 120 PPI and
  3.8 mm at 294 PPI
- measured data from the artboard (scene block "navrh", carried by the kit
  bridge): elements clipped by their own parent or by a reserved band, text
  overflow measured with the REAL font instead of a character estimate, value
  roles that promise a reading and deliver none, a dash standing in for a
  sentence, grid capacity against the number of items to place, firmware DPI
  against panel PPI, machine names inside sentences written for a human, and
  one vocabulary per thing across screens
- what the box really did to the text: content actually clipped by its own
  clip box (a DIFFERENT quantity from the declared cell above - a text can
  overflow the column it was budgeted and still be clipped by nothing), and
  text that wrapped into more lines than there was room for
- the design language itself: dark ink belongs on the light enamel it is
  drawn on, and a divider must not run through the glyphs of a sentence
  (both gated by the panel profile - they are TabOS laws, not properties
  of a piece of glass)
- typography, colour and the indentation system: a type size outside the
  binding scale of roles, a glyph whose ANGULAR height falls under what an
  eye resolves at the reading distance (the profile carries PPI and the
  distance, so the same 14 px passes on one panel and fails on another),
  a colour that is not in the palette, and text glued to the frame instead
  of sitting on the mandatory indent

Usage:
  python tools/validate_design.py main_scene.json
  python tools/validate_design.py main_scene.json --warnings-as-errors
    python tools/validate_design.py main_scene.json --strict-critical
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_PATH = REPO_ROOT / "schemas" / "ui_design.schema.json"

from tools.ui_codegen import WIDGET_TYPE_MAP

# ── Enum sets ──────────────────────────────────────────────────────────────
ALLOWED_BORDER_STYLES = {"none", "", "single", "double", "rounded", "bold", "dashed"}
ALLOWED_ALIGN = {"left", "center", "right"}
ALLOWED_VALIGN = {"top", "middle", "bottom"}
ALLOWED_OVERFLOW = {"ellipsis", "wrap", "clip", "auto"}
ALLOWED_STYLES = {"", "default", "bold", "inverse", "highlight", "bar", "line"}

# Widget types that carry visible text and need overflow checks
TEXT_TYPES = {"label", "button", "checkbox", "textbox", "radiobutton"}

# Widget types that carry value/min/max fields
VALUE_TYPES = {"gauge", "progressbar", "slider"}

# Focusable types in firmware (ui_nav.c)
FOCUSABLE_TYPES = {
    "button",
    "checkbox",
    "radiobutton",
    "slider",
    "list",
    "toggle",
    "gauge",
    "progressbar",
}

# Valid constraint dict keys (ui_models.py Constraints TypedDict)
ALLOWED_CONSTRAINT_KEYS = {"b", "ax", "ay", "sx", "sy", "mx", "my", "mr", "mb"}

# Valid runtime meta keys (ui_meta.c ui_meta_parse)
ALLOWED_RUNTIME_META_KEYS = {
    "bind",
    "key",
    "kind",
    "type",
    "min",
    "max",
    "step",
    "values",
    "suffix",
    "unit",
    "prefix",
    "precision",
    "decimals",
    "scale",
    "divisor",
}

# Valid runtime kind values (must match parse_kind() in ui_meta.c)
ALLOWED_RUNTIME_KINDS = {"bool", "int", "enum", "str", "float"}

# Runtime keys whose values must be numeric (int or float)
NUMERIC_RUNTIME_KEYS = {"min", "max", "step", "precision", "decimals", "scale", "divisor"}

# ── Rendering constants (must match drawing.py / firmware) ──────────────
CHAR_W = 6  # font6x8 char width
CHAR_H = 8  # font6x8 char height
RENDER_PAD = 2  # per-side padding (clip_rect = rect.inflate(-4, -4))
MIN_TEXT_H = RENDER_PAD * 2 + CHAR_H  # 12 — minimum for 1 text line

# Firmware field limits (must match uint16_t / int16_t in ui_scene.h)
INT16_MIN = -32768
INT16_MAX = 32767
UINT16_MAX = 65535
MAX_WIDGETS_PER_SCENE = 64  # soft limit; ESP32 memory pressure
HARD_WIDGET_LIMIT = 256  # hard cap; skip O(n²) checks above this
MIN_WIDGET_GAP_PX = 1  # minimum pixel gap between non-grouped widgets
MAX_JSON_FILE_SIZE = 10 * 1024 * 1024  # 10 MB guard for resource exhaustion
MAX_TEXT_LEN = 127  # practical limit for OLED readability

# Valid widget ID pattern: letters, digits, underscore, hyphen, dot
_WIDGET_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
_SCENE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RUNTIME_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

# Supported characters in font6x8 (lowercase auto-mapped to uppercase)
FONT_CHARS = set(" .:_-/%?+<>!=(),#*0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# ── Color helpers ──────────────────────────────────────────────────────────
_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}
MIN_VISIBLE_BRIGHTNESS = 0x20  # ~12 % — anything below is unreadable on OLED
MIN_CONTRAST = 40  # min brightness delta between fg and bg
MIN_EDGE_MARGIN = 2  # px from screen edge for non-full-span widgets

# Warning text fragments promoted to ERROR when strict_critical=True.
#
# NOTE on overlap: a bare "overlap" marker is intentionally NOT listed here.
# Overlap is not inherently a defect — this UI model composites by widget
# array / draw order (every widget is z_index=0; there is no separate z plane),
# so a background/container ``panel``/``box`` drawn behind its own content, and
# a deliberately hidden (``visible:false``) toast overlay positioned over the
# hint/status band, are *legitimate, intentional* layering. Promoting every
# such overlap to a build-failing ERROR under --strict-critical made the gate
# dishonest: it failed on correct-by-design scenes. Only the genuine broken
# case — two *visible, non-container* widgets partially colliding — is a real
# layout defect, and it is flagged with the specific marker below (emitted by
# Rule 21 / Rule 105 via ``_overlap_is_benign``). See ``_overlap_is_benign``.
OVERLAP_COLLISION_MARKER = "overlap (visible content collision)"
CRITICAL_WARNING_MARKERS = (
    OVERLAP_COLLISION_MARKER,
    "too short for text",
    "too short to render text",
    "too narrow for text",
    "low contrast",
    "too dim",
    "fully outside scene",
    "outside scene bounds",
)

# Widget types that act as backdrop / container frames. When one of these
# fully contains the other widget in an overlapping pair, the overlap is the
# intended "panel behind its content" composition, not a collision defect.
CONTAINER_WIDGET_TYPES = {"panel", "box"}

# Widget types a finger actually has to hit. Size limits below apply to these.
TOUCH_WIDGET_TYPES = {"button", "checkbox", "radiobutton", "slider", "textbox"}

# ── Blok "navrh": merena data z artboardu (most tabos-ui-kit -> ESPOS) ──────
#
# Nektere vady se z holych souradnic widgetu poznat NEDAJI: ze scena rekne
# "stitek 388x24, text 'V0.4-71-gee91351-dirty'" nikdo nevyctete, jestli se
# ten text do stitku vejde - zalezi na skutecnem fontu, ne na odhadu z poctu
# znaku (Rule 7). A ze dlazdice presahuje svuj kontejner nebo leze do patky
# neni videt, dokud scena nenese, KDO je jeji rodic. Tahle mereni delaji
# generatory a most (headless Chrome nad artboardem) a vozi je sem.
#
# Nosic je JEDEN SCENOVY KLIC "navrh", ne nova pole widgetu. Duvod je tvrdy:
# widget ma ve schematu "additionalProperties": false a je obousmerne svazany
# s `ui_models.WidgetConfig` (tests/test_schema_sync.py), takze nove pole
# widgetu by `asdict` vysypal do KAZDEHO ulozeneho navrhu. Scena ma
# "additionalProperties": true - blok je tam zadarmo a nikoho dalsiho se
# netyka.
#
# Tvar (vsechny klice nepovinne):
#   "navrh": {
#     "pasy":  {"razitko": [x, y, sirka, vyska]},
#     "prvky": {"<_widget_id>": {"rodic": [x, y, sirka, vyska],
#                                "pas": "razitko",
#                                "sirka_textu": 402.7,
#                                "sirka_bunky": 388.0}}
#   }
#
# Kdyz blok CHYBI, pravidla nad nim MLCI - a je to zamer, ne diera: dokument,
# ktery si editor stavi sam, merena data z prohlizece legitimne nema, a
# poctivost patri tam, kde mereni vznika (most `do_espos.py` je fail-closed
# a scenu bez mereni nevyda). Kdyz blok JE, ale je vadny, rekne se to NAHLAS:
# preklep v datech nesmi pravidlo tise vypnout.
NAVRH_KLIC = "navrh"

# Druh listu. Artboard je bud OBRAZOVKA (co bude na skle pristroje), nebo
# VYKLAD o navrhu (rozvrzeni ramce, slovnik smaltu, stavova karta, hlaseni
# "dnes na zarizeni"). Rozdil neni kosmeticky: jazykovy zakon F4 mluvi
# o textu NA PRISTROJI, kdezto vyklad o vade tu vadu CITUJE - veta
# "V ceske sestave patri carka; %.1f ji neda." je spravne napsany vyklad,
# ne poruseni zakona. Bez tohohle rozliseni hlasila brana na 62 listech
# osm nalezu na ctyrech vykladovych listech (Main, Dnes, FilesStavy,
# SvorkaJazyk) a vsechny byly citace.
#
# Rozhoduje GENERATOR atributem `data-list` na korenu listu; chybejici
# atribut znamena obrazovka, tedy dnesni chovani (mereni). Ticho neni
# neviditelne: na vykladovem listu se ohlasi jednou `ZNACKA_R142_VYKLAD`
# (WARN), takze v souhrnu brany je videt, ze se pravidlo NEMERILO.
DRUHY_LISTU = ("obrazovka", "vyklad")

# Pevne ASCII znacky hlasek. Most si je bere behovou hodnotou z tohohle
# modulu (`vd.ZNACKA_R136_RODIC`), aby se trideni nalezu v kitu nemohlo
# rozejit s textem, ktery brana skutecne vydava.
ZNACKA_NAVRH_VADNY = "vadny blok navrh"
ZNACKA_R136_RODIC = "presahuje sveho rodice"
ZNACKA_R136_PAS = "zasahuje do pasu"
ZNACKA_R136_PAS_VEN = "vycniva ze sveho pasu"
ZNACKA_R136_OZNACENI = "oznaceni zamerneho presahu"
ZNACKA_R137 = "text pretece bunku"
ZNACKA_R137_NEMERENO = "preteceni textu se NEMERILO"
ZNACKA_R138 = "prazdny smalt"
ZNACKA_R138_OZNACENI = "oznaceni zamerne prazdneho"
ZNACKA_R139 = "pomlcka misto hodnoty"
ZNACKA_R139_ZASTUPNY = "zastupny znak misto hodnoty"
ZNACKA_R140 = "mrizka nepojme vsechny polozky"
ZNACKA_R140_NEMERENO = "kapacita mrizky se NEMERILA"
ZNACKA_R141 = "DPI firmwaru nesouhlasi"
ZNACKA_R141_NEMERENO = "DPI firmwaru nezmereno"
ZNACKA_R141_ODCHYLKA = "DPI firmwaru je vedoma odchylka"
ZNACKA_R142 = "veta pro cloveka"
ZNACKA_R142_NEMERENO = "jmena SDK nedodana"
ZNACKA_R142_VYKLAD = "list je vyklad o navrhu"
ZNACKA_R143 = "jiny stav teze veci"
ZNACKA_R143_NEMERENO = "slovnik stavu chybi"
ZNACKA_R143_ROLE_NEMERENO = "slovnik stavu: zadny prvek s roli stav"
# Prurez listu (cista funkce `slovnik_prurez`; vola ji most nad VSEMI
# scenami najednou, validator sam vidi jen jeden dokument): dva listy
# tvrdi o teze veci dva ruzne stavy ze slovniku, a vec ze slovniku,
# o ktere zadny list netvrdi STAV (zavora per-VEC, ne per-list).
ZNACKA_R143_PRUREZ = "listy si odporuji o stavu teze veci"
ZNACKA_R143_VEC_NEMERENO = "slovnik stavu: vec bez jedineho tvrzeni"
ZNACKA_R144 = "text oriznuty schrankou"
ZNACKA_R145 = "text pretekl dolu"
ZNACKA_R146 = "cizi text na smaltu"
ZNACKA_R147 = "delici cara pres text"
ZNACKA_R148 = "rez pisma mimo skalu"
ZNACKA_R148_NEMERENO = "zavazna skala pisma nedodana"
ZNACKA_R148_ODCHYLKA = "rez pisma je jmenovita vyjimka"
ZNACKA_R149 = "znak pod mezi citelnosti"
ZNACKA_R150 = "barva mimo paletu"
ZNACKA_R150_NEMERENO = "paleta navrhu nedodana"
ZNACKA_R150_ODCHYLKA = "list ma vlastni paletu"
ZNACKA_R151 = "text se lepi na ram"
ZNACKA_R151_NEMERENO = "soustava odsazeni nedodana"
# Rule 152: mrizka, kterou artboard NAKRESLIL (sest a vic stejnych prvku
# teze tridy srovnanych do radku a sloupcu), ale NEDEKLAROVAL
# (`navrh.mrizky` bez zaznamu tehoz jmena). Rule 140 nad ni nema co merit
# a jeji ticho vypadalo jako zelena - viz `_r152_nalezy`.
ZNACKA_R152_NEMERENO = "mrizka bez kapacity"
# Rule 17: neaktivni ovladac je z kontrastu VYNATY (WCAG 2.1, 1.4.3). Ticho
# ale musi byt VIDET, jinak se vyjimka neda odlisit od zmereneho "v poradku"
# - hlasi se proto tehdy (a jen tehdy), kdyz opravdu neco vyjmula.
ZNACKA_R17_NEAKTIVNI = "neaktivni ovladac mimo kontrast"

# R136: most zaokrouhluje OBE hrany obdelniku zvlast (viz komentar v
# `do_espos.MERIC`: zaokrouhlovani hrany a SIRKY zvlast vyrobilo jedenact
# fantomovych prekryvu o 1 px na jednom listu). Jednopixelovy rozdil je
# proto artefakt mereni, ne vada; hlasi se od 1 px vys.
R136_PRAH_PX = 1
# R137: Chrome pocita v 1/64 px a `Range.getClientRects()` vraci subpixely,
# takze rovnost se nikdy netrefi presne. Pul pixelu je pod rozlisenim oka
# i panelu.
R137_TOLERANCE_PX = 0.5

# R144/R145: `scrollWidth`/`clientWidth` (a jejich svisle protejsky) vraci
# Chrome jako CELA cisla - zaokrouhluje se v nich subpixelova sirka obsahu
# nahoru a subpixelova sirka schranky dolu, takze rozdil 1 px umi vzniknout
# i u textu, ktery se vejde presne. Hlasi se proto od 2 px vys. Je to tataz
# mez, jakou mel merid kitu (`zmer_prekryv.py`: `sw > cw + 1`) a nad 62
# listy s ni nevznikl ani jeden nalez - tedy ani jeden falesny.
# Ctyri rozmery jednoho odectu: kolik obsahu prvek MA a kolik ho je VIDET.
# Jmena jsou ceska schvalne - je to smlouva mezi generatorem a branou, ne
# jmena z DOM API.
OREZ_KLICE = ("sirka_obsahu", "sirka_schranky", "vyska_obsahu", "vyska_schranky")
R144_PRAH_PX = 2
R145_PRAH_PX = 2
# R146: dotek neni prekryv. Most zaokrouhluje obe hrany obdelniku zvlast
# (tataz uvaha jako u `R136_PRAH_PX`), takze prekryv pod 1 px je artefakt
# mereni, ne inkoust lezici na smaltu.
R146_PRAH_PX = 1
# R147: cara musi lezet UVNITR inkoustu, ne se ho dotknout. Scena nese
# u popisku rozsah INKOUSTU (viz `do_espos.inkoust`), takze "cara protina
# text" znamena doslova "cara jde pres glyfy".
R147_ODSTUP_PX = 1

# ── Rule 17, rozsireni o mez velkeho textu (WCAG 2.1 AA, 1.4.3) ──
# Norma ma DVE meze, ne jednu: bezny text 4,5:1 a "velky" text 3,0:1, kde
# velky znamena 24 px a vic, nebo 19 px a vic pri tucnem rezu (norma mluvi
# o 18,66 px = 14 bodu tucne; 19 px je totez cislo zaokrouhlene nahoru,
# tedy PRISNEJI). Do 9. 9. 2026 tu byla jen mez 4,5 pro vsechno, takze
# velky titulek na hrane dostaval falesny poplach - a falesny poplach je
# horsi nez zadny, protoze se na branu prestane koukat.
WCAG_VELKY_PX = 24.0
WCAG_TUCNE_PX = 19.0

# ── Rule 149: uhlova velikost znaku ──
# Meze nejsou z tohohle projektu a to je jejich smysl. Mez, ktera prijde
# zevnitr, popisuje jen to, co uz mame.
#   ~1'  rozliseni dvou car u zdraveho oka (Snellen 20/20) - na TEHLE mezi
#        se veci prekryvaji: tusim, ze tam neco je, nerozeznam co.
#   ~3'  spolehlive rozpoznani TVARU glyfu.
#   ~5'  pohodlne pri letmem pohledu, bez zaostrovani.
#   16'  ISO 9241-303, minimalni uhlova vyska ZNAKU (doporuceni 20-22').
#
# GATUJE SE NA 5' (WARN) a 3' (ERROR), NE NA ISO, a je poctive rict proc:
# na 450 mm zada ISO rez 35 px, kdezto bezna hodnota TabOSu ma 20 px
# (58 % meze), popisek 16 px (46 %) a patka 14 px (40 %). Pravidlo na 16'
# by vystrelilo na VSECH 3751 textech kitu a tim by neomerilo nic -
# vzdalenost od ISO je rozhodnuti o OBSAHU (pri 35 px padne sloupec z 26
# radku na 14), ne vada rozvrzeni, a majitel ho uz jednou ucinil
# (`tokens.json: _pozn_typografie._vyhrada_iso`). ISO mez proto tenhle
# modul zna, pocita a pise do hlasky jako procento - ale nesoudi podle ni.
R149_MEZ_DETEKCE = 1.0
R149_MEZ_TVAR = 3.0
R149_MEZ_LETMO = 5.0
R149_MEZ_ISO = 16.0

# Role prvku: co ta plocha SLIBUJE. Hodnotova role slibuje sdeleni ("jaky
# port", "kolik", "jaky stav"), popiskova role je jen navesti nad cizim
# sdelenim. Rule 138 a Rule 139 meri jen sliby: prazdny nadpis vada neni a
# pomlcka mezi cisly rozsahu taky ne. Roli vozi generator (`data-role`
# v kitu) - scena sama nese jen obdelniky a texty, o slibech nevi nic.
# `stav` je UZSI slib nez `hodnota`: prvek netvrdi jen "tady bude sdeleni",
# ale "tady stoji STAV teto veci". Rozdil je mericí, ne slovickareni -
# pravidlo 143 se pta, jestli je ten stav ze slovniku, a "28,4 GB volno"
# nebo "NERTERA" zadny stav netvrdi (je to hodnota O veci). Do 9. 9. 2026
# meril slovnik kazdou hodnotu s `data-vec` a mel na 62 listech deset
# nalezu, z nichz ZADNY nebyl vada, kterou hleda.
ROLE_STAV = "stav"
ROLE_HODNOTY = frozenset({"hodnota", "smalt", "stitek", "cislo", ROLE_STAV})
ROLE_POPISKU = frozenset({"popisek", "patka", "titulek"})
ROLE_ZNAME = ROLE_HODNOTY | ROLE_POPISKU

# R139: vsechny tvary, kterymi se na panelu psalo "nic nevim". Jen tyhle
# JEDNOZNAKOVE tvary a jen jako CELY text; "1-13" se nehlasi (viz
# `_r139_nalezy`).
#
# U+2010 HYPHEN a U+2011 NON-BREAKING HYPHEN doplneny 2026-09-09: mnozina
# zacinala az u U+2012, takze "obycejna" typograficka pomlcka prosla mlckym
# a byla to jedina znama dira, kterou se dalo napsat "nic nevim" tvarem,
# ktery vypada uplne stejne jako U+2013.
POMLCKY = frozenset(
    {"-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"}
)

# Nulove sirky. `strip()` je NEODSTRANI (nejsou to bile znaky), takze prvek
# s U+200B vypada prazdne, ale Rule 138 na nej nesahne - a Rule 139 by ho
# taky nechala byt, protoze v POMLCKY neni. Byl to jediny znamy tvar, ktery
# obchazel OBE pravidla naraz.
NULOVE_SIRKY = "\u200b\u200c\u200d\ufeff\u2060"

# Zastupne znaky: "nic nevim" napsane necim jinym nez pomlckou. Tataz vada
# jako pomlcka (ctenar z toho nepozna, jestli se veci nikdo neptal, jestli
# odpoved nedosla, nebo jestli je vysledek prazdny), proto stejna hlaska
# a stejna zavaznost - jen jine pojmenovani, aby se opravovalo to, co tam
# doopravdy stoji. Porovnava se CELY text po `strip()` a bez ohledu na
# velikost pismen ("n/a" i "N/A").
ZASTUPNE = frozenset({"\u2022", "\u2026", "...", "?", "??", "n/a", "--", "---", "\u2014\u2014"})

# ── Rule 142: co ve vete pro cloveka byt nesmi ─────────────────────────────
#
# Sedm tvaru, u kterych je odpoved ano/ne a nezalezi na vkusu. Vzory jsou
# BYTE-IDENTICKE s `tabos-core/tools/brana_vety.py` (zakon F4, charta
# docs/CHARTA_JAZYKA_VET.md) a jsou VEREJNE schvalne: kit si je bere behovou
# hodnotou a porovnava obe brany proti sobe. Opsana kopie vzoru by se
# s originalem drive nebo pozdeji rozesla a jedna z bran by pak mlcela prave
# o tom, co druha hlasi.
#
# Delba prace mezi obema branami: `brana_vety.py` cte ZDROJ (retezcove
# literaly uvnitr znamych vyusteni), ESPOS cte SCENU (hotovy text na plose).
# Z toho plynou presne dva rozdily a oba jsou napsane u sveho vzoru nize.

# Jmeno v kodu: `tabos::ui::znacka`, `ISystemMetrics::radioTemp`.
_V_SCOPE = re.compile(r"::")
# Jmeno hlavicky: `smalt.h`, `data_source.hpp`. Prava tecka pred priponou.
_V_HLAVICKA = re.compile(r"\b[A-Za-z_][\w./\\-]*\.(?:h|hpp|hh|cpp|cc|c)\b")
# Prevodni znacka, kterou clovek uvidi doslova ("%.1f" v Settings).
#
# ROZDIL PROTI `brana_vety.py` C. 1: tam se `%` u formatujicich vyusteni
# (`lv_label_set_text_fmt`) NEHLASI, protoze format se teprve zpracuje. Ve
# scene je text HOTOVY - zadne dosazovani uz neprijde, takze procento na
# plose je vzdy chyba. Nejde o jinou mez, jde o jine misto mereni.
#
# SAMOTNA MEZERA NENI PRIZNAK. Puvodni trida priznaku `[-+ #0]*` obsahovala
# mezeru (printf ji zna jako priznak znamenka, `% d`), takze v cestine, kde
# se pred procentem mezera PISE, spolkla mezeru a nasledujici slovo zacinajici
# na d/i/o/u/x/e/f/g/a/c/s/p/n prohlasila za prevodni znacku:
#     '... vzrostl z 1,2 % na 18,6 %'  ->  '% n'   (SvorkaRfKoex, ostry beh)
#     'vyuziti 12,5 % pameti RAM'      ->  '% p'
#     'signal 80 % dobry'              ->  '% d'
# Vsechny tri vety jsou spravne cesky. Brana, ktera rudne na spravne vete,
# uci cloveka rudou barvu ignorovat - a prave tady se ma cist. Mezera je
# proto z tridy priznaku PRYC; cenou je, ze `% d` psane s mezerou (v C legalni
# tvar) projde. Ta cena je ZMERENA: v korpusu ESPOS ani na 62 listech kitu
# neni ani jeden takovy tvar, zatimco ceskych vet s procentem uprostred jsou
# desitky. Vzor zustava byte-identicky s `brana_vety.PROCENTO`.
_V_PROCENTO = re.compile(r"%[-+#0]*[\d.*]*(?:hh|h|ll|l|j|z|t|L)?[diouxXeEfgGaAcspn%]")
# Volani funkce ve vete: `startScan()`, `measureChannel()`.
_V_VOLANI = re.compile(r"\b[A-Za-z_]\w*\(\s*\)")
# Strojovy CLEN: `rx_ctrl.noise_floor`, `wifi_ap_record.rssi`. Pristup na
# polozku struktury cizi knihovny. Zivy protejsek je na listu Network Tools
# ("chybi API (rx_ctrl.noise_floor v promiskuitnim rezimu)") a nechytal ho
# ani jeden ze sedmi puvodnich tvaru: `rx` neni v PREDPONY_SDK, `.noise_floor`
# neni pripona hlavicky a zavorky tam nejsou.
#
# Rozhodovaci pravidlo: identifikator s PODTRZITKEM, tecka, dalsi
# identifikator. Podtrzitko je ta rozhodujici pulka - v ceske vete se
# nevyskytuje, takze `veta. Dalsi veta` ani `tabos.cc` sem nespadnou.
# `_V_HLAVICKA` rozhoduje driv, takze `data_source.h` zustava jmenem hlavicky.
#
# JMENO SOUBORU NENI CLEN. Zmereno na 62 listech kitu: bez teto vyjimky
# hlasil vzor `capture_0412.la`, `uart_dump.bin`, `mereni_i2c_100_khz.la`
# i `cat zaznam_042.la | hex` - deset nalezu a ani jeden neni vada.
# Jmeno souboru je pro cloveka TOTEZ co cesta na karte: prijde si ho
# precist do Souboru a musi souhlasit do pismene (tataz uvaha jako
# u pojmenovane vyjimky "/sd/"). Rozhoduje PRIPONA a je to seznam, ne
# domysleni - kdyz pribude format, pribude radek. Pripony ZDROJOVEHO kodu
# se sem schvalne nedavaji: `data_source.h` rozhoduje `_V_HLAVICKA`, ktera
# je v poradi driv.
PRIPONY_SOUBORU = (
    "la", "bin", "csv", "tsv", "txt", "log", "json", "raw", "vcd", "dat",
    "wav", "png", "bmp", "jpg", "gif", "zip", "tar", "gz", "pdf", "md",
    "cfg", "ini", "toml", "yaml", "yml", "bak", "tmp", "hex", "elf", "img",
)  # fmt: skip
_V_CLEN = re.compile(
    r"\b[A-Za-z_]\w*_\w+\.(?!(?i:"
    + "|".join(PRIPONY_SOUBORU)
    + r")\b)[A-Za-z_]\w*\b"
)
# Strojovy stitek chybejiciho backendu: `esp_hosted:GetRadioInfo@fazeA`.
_V_STITEK = re.compile(r"\b[A-Za-z_]\w*:[A-Za-z_]\w*@[A-Za-z_]\w*\b")
# Jmeno rozhrani podle konvence repa: velke I a hned za nim dalsi velke
# pismeno (`IHwDiagnostics`, `INetworkService`, `I802154Service`).
_V_ROZHRANI = re.compile(r"\bI(?=[A-Z0-9])[A-Za-z0-9]{3,}\b")

# Predpony cizich SDK (IDF, LVGL, FreeRTOS). Za predponou musi byt NEJMENE
# DVA dalsi useky - to je hranice mezi jmenem FUNKCE (`esp_wifi_ftm_initiate_
# session`) a jmenem SOUCASTI (`esp_hosted`), ktere clovek nahrava do C6 a
# musi souhlasit do pismene. Obsah i PORADI je shodne s
# `brana_vety.PREDPONY_SDK` vcetne cleneni radku, aby se obe mista dala
# porovnat i ocima. Na PORADI zalezi: sklada se z nej alternace nize.
VETY_PREDPONY_SDK = (
    "esp", "lv", "nvs", "gpio", "i2c", "i2s", "spi", "uart", "ledc", "rmt",
    "mcpwm", "adc", "dac", "rtc", "usb", "sdmmc", "periph", "heap", "lwip",
    "netif", "mbedtls", "pthread", "ieee802154", "ot",
    "xTask", "vTask", "xQueue", "xSemaphore", "xEventGroup",
)  # fmt: skip
_V_API_JMENO = re.compile(
    r"\b(?:" + "|".join(VETY_PREDPONY_SDK) + r")_[A-Za-z0-9]+(?:_[A-Za-z0-9]+|_\*)+"
)

# Slova, ktera vypadaji jako jmeno rozhrani, ale jsou to bezne udaje.
# Seznam je shodny s `brana_vety.NENI_ROZHRANI`.
VETY_NENI_ROZHRANI = frozenset({"IPv4", "IPv6", "I2C", "I2S", "IEEE", "ID", "IO", "IRQ"})

# ── Verzalkove slovo uvnitr vety (osmy tvar) ───────────────────────────────
#
# Puvodni vyjimka znela "slovo cele verzalkami neni jmeno rozhrani" a byla
# PRILIS SIROKA: umlcela `IHWDIAGNOSTICS` i `vraci UNAVAILABLE`, coz jsou
# obe zive vady F4 z panelu (smalt se sazi verzalkami, takze jmeno typu
# v nem verzalkove JE). Zaroven ale musi zustat ticho na `USB`, `RAM`,
# `LVGL`, `TEPLOTA CPU` - a to jsou taky verzalky. Tvar slova tedy
# nerozhoduje; rozhoduje, jestli to slovo NEKDE V SDK JE.
#
# Trida se deli na dve a hranice je mereny, ne vkusovy:
#
#  (a) **Text CELY verzalkami je STITEK** a tahle trida se v nem NEMERI.
#      Duvod: hodnoty enumu SDK jsou bezna slova (`Error`, `Stav`, `Info`,
#      `Live`, `Mock`, `Uroven`), takze stitek `STAV` nebo `CHYBA` by se
#      s nimi trefil a brana by obvinila spravny popisek. V celoverzalkovem
#      textu se ty dve veci rozlisit nedaji.
#  (b) **Uvnitr vety, ktera ma i mala pismena**, je verzalkove slovo
#      neobvykle a shoda uz neco znamena: porovna se BEZ OHLEDU NA VELIKOST
#      PISMEN se jmeny ze SDK (`jmena_ze_sdk`). Shoda = ERROR, jinak ticho.
#
# Seznam jmen se NEOPISUJE: cte ho `jmena_ze_sdk()` z hlavicek SDK a vozi
# ho most ve scene (`navrh.jmena_sdk`). Opsany seznam by zestarl prvni
# zmenou v SDK a brana by mlcela prave o novem jmenu.
_V_VERZALKY = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

# --- Jmeno rozhrani ve STITKU verzalkami (devaty tvar) --------------------
#
# Rozhodnuti koordinatora 9. 9. 2026 k rezidu R3 kritika. Bod (a) vyse rika,
# ze text CELY verzalkami je stitek a bezna slova ze SDK (`SMALT`, `ZNAK`,
# `INFO`) se v nem nemeri - to plati dal a je to ZMERENA mez. Jmeno
# ROZHRANI je ale jina vec: `IHwDiagnostics` neni bezne slovo, ktere by
# nekdo napsal na smalt, a patka "ZDROJ IHWDIAGNOSTICS" je tataz vada F4
# jako "ZDROJ IHwDiagnostics" o radek vedle. Do 9. 9. mlcely OBE brany.
#
# Ve verzalkovem textu se hrby VIDET NEDAJI (`IHWDIAGNOSTICS` je jen dlouhe
# slovo), takze tvar sam rozhodnout nemuze a POROVNAVA se se jmeny ze SDK.
# Aby se nechytila jednohrba jmena, jejichz verzalkova podoba uz muze byt
# bezne slovo (`IClock` -> `ICLOCK`, `ISettings` -> `ISETTINGS`), zada se
# konvence repa PLNE: velke I a za nim CamelCase s NEJMENE DVEMA hrby.
# Zmereno nad zivym SDK (57 jmen): 23 rozhrani, z toho 18 dvouhrbych;
# petice jednohrbych (`IAsync`, `IClock`, `ILogger`, `ISettings`,
# `ITelemetry`) je vedomy okraj, ne opomenuti.
_V_ROZHRANI_HRBY = 2


def _dvouhrba_rozhrani(jmena_sdk: frozenset[str]) -> frozenset[str]:
    """Jmena rozhrani I+CamelCase se dvema hrby, VERZALKOVE (pro porovnani).

    Filtruje se TVAREM, ne rucnim seznamem: co je v SDK rozhranim, urcuje
    `jmena_ze_sdk`, a co je dost nezamenitelne na to, aby se hlasilo i ve
    stitku verzalkami, urcuje pocet hrbu.
    """
    ven = set()
    for j in jmena_sdk:
        if not _V_ROZHRANI.fullmatch(j):
            continue
        if sum(1 for z in j[1:] if z.isupper()) < _V_ROZHRANI_HRBY:
            continue
        ven.add(j.upper())
    return frozenset(ven)


# CamelCase slovo se dvema hrby uvnitr vety: `NotFound`, `InvalidArgument`,
# `OutOfMemory`. Hlasi se JEN pri shode se jmenem ze SDK - jinak by kazde
# `TabOS`, `BusLab` nebo `WiFiKarta` bylo obvinenim a brana by rudla na
# vlastnim jmenu pristroje. Zmereno nad zivym SDK: shodu davaji `BadState`,
# `InvalidArgument`, `NotFound`, `OutOfMemory`, `PermissionDenied`,
# `WifiHosted`; `TabOS` tvarem sedi, ale v SDK neni, takze mlci.
#
# Zavira reziduum R4 kritika: radek terminalu 'ERROR cteni: NotFound' se
# dosud citoval slabsim kusem (`ERROR` je bezne slovo severity), zatimco
# ostrejsi dukaz `NotFound` propadal. Proto se tenhle tvar meri PRED
# verzalkovym - hlaska ma ukazat na to, co je nejmene sporne.
_V_CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b")

# Verzalkova slova, ktera se se jmenem ze SDK trefi TVAREM, ale na panelu
# znamenaji neco jineho. Kazde jmenovite a s duvodem; seznam je shodny
# s `brana_vety.NENI_JMENO_SDK`.
VETY_NENI_JMENO_SDK = frozenset(
    {
        # `Mock` je hodnota `DataState`, ale "MOCK DATA" je ceduka o tom, ze
        # cisla jsou nastrcena - clovek to cte jako pridavne jmeno, ne jako
        # odpoved sluzby. Rozhodnuti je starsi nez tahle trida (hlavicka
        # brany vet, 3. 9. 2026: "MOCK DATA, TabOS i USB-A jsou legitimni").
        # Zmereno: bez teto vyjimky pribylo v jadre a v appkach sedm nalezu
        # a vsech sedm bylo na retezcich typu "MOCK DATA - desktop".
        "MOCK",
    }
)

# Hlavicky SDK: `class IHwDiagnostics`, `struct IRadioInfo`.
_SDK_ROZHRANI = re.compile(r"\b(?:class|struct)\s+(I[A-Z][A-Za-z0-9]*)\b")
# `enum class Error : uint16_t { None = 0, InvalidArgument, ... }`. Telo se
# bere az po prvni `}`; hodnoty jsou identifikatory pred `=` nebo `,`.
_SDK_ENUM = re.compile(r"\benum\s+(?:class\s+|struct\s+)?[A-Za-z_]\w*[^{;]*\{([^}]*)\}")
_SDK_HODNOTA = re.compile(r"\b([A-Za-z_]\w*)\s*(?:=[^,]*)?(?:,|$)")

# Pojmenovane vyjimky, shodne s `brana_vety.VYJIMKY`. Kazda ma duvod;
# vyjimka bez duvodu je diera.
VETY_VYJIMKY = (
    # Cesta na karte je pro cloveka MISTO, ne jmeno v kodu.
    (re.compile(r"^/(?:sd|dev|sys)/"), "cesta na uloziste je udaj pro cloveka"),
    # Prazdny retezec a jednoznaky oddelovac nejsou veta.
    (re.compile(r"^.{0,1}$"), "neni veta"),
)

# (klic v `brana_vety.py`, pojmenovani v hlasce, vzor). Poradi je poradi
# rozhodovani ve `brana_vety.strojove_jmeno` - jmeno rozhrani az naposled,
# protoze je z celeho sedmilistku nejsirsi. Klic je tu proto, aby test
# shody v kitu porovnal dvojice HODNOTAMI (`getattr(brana_vety, klic)`),
# ne ocima.
VETY_VZORY = (
    ("SCOPE", "jmeno v kodu", _V_SCOPE),
    ("HLAVICKA", "jmeno hlavicky", _V_HLAVICKA),
    ("PROCENTO", "prevodni znacka", _V_PROCENTO),
    ("VOLANI", "volani funkce", _V_VOLANI),
    ("CLEN", "strojovy clen", _V_CLEN),
    ("STITEK", "strojovy stitek", _V_STITEK),
    ("API_JMENO", "jmeno funkce SDK", _V_API_JMENO),
    ("ROZHRANI", "jmeno rozhrani", _V_ROZHRANI),
)

# ── Device profiles ────────────────────────────────────────────────────────
#
# Every constant above describes ONE panel: the 256x128 4bpp OLED with the
# monospaced font6x8. Those numbers are not universal, and applying them to a
# different display produces two kinds of nonsense at the same time — findings
# that cannot apply, and silence exactly where a real defect sits. A 1280x720
# colour panel with a proportional font needs its own numbers, not a scaled
# copy of these.
#
# The profile is picked from the design data (explicit ``"device"`` key, else
# by scene dimensions). Anything unrecognised falls back to the OLED, so every
# existing design and test keeps behaving exactly as it did before.


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.1 relative luminance (sRGB, gamma-correct)."""

    def ch(v: int) -> float:
        c = v / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG contrast ratio, 1.0 .. 21.0. Symmetric: polarity does not matter."""
    a, b = _rel_luminance(fg), _rel_luminance(bg)
    lo, hi = min(a, b), max(a, b)
    return (hi + 0.05) / (lo + 0.05)


@dataclass(frozen=True)
class DeviceProfile:
    """The panel a design is drawn for, and the numbers that follow from it."""

    name: str
    match_w: int  # scene size this profile is recognised by (0 = never auto)
    match_h: int
    char_w: int  # LOWER BOUND on glyph advance, see note in PROFILE_TAB5
    char_h: int
    render_pad: int  # per-side inset the renderer eats inside a text box
    min_text_h: int
    font_chars: frozenset[str] | None  # None = no charset restriction
    max_text_len: int
    soft_widgets: int
    hard_widgets: int
    min_edge_margin: int
    contrast_mode: str  # "brightness" (delta) | "wcag" (ratio)
    min_contrast: float
    min_visible_brightness: int  # only meaningful in "brightness" mode
    ppi: float
    min_touch_px: int  # below this a touch target is an ERROR
    warn_touch_px: int  # below this it is a WARN
    # Rule 142: plati na tomhle panelu jazykovy zakon F4 (veta pro
    # cloveka nesmi nest strojove jmeno)? Je to zakon TabOSu, ne
    # vlastnost displeje - cizi navrh se jim soudit nema.
    vety_pro_cloveka: bool = False
    # Rule 146: plati na tomhle panelu zakon polarity (svetla smaltova
    # plocha nese TMAVY inkoust, ktery na ni PATRI)? Tataz uvaha jako
    # u `vety_pro_cloveka`: je to zakon jazyka TabOSu (ram.py, "SVETLA
    # SMALTOVA PLOCHA = FYZICKA PRAVDA PRISTROJE"), ne vlastnost skla.
    # Cizi navrh muze mit svetle plochy a svetly text nad nimi zamerne.
    polarita_smaltu: bool = False
    # Rule 147: rozhoduje na tomhle panelu delici cara? Gatuje se profilem
    # proto, ze CO JE CARA je rozhodnuti kreslicího jazyka: v TabOSu je to
    # vlasova linka `.cara` (1 px pres sirku pole), jinde muze byt 2 px
    # vysoky obdelnik plocha, ne oddelovac. Bez teto pulky by pravidlo
    # v cizim navrhu obvinovalo vyplne.
    delici_cary: bool = False
    # Rule 17: druha, VOLNEJSI mez kontrastu pro velky text (WCAG 2.1 AA).
    # Nula = profil druhou mez nema a plati jedina `min_contrast` pro
    # vsechno; smysl ma jen v rezimu "wcag" (v rezimu "brightness" se
    # nemeri pomer, ale rozdil jasu, a WCAG o nem nemluvi).
    min_contrast_velky: float = 0.0
    # Rule 149: jak daleko od skla je oko. Uhlova velikost znaku je
    # vlastnost TROJICE (rez, PPI, vzdalenost), takze bez tohohle cisla
    # nema pravidlo co pocitat a MLCI. 0 = profil vzdalenost nezna.
    cteci_vzdalenost_mm: float = 0.0
    # Rule 149: kolik z rezu je VERZALKA. Je to vlastnost FONTU, ne skla
    # (OS/2 sCapHeight deleno unitsPerEm), ale profil uz jednu vlastnost
    # fontu nese (`font_chars`) a je to tyz font, ktery panel opravdu ma
    # ve flashi. 0 = nezname, pravidlo mlci.
    verzalka_pomer: float = 0.0

    def mm(self, px: float) -> float:
        """Physical size of ``px`` on this panel, in millimetres."""
        return px * 25.4 / self.ppi if self.ppi else 0.0

    def minuty(self, px: float) -> float:
        """Uhlova velikost ``px`` na tomhle panelu, v uhlovych minutach.

        Presny prepocet ``2*atan(h/2d)``, ne maly uhel ``h/d``. Rozdil je
        0,007 %, ale u rezu 32 px prehodi zaokrouhleni ze 14,78' na 14,79'
        - a prave o tenhle jeden setinovy rozdil se v kitu rozesly dve
        tabulky, kazda s vlastnim zakazem opravy. Sjednoceno 2026-09-06
        ve prospech presneho prepoctu (fyzika, ne konvence).
        """
        if not self.ppi or not self.cteci_vzdalenost_mm:
            return 0.0
        return math.degrees(
            2.0 * math.atan(self.mm(px) / (2.0 * self.cteci_vzdalenost_mm))
        ) * 60.0


PROFILE_OLED256 = DeviceProfile(
    name="oled256",
    match_w=256,
    match_h=128,
    char_w=CHAR_W,
    char_h=CHAR_H,
    render_pad=RENDER_PAD,
    min_text_h=MIN_TEXT_H,
    font_chars=frozenset(FONT_CHARS),
    max_text_len=MAX_TEXT_LEN,
    soft_widgets=MAX_WIDGETS_PER_SCENE,
    hard_widgets=HARD_WIDGET_LIMIT,
    min_edge_margin=MIN_EDGE_MARGIN,
    contrast_mode="brightness",
    min_contrast=MIN_CONTRAST,
    min_visible_brightness=MIN_VISIBLE_BRIGHTNESS,
    ppi=0.0,  # no touch panel; size limits below are disabled by 0
    min_touch_px=0,
    warn_touch_px=0,
    # Zmereno, ne odhadnuto: `widget_catalog.json` (256x128) nese text
    # "INVERSE", ktery vzor jmena rozhrani chyta. Cizi navrh neni
    # TabOS a jazykovym zakonem F4 se soudit nema.
    vety_pro_cloveka=False,
    # Tyz duvod: 256x128 4bpp seda zadny "smalt" nema (svetla plocha je
    # tam bezna vypln) a "cara" je na ni 1 px obdelnik, kterym se kresli
    # i ramecky. Obe pravidla by tu merila neco jineho, nez slibuji.
    polarita_smaltu=False,
    delici_cary=False,
    # Rezim "brightness" pomer nepocita, takze druha mez WCAG nema co
    # zjemnit; 4bpp seda navic zna 16 odstinu a "velky text" je tu 8 px.
    min_contrast_velky=0.0,
    # Bez PPI nema uhlova velikost co pocitat (viz `ppi=0.0` vyse), takze
    # vzdalenost ani verzalka nedavaji smysl a Rule 149 mlci.
    cteci_vzdalenost_mm=0.0,
    verzalka_pomer=0.0,
)

# Glyfy, ktere jsou OPRAVDU vyrezane ve fontu zarizeni. Tenhle seznam je
# smysl celeho profilu: LVGL chybejici glyf TISE preskoci, takze znak mimo
# tuhle mnozinu se nevykresli spatne — nevykresli se vubec, a z "-58 dBm"
# se stane "58 dBm".
#
# JEDEN ZDROJ PRAVDY: `core/src/fonts/lv_font_tabos_*.c`, tedy to, co ma
# zarizeni ve flashi. Tenhle seznam je jeho OPIS a opis se s originalem
# drive nebo pozdeji rozejde — proto ho pribiji test
# `test_znakova_sada_sedi_s_fontem_zarizeni` (cte cmap funkci
# `znaky_fontu_zarizeni` a porovnava ji se vsemi ctyrmi kopiemi, ktere
# v projektu zijou: tady, `gen_subset.SADA` v kitu a recept
# `gen_fonty.py` v jadre). Zmereno 2026-09-09: font ma 201 kodovych bodu
# — 141 textovych a 60 symbolu LVGL.
#
# Delba na dve pulky NENI kosmetika:
#
#  * `_TAB5_FONT_TEXT` je to, co umi i podmnozina vsazena do artboardu
#    (`montserrat_b64.txt`); v prohlizeci se tyhle znaky nakresli TOUZ
#    kresbou jako na skle, takze meridla sirek nad artboardem plati.
#  * `_TAB5_FONT_SYMBOLY` jsou symboly LVGL (FontAwesome, U+F000 a vys).
#    Zarizeni je UMI — pouzivaji je vestavene widgety (klavesnice mela
#    misto backspace prazdny ramecek, dokud se vynechavaly — zmereno na
#    desce). Do subsetu artboardu se schvalne NEDAVAJI: v listech se
#    nekresli a FontAwesome by base64 zbytecne nafoukl. Pravidlo 26 ale
#    meri, co zarizeni UMI, ne co umi artboard, takze do profilu patri.
_TAB5_FONT_TEXT = frozenset(
    [chr(c) for c in range(0x20, 0x7F)]
    + [
        chr(c)
        for c in (
            0xE1,
            0xE9,
            0xED,
            0xF3,
            0xFA,
            0xFD,
            0xC1,
            0xC9,
            0xCD,
            0xD3,
            0xDA,
            0xDD,
            0x10C,
            0x10D,
            0x10E,
            0x10F,
            0x11A,
            0x11B,
            0x147,
            0x148,
            0x158,
            0x159,
            0x160,
            0x161,
            0x164,
            0x165,
            0x16E,
            0x16F,
            0x17D,
            0x17E,
        )
    ]
    + [
        chr(c)
        for c in (
            0x2013,
            0x2014,
            0x2022,
            0x201E,
            0x201C,
            0xB0,
            0xB7,
            # rozsireni 2026-08-25: minus, mikro, +-, krat a
            # kurzorove sipky - dorezano do gen_fonty.py
            0x2212,
            0xB5,
            0xB1,
            0xD7,
            0x2192,
            0x2190,
            # + uhlove minuty, ohm a delta - mereni je
            # bez nich nema; dorezano tehoz dne
            0x2032,
            0x3A9,
            0x394,
        )
    ]
)

# Symboly LVGL (FontAwesome) prilozene do tehoz fontu. Cisla jsou z receptu
# `tabos-core/tools/gen_fonty.py` (SYMBOLY) a zmereno se shoduji s cmap
# vygenerovaneho `lv_font_tabos_16.c` do jednoho kodoveho bodu.
_TAB5_FONT_SYMBOLY = frozenset(
    chr(c)
    for c in (
        0xF001, 0xF008, 0xF00B, 0xF00C, 0xF00D, 0xF011,
        0xF013, 0xF015, 0xF019, 0xF01C, 0xF021, 0xF026,
        0xF027, 0xF028, 0xF03E, 0xF043, 0xF048, 0xF04B,
        0xF04C, 0xF04D, 0xF051, 0xF052, 0xF053, 0xF054,
        0xF067, 0xF068, 0xF06E, 0xF070, 0xF071, 0xF074,
        0xF077, 0xF078, 0xF079, 0xF07B, 0xF093, 0xF095,
        0xF0C4, 0xF0C5, 0xF0C7, 0xF0C9, 0xF0E0, 0xF0E7,
        0xF0EA, 0xF0F3, 0xF11C, 0xF124, 0xF15B, 0xF1EB,
        0xF240, 0xF241, 0xF242, 0xF243, 0xF244, 0xF287,
        0xF293, 0xF2ED, 0xF304, 0xF55A, 0xF7C2, 0xF8A2,
    )
)  # fmt: skip

_TAB5_FONT_CHARS = _TAB5_FONT_TEXT | _TAB5_FONT_SYMBOLY

PROFILE_TAB5 = DeviceProfile(
    name="tab5",
    match_w=1280,
    match_h=720,
    # Montserrat is PROPORTIONAL, so there is no single character width. The
    # narrowest printable advance in the shipped subset is 2.73 px at the
    # smallest size in use (13 px), measured from the TTF hmtx table. Floored
    # to 2 on purpose: the fit checks divide by this, so a LOWER bound can only
    # ever overestimate how much text fits. That makes "cannot fit" sound —
    # it never accuses falsely — at the cost of missing marginal cases.
    char_w=2,
    # Geometry from the converter is INK, not the line box, so the floor here
    # is the smallest ink a single line can have: the x-height of the smallest
    # type in use. Montserrat sxHeight is 0.53 em = 6.89 px at 13 px, floored
    # to 6. Using the font SIZE (13) invented hundreds of "cannot fit"
    # findings on lines that simply had no ascenders in them.
    char_h=6,
    # The OLED renderer clips 2 px inside every box; LVGL does not —
    # the box IS the line box, so 13 px type in a 16 px box fits exactly.
    # Keeping the OLED's 2 px here invented a 'cannot fit' on every label.
    render_pad=0,
    min_text_h=6,  # ink, not line box — see char_h above
    font_chars=_TAB5_FONT_CHARS,
    max_text_len=256,  # 127 is an OLED readability limit, not a panel limit
    soft_widgets=200,
    hard_widgets=800,  # P4 with PSRAM; O(n^2) at 800 is still ~0.3 s
    min_edge_margin=8,
    contrast_mode="wcag",
    min_contrast=4.5,  # WCAG 2.1 AA for body text
    min_visible_brightness=0,  # a dark foreground is not a defect, see below
    # PPI panelu. Cislo se NEVOLI: uhlopricka v pixelech
    # sqrt(1280^2+720^2) = 1468,6 delena 5,0" da 293,72, zaokrouhleno 294.
    # 294 je JEDINE cislo panelu v celem projektu (drive tu bylo 293,7,
    # zatimco `tokens.json` i `citelnost.py` pocitaly s 294 - rozdil 0,1 %,
    # tedy 0,001 mm na verzalce, ale dve pravdy). Pribito testem
    # `test_ppi_je_odvozene_a_shodne_s_tokens` proti primarnim udajum
    # (`tokens.json: panel`), takze sem nikdo nesmi napsat libovolne cislo.
    ppi=294.0,
    # 294 PPI means 1 px = 0.086 mm, so pixel counts are misleading: a 44 px
    # button is 3.8 mm, well under any published minimum. Apple asks 7.0 mm,
    # Material 7.6 mm, ISO 9241-411 7 mm as the floor. 7 mm = 81 px here;
    # below 5 mm (58 px) touch error rates climb steeply, so that is the line
    # between a warning and an error.
    min_touch_px=58,
    warn_touch_px=81,
    # Tady zakon F4 plati: jsou to listy TabOSu (charta
    # docs/CHARTA_JAZYKA_VET.md).
    vety_pro_cloveka=True,
    # A tady plati i zakon polarity a kreslici jazyk s vlasovou carou
    # (tabos-ui-kit/navrh-appky/ram.py).
    polarita_smaltu=True,
    delici_cary=True,
    # WCAG 2.1 AA zna dve meze, ne jednu: 3,0:1 pro velky text (>= 24 px,
    # nebo >= 19 px tucne). Bez ni hlasi Rule 17 falesny poplach na kazdem
    # velkem titulku, ktery se do 4,5 netrefi - a to je prave trida, kde
    # norma vetsi glyf uznava jako nahradu kontrastu.
    min_contrast_velky=3.0,
    # Nad pristrojem se stoji, ne sedi: 450 mm je vzdalenost, na ktere se
    # panel opravdu cte (`tabos-ui-kit/navrh-appky/citelnost.py`, tabulka
    # vzdalenosti 400/450/600/900 mm; verdikt se vynasi na 450).
    cteci_vzdalenost_mm=450.0,
    # Montserrat-Medium, ktery jde do LVGL: OS/2 sCapHeight 700 pri
    # unitsPerEm 1000. Potvrzeno druhym ctenim (bbox glyfu 'H' i 'E' ma
    # ymax 700). NENI to 0,708 - to je vyska CISLICE (bbox '0' ma pretah
    # 8 jednotek) a kdo si ji splete, nadsadi citelnost o 2,86 %.
    verzalka_pomer=0.700,
)

PROFILES: dict[str, DeviceProfile] = {
    PROFILE_OLED256.name: PROFILE_OLED256,
    PROFILE_TAB5.name: PROFILE_TAB5,
}


def _profile_for(data: dict[str, Any]) -> DeviceProfile:
    """Pick the panel profile for a design: explicit key first, size second."""
    named = data.get("device")
    if isinstance(named, str) and named in PROFILES:
        return PROFILES[named]
    w, h = data.get("width"), data.get("height")
    if not (_is_int(w) and _is_int(h)):
        scenes = data.get("scenes")
        if isinstance(scenes, dict):
            for sc in scenes.values():
                if isinstance(sc, dict) and _is_int(sc.get("width")) and _is_int(sc.get("height")):
                    w, h = sc["width"], sc["height"]
                    break
    for prof in PROFILES.values():
        if prof.match_w and prof.match_w == w and prof.match_h == h:
            return prof
    return PROFILE_OLED256


def _parse_color(s: str) -> tuple[int, int, int] | None:
    if not s:
        return None
    low = s.strip().lower()
    if low in _NAMED_COLORS:
        return _NAMED_COLORS[low]
    m = _HEX_RE.match(s.strip())
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return None


def _brightness(rgb: tuple[int, int, int]) -> int:
    return int(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])


def _is_critical_warning(message: str) -> bool:
    msg = message.lower()
    return any(marker in msg for marker in CRITICAL_WARNING_MARKERS)


# ── Core types ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Issue:
    level: str  # "ERROR" | "WARN"
    message: str


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_bool(v: object) -> bool:
    return isinstance(v, bool)


def _parse_runtime_meta(runtime: str) -> dict[str, str]:
    """Parse 'key=val;key2=val2' into a dict of lowercased keys to raw values."""
    meta: dict[str, str] = {}
    for part in runtime.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        meta[k.strip().lower()] = v.strip()
    return meta


# ── Visual-backend logic (events / rules) vocabulary ──────────────────────
_LOGIC_TRIGGERS = {"boot", "timer", "gpio_in", "ble_recv", "lora_recv", "widget"}
_LOGIC_ACTIONS = {
    "set_scene",
    "set_widget",
    "set_var",
    "gpio_write",
    "toast",
    "start_timer",
    "stop_timer",
    "ble_send",
    "lora_send",
}
_LOGIC_PROPS = {"value", "text", "checked", "visible", "enabled"}
_LOGIC_OPS = {"==", "!=", "<", ">", "<=", ">="}
_LOGIC_WIDGET_EVENTS = {"on_press", "on_change", "on_focus"}
_RADIO_ACTIONS = {"ble_send": "ble", "lora_send": "lora_sx1262"}
_VAR_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_EXPR_RE = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_]*|-?\d+"
    r"(\s*[+\-*/]\s*([A-Za-z_][A-Za-z0-9_]*|-?\d+))?\s*$"
)


def _board_peripherals(data: dict[str, Any]) -> tuple[set[str] | None, str]:
    """Resolve declared board -> its peripheral set via board_registry.

    Returns ``(peripherals_or_None, board_label)``. ``None`` means no board
    was declared or it is unknown — radio actions then warn (capability
    unverifiable) rather than hard-error, so generic designs still validate.
    """
    board_id = data.get("board") or data.get("active_board")
    if not isinstance(board_id, str) or not board_id:
        return None, ""
    try:
        from board_registry import load_registry

        reg = load_registry()
        b = reg.get(board_id)
    except Exception:  # registry missing/broken — treat as unverifiable
        return None, board_id
    if b is None:
        return None, board_id
    return set(b.peripherals or []), board_id


def _logic_operand_issue(ref: Any, where: str, widget_ids: set[str]) -> str | None:
    """Validate a condition operand / rhs. Returns an error message or None."""
    if isinstance(ref, bool):
        return f"{where}: boolean operand not allowed (use 0/1)"
    if isinstance(ref, int):
        return None
    if not isinstance(ref, str) or not ref:
        return f"{where}: operand must be int, 'var:<n>' or 'widget:<id>.value|checked'"
    s = ref.strip()
    if re.fullmatch(r"-?\d+", s):
        return None
    if s.startswith("var:"):
        return None if _VAR_NAME_RE.match(s[4:].strip()) else f"{where}: bad var name {s!r}"
    if s.startswith("widget:"):
        body = s[len("widget:") :]
        wid, _, attr = body.partition(".")
        wid = wid.strip()
        attr = (attr or "value").strip().lower()
        if not wid:
            return f"{where}: widget operand missing id"
        if attr not in ("value", "checked"):
            return f"{where}: widget operand attr must be .value or .checked"
        if wid not in widget_ids:
            return f"{where}: references unknown widget id {wid!r}"
        return None
    return f"{where}: unparseable operand {ref!r}"


def _validate_action(
    a: Any,
    where: str,
    scene_names: set[str],
    widget_ids: set[str],
    board_per: set[str] | None,
    board_label: str,
) -> list[Issue]:
    out: list[Issue] = []
    if not isinstance(a, dict):
        out.append(Issue("ERROR", f"{where}: action must be an object"))
        return out
    t = str(a.get("type", "")).strip().lower()
    if t not in _LOGIC_ACTIONS:
        out.append(Issue("ERROR", f"{where}: unknown action type {a.get('type')!r}"))
        return out
    if t == "set_scene":
        sc = a.get("scene")
        if not isinstance(sc, str) or not sc:
            out.append(Issue("ERROR", f"{where}: set_scene needs 'scene'"))
        elif sc not in scene_names:
            out.append(Issue("ERROR", f"{where}: set_scene -> unknown scene {sc!r}"))
    elif t == "set_widget":
        wid = a.get("widget")
        if not isinstance(wid, str) or not wid:
            out.append(Issue("ERROR", f"{where}: set_widget needs 'widget'"))
        elif wid not in widget_ids:
            out.append(Issue("ERROR", f"{where}: set_widget -> unknown widget id {wid!r}"))
        prop = str(a.get("prop", "value") or "value").lower()
        if prop not in _LOGIC_PROPS:
            out.append(Issue("ERROR", f"{where}: set_widget bad prop {prop!r}"))
        if prop == "text" and not isinstance(a.get("text", a.get("value", "")), str):
            out.append(Issue("WARN", f"{where}: set_widget(text) value should be a string"))
    elif t == "set_var":
        v = a.get("var")
        if not isinstance(v, str) or not _VAR_NAME_RE.match(v or ""):
            out.append(Issue("ERROR", f"{where}: set_var needs a [a-z0-9_] 'var' name"))
        ex = a.get("expr")
        if not isinstance(ex, str) or not ex.strip():
            out.append(Issue("ERROR", f"{where}: set_var needs a non-empty 'expr'"))
        elif not _EXPR_RE.match(ex):
            out.append(
                Issue("ERROR", f"{where}: set_var expr {ex!r} too complex (only 'A' or 'A op B')")
            )
    elif t == "gpio_write":
        if not _is_int(a.get("pin")):
            out.append(Issue("ERROR", f"{where}: gpio_write needs int 'pin'"))
        if a.get("level") not in (0, 1):
            out.append(Issue("ERROR", f"{where}: gpio_write 'level' must be 0 or 1"))
    elif t == "toast":
        if not isinstance(a.get("text"), str):
            out.append(Issue("WARN", f"{where}: toast should have a 'text' string"))
    elif t == "start_timer":
        tid = a.get("timer_id")
        if not _is_int(tid) or not (0 <= int(tid) <= 15):
            out.append(Issue("ERROR", f"{where}: start_timer 'timer_id' must be 0..15"))
        ms = a.get("ms")
        if not _is_int(ms) or int(ms) < 1:
            out.append(Issue("ERROR", f"{where}: start_timer 'ms' must be a positive int"))
    elif t == "stop_timer":
        tid = a.get("timer_id")
        if not _is_int(tid) or not (0 <= int(tid) <= 15):
            out.append(Issue("ERROR", f"{where}: stop_timer 'timer_id' must be 0..15"))
    elif t in _RADIO_ACTIONS:
        if not isinstance(a.get("bytes"), str) or not a.get("bytes"):
            out.append(Issue("ERROR", f"{where}: {t} needs a non-empty 'bytes' string"))
        need = _RADIO_ACTIONS[t]
        if board_per is None:
            out.append(
                Issue(
                    "WARN",
                    f"{where}: {t} requires a board with '{need}' - no/unknown board "
                    f"declared, capability unverifiable",
                )
            )
        elif need not in board_per:
            out.append(
                Issue(
                    "ERROR",
                    f"{where}: {t} not allowed - board '{board_label}' lacks '{need}' peripheral",
                )
            )
    return out


def _validate_logic(
    data: dict[str, Any], scenes: dict[str, dict[str, Any]], file_label: str
) -> list[Issue]:
    """Validate per-widget ``events`` and per-scene ``rules`` end to end.

    Rule 130 (this block): trigger/action/condition vocabulary, var-name
    format, set_scene/set_widget/widget-operand cross-references, and
    board-peripheral gating for ble_send/lora_send.
    """
    issues: list[Issue] = []
    scene_names = set(scenes.keys())
    board_per, board_label = _board_peripherals(data)

    for scene_name, scene in scenes.items():
        pfx = f"{file_label}: {scene_name}"
        widgets = scene.get("widgets") or []
        widget_ids: set[str] = set()
        for w in widgets:
            if isinstance(w, dict):
                wid = w.get("_widget_id") or w.get("id")
                if isinstance(wid, str) and wid:
                    widget_ids.add(wid)

        # ── Per-widget events ──
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            ev = w.get("events")
            if ev is None:
                continue
            ref = _wref(scene_name, w, idx)
            if not isinstance(ev, dict):
                issues.append(Issue("ERROR", f"{pfx}: {ref}: 'events' must be an object"))
                continue
            wid = w.get("_widget_id") or w.get("id")
            for ek, acts in ev.items():
                if ek not in _LOGIC_WIDGET_EVENTS:
                    issues.append(Issue("ERROR", f"{pfx}: {ref}: unknown event handler {ek!r}"))
                    continue
                if not isinstance(acts, list) or not acts:
                    issues.append(Issue("WARN", f"{pfx}: {ref}: events.{ek} is empty"))
                    continue
                if not (isinstance(wid, str) and wid):
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{pfx}: {ref}: widget has events but no id — handlers "
                            f"cannot be wired in firmware",
                        )
                    )
                for ai, a in enumerate(acts):
                    issues.extend(
                        _validate_action(
                            a,
                            f"{pfx}: {ref}: events.{ek}[{ai}]",
                            scene_names,
                            widget_ids,
                            board_per,
                            board_label,
                        )
                    )

        # ── Per-scene rules ──
        rules = scene.get("rules")
        if rules is None:
            continue
        if not isinstance(rules, list):
            issues.append(Issue("ERROR", f"{pfx}: 'rules' must be a list"))
            continue
        for r_i, rule in enumerate(rules):
            rl = f"{pfx}: rule[{r_i}]"
            if not isinstance(rule, dict):
                issues.append(Issue("ERROR", f"{rl}: rule must be an object"))
                continue
            trig = rule.get("trigger")
            if not isinstance(trig, dict):
                issues.append(Issue("ERROR", f"{rl}: missing/invalid 'trigger'"))
            else:
                tt = str(trig.get("type", "")).strip().lower()
                if tt not in _LOGIC_TRIGGERS:
                    issues.append(Issue("ERROR", f"{rl}: bad trigger type {tt!r}"))
                elif tt == "timer":
                    if not _is_int(trig.get("timer_id")) or not (
                        0 <= int(trig.get("timer_id")) <= 15
                    ):
                        issues.append(Issue("ERROR", f"{rl}: timer 'timer_id' must be 0..15"))
                elif tt == "gpio_in":
                    if not _is_int(trig.get("pin")):
                        issues.append(Issue("ERROR", f"{rl}: gpio_in needs int 'pin'"))
                    edge = str(trig.get("edge", "any")).lower()
                    if edge not in ("any", "rising", "falling"):
                        issues.append(Issue("ERROR", f"{rl}: gpio_in bad 'edge' {edge!r}"))
                elif tt == "widget":
                    twid = trig.get("widget")
                    if not isinstance(twid, str) or not twid:
                        issues.append(Issue("ERROR", f"{rl}: widget trigger needs 'widget'"))
                    elif twid not in widget_ids:
                        issues.append(
                            Issue("ERROR", f"{rl}: widget trigger -> unknown id {twid!r}")
                        )
                    wev = str(trig.get("event", "on_press")).lower()
                    if wev not in _LOGIC_WIDGET_EVENTS:
                        issues.append(Issue("ERROR", f"{rl}: widget trigger bad event {wev!r}"))

            conds = rule.get("conditions")
            if conds is not None:
                if not isinstance(conds, list):
                    issues.append(Issue("ERROR", f"{rl}: 'conditions' must be a list"))
                else:
                    for ci, c in enumerate(conds):
                        cl = f"{rl}: cond[{ci}]"
                        if not isinstance(c, dict):
                            issues.append(Issue("ERROR", f"{cl}: must be an object"))
                            continue
                        if str(c.get("op", "")) not in _LOGIC_OPS:
                            issues.append(Issue("ERROR", f"{cl}: bad op {c.get('op')!r}"))
                        m = _logic_operand_issue(c.get("lhs"), f"{cl}.lhs", widget_ids)
                        if m:
                            issues.append(Issue("ERROR", m))
                        m = _logic_operand_issue(c.get("rhs"), f"{cl}.rhs", widget_ids)
                        if m:
                            issues.append(Issue("ERROR", m))
                        jn = c.get("join", "&&")
                        if jn not in ("&&", "||"):
                            issues.append(Issue("ERROR", f"{cl}: bad join {jn!r}"))

            acts = rule.get("actions")
            if not isinstance(acts, list) or not acts:
                issues.append(Issue("ERROR", f"{rl}: 'actions' must be a non-empty list"))
            else:
                for ai, a in enumerate(acts):
                    issues.extend(
                        _validate_action(
                            a,
                            f"{rl}: actions[{ai}]",
                            scene_names,
                            widget_ids,
                            board_per,
                            board_label,
                        )
                    )
    return issues


def _scenes_from_data(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scenes_raw = data.get("scenes", {})
    if isinstance(scenes_raw, dict):
        out: dict[str, dict[str, Any]] = {}
        for name, scene in scenes_raw.items():
            if isinstance(scene, dict):
                out[str(name)] = scene
        return out
    if isinstance(scenes_raw, list):
        out = {}
        for i, scene in enumerate(scenes_raw):
            if not isinstance(scene, dict):
                continue
            name = str(scene.get("id") or scene.get("name") or f"scene_{i}")
            out[name] = scene
        return out
    return {}


def _wref(scene_name: str, w: dict[str, Any], idx: int) -> str:
    wid = w.get("_widget_id") or w.get("id") or f"#{idx}"
    return f"scene '{scene_name}': widget[{idx}] ({wid})"


def _widget_group(w: dict[str, Any]) -> str:
    """Return the group prefix from ``_widget_id`` (part before first '.')."""
    wid = w.get("_widget_id") or w.get("id") or ""
    if not isinstance(wid, str):
        return ""
    dot = wid.find(".")
    return wid[:dot] if dot > 0 else wid


def _rect_contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    """True if the ``outer`` (x, y, x2, y2) rect fully encloses ``inner``."""
    ox, oy, ox2, oy2 = outer
    ix, iy, ix2, iy2 = inner
    return ox <= ix and oy <= iy and ox2 >= ix2 and oy2 >= iy2


def _overlap_is_benign(
    a: dict[str, Any],
    b: dict[str, Any],
    rect_a: tuple[int, int, int, int],
    rect_b: tuple[int, int, int, int],
) -> bool:
    """Decide whether an overlapping widget pair is *intentional* layering
    rather than a collision defect.

    This UI model has no real z plane — widgets composite in array / draw
    order. Two principled, narrowly-scoped exemptions cover every legitimate
    overlap pattern without disabling collision detection in general:

    1. **Hidden overlay.** If either widget is ``visible: false`` it cannot
       visually collide with anything; a deliberately hidden toast/notification
       panel parked over the hint band is correct by design.
    2. **Background / container layering.** If one widget is a container type
       (``panel``/``box``) that *fully contains* the other, it is acting as the
       backdrop/frame the other is drawn on top of (title-bar panel behind its
       label/badge; content panel behind its child labels/buttons). The
       containment requirement is what keeps this principled: a panel that only
       *partially* clips an unrelated widget is still flagged.

    Anything else — two visible, mutually non-containing widgets (e.g. two
    labels stomping each other) — is a genuine layout defect and is NOT
    exempted.
    """
    if a.get("visible") is False or b.get("visible") is False:
        return True
    a_type = a.get("type")
    b_type = b.get("type")
    if a_type in CONTAINER_WIDGET_TYPES and _rect_contains(rect_a, rect_b):
        return True
    return b_type in CONTAINER_WIDGET_TYPES and _rect_contains(rect_b, rect_a)


# ── Cteni bloku "navrh" a pravidla, ktera z nej ziji ───────────────────────


def _obdelnik4(v: object) -> tuple[int, int, int, int] | None:
    """``[x, y, sirka, vyska]`` jako ctyri cela cisla, jinak ``None``."""
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    if not all(_is_int(c) for c in v):
        return None
    return (int(v[0]), int(v[1]), int(v[2]), int(v[3]))


def _nezaporne_cislo(v: object) -> float | None:
    """Nezaporne cislo v px (int i float), jinak ``None``. Bool cislo NENI."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v >= 0 else None


def _zhustit_mezery(text: str) -> str:
    """Text bez okrajovych mezer a s jednou mezerou misto kazde skupiny.

    Rule 143 porovnava vety, ne bajty: sazba muze pridat mezeru navic
    (nebo pevnou mezeru z generatoru) a slovnik by pak neplatil pro nic.
    """
    return " ".join(text.split())


def _vycet_a(casti: list[str]) -> str:
    """Cesky vycet: ``['a', 'b', 'c']`` -> ``'a, b a c'``."""
    if len(casti) == 1:
        return casti[0]
    return ", ".join(casti[:-1]) + " a " + casti[-1]


def _navrh_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
    znama_id: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[int, int, int, int]], list[Issue]]:
    """Precte scenovy blok ``navrh`` -> (prvky, pasy, nalezy o vadnem bloku).

    Chybejici blok = prazdno a ZADNY nalez (pravidla nad merenim pak mlci).
    Vadny blok = nalez ke KAZDEMU vadnemu klici a zahozeni jen te jedne
    hodnoty; zbytek prvku se cte dal. Merene cislo, ktere se tise zahodi, je
    horsi nez zadne mereni: pravidlo by pak mlcelo a vypadalo by to jako
    "v poradku".
    """
    issues: list[Issue] = []
    prvky: dict[str, dict[str, Any]] = {}
    pasy: dict[str, tuple[int, int, int, int]] = {}

    blok = scene.get(NAVRH_KLIC)
    if blok is None:
        return prvky, pasy, issues
    if not isinstance(blok, dict):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: '{NAVRH_KLIC}' ma byt objekt, "
                f"je {type(blok).__name__}",
            )
        )
        return prvky, pasy, issues

    pasy_raw = blok.get("pasy")
    if pasy_raw is not None:
        if not isinstance(pasy_raw, dict):
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'pasy' ma byt objekt, "
                    f"je {type(pasy_raw).__name__}",
                )
            )
        else:
            for jmeno, rect_raw in pasy_raw.items():
                rect = _obdelnik4(rect_raw)
                if rect is None or rect[2] <= 0 or rect[3] <= 0:
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'pasy.{jmeno}' ma byt ctyri cela "
                            f"cisla [x, y, sirka, vyska] s kladnymi rozmery, je {rect_raw!r}",
                        )
                    )
                    continue
                pasy[str(jmeno)] = rect

    prvky_raw = blok.get("prvky")
    if prvky_raw is None:
        return prvky, pasy, issues
    if not isinstance(prvky_raw, dict):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky' ma byt objekt, "
                f"je {type(prvky_raw).__name__}",
            )
        )
        return prvky, pasy, issues

    for wid_raw, prvek_raw in prvky_raw.items():
        wid = str(wid_raw)
        if not isinstance(prvek_raw, dict):
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}' ma byt objekt, "
                    f"je {type(prvek_raw).__name__}",
                )
            )
            continue
        if wid not in znama_id:
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}' neodpovida zadnemu widgetu "
                    f"sceny - merena data se zahazuji",
                )
            )
        # Nezname klice (role, prazdne, vec ...) se nesou dal beze zmeny:
        # patri pravidlum, ktera se sem teprve pridaji.
        prvek: dict[str, Any] = {
            k: v
            for k, v in prvek_raw.items()
            if k
            not in (
                "rodic",
                "pas",
                "sirka_textu",
                "sirka_bunky",
                "role",
                "prazdne",
                "presah",
                "vec",
                "orez",
                "font_size",
                "enabled",
            )
        }
        rodic_raw = prvek_raw.get("rodic")
        if rodic_raw is not None:
            rodic = _obdelnik4(rodic_raw)
            if rodic is None:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.rodic' ma byt ctyri cela "
                        f"cisla [x, y, sirka, vyska], je {rodic_raw!r}",
                    )
                )
            else:
                prvek["rodic"] = rodic
        pas_raw = prvek_raw.get("pas")
        if pas_raw is not None:
            if not isinstance(pas_raw, str) or not pas_raw.strip():
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.pas' ma byt jmeno pasu, "
                        f"je {pas_raw!r}",
                    )
                )
            elif pas_raw not in pasy:
                # Prvek se hlasi do pasu, ktery scena nezna: vyjimka by se
                # neuplatnila na nic a pravidlo by prvek obvinilo z cizi viny.
                znam = ", ".join(sorted(pasy)) or "zadny"
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.pas' odkazuje na neznamy "
                        f"pas '{pas_raw}' (znam: {znam})",
                    )
                )
            else:
                prvek["pas"] = pas_raw
        rodic_id_raw = prvek_raw.get("rodic_id")
        if rodic_id_raw is not None:
            # Jmeno nejblizsiho predka, ktery je taky ve scene. Rule 138 se
            # jim pta na PRISLUSNOST misto na prekryv (viz `_text_uvnitr`).
            # Odkaz na neznamy prvek se zahazuje NAHLAS: tise by z nej byl
            # vypnuty rodokmen a vyjimka "uvnitr sebe" by prestala platit
            # bez jedineho slova.
            if not isinstance(rodic_id_raw, str) or not rodic_id_raw.strip():
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.rodic_id' ma byt jmeno "
                        f"prvku, je {rodic_id_raw!r}",
                    )
                )
            elif rodic_id_raw.strip() not in znama_id:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.rodic_id' odkazuje na "
                        f"prvek '{rodic_id_raw}', ktery ve scene neni",
                    )
                )
            elif rodic_id_raw.strip() == wid:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.rodic_id' ukazuje sam "
                        f"na sebe",
                    )
                )
            else:
                prvek["rodic_id"] = rodic_id_raw.strip()
        role_raw = prvek_raw.get("role")
        if role_raw is not None:
            if not isinstance(role_raw, str) or not role_raw.strip():
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.role' ma byt jmeno role, "
                        f"je {role_raw!r}",
                    )
                )
            elif role_raw.strip().lower() not in ROLE_ZNAME:
                # Preklep v roli nesmi pravidlo TISE vypnout: role je jediny
                # klic, kterym se Rule 138/139 vubec pousti, takze 'hodnta'
                # misto 'hodnota' by prazdny smalt umlcelo natrvalo.
                issues.append(
                    Issue(
                        "WARN",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.role' je nezname jmeno role "
                        f"'{role_raw}' (znam: {', '.join(sorted(ROLE_ZNAME))}) - merena data "
                        f"se zahazuji",
                    )
                )
            else:
                prvek["role"] = role_raw.strip().lower()
        # Zamerny presah rodice. Tataz uvaha jako u `prazdne` u Rule 138:
        # bez oznaceni se prvni zamerne precnivajici prvek (odznak pres roh
        # karty, popisek zony NAD svym boxem) stane duvodem, proc nekdo
        # vypne cele pravidlo. Zmereno: na listu Main kitu jsou dva takove
        # popisky (`u.35`, `u.54`, 20 px nad boxem zony) a nic se na nich
        # neoreze - `.zona` nema `overflow:hidden`.
        #
        # Oznaceni umlci JEN rodicovskou pulku. Zasah do vyhrazeneho pasu
        # a utek clena z pasu se jim vypnout NEDA: pas je slib o miste,
        # ktere patri nekomu jinemu, a ten slib nemuze zrusit ten, kdo ho
        # porusuje.
        presah_raw = prvek_raw.get("presah")
        if presah_raw is not None:
            if not isinstance(presah_raw, str):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.presah' ma byt veta o tom, "
                        f"proc prvek precniva, je {presah_raw!r}",
                    )
                )
            elif not presah_raw.strip():
                issues.append(
                    Issue(
                        "WARN",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.presah' je prazdne oznaceni "
                        f"bez vety - vypinac pravidla bez duvodu se zahazuje",
                    )
                )
            else:
                prvek["presah"] = presah_raw.strip()
        prazdne_raw = prvek_raw.get("prazdne")
        if prazdne_raw is not None:
            if not isinstance(prazdne_raw, str):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.prazdne' ma byt veta o tom, "
                        f"proc je prvek prazdny, je {prazdne_raw!r}",
                    )
                )
            elif not prazdne_raw.strip():
                # Oznaceni bez vety je jen vypinac pravidla. Zahazuje se, aby
                # Rule 138 dobehla - a rekne se to nahlas, jinak by po nem
                # zbylo ticho vypadajici jako "v poradku".
                issues.append(
                    Issue(
                        "WARN",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.prazdne' je prazdne oznaceni "
                        f"- zamer bez vety neni zamer, oznaceni se zahazuje",
                    )
                )
            else:
                prvek["prazdne"] = prazdne_raw
        vec_raw = prvek_raw.get("vec")
        if vec_raw is not None:
            # Vec je lidske slovo ("microSD"), ne identifikator: nechava se,
            # jak ji napsal generator, a paruje se se slovnikem bez ohledu na
            # velikost pismen (viz `_slovnik_ze_sceny`).
            if not isinstance(vec_raw, str) or not vec_raw.strip():
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.vec' ma byt jmeno veci, "
                        f"o ktere prvek mluvi, je {vec_raw!r}",
                    )
                )
            else:
                prvek["vec"] = vec_raw.strip()
        orez_raw = prvek_raw.get("orez")
        if orez_raw is not None:
            # OREZ JE JEDNO MERENI, NE CTYRI. Vsechny ctyri hodnoty vznikaji
            # z JEDNOHO odectu vykresleneho DOM (`scrollWidth`/`clientWidth`
            # a jejich svisle protejsky), takze pulka mereni neni "mezera
            # v pokryti", ale rozbita smlouva - a ta se hlasi NAHLAS a cela
            # se zahodi. Kdyby se pulka nechala projit, mel by tu vzniknout
            # tvar "kontrola NEPROBEHLA", ktery by nad dnesnim mostem nikdy
            # nenastal - a mrtva vetev je horsi nez zadna (kritik ji nasel
            # u `ZNACKA_R137_NEMERENO`).
            if not isinstance(orez_raw, dict):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.orez' ma byt objekt "
                        f"se ctyrmi rozmery {list(OREZ_KLICE)}, je "
                        f"{type(orez_raw).__name__}",
                    )
                )
            else:
                orez: dict[str, float] = {}
                spatne = False
                for klic in OREZ_KLICE:
                    hod = _nezaporne_cislo(orez_raw.get(klic))
                    if hod is None:
                        spatne = True
                        issues.append(
                            Issue(
                                "ERROR",
                                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.orez.{klic}' "
                                f"ma byt nezaporne cislo v px, je "
                                f"{orez_raw.get(klic)!r}",
                            )
                        )
                    else:
                        orez[klic] = hod
                navic = sorted(set(orez_raw) - set(OREZ_KLICE))
                if navic:
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.orez' zna klice "
                            f"{', '.join(navic)}, ktere pravidla 144 a 145 neumi "
                            f"(znam: {', '.join(OREZ_KLICE)})",
                        )
                    )
                if not spatne and not navic:
                    prvek["orez"] = orez
        font_raw = prvek_raw.get("font_size")
        if font_raw is not None:
            # Rez pisma v px. Sam o sobe dnes ZADNE pravidlo nespousti - je
            # to nosic pro pravidla 148 (rez mimo zavaznou skalu) a 149
            # (uhlova velikost znaku) a pro rozsireni Rule 17 o mez velkeho
            # textu. Cte se uz ted, aby smlouva o atributech byla JEDNA
            # a most ji nemusel menit dvakrat.
            hod = _nezaporne_cislo(font_raw)
            if hod is None or hod <= 0:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.font_size' ma byt "
                        f"kladne cislo v px, je {font_raw!r}",
                    )
                )
            else:
                prvek["font_size"] = hod
        enabled_raw = prvek_raw.get("enabled")
        if enabled_raw is not None:
            # Je ovladac ciny? Nosic pro vyjimku WCAG 1.4.3 (neaktivni
            # ovladac nema predepsany kontrast) v rozsireni Rule 17.
            # Musi to byt PRAVDIVOSTNI hodnota: retezec "false" je v Pythonu
            # pravdivy, takze by vyjimku tise otocil naruby.
            if not _is_bool(enabled_raw):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.enabled' ma byt true "
                        f"nebo false, je {enabled_raw!r}",
                    )
                )
            else:
                prvek["enabled"] = bool(enabled_raw)
        tucne_raw = prvek_raw.get("tucne")
        if tucne_raw is not None:
            # Je rez TUCNY? Druha polovina meze "velky text" ve WCAG 2.1
            # (>= 19 px tucne se pocita stejne jako >= 24 px bezne).
            # Musi to byt PRAVDIVOSTNI hodnota ze stejneho duvodu jako
            # u `enabled`: retezec "false" je v Pythonu pravdivy, takze by
            # mez tise povolil o pet pixelu niz.
            if not _is_bool(tucne_raw):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.tucne' ma byt true "
                        f"nebo false, je {tucne_raw!r}",
                    )
                )
            else:
                prvek["tucne"] = bool(tucne_raw)
        for klic in ("inkoust", "podklad"):
            barva_raw = prvek_raw.get(klic)
            if barva_raw is None:
                continue
            # VIDENA dvojice pro Rule 17: popredi a pozadi uz se slozenou
            # alfou a `opacity`. Scenove `color_fg`/`color_bg` zustavaji
            # tim, cim byla - barvou, kterou generator NAPSAL, protoze
            # prave na ni se pta Rule 150. Dve otazky, dve pole.
            if not isinstance(barva_raw, str) or _parse_color(barva_raw) is None:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.{klic}' ma byt "
                        f"barva, je {barva_raw!r}",
                    )
                )
            else:
                prvek[klic] = barva_raw
        vsazka_raw = prvek_raw.get("vsazka")
        if vsazka_raw is not None:
            # Vlastni odsazeni bloku (Rule 151). NENI to vypinac pravidla:
            # klavesnicovy blok ma okraj 8 px misto 16 a meri se PROTI
            # NEMU, takze klavesa, ktera se do vlastni soustavy bloku
            # netrefi, nalez porad dostane.
            hod = _nezaporne_cislo(vsazka_raw)
            if hod is None or hod <= 0:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.vsazka' ma byt kladne "
                        f"cislo v px, je {vsazka_raw!r}",
                    )
                )
            else:
                prvek["vsazka"] = hod
        for klic in ("sirka_textu", "sirka_bunky"):
            hod_raw = prvek_raw.get(klic)
            if hod_raw is None:
                continue
            hod = _nezaporne_cislo(hod_raw)
            if hod is None:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'prvky.{wid}.{klic}' ma byt nezaporne "
                        f"cislo v px, je {hod_raw!r}",
                    )
                )
            else:
                prvek[klic] = hod
        prvky[wid] = prvek

    return prvky, pasy, issues


def _r136_nalezy(
    wl: str,
    prvek: dict[str, Any],
    rect: tuple[int, int, int, int],
    scena: tuple[int, int],
    pasy: dict[str, tuple[int, int, int, int]],
) -> list[Issue]:
    """Rule 136: prvek presahuje sveho rodice / leze do vyhrazeneho pasu.

    Dva tvary tehoz oriznuti. Zivy protejsek obou: dlazdice RF Sonda na
    Domove, ktere patka usekla spodni hranu.

    Kdo tu MLCI a proc (jinak by na jednom pixelu stala dve meridla):

    * **Rodic je scena** -> mlci. Hranice sceny uz meri Rule 63 (vic nez
      75 % venku), Rule 79 (vetsi nez scena) a Rule 80.
    * **Panel za svym obsahem** -> mlci. Dite uvnitr sveho rodice je prave ta
      "intentional layering", kterou hlasi Rule 21; R136 se pta obracene nez
      Rule 21 ("je dite uvnitr sveho rodice?"), takze spravne slozeny panel
      projde obema.
    * **Prvek, ktery do pasu patri** (``pas`` == jmeno pasu) -> do nej smi,
      ale musi v nem lezet CELY. Jeho presah VEN meri treti pulka pravidla
      (`ZNACKA_R136_PAS_VEN`).

      OPRAVENO 2026-09-09, a je to poucne. Docstring tu do te chvile tvrdil,
      ze treti meridlo neni potreba, protoze "v kitu je obal pasu zaroven
      ``offsetParent`` jeho obsahu, takze ``rodic`` takoveho prvku JE
      obdelnik pasu". Kritik to ZMERIL na vsech 62 listech a vyslo:
      **0 z 368 clenu pasu ma rodice rovneho obdelniku pasu** - most vydava
      ``rodic = ramecek(el.offsetParent)`` a ``offsetParent`` clenu razitka
      je ``.obsah``, ne obal pasu. Hodnota razitka nakreslena 52 px NAD
      pasem prosla mlckym. Diru zaviraly jen data, ktera most nikdy
      neposilal - a fixtura ji pribijela ve tvaru, ktery most nevyrabi.
      Poucení: predpoklad o datech mostu se overuje MERENIM nad skutecnymi
      scenami, ne cetbou generatoru.
    * **Prvek CELY uvnitr pasu** -> jen WARN, ne ERROR: oriznout ho pas nemuze,
      chybi mu jen prihlaska (nebo zabloudil pod patku). Oriznuti je prave a
      jen preteti HRANY pasu.
    * **Prvek, ktery pas CELY obsahuje** -> mlci. Obal obsahu, uvnitr ktereho
      patka sedi, pas nenarusuje: je to podklad, na kterem pas lezi.
    * **``visible: false``** -> preskok, stejne jako v Rule 135.

    Pas se naproti tomu meri i prvku, ktery v bloku vlastni zaznam NEMA - pas
    je vlastnost sceny, ne prvku, a nezmereny prvek by jinak patku prosel
    mlcky. Rodic se meri jen tomu, kdo ho zmereneho ma.

    Pozor na jeden nevysloveny predpoklad: u popisku posila most INKOUST, ne
    ramecek, takze inkoust je vzdy uvnitr boxu a falesny nalez z tohohle
    titulu vzniknout nemuze. Az most zacne posilat box, tenhle odstavec
    prestane platit.
    """
    issues: list[Issue] = []
    x, y, w, h = rect
    x2, y2 = x + w, y + h
    sw, sh = scena

    def _presahy(ox: int, oy: int, ox2: int, oy2: int) -> dict[str, str]:
        """{smer: 'smer o N px'} pro hrany, ktere prvek pretl aspon o prah."""
        return {
            smer: f"{smer} o {kolik} px"
            for smer, kolik in (
                ("vlevo", ox - x),
                ("nahore", oy - y),
                ("vpravo", x2 - ox2),
                ("dole", y2 - oy2),
            )
            if kolik >= R136_PRAH_PX
        }

    muj_pas = prvek.get("pas")
    # Treti meridlo: clen pasu musi lezet CELY uvnitr sveho pasu. Bez nej
    # projde mlckym prvek, ktery se z pasu vysunul - a prave to je oriznuti
    # patkou, kvuli kteremu pravidlo vzniklo. Meri se jen prvku, ktery se do
    # pasu HLASI a jehoz pas scena zna (neznamy pas hlasi ctecka bloku).
    #
    # Meri se PRVNI, protoze pas lezi uvnitr rodice: kdyz clen pretece obe
    # hranice tymz smerem (patka razitka sedi na spodni hrane `.obsah`, takze
    # se dolni hrany kryji), je to JEDNA obet a nalez ma nest to TESNEJSI
    # meridlo. Rodicovska pulka pak tenhle smer uz nehlasi.
    ven_smery: set[str] = set()
    if muj_pas in pasy:
        px, py, pw, ph = pasy[muj_pas]
        ven = _presahy(px, py, px + pw, py + ph)
        if ven:
            ven_smery = set(ven)
            issues.append(
                Issue(
                    "ERROR",
                    f"{wl}: {ZNACKA_R136_PAS_VEN} '{muj_pas}' {_vycet_a(list(ven.values()))} "
                    f"(prvek {x},{y} {w}x{h}, pas {px},{py} {pw}x{ph})",
                )
            )

    rodic = prvek.get("rodic")
    if rodic is not None:
        rx, ry, rw, rh = rodic
        rx2, ry2 = rx + rw, ry + rh
        je_scena = rx <= 0 and ry <= 0 and rx2 >= sw and ry2 >= sh
        if not je_scena:
            presahy = [
                popis
                for smer, popis in _presahy(rx, ry, rx2, ry2).items()
                if smer not in ven_smery
            ]
            oznaceni = prvek.get("presah")
            if presahy and oznaceni:
                # Zamerny presah: rekne se to, ale jako WARN. Uplne ticho by
                # znamenalo, ze oznaceni je vypinac, o kterem se v souhrnu
                # nikdo nedozvi.
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: {ZNACKA_R136_OZNACENI}: {_vycet_a(presahy)} - "
                        f"{oznaceni}",
                    )
                )
            elif presahy:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{wl}: {ZNACKA_R136_RODIC} {_vycet_a(presahy)} "
                        f"(prvek {x},{y} {w}x{h}, rodic {rx},{ry} {rw}x{rh})",
                    )
                )
            elif oznaceni:
                # Oznaceni na prvku, ktery nikam nepresahuje. Tataz vada jako
                # u `prazdne` na prvku s textem: zustalo tu po zmene, kterou
                # uz nikdo nehlida, a pristi presah umlci mlcky.
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: {ZNACKA_R136_OZNACENI}: prvek je oznaceny jako zamerne "
                        f"precnivajici ('{oznaceni}'), ale sveho rodice nepresahuje - "
                        f"oznaceni uz neplati",
                    )
                )

    for jmeno in sorted(pasy):
        if jmeno == muj_pas:
            continue
        px, py, pw, ph = pasy[jmeno]
        px2, py2 = px + pw, py + ph
        # Dotek neni zasah: pas je polootevreny interval, presah pod prah
        # mereni je artefakt zaokrouhleni mostu.
        if min(x2, px2) - max(x, px) < R136_PRAH_PX:
            continue
        if min(y2, py2) - max(y, py) < R136_PRAH_PX:
            continue
        # Prvek, ktery pas CELY obsahuje, je podklad, na kterem pas lezi
        # (obal obsahu, uvnitr ktereho patka sedi), ne narusitel - tataz
        # vyjimka, jakou ma Rule 21 pro panel za svym obsahem.
        if _rect_contains((x, y, x2, y2), (px, py, px2, py2)):
            continue
        # Prvek CELY uvnitr pasu nemuze byt oriznuty - je to bud vlastni obsah
        # pasu, kteremu jen chybi prihlaska (`pas`), nebo prvek zabloudily pod
        # patku. Oriznuti to ale NENI, takze to nesmi nest tutez zavaznost:
        # ERROR by tu meril jinou velicinu, nez pravidlo slibuje.
        if _rect_contains((px, py, px2, py2), (x, y, x2, y2)):
            issues.append(
                Issue(
                    "WARN",
                    f"{wl}: {ZNACKA_R136_PAS} '{jmeno}': lezi cely uvnitr pasu, ale nehlasi "
                    f"se do nej (prvek {x},{y} {w}x{h}, pas {px},{py} {pw}x{ph}); kdyz do "
                    f"pasu patri, ma to rict navrh.prvky[<id>].pas",
                )
            )
            continue
        # Nejmelci pruhyb rekne, KTEROU hranu prvek pretl - to je cislo,
        # ktere se opravuje.
        hloubka, popis = min(
            (
                (y2 - py, f"prvek konci na y={y2}, pas zacina na y={py}"),
                (py2 - y, f"prvek zacina na y={y}, pas konci na y={py2}"),
                (x2 - px, f"prvek konci na x={x2}, pas zacina na x={px}"),
                (px2 - x, f"prvek zacina na x={x}, pas konci na x={px2}"),
            ),
            key=lambda dvojice: dvojice[0],
        )
        issues.append(Issue("ERROR", f"{wl}: {ZNACKA_R136_PAS} '{jmeno}' o {hloubka} px ({popis})"))
    return issues


def _r137_nalezy(wl: str, prvek: dict[str, Any], text: str) -> list[Issue]:
    """Rule 137: zmerena sirka textu > sirka jeho bunky.

    Nahrada Rule 7 pro panely, kde most mericem v prohlizeci zmeril SKUTECNY
    font. Rule 7 je znakovy odhad pro font 6x8 a na tab5 ma ``char_w=2`` jako
    dolni mez, tj. je zamerne neobvinujici - proto se pro zmereny widget jeho
    vodorovna pulka vypina (svisla zustava, ta meri vysku, ne sirku). Dve
    meridla s ruznymi predpoklady na jednom pixelu by byla presne ta druha
    pravda, kterou tahle brana ma odstranit.

    ``text_overflow: "ellipsis"`` NEOMLOUVA: useknuty stitek FIRMWARE
    "V0.4-71-gee91351-dirty" na skutecnem panelu je prave ten pripad -
    trojtecka neni sdeleni, je to ztraceny konec.

    Kdyz je zmerena jen jedna z obou sirek, kontrola NEPROBEHLA a rekne se to
    (WARN), misto aby pravidlo mlcelo, jako by bylo cisto.
    """
    sirka_textu = prvek.get("sirka_textu")
    sirka_bunky = prvek.get("sirka_bunky")
    if sirka_textu is not None and sirka_bunky is not None:
        pretok = sirka_textu - sirka_bunky
        if pretok > R137_TOLERANCE_PX:
            # Text se cituje tak, jak ho scena nese. Prazdne uvozovky nejsou
            # chyba hlasky: znamenaji, ze most sirku zmeril, ale text sam do
            # sceny neposlal (dnes se to deje u sazby uvnitr <b>/<u>/<s>).
            return [
                Issue(
                    "ERROR",
                    f"{wl}: {ZNACKA_R137}: zmereno {sirka_textu:.1f} px, bunka ma "
                    f"{sirka_bunky:.1f} px (pretok {pretok:.1f} px), text '{text}'",
                )
            ]
        return []
    if sirka_textu is not None:
        return [
            Issue(
                "WARN",
                f"{wl}: {ZNACKA_R137_NEMERENO}: chybi 'sirka_bunky' "
                f"(zmerena je jen sirka textu {sirka_textu:.1f} px)",
            )
        ]
    if sirka_bunky is not None:
        return [
            Issue(
                "WARN",
                f"{wl}: {ZNACKA_R137_NEMERENO}: chybi 'sirka_textu' "
                f"(znama je jen sirka bunky {sirka_bunky:.1f} px)",
            )
        ]
    return []


def _texty_sceny(
    widgets: list[Any],
) -> list[tuple[int, str, tuple[int, int, int, int], str]]:
    """Viditelne texty sceny: ``(poradi, id, obdelnik (x,y,x2,y2), text)``.

    Rule 138 potrebuje vedet, kdo je ciho POTOMKA - a to se ze samotnych
    obdelniku vycist neda. Prislusnost vozi most (``navrh.prvky[id].
    rodic_id``); tenhle seznam je druha pulka paru, aby se nemusel prochazet
    cely seznam widgetu pri kazdem dotazu.
    """
    ven: list[tuple[int, str, tuple[int, int, int, int], str]] = []
    for i, cw in enumerate(widgets):
        if not isinstance(cw, dict) or cw.get("visible") is False:
            continue
        ct = cw.get("text")
        if not isinstance(ct, str) or not ct.strip():
            continue
        if not all(_is_int(cw.get(k)) for k in ("x", "y", "width", "height")):
            continue
        cx, cy = int(cw["x"]), int(cw["y"])
        wid = str(cw.get("_widget_id") or cw.get("id") or "")
        ven.append((i, wid, (cx, cy, cx + int(cw["width"]), cy + int(cw["height"])), ct))
    return ven


# Kolik urovni stromu se u `rodic_id` projde, nez to pravidlo vzda. Strom
# artboardu ma dnes nejvyse 5 urovni; 32 je strop proti CYKLU v datech
# (a > b > a), ktery by jinak zacyklil validator misto toho, aby ohlasil
# vadny blok.
R138_HLOUBKA = 32


def _je_potomek(wid: str, predek: str, prvky: dict[str, dict[str, Any]]) -> bool:
    """Je ``wid`` potomkem ``predek`` podle retezu ``rodic_id``?"""
    cur = wid
    for _ in range(R138_HLOUBKA):
        rodic = prvky.get(cur, {}).get("rodic_id")
        if not isinstance(rodic, str):
            return False
        if rodic == predek:
            return True
        cur = rodic
    return False


def _text_uvnitr(
    idx: int,
    wid: str,
    rect: tuple[int, int, int, int],
    rect_prvku: tuple[int, int, int, int],
    texty: list[tuple[int, str, tuple[int, int, int, int], str]],
    prvky: dict[str, dict[str, Any]],
    zna_rodic_id: bool,
) -> str | None:
    """Prvni text, ktery prvek ``wid`` nese UVNITR SEBE. ``None`` = zadny.

    OPRAVENO 2026-09-09. Puvodni podoba se ptala jen GEOMETRICKY ("lezi cely
    uvnitr meho obdelniku?") a to je prilis siroka vyjimka: kritik ji obesel
    tim, ze pod prazdny smalt polozil CIZI popisek, ktery s nim nema nic
    spolecneho - a pravidlo zmlklo. Prazdny smalt umlci cokoli, co pod nim
    nahodou lezi.

    "Uvnitr sebe" proto plati jen pro POTOMKY:

    * kdyz most vydava ``rodic_id`` (jmeno nejblizsiho predka, ktery je taky
      ve scene), jde se po retezu nahoru - to je presna DOM prislusnost;
    * kdyz ``rodic_id`` ve scene neni ANI JEDNOU (starsi scena, dokument
      editoru), pouzije se ``rodic`` = obdelnik ``offsetParent``u: text,
      jehoz offsetParent je PRESNE tenhle prvek, je jeho potomek. Je to
      hrubsi meridlo, ale porad se pta na PRISLUSNOST, ne na prekryv.

    Geometrie zustava jako druha podminka v obou vetvich: potomek, ktery
    z rodice utekl, uvnitr nej neni (a jeho oriznuti meri Rule 136).
    """
    for i, cid, r, ct in texty:
        if i == idx or not _rect_contains(rect, r):
            continue
        if zna_rodic_id:
            if _je_potomek(cid, wid, prvky):
                return ct
            continue
        if tuple(prvky.get(cid, {}).get("rodic") or ()) == rect_prvku:
            return ct
    return None


def _r138_nalezy(
    wl: str,
    wid: str,
    role: str,
    prvek: dict[str, Any],
    text: str,
    text_uvnitr: str | None,
) -> list[Issue]:
    """Rule 138: hodnotova role, ktera nenese zadne sdeleni.

    Zive protejsky: Terminal smalt PORT i PRIJATO prazdne, Files smalt VOLNO,
    USB sloupec "CO TO JE", SysMon TEPLOTA RADIA. Ze souradnic to videt neni:
    scena nese text, ale ne to, jestli ta plocha nejakou hodnotu SLIBUJE.
    Slib vozi ``role`` z generatoru; bez nej pravidlo mlci (datove gatovani,
    plati na kazdem panelu).

    Prazdno se hleda GEOMETRICKY, ne pres DOM: `ram.svorkovnice()` sazi text
    do deti (``<b>``), takze obal sam PRIMY text nema. Kdyz uvnitr obdelniku
    lezi cely jiny prvek s textem, sdeleni tam JE a pravidlo mlci.
    Cena teto vyjimky je poctiva mez, kterou je nutne znat: sedi-li ``role``
    na OBALU, ktery uvnitr nese svuj vlastni popisek ("PORT"), pravidlo
    chybejici hodnotu neuvidi. Role proto patri na hodnotu, ne na obal - a
    "zelena" na listu, kde je role na obalech, nic netvrdi.

    Kdo tu mlci a proc (jinak by jednu obet obvinila dve meridla):

    * **Rule 25** ("text widget with no text") uz dnes mlci u kazdeho prvku,
      ktery ma ``_widget_id`` - a prvek s merenou roli ho ma vzdy, protoze
      podle nej se merena data paruji. Dvojity nalez tedy vzniknout nemuze.
    * **Rule 139** meri NEPRAZDNY text; prazdny patri vyhradne sem.
    * **Rule 91** (text neni retezec) meri vadny TYP, ne prazdno - pri
      necitelnem textu se Rule 138 nepousti vubec.

    ``prazdne`` je jediny ustup: veta o tom, proc je plocha prazdna zamerne.
    Prazdny retezec ustupem NENI (zahazuje ho uz ctecka bloku) a stare
    oznaceni na prvku, ktery text zase nese, se pripomene - jinak by v datech
    zustal trvaly vypinac pravidla.
    """
    prazdne = prvek.get("prazdne")
    if text.strip():
        if prazdne:
            return [
                Issue(
                    "WARN",
                    f"{wl}: {ZNACKA_R138_OZNACENI}: prvek je oznaceny jako zamerne prazdny "
                    f"('{prazdne}'), ale text nese: '{text}'",
                )
            ]
        return []
    if prazdne or text_uvnitr is not None:
        return []
    return [
        Issue(
            "ERROR",
            f"{wl}: {ZNACKA_R138}: role '{role}' nenese zadny text ani uvnitr sebe; "
            f"nedostupnost se rekne vetou, nebo se prvek oznaci jako zamerne prazdny "
            f"(navrh.prvky['{wid}'].prazdne)",
        )
    ]


_R139_SLOT = re.compile(
    r"(?<!\S)(\S+)[ \t]+(?:" + "|".join(re.escape(p) for p in sorted(POMLCKY)) + r")(?!\S)"
)


def _r139_prazdne_sloty(text: str) -> list[str]:
    """Jmena slotu, ktere v jednom prvku nesou pomlcku misto hodnoty.

    Hleda DVE A VIC po sobe jdoucich skupin "slovo mezera pomlcka", tedy tvar
    ``SOUBOR - OKNO - ZOBRAZENO -`` (patka Hexu z fotoprotokolu). Prazdny
    seznam = nic takoveho tam neni.

    Proc az od dvou: JEDNA skupina se od spravne hodnoty s oddelovacem
    nerozezna. "vlozena - nepripojena" ma presne tentyz tvar (slovo, mezera,
    pomlcka, ...) a je to hodnota v poradku. Cena je poctive priznana
    v `_r139_nalezy`: osamely slot s pomlckou projde.
    """
    sloty: list[str] = []
    konec = -1
    for m in _R139_SLOT.finditer(text):
        if sloty and text[konec:m.start()].strip():
            # Mezi skupinami stoji jeste jine slovo -> nejde o vycet slotu,
            # ale o vetu, ve ktere se pomlcka vyskytla dvakrat. Pocita se
            # znovu od teto skupiny.
            sloty = []
        sloty.append(m.group(1))
        konec = m.end()
    return sloty if len(sloty) >= 2 else []


def _r139_nalezy(wl: str, text: str) -> list[Issue]:
    """Rule 139: pomlcka (nebo jiny zastupny znak) misto hodnoty.

    Zive protejsky: Logic Analyzer "SPOUST —" a patka "—", prazdna patka
    v Hexu, hodnota dlazdice RF Sonda. Pomlcka je znacka, ne sdeleni: ctenar
    z ni nepozna, jestli se veci nikdo neptal, jestli odpoved nedosla, nebo
    jestli je vysledek prazdny. Nedostupnost se rika vetou (C4: pet forem
    nedostupnosti se ma sejit v jednu).

    Tri podoby teze vady, kazda s vlastnim pojmenovanim (opravuje se to, co
    tam doopravdy stoji), ale se stejnou zavaznosti:

    1. **Cely text je pomlcka** (``POMLCKY``, vcetne U+2010 a U+2011).
    2. **Cely text je zastupny znak** (``ZASTUPNE``: •, …, ?, n/a, --) nebo
       po odstraneni nulovych sirek nezbyde nic. Tvar je jiny, sdeleni
       stejne zadne. U+200B byl navic jediny znamy tvar, ktery obchazel
       Rule 138 i Rule 139 naraz: `strip()` ho nesmaze, takze prvek nebyl
       "prazdny", a v POMLCKY nebyl taky.
    3. **Vic slotu v jednom prvku** - patka Hexu "SOUBOR — OKNO —
       ZOBRAZENO —". Pravidlo merilo jen CELY text, takze generator, ktery
       nesazi kazdou hodnotu jako vlastni prvek, tri prazdne sloty protahl.

    Hranice tretiho tvaru je uzka schvalne a MA dolozitelnou cenu: hlasi se
    az DVE PO SOBE JDOUCI skupiny "slovo pomlcka", protoze jedna jedina se
    nedá odlisit od hodnoty s oddelovacem ("vlozena - nepripojena" je
    spravna hodnota se stejnym tvarem). Jeden osamely slot s pomlckou tedy
    projde - a je to napsane nahlas, misto aby to schoval sirsi vzor, ktery
    by zacal obvinovat spravne hodnoty.

    Kdo tu jeste mlci a proc:

    * PRAZDNY text patri VYHRADNE Rule 138 - jedna obet, jeden nalez;
    * pomlcka UVNITR delsiho textu ("1-13", "A-B") je oddelovac;
    * popiskova role (patka, popisek, titulek) pomlcku jako oddelovac mit
      smi - pravidlo se na ni vubec nepousti (viz volajici).
    """
    holy = text.strip()
    if not holy:
        # Prazdny text patri VYHRADNE Rule 138. Bez teto zavory by ho druha
        # vetev nize ("po odstraneni nulovych sirek nezbyde nic") obvinila
        # podruhe - jedna obet, dva nalezy.
        return []
    if holy in POMLCKY:
        return [
            Issue(
                "ERROR",
                f"{wl}: {ZNACKA_R139}: text '{text}' neni veta; rekni, co se stalo "
                f"(napr. 'spoust nenastavena')",
            )
        ]
    bez_nulovych = holy.strip(NULOVE_SIRKY).strip()
    if holy.lower() in ZASTUPNE or not bez_nulovych:
        return [
            Issue(
                "ERROR",
                f"{wl}: {ZNACKA_R139_ZASTUPNY}: text {text!r} neni veta; rekni, co se "
                f"stalo (napr. 'spoust nenastavena')",
            )
        ]
    sloty = _r139_prazdne_sloty(holy)
    if sloty:
        return [
            Issue(
                "ERROR",
                f"{wl}: {ZNACKA_R139}: {len(sloty)} slotu v jednom prvku nema hodnotu "
                f"({', '.join(sloty)}) - text '{text}'",
            )
        ]
    return []


def _r144_nalezy(wl: str, prvek: dict[str, Any], text: str) -> list[Issue]:
    """Rule 144: text, ktery SKUTECNE useknula jeho vlastni schranka.

    JINA VELICINA NEZ Rule 137, i kdyz obe mluvi o sirce. Rule 137 se pta,
    jestli se text vejde do BUNKY, kterou mu generator DEKLAROVAL
    (``data-bunka``, sloupec razitka) - to je otazka o rozvrzeni a odpoved
    "nevejde" znamena "sloupec je uzky", ne nutne "neco je pryc". Rule 144
    se pta, jestli prohlizec obsah opravdu OREZAL: ``sirka_obsahu``
    (``scrollWidth``) je sirka, kterou obsah potrebuje, ``sirka_schranky``
    (``clientWidth``) sirka, ktera je videt.

    Ze rozdil neni akademicky, je ZMERENE: ze sesti dnesnich nalezu Rule 137
    na 62 listech kitu jsou dva o textu, ktery se sve delici cary ani
    nedotkne (SvorkaCislice: inkoust konci 3,9 px PRED carou), a zadny
    z tech sesti prvku nema nad sebou ``overflow: hidden`` - takze se
    neuseklo nic. Kritik to hlasi jako reziduum R1 a tohle pravidlo ho
    zavira z druhe strany: kdyz Rule 144 mlci a Rule 137 hlasi, je vada
    v rozvrzeni; kdyz hlasi obe, je i v obsahu.

    Bez zmereneho ``orez`` pravidlo MLCI - tataz datova zavora jako
    u Rule 136 a 137. Pulka mereni sem nedojde: neuplny ``orez`` zahodi
    hlasite uz ctecka bloku (viz `_navrh_ze_sceny`).
    """
    orez = prvek.get("orez")
    if not orez:
        return []
    obsah = orez["sirka_obsahu"]
    schranka = orez["sirka_schranky"]
    pretok = obsah - schranka
    if pretok < R144_PRAH_PX:
        return []
    return [
        Issue(
            "ERROR",
            f"{wl}: {ZNACKA_R144}: obsah je {obsah:.0f} px siroky, videt je "
            f"{schranka:.0f} px (useklo se {pretok:.0f} px), text '{text}'",
        )
    ]


def _r145_nalezy(wl: str, prvek: dict[str, Any], text: str) -> list[Issue]:
    """Rule 145: text se zalomil do vic radku, nez pro nej bylo mista.

    Svisla pulka tehoz oriznuti. Zavira otevrene reziduum kritika (bod 7):
    "text, ktery se vodorovne vejde, ale je na dva radky v bunce vysoke na
    jeden -> TICHO; vyska bunky se do sceny nevozi vubec."

    Proc to nechyti zadne jine pravidlo: Rule 136 meri presah RODICE, jenze
    prvek se svisle NEPRETECE - schranka ho oreze a jeho obdelnik zustane
    presne tak vysoky, jak ma byt. Ven neceni nic; zmizi DRUHY RADEK, a to
    je videt jen na rozdilu ``vyska_obsahu`` proti ``vyska_schranky``.

    Zivy protejsek: kterykoli jednoradkovy stavovy radek, kteremu delsi
    preklad pridal slovo (nemecke "Nicht verbunden" na dva radky do boxu
    vysokeho 19 px).
    """
    orez = prvek.get("orez")
    if not orez:
        return []
    obsah = orez["vyska_obsahu"]
    schranka = orez["vyska_schranky"]
    pretok = obsah - schranka
    if pretok < R145_PRAH_PX:
        return []
    return [
        Issue(
            "ERROR",
            f"{wl}: {ZNACKA_R145}: obsah je {obsah:.0f} px vysoky, videt je "
            f"{schranka:.0f} px (useklo se {pretok:.0f} px dolu), text '{text}'",
        )
    ]


def _plochy_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
    znama_id: set[str],
) -> tuple[list[str], list[Issue]]:
    """Precte ``navrh.plochy`` -> (jmena prvku, nalezy o vadnem bloku).

    Smaltova plocha je PLOCHA, ne hodnota. Role ``smalt`` v ``prvky[*].role``
    rika "tenhle prvek NESE namerenou hodnotu" (meridlo Rule 138/139); tenhle
    seznam rika "tahle plocha JE smalt", tedy svetle pole, na kterem smi
    lezet jen tmavy inkoust, ktery na nej PATRI.

    Nese se to jmenem prvku, ne obdelnikem, a ma to duvod: obdelnik uz ve
    scene JE (plocha ma vypln, takze do sceny vstoupi), kdezto PRISLUSNOST
    se z obdelniku vycist neda - a prave o ni Rule 146 rozhoduje. Odkaz na
    prvek, ktery ve scene neni, je ERROR: tise zahozena plocha by pravidlo
    vypnula beze slova.
    """
    issues: list[Issue] = []
    plochy: list[str] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return plochy, issues
    raw = blok.get("plochy")
    if raw is None:
        return plochy, issues
    if not isinstance(raw, list):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'plochy' ma byt seznam jmen prvku, "
                f"je {type(raw).__name__}",
            )
        )
        return plochy, issues
    for i, jm_raw in enumerate(raw):
        if not isinstance(jm_raw, str) or not jm_raw.strip():
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'plochy[{i}]' ma byt jmeno prvku, "
                    f"je {jm_raw!r}",
                )
            )
            continue
        jm = jm_raw.strip()
        if jm not in znama_id:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'plochy[{i}]' odkazuje na prvek "
                    f"'{jm}', ktery ve scene neni",
                )
            )
            continue
        if jm not in plochy:
            plochy.append(jm)
    return plochy, issues


def _r146_nalezy(
    wl: str,
    wid: str,
    rect: tuple[int, int, int, int],
    text: str,
    plochy: list[tuple[str, tuple[int, int, int, int]]],
    prvky: dict[str, dict[str, Any]],
    zna_rodic_id: bool,
) -> list[Issue]:
    """Rule 146: cizi text lezici na smaltove plose (obracena polarita).

    Zakon jazyka (tabos-ui-kit/navrh-appky/ram.py): SVETLA SMALTOVA PLOCHA
    je fyzicka pravda pristroje a nese TMAVY inkoust. Text, ktery na smaltu
    LEZI, ale nepatri mu, se kresli barvou tmave strany - tedy svetlou na
    svetlem, nebo naopak. Stalo se to uz tretikrat (tlacitko Odpojit,
    popisek tridy .stitek, popisek vodopadu), a ani jednou to nechytila
    zadna kontrola prekryvu: obe plochy jsou "spravne", jen na sobe.

    Kdo tu MLCI a proc:

    * **Plocha sama** - je to jeji vlastni text.
    * **Potomek plochy** - inkoust, ktery na ni PATRI. Prislusnost se bere
      z retezu ``rodic_id`` (tataz cesta jako u Rule 138), ne z geometrie:
      geometricka verze by umlcela kazdy cizi popisek, ktery pod plochou
      nahodou lezi - presne ten obchvat, kterym kritik umlcel Rule 138.
      Kdyz scena ``rodic_id`` NENESE ANI JEDNOU (starsi scena, dokument
      editoru), spadne se na hrubsi meridlo ``rodic`` = obdelnik
      ``offsetParent``u, presne jako v `_text_uvnitr`. Bez teto zavory by
      pravidlo nad starou scenou obvinilo KAZDY text uvnitr KAZDEHO
      smaltu - a ze slepoty by delalo poplach misto ticha.
    * **Predek plochy** - podklad, uvnitr ktereho smalt sedi. Bez teto
      vyjimky by kazdy radek s vlastnim textem a se smaltovym stitkem
      uvnitr byl nalez: scena nese u popisku obdelnik CELEHO prvku, takze
      radek smalt geometricky obsahuje. Tataz vyjimka, jakou ma Rule 21
      pro "panel za svym obsahem" (`_overlap_is_benign`).
    * **Prekryv pod prah** - dotek hranou neni inkoust na smaltu.

    Pravidlo je gatovane PROFILEM (`polarita_smaltu`), ne daty: polarita je
    zakon TabOSu, ne vlastnost skla.
    """
    issues: list[Issue] = []
    x, y, w, h = rect
    x2, y2 = x + w, y + h
    for pid, (px, py, pw, ph) in plochy:
        if pid == wid:
            continue
        px2, py2 = px + pw, py + ph
        if min(x2, px2) - max(x, px) < R146_PRAH_PX:
            continue
        if min(y2, py2) - max(y, py) < R146_PRAH_PX:
            continue
        if zna_rodic_id:
            if _je_potomek(wid, pid, prvky):
                continue
            if _je_potomek(pid, wid, prvky):
                continue
        elif tuple(prvky.get(wid, {}).get("rodic") or ()) == (px, py, pw, ph):
            continue
        if _rect_contains((x, y, x2, y2), (px, py, px2, py2)):
            continue
        issues.append(
            Issue(
                "ERROR",
                f"{wl}: {ZNACKA_R146}: text '{text}' lezi na smaltove plose '{pid}' "
                f"({px},{py} {pw}x{ph}), ale neni jeji soucasti - inkoust a smalt "
                f"maji obracenou polaritu",
            )
        )
    return issues


def _cary_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[list[tuple[int, int, int, int]], list[Issue]]:
    """Precte ``navrh.cary`` -> (obdelniky delicich car, nalezy o bloku).

    Delici cara je v kitu vlasova linka (1 px), a prave proto ji scena
    NENESE: most zahazuje vsechno tenci nez 2 px (``r.height < 2``), jinak
    by kazda sit v kresbe vyrobila stovky widgetu. Cary se tedy vozi
    zvlast - jako obdelniky, ne jako prvky, protoze se na ne nic jineho
    neptá.
    """
    issues: list[Issue] = []
    cary: list[tuple[int, int, int, int]] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return cary, issues
    raw = blok.get("cary")
    if raw is None:
        return cary, issues
    if not isinstance(raw, list):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'cary' ma byt seznam obdelniku, "
                f"je {type(raw).__name__}",
            )
        )
        return cary, issues
    for i, rect_raw in enumerate(raw):
        rect = _obdelnik4(rect_raw)
        if rect is None or rect[2] <= 0 or rect[3] <= 0:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'cary[{i}]' ma byt ctyri cela cisla "
                    f"[x, y, sirka, vyska] s kladnymi rozmery, je {rect_raw!r}",
                )
            )
            continue
        cary.append(rect)
    return cary, issues


def _r147_nalezy(
    wl: str,
    rect: tuple[int, int, int, int],
    text: str,
    cary: list[tuple[int, int, int, int]],
) -> list[Issue]:
    """Rule 147: delici cara vede pres text.

    Blok textu nema pevnou vysku: kdyz naroste o radek, tise prejede pres
    oddelovac - a zadna kontrola preteceni to nevidi, protoze prvek nikam
    neceni.

    MERI SE INKOUST, NE BOX, a je to rozdil se zmerenym dopadem. Meridlo
    kitu (`zmer_prekryv.py`) porovnavalo caru s DOM boxem a s odstupem 4 px
    od jeho hran; na listu `Main` z toho vysel jeho JEDINY nalez:

        div.kostra box  537,140 686x229   "Zatim neni co ukazovat"
        cary site       y192, y244, y296, y348
        INKOUST tehoz textu ve scene: 537,248 686x12

    Text je ve svem boxu svisle na stredu, takze cary jdou pres PRAZDNOU
    cast boxu - nejblizsi (y244) konci 4 px nad prvnim pixelem pisma.
    Nalez byl artefakt merene veliciny, ne vada na skle. Scena nese
    u popisku rozsah inkoustu (`do_espos.inkoust`), takze tady se pravidlo
    pta presne na to, co slibuje: jde cara pres glyfy?

    Odstup `R147_ODSTUP_PX` je z teze uvahy: cara, ktera se inkoustu jen
    dotkne shora nebo zdola, je podtrzeni nebo nadpis nad carou, ne
    preskrtnuti.

    Gatovano profilem (`delici_cary`) - viz `DeviceProfile`.
    """
    issues: list[Issue] = []
    x, y, w, h = rect
    x2, y2 = x + w, y + h
    for cx, cy, cw, ch in cary:
        cx2, cy2 = cx + cw, cy + ch
        if min(x2, cx2) - max(x, cx) < 1:
            continue
        if cy - y < R147_ODSTUP_PX or y2 - cy2 < R147_ODSTUP_PX:
            continue
        issues.append(
            Issue(
                "ERROR",
                f"{wl}: {ZNACKA_R147}: cara {cx},{cy} {cw}x{ch} vede pres text "
                f"'{text}' (inkoust {x},{y} {w}x{h})",
            )
        )
    return issues


def _skala_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[dict[str, Any] | None, list[Issue]]:
    """Precte ``navrh.skala`` -> (zavazna skala rezu + vyjimky, nalezy).

    Tvar: ``{"rezy": [14, 16, 20, 24, 32], "vyjimky": {"40": "duvod"}}``.

    ``rezy`` je ZAVAZNA skala roli - pet roli, pet velikosti, nic jineho
    (`tokens.json: typography`). ``vyjimky`` jsou rezy, ktere smi stat
    PRAVE NA TOMHLE LISTU, a ke kazdemu MUSI byt veta proc: vyjimka bez
    duvodu je jen vypinac pravidla (tataz uvaha jako u ``presah``
    a ``prazdne`` u Rule 136 a 138).

    Vraci ``None``, kdyz blok chybi - pravidlo pak rekne NAHLAS, ze se
    nemerilo, misto aby mlcelo jako "v poradku".
    """
    issues: list[Issue] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return None, issues
    raw = blok.get("skala")
    if raw is None:
        return None, issues
    if not isinstance(raw, dict):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'skala' ma byt objekt "
                f"{{'rezy': [...], 'vyjimky': {{...}}}}, je {type(raw).__name__}",
            )
        )
        return None, issues
    rezy_raw = raw.get("rezy")
    if not isinstance(rezy_raw, list) or not rezy_raw:
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'skala.rezy' ma byt neprazdny seznam "
                f"rezu v px, je {rezy_raw!r}",
            )
        )
        return None, issues
    rezy: set[float] = set()
    for rez_raw in rezy_raw:
        hod = _nezaporne_cislo(rez_raw)
        if hod is None or hod <= 0:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'skala.rezy' ma byt seznam kladnych "
                    f"cisel v px, je v nem {rez_raw!r}",
                )
            )
            return None, issues
        rezy.add(float(hod))
    vyjimky: dict[float, str] = {}
    vyjimky_raw = raw.get("vyjimky")
    if vyjimky_raw is not None:
        if not isinstance(vyjimky_raw, dict):
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'skala.vyjimky' ma byt objekt "
                    f"{{rez: duvod}}, je {type(vyjimky_raw).__name__}",
                )
            )
        else:
            for rez_raw, duvod_raw in vyjimky_raw.items():
                # Klic JSONoveho objektu je vzdycky RETEZEC ("12"), takze
                # se tu cislo cte z retezce - jinde v tomhle modulu by to
                # byla dira (retezec misto cisla je vada dat), tady je to
                # jediny tvar, ktery JSON umi.
                hod = _rez_z_klice(rez_raw)
                if hod is None:
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'skala.vyjimky' ma klic "
                            f"{rez_raw!r}, ktery neni rez v px",
                        )
                    )
                    continue
                if not isinstance(duvod_raw, str) or not duvod_raw.strip():
                    # Vyjimka bez vety je vypinac pravidla. Zahazuje se
                    # a rekne se to nahlas - jinak by po ni zbylo ticho
                    # vypadajici jako "tenhle rez je v poradku".
                    issues.append(
                        Issue(
                            "WARN",
                            f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'skala.vyjimky[{rez_raw}]' je "
                            f"vyjimka bez duvodu - zahazuje se",
                        )
                    )
                    continue
                vyjimky[float(hod)] = duvod_raw.strip()
    return {"rezy": rezy, "vyjimky": vyjimky}, issues


def _rez_z_klice(v: object) -> float | None:
    """Rez v px z klice JSONoveho objektu ("12" i 12), jinak ``None``."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    if isinstance(v, str):
        try:
            hod = float(v.strip())
        except ValueError:
            return None
        return hod if hod > 0 else None
    return None


def _skala_popis(rezy: set[float]) -> str:
    return "/".join(f"{r:g}" for r in sorted(rezy))


def _r148_nalezy(
    pfx: str,
    widgets: list[Any],
    prvky: dict[str, dict[str, Any]],
    skala: dict[str, Any] | None,
) -> list[Issue]:
    """Rule 148: rez pisma mimo zavaznou skalu roli.

    Pet roli, pet velikosti (`tokens.json: typography`, tabulka 3.1
    specifikace). Kdo sazi sesty rez, sazi ho od oka - a od oka se pismo
    na 294 PPI sazet neda: rozdil 13 vs 14 px je 0,086 mm, tedy pod
    rozlisenim oka, ale nad rozlisenim MRIZKY (radkovy box 17 vs 18)
    a sloupec opakovanych radku se o nej rozjede.

    Kdo tu MLCI a proc:

    * **Prvek bez ``font_size``** -> mlci. Bez mereni neni co soudit;
      most vozi rez jen prvku, ktery nese VLASTNI text.
    * **Prvek bez textu** -> mlci. Rez prazdne schranky nikdo nevidi.
    * **Rez ve vyjimkach TOHOHLE listu** -> hlasi se jako ODCHYLKA
      s duvodem, ne jako vada. Ticho by se nedalo odlisit od zmereneho
      "v poradku" a prvni clovek, ktery vyjimku nenajde, ji zrusi.

    Vyjimky jsou JMENOVITE a per-list schvalne: rez 13 px je na
    klavesnici vedomy (vlastni soustava, roztec 18 pri boxu 18 nema kam
    rust), na listu Nastaveni by to byl preklep. Do 9. 9. 2026 zil
    tenhle seznam jen v `navrh-identita/gen_identita.py` a meril tedy
    25 listu z 62; ted je v `tokens.json` a meri se jim VSECH 62.

    HLASI SE PO REZECH, ne po prvcich, a je to rozhodnuti o hlasce: rez
    se opakuje. Klavesnice ma 26 prvku ve trech vyjimecnych rezech - tri
    vety jsou nalez, 26 je smetiste, ve kterem ten nalez zanikne. Tataz
    uvaha jako u Rule 150.
    """
    if skala is None:
        return []
    nalezy: dict[float, list[tuple[str, str]]] = {}
    for i, w in enumerate(widgets):
        if not isinstance(w, dict) or w.get("visible") is False:
            continue
        text = str(w.get("text", "")) if isinstance(w.get("text"), str) else ""
        if not text.strip():
            continue
        wid = w.get("_widget_id") or w.get("id")
        prvek = prvky.get(wid, {}) if isinstance(wid, str) else {}
        rez = prvek.get("font_size")
        if rez is None:
            continue
        rez = float(rez)
        if rez in skala["rezy"]:
            continue
        nalezy.setdefault(rez, []).append(
            (str(wid or f"widget[{i}]"), text)
        )
    issues: list[Issue] = []
    for rez in sorted(nalezy):
        kdo = nalezy[rez]
        duvod = skala["vyjimky"].get(rez)
        if duvod is not None:
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R148_ODCHYLKA}: rez {rez:g} px na {len(kdo)} "
                    f"prvcich neni ve skale {_skala_popis(skala['rezy'])}, "
                    f"duvod: {duvod}",
                )
            )
        else:
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R148}: rez {rez:g} px na {len(kdo)} prvcich "
                    f"(napr. {kdo[0][0]}, text '{kdo[0][1]}'), zavazna skala je "
                    f"{_skala_popis(skala['rezy'])} px",
                )
            )
    return issues


def _r149_nalezy(
    wl: str,
    prvek: dict[str, Any],
    text: str,
    prof: DeviceProfile,
) -> list[Issue]:
    """Rule 149: uhlova velikost znaku pod mezi ctenosti.

    Pixel o citelnosti nerika nic: tyz rez 14 px ma na 120 PPI verzalku
    2,07 mm a na 294 PPI 0,85 mm. Meritkem je UHLOVA velikost na
    vzdalenosti, ze ktere se pristroj opravdu cte - a ta je vlastnost
    TROJICE (rez, PPI panelu, vzdalenost oka), takze obe cisla nese
    profil a bez nich pravidlo MLCI.

    Meri se VYSKA ZNAKU (verzalka = ``verzalka_pomer * rez``), ne radkovy
    box a uz vubec ne dotykovy cil. Je to tataz delba, jakou dela
    `citelnost.py`: ISO 9241-303 mluvi o vysce znaku, natahnout tutez
    latku na mezeru v care nebo na dotykovy cil znamena merit jinou
    velicinu tymz meritkem (dotykovy cil 81 px by pak "splnoval ISO",
    coz nic neznamena - jeho mez je hmat, ne oko).

    O tom, PROC se nesoudi podle ISO, mluvi komentar u `R149_MEZ_ISO`.
    """
    if not prof.cteci_vzdalenost_mm or not prof.verzalka_pomer or not prof.ppi:
        return []
    rez = prvek.get("font_size")
    if rez is None or not text.strip():
        return []
    verzalka = prof.verzalka_pomer * float(rez)
    minut = prof.minuty(verzalka)
    if minut >= R149_MEZ_LETMO:
        return []
    uroven = "ERROR" if minut < R149_MEZ_TVAR else "WARN"
    co = (
        "tvar glyfu se nerozezna"
        if minut < R149_MEZ_TVAR
        else "letmym pohledem se to neprecte"
    )
    return [
        Issue(
            uroven,
            f"{wl}: {ZNACKA_R149}: rez {float(rez):g} px = verzalka "
            f"{prof.mm(verzalka):.3f} mm = {minut:.2f}' na "
            f"{prof.cteci_vzdalenost_mm:.0f} mm ({co}; mez {R149_MEZ_LETMO:.0f}' "
            f"letmo, {R149_MEZ_TVAR:.0f}' tvar, ISO 9241-303 zada "
            f"{R149_MEZ_ISO:.0f}' a tenhle znak je na "
            f"{100.0 * minut / R149_MEZ_ISO:.0f} % te meze), text '{text}'",
        )
    ]


def _barva_klic(s: str) -> str:
    """Barva jako porovnatelny klic: '#E9A63C', 'e9a63c' i 'red' -> jedno."""
    rgb = _parse_color(s)
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}" if rgb else s.strip().lower()


def _paleta_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[tuple[frozenset[str], str | None] | None, list[Issue]]:
    """Precte ``navrh.paleta`` a ``navrh.paleta_vlastni`` -> (paleta, duvod).

    ``paleta`` je seznam hexu, proti kterym se list meri (kit vozi
    `tokens.json: colors`, tedy tutez paletu, kterou ma firmware v
    `tema.h`). ``paleta_vlastni`` je veta o tom, ze TENHLE list ma
    vlastni identitu - list v negativu nebo zamerne stara obrazovka.

    Vraci ``None``, kdyz paleta nedosla: pravidlo pak rekne, ze se
    nemerilo, misto aby mlcelo.
    """
    issues: list[Issue] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return None, issues
    raw = blok.get("paleta")
    vlastni_raw = blok.get("paleta_vlastni")
    vlastni: str | None = None
    if vlastni_raw is not None:
        if not isinstance(vlastni_raw, str) or not vlastni_raw.strip():
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'paleta_vlastni' je oznaceni bez vety "
                    f"- vypinac pravidla bez duvodu se zahazuje",
                )
            )
        else:
            vlastni = vlastni_raw.strip()
    if raw is None:
        if vlastni is not None:
            # Pulka smlouvy: list rekl, ze ma vlastni paletu, ale paleta
            # nedosla. Ticho by tu bylo horsi nez nalez - vypadalo by
            # jako "zmereno a v poradku", pritom se nemerilo nic.
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'paleta_vlastni' je, ale "
                    f"'paleta' ne - vyjimka bez meze nic nevyjima",
                )
            )
        return None, issues
    if not isinstance(raw, list) or not raw:
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'paleta' ma byt neprazdny seznam hexu, "
                f"je {raw!r}",
            )
        )
        return None, issues
    barvy: set[str] = set()
    for barva_raw in raw:
        if not isinstance(barva_raw, str) or _parse_color(barva_raw) is None:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'paleta' ma byt seznam barev, "
                    f"je v nem {barva_raw!r}",
                )
            )
            return None, issues
        barvy.add(_barva_klic(barva_raw))
    return (frozenset(barvy), vlastni), issues


def _r150_nalezy(
    pfx: str,
    widgets: list[Any],
    paleta: tuple[frozenset[str], str | None] | None,
) -> list[Issue]:
    """Rule 150: barva prvku mimo paletu.

    SCENOVE pravidlo, ne widgetove, a je to rozhodnuti o hlasce: barva se
    opakuje. Zamerne stara obrazovka `DnesSystemMonitor` ma 54 prvku v peti
    barvach starsi generace palety; pet vet je nalez, 54 je smetiste, ve
    kterem ten nalez zanikne. Hlasi se proto KAZDA RUZNA barva jednou,
    s poctem prvku a s jednim jmenem pro priklad.

    Kdo tu MLCI a proc:

    * **Bez ``navrh.paleta``** -> tahle funkce mlci. Je to tataz DATOVA
      zavora jako u Rule 136, 137 a 144-147: bez mereni neni co soudit
      a cizi navrh, ktery paletu nedeklaruje, se z ni obvinovat nema.
      Ticho ale NENI konec: `validate_data` vedle toho hlasi
      `ZNACKA_R150_NEMERENO` vsude, kde prvky NESOU zmerenou barvu
      (`navrh.prvky[*].inkoust`) a paleta presto nedosla - tedy na
      kazdem listu kitu a na zadne cizi scene. Do 9. 9. 2026 tahle
      zavora chybela a rozbity `tokens.json` umlcel celou tridu bez
      jedineho slova. Ze most paletu opravdu vozi, meri
      `tests/test_paleta_jeden_zdroj.py`.
    * **List s vlastni identitou** (``paleta_vlastni``) -> jeden WARN
      s duvodem misto vyctu barev. List v negativu ma vlastni, take
      zmerenou paletu (`gen_negativ.BARVY`) a obvinovat ho z toho, ze
      neni smaltovy, znamena merit jinou vec, nez pravidlo slibuje.
    * **Neviditelny prvek** -> mlci, stejne jako u Rule 135 a 136.
    * **Barva pisma prvku BEZ pisma** -> mlci: dedi se z rodice a nikdo
      ji nevidi.

    Tohle je NAVRHOVA polovina brany `tabos-core/tools/barvy_natvrdo.py`:
    ta meri hexy ve ZDROJACICH C++ proti `tema.h`, tahle meri barvy na
    SKLE proti `tokens.json`. Dva hlidaci, kazdy na jiny clanek retezu -
    jinak by to byly dve palety a kazda strana by merila svou:

      * `tests/test_typografie_a_paleta.py` - ze se SHODUJI tri kopie
        palety (`tokens.json` x `tema.h` x `ram.BARVY` kitu);
      * `tests/test_paleta_jeden_zdroj.py` - ze ji most (`do_espos.paleta`)
        z `tokens.json` opravdu VOZI do sceny, takze to ticho vyse neni
        ticho nad prazdnou paletou.
    """
    if paleta is None:
        return []
    barvy, vlastni = paleta
    if vlastni is not None:
        return [
            Issue(
                "WARN",
                f"{pfx}: {ZNACKA_R150_ODCHYLKA}: {vlastni} - barvy prvku se proti "
                f"palete NEMERI",
            )
        ]
    nalezy: dict[tuple[str, str], list[str]] = {}
    for i, w in enumerate(widgets):
        if not isinstance(w, dict) or w.get("visible") is False:
            continue
        for klic, co in (("color_fg", "popredi"), ("color_bg", "pozadi")):
            s = w.get(klic)
            if not isinstance(s, str) or not s.strip():
                continue
            if klic == "color_fg" and not str(w.get("text", "")).strip():
                continue
            barva = _barva_klic(s)
            if barva in barvy:
                continue
            kdo = w.get("_widget_id") or w.get("id") or f"widget[{i}]"
            nalezy.setdefault((barva, co), []).append(str(kdo))
    issues: list[Issue] = []
    for (barva, co), kdo in sorted(nalezy.items()):
        issues.append(
            Issue(
                "WARN",
                f"{pfx}: {ZNACKA_R150}: {co} '{barva}' na {len(kdo)} prvcich "
                f"(napr. {kdo[0]}), paleta ma {len(barvy)} barev",
            )
        )
    return issues


def _soustava_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[dict[str, float] | None, list[Issue]]:
    """Precte ``navrh.soustava`` -> ({'pole_x', 'vsazka'}, nalezy).

    Dve cisla soustavy odsazeni: kde zacina POLE a o kolik od jeho hrany
    ma text odskocit. Kit je vozi z `tokens.json: layout`
    (``obsah.x`` a ``ram.vsazka``), tedy z tehoz mista, ze ktereho je bere
    generator i firmware.
    """
    issues: list[Issue] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return None, issues
    raw = blok.get("soustava")
    if raw is None:
        return None, issues
    if not isinstance(raw, dict):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'soustava' ma byt objekt "
                f"{{'pole_x': .., 'vsazka': ..}}, je {type(raw).__name__}",
            )
        )
        return None, issues
    ven: dict[str, float] = {}
    for klic in ("pole_x", "vsazka"):
        hod = _nezaporne_cislo(raw.get(klic))
        if hod is None:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'soustava.{klic}' ma byt nezaporne "
                    f"cislo v px, je {raw.get(klic)!r}",
                )
            )
            return None, issues
        ven[klic] = float(hod)
    if ven["vsazka"] <= 0:
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'soustava.vsazka' ma byt kladna, "
                f"je {ven['vsazka']:g} - s nulovou vsazkou nema Rule 151 co merit",
            )
        )
        return None, issues
    return ven, issues


def _r151_nalezy(
    wl: str,
    prvek: dict[str, Any],
    x: int,
    text: str,
    soustava: dict[str, float] | None,
) -> list[Issue]:
    """Rule 151: text se lepi na ram misto aby dosedl na vsazku.

    Soustava zni: leva hrana pole je ``pole_x``, text v nem zacina o
    ``vsazka`` dal. Text, ktery zacina MEZI tim, se lepi na ram - a je to
    skoro vzdycky preklep v souradnici, ne zamer: nikdo neodsazuje o
    patnact pixelu, kdyz soustava zna sestnact.

    Proc to nechyti Rule 134: ta meri near-miss dvou TEXTOVYCH hran do
    3 px od sebe. Zamerne stara obrazovka `DnesSystemMonitor` ma text na
    x=35 a nejblizsi jina hrana je x=20, tedy 15 px daleko - Rule 134
    o nem mlci a mlcet ma, protoze to neni preklep proti jinemu textu,
    ale proti SOUSTAVE.

    BLOK S VLASTNI VSAZKOU se nevypina, PARAMETRIZUJE. Klavesnicovy blok
    ma vlastni okraj 8 px (`klavesnice_blok.OKRAJ`), takze jeho klavesy
    stoji na x=28. Kdyby pravidlo umelo jen mez ze soustavy, hlasilo by
    24 falesnych nalezu; kdyby se blok dal jen VYPNOUT, prestalo by se
    v nem merit uplne. Prvek proto smi nest vlastni ``vsazka`` a meri se
    proti ni - klavesa na x=24 nalez porad dostane.

    Meri se jen text zacinajici v pasmu ``(pole_x, pole_x + vsazka)``.
    Vlevo od pole uz jsou hrany, ktere meri Rule 63 a Rule 80; vpravo od
    vsazky uz je soustava splnena.
    """
    if soustava is None or not text.strip():
        return []
    pole_x = soustava["pole_x"]
    vlastni_raw = prvek.get("vsazka")
    vsazka = soustava["vsazka"] if vlastni_raw is None else float(vlastni_raw)
    if vsazka <= 0:
        return []
    cil = pole_x + vsazka
    if not (pole_x < x < cil):
        return []
    vlastni = "" if vlastni_raw is None else " (blok ma vlastni vsazku)"
    return [
        Issue(
            "WARN",
            f"{wl}: {ZNACKA_R151}: text zacina na x={x}, hrana pole je "
            f"{pole_x:g} a soustava zada x={cil:g} (vsazka {vsazka:g} px)"
            f"{vlastni}, text '{text}'",
        )
    ]


def _mrizky_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[list[dict[str, Any]], list[Issue]]:
    """Precte ``navrh.mrizky`` -> (mrizky, nalezy o vadnem bloku).

    Cte tyz scenovy blok jako `_navrh_ze_sceny`, ale JEN klic ``mrizky``.
    Zamerne zvlast: mrizka je vlastnost SCENY (kolik dlazdic se na list
    vejde), ne vlastnost widgetu, takze ji pravidla nad prvky nemaji jak
    predat, a spolecna signatura by je svazala dohromady bez duvodu.
    Chybejici nebo neobjektovy blok se tu **mlci** preskoci - ohlasilo ho
    uz `_navrh_ze_sceny` a tyz preklep nesmi hlasit dve mista (zakon
    "dva nalezy, jedna obet").

    Kazda vadna hodnota = nalez a zahozeni te JEDNE mrizky; zbytek se cte
    dal. Mrizka se zahozenym poctem polozek uz z bloku nevystoupi vubec,
    takze nedostane jeste druhy nalez "kontrola NEPROBEHLA": o tom, ze se
    nezmerilo, mluvi prave ten ERROR.
    """
    issues: list[Issue] = []
    mrizky: list[dict[str, Any]] = []

    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return mrizky, issues
    raw = blok.get("mrizky")
    if raw is None:
        return mrizky, issues
    if not isinstance(raw, list):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'mrizky' ma byt seznam, "
                f"je {type(raw).__name__}",
            )
        )
        return mrizky, issues

    for i, polozka in enumerate(raw):
        if not isinstance(polozka, dict):
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'mrizky[{i}]' ma byt objekt, "
                    f"je {type(polozka).__name__}",
                )
            )
            continue
        jmeno_raw = polozka.get("jmeno")
        if not isinstance(jmeno_raw, str) or not jmeno_raw.strip():
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'mrizky[{i}].jmeno' ma byt jmeno "
                    f"mrizky, je {jmeno_raw!r}",
                )
            )
            continue
        jmeno = jmeno_raw.strip()
        kapacita_raw = polozka.get("kapacita")
        if not _is_int(kapacita_raw) or int(kapacita_raw) < 1:
            # Kapacita 0 nebo zaporna neni mrizka: pravidlo by pak obvinilo
            # kazdou polozku a vypadalo by to jako vada navrhu, ne dat.
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'mrizky[{jmeno}].kapacita' ma byt cele "
                    f"cislo >= 1, je {kapacita_raw!r}",
                )
            )
            continue
        polozek_raw = polozka.get("polozek")
        polozek: int | None = None
        if polozek_raw is not None:
            if not _is_int(polozek_raw) or int(polozek_raw) < 0:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'mrizky[{jmeno}].polozek' ma byt cele "
                        f"cislo >= 0, je {polozek_raw!r}",
                    )
                )
                continue
            polozek = int(polozek_raw)
        mrizky.append({"jmeno": jmeno, "kapacita": int(kapacita_raw), "polozek": polozek})

    return mrizky, issues


def _r140_nalezy(pfx: str, mrizky: list[dict[str, Any]]) -> list[Issue]:
    """Rule 140: mrizka s deklarovanou kapacitou nepojme vsechny polozky.

    Zivy protejsek: Domu ma dvanact slotu (`data-kapacita`), registr appek
    `tabos-core` jich dnes zna jedenact - a az jich bude trinact, ztrati se
    dvanacta a trinacta MIMO list, kde je zadne meridlo nad souradnicemi
    widgetu neuvidi: ve scene proste nebudou. Kapacita je proto jedina vec,
    kterou lze zmerit driv, nez se to stane.

    * ``polozek > kapacita`` -> ERROR (vic polozek, nez je kam dat).
    * ``polozek == kapacita`` i ``polozek < kapacita`` -> TICHO. Prazdny
      slot je v tomhle jazyce nosic, ne vada ("Dvanacty slot je prazdny
      a prazdny zustava", `gen_dalsi.py`); prazdna mrizka (``polozek == 0``)
      je jiny nalez a patri kostre, ne sem.
    * kapacita bez poctu polozek -> WARN, ze kontrola NEPROBEHLA. Vzor je
      Rule 133: meridlo, ktere se nepustilo, se hlasi nahlas, jinak vyjde
      ticho k nerozeznani od "v poradku".

    Pocet polozek artboard NEZNA a znat nemuze: kresli sloty, ne appky.
    Musi ho dodat most (z registru appek `tabos-core`, dnes jedenact) - do
    te doby je tenhle WARN jediny poctivy vysledek a jeho ubytek je merou
    toho, jak daleko je most hotovy.
    """
    issues: list[Issue] = []
    for m in mrizky:
        jmeno = m["jmeno"]
        kapacita = m["kapacita"]
        polozek = m["polozek"]
        if polozek is None:
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R140_NEMERENO}: mrizka '{jmeno}' ma kapacitu "
                    f"{kapacita}, ale pocet polozek nikdo nedodal - kontrola NEPROBEHLA",
                )
            )
            continue
        if polozek > kapacita:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_R140}: '{jmeno}' ma kapacitu {kapacita}, polozek "
                    f"je {polozek} (o {polozek - kapacita} vic)",
                )
            )
    return issues


# R152: od kolika stejnych prvku je to mrizka. Pet a min je rada nebo
# dvojice sloupcu (razitko ma ctyri sloty, zalozky tri); sest je nejmensi
# pocet, ktery se uz musi lamat do druheho radku nebo sloupce, a prave
# tam se pri zmene poctu polozek ztraci ta posledni. Zive protejsky:
# Domov 4x3 = 12 slotu (artboard), firmware kreslil 2x5 = 10 na 11 appek.
R152_MIN_PRVKU = 6


def _r152_nalezy(
    pfx: str,
    widgets: list[Any],
    mrizky: list[dict[str, Any]],
    blok_navrh: bool,
) -> list[Issue]:
    """Rule 152: nakreslena mrizka bez deklarovane kapacity (WARN, NEMERENO).

    Rule 140 meri kapacitu proti poctu polozek, ale JEN tam, kde generator
    napsal `data-kapacita`. Na 62 listech kitu to byly DVA (kritik
    espos-brany, bod 8): jedenact dlazdic bez deklarace = uplne ticho, a to
    ticho vypadalo v souhrnu brany stejne jako "zmereno, sedi". Tohle
    pravidlo tu diru zavira z druhe strany: kdyz scena OBSAHUJE neco, co
    vypada jako mrizka, a `navrh.mrizky` o tom neni zaznam, rekne se
    NAHLAS, ze se kapacita NEMERILA. Most kitu je fail-closed (kazda znacka
    `*_NEMERENO` = nenulovy navratovy kod), takze list s nedeklarovanou
    mrizkou uz zelene neprojde.

    CO JE MRIZKA - a je to zmerena mez, ne vkus:

    * prvky TEZE TRIDY (skupina podle `_widget_id` pred prvni teckou, tedy
      jmeno tridy z generatoru: `dlazdice.0` ... `dlazdice.11`),
    * TEZE VELIKOSTI (stejna sirka i vyska; razitko ma sloty ruznych sirek
      a mrizka to neni - to je kontrolni skupina pravidla),
    * je jich nejmene `R152_MIN_PRVKU`,
    * a stoji v NEJMENE DVOU sloupcich a NEJMENE DVOU radcich (aspon dve
      ruzne leve a dve ruzne horni hrany). Jeden sloupec je SEZNAM, ne
      mrizka: seznam souboru nebo sestnact kanalu analyzatoru ma pocet
      radku dany daty a roluje, kapacita tam neni vlastnost kresby.
      Tohle je POJMENOVANA MEZ pravidla: seznam o sestnacti radcich,
      ktery neroluje, projde. Kdo ho chce hlidat, deklaruje `data-kapacita`
      rukou (gen_appky to u LA uz dela) - Rule 140 ho pak meri.

    Deklarace se hleda podle JMENA: zaznam v `navrh.mrizky` se jmenem
    skupiny. Zaznam bez poctu polozek staci - o tom, ze se nemerilo,
    mluvi uz Rule 140 (`ZNACKA_R140_NEMERENO`) a tataz obet nesmi dostat
    dva nalezy.

    Gatovano DATY: bez bloku `navrh` pravidlo mlci (dokument editoru
    merena data legitimne nema, viz `NAVRH_KLIC`). Neviditelne prvky se
    preskakuji jako v Rule 135 a 136.
    """
    if not blok_navrh:
        return []
    deklarovane = {m["jmeno"] for m in mrizky}
    skupiny: dict[tuple[str, int, int], list[tuple[int, int]]] = {}
    for w in widgets:
        if not isinstance(w, dict) or w.get("visible") is False:
            continue
        skupina = _widget_group(w)
        if not skupina:
            continue
        x, y, ww, hh = (w.get(k) for k in ("x", "y", "width", "height"))
        if not all(_is_int(v) for v in (x, y, ww, hh)) or ww <= 0 or hh <= 0:
            continue
        skupiny.setdefault((skupina, int(ww), int(hh)), []).append((int(x), int(y)))
    issues: list[Issue] = []
    for (skupina, ww, hh), rohy in sorted(skupiny.items()):
        if len(rohy) < R152_MIN_PRVKU:
            continue
        sloupcu = len({x for x, _ in rohy})
        radku = len({y for _, y in rohy})
        if sloupcu < 2 or radku < 2:
            continue
        if skupina in deklarovane:
            continue
        issues.append(
            Issue(
                "WARN",
                f"{pfx}: {ZNACKA_R152_NEMERENO}: skupina '{skupina}' ma {len(rohy)} "
                f"stejnych prvku {ww}x{hh} ve {sloupcu} sloupcich a {radku} radcich, "
                f"ale navrh.mrizky o ni nema zaznam - kapacita se NEMERILA "
                f"(generator ma napsat data-kapacita a data-polozky)",
            )
        )
    return issues


# R141: LV_DPI_DEF z lv_conf.h (`#define LV_DPI_DEF 130     /*[px/inch]*/`)
# a CONFIG_LV_DPI_DEF ze sdkconfigu (`CONFIG_LV_DPI_DEF=130`). Zakomentovany
# radek ani `# CONFIG_LV_DPI_DEF is not set` se chytit nesmi - to je prave
# ten pripad "hodnota tu neni", ktery se hlasi jako nezmereno.
_R141_LV_DPI = re.compile(r"^[ \t]*#[ \t]*define[ \t]+LV_DPI_DEF[ \t]+\(?[ \t]*(\d+)", re.M)
_R141_SDK_DPI = re.compile(r"^[ \t]*CONFIG_LV_DPI_DEF[ \t]*=[ \t]*\"?(\d+)\"?[ \t]*$", re.M)


def _r141_dokumentovana(
    blok: Any,
    profil: str,
) -> tuple[int, str | None, Issue | None]:
    """Precte dokumentovanou hodnotu -> (cil, duvod, nalez o vadnem bloku).

    Blok je ``tokens.json -> firmware.lv_dpi_def`` = ``{"hodnota": 130,
    "duvod": "..."}``. Preklep v nem je ERROR, ne ticho a ne tichy navrat
    k profilu: oboji by za majitele rozhodlo, ze odchylka neplati - a prave
    takove tiche rozhodnuti tahle brana jinde odstranuje.
    """
    if not isinstance(blok, dict):
        return 0, None, Issue(
            "ERROR",
            f"{ZNACKA_R141_NEMERENO}: dokumentovana hodnota LV_DPI_DEF ma byt objekt "
            f"s klici 'hodnota' a 'duvod', je {type(blok).__name__}",
        )
    hodnota = blok.get("hodnota")
    if not _is_int(hodnota) or int(hodnota) <= 0:
        return 0, None, Issue(
            "ERROR",
            f"{ZNACKA_R141_NEMERENO}: dokumentovana hodnota LV_DPI_DEF ma byt kladne "
            f"cele cislo, je {hodnota!r}",
        )
    duvod = blok.get("duvod")
    if not isinstance(duvod, str) or not duvod.strip():
        # Odchylka bez duvodu neni rozhodnuti, je to vypinac brany. Tataz
        # uvaha jako u `prazdne` v Rule 138.
        return 0, None, Issue(
            "ERROR",
            f"{ZNACKA_R141_NEMERENO}: dokumentovana hodnota LV_DPI_DEF {int(hodnota)} "
            f"nema 'duvod' - odchylka bez duvodu neni rozhodnuti, je to vypinac brany "
            f"(profil '{profil}')",
        )
    return int(hodnota), duvod.strip(), None


def _r141_zdroj(
    jmeno: str,
    klic: str,
    vzor: re.Pattern[str],
    text: str,
    profil: str,
    cil: int,
    duvod: str | None = None,
    ppi: int = 0,
) -> list[Issue]:
    """Jeden zdroj DPI (soubor firmwaru) proti jedne cilove hodnote."""
    hodnoty = [int(m.group(1)) for m in vzor.finditer(text)]
    if not hodnoty:
        return [
            Issue(
                "WARN",
                f"{ZNACKA_R141_NEMERENO}: v {jmeno} neni radek {klic} - "
                f"kontrola NEPROBEHLA",
            )
        ]
    ruzne = sorted(set(hodnoty))
    if len(ruzne) > 1:
        return [
            Issue(
                "ERROR",
                f"{ZNACKA_R141_NEMERENO}: v {jmeno} je {klic} nekolikrat a ruzne "
                f"({', '.join(str(h) for h in ruzne)}) - nevim, ktera hodnota plati",
            )
        ]
    if ruzne[0] != cil:
        if duvod is None:
            return [
                Issue(
                    "ERROR",
                    f"{ZNACKA_R141} s panelem: {jmeno} {klic}={ruzne[0]}, profil "
                    f"'{profil}' ma {cil} px/palec",
                )
            ]
        return [
            Issue(
                "ERROR",
                f"{ZNACKA_R141} s dokumentaci: {jmeno} {klic}={ruzne[0]}, ale "
                f"tokens.json dokumentuje {cil} - firmware a dokumentace se rozesly",
            )
        ]
    if duvod is not None:
        # Shoda s DOKUMENTOVANOU hodnotou. Neni to ticho: odchylka od panelu
        # tam porad je, jen o ni nekdo rozhodl a napsal proc. WARN je presne
        # ta uroven - brana kit neshodi, ale odchylka zustane videt.
        return [
            Issue(
                "WARN",
                f"{ZNACKA_R141_ODCHYLKA}: {jmeno} {klic}={ruzne[0]}, vedoma odchylka "
                f"od profilu {ppi}, duvod: {duvod}",
            )
        ]
    return []


def zkontroluj_dpi(
    lv_conf_text: str,
    sdkconfig_text: str,
    prof: DeviceProfile,
    dokumentovano: Any = None,
) -> list[Issue]:
    """Rule 141: DPI firmwaru proti PPI panelu. CISTE TEXTOVA funkce.

    LVGL prepocitava vsechno, co je zadane v milimetrech nebo v "dip"
    (odsazeni, tloustky, dotykove meze), pres ``LV_DPI_DEF``. Kdyz tam stoji
    130 a panel ma 294 px/palec, firmware pocita s pixely, ktere jsou 2,26x
    vetsi, nez ve skutecnosti jsou - a navrh, ktery branou projde, se na
    desce presto rozpadne. Zadny pohled na scenu tohle neuvidi: cislo je
    v konfiguraci firmwaru, ne v navrhu.

    **Proc textova funkce a ne pravidlo uvnitr `validate_data`.** Validator
    smi cist JEN dokument, ktery dostal. `tests/test_tab5_validace.py`
    porovnava beh v pameti s behem CLI v podprocesu; cteni souboru z disku
    uvnitr pravidla by obe cesty rozeslo a mereni by zaviselo na tom, odkud
    se pusti. Soubory proto cte MOST (`do_espos.dpi_firmwaru`) a sem posila
    jejich TEXT. ESPOS drzi mez a jazyk hlasky, aby si most cislo 294
    neopsal - opsana mez je druha pravda.

    Nulova tolerance je zamer: ``#define`` neni mereni, nema sum. Bud tam
    je cislo panelu, nebo tam je jine cislo. Panel ma 293,7 px/palec, cili
    se porovnava se zaokrouhlenym 294 - a hlaska to cele cislo rekne, aby
    se nehledalo, proti cemu se merilo.

    Chybejici radek je WARN "nezmereno" (LVGL by vzalo svou vlastni vychozi
    hodnotu a co plati, z textu poznat nejde); dva ruzne radky jsou ERROR
    ze stejneho duvodu, jen naopak: hodnoty jsou dve a kontrola nema kterou
    vzit. Ticho by v obou pripadech vypadalo jako "souhlasi".
    """
    cil = round(prof.ppi)
    if cil <= 0:
        # Profil bez panelu (OLED nema ppi): neni proti cemu merit. Rict to
        # nahlas je jediny poctivy vysledek - nula by lhala, ze se merilo.
        return [
            Issue(
                "WARN",
                f"{ZNACKA_R141_NEMERENO}: profil '{prof.name}' nema ppi - "
                f"neni proti cemu merit",
            )
        ]
    issues: list[Issue] = []
    duvod: str | None = None
    if dokumentovano is not None:
        cil_doc, duvod, vadny = _r141_dokumentovana(dokumentovano, prof.name)
        if vadny is not None:
            # Preklep v dokumentaci NESMI byt ticho ani navrat k profilu:
            # oboji by tise rozhodlo za majitele. Bez pouzitelne dokumentace
            # se nemeri vubec a rekne se to.
            return [vadny]
        cil = cil_doc
    for jmeno, klic, vzor, text in (
        ("lv_conf.h", "LV_DPI_DEF", _R141_LV_DPI, lv_conf_text),
        ("sdkconfig", "CONFIG_LV_DPI_DEF", _R141_SDK_DPI, sdkconfig_text),
    ):
        issues.extend(
            _r141_zdroj(jmeno, klic, vzor, text, prof.name, cil, duvod, round(prof.ppi))
        )
    return issues


# Cmap vygenerovaneho LVGL fontu: `.range_start`/`.range_length` a bud
# `NULL` (souvisly rozsah), nebo `unicode_list_N` (rozptylene kodove body).
_FONT_SEZNAM = re.compile(
    r"static const uint16_t (unicode_list_\d+)\[\] = \{(.*?)\};", re.S
)
_FONT_CISLO = re.compile(r"0x[0-9a-fA-F]+|\d+")
_FONT_ROZSAH = re.compile(
    r"\.range_start\s*=\s*(\d+)\s*,\s*\.range_length\s*=\s*(\d+)\s*,"
    r".*?\.unicode_list\s*=\s*(NULL|unicode_list_\d+)",
    re.S,
)


def radkovy_box(rez: float, asc: float, desc: float) -> int:
    """Radkovy box rezu tak, jak ho opravdu vysadi prohlizec.

    ``round(asc*rez) + round(desc*rez)``, tedy KAZDA cast zaokrouhlena
    zvlast - NE ``round((asc+desc)*rez)``. Neni to detail: pri hhea
    968/251 dava spravny vzorec 14 -> 18, 16 -> 19, 20 -> 24, 24 -> 29
    a jednorazove zaokrouhleni by u rezu 16 vydalo 20 misto 19. Overeno
    merenim na vysazenem DOM.
    """
    return round(asc * rez) + round(desc * rez)


def skala_rozpory(
    prof: DeviceProfile,
    *,
    skala: dict[str, float],
    box: dict[int, int],
    roztec: dict[int, int],
    otisk_box: dict[int, int],
    otisk_minut: dict[int, float],
    typography: dict[str, Any],
    pozn_typografie: dict[str, Any],
    token_role: dict[str, int],
    asc: float,
    desc: float,
    roztec_pricti: int = 2,
    mez_minut: float = 0.005,
) -> list[str]:
    """Co se rozeslo mezi skalou pisma, jejim popisem a fyzikou.

    CISTA FUNKCE: dostane cisla, vrati vety. Na disk nesaha, takze ji
    muze pouzit jak brana v kitu (`citelnost.py`), tak pytest ESPOSu -
    a prave o to jde. Do 9. 9. 2026 zila tahle kontrola JEN v kitu jako
    skript s navratovym kodem; kdo ji nespustil rukou, nedozvedel se nic.

    Parametry, at je videt, co je co:

    * ``skala``   role -> rez v px, tak jak je SAZI generator (`ram.py`).
    * ``box``, ``roztec``  co generator vysazi jako radkovy box a roztec.
    * ``otisk_box``, ``otisk_minut``  ZAVAZNA tabulka 3.1 specifikace.
    * ``typography``  `tokens.json: typography` (role -> jmeno LVGL fontu).
    * ``pozn_typografie``  `tokens.json: _pozn_typografie` (druhy opis
      tychz cisel; do 2026-09-06 ho neporovnaval nikdo).
    * ``token_role``  ktery klic tokenu je ktera role v `ram.py`. Klice
      se zamerne neprejmenovavaly, takze jmeno roli neprozradi - spojnici
      drzi jen tahle tabulka.

    OBA SMERY. Kontroly tvaru "je-li rez v tabulce, sedi?" propusti
    POSUNUTOU SKALU: kdyz se rezy zmeni na 15/17/21/25/33 a vsechny opisy
    se srovnaji, zadny `rez in otisk` neplati, cyklus se o nic neopre
    a meridlo vytiskne SHODU. Skala se proto porovnava s tabulkou 3.1
    jako MNOZINA, v obou smerech.
    """
    nalezy: list[str] = []
    mereno: set[int] = set()
    for _role, rez_raw in skala.items():
        rez = int(rez_raw)
        mereno.add(rez)
        muj = radkovy_box(rez, asc, desc)
        if rez in box and box[rez] != muj:
            nalezy.append(
                f"box rezu {rez}: generator sazi {box[rez]}, "
                f"hhea {asc:g}/{desc:g} dava {muj}"
            )
        if rez in roztec and roztec[rez] != muj + roztec_pricti:
            nalezy.append(
                f"roztec rezu {rez}: generator ma {roztec[rez]}, "
                f"box+{roztec_pricti} je {muj + roztec_pricti}"
            )
        if rez in otisk_box and otisk_box[rez] != muj:
            nalezy.append(
                f"box rezu {rez}: specifikace 3.1 rika {otisk_box[rez]}, "
                f"spocitano {muj}"
            )
        if rez in otisk_minut:
            m = prof.minuty(prof.verzalka_pomer * rez)
            if abs(m - otisk_minut[rez]) > mez_minut:
                nalezy.append(
                    f"rez {rez} na {prof.cteci_vzdalenost_mm:.0f} mm: specifikace "
                    f"3.1 rika {otisk_minut[rez]:.2f}', spocitano {m:.2f}'"
                )
    chybi = sorted(set(box) - mereno)
    if chybi:
        nalezy.append(f"generator zna rezy {chybi}, ktere tahle skala nemeri")
    prebyva = sorted(mereno - set(otisk_minut))
    if prebyva:
        nalezy.append(
            f"skala sazi rezy {prebyva}, ktere zavazna tabulka 3.1 nezna"
        )
    schazi = sorted(set(otisk_minut) - mereno)
    if schazi:
        nalezy.append(
            f"zavazna tabulka 3.1 predepisuje rezy {schazi}, ktere skala nesazi"
        )
    for klic, rez in token_role.items():
        zaznam = pozn_typografie.get(klic)
        if not isinstance(zaznam, dict):
            nalezy.append(
                f"_pozn_typografie nema zaznam '{klic}' (role rezu {rez})"
            )
        else:
            if zaznam.get("rez_px") != rez:
                nalezy.append(
                    f"_pozn_typografie.{klic}.rez_px = {zaznam.get('rez_px')}, "
                    f"generator ma {rez}"
                )
            if zaznam.get("radkovy_box_px") != radkovy_box(rez, asc, desc):
                nalezy.append(
                    f"_pozn_typografie.{klic}.radkovy_box_px = "
                    f"{zaznam.get('radkovy_box_px')}, spocitano "
                    f"{radkovy_box(rez, asc, desc)}"
                )
            m = prof.minuty(prof.verzalka_pomer * rez)
            try:
                zapsano = float(zaznam.get("minut_450mm", -1))
            except (TypeError, ValueError):
                zapsano = -1.0
            if abs(zapsano - round(m, 2)) > mez_minut:
                nalezy.append(
                    f"_pozn_typografie.{klic}.minut_450mm = "
                    f"{zaznam.get('minut_450mm')}, spocitano {m:.2f}'"
                )
        if klic not in typography:
            nalezy.append(f"typography nema klic '{klic}' (role rezu {rez})")
            continue
        ceka = f"tabos_{rez}"
        if str(typography[klic]) != ceka:
            nalezy.append(
                f"typography.{klic} = '{typography[klic]}', role ma rez "
                f"{rez} px (ceka '{ceka}')"
            )
    navic = sorted(set(typography) - set(token_role))
    if navic:
        nalezy.append(
            f"typography ma navic klice {navic}, ktere zadne roli neodpovidaji"
        )
    return nalezy


def sirka_retezce(
    text: str,
    rez: float,
    prostrkani: float,
    upem: int,
    cmap: dict[int, str],
    hmtx: dict[str, Any],
) -> float:
    """Sirka retezce jako SOUCET ADVANCE SIREK glyfu daneho fontu.

    Druhy, NEZAVISLY odhad teze veliciny, kterou meri Rule 137 v
    prohlizeci (`Range.getClientRects()`). Neni to tyz vypocet - Chrome
    navic uplatnuje parovy kerning z GPOS - takze se neporovnava na
    rovnost, ale mezi (viz `sirka_meze`). Ze si obe cesty odpovidaji,
    meri `test_parita_sirek_R137_a_fontu`: na vete "Vypada to jako I2C.
    D1 = SCL, D0 = SDA." pri rezu 20 px vysel rozdil 0,04 px.

    `prostrkani` je CSS letter-spacing v em. CSS ho pricita i ZA posledni
    pismeno, takze se tak pocita i tady - schranka textu je o tu mezeru
    sirsi nez jeho inkoust.

    Znak, ktery font NEMA, je ValueError, ne nula: LVGL chybejici glyf
    TISE preskoci a z "-58 dBm" se stane "58 dBm" (viz Rule 26).
    """
    soucet = 0
    for ch in text:
        glyf = cmap.get(ord(ch))
        if glyf is None:
            raise ValueError(
                f"font nema glyf pro {ch!r} (U+{ord(ch):04X}) v retezci "
                f"{text!r} - vysadil by se prazdny"
            )
        soucet += hmtx[glyf][0]
    return soucet * rez / upem + prostrkani * rez * len(text)


def sirka_meze(soucet: float, kerning: float) -> tuple[float, float]:
    """Pripustne pasmo pro cislo OPSANE do generatoru: (dolni, horni).

    Mez je JEDNOSTRANNA, protoze kerning sirku jen ZMENSUJE:
    ``soucet - kerning <= opsane <= ceil(soucet)``. `kerning` je nejvetsi
    NAMERENY rozdil (v kitu 3,75 px u "/sd/capture_0412.la" v roli
    hodnota), zaokrouhleny nahoru. Mez tim padne az na retezec, ktery se
    OPRAVDU zmenil, ne na zaokrouhleni.
    """
    return soucet - kerning, float(math.ceil(soucet))


def znaky_fontu_zarizeni(cesta: Any) -> frozenset[str]:
    """Znaky, ktere umi font ZARIZENI (`lv_font_tabos_*.c`). CTE DISK.

    Tohle je JEDINY zdroj pravdy o znakove sade: nic jineho neni to, co
    ma pristroj ve flashi. Vsechny ostatni seznamy v projektu jsou opisy
    a merí se PROTI TOMUHLE - `_TAB5_FONT_CHARS` tady, `gen_subset.SADA`
    v kitu a recept `gen_fonty.py` v jadre. Opsany seznam zestarne prvni
    zmenou pisma a brana pak mlci prave o novem znaku; presne tak vznikla
    ctverice kopii, kterou tahle funkce rusi.

    **Proc funkce a ne pravidlo.** Tataz delba jako u `jmena_ze_sdk`
    a `zkontroluj_dpi`: `validate_data` smi zaviset jen na dokumentu,
    ktery dostal. Font cte volajici (test, brana) a vysledek si nese sam.

    Cte oba tvary, ktere `lv_font_conv` vydava, protoze font zarizeni
    obsahuje OBA naraz: souvisly rozsah ASCII (`unicode_list = NULL`)
    i rozptylene ceske znaky a symboly (`unicode_list_N` s offsety od
    `range_start`). Cist jen jeden tvar znamena tise ztratit pulku
    abecedy.

    Prazdna mnozina se NEVRACI: kdyz se v souboru zadna cmap nenajde,
    zmenil se format a je to CHYBA, ne "font nic neumi". Ticho vydavane
    za "cisto" je prave ta vada, kterou tahle kampan jinde odstranuje.
    """
    cesta = Path(cesta)
    text = cesta.read_text(encoding="utf-8", errors="replace")
    seznamy = {
        m.group(1): [int(x, 0) for x in _FONT_CISLO.findall(m.group(2))]
        for m in _FONT_SEZNAM.finditer(text)
    }
    umi: set[int] = set()
    for m in _FONT_ROZSAH.finditer(text):
        start, delka, seznam = int(m.group(1)), int(m.group(2)), m.group(3)
        if seznam == "NULL":
            umi |= set(range(start, start + delka))
        else:
            umi |= {start + k for k in seznamy.get(seznam, [])}
    if not umi:
        raise ValueError(f"v {cesta.name} neni zadna cmap - zmenil se format fontu?")
    return frozenset(chr(c) for c in umi)


def jmena_ze_sdk(koren: Any) -> frozenset[str]:
    """Jmena rozhrani a hodnot enumu z hlavicek SDK. CTE DISK.

    Osmy tvar pravidla 142 (verzalkove slovo uvnitr vety) potrebuje vedet,
    ktera slova jsou v SDK jmeny. Ten seznam se **neopisuje**: opsany by
    zestarl prvni zmenou v SDK a brana by mlcela prave o novem jmenu -
    tataz past, jakou uz jednou zpusobila opsana dotykova mez (`sonda.py`
    DOTYK = 48 proti `tokens.json`).

    **Proc funkce a ne pravidlo.** Tataz delba jako u `zkontroluj_dpi`:
    `validate_data` smi zaviset JEN na dokumentu, ktery dostal (testy
    porovnavaji beh v pameti s behem CLI v podprocesu, cteni z disku uvnitr
    pravidla by obe cesty rozeslo). Hlavicky proto cte MOST, tuhle funkci
    zavola s cestou z lockfile jadra a vysledek posle ve scene
    (`navrh.jmena_sdk`).

    Cte dva tvary a oba jsou rozhodnutelne strojove:

    * ``class IHwDiagnostics`` / ``struct IRadioInfo`` - jmeno rozhrani;
    * telo ``enum class Error : uint16_t { None = 0, Unavailable, ... }`` -
      hodnoty enumu (`Unavailable` je presne to slovo, ktere na panelu stoji
      jako `vraci UNAVAILABLE`).

    Vraci jmena tak, jak jsou napsana v hlavicce; porovnava se pozdeji bez
    ohledu na velikost pismen. Prazdna mnozina = nic se neprecetlo, a to
    volajici MUSI rict nahlas (`ZNACKA_R142_NEMERENO`), ne spolknout jako
    "cisto".
    """
    koren = Path(koren)
    jmena: set[str] = set()
    soubory = [koren] if koren.is_file() else sorted(koren.rglob("*.h"))
    for cesta in soubory:
        try:
            text = cesta.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        jmena.update(m.group(1) for m in _SDK_ROZHRANI.finditer(text))
        for m in _SDK_ENUM.finditer(text):
            for radek in m.group(1).split(","):
                h = _SDK_HODNOTA.match(radek.strip())
                if h:
                    jmena.add(h.group(1))
    return frozenset(jmena)


def _veta_strojove_jmeno(
    text: str,
    jmena_sdk: frozenset[str] = frozenset(),
) -> tuple[str, str] | None:
    """Duvod, proc `text` NENI veta pro cloveka -> (pojmenovani, nalezeny kus).

    `None` = veta je v poradku. Poradi rozhodovani i vzory jsou shodne
    s `brana_vety.strojove_jmeno` - viz komentar u `VETY_VZORY`.
    """
    if any(vzor.search(text) for vzor, _ in VETY_VYJIMKY):
        return None
    for klic, pojmenovani, vzor in VETY_VZORY:
        if klic == "ROZHRANI":
            for m in vzor.finditer(text):
                slovo = m.group(0)
                # Slovo psane cele verzalkami neni jmeno rozhrani PODLE TVARU:
                # konvence repa je I + CamelCase (`IHwDiagnostics`,
                # `INetworkService`, `I802154Service`), vsechna maji uvnitr
                # male pismeno. Bez teto vyjimky by na listech plnych verzalek
                # vznikaly nalezy typu IDENTITA, INKOUST, INVERSE - a jeden
                # takovy text v tomhle repu opravdu je ("INVERSE" ve
                # `widget_catalog.json`).
                #
                # POZOR: tohle uz NENI konec pribehu. Verzalkove slovo se
                # nezahazuje - propada do tridy `_verzalkove_jmeno()` nize,
                # kde se porovna se jmeny ze SDK. Diru "vraci UNAVAILABLE"
                # a "IHWDIAGNOSTICS" zaviral drive nikdo.
                if slovo in VETY_NENI_ROZHRANI or slovo.isupper():
                    continue
                return pojmenovani, slovo
            continue
        m = vzor.search(text)
        if m:
            return pojmenovani, m.group(0)
    return _verzalkove_jmeno(text, jmena_sdk)


def _verzalkove_jmeno(
    text: str,
    jmena_sdk: frozenset[str],
) -> tuple[str, str] | None:
    """Osmy tvar: verzalkove slovo uvnitr vety, ktere je jmenem ze SDK.

    Hranice je popsana u `_V_VERZALKY`. Strucne:

    * text CELY verzalkami je STITEK a tahle trida se v nem nemeri (hodnoty
      enumu jsou bezna slova, takze stitek `STAV` by se trefil s `Stav`);
    * ve vete, ktera ma i mala pismena, se verzalkove slovo porovna bez
      ohledu na velikost pismen; shoda se jmenem ze SDK = nalez.

    Bez seznamu jmen (`jmena_sdk` prazdna) trida MLCI - a to, ze se nemerila,
    rekne volajici (`ZNACKA_R142_NEMERENO`). Ticho vydavane za "cisto" je
    prave ta vada, kterou tahle kampan jinde odstranuje.
    """
    if not jmena_sdk:
        return None
    # (c) Jmeno rozhrani se dvema hrby se meri I VE STITKU VERZALKAMI.
    #     Bezi PRVNI a bez ohledu na velikost pismen zbytku textu, protoze
    #     'ZDROJ IHWDIAGNOSTICS' je tataz vada jako 'ZDROJ IHwDiagnostics'.
    rozhrani = _dvouhrba_rozhrani(jmena_sdk)
    if rozhrani:
        for m in _V_VERZALKY.finditer(text):
            slovo = m.group(0)
            if slovo in VETY_NENI_ROZHRANI or slovo in VETY_NENI_JMENO_SDK:
                continue
            if slovo.upper() in rozhrani:
                return "jmeno rozhrani ze SDK", slovo
    if not any(z.islower() for z in text):
        return None
    velka = {j.upper() for j in jmena_sdk}
    # (d) CamelCase jmeno ze SDK uvnitr vety. Meri se PRED verzalkovym
    #     tvarem: `NotFound` je ostrejsi dukaz nez `ERROR`, ktere je
    #     zaroven beznym slovem severity (reziduum R4 kritika).
    for m in _V_CAMEL.finditer(text):
        slovo = m.group(0)
        if slovo in VETY_NENI_ROZHRANI or slovo in VETY_NENI_JMENO_SDK:
            continue
        if slovo.upper() in velka:
            return "jmeno ze SDK", slovo
    for m in _V_VERZALKY.finditer(text):
        slovo = m.group(0)
        if slovo in VETY_NENI_ROZHRANI or slovo in VETY_NENI_JMENO_SDK:
            continue
        if slovo.upper() in velka:
            return "jmeno ze SDK", slovo
    return None


def _r142_ma_verzalkove_slovo(text: str) -> bool:
    """Je v tomhle textu co merit osmym tvarem? (pro hlaseni "nezmereno")

    Tataz podminka jako `_verzalkove_jmeno`, jen bez seznamu jmen. Bez ni by
    WARN "jmena SDK nedodana" vyskocil i na listech, kde by stejne nebylo
    co porovnavat - a varovani, ktere sviti porad, nikdo necte.
    """
    vzory = (
        (_V_VERZALKY,)
        if not any(z.islower() for z in text)
        else (_V_VERZALKY, _V_CAMEL)
    )
    return any(
        m.group(0) not in VETY_NENI_ROZHRANI
        and m.group(0) not in VETY_NENI_JMENO_SDK
        for vzor in vzory
        for m in vzor.finditer(text)
    )


def _druh_listu_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[str, list[Issue]]:
    """Precte ``navrh.druh`` -> (druh, nalezy o vadnem bloku).

    Chybejici klic = ``"obrazovka"``, tedy chovani, jake brana mela pred
    zavedenim vykladovych listu: kdo nic nerekl, je mereny. Preklep se
    NEPROMLCI - neznamy druh je ERROR, protoze tise prijaty preklep by
    pravidlo 142 vypnul na celem listu a nikdo by se to nedozvedel.
    """
    issues: list[Issue] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return DRUHY_LISTU[0], issues
    raw = blok.get("druh")
    if raw is None:
        return DRUHY_LISTU[0], issues
    if not isinstance(raw, str) or raw.strip().lower() not in DRUHY_LISTU:
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'druh' ma byt jeden z "
                f"{list(DRUHY_LISTU)}, je {raw!r}",
            )
        )
        return DRUHY_LISTU[0], issues
    return raw.strip().lower(), issues


def _jmena_sdk_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[frozenset[str], list[Issue]]:
    """Precte ``navrh.jmena_sdk`` -> (jmena, nalezy o vadnem bloku).

    Tentyz scenovy blok jako `_navrh_ze_sceny`, jen klic ``jmena_sdk``.
    Vozi ho most z `jmena_ze_sdk()`; validator hlavicky necte sam (viz
    docstring te funkce). Chybejici klic se tu **mlci** preskoci - o tom,
    ze se osmy tvar nemeril, mluvi az `ZNACKA_R142_NEMERENO` u prvniho
    textu, kde by bylo co merit.
    """
    issues: list[Issue] = []
    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return frozenset(), issues
    raw = blok.get("jmena_sdk")
    if raw is None:
        return frozenset(), issues
    if not isinstance(raw, list):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'jmena_sdk' ma byt seznam jmen, "
                f"je {type(raw).__name__}",
            )
        )
        return frozenset(), issues
    jmena: set[str] = set()
    for i, j in enumerate(raw):
        if not isinstance(j, str) or not j.strip():
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'jmena_sdk[{i}]' ma byt jmeno ze "
                    f"SDK, je {j!r}",
                )
            )
            continue
        jmena.add(j.strip())
    return frozenset(jmena), issues


def _r142_nalezy(
    wl: str,
    text: str,
    jmena_sdk: frozenset[str] = frozenset(),
) -> list[Issue]:
    """Rule 142: veta pro cloveka nese strojove jmeno.

    Zive protejsky ze snimku panelu: Settings "IHwDiagnostics" a "%.1f",
    Network "INetworkService::startScan() vraci UNAVAILABLE", SysMon
    "ISystemMetrics::radioTemp nedostupne", patka Diagnostics
    "ZDROJ IHwDiagnostics". Ctenar z nich nepozna, co ma delat: jmeno typu je
    adresa v kodu, ne odpoved na otazku "co se stalo".

    **Gatovani je PROFILOVE, ne datove**, a duvod je zmereny: F4 je jazykovy
    zakon TabOSu, ne vlastnost kazdeho panelu. Na korpusu ESPOS chyta tenhle
    sedmilistek jediny text, `"INVERSE"` ve `widget_catalog.json` (256x128,
    tedy profil oled256) - a je to nalez falesny. Bez profiloveho gatovani by
    pravidlo obvinilo cizi navrh z porusovani zakona, ktery pro nej neplati.
    (Tentyz text mlci i na tab5, ale az druhou vyjimkou - verzalkami; obe
    umlceni maji svuj test, protoze kazde umi zmizet zvlast.)

    Jeden text = NEJVYS jeden nalez: hlasi se prvni tvar v poradi
    `VETY_VZORY`, stejne jako ve `brana_vety.py`. Vyjmenovat u jedne vety
    vsechny jeji hrichy znamena psat tutez opravu nekolikrat.

    Osmy tvar (verzalkove slovo, ktere je jmenem ze SDK) potrebuje seznam
    jmen z hlavicek. Kdyz ho most nedodal, trida se NEMERI a rekne se to
    (WARN) - ale jen u textu, kde by opravdu bylo co porovnavat.
    """
    duvod = _veta_strojove_jmeno(text, jmena_sdk)
    if duvod is None:
        if not jmena_sdk and _r142_ma_verzalkove_slovo(text):
            return [
                Issue(
                    "WARN",
                    f"{wl}: {ZNACKA_R142_NEMERENO}: verzalkove slovo se nema s cim "
                    f"porovnat (navrh.jmena_sdk chybi) - text '{text}'",
                )
            ]
        return []
    pojmenovani, kus = duvod
    return [
        Issue(
            "ERROR",
            f"{wl}: {ZNACKA_R142} nese {pojmenovani}: '{kus}' - text '{text}'",
        )
    ]


def _slovnik_ze_sceny(
    scene: dict[str, Any],
    pfx: str,
) -> tuple[dict[str, dict[str, Any]], list[Issue]]:
    """Precte ``navrh.slovnik`` -> (slovnik stavu, nalezy o vadnem bloku).

    Klic vysledku je jmeno veci slozene na mala pismena (``microsd``),
    hodnota ``{"jmeno": "microSD", "stavy": ("vlozena, pripojena", ...)}``:
    jmeno veci je lidske slovo, ne identifikator, takze se paruje bez ohledu
    na velikost pismen - ale do hlasky patri tak, jak ho napsal generator.

    Tentyz scenovy blok jako `_navrh_ze_sceny`, jen klic ``slovnik``.
    Chybejici nebo neobjektovy blok se tu **mlci** preskoci: ohlasil ho uz
    `_navrh_ze_sceny` a tyz preklep nesmi hlasit dve mista (zakon "dva
    nalezy, jedna obet").

    Vec, ktera se do slovniku dostane dvakrat pod dvema tvary jmena
    (``microSD`` a ``microsd``), je ERROR a NEBERE se ani jedna: dva slovniky
    teze veci jsou prave ta rozdvojena pravda, kterou Rule 143 meri.
    """
    issues: list[Issue] = []
    slovnik: dict[str, dict[str, Any]] = {}

    blok = scene.get(NAVRH_KLIC)
    if not isinstance(blok, dict):
        return slovnik, issues
    raw = blok.get("slovnik")
    if raw is None:
        return slovnik, issues
    if not isinstance(raw, dict):
        issues.append(
            Issue(
                "ERROR",
                f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'slovnik' ma byt objekt, "
                f"je {type(raw).__name__}",
            )
        )
        return slovnik, issues

    for vec_raw, stavy_raw in raw.items():
        vec = str(vec_raw).strip()
        if not vec:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'slovnik' ma vec bez jmena ({vec_raw!r})",
                )
            )
            continue
        if not isinstance(stavy_raw, list) or not stavy_raw:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'slovnik.{vec}' ma byt neprazdny seznam "
                    f"stavu, je {stavy_raw!r}",
                )
            )
            continue
        stavy: list[str] = []
        for stav_raw in stavy_raw:
            if not isinstance(stav_raw, str) or not stav_raw.strip():
                issues.append(
                    Issue(
                        "ERROR",
                        f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'slovnik.{vec}' ma byt seznam vet, "
                        f"je v nem {stav_raw!r}",
                    )
                )
                stavy = []
                break
            stavy.append(_zhustit_mezery(stav_raw))
        if not stavy:
            continue
        klic = vec.casefold()
        if klic in slovnik:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {ZNACKA_NAVRH_VADNY}: 'slovnik' zna vec "
                    f"'{slovnik[klic]['jmeno']}' i '{vec}' - dve jmena teze veci, nevim, "
                    f"ktery slovnik plati",
                )
            )
            del slovnik[klic]
            continue
        slovnik[klic] = {"jmeno": vec, "stavy": tuple(stavy)}

    return slovnik, issues


def _r143_nalezy(
    wl: str,
    prvek: dict[str, Any],
    role: str | None,
    text: str,
    slovnik: dict[str, dict[str, Any]],
) -> list[Issue]:
    """Rule 143: o teze veci mluvi kazdy list jinak (WARNING).

    Zivy protejsek: microSD. Diagnostics rika "vlozena, nepripojena", Files
    "karta neni vlozena nebo mount selhal", Hex "nedostupne" - tri vety o teze
    karte, z toho jedna tvrdi, ze vlozena neni. Ctenar si z toho jeden obraz
    sveta nesestavi a nema jak poznat, ktera appka lze.

    **Krizeni listu se meri BEZ globalniho stavu.** Validator vidi jeden
    dokument; rozpor mezi tremi appkami se chyta tim, ze vsechny tri se meri
    proti JEDNOMU slovniku (kit ho vozi z `tokens.json` do sceny). Tim se
    otazka "shodnou se listy?" prevede na otazku "drzi se list slovniku?",
    kterou lze zodpovedet z jednoho listu. Kdo to bude chtit "vylepsit" na
    porovnavani mezi soubory, at si nejdriv rozmysli, ze pravidlo pak
    prestane platit pro jeden list pusteny samostatne.

    **Zavaznost je WARNING**, ne ERROR: neni to vada rozvrzeni (nic se
    neoreze, nic nepretece), je to rozpor ve slovniku. Rozhodl tak majitel.

    **MERI SE JEN ROLE `stav`** (rozhodnuti koordinatora 9. 9. 2026). Do
    te doby pravidlo merilo KAZDOU hodnotovou roli s `data-vec` - a na 62
    zivych listech vydalo deset nalezu, z nichz nebyl pravdivy ANI JEDEN:

        'USB-A host': 'LA1010 + FT232R'          'USB-A host': '2 zarizeni'
        'sit': 'NERTERA - -58 dBm - 2,4 GHz'     'sit': 'NERTERA'
        'microSD': '28,4 GB volno'

    Vsech pet je HODNOTA O VECI (kolik volneho mista, ktera sit, kolik
    zarizeni), ne STAV VECI. Pravidlo tedy merilo jinou velicinu, nez
    slibuje, a deset radku sumu se ctenar nauci preskakovat - vcetne toho
    jedenacteho, ktery pravdivy bude. Uzsi role je levnejsi nez chytrejsi
    heuristika nad textem: co je stav a co hodnota, vi generator, ne
    meridlo.

    Kdo tu mlci a proc:

    * role neni `stav` - "28,4 GB volno" je hodnota o karte, ne jeji stav;
      hlavicka sloupce "microSD" vec jen jmenuje. Slib nese ROLE, ne slovo.
      Ze se na listu, ktery o veci mluvi, ale zadnou roli `stav` nema,
      NEMERILO, rekne `validate_data` jednou za list;
    * prazdny text patri Rule 138 a samotna pomlcka Rule 139 - jedna obet,
      jeden nalez;
    * text, ktery je JEN jmenem veci ("microSD"), je navesti, ne tvrzeni.

    **Mez, kterou je poctive znat.** Meri se PODRETEZEC (bez ohledu na
    velikost pismen a na nasobne mezery), takze veta, ktera povoleny stav
    pouzije a jeste neco pridá ("karta neni vlozena nebo mount selhal"),
    PROJDE. Slovnik meri SLOVNIK, ne pocet tvrzeni v jedne vete; veta, ktera
    rika dve veci najednou, je jina vada a potrebuje jine meridlo. Diakritika
    se na hola pismena neprevadi: "vlozena" a "vložena" jsou pro panel dve
    ruzna slova (vestaveny font LVGL to umi dokazat - ceske pismeno v nem
    proste neni), takze slovnik musi byt psany touz abecedou jako texty.

    Vec vozi generator (``data-vec``), jinak se hleda podretezcem jmena
    v textu. Vec BEZ slovniku je WARN "kontrola NEPROBEHLA" (vzor Rule 133
    a Rule 140): most o veci neco tvrdil, meridlo se nepustilo - a ticho by
    vypadalo k nerozeznani od "v poradku".
    """
    if role != ROLE_STAV:
        return []
    vec = prvek.get("vec")
    if vec is None and not slovnik:
        return []
    t = _zhustit_mezery(text)
    if not t or t in POMLCKY:
        return []
    tl = t.casefold()

    if isinstance(vec, str):
        zaznam = slovnik.get(vec.casefold())
        if zaznam is None:
            znam = ", ".join(sorted(z["jmeno"] for z in slovnik.values())) or "zadnou vec"
            return [
                Issue(
                    "WARN",
                    f"{wl}: {ZNACKA_R143_NEMERENO}: prvek mluvi o veci '{vec}', ale slovnik "
                    f"stavu pro ni nikdo nedodal (znam: {znam}) - kontrola NEPROBEHLA",
                )
            ]
        zaznamy = [zaznam]
    else:
        zaznamy = [z for klic, z in slovnik.items() if klic in tl]

    issues: list[Issue] = []
    for zaznam in zaznamy:
        jmeno = zaznam["jmeno"]
        if tl == jmeno.casefold():
            continue
        if any(stav.casefold() in tl for stav in zaznam["stavy"]):
            continue
        issues.append(
            Issue(
                "WARN",
                f"{wl}: {ZNACKA_R143} '{jmeno}': text '{text}' nepouziva zadny stav ze "
                f"slovniku ({' | '.join(zaznam['stavy'])})",
            )
        )
    return issues


def slovnik_prurez(
    tvrzeni: dict[str, list[tuple[str, str]]],
    slovnik: dict[str, dict[str, Any]],
) -> list[Issue]:
    """Prurez listu: co o teze veci tvrdi VSECHNY listy dohromady. CISTA.

    Rule 143 meri kazdy list ZVLAST proti jednomu slovniku ("drzi se list
    slovniku?"). To ale nechyti rozpor, kde oba listy slovnik DRZI a presto
    si odporuji: Diagnostics rika o microSD "vlozena, nepripojena", Files
    "neni vlozena" - obe vety JSOU ve slovniku, jen kazda popisuje jiny
    svet. Fotoprotokol A-4: pet appek, pet vet o jedne karte. Validator
    vidi jeden dokument, takze tohle je funkce pro MOST, ktery ma vsechny
    sceny najednou; sem patri proto, ze slovnik i shoda stavu se maji merit
    JEDNIM kodem, ne dvema opisy.

    Vstup:

    * ``tvrzeni``: ``{jmeno_listu: [(vec, text), ...]}`` - JEN prvky s roli
      `stav` (slib nese role, ne slovo - tataz zavora jako u Rule 143);
    * ``slovnik``: vysledek `_slovnik_ze_sceny` (klic = vec casefold,
      hodnota ``{"jmeno", "stavy"}``).

    Vystup je seznam nalezu, deterministicky serazeny podle veci:

    * **`ZNACKA_R143_PRUREZ`** (WARN): o jedne veci tvrdi dva a vic listu
      dva a vic RUZNYCH stavu ze slovniku. Hlaska vyjmenuje, ktery list
      tvrdi co - to je ta veta, kterou clovek potrebuje, aby vybral JEDEN
      zdroj pravdy.
    * **`ZNACKA_R143_VEC_NEMERENO`** (WARN): vec ze slovniku, o ktere zadny
      list netvrdi stav. Zavora je per-VEC: kritik (espos-vse-oprava, 4.5)
      dolozil, ze `USB-A host` a `sit` nemaji roli `stav` na zadnem ze 62
      listu, a per-listova zavora Rule 143 o tom nerekla ani slovo - dve ze
      ctyr polozek slovniku se nikdy s nicim neporovnaly a "0 nalezu" se
      cetlo jako "0 rozporu".

    Normalizace je tataz jako v Rule 143: bez ohledu na velikost pismen a na
    nasobne mezery, diakritika se NEPREVADI. Stav se hleda PODRETEZCEM
    a bere se NEJDELSI shoda: "pripojena" je podretezcem "vlozena,
    nepripojena", takze bez teto volby by veta "vlozena, nepripojena"
    tvrdila DVA stavy naraz a prurez by obvinil sam sebe. Text, ktery
    zadny stav neobsahuje, sem NEPATRI - hlasi ho Rule 143 na svem listu
    a dva nalezy na jednu obet se nepisou. Tentyz list, ktery tvrdi dva
    ruzne stavy, je rozpor stejne jako dva listy: obrazovka nemuze o karte
    tvrdit dve veci naraz.
    """
    issues: list[Issue] = []
    # vec (casefold) -> stav -> serazena jmena listu
    tvrdi: dict[str, dict[str, set[str]]] = {klic: {} for klic in slovnik}
    for list_jmeno, polozky in tvrzeni.items():
        for vec, text in polozky:
            zaznam = slovnik.get(str(vec).casefold())
            if zaznam is None:
                continue
            t = _zhustit_mezery(str(text)).casefold()
            if not t or t in POMLCKY:
                continue
            shody = [s for s in zaznam["stavy"] if s.casefold() in t]
            if not shody:
                continue
            stav = max(shody, key=len)
            tvrdi[str(vec).casefold()].setdefault(stav, set()).add(str(list_jmeno))
    for klic in sorted(tvrdi):
        jmeno = slovnik[klic]["jmeno"]
        stavy = tvrdi[klic]
        if not stavy:
            issues.append(
                Issue(
                    "WARN",
                    f"{ZNACKA_R143_VEC_NEMERENO}: o veci '{jmeno}' netvrdi stav zadny "
                    f"list (slovnik zna: {' | '.join(slovnik[klic]['stavy'])}) - "
                    f"slovnik se s nicim NEPOROVNAL",
                )
            )
            continue
        if len(stavy) < 2:
            continue
        popis = "; ".join(
            f"'{stav}' tvrdi {', '.join(sorted(listy))}" for stav, listy in sorted(stavy.items())
        )
        issues.append(
            Issue(
                "WARN",
                f"{ZNACKA_R143_PRUREZ}: '{jmeno}' ma {len(stavy)} ruzne stavy "
                f"na {len(set().union(*stavy.values()))} listech: {popis}",
            )
        )
    return issues


# ── Main validator ─────────────────────────────────────────────────────────


def validate_data(
    data: dict[str, Any],
    *,
    file_label: str,
    warnings_as_errors: bool,
    strict_critical: bool = False,
) -> list[Issue]:
    issues: list[Issue] = []

    # Which panel is this drawn for? Every device-dependent number below is
    # rebound from the profile, so the rules read the same but measure the
    # right display. Unrecognised data resolves to the OLED, i.e. the exact
    # behaviour this validator had before profiles existed.
    doc_prof = _profile_for(data)
    prof = doc_prof
    CHAR_W = prof.char_w
    CHAR_H = prof.char_h
    MIN_TEXT_H = prof.min_text_h
    FONT_CHARS = prof.font_chars if prof.font_chars is not None else None
    MAX_TEXT_LEN = prof.max_text_len
    MAX_WIDGETS_PER_SCENE = prof.soft_widgets
    HARD_WIDGET_LIMIT = prof.hard_widgets
    MIN_EDGE_MARGIN = prof.min_edge_margin
    RENDER_PAD = prof.render_pad
    MIN_CONTRAST = prof.min_contrast
    MIN_VISIBLE_BRIGHTNESS = prof.min_visible_brightness

    root_w = data.get("width")
    root_h = data.get("height")
    if root_w is not None and not _is_int(root_w):
        issues.append(Issue("ERROR", f"{file_label}: root.width must be int"))
    if root_h is not None and not _is_int(root_h):
        issues.append(Issue("ERROR", f"{file_label}: root.height must be int"))

    scenes = _scenes_from_data(data)
    if not scenes:
        issues.append(Issue("ERROR", f"{file_label}: no scenes found (missing/invalid 'scenes')"))
        return issues

    # ── Rule 36: Scene name validation ──
    for scene_name in scenes:
        if not scene_name or not _SCENE_NAME_RE.match(scene_name):
            issues.append(
                Issue("WARN", f"{file_label}: scene name '{scene_name}' has invalid characters")
            )

    for scene_name, scene in scenes.items():
        pfx = f"{file_label}: {scene_name}"
        scene_w = scene.get("width", root_w)
        scene_h = scene.get("height", root_h)
        if not _is_int(scene_w) or int(scene_w) <= 0:
            issues.append(Issue("ERROR", f"{pfx}: width must be int >= 1"))
            continue
        if not _is_int(scene_h) or int(scene_h) <= 0:
            issues.append(Issue("ERROR", f"{pfx}: height must be int >= 1"))
            continue
        sw, sh = int(scene_w), int(scene_h)

        # One document can hold scenes for different panels. Resolving the
        # profile once for the whole file measured every scene by the first
        # one's panel. An explicit "device" key still governs the document;
        # otherwise each scene is matched on its own dimensions.
        if not isinstance(data.get("device"), str):
            prof = _profile_for({"width": sw, "height": sh})
            CHAR_W = prof.char_w
            CHAR_H = prof.char_h
            MIN_TEXT_H = prof.min_text_h
            FONT_CHARS = prof.font_chars
            MAX_TEXT_LEN = prof.max_text_len
            MAX_WIDGETS_PER_SCENE = prof.soft_widgets
            HARD_WIDGET_LIMIT = prof.hard_widgets
            MIN_EDGE_MARGIN = prof.min_edge_margin
            RENDER_PAD = prof.render_pad
            MIN_CONTRAST = prof.min_contrast
            MIN_VISIBLE_BRIGHTNESS = prof.min_visible_brightness

        widgets = scene.get("widgets", [])
        if not isinstance(widgets, list):
            issues.append(Issue("ERROR", f"{pfx}: widgets must be a list"))
            continue

        # ── Rule 22: Scene must not be empty ──
        if not widgets:
            issues.append(Issue("WARN", f"{pfx}: scene has 0 widgets"))

        # ── Merena data z artboardu: scenovy blok "navrh" ──
        # Bez bloku vyjde prazdno a pravidla nad merenim mlci; vadny blok se
        # ohlasi (viz `_navrh_ze_sceny`).
        znama_id = {
            str(w.get("_widget_id") or w.get("id"))
            for w in widgets
            if isinstance(w, dict) and (w.get("_widget_id") or w.get("id"))
        }
        navrh_prvky, navrh_pasy, navrh_nalezy = _navrh_ze_sceny(scene, pfx, znama_id)
        issues.extend(navrh_nalezy)

        # ── Rule 140: mrizka nepojme vsechny polozky ──
        # Scenove pravidlo, ne widgetove: mrizka je vlastnost LISTU. Bez
        # deklarovane kapacity mlci; s kapacitou a bez poctu polozek se
        # prizna, ze nemerila (viz `_r140_nalezy`).
        navrh_mrizky, mrizky_nalezy = _mrizky_ze_sceny(scene, pfx)
        issues.extend(mrizky_nalezy)
        issues.extend(_r140_nalezy(pfx, navrh_mrizky))

        # ── Rule 152: nakreslena mrizka bez deklarovane kapacity ──
        # Druha strana teze diry: Rule 140 mlci bez `data-kapacita`, tohle
        # rekne, ze mlcela (viz `_r152_nalezy`). Gatovano blokem `navrh`.
        issues.extend(
            _r152_nalezy(pfx, widgets, navrh_mrizky, isinstance(scene.get(NAVRH_KLIC), dict))
        )

        # ── Rule 143: slovnik stavu teze veci ──
        # Slovnik je vlastnost SCENY, stejne jako mrizky: kit ho vozi
        # z `tokens.json` a kazdy list se meri proti temuz. Tim se rozpor
        # NAPRIC listy meri bez globalniho stavu (viz `_r143_nalezy`).
        navrh_slovnik, slovnik_nalezy = _slovnik_ze_sceny(scene, pfx)
        issues.extend(slovnik_nalezy)
        # Ticho pravidla 143 musi byt VIDET, jinak se nemereni necha cist
        # jako "vsechny stavy sedi". Hlasi se JEDNOU za list a jen tehdy,
        # kdyz by pravidlo jinak MELO co merit:
        #
        #   list mluvi o VECI ZE SLOVNIKU (`data-vec`), ale ani jeden
        #   prvek na nem nema roli `stav`.
        #
        # Uzsi podminka nez "list nema roli stav": vetsina obrazovek o
        # zadnem sdilenem stavu netvrdi nic (Terminal, Hex, klavesnice) a
        # hlaska nad nimi by byla sum na 50 listech ze 62 - tedy prave to,
        # co se timhle rozhodnutim odstranuje. Zavora je tataz jako u 148,
        # 150 a 151: "pulka smlouvy dosla, druha ne".
        if navrh_slovnik:
            veci_listu = {
                pr["vec"].casefold() for pr in navrh_prvky.values()
                if isinstance(pr.get("vec"), str)
            } & set(navrh_slovnik)
            if veci_listu and not any(
                    pr.get("role") == ROLE_STAV for pr in navrh_prvky.values()):
                jmena = ", ".join(sorted(navrh_slovnik[k]["jmeno"]
                                         for k in veci_listu))
                issues.append(
                    Issue(
                        "WARN",
                        f"{pfx}: {ZNACKA_R143_ROLE_NEMERENO}: list mluvi o veci "
                        f"({jmena}), ale zadny prvek netvrdi STAV - slovnik se "
                        f"NEPOROVNAVAL",
                    )
                )

        # ── Rule 142, osmy tvar: jmena ze SDK ──
        # Seznam se neopisuje, cte ho `jmena_ze_sdk()` z hlavicek a vozi ho
        # most ve scene. Validator sam na disk nesaha (viz `zkontroluj_dpi`).
        navrh_jmena_sdk, jmena_nalezy = _jmena_sdk_ze_sceny(scene, pfx)
        issues.extend(jmena_nalezy)

        # ── Rule 146: smaltove plochy sceny ──
        # Seznam JMEN prvku, ne obdelniku: obdelnik uz scena nese, prislusnost
        # ne (viz `_plochy_ze_sceny`). Obdelnik se proto dohleda ve widgetech
        # a neviditelna plocha se preskoci - stejne jako v Rule 135 a 136.
        navrh_plochy, plochy_nalezy = _plochy_ze_sceny(scene, pfx, znama_id)
        issues.extend(plochy_nalezy)
        plochy_rects: list[tuple[str, tuple[int, int, int, int]]] = []
        if navrh_plochy:
            hledane = set(navrh_plochy)
            for cw in widgets:
                if not isinstance(cw, dict) or cw.get("visible") is False:
                    continue
                cid = cw.get("_widget_id") or cw.get("id")
                if not isinstance(cid, str) or cid not in hledane:
                    continue
                if not all(_is_int(cw.get(k)) for k in ("x", "y", "width", "height")):
                    continue
                plochy_rects.append(
                    (
                        cid,
                        (
                            int(cw["x"]),
                            int(cw["y"]),
                            int(cw["width"]),
                            int(cw["height"]),
                        ),
                    )
                )

        # ── Rule 147: delici cary sceny ──
        # Vlasove linky do sceny nevstupuji (most zahazuje vsechno tenci nez
        # 2 px), takze se vozi zvlast jako obdelniky.
        navrh_cary, cary_nalezy = _cary_ze_sceny(scene, pfx)
        issues.extend(cary_nalezy)

        # ── Rule 148: zavazna skala rezu + jmenovite vyjimky listu ──
        # Vlastnost SCENY, ne prvku: skala je smlouva o celem jazyce
        # a vyjimky plati PRO TENHLE LIST (rez 13 px je na klavesnici
        # vedomy, na Nastaveni preklep).
        navrh_skala, skala_nalezy = _skala_ze_sceny(scene, pfx)
        issues.extend(skala_nalezy)

        # ── Rule 150: paleta listu ──
        navrh_paleta, paleta_nalezy = _paleta_ze_sceny(scene, pfx)
        issues.extend(paleta_nalezy)

        # ── Rule 151: soustava odsazeni ──
        navrh_soustava, soustava_nalezy = _soustava_ze_sceny(scene, pfx)
        issues.extend(soustava_nalezy)

        # ── Rule 142: obrazovka, nebo vyklad o navrhu? ──
        # Vykladovy list vadu CITUJE misto aby ji delal (viz `DRUHY_LISTU`).
        # Ticho je videt: rekne se jednou za list, at nikdo necte nemereno
        # jako v poradku.
        druh_listu, druh_nalezy = _druh_listu_ze_sceny(scene, pfx)
        issues.extend(druh_nalezy)
        # Rule 148: skala nedosla? Rekne se to JEDNOU za list, ne u kazdeho
        # z tisice prvku - a rekne se to jen tehdy, kdyz na listu vubec
        # nejaky mereny rez je. Ticho o nezmerenem se nesmi cist jako cisto.
        if navrh_skala is None and any("font_size" in pr for pr in navrh_prvky.values()):
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R148_NEMERENO}: rezy pisma jsou zmerene, ale "
                    f"zavazna skala nedosla - rezy se NEPOROVNAVALY",
                )
            )
        # Tataz uvaha pro Rule 151. Zavora je `orez`, ne `vsazka`:
        #
        # Do 9. 9. 2026 se NEMERENO hlasilo jen tehdy, kdyz nejaky blok
        # DEKLAROVAL vlastni vsazku - to jsou dva klavesnicove listy.
        # Jenze `DnesSystemMonitor`, na kterem lezi vsechny ctyri zive
        # nalezy pravidla 151, zadnou vlastni vsazku nema. Zavora tedy
        # mlcela prave tam, kde pravidlo nachazi: kdyby ze scen zmizel
        # blok `soustava`, ctyri nalezy by zmizely BEZE SLOVA.
        #
        # `orez` je klic, ktery na prvek posila JEN most kitu (3751 prvku
        # na 62 listech), a to prave tehdy, kdyz prvek zmeril. Znamena
        # tedy "tenhle list most opravdu prosel" - cizi scena (editor,
        # ruzne psany navrh) ho nema, takze se na ni NEMERENO nevystreli.
        # Tataz uvaha jako u Rule 148 o `font_size`.
        #
        # `vsazka` v podmince ZUSTAVA vedle nej: deklarovana vlastni vsazka
        # bez soustavy je ROZBITA SMLOUVA i tehdy, kdyz prvek prosel jinou
        # cestou nez mostem. Stara zavora byla spravna, jen prilis uzka -
        # nerusi se, rozsiruje se.
        if navrh_soustava is None and any(
                ("orez" in pr or "vsazka" in pr) for pr in navrh_prvky.values()):
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R151_NEMERENO}: soustava odsazeni nedosla - "
                    f"leve hrany textu se proti ni NEMERILY",
                )
            )
        if prof.vety_pro_cloveka and druh_listu == "vyklad":
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R142_VYKLAD}, ne obrazovka - pravidlo 142 "
                    f"se na nem NEMERI (zakon F4 mluvi o textu na pristroji, "
                    f"vyklad vadu cituje)",
                )
            )
        # ── Rule 150: barvy prvku proti palete ──
        # Az TED, kdyz uz je videt cely seznam widgetu: hlasi se kazda ruzna
        # barva JEDNOU s poctem prvku, ne kazdy prvek zvlast (viz
        # `_r150_nalezy`).
        #
        # Bez palety se rekne NAHLAS, ze se nemerilo - a plati pro to tataz
        # UZSI zavora jako u Rule 148 a 151. Do 9. 9. 2026 tady zavora
        # nebyla vubec: jedna carka navic v `tokens.json` srazila tridu
        # `paleta` z peti nalezu na nulu UPLNE TISE a brana zustala zelena
        # (zmereno v pisikovisti kritika). Duvod, proc se NEMERENO nehlasilo,
        # byl spravny - vystrelovalo by na kazde cizi scene vcetne kazde
        # sceny editoru - ale lek byl silnejsi nez nemoc.
        #
        # Zavora je `inkoust`: klic, ktery na prvek posila JEN most kitu
        # (3751 prvku na 62 listech) a jen tehdy, kdyz mu barvu ZMERIL.
        # "Barvy jsou zmerene, ale paleta nedosla" je proto stav, ktery
        # nemuze nastat u ciziho navrhu - a u kitoveho znamena, ze se
        # NEMERILO. `color_fg` widgetu by se na tohle nehodilo: ten ma
        # kazda scena, takze by zavora byla jen jinak napsane "vzdycky".
        if navrh_paleta is None and any("inkoust" in pr for pr in navrh_prvky.values()):
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {ZNACKA_R150_NEMERENO}: barvy prvku jsou zmerene, ale "
                    f"paleta navrhu nedosla - barvy se NEPOROVNAVALY",
                )
            )
        issues.extend(_r150_nalezy(pfx, widgets, navrh_paleta))

        # ── Rule 148: rezy pisma proti zavazne skale ──
        # Take scenove a ze stejneho duvodu jako Rule 150: rez se opakuje,
        # takze se hlasi po REZECH s poctem prvku, ne po prvcich.
        issues.extend(_r148_nalezy(pfx, widgets, navrh_prvky, navrh_skala))

        # Rule 138 se pta "nese sdeleni nekdo UVNITR me?" geometricky, takze
        # potrebuje texty cele sceny predem. Bez merenych dat se nestavi.
        texty_sceny = _texty_sceny(widgets) if navrh_prvky else []
        # Vozi most rodokmen? Kdyz ANO, Rule 138 se pta na POTOMKY;
        # kdyz NE (starsi scena, dokument editoru), spadne na hrubsi
        # meridlo `rodic` = obdelnik offsetParentu. Ptat se jen
        # geometricky uz ne - prazdny smalt tak umlcel kazdy cizi
        # popisek, ktery pod nim nahodou lezel (viz `_text_uvnitr`).
        zna_rodic_id = any("rodic_id" in p for p in navrh_prvky.values())

        seen_ids: set[str] = set()

        for idx, w in enumerate(widgets):
            ref = _wref(scene_name, w, idx)
            wl = f"{pfx}: {ref}"
            if not isinstance(w, dict):
                issues.append(Issue("ERROR", f"{wl}: widget must be an object"))
                continue

            # ── Rule 2: Valid widget type ──
            wtype = w.get("type")
            if not isinstance(wtype, str) or not wtype.strip():
                issues.append(Issue("ERROR", f"{wl}: missing/invalid 'type'"))
                continue
            wt = wtype.lower()
            if wt not in WIDGET_TYPE_MAP:
                issues.append(Issue("ERROR", f"{wl}: unsupported type '{wtype}'"))

            # ── Required geometry fields ──
            for key in ("x", "y", "width", "height"):
                if key not in w:
                    issues.append(Issue("ERROR", f"{wl}: missing '{key}'"))

            x = w.get("x")
            y = w.get("y")
            ww = w.get("width")
            hh = w.get("height")
            text_raw = w.get("text", "")
            text = str(text_raw) if isinstance(text_raw, str) else ""
            has_border = w.get("border", False)
            runtime_raw = w.get("runtime", "")
            runtime = str(runtime_raw) if isinstance(runtime_raw, str) else ""

            # Merena data mostu pro tento widget. Prazdny slovnik = nemereno.
            wid_navrh = w.get("_widget_id") or w.get("id")
            navrh_prvek = navrh_prvky.get(wid_navrh, {}) if isinstance(wid_navrh, str) else {}

            # ── Rule 5: Integer coordinates ──
            all_int = True
            for dim_name, dim_val in [("x", x), ("y", y), ("width", ww), ("height", hh)]:
                if not _is_int(dim_val):
                    issues.append(Issue("ERROR", f"{wl}: {dim_name} must be int"))
                    all_int = False
            if not all_int:
                continue
            xi = int(x)
            yi = int(y)
            wwi = int(ww)
            hhi = int(hh)
            x, y, ww, hh = xi, yi, wwi, hhi

            # ── Rule 3: Positive dimensions ──
            if ww < 1 or hh < 1:
                issues.append(Issue("ERROR", f"{wl}: dimensions {ww}x{hh} must be >= 1x1"))

            # ── Rule 4: Within scene bounds ──
            if x < 0 or y < 0:
                issues.append(Issue("ERROR", f"{wl}: origin ({x},{y}) is negative"))
            intersects_scene = (x < sw) and (y < sh) and (x + ww > 0) and (y + hh > 0)
            if (x + ww > sw or y + hh > sh) and intersects_scene and w.get("visible") is not False:
                issues.append(
                    Issue("WARN", f"{wl}: rect ({x},{y},{ww},{hh}) out of bounds {sw}x{sh}")
                )

            # ── Rule 1: Unique widget IDs ──
            widget_id = w.get("_widget_id") or w.get("id")
            if widget_id is not None:
                if not isinstance(widget_id, str):
                    issues.append(Issue("ERROR", f"{wl}: _widget_id/id must be string"))
                else:
                    if widget_id in seen_ids:
                        issues.append(Issue("ERROR", f"{wl}: duplicate id '{widget_id}'"))
                    seen_ids.add(widget_id)

            # ── Bool fields ──
            for key in ("border", "checked", "visible", "enabled"):
                if key in w and not _is_bool(w.get(key)):
                    issues.append(Issue("ERROR", f"{wl}: '{key}' must be boolean"))

            # ── max_lines ──
            if (
                "max_lines" in w
                and w.get("max_lines") is not None
                and not _is_int(w.get("max_lines"))
            ):
                issues.append(Issue("ERROR", f"{wl}: max_lines must be int or null"))
            if _is_int(w.get("max_lines")) and int(w.get("max_lines")) < 0:  # type: ignore[arg-type]
                issues.append(Issue("ERROR", f"{wl}: max_lines must be >= 0"))

            # ── Rule 12: Valid border_style ──
            if "border_style" in w:
                bs = w.get("border_style")
                if not isinstance(bs, str) or bs.lower() not in ALLOWED_BORDER_STYLES:
                    issues.append(Issue("ERROR", f"{wl}: invalid border_style '{bs}'"))

            # ── Rule 11: Valid align/valign ──
            if "align" in w:
                a = w.get("align")
                if not isinstance(a, str) or a.lower() not in ALLOWED_ALIGN:
                    issues.append(Issue("ERROR", f"{wl}: invalid align '{a}'"))
            if "valign" in w:
                va = w.get("valign")
                if not isinstance(va, str) or va.lower() not in ALLOWED_VALIGN:
                    issues.append(Issue("ERROR", f"{wl}: invalid valign '{va}'"))

            # ── Rule 14: Valid text_overflow ──
            if "text_overflow" in w:
                ov = w.get("text_overflow")
                if not isinstance(ov, str) or ov.lower() not in ALLOWED_OVERFLOW:
                    issues.append(Issue("ERROR", f"{wl}: invalid text_overflow '{ov}'"))

            # ── Rule 13: border=True requires a visible border_style ──
            bstyle = (str(w.get("border_style", "none")) or "none").lower()
            if has_border is True and bstyle in {"none", ""}:
                issues.append(Issue("WARN", f"{wl}: border=True but border_style='{bstyle}'"))

            # ── Rule 6: Minimum height for text types ──
            if wt in TEXT_TYPES and hh < MIN_TEXT_H:
                issues.append(Issue("WARN", f"{wl}: h={hh} < min {MIN_TEXT_H} for text widget"))

            # ── Rule 8: Minimum widget width for text types ──
            if wt in TEXT_TYPES and text:
                min_w = RENDER_PAD * 2 + CHAR_W
                if ww < min_w:
                    issues.append(Issue("WARN", f"{wl}: w={ww} < min {min_w} (can't fit 1 char)"))

            # ── Rule 7: Text overflow check (H+V) ──
            if wt in TEXT_TYPES and text:
                border_inset = 1 if has_border else 0
                margin_each = RENDER_PAD + border_inset
                margin = margin_each * 2
                inner_w = ww - margin
                inner_h = hh - margin
                max_lines = inner_h // CHAR_H if inner_h > 0 else 0
                max_chars = inner_w // CHAR_W if inner_w > 0 else 0
                if max_lines < 1:
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: text cannot fit: h={hh} (inner_h={inner_h}) < font_h={CHAR_H}",
                        )
                    )
                # Zmerena sirka textu (blok "navrh") vypina VODOROVNOU pulku
                # Rule 7 pro tento widget: znakovy odhad pro font 6x8 a mereni
                # skutecneho fontu jsou dve meridla s ruznymi predpoklady a
                # nesmi soudit tyz pixel. Rule 137 nastupuje misto nej; kdyz
                # se nedomeri, rekne to nahlas. Svisla pulka (vyska radku)
                # zustava, tu Rule 137 nemeri.
                if (
                    max_chars > 0
                    and len(text) > max_chars
                    and navrh_prvek.get("sirka_textu") is None
                ):
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: text '{text}' ({len(text)} ch) overflows max {max_chars} chars",
                        )
                    )

            # ── Rule 9: Value range sanity ──
            if wt in ("gauge", "progressbar", "slider"):
                vmin = w.get("min_value", 0)
                vmax = w.get("max_value", 100)
                val = w.get("value", 0)
                if _is_int(vmin) and _is_int(vmax):
                    if vmin >= vmax:
                        issues.append(Issue("ERROR", f"{wl}: min_value={vmin} >= max_value={vmax}"))
                    if _is_int(val) and (val < vmin or val > vmax):
                        issues.append(Issue("WARN", f"{wl}: value={val} not in [{vmin},{vmax}]"))

            # ── Rule 18: Minimum gauge/slider/progressbar size ──
            if wt == "gauge" and (ww < 8 or hh < 8):
                issues.append(Issue("ERROR", f"{wl}: gauge {ww}x{hh} too small (min 8x8)"))
            if wt == "slider" and ww < 16:
                issues.append(Issue("ERROR", f"{wl}: slider w={ww} too narrow (min 16)"))
            if wt == "progressbar" and ww < 8:
                issues.append(Issue("ERROR", f"{wl}: progressbar w={ww} too narrow (min 8)"))

            # ── Rule 135: touch target measured in millimetres, not pixels ──
            #
            # A pixel count says nothing about whether a finger can hit it: the
            # same 44 px is 9.3 mm on a 120 PPI panel and 3.8 mm on a 294 PPI
            # one. Published minima are all physical — Apple 7.0 mm, Material
            # 7.6 mm, ISO 9241-411 7 mm — so the profile carries PPI and the
            # rule converts. Profiles with ppi=0 (no touch panel) skip it.
            if prof.min_touch_px and wt in TOUCH_WIDGET_TYPES and w.get("visible") is not False:
                small = min(ww, hh) if _is_int(ww) and _is_int(hh) else None
                if small is not None and small < prof.warn_touch_px:
                    lvl = "ERROR" if small < prof.min_touch_px else "WARN"
                    issues.append(
                        Issue(
                            lvl,
                            f"{wl}: touch target {ww}x{hh} is {prof.mm(small):.1f} mm "
                            f"on its short side (min {prof.mm(prof.warn_touch_px):.1f} mm "
                            f"= {prof.warn_touch_px} px on this panel)",
                        )
                    )

            # ── Rule 136: oriznuti (presah rodice / zasah do vyhrazeneho pasu) ──
            #
            # Vada, kterou ze samotnych souradnic widgetu poznat nelze: scena
            # nese absolutni obdelniky, ne to, KDO je ciho rodic. Mereni vozi
            # most; bez nej pravidlo mlci. Gatovani je proto DATOVE, ne
            # profilove - oriznuty prvek je vada na kazdem panelu.
            # Pas se meri KAZDEMU viditelnemu prvku, i tomu, ktery vlastni
            # zaznam v bloku nema: pas je vlastnost SCENY. Rodic se meri jen
            # tomu, kdo ho ma zmereneho. Kdyby se cely R136 vazal na zaznam,
            # prvek bez mereni by patku prosel mlcky.
            if (
                (navrh_prvek or navrh_pasy)
                and w.get("visible") is not False
                and _is_int(x)
                and _is_int(y)
                and _is_int(ww)
                and _is_int(hh)
            ):
                issues.extend(
                    _r136_nalezy(wl, navrh_prvek, (x, y, ww, hh), (sw, sh), navrh_pasy)
                )

            # ── Rule 137: preteceni textu zmerenym fontem ──
            if navrh_prvek and w.get("visible") is not False:
                issues.extend(_r137_nalezy(wl, navrh_prvek, text))

            # ── Rule 144 + Rule 145: text useknuty svou schrankou ──
            #
            # Jina velicina nez Rule 137: ta meri DEKLAROVANOU bunku
            # (rozvrzeni), tahle dvojice SKUTECNY orez (co je videt). Bez
            # textu se nemeri - prazdna schranka nic neusekla a prazdny
            # smalt patri Rule 138.
            if navrh_prvek and text.strip() and w.get("visible") is not False:
                issues.extend(_r144_nalezy(wl, navrh_prvek, text))
                issues.extend(_r145_nalezy(wl, navrh_prvek, text))

            # ── Rule 146: cizi text na smaltove plose ──
            #
            # Gatovane PROFILEM (polarita je zakon TabOSu) i DATY (bez
            # `navrh.plochy` neni co merit).
            if (
                prof.polarita_smaltu
                and plochy_rects
                and text.strip()
                and isinstance(wid_navrh, str)
                and w.get("visible") is not False
            ):
                issues.extend(
                    _r146_nalezy(
                        wl,
                        wid_navrh,
                        (x, y, ww, hh),
                        text,
                        plochy_rects,
                        navrh_prvky,
                        zna_rodic_id,
                    )
                )

            # ── Rule 147: delici cara pres text ──
            if (
                prof.delici_cary
                and navrh_cary
                and text.strip()
                and w.get("visible") is not False
            ):
                issues.extend(_r147_nalezy(wl, (x, y, ww, hh), text, navrh_cary))

            # ── Rule 149: co z rezu udela oko na 450 mm ──
            #
            # Druha otazka nad tymz merenim (`prvky[*].font_size`) nez
            # Rule 148 vyse: 148 se pta, jestli rez patri do SKALY
            # (smlouva jazyka, datove gatovana), 149 jestli je z nej na
            # 450 mm jeste neco videt (fyzika, gatovana PROFILEM - tyz
            # rez je na jinem panelu jina velicina). Prvek pod skalou
            # i pod mezi ctenosti dostane oba nalezy pravem: opravit se
            # to da dvema ruznymi zpusoby. Rule 149 zustava po prvcich,
            # protoze mez je fyzikalni a hlaska ma rict, CO se neprecte.
            if navrh_prvek and w.get("visible") is not False:
                issues.extend(_r149_nalezy(wl, navrh_prvek, text, prof))

            # ── Rule 151: text nalepeny na ram ──
            #
            # Meri se KAZDEMU viditelnemu prvku s textem, i tomu, ktery
            # vlastni zaznam v bloku nema - tataz uvaha jako u pasu
            # v Rule 136: soustava odsazeni je vlastnost SCENY a leva
            # hrana je u kazdeho widgetu. Kdyby se pravidlo vazalo na
            # zaznam, prvek bez merenych dat by se nalepil na ram mlcky.
            # Zaznam rozhoduje jen o tom, jestli blok ma VLASTNI vsazku.
            if navrh_soustava and w.get("visible") is not False and _is_int(x):
                issues.extend(
                    _r151_nalezy(wl, navrh_prvek, int(x), text, navrh_soustava)
                )

            # ── Rule 138 + Rule 139: hodnotova role bez sdeleni ──
            #
            # Dve podoby teze vady, kterou koordinator nasel ocima na panelu:
            # smalt bez slova (Terminal PORT, Files VOLNO, USB "CO TO JE") a
            # pomlcka misto vety (LA "SPOUST —", patky "—"). Prazdny text meri
            # VYHRADNE Rule 138, neprazdny Rule 139 - jedna obet, jeden nalez.
            # Text, ktery neni retezec, patri Rule 91; obe pravidla proto na
            # necitelny text nesahaji.
            role = navrh_prvek.get("role")
            if role in ROLE_HODNOTY and isinstance(text_raw, str) and w.get("visible") is not False:
                uvnitr = (
                    None
                    if text.strip()
                    else _text_uvnitr(
                        idx,
                        str(wid_navrh),
                        (x, y, x + ww, y + hh),
                        (x, y, ww, hh),
                        texty_sceny,
                        navrh_prvky,
                        zna_rodic_id,
                    )
                )
                issues.extend(
                    _r138_nalezy(wl, str(wid_navrh), role, navrh_prvek, text, uvnitr)
                )
                issues.extend(_r139_nalezy(wl, text))

            # ── Rule 142: veta pro cloveka nese strojove jmeno ──
            #
            # Jedine z novych pravidel gatovane PROFILEM, ne daty: F4 je
            # jazykovy zakon TabOSu, ne vlastnost panelu. Meri se hotovy text
            # na plose, takze zadny format uz se nedosadi (viz `_V_PROCENTO`).
            if (
                prof.vety_pro_cloveka
                and druh_listu != "vyklad"
                and isinstance(text_raw, str)
                and w.get("visible") is not False
            ):
                issues.extend(_r142_nalezy(wl, text, navrh_jmena_sdk))

            # ── Rule 143: slovnik stavu teze veci ──
            #
            # Datove gatovane: bez slovniku a bez `vec` mlci. Bezi i mimo
            # hodnotovou roli? Ne - slib nese role (viz `_r143_nalezy`).
            if isinstance(text_raw, str) and w.get("visible") is not False:
                issues.extend(_r143_nalezy(wl, navrh_prvek, role, text, navrh_slovnik))

            # ── Rule 19: z_index is an integer ──
            z = w.get("z_index", 0)
            if not _is_int(z):
                issues.append(Issue("ERROR", f"{wl}: z_index={z!r} must be int"))

            # ── Rule 15: Foreground color parseable + visibility ──
            fg_str = w.get("color_fg", "")
            if fg_str:
                fg_rgb = _parse_color(fg_str)
                if fg_rgb is None:
                    issues.append(Issue("WARN", f"{wl}: can't parse color_fg '{fg_str}'"))
                elif wt in TEXT_TYPES and text and MIN_VISIBLE_BRIGHTNESS > 0:
                    # Only meaningful where the panel is emissive and text is
                    # always the BRIGHTER thing. On a light surface, dark ink is
                    # the correct design, not a defect — profiles that allow it
                    # set this threshold to 0 and rely on the ratio check below.
                    br = _brightness(fg_rgb)
                    if br < MIN_VISIBLE_BRIGHTNESS:
                        issues.append(Issue("WARN", f"{wl}: fg '{fg_str}' too dim ({br}) for text"))

            # ── Rule 16: Background color parseable ──
            bg_str = w.get("color_bg", "")
            if bg_str:
                bg_rgb = _parse_color(bg_str)
                if bg_rgb is None:
                    issues.append(Issue("WARN", f"{wl}: can't parse color_bg '{bg_str}'"))

            # ── Rule 17: Contrast check (fg vs bg for text widgets) ──
            #
            # MERI SE, CO OKO VIDI. Kdyz most vozi slozenou dvojici
            # (`inkoust`/`podklad`, tedy barvy uz s prusvitnosti a
            # `opacity`), plati ona; jinak zbyva DEKLAROVANA dvojice ze
            # sceny. Rozdil neni akademicky: zasedle tlacitko "Pripojit"
            # ma napsany inkoust #12150E (pomer 14,07:1), ale na skle je
            # z nej #946D2A (2,23:1) - a stara Rule 17 o vsech deviti
            # zasedlych ovladacich kitu mlcela.
            fg_videna = navrh_prvek.get("inkoust", fg_str)
            bg_videna = navrh_prvek.get("podklad", bg_str)
            if wt in TEXT_TYPES and text and fg_videna and bg_videna:
                fg_str, bg_str = fg_videna, bg_videna
                fg_rgb = _parse_color(fg_str)
                bg_rgb = _parse_color(bg_str)
                if fg_rgb and bg_rgb:
                    if prof.contrast_mode == "wcag":
                        # A brightness DELTA is not a legibility measure: the
                        # same delta reads very differently at the dark and the
                        # light end of the range. WCAG's ratio is gamma-correct
                        # and symmetric, so it judges dark-on-light the same way
                        # as light-on-dark.
                        ratio = _contrast_ratio(fg_rgb, bg_rgb)
                        # WCAG 2.1 AA ma DVE meze, ne jednu. Velky text
                        # (>= 24 px, nebo >= 19 px tucne) staci 3,0:1,
                        # protoze vetsi glyf sam nese cast citelnosti.
                        # Bez teto pulky dostava kazdy velky titulek mezi
                        # 3,0 a 4,5 falesny poplach - a brana, ktera krici
                        # vlka, prestane byt bran vazne. Rez i tucnost
                        # vozi most v bloku `navrh`; kdyz nedosly, plati
                        # prisnejsi mez (nezmerene se nesmi vyplatit).
                        mez = MIN_CONTRAST
                        if prof.min_contrast_velky:
                            rez_px = navrh_prvek.get("font_size")
                            tucne = bool(navrh_prvek.get("tucne"))
                            if rez_px is not None and (
                                float(rez_px) >= WCAG_VELKY_PX
                                or (tucne and float(rez_px) >= WCAG_TUCNE_PX)
                            ):
                                mez = prof.min_contrast_velky
                        if ratio < mez:
                            # WCAG 2.1, 1.4.3: neaktivni ovladac je z meze
                            # kontrastu VYNATY - zasedle tlacitko ma vypadat
                            # zasedle a je to sdeleni, ne vada. Ticho ale
                            # musi byt VIDET: hlasi se, ze vyjimka opravdu
                            # neco vyjmula, a jen tehdy (vyjimka, ktera nic
                            # nezmenila, by byla jen sum).
                            if navrh_prvek.get("enabled") is False:
                                issues.append(
                                    Issue(
                                        "WARN",
                                        f"{wl}: {ZNACKA_R17_NEAKTIVNI}: "
                                        f"{ratio:.2f}:1 < {mez}:1 "
                                        f"fg='{fg_str}' vs bg='{bg_str}' "
                                        f"(WCAG 2.1, 1.4.3 - mez na nej neplati)",
                                    )
                                )
                            else:
                                issues.append(
                                    Issue(
                                        "WARN",
                                        f"{wl}: low contrast ({ratio:.2f}:1 < "
                                        f"{mez}:1) fg='{fg_str}' vs bg='{bg_str}'",
                                    )
                                )
                    else:
                        contrast = abs(_brightness(fg_rgb) - _brightness(bg_rgb))
                        if contrast < MIN_CONTRAST:
                            issues.append(
                                Issue(
                                    "WARN",
                                    f"{wl}: low contrast ({contrast}) fg='{fg_str}' vs bg='{bg_str}'",
                                )
                            )

            # ── Rule 20: runtime string format ──
            if runtime:
                for part in runtime.split(";"):
                    part = part.strip()
                    if not part:
                        continue
                    if "=" not in part:
                        issues.append(Issue("ERROR", f"{wl}: runtime '{part}' missing '='"))
                        break

            # ── Rule 24: Edge margin (non-full-span widgets shouldn't touch edges) ──
            # Flush edge (x+w==sw) allowed for non-bordered widgets (e.g. topbar halves)
            flush_right = x + ww == sw
            flush_bottom = y + hh == sh
            # Right edge
            if (
                ww < sw
                and x > 0
                and x + ww > sw - MIN_EDGE_MARGIN
                and x + ww <= sw
                and (has_border or not flush_right)
            ):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{wl}: right edge too close to boundary ({x + ww} > {sw - MIN_EDGE_MARGIN})",
                    )
                )
            # Bottom edge
            if (
                hh < sh
                and y > 0
                and y + hh > sh - MIN_EDGE_MARGIN
                and y + hh <= sh
                and (has_border or not flush_bottom)
            ):
                issues.append(
                    Issue(
                        "ERROR",
                        f"{wl}: bottom edge too close to boundary ({y + hh} > {sh - MIN_EDGE_MARGIN})",
                    )
                )
            # Left edge (non-origin widgets too close to left)
            if ww < sw and x > 0 and x < MIN_EDGE_MARGIN:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{wl}: left edge too close to boundary (x={x} < {MIN_EDGE_MARGIN})",
                    )
                )
            # Top edge (non-origin widgets too close to top)
            if hh < sh and y > 0 and y < MIN_EDGE_MARGIN:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{wl}: top edge too close to boundary (y={y} < {MIN_EDGE_MARGIN})",
                    )
                )

            # ── Rule 25: Text widget with no text and no runtime binding ──
            if (
                wt in TEXT_TYPES
                and not text
                and not runtime
                and w.get("visible") is not False
                and w.get("enabled") is not False
                and not widget_id
            ):
                issues.append(Issue("WARN", f"{wl}: {wt} with no text and no runtime binding"))

            # ── Rule 26: Font charset compliance ──
            if wt in TEXT_TYPES and text:
                # font6x8 has no lowercase and maps it to uppercase; a font
                # that carries real lowercase must be compared as written.
                fold = "a" not in FONT_CHARS
                bad = [ch for ch in text if (ch.upper() if fold else ch) not in FONT_CHARS]
                if bad:
                    unique = "".join(sorted(set(bad)))
                    issues.append(Issue("WARN", f"{wl}: unsupported chars in text: {unique!r}"))

            # ── Rule 10: Firmware int16 overflow (value/min/max) ──
            for vf in ("value", "min_value", "max_value"):
                vv = w.get(vf)
                if _is_int(vv) and (vv < INT16_MIN or vv > INT16_MAX):
                    issues.append(
                        Issue("ERROR", f"{wl}: {vf}={vv} overflows int16 [{INT16_MIN},{INT16_MAX}]")
                    )

            # ── Rule 23: Style field validation ──
            if "style" in w:
                st = w.get("style")
                if not isinstance(st, str) or st.lower() not in ALLOWED_STYLES:
                    issues.append(Issue("ERROR", f"{wl}: invalid style '{st}'"))

            # ── Rule 27: Widget ID format ──
            if widget_id is not None and isinstance(widget_id, str) and widget_id:
                if not _WIDGET_ID_RE.match(widget_id):
                    issues.append(
                        Issue("ERROR", f"{wl}: id '{widget_id}' contains invalid characters")
                    )

            # ── Rule 28: Chart data_points validation ──
            if wt == "chart":
                dp = w.get("data_points")
                if dp is not None:
                    if not isinstance(dp, list):
                        issues.append(Issue("ERROR", f"{wl}: data_points must be a list"))
                    else:
                        bad_dp = [
                            v for v in dp if not isinstance(v, (int, float)) or isinstance(v, bool)
                        ]
                        if bad_dp:
                            issues.append(
                                Issue("ERROR", f"{wl}: data_points contains non-numeric values")
                            )

            # ── Rule 29: Icon widget requires icon_char ──
            if wt == "icon":
                ic = w.get("icon_char", "")
                if not ic:
                    issues.append(Issue("WARN", f"{wl}: icon widget has no icon_char"))

            # ── Rule 30: Checkbox/radiobutton minimum size ──
            if wt in ("checkbox", "radiobutton") and (ww < 10 or hh < 10):
                issues.append(Issue("WARN", f"{wl}: {wt} {ww}x{hh} too small (min 10x10)"))

            # ── Rule 31: Non-negative padding/margin ──
            for pm_key in ("padding_x", "padding_y", "margin_x", "margin_y"):
                pm_val = w.get(pm_key)
                if _is_int(pm_val) and pm_val < 0:
                    issues.append(Issue("ERROR", f"{wl}: {pm_key}={pm_val} must be >= 0"))

            # ── Rule 32: Value field type check ──
            if wt in VALUE_TYPES:
                for vf in ("value", "min_value", "max_value"):
                    vv = w.get(vf)
                    if vv is not None and not _is_int(vv):
                        issues.append(Issue("ERROR", f"{wl}: {vf}={vv!r} must be int"))

            # ── Rule 34: Slider minimum height ──
            if wt == "slider" and hh < MIN_TEXT_H:
                issues.append(Issue("WARN", f"{wl}: slider h={hh} too short (min {MIN_TEXT_H})"))

            # ── Rule 35: Double border minimum size ──
            if bstyle == "double" and (ww < 5 or hh < 5):
                issues.append(Issue("WARN", f"{wl}: double border needs >= 5x5, got {ww}x{hh}"))

            # ── Rule 37: Animations field must be a list ──
            if "animations" in w:
                anim = w.get("animations")
                if anim is not None and not isinstance(anim, list):
                    issues.append(Issue("ERROR", f"{wl}: animations must be a list"))
                elif isinstance(anim, list):
                    bad_items = [a for a in anim if not isinstance(a, str)]
                    if bad_items:
                        issues.append(Issue("ERROR", f"{wl}: animations contains non-string items"))

            # ── Rule 38: Geometry uint16 overflow ──
            for gf, gv in [("x", x), ("y", y), ("width", ww), ("height", hh)]:
                if gv > UINT16_MAX:
                    issues.append(
                        Issue("ERROR", f"{wl}: {gf}={gv} overflows uint16 (max {UINT16_MAX})")
                    )

            # ── Rule 39: Text length warning ──
            if wt in TEXT_TYPES and text and len(text) > MAX_TEXT_LEN:
                issues.append(
                    Issue("WARN", f"{wl}: text length {len(text)} exceeds {MAX_TEXT_LEN} chars")
                )

            # ── Rule 40: Runtime key validation ──
            if runtime:
                for part in runtime.split(";"):
                    part = part.strip()
                    if not part:
                        continue
                    if "=" in part:
                        key = part.split("=", 1)[0].strip()
                        if key and not _RUNTIME_KEY_RE.match(key):
                            issues.append(
                                Issue("WARN", f"{wl}: runtime key '{key}' has invalid format")
                            )

            # ── Rule 41: Completely invisible widget ──
            if x >= sw and y >= sh:
                issues.append(
                    Issue("WARN", f"{wl}: widget at ({x},{y}) fully outside scene {sw}x{sh}")
                )

            # ── Rule 42: Hidden widget with runtime binding ──
            if w.get("visible") is False and runtime and not widget_id:
                issues.append(
                    Issue("WARN", f"{wl}: widget is hidden (visible=false) but has runtime binding")
                )

            # ── Rule 43: locked field must be bool ──
            if "locked" in w and not _is_bool(w.get("locked")):
                issues.append(Issue("ERROR", f"{wl}: 'locked' must be boolean"))

            # ── Rule 44: state_overrides must be a dict of dicts ──
            if "state_overrides" in w:
                so = w.get("state_overrides")
                if so is not None and not isinstance(so, dict):
                    issues.append(Issue("ERROR", f"{wl}: state_overrides must be a dict"))
                elif isinstance(so, dict):
                    for sk, sv in so.items():
                        if not isinstance(sv, dict):
                            issues.append(
                                Issue("ERROR", f"{wl}: state_overrides['{sk}'] must be a dict")
                            )

            # ── Rule 45: Scene dimensions within uint16 ──
        if sw > UINT16_MAX or sh > UINT16_MAX:
            issues.append(
                Issue(
                    "ERROR", f"{pfx}: scene dimensions {sw}x{sh} overflow uint16 (max {UINT16_MAX})"
                )
            )

        # ── Per-widget rules that need full pass complete ──
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            ref = _wref(scene_name, w, idx)
            wl = f"{pfx}: {ref}"
            wtype = w.get("type")
            if not isinstance(wtype, str) or not wtype.strip():
                continue
            wt = wtype.lower()
            # x and y MUST be rebound here. They used to leak in from the last
            # widget of an earlier loop over the same list, so Rule 63 measured
            # this widget's size at another widget's position — a rectangle that
            # exists nowhere. It reported a fully on-screen 1192x592 frame as
            # "12% visible", and the percentage changed as unrelated widgets were
            # added. The same leak could equally keep it silent about a widget
            # that really is off-screen.
            x = w.get("x", 0)
            y = w.get("y", 0)
            if not (_is_int(x) and _is_int(y)):
                continue
            ww = w.get("width", 0)
            hh = w.get("height", 0)
            if not (_is_int(ww) and _is_int(hh)):
                continue

            # ── Rule 46: Textbox minimum size ──
            if wt == "textbox" and (ww < 20 or hh < MIN_TEXT_H):
                issues.append(
                    Issue("WARN", f"{wl}: textbox {ww}x{hh} too small (min 20x{MIN_TEXT_H})")
                )

            # ── Rule 47: Panel with content but no border or bg ──
            text_raw2 = w.get("text", "")
            text = str(text_raw2) if isinstance(text_raw2, str) else ""
            has_border = w.get("border", False)
            bg_str = w.get("color_bg", "")
            if wt == "panel" and not has_border and not bg_str:
                issues.append(Issue("WARN", f"{wl}: panel has no border and no background color"))

            # ── Rule 48: z_index range warning ──
            z = w.get("z_index", 0)
            if _is_int(z) and (z < -100 or z > 200):
                issues.append(
                    Issue("WARN", f"{wl}: z_index={z} is extreme (typical range -100..200)")
                )

            # ── Rule 49: Duplicate text in same scene (exact match warning) ──
            # (computed after per-widget loop, below)

            # ── Rule 50: icon_char length check ──
            ic = w.get("icon_char", "")
            if isinstance(ic, str) and len(ic) > 1:
                issues.append(Issue("WARN", f"{wl}: icon_char '{ic}' should be a single character"))

            # ── Rule 51: constraints must be a dict ──
            if "constraints" in w:
                ct = w.get("constraints")
                if ct is not None and not isinstance(ct, dict):
                    issues.append(Issue("ERROR", f"{wl}: constraints must be a dict"))

            # ── Rule 52: responsive_rules must be a list ──
            if "responsive_rules" in w:
                rr = w.get("responsive_rules")
                if rr is not None and not isinstance(rr, list):
                    issues.append(Issue("ERROR", f"{wl}: responsive_rules must be a list"))

            # ── Rule 53: REMOVED (dead rule) ──
            # `parent_id` is not part of WidgetConfig, the JSON schema, the
            # codegen, or the designer. The schema declares
            # `additionalProperties: false`, so a `parent_id` key can never
            # legally appear in a schema-valid design and this rule could
            # never fire. Widget parenting is not a supported feature; the
            # rule was misleading dead code and has been removed. If parenting
            # is ever added, reintroduce both the model field and a schema
            # property alongside any validation rule.

            # ── Rule 54: Center-aligned text in very narrow widget ──
            align = str(w.get("align", "left") or "left").lower()
            if wt in TEXT_TYPES and align == "center" and ww < CHAR_W * 3 + RENDER_PAD * 2:
                issues.append(Issue("WARN", f"{wl}: center-aligned in narrow widget (w={ww})"))

            # ── Rule 55: Widget ID max length ──
            wid = w.get("_widget_id") or w.get("id") or ""
            if isinstance(wid, str) and len(wid) > 64:
                issues.append(Issue("WARN", f"{wl}: widget ID length {len(wid)} exceeds 64 chars"))

            # ── Rule 56: data_points on non-chart widget ──
            if wt != "chart" and w.get("data_points"):
                issues.append(Issue("WARN", f"{wl}: data_points on non-chart widget '{wt}'"))

            # ── Rule 57: value fields on non-value widget ──
            if wt not in VALUE_TYPES and wt != "chart":
                for vf in ("min_value", "max_value"):
                    vv57 = w.get(vf)
                    # Ignore schema defaults commonly present on all widgets.
                    if vf == "min_value" and vv57 == 0:
                        continue
                    if vf == "max_value" and vv57 == 100 and w.get("min_value") == 0:
                        continue
                    if vf in w and vv57 != 0:
                        issues.append(Issue("WARN", f"{wl}: {vf} on non-value widget '{wt}'"))

            # ── Rule 58: Negative dimensions ──
            if ww < 0 or hh < 0:
                issues.append(Issue("ERROR", f"{wl}: negative dimension {ww}x{hh}"))

            # ── Rule 59: font_size must be positive int if present ──
            fs = w.get("font_size")
            if fs is not None:
                if not _is_int(fs) or fs < 1:
                    issues.append(Issue("ERROR", f"{wl}: font_size={fs!r} must be a positive int"))

            # ── Rule 60: corner_radius must be non-negative int if present ──
            cr = w.get("corner_radius")
            if cr is not None:
                if not _is_int(cr) or cr < 0:
                    issues.append(
                        Issue("ERROR", f"{wl}: corner_radius={cr!r} must be a non-negative int")
                    )

            # ── Rule 61: border_width must be non-negative int if present ──
            bw = w.get("border_width")
            if bw is not None:
                if not _is_int(bw) or bw < 0:
                    issues.append(
                        Issue("ERROR", f"{wl}: border_width={bw!r} must be a non-negative int")
                    )

            # ── Rule 62: border_color must be parseable if present ──
            bc = w.get("border_color", "")
            if bc:
                if _parse_color(str(bc)) is None:
                    issues.append(Issue("WARN", f"{wl}: can't parse border_color '{bc}'"))

            # ── Rule 63: Widget mostly outside scene (>75% area outside) ──
            if ww > 0 and hh > 0:
                vis_x1 = max(0, min(x, sw))
                vis_y1 = max(0, min(y, sh))
                vis_x2 = max(0, min(x + ww, sw))
                vis_y2 = max(0, min(y + hh, sh))
                vis_area = max(0, vis_x2 - vis_x1) * max(0, vis_y2 - vis_y1)
                total_area = ww * hh
                is_fully_offscreen = (x + ww <= 0) or (y + hh <= 0) or (x >= sw) or (y >= sh)
                if total_area > 0 and vis_area < total_area * 0.25 and not is_fully_offscreen:
                    pct = int(100 * vis_area / total_area)
                    issues.append(Issue("WARN", f"{wl}: only {pct}% visible inside scene bounds"))

            # ── Rule 64: bold field must be bool ──
            if "bold" in w and not _is_bool(w.get("bold")):
                issues.append(Issue("ERROR", f"{wl}: 'bold' must be boolean"))

            # ── Rule 67: theme_fg_role / theme_bg_role must be strings ──
            for role_key in ("theme_fg_role", "theme_bg_role"):
                rv = w.get(role_key)
                if rv is not None and not isinstance(rv, str):
                    issues.append(Issue("ERROR", f"{wl}: {role_key}={rv!r} must be a string"))

            # ── Rule 68: state field must be a string ──
            state_val = w.get("state")
            if state_val is not None and not isinstance(state_val, str):
                issues.append(Issue("ERROR", f"{wl}: state={state_val!r} must be a string"))

            # ── Rule 69: max_lines must be >= 1 when set ──
            ml = w.get("max_lines")
            if _is_int(ml) and ml == 0:
                issues.append(Issue("WARN", f"{wl}: max_lines=0 effectively hides all text"))

            # ── Rule 70: text_color / bg_color / color must be parseable if set ──
            for alias_key in ("text_color", "bg_color", "color"):
                alias_val = w.get(alias_key)
                if isinstance(alias_val, str) and alias_val.strip():
                    if _parse_color(alias_val) is None:
                        issues.append(
                            Issue("ERROR", f"{wl}: {alias_key}='{alias_val}' is not a valid color")
                        )

            # ── Rule 71: max_lines excessively large ──
            if _is_int(w.get("max_lines")) and w.get("max_lines") > 100:
                issues.append(
                    Issue("WARN", f"{wl}: max_lines={w.get('max_lines')} seems excessive (>100)")
                )

            # ── Rule 72: text widget with both static text and runtime binding ──
            _tv = w.get("text", "")
            text_val = str(_tv) if isinstance(_tv, str) else ""
            _rv = w.get("runtime", "")
            runtime_val = str(_rv) if isinstance(_rv, str) else ""
            if (
                wt in TEXT_TYPES
                and text_val.strip()
                and runtime_val.strip()
                and w.get("visible") is not False
            ):
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: has both text='{text_val}' and runtime='{runtime_val}' (runtime may override text)",
                    )
                )

            # ── Rule 73: icon widget too small for icon_char ──
            if wt == "icon" and (ww < CHAR_W or hh < CHAR_H):
                issues.append(
                    Issue("WARN", f"{wl}: icon {ww}x{hh} too small (min {CHAR_W}x{CHAR_H})")
                )

            # ── Rule 74: padding larger than widget interior ──
            px = w.get("padding_x")
            py = w.get("padding_y")
            if _is_int(px) and px * 2 >= ww:
                issues.append(Issue("WARN", f"{wl}: padding_x={px} fills entire width {ww}"))
            if _is_int(py) and py * 2 >= hh:
                issues.append(Issue("WARN", f"{wl}: padding_y={py} fills entire height {hh}"))

            # ── Rule 75: Chart minimum size ──
            if wt == "chart" and (ww < 20 or hh < 16):
                issues.append(Issue("WARN", f"{wl}: chart {ww}x{hh} too small (min 20x16)"))

            # ── Rule 76: border_width > 0 but border=False ──
            bw_val = w.get("border_width")
            if _is_int(bw_val) and bw_val > 0 and not w.get("border", False):
                issues.append(Issue("WARN", f"{wl}: border_width={bw_val} but border=false"))

            # ── Rule 77: text_overflow on non-text widget ──
            tof = w.get("text_overflow")
            if (
                isinstance(tof, str)
                and tof.lower() not in {"", "ellipsis"}
                and wt not in TEXT_TYPES
            ):
                issues.append(Issue("WARN", f"{wl}: text_overflow='{tof}' on non-text type '{wt}'"))

            # ── Rule 78: align on non-text widget ──
            walign = w.get("align")
            if (
                isinstance(walign, str)
                and walign.lower() not in {"", "left"}
                and wt not in TEXT_TYPES
            ):
                issues.append(Issue("WARN", f"{wl}: align='{walign}' on non-text type '{wt}'"))

            # ── Rule 79: widget larger than scene ──
            if ww > sw:
                issues.append(Issue("WARN", f"{wl}: width {ww} > scene width {sw}"))
            if hh > sh:
                issues.append(Issue("WARN", f"{wl}: height {hh} > scene height {sh}"))

            # ── Rule 80: margin pushes widget offscreen ──
            mx = w.get("margin_x")
            my = w.get("margin_y")
            if _is_int(mx) and mx > 0 and x + mx >= sw:
                issues.append(
                    Issue("WARN", f"{wl}: margin_x={mx} pushes widget past scene right edge")
                )
            if _is_int(my) and my > 0 and y + my >= sh:
                issues.append(
                    Issue("WARN", f"{wl}: margin_y={my} pushes widget past scene bottom edge")
                )

            # ── Rule 81: progressbar with text (not rendered) ──
            if wt == "progressbar" and text.strip():
                issues.append(Issue("WARN", f"{wl}: progressbar text='{text}' is not rendered"))

            # ── Rule 82: value fields on checkbox/radiobutton ──
            if wt in {"checkbox", "radiobutton"}:
                for vf in ("value", "min_value", "max_value"):
                    vv = w.get(vf)
                    if _is_int(vv) and vv != 0:
                        issues.append(
                            Issue("WARN", f"{wl}: {vf}={vv} on {wt} (not a value widget)")
                        )
                        break

            # ── Rule 83: checked on non-checkbox/radiobutton/toggle ──
            if wt not in {"checkbox", "radiobutton", "toggle"} and w.get("checked") is True:
                issues.append(
                    Issue("WARN", f"{wl}: checked=true on non-checkbox/radiobutton '{wt}'")
                )

            # ── Rule 84: icon_char on non-icon widget ──
            if wt != "icon" and w.get("icon_char", ""):
                issues.append(Issue("WARN", f"{wl}: icon_char set on non-icon widget '{wt}'"))

            # ── Rule 85: max_lines on non-text widget ──
            if wt not in TEXT_TYPES and w.get("max_lines") is not None:
                ml85 = w.get("max_lines")
                if _is_int(ml85) and ml85 > 0:
                    issues.append(
                        Issue("WARN", f"{wl}: max_lines={ml85} on non-text widget '{wt}'")
                    )

            # ── Rule 86: max_lines firmware uint8 overflow ──
            ml86 = w.get("max_lines")
            if _is_int(ml86) and ml86 > 255:
                issues.append(Issue("ERROR", f"{wl}: max_lines={ml86} overflows uint8 (max 255)"))

            # ── Rule 87: padding/margin must be int ──
            for pm_key in ("padding_x", "padding_y", "margin_x", "margin_y"):
                pm_val = w.get(pm_key)
                if pm_val is not None and not _is_int(pm_val):
                    issues.append(Issue("ERROR", f"{wl}: {pm_key}={pm_val!r} must be int"))

            # ── Rule 88: max_lines with non-wrap text_overflow ──
            tof88 = str(w.get("text_overflow", "") or "").lower()
            ml88 = w.get("max_lines")
            if (
                wt in TEXT_TYPES
                and _is_int(ml88)
                and ml88 > 1
                and tof88
                and tof88 not in {"wrap", "auto", "", "ellipsis"}
            ):
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: max_lines={ml88} but text_overflow='{tof88}' (max_lines may be ignored)",
                    )
                )

            # ── Rule 89: responsive_rules entries structure ──
            rr89 = w.get("responsive_rules")
            if isinstance(rr89, list):
                for ri, entry in enumerate(rr89):
                    if not isinstance(entry, dict):
                        issues.append(
                            Issue("ERROR", f"{wl}: responsive_rules[{ri}] must be a dict")
                        )
                    elif "condition" not in entry:
                        issues.append(
                            Issue("ERROR", f"{wl}: responsive_rules[{ri}] missing 'condition'")
                        )

            # ── Rule 90: chart data_points int16 overflow ──
            if wt == "chart":
                dp90 = w.get("data_points")
                if isinstance(dp90, list):
                    bad90 = [
                        v
                        for v in dp90
                        if isinstance(v, (int, float))
                        and not isinstance(v, bool)
                        and (int(v) < INT16_MIN or int(v) > INT16_MAX)
                    ]
                    if bad90:
                        issues.append(
                            Issue(
                                "ERROR",
                                f"{wl}: data_points values outside int16 range: {bad90[:3]}",
                            )
                        )

            # ── Rule 91: text field must be a string ──
            text_raw = w.get("text")
            if text_raw is not None and not isinstance(text_raw, str):
                issues.append(Issue("ERROR", f"{wl}: text={text_raw!r} must be a string"))

            # ── Rule 92: valign on non-text widget ──
            va92 = str(w.get("valign", "") or "").lower()
            if wt not in TEXT_TYPES and va92 and va92 not in {"middle", ""}:
                issues.append(Issue("WARN", f"{wl}: valign='{va92}' on non-text widget '{wt}'"))

            # ── Rule 93: chart-only style on non-chart widget ──
            st93 = str(w.get("style", "") or "").lower()
            if wt != "chart" and st93 in {"bar", "line"}:
                issues.append(
                    Issue("WARN", f"{wl}: style='{st93}' is chart-specific on non-chart '{wt}'")
                )

            # ── Rule 94: font_size firmware range ──
            fs94 = w.get("font_size")
            if _is_int(fs94) and fs94 > 255:
                issues.append(Issue("ERROR", f"{wl}: font_size={fs94} overflows uint8 (max 255)"))

            # ── Rule 95: runtime field must be a string ──
            rt95 = w.get("runtime")
            if rt95 is not None and not isinstance(rt95, str):
                issues.append(Issue("ERROR", f"{wl}: runtime={rt95!r} must be a string"))

            # ── Rule 96: state_overrides keys must be valid state names ──
            so96 = w.get("state_overrides")
            if isinstance(so96, dict):
                for sk in so96:
                    if not isinstance(sk, str) or not sk.strip():
                        issues.append(
                            Issue(
                                "ERROR",
                                f"{wl}: state_overrides key {sk!r} must be a non-empty string",
                            )
                        )

            # ── Rule 97: cross-scene duplicate widget IDs ──
            # (computed after all scenes processed — deferred below)

            # ── Rule 98: corner_radius exceeds half of min dimension ──
            cr98 = w.get("corner_radius")
            if _is_int(cr98) and cr98 > 0:
                half_min = min(ww, hh) // 2
                if cr98 > half_min:
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: corner_radius={cr98} exceeds half of min dimension ({half_min})",
                        )
                    )

            # ── Rule 99: border_width firmware uint8 overflow ──
            bw99 = w.get("border_width")
            if _is_int(bw99) and bw99 > 255:
                issues.append(
                    Issue("ERROR", f"{wl}: border_width={bw99} overflows uint8 (max 255)")
                )

            # ── Rule 100: corner_radius firmware uint8 overflow ──
            cr100 = w.get("corner_radius")
            if _is_int(cr100) and cr100 > 255:
                issues.append(
                    Issue("ERROR", f"{wl}: corner_radius={cr100} overflows uint8 (max 255)")
                )

            # ── Rule 101: chart data_points count limit ──
            if wt == "chart":
                # The limit was written as a bare 128 with "on 256px display" in
                # the message: half the OLED's width. On a 1280 px panel that is
                # simply false. Derived from the profile it stays 128 for the
                # OLED and becomes 640 for the Tab5.
                # Still not the sound test: sub-pixel really means more points
                # than the CHART is wide, not than the panel is. Four tests in
                # test_validate_rules_99_106.py pin the panel-based threshold
                # (a 60 px chart with 128 points is asserted clean), so that
                # correction is left as a separate decision.
                dp101 = w.get("data_points")
                limit101 = (prof.match_w // 2) or 128
                if isinstance(dp101, list) and len(dp101) > limit101:
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: data_points has {len(dp101)} entries "
                            f"(>{limit101}, sub-pixel on a {prof.match_w}px display)",
                        )
                    )

            # ── Rule 102: empty runtime binding value ──
            _rv102 = w.get("runtime", "")
            rt102 = str(_rv102) if isinstance(_rv102, str) else ""
            if rt102:
                for part102 in rt102.split(";"):
                    part102 = part102.strip()
                    if not part102:
                        continue
                    if "=" in part102:
                        _key102, val102 = part102.split("=", 1)
                        if not val102.strip():
                            issues.append(
                                Issue(
                                    "WARN", f"{wl}: runtime '{part102}' has empty value after '='"
                                )
                            )

            # ── Rule 103: chart with no data and no runtime ──
            if wt == "chart":
                dp103 = w.get("data_points")
                _rv103 = w.get("runtime", "")
                rt103 = str(_rv103) if isinstance(_rv103, str) else ""
                if (dp103 is None or (isinstance(dp103, list) and len(dp103) == 0)) and not rt103:
                    issues.append(
                        Issue("WARN", f"{wl}: chart has no data_points and no runtime binding")
                    )

            # ── Rule 104: animations list contains empty strings ──
            if "animations" in w:
                anim104 = w.get("animations")
                if isinstance(anim104, list):
                    empty_ct = sum(1 for a in anim104 if isinstance(a, str) and not a.strip())
                    if empty_ct:
                        issues.append(
                            Issue("WARN", f"{wl}: animations contains {empty_ct} empty string(s)")
                        )

            # ── Rule 107: text_overflow=wrap with max_lines=1 ──
            ov107 = str(w.get("text_overflow", "") or "").lower()
            ml107 = w.get("max_lines")
            if ov107 == "wrap" and _is_int(ml107) and ml107 == 1:
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: text_overflow='wrap' with max_lines=1 (wrap can never produce a second line)",
                    )
                )

            # ── Rule 108: slider with height > width ──
            if wt == "slider" and hh > ww:
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: slider height({hh}) > width({ww}); firmware renders horizontal track",
                    )
                )

            # ── Rule 109: disabled+checked toggle without runtime ──
            if wt in ("checkbox", "radiobutton", "toggle"):
                r109_en = w.get("enabled")
                r109_chk = w.get("checked")
                _rv109 = w.get("runtime", "")
                rt109 = str(_rv109) if isinstance(_rv109, str) else ""
                if r109_en is False and r109_chk is True and not rt109:
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: disabled checked={r109_chk} {wt} with no runtime (stuck state)",
                        )
                    )

            # ── Rule 110: widget ID structural issues (.., trailing .- ) ──
            wid110 = w.get("_widget_id") or w.get("id")
            if isinstance(wid110, str) and wid110:
                if ".." in wid110 or wid110.endswith(".") or wid110.endswith("-"):
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{wl}: id '{wid110}' has structural issue (consecutive dots, trailing dot/hyphen)",
                        )
                    )

            # ── Rule 111: border=false but border_style not none/empty ──
            r111_border = w.get("border")
            r111_bs = str(w.get("border_style", "") or "").lower()
            if r111_border is False and r111_bs and r111_bs not in {"none", "", "single"}:
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: border=false but border_style='{r111_bs}' (style is ignored)",
                    )
                )

            # ── Rule 112: both visible=false and enabled=false ──
            if w.get("visible") is False and w.get("enabled") is False:
                issues.append(
                    Issue("WARN", f"{wl}: both visible=false and enabled=false (redundant)")
                )

            # ── Rule 113: text_overflow=wrap but too short for 2 lines ──
            ov113 = str(w.get("text_overflow", "") or "").lower()
            if ov113 == "wrap" and hh < RENDER_PAD * 2 + CHAR_H * 2:
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: text_overflow='wrap' but height={hh} too short for 2 lines (need {RENDER_PAD * 2 + CHAR_H * 2})",
                    )
                )

            # ── Rule 114: align center/right on checkbox/radiobutton ──
            if wt in ("checkbox", "radiobutton"):
                al114 = str(w.get("align", "") or "").lower()
                if al114 in ("center", "right"):
                    issues.append(
                        Issue(
                            "WARN", f"{wl}: align='{al114}' on {wt} (indicator is fixed left-edge)"
                        )
                    )

            # ── Rule 116: chart min_value >= max_value ──
            if wt == "chart":
                r116_min = w.get("min_value", 0)
                r116_max = w.get("max_value", 100)
                if _is_int(r116_min) and _is_int(r116_max) and r116_min >= r116_max:
                    issues.append(
                        Issue("ERROR", f"{wl}: chart min_value={r116_min} >= max_value={r116_max}")
                    )

            # ── Rule 117: progressbar height too small for visible fill ──
            if wt == "progressbar" and hh <= 2:
                issues.append(
                    Issue(
                        "WARN",
                        f"{wl}: progressbar height={hh} too small for visible fill (need >2)",
                    )
                )

            # ── Rule 118: constraints dict unrecognized keys ──
            r118_con = w.get("constraints")
            if isinstance(r118_con, dict) and r118_con:
                r118_bad = sorted(set(r118_con.keys()) - ALLOWED_CONSTRAINT_KEYS)
                if r118_bad:
                    issues.append(
                        Issue("WARN", f"{wl}: constraints has unrecognized keys: {r118_bad}")
                    )

            # ── Rule 119: icon widget too small for bitmap rendering ──
            if wt == "icon" and w.get("icon_char"):
                if ww < 20 or hh < 20:
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: icon {ww}x{hh} too small for bitmap (min 20x20 with border)",
                        )
                    )

            # ── Rule 120: checkbox/radiobutton too narrow for label text ──
            if wt in ("checkbox", "radiobutton") and text and ww < 16:
                issues.append(
                    Issue("WARN", f"{wl}: {wt} width={ww} too narrow for label text (min 16)")
                )

            # ── Rule 121: value/chart widget has text but height < CHAR_H ──
            if wt in ("gauge", "progressbar", "slider", "chart") and text and hh < CHAR_H:
                issues.append(
                    Issue(
                        "WARN", f"{wl}: {wt} height={hh} too short to render text (need >={CHAR_H})"
                    )
                )

            # ── Rule 122: runtime meta key validation ──
            if runtime:
                for r122_part in runtime.split(";"):
                    r122_part = r122_part.strip()
                    if not r122_part or "=" not in r122_part:
                        continue
                    r122_key = r122_part.split("=", 1)[0].strip().lower()
                    if r122_key and r122_key not in ALLOWED_RUNTIME_META_KEYS:
                        issues.append(
                            Issue(
                                "WARN",
                                f"{wl}: runtime key '{r122_key}' is not a recognized meta key",
                            )
                        )

            # ── Rule 124: runtime 'kind' value must be valid ──
            if runtime:
                r124_meta = _parse_runtime_meta(runtime)
                r124_kind = r124_meta.get("kind") or r124_meta.get("type")
                if r124_kind and r124_kind.lower() not in ALLOWED_RUNTIME_KINDS:
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{wl}: runtime kind '{r124_kind}' is not valid"
                            f" (expected {', '.join(sorted(ALLOWED_RUNTIME_KINDS))})",
                        )
                    )

            # ── Rule 125: runtime with meta keys but no bind/key ──
            if runtime:
                r125_meta = _parse_runtime_meta(runtime)
                r125_has_bind = "bind" in r125_meta or "key" in r125_meta
                r125_other = {k for k in r125_meta if k not in ("bind", "key")}
                if r125_other and not r125_has_bind:
                    issues.append(
                        Issue(
                            "WARN",
                            f"{wl}: runtime has meta keys ({', '.join(sorted(r125_other))})"
                            " but no 'bind' or 'key'",
                        )
                    )

            # ── Rule 126: duplicate keys in runtime string ──
            if runtime:
                r126_seen: dict[str, int] = {}
                for r126_part in runtime.split(";"):
                    r126_part = r126_part.strip()
                    if not r126_part or "=" not in r126_part:
                        continue
                    r126_k = r126_part.split("=", 1)[0].strip().lower()
                    if r126_k in r126_seen:
                        issues.append(
                            Issue(
                                "ERROR",
                                f"{wl}: runtime has duplicate key '{r126_k}'",
                            )
                        )
                    else:
                        r126_seen[r126_k] = 1

            # ── Rule 127: numeric runtime values must parse as numbers ──
            if runtime:
                r127_meta = _parse_runtime_meta(runtime)
                for r127_k in NUMERIC_RUNTIME_KEYS:
                    r127_v = r127_meta.get(r127_k)
                    if r127_v is not None:
                        try:
                            float(r127_v)
                        except ValueError:
                            issues.append(
                                Issue(
                                    "ERROR",
                                    f"{wl}: runtime '{r127_k}={r127_v}' is not a valid number",
                                )
                            )

            # ── Rule 128: bind value must be a valid identifier ──
            if runtime:
                r128_meta = _parse_runtime_meta(runtime)
                r128_bind = r128_meta.get("bind") or r128_meta.get("key")
                if r128_bind and not _RUNTIME_KEY_RE.match(r128_bind):
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{wl}: runtime bind value '{r128_bind}' is not a valid identifier",
                        )
                    )

            # ── Rule 130: LIST items must be a list of strings ──
            r130_items = w.get("items")
            if wt == "list" and r130_items is not None:
                if not isinstance(r130_items, list):
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{wl}: items field must be a list, got {type(r130_items).__name__}",
                        )
                    )
                else:
                    for r130_i, r130_v in enumerate(r130_items):
                        if not isinstance(r130_v, str):
                            issues.append(
                                Issue(
                                    "ERROR",
                                    f"{wl}: items[{r130_i}] must be a string,"
                                    f" got {type(r130_v).__name__}",
                                )
                            )
                            break

            # ── Rule 131: LIST with no text and no items ──
            if wt == "list" and not text and not r130_items:
                issues.append(Issue("WARN", f"{wl}: list widget has no text and no items"))

            # ── Rule 132: items on non-list widget ──
            if wt != "list" and w.get("items") is not None:
                r132_items = w.get("items")
                if isinstance(r132_items, list) and len(r132_items) > 0:
                    issues.append(
                        Issue("WARN", f"{wl}: items field on non-list widget '{wt}' (ignored)")
                    )

            # ── Rule 106: scene dimensions too small ──
            # (checked once per scene, outside per-widget loop — see below)

        # ── Rule 115: scene has no focusable widgets ──
        has_focusable = False
        for r115_w in widgets:
            if not isinstance(r115_w, dict):
                continue
            r115_t = str(r115_w.get("type", "") or "").lower()
            if (
                r115_t in FOCUSABLE_TYPES
                and r115_w.get("visible") is not False
                and r115_w.get("enabled") is not False
            ):
                has_focusable = True
                break
        if not has_focusable and len(widgets) > 0:
            issues.append(
                Issue("WARN", f"{pfx}: scene has no focusable widgets (navigation dead-end)")
            )

        # ── Rule 105: overlapping widgets with identical z_index ──
        if len(widgets) <= HARD_WIDGET_LIMIT:
            for i in range(len(widgets)):
                a = widgets[i]
                if not isinstance(a, dict):
                    continue
                ax, ay = a.get("x", 0), a.get("y", 0)
                aw, ah = a.get("width", 0), a.get("height", 0)
                az = a.get("z_index", 0)
                if not (_is_int(ax) and _is_int(ay) and _is_int(aw) and _is_int(ah)):
                    continue
                ax2, ay2 = ax + aw, ay + ah
                for j in range(i + 1, len(widgets)):
                    b = widgets[j]
                    if not isinstance(b, dict):
                        continue
                    bx, by = b.get("x", 0), b.get("y", 0)
                    bw, bh = b.get("width", 0), b.get("height", 0)
                    bz = b.get("z_index", 0)
                    if not (_is_int(bx) and _is_int(by) and _is_int(bw) and _is_int(bh)):
                        continue
                    bx2, by2 = bx + bw, by + bh
                    if ax < bx2 and ax2 > bx and ay < by2 and ay2 > by:
                        if _is_int(az) and _is_int(bz) and az == bz:
                            ref_a = _wref(scene_name, a, i)
                            ref_b = _wref(scene_name, b, j)
                            if _overlap_is_benign(a, b, (ax, ay, ax2, ay2), (bx, by, bx2, by2)):
                                # Same-z_index is the norm here (draw-order
                                # compositing, all widgets z=0); a hidden
                                # overlay or container-behind-content pair is
                                # intentional, not ambiguous. Plain WARN, not a
                                # critical marker.
                                issues.append(
                                    Issue(
                                        "WARN",
                                        f"{pfx}: OVERLAP (intentional layering) "
                                        f"same z_index={az}: {ref_a} <> {ref_b}",
                                    )
                                )
                            else:
                                # Two visible non-container widgets collide with
                                # identical z_index → genuinely ambiguous draw
                                # order. Critical marker.
                                issues.append(
                                    Issue(
                                        "WARN",
                                        f"{pfx}: OVERLAP (visible content collision) "
                                        f"same z_index={az}: {ref_a} <> {ref_b}",
                                    )
                                )

        # ── Rule 106: scene dimensions too small ──
        if sw < 8 or sh < 8:
            issues.append(Issue("WARN", f"{pfx}: scene dimensions {sw}x{sh} too small (min 8x8)"))

        # ── Rule 65: Duplicate geometry (same x,y,w,h = likely copy-paste) ──
        geo_map: dict[tuple[int, int, int, int], list[int]] = {}
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            gx, gy, gw, gh = w.get("x"), w.get("y"), w.get("width"), w.get("height")
            if _is_int(gx) and _is_int(gy) and _is_int(gw) and _is_int(gh):
                geo_key = (int(gx), int(gy), int(gw), int(gh))
                geo_map.setdefault(geo_key, []).append(idx)
        for geo, indices in geo_map.items():
            if len(indices) >= 2:
                refs = ", ".join(str(i) for i in indices)
                issues.append(
                    Issue("WARN", f"{pfx}: widgets [{refs}] share identical geometry {geo}")
                )

        # ── Rule 66: Disabled widget with no runtime (may be unreachable) ──
        for idx, w in enumerate(widgets):
            if not isinstance(w, dict):
                continue
            if w.get("enabled") is False and w.get("visible") is not False and w.get("text"):
                _rv66 = w.get("runtime", "")
                runtime_val = str(_rv66) if isinstance(_rv66, str) else ""
                if not runtime_val:
                    ref = _wref(scene_name, w, idx)
                    wl = f"{pfx}: {ref}"
                    issues.append(
                        Issue("WARN", f"{wl}: disabled (enabled=false) with no runtime binding")
                    )

        # ── Rule 49: Large number of identical non-empty text strings ──
        text_counts: dict[str, int] = {}
        for w in widgets:
            if not isinstance(w, dict):
                continue
            _t49 = w.get("text", "")
            t = str(_t49) if isinstance(_t49, str) else ""
            if t and len(t) > 3:
                text_counts[t] = text_counts.get(t, 0) + 1
        for t, count in text_counts.items():
            if count >= 4:
                issues.append(
                    Issue(
                        "WARN",
                        f"{pfx}: text '{t}' appears {count} times (consider runtime binding)",
                    )
                )

        # ── Rule 33: Excessive widget count per scene ──
        if len(widgets) > HARD_WIDGET_LIMIT:
            issues.append(
                Issue(
                    "ERROR",
                    f"{pfx}: {len(widgets)} widgets exceeds hard limit {HARD_WIDGET_LIMIT}",
                )
            )
        elif len(widgets) > MAX_WIDGETS_PER_SCENE:
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: {len(widgets)} widgets exceeds recommended max {MAX_WIDGETS_PER_SCENE}",
                )
            )

        # ── Rule 133: say so when collision detection was skipped ──
        #
        # Rule 21 is O(n^2) and gives up above the hard limit. Until now it did
        # that in SILENCE, so an over-budget scene came back with "no collisions"
        # when the truth was "not looked at". A filter that hides a real defect
        # is worse than no gauge at all, and this one hid the check itself.
        if len(widgets) > HARD_WIDGET_LIMIT:
            issues.append(
                Issue(
                    "WARN",
                    f"{pfx}: collision detection SKIPPED ({len(widgets)} widgets "
                    f"> {HARD_WIDGET_LIMIT}); this scene is unchecked for overlaps",
                )
            )

        # ── Rule 21: Overlap detection (skip if widget count exceeds hard limit) ──
        if len(widgets) <= HARD_WIDGET_LIMIT:
            for i in range(len(widgets)):
                a = widgets[i]
                if not isinstance(a, dict):
                    continue
                ax, ay = a.get("x", 0), a.get("y", 0)
                aw, ah = a.get("width", 0), a.get("height", 0)
                if not (_is_int(ax) and _is_int(ay) and _is_int(aw) and _is_int(ah)):
                    continue
                ax2, ay2 = ax + aw, ay + ah
                for j in range(i + 1, len(widgets)):
                    b = widgets[j]
                    if not isinstance(b, dict):
                        continue
                    bx, by = b.get("x", 0), b.get("y", 0)
                    bw, bh = b.get("width", 0), b.get("height", 0)
                    if not (_is_int(bx) and _is_int(by) and _is_int(bw) and _is_int(bh)):
                        continue
                    bx2, by2 = bx + bw, by + bh
                    if ax < bx2 and ax2 > bx and ay < by2 and ay2 > by:
                        ref_a = _wref(scene_name, a, i)
                        ref_b = _wref(scene_name, b, j)
                        if _overlap_is_benign(a, b, (ax, ay, ax2, ay2), (bx, by, bx2, by2)):
                            # Intentional layering (hidden overlay or container
                            # backdrop fully behind its content). Surfaced as a
                            # plain WARN for visibility; deliberately NOT a
                            # critical marker, so --strict-critical does not
                            # fail a correct-by-design scene.
                            issues.append(
                                Issue(
                                    "WARN",
                                    f"{pfx}: OVERLAP (intentional layering) {ref_a} <> {ref_b}",
                                )
                            )
                        else:
                            # Two visible, mutually non-containing widgets
                            # collide: a genuine layout defect. Critical marker
                            # → fails under --strict-critical.
                            issues.append(
                                Issue(
                                    "WARN",
                                    f"{pfx}: OVERLAP (visible content collision) "
                                    f"{ref_a} <> {ref_b}",
                                )
                            )

        # ── Rule 134: near-miss alignment (a coordinate typo, not a choice) ──
        #
        # Two edges 1-3 px apart are never a design decision — nobody indents by
        # two pixels on purpose. It is a typed coordinate that missed. The eye
        # cannot catch it because the two elements are usually far apart on the
        # screen, so this is precisely the class a gauge has to carry.
        # Only VISIBLE TEXT edges are compared: panels and rules legitimately
        # sit a pixel off a text edge to form a frame around it.
        # LEFT EDGES ONLY. The vertical variant is gone, and deliberately:
        # every single time it fired — in two different codebases — the rows
        # sat on the SAME coordinate and the "miss" was an artifact of where
        # the extreme points of the glyphs happened to land (baselines shared
        # by different type sizes; accents reaching higher than cap height in
        # ink-measured geometry). Left edges carry no such effect, and the one
        # real defect this rule ever caught (x=78 vs 80) was horizontal. The
        # real vertical defects seen in review (a button 10 px low, mixed
        # heights in one row) are either above this threshold or split into
        # different height buckets — the vertical variant cannot catch them.
        NEAR_MISS_PX = 3
        for axis, key in (("left", "x"),):
            buckets: dict[Any, dict[int, str]] = {}
            for w in widgets:
                if not isinstance(w, dict):
                    continue
                if w.get("visible") is False or w.get("type") not in TEXT_TYPES:
                    continue
                if not str(w.get("text", "")).strip():
                    continue
                v = w.get(key)
                if not _is_int(v):
                    continue
                # The left BOX edge is where the text starts only when the text
                # is left-aligned. Centred or right-aligned runs sit at an
                # offset that depends on the box width, so two boxes sharing a
                # centre but differing in width look like a 2 px miss and are
                # not one.
                if key == "x" and str(w.get("align", "left")).lower() != "left":
                    continue
                if key == "y":
                    h = w.get("height")
                    if not _is_int(h):  # malformed height must not crash the run
                        continue
                    bucket = h
                else:
                    bucket = None
                buckets.setdefault(bucket, {}).setdefault(v, str(w.get("text", ""))[:24])
            for edges in buckets.values():
                ordered = sorted(edges)
                for a, b in itertools.pairwise(ordered):
                    if 0 < b - a <= NEAR_MISS_PX:
                        issues.append(
                            Issue(
                                "WARN",
                                f"{pfx}: near-miss alignment: {axis} edges {a} and {b} "
                                f"differ by {b - a}px "
                                f"({edges[a]!r} vs {edges[b]!r})",
                            )
                        )

        # ── Rule 123: Min gap between non-grouped widgets ──
        if len(widgets) <= HARD_WIDGET_LIMIT:
            for i in range(len(widgets)):
                a = widgets[i]
                if not isinstance(a, dict):
                    continue
                ax, ay = a.get("x", 0), a.get("y", 0)
                aw, ah = a.get("width", 0), a.get("height", 0)
                if not (_is_int(ax) and _is_int(ay) and _is_int(aw) and _is_int(ah)):
                    continue
                ax2, ay2 = ax + aw, ay + ah
                ga = _widget_group(a)
                for j in range(i + 1, len(widgets)):
                    b = widgets[j]
                    if not isinstance(b, dict):
                        continue
                    # Skip widgets in the same group (shared ID prefix)
                    if ga and ga == _widget_group(b):
                        continue
                    bx, by = b.get("x", 0), b.get("y", 0)
                    bw, bh = b.get("width", 0), b.get("height", 0)
                    if not (_is_int(bx) and _is_int(by) and _is_int(bw) and _is_int(bh)):
                        continue
                    bx2, by2 = bx + bw, by + bh
                    # Compute axis-aligned gap between bounding boxes
                    x_gap = max(0, max(ax, bx) - min(ax2, bx2))
                    y_gap = max(0, max(ay, by) - min(ay2, by2))
                    # Only flag when rects share a band on the perpendicular axis
                    too_close = False
                    if (x_gap == 0 and 0 < y_gap < MIN_WIDGET_GAP_PX) or (
                        y_gap == 0 and 0 < x_gap < MIN_WIDGET_GAP_PX
                    ):
                        too_close = True
                    if too_close:
                        ref_a = _wref(scene_name, a, i)
                        ref_b = _wref(scene_name, b, j)
                        gap = min(g for g in (x_gap, y_gap) if g > 0)
                        issues.append(
                            Issue(
                                "WARN",
                                f"{pfx}: widgets too close ({gap}px < {MIN_WIDGET_GAP_PX}px min gap) "
                                f"{ref_a} <> {ref_b}",
                            )
                        )

    # ── Rule 97: Cross-scene duplicate widget IDs ──
    global_ids: dict[str, str] = {}  # id → first scene name
    for scene_name, scene in scenes.items():
        widgets = scene.get("widgets") or []
        for w in widgets:
            if not isinstance(w, dict):
                continue
            wid = w.get("_widget_id") or w.get("id")
            if not isinstance(wid, str) or not wid:
                continue
            if wid in global_ids and global_ids[wid] != scene_name:
                issues.append(
                    Issue(
                        "WARN",
                        f"{file_label}: widget id '{wid}' appears in both '{global_ids[wid]}' and '{scene_name}'",
                    )
                )
            else:
                global_ids[wid] = scene_name

    # ── Rule 129: Cross-scene bind key kind consistency ──
    bind_kinds: dict[str, tuple[str, str]] = {}  # bind_key → (kind, first_scene)
    for scene_name, scene in scenes.items():
        widgets = scene.get("widgets") or []
        for w in widgets:
            if not isinstance(w, dict):
                continue
            rt = w.get("runtime")
            if not isinstance(rt, str) or not rt:
                continue
            meta = _parse_runtime_meta(rt)
            bk = meta.get("bind") or meta.get("key")
            kd = meta.get("kind") or meta.get("type")
            if not bk or not kd:
                continue
            kd_lower = kd.lower()
            if bk in bind_kinds:
                prev_kind, prev_scene = bind_kinds[bk]
                if prev_kind != kd_lower:
                    issues.append(
                        Issue(
                            "ERROR",
                            f"{file_label}: bind '{bk}' has kind '{kd_lower}' in '{scene_name}'"
                            f" but '{prev_kind}' in '{prev_scene}'",
                        )
                    )
            else:
                bind_kinds[bk] = (kd_lower, scene_name)

    # ── Rule 130: Visual-backend events / rules validation ──
    issues.extend(_validate_logic(data, scenes, file_label))

    if warnings_as_errors:
        return [Issue("ERROR", i.message) if i.level == "WARN" else i for i in issues]
    if strict_critical:
        return [
            Issue("ERROR", i.message)
            if i.level == "WARN" and _is_critical_warning(i.message)
            else i
            for i in issues
        ]
    return issues


def validate_file(
    path: Path, *, warnings_as_errors: bool, strict_critical: bool = False
) -> list[Issue]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Issue("ERROR", f"{path}: failed to read file ({exc})")]
    if len(raw) > MAX_JSON_FILE_SIZE:
        return [
            Issue(
                "ERROR", f"{path}: file exceeds {MAX_JSON_FILE_SIZE // (1024 * 1024)}MB size limit"
            )
        ]
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return [Issue("ERROR", f"{path}: failed to parse JSON ({exc})")]
    if not isinstance(data, dict):
        return [Issue("ERROR", f"{path}: root must be a JSON object")]

    issues: list[Issue] = []

    # ── JSON Schema structural validation (MANDATORY) ──
    # This validator gates codegen / demo generation / visual verification /
    # PlatformIO builds. Schema enforcement must never be silently optional:
    # a missing dependency or schema file is a hard, actionable ERROR — not a
    # silent pass and not a soft warning. `jsonschema` is a declared runtime
    # dependency (see requirements.txt); installing it is the fix, never
    # suppressing this check.
    try:
        import jsonschema
    except ImportError:
        issues.append(
            Issue(
                "ERROR",
                f"{path}: schema validation unavailable — the 'jsonschema' package is "
                "not installed. It is a required runtime dependency; install it with "
                "'pip install -r requirements.txt' (or 'pip install jsonschema'). "
                "Schema validation is mandatory and will not be skipped.",
            )
        )
    else:
        if not SCHEMA_PATH.exists():
            issues.append(
                Issue(
                    "ERROR",
                    f"{path}: schema file missing at {SCHEMA_PATH} — cannot perform "
                    "mandatory structural validation.",
                )
            )
        else:
            try:
                schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
                validator = jsonschema.Draft202012Validator(schema)
            except (OSError, ValueError) as exc:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{path}: schema file at {SCHEMA_PATH} could not be loaded "
                        f"({exc}); structural validation cannot run.",
                    )
                )
            else:
                for error in validator.iter_errors(data):
                    loc = ".".join(str(p) for p in error.absolute_path) or "(root)"
                    issues.append(Issue("ERROR", f"{path}: schema: {loc}: {error.message}"))

    issues.extend(
        validate_data(
            data,
            file_label=str(path),
            warnings_as_errors=warnings_as_errors,
            strict_critical=strict_critical,
        )
    )
    return issues


def main() -> int:
    p = argparse.ArgumentParser(description="Validate ESP32OS UI design JSON")
    p.add_argument("json", type=Path, help="Input design JSON")
    p.add_argument("--warnings-as-errors", action="store_true", help="Treat warnings as errors")
    p.add_argument(
        "--strict-critical",
        action="store_true",
        help="Treat critical layout/readability warnings as errors",
    )
    args = p.parse_args()

    if not str(args.json).strip():
        p.error("json path cannot be empty or whitespace-only")

    issues = validate_file(
        args.json,
        warnings_as_errors=args.warnings_as_errors,
        strict_critical=args.strict_critical,
    )
    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    for i in issues:
        print(f"[{i.level}] {i.message}")

    if errors:
        print(f"[FAIL] {len(errors)} error(s), {len(warns)} warning(s)")
        return 1
    if warns:
        print(f"[WARN] {len(warns)} warning(s)")
    else:
        print("[OK] Design looks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
