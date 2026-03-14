#include "ui_anim.h"

#include <string.h>
#include <stdlib.h>
#include "display_config.h"

void ui_anim_init(UiAnimState *st)
{
    if (st == NULL) return;
    memset(st, 0, sizeof(*st));
}

/* ---- CSV parser ---- */

static int parse_int(const char **pp)
{
    const char *p = *pp;
    int v = 0;
    while (*p >= '0' && *p <= '9') {
        v = v * 10 + (*p - '0');
        p++;
    }
    *pp = p;
    return v;
}

static int str_starts(const char *s, const char *prefix)
{
    while (*prefix) {
        if (*s != *prefix) return 0;
        s++;
        prefix++;
    }
    return 1;
}

static UiAnimDir parse_dir(const char *s)
{
    if (str_starts(s, "right")) return UI_ANIM_DIR_RIGHT;
    if (str_starts(s, "up"))    return UI_ANIM_DIR_UP;
    if (str_starts(s, "down"))  return UI_ANIM_DIR_DOWN;
    return UI_ANIM_DIR_LEFT; /* default */
}

static int parse_one(const char *entry, UiAnimSlot *slot)
{
    if (entry == NULL || *entry == '\0') return 0;

    slot->kind = UI_ANIM_NONE;
    slot->duration_ms = 0;
    slot->dir = UI_ANIM_DIR_LEFT;
    slot->done = 0;

    if (str_starts(entry, "blink:")) {
        const char *p = entry + 6;
        int ms = parse_int(&p);
        if (ms < 50) ms = 50;   /* minimum 50 ms */
        if (ms > 30000) ms = 30000;
        slot->kind = UI_ANIM_BLINK;
        slot->duration_ms = (uint16_t)ms;
        return 1;
    }
    if (str_starts(entry, "fade:")) {
        const char *p = entry + 5;
        int ms = parse_int(&p);
        if (ms < 50) ms = 50;
        if (ms > 30000) ms = 30000;
        slot->duration_ms = (uint16_t)ms;
        if (*p == ':') p++;
        if (str_starts(p, "out")) {
            slot->kind = UI_ANIM_FADE_OUT;
        } else {
            slot->kind = UI_ANIM_FADE_IN;
        }
        return 1;
    }
    if (str_starts(entry, "slide:")) {
        const char *p = entry + 6;
        int ms = parse_int(&p);
        if (ms < 50) ms = 50;
        if (ms > 30000) ms = 30000;
        slot->duration_ms = (uint16_t)ms;
        if (*p == ':') p++;
        slot->dir = parse_dir(p);
        slot->kind = UI_ANIM_SLIDE;
        return 1;
    }
    if (str_starts(entry, "pulse:")) {
        const char *p = entry + 6;
        int ms = parse_int(&p);
        if (ms < 50) ms = 50;
        if (ms > 30000) ms = 30000;
        slot->kind = UI_ANIM_PULSE;
        slot->duration_ms = (uint16_t)ms;
        return 1;
    }
    if (str_starts(entry, "bounce:")) {
        const char *p = entry + 7;
        int ms = parse_int(&p);
        if (ms < 50) ms = 50;
        if (ms > 30000) ms = 30000;
        slot->kind = UI_ANIM_BOUNCE;
        slot->duration_ms = (uint16_t)ms;
        return 1;
    }
    return 0;
}

void ui_anim_start(UiAnimState *st, const UiScene *scene, int64_t now_us)
{
    if (st == NULL || scene == NULL) return;

    memset(st->slots, 0, sizeof(st->slots));
    st->count = 0;
    st->active = 0;

    for (int i = 0; i < (int)scene->widget_count && i < UI_ANIM_MAX_WIDGETS; i++) {
        const UiWidget *w = &scene->widgets[i];
        if (w->animations_csv == NULL || w->animations_csv[0] == '\0') continue;

        /* Parse semicolon-separated entries. */
        const char *csv = w->animations_csv;
        int slot_idx = 0;
        while (*csv && slot_idx < UI_ANIM_MAX_PER_WIDGET) {
            /* Find end of this entry. */
            const char *end = csv;
            while (*end && *end != ';') end++;

            /* Copy entry to temp buffer. */
            char buf[48];
            int len = (int)(end - csv);
            if (len >= (int)sizeof(buf)) len = (int)sizeof(buf) - 1;
            memcpy(buf, csv, (size_t)len);
            buf[len] = '\0';

            UiAnimSlot *sl = &st->slots[i][slot_idx];
            if (parse_one(buf, sl)) {
                sl->start_us = now_us;
                sl->orig_x = (int16_t)w->x;
                sl->orig_y = (int16_t)w->y;
                sl->orig_fg = w->fg;
                sl->orig_visible = w->visible;
                slot_idx++;
                st->active = 1;
            }

            if (*end == ';') end++;
            csv = end;
        }
        if (slot_idx > 0) st->count++;
    }
}

