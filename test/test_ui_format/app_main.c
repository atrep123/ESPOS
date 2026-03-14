/* Unity test runner for test_ui_format */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* BOOL */
extern void test_fmt_bool_true_default(void);
extern void test_fmt_bool_false_default(void);
extern void test_fmt_bool_custom_labels(void);

/* INT */
extern void test_fmt_int_plain(void);
extern void test_fmt_int_negative(void);
extern void test_fmt_int_prefix_suffix(void);
extern void test_fmt_int_zero(void);

/* ENUM */
extern void test_fmt_enum_valid_index(void);
extern void test_fmt_enum_first(void);
extern void test_fmt_enum_clamp_negative(void);
extern void test_fmt_enum_clamp_overflow(void);
extern void test_fmt_enum_no_values_fallback(void);

/* STR */
extern void test_fmt_str(void);
extern void test_fmt_str_null(void);

/* FLOAT */
extern void test_fmt_float_default_prec2(void);
extern void test_fmt_float_precision_1(void);
extern void test_fmt_float_precision_0_round_up(void);
extern void test_fmt_float_precision_0_no_round(void);
extern void test_fmt_float_custom_scale(void);
extern void test_fmt_float_scale_10_prec_1(void);
extern void test_fmt_float_with_suffix(void);
extern void test_fmt_float_negative(void);
extern void test_fmt_float_negative_zero(void);
extern void test_fmt_float_zero(void);
extern void test_fmt_float_negative_prec0_round(void);

/* edge cases */
extern void test_fmt_kind_none_returns_zero(void);
extern void test_fmt_null_meta_returns_zero(void);
extern void test_fmt_null_buf_returns_zero(void);

/* label_value */
extern void test_label_value_basic(void);
extern void test_label_value_null_label(void);
extern void test_label_value_null_value(void);
extern void test_label_value_null_buf(void);
extern void test_label_value_truncation(void);
extern void test_fmt_float_prefix_and_suffix(void);
extern void test_fmt_bool_single_custom_label_fallback(void);
extern void test_fmt_enum_single_value(void);
extern void test_fmt_int_large_positive(void);
extern void test_fmt_float_small_buffer_truncation(void);
extern void test_fmt_float_precision_10_clamped(void);
extern void test_fmt_float_precision_99_clamped(void);

int main(void)
{
    UNITY_BEGIN();

    /* BOOL */
    RUN_TEST(test_fmt_bool_true_default);
    RUN_TEST(test_fmt_bool_false_default);
    RUN_TEST(test_fmt_bool_custom_labels);

    /* INT */
    RUN_TEST(test_fmt_int_plain);
    RUN_TEST(test_fmt_int_negative);
    RUN_TEST(test_fmt_int_prefix_suffix);
    RUN_TEST(test_fmt_int_zero);

    /* ENUM */
    RUN_TEST(test_fmt_enum_valid_index);
    RUN_TEST(test_fmt_enum_first);
    RUN_TEST(test_fmt_enum_clamp_negative);
    RUN_TEST(test_fmt_enum_clamp_overflow);
    RUN_TEST(test_fmt_enum_no_values_fallback);

    /* STR */
    RUN_TEST(test_fmt_str);
    RUN_TEST(test_fmt_str_null);

    /* FLOAT */
    RUN_TEST(test_fmt_float_default_prec2);
    RUN_TEST(test_fmt_float_precision_1);
    RUN_TEST(test_fmt_float_precision_0_round_up);
    RUN_TEST(test_fmt_float_precision_0_no_round);
    RUN_TEST(test_fmt_float_custom_scale);
    RUN_TEST(test_fmt_float_scale_10_prec_1);
    RUN_TEST(test_fmt_float_with_suffix);
    RUN_TEST(test_fmt_float_negative);
    RUN_TEST(test_fmt_float_negative_zero);
    RUN_TEST(test_fmt_float_zero);
    RUN_TEST(test_fmt_float_negative_prec0_round);

    /* edge cases */
    RUN_TEST(test_fmt_kind_none_returns_zero);
    RUN_TEST(test_fmt_null_meta_returns_zero);
    RUN_TEST(test_fmt_null_buf_returns_zero);

    /* label_value */
    RUN_TEST(test_label_value_basic);
    RUN_TEST(test_label_value_null_label);
    RUN_TEST(test_label_value_null_value);
    RUN_TEST(test_label_value_null_buf);
    RUN_TEST(test_label_value_truncation);

    /* new edge-case tests */
    RUN_TEST(test_fmt_float_prefix_and_suffix);
    RUN_TEST(test_fmt_bool_single_custom_label_fallback);
    RUN_TEST(test_fmt_enum_single_value);
    RUN_TEST(test_fmt_int_large_positive);
    RUN_TEST(test_fmt_float_small_buffer_truncation);
    RUN_TEST(test_fmt_float_precision_10_clamped);
    RUN_TEST(test_fmt_float_precision_99_clamped);

    return UNITY_END();
}
