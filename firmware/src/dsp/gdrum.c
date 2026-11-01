/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore drum engine; see gdrum.h. */
#include "gdrum.h"
#include "fastmath.h"

#define GD_FS 44100.0f
#define GD_TWO_PI 6.2831853f

static const char *const MODEL_N[GDM_N] = {"KICK", "SNARE", "CLAP", "HAT", "TOM", "RIM", "METAL", "ZAP"};
static const char *const CURVE_N[GDC_N] = {"SOFT", "HARD", "FOLD", "TUBE", "CRUSH"};
static const char *const SLOT_N[GD_NSND] = {"KICK", "SNARE", "CLAP", "C.HAT", "O.HAT", "TOM", "RIM", "PERC"};

static const x0x_param_t PARAMS[GP_N] = {
    {"MODEL", GDM_N - 1, GDM_KICK, MODEL_N},
    {"LEVEL", 127, 100, 0},
    {"TUNE", 127, 24, 0},
    {"PITCH", 127, 80, 0},
    {"P.DEC", 127, 40, 0},
    {"BODY", 127, 30, 0},
    {"DECAY", 127, 70, 0},
    {"TAIL", 127, 0, 0},
    {"CLICK", 127, 40, 0},
    {"TONE", 127, 80, 0},
    {"NOISE", 127, 0, 0},
    {"DRIVE", 127, 20, 0},
    {"CURVE", GDC_N - 1, GDC_SOFT, CURVE_N},
    {"PUNCH", 127, 20, 0},
    {"ATTACK", 127, 0, 0},
    {"PAN", 127, 64, 0},
};

const x0x_param_t *gdrum_param(int i) { return (i >= 0 && i < GP_N) ? &PARAMS[i] : 0; }
const char *gdrum_slot_name(int snd) { return (snd >= 0 && snd < GD_NSND) ? SLOT_N[snd] : ""; }

/* 0..127 -> lo * 2^(oct * pot / 127): an exponential range */
static float expo(int pot, float lo, float oct) { return lo * fm_exp2f(oct * (float)pot * (1.0f / 127.0f)); }
/* per-sample multiplier of an exponential decay to -60 dB in t seconds */
static float decay_k(float t) { return fm_expf(-6.9077553f / (t * GD_FS)); }

static void voice_calc(gd_voice_t *v)
{
    const uint8_t *p = v->pot;
    float pdec, fc, g, k;
    int m = p[GP_MODEL];
    v->note_end = 12.0f + 0.75f * (float)p[GP_TUNE];
    v->pitch_amt = 72.0f * (float)p[GP_PITCH] * (1.0f / 127.0f);
    v->body_amt = 24.0f * (float)p[GP_BODY] * (1.0f / 127.0f);
    pdec = expo(p[GP_PDEC], 0.0003f, 7.64f);                    /* 0.3 .. 60 ms */
    v->k_pdec = fm_expf(-1.0f / (pdec * GD_FS));                /* to 1/e in pdec */
    v->k_body = fm_expf(-1.0f / (fm_clampf(8.0f * pdec, 0.02f, 0.3f) * GD_FS));
    v->k_dec = decay_k(expo(p[GP_DECAY], 0.005f, 9.23f));       /* 5 ms .. 3 s */
    v->k_tail = decay_k(2.0f * expo(p[GP_DECAY], 0.005f, 9.23f));
    v->tail_lvl = 0.35f * (float)p[GP_TAIL] * (1.0f / 127.0f);
    v->click = 1.5f * (float)p[GP_CLICK] * (1.0f / 127.0f);
    v->k_click = decay_k(0.004f);
    v->noise_mix = (float)p[GP_NOISE] * (1.0f / 127.0f);
    v->drive = expo(p[GP_DRIVE], 1.0f, 5.9f);                   /* 1 .. 60 */
    v->drive_comp = 1.0f;
    v->hold_n = (uint32_t)(0.05f * GD_FS * (float)p[GP_PUNCH] * (1.0f / 127.0f));
    v->att_inc = p[GP_ATTACK] ? 1.0f / (0.03f * GD_FS * (float)p[GP_ATTACK] * (1.0f / 127.0f)) : 2.0f;
    {   /* LEVEL, and each model's makeup: hats, metal and rims come out of the engine 6-12 dB under a
         * kick, so the kits' LEVEL pots (normalised to one loudness, tests/host/gdrum_test.c) stay in range */
        static const float MAKEUP[GDM_N] = {1.0f, 1.0f, 1.0f, 4.0f, 1.0f, 2.0f, 2.5f, 1.0f};
        float lv = (float)p[GP_LEVEL] * (1.0f / 100.0f);
        v->gain = 0.6f * lv * lv * MAKEUP[m < GDM_N ? m : 0];   /* 0.6: headroom for the DC blocker */
    }
    /* the noise / metal filter: TPT state-variable, resonance by model */
    fc = fm_minf(expo(p[GP_TONE], 100.0f, 7.32f), 18000.0f);    /* 100 Hz .. 16 kHz */
    g = fm_tanf(3.14159265f * fc / GD_FS);
    k = (m == GDM_SNARE || m == GDM_CLAP) ? 1.2f : (m == GDM_ZAP ? 0.5f : 1.4f);
    v->svf_f = g;
    v->svf_q = k;
    x0x_pan_gains(p[GP_PAN], &v->pan_l, &v->pan_r);
}

