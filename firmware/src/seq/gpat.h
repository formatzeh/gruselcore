/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore pattern model: 32 patterns, each 8 tracks.
 *
 * A track's TYPE (DRUM, 303, later VA / FM) belongs to the project, not to a pattern: the sound
 * stays when the pattern changes. A pattern holds each track's steps, in the form its type uses
 * (a union: changing a track's type clears that track's steps in every pattern, gpat_track_clear).
 *
 * Plain data, no pointers: a pattern copies with an assignment and the project stores the bytes.
 * The UI edits these in place from the main loop while the sequencer reads them in the audio ISR:
 * every field the sequencer reads is a single byte or an aligned 32-bit word, so a read never sees
 * half a write. A drum row is two words (steps 1-32, 33-64): sm_get / sm_flip below. */
#pragma once
#include <stdint.h>

#define NTRK 8                       /* tracks */
#define NPAT 32
#define NSTEPS 64
#define NSW (NSTEPS / 32)            /* 32-bit words in a row of steps */
#define NDSND 8                      /* sounds in a drum kit (gdrum.h GD_NSND) */

enum { TT_OFF, TT_DRUM, TT_303, TT_VA, NTT };                /* track types */
/* a note track (303, VA): the same steps (u.b), chords and arpeggiator; a change between the two
 * keeps the steps */
static inline int tt_notes(int tt) { return tt == TT_303 || tt == TT_VA; }
enum { RATE_16, RATE_16T, RATE_32, RATE_8T, RATE_8, NRATES };  /* step length */
enum { DIR_FWD, DIR_REV, DIR_PINGPONG, DIR_RANDOM, NDIRS };    /* playback direction (303 tracks) */
enum { G_REST, G_NOTE, G_TIE };                              /* a 303 step's gate */

/* a note step: one byte of note, one of flags (the TB-303's own semantics, see gseq.h) */
#define BS_GATE_MASK 0x03u
#define BS_ACCENT 0x04u
#define BS_SLIDE 0x08u                /* slide INTO the next step */
#define BS_CHORD_SHIFT 4              /* the step's chord (gp_chords), 0 = the note alone */
#define BS_CHORD_MASK 0xF0u
#define NCHORDS 16
#define CHORD_NMAX 4
typedef struct { const char *name; int8_t iv[CHORD_NMAX]; } chord_t;   /* intervals, -1 = none */
extern const chord_t gp_chords[NCHORDS];
int gp_chord_notes(int root, int chord, uint8_t *out);   /* the chord's notes (1..4), from the root */

/* the arpeggiator of a note track (tpart_t.u.b.arp): OFF plays the chord as a chord. Each step's chord
 * (or its note alone) is played as notes, ARP_DIV of them a step, over ARP_OCT octaves */
enum { ARP_OFF, ARP_UP, ARP_DOWN, ARP_UPDN, ARP_RAND, NARPS };
typedef struct {
    uint8_t note;                     /* MIDI note */
    uint8_t flags;                    /* gate | BS_ACCENT | BS_SLIDE */
} bstep_t;

#define TF_NOSWING 0x01u              /* tpart_t.flags: this track ignores the pattern's swing */

typedef struct {
    uint8_t len;                      /* 1..64 (the UI offers 8, 16, 32, 64) */
    uint8_t rate;                     /* RATE_* */
    uint8_t flags;                    /* TF_* */
    uint8_t dir;                      /* DIR_* (303 tracks; drums always play forward) */
    union {
        struct {
            uint32_t hit[NDSND][NSW]; /* step s (sm_get): the sound plays */
            uint32_t acc[NSW];        /* accent row: every sound on that step plays accented */
        } d;
        struct {
            bstep_t step[NSTEPS];
            uint8_t transpose;        /* semitones + 24 (24 = none), applied when played */
            uint8_t arp;              /* ARP_* */
            uint8_t arp_div;          /* notes a step - 1 (0..3) */
            uint8_t arp_oct;          /* octaves - 1 (0..2) */
        } b;
    } u;
} tpart_t;

typedef struct {
    tpart_t t[NTRK];
    uint8_t swing;                    /* unused: the swing is global (seq.swing, saved in the settings) */
    uint8_t rsv[3];
} pattern_t;

static inline int bstep_gate(const bstep_t *s) { return s->flags & BS_GATE_MASK; }
static inline int bstep_chord(const bstep_t *s) { return s->flags >> BS_CHORD_SHIFT; }

/* a row of steps (NSW words): step s */
static inline int sm_get(const uint32_t *m, int s) { return (int)((m[s >> 5] >> (s & 31)) & 1u); }
static inline void sm_flip(uint32_t *m, int s) { m[s >> 5] ^= 1u << (s & 31); }
static inline void sm_set(uint32_t *m, int s) { m[s >> 5] |= 1u << (s & 31); }
static inline void sm_clr(uint32_t *m, int s) { m[s >> 5] &= ~(1u << (s & 31)); }

/* an empty track of type tt: 16 steps of 1/16, no hits, 303 notes resting on C2 */
void gpat_track_clear(tpart_t *t, int tt);
/* an empty pattern for these track types: every track as gpat_track_clear, swing 0 */
void gpat_init(pattern_t *p, const uint8_t *types);
