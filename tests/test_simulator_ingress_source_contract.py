"""C source-contract evidence only: no preprocessor, compiler or C execution.

These checks protect wiring to the existing UI clock/scheduler/subscribers.
They deliberately do not claim functional C timing or rendering verification.
"""

import pytest

# Use the imported product root even when the tests are copied to an isolated
# evidence directory to avoid repository conftest environment mutations.
from tools.espos_runtime_simulator import ROOT as PRODUCT_ROOT
from tools.simulator_contract import MAX_ADVANCE_TICKS, MAX_EVENTS, MAX_TICKS_PER_STEP


@pytest.fixture
def source():
    return (PRODUCT_ROOT / "tools/native_simulator/main.c").read_text(encoding="utf-8")


def section(source, start, end):
    return source.split(start, 1)[1].split(end, 1)[0]


def test_c_and_python_bounds_agree_and_all_steps_validate_before_tasks_or_frames(source):
    for name, value in [
        ("SIM_MAX_EVENTS", MAX_EVENTS),
        ("SIM_MAX_STEP_TICKS", MAX_TICKS_PER_STEP),
        ("SIM_MAX_ADVANCE_TICKS", MAX_ADVANCE_TICKS),
    ]:
        assert f"#define {name} {value}\n" in source
    main = source.split("int main(int argc, char **argv)", 1)[1]
    validation = section(main, "unsigned advance_ticks = 0;", "#ifdef SIM_APP")
    assert "event_count = argc - 3;" in validation
    assert "sim_parse_step(argv[i + 3], &steps[i])" in validation
    assert "advance_ticks += steps[i].advance_ticks;" in validation
    assert "if (advance_ticks > SIM_MAX_ADVANCE_TICKS) return 2;" in validation
    assert main.index("sim_parse_step(") < main.index("sim_scheduler_init();")
    assert (
        main.index("sim_parse_step(") < main.index("ui_task(NULL)") < main.index("sim_save_frame(")
    )
    assert "argc > SIM_MAX_EVENTS + 3" in main
    assert 'strcmp(argv[2], "0")' in main and 'strcmp(argv[2], "261")' in main
    assert 'strcmp(argv[2], "-1")' in main and "else return 2;" in main


def test_c_parser_has_exact_ascii_edges_and_numeric_backcompat(source):
    parser = section(source, "static int sim_parse_step(", "#ifdef SIM_APP\n#include")
    assert "if (!length || length > 48) return 0;" in parser
    assert "length <= 3 && sim_decimal(text, length, 255, &value)" in parser
    assert "step->message.u.btn.pressed = 1;" in parser
    assert 'strcmp(edge + 1, "press") != 0 && strcmp(edge + 1, "release") != 0' in parser
    assert 'step->message.u.btn.pressed = strcmp(edge + 1, "press") == 0;' in parser
    assert "id_length > 3" in parser and "text[7] == '0'" in parser
    assert "length > 9 || text[5] == '0'" in parser
    assert "SIM_MAX_STEP_TICKS, &value) || !value" in parser
    assert "step->tick_only = 1;" in parser
    assert "step->advance_ticks = value;" in parser
    decimal = section(source, "static int sim_decimal(", "#ifdef SIM_APP")
    assert "length > 9" in decimal
    assert "text[i] < '0' || text[i] > '9'" in decimal
    assert "if (number > maximum) return 0;" in decimal
    for coercion in ("atoi(", "strtol(", "strtoul("):
        assert coercion not in source
    assert "(kind != 2 && kind != 3 && kind != 20)" in parser
    assert "sim_identifier(id + 1, id_length)" in parser


def test_default_tick_only_uses_the_real_ui_timeout_and_clock_path(source):
    receive = section(source, "int xQueueReceive(", "#endif")
    assert "if (!initial_repaint) { initial_repaint = 1; return 0; }" in receive
    assert "if (cursor >= event_count) longjmp(done, 1);" in receive
    assert "const SimStep *step = &steps[cursor++];" in receive
    assert "memcpy(out, &step->message, sizeof(step->message));" in receive
    assert "remaining_ticks = step->advance_ticks;" in receive
    tick_only = receive.split("remaining_ticks--;", 1)[1]
    assert "esp_timer_set_mock_time(sim_time + 10000LL);" in tick_only
    assert "return 0;" in tick_only
    assert "btn" not in tick_only and "memcpy" not in tick_only
    assert '#include "services/ui/ui.c"' in source
    assert "if (setjmp(done) == 0) ui_task(NULL);" in source


def test_app_preserves_real_subscribers_and_explicit_tick_clock_order(source):
    advance = section(source, "static void sim_advance_ticks(", "#endif")
    ordered = [
        "sim_scheduler_advance(10);",
        "tick->u.tick.tick++;",
        "bus_publish(tick);",
        "sim_scheduler_drain();",
    ]
    positions = [advance.index(operation) for operation in ordered]
    assert positions == sorted(positions)
    main = source.split("int main(int argc, char **argv)", 1)[1]
    assert "ui_start(); ui_app_start(); logic_start();" in main
    assert "sim_scheduler_advance(150);" in main
    assert "tick.topic = TOP_TICK_10MS; tick.u.tick.tick = 15;" in main
    dispatch = section(main, "const SimStep *step = &steps[i];", "#else")
    assert "if (!step->tick_only)" in dispatch
    assert "bus_publish(&step->message);" in dispatch
    assert "sim_scheduler_advance(step->advance_ticks * 10);" in dispatch
    tick_only = dispatch.split("} else {", 1)[1]
    assert "sim_advance_ticks(step->advance_ticks, &tick);" in tick_only
    assert "TOP_INPUT_BTN" not in tick_only and "btn" not in tick_only


