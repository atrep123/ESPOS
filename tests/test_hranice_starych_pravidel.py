"""Hranice starych pravidel (7, 24, 63, 80, 123) a schranka 0 u Rule 144.

Stara pravidla maji testy na "uprostred tridy"; hranice na pixel nikdo
nedrzel. Kazdy test tu ma obe strany hranice.

A JEDEN SKUTECNY NALEZ, ktery se tu NEOPRAVUJE (pravidlo kampane): Rule 123
("min gap between non-grouped widgets") je MRTVE. Podminka zni
``0 < gap < MIN_WIDGET_GAP_PX`` a ``MIN_WIDGET_GAP_PX = 1``; mezera je cele
cislo, takze interval (0, 1) je prazdny a pravidlo nemuze vystrelit nikdy.
Dukaz ve trech krocich: (1) dotykajici se cizi widgety (mezera 0) mlci
(xfail strict - ma hlasit), (2) mezera 1 px mlci (to je spravne),
(3) KONTROLNI SKUPINA: s mezi 2 px (monkeypatch) tataz scena s mezerou 1 px
HLASI - mechanika pravidla zije, zabiji ho konstanta.
"""

from __future__ import annotations

import pytest

from tools import validate_design as vd
from tools.validate_design import (
    MIN_EDGE_MARGIN,
    MIN_WIDGET_GAP_PX,
    R144_PRAH_PX,
    R145_PRAH_PX,
    ZNACKA_NAVRH_VADNY,
    ZNACKA_R144,
    ZNACKA_R145,
    validate_data,
)

FL = "test"


def _w(wid, x, y, ww, hh, *, text="AHOJ", t="label", **kw):
    d = {
        "type": t,
        "x": x,
        "y": y,
        "width": ww,
        "height": hh,
        "text": text,
        "color_fg": "#FFFFFF",
        "color_bg": "#000000",
        "align": "left",
        "valign": "middle",
        "_widget_id": wid,
    }
    d.update(kw)
    return d


def _make(widgets, *, navrh=None, scene_w=256, scene_h=128, device=None):
    scene = {"width": scene_w, "height": scene_h, "widgets": widgets}
    if navrh is not None:
        scene["navrh"] = navrh
    data = {"scenes": {"main": scene}}
    if device is not None:
        data["device"] = device
    return data


def _msgs(data):
    return [i.message for i in validate_data(data, file_label=FL, warnings_as_errors=False)]


def _obsahuji(zpravy, kus):
    return [z for z in zpravy if kus in z]


# --------------------------------------------------------------------------- #
# Rule 123 - mrtve pravidlo
# --------------------------------------------------------------------------- #

R123 = "widgets too close"


def _dva(mezera):
    return _make([_w("a.1", 0, 0, 10, 10), _w("b.1", 10 + mezera, 0, 10, 10)])


def test_r123_mez_je_jeden_pixel():
    assert MIN_WIDGET_GAP_PX == 1


@pytest.mark.xfail(
    strict=True,
    reason="SKUTECNA VADA: Rule 123 je mrtve - `0 < gap < MIN_WIDGET_GAP_PX` s mezi 1 "
    "na celych cislech nikdy neplati; dotykajici se cizi widgety (mezera 0) mlci. "
    "Neopravovat v testu; viz testy/kolo1.md.",
)
def test_r123_dotykajici_se_cizi_widgety_maji_dostat_nalez():
    assert _obsahuji(_msgs(_dva(0)), R123)


def test_r123_mezera_jeden_pixel_mlci():
    assert _obsahuji(_msgs(_dva(1)), R123) == []


def test_r123_tataz_skupina_mlci_i_pri_mezere_0():
    d = _make([_w("a.1", 0, 0, 10, 10), _w("a.2", 10, 0, 10, 10)])
    assert _obsahuji(_msgs(d), R123) == []


