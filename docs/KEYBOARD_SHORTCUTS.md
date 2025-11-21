# UI Designer Keyboard Shortcuts Reference

Quick reference guide for keyboard shortcuts in ESP32OS UI Designer.

## Component Palette Shortcuts (Ctrl+1-9)

Press `Ctrl` + number key to quickly insert components:

| Shortcut | Component | Description |
|----------|-----------|-------------|
| **Ctrl+1** | AlertDialog | Alert dialog with OK button |
| **Ctrl+2** | ConfirmDialog | Confirmation dialog with Yes/No buttons |
| **Ctrl+3** | InputDialog | Input dialog with text field |
| **Ctrl+4** | TabBar | Tab bar with 3 tabs |
| **Ctrl+5** | VerticalMenu | Vertical menu list |
| **Ctrl+6** | Breadcrumb | Breadcrumb navigation |
| **Ctrl+7** | StatCard | Statistics card with value and label |
| **Ctrl+8** | ProgressCard | Progress card with percentage |
| **Ctrl+9** | StatusIndicator | Status indicator with colored dot |

**Numpad Support**: You can also use numpad keys (Ctrl+Numpad1-9) for the same functions.

## General Editing Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+Z** | Undo last action |
| **Ctrl+Y** | Redo last undone action |
| **Ctrl+S** | Save current design |
| **Ctrl+C** | Copy selected widget(s) |
| **Ctrl+V** | Paste copied widget(s) |
| **Ctrl+D** | Duplicate selected widget(s) |
| **Ctrl+A** | Select all widgets |

## Navigation & Movement

| Shortcut | Action |
|----------|--------|
| **Arrow Keys** | Nudge selected widget(s) by 1 pixel |
| **Mouse Drag** | Move selected widget(s) |
| **Shift+Drag** | Resize widget (from handle) |
| **Ctrl+MouseWheel** | Zoom in/out centered on cursor |
| **Ctrl+Plus / Ctrl+Minus / Ctrl+0** | Zoom in / Zoom out / Reset zoom |
| **Space (hold) + Drag** | Hand-pan the canvas |

## Component Palette Window

### Search & Filter

- **Search Box**: Type to filter components by name or description
- **Category Dropdown**: Filter by category (Dialogs, Navigation, Controls, Data Display, Layouts)
- **Live Filter**: Results update as you type

### Adding Components

Three ways to add components:

1. **Click "➕ Add to Canvas"** button in palette
2. **Use keyboard shortcut** (Ctrl+1-9)
3. **Drag-and-drop** (coming soon)

## Tips & Tricks

### Quick Workflow

1. Press `Ctrl+4` to add a TabBar
2. Use arrow keys to position it
3. Press `Ctrl+5` to add a VerticalMenu
4. Press `Ctrl+D` to duplicate it
5. Press `Ctrl+S` to save

### Component Visibility

- Shortcuts are shown in palette window next to component names (green badges)
- First 9 components alphabetically have shortcuts
- Use search to quickly find specific components

### Multi-Selection

- Click individual widgets while holding Shift
- Use `Ctrl+A` to select all
- Arrow keys move all selected widgets together

## Export Shortcuts

While not keyboard shortcuts, these are accessible from menus:

- **Export JSON**: Save scene as JSON
- **Export C Code**: Generate ESP32 firmware code
- **Export WidgetConfig**: Save as ASCII text format
- **ASCII Preview**: Open live ASCII preview window

---

**Note**: All shortcuts work in the main UI Designer preview window. Make sure the preview window has focus when using keyboard shortcuts.
