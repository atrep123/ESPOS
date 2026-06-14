#pragma once

#include <array>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

namespace prop_xiao_link {

constexpr std::size_t MAX_LINE_LENGTH = 48;
constexpr std::uint8_t PROTOCOL_VERSION = 1;
constexpr std::uint8_t STATUS_LED_COUNT = 4;
constexpr std::uint8_t BARREL_WS2812_COUNT = 18;
constexpr std::uint8_t BUTTON_COUNT = 3;
constexpr std::uint8_t SWITCH_COUNT = 1;
constexpr std::uint16_t MAX_SEQUENCE = 9999;
constexpr std::uint16_t MAX_PHASE_MS = 5000;
constexpr std::uint8_t MAX_CURVE = 2;

struct Rgb {
    std::uint8_t r = 0;
    std::uint8_t g = 0;
    std::uint8_t b = 0;
};

struct Hello {
    std::uint8_t version = 0;
    std::uint8_t ws2812Count = 0;
    std::uint8_t ledCount = 0;
    std::uint8_t buttonCount = 0;
    std::uint8_t switchCount = 0;
};

struct InputEvent {
    std::uint8_t index = 0;
    bool active = false;
};

enum class BarrelMode {
    Off,
    Red,
    Fire,
};

struct BarrelCommand {
    BarrelMode mode = BarrelMode::Off;
    std::uint8_t intensity = 0;
    std::uint16_t rampMs = 0;
    std::uint16_t holdMs = 0;
    std::uint16_t fadeMs = 0;
    std::uint8_t curve = 0;
};

enum class CommandKind {
    Empty,
    Hello,
    Ping,
    Pong,
    Button,
    Switch,
    Stat4,
    Barrel,
    Error,
};

enum class ParseError {
    None,
    Empty,
    UnknownCommand,
    BadValue,
    ExtraToken,
};

struct ParseResult {
    CommandKind kind = CommandKind::Error;
    ParseError error = ParseError::UnknownCommand;
    Hello hello = {};
    std::uint16_t sequence = 0;
    InputEvent input = {};
    std::array<Rgb, STATUS_LED_COUNT> stat4 = {};
    BarrelCommand barrel = {};

    bool ok() const {
        return kind != CommandKind::Error;
    }
};

inline void skipSpaces(const char*& p) {
    while (*p != '\0' && std::isspace(static_cast<unsigned char>(*p)) != 0) {
        ++p;
    }
}

inline bool consumeSpaces(const char*& p) {
    bool consumed = false;
    while (*p != '\0' && std::isspace(static_cast<unsigned char>(*p)) != 0) {
        consumed = true;
        ++p;
    }
    return consumed;
}

inline bool consumeChar(const char*& p, char expected) {
    if (*p != expected) {
        return false;
    }
    ++p;
    return true;
}

inline bool consumeWord(const char*& p, const char* word) {
    const std::size_t len = std::strlen(word);
    if (std::strncmp(p, word, len) != 0) {
        return false;
    }
    p += len;
    return true;
}

inline bool atTokenBoundary(char c) {
    return c == '\0' || std::isspace(static_cast<unsigned char>(c)) != 0;
}

inline bool consumeToken(const char*& p, const char* word) {
    const std::size_t len = std::strlen(word);
    if (std::strncmp(p, word, len) != 0 || !atTokenBoundary(p[len])) {
        return false;
    }
    p += len;
    return true;
}

inline bool parseUnsigned(const char*& p, unsigned& out, unsigned maxValue) {
    if (std::isdigit(static_cast<unsigned char>(*p)) == 0) {
        return false;
    }
    unsigned value = 0;
    while (std::isdigit(static_cast<unsigned char>(*p)) != 0) {
        value = value * 10U + static_cast<unsigned>(*p - '0');
        if (value > maxValue) {
            return false;
        }
        ++p;
    }
    out = value;
    return true;
}

inline bool parseTaggedUnsigned(const char*& p, const char* tag, unsigned& out, unsigned maxValue) {
    return consumeWord(p, tag) && parseUnsigned(p, out, maxValue);
}

inline int hexNibble(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'A' && c <= 'F') {
        return 10 + (c - 'A');
    }
    return -1;
}

inline bool parseRgb(const char*& p, Rgb& color) {
    int n[6] = {};
    for (int i = 0; i < 6; ++i) {
        if (p[i] == '\0') {
            return false;
        }
        n[i] = hexNibble(p[i]);
        if (n[i] < 0) {
            return false;
        }
    }
    color.r = static_cast<std::uint8_t>((n[0] << 4) | n[1]);
    color.g = static_cast<std::uint8_t>((n[2] << 4) | n[3]);
    color.b = static_cast<std::uint8_t>((n[4] << 4) | n[5]);
    p += 6;
    return true;
}

