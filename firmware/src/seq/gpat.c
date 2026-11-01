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
    if (tt == TT_303) {
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