def test_frame_failure_still_tears_down_app_and_cannot_forge_wrapper_provenance(source):
    finish = source.split("int frame_error = sim_save_frame(argv[1]);", 1)[1]
    assert "if (!frame_error) {" in finish
    assert "ui_stop(); ui_app_stop(); logic_stop();" in finish
    assert "sim_scheduler_destroy(); bus_deinit();" in finish
    assert finish.index("ui_stop();") < finish.index("return frame_error ? 3 : 0;")
    assert "if (sim_save_frame(argv[1])) return 3;" not in source
    assert r"\"runtime_simulation\":true" in source
    assert r"\"simulation\"" not in source


def test_display_ingress_changes_the_existing_driver_and_requests_real_ui_repaint(source):
    parser = section(source, "static int sim_parse_step(", "#ifdef SIM_APP\n#include")
    for name, value in [("CONNECTED", "0"), ("DISCONNECTED", "0x105"), ("ERROR", "(-1)")]:
        assert f"#define SIM_DISPLAY_{name} {value}" in source
    for status, value in [
        ("connected", "SIM_DISPLAY_CONNECTED"),
        ("disconnected", "SIM_DISPLAY_DISCONNECTED"),
        ("error", "SIM_DISPLAY_ERROR"),
    ]:
        assert f'if (strcmp(text + 8, "{status}") == 0) step->display_status = {value};' in parser
    assert "step->display_status = ESP_ERR_NOT_FOUND" not in parser
    assert "step->display_change = 1;" in parser
    assert "step->advance_ticks = 5;" in parser
    apply = section(source, "static void sim_apply_display(", "#ifndef SIM_APP")
    assert "sim_display_status = step->display_status;" in apply
    assert "store_get_conf(&conf)" in apply
    assert "repaint->topic = TOP_RPC_CALL;" in apply
    assert 'memcpy(repaint->u.rpc.method, "set_bg", sizeof("set_bg"));' in apply
    assert "repaint->u.rpc.arg = conf.bg_rgb;" in apply
    assert "sim_save_frame" not in apply and "s_widgets" not in apply and "s_scene" not in apply
    assert apply.index("sim_display_status =") < apply.index("repaint->topic =")


def test_default_and_app_apply_hot_status_before_real_ui_delivery_and_ticks(source):
    receive = section(source, "int xQueueReceive(", "#endif")
    assert "if (step->display_change) sim_apply_display(step, out);" in receive
    assert "return pdTRUE;" in receive
    main = source.split("int main(int argc, char **argv)", 1)[1]
    dispatch = section(main, "const SimStep *step = &steps[i];", "#else")
    display = section(dispatch, "if (step->display_change) {", "} else if")
    operations = [
        "sim_apply_display(step, &repaint);",
        "bus_publish(&repaint);",
        "sim_scheduler_drain();",
        "sim_advance_ticks(step->advance_ticks, &tick);",
    ]
    positions = [display.index(operation) for operation in operations]
    assert positions == sorted(positions)
    assert "TOP_INPUT_BTN" not in display and "btn" not in display
    assert r"\"display_status\":%d" in main and "sim_display_status);" in main


def test_live_driver_status_gates_pixel_writes_and_keeps_last_accepted_frame():
    driver = (PRODUCT_ROOT / "tools/native_simulator/driver.c").read_text(encoding="utf-8")
    assert "int sim_display_status;" in driver
    assert "ssd1363_init_panel(void) { return sim_display_status; }" in driver
    begin = section(driver, "esp_err_t ssd1363_begin_frame(", "esp_err_t ssd1363_write_data(")
    assert "return sim_display_status;" in begin
    write = section(driver, "esp_err_t ssd1363_write_data(", "int sim_save_frame(")
    assert "if (sim_display_status) return sim_display_status;" in write
    assert write.index("if (sim_display_status)") < write.index("pixels[")
    assert "memset(pixels" not in driver  # hot state changes cannot replace captured pixels


def test_existing_production_rpc_path_forces_full_repaint_without_scene_reset():
    # Read-only .c evidence, after root/src AGENTS inspection; never read headers.
    ui = (PRODUCT_ROOT / "src/services/ui/ui.c").read_text(encoding="utf-8")
    rpc = section(ui, "static bool ui_handle_rpc_call(", "static void ui_task(")
    assert 'strcmp(m->u.rpc.method, "set_bg") == 0' in rpc
    assert "store_set_bg_rgb(rgb)" in rpc
    assert "s_bg_level = ui_bg_rgb_to_gray4(rgb);" in rpc and "return true;" in rpc
    assert "ui_scene_clone" not in rpc and "ui_nav_first_focus" not in rpc
    repaint = section(
        ui, "if (got && m.topic == TOP_RPC_CALL)", "if (got && m.topic == TOP_UI_CMD)"
    )
    assert "if (ui_handle_rpc_call(&m))" in repaint and "ui_dirty_full(&dirty);" in repaint
    assert "ui_render_scene(scene, &ops);" in ui and "ui_swbuf_flush_dirty_auto_ssd1363(&sw);" in ui
