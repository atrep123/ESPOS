/* Unity test runner for test_ui_render_widgets */
#include "unity.h"

extern void setUp(void);
extern void tearDown(void);

/* Label */
extern void test_label_no_border_no_text(void);
extern void test_label_with_border(void);
extern void test_label_with_text(void);
extern void test_label_text_needs_min_height(void);

/* Button */
extern void test_button_always_fills(void);
extern void test_button_with_border(void);
extern void test_button_with_text(void);

/* Panel */
extern void test_panel_fills_background(void);
extern void test_panel_with_border_and_text(void);

/* Box */
extern void test_box_delegates_to_panel(void);

/* Textbox */
extern void test_textbox_underline(void);
extern void test_textbox_fills_and_draws_text(void);

/* Progressbar */
extern void test_progressbar_zero_value(void);
extern void test_progressbar_full_value(void);
extern void test_progressbar_half_value(void);
extern void test_progressbar_with_text(void);
extern void test_progressbar_clamped_over_max(void);
extern void test_progressbar_tiny_widget(void);

/* Checkbox */
extern void test_checkbox_unchecked(void);
extern void test_checkbox_checked_draws_checkmark(void);
extern void test_checkbox_too_small(void);
extern void test_checkbox_with_text(void);

/* Radiobutton */
extern void test_radiobutton_unchecked(void);
extern void test_radiobutton_checked_draws_fill(void);
extern void test_radiobutton_too_small(void);
extern void test_radiobutton_with_text(void);

/* Slider */
extern void test_slider_draws_track_and_knob(void);
extern void test_slider_min_value(void);
extern void test_slider_max_value(void);
extern void test_slider_grip_line(void);
extern void test_slider_narrow_no_crash(void);

/* Gauge */
extern void test_gauge_large_draws_arc(void);
extern void test_gauge_small_fallback_bar(void);
extern void test_gauge_zero_value(void);
extern void test_gauge_with_label(void);
extern void test_gauge_tiny_widget(void);

/* Icon */
extern void test_icon_text_fallback(void);
extern void test_icon_null_text_shows_question(void);
extern void test_icon_empty_text_shows_question(void);
extern void test_icon_with_border(void);
extern void test_icon_too_short_for_text(void);

/* Chart */
extern void test_chart_draws_axes(void);
extern void test_chart_too_small(void);
extern void test_chart_with_text(void);
extern void test_chart_with_border(void);

/* Cross-cutting */
extern void test_border_style_single_fallback(void);
extern void test_border_style_double(void);
extern void test_custom_fg_bg(void);
extern void test_label_null_draw_text(void);

/* round-8 additions */
extern void test_slider_tiny_height(void);
extern void test_panel_no_border_no_text(void);
extern void test_button_text_needs_min_height(void);
extern void test_progressbar_under_min_value(void);
extern void test_chart_equal_min_max(void);
extern void test_gauge_null_fill_rect_no_crash(void);

/* min-size / zero-size widget tests */
extern void test_label_zero_size(void);
extern void test_label_1x1(void);
extern void test_button_zero_size(void);
extern void test_button_1x1(void);
extern void test_slider_zero_size(void);
extern void test_gauge_zero_size(void);
extern void test_chart_zero_size(void);
extern void test_panel_zero_size(void);
extern void test_textbox_zero_size(void);

/* List */
extern void test_list_basic_items(void);
extern void test_list_highlight_active(void);
extern void test_list_no_text(void);
extern void test_list_with_border(void);
extern void test_list_zero_size(void);

/* Toggle */
extern void test_toggle_unchecked_draws_track(void);
extern void test_toggle_checked_draws_track(void);
extern void test_toggle_with_text(void);
extern void test_toggle_no_text(void);
extern void test_toggle_zero_size(void);
extern void test_toggle_tiny_height(void);

