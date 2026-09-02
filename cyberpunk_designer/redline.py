"""Rudy zapis - patch v souradnicich generatoru TabOSu.

Editor navrh NEPREPISUJE. Navrhy TabOSu nejsou dokument, jsou to vygenerovane
HTML a zdrojem pravdy zustavaji generatory `navrh-appky/gen_*.py`. Kdyz Filip
prvek posune, editor spocita rozdil proti OTISKU (stav sceny pri nacteni,
`tab5_most.Otisk`) a vyda **rudy zapis**: strojove citelny JSON + citelny text
v souradnicich generatoru. Promitnuti do `gen_*.py` zustava krokem cloveka
nebo agenta - protoze prave tam je rozhodnuti, ktere pixel nezna.

ODKUD SE BERE "SOURADNICE GENERATORU" (a proc uz ne odectenim)
--------------------------------------------------------------
Puvodne se prevadelo odectenim `(PAD 20, OBSAH_Y 68)` od souradnice ve scene.
Revize A to zmerila na sesti artboardech a vyvratila dvakrat:

* **osa Y u popisku.** `do_espos.MERIC` u typu `label` nahrazuje `y`/`height`
  rozsahem INKOUSTU (metriky canvasu, podlaha 8 px), ne ramecku. Odectenim
  OBSAH_Y z inkoustu vznikne cislo, ktere v generatoru nikde neni - **449 ze
  451** merenych popisku. Doslovny pripad: SvorkaHex `bajt.19` ma
  `top: 60`, scena `y = 131`, odecet dal 63.
* **osa X u prvku, jejichz `offsetParent` neni `.obsah`.** Inline `left` je
  relativni k TOMU rodici. SvorkaCislice `mez.49` ma `left: 16` a rodice
  `karta`; odecet dal 850. Chyba az 834 px.

Rudy zapis proto zadne cislo NEDOPOCITAVA. Bere hodnotu, kterou generator
DOSLOVA zapsal do inline stylu (`style.left/top/width/height`) a kterou
prevodnik odlozil do `_meta_X.json` (`do_espos.py --zapis-scenu`). Novou
hodnotu sklada jako `inline + zmereny rozdil`; rozdil je spravny, protoze obe
strany mereni jsou tataz (to revize A potvrdila).

**Kdyz doklad neni, cislo se nevyda.** Prvek polohovany CSS tridou (zahlavi
z `ram.zahlavi()`) inline styl nema, novy prvek z editoru take ne, a scena
bez `_meta_X.json` nema doklad zadny. V takovem pripade je v patchi `null`,
osa je vyjmenovana v `neprevedeno` a `platny` je `false`. Radeji zadne cislo
nez vymyslene - a nikdy vymyslene cislo s `platny: true`.

Dalsi dve veci, na kterych to stoji:

* **Cislo se nedosazuje, klade se otazka.** Souradnice v generatoru jsou
  VZTAHY nad konstantami (osm tlacitek si deli zbytek sirky, aby prava hrana
  pasu sedla na ABS 1224). Kdyz se do generatoru dosadi cislo, invariant tise
  padne. Kandidaty hleda `navrh-appky/najdi_puvod.py` staticky pres `ast`.
* **Editor vidi jen cast navrhu.** Prevodnik `do_espos.py` je ztratovy: ze
  133 prvku artboardu SvorkaLA projde 41. Svorky D0-D15 ve scene VUBEC
  nejsou. Rudy zapis o nich tedy nemuze nic rict a nesmi budit dojem, ze je
  zkontroloval - proto to stoji v hlavicce kazdeho vydaneho patche.

Klic patche je `_widget_id`, ktery prevodnik sklada jako `trida.index`, kde
index je poradi v `document.querySelectorAll('*')`. Posune se, jakmile
generator pribere JAKYKOLI drivejsi prvek - patch tedy plati v ramci jedne
relace nad jednim otiskem. Kdyz je `_widget_id` prazdne nebo se opakuje,
prvek se do patche nedostane a duvod se vypise mezi varovanimi.

A prave proto `vydej` pred vydanim OVERI, ze soubor sceny na disku ma tentyz
sha256 jako pri nacteni (`tab5_most.overi_zdroj`). Bez toho staci pregenerovat
artboard pod bezicim editorem a patch vyda vymyslene zmeny, ktere navic
vypadaji hodnoverne: merenim na SvorkaLA jich bylo 62 ze 41 prvku, z toho 14
tvrdilo "prvek byl posunut" a 24 "prvek byl smazan" - a nikde ani slovo o tom,
ze se scena pod rukama zmenila. Neshoda otisku = zadny patch.
"""

