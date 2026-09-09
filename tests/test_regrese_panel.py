"""Regresni fixtury z fotoprotokolu skutecneho panelu Tab5 (2026-09-08).

Kazda fixtura je pojmenovana po OBRAZOVCE, ne po pravidle. Duvod je vecny:
jedna obrazovka mela vic vad naraz (Domov ma ctyri), opravuje se OBRAZOVKA
a clovek, ktery ji opravuje, potrebuje videt vsechny jeji nalezy pohromade.
Pojmenovani po pravidle by tutez obrazovku roztrhalo do ctyr souboru a
zadny z nich by neodpovedel na otazku "je uz Domov v poradku?".

Zdroj vad: `scratchpad/screeny/00_prvni_pruchod.md` + snimky `*.png`.
Zdroj CISEL: skutecne sceny kitu (`_scena_*.json`, 2026-09-09) - souradnice
dlazdic, stitku, karet, patek i pasu jsou opsane z mereni, ne vymyslene.
Kde se fixtura od artboardu lisi, lisi se o JEDNO cislo a je to napsane
v klici ``_puvod`` uvnitr fixtury (napr. dlazdice RF sondy: y 523 -> 548,
protoze artboard ma 13 px vzduchu nad patkou, kdezto panel ma mrizku o radu
vyssi).

CO TYHLE TESTY DELAJI A CO NE

* **Delaji:** pribijeji, ze na KAZDE z techto vad brana vystreli - a ze na
  teze obrazovce po oprave MLCI. Bez negativni tridy by test prosel i pro
  branu, ktera hlasi vzdycky.
* **Nedelaji:** nemeri artboardy kitu. Ty vady na artboardech vetsinou
  NEJSOU (artboard je navrh, panel je vysledek) - proto jsou fixtury zvlast.

CTYRI VADY Z FOTOPROTOKOLU, KTERE ZADNE MERIDLO NECHYTA, a je poctive to
rict nahlas misto abychom je tise vynechali (kazda ma test na TICHO, aby se
ticho nedalo zamenit za "zmereno a v poradku"):

1. ``(SDK CAS NEDAVA)`` jako hlavicka sloupce v Souborech. Je to omluva
   misto jmena sloupce - OBSAHOVA vada. Z navrhu se meri tvar a poloha,
   ne to, jestli veta dava smysl na miste, kde stoji.
2. Pravitko ``KDE JE VOLNO 1..13`` nad nicim (Network Tools). Kdyby brana
   umela "popisek stupnice bez stupnice", byla by to kontrola vazby dvou
   prvku, kterou dnes zadny atribut nenese.
3. Patka Terminalu ``UART1 G53/G54 115 200`` je VECNE spatne (UART1 je
   RS485, G53/G54 je Grove Port A na I2C). Zadne meridlo nad navrhem
   nezjisti, ze cislo portu nesedi se schematem desky - to je vec
   dokumentace hardwaru, ne rozvrzeni. Ta patka proto stoji i v CISTE
   tride Terminalu: kdyby se "opravila", test na ticho by uz nemeril
   mlceni brany, ale nepritomnost vety.
4. "Velke prazdno mezi radkem zarizeni a deskriptorem" (USB Inspector).
   Zmereno 26 px mezi ``v.29`` a ``zar.30``; "moc vzduchu" nema mez, kterou
   by slo odvodit z panelu - rozestup radku je vec SOUSTAVY (``tokens.json:
   layout``), ne vada rozvrzeni.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.validate_design import (
    PROFILE_OLED256,
    PROFILE_TAB5,
    R136_PRAH_PX,
    ZNACKA_R136_PAS,
    ZNACKA_R138,
    ZNACKA_R139,
    ZNACKA_R140,
    ZNACKA_R142,
    ZNACKA_R142_NEMERENO,
    ZNACKA_R143,
    ZNACKA_R144,
    validate_data,
    validate_file,
)

# Fixtury bydli v adresari POJMENOVANEM PODLE PRUCHODU PANELEM. Neni to
# uklid: az nekdo panel projde znovu, dostane vlastni adresar a obe sady
# pobezi vedle sebe. Kdyby lezely nasypane v `fixtures/`, druhy pruchod
# by musel ty prvni bud premazat, nebo si vymyslet priponu - a "vada
# z panelu" by prestala mit datum, ke kteremu se da vratit.
FIXTURY = pathlib.Path(__file__).parent / "fixtures" / "panel_2026-09-08"

# Deset obrazovek, ke kazde dvojice (vadna / cista). Seznam je zaroven
# strojovou kontrolou uplnosti - viz `test_kazda_obrazovka_ma_obe_tridy`.
OBRAZOVKY = [
    "panel_domov",
    "panel_system_monitor",
    "panel_hex",
    "panel_logic_analyzer",
    "panel_network_tools",
    "panel_diagnostics",
    "panel_files",
    "panel_settings",
    "panel_terminal",
    "panel_usb_inspector",
]

# Rule 26 a Rule 135 znacku nemaji (jsou to anglicka pravidla puvodniho
# ESPOSu); jejich hlasky se poznavaji timhle kusem.
KUS_R26 = "unsupported chars in text"
KUS_R135 = "touch target"


def _cesta(jmeno: str, trida: str) -> pathlib.Path:
    return FIXTURY / f"{jmeno}_{trida}.json"


def _zpravy(jmeno: str, trida: str) -> list[str]:
    return [
        i.message
        for i in validate_file(_cesta(jmeno, trida), warnings_as_errors=False)
    ]


def _chyby(jmeno: str, trida: str) -> list[str]:
    return [
        i.message
        for i in validate_file(_cesta(jmeno, trida), warnings_as_errors=False)
        if i.level == "ERROR"
    ]


def _obsahuji(zpravy: list[str], kus: str) -> list[str]:
    return [m for m in zpravy if kus in m]


def _scena(jmeno: str, trida: str) -> dict:
    return json.loads(_cesta(jmeno, trida).read_text(encoding="utf-8"))


def _zpravy_dat(data: dict, **kw) -> list[str]:
    return [
        i.message
        for i in validate_data(data, file_label="test", warnings_as_errors=False, **kw)
    ]


# --------------------------------------------------------------------------- #
# Nosic: fixtury musi byt legalni sceny, ne jen slepenec klicu
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("jmeno", OBRAZOVKY)
@pytest.mark.parametrize("trida", ["vady", "ciste"])
def test_kazda_obrazovka_ma_obe_tridy(jmeno: str, trida: str):
    """Dvojice musi existovat OBE. Fixtura bez negativni tridy netestuje nic:
    prosla by i brane, ktera hlasi na kazde scene."""
    assert _cesta(jmeno, trida).is_file()


def test_zadna_fixtura_nelezi_v_adresari_bez_testu():
    """Uplnost OBEMA smery. Bez teto kontroly by fixtura, kterou nekdo
    prida a zapomene zapsat do `OBRAZOVKY`, lezela v adresari a nikdo by ji
    nepustil - a vypadalo by to jako pokryti, ktere neni."""
    na_disku = {p.name for p in FIXTURY.glob("panel_*.json")}
    ceka = {f"{j}_{t}.json" for j in OBRAZOVKY for t in ("vady", "ciste")}
    assert na_disku == ceka, na_disku ^ ceka


@pytest.mark.parametrize("jmeno", OBRAZOVKY)
@pytest.mark.parametrize("trida", ["vady", "ciste"])
def test_fixtura_nese_svuj_puvod(jmeno: str, trida: str):
    """`_puvod` rika, ktera cisla jsou z artboardu a ktera z panelu.

    Bez toho by za rok nikdo nevedel, jestli je fixtura mereni, nebo vymysl -
    a prvni clovek, kterému by prekazela, by ji "opravil" na to, co prochazi.
    """
    doc = _scena(jmeno, trida)
    assert doc["_puvod"].strip(), f"{jmeno}_{trida}: prazdny puvod"
    assert doc["device"] == "tab5"


@pytest.mark.parametrize("jmeno", OBRAZOVKY)
def test_vadna_trida_vystreli_a_cista_nema_ani_jednu_chybu(jmeno: str):
    """Pozitivni i negativni trida naraz, pres `validate_file` (tedy vcetne
    POVINNEHO JSON schematu - jinak by se neoverilo, ze scena takovy blok
    vubec smi nest)."""
    assert _chyby(jmeno, "vady"), f"{jmeno}: vadna fixtura nevystrelila"
    assert _chyby(jmeno, "ciste") == [], f"{jmeno}: cista fixtura hlasi chybu"


# --------------------------------------------------------------------------- #
# DOMOV: dlazdice RF sondy oriznuta patkou, pomlcka misto hodnoty,
#        useknuty stitek FIRMWARE, mrizka 2x5 na 11 appek
# --------------------------------------------------------------------------- #


def test_domov_dlazdice_RF_sondy_je_oriznuta_patkou():
    """R136, pas `razitko`. Spodni hrana dlazdice na snimku CHYBI."""
    z = _obsahuji(_zpravy("panel_domov", "vady"), ZNACKA_R136_PAS)
    assert [m for m in z if "dlazdice.77" in m and "o 12 px" in m], z


def test_domov_hodnota_dlazdice_sedi_na_care_patky():
    """Druhy nalez R136 na TEZE obrazovce, ale na JINEM prvku.

    Fotoprotokol: "hodnota '—' sedi na care patky (y~604)". Je to druha
    obet teze priciny (mrizka o radu vyssi), ne druhy nalez teze obeti -
    proto se hlasi zvlast a proto se tu meri obe.
    """
    z = _obsahuji(_zpravy("panel_domov", "vady"), ZNACKA_R136_PAS)
    assert [m for m in z if "txt_zivy.80" in m and "o 6 px" in m], z


def test_domov_pomlcka_misto_hodnoty_dlazdice():
    """R139, prvni tvar: cely text je pomlcka."""
    z = _obsahuji(_zpravy("panel_domov", "vady"), ZNACKA_R139)
    assert [m for m in z if "txt_zivy.80" in m], z


def test_domov_stitek_FIRMWARE_je_useknuty():
    """R144: obsah 212 px, videt 149 px - "V0.4-71-gee91351-dirty ·"."""
    z = _obsahuji(_zpravy("panel_domov", "vady"), ZNACKA_R144)
    assert [m for m in z if "v.21" in m and "212" in m], z


def test_domov_mrizka_2x5_nepojme_jedenact_appek():
    """R140: kapacita 10, appek 11.

    Tohle je jediny nalez, ktery MUSI byt synteticky: artboard ma mrizku
    3x4 (kapacita 12) a tuhle vadu nema. Na panelu je mrizka 2x5 a
    jedenacta dlazdice se ztraci MIMO scenu - tam, kde ji zadne meridlo
    nad souradnicemi widgetu neuvidi. Proto je kapacita jedina vec, kterou
    lze zmerit driv, nez se to stane.
    """
    z = _obsahuji(_zpravy("panel_domov", "vady"), ZNACKA_R140)
    assert [m for m in z if "kapacitu 10" in m and "polozek je 11" in m], z


def test_domov_po_oprave_mlci_vsechna_ctyri_pravidla():
    z = _zpravy("panel_domov", "ciste")
    for znacka in (ZNACKA_R136_PAS, ZNACKA_R139, ZNACKA_R140, ZNACKA_R144):
        assert _obsahuji(z, znacka) == [], znacka


def test_domov_hranice_patky_na_pixel():
    """Prah R136 je 1 px a je to POLOOTEVRENY interval: dotek neni zasah.

    Dlazdice, ktera konci PRESNE na hornim okraji pasu, projde; o pixel niz
    uz ne. Bez teto hranice by se prah dal libovolne posunout a nikdo by
    nezmeril, kterym smerem.
    """
    doc = _scena("panel_domov", "ciste")
    sc = doc["scenes"]["main"]
    pas_y = sc["navrh"]["pasy"]["razitko"][1]
    dlazdice = next(w for w in sc["widgets"] if w["_widget_id"] == "dlazdice.77")

    dlazdice["y"] = pas_y - dlazdice["height"]  # konci presne na hrane
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R136_PAS) == []

    dlazdice["y"] = pas_y - dlazdice["height"] + R136_PRAH_PX  # o prah niz
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R136_PAS)


# --------------------------------------------------------------------------- #
# SYSTEM MONITOR: prazdny smalt TEPLOTA RADIA, veta se jmenem typu,
#                 zalozky 150x48
# --------------------------------------------------------------------------- #


def test_system_monitor_TEPLOTA_RADIA_je_prazdny_smalt():
    """R138: role slibuje hodnotu, plocha nenese nic - ani uvnitr sebe."""
    z = _obsahuji(_zpravy("panel_system_monitor", "vady"), ZNACKA_R138)
    assert [m for m in z if "karta_v.54" in m], z


def test_system_monitor_veta_nese_ISystemMetrics_radioTemp():
    """R142: "ISystemMetrics::radioTemp nedostupne" - adresa v kodu misto
    odpovedi na otazku "co se stalo"."""
    z = _obsahuji(_zpravy("panel_system_monitor", "vady"), ZNACKA_R142)
    assert [m for m in z if "'::'" in m and "radioTemp" in m], z


def test_system_monitor_zalozky_150x48_jsou_pod_podlahou():
    """Rule 135: 48 px = 4,1 mm na 294 PPI. Podlaha je 58 px (5,0 mm)."""
    z = _obsahuji(_zpravy("panel_system_monitor", "vady"), KUS_R135)
    assert len([m for m in z if "150x48" in m]) == 2, z


def test_system_monitor_po_oprave_mlci():
    z = _zpravy("panel_system_monitor", "ciste")
    for kus in (ZNACKA_R138, ZNACKA_R142, KUS_R135):
        assert _obsahuji(z, kus) == [], kus


def test_zalozky_na_hranici_podlahy_meni_ZAVAZNOST_ne_ticho():
    """Dve meze, dve zavaznosti - a hranice mezi nimi se meri.

    58 px je podlaha (pod ni ERROR), 81 px navrhova mez (pod ni VAROVANI).
    Kdyby se merila jen jedna, zalozka 60x60 by bud propadla mlckym, nebo
    by mela tutez zavaznost jako 48x48 - a to je rozdil, ktery rozhoduje,
    co se opravuje dnes a co pri pristi revizi.
    """
    doc = _scena("panel_system_monitor", "ciste")
    zal = doc["scenes"]["main"]["widgets"][0]

    zal["width"] = zal["height"] = PROFILE_TAB5.min_touch_px - 1
    assert [
        i.level
        for i in validate_data(doc, file_label="t", warnings_as_errors=False)
        if KUS_R135 in i.message
    ] == ["ERROR"]

    zal["width"] = zal["height"] = PROFILE_TAB5.min_touch_px
    assert [
        i.level
        for i in validate_data(doc, file_label="t", warnings_as_errors=False)
        if KUS_R135 in i.message
    ] == ["WARN"]

    zal["width"] = zal["height"] = PROFILE_TAB5.warn_touch_px
    assert _obsahuji(_zpravy_dat(doc), KUS_R135) == []


# --------------------------------------------------------------------------- #
# HEX VIEWER: patka se tremi sloty bez hodnoty, microSD "nedostupne"
# --------------------------------------------------------------------------- #


def test_hex_patka_ma_tri_sloty_bez_hodnoty():
    """R139, treti tvar: "SOUBOR — OKNO — ZOBRAZENO —" v JEDNOM prvku.

    Pravidlo do 2026-09-09 merilo jen CELY text, takze generator, ktery
    nesazi kazdou hodnotu jako vlastni prvek, tri prazdne sloty protahl.
    """
    z = _obsahuji(_zpravy("panel_hex", "vady"), ZNACKA_R139)
    assert [m for m in z if "3 slotu" in m and "SOUBOR, OKNO, ZOBRAZENO" in m], z


def test_hex_o_karte_mluvi_slovem_mimo_slovnik():
    """R143: "nedostupne" neni zadny ze ctyr stavu microSD.

    Diagnostics o teze karte rika "vlozena, nepripojena" - ctenar si z toho
    jeden obraz sveta nesestavi.
    """
    z = _obsahuji(_zpravy("panel_hex", "vady"), ZNACKA_R143)
    assert [m for m in z if "microSD" in m and "nedostupné" in m], z


def test_hex_po_oprave_mlci():
    z = _zpravy("panel_hex", "ciste")
    for znacka in (ZNACKA_R139, ZNACKA_R143):
        assert _obsahuji(z, znacka) == [], znacka


def test_jeden_osamely_slot_s_pomlckou_PROJDE_a_je_to_vedome():
    """Hranice tretiho tvaru R139 je uzka schvalne a ma dolozitelnou cenu.

    Hlasi se az DVE po sobe jdouci skupiny "slovo pomlcka", protoze jedna
    jedina se od spravne hodnoty s oddelovacem nerozezna: "vlozena -
    nepripojena" ma presne tentyz tvar a je to hodnota v poradku.

    Dusledek pro fotoprotokol: kdyby generator sazel Logic Analyzer jako
    JEDEN prvek "SPOUST —", brana by mlcela. Prave proto je v tamni fixture
    popisek a hodnota jako DVA prvky - tak, jak je sazi generator kitu.
    """
    doc = _scena("panel_hex", "vady")
    patka = doc["scenes"]["main"]["widgets"][1]

    patka["text"] = "SOUBOR — OKNO —"
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R139), "dva sloty hlasit MUSI"

    patka["text"] = "SPOUŠŤ —"
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R139) == []

    # A pozitivni kontrola te meze z druhe strany: spravna hodnota, ktera
    # ma tentyz tvar, mlci taky - to je duvod, proc mez existuje.
    patka["text"] = "vložena — nepřipojena"
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R139) == []


# --------------------------------------------------------------------------- #
# LOGIC ANALYZER: "SPOUST —" a patka "—"
# --------------------------------------------------------------------------- #


def test_logic_analyzer_dve_pomlcky_dva_nalezy():
    """Pet forem nedostupnosti (C4) se ma sejit v jednu VETU, ne v pomlcku."""
    z = _obsahuji(_zpravy("panel_logic_analyzer", "vady"), ZNACKA_R139)
    assert len(z) == 2, z
    assert [m for m in z if "txt.31" in m], z
    assert [m for m in z if "txt.61" in m], z


def test_logic_analyzer_po_oprave_mlci():
    assert _obsahuji(_zpravy("panel_logic_analyzer", "ciste"), ZNACKA_R139) == []


# --------------------------------------------------------------------------- #
# NETWORK TOOLS: Skenovat 166x66, dve vety F4, prazdna patka SITI
# --------------------------------------------------------------------------- #


def test_network_tools_Skenovat_166x66_je_pod_navrhovou_mezi():
    """Rule 135, ale VAROVANI, ne chyba: 66 px je nad podlahou 58 a pod
    navrhovou mezi 81. Zavaznost je tu sdeleni, ne formalita."""
    iss = [
        i
        for i in validate_file(_cesta("panel_network_tools", "vady"),
                               warnings_as_errors=False)
        if KUS_R135 in i.message
    ]
    assert len(iss) == 1 and iss[0].level == "WARN", [i.message for i in iss]
    assert "166x66" in iss[0].message


def test_network_tools_dve_ruzne_vety_F4():
    """Dva RUZNE tvary tehoz zakona - jmeno v kodu a strojovy clen.

    Text `pozn.118` je doslova ze sceny `_scena_SvorkaNetwork.dc.json`; je
    to dnes jediny zivy nalez R142 na tom listu, takze fixtura hlida i to,
    ze se ten nalez neztrati.
    """
    z = _obsahuji(_zpravy("panel_network_tools", "vady"), ZNACKA_R142)
    assert [m for m in z if "'::'" in m and "startScan" in m], z
    assert [m for m in z if "rx_ctrl.noise_floor" in m], z


def test_network_tools_patka_SITI_je_prazdny_smalt():
    z = _obsahuji(_zpravy("panel_network_tools", "vady"), ZNACKA_R138)
    assert [m for m in z if "txt.126" in m], z


def test_network_tools_po_oprave_mlci():
    z = _zpravy("panel_network_tools", "ciste")
    for kus in (ZNACKA_R138, ZNACKA_R142, KUS_R135):
        assert _obsahuji(z, kus) == [], kus


# --------------------------------------------------------------------------- #
# DIAGNOSTICS: patka "ZDROJ IHwDiagnostics" v obou sazbach
# --------------------------------------------------------------------------- #


def test_diagnostics_patka_nese_jmeno_rozhrani():
    z = _obsahuji(_zpravy("panel_diagnostics", "vady"), ZNACKA_R142)
    assert [m for m in z if "'IHwDiagnostics'" in m], z


def test_diagnostics_tyz_stitek_VERZALKAMI_taky_vystreli():
    """Devaty tvar R142 (rozhodnuti koordinatora k bodu R3 kritika).

    Ve verzalkovem stitku hrby CamelCase videt nejsou, takze se jmeno
    porovnava se seznamem ze SDK. Do 2026-09-09 o "ZDROJ IHWDIAGNOSTICS"
    mlcely OBE brany - ESPOS i `brana_vety.py` v jadre.
    """
    z = _obsahuji(_zpravy("panel_diagnostics", "vady"), ZNACKA_R142)
    assert [m for m in z if "'IHWDIAGNOSTICS'" in m], z


def test_verzalkovy_tvar_bez_jmen_ze_SDK_se_NEMERI_a_rekne_se_to():
    """Kdyz most seznam nedodal, trida se nemeri - a ticho by se od
    zmereneho "v poradku" nedalo odlisit. Proto WARN, ne mlceni."""
    doc = _scena("panel_diagnostics", "vady")
    del doc["scenes"]["main"]["navrh"]["jmena_sdk"]
    z = _zpravy_dat(doc)
    assert _obsahuji(z, "'IHWDIAGNOSTICS'") == []
    assert _obsahuji(z, ZNACKA_R142_NEMERENO), z
    # Sesty tvar (CamelCase se dvema hrby) seznam nepotrebuje a merit
    # nepresta - jinak by tenhle test schvaloval ticho o obou.
    assert _obsahuji(z, "'IHwDiagnostics'"), z


def test_diagnostics_stav_karty_ZE_SLOVNIKU_mlci_v_obou_tridach():
    """Kontrolni skupina slovniku: "vlozena, nepripojena" je povoleny stav.

    Bez teto kontroly by testy prosly i slovniku, ktery krici na vsem -
    a takovy slovnik nemeri nic.
    """
    for trida in ("vady", "ciste"):
        assert _obsahuji(_zpravy("panel_diagnostics", trida), ZNACKA_R143) == []


def test_vety_F4_jsou_zakon_TabOSu_ne_vlastnost_skla():
    """Profilove gatovani ma obe strany: tatáz scena na oled256 MLCI.

    Bez toho by brana obvinila cizi navrh z porusovani zakona, ktery pro
    nej neplati.
    """
    assert PROFILE_TAB5.vety_pro_cloveka is True
    assert PROFILE_OLED256.vety_pro_cloveka is False
    doc = _scena("panel_diagnostics", "vady")
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R142)
    doc["device"] = "oled256"
    assert _obsahuji(_zpravy_dat(doc), ZNACKA_R142) == []


# --------------------------------------------------------------------------- #
# FILES: prazdny smalt VOLNO + dve vady, na ktere meridlo nedosahne
# --------------------------------------------------------------------------- #


def test_files_smalt_VOLNO_je_prazdny():
    z = _obsahuji(_zpravy("panel_files", "vady"), ZNACKA_R138)
    assert [m for m in z if "zive.13" in m], z


def test_files_po_oprave_mlci():
    assert _obsahuji(_zpravy("panel_files", "ciste"), ZNACKA_R138) == []


def test_hlavicka_sloupce_SDK_CAS_NEDAVA_je_vada_BEZ_MERIDLA():
    """Poctive nahlas: tuhle vadu brana nechyti a chytit ji neumi.

    "(SDK CAS NEDAVA)" je omluva na miste, kde ma stat jmeno sloupce.
    Z navrhu se meri tvar (vejde se? je oriznuty? ma kontrast?) a jazyk
    (nese strojove jmeno?), ale ne to, jestli veta dava smysl TAM, kde
    stoji. Test drzi ticho ZAMERNE, aby se za rok nezamenilo za pokryti.
    """
    z = _zpravy("panel_files", "vady")
    assert _obsahuji(z, "SDK ČAS NEDÁVÁ") == []


def test_tri_vety_o_microSD_chyti_brana_JEN_JEDNU_a_tady_je_ta_mezera():
    """Zmereno, ne odhadnuto: ze tri vet fotoprotokolu vystreli JEDNA.

    | list        | veta na panelu                          | R143   |
    |-------------|-----------------------------------------|--------|
    | Diagnostics | "vlozena, nepripojena"                  | mlci   |
    | Files       | "karta neni vlozena nebo mount selhal"  | mlci   |
    | Hex         | "nedostupne"                            | KRICI  |

    Proc Files mlci: slovnik se meri PODRETEZCEM a ta veta obsahuje
    povoleny stav "neni vlozena". Je to vedoma tolerance (`tokens.json:
    _pozn_stavy._mez`) - slovnik meri SLOVNIK, ne pocet tvrzeni ve vete.

    Skutecna vada je ale jinde a R143 ji nemeri: dva listy rikaji o TEZE
    karte dva ruzne, vzajemne se vylucujici stavy. Kazdy z nich je sam
    o sobe legalni; rozpor vznika az MEZI listy a validator vidi vzdycky
    jen jednu scenu. Cross-listove pravidlo by muselo bydlet v moste
    (jediny, kdo vidi vsech 62 listu naraz) a je to NOVE meridlo, ne
    oprava tohohle - proto se v KROKU 4 nepsalo a mezera je tady zapsana.
    """
    doc = _scena("panel_files", "vady")
    prvek = next(
        w for w in doc["scenes"]["main"]["widgets"] if w["_widget_id"] == "zive.16"
    )
    vysledky = {}
    for veta in ("vložena, nepřipojena",
                 "karta není vložena nebo mount selhal",
                 "nedostupné"):
        prvek["text"] = veta
        vysledky[veta] = bool(_obsahuji(_zpravy_dat(doc), ZNACKA_R143))
    assert vysledky == {
        "vložena, nepřipojena": False,
        "karta není vložena nebo mount selhal": False,
        "nedostupné": True,
    }, vysledky


def test_pravitko_KDE_JE_VOLNO_nad_nicim_je_vada_BEZ_MERIDLA():
    """Druha z trojice vad bez meridla (Network Tools).

    Popisek stupnice, ktery nad sebou zadnou stupnici nema, by vyzadoval
    kontrolu VAZBY dvou prvku - a tu dnes zadny atribut nenese: scena zna
    obdelniky a role, ne to, ke ktere kresbe popisek patri.
    """
    doc = _scena("panel_network_tools", "ciste")
    doc["scenes"]["main"]["widgets"].append({
        "type": "label", "x": 36, "y": 300, "width": 400, "height": 15,
        "text": "KDE JE VOLNO 1..13", "color_fg": "#E6E1CE",
        "color_bg": "#14170F", "align": "left", "valign": "middle",
        "_widget_id": "pravitko.99",
    })
    assert [m for m in _zpravy_dat(doc) if "pravitko.99" in m] == []


# --------------------------------------------------------------------------- #
# SETTINGS: chybejici glyf, dve vety F4, hodiny mimo slovnik
# --------------------------------------------------------------------------- #


def test_settings_recke_mi_font_zarizeni_NEMA():
    """Rule 26: "perioda 0,5 μs" s U+03BC.

    Na panelu z toho byl prazdny obdelnik ("0,5 [] s" ve fotoprotokolu).
    """
    z = _obsahuji(_zpravy("panel_settings", "vady"), KUS_R26)
    assert [m for m in z if "jm.41" in m], z


def test_settings_znak_mikro_projde_a_recke_mi_ne():
    """Dva znaky k nerozeznani okem, jeden nalez - a je to zmerene.

    U+00B5 MICRO SIGN ve fontu zarizeni JE (overeno ctenim cmap
    `lv_font_tabos_*.c`), U+03BC GREEK SMALL LETTER MU NENI. Kdyby se
    merilo "oko", pravidlo by melo nulovou rozlisovaci schopnost prave
    tam, kde je nejvic potreba.
    """
    doc = _scena("panel_settings", "ciste")
    prvek = doc["scenes"]["main"]["widgets"][0]

    prvek["text"] = "perioda 0,5 µs"       # znak mikro
    assert _obsahuji(_zpravy_dat(doc), KUS_R26) == []

    prvek["text"] = "perioda 0,5 μs"       # recke mi
    assert _obsahuji(_zpravy_dat(doc), KUS_R26)


def test_settings_dve_vety_F4_dva_ruzne_tvary():
    z = _obsahuji(_zpravy("panel_settings", "vady"), ZNACKA_R142)
    assert [m for m in z if "'IHwDiagnostics'" in m], z
    assert [m for m in z if "'%.1f'" in m], z


def test_settings_hodiny_rikaji_chybi_API_misto_stavu():
    """R143: "chybi API" neni zadny ze tri stavu hodin.

    Dlazdice Domova pritom o tychz hodinach rika "nenastaveny" - a to je
    stav ze slovniku, takze na NI brana mlci. Ze dvou vet o hodinach
    vystreli jedna; druha polovina rozporu je mezi listy (viz
    `test_tri_vety_o_microSD_...`).
    """
    z = _obsahuji(_zpravy("panel_settings", "vady"), ZNACKA_R143)
    assert [m for m in z if "hodiny" in m and "chybí API" in m], z
    assert _obsahuji(_zpravy("panel_domov", "vady"), ZNACKA_R143) == []


def test_settings_po_oprave_mlci():
    z = _zpravy("panel_settings", "ciste")
    for kus in (KUS_R26, ZNACKA_R142, ZNACKA_R143):
        assert _obsahuji(z, kus) == [], kus


# --------------------------------------------------------------------------- #
# TERMINAL: smalty PORT a PRIJATO prazdne, veta se jmenem ze SDK,
#           patka, ktera je VECNE spatne a meridlo na ni nedosahne
# --------------------------------------------------------------------------- #


def test_terminal_smalty_PORT_i_PRIJATO_jsou_prazdne():
    """Dve prazdne plochy = DVA nalezy, ne jeden.

    Kdyby pravidlo hlasilo jednou za scenu, opravar by opravil PORT, brana
    by zezelenala a PRIJATO by zustalo prazdne. Test proto pribiji obe id.
    """
    z = _obsahuji(_zpravy("panel_terminal", "vady"), ZNACKA_R138)
    assert sorted(w for w in ("v.16", "v.25") if any(w in m for m in z)) == [
        "v.16",
        "v.25",
    ], z


def test_terminal_veta_nese_jmeno_ze_SDK():
    """`ERROR cteni: NotFound` - devaty tvar R142 (jmeno ze SDK ve vete).

    Tahle veta je ZIVA na obou stranach: stoji na artboardu
    `SvorkaTerminal.dc.html` (kde ji brana nad 62 listy hlasi dodnes)
    i na panelu. Fixtura tedy neni nahradou artboardu, ale pojistkou:
    kdyby nekdo devaty tvar vypnul, spadne to i tady, ne az u 62 listu.
    """
    z = _obsahuji(_zpravy("panel_terminal", "vady"), ZNACKA_R142)
    assert [m for m in z if "NotFound" in m], z


def test_terminal_po_oprave_mlci():
    assert _chyby("panel_terminal", "ciste") == []


def test_terminal_prazdny_smalt_s_DUVODEM_mlci_a_je_to_ustup():
    """Hranicni pripad k R138: prazdno, o kterem se VI, se hlasit nema.

    Ustup je jediny a je pojmenovany (`navrh.prvky[..].prazdne`). Bez teto
    zkousky by test vys netvrdil nic o MEZI pravidla - jen o tom, ze na
    prazdnem retezci nekdo kricel.
    """
    doc = _scena("panel_terminal", "vady")
    doc["scenes"]["main"]["navrh"]["prvky"]["v.16"]["prazdne"] = (
        "port se otevira az po prvnim zapisu"
    )
    z = _obsahuji(_zpravy_dat(doc), ZNACKA_R138)
    assert [m for m in z if "v.16" in m] == [], z
    assert [m for m in z if "v.25" in m], "druhy prazdny smalt musi hlasit dal"


def test_patka_Terminalu_UART1_G53_G54_je_vada_BEZ_MERIDLA():
    """Treti z trojice vad bez meridla - a meri se na SKUTECNE patce.

    Patka rika "UART1 G53/G54 115 200". Vecne je to spatne: UART1 je RS485
    (drzi ho modul rs485), G53/G54 je Grove Port A na I2C. Zadne meridlo
    nad navrhem nezjisti, ze cislo portu nesedi se schematem desky - navrh
    o schematu nic nevi. Stav "drzi jiny modul" je pritom spravne, takze
    ani jazykova pulka brany nema co hlasit.

    Proto ta patka zustava i v CISTE tride: kdyby se "opravila", test na
    ticho by uz nemeril mlceni brany, ale nepritomnost vety.
    """
    for trida in ("vady", "ciste"):
        doc = _scena("panel_terminal", trida)
        txt = next(
            w for w in doc["scenes"]["main"]["widgets"]
            if w["_widget_id"] == "txt.41"
        )["text"]
        assert "UART1" in txt and "G53/G54" in txt, txt
        assert [m for m in _zpravy("panel_terminal", trida) if "txt.41" in m] == []


# --------------------------------------------------------------------------- #
# USB INSPECTOR: sloupec "CO TO JE" prazdny v OBOU radcich
# --------------------------------------------------------------------------- #


def test_usb_sloupec_CO_TO_JE_je_prazdny_v_obou_radcich():
    z = _obsahuji(_zpravy("panel_usb_inspector", "vady"), ZNACKA_R138)
    assert sorted(w for w in ("v.29", "v.44") if any(w in m for m in z)) == [
        "v.29",
        "v.44",
    ], z


def test_usb_po_oprave_mlci():
    assert _chyby("panel_usb_inspector", "ciste") == []


def test_usb_dva_STEJNE_popisky_sloupcu_nejsou_chyba():
    """Pozitivni kontrola k predchozimu: hlavicka "CO TO JE" je v tabulce
    DVAKRAT (dva radky zarizeni) a to je spravne. Kdyby fixtura tise
    spolehala na to, ze opakovany text nikdo nemeri, prvni pravidlo o
    duplicitach by ji zezelenalo bez opravy panelu."""
    z = _chyby("panel_usb_inspector", "ciste")
    assert [m for m in z if "CO TO JE" in m] == [], z


def test_usb_velke_prazdno_mezi_radky_je_vada_BEZ_MERIDLA():
    """Ctvrta vada bez meridla, dopsana timhle krokem.

    Fotoprotokol si vsiml "velkeho prazdna mezi radkem zarizeni a
    deskriptorem". Zmereno: mezi `v.29` (konci na y=203) a `zar.30`
    (zacina na y=229) je 26 px, coz zadne pravidlo nesoudi - a soudit
    nemuze, protoze "moc vzduchu" nema mez, kterou by slo odvodit
    z panelu. Vzdalenost mezi radky je vec SOUSTAVY (tokens.json
    `layout`), ne vada rozvrzeni; dokud tam mez nestoji, brana o tom
    mlci a je to tady napsane.
    """
    z = _zpravy("panel_usb_inspector", "ciste")
    assert [m for m in z if "prazdno" in m.lower() and "smalt" not in m] == [], z


# --------------------------------------------------------------------------- #
# Souhrn: kolik vad z fotoprotokolu ma dnes meridlo
# --------------------------------------------------------------------------- #


# Rozpad chyb PO OBRAZOVKACH, ne jeden soucet. Duvod je zmereny:
# soucet 25 prezije i vymenu "jedna chyba ubyla, jina pribyla", tedy
# prave tu zmenu, kvuli ktere test existuje. Kdyz se cislo zmeni, ma
# hlaska rict, KDE - jinak zbyde "25 != 24" a hledani zacina od nuly.
CEKANE_CHYBY_VAD = {
    "panel_domov": 5,
    "panel_system_monitor": 4,
    "panel_hex": 1,               # + 1 WARN (slovnik stavu, role stav)
    "panel_logic_analyzer": 2,
    "panel_network_tools": 3,     # + 1 WARN
    "panel_diagnostics": 2,
    "panel_files": 1,
    "panel_settings": 2,          # + 1 WARN (slovnik stavu, role stav)
    "panel_terminal": 3,
    "panel_usb_inspector": 2,
}


def test_souhrn_pokryti_fotoprotokolu():
    """POJISTKA S POJMENOVANYM DUVODEM, ne dekorace.

    Duvod, proc tenhle test zustava, i kdyz kazdou z tech chyb uz meri
    vlastni test vyse: jednotlive testy se ptaji "najde brana TUHLE
    vadu?". Nikdo z nich se nepta "nepribyla nebo neubyla nejaka JINA?".
    Prave takova zmena je nejtissi: pravidlo se rozsiri, na fixture
    zacne strilet druhy nalez, kazdy jmenovity test dal prochazi a
    tabulka pokryti ve zprave uz neplati.

    Dvanact vad z fotoprotokolu ma meridlo (viz jednotlive testy vyse),
    ctyri ne (hlavicka sloupce, pravitko nad nicim, patka Terminalu,
    vzduch mezi radky USB) a dve pulky rozporu o teze veci lezi MEZI
    listy, kam validator nevidi.
    """
    zmereno = {jm: len(_chyby(jm, "vady")) for jm in OBRAZOVKY}
    assert zmereno == CEKANE_CHYBY_VAD, (
        f"rozpad chyb po obrazovkach se zmenil:\n"
        f"  ceka se {CEKANE_CHYBY_VAD}\n"
        f"  zmereno {zmereno}\n"
        f"Kdyz pravidlo pribylo nebo ubylo, oprav CEKANE_CHYBY_VAD a napis "
        f"do komentare, ktere to bylo - cislo bez duvodu je rohatka, ne "
        f"mereni.")
    assert sum(zmereno.values()) == 25, sum(zmereno.values())
