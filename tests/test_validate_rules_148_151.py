"""Testy pravidel 148-151 a rozsireni Rule 17 v `tools/validate_design.py`.

Treti vlna pravidel nad MERENYMI daty z artboardu (scenovy blok ``navrh``,
ktery vozi most `tabos-ui-kit/navrh-appky/do_espos.py`). Vsechna ctyri merila
do 2026-09-09 meridla v kitu, ktera nemela ani jeden test - a dve z nich
merila jen 25 listu z 62.

Rule 148: rez pisma mimo ZAVAZNOU SKALU roli (pet roli, pet velikosti).
          Jmenovite vyjimky jsou per-list a ke kazde patri veta proc: rez
          13 px je na klavesnici vedomy, na Nastaveni preklep.
Rule 149: uhlova velikost znaku pod mezi ctenosti. Pixel o citelnosti
          nerika nic - tyz rez 14 px ma na 120 PPI verzalku 2,07 mm
          a na 294 PPI 0,85 mm - takze se meri UHEL na vzdalenosti, ze
          ktere se pristroj cte. Meze 5' (letmo) a 3' (tvar glyfu); ISO
          9241-303 zada 16' a tenhle jazyk je na 40-92 % te meze, takze
          ISO se POCITA a pise do hlasky, ale NESOUDI se podle ni (jinak
          by pravidlo vystrelilo na vsech 3 751 textech a nemerilo nic).
Rule 150: barva prvku mimo paletu. Hlasi se po BARVACH s poctem prvku, ne
          po prvcich: barva se opakuje a 54 vet o peti barvach je
          smetiste, ve kterem nalez zanikne.
Rule 151: text nalepeny na ram misto na zavaznou vsazku. Blok s vlastni
          vsazkou (klavesnice) se PARAMETRIZUJE, ne vypina.
Rule 17:  druha mez WCAG 2.1 AA pro velky text (3,0:1 od 24 px, nebo od
          19 px tucne) + vyjimka neaktivniho ovladace (1.4.3), ktera se
          ale HLASI - ticho by se nedalo odlisit od zmereneho "v poradku".

Ke kazdemu pravidlu je POZITIVNI trida (vystreli), NEGATIVNI (mlci)
i hranice na pixel. Navic:

* **Fixtury jdou pres `validate_file`**, tedy vcetne POVINNEHO JSON
  schematu - jinak by se neoverilo, ze scena takovy blok vubec smi nest.
* **Profilove gatovani ma obe strany**: Rule 149 a druha mez Rule 17 jsou
  vazane na profil (PPI, cteci vzdalenost, rezim kontrastu), takze se
  tataz scena meri na tab5 (hlasi) i na oled256 (mlci).
* **Mutacni test**: bez druhe meze WCAG dostane velky titulek na 3,88:1
  falesny poplach. Kdyby ten test nebyl, rozsireni by nikdo nezmeril.
* **Poctive nahlas u fixtur**: vada Rule 148 a Rule 149 je SYNTETICKA.
  Na 62 listech kitu neni ani jeden rez mimo skalu bez jmenovite vyjimky
  a nejmensi rez je 12 px (5,54', tedy nad mezi). Fixtury Rule 150 a 151
  jsou naopak ze SKUTECNE sceny (`DnesSystemMonitor`, `SvorkaKlavesnice`).
"""

from __future__ import annotations

import dataclasses
import json
import pathlib

import pytest

from tools.validate_design import (
    PROFILE_OLED256,
    PROFILE_TAB5,
    PROFILES,
    R149_MEZ_ISO,
    R149_MEZ_LETMO,
    R149_MEZ_TVAR,
    WCAG_TUCNE_PX,
    WCAG_VELKY_PX,
    ZNACKA_NAVRH_VADNY,
    ZNACKA_R17_NEAKTIVNI,
    ZNACKA_R148,
    ZNACKA_R148_NEMERENO,
    ZNACKA_R148_ODCHYLKA,
    ZNACKA_R149,
    ZNACKA_R150,
    ZNACKA_R150_NEMERENO,
    ZNACKA_R150_ODCHYLKA,
    ZNACKA_R151,
    ZNACKA_R151_NEMERENO,
    validate_data,
    validate_file,
)

FL = "test"
FIXTURY = pathlib.Path(__file__).parent / "fixtures"

SKALA = {"rezy": [14, 16, 20, 24, 32], "vyjimky": {}}
PALETA = ["#14170F", "#1C2016", "#A9C24A", "#9BA28D", "#E9A63C", "#FF7B5E",
          "#E4DFCC", "#E27BE2", "#6F7764", "#E6E1CE", "#12150E", "#5A5F4C",
          "#6B6653"]
SOUSTAVA = {"pole_x": 20, "vsazka": 16}
# Uplny blok `orez`, tak jak ho na prvek posila most kitu. Znamena
# "tenhle prvek most opravdu zmeril" a je to zavora NEMERENO u Rule 151.
OREZ_ZMERENY = {"sirka_obsahu": 200, "sirka_schranky": 200,
                "vyska_obsahu": 19, "vyska_schranky": 19}

