/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) EVOLVE: generative playback (the PERFORM layer, KEYS EVOLVE and EVOLVE 2: ui_layer.c). While the music
 * plays, each track whose AMOUNT is on plays an evolved copy of its pattern (seq.c evo_step, seq_st), never its own
 * steps: what is edited, shown, kept into the bank and saved is the original, always. KEEP stores the copy as a new
 * pattern in a free entry of the track's list (bank.c bank_keep_steps), the track stays on its original.
 * Page 1 (KEYS EVOLVE), the knobs:
 *   AMOUNT  (the selected track's) how much changes each time; OFF: the track plays its original at once. A few steps
 *           go back to the original each time too, more the lower AMOUNT is: it wanders and stays recognisable
 *   EVERY   every 1, 2, 4, 8 or 16 passes of a track's loop a new version, written on its last step (so it comes in
 *           with the next pass)
 *   ARRANGE OFF; LIGHT: phrases of 16 bars, at each a few tracks drop out and the others come back, the FILL steps on
 *           a phrase's last bar; FULL: phrases of 8 bars, more out, now and then a breakdown (a phrase without the
 *           kick), then the drop
 *   DRIFT   (the selected track's) its sound wanders: the tone, a second sound parameter (DRUM's DECAY), the reverb
 *           and delay sends glide around their own values
 * Page 2 (KEYS EVOLVE 2): SWEEP (the tone up and down over 16 bars), GATE (length breathing over 8 bars: a kit's
 * DECAY, a line's step GATE, a held note's RELEASE and SUSTAIN), CHORD (thirds, fifths, octaves coming and going over
 * the notes), the selected track's; ROOT (every melodic
 * track through a progression, a step a phrase). The modulations are offsets the audio ISR puts over the parameters
 * for a block and takes off after it (fx.c evo_mod, throw.c), never saved; ROOT moves the notes as they play
 * (seq.c evo_trn); the mutes, FILL and ROOT come in on the bar (launch.c launch_clock).
 * The white keys (both pages): F3 on / off, G3..E4 the track the knobs edit, F4 ALL (held: the knobs set every
 * track), G4 HOME (every track its original, no modulation, until G4 again), A4 KEEP, B4 NEW (another seed), C5
 * PROTECT, D5 FREEZE.
 * PROTECT (on): DRUM tracks keep their kick and snare lanes, melodic ones their notes on the beats (steps 1, 5, 9 ..),
 * and a track with the kick or snare is never taken out; off, those are changed more than the rest.
 * Its own random numbers (a seed: NEW rolls one), not libc.c rng(). The settings are not saved: off at power-on */
#define EVO_RATES 5u
static const uint8_t EVO_RATE[EVO_RATES] = {1, 2, 4, 8, 16};
static const char *const EVO_ARR[3] = {"OFF", "LIGHT", "FULL"};
#define EVO_ROOTS 5u
static const char *const EVO_ROOT[EVO_ROOTS] = {"OFF", "I-IV", "I-V", "I-IV-V", "I-VII-VI"};
static const int8_t EVO_PROG[EVO_ROOTS][4] = {{0, 0, 0, 0}, {0, 5, 0, 5}, {0, 7, 0, 7}, {0, 5, 7, 5}, {0, -2, -4, -2}};
enum { EVO_KEY_ON, EVO_KEY_T1, EVO_KEY_ALL = EVO_KEY_T1 + NTRK, EVO_KEY_HOME, EVO_KEY_KEEP, EVO_KEY_NEW,
       EVO_KEY_PROTECT, EVO_KEY_FREEZE, EVO_KEYS };
static struct {
    uint8_t on;                        /* running */
    uint8_t keys;                      /* PERFORM's KEYS: 1 EVOLVE, 2 EVOLVE 2 (0: TRACK / SCENE) */
    uint8_t screen;                    /* the EVOLVE screen stays (ui_layer.c: until ARP is held on it) */
    uint32_t press_t;                  /* ARP pressed on it (fm1_ms | 1; 0 none) */
    uint8_t amt[NTRK], dft[NTRK], swp[NTRK], gat[NTRK], chd[NTRK];
    uint8_t rate, arrange, root;
    uint8_t protect, freeze, home;
    uint32_t all_k;                    /* F4 ALL held (its key's bit: ui_layer.c layer_keys) */
    uint8_t rr;                        /* the track looked at next (one a pass) */
    uint8_t brk;                       /* ARRANGE FULL: a breakdown (no kick) this phrase */
    uint8_t ppos, plen;                /* the phrase: its bar (1..), its length (0: none) */
    uint8_t since;                     /* ARRANGE FULL: phrases since the last breakdown */
    int8_t trn;                        /* ROOT now */
    uint8_t gen;                       /* changes (the map's signature) */
    uint32_t st;                       /* the generator */
    uint32_t sig[NTRK];                /* the track's steps the copy was made from (ui.c steps_sig) */
    uint16_t pass[NTRK];               /* take_pass when its last version came in */
    uint8_t due[NTRK];                 /* a new version is due (at the track's last step) */
    uint32_t bar;                      /* the bar looked at last (launch.c launch_steps / 16), ~0: none */
    int16_t dv[NTRK * 4u], dc[NTRK * 4u];   /* DRIFT: where each is going, where it is */
    uint32_t mod_t;                    /* fm1_ms of the last modulation pass */
} evo = {.rate = 1, .protect = 1, .st = 0x9E3779B9u, .bar = ~0u};   /* (AMOUNT 0 everywhere: on, nothing changes until a
                                                                      * track's AMOUNT is turned up) */

