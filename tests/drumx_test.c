/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
 * (Skiff, modified 2026-10-10) after tests/drumx_test.c of JIANT FM by juanjiant-bit,
 * https://github.com/juanjiant-bit/JIANT (GPL-3.0-only): its checks of the voice, on Skiff's DRUM-X engine. */
/* DRUM-X (src/drumx_voice.c, src/eng_drumx.c) on the host, through hostsim.c:
 *   build/host/drumx_test [DEMODIR]          (run_tests.sh: build/drumx_demo)
 * 1. every lane of the kit, struck through the engine (its GM note), sounds (peak above -30 dBFS), never at full
 *    scale, DC under 2 % of the peak, and ends: its voice frees itself within 3 s.
 * 2. MORPH (MRPH): 0 and 127 render different hits, 64 between them; moving it while a hit rings: no step larger
 *    than the hit's own at A or B (+20 %).
 * 3. PITCH: TUNE +12 semitones about doubles the tom; the kick's pitch envelope falls.
 * 4. the closed hat chokes the open one.
 * 5. the knobs: MRPH on KNOB 1, NOIS moves every lane's noise; FOLD 127 and FM 40 / 120 each another sound on every
 *    lane, under full scale, still ending.
 * 6. (Skiff) a drum track as DRUM's: drum_track, the GM map's lanes drum_lane's (every note), the lane names plain
 *    (DRUM's KIT swaps never apply), allowed on the light tracks; the project's kit the voice's (an edit is heard).
 * 7. demos into DEMODIR: every lane at MORPH 0, 64, 127; a beat with MORPH swept over 4 bars. */
#include <stdarg.h>
#define main hostsim_main
#include "hostsim.c"
#undef main

static int fails;
static void check(const char *what, int ok, const char *fmt, ...)
{
    printf("drumx: %-70s %s", what, ok ? "ok" : "FAIL");
    if (fmt) {
        va_list ap;
        va_start(ap, fmt);
        printf("  (");
        vprintf(fmt, ap);
        printf(")");
        va_end(ap);
    }
    printf("\n");
    fails += !ok;
}

#define MAXN (FS * 3u)
static int32_t buf[MAXN];
static const uint8_t NOTE[8] = {36, 38, 39, 42, 46, 45, 37, 56};   /* eng_drum.c DRUM_LANE_NOTE */

static track_t *kitx(int16_t morph, int16_t tune)
{
    track_t *t = &trk[0];
    uint32_t i;
    host_tracks_init();
    host_preset(t, ENGI_DRUMX, 0);
    t->p[P_E0] = morph;
    t->p[P_E1] = tune;
    for (i = 0; i < 4u; i++)
        t->p[P_DIST + i] = 0;
    return t;
}
static void run(uint32_t n)
{
    uint32_t i, k;
    for (k = 0; k < n; k += CTL) {
        int32_t o[2 * CTL];
        mix_block(o, CTL);
        for (i = 0; i < CTL && k + i < n; i++)
            buf[k + i] = o[2 * i];
    }
}
/* lane l struck, n samples of the left output into buf; 1 when a voice still sounds at the end */
static int strike(track_t *t, uint32_t l, uint32_t n)
{
    uint32_t i;
    trk_note_on(t, NOTE[l], 100);
    trk_note_off(t, NOTE[l]);
    run(n);
    for (i = 0; i < NVOICE; i++)
        if (t->v[i].active)
            return 1;
    return 0;
}
static double rms(uint32_t a, uint32_t b)
{
    double s = 0;
    uint32_t i;
    for (i = a; i < b; i++)
        s += (double)buf[i] * buf[i];
    return sqrt(s / (b - a));
}
static uint32_t crossings(uint32_t a, uint32_t b)
{
    uint32_t i, c = 0;
    for (i = a + 1; i < b; i++)
        c += buf[i - 1] < 0 && buf[i] >= 0;
    return c;
}
static int32_t maxstep(uint32_t n)
{
    int32_t s = 0;
    uint32_t i;
    for (i = 1; i < n; i++)
        s = abs(buf[i] - buf[i - 1]) > s ? abs(buf[i] - buf[i - 1]) : s;
    return s;
}
static void save(const char *dir, const char *name, uint32_t n)
{
    char path[512];
    FILE *f;
    uint32_t i;
    snprintf(path, sizeof path, "%s/%s", dir, name);
    if (!(f = fopen(path, "wb")))
        return;
    wav_hdr(f, n);
    for (i = 0; i < n; i++)
        wav_put(f, buf[i], buf[i]);
    fclose(f);
}

