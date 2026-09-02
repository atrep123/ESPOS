"""Rudy zapis (`cyberpunk_designer/redline.py`).

Jadro testu je jeden pozadavek zadani: **posun o znamy pocet pixelu musi dat
patch se spravnymi cisly v OBOU soustavach** - v obrazovce (scena 1280x720)
i v souradnicich generatoru.

Souradnice generatoru se ale NEDOPOCITAVA odectenim `(PAD 20, OBSAH_Y 68)`.
Revize A to vyvratila dvema merenimi a fixtura `tab5_clean_meta.json` oba
pripady drzi, aby uz nemohly znovu projit:

* `hodnota1` je POPISEK - scenove `y = 148` je rozsah inkoustu, ne ramecek.
  Generator ma `top: 76`; odecet by dal 80. (Zivy protejsek: SvorkaHex
  `bajt.19`, generator `top: 60`, odecet 63.)
* `radek1` ma `offsetParent` = `.karta`, ne `.obsah`. Generator ma
  `left: 16`; odecet by dal 44. (Zivy protejsek: SvorkaCislice `mez.49`,
  generator `left: 16`, odecet 850.)

Ke kazdemu tvrzeni protipriklad:

* cislo se vyda -> a u prvku bez inline stylu (zahlavi) i u sceny bez
  `_meta_X.json` se NEVYDA a rekne se "neprevedeno";
* zmena se najde -> a bez zmeny je patch prazdny;
* brana pusti cistou scenu -> a pri ERRORu rudy zapis NEVYDA;
* posun se meri proti otisku -> a to i po dvou posunech za sebou;
* Insert vyda patch -> a BEHEM psani do inspektoru ho nevyda;
* scena na disku sedi s otiskem -> patch se vyda; kdyz se pod editorem
  zmenila, NEVYDA se nic (rekonstrukce nalezu R4 z etapy 5).
"""

from __future__ import annotations

import collections
import json
import pathlib

import pytest

from cyberpunk_designer import redline, tab5_most
from ui_designer import WidgetConfig

FIXTURY = pathlib.Path(__file__).parent / "fixtures"
CISTA = FIXTURY / "tab5_clean.json"
CISTA_META = FIXTURY / "tab5_clean_meta.json"
VADNA = FIXTURY / "tab5_defects.json"


@pytest.fixture
def cista_scena_na_disku(tmp_path):
    """Scena VCETNE `_meta_X.json` - tak, jak ji vyda `do_espos --zapis-scenu`."""
    cil = tmp_path / "_scena_Cista.dc.json"
    cil.write_text(CISTA.read_text(encoding="utf-8"), encoding="utf-8")
    meta = tmp_path / "_meta_Cista.dc.json"
    meta.write_text(CISTA_META.read_text(encoding="utf-8"), encoding="utf-8")
    return cil


@pytest.fixture
def scena_bez_meta(tmp_path):
    """Tataz scena, ale BEZ meta - napr. po behu brany bez prepinacu."""
    cil = tmp_path / "_scena_Hola.dc.json"
    cil.write_text(CISTA.read_text(encoding="utf-8"), encoding="utf-8")
    return cil


@pytest.fixture
def vadna_scena_na_disku(tmp_path):
    cil = tmp_path / "_scena_Vadna.dc.json"
    cil.write_text(VADNA.read_text(encoding="utf-8"), encoding="utf-8")
    return cil


def _app_se_scenou(make_app, cesta):
    most = tab5_most.nacti(cesta, s_podkladem=False)
    app = make_app(size=(256, 128))
    tab5_most.pripoj(app, most)
    return app


def _widget(app, wid: str):
    for w in app.state.current_scene().widgets:
        if getattr(w, "_widget_id", None) == wid:
            return w
    raise AssertionError(f"widget {wid} ve scene neni")


def _zmena(zapis, wid: str):
    return next(z for z in zapis.zmeny if z.widget_id == wid)


def _posun(app, wid: str, dx: int = 0, dy: int = 0):
    w = _widget(app, wid)
    w.x = int(w.x) + dx
    w.y = int(w.y) + dy
    return redline.vytvor(app.tab5_otisk, app.state.current_scene().widgets)


# --------------------------------------------------------------------------- #
# Prevod: cislo pochazi z generatoru, ne z odectu
# --------------------------------------------------------------------------- #


