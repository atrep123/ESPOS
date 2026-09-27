"""Generator fixtur pravidla 153 (Zpet jen mimo koren).

    python tests/fixtures/gen_zpet_koren.py

Sest listu, jedna kresba. Cisla NEJSOU vymyslena: jsou to hodnoty, ktere
most kitu opravdu vydava (`tabos-ui-kit/navrh-appky/_scena_SvorkaFiles.dc.json`
a `_scena_SvorkaDomu.dc.json`, zmereno 10. 9. 2026) a ktere stoji v
`tokens.json: layout` (`zpet` = {x: 1148, w: 112}, `hlavicka` = {y: 8, h: 81}).

  tab5_zpet_ciste.json         ne-koren, Zpet na svem miste    -> ticho
  tab5_zpet_koren_ciste.json   KOREN bez Zpet (dnesni Domov)   -> ticho
  tab5_zpet_koren_vady.json    KOREN a presto Zpet             -> R153 koren
  tab5_zpet_chybi_vady.json    ne-koren bez Zpet               -> R153 chybi
  tab5_zpet_misto_vady.json    ne-koren, Zpet o 1 px vedle     -> R153 misto
  tab5_zpet_nemereno_vady.json scena z mostu bez `koren`       -> R153 NEMERENO

Dvojice `chybi_vady` x `koren_ciste` ma BAJT PO BAJTU tutez kresbu i tyz blok
`navrh` az na `koren` - opacny verdikt tedy nemuze pochazet z niceho jineho.
V kazdem listu stoji navic `dlazdice.0` jako KONTROLNI SKUPINA: dotykovy
ovladac, ktery Zpet NENI (a bez ktereho by list bez Zpet mohl projit uz tim,
ze na nem neco zmacknout jde).

POSLEDNI Z NICH JE TU ZA DVE VECI. Krome hranice "o jediny pixel" ukazuje,
PROC se poloha nesmi merit proti `navrh.pasy["navigace"]`: pas na listech
kitu zaklada SAM prvek `.zpet`, takze posunuty knoflik si pas posune s sebou
(fixtura to tak i ma, [1149, 8, 112, 81]). Meridlo postavene na pasu by tedy
merilo tlacitko proti sobe a nevystrelilo by nikdy - a Rule 136 na nem taky
mlci, protoze prvek ze sveho pasu nevycniva. Nalez vydá jedine DEKLARACE
z `tokens.json`.

Generator se pousti rukou po zmene tvaru bloku `navrh`; fixtury se commituji.
"""

from __future__ import annotations

import json
import pathlib

ZDE = pathlib.Path(__file__).resolve().parent

# tokens.json: layout.zpet + layout.hlavicka (opsano; test
# test_r153_deklarace_sedi_s_tokens_kitu porovnava s primarnim udajem, kdyz
# je kit po ruce).
MISTO = {"x": 1148, "y": 8, "w": 112, "h": 81}
PAS_HLAVICKA = [36, 8, 1100, 81]

INKOUST = "#e4dfcc"
PODKLAD = "#14170f"
SMALT = "#e6e1ce"
TMAVY = "#12150e"

# tokens.json: colors (tataz paleta, jakou vozi most kitu do kazde sceny)
PALETA = [
    "#14170F",
    "#1C2016",
    "#A9C24A",
    "#9BA28D",
    "#E9A63C",
    "#FF7B5E",
    "#E4DFCC",
    "#E27BE2",
    "#6F7764",
    "#E6E1CE",
    "#12150E",
    "#5A5F4C",
    "#6B6653",
]
SKALA = {"rezy": [14, 16, 20, 24, 32], "vyjimky": {}}
SOUSTAVA = {"pole_x": 20, "vsazka": 16}
# Jmena ze SDK (Rule 142, osmy tvar). Staci ta dve, ktera se na listech
# opravdu vyskytnou - bez nich by kazdy list nesl WARN "jmena SDK nedodana"
# a mereni pravidla 153 by se v nem hledalo hure.
JMENA_SDK = ["ITabOsApp", "IHwDiagnostics"]


