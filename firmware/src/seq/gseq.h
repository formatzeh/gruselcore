/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore sequencer: 8 tracks, runs in the audio ISR, sample accurate.
 * Derived from X0X's sequencer (Charles Vestal): the same timing core (sample-accurate steps, the
 * swing grid, the external clock, the TB-303's gate / tie / slide rules), without the song, chains,
 * knob motion and the line generator, and with tracks whose type is set by the project.
 *
 * The engine renders a block like this:
 *     while (n) {
 *         k = gseq_until_event(&seq, n);      // samples until the next due event (>= 1)
 *         render k samples;
 *         gseq_advance(&seq, k, &sink);       // moves time, fires the events now due
 *         n -= k;
 *     }
 *
 * Tracks: NTRK, each with its own step counter, length (1..64) and rate, so tracks loop against
 * each other. What a track plays follows its type (ttype[], written by the main loop): DRUM fires
 * its kit's sounds, 303 plays notes, OFF nothing. A type changed while playing takes effect at the
 * track's next step (a 303 note sounding is let go first).
 *
 * The bar: a hidden clock track (index NTRK) of 16 sixteenths. When it wraps, a cued pattern takes
 * over and every track starts again from its first step. So a pattern change always lands on the
 * bar, whatever the tracks' lengths.
 *
 * Swing delays every second 16th (or 32nd); triplets are never swung, nor a track with TF_NOSWING.
 * A step's lateness never carries over to the next (the grid-slot rule, as X0X's sequencer.h
 * explains): each step is scheduled from its grid slot, never from when the step before played.
 *
 * 303 semantics (as the TB-303 and Open303's sequencer):
 *   NOTE  plays; the gate falls at half the step, unless the step slides (BS_SLIDE) or the next
 *         step is a TIE, in which case it is held through.
 *   TIE   continues the sounding note (no retrigger); same gate rule.
 *   slide a NOTE following a step with BS_SLIDE glides from the held note.
 *   REST  releases. */
#pragma once
#include <stdint.h>
#include "gpat.h"

#define FS 44100u
#define TRK_BAR NTRK                  /* the hidden bar clock */
#define SEQ_CH_OFF 0xFFu

typedef struct {
    int (*drum)(void *ctx, int trk, int snd, float vel);     /* 0: the hit did not play */
    void (*note_on)(void *ctx, int trk, int note, int accent, int slide);
    void (*note_off)(void *ctx, int trk);
    void (*midi)(void *ctx, uint8_t status, uint8_t d1, uint8_t d2);   /* clock / transport / notes out */
    void (*step)(void *ctx, int trk, int step);                         /* UI playhead (optional) */
    void *ctx;
} seq_sink_t;

typedef struct {                      /* one track's runtime */
    uint8_t pos;                      /* current step */
    int8_t pp_dir;                    /* ping-pong direction */
    uint8_t started;                  /* the first step has fired since start */
    uint8_t sounding;                 /* 303: a note is held */
    uint8_t held_note;                /* 303: the held note, bit 7 = it slides on */
    uint8_t odd;                      /* the last step fired was odd, counted from the start */
    uint8_t ext_ticks;                /* external clock: ticks into this step */
    uint8_t played_type;              /* the type its last step played as (a type change lets go first) */
    uint32_t to_next;                 /* samples to the next step (Q8 fraction) */
    uint32_t swing_delay;             /* how long after its grid slot the next step plays, Q8 */
    uint32_t step_len;                /* the step playing: its length, Q8 */
    uint32_t to_off;                  /* 303: samples to the gate falling, Q8; 0 = none */
    uint32_t rng;                     /* DIR_RANDOM */
    uint8_t note_out;                 /* 303: the note echoed on MIDI, for the note off */
    uint8_t rsv[3];
} seq_track_t;

typedef struct {
    pattern_t *pat;                   /* NPAT patterns (the project's) */
    volatile uint8_t ttype[NTRK];     /* each track's type (TT_*) */
    volatile uint8_t playing;         /* 1 = running */
    volatile uint8_t cur;             /* the pattern playing */
    volatile uint8_t cue;             /* the cued pattern (0xFF = none): starts at the bar */
    volatile uint8_t ext;             /* 1 = following an external clock */
    volatile uint8_t send_clock;      /* 1 = emit MIDI clock + transport when internal */
    volatile uint8_t send_notes;      /* 1 = echo the sequence on MIDI, on each track's channel */
    volatile uint8_t ch[NTRK];        /* each track's MIDI channel 0-15 (in and out); SEQ_CH_OFF = none */
    volatile uint8_t mute;            /* bit t = track t muted */
    volatile uint8_t accent_q7;       /* drum velocity of a non-accented hit, of 127 */
    volatile uint8_t req_start, req_stop, req_cont;   /* transport requests from the UI / MIDI */
    float bpm;                        /* internal tempo (UI writes; read per step) */
    float ext_bpm;                    /* tempo measured from the external clock */
    seq_track_t t[NTRK + 1];          /* the tracks, then the bar clock */
    uint32_t bars;                    /* bars since start (the UI's bar counter) */
    uint32_t clk_to_next;             /* internal: samples to the next MIDI clock, Q8 */
    uint32_t ext_since;               /* samples since the last external clock (tempo estimate) */
    uint32_t ext_period;              /* smoothed samples per external clock, Q8 */
    volatile uint32_t ext_pending;    /* external clocks received, not yet consumed */
} seq_t;

void gseq_init(seq_t *s, pattern_t *patterns);
uint32_t gseq_until_event(seq_t *s, uint32_t n);
void gseq_advance(seq_t *s, uint32_t k, const seq_sink_t *o);

/* main loop / MIDI side (flag writes picked up at the next block) */
void gseq_start(seq_t *s);            /* from step 1 of the current (or cued) pattern */
void gseq_stop(seq_t *s);
void gseq_continue(seq_t *s);
void gseq_ext_clock(seq_t *s);        /* one 24-ppqn tick (MIDI 0xF8) */
void gseq_cue(seq_t *s, int pattern); /* at the end of the bar (at once, if stopped) */
int gseq_cue_of(const seq_t *s);      /* the cued pattern, or -1 */

uint32_t gseq_step_q8(const seq_t *s, int rate);   /* a step of this rate in samples, Q8 (no swing) */
float gseq_tempo(const seq_t *s);     /* the tempo in effect (internal or measured) */
int gseq_track_len(const seq_t *s, int t);         /* steps in track t's part of the current pattern */
