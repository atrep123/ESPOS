# Image Processing & Font Tools

Comprehensive toolkit for embedded display development, inspired by Lopaka.

## 🎨 Features

### 1. Floyd-Steinberg Dithering (`tools/image_dithering.py`)

High-quality conversion from grayscale/RGB to 1bpp monochrome displays.

**Algorithms:**
- **Floyd-Steinberg**: Best quality, error diffusion to 4 neighbors
- **Atkinson**: Mac-style, 6-neighbor diffusion with error loss
- **Ordered (Bayer)**: Fast, pattern-based, good for textures
- **Threshold**: Simple binary cutoff

**Usage:**
```python
from tools.image_dithering import floyd_steinberg_dither, image_to_xbm

# Dither grayscale image
pixels = [[...]]  # 2D array of 0-255 values
dithered = floyd_steinberg_dither(pixels, width, height)

# Convert to XBM format
width, height, bitmap = image_to_xbm(pixels, width, height, "floyd-steinberg")
```

**Performance:** Processes 64x64 gradients in ~1ms

---

### 2. XBMP Icon Deduplication (`tools/xbmp_dedup.py`)

Reduces code size by 30-50% through bitmap deduplication.

**Features:**
- MD5-based hash deduplication
- Automatic PIL Image support with dithering
- XBM format C code generation

**Usage:**
```python
from tools.xbmp_dedup import XBMPManager
from PIL import Image

xbmp = XBMPManager(default_dither="floyd-steinberg")

# Add icons (auto-deduplicates)
ref1 = xbmp.add_icon_from_pil(image1)
ref2 = xbmp.add_icon_from_pil(image2)

# Generate C code
c_code = xbmp.generate_c_code()
```

**Savings:** Test showed 40% reduction with 2/5 duplicate icons eliminated

---

### 3. BDF Font Support (`tools/bdf_font.py`)

Complete BDF (Bitmap Distribution Format) font parser and renderer.

**Features:**
- Full BDF specification support
- Text rendering to 1bpp bitmaps
- Configurable character spacing
- Font subsetting for minimal code size

**Usage:**
```python
from tools.bdf_font import BDFFont

# Load BDF font
font = BDFFont.load("myfont.bdf")

# Render text
width, height, bitmap = font.render_text("Hello World", spacing=1)

# Get text metrics
text_width = font.get_text_width("Hello", spacing=1)
```

**C Export:**
```python
from tools.bdf_font_export import export_font_to_c, export_font_subset

# Export full font
c_code = export_font_to_c(font, "my_font")

# Export only characters used in text (smaller code)
c_code = export_font_subset(font, "Hello World", "hello_font")
```

**Performance:** 30,000+ renders/sec for short strings

**Font Sources:**
- X11 fonts (misc-fixed, etc.)
- GNU Unifont
- Spleen fonts
- Custom BDF fonts

---

### 4. XBM Utilities (`tools/xbm_utils.py`)

Bitmap manipulation for embedded displays.

**Operations:**

```python
from tools.xbm_utils import *

# Invert (black ↔ white)
inverted = xbm_invert(bitmap, width, height)

# Rotate 90° clockwise
rotated, new_w, new_h = xbm_rotate_90(bitmap, width, height)

# Scale (nearest neighbor)
scaled, new_w, new_h = xbm_scale(bitmap, width, height, scale_x=2, scale_y=2)

# Pixelate effect (mosaic/blocky)
pixelated = xbm_pixelate(bitmap, width, height, pixel_size=4)

# Resize canvas (crop/extend)
resized = xbm_resize_canvas(bitmap, width, height, new_w, new_h, offset_x, offset_y)

# Debug: Convert to ASCII art
ascii_art = xbm_to_ascii(bitmap, width, height)
```

**Pixelate Effect:**
```
Original:         Pixelated (4px):
·····█████·····   ················
····███████····   ····████████····
···█████████···   ····████████····
···█████████···   ····████████····
···█████████···   ····████████····
····███████····   ····████████····
·····█████·····   ················
```

---

## 🔧 Integration with UI Designer

### Template-Based C Export

The UI designer now uses Jinja2 templates for cleaner C code generation:

