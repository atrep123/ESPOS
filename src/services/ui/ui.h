#pragma once


#include <stdbool.h>
#include <stdint.h>

/* Runtime UI service for SSD1363 (256x128).
 *
 * Responsibilities:
 *  - subscribe to input events (TOP_INPUT_BTN),
 *  - manage focus/navigation,
 *  - render the current UiScene into a software framebuffer,
 *  - flush only dirty regions to the SSD1363 panel (I2C-friendly).
 */
void ui_start(void);
void ui_stop(void);

/* UI commands (thread-safe): publish requests to the UI task via msgbus. */
void ui_cmd_set_text(const char *id, const char *text);
void ui_cmd_set_visible(const char *id, bool visible);
void ui_cmd_set_enabled(const char *id, bool enabled);
void ui_cmd_set_prefix_visible(const char *root, bool visible);
void ui_cmd_set_style(const char *id, uint8_t style);
void ui_cmd_set_value(const char *id, int value);
void ui_cmd_set_checked(const char *id, bool checked);

void ui_cmd_menu_set_active(const char *root, int active_index);
void ui_cmd_list_set_active(const char *root, int active_index);
void ui_cmd_tabs_set_active(const char *root, int active_index);

/* Virtualized list/menu models: use absolute indices + viewport scrolling. */
void ui_cmd_listmodel_set_len(const char *root, int count);
void ui_cmd_listmodel_set_item(const char *root, int index, const char *label, const char *value);
void ui_cmd_listmodel_set_active(const char *root, int active_index);

void ui_cmd_dialog_show(const char *root);
void ui_cmd_dialog_hide(const char *root);

void ui_cmd_toast_enqueue(const char *root, const char *message, uint32_t duration_ms);
void ui_cmd_toast_hide(const char *root);

/* Scene switching (multi-scene designs). */
void ui_cmd_switch_scene(int scene_index);
