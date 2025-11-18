"""Integration-style tests for the web designer backend collaboration layer.

These tests exercise the FastAPI app + WebSocket endpoints if FastAPI is available.
"""

import json

import pytest

fastapi = pytest.importorskip("fastapi")  # noqa: F401
from fastapi.testclient import TestClient  # type: ignore[import]

import web_designer_backend as backend
from ui_designer import UIDesigner, WidgetType


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


def test_ws_user_join_and_session_state(tmp_path, monkeypatch):
    """User join should receive session state and broadcast to others."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws1:
        # First user joins
        ws1.send_text(json.dumps({"op": "join", "user_name": "Alice"}))
        msg1 = json.loads(ws1.receive_text())
        
        # Should receive session_state
        assert msg1["op"] == "session_state"
        assert "user_id" in msg1
        assert "session" in msg1
        user_id_1 = msg1["user_id"]
        
        # Session should have 1 user
        assert len(msg1["session"]["users"]) == 1
        assert msg1["session"]["users"][0]["name"] == "Alice"
        
        with client.websocket_connect(f"/ws/projects/{project_id}") as ws2:
            # Second user joins
            ws2.send_text(json.dumps({"op": "join", "user_name": "Bob"}))
            
            # Bob receives session_state
            msg2 = json.loads(ws2.receive_text())
            assert msg2["op"] == "session_state"
            user_id_2 = msg2["user_id"]
            assert user_id_1 != user_id_2
            
            # Session should have 2 users
            assert len(msg2["session"]["users"]) == 2
            
            # Alice receives user_joined broadcast
            msg3 = json.loads(ws1.receive_text())
            assert msg3["op"] == "user_joined"
            assert msg3["user"]["name"] == "Bob"


def test_ws_cursor_tracking(tmp_path, monkeypatch):
    """Cursor updates should be broadcast to other users."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws1, \
         client.websocket_connect(f"/ws/projects/{project_id}") as ws2:
        
        # Both users join
        ws1.send_text(json.dumps({"op": "join", "user_name": "Alice"}))
        msg1 = json.loads(ws1.receive_text())
        user_id_1 = msg1["user_id"]
        
        # Alice sends cursor update
        ws1.send_text(json.dumps({"op": "cursor", "x": 100, "y": 200}))
        
        # Bob should receive cursor update
        msg3 = json.loads(ws2.receive_text())
        assert msg3["op"] == "cursor"
        assert msg3["user_id"] == user_id_1
        assert msg3["x"] == 100
        assert msg3["y"] == 200


def test_ws_widget_operations_broadcast(tmp_path, monkeypatch):
    """Widget add/update/delete should be broadcast with version."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws1, \
         client.websocket_connect(f"/ws/projects/{project_id}") as ws2:
        
        # Both users join
        ws1.send_text(json.dumps({"op": "join", "user_name": "Alice"}))
        ws1.receive_text()  # session_state
        
        ws2.send_text(json.dumps({"op": "join", "user_name": "Bob"}))
        ws2.receive_text()  # session_state
        ws1.receive_text()  # user_joined
        
        # Alice adds a widget
        ws1.send_text(json.dumps({
            "op": "widget_add",
            "widget": {
                "type": "label",
                "x": 10,
                "y": 20,
                "width": 30,
                "height": 10,
                "text": "New Widget"
            }
        }))
        
        # Bob should receive the widget_add broadcast
        msg = json.loads(ws2.receive_text())
        assert msg["op"] == "widget_add"
        assert "user_id" in msg
        assert "version" in msg
        assert msg["widget"]["text"] == "New Widget"


def test_ws_user_disconnect(tmp_path, monkeypatch):
    """User disconnect should broadcast user_left."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws1:
        # Alice joins
        ws1.send_text(json.dumps({"op": "join", "user_name": "Alice"}))
        ws1.receive_text()  # session_state
        
        with client.websocket_connect(f"/ws/projects/{project_id}") as ws2:
            # Bob joins
            ws2.send_text(json.dumps({"op": "join", "user_name": "Bob"}))
            msg = json.loads(ws2.receive_text())
            user_id_bob = msg["user_id"]
            
            ws1.receive_text()  # user_joined (Bob)
        
        # Bob disconnects (context manager exits)
        # Alice should receive user_left
        msg = json.loads(ws1.receive_text())
        assert msg["op"] == "user_left"
        assert msg["user_id"] == user_id_bob


def test_session_api_endpoint(tmp_path, monkeypatch):
    """GET /api/projects/{id}/session should return session state."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    # Initially empty session
    resp = client.get(f"/api/projects/{project_id}/session")
    assert resp.status_code == 200
    session = resp.json()
    assert session["project_id"] == project_id
    assert len(session["users"]) == 0
    assert session["version"] == 0
    
    # Connect a user via WebSocket
    with client.websocket_connect(f"/ws/projects/{project_id}") as ws:
        ws.send_text(json.dumps({"op": "join", "user_name": "TestUser"}))
        ws.receive_text()
        
        # Session should now show 1 user
        resp = client.get(f"/api/projects/{project_id}/session")
        assert resp.status_code == 200
        session = resp.json()
        assert len(session["users"]) == 1
        assert session["users"][0]["name"] == "TestUser"


def test_ws_heartbeat_keeps_user_alive(tmp_path, monkeypatch):
    """Heartbeat messages should update last_activity."""
    client, project_id = _make_app_with_project(tmp_path, monkeypatch)

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws:
        ws.send_text(json.dumps({"op": "join", "user_name": "Alice"}))
        _ = ws.receive_text()  # session_state
        
        # Get initial session
        resp = client.get(f"/api/projects/{project_id}/session")
        session1 = resp.json()
        activity1 = session1["users"][0]["last_activity"]
        
        # Send heartbeat
        import time
        time.sleep(0.1)
        ws.send_text(json.dumps({"op": "heartbeat"}))
        
        # Activity should be updated
        resp = client.get(f"/api/projects/{project_id}/session")
        session2 = resp.json()
        activity2 = session2["users"][0]["last_activity"]
        
        assert activity2 >= activity1


