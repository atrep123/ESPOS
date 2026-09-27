"""Prepise `vety` a `stitky` ve fixture verzalek kitu ze ZIVYCH listu.

PROC TENHLE SOUBOR VZNIKL (2026-09-10)
--------------------------------------
Fixtura `verzalky_kit_*.json` je KONTROLNI SKUPINA pravidla 142 (osmy a
devaty tvar) a jeji vlastni `_o_souboru` az dosud odkazovalo na
"scratchpad testy/gen_fixtury_kolo1.py" - tedy na soubor, ktery v zadnem
repozitari neni. Test `test_zivy_kit_snimek_nezastaral` pritom slibuje
"kdyz se kitove texty zmeni, fixtura se ma PREPSAT, ne tise starnout".
Slib, ktery se nema cim splnit, je slib bez pokryti: prvni zmena vety
v kitu (kampan kit-dorovnani, 10. 9. 2026) narazila presne na to.

CO PREPISUJE A CO NE
--------------------
Prepisuji se JEN `vety` a `stitky`, tedy snimek textu kitu. NEsahá se na:
  * `jmena_sdk`      druha osa kontrolni skupiny; meni ji zmena hlavicek
                     SDK, ne zmena kresby kitu,
  * `etalon_nalezu`  lidske rozhodnuti, ktery nalez je PRAVDIVY,
  * `_o_souboru`     puvod a vyklad.
Kdyby prepisoval i etalon, prestal by test merit cokoli: fantom by se
kazdym behem prohlasil za pravdu (rohatka by se sama povolila).

    python tests/fixtures/gen_verzalky_kit.py           # prepise fixturu
    python tests/fixtures/gen_verzalky_kit.py --rozdil  # jen ukaze rozdil
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from html.parser import HTMLParser

ZDE = pathlib.Path(__file__).resolve().parent
ESPOS = ZDE.parents[1]
if str(ESPOS) not in sys.path:
    sys.path.insert(0, str(ESPOS))

from tools.validate_design import (  # noqa: E402
    _V_VERZALKY,
    VETY_NENI_JMENO_SDK,
    VETY_NENI_ROZHRANI,
)

FIXTURA = ZDE / "verzalky_kit_2026-09-09.json"
KIT = ESPOS.parents[1] / "tabos-ui-kit" / "navrh-appky"


class _Texty(HTMLParser):
    """Tytez tri radky, jakymi cte listy sam test - kdyby si generator cetl
    kit jinak nez zkouska, vyrobil by fixturu, ktera nikdy nesedne."""

    def __init__(self):
        super().__init__()
        self.texty: list[str] = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False

    def handle_data(self, data):
        if self.skip:
            return
        d = " ".join(data.split())
        if d:
            self.texty.append(d)


def _verzalky(text: str) -> list[str]:
    return [
        m.group(0)
        for m in _V_VERZALKY.finditer(text)
        if m.group(0) not in VETY_NENI_ROZHRANI and m.group(0) not in VETY_NENI_JMENO_SDK
    ]


def snimek() -> tuple[list[dict], list[dict]]:
    """(vety, stitky) ze zivych listu. Deleni je totez, jake tvrdi fixtura:
    veta ma aspon jedno male pismeno, stitek je cely verzalkami."""
    listy = sorted(KIT.glob("*.dc.html"))
    if not listy:
        raise SystemExit(f"NEZMERENO: {KIT} nema zadny *.dc.html")
    kde: dict[str, list[str]] = {}
    for cesta in listy:
        p = _Texty()
        p.feed(cesta.read_text(encoding="utf-8"))
        jmeno = cesta.name.split(".")[0]
        for t in p.texty:
            if not _verzalky(t):
                continue
            if jmeno not in kde.setdefault(t, []):
                kde[t].append(jmeno)
    vety, stitky = [], []
    for t in sorted(kde):
        (vety if any(z.islower() for z in t) else stitky).append({"text": t, "listy": kde[t]})
    return vety, stitky


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rozdil", action="store_true", help="jen ukazat rozdil")
    a = ap.parse_args()

    f = json.loads(FIXTURA.read_text(encoding="utf-8"))
    vety, stitky = snimek()
    stary = {v["text"] for v in f["vety"]} | {s["text"] for s in f["stitky"]}
    novy = {v["text"] for v in vety} | {s["text"] for s in stitky}
    for t in sorted(novy - stary):
        print("+ " + t)
    for t in sorted(stary - novy):
        print("- " + t)
    print(f"vety {len(f['vety'])} -> {len(vety)}, stitky {len(f['stitky'])} -> {len(stitky)}")

    # Etalon je podmnozina VET. Kdyby prepis nektery etalonovy text z kitu
    # odstranil, fixtura by tvrdila nalez nad vetou, ktera uz nikde neni -
    # a to se musi rict nahlas, ne prepsat mlcky.
    chybi = [e["text"] for e in f["etalon_nalezu"] if e["text"] not in {v["text"] for v in vety}]
    if chybi:
        raise SystemExit(
            f"CHYBA: etalonovy text uz v kitu neni: {chybi}; "
            f"rozhodni o etalonu rucne, generator to neudela"
        )
    if a.rozdil:
        return 0
    f["vety"], f["stitky"] = vety, stitky
    FIXTURA.write_text(json.dumps(f, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{FIXTURA.name} prepsan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
