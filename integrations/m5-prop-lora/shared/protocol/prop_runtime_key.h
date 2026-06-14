#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace prop_runtime_key {

constexpr std::size_t MIN_KEY_LENGTH = 16;
constexpr std::size_t MAX_KEY_LENGTH = 64;
constexpr const char* NVS_NAMESPACE = "prop_key";
constexpr const char* NVS_KEY = "shared";

#ifndef PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY
#define PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY 0
#endif

inline bool allowDrySmokeRuntimeKey() {
#if PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY
    return true;
#else
    return false;
#endif
}

inline bool isKnownDrySmokeKey(const std::uint8_t* src, std::size_t len) {
    static constexpr std::uint8_t key[MIN_KEY_LENGTH] = {
        0x00, 0x11, 0x22, 0x33,
        0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb,
        0xcc, 0xdd, 0xee, 0xff,
    };
    if (src == nullptr || len != sizeof(key)) {
        return false;
    }
    for (std::size_t i = 0; i < sizeof(key); ++i) {
        if (src[i] != key[i]) {
            return false;
        }
    }
    return true;
}

inline void secureZero(std::uint8_t* data, std::size_t len) {
    if (data == nullptr) {
        return;
    }
    volatile std::uint8_t* p = data;
    while (len-- > 0) {
        *p++ = 0;
    }
}

template <std::size_t N>
inline void secureZero(std::array<std::uint8_t, N>& data) {
    secureZero(data.data(), data.size());
}

struct RuntimeKey {
    std::array<std::uint8_t, MAX_KEY_LENGTH> bytes = {};
    std::size_t length = 0;

    bool set(const std::uint8_t* src, std::size_t len) {
        clear();
        if (src == nullptr || len < MIN_KEY_LENGTH || len > bytes.size()) {
            return false;
        }
        if (isKnownDrySmokeKey(src, len) && !allowDrySmokeRuntimeKey()) {
            return false;
        }
        for (std::size_t i = 0; i < len; ++i) {
            bytes[i] = src[i];
        }
        length = len;
        return true;
    }

    void clear() {
        secureZero(bytes);
        length = 0;
    }

    bool loaded() const {
        return length >= MIN_KEY_LENGTH;
    }

    const std::uint8_t* data() const {
        return loaded() ? bytes.data() : nullptr;
    }

    std::size_t size() const {
        return loaded() ? length : 0;
    }
};

}  // namespace prop_runtime_key
