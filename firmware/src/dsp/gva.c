/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore VA synth; see gva.h. */
#include "gva.h"
#include "fastmath.h"

#define FS 44100.0f

static const char *const WAVE_N[VAW_N] = {"SAW", "SQR", "TRI", "SINE"};
static const char *const MODE_N[VAM_N] = {"MONO", "CHORD", "UNISN", "HYPER"};
static const char *const FTYPE_N[VAF_N] = {"LP24", "LP12", "BP", "HP"};
static const char *const LSHAPE_N[VAL_N] = {"TRI", "SAW", "SQR", "S&H"};
#define NLRATES 12
static const char *const LRATE_N[NLRATES] = {"8 BAR", "4 BAR", "2 BAR", "1 BAR", "1/2", "1/4", "1/4T",
                                             "1/8", "1/8T", "1/16", "16T", "1/32"};
static const float LRATE_BEATS[NLRATES] = {32.0f, 16.0f, 8.0f, 4.0f, 2.0f, 1.0f, 2.0f / 3.0f,
                                           0.5f, 1.0f / 3.0f, 0.25f, 1.0f / 6.0f, 0.125f};

static const x0x_param_t P[VA_N] = {
    {"WAVE 1", VAW_N - 1, VAW_SAW, WAVE_N}, {"WAVE 2", VAW_N - 1, VAW_SAW, WAVE_N},
    {"TUNE 2", 48, 24, 0},                  {"DETUNE", 127, 12, 0},
    {"MIX", 127, 64, 0},                    {"SUB", 127, 0, 0},
    {"NOISE", 127, 0, 0},                   {"PW", 127, 64, 0},
    {"CUTOFF", 127, 80, 0},                 {"RESO", 127, 20, 0},
    {"ENV", 127, 40, 0},                    {"FILTER", VAF_N - 1, VAF_LP24, FTYPE_N},
    {"F.ATT", 127, 0, 0},                   {"F.DEC", 127, 50, 0},
    {"F.SUS", 127, 0, 0},                   {"KEYTRK", 127, 64, 0},
    {"ATTACK", 127, 0, 0},                  {"DECAY", 127, 60, 0},
    {"SUSTN", 127, 100, 0},                 {"RELEAS", 127, 20, 0},
    {"MODE", VAM_N - 1, VAM_MONO, MODE_N},  {"GLIDE", 127, 0, 0},
    {"ACCENT", 127, 64, 0},                 {"VOLUME", 127, 100, 0},
    {"LFO", NLRATES - 1, 7, LRATE_N},       {"SHAPE", VAL_N - 1, VAL_TRI, LSHAPE_N},
    {"L>PTCH", 127, 0, 0},                  {"L>CUT", 127, 0, 0},
};

const x0x_param_t *gva_param(int i) { return i >= 0 && i < VA_N ? &P[i] : 0; }
int gva_get(const gva_t *va, int i) { return i >= 0 && i < VA_N ? va->pot[i] : 0; }

/* an envelope time: 1 ms .. 10 s, exponential over the pot */
static float env_time(int p) { return 0.001f * fm_exp2f((float)p * (13.3f / 127.0f)); }
/* one control step of an exponential segment that falls to -30 dB over t */
static float seg_k(float t) { return fm_expf(-(float)GVA_CR * 3.5f / (t * FS)); }