static int bank_keep_steps(uint32_t k, const step_t *st, uint32_t *ent);   /* (bank.c) */

static uint32_t evo_rnd(uint32_t n)
{
    evo.st ^= evo.st << 13;
    evo.st ^= evo.st >> 17;
    evo.st ^= evo.st << 5;
    return n ? evo.st % n : 0u;
}
static void evo_seed(uint32_t s) { evo.st = s ? s : 0x9E3779B9u; }
static uint32_t evo_sel(void) { return song.sel % NTRK; }

#define EVO_KS ((1u << DV_KICK) | (1u << DV_SNARE))
/* the lanes EVOLVE leaves alone on a DRUM track: the kick and the snare (PROTECT) */
static uint32_t evo_lock(void) { return evo.protect ? EVO_KS : 0u; }
/* a melodic track: ROOT moves its notes (not a kit, not an engine mapping the keys itself: seq.c's QNT SEQ rule) */
static int evo_melodic(track_t *t)
{
    const engine_t *e = ENGINES[eng_idx(t->eng_req)];
    return !drum_track(t) && !(e->keys && e->keys(t, 0) >= 0);
}
/* step i of the original is an anchor (PROTECT, melodic): a note on a beat */
static int evo_anchor(const step_t *own, uint32_t i)
{
    return !(i & 3u) && own[i].time == ST_NOTE && own[i].n && !own[i].hit;
}

/* track k playing its copy from now on: its own steps copied (the ISR held off: seq.c reads either) */
static void evo_reseed(uint32_t k)
{
    uint32_t f = motion_guard();
    memcpy(evo_step[k], trk[k].step, sizeof evo_step[k]);
    evo_play[k] = 1;
    motion_unguard(f);
    evo.sig[k] = steps_sig(&trk[k]);
    evo.pass[k] = take_pass[k];
    evo.due[k] = 0;
}
static void evo_drop(uint32_t k)                        /* .. its own steps again, in no arrangement */
{
    uint32_t f = motion_guard();
    evo_play[k] = 0;
    evo_mute &= (uint8_t)~(1u << k);
    evo_mute_nx &= (uint8_t)~(1u << k);
    motion_unguard(f);
    evo.due[k] = 0;
}
static void evo_mods_off(void)
{
    uint32_t k;
    evo_mod_n = 0;
    for (k = 0; k < NTRK * 4u; k++)
        evo.dv[k] = evo.dc[k] = 0;
}
/* everything off: the originals, no mute, FILL, ROOT or modulation */
static void evo_drop_all(void)
{
    uint32_t k, f;
    for (k = 0; k < NTRK; k++)
        evo_drop(k);
    f = motion_guard();
    evo_at = 0;
    evo_mute = evo_mute_nx = 0;
    evo_fill = evo_fill_nx = 0;
    for (k = 0; k < NTRK; k++)
        evo_trn[k] = evo_trn_nx[k] = 0;
    motion_unguard(f);
    evo_mods_off();
    evo.brk = 0;
    evo.trn = 0;
    evo.ppos = evo.plen = 0;
    evo.bar = ~0u;
}
static int evo_any(void)
{
    uint32_t k, a = evo_mute | evo_fill | evo_mod_n | (uint32_t)evo_at;
    for (k = 0; k < NTRK; k++)
        a |= evo_play[k] | (uint32_t)(uint8_t)evo_trn[k];
    return a != 0u;
}

