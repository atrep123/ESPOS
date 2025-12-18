#include "ui_listmodel.h"

#include <string.h>
#include <stdio.h>

static int ui_str_eq(const char *a, const char *b)
{
    if (a == NULL || b == NULL) {
        return 0;
    }
    return (strcmp(a, b) == 0) ? 1 : 0;
}

static void ui_copy_str(char *dst, int dst_cap, const char *src)
{
    if (dst == NULL || dst_cap <= 0) {
        return;
    }
    if (src == NULL) {
        dst[0] = '\0';
        return;
    }
    size_t n = strlen(src);
    if (n >= (size_t)dst_cap) {
        n = (size_t)dst_cap - 1;
    }
    memcpy(dst, src, n);
    dst[n] = '\0';
}

static uint16_t ui_listmodel_max_offset(uint16_t count, uint16_t visible)
{
    if (visible == 0 || count <= visible) {
        return 0;
    }
    return (uint16_t)(count - visible);
}

static void ui_listmodel_clamp(UiListModel *m, uint16_t visible_slots)
{
    if (m == NULL) {
        return;
    }

    if (m->count == 0) {
        m->active = 0;
        m->offset = 0;
        return;
    }

    if (m->active >= m->count) {
        m->active = (uint16_t)(m->count - 1);
    }

    uint16_t max_off = ui_listmodel_max_offset(m->count, visible_slots);
    if (m->offset > max_off) {
        m->offset = max_off;
    }

    if (m->active < m->offset) {
        m->offset = m->active;
    } else if (visible_slots > 0 && m->active >= (uint16_t)(m->offset + visible_slots)) {
        m->offset = (uint16_t)(m->active - visible_slots + 1);
    }

    max_off = ui_listmodel_max_offset(m->count, visible_slots);
    if (m->offset > max_off) {
        m->offset = max_off;
    }
}

void ui_listmodels_init(UiListModels *lists)
{
    if (lists == NULL) {
        return;
    }
    memset(lists, 0, sizeof(*lists));
}

UiListModel *ui_listmodels_get(UiListModels *lists, const char *root, bool create)
{
    if (lists == NULL || root == NULL || *root == '\0') {
        return NULL;
    }

    for (int i = 0; i < UI_LISTMODEL_MAX_MODELS; ++i) {
        UiListModel *m = &lists->models[i];
        if (!m->used) {
            continue;
        }
        if (ui_str_eq(m->root, root)) {
            return m;
        }
    }

    if (!create) {
        return NULL;
    }

    for (int i = 0; i < UI_LISTMODEL_MAX_MODELS; ++i) {
        UiListModel *m = &lists->models[i];
        if (m->used) {
            continue;
        }
        memset(m, 0, sizeof(*m));
        m->used = 1;
        ui_copy_str(m->root, (int)sizeof(m->root), root);
        return m;
    }

    return NULL;
}

void ui_listmodel_set_len(UiListModel *m, int count)
{
    if (m == NULL) {
        return;
    }
    if (count < 0) {
        count = 0;
    }
    if (count > UI_LISTMODEL_MAX_ITEMS) {
        count = UI_LISTMODEL_MAX_ITEMS;
    }
    m->count = (uint16_t)count;

    if (m->count == 0) {
        m->active = 0;
        m->offset = 0;
        return;
    }

    if (m->active >= m->count) {
        m->active = (uint16_t)(m->count - 1);
    }
    if (m->offset >= m->count) {
        m->offset = (uint16_t)(m->count - 1);
    }
}

void ui_listmodel_set_item(UiListModel *m, int index, const char *label, const char *value)
{
    if (m == NULL) {
        return;
    }
    if (index < 0 || index >= (int)UI_LISTMODEL_MAX_ITEMS) {
        return;
    }
    UiListItem *it = &m->items[index];
    ui_copy_str(it->label, (int)sizeof(it->label), label);
    ui_copy_str(it->value, (int)sizeof(it->value), value);
}

bool ui_listmodel_set_active(UiListModel *m, int active_index, int visible_slots)
{
    if (m == NULL) {
        return false;
    }
    if (m->count == 0) {
        if (m->active != 0 || m->offset != 0) {
            m->active = 0;
            m->offset = 0;
            return true;
        }
        return false;
    }

    if (active_index < 0) {
        active_index = 0;
    }
    if (active_index >= (int)m->count) {
        active_index = (int)m->count - 1;
    }

    uint16_t before_active = m->active;
    uint16_t before_offset = m->offset;
    m->active = (uint16_t)active_index;
    ui_listmodel_clamp(m, (visible_slots > 0) ? (uint16_t)visible_slots : 0);
    return (before_active != m->active) || (before_offset != m->offset);
}

bool ui_listmodel_move_active(UiListModel *m, int delta, int visible_slots)
{
    if (m == NULL || delta == 0) {
        return false;
    }
    if (m->count == 0) {
        return false;
    }
    int next = (int)m->active + delta;
    if (next < 0) {
        next = 0;
    }
    if (next >= (int)m->count) {
        next = (int)m->count - 1;
    }
    return ui_listmodel_set_active(m, next, visible_slots);
}

int ui_listmodel_active_slot(const UiListModel *m)
{
    if (m == NULL) {
        return 0;
    }
    if (m->active < m->offset) {
        return 0;
    }
    return (int)(m->active - m->offset);
}

void ui_listmodel_format_scroll(const UiListModel *m, char *out, int out_cap)
{
    if (out == NULL || out_cap <= 0) {
        return;
    }
    if (m == NULL || m->count == 0) {
        snprintf(out, (size_t)out_cap, "0/0");
        return;
    }
    unsigned a = (unsigned)m->active + 1U;
    unsigned c = (unsigned)m->count;
    snprintf(out, (size_t)out_cap, "%u/%u", a, c);
}

void ui_listmodel_parse_item_text(const char *text, char *label, int label_cap, char *value, int value_cap)
{
    if (label != NULL && label_cap > 0) {
        label[0] = '\0';
    }
    if (value != NULL && value_cap > 0) {
        value[0] = '\0';
    }
    if (text == NULL || *text == '\0') {
        return;
    }

    const char *sep = strchr(text, '\t');
    if (sep == NULL) {
        sep = strchr(text, '|');
    }

    if (sep == NULL) {
        ui_copy_str(label, label_cap, text);
        return;
    }

    int left_len = (int)(sep - text);
    if (left_len < 0) {
        left_len = 0;
    }
    if (label != NULL && label_cap > 0) {
        if (left_len >= label_cap) {
            left_len = label_cap - 1;
        }
        memcpy(label, text, (size_t)left_len);
        label[left_len] = '\0';
    }

    const char *rhs = sep + 1;
    ui_copy_str(value, value_cap, rhs);
}
