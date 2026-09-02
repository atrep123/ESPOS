"""Profil M5Stack Tab5 (1280x720) v editoru + posouvani platna.

Dve veci, ktere spolu souvisi vic, nez se zda:

1. Profil `tab5_1280x720` musi mit STEJNE rozliseni jako `PROFILE_TAB5` ve
   `tools/validate_design.py`, jinak by editor merilo neco jineho nez brana.
2. Scena 1280x720 se do editoru nevejde ani na monitoru 1920x1080 (paleta,
   inspektor a listy si vezmou svoje). Bez posouvani platna by pravy a dolni
   okraj navrhu nesel editovat vubec - profil by byl k nicemu.

Ke kazde kontrole je pozitivni kontrola: mereni, ktere pri spravne nastavene
situaci nalez SKUTECNE najde. Test, ktery jen "nespadne", nic nedokazuje.
"""

from __future__ import annotations

import itertools

import pygame
import pytest

from cyberpunk_designer import key_handlers, mouse_handlers, windowing
from cyberpunk_designer.constants import PROFILE_ORDER
from cyberpunk_designer.drawing.canvas import draw_canvas
from tools.validate_design import PROFILE_TAB5
from ui_designer import HARDWARE_PROFILES, UIDesigner, WidgetConfig

KLIC = "tab5_1280x720"

# Okno, do ktereho se scena 1280x720 nevejde: vyrez platna vyjde 680x544.
MALE_OKNO = (1000, 600)
VELKE_OKNO = (1920, 1080)


# --------------------------------------------------------------------------- #
# 1. Profil displeje
# --------------------------------------------------------------------------- #


def test_profil_existuje_a_ma_pole():
    assert KLIC in HARDWARE_PROFILES
    p = HARDWARE_PROFILES[KLIC]
    for pole in ("label", "width", "height", "color_depth", "max_fb_kb", "max_flash_kb"):
        assert pole in p, f"profilu chybi pole {pole!r}"
    assert p["width"] == 1280
    assert p["height"] == 720
    assert p["color_depth"] == 16


def test_rozliseni_sedi_s_validatorem():
    """Editor a brana musi merit tentyz panel, jinak si budou odporovat."""
    p = HARDWARE_PROFILES[KLIC]
    assert (p["width"], p["height"]) == (PROFILE_TAB5.match_w, PROFILE_TAB5.match_h)


def test_profil_je_v_nabidce():
    assert KLIC in PROFILE_ORDER


def test_profil_se_aplikuje_na_designer_i_scenu():
    designer = UIDesigner(16, 16)
    designer.create_scene("main")
    vysledek = designer.set_hardware_profile(KLIC)
    assert vysledek is not None
    assert (designer.width, designer.height) == (1280, 720)
    sc = designer.scenes["main"]
    assert (sc.width, sc.height) == (1280, 720)


def test_odhad_zdroju_nehlasi_preplneni():
    """1280*720*2 B = 1800 kB. Na Tab5 to lezi v PSRAM, poplach je falesny."""
    designer = UIDesigner(1280, 720)
    designer.create_scene("main")
    designer.set_hardware_profile(KLIC)
    est = designer.estimate_resources()
    assert est["framebuffer_bytes"] == pytest.approx(1280 * 720 * 2)
    assert est["framebuffer_kb"] == pytest.approx(1800.0)
    assert est["fb_over"] == 0.0, "profil tab5 hlasi preplneni framebufferu"
    assert est["flash_over"] == 0.0


def test_odhad_zdroju_preplneni_UMI_nahlasit():
    """Pozitivni kontrola: se skoupou mezi tentyz vypocet poplach VYDA.

    Bez ni by test vyse prosel i tehdy, kdyby `fb_over` bylo vzdycky nula.
    """
    designer = UIDesigner(1280, 720)
    designer.create_scene("main")
    designer.set_hardware_profile(KLIC)
    est = designer.estimate_resources(profile="tft_480x320")
    assert est["fb_over"] == 1.0


