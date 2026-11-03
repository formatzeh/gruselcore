/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) Every factory sound's loudness in a mix, against the drum kits': each played as it would in music for
 * 4 s at 150 BPM through the whole mix (sends off: dry, as tests/drum_test.c measures the kits), at the track's
 * default LEVEL (a preset load keeps the track's LEVEL), K-weighted (tests/gc_loudness.h):
 *   kits      a groove: kick on the beats, closed hat on the offbeats, clap on 2 and 4
 *   BASS      8th notes on C2, half a step long
 *   LEAD, PLUCK, KEYS, untagged: 16th notes C4 Eb4 G4 C5, half a step long
 *   PAD, TEST (on trial): one note, C3, held 4 s
 *   FX        a note each beat on C3, held most of it (a one-shot sounds each beat, a drone goes on)
 * The master 12 dB down for all of them (song.master_q12): no sound alone reaches the master's limiter, which would
 * flatten the loud ones and hide how loud they are
 * BODY: the mean over the 4 s (what a mix hears); PUNCH: the loudest 100 ms. Printed as a table, sorted by type, with
 * the gap to the kits' mean BODY.
 * Each sound's TRIM (core.h) is in what it measures. Fails when a listed sound (a type, not SAMPLE's untagged ones)
 * is more than 13 dB under the kits or 7 dB over them: a new sound evened out with TRIM before it ships.
 *   build/host/preset_loudness [TSV] */
#define main hostsim_main
#include "hostsim.c"
#undef main
#include "gc_loudness.h"
#include <math.h>

#define SECS 4u
static float L[FS * SECS], R[FS * SECS];

static double body_db(const float *l, const float *r, uint32_t n)
{
    lu_bq_t a, b;
    double acc = 0;
    uint32_t i;
    lu_shelf(&a, 44100.0);
    lu_hp(&b, 44100.0);
    for (i = 0; i < n; i++) {
        double x = lu_bq(&b, lu_bq(&a, 0.5 * ((double)l[i] + (double)r[i])));
        acc += x * x;
    }
    return 10.0 * log10(acc / n + 1e-12);
}

static const char *const TYPE[] = {"-", "BASS", "LEAD", "PAD", "KEYS", "PLUCK", "DRUM", "FX", "TEST"};
enum { K_GROOVE, K_BASS, K_LINE, K_HOLD, K_BEATS };

/* track 4 (as the drum test's) on engine e, preset p, played as kind k; the mix's output into L, R */
static void play(uint32_t e, uint32_t p, uint32_t kind)
{
    static const uint8_t LINE[4] = {60, 63, 67, 72};
    uint32_t step = FS * 60u / 150u / 4u, f, i, n = 0, held = 0;
    track_t *t = &trk[3];
    host_tracks_init();
    host_preset(t, e, p);
    song.master_q12 = 1024;                             /* (-12 dB: clear of the limiter) */
    t->p[P_CHOR] = t->p[P_DLY] = t->p[P_REV] = 0;
    for (f = 0; f + CTL <= FS * SECS; f += CTL) {
        int32_t o[2 * CTL];
        uint32_t s = f / step, in = f % step;
        if (in < CTL) {                                 /* a 16th starts */
            if (kind == K_GROOVE) {
                if (s % 4u == 0u) trk_note_on(t, 36, 100);
                if (s % 4u == 2u) trk_note_on(t, 42, 100);
                if (s % 8u == 4u) trk_note_on(t, 39, 100);
            } else if (kind == K_BASS && s % 2u == 0u) {
                trk_note_on(t, held = 36, 100);
            } else if (kind == K_LINE) {
                trk_note_on(t, held = LINE[n++ % 4u], 100);
            } else if (kind == K_BEATS && s % 4u == 0u) {
                trk_note_on(t, held = 48, 100);
            } else if (kind == K_HOLD && s == 0u) {
                trk_note_on(t, held = 48, 100);
            }
        }
        if (held && kind == K_BEATS && s % 4u == 3u && in >= step * 3u / 4u && in < step * 3u / 4u + CTL) {
            trk_note_off(t, held);
            held = 0;
        } else if (held && kind != K_HOLD && kind != K_BEATS && in >= step / 2u && in < step / 2u + CTL) {
            trk_note_off(t, held);
            held = 0;
        }
        mix_block(o, CTL);
        for (i = 0; i < CTL; i++) {
            L[f + i] = (float)o[2 * i] / 32768.0f;
            R[f + i] = (float)o[2 * i + 1] / 32768.0f;
        }
    }
}