/* ------------------------------------------------------------- drums --- */
/* lane l of step s on or off (ui.c grid_hit, on a step of the copy) */
static void evo_hit(step_t *s, uint32_t l, uint32_t on)
{
    uint32_t b = 1u << l;
    if (s->time != ST_NOTE) {
        if (!on)
            return;
        step_clear(s);
        s->time = ST_NOTE;
    }
    grid_own(s, l);
    if (on) {
        s->hit |= (uint8_t)b;
    } else {
        s->hit &= (uint8_t)~b;
        s->acc &= (uint8_t)~b;
        if (!s->n && !s->hit)
            step_clear(s);
    }
}
/* a step EVOLVE may change: no TIE, none after it */
static int evo_open(const step_t *st, uint32_t len, uint32_t i)
{
    const step_t *n = &st[(i + 1u) % len];
    return st[i].time != ST_TIE && n->time != ST_TIE && !step_ties(n) && !step_ties(&st[i]);
}
/* a step of the copy with lane l, from a random place on; len: none */
static uint32_t evo_find(const step_t *st, uint32_t len, uint32_t l)
{
    uint32_t i, j = evo_rnd(len);
    for (i = 0; i < len; i++, j = (j + 1u) % len)
        if ((step_lanes(&st[j]) >> l) & 1u)
            return j;
    return len;
}
static uint32_t evo_pick_lane(uint32_t m)              /* one of the lanes of m, at random */
{
    uint32_t l, j = evo_rnd((uint32_t)__builtin_popcount(m)) + 1u;
    for (l = 0; l < NLANE; l++)
        if (((m >> l) & 1u) && !--j)
            return l;
    return DV_HATC;
}
/* one change to a DRUM track's copy: 1 made */
static int evo_drum_op(step_t *st, uint32_t len)
{
    uint32_t used = 0, lock = evo_lock(), i, j, l, n, r = evo_rnd(20);
    for (i = 0; i < len; i++)
        used |= step_lanes(&st[i]);
    if (!evo.protect && (used & EVO_KS) && evo_rnd(2))  /* (PROTECT off: the kick and snare, half the time) */
        used &= EVO_KS;
    used &= ~lock;
    if (!used)
        used = (1u << DV_HATC) & ~lock;
    if (!used)
        return 0;
    l = evo_pick_lane(used);
    i = evo_find(st, len, l);
    if (r < 6u) {                                       /* move a hit a step on or back */
        if (i == len || !evo_open(st, len, i))
            return 0;
        j = (i + (evo_rnd(2) ? 1u : len - 1u)) % len;
        if (((step_lanes(&st[j]) >> l) & 1u) || !evo_open(st, len, j))
            return 0;
        r = (step_accents(&st[i]) >> l) & 1u;
        evo_hit(&st[i], l, 0);
        evo_hit(&st[j], l, 1);
        if (r)
            st[j].acc |= (uint8_t)(1u << l);
        return 1;
    }
    if (r < 11u) {                                      /* one more (off the beat, mostly) */
        j = evo_rnd(len);
        if (evo_rnd(3) && !(j & 1u))
            j = (j + 1u) % len;
        if (((step_lanes(&st[j]) >> l) & 1u) || !evo_open(st, len, j))
            return 0;
        evo_hit(&st[j], l, 1);
        return 1;
    }
    if (r < 15u) {                                      /* one away (never the lane's last) */
        for (n = 0, j = 0; j < len; j++)
            n += (step_lanes(&st[j]) >> l) & 1u;
        if (n < 2u || i == len || !evo_open(st, len, i))
            return 0;
        evo_hit(&st[i], l, 0);
        return 1;
    }
    if (i == len || !evo_open(st, len, i))
        return 0;
    if (r < 17u) {                                      /* its accent on / off */
        if (st[i].flags & SF_ACCENT) {
            st[i].acc |= st[i].hit;
            st[i].flags &= (uint8_t)~SF_ACCENT;
        }
        st[i].acc ^= (uint8_t)(1u << l);
        st[i].acc &= st[i].hit;
        return 1;
    }
    if (step_lanes(&st[i]) & lock)                      /* the whole step: never one with the kick or snare */
        return 0;
    if (r < 19u)                                        /* a ratchet (x2, x3) or none again */
        step_set_ratchet(&st[i], step_ratchet(&st[i]) > 1u ? 1u : 2u + evo_rnd(2));
    else                                                /* a chance or none again */
        step_set_chance(&st[i], step_chance(&st[i]) < 100u ? 100u : evo_rnd(2) ? 75u : 50u);
    return 1;
}

/* ----------------------------------------------------------- melodic --- */
/* a NOTE step of the copy that can change alone (PROTECT: not an anchor; only, a = 1: only one) */
static int evo_note_ok(const step_t *st, const step_t *own, uint32_t len, uint32_t i, int a)
{
    if (st[i].time != ST_NOTE || !st[i].n || st[i].hit || !evo_open(st, len, i))
        return 0;
    if (evo.protect && evo_anchor(own, i))
        return 0;
    return a ? evo_anchor(own, i) : 1;
}
/* the NOTE step a TIE at i holds (its run's start); NSTEP: none */
static uint32_t evo_run_start(const step_t *st, uint32_t i)
{
    while (i && st[i].time == ST_TIE)
        i--;
    return st[i].time == ST_NOTE && st[i].n && !st[i].hit ? i : NSTEP;
}
static void evo_note_copy(step_t *d, const step_t *s0)  /* a run's notes as a plain note (no ratchet, tie, accent) */
{
    *d = *s0;
    d->flags &= (uint8_t)~(SF_RATCH | SF_FLAM | SF_ACCENT);
    d->acc = 0;
    d->cond = 0;
    d->nudge = 0;
}
/* a held note's rhythm (AMOUNT): a TIE struck again (the run's notes), a run's last TIE cut to a rest, a rest after a
 * run held on, or the rest after a run given a short note of its pitch; the pitch stays. 1: made */
static int evo_held_op(step_t *st, uint32_t len)
{
    uint32_t i = evo_rnd(len), k, r = evo_rnd(4), s0;
    for (k = 0; k < len; k++, i = (i + 1u) % len) {
        const step_t *nx = &st[(i + 1u) % len];
        if (r < 2u && st[i].time == ST_TIE && i && (s0 = evo_run_start(st, i)) < NSTEP && !step_ties(nx)) {
            if (r == 0u) {                              /* struck again partway */
                evo_note_copy(&st[i], &st[s0]);
                return 1;
            }
            if (nx->time != ST_TIE) {                   /* its tail cut */
                step_clear(&st[i]);
                return 1;
            }
        } else if (r == 2u && st[i].time == ST_REST && !st[i].n && !st[i].hit && i &&
                   evo_run_start(st, i - 1u) < NSTEP && nx->time != ST_TIE && !step_ties(nx)) {
            st[i].time = ST_TIE;                        /* held on into a rest */
            return 1;
        } else if (r == 3u && st[i].time == ST_REST && !st[i].n && !st[i].hit && i >= 2u && !(i & 1u) &&
                   st[i - 1u].time == ST_REST && (s0 = evo_run_start(st, i - 2u)) < NSTEP &&
                   nx->time != ST_TIE && !step_ties(nx)) {
            evo_note_copy(&st[i], &st[s0]);             /* a short note of its pitch in a rest after it */
            return 1;
        }
    }
    return 0;
}
/* a beat of the line (4 steps without ties) onto another beat, now and then a scale step up or down (PROTECT: the
 * beat's anchor stays). 1: made */
