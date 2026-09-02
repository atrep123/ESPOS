"""Validace sceny artboardu v editoru (`cyberpunk_designer/tab5_validace.py`).

Ctyri veci, ktere se tu meri, a ke kazde POZITIVNI kontrola:

1. Adapter nalez SKUTECNE najde. Test proti `tests/fixtures/tab5_defects.json`
   trva na konkretnim ERRORu (dotykovy cil) a na konkretnich WARN (znaky,
   kontrast, kolize) - ne jen na tom, ze "to neselhalo". Protipolem je
   `tab5_clean.json`, kde nesmi byt ANI JEDEN ERROR.
2. Editor meri TOTEZ co brana. Vedle behu v pameti se pousti i CLI validator
   jako podproces a obe cesty musi dat tytez klasifikovane zpravy - VCETNE
   JSON-schema, kterou brana pousti pres `validate_file` a adapter ji drive
   vynechaval (dva dolozene rozchody: `groups` jako seznam a klic navic
   u widgetu). Podproces dostava `PYTHONIOENCODING=utf-8` presne jako brana
   a kontroluje se jeho NAVRATOVY KOD: bez toho validator na cp1250 spadl na
   `UnicodeEncodeError` po prvnim radku a test porovnaval useknuty vypis.
3. Deduplikace srazi vic hlaseni tehoz na jedno - a je dolozeno, ze nejakou
   dvojici opravdu srazi (jinak by test "sedi to" prosel i kdyby dedup vubec
   nic nedelal).
4. Trida `vrstveni` se nekresli, ale POCITA. Obe strany maji vlastni test.
5. `TRIDY` se hlida BEHOVOU hodnotou z `do_espos.py`, ne jen literalem ve
   zdroji. Ctyri obchazky (`append`, `+=`, druhe prirazeni, `TRIDY[0] = ...`)
   maji vlastni mutacni test.
6. Brana je FAIL-CLOSED: kdyz se nezmerilo, nevydava se. Pozitivni kontrola
   jde realnou cestou (`designer nema aktivni scenu`), ne umelou zaplatou.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

from cyberpunk_designer import io_ops, mouse_handlers, tab5_most, tab5_validace
from cyberpunk_designer.drawing.canvas import draw_canvas
from cyberpunk_designer.drawing.overlays import draw_nalezy
from ui_designer import WidgetConfig

FIXTURY = pathlib.Path(__file__).parent / "fixtures"
CISTA = FIXTURY / "tab5_clean.json"
VADNA = FIXTURY / "tab5_defects.json"
KOREN = pathlib.Path(__file__).resolve().parents[1]

# `do_espos.py` lezi v jinem pracovnim strome (tabos-ui-kit). Kdyz tam neni,
# testy shody tridy se preskoci - ale nikdy se nepreskoci to, co lze zmerit
# uvnitr ESPOSu.
DO_ESPOS = KOREN.parents[1] / "tabos-ui-kit" / "navrh-appky" / "do_espos.py"


def _data(cesta: pathlib.Path) -> dict:
    return json.loads(cesta.read_text(encoding="utf-8"))


_UROVEN_RE = re.compile(r"^\[(ERROR|WARN)\]\s*")


def _cli_nalezy(cesta: pathlib.Path):
    """Pusti validator jako PODPROCES - tedy toutez cestou jako brana.

    `PYTHONIOENCODING=utf-8` je doslovna kopie hraze z `do_espos.main()`.
    Bez ni validator na Windows (cp1250) spadne na znaku `U+2194` uprostred
    vypisu, vytiskne jediny radek a skonci kodem 1 - k nerozeznani od
    "dobehl a nasel chyby". Proto se kod kontroluje.

    Vraci `(returncode, [(uroven, zprava), ...])` po deduplikaci klicem
    z `do_espos.py`. Uroven se z radku odrizne, aby se zpravy daly porovnat
    s tim, co ma adapter v `Nalez.zprava` - schema hlasky totiz nemaji
    prefix `scene '...': `, ktery by `bez_prefixu` jinak useknul.
    """
    hot = subprocess.run(
        [sys.executable, str(KOREN / "tools" / "validate_design.py"), str(cesta)],
        capture_output=True,
        cwd=str(KOREN),
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        timeout=180,
        check=False,
    )
    txt = (hot.stdout + hot.stderr).decode("utf-8", "replace")
    videno: set = set()
    ven = []
    for radek in txt.splitlines():
        if ("ERROR" not in radek and "WARN" not in radek) or "warning(s)" in radek:
            continue
        uroven = "ERROR" if radek.strip().startswith("[ERROR]") else "WARN"
        zprava = tab5_validace.bez_prefixu(_UROVEN_RE.sub("", radek.strip()))
        klic = tab5_validace.klic_zpravy(zprava)
        if klic in videno:
            continue
        videno.add(klic)
        ven.append((uroven, zprava))
    return hot.returncode, ven


@pytest.fixture
def cista_scena_na_disku(tmp_path):
    cil = tmp_path / "_scena_Cista.dc.json"
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


# --------------------------------------------------------------------------- #
# Cteni zprav validatoru
# --------------------------------------------------------------------------- #


def test_bez_prefixu_odrizne_soubor_i_scenu():
    zprava = "tab5_clean.json: main: OVERLAP (intentional layering) scene 'main': widget[2] (ram)"
    assert tab5_validace.bez_prefixu(zprava).startswith("OVERLAP (intentional layering)")


def test_index_z_jednoduche_zpravy():
    zprava = "scene 'main': widget[13] (vada_dotyk): touch target 200x44 is 3.8 mm"
    assert tab5_validace.indexy_ze_zpravy(zprava) == (13,)


def test_index_z_OVERLAP_je_DVOJICE():
    """U OVERLAP nese jedna zprava dva odkazy - oba se musi obarvit."""
    zprava = (
        "OVERLAP (visible content collision) same z_index=0: "
        "scene 'main': widget[7] (radek1) <> scene 'main': widget[17] (vada_kolize_a)"
    )
    assert tab5_validace.indexy_ze_zpravy(zprava) == (7, 17)


def test_index_se_neopakuje():
    zprava = "widget[5] (a) <> widget[5] (a)"
    assert tab5_validace.indexy_ze_zpravy(zprava) == (5,)


def test_zprava_bez_odkazu_nema_indexy():
    assert tab5_validace.indexy_ze_zpravy("scene 'main': 900 widgets exceeds recommended") == ()


def test_trida_kolize_ma_prednost_pred_vrstvenim():
    """Poradi v TRIDY je vyznamne: obe zpravy zacinaji na OVERLAP."""
    kolize = "OVERLAP (visible content collision) same z_index=0: widget[7] <> widget[8]"
    vrstveni = "OVERLAP (intentional layering) same z_index=0: widget[2] <> widget[3]"
    assert tab5_validace.trida_zpravy(kolize) == "kolize"
    assert tab5_validace.trida_zpravy(vrstveni) == "vrstveni"


def test_neznama_zprava_je_netrideno():
    assert tab5_validace.trida_zpravy("neco docela jineho") == tab5_validace.NETRIDENO


def test_klic_srazi_zpravy_lisici_se_jen_prefixem():
    """Pozitivni kontrola deduplikace na urovni klice."""
    a = "a.json: main: widget[3] (x): touch target 40x40"
    b = "jiny/soubor.json: main: widget[3] (x): touch target 40x40"
    ka = tab5_validace.klic_zpravy(tab5_validace.bez_prefixu(a))
    kb = tab5_validace.klic_zpravy(tab5_validace.bez_prefixu(b))
    assert ka == kb


def test_klic_NEsrazi_dva_ruzne_prvky():
    """Protipriklad: kdyby klic srazil i tohle, cisla by byla podhodnocena."""
    a = tab5_validace.klic_zpravy("widget[3] (x): touch target 40x40")
    b = tab5_validace.klic_zpravy("widget[4] (y): touch target 40x40")
    assert a != b


# --------------------------------------------------------------------------- #
# TRIDY vs. do_espos.py
# --------------------------------------------------------------------------- #


def test_tridy_z_do_espos_cte_bez_importu(tmp_path):
    """Cteni pres `ast`: soubor se nesmi vykonat.

    V `navrh-appky` se `zapis()` vola na urovni modulu, takze import
    generatoru PREPISE artboard. Kontrola je primocara: soubor ma vedlejsi
    ucinek, ktery po precteni nesmi nastat.
    """
    stopa = tmp_path / "stopa.txt"
    soubor = tmp_path / "falesny_do_espos.py"
    soubor.write_text(
        "import pathlib\n"
        f"pathlib.Path({str(stopa)!r}).write_text('vykonano')\n"
        'TRIDY = [("kolize", "visible content collision"), ("dotyk", "touch target")]\n',
        encoding="utf-8",
    )
    assert tab5_validace.tridy_z_do_espos(soubor) == (
        ("kolize", "visible content collision"),
        ("dotyk", "touch target"),
    )
    assert not stopa.exists()


def test_tridy_z_do_espos_bez_prirazeni_vyhodi(tmp_path):
    soubor = tmp_path / "bez_trid.py"
    soubor.write_text("NECO = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="TRIDY"):
        tab5_validace.tridy_z_do_espos(soubor)


@pytest.mark.skipif(not DO_ESPOS.exists(), reason="tabos-ui-kit/navrh-appky/do_espos.py neni")
def test_TRIDY_se_shoduji_s_branou():
    """Kdyz se tridy rozejdou, cisla editoru a brany uz nejdou porovnat.

    Obe cesty: staticka (rekne PROC) i behova (rekne ZE).
    """
    assert tab5_validace.tridy_z_do_espos(DO_ESPOS) == tab5_validace.TRIDY
    assert tab5_validace.tridy_behem_behu(DO_ESPOS) == tab5_validace.TRIDY


# ---- ctyri obchazky, ktere drive prosly zelene (revize A, nalez B1) -------- #

_ZAKLAD_TRID = (
    "TRIDY = [\n"
    '    ("kolize", "visible content collision"),\n'
    '    ("vrstveni", "OVERLAP (intentional layering)"),\n'
    "]\n"
)
_SPRAVNE = (
    ("kolize", "visible content collision"),
    ("vrstveni", "OVERLAP (intentional layering)"),
)

OBCHAZKY = {
    "append": 'TRIDY.append(("ignorovat", "kalibrovano na 256x128"))\n',
    "plus_rovna_se": 'TRIDY += [("ignorovat", "kalibrovano na 256x128")]\n',
    "druhe_prirazeni": 'TRIDY = [("ignorovat", "kalibrovano na 256x128")]\n',
    "index": 'TRIDY[0] = ("kolize_TICHO", "visible content collision")\n',
}


def _mutant(tmp_path, pridavek: str) -> pathlib.Path:
    soubor = tmp_path / "do_espos.py"
    soubor.write_text(_ZAKLAD_TRID + pridavek, encoding="utf-8")
    return soubor


def test_nemutovany_soubor_obema_cestami_projde(tmp_path):
    """Pozitivni kontrola: bez mutace musi obe cteni dat TYZ spravny seznam."""
    soubor = _mutant(tmp_path, "")
    assert tab5_validace.tridy_z_do_espos(soubor) == _SPRAVNE
    assert tab5_validace.tridy_behem_behu(soubor) == _SPRAVNE


@pytest.mark.parametrize("jmeno", sorted(OBCHAZKY))
def test_obchazka_TRIDY_se_pozna_behovou_hodnotou(tmp_path, jmeno):
    """Behova hodnota vidi VSECHNY ctyri obchazky - literal ve zdroji ne."""
    soubor = _mutant(tmp_path, OBCHAZKY[jmeno])
    assert tab5_validace.tridy_behem_behu(soubor) != _SPRAVNE


@pytest.mark.parametrize("jmeno", sorted(OBCHAZKY))
def test_obchazka_TRIDY_selze_i_pri_statickem_cteni(tmp_path, jmeno):
    """A staticke cteni u toho rekne, ktere misto ji zpusobilo."""
    soubor = _mutant(tmp_path, OBCHAZKY[jmeno])
    with pytest.raises(ValueError, match="TRIDY"):
        tab5_validace.tridy_z_do_espos(soubor)


def test_behova_TRIDY_selze_hlasite_kdyz_soubor_nejde_nacist(tmp_path):
    """Meridlo, ktere pri chybe vrati prazdno, by tvrdilo shodu."""
    soubor = tmp_path / "do_espos.py"
    soubor.write_text("TRIDY = [('a', 'b')\n", encoding="utf-8")  # syntakticka chyba
    with pytest.raises(ValueError, match="kodem"):
        tab5_validace.tridy_behem_behu(soubor)


def test_behova_TRIDY_bez_souboru_vyhodi(tmp_path):
    with pytest.raises(ValueError, match="neexistuje"):
        tab5_validace.tridy_behem_behu(tmp_path / "neni.py")


# --------------------------------------------------------------------------- #
# Vyhodnoceni nad fixturami
# --------------------------------------------------------------------------- #


def test_cista_fixtura_nema_ani_jeden_ERROR():
    vysledek = tab5_validace.vyhodnot(_data(CISTA), file_label="cista")
    assert vysledek.chyb == 0


def test_cista_fixtura_ma_jen_vrstveni():
    vysledek = tab5_validace.vyhodnot(_data(CISTA), file_label="cista")
    assert set(vysledek.pocty) == {"vrstveni"}
    assert vysledek.varovani == sum(vysledek.pocty.values())


def test_vadna_fixtura_MA_ERROR_dotykoveho_cile():
    """POVINNA POZITIVNI KONTROLA: adapter nalez skutecne NAJDE."""
    vysledek = tab5_validace.vyhodnot(_data(VADNA), file_label="vadna")
    chyby = [n for n in vysledek.nalezy if n.uroven == "ERROR"]
    assert len(chyby) == 1
    assert chyby[0].trida == "dotyk"
    assert chyby[0].indexy == (13,)
    assert "touch target" in chyby[0].zprava


def test_vadna_fixtura_najde_i_znaky_kontrast_a_kolizi():
    vysledek = tab5_validace.vyhodnot(_data(VADNA), file_label="vadna")
    assert vysledek.pocty.get("znaky") == 1
    assert vysledek.pocty.get("kontrast") == 1
    assert vysledek.pocty.get("kolize", 0) >= 1


def test_vadna_fixtura_ma_vic_trid_nez_cista():
    """Rozlisovaci schopnost: obe fixtury se nesmi merit stejne."""
    cista = tab5_validace.vyhodnot(_data(CISTA), file_label="c")
    vadna = tab5_validace.vyhodnot(_data(VADNA), file_label="v")
    assert set(cista.pocty) < set(vadna.pocty)


def test_dedup_srazi_dve_stejna_hlaseni(monkeypatch):
    """Pozitivni kontrola deduplikace pres cely adapter.

    Dve pravidla hlasi tutez vec s jinym prefixem; ven smi jit jedno.
    """
    import tools.validate_design as vd

    dvojice = [
        vd.Issue("WARN", "x.json: main: widget[3] (a): touch target 40x40 is 3.4 mm"),
        vd.Issue("WARN", "x.json: scene 'main': widget[3] (a): touch target 40x40 is 3.4 mm"),
    ]
    monkeypatch.setattr(vd, "validate_data", lambda *a, **k: dvojice)
    # Dokument musi projit JSON-schematem, ktere adapter nove pousti taky -
    # jinak by k merenym dvema hlaskam pribyly schema ERRORy.
    vysledek = tab5_validace.vyhodnot(_data(CISTA), file_label="x")
    assert len(vysledek.nalezy) == 1
    assert vysledek.pocty == {"dotyk": 1}


def test_bez_dedup_by_jich_bylo_vic(monkeypatch):
    """Protipriklad k predchozimu: kdyz se lisi PRVEK, srazit se nesmi."""
    import tools.validate_design as vd

    dvojice = [
        vd.Issue("WARN", "x.json: main: widget[3] (a): touch target 40x40 is 3.4 mm"),
        vd.Issue("WARN", "x.json: main: widget[4] (b): touch target 40x40 is 3.4 mm"),
    ]
    monkeypatch.setattr(vd, "validate_data", lambda *a, **k: dvojice)
    assert len(tab5_validace.vyhodnot(_data(CISTA), file_label="x").nalezy) == 2


def test_editor_meri_totez_co_CLI_validator():
    """Beh v pameti vs. brana jako podproces - nezavisla cesta merenimi."""
    kod, z_cli = _cli_nalezy(VADNA)
    # Validator vraci 0 (ciste) nebo 1 (nasel ERROR). Cokoli jineho znamena,
    # ze spadl - a spadle meridlo neni "zadny nalez". Bez teto kontroly byl
    # test zeleny nad useknutym vypisem.
    assert kod in (0, 1), f"validator skoncil kodem {kod}"

    v_pameti = [
        (n.uroven, n.zprava)
        for n in tab5_validace.vyhodnot(_data(VADNA), file_label=str(VADNA)).nalezy
    ]
    assert z_cli
    assert len(z_cli) > 40, f"CLI vytiskl jen {len(z_cli)} nalezu - vypis je useknuty"
    assert z_cli == v_pameti


# --------------------------------------------------------------------------- #
# Parita se schema casti brany (nalez B2)
# --------------------------------------------------------------------------- #


def _s_vadou(uprav) -> dict:
    doc = json.loads(json.dumps(_data(CISTA)))
    uprav(doc)
    return doc


def _groups_jako_seznam(doc):
    doc["groups"] = []


def _klic_navic_u_widgetu(doc):
    doc["scenes"]["main"]["widgets"][0]["poznamka"] = "neco navic"


def _neznamy_typ(doc):
    doc["scenes"]["main"]["widgets"][0]["type"] = "neznamy"


def _width_retezec(doc):
    doc["scenes"]["main"]["widgets"][0]["width"] = "sto"


STRUKTURALNI_VADY = {
    "groups jako seznam": _groups_jako_seznam,
    "klic navic u widgetu": _klic_navic_u_widgetu,
    "neznamy typ widgetu": _neznamy_typ,
    "width jako retezec": _width_retezec,
}


@pytest.mark.parametrize("jmeno", sorted(STRUKTURALNI_VADY))
def test_strukturalni_vada_zastavi_editor_stejne_jako_branu(tmp_path, jmeno):
    """Nalez B2: adapter meril `validate_data`, brana `validate_file`.

    `groups` jako seznam a klic navic u widgetu byly pro branu ERROR a pro
    editor NIC. Kdyby to tak zustalo, prosla by editorem scena, kterou brana
    zastavi - a etapa 2 (`data-id` v generatorech) by to spustila hned.
    """
    doc = _s_vadou(STRUKTURALNI_VADY[jmeno])
    cesta = tmp_path / "x.json"
    cesta.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    kod, z_cli = _cli_nalezy(cesta)
    assert kod in (0, 1)
    vysledek = tab5_validace.vyhodnot(doc, file_label=str(cesta))

    chyb_cli = sum(1 for uroven, _ in z_cli if uroven == "ERROR")
    assert chyb_cli >= 1, "vada se ma projevit uz na brane"
    assert vysledek.chyb == chyb_cli
    assert [(n.uroven, n.zprava) for n in vysledek.nalezy] == z_cli


def test_cista_fixtura_zadny_schema_nalez_nema():
    """Protipriklad: schema nesmi kricet na dokumentu, ktery je v poradku."""
    assert tab5_validace.schema_nalezy(_data(CISTA), file_label="x") == []


def test_schema_nalez_nese_misto_vady():
    nalezy = tab5_validace.schema_nalezy(_s_vadou(_groups_jako_seznam), file_label="x")
    assert len(nalezy) == 1
    assert nalezy[0].level == "ERROR"
    assert "schema: groups:" in nalezy[0].message


def test_bez_jsonschema_je_to_tvrdy_ERROR(monkeypatch):
    """Chybejici zavislost nesmi znamenat tiche preskoceni kontroly."""
    import builtins

    puvodni = builtins.__import__

    def bez(jmeno, *a, **k):
        if jmeno == "jsonschema":
            raise ImportError("neni")
        return puvodni(jmeno, *a, **k)

    monkeypatch.setattr(builtins, "__import__", bez)
    nalezy = tab5_validace.schema_nalezy(_data(CISTA), file_label="x")
    assert len(nalezy) == 1
    assert nalezy[0].level == "ERROR"
    assert "jsonschema" in nalezy[0].message


# --------------------------------------------------------------------------- #
# Mapa urovni pro ramecky
# --------------------------------------------------------------------------- #


def test_ERROR_prebije_WARN_na_temze_prvku(monkeypatch):
    import tools.validate_design as vd

    monkeypatch.setattr(
        vd,
        "validate_data",
        lambda *a, **k: [
            vd.Issue("WARN", "main: widget[2] (a): low contrast (2:1 < 4.5:1)"),
            vd.Issue("ERROR", "main: widget[2] (a): touch target 10x10 is 0.9 mm"),
        ],
    )
    vysledek = tab5_validace.vyhodnot(_data(CISTA), file_label="x")
    assert vysledek.uroven_prvku(2) == "ERROR"


def test_vrstveni_NENI_v_ramecich_ale_JE_v_poctech():
    """Obe strany rozhodnuti maji vlastni doklad."""
    vysledek = tab5_validace.vyhodnot(_data(CISTA), file_label="cista")
    assert vysledek.pocty["vrstveni"] > 0
    assert vysledek.urovne_hlavni == {}
    assert vysledek.urovne_vse != {}
    assert vysledek.uroven_prvku(2) is None
    assert vysledek.uroven_prvku(2, vse=True) == "WARN"


def test_barva_urovne():
    assert tab5_validace.barva_urovne("ERROR") == tab5_validace.BARVA_ERROR
    assert tab5_validace.barva_urovne("WARN") == tab5_validace.BARVA_WARN
    assert tab5_validace.barva_urovne(None) is None


def test_nalez_pozor_je_jen_neprovereno():
    n = tab5_validace.Nalez("WARN", "neprovereno", "collision detection SKIPPED")
    m = tab5_validace.Nalez("WARN", "dotyk", "touch target")
    assert n.pozor is True
    assert m.pozor is False


# --------------------------------------------------------------------------- #
# Napojeni na bezici editor
# --------------------------------------------------------------------------- #


def test_je_tab5_je_False_pro_bezny_navrh(make_app):
    app = make_app(size=(256, 128))
    assert tab5_validace.je_tab5(app) is False


def test_je_tab5_staci_i_samotny_profil(make_app):
    app = make_app(size=(256, 128), profile=tab5_most.PROFIL_TAB5)
    assert tab5_validace.je_tab5(app) is True


def test_po_pusteni_mimo_tab5_nedela_nic(make_app):
    app = make_app(size=(256, 128))
    assert tab5_validace.po_pusteni(app) is None
    assert getattr(app, "tab5_vysledek", None) is None


def test_po_pusteni_na_scene_artboardu_vyda_vysledek(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    vysledek = tab5_validace.po_pusteni(app, ted=100.0)
    assert vysledek is not None
    assert vysledek.chyb == 0
    assert app.tab5_vysledek is vysledek


def test_debounce_druhe_pusteni_neni_a_oznaci_neaktualni(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    tab5_validace.po_pusteni(app, ted=100.0)
    assert tab5_validace.po_pusteni(app, ted=100.0 + tab5_validace.DEBOUNCE_S / 2) is None
    assert app._tab5_ceka is True
    assert app.tab5_vysledek.ceka is True


def test_po_debounce_uz_validace_probehne(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    tab5_validace.po_pusteni(app, ted=100.0)
    novy = tab5_validace.po_pusteni(app, ted=100.0 + tab5_validace.DEBOUNCE_S * 2)
    assert novy is not None
    assert novy.ceka is False


def test_tik_dobehne_odlozenou_validaci(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    tab5_validace.po_pusteni(app, ted=100.0)
    tab5_validace.po_pusteni(app, ted=100.01)
    assert tab5_validace.tik(app, ted=100.02) is None
    assert tab5_validace.tik(app, ted=100.0 + tab5_validace.DEBOUNCE_S * 2) is not None
    assert app._tab5_ceka is False


def test_tik_bez_cekani_nic_nedela(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    tab5_validace.po_pusteni(app, ted=100.0)
    assert tab5_validace.tik(app, ted=200.0) is None


def test_dokument_z_app_ma_device(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    doc = tab5_validace.dokument_z_app(app)
    assert doc["device"] == "tab5"
    assert (doc["width"], doc["height"]) == (1280, 720)


def test_na_device_opravdu_zalezi(make_app, cista_scena_na_disku):
    """Bez `device` a s jinym rozmerem spadne validator na jiny profil.

    Merim to, netvrdim: tentyz dokument bez `device` a s rozmerem, ktery
    tab5 neodpovida, dava JINE tridy nalezu.
    """
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    doc = tab5_validace.dokument_z_app(app)
    s_device = tab5_validace.vyhodnot(doc, file_label="x")

    bez = json.loads(json.dumps(doc))
    bez.pop("device")
    bez["width"] = bez["height"] = 999
    for sc in bez["scenes"].values():
        sc["width"] = sc["height"] = 999
    jiny = tab5_validace.vyhodnot(bez, file_label="x")
    assert set(s_device.pocty) != set(jiny.pocty)


def test_on_mouse_up_spusti_validaci(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    mouse_handlers.on_mouse_up(app, (0, 0))
    assert getattr(app, "tab5_vysledek", None) is not None


def test_on_mouse_up_mimo_tab5_zadny_vysledek_nezalozi(make_app):
    app = make_app(
        size=(256, 128), widgets=[WidgetConfig(type="label", x=0, y=0, width=8, height=8)]
    )
    mouse_handlers.on_mouse_up(app, (0, 0))
    assert getattr(app, "tab5_vysledek", None) is None


def test_prepni_nalezy(make_app):
    app = make_app(size=(256, 128))
    assert tab5_validace.prepni_nalezy(app) is False
    assert tab5_validace.prepni_nalezy(app) is True


# --------------------------------------------------------------------------- #
# Brana pri ulozeni
# --------------------------------------------------------------------------- #


def test_brana_pusti_cistou_scenu(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    assert tab5_validace.brana_ulozeni(app) is None


def test_brana_zastavi_scenu_s_ERROR(make_app, vadna_scena_na_disku):
    app = _app_se_scenou(make_app, vadna_scena_na_disku)
    duvod = tab5_validace.brana_ulozeni(app)
    assert duvod is not None
    assert duvod.startswith("1 ERROR")


def test_brana_mimo_tab5_nic_nezastavi(make_app):
    app = make_app(size=(256, 128))
    assert tab5_validace.brana_ulozeni(app) is None


def test_save_json_NEULOZI_pri_ERROR(make_app, vadna_scena_na_disku):
    app = _app_se_scenou(make_app, vadna_scena_na_disku)
    app.json_path.unlink(missing_ok=True)
    io_ops.save_json(app)
    assert not app.json_path.exists()


def test_save_json_ULOZI_cistou_scenu(make_app, cista_scena_na_disku):
    """Pozitivni kontrola k brane: bez ERRORu se ulozit MUSI."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    app.json_path.unlink(missing_ok=True)
    io_ops.save_json(app)
    assert app.json_path.exists()


