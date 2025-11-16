#!/usr/bin/env python3
"""
Visual UI Designer for ESP32 Simulator
Drag-and-drop widget editor with live preview and code generation
"""

import sys
import json
import copy
from typing import List, Dict, Optional, Tuple, Any, Iterable, TypedDict, Union, cast
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import os
from pathlib import Path


PREVIEW_SCRIPT = os.path.join(os.path.dirname(__file__), 'ui_designer_preview.py')


def _empty_int_list() -> List[int]:
    """Typed default factory for chart data."""
    return []


def _normalize_int_list(values: Iterable[Any]) -> List[int]:
    """Coerce an arbitrary iterable into a list of ints for chart data."""
    return [int(v) for v in values]


def _empty_str_list() -> List[str]:
    """Typed default factory for string lists (e.g., animations)."""
    return []


def _empty_state_overrides() -> Dict[str, Dict[str, Any]]:
    """Typed default factory for state overrides mapping."""
    return {}


class ConstraintBaseline(TypedDict, total=False):
    x: int
    y: int
    width: int
    height: int
    bw: int
    bh: int


class Constraints(TypedDict, total=False):
    b: ConstraintBaseline
    ax: str
    ay: str
    sx: bool
    sy: bool
    mx: int
    my: int
    mr: int
    mb: int


def _empty_constraints() -> Constraints:
    """Typed default factory for constraints metadata."""
    return {}


def _make_baseline(x: int, y: int, width: int, height: int, bw: int, bh: int) -> ConstraintBaseline:
    """Helper to build a typed ConstraintBaseline dict."""
    return {'x': x, 'y': y, 'width': width, 'height': height, 'bw': bw, 'bh': bh}


class ResponsiveRule(TypedDict, total=False):
    """Rule describing how to adapt a widget under certain conditions."""
    name: str
    condition: str
    apply: Dict[str, Any]
    else_apply: Dict[str, Any]


def _empty_responsive_rules() -> List['ResponsiveRule']:
    """Typed default factory for responsive rules."""
    return []


class WidgetType(Enum):
    """Available widget types"""
    LABEL = "label"
    BOX = "box"
    BUTTON = "button"
    GAUGE = "gauge"
    PROGRESSBAR = "progressbar"
    CHECKBOX = "checkbox"
    RADIOBUTTON = "radiobutton"
    SLIDER = "slider"
    TEXTBOX = "textbox"
    PANEL = "panel"
    ICON = "icon"
    CHART = "chart"


class BorderStyle(Enum):
    """Border styles"""
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"
    ROUNDED = "rounded"
    BOLD = "bold"
    DASHED = "dashed"


@dataclass
class WidgetConfig:
    """Widget configuration"""
    type: str  # label, box, button, gauge, progressbar, checkbox, etc.
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    style: str = "default"  # default, bold, inverse, highlight
    color_fg: str = "white"
    color_bg: str = "black"
    border: bool = True
    border_style: str = "single"  # single, double, rounded, bold, dashed
    align: str = "left"  # left, center, right
    valign: str = "middle"  # top, middle, bottom
    
    # Extended properties
    value: int = 0  # For gauge, slider, progressbar
    min_value: int = 0
    max_value: int = 100
    checked: bool = False  # For checkbox, radiobutton
    enabled: bool = True
    visible: bool = True
    icon_char: str = ""  # For icon widget
    data_points: List[int] = field(default_factory=_empty_int_list)  # For chart
    z_index: int = 0  # Layer order
    
    # Layout hints
    padding_x: int = 1
    padding_y: int = 0
    margin_x: int = 0
    margin_y: int = 0
    # Responsive/constraints metadata (stored as simple dicts for export)
    constraints: Constraints = field(default_factory=_empty_constraints)
    responsive_rules: List[ResponsiveRule] = field(default_factory=_empty_responsive_rules)
    animations: List[str] = field(default_factory=_empty_str_list)
    # Editing safeguards
    locked: bool = False
    # Theme role bindings (used when applying themes)
    theme_fg_role: str = ""
    theme_bg_role: str = ""
    # State variants
    state: str = "default"
    state_overrides: Dict[str, Dict[str, Any]] = field(default_factory=_empty_state_overrides)


@dataclass
class SceneConfig:
    """Scene configuration"""
    name: str
    width: int
    height: int
    widgets: List[WidgetConfig]
    bg_color: str = "black"
    # Responsive base used for constraints
    base_width: int = 128
    base_height: int = 64
    # Theme metadata
    theme: str = "default"
    contrast_lock: bool = True


