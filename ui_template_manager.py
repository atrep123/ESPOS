"""Template management utilities for UI Designer."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class SceneLike(Protocol):
    """Minimal scene contract used by Template for serialization."""

    _raw_data: Dict[str, Any]


@dataclass
class TemplateMetadata:
    name: str
    category: str
    description: str
    author: str = "User"
    tags: List[str] = field(default_factory=list)


@dataclass
class Template:
    metadata: TemplateMetadata
    scene: SceneLike  # Exposes `_raw_data` containing serializable scene data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": asdict(self.metadata),
            "scene": getattr(self.scene, "_raw_data", {}),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Template:
        meta_data = data.get("metadata", {})
        metadata = TemplateMetadata(
            name=meta_data.get("name", "Untitled"),
            category=meta_data.get("category", "Custom"),
            description=meta_data.get("description", ""),
            author=meta_data.get("author", "User"),
            tags=list(meta_data.get("tags", [])),
        )
        scene_data = data.get("scene", {"name": "scene", "widgets": []})
        return cls(metadata, _make_scene(scene_data))


class TemplateLibrary:
    """In-memory template registry with simple JSON persistence."""

    CATEGORIES = [
        "Layouts",
        "Forms",
        "Dashboards",
        "Dialogs",
        "Navigation",
        "Data Display",
        "Custom",
    ]

    def __init__(self, storage_path: Optional[str] = None):
        env_storage = os.environ.get("ESP32OS_TEMPLATES_PATH", "").strip()
        self.storage_path = storage_path or env_storage or str(Path("templates.json"))
        self.templates: List[Template] = []
        self._load_or_initialize()

    # Public API -------------------------------------------------------------
    def add_template(self, template: Template) -> None:
        self.templates.append(template)
        self._save()

    def remove_template(self, template: Template) -> None:
        if template in self.templates:
            self.templates.remove(template)
            self._save()

    def get_templates_by_category(self, category: str) -> List[Template]:
        return [t for t in self.templates if t.metadata.category == category]

    def search_templates(self, query: str) -> List[Template]:
        term = query.lower()
        results: List[Template] = []
        for t in self.templates:
            meta = t.metadata
            if term in meta.name.lower() or term in meta.description.lower():
                results.append(t)
                continue
            if any(term in tag.lower() for tag in meta.tags):
                results.append(t)
        return results

    # Persistence -----------------------------------------------------------
    def _load_or_initialize(self) -> None:
        path = Path(self.storage_path)
        backup_path = path.with_suffix(path.suffix + ".bak")

        def _backup_corrupted_file() -> None:
            if not path.exists():
                return
            try:
                backup_path.write_bytes(path.read_bytes())
            except OSError:
                pass

        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    loaded: List[Template] = []
                    for item in data:
                        try:
                            loaded.append(Template.from_dict(item))
                        except (KeyError, TypeError, ValueError, AttributeError):
                            # Skip malformed entries but keep the rest
                            continue
                    if loaded:
                        self.templates = loaded
                        return
                # Fall through to defaults if empty or wrong shape
            except (OSError, json.JSONDecodeError):
                _backup_corrupted_file()
        # Initialize with defaults and persist, keeping a backup if we are overwriting
        if path.exists() and not backup_path.exists():
            _backup_corrupted_file()
        self.templates = self._default_templates()
        self._save()

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.templates], f, indent=2)
        except OSError:
            # Persistence failures should not crash usage in tests
            pass

    # Defaults --------------------------------------------------------------
    def _default_templates(self) -> List[Template]:
        defaults: List[Template] = []
        defaults.append(self._dashboard_template())
        defaults.append(self._form_template())
        defaults.append(self._dialog_template())
        defaults.append(self._pixel_hud_template())
        defaults.append(self._nav_template())
        defaults.append(self._data_cards_template())
        defaults.append(self._status_bar_template())
        return defaults

    def _dashboard_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Analytics Dashboard",
            category="Dashboards",
            description="Widgets arranged for analytics overview",
            tags=["dashboard", "analytics", "metrics"],
        )
        scene_data = {
            "name": "dashboard",
            "widgets": [
                {"type": "label", "x": 4, "y": 2, "width": 40, "height": 3, "text": "Dashboard"},
                {"type": "box", "x": 2, "y": 6, "width": 60, "height": 20, "border": True},
                {
                    "type": "chart",
                    "x": 4,
                    "y": 8,
                    "width": 56,
                    "height": 16,
                    "data_points": [10, 20, 30],
                },
            ],
        }
        return Template(metadata, _make_scene(scene_data))

    def _form_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Settings Form",
            category="Forms",
            description="Simple settings form with labels and inputs",
            tags=["form", "settings"],
        )
        scene_data = {
            "name": "form",
            "widgets": [
                {"type": "label", "x": 2, "y": 2, "width": 20, "height": 1, "text": "Username"},
                {"type": "textbox", "x": 24, "y": 2, "width": 30, "height": 1, "text": ""},
                {"type": "label", "x": 2, "y": 5, "width": 20, "height": 1, "text": "Email"},
                {"type": "textbox", "x": 24, "y": 5, "width": 30, "height": 1, "text": ""},
                {"type": "button", "x": 2, "y": 8, "width": 12, "height": 2, "text": "Save"},
            ],
        }
        return Template(metadata, _make_scene(scene_data))

    def _nav_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Navigation Menu",
            category="Navigation",
            description="Vertical navigation with active item",
            tags=["nav", "menu"],
        )
        scene_data = {
            "name": "nav",
            "widgets": [
                {"type": "panel", "x": 0, "y": 0, "width": 40, "height": 64, "border": True},
                {
                    "type": "label",
                    "x": 4,
                    "y": 4,
                    "width": 32,
                    "height": 8,
                    "text": "MENU",
                    "border": False,
                },
                {
                    "type": "button",
                    "x": 4,
                    "y": 16,
                    "width": 32,
                    "height": 10,
                    "text": "Home",
                    "border": True,
                },
                {
                    "type": "button",
                    "x": 4,
                    "y": 28,
                    "width": 32,
                    "height": 10,
                    "text": "Stats",
                    "border": True,
                },
                {
                    "type": "button",
                    "x": 4,
                    "y": 40,
                    "width": 32,
                    "height": 10,
                    "text": "Settings",
                    "border": True,
                },
            ],
        }
        return Template(metadata, _make_scene(scene_data))

    def _data_cards_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Data Cards",
            category="Dashboards",
            description="Three metric cards side by side",
            tags=["cards", "data", "metrics"],
        )
        scene_data = {
            "name": "cards",
            "widgets": [
                {"type": "box", "x": 4, "y": 6, "width": 40, "height": 20, "border": True},
                {
                    "type": "label",
                    "x": 6,
                    "y": 8,
                    "width": 36,
                    "height": 8,
                    "text": "CPU",
                    "border": False,
                },
                {"type": "gauge", "x": 8, "y": 14, "width": 32, "height": 10, "value": 64},
                {"type": "box", "x": 50, "y": 6, "width": 40, "height": 20, "border": True},
                {
                    "type": "label",
                    "x": 52,
                    "y": 8,
                    "width": 36,
                    "height": 8,
                    "text": "NET",
                    "border": False,
                },
                {"type": "progressbar", "x": 52, "y": 16, "width": 32, "height": 8, "value": 45},
                {"type": "box", "x": 96, "y": 6, "width": 40, "height": 20, "border": True},
                {
                    "type": "label",
                    "x": 98,
                    "y": 8,
                    "width": 36,
                    "height": 8,
                    "text": "MEM",
                    "border": False,
                },
                {
                    "type": "chart",
                    "x": 98,
                    "y": 16,
                    "width": 36,
                    "height": 8,
                    "data_points": [5, 10, 6, 12],
                },
            ],
        }
        return Template(metadata, _make_scene(scene_data))

    def _status_bar_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Status Bar",
            category="Layouts",
            description="Bottom status bar with three fields",
            tags=["status", "bar"],
        )
        scene_data = {
            "name": "status",
            "widgets": [
                {"type": "panel", "x": 0, "y": 54, "width": 128, "height": 10, "border": True},
                {
                    "type": "label",
                    "x": 4,
                    "y": 56,
                    "width": 40,
                    "height": 8,
                    "text": "PWR 82%",
                    "border": False,
                },
                {
                    "type": "label",
                    "x": 48,
                    "y": 56,
                    "width": 36,
                    "height": 8,
                    "text": "WIFI OK",
                    "border": False,
                },
                {
                    "type": "label",
                    "x": 90,
                    "y": 56,
                    "width": 34,
                    "height": 8,
                    "text": "12:34",
                    "border": False,
                    "align": "right",
                },
            ],
        }
        return Template(metadata, _make_scene(scene_data))

    def _dialog_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Confirm Dialog",
            category="Dialogs",
            description="Confirmation dialog with actions",
            tags=["dialog", "confirm"],
        )
        scene_data = {
            "name": "dialog",
            "widgets": [
                {"type": "panel", "x": 2, "y": 2, "width": 40, "height": 10, "border": True},
                {
                    "type": "label",
                    "x": 4,
                    "y": 4,
                    "width": 36,
                    "height": 2,
                    "text": "Are you sure?",
                },
                {"type": "button", "x": 6, "y": 8, "width": 10, "height": 2, "text": "OK"},
                {"type": "button", "x": 20, "y": 8, "width": 10, "height": 2, "text": "Cancel"},
            ],
        }
        return Template(metadata, _make_scene(scene_data))

    def _pixel_hud_template(self) -> Template:
        metadata = TemplateMetadata(
            name="Pixel HUD 128x64",
            category="Dashboards",
            description="Compact HUD layout with status bar and segmented progress",
            tags=["hud", "pixel", "128x64"],
        )
        scene_data = {
            "name": "pixel_hud",
            "widgets": [
                {"type": "panel", "x": 0, "y": 0, "width": 128, "height": 12, "border": True},
                {
                    "type": "label",
                    "x": 2,
                    "y": 2,
                    "width": 50,
                    "height": 8,
                    "text": "CORE",
                    "border": False,
                },
                {
                    "type": "label",
                    "x": 80,
                    "y": 2,
                    "width": 46,
                    "height": 8,
                    "text": "12:34",
                    "align": "right",
                    "border": False,
                },
                {
                    "type": "progressbar",
                    "x": 2,
                    "y": 18,
                    "width": 124,
                    "height": 6,
                    "value": 60,
                    "border": True,
                    "style": "segmented",
                },
            ],
        }
        return Template(metadata, _make_scene(scene_data))


# GUI wrapper (unused in tests; provided for import compatibility)
class TemplateManagerWindow:
    def __init__(self, *args, **kwargs):
        self.library = kwargs.get("library")


def _make_scene(scene_data: Dict[str, Any]) -> SceneLike:
    """Create a lightweight scene object that satisfies SceneLike."""

    class _Scene:
        def __init__(self, data: Dict[str, Any]) -> None:
            self._raw_data = data

    return _Scene(scene_data)  # type: ignore[return-value]
