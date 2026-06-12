#include "gui_prop_tx.h"

#include <cmath>
#include <cstdio>
#include <cstring>

#include "ui_theme_dial_generated.h"   // theme colours: single source tools/m5_theme.json (gen: tools/gen_firmware_theme.py)

using MOONCAKE::USER_APP::PROP_TX::View_t;
using MOONCAKE::USER_APP::PROP_TX::VIEW_FIELD_HUE;
using MOONCAKE::USER_APP::PROP_TX::VIEW_FIELD_LED;
using MOONCAKE::USER_APP::PROP_TX::VIEW_FIELD_MODE;

namespace
{
    // Theme colours (P_GREEN/P_AMBER/P_RED, COL_WHITE, BG_BASE, RING_TRK, SOCKET,
    // TEXT_HI/TEXT_DIM, SEL_ACCENT, MODE_SETUP) come from ui_theme_dial_generated.h
    // (single source: tools/m5_theme.json "dial" section). Firmware-only colour stays:
    constexpr uint32_t COL_DARK = 0x0E1116;

    constexpr int CX = 120;
    constexpr int CY = 120;
    constexpr int RING_OUT = 116;
    constexpr int RING_IN = 110;
    constexpr int RING_CAP = 113;
    constexpr float TOP = 270.0f;
    constexpr float DEG = 3.14159265f / 180.0f;

    constexpr int ORB_CY = 120;
    constexpr int ORB_R = 43;
    constexpr int COMMAND_RING_R = 54;
    constexpr int COMMAND_RING_W = 10;
    constexpr int LED_R = 80;
    constexpr int LED_DOT_R = 10;
    constexpr float LED_ANGLES[4] = {126.0f, 102.0f, 78.0f, 54.0f};

    uint32_t mix(uint32_t a, uint32_t b, float t)
    {
        const int ar = (a >> 16) & 0xFF, ag = (a >> 8) & 0xFF, ab = a & 0xFF;
        const int br = (b >> 16) & 0xFF, bg = (b >> 8) & 0xFF, bb = b & 0xFF;
        const int r = ar + static_cast<int>((br - ar) * t);
        const int g = ag + static_cast<int>((bg - ag) * t);
        const int bl = ab + static_cast<int>((bb - ab) * t);
        return (static_cast<uint32_t>(r) << 16) | (static_cast<uint32_t>(g) << 8) | static_cast<uint32_t>(bl);
    }

    void drawCenteredText(LGFX_Sprite* canvas, const char* text, int x, int centerY)
    {
        if (canvas == nullptr || text == nullptr)
        {
            return;
        }
        canvas->drawCenterString(text, x, centerY - canvas->fontHeight() / 2);
    }

    void drawTopCenterText(LGFX_Sprite* canvas, const char* text, int x, int yTop)
    {
        if (canvas == nullptr || text == nullptr)
        {
            return;
        }
        canvas->drawCenterString(text, x, yTop);
    }

    void drawTrackedTopCenterText(LGFX_Sprite* canvas, const char* text, int x, int yTop, float tracking)
    {
        if (canvas == nullptr || text == nullptr)
        {
            return;
        }

        const size_t n = strlen(text);
        if (n == 0)
        {
            return;
        }

        float width = 0.0f;
        char glyph[2] = {0, 0};
        for (size_t i = 0; i < n; ++i)
        {
            glyph[0] = text[i];
            width += canvas->textWidth(glyph);
            if (i + 1 < n)
            {
                width += tracking;
            }
        }

        float cursor = static_cast<float>(x) - width / 2.0f;
        for (size_t i = 0; i < n; ++i)
        {
            glyph[0] = text[i];
            canvas->drawString(glyph, static_cast<int>(cursor), yTop);
            cursor += canvas->textWidth(glyph) + tracking;
        }
    }

    bool is_editing(const View_t& view, char key)
    {
        const char* lbl = view.field_label == nullptr ? "" : view.field_label;
        if (key == 'a')
        {
            return lbl[0] == 'a';
        }
        if (key == 'L')
        {
            return view.field == VIEW_FIELD_LED;
        }
        if (key == 'H')
        {
            return view.field == VIEW_FIELD_HUE;
        }
        if (key == 'M')
        {
            return view.field == VIEW_FIELD_MODE;
        }
        return false;
    }

    bool is_command_mode(const View_t& view)
    {
        return view.command_mode || view.awaiting_ack || view.armed || is_editing(view, 'a');
    }

