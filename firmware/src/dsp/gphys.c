/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore PHYS; see gphys.h. */
#include "gphys.h"
#include "fastmath.h"

#define FS 44100.0f

static const char *const MODEL_N[PHM_N] = {"PLUCK", "MALLT", "BELL", "DRUM"};
static const char *const MODE_N[PHV_N] = {"MONO", "CHORD"};
static const x0x_param_t P[PH_N] = {
    {"MODEL", PHM_N - 1, PHM_PLUCK, MODEL_N}, {"DECAY", 127, 70, 0}, {"TONE", 127, 70, 0}, {"POS", 127, 40, 0},
    {"HARD", 127, 70, 0},  {"INHARM", 127, 0, 0}, {"BODY", 127, 0, 0}, {"STRUM", 127, 0, 0},
    {"DROP", 127, 0, 0},   {"DROPT", 127, 40, 0}, {"DAMP", 127, 60, 0}, {"VOLUME", 127, 100, 0},
    {"MODE", PHV_N - 1, PHV_MONO, MODE_N}, {"ACCENT", 127, 64, 0}, {"CUTOFF", 127, 120, 0}, {"RESO", 127, 10, 0},
};
/* each model's level, so that every model sits at VOLUME ~100 for the kits' loudness */
static const float MODEL_GAIN[PHM_N] = {1.78f, 0.18f, 0.116f, 0.143f};
static const float RATIOS[PHM_N][4] = {
    {1.0f, 2.0f, 3.0f, 4.0f},                       /* (PLUCK: unused) */
    {1.0f, 2.756f, 5.404f, 8.933f},                 /* a free bar */
    {1.0f, 2.32f, 4.25f, 6.63f},                    /* a bell's partials */
    {1.0f, 1.593f, 2.136f, 2.296f},                 /* a membrane's */
};

const x0x_param_t *gphys_param(int i) { return i >= 0 && i < PH_N ? &P[i] : 0; }
int gphys_get(const gphys_t *p, int i) { return i >= 0 && i < PH_N ? p->pot[i] : 0; }

static void svf_coef(float *c, float g, float k)
{
    c[0] = 1.0f / (1.0f + g * (g + k));
    c[1] = g * c[0];
    c[2] = g * c[1];
}

static void calc(gphys_t *p, int i)
{
    float x = (float)p->pot[i] / 127.0f;
    switch (i) {
    case PH_DECAY: p->decay_t = 0.05f * fm_exp2f(x * 7.3f); break;        /* 50 ms .. 8 s (to -60 dB) */
    case PH_TONE: p->tone = x; break;
    case PH_POS: p->pos = x; break;
    case PH_HARD: p->hard = x; break;
    case PH_INHARM: p->inharm = x; break;
    case PH_BODY: p->body = x * 1.5f; break;
    case PH_STRUM: p->strum = x * x * 0.08f * FS; break;                  /* up to 80 ms between notes */
    case PH_DROP: p->drop = x * x * 2.0f; break;                          /* up to 3x the pitch at the strike */
    case PH_DROPT: p->drop_k = fm_expf(-(float)GPH_CR / ((0.003f + 0.25f * x * x) * FS)); break;
    case PH_DAMP: p->damp = x; break;
    case PH_VOLUME: p->gain = p->pot[i] ? fm_db2lin(((float)p->pot[i] - 100.0f) * 0.35f) : 0.0f; break;
    case PH_ACCENT: p->accamt = x; break;
    case PH_CUTOFF: case PH_RESO: {
        float fc = fm_minf(60.0f * fm_exp2f((float)p->pot[PH_CUTOFF] * (8.2f / 127.0f)), 18000.0f);
        p->fk = 2.0f - 1.85f * (float)p->pot[PH_RESO] / 127.0f;
        svf_coef(p->f, fm_tanf(3.14159265f * fc / FS), p->fk);
        break;
    }
    default: break;
    }
}

void gphys_set(gphys_t *p, int i, int value)
{
    if (i < 0 || i >= PH_N)
        return;
    p->pot[i] = (uint8_t)(value < 0 ? 0 : value > P[i].max ? P[i].max : value);
    calc(p, i);
}

void gphys_init(gphys_t *p)
{
    uint8_t *b = (uint8_t *)p;
    unsigned i;
    for (i = 0; i < sizeof *p; i++)
        b[i] = 0;
    for (i = 0; i < PH_N; i++)
        gphys_set(p, (int)i, P[i].def);
    p->bk = 1.0f / 1.5f;                              /* the body: a band-pass at 190 Hz */
    svf_coef(p->bf, fm_tanf(3.14159265f * 190.0f / FS), p->bk);
    p->idle = 1;
    p->rng = 0x6C8E9CF5u;
}

void gphys_set_lite(gphys_t *p, int on) { p->lite = (uint8_t)(on != 0); }

static float noise(gphys_t *p)
{
    uint32_t x = p->rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    p->rng = x;
    return (float)(int32_t)x * (1.0f / 2147483648.0f);
}

