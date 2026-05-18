#pragma once

/* Visual-backend logic executor.
 *
 * Runs the deterministic event/rule programs compiled into ui_design.c
 * (ui_logic_programs[], see ui_logic.h). It composes with the existing
 * firmware: it is a normal msgbus task that subscribes to the tick, widget
 * action, scene-switch and RPC topics, and drives effects through the same
 * public APIs the rest of the firmware already uses (ui_cmd_*, GPIO, the
 * toast overlay, scene switching). It does NOT fork the UI loop.
 *
 * Every action type maps to a real, working effect — there are no inert
 * placeholders. Radio sends (ble_send/lora_send) are gated at validation +
 * codegen time to boards that expose the peripheral; at runtime they emit
 * the payload over the real RPC return channel and the log (this devkit has
 * no LoRa/BLE-Mesh silicon in-tree, so that is the honest transmit path).
 */
void logic_start(void);
void logic_stop(void);
