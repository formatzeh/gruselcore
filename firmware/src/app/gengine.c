/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore audio engine; see gengine.h. After X0X's engine.c (Charles Vestal): the command queue,
 * the gliding mix gains, the second-core split, the output scaling. */
#include "gengine.h"
#include "plat.h"
#include "../dsp/gdrum.h"
#include "../dsp/bass303.h"
#include "../dsp/fxbus.h"
#include "../dsp/master.h"
#include "../dsp/fastmath.h"

#define POOL X0X_POOL
#define TRK_SPLIT 4                    /* tracks 0..3 on the first core, 4..7 on the second */
#define DLY_LEN 44100                  /* the shared delay: 1 s (X0X had 2 s; the RAM goes to the tracks) */

volatile uint32_t eng_prof[ENG_PROF_N], eng_prof_frames;
#define PROF_T(v) uint32_t v = plat_cycles()
#define PROF_ADD(k, t0) (eng_prof[k] += plat_cycles() - (t0))

/* ---------------------------------------------------------------- state --- */
seq_t seq;
volatile uint8_t eng_step[NTRK];
volatile uint16_t eng_peak[NTRK];
volatile uint8_t eng_hit[NTRK][NDSND];
int16_t eng_scope[SCOPE_N];
volatile uint32_t eng_scope_w;

typedef struct {                       /* one track's filter and drive (stereo) */
    float g, k, a1, a2, a3;            /* TPT state-variable coefficients */
    float ic1[2], ic2[2];
    int8_t mode;                       /* 0 off, -1 low-pass, +1 high-pass */
    float drive, drive_norm;           /* 0 = clean */
} insert_t;

typedef struct {
    union { gdrum_t d; bass303_t b; } u;
    uint8_t type;                      /* TT_*: what u holds */
    uint8_t active;                    /* rendered something this stretch (else nothing to mix) */
    insert_t ins;
} track_t;

static track_t trk[NTRK] POOL;
static fxbus_t fx POOL;
static master_t mst;
static int16_t dly_buf[DLY_LEN] POOL;
static const sound_t *base_snd;        /* the project's mirror: re-read on a type change or a reload */

/* ------------------------------------------------------- command queue --- */
/* uint32 commands, single producer (main loop) / single consumer (audio ISR):
 * type:4 | a:8 | b:8 | c:12 */
enum { C_DRUM = 8, C_NON, C_NOFF };
#define CQ 1024u
static uint32_t cq[CQ] POOL;
static volatile uint32_t cq_w, cq_r;

static void cq_put(uint32_t type, uint32_t a, uint32_t b, uint32_t c)
{
    uint32_t w = cq_w;
    if (w - cq_r >= CQ)
        return;                        /* full: drop (a param flood; the mirror still has it) */
    cq[w % CQ] = (type << 28) | ((a & 0xFFu) << 20) | ((b & 0xFFu) << 12) | (c & 0xFFFu);
    __asm__ volatile("" ::: "memory");
    cq_w = w + 1;
}

void engine_set(int t, int v, int i, int val) { cq_put((uint32_t)t, (uint32_t)v, (uint32_t)i, (uint32_t)val); }
void engine_drum(int t, int s, float vel)
{
    cq_put(C_DRUM, (uint32_t)t, (uint32_t)s, (uint32_t)(fm_clampf(vel, 0.0f, 1.0f) * 4095.0f));
}
void engine_note_on(int t, int note, int accent, int slide)
{
    cq_put(C_NON, (uint32_t)t, (uint32_t)note, (uint32_t)((accent ? 1u : 0u) | (slide ? 2u : 0u)));
}
void engine_note_off(int t) { cq_put(C_NOFF, (uint32_t)t, 0, 0); }

/* ------------------------------------------------------------ params --- */
static const x0x_param_t MIX_P[MX_NPARAMS] = {
    {"LEVEL", 127, 100, 0}, {"PAN", 127, 64, 0}, {"REV", 127, 0, 0}, {"DLY", 127, 0, 0},
    {"FILTER", 127, 64, 0}, {"RESO", 127, 20, 0}, {"DRIVE", 127, 0, 0},
};
static float mix_level[NTRK], mix_pl[NTRK], mix_pr[NTRK], mix_rev[NTRK], mix_dly[NTRK];

