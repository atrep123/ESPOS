"""Tests for helper functions in web_designer_backend."""

from pathlib import Path

from ui_designer import UIDesigner, WidgetType
import web_designer_backend as backend


def test_list_and_summarize_projects(tmp_path, monkeypatch):
    """_list_projects and _summarize_design should reflect simple UIDesigner output."""
    # Arrange: create a fake ui_projects directory with one project
    projects_dir = tmp_path / "ui_projects"
    project_dir = projects_dir / "demo_project"
    project_dir.mkdir(parents=True)

    design_path = project_dir / "design.json"
    designer = UIDesigner(128, 64)
    designer.create_scene("main")
    designer.add_widget(
        WidgetType.LABEL,
        x=0,
        y=0,
        width=20,
        height=8,
        text="Hello",
        border=False,
    )
    designer.save_to_json(str(design_path))

    # Point backend to the temporary projects directory
    monkeypatch.setattr(backend, "PROJECTS_DIR", projects_dir)

    # Act: list projects
    projects = backend._list_projects()

    # Assert: project is visible with correct design path
    assert "demo_project" in projects
    assert projects["demo_project"] == design_path

    # Act: summarize design
    summary = backend._summarize_design("demo_project", design_path)

    # Assert: summary includes the scene and widget count
    assert summary.project_id == "demo_project"
    assert summary.scenes
    first_scene = summary.scenes[0]
    assert first_scene.name == "main"
    assert first_scene.width == 128
    assert first_scene.height == 64
    assert first_scene.widget_count == 1

