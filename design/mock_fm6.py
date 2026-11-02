#!/usr/bin/env python3
"""FM6 LAB mockups: every value of an FM6 patch on the unit, and a sound built from the bare sine (plan 2026-10-13).
Two FM6-only EDIT pages after EDIT 2, drawn in BLOCKS (SKIFF) on track 1:
  OPERATOR  PRESETS picks OP1..OP6; SELECT moves the four knobs: TONE, ENV 1, ENV 2, KEYS, MORE
  ALL OPS   ALGO, PITCH 1, PITCH 2, LFO, DEPTH
The centrepiece is after an idea in a video by Floyd Steinberg (drawn our own way): the sound over time is the carriers'
envelope, each moment shaded cool -> hot by how hard the modulators drive them (a sine is cold, FM's bite hot), every
operator's envelope behind it. The curves are the engine's: msfa's envelope, pitch envelope and LFO as fm6_core.c runs
them (a Python port below), the patches tools/gen_fm6_patches.py's. Three directions:
  A  HEAT          operator tabs + the brightness envelope, full height; the ramp cool blue -> REC red
  B  HEAT + LENS   the same, shorter, over a strip that explains the window: the ratios on a ruler, the stages
                   numbered under their time, the keyboard
  C  TRACK HEAT    A's layout; the ramp is the track's colour, dark -> full -> white-hot
Starts from the firmware's renders (tests/ui_render.c, SKIFF: P6_RENDERS); FM6_GEN: build/gen (the LFO table).
  P6_RENDERS=~/skiff-fm6-ui/build/ui_new/ppm FM6_GEN=~/skiff-fm6-ui/build/gen python3 mock_fm6.py
Writes out/FM6<dir>_<screen>.png (1x, x2, x3) and mockups/fm6_sheet.png.
"""
import math
import os
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import mock
import mock_u3 as u3
from mock import OUT, W, H, mix, HERE

sys.path.insert(0, str(HERE.parent / "tools"))
import gen_fm6_patches as G                                # noqa: E402

GEN = Path(os.path.expanduser(os.environ.get("FM6_GEN", str(HERE.parent / "build" / "gen"))))

# ---------------------------------------------------------------- the engine (fm6_core.c), as it runs
FS, N = 44100, 32
BPS = FS / N                                             # envelope steps a second
R1, L1, BP, LD, RD, LC, RC, RS, AMS, KVS, OL, MODE, FC, FF, DET = 0, 4, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
PR1, PL1 = 126, 130
ALG, FB, OKS, LFS, LFD, LPMD, LAMD, LKS, LFW, LPMS, TRNSP = range(134, 145)
LEVELLUT = [0, 5, 9, 13, 17, 20, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 42, 43, 45, 46]
STATICS = [1764000, 1764000, 1411200, 1411200, 1190700, 1014300, 992250, 882000, 705600, 705600, 584325, 507150,
           502740, 441000, 418950, 352800, 308700, 286650, 253575, 220500, 220500, 176400, 145530, 145530, 125685,
           110250, 110250, 88200, 88200, 74970, 61740, 61740, 55125, 48510, 44100, 37485, 31311, 30870, 27562, 27562,
           22050, 18522, 17640, 15435, 14112, 13230, 11025, 9261, 9261, 7717, 6615, 6615, 5512, 5512, 4410, 3969, 3969,
           3439, 2866, 2690, 2249, 1984, 1896, 1808, 1411, 1367, 1234, 1146, 926, 837, 837, 705, 573, 573, 529, 441, 441]
PENV_RATE = [1, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 16, 16, 17, 18,
             18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 33, 34, 36, 37, 38, 39, 41, 42, 44, 46, 47, 49, 51, 53,
             54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 79, 82, 85, 88, 91, 94, 98, 102, 106, 110, 115, 120, 125,
             130, 135, 141, 147, 153, 159, 165, 171, 178, 185, 193, 202, 211, 232, 243, 254, 255]
PENV_TAB = [-128, -116, -104, -95, -85, -76, -68, -61, -56, -52, -49, -46, -43, -41, -39, -37, -35, -33, -32, -31, -30,
            -29, -28, -27, -26, -25, -24, -23, -22, -21, -20, -19, -18, -17, -16, -15, -14, -13, -12, -11, -10, -9, -8,
            -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
            23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 38, 40, 43, 46, 49, 53, 58, 65, 73, 82, 92, 103, 115,
            127]
PENV_UNIT, LFO_UNIT = 572, 18279
VELDATA = [0, 70, 86, 97, 106, 114, 121, 126, 132, 138, 142, 148, 152, 156, 160, 163, 166, 170, 173, 174, 178, 181, 184,
           186, 189, 190, 194, 196, 198, 200, 202, 205, 206, 209, 211, 214, 216, 218, 220, 222, 224, 225, 227, 229, 230,
           232, 233, 235, 237, 238, 240, 241, 242, 243, 244, 246, 246, 248, 249, 250, 251, 252, 253, 254]
EXPSCALE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 16, 19, 23, 27, 33, 39, 47, 56, 66, 80, 94, 110, 126, 142, 158, 174,
            190, 206, 222, 238, 250]