# Dvojice ZMERENE `zmer_kontrast.py` na vykreslenem DOM kitu (2026-09-09).
# Nejsou vymyslene: prvni dve jsou zasedle ovladace, ktere stara Rule 17
# nevidela vubec (most jí vozil NAPSANOU barvu #12150E, ne videnou).
ZASEDLE_PRIPOJIT = ("#946D2A", "#E9A63C")     # 2,23:1, FilesStavy, 16 px
ZASEDLE_SROVNAT = ("#727164", "#14170F")      # 3,68:1, Settings, 20 px
OBRYS_NA_PODKLADU = ("#6F7764", "#14170F")    # 3,88:1 - mezi 3,0 a 4,5
INKUTLUM_NA_PODKLADU = ("#5A5F4C", "#14170F")  # 2,74:1 - pod obema mezemi


def _w(wid, x, y, ww, hh, *, text="AHOJ", t="label", fg="#E4DFCC", bg="#14170F"):
    return {
        "type": t, "x": x, "y": y, "width": ww, "height": hh, "text": text,
        "color_fg": fg, "color_bg": bg, "align": "left", "valign": "middle",
        "_widget_id": wid,
    }


def _make(widgets, *, navrh=None, device="tab5"):
    scene = {"width": 1280, "height": 720, "widgets": widgets}
    if navrh is not None:
        scene["navrh"] = navrh
    data = {"scenes": {"main": scene}}
    if device is not None:
        data["device"] = device
    return data


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _zpravy(data, znacka, **kw):
    return [i for i in _issues(data, **kw) if znacka in i.message]


def _fix(jmeno):
    return validate_file(FIXTURY / jmeno, warnings_as_errors=False)


def _fix_zpravy(jmeno, znacka):
    return [i for i in _fix(jmeno) if znacka in i.message]


# --------------------------------------------------------------------------- #
# Rule 148 - rez pisma mimo zavaznou skalu
# --------------------------------------------------------------------------- #


def test_r148_rez_mimo_skalu_vystreli():
    data = _make(
        [_w("popis.1", 36, 120, 200, 19, text="TEPLOTA CPU")],
        navrh={"prvky": {"popis.1": {"font_size": 18}}, "skala": SKALA},
    )
    n = _zpravy(data, ZNACKA_R148)
    assert len(n) == 1
    assert "18 px" in n[0].message
    assert "14/16/20/24/32" in n[0].message


def test_r148_rez_ve_skale_mlci():
    for rez in SKALA["rezy"]:
        data = _make(
            [_w("popis.1", 36, 120, 200, 19, text="TEPLOTA CPU")],
            navrh={"prvky": {"popis.1": {"font_size": rez}}, "skala": SKALA},
        )
        assert not _zpravy(data, ZNACKA_R148), rez


def test_r148_hranice_na_pixel():
    """16 px mlci, 16,5 px uz ne. Rez je cislo, ne priblizne cislo."""
    for rez, ceka in ((16, 0), (16.5, 1), (17, 1)):
        data = _make(
            [_w("popis.1", 36, 120, 200, 19, text="TEPLOTA CPU")],
            navrh={"prvky": {"popis.1": {"font_size": rez}}, "skala": SKALA},
        )
        assert len(_zpravy(data, ZNACKA_R148)) == ceka, rez


def test_r148_jmenovita_vyjimka_je_odchylka_s_duvodem():
    """Vyjimka NEMLCI: rekne se, ze se odchyluje, a proc."""
    skala = {"rezy": [14, 16, 20, 24, 32],
             "vyjimky": {"40": "hlavni odecet vzdalenosti, jedine misto nad ISO"}}
    data = _make(
        [_w("velk.1", 36, 120, 300, 45, text="5,6 m")],
        navrh={"prvky": {"velk.1": {"font_size": 40}}, "skala": skala},
    )
    assert not _zpravy(data, ZNACKA_R148)
    odch = _zpravy(data, ZNACKA_R148_ODCHYLKA)
    assert len(odch) == 1
    assert "jedine misto nad ISO" in odch[0].message


def test_r148_vyjimka_bez_duvodu_se_zahazuje_a_rekne_se_to():
    """Vyjimka bez vety je jen vypinac pravidla - musi propadnout NALEZEM."""
    skala = {"rezy": [14, 16, 20, 24, 32], "vyjimky": {"40": "   "}}
    data = _make(
        [_w("velk.1", 36, 120, 300, 45, text="5,6 m")],
        navrh={"prvky": {"velk.1": {"font_size": 40}}, "skala": skala},
    )
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)
    assert _zpravy(data, ZNACKA_R148)      # zahozena vyjimka pravidlo NEVYPNE


