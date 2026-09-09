"""Jeden zdroj pravdy pro TYPOGRAFII a PALETU (krok 3 kampane).

PROC TENHLE SOUBOR JE
---------------------
Inventura meridel (9. 9. 2026) nasla vedle znakove sady, dotykove meze
a PPI jeste dve veliciny, ktere zily v nekolika kopiich naraz:

* **PALETA VE TRECH KOPIICH** - `tokens.json: colors` (navrh),
  `core/include/tabos_core/tema.h` (firmware) a `ram.BARVY` v kitu
  (dvanact hexu OPSANYCH z tokens.json). Kit ani ESPOS `tema.h` nikdy
  neporovnavaly a `ram.BARVY` neporovnaval nikdo s nicim. Hodnoty se
  shodovaly do posledniho bitu; kdyby se rozesly, poznalo by se to az
  na skle.
* **SKALA PISMA VE CTYRECH OPISECH** - `ram.py` (co generator sazi),
  `tokens.json: typography` (jmena LVGL fontu), `tokens.json:
  _pozn_typografie` (tataz cisla znovu, i s fyzikou) a tabulka 3.1
  specifikace (`citelnost.OTISK_*`). Porovnaval je JEN skript
  `citelnost.py` s navratovym kodem - kdo ho nespustil rukou, nedozvedel
  se nic.

K tomu dve veci, ktere se meri stejnou latkou ze dvou stran:

* **SIRKA RETEZCE**: `sirky.py` v kitu ji pocita ze souctu advance sirek
  tabulky `hmtx` (offline, PRED renderem), Rule 137 z `Range` v
  prohlizeci (po renderu). Nebyl to duplicitni merid ke smazani - meri
  se v jinem okamziku - ale CHYBEL TEST PARITY. Ted je (0,04 px na
  osmatricetiznakove vete).
* **PRAVIDLO 152 SE NENAPSALO** a je tu zaznam proc, i s cislem.

Zdroj pravdy je vzdy VEC, ne papir: `tema.h` je to, co ma pristroj ve
flashi, `montserrat_b64.txt` je font, ktery se do listu opravdu vsazi.

KDYZ SOUSEDNI REPOZITAR NENI VEDLE
----------------------------------
ESPOS na `tabos-core` ani na `tabos-ui-kit` zaviset nesmi. Testy, ktere
je potrebuji, se PRESKOCI S POJMENOVANYM DUVODEM. Tise preskoceny test
je zeleny nad nicim.
"""

from __future__ import annotations

import json
import math
import pathlib
import re
import sys

import pytest

from tools.validate_design import (
    PROFILE_TAB5,
    radkovy_box,
    sirka_meze,
    sirka_retezce,
    skala_rozpory,
    validate_data,
)

ESPOS = pathlib.Path(__file__).resolve().parents[1]
DILNA = ESPOS.parents[1]                      # .../kimi/workspace
JADRO = DILNA / "tabos-core"
KIT = DILNA / "tabos-ui-kit"
TOKENY = KIT / "tokens.json"
TEMA = JADRO / "core" / "include" / "tabos_core" / "tema.h"
NAVRH_APPKY = KIT / "navrh-appky"
FONT_B64 = NAVRH_APPKY / "montserrat_b64.txt"

# Ktery klic `tokens.json: colors` je ktery token `tema.h`. Klice se
# zamerne neprejmenovavaly (navrh mluvi o "phosphor_mut", firmware o
# "kMut"), takze jmeno protejsek neprozradi - spojnici drzi tahle tabulka
# a prave proto ji nekdo musi hlidat.
BARVA_TOKEN = {
    "base": "kBase", "panel": "kPanel", "raised": "kRaised",
    "phosphor": "kPhosphor", "phosphor_mut": "kMut", "accent": "kAccent",
    "warn": "kWarn", "text": "kText", "magenta_exception": "kVyjimka",
    "obrys": "kObrys", "smalt": "kSmalt", "inkoust": "kInkoust",
    "ink_utlum": "kInkUtlum", "ryska": "kRyska",
}
# `ok` je v `tokens.json` navic a je to ZAMER: role "v poradku" ma dnes
# tutez barvu jako zivy udaj, ale je to jina role a muze se rozejit.
BARVY_BEZ_TOKENU = {"ok"}
# `kDlazdiceShora` a `kDlazdiceZdola` jsou naopak navic ve firmwaru:
# prechod dlazdice, ktery navrh nekresli (obe strany = kPanel).
TOKENY_BEZ_BARVY = {"kDlazdiceShora", "kDlazdiceZdola"}


