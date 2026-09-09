"""Rule 152 (mrizka bez kapacity) a hranice Rule 140 na dnesnim Domove 11/11.

DIRA, KTEROU TO ZAVIRA (kritik espos-brany, bod 8; mapa mezer, priorita A):
`data-kapacita` nese na 62 listech kitu presne DVA. Mrizka bez atributu
nedostala ani WARN "nemerilo se" - jedenact dlazdic bez deklarace bylo
UPLNE TICHO, a ticho vypadalo v souhrnu jako zelena. Firmware pritom
kreslil 2x5 = 10 slotu na 11 appek. Rule 140 je v poradku, vada byla
v POKRYTI: pravidlo, ktere se nepustilo, o tom nerekne.

Rule 152 se pta obracene nez Rule 140: ne "sedi kapacita?", ale "je tu
mrizka, o ktere nikdo nerekl, jakou ma kapacitu?". Odpoved je WARN se
znackou `*_NEMERENO`, kterou most kitu bere jako fail-closed.

CO JE MRIZKA (kazda pulka podminky ma tu svuj protipriklad, viz
`slozena-podminka-kazda-pulka-ma-protipriklad`):

  (a) prvky TEZE TRIDY        - dve tridy po trech prvcich nejsou mrizka
  (b) TEZE VELIKOSTI          - razitko: ctyri sloty ruznych sirek (kontrolni
                                skupina) neni mrizka
  (c) nejmene R152_MIN_PRVKU  - hranice 5 vs 6
  (d) >= 2 sloupce a >= 2 radky - jeden sloupec je SEZNAM (16 kanalu LA,
                                radky souboru), jeden radek je RADA
                                (zalozky). Pojmenovana mez: seznam, ktery
                                neroluje, projde; kdo ho chce hlidat,
                                deklaruje data-kapacita rukou.

Gatovano DATY (blok `navrh` musi byt), ne profilem.
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from tools.validate_design import (
    R152_MIN_PRVKU,
    ZNACKA_R140,
    ZNACKA_R140_NEMERENO,
    ZNACKA_R152_NEMERENO,
    validate_data,
    validate_file,
)

FL = "test"
FIXTURY = pathlib.Path(__file__).parent / "fixtures"
CISTE = FIXTURY / "tab5_mrizka_bez_kapacity_ciste.json"
VADY = FIXTURY / "tab5_mrizka_bez_kapacity_vady.json"
PANEL = FIXTURY / "panel_2026-09-08"
STARSI_MRIZKA_VADY = FIXTURY / "tab5_mrizka_vady.json"


def _w(wid, x, y, ww, hh, *, text="AHOJ", t="label", **kw):
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


def _make(widgets, *, navrh=None, scene_w=1280, scene_h=720, device="tab5"):
    scene = {"width": scene_w, "height": scene_h, "widgets": widgets}
    if navrh is not None:
        scene["navrh"] = navrh
    data = {"scenes": {"main": scene}}
    if device is not None:
        data["device"] = device
    return data


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _msgs(data, **kw):
    return [i.message for i in _issues(data, **kw)]


def _warns(data, **kw):
    return [i.message for i in _issues(data, **kw) if i.level == "WARN"]


def _errors(data, **kw):
    return [i.message for i in _issues(data, **kw) if i.level == "ERROR"]


def _obsahuji(zpravy, kus):
    return [z for z in zpravy if kus in z]


def _dlazdice(n, *, sloupcu=3, skupina="dlazdice", w=386, h=120, x0=48, y0=140,
              dx=410, dy=130):
    """n prvku teze tridy a velikosti, lamanych po `sloupcu` do radku."""
    return [
        _w(f"{skupina}.{i}", x0 + dx * (i % sloupcu), y0 + dy * (i // sloupcu), w, h,
           text=f"APPKA {i}")
        for i in range(n)
    ]


def _scena(prvky, *, mrizky=None, navrh=True, **kw):
    blok = None
    if navrh:
        blok = {"prvky": {}}
        if mrizky is not None:
            blok["mrizky"] = mrizky
    return _make(prvky, navrh=blok, **kw)


# --------------------------------------------------------------------------- #
# Pozitivni trida
# --------------------------------------------------------------------------- #


def test_r152_dvanact_dlazdic_bez_deklarace_je_WARN_o_nemereni():
    d = _scena(_dlazdice(12))
    assert (
        f"{FL}: main: {ZNACKA_R152_NEMERENO}: skupina 'dlazdice' ma 12 stejnych prvku "
        f"386x120 ve 3 sloupcich a 4 radcich, ale navrh.mrizky o ni nema zaznam - "
        f"kapacita se NEMERILA (generator ma napsat data-kapacita a data-polozky)"
    ) in _warns(d)
    assert _obsahuji(_errors(d), ZNACKA_R152_NEMERENO) == []


def test_r152_je_WARN_ne_ERROR_a_znacka_je_NEMERENO():
    """Most kitu sbira znacky podle JMENA (`*_NEMERENO`) a hlaska musi nest
    slovo NEMERILA, aby ji clovek v souhrnu nezamenil za nalez na listu."""
    assert ZNACKA_R152_NEMERENO.isascii()
    assert "NEMERILA" in _obsahuji(_warns(_scena(_dlazdice(6))), ZNACKA_R152_NEMERENO)[0]


def test_r152_deklarace_JINE_mrizky_neumlci():
    d = _scena(_dlazdice(12), mrizky=[{"jmeno": "radky", "kapacita": 12, "polozek": 11}])
    assert _obsahuji(_warns(d), ZNACKA_R152_NEMERENO)


def test_r152_dve_skupiny_dva_nalezy_serazene():
    d = _scena(_dlazdice(6) + _dlazdice(6, skupina="karty", y0=600, h=20, dy=25))
    nalezy = _obsahuji(_warns(d), ZNACKA_R152_NEMERENO)
    assert len(nalezy) == 2
    assert "'dlazdice'" in nalezy[0] and "'karty'" in nalezy[1]


def test_r152_je_gatovane_daty_ne_profilem():
    d = _scena(_dlazdice(6, w=20, h=10, x0=4, y0=4, dx=30, dy=20),
               device="oled256", scene_w=256, scene_h=128)
    assert _obsahuji(_warns(d), ZNACKA_R152_NEMERENO)


# --------------------------------------------------------------------------- #
# Negativni trida - kazda pulka podminky ma svuj protipriklad
# --------------------------------------------------------------------------- #


def test_r152_deklarovana_mrizka_mlci():
    d = _scena(_dlazdice(12), mrizky=[{"jmeno": "dlazdice", "kapacita": 12, "polozek": 11}])
    assert _obsahuji(_msgs(d), ZNACKA_R152_NEMERENO) == []


def test_r152_deklarace_bez_poctu_polozek_je_JEDEN_nalez_a_patri_Rule_140():
    """Jedna obet, jeden nalez: o nemereni uz mluvi Rule 140."""
    d = _scena(_dlazdice(12), mrizky=[{"jmeno": "dlazdice", "kapacita": 12}])
    zpravy = _msgs(d)
    assert len(_obsahuji(zpravy, ZNACKA_R140_NEMERENO)) == 1
    assert _obsahuji(zpravy, ZNACKA_R152_NEMERENO) == []


def test_r152_kontrolni_skupina_razitko_ruznych_sirek_mlci():
    """(b) Ctyri az sest slotu TEZE vysky, RUZNYCH sirek, ve dvou radcich."""
    sirky = [300, 200, 250, 180, 150, 160]
    prvky = [
        _w(f"razitko.{i}", 40 + 320 * (i % 3), 600 + 44 * (i // 3), sirky[i], 40, text=f"S{i}")
        for i in range(6)
    ]
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []


def test_r152_dve_tridy_po_trech_nejsou_mrizka():
    """(a) Sest stejnych obdelniku, ale dve tridy - kazda ma jen tri."""
    prvky = _dlazdice(3) + _dlazdice(3, skupina="karty", y0=400)
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []


def test_r152_jeden_sloupec_je_seznam_ne_mrizka():
    """(d) Sestnact kanalu LA pod sebou - pocet dava hardware, ne kresba."""
    prvky = _dlazdice(16, sloupcu=1, skupina="kanal", w=1100, h=30, y0=120, dy=34)
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []


def test_r152_jeden_radek_je_rada_ne_mrizka():
    prvky = _dlazdice(6, sloupcu=6, skupina="zalozka", w=150, h=81, x0=40, dx=200)
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []


def test_r152_bez_bloku_navrh_mlci():
    """Dokument editoru merena data legitimne nema (viz NAVRH_KLIC)."""
    assert _obsahuji(_msgs(_scena(_dlazdice(12), navrh=False)), ZNACKA_R152_NEMERENO) == []


def test_r152_prazdny_blok_navrh_uz_meri():
    d = _make(_dlazdice(12), navrh={})
    assert _obsahuji(_warns(d), ZNACKA_R152_NEMERENO)


def test_r152_neviditelne_prvky_se_nepocitaji():
    prvky = _dlazdice(6)
    prvky[5]["visible"] = False
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []


def test_r152_prvek_bez_skupiny_se_nepocita():
    prvky = _dlazdice(6)
    for p in prvky:
        del p["_widget_id"]
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []


# --------------------------------------------------------------------------- #
# Hranice
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("n", "ceka_nalez"), [(5, False), (6, True), (7, True)])
def test_r152_hranice_pet_vs_sest(n, ceka_nalez):
    assert R152_MIN_PRVKU == 6
    d = _scena(_dlazdice(n))  # 3 sloupce: 5 = 3+2 (dva radky), 6 = 3+3
    assert bool(_obsahuji(_warns(d), ZNACKA_R152_NEMERENO)) is ceka_nalez


def test_r152_hranice_druheho_sloupce_je_jedna_leva_hrana():
    """Sest prvku: pet pod sebou + jeden vedle = 2 sloupce, 5 radku -> mrizka;
    tentyz sesty prvek POD nimi = 1 sloupec -> seznam."""
    pet = _dlazdice(5, sloupcu=1)
    vedle = [*pet, _w("dlazdice.5", 48 + 410, 140, 386, 120, text="X")]
    pod = [*pet, _w("dlazdice.5", 48, 140 + 130 * 5, 386, 120, text="X")]
    assert _obsahuji(_warns(_scena(vedle)), ZNACKA_R152_NEMERENO)
    assert _obsahuji(_msgs(_scena(pod)), ZNACKA_R152_NEMERENO) == []


def test_r152_hranice_velikosti_je_jeden_pixel():
    """Sesty prvek o 1 px sirsi uz do velikostni tridy nepatri -> pet -> ticho."""
    prvky = _dlazdice(6)
    prvky[5]["width"] = 387
    assert _obsahuji(_msgs(_scena(prvky)), ZNACKA_R152_NEMERENO) == []
    prvky[5]["width"] = 386
    assert _obsahuji(_warns(_scena(prvky)), ZNACKA_R152_NEMERENO)


# --------------------------------------------------------------------------- #
# Fixtury (jdou pres validate_file = i JSON schema) a starsi fixtura jako
# pozitivni kontrola nad skutecnymi cisly
# --------------------------------------------------------------------------- #


def test_fixtura_vady_projde_schematem_a_hlasi_prave_jednou():
    nalezy = [i for i in validate_file(VADY, warnings_as_errors=False)
              if ZNACKA_R152_NEMERENO in i.message]
    assert len(nalezy) == 1 and nalezy[0].level == "WARN"
    assert "'dlazdice' ma 12 stejnych prvku 386x120 ve 3 sloupcich a 4 radcich" in nalezy[0].message


def test_fixtura_ciste_projde_schematem_a_mlci():
    zpravy = [i.message for i in validate_file(CISTE, warnings_as_errors=False)]
    assert _obsahuji(zpravy, ZNACKA_R152_NEMERENO) == []
    assert _obsahuji(zpravy, ZNACKA_R140) == []
    assert _obsahuji(zpravy, ZNACKA_R140_NEMERENO) == []
    assert not [z for z in validate_file(CISTE, warnings_as_errors=False) if z.level == "ERROR"]


def test_fixtury_se_lisi_JEN_deklaraci_mrizky():
    """Obe nesou razitko (kontrolni skupina) a tutez kresbu."""
    v = json.loads(VADY.read_text(encoding="utf-8"))
    c = json.loads(CISTE.read_text(encoding="utf-8"))
    assert v["scenes"]["main"]["widgets"] == c["scenes"]["main"]["widgets"]
    assert "mrizky" not in v["scenes"]["main"]["navrh"]
    assert c["scenes"]["main"]["navrh"]["mrizky"] == [
        {"jmeno": "dlazdice", "kapacita": 12, "polozek": 11}
    ]
    assert sum(w["_widget_id"].startswith("razitko.") for w in v["scenes"]["main"]["widgets"]) == 4


def test_starsi_mrizkova_fixtura_bez_deklarace_by_dostala_nalez():
    """Pozitivni kontrola nad cisly, ktera uz v repu byla: `tab5_mrizka_vady`
    ma sest dlazdic 386x260 (3x2) s deklaraci -> R152 mlci; bez ni hlasi."""
    d = json.loads(STARSI_MRIZKA_VADY.read_text(encoding="utf-8"))
    assert _obsahuji(_msgs(d), ZNACKA_R152_NEMERENO) == []
    bez = copy.deepcopy(d)
    del bez["scenes"]["main"]["navrh"]["mrizky"]
    nalezy = _obsahuji(_warns(bez), ZNACKA_R152_NEMERENO)
    assert len(nalezy) == 1 and "6 stejnych prvku 386x260 ve 3 sloupcich a 2 radcich" in nalezy[0]


def test_r152_dva_behy_tyz_vysledek():
    d = _scena(_dlazdice(12) + _dlazdice(6, skupina="karty", y0=660, h=20, dy=25))
    assert _msgs(d) == _msgs(d)


# --------------------------------------------------------------------------- #
# Rule 140: hranice presne na dnesnim Domove (11 appek)
# --------------------------------------------------------------------------- #


def _mrizka(kapacita, polozek):
    return _scena([_w("obsah", 20, 97, 1240, 603, text="", t="panel")],
                  mrizky=[{"jmeno": "dlazdice", "kapacita": kapacita, "polozek": polozek}])


@pytest.mark.parametrize(
    ("kapacita", "polozek", "ceka_nalez"),
    [
        (11, 11, False),  # presne plno: kazda appka ma slot, zadny volny
        (10, 11, True),  # firmware 2x5 (fotoprotokol Domov) - jedenacta se ztrati
        (12, 11, False),  # artboard 4x3 - dvanacty slot prazdny
        (11, 12, True),  # az pribude dvanacta appka do 11 slotu
    ],
)
def test_r140_hranice_na_dnesnim_domove(kapacita, polozek, ceka_nalez):
    chyby = _obsahuji(_errors(_mrizka(kapacita, polozek)), ZNACKA_R140)
    assert bool(chyby) is ceka_nalez
    if ceka_nalez:
        assert f"ma kapacitu {kapacita}, polozek je {polozek} (o {polozek - kapacita} vic)" in chyby[0]


def test_r140_panelove_fixtury_domova_nesou_10_a_12_slotu_na_11_appek():
    """Fixtury z fotoprotokolu jsou ta hranice ve skutecnych cislech."""
    vady = json.loads((PANEL / "panel_domov_vady.json").read_text(encoding="utf-8"))
    ciste = json.loads((PANEL / "panel_domov_ciste.json").read_text(encoding="utf-8"))
    assert vady["scenes"]["main"]["navrh"]["mrizky"] == [
        {"jmeno": "dlazdice", "kapacita": 10, "polozek": 11}
    ]
    assert ciste["scenes"]["main"]["navrh"]["mrizky"] == [
        {"jmeno": "dlazdice", "kapacita": 12, "polozek": 11}
    ]
    assert _obsahuji(_errors(vady), "ma kapacitu 10, polozek je 11 (o 1 vic)")
    assert _obsahuji(_msgs(ciste), ZNACKA_R140) == []
