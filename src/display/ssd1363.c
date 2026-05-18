#include "display/ssd1363.h"

#include "driver/gpio.h"
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#include "display_config.h"
#include <string.h>
#include <stdbool.h>

static const char *TAG = "ssd1363";

#define I2C_TIMEOUT_MS 1000
#define I2C_SCAN_TIMEOUT_MS 20
#define I2C_SCAN_MAX_ADDR 0x7F

static bool s_i2c_inited = false;
static uint8_t s_col_offset_units = SSD1363_COL_OFFSET;

#define SSD1363_MAX_COL_ADDR 79U

static esp_err_t ssd1363_write_cmd_args(uint8_t cmd, const uint8_t *args, size_t arg_len)
{
    if (args == NULL || arg_len == 0) {
        return ssd1363_write_cmd(cmd);
    }
    if (arg_len > 8) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t buf[1 + 8];
    buf[0] = cmd;
    memcpy(buf + 1, args, arg_len);
    return ssd1363_write_cmd_list(buf, 1 + arg_len);
}

static esp_err_t ssd1363_cmd_unlock(void)
{
    const uint8_t arg = 0x12; /* unlock */
    return ssd1363_write_cmd_args(0xFD, &arg, 1);
}

/* Probe a single 7-bit I2C address: returns ESP_OK if the device ACKs,
 * ESP_ERR_NOT_FOUND if not, or the underlying bus error. */
static esp_err_t ssd1363_probe_addr(uint8_t addr7)
{
    if (!s_i2c_inited) {
        return ESP_ERR_INVALID_STATE;
    }
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    if (cmd == NULL) {
        return ESP_ERR_NO_MEM;
    }
    esp_err_t err = i2c_master_start(cmd);
    if (err == ESP_OK) {
        err = i2c_master_write_byte(cmd, (uint8_t)((addr7 << 1) | I2C_MASTER_WRITE), true);
    }
    if (err == ESP_OK) {
        err = i2c_master_stop(cmd);
    }
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }
    err = i2c_master_cmd_begin(DISPLAY_I2C_PORT, cmd, pdMS_TO_TICKS(I2C_SCAN_TIMEOUT_MS));
    i2c_cmd_link_delete(cmd);
    if (err == ESP_OK) {
        return ESP_OK;
    }
    if (err == ESP_ERR_TIMEOUT || err == ESP_FAIL) {
        /* No ACK from this address. */
        return ESP_ERR_NOT_FOUND;
    }
    return err;
}

esp_err_t ssd1363_probe(void)
{
    esp_err_t err = ssd1363_probe_addr(DISPLAY_I2C_ADDR);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "SSD1363 ACK at I2C addr 0x%02X", DISPLAY_I2C_ADDR);
    } else if (err == ESP_ERR_NOT_FOUND) {
        ESP_LOGE(TAG, "SSD1363 did NOT ACK at I2C addr 0x%02X (no panel / wrong addr / wiring)",
                 DISPLAY_I2C_ADDR);
    } else {
        ESP_LOGE(TAG, "SSD1363 probe bus error at 0x%02X: %s",
                 DISPLAY_I2C_ADDR, esp_err_to_name(err));
    }
    return err;
}

