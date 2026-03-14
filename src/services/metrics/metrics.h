#pragma once

#include <stdint.h>
#include "esp_err.h"

/**
 * Process one 10ms tick. Increments *tick_count; when it reaches 100,
 * publishes TOP_METRICS_RET with current heap stats and resets counter.
 * Returns 1 when metrics were published, 0 otherwise.
 */
int metrics_process_tick(uint32_t *tick_count);

esp_err_t metrics_start(void);
void metrics_stop(void);