def test_scena_se_vejde_do_meze_profilu():
    p = HARDWARE_PROFILES[KLIC]
    fb = p["width"] * p["height"] * (p["color_depth"] // 8)
    assert fb <= float(p["max_fb_kb"]) * 1024


# --------------------------------------------------------------------------- #
# 2. Posouvani platna - scena, ktera se vejde (chovani se NESMI zmenit)
# --------------------------------------------------------------------------- #


def test_kdyz_se_scena_vejde_nelze_posouvat(make_app):
    app = make_app(size=(256, 128))
    windowing.rebuild_layout(app, window_size=VELKE_OKNO, force_scene_size=False)
    assert windowing.pan_limits(app) == (0, 0)
    assert windowing.pan_by(app, 100, 100) is False
    assert (app.pan_x, app.pan_y) == (0, 0)


def test_bez_posunu_je_pocatek_totozny_s_vyrezem(make_app):
    """scene_origin musi pri nulovem posunu vratit presne scene_rect."""
    app = make_app(size=(256, 128))
    windowing.rebuild_layout(app, window_size=VELKE_OKNO, force_scene_size=False)
    assert windowing.scene_origin(app) == app.scene_rect


# --------------------------------------------------------------------------- #
# 3. Posouvani platna - scena vetsi nez vyrez
# --------------------------------------------------------------------------- #


def _app_tab5(make_app, okno=MALE_OKNO):
    app = make_app(size=(1280, 720))
    windowing.rebuild_layout(app, window_size=okno, force_scene_size=False)
    return app


def test_male_okno_zmensi_vyrez_a_povoli_posun(make_app):
    app = _app_tab5(make_app)
    cr = app.layout.canvas_rect
    assert cr.width < 1280, "vyrez platna se nezmensil, posun by byl mrtvy kod"
    assert cr.height < 720
    max_x, max_y = windowing.pan_limits(app)
    assert max_x > 0 and max_y > 0
    assert max_x == 1280 - app.scene_rect.width
    assert max_y == 720 - app.scene_rect.height


def test_posun_meni_pocatek_sceny(make_app):
    app = _app_tab5(make_app)
    puvod = windowing.scene_origin(app)
    assert windowing.pan_by(app, 120, 40) is True
    posunuty = windowing.scene_origin(app)
    assert posunuty.x == puvod.x - 120
    assert posunuty.y == puvod.y - 40
    assert posunuty.size == puvod.size


def test_posun_se_orizne_na_meze(make_app):
    app = _app_tab5(make_app)
    max_x, max_y = windowing.pan_limits(app)
    windowing.pan_by(app, 10**6, 10**6)
    assert (app.pan_x, app.pan_y) == (max_x, max_y)
    windowing.pan_by(app, -(10**6), -(10**6))
    assert (app.pan_x, app.pan_y) == (0, 0)


def test_prvek_u_praveho_okraje_je_dostupny_az_po_posunu(make_app):
    """Jadro veci: bez posunu se na prvek u x=1200 NEDA kliknout."""
    app = _app_tab5(make_app)
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(type="button", x=1200, y=8, width=64, height=64, text="X"))
    vyrez = app.scene_rect

    # Pozice se pocita z vyrezu a posunu NEZAVISLE na scene_origin - jinak by
    # test sdilel predpoklad s tim, co meri, a vadny prevod by mu propadl.
    bod0 = (vyrez.x - app.pan_x + 1205, vyrez.y - app.pan_y + 13)
    assert not vyrez.collidepoint(bod0), "prvek by mel byt mimo vyrez - test nic nemeri"

    windowing.pan_by(app, 600, 0)
    bod1 = (vyrez.x - app.pan_x + 1205, vyrez.y - app.pan_y + 13)
    assert vyrez.collidepoint(bod1)
    assert app.state.hit_test_at(bod1, windowing.scene_origin(app)) == len(sc.widgets) - 1


def test_zvetseni_okna_vrati_posun_do_mezi(make_app):
    app = _app_tab5(make_app)
    windowing.pan_by(app, 10**6, 10**6)
    assert app.pan_x > 0
    windowing.rebuild_layout(app, window_size=VELKE_OKNO, force_scene_size=False)
    assert windowing.pan_limits(app) == (0, 0)
    assert (app.pan_x, app.pan_y) == (0, 0)


def test_reset_posunu(make_app):
    app = _app_tab5(make_app)
    windowing.pan_by(app, 100, 100)
    assert windowing.reset_pan(app) is True
    assert (app.pan_x, app.pan_y) == (0, 0)
    assert windowing.reset_pan(app) is False


# --------------------------------------------------------------------------- #
# 4. Ovladani posunu (klavesnice, stredni tlacitko)
# --------------------------------------------------------------------------- #


