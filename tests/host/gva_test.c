/* SPDX-License-Identifier: GPL-3.0-only */
/* The VA synth: finite and bounded for every preset and every pot at its extremes; a note ends after
 * its release; MONO slides glide, CHORD plays its notes, UNISON detunes; every preset at the drum kits'
 * loudness (-16 dB, within 1.5 dB). Writes each preset to OUT/va_NN.wav. */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "../../firmware/src/dsp/gva.h"
#include "loudness.h"

#define FS 44100
#define TARGET_DB (-16.0)
static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL: " __VA_ARGS__); printf("\n"); fails++; } } while (0)

static gva_t va;
static float buf[FS * 4], buf2[FS * 4];

static void load(int k)
{
    gva_init(&va);
    for (int i = 0; i < VA_N; i++)
        gva_set(&va, i, gva_presets[k].pot[i]);
}

/* the note each preset is heard at: basses low, the rest in the middle */
static int test_note(int k)
{
    const char *n = gva_presets[k].name;
    return strstr(n, "BASS") ? 36 : strstr(n, "ACID") ? 43 : 57;
}

/* a note (a minor triad for CHORD presets) held 1.5 s, released, 4 s in all */
static void play(int k, float *o)
{
    uint8_t nt[3];
    int n = test_note(k);
    nt[0] = (uint8_t)n;
    nt[1] = (uint8_t)(n + 3);
    nt[2] = (uint8_t)(n + 7);
    gva_note_on(&va, nt, va.pot[VA_MODE] == VAM_CHORD ? 3 : 1, 0, 0);
    gva_render(&va, o, FS * 3 / 2);
    gva_note_off(&va);
    gva_render(&va, o + FS * 3 / 2, FS * 5 / 2);
}

static void wav(const char *path, const float *x, int n)
{
    FILE *f = fopen(path, "wb");
    int32_t d = n * 2, riff = 36 + d, fmt = 16, rate = FS, bps = FS * 2;
    int16_t pcm = 1, ch = 1, ba = 2, bits = 16;
    if (!f)
        return;
    fwrite("RIFF", 1, 4, f); fwrite(&riff, 4, 1, f); fwrite("WAVEfmt ", 1, 8, f); fwrite(&fmt, 4, 1, f);
    fwrite(&pcm, 2, 1, f); fwrite(&ch, 2, 1, f); fwrite(&rate, 4, 1, f); fwrite(&bps, 4, 1, f);
    fwrite(&ba, 2, 1, f); fwrite(&bits, 2, 1, f); fwrite("data", 1, 4, f); fwrite(&d, 4, 1, f);
    for (int i = 0; i < n; i++) {
        float c = x[i] > 1.0f ? 1.0f : x[i] < -1.0f ? -1.0f : x[i];
        int16_t v = (int16_t)lrintf(c * 32767.0f);
        fwrite(&v, 2, 1, f);
    }
    fclose(f);
}

static float peak(const float *x, int n, int *bad)
{
    float p = 0.0f;
    for (int i = 0; i < n; i++) {
        if (!isfinite(x[i]))
            (*bad)++;
        else if (fabsf(x[i]) > p)
            p = fabsf(x[i]);
    }
    return p;
}

