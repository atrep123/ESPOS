# Contributing

Thanks for helping improve ESP32OS. This project targets Python 3.9–3.12 and runs across Windows, macOS, and Linux.

## Environment setup
- Use a virtualenv: `python -m venv .venv && . .venv/Scripts/activate` (or `source .venv/bin/activate`).
- Install runtime deps: `pip install -r build/requirements.txt`.
- Install dev/test tools: `pip install -r build/requirements-dev.txt` (includes pytest, black, ruff, mypy, pre-commit).
- Optional: `pre-commit install` to run checks automatically on each commit.

## Workflow
- Align work with the roadmap in `docs/PROJECT_ROADMAP.md`; open or reference an issue before large changes.
- Keep PRs focused and include tests/docs for user-facing changes. Add a short summary in the PR body describing scope and validation.
- Avoid committing generated binaries or secrets; prefer environment variables for local credentials.

## Code architecture notes

### Preview module structure (`preview/` package)

The preview system has been refactored from a monolithic 6000+ line file into modular components:

- **`preview/settings.py`**: Configuration dataclass (`PreviewSettings`) with all preview window settings
- **`preview/rendering.py`**: Shared drawing helpers (color conversion, rounded rectangles, widget edge calculation)
- **`preview/animation_editor.py`**: Animation timeline editor window (`AnimationEditorWindow`)
- **`preview/window.py`**: Main preview window class (`VisualPreviewWindow`) - to be extracted from `ui_designer_preview.py`

**Import from new structure:**

```python
from preview import VisualPreviewWindow, PreviewSettings, AnimationEditorWindow
```

Backward compatibility maintained via `ui_designer_preview.py` compatibility shim.

### Preview rendering (`ui_designer_preview.py` / `preview/window.py`)

The preview window draws widgets in several distinct phases (refactored for maintainability):

1. **Geometry computation** (`_compute_widget_geometry`): determines scaled position and dimensions based on zoom and responsive settings.
2. **Color resolution** (`_resolve_widget_colors`): picks theme-aware colors for borders, backgrounds, and text.
3. **Background painting** (`_paint_widget_background`): fills the widget bounding box.
4. **Border painting** (`_paint_widget_border`): draws borders if enabled, accounting for radius and padding.
5. **Content painting** (`_paint_widget_content`): renders widget-specific content (text labels, gauge arcs, slider thumbs, checkbox marks).

Each stage is isolated to reduce complexity and simplify future changes. When extending the preview (e.g., adding a new widget type), add a case in `_paint_widget_content` and reuse existing color/geometry helpers.

### Alignment guides (`ui_designer_preview.py`)

Alignment guide logic is decomposed into:

- `_widget_edges(w)`: extracts left, right, top, bottom, center_x, center_y for a widget.
- `_add_vertical_guides(...)`: compares horizontal (X) alignment of widget edges and appends vertical guide hints.
- `_add_horizontal_guides(...)`: compares vertical (Y) alignment and appends horizontal guide hints.
- `_find_alignment_guides(widget)`: coordinates the search by calling the above helpers.

This split reduces cognitive complexity and facilitates caching or more nuanced threshold logic in the future.

### Event handling (`ui_designer_preview.py`)

Mouse and keyboard events are centralized in class-level constants (`EVT_MOUSE_LEFT`, `EVT_KEY_DELETE`, etc.) for easy discovery and consistent binding. See `_setup_bindings()` for all registered handlers.

## Code style & tooling (configured in `pyproject.toml`)

- Format with `black .` and lint with `ruff check . --fix`.
- Type-check with `mypy .` (imports are ignored by default; tighten types for new code where possible).
- Run `pre-commit run --all-files` to execute the full formatting/lint/type-check stack.
- UI data models live in `ui_models.py`; import shared enums/dataclasses from there instead of redefining them.

## Testing

- Default command: `python -m pytest`. The `pytest` section in `pyproject.toml` mirrors the existing markers and timeouts.
- Fast feedback: `python -m pytest test_ui_designer.py test_ui_designer_pro.py` or `-m "not visual"` when running headless.
- Keep golden artifacts and snapshots in sync when tests cover exports/previews; update docs alongside behavioral changes.

## Documentation

- Update relevant guides in `docs/` when changing UX, shortcuts, exports, or build steps.
- Note significant UI Designer changes in `docs/CHANGELOG_UI_DESIGNER.md` (or add a brief entry to the most relevant changelog).

## Pull request checklist

- [ ] Tests added/updated and passing locally.
- [ ] `black`, `ruff`, and `mypy` run locally or via pre-commit.
- [ ] Docs/changelog updated when behavior or setup changes.
- [ ] Screenshots or recordings attached when altering UI/visual output.