/* a mode's (or the string's) time to -60 dB, released or not */
static float decay_of(const gphys_t *p, const gph_voice_t *v, int mode)
{
    float t = p->decay_t;
    if (p->pot[PH_MODEL] != PHM_PLUCK)
        t /= 1.0f + (float)mode * (1.0f - p->tone) * 2.0f;   /* darker: the high modes die sooner */
    if (v->released)
        t *= 1.0f - 0.97f * p->damp;
    return t < 0.005f ? 0.005f : t;
}

/* the modes' coefficients for the voice's pitch now (the drum's drop included) */
static void modes(gphys_t *p, gph_voice_t *v)
{
    int model = p->pot[PH_MODEL], i;
    float mult = 1.0f + p->drop * v->drop_env;
    for (i = 0; i < 4; i++) {
        float r = RATIOS[model][i], hz, w, rr;
        if (model == PHM_MALLET)
            r = r + ((float)(i + 1) * (i == 0 ? 1.0f : 2.0f) - r) * p->inharm;   /* toward a tuned bar */
        else
            r *= 1.0f + 0.1f * p->inharm * (float)i;
        hz = v->hz * r * mult;
        if (hz > 0.45f * FS) {
            v->a1[i] = v->a2[i] = 0.0f;
            v->amp[i] = 0.0f;
            continue;
        }
        w = 6.2831853f * hz / FS;
        rr = fm_expf(-6.9078f / (decay_of(p, v, i) * FS));
        v->a1[i] = 2.0f * rr * fm_cosf(w);
        v->a2[i] = -rr * rr;
        {
            float sp = fm_fabsf(fm_sinf(3.14159265f * (float)(i + 1) * (0.08f + 0.84f * p->pos)));
            float tilt = 0.25f + 0.75f * p->tone, t = 1.0f;
            int k;
            for (k = 0; k < i; k++)
                t *= tilt;
            v->amp[i] = (0.3f + 0.7f * sp) * t * fm_sinf(w);
        }
    }
}

static void strike(gphys_t *p, gph_voice_t *v, int note, float vel, int delay)
{
    float t = 0.5f - 0.45f * p->tone;
    v->hz = 440.0f * fm_exp2f(((float)note - 69.0f) * (1.0f / 12.0f));
    v->len = fm_clampf(FS / v->hz - t, 2.0f, (float)(GPH_LINE - 3));
    v->vel = vel;
    v->drop_env = 1.0f;
    v->released = 0;
    v->delay = delay;
    v->exc_len = p->pot[PH_MODEL] == PHM_PLUCK ? (int)(v->len * (0.15f + 0.85f * p->pos)) + 1
                                               : 1 + (int)((1.0f - p->hard) * 40.0f);
    v->exc_left = v->exc_len;
    v->exc_lp = 0.0f;
    v->on = 1;
    modes(p, v);
}

void gphys_note_on(gphys_t *p, const uint8_t *notes, int n, int accent, int slide)
{
    int i, nv = (p->pot[PH_MODE] == PHV_CHORD && !p->lite) ? (n > GPH_NV ? GPH_NV : n) : 1;
    float vel = accent ? 0.75f + 0.25f * (1.0f + p->accamt) : 0.75f;
    if (n < 1)
        return;
    p->accent = accent ? 1.0f : 0.0f;
    for (i = 0; i < nv; i++) {
        gph_voice_t *v = &p->v[i];
        if (slide && v->on && !v->released) {          /* legato: the string's new length, no new pluck */
            float t = 0.5f - 0.45f * p->tone;
            v->hz = 440.0f * fm_exp2f(((float)notes[i] - 69.0f) * (1.0f / 12.0f));
            v->len = fm_clampf(FS / v->hz - t, 2.0f, (float)(GPH_LINE - 3));
            modes(p, v);
            continue;
        }
        strike(p, v, notes[i], vel, (int)(p->strum * (float)i));
    }
    for (; i < GPH_NV && p->pot[PH_MODE] == PHV_MONO; i++)
        p->v[i].released = 1;
    p->nv = (uint8_t)nv;
    p->idle = 0;
    p->quiet = 0;
}

void gphys_note_add(gphys_t *p, int note)
{
    int i;
    for (i = 0; i < GPH_NV; i++)
        if (!p->v[i].on || p->v[i].released) {
            strike(p, &p->v[i], note, 0.75f, 0);
            p->idle = 0;
            p->quiet = 0;
            return;
        }
}

void gphys_note_off(gphys_t *p)
{
    int i;
    for (i = 0; i < GPH_NV; i++)
        if (p->v[i].on && !p->v[i].released) {
            p->v[i].released = 1;
            modes(p, &p->v[i]);
        }
}

void gphys_all_off(gphys_t *p)
{
    int i, k;
    for (i = 0; i < GPH_NV; i++) {
        gph_voice_t *v = &p->v[i];
        for (k = 0; k < GPH_LINE; k++)
            v->line[k] = 0;
        for (k = 0; k < 4; k++)
            v->y1[k] = v->y2[k] = 0.0f;
        v->lp = 0.0f;
        v->on = 0;
    }
    p->s1a = p->s1b = p->b1a = p->b1b = 0.0f;
    p->idle = 1;
}

