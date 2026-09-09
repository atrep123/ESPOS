"""Testy pravidel 144-147 v `tools/validate_design.py`.

Druha vlna pravidel nad MERENYMI daty z artboardu (scenovy blok ``navrh``,
ktery vozi most `tabos-ui-kit/navrh-appky/do_espos.py`). Vsechna ctyri merila
do 2026-09-09 meridla v kitu, ktera nemela ani jeden test - tady se z nich
stavaji pravidla s pozitivni i negativni tridou.

Rule 144: text, ktery SKUTECNE useknula jeho schranka (``scrollWidth`` >
          ``clientWidth``). JINA VELICINA nez Rule 137: ta meri, jestli se
          text vejde do DEKLAROVANE bunky (``data-bunka``), a na listu
          SvorkaCislice hlasi ERROR o textu, ktery se sve delici cary ani
          nedotkne. Zavira reziduum R1 kritika.
Rule 145: text zalomeny do vic radku, nez pro nej bylo mista (``scrollHeight``
          > ``clientHeight``). Zavira reziduum bodu 7 kritika: prvek se
          svisle NEPRETECE, jeho obdelnik zustane spravny a zmizi DRUHY
          RADEK - to nechyti zadna kontrola presahu.
Rule 146: cizi text lezici na smaltove plose (obracena polarita inkoust /
          smalt). Zakon jazyka: svetla smaltova plocha nese TMAVY inkoust,
          ktery na ni PATRI - text, ktery na ni jen lezi, se kresli barvou
          tmave strany. Stalo se to tretikrat (tlacitko Odpojit, popisek
          tridy .stitek, popisek vodopadu).
Rule 147: delici cara vede pres text. Meri se INKOUST, ne box - a je to
          rozdil se zmerenym dopadem, viz `test_r147_realny_Main_mlci`.

Ke kazdemu pravidlu je POZITIVNI trida (vystreli), NEGATIVNI (mlci) i
hranice na pixel. Navic tri veci, bez kterych by testy netestovaly nic:

* **Nosic je legalni.** Fixtury jdou pres `validate_file`, tedy vcetne
  POVINNEHO JSON schematu - jinak by se neoverilo, ze scena takovy blok
  vubec smi nest.
* **Profilove gatovani ma obe strany.** R146 a R147 jsou zakony TabOSu, ne
  vlastnost skla; testy proto meri tutez scenu na tab5 (hlasi) i na
  oled256 (mlci).
* **Rozbita smlouva se hlasi NAHLAS.** Neuplny ``orez`` neni "nemereno", je
  to ERROR a cela hodnota se zahodi - pulka mereni by jinak vyrobila vetev
  "kontrola NEPROBEHLA", na kterou by se nad dnesnim mostem nikdy nedoslo
  (mrtvou vetev tehoz druhu nasel kritik u `ZNACKA_R137_NEMERENO`).
"""

from __future__ import annotations

import json
import pathlib

from tools.validate_design import (
    OREZ_KLICE,
    PROFILE_OLED256,
    PROFILE_TAB5,
    R144_PRAH_PX,
    R145_PRAH_PX,
    R146_PRAH_PX,
    R147_ODSTUP_PX,
    ZNACKA_NAVRH_VADNY,
    ZNACKA_R137,
    ZNACKA_R144,
    ZNACKA_R145,
    ZNACKA_R146,
    ZNACKA_R147,
    validate_data,
    validate_file,
)

FL = "test"
FIXTURY = pathlib.Path(__file__).parent / "fixtures"
OREZ_CISTA = FIXTURY / "tab5_orez_ciste.json"
OREZ_VADY = FIXTURY / "tab5_orez_vady.json"
POLARITA_CISTA = FIXTURY / "tab5_polarita_ciste.json"
POLARITA_VADY = FIXTURY / "tab5_polarita_vady.json"
CARY_CISTE = FIXTURY / "tab5_cary_ciste.json"
CARY_VADY = FIXTURY / "tab5_cary_vady.json"