static void calc(gva_t *va, int i)
{
    const uint8_t *p = va->pot;
    float x = (float)p[i] / 127.0f;
    switch (i) {
    case VA_ATT: va->a_inc = (float)GVA_CR / (env_time(p[i]) * FS); break;
    case VA_DEC: va->d_k = seg_k(env_time(p[i])); break;
    case VA_SUS: va->sus = x * x; break;
    case VA_REL: va->r_k = seg_k(env_time(p[i])); break;
    case VA_FATT: va->fa_inc = (float)GVA_CR / (env_time(p[i]) * FS); break;
    case VA_FDEC: va->fd_k = seg_k(env_time(p[i])); break;
    case VA_FSUS: va->fsus = x; break;
    case VA_PW: va->pw = fm_clampf(0.5f + ((float)p[i] - 64.0f) * (0.9f / 127.0f), 0.05f, 0.95f); break;
    case VA_MIX: va->mix = x; break;
    case VA_SUB: va->sub = x * 0.8f; break;
    case VA_NOISE: va->noise = x * x * 0.7f; break;
    case VA_DETUNE: va->det = x * x * 0.6f; break;          /* up to 0.6 semitones */
    case VA_CUTOFF: va->cut = x * 9.2f; break;              /* octaves over 30 Hz: up to ~17.6 kHz */
    case VA_RESO: va->reso = x; break;
    case VA_ENV: va->envamt = x * 7.0f; break;
    case VA_KEYTRK: va->keytrk = x; break;
    case VA_LPITCH: va->lpitch = x * x * 12.0f; break;      /* up to an octave either way */
    case VA_LCUT: va->lcut = x * 4.0f; break;               /* up to 4 octaves either way */
    case VA_ACCENT: va->accamt = x; break;
    case VA_GLIDE: va->glide_t = p[i] ? 0.002f + 0.5f * x * x : 0.0f; break;
    case VA_VOLUME: va->gain = p[i] ? fm_db2lin(((float)p[i] - 100.0f) * 0.35f) : 0.0f; break;   /* 0.35 dB a step */
    default: break;
    }
}

void gva_set(gva_t *va, int i, int value)
{
    if (i < 0 || i >= VA_N)
        return;
    va->pot[i] = (uint8_t)(value < 0 ? 0 : value > P[i].max ? P[i].max : value);
    calc(va, i);
}

void gva_init(gva_t *va)
{
    uint8_t *b = (uint8_t *)va;
    unsigned i;
    for (i = 0; i < sizeof *va; i++)
        b[i] = 0;
    for (i = 0; i < VA_N; i++)
        gva_set(va, (int)i, P[i].def);
    va->idle = 1;
    va->bpm = 145.0f;
    va->rng = 0x2545F491u;
}

void gva_set_bpm(gva_t *va, float bpm) { va->bpm = bpm; }
void gva_set_lite(gva_t *va, int on) { va->lite = (uint8_t)(on != 0); }

static uint32_t rnd(gva_t *va)
{
    uint32_t x = va->rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return va->rng = x;
}

/* the slots playing these notes; glide from where each slot is when it sounds and glides */
void gva_note_on(gva_t *va, const uint8_t *notes, int n, int accent, int slide)
{
    int mode = va->pot[VA_MODE], i, nv, sounding = va->aenv_st != 0 && va->aenv_st != 3;
    float tau;
    if (n < 1)
        return;
    if (va->lite)
        mode = VAM_MONO;
    nv = mode == VAM_CHORD ? (n > GVA_NCHORD ? GVA_NCHORD : n) : mode == VAM_UNISON ? GVA_NCHORD :
         mode == VAM_HYPER ? GVA_NV : 1;
    tau = slide && sounding ? (va->glide_t > 0.04f ? va->glide_t : 0.04f) : va->aenv_st ? va->glide_t : 0.0f;
    va->glide_k = tau > 0.0f ? 1.0f - fm_expf(-(float)GVA_CR / (tau * FS)) : 0.0f;
    for (i = 0; i < GVA_NV; i++) {
        gva_voice_t *v = &va->v[i];
        if (i >= nv) {
            v->on = 0;
            continue;
        }
        v->target = (float)notes[mode == VAM_CHORD ? i : 0];
        v->off = mode == VAM_UNISON ? va->det * (-1.0f + (float)i * (2.0f / 3.0f)) :
                 mode == VAM_HYPER ? va->det * 2.0f * (float)(i - 3) * (1.0f / 3.0f) : 0.0f;
        if (!v->on || va->glide_k == 0.0f)
            v->note = v->target;
        if (!v->on) {                                 /* a fresh slot starts its phases apart */
            v->ph1 = (float)(rnd(va) >> 8) * (1.0f / 16777216.0f);
            v->ph2 = (float)(rnd(va) >> 8) * (1.0f / 16777216.0f);
        }
        v->on = 1;
    }
    va->nv = (uint8_t)nv;
    if (!(slide && sounding)) {                       /* a new note: the envelopes again, from where they are */
        va->aenv_st = 1;
        va->fenv_st = 1;
        va->accent = accent ? 1.0f : 0.0f;
    }
    va->gate = 1;
    va->idle = 0;
    va->cr_left = 0;                                  /* the control step now: pitch and amp follow at once */
}