def _orez(w: int, h: int) -> dict:
    return {"sirka_obsahu": w, "sirka_schranky": w, "vyska_obsahu": h, "vyska_schranky": h}


def _w(
    wid: str,
    x: int,
    y: int,
    w: int,
    h: int,
    text: str,
    typ: str,
    fg: str = INKOUST,
    bg: str = PODKLAD,
) -> dict:
    return {
        "type": typ,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": text,
        "color_fg": fg,
        "color_bg": bg,
        "border": False,
        "border_style": "none",
        "align": "left",
        "valign": "middle",
        "_widget_id": wid,
    }


def _list(*, koren: bool | None, zpet: tuple[int, int, int, int] | None, puvod: list[str]) -> dict:
    """Jeden list: hlavicka s titulkem, pole obsahu, volitelne Zpet."""
    widgets = [
        _w("titulek.8", 36, 39, 79, 18, "Soubory", "label"),
        _w("obsah.20", 20, 97, 1240, 603, "", "panel", fg=TMAVY, bg=SMALT),
        _w(
            "veta.21", 36, 129, 420, 24, "Zaznam kanalu je pripraveny.", "label", fg=TMAVY, bg=SMALT
        ),
        # KONTROLNI SKUPINA v KAZDEM listu: dotykovy ovladac, ktery Zpet
        # NENI. Pravidlo se pta na tlacitko Zpet, ne na "nejaky knoflik" -
        # bez teto dlazdice by list bez Zpet mohl projit uz tim, ze na nem
        # neco zmacknout jde. (Mimochodem umlci Rule 115 "navigation
        # dead-end", ktera by jinak zastinila mereni.)
        _w("dlazdice.0", 48, 320, 386, 120, "Terminal", "button", fg=TMAVY, bg=SMALT),
    ]
    prvky = {
        "titulek.8": {
            "pas": "hlavicka",
            "orez": _orez(79, 18),
            "font_size": 20,
            "inkoust": INKOUST,
            "podklad": PODKLAD,
        },
        "obsah.20": {"orez": _orez(1240, 603)},
        "veta.21": {
            "rodic": [20, 97, 1240, 603],
            "rodic_id": "obsah.20",
            "orez": _orez(420, 24),
            "font_size": 20,
            "inkoust": TMAVY,
            "podklad": SMALT,
        },
        "dlazdice.0": {
            "rodic": [20, 97, 1240, 603],
            "rodic_id": "obsah.20",
            "orez": _orez(386, 120),
            "font_size": 24,
            "inkoust": TMAVY,
            "podklad": SMALT,
        },
    }
    pasy = {"hlavicka": PAS_HLAVICKA}
    if zpet is not None:
        x, y, w, h = zpet
        widgets.insert(1, _w("zpet.10", x, y, w, h, "Zpet", "button"))
        prvky["zpet.10"] = {
            "pas": "navigace",
            "orez": _orez(w, h),
            "font_size": 16,
            "inkoust": INKOUST,
            "podklad": PODKLAD,
        }
        # Pas navigace ZAKLADA sam prvek `.zpet` (nese `data-pas-vyska`),
        # takze se posouva s nim - presne jak to dela most nad artboardem.
        pasy["navigace"] = [x, y, w, h]
    return {
        "_puvod": puvod,
        "device": "tab5",
        "width": 1280,
        "height": 720,
        "scenes": {
            "main": {
                "name": "main",
                "width": 1280,
                "height": 720,
                "bg_color": PODKLAD,
                "navrh": {
                    # `koren=None` = klic v bloku VUBEC NENI (starsi most).
                    # Neni to "neni koren": pravidlo pak nemeri a rekne to.
                    **({} if koren is None else {"koren": koren}),
                    "navigace": dict(MISTO),
                    "pasy": pasy,
                    "prvky": prvky,
                    "skala": SKALA,
                    "paleta": PALETA,
                    "soustava": SOUSTAVA,
                    "jmena_sdk": JMENA_SDK,
                },
                "widgets": widgets,
            }
        },
    }


