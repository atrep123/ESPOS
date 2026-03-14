/*
 * Unit tests for extracted input service functions:
 * - input_debounce_update(): sample-counting debounce state machine
 * - input_encoder_step(): quadrature encoder Gray-code transition table
 * - input_axis_update(): joystick axis with deadzone and hysteresis
 *
 * All functions are pure (no FreeRTOS, GPIO, or msgbus dependencies).
 */

#include "unity.h"
#include "services/input/input.h"

void setUp(void) {}
void tearDown(void) {}

/* ================================================================== */
/* input_debounce_update                                               */
/* ================================================================== */

void test_debounce_no_change_returns_0(void)
{
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    int r = input_debounce_update(&st, 1, 2);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(0, st.cnt);
}

void test_debounce_single_sample_below_threshold(void)
{
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    /* One differing sample — not enough for threshold=2. */
    int r = input_debounce_update(&st, 0, 2);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(1, st.cnt);
    TEST_ASSERT_EQUAL(1, st.stable); /* unchanged */
}

void test_debounce_reaches_threshold_returns_1(void)
{
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    int r1 = input_debounce_update(&st, 0, 2);
    TEST_ASSERT_EQUAL(0, r1); /* cnt=1, not yet */
    int r2 = input_debounce_update(&st, 0, 2);
    TEST_ASSERT_EQUAL(1, r2); /* cnt reached threshold */
    TEST_ASSERT_EQUAL(0, st.stable);
    TEST_ASSERT_EQUAL(0, st.last);
    TEST_ASSERT_EQUAL(0, st.cnt); /* reset after transition */
}

void test_debounce_resets_count_on_revert(void)
{
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    input_debounce_update(&st, 0, 3); /* cnt=1 */
    input_debounce_update(&st, 0, 3); /* cnt=2 */
    /* Revert to stable level — count resets. */
    input_debounce_update(&st, 1, 3);
    TEST_ASSERT_EQUAL(0, st.cnt);
    TEST_ASSERT_EQUAL(1, st.stable); /* unchanged */
}

void test_debounce_threshold_1_immediate(void)
{
    input_btn_state_t st = { .stable = 0, .last = 0, .cnt = 0 };
    int r = input_debounce_update(&st, 1, 1);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(1, st.stable);
}

void test_debounce_threshold_3(void)
{
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    TEST_ASSERT_EQUAL(0, input_debounce_update(&st, 0, 3)); /* cnt=1 */
    TEST_ASSERT_EQUAL(0, input_debounce_update(&st, 0, 3)); /* cnt=2 */
    TEST_ASSERT_EQUAL(1, input_debounce_update(&st, 0, 3)); /* cnt=3 → change */
    TEST_ASSERT_EQUAL(0, st.stable);
}

void test_debounce_second_change_after_stable(void)
{
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    /* Transition 1→0 */
    input_debounce_update(&st, 0, 2);
    input_debounce_update(&st, 0, 2);
    TEST_ASSERT_EQUAL(0, st.stable);
    /* Stay at 0 */
    TEST_ASSERT_EQUAL(0, input_debounce_update(&st, 0, 2));
    /* Transition 0→1 */
    TEST_ASSERT_EQUAL(0, input_debounce_update(&st, 1, 2));
    TEST_ASSERT_EQUAL(1, input_debounce_update(&st, 1, 2));
    TEST_ASSERT_EQUAL(1, st.stable);
}

void test_debounce_null_state_returns_0(void)
{
    TEST_ASSERT_EQUAL(0, input_debounce_update(NULL, 1, 2));
}

void test_debounce_threshold_0_returns_0(void)
{
    input_btn_state_t st = { .stable = 0, .last = 0, .cnt = 0 };
    TEST_ASSERT_EQUAL(0, input_debounce_update(&st, 1, 0));
}

void test_debounce_negative_threshold_returns_0(void)
{
    input_btn_state_t st = { .stable = 0, .last = 0, .cnt = 0 };
    TEST_ASSERT_EQUAL(0, input_debounce_update(&st, 1, -1));
}

/* ================================================================== */
/* input_encoder_step                                                  */
/* ================================================================== */

/* Gray-code CW sequence: 00→10→11→01→00 (4 transitions = 1 detent, accumulator +4) */
static void feed_cw(uint8_t *ab, int *accum, int *last_result)
{
    /* 00 → 10 */
    *last_result = input_encoder_step(ab, accum, 1, 0);
    if (*last_result) return;
    /* 10 → 11 */
    *last_result = input_encoder_step(ab, accum, 1, 1);
    if (*last_result) return;
    /* 11 → 01 */
    *last_result = input_encoder_step(ab, accum, 0, 1);
    if (*last_result) return;
    /* 01 → 00 */
    *last_result = input_encoder_step(ab, accum, 0, 0);
}

