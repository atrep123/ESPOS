/*
 * Unit tests for seesaw.c — the I2C seesaw protocol layer.
 *
 * Tests cover:
 * - Raw read/write with I2C stub (success & error paths)
 * - Big-endian decoding: read_u8, read_u16, read_u32, read_i32
 * - Defensive limits (write >64 bytes, NULL out pointers)
 * - pin_mode_bulk encoding and multi-step writes
 * - hw_id_supported for known and unknown IDs
 */

#include "unity.h"

#include <string.h>

#include "services/input/seesaw.h"
#include "i2c_stub_capture.h"

#define TEST_ADDR 0x50

void setUp(void)
{
    i2c_stub_reset();
}

void tearDown(void)
{
}

/* ------------------------------------------------------------------ */
/* seesaw_read: basic success path                                     */
/* ------------------------------------------------------------------ */

void test_read_sends_prefix_and_returns_data(void)
{
    uint8_t staged[] = { 0xAB, 0xCD };
    i2c_stub_set_read_data(staged, sizeof(staged));

    uint8_t out[2] = { 0 };
    esp_err_t err = seesaw_read(TEST_ADDR, 0x01, 0x04, out, 2);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_HEX8(0xAB, out[0]);
    TEST_ASSERT_EQUAL_HEX8(0xCD, out[1]);

    /* Verify the 2-byte prefix was written. */
    TEST_ASSERT_EQUAL(1, i2c_stub_write_call_count());
    uint8_t wr[4];
    size_t n = i2c_stub_copy_last_write(wr, sizeof(wr));
    TEST_ASSERT_EQUAL(2, n);
    TEST_ASSERT_EQUAL_HEX8(0x01, wr[0]); /* base */
    TEST_ASSERT_EQUAL_HEX8(0x04, wr[1]); /* reg */
}

/* ------------------------------------------------------------------ */
/* seesaw_read: NULL / zero-length early returns                       */
/* ------------------------------------------------------------------ */

void test_read_null_out_returns_invalid_arg(void)
{
    esp_err_t err = seesaw_read(TEST_ADDR, 0x01, 0x04, NULL, 2);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
    TEST_ASSERT_EQUAL(0, i2c_stub_write_call_count());
}

void test_read_zero_len_returns_ok(void)
{
    uint8_t out[1] = { 0xFF };
    esp_err_t err = seesaw_read(TEST_ADDR, 0x01, 0x04, out, 0);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(0, i2c_stub_write_call_count());
}

/* ------------------------------------------------------------------ */
/* seesaw_read: write error propagation                                */
/* ------------------------------------------------------------------ */

void test_read_write_error_propagates(void)
{
    i2c_stub_set_write_err(ESP_FAIL);
    uint8_t out[1] = { 0 };
    esp_err_t err = seesaw_read(TEST_ADDR, 0x01, 0x04, out, 1);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
    /* No read should have been attempted. */
    TEST_ASSERT_EQUAL(0, i2c_stub_read_call_count());
}

/* ------------------------------------------------------------------ */
/* seesaw_read: read error propagation                                 */
/* ------------------------------------------------------------------ */

void test_read_i2c_read_error_propagates(void)
{
    i2c_stub_set_read_err(ESP_FAIL);
    uint8_t out[1] = { 0 };
    esp_err_t err = seesaw_read(TEST_ADDR, 0x01, 0x04, out, 1);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

/* ------------------------------------------------------------------ */
/* seesaw_write: basic success path                                    */
/* ------------------------------------------------------------------ */

void test_write_sends_prefix_plus_data(void)
{
    uint8_t payload[] = { 0x11, 0x22 };
    esp_err_t err = seesaw_write(TEST_ADDR, 0x09, 0x07, payload, sizeof(payload));
    TEST_ASSERT_EQUAL(ESP_OK, err);

    TEST_ASSERT_EQUAL(1, i2c_stub_write_call_count());
    uint8_t wr[8];
    size_t n = i2c_stub_copy_last_write(wr, sizeof(wr));
    TEST_ASSERT_EQUAL(4, n); /* 2 prefix + 2 data */
    TEST_ASSERT_EQUAL_HEX8(0x09, wr[0]); /* base */
    TEST_ASSERT_EQUAL_HEX8(0x07, wr[1]); /* reg */
    TEST_ASSERT_EQUAL_HEX8(0x11, wr[2]);
    TEST_ASSERT_EQUAL_HEX8(0x22, wr[3]);
}

/* ------------------------------------------------------------------ */
/* seesaw_write: NULL data, zero length                                */
/* ------------------------------------------------------------------ */

void test_write_null_data_zero_len(void)
{
    esp_err_t err = seesaw_write(TEST_ADDR, 0x00, 0x01, NULL, 0);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    /* Prefix only (2 bytes). */
    TEST_ASSERT_EQUAL(2, i2c_stub_last_write_len());
}

/* ------------------------------------------------------------------ */
/* seesaw_write: >64 bytes rejected                                    */
/* ------------------------------------------------------------------ */

void test_write_over_64_returns_invalid_size(void)
{
    uint8_t big[65] = { 0 };
    esp_err_t err = seesaw_write(TEST_ADDR, 0x01, 0x02, big, 65);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_SIZE, err);
    TEST_ASSERT_EQUAL(0, i2c_stub_write_call_count());
}