def test_sipky_bez_vyberu_posouvaji_platno(make_app):
    app = _app_tab5(make_app)
    app._set_selection([], anchor_idx=None)
    key_handlers.on_key_down(app, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert app.pan_x > 0
    predtim = app.pan_x
    key_handlers.on_key_down(app, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert app.pan_x < predtim


def test_sipky_s_vyberem_posunou_PRVEK_ne_platno(make_app):
    """Pozitivni kontrola k predchozimu: s vyberem se chovani nesmi zmenit."""
    app = _app_tab5(make_app)
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(type="box", x=100, y=100, width=32, height=32))
    app._set_selection([len(sc.widgets) - 1], anchor_idx=len(sc.widgets) - 1)
    x0 = sc.widgets[-1].x
    key_handlers.on_key_down(app, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert app.pan_x == 0, "platno se posunulo, ackoli byl vyber"
    assert sc.widgets[-1].x > x0


def test_stredni_tlacitko_tahne_platno(make_app):
    app = _app_tab5(make_app)
    cr = app.layout.canvas_rect
    start = (cr.centerx, cr.centery)
    assert windowing.pan_drag_start(app, start) is True
    mouse_handlers.on_mouse_move(app, (start[0] - 50, start[1] - 20), (0, 1, 0))
    assert (app.pan_x, app.pan_y) == (50, 20)
    windowing.pan_drag_end(app)
    assert getattr(app, "_pan_drag_from", None) is None


def test_tazeni_platna_nezacne_kdyz_se_scena_vejde(make_app):
    app = make_app(size=(256, 128))
    windowing.rebuild_layout(app, window_size=VELKE_OKNO, force_scene_size=False)
    cr = app.layout.canvas_rect
    assert windowing.pan_drag_start(app, (cr.centerx, cr.centery)) is False


def test_tazeni_platna_nezacne_mimo_platno(make_app):
    app = _app_tab5(make_app)
    assert windowing.pan_drag_start(app, (-50, -50)) is False


# ---- vlastni PRUBEH tazeni, ne jen jeho zacatek a konec ------------------- #
#
# Do teto chvile se testovalo, ze tazeni SMI zacit a SMI skoncit, ale ne, ze
# se behem nej platno hybe spravne. Mutace, ktera z `pan_drag_move` odstrani
# prepocet pocatku (`app._pan_drag_from = pos`), pak prosla vsemi testy:
# kazdy pohyb by znovu aplikoval CELY odstup od mista stisku, takze by platno
# pod mysi zrychlovalo. Tri kroky po stejnem prirustku to odhali.


def _tri_kroky(app, start, krok_x, krok_y):
    ven = []
    for i in (1, 2, 3):
        windowing.pan_drag_move(app, (start[0] - krok_x * i, start[1] - krok_y * i))
        ven.append((app.pan_x, app.pan_y))
    return ven


def test_tazeni_platna_je_PRIRUSTKOVE_ne_zrychlujici(make_app):
    """Stejny prirustek kurzoru = stejny prirustek posunu, porad dokola."""
    app = _app_tab5(make_app)
    cr = app.layout.canvas_rect
    start = (cr.centerx, cr.centery)
    assert windowing.pan_drag_start(app, start) is True

    kroky = _tri_kroky(app, start, 10, 5)
    assert kroky == [(10, 5), (20, 10), (30, 15)], (
        "posun neodpovida prirustku kurzoru - platno zrychluje"
    )
    # a rozdily mezi kroky jsou konstantni, ne rostouci
    rozdily = [(b[0] - a[0], b[1] - a[1]) for a, b in itertools.pairwise(kroky)]
    assert rozdily == [(10, 5), (10, 5)]


def test_tazeni_zpet_vrati_platno_tam_kde_bylo(make_app):
    """Protipriklad: kdyby se pocatek neprepocital, cesta zpet by nic neudelala."""
    app = _app_tab5(make_app)
    cr = app.layout.canvas_rect
    start = (cr.centerx, cr.centery)
    windowing.pan_drag_start(app, start)
    windowing.pan_drag_move(app, (start[0] - 40, start[1] - 16))
    assert (app.pan_x, app.pan_y) == (40, 16)
    windowing.pan_drag_move(app, start)
    assert (app.pan_x, app.pan_y) == (0, 0)


def test_pan_drag_move_bez_zahajeni_nic_nedela(make_app):
    app = _app_tab5(make_app)
    assert windowing.pan_drag_move(app, (10, 10)) is False
    assert (app.pan_x, app.pan_y) == (0, 0)


def test_pan_drag_move_po_ukonceni_uz_netahne(make_app):
    app = _app_tab5(make_app)
    cr = app.layout.canvas_rect
    start = (cr.centerx, cr.centery)
    windowing.pan_drag_start(app, start)
    windowing.pan_drag_move(app, (start[0] - 30, start[1]))
    windowing.pan_drag_end(app)
    assert windowing.pan_drag_move(app, (start[0] - 100, start[1])) is False
    assert app.pan_x == 30


def test_tazeni_na_doraz_se_zastavi_na_mezi(make_app):
    """Meze plati i behem tazeni - platno neutece za scenu."""
    app = _app_tab5(make_app)
    cr = app.layout.canvas_rect
    start = (cr.centerx, cr.centery)
    max_x, max_y = windowing.pan_limits(app)
    windowing.pan_drag_start(app, start)
    windowing.pan_drag_move(app, (start[0] - 100000, start[1] - 100000))
    assert (app.pan_x, app.pan_y) == (max_x, max_y)


# --------------------------------------------------------------------------- #
# 5. Posun a EDITACE musi mluvit stejnou soustavou souradnic
# --------------------------------------------------------------------------- #


def test_tazeni_prvku_po_posunu_ma_spravne_souradnice(make_app):
    """Kdyby mys a obraz pouzivaly jiny pocatek, prvek by skocil o pan."""
    app = _app_tab5(make_app)
    app.snap_enabled = False
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(type="box", x=700, y=200, width=48, height=48))
    idx = len(sc.widgets) - 1
    windowing.pan_by(app, 400, 100)

    vyrez = app.scene_rect
    app._set_selection([idx], anchor_idx=idx)
    app.pointer_down = True
    app.state.dragging = True
    app.state.drag_offset = (4, 4)
    app.state.drag_start_rect = pygame.Rect(700, 200, 48, 48)
    app.state.drag_start_positions = {idx: (700, 200)}

    # Kurzor na scenickou souradnici (750, 240) => prvek na (746, 236).
    # Souradnice na platne se pocita z vyrezu a posunu, ne pres scene_origin:
    # kdyby ji test bral z tehoz mista jako kod, vadny prevod by neodhalil.
    kurzor = (vyrez.x - app.pan_x + 750, vyrez.y - app.pan_y + 240)
    mouse_handlers.on_mouse_move(app, kurzor, (1, 0, 0))
    assert (sc.widgets[idx].x, sc.widgets[idx].y) == (746, 236)


def test_kresleni_s_posunem_nespadne(make_app):
    app = _app_tab5(make_app)
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(type="label", x=1100, y=600, width=120, height=40, text="ok"))
    app.show_grid = True
    app.show_rulers = True
    app.show_center_guides = True
    windowing.pan_by(app, 300, 120)
    draw_canvas(app)


