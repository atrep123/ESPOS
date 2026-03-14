#include "ui_dither.h"

const uint8_t ui_bayer4[4][4] = {
    {  0,  8,  2, 10 },
    { 12,  4, 14,  6 },
    {  3, 11,  1,  9 },
    { 15,  7, 13,  5 },
};

void ui_dither_pixel(const UiDrawOps *ops, int x, int y,
                     uint8_t hi, uint8_t lo, int ratio)
{
    uint8_t threshold = ui_bayer4[y & 3][x & 3];
    uint8_t c = ((uint8_t)ratio > threshold) ? hi : lo;
    ui_draw_pixel(ops, x, y, c);
}

void ui_dither_fill_h(const UiDrawOps *ops, int x, int y, int w, int h,
                      uint8_t hi, uint8_t lo)
{
    if (w <= 0 || h <= 0) return;
    for (int col = 0; col < w; ++col) {
        int ratio = (w > 1) ? (int)(((int64_t)col * 16) / (w - 1)) : 16;
        for (int row = 0; row < h; ++row) {
            ui_dither_pixel(ops, x + col, y + row, hi, lo, ratio);
        }
    }
}

void ui_dither_fill_v(const UiDrawOps *ops, int x, int y, int w, int h,
                      uint8_t hi, uint8_t lo)
{
    if (w <= 0 || h <= 0) return;
    for (int row = 0; row < h; ++row) {
        int ratio = (h > 1) ? (int)(((int64_t)(h - 1 - row) * 16) / (h - 1)) : 16;
        for (int col = 0; col < w; ++col) {
            ui_dither_pixel(ops, x + col, y + row, hi, lo, ratio);
        }
    }
}