typedef struct { const char *eng, *name, *type; double body, punch; } row_t;
static row_t rows[600];
static uint32_t nrows;

static int cmp(const void *a, const void *b)
{
    const row_t *x = a, *y = b;
    int c = strcmp(x->type, y->type);
    return c ? c : (x->body < y->body) - (x->body > y->body);
}

int main(int argc, char **argv)
{
    uint32_t e, p, i, nk = 0;
    double kit = 0;
    FILE *tsv = argc > 1 ? fopen(argv[1], "w") : 0;
    for (e = 0; e < NENGINES; e++) {
        const engine_t *en = ENGINES[e];
        if (!en || !en->npresets || e == ENGI_DRUMX || e == ENGI_SLICE || !strcmp(en->name, "-"))   /* (SLICE: needs its loop) */
            continue;
        for (p = 0; p < en->npresets && nrows < 600u; p++) {
            const preset_t *pr = &en->presets[p];
            uint32_t tag = pr->tag, kind = e == ENGI_DRUM ? K_GROOVE : tag == 1u ? K_BASS
                         : tag == 7u ? K_BEATS : (tag == 3u || tag == 8u) ? K_HOLD : K_LINE;
            row_t *r = &rows[nrows++];
            play(e, p, kind);
            r->eng = en->name;
            r->name = pr->name;
            r->type = e == ENGI_DRUM ? "KIT" : tag < 9u ? TYPE[tag] : "?";
            r->body = body_db(L, R, FS * SECS);
            r->punch = loudness_db(L, R, (int)(FS * SECS));
            if (e == ENGI_DRUM && strstr(pr->name, "PERC") == 0) {
                kit += r->body;
                nk++;
            }
        }
    }
    kit /= nk ? nk : 1;
    qsort(rows, nrows, sizeof rows[0], cmp);
    printf("kits (drum kits, not the PERC kits): mean BODY %.1f dB over %u kits\n", kit, nk);
    printf("%-6s %-8s %-14s %7s %7s %8s\n", "TYPE", "ENGINE", "SOUND", "BODY", "PUNCH", "vs KITS");
    for (i = 0; i < nrows; i++) {
        printf("%-6s %-8s %-14s %7.1f %7.1f %+8.1f\n", rows[i].type, rows[i].eng, rows[i].name, rows[i].body,
               rows[i].punch, rows[i].body - kit);
        if (tsv)
            fprintf(tsv, "%s\t%s\t%s\t%.2f\t%.2f\t%.2f\n", rows[i].type, rows[i].eng, rows[i].name, rows[i].body,
                    rows[i].punch, rows[i].body - kit);
    }
    if (tsv)
        fclose(tsv);
    {
        uint32_t bad = 0;
        for (i = 0; i < nrows; i++)
            if (strcmp(rows[i].type, "KIT") && strcmp(rows[i].type, "-") && strcmp(rows[i].type, "?") &&
                (rows[i].body - kit < -13.0 || rows[i].body - kit > 7.0)) {
                printf("preset_loudness: %s %s is %+.1f dB against the kits (-13 .. +7): FAIL\n", rows[i].eng,
                       rows[i].name, rows[i].body - kit);
                bad++;
            }
        printf("preset_loudness: %s\n", bad ? "FAILED" : "every listed sound within -13 .. +7 dB of the kits");
        return bad != 0;
    }
}
