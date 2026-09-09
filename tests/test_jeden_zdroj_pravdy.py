"""Jeden zdroj pravdy pro cisla, ktera zila v nekolika kopiich naraz.

PROC TENHLE SOUBOR JE
---------------------
Inventura meridel (9. 9. 2026) nasla ctyri veliciny, ktere mel projekt
opsane na vic mistech, a zadne dva opisy se navzajem neporovnavaly:

* ZNAKOVA SADA ZARIZENI ve ctyrech kopiich - `tabos-core/tools/gen_fonty.py`
  (recept, z ceho se font pece), `gen_subset.SADA` v kitu ("opsano
  z gen_fonty.py"), `validate_design._TAB5_FONT_CHARS` (rucne vypsanych 141
  glyfu) a `tabos-core/tools/font_pokryti.py`, ktery JEDINY cetl cmap
  skutecneho `lv_font_tabos_N.c`. Kdo pridal glyf a na kopii zapomnel,
  dostal falesny poplach - nebo hur, TICHO o znaku, ktery zarizeni neumi:
  LVGL chybejici glyf tise preskoci a z "-58 dBm" se stane "58 dBm".
* DOTYKOVA MEZ ve ctyrech kopiich - `tokens.json` 81/58 -> `tema.h` ->
  `ovladace.cpp` -> `PROFILE_TAB5.min_touch_px/warn_touch_px`. Prvni tri
  hlida `tabos_touch_lint --zrcadla`, CTVRTOU nehlidalo nic. Presne takhle
  vzniklo `sonda.py DOTYK = 48` proti `tokens.json` 81.
* PPI PANELU ve dvou cislech - `citelnost.PPI = 294` (a s nim cela tabulka
  `tokens.json._pozn_typografie`) proti `PROFILE_TAB5.ppi = 293,7`.
* DPI FIRMWARU ve dvou meridlech - `tools/lv_conf_diff.py` v jadre proti
  pravidlu 141 v ESPOSu.

Zdroj pravdy je vzdy VEC, ne papir: cmap vygenerovaneho fontu, `tokens.json`
u dotykove meze a slovniku, primarni rozmery panelu u PPI. Testy nize se
proti nim pribijeji - vcetne NEGATIVNI tridy, protoze test shody, ktery
projde i rozesle dvojici, meri jen sam sebe.

KDYZ SOUSEDNI REPOZITAR NENI VEDLE
----------------------------------
ESPOS na `tabos-core` ani na `tabos-ui-kit` zaviset nesmi. Testy, ktere je
potrebuji, se proto PRESKOCI S POJMENOVANYM DUVODEM (vzor:
`test_brana_vet_sedi_se_sdilenym_korpusem` v jadre). Tise preskoceny test
je zeleny nad nicim.
"""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import sys

import pytest

from tools.validate_design import (
    _TAB5_FONT_SYMBOLY,
    _TAB5_FONT_TEXT,
    PROFILE_TAB5,
    znaky_fontu_zarizeni,
)

ESPOS = pathlib.Path(__file__).resolve().parents[1]
DILNA = ESPOS.parents[1]                      # .../kimi/workspace
JADRO = DILNA / "tabos-core"
KIT = DILNA / "tabos-ui-kit"
FONTY = JADRO / "core" / "src" / "fonts"
TOKENY = KIT / "tokens.json"
VELIKOSTI = (14, 16, 20, 24)


def _font(velikost: int) -> pathlib.Path:
    return FONTY / f"lv_font_tabos_{velikost}.c"


def _potreba_font(velikost: int = 16) -> pathlib.Path:
    cesta = _font(velikost)
    if not cesta.is_file():
        pytest.skip(
            f"NEZMERENO: {cesta} neni na disku (tabos-core neni vedle ESPOSu) - "
            f"znakova sada zarizeni nemela na cem merit"
        )
    return cesta


def _potreba_tokeny() -> dict:
    if not TOKENY.is_file():
        pytest.skip(
            f"NEZMERENO: {TOKENY} neni na disku (tabos-ui-kit neni vedle ESPOSu) - "
            f"dotykova mez ani PPI panelu nemely proti cemu merit"
        )
    return json.loads(TOKENY.read_text(encoding="utf-8"))


