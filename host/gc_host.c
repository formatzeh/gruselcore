/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore host simulator: the whole app (UI, project, sequencer, engines) on this machine, driven
 * by a script, after X0X's x0x_host.c (Charles Vestal).
 *   gc_host SCRIPT [OUTDIR]
 * Script lines (# comments):
 *   wait MS                 run the app for MS milliseconds (UI frames, audio rendered)
 *   tap BTN | hold BTN | release BTN      BTN: FX SEL ENV LFO EDIT GLO HOME SAVE ARP SEQ PLAY REC OCTDN OCTUP
 *   tapkey wN | bN          white key N (0..15) / black key N (0..10), pressed and let go
 *   holdkey wN | releasekey wN
 *   turn ENC N              ENC: SELECT ALGO PRESET K1 K2 K3 K4; N detents (+ clockwise)
 *   shot NAME               the screen to OUTDIR/NAME.ppm
 *   wav NAME                start recording the audio to OUTDIR/NAME.wav (written at the end)
 *   reboot                  power off and on (the flash kept)
 *   expect WHAT VALUE       playing | view | trk | snd | cur | type.T | hit.T.S.STEP | gate.T.STEP |
 *                           note.T.STEP | len.T | mute | dirty | peak_min (output peak, % of full, since
 *                           the last peakreset) | kit.T
 *   peakreset */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#define __attribute__(x)

/* ------------------------------------------------------------ screen --- */
static uint16_t fb[240 * 240];
static void lcd_sync(void) {}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{
    uint32_t i, j;
    uint16_t sc = (uint16_t)(((c >> 8) & 0xFFu) | ((c & 0xFFu) << 8));
    for (j = y; j < y + h && j < 240u; j++)
        for (i = x; i < x + w && i < 240u; i++)
            fb[j * 240u + i] = sc;
}
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *px)
{
    uint32_t i, j;
    for (j = 0; j < h; j++)
        for (i = 0; i < w; i++)
            if (x + i < 240u && y + j < 240u)
                fb[(y + j) * 240u + x + i] = px[j * w + i];
}
#include "../firmware/src/gfx.c"

/* ---------------------------------------------------------- platform --- */
#include "../firmware/src/app/plat.h"
static uint32_t now_ms, held_btn, held_keys, master = 4096;
static int32_t enc_acc[NE];
uint32_t plat_ms(void) { return now_ms; }
uint32_t plat_buttons(void) { return held_btn; }
uint32_t plat_keys(void) { return held_keys; }
int32_t plat_enc(int role)
{
    int32_t v = enc_acc[role];
    enc_acc[role] = 0;
    return v;
}
uint32_t plat_master(void) { return master; }
int plat_battery(void) { return 3; }
static uint32_t lit_btn, lit_keys;
void plat_leds(uint32_t b, uint32_t k) { lit_btn = b; lit_keys = k; }
void plat_glow(int on) { (void)on; }
void plat_play_red(int red) { (void)red; }
void plat_keys_dim(uint32_t k) { (void)k; }
int plat_midi_in(uint32_t *pkt) { (void)pkt; return 0; }
void plat_midi_out(uint32_t pkt) { (void)pkt; }
void plat_midi_out_main(uint32_t pkt) { (void)pkt; }
int plat_midi_out_room(void) { return 64; }
static uint8_t store[OBJ_NOBJ][PLAT_STORE_MAX], store_prev[OBJ_NOBJ][PLAT_STORE_MAX];
static int store_len[OBJ_NOBJ] = {-1, -1, -1, -1, -1, -1, -1}, store_prev_len[OBJ_NOBJ] = {-1, -1, -1, -1, -1, -1, -1};
int plat_store_load(uint32_t obj, void *dst, uint32_t max)
{
    int n = obj < OBJ_NOBJ ? store_len[obj] : -1;
    if (n < 0)
        return -1;
    if ((uint32_t)n > max)
        n = (int)max;
    memcpy(dst, store[obj], (size_t)n);
    return n;
}
int plat_store_save(uint32_t obj, const void *src, uint32_t len)
{
    if (obj >= OBJ_NOBJ || len > PLAT_STORE_MAX)
        return -1;
    memcpy(store_prev[obj], store[obj], PLAT_STORE_MAX);
    store_prev_len[obj] = store_len[obj];
    memcpy(store[obj], src, len);
    store_len[obj] = (int)len;
    return 0;
}
int plat_store_load_prev(uint32_t obj, void *dst, uint32_t max)
{
    int n = obj < OBJ_NOBJ ? store_prev_len[obj] : -1;
    if (n < 0)
        return -1;
    if ((uint32_t)n > max)
        n = (int)max;
    memcpy(dst, store_prev[obj], (size_t)n);
    return n;
}
uint32_t plat_cpu_pct(void) { return 0; }
int plat_cpu2_run(void (*fn)(uint32_t), uint32_t arg) { (void)fn; (void)arg; return 0; }
int plat_cpu2_wait(void) { return 0; }
uint32_t plat_cycles(void) { return 0; }

