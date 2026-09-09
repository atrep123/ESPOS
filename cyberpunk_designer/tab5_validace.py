"""Validace sceny artboardu TabOSu primo v editoru (profil tab5).

Editor dosud validator nezapojoval vubec: `io_ops.validate_design` dela jen
JSON-schema. Tenhle modul je ADAPTER nad `tools.validate_design.validate_data`,
tedy nad tymtez merilem, kterym meri brana `navrh-appky/do_espos.py`.

Ctyri veci, kvuli kterym to neni jen "zavolat funkci":

1. **`Issue` nese jen `level` a `message`** (`tools/validate_design.py`,
   dataclass `Issue`). Odkaz na widget je slepeny do textu funkci `_wref()`
   do tvaru `scene 'main': widget[15] (ovl_hlavni.15)`. Aby se dal nalez
   obarvit na platne, musi se index z textu VYTAHNOUT - a u pravidel typu
   OVERLAP jsou v jedne zprave indexy DVA.
2. **Deduplikace.** Tutez viditelnou kolizi hlasi vic pravidel; `do_espos.py`
   je sraz na jednu podle klice `re.sub(r"^.*?(OVERLAP|widget\\[)", "", ...)`.
   Bez tehoz kroku by editor napocital jina cisla nez brana a nedaly by se
   porovnat. Klic i predrazeny orez prefixu jsou proto DOSLOVNE stejne.
3. **Tridy se neprejmenovavaji ani nepridavaji.** `TRIDY` nize je kopie
   `do_espos.TRIDY` (do_espos lezi v jinem strome, `tabos-ui-kit`, ktery
   ESPOS pri testech nemusi mit). Shodu hlida test pres `tridy_z_do_espos()`,
   ktera seznam prectete STATICKY pres `ast` - nikdy importem.
   Zadna nova trida "ignorovat" tu neni a byt nesmi: filtr, ktery schova
   skutecnou vadu, je horsi nez zadne meridlo.
4. **`device` musi byt v dokumentu.** Bez nej spadne validator na profil
   OLED 256x128, dotykove meze zmizi a znakova sada plati jina - a nic to
   nenahlasi. Dokument se proto stavi tady, ne pres `save_to_json`.
5. **JSON-schema se pousti taky.** Brana vola validator jako CLI, tedy
   `validate_file`, ktere PRED `validate_data` pousti POVINNOU schema
   validaci (`tools/validate_design.py`: "Schema enforcement must never be
   silently optional"). Adapter volal jen `validate_data` a dva doklady
   ukazaly, ze se cesty rozchazeji: `groups` jako seznam misto slovniku
   a klic navic u widgetu (`additionalProperties: false`) byly pro branu
   ERROR a pro editor nic. Tady se proto schema pousti tymz zpusobem
   a se stejne znejicimi zpravami - jinak by editor pustil dal to, co
   brana zastavi.
6. **Kdyz se NEZMERILO, brana zastavuje.** `brana_ulozeni` drive pri vyjimce
   vratila `None`, coz znamena "nic nebrani" - tedy fail-open. Rozbite
   meridlo se pak nedalo rozeznat od cisteho navrhu. Ted je to naopak:
   jakekoli selhani mereni je duvod nevydat.

Ramecky na platne se kresli pro vsechny tridy krome `vrstveni`. To NENI
potlaceni: `vrstveni` je "OVERLAP (intentional layering)", tedy trida, kterou
uz `do_espos.py` vedome oddeluje (panel za svym obsahem), je jich pres dva
tisice a na cistem artboardu SvorkaLA je to VSECH 34 nalezu. Kdyby se
kreslila, byl by zluty cely navrh a skutecna vada by v tom zapadla. V panelu
nalezu se pritom pocita a zobrazuje jako kazda jina, a `app.tab5_ramecky_vse`
ji do ramecku zapne.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

from .tab5_most import DEVICE_TAB5, PROFIL_TAB5, _widget_na_slovnik

logger = logging.getLogger(__name__)

# Kopie `navrh-appky/do_espos.py` -> TRIDY. Poradi je vyznamne: trida se urcuje
# PRVNIM vzorem, ktery ve zprave sedi ("kolize" musi predchazet "vrstveni").
TRIDY: Tuple[Tuple[str, str], ...] = (
    ("kolize", "visible content collision"),
    ("vrstveni", "OVERLAP (intentional layering)"),
    ("dotyk", "touch target"),
    ("znaky", "unsupported chars"),
    ("zarovnani", "near-miss alignment"),
    ("neprovereno", "collision detection SKIPPED"),
    ("kontrast", "low contrast"),
    ("mimo list", "visible inside scene"),
    ("u kraje", "too close to boundary"),
    ("maly", "too short"),
    ("nevejde", "cannot fit"),
    ("ovladani", "focusable"),
    ("pocet", "exceeds recommended"),
    ("dvojnik", "share identical geometry"),
    ("opakovany text", "consider runtime binding"),
    # Trida doplnena 2026-09-09. Do te doby padal nalez do "netrideno":
    # jde o Rule 26 (delka textu proti profilu) a objevil se az potom, co
    # most prestal preskakovat vnorene znacky - drive se ten text do sceny
    # vubec nedostal (kritik: 181 ztracenych textu na 17 listech).
    ("delka textu", "overflows max"),
)

NETRIDENO = "netrideno"

# Trida, ktera znamena, ze se NEMERILO (pravidlo 133 - preskocena detekce
# kolizi pri prekroceni tvrdeho limitu widgetu). Musi byt videt vyrazneji nez
# ostatni, protoze prazdny seznam pod ni neznamena "je to v poradku".
TRIDY_POZOR = ("neprovereno",)

# Tridy bez ramecku na platne - viz docstring modulu. Pocitaji se dal.
TRIDY_BEZ_RAMECKU = ("vrstveni",)

BARVA_ERROR = (220, 70, 60)
BARVA_WARN = (215, 175, 60)

# Validace cele sceny artboardu (41 widgetu) trva ~1,4 ms, takze debounce tu
# neni kvuli vykonu, ale kvuli poctivosti: pri davce pusteni za sebou se
# nevalidnuje kazde z nich a stavajici vysledek se OZNACI jako neaktualni
# (`ceka`), aby panel netvrdil, ze meri to, co je na platne ted.
DEBOUNCE_S = 0.15

# Duvod, ktery brana vraci, kdyz se NEZMERILO. Musi byt rozeznatelny od
# "zmerilo se a naslo se X ERRORu" - jsou to ruzne stavy a jen jeden z nich
# se da opravit v navrhu.
DUVOD_NEZMERENO = "NEZMERENO - nevydavam"

_PREFIX_RE = re.compile(r"^.*?(scene '[^']*': |main: )")
_KLIC_RE = re.compile(r"^.*?(OVERLAP|widget\[)")
_INDEX_RE = re.compile(r"widget\[(\d+)\]")


# --------------------------------------------------------------------------- #
# Nalez a vysledek
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Nalez:
    """Jeden nalez validatoru prelozeny do neceho, co jde nakreslit."""

    uroven: str  # "ERROR" | "WARN"
    trida: str
    zprava: str  # bez prefixu souboru a sceny, jako v do_espos.py
    indexy: Tuple[int, ...] = ()
    puvodni: str = ""

    @property
    def pozor(self) -> bool:
        """Nalez, ktery rika, ze se NEMERILO."""
        return self.trida in TRIDY_POZOR


@dataclass(frozen=True)
class Vysledek:
    """Vysledek jednoho behu validace nad celou scenou."""

    nalezy: Tuple[Nalez, ...] = ()
    pocty: Dict[str, int] = field(default_factory=dict)
    urovne_vse: Dict[int, str] = field(default_factory=dict)
    urovne_hlavni: Dict[int, str] = field(default_factory=dict)
    ceka: bool = False
    cas: float = 0.0

    @property
    def chyb(self) -> int:
        return sum(1 for n in self.nalezy if n.uroven == "ERROR")

    @property
    def varovani(self) -> int:
        return sum(1 for n in self.nalezy if n.uroven != "ERROR")

    def uroven_prvku(self, idx: int, *, vse: bool = False) -> Optional[str]:
        mapa = self.urovne_vse if vse else self.urovne_hlavni
        return mapa.get(int(idx))


def barva_urovne(uroven: Optional[str]) -> Optional[Tuple[int, int, int]]:
    if uroven == "ERROR":
        return BARVA_ERROR
    if uroven == "WARN":
        return BARVA_WARN
    return None


# --------------------------------------------------------------------------- #
# Cteni zprav validatoru
# --------------------------------------------------------------------------- #


def bez_prefixu(zprava: str) -> str:
    """Odrizne prefix souboru/sceny presne jako `do_espos.py`."""
    return _PREFIX_RE.sub("", str(zprava).strip())


def klic_zpravy(zprava: str) -> str:
    """Deduplikacni klic - doslova tentyz jako v `do_espos.py`."""
    return _KLIC_RE.sub("", zprava)


# Znacka hlasky -> trida nalezu. JMENA ZNACEK, ne jejich hodnoty: hodnota se
# bere behove z `validate_design`, aby zmena hlasky nezustala jako tise
# prazdna kategorie. Tataz tabulka zije v `do_espos.tridy()`; obe se
# porovnavaji behove (`test_CELA_tabulka_trid_se_shoduje_s_branou`), protoze
# dve rucne psane kopie se drive nebo pozdeji rozejdou.
#
# UPLNOST se kontroluje strojove: kazda verejna konstanta `ZNACKA_*`
# validatoru tu musi mit tridu a naopak. Prirazeni je rozhodnuti (jmeno
# tridy je vec vkusu), uplnost uz ne.
_MAPA_ZNACEK = {
    "ZNACKA_R136_RODIC": "oriznuti",
    "ZNACKA_R136_PAS": "oriznuti",
    "ZNACKA_R136_PAS_VEN": "oriznuti",
    "ZNACKA_R136_OZNACENI": "oriznuti",
    "ZNACKA_R137": "preteceni",
    "ZNACKA_R137_NEMERENO": "preteceni",
    "ZNACKA_R138": "prazdny-smalt",
    "ZNACKA_R138_OZNACENI": "prazdny-smalt",
    "ZNACKA_R139": "pomlcka",
    "ZNACKA_R139_ZASTUPNY": "pomlcka",
    "ZNACKA_R140": "kapacita",
    "ZNACKA_R140_NEMERENO": "kapacita",
    "ZNACKA_R141": "dpi",
    "ZNACKA_R141_NEMERENO": "dpi",
    "ZNACKA_R141_ODCHYLKA": "dpi",
    "ZNACKA_R142": "vety",
    "ZNACKA_R142_NEMERENO": "vety",
    "ZNACKA_R142_VYKLAD": "vety",
    "ZNACKA_R143": "slovnik",
    "ZNACKA_R143_NEMERENO": "slovnik",
    "ZNACKA_R143_ROLE_NEMERENO": "slovnik",
    "ZNACKA_R144": "oriznuti-schrankou",
    "ZNACKA_R145": "pretekl-dolu",
    "ZNACKA_R146": "polarita",
    "ZNACKA_R147": "cara",
    "ZNACKA_R148": "skala",
    "ZNACKA_R148_NEMERENO": "skala",
    "ZNACKA_R148_ODCHYLKA": "skala",
    "ZNACKA_R149": "citelnost",
    "ZNACKA_R150": "paleta",
    "ZNACKA_R150_NEMERENO": "paleta",
    "ZNACKA_R150_ODCHYLKA": "paleta",
    "ZNACKA_R151": "odsazeni",
    "ZNACKA_R151_NEMERENO": "odsazeni",
    "ZNACKA_R17_NEAKTIVNI": "kontrast",
    "ZNACKA_NAVRH_VADNY": "vadny navrh",
}

_TRIDY_MERENA: Optional[Tuple[Tuple[str, str], ...]] = None


def tridy_merena() -> Tuple[Tuple[str, str], ...]:
    """Tridy pravidel 136-143, tedy `do_espos.tridy()` bez zakladu.

    NENI to literal jako `TRIDY` a byt nemuze: vzor kazde tridy je znacka
    hlasky, kterou sklada `validate_design` (`ZNACKA_R136_RODIC` a dalsi).
    Opsany retezec by prezil zmenu hlasky jako tise prazdna kategorie -
    nalez by spadl do "netrideno" a vypadal by jako neco, co editor nezna,
    misto aby vypadal jako to, co je. Proto se bere BEHOVOU HODNOTOU
    z tehoz modulu, kterym editor validuje.

    Import je liny ze stejneho duvodu jako u `validate_data` nize: modul
    `tools` je na `sys.path` az za behu editoru, ne pri importu adapteru.

    Poradi: nove tridy jdou PRED zaklad, protoze jsou uzsi - doslova jako
    v `do_espos.tridy()`. Shodu obou tabulek hlida test proti behove
    hodnote brany.
    """
    global _TRIDY_MERENA
    if _TRIDY_MERENA is None:
        from tools import validate_design as vd

        zname = {j for j in dir(vd) if j.startswith("ZNACKA_")}
        chybi = sorted(zname - set(_MAPA_ZNACEK))
        if chybi:
            raise RuntimeError(
                "tab5_validace: validate_design ma znacky bez tridy: "
                + ", ".join(chybi)
                + " - nalez by spadl do 'netrideno' a vypadal by jako nezname hlaseni"
            )
        prebyva = sorted(set(_MAPA_ZNACEK) - zname)
        if prebyva:
            raise RuntimeError(
                "tab5_validace: `_MAPA_ZNACEK` zna znacky, ktere validate_design uz "
                "nema: " + ", ".join(prebyva) + " - trida by zustala tise prazdna"
            )
        poradi = sorted(_MAPA_ZNACEK, key=lambda j: -len(getattr(vd, j)))
        _TRIDY_MERENA = tuple(
            (_MAPA_ZNACEK[j], str(getattr(vd, j))) for j in poradi
        )
    return _TRIDY_MERENA


def trida_zpravy(zprava: str) -> str:
    for jmeno, vzor in tridy_merena() + TRIDY:
        if vzor in zprava:
            return jmeno
    return NETRIDENO


def indexy_ze_zpravy(zprava: str) -> Tuple[int, ...]:
    """Vytahne odkazy `widget[N]`. U OVERLAP jich zprava nese DVOJICI."""
    videno: List[int] = []
    for m in _INDEX_RE.finditer(zprava):
        i = int(m.group(1))
        if i not in videno:
            videno.append(i)
    return tuple(videno)


def _zasahy_do_TRIDY(strom: ast.AST) -> Tuple[List[ast.AST], List[str]]:
    """Vsechna mista, kde se modul jmena `TRIDY` dotkne.

    Puvodni cteni bralo PRVNI `ast.Assign` v `strom.body` a hned se vracelo.
    Revize A na tom predvedla ctyri obchazky, ktere vsechny prosly zelene:
    `TRIDY.append(...)`, `TRIDY += [...]`, druhe prirazeni niz v souboru
    a `TRIDY[0] = ...`. Je to tataz rodina jako rename-evasion: strazce
    hlidal ZAPIS LITERALU, ne skutecnou hodnotu. Proto se prochazi cely
    strom a cokoli jineho nez JEDINE literalove prirazeni je duvod selhat.
    """
    prirazeni: List[ast.AST] = []
    problemy: List[str] = []
    for uzel in ast.walk(strom):
        if isinstance(uzel, ast.Assign):
            for cil in uzel.targets:
                if isinstance(cil, ast.Name) and cil.id == "TRIDY":
                    prirazeni.append(uzel)
                elif (
                    isinstance(cil, (ast.Subscript, ast.Starred))
                    and isinstance(getattr(cil, "value", None), ast.Name)
                    and cil.value.id == "TRIDY"  # type: ignore[attr-defined]
                ):
                    problemy.append(f"radek {uzel.lineno}: prirazeni do prvku TRIDY[...]")
        elif isinstance(uzel, ast.AnnAssign):
            if isinstance(uzel.target, ast.Name) and uzel.target.id == "TRIDY" and uzel.value:
                prirazeni.append(uzel)
        elif isinstance(uzel, ast.AugAssign):
            if isinstance(uzel.target, ast.Name) and uzel.target.id == "TRIDY":
                problemy.append(f"radek {uzel.lineno}: TRIDY se rozsiruje pres +=")
        elif isinstance(uzel, ast.Attribute):
            if isinstance(uzel.value, ast.Name) and uzel.value.id == "TRIDY":
                problemy.append(f"radek {uzel.lineno}: volani TRIDY.{uzel.attr}")
        elif isinstance(uzel, ast.Delete):
            for cil in uzel.targets:
                if isinstance(cil, ast.Name) and cil.id == "TRIDY":
                    problemy.append(f"radek {uzel.lineno}: del TRIDY")
        elif isinstance(uzel, (ast.For, ast.NamedExpr)):
            if isinstance(uzel.target, ast.Name) and uzel.target.id == "TRIDY":
                problemy.append(f"radek {uzel.lineno}: TRIDY se prepisuje v cyklu/vyrazu")
    return prirazeni, problemy


def tridy_z_do_espos(cesta: pathlib.Path) -> Tuple[Tuple[str, str], ...]:
    """Precte `TRIDY` z `do_espos.py` STATICKY pres `ast`.

    Nikdy neimportuje: v `navrh-appky` se `zapis()` vola na urovni modulu,
    takze import generatoru prepise artboard. U `do_espos.py` by to sice
    neuskodilo (ma `if __name__`), ale pravidlo "nad tim stromem jen ast"
    nema mit vyjimky, ktere si musi clovek pamatovat.

    Selze na cemkoli jinem nez JEDINEM literalovem prirazeni - viz
    `_zasahy_do_TRIDY`. Doplnkem je `tridy_behem_behu()`, ktera cte skutecnou
    BEHOVOU hodnotu: staticka cesta rekne PROC se to rozchazi, behova ZE se
    to rozchazi.
    """
    strom = ast.parse(pathlib.Path(cesta).read_text(encoding="utf-8"))
    prirazeni, problemy = _zasahy_do_TRIDY(strom)
    if problemy:
        raise ValueError(f"v {cesta} se TRIDY meni jinak nez prirazenim: {'; '.join(problemy)}")
    if len(prirazeni) != 1:
        raise ValueError(f"v {cesta} je prirazeni TRIDY {len(prirazeni)}x, ocekava se prave jedno")
    try:
        polozky = ast.literal_eval(prirazeni[0].value)  # type: ignore[attr-defined]
    except (ValueError, TypeError) as exc:
        raise ValueError(f"v {cesta} neni TRIDY literal: {exc}") from exc
    return tuple((str(a), str(b)) for a, b in polozky)


# `python -c` pro podproces. Cte BEHOVOU hodnotu, tedy to, s cim brana
# opravdu pracuje - `append`, `+=`, druhe prirazeni ani `TRIDY[0] = ...` se
# pred ni neschovaji. `main()` se nespousti: modul ma `if __name__`.
_KOD_TRIDY = (
    "import json,sys;"
    "sys.path.insert(0, sys.argv[1]);"
    "import do_espos;"
    "sys.stdout.write(json.dumps([[str(a), str(b)] for a, b in do_espos.TRIDY]))"
)

# Cela tabulka brany, tedy `do_espos.tridy(validate_design)`. Staticky ji
# precist nelze - vzory pravidel 136-143 jsou behove hodnoty konstant, ne
# retezce ve zdroji - takze jedina poctiva kontrola je behova.
_KOD_TRIDY_MERENA = (
    "import json,sys;"
    "sys.path.insert(0, sys.argv[1]);"
    "import do_espos;"
    "sys.stdout.write(json.dumps("
    "[[str(a), str(b)] for a, b in do_espos.tridy(do_espos.validator())]))"
)


def tridy_behem_behu(cesta: pathlib.Path, *, timeout: float = 60.0,
                     kod: str = _KOD_TRIDY) -> Tuple[Tuple[str, str], ...]:
    """Precte BEHOVOU hodnotu `do_espos.TRIDY` podprocesem.

    Podproces, ne import do naseho procesu: `navrh-appky` je cizi strom
    a nema co lezet v `sys.modules` editoru. `PYTHONIOENCODING=utf-8` je
    tataz hraz, jakou si stavi brana - bez ni tisk na cp1250 pada.

    Selze hlasite. Meridlo, ktere pri chybe vrati prazdno, by tvrdilo shodu
    tam, kde se nezmerilo.
    """
    cesta = pathlib.Path(cesta)
    if not cesta.exists():
        raise ValueError(f"do_espos.py neexistuje: {cesta}")
    hot = subprocess.run(
        [sys.executable, "-c", kod, str(cesta.parent)],
        # PYTHONDONTWRITEBYTECODE: do ciziho stromu (`navrh-appky`) se nesmi
        # nic zapisovat. Import podprocesem by jinak prepsal `__pycache__/
        # do_espos.cpython-312.pyc` - a prave ten .pyc slouzil revizi A jako
        # jediny dochovany otisk brany PRED zasahy (slozka je untracked).
        env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if hot.returncode != 0:
        chyba = hot.stderr.decode("utf-8", "replace").strip().splitlines()
        raise ValueError(
            f"cteni behove TRIDY z {cesta} skoncilo kodem {hot.returncode}: "
            f"{chyba[-1] if chyba else ''}"
        )
    try:
        polozky = json.loads(hot.stdout.decode("utf-8", "replace"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"behova TRIDY z {cesta} neni JSON: {exc}") from exc
    return tuple((str(a), str(b)) for a, b in polozky)


def tridy_merena_behem_behu(
    cesta: pathlib.Path, *, timeout: float = 60.0
) -> Tuple[Tuple[str, str], ...]:
    """CELA tabulka brany (`do_espos.tridy(...)`) behovou hodnotou.

    Tataz cesta jako `tridy_behem_behu` a stejne fail-closed: kdyz se
    nezmeri, vyhodi vyjimku misto prazdna.
    """
    return tridy_behem_behu(cesta, timeout=timeout, kod=_KOD_TRIDY_MERENA)


# --------------------------------------------------------------------------- #
# Vlastni validace
# --------------------------------------------------------------------------- #


def _validate_data() -> Any:
    """Lazy import validatoru.

    Import az tady, aby start editoru nenesl 2 500 radku pravidel, ktera
    scena mimo tab5 stejne nepouzije.
    """
    from tools.validate_design import validate_data

    return validate_data


# Em dash z originalnich hlasek `validate_file`. Zapsana escapem, aby zdroj
# zustal ASCII a hlaska pritom byla znak po znaku tataz jako u brany.
_POMLCKA = "\u2014"

_ZPRAVA_BEZ_JSONSCHEMA = (
    "schema validation unavailable " + _POMLCKA + " the 'jsonschema' package is "
    "not installed. It is a required runtime dependency; install it with "
    "'pip install -r requirements.txt' (or 'pip install jsonschema'). "
    "Schema validation is mandatory and will not be skipped."
)


@dataclass(frozen=True)
class _SchemaNalez:
    """Nalez ze schema casti. Tvarem odpovida `validate_design.Issue`."""

    level: str
    message: str


_SCHEMA_CACHE: Dict[Any, Any] = {}


def _schema_validator(cesta: pathlib.Path, jsonschema: Any) -> Any:
    """Sestaveny validator schematu, cachovany podle mtime a velikosti.

    Cachuje se MERIDLO, ne vysledek: schema se nacita pri kazdem pusteni
    prvku a 531 radku JSONu je zbytecna prace. Klic nese mtime i velikost,
    takze zmena schematu se projevi hned.
    """
    stat = cesta.stat()
    klic = (str(cesta), stat.st_mtime_ns, stat.st_size)
    if klic not in _SCHEMA_CACHE:
        schema = json.loads(cesta.read_text(encoding="utf-8"))
        _SCHEMA_CACHE.clear()
        _SCHEMA_CACHE[klic] = jsonschema.Draft202012Validator(schema)
    return _SCHEMA_CACHE[klic]


def schema_nalezy(data: Dict[str, Any], *, file_label: str) -> List[_SchemaNalez]:
    """JSON-schema cast brany, doslova jako `validate_design.validate_file`.

    Brana `do_espos.py` pousti validator jako CLI, tedy `validate_file`, kde
    schema PREDCHAZI `validate_data` a je POVINNA ("Schema enforcement must
    never be silently optional"). Adapter, ktery ji vynecha, propusti to, co
    brana zastavi - dolozeno na dvou vadach: `groups` jako seznam misto
    slovniku a klic navic u widgetu (`additionalProperties: false`).

    Chybejici `jsonschema` nebo chybejici soubor schematu je proto tvrdy
    ERROR, ne tiche preskoceni.
    """
    from tools.validate_design import SCHEMA_PATH

    try:
        import jsonschema
    except ImportError:
        return [_SchemaNalez("ERROR", f"{file_label}: {_ZPRAVA_BEZ_JSONSCHEMA}")]
    if not SCHEMA_PATH.exists():
        return [
            _SchemaNalez(
                "ERROR",
                f"{file_label}: schema file missing at {SCHEMA_PATH} {_POMLCKA} cannot perform "
                "mandatory structural validation.",
            )
        ]
    try:
        validator = _schema_validator(SCHEMA_PATH, jsonschema)
    except (OSError, ValueError) as exc:
        return [
            _SchemaNalez(
                "ERROR",
                f"{file_label}: schema file at {SCHEMA_PATH} could not be loaded "
                f"({exc}); structural validation cannot run.",
            )
        ]
    nalezy: List[_SchemaNalez] = []
    for error in validator.iter_errors(data):
        loc = ".".join(str(usek) for usek in error.absolute_path) or "(root)"
        nalezy.append(_SchemaNalez("ERROR", f"{file_label}: schema: {loc}: {error.message}"))
    return nalezy


def vyhodnot(data: Dict[str, Any], *, file_label: str = "editor") -> Vysledek:
    """Zvaliduje CELOU scenu a vrati roztridene nalezy.

    Cela scena, ne jeden widget: pravidla 21 (overlap), 123 (gap), 134
    (near-miss) a duplicita `_widget_id` jsou MEZI prvky. Pri 41 widgetech
    je O(n^2) zdarma (~1,4 ms).

    Meri se **toutez cestou jako brana**, tedy vcetne JSON-schema
    (`schema_nalezy`) - viz bod 5 v hlavicce modulu.
    """
    zacatek = time.perf_counter()
    validate_data = _validate_data()
    # Poradi je tez jako ve `validate_file`: nejdriv schema, pak pravidla.
    # Brana cte radky CLI shora dolu, takze na poradi zalezi.
    issues = [
        *schema_nalezy(data, file_label=file_label),
        *validate_data(data, file_label=file_label, warnings_as_errors=False),
    ]

    videno: set = set()
    nalezy: List[Nalez] = []
    pocty: Counter = Counter()
    for it in issues:
        zprava = bez_prefixu(getattr(it, "message", ""))
        klic = klic_zpravy(zprava)
        if klic in videno:
            continue
        videno.add(klic)
        trida = trida_zpravy(zprava)
        pocty[trida] += 1
        nalezy.append(
            Nalez(
                uroven=str(getattr(it, "level", "WARN")),
                trida=trida,
                zprava=zprava,
                indexy=indexy_ze_zpravy(zprava),
                puvodni=str(getattr(it, "message", "")),
            )
        )

    urovne_vse: Dict[int, str] = {}
    urovne_hlavni: Dict[int, str] = {}
    for n in nalezy:
        for i in n.indexy:
            if n.uroven == "ERROR" or i not in urovne_vse:
                urovne_vse[i] = n.uroven
            if n.trida in TRIDY_BEZ_RAMECKU:
                continue
            if n.uroven == "ERROR" or i not in urovne_hlavni:
                urovne_hlavni[i] = n.uroven

    return Vysledek(
        nalezy=tuple(nalezy),
        pocty=dict(pocty),
        urovne_vse=urovne_vse,
        urovne_hlavni=urovne_hlavni,
        ceka=False,
        cas=time.perf_counter() - zacatek,
    )


# --------------------------------------------------------------------------- #
# Napojeni na bezici editor
# --------------------------------------------------------------------------- #


def je_tab5(app: Any) -> bool:
    """Meri se tahle scena profilem tab5?

    Bud je pripojeny most z artboardu (`tab5_most.pripoj`), nebo si uzivatel
    profil tab5 vybral rucne. Mimo to modul nedela NIC - navrhy pro OLED
    256x128 se timhle profilem merit nesmi.
    """
    if getattr(app, "tab5_otisk", None) is not None:
        return True
    return str(getattr(app, "hardware_profile", "") or "") == PROFIL_TAB5


def dokument_z_app(app: Any) -> Dict[str, Any]:
    """Slovnik aktualni sceny pro `validate_data`, VZDY s `device`."""
    des = app.designer
    jmeno = des.current_scene
    if not jmeno or jmeno not in des.scenes:
        raise ValueError("designer nema aktivni scenu")
    sc = des.scenes[jmeno]
    otisk = getattr(app, "tab5_otisk", None)
    device = str(getattr(otisk, "device", "") or "") or DEVICE_TAB5
    return {
        "device": device,
        "width": int(des.width),
        "height": int(des.height),
        "groups": {},
        "scenes": {
            jmeno: {
                "name": sc.name,
                "width": int(sc.width),
                "height": int(sc.height),
                "bg_color": getattr(sc, "bg_color", "#000000"),
                "widgets": [_widget_na_slovnik(w) for w in sc.widgets],
            }
        },
    }


def _popisek(app: Any) -> str:
    otisk = getattr(app, "tab5_otisk", None)
    return str(getattr(otisk, "scena", "") or "editor")


def _spust(app: Any, ted: float) -> Vysledek:
    vysledek = vyhodnot(dokument_z_app(app), file_label=_popisek(app))
    app.tab5_vysledek = vysledek
    app._tab5_posledni_validace = ted
    app._tab5_ceka = False
    try:
        app._set_status(
            f"tab5: {vysledek.chyb} ERROR, {vysledek.varovani} WARN",
            ttl_sec=2.0,
        )
    except (AttributeError, TypeError):
        logger.debug("editor nema _set_status")
    try:
        app._mark_dirty()
    except AttributeError:
        logger.debug("editor nema _mark_dirty")
    return vysledek


def po_pusteni(app: Any, ted: Optional[float] = None) -> Optional[Vysledek]:
    """Hak z `mouse_handlers.on_mouse_up`. Vraci vysledek, nebo None (debounce)."""
    if not je_tab5(app):
        return None
    ted = time.monotonic() if ted is None else float(ted)
    posledni = getattr(app, "_tab5_posledni_validace", None)
    if posledni is not None and (ted - float(posledni)) < DEBOUNCE_S:
        app._tab5_ceka = True
        stary = getattr(app, "tab5_vysledek", None)
        if isinstance(stary, Vysledek) and not stary.ceka:
            # Panel nesmi tvrdit, ze meri to, co je na platne TED.
            app.tab5_vysledek = replace(stary, ceka=True)
        return None
    return _spust(app, ted)


def tik(app: Any, ted: Optional[float] = None) -> Optional[Vysledek]:
    """Dobehne validaci odlozenou debouncem. Bezpecne volat kdykoli."""
    if not je_tab5(app) or not getattr(app, "_tab5_ceka", False):
        return None
    ted = time.monotonic() if ted is None else float(ted)
    posledni = getattr(app, "_tab5_posledni_validace", None)
    if posledni is not None and (ted - float(posledni)) < DEBOUNCE_S:
        return None
    return _spust(app, ted)


def aktualni(app: Any) -> Optional[Vysledek]:
    """Cerstvy vysledek BEZ debounce - pro branu.

    Brana nesmi rozhodovat podle vysledku, ktery uz neplati; debounce je
    pro obrazovku, ne pro rozhodnuti.
    """
    if not je_tab5(app):
        return None
    return _spust(app, time.monotonic())


def brana_ulozeni(app: Any) -> Optional[str]:
    """Vraci duvod, proc se vystup NEMA vydat, nebo None.

    Stejne prisna jako `do_espos.py`: jakykoli ERROR = selhani. WARN branu
    nezastavi (na cistem artboardu jich je 34 a vsechny jsou "vrstveni"),
    ale spocitaji se a jsou videt.

    **FAIL-CLOSED.** Drive brana pri vyjimce vratila `None`, coz znamena
    "nic nebrani" - rozbite meridlo se tedy nedalo rozeznat od cisteho
    navrhu a scena i rudy zapis se vydaly nad necim, co nikdo nezmeril.
    Realna cesta k tomu vede primo z tohohle modulu: `dokument_z_app`
    vyhodi `ValueError("designer nema aktivni scenu")`. `ImportError`
    (rozbity `tools.validate_design`) se drive nechytal vubec a propadl az
    do `save_json`, kde ho nikdo necekal. Oboji ted konci stejne: duvod
    nevydat.

    `do_espos.py` se chova tak: anomalii validatoru si zapise do `chyby`
    a vrati kod 1. Meridlo, ktere selhalo, neni nula nalezu.
    """
    try:
        if not je_tab5(app):
            return None
    except (AttributeError, TypeError) as exc:
        logger.warning("tab5: profil sceny nelze zjistit: %s", exc)
        return f"{DUVOD_NEZMERENO}: profil sceny nelze zjistit ({exc})"

    try:
        vysledek = aktualni(app)
    except (ValueError, LookupError, AttributeError, TypeError, ImportError, OSError) as exc:
        logger.warning("validace tab5 selhala: %s", exc)
        return f"{DUVOD_NEZMERENO}: validace selhala ({type(exc).__name__}: {exc})"
    except Exception as exc:  # necekana vyjimka je taky "nezmerilo se"
        logger.exception("validace tab5 skoncila necekanou vyjimkou")
        return f"{DUVOD_NEZMERENO}: necekana vyjimka ({type(exc).__name__}: {exc})"

    if vysledek is None:
        # je_tab5 vyse rekl True, takze `aktualni` vysledek vratit MELA.
        return f"{DUVOD_NEZMERENO}: validace nevratila vysledek"
    if not vysledek.chyb:
        return None
    prvni = next((n.zprava for n in vysledek.nalezy if n.uroven == "ERROR"), "")
    return f"{vysledek.chyb} ERROR - nevydavam: {prvni[:100]}"


def prepni_nalezy(app: Any) -> bool:
    """Prepinac panelu nalezu. Vraci novy stav."""
    novy = not bool(getattr(app, "show_nalezy", True))
    app.show_nalezy = novy
    try:
        app._mark_dirty()
    except AttributeError:
        logger.debug("editor nema _mark_dirty")
    return novy
