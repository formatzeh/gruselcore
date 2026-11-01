/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore engine on the host: 8 tracks (drums and 303s) through the sequencer, the inserts, the
 * shared FX and the master. Checks finite output and headroom, type changes and kit loads while
 * playing, mutes; reports the host's render cost; writes build/gengine/demo.wav to listen to. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "../../firmware/src/app/gengine.h"

/* the platform, as the engine needs it */
uint32_t plat_cycles(void) { return 0; }
uint32_t plat_master(void) { return 4096; }
int plat_midi_in(uint32_t *pkt) { (void)pkt; return 0; }
void plat_midi_out(uint32_t pkt) { (void)pkt; }
int plat_cpu2_run(void (*fn)(uint32_t), uint32_t arg) { (void)fn; (void)arg; return 0; }
int plat_cpu2_wait(void) { return 0; }

static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); fails++; } } while (0)

static pattern_t pat[NPAT];
static sound_t snd;
#define SEC 44100
static int32_t out[SEC * 2 * 2];
static float wav[SEC * 20 * 2];
static int nwav;

static float render(int frames, int keep)
{
    float pk = 0.0f;
    int i, done = 0;
    while (done < frames) {
        int n = frames - done > 128 ? 128 : frames - done;
        engine_render(out, (uint32_t)n);
        for (i = 0; i < 2 * n; i++) {
            float x = (float)out[i] / 4194304.0f;
            CHECK(isfinite(x), "not finite");
            if (fabsf(x) > pk)
                pk = fabsf(x);
            if (keep && nwav < SEC * 20 * 2)
                wav[nwav++] = x;
        }
        done += n;
    }
    return pk;
}

static void wav_write(const char *path)
{
    FILE *f = fopen(path, "wb");
    int32_t data = nwav * 2, riff = 36 + data, fmt = 16, rate = SEC, bps = SEC * 4;
    int16_t pcm = 1, ch = 2, align = 4, bits = 16;
    if (!f)
        return;
    fwrite("RIFF", 1, 4, f); fwrite(&riff, 4, 1, f); fwrite("WAVEfmt ", 1, 8, f);
    fwrite(&fmt, 4, 1, f); fwrite(&pcm, 2, 1, f); fwrite(&ch, 2, 1, f); fwrite(&rate, 4, 1, f);
    fwrite(&bps, 4, 1, f); fwrite(&align, 2, 1, f); fwrite(&bits, 2, 1, f);
    fwrite("data", 1, 4, f); fwrite(&data, 4, 1, f);
    for (int i = 0; i < nwav; i++) {
        float x = wav[i] > 1.0f ? 1.0f : wav[i] < -1.0f ? -1.0f : wav[i];
        int16_t v = (int16_t)lrintf(x * 32767.0f);
        fwrite(&v, 2, 1, f);
    }
    fclose(f);
}

static void set_mix(int t, int i, int v) { snd.mix[t][i] = (uint8_t)v; engine_set(T_MIX, t, i, v); }

