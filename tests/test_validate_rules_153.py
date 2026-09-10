"""Rule 153: Zpet jen mimo koren.

CO SE MERI. Navigace TabOSu je STROM s jednim korenem (Domov). Z toho plynou
DVE tridy, ne jedna, a pravidlo meri obe:

  koren       (`navrh.koren` je true)  tlacitko Zpet mit NESMI  - nema kam
                                       vest, je to slib bez pokryti
  kazdy jiny  (`navrh.koren` je false) tlacitko Zpet mit MUSI, a to na
                                       deklarovanem miste z `tokens.json`

Kontrolni skupina je zabudovana do tvaru pravidla: obe tridy maji vlastni
nalez, takze "prijmi vse" ani "odmitni vse" neprojde - kazde takove pravidlo
by na te druhe tride okamzite zcervenalo. Tenhle soubor to overuje na
DVOJICICH fixtur, ktere se lisi JEDINYM klicem (`tab5_zpet_chybi_vady` proti
`tab5_zpet_koren_ciste` maji bajt po bajtu tutez kresbu).

ROZHODUJE PRIZNAK, NE CHYBEJICI TLACITKO. Odvodit "kdyz Zpet neni, byl to asi
koren" nejde: "tlacitko chybi" je PRAVE TEN JEV, ktery ma pravidlo soudit -
brana by merila sama sebe a jedna z obou trid by tise zmizela. Priznak proto
vydava generator (`data-koren`) a most kitu ho vozi VZDY, i jako false.

POLOHA SE MERI PROTI DEKLARACI, NE PROTI SCENE. Ve scene uz jeden obdelnik
navigace je (`navrh.pasy["navigace"]`), ale na listech kitu ho ZAKLADA sam
prvek `.zpet` - posunuty knoflik si pas posune s sebou, takze by se merilo
tlacitko proti sobe samemu (a Rule 136 na nem mlci taky, protoze ze sveho pasu
nevycniva). Fixtura `tab5_zpet_misto_vady` je presne tenhle pripad: pas i
tlacitko na 1149, deklarace na 1148, nalez vyda jedine deklarace.

CO ZNAMENA TICHO (fail-closed jako 136-151):
  * scena bez bloku `navrh`                 -> pravidlo MLCI (dokument editoru)
  * scena Z MOSTU bez `koren`               -> `priznak korene nedodan`
  * ne-koren se Zpet, ale bez `navigace`    -> `misto pro Zpet nedodano`

Zavora "scena je z mostu" je klic `orez` na prvcich - tentyz klic a tataz
uvaha jako u Rule 150 a 151.
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from tools.validate_design import (
    R153_PAS,
    R153_TRIDA,
    ZNACKA_NAVRH_VADNY,
    ZNACKA_R136_PAS_VEN,
    ZNACKA_R153_CHYBI,
    ZNACKA_R153_KOREN,
    ZNACKA_R153_MISTO,
    ZNACKA_R153_MISTO_NEMERENO,
    ZNACKA_R153_NEMERENO,
    ZNACKA_R153_VIC,
    validate_data,
    validate_file,
)

FL = "test"
FIXTURY = pathlib.Path(__file__).parent / "fixtures"
CISTE = FIXTURY / "tab5_zpet_ciste.json"
KOREN_CISTE = FIXTURY / "tab5_zpet_koren_ciste.json"
KOREN_VADY = FIXTURY / "tab5_zpet_koren_vady.json"
CHYBI_VADY = FIXTURY / "tab5_zpet_chybi_vady.json"
MISTO_VADY = FIXTURY / "tab5_zpet_misto_vady.json"

# tokens.json: layout.zpet + layout.hlavicka
MISTO = {"x": 1148, "y": 8, "w": 112, "h": 81}
OBDELNIK = (MISTO["x"], MISTO["y"], MISTO["w"], MISTO["h"])


# --------------------------------------------------------------------------- #
# Stavebnice
# --------------------------------------------------------------------------- #


def _w(wid, x, y, ww, hh, *, text="Zpet", t="button"):
    return {
        "type": t,
        "x": x,
        "y": y,
        "width": ww,
        "height": hh,
        "text": text,
        "color_fg": "#e4dfcc",
        "color_bg": "#14170f",
        "align": "left",
        "valign": "middle",
        "_widget_id": wid,
    }


def _scena(widgets, navrh):
    scene = {"width": 1280, "height": 720, "widgets": widgets}
    if navrh is not None:
        scene["navrh"] = navrh
    return {"device": "tab5", "scenes": {"main": scene}}


def _navrh(*, koren=False, misto=True, z_mostu=True, prvky=None, pasy=None):
    """Blok `navrh` s pojmenovanymi pulkami, aby sla kazda vypnout zvlast."""
    blok: dict = {"prvky": dict(prvky or {})}
    if koren is not None:
        blok["koren"] = koren
    if misto:
        blok["navigace"] = dict(MISTO)
    if pasy is not None:
        blok["pasy"] = pasy
    if z_mostu:
        # `orez` je klic, ktery na prvek posila JEN most kitu - tim se pozna
        # scena, o ktere se SMI rict, ze v ni priznak chybi.
        blok["prvky"].setdefault("neco.0", {})["orez"] = {
            "sirka_obsahu": 10, "sirka_schranky": 10,
            "vyska_obsahu": 10, "vyska_schranky": 10,
        }
    return blok


def _zpet(obdelnik=OBDELNIK, wid="zpet.10", **kw):
    return _w(wid, *obdelnik, **kw)


def _issues(data):
    return validate_data(data, file_label=FL, warnings_as_errors=False)


def _msgs(data):
    return [i.message for i in _issues(data)]


def _errors(data):
    return [i.message for i in _issues(data) if i.level == "ERROR"]


def _warns(data):
    return [i.message for i in _issues(data) if i.level == "WARN"]


def _obsahuji(zpravy, kus):
    return [z for z in zpravy if kus in z]


def _ve_fixture(cesta, znacka, uroven=None):
    return [
        i.message
        for i in validate_file(cesta, warnings_as_errors=False)
        if znacka in i.message and (uroven is None or i.level == uroven)
    ]


# --------------------------------------------------------------------------- #
# Pozitivni trida A: koren s tlacitkem Zpet
# --------------------------------------------------------------------------- #


def test_r153_koren_s_tlacitkem_Zpet_je_ERROR():
    d = _scena([_zpet()], _navrh(koren=True))
    nalezy = _obsahuji(_errors(d), ZNACKA_R153_KOREN)
    assert len(nalezy) == 1
    assert "'zpet.10' (112x81 na 1148,8)" in nalezy[0]
    assert "KOREN navigace" in nalezy[0]


def test_r153_koren_hlasi_KAZDE_tlacitko_zvlast():
    """Dve tlacitka = dva sliby bez pokryti, ne jeden souhrn."""
    d = _scena([_zpet(), _zpet(wid="zpet.11")], _navrh(koren=True))
    assert len(_obsahuji(_errors(d), ZNACKA_R153_KOREN)) == 2


def test_r153_koren_se_na_polohu_uz_nepta():
    """Na koreni je vadou SAMA EXISTENCE. Jedna obet, jeden nalez."""
    d = _scena([_zpet((1149, 8, 112, 81))], _navrh(koren=True))
    zpravy = _msgs(d)
    assert len(_obsahuji(zpravy, ZNACKA_R153_KOREN)) == 1
    assert _obsahuji(zpravy, ZNACKA_R153_MISTO) == []


# --------------------------------------------------------------------------- #
# Pozitivni trida B: ne-koren bez tlacitka Zpet
# --------------------------------------------------------------------------- #


def test_r153_nekoren_bez_Zpet_je_ERROR():
    d = _scena([_w("stitek.0", 36, 129, 200, 24, text="Soubory", t="label")],
               _navrh(koren=False))
    nalezy = _obsahuji(_errors(d), ZNACKA_R153_CHYBI)
    assert len(nalezy) == 1
    assert R153_TRIDA in nalezy[0] and R153_PAS in nalezy[0]


def test_r153_KONTROLNI_SKUPINA_jiny_dotykovy_ovladac_Zpet_nenahradi():
    """Dlazdice je tlacitko a zmacknout se da - ale zpatky nevede.

    Bez teto kontroly by stacilo, aby na listu byl jakykoli knoflik, a
    pravidlo by se dalo splnit necim jinym, nez o cem mluvi.
    """
    d = _scena([_w("dlazdice.0", 48, 320, 386, 120, text="Terminal")],
               _navrh(koren=False))
    assert _obsahuji(_errors(d), ZNACKA_R153_CHYBI)


def test_r153_schovane_tlacitko_neni_slib():
    """`visible: false` se preskakuje jako v Rule 135, 136 a 152.

    Firmware Domova presne tohle dela (LV_OBJ_FLAG_HIDDEN v shell.cpp) a je
    to spravne chovani: na co se neda sahnout, to nic neslibuje. Obe strany
    mince: na ne-koreni takove tlacitko list NEZACHRANI.
    """
    schovany = dict(_zpet(), visible=False)
    d_koren = _scena([schovany], _navrh(koren=True))
    assert _obsahuji(_msgs(d_koren), ZNACKA_R153_KOREN) == []
    d_list = _scena([schovany], _navrh(koren=False))
    assert _obsahuji(_errors(d_list), ZNACKA_R153_CHYBI)


# --------------------------------------------------------------------------- #
# Pozitivni trida C: poloha (hranice na pixel)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("obdelnik", "ceka_nalez"),
    [
        ((1148, 8, 112, 81), False),  # deklarovane misto
        ((1149, 8, 112, 81), True),   # o 1 px vpravo
        ((1147, 8, 112, 81), True),   # o 1 px vlevo
        ((1148, 9, 112, 81), True),   # o 1 px niz
        ((1148, 7, 112, 81), True),   # o 1 px vys
        ((1148, 8, 113, 81), True),   # o 1 px sirsi
        ((1148, 8, 111, 81), True),   # o 1 px uzsi
        ((1148, 8, 112, 82), True),   # o 1 px vyssi
        ((1148, 8, 112, 80), True),   # o 1 px nizsi
    ],
    ids=["na miste", "x+1", "x-1", "y+1", "y-1", "w+1", "w-1", "h+1", "h-1"],
)
def test_r153_hranice_je_jediny_pixel_ve_vsech_ctyrech_cislech(obdelnik, ceka_nalez):
    """Bez tolerance, a je to zmerena volba, ne prisnost pro prisnost:

    slot i tlacitko jsou cela cisla z tehoz `tokens.json` a mezi nimi neni
    zadny prevod, ktery by zaokrouhloval. (Rule 136 tolerance 1 px MA -
    tam se zaokrouhluji dve hrany obdelniku zvlast a jednopixelovy rozdil je
    artefakt mereni. Tady zadne takove mereni neni.)
    """
    d = _scena([_zpet(obdelnik)], _navrh(koren=False))
    nalezy = _obsahuji(_errors(d), ZNACKA_R153_MISTO)
    assert bool(nalezy) is ceka_nalez
    if ceka_nalez:
        assert f"stoji {obdelnik[2]}x{obdelnik[3]} na {obdelnik[0]},{obdelnik[1]}" in nalezy[0]
        assert "deklarovane misto je 112x81 na 1148,8" in nalezy[0]


def test_r153_poloha_se_NEMERI_proti_pasu_navigace():
    """Klicova zkouska: pas si posunuty knoflik posune S SEBOU.

    Na listech kitu zaklada pas `navigace` sam prvek `.zpet`, takze meridlo
    postavene na pasu meri tlacitko proti sobe samemu. Tady je pas i tlacitko
    na 1149 a Rule 136 proto mlci - nalez vyda JEDINE deklarace z tokens.json.
    """
    posunuty = (1149, 8, 112, 81)
    d = _scena(
        [_zpet(posunuty)],
        _navrh(koren=False,
               pasy={"navigace": list(posunuty)},
               prvky={"zpet.10": {"pas": R153_PAS}}),
    )
    zpravy = _msgs(d)
    assert _obsahuji(zpravy, ZNACKA_R136_PAS_VEN) == [], "Rule 136 tu nema co merit"
    assert len(_obsahuji(_errors(d), ZNACKA_R153_MISTO)) == 1


def test_r153_vic_tlacitek_Zpet_je_ERROR():
    d = _scena([_zpet(), _zpet(wid="zpet.11")], _navrh(koren=False))
    nalezy = _obsahuji(_errors(d), ZNACKA_R153_VIC)
    assert len(nalezy) == 1
    assert "zpet.10, zpet.11" in nalezy[0]


# --------------------------------------------------------------------------- #
# Dva podpisy teze veci: trida a pas
# --------------------------------------------------------------------------- #


def test_r153_druhy_podpis_dotykovy_prvek_v_pasu_navigace():
    """Prejmenovana trida pravidlo neumlci: rozhoduje i PAS.

    Kdyby stacil jeden podpis, ma pravidlo jedno misto, kde se da vypnout -
    stacilo by prekrtit `.zpet` na `.navrat` a Zpet nakresleny na koreni by
    zmizel z mereni (falesna zelena).
    """
    d = _scena(
        [_w("navrat.10", *OBDELNIK)],
        _navrh(koren=True, pasy={"navigace": list(OBDELNIK)},
               prvky={"navrat.10": {"pas": R153_PAS}}),
    )
    assert len(_obsahuji(_errors(d), ZNACKA_R153_KOREN)) == 1


def test_r153_KONTROLNI_SKUPINA_panel_v_pasu_navigace_neni_Zpet():
    """Artboard `Ramec` kresli do pasu obdelnik `.zona`, ktery jen UKAZUJE,

    kde navigace lezi. Je to panel, ne tlacitko, a druha pulka podminky
    (`typ` je dotykovy) je tu prave proto, aby ho pravidlo neobvinilo.
    """
    d = _scena(
        [_w("zona.3", *OBDELNIK, text="", t="panel")],
        _navrh(koren=True, pasy={"navigace": list(OBDELNIK)},
               prvky={"zona.3": {"pas": R153_PAS}}),
    )
    assert _obsahuji(_msgs(d), ZNACKA_R153_KOREN) == []


def test_r153_trida_zpet_staci_i_bez_pasu():
    """Druha pulka teze uvahy: zapomenuty `data-pas` nesmi udelat

    z existujiciho tlacitka "chybi". Trida z generatoru staci sama.
    """
    d = _scena([_zpet()], _navrh(koren=False))
    assert _obsahuji(_msgs(d), ZNACKA_R153_CHYBI) == []
    assert _obsahuji(_msgs(d), ZNACKA_R153_MISTO) == []


# --------------------------------------------------------------------------- #
# Negativni trida
# --------------------------------------------------------------------------- #


def test_r153_nekoren_se_Zpet_na_miste_mlci():
    d = _scena([_zpet()], _navrh(koren=False))
    assert _obsahuji(_msgs(d), "Zpet") == []


def test_r153_koren_bez_Zpet_mlci():
    d = _scena([_w("dlazdice.0", 48, 320, 386, 120, text="Terminal")],
               _navrh(koren=True))
    assert _obsahuji(_msgs(d), "Zpet") == []


def test_r153_TATAZ_KRESBA_opacny_verdikt_podle_priznaku():
    """Jadro pravidla v jedne zkousce: dva listy, tataz kresba, jediny

    rozdil je `navrh.koren`. Kdyby pravidlo rozhodovalo z kresby, musely by
    oba dopadnout stejne.
    """
    kresba = [_w("dlazdice.0", 48, 320, 386, 120, text="Terminal")]
    koren = _scena(copy.deepcopy(kresba), _navrh(koren=True))
    list_ = _scena(copy.deepcopy(kresba), _navrh(koren=False))
    assert _obsahuji(_msgs(koren), ZNACKA_R153_CHYBI) == []
    assert len(_obsahuji(_errors(list_), ZNACKA_R153_CHYBI)) == 1


def test_r153_scena_bez_bloku_navrh_MLCI():
    """Dokument editoru merena data legitimne nema (viz NAVRH_KLIC)."""
    d = _scena([_zpet()], None)
    assert _obsahuji(_msgs(d), "Zpet") == []
    assert _obsahuji(_msgs(d), ZNACKA_R153_NEMERENO) == []


def test_r153_cizi_navrh_bez_mereni_mostu_se_neobvinuje():
    """Blok `navrh` bez `koren` A bez `orez` = ruzne psany navrh, ne kit.

    Kdyby se NEMERENO hlasilo i tady, vystrelilo by na kazde cizi scene -
    tataz uvaha, jakou uz nesou zavory Rule 148, 150 a 151.
    """
    d = _scena([_zpet()], _navrh(koren=None, z_mostu=False))
    assert _obsahuji(_msgs(d), ZNACKA_R153_NEMERENO) == []


# --------------------------------------------------------------------------- #
# NEMERENO (fail-closed)
# --------------------------------------------------------------------------- #


def test_r153_scena_z_mostu_bez_priznaku_je_NEMERENO():
    d = _scena([_zpet()], _navrh(koren=None))
    nalezy = _obsahuji(_warns(d), ZNACKA_R153_NEMERENO)
    assert len(nalezy) == 1
    assert "NEMERILA" in nalezy[0]
    # A NIC jineho se o Zpet netvrdi: nevi se, ktera trida to je.
    assert _obsahuji(_msgs(d), ZNACKA_R153_KOREN) == []
    assert _obsahuji(_msgs(d), ZNACKA_R153_CHYBI) == []
    assert _obsahuji(_msgs(d), ZNACKA_R153_MISTO) == []


def test_r153_NEMERENO_i_kdyz_tlacitko_uplne_chybi():
    """Zavora je scena z mostu, ne pritomnost tlacitka - jinak by se

    nezmereny list bez Zpet tvaril jako v poradku.
    """
    d = _scena([_w("stitek.0", 36, 129, 200, 24, text="Soubory", t="label")],
               _navrh(koren=None))
    assert len(_obsahuji(_warns(d), ZNACKA_R153_NEMERENO)) == 1


def test_r153_bez_deklarovaneho_mista_je_poloha_NEMERENA():
    d = _scena([_zpet((999, 500, 40, 40))], _navrh(koren=False, misto=False))
    nalezy = _obsahuji(_warns(d), ZNACKA_R153_MISTO_NEMERENO)
    assert len(nalezy) == 1
    assert "POLOHA se NEMERILA" in nalezy[0]
    # Pritomnost se zmerila (tlacitko JE), poloha ne - a rekne se to.
    assert _obsahuji(_msgs(d), ZNACKA_R153_CHYBI) == []
    assert _obsahuji(_msgs(d), ZNACKA_R153_MISTO) == []


def test_r153_bez_mista_ale_bez_tlacitka_se_o_poloze_nemluvi():
    """Chybejici tlacitko je JEDEN nalez; o poloze neexistujici veci se

    nemluvi vubec (tataz obet nesmi dostat dva nalezy).
    """
    d = _scena([], _navrh(koren=False, misto=False))
    assert len(_obsahuji(_errors(d), ZNACKA_R153_CHYBI)) == 1
    assert _obsahuji(_msgs(d), ZNACKA_R153_MISTO_NEMERENO) == []


def test_r153_obe_znacky_NEMERENO_konci_jmennou_konvenci_mostu():
    """Most kitu sbira fail-closed hlasky podle JMENA konstanty

    (`ZNACKA_*_NEMERENO`), ne podle obsahu vety - viz `do_espos.znacky_nemereno`.
    """
    assert ZNACKA_R153_NEMERENO.isascii()
    assert ZNACKA_R153_MISTO_NEMERENO.isascii()
    for z in (ZNACKA_R153_KOREN, ZNACKA_R153_CHYBI, ZNACKA_R153_MISTO,
              ZNACKA_R153_VIC):
        assert z.isascii()
    assert len({ZNACKA_R153_KOREN, ZNACKA_R153_CHYBI, ZNACKA_R153_MISTO,
                ZNACKA_R153_VIC, ZNACKA_R153_NEMERENO,
                ZNACKA_R153_MISTO_NEMERENO}) == 6


# --------------------------------------------------------------------------- #
# Vadna data se hlasi nahlas, ne tise nevypinaji pravidlo
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("hodnota", ["false", "true", 0, 1, None])
def test_r153_koren_musi_byt_PRAVDIVOSTNI_hodnota(hodnota):
    """Retezec "false" je v Pythonu PRAVDIVY: kdyby se prekladal, otocil by

    obe tridy naruby. `None` je zvlast: to znamena "klic tu neni".
    """
    blok = _navrh(koren=None)
    if hodnota is not None:
        blok["koren"] = hodnota
    d = _scena([_zpet()], blok)
    if hodnota is None:
        assert _obsahuji(_warns(d), ZNACKA_R153_NEMERENO)
        return
    nalezy = _obsahuji(_errors(d), ZNACKA_NAVRH_VADNY)
    assert [z for z in nalezy if "'koren'" in z]
    # Vadny priznak neni priznak: pravidlo pak o tridach nic netvrdi.
    assert _obsahuji(_msgs(d), ZNACKA_R153_KOREN) == []


@pytest.mark.parametrize(
    "navigace",
    [[1148, 8, 112, 81], "1148,8", {"x": 1148, "y": 8, "w": 112},
     {"x": 1148, "y": 8, "w": 0, "h": 81}, {"x": -1, "y": 8, "w": 112, "h": 81},
     {"x": 1148, "y": 8, "w": 112.5, "h": 81}],
    ids=["seznam", "retezec", "chybi h", "nulova sirka", "zaporne x", "desetinne"],
)
def test_r153_vadna_deklarace_mista_je_ERROR_a_ne_ticho(navigace):
    blok = _navrh(koren=False)
    blok["navigace"] = navigace
    d = _scena([_zpet()], blok)
    assert [z for z in _errors(d) if ZNACKA_NAVRH_VADNY in z and "navigace" in z]
    # Preklep pravidlo NEVYPNE: poloha se pak hlasi jako nezmerena.
    assert _obsahuji(_warns(d), ZNACKA_R153_MISTO_NEMERENO)


# --------------------------------------------------------------------------- #
# Fixtury
# --------------------------------------------------------------------------- #


def test_r153_fixtury_vad_hlasi_kazda_PRAVE_JEDNU_svou_tridu():
    assert len(_ve_fixture(KOREN_VADY, ZNACKA_R153_KOREN, "ERROR")) == 1
    assert len(_ve_fixture(CHYBI_VADY, ZNACKA_R153_CHYBI, "ERROR")) == 1
    assert len(_ve_fixture(MISTO_VADY, ZNACKA_R153_MISTO, "ERROR")) == 1


def test_r153_fixtury_vad_nemaji_ZADNY_jiny_ERROR():
    """Izolace mereni: kdyby fixtura nesla i cizi vadu, nedalo by se poznat,

    ze cerveno je od pravidla 153.
    """
    for cesta in (KOREN_VADY, CHYBI_VADY, MISTO_VADY):
        chyby = [i.message for i in validate_file(cesta, warnings_as_errors=False)
                 if i.level == "ERROR"]
        assert len(chyby) == 1, (cesta.name, chyby)


def test_r153_ciste_fixtury_o_Zpet_MLCI():
    for cesta in (CISTE, KOREN_CISTE):
        zpravy = [i.message for i in validate_file(cesta, warnings_as_errors=False)]
        assert _obsahuji(zpravy, "Zpet") == [], cesta.name
        assert [i for i in validate_file(cesta, warnings_as_errors=False)
                if i.level == "ERROR"] == []


def test_r153_dvojice_fixtur_se_lisi_JEDINYM_klicem():
    """`chybi_vady` a `koren_ciste` maji bajt po bajtu tutez kresbu i tyz

    blok `navrh` az na `koren`. Opacny verdikt tedy nemuze pochazet
    z niceho jineho.
    """
    a = json.loads(CHYBI_VADY.read_text(encoding="utf-8"))["scenes"]["main"]
    b = json.loads(KOREN_CISTE.read_text(encoding="utf-8"))["scenes"]["main"]
    assert a["widgets"] == b["widgets"]
    assert a["navrh"]["koren"] is False and b["navrh"]["koren"] is True
    del a["navrh"]["koren"], b["navrh"]["koren"]
    assert a["navrh"] == b["navrh"]


def test_r153_fixtura_mista_ma_pas_POSUNUTY_s_tlacitkem():
    """Doklad, ze fixtura opravdu meri to, co slibuje: pas navigace je na

    1149 stejne jako tlacitko, takze meridlo postavene na pasu by mlcelo.
    """
    m = json.loads(MISTO_VADY.read_text(encoding="utf-8"))["scenes"]["main"]
    zpet = next(w for w in m["widgets"] if w["_widget_id"] == "zpet.10")
    assert zpet["x"] == 1149
    assert m["navrh"]["pasy"]["navigace"] == [1149, 8, 112, 81]
    assert m["navrh"]["navigace"] == MISTO
    assert _ve_fixture(MISTO_VADY, ZNACKA_R136_PAS_VEN) == []


def test_r153_odebrani_deklarace_z_ciste_fixtury_zmlkne_o_poloze():
    """Pozitivni kontrola zavory: bez `navigace` prestane byt cista fixtura

    dokladem o poloze a rekne to.
    """
    d = json.loads(CISTE.read_text(encoding="utf-8"))
    assert _obsahuji(_msgs(d), ZNACKA_R153_MISTO_NEMERENO) == []
    bez = copy.deepcopy(d)
    del bez["scenes"]["main"]["navrh"]["navigace"]
    assert len(_obsahuji(_warns(bez), ZNACKA_R153_MISTO_NEMERENO)) == 1


def test_r153_dva_behy_tyz_vysledek():
    d = _scena([_zpet((1149, 8, 112, 81)), _zpet((1150, 8, 112, 81), wid="zpet.11")],
               _navrh(koren=False))
    assert _msgs(d) == _msgs(d)


# --------------------------------------------------------------------------- #
# Cisla proti primarnimu udaji (kdyz je kit po ruce)
# --------------------------------------------------------------------------- #

KIT_TOKENY = (
    pathlib.Path(__file__).resolve().parents[3] / "tabos-ui-kit" / "tokens.json"
)


@pytest.mark.skipif(not KIT_TOKENY.is_file(), reason="kit neni vedle ESPOSu")
def test_r153_cisla_fixtur_sedi_s_tokens_kitu():
    """Fixtury nesmi zit vlastnim zivotem: 1148/8/112/81 je `tokens.json`.

    Kdyz se rozvrzeni zmeni, ma tahle zkouska zcervenat a fixtury se maji
    pregenerovat (`tests/fixtures/gen_zpet_koren.py`), ne tise zastarat.
    """
    lay = json.loads(KIT_TOKENY.read_text(encoding="utf-8"))["layout"]
    assert MISTO["x"] == lay["zpet"]["x"]
    assert MISTO["w"] == lay["zpet"]["w"]
    assert MISTO["y"] == lay["hlavicka"]["y"]
    assert MISTO["h"] == lay["hlavicka"]["h"]
