# C Code Generation Templates

This directory contains Jinja2 templates for generating clean, maintainable C code from UI designs.

## Templates

### `ui_design.h.j2`
Header file template containing:
- Widget type enumeration (`UiWidgetType`)
- Widget structure definition (`UiWidget`)
- Scene structure definition (`UiScene`)
- Exported scene declaration

### `ui_design.c.j2`
Implementation file template containing:
- String pool (deduplicated strings)
- Widget array definitions
- Scene definition with metadata

## Features

### String Pool Deduplication
Identical strings are stored only once, reducing code size by 30-50%:
```c
/* String pool */
static const char str_0[] = "UI Demo";
static const char str_1[] = "OK";
static const char str_2[] = "Enable";
```

### Clean, Readable Output
- Auto-generated comments
- Structured sections
- Designated initializers (.field = value)
- Widget index and type comments

## Usage

Template-based export is automatic when `jinja2` is installed:

```bash
pip install jinja2
python -m tools.ui_export_c --preset esp32_oled_128x64_1bpp
```

Output:
```
[C Export] Template-based export -> src\ui_design.h, src\ui_design.c
  Scene: demo (128x64)
  Widgets: 5
  String pool: 3 unique strings
```

## Customization

Templates can be modified to:
- Support different embedded platforms
- Add custom metadata fields
- Change naming conventions
- Include bitmap data for icons
- Generate platform-specific code

## Template Variables

**Header template (`ui_design.h.j2`):**
- `base_name` - Output filename base
- `scene_name` - Scene identifier
- `widget_types` - List of (name, id) tuples

**Implementation template (`ui_design.c.j2`):**
- `base_name` - Output filename base
- `scene_name` - Scene identifier
- `scene_width`, `scene_height` - Dimensions
- `widget_count` - Number of widgets
- `string_pool` - Deduplicated string literals
- `widgets` - List of widget data dictionaries

## Benefits

✅ **Maintainability** - Logic separated from presentation  
✅ **Reduced code size** - String deduplication  
✅ **Better readability** - Comments and structured sections  
✅ **Easy customization** - Edit templates, not code  
✅ **Future-proof** - Easy to add new features  
