/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore sequencer; see gseq.h. Timing core after X0X's sequencer.c (Charles Vestal). */
#include "gseq.h"

#define NEVER 0xFFFFFFFFu

static const uint8_t TICKS_PER_STEP[NRATES] = {6, 4, 3, 8, 12};   /* 24 ppqn: 1/16, 1/16T, 1/32, 1/8T, 1/8 */
static const uint8_t GM_DRUM[NDSND] = {36, 38, 39, 42, 46, 45, 37, 56};   /* kit slots as General MIDI */

void gseq_init(seq_t *s, pattern_t *patterns)
{
    uint32_t i;
    uint8_t *p = (uint8_t *)s;
    for (i = 0; i < sizeof *s; i++)
        p[i] = 0;
    s->pat = patterns;
    for (i = 0; i < NTRK; i++)
        s->tcue[i] = 0xFF;
    s->bpm = 140.0f;
    s->ext_bpm = 140.0f;
    s->accent_q7 = 88;
    s->send_clock = 1;
    for (i = 0; i < NTRK; i++)
        s->ch[i] = (uint8_t)i;                      /* track 1 on MIDI channel 1, ... */
    for (i = 0; i <= NTRK; i++) {
        s->t[i].to_next = NEVER;
        s->t[i].pp_dir = 1;
        s->t[i].rng = 0x1234567u * (i + 1);
    }
    s->clk_to_next = NEVER;
}

float gseq_tempo(const seq_t *s) { return s->ext ? s->ext_bpm : s->bpm; }

uint32_t gseq_step_q8(const seq_t *s, int rate)
{
    float bpm = gseq_tempo(s), q;
    if (bpm < 20.0f)
        bpm = 20.0f;
    if (bpm > 300.0f)
        bpm = 300.0f;
    q = (float)FS * 60.0f / bpm;                    /* samples per quarter */
    if (rate < 0 || rate >= NRATES)
        rate = RATE_16;
    return (uint32_t)(q * 256.0f * (float)TICKS_PER_STEP[rate] / 24.0f);
}

static const tpart_t *tpart(const seq_t *s, int t) { return &s->pat[s->tpat[t] % NPAT].t[t]; }
static int is_303(const seq_t *s, int t) { return t < NTRK && tt_notes(s->ttype[t]); }   /* a note track */
static int track_dir(const seq_t *s, int t) { return is_303(s, t) ? tpart(s, t)->dir & 3 : DIR_FWD; }

int gseq_track_len(const seq_t *s, int t)
{
    int n = t >= NTRK ? 16 : tpart(s, t)->len;
    return n < 1 ? 1 : n > NSTEPS ? NSTEPS : n;
}

static int track_rate(const seq_t *s, int t)
{
    int r = t >= NTRK ? RATE_16 : tpart(s, t)->rate;
    return r < NRATES ? r : RATE_16;
}

/* swing offset of a step, Q8: odd 16ths / 32nds come late; triplets and 8ths are never swung */
static uint32_t swing_q8(const seq_t *s, int t, int rate, uint32_t step_q8)
{
    uint32_t sw = s->swing;
    if ((rate != RATE_16 && rate != RATE_32) || !sw || t >= NTRK || (tpart(s, t)->flags & TF_NOSWING))
        return 0;
    if (sw > 100u)
        sw = 100u;
    return step_q8 / 200u * sw;                     /* 100 -> half a step late = 75 % */
}

static uint32_t rng_next(uint32_t *r)
{
    uint32_t x = *r ? *r : 1;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *r = x;
}

/* the step after p in this track's direction (also used to look ahead for TIEs) */
static int next_pos(seq_t *s, int t, int p, int commit)
{
    seq_track_t *tr = &s->t[t];
    int len = gseq_track_len(s, t), n;
    switch (track_dir(s, t)) {
    case DIR_REV:
        return (p - 1 + len) % len;
    case DIR_PINGPONG:
        if (len == 1)
            return 0;
        n = p + tr->pp_dir;
        if (n >= len || n < 0) {
            n = p - tr->pp_dir;
            if (commit)
                tr->pp_dir = (int8_t)-tr->pp_dir;
        }
        return n;
    case DIR_RANDOM:
        if (!commit)
            return (p + 1) % len;                    /* a TIE look-ahead cannot know: assume forward */
        return (int)(rng_next(&tr->rng) % (uint32_t)len);
    default:
        return (p + 1) % len;
    }
}

