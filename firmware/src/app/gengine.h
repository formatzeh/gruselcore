/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore audio engine: 8 tracks, each a drum kit (dsp/gdrum) or a 303 (dsp/bass303) by its
 * type, each through its own filter and drive, then the mixer, the shared reverb and delay
 * (dsp/fxbus) and the master (dsp/master). engine_render() runs in the audio ISR; everything else is
 * called from the main loop and reaches the ISR only through the command queue, so the engines'
 * state is only ever touched by one context. Built after X0X's engine.c (Charles Vestal).
 *
 * Parameters are addressed as (target, voice, index) -> pot value, the same triple the UI, the
 * project and the command queue use:
 *   T_DRUM   voice = track * NDSND + sound (0..63), index = gdrum.h GP_*
 *   T_303    voice = track, index = bass303.h's pots
 *   T_MIX    voice = track, index = MX_*
 *   T_FX     voice 0 / 1: fxbus.h params k = voice * 16 + index (reverb, delay, master drive)
 *   T_MST    voice 0: master.h params (compressor / pump, filter, limiter)
 *   T_DMAC   voice = track: a drum track's kit macros, index = gdrum.h GDK_* (64 = the kit as it is)
 *   T_TRK    voice = track: index TK_TYPE (value = TT_*) changes the track's type; TK_RELOAD (value
 *            ignored) re-reads every pot of the track from the project's sound (after a kit load)
 *
 * A track's type lives in the sound (sound_t.ttype) and in the sequencer (seq.ttype); the engine
 * sets the sequencer's when it applies a type change, so the two never disagree in the ISR. */
#pragma once
#include <stdint.h>
#include "../dsp/x0x_param.h"
#include "../dsp/gdrum.h"
#include "../seq/gseq.h"

enum { T_DRUM, T_303, T_MIX, T_FX, T_MST, T_TRK, T_DMAC, NTARGETS };
enum { TK_TYPE, TK_RELOAD };
/* T_MIX, per track: level, pan, the two sends, the track's filter (64 = off, under it a low-pass,
 * over it a high-pass), its resonance, its drive (0 = clean) */
enum { MX_LEVEL, MX_PAN, MX_REV, MX_DLY, MX_FILTER, MX_RESO, MX_DRIVE, MX_NPARAMS };
/* a 303 track's output gain: its default sound at LEVEL 100 as loud as a drum kit's sounds (-16 dB,
 * tests/host/gdrum_test.c) */
#define B303_GAIN 3.6f
#define B303_NP 16                     /* room for the 303's pots in the sound */
#define FX_NP 32                       /* room for fxbus's pots */
#define MST_NP 16                      /* room for master's pots */

/* the sound of a project: every pot of every engine, mirrored here by the main loop */
typedef struct {
    uint8_t ttype[NTRK];               /* TT_* */
    uint8_t kit[NTRK];                 /* the factory kit last loaded on a drum track (shown, not used) */
    uint8_t drum[NTRK][NDSND][GP_N];   /* a drum track's 8 sounds */
    uint8_t b303[NTRK][B303_NP];       /* a 303 track's pots */
    uint8_t mix[NTRK][MX_NPARAMS + 1]; /* (+1: aligned) */
    uint8_t fx[FX_NP];
    uint8_t mst[MST_NP];
    uint8_t dmac[NTRK][GDK_N];         /* a drum track's kit macros (HOME's knobs) */
} sound_t;

extern seq_t seq;                      /* the sequencer (its pattern pointer is the project's) */
/* render stages (the PERF screen): tracks 1-8, FX, MASTER, SEQ */
enum { PR_TRK0, PR_FX = NTRK, PR_MST, PR_SEQ, ENG_PROF_N };
extern volatile uint32_t eng_prof[ENG_PROF_N], eng_prof_frames;
extern volatile uint8_t eng_step[NTRK];        /* playheads for the UI */
extern volatile uint16_t eng_peak[NTRK];       /* track meters, Q15, decaying (UI) */
extern volatile uint8_t eng_hit[NTRK][NDSND];  /* each drum sound's last hit, 255 = full velocity */
#define SCOPE_N 256u
extern int16_t eng_scope[SCOPE_N];
extern volatile uint32_t eng_scope_w;

void engine_init(pattern_t *patterns, const sound_t *base);
void engine_render(int32_t *out_lr, uint32_t n);   /* ISR: n stereo frames, 24-bit in int32 */
void engine_load(uint32_t pct, uint32_t frames);  /* ISR, after engine_render: the overload guard */
int engine_guard_active(void);
extern volatile uint32_t eng_guard_count;

/* parameter descriptors (UI) */
int engine_nvoices(int target);
int engine_nparams(int target, int voice);
const x0x_param_t *engine_param(int target, int voice, int i);

/* main loop -> ISR */
void engine_set(int target, int voice, int i, int value);   /* queued; the sound_t mirror is the caller's */
void engine_apply_sound(const sound_t *s);                  /* queue every value (load, init) */
void engine_sound_defaults(sound_t *s);                     /* the power-on sound: see gengine.c */
void engine_track_kit(sound_t *s, int trk, int kit);        /* a factory kit into a drum track's mirror,
                                                             * then TK_RELOAD queued */
void engine_drum(int trk, int snd, float vel);              /* play now (keys) */
void engine_note_on(int trk, int note, int accent, int slide);
void engine_note_off(int trk);
void engine_out_loud(int on);
void engine_usb_full(int on);
void engine_volume(int32_t *out_lr, uint32_t n);
float engine_gr_db(void);                                   /* master compressor gain reduction (UI meter) */
