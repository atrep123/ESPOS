/*
 * Unit tests for pure value formatting (ui_format.c):
 * - ui_format_meta_value: format raw values based on meta kind
 * - ui_format_label_value: compose "label: value" strings
 *
 * Tests cover: bool (default/custom labels), int (plain/prefix+suffix),
 * enum (valid/out-of-range/no-values), str, float (precision 0/1/2/3,
 * negative values, custom scale, negative zero sign).
 */

#include "unity.h"
#include <string.h>
#include <stdio.h>
#include "ui_format.h"

void setUp(void) {}
void tearDown(void) {}

/* Helper: build a zeroed meta with a specific kind. */
static ui_meta_t make_meta(ui_meta_kind_t kind)
{
    ui_meta_t m;
    memset(&m, 0, sizeof(m));
    m.kind = kind;
    m.precision = -1; /* default */
    return m;
}

/* ================================================================== */
/* ui_format_meta_value — BOOL                                         */
/* ================================================================== */

void test_fmt_bool_true_default(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_BOOL);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 1, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("on", buf);
}

void test_fmt_bool_false_default(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_BOOL);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("off", buf);
}

void test_fmt_bool_custom_labels(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_BOOL);
    snprintf(m.values, sizeof(m.values), "disabled|enabled");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 1, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("enabled", buf);

    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("disabled", buf);
}

/* ================================================================== */
/* ui_format_meta_value — INT                                          */
/* ================================================================== */

void test_fmt_int_plain(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_INT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 42, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("42", buf);
}

void test_fmt_int_negative(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_INT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, -7, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("-7", buf);
}

void test_fmt_int_prefix_suffix(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_INT);
    snprintf(m.prefix, sizeof(m.prefix), "$");
    snprintf(m.suffix, sizeof(m.suffix), "k");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 100, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("$100k", buf);
}

void test_fmt_int_zero(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_INT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("0", buf);
}

/* ================================================================== */
/* ui_format_meta_value — ENUM                                         */
/* ================================================================== */

void test_fmt_enum_valid_index(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_ENUM);
    snprintf(m.values, sizeof(m.values), "Alpha|Beta|Gamma");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 1, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("Beta", buf);
}

void test_fmt_enum_first(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_ENUM);
    snprintf(m.values, sizeof(m.values), "A|B|C");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("A", buf);
}

void test_fmt_enum_clamp_negative(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_ENUM);
    snprintf(m.values, sizeof(m.values), "X|Y|Z");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, -5, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("X", buf);
}

void test_fmt_enum_clamp_overflow(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_ENUM);
    snprintf(m.values, sizeof(m.values), "X|Y|Z");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 99, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("Z", buf);
}

void test_fmt_enum_no_values_fallback(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_ENUM);
    /* values is empty */
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 3, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("3", buf);
}

/* ================================================================== */
/* ui_format_meta_value — STR                                          */
/* ================================================================== */

void test_fmt_str(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_STR);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, "hello", buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("hello", buf);
}

void test_fmt_str_null(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_STR);
    char buf[32];
    buf[0] = 'X';
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("", buf);
}

/* ================================================================== */
/* ui_format_meta_value — FLOAT                                        */
/* ================================================================== */

void test_fmt_float_default_prec2(void)
{
    /* 150 / 100 = 1.50 */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 150, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("1.50", buf);
}

void test_fmt_float_precision_1(void)
{
    /* 255 / 100, prec=1 → 2.5 */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.precision = 1;
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 255, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("2.5", buf);
}

void test_fmt_float_precision_0_round_up(void)
{
    /* 250 / 100, prec=0 → 3 (round half-up) */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.precision = 0;
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 250, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("3", buf);
}

void test_fmt_float_precision_0_no_round(void)
{
    /* 149 / 100, prec=0 → 1 (49 < 50, no round) */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.precision = 0;
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 149, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("1", buf);
}

void test_fmt_float_custom_scale(void)
{
    /* 3456 / 1000, prec=3 → 3.456 */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.scale = 1000;
    m.precision = 3;
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 3456, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("3.456", buf);
}

void test_fmt_float_scale_10_prec_1(void)
{
    /* 236 / 10, prec=1 → 23.6 */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.scale = 10;
    m.precision = 1;
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 236, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("23.6", buf);
}

void test_fmt_float_with_suffix(void)
{
    /* 236 / 10 = 23.6, suffix="V" */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.scale = 10;
    m.precision = 1;
    snprintf(m.suffix, sizeof(m.suffix), "V");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 236, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("23.6V", buf);
}

void test_fmt_float_negative(void)
{
    /* -150 / 100th = -1.50 */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, -150, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("-1.50", buf);
}

void test_fmt_float_negative_zero(void)
{
    /* -50 / 100 → whole=0, but value is negative → should show "-0.50" */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, -50, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("-0.50", buf);
}

void test_fmt_float_zero(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("0.00", buf);
}