def test_tlacitko_da_cisla_v_OBOU_soustavach(make_app, cista_scena_na_disku):
    """Hlavni pozadavek zadani, na prvku, kde je scenove y opravdu hrana boxu."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    w = _widget(app, "ovl1")
    puvodni_x, puvodni_y = int(w.x), int(w.y)
    zapis = _posun(app, "ovl1", dx=12, dy=-8)

    z = _zmena(zapis, "ovl1")
    assert z.stav == redline.STAV_POSUNUT
    assert z.pred[:2] == (puvodni_x, puvodni_y)
    assert z.po[:2] == (puvodni_x + 12, puvodni_y - 8)
    assert z.posun == (12, -8, 0, 0)

    # generator: inline styl z meta (44, 332, 240, 88) + tentyz rozdil
    assert z.pred_gen == (44, 332, 240, 88)
    assert z.po_gen == (56, 324, 240, 88)
    assert z.prevoditelny is True
    assert z.neprevedene_osy == ()


def test_popisek_bere_cislo_z_generatoru_NE_odectenim(make_app, cista_scena_na_disku):
    """Nalez A1: u popisku je scenove `y` inkoust, ne horni hrana ramecku.

    `hodnota1` ma ve scene y = 148, ale generator zapsal `top: 76`.
    Odectenim OBSAH_Y (68) by vzniklo 80 - cislo, ktere v generatoru NENI.
    """
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    w = _widget(app, "hodnota1")
    assert int(w.y) == 148  # kotva: kdyby se fixtura zmenila, test to rekne
    zapis = _posun(app, "hodnota1", dy=10)
    z = _zmena(zapis, "hodnota1")

    assert z.pred_gen[1] == 76
    assert z.po_gen[1] == 86
    assert z.pred_gen[1] != 148 - 68  # prave tenhle odecet byl nalez A1
    # vyska inline stylem zapsana neni -> zadne cislo se u ni nevyda
    assert z.pred_gen[3] is None
    assert z.neprevedene_osy == ("h",)
    assert z.prevoditelny is False


def test_prvek_s_cizim_rodicem_bere_cislo_toho_rodice(make_app, cista_scena_na_disku):
    """Nalez A2: inline `left` je relativni k `offsetParent`, ne k `.obsah`."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    w = _widget(app, "radek1")
    assert int(w.x) == 64
    zapis = _posun(app, "radek1", dx=6)
    z = _zmena(zapis, "radek1")

    assert z.rodic == "karta"
    assert z.cizi_rodic is True
    assert z.pred_gen[0] == 16
    assert z.po_gen[0] == 22
    assert z.pred_gen[0] != 64 - 20  # prave tenhle odecet byl nalez A2
    assert any("karta" in v for v in zapis.varovani)


def test_zahlavi_bez_inline_stylu_NEVYDA_zadne_cislo(make_app, cista_scena_na_disku):
    """`nadpis` kresli CSS trida; generator k nemu zadne cislo nezapsal."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    zapis = _posun(app, "nadpis", dx=4)
    z = _zmena(zapis, "nadpis")

    assert z.pred_gen == (None, None, None, None)
    assert z.po_gen == (None, None, None, None)
    assert z.prevoditelny is False
    assert z.neprevedene_osy == ("x", "y", "w", "h")
    assert any("NEVYDAVA" in v for v in zapis.varovani)


def test_bez_meta_se_nevyda_ani_jedno_cislo_a_rekne_se_to(make_app, scena_bez_meta):
    """Scena bez `_meta_X.json`: zadny doklad => zadne cislo, a nahlas."""
    app = _app_se_scenou(make_app, scena_bez_meta)
    assert app.tab5_otisk.ma_meta is False
    zapis = _posun(app, "ovl1", dx=12)
    z = _zmena(zapis, "ovl1")

    assert z.pred_gen == (None, None, None, None)
    assert z.prevoditelny is False
    assert any("_meta_" in v for v in zapis.varovani)
    # a v citelnem textu stoji "neprevedeno" misto cisla z odectu
    text = redline.jako_text(zapis)
    radek = next(r for r in text.splitlines() if r.strip().startswith("generator:"))
    assert "neprevedeno" in radek
    assert "44" not in radek
    assert "CHYBI" in text


def test_pridany_prvek_zadne_cislo_generatoru_nema(make_app, cista_scena_na_disku):
    """Novy prvek z editoru v generatoru neexistuje - nema odkud vzit cislo."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    sc = app.state.current_scene()
    novy = WidgetConfig(type="button", x=100, y=200, width=90, height=90, text="NOVY")
    novy._widget_id = "novy.99"
    sc.widgets.append(novy)
    z = _zmena(redline.vytvor(app.tab5_otisk, sc.widgets), "novy.99")

    assert z.stav == redline.STAV_PRIDAN
    assert z.pred is None
    assert z.po_gen == (None, None, None, None)
    assert z.neprevedene_osy == ("x", "y", "w", "h")