from __future__ import annotations

import json
import logging
import pathlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

PREDPONA_ZAPISU = "_rudy_zapis_"
PREDPONA_SCENY = "_scena_"

STAV_POSUNUT = "posunut"
STAV_PRIDAN = "pridan"
STAV_CHYBI = "chybi"

OSY = ("x", "y", "w", "h")

# Kontejner navrhu. `offsetParent` prvku, u ktereho je inline `left/top`
# relativni k pocatku obsahove plochy; u jineho rodice je cislo relativni
# k NEMU a patch to musi rict nahlas.
RODIC_OBSAHU = "obsah"

Obdelnik = Tuple[int, int, int, int]
Ctverice = Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]

BEZ_HODNOT: Ctverice = (None, None, None, None)


class RedlineError(Exception):
    """Rudy zapis nelze vydat."""


def artboard_ze_zdroje(zdroj: str) -> str:
    """`_scena_SvorkaLA.dc.json` -> `SvorkaLA.dc`."""
    jmeno = pathlib.Path(str(zdroj)).name
    if jmeno.startswith(PREDPONA_SCENY):
        jmeno = jmeno[len(PREDPONA_SCENY) :]
    if jmeno.endswith(".json"):
        jmeno = jmeno[: -len(".json")]
    return jmeno


# --------------------------------------------------------------------------- #
# Zmena a cely zapis
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Zmena:
    """Jeden rozdil proti otisku."""

    widget_id: str
    typ: str
    text: str
    stav: str
    pred: Optional[Obdelnik] = None
    po: Optional[Obdelnik] = None
    # Inline styl generatoru (`style.left/top/width/height`) z `_meta_X.json`.
    # `None` v ose = generator tam zadne cislo nezapsal.
    gen: Ctverice = BEZ_HODNOT
    rodic: str = ""
    ma_meta: bool = False

    @property
    def pred_gen(self) -> Ctverice:
        """Souradnice generatoru PRED zmenou - doslova inline styl."""
        if self.stav == STAV_PRIDAN:
            return BEZ_HODNOT
        return self.gen

    @property
    def po_gen(self) -> Ctverice:
        """Souradnice generatoru PO zmene = inline styl + zmereny rozdil.

        Absolutni cislo se nedopocitava ze sceny (to byl nalez A1/A2); bere se
        cislo generatoru a pricte se k nemu rozdil, ktery je v obou soustavach
        tentyz, protoze obe strany mereni jsou tataz.
        """
        if self.stav != STAV_POSUNUT:
            return BEZ_HODNOT
        posun = self.posun
        return tuple(  # type: ignore[return-value]
            None if h is None else int(h) + int(posun[i]) for i, h in enumerate(self.gen)
        )

    @property
    def neprevedene_osy(self) -> Tuple[str, ...]:
        """Osy, pro ktere doklad z generatoru NENI - cislo se u nich nevyda."""
        if self.stav == STAV_PRIDAN:
            return OSY
        return tuple(jm for i, jm in enumerate(OSY) if self.gen[i] is None)

    @property
    def prevoditelny(self) -> bool:
        """Jsou VSECHNY osy dolozene inline stylem generatoru?

        `platny: true` v patchi tedy znamena "kazde vypsane cislo pochazi
        z generatoru", ne "nejak jsme to spocitali".
        """
        return not self.neprevedene_osy

    @property
    def cizi_rodic(self) -> bool:
        """Je inline cislo relativni k necemu jinemu nez ke kontejneru obsahu?"""
        return bool(self.rodic) and self.rodic != RODIC_OBSAHU

    @property
    def posun(self) -> Obdelnik:
        """(dx, dy, dw, dh) v obrazovce. Rozdil je v obou soustavach tentyz."""
        if self.pred is None or self.po is None:
            return (0, 0, 0, 0)
        return tuple(int(b) - int(a) for a, b in zip(self.pred, self.po, strict=True))  # type: ignore[return-value]