int main(int argc, char **argv)
{
    int t, i, p;
    const char *dir = argc > 1 ? argv[1] : 0;
    engine_sound_defaults(&snd);
    for (p = 0; p < NPAT; p++)
        gpat_init(&pat[p], snd.ttype);
    engine_init(pat, &snd);
    engine_apply_sound(&snd);
    seq.bpm = 145.0f;
    seq.send_clock = 0;
    /* track 1: Hardtek kit, kick on the quarters, clap on 2 and 4, hats on the offbeats */
    for (i = 0; i < 16; i += 4)
        sm_set(pat[0].t[0].u.d.hit[0], i);
    sm_set(pat[0].t[0].u.d.hit[2], 4);
    sm_set(pat[0].t[0].u.d.hit[2], 12);
    for (i = 2; i < 16; i += 4)
        sm_set(pat[0].t[0].u.d.hit[3], i);
    /* track 2: tribe percussion, 12 steps */
    pat[0].t[1].len = 12;
    sm_set(pat[0].t[1].u.d.hit[1], 0);
    sm_set(pat[0].t[1].u.d.hit[2], 3);
    sm_set(pat[0].t[1].u.d.hit[1], 6);
    sm_set(pat[0].t[1].u.d.hit[5], 9);
    for (i = 0; i < 12; i++)
        sm_set(pat[0].t[1].u.d.hit[3], i);
    /* track 3: a rolling psy bass on the offbeat 16ths */
    for (i = 0; i < 16; i++) {
        bstep_t *b = &pat[0].t[2].u.b.step[i];
        b->note = (uint8_t)(i % 4 == 0 ? 33 : 33 + (i % 8 == 6 ? 3 : 0));
        b->flags = (uint8_t)(i % 4 == 0 ? G_REST : G_NOTE | (i % 4 == 3 ? BS_ACCENT : 0));
    }
    /* track 4: a 303 line, 1/8, with slides */
    pat[0].t[3].rate = RATE_8;
    {
        static const uint8_t N[8] = {45, 45, 57, 48, 45, 52, 50, 57};
        for (i = 0; i < 8; i++) {
            pat[0].t[3].u.b.step[i].note = N[i];
            pat[0].t[3].u.b.step[i].flags = (uint8_t)(G_NOTE | (i == 2 || i == 5 ? BS_SLIDE : 0) | (i == 4 ? BS_ACCENT : 0));
        }
    }
    set_mix(3, MX_DLY, 50);
    set_mix(1, MX_REV, 30);
    gseq_start(&seq);
    {
        clock_t c0 = clock();
        float pk = render(SEC * 8, 1);
        double cpu = (double)(clock() - c0) / CLOCKS_PER_SEC / 8.0;
        printf("8 s of 4 tracks: peak %.2f, host render %.1f %% of real time\n", (double)pk, cpu * 100.0);
        CHECK(pk > 0.05f, "silent");
        CHECK(pk <= 2.0f, "over the output's clamp: %.2f", (double)pk);
    }
    /* a filter sweep and drive on the bass while playing */
    set_mix(2, MX_FILTER, 30);
    set_mix(2, MX_RESO, 90);
    set_mix(2, MX_DRIVE, 60);
    render(SEC * 2, 1);
    /* live: track 5 becomes a drum track with the Psytrance kit, track 4 becomes OFF, track 2 muted */
    snd.ttype[4] = TT_DRUM;
    for (p = 0; p < NPAT; p++)
        gpat_track_clear(&pat[p].t[4], TT_DRUM);
    engine_set(T_TRK, 4, TK_TYPE, TT_DRUM);
    engine_track_kit(&snd, 4, 6);
    for (i = 0; i < 16; i += 2)
        sm_set(pat[0].t[4].u.d.hit[3], i);
    snd.ttype[3] = TT_OFF;
    engine_set(T_TRK, 3, TK_TYPE, TT_OFF);
    seq.mute = 1u << 1;
    render(SEC * 4, 1);
    CHECK(seq.ttype[4] == TT_DRUM && seq.ttype[3] == TT_OFF, "type changes not applied (%d %d)", seq.ttype[4], seq.ttype[3]);
    /* all 8 tracks busy: 4 drum kits, 4 303s, for the cost figure */
    for (t = 0; t < NTRK; t++) {
        int tt = t % 2 ? TT_303 : TT_DRUM;
        snd.ttype[t] = (uint8_t)tt;
        for (p = 0; p < NPAT; p++)
            gpat_track_clear(&pat[p].t[t], tt);
        engine_set(T_TRK, t, TK_TYPE, tt);
        for (i = 0; i < 16; i++) {
            if (tt == TT_DRUM) {
                sm_set(pat[0].t[t].u.d.hit[i % 8], i);
                sm_set(pat[0].t[t].u.d.hit[0], i);
            } else {
                pat[0].t[t].u.b.step[i].note = (uint8_t)(36 + (i * 5) % 12);
                pat[0].t[t].u.b.step[i].flags = G_NOTE;
            }
        }
    }
    seq.mute = 0;
    {
        clock_t c0 = clock();
        float pk = render(SEC * 4, 1);
        double cpu = (double)(clock() - c0) / CLOCKS_PER_SEC / 4.0;
        printf("8 busy tracks: peak %.2f, host render %.1f %% of real time\n", (double)pk, cpu * 100.0);
        CHECK(pk <= 2.0f, "8 tracks over the clamp: %.2f", (double)pk);
    }
    gseq_stop(&seq);
    render(SEC, 0);
    if (dir) {
        char path[512];
        snprintf(path, sizeof path, "%s/demo.wav", dir);
        wav_write(path);
    }
    printf(fails ? "gengine: %d FAILED\n" : "gengine: all checks passed\n", fails);
    return fails != 0;
}
