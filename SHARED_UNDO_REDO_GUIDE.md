# Shared Undo/Redo System Guide

Collaborative undo/redo system for multi-user editing with conflict resolution.

## Features

### 📝 Operation-Based History

Track all edits as discrete operations:
- **Add Widget** - Create new UI elements
- **Delete Widget** - Remove widgets (with state preservation)
- **Move Widget** - Reposition widgets
- **Resize Widget** - Change dimensions
- **Modify Property** - Update widget properties (text, color, etc.)
- **Reorder Widget** - Change z-index/stacking
- **Group/Ungroup** - Combine/separate widgets

### ⏮️ ⏭️ Undo/Redo

Full undo/redo support:
- Unlimited undo (configurable max history)
- Branching history (new operations after undo create new branch)
- Operation descriptions for UI display
- Callbacks for undo/redo actions

### 👥 Collaborative Editing

Multi-user support with conflict resolution:
- Local and remote operation tracking
- Operational Transformation (OT) inspired conflict resolution
- Last-writer-wins for concurrent edits
- Automatic conflict detection and resolution

### 💾 Persistence

Save and restore history:
- JSON serialization
- Session tracking
- Version management
- Full state replay

## Usage

### Basic Undo/Redo

```python
from shared_undo_redo import UndoRedoManager, OperationBuilder

# Create manager
manager = UndoRedoManager(max_history=50, user_id="user1")

# Execute operations
op1 = OperationBuilder.add_widget("btn1", "button", 10, 20, 100, 30, text="Click me")
manager.execute(op1)

op2 = OperationBuilder.move_widget("btn1", 10, 20, 50, 60)
manager.execute(op2)

# Check availability
if manager.can_undo():
    print("Can undo!")

# Undo last operation
undone = manager.undo()
print(f"Undone: {manager.get_operation_description(undone)}")

# Redo
if manager.can_redo():
    redone = manager.redo()
    print(f"Redone: {manager.get_operation_description(redone)}")
```

### With Callbacks

```python
def on_operation(op):
    """Called when operation is executed"""
    print(f"✓ {manager.get_operation_description(op)}")
    # Update UI to reflect change

def on_undo(op):
    """Called when operation is undone"""
    print(f"⟲ Undo: {manager.get_operation_description(op)}")
    # Reverse the operation in UI

def on_redo(op):
    """Called when operation is redone"""
    print(f"⟳ Redo: {manager.get_operation_description(op)}")
    # Reapply the operation in UI

manager.on_operation = on_operation
manager.on_undo = on_undo
manager.on_redo = on_redo
```

### Building Operations

```python
from shared_undo_redo import OperationBuilder

# Add widget
op = OperationBuilder.add_widget(
    widget_id="btn1",
    widget_type="button", 
    x=10, y=20,
    width=100, height=30,
    text="Click",  # Additional properties
    color="#007acc"
)

# Delete widget (preserve state for undo)
widget_state = {'type': 'button', 'x': 10, 'y': 20, 'text': 'Click'}
op = OperationBuilder.delete_widget("btn1", widget_state)

# Move widget
op = OperationBuilder.move_widget(
    widget_id="btn1",
    old_x=10, old_y=20,
    new_x=50, new_y=60
)

# Resize widget
op = OperationBuilder.resize_widget(
    widget_id="btn1",
    old_width=100, old_height=30,
    new_width=120, new_height=35
)

# Modify property
op = OperationBuilder.modify_property(
    widget_id="btn1",
    property_name="text",
    old_value="Click",
    new_value="Press"
)

# Group widgets
op = OperationBuilder.group_widgets(
    group_id="group1",
    widget_ids=["btn1", "btn2", "label1"]
)
```

### Persistence

```python
# Save history to file
manager.save_state("undo_history.json")

# Load history from file
manager2 = UndoRedoManager()
manager2.load_state("undo_history.json")

# Continue from saved state
if manager2.can_undo():
    manager2.undo()
```

### Collaborative Editing

```python
from shared_undo_redo import CollaborativeUndoRedo

# Create collaborative manager
collab = CollaborativeUndoRedo(user_id="alice", max_history=100)

# Broadcast callback for WebSocket/network
def broadcast_operation(op):
    """Send operation to other users"""
    websocket.send(json.dumps(op.to_dict()))

collab.on_broadcast = broadcast_operation

# Execute local operation (automatically broadcasts)
op = OperationBuilder.add_widget("btn1", "button", 10, 20, 100, 30)
collab.execute_local(op)

# Receive operation from remote user
def on_websocket_message(message):
    """Handle incoming operation from other user"""
    data = json.loads(message)
    remote_op = Operation.from_dict(data)
    
    # Transform and apply
    transformed = collab.receive_remote(remote_op)
    
    # Update UI with transformed operation
    apply_operation_to_ui(transformed)

# Get complete history (local + remote, sorted by time)
all_operations = collab.get_all_operations()
for op in all_operations:
    print(f"{op.user_id}: {collab.local_manager.get_operation_description(op)}")
```