int engine_nvoices(int t)
{
    switch (t) {
    case T_DRUM: return NTRK * NDSND;
    case T_303: case T_MIX: case T_TRK: return NTRK;
    case T_FX: return (fxbus_nparams() + 15) / 16;
    case T_MST: return 1;
    default: return 0;
    }
}

int engine_nparams(int t, int v)
{
    switch (t) {
    case T_DRUM: return GP_N;
    case T_303: return BASS303_NPARAMS;
    case T_MIX: return MX_NPARAMS;
    case T_FX: {
        int n = fxbus_nparams() - v * 16;
        return n < 0 ? 0 : n > 16 ? 16 : n;
    }
    case T_MST: return MST_NPARAMS;
    default: return 0;
    }
}

const x0x_param_t *engine_param(int t, int v, int i)
{
    if (i < 0 || i >= engine_nparams(t, v))
        return 0;
    switch (t) {
    case T_DRUM: return gdrum_param(i);
    case T_303: return bass303_param(i);
    case T_MIX: return &MIX_P[i];
    case T_FX: return fxbus_param(v * 16 + i);
    case T_MST: return master_param(i);
    default: return 0;
    }
}

/* the insert's filter: FILTER 64 = off; under it a low-pass sweeping from 20 kHz down to 60 Hz,
 * over it a high-pass sweeping from 20 Hz up to 6 kHz; RESO from gentle to sharp */
static void insert_calc(insert_t *ins, const uint8_t *m)
{
    int f = m[MX_FILTER];
    float fc, g;
    ins->mode = (int8_t)(f < 62 ? -1 : f > 66 ? 1 : 0);
    if (ins->mode < 0)
        fc = 60.0f * fm_exp2f(8.38f * (float)f / 62.0f);              /* 60 Hz .. 20 kHz */
    else
        fc = 20.0f * fm_exp2f(8.23f * (float)(f - 66) / 61.0f);       /* 20 Hz .. 6 kHz */
    fc = fm_minf(fc, 18000.0f);
    g = fm_tanf(3.14159265f * fc / 44100.0f);
    ins->g = g;
    ins->k = 2.0f - 1.9f * (float)m[MX_RESO] / 127.0f;                 /* 1/Q: 2 (soft) .. 0.1 (sharp) */
    ins->a1 = 1.0f / (1.0f + g * (g + ins->k));
    ins->a2 = g * ins->a1;
    ins->a3 = g * ins->a2;
    ins->drive = m[MX_DRIVE] ? fm_exp2f(4.3f * (float)m[MX_DRIVE] / 127.0f) : 0.0f;   /* 1 .. 20 */
    ins->drive_norm = ins->drive > 0.0f ? 1.0f / fm_tanhf(fm_minf(ins->drive, 3.0f)) * 0.7f : 1.0f;
}

static void mix_calc(int t)
{
    const uint8_t *m = base_snd->mix[t];
    float lv = (float)m[MX_LEVEL] / 100.0f;
    mix_level[t] = lv * lv;
    x0x_pan_gains(m[MX_PAN], &mix_pl[t], &mix_pr[t]);
    mix_rev[t] = (float)m[MX_REV] / 127.0f;
    mix_dly[t] = (float)m[MX_DLY] / 127.0f;
    insert_calc(&trk[t].ins, m);
}

/* track t's engine for type tt, every pot from the project's sound */
static void track_load(int t, int tt)
{
    track_t *k = &trk[t];
    int s, i;
    if (k->type == TT_303 && tt != TT_303)
        bass303_all_off(&k->u.b);
    if (tt != k->type) {
        if (tt == TT_DRUM)
            gdrum_init(&k->u.d);
        else if (tt == TT_303)
            bass303_init(&k->u.b);
        k->type = (uint8_t)tt;
        k->ins.ic1[0] = k->ins.ic1[1] = k->ins.ic2[0] = k->ins.ic2[1] = 0.0f;
    }
    if (tt == TT_DRUM)
        for (s = 0; s < NDSND; s++)
            for (i = 0; i < GP_N; i++)
                gdrum_set(&k->u.d, s, i, base_snd->drum[t][s][i]);
    else if (tt == TT_303)
        for (i = 0; i < BASS303_NPARAMS; i++)
            bass303_set(&k->u.b, i, base_snd->b303[t][i]);
    seq.ttype[t] = (uint8_t)tt;
    mix_calc(t);
}