#if SSD1363_I2C_SCAN_ON_BOOT
static void ssd1363_scan_i2c(void)
{
    ESP_LOGI(TAG, "I2C scan (port=%d) ...", DISPLAY_I2C_PORT);
    int found = 0;
    int found_display = 0;

    for (int addr = 1; addr < I2C_SCAN_MAX_ADDR; ++addr) {
        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        if (cmd == NULL) {
            ESP_LOGE(TAG, "i2c_cmd_link_create failed during scan");
            return;
        }
        esp_err_t err = i2c_master_start(cmd);
        if (err == ESP_OK) {
            err = i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
        }
        if (err == ESP_OK) {
            err = i2c_master_stop(cmd);
        }
        if (err != ESP_OK) {
            i2c_cmd_link_delete(cmd);
            continue;
        }

        err = i2c_master_cmd_begin(DISPLAY_I2C_PORT, cmd, pdMS_TO_TICKS(I2C_SCAN_TIMEOUT_MS));
        i2c_cmd_link_delete(cmd);

        if (err == ESP_OK) {
            found += 1;
            if (addr == DISPLAY_I2C_ADDR) {
                found_display = 1;
            }
            ESP_LOGI(TAG, "I2C device @0x%02X", addr);
        } else if (err != ESP_ERR_TIMEOUT && err != ESP_FAIL) {
            ESP_LOGW(TAG, "I2C scan addr 0x%02X: %s", addr, esp_err_to_name(err));
        }
    }

    if (found == 0) {
        ESP_LOGW(TAG, "I2C scan: no devices found");
        return;
    }
    if (!found_display) {
        ESP_LOGW(TAG, "I2C scan: DISPLAY_I2C_ADDR=0x%02X not found", DISPLAY_I2C_ADDR);
    }
}
#endif

#if SSD1363_BOOT_TEST_PATTERN
static esp_err_t ssd1363_boot_test_pattern(void)
{
    ESP_LOGI(TAG, "SSD1363 boot test pattern");

    esp_err_t err = ssd1363_begin_frame(0, 0, (uint16_t)(DISPLAY_WIDTH - 1), (uint16_t)(DISPLAY_HEIGHT - 1));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "begin_frame failed: %d", err);
        return err;
    }

#if DISPLAY_COLOR_BITS == 4
    const int row_bytes = (DISPLAY_WIDTH + 1) / 2;
    uint8_t line[(DISPLAY_WIDTH + 1) / 2];
    for (int y = 0; y < DISPLAY_HEIGHT; ++y) {
        for (int bx = 0; bx < row_bytes; ++bx) {
            uint8_t v = 0x0F;
            if (row_bytes > 1) {
                v = (uint8_t)((bx * 15) / (row_bytes - 1));
            }
            if (y & 1) {
                v = (uint8_t)(v ^ 0x0F);
            }
            line[bx] = (uint8_t)((uint8_t)(v << 4) | (v & 0x0F));
        }
        err = ssd1363_write_data(line, (size_t)row_bytes);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "write_data failed (row=%d): %d", y, err);
            return err;
        }
    }
    return ESP_OK;
#else
    const int row_bytes = (DISPLAY_WIDTH + 7) / 8;
    uint8_t line[(DISPLAY_WIDTH + 7) / 8];
    for (int y = 0; y < DISPLAY_HEIGHT; ++y) {
        memset(line, (y & 1) ? 0xAA : 0x55, (size_t)row_bytes);
        err = ssd1363_write_data(line, (size_t)row_bytes);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "write_data failed (row=%d): %d", y, err);
            return err;
        }
    }
    return ESP_OK;
#endif
}
#endif

esp_err_t ssd1363_bus_init(void)
{
    if (s_i2c_inited) {
        return ESP_OK;
    }

    if (DISPLAY_I2C_SDA_GPIO < 0 || DISPLAY_I2C_SCL_GPIO < 0) {
        ESP_LOGE(TAG, "DISPLAY_I2C_SDA_GPIO / DISPLAY_I2C_SCL_GPIO are not set");
        return ESP_ERR_INVALID_STATE;
    }

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = DISPLAY_I2C_SDA_GPIO,
        .scl_io_num = DISPLAY_I2C_SCL_GPIO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = DISPLAY_I2C_FREQ_HZ,
        .clk_flags = 0,
    };

    esp_err_t err = i2c_param_config(DISPLAY_I2C_PORT, &conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_param_config failed: %d", err);
        return err;
    }

    err = i2c_driver_install(DISPLAY_I2C_PORT, conf.mode, 0, 0, 0);
    if (err == ESP_ERR_INVALID_STATE) {
        /* Driver already installed, treat as success. */
        s_i2c_inited = true;
        return ESP_OK;
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_driver_install failed: %d", err);
        return err;
    }

    s_i2c_inited = true;
    ESP_LOGI(TAG, "I2C bus initialised on SDA=%d SCL=%d freq=%d Hz",
             DISPLAY_I2C_SDA_GPIO, DISPLAY_I2C_SCL_GPIO, DISPLAY_I2C_FREQ_HZ);
    return ESP_OK;
}

