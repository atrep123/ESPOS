/* Unity test runner for test_ui_scene_util */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* widget_rect */
extern void test_widget_rect_basic(void);
extern void test_widget_rect_null_scene(void);
extern void test_widget_rect_oob_negative(void);
extern void test_widget_rect_oob_too_large(void);
extern void test_widget_rect_partial_null_out(void);

/* find_by_id */
extern void test_find_by_id_found(void);
extern void test_find_by_id_not_found(void);
extern void test_find_by_id_null_scene(void);
extern void test_find_by_id_null_id(void);
extern void test_find_by_id_empty_id(void);
extern void test_find_by_id_widget_null_id_skipped(void);
extern void test_find_by_id_first_duplicate(void);

/* count_item_slots */
extern void test_count_items_three(void);
extern void test_count_items_zero(void);
extern void test_count_items_gap_stops(void);
extern void test_count_items_null_scene(void);
extern void test_count_items_null_root(void);
extern void test_count_items_empty_root(void);

/* modal_find_rect */
extern void test_modal_find_dialog(void);
extern void test_modal_find_panel_fallback(void);
extern void test_modal_find_prefers_dialog(void);
extern void test_modal_find_not_found(void);
extern void test_modal_find_zero_size_returns_zero(void);
extern void test_modal_find_null_scene(void);
extern void test_modal_find_null_root(void);
extern void test_modal_find_partial_null_out(void);

/* scene_clone */
extern void test_clone_basic(void);
extern void test_clone_truncates_to_max(void);
extern void test_clone_preserves_width_height(void);
extern void test_clone_null_src_returns_zero(void);
extern void test_clone_null_dst_returns_zero(void);
extern void test_clone_null_dst_widgets_returns_zero(void);
extern void test_clone_src_null_widgets_returns_zero(void);
extern void test_clone_exact_fit(void);
extern void test_clone_zero_max_widgets(void);
extern void test_clone_dst_points_to_buffer(void);

/* round-8 additions */
extern void test_find_by_id_single_widget_match(void);
extern void test_count_item_slots_many_sequential(void);
extern void test_clone_preserves_widget_type_and_visible(void);
extern void test_modal_find_zero_height_only(void);
extern void test_widget_rect_last_valid_index(void);

/* edge-case additions */
extern void test_widget_rect_uint16_max_coords(void);
extern void test_clone_empty_scene(void);
extern void test_find_by_id_empty_scene(void);

int main(void)
{
    UNITY_BEGIN();

    /* widget_rect */
    RUN_TEST(test_widget_rect_basic);
    RUN_TEST(test_widget_rect_null_scene);
    RUN_TEST(test_widget_rect_oob_negative);
    RUN_TEST(test_widget_rect_oob_too_large);
    RUN_TEST(test_widget_rect_partial_null_out);

    /* find_by_id */
    RUN_TEST(test_find_by_id_found);
    RUN_TEST(test_find_by_id_not_found);
    RUN_TEST(test_find_by_id_null_scene);
    RUN_TEST(test_find_by_id_null_id);
    RUN_TEST(test_find_by_id_empty_id);
    RUN_TEST(test_find_by_id_widget_null_id_skipped);
    RUN_TEST(test_find_by_id_first_duplicate);

    /* count_item_slots */
    RUN_TEST(test_count_items_three);
    RUN_TEST(test_count_items_zero);
    RUN_TEST(test_count_items_gap_stops);
    RUN_TEST(test_count_items_null_scene);
    RUN_TEST(test_count_items_null_root);
    RUN_TEST(test_count_items_empty_root);

    /* modal_find_rect */
    RUN_TEST(test_modal_find_dialog);
    RUN_TEST(test_modal_find_panel_fallback);
    RUN_TEST(test_modal_find_prefers_dialog);
    RUN_TEST(test_modal_find_not_found);
    RUN_TEST(test_modal_find_zero_size_returns_zero);
    RUN_TEST(test_modal_find_null_scene);
    RUN_TEST(test_modal_find_null_root);
    RUN_TEST(test_modal_find_partial_null_out);

    /* scene_clone */
    RUN_TEST(test_clone_basic);
    RUN_TEST(test_clone_truncates_to_max);
    RUN_TEST(test_clone_preserves_width_height);
    RUN_TEST(test_clone_null_src_returns_zero);
    RUN_TEST(test_clone_null_dst_returns_zero);
    RUN_TEST(test_clone_null_dst_widgets_returns_zero);
    RUN_TEST(test_clone_src_null_widgets_returns_zero);
    RUN_TEST(test_clone_exact_fit);
    RUN_TEST(test_clone_zero_max_widgets);
    RUN_TEST(test_clone_dst_points_to_buffer);

    /* round-8 additions */
    RUN_TEST(test_find_by_id_single_widget_match);
    RUN_TEST(test_count_item_slots_many_sequential);
    RUN_TEST(test_clone_preserves_widget_type_and_visible);
    RUN_TEST(test_modal_find_zero_height_only);
    RUN_TEST(test_widget_rect_last_valid_index);

    /* edge-case additions */
    RUN_TEST(test_widget_rect_uint16_max_coords);
    RUN_TEST(test_clone_empty_scene);
    RUN_TEST(test_find_by_id_empty_scene);

    return UNITY_END();
}
