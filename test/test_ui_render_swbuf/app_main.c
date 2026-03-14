#include "unity.h"

#include "display_config.h"

#ifdef ESP_PLATFORM

void test_swbuf_clear_marks_full_dirty(void);
void test_swbuf_mark_dirty_merges_regions(void);
void test_swbuf_init_null_buf_no_crash(void);
void test_swbuf_init_null_mem_no_crash(void);
void test_swbuf_clear_null_buf_no_crash(void);
void test_swbuf_clear_null_data_no_crash(void);

void app_main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_swbuf_init_null_buf_no_crash);
    RUN_TEST(test_swbuf_init_null_mem_no_crash);
    RUN_TEST(test_swbuf_clear_null_buf_no_crash);
    RUN_TEST(test_swbuf_clear_null_data_no_crash);
    RUN_TEST(test_swbuf_clear_marks_full_dirty);
    RUN_TEST(test_swbuf_mark_dirty_merges_regions);
    UNITY_END();
}

#else

void test_swbuf_clear_marks_full_dirty(void);
void test_swbuf_mark_dirty_merges_regions(void);
void test_render_label_overflow_ellipsis_truncates(void);
void test_render_label_overflow_clip_truncates_without_ellipsis(void);
void test_render_label_overflow_wrap_wraps_and_ellipsizes_last_line(void);
void test_render_checkbox_overflow_clip_truncates_without_ellipsis(void);
void test_swbuf_init_null_buf_no_crash(void);
void test_swbuf_init_null_mem_no_crash(void);
void test_swbuf_clear_null_buf_no_crash(void);
void test_swbuf_clear_null_data_no_crash(void);
#if DISPLAY_COLOR_BITS == 4
void test_swbuf_flush_dirty_gray4_aligns_x_to_columns(void);
void test_swbuf_flush_gray4_full_sends_all_rows(void);
void test_swbuf_flush_gray4_full_preserves_pixel_data(void);
void test_swbuf_flush_auto_delegates_to_gray4(void);
void test_swbuf_flush_dirty_auto_delegates_to_gray4(void);
void test_swbuf_flush_dirty_gray4_clean_falls_back_to_full(void);
void test_swbuf_flush_dirty_gray4_multi_row_region(void);
void test_swbuf_blit_mono_gray4_sets_pixels(void);
void test_swbuf_hline_sets_pixels_and_marks_dirty(void);
void test_swbuf_vline_sets_pixels_and_marks_dirty(void);
void test_swbuf_fill_rect_marks_dirty(void);
void test_swbuf_text_marks_dirty(void);
void test_swbuf_text_null_no_crash(void);
void test_swbuf_text_empty_no_dirty(void);
void test_swbuf_rect_marks_dirty(void);
void test_swbuf_make_ops_fills_all(void);
void test_swbuf_fill_rect_sets_pixels(void);
void test_swbuf_hline_clipping(void);
void test_swbuf_vline_clipping(void);
void test_swbuf_rect_draws_outline(void);
void test_swbuf_clear_sets_all_bytes(void);
void test_render_scene_draws_all_visible_widgets(void);
void test_render_scene_null_no_crash(void);
void test_render_widget_progressbar(void);
void test_render_widget_slider(void);
void test_render_widget_gauge(void);
void test_render_widget_radiobutton(void);
void test_render_widget_textbox(void);
void test_render_widget_chart(void);
void test_render_widget_unknown_type(void);
void test_render_widget_sentinel_type_rejected(void);
void test_render_label_center_align(void);
void test_render_label_text_overflow_auto_wraps(void);
void test_render_widget_disabled_style(void);
void test_render_widget_button(void);
void test_render_widget_button_no_border(void);
void test_render_widget_button_null_text(void);
void test_render_widget_panel(void);
void test_render_widget_panel_no_text(void);
void test_render_widget_box(void);
void test_render_widget_icon_no_crash(void);
void test_render_widget_icon_with_border(void);
void test_render_widget_invisible_skipped(void);
void test_render_widget_button_border_styles(void);
void test_swbuf_blit_mono_stride_too_small_rejected(void);
void test_render_chart_tiny_widget_no_crash(void);
void test_render_progressbar_large_range_no_overflow(void);
void test_render_gauge_large_range_no_overflow(void);
void test_swbuf_rect_zero_width_no_dirty(void);
void test_swbuf_rect_zero_height_no_dirty(void);
void test_swbuf_rect_negative_dims_no_dirty(void);
void test_render_checkbox_tiny_no_crash(void);
void test_render_radiobutton_tiny_no_crash(void);
void test_render_button_tiny_no_text(void);
void test_render_panel_tiny_no_text(void);
void test_render_textbox_tiny_no_text(void);
void test_render_slider_narrow_no_crash(void);
void test_render_chart_small_no_crash(void);
void test_render_icon_tiny_no_text(void);
void test_swbuf_flush_ssd1363_begin_frame_params(void);
void test_swbuf_flush_ssd1363_sends_correct_bytes(void);
void test_swbuf_flush_ssd1363_sends_buffer_content(void);
void test_swbuf_clear_with_midrange_color(void);
void test_swbuf_hline_zero_width_no_dirty(void);
void test_swbuf_fill_rect_fully_outside_no_dirty(void);
void test_swbuf_vline_zero_height_no_dirty(void);
void test_swbuf_blit_mono_fully_outside_no_dirty(void);
void test_swbuf_fill_rect_zero_size_no_crash(void);
void test_swbuf_fill_rect_negative_origin_clipped(void);
void test_render_scene_zero_widgets(void);
void test_swbuf_blit_mono_stride_too_large_rejected(void);
void test_render_all_types_null_text_no_crash(void);
void test_render_all_types_zero_dims_no_crash(void);
void test_render_degenerate_range_no_crash(void);
void test_render_value_overflow_no_crash(void);
#endif

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_swbuf_init_null_buf_no_crash);
    RUN_TEST(test_swbuf_init_null_mem_no_crash);
    RUN_TEST(test_swbuf_clear_null_buf_no_crash);
    RUN_TEST(test_swbuf_clear_null_data_no_crash);
    RUN_TEST(test_swbuf_clear_marks_full_dirty);
    RUN_TEST(test_swbuf_mark_dirty_merges_regions);
    RUN_TEST(test_render_label_overflow_ellipsis_truncates);
    RUN_TEST(test_render_label_overflow_clip_truncates_without_ellipsis);
    RUN_TEST(test_render_label_overflow_wrap_wraps_and_ellipsizes_last_line);
    RUN_TEST(test_render_checkbox_overflow_clip_truncates_without_ellipsis);
