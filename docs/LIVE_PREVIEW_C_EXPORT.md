# Live Preview & C Export - Quick Reference

## 🎨 Live Preview Mode

Auto-refresh browser when you edit UI designs in real-time.

### Quick Start

```powershell
python ui_designer.py --live-preview examples/demo_scene.json
```

This will:
- Open browser with live-updating HTML preview
- Watch `demo_scene.json` for changes
- Auto-regenerate HTML when you save edits
- Push reload signal via WebSocket (port 8765)

### Workflow

1. Start live preview server: `python ui_designer.py --live-preview my_design.json`
2. Browser opens automatically showing current design
3. Edit JSON file (or use UI designer interactively to save changes)
4. Save → server detects change → HTML regenerates → browser refreshes

### Options

The underlying script `ui_designer_live.py` supports:

```powershell
python ui_designer_live.py --json design.json [--html output.live.html] [--ws-port 8765] [--no-browser]
```

- `--json`: Design file to watch (required)
- `--html`: Custom output path (default: `<json_name>.live.html`)
- `--ws-port`: WebSocket port (default: 8765)
- `--no-browser`: Don't auto-open browser

### VS Code Task

Use the task **"UI Designer: Live Preview"** from the command palette:

1. Press `Ctrl+Shift+P`
2. Type "Run Task"
3. Select "UI Designer: Live Preview"
4. Enter JSON file path when prompted

## 🔧 C Header Export

Generate embedded-ready const widget arrays for firmware integration.

### Quick Start

```powershell
python ui_designer.py --export-c-header examples/demo_scene.json src/ui_demo.h
```

Output:
```c
static const ui_widget_t demo_widgets[] = {
    { .type = UI_WIDGET_LABEL, .x = 0, .y = 0, .width = 128, .height = 10, ... },
    { .type = UI_WIDGET_BUTTON, .x = 39, .y = 16, ... },
    // ...
};

static const ui_scene_t demo_scene = {
    .name = "Demo",
    .width = 128, .height = 64,
    .widget_count = 4,
    .widgets = demo_widgets,
};
```

### Direct Script Usage

```powershell
python ui_export_c_header.py design.json -o output.h
```

### Integration Example

```c
#include "ui_demo.h"

void app_main(void) {
    // Load scene from generated header
    ui_render_scene(&demo_scene);
}
```

### Color Mapping

The exporter maps JSON colors to C constants:

| JSON Color | C Constant |
|------------|------------|
| "black" | UI_COLOR_BLACK |
| "white" | UI_COLOR_WHITE |
| "red" | UI_COLOR_RED |
| "#FF5500" | 0xFF5500 |

Ensure `ui_render.h` defines these constants or use hex literals.

### Widget Type Support

All widget types are mapped to `UI_WIDGET_*` enums:
- label → `UI_WIDGET_LABEL`
- button → `UI_WIDGET_BUTTON`
- gauge → `UI_WIDGET_GAUGE`
- progressbar → `UI_WIDGET_PROGRESSBAR`
- etc.

### Scene Registry

Multiple scenes generate a registry array:

```c
static const ui_scene_t* all_scenes[] = {
    &main_menu_scene,
    &settings_scene,
    &dashboard_scene,
};
#define SCENE_COUNT 3
```

Use this for scene switching:

```c
for (int i = 0; i < SCENE_COUNT; i++) {
    if (strcmp(all_scenes[i]->name, "Settings") == 0) {
        ui_render_scene(all_scenes[i]);
        break;
    }
}
```

## 🚀 Combined Workflow

Design → Preview → Export → Deploy

```powershell
# 1. Create design interactively
python ui_designer.py

# 2. Live preview while editing
python ui_designer.py --live-preview my_design.json

# 3. Export to C header
python ui_designer.py --export-c-header my_design.json src/ui_scenes.h

# 4. Build firmware
pio run -t upload
```

## 📝 Tips

### Live Preview

- Keep browser window visible for instant feedback
- Edit JSON directly or use CLI commands
- Use `Ctrl+C` in terminal to stop server
- WebSocket reconnects automatically if connection drops

### C Export

- Use snake_case for scene names (better C identifiers)
- Avoid special characters in text strings
- Check generated header for correct includes
- Widget arrays are `const` → stored in flash on ESP32
- Scene structs reference widget arrays → minimal RAM usage

### Debugging

If live preview doesn't refresh:
- Check console for WebSocket errors
- Verify `ui_designer_preview.py` exists
- Ensure JSON is valid (use `python -m json.tool design.json`)

If C export fails:
- Check JSON structure (scenes → widgets)
- Verify all widget types are recognized
- Look for unsupported characters in strings

## 🔗 See Also

- `UI_DESIGNER_GUIDE.md` - Full designer documentation
- `SIMULATOR_README.md` - Testing exported designs
- `ui_render.h` - Widget struct definitions