def test_save_json_mimo_tab5_bez_zmeny(make_app):
    app = make_app(
        size=(256, 128), widgets=[WidgetConfig(type="label", x=0, y=0, width=8, height=8)]
    )
    app.json_path.unlink(missing_ok=True)
    io_ops.save_json(app)
    assert app.json_path.exists()


# --------------------------------------------------------------------------- #
# FAIL-CLOSED: kdyz se NEZMERILO, brana zastavuje
# --------------------------------------------------------------------------- #


def _rozbij_meridlo(app):
    """Realna cesta k selhani, ne umela zaplata.

    `dokument_z_app` vyhodi `ValueError("designer nema aktivni scenu")`, kdyz
    designer aktivni scenu nema. Presne tenhle stav revize A i B pouzily
    k doklad fail-open chovani.
    """
    app.designer.current_scene = None


def test_pozitivni_kontrola_rozbite_meridlo_opravdu_vyhazuje(make_app, cista_scena_na_disku):
    """Bez tohohle by testy nize prosly, i kdyby se nic nerozbilo."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _rozbij_meridlo(app)
    with pytest.raises(ValueError, match="aktivni scenu"):
        tab5_validace.dokument_z_app(app)


def test_brana_pri_rozbitem_meridle_ZASTAVI(make_app, cista_scena_na_disku):
    """Drive vratila None = "nic nebrani". Meridlo, ktere selhalo, neni nula."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _rozbij_meridlo(app)
    duvod = tab5_validace.brana_ulozeni(app)
    assert duvod is not None
    assert duvod.startswith(tab5_validace.DUVOD_NEZMERENO)
    assert "aktivni scenu" in duvod


