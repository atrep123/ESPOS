#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string>

#include "../terminal_config.h"
#include "../terminal_external_display.h"
#include "../terminal_grove_route.h"

#if defined(ARDUINO) && TERMINAL_EXTERNAL_OLED_ENABLED && TERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2
#include <M5UnitGLASS2.h>
#define TERMINAL_EXTERNAL_OLED_HAS_M5UNITGLASS2 1
#else
#define TERMINAL_EXTERNAL_OLED_HAS_M5UNITGLASS2 0
#endif

#if defined(ARDUINO) && TERMINAL_EXTERNAL_OLED_ENABLED && TERMINAL_EXTERNAL_OLED_DRIVER_SSD1309
#include <Wire.h>
#define TERMINAL_EXTERNAL_OLED_HAS_SSD1309 1
#else
#define TERMINAL_EXTERNAL_OLED_HAS_SSD1309 0
#endif

namespace terminal_external_oled {

class ExternalOledSink {
   public:
    virtual ~ExternalOledSink() = default;
    virtual bool begin() = 0;
    virtual bool draw(const terminal_external_display::DisplayRenderPlan& plan,
                      const terminal_external_display::DisplayFrame& frame) = 0;
};

class MissingExternalOledSink : public ExternalOledSink {
   public:
    bool begin() override {
        return false;
    }

    bool draw(const terminal_external_display::DisplayRenderPlan& plan,
              const terminal_external_display::DisplayFrame& frame) override {
        (void)plan;
        (void)frame;
        return false;
    }
};

#if TERMINAL_EXTERNAL_OLED_HAS_SSD1309
class Ssd1309ExternalOledSink : public ExternalOledSink {
   public:
    bool begin() override {
        if (!terminal_config::EXTERNAL_OLED_ENABLED) {
            return false;
        }
        if (!terminal_grove_route::selectExternalOledPahub()) {
            available_ = false;
            invalidatePageCache();
            return false;
        }
        available_ = initOledSsd1309() && clearOled();
        if (available_) {
            resetPageCacheToClearedDisplay();
        } else {
            invalidatePageCache();
        }
        return available_;
    }

    bool draw(const terminal_external_display::DisplayRenderPlan& plan,
              const terminal_external_display::DisplayFrame& frame) override {
        if (!available_) {
            return false;
        }
        if (!terminal_grove_route::selectExternalOledPahub()) {
            available_ = false;
            invalidatePageCache();
            return false;
        }
        const OledPages pages = renderFrameBuffer(plan, frame);
        for (std::uint8_t page = 0; page < SSD1309_PAGES; ++page) {
            if (pageCached_[page] && cachedPages_[page] == pages[page]) {
                continue;
            }
            if (!writeOledPageBuffer(page, pages[page])) {
                available_ = false;
                invalidatePageCache();
                return false;
            }
            cachedPages_[page] = pages[page];
            pageCached_[page] = true;
        }
        return true;
    }

   private:
    static constexpr std::uint8_t SSD1309_WIDTH = 128;
    static constexpr std::uint8_t SSD1309_PAGES = 8;
    static constexpr std::uint8_t SSD1309_PAGE_HEIGHT_PX = 8;
    static constexpr std::uint8_t I2C_CHUNK = 16;
    static constexpr std::uint8_t CONTROL_COMMAND = 0x00;
    static constexpr std::uint8_t CONTROL_DATA = 0x40;
    using OledPages = std::array<std::array<std::uint8_t, SSD1309_WIDTH>, SSD1309_PAGES>;

    TwoWire& bus() const {
        return terminal_config::EXTERNAL_OLED_I2C_PORT == 1 ? Wire1 : Wire;
    }

    bool writeI2cBytes(const std::uint8_t* data, std::size_t size) {
        TwoWire& targetBus = bus();
        targetBus.beginTransmission(static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_I2C_ADDRESS));
        targetBus.write(data, size);
        return targetBus.endTransmission() == 0;
    }

    bool sendOledCommands(const std::uint8_t* commands, std::size_t size) {
        std::uint8_t packet[I2C_CHUNK + 1] = {CONTROL_COMMAND};
        std::size_t offset = 0;
        while (offset < size) {
            const std::size_t chunk = size - offset > I2C_CHUNK ? I2C_CHUNK : size - offset;
            for (std::size_t i = 0; i < chunk; ++i) {
                packet[i + 1] = commands[offset + i];
            }
            if (!writeI2cBytes(packet, chunk + 1)) {
                return false;
            }
            offset += chunk;
        }
        return true;
    }