# Inkoust textu "Zatim neni co ukazovat" na listu Main kitu a sit, ktera pod
# nim lezi. Obe cisla jsou ZMERENA (2026-09-09), ne vymyslena: box tehoz
# prvku je 537,140 686x229, takze meridlo kitu nad BOXEM hlasilo nalez,
# zatimco nad INKOUSTEM je nejblizsi cara 4 px nad prvnim pixelem pisma.
MAIN_INKOUST = (537, 248, 686, 12)
MAIN_CARY = [[537, 192, 688, 1], [537, 244, 688, 1], [537, 296, 688, 1], [537, 348, 688, 1]]


def _w(wid, x, y, ww, hh, *, text="AHOJ", t="label", **kw):
    d = {
        "type": t,
        "x": x,
        "y": y,
        "width": ww,
        "height": hh,
        "text": text,
        "color_fg": "#e6e1ce",
        "color_bg": "#14170f",
        "align": "left",
        "valign": "middle",
        "_widget_id": wid,
    }
    d.update(kw)
    return d


def _make(widgets, *, navrh=None, scene_w=1280, scene_h=720, device="tab5"):
    scene = {"width": scene_w, "height": scene_h, "widgets": widgets}
    if navrh is not None:
        scene["navrh"] = navrh
    data = {"scenes": {"main": scene}}
    if device is not None:
        data["device"] = device
    return data


def _issues(data, **kw):
    return validate_data(data, file_label=FL, warnings_as_errors=False, **kw)


def _msgs(data, **kw):
    return [i.message for i in _issues(data, **kw)]


def _errors(data, **kw):
    return [i.message for i in _issues(data, **kw) if i.level == "ERROR"]


def _obsahuji(zpravy, kus):
    return [m for m in zpravy if kus in m]


def _orez(so, ss, vo, vs):
    return {
        "sirka_obsahu": so,
        "sirka_schranky": ss,
        "vyska_obsahu": vo,
        "vyska_schranky": vs,
    }


# --------------------------------------------------------------------------- #
# Nosic: rozsirena smlouva o atributech
# --------------------------------------------------------------------------- #


def test_znacky_144_147_jsou_ASCII():
    """Hlasky se tisknou i na holou cp1250 konzoli; znacka musi projit vzdy."""
    for znacka in (ZNACKA_R144, ZNACKA_R145, ZNACKA_R146, ZNACKA_R147):
        assert znacka == znacka.encode("ascii", "replace").decode("ascii")


def test_znacky_144_147_se_navzajem_nepohlcuji():
    """`do_espos._trida` bere PRVNI sedici vzor - znacka nesmi byt predponou
    jine, jinak by nalez spadl do cizi kategorie."""
    znacky = (ZNACKA_R144, ZNACKA_R145, ZNACKA_R146, ZNACKA_R147)
    for a in znacky:
        for b in znacky:
            if a is not b:
                assert a not in b


def test_bez_bloku_navrh_nova_pravidla_mlci():
    """Text, cara i plocha - ale nikdo nic nezmeril."""
    d = _make([_w("a", 537, 248, 686, 12, text="Zatim neni co ukazovat")])
    msgs = _msgs(d)
    for znacka in (ZNACKA_R144, ZNACKA_R145, ZNACKA_R146, ZNACKA_R147):
        assert _obsahuji(msgs, znacka) == []


def test_orez_neni_objekt_je_ERROR():
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"orez": [200, 200]}}})
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'prvky.a.orez' ma byt objekt se ctyrmi "
        f"rozmery {list(OREZ_KLICE)}, je list"
    ) in _errors(d)


def test_orez_bez_ctvrteho_klice_je_ERROR_a_pravidlo_nemeri():
    """Pulka mereni neni mezera v pokryti, ale rozbita smlouva.

    Pozitivni kontrola je hned pod tim: TYZ prvek s uplnym `orez` hlasit
    MUSI - jinak by tenhle test prosel i tehdy, kdyby Rule 144 nemerila nic.
    """
    pul = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": {"sirka_obsahu": 320, "sirka_schranky": 200}}}},
    )
    msgs = _msgs(pul)
    assert _obsahuji(msgs, "'prvky.a.orez.vyska_obsahu' ma byt nezaporne cislo")
    assert _obsahuji(msgs, "'prvky.a.orez.vyska_schranky' ma byt nezaporne cislo")
    assert _obsahuji(msgs, ZNACKA_R144) == []

    cely = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": _orez(320, 200, 20, 20)}}},
    )
    assert _obsahuji(_errors(cely), ZNACKA_R144) != []


