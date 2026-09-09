"""Regresni fixtury z druheho pruchodu panelem Tab5 (2026-09-09, screeny3).

Druhy adresar vedle `panel_2026-09-08/` - tentyz duvod, proc ma prvni
pruchod datum ve jmene: obe sady bezi vedle sebe a zadna neprepisuje druhou.
Tady jsou TRIDY, ktere prvni pruchod NEMEL, protoze je videl az nastroj
`tabos-core/tools/deska_regrese.py --z-adresare screeny3` (kolo 4):

1. **Behove prazdno** (R138, `prazdny smalt`): hodnota, kterou appka nikdy
   nezapsala. Razitko Hexu SOUBOR / OKNO / ZOBRAZENO (tri SAMOSTATNE prvky bez
   textu - 2026-09-08 mel JEDEN prvek s pomlckami, coz je R139, jina trida),
   POKRYTI a sloupce PROPUSTNOST / ZTRATY na Koexu, VYMEN + ROZPTYL + PLATNE
   VYMENY + DUVERA + smalt VZDALENOST na FTM, SITI v Network Tools. Zmereno
   nad snimkem: inkoust 0,0 % v bunce (deska_regrese, sloupec `prazdne
   hodnoty`). `brana_prazdny_smalt` to nevidi - cte literaly, ne beh.

2. **Pas bez clena** - VADA BEZ MERIDLA, a je to tu napsane nahlas: LA SPOUST,
   LA SMYCKA (modalni panel kresli titulek uvnitr obsahu, pas hlavicky je
   prazdny, cara razitka chybi) a RF VYBER LISTU (titulek ma, razitko ne).
   R136 meri PRVKY proti pasum; pas, ve kterem nikdo neni, nikoho neorezava
   a pravidlo mlci. Obe tridy (panel jak je / s doplnenym clenem) jsou bez
   chyby a test to pribiji: az nekdo pas bez clena zacne merit, tenhle test
   zcervena a cislo v `CEKANE_CHYBY_VAD` se zvedne s duvodem. Nad snimkem
   to dnes meri jen `deska_stranky.invarianty_ramce` (kit) - tedy jine
   meridlo, jina vrstva.

Kazda fixtura nese `_puvod` (ktera cisla jsou z artboardu, ktera z panelu,
kde je vlozena vada). Vsechny fixtury vyrobil skript ze scen mostu
(`do_espos.py --zapis-scenu`), takze souradnice jsou zmerene, ne opsane.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.validate_design import (
    ZNACKA_R136_PAS,
    ZNACKA_R136_PAS_VEN,
    ZNACKA_R138,
    ZNACKA_R138_OZNACENI,
    ZNACKA_R139,
    ZNACKA_R143,
    validate_data,
    validate_file,
)

FIXTURY = pathlib.Path(__file__).parent / "fixtures" / "panel_2026-09-09"
STARSI = pathlib.Path(__file__).parent / "fixtures" / "panel_2026-09-08"

OBRAZOVKY = [
    "panel_hex_runtime",
    "panel_rf_koex",
    "panel_rf_ftm",
    "panel_network",
    "panel_la_spoust",
    "panel_la_smycka",
    "panel_rf_vyber",
]

# Obrazovky, jejichz vada NEMA meridlo: vadna trida je (zatim) bez chyby a
# test to drzi vyslovne, aby ticho nevypadalo jako "zmereno a v poradku".
BEZ_MERIDLA = {"panel_la_spoust", "panel_la_smycka", "panel_rf_vyber"}

# Rozpad chyb PO OBRAZOVKACH (tataz pojistka jako v test_regrese_panel.py:
# soucet 12 by prezil vymenu "jedna ubyla, jina pribyla").
CEKANE_CHYBY_VAD = {
    "panel_hex_runtime": 3,    # R138 x3 (SOUBOR, OKNO, ZOBRAZENO)  + 1 WARN R143 (microSD: nedostupne)
    "panel_rf_koex": 3,        # R138 x3 (POKRYTI, PROPUSTNOST A, ZTRATY A)
    "panel_rf_ftm": 5,         # R138 x5 (VYMEN, smalt VZDALENOST, ROZPTYL, PLATNE, DUVERA)
    "panel_network": 1,        # R138 x1 (SITI)
    "panel_la_spoust": 0,      # pas bez clena - BEZ MERIDLA
    "panel_la_smycka": 0,      # pas bez clena - BEZ MERIDLA
    "panel_rf_vyber": 0,       # razitko bez clena - BEZ MERIDLA
}


def _cesta(jmeno: str, trida: str) -> pathlib.Path:
    return FIXTURY / f"{jmeno}_{trida}.json"


def _issues(jmeno: str, trida: str):
    return validate_file(_cesta(jmeno, trida), warnings_as_errors=False)


def _zpravy(jmeno: str, trida: str) -> list[str]:
    return [i.message for i in _issues(jmeno, trida)]


def _chyby(jmeno: str, trida: str) -> list[str]:
    return [i.message for i in _issues(jmeno, trida) if i.level == "ERROR"]


def _obsahuji(zpravy: list[str], kus: str) -> list[str]:
    return [m for m in zpravy if kus in m]


def _scena(jmeno: str, trida: str) -> dict:
    return json.loads(_cesta(jmeno, trida).read_text(encoding="utf-8"))


def _chyby_dat(doc: dict) -> list[str]:
    return [i.message for i in validate_data(doc, file_label="t", warnings_as_errors=False) if i.level == "ERROR"]


def _widget(doc: dict, wid: str) -> dict:
    return next(w for w in doc["scenes"]["main"]["widgets"] if w["_widget_id"] == wid)


# --------------------------------------------------------------------------- #
# Nosic
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("jmeno", OBRAZOVKY)
@pytest.mark.parametrize("trida", ["vady", "ciste"])
def test_kazda_obrazovka_ma_obe_tridy_a_puvod(jmeno: str, trida: str):
    assert _cesta(jmeno, trida).is_file()
    doc = _scena(jmeno, trida)
    assert doc["_puvod"].strip() and doc["device"] == "tab5"
    assert "2026-09-09" in doc["_puvod"]


def test_zadna_fixtura_nelezi_v_adresari_bez_testu():
    na_disku = {p.name for p in FIXTURY.glob("panel_*.json")}
    ceka = {f"{j}_{t}.json" for j in OBRAZOVKY for t in ("vady", "ciste")}
    assert na_disku == ceka, na_disku ^ ceka


def test_novy_adresar_neprepisuje_stary_a_jmena_se_neprekryvaji():
    """Dva pruchody, dva adresare. Hex je v obou, ale pod jinym jmenem
    (`panel_hex` = pomlcky R139, `panel_hex_runtime` = prazdno R138)."""
    stare = {p.stem for p in STARSI.glob("panel_*.json")}
    nove = {p.stem for p in FIXTURY.glob("panel_*.json")}
    assert stare and nove and not (stare & nove)


@pytest.mark.parametrize("jmeno", sorted(set(OBRAZOVKY) - BEZ_MERIDLA))
def test_vadna_trida_vystreli_a_cista_nema_ani_jednu_chybu(jmeno: str):
    assert _chyby(jmeno, "vady"), f"{jmeno}: vadna fixtura nevystrelila"
    assert _chyby(jmeno, "ciste") == [], f"{jmeno}: cista fixtura hlasi chybu"


@pytest.mark.parametrize("jmeno", sorted(BEZ_MERIDLA))
def test_pas_bez_clena_je_vada_BEZ_MERIDLA_obe_tridy_mlci(jmeno: str):
    """Vadna trida = panel jak je (pas deklarovany, zadny clen); cista = clen
    doplneny. Brana je od sebe nerozezna. Az rozezna, zmen CEKANE_CHYBY_VAD."""
    assert _chyby(jmeno, "vady") == [], _chyby(jmeno, "vady")
    assert _chyby(jmeno, "ciste") == []
    z = _zpravy(jmeno, "vady")
    assert _obsahuji(z, ZNACKA_R136_PAS) == [] and _obsahuji(z, ZNACKA_R136_PAS_VEN) == []
    # a rozdil mezi tridami skutecne existuje: cista ma cleny pasu, vadna ne
    prvky_v = _scena(jmeno, "vady")["scenes"]["main"]["navrh"]["prvky"]
    prvky_c = _scena(jmeno, "ciste")["scenes"]["main"]["navrh"]["prvky"]
    assert not any(p.get("pas") == "razitko" for p in prvky_v.values())
    assert sum(1 for p in prvky_c.values() if p.get("pas") == "razitko") >= 8


# --------------------------------------------------------------------------- #
# HEX (19): tri samostatne prazdne sloty
# --------------------------------------------------------------------------- #


def test_hex_tri_sloty_razitka_bez_textu_jsou_tri_nalezy_R138():
    z = _obsahuji(_chyby("panel_hex_runtime", "vady"), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["txt.248", "txt.250", "txt.253"], z


def test_hex_prazdno_a_pomlcka_jsou_dve_ruzne_tridy():
    """Tyz slot, dve podoby: 2026-09-08 pomlcky (R139), 2026-09-09 prazdno
    (R138). Kdyby jedna pulka mlcela, druha by ji zakryla."""
    stare = [i.message for i in validate_file(STARSI / "panel_hex_vady.json", warnings_as_errors=False)
             if i.level == "ERROR"]
    assert _obsahuji(stare, ZNACKA_R139) and not _obsahuji(stare, ZNACKA_R138)
    nove = _chyby("panel_hex_runtime", "vady")
    assert _obsahuji(nove, ZNACKA_R138) and not _obsahuji(nove, ZNACKA_R139)


def test_hex_hranice_samotne_mezery_jsou_porad_prazdno():
    doc = _scena("panel_hex_runtime", "ciste")
    _widget(doc, "txt.248")["text"] = "   "
    z = _obsahuji(_chyby_dat(doc), ZNACKA_R138)
    assert len(z) == 1 and "txt.248" in z[0], z


def test_hex_KONTROLNI_SKUPINA_prazdne_s_vetou_mlci_a_bez_vety_ne():
    doc = _scena("panel_hex_runtime", "vady")
    doc["scenes"]["main"]["navrh"]["prvky"]["txt.248"]["prazdne"] = "bez karty neni co ukazat"
    z = _obsahuji(_chyby_dat(doc), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["txt.250", "txt.253"], z
    doc["scenes"]["main"]["navrh"]["prvky"]["txt.248"]["prazdne"] = "   "
    assert len(_obsahuji(_chyby_dat(doc), ZNACKA_R138)) == 3


def test_hex_oznaceni_prazdne_na_prvku_s_textem_se_pripomene():
    doc = _scena("panel_hex_runtime", "ciste")
    doc["scenes"]["main"]["navrh"]["prvky"]["txt.256"]["prazdne"] = "zamerne"
    z = [i.message for i in validate_data(doc, file_label="t", warnings_as_errors=False)]
    assert _obsahuji(z, ZNACKA_R138_OZNACENI), z


def test_hex_microSD_mimo_slovnik_je_WARN_R143_v_obou_pruchodech():
    z = [i for i in _issues("panel_hex_runtime", "vady") if ZNACKA_R143 in i.message]
    assert len(z) == 1 and z[0].level == "WARN"
    assert [i for i in _issues("panel_hex_runtime", "ciste") if ZNACKA_R143 in i.message] == []


# --------------------------------------------------------------------------- #
# KOEX (07): POKRYTI + sloupce PROPUSTNOST / ZTRATY
# --------------------------------------------------------------------------- #


def test_koex_POKRYTI_a_dva_sloupce_radku_A_jsou_prazdne():
    z = _obsahuji(_chyby("panel_rf_koex", "vady"), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["prop.A", "txt.107", "ztr.A"], z


def test_koex_VERDIKT_nezmereno_je_slovo_a_neni_nalez():
    z = _chyby("panel_rf_koex", "vady")
    assert not [m for m in z if "verd.A" in m], z


def test_koex_hranice_hodnota_bez_role_mlci_datova_zavora():
    """R138 je gatovane roli: prvek bez `role` brana nesoudi, i kdyz je
    prazdny. To je poctiva mez - a duvod, proc sloupce v artboardu bez role
    nikdo nemeril (kritik: 'mrizka bez data-kapacita = ticho', tataz past)."""
    doc = _scena("panel_rf_koex", "vady")
    del doc["scenes"]["main"]["navrh"]["prvky"]["prop.A"]
    z = _obsahuji(_chyby_dat(doc), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["txt.107", "ztr.A"], z


def test_koex_KONTROLNI_SKUPINA_cizi_popisek_pod_prazdnym_obalem_prazdno_NEZAKRYJE():
    """Obchvat z kritiky (2026-09-09): pod prazdny smalt se polozi CIZI
    popisek a pravidlo zmlkne. Od dnesni opravy `_text_uvnitr` plati jen
    POTOMEK - cizi text, ktery jen geometricky lezi uvnitr, nic nezakryje."""
    doc = _scena("panel_rf_koex", "vady")
    obal = _widget(doc, "prop.A")
    obal["x"], obal["y"], obal["width"], obal["height"] = 800, 420, 180, 60   # obal pres popis.65
    z = _obsahuji(_chyby_dat(doc), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["prop.A", "txt.107", "ztr.A"], z


def test_koex_hranice_potomek_s_textem_uvnitr_obalu_prazdno_zakryje():
    """Druha pulka teze meze: kdyz je popisek POTOMKEM obalu (`rodic` = presne
    obdelnik obalu, tak to vozi most), sdeleni uvnitr JE a R138 mlci. Je to
    poctiva mez pravidla (role na obalu, ne na hodnote) - tady je zmerena."""
    doc = _scena("panel_rf_koex", "vady")
    obal = _widget(doc, "prop.A")
    obal["x"], obal["y"], obal["width"], obal["height"] = 800, 420, 180, 60
    doc["scenes"]["main"]["navrh"]["prvky"]["popis.65"]["rodic"] = [800, 420, 180, 60]
    z = _obsahuji(_chyby_dat(doc), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["txt.107", "ztr.A"], z


# --------------------------------------------------------------------------- #
# FTM (08): pet prazdnych mist na jedne obrazovce
# --------------------------------------------------------------------------- #


def test_ftm_pet_prazdnych_mist_pet_nalezu():
    z = _obsahuji(_chyby("panel_rf_ftm", "vady"), ZNACKA_R138)
    assert sorted(m.split(" (")[1].split(")")[0] for m in z) == ["txt.84", "v.16", "v.duvera", "v.platne", "v.rozptyl"], z


def test_ftm_KALIBRACE_ma_slovo_a_neni_nalez_v_zadne_tride():
    for trida in ("vady", "ciste"):
        assert not [m for m in _chyby("panel_rf_ftm", trida) if "v.kalib" in m]


def test_ftm_smalt_i_hodnota_jsou_tataz_vada_s_jinou_roli():
    z = _obsahuji(_chyby("panel_rf_ftm", "vady"), ZNACKA_R138)
    assert any("v.16" in m and "role 'smalt'" in m for m in z)
    assert any("v.rozptyl" in m and "role 'hodnota'" in m for m in z)


def test_ftm_po_oprave_mlci():
    assert _obsahuji(_chyby("panel_rf_ftm", "ciste"), ZNACKA_R138) == []


# --------------------------------------------------------------------------- #
# NETWORK (22): SITI prazdne; seznam siti = plocha bez prvku (bez meridla)
# --------------------------------------------------------------------------- #


def test_network_SITI_prazdne_je_jediny_nalez():
    z = _chyby("panel_network", "vady")
    assert len(z) == 1 and "txt.126" in z[0] and ZNACKA_R138 in z[0], z


def test_network_prazdny_seznam_siti_je_vada_BEZ_MERIDLA():
    """Plocha y 452..570 pod KDO TAM JE je na panelu prazdna. Neni to prvek,
    nema roli, nema text - zadne pravidlo ji nesoudi. Rika se to tu nahlas."""
    z = _zpravy("panel_network", "ciste")
    assert [m for m in z if "KDO TAM JE" in m] == [], z


def test_network_SKENU_nedostupne_je_slovo_ne_nalez():
    assert not [m for m in _chyby("panel_network", "vady") if "txt.123" in m]


# --------------------------------------------------------------------------- #
# Souhrn
# --------------------------------------------------------------------------- #


def test_souhrn_pokryti_fotoprotokolu_2026_09_09():
    zmereno = {jm: len(_chyby(jm, "vady")) for jm in OBRAZOVKY}
    assert zmereno == CEKANE_CHYBY_VAD, (
        f"rozpad chyb po obrazovkach se zmenil:\n  ceka se {CEKANE_CHYBY_VAD}\n  zmereno {zmereno}\n"
        f"Kdyz pravidlo pribylo nebo ubylo, oprav CEKANE_CHYBY_VAD a napis do komentare, ktere to bylo.")
    assert sum(zmereno.values()) == 12, sum(zmereno.values())
    assert all(zmereno[j] == 0 for j in BEZ_MERIDLA)