    bool sendOledData(const std::uint8_t* data, std::size_t size) {
        std::uint8_t packet[I2C_CHUNK + 1] = {CONTROL_DATA};
        std::size_t offset = 0;
        while (offset < size) {
            const std::size_t chunk = size - offset > I2C_CHUNK ? I2C_CHUNK : size - offset;
            for (std::size_t i = 0; i < chunk; ++i) {
                packet[i + 1] = data[offset + i];
            }
            if (!writeI2cBytes(packet, chunk + 1)) {
                return false;
            }
            offset += chunk;
        }
        return true;
    }

    bool initOledSsd1309() {
        const std::uint8_t init[] = {
            0xAE,
            0xD5, 0x80,
            0xA8, 0x3F,
            0xD3, 0x00,
            0x40,
            0x20, 0x00,
            0xA1,
            0xC8,
            0xDB, 0x10,
            0xA4,
            0x2E,
            0x8D, 0x14,
            0xDA, 0x12,
            0x81, 0xFF,
            0xD9, 0x11,
            0xA6,
            0xAF,
        };
        return sendOledCommands(init, sizeof(init));
    }

    bool writeOledPageBuffer(std::uint8_t page, const std::array<std::uint8_t, SSD1309_WIDTH>& pageBuffer) {
        const std::uint8_t setPage[] = {
            0x21,
            0x00,
            0x7F,
            0x22,
            page,
            page,
        };
        return sendOledCommands(setPage, sizeof(setPage)) &&
               sendOledData(pageBuffer.data(), pageBuffer.size());
    }

    bool clearOled() {
        const std::array<std::uint8_t, SSD1309_WIDTH> empty = {};
        for (std::uint8_t page = 0; page < SSD1309_PAGES; ++page) {
            if (!writeOledPageBuffer(page, empty)) {
                return false;
            }
        }
        return true;
    }

    void resetPageCacheToClearedDisplay() {
        for (auto& page : cachedPages_) {
            page.fill(0);
        }
        pageCached_.fill(true);
    }

    void invalidatePageCache() {
        pageCached_.fill(false);
    }

