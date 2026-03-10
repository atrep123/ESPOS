/*
 * Unit tests for store.c — NVS-backed persistent configuration.
 *
 * Strategy: include the real store.c implementation directly under
 * test-local symbol names to avoid clashes with store_stub.c. NVS functions are
 * provided by nvs_stub.c (in-memory mock).
 *
 * Tests cover:
 * - Init with fresh NVS (NOT_FOUND → defaults written)
 * - Init with existing blob (schema match → loaded)
 * - Init with wrong schema (reset to defaults)
 * - Init NULL out pointer
 * - nvs_flash_init error and retry after erase
 * - get_conf before/after init
 * - set_bg_rgb, set_display_contrast, set_display_invert
 * - set_display_col_offset clamping at 79
 */

#include "unity.h"

#include <string.h>

/* Keep native global store stubs available for other test targets while this
 * suite exercises the real implementation under test-local symbol names. */
#define store_init test_store_real_init
#define store_get_conf test_store_real_get_conf
#define store_set_bg_rgb test_store_real_set_bg_rgb
#define store_set_display_contrast test_store_real_set_display_contrast
#define store_set_display_invert test_store_real_set_display_invert
#define store_set_display_col_offset test_store_real_set_display_col_offset

/* Include the real implementation under renamed symbols. */
#include "services/store/store.c"

#include "nvs_stub_capture.h"

/* store.c has static state that persists across tests.
 * We must carefully order tests: "before init" first, then init, then the rest.
 * Or we can reset by poking the static directly since we #included store.c. */

void setUp(void)
{
    nvs_stub_reset();
    /* Reset store.c statics (accessible since we #included the .c file). */
    s_inited = false;
    g_conf.schema = SCHEMA_VER;
    g_conf.bg_rgb = 0x101010;
    g_conf.display_contrast = 0xFF;
    g_conf.display_invert = 0;
    g_conf.display_col_offset = SSD1363_COL_OFFSET;
    g_conf._reserved0 = 0;
}

void tearDown(void)
{
}

/* ------------------------------------------------------------------ */
/* store_init: NULL out pointer                                        */
/* ------------------------------------------------------------------ */

