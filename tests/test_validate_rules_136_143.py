"""Testy pravidel 136-143 v `tools/validate_design.py`.

Pravidla nad MERENYMI daty z artboardu (scenovy blok ``navrh``, ktery vozi
most `tabos-ui-kit/navrh-appky/do_espos.py`). Chytaji vady, ktere koordinator
nasel ocima na skutecnem panelu Tab5 a ktere z holych souradnic widgetu poznat
nejdou.

Rule 136: oriznuti - prvek presahuje sveho rodice nebo zasahuje do vyhrazeneho
          pasu (dlazdice RF Sonda useknuta patkou na Domove)
Rule 137: preteceni textu ZMERENYM fontem, ne odhadem z poctu znaku
          (stitek FIRMWARE "V0.4-71-gee91351-dirty ·" useknuty v razitku)
Rule 138: prazdny smalt - hodnotova role, ktera nenese zadne sdeleni
          (Terminal PORT a PRIJATO, Files VOLNO, USB "CO TO JE", SysMon
          TEPLOTA RADIA)
Rule 139: pomlcka misto hodnoty - "\u2014" jako cely text hodnoty
          (Logic Analyzer "SPOUST \u2014", patky "\u2014")
Rule 140: kapacita mrizky - deklarovana kapacita listu proti poctu polozek,
          ktere na nej maji jit (Domu ma dvanact slotu, registr appek jedenact
          polozek; trinacta by se ztratila MIMO scenu)
Rule 141: DPI firmwaru proti PPI panelu - `zkontroluj_dpi()` je CISTE TEXTOVA
          funkce, soubory firmwaru cte most (`do_espos.dpi_firmwaru`), aby
          validator zustal zavisly jen na dokumentu, ktery dostal
Rule 142: veta pro cloveka nese strojove jmeno - sedm tvaru se vzory
          byte-identickymi s `tabos-core/tools/brana_vety.py` (Settings
          "IHwDiagnostics" a "%.1f", Network "INetworkService::startScan()",
          SysMon "ISystemMetrics::radioTemp", patka Diagnostics)
Rule 143: slovnik stavu teze veci - o microSD mluvi Diagnostics, Files i Hex
          kazdy jinak; vsechny tri se meri proti JEDNOMU slovniku, takze se
          rozpor napric listy chyta bez globalniho stavu (WARNING)

Ke kazdemu pravidlu tu je POZITIVNI trida (pravidlo vystreli), NEGATIVNI
(mlci) i hranice na pixel. Navic tri veci, bez kterych by testy netestovaly
nic:

* **Nosic je legalni.** Fixtura s blokem ``navrh`` jde pres `validate_file`,
  tedy vcetne POVINNE JSON schematu - jinak by se neoverilo, ze scena takovy
  blok vubec smi nest.
* **Vypnuti Rule 7 ma pozitivni kontrolu.** Tyz widget bez zmerene sirky MUSI
  dat WARN Rule 7; bez toho by test "Rule 7 mlci" prosel i kdyby Rule 7 na
  ten tvar nikdy nestrilela.
* **Nemereno != cisto.** Kdyz blok chybi, pravidla mlci; kdyz je vadny nebo
  domereny jen z poloviny, rekne se to nahlas.
* **Rule 142 meri i to, co nikdo nemeril.** Je jedine gatovane PROFILEM, tedy
  bezi nad kazdym tab5 textem vcetne starsich fixtur - proto tu je test, ktery
  hlida, ze na nich mlci (zmereny dopad na stavajici korpus je nula).
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.validate_design import (
    DRUHY_LISTU,
    POMLCKY,
    PRIPONY_SOUBORU,
    PROFILE_OLED256,
    PROFILE_TAB5,
    VETY_NENI_JMENO_SDK,
    VETY_NENI_ROZHRANI,
    VETY_PREDPONY_SDK,
    VETY_VYJIMKY,
    VETY_VZORY,
    ZNACKA_NAVRH_VADNY,
    ZNACKA_R136_OZNACENI,
    ZNACKA_R136_PAS,
    ZNACKA_R136_PAS_VEN,
    ZNACKA_R136_RODIC,
    ZNACKA_R137,
    ZNACKA_R137_NEMERENO,
    ZNACKA_R138,
    ZNACKA_R138_OZNACENI,
    ZNACKA_R139,
    ZNACKA_R139_ZASTUPNY,
    ZNACKA_R140,
    ZNACKA_R140_NEMERENO,
    ZNACKA_R141,
    ZNACKA_R141_NEMERENO,
    ZNACKA_R141_ODCHYLKA,
    ZNACKA_R142,
    ZNACKA_R142_NEMERENO,
    ZNACKA_R142_VYKLAD,
    ZNACKA_R143,
    ZNACKA_R143_NEMERENO,
    _veta_strojove_jmeno,
    jmena_ze_sdk,
    validate_data,
    validate_file,
    zkontroluj_dpi,
)

FL = "test"
FIXTURY = pathlib.Path(__file__).parent / "fixtures"
CISTA = FIXTURY / "tab5_navrh_ciste.json"
VADNA = FIXTURY / "tab5_navrh_vady.json"
SMALT_CISTA = FIXTURY / "tab5_smalt_ciste.json"
SMALT_VADNA = FIXTURY / "tab5_smalt_vady.json"
MRIZKA_CISTA = FIXTURY / "tab5_mrizka_ciste.json"
MRIZKA_VADNA = FIXTURY / "tab5_mrizka_vady.json"
JAZYK_CISTA = FIXTURY / "tab5_jazyk_ciste.json"
JAZYK_VADY = FIXTURY / "tab5_jazyk_vady.json"
KORPUS_VET = FIXTURY / "vety_korpus.json"
SDK_HLAVICKA = FIXTURY / "sdk_hlavicka.h"

# Pomlcky, kterymi se na panelu psalo "nic nevim". V testech jako escape:
# v editoru se od sebe nerozezna, ktera je ktera.
POMLCKA = "\u2014"
POMLCKA_KRATKA = "\u2013"

# Pas razitka (patky) tak, jak ho meri artboard kitu: PAD, OBSAH_Y + POLE_H
# - RAZ_H, POLE_W, RAZ_H.
PAS_RAZITKO = {"razitko": [20, 612, 1240, 88]}

# Obdelnik `.obsah`, tedy RODIC, ktery most u clenu pasu skutecne vydava
# (`ramecek(el.offsetParent)`). Fixtura tu do 2026-09-09 mela obdelnik PASU
# - tvar, ktery most nikdy nevyrobi: kritik zmeril 0 z 368 clenu pasu
# s rodicem == pas. Test pribijel predpoklad, ne skutecnost.
OBSAH = [20, 97, 1240, 603]


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


def _errors(data, **kw):
    return [i.message for i in _issues(data, **kw) if i.level == "ERROR"]


def _warns(data, **kw):
    return [i.message for i in _issues(data, **kw) if i.level == "WARN"]


def _obsahuji(zpravy, kus):
    return [m for m in zpravy if kus in m]


# --------------------------------------------------------------------------- #
# Nosic dat: scenovy blok "navrh"
# --------------------------------------------------------------------------- #


def test_znacky_pravidel_jsou_ASCII():
    """Hlasky se tisknou i na holou cp1250 konzoli; znacka musi projit vzdy."""
    for znacka in (
        ZNACKA_NAVRH_VADNY,
        ZNACKA_R136_RODIC,
        ZNACKA_R136_PAS,
        ZNACKA_R137,
        ZNACKA_R137_NEMERENO,
        ZNACKA_R138,
        ZNACKA_R138_OZNACENI,
        ZNACKA_R139,
        ZNACKA_R140,
        ZNACKA_R140_NEMERENO,
        ZNACKA_R141,
        ZNACKA_R141_NEMERENO,
        ZNACKA_R142,
        ZNACKA_R143,
        ZNACKA_R143_NEMERENO,
    ):
        assert znacka == znacka.encode("ascii", "replace").decode("ascii")


def test_bez_bloku_navrh_pravidla_mlci():
    """Prvek presahujici to, co by byl jeho rodic - ale nikdo to nezmeril."""
    d = _make([_w("dlazdice.07", 446, 240, 386, 76)])
    msgs = _msgs(d)
    assert _obsahuji(msgs, ZNACKA_R136_RODIC) == []
    assert _obsahuji(msgs, ZNACKA_R136_PAS) == []
    assert _obsahuji(msgs, ZNACKA_R137) == []
    assert _obsahuji(msgs, ZNACKA_NAVRH_VADNY) == []


def test_blok_navrh_neni_objekt_je_ERROR():
    d = _make([_w("a", 10, 10, 100, 20)], navrh=["prvky"])
    assert f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'navrh' ma byt objekt, je list" in _errors(d)


def test_prvky_nejsou_objekt_je_ERROR():
    d = _make([_w("a", 10, 10, 100, 20)], navrh={"prvky": []})
    assert f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky' ma byt objekt, je list" in _errors(d)


def test_vadny_rodic_je_ERROR_a_pravidlo_nemeri():
    """Preklep v datech nesmi pravidlo TISE vypnout (meridlo selhalo != nula)."""
    d = _make(
        [_w("dlazdice.07", 446, 240, 386, 76)],
        navrh={"prvky": {"dlazdice.07": {"rodic": [446, 240]}}},
    )
    msgs = _msgs(d)
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.dlazdice.07.rodic' ma byt ctyri cela "
        f"cisla [x, y, sirka, vyska], je [446, 240]"
    ) in msgs
    assert _obsahuji(msgs, ZNACKA_R136_RODIC) == []


def test_prvek_bez_sveho_widgetu_je_WARN():
    """Merena data, ktera nemaji kam sednout, se zahazuji - a rekne se to."""
    d = _make(
        [_w("a", 10, 10, 100, 20)],
        navrh={"prvky": {"neexistuje": {"rodic": [0, 0, 100, 100]}}},
    )
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.neexistuje' neodpovida zadnemu widgetu "
        f"sceny - merena data se zahazuji"
    ) in _warns(d)


def test_vadny_obdelnik_pasu_je_ERROR():
    d = _make([_w("a", 10, 10, 100, 20)], navrh={"pasy": {"razitko": [20, 612, 0, 88]}})
    assert _obsahuji(_errors(d), "'pasy.razitko' ma byt ctyri cela cisla")


def test_odkaz_na_neznamy_pas_je_ERROR():
    """Bez teto hlasky by vyjimka 'do sveho pasu smi' tise neplatila."""
    d = _make(
        [_w("a", 40, 630, 100, 20)],
        navrh={"pasy": PAS_RAZITKO, "prvky": {"a": {"pas": "patka"}}},
    )
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.a.pas' odkazuje na neznamy pas 'patka' "
        f"(znam: razitko)"
    ) in _errors(d)


# --------------------------------------------------------------------------- #
# Rule 136: oriznuti rodicem
# --------------------------------------------------------------------------- #


def test_r136_presah_hlasi_smery_i_obe_geometrie():
    d = _make(
        [_w("dlazdice.07", 446, 240, 386, 76)],
        navrh={"prvky": {"dlazdice.07": {"rodic": [446, 240, 374, 72]}}},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (dlazdice.07): {ZNACKA_R136_RODIC} "
        f"vpravo o 12 px a dole o 4 px (prvek 446,240 386x76, rodic 446,240 374x72)"
    ]


def test_r136_presah_vlevo_a_nahore():
    d = _make(
        [_w("a", 40, 90, 100, 20)],
        navrh={"prvky": {"a": {"rodic": [48, 97, 200, 100]}}},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (a): {ZNACKA_R136_RODIC} "
        f"vlevo o 8 px a nahore o 7 px (prvek 40,90 100x20, rodic 48,97 200x100)"
    ]


def test_r136_jediny_smer_je_bez_spojky():
    d = _make(
        [_w("a", 48, 97, 100, 20)],
        navrh={"prvky": {"a": {"rodic": [48, 97, 90, 100]}}},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (a): {ZNACKA_R136_RODIC} "
        f"vpravo o 10 px (prvek 48,97 100x20, rodic 48,97 90x100)"
    ]


def test_r136_licuje_s_rodicem_mlci():
    """Hranice: prvek vyplnuje rodice presne na pixel."""
    d = _make(
        [_w("a", 446, 540, 374, 72)],
        navrh={"prvky": {"a": {"rodic": [446, 540, 374, 72]}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R136_RODIC) == []


@pytest.mark.parametrize(("vyska", "ceka_nalez"), [(72, False), (73, True)])
def test_r136_prah_je_jeden_pixel(vyska, ceka_nalez):
    """Prah 1 px neni vkus: most zaokrouhluje OBE hrany zvlast."""
    d = _make(
        [_w("a", 446, 540, 374, vyska)],
        navrh={"prvky": {"a": {"rodic": [446, 540, 374, 72]}}},
    )
    nalezy = _obsahuji(_errors(d), ZNACKA_R136_RODIC)
    if not ceka_nalez:
        assert nalezy == []
    else:
        assert nalezy == [
            f"{FL}: main: scene 'main': widget[0] (a): {ZNACKA_R136_RODIC} "
            f"dole o 1 px (prvek 446,540 374x73, rodic 446,540 374x72)"
        ]


def test_r136_rodic_je_scena_mlci():
    """Hranice sceny uz meri Rule 63/79/80. Dva nalezy, jedna obet."""
    d = _make(
        [_w("a", -10, 100, 100, 20)],
        navrh={"prvky": {"a": {"rodic": [0, 0, 1280, 720]}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R136_RODIC) == []


def test_r136_neviditelny_prvek_se_preskoci():
    d = _make(
        [_w("a", 446, 240, 386, 76, visible=False)],
        navrh={"prvky": {"a": {"rodic": [446, 240, 374, 72]}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R136_RODIC) == []


def test_r136_panel_za_svym_obsahem_projde_obema_pravidly():
    """Souziti s Rule 21: tyz tvar je pro obe pravidla v poradku.

    Rule 21 se pta 'obsahuje kontejner to druhe?' a hlasi zamerne vrstveni;
    Rule 136 se pta obracene 'je dite uvnitr sveho rodice?' a mlci. Kdyby se
    poperou, dostane spravne slozeny panel ERROR.
    """
    d = _make(
        [
            _w("ram", 48, 88, 1192, 592, t="panel", text=""),
            _w("popisek", 100, 120, 400, 24),
        ],
        navrh={"prvky": {"popisek": {"rodic": [48, 88, 1192, 592]}}},
    )
    msgs = _msgs(d)
    assert _obsahuji(msgs, "OVERLAP (intentional layering)")
    assert _obsahuji(msgs, ZNACKA_R136_RODIC) == []
    assert _errors(d) == []


# --------------------------------------------------------------------------- #
# Rule 136: zasah do vyhrazeneho pasu
# --------------------------------------------------------------------------- #


def test_r136_zasah_do_pasu_hlasi_pretlou_hranu():
    """Zivy pripad: dlazdice RF Sonda, ktere patka usekla spodni hranu."""
    d = _make(
        [_w("dlazdice.11", 700, 540, 250, 76)],
        navrh={"pasy": PAS_RAZITKO, "prvky": {"dlazdice.11": {"rodic": [20, 97, 1240, 603]}}},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (dlazdice.11): {ZNACKA_R136_PAS} 'razitko' "
        f"o 4 px (prvek konci na y=616, pas zacina na y=612)"
    ]


def test_r136_dlazdice_sedi_v_rodici_ale_leze_do_pasu_je_JEDEN_nalez():
    """Rodic a pas jsou dve nezavisla mereni; jedna vada nesmi dat dve hlasky."""
    d = _make(
        [_w("dlazdice.11", 700, 540, 250, 76)],
        navrh={"pasy": PAS_RAZITKO, "prvky": {"dlazdice.11": {"rodic": [20, 97, 1240, 603]}}},
    )
    assert len(_obsahuji(_errors(d), ZNACKA_R136_RODIC)) == 0
    assert len(_obsahuji(_errors(d), ZNACKA_R136_PAS)) == 1


@pytest.mark.parametrize(("vyska", "ceka_nalez"), [(72, False), (73, True)])
def test_r136_dotek_hrany_pasu_neni_zasah(vyska, ceka_nalez):
    """Hranice: dolni hrana presne na y=612 mlci, o pixel niz je nalez."""
    d = _make(
        [_w("a", 700, 540, 250, vyska)],
        navrh={"pasy": PAS_RAZITKO, "prvky": {"a": {"rodic": [20, 97, 1240, 603]}}},
    )
    nalezy = _obsahuji(_errors(d), ZNACKA_R136_PAS)
    if not ceka_nalez:
        assert nalezy == []
    else:
        assert nalezy == [
            f"{FL}: main: scene 'main': widget[0] (a): {ZNACKA_R136_PAS} 'razitko' o 1 px "
            f"(prvek konci na y=613, pas zacina na y=612)"
        ]


def test_r136_clen_pasu_do_nej_smi():
    """Musi mlcet UPLNE, ne jen o uroven mene.

    Kdyby se tu tvrdilo pouze 'zadny ERROR', prosel by test i po zruseni
    vyjimky: prvek cely uvnitr pasu dostane WARN, a ten by se schoval.

    NEGATIVNI TRIDA tretiho meridla: rodic je ``.obsah``, tedy tvar, ktery
    most SKUTECNE vydava - ne obdelnik pasu, jak fixtura tvrdila do
    2026-09-09.
    """
    d = _make(
        [_w("razitko.firmware", 40, 630, 388, 24)],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {"razitko.firmware": {"rodic": OBSAH, "pas": "razitko"}},
        },
    )
    assert _errors(d) == []
    assert _obsahuji(_msgs(d), ZNACKA_R136_PAS) == []
    assert _obsahuji(_msgs(d), ZNACKA_R136_PAS_VEN) == []


def test_r136_clen_pasu_ktery_z_pasu_utece_je_ERROR():
    """POZITIVNI TRIDA tretiho meridla - kritikuv obchvat, doslova.

    Hodnota razitka nakreslena 52 px NAD pasem, ``rodic`` = ``.obsah``.
    Presne tenhle tvar most vydava (kritik zmeril: **0 z 368 clenu pasu**
    ma rodice rovneho obdelniku pasu) a do 2026-09-09 prosel MLCKY, protoze
    rodicovska pulka pravidla mela obdelnik ``.obsah`` a ten prvek cely
    obsahuje.
    """
    d = _make(
        [_w("razitko.uteklo", 245, 560, 302, 19, text="normalni rezim")],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {"razitko.uteklo": {"rodic": OBSAH, "pas": "razitko"}},
        },
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (razitko.uteklo): {ZNACKA_R136_PAS_VEN} "
        f"'razitko' nahore o 52 px (prvek 245,560 302x19, pas 20,612 1240x88)"
    ]


def test_r136_clen_pasu_vycnivajici_dole_hlasi_smer_i_hloubku():
    """Druhy smer teze tridy - patka, ktera prerostla spodni hranu pasu.

    Bez tohohle testu by staz stacilo meridlo, ktere umi jen horni hranu.
    """
    d = _make(
        [_w("razitko.firmware", 40, 630, 388, 90)],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {"razitko.firmware": {"rodic": OBSAH, "pas": "razitko"}},
        },
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (razitko.firmware): {ZNACKA_R136_PAS_VEN} "
        f"'razitko' dole o 20 px (prvek 40,630 388x90, pas 20,612 1240x88)"
    ]


def test_r136_clen_pasu_licujici_s_hranou_mlci():
    """HRANICNI trida: dotek neni presah, prah je 1 px (zaokrouhleni mostu).

    Prvek zacina PRESNE na horni hrane pasu a konci PRESNE na spodni.
    """
    d = _make(
        [_w("razitko.firmware", 20, 612, 1240, 88)],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {"razitko.firmware": {"rodic": OBSAH, "pas": "razitko"}},
        },
    )
    assert _obsahuji(_msgs(d), ZNACKA_R136_PAS_VEN) == []
    # a o jeden pixel vys uz je to nalez
    d2 = _make(
        [_w("razitko.firmware", 20, 611, 1240, 88)],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {"razitko.firmware": {"rodic": OBSAH, "pas": "razitko"}},
        },
    )
    assert len(_obsahuji(_errors(d2), ZNACKA_R136_PAS_VEN)) == 1


def test_r136_cizi_prvek_cely_v_pasu_je_jen_WARN():
    """Oriznout ho pas nemuze - chybi mu prihlaska, to neni tataz vada.

    ERROR by tu meril jinou velicinu, nez pravidlo slibuje: oriznuti je
    preteti HRANY pasu, ne poloha uvnitr nej.
    """
    d = _make(
        [_w("smalt.volno", 40, 630, 380, 24)],
        navrh={"pasy": PAS_RAZITKO, "prvky": {"smalt.volno": {"rodic": [20, 97, 1240, 603]}}},
    )
    assert _errors(d) == []
    assert _obsahuji(_warns(d), ZNACKA_R136_PAS) == [
        f"{FL}: main: scene 'main': widget[0] (smalt.volno): {ZNACKA_R136_PAS} 'razitko': "
        f"lezi cely uvnitr pasu, ale nehlasi se do nej (prvek 40,630 380x24, "
        f"pas 20,612 1240x88); kdyz do pasu patri, ma to rict navrh.prvky[<id>].pas"
    ]


def test_r136_zasah_do_svisleho_pasu_zprava():
    """Pas nemusi byt vodorovny - hlasi se hrana, kterou prvek skutecne pretl."""
    d = _make([_w("a", 90, 100, 110, 40)], navrh={"pasy": {"sloupec": [0, 0, 100, 720]}})
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (a): {ZNACKA_R136_PAS} 'sloupec' o 10 px "
        f"(prvek zacina na x=90, pas konci na x=100)"
    ]


def test_r136_pas_se_meri_i_prvku_bez_vlastniho_zaznamu():
    """Pas je vlastnost SCENY: nezmereny prvek nesmi patku projit mlcky."""
    d = _make([_w("a", 700, 540, 250, 76)], navrh={"pasy": PAS_RAZITKO})
    assert len(_obsahuji(_errors(d), ZNACKA_R136_PAS)) == 1


def test_r136_podklad_ktery_pas_obsahuje_mlci():
    """Obal obsahu, uvnitr ktereho patka sedi, neni narusitel, ale podklad.

    Tataz vyjimka, jakou ma Rule 21 pro panel za svym obsahem - bez ni by
    kazdy list zacinal ERRORem na vlastnim ramu.
    """
    d = _make(
        [_w("obsah", 20, 97, 1240, 603, t="panel", text="")],
        navrh={"pasy": PAS_RAZITKO},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R136_PAS) == []


def test_r136_prvek_mimo_pas_mlci():
    d = _make(
        [_w("a", 700, 300, 250, 76)],
        navrh={"pasy": PAS_RAZITKO, "prvky": {"a": {"rodic": [20, 97, 1240, 603]}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R136_PAS) == []


# --------------------------------------------------------------------------- #
# Rule 137: preteceni textu zmerenym fontem
# --------------------------------------------------------------------------- #


def _stitek(sirka_textu=None, sirka_bunky=None, text="V0.4-71-gee91351-dirty", **kw):
    prvek = {}
    if sirka_textu is not None:
        prvek["sirka_textu"] = sirka_textu
    if sirka_bunky is not None:
        prvek["sirka_bunky"] = sirka_bunky
    return _make(
        [_w("razitko.firmware", 40, 630, 388, 24, text=text, **kw)],
        navrh={"prvky": {"razitko.firmware": prvek}},
    )


def test_r137_pretok_hlasi_zmerena_cisla():
    d = _stitek(402.7, 388.0)
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (razitko.firmware): {ZNACKA_R137}: "
        f"zmereno 402.7 px, bunka ma 388.0 px (pretok 14.7 px), "
        f"text 'V0.4-71-gee91351-dirty'"
    ]


def test_r137_kratsi_text_mlci():
    assert _obsahuji(_msgs(_stitek(300.0, 388.0)), ZNACKA_R137) == []


@pytest.mark.parametrize(
    ("sirka_textu", "ceka_nalez"),
    [(388.4, False), (388.5, False), (388.6, True)],
)
def test_r137_tolerance_je_pul_pixelu(sirka_textu, ceka_nalez):
    """Chrome pocita v 1/64 px; rovnost se nikdy netrefi presne."""
    nalezy = _obsahuji(_errors(_stitek(sirka_textu, 388.0)), ZNACKA_R137)
    assert bool(nalezy) is ceka_nalez


def test_r137_ellipsis_neomlouva():
    """Trojtecka neni sdeleni, je to ztraceny konec (stitek FIRMWARE)."""
    d = _stitek(402.7, 388.0, text_overflow="ellipsis")
    assert _obsahuji(_errors(d), ZNACKA_R137)


def test_r137_hlasi_i_kdyz_scena_text_nenese():
    """Most sirku zmeril, ale text neposlal (sazba uvnitr <b>/<u>/<s>).

    Prazdne uvozovky v hlasce jsou ta informace: 'zelena' na takovem listu
    nic neznamena, protoze scena texty dlazdic vubec nenese.
    """
    d = _stitek(402.7, 388.0, text="")
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (razitko.firmware): {ZNACKA_R137}: "
        f"zmereno 402.7 px, bunka ma 388.0 px (pretok 14.7 px), text ''"
    ]


def test_r137_neviditelny_prvek_se_preskoci():
    d = _stitek(402.7, 388.0, visible=False)
    assert _obsahuji(_msgs(d), ZNACKA_R137) == []


def test_r137_chybejici_sirka_bunky_je_WARN_o_nemereni():
    """Nemereno != cisto: polovicni mereni se prizna."""
    d = _stitek(402.7, None)
    assert _obsahuji(_warns(d), ZNACKA_R137_NEMERENO) == [
        f"{FL}: main: scene 'main': widget[0] (razitko.firmware): {ZNACKA_R137_NEMERENO}: "
        f"chybi 'sirka_bunky' (zmerena je jen sirka textu 402.7 px)"
    ]


def test_r137_chybejici_sirka_textu_je_WARN_o_nemereni():
    d = _stitek(None, 388.0)
    assert _obsahuji(_warns(d), ZNACKA_R137_NEMERENO) == [
        f"{FL}: main: scene 'main': widget[0] (razitko.firmware): {ZNACKA_R137_NEMERENO}: "
        f"chybi 'sirka_textu' (znama je jen sirka bunky 388.0 px)"
    ]


def test_r137_bez_mereni_ani_WARN_ani_ERROR():
    d = _stitek(None, None)
    msgs = _msgs(d)
    assert _obsahuji(msgs, ZNACKA_R137) == []
    assert _obsahuji(msgs, ZNACKA_R137_NEMERENO) == []


def test_r137_vadna_sirka_je_ERROR_a_pravidlo_nemeri():
    d = _make(
        [_w("razitko.firmware", 40, 630, 388, 24)],
        navrh={"prvky": {"razitko.firmware": {"sirka_textu": "402.7", "sirka_bunky": 388.0}}},
    )
    msgs = _msgs(d)
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.razitko.firmware.sirka_textu' ma byt "
        f"nezaporne cislo v px, je '402.7'"
    ) in msgs
    assert _obsahuji(msgs, ZNACKA_R137) == []
    # Zbytek mereni se cte dal: jedna vadna hodnota nezahazuje cely prvek.
    assert _obsahuji(msgs, ZNACKA_R137_NEMERENO)


# --------------------------------------------------------------------------- #
# Rule 137 vs Rule 7: jeden pixel, jedno meridlo
# --------------------------------------------------------------------------- #

# Na profilu tab5 je CHAR_W dolni mez 2 px, takze do sirky 40 px se "vejde"
# 20 znaku. Text ma 24 - Rule 7 tedy na tomhle tvaru MLUVI.
_DLOUHY = "A" * 24


def test_rule7_bez_mereni_mluvi():
    """POZITIVNI KONTROLA VYPNUTI: bez ni by test nize neoveril nic."""
    d = _make([_w("a", 100, 100, 40, 24, text=_DLOUHY)])
    assert _obsahuji(_warns(d), "overflows max 20 chars")


def test_r137_zmerena_sirka_umlci_vodorovnou_pulku_rule7():
    d = _make(
        [_w("a", 100, 100, 40, 24, text=_DLOUHY)],
        navrh={"prvky": {"a": {"sirka_textu": 30.0, "sirka_bunky": 40.0}}},
    )
    assert _obsahuji(_msgs(d), "overflows max") == []


def test_r137_svisla_pulka_rule7_zustava():
    """Rule 137 meri sirku, ne vysku - svisla kontrola se vypnout nesmi."""
    d = _make(
        [_w("a", 100, 100, 40, 4, text="AB")],
        navrh={"prvky": {"a": {"sirka_textu": 30.0, "sirka_bunky": 40.0}}},
    )
    assert _obsahuji(_warns(d), "text cannot fit: h=4")


# --------------------------------------------------------------------------- #
# Fixtury: nosic je legalni a obe tridy se lisi
# --------------------------------------------------------------------------- #


def test_cista_fixtura_projde_JSON_schematem():
    """Bez tohohle testu by nikdo neoveril, ze scena blok 'navrh' vubec smi."""
    nalezy = validate_file(CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_cista_fixtura_nema_ani_jeden_ERROR():
    nalezy = validate_file(CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if i.level == "ERROR"] == []


def test_vadna_fixtura_projde_JSON_schematem():
    nalezy = validate_file(VADNA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_vadna_fixtura_najde_vsechny_ctyri_zasazene_tridy():
    """Rozlisovaci schopnost: obe fixtury se nesmi merit stejne."""
    chyby = [i.message for i in validate_file(VADNA, warnings_as_errors=False) if i.level == "ERROR"]
    assert len(_obsahuji(chyby, ZNACKA_R136_PAS)) == 1
    assert len(_obsahuji(chyby, ZNACKA_R136_PAS_VEN)) == 1
    assert len(_obsahuji(chyby, ZNACKA_R136_RODIC)) == 1
    assert len(_obsahuji(chyby, ZNACKA_R137)) == 1
    assert len(chyby) == 4


def test_fixtura_nese_tvar_rodice_ktery_MOST_SKUTECNE_VYDAVA():
    """Fixtura nesmi pribijet neexistujici svet.

    Most vydava ``rodic = ramecek(el.offsetParent)`` a ``offsetParent`` clena
    razitka je ``.obsah``, ne obal pasu; kritik zmeril na 62 listech
    **0 z 368** clenu pasu s rodicem rovnym obdelniku sveho pasu. Kdyby se
    fixtura vratila k obdelniku pasu, treti meridlo by uz zadny obchvat
    nechytalo a tenhle test by o tom mlcel - proto tvrdi oboji: rodic NENI
    obdelnik pasu a ZAROVEN aspon dva clenove pasu ve fixture jsou.
    """
    scena = json.loads(VADNA.read_text(encoding="utf-8"))["scenes"]["main"]
    pasy = scena["navrh"]["pasy"]
    clenu = 0
    for wid, prvek in scena["navrh"]["prvky"].items():
        pas = prvek.get("pas")
        if pas is None:
            continue
        clenu += 1
        assert prvek.get("rodic") != pasy[pas], (
            f"{wid}: rodic == obdelnik pasu je tvar, ktery most nikdy nevyda"
        )
    assert clenu >= 2


def test_obe_fixtury_maji_blok_navrh_a_lisi_se_jen_merenim():
    """Kdyby cista fixtura blok nemela, mlcela by z jineho duvodu nez mysli."""
    for cesta in (CISTA, VADNA):
        scena = json.loads(cesta.read_text(encoding="utf-8"))["scenes"]["main"]
        assert "navrh" in scena
        assert scena["navrh"]["prvky"]


# --------------------------------------------------------------------------- #
# Role prvku: nosic Rule 138 i Rule 139
# --------------------------------------------------------------------------- #


def _smalt(role=None, text="", *, wid="smalt.port", navic=None, deti=(), deti_navrh=None, **kw):
    """Jeden smalt (48,200 300x88) a k nemu merena data; ``deti`` sazi dovnitr.

    ``deti_navrh`` je merena data DETI - typicky ``rodic_id``, kterym most
    rika, kdo je ciho potomka. Bez nej dite smalt NEUMLCI: geometricky
    prekryv sam o sobe prislusnost nedokazuje (viz `_text_uvnitr`).
    """
    prvek = {}
    if role is not None:
        prvek["role"] = role
    if navic:
        prvek.update(navic)
    prvky = {wid: prvek}
    if deti_navrh:
        prvky.update(deti_navrh)
    return _make([_w(wid, 48, 200, 300, 88, text=text, **kw), *deti], navrh={"prvky": prvky})


def test_vadna_role_je_ERROR_a_pravidlo_nemeri():
    d = _smalt(role=5)
    msgs = _msgs(d)
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.smalt.port.role' ma byt jmeno role, je 5"
    ) in msgs
    assert _obsahuji(msgs, ZNACKA_R138) == []


def test_neznama_role_je_WARN_a_pravidlo_nemeri():
    """Preklep v roli je vypinac pravidla - musi byt slyset.

    Pozitivni kontrola je ve stejnem testu: se spravne napsanou roli tyz tvar
    ERROR dostane. Bez ni by test prosel, i kdyby Rule 138 nikdy nestrilela.
    """
    d = _smalt(role="hodnta")
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.smalt.port.role' je nezname jmeno role "
        f"'hodnta' (znam: cislo, hodnota, patka, popisek, smalt, stitek, titulek) - merena "
        f"data se zahazuji"
    ) in _warns(d)
    assert _obsahuji(_msgs(d), ZNACKA_R138) == []
    assert _obsahuji(_errors(_smalt(role="hodnota")), ZNACKA_R138)


def test_role_se_cte_bez_ohledu_na_velikost_pismen():
    d = _smalt(role="Hodnota")
    assert _obsahuji(_errors(d), ZNACKA_R138)
    assert _obsahuji(_msgs(d), ZNACKA_NAVRH_VADNY) == []


def test_prazdne_neni_retezec_je_ERROR_a_pravidlo_dobehne():
    d = _smalt(role="hodnota", navic={"prazdne": True})
    msgs = _msgs(d)
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.smalt.port.prazdne' ma byt veta o tom, "
        f"proc je prvek prazdny, je True"
    ) in msgs
    assert _obsahuji(_errors(d), ZNACKA_R138)


def test_prazdne_bez_vety_je_WARN_a_pravidlo_dobehne():
    """Hranice: oznaceni bez vety je jen vypinac, ne zamer."""
    d = _smalt(role="hodnota", navic={"prazdne": "  "})
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.smalt.port.prazdne' je prazdne oznaceni "
        f"- zamer bez vety neni zamer, oznaceni se zahazuje"
    ) in _warns(d)
    assert _obsahuji(_errors(d), ZNACKA_R138)


# --------------------------------------------------------------------------- #
# Rule 138: prazdny smalt
# --------------------------------------------------------------------------- #


def test_r138_prazdna_hodnota_je_ERROR():
    """Zivy protejsek: Terminal smalt PORT, Files VOLNO, USB 'CO TO JE'."""
    d = _smalt(role="hodnota")
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (smalt.port): {ZNACKA_R138}: role 'hodnota' "
        f"nenese zadny text ani uvnitr sebe; nedostupnost se rekne vetou, nebo se prvek "
        f"oznaci jako zamerne prazdny (navrh.prvky['smalt.port'].prazdne)"
    ]


def test_r138_hodnota_s_textem_mlci():
    assert _obsahuji(_msgs(_smalt(role="hodnota", text="115 200 Bd")), ZNACKA_R138) == []


@pytest.mark.parametrize("text", ["", "   "])
def test_r138_text_ze_samych_mezer_je_prazdno(text):
    """Hranice: mezery nejsou sdeleni, jen jinak zapsane prazdno."""
    assert len(_obsahuji(_errors(_smalt(role="hodnota", text=text)), ZNACKA_R138)) == 1


@pytest.mark.parametrize("role", ["cislo", "hodnota", "smalt", "stitek"])
def test_r138_plati_pro_kazdou_hodnotovou_roli(role):
    """Slovnik roli je soucast pravidla, ne detail - meri se cely."""
    assert len(_obsahuji(_errors(_smalt(role=role)), ZNACKA_R138)) == 1


@pytest.mark.parametrize("role", ["patka", "popisek", "titulek"])
def test_r138_popiskova_role_mlci(role):
    """Popisek nic neslibuje: prazdne navesti hodnotu nedluzi."""
    assert _obsahuji(_msgs(_smalt(role=role)), ZNACKA_R138) == []


def test_r138_text_uvnitr_smaltu_umlci():
    """Svorkovnice sazi text do deti - obal sam PRIMY text nema.

    Prislusnost vozi most (``rodic_id``); geometrie je az druha podminka.
    """
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("smalt.port.cislo", 60, 230, 200, 32, text="115 200 Bd")],
        deti_navrh={"smalt.port.cislo": {"rodic_id": "smalt.port"}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R138) == []


def test_r138_CIZI_text_pod_smaltem_ho_NEUMLCI():
    """Kritikuv obchvat, doslova: prazdny smalt pres cizi popisek = TICHO.

    Do 2026-09-09 se vyjimka "uvnitr sebe" ptala jen GEOMETRICKY, takze
    prazdnemu smaltu stacilo prekryvat jakykoli jiny popisek a pravidlo
    zmlklo. Tenhle test je nutny protipriklad k testu vys: obe sceny maji
    TUTEZ geometrii a lisi se JEN prislusnosti.
    """
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("jiny.popisek", 60, 230, 200, 32, text="VOLNO")],
        deti_navrh={"jiny.popisek": {"rodic_id": "obsah"}},
    )
    assert len(_obsahuji(_errors(d), ZNACKA_R138)) == 1


def test_r138_bez_rodokmenu_umlcuje_jen_vlastni_offsetParent():
    """Starsi scena bez ``rodic_id``: prislusnost rekne obdelnik rodice.

    Hrubsi meridlo, ale porad se pta na PRISLUSNOST, ne na prekryv - cizi
    popisek s jinym rodicem smalt neumlci ani tady.
    """
    muj = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cislo", 60, 230, 200, 32, text="115 200 Bd")],
        deti_navrh={"cislo": {"rodic": [48, 200, 300, 88]}},
    )
    assert _obsahuji(_msgs(muj), ZNACKA_R138) == []
    cizi = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cislo", 60, 230, 200, 32, text="115 200 Bd")],
        deti_navrh={"cislo": {"rodic": [20, 97, 1240, 603]}},
    )
    assert len(_obsahuji(_errors(cizi), ZNACKA_R138)) == 1


def test_r138_rodic_id_na_neznamy_prvek_je_ERROR_a_neumlcuje():
    """Preklep v rodokmenu nesmi tise vypnout ani vyjimku, ani pravidlo."""
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cislo", 60, 230, 200, 32, text="115 200 Bd")],
        deti_navrh={"cislo": {"rodic_id": "smalt.pjrt"}},
    )
    msgs = _msgs(d)
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.cislo.rodic_id' odkazuje na prvek "
        f"'smalt.pjrt', ktery ve scene neni"
    ) in msgs
    assert len(_obsahuji(_errors(d), ZNACKA_R138)) == 1


def test_r138_rodic_id_sam_na_sebe_je_ERROR():
    """Cyklus v rodokmenu by jinak validator zacyklil misto hlaseni."""
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cislo", 60, 230, 200, 32, text="115 200 Bd")],
        deti_navrh={"cislo": {"rodic_id": "cislo"}},
    )
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.cislo.rodic_id' ukazuje sam na sebe"
    ) in _msgs(d)


def test_r138_vnuk_umlcuje_taky():
    """Retez ``rodic_id`` se prochazi nahoru, ne jen o jednu uroven."""
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[
            _w("radek", 55, 220, 250, 50, text=""),
            _w("cislo", 60, 230, 200, 32, text="115 200 Bd"),
        ],
        deti_navrh={
            "radek": {"rodic_id": "smalt.port"},
            "cislo": {"rodic_id": "radek"},
        },
    )
    assert _obsahuji(_msgs(d), ZNACKA_R138) == []


def test_r138_text_jen_castecne_uvnitr_neumlci():
    """Sdeleni musi lezet CELE uvnitr, jinak patri nekomu jinemu."""
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cizi", 300, 230, 200, 32, text="115 200 Bd")],
    )
    assert len(_obsahuji(_errors(d), ZNACKA_R138)) == 1


@pytest.mark.parametrize(("sirka", "ceka_ticho"), [(300, True), (301, False)])
def test_r138_hranice_obsazeni_je_na_pixel(sirka, ceka_ticho):
    """Dite presne licujici se smaltem jeste umlcuje, o pixel sirsi uz ne."""
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cislo", 48, 200, sirka, 88, text="115 200 Bd")],
        deti_navrh={"cislo": {"rodic_id": "smalt.port"}},
    )
    assert (_obsahuji(_errors(d), ZNACKA_R138) == []) is ceka_ticho


def test_r138_neviditelny_text_uvnitr_neumlci():
    """Skryte sdeleni na panelu videt neni, takze smalt zustava prazdny."""
    d = _smalt(
        role="smalt",
        t="panel",
        deti=[_w("cislo", 60, 230, 200, 32, text="115 200 Bd", visible=False)],
    )
    assert len(_obsahuji(_errors(d), ZNACKA_R138)) == 1


def test_r138_zamerne_prazdny_s_vetou_mlci():
    d = _smalt(role="hodnota", navic={"prazdne": "port drzi jiny modul"})
    assert _obsahuji(_msgs(d), ZNACKA_R138) == []


def test_r138_stare_oznaceni_na_prvku_s_textem_je_WARN():
    """Oznaceni je trvaly vypinac pravidla; kdyz uz neplati, ma se pripomenout."""
    d = _smalt(role="hodnota", text="115 200 Bd", navic={"prazdne": "port drzi jiny modul"})
    assert _obsahuji(_warns(d), ZNACKA_R138_OZNACENI) == [
        f"{FL}: main: scene 'main': widget[0] (smalt.port): {ZNACKA_R138_OZNACENI}: prvek je "
        f"oznaceny jako zamerne prazdny ('port drzi jiny modul'), ale text nese: '115 200 Bd'"
    ]
    assert _errors(d) == []


def test_r138_bez_role_mlci():
    """Datove gatovani: bez merene role pravidlo neexistuje."""
    assert _obsahuji(_msgs(_smalt()), ZNACKA_R138) == []


def test_r138_neviditelny_prvek_se_preskoci():
    assert _obsahuji(_msgs(_smalt(role="hodnota", visible=False)), ZNACKA_R138) == []


def test_r138_neretezcovy_text_patri_rule91():
    """Dva nalezy, jedna obet: vadny TYP textu meri Rule 91, ne Rule 138."""
    d = _make(
        [_w("smalt.port", 48, 200, 300, 88, text=42)],
        navrh={"prvky": {"smalt.port": {"role": "hodnota"}}},
    )
    chyby = _errors(d)
    assert _obsahuji(chyby, "must be a string")
    assert _obsahuji(chyby, ZNACKA_R138) == []


def test_r138_a_rule25_se_neprekryvaji():
    """Rule 25 mlci u prvku s _widget_id - a podle nej se merena data paruji.

    Pozitivni kontrola, ze Rule 25 vubec zije: tyz prazdny label bez id ji
    dostane. Bez ni by prvni tvrzeni proslo i s mrtvou Rule 25.
    """
    assert _obsahuji(_msgs(_smalt(role="hodnota")), "with no text and no runtime binding") == []
    bez_id = _make(
        [
            {
                "type": "label",
                "x": 48,
                "y": 200,
                "width": 300,
                "height": 88,
                "text": "",
                "color_fg": "#e6e1ce",
                "color_bg": "#14170f",
            }
        ]
    )
    assert _obsahuji(_warns(bez_id), "with no text and no runtime binding")


# --------------------------------------------------------------------------- #
# Rule 139: pomlcka jako hodnota
# --------------------------------------------------------------------------- #


def test_r139_pomlcka_je_ERROR():
    """Zivy protejsek: Logic Analyzer SPOUST a patka bez slova."""
    d = _smalt(role="hodnota", text=POMLCKA)
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (smalt.port): {ZNACKA_R139}: text '{POMLCKA}' "
        f"neni veta; rekni, co se stalo (napr. 'spoust nenastavena')"
    ]


def test_r139_mnozina_tvaru_je_uzka_a_pojmenovana():
    """Parametrizace nize cte mnozinu z modulu; tenhle test hlida, co v ni je.

    U+2010 HYPHEN a U+2011 NON-BREAKING HYPHEN doplneny 2026-09-09: mnozina
    zacinala az u U+2012, takze "obycejna" typograficka pomlcka - na skle
    k nerozeznani od U+2013 - prosla mlckym.
    """
    assert sorted(hex(ord(z)) for z in POMLCKY) == [
        "0x2010",
        "0x2011",
        "0x2012",
        "0x2013",
        "0x2014",
        "0x2015",
        "0x2212",
        "0x2d",
    ]


@pytest.mark.parametrize("znak", sorted(POMLCKY))
def test_r139_vsechny_tvary_pomlcky_strili(znak):
    assert len(_obsahuji(_errors(_smalt(role="hodnota", text=znak)), ZNACKA_R139)) == 1


def test_r139_pomlcka_s_mezerami_je_ERROR():
    """Hranice: obalena mezerami je porad cely text."""
    assert len(_obsahuji(_errors(_smalt(role="hodnota", text=f" {POMLCKA} ")), ZNACKA_R139)) == 1


def test_r139_dve_spojovniky_jsou_ZASTUPNY_ZNAK_ne_pomlcka():
    """Mnozina POMLCKY zustava jednoznakova; "--" ma vlastni nalez.

    Presne to, co si predchozi verze pravidla vyhradila nahlas ("kdo chce
    chytat i dva spojovniky, ma to napsat jako vlastni nalez, ne tise
    rozsirit mnozinu tvaru") - jinak by sirsi mnozina zacala obvinovat
    vodorovne cary sazene textem.
    """
    chyby = _errors(_smalt(role="hodnota", text="--"))
    assert _obsahuji(chyby, ZNACKA_R139) == []
    assert len(_obsahuji(chyby, ZNACKA_R139_ZASTUPNY)) == 1


@pytest.mark.parametrize("znak", ["•", "…", "...", "?", "n/a", "N/A", "---"])
def test_r139_zastupny_znak_misto_hodnoty_je_ERROR(znak):
    """POZITIVNI trida: "nic nevim" napsane jinym znakem nez pomlckou.

    Vsechny tyhle tvary do 2026-09-09 prosly MLCKY (kritik je zmeril na
    hodnotove roli), pritom na skle znamenaji totez co pomlcka.
    """
    assert len(_obsahuji(_errors(_smalt(role="hodnota", text=znak)), ZNACKA_R139_ZASTUPNY)) == 1


def test_r139_nulova_mezera_neni_prazdno_ani_pomlcka_a_presto_je_ERROR():
    """Jediny znamy tvar, ktery obchazel Rule 138 i Rule 139 NARAZ.

    `strip()` U+200B neodstrani, takze prvek nebyl "prazdny" (Rule 138
    mlcela), a v POMLCKY nebyl taky (Rule 139 mlcela). Na skle vypada
    uplne prazdne.
    """
    chyby = _errors(_smalt(role="hodnota", text=" ​ "))
    assert len(_obsahuji(chyby, ZNACKA_R139_ZASTUPNY)) == 1
    assert _obsahuji(chyby, ZNACKA_R138) == []


def test_r139_prazdny_text_zastupnou_vetev_NEspousti():
    """Jedna obet, jeden nalez: prazdno patri vyhradne Rule 138.

    Bez zavory by ho vetev "po odstraneni nulovych sirek nezbyde nic"
    obvinila podruhe.
    """
    chyby = _errors(_smalt(role="hodnota", text=""))
    assert len(_obsahuji(chyby, ZNACKA_R138)) == 1
    assert _obsahuji(chyby, ZNACKA_R139_ZASTUPNY) == []
    assert len(chyby) == 1


def test_r139_vic_slotu_s_pomlckou_v_jednom_prvku_je_ERROR_s_vyctem():
    """POZITIVNI trida: patka Hexu "SOUBOR - OKNO - ZOBRAZENO -".

    Pravidlo merilo jen CELY text, takze generator, ktery nesazi kazdou
    hodnotu jako vlastni prvek, tri prazdne sloty protahl MLCKY.
    """
    text = f"SOUBOR {POMLCKA} OKNO {POMLCKA} ZOBRAZENO {POMLCKA}"
    chyby = _errors(_smalt(role="hodnota", text=text))
    assert chyby == [
        f"{FL}: main: scene 'main': widget[0] (smalt.port): {ZNACKA_R139}: 3 slotu "
        f"v jednom prvku nema hodnotu (SOUBOR, OKNO, ZOBRAZENO) - text '{text}'"
    ]


@pytest.mark.parametrize(
    "text",
    [
        "1–13",
        "vlozena – nepripojena",
        "A–B",
        "28,4 GB volno",
    ],
)
def test_r139_kontrolni_skupina_vyctu_slotu_mlci(text):
    """NEGATIVNI trida vyctu slotu - hodnoty, ve kterych pomlcka ODDELUJE.

    "vlozena - nepripojena" ma PRESNE tentyz tvar jako jeden slot s pomlckou
    (slovo, mezera, pomlcka) - proto se hlasi az DVE po sobe jdouci skupiny
    a osamely slot poctive projde.
    """
    assert _obsahuji(_msgs(_smalt(role="hodnota", text=text)), ZNACKA_R139) == []


def test_r139_pomlcka_uvnitr_textu_mlci():
    d = _smalt(role="hodnota", text=f"1{POMLCKA_KRATKA}13")
    assert _obsahuji(_msgs(d), ZNACKA_R139) == []


@pytest.mark.parametrize("role", ["patka", "popisek", "titulek"])
def test_r139_popiskova_role_mlci(role):
    """V patce nebo v popisku pomlcka oddeluje, nezastupuje hodnotu."""
    assert _obsahuji(_msgs(_smalt(role=role, text=POMLCKA)), ZNACKA_R139) == []


def test_r139_bez_role_mlci():
    assert _obsahuji(_msgs(_smalt(text=POMLCKA)), ZNACKA_R139) == []


def test_r139_neviditelny_prvek_se_preskoci():
    d = _smalt(role="hodnota", text=POMLCKA, visible=False)
    assert _obsahuji(_msgs(d), ZNACKA_R139) == []


# --------------------------------------------------------------------------- #
# Rule 138 vs Rule 139: jedna obet, jeden nalez
# --------------------------------------------------------------------------- #


def test_prazdny_smalt_dostane_JEDEN_nalez_ne_dva():
    chyby = _errors(_smalt(role="hodnota"))
    assert len(_obsahuji(chyby, ZNACKA_R138)) == 1
    assert _obsahuji(chyby, ZNACKA_R139) == []
    assert len(chyby) == 1


def test_pomlcka_dostane_JEDEN_nalez_ne_dva():
    chyby = _errors(_smalt(role="hodnota", text=POMLCKA))
    assert len(_obsahuji(chyby, ZNACKA_R139)) == 1
    assert _obsahuji(chyby, ZNACKA_R138) == []
    assert len(chyby) == 1


# --------------------------------------------------------------------------- #
# Fixtury Rule 138 / Rule 139: obe tridy
# --------------------------------------------------------------------------- #


def test_smaltova_fixtura_ciste_projde_JSON_schematem():
    nalezy = validate_file(SMALT_CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_smaltova_fixtura_ciste_nema_ani_jeden_ERROR():
    nalezy = validate_file(SMALT_CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if i.level == "ERROR"] == []


def test_smaltova_fixtura_ciste_nese_kazdy_tvar_ticha():
    """Kdyby z fixtury tvary vypadly, mlcela by z jineho duvodu, nez tvrdi."""
    prvky = json.loads(SMALT_CISTA.read_text(encoding="utf-8"))["scenes"]["main"]["navrh"]["prvky"]
    assert {"hodnota", "smalt", "patka"} <= {p.get("role") for p in prvky.values()}
    assert [p for p in prvky.values() if p.get("prazdne")]


def test_smaltova_fixtura_vady_projde_JSON_schematem():
    nalezy = validate_file(SMALT_VADNA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_smaltova_fixtura_vady_najde_obe_tridy():
    """Rozlisovaci schopnost: obe fixtury se nesmi merit stejne."""
    chyby = [
        i.message
        for i in validate_file(SMALT_VADNA, warnings_as_errors=False)
        if i.level == "ERROR"
    ]
    assert len(_obsahuji(chyby, ZNACKA_R138)) == 2
    assert len(_obsahuji(chyby, ZNACKA_R139)) == 1
    assert len(chyby) == 3


def test_fixtury_bez_roli_na_smaltova_pravidla_mlci():
    """Datove gatovani na skutecnem souboru, ne jen na slovniku v pameti."""
    for cesta in (CISTA, VADNA):
        zpravy = [i.message for i in validate_file(cesta, warnings_as_errors=False)]
        assert _obsahuji(zpravy, ZNACKA_R138) == []
        assert _obsahuji(zpravy, ZNACKA_R139) == []


# --------------------------------------------------------------------------- #
# Rule 140: kapacita mrizky
# --------------------------------------------------------------------------- #


def _mrizka(*mrizky, device="tab5", scene_w=1280, scene_h=720):
    """Scena s deklarovanymi mrizkami.

    Widget je tu jen proto, aby scena nebyla prazdna: Rule 140 se pta SCENY,
    kolik polozek slibila pojmout, ne widgetu, kolik jich je videt. Prave
    v tom je jeji smysl - trinacta dlazdice ve scene NENI, protoze se na list
    nevesla, takze zadne meridlo nad souradnicemi widgetu ji chytit nemuze.
    """
    return _make(
        [_w("obsah", 20, 97, 1240, 603, text="", t="panel")],
        navrh={"mrizky": list(mrizky)},
        device=device,
        scene_w=scene_w,
        scene_h=scene_h,
    )


def test_r140_vic_polozek_nez_slotu_je_ERROR():
    d = _mrizka({"jmeno": "dlazdice", "kapacita": 12, "polozek": 13})
    assert (
        f"{FL}: main: {ZNACKA_R140}: 'dlazdice' ma kapacitu 12, polozek je 13 (o 1 vic)"
    ) in _errors(d)


def test_r140_hlaska_nese_i_vetsi_rozdil():
    """Cislo prebytku je v hlasce proto, aby se nemuselo dopocitavat."""
    d = _mrizka({"jmeno": "appky", "kapacita": 6, "polozek": 11})
    assert _obsahuji(_errors(d), "ma kapacitu 6, polozek je 11 (o 5 vic)")


def test_r140_pocet_sedi_presne_mlci():
    d = _mrizka({"jmeno": "d", "kapacita": 12, "polozek": 12})
    assert _obsahuji(_msgs(d), ZNACKA_R140) == []


def test_r140_volne_sloty_mlci():
    """Prazdny slot je v tomhle jazyce nosic, ne vada (gen_dalsi.py)."""
    d = _mrizka({"jmeno": "d", "kapacita": 12, "polozek": 11})
    assert _obsahuji(_msgs(d), ZNACKA_R140) == []


def test_r140_prazdna_mrizka_mlci():
    """Nula polozek je jiny nalez (kostra listu), ne kapacitni."""
    zpravy = _msgs(_mrizka({"jmeno": "d", "kapacita": 12, "polozek": 0}))
    assert _obsahuji(zpravy, ZNACKA_R140) == []
    assert _obsahuji(zpravy, ZNACKA_R140_NEMERENO) == []


@pytest.mark.parametrize(
    ("polozek", "ceka_nalez"),
    [(11, False), (12, False), (13, True), (14, True)],
)
def test_r140_hranice_je_o_jednu_polozku(polozek, ceka_nalez):
    d = _mrizka({"jmeno": "d", "kapacita": 12, "polozek": polozek})
    assert bool(_obsahuji(_errors(d), ZNACKA_R140)) is ceka_nalez


def test_r140_kapacita_bez_poctu_polozek_je_WARN_o_nemereni():
    """Vzor Rule 133: meridlo, ktere se nepustilo, se prizna nahlas."""
    d = _mrizka({"jmeno": "dlazdice", "kapacita": 12})
    assert (
        f"{FL}: main: {ZNACKA_R140_NEMERENO}: mrizka 'dlazdice' ma kapacitu 12, "
        f"ale pocet polozek nikdo nedodal - kontrola NEPROBEHLA"
    ) in _warns(d)
    assert _errors(d) == []


def test_r140_polozek_null_je_totez_co_chybejici():
    d = _mrizka({"jmeno": "dlazdice", "kapacita": 12, "polozek": None})
    assert len(_obsahuji(_warns(d), ZNACKA_R140_NEMERENO)) == 1


def test_r140_bez_klice_mrizky_mlci():
    d = _make([_w("a", 10, 10, 100, 20)], navrh={"prvky": {}})
    zpravy = _msgs(d)
    assert _obsahuji(zpravy, ZNACKA_R140) == []
    assert _obsahuji(zpravy, ZNACKA_R140_NEMERENO) == []


def test_r140_bez_bloku_navrh_mlci():
    zpravy = _msgs(_make([_w("a", 10, 10, 100, 20)]))
    assert _obsahuji(zpravy, ZNACKA_R140) == []
    assert _obsahuji(zpravy, ZNACKA_R140_NEMERENO) == []


def test_r140_prazdny_seznam_mrizek_mlci():
    zpravy = _msgs(_make([_w("a", 10, 10, 100, 20)], navrh={"mrizky": []}))
    assert _obsahuji(zpravy, ZNACKA_R140) == []
    assert _obsahuji(zpravy, ZNACKA_R140_NEMERENO) == []


def test_r140_meri_kazdou_mrizku_zvlast():
    d = _mrizka(
        {"jmeno": "dlazdice", "kapacita": 12, "polozek": 13},
        {"jmeno": "radky", "kapacita": 4, "polozek": 4},
        {"jmeno": "zalozky", "kapacita": 3, "polozek": 5},
    )
    nalezy = _obsahuji(_errors(d), ZNACKA_R140)
    assert len(nalezy) == 2
    assert _obsahuji(nalezy, "'dlazdice'") and _obsahuji(nalezy, "'zalozky'")


def test_r140_je_gatovane_daty_ne_profilem():
    """Oriznuta mrizka je vada na kazdem panelu; profil s tim nema co delat.

    Na OLEDu se blok `navrh` nevyskytuje, takze pravidlo tam v praxi mlci -
    ale kdyz uz nekdo kapacitu deklaruje, meri se stejne.
    """
    d = _mrizka(
        {"jmeno": "radky", "kapacita": 4, "polozek": 6},
        device="oled256",
        scene_w=256,
        scene_h=128,
    )
    assert _obsahuji(_errors(d), ZNACKA_R140)


def test_r140_mrizky_nejsou_seznam_je_ERROR():
    d = _make([_w("a", 10, 10, 100, 20)], navrh={"mrizky": {"dlazdice": 12}})
    assert f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'mrizky' ma byt seznam, je dict" in _errors(d)


def test_r140_polozka_seznamu_neni_objekt_je_ERROR():
    d = _make([_w("a", 10, 10, 100, 20)], navrh={"mrizky": ["dlazdice"]})
    assert f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'mrizky[0]' ma byt objekt, je str" in _errors(d)


@pytest.mark.parametrize("jmeno", [None, "", "   ", 7])
def test_r140_mrizka_bez_jmena_je_ERROR(jmeno):
    """Bez jmena se nalez neda opravit: nevi se, ktera mrizka to je."""
    d = _mrizka({"jmeno": jmeno, "kapacita": 4, "polozek": 9})
    chyby = _errors(d)
    assert _obsahuji(chyby, f"{ZNACKA_NAVRH_VADNY}: 'mrizky[0].jmeno'")
    assert _obsahuji(chyby, ZNACKA_R140) == []


@pytest.mark.parametrize("kapacita", [None, 0, -1, "12", 12.0, True])
def test_r140_vadna_kapacita_je_ERROR_a_pravidlo_nemeri(kapacita):
    """Preklep v kapacite nesmi pravidlo TISE vypnout (meridlo selhalo != nula)."""
    d = _mrizka({"jmeno": "dlazdice", "kapacita": kapacita, "polozek": 99})
    chyby = _errors(d)
    assert _obsahuji(
        chyby, f"{ZNACKA_NAVRH_VADNY}: 'mrizky[dlazdice].kapacita' ma byt cele cislo >= 1"
    )
    assert _obsahuji(chyby, ZNACKA_R140) == []


@pytest.mark.parametrize("polozek", [-1, "13", 13.0, True, []])
def test_r140_vadny_pocet_polozek_je_JEDEN_ERROR(polozek):
    """Jedna obet, jeden nalez: o tom, ze se nemerilo, uz mluvi ten ERROR."""
    d = _mrizka({"jmeno": "dlazdice", "kapacita": 12, "polozek": polozek})
    chyby = _errors(d)
    assert _obsahuji(
        chyby, f"{ZNACKA_NAVRH_VADNY}: 'mrizky[dlazdice].polozek' ma byt cele cislo >= 0"
    )
    assert _obsahuji(_warns(d), ZNACKA_R140_NEMERENO) == []
    assert _obsahuji(chyby, ZNACKA_R140) == []


def test_r140_vadna_mrizka_nezastavi_ostatni():
    """Zahazuje se JEDNA hodnota, ne cely blok - jinak by preklep umlcel list."""
    d = _mrizka(
        {"jmeno": "dlazdice", "kapacita": 0},
        {"jmeno": "radky", "kapacita": 4, "polozek": 6},
    )
    chyby = _errors(d)
    assert _obsahuji(chyby, "'mrizky[dlazdice].kapacita'")
    assert _obsahuji(chyby, f"{ZNACKA_R140}: 'radky'")


# --------------------------------------------------------------------------- #
# Fixtury Rule 140: obe tridy
# --------------------------------------------------------------------------- #


def test_mrizkova_fixtura_ciste_projde_JSON_schematem():
    nalezy = validate_file(MRIZKA_CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_mrizkova_fixtura_ciste_nema_ani_jeden_ERROR():
    nalezy = validate_file(MRIZKA_CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if i.level == "ERROR"] == []


def test_mrizkova_fixtura_ciste_nese_obe_ticha():
    """Kdyby z fixtury cisla vypadla, mlcela by z jineho duvodu, nez tvrdi."""
    scena = json.loads(MRIZKA_CISTA.read_text(encoding="utf-8"))["scenes"]["main"]
    mrizky = scena["navrh"]["mrizky"]
    assert [m for m in mrizky if m["polozek"] < m["kapacita"]]
    assert [m for m in mrizky if m["polozek"] == m["kapacita"]]


def test_mrizkova_fixtura_vady_projde_JSON_schematem():
    nalezy = validate_file(MRIZKA_VADNA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_mrizkova_fixtura_vady_najde_obe_tridy():
    """Rozlisovaci schopnost: obe fixtury se nesmi merit stejne."""
    nalezy = validate_file(MRIZKA_VADNA, warnings_as_errors=False)
    chyby = [i.message for i in nalezy if i.level == "ERROR"]
    varovani = [i.message for i in nalezy if i.level == "WARN"]
    assert len(_obsahuji(chyby, ZNACKA_R140)) == 1
    assert len(_obsahuji(varovani, ZNACKA_R140_NEMERENO)) == 1
    assert len(chyby) == 1


def test_fixtury_bez_mrizek_na_kapacitu_mlci():
    """Datove gatovani na skutecnych souborech, ne jen na slovniku v pameti."""
    for cesta in (CISTA, VADNA, SMALT_CISTA, SMALT_VADNA):
        zpravy = [i.message for i in validate_file(cesta, warnings_as_errors=False)]
        assert _obsahuji(zpravy, ZNACKA_R140) == []
        assert _obsahuji(zpravy, ZNACKA_R140_NEMERENO) == []


# --------------------------------------------------------------------------- #
# Rule 141: DPI firmwaru proti PPI panelu
# --------------------------------------------------------------------------- #
#
# `zkontroluj_dpi()` je ciste textova: dostane OBSAH souboru, ne cestu.
# Validator smi cist jen dokument, ktery dostal - `tests/test_tab5_validace.py`
# porovnava beh v pameti s behem CLI v podprocesu a cteni z disku uvnitr
# pravidla by obe cesty rozeslo. Soubory proto cte most (do_espos.dpi_firmwaru).

LV_CONF_DNES = "#define LV_DPI_DEF 130     /*[px/inch]*/"
SDK_DNES = "CONFIG_LV_DPI_DEF=130"


def _dpi(lv, sdk, prof=PROFILE_TAB5):
    return [f"[{i.level}] {i.message}" for i in zkontroluj_dpi(lv, sdk, prof)]


def test_r141_dnesni_stav_firmwaru_dava_dva_ERRORy():
    """Radky opsane z tabos-core (lv_conf.h:96, platforms/tab5/sdkconfig:2351)."""
    assert _dpi(LV_CONF_DNES, SDK_DNES) == [
        "[ERROR] DPI firmwaru nesouhlasi s panelem: lv_conf.h LV_DPI_DEF=130, "
        "profil 'tab5' ma 294 px/palec",
        "[ERROR] DPI firmwaru nesouhlasi s panelem: sdkconfig CONFIG_LV_DPI_DEF=130, "
        "profil 'tab5' ma 294 px/palec",
    ]


def test_r141_opraveny_firmware_mlci():
    """Pozitivni kontrola: kdyby pravidlo krizelo vzdy, prvni test netvrdi nic."""
    assert _dpi("#define LV_DPI_DEF 294     /*[px/inch]*/", "CONFIG_LV_DPI_DEF=294") == []


def test_r141_mez_je_z_profilu_ne_opsana():
    """Cislo v hlasce je zaokrouhlene ppi profilu, ne konstanta v pravidle."""
    (hlaska,) = _dpi(LV_CONF_DNES, "CONFIG_LV_DPI_DEF=294")
    assert f"ma {round(PROFILE_TAB5.ppi)} px/palec" in hlaska


@pytest.mark.parametrize(("dpi", "ceka_nalez"), [(293, True), (294, False), (295, True)])
def test_r141_tolerance_je_nulova(dpi, ceka_nalez):
    """`#define` neni mereni, nema sum: panel ma 293,7 -> porovnava se s 294."""
    nalezy = _dpi(f"#define LV_DPI_DEF {dpi}", f"CONFIG_LV_DPI_DEF={dpi}")
    assert bool(nalezy) is ceka_nalez


def test_r141_chybejici_radek_je_WARN_o_nemereni():
    """Ticho by vypadalo jako 'souhlasi'; kontrola se ale nepustila."""
    assert _dpi("/* nic tu neni */", "CONFIG_LV_USE_LOG=y") == [
        "[WARN] DPI firmwaru nezmereno: v lv_conf.h neni radek LV_DPI_DEF - "
        "kontrola NEPROBEHLA",
        "[WARN] DPI firmwaru nezmereno: v sdkconfig neni radek CONFIG_LV_DPI_DEF - "
        "kontrola NEPROBEHLA",
    ]


def test_r141_zakomentovana_hodnota_neni_hodnota():
    """`# CONFIG_... is not set` je prave to 'neni tu' - nesmi se cist jako cislo."""
    nalezy = _dpi("// #define LV_DPI_DEF 294", "# CONFIG_LV_DPI_DEF is not set")
    assert len(_obsahuji(nalezy, ZNACKA_R141_NEMERENO)) == 2
    assert _obsahuji(nalezy, ZNACKA_R141 + " s panelem") == []


def test_r141_dve_ruzne_hodnoty_je_ERROR_o_nejednoznacnosti():
    lv = "#define LV_DPI_DEF 130\n#if 0\n#define LV_DPI_DEF 294\n#endif\n"
    (hlaska,) = _dpi(lv, "CONFIG_LV_DPI_DEF=294")
    assert hlaska == (
        "[ERROR] DPI firmwaru nezmereno: v lv_conf.h je LV_DPI_DEF nekolikrat "
        "a ruzne (130, 294) - nevim, ktera hodnota plati"
    )


def test_r141_dvakrat_tataz_hodnota_se_porovna_normalne():
    lv = "#define LV_DPI_DEF 130\n#define LV_DPI_DEF 130\n"
    nalezy = _dpi(lv, "CONFIG_LV_DPI_DEF=294")
    assert len(nalezy) == 1
    assert "LV_DPI_DEF=130" in nalezy[0]


@pytest.mark.parametrize(
    "lv",
    [
        "#define LV_DPI_DEF 294",
        "  #  define  LV_DPI_DEF   294  ",
        "#define LV_DPI_DEF (294)",
        "#define LV_DPI_DEF 294 /*[px/inch]*/",
    ],
)
def test_r141_tvary_radku_lv_conf(lv):
    assert _obsahuji(_dpi(lv, "CONFIG_LV_DPI_DEF=294"), "lv_conf.h") == []


@pytest.mark.parametrize(
    "sdk",
    ["CONFIG_LV_DPI_DEF=294", "CONFIG_LV_DPI_DEF = 294", 'CONFIG_LV_DPI_DEF="294"'],
)
def test_r141_tvary_radku_sdkconfig(sdk):
    assert _obsahuji(_dpi("#define LV_DPI_DEF 294", sdk), "sdkconfig") == []


def test_r141_podobne_jmeno_v_sdkconfigu_neni_ono():
    """`CONFIG_LV_DPI_DEF_FOO` je jiny klic; cist ho by byla druha pravda."""
    nalezy = _dpi("#define LV_DPI_DEF 294", "CONFIG_LV_DPI_DEF_FOO=130")
    assert len(_obsahuji(nalezy, ZNACKA_R141_NEMERENO)) == 1


def test_r141_profil_bez_ppi_rekne_ze_nemeril():
    """OLED zadne ppi nema - nula by lhala, ze se merilo a vyslo to."""
    nalezy = _dpi(LV_CONF_DNES, SDK_DNES, PROFILE_OLED256)
    assert nalezy == [
        "[WARN] DPI firmwaru nezmereno: profil 'oled256' nema ppi - neni proti cemu merit"
    ]


def test_r141_neni_pravidlem_validatoru():
    """Deleni prace: cislo drzi ESPOS, soubory cte most (do_espos.dpi_firmwaru).

    Kdyby pravidlo sahlo na disk uvnitr `validate_data`, rozesla by se cesta
    v pameti s cestou CLI - a prave ty dve porovnava `test_tab5_validace.py`.
    """
    zpravy = _msgs(_make([_w("a", 10, 10, 100, 20)]))
    assert _obsahuji(zpravy, ZNACKA_R141) == []
    assert _obsahuji(zpravy, ZNACKA_R141_NEMERENO) == []


# --------------------------------------------------------------------------- #
# Rule 142: veta pro cloveka nese strojove jmeno
# --------------------------------------------------------------------------- #
#
# Jedine z pravidel 136-143 gatovane PROFILEM, ne daty: F4 je jazykovy zakon
# TabOSu (charta docs/CHARTA_JAZYKA_VET.md), ne vlastnost displeje. Vzory jsou
# byte-identicke s `tabos-core/tools/brana_vety.py`; vlastni test SHODY zije
# v kitu (`vd.VETY_VZORY` proti `getattr(brana_vety, klic)`), protoze ESPOS na
# tabos-core zaviset nesmi. Tady se meri to, co jde bez nej: ze konstanty JSOU
# verejne, ze jich je sedm a ze se rozhoduji v tomtez poradi.

# (text, pojmenovani v hlasce, kus, ktery se ma citovat). Kazdy radek je jiny
# tvar a je vybrany tak, aby ho nechytil zadny drivejsi vzor v poradi.
VETY_PRIPADY = [
    ("ISystemMetrics::radioTemp nedostupne", "jmeno v kodu", "::"),
    ("chyba v smalt.h", "jmeno hlavicky", "smalt.h"),
    ("vyslo na displeji %.1f", "prevodni znacka", "%.1f"),
    ("startScan() vraci UNAVAILABLE", "volani funkce", "startScan()"),
    ("esp_hosted:GetRadioInfo@fazeA", "strojovy stitek", "esp_hosted:GetRadioInfo@fazeA"),
    (
        "chybi RPC esp_wifi_ftm_initiate_session",
        "jmeno funkce SDK",
        "esp_wifi_ftm_initiate_session",
    ),
    ("ZDROJ IHwDiagnostics", "jmeno rozhrani", "IHwDiagnostics"),
]


def _veta(text, wid="patka.zdroj", **kw):
    """Jeden viditelny popisek s danym textem na tab5 (bez bloku navrh)."""
    return _make([_w(wid, 48, 140, 560, 32, text=text, **kw)])


@pytest.mark.parametrize(("text", "pojmenovani", "kus"), VETY_PRIPADY)
def test_r142_kazdy_tvar_ma_svuj_nalez_i_jmeno(text, pojmenovani, kus):
    """Sedm tvaru, sedm pojmenovani - a hlaska cituje, co presne vadi."""
    assert _errors(_veta(text)) == [
        f"{FL}: main: scene 'main': widget[0] (patka.zdroj): {ZNACKA_R142} "
        f"nese {pojmenovani}: '{kus}' - text '{text}'"
    ]


def test_r142_zivy_protejsek_z_patky_diagnostics():
    """Presna hlaska, kterou ma pristi kolo najit misto koordinatorova oka."""
    assert _errors(_veta("ZDROJ IHwDiagnostics")) == [
        f"{FL}: main: scene 'main': widget[0] (patka.zdroj): veta pro cloveka nese "
        f"jmeno rozhrani: 'IHwDiagnostics' - text 'ZDROJ IHwDiagnostics'"
    ]


def test_r142_jeden_text_dostane_JEDEN_nalez():
    """Network: `INetworkService::startScan()` je hned trojnasobny hrich.

    Vyjmenovat u jedne vety vsechny jeji tvary znamena psat tutez opravu
    trikrat. Hlasi se prvni v poradi `VETY_VZORY`, stejne jako v brane vet.
    """
    text = "INetworkService::startScan() vraci UNAVAILABLE"
    nalezy = _obsahuji(_errors(_veta(text)), ZNACKA_R142)
    assert len(nalezy) == 1
    assert "nese jmeno v kodu: '::'" in nalezy[0]


def test_r142_nepotrebuje_blok_navrh():
    """Profilove gatovani: pravidlo meri text, ne merena data z artboardu."""
    d = _veta("ZDROJ IHwDiagnostics")
    assert "navrh" not in d["scenes"]["main"]
    assert _obsahuji(_errors(d), ZNACKA_R142) != []


def test_r142_na_OLEDu_mlci():
    """Cizi navrh neni TabOS a jazykovym zakonem F4 se soudit nema."""
    d = _make(
        [_w("a", 10, 10, 200, 20, text="ZDROJ IHwDiagnostics")],
        device="oled256",
        scene_w=256,
        scene_h=128,
    )
    assert _obsahuji(_msgs(d), ZNACKA_R142) == []


def test_r142_profil_se_bere_i_bez_klice_device():
    """Rozmery sceny profil urcuji taky - jinak by se gatovani dalo obejit."""
    maly = _make(
        [_w("a", 10, 10, 200, 20, text="ZDROJ IHwDiagnostics")],
        device=None,
        scene_w=256,
        scene_h=128,
    )
    assert _obsahuji(_msgs(maly), ZNACKA_R142) == []
    velky = _make([_w("a", 48, 140, 560, 32, text="ZDROJ IHwDiagnostics")], device=None)
    assert _obsahuji(_errors(velky), ZNACKA_R142) != []


@pytest.mark.parametrize("slovo", ["INVERSE", "IDENTITA", "INKOUST", "IZOLACE"])
def test_r142_verzalky_nejsou_jmeno_rozhrani(slovo):
    """VYJIMKA navic proti brane vet, a je zmerena, ne vymyslena.

    Konvence repa je I + CamelCase (`IHwDiagnostics`, `INetworkService`,
    `I802154Service`) - vsechna maji uvnitr male pismeno. Smalt na tab5 se
    sazi VERZALKAMI, takze bez teto vyjimky by kazde takove slovo bylo
    "jmeno rozhrani". Vzor se NEMENI (test shody vzoru v kitu tim projde);
    jestli tutez vyjimku prijmout i v `brana_vety.py`, rozhoduje majitel.
    """
    assert _obsahuji(_msgs(_veta(slovo + " zapnuta")), ZNACKA_R142) == []


def test_r142_INVERSE_mlci_z_obou_duvodu_zvlast():
    """Dve umlceni teze obeti - kazde umi zmizet samo, tak se meri obe.

    `widget_catalog.json` (256x128) opravdu nese text "INVERSE": na OLEDu ho
    umlci profil, na tab5 verzalky. Kdyby test meril jen jedno, druhe by se
    dalo smazat a nikdo by si toho nevsiml.
    """
    oled = _make(
        [_w("a", 10, 10, 100, 12, text="INVERSE")],
        device="oled256",
        scene_w=256,
        scene_h=128,
    )
    assert _obsahuji(_msgs(oled), ZNACKA_R142) == []
    assert _obsahuji(_msgs(_veta("INVERSE")), ZNACKA_R142) == []
    # ... a ze to neni tim, ze pravidlo na tab5 vubec nemeri:
    assert _obsahuji(_errors(_veta("ZDROJ IHwDiagnostics")), ZNACKA_R142) != []


@pytest.mark.parametrize("slovo", sorted(VETY_NENI_ROZHRANI))
def test_r142_pojmenovane_neni_rozhrani_mlci(slovo):
    """Seznam je shodny s `brana_vety.NENI_ROZHRANI` - bezne udaje, ne typy."""
    assert _obsahuji(_msgs(_veta(f"{slovo} je pripojeny")), ZNACKA_R142) == []


def test_r142_cesta_na_karte_je_udaj_pro_cloveka():
    """Pojmenovana vyjimka: "/sd/tabos" si clovek prijde precist na kartu."""
    assert _obsahuji(_msgs(_veta("/sd/tabos")), ZNACKA_R142) == []


def test_r142_cesta_predbehne_i_jmeno_hlavicky():
    """Poradi rozhodovani je shodne s branou vet: vyjimky se ptaji PRVNI.

    Kdyby se ptaly az za vzory, "/sd/tabos.h" by se stalo "jmenem hlavicky"
    a obe brany by na temze retezci rekly neco jineho.
    """
    assert _obsahuji(_msgs(_veta("/sd/tabos.h")), ZNACKA_R142) == []


@pytest.mark.parametrize("text", ["-", "I", "x"])
def test_r142_jeden_znak_neni_veta(text):
    """Druha pojmenovana vyjimka: oddelovac neni veta pro cloveka."""
    assert _obsahuji(_msgs(_veta(text)), ZNACKA_R142) == []


def test_r142_procento_se_hlasi_vzdy_narozdil_od_brany_vet():
    """ROZDIL C. 1 proti `brana_vety.py`, a je to jine MISTO, ne jina mez.

    Ve zdroji je "%.1f" uvnitr `lv_label_set_text_fmt` legitimni - format se
    teprve dosadi. Ve scene je text HOTOVY: co je v nem, to clovek uvidi.
    """
    assert _obsahuji(_errors(_veta("vyslo na displeji %.1f")), ZNACKA_R142) != []


def test_r142_neviditelny_prvek_se_preskoci():
    d = _make([_w("a", 48, 140, 560, 32, text="ZDROJ IHwDiagnostics", visible=False)])
    assert _obsahuji(_msgs(d), ZNACKA_R142) == []


def test_r142_neretezcovy_text_patri_rule91():
    """Vadny TYP textu meri Rule 91; R142 na necitelny text nesaha."""
    d = _make([_w("a", 48, 140, 560, 32, text=123)])
    assert _obsahuji(_msgs(d), ZNACKA_R142) == []


def test_r142_vzory_jsou_verejne_a_pojmenovane_jako_v_brane_vet():
    """Kit porovna obe brany behovou hodnotou; k tomu potrebuje klice.

    Poradi neni kosmetika: rozhoduje o tom, ktere jmeno se ve vete objevi
    (`INetworkService::startScan()` je "jmeno v kodu", ne "volani funkce").
    """
    assert [klic for klic, _, _ in VETY_VZORY] == [
        "SCOPE",
        "HLAVICKA",
        "PROCENTO",
        "VOLANI",
        "CLEN",
        "STITEK",
        "API_JMENO",
        "ROZHRANI",
    ]
    assert [pojmenovani for _, pojmenovani, _ in VETY_VZORY] == [
        "jmeno v kodu",
        "jmeno hlavicky",
        "prevodni znacka",
        "volani funkce",
        "strojovy clen",
        "strojovy stitek",
        "jmeno funkce SDK",
        "jmeno rozhrani",
    ]
    assert all(hasattr(vzor, "search") for _, _, vzor in VETY_VZORY)
    assert all(isinstance(p, str) and p for p in VETY_PREDPONY_SDK)
    assert VETY_PREDPONY_SDK[0] == "esp"
    assert "xEventGroup" in VETY_PREDPONY_SDK
    assert [duvod for _, duvod in VETY_VYJIMKY] == [
        "cesta na uloziste je udaj pro cloveka",
        "neni veta",
    ]


def test_r142_predpony_sdk_odlisuji_jmeno_funkce_od_jmena_soucasti():
    """Za predponou musi byt nejmene DVA useky - hranice z brany vet.

    `esp_hosted` je jmeno soucasti (clovek ji nahrava do C6 a musi souhlasit
    do pismene), `esp_wifi_ftm_initiate_session` je jmeno funkce.
    """
    assert _obsahuji(_msgs(_veta("esp_hosted nenahrany")), ZNACKA_R142) == []
    assert _obsahuji(_errors(_veta("chybi esp_phy_*")), ZNACKA_R142) != []


# --------------------------------------------------------------------------- #
# Rule 143: slovnik stavu teze veci
# --------------------------------------------------------------------------- #
#
# Slovnik vozi kit z `tokens.json` do sceny. Tri listy panelu (Diagnostics,
# Files, Hex) mluvi o teze karte; rozpor MEZI nimi se meri bez globalniho
# stavu tim, ze se vsechny meri proti TEMUZ slovniku.

SLOVNIK = {
    "microSD": ["vlozena, pripojena", "vlozena, nepripojena", "neni vlozena"],
    "hodiny": ["hodiny nastaveny", "hodiny nenastaveny"],
}
STAVY_MICROSD = "vlozena, pripojena | vlozena, nepripojena | neni vlozena"


def _stav(text, prvek=None, *, wid="hex.karta", slovnik=None, **kw):
    """Jeden hodnotovy popisek proti slovniku stavu."""
    navrh = {"prvky": {wid: prvek if prvek is not None else {"role": "hodnota"}}}
    if slovnik is not None:
        navrh["slovnik"] = slovnik
    return _make([_w(wid, 48, 140, 560, 32, text=text, **kw)], navrh=navrh)


def test_r143_jiny_slovnik_je_WARNING():
    """Hex rika o teze karte "nedostupne", zatimco Diagnostics zna tri stavy."""
    d = _stav("nedostupne", {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_warns(d), ZNACKA_R143) == [
        f"{FL}: main: scene 'main': widget[0] (hex.karta): {ZNACKA_R143} 'microSD': "
        f"text 'nedostupne' nepouziva zadny stav ze slovniku ({STAVY_MICROSD})"
    ]
    assert _obsahuji(_errors(d), ZNACKA_R143) == []


def test_r143_stav_ze_slovniku_mlci():
    d = _stav("vlozena, nepripojena", {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_stav_s_privazkem_mlci():
    """HRANICE: stav je podretezec, dalsi udaj za nim je v poradku."""
    d = _stav(
        "microSD: vlozena, pripojena · 28,4 GB volno",
        {"role": "hodnota", "vec": "microSD"},
        slovnik=SLOVNIK,
    )
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_vic_mezer_nerozhoduje():
    """Sazba pridala mezeru navic - slovnik nesmi prestat platit."""
    d = _stav("vlozena,   nepripojena", {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_velikost_pismen_nerozhoduje():
    """Smalt sazi verzalkami; stav se tim menit nema."""
    d = _stav("VLOZENA, NEPRIPOJENA", {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_velikost_pismen_nerozhoduje_ani_ve_slovniku():
    """Druhy smer teze otazky: verzalky ve SLOVNIKU, mala pismena v textu.

    Bez tohohle testu staci slozit jen text a mereni se tvari, ze funguje -
    az do prvniho slovniku psaneho verzalkami (a smalt verzalkami sazi).
    """
    d = _stav(
        "vlozena, pripojena",
        {"role": "hodnota", "vec": "microSD"},
        slovnik={"microSD": ["VLOZENA, PRIPOJENA"]},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_diakritika_se_neprevadi_na_hola_pismena():
    """MEZ, kterou je poctive znat: "vlozena" a "vložena" jsou dve slova.

    Pro panel to dve slova opravdu jsou (vestaveny font LVGL ceske pismeno
    s diakritikou nema vubec), takze slovnik musi byt psany touz abecedou
    jako texty. Kdyby se diakritika skladala, brana by tise prijala text,
    ktery se na desce vykresli jinak, nez jak stoji ve slovniku.
    """
    d = _stav("vložena, nepřipojena", {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_warns(d), ZNACKA_R143) != []


def test_r143_vec_se_najde_i_bez_data_vec():
    """Bez `vec` se vec hleda podretezcem jmena v textu."""
    d = _stav("microSD zase nic", {"role": "hodnota"}, slovnik=SLOVNIK)
    assert _obsahuji(_warns(d), ZNACKA_R143) != []


def test_r143_jmeno_veci_bez_dalsiho_slova_mlci():
    """HRANICE: "microSD" je navesti, ne tvrzeni o stavu."""
    d = _stav("microSD", {"role": "hodnota"}, slovnik=SLOVNIK)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_veta_s_povolenym_stavem_a_privazkem_je_MEZ_pravidla():
    """Files: "karta neni vlozena nebo mount selhal" PROJDE - a je to mez.

    Slovnik meri SLOVNIK, ne pocet tvrzeni v jedne vete: povoleny stav
    "neni vlozena" v te vete je, takze pravidlo mlci. Ze veta rika dve veci
    najednou ("nebo"), je jina vada a potrebuje jine meridlo. Kdyby tenhle
    test zmizel, ctenar by si myslel, ze mereni umi vic, nez umi.
    """
    d = _stav(
        "karta neni vlozena nebo mount selhal",
        {"role": "hodnota", "vec": "microSD"},
        slovnik=SLOVNIK,
    )
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


@pytest.mark.parametrize("role", ["popisek", "patka", "titulek"])
def test_r143_popiskova_role_mlci(role):
    """Hlavicka sloupce vec jmenuje, ale zadny stav netvrdi."""
    d = _stav("nedostupne", {"role": role, "vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_bez_role_mlci():
    """Slib nese role; bez ni scena nevi, ze ta plocha ma rikat stav."""
    d = _stav("nedostupne", {"vec": "microSD"}, slovnik=SLOVNIK)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_bez_slovniku_a_bez_vec_mlci():
    """Datove gatovani: bez slovniku neni proti cemu merit."""
    d = _stav("nedostupne", {"role": "hodnota"})
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []
    assert _obsahuji(_msgs(d), ZNACKA_R143_NEMERENO) == []


def test_r143_vec_bez_slovniku_je_WARN_o_nemereni():
    """Most o veci neco tvrdil, meridlo se nepustilo - ticho by lhalo."""
    d = _stav("nedostupne", {"role": "hodnota", "vec": "USB-A"}, slovnik=SLOVNIK)
    assert _obsahuji(_warns(d), ZNACKA_R143_NEMERENO) == [
        f"{FL}: main: scene 'main': widget[0] (hex.karta): {ZNACKA_R143_NEMERENO}: "
        f"prvek mluvi o veci 'USB-A', ale slovnik stavu pro ni nikdo nedodal "
        f"(znam: hodiny, microSD) - kontrola NEPROBEHLA"
    ]


def test_r143_vec_bez_jedineho_slovniku_taky_rekne_ze_nemerila():
    """Chybi CELY slovnik: vec je deklarovana, tak se rekne, ze se nemerilo."""
    d = _stav("nedostupne", {"role": "hodnota", "vec": "USB-A"})
    nalezy = _obsahuji(_warns(d), ZNACKA_R143_NEMERENO)
    assert len(nalezy) == 1
    assert "znam: zadnou vec" in nalezy[0]


def test_r143_jmeno_veci_se_paruje_bez_ohledu_na_velikost_pismen():
    """"microsd" a "microSD" je tataz karta; do hlasky patri jmeno ze slovniku."""
    d = _stav("nedostupne", {"role": "hodnota", "vec": "microsd"}, slovnik=SLOVNIK)
    nalezy = _obsahuji(_warns(d), ZNACKA_R143)
    assert len(nalezy) == 1
    assert "'microSD'" in nalezy[0]


def test_r143_neviditelny_prvek_se_preskoci():
    d = _stav(
        "nedostupne",
        {"role": "hodnota", "vec": "microSD"},
        slovnik=SLOVNIK,
        visible=False,
    )
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []


def test_r143_meri_kazdy_list_proti_TEMUZ_slovniku():
    """Krizeni listu bez globalniho stavu: tri vety o teze karte, jeden slovnik.

    Diagnostics stav pouzije, Files a Hex kazdy jinak - a prave tim se otazka
    "shodnou se listy?" prevede na otazku, kterou lze zodpovedet z jednoho
    listu.
    """
    d = _make(
        [
            _w("diag.karta", 48, 140, 560, 32, text="vlozena, nepripojena"),
            _w("files.karta", 48, 200, 560, 32, text="nepripojena"),
            _w("hex.karta", 48, 260, 560, 32, text="nedostupne"),
        ],
        navrh={
            "slovnik": SLOVNIK,
            "prvky": {
                "diag.karta": {"role": "hodnota", "vec": "microSD"},
                "files.karta": {"role": "hodnota", "vec": "microSD"},
                "hex.karta": {"role": "hodnota", "vec": "microSD"},
            },
        },
    )
    nalezy = _obsahuji(_warns(d), ZNACKA_R143)
    assert len(nalezy) == 2
    assert all("(diag.karta)" not in m for m in nalezy)


def test_r143_slovnik_neni_objekt_je_ERROR():
    d = _stav("nedostupne", {"role": "hodnota"}, slovnik=["microSD"])
    assert f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'slovnik' ma byt objekt, je list" in _errors(d)


@pytest.mark.parametrize("stavy", [[], "vlozena", {"a": 1}, None])
def test_r143_vadny_seznam_stavu_je_ERROR_a_pravidlo_nemeri(stavy):
    """Prazdny seznam stavu by pravidlo TISE vypnul - meridlo selhalo != nula."""
    d = _stav("nedostupne", {"role": "hodnota", "vec": "microSD"}, slovnik={"microSD": stavy})
    assert _obsahuji(_errors(d), "'slovnik.microSD' ma byt neprazdny seznam stavu") != []
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []
    # ... a po zahozene veci nezbyde ticho, ale priznani, ze se nemerilo:
    assert _obsahuji(_warns(d), ZNACKA_R143_NEMERENO) != []


def test_r143_stav_ktery_neni_veta_je_ERROR():
    d = _stav(
        "nedostupne",
        {"role": "hodnota", "vec": "microSD"},
        slovnik={"microSD": ["vlozena, pripojena", "  "]},
    )
    assert _obsahuji(_errors(d), "'slovnik.microSD' ma byt seznam vet, je v nem '  '") != []


def test_r143_vec_bez_jmena_je_ERROR():
    d = _stav("nedostupne", {"role": "hodnota"}, slovnik={"  ": ["vlozena"]})
    assert _obsahuji(_errors(d), "'slovnik' ma vec bez jmena") != []


def test_r143_dve_jmena_teze_veci_je_ERROR_a_nebere_se_ani_jedno():
    """Dva slovniky teze veci jsou prave ta rozdvojena pravda, kterou meri.

    Nesmi se stat, ze si brana jeden z nich vybere - a nesmi se stat ani to,
    ze po ERRORu zbyde ticho: prvek s tou veci dostane "kontrola NEPROBEHLA".
    """
    d = _stav(
        "nedostupne",
        {"role": "hodnota", "vec": "microSD"},
        slovnik={"microSD": ["vlozena"], "microsd": ["neni vlozena"]},
    )
    assert _obsahuji(_errors(d), "dve jmena teze veci") != []
    assert _obsahuji(_warns(d), ZNACKA_R143_NEMERENO) != []


def test_r143_vadna_vec_na_prvku_je_ERROR_a_pravidlo_nemeri():
    d = _stav("nedostupne", {"role": "hodnota", "vec": 5}, slovnik=SLOVNIK)
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.hex.karta.vec' ma byt jmeno veci, "
        f"o ktere prvek mluvi, je 5"
    ) in _errors(d)
    assert _obsahuji(_msgs(d), ZNACKA_R143) == []
    assert _obsahuji(_msgs(d), ZNACKA_R143_NEMERENO) == []


# --------------------------------------------------------------------------- #
# Souziti Rule 142/143 se sousedy: jedna obet, jeden nalez
# --------------------------------------------------------------------------- #


def test_prazdna_hodnota_s_veci_dostane_jen_rule138():
    """Prazdny text patri VYHRADNE Rule 138, i kdyz o veci mluvit mel."""
    d = _stav("", {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    zpravy = _msgs(d)
    assert len(_obsahuji(zpravy, ZNACKA_R138)) == 1
    assert _obsahuji(zpravy, ZNACKA_R143) == []


def test_pomlcka_s_veci_dostane_jen_rule139():
    """Pomlcku uz obvinila Rule 139; druhy nalez by byl tyz nalez dvakrat."""
    d = _stav(POMLCKA, {"role": "hodnota", "vec": "microSD"}, slovnik=SLOVNIK)
    zpravy = _msgs(d)
    assert len(_obsahuji(zpravy, ZNACKA_R139)) == 1
    assert _obsahuji(zpravy, ZNACKA_R143) == []


def test_veta_muze_byt_zaroven_strojova_i_mimo_slovnik():
    """Naopak R142 a R143 meri RUZNE veci a smi promluvit obe.

    "ISystemMetrics::radioTemp nedostupne" je zaroven jmeno v kodu (F4)
    a jiny stav teze veci (C4). Slouceni do jednoho nalezu by schovalo jednu
    z oprav.
    """
    d = _stav(
        "ISystemMetrics::radioTemp nedostupne",
        {"role": "hodnota", "vec": "microSD"},
        slovnik=SLOVNIK,
    )
    zpravy = _msgs(d)
    assert len(_obsahuji(zpravy, ZNACKA_R142)) == 1
    assert len(_obsahuji(zpravy, ZNACKA_R143)) == 1


# --------------------------------------------------------------------------- #
# Fixtury Rule 142/143
# --------------------------------------------------------------------------- #


def test_jazykova_fixtura_ciste_projde_JSON_schematem():
    nalezy = validate_file(JAZYK_CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_jazykova_fixtura_ciste_nema_ani_jeden_ERROR():
    nalezy = validate_file(JAZYK_CISTA, warnings_as_errors=False)
    assert [i.message for i in nalezy if i.level == "ERROR"] == []


def test_jazykova_fixtura_ciste_nese_kazdy_tvar_ticha():
    """Kdyby z fixtury tvary vypadly, mlcela by z jineho duvodu, nez tvrdi."""
    scena = json.loads(JAZYK_CISTA.read_text(encoding="utf-8"))["scenes"]["main"]
    texty = {w["_widget_id"]: w["text"] for w in scena["widgets"]}
    assert set(scena["navrh"]["slovnik"]) == {"microSD", "hodiny"}
    # tri listy, jedna karta, tri ruzne vety - vsechny ze slovniku
    assert {"diag.karta", "files.karta", "hex.karta"} <= set(texty)
    assert texty["hlavicka.karta"] == "microSD"  # navesti bez stavu
    assert texty["smalt.rezim"].isupper()  # verzalky
    assert texty["files.cesta"].startswith("/sd/")  # pojmenovana vyjimka
    assert "IPv4" in texty["diag.adresa"]  # neni rozhrani


def test_jazykova_fixtura_ciste_na_obe_pravidla_mlci():
    zpravy = [i.message for i in validate_file(JAZYK_CISTA, warnings_as_errors=False)]
    assert _obsahuji(zpravy, ZNACKA_R142) == []
    assert _obsahuji(zpravy, ZNACKA_R143) == []
    assert _obsahuji(zpravy, ZNACKA_R143_NEMERENO) == []
    assert _obsahuji(zpravy, ZNACKA_NAVRH_VADNY) == []


def test_jazykova_fixtura_vady_projde_JSON_schematem():
    nalezy = validate_file(JAZYK_VADY, warnings_as_errors=False)
    assert [i.message for i in nalezy if "schema:" in i.message] == []


def test_jazykova_fixtura_vady_najde_obe_tridy():
    """Rozlisovaci schopnost: tri strojove vety (ERROR), dve veci mimo slovnik."""
    nalezy = validate_file(JAZYK_VADY, warnings_as_errors=False)
    zpravy = [i.message for i in nalezy]
    vety = _obsahuji(zpravy, ZNACKA_R142)
    stavy = _obsahuji(zpravy, ZNACKA_R143)
    assert len(vety) == 3
    assert len(stavy) == 2
    assert all(i.level == "ERROR" for i in nalezy if ZNACKA_R142 in i.message)
    assert all(i.level == "WARN" for i in nalezy if ZNACKA_R143 in i.message)
    assert _obsahuji(vety, "jmeno rozhrani: 'IHwDiagnostics'") != []
    assert _obsahuji(vety, "jmeno v kodu: '::'") != []
    assert _obsahuji(vety, "prevodni znacka: '%.1f'") != []


def test_starsi_fixtury_na_jazykova_pravidla_mlci():
    """Zmereny dopad na stavajici korpus: nula.

    R142 je jedine z novych pravidel, ktere meri KAZDY text na tab5, tedy
    i fixtury, ktere o merenych datech nevedi. Kdyby se rozsirilo, pozna se
    to tady - a ne az tim, ze nekomu zcervena cizi soubor.
    """
    for cesta in (
        FIXTURY / "tab5_clean.json",
        FIXTURY / "tab5_defects.json",
        CISTA,
        VADNA,
        SMALT_CISTA,
        SMALT_VADNA,
        MRIZKA_CISTA,
        MRIZKA_VADNA,
    ):
        zpravy = [i.message for i in validate_file(cesta, warnings_as_errors=False)]
        assert _obsahuji(zpravy, ZNACKA_R142) == [], cesta.name
        assert _obsahuji(zpravy, ZNACKA_R143) == [], cesta.name
        assert _obsahuji(zpravy, ZNACKA_R143_NEMERENO) == [], cesta.name


# --------------------------------------------------------------------------- #
# Rule 142, osmy tvar: jmena ze SDK a verzalkove slovo
# --------------------------------------------------------------------------- #
#
# Vyjimka "slovo cele verzalkami neni jmeno rozhrani" byla PRILIS SIROKA:
# umlcela `vraci UNAVAILABLE` i `IHWDIAGNOSTICS`, coz jsou obe zive vady F4
# z panelu. Zaroven ale musi zustat ticho na `USB`, `RAM`, `LVGL` a
# `TEPLOTA CPU`. Tvar slova tedy nerozhoduje - rozhoduje, jestli je to slovo
# jmenem NEKDE V SDK, a ten seznam se NEOPISUJE (`jmena_ze_sdk`).

SDK_JMENA = frozenset({"IHwDiagnostics", "Unavailable", "NotFound", "Error", "Mock"})


def _veta_sdk(text, jmena=SDK_JMENA, **kw):
    """Popisek na tab5 se seznamem jmen SDK ve scene (tak, jak ho vozi most)."""
    navrh = {"jmena_sdk": sorted(jmena)} if jmena is not None else {}
    return _make(
        [_w("patka.zdroj", 48, 140, 560, 32, text=text, **kw)], navrh=navrh
    )


def test_jmena_ze_sdk_cte_oba_tvary_z_hlavicky():
    """Rozhrani (`class IHwDiagnostics`) i hodnoty enumu z tela `{...}`."""
    jmena = jmena_ze_sdk(SDK_HLAVICKA)
    assert "IHwDiagnostics" in jmena          # class
    assert "IRadioInfo" in jmena              # struct
    assert "Unavailable" in jmena             # hodnota enumu bez prirazeni
    assert "None" in jmena                    # hodnota enumu s "= 0"
    assert "Mock" in jmena                    # enum s typem za dvojteckou


def test_jmena_ze_sdk_necte_co_nema():
    """Negativni trida: co konvenci NEODPOVIDA, se do seznamu dostat nesmi.

    Bez ni by test prosel i seznamu, ktery bere kazde slovo v hlavicce -
    a takovy seznam by obvinil kazdou vetu, ve ktere se nahodou objevi
    jakekoli slovo z SDK.
    """
    jmena = jmena_ze_sdk(SDK_HLAVICKA)
    assert "DesktopMock" not in jmena         # neni I + velke pismeno
    assert "Ihned" not in jmena               # I + male pismeno je ceske slovo
    assert "I2cSbernice" not in jmena
    assert "unavailableSomewhere" not in jmena


def test_jmena_ze_sdk_prochazi_i_adresar():
    """Cesta smi byt soubor i koren stromu - most vozi koren SDK."""
    assert jmena_ze_sdk(SDK_HLAVICKA) <= jmena_ze_sdk(FIXTURY)
    assert "IHwDiagnostics" in jmena_ze_sdk(FIXTURY)


def test_jmena_ze_sdk_na_neexistujici_ceste_je_PRAZDNO_ne_vyjimka():
    """Prazdno je platna odpoved - a volajici o nem MUSI rict nahlas."""
    assert jmena_ze_sdk(FIXTURY / "tohle-neexistuje") == frozenset()


def test_r142_verzalkove_jmeno_ze_SDK_je_ERROR():
    """Ziva vada z Network Tools: "vraci UNAVAILABLE"."""
    nalezy = _obsahuji(_errors(_veta_sdk("Sken nedostupny - sluzba vraci UNAVAILABLE")), ZNACKA_R142)
    assert len(nalezy) == 1
    assert "jmeno ze SDK: 'UNAVAILABLE'" in nalezy[0]


@pytest.mark.parametrize("slovo", ["USB", "RAM", "LVGL", "AP", "SSID"])
def test_r142_verzalky_mimo_SDK_mlci(slovo):
    """Kontrolni skupina: verzalky, ktere v SDK nejsou, nejsou vada."""
    assert _obsahuji(_msgs(_veta_sdk(f"{slovo} je pripojeny")), ZNACKA_R142) == []


def test_r142_cely_text_verzalkami_je_STITEK_a_NEMERI_se():
    """(a) z rozhodnuti: v celoverzalkovem textu se trida nemeri.

    Hodnoty enumu SDK jsou bezna slova (`Error`, `Live`, `Smalt`), takze
    stitek `SMALT` nebo `CHYBA` by se s nimi trefil a brana by obvinila
    spravny popisek. Je to ZMERENA MEZ, ne opomenuti - proto ma vlastni
    test a je zapsana i ve sdilenem korpusu vet.
    """
    assert _obsahuji(_msgs(_veta_sdk("IHWDIAGNOSTICS")), ZNACKA_R142) == []
    assert _obsahuji(_msgs(_veta_sdk("ZDROJ UNAVAILABLE")), ZNACKA_R142) == []
    # ... a ze to neni tim, ze by trida nemerila vubec:
    assert _obsahuji(_errors(_veta_sdk("zdroj vraci UNAVAILABLE")), ZNACKA_R142) != []


def test_r142_mala_pismena_rozhoduji_o_meritelnosti():
    """MUTACE: kdyby (a) zmizela, tenhle par by rekl totez. Rika neco jineho."""
    velky = _obsahuji(_msgs(_veta_sdk("ZDROJ IHWDIAGNOSTICS")), ZNACKA_R142)
    maly = _obsahuji(_msgs(_veta_sdk("zdroj IHWDIAGNOSTICS")), ZNACKA_R142)
    assert velky == []
    assert len(maly) == 1


def test_r142_shoda_se_jmenem_SDK_je_bez_ohledu_na_velikost_pismen():
    """`UNAVAILABLE` na panelu proti `Unavailable` v hlavicce."""
    assert _obsahuji(_errors(_veta_sdk("stav: UNAVAILABLE")), ZNACKA_R142) != []


def test_r142_MOCK_je_pojmenovana_vyjimka():
    """`Mock` JE hodnota enumu, ale "MOCK DATA" je ceduka pro cloveka.

    Rozhodnuti je starsi nez tahle trida (hlavicka `brana_vety.py`)
    a je ZMERENE: bez teto vyjimky pribylo v jadre a v appkach sedm
    nalezu a vsech sedm bylo na retezcich typu "MOCK DATA - desktop".
    """
    assert "MOCK" in VETY_NENI_JMENO_SDK
    assert _obsahuji(_msgs(_veta_sdk("MOCK DATA - desktop, ne deska")), ZNACKA_R142) == []
    # Pozitivni kontrola teze vety: jiny SDK tvar v ni vystreli.
    assert _obsahuji(_errors(_veta_sdk("MOCK DATA - vraci UNAVAILABLE")), ZNACKA_R142) != []


def test_r142_bez_jmen_SDK_se_trida_NEMERI_a_rekne_se_to():
    """Ticho vydavane za "cisto" je prave ta vada, kterou kampan odstranuje."""
    bez = _veta_sdk("Sken nedostupny - sluzba vraci UNAVAILABLE", jmena=None)
    assert _obsahuji(_errors(bez), ZNACKA_R142) == []
    assert _obsahuji(_warns(bez), ZNACKA_R142_NEMERENO) != []


def test_r142_WARN_o_nemereni_nevyskakuje_kde_neni_co_merit():
    """Varovani, ktere sviti porad, nikdo necte."""
    bez = _veta_sdk("Vlozena, nepripojena.", jmena=None)
    assert _obsahuji(_msgs(bez), ZNACKA_R142_NEMERENO) == []


def test_r142_vadny_seznam_jmen_je_ERROR_o_mostu():
    """Rozbita smlouva o atributech je vada MOSTU, ne navrhu."""
    d = _make([_w("a", 48, 140, 560, 32, text="ahoj")], navrh={"jmena_sdk": "IHwDiagnostics"})
    assert _obsahuji(_errors(d), ZNACKA_NAVRH_VADNY) != []


# --------------------------------------------------------------------------- #
# Rule 142, tvar CLEN: jmeno souboru neni strojovy clen
# --------------------------------------------------------------------------- #


def test_r142_strojovy_clen_je_ERROR():
    """Ziva vada z Network Tools; do 9. 9. 2026 ji nechytal zadny tvar."""
    text = "Sum se nemeri - chybi API (rx_ctrl.noise_floor v promiskuitnim rezimu)"
    nalezy = _obsahuji(_errors(_veta(text)), ZNACKA_R142)
    assert len(nalezy) == 1
    assert "strojovy clen: 'rx_ctrl.noise_floor'" in nalezy[0]


@pytest.mark.parametrize(
    "text",
    [
        "capture_0412.la",
        "uart_dump.bin",
        "mereni_i2c_100_khz.la",
        "RRRR-MM-DD_mereni.la",
        "cat zaznam_042.la | hex",
        "zaznam_042.LA",
    ],
)
def test_r142_jmeno_souboru_neni_clen(text):
    """Kontrolni skupina: jmeno souboru je pro cloveka MISTO, ne jmeno v kodu.

    Zmereno na 62 listech: bez teto hranice hlasil vzor deset jmen souboru
    na listech Souboru, Hexu a klavesnice - a ani jedno neni vada.
    """
    assert _obsahuji(_msgs(_veta(text)), ZNACKA_R142) == []


def test_r142_pripona_zdrojaku_zustava_nalezem():
    """MUTACE: kdyby se do PRIPONY_SOUBORU dostalo 'h', umlkla by hlavicka."""
    assert "h" not in PRIPONY_SOUBORU
    assert "cpp" not in PRIPONY_SOUBORU
    nalezy = _obsahuji(_errors(_veta("chyba v data_source.h")), ZNACKA_R142)
    assert len(nalezy) == 1
    assert "data_source.h" in nalezy[0]


def test_r142_clen_bez_podtrzitka_neni_clen():
    """Ceska veta s teckou uprostred ("web tabos.cc") nesmi byt clen.

    Podtrzitko je ta rozhodujici pulka vzoru: v ceske vete se nevyskytuje.
    """
    assert _obsahuji(_msgs(_veta("dve AP teze site. Druha je slabsi")), ZNACKA_R142) == []


# --------------------------------------------------------------------------- #
# Druh listu: obrazovka vs vyklad o navrhu
# --------------------------------------------------------------------------- #
#
# Artboard je bud obrazovka (co bude na skle), nebo vyklad o navrhu. Zakon F4
# mluvi o textu NA PRISTROJI; vyklad vadu CITUJE. Bez tohohle rozliseni hlasila
# brana na 62 listech osm nalezu na ctyrech vykladovych listech (Main, Dnes,
# FilesStavy, SvorkaJazyk) a vsechny osm byly citace.


def _vyklad(text, druh="vyklad"):
    return _make(
        [_w("em.56", 48, 140, 560, 32, text=text)],
        navrh={"druh": druh} if druh is not None else {},
    )


def test_druh_listu_zna_prave_dve_hodnoty():
    assert DRUHY_LISTU == ("obrazovka", "vyklad")


def test_vykladovy_list_pravidlo_142_NEMERI():
    text = "V ceske sestave patri carka; %.1f ji neda."
    assert _obsahuji(_errors(_vyklad(text)), ZNACKA_R142) == []


def test_vykladovy_list_o_svem_tichu_REKNE():
    """Nemereno se nesmi dat zamenit za zmereno."""
    assert _obsahuji(_warns(_vyklad("cokoli")), ZNACKA_R142_VYKLAD) != []


def test_obrazovka_meri_dal():
    """Pozitivni kontrola: tataz veta na obrazovce je porad ERROR."""
    text = "V ceske sestave patri carka; %.1f ji neda."
    assert _obsahuji(_errors(_vyklad(text, druh="obrazovka")), ZNACKA_R142) != []
    assert _obsahuji(_errors(_vyklad(text, druh=None)), ZNACKA_R142) != []


def test_chybejici_druh_je_obrazovka():
    """Kdo nic nerekl, je mereny - dnesni chovani zustava vychozi."""
    assert _obsahuji(_msgs(_vyklad("cokoli", druh=None)), ZNACKA_R142_VYKLAD) == []


def test_preklep_v_druhu_je_ERROR_a_list_se_MERI_dal():
    """Tise prijaty preklep by pravidlo vypnul na celem listu."""
    # Mezera navic je preklep, ne jiny druh: orizne se a list zustane vykladem.
    d = _vyklad("V ceske sestave patri carka; %.1f ji neda.", druh="vyklad ")
    assert _obsahuji(_errors(d), ZNACKA_NAVRH_VADNY) == []
    assert _obsahuji(_warns(d), ZNACKA_R142_VYKLAD) != []
    # Nezname jmeno uz preklep JE - a list se meri dal, at se pravidlo
    # nevypne tim, ze se nekdo prepise.
    d2 = _vyklad("V ceske sestave patri carka; %.1f ji neda.", druh="dokument")
    assert _obsahuji(_errors(d2), ZNACKA_NAVRH_VADNY) != []
    assert _obsahuji(_errors(d2), ZNACKA_R142) != []


def test_vyklad_nevypina_geometricka_pravidla():
    """Vyklad je porad kresba: co pretece, pretece i na nem.

    Kdyby `druh` vypinal vsechno, byl by to prepinac na branu, ne rozliseni
    predmetu mereni.
    """
    d = _make(
        [_w("txt.1", 40, 630, 200, 18, text="dlouhy popis")],
        navrh={
            "druh": "vyklad",
            "prvky": {"txt.1": {"sirka_textu": 290.1, "sirka_bunky": 278.0}},
        },
    )
    assert _obsahuji(_errors(d), ZNACKA_R137) != []


# --------------------------------------------------------------------------- #
# SDILENY KORPUS VET: parita s `tabos-core/tools/brana_vety.py` CHOVANIM
# --------------------------------------------------------------------------- #
#
# Test shody VZORU (`VETY_VZORY` proti `getattr(brana_vety, klic)`) je slepy
# k vyjimkam, ktere zijou v KODU: `slovo.isupper()` obe brany do 9. 9. 2026
# rozdelovala ('IHWDIAGNOSTICS' = jmeno rozhrani v jadre, TICHO v ESPOSu)
# a test o tom nevedel. Parita se proto meri CHOVANIM na seznamu retezcu.
#
# Korpus zije TADY, protoze ESPOS na `tabos-core` zaviset nesmi; druha
# strana ho cte pres ../research/ESPOS a kdyz ESPOS vedle neni, PRESKOCI SE
# S POJMENOVANYM DUVODEM.


def _korpus():
    return json.loads(KORPUS_VET.read_text(encoding="utf-8"))


def test_korpus_vet_je_nabity():
    """Korpus bez obou trid by byl zeleny nad nicim."""
    k = _korpus()
    verdikty = [z["verdikt"] for z in k["vety"]]
    assert verdikty.count("krici") >= 8
    assert verdikty.count("mlci") >= 8
    assert set(verdikty) == {"krici", "mlci"}
    assert k["jmena_sdk"], "bez jmen SDK by devaty tvar mlcel nad prazdnou mnozinou"


def test_korpus_vet_ma_u_kazde_vety_duvod_i_puvod():
    """Radek bez duvodu je diera: nikdo pozdeji nepozna, proc tam je."""
    for z in _korpus()["vety"]:
        assert z["duvod"].strip(), z["text"]
        assert z["kde"].strip(), z["text"]
        if z["verdikt"] == "krici":
            assert z["kus"].strip(), z["text"]


def test_korpus_vet_sedi_na_ESPOSu():
    """Kazda veta korpusu ma v ESPOSu verdikt, ktery korpus slibuje."""
    k = _korpus()
    jmena = frozenset(k["jmena_sdk"])
    potize = []
    for z in k["vety"]:
        d = _veta_strojove_jmeno(z["text"], jmena)
        krici = d is not None
        if krici != (z["verdikt"] == "krici"):
            potize.append(f"{z['text']!r}: korpus rika {z['verdikt']}, ESPOS {d}")
        elif krici and z["kus"] not in d[1]:
            potize.append(f"{z['text']!r}: ESPOS cituje {d[1]!r}, korpus {z['kus']!r}")
    assert not potize, "korpus a ESPOS se rozesly:\n" + "\n".join(potize)


def test_korpus_vet_meri_i_pres_celou_branu():
    """Nejen `_veta_strojove_jmeno`, ale cela cesta pres `validate_data`.

    Bez toho by korpus mohl byt zeleny nad funkci, kterou pravidlo 142
    nevola (napr. kdyby se gatovani rozbilo).
    """
    k = _korpus()
    for z in k["vety"]:
        zpravy = _obsahuji(_errors(_veta_sdk(z["text"], jmena=k["jmena_sdk"])), ZNACKA_R142)
        assert bool(zpravy) == (z["verdikt"] == "krici"), z["text"]


# --------------------------------------------------------------------------- #
# Rule 136: zamerny presah rodice (`presah`)
# --------------------------------------------------------------------------- #
#
# Kritik, DROBNE 1: "R136 nema jak povolit zamerny presah. Az takovy prvek
# nekdo nakresli, bude se vypinat cele pravidlo." Nakreslene uz jsou: list
# Main kitu ma dva popisky zon 20 px NAD svym boxem a nic se na nich neoreze
# (`.zona` nema `overflow:hidden`). Oznaceni je proto tataz pojistka jako
# `prazdne` u Rule 138 - vcetne toho, ze samo ma svuj nalez.

RODIC_MALY = [520, 123, 720, 261]


def _presah(vyska_nad, oznaceni=None, *, wid="u.35"):
    """Popisek `vyska_nad` px nad hornou hranou sveho rodice."""
    prvek = {"rodic": RODIC_MALY}
    if oznaceni is not None:
        prvek["presah"] = oznaceni
    return _make(
        [_w(wid, 520, 123 - vyska_nad, 141, 10, text="ZONA 1")],
        navrh={"prvky": {wid: prvek}},
    )


def test_r136_zamerny_presah_je_WARN_ne_ERROR():
    d = _presah(20, "popisek zony stoji NAD svym boxem, aby ho nezakryval")
    assert _obsahuji(_errors(d), ZNACKA_R136_RODIC) == []
    nalezy = _obsahuji(_warns(d), ZNACKA_R136_OZNACENI)
    assert len(nalezy) == 1
    assert "popisek zony stoji NAD svym boxem" in nalezy[0]


def test_r136_bez_oznaceni_je_tyz_tvar_ERROR():
    """Pozitivni kontrola: kdyby pravidlo na tenhle tvar nikdy nestrilelo,
    byl by test vys zeleny i nad vypnutym pravidlem."""
    assert _obsahuji(_errors(_presah(20)), ZNACKA_R136_RODIC) != []


def test_r136_oznaceni_bez_presahu_je_WARN_o_zbytecnem_oznaceni():
    """Oznaceni, ktere uz neplati, umlci pristi skutecny presah mlcky."""
    d = _presah(0, "kdysi to precnivalo")
    assert _obsahuji(_errors(d), ZNACKA_R136_RODIC) == []
    assert _obsahuji(_warns(d), ZNACKA_R136_OZNACENI) != []


def test_r136_oznaceni_NEUMLCI_zasah_do_pasu():
    """Pas je slib o miste, ktere patri nekomu jinemu.

    MUTACE: kdyby oznaceni umlcelo i pasovou pulku, dala by se jim vypnout
    prave ta vada, kvuli ktere pravidlo vzniklo (dlazdice useknuta patkou).
    """
    d = _make(
        [_w("dlazdice.77", 245, 560, 302, 68, text="RF Sonda")],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {"dlazdice.77": {"rodic": OBSAH, "presah": "je to zamer"}},
        },
    )
    assert _obsahuji(_errors(d), ZNACKA_R136_PAS) != []


def test_r136_oznaceni_NEUMLCI_utek_clena_z_pasu():
    d = _make(
        [_w("txt.85", 245, 560, 302, 19, text="normalni rezim")],
        navrh={
            "pasy": PAS_RAZITKO,
            "prvky": {
                "txt.85": {"rodic": OBSAH, "pas": "razitko", "presah": "je to zamer"}
            },
        },
    )
    assert _obsahuji(_errors(d), ZNACKA_R136_PAS_VEN) != []


def test_r136_prazdne_oznaceni_presahu_se_zahodi_NAHLAS():
    """Vypinac bez duvodu je diera; pravidlo musi dobehnout."""
    d = _presah(20, "   ")
    assert _obsahuji(_errors(d), ZNACKA_R136_RODIC) != []
    assert _obsahuji(_warns(d), ZNACKA_NAVRH_VADNY) != []


def test_r136_neretezcove_oznaceni_presahu_je_ERROR():
    d = _make(
        [_w("u.35", 520, 103, 141, 10, text="ZONA 1")],
        navrh={"prvky": {"u.35": {"rodic": RODIC_MALY, "presah": 1}}},
    )
    assert _obsahuji(_errors(d), ZNACKA_NAVRH_VADNY) != []
    assert _obsahuji(_errors(d), ZNACKA_R136_RODIC) != []


# --------------------------------------------------------------------------- #
# Rule 141: DOKUMENTOVANA odchylka LV_DPI_DEF
# --------------------------------------------------------------------------- #
#
# Kritik, DROBNE 3: "dokud majitel firmware neopravi, vraci brana vzdy 1.
# Trvale rude svetlo je vlastni druh selhani (nikdo uz nekouka, co jeste
# svitne)." Rozhodnuti koordinatora podle kampane panel-maximum (Z7):
# LV_DPI_DEF zustava 130, protoze `lv_dpx` se v TabOSu nevola a prepnuti na
# 294 by prestavelo vychozi tema LVGL. Odchylka se proto ZAPISUJE do
# `tokens.json` (`firmware.lv_dpi_def`) i s duvodem a brana ji hlasi jako
# WARN - videt zustane, kit uz neshodi.
#
# Vypinac bez duvodu ale NENI rozhodnuti: preklep v bloku je ERROR.

DPI_130 = "#define LV_DPI_DEF 130\n"
SDK_130 = 'CONFIG_LV_DPI_DEF=130\n'
DOKUMENT = {"hodnota": 130, "duvod": "lv_dpx se nevola, scrollbar je 12 px (Z7)"}


def test_r141_bez_dokumentace_je_dnesni_chovani_ERROR():
    """Pozitivni kontrola: kdo nic nezapsal, meri se proti profilu 294."""
    n = zkontroluj_dpi(DPI_130, SDK_130, PROFILE_TAB5)
    assert [i.level for i in n] == ["ERROR", "ERROR"]
    assert all(ZNACKA_R141 in i.message for i in n)


def test_r141_dokumentovana_odchylka_je_WARN_s_duvodem():
    n = zkontroluj_dpi(DPI_130, SDK_130, PROFILE_TAB5, dokumentovano=DOKUMENT)
    assert [i.level for i in n] == ["WARN", "WARN"]
    for i in n:
        assert ZNACKA_R141_ODCHYLKA in i.message
        assert "294" in i.message                 # proti cemu se merilo
        assert "lv_dpx se nevola" in i.message    # a proc se to nemeri


def test_r141_firmware_mimo_dokumentaci_je_ERROR():
    """MUTACE: dokumentace neni vypinac, je to DRUHA MEZ.

    Kdyby blok jen umlcel pravidlo, prosla by i hodnota, o ktere nikdo
    nerozhodl - a to je horsi nez trvale rude svetlo.
    """
    n = zkontroluj_dpi("#define LV_DPI_DEF 160\n", SDK_130, PROFILE_TAB5,
                       dokumentovano=DOKUMENT)
    urovne = [i.level for i in n]
    assert "ERROR" in urovne
    assert any("dokumentace se rozesly" in i.message for i in n)


def test_r141_dokumentovana_shoda_s_profilem_MLCI():
    """Kdyz firmware nakonec sedne na panel, neni co hlasit ani jako WARN."""
    n = zkontroluj_dpi("#define LV_DPI_DEF 294\n", "CONFIG_LV_DPI_DEF=294\n",
                       PROFILE_TAB5,
                       dokumentovano={"hodnota": 294, "duvod": "srovnano s panelem"})
    assert [i.message for i in n if i.level != "WARN"] == []
    assert _obsahuji([i.message for i in n], ZNACKA_R141_ODCHYLKA) != []


@pytest.mark.parametrize(
    "blok",
    [
        130,                                   # neni objekt
        "130",                                 # taky neni objekt
        {"duvod": "chybi hodnota"},            # bez hodnoty
        {"hodnota": "130", "duvod": "text"},   # hodnota neni cislo
        {"hodnota": 0, "duvod": "text"},       # nekladne cislo
        {"hodnota": -130, "duvod": "text"},
        {"hodnota": 130},                      # bez duvodu
        {"hodnota": 130, "duvod": "   "},      # duvod bez vety
        {"hodnota": 130, "duvod": 5},          # duvod neni veta
    ],
)
def test_r141_preklep_v_dokumentaci_je_ERROR_ne_ticho(blok):
    """Tise prijaty preklep by za majitele rozhodl, ze odchylka neplati."""
    n = zkontroluj_dpi(DPI_130, SDK_130, PROFILE_TAB5, dokumentovano=blok)
    assert [i.level for i in n] == ["ERROR"], [i.message for i in n]
    assert ZNACKA_R141_NEMERENO in n[0].message


def test_r141_preklep_se_NEVRACI_tise_k_profilu():
    """Ani ERROR proti 294 by nebyl poctivy: rozhodl by taky, jen naopak.

    Hlaska musi rikat, ze se NEMERILO, ne ze firmware nesouhlasi s panelem.
    """
    n = zkontroluj_dpi(DPI_130, SDK_130, PROFILE_TAB5,
                       dokumentovano={"hodnota": 130})
    assert len(n) == 1
    assert ZNACKA_R141 not in n[0].message.split(":")[0]
    assert "vypinac brany" in n[0].message


def test_r141_dokumentace_na_profilu_bez_ppi_nic_nezmeni():
    """OLED nema panel, takze neni proti cemu merit - ani s dokumentaci."""
    n = zkontroluj_dpi(DPI_130, SDK_130, PROFILE_OLED256, dokumentovano=DOKUMENT)
    assert len(n) == 1
    assert ZNACKA_R141_NEMERENO in n[0].message
