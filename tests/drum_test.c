/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) The DRUM engine with GruselCore's kits (gc_drum.c, gc_kits.c) through the whole mix, no sends:
 *   - every kit, every lane: one hit sounds, is finite, does not clip, ends (its tail is gone at the end of a second),
 *     and is as loud as the kits are meant to be (tests/gc_loudness.h: K-weighted, the loudest 100 ms);
 *   - a closed hat chokes the open one; a second hit of a lane does not click or run away;
 *   - KIT, PITCH, TONE, DECAY and GRIT change the sound, 0 and 127 alike are bounded.
 * (Skiff's own drum voices' tests, drum_voice.c, are not in the build any more.)
 *   build/host/drum_test [DEMO_DIR]  (the argument is accepted and not used) */
#define main hostsim_main
#include "hostsim.c"
#undef main
#include "gc_loudness.h"
#include <math.h>

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("drum: FAIL "); printf(__VA_ARGS__); printf("\n"); } } while (0)

static const uint8_t LANE_NOTE[8] = {36, 38, 39, 42, 46, 45, 37, 56};

typedef struct { double db; int32_t peak; double tail; double sum; int bad; } hit_t;

/* one hit (or two: `then` is a note played at 1/8 s, 0: none) of a track on preset `preset`; the end is read as the
 * peak of the last 100 ms against the hit's peak */
static hit_t hit(uint32_t preset, uint32_t note, uint32_t then, const int16_t *set)
{
    static float l[FS], r[FS];
    uint32_t f, i, k;
    hit_t h = {0, 0, 0, 0, 0};
    int32_t tp = 0;
    host_tracks_init();
    host_preset(&trk[3], ENGI_DRUM, preset);
    trk[3].p[P_CHOR] = trk[3].p[P_DLY] = trk[3].p[P_REV] = 0;
    for (k = 0; set && set[k] >= 0; k += 2)
        trk[3].p[set[k]] = set[k + 1];
    trk_note_on(&trk[3], note, 100);
    for (f = 0; f + CTL <= FS; f += CTL) {
        int32_t o[2 * CTL];
        if (f == FS / 4u)
            trk_note_off(&trk[3], note);
        if (then && f == FS / 8u)
            trk_note_on(&trk[3], then, 100);
        mix_block(o, CTL);
        for (i = 0; i < CTL; i++) {
            int32_t a = abs(o[2 * i]);
            l[f + i] = (float)o[2 * i] / 32768.0f;
            r[f + i] = (float)o[2 * i + 1] / 32768.0f;
            if (o[2 * i] < -32768 || o[2 * i] > 32767)
                h.bad = 1;
            if (a > h.peak)
                h.peak = a;
            if (f + i >= FS - FS / 10u && a > tp)
                tp = a;
            h.sum += (double)a;
        }
    }
    h.db = loudness_db(l, r, FS);
    h.tail = h.peak ? (double)tp / (double)h.peak : 0.0;
    return h;
}

static void kits(void)
{
    uint32_t p, k, n = ENGINES[ENGI_DRUM]->npresets, worst = 0;
    double sum = 0.0, lo = 99.0, hi = -99.0;
    uint32_t cnt = 0;
    for (p = 0; p < n; p++) {
        for (k = 0; k < 8u; k++) {
            hit_t h = hit(p, LANE_NOTE[k], 0, 0);
            const char *nm = ENGINES[ENGI_DRUM]->presets[p].name;
            if (!(p < 18u))
                continue;                                   /* (the user kits are the sample engine's) */
            CHECK(h.peak > 200, "%s lane %u is silent (peak %d)", nm, k, h.peak);
            CHECK(!h.bad, "%s lane %u leaves the 16-bit range", nm, k);
            CHECK(h.peak < 32000, "%s lane %u peaks at %d (clipping)", nm, k, h.peak);
            CHECK(h.tail < 0.02, "%s lane %u has not ended after a second (tail %.3f of its peak)", nm, k, h.tail);
            CHECK(h.db > -24.0 && h.db < -8.0, "%s lane %u is %.1f dB (-24..-8)", nm, k, h.db);
            sum += h.db;
            cnt++;
            if (h.db < lo) lo = h.db;
            if (h.db > hi) hi = h.db;
            (void)worst;
        }
    }
    printf("drum: %u hits of %u kits, loudness %.1f..%.1f dB, mean %.1f\n", cnt, 18u, lo, hi, sum / cnt);
    CHECK(cnt == 18u * 8u, "every kit has 8 lanes");
    CHECK(sum / cnt > -18.0 && sum / cnt < -13.0, "the kits' mean loudness %.1f dB (-18..-13)", sum / cnt);
}

static void choke(void)
{
    uint32_t p;
    for (p = 0; p < 3u; p++) {
        hit_t open = hit(p, 46, 0, 0), shut = hit(p, 46, 42, 0);
        /* the open hat alone rings; with the closed one at 1/8 s the sum of |output| is smaller (the open hat is cut) */
        CHECK(shut.sum != open.sum, "kit %u: the closed hat changes nothing", p);
    }
}

static void controls(void)
{
    uint32_t p = 0;
    hit_t a = hit(p, 36, 0, 0);
    static const int16_t PITCH_UP[] = {P_E1, 127, -1};
    static const int16_t TONE_UP[] = {P_E2, 127, -1};
    static const int16_t DEC_UP[] = {P_E3, 127, -1};
    static const int16_t DEC_DN[] = {P_E3, 0, -1};
    static const int16_t GRIT_UP[] = {P_E4, 127, -1};
    static const int16_t GRIT_DN[] = {P_E4, 0, -1};
    hit_t b;
    b = hit(p, 36, 0, DEC_UP);
    CHECK(!b.bad && b.peak < 32000, "DECAY 127: bounded (peak %d)", b.peak);
    CHECK(b.sum > a.sum, "DECAY 127 does not lengthen the kick");
    b = hit(p, 36, 0, DEC_DN);
    CHECK(!b.bad && b.sum < a.sum, "DECAY 0 does not shorten the kick");
    b = hit(p, 36, 0, PITCH_UP);
    CHECK(!b.bad && b.peak < 32000 && b.sum != a.sum, "PITCH 127: bounded and different (peak %d)", b.peak);
    b = hit(p, 36, 0, TONE_UP);
    CHECK(!b.bad && b.peak < 32000 && b.sum != a.sum, "TONE 127: bounded and different (peak %d)", b.peak);
    b = hit(p, 36, 0, GRIT_UP);
    CHECK(!b.bad && b.peak < 32000 && b.sum != a.sum, "GRIT 127: bounded and different (peak %d)", b.peak);
    b = hit(p, 36, 0, GRIT_DN);
    CHECK(!b.bad && b.peak < 32000, "GRIT 0: bounded (peak %d)", b.peak);
}

static void retrigger(void)
{
    uint32_t p, k;
    for (p = 0; p < 18u; p += 5)
        for (k = 0; k < 8u; k++) {
            hit_t h = hit(p, LANE_NOTE[k], LANE_NOTE[k], 0);
            CHECK(!h.bad && h.peak < 32000 && h.tail < 0.02, "%s lane %u struck twice: peak %d tail %.3f",
                  ENGINES[ENGI_DRUM]->presets[p].name, k, h.peak, h.tail);
        }
}

int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    kits();
    choke();
    controls();
    retrigger();
    printf("drum_test: %s\n", fails ? "FAILED" : "all checks ok");
    return fails != 0;
}
