# ESP32OS Collaborative Web Designer

Real-time collaborative UI designer for ESP32OS with WebSocket-based multi-user editing.

## Features

- **Real-time Collaboration**: Multiple users can edit the same design simultaneously
- **Cursor Tracking**: See where other users are working in real-time
- **User Identification**: Each user gets a unique color and name
- **Live Updates**: Widget changes are broadcast instantly to all connected users
- **Session Management**: Automatic cleanup of disconnected users
- **REST API**: Complete CRUD operations for projects and designs
- **WebSocket Protocol**: Structured message protocol for reliable collaboration

## Architecture

### Backend (FastAPI + WebSockets)

The backend provides:

- REST API for project management (`/api/projects/*`)
- WebSocket endpoint for real-time collaboration (`/ws/projects/{project_id}`)
- In-memory session management with user tracking
- Version counter for operational transformation

### Frontend (HTML5 + JavaScript)

The web client provides:

- HTML5 Canvas rendering of UI designs
- Real-time cursor visualization
- User list with color coding
- Activity log for collaboration events
- Mouse-based cursor tracking

## Installation

### Prerequisites

```bash
# Install FastAPI and dependencies
pip install fastapi uvicorn websockets

# Or install all optional dependencies
pip install -r requirements.txt
```

### Quick Start

1. **Start the backend server:**

   ```bash
   python web_designer_backend.py
   ```

   Server will start on `http://localhost:8000`

2. **Open the web client:**

   Open `web_designer_client.html` in your browser, or navigate to:

   ```text
   file:///path/to/ESP32OS/web_designer_client.html
   ```

3. **Create a demo project (optional):**

   ```bash
   curl -X POST http://localhost:8000/api/projects \
     -H "Content-Type: application/json" \
     -d '{"id": "demo_project", "width": 128, "height": 64}'
   ```

4. **Connect and collaborate:**

   - Enter project ID (e.g., `demo_project`)
   - Enter your name
   - Click "Connect"
   - Open the same page in another browser/tab to see collaboration in action!

## API Reference

### REST Endpoints

#### List Projects

```http
GET /api/projects
```

Response:

```json
[
  {
    "id": "demo_project",
    "path": "/path/to/ui_projects/demo_project/design.json"
  }
]
```

#### Get Project Summary

```http
GET /api/projects/{project_id}
```

Response:

```json
{
  "project_id": "demo_project",
  "scenes": [
    {
      "name": "main",
      "width": 128,
      "height": 64,
      "widget_count": 3
    }
  ]
}
```

#### Create Project

```http
POST /api/projects
Content-Type: application/json

{
  "id": "new_project",
  "width": 128,
  "height": 64
}
```

#### Get Design JSON

```http
GET /api/projects/{project_id}/design
```

#### Update Design JSON

```http
PUT /api/projects/{project_id}/design
Content-Type: application/json

{
  "width": 128,
  "height": 64,
  "scenes": { ... }
}
```

#### Get Session State

```http
GET /api/projects/{project_id}/session
```

Response:

```json
{
  "project_id": "demo_project",
  "users": [
    {
      "id": "uuid-here",
      "name": "Alice",
      "color": "#FF6B6B",
      "cursor_x": 100,
      "cursor_y": 50,
      "last_activity": 1700000000.0
    }
  ],
  "version": 5
}
```

### WebSocket Protocol

Connect to: `ws://localhost:8000/ws/projects/{project_id}`

#### Client → Server Messages

**Join Session:**

```json
{
  "op": "join",
  "user_name": "Alice"
}
```

**Update Cursor:**

```json
{
  "op": "cursor",
  "x": 100,
  "y": 200
}
```

**Add Widget:**

```json
{
  "op": "widget_add",
  "widget": {
    "type": "label",
    "x": 10,
    "y": 20,
    "width": 30,
    "height": 10,
    "text": "Hello"
  }
}
```

**Update Widget:**

```json
{
  "op": "widget_update",
  "widget_id": "widget-uuid",
  "changes": {
    "x": 15,
    "text": "Updated"
  }
}
```

**Delete Widget:**

```json
{
  "op": "widget_delete",
  "widget_id": "widget-uuid"
}
```

**Heartbeat (keep-alive):**

```json
{
  "op": "heartbeat"
}
```

#### Server → Client Messages

**Session State (on join):**