PMS = [0, 10, 20, 33, 55, 92, 153, 255]
ALGS = [[0xc1, 0x11, 0x11, 0x14, 0x01, 0x14], [0x01, 0x11, 0x11, 0x14, 0xc1, 0x14], [0xc1, 0x11, 0x14, 0x01, 0x11, 0x14],
        [0xc1, 0x11, 0x94, 0x01, 0x11, 0x14], [0xc1, 0x14, 0x01, 0x14, 0x01, 0x14], [0xc1, 0x94, 0x01, 0x14, 0x01, 0x14],
        [0xc1, 0x11, 0x05, 0x14, 0x01, 0x14], [0x01, 0x11, 0xc5, 0x14, 0x01, 0x14], [0x01, 0x11, 0x05, 0x14, 0xc1, 0x14],
        [0x01, 0x05, 0x14, 0xc1, 0x11, 0x14], [0xc1, 0x05, 0x14, 0x01, 0x11, 0x14], [0x01, 0x05, 0x05, 0x14, 0xc1, 0x14],
        [0xc1, 0x05, 0x05, 0x14, 0x01, 0x14], [0xc1, 0x05, 0x11, 0x14, 0x01, 0x14], [0x01, 0x05, 0x11, 0x14, 0xc1, 0x14],
        [0xc1, 0x11, 0x02, 0x25, 0x05, 0x14], [0x01, 0x11, 0x02, 0x25, 0xc5, 0x14], [0x01, 0x11, 0x11, 0xc5, 0x05, 0x14],
        [0xc1, 0x14, 0x14, 0x01, 0x11, 0x14], [0x01, 0x05, 0x14, 0xc1, 0x14, 0x14], [0x01, 0x14, 0x14, 0xc1, 0x14, 0x14],
        [0xc1, 0x14, 0x14, 0x14, 0x01, 0x14], [0xc1, 0x14, 0x14, 0x01, 0x14, 0x04], [0xc1, 0x14, 0x14, 0x14, 0x04, 0x04],
        [0xc1, 0x14, 0x14, 0x04, 0x04, 0x04], [0xc1, 0x05, 0x14, 0x01, 0x14, 0x04], [0x01, 0x05, 0x14, 0xc1, 0x14, 0x04],
        [0x04, 0xc1, 0x11, 0x14, 0x01, 0x14], [0xc1, 0x14, 0x01, 0x14, 0x04, 0x04], [0x04, 0xc1, 0x11, 0x14, 0x04, 0x04],
        [0xc1, 0x14, 0x04, 0x04, 0x04, 0x04], [0xc4, 0x04, 0x04, 0x04, 0x04, 0x04]]


def lfo_delta():
    try:
        t = (GEN / "felucca_tables.h").read_text()
        body = t[t.index("FM6_LFO_DELTA[100]"):]
        return [int(x) for x in re.findall(r"\d+", body[body.index("{"):body.index("}")])]
    except (OSError, ValueError):                       # (no build: msfa's curve, near enough for a picture)
        return [round(2 ** 32 / BPS * 0.062 * 1.0657 ** i) for i in range(100)]


LFO_DELTA = lfo_delta()


def scaleout(ol):
    return 28 + ol if ol >= 20 else LEVELLUT[max(ol, 0)]


def scale_vel(vel, sens):
    return ((sens * (VELDATA[max(0, min(127, vel)) >> 1] - 239) + 7) >> 3) << 4