    bool is_ack_status(const View_t& view)
    {
        const char* s = view.status == nullptr ? "" : view.status;
        return strncmp(s, "ACK ", 4) == 0 || strcmp(s, "POTVRZENO") == 0;
    }

    bool is_no_ack_status(const View_t& view)
    {
        const char* s = view.status == nullptr ? "" : view.status;
        return strcmp(s, "NO ACK") == 0 || strcmp(s, "no ack") == 0 ||
               strcmp(s, "timeout") == 0 || strcmp(s, "ZAMITNUTO") == 0 ||
               strcmp(s, "BLOKOVANO") == 0;
    }

    bool is_locked_fire_choice(const View_t& view)
    {
        const char* s = view.status == nullptr ? "" : view.status;
        const char* label = view.action_label == nullptr ? "" : view.action_label;
        return !view.armed && !view.awaiting_ack && strcmp(s, "ready") == 0 &&
               strcmp(label, "ODPAL") == 0;
    }

    bool is_preview_choice(const View_t& view)
    {
        const char* label = view.action_label == nullptr ? "" : view.action_label;
        return !view.armed && !view.awaiting_ack && strcmp(label, "PREVIEW") == 0 &&
               is_command_mode(view);
    }

    uint32_t state_color(const View_t& view)
    {
        const char* s = view.status == nullptr ? "" : view.status;
        // Fault states must NOT read as green/OK. Catch the explicit error statuses the app
        // sets (ENCODE/PAL ENC FAIL, BAD ACK, RX IGNORED, FIRE KEY MISSING, nvs/uart err,
        // ERR ...) so the ring shows danger instead of a misleading "ready" colour.
        if (view.armed || strncmp(s, "ERR ", 4) == 0 ||
            strstr(s, "FAIL") != nullptr || strstr(s, "err") != nullptr ||
            strstr(s, "MISSING") != nullptr || strcmp(s, "BAD ACK") == 0 ||
            strcmp(s, "RX IGNORED") == 0 || strcmp(s, "ZAMITNUTO") == 0 ||
            strcmp(s, "BLOKOVANO") == 0 || strcmp(s, "FF BUSY") == 0 ||
            strcmp(s, "FF DUTY") == 0)
        {
            return P_RED;
        }
        if (is_locked_fire_choice(view))
        {
            return P_AMBER;
        }
        if (view.awaiting_ack || strncmp(s, "sent ", 5) == 0 ||
            strcmp(s, "ODESILAM") == 0 || strcmp(s, "ODESLANO") == 0 ||
            is_no_ack_status(view))
        {
            return P_AMBER;
        }
        return P_GREEN;
    }

    uint32_t led_rgb(const View_t& view, int i)
    {
        if (i < 0 || i >= static_cast<int>(view.colors.size()))
        {
            i = 0;
        }
        return (static_cast<uint32_t>(view.colors[i][0]) << 16) |
               (static_cast<uint32_t>(view.colors[i][1]) << 8) |
               view.colors[i][2];
    }

    // B4b: palette dots are arranged on the lower ring arc. With 4 slots this matches
    // the original LED_ANGLES {126,102,78,54} (a 72deg span, 24deg apart). For more
    // slots the span widens (capped at 144deg) so up to 8 dots fit without overlap;
    // a single slot sits dead-centre at the bottom (90deg).
    float led_angle(int i, int count)
    {
        if (count <= 1)
        {
            return 90.0f;
        }
        float span = (count - 1) * 24.0f;
        if (span > 144.0f)
        {
            span = 144.0f;
        }
        const float spacing = span / (count - 1);
        return 90.0f + span / 2.0f - static_cast<float>(i) * spacing;
    }

    uint32_t on_color(uint32_t col)
    {
        const int r = (col >> 16) & 0xFF, g = (col >> 8) & 0xFF, b = col & 0xFF;
        const float lum = 0.299f * r + 0.587f * g + 0.114f * b;
        return lum > 150.0f ? COL_DARK : COL_WHITE;
    }

    void fit_text_size(LGFX_Sprite* canvas, const char* text, float start_size, float min_size, int max_width)
    {
        float size = start_size;
        while (size > min_size)
        {
            canvas->setTextSize(size);
            if (canvas->textWidth(text) <= max_width)
            {
                return;
            }
            size -= 0.06f;
        }
        canvas->setTextSize(min_size);
    }