void test_fmt_float_negative_prec0_round(void)
{
    /* -250 / 100, prec=0 → -3 (frac=50 >= 50, round away from zero) */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.precision = 0;
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, -250, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("-3", buf);
}

/* ================================================================== */
/* ui_format_meta_value — edge cases                                   */
/* ================================================================== */

void test_fmt_kind_none_returns_zero(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_NONE);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(0, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
}

void test_fmt_null_meta_returns_zero(void)
{
    char buf[32];
    TEST_ASSERT_EQUAL_INT(0, ui_format_meta_value(NULL, 0, 0, NULL, buf, sizeof(buf)));
}

void test_fmt_null_buf_returns_zero(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_INT);
    TEST_ASSERT_EQUAL_INT(0, ui_format_meta_value(&m, 5, 0, NULL, NULL, 0));
}

/* ================================================================== */
/* ui_format_label_value                                               */
/* ================================================================== */

void test_label_value_basic(void)
{
    char buf[64];
    int n = ui_format_label_value("Temp", "23.6V", buf, sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("Temp: 23.6V", buf);
    TEST_ASSERT_EQUAL_INT(11, n);
}

void test_label_value_null_label(void)
{
    char buf[64];
    ui_format_label_value(NULL, "42", buf, sizeof(buf));
    TEST_ASSERT_EQUAL_STRING(": 42", buf);
}

void test_label_value_null_value(void)
{
    char buf[64];
    ui_format_label_value("Key", NULL, buf, sizeof(buf));
    TEST_ASSERT_EQUAL_STRING("Key: ", buf);
}

void test_label_value_null_buf(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_format_label_value("a", "b", NULL, 0));
}

void test_label_value_truncation(void)
{
    char buf[8];
    ui_format_label_value("ABCDEF", "XYZ", buf, sizeof(buf));
    /* "ABCDEF: XYZ" truncated to 7 chars + NUL */
    TEST_ASSERT_EQUAL_INT(7, (int)strlen(buf));
    TEST_ASSERT_EQUAL_STRING("ABCDEF:", buf);
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_fmt_float_prefix_and_suffix(void)
{
    /* Float with both prefix and suffix */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.scale = 10;
    m.precision = 1;
    snprintf(m.prefix, sizeof(m.prefix), "$");
    snprintf(m.suffix, sizeof(m.suffix), "M");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 156, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("$15.6M", buf);
}

void test_fmt_bool_single_custom_label_fallback(void)
{
    /* Only 1 value in custom labels (need >=2) → fallback to on/off */
    ui_meta_t m = make_meta(UI_META_KIND_BOOL);
    snprintf(m.values, sizeof(m.values), "only_one");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 1, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("on", buf);
}

void test_fmt_enum_single_value(void)
{
    /* Enum with a single entry — any index clamps to it */
    ui_meta_t m = make_meta(UI_META_KIND_ENUM);
    snprintf(m.values, sizeof(m.values), "Only");
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 0, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("Only", buf);
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 5, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("Only", buf);
}

void test_fmt_int_large_positive(void)
{
    ui_meta_t m = make_meta(UI_META_KIND_INT);
    char buf[32];
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 2147483647, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_STRING("2147483647", buf);
}

void test_fmt_float_small_buffer_truncation(void)
{
    /* Buffer too small to fit full float → snprintf truncates */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    char buf[4]; /* "1.50" needs 5 chars + NUL */
    TEST_ASSERT_EQUAL_INT(1, ui_format_meta_value(&m, 150, 0, NULL, buf, sizeof(buf)));
    TEST_ASSERT_EQUAL_INT(3, (int)strlen(buf));
}

/* ================================================================== */
/* Precision clamp stress test                                         */
/* ================================================================== */

void test_fmt_float_precision_10_clamped(void)
{
    /* precision=10 would overflow int pow10 (10^10 > INT32_MAX).
       After the fix, precision is clamped to 9. */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.scale = 100;
    m.precision = 10;
    char buf[64];
    int ok = ui_format_meta_value(&m, 12345, 0, NULL, buf, sizeof(buf));
    TEST_ASSERT_EQUAL_INT(1, ok);
    /* Should produce a valid string (precision clamped to 9) */
    TEST_ASSERT_TRUE(strlen(buf) > 0);
    TEST_ASSERT_TRUE(strlen(buf) < sizeof(buf));
}

void test_fmt_float_precision_99_clamped(void)
{
    /* Extreme precision value — should be clamped to 9 */
    ui_meta_t m = make_meta(UI_META_KIND_FLOAT);
    m.scale = 1000;
    m.precision = 99;
    char buf[64];
    int ok = ui_format_meta_value(&m, 5000, 0, NULL, buf, sizeof(buf));
    TEST_ASSERT_EQUAL_INT(1, ok);
    TEST_ASSERT_TRUE(strlen(buf) > 0);
}
