/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore PHYS: physical models for plucked and struck sounds.
 *
 * MODEL
 *   PLUCK   a string (Karplus-Strong): a burst of noise in a delay line one period long, filtered a
 *           little more each time round (TONE), losing energy over DECAY; POS is where it is plucked
 *   MALLET  a struck bar: four resonant modes (a marimba's or kalimba's), INHARM pulls them from the
 *           bar's own ratios toward harmonics
 *   BELL    four modes at a bell's inharmonic ratios, long decays
 *   DRUM    a membrane's four modes, with a pitch drop (DROP over DROPT): tuned tribal toms and congas
 * HARD shapes the strike (soft: a longer, darker burst; hard: a click). BODY adds a wooden body's
 * resonance. In CHORD mode the notes of a chord are played STRUM apart. DAMP shortens the decay
 * once the note is let go. A resonant low-pass (CUTOFF, RESO) closes it.
 * Three voices; instance based; runs in the audio ISR, gphys_set() too. */
#pragma once
#include <stdint.h>
#include "x0x_param.h"

#define GPH_NV 3
#define GPH_LINE 1024                               /* the string's delay line: down to 43 Hz */
#define GPH_CR 16
enum { PHM_PLUCK, PHM_MALLET, PHM_BELL, PHM_DRUM, PHM_N };
enum { PHV_MONO, PHV_CHORD, PHV_N };
enum {
    PH_MODEL, PH_DECAY, PH_TONE, PH_POS,
    PH_HARD, PH_INHARM, PH_BODY, PH_STRUM,
    PH_DROP, PH_DROPT, PH_DAMP, PH_VOLUME,
    PH_MODE, PH_ACCENT, PH_CUTOFF, PH_RESO,
    PH_N
};

typedef struct {
    int16_t line[GPH_LINE];
    float len, wpos;                                /* the period in samples; the write position */
    float lp;                                       /* the loop filter's state */
    float y1[4], y2[4], a1[4], a2[4], amp[4];      /* the modes */
    float hz, drop_env, vel;
    int exc_left, exc_len, delay;                   /* the strike's burst; samples until it starts (strum) */
    float exc_lp;
    uint8_t on, released;
} gph_voice_t;

typedef struct {
    uint8_t pot[PH_N];
    gph_voice_t v[GPH_NV];
    uint8_t nv, idle, lite;
    float decay_t, tone, pos, hard, inharm, body, strum, drop, drop_k, damp, gain, accamt, cut, reso;
    float s1a, s1b, b1a, b1b;                       /* the low-pass and the body's states */
    float f[3], bf[3], fk, bk;
    float accent;
    uint32_t rng;
    int cr_left, quiet;
} gphys_t;

void gphys_init(gphys_t *p);
void gphys_note_on(gphys_t *p, const uint8_t *notes, int n, int accent, int slide);
void gphys_note_add(gphys_t *p, int note);
void gphys_note_off(gphys_t *p);
void gphys_all_off(gphys_t *p);
void gphys_render(gphys_t *p, float *out, int n);   /* writes n samples (mono) */
void gphys_set_lite(gphys_t *p, int on);
void gphys_set(gphys_t *p, int i, int value);
int gphys_get(const gphys_t *p, int i);
const x0x_param_t *gphys_param(int i);

/* factory presets (gphys_presets.c) */
#include "gcat.h"
typedef struct { const char *name; uint8_t cat; uint8_t pot[PH_N]; } gphys_preset_t;
extern const gphys_preset_t gphys_presets[];
extern const int gphys_npresets;
