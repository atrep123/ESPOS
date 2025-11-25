#!/usr/bin/env python3
"""
UI Exporter: Produce demo JSON/HTML/PNG and C headers/sources for firmware
- Generates a small demo scene (or uses presets)
- Writes output/ui_demo.* by default
- Writes src/ui_design.h and src/ui_design.c for firmware integration
"""

import argparse
import json
import os
from typing import Tuple

from ui_designer import UIDesigner, WidgetType

# Template engine for C code generation
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

# Optional PNG export using PIL (headless, no Tk)
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)

_COLOR_MAP = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray": (128, 128, 128),
}

def _get_rgb(name_or_hex: str):
    if not name_or_hex:
        return (255, 255, 255)
    if name_or_hex.startswith('#'):
        return _hex_to_rgb(name_or_hex)
    return _COLOR_MAP.get(name_or_hex.lower(), (255, 255, 255))


def _render_progressbar_png(draw, x, y, wd, ht, widget, fgc):
    """Render progressbar widget to PNG."""
    inner = max(0, wd - 4)
    prog = 0
    if (widget.max_value - widget.min_value) != 0:
        ratio = (widget.value - widget.min_value) / (widget.max_value - widget.min_value)
        prog = int(ratio * inner)
    if prog > 0:
        draw.rectangle([x + 2, y + 2, x + 2 + prog, y + ht - 3], fill=fgc)


def _render_checkbox_png(draw, x, y, ht, widget, fgc):
    """Render checkbox widget to PNG."""
    box = min(ht - 4, 8)
    bx, by = x + 2, y + (ht - box) // 2
    draw.rectangle([bx, by, bx + box, by + box], outline=fgc)
    if widget.checked:
        draw.line([(bx + 1, by + 1), (bx + box - 1, by + box - 1)], fill=fgc)
        draw.line([(bx + 1, by + box - 1), (bx + box - 1, by + 1)], fill=fgc)


def _render_text_placeholder_png(draw, x, y, wd, ht, fgc):
    """Render simple text placeholder to PNG."""
    cy = y + ht // 2
    draw.line([(x + 2, cy), (x + wd - 3, cy)], fill=fgc)


def _render_widget_background_png(draw, x, y, wd, ht, widget, bgc, fgc):
    """Render widget background and border to PNG."""
    draw.rectangle([x, y, x + wd - 1, y + ht - 1], fill=bgc)
    if widget.border:
        draw.rectangle([x, y, x + wd - 1, y + ht - 1], outline=fgc, width=1)


def export_png_from_scene(designer: UIDesigner, filename: str, bg="#000000"):
    if not PIL_AVAILABLE:
        print("[warn] PIL not available; skipping PNG export")
        return False
    if not designer.current_scene:
        return False
    scene = designer.scenes.get(designer.current_scene)
    if not scene:
        return False

    img = Image.new("RGB", (scene.width, scene.height), _hex_to_rgb(bg))
    draw = ImageDraw.Draw(img)

    for w in scene.widgets:
        if not w.visible:
            continue
        x, y, wd, ht = w.x, w.y, w.width, w.height
        # None-safety: ensure dimensions are valid
        if wd is None or ht is None or wd <= 0 or ht <= 0:
            continue
        bgc = _get_rgb(w.color_bg)
        fgc = _get_rgb(w.color_fg)
        
        # Background and border
        _render_widget_background_png(draw, x, y, wd, ht, w, bgc, fgc)
        
        # Widget-specific content
        if w.type == WidgetType.PROGRESSBAR.value:
            _render_progressbar_png(draw, x, y, wd, ht, w, fgc)
        elif w.type == WidgetType.CHECKBOX.value:
            _render_checkbox_png(draw, x, y, ht, w, fgc)
        elif w.text:
            _render_text_placeholder_png(draw, x, y, wd, ht, fgc)
    
    # scale up 4x for easier viewing
    img = img.resize((scene.width * 4, scene.height * 4), Image.NEAREST)
    img.save(filename)
    return True


def escape_c_string(s: str) -> str:
    return s.replace('\\', r'\\').replace('"', r'\"')


def _generate_widget_declaration(widget, str_index, str_consts, type_code_fn):
    """Generate C declaration for a single widget.
    
    Returns: (widget_line, updated_str_index)
    """
    txt_name = "NULL"
    constr_name = "NULL"
    anims_name = "NULL"
    
    if widget.text:
        cname = f"TXT_{str_index}"
        str_index += 1
        str_consts.append(f'static const char {cname}[] = "{escape_c_string(widget.text)}";\n')
        txt_name = cname
    
    # constraints JSON (if present)
    w_constraints = getattr(widget, 'constraints', None)
    if w_constraints:
        import json
        cjson = json.dumps(w_constraints, separators=(',', ':'), ensure_ascii=True)
        cname = f"CSTR_{str_index}"
        str_index += 1
        str_consts.append(f'static const char {cname}[] = "{escape_c_string(cjson)}";\n')
        constr_name = cname
    
    # animations CSV (if present)
    w_anims = getattr(widget, 'animations', None) or []
    if w_anims:
        csv = ';'.join([str(a) for a in w_anims])
        cname = f"ANIM_{str_index}"
        str_index += 1
        str_consts.append(f'static const char {cname}[] = "{escape_c_string(csv)}";\n')
        anims_name = cname
    
    widget_line = (
        "    { "
        f"{type_code_fn(widget.type)}, {widget.x}, {widget.y}, {widget.width}, {widget.height}, "
        f"{1 if widget.border else 0}, {1 if widget.checked else 0}, "
        f"{widget.value}, {widget.min_value}, {widget.max_value}, "
        f"{txt_name}, {constr_name}, {anims_name} "
        "},\n"
    )
    
    return widget_line, str_index


