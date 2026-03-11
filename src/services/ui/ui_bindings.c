#include "ui_bindings.h"

#include <string.h>

#include "display/ssd1363.h"
#include "esp_log.h"
#include "services/store/store.h"

#ifndef ESPOS_NATIVE
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
static SemaphoreHandle_t s_mtx;
#define BIND_LOCK()   do { if (s_mtx) xSemaphoreTake(s_mtx, portMAX_DELAY); } while (0)
#define BIND_UNLOCK() do { if (s_mtx) xSemaphoreGive(s_mtx); } while (0)
#else
#define BIND_LOCK()   ((void)0)
#define BIND_UNLOCK() ((void)0)
#endif

static const char *TAG = "ui_bindings";

/* ---------------------------------------------------------------------------
 * Generic in-RAM binding store
 * ---------------------------------------------------------------------------
 * Fixed-size table.  Each slot holds a key, an int value, and a short string
 * value.  Slots are "active" while key[0] != '\0'.
 * Lookup is linear O(N) which is fine for < 128 keys at UI frame rate.
 * ------------------------------------------------------------------------ */

enum {
    BIND_KEY_LEN   = 24,
    BIND_STR_LEN   = 32,
    BIND_MAX_SLOTS = 96,
};

typedef struct {
    char key[BIND_KEY_LEN];
    int  ival;
    char sval[BIND_STR_LEN];
} bind_slot_t;

static bind_slot_t s_slots[BIND_MAX_SLOTS];

static bind_slot_t *slot_find(const char *key)
{
    for (int i = 0; i < BIND_MAX_SLOTS; ++i) {
        if (s_slots[i].key[0] != '\0' && strcmp(s_slots[i].key, key) == 0) {
            return &s_slots[i];
        }
    }
    return NULL;
}

static bind_slot_t *slot_alloc(const char *key)
{
    bind_slot_t *s = slot_find(key);
    if (s != NULL) {
        return s;
    }
    for (int i = 0; i < BIND_MAX_SLOTS; ++i) {
        if (s_slots[i].key[0] == '\0') {
            strncpy(s_slots[i].key, key, BIND_KEY_LEN - 1);
            s_slots[i].key[BIND_KEY_LEN - 1] = '\0';
            s_slots[i].ival = 0;
            s_slots[i].sval[0] = '\0';
            return &s_slots[i];
        }
    }
    ESP_LOGW(TAG, "binding store full (%d slots), key='%s'", BIND_MAX_SLOTS, key);
    return NULL;  /* store full */
}

void ui_bind_clear_all(void)
{
    BIND_LOCK();
    memset(s_slots, 0, sizeof(s_slots));
    BIND_UNLOCK();
}

void ui_bind_init(void)
{
#ifndef ESPOS_NATIVE
    if (s_mtx == NULL) {
        s_mtx = xSemaphoreCreateMutex();
        if (s_mtx == NULL) {
            ESP_LOGE(TAG, "mutex creation failed");
        }
    }
#endif
    ui_bind_clear_all();
}

/* ---------------------------------------------------------------------------
 * Integer bindings
 * Hardware-backed keys (contrast, col_offset) read/write NVS + peripherals.
 * Everything else falls through to the generic store.
 * ------------------------------------------------------------------------ */

bool ui_bind_get_int(const char *key, int *out)
{
    if (out == NULL) {
        return false;
    }
    *out = 0;
    if (key == NULL || *key == '\0') {
        return false;
    }

    /* Hardware-backed display keys */
    if (strcmp(key, "contrast") == 0 || strcmp(key, "col_offset") == 0) {
        store_conf_t conf;
        if (store_get_conf(&conf) != ESP_OK) {
            return false;
        }
        if (strcmp(key, "contrast") == 0) {
            *out = (int)conf.display_contrast;
        } else {
            *out = (int)conf.display_col_offset;
        }
        return true;
    }

    /* Generic store */
    BIND_LOCK();
    bind_slot_t *s = slot_find(key);
    if (s != NULL) {
        *out = s->ival;
        BIND_UNLOCK();
        return true;
    }
    BIND_UNLOCK();
    return false;
}