/* ---------------------------------------------------------- the app --- */
#include "../firmware/src/app/gc.h"
#include "../firmware/src/app/gproject.c"
#include "../firmware/src/app/gui.c"

static int fails;
static float peak;
static FILE *wavf;
static uint32_t wav_frames;

static void render_ms(uint32_t ms)
{
    static int32_t out[441 * 2 * 2];
    uint32_t i, n = 441u * ms / 10u, done = 0;
    while (done < n) {
        uint32_t k = n - done > 128u ? 128u : n - done;
        engine_render(out, k);
        for (i = 0; i < 2u * k; i++) {
            float x = (float)out[i] / 8388608.0f;   /* the codec's full scale */
            if (fabsf(x) > peak)
                peak = fabsf(x);
            if (wavf) {
                float c = x > 1.0f ? 1.0f : x < -1.0f ? -1.0f : x;
                int16_t v = (int16_t)lrintf(c * 32767.0f);
                fwrite(&v, 2, 1, wavf);
            }
        }
        if (wavf)
            wav_frames += k;
        done += k;
    }
}

static void run(uint32_t ms)
{
    uint32_t t;
    for (t = 0; t < ms; t += 10) {
        now_ms += 10;
        render_ms(10);
        ui_frame();
    }
}

static void boot(void)
{
    palette_set(1);
    engine_init(proj.pat, &proj.sound);
    if (project_load() != 0)
        project_defaults();
    engine_apply_sound(&proj.sound);
    seq.bpm = (float)proj.set.bpm_x10 / 10.0f;
    seq.accent_q7 = proj.set.accent_q7;
    project_apply_io();
    ui_init();
    run(50);
}

static int btn_of(const char *s)
{
    static const char *const N[NB] = {"FX", "SEL", "ENV", "LFO", "EDIT", "GLO", "HOME", "SAVE", "ARP", "SEQ",
                                      "PLAY", "REC", "OCTDN", "OCTUP"};
    int i;
    for (i = 0; i < NB; i++)
        if (!strcmp(s, N[i]))
            return i;
    fprintf(stderr, "unknown button %s\n", s);
    exit(2);
}
static int enc_of(const char *s)
{
    static const char *const N[NE] = {"SELECT", "ALGO", "PRESET", "K1", "K2", "K3", "K4"};
    int i;
    for (i = 0; i < NE; i++)
        if (!strcmp(s, N[i]))
            return i;
    fprintf(stderr, "unknown encoder %s\n", s);
    exit(2);
}
static int key_of(const char *s)
{
    int n = atoi(s + 1), k;
    keys_init();
    for (k = 0; k < NKEYS; k++)
        if ((s[0] == 'w' && key_white[k] == n) || (s[0] == 'b' && key_black[k] == n))
            return k;
    fprintf(stderr, "unknown key %s\n", s);
    exit(2);
}