static void apply_param(int target, int v, int i, int val)
{
    switch (target) {
    case T_DRUM:
        if (v / NDSND < NTRK && trk[v / NDSND].type == TT_DRUM)
            gdrum_set(&trk[v / NDSND].u.d, v % NDSND, i, val);
        break;
    case T_303:
        if (v < NTRK && trk[v].type == TT_303)
            bass303_set(&trk[v].u.b, i, val);
        break;
    case T_MIX:
        if (v < NTRK)
            mix_calc(v);                               /* (reads the mirror: the main loop wrote it first) */
        break;
    case T_FX:
        fxbus_set(&fx, v * 16 + i, val);
        break;
    case T_MST:
        master_set(&mst, i, val);
        break;
    case T_TRK:
        if (v < NTRK)
            track_load(v, i == TK_TYPE ? val : trk[v].type);
        break;
    default:
        break;
    }
}

/* ------------------------------------------------------------- sink --- */
static int s_drum(void *ctx, int t, int s, float vel)
{
    (void)ctx;
    if (t < 0 || t >= NTRK || trk[t].type != TT_DRUM)
        return 0;
    gdrum_trigger(&trk[t].u.d, s, vel);
    eng_hit[t][s] = (uint8_t)(vel * 255.0f);
    if (s == GD_KICK && base_snd->drum[t][s][GP_MODEL] == GDM_KICK)
        master_key(&mst, 0, vel);                      /* the PUMP follows every drum track's kick */
    return 1;
}
static void s_note_on(void *ctx, int t, int note, int accent, int slide)
{
    (void)ctx;
    if (t >= 0 && t < NTRK && trk[t].type == TT_303)
        bass303_note_on(&trk[t].u.b, note, accent, slide);
}
static void s_note_off(void *ctx, int t)
{
    (void)ctx;
    if (t >= 0 && t < NTRK && trk[t].type == TT_303)
        bass303_note_off(&trk[t].u.b);
}
static void s_midi(void *ctx, uint8_t st, uint8_t d1, uint8_t d2)
{
    uint32_t cin = st >= 0xF0 ? 0x0Fu : (uint32_t)(st >> 4);     /* USB-MIDI code index */
    (void)ctx;
    plat_midi_out(cin | ((uint32_t)st << 8) | ((uint32_t)d1 << 16) | ((uint32_t)d2 << 24));
}
static void s_step(void *ctx, int t, int p)
{
    (void)ctx;
    if (t >= 0 && t < NTRK)
        eng_step[t] = (uint8_t)p;
}
static const seq_sink_t SINK = {s_drum, s_note_on, s_note_off, s_midi, s_step, 0};

/* MIDI in: transport and clock, then each track's notes on its channel (drums on GM notes) */
static uint8_t note_held[NTRK];
static void midi_in(uint32_t pkt)
{
    static const uint8_t GM[NDSND] = {36, 38, 39, 42, 46, 45, 37, 56};
    uint8_t st = (uint8_t)(pkt >> 8), d1 = (uint8_t)(pkt >> 16) & 0x7F, d2 = (uint8_t)(pkt >> 24) & 0x7F;
    uint8_t ch = st & 0x0F, ty = st & 0xF0;
    int t, v;
    switch (st) {
    case 0xF8: gseq_ext_clock(&seq); return;
    case 0xFA: gseq_start(&seq); return;
    case 0xFB: gseq_continue(&seq); return;
    case 0xFC: gseq_stop(&seq); return;
    default: break;
    }
    if (ty == 0x90 && d2 == 0)
        ty = 0x80;
    for (t = 0; t < NTRK; t++) {
        if (seq.ch[t] != ch)
            continue;
        if (trk[t].type == TT_DRUM && ty == 0x90) {
            for (v = 0; v < NDSND; v++)
                if (GM[v] == d1)
                    s_drum(0, t, v, (float)d2 / 127.0f);
        } else if (trk[t].type == TT_303) {
            if (ty == 0x90) {
                bass303_note_on(&trk[t].u.b, d1, d2 >= 100, note_held[t] != 0);
                note_held[t] = d1;
            } else if ((ty == 0x80 && note_held[t] == d1) || (ty == 0xB0 && (d1 == 120 || d1 == 123))) {
                bass303_note_off(&trk[t].u.b);
                note_held[t] = 0;
            }
        }
    }
}