def test_r148_vyjimka_plati_JEN_pro_svuj_list():
    """Tyz rez, dva listy: s vyjimkou odchylka, bez ni nalez."""
    prvky = {"drobne.1": {"font_size": 13}}
    s_vyjimkou = _make(
        [_w("drobne.1", 36, 120, 200, 17, text="rozsah 55,8-60,0")],
        navrh={"prvky": prvky,
               "skala": {"rezy": [14, 16, 20, 24, 32],
                         "vyjimky": {"13": "klavesnicovy blok ma vlastni soustavu"}}},
    )
    bez = _make(
        [_w("drobne.1", 36, 120, 200, 17, text="rozsah 55,8-60,0")],
        navrh={"prvky": prvky, "skala": SKALA},
    )
    assert not _zpravy(s_vyjimkou, ZNACKA_R148)
    assert _zpravy(s_vyjimkou, ZNACKA_R148_ODCHYLKA)
    assert _zpravy(bez, ZNACKA_R148)


def test_r148_hlasi_po_rezech_ne_po_prvcich():
    """Deset prvku v jednom rezu = jedna veta s poctem, ne deset vet."""
    widgets = [_w(f"popis.{i}", 36, 100 + 30 * i, 200, 19, text=f"radek {i}")
               for i in range(10)]
    prvky = {f"popis.{i}": {"font_size": 18} for i in range(10)}
    n = _zpravy(_make(widgets, navrh={"prvky": prvky, "skala": SKALA}), ZNACKA_R148)
    assert len(n) == 1
    assert "na 10 prvcich" in n[0].message


def test_r148_bez_skaly_rekne_ze_nemerilo():
    data = _make(
        [_w("popis.1", 36, 120, 200, 19, text="TEPLOTA CPU")],
        navrh={"prvky": {"popis.1": {"font_size": 18}}},
    )
    assert _zpravy(data, ZNACKA_R148_NEMERENO)
    assert not _zpravy(data, ZNACKA_R148)


def test_r148_bez_merenych_rezu_o_nicem_nemluvi():
    """NEMERENO se hlasi jen tam, kde bylo CO merit."""
    data = _make([_w("popis.1", 36, 120, 200, 19, text="TEPLOTA CPU")],
                 navrh={"prvky": {"popis.1": {"role": "popisek"}}})
    assert not _zpravy(data, ZNACKA_R148_NEMERENO)


def test_r148_prazdny_text_se_nemeri():
    """Rez prazdne schranky nikdo nevidi - to je Rule 138, ne 148."""
    data = _make(
        [_w("popis.1", 36, 120, 200, 19, text="   ")],
        navrh={"prvky": {"popis.1": {"font_size": 18}}, "skala": SKALA},
    )
    assert not _zpravy(data, ZNACKA_R148)


def test_r148_fixtury_obou_trid():
    assert _fix_zpravy("tab5_skala_vady.json", ZNACKA_R148)
    assert not _fix_zpravy("tab5_skala_ciste.json", ZNACKA_R148)
    assert _fix_zpravy("tab5_skala_ciste.json", ZNACKA_R148_ODCHYLKA)


# --------------------------------------------------------------------------- #
# Rule 149 - uhlova velikost znaku
# --------------------------------------------------------------------------- #


def test_r149_meze_odpovidaji_fyzice_panelu():
    """Kontrolni prepocet: profil musi davat cisla tabulky 3.1 specifikace."""
    assert round(PROFILE_TAB5.minuty(PROFILE_TAB5.verzalka_pomer * 14), 2) == 6.47
    assert round(PROFILE_TAB5.minuty(PROFILE_TAB5.verzalka_pomer * 32), 2) == 14.78


def test_r149_pod_mezi_letmo_je_WARN():
    data = _make(
        [_w("drobne.1", 36, 120, 300, 12, text="vzorkuje po 2 s")],
        navrh={"prvky": {"drobne.1": {"font_size": 10}}},
    )
    n = _zpravy(data, ZNACKA_R149)
    assert len(n) == 1 and n[0].level == "WARN"
    assert "4.62'" in n[0].message


def test_r149_pod_mezi_tvaru_je_ERROR():
    data = _make(
        [_w("nano.1", 36, 120, 300, 7, text="D0 D1")],
        navrh={"prvky": {"nano.1": {"font_size": 5}}},
    )
    n = _zpravy(data, ZNACKA_R149)
    assert len(n) == 1 and n[0].level == "ERROR"


def test_r149_nejmensi_rez_kitu_mlci():
    """12 px klavesnice = 5,54' na 450 mm, tedy nad mezi. Zmereno, ne odhad."""
    data = _make(
        [_w("klavesa.1", 28, 500, 116, 18, text="q")],
        navrh={"prvky": {"klavesa.1": {"font_size": 12}}},
    )
    assert not _zpravy(data, ZNACKA_R149)