def _potreba(cesta: pathlib.Path, co: str) -> pathlib.Path:
    if not cesta.exists():
        pytest.skip(
            f"NEZMERENO: {cesta} neni na disku - {co} nemelo proti cemu merit"
        )
    return cesta


def _tokeny() -> dict:
    return json.loads(_potreba(TOKENY, "paleta ani skala pisma")
                      .read_text(encoding="utf-8"))


def _tema_barvy() -> dict[str, str]:
    t = _potreba(TEMA, "paleta firmwaru").read_text(encoding="utf-8")
    return {
        m.group(1): "#" + m.group(2).upper()
        for m in re.finditer(r"constexpr uint32_t (k\w+)\s*=\s*0x([0-9A-Fa-f]{6})", t)
    }


def _kit_modul(jmeno: str):
    _potreba(NAVRH_APPKY / f"{jmeno}.py", f"modul {jmeno} kitu")
    if str(NAVRH_APPKY) not in sys.path:
        sys.path.insert(0, str(NAVRH_APPKY))
    return __import__(jmeno)


# --------------------------------------------------------------------------- #
# Paleta: tri kopie, jedna pravda
# --------------------------------------------------------------------------- #


def test_paleta_navrhu_sedi_s_paletou_firmwaru():
    barvy = _tokeny()["colors"]
    tema = _tema_barvy()
    assert tema, "tema.h nema ani jeden token - zmenil se tvar?"
    rozdily = []
    for klic, token in BARVA_TOKEN.items():
        if klic not in barvy:
            rozdily.append(f"tokens.json colors nema '{klic}'")
        elif token not in tema:
            rozdily.append(f"tema.h nema '{token}' (barva '{klic}')")
        elif barvy[klic].upper() != tema[token]:
            rozdily.append(
                f"{klic} = {barvy[klic].upper()}, ale {token} = {tema[token]}")
    assert not rozdily, "; ".join(rozdily)


def test_paleta_ma_v_obou_smerech_stejne_role():
    """Kontrolni skupina: kdyz pribude barva jen na jedne strane, musi
    to byt VIDET. Bez tohohle by test vyse prosel nad neuplnou mnozinou."""
    barvy = set(_tokeny()["colors"])
    tema = set(_tema_barvy())
    assert barvy - set(BARVA_TOKEN) == BARVY_BEZ_TOKENU
    assert tema - set(BARVA_TOKEN.values()) == TOKENY_BEZ_BARVY


def test_ok_a_phosphor_maji_dnes_tutez_barvu_a_je_to_zamer():
    barvy = _tokeny()["colors"]
    assert barvy["ok"].upper() == barvy["phosphor"].upper()


def test_dlazdice_firmwaru_je_dnes_panel():
    tema = _tema_barvy()
    assert tema["kDlazdiceShora"] == tema["kDlazdiceZdola"] == tema["kPanel"]


def test_ram_kitu_uz_paletu_NEOPISUJE():
    """Treti kopie je pryc: `ram.BARVY` se cte z `tokens.json`."""
    ram = _kit_modul("ram")
    barvy = _tokeny()["colors"]
    for role, token in ram.ROLE_TOKENU.items():
        assert ram.BARVY[role] == barvy[token].upper(), role


