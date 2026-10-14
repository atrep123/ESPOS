"""Contract checks require no scene, native runner, compiler, or device."""

from enum import IntEnum

import pytest

from tools.simulator_contract import parse_cli_events, validate_inputs


class IntSubclass(int):
    def __le__(self, other):
        raise AssertionError("Must not compare an int subclass")

    def __ge__(self, other):
        raise AssertionError("Must not compare an int subclass")


class StrSubclass(str):
    def __eq__(self, other):
        raise AssertionError("Must not compare a str subclass")

    def __hash__(self):
        raise AssertionError("Must not hash a str subclass")


class ListSubclass(list):
    def __len__(self):
        raise AssertionError("Must not inspect a list subclass")

    def __iter__(self):
        raise AssertionError("Must not iterate a list subclass")


class TupleSubclass(tuple):
    def __len__(self):
        raise AssertionError("Must not inspect a tuple subclass")

    def __iter__(self):
        raise AssertionError("Must not iterate a tuple subclass")


class InputId(IntEnum):
    ZERO = 0


class ValueAccessor:
    @property
    def value(self):
        raise AssertionError("Must not read value accessors")

    def __bool__(self):
        raise AssertionError("Must not coerce unknown objects")

    def __int__(self):
        raise AssertionError("Must not coerce unknown objects")

    def __str__(self):
        raise AssertionError("Must not coerce unknown objects")

    def __len__(self):
        raise AssertionError("Must not inspect unknown objects")

    def __iter__(self):
        raise AssertionError("Must not iterate unknown objects")

    def __eq__(self, other):
        raise AssertionError("Must not compare unknown objects")

    def __hash__(self):
        raise AssertionError("Must not hash unknown objects")


def unconsumable_events():
    raise AssertionError("Must not advance generators")
    yield 0


@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("display", ["connected", "disconnected", "error"])
@pytest.mark.parametrize("events", [[], [0], [255], [0, 1, 254, 255, 0], list(range(256))])
def test_numeric_events_and_count_boundaries(container, app, display, events):
    source = container(events)
    result = validate_inputs(source, display, app)
    assert type(result) is list
    assert result == events
    assert result is not source


VALID_APP_EVENTS = [
    "action:a:0",
    "action:AazZ09_.-:000000000",
    "action:" + "a" * 31 + ":999999999",
    "cmd:2:a:0",
    "cmd:3:AazZ09_.-:000000000",
    "cmd:20:" + "Z" * 31 + ":999999999",
]


@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("event", VALID_APP_EVENTS)
def test_app_strings_preserve_order_and_values(container, event):
    events = container([255, event, 0, event])
    result = validate_inputs(events, "connected", True)
    assert result == [255, event, 0, event]
    assert result is not events
    assert all(type(value) in (int, str) for value in result)


@pytest.mark.parametrize("event", VALID_APP_EVENTS)
def test_app_strings_require_app_true(event):
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs([event], "connected", False)


@pytest.mark.parametrize("container", [list, tuple])
def test_app_event_count_boundary(container):
    events = container([0, "action:a:0", 255, "cmd:20:a:999999999"] * 64)
    result = validate_inputs(events, "error", True)
    assert result == list(events)
    assert result is not events


@pytest.mark.parametrize("app", [False, True])
def test_returned_list_is_detached_in_both_directions(app):
    source = [0, 255, 0]
    result = validate_inputs(source, "connected", app)
    source[0] = 1
    source.append(2)
    assert result == [0, 255, 0]
    result[1] = 3
    result.append(4)
    assert source == [1, 255, 0, 2]


@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("count", [257, 1024])
def test_excess_event_count_uses_legacy_error(container, app, count):
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs(container([0] * count), "connected", app)


@pytest.mark.parametrize(
    "events",
    [
        None,
        0,
        False,
        "",
        "action:a:0",
        b"",
        {},
        {0},
        range(2),
        iter([0]),
        unconsumable_events(),
        ListSubclass([0]),
        TupleSubclass((0,)),
        ValueAccessor(),
    ],
    ids=[
        "none",
        "int",
        "bool",
        "string",
        "action-string",
        "bytes",
        "dict",
        "set",
        "range",
        "iterator",
        "generator",
        "list-subclass",
        "tuple-subclass",
        "accessor",
    ],
)
def test_events_require_plain_list_or_tuple(events):
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs(events, "connected", True)


