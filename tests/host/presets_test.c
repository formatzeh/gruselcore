/* SPDX-License-Identifier: GPL-3.0-only */
/* Every VA and 303 preset at the drum kits' loudness (-16 dB, K-weighted, the loudest 100 ms; within
 * 1.5 dB), finite and with sane peaks. The VA as gva_test plays it (a note, a minor triad in CHORD
 * mode, held 1.5 s); the 303 as gdrum_test does (eighth notes over a fifth, through B303_GAIN).
 *   presets_test [measure]   measure: print "va:NAME dB" / "303:NAME dB" lines, no checks */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "../../firmware/src/dsp/gva.h"
#include "../../firmware/src/dsp/bass303.h"
#include "../../firmware/src/app/gengine.h"   /* B303_GAIN */
#include "loudness.h"

#undef FS
#define FS 44100
#define TARGET_DB (-16.0)
static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL: " __VA_ARGS__); printf("\n"); fails++; } } while (0)
static float a[FS * 4];
static gva_t va;
static bass303_t bs;

static int va_note(const char *n) { return strstr(n, "BASS") || strstr(n, " BS") || strstr(n, "RUMBL") || strstr(n, "ROLLER") ? 36 : strstr(n, "ACID") ? 43 : 57; }

int main(int argc, char **argv)
{
    int measure = argc > 1;
    (void)argv;
    for (int k = 0; k < gva_npresets; k++) {
        uint8_t nt[3];
        int n = va_note(gva_presets[k].name), bad = 0;
        float pk = 0.0f;
        double lu;
        gva_init(&va);
        for (int i = 0; i < VA_N; i++)
            gva_set(&va, i, gva_presets[k].pot[i]);
        nt[0] = (uint8_t)n, nt[1] = (uint8_t)(n + 3), nt[2] = (uint8_t)(n + 7);
        gva_note_on(&va, nt, va.pot[VA_MODE] == VAM_CHORD ? 3 : 1, 0, 0);
        gva_render(&va, a, FS * 3 / 2);
        gva_note_off(&va);
        gva_render(&va, a + FS * 3 / 2, FS * 5 / 2);
        for (int i = 0; i < FS * 4; i++) {
            if (!isfinite(a[i])) bad++;
            else if (fabsf(a[i]) > pk) pk = fabsf(a[i]);
        }
        lu = loudness_db(a, a, FS * 4);
        printf("va:%s %.2f %.2f\n", gva_presets[k].name, lu, pk);
        if (!measure) {
            CHECK(!bad && pk < 1.9f, "VA %s: peak %.2f, %d not finite", gva_presets[k].name, pk, bad);
            CHECK(fabs(lu - TARGET_DB) <= 1.5, "VA %s: loudness %.1f dB, want %.1f", gva_presets[k].name, lu, TARGET_DB);
            CHECK(va.idle, "VA %s: still sounding 2.5 s after its release", gva_presets[k].name);
        }
    }
    for (int k = 0; k < b303_npresets; k++) {
        int bad = 0;
        float pk = 0.0f;
        double lu;
        memset(a, 0, sizeof a);
        bass303_init(&bs);
        for (int i = 0; i < bass303_nparams(); i++)
            bass303_set(&bs, i, b303_presets[k].pot[i]);
        for (int j = 0; j < 8; j++) {
            bass303_note_on(&bs, 36 + (j % 3) * 7, j % 4 == 0, 0);
            bass303_render(&bs, a + j * 5512, 2756);
            bass303_note_off(&bs);
            bass303_render(&bs, a + j * 5512 + 2756, 2756);
        }
        for (int i = 0; i < FS; i++) {
            a[i] *= B303_GAIN;
            if (!isfinite(a[i])) bad++;
            else if (fabsf(a[i]) > pk) pk = fabsf(a[i]);
        }
        lu = loudness_db(a, a, FS);
        printf("303:%s %.2f %.2f\n", b303_presets[k].name, lu, pk);
        if (!measure) {
            CHECK(!bad && pk < 2.5f, "303 %s: peak %.2f, %d not finite", b303_presets[k].name, pk, bad);
            CHECK(fabs(lu - TARGET_DB) <= 1.5, "303 %s: loudness %.1f dB, want %.1f", b303_presets[k].name, lu, TARGET_DB);
        }
    }
    printf(fails ? "presets: %d FAILED\n" : "presets: ok\n", fails);
    return fails != 0;
}
