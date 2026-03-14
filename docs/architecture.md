# Pygame Designer — Architecture

Internal architecture of the `cyberpunk_designer/` package and its supporting modules.

For the firmware side and the overall data-flow (JSON → C → ESP32), see
[IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md).

---

## High-level data flow

```
main_scene.json
      │
      ▼
  UIDesigner          (ui_designer.py — model, undo, grid, snap)
      │
      ▼
  CyberpunkEditorApp  (cyberpunk_designer/app.py — init, loop, draw)
   ├─ EditorState     (state.py — selection, drag, scroll, input mode)
   ├─ drawing/*       (canvas, overlays, inspector, toolbar)
   ├─ input_handlers  (keyboard/mouse → state mutations)
   ├─ scene_ops       (z-order, scenes, widget factory, export)
   └─ io_ops          (save/load JSON, autosave, presets)
      │
      ▼
  pygame window (256×128 logical, scaled to desktop)
```

---

## Module map

### Core model (root level)

| Module | Responsibility |
|--------|---------------|
| `ui_models.py` | Data classes: `WidgetConfig`, `SceneConfig`, `WidgetType`, `BorderStyle`, `HardwareProfile`, `Constraints` |
| `ui_designer.py` | `UIDesigner` — scene CRUD, widget add/delete/move, undo/redo snapshots, grid/snap, themes, resource estimation |
| `shared_undo_redo.py` | `UndoRedoManager` — operation-level undo/redo stack with typed `Operation` records |
| `event_manager.py` | `EventManager` — priority-queued event bus with debounce; decouples components |
| `design_tokens.py` | Color, spacing, typography tokens for the editor UI |
| `constants.py` | Root-level shared constants (`NAMED_COLORS`, firmware limits) |

### Application shell (`cyberpunk_designer/`)

| Module | Responsibility |
|--------|---------------|
| `app.py` | `CyberpunkEditorApp` — init phases, main loop (`run()`), draw orchestration, palette/toolbar build |
| `state.py` | `EditorState` — mutable UI state layered on `UIDesigner` (selection, drag, resize, box-select, scroll, input) |
| `constants.py` | Designer-specific constants (panel widths, colors, key codes) |

### Input handling

| Module | Responsibility |
|--------|---------------|
| `input_handlers.py` | `on_key_down`, `on_mouse_down/up/move`, `on_mouse_wheel` — dispatch-table driven keyboard shortcuts, drag/resize logic, box-select |
| `scene_ops.py` | Extracted scene actions: z-order, scene CRUD (new/delete/duplicate/rename/jump), widget factory, auto-arrange, C header export |
| `selection_ops.py` | Copy/paste/cut/delete, clipboard, multi-select helpers |
| `focus_nav.py` | D-pad/encoder focus traversal simulation for embedded preview |

### Drawing pipeline (`cyberpunk_designer/drawing/`)

| Module | Responsibility |
|--------|---------------|
| `__init__.py` | Re-exports ~35 drawing functions |
| `canvas.py` | `draw_canvas()`, `draw_widget_preview()`, rulers, selection info, distance indicators, overflow markers |
| `overlays.py` | Help overlay, context menus, tooltips |
| `panels.py` | Inspector panel, palette panel, status bar |
| `toolbar.py` | Toolbar actions, scene tabs |
| `primitives.py` | `draw_bevel_frame`, `draw_border_style`, `draw_dashed_rect`, `draw_pixel_frame`, `draw_pixel_panel_bg` |
| `text.py` | `draw_text_clipped`, `draw_text_in_rect`, `ellipsize_text_px`, `wrap_text_px` |

### Layout & geometry

| Module | Responsibility |
|--------|---------------|
| `layout.py` | `Layout` — panel/canvas region calculations, responsive resizing |
| `layout_tools.py` | Alignment (left/center/right/top/bottom), distribution, snap-to-guide |
| `windowing.py` | Window management, zoom/pan, hit-testing |

### Rendering support