def test_artboard_ze_zdroje():
    assert redline.artboard_ze_zdroje("_scena_SvorkaLA.dc.json") == "SvorkaLA.dc"
    assert redline.artboard_ze_zdroje("SvorkaLA.dc.json") == "SvorkaLA.dc"
    assert redline.artboard_ze_zdroje("") == ""


# --------------------------------------------------------------------------- #
# Rozdil proti otisku
# --------------------------------------------------------------------------- #


def test_zmena_velikosti_se_taky_zaznamena(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    w = _widget(app, "ovl1")
    w.width = int(w.width) + 20
    z = _zmena(redline.vytvor(app.tab5_otisk, app.state.current_scene().widgets), "ovl1")
    assert z.posun == (0, 0, 20, 0)
    assert z.po_gen[2] - z.pred_gen[2] == 20
    assert z.po_gen[2] == 260


def test_bez_zmeny_je_patch_prazdny(make_app, cista_scena_na_disku):
    """Protipriklad: kdyz se nic nehnulo, nesmi vzniknout ani jedna zmena."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    zapis = redline.vytvor(app.tab5_otisk, app.state.current_scene().widgets)
    assert zapis.prazdny is True
    assert zapis.zmeny == ()
    assert zapis.varovani == ()


def test_meri_se_proti_OTISKU_ne_proti_minulemu_stavu(make_app, cista_scena_na_disku):
    """Dva posuny za sebou musi dat soucet, ne jen ten posledni."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    w = _widget(app, "ovl1")
    puvodni_x = int(w.x)
    w.x = puvodni_x + 10
    redline.vytvor(app.tab5_otisk, app.state.current_scene().widgets)
    w.x = puvodni_x + 25
    z = _zmena(redline.vytvor(app.tab5_otisk, app.state.current_scene().widgets), "ovl1")
    assert z.posun[0] == 25
    assert z.po_gen[0] == 44 + 25


def test_smazany_prvek(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    sc = app.state.current_scene()
    sc.widgets.remove(_widget(app, "ovl1"))
    z = _zmena(redline.vytvor(app.tab5_otisk, sc.widgets), "ovl1")
    assert z.stav == redline.STAV_CHYBI
    assert z.po is None
    assert z.posun == (0, 0, 0, 0)
    # cislo PRED zmenou znamo je, cislo PO neexistuje
    assert z.pred_gen == (44, 332, 240, 88)
    assert z.po_gen == (None, None, None, None)


def test_prvky_bez_id_se_ohlasi(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    sc = app.state.current_scene()
    bezejmenny = WidgetConfig(type="label", x=100, y=200, width=20, height=20)
    sc.widgets.append(bezejmenny)
    zapis = redline.vytvor(app.tab5_otisk, sc.widgets)
    assert any("_widget_id" in v for v in zapis.varovani)
    assert zapis.zmeny == ()


def test_opakovane_id_se_vynecha_a_ohlasi(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    sc = app.state.current_scene()
    dvojnik = WidgetConfig(type="button", x=300, y=300, width=90, height=90)
    dvojnik._widget_id = "ovl1"
    sc.widgets.append(dvojnik)
    zapis = redline.vytvor(app.tab5_otisk, sc.widgets)
    assert any("vicekrat" in v for v in zapis.varovani)
    assert all(z.widget_id != "ovl1" for z in zapis.zmeny)


def test_bez_otisku_to_rekne():
    with pytest.raises(redline.RedlineError, match="otisk"):
        redline.vytvor(None, [])


# --------------------------------------------------------------------------- #
# Vystup
# --------------------------------------------------------------------------- #


def test_json_nese_obe_soustavy(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    data = redline.na_json(_posun(app, "ovl1", dx=12, dy=-8))
    z = next(x for x in data["zmeny"] if x["widget_id"] == "ovl1")
    assert z["obrazovka"]["po"]["x"] - z["obrazovka"]["pred"]["x"] == 12
    assert z["generator"]["po"]["x"] - z["generator"]["pred"]["x"] == 12
    assert z["generator"]["pred"] == {"x": 44, "y": 332, "w": 240, "h": 88}
    assert z["generator"]["platny"] is True
    assert z["generator"]["neprevedeno"] == []
    assert z["generator"]["rodic"] == "obsah"
    assert data["format"] == "rudy-zapis/2"
    assert data["prevod"]["meta_k_dispozici"] is True


def test_json_u_neprevedeneho_NEMA_cislo_a_neni_platny(make_app, cista_scena_na_disku):
    """Klicova pojistka: nikdy cislo s `platny: true`, kdyz doklad neni."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    data = redline.na_json(_posun(app, "nadpis", dx=4))
    z = next(x for x in data["zmeny"] if x["widget_id"] == "nadpis")
    assert z["generator"]["platny"] is False
    assert z["generator"]["pred"] is None
    assert z["generator"]["po"] is None
    assert set(z["generator"]["neprevedeno"]) == {"x", "y", "w", "h"}


def test_json_pripomina_ztratovost_a_zpusob_prevodu(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    data = redline.na_json(_posun(app, "ovl1", dx=12))
    assert any("NERIKA NIC" in p for p in data["poznamky"])
    assert any("inkoustu" in p for p in data["poznamky"])
    assert data["videno_prvku"] == len(app.tab5_otisk.prvky)


def test_text_ukazuje_obe_soustavy(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    text = redline.jako_text(_posun(app, "ovl1", dx=12, dy=-8))
    assert "obrazovka:" in text
    assert "generator:" in text
    assert "(+12)" in text
    assert "(-8)" in text
    assert "nedosazuj" in text.lower()


def test_text_prazdneho_zapisu(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    text = redline.jako_text(redline.vytvor(app.tab5_otisk, app.state.current_scene().widgets))
    assert "Zadna zmena" in text


def test_text_u_zahlavi_rekne_neprevedeno_a_neuvede_cislo(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    text = redline.jako_text(_posun(app, "nadpis", dx=4))
    radek = next(r for r in text.splitlines() if r.strip().startswith("generator:"))
    assert "neprevedeno" in radek
    assert "-44" not in text


def test_uloz_vyrobi_oba_soubory(make_app, cista_scena_na_disku, tmp_path):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    js, txt = redline.uloz(_posun(app, "ovl1", dx=12), tmp_path)
    assert js.name == "_rudy_zapis_Cista.dc.json"
    assert txt.name == "_rudy_zapis_Cista.dc.txt"
    assert json.loads(js.read_text(encoding="utf-8"))["zmeny"]
    assert "RUDY ZAPIS" in txt.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Hak do editoru
# --------------------------------------------------------------------------- #


def test_vydej_zapise_vedle_sceny(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    zapis = redline.vydej(app)
    assert zapis is not None
    assert len(zapis.zmeny) == 1
    js, txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert js.exists()
    assert txt.exists()


def test_vydej_nese_i_souhrn_validace(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    zapis = redline.vydej(app)
    assert zapis.chyb == 0
    assert zapis.warn > 0
    assert "vrstveni" in (zapis.pocty_nalezu or {})


def test_vydej_pri_ERROR_NEVYDA(make_app, vadna_scena_na_disku):
    """Brana je tataz jako v do_espos.py: jakykoli ERROR = nevydat."""
    app = _app_se_scenou(make_app, vadna_scena_na_disku)
    w = _widget(app, "ovl1")
    w.x = int(w.x) + 12
    assert redline.vydej(app) is None
    js, _txt = redline.cesty_vystupu(vadna_scena_na_disku.parent, "Vadna.dc")
    assert not js.exists()


def test_vydej_kdyz_se_NEZMERILO_take_NEVYDA(make_app, cista_scena_na_disku):
    """Fail-closed: rozbite meridlo neni "zadny nalez"."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    app.designer.current_scene = None  # realna cesta k ValueError v dokument_z_app
    assert redline.vydej(app) is None
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()


def test_vydej_bez_zmeny_nic_nezapise(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    zapis = redline.vydej(app)
    assert zapis is not None
    assert zapis.prazdny is True
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()


def test_vydej_bez_mostu_jen_rekne(make_app):
    app = make_app(size=(256, 128))
    assert redline.vydej(app) is None


def test_vydej_snese_nezapisovatelnou_slozku(make_app, cista_scena_na_disku, tmp_path):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    assert redline.vydej(app, slozka=tmp_path / "neexistuje" / "hloubeji") is None


# --------------------------------------------------------------------------- #
# Klavesa Insert a modalni straze
# --------------------------------------------------------------------------- #


def _stisk_insert(app):
    import pygame

    from cyberpunk_designer import key_handlers

    key_handlers.on_key_down(app, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_INSERT))


def test_klavesa_Insert_vyda_rudy_zapis(make_app, cista_scena_na_disku):
    """Pozitivni kontrola ke strazim nize: bez modalu Insert patch VYDA."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    _stisk_insert(app)
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert js.exists()


def test_Insert_behem_psani_do_inspektoru_NEVYDA(make_app, cista_scena_na_disku):
    """Psani do inspektoru je modalni stav; Insert je tam bezny reflex."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    app.state.inspector_selected_field = "text"
    _stisk_insert(app)
    js, txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()
    assert not txt.exists()


def test_Insert_pod_pripnutou_napovedou_NEVYDA(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    app.show_help_overlay = True
    app._help_pinned = True
    _stisk_insert(app)
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()


def test_polozka_v_kontextovem_menu_vyda_rudy_zapis(make_app, cista_scena_na_disku):
    from cyberpunk_designer import context_menu

    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    polozky = context_menu.ctx_tab5_items(app)
    akce = [a for _, _, a in polozky]
    assert "tab5_rudy_zapis" in akce
    context_menu.execute_context_action(app, "tab5_rudy_zapis")
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert js.exists()


def test_polozky_tab5_se_mimo_tab5_neukazuji(make_app):
    """Protipriklad: v beznem navrhu pro OLED tam nemaji co delat."""
    from cyberpunk_designer import context_menu

    app = make_app(size=(256, 128))
    assert context_menu.ctx_tab5_items(app) == []


def test_prepinace_podkladu_a_nalezu_z_menu(make_app, cista_scena_na_disku):
    from cyberpunk_designer import context_menu

    app = _app_se_scenou(make_app, cista_scena_na_disku)
    app.show_backdrop = True
    context_menu.execute_context_action(app, "tab5_podklad")
    assert app.show_backdrop is False
    context_menu.execute_context_action(app, "tab5_nalezy")
    assert app.show_nalezy is False
    context_menu.execute_context_action(app, "tab5_ramecky_vse")
    assert app.tab5_ramecky_vse is True


# --------------------------------------------------------------------------- #
# Identita zdroje: zmenil se artboard pod editorem?
# --------------------------------------------------------------------------- #
#
# Nalez R4 (etapa 5): klicem patche je `_widget_id` = `trida.index`, tedy
# poradi v `querySelectorAll('*')`. Kdyz generator pribere jediny drivejsi
# prvek, indexy se posunou, otisk uz popisuje jine prvky a rudy zapis vydal
# 62 zmen ze 41 prvku - 14 z nich tvrdilo "Filip to tahl". Nikde pritom
# nerekl, ze se scena pod rukama zmenila.


def _pregeneruj_scenu(cesta: pathlib.Path) -> None:
    """Prepise scenu na disku tak, jak by to udelalo pregenerovani artboardu.

    Prvku je porad stejne, jen `_widget_id` se posunou o jedno mist - presne
    to, co udela jediny novy prvek drive v `querySelectorAll('*')`.
    """
    data = json.loads(cesta.read_text(encoding="utf-8"))
    sc = data["scenes"][next(iter(data["scenes"]))]
    puvodni = [w["_widget_id"] for w in sc["widgets"]]
    posunute = [*puvodni[1:], "novy.99"]
    for w, wid in zip(sc["widgets"], posunute, strict=True):
        w["_widget_id"] = wid
    cesta.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def test_vydej_pri_NEZMENENEM_zdroji_projde(make_app, cista_scena_na_disku):
    """KONTROLNI SKUPINA. Bez ni by "nevydal" nedokazoval nic.

    Pojistka na zmenu zdroje musi umet i druhy smer: kdyz se soubor sceny
    nezmenil, patch odchazi jako driv.
    """
    pred = cista_scena_na_disku.read_bytes()
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)

    zapis = redline.vydej(app)
    assert zapis is not None
    assert len(zapis.zmeny) == 1
    js, txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert js.exists() and txt.exists()
    assert cista_scena_na_disku.read_bytes() == pred  # vydani samo zdroj nesaha


def test_vydej_kdyz_se_scena_na_disku_ZMENILA_NEVYDA(make_app, cista_scena_na_disku):
    """Neshoda otisku = zadny patch, a nahlas."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    _pregeneruj_scenu(cista_scena_na_disku)

    assert redline.vydej(app) is None
    js, txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()
    assert not txt.exists()
    assert tab5_most.DUVOD_ZMENA_ZDROJE in app.dialog_message
    assert "nacti scenu znovu" in app.dialog_message
    assert "_scena_Cista.dc.json" in app.dialog_message


def test_R4_pregenerovany_artboard_by_vydal_vymyslene_zmeny(make_app, cista_scena_na_disku):
    """Doslovna rekonstrukce R4 - a doklad, ze brana zabira prave tam.

    Prvni pulka testu je POZITIVNI KONTROLA nebezpeci: kdyby se rozdil pocital
    bez brany, patch by tvrdil hromadu zmen, ktere se nestaly. Druha pulka
    ukazuje, ze `vydej` z toho nevyda nic.
    """
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    stary_otisk = app.tab5_otisk

    _pregeneruj_scenu(cista_scena_na_disku)
    novy = tab5_most.nacti(cista_scena_na_disku, s_podkladem=False)
    tab5_most.pripoj(app, novy)
    app.tab5_otisk = stary_otisk  # presne stav R4: novy obsah, stary otisk

    slepy = redline.vytvor(stary_otisk, app.state.current_scene().widgets)
    stavy = collections.Counter(z.stav for z in slepy.zmeny)
    assert len(slepy.zmeny) > len(stary_otisk.prvky)  # vic zmen nez prvku
    assert stavy[redline.STAV_POSUNUT] > 0  # "Filip to tahl" - nikdo netahl
    assert stavy[redline.STAV_CHYBI] > 0  # "prvek zmizel" - nezmizel

    assert redline.vydej(app) is None
    js, txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()
    assert not txt.exists()
    assert tab5_most.DUVOD_ZMENA_ZDROJE in app.dialog_message


def test_vydej_kdyz_scena_z_disku_ZMIZI_NEVYDA(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    cista_scena_na_disku.unlink()

    assert redline.vydej(app) is None
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()
    assert "na disku uz neni" in app.dialog_message


def test_vydej_kdyz_se_zmenila_META_NEVYDA(make_app, cista_scena_na_disku):
    """Cisla generatoru v patchi pochazeji z mety - jina meta = jiny patch."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    meta = tab5_most.cesta_meta(cista_scena_na_disku)
    zaznamy = json.loads(meta.read_text(encoding="utf-8"))
    zaznamy[9]["gen"]["left"] = 444  # ovl1: jine inline cislo generatoru
    meta.write_text(json.dumps(zaznamy, ensure_ascii=False), encoding="utf-8")

    assert redline.vydej(app) is None
    js, _txt = redline.cesty_vystupu(cista_scena_na_disku.parent, "Cista.dc")
    assert not js.exists()
    assert "_meta_Cista.dc.json" in app.dialog_message


def test_vydej_kdyz_META_pribyla_NEVYDA(make_app, scena_bez_meta):
    """Scena nactena bez mety; meta se objevila az potom.

    Patch by nesel vydat s cisly generatoru, ktera pri nacteni nebyla videt.
    """
    app = _app_se_scenou(make_app, scena_bez_meta)
    assert app.tab5_otisk.ma_meta is False
    _posun(app, "ovl1", dx=12)
    tab5_most.cesta_meta(scena_bez_meta).write_text(
        CISTA_META.read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert redline.vydej(app) is None
    js, _txt = redline.cesty_vystupu(scena_bez_meta.parent, "Hola.dc")
    assert not js.exists()
    assert "pri nacteni nebyla" in app.dialog_message


def test_vydej_i_pri_zmene_JEN_v_bajtech_NEVYDA(make_app, cista_scena_na_disku):
    """Fail-closed je zamerne prisny: rozhoduje sha souboru, ne geometrie.

    Preformatovany, obsahove tentyz soubor patch zastavi. Je to levnejsi nez
    rozhodovat, ktera zmena je "neskodna" - nacist scenu znovu stoji nic.
    """
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    data = json.loads(cista_scena_na_disku.read_text(encoding="utf-8"))
    cista_scena_na_disku.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert redline.vydej(app) is None
    assert tab5_most.DUVOD_ZMENA_ZDROJE in app.dialog_message


def test_vydej_bez_znameho_zdroje_NEVYDA(make_app, cista_scena_na_disku):
    """Fail-closed: co nejde overit, se nevydava."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _posun(app, "ovl1", dx=12)
    app.tab5_zdroj = None

    assert redline.vydej(app) is None
    assert tab5_most.DUVOD_NEOVERENO in app.dialog_message
