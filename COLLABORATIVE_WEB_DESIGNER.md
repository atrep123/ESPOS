# Collaborative Web Designer - Documentation

## Overview

The Collaborative Web Designer is a real-time, multi-user UI design tool that allows multiple designers to work together on the same design project simultaneously. Built on top of the ESP32OS UI framework, it provides WebSocket-based synchronization, conflict resolution, and presence awareness.

## Features

### Real-Time Collaboration
- **Multi-user editing**: Multiple users can edit the same design simultaneously
- **Live synchronization**: Changes are broadcast to all connected clients in real-time
- **Presence awareness**: See who else is currently working on the design
- **Cursor tracking**: View other users' cursor positions and selections

### Conflict Resolution
- **Last-write-wins**: Simple conflict resolution strategy
- **Version tracking**: Each change includes a version number for tracking
- **Optimistic updates**: Local changes are applied immediately, then synchronized

### Session Management
- **Persistent sessions**: Design state is maintained on the server
- **Auto-save**: Changes are automatically saved to the server
- **Session recovery**: Reconnect to existing sessions after disconnection

## Architecture

```text
┌─────────────────┐     WebSocket      ┌─────────────────┐
│                 │◄──────────────────►│                 │
│   Web Client    │     JSON msgs      │  Flask Server   │
│   (Browser)     │                    │  + SocketIO     │
│                 │                    │                 │
└─────────────────┘                    └─────────────────┘
                                              │
                                              │ In-memory
                                              ▼
                                       ┌─────────────┐
                                       │   Session   │
                                       │    State    │
                                       └─────────────┘
```

## Protocol

### Message Types

All messages are JSON objects with a `type` field indicating the message type.

#### Client → Server

**1. Join Session**
```json
{
  "type": "join",
  "session_id": "design-123",
  "user_id": "user-456",
  "username": "Alice"
}
```

**2. Widget Update**
```json
{
  "type": "widget_update",
  "widget_id": "widget-789",
  "changes": {
    "x": 100,
    "y": 50,
    "width": 200
  },
  "version": 42
}
```

**3. Widget Create**
```json
{
  "type": "widget_create",
  "widget": {
    "id": "widget-new",
    "type": "button",
    "x": 10,
    "y": 20,
    "width": 80,
    "height": 30,
    "text": "Click me"
  }
}
```

**4. Widget Delete**
```json
{
  "type": "widget_delete",
  "widget_id": "widget-789"
}
```

**5. Cursor Move**
```json
{
  "type": "cursor_move",
  "x": 150,
  "y": 200
}
```

**6. Selection Change**
```json
{
  "type": "selection",
  "widget_ids": ["widget-1", "widget-2"]
}
```

#### Server → Client

**1. Session State**
```json
{
  "type": "session_state",
  "session_id": "design-123",
  "widgets": [...],
  "users": [
    {
      "user_id": "user-456",
      "username": "Alice",
      "cursor": {"x": 100, "y": 50},
      "selection": ["widget-1"]
    }
  ],
  "version": 42
}
```

**2. Widget Update Broadcast**
```json
{
  "type": "widget_updated",
  "widget_id": "widget-789",
  "changes": {...},
  "user_id": "user-456",
  "version": 43
}
```

**3. User Joined/Left**
```json
{
  "type": "user_joined",
  "user_id": "user-789",
  "username": "Bob"
}
```

```json
{
  "type": "user_left",
  "user_id": "user-789"
}
```

**4. Error**
```json
{
  "type": "error",
  "message": "Invalid widget ID",
  "code": "INVALID_WIDGET"
}
```

## API Endpoints

### HTTP REST API

**GET /api/sessions/:session_id**
- Get current session state
- Returns: `{ "session_id": "...", "widgets": [...], "users": [...], "version": 42 }`

**POST /api/sessions**
- Create a new design session
- Body: `{ "session_id": "design-123" }` (optional, auto-generated if not provided)
- Returns: `{ "session_id": "...", "created": true }`

### WebSocket API

**Connect**: `ws://localhost:5000/socket.io/`