static int evo_phrase_op(const track_t *t, step_t *st, uint32_t len)
{
    uint32_t nb = len / 4u, a, b, j, notes = 0;
    int32_t d = evo_rnd(3) ? 0 : (evo_rnd(2) ? 1 : -1);
    if (nb < 2u)
        return 0;
    a = evo_rnd(nb);
    b = (a + 1u + evo_rnd(nb - 1u)) % nb;
    for (j = 0; j < 4u; j++) {                          /* (both beats free of ties, the steps after them too) */
        if (!evo_open(st, len, a * 4u + j) || !evo_open(st, len, b * 4u + j) || st[a * 4u + j].hit ||
            st[b * 4u + j].hit)
            return 0;
        notes += st[a * 4u + j].time == ST_NOTE && st[a * 4u + j].n;
    }
    if (notes < 2u)                                     /* (a line's beat: not one note and rests) */
        return 0;
    for (j = evo.protect ? 1u : 0u; j < 4u; j++) {
        step_t x = st[a * 4u + j];
        uint32_t k;
        for (k = 0; d && x.time == ST_NOTE && k < x.n && k < 4u; k++)
            x.note[k] = (uint8_t)tl_neigh(t, x.note[k], d);
        st[b * 4u + j] = x;
    }
    return 1;
}
static int evo_mel_op(const track_t *t, step_t *st, uint32_t len)
{
    uint32_t i, j, k, g = 0, r = evo_rnd(24);
    int a = 0;
    step_t *s;
    const step_t *own = t->step;
    if (r >= 20u)                                       /* a held note's rhythm, else a phrase */
        return evo_held_op(st, len) || evo_phrase_op(t, st, len);
    if (r >= 17u && evo_phrase_op(t, st, len))
        return 1;
    if (!evo.protect && evo_rnd(2))                     /* (PROTECT off: the notes on the beats, half the time) */
        for (j = 0; j < len && !a; j++)
            a = evo_note_ok(st, own, len, j, 1);
    for (j = 0; j < len; j++)
        g += (uint32_t)evo_note_ok(st, own, len, j, a);
    if (!g)
        return evo_held_op(st, len);                    /* (held notes only: their rhythm) */
    for (j = evo_rnd(g), i = 0; i < len && (!evo_note_ok(st, own, len, i, a) || j--); i++)
        ;
    if (i >= len)
        return 0;
    s = &st[i];
    r = evo_rnd(20);
    if (r < 10u && (own[i].time != ST_NOTE || !own[i].n))   /* (a note made of a held one: its pitch stays) */
        return evo_held_op(st, len);
    if (r < 10u) {                                      /* a scale step up or down, (r 9) an octave: a line's own notes */
        int32_t d = evo_rnd(2) ? 1 : -1, x;
        uint8_t q[4];
        for (k = 0; k < s->n && k < 4u; k++) {
            x = r == 9u ? s->note[k] + 12 * d : tl_neigh(t, s->note[k], d);
            if (x < 24 || x > 108)
                return 0;
            q[k] = (uint8_t)x;
            for (j = 0; j < k; j++)
                if (q[j] == q[k])
                    return 0;
        }
        for (k = 0; k < s->n && k < 4u; k++)
            s->note[k] = q[k];
        return 1;
    }
    if (r < 12u) {
        s->flags ^= SF_ACCENT;
    } else if (r < 14u) {
        s->flags ^= SF_SLIDE;
    } else if (r < 16u) {
        step_set_chance(s, step_chance(s) < 100u ? 100u : evo_rnd(2) ? 75u : 50u);
    } else if (r < 17u) {
        step_set_ratchet(s, step_ratchet(s) > 1u ? 1u : 2u);
    } else if (r < 18u && g > 2u) {                     /* a note taken out */
        step_clear(s);
    } else {                                            /* a note in a rest near it: its notes */
        j = (i + 1u + evo_rnd(3)) % len;
        if ((evo.protect && !(j & 3u)) || st[j].time != ST_REST || st[j].n || st[j].hit ||
            st[(j + 1u) % len].time == ST_TIE || step_ties(&st[(j + 1u) % len]))
            return 0;                                   /* (PROTECT: none onto a beat) */
        st[j] = *s;
        st[j].flags &= (uint8_t)~(SF_RATCH | SF_FLAM);
        st[j].cond = 0;
        st[j].nudge = 0;
    }
    return 1;
}

/* CHORD: on each NOTE step of a melodic copy a third, a fifth or an octave (the scale's, over the step's first note)
 * comes and goes; the step's own notes always stay. Thicker the higher CHORD is */