int main(int argc, char **argv)
{
    const char *out = argc > 1 ? argv[1] : 0;
    int measure = argc > 2;
    for (int k = 0; k < gva_npresets; k++) {
        int bad = 0;
        double lu;
        float pk;
        char path[256];
        load(k);
        play(k, buf);
        pk = peak(buf, FS * 4, &bad);
        lu = loudness_db(buf, buf, FS * 4);
        printf("%-13s %6.1f dB  peak %.2f%s\n", gva_presets[k].name, lu, pk, measure ? "" : "");
        CHECK(!bad, "%s: not finite", gva_presets[k].name);
        CHECK(pk < 1.8f, "%s: peak %.2f", gva_presets[k].name, pk);
        if (!measure)
            CHECK(fabs(lu - TARGET_DB) <= 1.5, "%s: loudness %.1f dB, want %.1f", gva_presets[k].name, lu, TARGET_DB);
        CHECK(va.idle, "%s: still sounding 2.5 s after its release", gva_presets[k].name);
        if (out) {
            snprintf(path, sizeof path, "%s/va_%02d.wav", out, k + 1);
            wav(path, buf, FS * 4);
        }
    }
    /* every pot at 0 and at its max, the rest the defaults and a preset: finite and bounded */
    for (int k = 0; k < gva_npresets; k++)
        for (int i = 0; i < VA_N; i++)
            for (int e = 0; e < 2; e++) {
                int bad = 0;
                float pk;
                load(k);
                gva_set(&va, i, e ? gva_param(i)->max : 0);
                play(k, buf);
                pk = peak(buf, FS * 2, &bad);
                CHECK(!bad && pk < 4.0f, "%s, %s = %d: peak %.2f, %d not finite", gva_presets[k].name,
                      gva_param(i)->name, e ? gva_param(i)->max : 0, pk, bad);
            }
    /* MONO: a slide glides (the pitch passes between), and does not retrigger the envelope */
    {
        uint8_t a = 36, b = 48;
        gva_init(&va);
        gva_set(&va, VA_CUTOFF, 127);
        gva_note_on(&va, &a, 1, 0, 0);
        gva_render(&va, buf, 4410);
        gva_note_on(&va, &b, 1, 0, 1);
        gva_render(&va, buf, 300);
        CHECK(va.v[0].note > 36.5f && va.v[0].note < 47.5f, "slide: note %.2f, want gliding", va.v[0].note);
        CHECK(va.aenv_st == 2, "slide: envelope retriggered (stage %d)", va.aenv_st);
        gva_render(&va, buf, 22050);
        CHECK(fabsf(va.v[0].note - 48.0f) < 0.01f, "slide: ends at %.2f", va.v[0].note);
        gva_note_on(&va, &a, 1, 0, 0);
        CHECK(va.aenv_st == 1 && va.v[0].note == 36.0f, "no slide, GLIDE 0: a jump and a new attack");
    }
    /* CHORD: three slots on the chord's notes, a fourth added by hand; MONO plays one */
    {
        uint8_t c[3] = {48, 52, 55};
        gva_init(&va);
        gva_set(&va, VA_MODE, VAM_CHORD);
        gva_note_on(&va, c, 3, 0, 0);
        CHECK(va.nv == 3 && va.v[2].target == 55.0f, "chord: %d slots", va.nv);
        gva_note_add(&va, 60);
        CHECK(va.nv == 4 && va.v[3].note == 60.0f, "chord: a note added (%d slots)", va.nv);
        gva_set_lite(&va, 1);
        gva_note_on(&va, c, 3, 0, 0);
        CHECK(va.nv == 1, "chord in the light mode: one slot (%d)", va.nv);
        gva_set(&va, VA_MODE, VAM_MONO);
        gva_set_lite(&va, 0);
        gva_note_on(&va, c, 3, 0, 0);
        CHECK(va.nv == 1 && va.v[0].target == 48.0f, "mono: the root");
    }
    /* UNISON: four slots spread around the note */
    {
        uint8_t n = 60;
        gva_init(&va);
        gva_set(&va, VA_MODE, VAM_UNISON);
        gva_set(&va, VA_DETUNE, 127);
        gva_note_on(&va, &n, 1, 0, 0);
        CHECK(va.nv == 4 && va.v[0].off < -0.5f && va.v[3].off > 0.5f, "unison: spread %.2f .. %.2f", va.v[0].off, va.v[3].off);
    }
    /* idle when untouched, silent output */
    {
        int bad = 0;
        gva_init(&va);
        gva_render(&va, buf2, 1000);
        CHECK(peak(buf2, 1000, &bad) == 0.0f && va.idle, "idle: silent");
    }
    printf(fails ? "gva: %d FAILED\n" : "gva: ok\n", fails);
    return fails != 0;
}
