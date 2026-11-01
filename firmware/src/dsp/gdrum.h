/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore drum engine: one kit of 8 synthesized drum sounds, built for punch.
 *
 * Every sound is the same voice with a MODEL (kick, snare, clap, hat, tom, rim, metal, zap) and 16
 * pots. A kick is a sine with a two-stage pitch drop (PITCH over PDEC, then BODY over a slower glide),
 * a click layer, an amp envelope with a hold (PUNCH), a tail for the rumble, and a drive stage with
 * five curves. The other models use the same parts: a tone, filtered noise (TONE), six square
 * oscillators for metal, retriggered noise for claps.
 *
 * A kit is plain data: 8 x GP_N pots (gd_kit_t). The factory kits are in gdrum_kits.c.
 * Slot 3 (closed hat) chokes slot 4 (open hat), as on most drum machines.
 *
 * The engine is instance based (no shared state but read-only tables), so each DRUM track owns
 * one gdrum_t. Everything runs in the audio ISR: gdrum_set() may be called there too (it only
 * recomputes the voice's coefficients). */
#pragma once
#include <stdint.h>
#include "x0x_param.h"

#define GD_NSND 8                                   /* sounds per kit */
enum { GD_KICK, GD_SNARE, GD_CLAP, GD_CHAT, GD_OHAT, GD_TOM, GD_RIM, GD_PERC };   /* slot roles */
enum { GDM_KICK, GDM_SNARE, GDM_CLAP, GDM_HAT, GDM_TOM, GDM_RIM, GDM_METAL, GDM_ZAP, GDM_N };
enum { GDC_SOFT, GDC_HARD, GDC_FOLD, GDC_TUBE, GDC_CRUSH, GDC_N };
enum {
    GP_MODEL,   /* GDM_*                                                   */
    GP_LEVEL,   /* 100 = unity                                             */
    GP_TUNE,    /* the end pitch: note 12 + 0.75 * pot                     */
    GP_PITCH,   /* first pitch drop: 0..72 semitones                       */
    GP_PDEC,    /* its time: 0.3..60 ms                                    */
    GP_BODY,    /* second, slower drop: 0..24 semitones over 8 x PDEC      */
    GP_DECAY,   /* amp decay: 5 ms..3 s                                    */
    GP_TAIL,    /* a second, 2x longer decay under the first (rumble)      */
    GP_CLICK,   /* the transient layer's level                             */
    GP_TONE,    /* noise / click / metal filter: 100 Hz..16 kHz            */
    GP_NOISE,   /* tone <-> noise mix                                      */
    GP_DRIVE,   /* drive gain 1..60                                        */
    GP_CURVE,   /* GDC_*                                                   */
    GP_PUNCH,   /* full-level hold before the decay: 0..50 ms              */
    GP_ATTACK,  /* 0..30 ms                                                */
    GP_PAN,     /* 64 = centre                                             */
    GP_N
};

typedef struct { uint8_t pot[GD_NSND][GP_N]; } gd_kit_t;

typedef struct {
    uint8_t pot[GP_N];
    /* derived (gd_voice_calc) */
    float note_end, pitch_amt, body_amt, gain, click, noise_mix, drive, drive_comp;
    float k_pdec, k_body, k_dec, k_tail, tail_lvl, att_inc, k_click;
    uint32_t hold_n;
    float svf_f, svf_q, pan_l, pan_r;
    /* runtime */
    uint8_t active, stage;                          /* stage: 0 attack, 1 hold, 2 decay */
    uint8_t clap_n;                                 /* clap: bursts still to come */
    float ph, e1, e2, amp, tail, clk, vel;
    uint32_t hold_left, clap_next;
    float lp, bp;                                   /* SVF state */
    float clk_lp, dc_x, dc_y;
    float mph[6];                                   /* metal oscillators */
    float crush_h; uint8_t crush_c;
} gd_voice_t;

typedef struct {
    gd_voice_t v[GD_NSND];
    uint32_t rng;
} gdrum_t;

void gdrum_init(gdrum_t *d);                        /* silent, the first factory kit */
void gdrum_load_kit(gdrum_t *d, const gd_kit_t *k);
void gdrum_trigger(gdrum_t *d, int snd, float vel); /* vel 0..1 (1 = accent) */
void gdrum_render_st(gdrum_t *d, float *l, float *r, int n);   /* ADDS n samples to l, r */
int gdrum_active(const gdrum_t *d);
void gdrum_set(gdrum_t *d, int snd, int i, int value);
int gdrum_get(const gdrum_t *d, int snd, int i);
const x0x_param_t *gdrum_param(int i);
const char *gdrum_slot_name(int snd);              /* "KICK", "SNARE", ... */

/* factory kits (gdrum_kits.c) */
extern const gd_kit_t gd_kits[];
extern const char *const gd_kit_names[];
extern const int gd_nkits;
