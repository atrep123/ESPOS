"""`validate_design.slovnik_prurez` - prurez listu nad slovnikem stavu (cista fce).

DIRA (fotoprotokol A-4, kritik espos-vse-oprava 4.5, mapa mezer): Rule 143
meri kazdy list ZVLAST ("drzi se list slovniku?"). Dva listy, ktere slovnik
DRZI a presto si odporuji (Diagnostics "vlozena, nepripojena", Files "neni
vlozena"), tak nechyti nikdo; a zavora NEMERENO je per-list, takze vec ze
slovniku, o ktere zadny list netvrdi stav (`USB-A host`, `sit` - 0 z 62
listu), se nikdy s nicim neporovna a nikdo to nerekne.

Kazdy test tu ma obe tridy; hranice jsou: dva stavy vs jeden, dva listy vs
jeden list se dvema prvky, nejdelsi shoda ("pripojena" je podretezcem
"vlozena, nepripojena"), diakritika, prazdny text a pomlcka.
"""

from __future__ import annotations

import pytest

from tools.validate_design import (
    ZNACKA_R143_PRUREZ,
    ZNACKA_R143_VEC_NEMERENO,
    _slovnik_ze_sceny,
    slovnik_prurez,
)

# Slovnik tokens.json kitu (bez diakritiky, jak ho testy ESPOS pisou).
STAVY = {
    "microSD": ["detekce nedostupna", "neni vlozena", "vlozena, nepripojena", "pripojena"],
    "hodiny": ["nenastaveny", "nastaveny podle site", "nezmereno"],
    "USB-A host": ["hostitel nedostupny", "bez zarizeni", "zarizeni pripojena"],
    "sit": ["nepripojena", "pripojena", "nezmereno"],
}


def _slovnik(stavy=None):
    slovnik, nalezy = _slovnik_ze_sceny({"navrh": {"slovnik": stavy or STAVY}}, "t")
    assert nalezy == []
    return slovnik


def _jen(nalezy, znacka):
    return [n.message for n in nalezy if znacka in n.message]


def test_znacky_jsou_ASCII_a_ruzne():
    assert ZNACKA_R143_PRUREZ.isascii() and ZNACKA_R143_VEC_NEMERENO.isascii()
    assert ZNACKA_R143_PRUREZ not in ZNACKA_R143_VEC_NEMERENO


# --------------------------------------------------------------------------- #
# Prurez: dva listy, dva stavy
# --------------------------------------------------------------------------- #


def test_dva_listy_dva_stavy_je_WARN_s_vyctem_listu():
    tvrzeni = {
        "SvorkaDiagnostics": [("microSD", "vlozena, nepripojena")],
        "SvorkaFiles": [("microSD", "karta neni vlozena")],
    }
    nalezy = slovnik_prurez(tvrzeni, _slovnik({"microSD": STAVY["microSD"]}))
    assert [n.level for n in nalezy] == ["WARN"]
    assert nalezy[0].message == (
        f"{ZNACKA_R143_PRUREZ}: 'microSD' ma 2 ruzne stavy na 2 listech: "
        f"'neni vlozena' tvrdi SvorkaFiles; 'vlozena, nepripojena' tvrdi SvorkaDiagnostics"
    )


def test_dva_listy_tentyz_stav_mlci():
    tvrzeni = {"A": [("microSD", "vlozena, nepripojena")], "B": [("microSD", "vlozena, nepripojena")]}
    assert slovnik_prurez(tvrzeni, _slovnik({"microSD": STAVY["microSD"]})) == []


def test_pet_listu_jeden_stav_mlci_HRANICE_je_druhy_stav():
    sl = _slovnik({"microSD": STAVY["microSD"]})
    pet = {f"L{i}": [("microSD", "pripojena")] for i in range(5)}
    assert slovnik_prurez(pet, sl) == []
    pet["L5"] = [("microSD", "neni vlozena")]
    nalezy = _jn = _jen(slovnik_prurez(pet, sl), ZNACKA_R143_PRUREZ)
    assert len(nalezy) == 1 and "2 ruzne stavy na 6 listech" in _jn[0]


def test_jeden_list_dva_prvky_dva_stavy_je_taky_rozpor():
    tvrzeni = {"SvorkaDomu": [("microSD", "pripojena"), ("microSD", "neni vlozena")]}
    nalezy = _jen(slovnik_prurez(tvrzeni, _slovnik({"microSD": STAVY["microSD"]})), ZNACKA_R143_PRUREZ)
    assert len(nalezy) == 1 and "na 1 listech" in nalezy[0]