def _konstanty(cesta: pathlib.Path, jmena: tuple[str, ...]) -> dict:
    """Prectena hodnota konstant ze ZDROJE souseda, ne z importu.

    Import by rozhodl o tom, jestli test meri soubor, nebo naposledy
    nactenou pamet; a hlavne by ESPOS musel sousedni repozitar umet
    naimportovat i s jeho zavislostmi.
    """
    zdroj = cesta.read_text(encoding="utf-8")
    ns: dict = {}
    for jmeno in jmena:
        zacatek = zdroj.index(f"{jmeno} = ")
        konec = zdroj.index("\n\n", zacatek)
        exec(compile(zdroj[zacatek:konec], str(cesta), "exec"), ns)  # noqa: S102
    return ns


# --------------------------------------------------------------------------- #
# 1. Znakova sada zarizeni
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("velikost", VELIKOSTI)
def test_znakova_sada_sedi_s_fontem_zarizeni(velikost):
    """`_TAB5_FONT_CHARS` == cmap toho, co ma pristroj ve flashi.

    Meri se VSECHNY CTYRI velikosti: font se pece ctyrikrat a rozejit se
    muze jedna jedina. Kdyby test cetl jen jednu, mlcel by prave o te,
    ktera se pri prekladu nepovedla.
    """
    cesta = _potreba_font(velikost)
    umi = znaky_fontu_zarizeni(cesta)
    chybi = sorted(hex(ord(z)) for z in (umi - PROFILE_TAB5.font_chars))
    navic = sorted(hex(ord(z)) for z in (PROFILE_TAB5.font_chars - umi))
    assert not chybi, f"{cesta.name} umi znaky, o kterych profil nevi: {chybi}"
    assert not navic, f"profil slibuje znaky, ktere {cesta.name} nema: {navic}"


def test_vsechny_ctyri_velikosti_maji_TUTEZ_sadu():
    """Pozitivni kontrola k testu vyse: ctyri fonty, jedna sada.

    Bez teto kontroly by shoda s profilem mohla platit "prumerne" - kazda
    velikost jina a profil nekde mezi. Rez se lisi kresbou, ne abecedou.
    """
    _potreba_font()
    sady = {v: znaky_fontu_zarizeni(_font(v)) for v in VELIKOSTI if _font(v).is_file()}
    assert len(sady) == len(VELIKOSTI)
    prvni = sady[VELIKOSTI[0]]
    for v, s in sady.items():
        assert s == prvni, f"velikost {v} ma jinou sadu nez {VELIKOSTI[0]}"


def test_sada_se_deli_na_TEXT_a_SYMBOLY_a_nic_nezbyva():
    """Delba je uplna: kazdy glyf je bud text, nebo symbol LVGL."""
    assert frozenset() == _TAB5_FONT_TEXT & _TAB5_FONT_SYMBOLY
    assert PROFILE_TAB5.font_chars == _TAB5_FONT_TEXT | _TAB5_FONT_SYMBOLY
    assert len(_TAB5_FONT_TEXT) == 141
    assert len(_TAB5_FONT_SYMBOLY) == 60
    # Hranice mezi pulkami je kodovy bod, ne vkus: symboly LVGL sedi
    # v soukrome zone U+F000 a vys, text nikde blizko.
    assert all(ord(z) >= 0xF000 for z in _TAB5_FONT_SYMBOLY)
    assert all(ord(z) < 0xF000 for z in _TAB5_FONT_TEXT)


def test_textova_pulka_sedi_s_cmap_bez_symbolu():
    """Kontrola z druhe strany: text = cmap minus soukroma zona."""
    umi = znaky_fontu_zarizeni(_potreba_font())
    assert frozenset(z for z in umi if ord(z) < 0xF000) == _TAB5_FONT_TEXT
    assert frozenset(z for z in umi if ord(z) >= 0xF000) == _TAB5_FONT_SYMBOLY