class UIDesigner:
    """Visual UI designer with layout editor"""
    
    def __init__(self, width: int = 128, height: int = 64):
        self.width = width
        self.height = height
        self.scenes: Dict[str, SceneConfig] = {}
        self.current_scene: Optional[str] = None
        self.selected_widget: Optional[int] = None
        
        # Undo/redo stacks
        self.undo_stack: List[str] = []  # JSON snapshots
        self.redo_stack: List[str] = []
        self.max_undo = 50
        
        # Templates
        self.templates: Dict[str, WidgetConfig] = self._create_default_templates()
        
        # Grid settings
        self.grid_enabled = True
        self.grid_size = 4
        self.snap_to_grid = True
        # Magnetic snapping settings
        self.snap_edges = True
        self.snap_centers = True
        self.snap_tolerance = 3
        self.snap_fluid = True  # fluid mode ignores strict grid when snapping
        self.show_guides = True
        self.last_guides: List[Dict[str, Any]] = []

        # Named checkpoints (in-memory) for quick diff/rollback
        self.checkpoints: Dict[str, Dict[str, Any]] = {}

        # Groups and Symbols
        self.groups: Dict[str, List[int]] = {}
        self.symbols: Dict[str, Dict[str, Any]] = {}

        # Grid columns (affects grid size helper)
        self.grid_columns = 8

        # Theme presets
        self.themes: Dict[str, Dict[str, str]] = {
            'default': {'bg':'black','text':'white','primary':'cyan','secondary':'green','accent':'yellow','danger':'red'},
            'light':   {'bg':'#f7f7f7','text':'#111','primary':'#0066cc','secondary':'#2e7d32','accent':'#ff8f00','danger':'#c62828'},
            'dark':    {'bg':'#121212','text':'#e0e0e0','primary':'#64b5f6','secondary':'#81c784','accent':'#ffd54f','danger':'#ef5350'},
            'hc':      {'bg':'#000','text':'#fff','primary':'#0ff','secondary':'#0f0','accent':'#ff0','danger':'#f00'},
            'cyber':   {'bg':'#0a0f14','text':'#05f1fe','primary':'#27f78d','secondary':'#9a4dff','accent':'#ff2e97','danger':'#ff3b30'},
        }
        self.theme_contrast_min = 4.5

        # Animation preview context
        self.anim_context: Optional[Dict[str, Any]] = None
    
    def _create_default_templates(self) -> Dict[str, WidgetConfig]:
        """Create default widget templates"""
        return {
            'title_label': WidgetConfig(
                type='label', x=0, y=0, width=128, height=10,
                text='Title', align='center', style='bold',
                border=False, color_fg='cyan'
            ),
            'button_primary': WidgetConfig(
                type='button', x=0, y=0, width=40, height=12,
                text='OK', align='center', border=True,
                border_style='rounded', color_fg='black', color_bg='green'
            ),
            'button_secondary': WidgetConfig(
                type='button', x=0, y=0, width=40, height=12,
                text='Cancel', align='center', border=True,
                border_style='rounded', color_fg='white', color_bg='red'
            ),
            'info_panel': WidgetConfig(
                type='panel', x=0, y=0, width=120, height=50,
                border=True, border_style='double', color_fg='white', color_bg='blue'
            ),
            'progress_bar': WidgetConfig(
                type='progressbar', x=0, y=0, width=100, height=8,
                value=50, min_value=0, max_value=100,
                border=True, color_fg='green', color_bg='black'
            ),
            'gauge_half': WidgetConfig(
                type='gauge', x=0, y=0, width=40, height=20,
                value=75, min_value=0, max_value=100,
                border=True, color_fg='yellow'
            ),
        }
    
    def _save_state(self):
        """Save current state for undo"""
        if self.current_scene and self.current_scene in self.scenes:
            state = json.dumps(asdict(self.scenes[self.current_scene]))
            self.undo_stack.append(state)
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            # Autosave snapshot (undo-safe)
            try:
                backup_dir = Path.home() / ".esp32os" / "designer_backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                scene_name = (self.current_scene or "scene").replace(" ", "_")
                snap_path = backup_dir / f"{scene_name}_{ts}.json"
                with open(snap_path, 'w', encoding='utf-8') as f:
                    f.write(state)
            except Exception:
                pass
    
    def undo(self) -> bool:
        """Undo last operation"""
        if not self.undo_stack or not self.current_scene:
            return False
        
        # Save current state to redo
        current_state = json.dumps(asdict(self.scenes[self.current_scene]))
        self.redo_stack.append(current_state)
        
        # Restore previous state
        prev_state = json.loads(self.undo_stack.pop())
        widgets = [WidgetConfig(**w) for w in prev_state['widgets']]
        self.scenes[self.current_scene] = SceneConfig(
            name=prev_state['name'],
            width=prev_state['width'],
            height=prev_state['height'],
            widgets=widgets,
            bg_color=prev_state.get('bg_color', 'black')
        )
        return True
    
    def redo(self) -> bool:
        """Redo last undone operation"""
        if not self.redo_stack or not self.current_scene:
            return False
        
        # Save current state to undo
        current_state = json.dumps(asdict(self.scenes[self.current_scene]))
        self.undo_stack.append(current_state)
        
        # Restore next state
        next_state = json.loads(self.redo_stack.pop())
        widgets = [WidgetConfig(**w) for w in next_state['widgets']]
        self.scenes[self.current_scene] = SceneConfig(
            name=next_state['name'],
            width=next_state['width'],
            height=next_state['height'],
            widgets=widgets,
            bg_color=next_state.get('bg_color', 'black')
        )
        return True
    
    def snap_position(self, x: int, y: int) -> Tuple[int, int]:
        """Snap coordinates to grid"""
        if self.snap_to_grid and self.grid_enabled:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size
        return x, y

    def _apply_snapping(self, widget: WidgetConfig, x: int, y: int, scene: SceneConfig) -> Tuple[int, int]:
        """Apply magnetic snapping to edges and centers within tolerance. Records guides."""
        # Reset guides
        self.last_guides = []
        if not (self.snap_edges or self.snap_centers):
            return x, y
        # Optionally apply grid first depending on mode
        if not self.snap_fluid:
            x, y = self.snap_position(x, y)
        best_dx = None
        best_dy = None
        best_vline: Optional[Tuple[int, int, int, str]] = None
        best_hline: Optional[Tuple[int, int, int, str]] = None
        w_left = x
        w_right = x + widget.width
        w_top = y
        w_bottom = y + widget.height
        w_cx = x + widget.width // 2
        w_cy = y + widget.height // 2
        for other in scene.widgets:
            if other is widget:
                continue
            o_left = other.x
            o_right = other.x + other.width
            o_top = other.y
            o_bottom = other.y + other.height
            o_cx = other.x + other.width // 2
            o_cy = other.y + other.height // 2
            # Horizontal axis snapping (affects x): align lefts/rights/centers
            candidates_x: List[Tuple[int, Tuple[int, int, int], str]] = []
            if self.snap_edges:
                candidates_x += [
                    (o_left - w_left, (o_left, min(w_top, o_top), max(w_bottom, o_bottom)), 'L'),
                    (o_right - w_right, (o_right, min(w_top, o_top), max(w_bottom, o_bottom)), 'R'),
                ]
            if self.snap_centers:
                candidates_x.append((o_cx - w_cx, (o_cx, min(w_top, o_top), max(w_bottom, o_bottom)), 'C'))
            for dx, (vx, vy1, vy2), kind in candidates_x:
                if abs(dx) <= self.snap_tolerance:
                    if best_dx is None or abs(dx) < abs(best_dx):
                        best_dx = dx
                        best_vline = (vx, vy1, vy2, kind)
            # Vertical axis snapping (affects y): align tops/bottoms/centers
            candidates_y: List[Tuple[int, Tuple[int, int, int], str]] = []
            if self.snap_edges:
                candidates_y += [
                    (o_top - w_top, (o_top, min(w_left, o_left), max(w_right, o_right)), 'T'),
                    (o_bottom - w_bottom, (o_bottom, min(w_left, o_left), max(w_right, o_right)), 'B'),
                ]
            if self.snap_centers:
                candidates_y.append((o_cy - w_cy, (o_cy, min(w_left, o_left), max(w_right, o_right)), 'C'))
            for dy, (hy, hx1, hx2), kind in candidates_y:
                if abs(dy) <= self.snap_tolerance:
                    if best_dy is None or abs(dy) < abs(best_dy):
                        best_dy = dy
                        best_hline = (hy, hx1, hx2, kind)
        if best_dx is not None:
            x += best_dx
            if best_vline is not None:
                vx, vy1, vy2, k = best_vline
                self.last_guides.append({'type':'v','x':vx,'y1':max(0,vy1),'y2':min(scene.height-1,vy2),'k':k})
        if best_dy is not None:
            y += best_dy
            if best_hline is not None:
                hy, hx1, hx2, k = best_hline
                self.last_guides.append({'type':'h','y':hy,'x1':max(0,hx1),'x2':min(scene.width-1,hx2),'k':k})
        # Final clamp to scene bounds
        x = max(0, min(scene.width - widget.width, x))
        y = max(0, min(scene.height - widget.height, y))
        return x, y
    
    def create_scene(self, name: str) -> SceneConfig:
        """Create new scene"""
        scene = SceneConfig(
            name=name,
            width=self.width,
            height=self.height,
            widgets=[]
        )
        self.scenes[name] = scene
        self.current_scene = name
        return scene

    # --- Responsive helpers ---
    def set_responsive_base(self, scene_name: Optional[str] = None):
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        sc = self.scenes[scene_name]
        sc.base_width, sc.base_height = sc.width, sc.height

        # Store baseline into widget.constraints.b for later use
        for w in sc.widgets:
            b = _make_baseline(
                w.x, w.y, w.width, w.height,
                sc.base_width, sc.base_height,
            )
            w.constraints = w.constraints or _empty_constraints()
            w.constraints['b'] = b
            # Provide default anchors if absent
            w.constraints.setdefault('ax', 'left')
            w.constraints.setdefault('ay', 'top')
            w.constraints.setdefault('sx', False)
            w.constraints.setdefault('sy', False)
            w.constraints.setdefault('mx', 0)
            w.constraints.setdefault('my', 0)
            w.constraints.setdefault('mr', 0)
            w.constraints.setdefault('mb', 0)

    def apply_responsive(self, scene_name: Optional[str] = None):
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        sc = self.scenes[scene_name]
        bw = sc.base_width or sc.width
        bh = sc.base_height or sc.height
        dw = sc.width - bw
        dh = sc.height - bh
        if bw <= 0 or bh <= 0:
            return
        sx_ratio = sc.width / bw
        sy_ratio = sc.height / bh
        for w in sc.widgets:
            c: Constraints = w.constraints or _empty_constraints()
            b = cast(ConstraintBaseline, c.get('b') or _make_baseline(w.x, w.y, w.width, w.height, bw, bh))
            ax = c.get('ax', 'left')
            ay = c.get('ay', 'top')
            scale_x = bool(c.get('sx', False))
            scale_y = bool(c.get('sy', False))
            # Base values
            bx = b.get('x', w.x)
            by = b.get('y', w.y)
            bwid = b.get('width', w.width)
            bhgt = b.get('height', w.height)
            # Horizontal
            if ax == 'left':
                nx = bx
            elif ax == 'right':
                nx = bx + dw
            elif ax == 'center':
                nx = int(bx + dw/2)
            elif ax == 'stretch':
                nx = bx
                scale_x = True
            else:
                nx = bx
            # Vertical
            if ay == 'top':
                ny = by
            elif ay == 'bottom':
                ny = by + dh
            elif ay == 'middle':
                ny = int(by + dh/2)
            elif ay == 'stretch':
                ny = by
                scale_y = True
            else:
                ny = by
            # Size scaling
            nw = int(bwid * sx_ratio) if scale_x else bwid
            nh = int(bhgt * sy_ratio) if scale_y else bhgt
            # Clamp
            w.x = max(0, min(sc.width - 1, nx))
            w.y = max(0, min(sc.height - 1, ny))
            w.width = max(1, min(sc.width, nw))
            w.height = max(1, min(sc.height, nh))

    def set_grid_columns(self, n: int):
        if n in (4, 8, 12):
            self.grid_columns = n
            if self.current_scene and self.current_scene in self.scenes:
                sc = self.scenes[self.current_scene]
                self.grid_size = max(1, sc.width // n)
    
    def add_widget(
        self,
        widget: Union[WidgetConfig, WidgetType, str],
        scene_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add widget to scene.

        Accepts either a WidgetConfig instance (existing behavior) or a widget type
        (WidgetType or str) with keyword args like x, y, width, height, text, etc.
        """
        kw: Dict[str, Any] = kwargs
        # Normalize input to WidgetConfig
        if isinstance(widget, WidgetConfig):
            new_widget = widget
        else:
            # Determine widget type string
            if isinstance(widget, WidgetType):
                wtype = widget.value
            else:
                wtype = str(widget)

            # Required fields
            raw_x = kw.get('x')
            raw_y = kw.get('y')
            raw_w = kw.get('width')
            raw_h = kw.get('height')
            if raw_x is None or raw_y is None or raw_w is None or raw_h is None:
                raise TypeError("add_widget requires x, y, width, height when providing a type")
            try:
                x = int(raw_x)
                y = int(raw_y)
                width = int(raw_w)
                height = int(raw_h)
            except Exception as e:
                raise TypeError("add_widget requires x, y, width, height as integers") from e

            # Build WidgetConfig with optional fields
            new_widget = WidgetConfig(
                type=wtype,
                x=x,
                y=y,
                width=width,
                height=height,
                text=kw.get('text', ''),
                style=kw.get('style', 'default'),
                color_fg=kw.get('color_fg', 'white'),
                color_bg=kw.get('color_bg', 'black'),
                border=bool(kw.get('border', True)),
                border_style=str(kw.get('border_style', 'single')),
                align=str(kw.get('align', 'left')),
                valign=str(kw.get('valign', 'middle')),
                value=int(kw.get('value', 0)) if kw.get('value') is not None else 0,
                min_value=int(kw.get('min_value', 0)),
                max_value=int(kw.get('max_value', 100)),
                checked=bool(kw.get('checked', False)),
                enabled=bool(kw.get('enabled', True)),
                visible=bool(kw.get('visible', True)),
                icon_char=str(kw.get('icon_char', '')),
                data_points=_normalize_int_list(kw.get('data_points', []) or []),
                z_index=int(kw.get('z_index', 0)),
                padding_x=int(kw.get('padding_x', 1)),
                padding_y=int(kw.get('padding_y', 0)),
                margin_x=int(kw.get('margin_x', 0)),
                margin_y=int(kw.get('margin_y', 0)),
            )

        self._save_state()
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            # Snap to grid and magnetic snap against existing widgets
            sx, sy = self.snap_position(new_widget.x, new_widget.y)
            sx, sy = self._apply_snapping(new_widget, sx, sy, self.scenes[scene_name])
            new_widget.x, new_widget.y = sx, sy
            self.scenes[scene_name].widgets.append(new_widget)
    
    def add_widget_from_template(self, template_name: str, _widget_id: str,
                                 x: int, y: int, **kwargs: Any):
        """Add widget from template with custom properties"""
        if template_name not in self.templates:
            print(f"❌ Template '{template_name}' not found")
            return
        
        # Deep copy template and update properties
        widget = copy.deepcopy(self.templates[template_name])
        widget.x = x
        widget.y = y
        
        # Update with any additional properties
        for key, value in kwargs.items():
            if hasattr(widget, key):
                setattr(widget, key, value)
        
        # Add to scene
        self.add_widget(widget)
    
    def clone_widget(self, widget_idx: int, offset_x: int = 10, offset_y: int = 10,
                     scene_name: Optional[str] = None):
        """Clone existing widget"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                # Cloning allowed even if source is locked
                self._save_state()
                cloned = copy.deepcopy(scene.widgets[widget_idx])
                cloned.x += offset_x
                cloned.y += offset_y
                scene.widgets.append(cloned)
    
    def move_widget(self, widget_idx: int, dx: int, dy: int, scene_name: Optional[str] = None):
        """Move widget by delta"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                widget = scene.widgets[widget_idx]
                if getattr(widget, 'locked', False):
                    return
                nx = widget.x + dx
                ny = widget.y + dy
                # Apply grid then magnetic snapping against other widgets
                nx, ny = self._apply_snapping(widget, nx, ny, scene)
                widget.x = nx
                widget.y = ny
    
    def resize_widget(self, widget_idx: int, dw: int, dh: int, scene_name: Optional[str] = None):
        """Resize widget by delta"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                widget = scene.widgets[widget_idx]
                if getattr(widget, 'locked', False):
                    return
                widget.width = max(1, widget.width + dw)
                widget.height = max(1, widget.height + dh)
    
    def delete_widget(self, widget_idx: int, scene_name: Optional[str] = None):
        """Delete widget"""
        scene_name = scene_name or self.current_scene
        if scene_name and scene_name in self.scenes:
            scene = self.scenes[scene_name]
            if 0 <= widget_idx < len(scene.widgets):
                if getattr(scene.widgets[widget_idx], 'locked', False):
                    return
                del scene.widgets[widget_idx]
                self._reindex_after_delete(widget_idx)

    def _reindex_after_delete(self, deleted_idx: int):
        """Adjust group indices and selection after a widget deletion."""
        # Update selection
        if self.selected_widget is not None:
            if self.selected_widget == deleted_idx:
                self.selected_widget = None
            elif self.selected_widget > deleted_idx:
                self.selected_widget -= 1
        # Update groups
        for gname, members in self.groups.items():
            new_members: List[int] = []
            for m in members:
                if m == deleted_idx:
                    continue
                new_members.append(m - 1 if m > deleted_idx else m)
            if new_members:
                self.groups[gname] = new_members
            else:
                # Drop empty groups
                del self.groups[gname]

    # --- Groups API ---
    def create_group(self, name: str, indices: List[int]) -> bool:
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        valid = [i for i in indices if 0 <= i < len(self.scenes[self.current_scene].widgets)]
        if not valid:
            return False
        self.groups[name] = sorted(set(valid))
        return True

    def add_to_group(self, name: str, indices: List[int]) -> bool:
        if name not in self.groups:
            return False
        cur = set(self.groups[name])
        for i in indices:
            if self.current_scene and self.current_scene in self.scenes:
                if 0 <= i < len(self.scenes[self.current_scene].widgets):
                    cur.add(i)
        self.groups[name] = sorted(cur)
        return True

    def remove_from_group(self, name: str, indices: List[int]) -> bool:
        if name not in self.groups:
            return False
        cur = [i for i in self.groups[name] if i not in set(indices)]
        if cur:
            self.groups[name] = sorted(cur)
        else:
            del self.groups[name]
        return True

    def delete_group(self, name: str) -> bool:
        return bool(self.groups.pop(name, None) is not None)

    def list_groups(self) -> List[Tuple[str, List[int]]]:
        return sorted([(k, v) for k, v in self.groups.items()], key=lambda x: x[0])

    def group_set_lock(self, name: str, mode: str) -> bool:
        if name not in self.groups:
            return False
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        scene = self.scenes[self.current_scene]
        for i in self.groups[name]:
            if 0 <= i < len(scene.widgets):
                if mode == 'on':
                    scene.widgets[i].locked = True
                elif mode == 'off':
                    scene.widgets[i].locked = False
                elif mode == 'toggle':
                    scene.widgets[i].locked = not scene.widgets[i].locked
        return True

    def group_set_visible(self, name: str, mode: str) -> bool:
        if name not in self.groups:
            return False
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        scene = self.scenes[self.current_scene]
        for i in self.groups[name]:
            if 0 <= i < len(scene.widgets):
                if mode == 'on':
                    scene.widgets[i].visible = True
                elif mode == 'off':
                    scene.widgets[i].visible = False
                elif mode == 'toggle':
                    scene.widgets[i].visible = not scene.widgets[i].visible
        return True

    # --- Symbols API ---
    def save_symbol(self, name: str, indices: List[int]) -> bool:
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        scene = self.scenes[self.current_scene]
        sel = [scene.widgets[i] for i in indices if 0 <= i < len(scene.widgets)]
        if not sel:
            return False
        min_x = min(w.x for w in sel)
        min_y = min(w.y for w in sel)
        items = []
        for w in sel:
            d = asdict(w)
            d['x'] = w.x - min_x
            d['y'] = w.y - min_y
            items.append(d)
        self.symbols[name] = {'items': items, 'size': (max(w.x+w.width for w in sel)-min_x, max(w.y+w.height for w in sel)-min_y)}
        return True

    def place_symbol(self, name: str, x: int, y: int) -> bool:
        if name not in self.symbols:
            return False
        if not self.current_scene or self.current_scene not in self.scenes:
            return False
        spec = self.symbols[name]
        for item in spec.get('items', []):
            w = WidgetConfig(**{k: v for k, v in item.items() if k in WidgetConfig.__dataclass_fields__})
            w.x = x + int(item.get('x', 0))
            w.y = y + int(item.get('y', 0))
            self.add_widget(w)
        return True

    # --- Checkpoints & Diff ---
    def _current_scene_state(self) -> Optional[Dict[str, Any]]:
        if not self.current_scene or self.current_scene not in self.scenes:
            return None
        scene = self.scenes[self.current_scene]
        return {
            'name': scene.name,
            'width': scene.width,
            'height': scene.height,
            'bg_color': scene.bg_color,
            'widgets': [asdict(w) for w in scene.widgets],
        }

    def create_checkpoint(self, name: str) -> bool:
        state = self._current_scene_state()
        if state is None:
            return False
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        payload = {'ts': ts, 'scene': state}
        self.checkpoints[name] = payload
        # Persist snapshot to disk for durability
        try:
            base_dir = Path.home() / '.esp32os' / 'designer_checkpoints' / (self.current_scene or 'scene')
            base_dir.mkdir(parents=True, exist_ok=True)
            with open(base_dir / f"{ts}_{name}.json", 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass
        return True

    def list_checkpoints(self) -> List[Tuple[str, str]]:
        return sorted([(k, v.get('ts', '')) for k, v in self.checkpoints.items()], key=lambda x: x[1])

    def rollback_checkpoint(self, name: str) -> bool:
        if name not in self.checkpoints:
            return False
        snap = self.checkpoints[name].get('scene')
        if not snap:
            return False
        try:
            widgets = [WidgetConfig(**w) for w in snap.get('widgets', [])]
            self.scenes[snap['name']] = SceneConfig(
                name=snap['name'],
                width=int(snap.get('width', self.width)),
                height=int(snap.get('height', self.height)),
                widgets=widgets,
                bg_color=snap.get('bg_color', 'black'),
            )
            self.current_scene = snap['name']
            return True
        except Exception:
            return False

    def _diff_states(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """Compute a simple diff between two scene states."""
        diff: Dict[str, Any] = {
            'scene': {'a': a.get('name'), 'b': b.get('name')},
            'size': {'a': (a.get('width'), a.get('height')), 'b': (b.get('width'), b.get('height'))},
            'widgets': {
                'count': {'a': len(a.get('widgets', [])), 'b': len(b.get('widgets', []))},
                'changed': [],
                'added': [],
                'removed': [],
            }
        }
        wa = a.get('widgets', [])
        wb = b.get('widgets', [])
        n = min(len(wa), len(wb))
        keys_to_check = ['type','x','y','width','height','text','style','color_fg','color_bg','border','border_style','align','valign','value','min_value','max_value','checked','enabled','visible','z_index']
        for i in range(n):
            changes = {}
            for k in keys_to_check:
                va = wa[i].get(k)
                vb = wb[i].get(k)
                if va != vb:
                    changes[k] = {'a': va, 'b': vb}
            if changes:
                diff['widgets']['changed'].append({'index': i, 'changes': changes})
        if len(wa) > n:
            diff['widgets']['removed'] = list(range(n, len(wa)))
        if len(wb) > n:
            diff['widgets']['added'] = list(range(n, len(wb)))
        return diff
    
    def save_to_json(self, filename: str):
        """Save design to JSON file"""
        data = {
            "width": self.width,
            "height": self.height,
            "scenes": {
                name: {
                    "name": scene.name,
                    "width": scene.width,
                    "height": scene.height,
                    "bg_color": scene.bg_color,
                    "widgets": [asdict(w) for w in scene.widgets]
                }
                for name, scene in self.scenes.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Design saved: {filename}")
        # Auto: run preflight and export previews unless disabled
        try:
            if os.environ.get('ESP32OS_AUTO_EXPORT', '1') != '0':
                _auto_preflight_and_export(self, filename)
        except Exception as _e:
            print(f"⚠️ Auto-export skipped: {_e}")
    
    def load_from_json(self, filename: str):
        """Load design from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.width = data.get("width", 128)
        self.height = data.get("height", 64)
        self.scenes = {}
        
        for name, scene_data in data.get("scenes", {}).items():
            widgets = [WidgetConfig(**w) for w in scene_data.get("widgets", [])]
            scene = SceneConfig(
                name=scene_data["name"],
                width=scene_data["width"],
                height=scene_data["height"],
                widgets=widgets,
                bg_color=scene_data.get("bg_color", "black")
            )
            self.scenes[name] = scene
        
        if self.scenes:
            self.current_scene = list(self.scenes.keys())[0]
        
        print(f"📂 Design loaded: {filename}")
    
    def generate_python_code(self, scene_name: Optional[str] = None) -> str:
        """Generate Python code for scene"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return ""
        
        scene = self.scenes[scene_name]
        
        code_lines = [
            "# Auto-generated by UI Designer",
            f"# Scene: {scene.name}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "from dataclasses import dataclass",
            "from typing import List",
            "",
            "",
            "@dataclass",
            "class Widget:",
            "    type: str",
            "    x: int",
            "    y: int",
            "    width: int",
            "    height: int",
            "    text: str = ''",
            "    style: str = 'default'",
            "    color_fg: str = 'white'",
            "    color_bg: str = 'black'",
            "    border: bool = True",
            "    align: str = 'left'",
            "",
            "",
            f"def create_{scene.name.lower()}_scene() -> List[Widget]:",
            f'    """Create {scene.name} scene widgets"""',
            "    return [",
        ]
        
        for widget in scene.widgets:
            code_lines.append("        Widget(")
            code_lines.append(f"            type='{widget.type}',")
            code_lines.append(f"            x={widget.x},")
            code_lines.append(f"            y={widget.y},")
            code_lines.append(f"            width={widget.width},")
            code_lines.append(f"            height={widget.height},")
            if widget.text:
                code_lines.append(f"            text='{widget.text}',")
            if widget.style != 'default':
                code_lines.append(f"            style='{widget.style}',")
            if widget.color_fg != 'white':
                code_lines.append(f"            color_fg='{widget.color_fg}',")
            if widget.color_bg != 'black':
                code_lines.append(f"            color_bg='{widget.color_bg}',")
            if not widget.border:
                code_lines.append(f"            border={widget.border},")
            if widget.align != 'left':
                code_lines.append(f"            align='{widget.align}',")
            code_lines.append("        ),")
        
        code_lines.append("    ]")
        code_lines.append("")
        code_lines.append("")
        code_lines.append("if __name__ == '__main__':")
        code_lines.append(f"    widgets = create_{scene.name.lower()}_scene()")
        code_lines.append(f"    print(f'Created {{len(widgets)}} widgets for {scene.name} scene')")
        
        return '\n'.join(code_lines)
    
    def export_code(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as Python code file"""
        code = self.generate_python_code(scene_name)
        
        with open(filename, 'w') as f:
            f.write(code)
        
        print(f"🐍 Code exported: {filename}")
    
    def auto_layout(self, layout_type: str = 'vertical', spacing: int = 4,
                    scene_name: Optional[str] = None):
        """Auto-arrange widgets in scene"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        self._save_state()
        scene = self.scenes[scene_name]
        
        if layout_type == 'vertical':
            y_offset = spacing
            for widget in scene.widgets:
                widget.x = (scene.width - widget.width) // 2
                widget.y = y_offset
                y_offset += widget.height + spacing
        
        elif layout_type == 'horizontal':
            x_offset = spacing
            for widget in scene.widgets:
                widget.x = x_offset
                widget.y = (scene.height - widget.height) // 2
                x_offset += widget.width + spacing
        
        elif layout_type == 'grid':
            cols = int((scene.width + spacing) / (40 + spacing))  # Assume 40px avg width
            x_offset = spacing
            y_offset = spacing
            col = 0
            
            for widget in scene.widgets:
                widget.x = x_offset
                widget.y = y_offset
                
                col += 1
                x_offset += widget.width + spacing
                
                if col >= cols:
                    col = 0
                    x_offset = spacing
                    y_offset += 30 + spacing  # Assume 30px avg height
    
    def align_widgets(self, alignment: str, widget_indices: List[int],
                      scene_name: Optional[str] = None):
        """Align selected widgets"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        self._save_state()
        scene = self.scenes[scene_name]
        
        if not widget_indices:
            return
        
        widgets = [scene.widgets[i] for i in widget_indices if 0 <= i < len(scene.widgets)]
        
        if alignment == 'left':
            min_x = min(w.x for w in widgets)
            for w in widgets:
                w.x = min_x
        
        elif alignment == 'right':
            max_x = max(w.x + w.width for w in widgets)
            for w in widgets:
                w.x = max_x - w.width
        
        elif alignment == 'top':
            min_y = min(w.y for w in widgets)
            for w in widgets:
                w.y = min_y
        
        elif alignment == 'bottom':
            max_y = max(w.y + w.height for w in widgets)
            for w in widgets:
                w.y = max_y - w.height
        
        elif alignment == 'center_h':
            avg_x = sum(w.x + w.width // 2 for w in widgets) // len(widgets)
            for w in widgets:
                w.x = avg_x - w.width // 2
        
        elif alignment == 'center_v':
            avg_y = sum(w.y + w.height // 2 for w in widgets) // len(widgets)
            for w in widgets:
                w.y = avg_y - w.height // 2
    
    def distribute_widgets(self, direction: str, widget_indices: List[int],
                           scene_name: Optional[str] = None):
        """Distribute widgets evenly"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        self._save_state()
        scene = self.scenes[scene_name]
        
        if len(widget_indices) < 2:
            return
        
        widgets = [(i, scene.widgets[i]) for i in widget_indices if 0 <= i < len(scene.widgets)]
        
        if direction == 'horizontal':
            widgets.sort(key=lambda w: w[1].x)
            start_x = widgets[0][1].x
            end_x = widgets[-1][1].x + widgets[-1][1].width
            total_width = sum(w[1].width for w in widgets)
            spacing = (end_x - start_x - total_width) / (len(widgets) - 1)
            
            x_pos = start_x
            for _, widget in widgets:
                widget.x = int(x_pos)
                x_pos += widget.width + spacing
        
        elif direction == 'vertical':
            widgets.sort(key=lambda w: w[1].y)
            start_y = widgets[0][1].y
            end_y = widgets[-1][1].y + widgets[-1][1].height
            total_height = sum(w[1].height for w in widgets)
            spacing = (end_y - start_y - total_height) / (len(widgets) - 1)
            
            y_pos = start_y
            for _, widget in widgets:
                widget.y = int(y_pos)
                y_pos += widget.height + spacing
    
    def export_to_html(self, filename: str, scene_name: Optional[str] = None):
        """Export scene as HTML preview"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return
        
        scene = self.scenes[scene_name]
        preview = self.preview_ascii(scene_name)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{scene.name} - UI Design Preview</title>
    <style>
        body {{
            background: #1a1a1a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            padding: 20px;
        }}
        .preview {{
            background: #000;
            border: 2px solid #00ff00;
            padding: 20px;
            display: inline-block;
            white-space: pre;
            line-height: 1.2;
        }}
        .info {{
            margin-top: 20px;
            color: #00ffff;
        }}
    </style>
</head>
<body>
    <h1>🎨 {scene.name}</h1>
    <div class="preview">{preview}</div>
    <div class="info">
        <p>Size: {scene.width} × {scene.height}</p>
        <p>Widgets: {len(scene.widgets)}</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"🌐 HTML preview exported: {filename}")
    
    def preview_ascii(self, scene_name: Optional[str] = None, show_grid: bool = False) -> str:
        """Generate ASCII preview of scene with enhanced rendering"""
        scene_name = scene_name or self.current_scene
        if not scene_name or scene_name not in self.scenes:
            return ""
        
        scene = self.scenes[scene_name]
        
        # Create canvas
        canvas = [[' ' for _ in range(scene.width)] for _ in range(scene.height)]
        
        # Draw grid if enabled
        if show_grid and self.grid_enabled:
            for y in range(0, scene.height, self.grid_size):
                for x in range(0, scene.width, self.grid_size):
                    if x < scene.width and y < scene.height:
                        canvas[y][x] = '·'
        
        # Sort widgets by z_index
        sorted_widgets = sorted(enumerate(scene.widgets), key=lambda w: w[1].z_index)
        
        # Draw widgets
        for idx, widget in sorted_widgets:
            if not widget.visible:
                continue
            # Apply state overrides and animation preview on a copy
            eff = copy.deepcopy(widget)
            self._apply_state_overrides_inplace(eff)
            self._apply_animation_preview_inplace(eff, idx, scene)
            self._render_widget_to_canvas(canvas, eff, idx, scene.width, scene.height)

        # Draw magnetic guides if enabled
        if self.show_guides and self.last_guides:
            for g in self.last_guides:
                if g.get('type') == 'v':
                    x = g['x']
                    for y in range(max(0, g['y1']), min(scene.height, g['y2'] + 1)):
                        if 0 <= x < scene.width:
                            canvas[y][x] = '┆'
                elif g.get('type') == 'h':
                    y = g['y']
                    for x in range(max(0, g['x1']), min(scene.width, g['x2'] + 1)):
                        if 0 <= y < scene.height:
                            canvas[y][x] = '┄'
        
        # Convert to string
        lines = [''.join(row) for row in canvas]
        return '\n'.join(lines)
    
    def _render_widget_to_canvas(self, canvas: List[List[str]], widget: WidgetConfig, 
                                 idx: int, width: int, height: int):
        """Render single widget to canvas"""
        # Get border characters based on style
        border_chars = self._get_border_chars(widget.border_style)
        
        # Draw border
        if widget.border:
            self._draw_border(canvas, widget, border_chars, width, height)
        
        # Draw widget-specific content
        if widget.type == 'progressbar':
            self._draw_progressbar(canvas, widget, width, height)
        elif widget.type == 'gauge':
            self._draw_gauge(canvas, widget, width, height)
        elif widget.type == 'checkbox':
            self._draw_checkbox(canvas, widget, width, height)
        elif widget.type == 'slider':
            self._draw_slider(canvas, widget, width, height)
        elif widget.type == 'chart':
            self._draw_chart(canvas, widget, width, height)
        else:
            # Draw text for label, button, etc.
            if widget.text:
                self._draw_text(canvas, widget, width, height)
        
        # Draw widget index (top-left corner inside border)
        num_str = str(idx)
        num_y = widget.y if not widget.border else widget.y + 1
        num_x = widget.x + 1
        if 0 <= num_y < height:
            self._write_text_line(canvas, num_y, num_x, num_str, width)

    def _draw_border(self, canvas: List[List[str]], widget: WidgetConfig, border_chars: Dict[str, str], width: int, height: int) -> None:
        """Draw widget border with bounds checks."""
        x0, y0 = widget.x, widget.y
        x1 = widget.x + widget.width - 1
        y1 = widget.y + widget.height - 1
        # Top/bottom
        for x in range(max(0, x0), min(x1 + 1, width)):
            if 0 <= y0 < height:
                canvas[y0][x] = border_chars['h']
            if 0 <= y1 < height:
                canvas[y1][x] = border_chars['h']
        # Left/right
        for y in range(max(0, y0), min(y1 + 1, height)):
            if 0 <= x0 < width:
                canvas[y][x0] = border_chars['v']
            if 0 <= x1 < width:
                canvas[y][x1] = border_chars['v']
        # Corners
        if 0 <= y0 < height and 0 <= x0 < width:
            canvas[y0][x0] = border_chars['tl']
        if 0 <= y0 < height and 0 <= x1 < width:
            canvas[y0][x1] = border_chars['tr']
        if 0 <= y1 < height and 0 <= x0 < width:
            canvas[y1][x0] = border_chars['bl']
        if 0 <= y1 < height and 0 <= x1 < width:
            canvas[y1][x1] = border_chars['br']

    def _write_text_line(self, canvas: List[List[str]], y: int, x_start: int, text: str, width: int) -> None:
        """Write a text string to a single canvas row with bounds checks."""
        if not (0 <= y < len(canvas)):
            return
        for i, ch in enumerate(text):
            x = x_start + i
            if 0 <= x < width:
                canvas[y][x] = ch

    def _apply_state_overrides_inplace(self, widget: WidgetConfig) -> None:
        try:
            overrides = (widget.state_overrides or {}).get(widget.state or 'default')
            if overrides:
                for k, v in overrides.items():
                    if hasattr(widget, k):
                        try:
                            setattr(widget, k, type(getattr(widget, k))(v))
                        except Exception:
                            setattr(widget, k, v)
        except Exception:
            pass

    def _apply_animation_preview_inplace(self, widget: WidgetConfig, idx: int, scene: SceneConfig) -> None:
        ctx = self.anim_context
        if not ctx:
            return
        if ctx.get('idx') != idx:
            return
        name = (ctx.get('name') or '').lower()
        t = int(ctx.get('t', 0))
        steps = max(1, int(ctx.get('steps', 10)))
        try:
            if name == 'bounce':
                import math
                amp = max(1, min(3, scene.height // 10))
                dy = int(round(amp * math.sin(2 * math.pi * (t % steps) / steps)))
                widget.y = max(0, min(scene.height - widget.height, widget.y + dy))
            elif name == 'slideinleft':
                # from -width .. to current x
                start = -widget.width
                end = widget.x
                pos = start + (end - start) * (t % steps) / steps
                widget.x = max(-widget.width, min(scene.width - 1, int(pos)))
            elif name == 'pulse':
                # Toggle border style for visual emphasis
                if (t % 2) == 0:
                    widget.border_style = 'bold'
                else:
                    widget.border_style = 'single'
            elif name == 'fadein':
                # Simulate by switching style
                if (t % 2) == 0:
                    widget.style = 'highlight'
                else:
                    widget.style = 'default'
        except Exception:
            pass
    
    def _get_border_chars(self, style: str) -> Dict[str, str]:
        """Get border characters for style"""
        styles = {
            'single': {'h': '─', 'v': '│', 'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘'},
            'double': {'h': '═', 'v': '║', 'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝'},
            'rounded': {'h': '─', 'v': '│', 'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯'},
            'bold': {'h': '━', 'v': '┃', 'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛'},
            'dashed': {'h': '┄', 'v': '┆', 'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘'},
        }
        return styles.get(style, styles['single'])
    
    def _draw_text(self, canvas: List[List[str]], widget: WidgetConfig, 
                   width: int, height: int):
        """Draw text with alignment"""
        text_y = widget.y + widget.height // 2
        if widget.valign == 'top':
            text_y = widget.y + (1 if widget.border else 0) + widget.padding_y
        elif widget.valign == 'bottom':
            text_y = widget.y + widget.height - (1 if widget.border else 0) - widget.padding_y - 1
        
        text_x = widget.x + widget.padding_x + (1 if widget.border else 0)
        
        if widget.align == 'center':
            text_x = widget.x + (widget.width - len(widget.text)) // 2
        elif widget.align == 'right':
            text_x = widget.x + widget.width - len(widget.text) - widget.padding_x - (1 if widget.border else 0)
        
        if 0 <= text_y < height:
            self._write_text_line(canvas, text_y, text_x, widget.text, width)
    
    def _draw_progressbar(self, canvas: List[List[str]], widget: WidgetConfig,
                          width: int, height: int):
        """Draw progress bar"""
        inner_width = widget.width - (2 if widget.border else 0)
        progress = int((widget.value / max(widget.max_value, 1)) * inner_width)
        
        bar_y = widget.y + widget.height // 2
        bar_x_start = widget.x + (1 if widget.border else 0)
        
        if 0 <= bar_y < height:
            for i in range(inner_width):
                x = bar_x_start + i
                if 0 <= x < width:
                    canvas[bar_y][x] = '█' if i < progress else '░'
    
    def _draw_gauge(self, canvas: List[List[str]], widget: WidgetConfig,
                    width: int, height: int):
        """Draw gauge (simple bar)"""
        inner_height = widget.height - (2 if widget.border else 0)
        progress = int((widget.value / max(widget.max_value, 1)) * inner_height)
        
        gauge_x = widget.x + widget.width // 2
        gauge_y_start = widget.y + widget.height - (1 if widget.border else 0) - 1
        
        for i in range(inner_height):
            y = gauge_y_start - i
            if 0 <= y < height and 0 <= gauge_x < width:
                canvas[y][gauge_x] = '█' if i < progress else '░'
    
    def _draw_checkbox(self, canvas: List[List[str]], widget: WidgetConfig,
                       width: int, height: int):
        """Draw checkbox"""
        check_y = widget.y + widget.height // 2
        check_x = widget.x + (1 if widget.border else 0) + 1
        
        if 0 <= check_y < height and 0 <= check_x < width:
            canvas[check_y][check_x] = '☑' if widget.checked else '☐'
        
        # Draw label if text exists
        if widget.text and 0 <= check_y < height:
            text_x = check_x + 2
            for i, ch in enumerate(widget.text):
                x = text_x + i
                if 0 <= x < width:
                    canvas[check_y][x] = ch
    
    def _draw_slider(self, canvas: List[List[str]], widget: WidgetConfig,
                     width: int, height: int):
        """Draw slider"""
        inner_width = widget.width - (2 if widget.border else 0)
        slider_pos = int((widget.value / max(widget.max_value, 1)) * (inner_width - 1))
        
        slider_y = widget.y + widget.height // 2
        slider_x_start = widget.x + (1 if widget.border else 0)
        
        if 0 <= slider_y < height:
            for i in range(inner_width):
                x = slider_x_start + i
                if 0 <= x < width:
                    if i == slider_pos:
                        canvas[slider_y][x] = '▓'
                    else:
                        canvas[slider_y][x] = '─'
    
    def _draw_chart(self, canvas: List[List[str]], widget: WidgetConfig,
                    width: int, height: int):
        """Draw simple chart"""
        if not widget.data_points:
            return
        
        inner_width = widget.width - (2 if widget.border else 0)
        inner_height = widget.height - (2 if widget.border else 0)
        
        # Normalize data points
        max_val = max(widget.data_points) if widget.data_points else 1
        
        chart_x_start = widget.x + (1 if widget.border else 0)
        chart_y_start = widget.y + (1 if widget.border else 0)
        
        # Draw bars
        for i, val in enumerate(widget.data_points[:inner_width]):
            bar_height = int((val / max(max_val, 1)) * inner_height)
            x = chart_x_start + i
            
            for j in range(bar_height):
                y = chart_y_start + inner_height - 1 - j
                if 0 <= y < height and 0 <= x < width:
                    canvas[y][x] = '▌'


def _preflight_scene(scene: SceneConfig) -> Dict[str, Any]:
    """Run basic preflight checks and return results dict."""
    issues: List[str] = []
    warnings: List[str] = []
    n = len(scene.widgets)
    for i, w in enumerate(scene.widgets):
        if w.width < 1 or w.height < 1:
            issues.append(f"[{i}] {w.type}: invalid size {w.width}x{w.height}")
        if w.x < 0 or w.y < 0 or (w.x + w.width) > scene.width or (w.y + w.height) > scene.height:
            issues.append(f"[{i}] {w.type}: off-canvas pos=({w.x},{w.y}) size={w.width}x{w.height}")
        if w.type in ['label','button','textbox','checkbox','radiobutton'] and not (w.text or '').strip():
            warnings.append(f"[{i}] {w.type}: empty text")
    def overlap(a: WidgetConfig, b: WidgetConfig) -> bool:
        return not (a.x + a.width <= b.x or b.x + b.width <= a.x or a.y + a.height <= b.y or b.y + b.height <= a.y)
    for i in range(n):
        for j in range(i+1, n):
            if overlap(scene.widgets[i], scene.widgets[j]):
                warnings.append(f"[{i}] {scene.widgets[i].type} overlaps [{j}] {scene.widgets[j].type}")
    return {
        'issues': issues,
        'warnings': warnings,
        'ok': not issues,
        'counts': {'issues': len(issues), 'warnings': len(warnings), 'widgets': n}
    }

def _auto_preflight_and_export(designer: 'UIDesigner', json_path: str) -> None:
    """Run preflight and generate HTML/PNG next to the JSON file."""
    try:
        if not designer.current_scene or designer.current_scene not in designer.scenes:
            return
        scene = designer.scenes[designer.current_scene]
        result = _preflight_scene(scene)
        counts = result['counts']
        print("\n🔎 Preflight:")
        if counts['issues']:
            for m in result['issues'][:10]:
                print(f"  [fail] {m}")
        if counts['warnings']:
            for m in result['warnings'][:10]:
                print(f"  [warn] {m}")
        print(f"  Summary: {counts['widgets']} widgets | {counts['issues']} issues | {counts['warnings']} warnings")
    except Exception as e:
        print(f"⚠️ Preflight failed: {e}")

    try:
        base, _ = os.path.splitext(json_path)
        out_html = base + '.html'
        out_png = base + '.png'
        designer.export_to_html(out_html)
        try:
            import subprocess, sys as _sys
            cmd = [
                _sys.executable,
                PREVIEW_SCRIPT,
                '--headless-preview', '--in-json', json_path, '--out-png', out_png, '--out-html', out_html
            ]
            subprocess.run(cmd, check=False)
        except Exception:
            pass
        print(f"🖼️ Auto-export: {out_html} | {out_png}")
    except Exception as e:
        print(f"⚠️ Auto-export failed: {e}")

def create_cli_interface(commands: Optional[List[str]] = None):
    """Advanced CLI interface for UI designer.
    If 'commands' is provided, runs non-interactively executing each command in order.
    """
    designer = UIDesigner(128, 64)
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   ESP32 UI Designer - Advanced CLI Mode                  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print("📐 Scene Management:")
    print("  new <name>              - Create new scene")
    print("  list                    - List widgets in current scene")
    print("  scenes                  - List all scenes")
    print("  switch <name>           - Switch to scene")
    print()
    print("🎨 Widget Operations:")
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
    print("🎯 Advanced Features:")
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
    print("💾 File Operations:")
    print("  save <file>             - Save to JSON")
    print("  load <file>             - Load from JSON")
    print("  export <file>           - Export Python code")
    print("  restore [latest|list|<index>] - Restore from autosave snapshot")
    print("  checkpoint <name>       - Create a named checkpoint of current scene")
    print("  checkpoints             - List named checkpoints")
    print("  rollback <name>         - Restore the scene from a checkpoint")
    print("  diff <A> [B]            - Diff checkpoints A and B (or A vs current)")
    print()
    print("👥 Groups:")
    print("  group create <name> <idx...>   - Create a group")
    print("  group add <name> <idx...>      - Add widgets to group")
    print("  group remove <name> <idx...>   - Remove widgets from group")
    print("  group delete <name>            - Delete a group")
    print("  group list                     - List groups")
    print("  group lock <name> <on|off|toggle>    - Lock/unlock all members")
    print("  group visible <name> <on|off|toggle> - Show/hide all members")
    print()
    print("🔁 Symbols:")
    print("  symbol save <name> <idx...>    - Save selection as a symbol")
    print("  symbol list                    - List saved symbols")
    print("  symbol place <name> <x> <y>    - Place a symbol instance")
    print()
    print("🎨 Themes & WCAG:")
    print("  theme list                    - List theme presets")
    print("  theme set <name>              - Set scene theme and bg color")
    print("  theme bind <idx> <fg|bg> <role> - Bind widget color to role")
    print("  theme apply                   - Apply bound theme roles to widgets")
    print("  contrast [min]                - Audit contrast (optionally set min, e.g., 4.5)")
    print()
    print("❓ Help & Info:")
    print("  help [command]          - Show help")
    print("  widgets                 - List available widget types")
    print("  quit                    - Exit")
    print()
    print("💡 Widget types: label, box, button, gauge, progressbar,")
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
            if action == 'quit' or action == 'exit':
                break
            
            elif action == 'new':
                if len(parts) < 2:
                    print("Usage: new <scene_name>")
                    continue
                designer.create_scene(parts[1])
                print(f"✓ Created scene: {parts[1]}")
            
            elif action == 'scenes':
                if designer.scenes:
                    print("\n📋 Available scenes:")
                    for name in designer.scenes:
                        marker = " (current)" if name == designer.current_scene else ""
                        print(f"  - {name}{marker}")
                else:
                    print("No scenes created")
            
            elif action == 'switch':
                if len(parts) < 2:
                    print("Usage: switch <scene_name>")
                    continue
                if parts[1] in designer.scenes:
                    designer.current_scene = parts[1]
                    print(f"✓ Switched to scene: {parts[1]}")
                else:
                    print(f"❌ Scene '{parts[1]}' not found")
            
            # Widget Operations
            elif action == 'add':
                if len(parts) < 6:
                    print("Usage: add <type> <x> <y> <w> <h> [text]")
                    continue
                
                widget = WidgetConfig(
                    type=parts[1],
                    x=int(parts[2]),
                    y=int(parts[3]),
                    width=int(parts[4]),
                    height=int(parts[5]),
                    text=' '.join(parts[6:]) if len(parts) > 6 else ""
                )
                designer.add_widget(widget)
                print(f"✓ Added {widget.type} widget")
            
            elif action == 'template':
                if len(parts) < 5:
                    print("Usage: template <name> <id> <x> <y>")
                    continue
                designer.add_widget_from_template(parts[1], parts[2], int(parts[3]), int(parts[4]))
                print(f"✓ Added widget '{parts[2]}' from template: {parts[1]}")
            
            elif action == 'clone':
                if len(parts) < 2:
                    print("Usage: clone <idx> [offset_x] [offset_y]")
                    continue
                offset_x = int(parts[2]) if len(parts) > 2 else 10
                offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), offset_x, offset_y)
                print("✓ Widget cloned")
            
            elif action == 'duplicate':
                if len(parts) < 2:
                    print("Usage: duplicate <idx> [dx] [dy]")
                    continue
                _offset_x = int(parts[2]) if len(parts) > 2 else 10
                _offset_y = int(parts[3]) if len(parts) > 3 else 10
                designer.clone_widget(int(parts[1]), _offset_x, _offset_y)
                print("✓ Widget duplicated")
            
            elif action == 'move':
                if len(parts) < 4:
                    print("Usage: move <idx> <dx> <dy>")
                    continue
                designer.move_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("✓ Widget moved")
            
            elif action == 'resize':
                if len(parts) < 4:
                    print("Usage: resize <idx> <dw> <dh>")
                    continue
                designer.resize_widget(int(parts[1]), int(parts[2]), int(parts[3]))
                print("✓ Widget resized")
            
            elif action == 'delete':
                if len(parts) < 2:
                    print("Usage: delete <idx>")
                    continue
                designer.delete_widget(int(parts[1]))
                print("✓ Widget deleted")

            elif action == 'lock':
                if len(parts) < 3:
                    print("Usage: lock <idx> <on|off|toggle>")
                    continue
                _idx = int(parts[1])
                _mode = parts[2].lower()
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        if _mode == 'on':
                            scene.widgets[_idx].locked = True
                        elif _mode == 'off':
                            scene.widgets[_idx].locked = False
                        elif _mode == 'toggle':
                            scene.widgets[_idx].locked = not scene.widgets[_idx].locked
                        else:
                            print("Usage: lock <idx> <on|off|toggle>")
                            continue
                        state = '🔒' if scene.widgets[_idx].locked else '🔓'
                        print(f"✓ Widget {_idx} {state}")

            elif action == 'select':
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
                        print(f"✓ Selected widget [{_idx}] {scene.widgets[_idx].type}")
                    else:
                        print("Invalid index")
            
            elif action == 'edit':
                if len(parts) < 4:
                    print("Usage: edit <idx> <property> <value>")
                    continue
                _idx = int(parts[1])
                _prop = parts[2]
                _value = ' '.join(parts[3:])
                
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    if 0 <= _idx < len(scene.widgets):
                        # Save state before edit
                        _state = json.dumps(asdict(scene))
                        designer.undo_stack.append(_state)
                        designer.redo_stack.clear()
                        
                        widget = scene.widgets[_idx]
                        
                        # Set property
                        if _prop in ['x', 'y', 'width', 'height', 'value', 'min_value', 'max_value', 'z_index']:
                            setattr(widget, _prop, int(_value))
                        elif _prop in ['checked', 'enabled', 'visible', 'border']:
                            setattr(widget, _prop, _value.lower() in ['true', '1', 'yes'])
                        else:
                            setattr(widget, _prop, _value)
                        
                        print(f"✓ Updated {_prop} = {_value}")
            
            # Advanced Features
            elif action == 'undo':
                if designer.undo():
                    print("✓ Undone")
                else:
                    print("❌ Nothing to undo")
            
            elif action == 'redo':
                if designer.redo():
                    print("✓ Redone")
                else:
                    print("❌ Nothing to redo")
            
            elif action == 'grid':
                if len(parts) < 2:
                    print(f"Grid is {'enabled' if designer.grid_enabled else 'disabled'}")
                elif parts[1].lower() in ['on', 'true', '1']:
                    designer.grid_enabled = True
                    print("✓ Grid enabled")
                else:
                    designer.grid_enabled = False
                    print("✓ Grid disabled")
            
            elif action == 'snap':
                if len(parts) < 2:
                    print(f"Snap to grid is {'enabled' if designer.snap_to_grid else 'disabled'}")
                elif parts[1].lower() in ['on', 'true', '1']:
                    designer.snap_to_grid = True
                    print("✓ Snap to grid enabled")
                else:
                    designer.snap_to_grid = False
                    print("✓ Snap to grid disabled")

            elif action == 'guides':
                if len(parts) < 2:
                    print(f"Guides overlay is {'on' if designer.show_guides else 'off'}")
                elif parts[1].lower() in ['on', 'true', '1']:
                    designer.show_guides = True
                    print("✓ Guides enabled")
                else:
                    designer.show_guides = False
                    print("✓ Guides disabled")

            elif action == 'snaptol':
                if len(parts) < 2:
                    print(f"Snap tolerance: {designer.snap_tolerance} px")
                else:
                    try:
                        designer.snap_tolerance = max(0, int(parts[1]))
                        print(f"✓ Snap tolerance set to {designer.snap_tolerance} px")
                    except Exception:
                        print("Usage: snaptol <pixels>")

            elif action == 'snapmode':
                if len(parts) < 2:
                    mode = 'fluid' if designer.snap_fluid else 'pixel'
                    print(f"Snap mode: {mode}")
                else:
                    val = parts[1].lower()
                    if val in ['pixel','strict']:
                        designer.snap_fluid = False
                        print("✓ Snap mode: pixel (grid-first)")
                    elif val in ['fluid','magnetic']:
                        designer.snap_fluid = True
                        print("✓ Snap mode: fluid (magnetic-first)")
                    else:
                        print("Usage: snapmode <pixel|fluid>")
            
            elif action == 'list':
                if designer.current_scene:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\n📋 Scene: {scene.name} ({scene.width}x{scene.height})")
                    print(f"Widgets: {len(scene.widgets)}\n")
                    for i, w in enumerate(scene.widgets):
                        border_info = f" border={w.border_style}" if w.border else ""
                        value_info = f" value={w.value}" if w.type in ['gauge', 'progressbar', 'slider'] else ""
                        lock_info = " 🔒" if getattr(w, 'locked', False) else ""
                        print(f"  [{i}] {w.type:12s} pos=({w.x:3d},{w.y:3d}) size={w.width:3d}x{w.height:3d}{border_info}{value_info}{lock_info}")
                        if w.text:
                            print(f"       text='{w.text}'")
                else:
                    print("No scene loaded")
            
            elif action == 'preview':
                show_grid = len(parts) > 1 and parts[1].lower() == 'grid'
                print("\n" + designer.preview_ascii(show_grid=show_grid))
                print()
            
            elif action == 'templates':
                print("\n📦 Available templates:")
                for name, template in designer.templates.items():
                    print(f"  {name:20s} - {template.type} {template.width}x{template.height}")
                print()
            
            elif action == 'widgets':
                print("\n🎨 Available widget types:")
                for wtype in WidgetType:
                    print(f"  - {wtype.value}")
                print()

            # Theme & WCAG
            elif action == 'theme':
                if len(parts) < 2:
                    print("Usage: theme <list|set|bind|apply> ...")
                    continue
                sub = parts[1].lower()
                if sub == 'list':
                    print("\n🎨 Themes:")
                    for name, roles in sorted(designer.themes.items()):
                        print(f"  - {name:8s} bg={roles.get('bg')} text={roles.get('text')} primary={roles.get('primary')}")
                    print()
                elif sub == 'set':
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
                        sc.bg_color = designer.themes[name].get('bg', sc.bg_color)
                        print(f"✓ Theme set: {name}")
                elif sub == 'bind':
                    if len(parts) < 5:
                        print("Usage: theme bind <idx> <fg|bg> <role>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    _which = parts[3].lower()
                    _role = parts[4]
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        if 0 <= _idx < len(_sc.widgets):
                            if _which == 'fg':
                                _sc.widgets[_idx].theme_fg_role = _role
                            elif _which == 'bg':
                                _sc.widgets[_idx].theme_bg_role = _role
                            else:
                                print("Use fg or bg")
                                continue
                            print("✓ Theme role bound")
                elif sub == 'apply':
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        _roles = designer.themes.get(_sc.theme, designer.themes['default'])
                        for _w in _sc.widgets:
                            if _w.theme_fg_role:
                                _w.color_fg = _roles.get(_w.theme_fg_role, _w.color_fg)
                            if _w.theme_bg_role:
                                _w.color_bg = _roles.get(_w.theme_bg_role, _w.color_bg)
                        # Apply bg to preview HTML via scene.bg_color; ASCII unaffected
                        print("✓ Theme applied to bound widgets")
                else:
                    print("Unknown theme subcommand")

            elif action == 'contrast':
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
                        if getattr(_w, 'visible', True) and (_w.text or _w.type in ['label','button','textbox','checkbox','radiobutton']):
                            _r = _contrast_ratio(_w.color_fg, _w.color_bg)
                            if _r < _min_ratio:
                                _issues += 1
                                print(f"  [low] [{_i}] {_w.type}: contrast={_r:.2f} (fg={_w.color_fg}, bg={_w.color_bg})")
                                if _sc.contrast_lock:
                                    # Try swapping to scene theme text color for better contrast
                                    _roles = designer.themes.get(_sc.theme, designer.themes['default'])
                                    _candidate = _roles.get('text', _w.color_fg)
                                    if _contrast_ratio(_candidate, _w.color_bg) >= _min_ratio:
                                        _w.color_fg = _candidate
                                        print(f"       -> adjusted fg to {_candidate}")
                    if _issues == 0:
                        print(f"✓ All text meets contrast >= {_min_ratio}")
                    else:
                        print(f"⚠️  {_issues} items below contrast {_min_ratio}")

            elif action == 'tree':
                if designer.current_scene and designer.current_scene in designer.scenes:
                    scene = designer.scenes[designer.current_scene]
                    print(f"\n🌲 Tree for scene: {scene.name}")
                    if designer.groups:
                        print("\nGroups:")
                        for gname, members in designer.list_groups():
                            mem_str = ', '.join(str(i) for i in members)
                            print(f"  - {gname}: [{mem_str}]")
                    else:
                        print("(no groups)")
                    print("\nWidgets:")
                    for i, w in enumerate(scene.widgets):
                        tags = []
                        for gname, mem in designer.groups.items():
                            if i in mem:
                                tags.append(gname)
                        tag_str = f" groups={','.join(tags)}" if tags else ""
                        lock_info = " 🔒" if getattr(w, 'locked', False) else ""
                        vis_info = " (hidden)" if not getattr(w, 'visible', True) else ""
                        print(f"  [{i}] {w.type} at ({w.x},{w.y}) {w.width}x{w.height}{tag_str}{lock_info}{vis_info}")
                    print()
                else:
                    print("No scene loaded")
            
            # File Operations
            elif action == 'save':
                if len(parts) < 2:
                    print("Usage: save <file>")
                    continue
                designer.save_to_json(parts[1])
                # Note: save_to_json already triggers preflight/auto-export by default
            
            elif action == 'load':
                if len(parts) < 2:
                    print("Usage: load <file>")
                    continue
                designer.load_from_json(parts[1])
            elif action == 'restore':
                # Autosave restore utility
                backup_dir = Path.home() / ".esp32os" / "designer_backups"
                snaps = []
                if backup_dir.exists():
                    snaps = sorted(backup_dir.glob("*.json"))
                if not snaps:
                    print("No snapshots found")
                    continue
                if len(parts) == 1 or parts[1] == 'list':
                    print("\n📦 Snapshots:")
                    for i, p in enumerate(snaps):
                        print(f"  [{i}] {p.name}")
                    print()
                    continue
                _idx = -1
                if parts[1] == 'latest':
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
                        with open(snaps[_idx], 'r', encoding='utf-8') as _f:
                            _state = json.load(_f)
                        _name = _state.get('name', 'restored')
                        designer.scenes[_name] = SceneConfig(
                            name=_name,
                            width=int(_state.get('width', designer.width)),
                            height=int(_state.get('height', designer.height)),
                            widgets=[WidgetConfig(**_w) for _w in _state.get('widgets', [])],
                            bg_color=_state.get('bg_color', 'black'),
                        )
                        designer.current_scene = _name
                        # Show quick diff summary if previous scene exists in undo
                        if designer.undo_stack:
                            try:
                                _prev = json.loads(designer.undo_stack[-1])
                                _pw = len(_prev.get('widgets', []))
                                _cw = len(_state.get('widgets', []))
                                print(f"✓ Restored snapshot {snaps[_idx].name} (widgets: {_pw} -> {_cw})")
                            except Exception:
                                print(f"✓ Restored snapshot {snaps[_idx].name}")
                        else:
                            print(f"✓ Restored snapshot {snaps[_idx].name}")
                    except Exception as e:
                        print(f"❌ Failed to restore: {e}")
                else:
                    print("Invalid index")
            
            elif action == 'export':
                if len(parts) < 2:
                    print("Usage: export <file> [html]")
                    continue
                if len(parts) > 2 and parts[2].lower() == 'html':
                    designer.export_to_html(parts[1])
                else:
                    designer.export_code(parts[1])

            # Groups
            elif action == 'group':
                if len(parts) < 2:
                    print("Usage: group <create|add|remove|delete|list|lock|visible> ...")
                    continue
                _sub = parts[1].lower()
                if _sub == 'list':
                    _groups = designer.list_groups()
                    if not _groups:
                        print("No groups")
                    else:
                        print("\n👥 Groups:")
                        for _name, _members in _groups:
                            print(f"  - {_name:20s} [{', '.join(map(str, _members))}]")
                        print()
                elif _sub in ['create','add','remove']:
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
                    if _sub == 'create':
                        _ok = designer.create_group(_name, _idxs)
                    elif _sub == 'add':
                        _ok = designer.add_to_group(_name, _idxs)
                    else:
                        _ok = designer.remove_from_group(_name, _idxs)
                    print("✓ Done" if _ok else "❌ Failed")
                elif sub == 'delete':
                    if len(parts) < 3:
                        print("Usage: group delete <name>")
                        continue
                    print("✓ Deleted" if designer.delete_group(parts[2]) else "❌ Failed")
                elif sub in ['lock','visible']:
                    if len(parts) < 4:
                        print(f"Usage: group {sub} <name> <on|off|toggle>")
                        continue
                    _name = parts[2]
                    _mode = parts[3].lower()
                    if sub == 'lock':
                        _ok = designer.group_set_lock(_name, _mode)
                    else:
                        _ok = designer.group_set_visible(_name, _mode)
                    print("✓ Done" if _ok else "❌ Failed")
                else:
                    print("Unknown group subcommand")

            # Symbols
            elif action == 'symbol':
                if len(parts) < 2:
                    print("Usage: symbol <save|list|place> ...")
                    continue
                _sub = parts[1].lower()
                if _sub == 'list':
                    if not designer.symbols:
                        print("No symbols")
                    else:
                        print("\n🔁 Symbols:")
                        for _name, _spec in sorted(designer.symbols.items()):
                            _w, _h = _spec.get('size', (0,0))
                            print(f"  - {_name:20s} size={_w}x{_h} items={len(_spec.get('items', []))}")
                        print()
                elif _sub == 'save':
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
                    print("✓ Saved" if _ok else "❌ Failed to save symbol")
                elif _sub == 'place':
                    if len(parts) < 5:
                        print("Usage: symbol place <name> <x> <y>")
                        continue
                    _name = parts[2]
                    try:
                        _x = int(parts[3]); _y = int(parts[4])
                    except Exception:
                        print("x/y must be integers")
                        continue
                    _ok = designer.place_symbol(_name, _x, _y)
                    print("✓ Placed" if _ok else "❌ Failed to place symbol")
                else:
                    print("Unknown symbol subcommand")
            
            elif action == 'checkpoint':
                if len(parts) < 2:
                    print("Usage: checkpoint <name>")
                    continue
                _ok = designer.create_checkpoint(parts[1])
                if _ok:
                    print(f"✓ Checkpoint created: {parts[1]}")
                else:
                    print("❌ Failed to create checkpoint (no scene loaded?)")

            elif action == 'checkpoints':
                cps = designer.list_checkpoints()
                if not cps:
                    print("No checkpoints")
                else:
                    print("\n🗂️  Checkpoints:")
                    for name, ts in cps:
                        print(f"  - {name:20s} {ts}")
                    print()

            elif action == 'rollback':
                if len(parts) < 2:
                    print("Usage: rollback <name>")
                    continue
                if designer.rollback_checkpoint(parts[1]):
                    print(f"✓ Rolled back to checkpoint: {parts[1]}")
                else:
                    print("❌ Failed to rollback (unknown checkpoint?)")

            elif action == 'diff':
                if len(parts) < 2:
                    print("Usage: diff <A> [B]")
                    continue
                _name_a = parts[1]
                _name_b = parts[2] if len(parts) > 2 else None
                if _name_a not in designer.checkpoints:
                    print("Unknown checkpoint A")
                    continue
                _a = designer.checkpoints[_name_a]['scene']
                if _name_b:
                    if _name_b not in designer.checkpoints:
                        print("Unknown checkpoint B")
                        continue
                    _b = designer.checkpoints[_name_b]['scene']
                else:
                    _cur = designer._current_scene_state()
                    if not _cur:
                        print("No current scene to diff against")
                        continue
                    _b = _cur
                _d = designer._diff_states(_a, _b)
                _ca = _d['widgets']['count']['a']
                _cb = _d['widgets']['count']['b']
                print("\n🔍 Diff:")
                print(f"  Scene A: {_d['scene']['a']}  size={_d['size']['a']}  widgets={_ca}")
                print(f"  Scene B: {_d['scene']['b']}  size={_d['size']['b']}  widgets={_cb}")
                if _d['widgets']['added']:
                    print(f"  + Added indices in B: {_d['widgets']['added']}")
                if _d['widgets']['removed']:
                    print(f"  - Removed indices from A: {_d['widgets']['removed']}")
                if _d['widgets']['changed']:
                    print(f"  ~ Changed widgets: {len(_d['widgets']['changed'])}")
                    for _ch in _d['widgets']['changed'][:10]:
                        _ix = _ch['index']
                        _keys = ', '.join(list(_ch['changes'].keys())[:6])
                        print(f"     [{_ix}] fields: {_keys}{' ...' if len(_ch['changes'])>6 else ''}")
                else:
                    print("  No property changes in matching indices")
                print()
            
            elif action == 'layout':
                if len(parts) < 2:
                    print("Usage: layout <vertical|horizontal|grid> [spacing]")
                    continue
                _spacing = int(parts[2]) if len(parts) > 2 else 4
                designer.auto_layout(parts[1], _spacing)
                print(f"✓ Applied {parts[1]} layout")
            
            elif action == 'align':
                if len(parts) < 3:
                    print("Usage: align <left|right|top|bottom|center_h|center_v> <idx1> [idx2...]")
                    continue
                _indices = [int(_x) for _x in parts[2:]]
                designer.align_widgets(parts[1], _indices)
                print(f"✓ Aligned {len(_indices)} widgets ({parts[1]})")
            
            elif action == 'distribute':
                if len(parts) < 4:
                    print("Usage: distribute <horizontal|vertical> <idx1> <idx2> [idx3...]")
                    continue
                _indices = [int(_x) for _x in parts[2:]]
                designer.distribute_widgets(parts[1], _indices)
                print(f"✓ Distributed {len(_indices)} widgets ({parts[1]})")

            elif action == 'gridcols':
                if len(parts) < 2:
                    print(f"Grid columns: {designer.grid_columns} (grid size {designer.grid_size})")
                else:
                    try:
                        _n = int(parts[1])
                        designer.set_grid_columns(_n)
                        print(f"✓ Grid columns set to {designer.grid_columns} (grid size {designer.grid_size})")
                    except Exception:
                        print("Usage: gridcols <4|8|12>")

            elif action == 'bp':
                if len(parts) < 2:
                    print("Usage: bp <WxH>  (e.g., 128x64, 240x135, 320x240)")
                    continue
                try:
                    _wh = parts[1].lower().split('x')
                    _w = int(_wh[0]); _h = int(_wh[1])
                    if designer.current_scene and designer.current_scene in designer.scenes:
                        _sc = designer.scenes[designer.current_scene]
                        _sc.width = _w; _sc.height = _h
                        print(f"✓ Breakpoint applied: {_w}x{_h}")
                except Exception:
                    print("Usage: bp <WxH>")

            elif action == 'resp':
                if len(parts) < 2:
                    print("Usage: resp <base|apply>")
                    continue
                _sub = parts[1].lower()
                if _sub == 'base':
                    designer.set_responsive_base()
                    print("✓ Responsive base recorded")
                elif _sub == 'apply':
                    designer.apply_responsive()
                    print("✓ Responsive constraints applied")
                else:
                    print("Usage: resp <base|apply>")
            
            elif action == 'state':
                if len(parts) < 2:
                    print("Usage: state <define|set|list|clear> ...")
                    continue
                if not (designer.current_scene and designer.current_scene in designer.scenes):
                    print("No scene loaded")
                    continue
                _sub = parts[1].lower()
                _scene = designer.scenes[designer.current_scene]
                if _sub == 'define':
                    if len(parts) < 5:
                        print("Usage: state define <idx> <name> k=v [k=v]...")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _w = _scene.widgets[_idx]
                    _w.state_overrides = _w.state_overrides or {}
                    _cur = dict(_w.state_overrides.get(_name, {}))
                    for _kv in parts[4:]:
                        if '=' in _kv:
                            _k, _v = _kv.split('=', 1)
                            _cur[_k] = _v
                    _w.state_overrides[_name] = _cur
                    print(f"✓ State '{_name}' overrides defined for widget {_idx}")
                elif _sub == 'set':
                    if len(parts) < 4:
                        print("Usage: state set <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _scene.widgets[_idx].state = _name
                    print(f"✓ Widget {_idx} state set to '{_name}'")
                elif _sub == 'list':
                    if len(parts) < 3:
                        print("Usage: state list <idx>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _w = _scene.widgets[_idx]
                    _keys = sorted((_w.state_overrides or {}).keys())
                    _cur = _w.state or 'default'
                    if not _keys:
                        print(f"(no overrides). Current state: {_cur}")
                    else:
                        print(f"States for widget {_idx} (current: {_cur}): {', '.join(_keys)}")
                elif _sub == 'clear':
                    if len(parts) < 4:
                        print("Usage: state clear <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    _name = parts[3]
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _w = _scene.widgets[_idx]
                    if _name in (_w.state_overrides or {}):
                        del _w.state_overrides[_name]
                        print(f"✓ Removed state '{_name}' from widget {_idx}")
                    else:
                        print("No such state override")
                else:
                    print("Unknown state subcommand")

            elif action == 'anim':
                if len(parts) < 2:
                    print("Usage: anim <list|add|clear|preview|play> ...")
                    continue
                _sub = parts[1].lower()
                _builtins = ['bounce', 'slideinleft', 'pulse', 'fadein']
                if _sub == 'list':
                    print("\n🎞️  Animations:")
                    for _n in _builtins:
                        print(f"  - {_n}")
                    print()
                    continue
                if not (designer.current_scene and designer.current_scene in designer.scenes):
                    print("No scene loaded")
                    continue
                _scene = designer.scenes[designer.current_scene]
                if _sub == 'add':
                    if len(parts) < 4:
                        print("Usage: anim add <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    _name = parts[3].lower()
                    if _name not in _builtins:
                        print("Unknown animation name")
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _w = _scene.widgets[_idx]
                    if _name not in (_w.animations or []):
                        _w.animations.append(_name)
                    print(f"✓ Animation '{_name}' tagged on widget {_idx}")
                elif _sub == 'clear':
                    if len(parts) < 4:
                        print("Usage: anim clear <idx> <name>")
                        continue
                    try:
                        _idx = int(parts[2])
                    except Exception:
                        print("Index must be integer")
                        continue
                    _name = parts[3].lower()
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _w = _scene.widgets[_idx]
                    if _name in (_w.animations or []):
                        _w.animations = [_a for _a in (_w.animations or []) if _a != _name]
                        print(f"✓ Animation '{_name}' removed from widget {_idx}")
                    else:
                        print("Animation not tagged on widget")
                elif _sub == 'preview':
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
                        print("Unknown animation name")
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    # Set context, render once, then clear
                    designer.anim_context = {'idx': _idx, 'name': _name, 'steps': _steps, 't': _t}
                    print("\n" + designer.preview_ascii())
                    print()
                    designer.anim_context = None
                elif _sub == 'play':
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
                        print("Unknown animation name")
                        continue
                    if not (0 <= _idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    import time
                    try:
                        for _t in range(max(1, _steps)):
                            designer.anim_context = {'idx': _idx, 'name': _name, 'steps': _steps, 't': _t}
                            print(f"\n[# {_t+1}/{_steps}] {_name}\n")
                            print(designer.preview_ascii())
                            time.sleep(max(0, _delay_ms) / 1000.0)
                    except KeyboardInterrupt:
                        print("\n⏹️  Animation stopped")
                    finally:
                        designer.anim_context = None
                else:
                    print("Unknown anim subcommand")
            
            elif action == 'context':
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
                        print("Select a widget first with 'select <idx>' or pass an index: context <idx>")
                        continue
                    if not (0 <= _target_idx < len(_scene.widgets)):
                        print("Invalid index")
                        continue
                    _w = _scene.widgets[_target_idx]
                    _info = get_widget_help(_w)
                    print(f"\n🧩 Context: [{_target_idx}] {_w.type}")
                    print(f"   Size: {_w.width}x{_w.height} at ({_w.x},{_w.y})  Style: {_w.style}  Align: {_w.align}")
                    if getattr(_w, 'text', ''):
                        print(f"   Text: '{_w.text}'")
                    if getattr(_w, 'locked', False):
                        print(f"   State: 🔒 locked (use: lock {_target_idx} off)")
                    print(f"\n📖 About: {_info.get('description','N/A')}")
                    _tips = _info.get('tips', [])
                    if _tips:
                        print("🔧 Tips:")
                        for _t in _tips:
                            print(f"   - {_t}")
                    _qa = [
                        f"duplicate {_target_idx} 8 8",
                        f"align left {_target_idx} <idx2> [idx3...]",
                        f"distribute horizontal {_target_idx} <idx2> [idx3...]",
                        f"lock {_target_idx} toggle",
                    ]
                    print("\n⚡ Quick actions:")
                    for _a in _qa:
                        print(f"   > {_a}")
                    print()
                else:
                    print("No scene loaded")
            
            elif action == 'help':
                if len(parts) > 1:
                    show_command_help(parts[1])
                else:
                    print("Type command name for help. Available: add, template, edit, grid, layout, etc.")
            
            else:
                print(f"❌ Unknown command: {action}. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def show_command_help(command: str):
    """Show detailed help for specific command"""
    helps = {
        'add': """
Add widget: add <type> <x> <y> <w> <h> [text]
  Examples:
    add label 10 10 100 10 "Hello World"
    add button 20 30 40 12 "Click Me"
    add progressbar 10 50 100 8
    add gauge 60 20 40 30
        """,
        'template': """
Add from template: template <name> <x> <y>
  Available templates: title_label, button_primary, button_secondary,
                       info_panel, progress_bar, gauge_half
  Example: template button_primary 20 30
        """,
        'edit': """
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
        'label': {
            'description': 'Static text. Use for titles, captions, and inline hints.',
            'tips': [
                "Use align=center for titles; turn off border for clean headers",
                "Increase padding_x on narrow labels to avoid cramped text",
                "Keep contrast high (color_fg vs color_bg) for readability",
            ],
        },
        'button': {
            'description': 'Clickable action. Prefer concise verbs (OK, Save, Back).',
            'tips': [
                "Keep height >= 10 for legibility on small screens",
                "Use rounded/double border to indicate primary/secondary",
                "Align a group with align left/right; use distribute horizontal",
            ],
        },
        'progressbar': {
            'description': 'Linear progress indicator for completion percentage.',
            'tips': [
                "Use full width minus margins for dashboard layouts",
                "Set min/max bounds consistently across related bars",
            ],
        },
        'gauge': {
            'description': 'Vertical bar gauge for a single numeric value.',
            'tips': [
                "Group multiple gauges and distribute horizontally",
                "Show current value elsewhere; keep gauge visuals minimal",
            ],
        },
        'checkbox': {
            'description': 'Binary toggle with a label.',
            'tips': [
                "Ensure text is non-empty for accessibility",
                "Align left with other inputs for neat forms",
            ],
        },
        'radiobutton': {
            'description': 'Mutually exclusive options within a group.',
            'tips': [
                "Stack vertically; use distribute vertical to space evenly",
                "Group with a surrounding panel for clarity",
            ],
        },
        'textbox': {
            'description': 'Editable text input.',
            'tips': [
                "Ensure width is sufficient for expected content",
                "Use a label above with smaller padding",
            ],
        },
        'panel': {
            'description': 'Container/background for grouping elements.',
            'tips': [
                "Use double/bold border for emphasis",
                "Set z_index lower than foreground widgets",
            ],
        },
        'icon': {
            'description': 'Single-character icon glyph.',
            'tips': [
                "Pair with a label; align center for symmetry",
            ],
        },
        'chart': {
            'description': 'Compact bar chart for small datasets.',
            'tips': [
                "Limit categories to fit inner width",
                "Consider labels elsewhere to keep chart readable",
            ],
        },
        'box': {
            'description': 'Generic rectangle. Useful as spacer or divider.',
            'tips': [
                "Use dashed/bold borders to separate sections",
            ],
        },
        'slider': {
            'description': 'Adjustable control for a numeric range.',
            'tips': [
                "Reserve adequate width; show current value nearby",
            ],
        },
    }
    return base.get(wtype, {'description': 'Generic widget.', 'tips': []})

# --- Theme & WCAG helpers ---

_NAMED_COLORS = {
    'black': (0,0,0), 'white': (255,255,255), 'red': (255,0,0), 'green': (0,128,0),
    'blue': (0,0,255), 'yellow': (255,255,0), 'cyan': (0,255,255), 'magenta': (255,0,255),
    'gray': (128,128,128), 'grey': (128,128,128), 'orange': (255,165,0), 'purple': (128,0,128),
}

def _parse_color(c: str) -> Tuple[int,int,int]:
    c = (c or '').strip().lower()
    if c in _NAMED_COLORS:
        return _NAMED_COLORS[c]
    if c.startswith('#'):
        h = c[1:]
        if len(h) == 6:
            try:
                return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))
            except Exception:
                return (0,0,0)
    return (0,0,0)

def _rel_lum(rgb: Tuple[int,int,int]) -> float:
    def f(u: float) -> float:
        u = u/255.0
        return (u/12.92) if (u <= 0.03928*255) else pow((u+0.055)/1.055, 2.4)
    r,g,b = rgb
    return 0.2126*f(r) + 0.7152*f(g) + 0.0722*f(b)

def _contrast_ratio(fg: str, bg: str) -> float:
    L1 = _rel_lum(_parse_color(fg))
    L2 = _rel_lum(_parse_color(bg))
    lmax, lmin = (max(L1,L2), min(L1,L2))
    return (lmax + 0.05) / (lmin + 0.05)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="UI Designer CLI")
    parser.add_argument('--web', action='store_true', help='Start web interface (not implemented)')
    parser.add_argument('--guided', action='store_true', help='Run guided wizard for quick scene creation')
    parser.add_argument('--demo', action='store_true', help='Generate a demo scene showcasing states and animations')
    parser.add_argument('--script-file', default='', help='Run CLI commands from a file (one per line)')
    parser.add_argument('--preset', default='', help='Screen preset: dashboard|menu|dialog')
    parser.add_argument('--export', action='store_true', help='Export after guided flow')
    parser.add_argument('--out-json', default='examples/guided_scene.json')
    parser.add_argument('--out-html', default='examples/guided_scene.html')
    parser.add_argument('--out-png', default='examples/guided_scene.png')
    args = parser.parse_args()

    if args.web:
        print("🌐 Web interface not yet implemented")
        print("   Use CLI mode for now")
        sys.exit(0)

    if args.guided:
        # Minimal guided flow
        d = UIDesigner(128, 64)
        print("\n🧭 Guided mode: Choose a preset [dashboard/menu/dialog]")
        preset = args.preset or input("Preset (dashboard): ").strip().lower() or 'dashboard'
        scene_name = input("Scene name (Home): ").strip() or 'Home'
        try:
            w = int(input("Width (128): ") or '128')
            h = int(input("Height (64): ") or '64')
        except Exception:
            w, h = 128, 64
        d.width, d.height = w, h
        d.create_scene(scene_name)
        # Apply preset templates
        if preset == 'dashboard':
            d.add_widget(WidgetType.LABEL, x=0, y=0, width=w, height=10, text=scene_name, border=False, align='center', style='bold', color_fg='cyan')
            d.add_widget(WidgetType.GAUGE, x=4, y=14, width=w//3, height=h//2, value=72)
            d.add_widget(WidgetType.GAUGE, x=w//3 + 8, y=14, width=w//3, height=h//2, value=42)
            d.add_widget(WidgetType.PROGRESSBAR, x=4, y=h-14, width=w-8, height=8, value=60)
            d.add_widget(WidgetType.BUTTON, x=w-48, y=2, width=44, height=10, text='Menu')
        elif preset == 'menu':
            d.add_widget(WidgetType.LABEL, x=0, y=0, width=w, height=10, text=scene_name, border=False, align='center', style='bold')
            y = 14
            for label in ["Start", "Settings", "About"]:
                d.add_widget(WidgetType.BUTTON, x=(w-60)//2, y=y, width=60, height=12, text=label)
                y += 14
        else:  # dialog
            d.add_widget(WidgetType.PANEL, x=6, y=10, width=w-12, height=h-20)
            d.add_widget(WidgetType.LABEL, x=10, y=14, width=w-20, height=8, text="Confirm action?", align='center')
            d.add_widget(WidgetType.BUTTON, x=w//2-44, y=h-18, width=40, height=12, text='OK')
            d.add_widget(WidgetType.BUTTON, x=w//2+4, y=h-18, width=40, height=12, text='Cancel')

        # Export flow
        out_json = args.out_json
        out_html = args.out_html
        out_png = args.out_png
        Path(os.path.dirname(out_json)).mkdir(parents=True, exist_ok=True)
        # Save triggers preflight + auto-export by default
        d.save_to_json(out_json)
        # Ensure HTML/PNG at requested paths as well
        try:
            d.export_to_html(out_html)
        except Exception:
            pass
        try:
            import subprocess, sys as _sys
            cmd = [
                _sys.executable,
                PREVIEW_SCRIPT,
                '--headless-preview', '--in-json', out_json, '--out-png', out_png, '--out-html', out_html
            ]
            subprocess.run(cmd, check=False)
        except Exception:
            pass
        print(f"\n✅ Guided scene created and exported:\n  JSON: {out_json}\n  HTML: {out_html}\n  PNG:  {out_png}")
        sys.exit(0)

    if args.demo:
        # Build a small demo scene with state variants and an animation
        d = UIDesigner(128, 64)
        d.create_scene('Demo')
        w, h = 128, 64
        # Title
        d.add_widget(WidgetType.LABEL, x=0, y=0, width=w, height=10, text='Demo', border=False, align='center', style='bold', color_fg='cyan')
        # Button with states
        d.add_widget(WidgetType.BUTTON, x=(w-50)//2, y=16, width=50, height=12, text='Play')
        # Gauge and progress bar
        d.add_widget(WidgetType.GAUGE, x=8, y=14, width=32, height=24, value=70)
        d.add_widget(WidgetType.PROGRESSBAR, x=8, y=h-12, width=w-16, height=8, value=40)
        sc = d.scenes[d.current_scene]
        # Define button states
        btn = sc.widgets[1]
        btn.state_overrides = {
            'hover': {'style': 'bold', 'color_bg': '#222'},
            'active': {'style': 'inverse', 'color_bg': '#444'},
            'disabled': {'enabled': False, 'style': 'default'}
        }
        btn.state = 'default'
        # Tag animation and set preview context for export consistency
        btn.animations.append('bounce')
        # Use provided out paths or default under examples/demo_*
        out_json = args.out_json if args.out_json != 'examples/guided_scene.json' else 'examples/demo_scene.json'
        out_html = args.out_html if args.out_html != 'examples/guided_scene.html' else 'examples/demo_scene.html'
        out_png  = args.out_png  if args.out_png  != 'examples/guided_scene.png' else 'examples/demo_scene.png'
        Path(os.path.dirname(out_json)).mkdir(parents=True, exist_ok=True)
        # Save triggers preflight + auto-export
        d.save_to_json(out_json)
        # Ensure HTML/PNG at requested paths as well
        try:
            d.export_to_html(out_html)
        except Exception:
            pass
        try:
            import subprocess, sys as _sys
            cmd = [
                _sys.executable,
                PREVIEW_SCRIPT,
                '--headless-preview', '--in-json', out_json, '--out-png', out_png, '--out-html', out_html
            ]
            subprocess.run(cmd, check=False)
        except Exception:
            pass
        print(f"\n✅ Demo scene created and exported:\n  JSON: {out_json}\n  HTML: {out_html}\n  PNG:  {out_png}")
        sys.exit(0)

    # Scripted CLI mode
    if args.script_file:
        try:
            with open(args.script_file, 'r', encoding='utf-8') as f:
                lines = [ln.strip() for ln in f.readlines()]
            # Drop blanks and comments
            lines = [ln for ln in lines if ln and not ln.lstrip().startswith('#')]
            create_cli_interface(commands=lines)
            sys.exit(0)
        except Exception as e:
            print(f"❌ Failed to run script file: {e}")
            sys.exit(1)

    create_cli_interface()
