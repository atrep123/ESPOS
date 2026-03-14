#include "unity.h"

#ifdef ESP_PLATFORM

void test_ui_listmodel_scrolls_viewport(void);
void test_ui_listmodel_parse_item_text_splits_fields(void);
void test_ui_listmodel_manager_creates_and_reuses(void);
void test_ui_listmodel_set_len_negative(void);
void test_ui_listmodel_set_len_above_max(void);
void test_ui_listmodel_move_active_clamps_at_bounds(void);
void test_ui_listmodel_active_slot_basic(void);
void test_ui_listmodel_active_slot_null(void);
void test_ui_listmodel_max_models_exceeded(void);
void test_ui_listmodel_set_active_empty_list(void);
void test_ui_listmodel_move_on_empty_list(void);
void test_ui_listmodel_set_len_null(void);
void test_ui_listmodel_single_visible_slot(void);
void test_ui_listmodel_visible_slots_zero(void);
void test_ui_listmodel_parse_separator_only(void);
void test_ui_listmodel_parse_multiple_separators(void);
void test_ui_listmodel_parse_label_truncation(void);
void test_ui_listmodel_set_active_same_position(void);
void test_ui_listmodel_offset_stable(void);
void test_ui_listmodel_reinit_after_use(void);
void test_ui_listmodel_root_at_boundary(void);
void test_ui_listmodel_format_scroll_small_buffer(void);
void test_ui_listmodel_move_at_boundary_returns_false(void);
void test_ui_listmodel_set_item_max_index(void);
void test_ui_listmodel_root_truncation(void);
void test_ui_listmodel_parse_pipe_separator(void);
void test_ui_listmodel_set_active_beyond_count(void);
void test_ui_listmodel_format_scroll_single_item(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_listmodel_scrolls_viewport);
    RUN_TEST(test_ui_listmodel_parse_item_text_splits_fields);
    RUN_TEST(test_ui_listmodel_manager_creates_and_reuses);
    RUN_TEST(test_ui_listmodel_set_len_negative);
    RUN_TEST(test_ui_listmodel_set_len_above_max);
    RUN_TEST(test_ui_listmodel_move_active_clamps_at_bounds);
    RUN_TEST(test_ui_listmodel_active_slot_basic);
    RUN_TEST(test_ui_listmodel_active_slot_null);
    RUN_TEST(test_ui_listmodel_max_models_exceeded);
    RUN_TEST(test_ui_listmodel_set_active_empty_list);
    RUN_TEST(test_ui_listmodel_move_on_empty_list);
    RUN_TEST(test_ui_listmodel_set_len_null);
    RUN_TEST(test_ui_listmodel_single_visible_slot);
    RUN_TEST(test_ui_listmodel_visible_slots_zero);
    RUN_TEST(test_ui_listmodel_parse_separator_only);
    RUN_TEST(test_ui_listmodel_parse_multiple_separators);
    RUN_TEST(test_ui_listmodel_parse_label_truncation);
    RUN_TEST(test_ui_listmodel_set_active_same_position);
    RUN_TEST(test_ui_listmodel_offset_stable);
    RUN_TEST(test_ui_listmodel_reinit_after_use);
    RUN_TEST(test_ui_listmodel_root_at_boundary);
    RUN_TEST(test_ui_listmodel_format_scroll_small_buffer);
    RUN_TEST(test_ui_listmodel_move_at_boundary_returns_false);
    RUN_TEST(test_ui_listmodel_set_item_max_index);
    RUN_TEST(test_ui_listmodel_root_truncation);
    RUN_TEST(test_ui_listmodel_parse_pipe_separator);
    RUN_TEST(test_ui_listmodel_set_active_beyond_count);
    RUN_TEST(test_ui_listmodel_format_scroll_single_item);
    UNITY_END();
}

#else