/* ---- Tick logic ---- */

static void anim_tick_blink(UiAnimSlot *sl, UiWidget *w, int64_t now_us)
{
    if (sl->duration_ms == 0) return;

    int64_t elapsed_ms = (now_us - sl->start_us) / 1000;
    int phase = (int)(elapsed_ms / (int64_t)sl->duration_ms);
    /* Even phase = visible, odd phase = hidden. */
    uint8_t vis = (phase & 1) ? 0 : sl->orig_visible;
    w->visible = vis;
}

static void anim_tick_fade(UiAnimSlot *sl, UiWidget *w, int64_t now_us)
{
    if (sl->duration_ms == 0 || sl->done) return;

    int64_t elapsed_us = now_us - sl->start_us;
    int64_t dur_us = (int64_t)sl->duration_ms * 1000;
    if (elapsed_us < 0) elapsed_us = 0;

    if (elapsed_us >= dur_us) {
        /* Animation complete. */
        if (sl->kind == UI_ANIM_FADE_IN) {
            w->fg = sl->orig_fg;
            w->visible = sl->orig_visible;
        } else {
            w->fg = 0;
        }
        sl->done = 1;
        return;
    }

    /* Progress 0..15 (4bpp gray levels). */
    int progress = (int)(elapsed_us * 15 / dur_us);
    if (progress < 0) progress = 0;
    if (progress > 15) progress = 15;

    if (sl->kind == UI_ANIM_FADE_IN) {
        /* Scale original fg by progress/15. */
        int fg = (int)sl->orig_fg * progress / 15;
        w->fg = (uint8_t)fg;
        w->visible = sl->orig_visible;
    } else {
        /* Fade out: scale original fg by (15-progress)/15. */
        int fg = (int)sl->orig_fg * (15 - progress) / 15;
        w->fg = (uint8_t)fg;
    }
}

static void anim_tick_slide(UiAnimSlot *sl, UiWidget *w, int64_t now_us)
{
    if (sl->duration_ms == 0 || sl->done) return;

    int64_t elapsed_us = now_us - sl->start_us;
    int64_t dur_us = (int64_t)sl->duration_ms * 1000;
    if (elapsed_us < 0) elapsed_us = 0;

    if (elapsed_us >= dur_us) {
        /* Animation complete: snap to original position. */
        w->x = (uint16_t)sl->orig_x;
        w->y = (uint16_t)sl->orig_y;
        sl->done = 1;
        return;
    }

    /* remaining = 1.0 - progress, mapped to pixel offset. */
    /* For slide-in: start far away, end at orig position. */
    int remaining = (int)((dur_us - elapsed_us) * 256 / dur_us); /* 0..256 fixed-point */
    if (remaining < 0) remaining = 0;

    /* Offset distance: use widget dimension + some margin as travel distance. */
    int dist_x = 0, dist_y = 0;
    switch (sl->dir) {
        case UI_ANIM_DIR_LEFT:
            dist_x = -(int)w->width - (int)sl->orig_x;
            break;
        case UI_ANIM_DIR_RIGHT:
            dist_x = 256; /* screen width */
            break;
        case UI_ANIM_DIR_UP:
            dist_y = -(int)w->height - (int)sl->orig_y;
            break;
        case UI_ANIM_DIR_DOWN:
            dist_y = 128; /* screen height */
            break;
    }

    int off_x = dist_x * remaining / 256;
    int off_y = dist_y * remaining / 256;

    int nx = (int)sl->orig_x + off_x;
    int ny = (int)sl->orig_y + off_y;

    /* Clamp to uint16_t range (widget coords are unsigned). */
    if (nx < 0) nx = 0;
    if (ny < 0) ny = 0;
    if (nx > 65535) nx = 65535;
    if (ny > 65535) ny = 65535;

    w->x = (uint16_t)nx;
    w->y = (uint16_t)ny;
}