@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize(
    "event",
    [
        -1,
        256,
        10**100,
        True,
        False,
        0.0,
        255.0,
        None,
        b"action:a:0",
        [],
        {},
        object(),
        IntSubclass(0),
        InputId.ZERO,
        StrSubclass("action:a:0"),
        ValueAccessor(),
        unconsumable_events(),
    ],
    ids=[
        "negative",
        "over-255",
        "huge-int",
        "true",
        "false",
        "zero-float",
        "float",
        "none",
        "bytes",
        "list",
        "dict",
        "object",
        "int-subclass",
        "int-enum",
        "str-subclass",
        "accessor",
        "generator",
    ],
)
def test_invalid_event_types_and_ranges(container, app, event):
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs(container([0, event, 255]), "connected", app)


@pytest.mark.parametrize(
    "event",
    [
        "",
        "0",
        "255",
        "action:a",
        "action:a:",
        "action::0",
        "action:" + "a" * 32 + ":0",
        "action:a:1234567890",
        "cmd:2:a",
        "cmd:2:a:",
        "cmd:2::0",
        "cmd:2:" + "a" * 32 + ":0",
        "cmd:2:a:1234567890",
        "cmd:0:a:0",
        "cmd:1:a:0",
        "cmd:4:a:0",
        "cmd:19:a:0",
        "cmd:21:a:0",
        "cmd:02:a:0",
        "cmd:03:a:0",
        "cmd:020:a:0",
        "action:a:-1",
        "action:a:+1",
        "action:a:1.0",
        "action:a:1e2",
        "action:a:0x1",
        "action:a:١",
        "action:a:１",
        "action:é:1",
        "action:a/b:1",
        "action:a b:1",
        "action:a:1:2",
        "Action:a:1",
        "cmd:2:a:-1",
        "cmd:2:a:+1",
        "cmd:2:a:1.0",
        "cmd:2:a:١",
        "cmd:2:é:1",
        "cmd:2:a/b:1",
        "cmd:2:a b:1",
        "cmd:2:a:1:2",
        "CMD:2:a:1",
    ],
)
def test_malformed_app_events(event):
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs([event], "connected", True)


@pytest.mark.parametrize("event", VALID_APP_EVENTS)
@pytest.mark.parametrize("padding", [" ", "\t", "\n", "\r\n", "\x00", "prefix", "suffix"])
@pytest.mark.parametrize("side", ["before", "after"])
def test_app_regex_requires_full_match(event, padding, side):
    invalid = padding + event if side == "before" else event + padding
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs([invalid], "connected", True)


@pytest.mark.parametrize("event", ["action:a:0", "cmd:2:a:0", "cmd:3:a:0", "cmd:20:a:0"])
@pytest.mark.parametrize("separator", [" ", "\t", "\n", "\r", "\x00"])
def test_app_events_reject_internal_whitespace_and_nul(event, separator):
    with pytest.raises(ValueError, match=r"^At most 256"):
        validate_inputs([event.replace(":", ":" + separator, 1)], "connected", True)


@pytest.mark.parametrize(
    "app",
    [
        0,
        1,
        -1,
        0.0,
        1.0,
        None,
        "false",
        "true",
        [],
        {},
        IntSubclass(1),
        InputId.ZERO,
        ValueAccessor(),
    ],
    ids=[
        "zero",
        "one",
        "negative",
        "zero-float",
        "one-float",
        "none",
        "false-str",
        "true-str",
        "list",
        "dict",
        "int-subclass",
        "int-enum",
        "accessor",
    ],
)
def test_app_requires_exact_bool(app):
    with pytest.raises(ValueError, match=r"^app must be bool$"):
        validate_inputs([], "connected", app)