/* Gray-code CCW sequence: 00→01→11→10→00 (reverse of CW, accumulator -4) */
static void feed_ccw(uint8_t *ab, int *accum, int *last_result)
{
    /* 00 → 01 */
    *last_result = input_encoder_step(ab, accum, 0, 1);
    if (*last_result) return;
    /* 01 → 11 */
    *last_result = input_encoder_step(ab, accum, 1, 1);
    if (*last_result) return;
    /* 11 → 10 */
    *last_result = input_encoder_step(ab, accum, 1, 0);
    if (*last_result) return;
    /* 10 → 00 */
    *last_result = input_encoder_step(ab, accum, 0, 0);
}

void test_encoder_no_movement_returns_0(void)
{
    uint8_t ab = 0;
    int accum = 0;
    /* Same state → no movement */
    TEST_ASSERT_EQUAL(0, input_encoder_step(&ab, &accum, 0, 0));
    TEST_ASSERT_EQUAL(0, accum);
}

void test_encoder_cw_full_detent(void)
{
    uint8_t ab = 0;
    int accum = 0;
    int r = 0;
    feed_cw(&ab, &accum, &r);
    TEST_ASSERT_EQUAL(1, r);   /* CW detent */
    TEST_ASSERT_EQUAL(0, accum); /* reset after detent */
}

void test_encoder_ccw_full_detent(void)
{
    uint8_t ab = 0;
    int accum = 0;
    int r = 0;
    feed_ccw(&ab, &accum, &r);
    TEST_ASSERT_EQUAL(-1, r);  /* CCW detent */
    TEST_ASSERT_EQUAL(0, accum);
}

void test_encoder_partial_step_no_detent(void)
{
    uint8_t ab = 0;
    int accum = 0;
    /* Only 2 of 4 CW transitions */
    TEST_ASSERT_EQUAL(0, input_encoder_step(&ab, &accum, 0, 1));
    TEST_ASSERT_EQUAL(0, input_encoder_step(&ab, &accum, 1, 1));
    /* No detent yet, accumulator should be non-zero */
    TEST_ASSERT_NOT_EQUAL(0, accum);
}

void test_encoder_two_cw_detents(void)
{
    uint8_t ab = 0;
    int accum = 0;
    int r = 0;

    feed_cw(&ab, &accum, &r);
    TEST_ASSERT_EQUAL(1, r);

    feed_cw(&ab, &accum, &r);
    TEST_ASSERT_EQUAL(1, r);
}

void test_encoder_direction_reversal_resets(void)
{
    uint8_t ab = 0;
    int accum = 0;

    /* 2 CW steps: 00→10→11 */
    input_encoder_step(&ab, &accum, 1, 0);
    input_encoder_step(&ab, &accum, 1, 1);
    TEST_ASSERT_TRUE(accum > 0);

    /* Reverse (CCW transitions): 11→10→00 */
    input_encoder_step(&ab, &accum, 1, 0);
    input_encoder_step(&ab, &accum, 0, 0);
    /* Accumulator should have decreased (moved toward zero or negative) */
    TEST_ASSERT_TRUE(accum <= 0);
}

void test_encoder_null_prev_ab_returns_0(void)
{
    int accum = 0;
    TEST_ASSERT_EQUAL(0, input_encoder_step(NULL, &accum, 1, 0));
}

void test_encoder_null_accum_returns_0(void)
{
    uint8_t ab = 0;
    TEST_ASSERT_EQUAL(0, input_encoder_step(&ab, NULL, 1, 0));
}

void test_encoder_glitch_no_movement(void)
{
    uint8_t ab = 0;
    int accum = 0;
    /* Same state repeatedly — no transitions */
    for (int i = 0; i < 10; ++i) {
        TEST_ASSERT_EQUAL(0, input_encoder_step(&ab, &accum, 0, 0));
    }
    TEST_ASSERT_EQUAL(0, accum);
}

/* ================================================================== */
/* input_axis_update                                                   */
/* ================================================================== */

/* Using center=512, deadzone=100, hyst=20 */
#define AX_C 512
#define AX_DZ 100
#define AX_H 20