@dataclass(frozen=True)
class RudyZapis:
    """Cely patch pro jeden artboard."""

    artboard: str
    scena: str
    device: str
    width: int
    height: int
    zmeny: Tuple[Zmena, ...] = ()
    varovani: Tuple[str, ...] = ()
    chyb: int = 0
    warn: int = 0
    pocty_nalezu: Optional[Dict[str, int]] = None
    videno_prvku: int = 0
    ma_meta: bool = False

    @property
    def prazdny(self) -> bool:
        return not self.zmeny


# --------------------------------------------------------------------------- #
# Rozdil proti otisku
# --------------------------------------------------------------------------- #


def _prvek_ze_sceny(w: Any) -> Tuple[str, str, str, Obdelnik]:
    return (
        str(getattr(w, "_widget_id", "") or ""),
        str(getattr(w, "type", "") or ""),
        str(getattr(w, "text", "") or ""),
        (
            int(getattr(w, "x", 0) or 0),
            int(getattr(w, "y", 0) or 0),
            int(getattr(w, "width", 0) or 0),
            int(getattr(w, "height", 0) or 0),
        ),
    )


def _jedinecne(
    dvojice: Sequence[Tuple[str, Any]],
) -> Tuple[Dict[str, Any], List[str], set]:
    """Mapa id -> prvek, duvody vynechani a mnozina nejednoznacnych id."""
    mapa: Dict[str, Any] = {}
    vicekrat: List[str] = []
    prazdna = 0
    for wid, prvek in dvojice:
        if not wid:
            prazdna += 1
            continue
        if wid in mapa:
            if wid not in vicekrat:
                vicekrat.append(wid)
            continue
        mapa[wid] = prvek
    duvody: List[str] = []
    if prazdna:
        duvody.append(f"{prazdna} prvku bez `_widget_id` - nelze je adresovat, vynechany")
    for wid in vicekrat:
        mapa.pop(wid, None)
        duvody.append(f"`{wid}` je ve scene vicekrat - nejednoznacny klic, vynechan")
    return mapa, duvody, set(vicekrat)


def _gen_z_prvku(p: Any) -> Ctverice:
    hodnoty = getattr(p, "gen", None)
    if not hodnoty:
        return BEZ_HODNOT
    return tuple(None if h is None else int(h) for h in tuple(hodnoty)[:4])  # type: ignore[return-value]


def rozdil(otisk: Any, widgets: Sequence[Any]) -> Tuple[Tuple[Zmena, ...], Tuple[str, ...]]:
    """Porovna aktualni scenu proti otisku. Vraci zmeny a varovani."""
    stare, duvody_s, sporne_s = _jedinecne([(p.widget_id, p) for p in getattr(otisk, "prvky", ())])
    prevedene = [_prvek_ze_sceny(w) for w in widgets]
    nove, duvody_n, sporne_n = _jedinecne([(t[0], t) for t in prevedene])

    # Sporne id musi vypadnout z OBOU stran. Kdyby vypadlo jen z nove sceny,
    # hlasil by se prvek jako "chybi" - tedy jako smazany. To je horsi nez
    # mlceni: patch by tvrdil neco, co se nestalo.
    for wid in sporne_s | sporne_n:
        stare.pop(wid, None)
        nove.pop(wid, None)

    ma_meta = bool(getattr(otisk, "ma_meta", False))
    zmeny: List[Zmena] = []
    # Poradi drzi otisk: patch se pak da cist vedle artboardu shora dolu.
    for wid, p in stare.items():
        gen = _gen_z_prvku(p)
        rodic = str(getattr(p, "rodic", "") or "")
        if wid not in nove:
            zmeny.append(
                Zmena(
                    widget_id=wid,
                    typ=p.typ,
                    text=p.text,
                    stav=STAV_CHYBI,
                    pred=(p.x, p.y, p.width, p.height),
                    gen=gen,
                    rodic=rodic,
                    ma_meta=ma_meta,
                )
            )
            continue
        _, typ, text, rect = nove[wid]
        pred = (p.x, p.y, p.width, p.height)
        if rect != pred:
            zmeny.append(
                Zmena(
                    widget_id=wid,
                    typ=typ,
                    text=text,
                    stav=STAV_POSUNUT,
                    pred=pred,
                    po=rect,
                    gen=gen,
                    rodic=rodic,
                    ma_meta=ma_meta,
                )
            )
    for wid, (_, typ, text, rect) in nove.items():
        if wid not in stare:
            zmeny.append(
                Zmena(widget_id=wid, typ=typ, text=text, stav=STAV_PRIDAN, po=rect, ma_meta=ma_meta)
            )

    return tuple(zmeny), tuple(duvody_s + duvody_n)


