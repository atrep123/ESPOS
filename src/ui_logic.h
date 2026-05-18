#pragma once

#include <stdint.h>

/* Visual-backend logic schema (events / rules) shared by:
 *  - generated programs (ui_design.c, emitted by tools/ui_codegen.py),
 *  - the firmware logic executor (services/logic/logic.c).
 *
 * The designer's per-widget `events` and per-scene `rules` are compiled into
 * flat, deterministic tables of these PODs. Keep enum values STABLE: the
 * Python codegen emits these symbolic names, so reordering would silently
 * change generated firmware behavior.
 */

#ifdef __cplusplus
extern "C" {
#endif

/* What starts a rule. */
typedef enum {
    UI_TRIG_BOOT = 0,       /* fired once after the logic service starts */
    UI_TRIG_TIMER = 1,      /* a logic timer slot elapsed (t.timer_id) */
    UI_TRIG_GPIO_IN = 2,    /* GPIO level edge on t.pin (t.edge) */
    UI_TRIG_BLE_RECV = 3,   /* a BLE payload arrived (board must have ble) */
    UI_TRIG_LORA_RECV = 4,  /* a LoRa payload arrived (board must have lora) */
    UI_TRIG_WIDGET = 5,     /* a widget event (t.widget_id + t.widget_event) */
    UI_TRIG__COUNT
} UiLogicTriggerType;

/* Widget event sub-kind for UI_TRIG_WIDGET and per-widget event handlers. */
typedef enum {
    UI_WEV_PRESS = 0,
    UI_WEV_CHANGE = 1,
    UI_WEV_FOCUS = 2,
    UI_WEV__COUNT
} UiLogicWidgetEvent;

/* GPIO edge selector for UI_TRIG_GPIO_IN. */
typedef enum {
    UI_EDGE_ANY = 0,
    UI_EDGE_RISING = 1,
    UI_EDGE_FALLING = 2,
} UiLogicEdge;

/* One real, codegen-backed effect. Every type maps to working firmware C in
 * services/logic/logic.c — there are no inert/TODO actions. */
typedef enum {
    UI_ACT_SET_SCENE = 0,   /* switch to scene index a.i0 */
    UI_ACT_SET_WIDGET = 1,  /* set a.s0(id).a.prop to value/text */
    UI_ACT_SET_VAR = 2,     /* var[a.i0] = <expr over vars/literals> */
    UI_ACT_GPIO_WRITE = 3,  /* gpio_set_level(a.i0 pin, a.i1 level) */
    UI_ACT_TOAST = 4,       /* enqueue toast overlay with a.s0 text */
    UI_ACT_START_TIMER = 5, /* arm logic timer a.i0 with period a.i1 ms */
    UI_ACT_STOP_TIMER = 6,  /* disarm logic timer a.i0 */
    UI_ACT_BLE_SEND = 7,    /* transmit a.s0 bytes over BLE */
    UI_ACT_LORA_SEND = 8,   /* transmit a.s0 bytes over LoRa */
    UI_ACT__COUNT
} UiLogicActionType;

/* set_widget target property. */
typedef enum {
    UI_PROP_VALUE = 0,
    UI_PROP_TEXT = 1,
    UI_PROP_CHECKED = 2,
    UI_PROP_VISIBLE = 3,
    UI_PROP_ENABLED = 4,
} UiLogicProp;

/* Comparison operator for conditions. */
typedef enum {
    UI_CMP_EQ = 0, /* == */
    UI_CMP_NE = 1, /* != */
    UI_CMP_LT = 2, /* <  */
    UI_CMP_GT = 3, /* >  */
    UI_CMP_LE = 4, /* <= */
    UI_CMP_GE = 5, /* >= */
} UiLogicCmpOp;

/* Operand kind for a condition side / set_var term. */
typedef enum {
    UI_OPND_LITERAL = 0,      /* literal int (value) */
    UI_OPND_VAR = 1,          /* logic variable, index = i0 */
    UI_OPND_WIDGET_VALUE = 2, /* widget(s0).value */
    UI_OPND_WIDGET_CHECKED = 3 /* widget(s0).checked */
} UiLogicOperandKind;

/* How a condition combines with the NEXT condition in a rule. Evaluation is
 * strictly left-to-right (no precedence) — this is intentionally bounded. */
typedef enum {
    UI_JOIN_AND = 0, /* && */
    UI_JOIN_OR = 1,  /* || */
} UiLogicJoin;

typedef struct {
    uint8_t kind;       /* UiLogicOperandKind */
    int32_t value;      /* literal value OR var index (i0) */
    const char *s0;     /* widget id for widget operands; else NULL */
} UiLogicOperand;

typedef struct {
    UiLogicOperand lhs;
    uint8_t op;         /* UiLogicCmpOp */
    UiLogicOperand rhs;
    uint8_t join;       /* UiLogicJoin — combine with next cond */
} UiLogicCond;

/* set_var expression: result = lhs <arith> rhs (single bounded op). When
 * has_rhs == 0 it is a plain assignment of lhs. arith: 0:+ 1:- 2:* 3:/ . */
typedef struct {
    UiLogicOperand lhs;
    uint8_t arith;
    uint8_t has_rhs;
    UiLogicOperand rhs;
} UiLogicExpr;

typedef struct {
    uint8_t type;       /* UiLogicActionType */
    int32_t i0;         /* scene idx / pin / timer id / var idx / set_widget int value */
    int32_t i1;         /* level / period-ms */
    uint8_t prop;       /* UiLogicProp (set_widget) */
    const char *s0;     /* widget id (set_widget) / toast text / payload bytes */
    const char *s1;     /* set_widget(text=...) payload; else NULL */
    UiLogicExpr expr;   /* set_var expression (type == UI_ACT_SET_VAR) */
} UiLogicAction;

typedef struct {
    uint8_t trig;           /* UiLogicTriggerType */
    int32_t trig_i0;        /* timer id / gpio pin */
    uint8_t trig_edge;      /* UiLogicEdge (gpio_in) */
    const char *trig_s0;    /* widget id (UI_TRIG_WIDGET) */
    uint8_t trig_wev;       /* UiLogicWidgetEvent (UI_TRIG_WIDGET) */
    const char *name;       /* optional label (diagnostics) */
    const UiLogicCond *conds;
    uint16_t cond_count;
    const UiLogicAction *actions;
    uint16_t action_count;
} UiLogicRule;

/* All logic for a single scene (index-aligned with ui_scenes[]). */
typedef struct {
    const char *scene_name;
    const UiLogicRule *rules;
    uint16_t rule_count;
} UiLogicProgram;

#ifdef __cplusplus
}
#endif
