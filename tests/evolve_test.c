/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) EVOLVE (firmware/src/evolve.c; PERFORM, KEYS EVOLVE and EVOLVE 2) on the real sources with
 * tests/ui_test.c's stubs: a melodic T1 (C minor, 16 steps) and a DRUM T4 (kick, snare, hats; 16 steps), played with
 * the main loop's evo_poll between the blocks and the block's modulations on and off around them (as fx.c mix_block):
 *   OFF       nothing plays a copy, nothing modulated
 *   SAFE      everything on (AMOUNT 100, ARRANGE FULL, DRIFT SWEEP GATE, ROOT): the tracks' own steps (what the
 *             bank and the autosave keep) and their own parameters never change; the copies do
 *   PROTECT   on: the kick and snare lanes the original's (a breakdown: no kick), T1's notes on the beats as they are,
 *             the drum track never taken out; off: they change
 *   VALID     every step of the copies: at most 4 notes, a chance 0..101, RATCH x1..x4; T1's notes in C minor
 *   AMOUNT    per track: OFF plays the original, the other track evolves; ALL sets every track
 *   HOME      every track its original, nothing modulated or moved, until HOME again
 *   KEEP      the copy as a new pattern in a free entry, the track's own steps as they were; a full list says so
 *   ROOT      I-IV: the second phrase sounds 5 semitones up; STOP leaves nothing sounding
 *   HELD      a drone (one note held over the bar) at AMOUNT 100: its rhythm changes (struck again, cut, held on),
 *             never its pitch
 *   CHORD     100 at AMOUNT 0: thirds, fifths, octaves over T1's notes, every step's own notes kept, all in C minor
 *   GATE      100: a kit's DECAY, a synth's GATE, RELEASE and SUSTAIN in the modulations, their own values kept
 *   SEED      the same seed: the same copies
 *   EDIT      a step edited: the copy starts again from the edited steps
 *   SCREEN    ARP held in KEYS EVOLVE and let go: the screen stays; another page: it goes, EVOLVE runs on; ARP tapped:
 *             back; ARP held on it: closed, a tap then is ARP's page
 *   STOP      nothing left: no copy played, no mute, FILL, ROOT or modulation
 * Built and run by tests/run_tests.sh. */
#define UI_TEST_NO_MAIN 1
#include "ui_test.c"

static track_t *M, *D;                                  /* T1 melodic, T4 drums */
static step_t m0[NSTEP], d0[NSTEP];                     /* their steps as set up */
static int16_t mp0[P_COUNT], dp0[P_COUNT];              /* .. their parameters */

