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

void test_ui_meta_parse_str(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=model_name;kind=str", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_STR, (int)m.kind);
    TEST_ASSERT_EQUAL_STRING("model_name", m.bind_key);
}

void test_ui_meta_parse_float(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=batt_voltage;kind=float;min=3.0;max=4.2", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_FLOAT, (int)m.kind);
    TEST_ASSERT_EQUAL_STRING("batt_voltage", m.bind_key);
    /* min/max parsed as int (truncated) since parse_int_span uses strtol */
    TEST_ASSERT_TRUE(m.has_min);
    TEST_ASSERT_EQUAL_INT(3, m.min);
    TEST_ASSERT_TRUE(m.has_max);
    TEST_ASSERT_EQUAL_INT(4, m.max);
}

void test_ui_meta_parse_list(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=fs_mode;kind=list;values=Hold Last|Custom|No Pulse", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_ENUM, (int)m.kind);
    TEST_ASSERT_EQUAL_STRING("fs_mode", m.bind_key);
    TEST_ASSERT_EQUAL_INT(3, ui_meta_values_count(m.values));

    char out[16];
    TEST_ASSERT_TRUE(ui_meta_values_get(m.values, 0, out, sizeof(out)));
    TEST_ASSERT_EQUAL_STRING("Hold Last", out);
    TEST_ASSERT_TRUE(ui_meta_values_get(m.values, 2, out, sizeof(out)));
    TEST_ASSERT_EQUAL_STRING("No Pulse", out);
}

void test_ui_meta_parse_null_and_empty(void)
{
    ui_meta_t m;
    TEST_ASSERT_FALSE(ui_meta_parse(NULL, &m));
    TEST_ASSERT_FALSE(ui_meta_parse("", &m));
    TEST_ASSERT_FALSE(ui_meta_parse("kind=int", &m));  /* no bind key */
    TEST_ASSERT_FALSE(ui_meta_parse("noequals", &m));  /* no key=value */
}

void test_ui_meta_values_count_edge_cases(void)
{
    TEST_ASSERT_EQUAL_INT(0, ui_meta_values_count(NULL));
    TEST_ASSERT_EQUAL_INT(0, ui_meta_values_count(""));
    TEST_ASSERT_EQUAL_INT(1, ui_meta_values_count("single"));
    TEST_ASSERT_EQUAL_INT(2, ui_meta_values_count("A|B"));
}

void test_ui_meta_values_get_edge_cases(void)
{
    char out[16];
    TEST_ASSERT_FALSE(ui_meta_values_get(NULL, 0, out, sizeof(out)));
    TEST_ASSERT_FALSE(ui_meta_values_get("A|B", -1, out, sizeof(out)));
    TEST_ASSERT_FALSE(ui_meta_values_get("A|B", 2, out, sizeof(out)));
    /* NULL output buffer */
    TEST_ASSERT_FALSE(ui_meta_values_get("A", 0, NULL, 0));
}

void test_ui_meta_kind_aliases(void)
{
    ui_meta_t m;
    /* boolean alias */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=x;kind=boolean", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_BOOL, (int)m.kind);
    /* i32 alias */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=y;kind=i32", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_INT, (int)m.kind);
    /* choice alias → ENUM */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=z;kind=choice;values=A|B", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_ENUM, (int)m.kind);
    /* f32 alias → FLOAT */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=w;kind=f32", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_FLOAT, (int)m.kind);
    /* type= alias for kind= */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;type=string", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_STR, (int)m.kind);
}

void test_ui_meta_step_zero_defaults_to_one(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=val;kind=int;step=0", &m));
    TEST_ASSERT_TRUE(m.has_step);
    TEST_ASSERT_EQUAL_INT(1, m.step);
}

void test_ui_meta_key_alias(void)
{
    ui_meta_t m;
    /* key= is an alias for bind= */
    TEST_ASSERT_TRUE(ui_meta_parse("key=brightness;kind=int", &m));
    TEST_ASSERT_EQUAL_STRING("brightness", m.bind_key);
}

