"""Mutacni doklad pravidel 137-152 a `slovnik_prurez` (kolo 1, mapa mezer C2).

PROC. Test s pozitivni tridou dokazuje jen to, ze pravidlo DNES hlasi. Ze by
zcervenal, kdyby pravidlo prestalo hlasit, dokazuje az MUTACE: produkcni kod
se v izolovane kopii pokazi pojmenovanym zpusobem (prah do nekonecna, podminka
navzdy nepravdiva) a tentyz pozitivni test nad kopii MUSI selhat. Bez toho je
zeleny test jen tvrzeni (pamet: "Zeleny test, ktery nic nezmeril").

JAK. Kazda mutace je trojice (kotva v `tools/validate_design.py`, nahrada,
pozitivni + negativni mereni). Kotva se musi ve zdroji vyskytnout PRAVE
JEDNOU - jinak test spadne s vetou, ne s tichym "nic se nezmutovalo". Kopie
se pise MIMO repo: do `$ESPOS_MUTACE_KOPIE/mutace/<jmeno>/tools/` (kampan:
scratchpad/testy/mut-1/ESPOS), bez promenne do `tmp_path`. Modul se nacita
`importlib` pod vlastnim jmenem, takze `tools.validate_design` v ostatnich
testech zustava netknuty. Schema se kopiruje vedle (validator ho hleda
relativne k `__file__`).

CTYRI MERENI NA MUTACI:

1. kotva je v produkcnim kodu prave jednou (predpoklad mereni),
2. PRISTINA kopie nactena touz cestou pozitivni tridu HLASI (kontrolni
   skupina nacitani - jinak by kazda mutace "zabrala" jen proto, ze kopie
   nic nenacte),
3. MUTOVANA kopie pozitivni tridu NEHLASI (= existujici test by zcervenal;
   vypis "mutace X -> test Y cerveny" jde do VYSLEDEK.txt v kopii),
4. mutovana kopie negativni tridu dal NEHLASI a CIZI pravidlo dal hlasi
   (mutace je lokalni umlceni, ne pad validatoru; pad by se tvaril jako
   "chytil jsem mutaci").

Determinismus: kopie se pise idempotentne (tentyz bajt pri kazdem behu).
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType

import pytest

from tools import validate_design as vd

ESPOS = pathlib.Path(__file__).resolve().parents[1]
ZDROJ = ESPOS / "tools" / "validate_design.py"
SCHEMA = ESPOS / "schemas" / "ui_design.schema.json"
FIXTURY = ESPOS / "tests" / "fixtures"


def _pocet(modul: ModuleType, fixtura: str, znacka: str, uroven: str | None = None) -> int:
    nalezy = modul.validate_file(FIXTURY / fixtura, warnings_as_errors=False)
    return sum(1 for i in nalezy if znacka in i.message and (uroven is None or i.level == uroven))


def _fix(fixtura: str, znacka: str, uroven: str | None = None) -> Callable[[ModuleType], int]:
    return lambda m: _pocet(m, fixtura, znacka, uroven)


# -- slovnik_prurez: cista funkce, mereni bez fixtury ------------------------

STAVY_SD = ["detekce nedostupna", "neni vlozena", "vlozena, nepripojena", "pripojena"]


def _slovnik(modul: ModuleType):
    slovnik, nalezy = modul._slovnik_ze_sceny({"navrh": {"slovnik": {"microSD": STAVY_SD}}}, "t")
    assert nalezy == []
    return slovnik


def _prurez(modul: ModuleType, tvrzeni, znacka: str) -> int:
    return sum(1 for n in modul.slovnik_prurez(tvrzeni, _slovnik(modul)) if znacka in n.message)


A4 = {
    "diagnostics": [("microSD", "vlozena, nepripojena")],
    "files": [("microSD", "karta neni vlozena")],
}
A4_SHODA = {"a": [("microSD", "pripojena")], "b": [("microSD", "pripojena")]}
NEJDELSI = {"a": [("microSD", "vlozena, nepripojena")], "b": [("microSD", "pripojena")]}
NEJDELSI_SHODA = {"a": [("microSD", "vlozena, nepripojena")], "b": [("microSD", "vlozena, nepripojena")]}
BEZ_TVRZENI = {"a": [("kamera", "bezi")]}
S_TVRZENIM = {"a": [("microSD", "pripojena")]}


def _r147_svisla_uvnitr(modul: ModuleType) -> int:
    """Kratka svisla cara uvnitr inkoustu (test_validate_rules_147_svisle)."""
    w = {
        "type": "label", "x": 600, "y": 640, "width": 100, "height": 12, "text": "kanal 7 spoust",
        "color_fg": "#e6e1ce", "color_bg": "#14170f", "align": "left", "valign": "middle",
        "_widget_id": "hodnota.7",
    }
    scene = {"width": 1280, "height": 720, "widgets": [w], "navrh": {"cary": [[640, 641, 1, 10]]}}
    nalezy = modul.validate_data({"device": "tab5", "scenes": {"main": scene}}, file_label="t", warnings_as_errors=False)
    return sum(1 for i in nalezy if vd.ZNACKA_R147 in i.message)


# Cizi pravidlo, ktere ma po kazde mutaci dal hlasit (lokalnost mutace).
CIZI_VYCHOZI = _fix("tab5_polarita_vady.json", vd.ZNACKA_R146)


@dataclass(frozen=True)
class Mutace:
    jmeno: str
    kotva: str
    nahrada: str
    pozitivni: Callable[[ModuleType], int]
    negativni: Callable[[ModuleType], int]
    cerveny_test: str
    cizi: Callable[[ModuleType], int] = CIZI_VYCHOZI


MUTACE = [
    Mutace(
        "R137_tolerance_nekonecna",
        "if pretok > R137_TOLERANCE_PX:",
        "if pretok > R137_TOLERANCE_PX + 10**6:",
        _fix("tab5_navrh_vady.json", vd.ZNACKA_R137),
        _fix("tab5_navrh_ciste.json", vd.ZNACKA_R137),
        "test_validate_rules_136_143.py::test_vadna_fixtura_najde_vsechny_ctyri_zasazene_tridy",
    ),
    Mutace(
        "R138_prazdny_smalt_vzdy_omluven",
        "if prazdne or text_uvnitr is not None:",
        "if prazdne or text_uvnitr is not None or True:",
        _fix("tab5_smalt_vady.json", vd.ZNACKA_R138 + ":"),
        _fix("tab5_smalt_ciste.json", vd.ZNACKA_R138 + ":"),
        "test_validate_rules_136_143.py::test_smaltova_fixtura_vady_najde_obe_tridy",
    ),
    Mutace(
        "R139_pomlcka_neni_pomlcka",
        "if holy in POMLCKY:",
        "if holy in POMLCKY and not holy:",
        _fix("tab5_smalt_vady.json", vd.ZNACKA_R139 + ":"),
        _fix("tab5_smalt_ciste.json", vd.ZNACKA_R139 + ":"),
        "test_validate_rules_136_143.py::test_smaltova_fixtura_vady_najde_obe_tridy",
    ),
    Mutace(
        "R140_kapacita_nekonecna",
        "if polozek > kapacita:",
        "if polozek > kapacita + 10**6:",
        _fix("tab5_mrizka_vady.json", vd.ZNACKA_R140 + ":", "ERROR"),
        _fix("tab5_mrizka_ciste.json", vd.ZNACKA_R140 + ":", "ERROR"),
        "test_validate_rules_136_143.py::test_mrizkova_fixtura_vady_najde_obe_tridy",
    ),
    Mutace(
        "R144_prah_nekonecny",
        "if pretok < R144_PRAH_PX:",
        "if pretok < R144_PRAH_PX * 10**6:",
        _fix("tab5_orez_vady.json", vd.ZNACKA_R144),
        _fix("tab5_orez_ciste.json", vd.ZNACKA_R144),
        "test_validate_rules_144_147.py::test_fixtura_orez_vady_hlasi_obe_pulky",
    ),
    Mutace(
        "R145_prah_nekonecny",
        "if pretok < R145_PRAH_PX:",
        "if pretok < R145_PRAH_PX * 10**6:",
        _fix("tab5_orez_vady.json", vd.ZNACKA_R145),
        _fix("tab5_orez_ciste.json", vd.ZNACKA_R145),
        "test_validate_rules_144_147.py::test_fixtura_orez_vady_hlasi_obe_pulky",
    ),
    Mutace(
        "R146_prekryv_nikdy",
        "if min(x2, px2) - max(x, px) < R146_PRAH_PX:",
        "if min(x2, px2) - max(x, px) < R146_PRAH_PX + 10**6:",
        _fix("tab5_polarita_vady.json", vd.ZNACKA_R146),
        _fix("tab5_polarita_ciste.json", vd.ZNACKA_R146),
        "test_validate_rules_144_147.py::test_fixtura_polarita_vady_hlasi_jednou",
        cizi=_fix("tab5_cary_vady.json", vd.ZNACKA_R147),
    ),
    Mutace(
        "R147_odstup_nekonecny",
        "R147_ODSTUP_PX = 1\n",
        "R147_ODSTUP_PX = 10**6\n",
        _fix("tab5_cary_vady.json", vd.ZNACKA_R147),
        _fix("tab5_cary_ciste.json", vd.ZNACKA_R147),
        "test_validate_rules_144_147.py::test_fixtura_cary_vady_hlasi_jednou",
    ),
    Mutace(
        "R147_odstup_nekonecny_svisla",
        "R147_ODSTUP_PX = 1\n",
        "R147_ODSTUP_PX = 10**6\n",
        _r147_svisla_uvnitr,
        _fix("tab5_cary_svisle_ciste.json", vd.ZNACKA_R147),
        "test_validate_rules_147_svisle.py::test_svisla_cara_uvnitr_inkoustu_hlasi",
    ),
    Mutace(
        "R149_vse_je_citelne",
        "if minut >= R149_MEZ_LETMO:",
        "if minut >= 0:",
        _fix("tab5_citelnost_vady.json", vd.ZNACKA_R149),
        _fix("tab5_citelnost_ciste.json", vd.ZNACKA_R149),
        "test_validate_rules_148_151.py::test_r149_fixtury_obou_trid",
    ),
    Mutace(
        "R152_min_prvku_nekonecne",
        "R152_MIN_PRVKU = 6\n",
        "R152_MIN_PRVKU = 10**6\n",
        _fix("tab5_mrizka_bez_kapacity_vady.json", vd.ZNACKA_R152_NEMERENO),
        _fix("tab5_mrizka_bez_kapacity_ciste.json", vd.ZNACKA_R152_NEMERENO),
        "test_validate_rules_152.py::test_fixtura_vady_projde_schematem_a_hlasi_prave_jednou",
    ),
    Mutace(
        "PRUREZ_dva_stavy_nejsou_rozpor",
        "if len(stavy) < 2:",
        "if len(stavy) < 10**6:",
        lambda m: _prurez(m, A4, vd.ZNACKA_R143_PRUREZ),
        lambda m: _prurez(m, A4_SHODA, vd.ZNACKA_R143_PRUREZ),
        "test_slovnik_prurez.py::test_dva_listy_dva_stavy_je_WARN_s_vyctem_listu",
    ),
    Mutace(
        "PRUREZ_nejkratsi_shoda",
        "stav = max(shody, key=len)",
        "stav = min(shody, key=len)",
        lambda m: _prurez(m, NEJDELSI, vd.ZNACKA_R143_PRUREZ),
        lambda m: _prurez(m, NEJDELSI_SHODA, vd.ZNACKA_R143_PRUREZ),
        "test_slovnik_prurez.py::test_nejdelsi_shoda_neobvini_vetu_ktera_obsahuje_kratsi_stav",
    ),
    Mutace(
        "PRUREZ_vec_bez_tvrzeni_se_preskoci",
        "        if not stavy:\n            issues.append(",
        "        if not stavy:\n            continue\n            issues.append(",
        lambda m: _prurez(m, BEZ_TVRZENI, vd.ZNACKA_R143_VEC_NEMERENO),
        lambda m: _prurez(m, S_TVRZENIM, vd.ZNACKA_R143_VEC_NEMERENO),
        "test_slovnik_prurez.py::test_vec_bez_jedineho_tvrzeni_je_WARN_o_nemereni",
    ),
]
JMENA = [m.jmeno for m in MUTACE]


def test_jmena_mutaci_jsou_ASCII_a_ruzna():
    assert len(set(JMENA)) == len(JMENA)
    assert all(j.isascii() for j in JMENA)


@pytest.mark.parametrize("m", MUTACE, ids=JMENA)
def test_kotva_je_v_produkcnim_kodu_prave_jednou(m: Mutace):
    n = ZDROJ.read_text(encoding="utf-8").count(m.kotva)
    assert n == 1, f"mutace {m.jmeno}: kotva {m.kotva!r} je ve zdroji {n}x, ma byt 1x - mutace by se nepripnula"
    assert m.kotva != m.nahrada


# --------------------------------------------------------------------------- #
# Kopie mimo repo a nacitani
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def koren_kopie(tmp_path_factory) -> pathlib.Path:
    cesta = os.environ.get("ESPOS_MUTACE_KOPIE")
    koren = pathlib.Path(cesta) if cesta else tmp_path_factory.mktemp("espos-mutace")
    koren = koren.resolve()
    assert ESPOS not in koren.parents and koren != ESPOS, f"kopie {koren} lezi v repu"
    (koren / "mutace").mkdir(parents=True, exist_ok=True)
    return koren


def _zapis_idempotentne(cesta: pathlib.Path, obsah: str) -> None:
    cesta.parent.mkdir(parents=True, exist_ok=True)
    if not cesta.is_file() or cesta.read_text(encoding="utf-8") != obsah:
        cesta.write_text(obsah, encoding="utf-8", newline="\n")


def _pripravit(koren: pathlib.Path, jmeno: str, zdroj: str) -> pathlib.Path:
    slozka = koren / "mutace" / jmeno
    _zapis_idempotentne(slozka / "tools" / "validate_design.py", zdroj)
    schema_cil = slozka / "schemas" / "ui_design.schema.json"
    schema_cil.parent.mkdir(parents=True, exist_ok=True)
    if not schema_cil.is_file() or schema_cil.read_bytes() != SCHEMA.read_bytes():
        shutil.copyfile(SCHEMA, schema_cil)
    return slozka / "tools" / "validate_design.py"


def _nacti(cesta: pathlib.Path, jmeno_modulu: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(jmeno_modulu, cesta)
    assert spec is not None and spec.loader is not None
    modul = importlib.util.module_from_spec(spec)
    sys.modules[jmeno_modulu] = modul
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(scope="session")
def pristina(koren_kopie) -> ModuleType:
    zdroj = ZDROJ.read_text(encoding="utf-8")
    modul = _nacti(_pripravit(koren_kopie, "_pristina", zdroj), "validate_design_mut_pristina")
    assert modul is not vd
    assert koren_kopie / "mutace" / "_pristina" == modul.REPO_ROOT
    return modul


@pytest.fixture(scope="session")
def mutovane(koren_kopie) -> dict[str, ModuleType]:
    zdroj = ZDROJ.read_text(encoding="utf-8")
    ven = {}
    for m in MUTACE:
        assert zdroj.count(m.kotva) == 1, m.jmeno
        mut = zdroj.replace(m.kotva, m.nahrada)
        assert mut != zdroj
        ven[m.jmeno] = _nacti(_pripravit(koren_kopie, m.jmeno, mut), f"validate_design_mut_{m.jmeno}")
    return ven


def test_kopie_lezi_mimo_repo_a_je_izolovana(koren_kopie, pristina):
    assert ESPOS not in pathlib.Path(pristina.__file__).parents
    assert pristina.__file__ != vd.__file__
    # Nacteni kopie nepremapovalo produkcni modul.
    assert sys.modules["tools.validate_design"] is vd


@pytest.mark.parametrize("m", MUTACE, ids=JMENA)
def test_pristina_kopie_pozitivni_tridu_HLASI(m: Mutace, pristina):
    """Kontrolni skupina nacitani: bez tohohle by 'mutace umlcela' mohlo
    znamenat 'kopie nic nenacte'."""
    assert m.pozitivni(pristina) >= 1, f"{m.jmeno}: pristina kopie nehlasi - mereni mutace by bylo o nicem"
    assert m.pozitivni(pristina) == m.pozitivni(vd)
    assert m.negativni(pristina) == 0


@pytest.mark.parametrize("m", MUTACE, ids=JMENA)
def test_mutace_umlci_pozitivni_tridu(m: Mutace, mutovane, koren_kopie):
    modul = mutovane[m.jmeno]
    pred = m.pozitivni(vd)
    po = m.pozitivni(modul)
    veta = f"mutace {m.jmeno} -> {m.cerveny_test} cerveny ({pred} nalezu pred, {po} po)"
    _zapis_idempotentne(koren_kopie / "mutace" / m.jmeno / "VYSLEDEK.txt", veta + "\n")
    assert po == 0 and pred >= 1, veta.replace("cerveny", "NENI cerveny - mutace prezila")


@pytest.mark.parametrize("m", MUTACE, ids=JMENA)
def test_mutace_je_lokalni_umlceni_ne_pad(m: Mutace, mutovane):
    modul = mutovane[m.jmeno]
    assert m.negativni(modul) == 0, f"{m.jmeno}: mutace hlasi na negativni tride - to neni umlceni"
    assert m.cizi(modul) >= 1, f"{m.jmeno}: cizi pravidlo po mutaci mlci - mutace neni lokalni (pad?)"
    assert m.cizi(modul) == m.cizi(vd)


def test_kopie_je_idempotentni_tentyz_bajt(koren_kopie, mutovane):
    """Dva behy = tyz obsah (determinismus kopie)."""
    zdroj = ZDROJ.read_text(encoding="utf-8")
    for m in MUTACE:
        cesta = koren_kopie / "mutace" / m.jmeno / "tools" / "validate_design.py"
        assert cesta.read_text(encoding="utf-8") == zdroj.replace(m.kotva, m.nahrada)


def test_kazda_mutace_ma_jiny_zdroj_nez_pristina(koren_kopie, pristina, mutovane):
    pristina_text = pathlib.Path(pristina.__file__).read_text(encoding="utf-8")
    for m in MUTACE:
        text = pathlib.Path(mutovane[m.jmeno].__file__).read_text(encoding="utf-8")
        assert text != pristina_text, m.jmeno
        assert m.nahrada in text and m.kotva not in text.replace(m.nahrada, ""), m.jmeno