def test_znaky_fontu_zarizeni_cte_OBA_tvary_cmap():
    """Souvisly rozsah (ASCII) i rozptyleny seznam (cestina, symboly).

    Kdyby cetl jen jeden tvar, ztratil by TISE pulku abecedy - a shoda
    s profilem by pak byla zelena nad polovicnim mereni.
    """
    umi = znaky_fontu_zarizeni(_potreba_font())
    assert "A" in umi and "~" in umi              # souvisly rozsah 0x20-0x7E
    assert "ř" in umi and "−" in umi    # rozptyleny seznam
    assert "" in umi                        # symboly LVGL


def test_znaky_fontu_zarizeni_na_souboru_bez_cmap_je_CHYBA_ne_prazdno(tmp_path):
    """NEGATIVNI TRIDA: prazdna mnozina se nesmi tvarit jako 'font nic neumi'.

    Kdyby cteni pri zmene formatu vratilo prazdno, prosly by testy vyse
    jedine tehdy, kdyby byl prazdny i profil - ale hur: brana by pak
    mlcela o KAZDEM znaku, protoze porovnavat by nebylo s cim.
    """
    podvrh = tmp_path / "lv_font_tabos_16.c"
    podvrh.write_text("/* zadna cmap */\nint x = 0;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cmap"):
        znaky_fontu_zarizeni(podvrh)


def test_MUTACE_zmena_v_cmap_test_zcervena(tmp_path):
    """Kdyz se font opravdu rozejde s profilem, pozna se to.

    Bez teto mutace by shoda vyse mohla byt shodou dvou kopii teze chyby.
    """
    zdroj = _potreba_font()
    text = zdroj.read_text(encoding="utf-8", errors="replace")
    # Prvni souvisly rozsah zkratime o jeden znak - font tim prijde o '~'.
    zmeneny = text.replace(".range_length = 95,", ".range_length = 94,", 1)
    assert zmeneny != text, "predpoklad mutace nesedi - zmenil se format fontu"
    podvrh = tmp_path / "lv_font_tabos_16.c"
    podvrh.write_text(zmeneny, encoding="utf-8")
    assert znaky_fontu_zarizeni(podvrh) != PROFILE_TAB5.font_chars


def test_znakova_sada_kitu_sedi_s_textovou_pulkou():
    """`gen_subset.SADA` uz se neopisuje - je to obal nad ESPOSem.

    Test to overuje NAD SOUBOREM v kitu, ne nad importem v pameti: kdyby
    tam nekdo vratil rucni seznam, tenhle test to musi videt.
    """
    cesta = KIT / "navrh-appky" / "gen_subset.py"
    if not cesta.is_file():
        pytest.skip(
            f"NEZMERENO: {cesta} neni na disku (tabos-ui-kit neni vedle ESPOSu) - "
            f"znakova sada kitu nemela proti cemu merit"
        )
    zdroj = cesta.read_text(encoding="utf-8")
    assert "_TAB5_FONT_TEXT" in zdroj, (
        "gen_subset.py si sadu zase opisuje; ma ji brat z validate_design"
    )
    assert "SADA = sorted(ord(z) for z in _TAB5_FONT_TEXT)" in zdroj


def test_recept_gen_fonty_zada_PRESNE_to_co_font_umi():
    """Recept v jadre (`gen_fonty.py`) proti cmap upeceneho fontu.

    Recept je jediny seznam, ktery neni opis - je to ZADANI. Musi tedy
    sedet do znaku: kdyz zada vic, nekdo ceka glyf, ktery ve flashi neni
    (do 9. 9. 2026 to bylo U+007F DEL, pro ktery Montserrat glyf nema).
    """
    cesta = JADRO / "tools" / "gen_fonty.py"
    if not cesta.is_file():
        pytest.skip(
            f"NEZMERENO: {cesta} neni na disku (tabos-core neni vedle ESPOSu) - "
            f"recept fontu nemel proti cemu merit"
        )
    umi = znaky_fontu_zarizeni(_potreba_font())
    ns = _konstanty(cesta, ("ASCII", "CESKE", "TYPO", "SYMBOLY"))
    zadane: set[int] = set()
    for jmeno in ("ASCII", "CESKE", "TYPO", "SYMBOLY"):
        for kus in str(ns[jmeno]).split(","):
            kus = kus.strip()
            if "-" in kus and kus.startswith("0x"):
                a, b = kus.split("-")
                zadane |= set(range(int(a, 16), int(b, 16) + 1))
            elif kus:
                zadane.add(int(kus, 0))
    ma = {ord(z) for z in umi}
    assert sorted(hex(c) for c in (zadane - ma)) == []
    assert sorted(hex(c) for c in (ma - zadane)) == []


