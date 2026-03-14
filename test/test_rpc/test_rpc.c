/*
 * Unit tests for rpc_parse_line() — the RPC command parser.
 *
 * Tests cover: valid set_bg commands, hex edge cases, overflow,
 * unknown commands, null safety, and method field truncation.
 */

#include "unity.h"

#include <string.h>

#include "services/rpc/rpc.h"

void setUp(void) {}
void tearDown(void) {}

/* ======================== Valid set_bg ======================== */

void test_parse_set_bg_simple(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg FF8800", &m));
    TEST_ASSERT_EQUAL_INT(TOP_RPC_CALL, m.topic);
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0xFF8800, m.u.rpc.arg);
}

void test_parse_set_bg_lowercase(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg ff8800", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0xFF8800, m.u.rpc.arg);
}

void test_parse_set_bg_zero(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg 0", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0, m.u.rpc.arg);
}

void test_parse_set_bg_max_24bit(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg FFFFFF", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0xFFFFFF, m.u.rpc.arg);
}

void test_parse_set_bg_trailing_space(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg AA ", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0xAA, m.u.rpc.arg);
}

/* ======================== Invalid set_bg ======================== */

void test_parse_set_bg_overflow_rejects(void)
{
    msg_t m;
    /* Value > 0xFFFFFF should be rejected */
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg 1000000", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_huge_overflow(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg FFFFFFFF", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_no_value(void)
{
    msg_t m;
    /* "set_bg " with nothing after — strtoul returns 0 but end == line+7 */
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg ", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_garbage_value(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg xyz", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_trailing_junk(void)
{
    msg_t m;
    /* "set_bg AAjunk" — end points to 'j', not '\0' or ' ' */
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg AAjunk", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_negative(void)
{
    msg_t m;
    /* strtoul accepts negative but wraps; should fail 24-bit check */
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg -1", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

/* ======================== Unknown commands ======================== */

void test_parse_unknown_command(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("hello world", &m));
    TEST_ASSERT_EQUAL_INT(TOP_RPC_CALL, m.topic);
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_empty_line(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_no_space(void)
{
    msg_t m;
    /* "set_bgFF" is not "set_bg " prefix */
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bgFF", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

/* ======================== Null safety ======================== */

void test_parse_null_line(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(0, rpc_parse_line(NULL, &m));
}

void test_parse_null_msg(void)
{
    TEST_ASSERT_EQUAL_INT(0, rpc_parse_line("set_bg FF", NULL));
}

void test_parse_both_null(void)
{
    TEST_ASSERT_EQUAL_INT(0, rpc_parse_line(NULL, NULL));
}

/* ======================== Message struct ======================== */

void test_parse_zeroes_msg(void)
{
    msg_t m;
    memset(&m, 0xFF, sizeof(m));
    rpc_parse_line("set_bg 0", &m);
    /* arg should be 0, not leftover 0xFF */
    TEST_ASSERT_EQUAL_UINT32(0, m.u.rpc.arg);
}

/* ======================== Additional edge cases ======================== */

void test_parse_set_bg_leading_zeros(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg 00FF00", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0xFF00, m.u.rpc.arg);
}

void test_parse_set_bg_0x_prefix(void)
{
    /* strtoul(..., 16) accepts 0x prefix silently */
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg 0xFF0000", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0xFF0000, m.u.rpc.arg);
}

void test_parse_whitespace_only_line(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("   ", &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_very_long_line(void)
{
    /* 200+ char line doesn't cause buffer issues in rpc_parse_line */
    char buf[256];
    memset(buf, 'A', sizeof(buf) - 1);
    buf[255] = '\0';
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line(buf, &m));
    TEST_ASSERT_EQUAL_STRING("noop", m.u.rpc.method);
}

void test_parse_set_bg_single_digit(void)
{
    msg_t m;
    TEST_ASSERT_EQUAL_INT(1, rpc_parse_line("set_bg F", &m));
    TEST_ASSERT_EQUAL_STRING("set_bg", m.u.rpc.method);
    TEST_ASSERT_EQUAL_UINT32(0x0F, m.u.rpc.arg);
}