static void drain(void)
{
    uint32_t r = cq_r, pkt;
    int guard = 64;
    while (r != cq_w) {
        uint32_t c = cq[r % CQ], type = c >> 28, a = (c >> 20) & 0xFFu, b = (c >> 12) & 0xFFu, v = c & 0xFFFu;
        r++;
        if (type < 8u)
            apply_param((int)type, (int)a, (int)b, (int)v);
        else if (type == C_DRUM)
            s_drum(0, (int)a, (int)b, (float)v / 4095.0f);
        else if (type == C_NON)
            s_note_on(0, (int)a, (int)b, (int)(v & 1u), (int)((v >> 1) & 1u));
        else if (type == C_NOFF)
            s_note_off(0, (int)a);
    }
    cq_r = r;
    while (guard-- && plat_midi_in(&pkt))
        midi_in(pkt);
}

/* ---------------------------------------------------------- overload --- */
/* past the CPU (a block over 92 %, or 85 % on average) every 303 drops its oversampling; after 3 s
 * back under 65 % it returns (X0X's guard) */
#define GUARD_ON_LAST 92u
#define GUARD_ON_AVG 85u
#define GUARD_OFF 65u
#define GUARD_CALM_FRAMES (3u * 44100u)
static uint8_t guard_on, guard_applied;
static uint32_t guard_avg_q8, guard_calm;
volatile uint32_t eng_guard_count;
int engine_guard_active(void) { return guard_on; }
void engine_load(uint32_t pct, uint32_t frames)
{
    guard_avg_q8 = (guard_avg_q8 * 15u + pct * 256u) / 16u;
    if (!guard_on) {
        if (pct > GUARD_ON_LAST || guard_avg_q8 > GUARD_ON_AVG * 256u) {
            guard_on = 1;
            guard_calm = 0;
            eng_guard_count++;
        }
    } else if (pct >= GUARD_OFF || guard_avg_q8 >= GUARD_OFF * 256u) {
        guard_calm = 0;
    } else if ((guard_calm += frames) >= GUARD_CALM_FRAMES) {
        guard_on = 0;
    }
}
static void guard_apply(void)
{
    int t;
    if (guard_on == guard_applied)
        return;
    guard_applied = guard_on;
    for (t = 0; t < NTRK; t++)
        if (trk[t].type == TT_303)
            bass303_set_lite(&trk[t].u.b, guard_on);
}

/* ------------------------------------------------------------ mixing --- */
/* a mix gain that glides to its target (one pole, ~10 ms), so quick knob turns don't zipper */
typedef struct { float cur, tgt; } glide_t;
#define GLIDE_A 0.0022651f
static void glide_set(glide_t *g, float t)
{
    g->tgt = t;
    if (g->cur < 0.0f)
        g->cur = t;
}
__attribute__((noinline)) static void add_glide(float *dst, const float *src, glide_t *g, uint32_t n)
{
    uint32_t i;
    float c = g->cur, t = g->tgt;
    if (c == t) {
        if (c != 0.0f)
            for (i = 0; i < n; i++)
                dst[i] += src[i] * c;
        return;
    }
    for (i = 0; i < n; i++) {
        c += (t - c) * GLIDE_A;
        dst[i] += src[i] * c;
    }
    if (fm_fabsf(t - c) < 1e-5f)
        c = t;
    g->cur = c;
}
enum { GL_L, GL_R, GL_REV, GL_DLY, GL_N };
static glide_t mix_glide[NTRK][GL_N];