void gva_note_add(gva_t *va, int note)
{
    uint8_t nt = (uint8_t)note;
    if (va->pot[VA_MODE] == VAM_CHORD && !va->lite && va->gate && va->nv < GVA_NCHORD) {
        gva_voice_t *v = &va->v[va->nv++];
        v->target = v->note = (float)note;
        v->off = 0.0f;
        v->on = 1;
        return;
    }
    gva_note_on(va, &nt, 1, 0, 1);
}

void gva_note_off(gva_t *va)
{
    va->gate = 0;
    if (va->aenv_st)
        va->aenv_st = 3;
    if (va->fenv_st)
        va->fenv_st = 3;
}

void gva_all_off(gva_t *va)
{
    int i;
    va->gate = 0;
    va->aenv_st = va->fenv_st = 0;
    va->aenv = va->fenv = va->amp = va->amp_step = 0.0f;
    va->s1a = va->s1b = va->s2a = va->s2b = 0.0f;
    for (i = 0; i < GVA_NV; i++)
        va->v[i].on = 0;
    va->nv = 0;
    va->idle = 1;
}

static void env_step(float *e, uint8_t *st, float inc, float dk, float sus, float rk)
{
    switch (*st) {
    case 1:
        *e += inc;
        if (*e >= 1.0f) {
            *e = 1.0f;
            *st = 2;
        }
        break;
    case 2:
        *e = sus + (*e - sus) * dk;
        if (sus == 0.0f && *e < 1e-4f) {              /* decayed to nothing (-80 dB): done, no denormals */
            *e = 0.0f;
            *st = 0;
        }
        break;
    case 3:
        *e *= rk;
        if (*e < 1e-4f) {
            *e = 0.0f;
            *st = 0;
        }
        break;
    default:
        *e = 0.0f;
        break;
    }
}

static void svf_coef(float *c, float g, float k)
{
    c[0] = 1.0f / (1.0f + g * (g + k));
    c[1] = g * c[0];
    c[2] = g * c[1];
}

static float note_inc(float semis) { return 440.0f * fm_exp2f((semis - 69.0f) * (1.0f / 12.0f)) * (1.0f / FS); }