void gdrum_load_kit(gdrum_t *d, const gd_kit_t *k)
{
    int s, i;
    for (s = 0; s < GD_NSND; s++) {
        for (i = 0; i < GP_N; i++)
            d->v[s].pot[i] = k->pot[s][i];
        voice_calc(&d->v[s]);
    }
}

void gdrum_init(gdrum_t *d)
{
    uint8_t *b = (uint8_t *)d;
    unsigned i;
    for (i = 0; i < sizeof *d; i++)
        b[i] = 0;
    d->rng = 0x12345678u;
    gdrum_load_kit(d, &gd_kits[0]);
}

void gdrum_set(gdrum_t *d, int snd, int i, int value)
{
    const x0x_param_t *p = gdrum_param(i);
    if (snd < 0 || snd >= GD_NSND || !p)
        return;
    if (value < 0)
        value = 0;
    if (value > p->max)
        value = p->max;
    d->v[snd].pot[i] = (uint8_t)value;
    voice_calc(&d->v[snd]);
}

int gdrum_get(const gdrum_t *d, int snd, int i)
{
    return (snd >= 0 && snd < GD_NSND && i >= 0 && i < GP_N) ? d->v[snd].pot[i] : 0;
}

void gdrum_trigger(gdrum_t *d, int snd, float vel)
{
    gd_voice_t *v;
    if (snd < 0 || snd >= GD_NSND)
        return;
    v = &d->v[snd];
    v->active = 1;
    v->vel = 0.55f + 0.45f * fm_clampf(vel, 0.0f, 1.0f);
    v->ph = 0.0f;
    v->e1 = 1.0f;
    v->e2 = 1.0f;
    v->clk = 1.0f;
    v->tail = v->tail_lvl;
    v->amp = v->att_inc >= 1.0f ? 1.0f : 0.0f;
    v->stage = v->att_inc >= 1.0f ? 1 : 0;
    v->hold_left = v->hold_n;
    v->clap_n = v->pot[GP_MODEL] == GDM_CLAP ? 3 : 0;
    v->clap_next = (uint32_t)(0.009f * GD_FS);
    v->crush_c = 0;
    if (snd == GD_CHAT && d->v[GD_OHAT].active)
        d->v[GD_OHAT].stage = 3;                    /* the closed hat chokes the open one */
}

int gdrum_active(const gdrum_t *d)
{
    int s;
    for (s = 0; s < GD_NSND; s++)
        if (d->v[s].active)
            return 1;
    return 0;
}

static const float METAL_R[6] = {1.0f, 1.3420f, 1.2312f, 1.6532f, 1.9523f, 2.1523f};

static float shape(gd_voice_t *v, float x)
{
    float y;
    x *= v->drive;
    switch (v->pot[GP_CURVE]) {
    case GDC_HARD:
        y = fm_clampf(x, -1.0f, 1.0f);
        break;
    case GDC_FOLD:
        y = fm_sinf(x * 1.5707963f);                    /* folds back past +-1 */
        break;
    case GDC_TUBE:
        y = fm_tanhf(x);                                /* asymmetric: even harmonics */
        y = 0.8f * (y + 0.25f * y * y);
        break;
    case GDC_CRUSH:
        if (v->crush_c == 0) {
            float q = fm_clampf(x, -1.0f, 1.0f) * 31.0f;
            v->crush_h = (float)(int)(q + (q >= 0.0f ? 0.5f : -0.5f)) * (1.0f / 31.0f);
            v->crush_c = (uint8_t)(1 + (v->pot[GP_DRIVE] >> 4));
        }
        v->crush_c--;
        y = v->crush_h;
        break;
    default:
        y = fm_tanhf(x);
        break;
    }
    return y * v->drive_comp;
}