static void evo_chords(const track_t *t, step_t *nx, const step_t *own, uint32_t len, uint32_t chd)
{
    static const uint8_t UP[3] = {2, 4, 7};             /* scale steps: a third, a fifth; an octave */
    uint32_t i, k, base;
    for (i = 0; i < len; i++) {
        step_t *s = &nx[i];
        if (s->time != ST_NOTE || !s->n || s->hit)
            continue;
        base = own[i].time == ST_NOTE && !own[i].hit && own[i].n && own[i].n <= s->n ? own[i].n : 1u;
        if (s->n < 4u && evo_rnd(200) < chd) {          /* one more */
            int32_t x = s->note[0];
            uint32_t up = UP[evo_rnd(3)], dup = 0;
            if (up == 7u)
                x += 12;
            else
                for (k = 0; k < up; k++)
                    x = tl_neigh(t, x, 1);
            for (k = 0; k < s->n; k++)
                dup |= s->note[k] == x;
            if (!dup && x <= 108) {
                s->note[s->n] = (uint8_t)x;
                s->acc &= (uint8_t)~(1u << s->n);       /* (a new note: not tied) */
                s->n++;
            }
        } else if (s->n > base && evo_rnd(200) < 100u - chd) {
            s->n--;                                     /* the last one added goes */
            s->acc &= (uint8_t)((1u << s->n) - 1u);
        }
    }
}

/* ------------------------------------------------------- a new version --- */
/* step i of the copy back to the original, its ties with it (the run it is part of) */
static void evo_home_step(step_t *st, const step_t *own, uint32_t len, uint32_t i)
{
    uint32_t a = i, b = i;
    while (a && (own[a].time == ST_TIE || step_ties(&own[a])))
        a--;
    while (b + 1u < len && (own[b + 1u].time == ST_TIE || step_ties(&own[b + 1u])))
        b++;
    for (; a <= b; a++)
        st[a] = own[a];
}
/* PROTECT and a breakdown on a DRUM track's copy: the kick and snare lanes the original's, each hit and accent (a
 * breakdown: no kick; PROTECT off: no snare either) */
static void evo_drum_fix(step_t *nx, const step_t *own, uint32_t len)
{
    uint32_t i, l, brk = evo.brk ? (evo.protect ? 1u << DV_KICK : EVO_KS) : 0u, lk = evo_lock() | brk;
    for (i = 0; lk && i < len; i++)
        for (l = 0; l < NLANE; l++) {
            uint32_t on = (step_lanes(&own[i]) >> l) & 1u;
            if (!((lk >> l) & 1u))
                continue;
            if ((brk >> l) & 1u)
                on = 0;
            if (((step_lanes(&nx[i]) >> l) & 1u) != on)
                evo_hit(&nx[i], l, on);
            if (on && ((step_accents(&nx[i]) >> l) & 1u) != ((step_accents(&own[i]) >> l) & 1u)) {
                if (nx[i].flags & SF_ACCENT) {
                    nx[i].acc |= nx[i].hit;
                    nx[i].flags &= (uint8_t)~SF_ACCENT;
                }
                nx[i].acc ^= (uint8_t)(1u << l);
            }
        }
}
/* track k's next version into its copy (the ISR held off while it is written) */
static void evo_build(uint32_t k)
{
    static step_t nx[NSTEP];
    const track_t *t = &trk[k];
    uint32_t len = tl_len(t), i, k2, m, tries, f, amt = evo.amt[k], home = 4u + (100u - amt) / 3u;
    int drum = drum_track(t);
    memcpy(nx, amt ? evo_step[k] : t->step, sizeof nx);   /* (AMOUNT OFF, CHORD on: the original each time) */
    if (amt) {
        for (i = 0; i < len; i++)
            if (evo_rnd(100) < home)
                evo_home_step(nx, t->step, len, i);
        m = len * amt / (drum ? 150u : 100u);           /* (lines: as many changes as AMOUNT % of the steps) */
        for (m = m ? m : 1u, tries = 8u * m; m && tries; tries--)
            if (drum ? evo_drum_op(nx, len) : evo_mel_op(t, nx, len))
                m--;
    }
    if (!drum && evo.chd[k])
        evo_chords(t, nx, t->step, len, evo.chd[k]);
    if (drum)
        evo_drum_fix(nx, t->step, len);
    else if (evo.protect)                               /* the anchors the original's (CHORD's notes over them stay) */
        for (i = 0; i < len; i += 4u) {
            const step_t *o = &t->step[i];
            int keep = nx[i].time == o->time && nx[i].n >= o->n && !nx[i].hit;
            for (k2 = 0; keep && k2 < o->n; k2++)
                keep = nx[i].note[k2] == o->note[k2];
            if ((evo_anchor(t->step, i) || nx[i].n) && !keep)
                evo_home_step(nx, t->step, len, i);
        }
    f = motion_guard();
    if (evo_play[k])
        memcpy(evo_step[k], nx, sizeof nx);
    motion_unguard(f);
}

/* ------------------------------------------------------- the arrangement --- */
/* a track ARRANGE may take out: evolving, not one with the kick or the snare (PROTECT) */
static int evo_may_mute(uint32_t k)
{
    uint32_t i, len = tl_len(&trk[k]), m = 0;
    if (!evo_play[k])
        return 0;
    if (drum_track(&trk[k]))
        for (i = 0; i < len; i++)
            m |= step_lanes(&trk[k].step[i]);
    return !(m & (evo_lock() | 1u << DV_KICK));         /* (the kick never drops out: no long breaks) */
}
static uint8_t evo_new_mutes(void)
{
    uint32_t k, can = 0, n = 0, max, p = evo.arrange == 2u ? 35u : 20u, m = 0;
    for (k = 0; k < NTRK; k++)
        if (evo_may_mute(k)) {
            can |= 1u << k;
            n++;
        }
    max = n / 2u;
    for (k = 0; k < NTRK && max; k++)
        if (((can >> k) & 1u) && evo_rnd(100) < p) {
            m |= 1u << k;
            max--;
        }
    return (uint8_t)m;
}
static void evo_all_due(void)
{
    uint32_t k;
    for (k = 0; k < NTRK; k++)
        evo.due[k] = evo_play[k];
}
/* the bar that comes next, looked at on the bar's last 1/16: its mutes, FILL and ROOT staged to come in on its first
 * (launch.c launch_clock); a breakdown's copies are made on each track's last step */
