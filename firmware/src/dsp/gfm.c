/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore FM synth; see gfm.h. */
#include "gfm.h"
#include "fastmath.h"

#define FS 44100.0f

static const char *const ALG_N[GFM_NALG] = {"1", "2", "3", "4", "5", "6", "7", "8"};
static const char *const MODE_N[FMM_N] = {"MONO", "CHORD"};
#define NRATIO 22
static const char *const RATIO_N[NRATIO] = {"0.25", "0.5", "1", "1.41", "1.5", "2", "2.5", "3", "3.5", "4",
                                            "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"};
static const float RATIO_V[NRATIO] = {0.25f, 0.5f, 1.0f, 1.41421f, 1.5f, 2.0f, 2.5f, 3.0f, 3.5f, 4.0f,
                                      5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f, 11.0f, 12.0f, 13.0f, 14.0f, 15.0f, 16.0f};
#define NLRATES 12
static const char *const LRATE_N[NLRATES] = {"8 BAR", "4 BAR", "2 BAR", "1 BAR", "1/2", "1/4", "1/4T",
                                             "1/8", "1/8T", "1/16", "16T", "1/32"};
static const float LRATE_BEATS[NLRATES] = {32.0f, 16.0f, 8.0f, 4.0f, 2.0f, 1.0f, 2.0f / 3.0f,
                                           0.5f, 1.0f / 3.0f, 0.25f, 1.0f / 6.0f, 0.125f};

/* each algorithm: which operators modulate operator i (bit j: operator j + 1), and the carriers */
static const uint8_t ALG_MOD[GFM_NALG][4] = {
    {0x2, 0x4, 0x8, 0}, {0x2, 0xC, 0, 0}, {0x6, 0, 0x8, 0}, {0x6, 0x8, 0, 0},
    {0x2, 0, 0x8, 0},   {0x8, 0x8, 0x8, 0}, {0, 0, 0x8, 0}, {0, 0, 0, 0},
};
static const uint8_t ALG_CAR[GFM_NALG] = {0x1, 0x1, 0x1, 0x1, 0x5, 0x7, 0x7, 0xF};

