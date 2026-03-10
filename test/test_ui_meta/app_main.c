#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_meta_parse_int(void);
void test_ui_meta_parse_bool(void);
void test_ui_meta_values_helpers(void);
void test_ui_meta_parse_str(void);
void test_ui_meta_parse_float(void);
void test_ui_meta_parse_list(void);
void test_ui_meta_parse_null_and_empty(void);
void test_ui_meta_values_count_edge_cases(void);
void test_ui_meta_values_get_edge_cases(void);
void test_ui_meta_kind_aliases(void);
void test_ui_meta_step_zero_defaults_to_one(void);
void test_ui_meta_key_alias(void);
void test_ui_meta_parse_int_overflow_rejected(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_meta_parse_int);
    RUN_TEST(test_ui_meta_parse_bool);
    RUN_TEST(test_ui_meta_values_helpers);
    RUN_TEST(test_ui_meta_parse_str);
    RUN_TEST(test_ui_meta_parse_float);
    RUN_TEST(test_ui_meta_parse_list);
    RUN_TEST(test_ui_meta_parse_null_and_empty);
    RUN_TEST(test_ui_meta_values_count_edge_cases);
    RUN_TEST(test_ui_meta_values_get_edge_cases);
    RUN_TEST(test_ui_meta_kind_aliases);
    RUN_TEST(test_ui_meta_step_zero_defaults_to_one);
    RUN_TEST(test_ui_meta_key_alias);
    RUN_TEST(test_ui_meta_parse_int_overflow_rejected);
    UNITY_END();
}

#else

void test_ui_meta_parse_int(void);
void test_ui_meta_parse_bool(void);
void test_ui_meta_values_helpers(void);
void test_ui_meta_parse_str(void);
void test_ui_meta_parse_float(void);
void test_ui_meta_parse_list(void);
void test_ui_meta_parse_null_and_empty(void);
void test_ui_meta_values_count_edge_cases(void);
void test_ui_meta_values_get_edge_cases(void);
void test_ui_meta_kind_aliases(void);
void test_ui_meta_step_zero_defaults_to_one(void);
void test_ui_meta_key_alias(void);
void test_ui_meta_parse_int_overflow_rejected(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_meta_parse_int);
    RUN_TEST(test_ui_meta_parse_bool);
    RUN_TEST(test_ui_meta_values_helpers);
    RUN_TEST(test_ui_meta_parse_str);
    RUN_TEST(test_ui_meta_parse_float);
    RUN_TEST(test_ui_meta_parse_list);
    RUN_TEST(test_ui_meta_parse_null_and_empty);
    RUN_TEST(test_ui_meta_values_count_edge_cases);
    RUN_TEST(test_ui_meta_values_get_edge_cases);
    RUN_TEST(test_ui_meta_kind_aliases);
    RUN_TEST(test_ui_meta_step_zero_defaults_to_one);
    RUN_TEST(test_ui_meta_key_alias);
    RUN_TEST(test_ui_meta_parse_int_overflow_rejected);
    return UNITY_END();
}

#endif

