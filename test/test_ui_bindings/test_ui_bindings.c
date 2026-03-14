#include "unity.h"

#include <stdio.h>
#include <string.h>

#include "services/ui/ui_bindings.h"

void setUp(void)
{
    ui_bind_clear_all();
}

void tearDown(void) {}

void test_ui_bind_int_generic(void)
{
    int val = -1;

    /* Key not set → returns false */
    TEST_ASSERT_FALSE(ui_bind_get_int("volume", &val));

    /* Set and get */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("volume", 42));
    TEST_ASSERT_TRUE(ui_bind_get_int("volume", &val));
    TEST_ASSERT_EQUAL_INT(42, val);

    /* Different key */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("brightness", 7));
    TEST_ASSERT_TRUE(ui_bind_get_int("brightness", &val));
    TEST_ASSERT_EQUAL_INT(7, val);
}

void test_ui_bind_bool_generic(void)
{
    bool val = true;

    /* Key not set → returns false */
    TEST_ASSERT_FALSE(ui_bind_get_bool("enabled", &val));
    TEST_ASSERT_FALSE(val);

    /* Set true */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("enabled", true));
    TEST_ASSERT_TRUE(ui_bind_get_bool("enabled", &val));
    TEST_ASSERT_TRUE(val);

    /* Set false */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("enabled", false));
    TEST_ASSERT_TRUE(ui_bind_get_bool("enabled", &val));
    TEST_ASSERT_FALSE(val);
}

void test_ui_bind_str_generic(void)
{
    char buf[32];

    /* Key not set → returns false */
    TEST_ASSERT_FALSE(ui_bind_get_str("name", buf, sizeof(buf)));

    /* Set and get */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_str("name", "hello"));
    TEST_ASSERT_TRUE(ui_bind_get_str("name", buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("hello", buf);
}

void test_ui_bind_clear_all(void)
{
    int val = -1;
    char buf[16];

    ui_bind_set_int("a", 10);
    ui_bind_set_str("b", "test");
    ui_bind_set_bool("c", true);

    ui_bind_clear_all();

    TEST_ASSERT_FALSE(ui_bind_get_int("a", &val));
    TEST_ASSERT_FALSE(ui_bind_get_str("b", buf, sizeof(buf)));
    bool bval = true;
    TEST_ASSERT_FALSE(ui_bind_get_bool("c", &bval));
}

void test_ui_bind_null_key(void)
{
    int val = 0;
    bool bval = false;
    char buf[16];

    /* NULL key → invalid arg or false */
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ui_bind_set_int(NULL, 1));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ui_bind_set_int("", 1));
    TEST_ASSERT_FALSE(ui_bind_get_int(NULL, &val));
    TEST_ASSERT_FALSE(ui_bind_get_int("", &val));

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ui_bind_set_bool(NULL, true));
    TEST_ASSERT_FALSE(ui_bind_get_bool(NULL, &bval));

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ui_bind_set_str(NULL, "x"));
    TEST_ASSERT_FALSE(ui_bind_get_str(NULL, buf, sizeof(buf)));

    /* NULL out pointers */
    TEST_ASSERT_FALSE(ui_bind_get_int("key", NULL));
    TEST_ASSERT_FALSE(ui_bind_get_bool("key", NULL));
    TEST_ASSERT_FALSE(ui_bind_get_str("key", NULL, 0));
}

void test_ui_bind_store_full(void)
{
    /* Fill all 96 slots */
    char key[24];
    for (int i = 0; i < 96; ++i) {
        snprintf(key, sizeof(key), "key%d", i);
        TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int(key, i));
    }

    /* 97th slot should fail */
    TEST_ASSERT_EQUAL(ESP_FAIL, ui_bind_set_int("overflow", 999));

    /* Existing keys should still work */
    int val;
    TEST_ASSERT_TRUE(ui_bind_get_int("key0", &val));
    TEST_ASSERT_EQUAL_INT(0, val);
    TEST_ASSERT_TRUE(ui_bind_get_int("key95", &val));
    TEST_ASSERT_EQUAL_INT(95, val);
}

