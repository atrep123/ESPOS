"""Tests for validation rules 124-129."""

from __future__ import annotations

from tools.validate_design import validate_data


def _make(widgets, *, sw=256, sh=128, scene_name="s"):
    return {
        "scenes": {
            scene_name: {"width": sw, "height": sh, "widgets": widgets},
        }
    }


def _make_multi(scenes_dict):
    return {"scenes": scenes_dict}


def _errs(data):
    return [
        i
        for i in validate_data(data, file_label="test", warnings_as_errors=False)
        if i.level == "ERROR"
    ]


def _warns(data):
    return [
        i
        for i in validate_data(data, file_label="test", warnings_as_errors=False)
        if i.level == "WARN"
    ]


def _w(runtime, wtype="slider"):
    return {
        "type": wtype,
        "x": 10,
        "y": 10,
        "width": 60,
        "height": 14,
        "text": "T",
        "runtime": runtime,
    }


# ---------------------------------------------------------------------------
# Rule 124: runtime 'kind' value must be valid
# ---------------------------------------------------------------------------


class TestRule124:
    def test_valid_kind_int(self):
        d = _make([_w("bind=x;kind=int;min=0;max=100")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert not errs

    def test_valid_kind_bool(self):
        d = _make([_w("bind=x;kind=bool", wtype="checkbox")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert not errs

    def test_valid_kind_enum(self):
        d = _make([_w("bind=x;kind=enum;values=a|b|c")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert not errs

    def test_valid_kind_float(self):
        d = _make([_w("bind=x;kind=float;min=0;max=1;step=0.1")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert not errs

    def test_valid_kind_str(self):
        d = _make([_w("bind=x;kind=str", wtype="label")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert not errs

    def test_invalid_kind(self):
        d = _make([_w("bind=x;kind=integer;min=0;max=100")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert len(errs) == 1
        assert "integer" in errs[0].message

    def test_invalid_kind_via_type_alias(self):
        """'type' is an alias for 'kind' in the firmware parser."""
        d = _make([_w("bind=x;type=number")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert len(errs) == 1
        assert "number" in errs[0].message

    def test_no_kind_is_ok(self):
        """No kind/type key should not trigger rule 124."""
        d = _make([_w("bind=x")])
        errs = [e for e in _errs(d) if "kind" in e.message]
        assert not errs


# ---------------------------------------------------------------------------
# Rule 125: runtime with meta keys but no bind/key
# ---------------------------------------------------------------------------


class TestRule125:
    def test_bind_present(self):
        d = _make([_w("bind=brightness;kind=int;min=0;max=100")])
        ws = [w for w in _warns(d) if "no 'bind'" in w.message]
        assert not ws

    def test_key_present(self):
        d = _make([_w("key=brightness;kind=int")])
        ws = [w for w in _warns(d) if "no 'bind'" in w.message]
        assert not ws

    def test_meta_without_bind(self):
        d = _make([_w("kind=int;min=0;max=100")])
        ws = [w for w in _warns(d) if "no 'bind'" in w.message]
        assert len(ws) == 1

    def test_bind_only_is_ok(self):
        d = _make([_w("bind=x")])
        ws = [w for w in _warns(d) if "no 'bind'" in w.message]
        assert not ws


# ---------------------------------------------------------------------------
# Rule 126: duplicate keys in runtime string
# ---------------------------------------------------------------------------


class TestRule126:
    def test_no_duplicates(self):
        d = _make([_w("bind=x;kind=int;min=0;max=255")])
        errs = [e for e in _errs(d) if "duplicate" in e.message.lower()]
        assert not errs

    def test_duplicate_key(self):
        d = _make([_w("bind=x;kind=int;kind=bool")])
        errs = [e for e in _errs(d) if "duplicate" in e.message.lower()]
        assert len(errs) == 1
        assert "kind" in errs[0].message

    def test_duplicate_bind(self):
        d = _make([_w("bind=x;bind=y")])
        errs = [e for e in _errs(d) if "duplicate" in e.message.lower()]
        assert len(errs) == 1

    def test_case_insensitive_duplicate(self):
        d = _make([_w("bind=x;Bind=y")])
        errs = [e for e in _errs(d) if "duplicate" in e.message.lower()]
        assert len(errs) == 1


# ---------------------------------------------------------------------------
# Rule 127: numeric runtime values must parse as numbers
# ---------------------------------------------------------------------------


class TestRule127:
    def test_valid_integers(self):
        d = _make([_w("bind=x;kind=int;min=0;max=255;step=8")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert not errs

    def test_valid_float_step(self):
        d = _make([_w("bind=x;kind=float;min=0.0;max=1.0;step=0.1")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert not errs

    def test_negative_min(self):
        d = _make([_w("bind=x;kind=int;min=-10;max=10")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert not errs

    def test_non_numeric_min(self):
        d = _make([_w("bind=x;kind=int;min=abc;max=100")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert len(errs) == 1
        assert "min" in errs[0].message

    def test_non_numeric_max(self):
        d = _make([_w("bind=x;kind=int;min=0;max=xyz")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert len(errs) == 1
        assert "max" in errs[0].message

    def test_non_numeric_step(self):
        d = _make([_w("bind=x;kind=int;min=0;max=100;step=fast")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert len(errs) == 1
        assert "step" in errs[0].message

    def test_precision_numeric(self):
        d = _make([_w("bind=x;kind=float;precision=2")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert not errs

    def test_precision_non_numeric(self):
        d = _make([_w("bind=x;kind=float;precision=high")])
        errs = [e for e in _errs(d) if "not a valid number" in e.message]
        assert len(errs) == 1


# ---------------------------------------------------------------------------
# Rule 128: bind value must be a valid identifier
# ---------------------------------------------------------------------------


class TestRule128:
    def test_valid_bind(self):
        d = _make([_w("bind=contrast")])
        errs = [e for e in _errs(d) if "valid identifier" in e.message]
        assert not errs

    def test_dotted_bind(self):
        d = _make([_w("bind=sensor.temp")])
        errs = [e for e in _errs(d) if "valid identifier" in e.message]
        assert not errs

    def test_underscore_bind(self):
        d = _make([_w("bind=free_heap")])
        errs = [e for e in _errs(d) if "valid identifier" in e.message]
        assert not errs

    def test_bind_with_spaces(self):
        d = _make([_w("bind=my value")])
        errs = [e for e in _errs(d) if "valid identifier" in e.message]
        assert len(errs) == 1

    def test_bind_starts_with_digit(self):
        d = _make([_w("bind=3sensor")])
        errs = [e for e in _errs(d) if "valid identifier" in e.message]
        assert len(errs) == 1

    def test_bind_with_special_chars(self):
        d = _make([_w("bind=val@ue")])
        errs = [e for e in _errs(d) if "valid identifier" in e.message]
        assert len(errs) == 1


# ---------------------------------------------------------------------------
# Rule 129: cross-scene bind key kind consistency
# ---------------------------------------------------------------------------


class TestRule129:
    def test_consistent_kinds(self):
        d = _make_multi({
            "scene_a": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=brightness;kind=int;min=0;max=100")],
            },
            "scene_b": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=brightness;kind=int;min=0;max=255")],
            },
        })
        errs = [e for e in _errs(d) if "kind" in e.message and "bind" in e.message]
        assert not errs

    def test_conflicting_kinds(self):
        d = _make_multi({
            "scene_a": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=brightness;kind=int")],
            },
            "scene_b": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=brightness;kind=float")],
            },
        })
        errs = [e for e in _errs(d) if "kind" in e.message and "bind" in e.message]
        assert len(errs) == 1
        assert "brightness" in errs[0].message

    def test_different_bind_keys_ok(self):
        d = _make_multi({
            "scene_a": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=temp;kind=float")],
            },
            "scene_b": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=count;kind=int")],
            },
        })
        errs = [e for e in _errs(d) if "kind" in e.message and "bind" in e.message]
        assert not errs

    def test_no_kind_no_conflict(self):
        """bind without kind in one scene should not conflict."""
        d = _make_multi({
            "scene_a": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=brightness;kind=int")],
            },
            "scene_b": {
                "width": 256, "height": 128,
                "widgets": [_w("bind=brightness")],
            },
        })
        errs = [e for e in _errs(d) if "kind" in e.message and "bind" in e.message]
        assert not errs