def test_r149_hranice_meze_letmo():
    """Rez, jehoz verzalka da presne 5', jeste mlci; o desetinu min uz ne."""
    hranice = R149_MEZ_LETMO
    rez = 10.83   # 0,700*10,83 px = 5,00' na 450 mm pri 294 PPI
    minut = PROFILE_TAB5.minuty(PROFILE_TAB5.verzalka_pomer * rez)
    assert minut >= hranice
    tesne = _make([_w("a.1", 36, 120, 300, 12, text="x")],
                  navrh={"prvky": {"a.1": {"font_size": rez}}})
    pod = _make([_w("a.1", 36, 120, 300, 12, text="x")],
                navrh={"prvky": {"a.1": {"font_size": rez - 0.2}}})
    assert not _zpravy(tesne, ZNACKA_R149)
    assert _zpravy(pod, ZNACKA_R149)


def test_r149_hlaska_nese_ISO_ale_nesoudi_podle_ni():
    """ISO je v hlasce jako meritko; kdyby byla mezi, hlasil by kazdy text."""
    data = _make(
        [_w("hodnota.1", 36, 120, 300, 24, text="49,4 °C")],
        navrh={"prvky": {"hodnota.1": {"font_size": 20}}},
    )
    assert not _zpravy(data, ZNACKA_R149)
    minut = PROFILE_TAB5.minuty(PROFILE_TAB5.verzalka_pomer * 20)
    assert minut < R149_MEZ_ISO        # bezna hodnota je na 58 % ISO
    assert minut >= R149_MEZ_LETMO     # a presto se cte


def test_r149_je_gatovana_profilem():
    """Tyz rez, dva panely: oled256 nema PPI ani vzdalenost, takze mlci."""
    widgets = [_w("nano.1", 36, 120, 200, 7, text="D0")]
    navrh = {"prvky": {"nano.1": {"font_size": 5}}}
    assert _zpravy(_make(widgets, navrh=navrh, device="tab5"), ZNACKA_R149)
    assert not _zpravy(
        _make(widgets, navrh=navrh, device="oled256"), ZNACKA_R149)


def test_r149_meze_jsou_serazene_a_zvenci():
    assert R149_MEZ_TVAR < R149_MEZ_LETMO < R149_MEZ_ISO


def test_r149_fixtury_obou_trid():
    n = _fix_zpravy("tab5_citelnost_vady.json", ZNACKA_R149)
    assert len(n) == 2
    assert {i.level for i in n} == {"WARN", "ERROR"}
    assert not _fix_zpravy("tab5_citelnost_ciste.json", ZNACKA_R149)


# --------------------------------------------------------------------------- #
# Rule 150 - barva mimo paletu
# --------------------------------------------------------------------------- #


def test_r150_barva_mimo_paletu_vystreli():
    data = _make(
        [_w("karta.1", 36, 120, 200, 19, text="FPS", fg="#8FA0A5", bg="#151E26")],
        navrh={"paleta": PALETA},
    )
    n = _zpravy(data, ZNACKA_R150)
    assert len(n) == 2
    assert any("#8fa0a5" in i.message for i in n)
    assert any("#151e26" in i.message for i in n)


def test_r150_barva_z_palety_mlci():
    data = _make(
        [_w("txt.1", 36, 120, 200, 19, text="FPS", fg="#E4DFCC", bg="#14170F")],
        navrh={"paleta": PALETA},
    )
    assert not _zpravy(data, ZNACKA_R150)


def test_r150_velikost_pismen_hexu_nerozhoduje():
    data = _make(
        [_w("txt.1", 36, 120, 200, 19, text="FPS", fg="#e4dfcc", bg="#14170f")],
        navrh={"paleta": PALETA},
    )
    assert not _zpravy(data, ZNACKA_R150)


def test_r150_hlasi_po_barvach_ne_po_prvcich():
    widgets = [_w(f"karta.{i}", 36, 100 + 30 * i, 200, 19, text=f"r{i}",
                  fg="#8FA0A5", bg="#14170F") for i in range(12)]
    n = _zpravy(_make(widgets, navrh={"paleta": PALETA}), ZNACKA_R150)
    assert len(n) == 1
    assert "na 12 prvcich" in n[0].message


def test_r150_vlastni_paleta_je_jedna_veta_s_duvodem():
    widgets = [_w(f"karta.{i}", 36, 100 + 30 * i, 200, 19, text=f"r{i}",
                  fg="#8FA0A5", bg="#151E26") for i in range(12)]
    data = _make(widgets, navrh={"paleta": PALETA,
                                 "paleta_vlastni": "list v negativu ma vlastni paletu"})
    assert not _zpravy(data, ZNACKA_R150)
    odch = _zpravy(data, ZNACKA_R150_ODCHYLKA)
    assert len(odch) == 1
    assert "list v negativu" in odch[0].message


