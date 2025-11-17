#pragma once

#include "ui_render_swbuf.h"

void ui_scene_icon_demo(display_t *d);
void ui_icon_set_size(uint8_t px);
void ui_icon_set_mode(enum display_blit_mode mode);
void ui_icon_bench(display_t *d, uint32_t count, uint8_t size_px, enum display_blit_mode mode, char *out_json, size_t out_len);