void test_store_init_null_returns_invalid_arg(void)
{
    esp_err_t err = store_init(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

/* ------------------------------------------------------------------ */
/* store_init: fresh NVS (blob missing) → defaults written             */
/* ------------------------------------------------------------------ */

void test_store_init_fresh_nvs_writes_defaults(void)
{
    /* nvs_get_blob returns NOT_FOUND (default stub behavior). */
    store_conf_t out;
    memset(&out, 0xCC, sizeof(out));

    esp_err_t err = store_init(&out);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    /* Defaults should be returned. */
    TEST_ASSERT_EQUAL(SCHEMA_VER, out.schema);
    TEST_ASSERT_EQUAL_HEX32(0x101010, out.bg_rgb);
    TEST_ASSERT_EQUAL(0xFF, out.display_contrast);
    TEST_ASSERT_EQUAL(0, out.display_invert);
    TEST_ASSERT_EQUAL(SSD1363_COL_OFFSET, out.display_col_offset);

    /* Defaults should have been written to NVS. */
    TEST_ASSERT_EQUAL(1, nvs_stub_set_blob_call_count());
}

/* ------------------------------------------------------------------ */
/* store_init: existing blob with correct schema → loaded              */
/* ------------------------------------------------------------------ */

void test_store_init_existing_blob_loaded(void)
{
    store_conf_t staged = {
        .schema = SCHEMA_VER,
        .bg_rgb = 0xAABBCC,
        .display_contrast = 128,
        .display_invert = 1,
        .display_col_offset = 20,
        ._reserved0 = 0,
    };
    nvs_stub_set_blob(&staged, sizeof(staged));

    store_conf_t out;
    esp_err_t err = store_init(&out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_HEX32(0xAABBCC, out.bg_rgb);
    TEST_ASSERT_EQUAL(128, out.display_contrast);
    TEST_ASSERT_EQUAL(1, out.display_invert);
    TEST_ASSERT_EQUAL(20, out.display_col_offset);

    /* Should NOT have re-written defaults. */
    TEST_ASSERT_EQUAL(0, nvs_stub_set_blob_call_count());
}

/* ------------------------------------------------------------------ */
/* store_init: wrong schema → reset to defaults                        */
/* ------------------------------------------------------------------ */

void test_store_init_wrong_schema_resets(void)
{
    store_conf_t staged = {
        .schema = 999,
        .bg_rgb = 0xAAAAAA,
        .display_contrast = 50,
        .display_invert = 1,
        .display_col_offset = 70,
        ._reserved0 = 0,
    };
    nvs_stub_set_blob(&staged, sizeof(staged));

    store_conf_t out;
    esp_err_t err = store_init(&out);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    /* Should get defaults, not the staged values. */
    TEST_ASSERT_EQUAL(SCHEMA_VER, out.schema);
    TEST_ASSERT_EQUAL_HEX32(0x101010, out.bg_rgb);
    TEST_ASSERT_EQUAL(0xFF, out.display_contrast);
    TEST_ASSERT_EQUAL(1, nvs_stub_set_blob_call_count());
}

/* ------------------------------------------------------------------ */
/* store_init: nvs_flash_init fails with NO_FREE_PAGES → erase+retry  */
/* ------------------------------------------------------------------ */

void test_store_init_flash_erase_retry(void)
{
    nvs_stub_set_flash_init_err(ESP_ERR_NVS_NO_FREE_PAGES);

    store_conf_t out;
    esp_err_t err = store_init(&out);
    /* After erase, nvs_flash_init is called again.
     * Our stub returns the configured error every time, so the second init
     * also returns NO_FREE_PAGES → the function will fail. But the erase+retry
     * path was exercised. */
    TEST_ASSERT_NOT_EQUAL(ESP_OK, err);
}

/* ------------------------------------------------------------------ */
/* store_init: nvs_open fails → error propagated                       */
/* ------------------------------------------------------------------ */

void test_store_init_nvs_open_fails(void)
{
    nvs_stub_set_open_err(ESP_FAIL);

    store_conf_t out;
    esp_err_t err = store_init(&out);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

/* ------------------------------------------------------------------ */
/* store_get_conf: before init → INVALID_STATE                         */
/* ------------------------------------------------------------------ */

void test_get_conf_before_init(void)
{
    store_conf_t out;
    esp_err_t err = store_get_conf(&out);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
}

/* ------------------------------------------------------------------ */
/* store_get_conf: after init → returns current conf                   */
/* ------------------------------------------------------------------ */

void test_get_conf_after_init(void)
{
    store_conf_t init_out;
    TEST_ASSERT_EQUAL(ESP_OK, store_init(&init_out));

    store_conf_t out;
    esp_err_t err = store_get_conf(&out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(init_out.bg_rgb, out.bg_rgb);
}

/* ------------------------------------------------------------------ */
/* store_get_conf: NULL out pointer                                    */
/* ------------------------------------------------------------------ */

void test_get_conf_null_returns_invalid_arg(void)
{
    store_conf_t init_out;
    store_init(&init_out);

    esp_err_t err = store_get_conf(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

/* ------------------------------------------------------------------ */
/* store_set_bg_rgb                                                    */
/* ------------------------------------------------------------------ */

void test_set_bg_rgb_before_init(void)
{
    esp_err_t err = store_set_bg_rgb(0x112233);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
}

void test_set_bg_rgb(void)
{
    store_conf_t out;
    store_init(&out);

    esp_err_t err = store_set_bg_rgb(0x112233);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    store_get_conf(&out);
    TEST_ASSERT_EQUAL_HEX32(0x112233, out.bg_rgb);
}

/* ------------------------------------------------------------------ */
/* store_set_display_contrast                                          */
/* ------------------------------------------------------------------ */

void test_set_display_contrast_before_init(void)
{
    esp_err_t err = store_set_display_contrast(100);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
}

void test_set_display_contrast(void)
{
    store_conf_t out;
    store_init(&out);

    store_set_display_contrast(42);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(42, out.display_contrast);
}

/* ------------------------------------------------------------------ */
/* store_set_display_invert                                            */
/* ------------------------------------------------------------------ */

void test_set_display_invert(void)
{
    store_conf_t out;
    store_init(&out);

    store_set_display_invert(true);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(1, out.display_invert);

    store_set_display_invert(false);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(0, out.display_invert);
}

/* ------------------------------------------------------------------ */
/* store_set_display_col_offset: normal + clamping                     */
/* ------------------------------------------------------------------ */

void test_set_col_offset_normal(void)
{
    store_conf_t out;
    store_init(&out);

    store_set_display_col_offset(30);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(30, out.display_col_offset);
}

void test_set_col_offset_boundary(void)
{
    store_conf_t out;
    store_init(&out);

    store_set_display_col_offset(79);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(79, out.display_col_offset);
}

void test_set_col_offset_clamped(void)
{
    store_conf_t out;
    store_init(&out);

    store_set_display_col_offset(80);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(79, out.display_col_offset);
}

void test_set_col_offset_clamped_max(void)
{
    store_conf_t out;
    store_init(&out);

    store_set_display_col_offset(255);
    store_get_conf(&out);
    TEST_ASSERT_EQUAL(79, out.display_col_offset);
}