def test_fotoprotokol_A4_pet_appek_pet_vet():
    tvrzeni = {
        "diagnostics": [("microSD", "vlozena, nepripojena")],
        "files": [("microSD", "karta neni vlozena nebo mount selhal")],
        "hex": [("microSD", "detekce nedostupna")],
        "settings": [("microSD", "pripojena")],
        "domov": [("microSD", "neni vlozena")],
    }
    nalezy = _jen(slovnik_prurez(tvrzeni, _slovnik({"microSD": STAVY["microSD"]})), ZNACKA_R143_PRUREZ)
    assert len(nalezy) == 1
    assert "4 ruzne stavy na 5 listech" in nalezy[0]
    assert "'neni vlozena' tvrdi domov, files" in nalezy[0]


# --------------------------------------------------------------------------- #
# Zavora per-VEC (kritik 4.5)
# --------------------------------------------------------------------------- #


def test_vec_bez_jedineho_tvrzeni_je_WARN_o_nemereni():
    tvrzeni = {"SvorkaDiagnostics": [("microSD", "pripojena")]}
    nalezy = slovnik_prurez(tvrzeni, _slovnik())
    nemereno = _jen(nalezy, ZNACKA_R143_VEC_NEMERENO)
    # Poradi je podle klice slovniku (casefold): hodiny < sit < usb-a host.
    # Podle jmena s velkym pismenem by 'USB-A host' skocil pred 'hodiny'
    # (ASCII 'U' < 'h') a poradi by zaviselo na tom, jak kit vec napsal.
    assert nemereno == [
        f"{ZNACKA_R143_VEC_NEMERENO}: o veci 'hodiny' netvrdi stav zadny list "
        f"(slovnik zna: nenastaveny | nastaveny podle site | nezmereno) - "
        f"slovnik se s nicim NEPOROVNAL",
        f"{ZNACKA_R143_VEC_NEMERENO}: o veci 'sit' netvrdi stav zadny list "
        f"(slovnik zna: nepripojena | pripojena | nezmereno) - "
        f"slovnik se s nicim NEPOROVNAL",
        f"{ZNACKA_R143_VEC_NEMERENO}: o veci 'USB-A host' netvrdi stav zadny list "
        f"(slovnik zna: hostitel nedostupny | bez zarizeni | zarizeni pripojena) - "
        f"slovnik se s nicim NEPOROVNAL",
    ]
    assert _jen(nalezy, ZNACKA_R143_PRUREZ) == []


def test_kazda_vec_s_tvrzenim_uz_NEMERENO_nedostane():
    tvrzeni = {
        "A": [("microSD", "pripojena"), ("hodiny", "nenastaveny")],
        "B": [("USB-A host", "bez zarizeni"), ("sit", "nezmereno")],
    }
    assert slovnik_prurez(tvrzeni, _slovnik()) == []


def test_stav_ke_kritice_4_5_syntetika_dve_veci_ze_ctyr_bez_tvrzeni():
    """SYNTETIKA opsana ze stavu kitu ke kritice 4.5 (pred fe66ed0): roli
    stav mela jen microSD (4x) a hodiny (1x), sit a USB-A host nic.

    Slovnik i tvrzeni jsou psane ZDE, ne ctene z kitu - test meri
    `slovnik_prurez` nad znamym vstupem, ne dnesni kit. Dnes uz roli stav
    maji vsechny 4 veci (kit `test_A7b`), a to je v poradku: tenhle test o
    dnesku nic netvrdi."""
    tvrzeni = {
        "diag": [("microSD", "vlozena, nepripojena")],
        "files": [("microSD", "vlozena, nepripojena")],
        "hex": [("microSD", "vlozena, nepripojena")],
        "settings": [("microSD", "vlozena, nepripojena")],
        "domov": [("hodiny", "hodiny nenastaveny")],
    }
    nalezy = slovnik_prurez(tvrzeni, _slovnik())
    assert [n.message.split("'")[1] for n in nalezy] == ["sit", "USB-A host"]
    assert all(ZNACKA_R143_VEC_NEMERENO in n.message for n in nalezy)


# --------------------------------------------------------------------------- #
# Normalizace a nejdelsi shoda
# --------------------------------------------------------------------------- #


def test_velikost_pismen_a_nasobne_mezery_nerozhoduji():
    tvrzeni = {"A": [("microSD", "VLOZENA,   nepripojena")], "B": [("MicroSD", "vlozena, nepripojena")]}
    assert slovnik_prurez(tvrzeni, _slovnik({"microSD": STAVY["microSD"]})) == []


