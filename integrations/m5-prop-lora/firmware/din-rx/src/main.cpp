/**
 * @file main.cpp
 * @brief DinMeter prop receiver entry point.
 *
 * Boots straight into the LoRa prop receiver (prop_rx_run) instead of the M5
 * factory launcher menu / test screens -- the receiver must come up autonomously.
 * A short on-theme boot splash is shown first.
 */
#include "factory_test/factory_test.h"
#include "prop_rx.h"

static FactoryTest ft;

// On-theme boot splash: "PROP / LoRa RX" + the four channel colours (matches the
// Dial's instrument palette), shown briefly before the receiver UI takes over.
static void show_boot_logo(FactoryTest* test)
{
    auto* cv = test->_canvas;
    const int w = cv->width();
    const int h = cv->height();

    cv->fillScreen(cv->color888(0x12, 0x18, 0x20));

    cv->setFont(&fonts::efontCN_24);
    cv->setTextSize(2);
    cv->setTextColor(cv->color888(0xE7, 0xE9, 0xED));
    cv->drawCenterString("PROP", w / 2, h / 2 - 50);

    cv->setTextSize(1);
    cv->setTextColor(cv->color888(0x9F, 0xC2, 0xC8));
    cv->drawCenterString("LoRa  RX", w / 2, h / 2 + 10);

    const uint32_t cols[4] = {
        cv->color888(0xC8, 0x41, 0x3E), cv->color888(0x2E, 0x9E, 0x72),
        cv->color888(0x3E, 0x72, 0xC8), cv->color888(0xC8, 0x9A, 0x3E)};
    const int gap = 24;
    const int x0 = w / 2 - (gap * 3) / 2;
    const int dy = h - 18;
    for (int i = 0; i < 4; ++i)
    {
        cv->fillCircle(x0 + i * gap, dy, 5, cols[i]);
    }

    test->_canvas_update();
    // BOOT SPEEDUP: the splash was a blocking delay(1600) before the receiver UI took over.
    // Cut to a brief glance (250ms) -- the receiver's own status screen renders almost
    // immediately after, so total boot-to-live drops by ~1.35s with the logo still visible.
    delay(250);
}

void setup()
{
    ft.init();
    show_boot_logo(&ft);
}

void loop()
{
    // Stay in the receiver; if it ever exits, re-enter it (no factory menu).
    prop_rx_run(&ft);
}
