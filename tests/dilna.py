"""Hlidac sousedniho `tokens.json` kitu (sdileny pro testy nad DILNOU).

PROC TENHLE MODUL JE. Testy kampane se na kit divaji cestou
``DILNA = ESPOS.parents[1] / "tabos-ui-kit" / "tokens.json"`` - tedy na to,
co NAHODOU lezi dve patra nad ESPOSem. Kritik (espos-vse-kritik D2) na to
naletel sam: piskoviste si naslo cizi stary ``scratchpad/tabos-ui-kit/
tokens.json`` a testy spadly na ``KeyError: 'panel'`` misto pojmenovaneho
skipu. Skip existoval (`_potreba_tokeny`), ale nikdo neoveroval, ze
nalezeny soubor je TEN SPRAVNY.

Ctyri tridy vysledku a proc se nesmi slit do dvou:

* ``chybi``   - soubor na disku neni       -> SKIP (kit neni vedle, neni co merit)
* ``rozbity`` - neni to JSON               -> SKIP (podepsat se neda)
* ``cizi``    - JSON bez podpisu kitu      -> SKIP (soubor tehoz jmena, ne kit)
* ``neuplny`` - podpis sedi, klic chybi    -> PAD  (to JE kit a JE vadny)
* ``ok``      - podpis i klice             -> mereni

Kdyby ``neuplny`` koncil skipem, ubrani bloku ``stavy`` nebo ``panel``
z kitoveho souboru by celou sadu umlcelo a zustala by zelena nad nicim.
Rozdil mezi ``cizi`` a ``neuplny`` drzi PODPIS: ``theme`` kitu je jmeno
navrhoveho jazyka ("smaltovy-cifernik"), ne obecne slovo.

Funkce `tokeny_kitu` je CISTA (bere cestu, vraci dvojici) - test ji
pousti nad piskovistem v obou tridach. `potreba_tokeny` je jeji obal pro
pytest (skip / fail / data).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

PODPIS = ("theme", "smaltovy-cifernik")
# Klice, bez kterych most nema co vozit: paleta (150), skala (148),
# soustava (151), dotyk a PPI (135, 141), slovnik stavu (143).
POVINNE_KLICE = ("colors", "typography", "layout", "spacing", "stavy", "panel", "touch")


def tokeny_kitu(cesta: pathlib.Path | str) -> tuple[str, Any]:
    """-> (trida, data | veta). Tridy: ok, chybi, rozbity, cizi, neuplny."""
    cesta = pathlib.Path(cesta)
    if not cesta.is_file():
        return "chybi", f"NEZMERENO: {cesta} neni na disku - tabos-ui-kit neni vedle ESPOSu"
    try:
        data = json.loads(cesta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return "rozbity", f"NEZMERENO: {cesta} se neda precist jako JSON ({e})"
    klic, hodnota = PODPIS
    if not isinstance(data, dict) or data.get(klic) != hodnota:
        nalezeno = data.get(klic) if isinstance(data, dict) else type(data).__name__
        return (
            "cizi",
            f"NEZMERENO: {cesta} nema {klic} == {hodnota!r} (ma {nalezeno!r}) - "
            f"neni to tokens.json kitu, jen soubor tehoz jmena",
        )
    chybi = [k for k in POVINNE_KLICE if not isinstance(data.get(k), dict)]
    if chybi:
        return (
            "neuplny",
            f"{cesta} JE tokens.json kitu (podpis {klic}={hodnota!r} sedi), ale chybi "
            f"mu {len(chybi)} z {len(POVINNE_KLICE)} povinnych bloku: {', '.join(chybi)} - "
            f"most by nad zivymi listy nemel co vozit",
        )
    return "ok", data


def potreba_tokeny(cesta: pathlib.Path | str) -> dict:
    """`tokeny_kitu` pro pytest: skip s vetou, PAD u vadneho kitu, jinak data."""
    trida, vysledek = tokeny_kitu(cesta)
    if trida == "ok":
        return vysledek
    if trida == "neuplny":
        pytest.fail(vysledek)
    pytest.skip(vysledek)
    raise AssertionError("nedosazitelne")  # pragma: no cover
