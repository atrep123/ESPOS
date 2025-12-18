#include "unity.h"

#include "services/ui/ui_meta.h"

void setUp(void) {}
void tearDown(void) {}

void test_ui_meta_parse_int(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=contrast;kind=int;min=0;max=255;step=8", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_INT, (int)m.kind);
    TEST_ASSERT_EQUAL_STRING("contrast", m.bind_key);
    TEST_ASSERT_TRUE(m.has_min);
    TEST_ASSERT_TRUE(m.has_max);
    TEST_ASSERT_TRUE(m.has_step);
    TEST_ASSERT_EQUAL_INT(0, m.min);
    TEST_ASSERT_EQUAL_INT(255, m.max);
    TEST_ASSERT_EQUAL_INT(8, m.step);
}

void test_ui_meta_parse_bool(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=invert;kind=bool;values=off|on", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_BOOL, (int)m.kind);
    TEST_ASSERT_EQUAL_STRING("invert", m.bind_key);
    TEST_ASSERT_EQUAL_INT(2, ui_meta_values_count(m.values));

    char v0[16];
    char v1[16];
    TEST_ASSERT_TRUE(ui_meta_values_get(m.values, 0, v0, sizeof(v0)));
    TEST_ASSERT_TRUE(ui_meta_values_get(m.values, 1, v1, sizeof(v1)));
    TEST_ASSERT_EQUAL_STRING("off", v0);
    TEST_ASSERT_EQUAL_STRING("on", v1);
}

void test_ui_meta_values_helpers(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=mode;values=A|B|C", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_ENUM, (int)m.kind);
    TEST_ASSERT_EQUAL_INT(3, ui_meta_values_count(m.values));

    char out[8];
    TEST_ASSERT_TRUE(ui_meta_values_get(m.values, 2, out, sizeof(out)));
    TEST_ASSERT_EQUAL_STRING("C", out);
    TEST_ASSERT_FALSE(ui_meta_values_get(m.values, 3, out, sizeof(out)));
}