# --------------------------------------------------------------------------- #
# 2. Dotykova mez
# --------------------------------------------------------------------------- #


def test_profil_tab5_sedi_s_tokens_json():
    """Ctvrta kopie dotykove meze uz neni bez hlidace."""
    tokeny = _potreba_tokeny()
    dotyk = tokeny["touch"]
    assert PROFILE_TAB5.warn_touch_px == dotyk["target_min_px"] == 81
    assert PROFILE_TAB5.min_touch_px == dotyk["hard_floor_px"] == 58


def test_dotykova_mez_je_v_MILIMETRECH_tim_cim_ji_publikace_zada():
    """Pozitivni kontrola smyslu: 81 px = 7,0 mm, 58 px = 5,0 mm.

    Pixel je na 294 PPI zavadejici jednotka - 44px tlacitko ma 3,8 mm.
    Publikovane meze (Apple 7,0 mm, Material 7,6 mm, ISO 9241-411 7 mm)
    jsou fyzicke, takze se test pta na milimetry, ne na cislo v tokenech.
    """
    _potreba_tokeny()
    assert round(PROFILE_TAB5.mm(PROFILE_TAB5.warn_touch_px), 1) == 7.0
    assert round(PROFILE_TAB5.mm(PROFILE_TAB5.min_touch_px), 1) == 5.0


def test_MUTACE_zmeneny_token_dotyku_test_zcervena():
    """Kdyz se tokeny hnou a profil ne, musi to test poznat.

    Bez mutace by tvrzeni "obe strany sedi" platilo i pro dva shodne
    OPISY teze chyby: obe strany by mohly nest tutez spatnou hodnotu.
    """
    tokeny = _potreba_tokeny()
    zmeneny = json.loads(json.dumps(tokeny))
    zmeneny["touch"]["target_min_px"] = 96
    assert PROFILE_TAB5.warn_touch_px != zmeneny["touch"]["target_min_px"]
    assert PROFILE_TAB5.warn_touch_px == tokeny["touch"]["target_min_px"]


# --------------------------------------------------------------------------- #
# 3. PPI panelu
# --------------------------------------------------------------------------- #


def test_ppi_je_odvozene_a_shodne_s_tokens():
    """PPI se nevoli: plyne z rozliseni a uhlopricky.

    Tim se z cisla stava mereni. Kdo do `tokens.json` napise libovolne
    cislo, spadne na prepoctu, ne na nazoru.
    """
    tokeny = _potreba_tokeny()
    panel = tokeny["panel"]
    uhlopricka_px = math.hypot(panel["sirka_px"], panel["vyska_px"])
    assert round(uhlopricka_px / panel["uhlopricka_in"]) == panel["ppi"] == 294
    assert PROFILE_TAB5.ppi == panel["ppi"]
    assert (panel["sirka_px"], panel["vyska_px"]) == (
        PROFILE_TAB5.match_w,
        PROFILE_TAB5.match_h,
    )


