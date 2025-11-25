/* Auto-generated font: Simple5x7 */
/* Size: 7pt, Glyphs: 4 */

#include <stdint.h>

/* Font metadata */
typedef struct {
    uint16_t encoding;    /* Unicode code point */
    uint8_t width;        /* Glyph width in pixels */
    uint8_t height;       /* Glyph height in pixels */
    int8_t x_offset;      /* X offset from origin */
    int8_t y_offset;      /* Y offset from baseline */
    uint8_t advance;      /* Horizontal advance */
    const uint8_t *bitmap; /* Pointer to bitmap data */
} BdfGlyph;

typedef struct {
    const char *name;
    uint8_t size;
    uint8_t bbox_w;
    uint8_t bbox_h;
    int8_t bbox_x;
    int8_t bbox_y;
    uint16_t glyph_count;
    const BdfGlyph *glyphs;
} BdfFont;

/* ' ' (U+0020) */
static const uint8_t glyph_32_bitmap[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

/* 'A' (U+0041) */
static const uint8_t glyph_65_bitmap[] = {
    0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x00
};

/* 'B' (U+0042) */
static const uint8_t glyph_66_bitmap[] = {
    0x1E, 0x11, 0x1E, 0x11, 0x11, 0x1E, 0x00
};

/* 'C' (U+0043) */
static const uint8_t glyph_67_bitmap[] = {
    0x0E, 0x11, 0x10, 0x10, 0x11, 0x0E, 0x00
};

static const BdfGlyph simple_font_glyphs[] = {
    { 32, 3, 7, 0, -1, 4, glyph_32_bitmap },
    { 65, 5, 7, 0, -1, 6, glyph_65_bitmap },
    { 66, 5, 7, 0, -1, 6, glyph_66_bitmap },
    { 67, 5, 7, 0, -1, 6, glyph_67_bitmap },
};

const BdfFont simple_font = {
    .name = "Simple5x7",
    .size = 7,
    .bbox_w = 5,
    .bbox_h = 7,
    .bbox_x = 0,
    .bbox_y = -1,
    .glyph_count = 4,
    .glyphs = simple_font_glyphs
};
