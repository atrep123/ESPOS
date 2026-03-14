#pragma once

#include "kernel/msgbus.h"

/**
 * Parse a single RPC command line into a message.
 * Returns 1 on success, 0 if line is NULL.
 * On unknown/invalid commands, m->u.rpc.method is set to "noop".
 */
int rpc_parse_line(const char *line, msg_t *m);

esp_err_t rpc_start(void);
void rpc_stop(void);