/* the control step: LFO, glide, envelopes, the oscillators' increments, the filter, the amp's ramp */
static void control(gva_t *va)
{
    const uint8_t *p = va->pot;
    float lfo, cutoct, fc, g, tgt, n0 = 60.0f, tune2;
    int i;
    {   /* LFO, synced to the tempo */
        float cyc = va->bpm * (1.0f / 60.0f) / LRATE_BEATS[p[VA_LRATE] % NLRATES] * ((float)GVA_CR / FS);
        va->lfo_ph += cyc;
        if (va->lfo_ph >= 1.0f) {
            va->lfo_ph -= fm_floorf(va->lfo_ph);
            va->lfo_sh = (float)(int32_t)rnd(va) * (1.0f / 2147483648.0f);
        }
        switch (p[VA_LSHAPE]) {
        case VAL_SAW: lfo = 1.0f - 2.0f * va->lfo_ph; break;
        case VAL_SQR: lfo = va->lfo_ph < 0.5f ? 1.0f : -1.0f; break;
        case VAL_SH: lfo = va->lfo_sh; break;
        default: lfo = va->lfo_ph < 0.5f ? 4.0f * va->lfo_ph - 1.0f : 3.0f - 4.0f * va->lfo_ph; break;
        }
        va->lfo_val = lfo;
    }
    env_step(&va->aenv, &va->aenv_st, va->a_inc, va->d_k, va->sus, va->r_k);
    env_step(&va->fenv, &va->fenv_st, va->fa_inc, va->fd_k, va->fsus, va->r_k);
    if (!va->aenv_st) {                               /* released, or decayed with no sustain: silent */
        gva_all_off(va);
        return;
    }
    tune2 = (float)p[VA_TUNE2] - 24.0f;
    for (i = 0; i < GVA_NV; i++) {
        gva_voice_t *v = &va->v[i];
        float s;
        if (!v->on)
            continue;
        if (va->glide_k > 0.0f) {
            v->note += (v->target - v->note) * va->glide_k;
            if (fm_fabsf(v->target - v->note) < 0.001f)
                v->note = v->target;
        } else {
            v->note = v->target;
        }
        s = v->note + v->off + lfo * va->lpitch;
        v->dt1 = fm_minf(note_inc(s), 0.45f);
        v->dt2 = fm_minf(note_inc(s + tune2 + va->det), 0.45f);
        v->dts = v->dt1 * 0.5f;
        if (i == 0)
            n0 = v->note;
    }
    /* the filter: cutoff in octaves over 30 Hz */
    cutoct = va->cut + va->envamt * va->fenv * (1.0f + 0.5f * va->accent * va->accamt)
           + va->keytrk * (n0 - 60.0f) * (1.0f / 12.0f) + lfo * va->lcut;
    fc = 30.0f * fm_exp2f(fm_clampf(cutoct, 0.0f, 9.5f));
    fc = fm_minf(fc, 18000.0f);
    g = fm_tanf(3.14159265f * fc / FS);
    if (p[VA_FTYPE] == VAF_LP24) {
        va->k1 = 1.41421356f;
        va->k2 = 2.0f - 1.85f * va->reso;
        svf_coef(va->f1, g, va->k1);
        svf_coef(va->f2, g, va->k2);
    } else {
        va->k1 = 2.0f - 1.85f * va->reso;
        svf_coef(va->f1, g, va->k1);
    }
    /* the amp: the envelope, the accent, VOLUME, the voices' sum normalised */
    {
        static const float NORM[GVA_NV + 1] = {0.0f, 1.0f, 0.72f, 0.6f, 0.52f, 0.47f, 0.43f, 0.4f};
        tgt = va->aenv * va->gain * NORM[va->nv] * (1.0f + 0.8f * va->accent * va->accamt);
        va->amp_step = (tgt - va->amp) * (1.0f / (float)GVA_CR);
    }
}

/* PolyBLEP: the step's correction near a discontinuity at phase 0 */
static inline float blep(float t, float dt)
{
    if (t < dt) {
        t /= dt;
        return t + t - t * t - 1.0f;
    }
    if (t > 1.0f - dt) {
        t = (t - 1.0f) / dt;
        return t * t + t + t + 1.0f;
    }
    return 0.0f;
}