/* ------------------------------------------------------------------ */
/* seesaw_read_u8                                                      */
/* ------------------------------------------------------------------ */

void test_read_u8_success(void)
{
    uint8_t staged = 0x42;
    i2c_stub_set_read_data(&staged, 1);

    uint8_t out = 0;
    esp_err_t err = seesaw_read_u8(TEST_ADDR, 0x00, 0x01, &out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_HEX8(0x42, out);
}

void test_read_u8_null_returns_invalid_arg(void)
{
    esp_err_t err = seesaw_read_u8(TEST_ADDR, 0x00, 0x01, NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

/* ------------------------------------------------------------------ */
/* seesaw_read_u16: big-endian decode                                  */
/* ------------------------------------------------------------------ */

void test_read_u16_big_endian(void)
{
    uint8_t staged[] = { 0xAB, 0xCD };
    i2c_stub_set_read_data(staged, 2);

    uint16_t out = 0;
    esp_err_t err = seesaw_read_u16(TEST_ADDR, 0x09, 0x07, &out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_HEX16(0xABCD, out);
}

void test_read_u16_null_returns_invalid_arg(void)
{
    esp_err_t err = seesaw_read_u16(TEST_ADDR, 0x09, 0x07, NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_read_u16_error_propagates(void)
{
    i2c_stub_set_read_err(ESP_FAIL);
    uint16_t out = 0;
    esp_err_t err = seesaw_read_u16(TEST_ADDR, 0x09, 0x07, &out);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

/* ------------------------------------------------------------------ */
/* seesaw_read_u32: big-endian decode                                  */
/* ------------------------------------------------------------------ */

void test_read_u32_big_endian(void)
{
    uint8_t staged[] = { 0xDE, 0xAD, 0xBE, 0xEF };
    i2c_stub_set_read_data(staged, 4);

    uint32_t out = 0;
    esp_err_t err = seesaw_read_u32(TEST_ADDR, 0x00, 0x02, &out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_HEX32(0xDEADBEEF, out);
}

void test_read_u32_null_returns_invalid_arg(void)
{
    esp_err_t err = seesaw_read_u32(TEST_ADDR, 0x00, 0x02, NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

/* ------------------------------------------------------------------ */
/* seesaw_read_i32: signed big-endian decode                           */
/* ------------------------------------------------------------------ */

void test_read_i32_positive(void)
{
    uint8_t staged[] = { 0x00, 0x00, 0x00, 0x03 };
    i2c_stub_set_read_data(staged, 4);

    int32_t out = 0;
    esp_err_t err = seesaw_read_i32(TEST_ADDR, 0x11, 0x40, &out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_INT32(3, out);
}

void test_read_i32_negative(void)
{
    /* -1 in 2's complement = 0xFFFFFFFF */
    uint8_t staged[] = { 0xFF, 0xFF, 0xFF, 0xFF };
    i2c_stub_set_read_data(staged, 4);

    int32_t out = 0;
    esp_err_t err = seesaw_read_i32(TEST_ADDR, 0x11, 0x40, &out);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_INT32(-1, out);
}

void test_read_i32_null_returns_invalid_arg(void)
{
    esp_err_t err = seesaw_read_i32(TEST_ADDR, 0x11, 0x40, NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_read_i32_error_propagates(void)
{
    i2c_stub_set_write_err(ESP_FAIL);
    int32_t out = 0;
    esp_err_t err = seesaw_read_i32(TEST_ADDR, 0x11, 0x40, &out);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

/* ------------------------------------------------------------------ */
/* seesaw_pin_mode_bulk: INPUT mode                                    */
/* ------------------------------------------------------------------ */

void test_pin_mode_bulk_input(void)
{
    esp_err_t err = seesaw_pin_mode_bulk(TEST_ADDR, 0x00FF0000, SEESAW_PIN_INPUT);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    /* One write: prefix [GPIO_BASE, DIRCLR_BULK] + 4 mask bytes big-endian */
    TEST_ASSERT_EQUAL(1, i2c_stub_write_call_count());
    uint8_t wr[8];
    size_t n = i2c_stub_copy_last_write(wr, sizeof(wr));
    TEST_ASSERT_EQUAL(6, n);
    TEST_ASSERT_EQUAL_HEX8(SEESAW_GPIO_BASE, wr[0]);
    TEST_ASSERT_EQUAL_HEX8(SEESAW_GPIO_DIRCLR_BULK, wr[1]);
    /* mask 0x00FF0000 big-endian */
    TEST_ASSERT_EQUAL_HEX8(0x00, wr[2]);
    TEST_ASSERT_EQUAL_HEX8(0xFF, wr[3]);
    TEST_ASSERT_EQUAL_HEX8(0x00, wr[4]);
    TEST_ASSERT_EQUAL_HEX8(0x00, wr[5]);
}

/* ------------------------------------------------------------------ */
/* seesaw_pin_mode_bulk: INPUT_PULLUP mode (3 sequential writes)       */
/* ------------------------------------------------------------------ */

void test_pin_mode_bulk_input_pullup(void)
{
    esp_err_t err = seesaw_pin_mode_bulk(TEST_ADDR, 0x0000000F, SEESAW_PIN_INPUT_PULLUP);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    /* Should issue 3 writes: DIRCLR_BULK, PULLENSET, BULK_SET */
    TEST_ASSERT_EQUAL(3, i2c_stub_write_call_count());

    /* Last write should be BULK_SET. */
    uint8_t wr[8];
    size_t n = i2c_stub_copy_last_write(wr, sizeof(wr));
    TEST_ASSERT_EQUAL(6, n);
    TEST_ASSERT_EQUAL_HEX8(SEESAW_GPIO_BASE, wr[0]);
    TEST_ASSERT_EQUAL_HEX8(SEESAW_GPIO_BULK_SET, wr[1]);
    TEST_ASSERT_EQUAL_HEX8(0x00, wr[2]);
    TEST_ASSERT_EQUAL_HEX8(0x00, wr[3]);
    TEST_ASSERT_EQUAL_HEX8(0x00, wr[4]);
    TEST_ASSERT_EQUAL_HEX8(0x0F, wr[5]);
}

/* ------------------------------------------------------------------ */
/* seesaw_pin_mode_bulk: INPUT_PULLUP with first write failing         */
/* ------------------------------------------------------------------ */

void test_pin_mode_bulk_pullup_write_error_aborts(void)
{
    i2c_stub_set_write_err(ESP_FAIL);
    esp_err_t err = seesaw_pin_mode_bulk(TEST_ADDR, 0x01, SEESAW_PIN_INPUT_PULLUP);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
    /* Should have attempted exactly one write before bailing. */
    TEST_ASSERT_EQUAL(1, i2c_stub_write_call_count());
}

/* ------------------------------------------------------------------ */
/* seesaw_pin_mode_bulk: invalid mode                                  */
/* ------------------------------------------------------------------ */

void test_pin_mode_bulk_invalid_mode(void)
{
    esp_err_t err = seesaw_pin_mode_bulk(TEST_ADDR, 0x01, (seesaw_pin_mode_t)99);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

/* ------------------------------------------------------------------ */
/* seesaw_hw_id_supported                                              */
/* ------------------------------------------------------------------ */

void test_hw_id_supported_known(void)
{
    TEST_ASSERT_TRUE(seesaw_hw_id_supported(SEESAW_HW_ID_CODE_SAMD09));
    TEST_ASSERT_TRUE(seesaw_hw_id_supported(SEESAW_HW_ID_CODE_TINY817));
    TEST_ASSERT_TRUE(seesaw_hw_id_supported(SEESAW_HW_ID_CODE_TINY1616));
    TEST_ASSERT_TRUE(seesaw_hw_id_supported(SEESAW_HW_ID_CODE_TINY1617));
}

void test_hw_id_supported_unknown(void)
{
    TEST_ASSERT_FALSE(seesaw_hw_id_supported(0x00));
    TEST_ASSERT_FALSE(seesaw_hw_id_supported(0x01));
    TEST_ASSERT_FALSE(seesaw_hw_id_supported(0xFF));
}