def test_r150_oznaceni_bez_vety_pravidlo_NEVYPNE():
    data = _make(
        [_w("karta.1", 36, 120, 200, 19, text="FPS", fg="#8FA0A5", bg="#151E26")],
        navrh={"paleta": PALETA, "paleta_vlastni": "  "},
    )
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)
    assert _zpravy(data, ZNACKA_R150)


def test_r150_vlastni_paleta_BEZ_palety_je_rozbita_smlouva():
    """Vyjimka bez meze nic nevyjima - musi to byt slyset."""
    data = _make(
        [_w("karta.1", 36, 120, 200, 19, text="FPS", fg="#8FA0A5")],
        navrh={"paleta_vlastni": "list v negativu"},
    )
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)


def test_r150_bez_palety_NEOBVINUJE_ale_ANI_NEMLCI():
    """Datova zavora jako u Rule 136 - ale ticho o ni musi byt SLYSET.

    Dve veci naraz, protoze samostatne kazda lze:

    * cizi navrh se z NASI palety nesoudi (zadne `barva mimo paletu`),
    * a zaroven se nesmi tvarit, ze se zmerilo (`paleta navrhu nedodana`),
      protoze prvek NESE zmerenou barvu (`inkoust`).

    Do 9. 9. 2026 tenhle test zapisoval uplne ticho jako spravne. Kritik
    to zmeril v pisikovisti: jedna carka navic v `tokens.json` srazila
    tridu `paleta` z peti nalezu na nulu, pocet ERRORu se nezmenil a
    brana zustala zelena. Zelena brana nad nezmerenym listem tvrdi neco,
    co nikdo nemeril.
    """
    data = _make(
        [_w("karta.1", 36, 120, 200, 19, text="FPS", fg="#8FA0A5", bg="#151E26")],
        navrh={"prvky": {"karta.1": {"inkoust": "#8fa0a5"}}},
    )
    assert not _zpravy(data, ZNACKA_R150), "cizi navrh se z nasi palety soudil"
    assert _zpravy(data, ZNACKA_R150_NEMERENO), (
        "paleta nedosla a pravidlo 150 o tom NERUKLO ani slovo")


def test_r150_NEMERENO_mlci_nad_scenou_BEZ_zmerenych_barev():
    """Kontrolni skupina k zavore: cizi scena NEMERENO nedostane.

    Editor pousti validator nad scenami, ktere most kitu nikdy nevidel -
    ty klic `inkoust` nemaji. Kdyby zavora byla "prvek ma color_fg", byla
    by to jen jinak napsana podminka "vzdycky" a hlaska by vyskocila na
    kazde scene editoru. Presne proto se NEMERENO puvodne nehlasilo
    vubec; tenhle test drzi, ze uzsi zavora ten duvod uz nema.
    """
    data = _make(
        [_w("karta.1", 36, 120, 200, 19, text="FPS", fg="#8FA0A5", bg="#151E26")],
        navrh={"prvky": {"karta.1": {"rodic": "root"}}},
    )
    assert not _zpravy(data, ZNACKA_R150_NEMERENO)


def test_r150_S_PALETOU_uz_NEMERENO_nehlasi():
    """Pozitivni kontrola: kdyz paleta dojde, hlaska zmizi.

    Bez ni by "NEMERENO vystrelilo" mohlo znamenat, ze vystreli vzdycky.
    """
    data = _make(
        [_w("karta.1", 36, 120, 200, 19, text="FPS", fg=PALETA[0], bg=PALETA[1])],
        navrh={"prvky": {"karta.1": {"inkoust": PALETA[0].lower()}},
               "paleta": PALETA},
    )
    assert not _zpravy(data, ZNACKA_R150_NEMERENO)
    assert not _zpravy(data, ZNACKA_R150)


def test_r151_NEMERENO_i_bez_deklarovane_vsazky():
    """Regrese B3: `DnesSystemMonitor` vlastni vsazku NEMA.

    Stara zavora hlasila NEMERENO jen tehdy, kdyz nejaky blok DEKLAROVAL
    vlastni vsazku - to jsou dva klavesnicove listy. Vsechny ctyri zive
    nalezy pravidla 151 lezi ale na `DnesSystemMonitor`, ktery zadnou
    nema: kdyby ze scen zmizel blok `soustava`, ctyri nalezy by zmizely
    BEZE SLOVA. Zavora je proto `orez` (klic mostu) NEBO `vsazka`.
    """
    data = _make(
        [_w("fps.1", 35, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"fps.1": {"orez": OREZ_ZMERENY}}},
    )
    assert _zpravy(data, ZNACKA_R151_NEMERENO)


def test_r151_NEMERENO_mlci_nad_scenou_BEZ_klice_mostu():
    """Kontrolni skupina: cizi scena hlasku nedostane."""
    data = _make(
        [_w("fps.1", 35, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"fps.1": {"rodic": "root"}}},
    )
    assert not _zpravy(data, ZNACKA_R151_NEMERENO)


