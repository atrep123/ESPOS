#include "unity.h"

#include "services/ui/ui_helpers.h"

#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* ======================== ui_parse_uint_dec ======================== */

void test_parse_uint_dec_simple(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_uint_dec("42", &v));
    TEST_ASSERT_EQUAL_INT(42, v);
}

void test_parse_uint_dec_zero(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_uint_dec("0", &v));
    TEST_ASSERT_EQUAL_INT(0, v);
}

void test_parse_uint_dec_trailing_chars(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_uint_dec("123abc", &v));
    TEST_ASSERT_EQUAL_INT(123, v);
}

void test_parse_uint_dec_null_string(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_uint_dec(NULL, &v));
    TEST_ASSERT_EQUAL_INT(0, v);
}

void test_parse_uint_dec_empty_string(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_uint_dec("", &v));
    TEST_ASSERT_EQUAL_INT(0, v);
}

void test_parse_uint_dec_non_digit(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_uint_dec("abc", &v));
    TEST_ASSERT_EQUAL_INT(0, v);
}

void test_parse_uint_dec_null_out(void)
{
    /* Should not crash when out_value is NULL */
    TEST_ASSERT_EQUAL_INT(1, ui_parse_uint_dec("99", NULL));
}

void test_parse_uint_dec_large_number(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_uint_dec("100000", &v));
    TEST_ASSERT_EQUAL_INT(100000, v);
}

void test_parse_uint_dec_overflow_stops(void)
{
    /* A number that would overflow int (>2147483647) should be rejected. */
    int v = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_uint_dec("9999999999", &v));
    TEST_ASSERT_EQUAL_INT(0, v); /* reset to 0 on failure */
}

void test_parse_uint_dec_max_int(void)
{
    int v = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_uint_dec("2147483647", &v));
    TEST_ASSERT_EQUAL_INT(2147483647, v);
}

/* ======================== ui_parse_item_root_slot ======================== */

void test_parse_item_root_slot_basic(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_item_root_slot("list.item0", root, sizeof(root), &slot));
    TEST_ASSERT_EQUAL_STRING("list", root);
    TEST_ASSERT_EQUAL_INT(0, slot);
}

void test_parse_item_root_slot_higher_index(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_item_root_slot("menu.item12", root, sizeof(root), &slot));
    TEST_ASSERT_EQUAL_STRING("menu", root);
    TEST_ASSERT_EQUAL_INT(12, slot);
}

void test_parse_item_root_slot_null_id(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot(NULL, root, sizeof(root), &slot));
}

void test_parse_item_root_slot_empty_id(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot("", root, sizeof(root), &slot));
}

void test_parse_item_root_slot_no_dot(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot("listitem0", root, sizeof(root), &slot));
}

void test_parse_item_root_slot_not_item_prefix(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot("list.button", root, sizeof(root), &slot));
}

void test_parse_item_root_slot_dot_at_start(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot(".item0", root, sizeof(root), &slot));
}

void test_parse_item_root_slot_dot_at_end(void)
{
    char root[32];
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot("list.", root, sizeof(root), &slot));
}

void test_parse_item_root_slot_small_root_buffer(void)
{
    char root[4]; /* too small to hold "mylist" */
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_item_root_slot("mylist.item5", root, sizeof(root), &slot));
    /* truncated root */
    TEST_ASSERT_EQUAL_INT(3, (int)strlen(root));
    TEST_ASSERT_EQUAL_INT(5, slot);
}

void test_parse_item_root_slot_null_root(void)
{
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(0, ui_parse_item_root_slot("list.item0", NULL, 0, &slot));
}

void test_parse_item_root_slot_null_out_slot(void)
{
    char root[32];
    /* Should not crash when out_slot is NULL */
    TEST_ASSERT_EQUAL_INT(1, ui_parse_item_root_slot("list.item3", root, sizeof(root), NULL));
    TEST_ASSERT_EQUAL_STRING("list", root);
}

void test_parse_item_root_slot_cap1_truncates_root(void)
{
    char root[1]; /* only room for NUL terminator */
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_item_root_slot("abc.item7", root, sizeof(root), &slot));
    TEST_ASSERT_EQUAL_STRING("", root); /* root truncated to empty */
    TEST_ASSERT_EQUAL_INT(7, slot);
}

void test_parse_item_root_slot_cap2_truncates_root(void)
{
    char root[2]; /* room for 1 char + NUL */
    int slot = -1;
    TEST_ASSERT_EQUAL_INT(1, ui_parse_item_root_slot("hello.item99", root, sizeof(root), &slot));
    TEST_ASSERT_EQUAL_STRING("h", root); /* root truncated to 1 char */
    TEST_ASSERT_EQUAL_INT(99, slot);
}

/* ======================== Toast queue ======================== */

