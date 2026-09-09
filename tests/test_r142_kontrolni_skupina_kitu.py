"""Rule 142, osmy a devaty tvar: KONTROLNI SKUPINA verzalkovych slov z kitu.

REZIDUUM R2 KRITIKA (espos-oprava): z 57 (dnes 65) jmen SDK je nejmene 20
beznych slov - SMALT, ZNAK, JMENO, HLAVNI, PRIMO, INFO, LIVE, NONE, DEBUG,
WARN, BUSY, ... - a slovnik kitu je zrovna smalt/znak/jmeno. Dnes je
0 fantomu, ale "jen nahodou": nikdo to nemeril nad texty kitu. Tenhle
soubor z toho dela mereni s rohatkou:

* `vety`   = 130 textu kitu s malymi pismeny a verzalkovym slovem (trida se
             v nich MERI): nalezu osmeho/devateho tvaru musi byt PRESNE
             etalon (dnes jeden: `ERROR cteni: NotFound`), nic navic
             (fantom) a nic min (ztraceny pravdivy nalez).
* `stitky` = 138 textu cele verzalkami (STITEK, trida se v nich NEMERI):
             0 nalezu osmeho tvaru.
* KONTROLNI SKUPINA S OPACNOU PRAVDOU: bezna slova ze SDK jako STITEK mlci,
  tataz slova UVNITR VETY hlasi - obe pulky meze (a)/(b) u `_V_VERZALKY`
  maji tady svuj dolozeny pruchod nad ZIVYMI jmeny SDK.
* MUTACE DAT: pridat do jmen SDK bezne kitove slovo (BLE, USB, ...) musi
  vyrobit fantom -> dokazuje, ze test meri kitove texty, ne prazdno.
* ZIVY KIT: kdyz kit lezi vedle, tataz rohatka jede i nad dnesnimi listy
  (fixtura je snimek k fe66ed0; drift se pozna, ne prehlasi).

Fixtura: tests/fixtures/verzalky_kit_2026-09-09.json (odkud a jak, viz jeji
`_o_souboru`).
"""

from __future__ import annotations

import json
import pathlib
from html.parser import HTMLParser

import pytest

from tools.validate_design import (
    _V_ROZHRANI,
    _V_VERZALKY,
    VETY_NENI_JMENO_SDK,
    VETY_NENI_ROZHRANI,
    ZNACKA_R142,
    _veta_strojove_jmeno,
    validate_data,
)

FIXTURA = pathlib.Path(__file__).parent / "fixtures" / "verzalky_kit_2026-09-09.json"
# ESPOS lezi ve workspace/research/ESPOS, kit ve workspace/tabos-ui-kit:
# tests/ -> ESPOS -> research -> workspace = parents[3] (tataz cesta jako
# `DILNA` v `dilna.py`: ESPOS.parents[1]). S parents[2] test tise skipoval.
KIT = pathlib.Path(__file__).resolve().parents[3] / "tabos-ui-kit" / "navrh-appky"
TVARY_SDK = ("jmeno ze SDK", "jmeno rozhrani ze SDK")


def _fixtura() -> dict:
    return json.loads(FIXTURA.read_text(encoding="utf-8"))


def _jmena(f) -> frozenset[str]:
    return frozenset(f["jmena_sdk"]["jmena"])


def _nalezy_sdk(texty, jmena):
    """{text: (pojmenovani, kus)} jen pro osmy/devaty tvar."""
    ven = {}
    for t in texty:
        d = _veta_strojove_jmeno(t, jmena)
        if d is not None and d[0] in TVARY_SDK:
            ven[t] = d
    return ven


def _verzalky(text):
    return [m.group(0) for m in _V_VERZALKY.finditer(text)
            if m.group(0) not in VETY_NENI_ROZHRANI and m.group(0) not in VETY_NENI_JMENO_SDK]


def test_fixtura_je_nabita_a_ma_puvod():
    f = _fixtura()
    assert f["kit"] == "fe66ed0"
    assert len(f["vety"]) >= 100 and len(f["stitky"]) >= 100 and len(_jmena(f)) >= 50
    assert all(_verzalky(v["text"]) for v in f["vety"] + f["stitky"])
    assert all(any(z.islower() for z in v["text"]) for v in f["vety"])
    assert not any(any(z.islower() for z in s["text"]) for s in f["stitky"])
    assert {e["text"] for e in f["etalon_nalezu"]} <= {v["text"] for v in f["vety"]}


def test_vety_kitu_daji_PRESNE_etalon_nalezu_0_fantomu():
    f = _fixtura()
    nalezy = _nalezy_sdk([v["text"] for v in f["vety"]], _jmena(f))
    etalon = {e["text"]: (e["pojmenovani"], e["kus"]) for e in f["etalon_nalezu"]}
    fantomy = {t: d for t, d in nalezy.items() if t not in etalon}
    ztracene = {t: d for t, d in etalon.items() if t not in nalezy}
    assert not fantomy, f"FANTOM osmeho tvaru na textu kitu: {fantomy}"
    assert not ztracene, f"ztraceny pravdivy nalez: {ztracene}"
    assert nalezy == etalon


def test_stitky_kitu_verzalkami_se_NEMERI():
    f = _fixtura()
    assert _nalezy_sdk([s["text"] for s in f["stitky"]], _jmena(f)) == {}


