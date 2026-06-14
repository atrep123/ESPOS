from pathlib import Path
import os
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
ESPOS_ROOT = ROOT.parents[1]


class ProjectSourceTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = ROOT / relative_path
        if not path.exists():
            self.fail(f"{relative_path} does not exist")
        return path.read_text(encoding="utf-8")

    def read_espos(self, relative_path: str) -> str:
        path = ESPOS_ROOT / relative_path
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
        # moved pin knobs are found. Setup/editor fields now live on the Terminal;
        # the Dial keeps only a command action selector.
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
                "selected_action",
                "_adjust_selected_action(direction)",
                '"SETUP NA TERMINALU"',
                "FrameType::Ack",
                "_poll_uart",
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )

    def test_dial_setup_editor_paths_are_not_active_today(self):
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
            "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "DIAL_SETUP_EDITOR_ENABLED  = false",
                '"SETUP NA TERMINALU"',
                "_adjust_selected_action(direction)",
            ],
            "dial command-only setup handoff",
        )
        self.assert_text_not_contains_any(
            text,
            [
                "_data.mode = PROP_TX::MODE_SETUP",
                "_next_field();",
                "_select_led_from_touch(x);",
                "_touch_in_led_strip(x, y)",
                "else if (!_locked() && !_is_command_mode())",
            ],
            "dial command-only setup handoff",
        )

    def test_dial_command_surface_does_not_push_terminal_owned_palette_or_remote_leds(self):
        text = self.module_text(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
        )
        command_block = text.split("COMMAND_ACTIONS", 1)[1].split("#if SELFTEST_FIRE", 1)[0]
        self.assert_text_not_contains_any(
            command_block,
            [
                "ACTION_LED3_ON",
                "ACTION_LED5_ON",
            ],
            "dial command action order",
        )
        self.assert_text_not_contains_any(
            text,
            [
                "void PropTx::_send_remote_led",
                "_send_remote_led(",
                "void PropTx::_send_palette",
                "_send_palette(",
            ],
            "dial production command path",
        )

    def test_dinmeter_local_setup_editor_is_disabled_by_default(self):
        text = self.module_text(
            "firmware/din-rx/src/prop_rx.cpp",
            "firmware/din-rx/src/prop_config.h",
        )
        self.assert_text_contains_all(
            text,
            [
                "DINMETER_LOCAL_SETUP_EDITOR_ENABLED = false",
                "if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)",
            ],
            "dinmeter indication-only production guard",
        )
        for mutator in (
            "void handleEncoder",
            "void handleShortPress",
            "void handleLongPress",
            "void advancePage",
        ):
            block = text.split(mutator, 1)[1].split("\n    }", 1)[0]
            self.assertIn("DINMETER_LOCAL_SETUP_EDITOR_ENABLED", block, mutator)

    def test_dinmeter_modem_line_buffer_uses_shared_protocol_budget(self):
        text = self.read("firmware/din-rx/src/prop_rx.cpp")
        self.assertIn("prop_protocol::MAX_HOST_RX_LINE_LENGTH", text)
        self.assertNotIn("_line.length() < 160", text)

    def test_dial_does_not_persist_terminal_owned_palette_state(self):
        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        load_section = text[
            text.index("void PropTx::_load_settings()") :
            text.index("bool PropTx::_load_runtime_key()", text.index("void PropTx::_load_settings()"))
        ]
        save_section = text[
            text.index("void PropTx::_save_settings()") :
            text.index("void PropTx::_save_sequence()", text.index("void PropTx::_save_settings()"))
        ]
        rx_section = text[
            text.index("if (decoded.type == prop_protocol::FrameType::LedColorSet)") :
            text.index("const bool ack_route_matches", text.index("if (decoded.type == prop_protocol::FrameType::LedColorSet)"))
        ]

        self.assertNotIn("nvs_get_blob", load_section)
        self.assertNotIn("nvs_set_blob", save_section)
        for key in ('"palFade"', '"colors"', '"hueDeg"', '"hues"'):
            self.assertIn(f"nvs_erase_key(nvs, {key})", load_section + save_section)
        self.assertNotIn("_save_settings();", rx_section)
        self.assertNotIn("BARVY SYNC", rx_section)
        self.assertNotIn("PALETA SYNC", rx_section)

    def test_dinmeter_terminal_commit_does_not_sync_setup_back_to_dial(self):
        text = self.read("firmware/din-rx/src/prop_rx.cpp")
        begin_section = text[
            text.index("void begin()") :
            text.index("Serial.begin", text.index("void begin()"))
        ]
        commit_section = text[
            text.index("bool commitTerminalSetup") :
            text.index("bool previewTerminalSimFire", text.index("bool commitTerminalSetup"))
        ]

        for load_call in ("loadPalette();", "loadLedColors();", "loadOdpalCfg();", "loadLedBrightness();"):
            self.assertIn(load_call, begin_section)
        self.assertIn("if (DINMETER_LOCAL_SETUP_EDITOR_ENABLED)", begin_section)
        self.assertIn("loadTerminalSetupState();", begin_section)
        self.assertNotIn("sendLedColorSet();", commit_section)
        self.assertNotIn("sendPaletteSet();", commit_section)

    def test_dinmeter_usb_setup_overflow_is_scoped_and_uses_shared_budget(self):
        text = self.module_text(
            "firmware/din-rx/src/prop_rx.cpp",
            "shared/terminal/terminal_setup_link.h",
        )
        self.assertIn("_usbSetupLine.length() < prop_protocol::MAX_HOST_RX_LINE_LENGTH", text)
        self.assertIn("formatUnscopedResponseLine", text)
        self.assertIn('+ " 0"', text)
        self.assertNotIn("Serial.println(terminal_setup_link::RESPONSE_ERR);", text)

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
                "std::array<uint16_t, 8> hues",
            ],
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h",
            ["FIELD_RED", "FIELD_GREEN", "FIELD_BLUE", "FIELD_HUE", "selected_field"],
        )
        # HUE_MAX moved into prop_tx_config.h ([7] colour-wheel range). Dial keeps
        # factory hue/color helpers for effect payload defaults, but no longer
        # persists setup-owned palette state.
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
                "FIELD_HUE",
                '"LED %u BARVA"',
                'nvs_get_blob(nvs, "hueDeg"',
                'nvs_set_blob(nvs, "hueDeg"',
                'nvs_get_blob(nvs, "hues"',
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
                'variant = "stop"',
                "draw_wait_sweep(",
                "draw_check_glyph(",
                "draw_x_glyph(",
                '"NO FIRE"',
                '"OUTPUT OFF"',
                '"FIRE LOCKED"',
                '"ARM REQUIRED"',
                '"STOP"',
                '"OUTPUT OFF"',
                '"DO NOT PRESS"',
                '"PRESS"',
                '"TO DISARM"',
                "field_caption(view)",
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

    def test_dial_prop_tx_hue_is_protocol_state_not_dial_editor_state(self):
        # Hues remain factory effect-payload defaults, but Dial no longer projects
        # them into an editable setup view or persists terminal-owned palette state.
        self.assert_contains_all(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            [
                "hue_from_rgb",
                "wrap_hue",
                'nvs_erase_key(nvs, "hueDeg")',
                'nvs_erase_key(nvs, "hues")',
                'snprintf(view.field_value, sizeof(view.field_value), "%s", view.action_label == nullptr ? "" : view.action_label)',
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
                "view.selected_hue_degrees",
                "selected_field",
                "_field_value",
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
        # ZONES); Dial is command-only now, so the touch gate is just locked-state
        # plus the action hitbox. Read cpp + config so moved constants are found.
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
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )
        self.assert_not_contains_any(
            "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp",
            ["else if (y > 50 && y < 190)"],
        )

    def test_dial_prop_tx_touch_row_no_longer_selects_setup_led(self):
        # The older LED touch-strip geometry can remain documented in the config
        # for render parity, but the active Dial app must not use it as an editor.
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
            ],
            "dial prop_tx module (app_prop_tx.cpp + prop_tx_config.h)",
        )
        self.assert_text_not_contains_any(
            text,
            [
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

    def test_dial_ignores_dinmeter_palette_sync_for_terminal_owned_setup(self):
        text = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")

        palette_branch = text.split("if (decoded.type == prop_protocol::FrameType::PaletteSet)", 1)[
            1
        ].split("const bool ack_route_matches", 1)[0]
        led_branch = text.split("if (decoded.type == prop_protocol::FrameType::LedColorSet)", 1)[
            1
        ].split("if (decoded.type == prop_protocol::FrameType::PaletteSet)", 1)[0]
        self.assertRegex(palette_branch, r"\{\s*return;\s*\}")
        self.assertRegex(led_branch, r"\{\s*return;\s*\}")
        self.assertNotIn("prop_protocol::parsePalettePayload", palette_branch)
        self.assertNotIn("_save_settings()", palette_branch + led_branch)
        self.assertNotIn("_set_status(\"PALETA SYNC\")", palette_branch)
        self.assertNotIn("_set_status(\"BARVY SYNC\")", led_branch)

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
        self.assert_contains_all("tools/build.ps1", ["dial-tx", "din-rx", "c6l-modem", "sticks3-terminal"])
        self.assert_contains_all("tools/flash.ps1", ["dial-tx", "din-rx", "c6l-modem", "sticks3-terminal"])
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
                "Get-FirmwareBuildDefineArgs",
                "PROP_TX_ALLOW_SELFTEST_FIRE=0",
                "SELFTEST_FIRE=0",
                "Runtime HMAC key provider is incomplete",
                "C++ firmware must use the runtime HMAC key provider",
                "C++ firmware still uses a source-embedded HMAC key",
                '$Release -or ($env:CI -eq "true")',
            ],
        )
        self.assert_not_contains_any("tools/build.ps1", ["-m unittest", "unittest discover"])

    def test_root_ci_runs_m5_deterministic_gates(self):
        workflow = self.read_espos(".github/workflows/ci.yml")

        self.assert_text_contains_all(
            workflow,
            [
                "M5 Prop LoRa static + dry-smoke gates (no firmware build)",
                "if: matrix.python-version == '3.12'",
                "working-directory: integrations/m5-prop-lora",
                "python -m pytest -q --tb=short tests",
                "Toolchain-light release invariant check",
                "tools/build.ps1 -ReleaseGatesOnly",
                "python tools/validate_uiflow_blocks.py",
                "python tools/uiflow_dial_offline.py bundle --dry-smoke --out \"$RUNNER_TEMP/m5_uiflow_dial_offline\"",
                "python tools/uiflow_dial_offline.py verify --bundle \"$RUNNER_TEMP/m5_uiflow_dial_offline\"",
                "M5 host C++ logic",
                "./tools/run_host_tests.ps1",
                "M5 Terminal firmware build",
                "pio run -d firmware/sticks3-terminal -e sticks3-terminal",
                "pio run -d firmware/sticks3-terminal -e sticks3-terminal-chain-uart-smoke",
                "pio run -d firmware/sticks3-terminal -e sticks3-terminal-oled-i2c-scan-smoke",
            ],
            ".github/workflows/ci.yml",
        )
        self.assert_text_not_contains_any(
            workflow,
            [
                "tools/build.ps1 -Release\n",
                "idf.py -C firmware/dial-tx",
            ],
            ".github/workflows/ci.yml",
        )

    def test_build_docs_explain_host_safety_test_compiler_prereq(self):
        self.assert_contains_all(
            "BUILD.md",
            [
                "Host C++ logic tests",
                "./tools/run_host_tests.ps1",
                "firmware/tests/test_*.cpp",
                "Terminal pure logic",
                "g++",
                "WinLibs",
                "winget install --id BrechtSanders.WinLibs.POSIX.UCRT",
                "sudo apt-get install g++",
                "xcode-select --install",
                "-Compiler",
                "CI / local deterministic gates",
                "CI-equivalent local gate from the ESPOS repo root",
                "python -m pytest -q --tb=short tests",
                "python tools/uiflow_dial_offline.py verify --bundle build/m5_uiflow_dial_offline",
                "Terminal PlatformIO firmware builds",
                "sticks3-terminal-chain-uart-smoke",
                "sticks3-terminal-oled-i2c-scan-smoke",
                "does not compile Dial ESP-IDF or non-Terminal PlatformIO firmware images",
                "./tools/build.ps1 -Release",
                "hardware key provisioning",
            ],
        )

    def test_host_cpp_runner_discovers_all_firmware_test_cpp_files(self):
        self.assert_contains_all(
            "tools/run_host_tests.ps1",
            [
                "$TestDir  = Join-Path $RepoRoot 'firmware/tests'",
                "-Filter 'test_*.cpp'",
                "shared/terminal + sticks3-terminal pure logic",
                "USB setup replies",
                "Arduino",
                "Get-ChildItem",
                "& $gxx",
                "& $exe",
            ],
        )

    def test_docs_do_not_overstate_chain_key_or_production_acceptance(self):
        readme = self.read("README.md")
        self.assert_text_contains_all(
            readme,
            [
                "dry-smoke bench work is supported",
                "full current hardware acceptance, including Chain Key, is pending",
                "Production release requires runtime non-source HMAC key provisioning",
            ],
            "README.md",
        )
        self.assert_text_not_contains_any(
            readme,
            [
                "chain (Dial",
                "LoRa + 2.4 link, ARM/Fire/Preview/sync",
            ],
            "README.md",
        )

        control = self.read("docs/control_architecture.md")
        self.assert_text_contains_all(
            control,
            [
                "M5Stack Chain Key",
                "Port B",
                "UART/M5Chain",
                "VERIFY ON DEVICE",
            ],
            "docs/control_architecture.md",
        )
        self.assert_text_not_contains_any(
            control,
            [
                "NEW, to be added",
                "new GPIO",
                "pick the FIRE-button GPIO",
            ],
            "docs/control_architecture.md",
        )

    def test_release_build_flags_are_consumed_by_firmware_build_systems(self):
        self.assert_contains_all(
            "firmware/din-rx/gen_theme_pre.py",
            ["PROP_RELEASE_BUILD_FLAGS", "shlex.split", "env.Append", "BUILD_FLAGS"],
        )
        self.assert_contains_all(
            "firmware/dial-tx/CMakeLists.txt",
            ["PROP_RELEASE_BUILD_FLAGS", "separate_arguments", "add_compile_options"],
        )

    def test_cpp_hmac_key_is_runtime_provisioned_and_uiflow_key_fails_closed(self):
        tx = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        rx = self.read("firmware/din-rx/src/prop_rx.cpp")
        tx_h = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h")
        provider = self.read("shared/protocol/prop_runtime_key.h")
        ui = self.read("uiflow/dial/prop_frame.py")
        for text in (tx, rx):
            self.assertIn("prop_runtime_key.h", text)
            self.assertIn("RuntimeKey", text)
            self.assertIn("KEY MISSING", text)
            self.assertNotIn("SHARED_KEY[]", text)
            self.assertNotIn("sizeof(SHARED_KEY)", text)
        self.assertIn("prop_runtime_key::RuntimeKey _runtime_key", tx_h)
        self.assertIn("NVS_NAMESPACE", provider)
        self.assertIn("NVS_KEY", provider)
        self.assertIn("MIN_KEY_LENGTH = 16", provider)
        self.assertIn("isKnownDrySmokeKey", provider)
        self.assertIn("secureZero", provider)
        self.assertIn("volatile std::uint8_t* p", provider)
        self.assertIn("secureZero(bytes)", provider)
        self.assertIn("PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY", provider)
        self.assertNotIn("00112233445566778899aabbccddeeff", provider)
        self.assertIn("import prop_key", ui)
        self.assertIn("prop_key.py did not provide SHARED_KEY_HEX", ui)
        self.assertIn("prop_key.py must not define SHARED_KEY", ui)
        self.assertIn("ALLOW_PROTOTYPE_SHARED_KEY", ui)
        self.assertIn("dry-smoke HMAC key", ui)
        self.assertIn("DRY_SMOKE_KEY_ACTIVE", ui)
        self.assertNotIn("00112233445566778899aabbccddeeff", ui)
        self.assertNotIn("_PROTOTYPE_KEY", ui)
        self.assertNotIn("SHARED_KEY = bytes(", ui)
        self.assertNotIn("00112233445566778899aabbccddeeff", ui)
        self.assertIn("PROP_TX_ALLOW_SELFTEST_FIRE", tx)
        self.assertIn("SELFTEST_FIRE requires explicit bench-only", tx)
        self.assertIn("prop_runtime_key::secureZero(buffer)", tx)
        self.assertIn("prop_runtime_key::secureZero(buffer)", rx)

    def test_dial_tx_send_paths_use_runtime_hmac_key_material(self):
        tx = self.read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
        for method in [
            "_send_frame",
            "_send_fire_burst",
            "_send_arm",
        ]:
            with self.subTest(method=method):
                start = tx.index(f"PropTx::{method}")
                next_method = tx.find("\nvoid PropTx::", start + 1)
                if next_method == -1:
                    next_method = tx.find("\nbool PropTx::", start + 1)
                body = tx[start: next_method if next_method != -1 else len(tx)]
                self.assertIn("_runtime_key_or_status()", body)
                self.assertIn("key->data()", body)
                self.assertIn("key->size()", body)
                self.assertIn("prop_protocol::encodeFrame", body)

    def test_release_gate_checks_runtime_hmac_provider_instead_of_compiled_key(self):
        build = self.read("tools/build.ps1")
        self.assertIn("shared/protocol/prop_runtime_key.h", build)
        self.assertIn("load_runtime_key_from_nvs", build)
        self.assertIn("loadRuntimeKeyFromPreferences", build)
        self.assertIn("PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=0", build)
        self.assertIn("DEBUG_HUD=0", build)
        self.assertIn("Get-ReleaseBuildDefineMap", build)
        self.assertIn("Test-ReleaseDefineIsExactlyZero", build)
        self.assertIn("Test-RuntimeKeyAtRestPolicy", build)
        self.assertIn("docs/runtime_key_at_rest_decision.json", build)
        self.assertIn("PROP_RUNTIME_KEY_AT_REST_DECISION", build)
        self.assertIn('$releaseFlags = $env:PROP_RELEASE_BUILD_FLAGS', build)
        self.assertIn('(Get-FirmwareBuildDefineArgs) -join " "', build)
        self.assertIn("Release builds must reject the dry-smoke runtime HMAC key.", build)
        self.assertIn("Release builds must disable receiver debug HUD/serial diagnostics.", build)
        self.assertIn("Release builds must disable bench self-test fire override.", build)
        self.assertIn("Release builds must keep bench auto-fire disabled.", build)
        self.assertIn("SHARED_KEY\\s*\\[\\]", build)
        self.assertIn("sizeof\\s*\\(\\s*SHARED_KEY\\s*\\)", build)
        self.assertNotIn("Prototype HMAC key is still compiled in", build)

    def test_release_gates_reject_nonzero_missing_or_duplicate_safety_defines(self):
        cases = [
            (
                "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=0x10 "
                "-DPROP_TX_ALLOW_SELFTEST_FIRE=0 -DSELFTEST_FIRE=0 -DDEBUG_HUD=0",
                "Release builds must reject the dry-smoke runtime HMAC key.",
            ),
            (
                "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=0 "
                "-DPROP_TX_ALLOW_SELFTEST_FIRE=0 -DSELFTEST_FIRE=0 "
                "-DDEBUG_HUD=0 -DDEBUG_HUD=1",
                "Release build define DEBUG_HUD is set more than once.",
            ),
            (
                "-DPROP_TX_ALLOW_SELFTEST_FIRE=0 -DSELFTEST_FIRE=0 -DDEBUG_HUD=0",
                "Release builds must reject the dry-smoke runtime HMAC key.",
            ),
        ]
        for flags, expected_error in cases:
            with self.subTest(flags=flags):
                env = os.environ.copy()
                env["PROP_RELEASE_BUILD_FLAGS"] = flags
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ROOT / "tools" / "build.ps1"),
                        "-ReleaseGatesOnly",
                    ],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_release_gates_require_runtime_key_at_rest_policy_decision(self):
        valid_policy = ROOT / "docs" / "runtime_key_at_rest_decision.json"
        self.assertTrue(valid_policy.exists())
        policy_text = valid_policy.read_text(encoding="utf-8")
        self.assertIn("prop-runtime-key-at-rest-decision-v1", policy_text)
        self.assertIn("accepted-with-waiver", policy_text)
        self.assertIn("raw_key_bytes_allowed_in_repo", policy_text)
        self.assertNotIn("00112233445566778899aabbccddeeff", policy_text)

        sdkconfig = self.read("firmware/dial-tx/sdkconfig")
        self.assertIn("# CONFIG_SECURE_BOOT is not set", sdkconfig)
        self.assertIn("# CONFIG_FLASH_ENCRYPTION_ENABLED is not set", sdkconfig)

        cases = [
            (ROOT / "build" / "missing-runtime-key-policy.json", "policy decision is required"),
        ]
        invalid_policy = ROOT / "build" / "invalid-runtime-key-policy.json"
        invalid_policy.parent.mkdir(parents=True, exist_ok=True)
        invalid_policy.write_text('{"schema":"wrong"}\n', encoding="utf-8")
        cases.append((invalid_policy, "policy decision schema mismatch"))

        for policy_path, expected_error in cases:
            with self.subTest(policy_path=str(policy_path)):
                env = os.environ.copy()
                env["PROP_RUNTIME_KEY_AT_REST_DECISION"] = str(policy_path)
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ROOT / "tools" / "build.ps1"),
                        "-ReleaseGatesOnly",
                    ],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

        env = os.environ.copy()
        env["PROP_RUNTIME_KEY_AT_REST_DECISION"] = str(valid_policy)
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "tools" / "build.ps1"),
                "-ReleaseGatesOnly",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Release gates completed.", result.stdout)

    def test_disabled_openthread_dataset_does_not_commit_public_credentials(self):
        sdkconfig = self.read("firmware/dial-tx/sdkconfig")

        self.assertIn("# CONFIG_OPENTHREAD_ENABLED is not set", sdkconfig)
        self.assertIn(
            'CONFIG_OPENTHREAD_NETWORK_MASTERKEY="00000000000000000000000000000000"',
            sdkconfig,
        )
        self.assertIn(
            'CONFIG_OPENTHREAD_NETWORK_PSKC="00000000000000000000000000000000"',
            sdkconfig,
        )
        self.assertNotIn("CONFIG_OPENTHREAD_NETWORK_MASTERKEY=\"00112233445566778899aabbccddeeff\"", sdkconfig)
        self.assertNotIn("CONFIG_OPENTHREAD_NETWORK_PSKC=\"104810e2315100afd6bc9215a6bfac53\"", sdkconfig)

    def test_cxx_runtime_key_provisioning_runbook_is_concrete(self):
        self.assert_contains_all(
            "docs/cxx_key_provisioning.md",
            [
                "namespace `prop_key`, key `shared`",
                "prop-key.hex",
                "tools/provision_prop_key.py",
                "prop_key_manifest.json",
                "prop_key_receipt.template.json",
                "prop_key.nvs.csv",
                "sha256(key_bytes)",
                "Hardware Receipt And Readback",
                "read_flash 0x9000 0x6000",
                "readback bins are secret",
                "complete NVS partition image",
                "docs/runtime_key_at_rest_decision.json",
                "secureZero(readback",
                "validated.clear()",
                "loaded.clear()",
                "prop_runtime_key::NVS_NAMESPACE",
                "prop_runtime_key::NVS_KEY",
                "nvs_set_blob",
                "Preferences prefs",
                "prefs.putBytes",
                "KEY MISSING",
                "BAD MAC",
                "Production hardware acceptance remains blocked",
            ],
        )

    def test_uiflow_docs_do_not_regress_block_or_key_upload_paths(self):
        uiflow_readme = self.read("uiflow/dial/README.md")
        bench = self.read("docs/bench_test_checklist.md")
        control = self.read("docs/control_architecture.md")
        self.assertIn("`prop_key.py`, `prop_frame.py`", uiflow_readme)
        self.assertIn("uiflow/dial/blocks/dist/PropTx.m5b2", uiflow_readme)
        self.assertIn("build/uiflow_dial_offline/blocks/PropTx.m5b2", uiflow_readme)
        self.assertIn("--dry-smoke --dry-run", uiflow_readme)
        self.assertIn("--prop-key-hex-file C:\\path\\to\\prop-key.hex", uiflow_readme)
        self.assertIn("docs/cxx_key_provisioning.md", bench)
        self.assertIn("KEY MISSING` for the HMAC runtime key", bench)
        self.assertIn("FIRE KEY MISSING", bench)
        self.assertIn("separate from the physical Chain Key diagnostic", control)
        self.assertNotIn("Import `blocks/PropTx.m5b2`", uiflow_readme)
        self.assertNotIn("currently always `_next_field`", control)


if __name__ == "__main__":
    unittest.main()