### Conflict Resolution

The system handles conflicts automatically:

```python
# Scenario: Two users move the same widget concurrently

# Alice moves widget at t=1
alice_op = OperationBuilder.move_widget("btn1", 0, 0, 10, 10)
alice_op.user_id = "alice"
alice_op.timestamp = 1.0

# Bob moves same widget at t=2 (later)
bob_op = OperationBuilder.move_widget("btn1", 0, 0, 20, 20)
bob_op.user_id = "bob"
bob_op.timestamp = 2.0

# When Alice receives Bob's operation:
# - System detects concurrent edit on same widget
# - Last-writer-wins: Bob's position (20, 20) is used
# - Alice's local history is preserved for her own undo

transformed = collab.receive_remote(bob_op)
# transformed.data['x'] == 20 (Bob's value wins)
```

### Delete Conflicts

```python
# Scenario: User deletes widget while another user is editing it

# Alice deletes widget
collab_alice.execute_local(
    OperationBuilder.delete_widget("btn1", widget_state)
)

# Bob tries to move the deleted widget (timestamp before delete)
bob_op = OperationBuilder.move_widget("btn1", 0, 0, 10, 10)
bob_op.timestamp = earlier_timestamp

# When Alice receives Bob's operation:
transformed = collab_alice.receive_remote(bob_op)
# transformed.data['no_op'] == True (operation is nullified)
```

## Integration Examples

### Tkinter Integration

```python
import tkinter as tk
from shared_undo_redo import UndoRedoManager, OperationBuilder

class UndoableCanvas:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.manager = UndoRedoManager(user_id="user1")
        self.widgets = {}
        
        # Setup callbacks
        self.manager.on_undo = self._handle_undo
        self.manager.on_redo = self._handle_redo
    
    def add_widget(self, widget_id, widget_type, x, y, width, height):
        """Add widget with undo support"""
        # Create widget in canvas
        item_id = self.canvas.create_rectangle(
            x, y, x+width, y+height,
            fill="lightblue", tags=widget_id
        )
        self.widgets[widget_id] = item_id
        
        # Record operation
        op = OperationBuilder.add_widget(
            widget_id, widget_type, x, y, width, height
        )
        self.manager.execute(op)
    
    def move_widget(self, widget_id, new_x, new_y):
        """Move widget with undo support"""
        if widget_id not in self.widgets:
            return
        
        # Get current position
        item_id = self.widgets[widget_id]
        coords = self.canvas.coords(item_id)
        old_x, old_y = coords[0], coords[1]
        
        # Move in canvas
        dx, dy = new_x - old_x, new_y - old_y
        self.canvas.move(item_id, dx, dy)
        
        # Record operation
        op = OperationBuilder.move_widget(
            widget_id, old_x, old_y, new_x, new_y
        )
        self.manager.execute(op)
    
    def _handle_undo(self, op):
        """Handle undo operation"""
        if op.type == OperationType.ADD_WIDGET:
            # Remove widget
            if op.widget_id in self.widgets:
                self.canvas.delete(self.widgets[op.widget_id])
                del self.widgets[op.widget_id]
        
        elif op.type == OperationType.MOVE_WIDGET:
            # Move back to old position
            old_x, old_y = op.data['old_x'], op.data['old_y']
            new_x, new_y = op.data['x'], op.data['y']
            dx, dy = old_x - new_x, old_y - new_y
            self.canvas.move(self.widgets[op.widget_id], dx, dy)
    
    def _handle_redo(self, op):
        """Handle redo operation"""
        if op.type == OperationType.ADD_WIDGET:
            # Recreate widget
            x, y = op.data['x'], op.data['y']
            width, height = op.data['width'], op.data['height']
            item_id = self.canvas.create_rectangle(
                x, y, x+width, y+height,
                fill="lightblue", tags=op.widget_id
            )
            self.widgets[op.widget_id] = item_id
        
        elif op.type == OperationType.MOVE_WIDGET:
            # Move to new position
            old_x, old_y = op.data['old_x'], op.data['old_y']
            new_x, new_y = op.data['x'], op.data['y']
            dx, dy = new_x - old_x, new_y - old_y
            self.canvas.move(self.widgets[op.widget_id], dx, dy)
    
    def undo(self):
        """Undo last operation"""
        if self.manager.can_undo():
            self.manager.undo()
    
    def redo(self):
        """Redo next operation"""
        if self.manager.can_redo():
            self.manager.redo()

# Usage
root = tk.Tk()
canvas = tk.Canvas(root, width=400, height=300)
canvas.pack()

undoable = UndoableCanvas(canvas)

# Add widgets
undoable.add_widget("btn1", "button", 50, 50, 100, 30)
undoable.add_widget("lbl1", "label", 150, 100, 80, 20)

# Move widget
undoable.move_widget("btn1", 100, 100)

# Undo/Redo with keyboard
root.bind('<Control-z>', lambda e: undoable.undo())
root.bind('<Control-y>', lambda e: undoable.redo())
```

