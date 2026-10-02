"""Rule 142, osmy a devaty tvar: KONTROLNI SKUPINA verzalkovych slov z kitu.

REZIDUUM R2 KRITIKA (espos-oprava): z 57 (dnes 65) jmen SDK je nejmene 20
beznych slov - SMALT, ZNAK, JMENO, HLAVNI, PRIMO, INFO, LIVE, NONE, DEBUG,
WARN, BUSY, ... - a slovnik kitu je zrovna smalt/znak/jmeno. Dnes je
0 fantomu, ale "jen nahodou": nikdo to nemeril nad texty kitu. Tenhle
soubor z toho dela mereni s rohatkou:

* `vety`   = 130 textu kitu s malymi pismeny a verzalkovym slovem (trida se
             v nich MERI): nalezu osmeho/devateho tvaru musi byt PRESNE
             etalon (dnes jeden: `ERROR cteni: NotFound`), nic navic
             (fantom) a nic min (ztraceny pravdivy nalez).
* `stitky` = 138 textu cele verzalkami (STITEK, trida se v nich NEMERI):
             0 nalezu osmeho tvaru.
* KONTROLNI SKUPINA S OPACNOU PRAVDOU: bezna slova ze SDK jako STITEK mlci,
  tataz slova UVNITR VETY hlasi - obe pulky meze (a)/(b) u `_V_VERZALKY`
  maji tady svuj dolozeny pruchod nad ZIVYMI jmeny SDK.
* MUTACE DAT: pridat do jmen SDK bezne kitove slovo (BLE, USB, ...) musi
  vyrobit fantom -> dokazuje, ze test meri kitove texty, ne prazdno.
* ZIVY KIT: dnesni texty se porovnavaji se SAMOSTATNYM snimkem 744643f.
  Tenhle commit zamerne odstranil produkcni SDK vetu; dnesni etalon je
  explicitne prazdny. Historicky snimek i jeho must-red kontroly zustavaji.

Fixtura: tests/fixtures/verzalky_kit_2026-09-09.json (odkud a jak, viz jeji
`_o_souboru`).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import runpy
from html.parser import HTMLParser

import pytest

from tests.dilna import repo_path
from tools.validate_design import (
    _V_ROZHRANI,
    _V_VERZALKY,
    VETY_NENI_JMENO_SDK,
    VETY_NENI_ROZHRANI,
    ZNACKA_R142,
    _veta_strojove_jmeno,
    validate_data,
)

FIXTURA = pathlib.Path(__file__).parent / "fixtures" / "verzalky_kit_2026-09-09.json"
SOUCASNA_FIXTURA = FIXTURA.with_name("verzalky_kit_e532e3b.json")
KIT_COMMIT = "e532e3b7c8ebd7c402f255447ba092e4565babd7"
SDK_COMMIT = "cb778d8da0d8994674aff217ef14438ed680ccef"
# ESPOS lezi ve workspace/research/ESPOS, kit ve workspace/tabos-ui-kit:
# tests/ -> ESPOS -> research -> workspace = parents[3] (tataz cesta jako
# `DILNA` v `dilna.py`: ESPOS.parents[1]). S parents[2] test tise skipoval.
KIT_ROOT = repo_path(
    "TABOS_UI_KIT_ROOT", pathlib.Path(__file__).resolve().parents[3] / "tabos-ui-kit"
)
KIT = KIT_ROOT / "navrh-appky"
TVARY_SDK = ("jmeno ze SDK", "jmeno rozhrani ze SDK")


def _fixtura() -> dict:
    return json.loads(FIXTURA.read_text(encoding="utf-8"))


def _soucasna_fixtura() -> dict:
    return json.loads(SOUCASNA_FIXTURA.read_text(encoding="utf-8"))


def _jmena(f) -> frozenset[str]:
    return frozenset(f["jmena_sdk"]["jmena"])


def _nalezy_sdk(texty, jmena):
    """{text: (pojmenovani, kus)} jen pro osmy/devaty tvar."""
    ven = {}
    for t in texty:
        d = _veta_strojove_jmeno(t, jmena)
        if d is not None and d[0] in TVARY_SDK:
            ven[t] = d
    return ven


def _verzalky(text):
    return [
        m.group(0)
        for m in _V_VERZALKY.finditer(text)
        if m.group(0) not in VETY_NENI_ROZHRANI and m.group(0) not in VETY_NENI_JMENO_SDK
    ]


def test_fixtura_je_nabita_a_ma_puvod():
    f = _fixtura()
    # Revize kitu, ze ktere je snimek. Meni se s KAZDOU regeneraci
    # (`tests/fixtures/gen_verzalky_kit.py`) - je to jedine misto, kde
    # se pozna, ze fixtura NENI z dnesnich listu, kdyby nekdo prepsal
    # jen texty a puvod nechal stat.
    assert f["kit"] == "dfbdbbb+dirty-faze0-2026-09-27"
    assert len(f["vety"]) >= 100 and len(f["stitky"]) >= 100 and len(_jmena(f)) >= 50
    # Historical corpus predates named exclusions added to the live gate;
    # assert it still contains measured uppercase tokens, not today's allowlist.
    assert all(_V_VERZALKY.search(v["text"]) for v in f["vety"] + f["stitky"])
    assert all(any(z.islower() for z in v["text"]) for v in f["vety"])
    assert not any(any(z.islower() for z in s["text"]) for s in f["stitky"])
    assert {e["text"] for e in f["etalon_nalezu"]} <= {v["text"] for v in f["vety"]}


def test_vety_kitu_daji_PRESNE_etalon_nalezu_0_fantomu():
    f = _fixtura()
    nalezy = _nalezy_sdk([v["text"] for v in f["vety"]], _jmena(f))
    etalon = {e["text"]: (e["pojmenovani"], e["kus"]) for e in f["etalon_nalezu"]}
    fantomy = {t: d for t, d in nalezy.items() if t not in etalon}
    ztracene = {t: d for t, d in etalon.items() if t not in nalezy}
    assert not fantomy, f"FANTOM osmeho tvaru na textu kitu: {fantomy}"
    assert not ztracene, f"ztraceny pravdivy nalez: {ztracene}"
    assert nalezy == etalon


def test_stitky_kitu_verzalkami_se_NEMERI():
    f = _fixtura()
    assert _nalezy_sdk([s["text"] for s in f["stitky"]], _jmena(f)) == {}


def test_etalon_je_pravdivy_nalez_i_pres_celou_branu():
    f = _fixtura()
    for e in f["etalon_nalezu"]:
        scene = {
            "width": 1280,
            "height": 720,
            "navrh": {"jmena_sdk": sorted(_jmena(f))},
            "widgets": [
                {
                    "type": "label",
                    "x": 40,
                    "y": 200,
                    "width": 400,
                    "height": 20,
                    "text": e["text"],
                    "color_fg": "#e6e1ce",
                    "color_bg": "#14170f",
                    "align": "left",
                    "valign": "middle",
                    "_widget_id": "radek.1",
                }
            ],
        }
        zpravy = [
            i.message
            for i in validate_data(
                {"device": "tab5", "scenes": {"main": scene}},
                file_label="t",
                warnings_as_errors=False,
            )
        ]
        assert [z for z in zpravy if ZNACKA_R142 in z and f"'{e['kus']}'" in z]


def _bezna_slova_sdk(jmena):
    """Jmena SDK, ktera vypadaji jako bezne slovo: bez I-rozhrani, jednohrba."""
    return sorted(
        j
        for j in jmena
        if not _V_ROZHRANI.fullmatch(j)
        and len(j) >= 3
        and sum(1 for z in j[1:] if z.isupper()) == 0
        and j.upper() not in VETY_NENI_JMENO_SDK
    )


def test_kontrolni_skupina_bezna_slova_SDK_jako_STITEK_mlci_ale_ve_VETE_hlasi():
    f = _fixtura()
    jmena = _jmena(f)
    slova = _bezna_slova_sdk(jmena)
    assert len(slova) >= 15, slova  # kritik R2: "nejmene 20 z 57"
    assert {"Smalt", "Znak", "Primo", "Info", "Hlavni"} <= set(slova)
    for s in slova:
        stitek = s.upper()
        assert _veta_strojove_jmeno(stitek, jmena) is None, f"stitek '{stitek}' obvinen"
        assert _veta_strojove_jmeno(f"STAV {stitek}", jmena) is None
        veta = f"stav je {stitek} a mereni pokracuje"
        assert _veta_strojove_jmeno(veta, jmena) == ("jmeno ze SDK", stitek), veta


def test_kitove_stitky_ktere_jsou_zaroven_jmenem_SDK_jsou_dnes_nula():
    """Rohatka: kolik kitovych stitku se trefi do jmen SDK (dnes 0). Az bude
    prvni, ma tu pribyt do seznamu a test ho ma pojmenovat, ne umlcet."""
    f = _fixtura()
    velka = {j.upper() for j in _jmena(f)}
    kolize = sorted(
        s["text"] for s in f["stitky"] if any(v.upper() in velka for v in _verzalky(s["text"]))
    )
    assert kolize == []


@pytest.mark.parametrize("slovo", ["BLE", "USB", "LA1010", "ESP32", "PHY", "NERTERA"])
def test_MUTACE_DAT_kitove_slovo_v_SDK_je_fantom(slovo):
    """Kdyby se do SDK dostal enum `Ble` nebo `Usb`, brana by obvinila
    kitove vety. Test to musi VIDET - jinak by nemeril kitove texty."""
    f = _fixtura()
    jmena = _jmena(f) | {slovo.capitalize()}
    nalezy = _nalezy_sdk([v["text"] for v in f["vety"]], jmena)
    fantomy = {t: d for t, d in nalezy.items() if d[1] == slovo}
    assert len(fantomy) >= 1, slovo


def test_dva_behy_tyz_vysledek():
    f = _fixtura()
    texty = [v["text"] for v in f["vety"]]
    assert _nalezy_sdk(texty, _jmena(f)) == _nalezy_sdk(texty, _jmena(f))


# --------------------------------------------------------------------------- #
# Zivy kit vedle ESPOSu: tataz rohatka nad dnesnimi listy
# --------------------------------------------------------------------------- #


class _Texty(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texty: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if self.skip:
            return
        d = " ".join(data.split())
        if d:
            self.texty.append(d)


def _texty_kitu():
    listy = sorted(KIT.glob("*.dc.html"))
    if not listy:
        pytest.skip(f"NEZMERENO: {KIT} nema zadny *.dc.html - kit neni vedle ESPOSu")
    ven = []
    for cesta in listy:
        p = _Texty()
        p.feed(cesta.read_text(encoding="utf-8"))
        ven.extend(t for t in p.texty if _verzalky(t))
    return ven


def test_zivy_kit_vety_0_fantomu_a_etalon_drzi():
    f = _soucasna_fixtura()
    vety = sorted({t for t in _texty_kitu() if any(z.islower() for z in t)})
    nalezy = _nalezy_sdk(vety, _jmena(f))
    etalon = {e["text"] for e in f["etalon_nalezu"]}
    fantomy = {t: d for t, d in nalezy.items() if t not in etalon}
    assert not fantomy, f"FANTOM na zivem listu kitu: {fantomy}"
    assert set(nalezy) == etalon


def test_zivy_kit_snimek_nezastaral():
    """Live text drift must stay visible against the independent current snapshot."""
    f = _soucasna_fixtura()
    zive = sorted(set(_texty_kitu()))
    snimek = sorted({v["text"] for v in f["vety"]} | {s["text"] for s in f["stitky"]})
    navic, chybi = sorted(set(zive) - set(snimek)), sorted(set(snimek) - set(zive))
    assert not navic and not chybi, (
        f"snimek kitu zastaral: {len(navic)} textu navic, {len(chybi)} chybi; "
        f"navic={navic[:5]} chybi={chybi[:5]}"
    )


def test_historicky_snimek_a_kladny_etalon_jsou_nezmenene():
    # Content guard is portable across Git's Windows CRLF / Linux LF checkout.
    assert hashlib.sha256(FIXTURA.read_text(encoding="utf-8").encode("utf-8")).hexdigest() == (
        "fe6afdcb0605b49807746a08ce58ecd28903faf2da469ee7f1b387d77e5afcf7"
    )
    assert [e["text"] for e in _fixtura()["etalon_nalezu"]] == ["ERROR cteni: NotFound"]


def test_soucasny_snimek_ma_presny_puvod_a_explicitni_nulovy_etalon():
    f = _soucasna_fixtura()
    assert f["kit"] == KIT_COMMIT and f["jmena_sdk"]["commit"] == SDK_COMMIT
    assert len(f["listy_sha256"]) == 42
    assert len(f["jmena_sdk"]["hlavicky_sha256"]) == 37
    assert len(_jmena(f)) == 78
    assert len(f["vety"]) >= 100 and len(f["stitky"]) >= 100
    for entries in (f["listy_sha256"], f["jmena_sdk"]["hlavicky_sha256"]):
        assert all(len(v) == 64 and set(v) <= set("0123456789abcdef") for v in entries.values())
    assert f["etalon_nalezu"] == []
    assert "ERROR cteni: NotFound" not in {v["text"] for v in f["vety"]}
    assert _nalezy_sdk([v["text"] for v in f["vety"]], _jmena(f)) == {}
    assert _nalezy_sdk([v["text"] for v in f["stitky"]], _jmena(f)) == {}


@pytest.mark.parametrize(
    "text",
    [
        "ERROR cteni: NotFound",
        "stav je ERROR a mereni pokracuje",
        "stav poskytuje IHWDIAGNOSTICS a mereni pokracuje",
    ],
)
def test_soucasny_snimek_s_vlozenym_sdk_unikem_musi_zcervenat(text):
    f = _soucasna_fixtura()
    original = [v["text"] for v in f["vety"]]
    assert _nalezy_sdk(original, _jmena(f)) == {}
    assert set(_nalezy_sdk([*original, text], _jmena(f))) == {text}
    # Positive oracle goes through the actual gate, independently of the parser.
    data = {
        "device": "tab5",
        "scenes": {
            "main": {
                "width": 1280,
                "height": 720,
                "navrh": {"jmena_sdk": sorted(_jmena(f))},
                "widgets": [
                    {
                        "type": "label",
                        "_widget_id": "injected.1",
                        "x": 40,
                        "y": 200,
                        "width": 900,
                        "height": 24,
                        "text": text,
                        "color_fg": "#e6e1ce",
                        "color_bg": "#14170f",
                    }
                ],
            }
        },
    }
    found = [
        i
        for i in validate_data(data, file_label="sdk_injection", warnings_as_errors=False)
        if ZNACKA_R142 in i.message
    ]
    assert len(found) == 1 and found[0].level == "ERROR"


def test_soucasny_snimek_je_reprodukovatelny_z_commit_blobu():
    sdk = (
        repo_path("TABOS_CORE_ROOT", KIT_ROOT.parent / "tabos-core") / "apps" / "_src" / "tabos-sdk"
    )
    if not KIT.is_dir() or not sdk.is_dir():
        pytest.skip("NEZMERENO: local kit/SDK repositories absent; recorded snapshot still tested")
    generator = runpy.run_path(str(FIXTURA.with_name("gen_verzalky_kit.py")))
    fresh = generator["novy_snimek"](KIT.parent, KIT_COMMIT, sdk, SDK_COMMIT)
    assert fresh == _soucasna_fixtura()


def test_generator_nesmi_prevzit_sdk_unik_jako_novy_etalon(monkeypatch):
    generator = runpy.run_path(str(FIXTURA.with_name("gen_verzalky_kit.py")))
    build = generator["novy_snimek"]

    def committed(root, ref, folder, suffix):
        if suffix == ".h":
            return SDK_COMMIT, [("include/test.h", b"enum class E { Error, NotFound };")]
        return KIT_COMMIT, [
            ("navrh-appky/Test.dc.html", b"<p>stav je ERROR a mereni pokracuje</p>")
        ]

    monkeypatch.setitem(build.__globals__, "_committed_files", committed)
    with pytest.raises(ValueError, match="explicit zero oracle"):
        build(KIT.parent, KIT_COMMIT, KIT.parent, SDK_COMMIT)


def test_generator_noveho_snimku_nesmi_prepsat_historii(monkeypatch):
    generator = runpy.run_path(str(FIXTURA.with_name("gen_verzalky_kit.py")))
    monkeypatch.setattr(
        "sys.argv",
        [
            "gen_verzalky_kit.py",
            "--nova-fixtura",
            str(FIXTURA),
            "--kit-ref",
            KIT_COMMIT,
            "--sdk-root",
            str(KIT),
            "--sdk-ref",
            SDK_COMMIT,
        ],
    )
    with pytest.raises(SystemExit) as raised:
        generator["main"]()
    assert raised.value.code == 2
