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
from pathlib import Path
from typing import Dict, List, Optional

from ui_designer import UIDesigner

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
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
            raise HTTPException(status_code=500, detail=str(exc))

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
            raise HTTPException(status_code=500, detail=str(exc))
        return {"status": "ok"}

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

    # --- Collaborative editing (minimal broadcast hub) ---

    # project_id -> list of WebSocket connections
    ws_clients: Dict[str, List[WebSocket]] = {}

    async def _register_ws(project_id: str, ws: WebSocket) -> None:
        await ws.accept()
        ws_clients.setdefault(project_id, []).append(ws)

    async def _unregister_ws(project_id: str, ws: WebSocket) -> None:
        clients = ws_clients.get(project_id, [])
        if ws in clients:
            clients.remove(ws)
        if not clients and project_id in ws_clients:
            ws_clients.pop(project_id, None)

    async def _broadcast(project_id: str, sender: WebSocket, message: str) -> None:
        """Broadcast message to all clients for a project except sender."""
        for client in ws_clients.get(project_id, []):
            if client is sender:
                continue
            try:
                await client.send_text(message)
            except Exception:
                # Ignore send errors; cleanup happens on disconnect.
                continue

    @app.websocket("/ws/projects/{project_id}")
    async def project_ws(project_id: str, websocket: WebSocket) -> None:
        """
        Minimal collaborative channel for a project.

        - Accepts any text message (typically JSON with `op` / `payload`).
        - Broadcasts received messages to other connected clients for the same project.
        - Does not persist the state; clients are responsible for syncing design JSON
          via the REST endpoints.
        """
        await _register_ws(project_id, websocket)
        try:
            while True:
                msg = await websocket.receive_text()
                await _broadcast(project_id, websocket, msg)
        except WebSocketDisconnect:
            await _unregister_ws(project_id, websocket)
        except Exception:
            await _unregister_ws(project_id, websocket)

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