esp_err_t ssd1363_reset(void)
{
    /* If reset pin is not configured, nothing to do. */
#if DISPLAY_RST_GPIO < 0
    return ESP_OK;
#else
    gpio_config_t io_conf = {
        .pin_bit_mask = 1ULL << DISPLAY_RST_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&io_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "gpio_config(reset) failed: %d", err);
        return err;
    }

    gpio_set_level(DISPLAY_RST_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(DISPLAY_RST_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(10));

    ESP_LOGI(TAG, "Panel reset pulse sent on GPIO %d", DISPLAY_RST_GPIO);
    return ESP_OK;
#endif
}

static esp_err_t ssd1363_send_bytes(bool is_cmd, const uint8_t *data, size_t len)
{
    if (!s_i2c_inited) {
        ESP_LOGE(TAG, "I2C bus not initialised, call ssd1363_bus_init() first");
        return ESP_ERR_INVALID_STATE;
    }
    if (data == NULL || len == 0) {
        return ESP_OK;
    }

    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    if (cmd == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = i2c_master_start(cmd);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_write_byte(cmd, (DISPLAY_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    /* Control byte: Co=0, D/C# = 0 for command, 1 for data.
     * This matches the typical SSD13xx I2C protocol.
     */
    uint8_t control = is_cmd ? 0x00 : 0x40;
    err = i2c_master_write_byte(cmd, control, true);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_write(cmd, (uint8_t *)data, len, true);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_stop(cmd);
    if (err != ESP_OK) {
        i2c_cmd_link_delete(cmd);
        return err;
    }

    err = i2c_master_cmd_begin(DISPLAY_I2C_PORT,
                               cmd,
                               pdMS_TO_TICKS(I2C_TIMEOUT_MS));
    i2c_cmd_link_delete(cmd);

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_master_cmd_begin failed: %d", err);
    }
    return err;
}

esp_err_t ssd1363_write_cmd(uint8_t cmd_byte)
{
    return ssd1363_send_bytes(true, &cmd_byte, 1);
}

esp_err_t ssd1363_write_cmd_list(const uint8_t *cmds, size_t len)
{
    return ssd1363_send_bytes(true, cmds, len);
}

esp_err_t ssd1363_write_data(const uint8_t *data, size_t len)
{
    return ssd1363_send_bytes(false, data, len);
}

esp_err_t ssd1363_init_panel(void)
{
    esp_err_t err = ssd1363_bus_init();
    if (err != ESP_OK) {
        return err;
    }

    err = ssd1363_reset();
    if (err != ESP_OK) {
        return err;
    }

#if SSD1363_I2C_SCAN_ON_BOOT
    ssd1363_scan_i2c();
#endif

    /* Failure detection (root-cause fix for "init always returns OK"):
     * before sending any init bytes, verify the panel actually ACKs its
     * I2C address. The write-only SSD1363 command path cannot be read
     * back, but a missing ACK is a definitive, detectable signal that the
     * panel is absent / mis-wired / on the wrong address. Without this the
     * old code happily streamed the whole init to a NAKing bus and still
     * returned ESP_OK, producing a silent blank screen with no diagnostic.
     *
     * Gated by SSD1363_REQUIRE_PROBE so bring-up on exotic bus expanders
     * that don't ACK cleanly can still opt out (defaults to required). */
#if SSD1363_REQUIRE_PROBE
    err = ssd1363_probe();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Aborting init: SSD1363 not detected on I2C "
                      "(set -DSSD1363_REQUIRE_PROBE=0 to bypass for bring-up)");
        return (err == ESP_ERR_NOT_FOUND) ? ESP_ERR_NOT_FOUND : err;
    }
#else
    /* Probe is advisory only; still log so a blank screen is explainable. */
    (void)ssd1363_probe();
#endif

    /* Clamp runtime column offset against current DISPLAY_WIDTH. */
    err = ssd1363_set_col_offset_units(ssd1363_get_col_offset_units());
    if (err != ESP_OK) {
        return err;
    }

    /* ===================================================================
     * SSD1363 256x128 init sequence.
     *
     * !!! UNVERIFIED-ON-HARDWARE !!!  Best-effort, sourced per command
     * against olikraus/u8g2 csrc/u8x8_d_ssd1363.c (master branch,
     * u8x8_d_ssd1363_256x128_init_seq[]) which is the de-facto reference
     * for this controller (Solomon Systech SSD1363, 320x160 GDDRAM, 16
     * gray levels). Order and values below were cross-checked byte-for-byte
     * against that array; the U8g2 array itself is annotated "(midas
     * datasheet)" by its author. No public Solomon Systech SSD1363
     * datasheet PDF was retrievable to independently confirm bitfields, so
     * every register here remains a tuning candidate via SSD1363_INIT_*.
     *
     * Per-command source map (cmd : U8g2 ref line : note):
     *   0xFD,0x12  unlock                 : U8X8_CA(0xfd,0x12)
     *   0xAE       display off            : U8X8_C(0xae)
     *   0xB3,clk   clock/osc              : U8X8_CA(0xb3,0x30)   default 0x30
     *   0xCA,mux   multiplex ratio        : U8X8_CA(0xca,127)    127 == 0x7F
     *   0xA2,off   display offset         : U8X8_CA(0xa2,0x20)   default 0x20
     *   0xA1,sl    start line             : U8X8_CA(0xa1,0x00)
     *   0xA0,a,b   remap / dual-COM       : U8X8_CAA(0xa0,0x32,0x00)
     *   0xB4,a,b   display enhancement A  : U8X8_CAA(0xb4,0x32,0x0c)
     *   0xC1,ct    contrast               : U8X8_CA(0xc1,0xff)   0..255
     *   0xBA,v     Vp voltage config      : U8X8_CA(0xba,0x03)
     *   0xB9       linear grayscale       : U8X8_C(0xb9)
     *   0xAD,ir    IREF (0x90 int/0x80 ext): U8X8_CA(0xad,0x90)
     *   0xB1,ph    phase1/2 period        : U8X8_CA(0xb1,0x74)
     *   0xBB,pv    precharge voltage      : U8X8_CA(0xbb,0x0c)
     *   0xB6,sp    second precharge       : U8X8_CA(0xb6,0xc8)
     *   0xBE,vc    VCOMH                  : U8X8_CA(0xbe,0x04)
     *   0xA6       normal (non-invert)    : U8X8_C(0xa6)
     *   0xA9       exit partial display   : U8X8_C(0xa9)
     *
     * Known-correct cross-checks (do NOT "fix" these):
     *  - default_x_offset == 8 byte-columns matches SSD1363_COL_OFFSET=8;
     *    the GDDRAM is 320 wide, panel 256, (320-256)/2=32px, 32px/4=8
     *    column-units. ssd1363_set_addr_window() computes
     *    col = 8 + (pixel_x>>2) which equals U8g2's x*2+8 per 8px tile.
     *  - 0xA6 (normal) is correct; 0xA4/0xA5 are entire-display-on, a
     *    different command (was a documented confusion in U8g2 #2298).
     *  - 0x5C "write RAM" must precede each data block; see
     *    ssd1363_begin_frame()/ssd1363_write_ram_start().
     *
     * Concrete discrepancy fixed here:
     *  - Multiplex ratio previously used (DISPLAY_HEIGHT-1). For the 128px
     *    panel that is 127, which coincidentally equals U8g2's literal 127,
     *    but the "-1" form is wrong for SSD1363: U8g2 programs the MUX as
     *    the literal active-COM count (127 for a 128-row visible area on a
     *    160-COM part), not height-1 in the SSD13xx "ratio = N-1" sense.
     *    Now driven by SSD1363_INIT_MUX_RATIO (default 127) so it tracks
     *    the reference exactly and is tunable. UNVERIFIED-ON-HARDWARE.
     * =================================================================== */
#if SSD1363_USE_DEFAULT_INIT
    err = ssd1363_cmd_unlock();                                  /* 0xFD,0x12 unlock — U8g2 ref. UNVERIFIED-ON-HARDWARE */
    if (err != ESP_OK) {
        return err;
    }

    err = ssd1363_display_off();                                 /* 0xAE display off — U8g2 ref. UNVERIFIED-ON-HARDWARE */
    if (err != ESP_OK) {
        return err;
    }

    /* 0xB3 clock divide / osc freq (1 byte). Src: U8X8_CA(0xb3,0x30). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xB3, (const uint8_t[]){ SSD1363_INIT_CLOCK }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xCA multiplex ratio (1 byte). Src: U8X8_CA(0xca,127). NOTE: literal
     * active-COM count, NOT (height-1). Driven by SSD1363_INIT_MUX_RATIO
     * (default 127) to match U8g2 exactly. UNVERIFIED-ON-HARDWARE */
    err = ssd1363_set_multiplex_ratio((uint8_t)SSD1363_INIT_MUX_RATIO);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xA2 display offset (1 byte). Src: U8X8_CA(0xa2,0x20). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_set_display_offset(SSD1363_INIT_DISPLAY_OFFSET);
    if (err != ESP_OK) {
        return err;
    }
    /* 0xA1 display start line (1 byte). Src: U8X8_CA(0xa1,0x00). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_set_start_line(SSD1363_INIT_START_LINE);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xA0 re-map / dual-COM (2 bytes). Src: U8X8_CAA(0xa0,0x32,0x00).
     * Bit semantics (per U8g2 inline comment): A[0] addr-increment dir,
     * A[1] column re-map, A[4] COM scan dir, A[5] COM split odd/even,
     * B[4] dual-COM enable (only when MUX<=79). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xA0, (const uint8_t[]){ SSD1363_INIT_REMAP_A, SSD1363_INIT_REMAP_B }, 2);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xB4 display enhancement A (2 bytes). Src: U8X8_CAA(0xb4,0x32,0x0c).
     * Undocumented in U8g2 ("NOT DOCUMENTED"); kept as-is. UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xB4, (const uint8_t[]){ SSD1363_INIT_ENH_A0, SSD1363_INIT_ENH_A1 }, 2);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xC1 contrast (1 byte, 0..255). Src: U8X8_CA(0xc1,0xff). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_set_contrast(SSD1363_INIT_CONTRAST);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xBA Vp voltage config (1 byte). Src: U8X8_CA(0xba,0x03). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xBA, (const uint8_t[]){ SSD1363_INIT_VOLTAGE_CONFIG }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xB9 linear grayscale table (no args). Src: U8X8_C(0xb9). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd(0xB9);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xAD IREF select (1 byte; 0x90 internal / 0x80 external). Src:
     * U8X8_CA(0xad,0x90). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xAD, (const uint8_t[]){ SSD1363_INIT_IREF }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xB1 phase 1/2 (reset/precharge) period (1 byte). Src:
     * U8X8_CA(0xb1,0x74). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_set_precharge(SSD1363_INIT_PHASE_LENGTH);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xBB precharge voltage (1 byte). Src: U8X8_CA(0xbb,0x0c). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xBB, (const uint8_t[]){ SSD1363_INIT_PRECHARGE_VOLTAGE }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xB6 second precharge period (1 byte). Src: U8X8_CA(0xb6,0xc8). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd_args(0xB6, (const uint8_t[]){ SSD1363_INIT_SECOND_PRECHARGE }, 1);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xBE VCOMH (1 byte). Src: U8X8_CA(0xbe,0x04). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_set_vcomh(SSD1363_INIT_VCOMH);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xA6 normal (non-inverted) display. Src: U8X8_C(0xa6). NOTE: this is
     * NOT 0xA4/0xA5 (entire-display-on) — that confusion caused blank/all-on
     * screens in U8g2 #2298. UNVERIFIED-ON-HARDWARE */
    err = ssd1363_invert_display(false);
    if (err != ESP_OK) {
        return err;
    }

    /* 0xA9 exit partial display. Src: U8X8_C(0xa9). UNVERIFIED-ON-HARDWARE */
    err = ssd1363_write_cmd(0xA9);
    if (err != ESP_OK) {
        return err;
    }
#else
    /* Minimal init for custom bring-up: unlock + display off.
     * Root-cause fix: previously these used (void) casts and discarded
     * the I2C error, so init reported success on a dead bus. Propagate. */
    err = ssd1363_cmd_unlock();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "minimal init: unlock failed: %s", esp_err_to_name(err));
        return err;
    }
    err = ssd1363_display_off();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "minimal init: display_off failed: %s", esp_err_to_name(err));
        return err;
    }