```python
from tools.ui_export_c import export_c_templated

# Export with templates
export_c_templated(designer, "output_file", scene_name="demo")
```

**Generated Code Structure:**
```c
/* ui_design.h */
typedef enum { UIW_LABEL, UIW_BOX, ... } UiWidgetType;
typedef struct { ... } UiWidget;
extern const UiScene UI_SCENE_DEMO;

/* ui_design.c */
/* Icon bitmaps (deduplicated XBM) */
static const unsigned char icon_bitmap_abc123[] = { ... };

/* String pool (deduplicated) */
static const char str_0[] = "Hello";
static const char str_1[] = "OK";

/* Widget array */
static const UiWidget widgets[] = {
    { // [0] label "Hello"
        .type = UIW_LABEL,
        .x = 0, .y = 0,
        .text = str_0,
        ...
    },
};
```

**Benefits:**
- 30-50% code size reduction (string + bitmap deduplication)
- Clean, readable output
- Easy customization via templates
- Designated initializers (.field = value)

---

## 📊 Performance

| Operation | Performance | Notes |
|-----------|------------|-------|
| Floyd-Steinberg 64x64 | ~1ms | Single-threaded |
| BDF text render | 30,000/sec | Short strings |
| XBMP deduplication | Instant | MD5 hash-based |
| XBM rotate 90° | <1ms | 16x16 bitmap |
| XBM pixelate | <1ms | 32x16, 4px blocks |

---

## 🧪 Testing

All features include comprehensive test suites:

```bash
# Dithering tests
python test_dithering_integration.py

# BDF font tests
python test_bdf_font.py

# XBM utilities tests
python test_xbm_utils.py
```

**Test Coverage:**
- ✅ Dithering algorithms (4 methods)
- ✅ BDF parsing and rendering
- ✅ C code export (full + subset)
- ✅ XBM transformations (rotate, scale, pixelate)
- ✅ Icon deduplication
- ✅ ASCII art preview

---

## 📚 Examples

### Complete Workflow

```python
from PIL import Image
from tools.image_dithering import image_to_xbm
from tools.xbmp_dedup import XBMPManager
from tools.bdf_font import BDFFont
from tools.xbm_utils import xbm_pixelate

# 1. Load and dither image
img = Image.open("logo.png").convert("L")
xbmp = XBMPManager(default_dither="floyd-steinberg")
icon_ref = xbmp.add_icon_from_pil(img)

# 2. Render text with BDF font
font = BDFFont.load("font.bdf")
text_w, text_h, text_bitmap = font.render_text("ESP32", spacing=1)

# 3. Apply pixelate effect
pixelated = xbm_pixelate(text_bitmap, text_w, text_h, pixel_size=2)

# 4. Generate C code
c_code = xbmp.generate_c_code()
with open("assets.c", "w") as f:
    f.write(c_code)
```

---

## 🎯 Lopaka Compatibility

This toolkit implements key features from Lopaka:

| Feature | Lopaka | This Implementation |
|---------|--------|-------------------|
| Floyd-Steinberg dithering | ✅ | ✅ `image_dithering.py` |
| BDF font support | ✅ | ✅ `bdf_font.py` |
| XBM format | ✅ | ✅ Native throughout |
| Bitmap deduplication | ✅ | ✅ `xbmp_dedup.py` |
| Pixelate primitive | ✅ | ✅ `xbm_utils.py` |
| C code export | ✅ | ✅ Template-based |

---

## 📦 Dependencies

**Required:**
- Python 3.10+
- Jinja2 (for template export)

**Optional:**
- Pillow (for PIL Image support in dithering/XBMP)

```bash
pip install jinja2 pillow
```

---

## 🚀 Quick Start

```python
# 1. Install dependencies
pip install jinja2 pillow

# 2. Try dithering demo
python -m tools.image_dithering

# 3. Try BDF font demo
python -m tools.bdf_font

# 4. Try XBM utilities demo
python -m tools.xbm_utils

# 5. Run all tests
python test_dithering_integration.py
python test_bdf_font.py
python test_xbm_utils.py
```

---

## 📝 License

Same as main ESP32OS project.

## 🙏 Credits

Inspired by [Lopaka](https://github.com/sbstjn/lopaka) - Bitmap editor for embedded displays.