static float dry_l[256], dry_r[256], rev[256], dly[256];
static float tl[NTRK - TRK_SPLIT][256] POOL, trr[NTRK - TRK_SPLIT][256] POOL;   /* the second core's tracks */
static float sl[256], sr[256];                                                  /* the first core's scratch */
static float trk_peak[NTRK];

/* track t's engine into l, r (zeroed here). Returns 0 when it is silent (nothing written). */
static int track_render(int t, float *l, float *r, uint32_t n)
{
    track_t *k = &trk[t];
    uint32_t i;
    if (k->type == TT_DRUM) {
        if (!gdrum_active(&k->u.d))
            return 0;
        for (i = 0; i < n; i++)
            l[i] = r[i] = 0.0f;
        gdrum_render_st(&k->u.d, l, r, (int)n);
        return 1;
    }
    if (k->type == TT_303) {
        if (k->u.b.idle)
            return 0;
        bass303_render(&k->u.b, l, (int)n);
        for (i = 0; i < n; i++)                         /* Open303 sits ~17 dB under the drum kits */
            r[i] = l[i] = l[i] * B303_GAIN;               /* (gengine.h: the same loudness at LEVEL 100) */
        return 1;
    }
    return 0;
}

/* the track's filter and drive, in place */
__attribute__((noinline)) static void track_insert(insert_t *ins, float *l, float *r, uint32_t n)
{
    uint32_t i;
    int c;
    if (ins->mode) {
        for (c = 0; c < 2; c++) {
            float *x = c ? r : l, ic1 = ins->ic1[c], ic2 = ins->ic2[c];
            const float a1 = ins->a1, a2 = ins->a2, a3 = ins->a3, k = ins->k;
            for (i = 0; i < n; i++) {
                float v3 = x[i] - ic2, v1 = a1 * ic1 + a2 * v3, v2 = ic2 + a2 * ic1 + a3 * v3;
                ic1 = 2.0f * v1 - ic1;
                ic2 = 2.0f * v2 - ic2;
                x[i] = ins->mode < 0 ? v2 : x[i] - k * v1 - v2;
            }
            ins->ic1[c] = fm_flush(ic1);
            ins->ic2[c] = fm_flush(ic2);
        }
    }
    if (ins->drive > 0.0f) {
        const float d = ins->drive, nrm = ins->drive_norm;
        for (i = 0; i < n; i++) {
            l[i] = fm_tanhf(l[i] * d) * nrm;
            r[i] = fm_tanhf(r[i] * d) * nrm;
        }
    }
}

/* a rendered track into the mix: its insert, then level, pan and sends (gliding), and its meter */
static void track_mix(int t, float *l, float *r, uint32_t n)
{
    float g = mix_level[t], pk = trk_peak[t];
    uint32_t i;
    track_insert(&trk[t].ins, l, r, n);
    glide_set(&mix_glide[t][GL_L], g * mix_pl[t]);
    glide_set(&mix_glide[t][GL_R], g * mix_pr[t]);
    glide_set(&mix_glide[t][GL_REV], g * mix_rev[t]);
    glide_set(&mix_glide[t][GL_DLY], g * mix_dly[t]);
    add_glide(dry_l, l, &mix_glide[t][GL_L], n);
    add_glide(dry_r, r, &mix_glide[t][GL_R], n);
    for (i = 0; i < n; i++) {
        float m = (l[i] + r[i]) * 0.5f, a = fm_fabsf(m) * g;
        l[i] = m;                                      /* the sends are mono */
        if (a > pk)
            pk = a;
    }
    add_glide(rev, l, &mix_glide[t][GL_REV], n);
    add_glide(dly, l, &mix_glide[t][GL_DLY], n);
    trk_peak[t] = pk;
}

/* the second core's job (or the first's, with one core): tracks TRK_SPLIT.. into their own buffers.
 * Nothing is mixed here: the first core mixes afterwards, always in track order */