void test_axis_center_no_change(void)
{
    int s = 0;
    int r = input_axis_update(AX_C, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(0, s);
}

void test_axis_push_negative(void)
{
    int s = 0;
    /* Push below center - deadzone */
    int r = input_axis_update(AX_C - AX_DZ - 1, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(-1, s);
}

void test_axis_push_positive(void)
{
    int s = 0;
    int r = input_axis_update(AX_C + AX_DZ + 1, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(1, s);
}

void test_axis_hysteresis_holds_negative(void)
{
    int s = -1;
    /* Slightly within hysteresis band — stays negative */
    int val = AX_C - AX_DZ + AX_H - 1; /* just below release point */
    int r = input_axis_update(val, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(-1, s);
}

void test_axis_hysteresis_releases_negative(void)
{
    int s = -1;
    /* At release point */
    int val = AX_C - AX_DZ + AX_H; /* exactly at release threshold */
    int r = input_axis_update(val, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(0, s);
}

void test_axis_hysteresis_holds_positive(void)
{
    int s = 1;
    int val = AX_C + AX_DZ - AX_H + 1; /* just above release point */
    int r = input_axis_update(val, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(1, s);
}

void test_axis_hysteresis_releases_positive(void)
{
    int s = 1;
    int val = AX_C + AX_DZ - AX_H; /* exactly at release threshold */
    int r = input_axis_update(val, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(0, s);
}

void test_axis_null_state_returns_0(void)
{
    TEST_ASSERT_EQUAL(0, input_axis_update(500, 512, 100, 20, NULL));
}

/* ================================================================== */
/* New edge-case tests                                                 */
/* ================================================================== */

void test_debounce_long_sequence_transitions(void)
{
    /* Feed many alternating transitions; each should trigger exactly once */
    input_btn_state_t st = { .stable = 1, .last = 1, .cnt = 0 };
    int transitions = 0;
    for (int cycle = 0; cycle < 10; ++cycle) {
        /* transition 1 -> 0 */
        for (int i = 0; i < 3; ++i) {
            transitions += input_debounce_update(&st, 0, 3);
        }
        /* transition 0 -> 1 */
        for (int i = 0; i < 3; ++i) {
            transitions += input_debounce_update(&st, 1, 3);
        }
    }
    /* 10 cycles × 2 transitions = 20 */
    TEST_ASSERT_EQUAL(20, transitions);
    TEST_ASSERT_EQUAL(1, st.stable);
}

void test_encoder_all_16_transitions(void)
{
    /* Verify every transition in the 4x4 lookup table */
    static const int8_t expected[16] = {
        0, -1, +1, 0,
        +1, 0, 0, -1,
        -1, 0, 0, +1,
        0, +1, -1, 0,
    };
    for (int prev = 0; prev < 4; ++prev) {
        for (int cur = 0; cur < 4; ++cur) {
            uint8_t pab = (uint8_t)prev;
            int accum = 0;
            int a = (cur >> 1) & 1;
            int b = cur & 1;
            int det = input_encoder_step(&pab, &accum, a, b);
            int8_t exp_step = expected[(prev << 2) | cur];
            if (exp_step == 0) {
                TEST_ASSERT_EQUAL(0, det);
                TEST_ASSERT_EQUAL(0, accum);
            } else {
                TEST_ASSERT_EQUAL(0, det); /* single step never reaches ±4 */
                TEST_ASSERT_EQUAL((int)exp_step, accum);
            }
            TEST_ASSERT_EQUAL_UINT8((uint8_t)cur, pab);
        }
    }
}

void test_axis_deadzone_exact_boundary(void)
{
    int s = 0;
    /* Exactly at deadzone boundary: center + deadzone */
    int r = input_axis_update(AX_C + AX_DZ, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(1, s);

    /* Reset and test negative side */
    s = 0;
    r = input_axis_update(AX_C - AX_DZ, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(1, r);
    TEST_ASSERT_EQUAL(-1, s);

    /* One unit inside deadzone: should NOT trigger */
    s = 0;
    r = input_axis_update(AX_C + AX_DZ - 1, AX_C, AX_DZ, AX_H, &s);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(0, s);
}

void test_debounce_threshold_boundary_exact(void)
{
    /* cnt reaches exactly threshold-1 then reverts */
    input_btn_state_t st = { .stable = 0, .last = 0, .cnt = 0 };
    /* Feed (threshold-1) differing samples */
    for (int i = 0; i < 4; ++i) {
        int r = input_debounce_update(&st, 1, 5);
        TEST_ASSERT_EQUAL(0, r);
    }
    TEST_ASSERT_EQUAL(4, st.cnt);
    /* Revert — counter resets */
    int r = input_debounce_update(&st, 0, 5);
    TEST_ASSERT_EQUAL(0, r);
    TEST_ASSERT_EQUAL(0, st.cnt);
    TEST_ASSERT_EQUAL(0, st.stable);
}

void test_encoder_multi_detent_sequence(void)
{
    /* Run 3 full CW detents and 2 full CCW detents, verify counts */
    uint8_t pab = 0;
    int accum = 0;
    int result = 0;
    int cw_count = 0, ccw_count = 0;
    /* 3 CW detents */
    for (int d = 0; d < 3; ++d) {
        feed_cw(&pab, &accum, &result);
        if (result > 0) cw_count++;
        else if (result < 0) ccw_count++;
    }
    TEST_ASSERT_EQUAL(3, cw_count);
    TEST_ASSERT_EQUAL(0, ccw_count);
    /* 2 CCW detents */
    for (int d = 0; d < 2; ++d) {
        feed_ccw(&pab, &accum, &result);
        if (result > 0) cw_count++;
        else if (result < 0) ccw_count++;
    }
    TEST_ASSERT_EQUAL(3, cw_count);
    TEST_ASSERT_EQUAL(2, ccw_count);
}
