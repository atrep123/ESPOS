#include "ui_design.h"

static const char TXT_0[] = "UI Demo";
static const char TXT_1[] = "OK";
static const char TXT_2[] = "Enable";

const UiWidget UI_WIDGETS_DEMO[] = {
    { 0, 0, 0, 124, 10, 0, 0, 0, 0, 100, TXT_0 },
    { 1, 0, 12, 124, 46, 1, 0, 0, 0, 100, NULL },
    { 2, 8, 20, 40, 12, 1, 0, 0, 0, 100, TXT_1 },
    { 4, 8, 36, 108, 8, 1, 0, 70, 0, 100, NULL },
    { 5, 56, 24, 60, 10, 0, 1, 0, 0, 100, TXT_2 },
};


const UiScene UI_SCENE_DEMO = {
    "demo", 128, 64, (uint16_t)(sizeof(UI_WIDGETS_DEMO)/sizeof(UI_WIDGETS_DEMO[0])), UI_WIDGETS_DEMO
};
