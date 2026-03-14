#pragma once

#include "ui_render.h"  /* UiDrawOps, UiWidget */

/*
 * Individual widget renderers extracted from ui_render.c.
 * Each takes a single widget + draw ops and renders it fully.
 * No scene state, no hardware — pure drawing logic.
 */

void ui_render_label(const UiWidget *w, const UiDrawOps *ops);
void ui_render_button(const UiWidget *w, const UiDrawOps *ops);
void ui_render_panel(const UiWidget *w, const UiDrawOps *ops);
void ui_render_box(const UiWidget *w, const UiDrawOps *ops);
void ui_render_textbox(const UiWidget *w, const UiDrawOps *ops);
void ui_render_progressbar(const UiWidget *w, const UiDrawOps *ops);
void ui_render_checkbox(const UiWidget *w, const UiDrawOps *ops);
void ui_render_radiobutton(const UiWidget *w, const UiDrawOps *ops);
void ui_render_slider(const UiWidget *w, const UiDrawOps *ops);
void ui_render_gauge(const UiWidget *w, const UiDrawOps *ops);
void ui_render_icon(const UiWidget *w, const UiDrawOps *ops);
void ui_render_chart(const UiWidget *w, const UiDrawOps *ops);
void ui_render_list(const UiWidget *w, const UiDrawOps *ops);
void ui_render_toggle(const UiWidget *w, const UiDrawOps *ops);
