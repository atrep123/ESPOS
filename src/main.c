#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <inttypes.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "esp_spiffs.h"

#include "display/ssd1363.h"
#include "kernel/msgbus.h"
#include "kernel/timers.h"
#include "services/input/input.h"
#include "services/rpc/rpc.h"
#include "services/store/store.h"
#include "services/ui/ui.h"

static const char *TAG = "ESP32OS";

static void init_spiffs(void)
{
    ESP_LOGI(TAG, "Initializing SPIFFS");

    esp_vfs_spiffs_conf_t conf = {
        .base_path = "/spiffs",
        .partition_label = NULL,
        .max_files = 5,
        .format_if_mount_failed = true,
    };

    esp_err_t ret = esp_vfs_spiffs_register(&conf);

    if (ret != ESP_OK) {
        if (ret == ESP_FAIL) {
            ESP_LOGE(TAG, "Failed to mount or format filesystem");
        } else if (ret == ESP_ERR_NOT_FOUND) {
            ESP_LOGE(TAG, "Failed to find SPIFFS partition");
        } else {
            ESP_LOGE(TAG, "Failed to initialize SPIFFS (%s)", esp_err_to_name(ret));
        }
        return;
    }

    size_t total = 0;
    size_t used = 0;
    ret = esp_spiffs_info(NULL, &total, &used);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get SPIFFS partition information (%s)", esp_err_to_name(ret));
    } else {
        ESP_LOGI(TAG, "Partition size: total: %d, used: %d", total, used);
    }
}

static void test_spiffs(void)
{
    ESP_LOGI(TAG, "Opening file");
    FILE *f = fopen("/spiffs/hello.txt", "w");
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open file for writing");
        return;
    }
    fprintf(f, "Hello World from ESP32-S3!\n");
    fprintf(f, "This is a test file.\n");
    fclose(f);
    ESP_LOGI(TAG, "File written");

    ESP_LOGI(TAG, "Renaming file");
    if (rename("/spiffs/hello.txt", "/spiffs/test.txt") != 0) {
        ESP_LOGE(TAG, "Rename failed");
        return;
    }

    ESP_LOGI(TAG, "Reading file");
    f = fopen("/spiffs/test.txt", "r");
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open file for reading");
        return;
    }
    char line[64];
    while (fgets(line, sizeof(line), f) != NULL) {
        char *pos = strchr(line, '\n');
        if (pos) {
            *pos = '\0';
        }
        ESP_LOGI(TAG, "Read from file: '%s'", line);
    }
    fclose(f);

    struct stat st;
    if (stat("/spiffs/test.txt", &st) == 0) {
        ESP_LOGI(TAG, "File size: %ld bytes", st.st_size);
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32-S3 OS Started!");

    store_conf_t conf;
    esp_err_t err = store_init(&conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "store_init failed: %d", err);
    } else {
        ESP_LOGI(TAG, "Loaded config: schema=%" PRIu32 " bg_rgb=0x%08" PRIX32,
                 conf.schema, conf.bg_rgb);
    }

    init_spiffs();
    test_spiffs();

    /* Initialise I2C bus and send a minimal
     * placeholder init sequence to the SSD1363 panel.
     * Safe even if the display is not wired yet, but
     * will log an error if I2C pins are still -1.
     */
    (void)ssd1363_init_panel();

    bus_init();
    kernel_start_ticker();
    input_start();
    rpc_start();

    /* TODO: initialize your ST7789 panel here and pass handle instead of NULL. */
    esp_lcd_panel_handle_t panel = NULL;
    ui_start(panel);

    ESP_LOGI(TAG, "=== System Ready ===");

    while (1) {
        ESP_LOGI(TAG, "System running...");
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}