    static const std::array<std::uint8_t, 5>& glyphFor(char ch) {
        static const std::array<std::uint8_t, 5> space{0x00, 0x00, 0x00, 0x00, 0x00};
        static const std::array<std::uint8_t, 5> n0{0x3E, 0x51, 0x49, 0x45, 0x3E};
        static const std::array<std::uint8_t, 5> n1{0x00, 0x42, 0x7F, 0x40, 0x00};
        static const std::array<std::uint8_t, 5> n2{0x42, 0x61, 0x51, 0x49, 0x46};
        static const std::array<std::uint8_t, 5> n3{0x21, 0x41, 0x45, 0x4B, 0x31};
        static const std::array<std::uint8_t, 5> n4{0x18, 0x14, 0x12, 0x7F, 0x10};
        static const std::array<std::uint8_t, 5> n5{0x27, 0x45, 0x45, 0x45, 0x39};
        static const std::array<std::uint8_t, 5> n6{0x3C, 0x4A, 0x49, 0x49, 0x30};
        static const std::array<std::uint8_t, 5> n7{0x01, 0x71, 0x09, 0x05, 0x03};
        static const std::array<std::uint8_t, 5> n8{0x36, 0x49, 0x49, 0x49, 0x36};
        static const std::array<std::uint8_t, 5> n9{0x06, 0x49, 0x49, 0x29, 0x1E};
        static const std::array<std::uint8_t, 5> a{0x7E, 0x11, 0x11, 0x11, 0x7E};
        static const std::array<std::uint8_t, 5> b{0x7F, 0x49, 0x49, 0x49, 0x36};
        static const std::array<std::uint8_t, 5> c{0x3E, 0x41, 0x41, 0x41, 0x22};
        static const std::array<std::uint8_t, 5> d{0x7F, 0x41, 0x41, 0x22, 0x1C};
        static const std::array<std::uint8_t, 5> e{0x7F, 0x49, 0x49, 0x49, 0x41};
        static const std::array<std::uint8_t, 5> f{0x7F, 0x09, 0x09, 0x09, 0x01};
        static const std::array<std::uint8_t, 5> g{0x3E, 0x41, 0x49, 0x49, 0x7A};
        static const std::array<std::uint8_t, 5> h{0x7F, 0x08, 0x08, 0x08, 0x7F};
        static const std::array<std::uint8_t, 5> i{0x00, 0x41, 0x7F, 0x41, 0x00};
        static const std::array<std::uint8_t, 5> j{0x20, 0x40, 0x41, 0x3F, 0x01};
        static const std::array<std::uint8_t, 5> k{0x7F, 0x08, 0x14, 0x22, 0x41};
        static const std::array<std::uint8_t, 5> l{0x7F, 0x40, 0x40, 0x40, 0x40};
        static const std::array<std::uint8_t, 5> m{0x7F, 0x02, 0x0C, 0x02, 0x7F};
        static const std::array<std::uint8_t, 5> n{0x7F, 0x04, 0x08, 0x10, 0x7F};
        static const std::array<std::uint8_t, 5> o{0x3E, 0x41, 0x41, 0x41, 0x3E};
        static const std::array<std::uint8_t, 5> p{0x7F, 0x09, 0x09, 0x09, 0x06};
        static const std::array<std::uint8_t, 5> q{0x3E, 0x41, 0x51, 0x21, 0x5E};
        static const std::array<std::uint8_t, 5> r{0x7F, 0x09, 0x19, 0x29, 0x46};
        static const std::array<std::uint8_t, 5> s{0x46, 0x49, 0x49, 0x49, 0x31};
        static const std::array<std::uint8_t, 5> t{0x01, 0x01, 0x7F, 0x01, 0x01};
        static const std::array<std::uint8_t, 5> u{0x3F, 0x40, 0x40, 0x40, 0x3F};
        static const std::array<std::uint8_t, 5> v{0x1F, 0x20, 0x40, 0x20, 0x1F};
        static const std::array<std::uint8_t, 5> w{0x3F, 0x40, 0x38, 0x40, 0x3F};
        static const std::array<std::uint8_t, 5> x{0x63, 0x14, 0x08, 0x14, 0x63};
        static const std::array<std::uint8_t, 5> y{0x07, 0x08, 0x70, 0x08, 0x07};
        static const std::array<std::uint8_t, 5> z{0x61, 0x51, 0x49, 0x45, 0x43};
        static const std::array<std::uint8_t, 5> hash{0x14, 0x7F, 0x14, 0x7F, 0x14};
        static const std::array<std::uint8_t, 5> dash{0x08, 0x08, 0x08, 0x08, 0x08};
        static const std::array<std::uint8_t, 5> percent{0x63, 0x13, 0x08, 0x64, 0x63};
        switch (ch) {
            case '#': return hash;
            case '-': return dash;
            case '%': return percent;
            case '0': return n0;
            case '1': return n1;
            case '2': return n2;
            case '3': return n3;
            case '4': return n4;
            case '5': return n5;
            case '6': return n6;
            case '7': return n7;
            case '8': return n8;
            case '9': return n9;
            case 'A': return a;
            case 'B': return b;
            case 'C': return c;
            case 'D': return d;
            case 'E': return e;
            case 'F': return f;
            case 'G': return g;
            case 'H': return h;
            case 'I': return i;
            case 'J': return j;
            case 'K': return k;
            case 'L': return l;
            case 'M': return m;
            case 'N': return n;
            case 'O': return o;
            case 'P': return p;
            case 'Q': return q;
            case 'R': return r;
            case 'S': return s;
            case 'T': return t;
            case 'U': return u;
            case 'V': return v;
            case 'W': return w;
            case 'X': return x;
            case 'Y': return y;
            case 'Z': return z;
            default: return space;
        }
    }

    static void setPixel(OledPages& pages, std::uint8_t x, std::uint8_t y, bool on = true) {
        if (x >= SSD1309_WIDTH || y >= terminal_external_display::OLED_HEIGHT_PX) {
            return;
        }
        const std::uint8_t page = static_cast<std::uint8_t>(y / SSD1309_PAGE_HEIGHT_PX);
        const std::uint8_t bit = static_cast<std::uint8_t>(1U << (y % SSD1309_PAGE_HEIGHT_PX));
        if (on) {
            pages[page][x] = static_cast<std::uint8_t>(pages[page][x] | bit);
        } else {
            pages[page][x] = static_cast<std::uint8_t>(pages[page][x] & ~bit);
        }
    }

