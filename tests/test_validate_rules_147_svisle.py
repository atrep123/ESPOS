"""Rule 147 a SVISLA cara (fixtury `tab5_cary_svisle_*.json`).

DIRA (rdf-overeni 7B/7F, mapa mezer A5): sit analyzatoru (7 svislych car
x=271..1105) i sloupce razitka (x=330/640/950, pas 612..700) jsou SVISLE.
Jediny zivy nalez Rule 147 je vodorovny (`tab5_cary_vady.json`), most kitu
svisle cary do `navrh.cary` nevozi (`CARA_MIN_W = 200`) - a mapa mezer
tvrdila, ze validator sam je k orientaci lhostejny. NENI, a je to tu
ZMERENO, ne opsano:

    _r147_nalezy, r. 2638:
        if cy - y < R147_ODSTUP_PX or y2 - cy2 < R147_ODSTUP_PX:
            continue

Podminka zada, aby cara lezela SVISLE UVNITR inkoustu (aspon 1 px pod
horni a nad dolni hranou). Svisla cara [640, 612, 1, 88] (pas razitka)
protina inkoust 640..652 CELY - cy - y = -28 - a pravidlo ji preskoci
jako "dotek shora". Kratka svisla cara [640, 641, 1, 10] UVNITR tehoz
inkoustu nalez dostane. Tataz cara o 2 px delsi = ticho. To je vada
validatoru, ne fixtury: preskrtnuti se nestane mene preskrtnutim tim, ze
cara pokracuje nad a pod pismo.

Podle pravidel kampane se vada v produkcnim kodu NEOPRAVUJE v testu:
pozitivni trida je `xfail(strict=True)` s odkazem na testy/kolo1.md, a az
ji nekdo opravi, strict xfail zcervena a tenhle text se smaze.

Co tu je (obe tridy, hranice, kontrolni skupina):

* fixtura VADY (svisla cara pres inkoust)      -> ma hlasit  [xfail strict]
* fixtura CISTE (tataz cara 10 px vlevo)       -> mlci       [zeleny]
* kratka svisla cara uvnitr inkoustu           -> hlasi      [zeleny; dukaz,
  ze pravidlo svislou caru jako takovou NEODMITA - kontrolni skupina]
* tataz cara prodlouzena nad i pod inkoust     -> ma hlasit  [xfail strict]
* hranice na vodorovne ose (x = 599 vs 600)    -> mlci / hlasi [zeleny]
* profil oled256 (bez delicich car)            -> mlci       [zeleny]
* mutace (testy/test_mutace_pravidel.py, `R147_odstup_nekonecny`): kratka
  svisla cara uvnitr inkoustu zmlkne -> `test_svisla_cara_uvnitr_inkoustu_hlasi`
  cerveny.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.validate_design import (
    PROFILE_OLED256,
    PROFILE_TAB5,
    R147_ODSTUP_PX,
    ZNACKA_R147,
    validate_data,
    validate_file,
)

FL = "test"
FIXTURY = pathlib.Path(__file__).parent / "fixtures"
SVISLE_CISTE = FIXTURY / "tab5_cary_svisle_ciste.json"
SVISLE_VADY = FIXTURY / "tab5_cary_svisle_vady.json"

# Inkoust popisku z fixtury a sloupec razitka, ktery pres nej vede.
INKOUST = (600, 640, 100, 12)
SLOUPEC_PRES = [640, 612, 1, 88]  # y 612..700, inkoust 640..652 lezi uvnitr
SLOUPEC_VEDLE = [590, 612, 1, 88]

VADA_R147_SVISLE = (
    "SKUTECNA VADA validatoru: `_r147_nalezy` preskoci caru, ktera zacina NAD "
    "inkoustem (`cy - y < R147_ODSTUP_PX`), takze svisla cara protinajici text "
    "cely je 'dotek shora' a mlci; kratka svisla cara uvnitr tehoz inkoustu "
    "nalez dostane. Neopravovat v testu; viz testy/kolo1.md (A5)."
)


def _w(wid, x, y, ww, hh, *, text="kanal 7 spoust", t="label", **kw):
    d = {
        "type": t,
        "x": x,
        "y": y,
        "width": ww,
        "height": hh,
        "text": text,
        "color_fg": "#e6e1ce",
        "color_bg": "#14170f",
        "align": "left",
        "valign": "middle",
        "_widget_id": wid,
    }
    d.update(kw)
    return d


def _make(widgets, *, cary, scene_w=1280, scene_h=720, device="tab5"):
    scene = {"width": scene_w, "height": scene_h, "widgets": widgets, "navrh": {"cary": cary}}
    return {"device": device, "scenes": {"main": scene}}


def _r147(data):
    return [
        i.message
        for i in validate_data(data, file_label=FL, warnings_as_errors=False)
        if ZNACKA_R147 in i.message
    ]


def _r147_soubor(cesta):
    return [i.message for i in validate_file(cesta, warnings_as_errors=False) if ZNACKA_R147 in i.message]


# --------------------------------------------------------------------------- #
# Fixtury: nosic je legalni a dvojice se lisi jen polohou cary
# --------------------------------------------------------------------------- #


def test_fixtury_svisle_projdou_schematem_a_lisi_se_jen_x_cary():
    for cesta in (SVISLE_CISTE, SVISLE_VADY):
        chyby = [i.message for i in validate_file(cesta, warnings_as_errors=False) if "schema" in i.message]
        assert chyby == [], cesta.name
    ciste = json.loads(SVISLE_CISTE.read_text(encoding="utf-8"))
    vady = json.loads(SVISLE_VADY.read_text(encoding="utf-8"))
    assert ciste["scenes"]["main"]["navrh"]["cary"] == [SLOUPEC_VEDLE]
    assert vady["scenes"]["main"]["navrh"]["cary"] == [SLOUPEC_PRES]
    ciste["scenes"]["main"]["navrh"]["cary"] = vady["scenes"]["main"]["navrh"]["cary"]
    assert ciste == vady, "dvojice se ma lisit JEN polohou cary"
    w = vady["scenes"]["main"]["widgets"][0]
    assert (w["x"], w["y"], w["width"], w["height"]) == INKOUST
    # Cara je opravdu svisla a opravdu inkoust protina (aritmetika, ne pravidlo).
    cx, cy, cw, ch = SLOUPEC_PRES
    x, y, ww, hh = INKOUST
    assert cw == 1 and ch > hh
    assert x <= cx < x + ww and cy < y and cy + ch > y + hh


def test_fixtura_svisle_ciste_mlci():
    """Negativni trida: sloupec 10 px vlevo od prvniho pixelu pisma."""
    assert _r147_soubor(SVISLE_CISTE) == []


@pytest.mark.xfail(strict=True, reason=VADA_R147_SVISLE)
def test_fixtura_svisle_vady_ma_hlasit_sloupec_razitka_pres_text():
    """Pozitivni trida: sloupec razitka x=640 jde skrz inkoust 600..700."""
    nalezy = _r147_soubor(SVISLE_VADY)
    assert len(nalezy) == 1
    assert "cara 640,612 1x88 vede pres text 'kanal 7 spoust' (inkoust 600,640 100x12)" in nalezy[0]


# --------------------------------------------------------------------------- #
# Kontrolni skupina: svislou caru pravidlo zna - jen ne tu, ktera presahuje
# --------------------------------------------------------------------------- #


def test_svisla_cara_uvnitr_inkoustu_hlasi():
    """Kratky svisly usek [640, 641, 1, 10] lezi cely v inkoustu 640..652.

    Dukaz, ze `_r147_nalezy` svislou caru jako takovou neodmita - a cil
    mutace `R147_odstup_nekonecny` (test_mutace_pravidel.py)."""
    d = _make([_w("hodnota.7", *INKOUST)], cary=[[640, 641, 1, 10]])
    nalezy = _r147(d)
    assert len(nalezy) == 1
    assert "cara 640,641 1x10 vede pres text 'kanal 7 spoust' (inkoust 600,640 100x12)" in nalezy[0]


@pytest.mark.xfail(strict=True, reason=VADA_R147_SVISLE)
def test_tataz_cara_prodlouzena_o_pixel_nad_i_pod_inkoust_ma_hlasit_taky():
    """Cara 639..653 preskrtava vic, ne min, nez cara 641..651."""
    d = _make([_w("hodnota.7", *INKOUST)], cary=[[640, 640 - 1, 1, 12 + 2]])
    assert len(_r147(d)) == 1


def test_prodlouzeni_cary_je_dnes_presne_ta_mez_kde_pravidlo_zmlkne():
    """Doklad vady jako MERENI (zeleny, dokud vada trva; po oprave ho smazat
    spolu s obema xfaily): delka cary rozhoduje, poloha ne.

    Kdyby tenhle test zcervenal a xfaily zustaly zelene, znamena to, ze
    se pravidlo zmenilo jinak, nez xfaily cekaji - a ma se to precist."""
    x, y, ww, hh = INKOUST
    uvnitr = _make([_w("h", *INKOUST)], cary=[[640, y + R147_ODSTUP_PX, 1, hh - 2 * R147_ODSTUP_PX]])
    o_pixel_vic = _make(
        [_w("h", *INKOUST)],
        cary=[[640, y + R147_ODSTUP_PX - 1, 1, hh - 2 * R147_ODSTUP_PX + 1]],
    )
    assert len(_r147(uvnitr)) == 1
    assert _r147(o_pixel_vic) == [], "vada opravena? smaz tento test a oba xfaily"


# --------------------------------------------------------------------------- #
# Hranice na vodorovne ose a profil
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("cx", "ceka_nalez"),
    [
        (599, False),  # sloupec 1 px vlevo od prvniho pixelu inkoustu
        (600, True),  # sloupec na prvnim pixelu inkoustu
        (699, True),  # na poslednim pixelu
        (700, False),  # 1 px za poslednim
    ],
)
def test_hranice_svisle_cary_na_vodorovne_ose(cx, ceka_nalez):
    """Meri se kratkou carou uvnitr inkoustu (ta dnes funguje), aby hranice
    vodorovneho prekryvu nebyla zastinena vadou svisleho presahu."""
    d = _make([_w("h", *INKOUST)], cary=[[cx, 641, 1, 10]])
    assert (len(_r147(d)) == 1) is ceka_nalez


def test_svisla_cara_mimo_profil_tab5_mlci():
    assert PROFILE_TAB5.delici_cary is True
    assert PROFILE_OLED256.delici_cary is False
    d = _make([_w("h", 40, 40, 100, 12)], cary=[[60, 41, 1, 10]], scene_w=256, scene_h=128, device="oled256")
    assert _r147(d) == []
    d["device"] = "tab5"
    d["scenes"]["main"]["width"], d["scenes"]["main"]["height"] = 1280, 720
    assert len(_r147(d)) == 1


def test_dva_behy_tyz_vysledek():
    a = [i.message for i in validate_file(SVISLE_VADY, warnings_as_errors=False)]
    b = [i.message for i in validate_file(SVISLE_VADY, warnings_as_errors=False)]
    assert a == b
