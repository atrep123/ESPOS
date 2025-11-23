# ESP32OS Web Designer

## Overview

A modern web-based UI designer for ESP32OS. Supports collaborative editing, live preview, and export to firmware formats.

### Features
- Drag & drop widget editing
- Real-time preview (WebSocket bridge)
- Multi-user collaboration
- Export to JSON, C, HTML
- Snap-to-grid, magnetic guides
- Undo/redo, history

### Quick Start

1. Start the frontend server:
   ```powershell
   .\web_designer_frontend\serve_frontend.ps1
   ```
2. Open [http://localhost:8080](http://localhost:8080) in your browser
3. Connect to ESP32OS simulator for live preview

### Architecture
- `app.js` – main UI logic
- `canvas-renderer.js` – widget rendering
- `preview-client.js` – live preview bridge
- `properties-editor.js` – widget property panel
- `undo-redo-ui.js` – history management
- `websocket-client.js` – collaboration

### Documentation
- See `UI_DESIGNER_GUIDE.md` for design patterns
- See `SIMULATOR_README.md` for backend integration

---

For feature requests, use the GitHub issue template: `.github/ISSUE_TEMPLATE/feature_request.md`
