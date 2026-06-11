// shared/protocol/prop_colors.h
#pragma once
#include <cstdint>
#include <cstddef>

namespace prop_colors {

struct ColorPreset {
    std::uint8_t r, g, b;
    const char*  name;
};

// SINGLE source of truth. Order is the encoder-cycle order on both devices.
static constexpr ColorPreset COLOR_PRESETS[] = {
    {255,   0,   0, "CERVENA"},
    {  0, 255,   0, "ZELENA"},
    {  0,   0, 255, "MODRA"},
    {255, 255, 255, "BILA"},
    {255, 150,   0, "ORANZOVA"},
    {  0, 255, 255, "AZUROVA"},
    {255,   0, 255, "FIALOVA"},
    {  0,   0,   0, "ZHASNUTO"},
};
static constexpr int NUM_COLOR_PRESETS =
    static_cast<int>(sizeof(COLOR_PRESETS) / sizeof(COLOR_PRESETS[0]));

// Neutral custom label shown when no exact preset matches.
static constexpr const char* CUSTOM_COLOR_NAME = "VLASTNI";

// THE unified label rule: exact RGB match -> preset name, else "VLASTNI".
// Never nearest-preset, never cursor-relative.
static inline const char* exactPresetName(std::uint8_t r, std::uint8_t g, std::uint8_t b) {
    for (int i = 0; i < NUM_COLOR_PRESETS; ++i) {
        if (COLOR_PRESETS[i].r == r &&
            COLOR_PRESETS[i].g == g &&
            COLOR_PRESETS[i].b == b) {
            return COLOR_PRESETS[i].name;
        }
    }
    return CUSTOM_COLOR_NAME;
}

// Nearest-preset index. KEEP ONLY as the encoder-cycle anchor; never for display text.
static inline int nearestPresetIndex(std::uint8_t r, std::uint8_t g, std::uint8_t b) {
    int best = 0;
    std::uint32_t bestD = 0xFFFFFFFFu;
    for (int i = 0; i < NUM_COLOR_PRESETS; ++i) {
        const int dr = static_cast<int>(r) - COLOR_PRESETS[i].r;
        const int dg = static_cast<int>(g) - COLOR_PRESETS[i].g;
        const int db = static_cast<int>(b) - COLOR_PRESETS[i].b;
        const std::uint32_t d =
            static_cast<std::uint32_t>(dr*dr + dg*dg + db*db);
        if (d < bestD) { bestD = d; best = i; }
    }
    return best;
}

} // namespace prop_colors