int main(int argc, char **argv)
{
    static const char *const NAME[8] = {"kick", "snare", "clap", "hatcl", "hatop", "tom", "rim", "bell"};
    const char *dir = argc > 1 ? argv[1] : "build/drumx_demo";
    char nm[96];
    uint32_t l, i;
    int ok;

    /* 1 */
    for (l = 0; l < 8u; l++) {
        track_t *t = kitx(64, 64);
        int32_t pk = 0;
        double dc = 0;
        int ended;
        strike(t, l, FS / 2u);
        for (i = 0; i < FS / 2u; i++) {
            pk = abs(buf[i]) > pk ? abs(buf[i]) : pk;
            dc += buf[i];
        }
        dc /= FS / 2u;
        ended = !strike(t, l, MAXN);
        snprintf(nm, sizeof nm, "%s: sounds, under full scale, no DC, ends", NAME[l]);
        check(nm, pk > 1036 && pk < 32000 && fabs(dc) < pk * 0.02 && ended, "peak %d, DC %.0f", pk, dc);
    }
    /* 1b (Skiff phase 9) every kit a preset loads (eng_drumx.c DRUMX_PKIT): the same, every lane at A and at B */
    for (i = 2; i < ENG_DRUMX.npresets; i++) {
        int32_t lo = 32767, hi = 0;
        int all = 1;
        char why[48] = "";
        for (l = 0; l < 16u; l++) {
            track_t *t = &trk[0];
            int32_t pk = 0;
            double dc = 0;
            uint32_t j;
            host_tracks_init();
            host_preset(t, ENGI_DRUMX, i);
            t->p[P_E0] = l < 8u ? 0 : 127;
            for (j = 0; j < 4u; j++)
                t->p[P_DIST + j] = 0;
            strike(t, l & 7u, FS / 2u);
            for (j = 0; j < FS / 2u; j++) {
                pk = abs(buf[j]) > pk ? abs(buf[j]) : pk;
                dc += buf[j];
            }
            dc /= FS / 2u;
            if (!(pk > 1036 && pk < 32000 && fabs(dc) < pk * 0.02 && !strike(t, l & 7u, MAXN)) && all) {
                snprintf(why, sizeof why, "; %s at %s: peak %d, DC %.0f", NAME[l & 7u], l < 8u ? "A" : "B", pk, dc);
                all = 0;
            }
            lo = pk < lo ? pk : lo;
            hi = pk > hi ? pk : hi;
        }
        snprintf(nm, sizeof nm, "%s: every lane at A and B sounds, under full scale, no DC, ends",
                 ENG_DRUMX.presets[i].name);
        check(nm, all && !memcmp(dx_kit, DX_KITS[DRUMX_PKIT[i] - 1u], sizeof dx_kit), "peaks %d .. %d%s", lo, hi, why);
    }

    /* 2 */
    {
        static int32_t a[FS / 4];
        double r0, r1, rm;
        int32_t d = 0, own = 0, step;
        uint32_t m;
        track_t *t = kitx(0, 64);
        strike(t, 1, FS / 4u);
        memcpy(a, buf, sizeof a);
        r0 = rms(0, FS / 4u);
        t = kitx(127, 64);
        strike(t, 1, FS / 4u);
        r1 = rms(0, FS / 4u);
        for (i = 0; i < FS / 4u; i++)
            d = abs(buf[i] - a[i]) > d ? abs(buf[i] - a[i]) : d;
        t = kitx(64, 64);
        strike(t, 1, FS / 4u);
        rm = rms(0, FS / 4u);
        check("MORPH: A and B differ, the middle between them", d > 2000 &&
              rm > (r0 < r1 ? r0 : r1) * 0.7 && rm < (r0 > r1 ? r0 : r1) * 1.3, "RMS %.0f / %.0f / %.0f", r0, rm, r1);
        for (m = 0; m < 2u; m++) {                       /* the open hat's own largest steps at A and B */
            int32_t s;
            t = kitx(m ? 127 : 0, 64);
            strike(t, 4, FS / 2u);
            s = maxstep(FS / 2u);
            own = s > own ? s : own;
        }
        t = kitx(0, 64);                                 /* MORPH swept while the open hat rings */
        trk_note_on(t, NOTE[4], 100);
        for (i = 0; i < FS / 2u; i += CTL) {
            int32_t o[2 * CTL];
            uint32_t j;
            t->p[P_E0] = (int16_t)(i * 127u / (FS / 2u));
            mix_block(o, CTL);
            for (j = 0; j < CTL; j++)
                buf[i + j] = o[2 * j];
        }
        step = maxstep(FS / 2u);
        check("MORPH moves a ringing hit without a jump", step <= own + own / 5, "largest step %d, the hat's own %d", step, own);
    }

    /* 3 */
    {
        uint32_t c0, c1, e0, e1;
        track_t *t = kitx(0, 64);
        strike(t, 5, FS / 2u);
        c0 = crossings(FS / 10u, FS / 5u);
        t = kitx(0, 127);                                /* +63 x 3 / 16 = 11.8 semitones */
        strike(t, 5, FS / 2u);
        c1 = crossings(FS / 10u, FS / 5u);
        check("PITCH: TUNE up ~12 semitones about doubles the tom", c1 > c0 * 1.85 && c1 < c0 * 2.15, "%u -> %u", c0, c1);
        t = kitx(0, 64);
        strike(t, 0, FS / 4u);
        e0 = crossings(0, FS / 50u);
        e1 = crossings(FS / 10u, FS / 10u + FS / 50u);
        check("PITCH: the kick's pitch envelope falls", e0 > e1, "%u -> %u crossings in 20 ms", e0, e1);
    }

    /* 4 */
    {
        track_t *t = kitx(64, 64);
        const drumx_lane_t *K;
        trk_note_on(t, NOTE[4], 100);
        run(FS / 10u);
        trk_note_on(t, NOTE[3], 1);                      /* (a quiet closed hat: the open one's tail is measured) */
        run(FS / 50u);
        K = drumx_kit_of(t);
        check("the closed hat chokes the open one", !K[DV_HATO].x.live || K[DV_HATO].x.ea < (1 << 30) / 1000,
              "open hat envelope %d", (int)K[DV_HATO].x.ea);
    }

    /* 5 */
    {
        double r0, r1;
        uint32_t lw, ok2 = 1;
        track_t *t = kitx(64, 64);
        ok = str_eq(ENG_DRUMX.edit[0].label, "MORPH") && str_eq(ENG_DRUMX.edit[4].label, "NOISE") && ENG_DRUMX.knob[0] == P_E0;   /* ((Skiff U4) the words) */
        t->p[P_E4] = 0;                                  /* NOIS: the snare's noise out, then all noise */
        strike(t, 1, FS / 4u);
        r0 = rms(FS / 20u, FS / 4u);
        t = kitx(64, 64);
        t->p[P_E4] = 127;
        strike(t, 1, FS / 4u);
        r1 = rms(FS / 20u, FS / 4u);
        check("the knobs: MRPH (KNOB 1), NOIS moves the noise of every lane", ok && fabs(r0 - r1) > 0.2 * (r0 > r1 ? r0 : r1),
              "snare tail RMS %.0f / %.0f", r0, r1);
        for (lw = 0; lw < 8u; lw++) {                    /* FOLD 127, FM 40 and 120: another sound, every lane */
            static int32_t a0[FS / 8];
            static const uint8_t KN[3][2] = {{P_E6, 127}, {P_E5, 40}, {P_E5, 120}};
            uint32_t k;
            t = kitx(64, 64);
            strike(t, lw, FS / 8u);
            memcpy(a0, buf, sizeof a0);
            for (k = 0; k < 3u; k++) {
                int32_t pk = 0;
                double d = 0;
                t = kitx(64, 64);
                t->p[KN[k][0]] = KN[k][1];
                strike(t, lw, FS / 8u);
                for (i = 0; i < FS / 8u; i++) {
                    d += fabs((double)buf[i] - a0[i]);
                    pk = abs(buf[i]) > pk ? abs(buf[i]) : pk;
                }
                ok2 &= d / (FS / 8u) > 200 && pk < 32700 && !strike(t, lw, MAXN);
            }
        }
        check("FOLD 127, FM 40 / 120: every lane another sound, under full scale, still ends", ok2, 0);
    }

    /* 6 */
    {
        uint32_t n, bad = 0;
        track_t *t = kitx(127, 64);                      /* (MRPH 127: DRUM's KIT 127 would swap lanes 6..8) */
        for (n = 0; n < 128u; n++)
            bad += (uint32_t)DX_GM[dx_gm_ix(n)][0] != drum_lane(n);
        ok = drum_track(t) && !bad && str_eq(drum_lane_name(t, DV_TOM), "TOM") && str_eq(drum_lane_abbr(t, DV_RIM), "RS") &&
             eng_allowed(NTRK - 1u, ENGI_DRUMX) && str_eq(ENGINES[ENGI_DRUMX]->name, "DRUM-X");
        check("a drum track: the GM lanes drum_lane's, plain lane names, the light tracks", ok, "%u notes off", bad);
        {                                                /* the last track (with six: a light one, its eng_lite area) */
            track_t *z = &trk[NTRK - 1u];
            int32_t pk = 0;
            host_tracks_init();
            host_preset(z, ENGI_DRUMX, 0);
            for (i = 0; i < 4u; i++)
                z->p[P_DIST + i] = 0;
            trk_note_on(z, NOTE[0], 100);
            run(FS / 4u);
            for (i = 0; i < FS / 4u; i++)
                pk = abs(buf[i]) > pk ? abs(buf[i]) : pk;
            check("the last track plays DRUM-X too (T6 with six: its light area)", pk > 1036 && pk < 32000, "peak %d, track %u",
                  pk, NTRK);
        }
        {
            dx_lane_t keep = dx_kit[DV_KICK];
            double r0, r1;
            t = kitx(64, 64);
            strike(t, 0, FS / 4u);
            r0 = rms(0, FS / 4u);
            dx_kit[DV_KICK].a[DXP_DECAY] = dx_kit[DV_KICK].b[DXP_DECAY] = 10;   /* (a short kick) */
            t = kitx(64, 64);
            strike(t, 0, FS / 4u);
            r1 = rms(0, FS / 4u);
            dx_kit[DV_KICK] = keep;
            check("the project's kit is what plays: a shorter kick is heard", r1 < r0 * 0.7, "RMS %.0f -> %.0f", r0, r1);
        }
    }

    /* 7 */
    for (l = 0; l < 8u; l++) {
        static const int16_t MR[3] = {0, 64, 127};
        uint32_t m;
        for (m = 0; m < 3u; m++) {
            track_t *t = kitx(MR[m], 64);
            strike(t, l, FS / 2u);
            snprintf(nm, sizeof nm, "%s_m%d.wav", NAME[l], MR[m]);
            save(dir, nm, FS / 2u);
        }
    }
    {
        static int32_t beat[FS * 8];
        static const uint8_t PAT[16] = {1, 0, 8, 0, 2 | 8, 0, 8, 1, 1, 0, 8, 0, 2 | 8, 0, 16, 64};
        track_t *t = kitx(0, 64);
        uint32_t s, n = 0, per = FS * 60u / 120u / 4u;
        for (s = 0; s < 64u && n + per <= FS * 8u; s++) {
            uint32_t b = PAT[s % 16u], k;
            t->p[P_E0] = (int16_t)(s * 127u / 63u);
            for (k = 0; k < 8u; k++)
                if ((b >> k) & 1u)
                    trk_note_on(t, NOTE[k], 100);
            run(per);
            for (k = 0; k < per; k++)
                beat[n + k] = buf[k];
            n += per;
        }
        memcpy(buf, beat, n * sizeof beat[0] < sizeof buf ? n * sizeof beat[0] : sizeof buf);
        save(dir, "beat_morph.wav", n < MAXN ? n : MAXN);
    }

    printf(fails ? "drumx: %d FAILED\n" : "drumx: all ok\n", fails);
    return fails != 0;
}
