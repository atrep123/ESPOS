# Widget Operations - Quick Reference

## Message Flow Architecture

```text
┌─────────────────┐
│  Web Designer   │
│   (app.js)      │
└────────┬────────┘
         │ WebSocket
         │ ws://localhost:3000
         ▼
┌─────────────────┐
│  Bridge Server  │
│ web_sim_bridge  │
│   Port: 8765    │
└────────┬────────┘
         │ WebSocket
         │ ws://localhost:8765
         ▼
┌─────────────────┐
│   Simulator     │
│   sim_run.py    │
└─────────────────┘
```

## Widget Operations

### 1. Add Widget

**Web Designer (JavaScript):**
```javascript
ws.addWidget({
    id: 'widget-123',
    type: 'button',
    x: 10, y: 20,
    width: 80, height: 30,
    text: 'Click Me'
});
```

**Bridge receives:**
```json
{
    "op": "widget_add",
    "widget": { "id": "widget-123", "type": "button", ... }
}
```

**Simulator applies (sim_run.py line 1039):**
```python
widget = data.get('widget', {})
latest_design_holder['scene'].setdefault('widgets', []).append(widget)
```

---

### 2. Update Widget (Drag & Drop)

**Web Designer (JavaScript):**
```javascript
// On drag end
ws.updateWidget('widget-123', { x: 50, y: 60 });
```

**Bridge receives:**
```json
{
    "op": "widget_update",
    "widget_id": "widget-123",
    "changes": { "x": 50, "y": 60 }
}
```

**Simulator applies (sim_run.py line 1046):**
```python
widget_id = data.get('widget_id')
changes = data.get('changes', {})
for w in latest_design_holder['scene']['widgets']:
    if w.get('id') == widget_id:
        w.update(changes)  # ✓ Position updated!
        break
```

---

### 3. Delete Widget

**Web Designer (JavaScript):**
```javascript
ws.deleteWidget('widget-123');
```

**Bridge receives:**
```json
{
    "op": "widget_delete",
    "widget_id": "widget-123"
}
```

**Simulator applies (sim_run.py line 1057):**
```python
widget_id = data.get('widget_id')
latest_design_holder['scene']['widgets'] = [
    w for w in widgets if w.get('id') != widget_id
]
```

---

## Testing

**Unit tests:**
```bash
# Test bridge widget operations
python test_bridge_widget_update.py

# Test end-to-end flow
python test_widget_operations_e2e.py
```

**Integration test:**
```bash
# All widget operation tests
pytest test_bridge_widget_update.py test_widget_operations_e2e.py -v
```

---

## Files Modified (Nov 2025 - Widget Operations Fix)

1. **`sim_run.py`** (lines 1039-1065)
   - ✓ widget_add: Now adds widgets to scene
   - ✓ widget_update: Now applies position/property changes
   - ✓ widget_delete: Now removes widgets from scene

2. **`test_bridge_widget_update.py`** - Unit tests for each operation

3. **`test_widget_operations_e2e.py`** - End-to-end flow tests

4. **`DRAG_DROP_FIX.md`** - Complete technical documentation

---

## Debugging Tips

**Enable bridge debug output:**
```bash
# Run simulator with bridge
python sim_run.py --bridge-url ws://localhost:8765

# Watch for messages:
# "Bridge: widget added id=widget-123"
# "Bridge: widget updated id=widget-123 changes={'x': 50, 'y': 60}"
# "Bridge: widget deleted id=widget-123"
```

**Check widget list in simulator:**
```python
# In sim_run.py, add debug print:
if latest_design_holder.get('scene'):
    widgets = latest_design_holder['scene'].get('widgets', [])
    print(f"Current widgets: {[w.get('id') for w in widgets]}")
```

**Verify WebSocket messages:**
```bash
# Use browser DevTools → Network → WS
# Watch for widget_add/update/delete messages
```

---

## Common Issues

**Problem:** Drag and drop doesn't update simulator
- **Check:** Bridge connection (`ws://localhost:8765`)
- **Check:** Simulator running with `--bridge-url`
- **Check:** Widget ID consistency

**Problem:** Widget appears but can't be dragged
- **Solution:** This was the original bug - ensure you have the latest `sim_run.py` with widget_update handler

**Problem:** Multiple simulators out of sync
- **Note:** Bridge broadcasts to ALL connected simulators - they should stay in sync

---

## Protocol Reference

**Widget Type Mapping:**
```javascript
// Web Designer → Simulator
'label'       → 'LABEL'
'button'      → 'BUTTON'
'checkbox'    → 'CHECKBOX'
'slider'      → 'SLIDER'
'progressbar' → 'PROGRESSBAR'
'panel'       → 'PANEL'
```

**Required Widget Properties:**
```json
{
    "id": "unique-widget-id",
    "type": "label|button|checkbox|...",
    "x": 0,
    "y": 0,
    "width": 50,
    "height": 20
}
```

**Optional Properties:**
```json
{
    "text": "Label Text",
    "value": 50,
    "checked": true,
    "color": "#FF0000",
    "bg_color": "#000000",
    "border": true,
    "visible": true
}
```

---

## Performance Notes

**Current Optimization (Already Implemented):**
- ✅ Widget updates **are optimized** during drag - NO updates sent while dragging
- ✅ Only **final position** is sent on drag end (see `app.js` line 776)
- ✅ Local preview updates during drag (renderer only, no WebSocket)
- ✅ This prevents network spam and reduces bridge/simulator load

**Architecture:**
- Bridge holds full design state in memory (no persistence by default)
- Simulator applies updates immediately when received
- Web frontend uses requestAnimationFrame for smooth rendering

**Scaling Considerations:**
- For 100+ widgets: Consider viewport culling (only render visible widgets)
- For 1000+ widgets: Use `LazyLoader` from `performance_optimizer.py`
- For collaborative editing: Updates are already broadcast-optimized

---

Last Updated: November 20, 2025
Version: 1.0 (Widget Operations Fix)