#define OP(r, l, d, s) {"RATIO" #r, NRATIO - 1, 2, RATIO_N}, {"LEVEL" #r, 127, l, 0}, {"DECAY" #r, 127, d, 0}, \
                       {"SUSTN" #r, 127, s, 0}
static const x0x_param_t P[FM_N] = {
    {"ALGO", GFM_NALG - 1, 0, ALG_N}, {"FEEDBK", 127, 0, 0}, {"MODE", FMM_N - 1, FMM_MONO, MODE_N}, {"GLIDE", 127, 0, 0},
    OP(1, 110, 70, 90), OP(2, 70, 50, 20), OP(3, 0, 50, 0), OP(4, 0, 50, 0),
    {"ATTACK", 127, 0, 0}, {"RELEAS", 127, 25, 0}, {"ACCENT", 127, 64, 0}, {"VOLUME", 127, 100, 0},
    {"LFO", NLRATES - 1, 7, LRATE_N}, {"L>PTCH", 127, 0, 0}, {"L>MOD", 127, 0, 0}, {"DETUNE", 127, 0, 0},
};

/* the operators' sine: a table of one cycle, read with linear interpolation (much cheaper than the
 * polynomial, and the FM's own harmonics hide its tiny error). A phase in turns, any sign within +-16 */
#define SINTAB 1024
static float sintab[SINTAB + 1];
static void sintab_init(void)
{
    int i;
    if (sintab[SINTAB / 4] != 0.0f)
        return;
    for (i = 0; i <= SINTAB; i++)
        sintab[i] = fm_sin_turns((float)i / (float)SINTAB);
}
static inline float tsin(float ph)
{
    float x = (ph + 16.0f) * (float)SINTAB;
    int i;
    float fr;
    if (x < 0.0f)
        x = 0.0f;
    i = (int)x;
    fr = x - (float)i;
    i &= SINTAB - 1;
    return sintab[i] + (sintab[i + 1] - sintab[i]) * fr;
}

const x0x_param_t *gfm_param(int i) { return i >= 0 && i < FM_N ? &P[i] : 0; }
int gfm_get(const gfm_t *f, int i) { return i >= 0 && i < FM_N ? f->pot[i] : 0; }

static float env_time(int p) { return 0.001f * fm_exp2f((float)p * (13.3f / 127.0f)); }
static float seg_k(float t) { return fm_expf(-(float)GFM_CR * 3.5f / (t * FS)); }

static void calc(gfm_t *f, int i)
{
    const uint8_t *p = f->pot;
    float x = (float)p[i] / 127.0f;
    if (i >= FM_R1 && i <= FM_S4) {
        int op = (i - FM_R1) / 4;
        switch ((i - FM_R1) % 4) {
        case 0: f->ratio[op] = RATIO_V[p[i] % NRATIO]; break;
        case 1: f->lvl[op] = x * x; break;
        case 2: f->dk[op] = seg_k(env_time(p[i])); break;
        default: f->sus[op] = x * x; break;
        }
        return;
    }
    switch (i) {
    case FM_FEEDBK: f->fb = x * x * 0.35f; break;   /* turns of self-modulation */
    case FM_GLIDE: f->glide_t = p[i] ? 0.002f + 0.5f * x * x : 0.0f; break;
    case FM_ATT: f->a_inc = (float)GFM_CR / (env_time(p[i]) * FS); break;
    case FM_REL: f->r_k = seg_k(env_time(p[i])); break;
    case FM_ACCENT: f->accamt = x; break;
    case FM_VOLUME: f->gain = p[i] ? fm_db2lin(((float)p[i] - 100.0f) * 0.35f) * 0.5f : 0.0f; break;
    case FM_LPITCH: f->lpitch = x * x * 12.0f; break;
    case FM_LMOD: f->lmod = x; break;
    case FM_DETUNE: f->det = x * x * 0.3f; break;   /* semitones on operators 2 and 4 */
    default: break;
    }
}

void gfm_set(gfm_t *f, int i, int value)
{
    if (i < 0 || i >= FM_N)
        return;
    f->pot[i] = (uint8_t)(value < 0 ? 0 : value > P[i].max ? P[i].max : value);
    calc(f, i);
}

void gfm_init(gfm_t *f)
{
    uint8_t *b = (uint8_t *)f;
    unsigned i;
    for (i = 0; i < sizeof *f; i++)
        b[i] = 0;
    sintab_init();
    for (i = 0; i < FM_N; i++)
        gfm_set(f, (int)i, P[i].def);
    f->idle = 1;
    f->bpm = 145.0f;
}

void gfm_set_bpm(gfm_t *f, float bpm) { f->bpm = bpm; }
void gfm_set_lite(gfm_t *f, int on) { f->lite = (uint8_t)(on != 0); }

void gfm_note_on(gfm_t *f, const uint8_t *notes, int n, int accent, int slide)
{
    int mode = f->lite ? FMM_MONO : f->pot[FM_MODE], i, nv, sounding = f->st == 1 || f->st == 2;
    float tau;
    if (n < 1)
        return;
    nv = mode == FMM_CHORD ? (n > GFM_NV ? GFM_NV : n) : 1;
    tau = slide && sounding ? (f->glide_t > 0.04f ? f->glide_t : 0.04f) : f->st ? f->glide_t : 0.0f;
    f->glide_k = tau > 0.0f ? 1.0f - fm_expf(-(float)GFM_CR / (tau * FS)) : 0.0f;
    for (i = 0; i < GFM_NV; i++) {
        gfm_voice_t *v = &f->v[i];
        if (i >= nv) {
            v->on = 0;
            continue;
        }
        v->target = (float)notes[i];
        if (!v->on || f->glide_k == 0.0f)
            v->note = v->target;
        if (!v->on) {
            v->ph[0] = v->ph[1] = v->ph[2] = v->ph[3] = 0.0f;
            f->fbz[i][0] = f->fbz[i][1] = 0.0f;
        }
        v->on = 1;
    }
    f->nv = (uint8_t)nv;
    if (!(slide && sounding)) {
        f->st = 1;
        f->accent = accent ? 1.0f : 0.0f;
        for (i = 0; i < 4; i++)                       /* a new note: every operator from where it is */
            if (f->env[i] < 0.0f)
                f->env[i] = 0.0f;
    }
    f->gate = 1;
    f->idle = 0;
    f->cr_left = 0;
}

void gfm_note_add(gfm_t *f, int note)
{
    uint8_t nt = (uint8_t)note;
    if (f->pot[FM_MODE] == FMM_CHORD && !f->lite && f->gate && f->nv < GFM_NV) {
        gfm_voice_t *v = &f->v[f->nv];
        v->target = v->note = (float)note;
        v->ph[0] = v->ph[1] = v->ph[2] = v->ph[3] = 0.0f;
        f->fbz[f->nv][0] = f->fbz[f->nv][1] = 0.0f;
        v->on = 1;
        f->nv++;
        return;
    }
    gfm_note_on(f, &nt, 1, 0, 1);
}

void gfm_note_off(gfm_t *f)
{
    f->gate = 0;
    if (f->st)
        f->st = 3;
}

void gfm_all_off(gfm_t *f)
{
    int i;
    f->gate = 0;
    f->st = 0;
    f->amp = f->amp_step = 0.0f;
    for (i = 0; i < 4; i++)
        f->env[i] = f->mod_now[i] = f->mod_step[i] = 0.0f;
    for (i = 0; i < GFM_NV; i++)
        f->v[i].on = 0;
    f->nv = 0;
    f->idle = 1;
}

static float note_hz(float semis) { return 440.0f * fm_exp2f((semis - 69.0f) * (1.0f / 12.0f)); }

static void control(gfm_t *f)
{
    const uint8_t *p = f->pot;
    const int alg = p[FM_ALGO] % GFM_NALG, car = ALG_CAR[alg];
    float lfo, emax = 0.0f;
    int i, j, ncar = 0;
    {
        float cyc = f->bpm * (1.0f / 60.0f) / LRATE_BEATS[p[FM_LRATE] % NLRATES] * ((float)GFM_CR / FS);
        f->lfo_ph += cyc;
        f->lfo_ph -= fm_floorf(f->lfo_ph);
        lfo = f->lfo_ph < 0.5f ? 4.0f * f->lfo_ph - 1.0f : 3.0f - 4.0f * f->lfo_ph;
        f->lfo_val = lfo;
    }
    for (i = 0; i < 4; i++) {                        /* the operators' envelopes */
        float *e = &f->env[i];
        switch (f->st) {
        case 1:
            *e += f->a_inc;
            if (*e >= 1.0f)
                *e = 1.0f;
            break;
        case 2:
            *e = f->sus[i] + (*e - f->sus[i]) * f->dk[i];
            break;
        case 3:
            *e *= f->r_k;
            break;
        default:
            *e = 0.0f;
            break;
        }
        if (car >> i & 1) {
            ncar++;
            if (*e > emax)
                emax = *e;
        }
    }
    if (f->st == 1 && f->env[0] >= 1.0f && f->env[1] >= 1.0f && f->env[2] >= 1.0f && f->env[3] >= 1.0f)
        f->st = 2;
    if (f->st >= 2 && emax < 1e-4f) {                /* every carrier silent: done (no denormals) */
        int held = 0;
        for (i = 0; i < 4; i++)
            if ((car >> i & 1) && f->sus[i] > 0.0f && f->st == 2)
                held = 1;
        if (!held) {
            gfm_all_off(f);
            return;
        }
    }
    for (j = 0; j < GFM_NV; j++) {
        gfm_voice_t *v = &f->v[j];
        float hz;
        if (!v->on)
            continue;
        if (f->glide_k > 0.0f) {
            v->note += (v->target - v->note) * f->glide_k;
            if (fm_fabsf(v->target - v->note) < 0.001f)
                v->note = v->target;
        } else {
            v->note = v->target;
        }
        hz = note_hz(v->note + lfo * f->lpitch) * (1.0f / FS);
        for (i = 0; i < 4; i++) {
            float r = f->ratio[i] * ((i & 1) ? fm_exp2f(f->det * (1.0f / 12.0f)) : 1.0f);
            v->inc[i] = fm_minf(hz * r, 0.45f);
        }
    }
    {   /* each operator's level: a carrier's loudness, a modulator's depth in turns */
        static const float NORM[GFM_NV + 1] = {0.0f, 1.0f, 0.72f, 0.6f};
        float depth = 2.0f * (1.0f + 0.6f * f->accent * f->accamt) * (1.0f + 0.5f * lfo * f->lmod);
        for (i = 0; i < 4; i++) {
            float t = (car >> i & 1) ? f->lvl[i] * f->env[i] / (float)(ncar ? ncar : 1)
                                     : f->lvl[i] * f->env[i] * depth;
            f->mod_step[i] = (t - f->mod_now[i]) * (1.0f / (float)GFM_CR);
        }
        {
            float tgt = f->gain * NORM[f->nv];
            f->amp_step = (tgt - f->amp) * (1.0f / (float)GFM_CR);
        }
    }
}

void gfm_render(gfm_t *f, float *out, int n)
{
    while (n > 0) {
        int m, i, j;
        if (f->cr_left <= 0) {
            control(f);
            f->cr_left = GFM_CR;
        }
        m = n < f->cr_left ? n : f->cr_left;
        for (i = 0; i < m; i++)
            out[i] = 0.0f;
        if (!f->idle) {
            const int alg = f->pot[FM_ALGO] % GFM_NALG, car = ALG_CAR[alg];
            const uint8_t *mod = ALG_MOD[alg];
            const float fb = f->fb;
            for (j = 0; j < GFM_NV; j++) {
                gfm_voice_t *v = &f->v[j];
                float m0 = f->mod_now[0], m1 = f->mod_now[1], m2 = f->mod_now[2], m3 = f->mod_now[3];
                float z0 = f->fbz[j][0], z1 = f->fbz[j][1];
                if (!v->on)
                    continue;
                for (i = 0; i < m; i++) {
                    float o[4], s;
                    s = tsin(v->ph[3] + fb * (z0 + z1));   /* feedback: the last two raw outputs */
                    z1 = z0;
                    z0 = s;
                    o[3] = s * m3;
                    o[2] = tsin(v->ph[2] + ((mod[2] & 8) ? o[3] : 0.0f)) * m2;
                    s = ((mod[1] & 8) ? o[3] : 0.0f) + ((mod[1] & 4) ? o[2] : 0.0f);
                    o[1] = tsin(v->ph[1] + s) * m1;
                    s = ((mod[0] & 8) ? o[3] : 0.0f) + ((mod[0] & 4) ? o[2] : 0.0f) + ((mod[0] & 2) ? o[1] : 0.0f);
                    o[0] = tsin(v->ph[0] + s) * m0;
                    out[i] += ((car & 1) ? o[0] : 0.0f) + ((car & 2) ? o[1] : 0.0f) + ((car & 4) ? o[2] : 0.0f) +
                              ((car & 8) ? o[3] : 0.0f);
                    v->ph[0] += v->inc[0];
                    v->ph[1] += v->inc[1];
                    v->ph[2] += v->inc[2];
                    v->ph[3] += v->inc[3];
                    v->ph[0] -= v->ph[0] >= 1.0f ? 1.0f : 0.0f;
                    v->ph[1] -= v->ph[1] >= 1.0f ? 1.0f : 0.0f;
                    v->ph[2] -= v->ph[2] >= 1.0f ? 1.0f : 0.0f;
                    v->ph[3] -= v->ph[3] >= 1.0f ? 1.0f : 0.0f;
                    m0 += f->mod_step[0];
                    m1 += f->mod_step[1];
                    m2 += f->mod_step[2];
                    m3 += f->mod_step[3];
                }
                f->fbz[j][0] = z0;
                f->fbz[j][1] = z1;
            }
            {
                float amp = f->amp;
                for (i = 0; i < m; i++) {
                    amp += f->amp_step;
                    out[i] *= amp;
                }
                f->amp = amp;
            }
            for (i = 0; i < 4; i++)
                f->mod_now[i] += f->mod_step[i] * (float)m;
        }
        out += m;
        n -= m;
        f->cr_left -= m;
    }
}
