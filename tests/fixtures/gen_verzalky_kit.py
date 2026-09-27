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

Samostatny aktualni snimek (2026-09-27): --nova-fixtura NEW_PATH vyzaduje
--kit-ref, --sdk-root a --sdk-ref. Cte commit bloby, nikoli dirty strom,
nese hashe listu/hlavicek a explicitne NULOVY etalon. SDK unik je chyba,
ne novy etalon. Existujici/historickou fixturu tato cesta nikdy neprepise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from html.parser import HTMLParser

ZDE = pathlib.Path(__file__).resolve().parent
ESPOS = ZDE.parents[1]
if str(ESPOS) not in sys.path:
    sys.path.insert(0, str(ESPOS))

from tools.validate_design import (  # noqa: E402
    _V_VERZALKY,
    VETY_NENI_JMENO_SDK,
    VETY_NENI_ROZHRANI,
    _veta_strojove_jmeno,
    jmena_ze_sdk,
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


def _snimek_textu(listy: Iterable[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Pure parser shared by working-tree and immutable-commit snapshots."""
    kde: dict[str, list[str]] = {}
    for filename, html in listy:
        p = _Texty()
        p.feed(html)
        jmeno = filename.split(".")[0]
        for t in p.texty:
            if not _verzalky(t):
                continue
            if jmeno not in kde.setdefault(t, []):
                kde[t].append(jmeno)
    vety: list[dict] = []
    stitky: list[dict] = []
    for t in sorted(kde):
        (vety if any(z.islower() for z in t) else stitky).append({"text": t, "listy": kde[t]})
    return vety, stitky


def snimek() -> tuple[list[dict], list[dict]]:
    """(vety, stitky) ze zivych listu. Deleni je totez, jake tvrdi fixtura:
    veta ma aspon jedno male pismeno, stitek je cely verzalkami."""
    listy = sorted(KIT.glob("*.dc.html"))
    if not listy:
        raise SystemExit(f"NEZMERENO: {KIT} nema zadny *.dc.html")
    return _snimek_textu((p.name, p.read_text(encoding="utf-8")) for p in listy)


def _git(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=30)


def _committed_files(
    root: pathlib.Path,
    ref: str,
    folder: str,
    suffix: str,
) -> tuple[str, list[tuple[str, bytes]]]:
    commit = _git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    paths = _git(root, "ls-tree", "-r", "--name-only", commit, "--", folder).decode().splitlines()
    files = [(p, _git(root, "show", f"{commit}:{p}")) for p in sorted(paths) if p.endswith(suffix)]
    if not files:
        raise ValueError(f"NEZMERENO: {root} @ {commit}: no {folder}/*{suffix}")
    return commit, files


def novy_snimek(
    kit_root: pathlib.Path,
    kit_ref: str,
    sdk_root: pathlib.Path,
    sdk_ref: str,
) -> dict:
    """Separate immutable snapshot with an explicitly authorized ZERO oracle.

    Never learn expected findings from the validator or rewrite historical data.
    Dirty working-tree edits cannot silently acquire clean commit provenance.
    """
    kit_commit, boards = _committed_files(kit_root, kit_ref, "navrh-appky", ".dc.html")
    sdk_commit, headers = _committed_files(sdk_root, sdk_ref, "include", ".h")
    vety, stitky = _snimek_textu((pathlib.Path(p).name, b.decode("utf-8")) for p, b in boards)
    with tempfile.TemporaryDirectory(prefix="r142-sdk-") as directory:
        root = pathlib.Path(directory)
        for p, data in headers:
            destination = root / p
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        names = jmena_ze_sdk(root / "include")
    if not names:
        raise ValueError("NEZMERENO: committed SDK supplied no names")
    leaks = {}
    for entry in vety:
        found = _veta_strojove_jmeno(entry["text"], names)
        if found is not None and found[0] in ("jmeno ze SDK", "jmeno rozhrani ze SDK"):
            leaks[entry["text"]] = found
    if leaks:
        raise ValueError(f"SDK leaks violate the explicit zero oracle: {leaks}")
    return {
        "_o_souboru": [
            "Independent current R142 snapshot from committed HTML, parsed offline.",
            "Kit 6724fc5 deliberately replaced ERROR cteni: NotFound and the SDK-shaped hardware/RF wording.",
            "Expected current SDK leaks are explicitly ZERO; findings never become the oracle.",
            "Historical verzalky_kit_2026-09-09.json and its positive oracle remain unchanged.",
            "Regenerate via gen_verzalky_kit.py --nova-fixtura with explicit kit/SDK refs.",
        ],
        "kit": kit_commit,
        "listy_sha256": {p: hashlib.sha256(data).hexdigest() for p, data in boards},
        "jmena_sdk": {
            "commit": sdk_commit,
            "odkud": "committed tabos-sdk include/*.h",
            "hlavicky_sha256": {p: hashlib.sha256(data).hexdigest() for p, data in headers},
            "jmena": sorted(names),
        },
        "vety": vety,
        "stitky": stitky,
        "etalon_nalezu": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rozdil", action="store_true", help="jen ukazat rozdil")
    ap.add_argument(
        "--nova-fixtura", type=pathlib.Path, help="separate snapshot; historical path forbidden"
    )
    ap.add_argument("--kit-ref", help="exact committed kit source")
    ap.add_argument("--sdk-root", type=pathlib.Path)
    ap.add_argument("--sdk-ref", help="exact committed SDK source")
    a = ap.parse_args()

    if a.nova_fixtura is not None:
        if a.rozdil or not all((a.kit_ref, a.sdk_root, a.sdk_ref)):
            ap.error("--nova-fixtura requires --kit-ref, --sdk-root, --sdk-ref and no --rozdil")
        if a.nova_fixtura.resolve() == FIXTURA.resolve() or a.nova_fixtura.exists():
            ap.error("new snapshot must not overwrite an existing/historical file")
        fresh = novy_snimek(KIT.parent, a.kit_ref, a.sdk_root, a.sdk_ref)
        a.nova_fixtura.write_text(
            json.dumps(fresh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"{a.nova_fixtura}: kit {fresh['kit']}, explicit zero SDK oracle")
        return 0
    if any((a.kit_ref, a.sdk_root, a.sdk_ref)):
        ap.error("snapshot refs require --nova-fixtura")

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
