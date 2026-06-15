#pragma once

#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include <mbedtls/md.h>

namespace prop_protocol {

constexpr uint16_t PROP_FRAME_MAGIC = 0x504C;
constexpr uint8_t PROP_PROTOCOL_VERSION = 2;  // v2: 32-bit epoch (top 32 bits of nonce); forces coordinated flash, old v1 fleet fails safe (dropped) not silently
constexpr size_t MAX_PAYLOAD_LENGTH = 64;
constexpr size_t LED_PAYLOAD_LENGTH = 13;
constexpr size_t MAC_LENGTH = 12;
constexpr size_t HEADER_LENGTH = 20;
constexpr size_t MAX_FRAME_LENGTH = HEADER_LENGTH + MAX_PAYLOAD_LENGTH + MAC_LENGTH;

// Worst-case length of a host UART line carrying a max-size received frame, so BOTH firmwares
// (DinMeter din-rx, Dial dial-tx) can size their UART line buffers from one shared number
// instead of magic literals. The modem prints received frames as (see c6l-modem modem_core.h):
//     "RX " + "<rssi> <snr>" + " " + <hex>        (then a '\n' line terminator)
// Worst case = MAX_FRAME_LENGTH*2 hex chars + the modem "RX <rssi> <snr> " prefix + a NUL.
// Prefix budget (16): "RX " (3) + rssi (up to "-128.0" = 6) + " " (1) + snr ("-128.0" = 6) ...
// rounded up to 16 to leave headroom; +1 for the C-string NUL terminator. Expressed with '+'
// only (no '*') so the shared-constant parity test can evaluate it. DOCUMENTATION ONLY: this
// does NOT change the wire format -- frames on the air are still capped at MAX_FRAME_LENGTH.
constexpr size_t MODEM_RX_LINE_PREFIX_BUDGET = 16;  // "RX <rssi> <snr> " worst case, padded
constexpr size_t MAX_HOST_RX_LINE_LENGTH =
    MAX_FRAME_LENGTH + MAX_FRAME_LENGTH + MODEM_RX_LINE_PREFIX_BUDGET + 1;  // = 96*2 + 16 + 1 = 209

enum class FrameType : uint8_t {
    Ping = 1,
    Status = 2,
    Preview = 3,
    Fire = 4,
    Stop = 5,
    Ack = 6,
    Error = 7,
    PaletteSet = 8,
    Arm = 9,        // receiver-side ARM authority: Fire is rejected unless ARMED (Sprint A 0.1)
    LedColorSet = 10,  // bidirectional 4-LED colour sync (Dial<->DinMeter). Payload = LED_PAYLOAD
                       // (brightness + 4 RGB). NO version bump: modems forward by version byte not
                       // frame type, and an un-upgraded endpoint just ignores the unknown type.
    RemoteLed = 11,  // ON-only remote latch for LED#3 + LED#5. Payload = 2 bytes:
                     //   [0] = LED mask: bit0 (0x01)=LED#3, bit1 (0x02)=LED#5 (set bit = turn ON).
                     //   [1] = reserved (0).
                     // Colour comes from the already-synced palette slots, NOT this frame.
                     // OFF is never sent here: STOP is the master clear. ON-only is RX policy.
                     // No version bump: modems relay by version byte; an un-upgraded RX drops the type.
    PropAction = 12,  // DualKey broadcast prop action. Payload = 6 bytes:
                      //   [0] action id, [1] value, [2..5] event id (u32be).
                      // Used for idempotent BLUE_SET and duplicate-safe BARREL_EFFECT.
};

constexpr FrameType PREVIEW_FRAME_TYPE = FrameType::Preview;
constexpr FrameType FIRE_FRAME_TYPE = FrameType::Fire;

struct Frame {
    FrameType type = FrameType::Ping;
    uint8_t keyId = 1;
    uint8_t source = 0;
    uint8_t destination = 0;
    uint32_t sequence = 0;
    uint64_t nonce = 0;
    std::vector<uint8_t> payload;
};

struct ReplayWindow {
    uint8_t lastSource = 0;
    uint32_t lastSequence = 0;
    bool hasLast = false;

