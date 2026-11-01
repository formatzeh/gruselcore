/* SPDX-License-Identifier: GPL-3.0-only */
/* Every synth preset (303, VA, FM, PHYS) at the drum kits' loudness (-16 dB, K-weighted, the loudest
 * 100 ms; within 1.5 dB), finite, with sane peaks, and silent again after its release. The VA, FM and
 * PHYS: a note (a minor triad in CHORD mode) held 1.5 s, at a pitch for its kind (basses low); the 303
 * as gdrum_test plays it (eighth notes over a fifth, through B303_GAIN).
 *   presets_test [measure]   measure: print the "engine:NAME dB peak" lines only, no checks */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "../../firmware/src/dsp/gva.h"
#include "../../firmware/src/dsp/gfm.h"
#include "../../firmware/src/dsp/gphys.h"
#include "../../firmware/src/dsp/bass303.h"
#include "../../firmware/src/app/gengine.h"   /* B303_GAIN */
#include "loudness.h"

#undef FS
#define FS 44100
#define TARGET_DB (-16.0)
static int fails, measure;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL: " __VA_ARGS__); printf("\n"); fails++; } } while (0)
static float a[FS * 4];
static gva_t va;
static gfm_t fm;
static gphys_t ph;
static bass303_t bs;

static int note_of(int cat) { return cat == CAT_BASS ? 36 : cat == CAT_ACID ? 43 : cat == CAT_PERC ? 50 : 57; }

static void judge(const char *eng, const char *name, int n, float maxpk, int idle)
{
    int bad = 0;
    float pk = 0.0f;
    double lu;
    for (int i = 0; i < n; i++) {
        if (!isfinite(a[i])) bad++;
        else if (fabsf(a[i]) > pk) pk = fabsf(a[i]);
    }
    lu = loudness_db(a, a, n);
    printf("%s:%s %.2f %.2f\n", eng, name, lu, pk);
    if (measure)
        return;
    CHECK(!bad && pk < maxpk, "%s %s: peak %.2f, %d not finite", eng, name, pk, bad);
    CHECK(fabs(lu - TARGET_DB) <= 1.5, "%s %s: loudness %.1f dB, want %.1f", eng, name, lu, TARGET_DB);
    CHECK(idle, "%s %s: still sounding 2.5 s after its release", eng, name);
}

int main(int argc, char **argv)
{
    (void)argv;
    measure = argc > 1;
    for (int k = 0; k < gva_npresets; k++) {
        int n = note_of(gva_presets[k].cat);
        uint8_t nt[3] = {(uint8_t)n, (uint8_t)(n + 3), (uint8_t)(n + 7)};
        gva_init(&va);
        for (int i = 0; i < VA_N; i++)
            gva_set(&va, i, gva_presets[k].pot[i]);
        gva_note_on(&va, nt, va.pot[VA_MODE] == VAM_CHORD ? 3 : 1, 0, 0);
        gva_render(&va, a, FS * 3 / 2);
        gva_note_off(&va);
        gva_render(&va, a + FS * 3 / 2, FS * 5 / 2);
        judge("va", gva_presets[k].name, FS * 4, 1.9f, va.idle);
    }
    for (int k = 0; k < gfm_npresets; k++) {
        int n = note_of(gfm_presets[k].cat);
        uint8_t nt[3] = {(uint8_t)n, (uint8_t)(n + 3), (uint8_t)(n + 7)};
        gfm_init(&fm);
        for (int i = 0; i < FM_N; i++)
            gfm_set(&fm, i, gfm_presets[k].pot[i]);
        gfm_note_on(&fm, nt, fm.pot[FM_MODE] == FMM_CHORD ? 3 : 1, 0, 0);
        gfm_render(&fm, a, FS * 3 / 2);
        gfm_note_off(&fm);
        gfm_render(&fm, a + FS * 3 / 2, FS * 5 / 2);
        judge("fm", gfm_presets[k].name, FS * 4, 1.9f, fm.idle);
    }
    for (int k = 0; k < gphys_npresets; k++) {
        int n = note_of(gphys_presets[k].cat);
        uint8_t nt[3] = {(uint8_t)n, (uint8_t)(n + 3), (uint8_t)(n + 7)};
        gphys_init(&ph);
        for (int i = 0; i < PH_N; i++)
            gphys_set(&ph, i, gphys_presets[k].pot[i]);
        gphys_note_on(&ph, nt, ph.pot[PH_MODE] == PHV_CHORD ? 3 : 1, 0, 0);
        for (int j = 0; j < FS * 3 / 2; j += 256)
            gphys_render(&ph, a + j, FS * 3 / 2 - j < 256 ? FS * 3 / 2 - j : 256);
        gphys_note_off(&ph);
        for (int j = FS * 3 / 2; j < FS * 4; j += 256)
            gphys_render(&ph, a + j, FS * 4 - j < 256 ? FS * 4 - j : 256);
        judge("ph", gphys_presets[k].name, FS * 4, 1.9f, 1);   /* (a gong rings on: idle not required) */
    }
    for (int k = 0; k < b303_npresets; k++) {
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
        for (int i = 0; i < FS; i++)
            a[i] *= B303_GAIN;
        judge("303", b303_presets[k].name, FS, 2.5f, 1);
    }
    printf(fails ? "presets: %d FAILED\n" : "presets: ok\n", fails);
    return fails != 0;
}
