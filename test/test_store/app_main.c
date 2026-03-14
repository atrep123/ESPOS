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
void test_set_display_invert_before_init(void);
void test_store_double_init_returns_cached(void);
void test_set_col_offset_zero(void);
void test_store_init_new_version_found_erases(void);
void test_set_bg_rgb_open_failure_rollback(void);
void test_store_init_mutex_failure_returns_no_mem(void);
void test_store_deinit_no_crash(void);
void test_store_deinit_then_reinit(void);
void test_store_deinit_before_init_no_crash(void);

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
    RUN_TEST(test_set_display_invert_before_init);
    RUN_TEST(test_store_double_init_returns_cached);
    RUN_TEST(test_set_col_offset_zero);
    RUN_TEST(test_store_init_new_version_found_erases);
    RUN_TEST(test_set_bg_rgb_open_failure_rollback);
    RUN_TEST(test_store_init_mutex_failure_returns_no_mem);
    RUN_TEST(test_store_deinit_no_crash);
    RUN_TEST(test_store_deinit_then_reinit);
    RUN_TEST(test_store_deinit_before_init_no_crash);
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
    RUN_TEST(test_set_display_invert_before_init);
    RUN_TEST(test_store_double_init_returns_cached);
    RUN_TEST(test_set_col_offset_zero);
    RUN_TEST(test_store_init_new_version_found_erases);
    RUN_TEST(test_set_bg_rgb_open_failure_rollback);
    RUN_TEST(test_store_init_mutex_failure_returns_no_mem);
    RUN_TEST(test_store_deinit_no_crash);
    RUN_TEST(test_store_deinit_then_reinit);
    RUN_TEST(test_store_deinit_before_init_no_crash);
    return UNITY_END();
}

#endif
