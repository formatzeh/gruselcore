/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore UI: 8 tracks on the FM-1's panel. Everything here runs in the main loop; it edits the
 * project in place (the sequencer reads the patterns as they are) and tells the engine about sound
 * changes through engine_set, so nothing ever waits for the sequencer to stop.
 *
 * Screens (the button that opens each):
 *   HOME  all 8 tracks; the keyboard plays the selected track (drum sounds, or a 303 / VA chromatic,
 *         OCT-/+ the octave). HOME held: white keys cue the selected track's pattern 1-16 (OCT-/+:
 *         17-32; with SEL held too, every track's), black keys 1-8 mute. Knobs: the track's four main
 *         controls (a kit's macros, the 303's or VA's filter)
 *   SEQ   the selected track's steps. DRUM: a grid of its 8 sounds; black keys 1-8 pick the sound,
 *         white keys set its steps (ENV held: accents). 303 / VA: white keys pick a step and switch it
 *         on / off (ENV held: its accent); held, KNOB 1-4 set its note, gate, chord, slide. SELECT or
 *         ARP: the arpeggiator's page. OCT-/+: steps 17-64
 *   EDIT  the selected track's sound, 4 pots a page (SELECT turns the pages); the keyboard plays the
 *         track (on a DRUM track a key also picks the sound to edit); PRESETS loads a kit
 *   FX    the track's filter, resonance, drive, level; then pan and sends; press again: the shared
 *         reverb, delay and master
 *   LFO   the mixer: levels, pans, sends, meters; black keys mute
 *   GLO   the track's type (SEL applies it), its MIDI channel, clock and notes out, about
 * ALGORITHM selects the track everywhere. PLAY starts and stops, REC records notes played on the keys.
 * SAVE saves (playing: when it stops, as the flash pauses the sound while it writes). */
#include "gc.h"
#include "../dsp/master.h"           /* MST_* (HOME's knobs, the master pages) */
#include "../dsp/bass303.h"          /* BASS303_* (HOME's knobs on a 303 track) */
#include "../dsp/gva.h"              /* VA_*, FM_*, PH_*: HOME's knobs on a synth track */
#include "../dsp/gfm.h"
#include "../dsp/gphys.h"

/* ------------------------------------------------------------- state --- */
enum { V_HOME, V_SEQ, V_EDIT, V_FX, V_MIX, V_GLO, NVIEWS };
static const char *const VIEW_N[NVIEWS] = {"HOME", "SEQ", "EDIT", "FX", "MIX", "GLO"};
static const char *const TYPE_N[NTT] = {"OFF", "DRUM", "303", "VA", "FM", "PHYS"};
static const char *const ARP_N[NARPS] = {"OFF", "UP", "DOWN", "UP-DN", "RAND"};
static const char *const RATE_N[NRATES] = {"1/16", "1/16T", "1/32", "1/8T", "1/8"};
static const char *const DIR_N[NDIRS] = {"FWD", "REV", "PING", "RAND"};
static const char *const GATE_N[3] = {"REST", "NOTE", "TIE"};
static const char *const NOTE_N[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};

static struct {
    uint8_t view, trk, snd, page;      /* screen, selected track, drum sound, 16-step page */
    uint8_t epage, fxpage, glopage;    /* knob pages of EDIT, FX, GLO */
    uint8_t spage;                     /* SEQ, a note track: 0 the track, 1 its arpeggiator */
    uint8_t pbank;                     /* HOME: patterns 1-16 or 17-32 */
    uint8_t rec;                       /* recording */
    int8_t oct;                        /* the keyboard's octave, -3..+3 (0: F2 on the lowest key) */
    uint8_t home_used;                 /* HOME held: a key was used (patterns, mutes) */
    uint8_t glo_used;                  /* GLO held: SELECT set the tempo (GLO then does not open) */
    int8_t held_step;                  /* SEQ, 303: the step held (-1 none) */
    uint8_t pend_type;                 /* GLO: the type SEL would apply */
    uint8_t dirty, redraw, save_wait;
    uint32_t btn, keys;                /* held last frame */
    uint32_t act_t, saved_t, say_t, frame_t;
    char say_a[28], say_b[28];
    uint8_t say_warn;
    uint32_t last_hash;
    int last_bar;                        /* the bar.beat on the screen (bar_key) */
} ui;
uint8_t ui_autosave_block;
static uint8_t save_hold;

/* the 27 keys from F3: white keys 0..15, black keys 0..10 */
static int8_t key_white[NKEYS], key_black[NKEYS];
static void keys_init(void)
{
    int k, w = 0, b = 0;
    for (k = 0; k < NKEYS; k++) {
        int s = (5 + k) % 12;                  /* F3 is key 0 */
        int black = s == 1 || s == 3 || s == 6 || s == 8 || s == 10;
        key_white[k] = (int8_t)(black ? -1 : w++);
        key_black[k] = (int8_t)(black ? b++ : -1);
    }
}

/* ----------------------------------------------------------- helpers --- */
static void put_num(char *b, int v)
{
    char t[12];
    int n = 0, i = 0;
    if (v < 0) {
        b[i++] = '-';
        v = -v;
    }
    do {
        t[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v);
    while (n)
        b[i++] = t[--n];
    b[i] = 0;
}
static void put_2(char *b, int v)
{
    b[0] = (char)('0' + (v / 10) % 10);
    b[1] = (char)('0' + v % 10);
    b[2] = 0;
}
static void scat(char *d, const char *s)
{
    while (*d)
        d++;
    while ((*d++ = *s++))
        ;
}
static void note_name(char *b, int n)
{
    b[0] = 0;
    scat(b, NOTE_N[n % 12]);
    {
        char o[4];
        put_num(o, n / 12 - 1);
        scat(b, o);
    }
}
static int strlen_(const char *s)
{
    int n = 0;
    while (s[n])
        n++;
    return n;
}
static void touch(void)
{
    ui.dirty = 1;
    ui.act_t = plat_ms();
}
void ui_say(const char *a, const char *b)
{
    int i;
    for (i = 0; i < 27 && a && a[i]; i++)
        ui.say_a[i] = a[i];
    ui.say_a[i] = 0;
    for (i = 0; i < 27 && b && b[i]; i++)
        ui.say_b[i] = b[i];
    ui.say_b[i] = 0;
    ui.say_t = plat_ms() | 1u;
    ui.say_warn = 0;
}
void ui_warn(const char *a, const char *b)
{
    ui_say(a, b);
    ui.say_warn = 1;
}
static tpart_t *tp_of(int t) { return &proj.pat[seq.tpat[t] % NPAT].t[t]; }   /* track t in the pattern it plays */
static tpart_t *cur_tp(void) { return tp_of(ui.trk); }
static int ttype(int t) { return proj.sound.ttype[t]; }
static int notes(int t) { return tt_notes(proj.sound.ttype[t]); }   /* a 303 or VA track */

/* a pot of the sound: set in the mirror and sent to the engine */
static void pot_set(int target, int voice, int i, int v)
{
    const x0x_param_t *p = engine_param(target, voice, i);
    uint8_t *m = 0;
    if (!p)
        return;
    v = v < 0 ? 0 : v > p->max ? p->max : v;
    switch (target) {
    case T_DRUM: m = &proj.sound.drum[voice / NDSND][voice % NDSND][i]; break;
    case T_303: m = &proj.sound.b303[voice][i]; break;
    case T_MIX: m = &proj.sound.mix[voice][i]; break;
    case T_FX: m = &proj.sound.fx[voice * 16 + i]; break;
    case T_MST: m = &proj.sound.mst[i]; break;
    case T_DMAC: m = &proj.sound.dmac[voice][i]; break;
    case T_SYN: m = &proj.sound.syn[voice][i]; break;
    default: return;
    }
    if (*m == v)
        return;
    *m = (uint8_t)v;
    engine_set(target, voice, i, v);
    touch();
}
static int pot_get(int target, int voice, int i)
{
    switch (target) {
    case T_DRUM: return proj.sound.drum[voice / NDSND][voice % NDSND][i];
    case T_303: return proj.sound.b303[voice][i];
    case T_MIX: return proj.sound.mix[voice][i];
    case T_FX: return proj.sound.fx[voice * 16 + i];
    case T_MST: return proj.sound.mst[i];
    case T_DMAC: return proj.sound.dmac[voice][i];
    case T_SYN: return proj.sound.syn[voice][i];
    default: return 0;
    }
}
/* a knob turn on a pot: continuous pots move a step a detent (faster when spun), switches one position */
static void pot_turn(int target, int voice, int i, int d)
{
    const x0x_param_t *p = engine_param(target, voice, i);
    if (!p || !d)
        return;
    if (p->max == 127 && (d > 2 || d < -2))
        d *= 3;
    pot_set(target, voice, i, pot_get(target, voice, i) + d);
}

/* ----------------------------------------------------- knob pages --- */
/* what KNOB 1-4 control on the screen showing: (target, voice, index) each, or a special role */
enum { KR_NONE, KR_POT, KR_TEMPO, KR_SWING, KR_LEN, KR_RATE, KR_TSWING, KR_DIR, KR_TRANS,
       KR_SNOTE, KR_SGATE, KR_SCHORD, KR_SSLIDE, KR_ARP, KR_ARPDIV, KR_ARPOCT, KR_TYPE, KR_MCH, KR_CLK, KR_NOTES };
typedef struct { uint8_t role, target, voice, index; } knob_t;

static int fx_pages(void) { return (engine_nparams(T_FX, 0) + engine_nparams(T_FX, 1) + 3) / 4; }

static void knobs_of(knob_t *k)
{
    int i, t = ui.trk;
    for (i = 0; i < 4; i++)
        k[i].role = KR_NONE, k[i].target = k[i].voice = k[i].index = 0;
    switch (ui.view) {
    case V_HOME:                                       /* the track's four main controls (as Skiff) */
        if (ttype(t) == TT_DRUM)
            for (i = 0; i < 4; i++)
                k[i] = (knob_t){KR_POT, T_DMAC, (uint8_t)t, (uint8_t)i};   /* kit TUNE, DECAY, DRIVE, TONE */
        else if (ttype(t) == TT_303) {
            static const uint8_t B[4] = {BASS303_CUTOFF, BASS303_RESO, BASS303_ENVMOD, BASS303_DECAY};
            for (i = 0; i < 4; i++)
                k[i] = (knob_t){KR_POT, T_303, (uint8_t)t, B[i]};
        } else if (ttype(t) >= TT_VA) {
            static const uint8_t V[4] = {VA_CUTOFF, VA_RESO, VA_ENV, VA_FDEC};
            static const uint8_t F[4] = {FM_L2, FM_D2, FM_FEEDBK, FM_REL};
            static const uint8_t H[4] = {PH_DECAY, PH_TONE, PH_HARD, PH_CUTOFF};
            const uint8_t *m = ttype(t) == TT_VA ? V : ttype(t) == TT_FM ? F : H;
            for (i = 0; i < 4; i++)
                k[i] = (knob_t){KR_POT, T_SYN, (uint8_t)t, m[i]};
        }
        break;
    case V_SEQ:
        if (notes(t) && ui.held_step >= 0) {
            k[0].role = KR_SNOTE;
            k[1].role = KR_SGATE;
            k[2].role = KR_SCHORD;
            k[3].role = KR_SSLIDE;
        } else if (notes(t) && ui.spage) {           /* the arpeggiator (ARP, or SELECT) */
            k[0].role = KR_ARP;
            k[1].role = KR_ARPDIV;
            k[2].role = KR_ARPOCT;
            k[3].role = KR_DIR;
        } else {
            k[0].role = KR_LEN;
            k[1].role = KR_RATE;
            k[2].role = KR_TSWING;
            k[3].role = notes(t) ? KR_TRANS : KR_NONE;
        }
        break;
    case V_EDIT:
        if (ttype(t) == TT_DRUM)
            for (i = 0; i < 4 && ui.epage * 4 + i < GP_N; i++)
                k[i] = (knob_t){KR_POT, T_DRUM, (uint8_t)(t * NDSND + ui.snd), (uint8_t)(ui.epage * 4 + i)};
        else if (ttype(t) == TT_303)
            for (i = 0; i < 4 && ui.epage * 4 + i < engine_nparams(T_303, t); i++)
                k[i] = (knob_t){KR_POT, T_303, (uint8_t)t, (uint8_t)(ui.epage * 4 + i)};
        else if (ttype(t) >= TT_VA)
            for (i = 0; i < 4 && ui.epage * 4 + i < engine_nparams(T_SYN, t); i++)
                k[i] = (knob_t){KR_POT, T_SYN, (uint8_t)t, (uint8_t)(ui.epage * 4 + i)};
        break;
    case V_FX:
        if (ui.fxpage == 0) {
            k[0] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_FILTER};
            k[1] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_RESO};
            k[2] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_DRIVE};
            k[3] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_LEVEL};
        } else if (ui.fxpage == 1) {
            k[0] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_PAN};
            k[1] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_REV};
            k[2] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_DLY};
        } else {
            int base = (ui.fxpage - 2) * 4, nfx = engine_nparams(T_FX, 0) + engine_nparams(T_FX, 1);
            for (i = 0; i < 4; i++) {
                int q = base + i;
                if (q < nfx)
                    k[i] = (knob_t){KR_POT, T_FX, (uint8_t)(q / 16), (uint8_t)(q % 16)};
                else if (q - nfx < MST_NPARAMS)
                    k[i] = (knob_t){KR_POT, T_MST, 0, (uint8_t)(q - nfx)};
            }
        }
        break;
    case V_MIX:
        k[0] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_LEVEL};
        k[1] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_PAN};
        k[2] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_REV};
        k[3] = (knob_t){KR_POT, T_MIX, (uint8_t)t, MX_DLY};
        break;
    case V_GLO:
        if (!ui.glopage) {
            k[0].role = KR_TYPE;
            k[1].role = KR_MCH;
            k[2].role = KR_CLK;
            k[3].role = KR_NOTES;
        } else {                                       /* page 2: the global groove and master */
            k[0].role = KR_SWING;
            k[1] = (knob_t){KR_POT, T_MST, 0, MST_DJF};
            k[2] = (knob_t){KR_POT, T_MST, 0, MST_PUMP};
            k[3].role = KR_TEMPO;
        }
        break;
    default:
        break;
    }
}