esp_err_t ui_bind_set_int(const char *key, int v)
{
    if (key == NULL || *key == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    /* Hardware-backed display keys (mutex-guarded to serialize I2C + NVS) */
    if (strcmp(key, "contrast") == 0) {
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        BIND_LOCK();
        esp_err_t err = ssd1363_set_contrast((uint8_t)v);
        if (err == ESP_OK) {
            err = store_set_display_contrast((uint8_t)v);
        }
        BIND_UNLOCK();
        return err;
    }
    if (strcmp(key, "col_offset") == 0) {
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        BIND_LOCK();
        esp_err_t cerr = ssd1363_set_col_offset_units((uint8_t)v);
        if (cerr != ESP_OK) {
            ESP_LOGW(TAG, "ssd1363_set_col_offset_units failed: %s", esp_err_to_name(cerr));
        }
        uint8_t actual = ssd1363_get_col_offset_units();
        esp_err_t err = store_set_display_col_offset(actual);
        BIND_UNLOCK();
        return err;
    }

    /* Generic store */
    BIND_LOCK();
    bind_slot_t *s = slot_alloc(key);
    if (s == NULL) {
        BIND_UNLOCK();
        return ESP_FAIL;
    }
    s->ival = v;
    BIND_UNLOCK();
    return ESP_OK;
}

/* ---------------------------------------------------------------------------
 * Boolean bindings (stored as int 0/1)
 * ------------------------------------------------------------------------ */

bool ui_bind_get_bool(const char *key, bool *out)
{
    if (out == NULL) {
        return false;
    }
    *out = false;
    if (key == NULL || *key == '\0') {
        return false;
    }

    /* Hardware-backed key */
    if (strcmp(key, "invert") == 0) {
        store_conf_t conf;
        if (store_get_conf(&conf) != ESP_OK) {
            return false;
        }
        *out = (conf.display_invert != 0);
        return true;
    }

    /* Generic store (int-based) */
    BIND_LOCK();
    bind_slot_t *s = slot_find(key);
    if (s != NULL) {
        *out = (s->ival != 0);
        BIND_UNLOCK();
        return true;
    }
    BIND_UNLOCK();
    return false;
}

esp_err_t ui_bind_set_bool(const char *key, bool v)
{
    if (key == NULL || *key == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    /* Hardware-backed key (mutex-guarded to serialize I2C + NVS) */
    if (strcmp(key, "invert") == 0) {
        BIND_LOCK();
        esp_err_t err = ssd1363_invert_display(v);
        if (err == ESP_OK) {
            err = store_set_display_invert(v);
        }
        BIND_UNLOCK();
        return err;
    }

    /* Generic store */
    BIND_LOCK();
    bind_slot_t *s = slot_alloc(key);
    if (s == NULL) {
        BIND_UNLOCK();
        return ESP_FAIL;
    }
    s->ival = v ? 1 : 0;
    BIND_UNLOCK();
    return ESP_OK;
}

/* ---------------------------------------------------------------------------
 * String bindings (generic store only)
 * ------------------------------------------------------------------------ */

bool ui_bind_get_str(const char *key, char *out, size_t out_cap)
{
    if (out == NULL || out_cap == 0) {
        return false;
    }
    out[0] = '\0';
    if (key == NULL || *key == '\0') {
        return false;
    }

    BIND_LOCK();
    bind_slot_t *s = slot_find(key);
    if (s != NULL) {
        strncpy(out, s->sval, out_cap - 1);
        out[out_cap - 1] = '\0';
        BIND_UNLOCK();
        return true;
    }
    BIND_UNLOCK();
    return false;
}

esp_err_t ui_bind_set_str(const char *key, const char *value)
{
    if (key == NULL || *key == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    BIND_LOCK();
    bind_slot_t *s = slot_alloc(key);
    if (s == NULL) {
        BIND_UNLOCK();
        return ESP_FAIL;
    }
    if (value != NULL) {
        strncpy(s->sval, value, BIND_STR_LEN - 1);
        s->sval[BIND_STR_LEN - 1] = '\0';
    } else {
        s->sval[0] = '\0';
    }
    BIND_UNLOCK();
    return ESP_OK;
}