def test_r151_SE_SOUSTAVOU_uz_NEMERENO_nehlasi():
    """Pozitivni kontrola teze cesty."""
    data = _make(
        [_w("fps.1", 36, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"fps.1": {"orez": OREZ_ZMERENY}},
               "soustava": SOUSTAVA},
    )
    assert not _zpravy(data, ZNACKA_R151_NEMERENO)


def test_r150_neviditelny_prvek_se_nemeri():
    w = _w("karta.1", 36, 120, 200, 19, text="FPS", fg="#8FA0A5", bg="#151E26")
    w["visible"] = False
    assert not _zpravy(_make([w], navrh={"paleta": PALETA}), ZNACKA_R150)


def test_r150_barva_pisma_prvku_bez_pisma_se_nemeri():
    """Prvek bez textu barvu pisma jen DEDI; nikdo ji nevidi."""
    w = _w("panel.1", 36, 120, 200, 19, text="", t="panel",
           fg="#8FA0A5", bg="#14170F")
    n = _zpravy(_make([w], navrh={"paleta": PALETA}), ZNACKA_R150)
    assert not n


def test_r150_fixtury_obou_trid():
    assert _fix_zpravy("tab5_paleta_vady.json", ZNACKA_R150)
    assert not _fix_zpravy("tab5_paleta_ciste.json", ZNACKA_R150)
    assert _fix_zpravy("tab5_paleta_vlastni.json", ZNACKA_R150_ODCHYLKA)
    assert not _fix_zpravy("tab5_paleta_vlastni.json", ZNACKA_R150)


# --------------------------------------------------------------------------- #
# Rule 151 - text nalepeny na ram
# --------------------------------------------------------------------------- #


def test_r151_text_v_pasmu_lepeni_vystreli():
    data = _make(
        [_w("karta_l.1", 35, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"karta_l.1": {}}, "soustava": SOUSTAVA},
    )
    n = _zpravy(data, ZNACKA_R151)
    assert len(n) == 1
    assert "x=35" in n[0].message and "x=36" in n[0].message


def test_r151_text_na_soustave_mlci():
    data = _make(
        [_w("txt.1", 36, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"txt.1": {}}, "soustava": SOUSTAVA},
    )
    assert not _zpravy(data, ZNACKA_R151)


def test_r151_hranice_na_pixel():
    """20 mlci (to je hrana pole), 21 a 35 hlasi, 36 mlci."""
    for x, ceka in ((19, 0), (20, 0), (21, 1), (35, 1), (36, 0), (37, 0)):
        data = _make(
            [_w("txt.1", x, 120, 200, 19, text="FPS")],
            navrh={"prvky": {"txt.1": {}}, "soustava": SOUSTAVA},
        )
        assert len(_zpravy(data, ZNACKA_R151)) == ceka, x


def test_r151_vlastni_vsazka_bloku_PARAMETRIZUJE_a_nevypina():
    """Klavesa na 28 s vlastni vsazkou 8 mlci; na 24 hlasi porad."""
    ok = _make(
        [_w("klv.1", 28, 500, 116, 18, text="q")],
        navrh={"prvky": {"klv.1": {"vsazka": 8}}, "soustava": SOUSTAVA},
    )
    spatne = _make(
        [_w("klv.1", 24, 500, 116, 18, text="q")],
        navrh={"prvky": {"klv.1": {"vsazka": 8}}, "soustava": SOUSTAVA},
    )
    assert not _zpravy(ok, ZNACKA_R151)
    n = _zpravy(spatne, ZNACKA_R151)
    assert len(n) == 1
    assert "blok ma vlastni vsazku" in n[0].message


def test_r151_bez_vlastni_vsazky_by_klavesnice_hlasila():
    """Kontrolni skupina: tataz klavesa BEZ deklarace je nalez."""
    data = _make(
        [_w("klv.1", 28, 500, 116, 18, text="q")],
        navrh={"prvky": {"klv.1": {}}, "soustava": SOUSTAVA},
    )
    assert _zpravy(data, ZNACKA_R151)


def test_r151_prazdny_text_se_nemeri():
    data = _make(
        [_w("txt.1", 30, 120, 200, 19, text="  ")],
        navrh={"prvky": {"txt.1": {}}, "soustava": SOUSTAVA},
    )
    assert not _zpravy(data, ZNACKA_R151)


def test_r151_bez_soustavy_mlci():
    data = _make([_w("txt.1", 35, 120, 200, 19, text="FPS")],
                 navrh={"prvky": {"txt.1": {}}})
    assert not _zpravy(data, ZNACKA_R151)


def test_r151_deklarovana_vsazka_bez_soustavy_rekne_ze_nemerila():
    """Pulka smlouvy je rozbita smlouva, ne mezera v mereni."""
    data = _make([_w("klv.1", 28, 500, 116, 18, text="q")],
                 navrh={"prvky": {"klv.1": {"vsazka": 8}}})
    assert _zpravy(data, ZNACKA_R151_NEMERENO)


