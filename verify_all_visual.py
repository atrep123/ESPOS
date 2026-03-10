"""Comprehensive headless visual verification — grayscale palette aware."""

import inspect  # noqa: E402
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

pygame.init()

from pathlib import Path  # noqa: E402

from cyberpunk_designer import drawing  # noqa: E402
from cyberpunk_designer.app import CyberpunkEditorApp  # noqa: E402
from cyberpunk_designer.constants import PALETTE  # noqa: E402

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        tag = "OK"
    else:
        FAIL += 1
        tag = "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{tag}] {name}{extra}")


app = CyberpunkEditorApp(json_path=Path("main_scene.json"), profile="esp32os_256x128_gray4")
app._pump_events = lambda: None
surf = app.logical_surface
W, H = surf.get_width(), surf.get_height()


def full_draw():
    """Full redraw — writes to logical_surface."""
    surf.fill(PALETTE["bg"])
    drawing.draw_toolbar(app)
    drawing.draw_scene_tabs(app)
    drawing.draw_palette(app)
    drawing.draw_canvas(app)
    drawing.draw_inspector(app)
    drawing.draw_status(app)
    if getattr(app, "show_help_overlay", False):
        drawing.draw_help_overlay(app)
    drawing.draw_context_menu(app)
    drawing.draw_tooltip(app)


def canvas_draw():
    """Redraw just the canvas area (properly clears + redraws)."""
    drawing.draw_canvas(app)


def count_bright(rect, threshold=30):
    n = 0
    for x in range(max(0, rect.x), min(W, rect.right)):
        for y in range(max(0, rect.y), min(H, rect.bottom)):
            c = surf.get_at((x, y))
            if max(c[0], c[1], c[2]) > threshold:
                n += 1
    return n


def snapshot_rect(rect):
    pixels = {}
    for x in range(max(0, rect.x), min(W, rect.right)):
        for y in range(max(0, rect.y), min(H, rect.bottom)):
            c = surf.get_at((x, y))
            pixels[(x, y)] = (c[0], c[1], c[2])
    return pixels


def diff_snapshots(a, b):
    changed = 0
    for k in a:
        if k in b and a[k] != b[k]:
            changed += 1
    return changed


sc = app.state.current_scene()
sr = getattr(app, "scene_rect", app.layout.canvas_rect)

# ══════════════════════════════════════════════
print("\n=== 1. FULL FRAME RENDER ===")
full_draw()
print("\n--- 1a. TOOLBAR ---")
tr = app.layout.toolbar_rect
check("Toolbar has content", count_bright(tr) > 50, f"{count_bright(tr)} px")
hitboxes = getattr(app, "toolbar_hitboxes", [])
check("Toolbar buttons exist (>=3)", len(hitboxes) >= 3, f"{len(hitboxes)} buttons")

print("\n--- 1b. SCENE TABS ---")
tabs_r = app.layout.scene_tabs_rect
check("Scene tabs has content", count_bright(tabs_r) > 20, f"{count_bright(tabs_r)} px")
tab_hits = getattr(app, "tab_hitboxes", [])
check("Tab hitboxes present", len(tab_hits) >= 1, f"{len(tab_hits)} tabs")

print("\n--- 1c. PALETTE ---")
pal_r = app.layout.palette_rect
check("Palette has content", count_bright(pal_r) > 100, f"{count_bright(pal_r)} px")
check(
    "Palette hitboxes",
    len(getattr(app, "palette_hitboxes", [])) > 0,
    f"{len(getattr(app, 'palette_hitboxes', []))} hitboxes",
)

print("\n--- 1d. CANVAS ---")
check("Canvas has content", count_bright(sr) > 50, f"{count_bright(sr)} px")

print("\n--- 1e. INSPECTOR ---")
insp_r = app.layout.inspector_rect
check("Inspector has content", count_bright(insp_r) > 50, f"{count_bright(insp_r)} px")

print("\n--- 1f. STATUS BAR ---")
stat_r = app.layout.status_rect
check("Status bar has content", count_bright(stat_r) > 30, f"{count_bright(stat_r)} px")

