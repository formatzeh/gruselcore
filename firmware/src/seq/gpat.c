/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore pattern model; see gpat.h. */
#include "gpat.h"

void gpat_track_clear(tpart_t *t, int tt)
{
    uint8_t *b = (uint8_t *)t;
    unsigned i;
    for (i = 0; i < sizeof *t; i++)
        b[i] = 0;
    t->len = 16;
    t->rate = RATE_16;
    t->dir = DIR_FWD;
    if (tt_notes(tt)) {
        for (i = 0; i < NSTEPS; i++)
            t->u.b.step[i].note = 36;             /* C2, resting */
        t->u.b.transpose = 24;
    }
}

void gpat_init(pattern_t *p, const uint8_t *types)
{
    int k;
    for (k = 0; k < NTRK; k++)
        gpat_track_clear(&p->t[k], types[k]);
    p->swing = 0;
    p->rsv[0] = p->rsv[1] = p->rsv[2] = 0;
}

/* the chords a step can play: built for the genres (fifths and octaves for basses and stabs, minor
 * and suspended colours, the Phrygian b2 of dark psy) */
const chord_t gp_chords[NCHORDS] = {
    {"-", {0, -1, -1, -1}},   {"OCT", {0, 12, -1, -1}},  {"5TH", {0, 7, -1, -1}},  {"5+8", {0, 7, 12, -1}},
    {"MIN", {0, 3, 7, -1}},   {"MAJ", {0, 4, 7, -1}},    {"SUS2", {0, 2, 7, -1}},  {"SUS4", {0, 5, 7, -1}},
    {"MIN7", {0, 3, 7, 10}},  {"MAJ7", {0, 4, 7, 11}},   {"DOM7", {0, 4, 7, 10}},  {"MIN9", {0, 3, 7, 14}},
    {"ADD9", {0, 4, 7, 14}},  {"DIM", {0, 3, 6, -1}},    {"AUG", {0, 4, 8, -1}},   {"PHRYG", {0, 1, 7, -1}},
};

int gp_chord_notes(int root, int chord, uint8_t *out)
{
    const chord_t *c = &gp_chords[chord & (NCHORDS - 1)];
    int i, n = 0;
    for (i = 0; i < CHORD_NMAX && c->iv[i] >= 0; i++) {
        int x = root + c->iv[i];
        out[n++] = (uint8_t)(x < 0 ? 0 : x > 127 ? 127 : x);
    }
    return n;
}