```json
{
  "op": "session_state",
  "user_id": "your-uuid-here",
  "session": {
    "project_id": "demo_project",
    "users": [...],
    "version": 5
  }
}
```

**User Joined:**

```json
{
  "op": "user_joined",
  "user": {
    "id": "uuid",
    "name": "Bob",
    "color": "#4ECDC4",
    ...
  }
}
```

**User Left:**

```json
{
  "op": "user_left",
  "user_id": "uuid"
}
```

**Cursor Update:**

```json
{
  "op": "cursor",
  "user_id": "uuid",
  "x": 100,
  "y": 200
}
```

**Widget Operations (add/update/delete):**

```json
{
  "op": "widget_add",
  "user_id": "uuid",
  "version": 6,
  "widget": { ... }
}
```

## Development

### Running Tests

```bash
# Run all web designer tests
pytest test_web_designer_backend.py test_web_designer_collab.py -v

# Run only collaboration tests
pytest test_web_designer_collab.py -v
```

### Project Structure

```text
ESP32OS/
├── web_designer_backend.py       # FastAPI backend server
├── web_designer_client.html      # HTML5 web client
├── test_web_designer_backend.py  # Backend unit tests
├── test_web_designer_collab.py   # Collaboration integration tests
├── ui_projects/                  # Project storage directory
│   └── {project_id}/
│       └── design.json
└── WEB_DESIGNER_README.md        # This file
```

### Extending the Protocol

To add new operations:

1. **Backend**: Add handler in `project_ws()` function in `web_designer_backend.py`
2. **Frontend**: Add handler in `handleMessage()` function in `web_designer_client.html`
3. **Tests**: Add test case in `test_web_designer_collab.py`

Example:

```python
# Backend
elif op == "my_custom_op":
    # Process message
    await _broadcast(session, user_id, {
        "op": "my_custom_op",
        "user_id": user_id,
        ...
    })

# Frontend
case 'my_custom_op':
    // Handle custom operation
    log(`Custom op from ${msg.user_id}`, 'info');
    break;
```

## Deployment

### Production Considerations

1. **Enable HTTPS/WSS**: Use reverse proxy (nginx, traefik) with SSL certificates
2. **Authentication**: Implement JWT tokens or OAuth for user authentication
3. **Persistence**: Add database (PostgreSQL, MongoDB) for design storage
4. **Scaling**: Use Redis for session state sharing across multiple backend instances
5. **Rate Limiting**: Protect WebSocket endpoints from abuse

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "web_designer_backend.py"]
```

```bash
# Build and run
docker build -t esp32os-web-designer .
docker run -p 8000:8000 esp32os-web-designer
```

### Environment Variables

- `ESP32OS_WEB_BUILD_ENABLED=1`: Enable web-triggered builds (disabled by default)
- `ESP32OS_WEB_API_KEY=secret`: Require API key for builds
- `ESP32OS_AUTO_EXPORT=0`: Disable auto-export when creating designs

## Limitations

- In-memory session storage (lost on server restart)
- No conflict resolution beyond last-write-wins
- No persistent undo/redo history
- Basic operational transformation (version counter only)

## Future Enhancements

- [ ] Persistent session storage (Redis/database)
- [ ] Advanced OT/CRDT for true conflict-free collaboration
- [ ] Real-time presence indicators on widgets
- [ ] Chat/comments system
- [ ] Version history and rollback
- [ ] Role-based permissions (viewer/editor/admin)
- [ ] Project templates and asset library
- [ ] Integration with ESP32 live preview

## Troubleshooting

**WebSocket connection fails:**

- Check that backend is running on port 8000
- Verify firewall allows WebSocket connections
- Check browser console for CORS errors

**Users not seeing each other:**

- Ensure both users join the same project ID
- Check session endpoint: `GET /api/projects/{id}/session`
- Verify WebSocket is in OPEN state

**Cursor not updating:**

- Check that mouse is over the canvas element
- Verify WebSocket messages are being sent (browser DevTools → Network → WS)
- Check for JavaScript errors in console

## License

Part of ESP32OS project. See main README.md for license information.

## Contributing

Contributions welcome! Please ensure:

- All tests pass: `pytest test_web_designer*.py`
- Code follows existing style
- New features include tests and documentation
- WebSocket protocol changes are backward compatible

## Support

For issues and questions:

- GitHub Issues: <https://github.com/atrep123/ESPOS/issues>
- Label as `web` and `collaboration`
