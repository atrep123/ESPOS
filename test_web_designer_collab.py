"""Integration-style tests for the web designer backend collaboration layer.

These tests exercise the FastAPI app + WebSocket endpoints if FastAPI is available.
"""

import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")  # noqa: F401
from fastapi.testclient import TestClient  # type: ignore[import]

from ui_designer import UIDesigner, WidgetType
import web_designer_backend as backend


def _make_app_with_project(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    """Create a FastAPI app backed by a temporary ui_projects directory."""
    projects_dir = tmp_path / "ui_projects"
    project_dir = projects_dir / "demo_project"
    project_dir.mkdir(parents=True)

    # Create a simple design.json via UIDesigner so format matches the rest of the app.
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

    monkeypatch.setattr(backend, "PROJECTS_DIR", projects_dir)
    app = backend.create_app()
    client = TestClient(app)
    return client, "demo_project"


def test_ws_broadcast_simple_text(tmp_path, monkeypatch):
    """Messages sent by one WebSocket client should reach the others."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws1, client.websocket_connect(
        f"/ws/projects/{project_id}"
    ) as ws2:
        payload = "ping-collab"
        ws1.send_text(payload)
        received = ws2.receive_text()
        assert received == payload


def test_ws_design_update_roundtrip(tmp_path, monkeypatch):
    """design_update messages should round-trip unchanged through the broadcast hub."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws1, client.websocket_connect(
        f"/ws/projects/{project_id}"
    ) as ws2:
        update = {
            "type": "design_update",
            "project_id": project_id,
            "user": "client-test",
            "design": {
                "width": 128,
                "height": 64,
                "scenes": {"main": {"name": "main", "width": 128, "height": 64, "widgets": []}},
            },
        }
        ws1.send_text(json.dumps(update))
        received_raw = ws2.receive_text()
        received = json.loads(received_raw)

        assert received["type"] == "design_update"
        assert received["project_id"] == project_id
        assert received["user"] == "client-test"
        assert "design" in received
        assert received["design"]["width"] == 128