def test_citelnost_kitu_bere_PPI_z_tehoz_mista():
    """Kit uz PPI neopisuje - cte ho z `tokens.json` jako vsichni ostatni."""
    cesta = KIT / "navrh-appky" / "citelnost.py"
    if not cesta.is_file():
        pytest.skip(
            f"NEZMERENO: {cesta} neni na disku (tabos-ui-kit neni vedle ESPOSu) - "
            f"PPI kitu nemelo proti cemu merit"
        )
    zdroj = cesta.read_text(encoding="utf-8")
    assert "PPI = _ppi_z_tokenu()" in zdroj, (
        "citelnost.py ma PPI zase natvrdo; ma ho brat z tokens.json"
    )
    # ... a zadny KOD uz cislo nesmi nest. Hleda se v radcich, ne v celem
    # souboru: v komentari o teto oprave veta "PPI = 294" stat SMI a musi -
    # bez ni by se za rok nikdo nedozvedel, proc se to menilo.
    kod = [r for r in zdroj.splitlines() if not r.lstrip().startswith("#")]
    assert not [r for r in kod if r.strip().startswith("PPI = 294")]


def test_zaokrouhleni_PPI_je_pod_rozlisenim_meridla():
    """Poctive k zaokrouhleni 293,72 -> 294: o kolik to lze.

    Odchylka 0,1 % dela na nejmensi verzalce (rez 14 px) 0,001 mm, tedy
    ~1/86 pixelu. Kdyby byla vetsi nez pixel, zaokrouhlit by se nesmelo -
    a tenhle test by to rekl.
    """
    tokeny = _potreba_tokeny()
    panel = tokeny["panel"]
    presne = math.hypot(panel["sirka_px"], panel["vyska_px"]) / panel["uhlopricka_in"]
    verzalka_px = 0.700 * 14
    rozdil_mm = abs(verzalka_px * 25.4 / presne - verzalka_px * 25.4 / panel["ppi"])
    assert rozdil_mm < 25.4 / panel["ppi"], "zaokrouhleni PPI uz je videt na pixelu"


# --------------------------------------------------------------------------- #
# 4. DPI firmwaru: jedno meridlo, ne dve
# --------------------------------------------------------------------------- #


def test_lv_conf_diff_uz_DPI_nesoudi_a_rekne_kdo_ho_meri():
    """Druha mez, ktera o dokumentovane odchylce nevedela, je pryc.

    Podminka NENI "neobsahuje LV_DPI_DEF": nastroj o nem musi mluvit dal,
    jen uz ho nesmi mit v seznamu, ktery soudi. Ticho o volbe, ktera tam
    byla, by se od "zmereno a v poradku" nedalo rozeznat.
    """
    cesta = JADRO / "tools" / "lv_conf_diff.py"
    if not cesta.is_file():
        pytest.skip(
            f"NEZMERENO: {cesta} neni na disku (tabos-core neni vedle ESPOSu) - "
            f"delba mezi lv_conf_diff a pravidlem 141 nemela na cem merit"
        )
    ns = _konstanty(cesta, ("DULEZITE", "JINDE_MERENE"))
    assert "LV_DPI_DEF" not in ns["DULEZITE"]
    assert "LV_DPI_DEF" in ns["JINDE_MERENE"]
    assert "141" in ns["JINDE_MERENE"]["LV_DPI_DEF"]
    # Pozitivni kontrola: ostatni volby tam zustaly, takze to neni tim,
    # ze by nastroj prestal soudit vsechno.
    assert "LV_COLOR_DEPTH" in ns["DULEZITE"]


def test_dokumentovana_odchylka_DPI_je_v_tokens_a_ma_duvod():
    """Zdroj vedome odchylky je JEDEN a je to `tokens.json`."""
    tokeny = _potreba_tokeny()
    blok = tokeny["firmware"]["lv_dpi_def"]
    assert isinstance(blok["hodnota"], int) and blok["hodnota"] > 0
    assert len(blok["duvod"]) > 40, "odchylka bez duvodu je diera, ne rozhodnuti"


# --------------------------------------------------------------------------- #
# 5. Slovnik stavu (pravidlo 143) - obsahove rozhodnuti majitele
# --------------------------------------------------------------------------- #


def test_slovnik_stavu_v_tokens_je_nabity():
    """Do 9. 9. 2026 klic `stavy` neexistoval a pravidlo 143 nemelo co merit."""
    tokeny = _potreba_tokeny()
    stavy = tokeny["stavy"]
    assert set(stavy) >= {"microSD", "hodiny"}
    for vec, seznam in stavy.items():
        assert isinstance(seznam, list) and seznam, vec
        assert all(isinstance(s, str) and s.strip() for s in seznam), vec