def test_brana_zastavi_i_pri_ImportError(make_app, cista_scena_na_disku, monkeypatch):
    """`ImportError` se drive nechytal vubec a propadl az do `save_json`."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    monkeypatch.setattr(
        tab5_validace,
        "_validate_data",
        lambda: (_ for _ in ()).throw(ImportError("rozbity tools.validate_design")),
    )
    duvod = tab5_validace.brana_ulozeni(app)
    assert duvod is not None
    assert duvod.startswith(tab5_validace.DUVOD_NEZMERENO)
    assert "ImportError" in duvod


def test_brana_zastavi_i_pri_necekane_vyjimce(make_app, cista_scena_na_disku, monkeypatch):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    monkeypatch.setattr(
        tab5_validace,
        "_validate_data",
        lambda: (_ for _ in ()).throw(ZeroDivisionError("necekane")),
    )
    duvod = tab5_validace.brana_ulozeni(app)
    assert duvod is not None
    assert duvod.startswith(tab5_validace.DUVOD_NEZMERENO)


def test_save_json_pri_rozbitem_meridle_NEULOZI(make_app, cista_scena_na_disku):
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    app.json_path.unlink(missing_ok=True)
    _rozbij_meridlo(app)
    io_ops.save_json(app)
    assert not app.json_path.exists()


def test_brana_mimo_tab5_selhani_meridla_neresi(make_app):
    """Protipriklad: bezny navrh pro OLED se timhle profilem nemeri vubec."""
    app = make_app(size=(256, 128))
    app.designer.current_scene = None
    assert tab5_validace.brana_ulozeni(app) is None


# --------------------------------------------------------------------------- #
# Autosave nesmi mlcet
# --------------------------------------------------------------------------- #


def _priprav_autosave(app):
    app.autosave_enabled = True
    app.autosave_interval = 0.0
    app._last_autosave_ts = 0.0
    app._dirty = True
    app.autosave_path.unlink(missing_ok=True)


def test_autosave_pri_zastavene_brane_hlasi_a_NEshodi_dirty(make_app, vadna_scena_na_disku):
    """Prace se ulozi do autosave, ale navrh ulozeny NENI - a rekne se to."""
    app = _app_se_scenou(make_app, vadna_scena_na_disku)
    _priprav_autosave(app)
    io_ops.maybe_autosave(app)

    assert app.autosave_path.exists(), "prace se nesmi ztratit"
    assert app._dirty is True, "navrh v json_path je porad stary - dirty musi zustat"
    assert "NEULOZENO" in str(getattr(app, "dialog_message", "") or "")


def test_autosave_na_ciste_scene_dirty_shodi(make_app, cista_scena_na_disku):
    """Pozitivni kontrola: bez ERRORu se autosave chova jako drive."""
    app = _app_se_scenou(make_app, cista_scena_na_disku)
    _priprav_autosave(app)
    io_ops.maybe_autosave(app)

    assert app.autosave_path.exists()
    assert app._dirty is False


def test_autosave_mimo_tab5_beze_zmeny(make_app):
    app = make_app(
        size=(256, 128), widgets=[WidgetConfig(type="label", x=0, y=0, width=8, height=8)]
    )
    _priprav_autosave(app)
    io_ops.maybe_autosave(app)
    assert app.autosave_path.exists()
    assert app._dirty is False


def test_selhany_zapis_autosave_se_ohlasi(make_app, monkeypatch):
    """Log sam nestaci - uzivatel se to musi dozvedet ze stavoveho radku."""
    app = make_app(size=(256, 128))
    _priprav_autosave(app)

    def spadni(_cesta):
        raise OSError("disk plny")

    monkeypatch.setattr(app.designer, "save_to_json", spadni)
    io_ops.maybe_autosave(app)
    assert "AUTOSAVE SELHAL" in str(getattr(app, "dialog_message", "") or "")


# --------------------------------------------------------------------------- #
# Kresleni
# --------------------------------------------------------------------------- #


def _app_s_jednim_prvkem(make_app):
    app = make_app(
        size=(256, 128),
        widgets=[WidgetConfig(type="button", x=100, y=60, width=60, height=30)],
    )
    app.show_grid = False
    app.show_rulers = False
    app.state.selected = []
    app.state.selected_idx = None
    return app


def _bod_rameckem(app, idx: int = 1):
    from cyberpunk_designer.windowing import scene_origin

    o = scene_origin(app)
    w = app.state.current_scene().widgets[idx]
    return (o.x + int(w.x) - 1, o.y + int(w.y) + 5)


def test_ramecek_ERROR_se_opravdu_nakresli(make_app):
    app = _app_s_jednim_prvkem(make_app)
    idx = len(app.state.current_scene().widgets) - 1
    app.tab5_vysledek = tab5_validace.Vysledek(
        nalezy=(tab5_validace.Nalez("ERROR", "dotyk", "touch target", (idx,)),),
        pocty={"dotyk": 1},
        urovne_hlavni={idx: "ERROR"},
        urovne_vse={idx: "ERROR"},
    )
    draw_canvas(app)
    assert app.logical_surface.get_at(_bod_rameckem(app, idx))[:3] == tab5_validace.BARVA_ERROR


def test_bez_vysledku_se_ramecek_nekresli(make_app):
    """Protipriklad: bez nalezu tam ta barva byt NESMI."""
    app = _app_s_jednim_prvkem(make_app)
    idx = len(app.state.current_scene().widgets) - 1
    draw_canvas(app)
    assert app.logical_surface.get_at(_bod_rameckem(app, idx))[:3] != tab5_validace.BARVA_ERROR


def test_vrstveni_se_do_ramecku_dostane_az_prepinacem(make_app):
    app = _app_s_jednim_prvkem(make_app)
    idx = len(app.state.current_scene().widgets) - 1
    app.tab5_vysledek = tab5_validace.Vysledek(
        nalezy=(tab5_validace.Nalez("WARN", "vrstveni", "OVERLAP (intentional layering)", (idx,)),),
        pocty={"vrstveni": 1},
        urovne_hlavni={},
        urovne_vse={idx: "WARN"},
    )
    draw_canvas(app)
    bez = app.logical_surface.get_at(_bod_rameckem(app, idx))[:3]

    app.tab5_ramecky_vse = True
    draw_canvas(app)
    s_nim = app.logical_surface.get_at(_bod_rameckem(app, idx))[:3]

    assert bez != tab5_validace.BARVA_WARN
    assert s_nim == tab5_validace.BARVA_WARN


def _otisk_platna(app) -> bytes:
    import pygame

    return pygame.image.tostring(app.logical_surface, "RGB")


def test_panel_nalezu_se_kresli_a_da_se_vypnout(make_app):
    app = _app_s_jednim_prvkem(make_app)
    app.tab5_vysledek = tab5_validace.Vysledek(
        nalezy=(tab5_validace.Nalez("ERROR", "dotyk", "touch target 10x10", (0,)),),
        pocty={"dotyk": 1},
    )
    app.logical_surface.fill((0, 0, 0))
    pred = _otisk_platna(app)
    draw_nalezy(app)
    assert _otisk_platna(app) != pred

    app.logical_surface.fill((0, 0, 0))
    app.show_nalezy = False
    pred = _otisk_platna(app)
    draw_nalezy(app)
    assert _otisk_platna(app) == pred


def test_panel_bez_nalezu_nekresli_nic(make_app):
    app = _app_s_jednim_prvkem(make_app)
    app.tab5_vysledek = tab5_validace.Vysledek()
    app.logical_surface.fill((0, 0, 0))
    pred = _otisk_platna(app)
    draw_nalezy(app)
    assert _otisk_platna(app) == pred


def test_panel_hlasi_neaktualnost(make_app):
    """Kdyz je vysledek odlozeny debouncem, panel to musi rict."""
    from cyberpunk_designer.drawing import overlays

    app = _app_s_jednim_prvkem(make_app)
    texty = []
    puvodni = overlays.render_pixel_text

    def sledovac(app_, text, color, *a, **k):
        texty.append(text)
        return puvodni(app_, text, color, *a, **k)

    overlays.render_pixel_text = sledovac
    try:
        app.tab5_vysledek = tab5_validace.Vysledek(
            nalezy=(tab5_validace.Nalez("WARN", "dotyk", "touch target"),),
            pocty={"dotyk": 1},
            ceka=True,
        )
        draw_nalezy(app)
    finally:
        overlays.render_pixel_text = puvodni
    assert any("neaktualni" in t for t in texty)


def test_panel_stavi_neprovereno_na_prvni_misto():
    """Rule 133 znamena, ze se NEMERILO - musi byt videt driv nez cokoli."""
    from cyberpunk_designer.drawing.overlays import _nalezy_poradi

    radky = _nalezy_poradi({"vrstveni": 34, "neprovereno": 1, "dotyk": 2})
    assert radky[0] == ("neprovereno", 1)
    assert radky[1] == ("vrstveni", 34)


def test_panel_dopise_a_dalsich(make_app):
    from cyberpunk_designer.drawing import overlays

    app = _app_s_jednim_prvkem(make_app)
    kolik = overlays.NALEZY_MAX_RADKU + 3
    app.tab5_vysledek = tab5_validace.Vysledek(
        nalezy=tuple(
            tab5_validace.Nalez("WARN", "dotyk", f"touch target {i}") for i in range(kolik)
        ),
        pocty={"dotyk": kolik},
    )
    texty = []
    puvodni = overlays.render_pixel_text

    def sledovac(app_, text, color, *a, **k):
        texty.append(text)
        return puvodni(app_, text, color, *a, **k)

    overlays.render_pixel_text = sledovac
    try:
        draw_nalezy(app)
    finally:
        overlays.render_pixel_text = puvodni
    assert any("a dalsich 3" in x for x in texty)


def test_polozky_tab5_jsou_v_normalnim_menu_pohledu(make_app, cista_scena_na_disku):
    """Polozky nesmi zustat viset stranou - musi byt v `ctx_view_items`."""
    from cyberpunk_designer import context_menu

    app = _app_se_scenou(make_app, cista_scena_na_disku)
    akce = [a for _, _, a in context_menu.ctx_view_items(app)]
    assert "tab5_rudy_zapis" in akce
    assert "view_grid" in akce

    bezny = make_app(size=(256, 128))
    assert "tab5_rudy_zapis" not in [a for _, _, a in context_menu.ctx_view_items(bezny)]