void test_toast_reset(void)
{
    UiToast toast;
    toast.active = 1;
    toast.expires_us = 12345;
    toast.head = 2;
    toast.count = 3;
    strcpy(toast.root, "hello");

    ui_toast_reset(&toast);

    TEST_ASSERT_EQUAL_UINT(0, toast.active);
    TEST_ASSERT_EQUAL_INT64(0, toast.expires_us);
    TEST_ASSERT_EQUAL_STRING("", toast.root);
    TEST_ASSERT_EQUAL_UINT(0, toast.head);
    TEST_ASSERT_EQUAL_UINT(0, toast.count);
}

void test_toast_reset_null_safe(void)
{
    /* Should not crash */
    ui_toast_reset(NULL);
}

void test_toast_push_pop_single(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    ui_toast_queue_push(&toast, "hello", 2000);
    TEST_ASSERT_EQUAL_UINT(1, toast.count);

    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("hello", item.message);
    TEST_ASSERT_EQUAL_UINT32(2000, item.duration_ms);
    TEST_ASSERT_EQUAL_UINT(0, toast.count);
}

void test_toast_push_pop_fifo_order(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    ui_toast_queue_push(&toast, "first", 1000);
    ui_toast_queue_push(&toast, "second", 2000);
    ui_toast_queue_push(&toast, "third", 3000);

    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("first", item.message);

    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("second", item.message);

    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("third", item.message);

    TEST_ASSERT_EQUAL_UINT(0, toast.count);
}

void test_toast_pop_empty(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(0, ui_toast_queue_pop(&toast, &item));
}

void test_toast_pop_null_out(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));
    ui_toast_queue_push(&toast, "msg", 500);

    /* Pop without out_item — should not crash */
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, NULL));
    TEST_ASSERT_EQUAL_UINT(0, toast.count);
}

void test_toast_push_overflow_drops_oldest(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    /* Fill all 4 slots */
    ui_toast_queue_push(&toast, "msg0", 100);
    ui_toast_queue_push(&toast, "msg1", 200);
    ui_toast_queue_push(&toast, "msg2", 300);
    ui_toast_queue_push(&toast, "msg3", 400);
    TEST_ASSERT_EQUAL_UINT(UI_TOAST_QUEUE_LEN, toast.count);

    /* Push one more — should drop msg0 */
    ui_toast_queue_push(&toast, "msg4", 500);
    TEST_ASSERT_EQUAL_UINT(UI_TOAST_QUEUE_LEN, toast.count);

    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("msg1", item.message);
    TEST_ASSERT_EQUAL_UINT32(200, item.duration_ms);
}

void test_toast_push_null_message(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    ui_toast_queue_push(&toast, NULL, 1000);
    TEST_ASSERT_EQUAL_UINT(1, toast.count);

    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("", item.message);
}

void test_toast_push_null_toast(void)
{
    /* Should not crash */
    ui_toast_queue_push(NULL, "msg", 1000);
}

void test_toast_pop_null_toast(void)
{
    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(0, ui_toast_queue_pop(NULL, &item));
}

void test_toast_push_pop_wraparound(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    /* Push and pop a few to advance head */
    ui_toast_queue_push(&toast, "a", 100);
    ui_toast_queue_push(&toast, "b", 200);
    UiToastItem item;
    ui_toast_queue_pop(&toast, &item);
    ui_toast_queue_pop(&toast, &item);

    /* Now head is at index 2. Fill again. */
    ui_toast_queue_push(&toast, "c", 300);
    ui_toast_queue_push(&toast, "d", 400);
    ui_toast_queue_push(&toast, "e", 500);
    ui_toast_queue_push(&toast, "f", 600);

    TEST_ASSERT_EQUAL_UINT(4, toast.count);

    /* Verify FIFO order correctly wraps around circular buffer */
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("c", item.message);
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("d", item.message);
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("e", item.message);
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    TEST_ASSERT_EQUAL_STRING("f", item.message);

    TEST_ASSERT_EQUAL_UINT(0, toast.count);
}

void test_toast_long_message_truncation(void)
{
    UiToast toast;
    memset(&toast, 0, sizeof(toast));

    /* Build a string longer than UI_TOAST_MSG_LEN */
    char long_msg[128];
    memset(long_msg, 'X', sizeof(long_msg) - 1);
    long_msg[sizeof(long_msg) - 1] = '\0';

    ui_toast_queue_push(&toast, long_msg, 1000);

    UiToastItem item;
    TEST_ASSERT_EQUAL_INT(1, ui_toast_queue_pop(&toast, &item));
    /* Message should be truncated to UI_TOAST_MSG_LEN - 1 */
    TEST_ASSERT_EQUAL_INT(UI_TOAST_MSG_LEN - 1, (int)strlen(item.message));
}
