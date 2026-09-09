"""Hlidac sousedniho `tokens.json` (`tests/dilna.py`) - obe tridy a hranice.

Vada, kterou zavira (kritik espos-vse-kritik D2): ``DILNA = ESPOS.parents[1]``
vaze testy na to, co nahodou lezi dve patra nad ESPOSem; cizi soubor tehoz
jmena shodil sadu na ``KeyError: 'panel'`` misto pojmenovaneho skipu.

Tridy hlidace a co je tu pribite:

* POZITIVNI: kitovy soubor (podpis + vsechny bloky) -> ``ok`` a data.
* NEGATIVNI: cizi soubor tehoz jmena -> ``cizi`` a SKIP (ne KeyError),
  chybejici -> ``chybi``, rozbity JSON -> ``rozbity``.
* HRANICE: podpis sedi, ale jeden blok chybi -> ``neuplny`` a PAD, ne skip.
  Presne tohle je ta hranice, kterou nesmi nikdo "zjednodusit": skip by
  ubrani bloku umlcel.
* KONTROLNI SKUPINA: soubor, ktery ma VSECHNY povinne bloky, ale cizi
  podpis, je porad ``cizi`` (o tride rozhoduje podpis, ne pocet klicu).
* ZIVY SOUSED: kdyz kit vedle je, jeho tokens.json musi byt ``ok``.

Mutace (piskoviste testy/mut-1): hlidac bez kontroly podpisu vrati
u ciziho souboru ``ok`` -> `test_cizi_soubor_konci_skipem_ne_KeyError`
a `test_kontrolni_skupina_uplny_ale_cizi_je_cizi` zcervenaji.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tests.dilna import PODPIS, POVINNE_KLICE, potreba_tokeny, tokeny_kitu

ESPOS = pathlib.Path(__file__).resolve().parents[1]
ZIVY = ESPOS.parents[1] / "tabos-ui-kit" / "tokens.json"


def _kit(**navic) -> dict:
    """Nejmensi soubor, ktery hlidac uzna za kitovy."""
    d = {PODPIS[0]: PODPIS[1]}
    d.update({k: {"x": 1} for k in POVINNE_KLICE})
    d.update(navic)
    return d


def _zapis(tmp_path: pathlib.Path, obsah, jmeno="tokens.json") -> pathlib.Path:
    p = tmp_path / jmeno
    p.write_text(obsah if isinstance(obsah, str) else json.dumps(obsah), encoding="utf-8")
    return p


def test_kitovy_soubor_je_ok_a_vraci_data(tmp_path):
    p = _zapis(tmp_path, _kit(colors={"base": "#14170f"}))
    trida, data = tokeny_kitu(p)
    assert trida == "ok"
    assert data["colors"] == {"base": "#14170f"}
    assert potreba_tokeny(p)["colors"]["base"] == "#14170f"


def test_chybejici_soubor_je_chybi_s_cestou(tmp_path):
    trida, veta = tokeny_kitu(tmp_path / "tokens.json")
    assert trida == "chybi"
    assert veta.startswith("NEZMERENO:") and "tokens.json" in veta


def test_rozbity_json_je_rozbity_ne_vyjimka(tmp_path):
    p = _zapis(tmp_path, '{"theme": "smaltovy-cifernik", ')
    trida, veta = tokeny_kitu(p)
    assert trida == "rozbity"
    assert veta.startswith("NEZMERENO:")


@pytest.mark.parametrize(
    "obsah",
    [
        {"theme": "jiny-jazyk", "colors": {}},  # D2: cizi soubor bez 'panel'
        {"colors": {}},  # bez podpisu vubec
        ["seznam"],  # ani objekt
        {"theme": "smaltovy-cifernik "},  # skoro podpis - mezera navic
    ],
)
def test_cizi_soubor_je_cizi_a_veta_rika_proc(tmp_path, obsah):
    trida, veta = tokeny_kitu(_zapis(tmp_path, obsah))
    assert trida == "cizi"
    assert veta.startswith("NEZMERENO:") and "smaltovy-cifernik" in veta


def test_cizi_soubor_konci_skipem_ne_KeyError(tmp_path):
    """Presne pripad D2: cizi soubor bez 'panel'. Hlidac ma SKIPNOUT.

    Bez podpisove kontroly by `potreba_tokeny` vratila data a prvni
    `data["panel"]` by spadl na KeyError - to je cervena teto mutace.
    """
    p = _zapis(tmp_path, {"theme": "starsi-kit", "colors": {"base": "#000"}})
    with pytest.raises(pytest.skip.Exception) as e:
        potreba_tokeny(p)["panel"]
    assert "NEZMERENO" in str(e.value)


@pytest.mark.parametrize("chybejici", list(POVINNE_KLICE))
def test_HRANICE_kitovy_soubor_bez_jednoho_bloku_je_neuplny_a_PADA(tmp_path, chybejici):
    d = _kit()
    del d[chybejici]
    p = _zapis(tmp_path, d)
    trida, veta = tokeny_kitu(p)
    assert trida == "neuplny"
    assert f"1 z {len(POVINNE_KLICE)}" in veta and chybejici in veta
    with pytest.raises(pytest.fail.Exception):
        potreba_tokeny(p)


def test_blok_ktery_neni_objekt_je_neuplny(tmp_path):
    """`"stavy": []` ma klic, ale most z nej nic nevyveze - je to totez co chybi."""
    trida, veta = tokeny_kitu(_zapis(tmp_path, _kit(stavy=[])))
    assert trida == "neuplny" and "stavy" in veta


def test_kontrolni_skupina_uplny_ale_cizi_je_cizi(tmp_path):
    """Vsechny povinne bloky, jiny podpis -> porad cizi (rozhoduje podpis)."""
    d = _kit()
    d[PODPIS[0]] = "jiny-jazyk"
    trida, _ = tokeny_kitu(_zapis(tmp_path, d))
    assert trida == "cizi"


def test_dve_volani_daji_tyz_vysledek(tmp_path):
    p = _zapis(tmp_path, _kit())
    assert tokeny_kitu(p) == tokeny_kitu(p)


def test_zivy_kit_vedle_ESPOSu_je_ok():
    if not ZIVY.is_file():
        pytest.skip(f"NEZMERENO: {ZIVY} neni na disku - kit neni vedle ESPOSu")
    trida, vysledek = tokeny_kitu(ZIVY)
    assert trida == "ok", vysledek
    assert vysledek["panel"]["ppi"] == 294
