#pragma once

/*
 * Minimal esp_timer stub for native/host builds.
 * Provides a controllable mock time for unit tests.
 */

#include <stdint.h>

static int64_t s_esp_timer_mock_us = 0;

static inline int64_t esp_timer_get_time(void)
{
    return s_esp_timer_mock_us;
}

static inline void esp_timer_set_mock_time(int64_t us)
{
    s_esp_timer_mock_us = us;
}
