/* SPDX-License-Identifier: GPL-3.0-only */
/* Demo grooves for listening: a main kit and a percussion kit playing together, 4 bars each.
 *   gdrum_groove OUTDIR
 * Each pattern row is 16 steps: x = hit, X = accent, . = rest. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "../../firmware/src/dsp/gdrum.h"

#define FS 44100

typedef struct { int kit, snd; const char *row; } row_t;
typedef struct {
    const char *name;
    float bpm, swing;                               /* swing: the late 16ths' delay, share of a 16th */
    int nrows;
    row_t rows[12];
} groove_t;

static const groove_t GROOVES[] = {
    {"darkprog_126", 126.0f, 0.08f, 10, {
        {8, 0, "X...x...X...x..."}, {8, 2, "....X.......X..."}, {8, 3, "..x...x...x...x."},
        {12, 2, "xxXxxxXxxxXxxxXx"}, {12, 0, "...x.......x..x."}, {12, 1, "......x.......x."},
        {12, 4, ".......x.....x.."}, {12, 7, "..........x....."}, {12, 5, "...............x"},
        {12, 6, "....x..........."}}},
    {"tribetek_150", 150.0f, 0.0f, 10, {
        {1, 0, "X...X...X...X..."}, {1, 2, "....x.......x..."}, {1, 3, "..x...x...x...x."},
        {10, 0, "x..x..x...x..x.."}, {10, 1, "..x....x..x...x."}, {10, 2, ".x...x...x...x.x"},
        {10, 5, "...x.x.....x.x.."}, {10, 3, "xxxxxxxxxxxxxxxx"}, {10, 6, "x.....x.....x..."},
        {10, 7, "X.......x.....x."}}},
    {"mentaltek_165", 165.0f, 0.0f, 10, {
        {2, 0, "X...X...X...X..."}, {2, 1, "....x.......x..."}, {2, 3, "xxxxxxxxxxxxxxxx"},
        {11, 0, "...x......x....x"}, {11, 1, ".......x.......x"}, {11, 2, "..x...x.x....x.."},
        {11, 3, "x.x.x.x.x.x.x.x."}, {11, 5, "....x.......x..x"}, {11, 6, ".x...x...x...x.."},
        {11, 7, "x..............."}}},
};

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
            float x = tanhf(s[c] * 0.9f);           /* a soft master clip, as the FM-1's limiter would */
            int16_t v = (int16_t)lrintf(x * 32767.0f);
            fwrite(&v, 2, 1, f);
        }
    }
    fclose(f);
}

int main(int argc, char **argv)
{
    static float L[FS * 12], R[FS * 12];
    static gdrum_t kits[2];
    const char *dir = argc > 1 ? argv[1] : ".";
    for (unsigned g = 0; g < sizeof GROOVES / sizeof GROOVES[0]; g++) {
        const groove_t *gr = &GROOVES[g];
        float step = 60.0f / gr->bpm / 4.0f * FS;
        int kit_of[2] = {gr->rows[0].kit, -1}, total = (int)(step * 64), pos = 0;
        char path[512];
        for (int i = 0; i < gr->nrows; i++)
            if (gr->rows[i].kit != kit_of[0])
                kit_of[1] = gr->rows[i].kit;
        for (int k = 0; k < 2; k++) {
            gdrum_init(&kits[k]);
            if (kit_of[k] >= 0)
                gdrum_load_kit(&kits[k], &gd_kits[kit_of[k]]);
        }
        memset(L, 0, sizeof L);
        memset(R, 0, sizeof R);
        for (int s = 0; s < 64; s++) {
            int at = (int)(s * step + ((s & 1) ? gr->swing * step : 0.0f));
            if (at > pos) {
                for (int k = 0; k < 2; k++)
                    gdrum_render_st(&kits[k], L + pos, R + pos, at - pos);
                pos = at;
            }
            for (int i = 0; i < gr->nrows; i++) {
                char c = gr->rows[i].row[s & 15];
                if (c == 'x' || c == 'X')
                    gdrum_trigger(&kits[gr->rows[i].kit == kit_of[0] ? 0 : 1], gr->rows[i].snd, c == 'X' ? 1.0f : 0.6f);
            }
        }
        for (int k = 0; k < 2; k++)
            gdrum_render_st(&kits[k], L + pos, R + pos, total - pos);
        snprintf(path, sizeof path, "%s/groove_%s.wav", dir, gr->name);
        wav_write(path, L, R, total);
        printf("%s\n", path);
    }
    return 0;
}
