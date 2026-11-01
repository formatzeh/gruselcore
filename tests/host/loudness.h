/* SPDX-License-Identifier: GPL-3.0-only */
/* Loudness of a single sound, as the ear hears a hit: the signal K-weighted (ITU-R BS.1770's two
 * filters, computed for 44.1 kHz), then the highest mean square over any 100 ms window, in dB.
 * 100 ms rather than BS.1770's 400 ms: a hit of 20 ms and a kick of 400 ms are compared as they are
 * heard one at a time, not as averages over silence. Mono (the mean of L and R). */
#pragma once
#include <math.h>
#include <stdlib.h>

typedef struct { double b0, b1, b2, a1, a2, z1, z2; } lu_bq_t;
static double lu_bq(lu_bq_t *f, double x)
{
    double y = f->b0 * x + f->z1;
    f->z1 = f->b1 * x - f->a1 * y + f->z2;
    f->z2 = f->b2 * x - f->a2 * y;
    return y;
}
static void lu_shelf(lu_bq_t *f, double fs)          /* stage 1: +4 dB high shelf at 1682 Hz */
{
    double A = pow(10.0, 3.99984 / 40.0), w = 2.0 * M_PI * 1681.974 / fs, cw = cos(w), sw = sin(w);
    double al = sw / (2.0 * 0.7071752), sA = 2.0 * sqrt(A) * al, a0 = (A + 1) - (A - 1) * cw + sA;
    f->b0 = A * ((A + 1) + (A - 1) * cw + sA) / a0;
    f->b1 = -2 * A * ((A - 1) + (A + 1) * cw) / a0;
    f->b2 = A * ((A + 1) + (A - 1) * cw - sA) / a0;
    f->a1 = 2 * ((A - 1) - (A + 1) * cw) / a0;
    f->a2 = ((A + 1) - (A - 1) * cw - sA) / a0;
    f->z1 = f->z2 = 0;
}
static void lu_hp(lu_bq_t *f, double fs)             /* stage 2: high-pass at 38 Hz */
{
    double w = 2.0 * M_PI * 38.135 / fs, cw = cos(w), al = sin(w) / (2.0 * 0.5003), a0 = 1 + al;
    f->b0 = (1 + cw) / 2 / a0;
    f->b1 = -(1 + cw) / a0;
    f->b2 = (1 + cw) / 2 / a0;
    f->a1 = -2 * cw / a0;
    f->a2 = (1 - al) / a0;
    f->z1 = f->z2 = 0;
}
/* l, r: n samples at 44.1 kHz; returns dB (0 dB = a full-scale K-weighted mean square of 1) */
static double loudness_db(const float *l, const float *r, int n)
{
    lu_bq_t a, b;
    const int win = 4410;
    double *sq = malloc(sizeof(double) * (size_t)(n > 0 ? n : 1)), acc = 0, best = 1e-12;
    int i;
    lu_shelf(&a, 44100.0);
    lu_hp(&b, 44100.0);
    for (i = 0; i < n; i++) {
        double x = lu_bq(&b, lu_bq(&a, 0.5 * ((double)l[i] + (double)r[i])));
        sq[i] = x * x;
        acc += sq[i];
        if (i >= win)
            acc -= sq[i - win];
        if (acc / win > best)
            best = acc / win;
    }
    free(sq);
    return 10.0 * log10(best);
}
