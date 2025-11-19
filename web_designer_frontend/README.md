# ESP32OS Collaborative Web Designer (Frontend)

This folder contains the HTML/CSS/JS frontend for the collaborative UI designer.

## Quick Start

Prerequisites:
- Backend running (FastAPI app in the repo root)
- Python 3 available in PATH

### Option A: Run both backend and frontend

From the repo root:

```powershell
# Starts backend in a new PowerShell window and serves the frontend on port 8080
.\run_frontend.ps1 -Port 8080
```

Open browser (auto-opens):
- http://localhost:8080/index.html

### Option B: Serve only the frontend

From this folder:

```powershell
# Serve frontend and open the browser
.\serve_frontend.ps1 -Port 8080
```

Run the backend separately:

```powershell
python web_designer_backend.py
```

## Features

- **Real-time collaboration** over WebSocket: cursors, widget ops
- **Undo/Redo** with history timeline (Ctrl+Z / Ctrl+Y)
- **Widget toolbox** with drag & drop (Label, Button, Panel, etc.)
- **Properties panel** with live updates
- **Canvas controls**: zoom in/out/reset, zoom-to-fit, grid toggle with variable size
- **Multi-select**: Shift-click or marquee selection (drag on empty canvas)
- **Group operations**: Move and resize multiple widgets simultaneously
- **Alignment guides**: Visual snapping to other widgets' edges and centers
- **Performance optimizations**: Offscreen grid caching, throttled rendering, dirty-rect updates
- **Canvas panning**: Space+drag or middle mouse button to pan the canvas
- **Clipboard operations**: Copy/paste widgets with Ctrl+C/V
- **Export**: Export design to JSON or PNG via Export button
- **Auto-save**: Automatic save to localStorage every 30 seconds
- **Quick edit**: Double-click widget to edit text
- **Hover info**: Hover over widgets to see type, size, and position
- **Keyboard shortcuts**:
  - `Escape` — Clear selection
  - `Delete` — Remove selected widget
  - `Arrow keys` — Nudge widget (Shift for 10px)
  - `Ctrl+A` — Select all widgets
  - `Ctrl+C` — Copy selected widget
  - `Ctrl+V` — Paste widget from clipboard
  - `Ctrl+D` — Duplicate selected widget
  - `Ctrl+wheel` — Zoom at cursor position
  - `Space+drag` — Pan canvas
  - `+/-` — Zoom in/out
  - `0` — Reset zoom to 100%
  - `F` — Zoom to fit
  - `G` — Toggle grid
  - `[/]` — Send to back / Bring to front
- **Z-order controls**: Bring to front / send to back
- **Cursor feedback**: Contextual cursors for move/resize operations
- **Selection feedback**: Display count of selected widgets in status bar
- **History squashing**: Drag operations create single undo entries

## Usage Notes
- On load, a join modal asks for your `username` and `project ID`.
- Use two browser windows with the same `project ID` to test collaboration.
- The frontend expects the backend WebSocket at `ws://localhost:8000/ws/projects/{project}`.

## Files
- `index.html` — UI layout
- `styles.css` — Dark theme styles
- `app.js` — App wiring and interactions
- `websocket-client.js` — WS connection, protocol helpers
- `canvas-renderer.js` — Canvas drawing & transforms
- `undo-redo-ui.js` — Undo/redo buttons, history timeline
- `properties-editor.js` — Dynamic properties form

## Manual QA Checklist
- Join with two users; verify both appear in header
- Move mouse on canvas; remote cursor updates with label
- Drag a widget from toolbox; appears in both windows
- Select widget; edit properties; changes sync across windows
- Use Undo/Redo (toolbar or Ctrl+Z/Y); timeline updates, buttons enabled/disabled

## Troubleshooting
- If the page can’t connect, ensure backend runs on `localhost:8000`.
- If nothing renders, open DevTools Console and look for errors.
- If CORS issues occur when serving differently, use the included scripts which serve via `http.server`.