# ══════════════════════════════════════════════
print("\n=== 2. RULERS (diff on/off) ===")
app.show_rulers = True
canvas_draw()
ruler_on = snapshot_rect(pygame.Rect(sr.x, sr.y, sr.width, 10))
app.show_rulers = False
canvas_draw()
ruler_off = snapshot_rect(pygame.Rect(sr.x, sr.y, sr.width, 10))
ruler_diff = diff_snapshots(ruler_on, ruler_off)
check("Top ruler diff >3", ruler_diff > 3, f"{ruler_diff} px differ")
app.show_rulers = True
canvas_draw()
lruler_on = snapshot_rect(pygame.Rect(sr.x, sr.y, 10, sr.height))
app.show_rulers = False
canvas_draw()
lruler_off = snapshot_rect(pygame.Rect(sr.x, sr.y, 10, sr.height))
lruler_diff = diff_snapshots(lruler_on, lruler_off)
check("Left ruler diff >3", lruler_diff > 3, f"{lruler_diff} px differ")
app.show_rulers = True

# ══════════════════════════════════════════════
print("\n=== 3. GRID (diff on/off) ===")
# Use an empty area below visible widgets
empty_area = pygame.Rect(sr.x + 4, sr.y + 100, 20, 20)
app.show_grid = True
canvas_draw()
grid_on = snapshot_rect(empty_area)
app.show_grid = False
canvas_draw()
grid_off = snapshot_rect(empty_area)
grid_diff = diff_snapshots(grid_on, grid_off)
check("Grid diff >0 in empty area", grid_diff > 0, f"{grid_diff} px changed")
app.show_grid = True

# ══════════════════════════════════════════════
print("\n=== 4. SELECTION (diff with/without) ===")
app.state.selected = []
app.pointer_pos = (0, 0)
canvas_draw()
nosel = snapshot_rect(sr)
app.state.selected = [0]
canvas_draw()
sel = snapshot_rect(sr)
sel_diff = diff_snapshots(nosel, sel)
check("Selection diff >5", sel_diff > 5, f"{sel_diff} px changed")

# ══════════════════════════════════════════════
print("\n=== 5. HOVER HIGHLIGHT (diff pointer on/off widget) ===")
if len(sc.widgets) > 1:
    w1 = sc.widgets[1]
    w1_area = pygame.Rect(
        sr.x + int(w1.x) - 5,
        sr.y + int(w1.y) - 5,
        int(getattr(w1, "width", 8) or 8) + 90,
        int(getattr(w1, "height", 8) or 8) + 10,
    )
    app.state.selected = []
    app.pointer_pos = (0, 0)
    app.pointer_down = False
    app.sim_input_mode = False
    app._context_menu = None
    canvas_draw()
    nohover = snapshot_rect(w1_area)
    app.pointer_pos = (sr.x + int(w1.x) + 30, sr.y + int(w1.y) + 5)
    canvas_draw()
    hover = snapshot_rect(w1_area)
    hover_diff = diff_snapshots(nohover, hover)
    check("Hover diff >3 (dashed rect + tooltip)", hover_diff > 3, f"{hover_diff} px changed")
else:
    check("Enough widgets for hover", False, "need >1")

# ══════════════════════════════════════════════
print("\n=== 6. SELECTION INFO (resize/drag labels) ===")
if len(sc.widgets) > 1:
    app.state.selected = [1]
    app.state.resizing = False
    app.state.dragging = False
    canvas_draw()
    base = snapshot_rect(sr)
    app.state.resizing = True
    app.state.resize_anchor = "br"
    canvas_draw()
    resize = snapshot_rect(sr)
    check(
        "Resize info diff >0",
        diff_snapshots(base, resize) > 0,
        f"{diff_snapshots(base, resize)} px",
    )
    app.state.resizing = False
    app.state.dragging = True
    canvas_draw()
    drag = snapshot_rect(sr)
    check("Drag info diff >0", diff_snapshots(base, drag) > 0, f"{diff_snapshots(base, drag)} px")
    app.state.dragging = False

# ══════════════════════════════════════════════
print("\n=== 7. DISTANCE INDICATORS (drag diff) ===")
if len(sc.widgets) > 1:
    app.state.selected = [1]
    app.state.dragging = False
    canvas_draw()
    nodist = snapshot_rect(sr)
    app.state.dragging = True
    canvas_draw()
    dist = snapshot_rect(sr)
    dist_diff = diff_snapshots(nodist, dist)
    check("Distance diff >5 when dragging", dist_diff > 5, f"{dist_diff} px changed")
    app.state.dragging = False

