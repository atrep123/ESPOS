#!/usr/bin/env python3
"""
UI Exporter: Produce demo JSON/HTML/PNG and C headers/sources for firmware
- Generates a small demo scene (or uses presets)
- Writes examples/ui_demo.* by default
- Writes src/ui_design.h and src/ui_design.c for firmware integration
"""

import os
import json
from dataclasses import asdict
import argparse
from typing import Tuple

from ui_designer import UIDesigner, WidgetType, WidgetConfig

# Optional PNG export using PIL (headless, no Tk)
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

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
        bgc = _get_rgb(w.color_bg)
        fgc = _get_rgb(w.color_fg)
        # background
        draw.rectangle([x, y, x+wd-1, y+ht-1], fill=bgc)
        # border
        if w.border:
            draw.rectangle([x, y, x+wd-1, y+ht-1], outline=fgc, width=1)
        # simple content
        if w.type == WidgetType.PROGRESSBAR.value:
            inner = max(0, wd-4)
            prog = 0
            if (w.max_value - w.min_value) != 0:
                prog = int((w.value - w.min_value) / (w.max_value - w.min_value) * inner)
            if prog > 0:
                draw.rectangle([x+2, y+2, x+2+prog, y+ht-3], fill=fgc)
        elif w.type == WidgetType.CHECKBOX.value:
            box = min(ht-4, 8)
            bx, by = x+2, y+(ht-box)//2
            draw.rectangle([bx, by, bx+box, by+box], outline=fgc)
            if w.checked:
                draw.line([(bx+1,by+1),(bx+box-1,by+box-1)], fill=fgc)
                draw.line([(bx+1,by+box-1),(bx+box-1,by+1)], fill=fgc)
        else:
            # very simple text mark: draw a 1px line to hint content
            if w.text:
                cx = x + wd//2
                cy = y + ht//2
                draw.line([(x+2, cy), (x+wd-3, cy)], fill=fgc)
    # scale up 4x for easier viewing
    img = img.resize((scene.width*4, scene.height*4), Image.NEAREST)
    img.save(filename)
    return True


def escape_c_string(s: str) -> str:
    return s.replace('\\', r'\\').replace('"', r'\"')


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
        ("checkbox",), ("radiobutton",), ("slider",), ("textbox",), ("panel",), ("icon",), ("chart",)
    ]
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

    # Source
    str_consts = []
    widgets_lines = [f"const UiWidget UI_WIDGETS_{scene.name.upper()}[] = {{\n"]
    str_index = 0

    def type_code(t: str) -> int:
        for i, (nm,) in enumerate(types):
            if nm == t:
                return i
        return 0

    for w in scene.widgets:
        txt_name = "NULL"
        constr_name = "NULL"
        anims_name = "NULL"
        if w.text:
            cname = f"TXT_{str_index}"
            str_index += 1
            str_consts.append(f"static const char {cname}[] = \"{escape_c_string(w.text)}\";\n")
            txt_name = cname
        # constraints JSON (if present)
        w_constraints = getattr(w, 'constraints', None)
        if w_constraints:
            import json
            cjson = json.dumps(w_constraints, separators=(',', ':'), ensure_ascii=True)
            cname = f"CSTR_{str_index}"
            str_index += 1
            str_consts.append(f"static const char {cname}[] = \"{escape_c_string(cjson)}\";\n")
            constr_name = cname
        # animations CSV (if present)
        w_anims = getattr(w, 'animations', None) or []
        if w_anims:
            csv = ';'.join([str(a) for a in w_anims])
            cname = f"ANIM_{str_index}"
            str_index += 1
            str_consts.append(f"static const char {cname}[] = \"{escape_c_string(csv)}\";\n")
            anims_name = cname
        widgets_lines.append(
            "    { "
            f"{type_code(w.type)}, {w.x}, {w.y}, {w.width}, {w.height}, "
            f"{1 if w.border else 0}, {1 if w.checked else 0}, {w.value}, {w.min_value}, {w.max_value}, {txt_name}, {constr_name}, {anims_name} "
            "},\n"
        )
    widgets_lines.append("};\n\n")

    source = f"""
#include "{base_name}.h"

{''.join(str_consts)}
{''.join(widgets_lines)}
const UiScene UI_SCENE_{scene.name.upper()} = {{
    "{scene.name}", {scene.width}, {scene.height}, (uint16_t)(sizeof(UI_WIDGETS_{scene.name.upper()})/sizeof(UI_WIDGETS_{scene.name.upper()}[0])), UI_WIDGETS_{scene.name.upper()}
}};
""".lstrip()

    with open(h_path, 'w', encoding='utf-8') as f:
        f.write(header)
    with open(c_path, 'w', encoding='utf-8') as f:
        f.write(source)
    print(f"[ok] C export written: {h_path}, {c_path}")


def build_demo_and_export():
    parser = argparse.ArgumentParser(description="UI Exporter with presets")
    parser.add_argument('--preset', default='', help='Device preset: esp32_oled_128x64_1bpp | st7789_240x135_4bpp')
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
    d.add_widget(WidgetType.LABEL, x=2, y=2, width=124, height=10, text="UI Demo", border=False, align="center")
    # Card
    d.add_widget(WidgetType.BOX, x=2, y=14, width=124, height=46, text="", border=True)
    # Button
    d.add_widget(WidgetType.BUTTON, x=8, y=22, width=40, height=12, text="OK", border=True)
    # Progress
    d.add_widget(WidgetType.PROGRESSBAR, x=8, y=38, width=108, height=8, value=70, border=True)
    # Checkbox
    d.add_widget(WidgetType.CHECKBOX, x=58, y=24, width=60, height=10, text="Enable", checked=True, border=False)

    # Output dir for demo artifacts
    out_dir = os.path.join(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Save JSON and HTML
    d.save_to_json(os.path.join(out_dir, "ui_demo.json"))
    d.export_to_html(os.path.join(out_dir, "ui_demo.html"))

    # PNG
    exported = export_png_from_scene(d, os.path.join(out_dir, "ui_demo.png"), bg="#000000")
    if exported:
        print("[ok] PNG exported: examples/ui_demo.png")

    # C export
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