static int fxpage_count(void) { return 2 + (fx_pages() * 4 + MST_NPARAMS + 3) / 4; }

static void knob_label(const knob_t *k, char *name, char *val)
{
    tpart_t *tp = cur_tp();
    name[0] = val[0] = 0;
    switch (k->role) {
    case KR_POT: {
        const x0x_param_t *p = engine_param(k->target, k->voice, k->index);
        int v = pot_get(k->target, k->voice, k->index);
        if (!p)
            return;
        scat(name, p->name);
        if (p->names)
            scat(val, p->names[v]);
        else if (k->target == T_MIX && k->index == MX_PAN && v == 64)
            scat(val, "C");
        else if (k->target == T_SYN && ttype(k->voice) == TT_VA && k->index == VA_TUNE2) {   /* semitones from osc 1 */
            if (v > 24)
                scat(val, "+");
            put_num(val + (v > 24), v - 24);
        }
        else if (k->target == T_DMAC) {                 /* a kit macro: its offset from the kit */
            if (v > 64)
                scat(val, "+");
            put_num(val + (v > 64), v - 64);
        }
        else if ((k->target == T_MIX && k->index == MX_FILTER) || (k->target == T_MST && k->index == MST_DJF)) {
            if (v >= 62 && v <= 66)
                scat(val, "OFF");
            else
                scat(val, v < 64 ? "LP" : "HP"), put_num(val + 2, v < 64 ? 64 - v : v - 64);
        }
        else
            put_num(val, v);
        break;
    }
    case KR_TEMPO: {
        int b = (int)(seq.bpm * 10.0f + 0.5f);
        scat(name, "TEMPO");
        put_num(val, b / 10);
        scat(val, ".");
        {
            char d[3] = {(char)('0' + b % 10), 0, 0};
            scat(val, d);
        }
        break;
    }
    case KR_SWING:
        scat(name, "SWING");
        put_num(val, 50 + seq.swing / 4);
        scat(val, "%");
        break;
    case KR_LEN: scat(name, "LENGTH"); put_num(val, tp->len); break;
    case KR_RATE: scat(name, "RATE"); scat(val, RATE_N[tp->rate % NRATES]); break;
    case KR_TSWING: scat(name, "SWING"); scat(val, (tp->flags & TF_NOSWING) ? "OFF" : "ON"); break;
    case KR_DIR: scat(name, "DIR"); scat(val, DIR_N[tp->dir & 3]); break;
    case KR_TRANS: scat(name, "TRANSP"); put_num(val, (int)tp->u.b.transpose - 24); break;
    case KR_SNOTE: scat(name, "NOTE"); note_name(val, tp->u.b.step[ui.held_step].note); break;
    case KR_SGATE: scat(name, "GATE"); scat(val, GATE_N[bstep_gate(&tp->u.b.step[ui.held_step]) % 3]); break;
    case KR_SCHORD: scat(name, "CHORD"); scat(val, gp_chords[bstep_chord(&tp->u.b.step[ui.held_step])].name); break;
    case KR_ARP: scat(name, "ARP"); scat(val, ARP_N[tp->u.b.arp % NARPS]); break;
    case KR_ARPDIV: scat(name, "NOTES"); put_num(val, tp->u.b.arp_div % 4 + 1); scat(val, "/STEP"); break;
    case KR_ARPOCT: scat(name, "OCTAVES"); put_num(val, tp->u.b.arp_oct % 3 + 1); break;
    case KR_SSLIDE: scat(name, "SLIDE"); scat(val, (tp->u.b.step[ui.held_step].flags & BS_SLIDE) ? "ON" : "OFF"); break;
    case KR_TYPE:
        scat(name, "TYPE");
        scat(val, TYPE_N[ui.pend_type % NTT]);
        if (ui.pend_type != ttype(ui.trk))
            scat(val, "?");
        break;
    case KR_MCH:
        scat(name, "MIDI CH");
        if (seq.ch[ui.trk] == SEQ_CH_OFF)
            scat(val, "OFF");
        else
            put_num(val, seq.ch[ui.trk] + 1);
        break;
    case KR_CLK: scat(name, "CLK OUT"); scat(val, seq.send_clock ? "ON" : "OFF"); break;
    case KR_NOTES: scat(name, "NOTES OUT"); scat(val, seq.send_notes ? "ON" : "OFF"); break;
    default: break;
    }
}

