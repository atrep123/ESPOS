#include "unity.h"

#include "display_config.h"

#ifdef ESP_PLATFORM

void test_swbuf_clear_marks_full_dirty(void);
void test_swbuf_mark_dirty_merges_regions(void);

void app_main(void)
{
    UNITY_BEGIN();
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
#if DISPLAY_COLOR_BITS == 4
void test_swbuf_flush_dirty_gray4_aligns_x_to_columns(void);
void test_swbuf_blit_mono_gray4_sets_pixels(void);
#endif

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_swbuf_clear_marks_full_dirty);
    RUN_TEST(test_swbuf_mark_dirty_merges_regions);
    RUN_TEST(test_render_label_overflow_ellipsis_truncates);
    RUN_TEST(test_render_label_overflow_clip_truncates_without_ellipsis);
    RUN_TEST(test_render_label_overflow_wrap_wraps_and_ellipsizes_last_line);
    RUN_TEST(test_render_checkbox_overflow_clip_truncates_without_ellipsis);
#if DISPLAY_COLOR_BITS == 4
    RUN_TEST(test_swbuf_flush_dirty_gray4_aligns_x_to_columns);
    RUN_TEST(test_swbuf_blit_mono_gray4_sets_pixels);
#endif
    return UNITY_END();
}

#endif
