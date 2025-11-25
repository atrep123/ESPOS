/* Auto-generated header file for demo */
#ifndef UI_DESIGN_H
#define UI_DESIGN_H
#include <stdint.h>

#define UI_ENABLE_CONSTRAINTS 1
#define UI_ENABLE_ANIMATIONS  1

#ifdef __cplusplus
extern "C" {
#endif

/* Widget type enumeration */
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

/* Widget structure */
typedef struct {
    uint8_t  type;      // UiWidgetType
    uint16_t x, y;
    uint16_t width, height;
    uint8_t  border;
    uint8_t  checked;
    int16_t  value, min_value, max_value;
    const char* text;
    const char* constraints_json; // optional constraints metadata
    const char* animations_csv;   // optional animations list
} UiWidget;

/* Scene structure */
typedef struct {
    const char* name;
    uint16_t width, height;
    uint16_t widget_count;
    const UiWidget* widgets;
} UiScene;

/* Exported scene */
extern const UiScene ui_design;

#ifdef __cplusplus
}
#endif

#endif /* UI_DESIGN_H */