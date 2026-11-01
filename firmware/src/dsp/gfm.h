/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore FM synth: four sine operators, eight algorithms, feedback on operator 4.
 *
 * Each operator has a RATIO (of the note's frequency), a LEVEL (a modulator's: how deep it modulates;
 * a carrier's: how loud it is) and its own envelope: the shared ATTACK, then its DECAY down to its
 * SUSTN, and the shared RELEAS. ACCENT deepens the modulation of an accented note; the LFO (synced to
 * the tempo) moves the pitch and / or the modulation depth. MODE: MONO (a slide glides, without a new
 * attack) or CHORD (up to GFM_NV notes, the envelopes shared).
 *
 * Algorithms (a -> b: a modulates b; the carriers are heard):
 *   1  4>3>2>1           5  4>3, 2>1 (two stacks)
 *   2  (3+4)>2>1         6  4>1, 4>2, 4>3 (one modulator, three carriers)
 *   3  4>3>1, 2>1        7  4>3, carriers 1 2 3
 *   4  4>2>1, 3>1        8  1 2 3 4 all carriers (additive)
 * Control rate GFM_CR samples; instance based; runs in the audio ISR, gfm_set() too. */
#pragma once
#include <stdint.h>
#include "x0x_param.h"

#define GFM_NV 3                                    /* notes in CHORD mode */
#define GFM_CR 16
#define GFM_NALG 8
enum { FMM_MONO, FMM_CHORD, FMM_N };
enum {
    FM_ALGO, FM_FEEDBK, FM_MODE, FM_GLIDE,
    FM_R1, FM_L1, FM_D1, FM_S1,                     /* operator 1: ratio, level, decay, sustain */
    FM_R2, FM_L2, FM_D2, FM_S2,
    FM_R3, FM_L3, FM_D3, FM_S3,
    FM_R4, FM_L4, FM_D4, FM_S4,
    FM_ATT, FM_REL, FM_ACCENT, FM_VOLUME,
    FM_LRATE, FM_LPITCH, FM_LMOD, FM_DETUNE,
    FM_N
};

typedef struct {
    float ph[4];                                    /* operator phases, turns */
    float note, target;
    float inc[4];                                   /* phase increments a sample */
    uint8_t on;
} gfm_voice_t;

typedef struct {
    uint8_t pot[FM_N];
    gfm_voice_t v[GFM_NV];
    uint8_t nv, gate, idle, lite, st;               /* st: 0 off, 1 attack, 2 decay / sustain, 3 release */
    float env[4], lvl[4], ratio[4];                 /* each operator's envelope, level, ratio */
    float sus[4], dk[4];
    float a_inc, r_k, accent, accamt, gain, glide_t, glide_k, det, fb, fbz[GFM_NV][2];
    float lfo_ph, lfo_val, lpitch, lmod, bpm;
    float amp, amp_step;
    float mod_now[4], mod_step[4];                  /* the operators' levels, ramped across a control step */
    int cr_left;
} gfm_t;

void gfm_init(gfm_t *f);
void gfm_note_on(gfm_t *f, const uint8_t *notes, int n, int accent, int slide);
void gfm_note_add(gfm_t *f, int note);
void gfm_note_off(gfm_t *f);
void gfm_all_off(gfm_t *f);
void gfm_render(gfm_t *f, float *out, int n);       /* writes n samples (mono) */
void gfm_set_bpm(gfm_t *f, float bpm);
void gfm_set_lite(gfm_t *f, int on);                /* the overload guard: CHORD on one note */
void gfm_set(gfm_t *f, int i, int value);
int gfm_get(const gfm_t *f, int i);
const x0x_param_t *gfm_param(int i);

/* factory presets (gfm_presets.c) */
#include "gcat.h"
typedef struct { const char *name; uint8_t cat; uint8_t pot[FM_N]; } gfm_preset_t;
extern const gfm_preset_t gfm_presets[];
extern const int gfm_npresets;