/* how long after its grid slot the step after p plays, Q8: the swing's delay if it is an odd step */
static uint32_t next_swing_delay(seq_t *s, int t, int p, int rate, uint32_t L)
{
    int odd;
    switch (track_dir(s, t)) {
    case DIR_REV:
        odd = (gseq_track_len(s, t) - 1 - next_pos(s, t, p, 0)) & 1;
        break;
    case DIR_RANDOM:
        odd = !s->t[t].odd;
        break;
    default:
        odd = next_pos(s, t, p, 0) & 1;
        break;
    }
    return odd ? swing_q8(s, t, rate, L) : 0;
}

static void midi(const seq_sink_t *o, uint8_t st, uint8_t d1, uint8_t d2)
{
    if (o->midi)
        o->midi(o->ctx, st, d1, d2);
}

static void note_release(seq_t *s, int t, const seq_sink_t *o)
{
    seq_track_t *tr = &s->t[t];
    if (tr->sounding) {
        o->note_off(o->ctx, t);
        tr->sounding = 0;
        if (tr->note_out) {
            if (s->send_notes && s->ch[t] != SEQ_CH_OFF)
                midi(o, (uint8_t)(0x80 | s->ch[t]), tr->note_out, 0);
            tr->note_out = 0;
        }
    }
    tr->to_off = 0;
}

/* the arpeggiator's notes still to come in a step: none (stop, restart, rest) */
static void arp_cancel(seq_track_t *tr)
{
    tr->arp_to_next = 0;
    tr->arp_left = 0;
}

static void fire_drum(seq_t *s, int t, int p, const seq_sink_t *o)
{
    const tpart_t *d = tpart(s, t);
    uint32_t bit = 1u << (p & 31);
    int w = p >> 5, v;
    float vel = (d->u.d.acc[w] & bit) ? 1.0f : (float)s->accent_q7 / 127.0f;
    if (s->mute & (1u << t))
        return;
    for (v = 0; v < NDSND; v++) {
        if (!(d->u.d.hit[v][w] & bit))
            continue;
        if (!o->drum(o->ctx, t, v, vel))
            continue;
        if (s->send_notes && s->ch[t] != SEQ_CH_OFF) {
            uint8_t mv = (uint8_t)(vel * 127.0f);
            midi(o, (uint8_t)(0x90 | s->ch[t]), GM_DRUM[v], mv);
            midi(o, (uint8_t)(0x80 | s->ch[t]), GM_DRUM[v], 0);
        }
    }
}

/* a note to the engine, and its echo on MIDI (a chord's root) */
static void play_note(seq_t *s, int t, int note, int chord, int accent, int slide, const seq_sink_t *o)
{
    seq_track_t *tr = &s->t[t];
    o->note_on(o->ctx, t, note, chord, accent, slide);
    if (s->send_notes && s->ch[t] != SEQ_CH_OFF) {
        uint8_t old = tr->note_out;
        midi(o, (uint8_t)(0x90 | s->ch[t]), (uint8_t)note, accent ? 127 : 90);
        if (old && old != note)
            midi(o, (uint8_t)(0x80 | s->ch[t]), old, 0);   /* legato: the new note first */
        tr->note_out = (uint8_t)note;
    }
    tr->sounding = 1;
}

/* the arpeggiator's next note: its chord over its octaves, in its order */
static int arp_next(seq_t *s, int t)
{
    seq_track_t *tr = &s->t[t];
    const tpart_t *bp = tpart(s, t);
    uint8_t nt[CHORD_NMAX];
    int n = gp_chord_notes(tr->arp_root, tr->arp_chord, nt), oct = bp->u.b.arp_oct % 3 + 1;
    int N = n * oct, i = tr->arp_i++, k, P, j, x;
    switch (bp->u.b.arp % NARPS) {
    case ARP_DOWN: k = N - 1 - i % N; break;
    case ARP_UPDN:
        P = N > 1 ? 2 * N - 2 : 1;
        j = i % P;
        k = j < N ? j : P - j;
        break;
    case ARP_RAND: k = (int)(rng_next(&tr->rng) % (uint32_t)N); break;
    default: k = i % N; break;
    }
    x = nt[k % n] + 12 * (k / n);
    return x > 127 ? 127 : x;
}

/* the arpeggiator's note now; carry: how far into this sample it was due */
static void arp_fire(seq_t *s, int t, uint32_t carry, const seq_sink_t *o)
{
    seq_track_t *tr = &s->t[t];
    play_note(s, t, arp_next(s, t), 0, tr->arp_acc, 0, o);
    tr->to_off = tr->arp_left || !tr->arp_hold ? carry + tr->arp_period / 2u : 0;
    if (tr->arp_left) {
        tr->arp_left--;
        tr->arp_to_next = carry + tr->arp_period;
    } else {
        tr->arp_to_next = 0;
    }
}

