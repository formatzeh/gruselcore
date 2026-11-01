/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore drum engine on the host: every factory kit's 8 sounds rendered, checked and measured.
 *   checks: finite output, peak within headroom, every sound ends (goes inactive) within 5 s,
 *           a closed hat chokes a ringing open hat, pots clamp
 *   report: per sound the peak, the length to -60 dB, and for kicks the pitch at 1, 5, 20, 60 ms
 *   WAVs:   argv[1] (a directory), one file per kit: the 8 sounds one after another, 0.6 s apart */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../firmware/src/dsp/gdrum.h"

#define FS 44100
#define MAXN (FS * 5)

static float L[MAXN], R[MAXN];
static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL: " __VA_ARGS__); printf("\n"); fails++; } } while (0)

static int render_one(gdrum_t *d, int snd, float vel, int *len60, float *peak)
{
    int n = 0, last = 0;
    memset(L, 0, sizeof L);
    memset(R, 0, sizeof R);
    gdrum_trigger(d, snd, vel);
    while (n < MAXN && d->v[snd].active) {
        int k = MAXN - n < 64 ? MAXN - n : 64;
        gdrum_render_st(d, L + n, R + n, k);
        n += k;
    }
    *peak = 0.0f;
    for (int i = 0; i < n; i++) {
        float a = fabsf(L[i]) > fabsf(R[i]) ? fabsf(L[i]) : fabsf(R[i]);
        if (!isfinite(L[i]) || !isfinite(R[i]))
            return -1;
        if (a > *peak)
            *peak = a;
    }
    for (int i = 0; i < n; i++)
        if (fabsf(L[i]) + fabsf(R[i]) > 2e-3f * *peak)
            last = i;
    *len60 = last;
    return n;
}

/* the kick's oscillator pitch t ms after the trigger, from the voice's own pitch envelopes */
static float pitch_at(const gd_kit_t *kit, int snd, float ms)
{
    static float l[64], r[64];
    gdrum_t d;
    int n = (int)(ms * FS / 1000.0f);
    const gd_voice_t *v = &d.v[snd];
    gdrum_init(&d);
    gdrum_load_kit(&d, kit);
    gdrum_trigger(&d, snd, 1.0f);
    for (int i = 0; i < n; i++)
        gdrum_render_st(&d, l, r, 1);
    return 440.0f * powf(2.0f, (v->note_end + v->pitch_amt * v->e1 + v->body_amt * v->e2 - 69.0f) / 12.0f);
}

static void wav_write(const char *path, const float *l, const float *r, int n)
{
    FILE *f = fopen(path, "wb");
    int32_t data = n * 4, riff = 36 + data, fmt = 16, rate = FS, bps = FS * 4;
    int16_t pcm = 1, ch = 2, align = 4, bits = 16;
    if (!f)
        return;
    fwrite("RIFF", 1, 4, f); fwrite(&riff, 4, 1, f); fwrite("WAVEfmt ", 1, 8, f);
    fwrite(&fmt, 4, 1, f); fwrite(&pcm, 2, 1, f); fwrite(&ch, 2, 1, f); fwrite(&rate, 4, 1, f);
    fwrite(&bps, 4, 1, f); fwrite(&align, 2, 1, f); fwrite(&bits, 2, 1, f);
    fwrite("data", 1, 4, f); fwrite(&data, 4, 1, f);
    for (int i = 0; i < n; i++) {
        float s[2] = {l[i], r[i]};
        for (int c = 0; c < 2; c++) {
            float x = s[c] > 1.0f ? 1.0f : s[c] < -1.0f ? -1.0f : s[c];
            int16_t v = (int16_t)lrintf(x * 32767.0f);
            fwrite(&v, 2, 1, f);
        }
    }
    fclose(f);
}

int main(int argc, char **argv)
{
    static gdrum_t d;
    static float wl[FS * 5], wr[FS * 5];
    const char *dir = argc > 1 ? argv[1] : 0;
    for (int k = 0; k < gd_nkits; k++) {
        int wn = 0;
        printf("%-12s", gd_kit_names[k]);
        memset(wl, 0, sizeof wl);
        memset(wr, 0, sizeof wr);
        for (int s = 0; s < GD_NSND; s++) {
            int len60, n;
            float peak;
            gdrum_init(&d);
            gdrum_load_kit(&d, &gd_kits[k]);
            n = render_one(&d, s, 1.0f, &len60, &peak);
            CHECK(n >= 0, "%s %s: not finite", gd_kit_names[k], gdrum_slot_name(s));
            CHECK(n < MAXN, "%s %s: still sounding after 5 s", gd_kit_names[k], gdrum_slot_name(s));
            CHECK(peak < 1.0f, "%s %s: peak %.2f", gd_kit_names[k], gdrum_slot_name(s), (double)peak);
            CHECK(peak > 0.05f, "%s %s: too quiet, peak %.3f", gd_kit_names[k], gdrum_slot_name(s), (double)peak);
            printf(" %s %.2f/%dms", gdrum_slot_name(s), (double)peak, len60 * 1000 / FS);
            for (int i = 0; i < FS * 6 / 10 && i < n; i++) {
                wl[wn + i] = L[i];
                wr[wn + i] = R[i];
            }
            wn += FS * 6 / 10;
        }
        printf("\n");
        if (gd_kits[k].pot[GD_KICK][GP_MODEL] == GDM_KICK)
            printf("             kick pitch: %.0f Hz at 1 ms, %.0f at 5, %.0f at 20, %.0f at 60\n",
                   (double)pitch_at(&gd_kits[k], GD_KICK, 1), (double)pitch_at(&gd_kits[k], GD_KICK, 5),
                   (double)pitch_at(&gd_kits[k], GD_KICK, 20), (double)pitch_at(&gd_kits[k], GD_KICK, 60));
        if (dir) {
            char path[512], name[64];
            int j = 0;
            for (const char *c = gd_kit_names[k]; *c && j < 60; c++)
                name[j++] = *c == ' ' ? '_' : (char)(*c | 0x20);
            name[j] = 0;
            snprintf(path, sizeof path, "%s/kit_%02d_%s.wav", dir, k + 1, name);
            wav_write(path, wl, wr, wn);
        }
    }
    /* the closed hat chokes the open one */
    {
        int n;
        gdrum_init(&d);
        gdrum_trigger(&d, GD_OHAT, 1.0f);
        memset(L, 0, sizeof L);
        gdrum_render_st(&d, L, R, 2048);
        gdrum_trigger(&d, GD_CHAT, 1.0f);
        for (n = 0; n < FS && d.v[GD_OHAT].active; n += 64)
            gdrum_render_st(&d, L, R, 64);
        CHECK(!d.v[GD_OHAT].active && n < FS / 4, "the closed hat did not choke the open hat (%d samples)", n);
    }
    /* pots clamp */
    gdrum_init(&d);
    gdrum_set(&d, 0, GP_CURVE, 99);
    CHECK(gdrum_get(&d, 0, GP_CURVE) == GDC_N - 1, "CURVE did not clamp");
    gdrum_set(&d, 0, GP_LEVEL, 300);
    CHECK(gdrum_get(&d, 0, GP_LEVEL) == 127, "LEVEL did not clamp");
    printf(fails ? "gdrum: %d FAILED\n" : "gdrum: all checks passed\n", fails);
    return fails != 0;
}