static const uint8_t LENS[4] = {8, 16, 32, 64};
static void knob_turn(const knob_t *k, int d)
{
    tpart_t *tp = cur_tp();
    int i;
    if (!d)
        return;
    switch (k->role) {
    case KR_POT: pot_turn(k->target, k->voice, k->index, d); return;
    case KR_TEMPO: {                                  /* 1 BPM a detent */
        float b = (float)(int)(seq.bpm + 0.5f) + (float)d;
        seq.bpm = b < 40.0f ? 40.0f : b > 300.0f ? 300.0f : b;
        break;
    }
    case KR_SWING: {
        int s = seq.swing + d * 4;
        seq.swing = (uint8_t)(s < 0 ? 0 : s > 100 ? 100 : s);
        break;
    }
    case KR_LEN:
        for (i = 0; i < 4 && LENS[i] != tp->len; i++)
            ;
        i = (i == 4 ? 1 : i) + d;
        tp->len = LENS[i < 0 ? 0 : i > 3 ? 3 : i];
        if (ui.page * 16 >= tp->len)
            ui.page = 0;
        break;
    case KR_RATE: {
        int r = tp->rate + d;
        tp->rate = (uint8_t)(r < 0 ? 0 : r >= NRATES ? NRATES - 1 : r);
        break;
    }
    case KR_TSWING: tp->flags = (uint8_t)(d > 0 ? tp->flags & ~TF_NOSWING : tp->flags | TF_NOSWING); break;
    case KR_DIR: tp->dir = (uint8_t)((tp->dir + (d > 0 ? 1 : NDIRS - 1)) % NDIRS); break;
    case KR_TRANS: {
        int v = tp->u.b.transpose + d;
        tp->u.b.transpose = (uint8_t)(v < 0 ? 0 : v > 48 ? 48 : v);
        break;
    }
    case KR_SNOTE: {
        bstep_t *s = &tp->u.b.step[ui.held_step];
        int n = s->note + d;
        s->note = (uint8_t)(n < 12 ? 12 : n > 96 ? 96 : n);
        if (bstep_gate(s) == G_REST)
            s->flags = (uint8_t)((s->flags & ~BS_GATE_MASK) | G_NOTE);
        if (!seq.playing)
            engine_note_on(ui.trk, s->note, bstep_chord(s), 0, 0);
        break;
    }
    case KR_SGATE: {
        bstep_t *s = &tp->u.b.step[ui.held_step];
        int g = (bstep_gate(s) + (d > 0 ? 1 : 2)) % 3;
        s->flags = (uint8_t)((s->flags & ~BS_GATE_MASK) | g);
        break;
    }
    case KR_SCHORD: {
        bstep_t *s = &tp->u.b.step[ui.held_step];
        int c = bstep_chord(s) + d;
        c = c < 0 ? 0 : c >= NCHORDS ? NCHORDS - 1 : c;
        s->flags = (uint8_t)((s->flags & ~BS_CHORD_MASK) | (c << BS_CHORD_SHIFT));
        if (bstep_gate(s) == G_REST)
            s->flags = (uint8_t)((s->flags & ~BS_GATE_MASK) | G_NOTE);
        if (!seq.playing)
            engine_note_on(ui.trk, s->note, c, 0, 0);
        break;
    }
    case KR_ARP: {
        int a = tp->u.b.arp % NARPS + d;
        tp->u.b.arp = (uint8_t)(a < 0 ? 0 : a >= NARPS ? NARPS - 1 : a);
        break;
    }
    case KR_ARPDIV: {
        int a = tp->u.b.arp_div % 4 + d;
        tp->u.b.arp_div = (uint8_t)(a < 0 ? 0 : a > 3 ? 3 : a);
        break;
    }
    case KR_ARPOCT: {
        int a = tp->u.b.arp_oct % 3 + d;
        tp->u.b.arp_oct = (uint8_t)(a < 0 ? 0 : a > 2 ? 2 : a);
        break;
    }
    case KR_SSLIDE: tp->u.b.step[ui.held_step].flags = (uint8_t)(d > 0 ? tp->u.b.step[ui.held_step].flags | BS_SLIDE : tp->u.b.step[ui.held_step].flags & ~BS_SLIDE); break;
    case KR_TYPE: ui.pend_type = (uint8_t)(((ui.pend_type + d) % NTT + NTT) % NTT); break;
    case KR_MCH: {
        int c = seq.ch[ui.trk] == SEQ_CH_OFF ? 16 : seq.ch[ui.trk];
        c += d > 0 ? 1 : -1;
        c = c < 0 ? 0 : c > 16 ? 16 : c;
        seq.ch[ui.trk] = (uint8_t)(c == 16 ? SEQ_CH_OFF : c);
        break;
    }
    case KR_CLK: seq.send_clock = (uint8_t)(d > 0); break;
    case KR_NOTES: seq.send_notes = (uint8_t)(d > 0); break;
    default: return;
    }
    touch();
}

/* ------------------------------------------------------------ input --- */
static void select_track(int t)
{
    if (t < 0 || t >= NTRK || t == ui.trk)
        return;
    ui.trk = (uint8_t)t;
    ui.held_step = -1;
    ui.pend_type = (uint8_t)ttype(t);
    ui.epage = 0;
    ui.spage = 0;
    if (ui.page * 16 >= cur_tp()->len)
        ui.page = 0;
}

