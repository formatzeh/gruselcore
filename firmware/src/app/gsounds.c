/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore's synth sound list; see gsounds.h. */
#include "gsounds.h"
#include "../seq/gpat.h"
#include "../dsp/bass303.h"
#include "../dsp/gva.h"
#include "../dsp/gfm.h"
#include "../dsp/gphys.h"

#define GS_MAX 255
static uint8_t order[GS_MAX], pos_of[GS_MAX];   /* browse order, and each id's place in it */
static int n_order;
static const char *const CATN[NCAT] = CAT_NAMES;

int gs_count(void) { return b303_npresets + gva_npresets + gfm_npresets + gphys_npresets; }

/* the engine of id, and its index in that engine's table */
static int split(int id, int *k)
{
    if (id < 0)
        id = 0;
    if (id < b303_npresets) { *k = id; return TT_303; }
    id -= b303_npresets;
    if (id < gva_npresets) { *k = id; return TT_VA; }
    id -= gva_npresets;
    if (id < gfm_npresets) { *k = id; return TT_FM; }
    id -= gfm_npresets;
    *k = id < gphys_npresets ? id : 0;
    return TT_PHYS;
}

int gs_type(int id) { int k; return split(id, &k); }
int gs_cat(int id)
{
    int k, tt = split(id, &k);
    return tt == TT_303 ? b303_presets[k].cat : tt == TT_VA ? gva_presets[k].cat :
           tt == TT_FM ? gfm_presets[k].cat : gphys_presets[k].cat;
}
const char *gs_name(int id)
{
    int k, tt = split(id, &k);
    return tt == TT_303 ? b303_presets[k].name : tt == TT_VA ? gva_presets[k].name :
           tt == TT_FM ? gfm_presets[k].name : gphys_presets[k].name;
}
const uint8_t *gs_pots(int id, int *n)
{
    int k, tt = split(id, &k);
    switch (tt) {
    case TT_303: *n = BASS303_NPARAMS; return b303_presets[k].pot;
    case TT_VA: *n = VA_N; return gva_presets[k].pot;
    case TT_FM: *n = FM_N; return gfm_presets[k].pot;
    default: *n = PH_N; return gphys_presets[k].pot;
    }
}
int gs_first(int tt)
{
    switch (tt) {
    case TT_VA: return b303_npresets;
    case TT_FM: return b303_npresets + gva_npresets;
    case TT_PHYS: return b303_npresets + gva_npresets + gfm_npresets;
    default: return 0;
    }
}

static void build(void)
{
    int c, id, n = gs_count();
    if (n_order)
        return;
    if (n > GS_MAX)
        n = GS_MAX;
    for (c = 0; c < NCAT; c++)
        for (id = 0; id < n; id++)
            if (gs_cat(id) == c) {
                pos_of[id] = (uint8_t)n_order;
                order[n_order++] = (uint8_t)id;
            }
}

int gs_pos(int id, int cat, int *total)
{
    int i, p = 0, t = 0;
    build();
    if (cat < 0) {
        *total = n_order;
        return id >= 0 && id < n_order ? pos_of[id] : 0;
    }
    for (i = 0; i < n_order; i++)
        if (gs_cat(order[i]) == cat) {
            if (order[i] == id)
                p = t;
            t++;
        }
    *total = t;
    return p;
}

int gs_step(int id, int d, int cat)
{
    int p, total, i;
    build();
    if (cat < 0) {
        p = id >= 0 && id < n_order ? pos_of[id] : 0;
        p = ((p + d) % n_order + n_order) % n_order;
        return order[p];
    }
    if (gs_cat(id) != cat) {                         /* not in the list: its first (or last) sound */
        for (i = 0; i < n_order; i++)
            if (gs_cat(order[d > 0 ? i : n_order - 1 - i]) == cat)
                return order[d > 0 ? i : n_order - 1 - i];
        return id;
    }
    p = gs_pos(id, cat, &total);
    p = ((p + d) % total + total) % total;
    for (i = 0; i < n_order; i++)
        if (gs_cat(order[i]) == cat && !p--)
            return order[i];
    return id;
}

const char *gs_cat_name(int cat) { return cat >= 0 && cat < NCAT ? CATN[cat] : "ALL"; }
const char *gs_engine_name(int tt)
{
    return tt == TT_303 ? "303" : tt == TT_VA ? "VA" : tt == TT_FM ? "FM" : tt == TT_PHYS ? "PHYS" : "";
}