### WebSocket Collaborative Example

```python
import asyncio
import websockets
import json
from shared_undo_redo import CollaborativeUndoRedo, Operation

class CollaborativeEditor:
    def __init__(self, user_id, websocket_url):
        self.user_id = user_id
        self.collab = CollaborativeUndoRedo(user_id)
        self.websocket_url = websocket_url
        self.ws = None
        
        # Setup broadcast callback
        self.collab.on_broadcast = self._broadcast_operation
    
    async def connect(self):
        """Connect to WebSocket server"""
        self.ws = await websockets.connect(self.websocket_url)
        
        # Start receiving messages
        asyncio.create_task(self._receive_messages())
    
    def _broadcast_operation(self, op):
        """Send operation to other users"""
        if self.ws:
            message = json.dumps({
                'type': 'operation',
                'data': op.to_dict()
            })
            asyncio.create_task(self.ws.send(message))
    
    async def _receive_messages(self):
        """Receive operations from other users"""
        async for message in self.ws:
            data = json.loads(message)
            
            if data['type'] == 'operation':
                # Receive and transform remote operation
                remote_op = Operation.from_dict(data['data'])
                transformed = self.collab.receive_remote(remote_op)
                
                # Apply to UI
                self._apply_operation(transformed)
    
    def _apply_operation(self, op):
        """Apply operation to UI (implement based on your UI)"""
        pass
    
    def execute(self, op):
        """Execute local operation"""
        self.collab.execute_local(op)
        self._apply_operation(op)

# Usage
editor = CollaborativeEditor("alice", "ws://localhost:8765")
await editor.connect()

# Execute operations - automatically synced with other users
editor.execute(OperationBuilder.add_widget("btn1", "button", 10, 20, 100, 30))
```

## Best Practices

1. **Always preserve state for delete operations** - Store widget state so it can be restored on undo
2. **Use descriptive widget IDs** - Makes debugging and conflict resolution easier
3. **Set reasonable max_history** - Balance memory usage vs. undo depth (50-100 is good)
4. **Handle callbacks asynchronously** - Don't block undo/redo operations
5. **Persist history for session recovery** - Save state on app close, load on startup
6. **Test conflict scenarios** - Ensure your conflict resolution matches expectations
7. **Display operation descriptions in UI** - Use `get_operation_description()` for undo/redo menu items

## Testing

Run comprehensive tests:

```bash
pytest test_shared_undo_redo.py -v
```

All 27 tests passing covering:
- Operation creation and serialization
- Undo/redo functionality
- History management and branching
- Persistence (save/load)
- Collaborative features
- Conflict resolution
- Operation builders

## Demo

Run interactive demo:

```bash
python shared_undo_redo.py
```

Shows:
- Basic undo/redo operations
- Operation descriptions
- State persistence
- Collaborative sync simulation

## Files

- `shared_undo_redo.py` - Complete undo/redo system (500+ lines)
- `test_shared_undo_redo.py` - Comprehensive tests (27 tests)

## Performance

- **Memory**: O(n) where n = max_history (typically 50-100 operations)
- **Undo/Redo**: O(1) - instant
- **Conflict resolution**: O(m) where m = concurrent operations (typically small)
- **Persistence**: O(n) to serialize all operations

## Future Enhancements

Consider adding:
- Compressed history for long sessions
- Periodic snapshots for faster replay
- Fine-grained property diffing
- Custom merge strategies per operation type
- Visual history timeline UI
- Selective undo (cherry-pick operations)

The shared undo/redo system provides production-ready collaborative editing with automatic conflict resolution!