static void open_view(int v)
{
    if (v == V_FX && ui.view == V_FX)
        ui.fxpage = (uint8_t)(ui.fxpage < 2 ? 2 : 0);    /* FX again: the shared effects, and back */
    else if (v == V_GLO && ui.view == V_GLO)
        ui.glopage ^= 1u;
    if (v == V_SEQ && ui.view != V_SEQ)
        ui.spage = 0;                                   /* SEQ opens on the track's page (ARP: its arpeggiator) */
    ui.view = (uint8_t)v;
    ui.held_step = -1;
    ui.pend_type = (uint8_t)ttype(ui.trk);
}

static void save_project(void)
{
    if (seq.playing || seq.req_stop) {
        ui.save_wait = 1;
        ui_say("SAVES WHEN STOPPED", "(THE FLASH PAUSES THE SOUND)");
        return;
    }
    ui.save_wait = 0;
    switch (project_save()) {
    case 0:
        ui.dirty = 0;
        ui_autosave_block = 0;                          /* saved on purpose: autosave may follow again */
        ui_say("SAVED", 0);
        break;
    case -7:
        ui_warn("MEMORY FULL: NOT SAVED", 0);
        break;
    default:
        ui_warn("SAVE FAILED", 0);
        break;
    }
    ui.saved_t = plat_ms();
}

static void white_key(int w, int down)
{
    tpart_t *tp = cur_tp();
    int t = ui.trk, step = ui.page * 16 + w;
    if (ui.view != V_SEQ || step >= tp->len)
        return;
    if (ttype(t) == TT_DRUM && down) {
        if (ui.btn & (1u << B_ENV))
            sm_flip(tp->u.d.acc, step);
        else
            sm_flip(tp->u.d.hit[ui.snd], step);
        touch();
    } else if (notes(t)) {
        if (down) {
            bstep_t *s = &tp->u.b.step[step];
            ui.held_step = (int8_t)step;
            if (ui.btn & (1u << B_ENV)) {                 /* ENV held: the step's accent */
                s->flags ^= BS_ACCENT;
            } else if (!(ui.btn & (1u << B_LFO))) {
                s->flags = (uint8_t)((s->flags & ~BS_GATE_MASK) | (bstep_gate(s) == G_REST ? G_NOTE : G_REST));
                if (bstep_gate(s) != G_REST && !seq.playing)
                    engine_note_on(t, s->note, bstep_chord(s), 0, 0);
            }
            touch();
        } else if (ui.held_step == step) {
            ui.held_step = -1;
            if (!seq.playing)
                engine_note_off(t);
        }
    }
}

static void black_key(int b, int down)
{
    if (!down || b >= NTRK)
        return;
    if (ui.view == V_MIX) {
        seq.mute ^= (uint8_t)(1u << b);
        select_track(b);
        return;
    }
    if ((ui.view == V_SEQ || ui.view == V_EDIT) && ttype(ui.trk) == TT_DRUM) {
        ui.snd = (uint8_t)b;
        engine_drum(ui.trk, b, 0.8f);                   /* always heard, playing or not */
        if (ui.rec && seq.playing && ui.view == V_SEQ) {  /* REC while playing: the hit goes into the step */
            tpart_t *tp = cur_tp();
            int st = eng_step[ui.trk] % tp->len;
            sm_set(tp->u.d.hit[b], st);
            touch();
        }
        return;
    }
    select_track(b);
}

/* HOME held: the white keys cue patterns (OCT-/+ choose 1-16 or 17-32), the black keys mute tracks */
static void home_key(int k, int down)
{
    int w = key_white[k], b = key_black[k];
    if (!down)
        return;
    if (w >= 0) {
        int p = ui.pbank * 16 + w, all = (ui.btn & (1u << B_SEL)) != 0;
        char t[24] = "", n[4];
        if (all) {
            gseq_cue(&seq, p);                          /* HOME + SEL: every track */
            scat(t, "ALL: PATTERN ");
        } else {
            gseq_cue_track(&seq, ui.trk, p);            /* the selected track only */
            t[0] = 'T';
            t[1] = (char)('1' + ui.trk);
            t[2] = 0;
            scat(t, ": PATTERN ");
        }
        put_num(n, p + 1);
        scat(t, n);
        ui_say(t, seq.playing ? "AT THE NEXT BAR" : 0);
        ui.home_used = 1;
    } else if (b >= 0 && b < NTRK) {
        seq.mute ^= (uint8_t)(1u << b);
        ui.home_used = 1;
    }
}

/* the keyboard plays the selected track (HOME, EDIT; on SEQ with REC, a 303):
 *   DRUM  the black keys 1-8 are the kit's sounds, and the white keys 1-8 (and again 9-16)
 *   303   the keys from F, chromatic; OCT-/+ the octave; a key pressed while another is held slides
 * With REC on, what is played is written into the steps: while playing, into the step playing; a
 * 303 while stopped, one step after another */
static uint8_t rec_step, keys_down;
static void play_key(int k, int down)
{
    int t = ui.trk, w = key_white[k], b = key_black[k];
    tpart_t *tp = cur_tp();
    if (ttype(t) == TT_DRUM) {
        int snd = w >= 0 ? w % NDSND : b < NDSND ? b : -1;
        if (!down || snd < 0)
            return;
        ui.snd = (uint8_t)snd;
        engine_drum(t, snd, 0.8f);
        if (ui.rec && seq.playing) {
            sm_set(tp->u.d.hit[snd], eng_step[t] % tp->len);
            touch();
        }
        return;
    }
    if (!notes(t))
        return;
    if (!down) {
        if (keys_down)
            keys_down--;
        if (!keys_down)
            engine_note_off(t);
        return;
    }
    {
        int note = 41 + 12 * ui.oct + k;              /* F2 on the lowest key, an octave a step */
        if (keys_down && engine_chord_mode(&proj.sound, t))
            engine_note_add(t, note);                   /* a synth in CHORD: the keys held sound together */
        else
            engine_note_on(t, note, 0, 0, keys_down != 0);
        keys_down++;
        if (ui.rec) {
            int st = seq.playing ? eng_step[t] : rec_step;
            bstep_t *x = &tp->u.b.step[st % tp->len];
            x->note = (uint8_t)note;
            x->flags = (uint8_t)((x->flags & ~BS_GATE_MASK) | G_NOTE);
            if (!seq.playing)
                rec_step = (uint8_t)((st + 1) % tp->len);
            touch();
        }
    }
}

