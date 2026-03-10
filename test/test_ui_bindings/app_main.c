#include "unity.h"

#ifdef ESP_PLATFORM

void app_main(void)
{
    UNITY_BEGIN();
    UNITY_END();
}

#else

void test_ui_bind_int_generic(void);
void test_ui_bind_bool_generic(void);
void test_ui_bind_str_generic(void);
void test_ui_bind_clear_all(void);
void test_ui_bind_null_key(void);
void test_ui_bind_store_full(void);
void test_ui_bind_overwrite(void);
void test_ui_bind_str_null_value(void);
void test_ui_bind_int_hw_contrast(void);
void test_ui_bind_bool_hw_invert(void);
void test_ui_bind_set_int_contrast_clamped(void);
void test_ui_bind_set_int_col_offset(void);
void test_ui_bind_set_bool_generic(void);
void test_ui_bind_set_str_truncation(void);
void test_ui_bind_set_bool_store_full(void);
void test_ui_bind_set_str_empty_key(void);
void test_ui_bind_get_str_small_buf(void);
void test_ui_bind_int_negative_value(void);
void test_ui_bind_contrast_boundary_adjacent(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_bind_int_generic);
    RUN_TEST(test_ui_bind_bool_generic);
    RUN_TEST(test_ui_bind_str_generic);
    RUN_TEST(test_ui_bind_clear_all);
    RUN_TEST(test_ui_bind_null_key);
    RUN_TEST(test_ui_bind_store_full);
    RUN_TEST(test_ui_bind_overwrite);
    RUN_TEST(test_ui_bind_str_null_value);
    RUN_TEST(test_ui_bind_int_hw_contrast);
    RUN_TEST(test_ui_bind_bool_hw_invert);
    RUN_TEST(test_ui_bind_set_int_contrast_clamped);
    RUN_TEST(test_ui_bind_set_int_col_offset);
    RUN_TEST(test_ui_bind_set_bool_generic);
    RUN_TEST(test_ui_bind_set_str_truncation);
    RUN_TEST(test_ui_bind_set_bool_store_full);
    RUN_TEST(test_ui_bind_set_str_empty_key);
    RUN_TEST(test_ui_bind_get_str_small_buf);
    RUN_TEST(test_ui_bind_int_negative_value);
    RUN_TEST(test_ui_bind_contrast_boundary_adjacent);
    return UNITY_END();
}

#endif