void test_ui_meta_parse_int_overflow_rejected(void)
{
    ui_meta_t m;
    /* Huge positive number exceeds LONG_MAX — should be rejected */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=x;kind=int;min=99999999999999999999", &m));
    TEST_ASSERT_FALSE(m.has_min);

    /* Huge negative number exceeds LONG_MIN — should be rejected */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=x;kind=int;max=-99999999999999999999", &m));
    TEST_ASSERT_FALSE(m.has_max);

    /* Normal values still work */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=x;kind=int;min=-1000;max=1000", &m));
    TEST_ASSERT_TRUE(m.has_min);
    TEST_ASSERT_TRUE(m.has_max);
    TEST_ASSERT_EQUAL_INT(-1000, m.min);
    TEST_ASSERT_EQUAL_INT(1000, m.max);
}

void test_ui_meta_parse_suffix(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=temp;kind=float;suffix=\xc2\xb0""C", &m));
    TEST_ASSERT_EQUAL_STRING("\xc2\xb0""C", m.suffix);
    TEST_ASSERT_EQUAL_STRING("", m.prefix);

    /* unit= is an alias for suffix= */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=bat;kind=int;unit=%", &m));
    TEST_ASSERT_EQUAL_STRING("%", m.suffix);
}

void test_ui_meta_parse_prefix(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse("bind=price;kind=int;prefix=$", &m));
    TEST_ASSERT_EQUAL_STRING("$", m.prefix);
    TEST_ASSERT_EQUAL_STRING("", m.suffix);
}

void test_ui_meta_parse_precision(void)
{
    ui_meta_t m;
    /* precision= sets decimal places */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;precision=1", &m));
    TEST_ASSERT_EQUAL_INT(1, m.precision);

    /* decimals= is alias */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;decimals=3", &m));
    TEST_ASSERT_EQUAL_INT(3, m.precision);

    /* default is -1 (use default 2) */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float", &m));
    TEST_ASSERT_EQUAL_INT(-1, m.precision);

    /* clamp: negative → 0, >6 → 6 */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;precision=-5", &m));
    TEST_ASSERT_EQUAL_INT(0, m.precision);

    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;precision=99", &m));
    TEST_ASSERT_EQUAL_INT(6, m.precision);
}

void test_ui_meta_parse_scale(void)
{
    ui_meta_t m;
    /* scale= sets fixed-point divisor */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;scale=10", &m));
    TEST_ASSERT_EQUAL_INT(10, m.scale);

    /* divisor= is alias */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;divisor=1000", &m));
    TEST_ASSERT_EQUAL_INT(1000, m.scale);

    /* default is 0 (meaning use 100) */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float", &m));
    TEST_ASSERT_EQUAL_INT(0, m.scale);

    /* non-positive values are ignored */
    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;scale=0", &m));
    TEST_ASSERT_EQUAL_INT(0, m.scale);

    TEST_ASSERT_TRUE(ui_meta_parse("bind=v;kind=float;scale=-10", &m));
    TEST_ASSERT_EQUAL_INT(0, m.scale);
}

void test_ui_meta_combined_formatting_fields(void)
{
    ui_meta_t m;
    TEST_ASSERT_TRUE(ui_meta_parse(
        "bind=temp;kind=float;scale=10;precision=1;suffix=\xc2\xb0""C;prefix= ", &m));
    TEST_ASSERT_EQUAL_INT(UI_META_KIND_FLOAT, (int)m.kind);
    TEST_ASSERT_EQUAL_STRING("temp", m.bind_key);
    TEST_ASSERT_EQUAL_INT(10, m.scale);
    TEST_ASSERT_EQUAL_INT(1, m.precision);
    TEST_ASSERT_EQUAL_STRING("\xc2\xb0""C", m.suffix);
    TEST_ASSERT_EQUAL_STRING(" ", m.prefix);
}