static void input(void)
{
    uint32_t b = plat_buttons(), k = plat_keys(), down = b & ~ui.btn, up = ui.btn & ~b;
    uint32_t kd = k & ~ui.keys, ku = ui.keys & ~k;
    knob_t kn[4];
    int i, d;
    ui.btn = b;
    ui.keys = k;
    if (down | up | kd | ku)
        ui.act_t = plat_ms();
    if ((b & ((1u << B_OCTDN) | (1u << B_OCTUP))) == ((1u << B_OCTDN) | (1u << B_OCTUP)))
        down &= ~((1u << B_OCTDN) | (1u << B_OCTUP));  /* both held: the update mode's countdown (main_fm1.c) */
    if (down & (1u << B_PLAY)) {
        if (seq.playing)
            gseq_stop(&seq);
        else
            gseq_start(&seq);
    }
    if (down & (1u << B_REC)) {
        ui.rec ^= 1u;
        rec_step = 0;
        keys_down = 0;
        ui_say(ui.rec ? "REC ON" : "REC OFF", !ui.rec ? 0 : notes(ui.trk) ? "THE KEYS RECORD NOTES" :
               ttype(ui.trk) == TT_DRUM ? "BLACK KEYS RECORD HITS" : 0);
    }
    if (down & (1u << B_HOME)) open_view(V_HOME);
    if (down & (1u << B_SEQ)) open_view(V_SEQ);
    if (down & (1u << B_EDIT)) open_view(V_EDIT);
    if (down & (1u << B_FX)) open_view(V_FX);
    if (down & (1u << B_LFO)) open_view(V_MIX);
    if (down & (1u << B_GLO))
        ui.glo_used = 0;
    if ((up & (1u << B_GLO)) && !ui.glo_used)      /* GLO opens on release: held with SELECT, it set the tempo */
        open_view(V_GLO);
    if (down & (1u << B_ARP)) {                    /* the selected note track's arpeggiator */
        if (!notes(ui.trk)) {
            ui_say("ARPEGGIATOR", "ON 303 AND VA TRACKS");
        } else {
            ui.spage = (uint8_t)(ui.view == V_SEQ ? !ui.spage : 1);
            ui.view = V_SEQ;
            ui.held_step = -1;
        }
    }
    if (down & (1u << B_SAVE))
        save_project();
    if (down & (1u << B_SEL)) {
        if (ui.view == V_GLO && ui.pend_type != ttype(ui.trk)) {
            int keep = notes(ui.trk) && tt_notes(ui.pend_type);   /* 303 <-> VA: the same steps */
            project_set_type(ui.trk, ui.pend_type);
            ui.page = 0;
            touch();
            ui_say("TYPE CHANGED", keep ? "THE STEPS STAY" : "ITS STEPS ARE CLEARED");
        }
    }
    if (down & ((1u << B_OCTDN) | (1u << B_OCTUP))) {
        int dir = (down & (1u << B_OCTUP)) ? 1 : -1;
        if (b & (1u << B_HOME)) {
            ui.pbank = (uint8_t)(dir > 0);
            ui.home_used = 1;
        } else if (ui.view == V_HOME || ui.view == V_EDIT || (ui.rec && notes(ui.trk))) {
            int o = ui.oct + dir;
            ui.oct = (int8_t)(o < -3 ? -3 : o > 3 ? 3 : o);
        } else if (ui.view == V_SEQ) {
            int pages = (cur_tp()->len + 15) / 16, p = ui.page + dir;
            ui.page = (uint8_t)(p < 0 ? 0 : p >= pages ? pages - 1 : p);
        }
    }
    for (i = 0; i < NKEYS; i++) {
        uint32_t m = 1u << i;
        if (!((kd | ku) & m))
            continue;
        if (b & (1u << B_HOME))
            home_key(i, (kd & m) != 0);
        else if (ui.view == V_HOME || ui.view == V_EDIT || (ui.view == V_SEQ && ui.rec && notes(ui.trk)))
            play_key(i, (kd & m) != 0);
        else if (key_white[i] >= 0)
            white_key(key_white[i], (kd & m) != 0);
        else
            black_key(key_black[i], (kd & m) != 0);
    }
    /* encoders */
    d = plat_enc(EN_ALGO);
    if (d) {
        int t = (int)ui.trk + d;
        select_track(t < 0 ? 0 : t >= NTRK ? NTRK - 1 : t);
    }
    d = plat_enc(EN_SELECT);
    if (d && (b & (1u << B_GLO))) {                   /* GLO + SELECT: the tempo, on every screen */
        knob_t kt = {KR_TEMPO, 0, 0, 0};
        knob_turn(&kt, d);
        ui.glo_used = 1;
        d = 0;
    }
    if (d && ui.view == V_HOME)
        ui_say("BPM LOCKED", "GLO + SELECT: TEMPO");
    else if (d) {
        int s = d > 0 ? 1 : -1;
        if (ui.view == V_EDIT) {
            int n = ttype(ui.trk) == TT_DRUM ? GP_N : ttype(ui.trk) >= TT_VA ? engine_nparams(T_SYN, ui.trk) :
                    engine_nparams(T_303, ui.trk);
            int pages = (n + 3) / 4;
            int p = ui.epage + s;
            ui.epage = (uint8_t)(p < 0 ? 0 : p >= pages ? pages - 1 : p);
        } else if (ui.view == V_FX) {
            int p = ui.fxpage + s, n = fxpage_count();
            ui.fxpage = (uint8_t)(p < 0 ? 0 : p >= n ? n - 1 : p);
        } else if (ui.view == V_GLO) {
            ui.glopage ^= 1u;
        } else if (ui.view == V_SEQ && notes(ui.trk)) {
            ui.spage = (uint8_t)(s > 0);
        }
    }
    d = plat_enc(EN_PRESET);                          /* PRESETS: the track's kit or preset, on every screen */
    if (d && (b & (1u << B_SEL))) {                   /* SEL + PRESETS: the list, every kind or one */
        int l = (proj.set.list + d) % (NCAT + 1);
        proj.set.list = (uint8_t)(l < 0 ? l + NCAT + 1 : l);
        ui_say("LIST", gs_cat_name((int)proj.set.list - 1));
        touch();
        d = 0;
    }
    if (d && engine_npresets(ttype(ui.trk))) {
        char t[24] = "", nb[4];
        int k, pos, n;
        if (ttype(ui.trk) == TT_DRUM) {
            n = gd_nkits;
            k = (((int)proj.sound.kit[ui.trk] + d) % n + n) % n;
            engine_track_preset(&proj.sound, ui.trk, k);   /* loads while playing */
            pos = k;
            scat(t, "KIT ");
        } else {                                      /* a sound from the list; another engine switches it */
            int cat = (int)proj.set.list - 1;
            k = gs_step(proj.sound.kit[ui.trk], d, cat);
            project_load_sound(ui.trk, k);
            pos = gs_pos(k, cat, &n);
            scat(t, gs_cat_name(cat >= 0 ? cat : gs_cat(k)));
            scat(t, " ");
        }
        put_num(nb, pos + 1);
        scat(t, nb);
        scat(t, "/");
        put_num(nb, n);
        scat(t, nb);
        if (ttype(ui.trk) != TT_DRUM) {
            scat(t, " ");
            scat(t, gs_engine_name(ttype(ui.trk)));
        }
        ui_say(t, engine_preset_name(ttype(ui.trk), k));
        ui.epage = 0;
        touch();
    }
    knobs_of(kn);
    for (i = 0; i < 4; i++)
        knob_turn(&kn[i], plat_enc(EN_K1 + i));
}

/* ------------------------------------------------------------ drawing --- */
#define TOP_H 24
#define MAIN_Y 24
#define MAIN_H 144
#define BOT_Y 168
#define BOT_H 72

/* bar.beat (as Skiff): where the selected track is in its pattern, in bars of 4 beats at its rate; a
 * 16-step pattern of 1/16 runs 1.1 .. 1.4, a 32-step one 1.1 .. 2.4, then again. 1.1 when stopped */
static int bar_key(void)
{
    static const uint8_t SPB[NRATES] = {4, 6, 8, 3, 2};   /* steps a beat: 1/16, 1/16T, 1/32, 1/8T, 1/8 */
    int spb, st;
    if (!seq.playing)
        return 0;
    spb = SPB[cur_tp()->rate % NRATES];
    st = eng_step[ui.trk] % NSTEPS;
    return st / spb;                                    /* beats from the pattern's start */
}
static void bar_beat(char *b)
{
    int k = bar_key();
    char n[4];
    b[0] = 0;
    put_num(b, k / 4 + 1);
    scat(b, ".");
    put_num(n, k % 4 + 1);
    scat(b, n);
}

static void draw_top(void)
{
    char b[40], n[8];
    int x;
    cv_begin(240, TOP_H, C_BLACK);
    if (seq.playing)                                   /* the play state: a triangle, or REC's red */
        for (x = 0; x < 8; x++)
            cv_rect(4 + x, 6 + x / 2, 1, 12 - x, ui.rec ? RGB(255, 60, 40) : RGB(80, 220, 90));
    else
        cv_rect(4, 7, 9, 9, ui.rec ? RGB(160, 40, 30) : C_DIM);
    bar_beat(b);
    x = cv_text(18, 4, &FONT_B, b, seq.playing ? C_WHITE : C_GRAY) + 8;
    put_num(b, (int)(gseq_tempo(&seq) + 0.5f));
    scat(b, " BPM");
    x = cv_text(x, 4, &FONT_S, b, C_AMB) + 8;
    if (ui.say_t && plat_ms() - ui.say_t < 1500u) {   /* a message takes the title's place */
        cv_text(x, 4, &FONT_B, ui.say_a, ui.say_warn ? RGB(255, 90, 60) : C_WHITE);
    } else {
        if (ui.oct) {
            b[0] = 0;
            scat(b, "OCT ");
            if (ui.oct > 0)
                scat(b, "+");
            put_num(b + strlen_(b), ui.oct);
            x = cv_text(x, 4, &FONT_S, b, C_HI) + 8;
        }
        b[0] = 'T';
        b[1] = (char)('1' + ui.trk);
        b[2] = ' ';
        b[3] = 'P';
        put_2(b + 4, seq.tpat[ui.trk] + 1);
        if (seq.tcue[ui.trk] < NPAT) {
            scat(b, ">");
            put_2(n, seq.tcue[ui.trk] + 1);
            scat(b, n);
        }
        cv_text(236 - text_w(&FONT_S, b), 4, &FONT_S, b, seq.tcue[ui.trk] < NPAT ? C_WHITE : C_HI);
    }
    if (ui.dirty)
        cv_rect(236, 0, 4, 3, C_GRAY);
    cv_rect(0, TOP_H - 1, 240, 1, C_LINE);
    cv_blit(0, 0);
}