static void fire_303(seq_t *s, int t, int p, uint32_t step_q8, uint32_t carry, const seq_sink_t *o)
{
    seq_track_t *tr = &s->t[t];
    const tpart_t *bp = tpart(s, t);
    const bstep_t *st = &bp->u.b.step[p];
    int gate = bstep_gate(st), note, hold, nx, chord = bstep_chord(st), acc = (st->flags & BS_ACCENT) != 0;
    uint8_t prev_slide = tr->held_note & 0x80u;
    if (s->mute & (1u << t))
        gate = G_REST;
    arp_cancel(tr);
    if (gate == G_REST) {
        note_release(s, t, o);
        tr->held_note = 0;
        return;
    }
    note = st->note + (int)bp->u.b.transpose - 24;
    note = note < 0 ? 0 : note > 127 ? 127 : note;
    nx = next_pos(s, t, p, 0);
    hold = (st->flags & BS_SLIDE) || bstep_gate(&bp->u.b.step[nx]) == G_TIE;
    if (bp->u.b.arp % NARPS) {                       /* the arpeggiator plays the step */
        int div = bp->u.b.arp_div % 4 + 1;
        if (gate == G_NOTE || !tr->sounding) {
            if (note != tr->arp_root || chord != tr->arp_chord)
                tr->arp_i = 0;                       /* a new chord: from its first note */
            tr->arp_root = (uint8_t)note;
            tr->arp_chord = (uint8_t)chord;
            tr->arp_acc = (uint8_t)acc;
        }
        tr->arp_hold = (uint8_t)hold;
        tr->arp_period = step_q8 / (uint32_t)div;
        tr->arp_left = (uint8_t)(div - 1);
        tr->held_note = 0;
        arp_fire(s, t, carry, o);
        return;
    }
    if (gate == G_NOTE || !tr->sounding)
        play_note(s, t, note, chord, acc, tr->sounding && prev_slide, o);
    tr->held_note = (uint8_t)((note & 0x7F) | ((st->flags & BS_SLIDE) ? 0x80 : 0));
    tr->to_off = hold ? 0 : carry + step_q8 / 2u;
}

/* the bar's end (the bar clock wrapping), or the start: each cued track takes its pattern. Returns the
 * tracks that switched (bit t); a cue of the pattern a track plays restarts it too */
static uint32_t bar_end(seq_t *s)
{
    uint32_t changed = 0;
    int t;
    for (t = 0; t < NTRK; t++)
        if (s->tcue[t] < NPAT) {
            s->tpat[t] = s->tcue[t];
            s->tcue[t] = 0xFF;
            changed |= 1u << t;
        }
    return changed;
}

/* these tracks from their first step at once (their pattern changed at the bar) */
static void restart_tracks(seq_t *s, uint32_t mask, const seq_sink_t *o)
{
    int t;
    for (t = 0; t < NTRK; t++) {
        seq_track_t *tr = &s->t[t];
        if (!(mask >> t & 1u))
            continue;
        if (tr->sounding && tt_notes(tr->played_type))
            note_release(s, t, o);
        arp_cancel(tr);
        tr->started = 0;
        tr->to_next = s->ext ? NEVER : 0;
        tr->swing_delay = 0;
        tr->ext_ticks = (uint8_t)(TICKS_PER_STEP[track_rate(s, t)] - 1);
        tr->pp_dir = 1;
    }
}