#endif

    /* Set a default full-frame address window so subsequent writes cover the panel. */
    err = ssd1363_set_addr_window(0, DISPLAY_WIDTH - 1, 0, DISPLAY_HEIGHT - 1);
    if (err != ESP_OK) {
        return err;
    }

    /* Finally, turn the display ON. */
    err = ssd1363_display_on();
    if (err != ESP_OK) {
        return err;
    }

#if SSD1363_BOOT_TEST_PATTERN
    err = ssd1363_boot_test_pattern();
    if (err != ESP_OK) {
        return err;
    }
#endif

    /* Init bytes were ACKed on the bus, but the SSD1363 command path is
     * write-only here: visual correctness (offsets, remap, grayscale) is
     * UNVERIFIED-ON-HARDWARE. "init OK" means "panel present and accepted
     * the sequence", NOT "image is correct". Use the bring-up checklist. */
    ESP_LOGI(TAG, "SSD1363 init sequence accepted (addr=0x%02X, col_offset=%u) "
                  "- visual params UNVERIFIED, see bring-up checklist",
             DISPLAY_I2C_ADDR, (unsigned)ssd1363_get_col_offset_units());
    return ESP_OK;
}

/* =======================================================================
 * SSD1363 HARDWARE BRING-UP CHECKLIST  (UNVERIFIED-ON-HARDWARE driver)
 * -----------------------------------------------------------------------
 * Do these in order the first time real hardware is attached. All knobs
 * live in src/user_config.h (uncomment) or PlatformIO -D build_flags.
 *
 * 1. WIRING / BUS
 *    - Set DISPLAY_I2C_SDA_GPIO / DISPLAY_I2C_SCL_GPIO to real pins.
 *    - Confirm panel I2C address (0x3C or 0x3D) -> DISPLAY_I2C_ADDR.
 *    - Build with -DSSD1363_I2C_SCAN_ON_BOOT=1 and check the log: every
 *      device on the bus is listed; DISPLAY_I2C_ADDR must appear. If the
 *      panel does not ACK, ssd1363_init_panel() now returns
 *      ESP_ERR_NOT_FOUND instead of a false ESP_OK (fixed root cause).
 *
 * 2. RAW PANEL LIFE
 *    - Build with -DSSD1363_BOOT_TEST_PATTERN=1. Expect a grayscale ramp
 *      with alternating-row inversion across the full 256x128 area.
 *    - All blank  -> check contrast (SSD1363_INIT_CONTRAST), VCOMH
 *      (SSD1363_INIT_VCOMH), IREF (SSD1363_INIT_IREF), panel Vcc.
 *    - All on / noise -> remap/dual-COM (SSD1363_INIT_REMAP_A/B) or
 *      mux ratio (SSD1363_INIT_MUX_RATIO) wrong (U8g2 #2298/#2608).
 *
 * 3. HORIZONTAL OFFSET / WRAP  (most common SSD1363 symptom)
 *    - Image shifted left/right or wrapping: tune SSD1363_COL_OFFSET
 *      (units of 4 px; GDDRAM is 320 wide vs 256 visible, default 8).
 *    - Also try SSD1363_INIT_DISPLAY_OFFSET (0xA2) for a COM/row shift.
 *
 * 4. MIRROR / UPSIDE-DOWN
 *    - Flip via SSD1363_INIT_REMAP_A bits (A[1] column re-map, A[4] COM
 *      scan dir) — see the 0xA0 comment in ssd1363_init_panel().
 *
 * 5. GRAYSCALE / CONTRAST POLARITY
 *    - Inverted shades: toggle store display_invert (0xA6/0xA7).
 *    - Banding: SSD1363_INIT_PHASE_LENGTH (0xB1) /
 *      SSD1363_INIT_PRECHARGE_VOLTAGE (0xBB) /
 *      SSD1363_INIT_SECOND_PRECHARGE (0xB6).
 *
 * 6. DATA NOT APPEARING THOUGH PANEL ALIVE
 *    - Confirm 0x5C "write RAM" precedes every data block: callers must
 *      use ssd1363_begin_frame() (which does set-window then 0x5C), or
 *      call ssd1363_write_ram_start() after any bare ssd1363_set_addr_window().
 *      (U8g2 #2298: missing 0x5C => data silently dropped.)
 *
 * Reference: olikraus/u8g2 csrc/u8x8_d_ssd1363.c (BSD-2-Clause) and
 * issues #2298 / #2490 / #2608. No Solomon Systech SSD1363 datasheet PDF
 * was publicly retrievable; bitfield-level claims remain UNVERIFIED.
 * ======================================================================= */