def test_r151_vadna_soustava_se_hlasi():
    data = _make(
        [_w("txt.1", 35, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"txt.1": {}}, "soustava": {"pole_x": 20, "vsazka": 0}},
    )
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)
    assert not _zpravy(data, ZNACKA_R151)


def test_r151_fixtury_obou_trid():
    n = _fix_zpravy("tab5_odsazeni_vady.json", ZNACKA_R151)
    assert len(n) == 2                     # karta_l a karta_r, obe na x=35
    assert all("x=35" in i.message for i in n)
    assert not _fix_zpravy("tab5_odsazeni_ciste.json", ZNACKA_R151)


def test_r151_meri_neco_jineho_nez_Rule_134():
    """Doklad, ze se pravidla neprekryvaji: 15 px je pro R134 daleko."""
    data = _make(
        [_w("pole.1", 20, 80, 400, 19, text="Systemovy monitor"),
         _w("karta_l.2", 35, 120, 200, 19, text="FPS")],
        navrh={"prvky": {"karta_l.2": {}}, "soustava": SOUSTAVA},
    )
    assert _zpravy(data, ZNACKA_R151)
    assert not [i for i in _issues(data) if "near-miss alignment" in i.message]


# --------------------------------------------------------------------------- #
# Rule 17 - druha mez WCAG a vyjimka neaktivniho ovladace
# --------------------------------------------------------------------------- #


def _kontrast(rez, fg_bg, *, tucne=None, enabled=None, device="tab5"):
    fg, bg = fg_bg
    prvek = {"font_size": rez, "inkoust": fg, "podklad": bg}
    if tucne is not None:
        prvek["tucne"] = tucne
    if enabled is not None:
        prvek["enabled"] = enabled
    return _make(
        [_w("txt.1", 36, 120, 400, 29, text="TEPLOTA RADIA", fg=fg, bg=bg)],
        navrh={"prvky": {"txt.1": prvek}}, device=device,
    )


def _nizky(data):
    return [i for i in _issues(data) if "low contrast" in i.message]


def test_r17_velky_text_ma_volnejsi_mez():
    """3,88:1 pri 24 px projde; tataz dvojice pri 20 px ne."""
    assert not _nizky(_kontrast(24, OBRYS_NA_PODKLADU))
    assert _nizky(_kontrast(20, OBRYS_NA_PODKLADU))


def test_r17_hranice_velkeho_textu_na_pixel():
    for rez, propadne in ((23.9, True), (WCAG_VELKY_PX, False)):
        assert bool(_nizky(_kontrast(rez, OBRYS_NA_PODKLADU))) is propadne, rez


def test_r17_tucny_text_ma_volnejsi_mez_uz_od_19px():
    assert not _nizky(_kontrast(WCAG_TUCNE_PX, OBRYS_NA_PODKLADU, tucne=True))
    assert _nizky(_kontrast(WCAG_TUCNE_PX, OBRYS_NA_PODKLADU, tucne=False))
    assert _nizky(_kontrast(18.9, OBRYS_NA_PODKLADU, tucne=True))


def test_r17_volnejsi_mez_neni_zadna_mez():
    """2,74:1 propadne i jako velky text - jinak by rozsireni bylo dira."""
    n = _nizky(_kontrast(32, INKUTLUM_NA_PODKLADU))
    assert len(n) == 1
    assert "3.0:1" in n[0].message


def test_r17_bez_rezu_plati_PRISNEJSI_mez():
    """Nezmerene se nesmi vyplatit."""
    data = _make(
        [_w("txt.1", 36, 120, 400, 29, text="TEPLOTA RADIA",
            fg=OBRYS_NA_PODKLADU[0], bg=OBRYS_NA_PODKLADU[1])],
        navrh={"prvky": {"txt.1": {}}},
    )
    assert _nizky(data)


def test_r17_MUTACE_bez_druhe_meze_padne_falesny_poplach(monkeypatch):
    """Bez rozsireni dostane velky titulek 3,88:1 poplach. Kdyby tenhle
    test nebyl, nikdo by nezmeril, co druha mez opravdu udelala."""
    stary = dataclasses.replace(PROFILE_TAB5, min_contrast_velky=0.0)
    monkeypatch.setitem(PROFILES, "tab5", stary)
    assert _nizky(_kontrast(24, OBRYS_NA_PODKLADU))
    assert _nizky(_kontrast(WCAG_TUCNE_PX, OBRYS_NA_PODKLADU, tucne=True))


def test_r17_neaktivni_ovladac_je_vyjmuty_ALE_rekne_se_to():
    data = _kontrast(16, ZASEDLE_PRIPOJIT, enabled=False)
    assert not _nizky(data)
    n = _zpravy(data, ZNACKA_R17_NEAKTIVNI)
    assert len(n) == 1
    assert "1.4.3" in n[0].message and "2.23:1" in n[0].message


