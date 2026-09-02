"""Most z artboardu TabOSu (tabos-ui-kit) do editoru ESPOS.

Navrhy TabOSu nejsou dokument, jsou to VYGENEROVANE HTML. Jedina cesta do
editoru vede pres `navrh-appky/do_espos.py`, ktery artboard promeri headless
Chromem a vyda scenu `_scena_X.json` (a s prepinacem `--snimek` i podklad
`_snimek_X.png`).

Tenhle modul tu scenu nacte a pripoji k editoru. Plati u toho tri veci:

1. **Editor navrh NEPREPISUJE.** Zdrojem pravdy zustavaji generatory
   `gen_*.py`. Editor vyda az v etape 4 "rudy zapis" - patch v souradnicich
   generatoru. Proto se pri nacteni pori OTISK: proti nemu se pozdeji dela
   rozdil. Bez otisku by se nedalo poznat, co Filip posunul.
2. **Prevod je ZTRATOVY** (ze 133 prvku artboardu SvorkaLA projde 41).
   Editor tedy ukazuje mensi cast navrhu, nez v nem je - proto podklad.
3. **`UIDesigner.save_to_json` zahazuje korenovy klic `device`.** Kdyz se
   scena ulozi a znovu nacte, `device: tab5` je pryc a validator by spadl
   zpet na profil OLED 256x128 - jine dotykove meze, jina znakova sada, jiny
   model kontrastu. A NIC by to nenahlasilo. Otisk si proto `device` pamatuje
   zvlast a `dokument()` ho do slovniku pro validator vzdy doplni.
4. **Vedle sceny lezi `_meta_X.json`** - dodatecna pole, ktera do sceny
   patrit nesmi (schema ma `additionalProperties: false`, kazdy klic navic je
   pro branu tvrdy ERROR). Nese skutecny ramecek prvku, inline styl
   generatoru a `offsetParent`. Bez nich rudy zapis vydaval vymyslena cisla
   (revize A, nalezy A1/A2). Kdyz meta neni, otisk ma `ma_meta = False`
   a rudy zapis zadne cislo generatoru nevyda.
5. **Otisk si pamatuje IDENTITU zdroje** - sha256 souboru sceny i mety
   v okamziku nacteni (`Otisk.sha_sceny`, `Otisk.sha_meta`). Klicem patche je
   `trida.index`; kdyz se artboard pod bezicim editorem pregeneruje, indexy se
   posunou a rozdil proti otisku vyda hromadu vymyslenych zmen (na SvorkaLA
   62 zmen ze 41 prvku). `overi_zdroj()` to pozna a `redline.vydej` v tom
   pripade NEVYDA nic.

PRACOVNI POSTUP - PROC VZDY `--zapis-scenu`
-------------------------------------------
`python do_espos.py <artboard>` **bez prepinacu** je BRANA, ne vyroba vstupu:
scenu si vyrobi, zmeri ji validatorem a `_scena_X.json` i `_meta_X.json`
zase SMAZE (`do_espos.main()`, vetev `else: js.unlink(...)`). Je to tak
spravne - mezikrok neni vystup - ale je to past: bezne denni prohnani vsech
artboardu branou vezme scenu pod rukama a `nacti()` pak spadne na
`MostError: scena neexistuje`, zatimco `_snimek_X.png` zustane lezet a
slozka vypada pripravene.

Vstup pro editor se proto vyraba VZDY takhle:

    python do_espos.py SvorkaLA.dc.html --zapis-scenu --snimek

Scena a meta odchazeji spolecne, takze nikdy nevznikne dvojice "cerstva
scena + stara meta" - to by rudy zapis krmilo cisly z jineho behu.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pygame

from ui_designer import UIDesigner

logger = logging.getLogger(__name__)

# Profil displeje. Musi sedet s klicem v `ui_designer.HARDWARE_PROFILES`
# a se jmenem profilu v `tools/validate_design.py` (PROFILE_TAB5.name).
PROFIL_TAB5 = "tab5_1280x720"
DEVICE_TAB5 = "tab5"

PREDPONA_SCENY = "_scena_"
PREDPONA_SNIMKU = "_snimek_"
PREDPONA_META = "_meta_"

# Poradi os v `OtiskPrvku.gen` - tytez, jake pouziva `redline`.
OSY = ("left", "top", "width", "height")

# Duvody, proc se proti otisku uz nesmi nic vydat (viz `overi_zdroj`).
# `_widget_id` je `trida.index`, tedy poradi v `querySelectorAll('*')`.
# Kdyz se artboard pod editorem pregeneruje, indexy se posunou a rozdil
# proti otisku vyrobi vymyslene zmeny: na SvorkaLA (41 prvku) to bylo
# 62 zmen, z toho 14 tvrdilo "prvek byl posunut" a 24 "prvek byl smazan".
# Patch to nikde nerekl - proto si otisk pamatuje sha256 zdrojovych
# souboru a `redline.vydej` je pred vydanim porovna.
DUVOD_ZMENA_ZDROJE = "artboard se pod editorem zmenil - nacti scenu znovu"
DUVOD_NEOVERENO = "NEOVERENO - nevydavam"


class MostError(Exception):
    """Scenu se nepodarilo nacist tak, aby se dala editovat."""


@dataclass(frozen=True)
class OtiskPrvku:
    """Jeden prvek tak, jak PRISEL z artboardu.

    `x/y/width/height` je to, co je ve SCENE - a u popisku to NENI ramecek,
    ale rozsah inkoustu (`do_espos.MERIC`, funkce `inkoust()`). Skutecny
    ramecek je v `box` a cislo, ktere generator zapsal, v `gen`. Rudy zapis
    smi vydavat jen `gen`; odectenim od sceny vznikala vymyslena cisla.
    """

    widget_id: str
    typ: str
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    # z `_meta_X.json`; None = doklad neni
    box: Optional[Tuple[int, int, int, int]] = None
    gen: Tuple[Optional[int], Optional[int], Optional[int], Optional[int]] = (
        None,
        None,
        None,
        None,
    )
    rodic: str = ""
    v_obsahu: bool = False

    @property
    def obdelnik(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class Otisk:
    """Stav sceny pri nacteni; proti nemu se v etape 4 dela rudy zapis."""

    zdroj: str
    scena: str
    device: str
    width: int
    height: int
    prvky: Tuple[OtiskPrvku, ...] = ()
    # Byla k dispozici `_meta_X.json`? Kdyz ne, rudy zapis nesmi vydat ani
    # jedno cislo v souradnicich generatoru - nema je z ceho dolozit.
    ma_meta: bool = False
    # IDENTITA ZDROJE: sha256 souboru `_scena_X.json` v okamziku nacteni.
    # Prazdny retezec = otisk vznikl z dat, ne ze souboru; overit ho pak
    # nejde a `overi_zdroj` fail-closed odmitne.
    sha_sceny: str = ""
    # sha256 `_meta_X.json`, nebo None, kdyz meta pri nacteni NEBYLA.
    # Drzi se stejny stav jako `ma_meta`: None <-> ma_meta is False.
    sha_meta: Optional[str] = None

    def podle_id(self) -> Dict[str, OtiskPrvku]:
        """Prvky podle `_widget_id`.

        POZOR: `_widget_id` z prevodniku je `trida.index` a index je poradi
        v `document.querySelectorAll('*')` - posune se, jakmile generator
        pribere jakykoli DRIVEJSI prvek. Jako klic patche to plati jen v ramci
        JEDNE relace nad JEDNIM otiskem artboardu.
        """
        return {p.widget_id: p for p in self.prvky if p.widget_id}


@dataclass
class Most:
    """Nactena scena artboardu pripravena pro editor."""

    designer: UIDesigner
    otisk: Otisk
    cesta_sceny: pathlib.Path
    cesta_podkladu: Optional[pathlib.Path] = None
    podklad: Optional[pygame.Surface] = None
    data: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Cesty
# --------------------------------------------------------------------------- #


def _holy_nazev(cesta_sceny: pathlib.Path) -> str:
    jmeno = pathlib.Path(cesta_sceny).name
    if jmeno.startswith(PREDPONA_SCENY):
        jmeno = jmeno[len(PREDPONA_SCENY) :]
    return pathlib.Path(jmeno).stem


def cesta_podkladu(cesta_sceny: pathlib.Path) -> pathlib.Path:
    """`_scena_SvorkaLA.dc.json` -> `_snimek_SvorkaLA.dc.png` ve stejne slozce."""
    cesta_sceny = pathlib.Path(cesta_sceny)
    return cesta_sceny.with_name(PREDPONA_SNIMKU + _holy_nazev(cesta_sceny) + ".png")


def cesta_meta(cesta_sceny: pathlib.Path) -> pathlib.Path:
    """`_scena_SvorkaLA.dc.json` -> `_meta_SvorkaLA.dc.json` ve stejne slozce."""
    cesta_sceny = pathlib.Path(cesta_sceny)
    return cesta_sceny.with_name(PREDPONA_META + _holy_nazev(cesta_sceny) + ".json")


# --------------------------------------------------------------------------- #
# Nacteni
# --------------------------------------------------------------------------- #


def otisk_souboru(cesta: pathlib.Path) -> Optional[str]:
    """sha256 souboru v hex; `None`, kdyz soubor NENI.

    Neprecteny soubor NENI totez co "zadny soubor" - to by byl tichy propad
    presne k tomu, co tahle pojistka hlida (merilo selhalo, nikoli nula).
    Proto se z neho stane `MostError` a volajici se rozhodne nahlas.
    """
    cesta = pathlib.Path(cesta)
    try:
        return hashlib.sha256(cesta.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MostError(f"otisk souboru nelze poridit: {cesta} ({exc})") from exc


def _cti_json(cesta: pathlib.Path) -> Tuple[Dict[str, Any], str]:
    """Data sceny a sha256 TYCHZ bajtu.

    Otisk se pocita z bajtu, ktere se prave rozparsovaly, ne dalsim ctenim -
    jinak by mezi obojim byla skulina a otisk by patril jinemu obsahu, nez
    ze ktereho vznikla scena.
    """
    cesta = pathlib.Path(cesta)
    try:
        syrove = cesta.read_bytes()
    except FileNotFoundError as exc:
        raise MostError(f"scena neexistuje: {cesta}") from exc
    except OSError as exc:
        raise MostError(f"scenu nelze precist: {cesta} ({exc})") from exc
    try:
        data = json.loads(syrove.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MostError(f"scenu nelze precist: {cesta} ({exc})") from exc
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), dict):
        raise MostError(f"scena nema tvar navrhu ESPOS: {cesta}")
    if not data["scenes"]:
        raise MostError(f"scena neobsahuje zadnou scenu: {cesta}")
    return data, hashlib.sha256(syrove).hexdigest()


def _prvni_scena(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    jmeno = next(iter(data["scenes"]))
    sc = data["scenes"][jmeno]
    if not isinstance(sc, dict):
        raise MostError(f"scena {jmeno!r} neni slovnik")
    return jmeno, sc


def nacti_meta(cesta: pathlib.Path) -> Optional[Dict[str, Dict[str, Any]]]:
    """Nacte `_meta_X.json` do mapy `_widget_id -> zaznam`. None = neni.

    Chybejici meta NENI vyjimka: scena se da editovat i bez ni, jen rudy
    zapis pak nevyda ani jedno cislo v souradnicich generatoru. Rozbita meta
    se ale nesmi tvarit jako "zadna" - to by byl tichy propad k tomu, co
    revize A vyvratila. Proto se vyhodi `MostError`.
    """
    return _cti_meta(cesta)[0]


def _cti_meta(
    cesta: pathlib.Path,
) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[str]]:
    """Mapa z `_meta_X.json` a sha256 TYCHZ bajtu. `(None, None)` = meta neni."""
    cesta = pathlib.Path(cesta)
    try:
        syrove = cesta.read_bytes()
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise MostError(f"meta nelze precist: {cesta} ({exc})") from exc
    try:
        data = json.loads(syrove.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MostError(f"meta nelze precist: {cesta} ({exc})") from exc
    if not isinstance(data, list):
        raise MostError(f"meta nema tvar seznamu: {cesta}")
    mapa: Dict[str, Dict[str, Any]] = {}
    for zaznam in data:
        if not isinstance(zaznam, dict):
            continue
        wid = str(zaznam.get("_widget_id") or "")
        if wid:
            mapa[wid] = zaznam
    return mapa, hashlib.sha256(syrove).hexdigest()


def _ctverice(hodnoty: Any, klice: Tuple[str, ...]) -> Tuple[Optional[int], ...]:
    if not isinstance(hodnoty, dict):
        return (None,) * len(klice)
    ven: List[Optional[int]] = []
    for k in klice:
        h = hodnoty.get(k)
        ven.append(int(h) if isinstance(h, (int, float)) and not isinstance(h, bool) else None)
    return tuple(ven)


def _box(hodnoty: Any) -> Optional[Tuple[int, int, int, int]]:
    if not isinstance(hodnoty, list) or len(hodnoty) != 4:
        return None
    try:
        return (int(hodnoty[0]), int(hodnoty[1]), int(hodnoty[2]), int(hodnoty[3]))
    except (TypeError, ValueError):
        return None


def otisk_z_dat(
    data: Dict[str, Any],
    zdroj: str = "",
    meta: Optional[Dict[str, Dict[str, Any]]] = None,
    sha_sceny: str = "",
    sha_meta: Optional[str] = None,
) -> Otisk:
    """Poridi otisk sceny tak, jak prisla z artboardu.

    `sha_sceny`/`sha_meta` dodava `nacti()` z bajtu, ktere prave precetl.
    Bez nich otisk identitu zdroje nezna a `overi_zdroj` nic nepusti.
    """
    jmeno, sc = _prvni_scena(data)
    prvky: List[OtiskPrvku] = []
    for w in sc.get("widgets") or []:
        if not isinstance(w, dict):
            continue
        wid = str(w.get("_widget_id") or "")
        m = (meta or {}).get(wid) or {}
        prvky.append(
            OtiskPrvku(
                widget_id=wid,
                typ=str(w.get("type") or ""),
                x=int(w.get("x") or 0),
                y=int(w.get("y") or 0),
                width=int(w.get("width") or 0),
                height=int(w.get("height") or 0),
                text=str(w.get("text") or ""),
                box=_box(m.get("box")),
                gen=_ctverice(m.get("gen"), OSY),  # type: ignore[arg-type]
                rodic=str(m.get("rodic") or ""),
                v_obsahu=bool(m.get("v_obsahu")),
            )
        )
    return Otisk(
        zdroj=str(zdroj),
        scena=str(sc.get("name") or jmeno),
        # Kdyz prevodnik `device` nedodal, dosadi se tab5 podle rozmeru: tenhle
        # most vede z artboardu TabOSu a nikam jinam.
        device=str(data.get("device") or DEVICE_TAB5),
        width=int(data.get("width") or sc.get("width") or 0),
        height=int(data.get("height") or sc.get("height") or 0),
        prvky=tuple(prvky),
        ma_meta=meta is not None,
        sha_sceny=str(sha_sceny or ""),
        sha_meta=sha_meta,
    )


def nacti_podklad(cesta: pathlib.Path) -> Optional[pygame.Surface]:
    """Nacte PNG podklad. Vraci None, kdyz neni - to neni chyba."""
    cesta = pathlib.Path(cesta)
    if not cesta.exists():
        return None
    try:
        plocha = pygame.image.load(str(cesta))
    except (pygame.error, OSError) as exc:
        logger.warning("podklad %s nelze nacist: %s", cesta, exc)
        return None
    try:
        return plocha.convert()
    except pygame.error:
        # Bez inicializovaneho displeje convert() nejde; syrova plocha staci.
        return plocha


def nacti(cesta_sceny: pathlib.Path, *, s_podkladem: bool = True) -> Most:
    """Nacte `_scena_X.json` (a k ni podklad) do noveho `UIDesigner`.

    Vyhodi `MostError`, kdyz se scena nenacte CELA. `UIDesigner.load_from_json`
    totiz pri chybe jen zaloguje a tise podstrci PRAZDNOU scenu - editor by pak
    ukazal cisty list a vypadalo by to, ze artboard nic neobsahuje.
    """
    cesta_sceny = pathlib.Path(cesta_sceny)
    data, sha_sceny = _cti_json(cesta_sceny)
    meta, sha_meta = _cti_meta(cesta_meta(cesta_sceny))
    if meta is None:
        logger.warning(
            "k %s neni %s - rudy zapis nevyda souradnice generatoru "
            "(vyrobi ji `do_espos.py <artboard> --zapis-scenu`)",
            cesta_sceny.name,
            cesta_meta(cesta_sceny).name,
        )
    otisk = otisk_z_dat(
        data,
        zdroj=cesta_sceny.name,
        meta=meta,
        sha_sceny=sha_sceny,
        sha_meta=sha_meta,
    )

    designer = UIDesigner(otisk.width or 1280, otisk.height or 720)
    designer.load_from_json(str(cesta_sceny))
    if not designer.scenes or designer.current_scene is None:
        raise MostError(f"UIDesigner scenu nenacetl: {cesta_sceny}")

    sc = designer.scenes[designer.current_scene]
    if len(sc.widgets) != len(otisk.prvky):
        # Tichy fallback na prazdnou scenu je presne to, co se nesmi prehlednout.
        raise MostError(
            f"nacteno {len(sc.widgets)} prvku, ale scena jich ma {len(otisk.prvky)} ({cesta_sceny})"
        )

    designer.set_hardware_profile(PROFIL_TAB5)

    podklad = None
    cesta_png = cesta_podkladu(cesta_sceny)
    if s_podkladem:
        podklad = nacti_podklad(cesta_png)

    return Most(
        designer=designer,
        otisk=otisk,
        cesta_sceny=cesta_sceny,
        cesta_podkladu=cesta_png if podklad is not None else None,
        podklad=podklad,
        data=data,
    )


# --------------------------------------------------------------------------- #
# Identita zdroje: zmenil se artboard pod editorem?
# --------------------------------------------------------------------------- #


def overi_zdroj(otisk: Any, cesta_sceny: Any) -> Optional[str]:
    """Vraci duvod, proc se proti tomuhle otisku uz NESMI nic vydat, nebo None.

    Cely rudy zapis stoji na klici `_widget_id` = `trida.index`, kde index je
    poradi v `document.querySelectorAll('*')`. Kdyz se artboard mezitim
    pregeneruje (a staci JEDINY drivejsi prvek navic), indexy se posunou,
    otisk uz popisuje jine prvky a rozdil proti nemu vyda vymyslene zmeny:
    na SvorkaLA jich bylo 62 ze 41 prvku, z toho 14 tvrdilo "posunut" a 24
    "chybi". Patch pritom nikde nerekl, ze se scena zmenila. Tenhle test je
    jedina cesta, jak to poznat konstrukci, a ne shodou okolnosti.

    **FAIL-CLOSED, stejna filozofie jako `tab5_validace.brana_ulozeni`:**
    co nejde overit, se nevydava. Chybejici cesta, otisk bez sha, zmizely
    soubor i necitelny soubor konci stejne jako doslova jiny obsah - duvodem
    nevydat. Zmena mety se pocita taky: cisla generatoru v patchi pochazeji
    z ni, takze "cerstva meta ke stare scene" je tentyz problem.
    """
    if otisk is None:
        return f"{DUVOD_NEOVERENO}: neni otisk artboardu"
    if not cesta_sceny:
        return f"{DUVOD_NEOVERENO}: neni znama cesta k souboru sceny"
    ocekavana = str(getattr(otisk, "sha_sceny", "") or "")
    if not ocekavana:
        return f"{DUVOD_NEOVERENO}: otisk nenese sha256 souboru sceny"

    cesta_sceny = pathlib.Path(cesta_sceny)
    try:
        skutecna = otisk_souboru(cesta_sceny)
        skutecna_meta = otisk_souboru(cesta_meta(cesta_sceny))
    except MostError as exc:
        return f"{DUVOD_NEOVERENO}: {exc}"

    if skutecna is None:
        return f"{DUVOD_ZMENA_ZDROJE} ({cesta_sceny.name} na disku uz neni)"
    if skutecna != ocekavana:
        return (
            f"{DUVOD_ZMENA_ZDROJE} ({cesta_sceny.name}: sha256 pri nacteni "
            f"{ocekavana[:12]}, na disku {skutecna[:12]})"
        )

    ocekavana_meta = getattr(otisk, "sha_meta", None)
    if skutecna_meta == ocekavana_meta:
        return None
    jmeno_meta = cesta_meta(cesta_sceny).name
    if ocekavana_meta is None:
        detail = f"{jmeno_meta} pri nacteni nebyla, ted na disku je"
    elif skutecna_meta is None:
        detail = f"{jmeno_meta} pri nacteni byla, ted na disku neni"
    else:
        detail = (
            f"{jmeno_meta}: sha256 pri nacteni {ocekavana_meta[:12]}, na disku {skutecna_meta[:12]}"
        )
    return f"{DUVOD_ZMENA_ZDROJE} ({detail})"


# --------------------------------------------------------------------------- #
# Dokument pro validator
# --------------------------------------------------------------------------- #


def dokument(most: Most) -> Dict[str, Any]:
    """Slovnik sceny pro `tools.validate_design.validate_data`, VZDY s `device`.

    `UIDesigner.save_to_json` stavi slovnik napevno ze ctyr klicu a `device`
    zahodi. Kdyby se dokument bral odtamtud, validator by spadl na profil
    OLED 256x128 a merit uplne jine meze - bez jedineho hlaseni.
    """
    des = most.designer
    jmeno = des.current_scene
    if not jmeno or jmeno not in des.scenes:
        raise MostError("designer nema aktivni scenu")
    sc = des.scenes[jmeno]
    return {
        "device": most.otisk.device or DEVICE_TAB5,
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


def _widget_na_slovnik(w: Any) -> Dict[str, Any]:
    slovnik: Dict[str, Any] = {
        "type": getattr(w, "type", "label"),
        "x": int(getattr(w, "x", 0) or 0),
        "y": int(getattr(w, "y", 0) or 0),
        "width": int(getattr(w, "width", 0) or 0),
        "height": int(getattr(w, "height", 0) or 0),
        "text": getattr(w, "text", "") or "",
    }
    for klic in ("color_fg", "color_bg", "border", "border_style", "align", "valign"):
        hodnota = getattr(w, klic, None)
        if hodnota is not None:
            slovnik[klic] = hodnota
    wid = getattr(w, "_widget_id", None)
    if wid:
        slovnik["_widget_id"] = wid
    return slovnik


# --------------------------------------------------------------------------- #
# Pripojeni k bezicimu editoru
# --------------------------------------------------------------------------- #


def pripoj(app: Any, most: Most) -> None:
    """Preveze scenu, profil, otisk i podklad do bezici aplikace editoru."""
    app.designer.scenes = dict(most.designer.scenes)
    app.designer.current_scene = most.designer.current_scene
    app.designer.width = most.designer.width
    app.designer.height = most.designer.height
    app.designer.set_hardware_profile(PROFIL_TAB5)
    app.hardware_profile = PROFIL_TAB5

    app.tab5_otisk = most.otisk
    app.tab5_zdroj = most.cesta_sceny
    app.backdrop_surface = most.podklad
    app.show_backdrop = most.podklad is not None

    try:
        app.state.selected_idx = None
        app.state.selected = []
    except AttributeError:
        pass
    try:
        from . import windowing

        windowing.reset_pan(app)
        # Bez window_size si layout dopocita prirozenou velikost pro novy
        # profil - tedy totez, co udela editor pri startu s `--profile
        # tab5_1280x720`. Kdyz se okno na obrazovku nevejde, ohlasi OS
        # VIDEORESIZE, layout se zmensi a nastupuje posouvani platna.
        windowing.rebuild_layout(app, window_size=None, force_scene_size=False)
    except (AttributeError, pygame.error):
        pass
    try:
        app._mark_dirty()
    except AttributeError:
        pass


def prepni_podklad(app: Any) -> bool:
    """Prepinac zobrazeni podkladu. Vraci novy stav."""
    novy = not bool(getattr(app, "show_backdrop", True))
    app.show_backdrop = novy
    try:
        app._mark_dirty()
    except AttributeError:
        pass
    return novy