def test_orez_zna_navic_klic_je_ERROR():
    """Preklep v nazvu rozmeru nesmi projit jako 'zmereno'."""
    o = _orez(200, 200, 20, 20)
    o["sirka_bunky"] = 180
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"orez": o}}})
    assert _obsahuji(
        _errors(d), "'prvky.a.orez' zna klice sirka_bunky, ktere pravidla 144 a 145 neumi"
    )


def test_orez_zaporny_rozmer_je_ERROR():
    d = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": _orez(-1, 200, 20, 20)}}},
    )
    assert _obsahuji(_errors(d), "'prvky.a.orez.sirka_obsahu' ma byt nezaporne cislo")


def test_font_size_musi_byt_kladne_cislo():
    """Nosic pravidel 148/149. Sam nic nespousti - meri se tim, ze vadna
    hodnota je ERROR a dobra projde bez jedineho slova o vadnem bloku."""
    spatne = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"font_size": 0}}})
    assert _obsahuji(_errors(spatne), "'prvky.a.font_size' ma byt kladne cislo v px, je 0")
    dobre = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"font_size": 16}}})
    assert _obsahuji(_msgs(dobre), ZNACKA_NAVRH_VADNY) == []


def test_enabled_musi_byt_pravdivostni_hodnota():
    """Retezec 'false' je v Pythonu PRAVDIVY, takze by vyjimku WCAG 1.4.3
    tise otocil naruby."""
    spatne = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"enabled": "false"}}})
    assert _obsahuji(_errors(spatne), "'prvky.a.enabled' ma byt true nebo false, je 'false'")
    for hodnota in (True, False):
        dobre = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"enabled": hodnota}}})
        assert _obsahuji(_msgs(dobre), ZNACKA_NAVRH_VADNY) == []


def test_plochy_nejsou_seznam_je_ERROR():
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"plochy": {"a": True}})
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'plochy' ma byt seznam jmen prvku, je dict"
    ) in _errors(d)


def test_plocha_mimo_scenu_je_ERROR():
    """Tise zahozena plocha by pravidlo vypnula beze slova."""
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"plochy": ["neexistuje"]})
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'plochy[0]' odkazuje na prvek "
        f"'neexistuje', ktery ve scene neni"
    ) in _errors(d)


def test_plocha_uvedena_dvakrat_nehlasi_dvakrat():
    """Jedna obet, jeden nalez - i kdyz most posle jmeno dvakrat."""
    d = _make(
        [
            _w("smalt.1", 100, 100, 300, 40, text="", t="panel"),
            _w("cizi.2", 110, 105, 80, 20, text="VOLNO"),
        ],
        navrh={"plochy": ["smalt.1", "smalt.1"]},
    )
    assert len(_obsahuji(_errors(d), ZNACKA_R146)) == 1


def test_cary_nejsou_seznam_je_ERROR():
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"cary": "537,244"})
    assert (
        f"{FL}: main: {ZNACKA_NAVRH_VADNY}: 'cary' ma byt seznam obdelniku, je str"
    ) in _errors(d)


def test_cara_s_nulovou_vyskou_je_ERROR():
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"cary": [[537, 244, 688, 0]]})
    assert _obsahuji(_errors(d), "'cary[0]' ma byt ctyri cela cisla")


# --------------------------------------------------------------------------- #
# Rule 144: text useknuty svou schrankou
# --------------------------------------------------------------------------- #


def test_r144_useknuty_text_je_ERROR():
    d = _make(
        [_w("stitek.firmware", 256, 229, 149, 24, text="0.9.3 - IDF 5.4.2 - dirty")],
        navrh={"prvky": {"stitek.firmware": {"orez": _orez(212, 149, 24, 24)}}},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (stitek.firmware): {ZNACKA_R144}: "
        f"obsah je 212 px siroky, videt je 149 px (useklo se 63 px), "
        f"text '0.9.3 - IDF 5.4.2 - dirty'"
    ]


