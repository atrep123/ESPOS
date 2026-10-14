/* Deterministic cooperative Windows fibers, not a FreeRTOS timing emulator. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "scheduler.h"
typedef struct {
    unsigned char *data;
    size_t size, capacity, head, count;
} SimQueue;
typedef struct {
    void *fiber;
    TaskFunction_t fn;
    void *arg;
    SimQueue *waiting;
    int64_t deadline;
    int stopped;
} SimTask;
static SimTask tasks[3];
static int task_count, current = -1;
static void *controller;
static int64_t now_us;
static unsigned steps;
static int gpio_levels[64];
static SimQueue *owned_queues[3];
static unsigned queue_count;
static void fail(const char *why) { fprintf(stderr, "sim scheduler: %s\n", why); exit(4); }
int64_t esp_timer_get_time(void) { return now_us; }
void esp_timer_set_mock_time(int64_t us) { now_us = us; }
static void yield(void) { SwitchToFiber(controller); }
static VOID WINAPI task_entry(void *arg)
{
    SimTask *task = arg;
    task->fn(task->arg);
    task->stopped = 1;
    yield();
    fail("stopped task resumed");
}
void sim_scheduler_init(void)
{
    controller = ConvertThreadToFiber(NULL);
    if (!controller) fail("ConvertThreadToFiber failed");
}
BaseType_t xTaskCreatePinnedToCore(TaskFunction_t fn, const char *name, uint32_t stack,
    void *arg, int priority, TaskHandle_t *handle, int core)
{
    (void)name; (void)stack; (void)priority; (void)core;
    if (task_count == 3) return pdFAIL;
    SimTask *task = &tasks[task_count++];
    task->fn = fn; task->arg = arg;
    task->fiber = CreateFiber(1024 * 1024, task_entry, task);
    if (!task->fiber) fail("CreateFiber failed");
    *handle = task;
    return pdPASS;
}
void vTaskDelete(TaskHandle_t handle)
{
    SimTask *task = handle ? handle : &tasks[current];
    task->stopped = 1;
    if (current >= 0 && task == &tasks[current]) yield();
}
void vTaskDelay(TickType_t ticks)
{
    tasks[current].deadline = now_us + (int64_t)ticks * 1000;
    yield();
}
QueueHandle_t xQueueCreate(size_t depth, size_t size)
{
    SimQueue *q = calloc(1, sizeof(*q));
    if (!q) fail("queue allocation failed");
    q->data = calloc(depth, size); q->capacity = depth; q->size = size;
    if (!q->data) fail("queue storage allocation failed");
    if (queue_count == 3) fail("queue budget exceeded");
    owned_queues[queue_count++] = q;
    return q;
}
int xQueueSend(QueueHandle_t handle, const void *item, uint32_t timeout)
{
    (void)timeout;
    SimQueue *q = handle;
    if (q->count == q->capacity) return pdFALSE;
    memcpy(q->data + ((q->head + q->count) % q->capacity) * q->size, item, q->size);
    q->count++;
    /* Publication is a scheduling point so finite firmware queues drain. */
    if (current >= 0) yield();
    return pdTRUE;
}
int xQueueReceive(QueueHandle_t handle, void *out, uint32_t timeout)
{
    SimQueue *q = handle;
    if (!q->count && timeout) {
        tasks[current].waiting = q;
        tasks[current].deadline = timeout == portMAX_DELAY ? INT64_MAX : now_us + timeout * 1000LL;
        yield();
        tasks[current].waiting = NULL;
        tasks[current].deadline = 0;
    }
    if (!q->count) return pdFALSE;
    memcpy(out, q->data + q->head * q->size, q->size);
    q->head = (q->head + 1) % q->capacity; q->count--;
    return pdTRUE;
}
void vQueueDelete(QueueHandle_t handle)
{
    SimQueue *q = handle;
    /* Production bus_deinit visits the same subscribed queue per topic. */
    for (unsigned i = 0; i < queue_count; i++) {
        if (owned_queues[i] == q) {
            owned_queues[i] = NULL; free(q->data); free(q); return;
        }
    }
}
void sim_scheduler_drain(void)
{
    int progress;
    do {
        progress = 0;
        for (int i = 0; i < task_count; i++) {
            SimTask *task = &tasks[i];
            if (task->stopped) continue;
            if (task->deadline > now_us && (!task->waiting || !task->waiting->count)) continue;
            if (++steps > 100000) fail("100000 scheduling-step budget exceeded");
            current = i; SwitchToFiber(task->fiber); current = -1;
            progress = 1;
        }
    } while (progress);
}
void sim_scheduler_advance(unsigned ms) { now_us += ms * 1000LL; sim_scheduler_drain(); }
unsigned sim_scheduler_steps(void) { return steps; }
void sim_scheduler_destroy(void)
{
    for (int i = 0; i < task_count; i++) DeleteFiber(tasks[i].fiber);
    ConvertFiberToThread();
}
esp_err_t gpio_config(const gpio_config_t *cfg) { return cfg ? ESP_OK : ESP_ERR_INVALID_ARG; }
int gpio_get_level(gpio_num_t pin) { return GPIO_IS_VALID_GPIO(pin) ? gpio_levels[pin] : 0; }
esp_err_t gpio_set_level(gpio_num_t pin, int value)
{
    if (!GPIO_IS_VALID_GPIO(pin)) return ESP_ERR_INVALID_ARG;
    gpio_levels[pin] = value != 0; return ESP_OK;
}
