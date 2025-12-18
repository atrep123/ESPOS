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