| Module | Responsibility |
|--------|---------------|
| `perf.py` | `RenderCache` (LRU surface cache + `frame_cache_key()`), `SmartEventQueue`, `compute_dirty_rects()` |
| `fit_text.py` | Auto-fit text to widget bounds |
| `fit_widget.py` | Auto-size widget to content |
| `text_metrics.py` | Text width/height measurement |
| `font6x8.py` | 6×8 pixel font data (matches firmware font) |

### I/O & persistence

| Module | Responsibility |
|--------|---------------|
| `io_ops.py` | Save/load JSON, autosave detection, widget presets, clipboard I/O |
| `inspector_logic.py` | Property inspector field editing (start/commit/cancel) |
| `inspector_utils.py` | Inspector field helpers (type-safe parsing, validation) |
| `component_fields.py` | Widget property field type definitions |
| `components.py` | Widget component definitions (default sizes, templates) |
| `component_insert.py` | Widget insertion logic (smart positioning) |
| `live_preview.py` | Serial live preview to ESP32 hardware |

---

## Initialization sequence

`CyberpunkEditorApp.__init__` runs 5 phases in order:

1. **`_init_pygame()`** — `pygame.init()`, font subsystem, event filtering
2. **`_init_config(json_path, default_size, profile)`** — `UIDesigner` backend, hardware profile, env vars, file paths, feature flags
3. **`_init_window()`** — display surface, `EventManager`, clock
4. **`_init_fonts_and_metrics()`** — pixel-art font loading, row-height calculation, pointer, sim-input
5. **`_init_state_and_perf()`** — `EditorState`, `RenderCache`, FPS counters

Then `_build_palette()` and `_build_toolbar()` construct the UI panels.

---

## Main loop (`run()`)

```
while running:
    clock.tick(FPS)
    events = SmartEventQueue.process_batch()
    for event in events:
        _handle_events(event)       # → input_handlers.*
    EventManager.dispatch_all()     # fire queued events
    _optimized_draw_frame()         # → drawing/*
    pygame.display.flip()           # (or update dirty rects)
```

### Drawing frame pipeline

`_optimized_draw_frame()`:
1. Compute `frame_cache_key()` — hash of scene state, selection, scroll, mode
2. If cache hit → blit cached surface, return
3. Compute `compute_dirty_rects()` — which regions need redraw
4. Draw layers in order:
   - Canvas background + grid
   - Widget previews (z-order, bottom-to-top)
   - Selection highlights, guides, rulers
   - Panels: palette (left), inspector (right), toolbar (top), scene tabs, status bar (bottom)
   - Overlays: help, context menu, tooltips
5. Store result in `RenderCache`

---

## Key design decisions

- **Standalone functions, not methods** — Input handlers, scene operations, and drawing are free functions that receive the `app` instance, not methods on `CyberpunkEditorApp`. This keeps the class focused on lifecycle and lets modules evolve independently.

- **Dispatch tables for shortcuts** — Keyboard shortcuts use dict-based dispatch tables (`_CTRL_FKEY_TABLE`, `_CTRL_SCENE_JUMP`, etc.) instead of if/elif chains for maintainability.

- **Integer pixel coordinates** — All widget positions and sizes are `int`, never `float`. Coordinates are `round()`-ed before storage to prevent sub-pixel drift.

- **Single undo checkpoint per user action** — One conceptual action (drag, resize, property edit) produces one undo entry, never multiple.

- **Surface caching** — `RenderCache` stores rendered frames keyed by a hash of the visible state. Cache is invalidated automatically when state changes.

- **JSON as source of truth** — `main_scene.json` is the canonical design file. Generated C code (`src/ui_design.c|h`) is never edited manually.

---

## Testing

- **Framework:** pytest with coverage
- **Test location:** `tests/` (Python), `test/` (native C via PlatformIO)
- **Run:** `python -m pytest -q --ignore=output`
- **Lint:** `python -m ruff check .`
- **Type check:** `python -m pyright`