def test_etalon_je_pravdivy_nalez_i_pres_celou_branu():
    f = _fixtura()
    for e in f["etalon_nalezu"]:
        scene = {"width": 1280, "height": 720, "navrh": {"jmena_sdk": sorted(_jmena(f))},
                 "widgets": [{"type": "label", "x": 40, "y": 200, "width": 400, "height": 20,
                              "text": e["text"], "color_fg": "#e6e1ce", "color_bg": "#14170f",
                              "align": "left", "valign": "middle", "_widget_id": "radek.1"}]}
        zpravy = [i.message for i in validate_data({"device": "tab5", "scenes": {"main": scene}},
                                                   file_label="t", warnings_as_errors=False)]
        assert [z for z in zpravy if ZNACKA_R142 in z and f"'{e['kus']}'" in z]


def _bezna_slova_sdk(jmena):
    """Jmena SDK, ktera vypadaji jako bezne slovo: bez I-rozhrani, jednohrba."""
    return sorted(j for j in jmena
                  if not _V_ROZHRANI.fullmatch(j) and len(j) >= 3
                  and sum(1 for z in j[1:] if z.isupper()) == 0
                  and j.upper() not in VETY_NENI_JMENO_SDK)


def test_kontrolni_skupina_bezna_slova_SDK_jako_STITEK_mlci_ale_ve_VETE_hlasi():
    f = _fixtura()
    jmena = _jmena(f)
    slova = _bezna_slova_sdk(jmena)
    assert len(slova) >= 15, slova  # kritik R2: "nejmene 20 z 57"
    assert {"Smalt", "Znak", "Primo", "Info", "Hlavni"} <= set(slova)
    for s in slova:
        stitek = s.upper()
        assert _veta_strojove_jmeno(stitek, jmena) is None, f"stitek '{stitek}' obvinen"
        assert _veta_strojove_jmeno(f"STAV {stitek}", jmena) is None
        veta = f"stav je {stitek} a mereni pokracuje"
        assert _veta_strojove_jmeno(veta, jmena) == ("jmeno ze SDK", stitek), veta


def test_kitove_stitky_ktere_jsou_zaroven_jmenem_SDK_jsou_dnes_nula():
    """Rohatka: kolik kitovych stitku se trefi do jmen SDK (dnes 0). Az bude
    prvni, ma tu pribyt do seznamu a test ho ma pojmenovat, ne umlcet."""
    f = _fixtura()
    velka = {j.upper() for j in _jmena(f)}
    kolize = sorted(s["text"] for s in f["stitky"] if any(v.upper() in velka for v in _verzalky(s["text"])))
    assert kolize == []


@pytest.mark.parametrize("slovo", ["BLE", "USB", "LA1010", "ESP32", "PHY", "NERTERA"])
def test_MUTACE_DAT_kitove_slovo_v_SDK_je_fantom(slovo):
    """Kdyby se do SDK dostal enum `Ble` nebo `Usb`, brana by obvinila
    kitove vety. Test to musi VIDET - jinak by nemeril kitove texty."""
    f = _fixtura()
    jmena = _jmena(f) | {slovo.capitalize()}
    nalezy = _nalezy_sdk([v["text"] for v in f["vety"]], jmena)
    fantomy = {t: d for t, d in nalezy.items() if d[1] == slovo}
    assert len(fantomy) >= 1, slovo


def test_dva_behy_tyz_vysledek():
    f = _fixtura()
    texty = [v["text"] for v in f["vety"]]
    assert _nalezy_sdk(texty, _jmena(f)) == _nalezy_sdk(texty, _jmena(f))


# --------------------------------------------------------------------------- #
# Zivy kit vedle ESPOSu: tataz rohatka nad dnesnimi listy
# --------------------------------------------------------------------------- #


class _Texty(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texty: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if self.skip:
            return
        d = " ".join(data.split())
        if d:
            self.texty.append(d)


def _texty_kitu():
    listy = sorted(KIT.glob("*.dc.html"))
    if not listy:
        pytest.skip(f"NEZMERENO: {KIT} nema zadny *.dc.html - kit neni vedle ESPOSu")
    ven = []
    for cesta in listy:
        p = _Texty()
        p.feed(cesta.read_text(encoding="utf-8"))
        ven.extend(t for t in p.texty if _verzalky(t))
    return ven


def test_zivy_kit_vety_0_fantomu_a_etalon_drzi():
    f = _fixtura()
    vety = sorted({t for t in _texty_kitu() if any(z.islower() for z in t)})
    nalezy = _nalezy_sdk(vety, _jmena(f))
    etalon = {e["text"] for e in f["etalon_nalezu"]}
    fantomy = {t: d for t, d in nalezy.items() if t not in etalon}
    assert not fantomy, f"FANTOM na zivem listu kitu: {fantomy}"
    assert set(nalezy) == etalon


def test_zivy_kit_snimek_nezastaral():
    """Kdyz se kitove texty s verzalkami zmeni, fixtura se ma prepsat, ne
    tise starnout (regenerace: viz `_o_souboru` fixtury)."""
    f = _fixtura()
    zive = sorted(set(_texty_kitu()))
    snimek = sorted({v["text"] for v in f["vety"]} | {s["text"] for s in f["stitky"]})
    navic, chybi = sorted(set(zive) - set(snimek)), sorted(set(snimek) - set(zive))
    assert not navic and not chybi, (
        f"snimek kitu zastaral: {len(navic)} textu navic, {len(chybi)} chybi; "
        f"navic={navic[:5]} chybi={chybi[:5]}"
    )