static void anim_tick_pulse(UiAnimSlot *sl, UiWidget *w, int64_t now_us)
{
    if (sl->duration_ms == 0) return;

    int64_t elapsed_ms = (now_us - sl->start_us) / 1000;
    /* Triangular wave: ramp up for half-period, ramp down for other half. */
    int period = (int)sl->duration_ms;
    int phase = (int)(elapsed_ms % (int64_t)period);
    int half = period / 2;
    if (half == 0) half = 1;

    /* progress: 0..15..0 over one period */
    int progress;
    if (phase < half) {
        progress = phase * 15 / half;
    } else {
        progress = (period - phase) * 15 / half;
    }
    if (progress < 0) progress = 0;
    if (progress > 15) progress = 15;

    /* Modulate fg between half-brightness and full. */
    int base = (int)sl->orig_fg;
    int lo = base / 2;
    int fg = lo + (base - lo) * progress / 15;
    if (fg > 15) fg = 15;
    w->fg = (uint8_t)fg;
}

static void anim_tick_bounce(UiAnimSlot *sl, UiWidget *w, int64_t now_us)
{
    if (sl->duration_ms == 0) return;

    int64_t elapsed_ms = (now_us - sl->start_us) / 1000;
    int period = (int)sl->duration_ms;
    int phase = (int)(elapsed_ms % (int64_t)period);
    int half = period / 2;
    if (half == 0) half = 1;

    /* Triangular wave: 0..amplitude..0 offset on Y axis. */
    int amplitude = (int)w->height / 2;
    if (amplitude < 1) amplitude = 1;
    if (amplitude > 16) amplitude = 16;

    int offset;
    if (phase < half) {
        offset = phase * amplitude / half;
    } else {
        offset = (period - phase) * amplitude / half;
    }

    int ny = (int)sl->orig_y - offset;
    if (ny < 0) ny = 0;
    if (ny > 65535) ny = 65535;
    w->y = (uint16_t)ny;
}

void ui_anim_tick(UiAnimState *st, UiScene *scene, int64_t now_us, UiDirty *dirty)
{
    if (st == NULL || scene == NULL || !st->active) return;

    int any_running = 0;

    for (int i = 0; i < (int)scene->widget_count && i < UI_ANIM_MAX_WIDGETS; i++) {
        for (int s = 0; s < UI_ANIM_MAX_PER_WIDGET; s++) {
            UiAnimSlot *sl = &st->slots[i][s];
            if (sl->kind == UI_ANIM_NONE) continue;

            /* Cast away const — animation runtime needs to mutate live widgets. */
            UiWidget *w = (UiWidget *)&scene->widgets[i];
            int x, y, ww, hh;
            /* Mark old rect dirty before mutation. */
            x = (int)w->x;
            y = (int)w->y;
            ww = (int)w->width;
            hh = (int)w->height;

            switch (sl->kind) {
                case UI_ANIM_BLINK:
                    anim_tick_blink(sl, w, now_us);
                    any_running = 1;
                    break;
                case UI_ANIM_FADE_IN:
                case UI_ANIM_FADE_OUT:
                    anim_tick_fade(sl, w, now_us);
                    if (!sl->done) any_running = 1;
                    break;
                case UI_ANIM_SLIDE:
                    anim_tick_slide(sl, w, now_us);
                    if (!sl->done) any_running = 1;
                    break;
                case UI_ANIM_PULSE:
                    anim_tick_pulse(sl, w, now_us);
                    any_running = 1;
                    break;
                case UI_ANIM_BOUNCE:
                    anim_tick_bounce(sl, w, now_us);
                    any_running = 1;
                    break;
                default:
                    break;
            }

            if (dirty != NULL) {
                ui_dirty_add(dirty, x, y, ww, hh, DISPLAY_WIDTH, DISPLAY_HEIGHT);
                /* Also mark new rect if position changed. */
                ui_dirty_add(dirty, (int)w->x, (int)w->y, (int)w->width, (int)w->height, DISPLAY_WIDTH, DISPLAY_HEIGHT);
            }
        }
    }

    st->active = any_running;
}

int ui_anim_is_active(const UiAnimState *st)
{
    return (st != NULL && st->active) ? 1 : 0;
}
