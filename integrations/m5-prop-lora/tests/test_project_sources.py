from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectSourceTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = ROOT / relative_path
        if not path.exists():
            self.fail(f"{relative_path} does not exist")
        return path.read_text(encoding="utf-8")

    def module_text(self, *relative_paths: str) -> str:
        # Concatenate a firmware module's .cpp with its sibling config/theme
        # headers so a Marlin-style refactor (constants MOVED into a sibling
        # header) is still found wherever it now lives.
        return "\n".join(self.read(p) for p in relative_paths)

    def assert_text_contains_all(self, text: str, needles: list[str], label: str) -> None:
        for needle in needles:
            with self.subTest(source=label, needle=needle):
                self.assertIn(needle, text)

    def assert_text_not_contains_any(self, text: str, needles: list[str], label: str) -> None:
        for needle in needles:
            with self.subTest(source=label, needle=needle):
                self.assertNotIn(needle, text)

    def assert_contains_all(self, relative_path: str, needles: list[str]) -> None:
        text = self.read(relative_path)
        for needle in needles:
            with self.subTest(path=relative_path, needle=needle):
                self.assertIn(needle, text)

    def assert_not_contains_any(self, relative_path: str, needles: list[str]) -> None:
        text = self.read(relative_path)
        for needle in needles:
            with self.subTest(path=relative_path, needle=needle):
                self.assertNotIn(needle, text)

    def constant(self, text: str, name: str) -> int:
        match = re.search(rf"{name}\s*=\s*(\d+)", text)
        if match is None:
            self.fail(f"{name} constant not found")
        return int(match.group(1))

    def header_icon_values(self, relative_path: str, symbol: str) -> list[int]:
        text = self.read(relative_path)
        match = re.search(rf"{symbol}\[\d+\]\s*=\s*\{{(.*?)\}};", text, re.S)
        if match is None:
            self.fail(f"{symbol} array not found")
        return [int(value, 16) for value in re.findall(r"0x[0-9A-Fa-f]{4}", match.group(1))]

    def test_cpp_protocol_header_defines_wire_contract(self):
        self.assert_contains_all(
            "shared/protocol/prop_protocol.h",
            [
                "PROP_FRAME_MAGIC",
                "PROP_PROTOCOL_VERSION",
                "FrameType::Fire",
                "FrameType::Preview",
                "HMAC",
                "MAX_PAYLOAD_LENGTH = 64",
                "HEADER_LENGTH = 20",
                "LED_PAYLOAD_LENGTH = 13",
                "isValidFrameType",
                "payloadLen = data[19]",
            ],
        )

    def test_c6l_modem_project_uses_radio_uart_and_auth_protocol(self):
        # Marlin-style refactor: radio PHY/pins + host-UART baud moved into
        # modem_config.h, and the host line grammar (SEND/ACK/RX) into modem_core.h.
        # Read the whole modem module so the moved constants are found wherever they live.
        text = self.module_text(
            "firmware/c6l-modem/src/main.cpp",
            "firmware/c6l-modem/src/modem_config.h",
            "firmware/c6l-modem/src/modem_core.h",
        )
        self.assert_text_contains_all(
            text,
            [
                # named-pin Module ctor (pins now constexpr in modem_config.h)
                "SX1262 radio = new Module(RADIO_NSS_PIN, RADIO_DIO1_PIN, RADIOLIB_NC, RADIO_BUSY_PIN)",
                "Serial1.begin(modem_config::UART_BAUD,",
                "SEND ",
                "ACK ",
                "RX ",
                "868.1",
                "250.0",
                "0x34",
            ],
            "c6l-modem module (main.cpp + modem_config.h + modem_core.h)",
        )

    def test_dial_prop_tx_app_has_guarded_fire_and_persistence(self):
        # Marlin-style refactor: the UART port/pins moved into prop_tx_config.h as
        # PROP_UART_PORT_NUM=1 / PROP_UART_TX_GPIO=13 / PROP_UART_RX_GPIO=15 (the .cpp
        # casts them to uart_port_t/gpio_num_t). Read cpp + that config header so the
        # moved pin knobs are found. FIELD_BRIGHTNESS was removed (no brightness field
        # anymore: the edit fields are now FIELD_LED/FIELD_HUE/FIELD_MODE).
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "Prop TX",
                "ODPAL",
                "ARM",
                "PREVIEW",
                "FIRE",
                "prop_protocol.h",
                "SEND ",
                "FrameType::Fire",
                "encodeLedPayload",
                "nvs_open",
                # UART port/pins are now config-header constants cast to the IDF types
                "PROP_UART_PORT_NUM = 1",
                "PROP_UART_TX_GPIO  = 13",
                "PROP_UART_RX_GPIO  = 15",
                "static_cast<uart_port_t>(prop_tx_config::PROP_UART_PORT_NUM)",
                "static_cast<gpio_num_t>(prop_tx_config::PROP_UART_TX_GPIO)",
                "selected_field",
                "FIELD_LED",  # was FIELD_BRIGHTNESS (removed); FIELD_LED/HUE/MODE are the live edit fields
                "FIELD_HUE",
                "FrameType::Ack",
                "_poll_uart",
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )

    def test_dial_boots_straight_into_prop_tx(self):
        # The demo launcher was dropped (task #34): main boots directly into Prop TX.
        self.assert_contains_all(
            "firmware/dial-tx/main/main.cpp",
            [
                "apps/app_prop_tx/app_prop_tx.h",
                "PropTx prop_tx",
                "prop_tx.onCreate()",
                "prop_tx.onRunning()",
            ],
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/main.cpp",
            ["Launcher app_launcher", "app_launcher.onRunning()"],
        )

    def test_dial_launcher_opens_prop_tx_as_first_demo_bubble(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/launcher/launcher_render_callback.hpp",
            [
                '"PROP", "TX"',
                "ICON_NUM",
                "icon_color_list",
                "icon_pic_list",
                "image_data_icon_prop_tx",
            ],
        )
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/launcher/launcher_icons/launcher_icons.h",
            ['#include "icon_prop_tx.h"'],
        )
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/launcher/launcher.cpp",
            ["case 0:", "app_ptr = new MOONCAKE::USER_APP::PropTx"],
        )

    def test_dial_prop_tx_uses_recycled_demo_gui(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
            [
                "gui/gui_prop_tx.h",
                "GUI_PropTx _gui",
                "GUI_Base* getGui() override { return &_gui; }",
            ],
        )
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            ["_gui.renderPage", "_run_selected_action()", "onDestroy()"],
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            ["canvas->setCursor", "canvas->fillScreen(TFT_BLACK)"],
        )

    def test_dial_prop_tx_gui_is_dark_premium_two_mode_layout(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                "fillScreen(bg)",
                "mix(BG_BASE, bg_src, bg_tint)",
                "ring_band(",
                "draw_orb(",
                "draw_command_token(",
                "draw_segmented_target(",
                "draw_setup_grid(",
                "draw_armed_frame(",
                "drawTrackedTopCenterText",
                "is_command_mode(",
                "thick_line(",
                "drawCenteredText",
                "state_color(",
                # the selected led becomes the centrepiece, command mode shows the action
                "draw_leader(",
                "is_editing(view, 'H')",
            ],
        )

    def test_dial_prop_tx_dark_premium_palette_and_geometry_constants(self):
        # Theme colours moved to the generated header ui_theme_dial_generated.h
        # (single source tools/m5_theme.json); the geometry constants + the
        # firmware-only COL_DARK stay in gui_prop_tx.cpp. Read both.
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/gui/ui_theme_dial_generated.h",
        )
        self.assert_text_contains_all(
            text,
            [
                # theme colours (now in ui_theme_dial_generated.h)
                "BG_BASE = 0x14171D",
                "RING_TRK = 0x363D4A",
                "SOCKET = 0x0B0D11",
                "TEXT_HI = 0xE7E9ED",
                "P_GREEN = 0x3FB36B",
                "P_AMBER = 0xFF8C00",
                "P_RED = 0xCC0000",
                "SEL_ACCENT = 0xF5F7FA",
                "MODE_SETUP = 0x59C6DC",
                # firmware-only colour + geometry stay in the .cpp
                "COL_DARK = 0x0E1116",
                "ORB_R = 43",
                "COMMAND_RING_R = 54",
                "COMMAND_RING_W = 10",
                "LED_R = 80",
                "RING_OUT = 116",
                "LED_ANGLES[4] = {126.0f, 102.0f, 78.0f, 54.0f}",
                "setFont(GUI_FONT_CN_BIG)",
            ],
            "dial prop_tx gui (gui_prop_tx.cpp + ui_theme_dial_generated.h)",
        )

    LED_ARC_ANGLES = (126.0, 102.0, 78.0, 54.0)

    def led_dot_centres(self, gui_text):
        import math

        r = self.constant(gui_text, "LED_R")
        return [
            (120 + r * math.cos(math.radians(a)), 120 + r * math.sin(math.radians(a)))
            for a in self.LED_ARC_ANGLES
        ]

    def test_dial_prop_tx_round_layout_fits_inside_the_dial(self):
        import math

        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp")
        ring_out = self.constant(text, "RING_OUT")
        orb_cy = self.constant(text, "ORB_CY")
        orb_r = self.constant(text, "ORB_R")
        sel_r = 16  # led selection glow/ring outer radius (selected forward)

        # the brightness ring stays inside the 120px radius panel
        self.assertLessEqual(ring_out, 120)
        # the centrepiece orb (plus its selection ring) fits within the ring
        self.assertLessEqual(orb_r + 9, ring_out - 4)

        dots = self.led_dot_centres(text)
        # every channel dot (plus selection ring) stays inside the round panel
        for x, y in dots:
            self.assertLessEqual(math.hypot(x - 120, y - 120) + sel_r, ring_out - 2)
        # the dots really form a bottom arc: the outer pair sits higher than the inner pair
        self.assertLess(dots[0][1], dots[1][1])
        self.assertLess(dots[3][1], dots[2][1])
        # in the redesign the orb and the selected channel dot are linked by a leader
        # pointer whose base tucks under the dot and whose apex touches the orb rim.
        self.assertIn("LED_R - 12", text)
        self.assertIn("ORB_R + 9", text)
        self.assertLess(orb_cy + orb_r + sel_r, max(y for _, y in dots))

    def test_dial_prop_tx_uses_hue_instead_of_rgb_fields(self):
        # The hues backing array widened 4->8 slots (NVS-blob layout stability; only
        # the first 5 are edited/transmitted), so the Data_t declaration is now
        # std::array<uint16_t, 8> hues seeded from prop_tx_config::DEFAULT_HUES.
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
            [
                "FIELD_HUE",
                "std::array<uint16_t, 8> hues",
            ],
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
            ["FIELD_RED", "FIELD_GREEN", "FIELD_BLUE"],
        )
        # HUE_MAX moved into prop_tx_config.h ([7] colour-wheel range); the HUE edit
        # field is labelled BARVA (Czech "colour") now, so the label literals are
        # "BARVA" / "LED %u BARVA". Read cpp + config so HUE_MAX is found.
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "HUE_MAX = 360",
                "wrap_hue",
                "set_color_from_hue",
                "hue_from_rgb",
                "_sync_colors_from_hues",
                'nvs_get_blob(nvs, "hueDeg"',
                'nvs_set_blob(nvs, "hueDeg"',
                'nvs_get_blob(nvs, "hues"',
                "FIELD_HUE",
                '"BARVA"',
                '"LED %u BARVA"',
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                "FIELD_RED",
                "FIELD_GREEN",
                "FIELD_BLUE",
                '"LED %u RGB"',
                'return "R"',
                'return "G"',
                'return "B"',
                "hue_degrees_from_legacy_percent",
                "looks_like_legacy_percent",
                'nvs_set_blob(nvs, "hues"',
            ],
        )

    def test_dial_prop_tx_state_is_color_coded(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                "uint32_t state_color(const View_t& view)",
                # the armed/ERR danger branch now also folds in FAIL/MISSING/BAD ACK/etc,
                # so the condition continues on the same line with a trailing `||`.
                'if (view.armed || strncmp(s, "ERR ", 4) == 0 ||',
                "return P_RED;",
                "view.awaiting_ack",
                'strcmp(s, "ODESILAM") == 0',
                'strcmp(s, "ODESLANO") == 0',
                "is_no_ack_status(view)",
                "return P_AMBER;",
                'strcmp(s, "NO ACK") == 0',
                "return P_GREEN;",
                # the state colour drives the brightness ring and command target
                "ring_band(_canvas, CX, CY, RING_OUT, RING_IN, a0, a1, sc)",
                "draw_command_token(_canvas, CX, ORB_CY, sc",
            ],
        )

    def test_dial_prop_tx_status_token_is_compact(self):
        # The approved mockup removes the old status word/token. State is carried by
        # colour and by command-token variants (wait/check/X), while setup values
        # live inside the orb. The inline "%u\xC2\xB0"/"%u%%" orb formatting moved
        # upstream into the controller this session: the GUI now draws the already-
        # formatted view.field_value as "%s", so those numeric literals no longer
        # live in the GUI source -- the compact token is now field_value-in-orb +
        # the draw_command_token glyph variants.
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                'variant = "wait"',
                'variant = "ack"',
                'variant = "no_ack"',
                'variant = "preview"',
                'variant = "locked_fire"',
                "draw_wait_sweep(",
                "draw_check_glyph(",
                "draw_x_glyph(",
                '"NO FIRE"',
                '"PREVIEW ONLY"',
                '"LOCKED OUT"',
                '"ARM FIRST"',
                "is_editing(view, 'H')",
                # the edited value, compact, inside the orb (formatted upstream)
                'snprintf(oval, sizeof(oval), "%s", view.field_value)',
                "draw_command_token(",
            ],
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                "draw_status_token(",
                "STATUS_TOKEN_MS",
                "status_text",
                # the orb no longer prints a raw degree/percent number itself
                '"%u\\xC2\\xB0"',
                '"%u%%"',
            ],
        )

    def test_dial_prop_tx_hue_is_degrees_and_field_value_is_named_preset(self):
        # This session the editable BRIGHTNESS field was removed entirely (the edit
        # fields are now LED / HUE(=BARVA) / MODE). So the old "brightness shown as %%,
        # hue as deg" contract no longer applies. The surviving, current truth:
        #   * hue still lives as DEGREES (selected_hue_degrees, hue_from_rgb, wrap_hue
        #     mod HUE_MAX) -- never as a percent;
        #   * the orb's field value is the colour PRESET NAME (exactPresetName) for HUE,
        #     the LED number for LED, and FADE/STEP for MODE -- not a "%%"/"deg" number.
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                "hue_from_rgb",
                "wrap_hue",
                "view.selected_hue_degrees = _data.hues[_data.selected_led]",
                # the HUE field value is the named preset, not a numeric percent/degree
                'snprintf(buffer, buffer_size, "%s", prop_colors::exactPresetName(c[0], c[1], c[2]))',
                # MODE field value is FADE/STEP text
                '_data.palette_fade ? "FADE" : "STEP"',
            ],
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                # no brightness field / percent helpers survive
                "brightness_to_percent",
                "percent_to_channel",
                "view.brightness_percent",
                "_data.brightness",
                "hue_percent_from_rgb",
                "selected_hue_percent",
                # the orb no longer prints a "%%"/"deg" number for the edited value
                'snprintf(buffer, buffer_size, "%u%%"',
                'snprintf(buffer, buffer_size, "%udeg"',
                '"BARVA %"',
                '"HUE %"',
            ],
        )

    def test_dial_prop_tx_ui_removes_redundant_title_and_second_status(self):
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                '"PROP TX"',
                "TITLE_Y",
                "STATE_CHIP_X",
                "STATE_CHIP_WIDTH",
                'view.armed ? "ARMED" : "SAFE"',
            ],
        )
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                "draw_armed_frame(",
                '"ARMED"',
                '"ODPAL"',
                "draw_orb(",
            ],
        )

    def test_dial_prop_tx_launcher_icon_is_custom_pixel_asset(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/launcher/launcher_icons/icon_prop_tx.h",
            [
                "clean high-contrast Prop TX icon",
                "keeps TFT_BLACK only for transparent padding",
                "centered 28x28 symbol",
                "0xFFFF",
                "0xFD20",
                "image_data_icon_prop_tx[1764]",
            ],
        )
        self.assertTrue(
            (ROOT / "firmware/dial-tx/main/apps/launcher/launcher_icons/icon_prop_tx.png").exists(),
            "Prop TX launcher icon should keep a source PNG for regeneration",
        )

    def test_dial_prop_tx_launcher_icon_png_is_centered_and_padded(self):
        try:
            from PIL import Image
        except ImportError as exc:
            self.fail(f"Pillow is required for launcher icon geometry checks: {exc}")

        path = ROOT / "firmware/dial-tx/main/apps/launcher/launcher_icons/icon_prop_tx.png"
        img = Image.open(path).convert("RGBA")
        alpha = img.getchannel("A")
        bbox = alpha.getbbox()
        self.assertIsNotNone(bbox, "launcher icon should have visible pixels")
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        center_x = (left + right - 1) / 2
        center_y = (top + bottom - 1) / 2

        self.assertEqual(left, 7)
        self.assertEqual(top, 7)
        self.assertEqual(right, 35)
        self.assertEqual(bottom, 35)
        self.assertEqual(width, 28)
        self.assertEqual(height, 28)
        self.assertLessEqual(abs(center_x - 20.5), 1.0)
        self.assertLessEqual(abs(center_y - 20.5), 1.0)

    def test_dial_prop_tx_launcher_icon_header_matches_png_geometry(self):
        try:
            from PIL import Image
        except ImportError as exc:
            self.fail(f"Pillow is required for launcher icon header checks: {exc}")

        header_values = self.header_icon_values(
            "firmware/dial-tx/main/apps/launcher/launcher_icons/icon_prop_tx.h",
            "image_data_icon_prop_tx",
        )
        self.assertEqual(len(header_values), 42 * 42)

        img = Image.open(
            ROOT / "firmware/dial-tx/main/apps/launcher/launcher_icons/icon_prop_tx.png"
        ).convert("RGBA")

        def rgb565(pixel):
            red, green, blue, alpha = pixel
            if alpha == 0:
                return 0
            return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)

        png_values = [rgb565(img.getpixel((x, y))) for y in range(42) for x in range(42)]
        self.assertEqual(header_values, png_values)

        visible = [(idx % 42, idx // 42) for idx, value in enumerate(header_values) if value != 0]
        self.assertTrue(visible, "launcher icon header should have visible pixels")
        left = min(x for x, _ in visible)
        right = max(x for x, _ in visible) + 1
        top = min(y for _, y in visible)
        bottom = max(y for _, y in visible) + 1
        self.assertEqual(left, 7)
        self.assertEqual(top, 7)
        self.assertEqual(right, 35)
        self.assertEqual(bottom, 35)

    def test_dial_prop_tx_action_touch_zone_prevents_accidental_fire(self):
        # The ACTION-button hit rectangle moved into prop_tx_config.h ([7] TOUCH
        # ZONES); the gating logic (_touch_in_action_button, command-mode guard) stays
        # in app_prop_tx.cpp. Read cpp + config so the moved constants are found.
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "PROP_TX_ACTION_TOUCH_LEFT   = 72",
                "PROP_TX_ACTION_TOUCH_RIGHT  = 168",
                "PROP_TX_ACTION_TOUCH_TOP    = 74",
                "PROP_TX_ACTION_TOUCH_BOTTOM = 166",
                "_touch_in_action_button(x, y)",
                "_is_command_mode() && _touch_in_action_button(x, y)",
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            ["else if (y > 50 && y < 190)"],
        )

    def test_dial_prop_tx_touch_row_selects_led_without_firing_action(self):
        # The LED touch-strip rectangle + dot layout moved into prop_tx_config.h
        # ([7] TOUCH ZONES). PROP_TX_LED_TOUCH_RIGHT widened 188->221 for the 5th LED
        # column; the touch-select status label is now "LED %u BARVA" (HUE field is
        # labelled BARVA). Read cpp + config so the moved constants are found.
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "PROP_TX_LED_TOUCH_LEFT   = 52",
                "PROP_TX_LED_TOUCH_RIGHT  = 221",
                "PROP_TX_LED_TOUCH_TOP    = 168",
                "PROP_TX_LED_TOUCH_BOTTOM = 220",
                "PROP_TX_LED_START_X      = 70",
                "PROP_TX_LED_SPACING      = 33",
                "_touch_in_led_strip(x, y)",
                "_select_led_from_touch(x)",
                '"LED %u BARVA"',
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )

    def test_dial_prop_tx_touch_zones_match_rendered_geometry(self):
        gui = self.read("firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp")
        app = (
            self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
            + "\n"
            + self.read("firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h")
        )

        action_top = self.constant(app, "PROP_TX_ACTION_TOUCH_TOP")
        action_bottom = self.constant(app, "PROP_TX_ACTION_TOUCH_BOTTOM")
        led_left = self.constant(app, "PROP_TX_LED_TOUCH_LEFT")
        led_right = self.constant(app, "PROP_TX_LED_TOUCH_RIGHT")
        led_top = self.constant(app, "PROP_TX_LED_TOUCH_TOP")
        led_bottom = self.constant(app, "PROP_TX_LED_TOUCH_BOTTOM")

        dots = self.led_dot_centres(gui)
        led_radius = 13  # touch-target radius around each rendered dot centre

        # the led touch band brackets every dot on the arc (centres +/- radius);
        # the band bottom is capped by the quit zone (y=220) so on the lowest dot it
        # covers the centre exactly rather than centre+radius
        self.assertLessEqual(led_top, min(y for _, y in dots) - led_radius)
        self.assertGreaterEqual(led_bottom, max(y for _, y in dots))
        self.assertLessEqual(led_left, min(x for x, _ in dots) - led_radius)
        self.assertGreaterEqual(led_right, max(x for x, _ in dots) + led_radius)
        # bands do not overlap and the action band sits above the led band
        self.assertLess(action_bottom, led_top)
        # the quit zone (y > 220) sits at/below the led band without overlap
        self.assertGreaterEqual(220 - led_bottom, 0)

    def test_dial_prop_tx_led_arc_channel_mapping_spans_the_dots(self):
        gui = self.read("firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp")
        app = (
            self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
            + "\n"
            + self.read("firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h")
        )
        start = self.constant(app, "PROP_TX_LED_START_X")
        spacing = self.constant(app, "PROP_TX_LED_SPACING")
        dots = self.led_dot_centres(gui)

        # touch x->channel mapping (x - (start - spacing/2)) / spacing must land
        # each rendered dot centre on its own channel index
        for idx, (x, _) in enumerate(dots):
            mapped = int((x - (start - spacing // 2)) // spacing)
            mapped = max(0, min(3, mapped))
            self.assertEqual(mapped, idx)

    def test_dial_prop_tx_hero_text_stays_readable(self):
        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp")
        # the edited value now lives inside the centred orb, drawn big with a
        # colour that contrasts the led colour
        self.assertIn("draw_orb(_canvas, CX, ORB_CY, ORB_R", text)
        self.assertIn("on_color(color)", text)
        self.assertIn("setFont(GUI_FONT_CN_BIG)", text)
        # the orb shows the edited field's value (HUE/MODE text) or the LED number, taken from
        # view.field_value / selected_led (the inline "%u\xC2\xB0"/"%u%%" formatting moved upstream
        # into the controller this session, so the format literals no longer live in the GUI source)
        self.assertIn('snprintf(oval, sizeof(oval), "%s", view.field_value)', text)
        self.assertIn('snprintf(oval, sizeof(oval), "%u", view.selected_led + 1)', text)
        self.assertNotIn("TFT_BLACK", text)

    def test_dial_prop_tx_does_not_persist_arm_and_binds_ack(self):
        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        self.assertNotIn('nvs_get_u8(nvs, "armed"', text)
        self.assertNotIn('nvs_set_u8(nvs, "armed"', text)
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                'nvs_erase_key(nvs, "armed")',
                "_data.armed = false",
                "_data.pending_nonce = frame.nonce",
                "_data.pending_type = frame.type",
                # the received ack frame is now bound as `decoded` (was `ack`); the
                # route/key/nonce match + payload check are unchanged in intent.
                "decoded.source == PROP_DESTINATION",
                "decoded.keyId == PROP_KEY_ID",
                "decoded.nonce == _data.pending_nonce",
                "_ack_payload_matches(decoded)",
            ],
        )

    def test_dial_prop_tx_arm_uses_heartbeat_not_local_disarm(self):
        # Permanent ARM on the Dial (task #25: no local auto-disarm). The safety
        # backstop moved to the receiver's 12s TTL, refreshed by a 5s ARM heartbeat
        # the Dial re-sends while armed (Sprint A A2 link-loss watchdog).
        # ARM_HEARTBEAT_MS moved into prop_tx_config.h ([4] TIMINGS / ARM); the
        # heartbeat logic that consumes it stays in app_prop_tx.cpp. Read both.
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "ARM_HEARTBEAT_MS = 5000",
                "_data.armed_started_ms = millis()",
                "millis() - _data.armed_hb_ms >= ARM_HEARTBEAT_MS",
                "_send_arm(1)",
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
            ["uint32_t armed_started_ms = 0", "uint32_t armed_hb_ms = 0"],
        )

    def test_dial_prop_tx_bad_mac_does_not_cancel_pending_ack(self):
        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        bad_mac_branch = text.split("if (!prop_protocol::hexToBytes", 1)[1].split(
            "if (_data.awaiting_ack &&", 1
        )[0]
        self.assertIn('"RX IGNORED"', bad_mac_branch)
        self.assertNotIn("_data.awaiting_ack = false", bad_mac_branch)
        self.assertNotIn("_data.armed = false", bad_mac_branch)

    def test_dial_prop_tx_waiting_ack_blocks_new_actions_and_reads_wait(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                "if (_data.awaiting_ack)",
                '"WAIT ACK"',
                "return;",
            ],
        )
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp",
            [
                "view.awaiting_ack",
                'variant = "wait"',
                "draw_wait_sweep(",
                "draw_command_token(_canvas, CX, ORB_CY, sc",
            ],
        )

    def test_dial_prop_tx_modem_errors_drop_pending_ack_and_arm(self):
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                'strncmp(line, "ERR ", 4) == 0',
                "_data.awaiting_ack = false",
                "_disarm()",
                '_set_status("%.40s", line)',
            ],
        )

    def test_dial_prop_tx_input_waits_keep_link_service_alive(self):
        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        running = text.split("void PropTx::onRunning()", 1)[1].split("void PropTx::onDestroy()", 1)[
            0
        ]
        self.assertIn("bool PropTx::_service_link_during_input_wait()", text)
        self.assertIn("_poll_uart();", text)
        self.assertIn("_handle_ack_timeout();", text)
        self.assertIn("_data.armed && millis() - _data.armed_hb_ms >= ARM_HEARTBEAT_MS", text)
        held_button = running.split("while (!_data.hal->encoder.btn.read())", 1)[1].split(
            "if (!fired_long)", 1
        )[0]
        stable_release = running.split("while (millis() - stable_since < 50)", 1)[1].split(
            "_data.encoder_button_released_after_move", 1
        )[0]
        touch_release = running.split("while (_data.hal->tp.isTouched())", 1)[1].split(
            "if ((millis() - _data.last_status_ms) > 250)", 1
        )[0]
        for block in (held_button, stable_release, touch_release):
            self.assertIn("_service_link_during_input_wait()", block)
            self.assertNotIn("delay(5);", block)

    def test_din_prop_rx_app_drives_five_led_sequence_on_port_b(self):
        # DinMeter redesign this session:
        #   * LED_COUNT 4->5 and the count moved into prop_config.h ([1] STRIP);
        #   * output is now an Adafruit NeoDriver (seesaw NeoPixel over I2C), so the
        #     old bit-banged Adafruit_NeoPixel + LED_PIN=2 are gone -- the strip object
        #     is `seesaw_NeoPixel pixels(...)`;
        #   * the old EffectConfig (intensity/periodMs/ledDelayMs/preTrigger/shapeParam/
        #     repeat/shape) was replaced by the LED#4 OdpalEnvelope fire-flash engine
        #     (ramp/hold/fade ms + a curve SHAPE: HRANA/LIN/SINUS).
        # Read prop_rx.cpp + prop_config.h so the moved LED_COUNT is found.
        text = self.module_text(
            "firmware/din-rx/src/prop_rx.cpp",
            "firmware/din-rx/src/prop_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "LED_COUNT = 5",  # was 4, now in prop_config.h
                "seesaw_NeoPixel pixels",  # was Adafruit_NeoPixel + LED_PIN=2 (removed)
                "PREVIEW",
                "FIRE",
                "STOP",
                "prop_protocol.h",
                "RX ",
                "decodeFrame",
                "FrameType::Preview",
                "FrameType::Fire",
                "Preferences",
                "ACK ",
                # current effect engine = the LED#4 odpal fire-flash envelope
                "OdpalEnvelope",
                "rampMs",
                "holdMs",
                "fadeMs",
                "curveShape",  # the ramp/fade SHAPE curve (was the old shape/shapeParam)
            ],
            "din-rx module (prop_rx.cpp + prop_config.h)",
        )

    def test_din_prop_rx_ui_matches_approved_desktop_mockup_visual_contract(self):
        # Re-approved this session to the redesigned receiver UI: the single status/plot screen
        # was replaced by the Stav / Barvy / Cas / Jas pages, and the shared theme colours + layout
        # constants moved to ui_theme_generated.h (single source tools/m5_theme.json). The contract
        # now pins the stable, current structure -- the page renderers, status/arrow chrome, the
        # firmware-only derived colours, and the fixed screen geometry -- rather than the old
        # pre-redesign layout literals. (Theme colours/layout are covered by the generated header.)
        self.assert_contains_all(
            "firmware/din-rx/src/prop_rx.cpp",
            [
                "SCREEN_W = 240",
                "SCREEN_H = 135",
                # firmware-only derived colours (shared theme + layout now in ui_theme_generated.h)
                "SELECT_BG = 0x26313B",
                "LABEL_DIM = 0x88898B",
                "TRACK_DIM = 0x22292B",
                # the redesigned receiver pages + chrome
                "void drawStav(",
                "void drawStatusBar(",
                "void drawFunctionRow(",
                "void drawArrowRow(",
                "void drawBarvy(",
                "void drawCas(",
                "void drawJas(",
                "void drawWarningGlyph(",
                "void drawBattery(",
            ],
        )

    def test_din_prop_rx_rejects_bad_route_payload_and_limits_power(self):
        text = self.read("firmware/din-rx/src/prop_rx.cpp")
        self.assertNotIn("applyLedPayload(frame.payload);\n            showPreview();", text)
        self.assertNotIn("applyLedPayload(frame.payload);\n            startFire();", text)
        self.assert_contains_all(
            "firmware/din-rx/src/prop_rx.cpp",
            [
                "validateFrameRoute",
                "frame.keyId != PROP_KEY_ID",
                "frame.source != PROP_DESTINATION",
                "frame.destination != PROP_SOURCE",
                "bool applyLedPayload",
                "return false",
                "LED_CURRENT_BUDGET_MA",
                "showBudgetedFrame",
                "SETTINGS_SAVE_DEBOUNCE_MS",
                'preferences.putUInt("lastSeq"',
            ],
        )

    def test_din_prop_rx_stop_fence_is_monotonic_and_colorset_guarded(self):
        text = self.read("firmware/din-rx/src/prop_rx.cpp")

        stop_branch = text.split("if (frame.type == prop_protocol::FrameType::Stop)", 1)[1].split(
            "if (frame.type == prop_protocol::FrameType::Ping", 1
        )[0]
        self.assertNotIn("_lockoutSeq = frame.sequence;", stop_branch)
        self.assertTrue(
            "rememberStopFence(frame);" in stop_branch
            or "if (frame.sequence > _lockoutSeq)" in stop_branch
        )

        colorset_branch = text.split("if (frame.type == prop_protocol::FrameType::LedColorSet)", 1)[
            1
        ].split("if (frame.type == prop_protocol::FrameType::RemoteLed)", 1)[0]
        self.assertIn("droppedByStopOrder(frame)", colorset_branch)
        self.assertLess(
            colorset_branch.index("droppedByStopOrder(frame)"),
            colorset_branch.index("applyLedPayload(frame.payload)"),
        )
        self.assertIn('sendAckFrame(frame, "COLORSET")', colorset_branch)

    def test_c6l_modem_rejects_unready_radio_and_waits_for_matching_ack(self):
        # The unready-radio guard + frame-bounds + host-command parse migrated into
        # modem_core.h (single source w/ the host simulator); main.cpp keeps the
        # dispatch + a few host strings. Read both. RadioLib's String::startsWith was
        # replaced by std::string::compare in the migrated core -- update those needles.
        text = self.module_text(
            "firmware/c6l-modem/src/main.cpp",
            "firmware/c6l-modem/src/modem_core.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "radioReady",
                "ERR RADIO_NOT_READY",
                "enterReceive()",
                "looksLikeMatchingAck",
                "ERR LINE_TOO_LONG",
                "frame.empty()",
                "frame.size() > MAX_RADIO_FRAME",
                'line.compare(0, 5, "SEND ") == 0',
                'line.compare(0, 4, "ACK ") == 0',
                'reportHost("ERR BAD_FRAME")',
            ],
            "c6l-modem module (main.cpp + modem_core.h)",
        )

    def test_docs_and_tools_cover_hardware_and_builds(self):
        self.assert_contains_all(
            "docs/hardware.md",
            [
                "Port A",
                "G13",
                "G15",
                "Unit C6L",
                "Port B",
                "G1/G2",
                "NeoDriver",
                "ByteButton",
                "LED-only",
            ],
        )
        self.assert_contains_all("tools/build.ps1", ["dial-tx", "din-rx", "c6l-modem"])
        self.assert_contains_all("tools/flash.ps1", ["dial-tx", "din-rx", "c6l-modem"])
        self.assert_contains_all("firmware/dial-tx/main/CMakeLists.txt", ["gui_prop_tx.cpp"])

    def test_build_helper_runs_pytest_and_gates_release_toolchains(self):
        self.assert_contains_all(
            "tools/build.ps1",
            [
                "[switch]$Release",
                "$RequireFirmwareToolchains",
                '$env:CI -eq "true"',
                "-m pytest tests -v",
                "required in CI/release mode",
                "PlatformIO command 'pio' was not found",
                "ESP-IDF command 'idf.py' was not found",
                "Invoke-ReleaseGates",
                "Get-ReleaseBuildDefineArgs",
                "PROP_ALLOW_PROTOTYPE_SHARED_KEY=0",
                "PROP_TX_ALLOW_SELFTEST_FIRE=0",
                "SELFTEST_FIRE=0",
                "Prototype HMAC key is still compiled in",
                "uiflow/dial/prop_frame.py",
                "PROTOTYPE_SHARED_KEY\\s*=\\s*True",
                '$Release -or ($env:CI -eq "true")',
            ],
        )
        self.assert_not_contains_any("tools/build.ps1", ["-m unittest", "unittest discover"])

    def test_release_build_flags_are_consumed_by_firmware_build_systems(self):
        self.assert_contains_all(
            "firmware/din-rx/gen_theme_pre.py",
            ["PROP_RELEASE_BUILD_FLAGS", "shlex.split", "env.Append", "BUILD_FLAGS"],
        )
        self.assert_contains_all(
            "firmware/dial-tx/CMakeLists.txt",
            ["PROP_RELEASE_BUILD_FLAGS", "separate_arguments", "add_compile_options"],
        )

    def test_prototype_hmac_key_is_marked_and_release_blocked(self):
        tx = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        rx = self.read("firmware/din-rx/src/prop_rx.cpp")
        ui = self.read("uiflow/dial/prop_frame.py")
        for text in (tx, rx):
            self.assertIn("PROP_ALLOW_PROTOTYPE_SHARED_KEY", text)
            self.assertIn("#error", text)
            self.assertIn("prototype shared HMAC key", text)
        self.assertIn("PROTOTYPE_SHARED_KEY = True", ui)
        self.assertIn("PROP_TX_ALLOW_SELFTEST_FIRE", tx)
        self.assertIn("SELFTEST_FIRE requires explicit bench-only", tx)

    def test_release_build_fails_closed_while_prototype_hmac_key_is_present(self):
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if shell is None:
            self.skipTest("PowerShell is not available")

        command = [shell, "-NoProfile"]
        if Path(shell).name.lower().startswith("powershell"):
            command += ["-ExecutionPolicy", "Bypass"]
        command += ["-File", str(ROOT / "tools" / "build.ps1"), "-Release"]

        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        combined = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Prototype HMAC key is still compiled in", combined)
        self.assertIn("Release gates failed", combined)
        self.assertNotIn("PlatformIO command 'pio' was not found", combined)
        self.assertNotIn("ESP-IDF command 'idf.py' was not found", combined)


if __name__ == "__main__":
    unittest.main()
