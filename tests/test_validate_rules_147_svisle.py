"""Rule 147 a svisla cara (fixtury `tab5_cary_svisle_*.json`).

Cara protinajici inkoust hlasi nalez i pri prodlouzeni nad a pod text.
Testy drzi vadnou/cistou fixturu, kratky usek, presah, pixelove hranice,
profilove gatovani a determinismus. Regrese z 27. 9. 2026 nahrazuji dve
strict xfail znacky, ktere dokladaly chybne odmitnuti presahujici cary.
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
    return [
        i.message
        for i in validate_file(cesta, warnings_as_errors=False)
        if ZNACKA_R147 in i.message
    ]


# --------------------------------------------------------------------------- #
# Fixtury: nosic je legalni a dvojice se lisi jen polohou cary
# --------------------------------------------------------------------------- #


def test_fixtury_svisle_projdou_schematem_a_lisi_se_jen_x_cary():
    for cesta in (SVISLE_CISTE, SVISLE_VADY):
        chyby = [
            i.message
            for i in validate_file(cesta, warnings_as_errors=False)
            if "schema" in i.message
        ]
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


def test_tataz_cara_prodlouzena_o_pixel_nad_i_pod_inkoust_ma_hlasit_taky():
    """Cara 639..653 preskrtava vic, ne min, nez cara 641..651."""
    d = _make([_w("hodnota.7", *INKOUST)], cary=[[640, 640 - 1, 1, 12 + 2]])
    assert len(_r147(d)) == 1


def test_prodlouzeni_cary_neztrati_nalez():
    """Prodlouzeni cary k horni hrane zachova prunik s inkoustem."""
    x, y, ww, hh = INKOUST
    uvnitr = _make(
        [_w("h", *INKOUST)], cary=[[640, y + R147_ODSTUP_PX, 1, hh - 2 * R147_ODSTUP_PX]]
    )
    o_pixel_vic = _make(
        [_w("h", *INKOUST)],
        cary=[[640, y + R147_ODSTUP_PX - 1, 1, hh - 2 * R147_ODSTUP_PX + 1]],
    )
    assert len(_r147(uvnitr)) == 1
    assert len(_r147(o_pixel_vic)) == 1


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
    d = _make(
        [_w("h", 40, 40, 100, 12)],
        cary=[[60, 41, 1, 10]],
        scene_w=256,
        scene_h=128,
        device="oled256",
    )
    assert _r147(d) == []
    d["device"] = "tab5"
    d["scenes"]["main"]["width"], d["scenes"]["main"]["height"] = 1280, 720
    assert len(_r147(d)) == 1


def test_dva_behy_tyz_vysledek():
    a = [i.message for i in validate_file(SVISLE_VADY, warnings_as_errors=False)]
    b = [i.message for i in validate_file(SVISLE_VADY, warnings_as_errors=False)]
    assert a == b