static uint8_t c2_active[NTRK - TRK_SPLIT];
static void core2_job(uint32_t arg)
{
    uint32_t n = arg & 0x1FFu ? arg & 0x1FFu : 256u;
    int t;
    if (n > 256u)
        n = 256u;
    for (t = TRK_SPLIT; t < NTRK; t++)
        c2_active[t - TRK_SPLIT] = (uint8_t)track_render(t, tl[t - TRK_SPLIT], trr[t - TRK_SPLIT], n);
}

static void render_sub(float *out_l, float *out_r, uint32_t n)
{
    uint32_t i;
    int t, on2 = plat_cpu2_run(core2_job, n);
    for (i = 0; i < n; i++)
        dry_l[i] = dry_r[i] = rev[i] = dly[i] = 0.0f;
    for (t = 0; t < TRK_SPLIT; t++) {
        PROF_T(pt);
        if (track_render(t, sl, sr, n))
            track_mix(t, sl, sr, n);
        PROF_ADD(PR_TRK0 + t, pt);
    }
    if (!on2 || plat_cpu2_wait())
        core2_job(n);                                  /* one core (or the second failed): here */
    for (t = TRK_SPLIT; t < NTRK; t++)
        if (c2_active[t - TRK_SPLIT])
            track_mix(t, tl[t - TRK_SPLIT], trr[t - TRK_SPLIT], n);
    {
        PROF_T(pf);
        fxbus_process_st(&fx, dry_l, dry_r, rev, dly, out_l, out_r, (int)n);
        PROF_ADD(PR_FX, pf);
    }
}

/* ------------------------------------------------------------ output --- */
static volatile float out_scale = 4194303.0f, out_lim = 2.0f;
void engine_out_loud(int on)
{
    out_scale = on ? 8388607.0f : 4194303.0f;
    out_lim = on ? 1.0f : 2.0f;
}
static volatile int usb_full;
static float vol_after = -1.0f;
void engine_usb_full(int on) { usb_full = on; }
void engine_volume(int32_t *out_lr, uint32_t n)
{
    float vol = (float)plat_master() / 4096.0f, v = vol_after < 0.0f ? vol : vol_after;
    uint32_t i;
    if (!usb_full) {
        vol_after = -1.0f;
        return;
    }
    for (i = 0; i < n; i++) {
        if (v != vol) {
            v += (vol - v) * 0.0022651f;
            if (fm_fabsf(vol - v) < 1e-5f)
                v = vol;
        }
        out_lr[2u * i] = (int32_t)((float)out_lr[2u * i] * v);
        out_lr[2u * i + 1u] = (int32_t)((float)out_lr[2u * i + 1u] * v);
    }
    vol_after = v;
}
float engine_gr_db(void) { return mst.gr_view; }

void engine_render(int32_t *out_lr, uint32_t n)
{
    static float out_l[256], out_r[256];
    uint32_t done = 0, i;
    float vol = usb_full ? 1.0f : (float)plat_master() / 4096.0f;
    int t;
    if (n > 256u)
        n = 256u;
    eng_prof_frames += n;
    guard_apply();
    {
        PROF_T(pt);
        drain();
        fxbus_set_bpm(&fx, gseq_tempo(&seq));
        gseq_advance(&seq, 0, &SINK);
        PROF_ADD(PR_SEQ, pt);
    }
    while (done < n) {
        uint32_t k = gseq_until_event(&seq, n - done);
        render_sub(out_l + done, out_r + done, k);
        {
            PROF_T(pt);
            gseq_advance(&seq, k, &SINK);
            PROF_ADD(PR_SEQ, pt);
        }
        done += k;
    }
    {
        PROF_T(pt);
        master_process_st(&mst, out_l, out_r, (int)n, vol);
        PROF_ADD(PR_MST, pt);
    }
    for (i = 0; i < n; i++) {
        float l = out_l[i], r = out_r[i];
        l = l > out_lim ? out_lim : l < -out_lim ? -out_lim : l;
        r = r > out_lim ? out_lim : r < -out_lim ? -out_lim : r;
        out_lr[2u * i] = (int32_t)(l * out_scale);
        out_lr[2u * i + 1u] = (int32_t)(r * out_scale);
        if (i & 1u)
            eng_scope[eng_scope_w++ & (SCOPE_N - 1u)] = (int16_t)((out_l[i] + out_r[i]) * 16383.5f);
    }
    for (t = 0; t < NTRK; t++) {                       /* meters: peak hold, the UI lets them fall */
        uint32_t q = (uint32_t)(fm_minf(trk_peak[t], 1.0f) * 32767.0f);
        if (q > eng_peak[t])
            eng_peak[t] = (uint16_t)q;
        trk_peak[t] = 0.0f;
    }
}