/* the step row of track t at y, 16 cells from the current page, h px tall */
static void draw_steps(int t, int x0, int w, int y, int h, int page, int sound, int hi)
{
    const tpart_t *tp = tp_of(t);
    int i, play = seq.playing ? eng_step[t] : -1;
    for (i = 0; i < 16; i++) {
        int s = page * 16 + i, on = 0, acc = 0;
        uint16_t c;
        if (s >= tp->len) {
            cv_rect(x0 + i * w + 1, y + h / 2, w - 2, 1, C_LINE);
            continue;
        }
        if (ttype(t) == TT_DRUM) {
            if (sound < 0) {
                int v;
                for (v = 0; v < NDSND; v++)
                    on |= sm_get(tp->u.d.hit[v], s);
            } else
                on = sm_get(tp->u.d.hit[sound], s);
            acc = sm_get(tp->u.d.acc, s);
        } else if (notes(t)) {
            on = bstep_gate(&tp->u.b.step[s]) != G_REST;
            acc = (tp->u.b.step[s].flags & BS_ACCENT) != 0;
        }
        c = on ? (hi ? C_HI : C_AMB) : C_LINE;
        if (s == play)
            c = on ? C_WHITE : C_GRAY;
        cv_rect(x0 + i * w + 1, y, w - 2, h, c);
        if (on && acc)
            cv_rect(x0 + i * w + 2, y + 1, w - 4, 2, C_BLACK);
        if (i % 4 == 0)
            cv_rect(x0 + i * w, y - 1, 1, h + 2, C_DIM);
    }
}

static void draw_home(void)
{
    int t;
    if (ui.btn & (1u << B_HOME)) {                    /* HOME held: each track's pattern and cue */
        for (t = 0; t < NTRK; t++) {
            int y = 2 + t * 15, muted = (seq.mute >> t) & 1;
            char b[24] = {(char)('1' + t), ' ', 0}, n[4];
            uint16_t c = t == ui.trk ? C_WHITE : muted ? C_DIM : C_GRAY;
            scat(b, TYPE_N[ttype(t) % NTT]);
            cv_text(4, y, &FONT_T, b, c);
            b[0] = 'P';
            put_2(b + 1, seq.tpat[t] + 1);
            if (seq.tcue[t] < NPAT) {
                scat(b, " > P");
                put_2(n, seq.tcue[t] + 1);
                scat(b, n);
            }
            cv_text(60, y, &FONT_T, b, seq.tcue[t] < NPAT ? C_WHITE : c);
            if (muted)
                cv_text(180, y, &FONT_T, "MUTE", RGB(255, 90, 60));
        }
        return;
    }
    for (t = 0; t < NTRK; t++) {                       /* a lane a track: its number and name, its steps */
        int y = 2 + t * 17, muted = (seq.mute >> t) & 1, len = tp_of(t)->len;
        char b[20] = {(char)('1' + t), 0};
        uint16_t c = t == ui.trk ? C_WHITE : muted ? C_DIM : C_GRAY;
        if (t == ui.trk)
            cv_rect(0, y - 1, 2, 15, C_HI);                 /* the selected track: a bar at its lane's edge */
        cv_text(3, y, &FONT_T, b, c);
        b[0] = 0;
        scat(b, engine_preset_name(ttype(t), proj.sound.kit[t]));
        cv_text(14, y, &FONT_T, b, muted ? RGB(255, 90, 60) : ttype(t) == TT_OFF ? C_DIM : c);
        if (muted)
            cv_text(14 + text_w(&FONT_T, b) + 4, y, &FONT_T, "M", RGB(255, 90, 60));
        if (ttype(t) != TT_OFF)                         /* the page with the playhead, 9 px a step */
            draw_steps(t, 94, 9, y + 2, 10, seq.playing && eng_step[t] < len ? eng_step[t] / 16 : 0, -1, !muted);
    }
}

/* a sound's name in 5 characters for the step grid: dots dropped; with a space, its first word's
 * first three letters and the last word's first ("CONGA L" -> "CON L") */
static void short_name(char *o, const char *nm)
{
    const char *sp = nm;
    int i = 0;
    while (*sp && *sp != ' ')
        sp++;
    if (*sp == ' ') {
        while (i < 3 && nm[i] && nm[i] != ' ')
            o[i] = nm[i], i++;
        o[i++] = ' ';
        o[i++] = sp[1];
    } else {
        for (; *nm && i < 5; nm++)
            if (*nm != '.')
                o[i++] = *nm;
    }
    o[i] = 0;
}

static void draw_seq(void)
{
    int t = ui.trk, v;
    const tpart_t *tp = cur_tp();
    char b[24];
    if (ttype(t) == TT_DRUM) {
        for (v = 0; v < NDSND; v++) {
            int y = 2 + v * 16;
            uint16_t c = v == ui.snd ? C_WHITE : C_GRAY;
            char s[6];
            short_name(s, gd_kit_snd_names[proj.sound.kit[t] % gd_nkits][v]);
            cv_text(2, y, &FONT_T, s, c);
            draw_steps(t, 32, 13, y + 2, 11, ui.page, v, v == ui.snd);
        }
        b[0] = 0;
        scat(b, gd_kit_names[proj.sound.kit[t] % gd_nkits]);
        cv_text(2, 130, &FONT_T, b, C_AMB);
    } else if (notes(t)) {
        int i;
        draw_steps(t, 32, 13, 4, 12, ui.page, -1, 1);
        for (i = 0; i < 16; i++) {                       /* each step's note as a bar in a 2-octave range */
            int s = ui.page * 16 + i, n;
            const bstep_t *st = &tp->u.b.step[s];
            if (s >= tp->len || bstep_gate(st) == G_REST)
                continue;
            n = (int)st->note - 24;
            n = n < 0 ? 0 : n > 48 ? 48 : n;
            cv_rect(32 + i * 13 + 2, 120 - n * 2, 9, 3, s == ui.held_step ? C_WHITE : C_HI);
            if (st->flags & BS_SLIDE)
                cv_rect(32 + i * 13 + 11, 121 - n * 2, 4, 1, C_AMB);
            if (bstep_gate(st) == G_TIE)
                cv_rect(32 + i * 13, 121 - n * 2, 3, 1, C_HI);
            if (bstep_chord(st))                        /* a chord: a mark over its note */
                cv_rect(32 + i * 13 + 4, 116 - n * 2, 5, 2, C_AMB);
        }
        if (ui.held_step >= 0) {
            const bstep_t *hs = &tp->u.b.step[ui.held_step];
            note_name(b, hs->note);
            if (bstep_chord(hs)) {
                scat(b, " ");
                scat(b, gp_chords[bstep_chord(hs)].name);
            }
            cv_text(2, 24, &FONT_S, b, C_WHITE);
        }
        if (tp->u.b.arp % NARPS) {                      /* the arpeggiator, when on */
            char n[4];
            b[0] = 0;
            scat(b, "ARP ");
            scat(b, ARP_N[tp->u.b.arp % NARPS]);
            scat(b, " ");
            put_num(n, tp->u.b.arp_div % 4 + 1);
            scat(b, n);
            scat(b, "/ST ");
            put_num(n, tp->u.b.arp_oct % 3 + 1);
            scat(b, n);
            scat(b, " OCT");
            cv_text(2, 130, &FONT_T, b, ui.spage ? C_WHITE : C_AMB);
        } else if (ui.spage) {
            cv_text(2, 130, &FONT_T, "ARP OFF", C_WHITE);
        }
    } else {
        cv_text(20, 60, &FONT_S, "TRACK OFF: GLO SETS ITS TYPE", C_GRAY);
    }
    b[0] = 0;
    scat(b, "STEPS ");
    put_num(b + 6, ui.page * 16 + 1);
    scat(b, "-");
    {
        char n[4];
        int e = ui.page * 16 + 16;
        put_num(n, e > tp->len ? tp->len : e);
        scat(b, n);
    }
    cv_text(150, 130, &FONT_T, b, C_GRAY);
}