int main(void)
{
    UNITY_BEGIN();

    /* Label */
    RUN_TEST(test_label_no_border_no_text);
    RUN_TEST(test_label_with_border);
    RUN_TEST(test_label_with_text);
    RUN_TEST(test_label_text_needs_min_height);

    /* Button */
    RUN_TEST(test_button_always_fills);
    RUN_TEST(test_button_with_border);
    RUN_TEST(test_button_with_text);

    /* Panel */
    RUN_TEST(test_panel_fills_background);
    RUN_TEST(test_panel_with_border_and_text);

    /* Box */
    RUN_TEST(test_box_delegates_to_panel);

    /* Textbox */
    RUN_TEST(test_textbox_underline);
    RUN_TEST(test_textbox_fills_and_draws_text);

    /* Progressbar */
    RUN_TEST(test_progressbar_zero_value);
    RUN_TEST(test_progressbar_full_value);
    RUN_TEST(test_progressbar_half_value);
    RUN_TEST(test_progressbar_with_text);
    RUN_TEST(test_progressbar_clamped_over_max);
    RUN_TEST(test_progressbar_tiny_widget);

    /* Checkbox */
    RUN_TEST(test_checkbox_unchecked);
    RUN_TEST(test_checkbox_checked_draws_checkmark);
    RUN_TEST(test_checkbox_too_small);
    RUN_TEST(test_checkbox_with_text);

    /* Radiobutton */
    RUN_TEST(test_radiobutton_unchecked);
    RUN_TEST(test_radiobutton_checked_draws_fill);
    RUN_TEST(test_radiobutton_too_small);
    RUN_TEST(test_radiobutton_with_text);

    /* Slider */
    RUN_TEST(test_slider_draws_track_and_knob);
    RUN_TEST(test_slider_min_value);
    RUN_TEST(test_slider_max_value);
    RUN_TEST(test_slider_grip_line);
    RUN_TEST(test_slider_narrow_no_crash);

    /* Gauge */
    RUN_TEST(test_gauge_large_draws_arc);
    RUN_TEST(test_gauge_small_fallback_bar);
    RUN_TEST(test_gauge_zero_value);
    RUN_TEST(test_gauge_with_label);
    RUN_TEST(test_gauge_tiny_widget);

    /* Icon */
    RUN_TEST(test_icon_text_fallback);
    RUN_TEST(test_icon_null_text_shows_question);
    RUN_TEST(test_icon_empty_text_shows_question);
    RUN_TEST(test_icon_with_border);
    RUN_TEST(test_icon_too_short_for_text);

    /* Chart */
    RUN_TEST(test_chart_draws_axes);
    RUN_TEST(test_chart_too_small);
    RUN_TEST(test_chart_with_text);
    RUN_TEST(test_chart_with_border);

    /* Cross-cutting */
    RUN_TEST(test_border_style_single_fallback);
    RUN_TEST(test_border_style_double);
    RUN_TEST(test_custom_fg_bg);
    RUN_TEST(test_label_null_draw_text);

    /* round-8 additions */
    RUN_TEST(test_slider_tiny_height);
    RUN_TEST(test_panel_no_border_no_text);
    RUN_TEST(test_button_text_needs_min_height);
    RUN_TEST(test_progressbar_under_min_value);
    RUN_TEST(test_chart_equal_min_max);
    RUN_TEST(test_gauge_null_fill_rect_no_crash);

    /* Min-size / zero-size */
    RUN_TEST(test_label_zero_size);
    RUN_TEST(test_label_1x1);
    RUN_TEST(test_button_zero_size);
    RUN_TEST(test_button_1x1);
    RUN_TEST(test_slider_zero_size);
    RUN_TEST(test_gauge_zero_size);
    RUN_TEST(test_chart_zero_size);
    RUN_TEST(test_panel_zero_size);
    RUN_TEST(test_textbox_zero_size);

    /* List */
    RUN_TEST(test_list_basic_items);
    RUN_TEST(test_list_highlight_active);
    RUN_TEST(test_list_no_text);
    RUN_TEST(test_list_with_border);
    RUN_TEST(test_list_zero_size);

    /* Toggle */
    RUN_TEST(test_toggle_unchecked_draws_track);
    RUN_TEST(test_toggle_checked_draws_track);
    RUN_TEST(test_toggle_with_text);
    RUN_TEST(test_toggle_no_text);
    RUN_TEST(test_toggle_zero_size);
    RUN_TEST(test_toggle_tiny_height);

    return UNITY_END();
}
