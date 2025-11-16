#include <string.h>
#include <unity.h>

#include "display_config.h"
#include "ui_render_swbuf.h"

/* Stubs to capture SSD1363 writes */
static uint8_t g_write_buf[64];
static size_t g_write_len = 0;
static int g_write_calls = 0;
static uint16_t g_begin_x0, g_begin_y0, g_begin_x1, g_begin_y1;

esp_err_t ssd1363_begin_frame(uint16_t x0, uint16_t y0, uint16_t x1_incl, uint16_t y1_incl)
{
    g_begin_x0 = x0; g_begin_y0 = y0; g_begin_x1 = x1_incl; g_begin_y1 = y1_incl;
    return ESP_OK;
}

esp_err_t ssd1363_write_data(const uint8_t *data, size_t len)
{
    if (len > sizeof(g_write_buf)) {
        len = sizeof(g_write_buf);
    }
    memcpy(g_write_buf + g_write_len, data, len);
    g_write_len += len;
    g_write_calls++;
    return ESP_OK;
}

/* Unused stubs */
esp_err_t ssd1363_write_cmd(uint8_t cmd) { (void)cmd; return ESP_OK; }
esp_err_t ssd1363_set_addr_window(uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1) {
    (void)x0; (void)x1; (void)y0; (void)y1; return ESP_OK;
}
esp_err_t ssd1363_write_ram_start(void) { return ESP_OK; }

void setUp(void)
{
    memset(g_write_buf, 0, sizeof(g_write_buf));
    g_write_len = 0;
    g_write_calls = 0;
    g_begin_x0 = g_begin_y0 = g_begin_x1 = g_begin_y1 = 0;
}

void tearDown(void) {}

void test_clear_marks_dirty_full_frame(void)
{
    uint8_t fb[8] = {0};
    UiSwBuf b;
    ui_swbuf_init(&b, fb, 16, 4);
    ui_swbuf_clear(&b, 0);

    int x, y, w, h;
    TEST_ASSERT_TRUE(ui_swbuf_get_dirty(&b, &x, &y, &w, &h));
    TEST_ASSERT_EQUAL_INT(0, x);
    TEST_ASSERT_EQUAL_INT(0, y);
    TEST_ASSERT_EQUAL_INT(16, w);
    TEST_ASSERT_EQUAL_INT(4, h);
}

void test_dirty_flush_aligns_bits_to_region(void)
{
    /* width 8, height 1, bits: x1 and x3 set -> 0b01010000 */
    uint8_t fb[1] = {0x50};
    UiSwBuf b;
    ui_swbuf_init(&b, fb, 8, 1);

    ui_swbuf_mark_dirty(&b, 1, 0, 3, 1); /* region x=1..3 */
    ui_swbuf_flush_dirty_ssd1363(&b);

    TEST_ASSERT_EQUAL_UINT16(1, g_begin_x0);
    TEST_ASSERT_EQUAL_UINT16(0, g_begin_y0);
    TEST_ASSERT_EQUAL_UINT16(3, g_begin_x1);
    TEST_ASSERT_EQUAL_UINT16(0, g_begin_y1);
    TEST_ASSERT_EQUAL_INT(1, g_write_calls);
    TEST_ASSERT_EQUAL_size_t(1, g_write_len);
    /* Expected packed bits: x1->bit7=1, x2->bit6=0, x3->bit5=1 => 0b1010 0000 = 0xA0 */
    TEST_ASSERT_EQUAL_UINT8(0xA0, g_write_buf[0]);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_clear_marks_dirty_full_frame);
    RUN_TEST(test_dirty_flush_aligns_bits_to_region);
    return UNITY_END();
}
