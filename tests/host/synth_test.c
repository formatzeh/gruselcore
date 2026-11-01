/* SPDX-License-Identifier: GPL-3.0-only */
/* FM and PHYS: finite and bounded for every preset with every pot at 0 and at its max; idle when
 * untouched; FM's slide glides without a new attack, its CHORD plays up to three notes; PHYS's chord
 * strums, its legato changes the pitch without a new strike. */
#include <stdio.h>
#include <math.h>
#include "../../firmware/src/dsp/gfm.h"
#include "../../firmware/src/dsp/gphys.h"

#define FS 44100
static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL: " __VA_ARGS__); printf("\n"); fails++; } } while (0)
static gfm_t fm;
static gphys_t ph;
static float buf[FS * 2];

static float peak(int n, int *bad)
{
    float p = 0.0f;
    for (int i = 0; i < n; i++) {
        if (!isfinite(buf[i])) (*bad)++;
        else if (fabsf(buf[i]) > p) p = fabsf(buf[i]);
    }
    return p;
}

int main(void)
{
    static const uint8_t nt[3] = {48, 51, 55};
    for (int k = 0; k < gfm_npresets; k++)
        for (int i = 0; i < FM_N; i++)
            for (int e = 0; e < 2; e++) {
                int bad = 0;
                float pk;
                gfm_init(&fm);
                for (int j = 0; j < FM_N; j++)
                    gfm_set(&fm, j, gfm_presets[k].pot[j]);
                gfm_set(&fm, i, e ? gfm_param(i)->max : 0);
                gfm_note_on(&fm, nt, 3, 1, 0);
                gfm_render(&fm, buf, FS / 2);
                gfm_note_off(&fm);
                gfm_render(&fm, buf + FS / 2, FS / 2);
                pk = peak(FS, &bad);
                CHECK(!bad && pk < 4.0f, "FM %s, %s = %d: peak %.2f, %d not finite", gfm_presets[k].name,
                      gfm_param(i)->name, e ? gfm_param(i)->max : 0, pk, bad);
            }
    for (int k = 0; k < gphys_npresets; k++)
        for (int i = 0; i < PH_N; i++)
            for (int e = 0; e < 2; e++) {
                int bad = 0;
                float pk;
                gphys_init(&ph);
                for (int j = 0; j < PH_N; j++)
                    gphys_set(&ph, j, gphys_presets[k].pot[j]);
                gphys_set(&ph, i, e ? gphys_param(i)->max : 0);
                gphys_note_on(&ph, nt, 3, 1, 0);
                for (int j = 0; j < FS / 2; j += 128)
                    gphys_render(&ph, buf + j, 128);
                gphys_note_off(&ph);
                for (int j = FS / 2; j < FS; j += 128)
                    gphys_render(&ph, buf + j, 128);
                pk = peak(FS, &bad);
                CHECK(!bad && pk < 4.0f, "PHYS %s, %s = %d: peak %.2f, %d not finite", gphys_presets[k].name,
                      gphys_param(i)->name, e ? gphys_param(i)->max : 0, pk, bad);
            }
    {   /* FM: slide and chord */
        uint8_t a = 36, b = 48;
        gfm_init(&fm);
        gfm_note_on(&fm, &a, 1, 0, 0);
        gfm_render(&fm, buf, 4410);
        gfm_note_on(&fm, &b, 1, 0, 1);
        gfm_render(&fm, buf, 300);
        CHECK(fm.v[0].note > 36.5f && fm.v[0].note < 47.5f, "FM slide: note %.2f", fm.v[0].note);
        CHECK(fm.st == 2, "FM slide: a new attack (stage %d)", fm.st);
        gfm_set(&fm, FM_MODE, FMM_CHORD);
        gfm_note_on(&fm, nt, 3, 0, 0);
        CHECK(fm.nv == 3, "FM chord: %d notes", fm.nv);
        gfm_set_lite(&fm, 1);
        gfm_note_on(&fm, nt, 3, 0, 0);
        CHECK(fm.nv == 1, "FM light: %d notes", fm.nv);
    }
    {   /* PHYS: idle, the strum, legato */
        int bad = 0;
        gphys_init(&ph);
        gphys_render(&ph, buf, 256);
        CHECK(ph.idle && peak(256, &bad) == 0.0f, "PHYS idle: silent");
        gphys_set(&ph, PH_MODE, PHV_CHORD);
        gphys_set(&ph, PH_STRUM, 127);
        gphys_note_on(&ph, nt, 3, 0, 0);
        CHECK(ph.v[1].delay > 0 && ph.v[2].delay > ph.v[1].delay, "PHYS strum: %d, %d", ph.v[1].delay, ph.v[2].delay);
        gphys_set(&ph, PH_MODE, PHV_MONO);
        gphys_note_on(&ph, nt, 1, 0, 0);
        gphys_render(&ph, buf, 256);
        {
            uint8_t up = 60;
            float l0 = ph.v[0].len;
            gphys_note_on(&ph, &up, 1, 0, 1);
            CHECK(ph.v[0].len < l0 * 0.6f && ph.v[0].exc_left == 0, "PHYS legato: len %.1f -> %.1f, burst %d", l0, ph.v[0].len, ph.v[0].exc_left);
        }
    }
    printf(fails ? "synth: %d FAILED\n" : "synth: ok\n", fails);
    return fails != 0;
}
