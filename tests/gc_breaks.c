/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) SLICE's built-in loops from GruselCore's own kits (in place of Skiff's drum takes):
 *   break.wav  BREAK: a Jungle break, the JUNGLE KIT, one bar at 120 BPM (44100 samples at 22050 Hz)
 *   funk.wav   FUNK:  a Drum and Bass loop, the DNB KIT, two beats at 86.33 BPM (30650 samples at 22050 Hz)
 * Rendered with the DRUM engine's own voice (gc_drum.c) at 44.1 kHz, halved to 22050 Hz (a 2-tap average), mono,
 * the peak at -0.5 dBFS; tools/gen_samples.py encodes them as it did Skiff's.
 *   build/host/gc_breaks assets/breaks          (cc -O2 -w -Ibuild/gen -Ifirmware/src tests/gc_breaks.c -lm) */
#define main hostsim_main
#include "hostsim.c"
#undef main

typedef struct { uint8_t step, lane, vel; } hit_t;

static int kit_of(const char *name)
{
    uint32_t k;
    for (k = 0; k < GC_NKITS; k++)
        if (!strcmp(GC_KITS[k].name, name))
            return (int)k;
    return 0;
}

/* steps of 1/16 at bpm, n44 samples at 44.1 kHz rendered, out at 22050 Hz */
static int render(const char *path, const char *kit, float bpm, uint32_t n22, const hit_t *h, uint32_t nh)
{
    static gcd_coef_t c[GCD_NSND];
    static gcd_voice_t v[GCD_NSND];
    static int32_t mix[2 * 44100 * 2 + 64], y[GCD_SUB];
    static int16_t out[44100 * 2];
    uint32_t n44 = n22 * 2u, i, j, k = (uint32_t)kit_of(kit), l;
    double step = 44100.0 * 60.0 / bpm / 4.0;
    int32_t peak = 1;
    FILE *f;
    memset(mix, 0, sizeof mix);
    memset(v, 0, sizeof v);
    for (l = 0; l < GCD_NSND; l++)
        gcd_setup(&c[l], GC_KITS[k].pot[l], 0, 64, 64, 64);
    for (i = 0; i + GCD_SUB <= n44; i += GCD_SUB) {
        for (j = 0; j < nh; j++)
            if ((uint32_t)(h[j].step * step) / GCD_SUB * GCD_SUB == i) {
                if (h[j].lane == 3 && v[4].live)
                    gcd_choke(&v[4]);
                gcd_trigger(&v[h[j].lane], &c[h[j].lane], h[j].vel * 258);
            }
        for (l = 0; l < GCD_NSND; l++) {
            uint32_t q;
            gcd_run(&v[l], &c[l], y, GCD_SUB);
            for (q = 0; q < GCD_SUB; q++)
                mix[i + q] += y[q];
        }
    }
    for (i = 0; i < n22; i++) {
        int32_t s = (mix[2 * i] + mix[2 * i + 1]) / 2;
        mix[i] = s;
        if (abs(s) > peak)
            peak = abs(s);
    }
    for (i = 0; i < n22; i++)
        out[i] = (int16_t)((int64_t)mix[i] * 30934 / peak);   /* -0.5 dBFS */
    f = fopen(path, "wb");
    if (!f)
        return 1;
    wav_hdr(f, n22);   /* (hostsim's: stereo 44.1 kHz) rewritten below as mono 22050 Hz */
    fseek(f, 0, SEEK_SET);
    {
        uint32_t d = n22 * 2u, riff = 36u + d, fmt = 16u, rate = 22050u, bps = 44100u;
        uint16_t pcm = 1, ch = 1, ba = 2, bits = 16;
        fwrite("RIFF", 1, 4, f); fwrite(&riff, 4, 1, f); fwrite("WAVEfmt ", 1, 8, f); fwrite(&fmt, 4, 1, f);
        fwrite(&pcm, 2, 1, f); fwrite(&ch, 2, 1, f); fwrite(&rate, 4, 1, f); fwrite(&bps, 4, 1, f);
        fwrite(&ba, 2, 1, f); fwrite(&bits, 2, 1, f); fwrite("data", 1, 4, f); fwrite(&d, 4, 1, f);
    }
    fwrite(out, 2, n22, f);
    fclose(f);
    printf("%s: %s, %u samples at 22050 Hz, %u hits\n", path, kit, n22, nh);
    return 0;
}

int main(int argc, char **argv)
{
    /* a Jungle break: kick 1 3 11 12, snare 5 13 with ghosts, the ride on the eighths, an open hat on the and of 4 */
    static const hit_t BRK[] = {
        {0, 0, 120}, {2, 0, 100}, {10, 0, 110}, {11, 0, 90},
        {4, 1, 127}, {7, 1, 55}, {9, 1, 60}, {12, 1, 127}, {14, 1, 50}, {15, 1, 70},
        {0, 7, 70}, {2, 7, 60}, {4, 7, 70}, {6, 7, 60}, {8, 7, 70}, {10, 7, 60}, {12, 7, 70},
        {1, 3, 45}, {3, 3, 50}, {5, 3, 45}, {9, 3, 45}, {11, 3, 50}, {13, 3, 45}, {14, 4, 70},
    };
    /* a Drum and Bass loop, two beats: kick 1, snare on 2, hats on the sixteenths, a ghost kick */
    static const hit_t DNB[] = {
        {0, 0, 127}, {6, 0, 90}, {4, 1, 127}, {7, 1, 50},
        {0, 3, 70}, {1, 3, 45}, {2, 3, 80}, {3, 3, 45}, {4, 3, 70}, {5, 3, 45}, {6, 4, 80},
    };
    const char *dir = argc > 1 ? argv[1] : "assets/breaks";
    char p[512];
    snprintf(p, sizeof p, "%s/break.wav", dir);
    if (render(p, "JUNGLE KIT", 120.0f, 44100u, BRK, NELEM(BRK)))
        return 1;
    snprintf(p, sizeof p, "%s/funk.wav", dir);
    return render(p, "DNB KIT", 86.33f, 30650u, DNB, NELEM(DNB));
}