def scale_rate(note, sens):
    return (sens * max(0, min(31, note // 3 - 7))) >> 3


def scale_curve(group, depth, curve):
    s = (group * depth * 329) >> 12 if curve in (0, 3) else (EXPSCALE[min(group, 32)] * depth * 329) >> 15
    return -s if curve < 2 else s


def scale_level(note, op):
    off = note - op[BP] - 17
    return scale_curve((off + 1) // 3, op[RD], op[RC]) if off >= 0 else scale_curve(-(off - 1) // 3, op[LD], op[LC])


class Env:                                               # fm6_env_t: fm6_env_init / advance / get / key
    def __init__(s, op, outlevel, rscale):
        s.op, s.outlevel, s.rscale, s.level, s.down = op, outlevel, rscale, 0, 1
        s.advance(0)

    def advance(s, ix):
        s.ix = ix
        if ix >= 4:
            return
        lv = s.op[L1 + ix]
        actual = max(((scaleout(lv) >> 1) << 6) + s.outlevel - 4256, 16)
        s.target = actual << 16
        s.rising = s.target > s.level
        qrate = min(((s.op[R1 + ix] * 41) >> 6) + s.rscale, 63)
        if s.target == s.level or (ix == 0 and lv == 0):
            sr = min(s.op[R1 + ix] + s.rscale, 99)
            s.statc = STATICS[sr] if sr < 77 else 20 * (99 - sr)
            if sr < 77 and ix == 0 and lv == 0:
                s.statc //= 20
        else:
            s.statc = 0
        s.inc = (4 + (qrate & 3)) << (2 + 5 + (qrate >> 2))

    def get(s):
        if s.statc:
            s.statc -= N
            if s.statc <= 0:
                s.statc = 0
                s.advance(s.ix + 1)
        if s.ix < 3 or (s.ix < 4 and not s.down):
            if s.statc:
                pass
            elif s.rising:
                s.level = max(s.level, 1716 << 16)
                s.level += (((17 << 24) - s.level) >> 24) * s.inc
                if s.level >= s.target:
                    s.level = s.target
                    s.advance(s.ix + 1)
            else:
                s.level -= s.inc
                if s.level <= s.target:
                    s.level = s.target
                    s.advance(s.ix + 1)
        return s.level

    def key(s, down):
        if s.down != down:
            s.down = down
            s.advance(0 if down else 3)


class PEnv:                                              # fm6_penv_t
    def __init__(s, p):
        s.p, s.level, s.down = p, PENV_TAB[p[PL1 + 3] % 100] << 19, 1
        s.advance(0)

    def advance(s, ix):
        s.ix = ix
        if ix < 4:
            s.target = PENV_TAB[s.p[PL1 + ix] % 100] << 19
            s.rising = s.target > s.level
            s.inc = PENV_RATE[s.p[PR1 + ix] % 100] * PENV_UNIT

    def get(s):
        if s.ix < 3 or (s.ix < 4 and not s.down):
            s.level += s.inc if s.rising else -s.inc
            if (s.rising and s.level >= s.target) or (not s.rising and s.level <= s.target):
                s.level = s.target
                s.advance(s.ix + 1)
        return s.level

    def key(s, down):
        if s.down != down:
            s.down = down
            s.advance(0 if down else 3)


class Lfo:                                               # fm6_lfo_t (sine and triangle are all the mockups need)
    def __init__(s, p):
        a = 99 - p[LFD] % 100
        s.delta, s.wave, s.dstate = LFO_DELTA[p[LFS] % 100], p[LFW], 0
        s.phase = (1 << 31) - 1 if p[LKS] else 0
        if a == 99:
            s.dinc = s.dinc2 = 2 ** 32 - 1
        else:
            a = (16 + (a & 15)) << (1 + (a >> 4))
            s.dinc = LFO_UNIT * a
            s.dinc2 = LFO_UNIT * max(a & 0xff80, 0x80)

    def sample(s):
        s.phase = (s.phase + s.delta) & 0xFFFFFFFF
        if s.wave == 4:
            return 0.5 + 0.5 * math.sin(2 * math.pi * s.phase / 2 ** 32)
        x = s.phase / 2 ** 32
        return 2 * x if x < 0.5 else 2 - 2 * x

    def delay(s):
        d = s.dinc if s.dstate < 2 ** 31 else s.dinc2
        n = s.dstate + d
        if n >= 2 ** 32:
            return 1.0
        s.dstate = n
        return 0.0 if n < 2 ** 31 else ((n >> 7) & ((1 << 24) - 1)) / (1 << 24)


def carriers(alg):
    """per operator 1..6: a carrier of algorithm alg (1..32)"""
    return [not (ALGS[alg - 1][5 - k] & 3) for k in range(6)]


def fb_op(alg):
    return next((k for k in range(6) if ALGS[alg - 1][5 - k] & 0xC0 == 0xC0), 5)


def op_bytes(p, k):                                      # operator k + 1's 21 bytes (the sixth first in the patch)
    return p[(5 - k) * 21:(6 - k) * 21]


TOP, SPAN, HSPAN = 15 << 24, 10 << 24, 10 << 24         # full scale; the 60 dB shown; the modulators' 60 dB of heat


def run(p, note=60, vel=100, held=None, rel=None):
    """the note as the engine plays it: per step every operator's level (Q24 log2), the pitch envelope (semitones), the
    LFO's vibrato (semitones); the key up at step `held`. held/rel None: found (every carrier at its sustain, cap 4 s;
    the release until the carriers fall below the 60 dB shown, cap 2 s)"""
    note += p[TRNSP] - 24
    car = carriers(p[ALG] + 1)
    env = []
    for k in range(6):
        op = op_bytes(p, k)
        ol = (min(scaleout(op[OL]) + scale_level(note, op), 127) << 5) + scale_vel(vel, op[KVS])
        env.append(Env(op, max(ol, 0), scale_rate(note, op[RS])))
    pe, lfo = PEnv(p), Lfo(p)
    cap = held if held is not None else int(4 * BPS)
    lv, pitch, vib, stage, n = [[] for _ in range(6)], [], [], [], 0
    while True:
        if n == cap:
            for e in env:
                e.key(0)
            pe.key(0)
        for k in range(6):
            lv[k].append(env[k].get())
        stage.append([e.ix for e in env])
        pitch.append(pe.get() / (1 << 24) * 12)
        d = lfo.delay()
        s = lfo.sample()
        pmd = (p[LPMD] % 100) * 165 >> 6
        vib.append(pmd * d * PMS[p[LPMS] & 7] * (s - 0.5) / 2 ** 15 * 12)        # (Q24 octaves: the >> 39)
        n += 1
        if held is None and n < cap and all(env[k].ix >= 3 for k in range(6) if car[k]):
            return run(p, note - p[TRNSP] + 24, vel, max(n + int(n / 4), int(0.35 * BPS)), rel)
        if n > cap and (n - cap >= (rel or int(2 * BPS)) or
                        (rel is None and all(lv[k][-1] < TOP - SPAN for k in range(6) if car[k]))):
            break
    return dict(lv=lv, pitch=pitch, vib=vib, stage=stage, held=cap, n=n, car=car)


def heat(p, r, i):
    """0..1: how hard the modulators drive the carriers at step i: the strongest modulator's level over its top 60 dB
    (the feedback one more, scaled by FB / 7). (Steinberg averages the modulators: with six operators and several
    carriers an average dulls a bright pair beside quiet ones, so the strongest one rules here)"""
    car, terms = r["car"], []
    for k in range(6):
        if not car[k] and op_bytes(p, k)[OL]:
            terms.append(max(0.0, min(1.0, (r["lv"][k][i] - (TOP - HSPAN)) / HSPAN)))
    if p[FB]:
        k = fb_op(p[ALG] + 1)
        terms.append(p[FB] / 7 * max(0.0, min(1.0, (r["lv"][k][i] - (TOP - HSPAN)) / HSPAN)))
    return math.sqrt(max(terms)) if terms else 0.0       # (the square root: a little FM is already heard)


def routes(alg):
    """m[k]: the operators (bit j: operator j + 1) that modulate operator k + 1 (ui_graph.c fm6_routes)"""
    f, bus, m = ALGS[alg - 1], [0, 0, 0, 0], [0] * 6
    for k in range(6):
        op, inn, o = 5 - k, (f[k] >> 4) & 3, f[k] & 3
        m[op] = bus[inn] if inn else 0
        bus[o] = (bus[o] if f[k] & 4 else 0) | 1 << op
    return m


def feeders(alg, c):
    m, seen, todo = routes(alg), 0, [c]
    while todo:
        k = todo.pop()
        new = m[k] & ~seen
        seen |= new
        todo += [j for j in range(6) if new >> j & 1]
    return seen


def heat_of(p, r, i, c):
    """D: carrier c's own heat: the strongest of the modulators feeding it (the feedback if its operator is among
    them or c itself)"""
    terms, f = [], feeders(p[ALG] + 1, c)
    for k in range(6):
        if f >> k & 1 and op_bytes(p, k)[OL]:
            terms.append(max(0.0, min(1.0, (r["lv"][k][i] - (TOP - HSPAN)) / HSPAN)))
    k = fb_op(p[ALG] + 1)
    if p[FB] and (f >> k & 1 or k == c):
        terms.append(p[FB] / 7 * max(0.0, min(1.0, (r["lv"][k][i] - (TOP - HSPAN)) / HSPAN)))
    return math.sqrt(max(terms)) if terms else 0.0       # (the square root: a little FM is already heard)


def loud(r, i):
    return max(r["lv"][k][i] for k in range(6) if r["car"][k])


# ---------------------------------------------------------------- the patches
def patch(name):
    if name == "INIT VOICE":
        return list(G.INIT)
    return list(next(v for n, v in G.PATCHES if v[145:155] == [ord(c) for c in name.ljust(10)] or n == name))


TINE = patch("TINE EP")
KEYS = list(TINE)                                        # OP2 played softer up the keyboard (the mock's edit)
KEYS[(5 - 1) * 21 + RD], KEYS[(5 - 1) * 21 + RC] = 40, 0
BRASS, INIT = patch("BRASS"), patch("INIT VOICE")

# ---------------------------------------------------------------- the screen
BLUE = (40, 92, 232)
TRK0 = mock.hexc("#FF5A36")


def ramp(s, d, t1=TRK0):
    """the 12 shades, cold to hot"""
    if d == "C":
        lo = mix(s.c["surf"], t1, 0.3)
        return [mix(lo, t1, i / 6) if i <= 6 else mix(t1, (255, 255, 255), (i - 6) / 5 * 0.85) for i in range(12)]
    cold = mix(s.c["surf"], BLUE, 0.6 if d != "D" else 0.8)
    return [mix(cold, s.c["rec"], i / 11) for i in range(12)]


def base(title, cards, hot, name="TINE EP", right="SELECT: ROWS"):
    s = u3.kit("SKIFF_edit_fm6")
    s.c["rec"] = (255, 72, 72)
    u3.title(s, title)
    u3.cards(s, [it or ("", "", "", None) for it in cards], hot)
    s.box(0, 74, 239, 216, fill=s.c["bg"])
    s.box(3, 76, 236, 213, fill=s.c["surf"])
    s.box(0, 218, 239, 239, fill=s.c["bg"])
    s.text((5, 236), "1", "val", s.trk[0])
    s.text((21, 234), "FM6", "lab", "text")
    s.text((21 + s.tw("FM6", "lab") + 7, 234), name, "lab", "text")
    s.text((235, 234), right, "lab", "mid", anchor="rs")
    return s


def raise_(s):
    return mix(s.c["surf"], s.c["text"], 0.12)


def ratio_txt(op):
    if op[MODE]:
        return ("1", "10", "100", "1K")[op[FC] & 3]
    return "0.5" if op[FC] == 0 else str(op[FC])


def tabs(s, p, sel, y=80, h=17, ratios=False):
    car = carriers(p[ALG] + 1)
    for k in range(6):
        x = 8 + k * 38
        op = op_bytes(p, k)
        on = k == sel
        fill = s.trk[0] if on else raise_(s)
        s.box(x, y, x + 33, y + h - 1, fill=fill)
        ink = s.c["ink"] if on else (s.c["dim"] if not op[OL] else s.c["text"])
        if ratios:
            s.text((x + 4, y + h - 4), str(k + 1), "lab", ink)
            s.text((x + 30, y + h - 4), ratio_txt(op) + ("x" if not op[MODE] else ""), "lab",
                   s.c["ink"] if on else s.c["mid"], anchor="rs")
        else:
            s.text((x + 17, y + h - 4), str(k + 1), "lab", ink, anchor="ms")
        if car[k]:                                       # the carriers: the output bus under them
            s.box(x, y + h + 1, x + 33, y + h + 2, fill=s.trk[0] if on else s.c["mid"])


def scroll(s, w, n=5, y0=80, y1=211):
    s.box(236, y0, 237, y1, fill=raise_(s))
    hgt = (y1 - y0) // n
    s.box(236, y0 + w * hgt, 237, y0 + (w + 1) * hgt, fill=s.c["mid"])


X0, XW = 10, 220                                        # the graph's columns
HELD_W = 160                                            # the held part's columns; the release's the rest


def col_step(r, x):
    """the step column x shows: the held part and the release each on a log time axis (the attack gets room)"""
    tau = 0.02 * BPS
    if x < HELD_W:
        T = r["held"]
        return min(T - 1, int(tau * ((1 + T / tau) ** (x / (HELD_W - 1)) - 1)))
    T = r["n"] - r["held"]
    return min(r["n"] - 1, r["held"] + int(tau * ((1 + T / tau) ** ((x - HELD_W) / (XW - HELD_W - 1)) - 1)))


def step_col(r, i):
    return next((x for x in range(XW) if col_step(r, x) >= i), XW - 1)


def lv_at(r, k, x):
    """operator k's level at column x, between the steps where a column is less than one"""
    i = col_step(r, x)
    j = col_step(r, x + 1) if x + 1 < XW else i
    if j <= i + 1 and x > 0:
        a = col_step(r, x - 1)
        nx = next((xx for xx in range(x + 1, XW) if col_step(r, xx) != i), XW)
        px = next((xx for xx in range(x - 1, -1, -1) if col_step(r, xx) != i), -1) + 1
        if nx - px > 1 and nx < XW:                     # x is in a run of columns on one step: slide to the next
            f = (x - px) / (nx - px)
            return r["lv"][k][i] + f * (r["lv"][k][col_step(r, nx)] - r["lv"][k][i])
    return r["lv"][k][i]


def lvy(v, y0, h):
    return y0 + round(max(0.0, min(1.0, (TOP - v) / SPAN)) * (h - 1))


def secs(i):
    t = i / BPS
    return f"{max(1, round(t * 1000))} MS" if t < 0.1 else f"{t:.2f} S" if t < 1 else f"{t:.1f} S"


def heat_view(s, p, sel, d, y0, h, marks=(), hot_mark=None, outline_only=False):
    """the brightness envelope: per column the carriers' level, filled with the heat's shade; the operators behind"""
    r = run(p)
    sh = ramp(s, d)
    hs = [heat(p, r, col_step(r, x)) for x in range(XW)]
    for x in range(XW):
        i = col_step(r, x)
        top = lvy(loud(r, i), y0, h)
        col = raise_(s) if outline_only else sh[round(hs[x] * 11)]
        s.box(X0 + x, top, X0 + x, y0 + h - 1, fill=col)
    kx = X0 + HELD_W                                     # the key up
    for yy in range(y0, y0 + h, 2):
        s.g.point((kx, yy), fill=s.c["dim"])
    if outline_only:
        return r
    for k in sorted(range(6), key=lambda k: k == sel):  # the operators: MID, the selected one bright on a shadow
        if not op_bytes(p, k)[OL]:
            continue
        pts = [(X0 + x, lvy(r["lv"][k][col_step(r, x)], y0, h)) for x in range(XW)]
        if k == sel:
            s.g.line([(x, y + 1) for x, y in pts], fill=s.c["bg"], width=2)
            s.g.line(pts, fill=s.c["text"] if d == "C" else s.trk[0], width=2)
        else:
            s.g.line(pts, fill=s.c["mid"], width=1)
    ends = []                                            # the selected operator's stage ends: where each was reached
    st = [row[sel] for row in r["stage"]]
    for i in range(1, len(st)):
        if st[i] != st[i - 1] and st[i - 1] < 4 and (st[i] == st[i - 1] + 1):
            ends.append((st[i - 1], i))
    for stg, i in ends:
        if stg in marks:
            x = X0 + step_col(r, i)
            y = lvy(r["lv"][sel][i], y0, h)
            s.box(x - 2, y - 2, x + 2, y + 2, fill=s.c["text"] if stg == hot_mark else s.trk[0])
    best = max(range(XW), key=lambda x: hs[x])
    if hs[best] > 0.01:
        s.g.polygon([(X0 + best - 3, y0 + h + 5), (X0 + best + 3, y0 + h + 5), (X0 + best, y0 + h + 1)],
                    fill=s.c["text"])
        s.text((10, 211), "BRIGHTEST " + secs(col_step(r, best)), "lab", "mid")
    else:
        live = sum(1 for k, c in enumerate(carriers(p[ALG] + 1)) if c and op_bytes(p, k)[OL])
        s.text((10, 211), "PURE SINE" if live == 1 else "NO MODULATION", "lab", "mid")
    s.text((X0 + HELD_W - 3, 211), "KEY UP " + secs(r["held"]), "lab", "dim", anchor="rs")
    s.text((229, 211), secs(r["n"]), "lab", "mid", anchor="rs")
    return r


OPC = ["#FF5A36", "#22C3B4", "#FFBF00", "#9580FF", "#FF6FAE", "#A3E635"]   # an operator's own colour (the
                                                                          # palette's six: T_TRK)


def warp(r, i):
    """step i -> its column: the held part and the release each on a log time axis (the attack gets room)"""
    tau = 0.02 * BPS
    if i <= r["held"]:
        T = r["held"]
        return (HELD_W - 1) * math.log(1 + i / tau) / math.log(1 + T / tau)
    T = max(1, r["n"] - r["held"])
    return HELD_W + (XW - HELD_W - 1) * math.log(1 + min(i - r["held"], T) / tau) / math.log(1 + T / tau)


def breaks(r, k):
    """operator k's envelope as straight segments: (column, level) at its start, every stage it finishes, the key up
    and the end; and where each stage ends among them (the handles). lv[i] is the level after step i: at time i + 1"""
    st, lv = [row[k] for row in r['stage']], r['lv'][k]
    pts, ends, prev = [(0.0, 0)], {}, 0
    for i in range(r['n']):
        if st[i] != prev or i + 1 == r['held']:
            pts.append((warp(r, i + 1), lv[i]))
            for s_ in range(prev, min(st[i], 4) if st[i] > prev else prev):
                ends[s_] = len(pts) - 1
            prev = st[i]
    pts.append((warp(r, r['n']), lv[r['n'] - 1]))
    return pts, ends


def at(pts, x):
    for (xa, va), (xb, vb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return va if xb == xa else va + (vb - va) * (x - xa) / (xb - xa)
    return pts[-1][1]


def brush(s, x, y, w, col):
    """a round brush w px wide (2..5): a square with its corners off"""
    a, b = -(w // 2), w - w // 2 - 1
    x, y = round(x), round(y)
    if w > 3:
        s.box(x + a, y + a + 1, x + b, y + b - 1, fill=col)
        s.box(x + a + 1, y + a, x + b - 1, y + b, fill=col)
    else:
        s.box(x + a, y + a, x + b, y + b, fill=col)


def stroke(s, pts, w, colf):
    """a polyline with the round brush, its colour per column (colf(x))"""
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        n = max(1, int(max(abs(xb - xa), abs(yb - ya)) * 2))
        for j in range(n + 1):
            x, y = xa + (xb - xa) * j / n, ya + (yb - ya) * j / n
            brush(s, x, y, w, colf(x))


def ring(s, x, y, filled):
    """a breakpoint's handle: a 9 px ring (the one the knob just turned: filled)"""
    x, y = round(x), round(y)
    s.g.ellipse([x - 5, y - 5, x + 5, y + 5], fill=s.c["bg"])
    s.g.ellipse([x - 4, y - 4, x + 4, y + 4], outline=s.c["text"], width=2, fill=s.c["text"] if filled else s.c["surf"])


def lines_view(s, p, sel, y0, h, marks=(), hot_mark=None):
    """D LINES, as Floyd Steinberg's screen: every operator's envelope as straight segments between its breakpoints;
    the modulators thin in their own colours, each carrier thick and shaded along its length by its own heat (the
    modulators feeding it, at that moment, as drawn); the picked operator's breakpoints as handles"""
    r = run(p)
    sh = ramp(s, "D")
    car = carriers(p[ALG] + 1)
    alg = p[ALG] + 1
    seg = {k: breaks(r, k) for k in range(6) if op_bytes(p, k)[OL]}

    def yv(v):
        return lvy(v, y0 + 4, h - 8)

    def norm(v):
        return max(0.0, min(1.0, (v - (TOP - HSPAN)) / HSPAN))

    def heat_x(c, x):
        f = feeders(alg, c)
        terms = [norm(at(seg[k][0], x)) for k in seg if f >> k & 1]
        k = fb_op(alg)
        if p[FB] and k in seg and (f >> k & 1 or k == c):
            terms.append(p[FB] / 7 * norm(at(seg[k][0], x)))
        return math.sqrt(max(terms)) if terms else 0.0   # (the square root: a little FM is already heard)

    kx = X0 + HELD_W
    for yy in range(y0, y0 + h, 2):                     # the key up
        s.g.point((kx, yy), fill=s.c["dim"])
    order = [k for k in seg if not car[k] and k != sel] + [k for k in seg if car[k] and k != sel] + \
        ([sel] if sel in seg else [])
    best, bx = 0.0, 0
    for k in order:
        pts = [(X0 + x, yv(v)) for x, v in seg[k][0]]
        if car[k]:
            hc = {}

            def colf(x, k=k, hc=hc):
                xi = round(x - X0)
                if xi not in hc:
                    hc[xi] = heat_x(k, xi)
                return sh[round(hc[xi] * 11)]
            stroke(s, [(x, y + 1) for x, y in pts], 5, lambda x: s.c["bg"])
            stroke(s, pts, 4 if k != sel else 5, colf)
            for xi, hv in hc.items():
                if hv > best:
                    best, bx = hv, xi
        else:
            col = mock.hexc(OPC[k])
            c = col if k == sel else mix(s.c["surf"], col, 0.7)
            stroke(s, pts, 2 if k != sel else 3, lambda x, c=c: c)
    if sel in seg:                                      # the handles: the breakpoints the window's knobs move
        pts, ends = seg[sel]
        for stg in marks:
            if stg in ends:
                x, v = pts[ends[stg]]
                ring(s, X0 + x, yv(v), stg == hot_mark)
    if best > 0.01:
        s.g.polygon([(X0 + bx - 3, y0 + h + 5), (X0 + bx + 3, y0 + h + 5), (X0 + bx, y0 + h + 1)], fill=s.c["text"])
        i = next((i for i in range(r["n"]) if warp(r, i) >= bx), 0)
        s.text((10, 211), "BRIGHTEST " + secs(i), "lab", "mid")
    else:
        live = sum(1 for k, c in enumerate(car) if c and op_bytes(p, k)[OL])
        s.text((10, 211), "PURE SINE" if live == 1 else "NO MODULATION", "lab", "mid")
    s.text((229, 211), secs(r["n"]), "lab", "mid", anchor="rs")
    s.text((129, 211), "SINE", "lab", "dim", anchor="rs")   # the key: cold .. hot (the key up: the dotted line)
    for j, c in enumerate(sh):
        s.box(132 + j * 3, 204, 134 + j * 3, 210, fill=c)
    s.text((171, 211), "FM", "lab", "dim")
    return r


def tabs_d(s, p, sel, y=80, h=17, ratios=False):
    """D's tabs, outlined as his, the picked one in the track's colour; under each, its line's colour (a carrier's:
    the ramp, it shows the heat)"""
    car = carriers(p[ALG] + 1)
    sh = ramp(s, "D")
    for k in range(6):
        x = 8 + k * 38
        op = op_bytes(p, k)
        on = k == sel
        s.box(x, y, x + 33, y + h - 1, fill=s.c["surf"], outline=s.c["text"] if on else s.c["dim"], w=2 if on else 1)
        ink = s.c["text"] if on else (s.c["dim"] if not op[OL] else s.c["mid"])
        if ratios:
            s.text((x + 5, y + h - 4), str(k + 1), "lab", ink)
            s.text((x + 29, y + h - 4), ratio_txt(op) + ("x" if not op[MODE] else ""), "lab", s.c["mid"], anchor="rs")
        else:
            s.text((x + 17, y + h - 4), "OP" + str(k + 1), "lab", ink, anchor="ms")
        if not op[OL]:
            continue
        if car[k]:
            for j in range(12):
                s.box(x + 3 + j * 2 + (j > 5) * 4, y + h + 2, x + 4 + j * 2 + (j > 5) * 4, y + h + 3, fill=sh[j])
        else:
            s.box(x + 3, y + h + 2, x + 30, y + h + 3, fill=mock.hexc(OPC[k]))


def lens_ratios(s, p, sel, y0):
    """B's TONE strip: the ratios on a ruler, x0.5 .. x32 (log), modulators above, carriers below"""
    car = carriers(p[ALG] + 1)
    y = y0 + 17
    s.box(14, y, 225, y, fill=s.c["line"])
    for i, lab in enumerate(["0.5", "1", "2", "4", "8", "16", "32"]):
        x = 14 + round(i * 211 / 6)
        s.box(x, y - 2, x, y + 2, fill=s.c["dim"])
        s.text((x, y0 + 35), lab, "lab", "dim", anchor="ms")
    seen = {}
    for k in range(6):
        op = op_bytes(p, k)
        if not op[OL] or op[MODE]:
            continue
        rt = (op[FC] or 0.5) * (1 + op[FF] / 100)
        x = 14 + round((math.log2(rt) + 1) * 211 / 6)
        row = 0 if not car[k] else 1
        n = seen.get((x // 12, row), 0)
        seen[(x // 12, row)] = n + 1
        bx = x - 5 + n * 12
        by = y0 + 3 if row == 0 else y + 4
        on = k == sel
        s.box(bx, by, bx + 10, by + 10, fill=s.trk[0] if on else raise_(s))
        s.text((bx + 5, by + 10), str(k + 1), "lab", s.c["ink"] if on else s.c["text"], anchor="ms")


def lens_stages(s, r, sel, y0, lit, hot):
    """B's ENV strip: the selected operator's stages numbered under their time (the heat view's own axis)"""
    st = [row[sel] if row[sel] < 3 else (3 if i >= r["held"] else -1) for i, row in enumerate(r["stage"])]
    spans, a = [], 0                                     # (-1: holding at LEVEL 3 with the key down)
    for i in range(1, len(st) + 1):
        if i == len(st) or st[i] != st[a]:
            spans.append((st[a], step_col(r, a), step_col(r, i - 1)))
            a = i
    for stg, xa, xb in spans:
        if stg >= 4 or xb - xa < 3:
            continue
        on = stg in lit
        fill = s.trk[0] if stg == hot else (mix(s.c["surf"], s.trk[0], 0.35) if on else raise_(s))
        s.box(X0 + xa + 1, y0 + 6, X0 + xb - 1, y0 + 22, fill=fill)
        if xb - xa > 12:
            s.text(((2 * X0 + xa + xb) / 2, y0 + 19), str(stg + 1) if stg >= 0 else "HOLD", "lab",
                   s.c["ink"] if stg == hot else s.c["text"] if on else s.c["mid"], anchor="ms")
    s.text((X0, y0 + 34), "STAGES OF OP" + str(sel + 1), "lab", "dim")


def note_name(n):                                        # ui.c note_name: MIDI 60 = C4
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][n % 12] + str(n // 12 - 1)


def keyboard(s, p, sel, y0, h):
    """the selected operator's level across the keys: its offset (dB) for MIDI 21..108, BREAK marked, C4 a dot"""
    op = op_bytes(p, sel)
    kb = y0 + h - 16
    for o in range(1, 8):                                # the octaves under the curve, C1 .. C7 (MIDI 24 ..)
        xa = X0 + (12 * o + 12 - 21) * (XW - 1) / 87
        xb = min(X0 + XW - 1, X0 + (12 * o + 24 - 21) * (XW - 1) / 87)
        s.box(round(xa), kb + 2, round(xb) - 1, kb + 5, fill=raise_(s) if o % 2 else s.c["dim"])
        if o in (2, 4, 6):
            s.text((round(xa), kb + 15), "C" + str(o), "lab", "dim")
    zy, rng = y0 + 22, (kb - 6) - (y0 + 22)
    s.hline(zy, "line", X0, X0 + XW - 1)
    s.text((X0 + XW - 1, zy - 3), "0 DB", "lab", "dim", anchor="rs")
    s.text((X0 + XW - 1, kb - 4), "-48 DB", "lab", "dim", anchor="rs")
    pts = []
    for n in range(21, 109):
        db = scale_level(n, op) * 0.75                   # an outlevel step: 1/8 of 6 dB
        x = X0 + (n - 21) * (XW - 1) / 87
        pts.append((x, zy + max(-12.0, min(48.0, -db)) / 48 * rng))
    s.g.line([(x, y + 1) for x, y in pts], fill=s.c["bg"], width=2)
    s.g.line(pts, fill=s.trk[0], width=2)
    bx = X0 + (op[BP] + 21 - 21) * (XW - 1) / 87
    for yy in range(y0 + 4, kb - 2, 2):
        s.g.point((round(bx), yy), fill=s.c["text"])
    s.text((round(bx) + 4, y0 + 13), "BREAK " + note_name(op[BP] + 21), "lab", "text")
    cx = X0 + (60 - 21) * (XW - 1) / 87
    cy = zy + max(-12.0, min(48.0, -scale_level(60, op) * 0.75)) / 48 * rng
    s.box(round(cx) - 2, round(cy) - 2, round(cx) + 2, round(cy) + 2, fill=s.c["text"])
    db_hi = scale_level(96, op) * 0.75
    s.text((X0, y0 + 13), f"C7 {db_hi:+.0f} DB", "lab", "mid")


def pitch_view(s, p, y0, h, lfo=False):
    """ALL OPS' PITCH and LFO windows: the sound's outline in RAISE, the pitch (envelope + vibrato) bright"""
    if lfo:
        r = run(p, held=int(2 * BPS), rel=1)
        n = int(2 * BPS)
        steps = [round(x * (n - 1) / (XW - 1)) for x in range(XW)]
    else:
        r = run(p)
        steps = [col_step(r, x) for x in range(XW)]
    for x, i in enumerate(steps):                      # the sound behind
        s.box(X0 + x, lvy(loud(r, i), y0, h), X0 + x, y0 + h - 1, fill=raise_(s))
    vals = [r["vib"][i] if lfo else r["pitch"][i] for i in steps]   # (LFO: the vibrato alone, PITCH its envelope)
    m = max(abs(v) for v in vals) or 1
    rng = next(v for v in (0.1, 0.25, 0.5, 1, 2, 4, 12, 24, 48) if v >= m)
    zy = y0 + h // 2
    s.hline(zy, "line", X0, X0 + XW - 1)
    pts = [(X0 + x, zy - v / rng * (h // 2 - 6)) for x, v in enumerate(vals)]
    s.g.line([(x, y + 1) for x, y in pts], fill=s.c["bg"], width=2)
    s.g.line(pts, fill=s.trk[0], width=2)
    s.text((10, y0 + 12), f"+{rng:g} ST", "lab", "mid")
    s.text((10, y0 + h - 4), f"-{rng:g} ST", "lab", "mid")
    if lfo:
        hz = LFO_DELTA[p[LFS]] * BPS / 2 ** 32
        s.text((10, 211), f"VIBRATO {hz:.1f} HZ, IN AFTER " + secs(next((i for i, v in enumerate(r['vib'])
                                                                          if abs(v) > 0.2 * m), 0)), "lab", "mid")
        s.text((229, 211), "2.0 S", "lab", "mid", anchor="rs")
    else:
        s.text((10, 211), "PITCH OVER THE NOTE", "lab", "mid")
        s.text((229, 211), secs(r["n"]), "lab", "mid", anchor="rs")


def algo(s):
    """ALL OPS ALGO: the firmware's chart (algorithm 5), the operator PRESETS picked lit"""
    chart = Image.open(u3.p6.RENDERS / "SKIFF_fm6_alg_05.ppm").convert("RGB").crop((3, 76, 237, 214))
    s.img.paste(chart, (3, 76))
    s.g = ImageDraw.Draw(s.img)
    s.g.fontmode = "L"
    x, y = 120 + 1 * 24 - 2 * 12, 76 + 19 + 52 - 23     # OP4: column 1, row 1 (ui_graph.c graph_fm6)
    s.box(x - 10, y, x + 10, y + 16, fill=s.c["text"])
    s.text((x, y + 13), "4", "lab", s.c["ink"], anchor="ms")
    s.text((10, 211), "OP4 MODULATES OP3", "lab", "mid")


# ---------------------------------------------------------------- the screens
def op_cards(p, k, win):
    op = op_bytes(p, k)
    cv = ["-LIN", "-EXP", "+EXP", "+LIN"]
    if win == 0:
        rt = (op[FC] or 0.5) * (1 + op[FF] / 100)
        return [("OUTPUT", str(op[OL]), "", op[OL] / 99), ("RATIO", ratio_txt(op), "x", op[FC] / 31),
                ("FINE", f"{rt:.2f}", "", op[FF] / 99), ("DETUNE", str(op[DET] - 7), "", op[DET] / 14)]
    if win == 1:
        return [("RATE 1", str(op[R1]), "", op[R1] / 99), ("LEVEL 1", str(op[L1]), "", op[L1] / 99),
                ("RATE 2", str(op[R1 + 1]), "", op[R1 + 1] / 99), ("LEVEL 2", str(op[L1 + 1]), "", op[L1 + 1] / 99)]
    return [("L CURVE", cv[op[LC]], "", op[LC] / 3), ("L DEPTH", str(op[LD]), "", op[LD] / 99),
            ("R DEPTH", str(op[RD]), "", op[RD] / 99), ("R CURVE", cv[op[RC]], "", op[RC] / 3)]


def screen(d, what):
    lens = d == "B"
    hy, hh = (101, 58) if lens else (102, 94)
    if what == "tone":
        s = base("OPERATOR 4", op_cards(TINE, 3, 0), 0)
        (tabs_d if d == "D" else tabs)(s, TINE, 3, ratios=True)
        r = lines_view(s, TINE, 3, hy, hh, marks=(0, 1, 2, 3)) if d == "D" else heat_view(s, TINE, 3, d, hy, hh)
        if lens:
            lens_ratios(s, TINE, 3, 160)
        scroll(s, 0)
    elif what == "env":
        s = base("OPERATOR 4", op_cards(TINE, 3, 1), 2)
        (tabs_d if d == "D" else tabs)(s, TINE, 3)
        r = (lines_view(s, TINE, 3, hy, hh, marks=(0, 1, 2, 3), hot_mark=1) if d == "D" else
             heat_view(s, TINE, 3, d, hy, hh, marks=(0, 1), hot_mark=1))
        if lens:
            lens_stages(s, r, 3, 160, (0, 1), 1)
        scroll(s, 1)
    elif what == "keys":
        s = base("OPERATOR 2", op_cards(KEYS, 1, 3), 2)
        (tabs_d if d == "D" else tabs)(s, KEYS, 1)
        keyboard(s, KEYS, 1, 101, 108)
        scroll(s, 3)
    elif what == "algo":
        s = base("ALL OPS", [("ALGO", "5", "", 4 / 31), ("FEEDBACK", "3", "", 3 / 7), ("TRANSP", "0", "ST", 0.5),
                             None], 0)
        algo(s)
        scroll(s, 0)
    elif what == "pitch":
        s = base("ALL OPS", [("RATE 1", "80", "", 80 / 99), ("PITCH 1", "-1.5", "ST", 46 / 99),
                             ("RATE 2", "60", "", 60 / 99), ("PITCH 2", "0.0", "ST", 0.5)], 1, name="BRASS SECT")
        pitch_view(s, BRASS, 82, 116)
        scroll(s, 1)
    elif what == "lfo":
        s = base("ALL OPS", [("WAVE", "SINE", "", 0.8), ("RATE", "5.5", "HZ", 33 / 99), ("FADE", "50", "", 50 / 99),
                             ("KEY SYNC", "ON", "", 1.0)], 2, name="BRASS SECT")
        pitch_view(s, BRASS, 82, 116, lfo=True)
        scroll(s, 3)
    else:                                                # the bare sine INIT gives
        s = base("OPERATOR 1", op_cards(INIT, 0, 0), None, name="INIT VOICE")
        (tabs_d if d == "D" else tabs)(s, INIT, 0, ratios=True)
        lines_view(s, INIT, 0, hy, hh, marks=(0, 1, 2, 3)) if d == "D" else heat_view(s, INIT, 0, d, hy, hh)
        if lens:
            lens_ratios(s, INIT, 0, 160)
        scroll(s, 0)
    return s


def save(s, name):
    img = s.img
    img.save(OUT / f"{name}.png")
    for z in (2, 3):
        (OUT / f"x{z}").mkdir(parents=True, exist_ok=True)
        img.resize((W * z, H * z), Image.NEAREST).save(OUT / f"x{z}" / f"{name}.png")
    return img


PALS = [("SKIFF", (12, 12, 12), (30, 30, 30), (255, 255, 255), (255, 72, 72), (255, 90, 54)),
        ("HI-CON", (0, 0, 0), (40, 40, 40), (255, 255, 255), (255, 72, 72), (255, 232, 0)),
        ("PAPER", (244, 239, 228), (226, 218, 202), (34, 30, 24), (190, 24, 40), (10, 84, 70)),
        ("CRYPT", (10, 7, 5), (34, 24, 16), (236, 214, 172), (255, 72, 72), (236, 110, 50)),
        ("NEON", (12, 4, 26), (30, 12, 50), (244, 236, 255), (255, 72, 72), (255, 64, 176)),
        ("QUARK", (3, 7, 12), (10, 21, 32), (216, 243, 255), (255, 72, 72), (255, 84, 96))]


def ramps_strip(z=2):
    """the two ramps in every palette: A/B (cool blue -> REC), C (the track's colour to white-hot)"""
    im = Image.new("RGB", (W * z, 6 * 34 * z + 30 * z), (24, 24, 24))
    s = u3.kit()
    s.img, s.g = im, ImageDraw.Draw(im)
    s.g.fontmode = "L"
    for i, (name, bg, surf, text, rec, t1) in enumerate(PALS):
        y = 6 + i * 34
        s.box(0, y * z, W * z, (y + 32) * z, fill=bg)
        s.c["surf"], s.c["rec"] = surf, rec
        for row, d in enumerate("AC"):
            for j, c in enumerate(ramp(s, d, t1)):
                x = 60 + j * 14
                s.box(x * z, (y + 3 + row * 14) * z, (x + 13) * z - 1, (y + 15 + row * 14) * z - 1, fill=c)
            s.text((6 * z, (y + 13 + row * 14) * z), f"{name} {d}", "lab", text)
    return im


def main():
    names = ["tone", "env", "keys", "algo", "pitch", "lfo", "init"]
    rows = []
    for d in "ABCD":
        rows.append([save(screen(d, w), f"FM6{d}_{w}") for w in names])
    gap, z, top = 16, 2, 36
    lw = 120
    out = Image.new("RGB", (lw + len(names) * (W * z + gap) + gap, top + len(rows) * (H * z + gap) + gap),
                    (24, 24, 24))
    s = u3.kit()
    s.img, s.g = out, ImageDraw.Draw(out)
    s.g.fontmode = "L"
    heads = ["OPERATOR: TONE", "OPERATOR: ENV 1", "OPERATOR: KEYS", "ALL OPS: ALGO", "ALL OPS: PITCH 1",
             "ALL OPS: LFO", "AFTER INIT: THE BARE SINE"]
    for i, hd in enumerate(heads):
        s.text((lw + gap + i * (W * z + gap), top - 10), hd, "lab", (184, 184, 184))
    for r, shots in enumerate(rows):
        y = top + gap + r * (H * z + gap)
        s.text((16, y + 40), "ABCD"[r], "big", (255, 255, 255))
        s.text((16, y + 70), ["HEAT", "HEAT + LENS", "TRACK HEAT", "LINES"][r], "lab", (184, 184, 184))
        for i, im in enumerate(shots):
            out.paste(im.resize((W * z, H * z), Image.NEAREST), (lw + gap + i * (W * z + gap), y))
    out.save(HERE / "mockups" / "fm6_sheet.png")
    ramps_strip().save(HERE / "mockups" / "fm6_ramps.png")
    print("fm6_sheet.png", out.size)


if __name__ == "__main__":
    main()