def test_slovnik_stavu_nema_v_sobe_dokumentaci():
    """Klic `stavy` vozi most PRIMO do sceny; textovy klic by byl ERROR.

    Poznamky proto zijou v `_pozn_stavy` a tenhle test hlida, aby se tam
    nekdo nevratil - vada by se objevila az v behu brany nad 62 listy.
    """
    tokeny = _potreba_tokeny()
    assert not [k for k in tokeny["stavy"] if k.startswith("_")]
    assert tokeny["_pozn_stavy"]["_o_slovniku"]


# --------------------------------------------------------------------------- #
# 6. Anti-fake brana: dve kopie tehoz kodu ve dvou repozitarich
# --------------------------------------------------------------------------- #


def _potreba_anti_fake() -> tuple[pathlib.Path, pathlib.Path]:
    dvojice = (JADRO / "tools" / "anti_fake_check.py",
               KIT / "tools" / "anti_fake_check.py")
    chybi = [c for c in dvojice if not c.is_file()]
    if chybi:
        pytest.skip(
            f"NEZMERENO: {', '.join(str(c) for c in chybi)} neni na disku "
            f"(sousedni repozitar neni vedle ESPOSu) - shoda dvou kopii "
            f"anti-fake brany nemela na cem merit"
        )
    return dvojice


def test_anti_fake_brana_je_v_obou_repozitarich_TYZ_kod():
    """Dve kopie, jedno chovani - a hlidac, ktery si vsimne rozejiti.

    JEDNU kopii mit nelze a je poctive rict proc: kit je samostatny
    repozitar a jeho vlastni CI si branu pousti sam
    (`.github/workflows/ci.yml`: `python tools/anti_fake_check.py include
    tools`). Kdyby se kopie smazala, prestala by brana v kitu existovat;
    kdyby se z ni udelal obal nad jadrem, zmizela by v CI, kde jadro vedle
    neni. Zbyva tedy dvojice - ale UZ NE dvojice, ktera se muze tise
    rozejit.

    ROZESLA SE, a nebylo to kosmeticke (zmereno 9. 9. 2026): kopie v jadre
    dostala opravu, po ktere cesta NA SOUBOR znamena "zkontroluj prave
    tenhle soubor". Kopie v kitu ji nemela, takze `rglob` nad souborem
    vracel prazdno a brana TISE neskenovala nic - vratila "cisto" a nikdo
    se nedozvedel, ze nemerila. Kit ji dnes vola nad adresari, takze ta
    chyba nekousala; "dnes to nekouse" je ale presne to ticho, proti
    kteremu tahle kampan je.

    Konce radku se NEPOROVNAVAJI: kit ma LF, jadro CRLF, a je to vlastnost
    repozitare (`.gitattributes`), ne chovani brany.
    """
    jadro, kit = _potreba_anti_fake()
    a = jadro.read_bytes().replace(b"\r\n", b"\n")
    b = kit.read_bytes().replace(b"\r\n", b"\n")
    assert a == b, (
        "anti_fake_check.py se v jadre a v kitu rozesel; jedno chovani, "
        "dve kopie - prenes zmenu i do druhe"
    )