def _build_string_pool():
    """Create string pool and return pool list and reference function."""
    str_pool: list[str] = []
    str_map: dict[str, int] = {}  # value -> index
    
    def get_str_ref(val: str) -> str:
        """Get reference to string in pool, or NULL."""
        if not val:
            return "NULL"
        if val not in str_map:
            str_map[val] = len(str_pool)
            # Escape C string
            escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            str_pool.append(f'"{escaped}"')
        return f"str_{str_map[val]}"
    
    return str_pool, get_str_ref


def _build_widget_data_list(scene, get_str_ref):
    """Build widget data list for template rendering."""
    widget_data = []
    for w in scene.widgets:
        constraints_ref = (
            get_str_ref(w.constraints_json)
            if hasattr(w, 'constraints_json') and w.constraints_json
            else "NULL"
        )
        animations_ref = (
            get_str_ref(w.animations_csv)
            if hasattr(w, 'animations_csv') and w.animations_csv
            else "NULL"
        )
        widget_data.append({
            "type": w.type,
            "x": w.x,
            "y": w.y,
            "width": w.width or 0,
            "height": w.height or 0,
            "border": 1 if w.border else 0,
            "checked": 1 if w.checked else 0,
            "value": w.value,
            "min_value": w.min_value,
            "max_value": w.max_value,
            "text": w.text or "",
            "text_ref": get_str_ref(w.text),
            "constraints_ref": constraints_ref,
            "animations_ref": animations_ref
        })
    return widget_data


def export_c_templated(designer: UIDesigner, base_name: str = "ui_design"):
    """Export C code using Jinja2 templates (cleaner, more maintainable)."""
    if not JINJA2_AVAILABLE:
        print("Warning: jinja2 not available, falling back to legacy export")
        return export_c(designer, base_name)
    
    if not designer.current_scene:
        raise RuntimeError("No current scene to export")
    scene = designer.scenes[designer.current_scene]

    os.makedirs("src", exist_ok=True)
    
    # Widget type mapping
    types = [
        ("label",), ("box",), ("button",), ("gauge",), ("progressbar",),
        ("checkbox",), ("radiobutton",), ("slider",), ("textbox",),
        ("panel",), ("icon",), ("chart",)
    ]
    
    # Setup Jinja2 environment
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Build string pool and widget data
    str_pool, get_str_ref = _build_string_pool()
    widget_data = _build_widget_data_list(scene, get_str_ref)
    
    # Prepare template context
    context = {
        "base_name": base_name,
        "scene_name": scene.name,
        "scene_width": scene.width,
        "scene_height": scene.height,
        "widget_count": len(scene.widgets),
        "widget_types": [(name, i) for i, (name,) in enumerate(types)],
        "string_pool": str_pool,
        "widgets": widget_data
    }
    
    # Render templates
    h_template = env.get_template("ui_design.h.j2")
    c_template = env.get_template("ui_design.c.j2")
    
    h_content = h_template.render(context)
    c_content = c_template.render(context)
    
    # Write files
    h_path = os.path.join("src", f"{base_name}.h")
    c_path = os.path.join("src", f"{base_name}.c")
    
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(h_content)
    with open(c_path, "w", encoding="utf-8") as f:
        f.write(c_content)
    
    print(f"[C Export] Template-based export -> {h_path}, {c_path}")
    print(f"  Scene: {scene.name} ({scene.width}x{scene.height})")
    print(f"  Widgets: {len(scene.widgets)}")
    print(f"  String pool: {len(str_pool)} unique strings")


