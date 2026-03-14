"""Shared UI model definitions for the ASCII designer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, TypedDict

from constants import DEFAULT_WIDGET_SIZE


def normalize_int_list(values: Iterable[Any]) -> List[int]:
    """Coerce an arbitrary iterable into a list of ints for chart data; ignores bad entries."""
    normalized: List[int] = []
    for v in values or []:
        try:
            normalized.append(int(v))
        except (TypeError, ValueError):
            continue
    return normalized


def normalize_str_list(values: Iterable[Any]) -> List[str]:
    """Coerce an arbitrary iterable into a list of strings for list items."""
    normalized: List[str] = []
    for v in values or []:
        s = str(v).strip() if v is not None else ""
        if s:
            normalized.append(s)
    return normalized


def coerce_bool_flag(value: Any, default: bool) -> bool:
    """Convert loose truthy/falsey inputs into a bool with sane string handling."""
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    try:
        return bool(value)
    except (ValueError, TypeError):
        return default


def coerce_choice(value: Any, allowed: Iterable[str], default: str) -> str:
    """Return value if in allowed choices, else default."""
    if value is None:
        return default
    sval = str(value)
    return sval if sval in allowed else default


def _empty_str_list() -> List[str]:
    """Typed default factory for string lists (e.g., animations)."""
    return []


def _empty_state_overrides() -> Dict[str, Dict[str, Any]]:
    """Typed default factory for state overrides mapping."""
    return {}


class ConstraintBaseline(TypedDict, total=False):
    x: int
    y: int
    width: int
    height: int
    bw: int
    bh: int


class Constraints(TypedDict, total=False):
    b: ConstraintBaseline
    ax: str
    ay: str
    sx: bool
    sy: bool
    mx: int
    my: int
    mr: int
    mb: int


def empty_constraints() -> Constraints:
    """Typed default factory for constraints metadata."""
    return {}


class SceneConfigDict(TypedDict):
    width: int
    height: int
    name: str
    theme: str
    hardware_profile: Optional[str]
    max_fb_kb: Optional[int]
    max_flash_kb: Optional[int]


def _coerce_int(value: Optional[int]) -> int:
    """Coerce Optional[int] to int with 0 fallback."""
    try:
        return int(value) if value is not None else 0
    except (ValueError, TypeError):
        return 0


def make_baseline(
    x: int,
    y: int,
    width: Optional[int],
    height: Optional[int],
    bw: Optional[int],
    bh: Optional[int],
) -> ConstraintBaseline:
    """Helper to build a typed ConstraintBaseline dict."""
    width = width if width else 0
    height = height if height else 0
    return {
        "x": _coerce_int(x),
        "y": _coerce_int(y),
        "width": _coerce_int(width),
        "height": _coerce_int(height),
        "bw": _coerce_int(bw),
        "bh": _coerce_int(bh),
    }


class ResponsiveRule(TypedDict, total=False):
    """Rule describing how to adapt a widget under certain conditions."""

    name: str
    condition: str
    apply: Dict[str, Any]
    else_apply: Dict[str, Any]


def _empty_responsive_rules() -> List["ResponsiveRule"]:
    """Typed default factory for responsive rules."""
    return []


class WidgetType(Enum):
    """Available widget types."""

    LABEL = "label"
    BOX = "box"
    BUTTON = "button"
    GAUGE = "gauge"
    PROGRESSBAR = "progressbar"
    CHECKBOX = "checkbox"
    RADIOBUTTON = "radiobutton"
    SLIDER = "slider"
    TEXTBOX = "textbox"
    PANEL = "panel"
    ICON = "icon"
    CHART = "chart"
    LIST = "list"
    TOGGLE = "toggle"


class BorderStyle(Enum):
    """Border styles."""

    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"
    ROUNDED = "rounded"
    BOLD = "bold"
    DASHED = "dashed"


@dataclass
class WidgetConfig:
    """Widget configuration."""

    type: str  # label, box, button, gauge, progressbar, checkbox, etc.
    x: int
    y: int
    width: Optional[int] = None  # type: ignore[reportRedeclaration]
    height: Optional[int] = None  # type: ignore[reportRedeclaration]
    text: str = ""
    style: str = "default"  # default, bold, inverse, highlight
    color_fg: str = "white"
    color_bg: str = "black"
    border: bool = True
    border_style: str = "single"  # single, double, rounded, bold, dashed
    align: str = "left"  # left, center, right
    valign: str = "middle"  # top, middle, bottom

    # Text layout
    text_overflow: str = "ellipsis"  # ellipsis, wrap, clip, auto
    max_lines: Optional[int] = None  # only used for wrap/auto; None = auto-fit by height

    # Extended properties
    value: int = 0  # For gauge, slider, progressbar
    min_value: int = 0
    max_value: int = 100
    checked: bool = False  # For checkbox, radiobutton
    enabled: bool = True
    visible: bool = True
    icon_char: str = ""  # For icon widget
    data_points: List[int] = field(default_factory=list)  # For chart
    items: List[str] = field(default_factory=_empty_str_list)  # For list widget
    z_index: int = 0  # Layer order

    # Layout hints
    padding_x: int = 1
    padding_y: int = 0
    margin_x: int = 0
    margin_y: int = 0
    # Responsive/constraints metadata (stored as simple dicts for export)
    constraints: Constraints = field(default_factory=empty_constraints)
    responsive_rules: List[ResponsiveRule] = field(default_factory=_empty_responsive_rules)
    animations: List[str] = field(default_factory=_empty_str_list)
    # Firmware/runtime metadata (exported as `constraints_json` in C headers).
    runtime: str = ""
    # Editing safeguards
    locked: bool = False
    # Theme role bindings (used when applying themes)
    theme_fg_role: str = ""
    theme_bg_role: str = ""
    # State variants
    state: str = "default"
    state_overrides: Dict[str, Dict[str, Any]] = field(default_factory=_empty_state_overrides)

    # Compatibility alias fields (optional; normalized in __post_init__)
    # These allow external component libraries to pass richer args without breaking.
    bg_color: Any = None
    text_color: Any = None
    color: Any = None
    font_size: Optional[int] = None
    bold: bool = False
    corner_radius: Optional[int] = None
    border_width: Optional[int] = None
    border_color: Any = None
    _widget_id: Optional[str] = None

    def __post_init__(self):
        self._normalize_type()
        self._apply_color_aliases()
        self._apply_style_aliases()
        self._apply_text_defaults()
        self._apply_dimension_defaults()
        self._apply_integer_bounds()
        self._sync_items_text()

    def _apply_text_defaults(self) -> None:
        try:
            ov = str(getattr(self, "text_overflow", "") or "").strip().lower()
            if not ov:
                ov = "ellipsis"
            if ov not in {"ellipsis", "wrap", "clip", "auto"}:
                ov = "ellipsis"
            self.text_overflow = ov
        except (AttributeError, TypeError):
            self.text_overflow = "ellipsis"

        try:
            ml = getattr(self, "max_lines", None)
            if ml is None or ml == "":
                self.max_lines = None
                return
            ml_i = int(ml)
            self.max_lines = ml_i if ml_i > 0 else None
        except (ValueError, TypeError):
            self.max_lines = None

    def _normalize_type(self) -> None:
        try:
            from enum import Enum as _Enum

            t = getattr(self, "type", None)
            if isinstance(t, _Enum):
                self.type = str(getattr(t, "value", t))
                return
        except (ImportError, AttributeError, TypeError):
            pass
        try:
            t = getattr(self, "type", None)
            if t is not None and hasattr(t, "value"):
                self.type = str(t.value)
        except (AttributeError, TypeError):
            pass
        # Validate against known widget types
        _valid = {wt.value for wt in WidgetType}
        if self.type not in _valid:
            raise ValueError(
                f"Unknown widget type {self.type!r}; "
                f"valid types: {sorted(_valid)}"
            )

    def _to_color_str(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            if isinstance(value, int):
                return f"#{value & 0xFFFFFF:06x}"
            return str(value)
        except (ValueError, TypeError):
            return None

    def _apply_color_aliases(self) -> None:
        alias_map = (
            ("bg_color", "color_bg"),
            ("text_color", "color_fg"),
            ("color", "color_fg"),
            ("border_color", "color_fg"),
        )
        for source, target in alias_map:
            try:
                value = getattr(self, source, None)
                if value is None:
                    continue
                resolved = self._to_color_str(value)
                if resolved:
                    setattr(self, target, resolved)
            except (AttributeError, TypeError):
                continue

    def _apply_style_aliases(self) -> None:
        try:
            if self.border_width is not None:
                self.border = bool(self.border_width and int(self.border_width) > 0)
        except (ValueError, TypeError):
            pass
        try:
            if bool(self.bold):
                self.style = "bold"
        except (ValueError, TypeError):
            pass

    def _apply_dimension_defaults(self) -> None:
        self.width = self._sanitize_dimension(self.width, default=DEFAULT_WIDGET_SIZE)
        self.height = self._sanitize_dimension(self.height, default=DEFAULT_WIDGET_SIZE)

    def _apply_integer_bounds(self) -> None:
        """Clamp numeric fields to C type ranges used by firmware.

        Note: x/y are intentionally NOT clamped here — the designer uses
        negative coordinates for offscreen positioning / animation targets.
        The codegen layer (ui_codegen.py) handles final uint16_t clamping.
        """
        self.value = self._clamp_int16(self.value)
        self.min_value = self._clamp_int16(self.min_value)
        self.max_value = self._clamp_int16(self.max_value)
        if self.max_lines is not None:
            self.max_lines = self._clamp_uint8(self.max_lines)

    def _sync_items_text(self) -> None:
        """For list widgets: sync items list ↔ text (newline-separated).

        If items is non-empty, it takes precedence and overwrites text.
        If items is empty but text has newlines, populate items from text.
        """
        if self.type != "list":
            return
        if self.items:
            self.text = "\n".join(str(s) for s in self.items)
        elif self.text and "\n" in self.text:
            self.items = [s for s in self.text.split("\n") if s]

    def _default_width(self, widget_type: str) -> int:
        if widget_type == "label":
            pad = int(getattr(self, "padding_x", 1) or 0)
            border_pad = 2 if bool(getattr(self, "border", True)) else 0
            return max(1, min(120, len(getattr(self, "text", "") or "") + 2 + pad * 2 + border_pad))
        if widget_type == "button":
            return max(4, len(getattr(self, "text", "") or "") + 4)
        if widget_type in ("panel", "box", "textbox"):
            return 10
        return 8

    def _default_height(self, widget_type: str) -> int:
        if widget_type == "label":
            return 3 if bool(getattr(self, "border", True)) else 1
        if widget_type in ("button", "checkbox", "radiobutton"):
            return 3
        if widget_type in ("panel", "box", "textbox"):
            return 6
        return 3

    @staticmethod
    def _clamp_uint16(v: int) -> int:
        """Clamp to uint16_t range (0..65535)."""
        try:
            return max(0, min(65535, int(v)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _clamp_int16(v: int) -> int:
        """Clamp to int16_t range (-32768..32767)."""
        try:
            return max(-32768, min(32767, int(v)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _clamp_uint8(v: int) -> int:
        """Clamp to uint8_t range (0..255)."""
        try:
            return max(0, min(255, int(v)))
        except (TypeError, ValueError):
            return 0

    def _sanitize_dimension(self, value: Optional[int], default: int = DEFAULT_WIDGET_SIZE) -> int:
        try:
            if value is None:
                return default
            coerced = int(value)
            return max(1, min(65535, coerced))
        except (ValueError, TypeError):
            return default

    @property  # type: ignore[no-redef]
    def width(self) -> int:  # noqa: F811
        return getattr(self, "_width", DEFAULT_WIDGET_SIZE)

    @width.setter
    def width(self, value: Optional[int]) -> None:
        self._width = self._sanitize_dimension(value, default=DEFAULT_WIDGET_SIZE)

    @property  # type: ignore[no-redef]
    def height(self) -> int:  # noqa: F811
        return getattr(self, "_height", DEFAULT_WIDGET_SIZE)

    @height.setter
    def height(self, value: Optional[int]) -> None:
        self._height = self._sanitize_dimension(value, default=DEFAULT_WIDGET_SIZE)


@dataclass
class SceneConfig:
    """Scene configuration."""

    name: str
    width: int
    height: int
    widgets: List[WidgetConfig]
    bg_color: str = "black"
    # Responsive base used for constraints
    base_width: int = 128
    base_height: int = 64
    # Theme metadata
    theme: str = "default"
    contrast_lock: bool = True
    hardware_profile: Optional[str] = None
    max_fb_kb: Optional[int] = None
    max_flash_kb: Optional[int] = None


class Scene:
    """Backward-compatibility shim for tests expecting `Scene(name, width, height)`."""

    def __init__(self, name: str, width: int, height: int, bg_color: str = "black"):
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.bg_color = bg_color
        # Defaults aligned with SceneConfig
        self.base_width = self.width
        self.base_height = self.height
        self.theme = "default"
        self.contrast_lock = True
        # Mutable list expected by tests for direct append
        self.widgets: List[WidgetConfig] = []