static void render_voice(gdrum_t *d, gd_voice_t *v, float *l, float *r, int n)
{
    const int m = v->pot[GP_MODEL];
    const float a1 = 1.0f / (1.0f + v->svf_f * (v->svf_f + v->svf_q)), a2 = v->svf_f * a1, a3 = v->svf_f * a2;
    const float k_clapfast = 0.9915f;               /* a clap burst: ~3 ms */
    float out_peak = 0.0f;
    int i, j;
    for (i = 0; i < n; i++) {
        float note, inc, tone = 0.0f, nz, filt, v1, v2, x, env;
        /* envelopes */
        v->e1 *= v->k_pdec;
        v->e2 *= v->k_body;
        switch (v->stage) {
        case 0:
            v->amp += v->att_inc;
            if (v->amp >= 1.0f) {
                v->amp = 1.0f;
                v->stage = 1;
            }
            break;
        case 1:
            if (v->hold_left)
                v->hold_left--;
            else
                v->stage = 2;
            break;
        case 2:
            v->amp *= v->clap_n ? k_clapfast : v->k_dec;
            break;
        default:
            v->amp *= 0.995f;                       /* choked */
            v->tail *= 0.995f;
            break;
        }
        if (v->clap_n && --v->clap_next == 0) {
            v->amp = 1.0f;
            v->clap_n--;
            v->clap_next = (uint32_t)(0.009f * GD_FS);
        }
        v->tail *= v->k_tail;
        v->clk *= v->k_click;
        env = v->amp + v->tail;
        /* pitch and tone */
        note = v->note_end + v->pitch_amt * v->e1 + v->body_amt * v->e2;
        inc = 440.0f / GD_FS * fm_exp2f((note - 69.0f) * (1.0f / 12.0f));
        if (inc > 0.45f)
            inc = 0.45f;
        v->ph += inc;
        if (v->ph >= 1.0f)
            v->ph -= 1.0f;
        d->rng ^= d->rng << 13;
        d->rng ^= d->rng >> 17;
        d->rng ^= d->rng << 5;
        nz = (float)(int32_t)d->rng * (1.0f / 2147483648.0f);
        switch (m) {
        case GDM_KICK:
        case GDM_TOM:
        case GDM_ZAP:
        case GDM_SNARE:
            tone = fm_sin_turns(v->ph);
            break;
        case GDM_RIM: {
            float p2 = v->ph * 2.71f;
            p2 -= (float)(int)p2;
            tone = 0.6f * fm_sin_turns(v->ph) + 0.6f * fm_sin_turns(p2);
            break;
        }
        case GDM_HAT:
        case GDM_METAL:
            for (j = 0; j < 6; j++) {
                v->mph[j] += inc * METAL_R[j];
                if (v->mph[j] >= 1.0f)
                    v->mph[j] -= 1.0f;
                tone += v->mph[j] < 0.5f ? 1.0f : -1.0f;
            }
            tone *= (1.0f / 6.0f);
            break;
        default:
            break;
        }
        /* the filter: hats and metal filter the tone + noise, the rest only the noise */
        x = (m == GDM_HAT || m == GDM_METAL) ? tone * (1.0f - v->noise_mix) + nz * v->noise_mix : nz;
        {
            float v3 = x - v->bp;                   /* (bp holds ic2, lp holds ic1) */
            v1 = a1 * v->lp + a2 * v3;
            v2 = v->bp + a2 * v->lp + a3 * v3;
            v->lp = 2.0f * v1 - v->lp;
            v->bp = 2.0f * v2 - v->bp;
        }
        switch (m) {
        case GDM_HAT:
        case GDM_METAL:
            filt = x - v->svf_q * v1 - v2;          /* high-pass */
            x = filt;
            break;
        case GDM_SNARE:
        case GDM_CLAP:
            filt = v1 * 1.6f;                       /* band-pass */
            x = tone * (1.0f - v->noise_mix) + filt * v->noise_mix;
            break;
        default:
            filt = v2;                              /* low-pass noise under the tone */
            x = tone * (1.0f - v->noise_mix) + filt * v->noise_mix;
            break;
        }
        /* the click: high-passed noise, a few ms */
        v->clk_lp += 0.35f * (nz - v->clk_lp);
        x = x * env + v->click * v->clk * (nz - v->clk_lp);
        x = shape(v, x * v->vel) * v->gain;
        {                                           /* DC blocker, ~20 Hz (the asymmetric curves) */
            float y = x - v->dc_x + 0.99715f * v->dc_y;
            v->dc_x = x;
            v->dc_y = y;
            x = y;
        }
        l[i] += x * v->pan_l;
        r[i] += x * v->pan_r;
        out_peak = fm_maxf(out_peak, env + v->clk);
    }
    if (v->stage >= 2 && !v->clap_n && out_peak < 1.0e-4f) {
        v->active = 0;
        v->lp = v->bp = v->clk_lp = v->dc_x = v->dc_y = 0.0f;
    }
}

void gdrum_render_st(gdrum_t *d, float *l, float *r, int n)
{
    int s;
    for (s = 0; s < GD_NSND; s++)
        if (d->v[s].active)
            render_voice(d, &d->v[s], l, r, n);
}