void gphys_render(gphys_t *p, float *out, int n)
{
    const int model = p->pot[PH_MODEL];
    float peak = 0.0f;
    int i, j, total = n;
    float *o0 = out;
    for (i = 0; i < n; i++)
        out[i] = 0.0f;
    if (p->idle)
        return;
    for (j = 0; j < GPH_NV; j++) {
        gph_voice_t *v = &p->v[j];
        float excg = v->vel * (0.6f + 0.4f * p->hard + 0.3f * p->accent * p->accamt);
        float klp = 0.08f + 0.92f * p->hard * p->hard;
        if (!v->on)
            continue;
        if (model == PHM_PLUCK) {
            const float t = 0.5f - 0.45f * p->tone;
            const float loss = fm_expf(-6.9078f / (decay_of(p, v, 0) * v->hz));   /* a pass round the loop */
            const int li = (int)v->len;
            const float fr = v->len - (float)li;
            int w = (int)v->wpos;
            float lp = v->lp;
            for (i = 0; i < n; i++) {
                float x, y, e = 0.0f;
                if (v->delay > 0) {
                    v->delay--;
                    continue;
                }
                if (v->exc_left > 0) {
                    v->exc_lp += klp * (noise(p) - v->exc_lp);
                    e = v->exc_lp * excg;
                    v->exc_left--;
                }
                x = (float)v->line[(w - li) & (GPH_LINE - 1)] * (1.0f - fr) +
                    (float)v->line[(w - li - 1) & (GPH_LINE - 1)] * fr;
                x *= 1.0f / 16384.0f;
                y = ((1.0f - t) * x + t * lp) * loss;
                lp = x;
                y += e;
                y = fm_clampf(y, -1.99f, 1.99f);
                v->line[w & (GPH_LINE - 1)] = (int16_t)(y * 16384.0f);
                w++;
                out[i] += y;
            }
            v->wpos = (float)(w & (GPH_LINE - 1));
            v->lp = lp;
        } else {
            for (i = 0; i < n; i++) {
                float e = 0.0f, s = 0.0f;
                int k;
                if (v->delay > 0) {
                    v->delay--;
                    continue;
                }
                if (v->exc_left > 0) {
                    v->exc_lp += klp * (noise(p) - v->exc_lp);
                    e = (v->exc_left == v->exc_len ? p->hard * 2.0f : 0.0f) + v->exc_lp;
                    e *= excg;
                    v->exc_left--;
                }
                for (k = 0; k < 4; k++) {
                    float y = v->a1[k] * v->y1[k] + v->a2[k] * v->y2[k] + e * v->amp[k];
                    v->y2[k] = v->y1[k];
                    v->y1[k] = y;
                    s += y;
                }
                out[i] += s * 0.5f;
            }
            for (i = 0; i < 4; i++) {
                v->y1[i] = fm_flush(v->y1[i]);
                v->y2[i] = fm_flush(v->y2[i]);
            }
            if (model == PHM_DRUM && p->drop > 0.0f) {   /* the drop, a control step a block */
                int steps = (n + GPH_CR - 1) / GPH_CR;
                while (steps--)
                    v->drop_env *= p->drop_k;
                modes(p, v);
            }
        }
    }
    {   /* the body, the low-pass, the volume */
        float s1a = p->s1a, s1b = p->s1b, b1a = p->b1a, b1b = p->b1b;
        const float c1 = p->f[0], c2 = p->f[1], c3 = p->f[2], d1 = p->bf[0], d2 = p->bf[1], d3 = p->bf[2];
        const float body = p->body, g = p->gain * MODEL_GAIN[model];
        for (i = 0; i < n; i++) {
            float x = out[i], v1, v2, v3;
            if (body > 0.0f) {
                v3 = x - b1b;
                v1 = d1 * b1a + d2 * v3;
                v2 = b1b + d2 * b1a + d3 * v3;
                b1a = 2.0f * v1 - b1a;
                b1b = 2.0f * v2 - b1b;
                x += v1 * body;
            }
            v3 = x - s1b;
            v1 = c1 * s1a + c2 * v3;
            v2 = s1b + c2 * s1a + c3 * v3;
            s1a = 2.0f * v1 - s1a;
            s1b = 2.0f * v2 - s1b;
            out[i] = 2.0f * fm_tanhf(v2 * g * 0.5f);         /* never past 2, whatever the pots */
            if (fm_fabsf(out[i]) > peak)
                peak = fm_fabsf(out[i]);
        }
        p->s1a = fm_flush(s1a);
        p->s1b = fm_flush(s1b);
        p->b1a = fm_flush(b1a);
        p->b1b = fm_flush(b1b);
    }
    (void)o0;
    if (peak < 3e-5f) {                               /* silent for 0.2 s: idle */
        p->quiet += total;
        if (p->quiet > 8820)
            gphys_all_off(p);
    } else {
        p->quiet = 0;
    }
}