@pytest.mark.parametrize("ktera", [0, 1])
def test_anti_fake_brana_umi_cestu_na_SOUBOR(tmp_path, ktera):
    """Pozitivni kontrola te opravy: bez ni je test shody zeleny nad nicim.

    Kdyby se obe kopie vratily k rozbite verzi, test vys by porad prosel
    (jsou shodne!) a nikdo by nezmeril, ze brana nad souborem mlci. Tenhle
    test proto pousti OBE kopie jako proces a diva se, co udelaji - meri
    CHOVANI, ne pritomnost radku ve zdrojaku.

    Dve tridy naraz: soubor se zakazanym vzorem musi vydat nalez (jinak
    brana nemeri nic), cisty soubor musi projit (jinak brana krici na vsem
    a nalez by v tom hluku zanikl).
    """
    brana = _potreba_anti_fake()[ktera]

    spinavy = tmp_path / "spinavy.py"
    spinavy.write_text("# TO" + "DO: dodelat\n", encoding="utf-8")
    hot = subprocess.run(
        [sys.executable, str(brana), str(spinavy)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert hot.returncode == 1, (
        f"{brana}: cesta na SOUBOR se zakazanym vzorem prosla (kod "
        f"{hot.returncode}) - brana tise neskenovala nic"
    )
    assert "TO" + "DO" in hot.stdout + hot.stderr

    cisty = tmp_path / "cisty.py"
    cisty.write_text("x = 1\n", encoding="utf-8")
    hot = subprocess.run(
        [sys.executable, str(brana), str(cisty)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert hot.returncode == 0, hot.stdout + hot.stderr


# --------------------------------------------------------------------------- #
# 7. Rozliseni panelu (most do_espos.py) - PATA kopie tehoz cisla
# --------------------------------------------------------------------------- #
#
# `1280x720` stalo do 9. 9. 2026 v `do_espos.py` trikrat natvrdo: v oknu
# headless Chromu, v hlavicce dokumentu a v hlavicce sceny. Vedle nej zije
# tataz dvojice v `PROFILE_TAB5.match_w/match_h` - a podle NI si validator
# profil vybira. Rozejit se mohly tise: most by kreslil do jineho okna, nez
# v jakem se meri, a validator by si nestezoval, protoze by na dokument
# zadny profil nesedel (a s nim by zmlkla vsechna profilova pravidla naraz).

MOST = KIT / "navrh-appky" / "do_espos.py"


def _most():
    """`do_espos` nactene ze zdroje kitu (tyz postup jako u `_dopln_polozky`)."""
    import importlib.util

    if not MOST.is_file():
        pytest.skip(
            f"NEZMERENO: {MOST} neni na disku (tabos-ui-kit neni vedle ESPOSu) - "
            f"rozliseni panelu nemelo na cem merit"
        )
    spec = importlib.util.spec_from_file_location("_do_espos_rozmer", MOST)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_most_bere_rozliseni_panelu_z_PROFILU():
    assert _most().rozmer_panelu() == (PROFILE_TAB5.match_w, PROFILE_TAB5.match_h)


def test_MUTACE_zmeneny_profil_zmeni_i_most():
    """Ze to cislo NENI opsane, dokaze az to, ze se hne SPOLU s profilem.

    Prvni test by prosel i mostu, ktery ma `1280x720` natvrdo - dneska ta
    dve cisla shodou okolnosti sedi. Tenhle profil na okamzik prepise a
    ceka, ze most pojede za nim.
    """
    most = _most()
    prof = most.profil_espos()
    stare = (prof.match_w, prof.match_h)
    try:
        object.__setattr__(prof, "match_w", 800)
        object.__setattr__(prof, "match_h", 480)
        assert most.rozmer_panelu() == (800, 480)
    finally:
        object.__setattr__(prof, "match_w", stare[0])
        object.__setattr__(prof, "match_h", stare[1])
    assert most.rozmer_panelu() == stare


def test_v_moste_uz_rozliseni_natvrdo_NENI():
    """Pozitivni kontrola k obema testum vys: kdyby nekdo cislo pristi rok
    vratil na jine misto (treba do noveho prepinace Chromu), testy vys by
    porad prosly - meri jen funkci, ne cely soubor."""
    if not MOST.is_file():
        pytest.skip(f"NEZMERENO: {MOST} neni na disku")
    kod = [
        r for r in MOST.read_text(encoding="utf-8").splitlines()
        if "1280" in r and not r.lstrip().startswith("#")
    ]
    # Zbyt smi jen radky, ktere o tom cisle VYPRAVEJI (hlavicka modulu a
    # docstring `rozmer_panelu`), ne radky, ktere ho POUZIVAJI.
    assert all("x720" in r for r in kod), kod