    static void fillRect(OledPages& pages,
                         const terminal_external_display::DisplayRect& rect,
                         bool on = true) {
        const std::uint16_t xEnd = static_cast<std::uint16_t>(rect.xPx) + rect.widthPx;
        const std::uint16_t yEnd = static_cast<std::uint16_t>(rect.yPx) + rect.heightPx;
        for (std::uint16_t y = rect.yPx; y < yEnd; ++y) {
            for (std::uint16_t x = rect.xPx; x < xEnd; ++x) {
                setPixel(pages, static_cast<std::uint8_t>(x), static_cast<std::uint8_t>(y), on);
            }
        }
    }

    static void drawRect(OledPages& pages,
                         const terminal_external_display::DisplayRect& rect,
                         bool on = true) {
        if (rect.widthPx == 0 || rect.heightPx == 0) {
            return;
        }
        const std::uint16_t x1 = rect.xPx;
        const std::uint16_t y1 = rect.yPx;
        const std::uint16_t x2 = static_cast<std::uint16_t>(rect.xPx + rect.widthPx - 1);
        const std::uint16_t y2 = static_cast<std::uint16_t>(rect.yPx + rect.heightPx - 1);
        for (std::uint16_t x = x1; x <= x2; ++x) {
            setPixel(pages, static_cast<std::uint8_t>(x), static_cast<std::uint8_t>(y1), on);
            setPixel(pages, static_cast<std::uint8_t>(x), static_cast<std::uint8_t>(y2), on);
        }
        for (std::uint16_t y = y1; y <= y2; ++y) {
            setPixel(pages, static_cast<std::uint8_t>(x1), static_cast<std::uint8_t>(y), on);
            setPixel(pages, static_cast<std::uint8_t>(x2), static_cast<std::uint8_t>(y), on);
        }
    }

    static void drawText(OledPages& pages,
                         std::uint8_t startColumn,
                         std::uint8_t startY,
                         const std::string& text,
                         std::size_t maxChars,
                         bool on = true) {
        std::uint16_t column = startColumn;
        const std::size_t limit = text.size() < maxChars ? text.size() : maxChars;
        for (std::size_t index = 0; index < limit && column < SSD1309_WIDTH; ++index) {
            const std::array<std::uint8_t, 5>& glyph = glyphFor(text[index]);
            for (std::uint8_t glyphColumn = 0;
                 glyphColumn < glyph.size() && column < SSD1309_WIDTH;
                 ++glyphColumn) {
                for (std::uint8_t bit = 0; bit < 7; ++bit) {
                    if ((glyph[glyphColumn] & (1U << bit)) != 0) {
                        setPixel(pages,
                                 static_cast<std::uint8_t>(column),
                                 static_cast<std::uint8_t>(startY + bit),
                                 on);
                    }
                }
                ++column;
            }
            if (column < SSD1309_WIDTH) {
                ++column;
            }
        }
    }

    static void drawLaneNumber(OledPages& pages,
                               const terminal_external_display::DisplayRowPlan& plan,
                               const terminal_external_display::DisplayRow& row) {
        char text[2] = {};
        std::snprintf(text, sizeof(text), "%u", static_cast<unsigned>(row.laneNumber));
        drawText(pages, plan.laneTextX, plan.laneTextY, std::string(text), 1);
    }

    static void drawBrightnessBar(OledPages& pages,
                                  const terminal_external_display::DisplayRect& rect,
                                  std::uint8_t percent,
                                  bool on) {
        drawRect(pages, rect);
        if (!on || percent == 0 || rect.widthPx <= 2 || rect.heightPx <= 2) {
            return;
        }
        const std::uint8_t innerWidth = static_cast<std::uint8_t>(rect.widthPx - 2);
        const std::uint8_t fillWidth =
            static_cast<std::uint8_t>((static_cast<unsigned>(innerWidth) * percent + 50U) / 100U);
        if (fillWidth == 0) {
            return;
        }
        fillRect(pages,
                 terminal_external_display::DisplayRect{
                     static_cast<std::uint8_t>(rect.xPx + 1),
                     static_cast<std::uint8_t>(rect.yPx + 1),
                     fillWidth,
                     static_cast<std::uint8_t>(rect.heightPx - 2)});
    }