/* fire track t's next step now; returns the tracks whose pattern the bar clock's wrap switched */
static uint32_t fire_step(seq_t *s, int t, const seq_sink_t *o)
{
    seq_track_t *tr = &s->t[t];
    int rate = track_rate(s, t), p, wrapped;
    uint32_t changed = 0;
    uint32_t L = gseq_step_q8(s, rate);
    uint32_t carry = tr->to_next < 256u ? tr->to_next : 0;   /* the step was due this far into the sample */
    if (!tr->started) {
        p = track_dir(s, t) == DIR_REV ? gseq_track_len(s, t) - 1 : 0;
        tr->started = 1;
        tr->odd = 0;
        wrapped = 0;
    } else {
        tr->odd ^= 1u;
        p = next_pos(s, t, tr->pos, 1);
        wrapped = p == 0;
    }
    if (t == TRK_BAR && wrapped) {
        s->bars++;
        changed = bar_end(s);
    }
    tr->pos = (uint8_t)p;
    if (t < NTRK) {
        int tt = s->ttype[t];
        if (tt_notes(tr->played_type) && !tt_notes(tt)) {
            note_release(s, t, o);
            arp_cancel(tr);
        }                   /* its type changed under a held note */
        tr->played_type = (uint8_t)tt;
        if (o->step)
            o->step(o->ctx, t, p);
        if (tt == TT_DRUM)
            fire_drum(s, t, p, o);
        else if (tt_notes(tt))
            fire_303(s, t, p, L, carry, o);
    }
    if (s->ext) {
        tr->to_next = NEVER;                         /* the clock arms the next one */
    } else {
        uint32_t slot = L > tr->swing_delay ? L - tr->swing_delay : 0;
        tr->swing_delay = next_swing_delay(s, t, p, rate, L);
        tr->to_next = carry + slot + tr->swing_delay;
        tr->step_len = tr->to_next;
    }
    return changed;
}

static void do_start(seq_t *s, int from_top, const seq_sink_t *o)
{
    int t;
    if (from_top) {
        bar_end(s);
        s->bars = 0;
    }
    for (t = 0; t <= NTRK; t++) {
        seq_track_t *tr = &s->t[t];
        int rate = track_rate(s, t);
        if (from_top) {
            tr->started = 0;
            tr->pp_dir = 1;
            tr->arp_i = 0;
        }
        tr->to_off = 0;
        tr->swing_delay = !s->ext && tr->started ? next_swing_delay(s, t, tr->pos, rate, gseq_step_q8(s, rate)) : 0;
        tr->to_next = s->ext ? NEVER : tr->swing_delay;
        tr->ext_ticks = (uint8_t)(TICKS_PER_STEP[rate] - 1);   /* the first clock is the downbeat */
    }
    s->clk_to_next = 0;
    s->playing = 1;
    if (!s->ext && s->send_clock)
        midi(o, from_top ? 0xFA : 0xFB, 0, 0);
}

static void do_stop(seq_t *s, const seq_sink_t *o)
{
    int t;
    s->playing = 0;
    for (t = 0; t < NTRK; t++) {
        note_release(s, t, o);
        arp_cancel(&s->t[t]);
    }
    for (t = 0; t <= NTRK; t++)
        s->t[t].to_next = NEVER;
    if (!s->ext && s->send_clock)
        midi(o, 0xFC, 0, 0);
}

/* external clock ticks: arm the steps they complete */
static void ext_ticks(seq_t *s)
{
    int t;
    uint32_t n = s->ext_pending;
    s->ext_pending = 0;
    for (; n; n--) {
        if (s->ext_since > 0 && s->ext_since < FS) {
            uint32_t q = s->ext_since << 8;
            s->ext_period = s->ext_period ? s->ext_period - (s->ext_period >> 3) + (q >> 3) : q;
            s->ext_bpm = (float)FS * 60.0f * 256.0f / (24.0f * (float)s->ext_period);
        }
        s->ext_since = 0;
        if (!s->playing)
            continue;
        for (t = 0; t <= NTRK; t++) {
            seq_track_t *tr = &s->t[t];
            int rate = track_rate(s, t), tps = TICKS_PER_STEP[rate];
            if (++tr->ext_ticks < tps)
                continue;
            tr->ext_ticks = 0;
            {
                uint32_t L = s->ext_period ? s->ext_period * (uint32_t)tps : gseq_step_q8(s, rate);
                tr->swing_delay = tr->started ? next_swing_delay(s, t, tr->pos, rate, L) : 0;
                tr->to_next = tr->swing_delay;
            }
        }
    }
}

uint32_t gseq_until_event(seq_t *s, uint32_t n)
{
    uint32_t m = n, e;
    int t;
    if (!s->playing)
        return n;
    for (t = 0; t <= NTRK; t++) {
        if (s->t[t].to_next != NEVER && (e = s->t[t].to_next >> 8) < m)
            m = e;
        if (s->t[t].to_off && (e = s->t[t].to_off >> 8) < m)
            m = e;
        if (s->t[t].arp_to_next && (e = s->t[t].arp_to_next >> 8) < m)
            m = e;
    }
    if (!s->ext && s->send_clock && (e = s->clk_to_next >> 8) < m)
        m = e;
    return m ? m : 1;
}

