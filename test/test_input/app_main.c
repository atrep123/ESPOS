/* Unity test runner for test_input */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* Debounce tests */
extern void test_debounce_no_change_returns_0(void);
extern void test_debounce_single_sample_below_threshold(void);
extern void test_debounce_reaches_threshold_returns_1(void);
extern void test_debounce_resets_count_on_revert(void);
extern void test_debounce_threshold_1_immediate(void);
extern void test_debounce_threshold_3(void);
extern void test_debounce_second_change_after_stable(void);
extern void test_debounce_null_state_returns_0(void);
extern void test_debounce_threshold_0_returns_0(void);
extern void test_debounce_negative_threshold_returns_0(void);

/* Encoder tests */
extern void test_encoder_no_movement_returns_0(void);
extern void test_encoder_cw_full_detent(void);
extern void test_encoder_ccw_full_detent(void);
extern void test_encoder_partial_step_no_detent(void);
extern void test_encoder_two_cw_detents(void);
extern void test_encoder_direction_reversal_resets(void);
extern void test_encoder_null_prev_ab_returns_0(void);
extern void test_encoder_null_accum_returns_0(void);
extern void test_encoder_glitch_no_movement(void);

/* Axis tests */
extern void test_axis_center_no_change(void);
extern void test_axis_push_negative(void);
extern void test_axis_push_positive(void);
extern void test_axis_hysteresis_holds_negative(void);
extern void test_axis_hysteresis_releases_negative(void);
extern void test_axis_hysteresis_holds_positive(void);
extern void test_axis_hysteresis_releases_positive(void);
extern void test_axis_null_state_returns_0(void);
extern void test_debounce_long_sequence_transitions(void);
extern void test_encoder_all_16_transitions(void);
extern void test_axis_deadzone_exact_boundary(void);
extern void test_debounce_threshold_boundary_exact(void);
extern void test_encoder_multi_detent_sequence(void);

int main(void)
{
    UNITY_BEGIN();

    /* Debounce */
    RUN_TEST(test_debounce_no_change_returns_0);
    RUN_TEST(test_debounce_single_sample_below_threshold);
    RUN_TEST(test_debounce_reaches_threshold_returns_1);
    RUN_TEST(test_debounce_resets_count_on_revert);
    RUN_TEST(test_debounce_threshold_1_immediate);
    RUN_TEST(test_debounce_threshold_3);
    RUN_TEST(test_debounce_second_change_after_stable);
    RUN_TEST(test_debounce_null_state_returns_0);
    RUN_TEST(test_debounce_threshold_0_returns_0);
    RUN_TEST(test_debounce_negative_threshold_returns_0);

    /* Encoder */
    RUN_TEST(test_encoder_no_movement_returns_0);
    RUN_TEST(test_encoder_cw_full_detent);
    RUN_TEST(test_encoder_ccw_full_detent);
    RUN_TEST(test_encoder_partial_step_no_detent);
    RUN_TEST(test_encoder_two_cw_detents);
    RUN_TEST(test_encoder_direction_reversal_resets);
    RUN_TEST(test_encoder_null_prev_ab_returns_0);
    RUN_TEST(test_encoder_null_accum_returns_0);
    RUN_TEST(test_encoder_glitch_no_movement);

    /* Axis */
    RUN_TEST(test_axis_center_no_change);
    RUN_TEST(test_axis_push_negative);
    RUN_TEST(test_axis_push_positive);
    RUN_TEST(test_axis_hysteresis_holds_negative);
    RUN_TEST(test_axis_hysteresis_releases_negative);
    RUN_TEST(test_axis_hysteresis_holds_positive);
    RUN_TEST(test_axis_hysteresis_releases_positive);
    RUN_TEST(test_axis_null_state_returns_0);

    /* new edge-case tests */
    RUN_TEST(test_debounce_long_sequence_transitions);
    RUN_TEST(test_encoder_all_16_transitions);
    RUN_TEST(test_axis_deadzone_exact_boundary);
    RUN_TEST(test_debounce_threshold_boundary_exact);
    RUN_TEST(test_encoder_multi_detent_sequence);

    return UNITY_END();
}