def test_r17_vyjimka_ktera_nic_nevyjmula_se_nehlasi():
    """Zasedly ovladac s dobrym kontrastem je ticho, ne sum."""
    data = _kontrast(16, ("#E4DFCC", "#14170F"), enabled=False)
    assert not _zpravy(data, ZNACKA_R17_NEAKTIVNI)
    assert not _nizky(data)


def test_r17_cinny_ovladac_vyjimku_NEDOSTANE():
    data = _kontrast(16, ZASEDLE_PRIPOJIT, enabled=True)
    assert _nizky(data)
    assert not _zpravy(data, ZNACKA_R17_NEAKTIVNI)


def test_r17_meri_VIDENOU_dvojici_ne_napsanou():
    """Napsany inkoust #12150E na akcentu ma 14,07:1 a stara Rule 17 mlcela;
    videna dvojice ma 2,23:1."""
    napsana = _make(
        [_w("btn.1", 300, 300, 240, 81, text="Pripojit", t="button",
            fg="#12150E", bg="#E9A63C")],
        navrh={"prvky": {"btn.1": {"font_size": 16}}},
    )
    videna = _make(
        [_w("btn.1", 300, 300, 240, 81, text="Pripojit", t="button",
            fg="#12150E", bg="#E9A63C")],
        navrh={"prvky": {"btn.1": {"font_size": 16,
                                   "inkoust": ZASEDLE_PRIPOJIT[0],
                                   "podklad": ZASEDLE_PRIPOJIT[1]}}},
    )
    assert not _nizky(napsana)
    assert _nizky(videna)


def test_r17_vadna_videna_barva_se_hlasi():
    data = _make(
        [_w("txt.1", 36, 120, 400, 29, text="X")],
        navrh={"prvky": {"txt.1": {"inkoust": "nic"}}},
    )
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)


def test_r17_druha_mez_je_gatovana_profilem():
    """oled256 meri rozdil jasu, ne pomer - druhou mez WCAG nema."""
    assert PROFILE_OLED256.min_contrast_velky == 0.0
    assert PROFILE_TAB5.min_contrast_velky == 3.0


def test_r17_fixtury_obou_trid():
    vady = _fix("tab5_kontrast_vady.json")
    assert [i for i in vady if ZNACKA_R17_NEAKTIVNI in i.message]
    assert [i for i in vady if "low contrast" in i.message]
    ciste = _fix("tab5_kontrast_ciste.json")
    assert not [i for i in ciste if "low contrast" in i.message]
    assert not [i for i in ciste if ZNACKA_R17_NEAKTIVNI in i.message]


# --------------------------------------------------------------------------- #
# Smlouva o atributech: `tucne` a `vsazka`
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("hodnota", ["true", 1, "ano", None.__class__])
def test_tucne_musi_byt_pravdivostni_hodnota(hodnota):
    """Retezec 'false' je v Pythonu pravdivy - tise by mez posunul o 5 px."""
    data = _make([_w("txt.1", 36, 120, 200, 19)],
                 navrh={"prvky": {"txt.1": {"tucne": str(hodnota)}}})
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)


@pytest.mark.parametrize("hodnota", [-1, 0, "8", True])
def test_vsazka_musi_byt_kladne_cislo(hodnota):
    data = _make([_w("txt.1", 36, 120, 200, 19)],
                 navrh={"prvky": {"txt.1": {"vsazka": hodnota}}})
    assert _zpravy(data, ZNACKA_NAVRH_VADNY)


def test_vsazka_smi_chybet():
    """Blok bez vlastni vsazky je bezny stav, ne vada."""
    data = _make([_w("txt.1", 36, 120, 200, 19)],
                 navrh={"prvky": {"txt.1": {"role": "popisek"}},
                        "soustava": SOUSTAVA})
    assert not _zpravy(data, ZNACKA_NAVRH_VADNY)


def test_fixtury_projdou_schematem():
    """Nosic musi byt LEGALNI: kdyby scena takovy blok nesmela nest,
    testy vyse by merily neco, co brana v ostrem behu odmitne."""
    for jmeno in sorted(FIXTURY.glob("tab5_*.json")):
        nalezy = validate_file(jmeno, warnings_as_errors=False)
        assert not [i for i in nalezy if "schema" in i.message.lower()], jmeno.name


def test_fixtury_nesou_skutecna_cisla_ze_sceny():
    """Fixtury Rule 150 a 151 jsou ze SKUTECNE sceny DnesSystemMonitor:
    popisky karet na x=35 a starsi generace palety."""
    d = json.loads((FIXTURY / "tab5_odsazeni_vady.json").read_text(encoding="utf-8"))
    xs = {w["x"] for w in d["scenes"]["main"]["widgets"]}
    assert xs == {35}
    d2 = json.loads((FIXTURY / "tab5_paleta_vady.json").read_text(encoding="utf-8"))
    bg = {w["color_bg"] for w in d2["scenes"]["main"]["widgets"]}
    assert "#151e26" in bg
