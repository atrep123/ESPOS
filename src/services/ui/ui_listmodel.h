#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifndef UI_LISTMODEL_MAX_MODELS
#define UI_LISTMODEL_MAX_MODELS 4
#endif

#ifndef UI_LISTMODEL_MAX_ITEMS
#define UI_LISTMODEL_MAX_ITEMS 64
#endif

#ifndef UI_LISTMODEL_ROOT_LEN
#define UI_LISTMODEL_ROOT_LEN 32
#endif

#ifndef UI_LISTMODEL_LABEL_LEN
#define UI_LISTMODEL_LABEL_LEN 48
#endif

#ifndef UI_LISTMODEL_VALUE_LEN
#define UI_LISTMODEL_VALUE_LEN 32
#endif

typedef struct {
    char label[UI_LISTMODEL_LABEL_LEN];
    char value[UI_LISTMODEL_VALUE_LEN];
} UiListItem;

typedef struct {
    uint8_t used;
    char root[UI_LISTMODEL_ROOT_LEN];
    uint16_t count;
    uint16_t active;
    uint16_t offset;
    UiListItem items[UI_LISTMODEL_MAX_ITEMS];
} UiListModel;

typedef struct {
    UiListModel models[UI_LISTMODEL_MAX_MODELS];
} UiListModels;

void ui_listmodels_init(UiListModels *lists);
UiListModel *ui_listmodels_get(UiListModels *lists, const char *root, bool create);

void ui_listmodel_set_len(UiListModel *m, int count);
void ui_listmodel_set_item(UiListModel *m, int index, const char *label, const char *value);

bool ui_listmodel_set_active(UiListModel *m, int active_index, int visible_slots);
bool ui_listmodel_move_active(UiListModel *m, int delta, int visible_slots);

int ui_listmodel_active_slot(const UiListModel *m);

void ui_listmodel_format_scroll(const UiListModel *m, char *out, int out_cap);
void ui_listmodel_parse_item_text(const char *text, char *label, int label_cap, char *value, int value_cap);