VAROVANI_BEZ_META = (
    "scena nema `_meta_X.json` - souradnice generatoru NEVYDANY u zadneho prvku. "
    "Meta vyrabi `python do_espos.py <artboard> --zapis-scenu`; bez ni se cislo "
    "generatoru nema z ceho dolozit a dopocitat ho ze sceny je prokazatelne "
    "spatne (revize A, nalezy A1/A2)."
)


def vytvor(otisk: Any, widgets: Sequence[Any], vysledek: Any = None) -> RudyZapis:
    """Postavi rudy zapis z otisku a aktualni sceny."""
    if otisk is None:
        raise RedlineError("neni otisk artboardu - scena nebyla nactena mostem tab5")
    zmeny, varovani = rozdil(otisk, widgets)
    varovani = list(varovani)
    ma_meta = bool(getattr(otisk, "ma_meta", False))

    if zmeny and not ma_meta:
        varovani.append(VAROVANI_BEZ_META)
    elif ma_meta:
        chybi = [(z.widget_id, z.neprevedene_osy) for z in zmeny if z.neprevedene_osy]
        if chybi:
            varovani.append(
                "generator tyhle osy inline stylem nezapsal, cislo se u nich NEVYDAVA: "
                + "; ".join(f"{wid} [{','.join(osy)}]" for wid, osy in chybi)
            )
    cizi = sorted({z.rodic for z in zmeny if z.cizi_rodic})
    if cizi:
        varovani.append(
            "cislo generatoru je u nekterych prvku relativni k jinemu rodici nez "
            f"`.{RODIC_OBSAHU}` ({', '.join('.' + c for c in cizi)}) - hledej ho "
            "v tom bloku generatoru, ne v souradnicich obsahu"
        )

    return RudyZapis(
        artboard=artboard_ze_zdroje(getattr(otisk, "zdroj", "") or ""),
        scena=str(getattr(otisk, "scena", "") or ""),
        device=str(getattr(otisk, "device", "") or ""),
        width=int(getattr(otisk, "width", 0) or 0),
        height=int(getattr(otisk, "height", 0) or 0),
        zmeny=zmeny,
        varovani=tuple(varovani),
        chyb=int(getattr(vysledek, "chyb", 0) or 0),
        warn=int(getattr(vysledek, "varovani", 0) or 0),
        pocty_nalezu=dict(getattr(vysledek, "pocty", {}) or {}) if vysledek is not None else None,
        videno_prvku=len(getattr(otisk, "prvky", ()) or ()),
        ma_meta=ma_meta,
    )


# --------------------------------------------------------------------------- #
# Vystup
# --------------------------------------------------------------------------- #

POZNAMKA_ZTRATOVOST = (
    "Editor vidi jen prvky, ktere prosly prevodnikem do_espos.py (u SvorkaLA "
    "41 ze 133). O prvcich, ktere v otisku nejsou (napr. jednotlive svorky "
    "D0-D15), tenhle zapis NERIKA NIC - nebyly zkontrolovany."
)
POZNAMKA_PREVOD = (
    "Cislo v radku `generator` je DOSLOVA inline styl z generatoru "
    "(_meta_X.json), nova hodnota = inline styl + zmereny rozdil. Nic se "
    "nedopocitava ze sceny: u popisku je scenove `y` rozsah inkoustu, ne "
    "ramecku, a u prvku s jinym rodicem nez .obsah neplati posun o (20, 68). "
    "Kde inline styl neni, je v patchi `null` a osa stoji v `neprevedeno`."
)
POZNAMKA_VZTAHY = (
    "Cislo nedosazuj. Souradnice v generatoru jsou vztahy nad konstantami; "
    "otazka zni, KTERA konstanta se zmenila. Kandidaty hleda najdi_puvod.py."
)

POZNAMKY = (POZNAMKA_ZTRATOVOST, POZNAMKA_PREVOD, POZNAMKA_VZTAHY)


