/*
 * Unit tests for ui_cmd.c — the thread-safe command publisher API.
 *
 * Each test subscribes to TOP_UI_CMD via bus, calls the public ui_cmd_*
 * function, receives the message, and verifies kind/id/text/value fields.
 */

#include "unity.h"

#include <string.h>

#include "kernel/msgbus.h"
#include "services/ui/ui.h"

static QueueHandle_t q;

void setUp(void)
{
    bus_init();
    q = bus_make_queue(4);
    bus_subscribe(TOP_UI_CMD, q);
}

void tearDown(void)
{
    vQueueDelete(q);
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

static msg_t recv_one(void)
{
    msg_t m;
    memset(&m, 0, sizeof(m));
    int ok = xQueueReceive(q, &m, 0);
    TEST_ASSERT_EQUAL_INT_MESSAGE(1, ok, "Expected one message on queue");
    TEST_ASSERT_EQUAL_INT(TOP_UI_CMD, m.topic);
    return m;
}

/* ------------------------------------------------------------------ */
/* Test Cases                                                          */
/* ------------------------------------------------------------------ */

void test_cmd_set_text(void)
{
    ui_cmd_set_text("lbl1", "Hello");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_TEXT, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("lbl1", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_STRING("Hello", m.u.ui_cmd.text);
    TEST_ASSERT_EQUAL_INT32(0, m.u.ui_cmd.value);
}

void test_cmd_set_text_null_id(void)
{
    ui_cmd_set_text(NULL, "X");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_TEXT, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_STRING("X", m.u.ui_cmd.text);
}

void test_cmd_set_text_null_text(void)
{
    ui_cmd_set_text("w", NULL);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_TEXT, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("w", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_STRING("", m.u.ui_cmd.text);
}

void test_cmd_set_visible_true(void)
{
    ui_cmd_set_visible("btn1", true);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_VISIBLE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("btn1", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(1, m.u.ui_cmd.value);
}

void test_cmd_set_visible_false(void)
{
    ui_cmd_set_visible("btn1", false);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_VISIBLE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_INT32(0, m.u.ui_cmd.value);
}

void test_cmd_set_enabled(void)
{
    ui_cmd_set_enabled("slider", true);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_ENABLED, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("slider", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(1, m.u.ui_cmd.value);
}

void test_cmd_set_prefix_visible(void)
{
    ui_cmd_set_prefix_visible("menu", false);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_PREFIX_VISIBLE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("menu", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(0, m.u.ui_cmd.value);
}

void test_cmd_set_style(void)
{
    ui_cmd_set_style("lbl", 3);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_STYLE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("lbl", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(3, m.u.ui_cmd.value);
}

void test_cmd_set_value(void)
{
    ui_cmd_set_value("gauge1", 75);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_VALUE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("gauge1", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(75, m.u.ui_cmd.value);
}

void test_cmd_set_checked(void)
{
    ui_cmd_set_checked("chk1", true);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_CHECKED, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("chk1", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(1, m.u.ui_cmd.value);
}

void test_cmd_menu_set_active(void)
{
    ui_cmd_menu_set_active("nav", 2);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_MENU_SET_ACTIVE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("nav", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(2, m.u.ui_cmd.value);
}

void test_cmd_list_set_active(void)
{
    ui_cmd_list_set_active("list", 5);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LIST_SET_ACTIVE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("list", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(5, m.u.ui_cmd.value);
}

void test_cmd_tabs_set_active(void)
{
    ui_cmd_tabs_set_active("tabs", 1);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_TABS_SET_ACTIVE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("tabs", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(1, m.u.ui_cmd.value);
}

void test_cmd_listmodel_set_len(void)
{
    ui_cmd_listmodel_set_len("files", 42);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LISTMODEL_SET_LEN, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("files", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(42, m.u.ui_cmd.value);
}

void test_cmd_listmodel_set_item_label_only(void)
{
    ui_cmd_listmodel_set_item("files", 3, "readme.txt", NULL);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LISTMODEL_SET_ITEM, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("files", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(3, m.u.ui_cmd.value);
    TEST_ASSERT_EQUAL_STRING("readme.txt", m.u.ui_cmd.text);
}

void test_cmd_listmodel_set_item_label_and_value(void)
{
    ui_cmd_listmodel_set_item("files", 0, "WiFi", "ON");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LISTMODEL_SET_ITEM, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("files", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(0, m.u.ui_cmd.value);
    /* label\tvalue format */
    TEST_ASSERT_EQUAL_STRING("WiFi\tON", m.u.ui_cmd.text);
}

void test_cmd_listmodel_set_item_null_label(void)
{
    ui_cmd_listmodel_set_item("lst", 1, NULL, "val");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LISTMODEL_SET_ITEM, m.u.ui_cmd.kind);
    /* NULL label becomes "" — with non-empty value it's "\tval" */
    TEST_ASSERT_EQUAL_STRING("\tval", m.u.ui_cmd.text);
}

void test_cmd_listmodel_set_active(void)
{
    ui_cmd_listmodel_set_active("list", 7);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LISTMODEL_SET_ACTIVE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("list", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(7, m.u.ui_cmd.value);
}

void test_cmd_dialog_show(void)
{
    ui_cmd_dialog_show("confirm");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_DIALOG_SHOW, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("confirm", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_INT32(0, m.u.ui_cmd.value);
}

void test_cmd_dialog_hide(void)
{
    ui_cmd_dialog_hide("confirm");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_DIALOG_HIDE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("confirm", m.u.ui_cmd.id);
}

void test_cmd_toast_enqueue(void)
{
    ui_cmd_toast_enqueue("notif", "Saved!", 3000);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_TOAST_ENQUEUE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("notif", m.u.ui_cmd.id);
    TEST_ASSERT_EQUAL_STRING("Saved!", m.u.ui_cmd.text);
    TEST_ASSERT_EQUAL_INT32(3000, m.u.ui_cmd.value);
}

void test_cmd_toast_hide(void)
{
    ui_cmd_toast_hide("notif");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_TOAST_HIDE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("notif", m.u.ui_cmd.id);
}

void test_cmd_switch_scene(void)
{
    ui_cmd_switch_scene(2);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SWITCH_SCENE, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("", m.u.ui_cmd.id); /* id is NULL → empty */
    TEST_ASSERT_EQUAL_INT32(2, m.u.ui_cmd.value);
}

void test_cmd_id_truncation(void)
{
    /* id field is 32 bytes; a long id should be truncated, not overflow */
    const char *long_id = "this_is_a_very_long_widget_id_that_exceeds_buffer";
    ui_cmd_set_text(long_id, "ok");
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_SET_TEXT, m.u.ui_cmd.kind);
    /* Should be null-terminated at 31 chars */
    TEST_ASSERT_EQUAL_UINT(31, strlen(m.u.ui_cmd.id));
    TEST_ASSERT_EQUAL_CHAR('\0', m.u.ui_cmd.id[31]);
}

void test_cmd_text_truncation(void)
{
    /* text field is 64 bytes; long text should be truncated safely */
    const char *long_text =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        "abcdefghijklmnopqrstuvwxyz0123456789";
    ui_cmd_set_text("w", long_text);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_UINT(63, strlen(m.u.ui_cmd.text));
    TEST_ASSERT_EQUAL_CHAR('\0', m.u.ui_cmd.text[63]);
}

void test_cmd_listmodel_set_item_truncation(void)
{
    /* Combined label + tab + value exceeding 63 chars is truncated. */
    const char *label = "ABCDEFGHIJKLMNOPQRSTUVWXYZ01234"; /* 30 chars */
    const char *value = "abcdefghijklmnopqrstuvwxyz012345"; /* 31 chars */
    /* Total: 30 + 1(tab) + 31 = 62 => fits within 63 */
    ui_cmd_listmodel_set_item("x", 0, label, value);
    msg_t m = recv_one();
    TEST_ASSERT_TRUE(strlen(m.u.ui_cmd.text) <= 63);
    TEST_ASSERT_NOT_NULL(strchr(m.u.ui_cmd.text, '\t'));

    /* Now exceed: 40 + 1 + 40 = 81 > 63 */
    const char *big_label = "ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890123"; /* 40 */
    const char *big_value = "abcdefghijklmnopqrstuvwxyz01234567890123"; /* 40 */
    ui_cmd_listmodel_set_item("x", 1, big_label, big_value);
    m = recv_one();
    TEST_ASSERT_EQUAL_UINT(63, strlen(m.u.ui_cmd.text));
    TEST_ASSERT_EQUAL_CHAR('\0', m.u.ui_cmd.text[63]);
}

void test_cmd_listmodel_set_item_both_null(void)
{
    ui_cmd_listmodel_set_item("x", 0, NULL, NULL);
    msg_t m = recv_one();
    TEST_ASSERT_EQUAL_INT(UI_CMD_LISTMODEL_SET_ITEM, m.u.ui_cmd.kind);
    TEST_ASSERT_EQUAL_STRING("", m.u.ui_cmd.text);
}