void test_ui_bind_overwrite(void)
{
    int val;

    ui_bind_set_int("x", 10);
    ui_bind_set_int("x", 20);
    TEST_ASSERT_TRUE(ui_bind_get_int("x", &val));
    TEST_ASSERT_EQUAL_INT(20, val);

    char buf[32];
    ui_bind_set_str("s", "first");
    ui_bind_set_str("s", "second");
    TEST_ASSERT_TRUE(ui_bind_get_str("s", buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("second", buf);
}

void test_ui_bind_str_null_value(void)
{
    char buf[32];

    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_str("empty", NULL));
    TEST_ASSERT_TRUE(ui_bind_get_str("empty", buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("", buf);
}

void test_ui_bind_int_hw_contrast(void)
{
    /* "contrast" is a hardware-backed key */
    int val;
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", 128));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(128, val);
}

void test_ui_bind_bool_hw_invert(void)
{
    /* "invert" is a hardware-backed key */
    bool val;
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("invert", true));
    TEST_ASSERT_TRUE(ui_bind_get_bool("invert", &val));
    TEST_ASSERT_TRUE(val);

    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("invert", false));
    TEST_ASSERT_TRUE(ui_bind_get_bool("invert", &val));
    TEST_ASSERT_FALSE(val);
}

/* ---------------------------------------------------------------------------
 * Setter-specific tests
 * ------------------------------------------------------------------------ */

void test_ui_bind_set_int_contrast_clamped(void)
{
    int val;
    /* Negative contrast clamped to 0 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", -10));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(0, val);

    /* Over 255 clamped to 255 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", 999));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(255, val);
}

void test_ui_bind_set_int_col_offset(void)
{
    int val;
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("col_offset", 42));
    TEST_ASSERT_TRUE(ui_bind_get_int("col_offset", &val));
    TEST_ASSERT_EQUAL_INT(42, val);

    /* Clamping: negative */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("col_offset", -5));
    TEST_ASSERT_TRUE(ui_bind_get_int("col_offset", &val));
    TEST_ASSERT_EQUAL_INT(0, val);

    /* Clamping: > 255 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("col_offset", 300));
    TEST_ASSERT_TRUE(ui_bind_get_int("col_offset", &val));
    /* value is whatever ssd1363_get_col_offset_units returns after set */
    TEST_ASSERT_TRUE(val >= 0 && val <= 255);
}

void test_ui_bind_set_bool_generic(void)
{
    bool val;
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("flag", true));
    TEST_ASSERT_TRUE(ui_bind_get_bool("flag", &val));
    TEST_ASSERT_TRUE(val);

    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("flag", false));
    TEST_ASSERT_TRUE(ui_bind_get_bool("flag", &val));
    TEST_ASSERT_FALSE(val);
}

void test_ui_bind_set_str_truncation(void)
{
    /* String longer than BIND_STR_LEN (32) should be truncated */
    char buf[64];
    const char *long_str = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ";
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_str("long", long_str));
    TEST_ASSERT_TRUE(ui_bind_get_str("long", buf, sizeof(buf)));
    /* Should be truncated to 31 chars (BIND_STR_LEN - 1) */
    TEST_ASSERT_EQUAL_INT(31, (int)strlen(buf));
}

void test_ui_bind_set_bool_store_full(void)
{
    /* Fill all 96 slots with ints */
    char key[24];
    for (int i = 0; i < 96; ++i) {
        snprintf(key, sizeof(key), "k%d", i);
        TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int(key, i));
    }
    /* Bool set on new key should fail (store full) */
    TEST_ASSERT_EQUAL(ESP_FAIL, ui_bind_set_bool("new_bool", true));
    /* But overwrite an existing key via bool should succeed (reuses slot) */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_bool("k0", true));
}

void test_ui_bind_set_str_empty_key(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ui_bind_set_str("", "val"));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, ui_bind_set_bool("", true));
}

