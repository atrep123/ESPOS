#pragma once

#include <array>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

#include "terminal_color_definitions.h"

namespace terminal_setup_link {

constexpr std::size_t LANE_COUNT = 5;
constexpr const char* RESPONSE_OK = "SETUP_OK";
constexpr const char* RESPONSE_ERR = "SETUP_ERR";

struct Lane {
    std::uint16_t hue = 0;
    std::uint8_t brightness = 100;
    bool on = true;
    bool effect = false;
};

struct SetupCommand {
    std::uint32_t requestId = 0;
    std::array<Lane, LANE_COUNT> lanes = {};
};

enum class CommandKind {
    Empty,
    Setup,
    SimFire,
    Error,
};

enum class ParseError {
    None,
    Empty,
    UnknownCommand,
    BadLane,
    DuplicateLane,
    MissingLane,
    BadValue,
    ExtraToken,
};

struct ParseResult {
    CommandKind kind = CommandKind::Error;
    ParseError error = ParseError::UnknownCommand;
    SetupCommand setup = {};

    bool ok() const {
        return kind == CommandKind::Setup || kind == CommandKind::SimFire ||
               kind == CommandKind::Empty;
    }
};

inline void skipSpaces(const char*& p) {
    while (*p != '\0' && std::isspace(static_cast<unsigned char>(*p)) != 0) {
        ++p;
    }
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

inline bool parseUnsigned(const char*& p, unsigned& out) {
    if (std::isdigit(static_cast<unsigned char>(*p)) == 0) {
        return false;
    }
    unsigned value = 0;
    while (std::isdigit(static_cast<unsigned char>(*p)) != 0) {
        value = value * 10U + static_cast<unsigned>(*p - '0');
        if (value > 10000U) {
            return false;
        }
        ++p;
    }
    out = value;
    return true;
}

inline ParseResult error(ParseError code, std::uint32_t requestId = 0) {
    ParseResult result;
    result.kind = CommandKind::Error;
    result.error = code;
    result.setup.requestId = requestId;
    return result;
}

inline bool parseLaneToken(const char*& p, std::size_t& laneIndex, Lane& lane) {
    if (!consumeChar(p, 'L')) {
        return false;
    }

    unsigned laneNumber = 0;
    if (!parseUnsigned(p, laneNumber) || laneNumber < 1U || laneNumber > LANE_COUNT) {
        return false;
    }
    if (!consumeChar(p, ':')) {
        return false;
    }

    unsigned hue = 0;
    unsigned brightness = 0;
    unsigned on = 0;
    unsigned effect = 0;
    if (!parseUnsigned(p, hue) || !consumeChar(p, ',') ||
        !parseUnsigned(p, brightness) || !consumeChar(p, ',') ||
        !parseUnsigned(p, on) || !consumeChar(p, ',') ||
        !parseUnsigned(p, effect)) {
        return false;
    }
    if (hue > terminal_color_definitions::MAX_NAMED_COLOR_CODE ||
        brightness > 100U || on > 1U || effect > 1U) {
        return false;
    }

    laneIndex = laneNumber - 1U;
    lane.hue = static_cast<std::uint16_t>(hue);
    lane.brightness = static_cast<std::uint8_t>(brightness);
    lane.on = on != 0U;
    lane.effect = effect != 0U;
    return true;
}

inline ParseResult parseLine(const char* line) {
    const char* p = line == nullptr ? "" : line;
    skipSpaces(p);
    if (*p == '\0') {
        ParseResult result;
        result.kind = CommandKind::Empty;
        result.error = ParseError::Empty;
        return result;
    }

    if (consumeWord(p, "SIM_FIRE")) {
        ParseResult result;
        result.kind = CommandKind::SimFire;
        result.error = ParseError::None;
        skipSpaces(p);
        if (std::isdigit(static_cast<unsigned char>(*p)) != 0) {
            unsigned requestId = 0;
            if (!parseUnsigned(p, requestId) || requestId > 9999U) {
                return error(ParseError::BadValue);
            }
            result.setup.requestId = static_cast<std::uint32_t>(requestId);
            skipSpaces(p);
        }
        if (*p != '\0') {
            return error(ParseError::ExtraToken, result.setup.requestId);
        }
        return result;
    }

    if (!consumeWord(p, "SETUP")) {
        return error(ParseError::UnknownCommand);
    }

    ParseResult result;
    result.kind = CommandKind::Setup;
    result.error = ParseError::None;

    skipSpaces(p);
    if (std::isdigit(static_cast<unsigned char>(*p)) != 0) {
        unsigned requestId = 0;
        if (!parseUnsigned(p, requestId) || requestId > 9999U) {
            return error(ParseError::BadValue);
        }
        result.setup.requestId = static_cast<std::uint32_t>(requestId);
    }

    std::array<bool, LANE_COUNT> seen = {};
    std::size_t seenCount = 0;

    while (true) {
        skipSpaces(p);
        if (*p == '\0') {
            break;
        }

        std::size_t laneIndex = 0;
        Lane lane;
        if (!parseLaneToken(p, laneIndex, lane)) {
            return error(ParseError::BadValue, result.setup.requestId);
        }
        if (seen[laneIndex]) {
            return error(ParseError::DuplicateLane, result.setup.requestId);
        }
        seen[laneIndex] = true;
        ++seenCount;
        result.setup.lanes[laneIndex] = lane;
    }

    if (seenCount != LANE_COUNT) {
        return error(ParseError::MissingLane, result.setup.requestId);
    }
    return result;
}

inline std::string formatSetupLine(const SetupCommand& command, std::uint32_t requestId) {
    std::string out = "SETUP";
    if (requestId != 0U) {
        char request[16] = {};
        std::snprintf(request, sizeof(request), " %lu", static_cast<unsigned long>(requestId));
        out += request;
    }
    for (std::size_t i = 0; i < LANE_COUNT; ++i) {
        const Lane& item = command.lanes[i];
        char lane[64] = {};
        std::snprintf(
            lane,
            sizeof(lane),
            " L%u:%u,%u,%u,%u",
            static_cast<unsigned>(i + 1U),
            static_cast<unsigned>(item.hue),
            static_cast<unsigned>(item.brightness),
            item.on ? 1U : 0U,
            item.effect ? 1U : 0U);
        out += lane;
    }
    return out;
}

inline std::string formatSetupLine(const SetupCommand& command) {
    return formatSetupLine(command, command.requestId);
}

inline std::string formatSimFireLine(std::uint32_t requestId = 0) {
    if (requestId == 0U) {
        return "SIM_FIRE";
    }
    char out[24] = {};
    std::snprintf(out, sizeof(out), "SIM_FIRE %lu", static_cast<unsigned long>(requestId));
    return std::string(out);
}

inline std::string formatResponseLine(const char* response, std::uint32_t requestId) {
    if (requestId == 0U) {
        return std::string(response == nullptr ? "" : response);
    }
    char out[32] = {};
    std::snprintf(
        out,
        sizeof(out),
        "%s %lu",
        response == nullptr ? "" : response,
        static_cast<unsigned long>(requestId));
    return std::string(out);
}

inline std::string formatUnscopedResponseLine(const char* response) {
    return std::string(response == nullptr ? "" : response) + " 0";
}

}  // namespace terminal_setup_link