    void ring_band(LGFX_Sprite* canvas, int cx, int cy, int r_out, int r_in, float a0, float a1, uint32_t color)
    {
        canvas->fillArc(cx, cy, r_out, r_in, a0, a1, color);
    }

    void thick_line(LGFX_Sprite* canvas, float x0, float y0, float x1, float y1, float w, uint32_t color)
    {
        const float dx = x1 - x0;
        const float dy = y1 - y0;
        const float len = sqrtf(dx * dx + dy * dy);
        if (len < 0.001f)
        {
            return;
        }
        const float ox = -dy / len * (w / 2.0f);
        const float oy = dx / len * (w / 2.0f);
        canvas->fillTriangle(
            static_cast<int>(x0 + ox), static_cast<int>(y0 + oy),
            static_cast<int>(x0 - ox), static_cast<int>(y0 - oy),
            static_cast<int>(x1 + ox), static_cast<int>(y1 + oy), color);
        canvas->fillTriangle(
            static_cast<int>(x1 + ox), static_cast<int>(y1 + oy),
            static_cast<int>(x1 - ox), static_cast<int>(y1 - oy),
            static_cast<int>(x0 - ox), static_cast<int>(y0 - oy), color);
        canvas->fillSmoothCircle(static_cast<int>(x0), static_cast<int>(y0), static_cast<int>(w / 2.0f + 0.5f), color);
        canvas->fillSmoothCircle(static_cast<int>(x1), static_cast<int>(y1), static_cast<int>(w / 2.0f + 0.5f), color);
    }

    void draw_setup_grid(LGFX_Sprite* canvas, uint32_t color)
    {
        for (int x = 24; x < 240; x += 24)
        {
            canvas->drawLine(x, 14, x, 226, color);
        }
        for (int y = 24; y < 240; y += 24)
        {
            canvas->drawLine(14, y, 226, y, color);
        }
    }

    void draw_orb(LGFX_Sprite* canvas, int cx, int cy, int r, uint32_t color, uint32_t accent, const char* label)
    {
        canvas->fillSmoothCircle(cx, cy, r + 10, mix(BG_BASE, color, 0.18f));
        canvas->fillSmoothCircle(cx, cy, r + 5, mix(BG_BASE, color, 0.34f));
        canvas->fillSmoothCircle(cx, cy, r, color);
        canvas->fillSmoothCircle(cx, cy, static_cast<int>(r * 0.62f), mix(color, COL_WHITE, 0.09f));
        canvas->fillSmoothCircle(cx, cy, static_cast<int>(r * 0.30f), mix(color, COL_WHITE, 0.16f));
        ring_band(canvas, cx, cy, r + 1, r - 1, 0, 360, mix(color, COL_WHITE, 0.22f));
        ring_band(canvas, cx, cy, r + 8, r + 5, 0, 360, accent);

        if (label == nullptr || label[0] == '\0')
        {
            return;
        }

        const size_t n = strlen(label);
        canvas->setFont(GUI_FONT_CN_BIG);
        const float start = n <= 1 ? 1.78f : (n <= 3 ? 1.46f : 1.16f);
        fit_text_size(canvas, label, start, 0.78f, static_cast<int>(r * 2 * 0.92f));
        canvas->setTextColor(on_color(color));
        drawCenteredText(canvas, label, cx, cy);
    }

    float command_label_size(const char* label)
    {
        const size_t n = label == nullptr ? 0 : strlen(label);
        return n <= 4 ? 1.16f : (n == 5 ? 1.00f : (n == 6 ? 0.86f : 0.76f));
    }

    void draw_segmented_target(LGFX_Sprite* canvas, int cx, int cy, int r, int width, uint32_t color)
    {
        const float starts[4] = {285.0f, 15.0f, 105.0f, 195.0f};
        for (float start : starts)
        {
            ring_band(canvas, cx, cy, r + width / 2, r - width / 2, start, start + 58.0f, color);
        }
    }

    void draw_x_glyph(LGFX_Sprite* canvas, int cx, int cy, uint32_t color)
    {
        thick_line(canvas, cx - 17, cy - 17, cx + 17, cy + 17, 8, color);
        thick_line(canvas, cx + 17, cy - 17, cx - 17, cy + 17, 8, color);
    }

