"""
CLI interface for ESP32 UI Designer.
Extracted from ui_designer.py — provides the interactive command loop,
command help, widget help, and WCAG contrast utilities.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ui_models import SceneConfig, WidgetConfig, WidgetType

# MSG_* constants duplicated here to avoid circular import with ui_designer.
MSG_INVALID_INDEX = "Invalid index"
MSG_NO_SCENE = "No scene loaded"
MSG_INDEX_INTEGER = "Index must be integer"
MSG_FAILED = "Failed"
MSG_UNKNOWN_ANIM = "Unknown animation name"


def create_cli_interface(
    commands: Optional[List[str]] = None,
):
    """Advanced CLI interface for UI designer.

    If 'commands' is provided, runs non-interactively executing each command in order.

    Security: *commands* must come from a trusted source (e.g. hardcoded list or
    a file the operator controls).  Do NOT pass unsanitized external input.
    """
    from ui_designer import UIDesigner  # lazy import to avoid circular dependency

    designer = UIDesigner(128, 64)

    print("=============================================================")
    print("   ESP32 UI Designer - Advanced CLI Mode")
    print("=============================================================")
    print()
    print("Scene Management:")
    print("  new <name>              - Create new scene")
    print("  list                    - List widgets in current scene")
    print("  scenes                  - List all scenes")
    print("  switch <name>           - Switch to scene")
    print()
    print("Widget Operations:")
    print("  add <type> <x> <y> <w> <h> [text]    - Add widget")
    print("  template <name> <x> <y>              - Add from template")
    print("  clone <idx> [offset_x] [offset_y]    - Clone widget")
    print("  duplicate <idx> [dx] [dy]            - Alias for clone")
    print("  move <idx> <dx> <dy>                 - Move widget")
    print("  resize <idx> <dw> <dh>               - Resize widget")
    print("  delete <idx>                         - Delete widget")
    print("  lock <idx> <on|off|toggle>           - Toggle edit lock")
    print("  select <idx>                         - Select widget for context")
    print("  edit <idx> <prop> <value>            - Edit property")
    print()
    print("Advanced Features:")
    print("  undo                    - Undo last operation")
    print("  redo                    - Redo operation")
    print("  grid <on|off>           - Toggle grid")
    print("  snap <on|off>           - Toggle snap to grid")
    print("  guides <on|off>         - Toggle guide overlay in preview")
    print("  snaptol <px>            - Set magnetic snapping tolerance (px)")
    print("  snapmode <pixel|fluid>  - Pixel uses grid; fluid favors magnets")
    print("  preview [grid]          - Show ASCII preview")
    print("  templates               - List available templates")
    print("  layout <type>           - Auto-layout (vertical/horizontal/grid)")
    print("  align <type> <ids...>   - Align widgets (left/right/top/bottom/center_h/center_v)")
    print("  distribute <dir> <ids...> - Distribute evenly (horizontal/vertical)")
    print("  tree                    - Show group membership and widget hierarchy")
    print("  gridcols <4|8|12>       - Set grid columns and recompute grid size")
    print("  bp <WxH>                - Set breakpoint (scene size), e.g. 128x64")
    print("  resp base               - Record current as responsive base")
    print("  resp apply              - Apply constraints to current size")
    print("  state define <idx> <name> k=v [k=v]...  - Define/merge state overrides")
    print("  state set <idx> <name>                  - Switch current state")
    print("  state list <idx>                        - List states")
    print("  state clear <idx> <name>                - Remove a state override")
    print("  anim list                               - Show built-in animations")
    print("  anim add <idx> <name>                   - Attach an animation tag to widget")
    print("  anim clear <idx> <name>                 - Remove animation tag from widget")
    print("  anim preview <idx> <name> <steps> <t>   - Preview a single animation frame")
    print("  anim play <idx> <name> <steps> [delay]  - Play animation frames (delay ms)")
    print("  context [idx]           - Show contextual help and quick actions")
    print()
    print("File Operations:")
    print("  save <file>             - Save to JSON")
    print("  load <file>             - Load from JSON")
    print("  export <file>           - Export Python code")
    print("  restore [latest|list|<index>] - Restore from autosave snapshot")
    print("  checkpoint <name>       - Create a named checkpoint of current scene")
    print("  checkpoints             - List named checkpoints")
    print("  rollback <name>         - Restore the scene from a checkpoint")
    print("  diff <A> [B]            - Diff checkpoints A and B (or A vs current)")
    print()
    print("Groups:")
    print("  group create <name> <idx...>   - Create a group")
    print("  group add <name> <idx...>      - Add widgets to group")
    print("  group remove <name> <idx...>   - Remove widgets from group")
    print("  group delete <name>            - Delete a group")
    print("  group list                     - List groups")
    print("  group lock <name> <on|off|toggle>    - Lock/unlock all members")
    print("  group visible <name> <on|off|toggle> - Show/hide all members")
    print()
    print("Symbols:")
    print("  symbol save <name> <idx...>    - Save selection as a symbol")
    print("  symbol list                    - List saved symbols")
    print("  symbol place <name> <x> <y>    - Place a symbol instance")
    print()
    print("Themes & WCAG:")
    print("  theme list                    - List theme presets")
    print("  theme set <name>              - Set scene theme and bg color")
    print("  theme bind <idx> <fg|bg> <role> - Bind widget color to role")
    print("  theme apply                   - Apply bound theme roles to widgets")
    print("  contrast [min]                - Audit contrast (optionally set min, e.g., 4.5)")
    print()
    print("Help & Info:")
    print("  help [command]          - Show help")
    print("  widgets                 - List available widget types")
    print("  quit                    - Exit")
    print()
    print("Widget types: label, box, button, gauge, progressbar,")
    print("   checkbox, radiobutton, slider, textbox, panel, icon, chart")
    print()

    cmd_queue: Optional[List[str]] = list(commands) if commands is not None else None
    while True:
        try:
            if cmd_queue is not None:
                if not cmd_queue:
                    break
                cmd = cmd_queue.pop(0).strip()
                # Echo command to output for clarity in scripted runs
                if cmd:
                    print(f"> {cmd}")
            else:
                cmd = input("> ").strip()
            if not cmd:
                continue

            # Split command preserving quotes
            import shlex

            try:
                parts = shlex.split(cmd)
            except ValueError:
                parts = cmd.split()

            if not parts:
                continue

            action = parts[0].lower()

            # Scene Management
            if action == "quit" or action == "exit":
                break

            elif action == "new":
                if len(parts) < 2:
                    print("Usage: new <scene_name>")
                    continue
                designer.create_scene(parts[1])
                print(f"[OK] Created scene: {parts[1]}")

            elif action == "scenes":
                if designer.scenes:
                    print("\nList Available scenes:")
                    for name in designer.scenes:
                        marker = " (current)" if name == designer.current_scene else ""
                        print(f"  - {name}{marker}")
                else:
                    print("No scenes created")

            elif action == "switch":
                if len(parts) < 2:
                    print("Usage: switch <scene_name>")
                    continue
                if parts[1] in designer.scenes:
                    designer.current_scene = parts[1]
                    print(f"[OK] Switched to scene: {parts[1]}")
                else:
                    print(f"[FAIL] Scene '{parts[1]}' not found")

            # Widget Operations
            elif action == "add":
                if len(parts) < 6:
                    print("Usage: add <type> <x> <y> <w> <h> [text]")
                    continue

                _text = " ".join(parts[6:]) if len(parts) > 6 else ""
                if "_" in _text and " " not in _text:
                    _text = _text.replace("_", " ")
                    print(
                        '[TIP] Converted underscore placeholders to spaces. Use quotes for exact text: add ... "Sharp LCD Demo"'
                    )

                widget = WidgetConfig(
                    type=parts[1],
                    x=int(parts[2]),
                    y=int(parts[3]),
                    width=int(parts[4]),
                    height=int(parts[5]),
                    text=_text,
                )
                designer.add_widget(widget)
                print(f"[OK] Added {widget.type} widget")

            elif action == "template":
                if len(parts) < 5:
                    print("Usage: template <name> <id> <x> <y>")
                    continue
                designer.add_widget_from_template(parts[1], parts[2], int(parts[3]), int(parts[4]))
                print(f"[OK] Added widget '{parts[2]}' from template: {parts[1]}")

            elif action == "clone":
                if len(parts) < 2:
                    print("Usage: clone <idx> [offset_x] [offset_y]")
                    continue
                offset_x = int(parts[2]) if len(parts) > 2 else 10
                offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), offset_x, offset_y)
                print("[OK] Widget cloned")

            elif action == "duplicate":
                if len(parts) < 2:
                    print("Usage: duplicate <idx> [dx] [dy]")
                    continue
                _offset_x = int(parts[2]) if len(parts) > 2 else 10
                _offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), _offset_x, _offset_y)
                print("[OK] Widget duplicated")

            elif action == "move":
                if len(parts) < 4:
                    print("Usage: move <idx> <dx> <dy>")
                    continue
                designer.move_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("[OK] Widget moved")

            elif action == "resize":
                if len(parts) < 4:
                    print("Usage: resize <idx> <dw> <dh>")
                    continue
                designer.resize_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("[OK] Widget resized")

            elif action == "delete":
                if len(parts) < 2:
                    print("Usage: delete <idx>")
                    continue
                designer.delete_widget(int(parts[1]))
                print("[OK] Widget deleted")

            elif action == "lock":
                if len(parts) < 3:
                    print("Usage: lock <idx> <on|off|toggle>")
                    continue
                _idx = int(parts[1])
                _mode = parts[2].lower()
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        if _mode == "on":
                            scene.widgets[_idx].locked = True
                        elif _mode == "off":
                            scene.widgets[_idx].locked = False
                        elif _mode == "toggle":
                            scene.widgets[_idx].locked = not scene.widgets[_idx].locked
                        else:
                            print("Usage: lock <idx> <on|off|toggle>")
                            continue
                        state = "[LOCK]" if scene.widgets[_idx].locked else "[UNLOCK]"
                        print(f"[OK] Widget {_idx} {state}")

            elif action == "select":
                if len(parts) < 2:
                    print("Usage: select <idx>")
                    continue
                try:
                    _idx = int(parts[1])
                except Exception:
                    print("Usage: select <idx>")
                    continue
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        designer.selected_widget = _idx
                        print(f"[OK] Selected widget [{_idx}] {scene.widgets[_idx].type}")
                    else:
                        print(MSG_INVALID_INDEX)

            elif action == "edit":
                if len(parts) < 4:
                    print("Usage: edit <idx> <property> <value>")
                    continue
                _idx = int(parts[1])
                _prop = parts[2]
                _value = " ".join(parts[3:])
                if _prop == "text" and "_" in _value and " " not in _value:
                    _value = _value.replace("_", " ")
                    print(
                        '[TIP] Converted underscore placeholders to spaces. Use quotes for exact text: edit <idx> text "Sharp LCD Demo"'
                    )

                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        # Save state before edit
                        from dataclasses import asdict

                        _state = json.dumps(asdict(scene))
                        designer.undo_stack.append(_state)
                        designer.redo_stack.clear()

                        widget = scene.widgets[_idx]

                        # Set property
                        if _prop in [
                            "x",
                            "y",
                            "width",
                            "height",
                            "value",
                            "min_value",
                            "max_value",
                            "z_index",
                        ]:
                            setattr(widget, _prop, int(_value))
                        elif _prop in ["checked", "enabled", "visible", "border"]:
                            setattr(widget, _prop, _value.lower() in ["true", "1", "yes"])
                        else:
                            setattr(widget, _prop, _value)

                        print(f"[OK] Updated {_prop} = {_value}")

            # Advanced Features
            elif action == "undo":
                if designer.undo():
                    print("[OK] Undone")
                else:
                    print("[FAIL] Nothing to undo")

            elif action == "redo":
                if designer.redo():
                    print("[OK] Redone")
                else:
                    print("[FAIL] Nothing to redo")

            elif action == "grid":
                if len(parts) < 2:
                    print(f"Grid is {'enabled' if designer.grid_enabled else 'disabled'}")
                elif parts[1].lower() in ["on", "true", "1"]:
                    designer.grid_enabled = True
                    print("[OK] Grid enabled")
                else:
                    designer.grid_enabled = False
                    print("[OK] Grid disabled")

            elif action == "snap":
                if len(parts) < 2:
                    print(f"Snap to grid is {'enabled' if designer.snap_to_grid else 'disabled'}")
                elif parts[1].lower() in ["on", "true", "1"]:
                    designer.snap_to_grid = True
                    print("[OK] Snap to grid enabled")
                else:
                    designer.snap_to_grid = False
                    print("[OK] Snap to grid disabled")

            elif action == "guides":
                if len(parts) < 2:
                    print(f"Guides overlay is {'on' if designer.show_guides else 'off'}")
                elif parts[1].lower() in ["on", "true", "1"]:
                    designer.show_guides = True
                    print("[OK] Guides enabled")
                else:
                    designer.show_guides = False
                    print("[OK] Guides disabled")

            elif action == "snaptol":
                if len(parts) < 2:
                    print(f"Snap tolerance: {designer.snap_tolerance} px")
                else:
                    try:
                        designer.snap_tolerance = max(0, int(parts[1]))
                        print(f"[OK] Snap tolerance set to {designer.snap_tolerance} px")
                    except Exception:
                        print("Usage: snaptol <pixels>")

            elif action == "snapmode":
                if len(parts) < 2:
                    mode = "fluid" if designer.snap_fluid else "pixel"
                    print(f"Snap mode: {mode}")
                else:
                    val = parts[1].lower()
                    if val in ["pixel", "strict"]:
                        designer.snap_fluid = False
                        print("[OK] Snap mode: pixel (grid-first)")
                    elif val in ["fluid", "magnetic"]:
                        designer.snap_fluid = True
                        print("[OK] Snap mode: fluid (magnetic-first)")
                    else:
                        print("Usage: snapmode <pixel|fluid>")

            elif action == "list":
                if designer.current_scene:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\nList Scene: {scene.name} ({scene.width}x{scene.height})")
                    print(f"Widgets: {len(scene.widgets)}\n")
                    for i, w in enumerate(scene.widgets):
                        border_info = f" border={w.border_style}" if w.border else ""
                        value_info = (
                            f" value={w.value}"
                            if w.type in ["gauge", "progressbar", "slider"]
                            else ""
                        )
                        lock_info = " [LOCK]" if getattr(w, "locked", False) else ""
                        print(
                            f"  [{i}] {w.type:12s} pos=({w.x:3d},{w.y:3d}) size={w.width:3d}x{w.height:3d}{border_info}{value_info}{lock_info}"
                        )
                        if w.text:
                            print(f"       text='{w.text}'")
                else:
                    print(MSG_NO_SCENE)

            elif action == "preview":
                show_grid = len(parts) > 1 and parts[1].lower() == "grid"
                print("\n" + designer.preview_ascii(show_grid=show_grid))
                print()

            elif action == "templates":
                print("\nTemplates Available templates:")
                for name, template in designer.templates.items():
                    print(f"  {name:20s} - {template.type} {template.width}x{template.height}")
                print()

            elif action == "widgets":
                print("\nDesign Available widget types:")
                for wtype in WidgetType:
                    print(f"  - {wtype.value}")
                print()

            # Theme & WCAG
            elif action == "theme":
                if len(parts) < 2:
                    print("Usage: theme <list|set|bind|apply> ...")
                    continue
                sub = parts[1].lower()
                if sub == "list":
                    print("\nDesign Themes:")
                    for name, roles in sorted(designer.themes.items()):
                        print(
                            f"  - {name:8s} bg={roles.get('bg')} text={roles.get('text')} primary={roles.get('primary')}"
                        )
                    print()
                elif sub == "set":
                    if len(parts) < 3:
                        print("Usage: theme set <name>")
                        continue
                    name = parts[2]
                    if name not in designer.themes:
                        print("Unknown theme name")
                        continue
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        sc = designer.scenes[designer.current_scene]
                        sc.theme = name
                        sc.bg_color = designer.themes[name].get("bg", sc.bg_color)
                        print(f"[OK] Theme set: {name}")
                elif sub == "bind":
                    if len(parts) < 5:
                        print("Usage: theme bind <idx> <fg|bg> <role>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _which = parts[3].lower()
                    _role = parts[4]
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        if 0 <= _idx < len(_sc.widgets):
                            if _which == "fg":
                                _sc.widgets[_idx].theme_fg_role = _role
                            elif _which == "bg":
                                _sc.widgets[_idx].theme_bg_role = _role
                            else:
                                print("Use fg or bg")
                                continue
                            print("[OK] Theme role bound")
                elif sub == "apply":
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        _roles = designer.themes.get(_sc.theme, designer.themes["default"])
                        for _w in _sc.widgets:
                            if _w.theme_fg_role:
                                _w.color_fg = _roles.get(_w.theme_fg_role, _w.color_fg)
                            if _w.theme_bg_role:
                                _w.color_bg = _roles.get(_w.theme_bg_role, _w.color_bg)
                        # Apply bg to preview HTML via scene.bg_color; ASCII unaffected
                        print("[OK] Theme applied to bound widgets")
                else:
                    print("Unknown theme subcommand")

            elif action == "contrast":
                if designer.current_scene and designer.current_scene in designer.scenes:
                    _sc = designer.scenes[designer.current_scene]
                    if len(parts) > 1:
                        try:
                            designer.theme_contrast_min = float(parts[1])
                        except Exception:
                            pass
                    _min_ratio = designer.theme_contrast_min
                    _issues = 0
                    for _i, _w in enumerate(_sc.widgets):
                        if getattr(_w, "visible", True) and (
                            _w.text
                            or _w.type in ["label", "button", "textbox", "checkbox", "radiobutton"]
                        ):
                            _r = _contrast_ratio(_w.color_fg, _w.color_bg)
                            if _r < _min_ratio:
                                _issues += 1
                                print(
                                    f"  [low] [{_i}] {_w.type}: contrast={_r:.2f} (fg={_w.color_fg}, bg={_w.color_bg})"
                                )
                                if _sc.contrast_lock:
                                    # Try swapping to scene theme text color for better contrast
                                    _roles = designer.themes.get(
                                        _sc.theme, designer.themes["default"]
                                    )
                                    _candidate = _roles.get("text", _w.color_fg)
                                    if _contrast_ratio(_candidate, _w.color_bg) >= _min_ratio:
                                        _w.color_fg = _candidate
                                        print(f"       -> adjusted fg to {_candidate}")
                    if _issues == 0:
                        print(f"[OK] All text meets contrast >= {_min_ratio}")
                    else:
                        print(f"[WARN] {_issues} items below contrast {_min_ratio}")

            elif action == "tree":
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\nTree Tree for scene: {scene.name}")
                    if designer.groups:
                        print("\nGroups:")
                        for gname, members in designer.list_groups():
                            mem_str = ", ".join(str(i) for i in members)
                            print(f"  - {gname}: [{mem_str}]")
                        print()
                    else:
                        print("(no groups)")
                    print("\nWidgets:")
                    for i, w in enumerate(scene.widgets):
                        tags = []
                        for gname, mem in designer.groups.items():
                            if i in mem:
                                tags.append(gname)
                        tag_str = f" groups={','.join(tags)}" if tags else ""
                        lock_info = " [LOCK]" if getattr(w, "locked", False) else ""
                        vis_info = " (hidden)" if not getattr(w, "visible", True) else ""
                        print(
                            f"  [{i}] {w.type} at ({w.x},{w.y}) {w.width}x{w.height}{tag_str}{lock_info}{vis_info}"
                        )
                    print()
                else:
                    print(MSG_NO_SCENE)

            # File Operations
            elif action == "save":
                if len(parts) < 2:
                    print("Usage: save <file>")
                    continue
                designer.save_to_json(parts[1])
                # Note: save_to_json already triggers preflight/auto-export by default

            elif action == "load":
                if len(parts) < 2:
                    print("Usage: load <file>")
                    continue
                designer.load_from_json(parts[1])
            elif action == "restore":
                # Autosave restore utility
                backup_dir = Path.home() / ".esp32os" / "designer_backups"
                snaps = []
                if backup_dir.exists():
                    snaps = sorted(backup_dir.glob("*.json"))
                if not snaps:
                    print("No snapshots found")
                    continue
                if len(parts) == 1 or parts[1] == "list":
                    print("\nTemplates Snapshots:")
                    for i, p in enumerate(snaps):
                        print(f"  [{i}] {p.name}")
                    print()
                    continue
                _idx = -1
                if parts[1] == "latest":
                    _idx = len(snaps) - 1
                else:
                    try:
                        _idx = int(parts[1])
                    except Exception:
                        print("Usage: restore [latest|list|<index>]")
                        continue
                if 0 <= _idx < len(snaps):
                    try:
                        # Load snapshot into current scene (create scene if needed)
                        with open(snaps[_idx], encoding="utf-8") as _f:
                            _state = json.load(_f)
                        _name = _state.get("name", "restored")
                        designer.scenes[_name] = SceneConfig(
                            name=_name,
                            width=int(_state.get("width", designer.width)),
                            height=int(_state.get("height", designer.height)),
                            widgets=[WidgetConfig(**_w) for _w in _state.get("widgets", [])],
                            bg_color=_state.get("bg_color", "black"),
                        )
                        designer.current_scene = _name
                        # Show quick diff summary if previous scene exists in undo
                        if designer.undo_stack:
                            try:
                                _prev = json.loads(designer.undo_stack[-1])
                                _pw = len(_prev.get("widgets", []))
                                _cw = len(_state.get("widgets", []))
                                print(
                                    f"[OK] Restored snapshot {snaps[_idx].name} (widgets: {_pw} -> {_cw})"
                                )
                            except Exception:
                                print(f"[OK] Restored snapshot {snaps[_idx].name}")
                        else:
                            print(f"[OK] Restored snapshot {snaps[_idx].name}")
                    except Exception as e:
                        print(f"[FAIL] Failed to restore: {e}")
                else:
                    print("Invalid index")

            elif action == "export":
                if len(parts) < 2:
                    print("Usage: export <file> [html]")
                    continue
                if len(parts) > 2 and parts[2].lower() == "html":
                    designer.export_to_html(parts[1])
                else:
                    designer.export_code(parts[1])

            # Groups
            elif action == "group":
                if len(parts) < 2:
                    print("Usage: group <create|add|remove|delete|list|lock|visible> ...")
                    continue
                _sub = parts[1].lower()
                if _sub == "list":
                    _groups = designer.list_groups()
                    if not _groups:
                        print("No groups")
                    else:
                        print("\nGroups:")
                        for _name, _members in _groups:
                            print(f"  - {_name:20s} [{', '.join(map(str, _members))}]")
                        print()
                elif _sub in ["create", "add", "remove"]:
                    if len(parts) < 4:
                        print(f"Usage: group {_sub} <name> <idx1> [idx2...]")
                        continue
                    _name = parts[2]
                    try:
                        _idxs = [int(_x) for _x in parts[3:]]
                    except Exception:
                        print("Indices must be integers")
                        continue
                    _ok = False
                    if _sub == "create":
                        _ok = designer.create_group(_name, _idxs)
                    elif _sub == "add":
                        _ok = designer.add_to_group(_name, _idxs)
                    else:
                        _ok = designer.remove_from_group(_name, _idxs)
                    print("[OK] Done" if _ok else MSG_FAILED)
                elif _sub == "delete":
                    if len(parts) < 3:
                        print("Usage: group delete <name>")
                        continue
                    print("[OK] Deleted" if designer.delete_group(parts[2]) else MSG_FAILED)
                elif _sub in ["lock", "visible"]:
                    if len(parts) < 4:
                        print(f"Usage: group {_sub} <name> <on|off|toggle>")
                        continue
                    _name = parts[2]
                    _mode = parts[3].lower()
                    if _sub == "lock":
                        _ok = designer.group_set_lock(_name, _mode)
                    else:
                        _ok = designer.group_set_visible(_name, _mode)
                    print("[OK] Done" if _ok else MSG_FAILED)
                else:
                    print("Unknown group subcommand")

            # Symbols
            elif action == "symbol":
                if len(parts) < 2:
                    print("Usage: symbol <save|list|place> ...")
                    continue
                _sub = parts[1].lower()
                if _sub == "list":
                    if not designer.symbols:
                        print("No symbols")
                    else:
                        print("\nRepeat Symbols:")
                        for _name, _spec in sorted(designer.symbols.items()):
                            _w, _h = _spec.get("size", (0, 0))
                            print(
                                f"  - {_name:20s} size={_w}x{_h} items={len(_spec.get('items', []))}"
                            )
                        print()
                    continue
                if _sub == "save":
                    if len(parts) < 4:
                        print("Usage: symbol save <name> <idx1> [idx2...]")
                        continue
                    _name = parts[2]
                    try:
                        _idxs = [int(_x) for _x in parts[3:]]
                    except Exception:
                        print("Indices must be integers")
                        continue
                    _ok = designer.save_symbol(_name, _idxs)
                    print("[OK] Saved" if _ok else "[FAIL] Failed to save symbol")
                elif _sub == "place":
                    if len(parts) < 5:
                        print("Usage: symbol place <name> <x> <y>")
                        continue
                    _name = parts[2]
                    try:
                        _x = int(parts[3])
                        _y = int(parts[4])
                    except Exception:
                        print("x/y must be integers")
                        continue
                    _ok = designer.place_symbol(_name, _x, _y)
                    print("[OK] Placed" if _ok else "[FAIL] Failed to place symbol")
                else:
                    print("Unknown symbol subcommand")

            elif action == "checkpoint":
                if len(parts) < 2:
                    print("Usage: checkpoint <name>")
                    continue
                _ok = designer.create_checkpoint(parts[1])
                if _ok:
                    print(f"[OK] Checkpoint created: {parts[1]}")
                else:
                    print("[FAIL] Failed to create checkpoint (no scene loaded[OK])")

            elif action == "checkpoints":
                cps = designer.list_checkpoints()
                if not cps:
                    print("No checkpoints")
                else:
                    print("\nCheckpoints:")
                    for name, ts in cps:
                        print(f"  - {name:20s} {ts}")
                    print()

            elif action == "rollback":
                if len(parts) < 2:
                    print("Usage: rollback <name>")
                    continue
                if designer.rollback_checkpoint(parts[1]):
                    print(f"[OK] Rolled back to checkpoint: {parts[1]}")
                else:
                    print("[FAIL] Failed to rollback (unknown checkpoint[OK])")

            elif action == "diff":
                if len(parts) < 2:
                    print("Usage: diff <A> [B]")
                    continue
                _name_a = parts[1]
                _name_b = parts[2] if len(parts) > 2 else None
                if _name_a not in designer.checkpoints:
                    print("Unknown checkpoint A")
                    continue
                _a = designer.checkpoints[_name_a]["scene"]
                if _name_b:
                    if _name_b not in designer.checkpoints:
                        print("Unknown checkpoint B")
                        continue
                    _b = designer.checkpoints[_name_b]["scene"]
                else:
                    _cur = designer._current_scene_state()
                    if not _cur:
                        print("No current scene to diff against")
                        continue
                    _b = _cur
                _d = designer._diff_states(_a, _b)
                _ca = _d["widgets"]["count"]["a"]
                _cb = _d["widgets"]["count"]["b"]
                print("\nSearch Diff:")
                print(f"  Scene A: {_d['scene']['a']}  size={_d['size']['a']}  widgets={_ca}")
                print(f"  Scene B: {_d['scene']['b']}  size={_d['size']['b']}  widgets={_cb}")
                if _d["widgets"]["added"]:
                    print(f"  + Added indices in B: {_d['widgets']['added']}")
                if _d["widgets"]["removed"]:
                    print(f"  - Removed indices from A: {_d['widgets']['removed']}")
                if _d["widgets"]["changed"]:
                    print(f"  ~ Changed widgets: {len(_d['widgets']['changed'])}")
                    for _ch in _d["widgets"]["changed"][:10]:
                        _ix = _ch["index"]
                        _keys = ", ".join(list(_ch["changes"].keys())[:6])
                        print(
                            f"     [{_ix}] fields: {_keys}{' ...' if len(_ch['changes']) > 6 else ''}"
                        )
                else:
                    print("  No property changes in matching indices")
                print()

            elif action == "layout":
                if len(parts) < 2:
                    print("Usage: layout <vertical|horizontal|grid> [spacing]")
                    continue
                _spacing = int(parts[2]) if len(parts) > 2 else 4
                designer.auto_layout(parts[1], _spacing)
                print(f"[OK] Applied {parts[1]} layout")

            elif action == "align":
                if len(parts) < 3:
                    print("Usage: align <left|right|top|bottom|center_h|center_v> <idx1> [idx2...]")
                    continue
                _indices = [int(_x) for _x in parts[2:]]
                designer.align_widgets(parts[1], _indices)
                print(f"[OK] Aligned {len(_indices)} widgets ({parts[1]})")

            elif action == "distribute":
                if len(parts) < 4:
                    print("Usage: distribute <horizontal|vertical> <idx1> <idx2> [idx3...]")
                    continue
                _indices = [int(_x) for _x in parts[2:]]
                designer.distribute_widgets(parts[1], _indices)
                print(f"[OK] Distributed {len(_indices)} widgets ({parts[1]})")

            elif action == "gridcols":
                if len(parts) < 2:
                    print(f"Grid columns: {designer.grid_columns} (grid size {designer.grid_size})")
                else:
                    try:
                        _n = int(parts[1])
                        designer.set_grid_columns(_n)
                        print(
                            f"[OK] Grid columns set to {designer.grid_columns} (grid size {designer.grid_size})"
                        )
                    except Exception:
                        print("Usage: gridcols <4|8|12>")

            elif action == "bp":
                if len(parts) < 2:
                    print("Usage: bp <WxH>  (e.g., 128x64, 240x135, 320x240)")
                    continue
                try:
                    _wh = parts[1].lower().split("x")
                    _w = int(_wh[0])
                    _h = int(_wh[1])
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        _sc.width = _w
                        _sc.height = _h
                        print(f"[OK] Breakpoint applied: {_w}x{_h}")
                except Exception:
                    print("Usage: bp <WxH>")

            elif action == "resp":
                if len(parts) < 2:
                    print("Usage: resp <base|apply>")
                    continue
                _sub = parts[1].lower()
                if _sub == "base":
                    designer.set_responsive_base()
                    print("[OK] Responsive base recorded")
                elif _sub == "apply":
                    designer.apply_responsive()
                    print("[OK] Responsive constraints applied")
                else:
                    print("Usage: resp <base|apply>")

            elif action == "state":
                if len(parts) < 2:
                    print("Usage: state <define|set|list|clear> ...")
                    continue
                if not (designer.current_scene and designer.current_scene in designer.scenes):
                    print(MSG_NO_SCENE)
                    continue
                _sub = parts[1].lower()
                _scene = designer.scenes[designer.current_scene]
                if _sub == "define":
                    if len(parts) < 5:
                        print("Usage: state define <idx> <name> k=v [k=v]...")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    _w.state_overrides = _w.state_overrides or {}
                    _cur = dict(_w.state_overrides.get(_name, {}))
                    for _kv in parts[4:]:
                        if "=" in _kv:
                            _k, _v = _kv.split("=", 1)
                            _cur[_k] = _v
                    _w.state_overrides[_name] = _cur
                    print(f"[OK] State '{_name}' overrides defined for widget {_idx}")
                elif _sub == "set":
                    if len(parts) < 4:
                        print("Usage: state set <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _scene.widgets[_idx].state = _name
                    print(f"[OK] Widget {_idx} state set to '{_name}'")
                elif _sub == "list":
                    if len(parts) < 3:
                        print("Usage: state list <idx>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    _keys = sorted((_w.state_overrides or {}).keys())
                    _cur = _w.state or "default"
                    if not _keys:
                        print(f"(no overrides). Current state: {_cur}")
                    else:
                        print(f"States for widget {_idx} (current: {_cur}): {', '.join(_keys)}")
                elif _sub == "clear":
                    if len(parts) < 4:
                        print("Usage: state clear <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    if _name in (_w.state_overrides or {}):
                        del _w.state_overrides[_name]
                        print(f"[OK] Removed state '{_name}' from widget {_idx}")
                    else:
                        print("No such state override")
                else:
                    print("Unknown state subcommand")

            elif action == "anim":
                if len(parts) < 2:
                    print("Usage: anim <list|add|clear|preview|play> ...")
                    continue
                _sub = parts[1].lower()
                _builtins = ["bounce", "slideinleft", "pulse", "fadein"]
                if _sub == "list":
                    print("\nAnimations:")
                    for _n in _builtins:
                        print(f"  - {_n}")
                    print()
                    continue
                if not (designer.current_scene and designer.current_scene in designer.scenes):
                    print(MSG_NO_SCENE)
                    continue
                _scene = designer.scenes[designer.current_scene]
                if _sub == "add":
                    if len(parts) < 4:
                        print("Usage: anim add <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print(MSG_UNKNOWN_ANIM)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    if _name not in (_w.animations or []):
                        _w.animations.append(_name)
                    print(f"[OK] Animation '{_name}' tagged on widget {_idx}")
                elif _sub == "clear":
                    if len(parts) < 4:
                        print("Usage: anim clear <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print(MSG_INDEX_INTEGER)
                        continue
                    _name = parts[3].lower()
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_idx]
                    if _name in (_w.animations or []):
                        _w.animations = [_a for _a in (_w.animations or []) if _a != _name]
                        print(f"[OK] Animation '{_name}' removed from widget {_idx}")
                    else:
                        print("Animation not tagged on widget")
                elif _sub == "preview":
                    if len(parts) < 6:
                        print("Usage: anim preview <idx> <name> <steps> <t>")
                        continue
                    try:
                        _idx = int(parts[2])
                        _steps = int(parts[4])
                        _t = int(parts[5])
                    except Exception:
                        print("Usage: anim preview <idx> <name> <steps> <t>")
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print(MSG_UNKNOWN_ANIM)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    # Set context, render once, then clear
                    designer.anim_context = {"idx": _idx, "name": _name, "steps": _steps, "t": _t}
                    print("\n" + designer.preview_ascii())
                    print()
                    designer.anim_context = None
                elif _sub == "play":
                    if len(parts) < 5:
                        print("Usage: anim play <idx> <name> <steps> [delay_ms]")
                        continue
                    try:
                        _idx = int(parts[2])
                        _steps = int(parts[4])
                        _delay_ms = int(parts[5]) if len(parts) > 5 else 120
                    except Exception:
                        print("Usage: anim play <idx> <name> <steps> [delay_ms]")
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print(MSG_UNKNOWN_ANIM)
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    import time

                    try:
                        for _t in range(max(1, _steps)):
                            designer.anim_context = {
                                "idx": _idx,
                                "name": _name,
                                "steps": _steps,
                                "t": _t,
                            }
                            print(f"\n[# {_t + 1}/{_steps}] {_name}\n")
                            print(designer.preview_ascii())
                            time.sleep(max(0, _delay_ms) / 1000.0)
                    except KeyboardInterrupt:
                        print("\nStop: Animation stopped")
                    finally:
                        designer.anim_context = None
                else:
                    print("Unknown anim subcommand")

            elif action == "context":
                # Contextual help for a widget
                _target_idx: Optional[int] = None
                if len(parts) > 1:
                    try:
                        _target_idx = int(parts[1])
                    except Exception:
                        print("Usage: context [idx]")
                        continue
                else:
                    _target_idx = designer.selected_widget
                if designer.current_scene and designer.current_scene in designer.scenes:
                    _scene = designer.scenes[designer.current_scene]
                    if _target_idx is None:
                        print(
                            "Select a widget first with 'select <idx>' or pass an index: context <idx>"
                        )
                        continue
                    if not (0 <= _target_idx < len(_scene.widgets)):
                        print(MSG_INVALID_INDEX)
                        continue
                    _w = _scene.widgets[_target_idx]
                    _info = get_widget_help(_w)
                    print(f"\nContext Context: [{_target_idx}] {_w.type}")
                    print(
                        f"   Size: {_w.width}x{_w.height} at ({_w.x},{_w.y})  Style: {_w.style}  Align: {_w.align}"
                    )
                    if getattr(_w, "text", ""):
                        print(f"   Text: '{_w.text}'")
                    if getattr(_w, "locked", False):
                        print(f"   State: [LOCK] locked (use: lock {_target_idx} off)")
                    print(f"\nAbout About: {_info.get('description', 'N/A')}")
                    _tips = _info.get("tips", [])
                    if _tips:
                        print("Tips Tips:")
                        for _t in _tips:
                            print(f"   - {_t}")
                    _qa = [
                        f"duplicate {_target_idx} 8 8",
                        f"align left {_target_idx} <idx2> [idx3...]",
                        f"distribute horizontal {_target_idx} <idx2> [idx3...]",
                        f"lock {_target_idx} toggle",
                    ]
                    print("\nFast Quick actions:")
                    for _a in _qa:
                        print(f"   > {_a}")
                    print()
                else:
                    print(MSG_NO_SCENE)

            elif action == "help":
                if len(parts) > 1:
                    show_command_help(parts[1])
                else:
                    print(
                        "Type command name for help. Available: add, template, edit, grid, layout, etc."
                    )

            else:
                print(f"[FAIL] Unknown command: {action}. Type 'help' for commands.")

        except KeyboardInterrupt:
            print("\n\nBye Exiting...")
            break
        except Exception as e:
            print(f"[FAIL] Error: {e}")


def show_command_help(command: str):
    """Show detailed help for specific command"""
    helps = {
        "add": """