#if DISPLAY_COLOR_BITS == 4
    RUN_TEST(test_swbuf_flush_dirty_gray4_aligns_x_to_columns);
    RUN_TEST(test_swbuf_flush_gray4_full_sends_all_rows);
    RUN_TEST(test_swbuf_flush_gray4_full_preserves_pixel_data);
    RUN_TEST(test_swbuf_flush_auto_delegates_to_gray4);
    RUN_TEST(test_swbuf_flush_dirty_auto_delegates_to_gray4);
    RUN_TEST(test_swbuf_flush_dirty_gray4_clean_falls_back_to_full);
    RUN_TEST(test_swbuf_flush_dirty_gray4_multi_row_region);
    RUN_TEST(test_swbuf_blit_mono_gray4_sets_pixels);
    RUN_TEST(test_swbuf_hline_sets_pixels_and_marks_dirty);
    RUN_TEST(test_swbuf_vline_sets_pixels_and_marks_dirty);
    RUN_TEST(test_swbuf_fill_rect_marks_dirty);
    RUN_TEST(test_swbuf_text_marks_dirty);
    RUN_TEST(test_swbuf_text_null_no_crash);
    RUN_TEST(test_swbuf_text_empty_no_dirty);
    RUN_TEST(test_swbuf_rect_marks_dirty);
    RUN_TEST(test_swbuf_make_ops_fills_all);
    RUN_TEST(test_swbuf_fill_rect_sets_pixels);
    RUN_TEST(test_swbuf_hline_clipping);
    RUN_TEST(test_swbuf_vline_clipping);
    RUN_TEST(test_swbuf_rect_draws_outline);
    RUN_TEST(test_swbuf_clear_sets_all_bytes);
    RUN_TEST(test_render_scene_draws_all_visible_widgets);
    RUN_TEST(test_render_scene_null_no_crash);
    RUN_TEST(test_render_widget_progressbar);
    RUN_TEST(test_render_widget_slider);
    RUN_TEST(test_render_widget_gauge);
    RUN_TEST(test_render_widget_radiobutton);
    RUN_TEST(test_render_widget_textbox);
    RUN_TEST(test_render_widget_chart);
    RUN_TEST(test_render_widget_unknown_type);
    RUN_TEST(test_render_widget_sentinel_type_rejected);
    RUN_TEST(test_render_label_center_align);
    RUN_TEST(test_render_label_text_overflow_auto_wraps);
    RUN_TEST(test_render_widget_disabled_style);
    RUN_TEST(test_render_widget_button);
    RUN_TEST(test_render_widget_button_no_border);
    RUN_TEST(test_render_widget_button_null_text);
    RUN_TEST(test_render_widget_panel);
    RUN_TEST(test_render_widget_panel_no_text);
    RUN_TEST(test_render_widget_box);
    RUN_TEST(test_render_widget_icon_no_crash);
    RUN_TEST(test_render_widget_icon_with_border);
    RUN_TEST(test_render_widget_invisible_skipped);
    RUN_TEST(test_render_widget_button_border_styles);
    RUN_TEST(test_swbuf_blit_mono_stride_too_small_rejected);
    RUN_TEST(test_render_chart_tiny_widget_no_crash);
    RUN_TEST(test_render_progressbar_large_range_no_overflow);
    RUN_TEST(test_render_gauge_large_range_no_overflow);
    RUN_TEST(test_swbuf_rect_zero_width_no_dirty);
    RUN_TEST(test_swbuf_rect_zero_height_no_dirty);
    RUN_TEST(test_swbuf_rect_negative_dims_no_dirty);
    RUN_TEST(test_render_checkbox_tiny_no_crash);
    RUN_TEST(test_render_radiobutton_tiny_no_crash);
    RUN_TEST(test_render_button_tiny_no_text);
    RUN_TEST(test_render_panel_tiny_no_text);
    RUN_TEST(test_render_textbox_tiny_no_text);
    RUN_TEST(test_render_slider_narrow_no_crash);
    RUN_TEST(test_render_chart_small_no_crash);
    RUN_TEST(test_render_icon_tiny_no_text);
    RUN_TEST(test_swbuf_flush_ssd1363_begin_frame_params);
    RUN_TEST(test_swbuf_flush_ssd1363_sends_correct_bytes);
    RUN_TEST(test_swbuf_flush_ssd1363_sends_buffer_content);
    RUN_TEST(test_swbuf_clear_with_midrange_color);
    RUN_TEST(test_swbuf_hline_zero_width_no_dirty);
    RUN_TEST(test_swbuf_fill_rect_fully_outside_no_dirty);
    RUN_TEST(test_swbuf_vline_zero_height_no_dirty);
    RUN_TEST(test_swbuf_blit_mono_fully_outside_no_dirty);
    RUN_TEST(test_swbuf_fill_rect_zero_size_no_crash);
    RUN_TEST(test_swbuf_fill_rect_negative_origin_clipped);
    RUN_TEST(test_render_scene_zero_widgets);
    RUN_TEST(test_swbuf_blit_mono_stride_too_large_rejected);
    RUN_TEST(test_render_all_types_null_text_no_crash);
    RUN_TEST(test_render_all_types_zero_dims_no_crash);
    RUN_TEST(test_render_degenerate_range_no_crash);
    RUN_TEST(test_render_value_overflow_no_crash);
#endif
    return UNITY_END();
}

#endif
