"""Most artboard TabOSu -> editor ESPOS (`cyberpunk_designer/tab5_most.py`).

Tri veci, ktere se tu meri, a ke kazde pozitivni kontrola:

1. Scena se nacte CELA (pocet prvku sedi) - a kdyz nesedi, most to REKNE.
   `UIDesigner.load_from_json` totiz pri chybe tise podstrci prazdnou scenu.
2. `device` prezije do dokumentu pro validator - a je dolozeno, ze na nem
   zalezi: bez nej spadne validator na profil OLED 256x128 a dotykove meze
   i znakova sada se ZMENI.
3. Podklad se nacte a vykresli - a da se vypnout.
4. `_meta_X.json` (inline styl generatoru) se nacte, kdyz je - a kdyz neni,
   otisk to PRIZNA (`ma_meta = False`), aby rudy zapis zadne cislo nevydal.
   Rozbita meta se nesmi tvarit jako zadna.
5. Otisk si pamatuje IDENTITU zdroje (sha256 sceny i mety) a `overi_zdroj`
   pozna, ze se soubor pod editorem zmenil - a ke kazdemu "nepusti" je tu
   protipriklad "pusti", jinak by pojistka mohla odmitat vzdycky.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import pygame
import pytest

from cyberpunk_designer import tab5_most, windowing
from cyberpunk_designer.drawing.canvas import draw_canvas
from tools.validate_design import validate_data
from ui_designer import UIDesigner

FIXTURA_TAB5 = pathlib.Path(__file__).parent / "fixtures" / "tab5_clean.json"

# Scena ve tvaru, v jakem ji vyrabi navrh-appky/do_espos.py: korenovy klic
# `device`, 1280x720 a `_widget_id` ve tvaru `trida.index`.
SCENA = {
    "device": "tab5",
    "width": 1280,
    "height": 720,
    "groups": {},
    "scenes": {
        "main": {
            "name": "SvorkaTest.dc",
            "width": 1280,
            "height": 720,
            "bg_color": "#14170f",
            "widgets": [
                {
                    "type": "label",
                    "x": 20,
                    "y": 24,
                    "width": 148,
                    "height": 19,
                    "text": "LOGIC ANALYZER",
                    "color_fg": "#a9c24a",
                    "color_bg": "#14170f",
                    "border": False,
                    "border_style": "none",
                    "align": "left",
                    "valign": "middle",
                    "_widget_id": "titulek.8",
                },
                {
                    "type": "button",
                    "x": 64,
                    "y": 88,
                    "width": 124,
                    "height": 82,
                    "text": "START",
                    "color_fg": "#14170f",
                    "color_bg": "#e6e1ce",
                    "border": True,
                    "border_style": "single",
                    "align": "left",
                    "valign": "middle",
                    "_widget_id": "ovl_hlavni.15",
                },
                {
                    "type": "panel",
                    "x": 44,
                    "y": 200,
                    "width": 1160,
                    "height": 300,
                    "text": "",
                    "color_fg": "#e6e1ce",
                    "color_bg": "#1b1f14",
                    "border": True,
                    "border_style": "single",
                    "align": "left",
                    "valign": "middle",
                    "_widget_id": "zona.107",
                },
            ],
        }
    },
}


@pytest.fixture
def scena_na_disku(tmp_path):
    """Zapise scenu pod jmenem, ktere pouziva prevodnik."""
    cesta = tmp_path / "_scena_SvorkaTest.dc.json"
    cesta.write_text(json.dumps(SCENA, ensure_ascii=False, indent=1), encoding="utf-8")
    return cesta


META = [
    {
        "_widget_id": "titulek.8",
        "box": [20, 20, 148, 26],
        "gen": {"left": None, "top": None, "width": None, "height": None},
        "rodic": "zahlavi",
        "v_obsahu": False,
    },
    {
        "_widget_id": "ovl_hlavni.15",
        "box": [64, 88, 124, 82],
        "gen": {"left": 44, "top": 20, "width": 124, "height": 82},
        "rodic": "obsah",
        "v_obsahu": True,
    },
]


@pytest.fixture
def scena_s_meta(scena_na_disku):
    tab5_most.cesta_meta(scena_na_disku).write_text(
        json.dumps(META, ensure_ascii=False), encoding="utf-8"
    )
    return scena_na_disku


def _uloz_podklad(cesta: pathlib.Path, barva=(255, 0, 0)) -> pathlib.Path:
    """Vyrobi maly PNG podklad. Do gitu snimky nepatri, tak vznika za behu."""
    plocha = pygame.Surface((1280, 720))
    plocha.fill(barva)
    pygame.image.save(plocha, str(cesta))
    return cesta


# --------------------------------------------------------------------------- #
# 1. Nacteni sceny
# --------------------------------------------------------------------------- #


def test_nacteni_fixtury_zachova_pocet_prvku(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    sc = most.designer.scenes[most.designer.current_scene]
    assert len(sc.widgets) == len(SCENA["scenes"]["main"]["widgets"]) == 3
    assert len(most.otisk.prvky) == 3


def test_nacteni_nastavi_profil_a_rozmer(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    assert most.designer.hardware_profile == tab5_most.PROFIL_TAB5
    assert (most.designer.width, most.designer.height) == (1280, 720)
    sc = most.designer.scenes[most.designer.current_scene]
    assert (sc.width, sc.height) == (1280, 720)


def test_device_prezije_v_otisku(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    assert most.otisk.device == "tab5"
    assert most.otisk.scena == "SvorkaTest.dc"


def test_save_to_json_device_ZAHODI(scena_na_disku, tmp_path):
    """Pozitivni kontrola k predchozimu: past je skutecna, ne domnela.

    Kdyby `save_to_json` klic `device` zachoval, byl by otisk zbytecny.
    Az tenhle test dela z komentare v modulu dolozene tvrzeni.
    """
    designer = UIDesigner(1280, 720)
    designer.load_from_json(str(scena_na_disku))
    ven = tmp_path / "ulozeno.json"
    designer.save_to_json(str(ven))
    assert "device" not in json.loads(ven.read_text(encoding="utf-8"))


def test_otisk_si_pamatuje_puvodni_souradnice(scena_na_disku):
    """Bez toho by se v etape 4 nedalo poznat, co se posunulo."""
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    sc = most.designer.scenes[most.designer.current_scene]
    sc.widgets[1].x += 12
    puvodni = most.otisk.podle_id()["ovl_hlavni.15"]
    assert puvodni.obdelnik == (64, 88, 124, 82)
    assert sc.widgets[1].x == 76


def test_chybejici_scena_vyhodi_MostError(tmp_path):
    with pytest.raises(tab5_most.MostError):
        tab5_most.nacti(tmp_path / "neexistuje.json")


def test_rozbity_json_vyhodi_MostError(tmp_path):
    cesta = tmp_path / "_scena_X.json"
    cesta.write_text("{tohle neni json", encoding="utf-8")
    with pytest.raises(tab5_most.MostError):
        tab5_most.nacti(cesta)


def test_json_bez_scen_vyhodi_MostError(tmp_path):
    cesta = tmp_path / "_scena_X.json"
    cesta.write_text(json.dumps({"width": 1280, "height": 720, "scenes": {}}), encoding="utf-8")
    with pytest.raises(tab5_most.MostError):
        tab5_most.nacti(cesta)


def test_neuplne_nacteni_se_NEPREJDE_mlcky(scena_na_disku, monkeypatch):
    """Pozitivni kontrola pojistky: kdyz designer prvky ztrati, most krici.

    Tichy fallback `load_from_json` na prazdnou scenu je presne to, co by
    vypadalo jako "artboard je prazdny" misto "nacteni selhalo".
    """

    def okleste(self, filename):
        self.width, self.height = 1280, 720
        self.scenes.clear()
        self.create_scene("main")
        self.current_scene = "main"

    monkeypatch.setattr(UIDesigner, "load_from_json", okleste)
    with pytest.raises(tab5_most.MostError, match="nacteno 0 prvku"):
        tab5_most.nacti(scena_na_disku, s_podkladem=False)


def test_json_ktery_neni_navrh_vyhodi_MostError(tmp_path):
    cesta = tmp_path / "_scena_X.json"
    cesta.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(tab5_most.MostError, match="tvar navrhu"):
        tab5_most.nacti(cesta)


def test_scena_ktera_neni_slovnik_vyhodi_MostError(tmp_path):
    cesta = tmp_path / "_scena_X.json"
    cesta.write_text(json.dumps({"scenes": {"main": "tohle neni slovnik"}}), encoding="utf-8")
    with pytest.raises(tab5_most.MostError, match="neni slovnik"):
        tab5_most.nacti(cesta)


def test_prazdny_designer_vyhodi_MostError(scena_na_disku, monkeypatch):
    """Kdyz designer nenacte ani scenu, most to nesmi vydat za prazdny navrh."""

    def nic(self, filename):
        self.scenes.clear()
        self.current_scene = None

    monkeypatch.setattr(UIDesigner, "load_from_json", nic)
    with pytest.raises(tab5_most.MostError, match="nenacetl"):
        tab5_most.nacti(scena_na_disku, s_podkladem=False)


def test_otisk_preskoci_prvek_ktery_neni_slovnik():
    data = copy.deepcopy(SCENA)
    data["scenes"]["main"]["widgets"].append("smeti")
    otisk = tab5_most.otisk_z_dat(data)
    assert len(otisk.prvky) == 3


def test_otisk_dosadi_device_kdyz_chybi():
    data = copy.deepcopy(SCENA)
    data.pop("device")
    assert tab5_most.otisk_z_dat(data).device == "tab5"


# --------------------------------------------------------------------------- #
# 2. Dokument pro validator
# --------------------------------------------------------------------------- #


def test_dokument_vzdy_nese_device(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    d = tab5_most.dokument(most)
    assert d["device"] == "tab5"
    assert d["width"] == 1280 and d["height"] == 720
    assert len(d["scenes"]["main"]["widgets"]) == 3
    assert d["scenes"]["main"]["widgets"][1]["_widget_id"] == "ovl_hlavni.15"


def test_dokument_bez_aktivni_sceny_vyhodi_MostError(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    most.designer.current_scene = None
    with pytest.raises(tab5_most.MostError, match="aktivni scenu"):
        tab5_most.dokument(most)


def test_dokument_projde_validatorem_bez_chyb(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    nalezy = validate_data(tab5_most.dokument(most), file_label="most", warnings_as_errors=False)
    assert [i for i in nalezy if i.level == "ERROR"] == []


def test_na_device_ZALEZI(scena_na_disku):
    """Pozitivni kontrola: bez `device` meri validator jiny panel.

    Pri rozmeru, ktery zadnemu profilu neodpovida, spadne `_profile_for` na
    OLED 256x128: dotykove meze zmizi (ppi=0) a znakova sada zacne hlasit
    znaky, ktere Montserrat ma. A NIC to nenahlasi - proto ta pojistka.
    """
    zaklad = json.loads(FIXTURA_TAB5.read_text(encoding="utf-8"))
    zaklad["width"] = zaklad["height"] = 999
    zaklad["scenes"]["main"]["width"] = zaklad["scenes"]["main"]["height"] = 999

    s_device = copy.deepcopy(zaklad)
    s_device["device"] = "tab5"
    bez_device = copy.deepcopy(zaklad)
    bez_device.pop("device", None)

    def znaky(data):
        return sum(
            1
            for i in validate_data(data, file_label="t", warnings_as_errors=False)
            if "unsupported chars" in i.message
        )

    assert znaky(bez_device) != znaky(s_device), (
        "profil se bez `device` nezmenil - tenhle test uz nic nemeri"
    )


# --------------------------------------------------------------------------- #
# 3. Podklad
# --------------------------------------------------------------------------- #


def test_jmeno_podkladu_odvozene_ze_sceny(tmp_path):
    scena = tmp_path / "_scena_SvorkaLA.dc.json"
    assert tab5_most.cesta_podkladu(scena).name == "_snimek_SvorkaLA.dc.png"


def test_podklad_se_nacte_kdyz_je(scena_na_disku):
    _uloz_podklad(tab5_most.cesta_podkladu(scena_na_disku))
    most = tab5_most.nacti(scena_na_disku)
    assert most.podklad is not None
    assert most.podklad.get_size() == (1280, 720)
    assert most.cesta_podkladu is not None


def test_chybejici_podklad_neni_chyba(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku)
    assert most.podklad is None
    assert most.cesta_podkladu is None


def test_poskozeny_podklad_neshodi_nacteni(scena_na_disku):
    cesta = tab5_most.cesta_podkladu(scena_na_disku)
    cesta.write_bytes(b"tohle neni PNG")
    most = tab5_most.nacti(scena_na_disku)
    assert most.podklad is None


# --------------------------------------------------------------------------- #
# 4. Pripojeni k editoru
# --------------------------------------------------------------------------- #


def test_pripojeni_preveze_scenu_profil_i_podklad(make_app, scena_na_disku):
    _uloz_podklad(tab5_most.cesta_podkladu(scena_na_disku))
    most = tab5_most.nacti(scena_na_disku)
    app = make_app(size=(256, 128))
    tab5_most.pripoj(app, most)

    assert app.hardware_profile == tab5_most.PROFIL_TAB5
    assert (app.designer.width, app.designer.height) == (1280, 720)
    assert len(app.state.current_scene().widgets) == 3
    assert app.tab5_otisk is most.otisk
    assert app.backdrop_surface is not None
    assert app.show_backdrop is True
    assert (app.pan_x, app.pan_y) == (0, 0)


def test_podklad_se_opravdu_vykresli(make_app, scena_na_disku):
    _uloz_podklad(tab5_most.cesta_podkladu(scena_na_disku), barva=(255, 0, 0))
    most = tab5_most.nacti(scena_na_disku)
    app = make_app(size=(256, 128))
    tab5_most.pripoj(app, most)
    app.show_grid = False
    app.show_rulers = False

    o = windowing.scene_origin(app)
    # Bod, na kterem v teto scene zadny widget nelezi.
    bod = (o.x + 900, o.y + 650)

    draw_canvas(app)
    assert app.logical_surface.get_at(bod)[:3] == (255, 0, 0)

    assert tab5_most.prepni_podklad(app) is False
    draw_canvas(app)
    assert app.logical_surface.get_at(bod)[:3] != (255, 0, 0)

    assert tab5_most.prepni_podklad(app) is True
    draw_canvas(app)
    assert app.logical_surface.get_at(bod)[:3] == (255, 0, 0)


def test_podklad_lezi_POD_widgety(make_app, scena_na_disku):
    """Podklad je podklad, ne prekryv: widget na nem musi byt videt."""
    _uloz_podklad(tab5_most.cesta_podkladu(scena_na_disku), barva=(255, 0, 0))
    most = tab5_most.nacti(scena_na_disku)
    app = make_app(size=(256, 128))
    tab5_most.pripoj(app, most)
    app.show_grid = False
    app.show_rulers = False
    draw_canvas(app)

    o = windowing.scene_origin(app)
    # Vnitrek panelu `zona.107` (44, 200, 1160x300).
    uvnitr = (o.x + 500, o.y + 350)
    assert app.logical_surface.get_at(uvnitr)[:3] != (255, 0, 0)


def test_pripojeni_bez_podkladu_ho_nezapne(make_app, scena_na_disku):
    most = tab5_most.nacti(scena_na_disku)
    app = make_app(size=(256, 128))
    tab5_most.pripoj(app, most)
    assert app.backdrop_surface is None
    assert app.show_backdrop is False


def test_pripojeni_snese_i_chudy_objekt(scena_na_disku):
    """Obranne vetve v `pripoj` nesmi shodit volajiciho."""
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)

    class Chudy:
        designer = UIDesigner(16, 16)

    chudy = Chudy()
    tab5_most.pripoj(chudy, most)
    assert chudy.hardware_profile == tab5_most.PROFIL_TAB5
    assert chudy.show_backdrop is False


# --------------------------------------------------------------------------- #
# Meta pro rudy zapis (inline styl generatoru)
# --------------------------------------------------------------------------- #


def test_cesta_meta_lezi_vedle_sceny(tmp_path):
    cesta = tmp_path / "_scena_SvorkaLA.dc.json"
    assert tab5_most.cesta_meta(cesta).name == "_meta_SvorkaLA.dc.json"
    assert tab5_most.cesta_meta(cesta).parent == tmp_path


def test_meta_se_nacte_a_prvky_nesou_cislo_generatoru(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    assert most.otisk.ma_meta is True
    prvky = most.otisk.podle_id()

    ovl = prvky["ovl_hlavni.15"]
    assert ovl.gen == (44, 20, 124, 82)
    assert ovl.rodic == "obsah"
    assert ovl.v_obsahu is True
    assert ovl.box == (64, 88, 124, 82)

    # zahlavi: generator k nemu zadne inline cislo nezapsal
    assert prvky["titulek.8"].gen == (None, None, None, None)
    assert prvky["titulek.8"].rodic == "zahlavi"


def test_bez_meta_to_otisk_PRIZNA(scena_na_disku):
    """Protipriklad: chybejici meta neni chyba, ale nesmi se zamlcet."""
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    assert most.otisk.ma_meta is False
    assert all(p.gen == (None, None, None, None) for p in most.otisk.prvky)


def test_rozbita_meta_je_CHYBA_ne_zadna_meta(scena_na_disku):
    """Tichy propad na "zadnou metu" by vratil stav, ktery revize A vyvratila."""
    tab5_most.cesta_meta(scena_na_disku).write_text("{tohle neni JSON", encoding="utf-8")
    with pytest.raises(tab5_most.MostError, match="meta"):
        tab5_most.nacti(scena_na_disku, s_podkladem=False)


def test_meta_musi_byt_seznam(scena_na_disku):
    tab5_most.cesta_meta(scena_na_disku).write_text('{"a": 1}', encoding="utf-8")
    with pytest.raises(tab5_most.MostError, match="seznam"):
        tab5_most.nacti(scena_na_disku, s_podkladem=False)


def test_meta_bez_zaznamu_k_prvku_necislovana_nechava(scena_na_disku):
    """Prvek, ktery v mete neni, zustava bez cisla - nedopocitava se."""
    tab5_most.cesta_meta(scena_na_disku).write_text(
        json.dumps([META[1]], ensure_ascii=False), encoding="utf-8"
    )
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    prvky = most.otisk.podle_id()
    assert prvky["ovl_hlavni.15"].gen == (44, 20, 124, 82)
    assert prvky["titulek.8"].gen == (None, None, None, None)


def test_meta_s_nesmyslnymi_hodnotami_se_neprevede_na_cislo(scena_na_disku):
    vadna = [
        {
            "_widget_id": "ovl_hlavni.15",
            "box": "neni seznam",
            "gen": {"left": "44px", "top": True, "width": None, "height": 82},
            "rodic": "obsah",
        }
    ]
    tab5_most.cesta_meta(scena_na_disku).write_text(
        json.dumps(vadna, ensure_ascii=False), encoding="utf-8"
    )
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    prvek = most.otisk.podle_id()["ovl_hlavni.15"]
    assert prvek.box is None
    # retezec ani bool nejsou cislo generatoru
    assert prvek.gen == (None, None, None, 82)


# --------------------------------------------------------------------------- #
# 5. Identita zdroje
# --------------------------------------------------------------------------- #
#
# `_widget_id` je `trida.index`. Kdyz se artboard pod editorem pregeneruje,
# indexy se posunou a rozdil proti otisku vyda vymyslene zmeny (etapa 5,
# nalez R4: 62 zmen ze 41 prvku). Jedina cesta, jak to poznat KONSTRUKCI,
# je pamatovat si, ze ktereho souboru otisk vznikl.


def _sha(cesta: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(cesta).read_bytes()).hexdigest()


def test_otisk_souboru_je_sha256_bajtu(tmp_path):
    cesta = tmp_path / "soubor.bin"
    cesta.write_bytes(b"tab5")
    assert tab5_most.otisk_souboru(cesta) == hashlib.sha256(b"tab5").hexdigest()


def test_otisk_souboru_vraci_None_kdyz_soubor_neni(tmp_path):
    assert tab5_most.otisk_souboru(tmp_path / "neni.json") is None


def test_otisk_souboru_neprecteny_soubor_NENI_zadny_soubor(tmp_path):
    """Selhani cteni se nesmi tvarit jako "soubor neexistuje" - to je tichy propad."""
    slozka = tmp_path / "_scena_Slozka.dc.json"
    slozka.mkdir()
    with pytest.raises(tab5_most.MostError):
        tab5_most.otisk_souboru(slozka)


def test_otisk_nese_sha_sceny_i_mety(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    assert most.otisk.sha_sceny == _sha(scena_s_meta)
    assert most.otisk.sha_meta == _sha(tab5_most.cesta_meta(scena_s_meta))
    assert most.otisk.ma_meta is True


def test_otisk_bez_mety_ma_sha_meta_None(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    assert most.otisk.sha_sceny == _sha(scena_na_disku)
    assert most.otisk.sha_meta is None
    assert most.otisk.ma_meta is False


def test_overi_zdroj_PUSTI_nezmeneny_soubor(scena_s_meta):
    """KONTROLNI SKUPINA: pojistka, ktera odmita vzdycky, nemeri nic."""
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    assert tab5_most.overi_zdroj(most.otisk, scena_s_meta) is None


def test_overi_zdroj_pozna_zmenenou_scenu(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    data = json.loads(scena_s_meta.read_text(encoding="utf-8"))
    data["scenes"]["main"]["widgets"][1]["_widget_id"] = "ovl_hlavni.16"
    scena_s_meta.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    duvod = tab5_most.overi_zdroj(most.otisk, scena_s_meta)
    assert duvod is not None
    assert tab5_most.DUVOD_ZMENA_ZDROJE in duvod
    assert "_scena_SvorkaTest.dc.json" in duvod


def test_overi_zdroj_pozna_zmizely_soubor(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    scena_s_meta.unlink()
    duvod = tab5_most.overi_zdroj(most.otisk, scena_s_meta)
    assert duvod is not None
    assert "na disku uz neni" in duvod


def test_overi_zdroj_pozna_zmenenou_metu(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    cesta = tab5_most.cesta_meta(scena_s_meta)
    zaznamy = json.loads(cesta.read_text(encoding="utf-8"))
    zaznamy[1]["gen"]["left"] = 999
    cesta.write_text(json.dumps(zaznamy, ensure_ascii=False), encoding="utf-8")

    duvod = tab5_most.overi_zdroj(most.otisk, scena_s_meta)
    assert duvod is not None
    assert "_meta_SvorkaTest.dc.json" in duvod


def test_overi_zdroj_pozna_zmizelou_metu(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    tab5_most.cesta_meta(scena_s_meta).unlink()
    duvod = tab5_most.overi_zdroj(most.otisk, scena_s_meta)
    assert duvod is not None
    assert "pri nacteni byla, ted na disku neni" in duvod


def test_overi_zdroj_pozna_pribylou_metu(scena_na_disku):
    most = tab5_most.nacti(scena_na_disku, s_podkladem=False)
    tab5_most.cesta_meta(scena_na_disku).write_text(
        json.dumps(META, ensure_ascii=False), encoding="utf-8"
    )
    duvod = tab5_most.overi_zdroj(most.otisk, scena_na_disku)
    assert duvod is not None
    assert "pri nacteni nebyla, ted na disku je" in duvod


def test_overi_zdroj_bez_sha_NEPUSTI():
    """Otisk z dat (ne ze souboru) overit nejde - fail-closed."""
    otisk = tab5_most.otisk_z_dat(SCENA, zdroj="_scena_SvorkaTest.dc.json")
    assert otisk.sha_sceny == ""
    duvod = tab5_most.overi_zdroj(otisk, "_scena_SvorkaTest.dc.json")
    assert duvod is not None
    assert tab5_most.DUVOD_NEOVERENO in duvod


def test_overi_zdroj_bez_cesty_NEPUSTI(scena_s_meta):
    most = tab5_most.nacti(scena_s_meta, s_podkladem=False)
    duvod = tab5_most.overi_zdroj(most.otisk, None)
    assert duvod is not None
    assert tab5_most.DUVOD_NEOVERENO in duvod


def test_overi_zdroj_bez_otisku_NEPUSTI(scena_s_meta):
    duvod = tab5_most.overi_zdroj(None, scena_s_meta)
    assert duvod is not None
    assert tab5_most.DUVOD_NEOVERENO in duvod


def test_overi_zdroj_neprecteny_soubor_NEPUSTI(tmp_path):
    """Rozbite meridlo neni "nic se nezmenilo"."""
    slozka = tmp_path / "_scena_Slozka.dc.json"
    slozka.mkdir()
    otisk = tab5_most.Otisk(
        zdroj=slozka.name,
        scena="Slozka.dc",
        device="tab5",
        width=1280,
        height=720,
        sha_sceny="ab" * 32,
    )
    duvod = tab5_most.overi_zdroj(otisk, slozka)
    assert duvod is not None
    assert tab5_most.DUVOD_NEOVERENO in duvod