void test_ui_bind_get_str_small_buf(void)
{
    char buf[4];
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_str("msg", "hello world"));
    TEST_ASSERT_TRUE(ui_bind_get_str("msg", buf, sizeof(buf)));
    /* Should be truncated by output buffer */
    TEST_ASSERT_EQUAL_INT(3, (int)strlen(buf));
    TEST_ASSERT_EQUAL_STRING("hel", buf);
}

void test_ui_bind_int_negative_value(void)
{
    int val;
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("temp", -42));
    TEST_ASSERT_TRUE(ui_bind_get_int("temp", &val));
    TEST_ASSERT_EQUAL_INT(-42, val);
}

void test_ui_bind_contrast_boundary_adjacent(void)
{
    int val;
    /* -1 is just below valid range → clamps to 0 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", -1));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(0, val);

    /* 0 is at boundary → stays 0 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", 0));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(0, val);

    /* 255 is at boundary → stays 255 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", 255));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(255, val);

    /* 256 is just above → clamps to 255 */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("contrast", 256));
    TEST_ASSERT_TRUE(ui_bind_get_int("contrast", &val));
    TEST_ASSERT_EQUAL_INT(255, val);
}

/* ================================================================== */
/* Additional edge cases                                               */
/* ================================================================== */

void test_ui_bind_key_at_max_length(void)
{
    /* Key exactly 23 chars (BIND_KEY_LEN - 1) should be stored and retrieved */
    const char *key23 = "abcdefghijklmnopqrstuvw"; /* 23 chars */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int(key23, 777));
    int val;
    TEST_ASSERT_TRUE(ui_bind_get_int(key23, &val));
    TEST_ASSERT_EQUAL_INT(777, val);
}

void test_ui_bind_long_key_truncated_unretrievable(void)
{
    /* Key > 23 chars: slot_alloc truncates via strncpy, but slot_find
     * compares with strcmp on the full input key.  The truncated stored key
     * will never match the full lookup key → effectively unretrievable. */
    const char *longkey = "abcdefghijklmnopqrstuvwAAAA"; /* 27 chars */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int(longkey, 100));
    /* Cannot retrieve with the original long key */
    int val = -1;
    TEST_ASSERT_FALSE(ui_bind_get_int(longkey, &val));
    /* But CAN retrieve with the truncated form (first 23 chars) */
    TEST_ASSERT_TRUE(ui_bind_get_int("abcdefghijklmnopqrstuvw", &val));
    TEST_ASSERT_EQUAL_INT(100, val);
}

void test_ui_bind_type_crossover_int_then_str(void)
{
    /* ival and sval are separate fields in the same slot */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("cross", 42));
    char buf[32];
    /* get_str should find the slot but sval is empty */
    TEST_ASSERT_TRUE(ui_bind_get_str("cross", buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("", buf);
    /* ival should be untouched */
    int val;
    TEST_ASSERT_TRUE(ui_bind_get_int("cross", &val));
    TEST_ASSERT_EQUAL_INT(42, val);
}

void test_ui_bind_get_str_cap_one(void)
{
    /* out_cap=1 → room for only '\0', should return true with empty string */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_str("msg", "hello"));
    char buf[1] = { 'X' };
    TEST_ASSERT_TRUE(ui_bind_get_str("msg", buf, 1));
    TEST_ASSERT_EQUAL_STRING("", buf);
}

void test_ui_bind_clear_all_then_refill(void)
{
    /* Fill all 96 slots, clear, then refill — verifies slot reuse */
    char key[24];
    for (int i = 0; i < 96; ++i) {
        snprintf(key, sizeof(key), "fill%d", i);
        TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int(key, i));
    }
    ui_bind_clear_all();
    /* All slots freed — can insert again */
    TEST_ASSERT_EQUAL(ESP_OK, ui_bind_set_int("new_key", 999));
    int val;
    TEST_ASSERT_TRUE(ui_bind_get_int("new_key", &val));
    TEST_ASSERT_EQUAL_INT(999, val);
}