def test_r144_hranice_na_pixel():
    """Prah je `R144_PRAH_PX`: o pixel min mlci, o pixel vic hlasi."""
    pod = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": _orez(200 + R144_PRAH_PX - 1, 200, 20, 20)}}},
    )
    assert _obsahuji(_msgs(pod), ZNACKA_R144) == []
    na = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": _orez(200 + R144_PRAH_PX, 200, 20, 20)}}},
    )
    assert len(_obsahuji(_errors(na), ZNACKA_R144)) == 1


def test_r144_bez_orezu_mlci():
    d = _make([_w("a", 40, 100, 200, 20)], navrh={"prvky": {"a": {"role": "hodnota"}}})
    assert _obsahuji(_msgs(d), ZNACKA_R144) == []


def test_r144_prazdny_text_patri_Rule_138_ne_sem():
    """Prazdna schranka nic neusekla; prazdny slib meri Rule 138."""
    d = _make(
        [_w("a", 40, 100, 200, 20, text="")],
        navrh={"prvky": {"a": {"role": "hodnota", "orez": _orez(320, 200, 20, 20)}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R144) == []


def test_r144_neviditelny_prvek_mlci():
    d = _make(
        [_w("a", 40, 100, 200, 20, visible=False)],
        navrh={"prvky": {"a": {"orez": _orez(320, 200, 20, 20)}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R144) == []


def test_r144_a_r137_meri_ruzne_veliciny():
    """Dve pravidla, dve otazky - a kazde umi mlcet tam, kde druhe hlasi.

    Cisla prvniho pripadu jsou ze SvorkaCislice kitu: Rule 137 tam hlasi
    ERROR (text 290,1 px do deklarovane bunky 278 px), ale schranka nic
    neusekla. Druhy pripad je obraceny: text se do bunky vejde a schranka
    ho presto oreze.
    """
    jen_137 = _make(
        [_w("txt.93", 36, 140, 291, 19, text="obrysy z Montserrat-Medium, 4 bpp")],
        navrh={
            "prvky": {
                "txt.93": {
                    "sirka_bunky": 278.0,
                    "sirka_textu": 290.1,
                    "orez": _orez(291, 291, 19, 19),
                }
            }
        },
    )
    chyby = _errors(jen_137)
    assert _obsahuji(chyby, ZNACKA_R137) != []
    assert _obsahuji(chyby, ZNACKA_R144) == []

    jen_144 = _make(
        [_w("txt.93", 36, 140, 291, 19, text="obrysy z Montserrat-Medium, 4 bpp")],
        navrh={
            "prvky": {
                "txt.93": {
                    "sirka_bunky": 400.0,
                    "sirka_textu": 290.1,
                    "orez": _orez(320, 291, 19, 19),
                }
            }
        },
    )
    chyby = _errors(jen_144)
    assert _obsahuji(chyby, ZNACKA_R137) == []
    assert _obsahuji(chyby, ZNACKA_R144) != []


# --------------------------------------------------------------------------- #
# Rule 145: svisle preteceni
# --------------------------------------------------------------------------- #


def test_r145_druhy_radek_v_jednoradkove_bunce_je_ERROR():
    d = _make(
        [_w("stav.radek", 36, 300, 200, 19, text="Nicht verbunden")],
        navrh={"prvky": {"stav.radek": {"orez": _orez(200, 200, 38, 19)}}},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (stav.radek): {ZNACKA_R145}: "
        f"obsah je 38 px vysoky, videt je 19 px (useklo se 19 px dolu), "
        f"text 'Nicht verbunden'"
    ]


def test_r145_hranice_na_pixel():
    pod = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": _orez(200, 200, 19 + R145_PRAH_PX - 1, 19)}}},
    )
    assert _obsahuji(_msgs(pod), ZNACKA_R145) == []
    na = _make(
        [_w("a", 40, 100, 200, 20)],
        navrh={"prvky": {"a": {"orez": _orez(200, 200, 19 + R145_PRAH_PX, 19)}}},
    )
    assert len(_obsahuji(_errors(na), ZNACKA_R145)) == 1


def test_r145_je_nezavisla_na_r144():
    """Vodorovne se vejde, svisle ne - a naopak."""
    jen_svisle = _make(
        [_w("a", 40, 100, 200, 19)],
        navrh={"prvky": {"a": {"orez": _orez(200, 200, 38, 19)}}},
    )
    chyby = _errors(jen_svisle)
    assert _obsahuji(chyby, ZNACKA_R145) != []
    assert _obsahuji(chyby, ZNACKA_R144) == []

    jen_vodorovne = _make(
        [_w("a", 40, 100, 200, 19)],
        navrh={"prvky": {"a": {"orez": _orez(320, 200, 19, 19)}}},
    )
    chyby = _errors(jen_vodorovne)
    assert _obsahuji(chyby, ZNACKA_R144) != []
    assert _obsahuji(chyby, ZNACKA_R145) == []


# --------------------------------------------------------------------------- #
# Rule 146: polarita smaltu
# --------------------------------------------------------------------------- #


def _smalt_scena(*, rodic_id=True, text_x=300, text_y=200, plochy=("stitek.1",), **kw):
    """Vyrobni stitek ze SvorkaDomu (36,113 413x154) + text na nem."""
    prvky = {"k.2": {"rodic_id": "stitek.1"}} if rodic_id else {"k.2": {"rodic": [36, 113, 413, 154]}}
    prvky.update(kw.pop("prvky", {}))
    return _make(
        [
            _w("stitek.1", 36, 113, 413, 154, text="", t="panel", border=True),
            _w("k.2", 52, 125, 62, 19, text="TabOS"),
            _w("odpojit.5", text_x, text_y, 120, 24, text="Odpojit"),
        ],
        navrh={"plochy": list(plochy), "prvky": prvky},
        **kw,
    )


def test_r146_cizi_text_na_smaltu_je_ERROR():
    d = _smalt_scena()
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[2] (odpojit.5): {ZNACKA_R146}: "
        f"text 'Odpojit' lezi na smaltove plose 'stitek.1' (36,113 413x154), "
        f"ale neni jeji soucasti - inkoust a smalt maji obracenou polaritu"
    ]


def test_r146_potomek_plochy_mlci():
    """Inkoust, ktery na smalt PATRI. (Prvek `k.2` je uvnitr stitku.)"""
    d = _smalt_scena(text_x=460, text_y=125)  # cizi text vedle plochy
    assert _obsahuji(_msgs(d), ZNACKA_R146) == []


def test_r146_predek_plochy_mlci():
    """Radek, ktery ma vlastni text A ZAROVEN drzi smaltovy stitek uvnitr.

    Scena nese u popisku obdelnik CELEHO prvku, takze radek smalt
    geometricky obsahuje - bez teto vyjimky by kazdy takovy radek byl nalez.
    """
    d = _make(
        [
            _w("radek.0", 36, 113, 500, 154, text="Zarizeni"),
            _w("stitek.1", 36, 113, 413, 154, text="", t="panel", border=True),
        ],
        navrh={"plochy": ["stitek.1"], "prvky": {"stitek.1": {"rodic_id": "radek.0"}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R146) == []


def test_r146_hranice_na_pixel():
    """Dotek hranou neni inkoust na smaltu; prekryv `R146_PRAH_PX` uz ano."""
    # Plocha konci na x = 36 + 413 = 449.
    dotek = _smalt_scena(text_x=449, text_y=125)
    assert _obsahuji(_msgs(dotek), ZNACKA_R146) == []
    prekryv = _smalt_scena(text_x=449 - R146_PRAH_PX, text_y=125)
    assert len(_obsahuji(_errors(prekryv), ZNACKA_R146)) == 1


def test_r146_bez_rodic_id_spadne_na_hrubsi_meridlo():
    """Stara scena bez rodokmenu nesmi obvinit KAZDY text uvnitr smaltu."""
    d = _make(
        [
            _w("stitek.1", 36, 113, 413, 154, text="", t="panel", border=True),
            _w("k.2", 52, 125, 62, 19, text="TabOS"),
        ],
        navrh={"plochy": ["stitek.1"], "prvky": {"k.2": {"rodic": [36, 113, 413, 154]}}},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R146) == []


def test_r146_neviditelna_plocha_mlci():
    d = _make(
        [
            _w("stitek.1", 36, 113, 413, 154, text="", t="panel", visible=False),
            _w("odpojit.5", 300, 200, 120, 24, text="Odpojit"),
        ],
        navrh={"plochy": ["stitek.1"]},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R146) == []


def test_r146_mimo_profil_tab5_mlci():
    """Polarita je zakon TabOSu, ne vlastnost skla."""
    assert PROFILE_TAB5.polarita_smaltu is True
    assert PROFILE_OLED256.polarita_smaltu is False
    d = _make(
        [
            _w("stitek.1", 10, 10, 200, 60, text="", t="panel", border=True),
            _w("odpojit.5", 20, 20, 80, 12, text="Odpojit"),
        ],
        navrh={"plochy": ["stitek.1"]},
        scene_w=256,
        scene_h=128,
        device="oled256",
    )
    assert _obsahuji(_msgs(d), ZNACKA_R146) == []
    # Pozitivni kontrola: tataz scena na tab5 hlasi.
    d["device"] = "tab5"
    assert _obsahuji(_errors(d), ZNACKA_R146) != []


# --------------------------------------------------------------------------- #
# Rule 147: delici cara pres text
# --------------------------------------------------------------------------- #


def test_r147_realny_Main_mlci():
    """Zmereny negativni pripad: cara y244 je 4 px NAD prvnim pixelem pisma.

    Meridlo kitu (`zmer_prekryv.py`) porovnavalo caru s DOM boxem
    (537,140 686x229) a hlasilo tu svuj JEDINY nalez ze vsech 62 listu.
    Proti inkoustu je odpoved ticho - a je to zmereno, ne odhadnuto.
    """
    d = _make(
        [_w("kostra.52", *MAIN_INKOUST, text="Zatim neni co ukazovat")],
        navrh={"cary": MAIN_CARY},
    )
    assert _obsahuji(_msgs(d), ZNACKA_R147) == []


def test_r147_cara_pres_inkoust_je_ERROR():
    """Tyz text o osm pixelu vys - cara y244 uz jde pres glyfy."""
    x, _, w, h = MAIN_INKOUST
    d = _make(
        [_w("kostra.52", x, 240, w, h, text="Zatim neni co ukazovat")],
        navrh={"cary": MAIN_CARY},
    )
    assert _errors(d) == [
        f"{FL}: main: scene 'main': widget[0] (kostra.52): {ZNACKA_R147}: "
        f"cara 537,244 688x1 vede pres text 'Zatim neni co ukazovat' "
        f"(inkoust 537,240 686x12)"
    ]


def test_r147_hranice_na_pixel():
    """Cara na hrane inkoustu je podtrzeni, o pixel dal uz preskrtnuti."""
    # Inkoust 100..120 (vyska 20), cara vysoka 1 px.
    dotek_shora = _make(
        [_w("t", 40, 100, 200, 20)], navrh={"cary": [[40, 100 + R147_ODSTUP_PX - 1, 200, 1]]}
    )
    assert _obsahuji(_msgs(dotek_shora), ZNACKA_R147) == []
    uvnitr = _make(
        [_w("t", 40, 100, 200, 20)], navrh={"cary": [[40, 100 + R147_ODSTUP_PX, 200, 1]]}
    )
    assert len(_obsahuji(_errors(uvnitr), ZNACKA_R147)) == 1
    # Spodni hrana: cara konci presne na dolnim pixelu inkoustu.
    dotek_zdola = _make(
        [_w("t", 40, 100, 200, 20)],
        navrh={"cary": [[40, 120 - R147_ODSTUP_PX, 200, 1]]},
    )
    assert _obsahuji(_msgs(dotek_zdola), ZNACKA_R147) == []


def test_r147_cara_vedle_textu_mlci():
    """Vodorovne se neprotinaji - cara vede jinym sloupcem."""
    d = _make([_w("t", 40, 100, 200, 20)], navrh={"cary": [[300, 108, 200, 1]]})
    assert _obsahuji(_msgs(d), ZNACKA_R147) == []


def test_r147_dve_cary_dva_nalezy():
    """Jedna obet na caru: text preskrtnuty dvakrat se hlasi dvakrat."""
    d = _make([_w("t", 40, 100, 200, 40)], navrh={"cary": [[40, 110, 200, 1], [40, 130, 200, 1]]})
    assert len(_obsahuji(_errors(d), ZNACKA_R147)) == 2


def test_r147_prazdny_text_mlci():
    """Cara pres prazdny box neni preskrtnuty text."""
    d = _make([_w("t", 40, 100, 200, 20, text="")], navrh={"cary": [[40, 110, 200, 1]]})
    assert _obsahuji(_msgs(d), ZNACKA_R147) == []


def test_r147_mimo_profil_tab5_mlci():
    """Co je cara, rozhoduje kreslici jazyk - viz `DeviceProfile.delici_cary`."""
    assert PROFILE_TAB5.delici_cary is True
    assert PROFILE_OLED256.delici_cary is False
    d = _make(
        [_w("t", 10, 40, 100, 20)],
        navrh={"cary": [[10, 48, 100, 1]]},
        scene_w=256,
        scene_h=128,
        device="oled256",
    )
    assert _obsahuji(_msgs(d), ZNACKA_R147) == []
    d["device"] = "tab5"
    assert _obsahuji(_errors(d), ZNACKA_R147) != []


# --------------------------------------------------------------------------- #
# Fixtury: nosic musi projit i JSON schematem
# --------------------------------------------------------------------------- #


def test_fixtura_orez_ciste_hlasi_jen_Rule_137():
    """Cista fixtura NENI nema: nese doklad, ze 137 a 144 meri ruzne veci."""
    chyby = [i.message for i in validate_file(OREZ_CISTA, warnings_as_errors=False)
             if i.level == "ERROR"]
    assert len(_obsahuji(chyby, ZNACKA_R137)) == 1
    assert _obsahuji(chyby, ZNACKA_R144) == []
    assert _obsahuji(chyby, ZNACKA_R145) == []


def test_fixtura_orez_vady_hlasi_obe_pulky():
    chyby = [i.message for i in validate_file(OREZ_VADY, warnings_as_errors=False)
             if i.level == "ERROR"]
    assert len(_obsahuji(chyby, ZNACKA_R144)) == 1
    assert len(_obsahuji(chyby, ZNACKA_R145)) == 1


def test_fixtura_polarita_ciste_mlci():
    chyby = [i.message for i in validate_file(POLARITA_CISTA, warnings_as_errors=False)
             if i.level == "ERROR"]
    assert chyby == []


def test_fixtura_polarita_vady_hlasi_jednou():
    chyby = [i.message for i in validate_file(POLARITA_VADY, warnings_as_errors=False)
             if i.level == "ERROR"]
    assert len(_obsahuji(chyby, ZNACKA_R146)) == 1


def test_fixtura_cary_ciste_mlci():
    chyby = [i.message for i in validate_file(CARY_CISTE, warnings_as_errors=False)
             if i.level == "ERROR"]
    assert chyby == []


def test_fixtura_cary_vady_hlasi_jednou():
    chyby = [i.message for i in validate_file(CARY_VADY, warnings_as_errors=False)
             if i.level == "ERROR"]
    assert len(_obsahuji(chyby, ZNACKA_R147)) == 1


def test_fixtury_nesou_blok_navrh_a_jsou_platny_JSON():
    """Bez tohohle by 'fixtura prosla schematem' znamenalo jen 'soubor existuje'."""
    for cesta in (OREZ_CISTA, OREZ_VADY, POLARITA_CISTA, POLARITA_VADY, CARY_CISTE, CARY_VADY):
        data = json.loads(cesta.read_text(encoding="utf-8"))
        assert "navrh" in data["scenes"]["main"], cesta.name
