/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) The drum voice of GruselCore's kits: GruselCore 0.1's drum sound (dsp/gdrum.c on the branch
 * x0x-base, float) in fixed point, Skiff's way (no FPU; dsp.c's sine, tanh, noise and pitch tables).
 *
 * Every sound of a kit is the same voice with a MODEL (kick, snare, clap, hat, tom, rim, metal, zap) and 16 pots.
 * A kick is a sine with a two-stage pitch drop (PITCH over P.DEC, then BODY over a slower glide), a click, an amp
 * envelope with a hold (PUNCH), a tail for the rumble and a drive with five curves. The other models use the same
 * parts: a tone, filtered noise (TONE), six square oscillators for hats and metal, retriggered noise for claps.
 *
 * Envelopes, pitch and the oscillators' increments move every GCD_SUB (8) samples, the level ramps between; the
 * tone, noise, filter and drive run per sample. Signals in Q15 (32768 = 1.0, the float engine's 1.0), envelopes in
 * Q30, multipliers in Q16 (build/gen/felucca_tables.h: GCD_*, tools/gen_tables.py gc_drum_tables).
 * Kits: gc_kits.c. The DRUM engine (eng_drum.c) plays a kit's sound i on its lane i. */

enum { GDM_KICK, GDM_SNARE, GDM_CLAP, GDM_HAT, GDM_TOM, GDM_RIM, GDM_METAL, GDM_ZAP, GDM_N };
enum { GDC_SOFT, GDC_HARD, GDC_FOLD, GDC_TUBE, GDC_CRUSH, GDC_N };
enum {
    GP_MODEL,   /* GDM_*                                                 */
    GP_LEVEL,   /* 100 = unity                                           */
    GP_TUNE,    /* the end pitch: note 12 + 0.75 * pot                   */
    GP_PITCH,   /* the first pitch drop: 0..72 semitones                 */
    GP_PDEC,    /* its time: 0.3..60 ms                                  */
    GP_BODY,    /* a second, slower drop: 0..24 semitones over 8 x P.DEC */
    GP_DECAY,   /* the amp's decay: 5 ms..3 s                            */
    GP_TAIL,    /* a second, 2x longer decay under the first (rumble)    */
    GP_CLICK,   /* the transient's level                                 */
    GP_TONE,    /* the noise / metal filter: 100 Hz..16 kHz              */
    GP_NOISE,   /* tone <-> noise                                        */
    GP_DRIVE,   /* the drive: 1..60                                      */
    GP_CURVE,   /* GDC_*                                                 */
    GP_PUNCH,   /* full level held before the decay: 0..50 ms            */
    GP_ATTACK,  /* 0..30 ms                                              */
    GP_PAN,     /* 64 = centre (the kit's design; the lane's PAN is the track's) */
    GP_N
};
#define GCD_ONE (1 << 30)                 /* an envelope at full */
#define GCD_NSND 8

typedef struct {                          /* a sound's coefficients (gcd_setup) */
    uint8_t model, curve, crush_n;
    int32_t note16, pitch16, body16;      /* the end pitch and the two drops, 1/16 semitone */
    uint16_t k_pdec, k_body, k_dec, k_tail;   /* Q16, a GCD_SUB step */
    int32_t tail_lvl;                     /* Q30 */
    int32_t click, noise;                 /* Q15 */
    int32_t drive;                        /* Q8 */
    int32_t gain;                         /* Q12: LEVEL and the model's makeup */
    uint32_t hold_n;                      /* GCD_SUB steps */
    int32_t att_inc;                      /* Q30 a step; 0: no attack */
    int32_t a1, a2, a3, k;                /* the filter: Simper's SVF (Q13), its damping (Q12) */
} gcd_coef_t;

typedef struct {                          /* a sounding sound */
    uint8_t live, stage, clap_n, crush_c; /* stage: 0 attack, 1 hold, 2 decay, 3 choked */
    uint8_t again;                        /* struck while it rang (eng_drum.c drum_declick) */
    uint32_t ph, ph2, mph[6];
    uint32_t inc, inc2, minc[6];
    int32_t e1, e2, amp, tail, clk;       /* Q30 */
    int32_t env15, clk15;                 /* the last step's level and click (Q15): the ramps start there */
    uint32_t hold_left, clap_next;
    int32_t vel;                          /* Q15 */
    int32_t ic1, ic2, clk_lp, dcx, dcy, crush_h;
    int32_t rng;
} gcd_voice_t;

/* a pot moved by a knob: pot + (knob - 64) * num / den, kept in 0..127 */
static uint32_t gcd_mac(int32_t pot, int32_t knob, int32_t num, int32_t den)
{
    return (uint32_t)clamp(pot + (knob - 64) * num / den, 0, 127);
}

/* the coefficients of a sound (pots p) with the track's knobs: off16 the pitch (1/16 semitone), tone, decay and grit
 * each 64 = the kit as designed (decay: lane's DECAY added) */
static void gcd_setup(gcd_coef_t *c, const uint8_t *p, int32_t off16, int32_t tone, int32_t decay, int32_t grit)
{
    static const uint8_t MAKEUP_X10[GDM_N] = {10, 10, 10, 40, 10, 20, 25, 10};   /* hats, metal, rims: their engine level */
    uint32_t m = p[GP_MODEL] < GDM_N ? p[GP_MODEL] : 0u, tn = gcd_mac(p[GP_TONE], tone, 1, 2);
    uint32_t dc = gcd_mac(p[GP_DECAY], decay, 1, 2), dr = gcd_mac(p[GP_DRIVE], grit, 1, 1);
    int32_t g, den, lv = p[GP_LEVEL];
    c->model = (uint8_t)m;
    c->curve = (uint8_t)(p[GP_CURVE] < GDC_N ? p[GP_CURVE] : 0);
    c->crush_n = (uint8_t)(1u + (dr >> 4));
    c->note16 = 192 + 12 * p[GP_TUNE] + off16;
    c->pitch16 = 1152 * p[GP_PITCH] / 127;
    c->body16 = 384 * p[GP_BODY] / 127;
    c->k_pdec = GCD_PDEC_K[p[GP_PDEC] & 127u];
    c->k_body = GCD_BODY_K[p[GP_PDEC] & 127u];
    c->k_dec = GCD_DEC_K[dc];
    c->k_tail = GCD_TAIL_K[dc];
    c->tail_lvl = p[GP_TAIL] * 2959187;              /* 0.35 x pot / 127, Q30 */
    c->click = p[GP_CLICK] * 387;                     /* 1.5 x pot / 127, Q15 */
    c->noise = p[GP_NOISE] * 258;
    c->drive = GCD_DRIVE_Q8[dr];
    c->gain = lv * lv * MAKEUP_X10[m] * 25 / 1017;    /* 0.6 x (LEVEL / 100)^2 x makeup, Q12 */
    c->hold_n = (uint32_t)p[GP_PUNCH] * 2205u / 127u / GCD_SUB;
    c->att_inc = p[GP_ATTACK] ? (int32_t)((uint32_t)GCD_ONE / (1323u * p[GP_ATTACK] / 127u / GCD_SUB + 1u)) : 0;
    c->k = m == GDM_SNARE || m == GDM_CLAP ? 4915 : m == GDM_ZAP ? 2048 : 5734;   /* 1.2, 0.5, 1.4 */
    g = GCD_TONE_G[tn];
    den = 4096 + ((g * (g + c->k)) >> 12);
    c->a1 = (int32_t)((4096u << 13) / (uint32_t)den);
    c->a2 = (c->a1 * g) >> 12;
    c->a3 = (c->a2 * g) >> 12;
}

/* struck at velocity vel (Q15, 0..32767); a hit while it rings starts its envelopes again, its filter as it is */
static void gcd_trigger(gcd_voice_t *v, const gcd_coef_t *c, int32_t vel)
{
    v->again = v->live;
    v->live = 1;
    v->vel = 18022 + (int32_t)(((uint32_t)vel * 14746u) >> 15);   /* 0.55 + 0.45 x vel */
    v->ph = 0;
    v->e1 = v->e2 = GCD_ONE;
    v->clk = GCD_ONE;
    v->tail = c->tail_lvl;
    v->amp = c->att_inc ? 0 : GCD_ONE;
    v->stage = c->att_inc ? 0 : 1;
    v->hold_left = c->hold_n;
    v->clap_n = c->model == GDM_CLAP ? 3 : 0;
    v->clap_next = 50;                                /* 9 ms in GCD_SUB steps */
    v->crush_c = 0;
    v->env15 = c->att_inc ? 0 : 32767;
    v->clk15 = 32767;
    if (!v->rng)
        v->rng = 0x12345678;
}

static void gcd_choke(gcd_voice_t *v)
{
    if (v->live)
        v->stage = 3;
}

/* the six square oscillators' ratios (Q16): a hat's or a metal's partials */
static const uint32_t GCD_METAL_R[6] = {65536u, 87950u, 80688u, 108344u, 127946u, 141053u};

/* one GCD_SUB step of the envelopes and the pitch; the level and click it ends at (Q15) */
static void gcd_step(gcd_voice_t *v, const gcd_coef_t *c, int32_t *env15, int32_t *clk15)
{
    int32_t p16, e;
    uint32_t inc, j;
    v->e1 = mulq16(v->e1, c->k_pdec);
    v->e2 = mulq16(v->e2, c->k_body);
    switch (v->stage) {
    case 0:
        v->amp += c->att_inc;
        if (v->amp >= GCD_ONE) {
            v->amp = GCD_ONE;
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
        v->amp = mulq16(v->amp, v->clap_n ? GCD_CLAP_K : c->k_dec);
        break;
    default:
        v->amp = mulq16(v->amp, GCD_CHOKE_K);
        v->tail = mulq16(v->tail, GCD_CHOKE_K);
        break;
    }
    if (v->clap_n && !--v->clap_next) {               /* a clap's next burst */
        v->amp = GCD_ONE;
        v->clap_n--;
        v->clap_next = 50;
    }
    v->tail = mulq16(v->tail, c->k_tail);
    v->clk = mulq16(v->clk, GCD_CLICK_K);
    e = (v->amp >> 15) + (v->tail >> 15);
    *env15 = e > 32767 ? 32767 : e;
    *clk15 = v->clk >> 15;
    p16 = c->note16 + ((c->pitch16 * (v->e1 >> 15)) >> 15) + ((c->body16 * (v->e2 >> 15)) >> 15);
    inc = pitch_inc((uint32_t)clamp(p16, 0, 2047));
    if (inc > 1932735283u)                            /* 0.45 of the rate */
        inc = 1932735283u;
    v->inc = inc;
    if (c->model == GDM_RIM)
        v->inc2 = (uint32_t)mulq16((int32_t)inc, 177602u);   /* x 2.71 */
    else if (c->model == GDM_HAT || c->model == GDM_METAL)
        for (j = 0; j < 6u; j++)
            v->minc[j] = (uint32_t)mulq16((int32_t)inc, GCD_METAL_R[j]);
}

/* the drive's curve on x (Q15, may be far past full scale) */
static int32_t gcd_shape(gcd_voice_t *v, const gcd_coef_t *c, int32_t x)
{
    int32_t t;
    switch (c->curve) {
    case GDC_HARD:
        return clamp(x, -32767, 32767);
    case GDC_FOLD:
        return sine_i((uint32_t)x << 15);            /* sin(x pi / 2): folds back past +-1 */
    case GDC_TUBE:
        t = softclip(x);                              /* asymmetric: even harmonics */
        return ((t + (((t * t) >> 15) >> 2)) * 26214) >> 15;
    case GDC_CRUSH:
        if (!v->crush_c) {
            int32_t q = clamp(x, -32767, 32767) * 31;
            q = (q + (q >= 0 ? 16384 : -16384)) / 32767;
            v->crush_h = q * 32767 / 31;
            v->crush_c = c->crush_n;
        }
        v->crush_c--;
        return v->crush_h;
    default:
        return softclip(x);
    }
}

/* n samples (a multiple of GCD_SUB) of the sound into y (written, Q15) */
static void gcd_run(gcd_voice_t *v, const gcd_coef_t *c, int32_t *y, uint32_t n)
{
    const uint32_t m = c->model;
    const int32_t a1 = c->a1, a2 = c->a2, a3 = c->a3, nm = c->noise, tm = 32767 - c->noise;
    uint32_t i, j, s;
    if (!v->live) {
        for (i = 0; i < n; i++)
            y[i] = 0;
        return;
    }
    for (s = 0; s < n; s += GCD_SUB) {
        int32_t e0 = v->env15, k0 = v->clk15, e1, k1;
        gcd_step(v, c, &e1, &k1);
        for (i = 0; i < GCD_SUB; i++) {
            int32_t env = e0 + (((e1 - e0) * (int32_t)(i + 1)) >> 3), ck = k0 + (((k1 - k0) * (int32_t)(i + 1)) >> 3);
            int32_t tone = 0, nz, x, v1, v2, v3;
            v->ph += v->inc;
            switch (m) {
            case GDM_RIM:
                v->ph2 += v->inc2;
                tone = (sine_i(v->ph) * 19661 + sine_i(v->ph2) * 19661) >> 15;   /* 0.6 + 0.6 */
                break;
            case GDM_HAT:
            case GDM_METAL: {
                int32_t cnt = 0;
                for (j = 0; j < 6u; j++) {
                    v->mph[j] += v->minc[j];
                    cnt += v->mph[j] < 0x80000000u ? 1 : -1;
                }
                tone = cnt * 5461;                    /* / 6 */
                break;
            }
            case GDM_CLAP:
                break;
            default:
                tone = sine_i(v->ph);
                break;
            }
            nz = (int32_t)noise32(&v->rng) >> 16;
            x = (m == GDM_HAT || m == GDM_METAL) ? ((tone * tm) >> 15) + ((nz * nm) >> 15) : nz;
            v3 = x - v->ic2;                          /* the filter (Simper): v1 band, v2 low */
            v1 = (a1 * v->ic1 + a2 * v3) >> 13;
            v2 = v->ic2 + ((a2 * v->ic1 + a3 * v3) >> 13);
            v->ic1 = clamp(2 * v1 - v->ic1, -150000, 150000);
            v->ic2 = clamp(2 * v2 - v->ic2, -150000, 150000);
            switch (m) {
            case GDM_HAT:
            case GDM_METAL:
                x = x - ((c->k * v1) >> 12) - v2;     /* high-pass */
                break;
            case GDM_SNARE:
            case GDM_CLAP:
                x = ((tone * tm) >> 15) + (((clamp(v1, -40000, 40000) * 52429) >> 16) * nm >> 14);   /* band-pass (x 1.6) */
                break;
            default:
                x = ((tone * tm) >> 15) + ((clamp(v2, -65535, 65535) >> 1) * nm >> 14);   /* low-passed noise under the tone */
                break;
            }
            v->clk_lp += ((nz - v->clk_lp) * 11469) >> 15;   /* the click: high-passed noise, a few ms */
            x = clamp(x, -65535, 65535);
            x = ((x * env) >> 15) + (((((c->click * ck) >> 15) >> 1) * clamp(nz - v->clk_lp, -65535, 65535)) >> 14);
            x = clamp(x, -65535, 65535);
            x = gcd_shape(v, c, ((((x >> 1) * v->vel) >> 14) * c->drive) >> 8);
            x = (x * c->gain) >> 12;
            v3 = x - v->dcx + v->dcy - ((v->dcy * 93) >> 15);   /* DC blocker, ~20 Hz (x 0.99715: the asymmetric curves) */
            v->dcx = x;
            v->dcy = v3;
            y[s + i] = v3;
        }
        v->env15 = e1;
        v->clk15 = k1;
    }
    if (v->stage >= 2 && !v->clap_n && (v->amp >> 15) + (v->tail >> 15) + (v->clk >> 15) < 4) {   /* -78 dB: over */
        v->live = 0;
        v->ic1 = v->ic2 = v->clk_lp = v->dcx = v->dcy = 0;
    }
}