def export_c(designer: UIDesigner, base_name: str = "ui_design"):
    if not designer.current_scene:
        raise RuntimeError("No current scene to export")
    scene = designer.scenes[designer.current_scene]

    os.makedirs("src", exist_ok=True)
    h_path = os.path.join("src", f"{base_name}.h")
    c_path = os.path.join("src", f"{base_name}.c")

    # Enum mapping
    types = [
        ("label",), ("box",), ("button",), ("gauge",), ("progressbar",),
        ("checkbox",), ("radiobutton",), ("slider",), ("textbox",),
        ("panel",), ("icon",), ("chart",)
    ]
    
    def type_code(t: str) -> int:
        for i, (nm,) in enumerate(types):
            if nm == t:
                return i
        return 0

    # Generate enum lines
    enum_lines = ["typedef enum {\n"]
    for i, (name,) in enumerate(types):
        enum_lines.append(f"    UIW_{name.upper()} = {i},\n")
    enum_lines.append("} UiWidgetType;\n\n")

    header = f"""
#ifndef UI_DESIGN_H
#define UI_DESIGN_H
#include <stdint.h>
    #define UI_ENABLE_CONSTRAINTS 1
    #define UI_ENABLE_ANIMATIONS  1
#ifdef __cplusplus
extern "C" {{
#endif

{''.join(enum_lines)}

typedef struct {{
    uint8_t  type;      // UiWidgetType
    uint16_t x, y;
    uint16_t width, height;
    uint8_t  border;
    uint8_t  checked;
    int16_t  value, min_value, max_value;
    const char* text;
    const char* constraints_json; // optional constraints metadata
    const char* animations_csv;   // optional animations list (semicolon-separated)
}} UiWidget;

typedef struct {{
    const char* name;
    uint16_t width, height;
    uint16_t widget_count;
    const UiWidget* widgets;
}} UiScene;

extern const UiWidget UI_WIDGETS_{scene.name.upper()}[];
extern const UiScene  UI_SCENE_{scene.name.upper()};

#ifdef __cplusplus
}}
#endif
#endif // UI_DESIGN_H
""".lstrip()

    # Generate widget declarations
    str_consts: list[str] = []
    widgets_lines = [f"const UiWidget UI_WIDGETS_{scene.name.upper()}[] = {{\n"]
    str_index = 0

    for w in scene.widgets:
        widget_line, str_index = _generate_widget_declaration(w, str_index, str_consts, type_code)
        widgets_lines.append(widget_line)
    
    widgets_lines.append("};\n\n")

    source = f"""
#include "{base_name}.h"

{''.join(str_consts)}
{''.join(widgets_lines)}
const UiScene UI_SCENE_{scene.name.upper()} = {{
    "{scene.name}", {scene.width}, {scene.height}, \
(uint16_t)(sizeof(UI_WIDGETS_{scene.name.upper()})/sizeof(UI_WIDGETS_{scene.name.upper()}[0])), \
UI_WIDGETS_{scene.name.upper()}
}};
""".lstrip()

    with open(h_path, 'w', encoding='utf-8') as f:
        f.write(header)
    with open(c_path, 'w', encoding='utf-8') as f:
        f.write(source)
    print(f"[ok] C export written: {h_path}, {c_path}")


def build_demo_and_export():
    parser = argparse.ArgumentParser(description="UI Exporter with presets")
    parser.add_argument(
        '--preset', default='',
        help='Device preset: esp32_oled_128x64_1bpp | st7789_240x135_4bpp'
    )
    parser.add_argument('--out-dir', default='examples', help='Output directory for artifacts')
    parser.add_argument('--base-name', default='ui_design', help='Base name for C exports in src/')
    args = parser.parse_args()

    presets = {
        'esp32_oled_128x64_1bpp': {'width': 128, 'height': 64, 'bpp': 1},
        'st7789_240x135_4bpp': {'width': 240, 'height': 135, 'bpp': 4},
    }

    cfg = presets.get(args.preset, {'width': 128, 'height': 64, 'bpp': 1})
    d = UIDesigner(cfg['width'], cfg['height'])
    d.create_scene("demo")

    # Title
    d.add_widget(
        WidgetType.LABEL, x=2, y=2, width=124, height=10,
        text="UI Demo", border=False, align="center"
    )
    # Card
    d.add_widget(WidgetType.BOX, x=2, y=14, width=124, height=46, text="", border=True)
    # Button
    d.add_widget(WidgetType.BUTTON, x=8, y=22, width=40, height=12, text="OK", border=True)
    # Progress
    d.add_widget(WidgetType.PROGRESSBAR, x=8, y=38, width=108, height=8, value=70, border=True)
    # Checkbox
    d.add_widget(
        WidgetType.CHECKBOX, x=58, y=24, width=60, height=10,
        text="Enable", checked=True, border=False
    )

    # Output dir for demo artifacts
    out_dir = os.path.join(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Save JSON and HTML
    d.save_to_json(os.path.join(out_dir, "ui_demo.json"))
    d.export_to_html(os.path.join(out_dir, "ui_demo.html"))

    # PNG
    exported = export_png_from_scene(d, os.path.join(out_dir, "ui_demo.png"), bg="#000000")
    if exported:
        print("[ok] PNG exported: output/ui_demo.png")

    # C export - use templated version if jinja2 available
    if JINJA2_AVAILABLE:
        export_c_templated(d, base_name=args.base_name)
    else:
        print("Note: Install jinja2 for cleaner template-based C export")
        export_c(d, base_name=args.base_name)

    # Save used preset
    used_preset = {
        'name': args.preset or 'custom',
        'width': cfg['width'],
        'height': cfg['height'],
        'bpp': cfg['bpp']
    }
    with open(os.path.join(out_dir, 'export_preset_used.json'), 'w', encoding='utf-8') as f:
        json.dump(used_preset, f, indent=2)


if __name__ == "__main__":
    build_demo_and_export()