    void draw_check_glyph(LGFX_Sprite* canvas, int cx, int cy, uint32_t color)
    {
        thick_line(canvas, cx - 22, cy + 2, cx - 7, cy + 17, 9, color);
        thick_line(canvas, cx - 7, cy + 17, cx + 26, cy - 18, 9, color);
        thick_line(canvas, cx - 22, cy + 2, cx - 7, cy + 17, 3, COL_WHITE);
        thick_line(canvas, cx - 7, cy + 17, cx + 26, cy - 18, 3, COL_WHITE);
    }

    void draw_chevron(LGFX_Sprite* canvas, int tip_x, int tip_y, int arm_dx, int half_h, uint32_t color)
    {
        thick_line(canvas, tip_x + arm_dx, tip_y - half_h, tip_x, tip_y, 5, color);
        thick_line(canvas, tip_x, tip_y, tip_x + arm_dx, tip_y + half_h, 5, color);
    }

    void draw_wait_sweep(LGFX_Sprite* canvas, int cx, int cy, uint32_t color)
    {
        ring_band(canvas, cx, cy, 38, 30, 0, 360, mix(BG_BASE, color, 0.35f));
        ring_band(canvas, cx, cy, 42, 30, 294, 36 + 360, color);
        canvas->fillSmoothCircle(cx, cy, 4, color);
    }

    void draw_command_token(LGFX_Sprite* canvas, int cx, int cy, uint32_t sc, const char* label, const char* variant)
    {
        draw_segmented_target(canvas, cx, cy, COMMAND_RING_R, COMMAND_RING_W, sc);

        if (strcmp(variant, "wait") == 0)
        {
            draw_wait_sweep(canvas, cx, cy, sc);
            return;
        }
        if (strcmp(variant, "ack") == 0)
        {
            draw_check_glyph(canvas, cx, cy, sc);
            return;
        }
        if (strcmp(variant, "no_ack") == 0)
        {
            draw_x_glyph(canvas, cx, cy, sc);
            canvas->fillRoundRect(cx - 70, cy + 18, 140, 40, 14, mix(P_AMBER, COL_WHITE, 0.10f));
            canvas->setFont(GUI_FONT_CN_BIG);
            canvas->setTextSize(1.08f);
            canvas->setTextColor(COL_DARK);
            drawTopCenterText(canvas, "NO ACK", cx, cy + 24);
            return;
        }
        if (strcmp(variant, "locked_fire") == 0)
        {
            canvas->setFont(GUI_FONT_CN_BIG);
            canvas->setTextSize(1.24f);
            canvas->setTextColor(TEXT_HI);
            drawTopCenterText(canvas, "LOCKED OUT", cx, cy - 36);
            canvas->fillRoundRect(cx - 82, cy + 20, 164, 26, 12, mix(P_AMBER, COL_WHITE, 0.10f));
            canvas->setTextSize(0.72f);
            canvas->setTextColor(COL_DARK);
            drawTopCenterText(canvas, "ARM FIRST", cx, cy + 20);
            return;
        }
        if (strcmp(variant, "preview") == 0)
        {
            canvas->setFont(GUI_FONT_CN_BIG);
            canvas->setTextSize(1.48f);
            canvas->setTextColor(TEXT_HI);
            drawTopCenterText(canvas, "NO FIRE", cx, cy - 38);
            canvas->fillRoundRect(cx - 78, cy + 18, 156, 30, 15, mix(MODE_SETUP, COL_WHITE, 0.16f));
            canvas->setTextSize(0.64f);
            canvas->setTextColor(COL_DARK);
            drawTopCenterText(canvas, "PREVIEW ONLY", cx, cy + 21);
            return;
        }

        canvas->setFont(GUI_FONT_CN_BIG);
        fit_text_size(canvas, label, command_label_size(label), 0.58f, COMMAND_RING_R * 2 - 28);
        canvas->setTextColor(TEXT_HI);
        drawCenteredText(canvas, label, cx, cy);
    }

    void draw_warning_glyph(LGFX_Sprite* canvas, int cx, int cy, int size, uint32_t color)
    {
        const float h = size * 1.72f;
        canvas->fillTriangle(cx, static_cast<int>(cy - h / 2.0f),
                             cx - size, static_cast<int>(cy + h / 2.0f),
                             cx + size, static_cast<int>(cy + h / 2.0f), color);
        canvas->setFont(GUI_FONT_CN_BIG);
        canvas->setTextSize(0.86f);
        canvas->setTextColor(P_RED);
        drawTopCenterText(canvas, "!", cx, static_cast<int>(cy - size * 0.74f));
    }

