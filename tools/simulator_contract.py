"""Pure, bounded input validation for the ESPOS runtime simulator."""

from __future__ import annotations

import re

_APP_EVENT = re.compile(
    r"(?:action:[A-Za-z0-9_.-]{1,31}:[0-9]{1,9}|"
    r"cmd:(?:2|3|20):[A-Za-z0-9_.-]{1,31}:[0-9]{1,9})"
)
_BUTTON_EVENT = re.compile(r"button:(0|[1-9][0-9]{0,2}):(press|release)")
_TICK_EVENT = re.compile(r"tick:([1-9][0-9]{0,3})")
_DISPLAY_EVENTS = ("display:connected", "display:disconnected", "display:error")
_CLI_NUMBER = re.compile(r"[0-9]{1,3}")
MAX_EVENTS = 256
MAX_TICKS_PER_STEP = 1000
MAX_ADVANCE_TICKS = 6000
_EVENT_ERROR = (
    "At most 256 events: input IDs 0..255, button:<id>:press|release, "
    "tick:1..1000 (10 ms each, at most 6000 ticks including 5 per non-tick event), "
    "display:connected|disconnected|error, or bounded app action/cmd events"
)


def validate_inputs(
    events: list[int | str] | tuple[int | str, ...], display: str, app: bool
) -> list[int | str]:
    """Return a detached list; reject coercions and non-builtin input types."""
    if type(app) is not bool:
        raise ValueError("app must be bool")
    if type(events) not in (list, tuple) or len(events) > MAX_EVENTS:
        raise ValueError(_EVENT_ERROR)

    validated = list(events)
    advance_ticks = 0
    for event in validated:
        ticks = 5  # Legacy non-tick steps keep their 50 ms time allowance.
        if type(event) is int:
            if not 0 <= event <= 255:
                raise ValueError(_EVENT_ERROR)
        elif type(event) is str:
            button = _BUTTON_EVENT.fullmatch(event)
            tick = _TICK_EVENT.fullmatch(event)
            if button is not None:
                if int(button[1]) > 255:
                    raise ValueError(_EVENT_ERROR)
            elif tick is not None:
                ticks = int(tick[1])
                if ticks > MAX_TICKS_PER_STEP:
                    raise ValueError(_EVENT_ERROR)
            elif event in _DISPLAY_EVENTS:
                pass  # Same 50 ms allowance as other non-tick steps.
            elif not app or _APP_EVENT.fullmatch(event) is None:
                raise ValueError(_EVENT_ERROR)
        else:
            raise ValueError(_EVENT_ERROR)
        advance_ticks += ticks
        if advance_ticks > MAX_ADVANCE_TICKS:
            raise ValueError(_EVENT_ERROR)

    if type(display) is not str or display not in ("connected", "disconnected", "error"):
        raise ValueError("Unknown simulated display state")
    return validated


def parse_cli_events(text: str, display: str, app: bool) -> list[int | str]:
    """Parse the same contract without dropping empty or malformed CLI steps."""
    if type(text) is not str or len(text) > MAX_EVENTS * 64:
        raise ValueError(_EVENT_ERROR)
    tokens = [] if text == "" else text.split(",")
    events = [int(token) if _CLI_NUMBER.fullmatch(token) else token for token in tokens]
    return validate_inputs(events, display, app)