static void evo_reset(void)
{
    uint32_t k;
    evo_set_on(0);
    evo.keys = evo.screen = 0;
    evo.press_t = 0;
    evo.rate = 0;
    evo.arrange = 0;
    evo.root = 0;
    evo.protect = 1;
    evo.freeze = evo.home = 0;
    evo.all_k = 0;
    for (k = 0; k < NTRK; k++) {
        evo.amt[k] = 100;
        evo.dft[k] = evo.swp[k] = evo.gat[k] = evo.chd[k] = 0;
    }
}
static void setup(void)
{
    uint32_t i;
    static const uint8_t N[16] = {48, 0, 51, 0, 55, 48, 0, 58, 60, 0, 55, 0, 51, 53, 0, 55};   /* C minor */
    ui_power_on();
    song.g[G_SWING] = 0;
    M = &trk[0];
    D = &trk[3];
    set_engine_of(M, 0);
    set_engine_of(D, ENGI_DRUM);
    track_defaults_steps(M);
    track_defaults_steps(D);
    for (i = 0; i < NSTEP; i++) {
        step_clear(&M->step[i]);
        step_clear(&D->step[i]);
    }
    M->p[P_SLEN] = D->p[P_SLEN] = 16;
    M->p[P_SCALE] = 2;                                  /* (a minor scale: the scale table's third) */
    M->p[P_ROOT] = 0;
    M->p[P_VOICE] = V_MONO;
    M->p[P_QUANT] = 0;
    for (i = 0; i < 16u; i++) {
        if (N[i])
            M->step[i] = (step_t){{N[i]}, 1, ST_NOTE, 0, 100};
        if (i % 4u == 0u)
            grid_hit(D, i, DV_KICK, 1);
        if (i % 8u == 4u)
            grid_hit(D, i, DV_SNARE, 1);
        if (i % 2u == 0u)
            grid_hit(D, i, DV_HATC, 1);
    }
    memcpy(m0, M->step, sizeof m0);
    memcpy(d0, D->step, sizeof d0);
    memcpy(mp0, M->p, sizeof mp0);
    memcpy(dp0, D->p, sizeof dp0);
    evo_reset();
    events_block(CTL);
}
static int sc_in(const track_t *t, uint32_t n) { return (scale_mask(t) >> ((n + 120u - (uint32_t)t->p[P_ROOT]) % 12u)) & 1u; }
static uint32_t lane_of(const step_t *st, uint32_t l)   /* lane l of the 16 steps as a mask */
{
    uint32_t i, m = 0;
    for (i = 0; i < 16u; i++)
        m |= ((step_lanes(&st[i]) >> l) & 1u) << i;
    return m;
}
static int sounding(const track_t *t, uint32_t note)
{
    uint32_t i;
    for (i = 0; i < NVOICE; i++)
        if (t->v[i].active && t->v[i].gate && t->v[i].note == note)
            return 1;
    return 0;
}
static uint32_t nsound(const track_t *t)
{
    uint32_t i, n = 0;
    for (i = 0; i < NVOICE; i++)
        n += t->v[i].active && t->v[i].gate;
    return n;
}
static void block(void)                                 /* one block as mix_block runs it, then the main loop */
{
    if (thr_out | evo_mod_n)
        throw_on(CTL);
    events_block(CTL);
    if (thr_on | evo_mod_on)
        throw_off();
    fm1_ms += 1u;                                       /* (about a block's time) */
    evo_poll();
}
static uint32_t step_len(void) { return div_samples(2); }   /* a 1/16 in samples */

static uint32_t brk_run, brk_max;                       /* 1/16s in a breakdown in a row, the most */
static struct { int prot, brk_seen, mute_bad, valid, scale, anchor, changed_m, changed_d, mods, own_p, ks_changed, anc_changed; } r;
static void run_steps(uint32_t steps)                   /* that many 1/16s, the copies looked at all along */
{
    uint32_t n, end = steps * step_len(), at, k, i;
    for (at = 0; at < end; at += CTL) {
        block();
        r.own_p |= memcmp(M->p, mp0, sizeof mp0) != 0 || memcmp(D->p, dp0, sizeof dp0) != 0;
        brk_run = evo.brk ? brk_run + 1u : 0u;
        brk_max = brk_run > brk_max ? brk_run : brk_max;
        if (evo_play[3]) {
            const step_t *e = evo_step[3];
            if (evo.brk && lane_of(e, DV_KICK) == 0u)
                r.brk_seen = 1;
            if (lane_of(e, DV_SNARE) != lane_of(d0, DV_SNARE) ||
                (lane_of(e, DV_KICK) != lane_of(d0, DV_KICK) && lane_of(e, DV_KICK) != 0u))
                r.prot = 1;
            r.ks_changed |= lane_of(e, DV_SNARE) != lane_of(d0, DV_SNARE) ||
                            (lane_of(e, DV_KICK) != lane_of(d0, DV_KICK) && lane_of(e, DV_KICK) != 0u);
            r.changed_d |= memcmp(e, d0, sizeof d0) != 0;
        }
        if (evo_mute & (1u << 3))
            r.mute_bad = 1;
        r.mods |= evo_mod_n != 0u;
        for (k = 0; k < NTRK; k++) {
            if (!evo_play[k])
                continue;
            for (i = 0; i < NSTEP; i++) {
                const step_t *s = &evo_step[k][i];
                if (s->n > 4u || s->probability > 101u || step_ratchet(s) > 4u)
                    r.valid = 1;
                if (k == 0u && s->time == ST_NOTE)
                    for (n = 0; n < s->n; n++)
                        r.scale |= !sc_in(M, s->note[n]);
            }
        }
        if (evo_play[0]) {
            r.changed_m |= memcmp(evo_step[0], m0, sizeof m0) != 0;
            for (i = 0; i < 16u; i += 4u) {
                r.anchor |= memcmp(&evo_step[0][i], &m0[i], sizeof m0[i]) != 0;
                r.anc_changed |= memcmp(&evo_step[0][i], &m0[i], sizeof m0[i]) != 0;
            }
        }
    }
}
static void run_bars(uint32_t bars) { run_steps(bars * 16u); }
static int nothing_left(void) { return !evo_any() && !evo_mute && !evo_fill && !evo_mod_n && !evo_trn[0]; }

