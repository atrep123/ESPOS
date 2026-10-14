"""Versioned tooling targets; display profiles do not imply board drivers.

Runtime and codegen are independent: the legacy exporter emits UiScene with
gray4 colors, even for color canvas profiles. No peripherals or simulators are
claimed here. Existing MCP board ids stay in board_registry, not this registry.
"""

import re
from dataclasses import asdict, dataclass

SCHEMA_VERSION = 1
COLOR_MODELS = {1: "mono", 4: "gray4", 8: "unavailable", 16: "rgb565"}
CAPABILITIES = frozenset({"display_profile", "scene_validation", "ui_scene_c_export"})


class TargetRegistryError(ValueError):
    """Invalid, duplicate or unknown target metadata."""


@dataclass(frozen=True)
class TargetProfile:
    profile_id: str
    label: str
    width: int
    height: int
    color_depth: int
    color_model: str
    input_kind: str
    runtime: str
    codegen: str
    capabilities: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.profile_id, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9_-]*", self.profile_id
        ):
            raise TargetRegistryError("invalid profile id")
        if not isinstance(self.label, str) or not self.label.strip():
            raise TargetRegistryError("label must be nonempty")
        for name in ("width", "height"):
            value = getattr(self, name)
            # UiScene dimensions are uint16; bool is not a dimension.
            if type(value) is not int or not 1 <= value <= 65535:
                raise TargetRegistryError(f"{name} must be an integer in 1..65535")
        if type(self.color_depth) is not int or self.color_depth not in COLOR_MODELS:
            raise TargetRegistryError("unsupported color depth")
        if (
            not isinstance(self.color_model, str)
            or self.color_model != COLOR_MODELS[self.color_depth]
        ):
            raise TargetRegistryError("color model does not match depth")
        for name, choices in (
            ("input_kind", {"unavailable", "focus_navigation", "touch"}),
            ("runtime", {"unavailable", "espos_ui_scene", "tabos_lvgl"}),
            ("codegen", {"unavailable", "tools.ui_codegen"}),
        ):
            if not isinstance(getattr(self, name), str) or getattr(self, name) not in choices:
                raise TargetRegistryError(f"unsupported {name}")
        if (
            not isinstance(self.capabilities, tuple)
            or any(not isinstance(c, str) or c not in CAPABILITIES for c in self.capabilities)
            or len(set(self.capabilities)) != len(self.capabilities)
        ):
            raise TargetRegistryError("invalid or duplicate capabilities")
        if ("ui_scene_c_export" in self.capabilities) != (self.codegen == "tools.ui_codegen"):
            raise TargetRegistryError("codegen capability mismatch")

    def to_dict(self):
        data = asdict(self)
        data["capabilities"] = list(self.capabilities)
        return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise TargetRegistryError("invalid profile schema fields")
        if not isinstance(data["capabilities"], list):
            raise TargetRegistryError("capabilities must be an array")
        fields = dict(data, capabilities=tuple(data["capabilities"]))
        try:
            return cls(**fields)
        except (TypeError, ValueError) as exc:
            raise TargetRegistryError(str(exc)) from exc


class TargetRegistry:
    def __init__(self, profiles=()):
        self._profiles = {}
        for profile in profiles:
            self.register(profile)

    def register(self, profile):
        if not isinstance(profile, TargetProfile):
            raise TargetRegistryError("expected TargetProfile")
        if profile.profile_id in self._profiles:
            raise TargetRegistryError(f"duplicate profile {profile.profile_id!r}")
        self._profiles[profile.profile_id] = profile

    def ids(self):
        return tuple(self._profiles)

    def get(self, profile_id):
        if not isinstance(profile_id, str) or profile_id not in self._profiles:
            raise TargetRegistryError(f"unknown profile {profile_id!r}")
        return self._profiles[profile_id]

    def to_dict(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "profiles": [p.to_dict() for p in self._profiles.values()],
        }

    @classmethod
    def from_dict(cls, data):
        if (
            not isinstance(data, dict)
            or set(data) != {"schema_version", "profiles"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != SCHEMA_VERSION
            or not isinstance(data["profiles"], list)
        ):
            raise TargetRegistryError("invalid registry schema/version")
        return cls(TargetProfile.from_dict(p) for p in data["profiles"])


def load_registry():
    """Read actual canvas metadata lazily; never modify production profiles.

    Unknown board inputs remain unavailable. Tab5 editing/validation is present,
    but this repository has no TabOS/LVGL exporter. Generic profiles describe
    tooling canvases rather than proof that a physical display driver exists.
    """
    from ui_designer import HARDWARE_PROFILES

    profiles = []
    for profile_id, source in HARDWARE_PROFILES.items():
        tab5 = profile_id == "tab5_1280x720"
        reference = profile_id == "esp32os_256x128_gray4"
        capabilities = ("display_profile", "scene_validation")
        if not tab5:
            capabilities += ("ui_scene_c_export",)
        profiles.append(
            TargetProfile(
                profile_id=profile_id,
                label=source["label"],
                width=source["width"],
                height=source["height"],
                color_depth=source["color_depth"],
                color_model=COLOR_MODELS.get(source["color_depth"], "unavailable"),
                input_kind="touch" if tab5 else "focus_navigation" if reference else "unavailable",
                runtime="tabos_lvgl" if tab5 else "espos_ui_scene" if reference else "unavailable",
                codegen="unavailable" if tab5 else "tools.ui_codegen",
                capabilities=capabilities,
            )
        )
    return TargetRegistry(profiles)