static void shot(const char *dir, const char *name)
{
    char path[512];
    FILE *f;
    int i;
    snprintf(path, sizeof path, "%s/%s.ppm", dir, name);
    f = fopen(path, "wb");
    if (!f)
        return;
    fprintf(f, "P6\n240 240\n255\n");
    for (i = 0; i < 240 * 240; i++) {
        uint16_t c = (uint16_t)(((fb[i] >> 8) & 0xFFu) | ((fb[i] & 0xFFu) << 8));
        uint8_t rgb[3] = {(uint8_t)((c >> 11) << 3), (uint8_t)(((c >> 5) & 63u) << 2), (uint8_t)((c & 31u) << 3)};
        fwrite(rgb, 1, 3, f);
    }
    fclose(f);
}

static int value_of(const char *what)
{
    int t, s, st;
    if (!strcmp(what, "playing")) return seq.playing;
    if (!strcmp(what, "view")) return ui.view;
    if (!strcmp(what, "trk")) return ui.trk;
    if (!strcmp(what, "snd")) return ui.snd;
    if (!strcmp(what, "cur")) return seq.tpat[ui.trk];             /* the selected track's pattern */
    if (sscanf(what, "pat.%d", &t) == 1) return seq.tpat[t];
    if (!strcmp(what, "mute")) return seq.mute;
    if (!strcmp(what, "dirty")) return ui.dirty;
    if (!strcmp(what, "bpm")) return (int)(seq.bpm * 10.0f + 0.5f);   /* the tempo x 10 */
    if (!strcmp(what, "oct")) return ui.oct;
    if (!strcmp(what, "barbeat")) return (bar_key() / 4 + 1) * 10 + bar_key() % 4 + 1;   /* 2.3 -> 23 */
    if (!strcmp(what, "topbar")) return ui.last_bar;               /* what the top line shows */
    if (sscanf(what, "dmac.%d.%d", &t, &s) == 2) return proj.sound.dmac[t][s];
    if (sscanf(what, "b303.%d.%d", &t, &s) == 2) return proj.sound.b303[t][s];
    if (!strcmp(what, "litkeys")) return (int)lit_keys;          /* the keys lit (bits), 0 = none */
    if (!strcmp(what, "peak_min")) return (int)(peak * 100.0f);
    if (sscanf(what, "type.%d", &t) == 1) return proj.sound.ttype[t] * 10 + seq.ttype[t];
    if (sscanf(what, "kit.%d", &t) == 1) return proj.sound.kit[t];
    if (sscanf(what, "anyhit.%d.%d", &t, &s) == 2) {          /* any step of that sound set */
        int n = 0;
        for (st = 0; st < NSTEPS; st++)
            n += sm_get(proj.pat[seq.tpat[t]].t[t].u.d.hit[s], st);
        return n;
    }
    if (sscanf(what, "anynote.%d.%d", &t, &s) == 2) {         /* steps of that 303 holding note s, gate on */
        int n = 0;
        for (st = 0; st < NSTEPS; st++)
            n += proj.pat[seq.tpat[t]].t[t].u.b.step[st].note == s && bstep_gate(&proj.pat[seq.tpat[t]].t[t].u.b.step[st]) != G_REST;
        return n;
    }
    if (sscanf(what, "heard.%d.%d", &t, &s) == 2) return eng_hit[t][s] > 0;   /* the sound played lately */
    if (sscanf(what, "len.%d", &t) == 1) return proj.pat[seq.tpat[t]].t[t].len;
    if (sscanf(what, "hit.%d.%d.%d", &t, &s, &st) == 3) return sm_get(proj.pat[seq.tpat[t]].t[t].u.d.hit[s], st);
    if (sscanf(what, "gate.%d.%d", &t, &st) == 2) return bstep_gate(&proj.pat[seq.tpat[t]].t[t].u.b.step[st]);
    if (sscanf(what, "note.%d.%d", &t, &st) == 2) return proj.pat[seq.tpat[t]].t[t].u.b.step[st].note;
    fprintf(stderr, "unknown expect %s\n", what);
    exit(2);
}

