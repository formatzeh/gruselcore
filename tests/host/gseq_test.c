/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore sequencer on the host: timing, lengths, types, the bar, cues, 303 gates, swing, mutes. */
#include <stdio.h>
#include <string.h>
#include "../../firmware/src/seq/gseq.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); fails++; } } while (0)

#define MAXEV 4096
typedef struct { uint32_t at; char kind; int trk, a, b; } ev_t;   /* kind: d drum, n note on, o note off */
static ev_t ev[MAXEV];
static int nev;
static uint32_t now;

static int s_drum(void *c, int t, int v, float vel) { (void)c; if (nev < MAXEV) ev[nev++] = (ev_t){now, 'd', t, v, vel >= 0.99f}; return 1; }
static void s_on(void *c, int t, int n, int acc, int sl) { (void)c; if (nev < MAXEV) ev[nev++] = (ev_t){now, 'n', t, n, acc | sl << 1}; }
static void s_off(void *c, int t) { (void)c; if (nev < MAXEV) ev[nev++] = (ev_t){now, 'o', t, 0, 0}; }
static const seq_sink_t SINK = {s_drum, s_on, s_off, 0, 0, 0};

static pattern_t pat[NPAT];
static seq_t seq;

static void run(uint32_t samples)
{
    uint32_t end = now + samples;
    gseq_advance(&seq, 0, &SINK);                           /* as the engine does at each block's start */
    while (now < end) {
        uint32_t k = gseq_until_event(&seq, end - now > 64 ? 64 : end - now);
        now += k;
        gseq_advance(&seq, k, &SINK);
    }
}

static void setup(const uint8_t *types, float bpm)
{
    int p, t;
    for (p = 0; p < NPAT; p++)
        gpat_init(&pat[p], types);
    gseq_init(&seq, pat);
    for (t = 0; t < NTRK; t++)
        seq.ttype[t] = types[t];
    seq.bpm = bpm;
    seq.send_clock = 0;
    nev = 0;
    now = 0;
}

static int count(char kind, int trk, int a)
{
    int i, n = 0;
    for (i = 0; i < nev; i++)
        if (ev[i].kind == kind && ev[i].trk == trk && (a < 0 || ev[i].a == a))
            n++;
    return n;
}