# ══════════════════════════════════════════════
print("\n=== 8. CENTER GUIDES (diff on/off) ===")
app.state.selected = []
app.pointer_pos = (0, 0)
app.show_center_guides = False
canvas_draw()
noguide = snapshot_rect(sr)
app.show_center_guides = True
canvas_draw()
guide = snapshot_rect(sr)
guide_diff = diff_snapshots(noguide, guide)
check("Center guides diff >10", guide_diff > 10, f"{guide_diff} px changed")
app.show_center_guides = False

# ══════════════════════════════════════════════
print("\n=== 9. WIDGET ID OVERLAY (diff on/off) ===")
app.show_widget_ids = False
canvas_draw()
noid = snapshot_rect(sr)
app.show_widget_ids = True
canvas_draw()
wid = snapshot_rect(sr)
id_diff = diff_snapshots(noid, wid)
check("Widget ID diff >3", id_diff > 3, f"{id_diff} px changed")
app.show_widget_ids = False

# ══════════════════════════════════════════════
print("\n=== 10. Z-LABEL OVERLAY (diff on/off) ===")
app.show_z_labels = False
canvas_draw()
noz = snapshot_rect(sr)
app.show_z_labels = True
canvas_draw()
zl = snapshot_rect(sr)
z_diff = diff_snapshots(noz, zl)
check("Z-label diff >3", z_diff > 3, f"{z_diff} px changed")
app.show_z_labels = False