    void draw_armed_frame(LGFX_Sprite* canvas, const View_t& view)
    {
        canvas->fillScreen(P_RED);
        ring_band(canvas, CX, CY, 119, 111, 0, 360, COL_WHITE);
        ring_band(canvas, CX, CY, 109, 106, 0, 360, mix(P_RED, COL_WHITE, 0.42f));
        draw_warning_glyph(canvas, CX, 48, 14, COL_WHITE);

        canvas->setFont(GUI_FONT_CN_BIG);
        canvas->setTextSize(1.72f);
        canvas->setTextColor(COL_WHITE);
        drawTopCenterText(canvas, "ODPAL", CX, 84);

        canvas->setTextSize(0.96f);
        canvas->setTextColor(mix(P_RED, COL_WHITE, 0.92f));
        drawTrackedTopCenterText(canvas, "ARMED", CX, 142, 5.0f);

        // Count-driven colour chips (was hard-coded 4): the palette is 5 slots now, so the
        // armed overlay must show LED#5 too. Re-centre on CX so any count stays symmetric.
        const int chip_count = static_cast<int>(view.colors.size());
        const int chip_spacing = 16;
        const int chip_x0 = CX - ((chip_count - 1) * chip_spacing) / 2;
        for (int i = 0; i < chip_count; ++i)
        {
            const int chx = chip_x0 + i * chip_spacing;
            canvas->fillSmoothCircle(chx, 188, 7, mix(P_RED, COL_WHITE, 0.85f));
            canvas->fillSmoothCircle(chx, 188, 5, led_rgb(view, i));
        }
    }

    void draw_leader(LGFX_Sprite* canvas, float angle_deg, uint32_t color)
    {
        const float a = angle_deg * DEG;
        const float px = cosf(a), py = sinf(a);
        const float qx = -py, qy = px;
        const float bx = CX + px * (LED_R - 12);
        const float by = CY + py * (LED_R - 12);
        const float ax = CX + px * (ORB_R + 9);
        const float ay = CY + py * (ORB_R + 9);

        canvas->fillTriangle(static_cast<int>(bx + qx * 7.5f), static_cast<int>(by + qy * 7.5f),
                             static_cast<int>(bx - qx * 7.5f), static_cast<int>(by - qy * 7.5f),
                             static_cast<int>(ax), static_cast<int>(ay), SOCKET);
        canvas->fillTriangle(static_cast<int>(bx + qx * 5.0f), static_cast<int>(by + qy * 5.0f),
                             static_cast<int>(bx - qx * 5.0f), static_cast<int>(by - qy * 5.0f),
                             static_cast<int>(ax), static_cast<int>(ay), color);
    }

    void draw_led_channel(LGFX_Sprite* canvas, const View_t& view, int i, int count,
                          bool selected, bool command)
    {
        const float ang = led_angle(i, count);
        const float a = ang * DEG;
        const int x = static_cast<int>(CX + LED_R * cosf(a));
        const int y = static_cast<int>(CY + LED_R * sinf(a));
        const uint32_t col = led_rgb(view, i);

        // Dense palettes (>5 slots) shrink the dots so they don't collide on the arc.
        const bool dense = count > 5;
        const int dot_r = dense ? 8 : LED_DOT_R;
        const int sock_r = dense ? 11 : 13;

        if (selected)
        {
            if (!command)
            {
                draw_leader(canvas, ang, col);
            }
            canvas->fillSmoothCircle(x, y, sock_r + 3, mix(BG_BASE, col, 0.30f));
            canvas->fillSmoothCircle(x, y, sock_r, SOCKET);
            canvas->fillSmoothCircle(x, y, dot_r, col);
            ring_band(canvas, x, y, sock_r + 2, sock_r, 0, 360, COL_WHITE);
            return;
        }

        canvas->fillSmoothCircle(x, y, sock_r, SOCKET);
        ring_band(canvas, x, y, sock_r, sock_r - 1, 0, 360, mix(BG_BASE, COL_WHITE, 0.12f));
        const uint32_t tint = command ? mix(col, BG_BASE, 0.30f) : mix(col, BG_BASE, 0.62f);
        canvas->fillSmoothCircle(x, y, dot_r, tint);
    }
}