inline ParseResult error(ParseError code) {
    ParseResult result;
    result.kind = CommandKind::Error;
    result.error = code;
    return result;
}

inline ParseResult empty() {
    ParseResult result;
    result.kind = CommandKind::Empty;
    result.error = ParseError::Empty;
    return result;
}

inline bool ensureEnd(const char* p) {
    skipSpaces(p);
    return *p == '\0';
}

inline ParseResult parseLine(const char* line) {
    const char* p = line == nullptr ? "" : line;
    if (std::strlen(p) >= MAX_LINE_LENGTH) {
        return error(ParseError::BadValue);
    }
    skipSpaces(p);
    if (*p == '\0') {
        return empty();
    }

    if (consumeToken(p, "HELLO")) {
        ParseResult result;
        result.kind = CommandKind::Hello;
        result.error = ParseError::None;
        unsigned version = 0;
        unsigned ws = 0;
        unsigned led = 0;
        unsigned btn = 0;
        unsigned sw = 0;
        if (!consumeSpaces(p) || !consumeToken(p, "XIAO_PROP_IO")) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p) || !parseUnsigned(p, version, PROTOCOL_VERSION)) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p) || !parseTaggedUnsigned(p, "WS:", ws, BARREL_WS2812_COUNT)) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p) || !parseTaggedUnsigned(p, "LED:", led, STATUS_LED_COUNT)) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p) || !parseTaggedUnsigned(p, "BTN:", btn, BUTTON_COUNT)) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p) || !parseTaggedUnsigned(p, "SW:", sw, SWITCH_COUNT)) {
            return error(ParseError::BadValue);
        }
        if (!ensureEnd(p) || version != PROTOCOL_VERSION || ws != BARREL_WS2812_COUNT ||
            led != STATUS_LED_COUNT || btn != BUTTON_COUNT || sw != SWITCH_COUNT) {
            return error(ParseError::BadValue);
        }
        result.hello.version = static_cast<std::uint8_t>(version);
        result.hello.ws2812Count = static_cast<std::uint8_t>(ws);
        result.hello.ledCount = static_cast<std::uint8_t>(led);
        result.hello.buttonCount = static_cast<std::uint8_t>(btn);
        result.hello.switchCount = static_cast<std::uint8_t>(sw);
        return result;
    }

    bool isPong = false;
    if (consumeToken(p, "PING") || (isPong = consumeToken(p, "PONG"))) {
        ParseResult result;
        result.kind = isPong ? CommandKind::Pong : CommandKind::Ping;
        result.error = ParseError::None;
        unsigned sequence = 0;
        if (!consumeSpaces(p) || !parseUnsigned(p, sequence, MAX_SEQUENCE)) {
            return error(ParseError::BadValue);
        }
        if (!ensureEnd(p)) {
            return error(ParseError::ExtraToken);
        }
        result.sequence = static_cast<std::uint16_t>(sequence);
        return result;
    }

    if (consumeToken(p, "BTN")) {
        ParseResult result;
        result.kind = CommandKind::Button;
        result.error = ParseError::None;
        unsigned index = 0;
        if (!consumeSpaces(p) || !parseUnsigned(p, index, BUTTON_COUNT) || index < 1U) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p)) {
            return error(ParseError::BadValue);
        }
        if (consumeToken(p, "DOWN")) {
            result.input.active = true;
        } else if (consumeToken(p, "UP")) {
            result.input.active = false;
        } else {
            return error(ParseError::BadValue);
        }
        if (!ensureEnd(p)) {
            return error(ParseError::ExtraToken);
        }
        result.input.index = static_cast<std::uint8_t>(index);
        return result;
    }

    if (consumeToken(p, "SW")) {
        ParseResult result;
        result.kind = CommandKind::Switch;
        result.error = ParseError::None;
        unsigned index = 0;
        if (!consumeSpaces(p) || !parseUnsigned(p, index, SWITCH_COUNT) || index < 1U) {
            return error(ParseError::BadValue);
        }
        if (!consumeSpaces(p)) {
            return error(ParseError::BadValue);
        }
        if (consumeToken(p, "ON")) {
            result.input.active = true;
        } else if (consumeToken(p, "OFF")) {
            result.input.active = false;
        } else {
            return error(ParseError::BadValue);
        }
        if (!ensureEnd(p)) {
            return error(ParseError::ExtraToken);
        }
        result.input.index = static_cast<std::uint8_t>(index);
        return result;
    }

    if (consumeToken(p, "STAT4")) {
        ParseResult result;
        result.kind = CommandKind::Stat4;
        result.error = ParseError::None;
        for (std::size_t i = 0; i < STATUS_LED_COUNT; ++i) {
            if (!consumeSpaces(p) || !parseRgb(p, result.stat4[i])) {
                return error(ParseError::BadValue);
            }
        }
        if (!ensureEnd(p)) {
            return error(ParseError::ExtraToken);
        }
        return result;
    }

    if (consumeToken(p, "BARREL")) {
        ParseResult result;
        result.kind = CommandKind::Barrel;
        result.error = ParseError::None;
        if (!consumeSpaces(p)) {
            return error(ParseError::BadValue);
        }
        if (consumeToken(p, "OFF")) {
            result.barrel.mode = BarrelMode::Off;
            if (!ensureEnd(p)) {
                return error(ParseError::ExtraToken);
            }
            return result;
        }
        if (consumeToken(p, "RED")) {
            unsigned intensity = 0;
            if (!consumeSpaces(p) || !parseUnsigned(p, intensity, 255)) {
                return error(ParseError::BadValue);
            }
            if (!ensureEnd(p)) {
                return error(ParseError::ExtraToken);
            }
            result.barrel.mode = BarrelMode::Red;
            result.barrel.intensity = static_cast<std::uint8_t>(intensity);
            return result;
        }
        if (consumeToken(p, "FIRE")) {
            unsigned ramp = 0;
            unsigned hold = 0;
            unsigned fade = 0;
            unsigned curve = 0;
            if (!consumeSpaces(p) || !parseUnsigned(p, ramp, MAX_PHASE_MS)) {
                return error(ParseError::BadValue);
            }
            if (!consumeSpaces(p) || !parseUnsigned(p, hold, MAX_PHASE_MS)) {
                return error(ParseError::BadValue);
            }
            if (!consumeSpaces(p) || !parseUnsigned(p, fade, MAX_PHASE_MS)) {
                return error(ParseError::BadValue);
            }
            if (!consumeSpaces(p) || !parseUnsigned(p, curve, MAX_CURVE)) {
                return error(ParseError::BadValue);
            }
            if (!ensureEnd(p)) {
                return error(ParseError::ExtraToken);
            }
            result.barrel.mode = BarrelMode::Fire;
            result.barrel.rampMs = static_cast<std::uint16_t>(ramp);
            result.barrel.holdMs = static_cast<std::uint16_t>(hold);
            result.barrel.fadeMs = static_cast<std::uint16_t>(fade);
            result.barrel.curve = static_cast<std::uint8_t>(curve);
            return result;
        }
        return error(ParseError::BadValue);
    }

    return error(ParseError::UnknownCommand);
}

