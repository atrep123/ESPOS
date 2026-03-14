#include "ui_render.h"

#include "ui_border.h"
#include "ui_render_widgets.h"
#include "ui_theme.h"
#include "ui_widget_style.h"

void ui_render_widget(const UiWidget *w, const UiDrawOps *ops)
{
    if (!w || !ops) return;
    if (!ui_widget_is_visible(w)) {
        return;
    }
    if (w->type >= UIW__COUNT) {
        return;
    }

    switch (w->type) {
        case UIW_LABEL:        ui_render_label(w, ops);        break;
        case UIW_BUTTON:       ui_render_button(w, ops);       break;
        case UIW_BOX:          ui_render_box(w, ops);          break;
        case UIW_PROGRESSBAR:  ui_render_progressbar(w, ops);  break;
        case UIW_CHECKBOX:     ui_render_checkbox(w, ops);     break;
        case UIW_GAUGE:        ui_render_gauge(w, ops);        break;
        case UIW_RADIOBUTTON:  ui_render_radiobutton(w, ops);  break;
        case UIW_SLIDER:       ui_render_slider(w, ops);       break;
        case UIW_TEXTBOX:      ui_render_textbox(w, ops);      break;
        case UIW_PANEL:        ui_render_panel(w, ops);        break;
        case UIW_ICON:         ui_render_icon(w, ops);         break;
        case UIW_CHART:        ui_render_chart(w, ops);        break;
        case UIW_LIST:         ui_render_list(w, ops);         break;
        case UIW_TOGGLE:       ui_render_toggle(w, ops);       break;
        default:
            ui_draw_rect_outline(ops, w->x, w->y, w->width, w->height, UI_COL_BORDER);
            break;
    }
}

void ui_render_scene(const UiScene *scene, const UiDrawOps *ops)
{
    if (!scene || !ops) return;
    for (uint16_t i = 0; i < scene->widget_count; ++i) {
        ui_render_widget(&scene->widgets[i], ops);
    }
}