def na_json(zapis: RudyZapis) -> Dict[str, Any]:
    """Strojove citelny tvar patche."""
    return {
        "format": "rudy-zapis/2",
        "artboard": zapis.artboard,
        "artboard_soubor": f"{zapis.artboard}.html" if zapis.artboard else "",
        "scena": zapis.scena,
        "device": zapis.device,
        "obrazovka": {"width": zapis.width, "height": zapis.height},
        "prevod": {
            "zdroj": "inline styl generatoru (_meta_X.json z do_espos.py --zapis-scenu)",
            "meta_k_dispozici": zapis.ma_meta,
        },
        "validace": {
            "error": zapis.chyb,
            "warn": zapis.warn,
            "tridy": zapis.pocty_nalezu,
        },
        "videno_prvku": zapis.videno_prvku,
        "poznamky": list(POZNAMKY),
        "varovani": list(zapis.varovani),
        "zmeny": [_zmena_na_json(z) for z in zapis.zmeny],
    }


def _rect_json(rect: Optional[Obdelnik]) -> Optional[Dict[str, int]]:
    if rect is None:
        return None
    return {"x": rect[0], "y": rect[1], "w": rect[2], "h": rect[3]}


def _gen_json(hodnoty: Ctverice) -> Optional[Dict[str, Optional[int]]]:
    if all(h is None for h in hodnoty):
        return None
    return {jm: hodnoty[i] for i, jm in enumerate(OSY)}


def _zmena_na_json(z: Zmena) -> Dict[str, Any]:
    dx, dy, dw, dh = z.posun
    return {
        "widget_id": z.widget_id,
        "typ": z.typ,
        "text": z.text,
        "stav": z.stav,
        "obrazovka": {"pred": _rect_json(z.pred), "po": _rect_json(z.po)},
        "generator": {
            # `platny: true` = kazde cislo v `pred`/`po` pochazi z inline stylu
            # generatoru. Jakmile chybi byt jedna osa, je to false a osa stoji
            # v `neprevedeno` - vymyslene cislo se nevyda nikdy.
            "platny": z.prevoditelny,
            "neprevedeno": list(z.neprevedene_osy),
            "rodic": z.rodic,
            "pred": _gen_json(z.pred_gen),
            "po": _gen_json(z.po_gen),
        },
        "posun": {"dx": dx, "dy": dy, "dw": dw, "dh": dh},
    }


def _osa(jmeno: str, pred: Optional[int], po: Optional[int]) -> str:
    if pred is None and po is None:
        return f"{jmeno} neprevedeno"
    if pred is None:
        return f"{jmeno} -> {po}"
    if po is None:
        return f"{jmeno} {pred}"
    d = po - pred
    return f"{jmeno} {pred} -> {po} ({d:+d})" if d else f"{jmeno} {pred}"


def _radek_obrazovky(pred: Optional[Obdelnik], po: Optional[Obdelnik]) -> str:
    casti = [
        _osa(jm, None if pred is None else pred[i], None if po is None else po[i])
        for i, jm in enumerate(OSY)
    ]
    return "    obrazovka: " + "   ".join(casti)


def _radek_generatoru(z: Zmena) -> str:
    pred, po = z.pred_gen, z.po_gen
    if all(h is None for h in pred) and all(h is None for h in po):
        return "    generator: neprevedeno (generator k tomuhle prvku zadne inline cislo nezapsal)"
    casti = [_osa(jm, pred[i], po[i]) for i, jm in enumerate(OSY)]
    radek = "    generator: " + "   ".join(casti)
    if z.rodic:
        radek += f"      [rodic .{z.rodic}]"
    return radek


def jako_text(zapis: RudyZapis) -> str:
    """Citelny tvar patche - to, co si precte clovek nebo agent."""
    r: List[str] = []
    r.append(f"RUDY ZAPIS  -  {zapis.artboard or '(neznamy artboard)'}")
    r.append("=" * 72)
    r.append(f"artboard : {zapis.artboard}.html" if zapis.artboard else "artboard : ?")
    r.append(f"scena    : {zapis.scena}    device: {zapis.device}    {zapis.width}x{zapis.height}")
    r.append(
        "prevod   : inline styl generatoru z _meta_X.json"
        + ("" if zapis.ma_meta else "   -- CHYBI, cisla generatoru nevydana")
    )
    tridy = ", ".join(f"{k} {v}" for k, v in sorted((zapis.pocty_nalezu or {}).items()))
    r.append(
        f"validace : {zapis.chyb} ERROR, {zapis.warn} WARN" + (f"   ({tridy})" if tridy else "")
    )
    r.append(f"prvku v otisku: {zapis.videno_prvku}")
    r.append(f"zmen     : {len(zapis.zmeny)}")
    r.append("")

    if not zapis.zmeny:
        r.append("Zadna zmena proti otisku - neni co vydat.")
    for i, z in enumerate(zapis.zmeny, 1):
        r.append(f"[{i}] {z.widget_id}   {z.typ}   {z.text[:40]!r}   ({z.stav})")
        r.append(_radek_obrazovky(z.pred, z.po))
        r.append(_radek_generatoru(z))
        r.append("")

    if zapis.varovani:
        r.append("VAROVANI:")
        r.extend(f"  ! {v}" for v in zapis.varovani)
        r.append("")
    r.append("POZNAMKY:")
    r.extend(f"  * {p}" for p in POZNAMKY)
    return "\n".join(r) + "\n"


