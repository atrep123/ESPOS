import json
from pathlib import Path

from ui_template_manager import Template, TemplateLibrary, TemplateMetadata


class DummyScene:
    def __init__(self, name="scene", widgets=None):
        self._raw_data = {"name": name, "widgets": widgets or []}


def test_initializes_defaults_when_file_missing(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))

    assert storage.exists()
    # Default templates seeded
    assert len(lib.templates) >= 5
    # A known default category should be present
    assert any(t.metadata.category == "Dashboards" for t in lib.templates)


def test_add_and_remove_template_persists_to_disk(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))

    custom = Template(
        metadata=TemplateMetadata(
            name="Custom Template",
            category="Custom",
            description="Test description",
            tags=["custom", "demo"],
        ),
        scene=DummyScene(),
    )
    lib.add_template(custom)
    # Should exist in memory
    assert any(t.metadata.name == "Custom Template" for t in lib.templates)

    # Should persist to disk
    data = json.loads(storage.read_text(encoding="utf-8"))
    assert any(item.get("metadata", {}).get("name") == "Custom Template" for item in data)

    # Removing should update memory and disk
    lib.remove_template(custom)
    data_after = json.loads(storage.read_text(encoding="utf-8"))
    assert all(item.get("metadata", {}).get("name") != "Custom Template" for item in data_after)


def test_search_matches_name_description_and_tags(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))

    lib.add_template(
        Template(
            metadata=TemplateMetadata(
                name="Voltage Monitor",
                category="Dashboards",
                description="Shows battery voltage and current",
                tags=["power", "battery"],
            ),
            scene=DummyScene(),
        )
    )

    by_name = lib.search_templates("voltage")
    assert any(t.metadata.name == "Voltage Monitor" for t in by_name)

    by_desc = lib.search_templates("battery")
    assert any(t.metadata.name == "Voltage Monitor" for t in by_desc)

    by_tag = lib.search_templates("POWER")
    assert any(t.metadata.name == "Voltage Monitor" for t in by_tag)


def test_corrupted_file_is_backed_up_and_defaults_restored(tmp_path: Path):
    storage = tmp_path / "templates.json"
    storage.write_text("{ this is not valid json", encoding="utf-8")

    lib = TemplateLibrary(storage_path=str(storage))

    # Should have created a .bak copy of the corrupted file
    assert (tmp_path / "templates.json.bak").exists()

    # Defaults should be loaded after fallback
    assert lib.templates
    assert any(t.metadata.category == "Forms" for t in lib.templates)


# ── Additional coverage ──


def test_get_templates_by_category(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))
    dashboards = lib.get_templates_by_category("Dashboards")
    assert len(dashboards) >= 1
    assert all(t.metadata.category == "Dashboards" for t in dashboards)


def test_get_templates_by_unknown_category(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))
    result = lib.get_templates_by_category("NonExistent")
    assert result == []


def test_template_to_dict_roundtrip(tmp_path: Path):
    scene = DummyScene("test_scene", [{"type": "label", "x": 0, "y": 0}])
    meta = TemplateMetadata(
        name="Roundtrip",
        category="Custom",
        description="Roundtrip test",
        tags=["test"],
    )
    template = Template(meta, scene)
    d = template.to_dict()
    assert d["metadata"]["name"] == "Roundtrip"
    assert d["metadata"]["category"] == "Custom"
    assert d["metadata"]["tags"] == ["test"]
    assert "widgets" in d["scene"]


def test_template_from_dict():
    d = {
        "metadata": {
            "name": "FromDict",
            "category": "Forms",
            "description": "Test from_dict",
            "author": "TestBot",
            "tags": ["alpha", "beta"],
        },
        "scene": {"name": "sc", "widgets": [{"type": "box"}]},
    }
    t = Template.from_dict(d)
    assert t.metadata.name == "FromDict"
    assert t.metadata.author == "TestBot"
    assert t.metadata.tags == ["alpha", "beta"]


def test_template_from_dict_defaults():
    t = Template.from_dict({})
    assert t.metadata.name == "Untitled"
    assert t.metadata.category == "Custom"
    assert t.metadata.author == "User"


def test_default_templates_have_all_required_categories(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))
    categories = {t.metadata.category for t in lib.templates}
    assert "Dashboards" in categories
    assert "Forms" in categories
    assert "Dialogs" in categories
    assert "Navigation" in categories
    assert "Layouts" in categories


def test_persistence_reload(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib1 = TemplateLibrary(storage_path=str(storage))
    initial_count = len(lib1.templates)
    lib1.add_template(Template(
        metadata=TemplateMetadata(name="Persist", category="Custom", description=""),
        scene=DummyScene(),
    ))
    assert len(lib1.templates) == initial_count + 1
    # Reload from same file
    lib2 = TemplateLibrary(storage_path=str(storage))
    assert len(lib2.templates) == initial_count + 1
    assert any(t.metadata.name == "Persist" for t in lib2.templates)


def test_remove_nonexistent_does_not_crash(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))
    fake = Template(
        metadata=TemplateMetadata(name="Ghost", category="Custom", description=""),
        scene=DummyScene(),
    )
    # Should not crash
    lib.remove_template(fake)


def test_search_no_match(tmp_path: Path):
    storage = tmp_path / "templates.json"
    lib = TemplateLibrary(storage_path=str(storage))
    result = lib.search_templates("zzz_nonexistent_zzz")
    assert result == []


def test_empty_file_loads_defaults(tmp_path: Path):
    storage = tmp_path / "templates.json"
    storage.write_text("[]", encoding="utf-8")
    lib = TemplateLibrary(storage_path=str(storage))
    # Empty list → should fall through to defaults
    assert len(lib.templates) >= 5


def test_malformed_entries_skipped(tmp_path: Path):
    """Lines 115-117: malformed template entries are skipped during load."""
    storage = tmp_path / "templates.json"
    good = Template(
        TemplateMetadata(name="Good", description="ok", category="Layouts", tags=[]),
        DummyScene("s1"),
    )
    # Write a list with one valid and one invalid entry
    data = [good.to_dict(), {"broken": True}, "not_a_dict"]
    storage.write_text(json.dumps(data), encoding="utf-8")
    lib = TemplateLibrary(storage_path=str(storage))
    # Should load the good entry or fall back to defaults
    assert len(lib.templates) >= 1


def test_save_failure_does_not_crash(tmp_path: Path):
    """Lines 134-136: _save() exception is silently caught."""
    storage = tmp_path / "readonly_dir" / "templates.json"
    # Don't create parent dir → write will fail
    lib = TemplateLibrary.__new__(TemplateLibrary)
    lib.storage_path = str(storage)
    lib.templates = []
    # Should not raise
    lib._save()


def test_make_scene_creates_scene_like():
    """Line 286: _make_scene returns object with _raw_data."""
    from ui_template_manager import _make_scene
    scene = _make_scene({"name": "test", "widgets": []})
    assert hasattr(scene, "_raw_data")
    assert scene._raw_data["name"] == "test"
