#include "ui.h"

#include <stdio.h>
#include <string.h>

#include "kernel/msgbus.h"

static size_t ui_cmd_append_trunc(char *dst, size_t dst_cap, size_t pos, const char *src)
{
    if (dst == NULL || dst_cap == 0) {
        return pos;
    }
    if (pos >= dst_cap) {
        dst[dst_cap - 1U] = '\0';
        return dst_cap - 1U;
    }
    if (src != NULL) {
        while (*src != '\0' && (pos + 1U) < dst_cap) {
            dst[pos] = *src;
            pos++;
            src++;
        }
    }
    dst[pos] = '\0';
    return pos;
}

static size_t ui_cmd_append_char_trunc(char *dst, size_t dst_cap, size_t pos, char ch)
{
    if (dst == NULL || dst_cap == 0) {
        return pos;
    }
    if ((pos + 1U) < dst_cap) {
        dst[pos] = ch;
        pos++;
    }
    if (pos < dst_cap) {
        dst[pos] = '\0';
    } else {
        dst[dst_cap - 1U] = '\0';
        pos = dst_cap - 1U;
    }
    return pos;
}

static void ui_cmd_copy_trunc(char *dst, size_t dst_cap, const char *src)
{
    if (dst == NULL || dst_cap == 0) {
        return;
    }
    dst[0] = '\0';
    (void)ui_cmd_append_trunc(dst, dst_cap, 0, src);
}

static void ui_publish_cmd(ui_cmd_kind_t kind, const char *id, const char *text, int32_t value)
{
    msg_t m = {0};
    m.topic = TOP_UI_CMD;
    m.u.ui_cmd.kind = (uint8_t)kind;
    ui_cmd_copy_trunc(m.u.ui_cmd.id, sizeof(m.u.ui_cmd.id), id);
    ui_cmd_copy_trunc(m.u.ui_cmd.text, sizeof(m.u.ui_cmd.text), text);
    m.u.ui_cmd.value = value;
    bus_publish(&m);
}

void ui_cmd_set_text(const char *id, const char *text)
{
    ui_publish_cmd(UI_CMD_SET_TEXT, id, text, 0);
}

void ui_cmd_set_visible(const char *id, bool visible)
{
    ui_publish_cmd(UI_CMD_SET_VISIBLE, id, NULL, visible ? 1 : 0);
}

void ui_cmd_set_enabled(const char *id, bool enabled)
{
    ui_publish_cmd(UI_CMD_SET_ENABLED, id, NULL, enabled ? 1 : 0);
}

void ui_cmd_set_prefix_visible(const char *root, bool visible)
{
    ui_publish_cmd(UI_CMD_SET_PREFIX_VISIBLE, root, NULL, visible ? 1 : 0);
}

void ui_cmd_set_style(const char *id, uint8_t style)
{
    ui_publish_cmd(UI_CMD_SET_STYLE, id, NULL, (int32_t)style);
}

void ui_cmd_set_value(const char *id, int value)
{
    ui_publish_cmd(UI_CMD_SET_VALUE, id, NULL, (int32_t)value);
}

void ui_cmd_set_checked(const char *id, bool checked)
{
    ui_publish_cmd(UI_CMD_SET_CHECKED, id, NULL, checked ? 1 : 0);
}

void ui_cmd_menu_set_active(const char *root, int active_index)
{
    ui_publish_cmd(UI_CMD_MENU_SET_ACTIVE, root, NULL, (int32_t)active_index);
}

void ui_cmd_list_set_active(const char *root, int active_index)
{
    ui_publish_cmd(UI_CMD_LIST_SET_ACTIVE, root, NULL, (int32_t)active_index);
}

void ui_cmd_tabs_set_active(const char *root, int active_index)
{
    ui_publish_cmd(UI_CMD_TABS_SET_ACTIVE, root, NULL, (int32_t)active_index);
}

void ui_cmd_listmodel_set_len(const char *root, int count)
{
    ui_publish_cmd(UI_CMD_LISTMODEL_SET_LEN, root, NULL, (int32_t)count);
}

void ui_cmd_listmodel_set_item(const char *root, int index, const char *label, const char *value)
{
    char buf[64] = {0};
    size_t pos = 0;
    const char *lhs = (label != NULL) ? label : "";
    const char *rhs = (value != NULL) ? value : "";
    pos = ui_cmd_append_trunc(buf, sizeof(buf), pos, lhs);
    if (*rhs != '\0') {
        pos = ui_cmd_append_char_trunc(buf, sizeof(buf), pos, '\t');
        (void)ui_cmd_append_trunc(buf, sizeof(buf), pos, rhs);
    }
    ui_publish_cmd(UI_CMD_LISTMODEL_SET_ITEM, root, buf, (int32_t)index);
}

void ui_cmd_listmodel_set_active(const char *root, int active_index)
{
    ui_publish_cmd(UI_CMD_LISTMODEL_SET_ACTIVE, root, NULL, (int32_t)active_index);
}

void ui_cmd_dialog_show(const char *root)
{
    ui_publish_cmd(UI_CMD_DIALOG_SHOW, root, NULL, 0);
}

void ui_cmd_dialog_hide(const char *root)
{
    ui_publish_cmd(UI_CMD_DIALOG_HIDE, root, NULL, 0);
}

void ui_cmd_toast_enqueue(const char *root, const char *message, uint32_t duration_ms)
{
    ui_publish_cmd(UI_CMD_TOAST_ENQUEUE, root, message, (int32_t)duration_ms);
}

void ui_cmd_toast_hide(const char *root)
{
    ui_publish_cmd(UI_CMD_TOAST_HIDE, root, NULL, 0);
}

void ui_cmd_switch_scene(int scene_index)
{
    ui_publish_cmd(UI_CMD_SWITCH_SCENE, NULL, NULL, (int32_t)scene_index);
}