static void draw_meters(void)
{
    int t;
    for (t = 0; t < NTRK; t++) {
        int x = 6 + t * 29, h = (int)eng_peak[t] * 100 / 32767, muted = (seq.mute >> t) & 1;
        char b[2] = {(char)('1' + t), 0};
        int lv = proj.sound.mix[t][MX_LEVEL];
        cv_rect(x, 8, 18, 104, C_LINE);
        if (h > 0)
            cv_rect(x + 2, 110 - h, 14, h, muted ? C_DIM : C_HI);
        cv_rect(x, 110 - lv * 100 / 127, 18, 2, C_WHITE);
        cv_text(x + 5, 118, &FONT_T, b, t == ui.trk ? C_WHITE : muted ? C_DIM : C_GRAY);
        if (eng_peak[t] > 400)
            eng_peak[t] = (uint16_t)(eng_peak[t] - eng_peak[t] / 8);
        else
            eng_peak[t] = 0;
    }
}

static void draw_glo(void)
{
    char b[32];
    if (!ui.glopage) {
        cv_text(4, 6, &FONT_S, "TRACK SETTINGS", C_GRAY);
        cv_text(4, 34, &FONT_S, "TYPE: TURN KNOB 1,", C_AMB);
        cv_text(4, 52, &FONT_S, "THEN SEL TO APPLY.", C_AMB);
        cv_text(4, 70, &FONT_S, "A NEW TYPE CLEARS THE", C_DIM);
        cv_text(4, 88, &FONT_S, "TRACK'S STEPS.", C_DIM);
    } else {
        cv_text(4, 6, &FONT_S, "GRUSELCORE " GC_VERSION, C_HI);
        b[0] = 0;
        scat(b, "PATTERN MEMORY ");
        put_num(b + 15, project_mem_pct());
        scat(b, "%");
        cv_text(4, 34, &FONT_S, b, C_AMB);
        b[0] = 0;
        scat(b, "CPU ");
        put_num(b + 4, (int)plat_cpu_pct());
        scat(b, "%");
        if (engine_guard_active())
            scat(b, " (LIGHT)");
        cv_text(4, 52, &FONT_S, b, C_AMB);
        cv_text(4, 80, &FONT_S, "RESCUE: OCT- AT POWER-ON", C_DIM);
        cv_text(4, 98, &FONT_S, "UPDATE: OCT- + OCT+ 5 S", C_DIM);
    }
}

static void draw_edit(void)
{
    int t = ui.trk;
    char b[32];
    if (ttype(t) == TT_DRUM) {
        const char *nm = gd_kit_snd_names[proj.sound.kit[t] % gd_nkits][ui.snd];
        cv_text(4, 6, &FONT_B, nm, C_WHITE);
        cv_text(4, 30, &FONT_S, gd_kit_names[proj.sound.kit[t] % gd_nkits], C_AMB);
        cv_text(4, 100, &FONT_T, "BLACK KEYS: SOUND   PRESETS: KIT", C_DIM);
    } else if (ttype(t) == TT_303) {
        cv_text(4, 6, &FONT_B, engine_preset_name(TT_303, proj.sound.kit[t]), C_WHITE);
        cv_text(4, 30, &FONT_S, "303", C_AMB);
        cv_text(4, 100, &FONT_T, "SELECT: PAGE   PRESETS: PRESET", C_DIM);
    } else if (ttype(t) >= TT_VA) {
        static const char *const PV[] = {"OSCILLATORS", "MIX", "FILTER", "FILTER ENVELOPE", "AMP ENVELOPE",
                                         "VOICE", "LFO"};
        static const char *const PF[] = {"ALGORITHM", "OPERATOR 1", "OPERATOR 2", "OPERATOR 3", "OPERATOR 4",
                                         "ENVELOPE", "LFO"};
        static const char *const PH[] = {"MODEL", "STRIKE", "DROP", "VOICE"};
        const char *pg = ttype(t) == TT_VA ? (ui.epage < 7 ? PV[ui.epage] : "") :
                         ttype(t) == TT_FM ? (ui.epage < 7 ? PF[ui.epage] : "") : (ui.epage < 4 ? PH[ui.epage] : "");
        cv_text(4, 6, &FONT_B, engine_preset_name(ttype(t), proj.sound.kit[t]), C_WHITE);
        b[0] = 0;
        scat(b, gs_engine_name(ttype(t)));
        scat(b, ": ");
        scat(b, pg);
        cv_text(4, 30, &FONT_S, b, C_AMB);
        cv_text(4, 100, &FONT_T, "SELECT: PAGE   PRESETS: SOUND", C_DIM);
    } else {
        cv_text(20, 60, &FONT_S, "TRACK OFF: GLO SETS ITS TYPE", C_GRAY);
        return;
    }
    b[0] = 0;
    scat(b, "PAGE ");
    put_num(b + 5, ui.epage + 1);
    cv_text(4, 120, &FONT_T, b, C_GRAY);
}

static void draw_fx(void)
{
    char b[32];
    cv_text(4, 6, &FONT_B, ui.fxpage < 2 ? "TRACK FX" : "SHARED FX", C_WHITE);
    cv_text(4, 30, &FONT_S, ui.fxpage == 0 ? "FILTER, RESO, DRIVE, LEVEL" : ui.fxpage == 1 ? "PAN, REVERB, DELAY" :
                            "REVERB, DELAY, MASTER", C_AMB);
    b[0] = 0;
    scat(b, "PAGE ");
    put_num(b + 5, ui.fxpage + 1);
    cv_text(4, 120, &FONT_T, b, C_GRAY);
}

static void draw_main(void)
{
    cv_begin(240, MAIN_H, C_BLACK);
    switch (ui.view) {
    case V_HOME: draw_home(); break;
    case V_SEQ: draw_seq(); break;
    case V_EDIT: draw_edit(); break;
    case V_FX: draw_fx(); break;
    case V_MIX: draw_meters(); break;
    case V_GLO: draw_glo(); break;
    default: break;
    }
    if (ui.btn & (1u << B_HOME)) {                    /* HOME held: what the keys do now */
        cv_rect(0, MAIN_H - 20, 240, 20, C_LINE);
        cv_text(4, MAIN_H - 18, &FONT_S, (ui.btn & (1u << B_SEL)) ? (ui.pbank ? "WHITE: ALL TRACKS 17-32" : "WHITE: ALL TRACKS 1-16")
                : ui.pbank ? "WHITE: PAT 17-32  BLACK: MUTE" : "WHITE: PAT 1-16  BLACK: MUTE", C_WHITE);
    } else if (ui.say_t && plat_ms() - ui.say_t < 1500u && ui.say_b[0]) {   /* a message's second part */
        cv_rect(0, MAIN_H - 20, 240, 20, C_LINE);
        cv_text(4, MAIN_H - 18, &FONT_S, ui.say_b, C_WHITE);
    }
    cv_blit(0, MAIN_Y);
}