void gseq_advance(seq_t *s, uint32_t k, const seq_sink_t *o)
{
    int t, guard;
    uint32_t dq = k << 8;
    s->ext_since += k;
    if (s->ext_pending)
        s->ext = 1;
    else if (s->ext && s->ext_since > FS / 2u) {    /* clock gone for 0.5 s: back to internal */
        s->ext = 0;
        for (t = 0; t <= NTRK; t++)
            if (s->playing && s->t[t].to_next == NEVER) {
                s->t[t].to_next = 0;
                s->t[t].swing_delay = 0;
            }
    }
    if (s->req_stop) {
        s->req_stop = 0;
        s->req_start = s->req_cont = 0;
        if (s->playing)
            do_stop(s, o);
    }
    if (s->req_start) {
        s->req_start = 0;
        do_start(s, 1, o);
    }
    if (s->req_cont) {
        s->req_cont = 0;
        do_start(s, 0, o);
    }
    if (s->ext_pending)
        ext_ticks(s);
    if (!s->playing) {
        if (!s->ext)
            s->clk_to_next = 0;
        for (t = 0; t < NTRK; t++)                   /* stopped: a cue takes effect at once */
            if (s->tcue[t] < NPAT) {
                s->tpat[t] = s->tcue[t];
                s->tcue[t] = 0xFF;
            }
        for (t = 0; t < NTRK; t++)                   /* a note played by hand while stopped falls by itself */
            if (s->t[t].to_off) {
                s->t[t].to_off = s->t[t].to_off > dq ? s->t[t].to_off - dq : 1;
                if (s->t[t].to_off < 256u)
                    note_release(s, t, o);
            }
        return;
    }
    for (t = 0; t <= NTRK; t++) {                    /* move time */
        seq_track_t *tr = &s->t[t];
        if (tr->to_next != NEVER)
            tr->to_next = tr->to_next > dq ? tr->to_next - dq : 0;
        if (tr->to_off)
            tr->to_off = tr->to_off > dq ? tr->to_off - dq : 1;   /* 1: due, still "set" */
        if (tr->arp_to_next)
            tr->arp_to_next = tr->arp_to_next > dq ? tr->arp_to_next - dq : 1;
    }
    if (!s->ext && s->send_clock)
        s->clk_to_next = s->clk_to_next > dq ? s->clk_to_next - dq : 0;
    /* fire what is due: the bar clock first, since its wrap may switch the pattern and restart
     * every track on this same sample */
    for (guard = 0; guard < 8; guard++) {
        int fired = 0;
        seq_track_t *bar = &s->t[TRK_BAR];
        if (bar->to_next < 256u) {
            uint32_t ch = fire_step(s, TRK_BAR, o);
            if (ch)
                restart_tracks(s, ch, o);
            fired = 1;
        }
        for (t = 0; t < NTRK; t++) {
            seq_track_t *tr = &s->t[t];
            if (tr->to_off && tr->to_off < 256u) {    /* gate falls (before a new step at the same time) */
                note_release(s, t, o);
                fired = 1;
            }
            if (tr->arp_to_next && tr->arp_to_next < 256u && tr->to_next >= 256u) {   /* the arp's next note */
                arp_fire(s, t, tr->arp_to_next < 256u ? tr->arp_to_next - 1u : 0, o);
                fired = 1;
            }
            if (tr->to_next < 256u) {
                fire_step(s, t, o);
                fired = 1;
            }
        }
        if (!fired)
            break;
    }
    if (!s->ext && s->send_clock && s->clk_to_next < 256u) {
        midi(o, 0xF8, 0, 0);
        s->clk_to_next += gseq_step_q8(s, RATE_16) / 6u;          /* 24 ppqn */
    }
}

void gseq_start(seq_t *s) { s->req_start = 1; }
void gseq_stop(seq_t *s) { s->req_stop = 1; }
void gseq_continue(seq_t *s) { s->req_cont = 1; }
void gseq_ext_clock(seq_t *s) { s->ext_pending++; }
void gseq_cue(seq_t *s, int p)
{
    int t;
    if (p >= 0 && p < NPAT)
        for (t = 0; t < NTRK; t++)
            s->tcue[t] = (uint8_t)p;
}
void gseq_cue_track(seq_t *s, int t, int p)
{
    if (t >= 0 && t < NTRK && p >= 0 && p < NPAT)
        s->tcue[t] = (uint8_t)p;
}
int gseq_cue_of(const seq_t *s, int t) { return t >= 0 && t < NTRK && s->tcue[t] < NPAT ? s->tcue[t] : -1; }