def test_kresleni_prvku_respektuje_posun(make_app):
    """Widget se po posunu musi vykreslit o `pan` jinam, ne na miste."""
    app = _app_tab5(make_app)
    app.show_grid = False
    app.show_rulers = False
    sc = app.state.current_scene()
    sc.widgets.append(
        WidgetConfig(type="box", x=200, y=100, width=64, height=64, color_bg="#00ff00")
    )
    vyrez = app.scene_rect
    draw_canvas(app)
    pred = app.logical_surface.get_at((vyrez.x + 200 + 5, vyrez.y + 100 + 5))[:3]

    windowing.pan_by(app, 64, 0)
    draw_canvas(app)
    po = app.logical_surface.get_at((vyrez.x + 200 + 5, vyrez.y + 100 + 5))[:3]
    posunuty = app.logical_surface.get_at((vyrez.x + 200 - 64 + 5, vyrez.y + 100 + 5))[:3]
    assert pred != po, "obraz se posunem nezmenil"
    assert posunuty == pred, "prvek se neposunul o presne pan_x"


def test_podklad_se_kresli_jen_kdyz_je_zapnuty(make_app):
    """Podklad (etapa 2) lezi pod mrizkou a da se vypnout."""
    app = _app_tab5(make_app)
    podklad = pygame.Surface((1280, 720))
    podklad.fill((255, 0, 0))
    app.backdrop_surface = podklad
    app.show_grid = False
    app.show_backdrop = True
    draw_canvas(app)
    o = windowing.scene_origin(app)
    assert app.logical_surface.get_at((o.x + 5, o.y + 5))[:3] == (255, 0, 0)

    app.show_backdrop = False
    draw_canvas(app)
    assert app.logical_surface.get_at((o.x + 5, o.y + 5))[:3] != (255, 0, 0)