int main(void)
{
    static const uint8_t TYPES[NTRK] = {TT_DRUM, TT_DRUM, TT_303, TT_303, TT_OFF, TT_OFF, TT_OFF, TT_OFF};
    const uint32_t step = 44100u * 60u / 120u / 4u;        /* a 16th at 120 BPM: 5512.5 samples */
    int i;

    /* four on the floor: 16 steps, kick on 0 4 8 12, sample accurate */
    setup(TYPES, 120.0f);
    for (i = 0; i < 16; i += 4)
        sm_set(pat[0].t[0].u.d.hit[0], i);
    gseq_start(&seq);
    run(step * 16 - 10);
    CHECK(count('d', 0, 0) == 4, "kick hits %d, want 4", count('d', 0, 0));
    for (i = 0; i < nev; i++)
        if (ev[i].kind == 'd') {
            uint32_t want = (uint32_t)((double)ev[i].at / 5512.5 + 0.5) * 5512.5 + 0.5;
            CHECK(ev[i].at - want + 1 <= 2, "hit at %u, grid %u", ev[i].at, want);
        }

    /* polymeter: track 1 is 12 steps with a hit on step 0; over 4 bars (64 sixteenths) it plays 6 times */
    setup(TYPES, 120.0f);
    pat[0].t[1].len = 12;
    sm_set(pat[0].t[1].u.d.hit[3], 0);
    gseq_start(&seq);
    run(step * 64 - 10);
    CHECK(count('d', 1, 3) == 6, "12-step track played %d times in 4 bars, want 6", count('d', 1, 3));

    /* 64 steps: a hit on step 40 plays once in 4 bars */
    setup(TYPES, 120.0f);
    pat[0].t[0].len = 64;
    sm_set(pat[0].t[0].u.d.hit[1], 40);
    gseq_start(&seq);
    run(step * 64 - 10);
    CHECK(count('d', 0, 1) == 1, "step 40 of 64 played %d times", count('d', 0, 1));

    /* a cue lands on the bar and restarts every track from step 1 */
    setup(TYPES, 120.0f);
    pat[0].t[0].len = 64;                                   /* pattern 1: a long track, hit on step 20 */
    sm_set(pat[0].t[0].u.d.hit[0], 20);
    sm_set(pat[1].t[0].u.d.hit[2], 0);                      /* pattern 2: a clap on step 1 */
    gseq_start(&seq);
    run(step * 6);
    gseq_cue(&seq, 1);
    run(step * 9);                                          /* still in bar 1 */
    CHECK(seq.tpat[0] == 0 && count('d', 0, 2) == 0, "the cue took over before the bar's end");
    run(step * 2);                                          /* past the bar line */
    CHECK(seq.tpat[0] == 1 && seq.tpat[5] == 1, "the cue did not take over at the bar (track 1 on %d)", seq.tpat[0]);
    CHECK(count('d', 0, 2) == 1, "pattern 2's first step did not fire at the bar");
    for (i = 0; i < nev; i++)
        if (ev[i].kind == 'd' && ev[i].a == 2)
            CHECK(ev[i].at >= 88199u && ev[i].at <= 88201u, "pattern 2 started at %u, want 88200 (a bar at 120 BPM)", ev[i].at);
    CHECK(count('d', 0, 0) == 0, "pattern 1's step 20 played after the change");

    /* one track cued on its own: it switches at the bar and restarts; the others keep their steps */
    setup(TYPES, 120.0f);
    pat[0].t[0].len = 64;
    sm_set(pat[0].t[0].u.d.hit[0], 20);                     /* track 1, pattern 1: step 21 */
    pat[0].t[1].len = 32;
    sm_set(pat[0].t[1].u.d.hit[1], 20);                     /* track 2, pattern 1: step 21 */
    sm_set(pat[3].t[1].u.d.hit[4], 0);                      /* track 2, pattern 4: step 1 */
    gseq_start(&seq);
    run(step * 4);
    gseq_cue_track(&seq, 1, 3);
    CHECK(gseq_cue_of(&seq, 1) == 3 && gseq_cue_of(&seq, 0) == -1, "per-track cue not stored");
    run(step * 18);                                         /* past the bar, into bar 2 (step 21 of track 1) */
    CHECK(seq.tpat[1] == 3 && seq.tpat[0] == 0, "track 2 should be on pattern 4, track 1 on 1 (%d, %d)", seq.tpat[1], seq.tpat[0]);
    CHECK(count('d', 1, 4) == 1, "track 2's new pattern did not start at the bar");
    CHECK(count('d', 1, 1) == 0, "track 2's old step 21 played after its switch");
    CHECK(count('d', 0, 0) == 1, "track 1 did not keep running through the bar (its step 21)");

    /* stopped: a cue takes effect at once */
    setup(TYPES, 120.0f);
    gseq_cue(&seq, 5);
    run(64);
    CHECK(seq.tpat[3] == 5, "stopped cue not applied");

    /* 303: note, gate at half a step, slide, tie */
    setup(TYPES, 120.0f);
    {
        bstep_t *b = pat[0].t[2].u.b.step;
        b[0] = (bstep_t){40, G_NOTE};
        b[1] = (bstep_t){43, G_NOTE | BS_SLIDE};
        b[2] = (bstep_t){45, G_NOTE};                       /* slides in from 43 */
        b[3] = (bstep_t){45, G_TIE};                        /* held through */
        b[4] = (bstep_t){0, G_REST};
    }
    gseq_start(&seq);
    run(step * 5);
    {
        int on = 0, off = 0, slid = 0;
        uint32_t off0 = 0;
        for (i = 0; i < nev; i++) {
            if (ev[i].trk != 2)
                continue;
            if (ev[i].kind == 'n') {
                on++;
                if (ev[i].a == 45 && (ev[i].b & 2))
                    slid = 1;
            }
            if (ev[i].kind == 'o') {
                if (!off)
                    off0 = ev[i].at;
                off++;
            }
        }
        CHECK(on == 3, "303 note-ons %d, want 3 (the tie does not retrigger)", on);
        CHECK(slid, "the note after a slide step did not slide");
        CHECK(off0 > step / 2 - 3 && off0 < step / 2 + 3, "first gate fell at %u, want half a step (%u)", off0, step / 2);
        CHECK(off == 2, "303 note-offs %d, want 2 (after step 1, and at the tie's end)", off);
    }

    /* mute: no hits from a muted track; a type change to OFF silences it at the next step */
    setup(TYPES, 120.0f);
    for (i = 0; i < 16; i++)
        sm_set(pat[0].t[0].u.d.hit[0], i);
    seq.mute = 1u;
    gseq_start(&seq);
    run(step * 4);
    CHECK(count('d', 0, 0) == 0, "a muted track played");
    seq.mute = 0;
    run(step * 4);
    CHECK(count('d', 0, 0) == 4, "unmuted track: %d hits, want 4", count('d', 0, 0));
    seq.ttype[0] = TT_OFF;
    run(step * 4);
    CHECK(count('d', 0, 0) == 4, "a track switched OFF kept playing");

    /* a 303 track switched to DRUM while its note sounds lets the note go */
    setup(TYPES, 120.0f);
    pat[0].t[2].u.b.step[0] = (bstep_t){40, G_NOTE | BS_SLIDE};
    pat[0].t[2].u.b.step[1] = (bstep_t){40, G_TIE | BS_SLIDE};
    gseq_start(&seq);
    run(step / 2);
    seq.ttype[2] = TT_DRUM;
    run(step);
    CHECK(count('o', 2, -1) == 1, "the held 303 note was not let go on the type change");

    /* swing: odd 16ths late by the swing; a TF_NOSWING track straight */
    setup(TYPES, 120.0f);
    seq.swing = 100;                                        /* half a step late */
    sm_set(pat[0].t[0].u.d.hit[0], 1);
    sm_set(pat[0].t[1].u.d.hit[0], 1);
    pat[0].t[1].flags = TF_NOSWING;
    gseq_start(&seq);
    run(step * 3);
    for (i = 0; i < nev; i++)
        if (ev[i].kind == 'd') {
            uint32_t want = ev[i].trk == 0 ? step + step / 2 : step;
            CHECK(ev[i].at + 3 > want && ev[i].at < want + 3, "track %d swung step at %u, want %u", ev[i].trk, ev[i].at, want);
        }

    /* the step rates: 1/8 is two 16ths */
    setup(TYPES, 120.0f);
    pat[0].t[0].rate = RATE_8;
    for (i = 0; i < 16; i++)
        sm_set(pat[0].t[0].u.d.hit[0], i);
    gseq_start(&seq);
    run(step * 16 - 10);
    CHECK(count('d', 0, 0) == 8, "1/8 track: %d hits in a bar, want 8", count('d', 0, 0));

    /* stop lets every note go */
    setup(TYPES, 120.0f);
    pat[0].t[3].u.b.step[0] = (bstep_t){40, G_NOTE | BS_SLIDE};
    gseq_start(&seq);
    run(step / 2);
    gseq_stop(&seq);
    run(64);
    CHECK(count('o', 3, -1) == 1 && !seq.playing, "stop did not let the 303 go");

    printf(fails ? "gseq: %d FAILED\n" : "gseq: all checks passed\n", fails);
    return fails != 0;
}
