#include "unity.h"

void test_store_init_null_returns_invalid_arg(void);
void test_store_init_fresh_nvs_writes_defaults(void);
void test_store_init_existing_blob_loaded(void);
void test_store_init_wrong_schema_resets(void);
void test_store_init_flash_erase_retry(void);
void test_store_init_nvs_open_fails(void);
void test_get_conf_before_init(void);
void test_get_conf_after_init(void);
void test_get_conf_null_returns_invalid_arg(void);
void test_set_bg_rgb_before_init(void);
void test_set_bg_rgb(void);
void test_set_display_contrast_before_init(void);
void test_set_display_contrast(void);
void test_set_display_invert(void);
void test_set_col_offset_normal(void);
void test_set_col_offset_boundary(void);
void test_set_col_offset_clamped(void);
void test_set_col_offset_clamped_max(void);
void test_store_init_truncated_blob_resets(void);

#ifdef ESP_PLATFORM

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_store_init_null_returns_invalid_arg);
    RUN_TEST(test_store_init_fresh_nvs_writes_defaults);
    RUN_TEST(test_store_init_existing_blob_loaded);
    RUN_TEST(test_store_init_wrong_schema_resets);
    RUN_TEST(test_store_init_flash_erase_retry);
    RUN_TEST(test_store_init_nvs_open_fails);
    RUN_TEST(test_get_conf_before_init);
    RUN_TEST(test_get_conf_after_init);
    RUN_TEST(test_get_conf_null_returns_invalid_arg);
    RUN_TEST(test_set_bg_rgb_before_init);
    RUN_TEST(test_set_bg_rgb);
    RUN_TEST(test_set_display_contrast_before_init);
    RUN_TEST(test_set_display_contrast);
    RUN_TEST(test_set_display_invert);
    RUN_TEST(test_set_col_offset_normal);
    RUN_TEST(test_set_col_offset_boundary);
    RUN_TEST(test_set_col_offset_clamped);
    RUN_TEST(test_set_col_offset_clamped_max);
    RUN_TEST(test_store_init_truncated_blob_resets);
    UNITY_END();
}

#else

#include "unity_internals.h"
#include <stdio.h>

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_store_init_null_returns_invalid_arg);
    RUN_TEST(test_store_init_fresh_nvs_writes_defaults);
    RUN_TEST(test_store_init_existing_blob_loaded);
    RUN_TEST(test_store_init_wrong_schema_resets);
    RUN_TEST(test_store_init_flash_erase_retry);
    RUN_TEST(test_store_init_nvs_open_fails);
    RUN_TEST(test_get_conf_before_init);
    RUN_TEST(test_get_conf_after_init);
    RUN_TEST(test_get_conf_null_returns_invalid_arg);
    RUN_TEST(test_set_bg_rgb_before_init);
    RUN_TEST(test_set_bg_rgb);
    RUN_TEST(test_set_display_contrast_before_init);
    RUN_TEST(test_set_display_contrast);
    RUN_TEST(test_set_display_invert);
    RUN_TEST(test_set_col_offset_normal);
    RUN_TEST(test_set_col_offset_boundary);
    RUN_TEST(test_set_col_offset_clamped);
    RUN_TEST(test_set_col_offset_clamped_max);
    RUN_TEST(test_store_init_truncated_blob_resets);
    return UNITY_END();
}

#endif