    static void drawRow(OledPages& pages,
                        const terminal_external_display::DisplayRowPlan& plan,
                        const terminal_external_display::DisplayRow& row) {
        drawRect(pages, plan.laneBox);
        drawLaneNumber(pages, plan, row);
        drawText(pages,
                 plan.colorTextX,
                 plan.colorTextY,
                 row.colorName,
                 terminal_external_display::COLOR_TEXT_MAX_CHARS);
        drawText(pages,
                 plan.brightnessTextX,
                 plan.brightnessTextY,
                 row.brightnessLabel,
                 terminal_external_display::BRIGHTNESS_TEXT_MAX_CHARS);
        drawBrightnessBar(pages, plan.brightnessBarBox, row.brightnessPercent, row.on);
        if (row.effect) {
            fillRect(pages, plan.effectBox);
        }
        drawText(pages,
                 plan.effectTextX,
                 plan.effectTextY,
                 row.effectLabel,
                 terminal_external_display::EFFECT_TEXT_CHARS,
                 !row.effect);
    }

    static OledPages renderFrameBuffer(const terminal_external_display::DisplayRenderPlan& plan,
                                       const terminal_external_display::DisplayFrame& frame) {
        OledPages pages = {};
        drawRect(pages, plan.frameBox);
        for (std::size_t row = 0; row < plan.rows.size(); ++row) {
            drawRow(pages, plan.rows[row], frame.rows[row]);
        }
        return pages;
    }

    bool available_ = false;
    std::array<std::array<std::uint8_t, SSD1309_WIDTH>, SSD1309_PAGES> cachedPages_ = {};
    std::array<bool, SSD1309_PAGES> pageCached_ = {};
};
#else
class Ssd1309ExternalOledSink : public MissingExternalOledSink {};
#endif

#if TERMINAL_EXTERNAL_OLED_HAS_M5UNITGLASS2
class M5GfxExternalOledSink : public ExternalOledSink {
   public:
    M5GfxExternalOledSink()
        : display_(
              static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_SDA_PIN),
              static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_SCL_PIN),
              static_cast<std::uint32_t>(terminal_config::EXTERNAL_OLED_I2C_FREQ),
              static_cast<std::int8_t>(terminal_config::EXTERNAL_OLED_I2C_PORT),
              static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_I2C_ADDRESS)) {}

    bool begin() override {
        if (!terminal_config::EXTERNAL_OLED_ENABLED ||
            !terminal_grove_route::selectExternalOledPahub()) {
            return false;
        }
        available_ = display_.begin();
        if (available_) {
            display_.setTextSize(1);
            display_.setTextColor(TFT_WHITE, TFT_BLACK);
            display_.fillScreen(TFT_BLACK);
        }
        return available_;
    }

    bool draw(const terminal_external_display::DisplayRenderPlan& plan,
              const terminal_external_display::DisplayFrame& frame) override {
        if (!available_ || !terminal_grove_route::selectExternalOledPahub()) {
            return false;
        }
        display_.fillScreen(TFT_BLACK);
        display_.setTextSize(1);
        display_.setTextColor(TFT_WHITE, TFT_BLACK);
        display_.drawRect(plan.frameBox.xPx,
                          plan.frameBox.yPx,
                          plan.frameBox.widthPx,
                          plan.frameBox.heightPx,
                          TFT_WHITE);
        for (std::size_t row = 0; row < plan.rows.size(); ++row) {
            drawRow(plan.rows[row], frame.rows[row]);
        }
        return true;
    }

   private:
    void drawText(std::uint8_t x, std::uint8_t y, const std::string& text) {
        display_.setCursor(x, y);
        display_.print(text.c_str());
    }

    void drawBrightnessBar(const terminal_external_display::DisplayRect& rect,
                           std::uint8_t percent,
                           bool on) {
        display_.drawRect(rect.xPx, rect.yPx, rect.widthPx, rect.heightPx, TFT_WHITE);
        if (!on || percent == 0 || rect.widthPx <= 2 || rect.heightPx <= 2) {
            return;
        }
        const std::uint8_t innerWidth = static_cast<std::uint8_t>(rect.widthPx - 2);
        const std::uint8_t fillWidth =
            static_cast<std::uint8_t>((static_cast<unsigned>(innerWidth) * percent + 50U) / 100U);
        if (fillWidth == 0) {
            return;
        }
        display_.fillRect(static_cast<std::uint8_t>(rect.xPx + 1),
                          static_cast<std::uint8_t>(rect.yPx + 1),
                          fillWidth,
                          static_cast<std::uint8_t>(rect.heightPx - 2),
                          TFT_WHITE);
    }

    void drawRow(const terminal_external_display::DisplayRowPlan& plan,
                 const terminal_external_display::DisplayRow& row) {
        display_.drawRect(plan.laneBox.xPx,
                          plan.laneBox.yPx,
                          plan.laneBox.widthPx,
                          plan.laneBox.heightPx,
                          TFT_WHITE);
        char laneText[2] = {};
        std::snprintf(laneText, sizeof(laneText), "%u", static_cast<unsigned>(row.laneNumber));
        display_.setTextColor(TFT_WHITE, TFT_BLACK);
        drawText(plan.laneTextX, plan.laneTextY, laneText);
        drawText(plan.colorTextX, plan.colorTextY, row.colorName);
        drawText(plan.brightnessTextX, plan.brightnessTextY, row.brightnessLabel);
        drawBrightnessBar(plan.brightnessBarBox, row.brightnessPercent, row.on);
        if (row.effect) {
            display_.fillRect(plan.effectBox.xPx,
                              plan.effectBox.yPx,
                              plan.effectBox.widthPx,
                              plan.effectBox.heightPx,
                              TFT_WHITE);
            display_.setTextColor(TFT_BLACK, TFT_WHITE);
            drawText(plan.effectTextX, plan.effectTextY, row.effectLabel);
            display_.setTextColor(TFT_WHITE, TFT_BLACK);
        } else {
            display_.setTextColor(TFT_WHITE, TFT_BLACK);
            drawText(plan.effectTextX, plan.effectTextY, row.effectLabel);
        }
    }

    bool available_ = false;
    M5UnitGLASS2 display_;
};
#else
class M5GfxExternalOledSink : public MissingExternalOledSink {};
#endif