Add widget: add <type> <x> <y> <w> <h> [text]
  Examples:
    add label 10 10 100 10 "Hello World"
    add button 20 30 40 12 "Click Me"
    add progressbar 10 50 100 8
    add gauge 60 20 40 30
        """,
        "template": """
Add from template: template <name> <x> <y>
  Available templates: title_label, button_primary, button_secondary,
                       info_panel, progress_bar, gauge_half
  Example: template button_primary 20 30
        """,
        "edit": """
Edit widget property: edit <idx> <property> <value>
  Properties: text, value, checked, border_style, color_fg, color_bg,
             align, valign, z_index, enabled, visible
  Examples:
    edit 0 text "New Text"
    edit 1 value 75
    edit 2 border_style double
    edit 3 color_fg cyan
        """,
    }
    print(helps.get(command, f"No detailed help for '{command}'"))


def get_widget_help(widget: WidgetConfig) -> Dict[str, Any]:
    """Return contextual description and layout/style tips for a widget."""
    wtype = str(widget.type).lower()
    base = {
        "label": {
            "description": "Static text. Use for titles, captions, and inline hints.",
            "tips": [
                "Use align=center for titles; turn off border for clean headers",
                "Increase padding_x on narrow labels to avoid cramped text",
                "Keep contrast high (color_fg vs color_bg) for readability",
            ],
        },
        "button": {
            "description": "Clickable action. Prefer concise verbs (OK, Save, Back).",
            "tips": [
                "Keep height >= 10 for legibility on small screens",
                "Use rounded/double border to indicate primary/secondary",
                "Align a group with align left/right; use distribute horizontal",
            ],
        },
        "progressbar": {
            "description": "Linear progress indicator for completion percentage.",
            "tips": [
                "Use full width minus margins for dashboard layouts",
                "Set min/max bounds consistently across related bars",
            ],
        },
        "gauge": {
            "description": "Vertical bar gauge for a single numeric value.",
            "tips": [
                "Group multiple gauges and distribute horizontally",
                "Show current value elsewhere; keep gauge visuals minimal",
            ],
        },
        "checkbox": {
            "description": "Binary toggle with a label.",
            "tips": [
                "Ensure text is non-empty for accessibility",
                "Align left with other inputs for neat forms",
            ],
        },
        "radiobutton": {
            "description": "Mutually exclusive options within a group.",
            "tips": [
                "Stack vertically; use distribute vertical to space evenly",
                "Group with a surrounding panel for clarity",
            ],
        },
        "textbox": {
            "description": "Editable text input.",
            "tips": [
                "Ensure width is sufficient for expected content",
                "Use a label above with smaller padding",
            ],
        },
        "panel": {
            "description": "Container/background for grouping elements.",
            "tips": [
                "Use double/bold border for emphasis",
                "Set z_index lower than foreground widgets",
            ],
        },
        "icon": {
            "description": "Single-character icon glyph.",
            "tips": [
                "Pair with a label; align center for symmetry",
            ],
        },
        "chart": {
            "description": "Compact bar chart for small datasets.",
            "tips": [
                "Limit categories to fit inner width",
                "Consider labels elsewhere to keep chart readable",
            ],
        },
        "box": {
            "description": "Generic rectangle. Useful as spacer or divider.",
            "tips": [
                "Use dashed/bold borders to separate sections",
            ],
        },
        "slider": {
            "description": "Adjustable control for a numeric range.",
            "tips": [
                "Reserve adequate width; show current value nearby",
            ],
        },
    }
    return base.get(wtype, {"description": "Generic widget.", "tips": []})


# --- Theme & WCAG helpers ---

_NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
}


def _parse_color(c: str) -> Tuple[int, int, int]:
    c = (c or "").strip().lower()
    if c in _NAMED_COLORS:
        return _NAMED_COLORS[c]
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 6:
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except Exception:
                return (0, 0, 0)
    return (0, 0, 0)


def _rel_lum(rgb: Tuple[int, int, int]) -> float:
    def f(u: float) -> float:
        u = u / 255.0
        return (u / 12.92) if (u <= 0.03928) else pow((u + 0.055) / 1.055, 2.4)

    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast_ratio(fg: str, bg: str) -> float:
    L1 = _rel_lum(_parse_color(fg))
    L2 = _rel_lum(_parse_color(bg))
    lmax, lmin = (max(L1, L2), min(L1, L2))
    return (lmax + 0.05) / (lmin + 0.05)