static void evo_next_bar(uint32_t bar)
{
    uint32_t plen = evo.arrange == 2u ? 8u : evo.arrange ? 16u : evo.root ? 8u : 0u, pos = plen ? bar % plen : 0u, k;
    uint8_t mute = evo_mute_nx, fill;
    uint32_t f;
    evo.plen = (uint8_t)plen;
    evo.ppos = (uint8_t)(pos + 1u);
    fill = (uint8_t)(evo.arrange && pos == plen - 1u);
    if (evo.arrange && !pos) {                          /* a phrase starts: (a breakdown's drop) its drop-outs */
        if (evo.brk) {
            evo.brk = 0;
            evo_all_due();
        }
        mute = evo_new_mutes();
        evo.since++;
    } else if (evo.arrange == 2u && pos == plen - 2u && evo.since >= 2u && (evo.since >= 4u || evo_rnd(2))) {
        evo.brk = 1;                                    /* (FULL) a breakdown: the phrase's last 2 bars without the */
        evo.since = 0;                                  /* kick, every 2 .. 4 phrases (never longer: no long breaks) */
        mute = 0;
        evo_all_due();
    } else if (!evo.arrange) {
        mute = 0;
        evo.brk = 0;
    }
    evo.trn = plen ? EVO_PROG[evo.root % EVO_ROOTS][(bar / plen) % 4u] : 0;
    f = motion_guard();
    evo_mute_nx = mute;
    evo_fill_nx = fill;
    for (k = 0; k < NTRK; k++)
        evo_trn_nx[k] = (int8_t)(evo_melodic(&trk[k]) ? evo.trn : 0);
    evo_at = bar * 16u;
    if (!evo_at)
        evo_at = 1u;                                    /* (the first bar: at once, 0 is none) */
    motion_unguard(f);
    evo.gen++;
}

/* ------------------------------------------------------- the modulations --- */
/* the parameter DRIFT's c (0 tone, 1 a second one, 2 reverb, 3 delay) moves on track t; P_COUNT: none (a pick, a
 * list: not to be drifted) */
static uint32_t evo_drift_id(const track_t *t, uint32_t c)
{
    uint32_t e = t->eng_req % NENGINES, id;
    const param_desc_t *d;
    if (c == 2u)
        return P_REV;
    if (c == 3u)
        return P_DLY;
    id = drum_track(t) ? (c ? P_E3 : P_E2) : c ? ENGINES[e]->knob[1] : throw_id(t, 0);
    d = param_desc_of(eng_idx(t->eng_req), id);
    return d->fmt == F_ENUM || d->max - d->min < 16 ? P_COUNT : id;
}
static uint32_t evo_tri(uint32_t pos, uint32_t per)    /* a triangle, 0 .. 1000 .. 0 over per */
{
    uint32_t v = (pos % per) * 2000u / per;
    return v < 1000u ? v : 2000u - v;
}
/* one offset into the list (one entry a parameter: a second adds to it) */
static uint32_t evo_mod_put(evo_mod_t *l, uint32_t n, uint32_t k, uint32_t id, int32_t off)
{
    const param_desc_t *d;
    uint32_t i;
    if (id >= P_COUNT || !off)
        return n;
    for (i = 0; i < n; i++)
        if (l[i].trk == k && l[i].id == id) {
            l[i].off = (int16_t)clamp(l[i].off + off, -32000, 32000);
            return n;
        }
    if (n >= EVO_MODS)
        return n;
    d = param_desc_of(eng_idx(trk[k].eng_req), id);
    l[n].trk = (uint8_t)k;
    l[n].id = (uint8_t)id;
    l[n].off = (int16_t)off;
    l[n].min = d->min;
    l[n].max = d->max;
    return n + 1u;
}
/* every 30 ms: DRIFT's glides, SWEEP's and GATE's waves (from the 1/16 steps since PLAY); the list handed over
 * with the ISR held off */