static void draw_bottom(void)
{
    knob_t kn[4];
    int i;
    knobs_of(kn);
    cv_begin(240, BOT_H, C_BLACK);
    cv_rect(0, 0, 240, 1, C_LINE);
    for (i = 0; i < 4; i++) {
        char name[16], val[16];
        int x = i * 60;
        knob_label(&kn[i], name, val);
        if (!name[0])
            continue;
        cv_text(x + 30 - text_w(&FONT_T, name) / 2, 8, &FONT_T, name, C_GRAY);
        cv_text(x + 30 - text_w(&FONT_S, val) / 2, 30, &FONT_S, val, C_HI);
        if (kn[i].role == KR_POT) {
            const x0x_param_t *p = engine_param(kn[i].target, kn[i].voice, kn[i].index);
            int v = pot_get(kn[i].target, kn[i].voice, kn[i].index);
            if (p && p->max == 127) {
                cv_rect(x + 8, 56, 44, 3, C_LINE);
                cv_rect(x + 8, 56, 44 * v / 127, 3, C_AMB);
            }
        }
    }
    cv_blit(0, BOT_Y);
}

/* a cheap fingerprint of what the screen shows: redraw only when it changes (or while playing) */
static uint32_t screen_hash(void)
{
    uint32_t h = 2166136261u;
    const uint8_t *p;
    unsigned i;
#define MIX(x) (h = (h ^ (uint32_t)(x)) * 16777619u)
    MIX(ui.view); MIX(ui.trk); MIX(ui.snd); MIX(ui.page); MIX(ui.epage); MIX(ui.fxpage); MIX(ui.glopage); MIX(ui.spage);
    MIX(ui.held_step); MIX(ui.pend_type); MIX(ui.dirty); MIX(ui.rec); MIX(seq.tpat[ui.trk]); MIX(seq.tcue[ui.trk]); MIX(seq.swing);
    for (i = 0; i < NTRK; i++)
        MIX(seq.tpat[i] | seq.tcue[i] << 8);
   
    MIX(seq.playing); MIX(seq.mute); MIX((int)(seq.bpm * 10.0f)); MIX(seq.ch[ui.trk]); MIX(seq.send_clock);
    MIX(seq.send_notes); MIX(ui.say_t && plat_ms() - ui.say_t < 1500u); MIX(ui.btn); MIX(ui.pbank); MIX(ui.oct);
    p = (const uint8_t *)cur_tp();
    for (i = 0; i < sizeof(tpart_t); i++)
        MIX(p[i]);
    p = (const uint8_t *)&proj.sound;
    for (i = 0; i < sizeof proj.sound; i += 4)
        MIX(p[i] | p[i + 1] << 8 | p[i + 2] << 16 | (uint32_t)p[i + 3] << 24);
#undef MIX
    return h;
}

static void leds(void)
{
    uint32_t lb = 0, lk = 0, dk = 0;
    int i;
    static const uint8_t VB[NVIEWS] = {B_HOME, B_SEQ, B_EDIT, B_FX, B_LFO, B_GLO};
    lb |= 1u << VB[ui.view];
    if (seq.playing)
        lb |= 1u << B_PLAY;
    if (ui.rec)
        lb |= 1u << B_REC;
    for (i = 0; i < NKEYS; i++) {
        int w = key_white[i], b = key_black[i];
        if (w >= 0) {
            if (ui.view == V_HOME && (ui.btn & (1u << B_HOME))) {
                int p = ui.pbank * 16 + w;
                if (p == seq.tpat[ui.trk])
                    lk |= 1u << i;
                else if (p == seq.tcue[ui.trk] && (plat_ms() / 200u) & 1u)
                    lk |= 1u << i;
            } else if (ui.view == V_SEQ) {
                const tpart_t *tp = cur_tp();
                int s = ui.page * 16 + w, on = 0;
                if (s < tp->len) {
                    if (ttype(ui.trk) == TT_DRUM)
                        on = sm_get(tp->u.d.hit[ui.snd], s);
                    else if (notes(ui.trk))
                        on = bstep_gate(&tp->u.b.step[s]) != G_REST;
                    if (seq.playing && eng_step[ui.trk] == s)
                        lk |= 1u << i;
                    else if (on)
                        dk |= 1u << i;
                }
            }
        } else if (b >= 0 && b < NTRK && ui.view != V_HOME && ui.view != V_EDIT) {
            if (ui.view == V_MIX) {
                if (!((seq.mute >> b) & 1))
                    lk |= 1u << i;
            } else if (ui.view == V_SEQ && ttype(ui.trk) == TT_DRUM) {
                if (b == ui.snd)
                    lk |= 1u << i;                         /* the sound whose steps the white keys set */
                else if (eng_hit[ui.trk][b] > 40)
                    dk |= 1u << i;
            }
        }
        if (ui.view == V_HOME && (ui.btn & (1u << B_HOME)) && b >= 0 && b < NTRK && !((seq.mute >> b) & 1))
            lk |= 1u << i;                                 /* HOME held: the tracks playing (unmuted) */
    }
    if ((ui.view == V_HOME && !(ui.btn & (1u << B_HOME))) || ui.view == V_EDIT)
        lk |= ui.keys;                                    /* playing the keyboard: the keys held */
    for (i = 0; i < NTRK; i++)                            /* the hit lights fade */
        for (int v = 0; v < NDSND; v++)
            if (eng_hit[i][v])
                eng_hit[i][v] = (uint8_t)(eng_hit[i][v] > 24 ? eng_hit[i][v] - 24 : 0);
    plat_glow(proj.set.keyled == 1);
    plat_keys_dim(dk);
    plat_play_red(ui.rec);
    plat_leds(proj.set.keyled ? lb : 0, lk);
}

/* ---------------------------------------------------------- autosave --- */
#define AUTOSAVE_QUIET 4000u
#define AUTOSAVE_GAP 20000u
static void autosave(void)
{
    uint32_t now = plat_ms();
    if (save_hold)
        return;
    if (ui.save_wait && !seq.playing && !seq.req_stop) {
        save_project();
        return;
    }
    if (ui_autosave_block || !ui.dirty || proj.set.autosave_off || seq.playing || seq.req_stop ||
        now - ui.act_t < AUTOSAVE_QUIET || (ui.saved_t && now - ui.saved_t < AUTOSAVE_GAP))
        return;
    ui.saved_t = now;
    if (project_save() == 0) {
        ui.dirty = 0;
        ui_say("AUTOSAVED", 0);
    }
}

/* ---------------------------------------------------------- the loop --- */
void ui_init(void)
{
    keys_init();
    ui.trk = 0;
    ui.held_step = -1;
    ui.pend_type = (uint8_t)ttype(0);
    ui.view = V_HOME;                                     /* the start screen */
    ui.redraw = 1;
    ui.btn = plat_buttons();                              /* held at power-on: not presses */
    ui.keys = plat_keys();
    lcd_fill(0, 0, 240, 240, C_BLACK);
}

void ui_input_only(void) { input(); }

void ui_frame(void)
{
    uint32_t now = plat_ms(), h;
    input();
    autosave();
    if (now - ui.frame_t < 33u)
        return;
    ui.frame_t = now;
    leds();
    h = screen_hash();
    if (h != ui.last_hash || ui.redraw) {                 /* something changed: the whole screen */
        ui.last_hash = h;
        ui.redraw = 0;
        ui.last_bar = bar_key();
        draw_top();
        draw_main();
        draw_bottom();
    } else if (seq.playing || ui.view == V_MIX) {         /* only the playheads and meters move */
        if (bar_key() != ui.last_bar) {                   /* and bar.beat */
            ui.last_bar = bar_key();
            draw_top();
        }
        draw_main();
    }
}

int ui_dirty(void) { return ui.dirty; }
void ui_redraw(void) { ui.redraw = 1; }
void ui_hold_saves(int on) { save_hold = (uint8_t)(on != 0); }
void ui_flush(void)
{
    if (ui.dirty && !seq.playing && project_save() == 0)
        ui.dirty = 0;
}
void app_restored(void)
{
    gseq_stop(&seq);
    if (project_load() != 0)
        project_defaults();
    engine_apply_sound(&proj.sound);
    seq.bpm = (float)proj.set.bpm_x10 / 10.0f;
    project_apply_io();
    project_flash_changed();
    ui.dirty = 0;
    ui.redraw = 1;
    ui_say("RESTORED", 0);
}
