/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore VA synth: a virtual-analog voice for leads, basses, plucks, stabs and pads.
 *
 * Seven voice slots, each with two oscillators (SAW, SQUARE with pulse width, TRIANGLE, SINE;
 * band-limited with PolyBLEP) and a sub square an octave under oscillator 1, plus noise. All slots
 * go through one filter (LP 24 dB, LP 12 dB, BP, HP; resonant) with its own envelope, then one amp
 * envelope. MODE:
 *   MONO    one slot; a note played while one is held (slide) glides and does not retrigger
 *   CHORD   up to four slots, one per note of the chord (the envelopes are shared: paraphonic)
 *   UNISON  four slots on the note, detuned against each other (DETUNE)
 *   HYPER   all seven slots on the note, spread twice as wide: a trance supersaw
 * GLIDE glides every note (portamento); a slide glides even at GLIDE 0. The LFO is synced to the
 * tempo (8 bars .. 1/32) and moves the pitch and / or the cutoff.
 *
 * Envelopes, glide, LFO and the filter's coefficients run at a control rate of GVA_CR samples.
 * Instance based, so each VA track owns one gva_t; everything runs in the audio ISR, gva_set() too. */
#pragma once
#include <stdint.h>
#include "x0x_param.h"

#define GVA_NV 7                                    /* voice slots (HYPER) */
#define GVA_NCHORD 4                                /* notes in CHORD, voices in UNISON */
#define GVA_CR 16                                   /* control rate: samples a step */
enum { VAW_SAW, VAW_SQR, VAW_TRI, VAW_SINE, VAW_N };
enum { VAM_MONO, VAM_CHORD, VAM_UNISON, VAM_HYPER, VAM_N };
enum { VAF_LP24, VAF_LP12, VAF_BP, VAF_HP, VAF_N };
enum { VAL_TRI, VAL_SAW, VAL_SQR, VAL_SH, VAL_N };
enum {
    VA_WAVE1, VA_WAVE2, VA_TUNE2, VA_DETUNE,        /* oscillators: TUNE2 64 = unison, +-24 semitones */
    VA_MIX, VA_SUB, VA_NOISE, VA_PW,                /* MIX 0 = osc 1 only, 127 = osc 2 only */
    VA_CUTOFF, VA_RESO, VA_ENV, VA_FTYPE,           /* filter: 30 Hz .. 18 kHz; ENV up to +7 octaves */
    VA_FATT, VA_FDEC, VA_FSUS, VA_KEYTRK,           /* the filter's envelope; key tracking 0..100 % */
    VA_ATT, VA_DEC, VA_SUS, VA_REL,                 /* the amp's envelope */
    VA_MODE, VA_GLIDE, VA_ACCENT, VA_VOLUME,        /* VOLUME: 0.35 dB a step, 100 = unity, 0 = off */
    VA_LRATE, VA_LSHAPE, VA_LPITCH, VA_LCUT,        /* LFO */
    VA_N
};

typedef struct {
    float ph1, ph2, phs;                            /* oscillator phases, 0..1 */
    float note, target;                             /* pitch now (gliding) and where it goes, semitones */
    float off;                                      /* unison detune, semitones */
    float dt1, dt2, dts;                            /* phase increments (control rate) */
    uint8_t on;
} gva_voice_t;

typedef struct {
    uint8_t pot[VA_N];
    gva_voice_t v[GVA_NV];
    uint8_t nv;                                     /* slots sounding */
    uint8_t gate, idle, lite;
    uint8_t aenv_st, fenv_st;                       /* 0 off, 1 attack, 2 decay / sustain, 3 release */
    float aenv, fenv, accent;
    float glide_k;                                  /* this note's glide coefficient (0 = jump) */
    float lfo_ph, lfo_val, lfo_sh;
    float bpm;
    uint32_t rng;
    int cr_left;                                    /* samples to the next control step */
    /* derived from the pots (gva_set) */
    float a_inc, d_k, r_k, fa_inc, fd_k, sus, fsus; /* envelopes, a control step at a time */
    float pw, mix, sub, noise, det, cut, reso, envamt, keytrk, lpitch, lcut, accamt, glide_t;
    /* filter: two TPT state-variable stages (a1, a2, a3 each), their states */
    float f1[3], f2[3], k1, k2, s1a, s1b, s2a, s2b;
    float amp, amp_step;                            /* the amp gain, ramped across a control step */
    float gain;                                     /* VOLUME and the voices' sum normalised */
} gva_t;

void gva_init(gva_t *va);                           /* silent, the defaults */
void gva_note_on(gva_t *va, const uint8_t *notes, int n, int accent, int slide);   /* n 1..4 */
void gva_note_add(gva_t *va, int note);             /* CHORD: one more note to the sounding ones */
void gva_note_off(gva_t *va);
void gva_all_off(gva_t *va);                        /* silent now */
void gva_render(gva_t *va, float *out, int n);      /* writes n samples (mono) */
void gva_set_bpm(gva_t *va, float bpm);
void gva_set_lite(gva_t *va, int on);               /* the overload guard: UNISON and CHORD on one slot */
void gva_set(gva_t *va, int i, int value);
int gva_get(const gva_t *va, int i);
const x0x_param_t *gva_param(int i);

/* factory presets (gva_presets.c) */
#include "gcat.h"
typedef struct { const char *name; uint8_t cat; uint8_t pot[VA_N]; } gva_preset_t;   /* cat: CAT_* */
extern const gva_preset_t gva_presets[];
extern const int gva_npresets;