static void evo_mods(void)
{
    static evo_mod_t l[EVO_MODS];
    static const uint8_t LIM[4] = {50, 35, 40, 40};    /* DRIFT 100: % of the parameter's range */
    uint32_t k, c, n = 0, now = fm1_ms, at = launch_steps, f;
    if (now - evo.mod_t < 30u)
        return;
    evo.mod_t = now;
    for (k = 0; k < NTRK; k++) {
        track_t *t = &trk[k];
        uint32_t tone = evo_drift_id(t, 0);
        for (c = 0; c < 4u; c++) {                      /* DRIFT */
            uint32_t i = k * 4u + c, id = evo_drift_id(t, c);
            const param_desc_t *d;
            int32_t span, lim, st;
            if (!evo.dft[k] || id >= P_COUNT) {
                evo.dv[i] = evo.dc[i] = 0;
                continue;
            }
            d = param_desc_of(eng_idx(t->eng_req), id);
            span = d->max - d->min;
            lim = span * evo.dft[k] * LIM[c] / 10000;
            st = span / 64 > 1 ? span / 64 : 1;
            if (!evo_rnd(33))                           /* somewhere else to go, about once a second */
                evo.dv[i] = (int16_t)(lim ? (int32_t)evo_rnd(2u * (uint32_t)lim + 1u) - lim : 0);
            evo.dv[i] = (int16_t)clamp(evo.dv[i], -lim, lim);
            evo.dc[i] = (int16_t)(evo.dc[i] < evo.dv[i] ? (evo.dc[i] + st > evo.dv[i] ? evo.dv[i] : evo.dc[i] + st)
                                                        : (evo.dc[i] - st < evo.dv[i] ? evo.dv[i] : evo.dc[i] - st));
            n = evo_mod_put(l, n, k, id, evo.dc[i]);
        }
        if (evo.swp[k] && tone < P_COUNT) {             /* SWEEP: 16 bars, each track a sixth on */
            const param_desc_t *d = param_desc_of(eng_idx(t->eng_req), tone);
            int32_t lim = (d->max - d->min) * evo.swp[k] * 60 / 10000;
            int32_t w = (int32_t)evo_tri(at + k * 256u / NTRK, 256u) * 2 - 1000;
            n = evo_mod_put(l, n, k, tone, w * lim / 1000);
        }
        if (evo.gat[k]) {                               /* GATE: 8 bars, length by kind: a kit's DECAY; else */
            int32_t w = (int32_t)evo_tri(at + k * 128u / NTRK + 64u, 128u) * 2 - 1000;   /* the step's GATE, */
            uint32_t e = eng_idx(t->eng_req);           /* the RELEASE, the SUSTAIN down where the wave is low */
            if (t->eng_req == ENGI_DRUM) {
                const param_desc_t *d = param_desc_of(e, P_E3);
                n = evo_mod_put(l, n, k, P_E3, w * ((d->max - d->min) * evo.gat[k] * 45 / 10000) / 1000);
            } else if (!drum_track(t)) {
                const param_desc_t *g = param_desc_of(e, P_SGATE), *rl = param_desc_of(e, P_REL),
                                   *su = param_desc_of(e, P_SUS);
                n = evo_mod_put(l, n, k, P_SGATE, w * ((g->max - g->min) * evo.gat[k] / 200) / 1000);
                n = evo_mod_put(l, n, k, P_REL, w * ((rl->max - rl->min) * evo.gat[k] * 35 / 10000) / 1000);
                if (w < 0)
                    n = evo_mod_put(l, n, k, P_SUS, w * ((su->max - su->min) * evo.gat[k] * 45 / 10000) / 1000);
            }
        }
    }
    f = motion_guard();
    memcpy(evo_mod, l, n * sizeof l[0]);
    evo_mod_n = (uint8_t)n;
    motion_unguard(f);
}

/* ------------------------------------------------------------- each pass --- */
static void evo_poll(void)
{
    uint32_t k, len, bar;
    track_t *t;
    if (!evo.on || !song.playing || evo.home) {
        if (evo_any())
            evo_drop_all();
        return;
    }
    bar = (launch_steps + 1u) / 16u;                    /* (on the bar's last 1/16: the next one) */
    if (bar != evo.bar) {
        evo.bar = bar;
        evo_next_bar(bar);
    }
    evo_mods();
    k = evo.rr++ % NTRK;
    t = &trk[k];
    if (!evo.amt[k] && (!evo.chd[k] || drum_track(t))) {   /* AMOUNT OFF (no CHORD): its original */
        if (evo_play[k])
            evo_drop(k);
        return;
    }
    if (!evo_play[k] || steps_sig(t) != evo.sig[k]) {   /* a new pattern, an edit: from it */
        evo_reseed(k);
        return;
    }
    if (evo.freeze)
        return;
    len = tl_len(t);
    if (!evo.due[k] && (uint16_t)(take_pass[k] - evo.pass[k]) >= EVO_RATE[evo.rate % EVO_RATES])
        evo.due[k] = 1;
    if (evo.due[k] && (t->seq_cnt >= len || len == 1u)) {   /* its last step: the next pass is the new one */
        evo.due[k] = 0;
        evo.pass[k] = (uint16_t)(take_pass[k] + 1u);
        evo_build(k);
    }
}