def test_nejdelsi_shoda_neobvini_vetu_ktera_obsahuje_kratsi_stav():
    """'pripojena' je podretezcem 'vlozena, nepripojena'. Bez nejdelsi
    shody by JEDNA veta tvrdila dva stavy a prurez by obvinil sam sebe."""
    sl = _slovnik({"microSD": STAVY["microSD"]})
    stejne = {"A": [("microSD", "vlozena, nepripojena")], "B": [("microSD", "vlozena, nepripojena")]}
    assert slovnik_prurez(stejne, sl) == []
    ruzne = {"A": [("microSD", "vlozena, nepripojena")], "B": [("microSD", "pripojena")]}
    nalezy = _jen(slovnik_prurez(ruzne, sl), ZNACKA_R143_PRUREZ)
    assert len(nalezy) == 1 and "'pripojena' tvrdi B" in nalezy[0]


def test_diakritika_se_neprevadi():
    """Slovnik s hacky, text bez nich -> zadna shoda -> vec bez tvrzeni."""
    sl = _slovnik({"microSD": ["vložena, nepřipojena", "připojena"]})
    nalezy = slovnik_prurez({"A": [("microSD", "vlozena, nepripojena")]}, sl)
    assert _jen(nalezy, ZNACKA_R143_VEC_NEMERENO) and not _jen(nalezy, ZNACKA_R143_PRUREZ)


@pytest.mark.parametrize("text", ["", "   ", "-", "—"])
def test_prazdny_text_a_pomlcka_se_nepocitaji(text):
    """Patri Rule 138 / 139 - tady nejsou tvrzeni."""
    nalezy = slovnik_prurez({"A": [("microSD", text)]}, _slovnik({"microSD": STAVY["microSD"]}))
    assert _jen(nalezy, ZNACKA_R143_VEC_NEMERENO) and not _jen(nalezy, ZNACKA_R143_PRUREZ)


def test_text_mimo_slovnik_neni_tvrzeni_ani_rozpor():
    """'karta shorela' hlasi Rule 143 na svem listu; tady se nepocita."""
    sl = _slovnik({"microSD": STAVY["microSD"]})
    nalezy = slovnik_prurez({"A": [("microSD", "pripojena")], "B": [("microSD", "karta shorela")]}, sl)
    assert nalezy == []


def test_neznama_vec_se_preskoci_bez_nalezu():
    """'kamera' ve slovniku neni -> zadny nalez O NI. Slovnikova 'microSD'
    ale zustala bez tvrzeni, a to se hlasi (zavora per-VEC) - ticho by tu
    bylo presne ta vada, kterou funkce zavira."""
    nalezy = slovnik_prurez({"A": [("kamera", "bezi")]}, _slovnik({"microSD": STAVY["microSD"]}))
    assert [n.message.split("'")[1] for n in nalezy] == ["microSD"]
    assert not _jen(nalezy, ZNACKA_R143_PRUREZ)
    assert not any("kamera" in n.message for n in nalezy)
    assert slovnik_prurez({"A": [("kamera", "bezi")]}, {}) == []


def test_prazdny_slovnik_nic_netvrdi():
    assert slovnik_prurez({"A": [("microSD", "pripojena")]}, {}) == []


def test_poradi_je_deterministicke_a_podle_veci():
    tvrzeni = {
        "Z": [("sit", "pripojena"), ("microSD", "pripojena")],
        "A": [("sit", "nepripojena"), ("microSD", "neni vlozena")],
    }
    sl = _slovnik({"sit": STAVY["sit"], "microSD": STAVY["microSD"]})
    prvni = [n.message for n in slovnik_prurez(tvrzeni, sl)]
    druhy = [n.message for n in slovnik_prurez(dict(reversed(list(tvrzeni.items()))), sl)]
    assert prvni == druhy
    assert [m.split("'")[1] for m in prvni] == ["microSD", "sit"]
    assert "'nepripojena' tvrdi A; 'pripojena' tvrdi Z" in prvni[1]


def test_vstup_se_nemeni():
    tvrzeni = {"A": [("microSD", "pripojena")]}
    kopie = {"A": [("microSD", "pripojena")]}
    sl = _slovnik({"microSD": STAVY["microSD"]})
    slovnik_prurez(tvrzeni, sl)
    assert tvrzeni == kopie and sl == _slovnik({"microSD": STAVY["microSD"]})
