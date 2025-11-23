#!/usr/bin/env python3
"""
Web UI Designer backend (FastAPI skeleton).

This module is an initial scaffold for the future web-based UI designer:
- REST API for listing projects and loading/saving UI designs.
- Hooks to integrate existing UIDesigner JSON format and ui_pipeline.

NOTE:
- FastAPI and uvicorn are optional; this file is safe to import without them.
- The implementation intentionally stays minimal and does not start any server
  unless run as a script.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Shared undo/redo import (pure-Python, no extra dependency requirements)
try:
    from shared_undo_redo import OperationBuilder, OperationType, UndoRedoManager
except Exception:  # pragma: no cover - defensive if file missing
    UndoRedoManager = None  # type: ignore
    OperationBuilder = None  # type: ignore
    OperationType = None  # type: ignore

from ui_designer import UIDesigner

try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    FASTAPI_AVAILABLE = True
except Exception:  # pragma: no cover - FastAPI is optional for now
    FastAPI = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]

    class BaseModel:  # type: ignore[no-redef]
        """Minimal fallback with attribute-based storage."""

        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

    FASTAPI_AVAILABLE = False


ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT / "ui_projects"


# --- Collaborative editing data models ---


@dataclass
class User:
    """Connected user for collaborative editing."""
    id: str
    name: str
    color: str  # Hex color for cursor/selection
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    last_activity: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "cursor_x": self.cursor_x,
            "cursor_y": self.cursor_y,
            "last_activity": self.last_activity,
        }


@dataclass
class ProjectSession:
    """In-memory session state for a project.

    Added fields:
    - history: per-session undo/redo manager (operation-based)
    - history_version: monotonic counter for history broadcasts
    """
    project_id: str
    users: Dict[str, User]  # user_id -> User
    websockets: Dict[str, WebSocket]  # user_id -> WebSocket
    version: int = 0  # Design version counter for OT (widget structural changes)
    history: Optional[UndoRedoManager] = None
    history_version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "users": [u.to_dict() for u in self.users.values()],
            "version": self.version,
            "history": self._history_state_summary(),
        }

    def _history_state_summary(self) -> Dict[str, Any]:
        if not self.history:
            return {"enabled": False}
        undo_label = ""
        redo_label = ""
        if self.history.can_undo():
            op = self.history.operations[self.history.current_index]
            undo_label = self.history.get_operation_description(op)
        if self.history.can_redo():
            op = self.history.operations[self.history.current_index + 1]
            redo_label = self.history.get_operation_description(op)
        return {
            "enabled": True,
            "can_undo": self.history.can_undo(),
            "can_redo": self.history.can_redo(),
            "undo_label": undo_label,
            "redo_label": redo_label,
            "count": len(self.history.operations),
            "index": self.history.current_index,
            "history_version": self.history_version,
        }


class ProjectInfo(BaseModel):  # type: ignore[misc]
    id: str
    path: str


class SceneSummary(BaseModel):  # type: ignore[misc]
    name: str
    width: int
    height: int
    widget_count: int


class DesignSummary(BaseModel):  # type: ignore[misc]
    project_id: str
    scenes: List[SceneSummary]


class ProjectCreate(BaseModel):  # type: ignore[misc]
    id: str
    width: Optional[int] = None
    height: Optional[int] = None


def _list_projects() -> Dict[str, Path]:
    """Return mapping project_id -> design.json path."""
    projects: Dict[str, Path] = {}
    if not PROJECTS_DIR.exists():
        return projects
    for entry in PROJECTS_DIR.iterdir():
        if not entry.is_dir():
            continue
        design_path = entry / "design.json"
        if design_path.is_file():
            projects[entry.name] = design_path
    return projects


def _summarize_design(project_id: str, design_path: Path) -> DesignSummary:
    """Return a simple summary of scenes in a design JSON."""
    designer = UIDesigner()
    designer.load_from_json(str(design_path))
    scenes: List[SceneSummary] = []
    for scene in designer.scenes.values():
        scenes.append(
            SceneSummary(
                name=scene.name,
                width=scene.width,
                height=scene.height,
                widget_count=len(scene.widgets),
            )
        )
    return DesignSummary(project_id=project_id, scenes=scenes)


# --- Collaborative editing session management ---

# Global session store: project_id -> ProjectSession
_sessions: Dict[str, ProjectSession] = {}

# User color palette for auto-assignment
_USER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
    "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B739", "#52B788",
]


def _get_or_create_session(project_id: str) -> ProjectSession:
    """Get or create a project session."""
    if project_id not in _sessions:
        history_mgr = UndoRedoManager(user_id="server") if UndoRedoManager else None
        _sessions[project_id] = ProjectSession(
            project_id=project_id,
            users={},
            websockets={},
            version=0,
            history=history_mgr,
        )
        # Attempt to load persisted history if available
        if history_mgr:
            history_path = _history_file_path(project_id)
            if history_path.is_file():
                try:
                    history_mgr.load_state(str(history_path))
                except Exception:
                    # Corrupt or unreadable history should not block session creation
                    pass
    return _sessions[project_id]


def _history_file_path(project_id: str) -> Path:
    """Return path to persisted history file for a project."""
    return PROJECTS_DIR / project_id / "history.json"


def _assign_user_color(session: ProjectSession) -> str:
    """Assign a unique color to a new user."""
    used_colors = {u.color for u in session.users.values()}
    for color in _USER_COLORS:
        if color not in used_colors:
            return color
    # If all colors used, generate a random one
    import random
    return f"#{random.randint(0, 0xFFFFFF):06X}"


def _cleanup_stale_users(session: ProjectSession, timeout: float = 30.0) -> None:
    """Remove users who haven't sent activity in timeout seconds."""
    import time
    now = time.time()
    stale_ids = [
        uid for uid, user in session.users.items()
        if now - user.last_activity > timeout
    ]
    for uid in stale_ids:
        session.users.pop(uid, None)
        session.websockets.pop(uid, None)