#if TERMINAL_EXTERNAL_OLED_HAS_SSD1309
using ConfiguredExternalOledSink = Ssd1309ExternalOledSink;
#elif TERMINAL_EXTERNAL_OLED_HAS_M5UNITGLASS2
using ConfiguredExternalOledSink = M5GfxExternalOledSink;
#else
using ConfiguredExternalOledSink = MissingExternalOledSink;
#endif

class ExternalOledDriver {
   public:
    ExternalOledDriver()
        : ExternalOledDriver(defaultSink()) {}

    explicit ExternalOledDriver(ExternalOledSink& sink)
        : sink_(sink) {}

    bool begin() {
        available_ = sink_.begin();
        return available_;
    }

    bool available() const {
        return available_;
    }

    bool draw(const terminal_external_display::DisplayFrame& frame) {
        if (!available_ && !begin()) {
            return false;
        }
        if (frame == lastFrame_) {
            return true;
        }
        if (!sink_.draw(terminal_external_display::renderPlan(), frame)) {
            available_ = false;
            return false;
        }
        lastFrame_ = frame;
        return true;
    }

    const terminal_external_display::DisplayFrame& lastFrame() const {
        return lastFrame_;
    }

   private:
    static MissingExternalOledSink& defaultSink() {
        static MissingExternalOledSink sink;
        return sink;
    }

    ExternalOledSink& sink_;
    bool available_ = false;
    terminal_external_display::DisplayFrame lastFrame_ = {};
};

class ConfiguredExternalOledDriver {
   public:
    ConfiguredExternalOledDriver()
        : driver_(sink_) {}

    bool begin() {
        return driver_.begin();
    }

    bool available() const {
        return driver_.available();
    }

    bool draw(const terminal_external_display::DisplayFrame& frame) {
        return driver_.draw(frame);
    }

    const terminal_external_display::DisplayFrame& lastFrame() const {
        return driver_.lastFrame();
    }

   private:
    ConfiguredExternalOledSink sink_;
    ExternalOledDriver driver_;
};

#undef TERMINAL_EXTERNAL_OLED_HAS_M5UNITGLASS2
#undef TERMINAL_EXTERNAL_OLED_HAS_SSD1309

}  // namespace terminal_external_oled