int main(int argc, char **argv)
{
    FILE *sc;
    char line[512], wavpath[512] = "";
    const char *dir = argc > 2 ? argv[2] : ".";
    int lineno = 0;
    if (argc < 2) {
        fprintf(stderr, "usage: gc_host SCRIPT [OUTDIR]\n");
        return 2;
    }
    sc = fopen(argv[1], "r");
    if (!sc) {
        perror(argv[1]);
        return 2;
    }
    boot();
    while (fgets(line, sizeof line, sc)) {
        char cmd[32] = {0}, a[128] = {0}, b[64] = {0};
        lineno++;
        if (line[0] == '#' || sscanf(line, "%31s %127s %63s", cmd, a, b) < 1)
            continue;
        if (!strcmp(cmd, "wait")) run((uint32_t)atoi(a));
        else if (!strcmp(cmd, "tap")) { held_btn |= 1u << btn_of(a); run(30); held_btn &= ~(1u << btn_of(a)); run(30); }
        else if (!strcmp(cmd, "hold")) { held_btn |= 1u << btn_of(a); run(30); }
        else if (!strcmp(cmd, "release")) { held_btn &= ~(1u << btn_of(a)); run(30); }
        else if (!strcmp(cmd, "tapkey")) { held_keys |= 1u << key_of(a); run(30); held_keys &= ~(1u << key_of(a)); run(30); }
        else if (!strcmp(cmd, "holdkey")) { held_keys |= 1u << key_of(a); run(30); }
        else if (!strcmp(cmd, "releasekey")) { held_keys &= ~(1u << key_of(a)); run(30); }
        else if (!strcmp(cmd, "turn")) { enc_acc[enc_of(a)] += atoi(b); run(40); }
        else if (!strcmp(cmd, "shot")) { ui.redraw = 1; run(40); shot(dir, a); }
        else if (!strcmp(cmd, "peakreset")) peak = 0.0f;
        else if (!strcmp(cmd, "wav")) {
            snprintf(wavpath, sizeof wavpath, "%s/%s.wav", dir, a);
            wavf = fopen(wavpath, "wb");
            if (wavf)
                fseek(wavf, 44, SEEK_SET);
        } else if (!strcmp(cmd, "reboot")) {
            memset(&ui, 0, sizeof ui);
            memset(&proj, 0, sizeof proj);
            boot();
        } else if (!strcmp(cmd, "expect")) {
            int got = value_of(a), want = atoi(b);
            int ok = !strcmp(a, "peak_min") ? got >= want : got == want;
            if (!ok) {
                printf("FAIL line %d: %s is %d, want %s%d\n", lineno, a, got, !strcmp(a, "peak_min") ? ">= " : "", want);
                fails++;
            }
        } else {
            fprintf(stderr, "line %d: unknown command %s\n", lineno, cmd);
            return 2;
        }
    }
    if (wavf) {
        int32_t data = (int32_t)wav_frames * 4, riff = 36 + data, fmt = 16, rate = 44100, bps = 44100 * 4;
        int16_t pcm = 1, ch = 2, align = 4, bits = 16;
        fseek(wavf, 0, SEEK_SET);
        fwrite("RIFF", 1, 4, wavf); fwrite(&riff, 4, 1, wavf); fwrite("WAVEfmt ", 1, 8, wavf);
        fwrite(&fmt, 4, 1, wavf); fwrite(&pcm, 2, 1, wavf); fwrite(&ch, 2, 1, wavf); fwrite(&rate, 4, 1, wavf);
        fwrite(&bps, 4, 1, wavf); fwrite(&align, 2, 1, wavf); fwrite(&bits, 2, 1, wavf);
        fwrite("data", 1, 4, wavf); fwrite(&data, 4, 1, wavf);
        fclose(wavf);
    }
    printf(fails ? "%s: %d FAILED\n" : "%s: ok\n", argv[1], fails);
    return fails != 0;
}