void GUI_PropTx::init()
{
    View_t view;
    renderPage(view);
}

void GUI_PropTx::renderPage(const View_t& view)
{
    if (view.armed)
    {
        draw_armed_frame(_canvas, view);
        _canvas->setTextSize(1);
        _canvas->pushSprite(0, 0);
        return;
    }

    const uint32_t sc = state_color(view);
    const bool command = is_command_mode(view);
    const bool ack = is_ack_status(view);
    const bool no_ack = is_no_ack_status(view);
    const float bg_tint = ack ? 0.25f : (command ? 0.10f : 0.06f);
    const uint32_t bg_src = command ? sc : MODE_SETUP;
    const uint32_t bg = mix(BG_BASE, bg_src, bg_tint);

    _canvas->fillScreen(bg);

    if (!command)
    {
        draw_setup_grid(_canvas, mix(BG_BASE, MODE_SETUP, 0.26f));
    }

    ring_band(_canvas, CX, CY, RING_OUT, RING_IN, 0, 360, RING_TRK);
    int bp = 100;
    if (bp > 0)
    {
        float sweep = bp / 100.0f * 352.0f;
        if (sweep < 8.0f)
        {
            sweep = 8.0f;
        }
        const float a0 = TOP;
        const float a1 = a0 + sweep;
        ring_band(_canvas, CX, CY, RING_OUT, RING_IN, a0, a1, sc);
        _canvas->fillSmoothCircle(static_cast<int>(CX + RING_CAP * cosf(a0 * DEG)),
                                  static_cast<int>(CY + RING_CAP * sinf(a0 * DEG)), 3, sc);
        _canvas->fillSmoothCircle(static_cast<int>(CX + RING_CAP * cosf(a1 * DEG)),
                                  static_cast<int>(CY + RING_CAP * sinf(a1 * DEG)), 3, sc);
    }

    _canvas->setFont(GUI_FONT_CN_BIG);
    _canvas->setTextSize(0.58f);
    _canvas->setTextColor(command ? SEL_ACCENT : MODE_SETUP);
    drawTrackedTopCenterText(_canvas, command ? "PRIKAZ" : "NASTAVENI", CX, 36, 4.0f);

    if (command)
    {
        const char* label = view.action_label == nullptr ? "" : view.action_label;
        const char* variant = "normal";
        if (view.awaiting_ack)
        {
            variant = "wait";
        }
        else if (ack)
        {
            variant = "ack";
        }
        else if (no_ack)
        {
            variant = "no_ack";
        }
        else if (is_locked_fire_choice(view))
        {
            variant = "locked_fire";
        }
        else if (is_preview_choice(view))
        {
            variant = "preview";
        }
        draw_command_token(_canvas, CX, ORB_CY, sc, label, variant);

        if (!view.awaiting_ack && strcmp(variant, "locked_fire") != 0 && strcmp(variant, "preview") != 0)
        {
            const int chev = COMMAND_RING_R + 14;
            draw_chevron(_canvas, CX - chev, ORB_CY, 9, 9, sc);
            draw_chevron(_canvas, CX + chev, ORB_CY, -9, 9, sc);
        }
    }
    else
    {
        char oval[24] = {0};   // must fit view.field_value (MODE text), not just the LED number
        uint32_t orb_col = led_rgb(view, view.selected_led);
        if (is_editing(view, 'H'))
        {
            snprintf(oval, sizeof(oval), "%s", view.field_value);
        }
        else if (is_editing(view, 'M'))
        {
            snprintf(oval, sizeof(oval), "%s", view.field_value);
            orb_col = MODE_SETUP;
        }
        else
        {
            snprintf(oval, sizeof(oval), "%u", view.selected_led + 1);
        }
        draw_orb(_canvas, CX, ORB_CY, ORB_R, orb_col, MODE_SETUP, oval);
    }

    const int selected_led = static_cast<int>(view.selected_led);
    const int slot_count = static_cast<int>(view.colors.size());
    for (int i = 0; i < slot_count; ++i)
    {
        if (i != selected_led)
        {
            draw_led_channel(_canvas, view, i, slot_count, false, command);
        }
    }
    if (selected_led >= 0 && selected_led < slot_count)
    {
        draw_led_channel(_canvas, view, selected_led, slot_count, true, command);
    }

    _canvas->setTextSize(1);
    _canvas->pushSprite(0, 0);
}