All WebSocket communication uses Socket.IO protocol.

## Usage Examples

### Starting the Server

```bash
# Install dependencies
pip install flask flask-socketio python-socketio

# Run server
python web_designer_backend.py

# Server starts on http://localhost:5000
```

### Client Example (JavaScript)

```javascript
// Connect to server
const socket = io('http://localhost:5000');

// Join session
socket.emit('message', {
  type: 'join',
  session_id: 'my-design',
  user_id: 'user-123',
  username: 'Alice'
});

// Listen for session state
socket.on('message', (data) => {
  if (data.type === 'session_state') {
    console.log('Current widgets:', data.widgets);
    console.log('Active users:', data.users);
  }
});

// Update a widget
socket.emit('message', {
  type: 'widget_update',
  widget_id: 'widget-1',
  changes: {
    x: 100,
    y: 50
  },
  version: 42
});

// Create a new widget
socket.emit('message', {
  type: 'widget_create',
  widget: {
    id: 'widget-new',
    type: 'button',
    x: 10,
    y: 20,
    width: 80,
    height: 30,
    text: 'Click me'
  }
});
```

### Client Example (Python)

```python
import socketio

# Create client
sio = socketio.Client()

@sio.on('message')
def on_message(data):
    print(f'Received: {data}')
    if data['type'] == 'session_state':
        print(f'Widgets: {data["widgets"]}')

# Connect
sio.connect('http://localhost:5000')

# Join session
sio.emit('message', {
    'type': 'join',
    'session_id': 'my-design',
    'user_id': 'user-123',
    'username': 'Alice'
})

# Wait for events
sio.wait()
```

## Testing

Run the test suite:

```bash
# Run all collaborative tests
pytest test_web_designer_collab.py -v

# Run specific test
pytest test_web_designer_collab.py::test_session_management -v

# Run with coverage
pytest test_web_designer_collab.py --cov=web_designer_backend
```

## Configuration

Environment variables:

- `WEB_DESIGNER_HOST`: Server host (default: `0.0.0.0`)
- `WEB_DESIGNER_PORT`: Server port (default: `5000`)
- `WEB_DESIGNER_DEBUG`: Enable debug mode (default: `False`)

## Security Considerations

⚠️ **Important**: This is a development/prototype implementation. For production use, consider:

1. **Authentication**: Add user authentication (JWT, OAuth, etc.)
2. **Authorization**: Implement session-level permissions
3. **Rate Limiting**: Prevent abuse with rate limits
4. **Input Validation**: Strict validation of all client inputs
5. **HTTPS/WSS**: Use encrypted connections
6. **CORS**: Configure CORS properly for production
7. **Session Persistence**: Add database backend for session storage

## Troubleshooting

### WebSocket Connection Issues

If clients can't connect:
1. Check firewall settings
2. Verify server is running: `curl http://localhost:5000/health`
3. Check browser console for errors
4. Ensure Socket.IO versions match (client and server)

### Synchronization Issues

If changes don't sync:
1. Check browser console for WebSocket errors
2. Verify message format matches protocol
3. Check server logs for errors
4. Ensure version numbers are being sent correctly

### Performance Issues

For large designs:
1. Implement widget pagination
2. Use incremental updates (delta sync)
3. Throttle cursor/selection updates
4. Consider using Redis for session storage

## Future Enhancements

- [ ] Operational Transformation (OT) for better conflict resolution
- [ ] Undo/Redo across multiple users
- [ ] Voice/video chat integration
- [ ] Design history and branching
- [ ] Real-time comments and annotations
- [ ] Export to various formats (PNG, SVG, JSON, C code)
- [ ] Database persistence (PostgreSQL, MongoDB)
- [ ] Horizontal scaling with Redis pub/sub
- [ ] Mobile client support

## License

Part of ESP32OS project. See main LICENSE file for details.

## Support

For issues and questions:

- GitHub Issues: <https://github.com/atrep123/ESPOS/issues>
- Documentation: See SIMULATOR_README.md and IMPLEMENTATION_SUMMARY.md
