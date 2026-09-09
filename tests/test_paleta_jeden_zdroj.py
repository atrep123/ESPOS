"""MOST vozi paletu (a soustavu, skalu, slovnik) - hlidac, ktery chybel.

PROC TENHLE SOUBOR JE
---------------------
Tri soubory se v komentari odvolavaly prave na tenhle nazev jako na
duvod, PROC smeji prestat opisovat paletu:

    research/ESPOS/tools/validate_design.py   (docstring `_r150_nalezy`)
    tabos-ui-kit/navrh-appky/ram.py:61
    tabos-ui-kit/navrh-appky/do_espos.py:1047

Soubor ale NEEXISTOVAL. Kdo si tu vetu sel overit, nenasel nic - a to je
tatáz trida vady, kterou tahle kampan uklizi: zduvodneni ticha, ktere se
odvolava na hlidace, jenz neni.

CO TU JE NAVIC PROTI `test_typografie_a_paleta.py`
--------------------------------------------------
Ten meri, ze se TRI KOPIE palety shoduji (`tokens.json` x `tema.h` x
`ram.BARVY`) a ze pravidlo 150 umi barvu mimo paletu poznat, kdyz mu
paletu nekdo PODA.

Tady se meri clanek mezi tim: ze ji nekdo opravdu poda. Zadny test
nesahal na `do_espos.paleta()`, `soustava()`, `skala_pisma()` ani
`slovnik_stavu()` - tedy na ctyri funkce mostu, ktere jsou JEDINOU cestou
z `tokens.json` do sceny. Kdyby kterakoli z nich zacala vracet prazdno,
pravidla 143, 148, 150 a 151 by nad zivymi listy mlcela a sada by
zustala zelena: fixtury si paletu nosi v sobe.

Vsechny ctyri se proto meri STEJNYM zpusobem:

  1. nad zivym `tokens.json` vraci to, co v nem stoji (ne prazdno),
  2. MUTACE souboru se v jejich vysledku PROJEVI (jinak by test mohl
     chytat opsanou konstantu misto cteni),
  3. ROZBITY soubor da prazdno - a to je datova zavora, ne "v poradku";
     ze na ni pravidlo rekne NEMERENO, meri `test_validate_rules_148_151`.

Ke kazde funkci je i POZITIVNI KONTROLA nad kopii, ktera je v poradku:
bez ni by "mutace spadla" mohlo znamenat jen to, ze cesta padá vzdycky.

KDYZ SOUSEDNI REPOZITAR NENI VEDLE
----------------------------------
ESPOS na `tabos-ui-kit` zaviset nesmi. Testy se PRESKOCI s pojmenovanym
duvodem - a nejen kdyz soubor chybi: preskoci se i tehdy, kdyz nalezeny
`tokens.json` NENI ten kitovy (nahodny stejnojmenny soubor dve patra nad
ESPOSem uz jednou dal `KeyError` misto skipu).
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

from tools.validate_design import validate_data

ESPOS = pathlib.Path(__file__).resolve().parents[1]
DILNA = ESPOS.parents[1]                      # .../kimi/workspace
KIT = DILNA / "tabos-ui-kit"
TOKENY = KIT / "tokens.json"
NAVRH_APPKY = KIT / "navrh-appky"
JADRO = DILNA / "tabos-core"

# Podpis kitoveho `tokens.json`. Bez nej staci stejne pojmenovany soubor
# kdekoli dve patra nad ESPOSem a testy pak padaji na `KeyError` misto
# toho, aby rekly "tenhle soubor nemerim".
#
# POZOR NA ROZDIL, KTERY SE LEHKO SLOUCI:
#   * CIZI soubor tehoz jmena  -> SKIP, protoze tady neni co merit;
#   * KITOVY soubor bez bloku  -> PAD, protoze prave to je vada.
# Kdyby oboji koncilo skipem, umlcelo by ubrani bloku `layout` nebo
# `colors` celou tuhle sadu a zustala by zelena nad nicim. Rozliseni drzi
# `PODPIS`: `theme` kitu je jmeno navrhoveho jazyka, ne obecne slovo.
PODPIS = ("theme", "smaltovy-cifernik")
POVINNE_KLICE = ("colors", "typography", "layout", "spacing", "stavy")
POVINNE_ROLE = ("base", "smalt", "inkoust", "phosphor")


def _tokeny_kitu() -> pathlib.Path:
    if not TOKENY.exists():
        pytest.skip(f"NEZMERENO: {TOKENY} neni na disku - most nemel co vozit")
    try:
        data = json.loads(TOKENY.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        # Rozbity soubor neumime podepsat. Ze to NENI ticho, drzi vedle
        # bezici testy mostu (`_most()`), ktere na podpis necekaji: nad
        # rozbitym JSONem vraci most prazdno a ty spadnou.
        pytest.skip(f"NEZMERENO: {TOKENY} se neda precist ({e})")
    klic, hodnota = PODPIS
    if not isinstance(data, dict) or data.get(klic) != hodnota:
        pytest.skip(f"NEZMERENO: {TOKENY} nema {klic} == {hodnota!r} - "
                    f"neni to tokens.json kitu, jen soubor tehoz jmena")
    chybi = [k for k in POVINNE_KLICE if k not in data]
    assert not chybi and isinstance(data.get("colors"), dict), (
        f"{TOKENY} JE tokens.json kitu (podpis sedi), ale chybi mu "
        f"{chybi or 'blok colors jako slovnik'} - most nema co vozit a "
        f"pravidla 143/148/150/151 by nad zivymi listy mlcela")
    chybi_role = [r for r in POVINNE_ROLE if r not in data["colors"]]
    assert not chybi_role, (
        f"{TOKENY} JE tokens.json kitu, ale v palete chybi role "
        f"{chybi_role} - paleta se rozesla s `tema.h` firmwaru")
    return TOKENY


def _most():
    """Modul `do_espos` kitu, nebo pojmenovany skip."""
    if not (NAVRH_APPKY / "do_espos.py").exists():
        pytest.skip(f"NEZMERENO: {NAVRH_APPKY / 'do_espos.py'} neni na disku")
    if str(NAVRH_APPKY) not in sys.path:
        sys.path.insert(0, str(NAVRH_APPKY))
    return __import__("do_espos")


def _kopie(tmp_path: pathlib.Path, uprav=None) -> pathlib.Path:
    """Kopie zivych tokenu; `uprav(data)` smi obsah zmenit pred zapisem."""
    data = json.loads(_tokeny_kitu().read_text(encoding="utf-8"))
    if uprav is not None:
        uprav(data)
    kam = tmp_path / "tokens.json"
    kam.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return kam


# --------------------------------------------------------------------------- #
# 1. PALETA (pravidlo 150)
# --------------------------------------------------------------------------- #


def test_most_vozi_paletu_z_tokens_json():
    """`do_espos.paleta()` vraci hexy z `tokens.json: colors`, ne opis."""
    most = _most()
    barvy = json.loads(_tokeny_kitu().read_text(encoding="utf-8"))["colors"]
    ocekavane = [v for v in barvy.values() if isinstance(v, str)]
    assert most.paleta() == ocekavane
    assert len(ocekavane) >= 10, (
        f"paleta ma jen {len(ocekavane)} barev - to uz neni paleta navrhu, "
        f"a pravidlo 150 by nad ni obvinovalo skoro vsechno")


def test_MUTACE_barvy_v_tokens_json_je_videt_v_palete_mostu(tmp_path):
    """Kdyby si most paletu OPSAL, tenhle test by zustal zeleny.

    Meni se jeden hex na hodnotu, ktera v zadne palete neni; musi zmizet
    stary a objevit se novy. Tim je doloženo, ze funkce CTE.
    """
    most = _most()
    stara = json.loads(_tokeny_kitu().read_text(encoding="utf-8"))["colors"]["smalt"]
    nova = "#010203"
    assert stara.lower() != nova

    kopie = _kopie(tmp_path, lambda d: d["colors"].__setitem__("smalt", nova))
    vysledek = [b.lower() for b in most.paleta(kopie)]
    assert nova in vysledek, "mutace se v palete mostu neprojevila"
    assert stara.lower() not in vysledek, "stara barva v palete zustala"


def test_paleta_mostu_nad_ZDRAVOU_kopii_je_TATAZ(tmp_path):
    """Pozitivni kontrola teze cesty: kopie beze zmeny da tyz vysledek.

    Bez ni by test vyse mohl chytat cokoli, co nad kopii dopadne jinak
    (jinou cestu, jine kodovani, prazdny navrat).
    """
    most = _most()
    assert most.paleta(_kopie(tmp_path)) == most.paleta()


def test_ROZBITY_tokens_json_da_prazdnou_paletu(tmp_path):
    """Datova zavora, ne "v poradku".

    Ze pravidlo 150 pri prazdne palete rekne NEMERENO (a brana kvuli tomu
    skonci nenulovym kodem), meri `test_validate_rules_148_151.py`; tady
    se meri jen to, ze most prazdno opravdu vrati a nic si nedomysli.
    """
    most = _most()
    rozbity = tmp_path / "tokens.json"
    rozbity.write_text('{"colors": {"base": "#000",,,}}', encoding="utf-8")
    assert most.paleta(rozbity) == []


def test_paleta_mostu_JE_MEZ_pravidla_150():
    """Nosic a mez se nesmi rozejit.

    Barva Z palety mostu musi projit, barva mimo ni vystrelit - obojí v
    jednom behu, aby "0 nalezu" nemohlo znamenat "pravidlo nebezelo".
    """
    most = _most()
    barvy = most.paleta()
    mimo = "#010203"
    assert mimo not in [b.lower() for b in barvy]

    def _scena(fg: str) -> dict:
        return {"device": "tab5", "scenes": {"main": {
            "width": 1280, "height": 720, "navrh": {"paleta": barvy},
            "widgets": [{"type": "label", "x": 36, "y": 120, "width": 200,
                         "height": 19, "text": "FPS", "color_fg": fg,
                         "color_bg": barvy[0], "align": "left",
                         "valign": "middle", "_widget_id": "a.1"}]}}}

    def _mimo_paletu(scena: dict) -> list[str]:
        return [i.message for i in validate_data(
            scena, file_label="t", warnings_as_errors=False)
            if "barva mimo paletu" in i.message]

    assert _mimo_paletu(_scena(barvy[1])) == [], "barva z palety vystrelila"
    obvineni = _mimo_paletu(_scena(mimo))
    assert len(obvineni) == 1, obvineni
    assert mimo in obvineni[0]


# --------------------------------------------------------------------------- #
# 2. SOUSTAVA ODSAZENI (pravidlo 151)
# --------------------------------------------------------------------------- #


def test_most_vozi_soustavu_odsazeni_z_tokens_json():
    most = _most()
    lay = json.loads(_tokeny_kitu().read_text(encoding="utf-8"))["layout"]
    assert most.soustava() == {"pole_x": lay["obsah"]["x"],
                               "vsazka": lay["ram"]["vsazka"]}


def test_MUTACE_soustavy_je_videt_v_moste(tmp_path):
    most = _most()
    kopie = _kopie(tmp_path, lambda d: d["layout"]["ram"].__setitem__("vsazka", 99))
    assert most.soustava(kopie)["vsazka"] == 99
    assert most.soustava()["vsazka"] != 99, "mutace prosakla do ZIVYCH tokenu"


def test_soustava_bez_bloku_layout_je_PRAZDNO(tmp_path):
    """Chybejici blok NENI nula: nula by rekla "text zacina na x=0"."""
    most = _most()
    assert most.soustava(_kopie(tmp_path, lambda d: d.pop("layout"))) == {}


# --------------------------------------------------------------------------- #
# 3. SKALA PISMA (pravidlo 148)
# --------------------------------------------------------------------------- #


def test_most_vozi_skalu_pisma_z_tokens_json():
    most = _most()
    sk = most.skala_pisma("SvorkaFiles")
    assert sk["rezy"], "skala pisma je prazdna - pravidlo 148 by nemelo mez"
    # Rezy se ctou ze JMEN LVGL fontu (`tabos_16`), ne z opsaneho seznamu.
    tok = json.loads(_tokeny_kitu().read_text(encoding="utf-8"))["typography"]
    z_jmen = sorted({int(s) for h in tok.values()
                     for s in [h.rsplit("_", 1)[-1]] if s.isdigit()})
    assert sk["rezy"] == z_jmen


def test_MUTACE_skaly_je_videt_v_moste(tmp_path):
    most = _most()
    role = next(iter(json.loads(
        _tokeny_kitu().read_text(encoding="utf-8"))["typography"]))
    kopie = _kopie(tmp_path,
                   lambda d: d["typography"].__setitem__(role, "tabos_33"))
    assert 33 in most.skala_pisma("SvorkaFiles", kopie)["rezy"]
    assert 33 not in most.skala_pisma("SvorkaFiles")["rezy"]


def test_vyjimky_skaly_jsou_PER_LIST(tmp_path):
    """Tyz rez smi byt na jednom listu zamer a na druhem preklep.

    Kdyby byly vyjimky globalni, jedna jmenovita vyjimka by umlcela
    pravidlo na vsech 62 listech naraz.
    """
    most = _most()
    kopie = _kopie(tmp_path, lambda d: d.__setitem__(
        "typografie_vyjimky", {"ListA": {"13": "vedomy rez klavesnice"}}))
    assert most.skala_pisma("ListA", kopie)["vyjimky"] == {
        "13": "vedomy rez klavesnice"}
    assert most.skala_pisma("ListB", kopie)["vyjimky"] == {}


# --------------------------------------------------------------------------- #
# 4. SLOVNIK STAVU (pravidlo 143)
# --------------------------------------------------------------------------- #


def test_most_vozi_slovnik_stavu_z_tokens_json():
    most = _most()
    stavy = json.loads(_tokeny_kitu().read_text(encoding="utf-8")).get("stavy")
    assert isinstance(stavy, dict) and stavy, (
        "tokens.json nema blok `stavy` - pravidlo 143 by nemelo slovnik")
    assert most.slovnik_stavu() == stavy


def test_MUTACE_slovniku_stavu_je_videt_v_moste(tmp_path):
    most = _most()
    kopie = _kopie(tmp_path, lambda d: d["stavy"].__setitem__(
        "microSD", ["vymysleny stav"]))
    assert most.slovnik_stavu(kopie)["microSD"] == ["vymysleny stav"]
    assert most.slovnik_stavu()["microSD"] != ["vymysleny stav"]


def test_slovnik_stavu_bez_bloku_je_PRAZDNO(tmp_path):
    most = _most()
    assert most.slovnik_stavu(_kopie(tmp_path, lambda d: d.pop("stavy"))) == {}


# --------------------------------------------------------------------------- #
# 5. Ze most vozi paletu i do ZIVE sceny, ne jen ve funkci
# --------------------------------------------------------------------------- #


def test_zive_sceny_kitu_NESOU_paletu_a_soustavu():
    """Mezikroky `_scena_*.dc.json` jsou to, co brana opravdu meri.

    Jsou gitignorovane, takze bez behu brany na disku nejsou - potom se
    test PRESKOCI s duvodem. Kdyz tam jsou, musi v nich blok `navrh`
    nest tutez paletu, jakou vraci `do_espos.paleta()`. Bez tohohle
    clanku by vsechno vyse platilo o funkci, kterou nikdo nevola.
    """
    most = _most()
    sceny = sorted(NAVRH_APPKY.glob("_scena_*.json"))
    if not sceny:
        pytest.skip(
            f"NEZMERENO: v {NAVRH_APPKY} nejsou mezikroky _scena_*.json "
            f"(brana nebezela s --zapis-scenu) - clanek most->scena se "
            f"nemel na cem overit")
    paleta = [b.lower() for b in most.paleta()]
    soustava = most.soustava()
    bez_palety, bez_soustavy = [], []
    for s in sceny:
        try:
            navrh = json.loads(s.read_text(encoding="utf-8")
                               )["scenes"]["main"].get("navrh", {})
        except (OSError, ValueError, KeyError):
            continue
        if [b.lower() for b in navrh.get("paleta", [])] != paleta:
            bez_palety.append(s.name)
        if navrh.get("soustava") != soustava:
            bez_soustavy.append(s.name)
    assert not bez_palety, (
        f"{len(bez_palety)} z {len(sceny)} scen nenese paletu mostu: "
        f"{bez_palety[:5]}")
    assert not bez_soustavy, (
        f"{len(bez_soustavy)} z {len(sceny)} scen nenese soustavu mostu: "
        f"{bez_soustavy[:5]}")


# --------------------------------------------------------------------------- #
# 6. Brana kitu je FAIL-CLOSED: nemereni konci nenulovym kodem
# --------------------------------------------------------------------------- #


def test_brana_zna_VSECHNY_znacky_nemereni_behovou_hodnotou():
    """`do_espos.znacky_nemereno` je bere z validatoru, neopisuje je.

    Kdyby se opsaly, prezila by kazda zmena hlasky jako tise prazdny
    seznam: brana by na nemereni prestala padat a nikdo by to nepoznal.
    Test proto porovnava s tim, co validator OPRAVDU ma - ne se seznamem
    napsanym tady.
    """
    from tools import validate_design as vd

    most = _most()
    ocekavane = sorted(getattr(vd, j) for j in dir(vd)
                       if j.startswith("ZNACKA_") and j.endswith("_NEMERENO"))
    assert ocekavane, "validate_design nema ani jednu znacku *_NEMERENO"
    assert sorted(most.znacky_nemereno(vd)) == ocekavane


def test_brana_bez_jedine_znacky_nemereni_je_CHYBA_ne_ticho():
    """MUTACE: validator, ktery prestane hlasit nemereni, branu ZASTAVI.

    Bez tohohle by "fail-closed plati" znamenalo jen to, ze dnes nahodou
    nejake znacky existuji. Prazdny seznam je nefunkcni pojistka, ne
    cisto - a nefunkcni pojistka se ma ozvat.
    """
    most = _most()

    class BezZnacek:
        ZNACKA_R150 = "barva mimo paletu"     # jina znacka, ale zadna NEMERENO

    with pytest.raises(SystemExit, match="NEMERENO"):
        most.znacky_nemereno(BezZnacek)


def test_znacky_nemereni_pokryvaji_vsechna_ctyri_datova_pravidla():
    """Pojmenovana kontrola rozsahu: 143, 148, 151 a nove 150.

    Vsechna ctyri vozi svou mez z `tokens.json`, tedy z jedineho souboru;
    jeden preklep v nem umlci vsechna. Kdyby nekteremu z nich znacka
    chybela, spadlo by jeho ticho pod branu, ktera zustane zelena.
    """
    from tools import validate_design as vd

    for jmeno in ("ZNACKA_R143_NEMERENO", "ZNACKA_R148_NEMERENO",
                  "ZNACKA_R150_NEMERENO", "ZNACKA_R151_NEMERENO"):
        assert hasattr(vd, jmeno), f"validate_design nema {jmeno}"