void test_ui_listmodel_scrolls_viewport(void);
void test_ui_listmodel_parse_item_text_splits_fields(void);
void test_ui_listmodel_manager_creates_and_reuses(void);
void test_ui_listmodel_format_scroll_basic(void);
void test_ui_listmodel_format_scroll_null(void);
void test_ui_listmodel_set_item_stores_values(void);
void test_ui_listmodel_set_item_bounds(void);
void test_ui_listmodel_set_len_clamps_active(void);
void test_ui_listmodel_move_active_delta_zero_no_change(void);
void test_ui_listmodel_get_nonexistent_returns_null(void);
void test_ui_listmodel_parse_null_and_empty(void);
void test_ui_listmodel_set_len_negative(void);
void test_ui_listmodel_set_len_above_max(void);
void test_ui_listmodel_move_active_clamps_at_bounds(void);
void test_ui_listmodel_active_slot_basic(void);
void test_ui_listmodel_active_slot_null(void);
void test_ui_listmodel_max_models_exceeded(void);
void test_ui_listmodel_set_active_empty_list(void);
void test_ui_listmodel_move_on_empty_list(void);
void test_ui_listmodel_set_len_null(void);
void test_ui_listmodel_single_visible_slot(void);
void test_ui_listmodel_visible_slots_zero(void);
void test_ui_listmodel_parse_separator_only(void);
void test_ui_listmodel_parse_multiple_separators(void);
void test_ui_listmodel_parse_label_truncation(void);
void test_ui_listmodel_set_active_same_position(void);
void test_ui_listmodel_offset_stable(void);
void test_ui_listmodel_reinit_after_use(void);
void test_ui_listmodel_root_at_boundary(void);
void test_ui_listmodel_format_scroll_small_buffer(void);
void test_ui_listmodel_move_at_boundary_returns_false(void);
void test_ui_listmodel_set_item_max_index(void);
void test_ui_listmodel_root_truncation(void);
void test_ui_listmodel_parse_pipe_separator(void);
void test_ui_listmodel_set_active_beyond_count(void);
void test_ui_listmodel_format_scroll_single_item(void);
void test_ui_listmodel_single_item_boundary(void);
void test_ui_listmodel_max_capacity_boundary(void);

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_ui_listmodel_scrolls_viewport);
    RUN_TEST(test_ui_listmodel_parse_item_text_splits_fields);
    RUN_TEST(test_ui_listmodel_manager_creates_and_reuses);
    RUN_TEST(test_ui_listmodel_format_scroll_basic);
    RUN_TEST(test_ui_listmodel_format_scroll_null);
    RUN_TEST(test_ui_listmodel_set_item_stores_values);
    RUN_TEST(test_ui_listmodel_set_item_bounds);
    RUN_TEST(test_ui_listmodel_set_len_clamps_active);
    RUN_TEST(test_ui_listmodel_move_active_delta_zero_no_change);
    RUN_TEST(test_ui_listmodel_get_nonexistent_returns_null);
    RUN_TEST(test_ui_listmodel_parse_null_and_empty);
    RUN_TEST(test_ui_listmodel_set_len_negative);
    RUN_TEST(test_ui_listmodel_set_len_above_max);
    RUN_TEST(test_ui_listmodel_move_active_clamps_at_bounds);
    RUN_TEST(test_ui_listmodel_active_slot_basic);
    RUN_TEST(test_ui_listmodel_active_slot_null);
    RUN_TEST(test_ui_listmodel_max_models_exceeded);
    RUN_TEST(test_ui_listmodel_set_active_empty_list);
    RUN_TEST(test_ui_listmodel_move_on_empty_list);
    RUN_TEST(test_ui_listmodel_set_len_null);
    RUN_TEST(test_ui_listmodel_single_visible_slot);
    RUN_TEST(test_ui_listmodel_visible_slots_zero);
    RUN_TEST(test_ui_listmodel_parse_separator_only);
    RUN_TEST(test_ui_listmodel_parse_multiple_separators);
    RUN_TEST(test_ui_listmodel_parse_label_truncation);
    RUN_TEST(test_ui_listmodel_set_active_same_position);
    RUN_TEST(test_ui_listmodel_offset_stable);
    RUN_TEST(test_ui_listmodel_reinit_after_use);
    RUN_TEST(test_ui_listmodel_root_at_boundary);
    RUN_TEST(test_ui_listmodel_format_scroll_small_buffer);
    RUN_TEST(test_ui_listmodel_move_at_boundary_returns_false);
    RUN_TEST(test_ui_listmodel_set_item_max_index);
    RUN_TEST(test_ui_listmodel_root_truncation);
    RUN_TEST(test_ui_listmodel_parse_pipe_separator);
    RUN_TEST(test_ui_listmodel_set_active_beyond_count);
    RUN_TEST(test_ui_listmodel_format_scroll_single_item);
    RUN_TEST(test_ui_listmodel_single_item_boundary);
    RUN_TEST(test_ui_listmodel_max_capacity_boundary);
    return UNITY_END();
}

#endif