def test_ram_kitu_pri_chybejici_barve_SPADNE(tmp_path):
    """MUTACE: generator, ktery si pri nesouhlasu dosadi vlastni cislo,
    uz neni jeden zdroj. Musi spadnout, ne mlcky pokracovat."""
    ram = _kit_modul("ram")
    zdroj = json.loads(TOKENY.read_text(encoding="utf-8"))
    del zdroj["colors"]["smalt"]
    falesny = tmp_path / "tokens.json"
    falesny.write_text(json.dumps(zdroj, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="smalt"):
        ram._paleta(falesny)


def test_ram_kitu_nad_zdravymi_tokeny_NESPADNE(tmp_path):
    """POZITIVNI KONTROLA teze cesty: nad kopii, ktera je v poradku,
    projde. Bez ni by test vyse mohl chytat neco uplne jineho."""
    ram = _kit_modul("ram")
    kopie = tmp_path / "tokens.json"
    kopie.write_text(TOKENY.read_text(encoding="utf-8"), encoding="utf-8")
    assert ram._paleta(kopie) == ram.BARVY


def test_pravidlo_150_meri_paletu_z_tokens_json():
    """Nosic a mez se nesmi rozejit: co brana pozna jako 'mimo paletu',
    musi byt presne to, co v `tokens.json` neni."""
    barvy = list(_tokeny()["colors"].values())
    scena = {
        "device": "tab5",
        "scenes": {"main": {"width": 1280, "height": 720, "widgets": [
            {"type": "label", "x": 36, "y": 120, "width": 200, "height": 19,
             "text": "FPS", "color_fg": barvy[0], "color_bg": "#151E26",
             "align": "left", "valign": "middle", "_widget_id": "a.1"}],
            "navrh": {"paleta": barvy}}},
    }
    n = [i for i in validate_data(scena, file_label="t", warnings_as_errors=False)
         if "barva mimo paletu" in i.message]
    assert len(n) == 1
    assert "#151e26" in n[0].message


# --------------------------------------------------------------------------- #
# Skala pisma: ctyri opisy, jedna fyzika
# --------------------------------------------------------------------------- #


def _skala_data():
    ram = _kit_modul("ram")
    cit = _kit_modul("citelnost")
    tok = _tokeny()
    skala = {jmeno: rez for jmeno, rez, pozn in cit.SKALA if not pozn}
    return dict(
        skala=skala,
        box=ram.BOX,
        roztec=ram.ROZTEC,
        otisk_box=cit.OTISK_BOX,
        otisk_minut=cit.OTISK_MINUT,
        typography=tok["typography"],
        pozn_typografie=tok["_pozn_typografie"],
        token_role=cit.TOKEN_ROLE,
        asc=cit.ASC,
        desc=cit.DESC,
    )


def test_skala_pisma_sedi():
    """ram.py x tokens.json x tabulka 3.1 x fyzika panelu: zadny rozpor."""
    nalezy = skala_rozpory(PROFILE_TAB5, **_skala_data())
    assert nalezy == [], "; ".join(nalezy)


def test_skala_pisma_POSUNUTA_neprojde():
    """MUTACE, kterou musi chytit KONTROLA MNOZINOU, ne polozkou.

    Kontroly tvaru "je-li rez v tabulce, sedi?" propusti posunutou skalu:
    kdyz se rezy zmeni na 15/17/21/25/33 a vsechny opisy se srovnaji,
    zadny `rez in otisk` neplati, cyklus se o nic neopre a meridlo
    vytiskne SHODU. Doloženo pokusem na kopii mimo repozitar (2026-09-06).
    """
    d = _skala_data()
    posun = {jmeno: rez + 1 for jmeno, rez in d["skala"].items()}
    d["skala"] = posun
    d["box"] = {r: radkovy_box(r, d["asc"], d["desc"]) for r in posun.values()}
    d["roztec"] = {r: b + 2 for r, b in d["box"].items()}
    nalezy = skala_rozpory(PROFILE_TAB5, **d)
    assert nalezy
    assert any("tabulka 3.1" in n for n in nalezy)


def test_skala_pisma_MUTACE_jednoho_boxu():
    d = _skala_data()
    d["box"] = dict(d["box"])
    rez = sorted(d["box"])[0]
    d["box"][rez] = d["box"][rez] + 1
    nalezy = skala_rozpory(PROFILE_TAB5, **d)
    assert any(f"box rezu {rez}" in n for n in nalezy)


def test_skala_pisma_MUTACE_jmena_fontu_v_tokenech():
    d = _skala_data()
    d["typography"] = dict(d["typography"])
    d["typography"]["label"] = "tabos_18"
    nalezy = skala_rozpory(PROFILE_TAB5, **d)
    assert any("typography.label" in n for n in nalezy)


def test_skala_pisma_MUTACE_uhlove_velikosti_v_poznamce():
    d = _skala_data()
    d["pozn_typografie"] = json.loads(json.dumps(d["pozn_typografie"]))
    d["pozn_typografie"]["body"]["minut_450mm"] = 9.99
    nalezy = skala_rozpory(PROFILE_TAB5, **d)
    assert any("minut_450mm" in n for n in nalezy)


def test_radkovy_box_zaokrouhluje_kazdou_cast_zvlast():
    """round(asc*rez)+round(desc*rez), NE round((asc+desc)*rez).
    Pri hhea 968/251 by jednorazove zaokrouhleni dalo u 16 px 20 misto 19."""
    asc, desc = 0.968, 0.251
    assert radkovy_box(16, asc, desc) == 19
    assert round((asc + desc) * 16) == 20


def test_skala_je_v_tokens_json_a_ne_v_generatoru():
    """Vyjimky rezu maji JEDINY strojovy zdroj - a ma jich pet listu."""
    vyj = _tokeny()["typografie_vyjimky"]
    listy = {k for k in vyj if not k.startswith("_")}
    assert listy == {"SvorkaCislice", "SvorkaRfFtm", "SvorkaKlavesnice",
                     "SvorkaTerminalKl", "DnesSystemMonitor"}
    for jmeno in listy:
        for rez, duvod in vyj[jmeno].items():
            assert int(rez) > 0, (jmeno, rez)
            assert isinstance(duvod, str) and duvod.strip(), (jmeno, rez)


def test_uhlova_velikost_panelu_sedi_s_tabulkou_31():
    """Fyzika profilu ESPOSu musi davat cisla, ktera specifikace tiskne."""
    cit = _kit_modul("citelnost")
    for rez, minut in cit.OTISK_MINUT.items():
        muj = PROFILE_TAB5.minuty(PROFILE_TAB5.verzalka_pomer * rez)
        assert abs(muj - minut) <= 0.005, (rez, muj, minut)


# --------------------------------------------------------------------------- #
# Sirka retezce: font offline vs prohlizec
# --------------------------------------------------------------------------- #

# ZMERENA dvojice (2026-09-09) na listu SvorkaPreklad: veta v roli hodnota,
# rez 20 px. `Range` v prohlizeci dal 393,800 px, soucet advance sirek
# tehoz fontu 393,840 px - rozdil 0,04 px, tedy 1/25 pixelu.
PARITA_TEXT = "Vypadá to jako I2C. D1 = SCL, D0 = SDA."
PARITA_REZ = 20
PARITA_RANGE_PX = 393.800
PARITA_ROZDIL_PX = 0.05


def _font():
    _potreba(FONT_B64, "sirka retezce vsazenym fontem")
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        pytest.skip("NEZMERENO: fontTools neni nainstalovan")
    import base64
    import io
    syrove = base64.b64decode(FONT_B64.read_text(encoding="ascii").strip())
    f = TTFont(io.BytesIO(syrove))
    return f["head"].unitsPerEm, f.getBestCmap(), f["hmtx"].metrics


def test_sirka_z_fontu_je_soucet_advance_sirek():
    upem, cmap, hm = _font()
    s = sirka_retezce("AV", 20, 0.0, upem, cmap, hm)
    rucne = (hm[cmap[ord("A")]][0] + hm[cmap[ord("V")]][0]) * 20 / upem
    assert abs(s - rucne) < 1e-9


def test_sirka_z_fontu_roste_s_rezem_linearne():
    upem, cmap, hm = _font()
    a = sirka_retezce("TEPLOTA CPU", 16, 0.0, upem, cmap, hm)
    b = sirka_retezce("TEPLOTA CPU", 32, 0.0, upem, cmap, hm)
    assert abs(b - 2 * a) < 1e-9


def test_sirka_z_fontu_pricita_prostrkani_i_za_posledni_pismeno():
    """CSS letter-spacing se pricita i ZA posledni glyf - schranka je
    o tu mezeru sirsi nez inkoust."""
    upem, cmap, hm = _font()
    bez = sirka_retezce("ABC", 20, 0.0, upem, cmap, hm)
    s = sirka_retezce("ABC", 20, 0.16, upem, cmap, hm)
    assert abs(s - bez - 0.16 * 20 * 3) < 1e-9


def test_sirka_z_fontu_NEZNAMY_glyf_je_chyba_ne_nula():
    """LVGL chybejici glyf TISE preskoci a z '-58 dBm' je '58 dBm'."""
    upem, cmap, hm = _font()
    with pytest.raises(ValueError, match="U\\+"):
        sirka_retezce("中", 20, 0.0, upem, cmap, hm)


def test_meze_opsaneho_cisla_jsou_jednostranne():
    """Kerning sirku jen ZMENSUJE, takze mez je jednostranna."""
    dolni, horni = sirka_meze(100.4, 6.0)
    assert dolni == pytest.approx(94.4)
    assert horni == math.ceil(100.4)
    assert not dolni <= 94.3 <= horni
    assert dolni <= 100 <= horni


def test_PARITA_sirek_R137_a_fontu():
    """Dve cesty k teze velicine se musi potkat.

    `sirky.py` scita advance sirky z `hmtx` PRED renderem; Rule 137 meri
    `Range` v prohlizeci PO renderu. Neni to tyz vypocet (Chrome navic
    uplatnuje parovy kerning z GPOS), takze se neporovnava na rovnost -
    ale rozdil musi byt pod mezi, jinak jedno z obou meri neco jineho.
    """
    upem, cmap, hm = _font()
    muj = sirka_retezce(PARITA_TEXT, PARITA_REZ, 0.0, upem, cmap, hm)
    assert abs(muj - PARITA_RANGE_PX) <= PARITA_ROZDIL_PX, (muj, PARITA_RANGE_PX)


def test_PARITA_by_padla_na_jinem_retezci():
    """POZITIVNI KONTROLA parity: kdyby se veta zmenila, test to pozna."""
    upem, cmap, hm = _font()
    jiny = sirka_retezce(PARITA_TEXT + " a jeste kus", PARITA_REZ, 0.0,
                         upem, cmap, hm)
    assert abs(jiny - PARITA_RANGE_PX) > PARITA_ROZDIL_PX


def test_sirky_kitu_uz_sirku_NEPOCITAJI_samy():
    """`sirky.py` se stal obalem: pocita ji `validate_design`."""
    sirky = _kit_modul("sirky")
    upem, cmap, hm = _font()
    assert sirky.sirka(PARITA_TEXT, PARITA_REZ) == pytest.approx(
        sirka_retezce(PARITA_TEXT, PARITA_REZ, 0.0, upem, cmap, hm))
    assert sirky.KERNING == 6.0


# --------------------------------------------------------------------------- #
# Pravidlo 152 se NENAPSALO - zaznam proc, i s cislem
# --------------------------------------------------------------------------- #


def test_R152_se_nenapsalo_a_tady_je_ta_mezera():
    """ZAZNAM ROZHODNUTI, ne mrtvy test.

    Meridlo kitu (`zmer_odsazeni.py`, vetev b) hlasilo hlavicku sloupce,
    ktera nesedi na svem obsahu, kdyz je od nej do 6 px. Prah 6 nebyl
    nikde odvozeny a pravidlo 152 se melo napsat JEN tehdy, kdyz se
    dolozi pripad 4-6 px, na kterem Rule 134 (near-miss <= 3 px) mlci.

    ZMERENO 9. 9. 2026 nad vsemi 62 listy kitu (obe slozky, sceny z
    mostu): takovych pripadu je **NULA**. Jedine, co ta vetev na 62
    listech vydala, byla trida (a) - klavesnicovy blok na x=28 - a tu
    ted meri Rule 151. Pravidlo 152 se proto NENAPSALO a vetev (b) se
    smazala.

    Tenhle test drzi obe hrany te mezery, aby bylo videt, ze je vedoma:
    rozdil 4 px je pro Rule 134 uz daleko a pro Rule 151 uz uvnitr
    soustavy, takze o nem dnes NIKDO nemluvi.
    """
    def _w(wid, x, text):
        return {"type": "label", "x": x, "y": 120 + 40 * int(wid[-1]),
                "width": 200, "height": 19, "text": text,
                "color_fg": "#E4DFCC", "color_bg": "#14170F",
                "align": "left", "valign": "middle", "_widget_id": wid}

    data = {
        "device": "tab5",
        "scenes": {"main": {"width": 1280, "height": 720, "widgets": [
            _w("popis.1", 40, "KANAL"), _w("txt.2", 36, "D0 dolu")],
            "navrh": {"prvky": {}, "soustava": {"pole_x": 20, "vsazka": 16}}}},
    }
    nalezy = validate_data(data, file_label="t", warnings_as_errors=False)
    assert not [i for i in nalezy if "near-miss alignment" in i.message]
    assert not [i for i in nalezy if "text se lepi na ram" in i.message]


def test_Rule_134_hlida_az_do_tri_pixelu():
    """Druha hrana teze mezery: 3 px Rule 134 JESTE chyti."""
    def _w(wid, x, y, text):
        return {"type": "label", "x": x, "y": y, "width": 200, "height": 19,
                "text": text, "color_fg": "#E4DFCC", "color_bg": "#14170F",
                "align": "left", "valign": "middle", "_widget_id": wid}

    data = {
        "device": "tab5",
        "scenes": {"main": {"width": 1280, "height": 720, "widgets": [
            _w("popis.1", 39, 120, "KANAL"), _w("txt.2", 36, 160, "D0 dolu")]}},
    }
    nalezy = validate_data(data, file_label="t", warnings_as_errors=False)
    assert [i for i in nalezy if "near-miss alignment" in i.message]