int main(void)
{
    int bad = 0, ok;
    step_t keep[NSTEP];
    uint32_t k, e, f, p0;
    uint8_t rec[BK_REC], want[BK_REC];

    for (ok = 1, k = 0; k < NTRK; k++)                  /* (before anything sets them) */
        ok &= evo.amt[k] == 0u;
    bad += check("AMOUNT: 0 on every track at power-on (EVOLVE on changes nothing until one is turned up)", ok);

    setup();                                            /* OFF */
    seq_start();
    run_bars(4);
    bad += check("OFF: no track plays a copy, nothing modulated", !evo_play[0] && !evo_play[3] && nothing_left());
    seq_stop();

    setup();                                            /* SAFE, PROTECT on */
    evo_set_on(1);
    evo_seed(12345u);
    evo.arrange = 2;
    evo.root = 3;
    for (k = 0; k < NTRK; k++) {
        evo.dft[k] = evo.swp[k] = evo.gat[k] = 100;
    }
    memset(&r, 0, sizeof r);
    seq_start();
    run_bars(64);
    bad += check("SAFE: 64 bars of everything: the tracks' own steps unchanged",
                 !memcmp(M->step, m0, sizeof m0) && !memcmp(D->step, d0, sizeof d0));
    bad += check("  .. their own parameters after every block (DRIFT SWEEP GATE only over them)", !r.own_p);
    bad += check("  the copies evolved (both tracks), the modulations ran", r.changed_m && r.changed_d && r.mods);
    bad += check("PROTECT on: the snare lane as it is, the kick as it is or (a breakdown) none", !r.prot);
    bad += check("  T1's notes on the beats (steps 1 5 9 13) as they are", !r.anchor);
    bad += check("  ARRANGE FULL made a breakdown (a copy with no kick) in 64 bars", r.brk_seen);
    bad += check("  .. never longer than 2 bars (no long breaks)", brk_max > 0u && brk_max <= 2u * 16u * step_len() / CTL + 4u);
    bad += check("  the drum track (kick, snare) never taken out", !r.mute_bad);
    bad += check("VALID: every copied step at most 4 notes, chance 0..101, RATCH x1..x4", !r.valid);
    bad += check("  T1's notes all in C minor", !r.scale);
    seq_stop();
    evo_poll();
    bad += check("STOP: no copy, no mute, FILL, ROOT or modulation left", nothing_left());

    setup();                                            /* PROTECT off */
    evo_set_on(1);
    evo_seed(99u);
    evo.protect = 0;
    memset(&r, 0, sizeof r);
    seq_start();
    run_bars(32);
    bad += check("PROTECT off: the kick or snare lanes and T1's beat notes do change", r.ks_changed && r.anc_changed);
    seq_stop();
    evo_poll();

    setup();                                            /* AMOUNT per track, ALL */
    evo_set_on(1);
    evo.amt[0] = 0;
    memset(&r, 0, sizeof r);
    seq_start();
    run_bars(8);
    bad += check("AMOUNT: T1 OFF plays its original, T4 (AMOUNT 100) evolves", !evo_play[0] && r.changed_d);
    sel_set(0);
    evo.all_k = 1;
    evo_knob(0, 5);
    ok = 1;
    for (k = 0; k < NTRK; k++)
        ok &= evo.amt[k] == evo.amt[0] && evo.amt[0] > 0u;
    evo.all_k = 0;
    evo_knob(0, -3);
    bad += check("  ALL held: KNOB 1 sets every track's AMOUNT; let go: the selected one's only", ok && evo.amt[0] < evo.amt[1]);
    seq_stop();
    evo_poll();

    setup();                                            /* HOME */
    evo_set_on(1);
    evo.dft[0] = evo.dft[3] = 100;
    evo.root = 1;
    seq_start();
    run_bars(8);
    evo_key(EVO_KEY_HOME);
    run_bars(8);
    bad += check("HOME: every track its original, nothing modulated or moved, for as long as it is on",
                 evo.home && !evo_play[0] && !evo_play[3] && nothing_left());
    evo_key(EVO_KEY_HOME);
    memset(&r, 0, sizeof r);
    run_bars(8);
    bad += check("  HOME again: evolving again", !evo.home && evo_play[3] && r.changed_d);

    sel_set(0);                                         /* KEEP */
    run_bars(4);
    memcpy(keep, evo_step[0], sizeof keep);
    p0 = lists.ent[0][lists.cur[0] % NENT][0];
    evo_keep_copy();
    for (f = NENT, e = 0; e < NENT; e++)
        if (e != lists.cur[0] % NENT && lists.ent[0][e][0])
            f = e;
    ok = f < NENT && !memcmp(M->step, m0, sizeof m0) && lists.ent[0][lists.cur[0] % NENT][0] == p0;
    if (ok) {
        int16_t tv[5];
        for (k = 0; k < 5u; k++)
            tv[k] = motion_base_value(M, BK_TIME[k]);
        ok = !pat_read(lists.ent[0][f][0] - 1u, rec) && bk_pack_raw(want, 0, keep, tv, &motion, motion_enabled(M)) &&
             !memcmp(rec, want, BK_REC);
    }
    bad += check("KEEP: the copy as a new pattern in a free entry, the track on its original, its steps as they were", ok);
    seq_stop();
    evo_poll();
    for (e = 0, ok = 1; e < NENT + 2u && ok; e++)
        ok = bank_keep_steps(0, keep, &f) == 0;
    bad += check("  the list full: NO EMPTY ENTRY (bank_keep_steps 1)", !ok && bank_keep_steps(0, keep, &f) == 1);

    setup();                                            /* ROOT */
    evo_set_on(1);
    evo.amt[0] = evo.amt[3] = 0;
    evo.root = 1;                                       /* (I-IV, phrases of 8 bars: ARRANGE OFF) */
    seq_start();
    run_steps(2u * 16u);
    for (k = 0; k < step_len() / 4u; k += CTL)          /* (a quarter into the step) */
        block();
    ok = sounding(M, 48) && !sounding(M, 53);           /* bar 3, its first step: C */
    run_steps(6u * 16u);                                /* bar 9 (the second phrase) */
    ok &= sounding(M, 53) && !sounding(M, 48);          /* .. F */
    bad += check("ROOT I-IV: the first phrase as written, the second 5 semitones up", ok);
    seq_stop();
    for (k = 0; k < 64u; k++)
        block();
    bad += check("  STOP: nothing sounding, nothing moved", nsound(M) == 0u && nothing_left());

    setup();                                            /* HELD: T1 a drone, C3 held over the bar */
    for (k = 0; k < 16u; k++)
        M->step[k] = k ? (step_t){{0}, 0, ST_TIE, 0, 0} : (step_t){{48}, 1, ST_NOTE, 0, 100};
    M->step[15] = (step_t){{0}, 0, ST_REST, 0, 0};
    memcpy(m0, M->step, sizeof m0);
    evo_set_on(1);
    evo_seed(31u);
    evo.amt[3] = 0;
    seq_start();
    {
        int changed = 0, pitch_ok = 1;
        for (e = 0; e < 16u; e++) {
            run_bars(1);
            changed |= memcmp(evo_step[0], m0, sizeof m0) != 0;
            for (k = 0; k < 16u; k++)
                for (f = 0; f < evo_step[0][k].n; f++)
                    pitch_ok &= evo_step[0][k].note[f] == 48;
        }
        bad += check("HELD: a drone at AMOUNT 100 changes its rhythm within 16 bars, its pitch never", changed && pitch_ok);
    }
    seq_stop();
    evo_poll();

    setup();                                            /* CHORD */
    evo_set_on(1);
    evo_seed(5u);
    evo.amt[0] = evo.amt[3] = 0;
    evo.chd[0] = 100;
    memset(&r, 0, sizeof r);
    seq_start();
    run_bars(8);
    {
        int more = 0, kept = 1;
        for (k = 0; k < 16u; k++) {
            const step_t *c = &evo_step[0][k];
            if (m0[k].time != ST_NOTE || !m0[k].n)
                continue;
            more |= c->n > m0[k].n;
            kept &= c->time == ST_NOTE && c->n >= m0[k].n && c->note[0] == m0[k].note[0];
        }
        bad += check("CHORD 100, AMOUNT 0: notes gain thirds / fifths / octaves, each step's own note kept, C minor",
                     evo_play[0] && more && kept && !r.scale && !r.valid && !memcmp(M->step, m0, sizeof m0));
    }
    seq_stop();
    evo_poll();

    setup();                                            /* GATE */
    evo_set_on(1);
    evo.gat[0] = evo.gat[3] = 100;
    memset(&r, 0, sizeof r);
    seq_start();
    run_bars(2);
    {
        int dec = 0, sg = 0, rel = 0;
        for (k = 0; k < evo_mod_n; k++) {
            dec |= evo_mod[k].trk == 3u && evo_mod[k].id == P_E3;
            sg |= evo_mod[k].trk == 0u && evo_mod[k].id == P_SGATE;
            rel |= evo_mod[k].trk == 0u && evo_mod[k].id == P_REL;
        }
        bad += check("GATE 100: the kit's DECAY, the synth's GATE and RELEASE breathe; their own values as they were",
                     dec && sg && rel && !r.own_p);
    }
    seq_stop();
    evo_poll();

    setup();                                            /* SEED */
    evo_set_on(1);
    evo_seed(777u);
    seq_start();
    run_bars(16);
    memcpy(keep, evo_step[0], sizeof keep);
    seq_stop();
    evo_poll();
    setup();
    evo_set_on(1);
    evo_seed(777u);
    seq_start();
    run_bars(16);
    bad += check("SEED: the same seed, the same copy", !memcmp(keep, evo_step[0], sizeof keep));
    M->step[2].note[0] = 63;                            /* EDIT */
    for (k = 0; k < 2u * NTRK; k++)
        evo_poll();
    bad += check("EDIT: the copy starts again from the edited steps", evo_step[0][2].note[0] == 63 &&
                 evo.sig[0] == steps_sig(M));
    seq_stop();
    evo_poll();

    ui_power_on();                                      /* SCREEN */
    evo_reset();
    evo.keys = 1;
    hold(B_ARP);
    frames(200);
    ok = ui.layer == LAYER_PERF && ui.lock == LAYER_PERF && evo.screen;
    bad += check("SCREEN: ARP held in KEYS EVOLVE, let go: the EVOLVE screen stays", ok);
    press(B_FX);
    frames(200);
    ok = ui.layer != LAYER_PERF && evo.screen;
    bad += check("  another page (FX): it goes, EVOLVE stays (the screen comes back)", ok);
    press(B_ARP);
    frames(200);
    ok = ui.layer == LAYER_PERF && ui.lock == LAYER_PERF;
    bad += check("  ARP tapped: the EVOLVE screen again", ok);
    press(B_ARP);
    frames(200);
    bad += check("  ARP tapped on it: it stays", ui.layer == LAYER_PERF && ui.lock == LAYER_PERF);
    hold(B_ARP);
    frames(200);
    ok = ui.layer != LAYER_PERF && !ui.lock && !evo.screen;
    bad += check("  ARP held on it: closed", ok);
    press(B_ARP);
    frames(200);
    bad += check("  .. a tap then: ARP's page, no EVOLVE screen", ui.layer != LAYER_PERF && !evo.screen);

    printf("evolve: %s\n", bad ? "FAILED" : "all ok");
    return bad ? 1 : 0;
}