@pytest.mark.parametrize(
    "display",
    [
        "",
        "unknown",
        "Connected",
        " connected",
        "connected ",
        "connected\n",
        "disconnected\n",
        "error\n",
        b"connected",
        None,
        True,
        0,
        [],
        {},
        StrSubclass("connected"),
        ValueAccessor(),
    ],
    ids=[
        "empty",
        "unknown",
        "case",
        "leading-space",
        "trailing-space",
        "connected-newline",
        "disconnected-newline",
        "error-newline",
        "bytes",
        "none",
        "bool",
        "int",
        "list",
        "dict",
        "str-subclass",
        "accessor",
    ],
)
def test_display_requires_exact_known_string(display):
    with pytest.raises(ValueError, match=r"^Unknown simulated display state$"):
        validate_inputs([], display, False)


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("display", ["connected", "disconnected", "error"])
def test_button_edges_and_tick_only_preserve_order_types_and_detachment(app, container, display):
    events = container(["button:255:release", "tick:1", 0, "button:0:press", "tick:1000"])
    validated = validate_inputs(events, display, app)
    assert validated == list(events) and validated is not events
    assert type(validated[2]) is int
    assert all(type(value) is str for i, value in enumerate(validated) if i != 2)
    assert validate_inputs(["tick:1000"] * 6, display, app) == ["tick:1000"] * 6


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("edge", ["press", "release"])
def test_all_button_ids_and_event_count_boundary(app, edge):
    events = [f"button:{i}:{edge}" for i in range(256)]
    assert validate_inputs(events, "connected", app) == events
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs([*events, "tick:1"], "connected", app)


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("ordinary", [0, "button:255:release", "button:0:press"])
def test_cumulative_tick_budget_counts_ordinary_steps(app, ordinary):
    events = ["tick:1000"] * 5 + ["tick:995", ordinary]
    assert validate_inputs(events, "error", app) == events
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs(["tick:1000"] * 5 + ["tick:996", ordinary], "error", app)
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs(["tick:1000"] * 6 + ["tick:1"], "error", app)


@pytest.mark.parametrize("event", ["action:a:0", "cmd:20:a:999999999"])
def test_app_events_also_consume_the_50_ms_tick_budget(event):
    assert validate_inputs(["tick:1000"] * 5 + ["tick:995", event], "connected", True)
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs(["tick:1000"] * 6 + [event], "connected", True)


MALFORMED_TIMED_EVENTS = [
    "button:",
    "button:0",
    "button::press",
    "button:256:press",
    "button:-1:release",
    "button:+1:press",
    "button:00:press",
    "button:0000:release",
    "button:0:1",
    "button:0:0",
    "button:0:PRESS",
    "button:0:Release",
    "Button:0:press",
    "button:0:release:tick:1",
    "button:0:press\x00",
    "button:é:press",
    "button:١:release",
    "button:０:press",
    "button:0.0:release",
    "tick:",
    "tick:0",
    "tick:00",
    "tick:01",
    "tick:1001",
    "tick:10000",
    "tick:999999999999999999999",
    "tick:-1",
    "tick:+1",
    "tick:1.0",
    "tick:1e3",
    "tick:0x10",
    "Tick:1",
    "tick:١",
    "tick:１",
    "tick:1:2",
    "tick:1\n",
    "C:/fixture.pgm",
    "../fixture",
    "--output",
    "cmd.exe",
    "exec:echo:1",
    "button:0:press;echo",
    "tick:1|echo",
    "tick:1,button:0:release",
]


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("event", MALFORMED_TIMED_EVENTS)
def test_malformed_timed_events_cannot_be_paths_or_commands(app, event):
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs([event], "connected", app)


@pytest.mark.parametrize("event", ["button:0:press", "button:255:release", "tick:1", "tick:1000"])
@pytest.mark.parametrize("padding", [" ", "\t", "\n", "\r", "\x00", "prefix", "suffix"])
@pytest.mark.parametrize("side", ["before", "after"])
def test_timed_events_require_an_exact_full_match(event, padding, side):
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs(
            [padding + event if side == "before" else event + padding], "connected", True
        )


@pytest.mark.parametrize("app", [False, True])
def test_cli_keeps_numeric_backcompat_and_timed_order(app):
    assert parse_cli_events("", "connected", app) == []
    assert parse_cli_events(
        "000,255,button:0:release,tick:1000,button:255:press", "error", app
    ) == [0, 255, "button:0:release", "tick:1000", "button:255:press"]
    assert parse_cli_events("tick:1", "connected", app) == ["tick:1"]