def test_r123_KONTROLNI_SKUPINA_s_mezi_2px_pravidlo_zije(monkeypatch):
    """Mechanika je v poradku - mezera 1 < 2 vystreli. Zabiji ji konstanta 1."""
    monkeypatch.setattr(vd, "MIN_WIDGET_GAP_PX", 2)
    nalezy = _obsahuji(_msgs(_dva(1)), R123)
    assert nalezy and "(1px < 2px min gap)" in nalezy[0]
    assert _obsahuji(_msgs(_dva(2)), R123) == []


def test_r123_interval_je_prazdny_pro_kazdou_celou_mezeru():
    """Primy dukaz nad podminkou: zadne cele cislo neni v (0, 1)."""
    assert not any(0 < g < MIN_WIDGET_GAP_PX for g in range(0, 1000))


# --------------------------------------------------------------------------- #
# Rule 7 - preteceni textu (znakovy odhad, OLED font 6x8)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("znaku", "ceka_nalez"), [(6, False), (7, True)])
def test_r7_hranice_sirky_na_znak(znaku, ceka_nalez):
    """w=40: inner 36 / 6 = 6 znaku."""
    d = _make([_w("t.1", 10, 10, 40, 16, text="A" * znaku)])
    assert bool(_obsahuji(_msgs(d), "overflows max 6 chars")) is ceka_nalez


@pytest.mark.parametrize(("vyska", "ceka_nalez"), [(12, False), (11, True)])
def test_r7_hranice_vysky_na_radek(vyska, ceka_nalez):
    """h=12: inner 8 = font_h -> jeden radek; 11 -> zadny."""
    d = _make([_w("t.1", 10, 10, 60, vyska, text="AB")])
    assert bool(_obsahuji(_msgs(d), "text cannot fit: h=")) is ceka_nalez


# --------------------------------------------------------------------------- #
# Rule 24 - okraj sceny
# --------------------------------------------------------------------------- #


def test_r24_mez_je_dva_pixely_na_OLEDu():
    assert MIN_EDGE_MARGIN == 2


@pytest.mark.parametrize(("prava", "ceka_nalez"), [(254, False), (255, True)])
def test_r24_hranice_prave_hrany(prava, ceka_nalez):
    d = _make([_w("t.1", 100, 10, prava - 100, 16)])
    assert bool(_obsahuji(_msgs(d), "right edge too close to boundary")) is ceka_nalez


def test_r24_licujici_hrana_bez_ramecku_mlci_s_rameckem_hlasi():
    bez = _make([_w("t.1", 100, 10, 156, 16)])
    s_ram = _make([_w("t.1", 100, 10, 156, 16, border=True, border_style="single")])
    assert _obsahuji(_msgs(bez), "right edge too close") == []
    assert _obsahuji(_msgs(s_ram), "right edge too close to boundary (256 > 254)")


@pytest.mark.parametrize(("dolni", "ceka_nalez"), [(126, False), (127, True)])
def test_r24_hranice_dolni_hrany(dolni, ceka_nalez):
    d = _make([_w("t.1", 10, 60, 60, dolni - 60)])
    assert bool(_obsahuji(_msgs(d), "bottom edge too close to boundary")) is ceka_nalez


# --------------------------------------------------------------------------- #
# Rule 63 - vetsina widgetu mimo scenu (< 25 % viditelne)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("x", "ceka_nalez"), [(-30, False), (-31, True)])
def test_r63_hranice_ctvrtiny_plochy(x, ceka_nalez):
    """40x20 na x=-30: 10/40 = presne 25 % -> mlci; -31: 9/40 = 22 % -> hlasi."""
    d = _make([_w("t.1", x, 10, 40, 20)])
    nalezy = _obsahuji(_msgs(d), "% visible inside scene bounds")
    assert bool(nalezy) is ceka_nalez
    if ceka_nalez:
        assert "only 22% visible" in nalezy[0]