def cesty_vystupu(slozka: pathlib.Path, artboard: str) -> Tuple[pathlib.Path, pathlib.Path]:
    slozka = pathlib.Path(slozka)
    zaklad = PREDPONA_ZAPISU + (artboard or "zapis")
    return (slozka / f"{zaklad}.json", slozka / f"{zaklad}.txt")


def uloz(zapis: RudyZapis, slozka: pathlib.Path) -> Tuple[pathlib.Path, pathlib.Path]:
    """Zapise JSON i citelny text vedle sceny. Vraci obe cesty."""
    js, txt = cesty_vystupu(slozka, zapis.artboard)
    js.write_text(json.dumps(na_json(zapis), ensure_ascii=False, indent=1), encoding="utf-8")
    txt.write_text(jako_text(zapis), encoding="utf-8")
    return js, txt


# --------------------------------------------------------------------------- #
# Hak do editoru
# --------------------------------------------------------------------------- #


def vydej(app: Any, slozka: Optional[pathlib.Path] = None) -> Optional[RudyZapis]:
    """Vyda rudy zapis z bezici aplikace. `None`, kdyz nema z ceho nebo nesmi.

    Brany jsou dve a obe fail-closed:

    1. **Zdroj se pod editorem nezmenil.** Soubor sceny (a mety) na disku musi
       mit tentyz sha256 jako v okamziku nacteni. Jinak uz otisk popisuje jine
       prvky - `_widget_id` je `trida.index` - a rozdil proti nemu je
       vymysleny. Nevydat a rict cloveku, at nacte znovu.
    2. **Mereni.** Tataz brana jako u ulozeni a jako v `do_espos.py`:
       **jakykoli ERROR = nevydat**, a kdyz se NEZMERILO, take nevydat. Zapis,
       ktery vznikl nad scenou s chybou, by agent promitl do generatoru
       a chyba by se stala soucasti navrhu.
    """
    from . import tab5_most, tab5_validace

    otisk = getattr(app, "tab5_otisk", None)
    if otisk is None:
        _stav(app, "rudy zapis: neni pripojena scena artboardu (tab5_most.nacti)")
        return None

    zdroj = getattr(app, "tab5_zdroj", None)
    duvod = tab5_most.overi_zdroj(otisk, zdroj)
    if duvod:
        logger.warning("rudy zapis NEVYDAN: %s", duvod)
        _stav(app, f"rudy zapis: NEVYDAN - {duvod}")
        return None

    duvod = tab5_validace.brana_ulozeni(app)
    if duvod:
        _stav(app, f"rudy zapis: NEVYDAN - {duvod}")
        return None

    sc = app.designer.scenes[app.designer.current_scene]
    zapis = vytvor(otisk, sc.widgets, getattr(app, "tab5_vysledek", None))
    if zapis.prazdny:
        _stav(app, "rudy zapis: zadna zmena proti otisku")
        return zapis

    if slozka is None:
        slozka = pathlib.Path(zdroj).parent if zdroj else pathlib.Path.cwd()
    try:
        js, _txt = uloz(zapis, slozka)
    except OSError as exc:
        logger.warning("rudy zapis nelze zapsat do %s: %s", slozka, exc)
        _stav(app, f"rudy zapis: zapis selhal ({exc})")
        return None
    _stav(app, f"rudy zapis: {len(zapis.zmeny)} zmen -> {js.name}")
    return zapis


def _stav(app: Any, text: str) -> None:
    try:
        app._set_status(text, ttl_sec=4.0)
    except (AttributeError, TypeError):
        logger.debug("editor nema _set_status")