esp_err_t ssd1363_display_on(void)
{
    return ssd1363_write_cmd(0xAF); /* Display ON */
}

esp_err_t ssd1363_display_off(void)
{
    return ssd1363_write_cmd(0xAE); /* Display OFF */
}

uint8_t ssd1363_get_col_offset_units(void)
{
    return s_col_offset_units;
}

esp_err_t ssd1363_set_col_offset_units(uint8_t offset_units)
{
#if DISPLAY_COLOR_BITS == 4
    uint16_t cols = (uint16_t)((DISPLAY_WIDTH - 1) >> 2);
    if (cols > SSD1363_MAX_COL_ADDR) {
        return ESP_ERR_INVALID_STATE;
    }
    uint16_t max_off = (uint16_t)(SSD1363_MAX_COL_ADDR - cols);
    if ((uint16_t)offset_units > max_off) {
        offset_units = (uint8_t)max_off;
    }
#else
    (void)offset_units;
    offset_units = 0;
#endif
    s_col_offset_units = offset_units;
    return ESP_OK;
}

esp_err_t ssd1363_set_addr_window(uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1)
{
    /* SSD1363 4bpp addressing. Cross-checked against U8g2
     * u8x8_d_ssd1363.c U8X8_MSG_DISPLAY_DRAW_TILE: U8g2 computes
     * col = tile_x*2 + x_offset(8) per 8-px tile; per pixel that is
     * (pixel_x>>2) + 8, which is exactly the formula below. The column
     * unit = 4 px (2 bytes); the +offset centres the 256-px panel in the
     * 320-wide GDDRAM. This arithmetic is VERIFIED against the reference;
     * only the absolute offset value (SSD1363_COL_OFFSET) is panel-tunable.
     *
     * IMPORTANT: callers that invoke this directly (not via
     * ssd1363_begin_frame) MUST call ssd1363_write_ram_start() (0x5C)
     * before the pixel data, or the controller drops the data
     * (U8g2 issue #2298). UNVERIFIED-ON-HARDWARE for absolute placement.
     */
#if DISPLAY_COLOR_BITS == 4
    uint16_t col0 = (uint16_t)(ssd1363_get_col_offset_units() + (x0 >> 2));
    uint16_t col1 = (uint16_t)(ssd1363_get_col_offset_units() + (x1 >> 2));
    if (col0 > SSD1363_MAX_COL_ADDR || col1 > SSD1363_MAX_COL_ADDR) {
        return ESP_ERR_INVALID_ARG;
    }
    x0 = col0;
    x1 = col1;
#endif
    if (y0 > 255 || y1 > 255) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t cmds[6];
    cmds[0] = 0x15; /* Set Column Address */
    cmds[1] = (uint8_t)x0;
    cmds[2] = (uint8_t)x1;
    cmds[3] = 0x75; /* Set Row Address */
    cmds[4] = (uint8_t)y0;
    cmds[5] = (uint8_t)y1;
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_write_ram_start(void)
{
    return ssd1363_write_cmd(0x5C); /* Write RAM */
}

/* Optional configuration helpers (verify codes for SSD1363 specifically). */
esp_err_t ssd1363_set_contrast(uint8_t contrast)
{
    uint8_t cmds[2] = { 0xC1, contrast };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_multiplex_ratio(uint8_t ratio)
{
    uint8_t cmds[2] = { 0xCA, ratio };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_display_offset(uint8_t offset)
{
    uint8_t cmds[2] = { 0xA2, offset };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_start_line(uint8_t line)
{
    uint8_t cmds[2] = { 0xA1, line };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_remap(uint8_t config)
{
    /* SSD1363: "Set Re-map and Dual COM Line mode" (A0h) takes 2 bytes.
     * Keep legacy signature and send a zeroed second byte by default.
     */
    uint8_t cmds[3] = { 0xA0, config, 0x00 };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_display_clock(uint8_t divide, uint8_t freq)
{
    /* 0xB3: upper nibble freq, lower nibble divide */
    uint8_t val = (uint8_t)(((freq & 0x0F) << 4) | (divide & 0x0F));
    uint8_t cmds[2] = { 0xB3, val };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_precharge(uint8_t period)
{
    uint8_t cmds[2] = { 0xB1, period };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_set_vcomh(uint8_t level)
{
    uint8_t cmds[2] = { 0xBE, level };
    return ssd1363_write_cmd_list(cmds, sizeof(cmds));
}

esp_err_t ssd1363_entire_display_on(bool on)
{
    return ssd1363_write_cmd(on ? 0xA5 : 0xA4);
}

esp_err_t ssd1363_invert_display(bool invert)
{
    return ssd1363_write_cmd(invert ? 0xA7 : 0xA6);
}

esp_err_t ssd1363_begin_frame(uint16_t x0, uint16_t y0, uint16_t x1_incl, uint16_t y1_incl)
{
    if (x0 > x1_incl || y0 > y1_incl) {
        return ESP_ERR_INVALID_ARG;
    }
    /* Clip to panel bounds */
    if (x0 >= DISPLAY_WIDTH || y0 >= DISPLAY_HEIGHT) {
        return ESP_ERR_INVALID_ARG;
    }
    if (x1_incl >= DISPLAY_WIDTH)  x1_incl = (uint16_t)(DISPLAY_WIDTH - 1);
    if (y1_incl >= DISPLAY_HEIGHT) y1_incl = (uint16_t)(DISPLAY_HEIGHT - 1);

    esp_err_t err = ssd1363_set_addr_window(x0, x1_incl, y0, y1_incl);
    if (err != ESP_OK) return err;
    return ssd1363_write_ram_start();
}
