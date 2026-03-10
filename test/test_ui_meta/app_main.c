#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_meta_parse_int(void);
void test_ui_meta_parse_bool(void);
void test_ui_meta_values_helpers(void);
void test_ui_meta_parse_str(void);
void test_ui_meta_parse_float(void);
void test_ui_meta_parse_list(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_meta_parse_int);
    RUN_TEST(test_ui_meta_parse_bool);
    RUN_TEST(test_ui_meta_values_helpers);
    RUN_TEST(test_ui_meta_parse_str);
    RUN_TEST(test_ui_meta_parse_float);
    RUN_TEST(test_ui_meta_parse_list);
    UNITY_END();
}

#else

void test_ui_meta_parse_int(void);
void test_ui_meta_parse_bool(void);
void test_ui_meta_values_helpers(void);
void test_ui_meta_parse_str(void);
void test_ui_meta_parse_float(void);
void test_ui_meta_parse_list(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_meta_parse_int);
    RUN_TEST(test_ui_meta_parse_bool);
    RUN_TEST(test_ui_meta_values_helpers);
    RUN_TEST(test_ui_meta_parse_str);
    RUN_TEST(test_ui_meta_parse_float);
    RUN_TEST(test_ui_meta_parse_list);
    return UNITY_END();
}

#endif

