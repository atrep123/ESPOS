#pragma once
#include <stdint.h>
int64_t esp_timer_get_time(void);
void esp_timer_set_mock_time(int64_t us);