/* ------------------------------------------------------- sound setup --- */
/* the power-on sound: tracks 1-2 drums (Hardtek kit, its percussion kit), 3-4 303s, 5-8 off;
 * every engine's own defaults for the rest */
void engine_sound_defaults(sound_t *s)
{
    static const uint8_t TT[NTRK] = {TT_DRUM, TT_DRUM, TT_303, TT_303, TT_OFF, TT_OFF, TT_OFF, TT_OFF};
    int t, i, v;
    uint8_t *b = (uint8_t *)s;
    for (i = 0; i < (int)sizeof *s; i++)
        b[i] = 0;
    for (t = 0; t < NTRK; t++) {
        s->ttype[t] = TT[t];
        for (v = 0; v < NDSND; v++)
            for (i = 0; i < GP_N; i++)
                s->drum[t][v][i] = gd_kits[0].pot[v][i];
        for (i = 0; i < BASS303_NPARAMS; i++)
            s->b303[t][i] = bass303_param(i)->def;
        for (i = 0; i < MX_NPARAMS; i++)
            s->mix[t][i] = MIX_P[i].def;
    }
    for (i = 0; i < fxbus_nparams() && i < FX_NP; i++)
        s->fx[i] = fxbus_param(i)->def;
    for (i = 0; i < MST_NPARAMS && i < MST_NP; i++)
        s->mst[i] = master_param(i)->def;
    {   /* track 2: the Tribe percussion kit */
        int k = gd_nkits > 10 ? 10 : 0;
        for (v = 0; v < NDSND; v++)
            for (i = 0; i < GP_N; i++)
                s->drum[1][v][i] = gd_kits[k].pot[v][i];
        s->kit[1] = (uint8_t)k;
    }
}

void engine_track_kit(sound_t *s, int t, int kit)
{
    int v, i;
    if (t < 0 || t >= NTRK || kit < 0 || kit >= gd_nkits)
        return;
    for (v = 0; v < NDSND; v++)
        for (i = 0; i < GP_N; i++)
            s->drum[t][v][i] = gd_kits[kit].pot[v][i];
    s->kit[t] = (uint8_t)kit;
    engine_set(T_TRK, t, TK_RELOAD, 0);
}

void engine_apply_sound(const sound_t *s)
{
    int t, i;
    for (t = 0; t < NTRK; t++)
        engine_set(T_TRK, t, TK_TYPE, s->ttype[t]);   /* the engine re-reads the track's pots itself */
    for (i = 0; i < fxbus_nparams() && i < FX_NP; i++)
        engine_set(T_FX, i / 16, i % 16, s->fx[i]);
    for (i = 0; i < MST_NPARAMS && i < MST_NP; i++)
        engine_set(T_MST, 0, i, s->mst[i]);
}

void engine_init(pattern_t *patterns, const sound_t *base)
{
    int t, g;
    base_snd = base;
    for (t = 0; t < NTRK; t++) {
        trk[t].type = TT_OFF;
        mix_level[t] = 1.0f;
        mix_pl[t] = mix_pr[t] = 1.0f;
        for (g = 0; g < GL_N; g++)
            mix_glide[t][g].cur = -1.0f;
    }
    fxbus_init(&fx, dly_buf, DLY_LEN);
    master_init(&mst);
    gseq_init(&seq, patterns);
}
