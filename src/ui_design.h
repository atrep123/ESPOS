#ifndef UI_DESIGN_H
#define UI_DESIGN_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    UIW_LABEL = 0,
    UIW_BOX = 1,
    UIW_BUTTON = 2,
    UIW_GAUGE = 3,
    UIW_PROGRESSBAR = 4,
    UIW_CHECKBOX = 5,
    UIW_RADIOBUTTON = 6,
    UIW_SLIDER = 7,
    UIW_TEXTBOX = 8,
    UIW_PANEL = 9,
    UIW_ICON = 10,
    UIW_CHART = 11,
} UiWidgetType;



typedef struct {
    uint8_t  type;      // UiWidgetType
    uint16_t x, y;
    uint16_t width, height;
    uint8_t  border;
    uint8_t  checked;
    int16_t  value, min_value, max_value;
    const char* text;
} UiWidget;

typedef struct {
    const char* name;
    uint16_t width, height;
    uint16_t widget_count;
    const UiWidget* widgets;
} UiScene;

extern const UiWidget UI_WIDGETS_DEMO[];
extern const UiScene  UI_SCENE_DEMO;

#ifdef __cplusplus
}
#endif
#endif // UI_DESIGN_H
