#pragma once

/* Simple application layer on top of the UI runtime:
 * - manages screen stack (menu -> list -> edit)
 * - reacts to TOP_UI_ACTION + B/back inputs
 * - populates list models via ui_cmd_listmodel_*
 */
void ui_app_start(void);