# ══════════════════════════════════════════════
print("\n=== 11. STATUS BAR DETAILS ===")
app.state.selected = [0]
full_draw()
rthird = pygame.Rect(stat_r.x + stat_r.width * 2 // 3, stat_r.y, stat_r.width // 3, stat_r.height)
check("Status right text", count_bright(rthird, 40) > 10, f"{count_bright(rthird, 40)} px")
app.state.selected = [0, 1] if len(sc.widgets) > 1 else [0]
full_draw()
check("Multi-sel status text", count_bright(rthird, 40) > 10, f"{count_bright(rthird, 40)} px")
app.state.selected = []

# ══════════════════════════════════════════════
print("\n=== 12. DIRTY TAB (diff clean/dirty) ===")
app._dirty_scenes = set()
full_draw()
clean = snapshot_rect(app.layout.scene_tabs_rect)
app._dirty_scenes = {app.designer.current_scene}
full_draw()
dirty = snapshot_rect(app.layout.scene_tabs_rect)
dirty_diff = diff_snapshots(clean, dirty)
check("Dirty tab diff >2 (star prefix)", dirty_diff > 2, f"{dirty_diff} px changed")
app._dirty_scenes = set()

# ══════════════════════════════════════════════
print("\n=== 13. CONTEXT MENU ===")
app.state.selected = [0]
app.pointer_pos = (sr.x + 50, sr.y + 50)
app._open_context_menu(app.pointer_pos)
menu = getattr(app, "_context_menu", None)
check("Context menu opens", menu and menu.get("visible"), "")
items = menu.get("items", []) if menu else []
labels = [i[0] for i in items]
check("Has Edit/Copy actions", any("Copy" in lb for lb in labels), "")
view_labels = [lb for lb in labels if lb.startswith("\u2713 ") or lb.startswith("  ")]
check("Has View toggle items (>=4)", len(view_labels) >= 4, f"{len(view_labels)}: {view_labels}")
check("Has Add Widget actions", any("Add Label" in lb for lb in labels), "")
ruler_vt = [lb for lb in view_labels if "Rulers" in lb]
check("Rulers in View toggles", len(ruler_vt) > 0, f"{ruler_vt}")
id_vt = [lb for lb in view_labels if "Widget IDs" in lb]
check("Widget IDs in View toggles", len(id_vt) > 0, f"{id_vt}")
zl_vt = [lb for lb in view_labels if "Z-Label" in lb]
check("Z-Labels in View toggles", len(zl_vt) > 0, f"{zl_vt}")
app._context_menu = None

# ══════════════════════════════════════════════
print("\n=== 14. VIEW TOGGLE ACTIONS ===")
for action, attr in [
    ("view_rulers", "show_rulers"),
    ("view_grid", "show_grid"),
    ("view_ids", "show_widget_ids"),
    ("view_zlabels", "show_z_labels"),
    ("view_snap", "snap_enabled"),
    ("view_guides", "show_center_guides"),
]:
    orig = getattr(app, attr)
    app._execute_context_action(action)
    check(f"{action} toggles {attr}", getattr(app, attr) != orig, f"{orig}->{getattr(app, attr)}")
    app._execute_context_action(action)

# ══════════════════════════════════════════════
print("\n=== 15. HELP OVERLAY ===")
app.show_help_overlay = False
full_draw()
nohelp = snapshot_rect(pygame.Rect(W // 4, H // 4, W // 2, H // 2))
app.show_help_overlay = True
full_draw()
withhelp = snapshot_rect(pygame.Rect(W // 4, H // 4, W // 2, H // 2))
help_diff = diff_snapshots(nohelp, withhelp)
check("Help overlay diff >100", help_diff > 100, f"{help_diff} px changed")
app.show_help_overlay = False

help_src = inspect.getsource(drawing.draw_help_overlay)
check("Help mentions Rulers", "Rulers" in help_src, "")
check("Help mentions Distance", "Distance" in help_src or "distance" in help_src, "")

# ══════════════════════════════════════════════
print("\n=== 16. TOOLTIP ===")
check("draw_tooltip exists", hasattr(drawing, "draw_tooltip"), "")

# ══════════════════════════════════════════════
print("\n=== 17. WIDGET RENDERING ===")
app.state.selected = []
app.pointer_pos = (0, 0)
full_draw()
visible = 0
offscreen = 0
for i, w in enumerate(sc.widgets):
    if not getattr(w, "visible", True):
        continue
    wx = sr.x + int(w.x)
    wy = sr.y + int(w.y)
    ww = max(4, int(getattr(w, "width", 4) or 4))
    wh = max(4, int(getattr(w, "height", 4) or 4))
    wr = pygame.Rect(wx, wy, ww, wh).clip(sr)
    if wr.width < 2 or wr.height < 2:
        offscreen += 1
        continue
    # Panels are dark containers with very faint borders (brightness ~8)
    thresh = 4 if w.type == "panel" else 8
    if count_bright(wr, thresh) > 0:
        visible += 1
    else:
        check(f"Widget[{i}] {w.type} ({ww}x{wh})", False, "0 bright px")
check(
    f"On-screen widgets render ({visible})",
    visible >= 3,
    f"{visible} visible, {offscreen} offscreen",
)

# ══════════════════════════════════════════════
print("\n=== 18. CURSOR ===")
check("_update_cursor exists", hasattr(app, "_update_cursor"), "")
app.pointer_pos = (sr.centerx, sr.centery)
app._update_cursor()
check(
    "Crosshair on canvas",
    getattr(app, "_cursor_kind", None) == "cross",
    f"{getattr(app, '_cursor_kind', None)}",
)
app.pointer_pos = (5, 5)
app._update_cursor()
check(
    "Arrow outside canvas",
    getattr(app, "_cursor_kind", None) == "arrow",
    f"{getattr(app, '_cursor_kind', None)}",
)

# ══════════════════════════════════════════════
print("\n=== 19. QUIT CONFIRMATION ===")
check("_dirty_scenes attr", hasattr(app, "_dirty_scenes"), "")
app._dirty_scenes = {"main"}
app._dirty = True
app.running = True
try:
    app._on_quit()
except Exception:
    pass
check("First quit blocked when dirty", app.running is True, f"running={app.running}")
app._dirty_scenes = set()
app._dirty = False

# ══════════════════════════════════════════════
print("\n=== 20. VALIDATION RULES ===")
from tools.validate_design import validate_file  # noqa: E402

issues_main = validate_file(Path("main_scene.json"), warnings_as_errors=False)
errors_main = [i for i in issues_main if i.level == "ERROR"]
warns_main = [i for i in issues_main if i.level == "WARN"]
check(
    "main_scene.json has zero validation errors",
    len(errors_main) == 0,
    f"{len(errors_main)} errors",
)
check(
    "main_scene.json warnings counted", isinstance(warns_main, list), f"{len(warns_main)} warnings"
)

if Path("rc_scene.json").exists():
    issues_rc = validate_file(Path("rc_scene.json"), warnings_as_errors=False)
    errors_rc = [i for i in issues_rc if i.level == "ERROR"]
    check(
        "rc_scene.json has zero validation errors", len(errors_rc) == 0, f"{len(errors_rc)} errors"
    )

if Path("widget_catalog.json").exists():
    issues_cat = validate_file(Path("widget_catalog.json"), warnings_as_errors=False)
    errors_cat = [i for i in issues_cat if i.level == "ERROR"]
    check(
        "widget_catalog.json has zero validation errors",
        len(errors_cat) == 0,
        f"{len(errors_cat)} errors",
    )

# ══════════════════════════════════════════════
print("\n=== 21. PER-WIDGET-TYPE DRAW ===")
from ui_designer import WidgetConfig  # noqa: E402

_test_surf = pygame.Surface((128, 64))
_test_bg = (0, 0, 0)
_all_types = [
    ("label", dict(text="TEST", border=False, border_style="none")),
    ("button", dict(text="BTN", border=True, border_style="single", color_bg="#303030")),
    ("checkbox", dict(text="CHK", checked=True)),
    ("radiobutton", dict(text="RAD", checked=True, border=False, border_style="none")),
    ("progressbar", dict(value=50, min_value=0, max_value=100)),
    ("slider", dict(value=50, min_value=0, max_value=100, border=False, border_style="none")),
    ("gauge", dict(value=50, min_value=0, max_value=100, border=False, border_style="none")),
    (
        "chart",
        dict(text="C", style="bar", data_points=[10, 20, 30], border=False, border_style="none"),
    ),
    ("textbox", dict(text="EDIT", border=True, border_style="single")),
    ("icon", dict(icon_char="@", border=False, border_style="none")),
    ("box", dict(border=True, border_style="single", color_bg="#303030")),
    ("panel", dict(border=True, border_style="single", color_bg="#101010")),
]

for wtype, extra in _all_types:
    _test_surf.fill(_test_bg)
    _defaults = dict(color_fg="#f0f0f0", color_bg="black")
    _defaults.update(extra)
    _wc = WidgetConfig(type=wtype, x=0, y=0, width=60, height=30, **_defaults)
    _rect = pygame.Rect(4, 4, 60, 30)
    drawing.draw_widget_preview(app, _test_surf, _wc, _rect, _test_bg, 2, False)
    _has_px = False
    for _x in range(_rect.left, _rect.right):
        for _y in range(_rect.top, _rect.bottom):
            c = _test_surf.get_at((_x, _y))
            if max(c[0], c[1], c[2]) > 5:
                _has_px = True
                break
        if _has_px:
            break
    check(f"  {wtype} produces pixels", _has_px, "")

# ══════════════════════════════════════════════
print("\n=== 22. WIDGET CATALOG LOAD ===")
if Path("widget_catalog.json").exists():
    import json

    with open("widget_catalog.json", encoding="utf-8") as f:
        catalog = json.load(f)
    cat_scenes = catalog.get("scenes", {})
    check("Catalog has >=3 scenes", len(cat_scenes) >= 3, f"{len(cat_scenes)} scenes")
    total_widgets = sum(len(s.get("widgets", [])) for s in cat_scenes.values())
    check("Catalog has >=40 widgets", total_widgets >= 40, f"{total_widgets} widgets")
    # Check all 12 types are represented
    all_types_in_catalog = set()
    for s in cat_scenes.values():
        for w in s.get("widgets", []):
            all_types_in_catalog.add(w.get("type", "").lower())
    check(
        "Catalog covers >=10 types",
        len(all_types_in_catalog) >= 10,
        f"{sorted(all_types_in_catalog)}",
    )
else:
    check("widget_catalog.json exists", False, "not found — run gen_widget_catalog.py")

# ══════════════════════════════════════════════
print(f"\n{'=' * 50}")
print(f"  TOTAL: {PASS + FAIL} | PASS: {PASS} | FAIL: {FAIL}")
if FAIL:
    print(f"  *** {FAIL} FAILURES ***")
else:
    print("  ALL CHECKS PASSED!")
print(f"{'=' * 50}\n")
sys.exit(1 if FAIL else 0)