def test_r63_uplne_mimo_scenu_neni_tento_nalez():
    d = _make([_w("t.1", -40, 10, 40, 20)])
    assert _obsahuji(_msgs(d), "% visible inside scene bounds") == []


# --------------------------------------------------------------------------- #
# Rule 80 - okraj vytlaci widget ze sceny
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("mx", "ceka_nalez"), [(155, False), (156, True)])
def test_r80_hranice_margin_x(mx, ceka_nalez):
    """x=100: 100+156 == sw -> hlasi (>=), 155 -> mlci."""
    d = _make([_w("t.1", 100, 10, 20, 16, margin_x=mx)])
    assert bool(_obsahuji(_msgs(d), "pushes widget past scene right edge")) is ceka_nalez


@pytest.mark.parametrize(("my", "ceka_nalez"), [(117, False), (118, True)])
def test_r80_hranice_margin_y(my, ceka_nalez):
    d = _make([_w("t.1", 10, 10, 20, 16, margin_y=my)])
    assert bool(_obsahuji(_msgs(d), "pushes widget past scene bottom edge")) is ceka_nalez


def test_r80_nulovy_a_zaporny_okraj_mlci():
    d = _make([_w("t.1", 250, 10, 5, 16, margin_x=0), _w("t.2", 250, 40, 5, 16, margin_x=-5)])
    assert _obsahuji(_msgs(d), "pushes widget") == []


# --------------------------------------------------------------------------- #
# Rule 144 / 145 - schranka 0 px (kritik espos-vse-kritik D1)
# --------------------------------------------------------------------------- #


def _orez(so, ss, vo, vs):
    prvek = _w("t.1", 40, 200, 300, 20, text="V0.4-71-gee91351-dirty")
    navrh = {"prvky": {"t.1": {"orez": {"sirka_obsahu": so, "sirka_schranky": ss,
                                        "vyska_obsahu": vo, "vyska_schranky": vs}}}}
    return _make([prvek], navrh=navrh, scene_w=1280, scene_h=720, device="tab5")


def test_r144_schranka_0_a_obsah_0_je_ticho_bez_vyjimky():
    """Radkovy prvek: scrollWidth i clientWidth 0. Neni to orez ani vadny blok."""
    zpravy = _msgs(_orez(0, 0, 0, 0))
    assert _obsahuji(zpravy, ZNACKA_R144) == [] and _obsahuji(zpravy, ZNACKA_R145) == []
    assert _obsahuji(zpravy, ZNACKA_NAVRH_VADNY) == []


def test_r144_schranka_0_s_obsahem_je_uplne_useknuti():
    nalezy = _obsahuji(_msgs(_orez(40, 0, 20, 20)), ZNACKA_R144)
    assert nalezy and "obsah je 40 px siroky, videt je 0 px (useklo se 40 px)" in nalezy[0]


@pytest.mark.parametrize(("obsah", "ceka_nalez"), [(1, False), (2, True)])
def test_r144_hranice_prahu_pri_schrance_0(obsah, ceka_nalez):
    assert R144_PRAH_PX == 2
    assert bool(_obsahuji(_msgs(_orez(obsah, 0, 20, 20)), ZNACKA_R144)) is ceka_nalez


@pytest.mark.parametrize(("obsah", "ceka_nalez"), [(1, False), (2, True)])
def test_r145_hranice_prahu_pri_schrance_0(obsah, ceka_nalez):
    assert R145_PRAH_PX == 2
    assert bool(_obsahuji(_msgs(_orez(300, 300, obsah, 0)), ZNACKA_R145)) is ceka_nalez


def test_r144_zaporna_schranka_je_vadny_blok_ne_useknuti():
    zpravy = _msgs(_orez(40, -1, 20, 20))
    assert _obsahuji(zpravy, f"{ZNACKA_NAVRH_VADNY}: 'prvky.t.1.orez.sirka_schranky'")
    assert _obsahuji(zpravy, ZNACKA_R144) == []