LISTY = {
    "tab5_zpet_ciste.json": _list(
        koren=False,
        zpet=(MISTO["x"], MISTO["y"], MISTO["w"], MISTO["h"]),
        puvod=[
            "R153 NEGATIVNI TRIDA: obycejna appka (jako SvorkaFiles). Neni koren,",
            "tlacitko Zpet ma, a stoji na deklarovanem miste 112x81 na 1148,8.",
            "Pravidlo 153 nad nim MLCI - a mlci proto, ze zmerilo, ne proto, ze",
            "se neptalo (priznak `koren` i deklarace `navigace` v bloku jsou).",
        ],
    ),
    "tab5_zpet_koren_vady.json": _list(
        koren=True,
        zpet=(MISTO["x"], MISTO["y"], MISTO["w"], MISTO["h"]),
        puvod=[
            "R153 POZITIVNI TRIDA A: KOREN navigace (Domov) s tlacitkem Zpet.",
            "Presne takhle artboard SvorkaDomu vypadal do 10. 9. 2026, zatimco",
            "deska ho uz kreslila bez nej (shell.cpp skryva Zpet pres",
            "LV_OBJ_FLAG_HIDDEN). Tlacitko na koreni nema kam vest - je to slib",
            "bez pokryti, tentyz nalez jako zakazane 'Srovnat podle site'.",
        ],
    ),
    "tab5_zpet_chybi_vady.json": _list(
        koren=False,
        zpet=None,
        puvod=[
            "R153 POZITIVNI TRIDA B: list, ktery NENI koren, a Zpet nema.",
            "Druha strana teze mince a duvod, proc pravidlo potrebuje PRIZNAK:",
            "od korene se tenhle list lisi jedine tim, co o sobe rekl generator.",
            "Kresba je bajt po bajtu tataz jako v tab5_zpet_koren_ciste.json.",
        ],
    ),
    "tab5_zpet_koren_ciste.json": _list(
        koren=True,
        zpet=None,
        puvod=[
            "R153 NEGATIVNI TRIDA: KOREN navigace bez tlacitka Zpet - dnesni",
            "SvorkaDomu a dnesni deska. Kontrolni skupina k",
            "tab5_zpet_chybi_vady.json: tataz kresba, opacny verdikt, a lisi je",
            "jedine priznak `navrh.koren`.",
        ],
    ),
    "tab5_zpet_nemereno_vady.json": _list(
        koren=None,
        zpet=(MISTO["x"], MISTO["y"], MISTO["w"], MISTO["h"]),
        puvod=[
            "R153 NEMERENO: scena Z MOSTU (prvky nesou `orez`), ale bez priznaku",
            "`navrh.koren`. Presne takhle vypada scena ze STARSIHO mostu. Kresba",
            "je tataz jako v tab5_zpet_ciste.json - jedine, co chybi, je vyrok",
            "generatora o tom, ktera trida to je. Fail-closed: nemereni se hlasi",
            "nahlas, protoze o listu netvrdi nic, a ticho by vypadalo jako zelena.",
        ],
    ),
    "tab5_zpet_misto_vady.json": _list(
        koren=False,
        zpet=(MISTO["x"] + 1, MISTO["y"], MISTO["w"], MISTO["h"]),
        puvod=[
            "R153 POZITIVNI TRIDA C: Zpet o JEDINY pixel vedle (x=1149 misto 1148).",
            "Hranice pravidla: poloha se meri na pixel, protoze obe strany jsou",
            "cela cisla z tehoz tokens.json a neni mezi nimi zadny zaokrouhlujici",
            "prevod. Pas `navigace` je tu posunuty S TLACITKEM ([1149,8,112,81]),",
            "protoze ho tlacitko zaklada - takze Rule 136 mlci a meridlo",
            "postavene na pasu by mlcelo taky. Nalez vyda jen deklarace.",
        ],
    ),
}


def main() -> None:
    for jmeno, data in LISTY.items():
        (ZDE / jmeno).write_text(
            json.dumps(data, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("+", jmeno)


if __name__ == "__main__":
    main()