    const char* classify(uint8_t source, uint32_t sequence) {
        if (!hasLast || source != lastSource || sequence > lastSequence) {
            lastSource = source;
            lastSequence = sequence;
            hasLast = true;
            return "new";
        }
        if (sequence == lastSequence) {
            return "duplicate";
        }
        return "stale";
    }
};

inline bool isValidFrameType(uint8_t type) {
    switch (static_cast<FrameType>(type)) {
        case FrameType::Ping:
        case FrameType::Status:
        case FrameType::Preview:
        case FrameType::Fire:
        case FrameType::Stop:
        case FrameType::Ack:
        case FrameType::Error:
        case FrameType::PaletteSet:
        case FrameType::Arm:
        case FrameType::LedColorSet:
        case FrameType::RemoteLed:
        case FrameType::PropAction:
            return true;
        default:
            return false;
    }
}

inline void putU16(std::vector<uint8_t>& out, uint16_t value) {
    out.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
    out.push_back(static_cast<uint8_t>(value & 0xFF));
}

inline void putU32(std::vector<uint8_t>& out, uint32_t value) {
    out.push_back(static_cast<uint8_t>((value >> 24) & 0xFF));
    out.push_back(static_cast<uint8_t>((value >> 16) & 0xFF));
    out.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
    out.push_back(static_cast<uint8_t>(value & 0xFF));
}

inline void putU64(std::vector<uint8_t>& out, uint64_t value) {
    for (int shift = 56; shift >= 0; shift -= 8) {
        out.push_back(static_cast<uint8_t>((value >> shift) & 0xFF));
    }
}

inline uint16_t readU16(const uint8_t* data) {
    return static_cast<uint16_t>((data[0] << 8) | data[1]);
}

inline uint32_t readU32(const uint8_t* data) {
    return (static_cast<uint32_t>(data[0]) << 24) |
           (static_cast<uint32_t>(data[1]) << 16) |
           (static_cast<uint32_t>(data[2]) << 8) |
           static_cast<uint32_t>(data[3]);
}

inline uint64_t readU64(const uint8_t* data) {
    uint64_t value = 0;
    for (int i = 0; i < 8; ++i) {
        value = (value << 8) | data[i];
    }
    return value;
}

inline bool hmacSha256Truncated(const uint8_t* key, size_t keyLen,
                                const uint8_t* data, size_t dataLen,
                                uint8_t out[MAC_LENGTH]) {
    // HMAC-SHA256, truncated to keep LoRa airtime low.
    const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    if (info == nullptr) {
        return false;
    }
    uint8_t fullMac[32] = {0};
    int rc = mbedtls_md_hmac(info, key, keyLen, data, dataLen, fullMac);
    if (rc != 0) {
        return false;
    }
    std::memcpy(out, fullMac, MAC_LENGTH);
    return true;
}

inline bool constantTimeEqual(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t diff = 0;
    for (size_t i = 0; i < len; ++i) {
        diff |= a[i] ^ b[i];
    }
    return diff == 0;
}

inline bool encodeFrame(const Frame& frame, const uint8_t* key, size_t keyLen, std::vector<uint8_t>& out) {
    if (frame.payload.size() > MAX_PAYLOAD_LENGTH || key == nullptr || keyLen < 16) {
        return false;
    }

    out.clear();
    out.reserve(HEADER_LENGTH + frame.payload.size() + MAC_LENGTH);
    putU16(out, PROP_FRAME_MAGIC);
    out.push_back(PROP_PROTOCOL_VERSION);
    out.push_back(static_cast<uint8_t>(frame.type));
    out.push_back(frame.keyId);
    out.push_back(frame.source);
    out.push_back(frame.destination);
    putU32(out, frame.sequence);
    putU64(out, frame.nonce);
    out.push_back(static_cast<uint8_t>(frame.payload.size()));
    out.insert(out.end(), frame.payload.begin(), frame.payload.end());

    uint8_t mac[MAC_LENGTH] = {0};
    if (!hmacSha256Truncated(key, keyLen, out.data(), out.size(), mac)) {
        return false;
    }
    out.insert(out.end(), mac, mac + MAC_LENGTH);
    return true;
}

inline bool decodeFrame(const uint8_t* data, size_t len, const uint8_t* key, size_t keyLen, Frame& frame) {
    if (data == nullptr || len < HEADER_LENGTH + MAC_LENGTH || len > MAX_FRAME_LENGTH || key == nullptr || keyLen < 16) {
        return false;
    }
    if (readU16(data) != PROP_FRAME_MAGIC || data[2] != PROP_PROTOCOL_VERSION) {
        return false;
    }
    if (!isValidFrameType(data[3])) {
        return false;
    }
    uint8_t payloadLen = data[19];
    if (payloadLen > MAX_PAYLOAD_LENGTH || len != HEADER_LENGTH + payloadLen + MAC_LENGTH) {
        return false;
    }

    uint8_t expectedMac[MAC_LENGTH] = {0};
    if (!hmacSha256Truncated(key, keyLen, data, HEADER_LENGTH + payloadLen, expectedMac)) {
        return false;
    }
    if (!constantTimeEqual(expectedMac, data + HEADER_LENGTH + payloadLen, MAC_LENGTH)) {
        return false;
    }

    frame.type = static_cast<FrameType>(data[3]);
    frame.keyId = data[4];
    frame.source = data[5];
    frame.destination = data[6];
    frame.sequence = readU32(data + 7);
    frame.nonce = readU64(data + 11);
    frame.payload.assign(data + HEADER_LENGTH, data + HEADER_LENGTH + payloadLen);
    return true;
}

inline bool encodeLedPayload(uint8_t brightness, const std::array<std::array<uint8_t, 3>, 4>& colors,
                             std::vector<uint8_t>& out) {
    out.clear();
    out.reserve(LED_PAYLOAD_LENGTH);
    // Byte 0 is RESERVED: both endpoints currently ignore transported brightness.
    // DinMeter owns LED brightness locally; senders write a constant placeholder.
    out.push_back(brightness);
    for (const auto& color : colors) {
        out.push_back(color[0]);
        out.push_back(color[1]);
        out.push_back(color[2]);
    }
    return out.size() == LED_PAYLOAD_LENGTH;
}

// RemoteLed (FrameType 11): ON-only 2-byte LED bitmask. Byte 0 = mask (LED#3/LED#5 bits),
// byte 1 = reserved (0). Reserved bits are stripped on BOTH ends so a future sender that sets
// an undefined bit can never accidentally light an LED. Colour is sourced on-device from the
// already-synced palette slots, never from this frame. LED_PAYLOAD_LENGTH/encodeLedPayload are
// deliberately untouched: this is a separate, additive frame so Preview/Fire stay byte-identical.
constexpr size_t  REMOTE_LED_PAYLOAD_LENGTH = 2;
constexpr uint8_t REMOTE_LED_BIT_LED3 = 0x01;
constexpr uint8_t REMOTE_LED_BIT_LED5 = 0x02;

inline bool encodeRemoteLedPayload(uint8_t mask, std::vector<uint8_t>& out) {
    out.clear();
    out.push_back(mask & (REMOTE_LED_BIT_LED3 | REMOTE_LED_BIT_LED5));  // strip reserved bits
    out.push_back(0x00);                                               // reserved
    return out.size() == REMOTE_LED_PAYLOAD_LENGTH;
}

inline bool parseRemoteLedPayload(const std::vector<uint8_t>& in, uint8_t& mask) {
    if (in.size() != REMOTE_LED_PAYLOAD_LENGTH) return false;
    mask = in[0] & (REMOTE_LED_BIT_LED3 | REMOTE_LED_BIT_LED5);        // ignore reserved bits
    return true;
}

constexpr size_t PROP_ACTION_PAYLOAD_LENGTH = 6;
constexpr uint8_t PROP_ACTION_BLUE_SET = 1;
constexpr uint8_t PROP_ACTION_BARREL_EFFECT = 2;

struct PropActionPayload {
    uint8_t action = 0;
    uint8_t value = 0;
    uint32_t eventId = 0;
};

inline bool propActionValueValid(uint8_t action, uint8_t value) {
    switch (action) {
        case PROP_ACTION_BLUE_SET:
            return value <= 1;
        case PROP_ACTION_BARREL_EFFECT:
            return value == 0;
        default:
            return false;
    }
}

inline bool encodePropActionPayload(uint8_t action, uint8_t value, uint32_t eventId,
                                    std::vector<uint8_t>& out) {
    if (!propActionValueValid(action, value)) return false;
    out.clear();
    out.reserve(PROP_ACTION_PAYLOAD_LENGTH);
    out.push_back(action);
    out.push_back(value);
    putU32(out, eventId);
    return out.size() == PROP_ACTION_PAYLOAD_LENGTH;
}

inline bool parsePropActionPayload(const std::vector<uint8_t>& in, PropActionPayload& out) {
    if (in.size() != PROP_ACTION_PAYLOAD_LENGTH) return false;
    PropActionPayload parsed;
    parsed.action = in[0];
    parsed.value = in[1];
    parsed.eventId = readU32(in.data() + 2);
    if (!propActionValueValid(parsed.action, parsed.value)) return false;
    out = parsed;
    return true;
}

constexpr size_t MAX_PALETTE_COLORS = 8;
constexpr size_t PALETTE_HEADER_LENGTH = 3;

struct PalettePayload {
    uint8_t paletteRev = 0;
    bool fade = false;
    std::vector<std::array<uint8_t, 3>> colors;
};

inline bool encodePalettePayload(const PalettePayload& in, std::vector<uint8_t>& out) {
    if (in.colors.empty() || in.colors.size() > MAX_PALETTE_COLORS) {
        return false;
    }

    out.clear();
    out.reserve(PALETTE_HEADER_LENGTH + 3 * in.colors.size());
    out.push_back(in.paletteRev);
    out.push_back(static_cast<uint8_t>(in.fade ? 1 : 0));
    out.push_back(static_cast<uint8_t>(in.colors.size()));
    for (const auto& color : in.colors) {
        out.push_back(color[0]);
        out.push_back(color[1]);
        out.push_back(color[2]);
    }
    return out.size() == PALETTE_HEADER_LENGTH + 3 * in.colors.size();
}

inline bool parsePalettePayload(const std::vector<uint8_t>& payload, PalettePayload& out) {
    if (payload.size() < PALETTE_HEADER_LENGTH) {
        return false;
    }

    const uint8_t count = payload[2];
    if (count == 0 || count > MAX_PALETTE_COLORS) {
        return false;
    }
    if (payload.size() != PALETTE_HEADER_LENGTH + 3 * count) {
        return false;
    }

    PalettePayload parsed;
    parsed.paletteRev = payload[0];
    parsed.fade = (payload[1] & 0x01) != 0;
    parsed.colors.reserve(count);
    for (size_t i = 0; i < count; ++i) {
        const size_t offset = PALETTE_HEADER_LENGTH + 3 * i;
        parsed.colors.push_back({payload[offset], payload[offset + 1], payload[offset + 2]});
    }

    out = parsed;
    return true;
}

inline char nibbleToHex(uint8_t nibble) {
    return nibble < 10 ? static_cast<char>('0' + nibble) : static_cast<char>('A' + (nibble - 10));
}

inline std::string bytesToHex(const uint8_t* data, size_t len) {
    std::string out;
    out.reserve(len * 2);
    for (size_t i = 0; i < len; ++i) {
        out.push_back(nibbleToHex((data[i] >> 4) & 0x0F));
        out.push_back(nibbleToHex(data[i] & 0x0F));
    }
    return out;
}

inline int hexValue(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}

inline bool hexToBytes(const std::string& hex, std::vector<uint8_t>& out) {
    if ((hex.size() % 2) != 0) {
        return false;
    }
    out.clear();
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i < hex.size(); i += 2) {
        int hi = hexValue(hex[i]);
        int lo = hexValue(hex[i + 1]);
        if (hi < 0 || lo < 0) {
            return false;
        }
        out.push_back(static_cast<uint8_t>((hi << 4) | lo));
    }
    return true;
}

}  // namespace prop_protocol