/* ------------------------------------------------------------- controls --- */
static void evo_set_on(int on)
{
    evo.on = (uint8_t)(on != 0);
    evo.home = 0;
    evo.rr = 0;
    if (!evo.on)
        evo_drop_all();
    else
        evo_seed(evo.st ^ fm1_ms);
    evo.gen++;
}
/* KEEP: the selected track's copy as a new pattern in a free entry (bank.c), the original as it is */
static void evo_keep_copy(void)
{
    uint32_t k = evo_sel(), e = 0;
    int rc;
    char b[24];
    if (!evo_play[k]) {
        ui_message("NOTHING EVOLVED");
        return;
    }
    rc = bank_keep_steps(k, evo_step[k], &e);
    if (rc == 1) {
        ui_message("NO EMPTY ENTRY");
        return;
    }
    if (rc) {
        ui_message("PATTERNS FULL");
        return;
    }
    str_cpy(b, "KEPT AS T", sizeof b);
    b[9] = (char)('1' + k);
    b[10] = ' ';
    b[11] = (char)('A' + e);
    b[12] = 0;
    ui_message(b);
}
static int evo_all(void) { return evo.all_k != 0u; }
/* PERFORM, KEYS EVOLVE: white key p (EVO_KEY_*) */
static void evo_key(uint32_t p)
{
    uint32_t k;
    if (p == EVO_KEY_ON) {
        evo_set_on(!evo.on);
        ui_say("EVOLVE ", evo.on ? "ON" : "OFF");
    } else if (p >= EVO_KEY_T1 && p < EVO_KEY_T1 + NTRK) {
        track_select(p - EVO_KEY_T1);
    } else if (p == EVO_KEY_ALL) {
        ui_message("ALL TRACKS: TURN A KNOB");
    } else if (p == EVO_KEY_HOME) {
        evo.home = (uint8_t)!evo.home;
        if (evo.home)
            evo_drop_all();
        else
            for (k = 0; k < NTRK; k++)
                evo.due[k] = 0;
        ui_message(evo.home ? "ORIGINALS: G4 EVOLVES AGAIN" : "EVOLVING AGAIN");
    } else if (p == EVO_KEY_KEEP) {
        evo_keep_copy();
    } else if (p == EVO_KEY_NEW) {
        evo_seed(evo.st ^ fm1_ms ^ 0x5BD1E995u);
        evo_all_due();
        ui_message("NEW SEED");
    } else if (p == EVO_KEY_PROTECT) {
        evo.protect = (uint8_t)!evo.protect;
        ui_say("PROTECT ", evo.protect ? "ON: KICK SNARE BEATS KEPT" : "OFF");
    } else if (p == EVO_KEY_FREEZE) {
        evo.freeze = (uint8_t)!evo.freeze;
        ui_say("FREEZE ", evo.freeze ? "ON" : "OFF");
    }
    evo.gen++;
    ui.force = 1;
}
/* a per-track setting v (the selected track's) turned s in steps of 1 (lo .. hi; acc: accelerated over 100), every
 * track's with ALL held */
static void evo_turn(uint8_t *v, uint32_t knob, int32_t s, int32_t hi, int acc)
{
    uint32_t k, sel = evo_sel();
    int32_t x = (int32_t)v[sel] + (acc ? accel(EN_K1 + knob, s, 100) : (s > 0 ? 1 : -1));
    x = clamp(x, 0, hi);
    for (k = 0; k < NTRK; k++)
        if (k == sel || evo_all())
            v[k] = (uint8_t)x;
}
/* PERFORM, KEYS EVOLVE: KNOB 1..4 AMOUNT EVERY ARRANGE DRIFT; EVOLVE 2: SWEEP GATE ROOT CHORD */
static void evo_knob(uint32_t k, int32_t s)
{
    if (evo.keys == 2u) {
        if (k == 0u)
            evo_turn(evo.swp, k, s, 100, 1);
        else if (k == 1u)
            evo_turn(evo.gat, k, s, 100, 1);
        else if (k == 2u)
            evo.root = (uint8_t)clamp((int32_t)evo.root + (s > 0 ? 1 : -1), 0, EVO_ROOTS - 1);
        else
            evo_turn(evo.chd, k, s, 100, 1);
    } else if (k == 0u) {
        evo_turn(evo.amt, k, s, 100, 1);
    } else if (k == 1u) {
        evo.rate = (uint8_t)clamp((int32_t)evo.rate + (s > 0 ? 1 : -1), 0, EVO_RATES - 1);
    } else if (k == 2u) {
        evo.arrange = (uint8_t)clamp((int32_t)evo.arrange + (s > 0 ? 1 : -1), 0, 2);
    } else {
        evo_turn(evo.dft, k, s, 100, 1);
    }
    evo.gen++;
}
/* the LEDs of KEYS EVOLVE: lit what is on (the selected track's key), the others breathe */
static uint32_t evo_led(uint32_t p, uint32_t *can)
{
    *can = p < EVO_KEYS;
    return p == EVO_KEY_ON ? evo.on
         : p >= EVO_KEY_T1 && p < EVO_KEY_T1 + NTRK ? p - EVO_KEY_T1 == evo_sel()
         : p == EVO_KEY_ALL ? (uint32_t)evo_all()
         : p == EVO_KEY_HOME ? evo.home
         : p == EVO_KEY_PROTECT ? evo.protect
         : p == EVO_KEY_FREEZE ? evo.freeze : 0u;
}
static uint32_t evo_sig(void)
{
    uint32_t k, h = evo.gen * 131u + evo.on * 7u + evo_mute * 977u + evo.brk * 31u + evo_fill * 61u + evo.keys * 3u +
                    evo.ppos * 7919u + (uint32_t)(uint8_t)evo.trn * 104729u + evo.home * 13u;
    for (k = 0; k < NTRK; k++)
        h = h * 33u + evo_play[k] + (trk[k].p[P_MUTE] != 0) * 7u + mute_arm[k] * 11u;
    h += perf_cut * 2803u + (perf_held >> PF_M1) * 977u;          /* (a mute held: the map's M) */
    h += (uint32_t)TSEL->eng_req * 104729u + TSEL->preset * 7919u + TSEL->user * 31u;   /* (its sound's name) */
    return h;
}
/* the header in KEYS EVOLVE (ui_blocks.c); 0: PERFORM's */
static const char *evo_head(void) { return evo.keys == 2u ? "EVOLVE 2" : evo.keys ? "EVOLVE" : 0; }
