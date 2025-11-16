#pragma once

/* Render the exported UI demo scene once to the SSD1363 panel.
 * Safe to call even if I2C pins are placeholders; will no-op on errors. */
void ui_demo_render_once(void);

/* Start a lightweight render loop task (~20 FPS) that continuously renders
 * the exported scene and a tiny animated overlay, flushing only dirty regions.
 * Safe to call multiple times (creates at most one task). */
void ui_demo_start(void);