inline std::string formatHelloLine() {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "HELLO XIAO_PROP_IO %u WS:%u LED:%u BTN:%u SW:%u",
                  PROTOCOL_VERSION, BARREL_WS2812_COUNT, STATUS_LED_COUNT, BUTTON_COUNT, SWITCH_COUNT);
    return std::string(buf);
}

inline std::string formatPingLine(std::uint16_t sequence) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "PING %u", static_cast<unsigned>(sequence));
    return std::string(buf);
}

inline std::string formatPongLine(std::uint16_t sequence) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "PONG %u", static_cast<unsigned>(sequence));
    return std::string(buf);
}

inline std::string formatButtonLine(std::uint8_t index, bool active) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "BTN %u %s", static_cast<unsigned>(index), active ? "DOWN" : "UP");
    return std::string(buf);
}

inline std::string formatSwitchLine(std::uint8_t index, bool active) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "SW %u %s", static_cast<unsigned>(index), active ? "ON" : "OFF");
    return std::string(buf);
}

inline std::string formatStat4Line(const std::array<Rgb, STATUS_LED_COUNT>& colors) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "STAT4 %02X%02X%02X %02X%02X%02X %02X%02X%02X %02X%02X%02X",
                  colors[0].r, colors[0].g, colors[0].b,
                  colors[1].r, colors[1].g, colors[1].b,
                  colors[2].r, colors[2].g, colors[2].b,
                  colors[3].r, colors[3].g, colors[3].b);
    return std::string(buf);
}

inline std::string formatBarrelOffLine() {
    return "BARREL OFF";
}

inline std::string formatBarrelRedLine(std::uint8_t intensity) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "BARREL RED %u", static_cast<unsigned>(intensity));
    return std::string(buf);
}

inline std::string formatBarrelFireLine(std::uint16_t rampMs, std::uint16_t holdMs,
                                        std::uint16_t fadeMs, std::uint8_t curve) {
    char buf[MAX_LINE_LENGTH] = {};
    std::snprintf(buf, sizeof(buf), "BARREL FIRE %u %u %u %u",
                  static_cast<unsigned>(rampMs), static_cast<unsigned>(holdMs),
                  static_cast<unsigned>(fadeMs), static_cast<unsigned>(curve));
    return std::string(buf);
}

}  // namespace prop_xiao_link