def create_app() -> "FastAPI":  # type: ignore[name-defined]
    """Create FastAPI app instance for the web UI Designer backend."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError(
            "FastAPI is not installed. Install extra dependencies, e.g. "
            "`pip install fastapi uvicorn` or use the 'web' extra."
        )

    app = FastAPI(title="ESP32OS Web UI Designer Backend")

    # Allow browser clients served from file:// or other ports during development.
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except Exception:
        # If CORS middleware is not available, continue without it.
        pass

    @app.get("/api/projects", response_model=List[ProjectInfo])
    def list_projects() -> List[ProjectInfo]:
        projects = _list_projects()
        return [
            ProjectInfo(id=pid, path=str(path))
            for pid, path in sorted(projects.items(), key=lambda kv: kv[0])
        ]

    @app.get("/api/projects/{project_id}", response_model=DesignSummary)
    def get_project_summary(project_id: str) -> DesignSummary:
        projects = _list_projects()
        design_path = projects.get(project_id)
        if not design_path:
            raise HTTPException(status_code=404, detail="Project not found")
        return _summarize_design(project_id, design_path)

    @app.post("/api/projects", response_model=ProjectInfo)
    def create_project(payload: ProjectCreate) -> ProjectInfo:
        """Create a new UI project with an empty scene."""
        project_id = payload.id.strip()
        if not project_id:
            raise HTTPException(status_code=400, detail="Project id must not be empty")

        root = PROJECTS_DIR / project_id
        if root.exists():
            raise HTTPException(status_code=409, detail="Project already exists")
        root.mkdir(parents=True, exist_ok=True)

        design_path = root / "design.json"

        # Disable auto-export side effects when running in backend context.
        os.environ.setdefault("ESP32OS_AUTO_EXPORT", "0")

        designer = UIDesigner(payload.width or 128, payload.height or 64)
        designer.create_scene("scene1")
        designer.save_to_json(str(design_path))

        return ProjectInfo(id=project_id, path=str(design_path))

    @app.get("/api/projects/{project_id}/design")
    def get_project_design(project_id: str) -> Dict:
        """Return raw design JSON for a project."""
        projects = _list_projects()
        design_path = projects.get(project_id)
        if not design_path:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            return json.loads(design_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - I/O edge cases
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.put("/api/projects/{project_id}/design")
    def put_project_design(project_id: str, payload: Dict) -> Dict[str, str]:
        """Overwrite design JSON for a project."""
        projects = _list_projects()
        design_path = projects.get(project_id)
        if not design_path:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            design_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - I/O edge cases
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"status": "ok"}

    @app.get("/api/projects/{project_id}/history")
    def get_project_history(project_id: str, include_operations: bool = False) -> Dict[str, Any]:
        """Return undo/redo history summary (and optionally full operations)."""
        projects = _list_projects()
        if project_id not in projects:
            raise HTTPException(status_code=404, detail="Project not found")
        session = _get_or_create_session(project_id)
        hist = session._history_state_summary()
        if include_operations and session.history:
            hist["operations"] = [op.to_dict() for op in session.history.get_history()]
        return hist
    
    @app.get("/api/projects/{project_id}/session")
    def get_project_session(project_id: str) -> Dict:
        """Get current collaborative session state for a project."""
        projects = _list_projects()
        if project_id not in projects:
            raise HTTPException(status_code=404, detail="Project not found")
        
        session = _get_or_create_session(project_id)
        _cleanup_stale_users(session)
        return session.to_dict()

    @app.post("/api/projects/{project_id}/build")
    def build_project(
        project_id: str,
        env: str = "esp32-s3-devkitm-1",
        port: Optional[str] = None,
        request: Request = None,  # type: ignore[assignment]
    ) -> Dict[str, int]:
        """
        Trigger export → build → (optional) flash for a project via ui_pipeline.

        For safety, this is disabled by default and requires setting
        ESP32OS_WEB_BUILD_ENABLED=1 in the environment.
        """
        if os.environ.get("ESP32OS_WEB_BUILD_ENABLED", "0") != "1":
            raise HTTPException(
                status_code=503,
                detail="Web-triggered builds are disabled. "
                "Set ESP32OS_WEB_BUILD_ENABLED=1 to enable.",
            )

        # Optional API key guard for production deployments.
        required_key = os.environ.get("ESP32OS_WEB_API_KEY")
        if required_key:
            provided = None
            if request is not None:  # pragma: no branch - simple header/param check
                provided = (
                    request.headers.get("x-esp32os-key")
                    or request.query_params.get("api_key")
                )
            if provided != required_key:
                raise HTTPException(status_code=401, detail="Invalid API key")

        projects = _list_projects()
        design_path = projects.get(project_id)
        if not design_path:
            raise HTTPException(status_code=404, detail="Project not found")

        cmd = [
            sys.executable,
            str(ROOT / "ui_pipeline.py"),
            "run-all",
            "--design",
            str(design_path),
            "--env",
            env,
        ]
        if port:
            cmd.extend(["--port", port])

        proc = subprocess.run(cmd, cwd=str(ROOT))
        return {"returncode": int(proc.returncode)}

    # --- Collaborative editing with user tracking and structured messages ---

    async def _broadcast(session: ProjectSession, sender_id: Optional[str], message: Dict) -> None:
        """Broadcast structured message to all clients in a session except sender."""
        msg_str = json.dumps(message)
        for user_id, ws in session.websockets.items():
            if user_id == sender_id:
                continue
            try:
                await ws.send_text(msg_str)
            except Exception:
                # Ignore send errors; cleanup happens on disconnect
                continue

    @app.websocket("/ws/projects/{project_id}")
    async def project_ws(project_id: str, websocket: WebSocket) -> None:
        """
        Collaborative WebSocket endpoint for real-time editing.
        
        Protocol (JSON messages):
        - Client -> Server:
          - {"op": "join", "user_name": "Alice"}
          - {"op": "cursor", "x": 100, "y": 200}
          - {"op": "widget_add", "widget": {...}}
          - {"op": "widget_update", "widget_id": "...", "changes": {...}}
          - {"op": "widget_delete", "widget_id": "..."}
          
        - Server -> Client:
          - {"op": "user_joined", "user": {...}}
          - {"op": "user_left", "user_id": "..."}
          - {"op": "cursor", "user_id": "...", "x": 100, "y": 200}
          - {"op": "widget_add", "user_id": "...", "widget": {...}}
          - {"op": "widget_update", "user_id": "...", "widget_id": "...", "changes": {...}}
          - {"op": "widget_delete", "user_id": "...", "widget_id": "..."}
          - {"op": "session_state", "session": {...}}
        """
        # Check if project exists
        projects = _list_projects()
        if project_id not in projects:
            await websocket.close(code=1008, reason="Project not found")
            return
        
        session = _get_or_create_session(project_id)
        user_id = str(uuid.uuid4())
        user_name = "Anonymous"
        
        await websocket.accept()
        
        try:
            while True:
                msg_str = await websocket.receive_text()
                try:
                    msg = json.loads(msg_str)
                except json.JSONDecodeError:
                    continue
                
                op = msg.get("op")
                
                if op == "join":
                    # User joins session
                    user_name = msg.get("user_name", "Anonymous")
                    user_color = _assign_user_color(session)
                    user = User(
                        id=user_id,
                        name=user_name,
                        color=user_color,
                        last_activity=time.time(),
                    )
                    session.users[user_id] = user
                    session.websockets[user_id] = websocket
                    
                    # Send current session state to new user
                    await websocket.send_text(json.dumps({
                        "op": "session_state",
                        "user_id": user_id,
                        "session": session.to_dict(),
                    }))
                    
                    # Broadcast user joined to others
                    await _broadcast(session, user_id, {
                        "op": "user_joined",
                        "user": user.to_dict(),
                    })
                
                elif op == "cursor":
                    # Update cursor position
                    if user_id in session.users:
                        session.users[user_id].cursor_x = msg.get("x", 0)
                        session.users[user_id].cursor_y = msg.get("y", 0)
                        session.users[user_id].last_activity = time.time()
                        
                        # Broadcast cursor update
                        await _broadcast(session, user_id, {
                            "op": "cursor",
                            "user_id": user_id,
                            "x": msg.get("x", 0),
                            "y": msg.get("y", 0),
                        })
                
                elif op in ("widget_add", "widget_update", "widget_delete"):
                    # Widget modifications - broadcast to all
                    if user_id in session.users:
                        session.users[user_id].last_activity = time.time()
                        session.version += 1
                        
                        broadcast_msg = {
                            "op": op,
                            "user_id": user_id,
                            "version": session.version,
                        }
                        broadcast_msg.update(msg)
                        
                        await _broadcast(session, user_id, broadcast_msg)

                        # Record operation into undo history
                        if session.history and OperationBuilder:
                            try:
                                widget_id = ""
                                if op == "widget_add":
                                    widget = msg.get("widget", {})
                                    widget_id = widget.get("id", str(uuid.uuid4()))
                                    add_op = OperationBuilder.add_widget(
                                        widget_id,
                                        widget.get("type", "widget"),
                                        int(widget.get("x", 0)),
                                        int(widget.get("y", 0)),
                                        int(widget.get("width", widget.get("w", 0) or 0)),
                                        int(widget.get("height", widget.get("h", 0) or 0)),
                                        **{k: v for k, v in widget.items() if k not in {"id","x","y","width","height","w","h","type"}}
                                    )
                                    add_op.user_id = user_id
                                    session.history.execute(add_op)
                                elif op == "widget_update":
                                    widget_id = msg.get("widget_id", "")
                                    changes = msg.get("changes", {})
                                    # Bulk modify operation
                                    mod_op = OperationBuilder.modify_property(
                                        widget_id,
                                        "bulk",
                                        None,
                                        changes,
                                    )
                                    mod_op.user_id = user_id
                                    session.history.execute(mod_op)
                                elif op == "widget_delete":
                                    widget_id = msg.get("widget_id", "")
                                    del_op = OperationBuilder.delete_widget(widget_id, {})
                                    del_op.user_id = user_id
                                    session.history.execute(del_op)
                                session.history_version += 1
                                # Persist history after every recorded operation (best-effort)
                                try:
                                    session.history.save_state(str(_history_file_path(project_id)))
                                except Exception:
                                    pass
                                # Broadcast updated history state
                                await _broadcast(session, None, {
                                    "op": "history_state",
                                    "session": session._history_state_summary(),
                                })
                            except Exception:
                                # History recording must not break collaboration
                                pass

                elif op in ("undo", "redo"):
                    if session.history:
                        applied = None
                        if op == "undo" and session.history.can_undo():
                            applied = session.history.undo()
                        elif op == "redo" and session.history.can_redo():
                            applied = session.history.redo()
                        if applied:
                            session.history_version += 1
                            # Persist after undo/redo as well
                            try:
                                session.history.save_state(str(_history_file_path(project_id)))
                            except Exception:
                                pass
                            # Broadcast undo/redo applied (clients decide how to update UI)
                            await _broadcast(session, None, {
                                "op": f"{op}_applied",
                                "operation": applied.to_dict(),
                                "session": session._history_state_summary(),
                            })
                            # Also echo back to requester
                            await websocket.send_text(json.dumps({
                                "op": f"{op}_applied",
                                "operation": applied.to_dict(),
                                "session": session._history_state_summary(),
                            }))
                    # Ignore if no history manager
                
                elif op == "heartbeat":
                    # Keep-alive ping
                    if user_id in session.users:
                        session.users[user_id].last_activity = time.time()
                
                # Cleanup stale users periodically
                _cleanup_stale_users(session)
                
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            # User left - cleanup and broadcast
            if user_id in session.users:
                session.users.pop(user_id, None)
                session.websockets.pop(user_id, None)
                
                await _broadcast(session, None, {
                    "op": "user_left",
                    "user_id": user_id,
                })
            
            # Clean up empty sessions
            if not session.users and project_id in _sessions:
                _sessions.pop(project_id, None)

    return app


def main() -> None:
    """Entry point for running the backend with uvicorn."""
    if not FASTAPI_AVAILABLE:
        print(
            "FastAPI/uvicorn are not installed.\n"
            "Install them via e.g. `pip install fastapi uvicorn` to run this server."
        )
        return

    try:
        import uvicorn  # type: ignore[import]
    except Exception:
        print(
            "uvicorn is not installed.\n"
            "Install it via `pip install uvicorn` to run this server."
        )
        return

    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