@pytest.mark.parametrize(
    "text",
    [
        ",",
        "0,",
        ",0",
        "0,,1",
        " ",
        "0, 1",
        "+1",
        "-0",
        "١",
        "１",
        "0000",
        "1\n",
        "tick:1,",
        "0," * 256,
        "tick:1" * 3000,
        None,
        StrSubclass("tick:1"),
        ValueAccessor(),
    ],
)
def test_cli_rejects_empty_steps_coercions_and_ambiguous_numbers(text):
    with pytest.raises(ValueError, match="At most 256"):
        parse_cli_events(text, "connected", True)


@pytest.mark.parametrize("event", [StrSubclass("tick:1"), StrSubclass("button:0:release")])
@pytest.mark.parametrize("app", [False, True])
def test_new_event_strings_still_require_exact_builtin_types(event, app):
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs([event], "connected", app)


def test_tick_step_range_exhaustive_and_mixed_app_order():
    for ticks in range(1, 1001):
        assert validate_inputs([f"tick:{ticks}"], "connected", False) == [f"tick:{ticks}"]
    events = ["button:0:press", "action:a:0", "tick:17", "cmd:2:a:1", "button:0:release", 255]
    assert validate_inputs(events, "connected", True) == events
    assert parse_cli_events(",".join(map(str, events)), "error", True) == events


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("container", [list, tuple])
@pytest.mark.parametrize("initial", ["connected", "disconnected", "error"])
def test_display_hot_sequence_is_exact_ordered_detached_and_cli_supported(app, container, initial):
    events = [
        0,
        "display:disconnected",
        "button:0:release",
        "tick:1",
        "display:error",
        "tick:1000",
        "display:connected",
        "button:255:press",
    ]
    incoming = container(events)
    validated = validate_inputs(incoming, initial, app)
    assert validated == events and validated is not incoming
    assert parse_cli_events(",".join(map(str, events)), initial, app) == events


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("state", ["connected", "disconnected", "error"])
def test_display_changes_count_toward_both_step_and_time_budgets(app, state):
    event = "display:" + state
    assert validate_inputs([event] * 256, "connected", app) == [event] * 256
    assert validate_inputs(["tick:1000"] * 5 + ["tick:995", event], "error", app)
    for events in (
        [event] * 257,
        ["tick:1000"] * 6 + [event],
        ["tick:1000"] * 5 + ["tick:996", event],
    ):
        with pytest.raises(ValueError, match="At most 256"):
            validate_inputs(events, "connected", app)


MALFORMED_DISPLAY_EVENTS = [
    "display",
    "display:",
    "display:Connected",
    "display:DISCONNECTED",
    "display:Error",
    "Display:connected",
    "display:reconnect",
    "display:disconnect",
    "display:unknown",
    "display:0",
    "display:1",
    "display:-1",
    "display:261",
    "display:true",
    "display: connected",
    "display:connected ",
    " display:error",
    "display:connected\n",
    "display:\tconnected",
    "display:connected\r",
    "display:connected\x00",
    "display:connected:0",
    "display:connected:tick:1",
    "display:connected,display:error",
    "display:connected;echo",
    "display:connected|echo",
    "display:../path",
    "display:C:/path",
    "display:cmd.exe",
    "display:cоnnected",  # non-ASCII Cyrillic o
    b"display:connected",
    {"display": "connected"},
    StrSubclass("display:connected"),
]


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("event", MALFORMED_DISPLAY_EVENTS)
def test_malformed_display_steps_and_non_builtin_types_are_refused(app, event):
    with pytest.raises(ValueError, match="At most 256"):
        validate_inputs(["display:disconnected", event, "display:connected"], "connected", app)


@pytest.mark.parametrize(
    "text",
    [
        "display:connected,",
        ",display:error",
        "display:connected,,tick:1",
        "display:connected\n",
        "display:error,exec:echo:1",
    ],
)
def test_cli_display_sequence_never_discards_bad_or_empty_steps(text):
    with pytest.raises(ValueError, match="At most 256"):
        parse_cli_events(text, "connected", True)
