#pragma once

#include <stddef.h>
#include <stdint.h>

/* Simple application layer on top of the UI runtime:
 * - manages screen stack (menu -> list -> edit)
 * - reacts to TOP_UI_ACTION + B/back inputs
 * - populates list models via ui_cmd_listmodel_*
 */
void ui_app_start(void);
void ui_app_stop(void);

/* ── Pure helpers (ui_app_logic.c) ── testable without FreeRTOS ── */

/* Format a byte count as human-readable "123M", "45K", or "678B". */
void ui_app_format_heap(char *out, size_t out_cap, uint32_t bytes);

/* Map an INPUT_ID_* to a short display name ("Enc CW", "Up", …). */
const char *ui_app_input_name(uint8_t id);

/* Map an input event to a state string ("press", "hold", "cw", "ccw", "down", "up"). */
const char *ui_app_input_state(uint8_t id, uint8_t pressed);

/* Return 1 if the given input ID is a "back" button (B, any encoder hold). */
int ui_app_is_back_button(uint8_t id);