/* one oscillator, n samples added to buf at gain a */
static void osc_add(float *buf, int n, int wave, float *php, float dt, float pw, float a)
{
    float ph = *php;
    int i;
    if (a == 0.0f) {
        ph += dt * (float)n;
        *php = ph - fm_floorf(ph);
        return;
    }
    switch (wave) {
    case VAW_SQR:
        for (i = 0; i < n; i++) {
            float t2 = ph + 1.0f - pw, s;
            t2 -= t2 >= 1.0f ? 1.0f : 0.0f;
            s = (ph < pw ? 1.0f : -1.0f) + blep(ph, dt) - blep(t2, dt);
            buf[i] += s * a;
            ph += dt;
            ph -= ph >= 1.0f ? 1.0f : 0.0f;
        }
        break;
    case VAW_TRI:
        for (i = 0; i < n; i++) {
            float s = ph < 0.5f ? 4.0f * ph - 1.0f : 3.0f - 4.0f * ph;
            buf[i] += s * a;
            ph += dt;
            ph -= ph >= 1.0f ? 1.0f : 0.0f;
        }
        break;
    case VAW_SINE:
        for (i = 0; i < n; i++) {
            buf[i] += fm_sin_turns(ph) * a;
            ph += dt;
            ph -= ph >= 1.0f ? 1.0f : 0.0f;
        }
        break;
    default:
        for (i = 0; i < n; i++) {
            buf[i] += (2.0f * ph - 1.0f - blep(ph, dt)) * a;
            ph += dt;
            ph -= ph >= 1.0f ? 1.0f : 0.0f;
        }
        break;
    }
    *php = ph;
}

void gva_render(gva_t *va, float *out, int n)
{
    float buf[GVA_CR];
    while (n > 0) {
        int m, i, j;
        if (va->cr_left <= 0) {
            control(va);
            va->cr_left = GVA_CR;
        }
        m = n < va->cr_left ? n : va->cr_left;
        if (va->idle) {
            for (i = 0; i < m; i++)
                out[i] = 0.0f;
        } else {
            const int w1 = va->pot[VA_WAVE1], w2 = va->pot[VA_WAVE2];
            const float a1 = 1.0f - va->mix, a2 = va->mix;
            for (i = 0; i < m; i++)
                buf[i] = 0.0f;
            for (j = 0; j < GVA_NV; j++) {
                gva_voice_t *v = &va->v[j];
                if (!v->on)
                    continue;
                osc_add(buf, m, w1, &v->ph1, v->dt1, va->pw, a1);
                osc_add(buf, m, w2, &v->ph2, v->dt2, va->pw, a2);
                if (va->sub > 0.0f)
                    osc_add(buf, m, VAW_SQR, &v->phs, v->dts, 0.5f, va->sub);
            }
            if (va->noise > 0.0f)
                for (i = 0; i < m; i++)
                    buf[i] += (float)(int32_t)rnd(va) * (1.0f / 2147483648.0f) * va->noise;
            {
                const int ft = va->pot[VA_FTYPE];
                float s1a = va->s1a, s1b = va->s1b, s2a = va->s2a, s2b = va->s2b, amp = va->amp;
                const float b1 = va->f1[0], b2 = va->f1[1], b3 = va->f1[2], k1 = va->k1;
                const float c1 = va->f2[0], c2 = va->f2[1], c3 = va->f2[2], st = va->amp_step;
                for (i = 0; i < m; i++) {
                    float x = buf[i], v1, v2, v3, y;
                    x = fm_clampf(x, -3.0f, 3.0f);
                    x = x * (27.0f + x * x) / (27.0f + 9.0f * x * x);   /* soft saturation (tanh-like) */
                    v3 = x - s1b;
                    v1 = b1 * s1a + b2 * v3;
                    v2 = s1b + b2 * s1a + b3 * v3;
                    s1a = 2.0f * v1 - s1a;
                    s1b = 2.0f * v2 - s1b;
                    switch (ft) {
                    case VAF_LP24:
                        v3 = v2 - s2b;
                        v1 = c1 * s2a + c2 * v3;
                        y = s2b + c2 * s2a + c3 * v3;
                        s2a = 2.0f * v1 - s2a;
                        s2b = 2.0f * y - s2b;
                        break;
                    case VAF_BP: y = v1; break;
                    case VAF_HP: y = x - k1 * v1 - v2; break;
                    default: y = v2; break;
                    }
                    amp += st;
                    out[i] = y * amp;
                }
                va->s1a = fm_flush(s1a);
                va->s1b = fm_flush(s1b);
                va->s2a = fm_flush(s2a);
                va->s2b = fm_flush(s2b);
                va->amp = amp;
            }
        }
        out += m;
        n -= m;
        va->cr_left -= m;
    }
}
