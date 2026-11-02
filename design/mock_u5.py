#!/usr/bin/env python3
"""U5 mockups (the UX review's screens batch), each screen in SKIFF (today's BLOCKS) beside CRYPT (B TORCHLIT's
palette, stone and motifs, its graphs drawn as A's ASCII art: / \\ _ | strokes in character cells; the user's pick):
  V1  a graph of its own for every page that shows the generic audio scope (ENV DEST, LFO DEST, DELAY, REVERB, CHORUS,
      GLOBAL, VOICE, VOICE 2, the EDIT pages, ARP, ARP 2)
  A1  HOME held (SHIFT): a map of what every control does on this page, drawn like the layer maps
SKIFF starts from the firmware's renders (tests/ui_render.c, P6_RENDERS) and redraws the graph panel; CRYPT is
mock_crypt's kit.
  P6_RENDERS=../build/ui_new/ppm python3 mock_u5.py   -> out/U5_*.png, out/CR_u5_*.png, mockups/u5_sheet.png
"""
import math
from PIL import Image, ImageDraw
import mock
import mock_crypt as K
import mock_u3 as u3
from mock import OUT, W, HERE, mix

K.G.update({'^': ["  #  ", " # # ", "#   #", "     ", "     ", "     ", "     "], '|': ["#"] * 7})
CH = 9                          # a row of CRYPT's text: the 5 x 7 font, two pixels between rows


# ---------------------------------------------------------------- SKIFF: a render, its graph panel redrawn
def sk(base, title=None, cards=None, hot=None, pos=None):
    s = u3.kit("SKIFF_" + base)
    s.key = "U5"
    if title:
        u3.title(s, title)
    if cards:
        u3.cards(s, [it or ("", "", "", None) for it in cards], hot)
    if pos:
        s.box(180, 218, 239, 239, fill=s.c["bg"])
        s.text((235, 234), pos, "lab", "mid", anchor="rs")
    s.box(3, 76, 236, 214, fill=s.c["surf"])
    return s


def line(s, pts, col, w=2):
    s.g.line(pts, fill=col, width=w, joint="curve")


def dot(s, x, y, col, r=3):
    s.g.rectangle([x - r, y - r, x + r, y + r], fill=col)


# ---------------------------------------------------------------- CRYPT: a page and A's ASCII-art strokes
def cr(title, cards, hot=None, pos="1/2", foot="ANALOG  ACID"):
    c = K.C(K.B)
    K.header(c, title)
    for k in range(4):
        it = cards[k] if k < len(cards) else None
        if it:
            l, v, u, f = it
            K.card(c, k, l, v, u, f, hot=k == hot, ztext=2 if K.text_w(v, 2) <= 49 - K.text_w(u) else 1)
        else:
            K.card(c, k, "", "", "", None)
    K.panel(c)
    K.footer(c, foot, pos, track=0)
    return c


def stroke(c, xa, ya, xb, yb, col, pen=2):
    n = max(abs(xb - xa), abs(yb - ya) // pen, 1)
    for t in range(n + 1):
        c.rect(round(xa + (xb - xa) * t / n), round(ya + (yb - ya) * t / n), pen, pen, col)


def art(c, x0, y0, cw, ch, levels, col, fill=None, floor=None):
    """a curve as ASCII art, A's way: levels (grid lines from the top, one per character column) joined cell by cell
    with _ where it holds, / or \\ where it moves a line or two, _| or |_ where it jumps (a saw's or a square's edge),
    all 2 px strokes; fill: a : in each cell under it down to floor"""
    for i, (r, r2) in enumerate(zip(levels, levels[1:])):
        xa, ya, yb = x0 + i * cw, y0 + r * ch, y0 + r2 * ch
        if abs(r2 - r) >= 3:
            stroke(c, xa, ya, xa + cw - 2, ya, col)
            stroke(c, xa + cw - 2, ya, xa + cw - 2, yb, col)
        else:
            stroke(c, xa, ya, xa + cw, yb, col)
        if fill:
            for k in range(max(r, r2) + 1, max(levels) + 1 if floor is None else floor):
                c.text(xa + cw // 2 - 1, y0 + k * ch - 8, ':', fill)


def lv(vals, rows):
    return [round((1 - v) * rows) for v in vals]


def head(c, x, y, col):
    """the snake's head (LFO's motif), its snout at x, y: an eye, a forked tongue"""
    c.sprite(x - 2, y - 3, ["  ####  ", " ###### ", "########", "##.#####", "########", " ###### "], {'#': col, '.': 'ink'})
    c.rect(x + 6, y, 4, 1, 'blood')
    c.pset(x + 10, y - 1, 'blood')
    c.pset(x + 10, y + 1, 'blood')


def snake(c, x0, y0, cw, ch, levels, col, belly='blood'):
    """a curve as a snake: the strokes doubled for a body (its belly darker), gold scales along it, the head at the end"""
    art(c, x0, y0 + 2, cw, ch, levels, belly)
    art(c, x0, y0, cw, ch, levels, col)
    for i in range(1, len(levels) - 1, 2):
        c.rect(x0 + i * cw + cw // 2 - 1, y0 + round((levels[i] + levels[i + 1]) / 2 * ch), 2, 1, 'gold')
    head(c, x0 + (len(levels) - 1) * cw, y0 + levels[-1] * ch + 1, col)


def adsr(x, a=0.08, d=0.25, s=0.45, r0=0.75):
    if x < a:
        return x / a
    if x < d:
        return 1 - (1 - s) * (x - a) / (d - a)
    if x < r0:
        return s
    return max(0.0, s * (1 - (x - r0) / (1 - r0)))


# ---------------------------------------------------------------- V1: the pages
ED = [("CUTOFF", "+40", "%", 0.81), ("PITCH", "-12", "%", 0.41), ("SHAPE", "0", "%", 0.5), None]


def env_dest():
    s = sk("env_dest", cards=ED, hot=0)
    t1 = s.trk[0]
    cy = 150
    s.hline(cy, "line", 10, 229)
    for amt, col, w in ((0, s.c["dim"], 1), (-12, s.c["mid"], 2), (40, t1, 3)):
        line(s, [(12 + i, cy - round(amt / 63 * 90 * adsr(i / 210))) for i in range(0, 211, 3)], col, w)
    s.text((228, 98), "CUTOFF +40", "lab", t1, anchor="rs")
    s.text((228, 194), "PITCH -12", "lab", "mid", anchor="rs")
    s.text((228, 209), "SHAPE 0", "lab", "dim", anchor="rs")
    s.save("env_dest")
    c = cr("ENV DEST", ED, hot=0, pos="2/2")
    n, cw = 19, 12
    xs = [i / (n - 1) for i in range(n)]
    c.rect(12, 154, 216, 1, 'line')
    top = lv([adsr(x) * 40 / 42 for x in xs], 4)
    art(c, 12, 98, cw, 14, top, 'amber', fill='line', floor=5)
    low = [round(adsr(x) * 12 / 42 * 4 + 0.3) for x in xs]
    art(c, 12, 154, cw, 14, low, 'mid')
    K.skull(c, 12 + 4 * cw, 154 + max(low) * 14 + 4, 'dim')
    pk = max(range(n), key=lambda i: adsr(xs[i]))
    K.skull(c, 12 + pk * cw - 4, 98 + top[pk] * 14 - 12, 'flame')
    c.text_r(230, 86, "CUTOFF +40", 'amber')
    c.text_r(230, 192, "PITCH -12", 'mid')
    c.text_r(230, 202, "SHAPE 0", 'dim')
    c.save("u5_env_dest")


LD = [("PITCH", "+10", "%", 0.58), ("CUTOFF", "+45", "%", 0.85), ("SHAPE", "0", "%", 0.5), ("AMP", "20", "%", 0.16)]
LD_AMT = [10, 45, 0, 20]


def lfo_dest():
    s = sk("lfo", title="LFO DEST", cards=LD, hot=1, pos="2/3")
    now = 0.62
    for k, ((lab, *_), amt) in enumerate(zip(LD, LD_AMT)):
        y = 93 + k * 32
        col = s.trk[0] if k == 1 else s.c["mid"] if amt else s.c["dim"]
        s.text((10, y + 5), lab, "lab", col)
        s.hline(y, "line", 62, 229)
        a = 13 * amt / 45
        line(s, [(62 + i, y - round(a * math.sin(i / 167 * 4 * math.pi))) for i in range(0, 168, 2)], col, 3 if k == 1 else 2)
        if amt:
            dot(s, 62 + round(now * 167), y - round(a * math.sin(now * 4 * math.pi)), s.c["text"], 2)
    s.save("lfo_dest")
    c = cr("LFO DEST", LD, hot=1, pos="2/3")
    n, cw = 21, 8
    for k, ((lab, *_), amt) in enumerate(zip(LD, LD_AMT)):
        y = 84 + k * 32
        col = 'amber' if k == 1 else 'mid' if amt else 'dim'
        c.text(10, y + 9, lab, col)
        a = 0 if not amt else max(1, round(2 * amt / 45))   # at least a line either way: a small amount still shows
        levels = [2 - round(a * math.sin(i / (n - 1) * 4 * math.pi)) for i in range(n)]
        i = round(now * (n - 1))
        if not amt:
            art(c, 60, y, cw, 6, levels, col)
            continue
        art(c, 60 + i * cw, y, cw, 6, levels[i:], 'line')          # where it goes next
        snake(c, 60, y, cw, 6, levels[:i + 1], col, 'ember' if k == 1 else 'dim')   # the head: where the LFO is now
    c.save("u5_lfo_dest")


DL = [("TIME", "1/8", "", 0.3), ("FEEDBACK", "47", "%", 0.47), ("COLOR", "55", "%", 0.55), ("MIX", "71", "%", 0.71)]


def taps(fb=0.47, mix_=0.71):
    """the dry hit, then the echoes: MIX the first, each next FEEDBACK lower"""
    out, lvl = [1.0], mix_
    while lvl >= 0.04 and len(out) < 8:
        out.append(lvl)
        lvl *= fb
    return out


def delay():
    s = sk("dly", hot=1, cards=DL)
    t1 = s.trk[0]
    for b in range(8):                                 # the eighths of a bar under it, its beats numbered
        x = 14 + b * 26
        s.g.rectangle([x, 199, x + 13, 199], fill=s.c["dim"] if b % 2 == 0 else s.c["line"])
        if b % 2 == 0:
            s.text((x, 212), str(b // 2 + 1), "lab", "dim")
    for i, lvl in enumerate(taps()):
        x, h = 14 + i * 26, round(100 * lvl)
        col = s.c["text"] if i == 0 else mix(t1, s.c["surf"], 0.15 + 0.5 * (i - 1) / 6)
        s.g.rectangle([x, 196 - h, x + 13, 196], fill=col)
    s.text((14, 92), "DRY", "lab", "mid")
    s.text((228, 92), "x 47% EACH", "lab", "mid", anchor="rs")
    s.save("delay")
    c = cr("DELAY", DL, hot=1, pos="2/5", foot="GLO")
    for i, lvl in enumerate(taps()):
        x = 16 + i * 26
        n = max(1, round(8 * lvl))
        col = ['text', 'amber', 'ember', 'ember', 'blood', 'blood', 'dim', 'dim'][i]
        for r in range(n):
            c.text(x + 2, 190 - r * CH, '#', col)
        if i == 0:
            K.torch(c, x, 190 - n * CH - 25, 0, z=2)
        else:
            K.skull(c, x, 190 - n * CH - 10, col)
        if i % 2 == 0:
            c.text(x + 3, 202, str(i // 2 + 1), 'dim')
    c.save("u5_delay")


RV = [("TYPE", "SPRING", "", None), ("SIZE", "71", "%", 0.71), ("DAMP", "47", "%", 0.47), None]


def reverb():
    s = sk("reverb_spring")
    t1 = s.trk[0]
    for i, h in enumerate((84, 60, 72, 46, 52)):        # the first reflections
        s.g.rectangle([12 + i * 6, 202 - h, 14 + i * 6, 202], fill=s.c["text"])
    for x in range(44, 229):                           # the tail: SIZE long, its top dimmed by DAMP
        t = (x - 44) / 184
        h = round(84 * math.exp(-2.4 * t))
        s.g.line([(x, 202 - round(h * 0.55)), (x, 202)], fill=mix(t1, s.c["surf"], t * 0.6))
        s.g.line([(x, 202 - h), (x, 202 - round(h * 0.55))], fill=mix(t1, s.c["surf"], 0.55 + t * 0.3))
    for x in range(64, 229):                           # SPRING: its coil
        s.g.point((x, 89 + round(3 * math.sin((x - 64) / 3.2))), fill=s.c["mid"])
    s.text((12, 93), "SPRING", "lab", "mid")
    s.save("reverb")
    c = cr("REVERB", RV, hot=1, pos="3/5", foot="GLO")
    shade = "#*+:."
    for i in range(5):                                 # the first reflections: ! columns
        for r in range((9, 7, 8, 5, 6)[i]):
            c.text(12 + i * 5, 196 - r * CH, '!', 'text')
    for ci in range(31):
        t = ci / 30
        n = round(11 * math.exp(-2.4 * t))
        for r in range(n):
            top = r >= n * 0.55
            ch = shade[min(4, int(t * 4) + (1 if top else 0))]
            c.text(42 + ci * 6, 196 - r * CH, ch, 'blood' if top else 'amber' if t < 0.35 else 'ember')
    K.torch(c, 12, 84, 1, z=2)
    c.text(36, 85, "~" * 26, 'mid')
    c.text_r(230, 86, "SPRING", 'dim')
    c.save("u5_reverb")


CO = [("RATE", ".41", "HZ", 0.3), ("DEPTH", "47", "%", 0.47), None, None]


def chorus():
    s = sk("chorus")
    t1 = s.trk[0]
    s.hline(150, "line", 10, 229)
    for k, (col, w) in enumerate(((s.c["dim"], 2), (s.c["mid"], 2), (t1, 3))):
        line(s, [(12 + i, 150 + round(44 * 0.47 * math.sin(i / 216 * 2 * math.pi * 2.2 + k * 2.1))) for i in range(0, 217, 2)], col, w)
    s.text((12, 92), "3 VOICES, PITCH DRIFTING", "lab", "mid")
    s.save("chorus")
    c = cr("CHORUS", CO, pos="4/5", foot="GLO")
    n, cw = 24, 8
    for k, col in enumerate(('amber', 'ember', 'blood')):
        y = 88 + k * 40
        c.text(10, y + 9, "V" + str(k + 1), col)
        snake(c, 34, y, cw, 9, [2 - round(2 * math.sin(i / (n - 1) * 2 * math.pi * 2.2 + k * 2.1)) for i in range(n)], col,
              'blood' if k < 2 else 'dim')
    c.save("u5_chorus")


GL = [("BPM", "124", "", 0.4), ("SWING+", "22", "%", 0.22), None, None]


def glob():
    s = sk("global", cards=GL, hot=1)
    t1 = s.trk[0]
    push = round(0.22 * 13)                              # SWING+ 22: the off sixteenths that much of a step late
    for i in range(16):
        x = 14 + i * 13
        h = 74 if i % 4 == 0 else 52 if i % 2 == 0 else 40
        if i % 2:
            s.g.rectangle([x, 201, x + 6, 203], fill=s.c["dim"])     # where it would be, straight
            x += push
        s.g.rectangle([x, 196 - h, x + 6, 196], fill=s.c["text"] if i % 4 == 0 else t1 if i % 2 == 0 else mix(t1, s.c["surf"], 0.35))
    for b in range(4):
        s.text((14 + b * 52, 112), str(b + 1), "num", "mid")
    s.text((228, 92), "OFF STEPS 22% LATE", "lab", "mid", anchor="rs")
    s.save("global")
    c = cr("GLOBAL", GL, hot=1, pos="5/5", foot="GLO")
    for i in range(16):
        x = 14 + i * 13 + (3 if i % 2 else 0)
        n = 8 if i % 4 == 0 else 6 if i % 2 == 0 else 4
        col = 'text' if i % 4 == 0 else 'amber' if i % 2 == 0 else 'ember'
        for r in range(n):
            c.text(x, 196 - r * CH, '#', col)
        if i % 2:
            c.text(x - 1, 205, '^', 'dim')
    for b in range(4):
        c.text(14 + b * 52, 88, str(b + 1), 'mid', z=2)
    K.torch(c, 14 + 9 * 13 + 1, 196 - 3 * CH - 27, 0, z=2)      # the playhead, as on HOME
    c.save("u5_global")


VO = [("VOICE", "LEG", "", None), ("GLIDE", "120", "MS", 0.4), ("GL MODE", "RATE", "", None), ("PRIORITY", "LAST", "", None)]


def voice():
    s = sk("voice", cards=VO, hot=1)
    t1 = s.trk[0]
    s.g.rectangle([12, 168, 100, 178], fill=s.c["mid"])
    line(s, [(100, 173), (150, 115)], t1, 4)
    s.g.rectangle([150, 110, 228, 120], fill=t1)
    for x in (100, 150):
        s.g.line([(x, 192), (x, 200)], fill=s.c["dim"])
    s.g.line([(100, 196), (150, 196)], fill=s.c["dim"])
    s.text((125, 211), "120 MS", "lab", "mid", anchor="ms")
    s.text((12, 92), "LEG: ONE VOICE, NO NEW ATTACK", "lab", "mid")
    s.save("voice")
    c = cr("VOICE", VO, hot=1, pos="3/4")
    art(c, 12, 110, 12, 14, [4] * 8 + [3, 2, 1, 0] + [0] * 6, 'amber')
    K.sword_gauge(c, 84, 186, 62, 1.0, 'amber')                   # the glide's time a sword, as long as it
    c.text(150, 186, "120 MS", 'mid')
    c.text(12, 86, "LEG: ONE VOICE", 'mid')
    c.save("u5_voice")


V2 = [("ALLOC", "ROT", "", None), ("DETUNE", "40", "", 0.31), None, None]


def voice2():
    s = sk("voice", title="VOICE 2", cards=V2, hot=0, pos="4/4")
    t1 = s.trk[0]
    for v in range(6):                                 # the voices; the next note takes the outlined one (ROT: in turn)
        x = 12 + v * 36
        on = v in (0, 1)
        s.g.rectangle([x, 100, x + 30, 128], fill=t1 if on else s.c["line"])
        s.text((x + 15, 120), str(v + 1), "num", "ink" if on else "mid", anchor="ms")
    s.g.rectangle([12 + 2 * 36 - 2, 98, 12 + 2 * 36 + 32, 130], outline=s.c["text"], width=2)
    s.text((12, 92), "NEXT NOTE: VOICE 3", "lab", "mid")
    for d in (-1, 0, 1):                               # DETUNE: the unison voices spread apart
        y = 172 + d * round(14 * 0.31 * 2)
        s.g.rectangle([60, y - 1, 228, y + 1], fill=t1 if d == 0 else s.c["mid"])
    s.text((12, 176), "SPREAD", "lab", "dim")
    s.save("voice2")
    c = cr("VOICE 2", V2, hot=0, pos="4/4")
    for v in range(6):
        K.skull(c, 14 + v * 36 + 6, 100, 'amber' if v in (0, 1) else 'gold' if v == 2 else 'dim', z=2)
    c.frame2(14 + 2 * 36, 94, 30, 30, 'gold')
    c.text(14, 84, "NEXT: 3", 'mid')
    for d in (-1, 0, 1):
        c.text(60, 168 + d * 9, "=" * 28, 'amber' if d == 0 else 'ember')
    c.text(12, 168, "SPREAD", 'dim')
    c.save("u5_voice2")


OS = [("WAVE", "SAW", "", None), ("DETUNE", "10", "CT", 0.08), ("MIX", "50", "%", 0.5), ("NOISE", "0", "%", 0.0)]


def saw(x, det=0.0):
    return (x * (1 + det)) % 1.0


def osc():
    s = sk("edit_analog", cards=OS, hot=0)
    t1 = s.trk[0]
    for col, w, det in ((s.c["mid"], 1, 0.06), (t1, 3, 0.0)):
        pts = [(12 + i, 196 - round(96 * saw(i / 72, det))) for i in range(217)]
        for a, b in zip(pts, pts[1:]):
            s.g.line([a, b], fill=col, width=w)
    s.text((12, 92), "SAW, A SECOND ONE 10 CT UP", "lab", "mid")
    s.save("osc")
    c = cr("OSC", OS, hot=0, pos="1/4")
    n, cw = 27, 8
    art(c, 12, 98, cw, 16, lv([saw((i + 0.5) / 9, 0.06) for i in range(n)], 6), 'dim')
    teeth = lv([saw((i + 0.5) / 9) for i in range(n)], 6)
    for i, (r, r2) in enumerate(zip(teeth, teeth[1:])):
        if r2 <= r:
            c.dither(12 + i * cw, 98 + r * 16 + 2, cw, (6 - r) * 16 - 2, 'blood', 2 if r < 3 else 1)
    art(c, 12, 98, cw, 16, teeth, 'amber')
    c.text(12, 85, "SAW", 'mid')
    c.save("u5_osc")


FL = [("CUTOFF", "355", "HZ", 0.62), ("RES", "79", "%", 0.79), ("DRIVE", "0", "%", 0.0), ("KEYTRK", "50", "%", 0.5)]


def lp(f, fc=0.45, res=0.79):
    """a low pass's level (0..1) at f (0..1 on a log axis): flat, a peak at fc as high as res, steep after"""
    if f <= fc:
        return 0.62 + 0.38 * res * math.exp(-((f - fc) / 0.05) ** 2)
    return max(0.0, (0.62 + 0.38 * res) - 3.2 * (f - fc))


def flt():
    s = sk("edit_analog", title="FLT", cards=FL, hot=0, pos="2/4")
    t1 = s.trk[0]
    xc = 12 + round(0.45 * 216)
    s.g.line([(xc, 84), (xc, 206)], fill=s.c["dim"])
    pts = [(12 + i, 202 - round(110 * lp(i / 216))) for i in range(217)]
    s.g.polygon(pts + [(228, 202), (12, 202)], fill=mix(t1, s.c["surf"], 0.75))
    line(s, pts, t1, 3)
    s.text((xc + 5, 96), "355 HZ", "lab", "text")
    s.text((12, 214), "LOW", "lab", "dim")
    s.text((228, 214), "HIGH", "lab", "dim", anchor="rs")
    s.save("flt")
    c = cr("FLT", FL, hot=0, pos="2/4")
    n, cw = 27, 8
    art(c, 12, 92, cw, 16, lv([lp(i / (n - 1)) for i in range(n)], 6), 'amber', fill='line', floor=7)
    curve = lv([lp(i / (n - 1)) for i in range(n)], 6)
    pk = min(range(n), key=lambda i: curve[i])
    K.skull(c, 12 + pk * cw, 92 + curve[pk] * 16 - 12, 'flame')
    xc = 12 + round(0.45 * (n - 1)) * cw
    c.sprite(xc - 4, 186, K.DAGGER[::-1], {'#': 'gold'}, z=2)
    c.text(xc + 9, 192, "355 HZ", 'gold')
    c.save("u5_flt")


AR = [("MODE", "UP", "", None), ("RATE", "1/16", "", 0.5), ("OCTAVE", "2", "", 0.33), ("GATE", "50", "%", 0.5)]
AR2 = [("SWING", "0", "%", 0.0), ("CHANCE", "80", "%", 0.63), ("HOLD", "ON", "", None), ("ORDER", "NOTE", "", None)]
ARP_N = [0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0, 1, 2, 3]     # C E G, then an octave up (OCTAVE 2), UP
SKIP = {5, 11}


def arp_graph_sk(s, chance):
    t1 = s.trk[0]
    for r in range(6):
        y = 186 - r * 18
        s.hline(y + 5, "line", 30, 228, dotted=True)
        s.text((12, y + 10), "CEGCEG"[r], "lab", "dim")
    for i, n in enumerate(ARP_N):
        x, y = round(30 + i * 12.4), 186 - n * 18
        gone = chance and i in SKIP
        s.g.rectangle([x, y, x + 6, y + 10], fill=s.c["surf"] if gone else s.c["text"] if i % 4 == 0 else t1,
                      outline=s.c["mid"] if gone else None)


def arp():
    s = sk("arp", cards=AR, hot=0)
    arp_graph_sk(s, False)
    s.save("arp")
    c = cr("ARP", AR, hot=0, pos="1/2")
    for i, n in enumerate(ARP_N):
        c.text(28 + i * 12, 186 - n * 19, '#', 'text' if i % 4 == 0 else 'amber', z=2)
    for r in range(6):
        c.text(12, 190 - r * 19, "CEGCEG"[r], 'dim')
    K.torch(c, 28 + 9 * 12, 186 - ARP_N[9] * 19 - 27, 0, z=2)
    c.save("u5_arp")
    s = sk("arp", title="ARP 2", cards=AR2, hot=1, pos="2/2")
    arp_graph_sk(s, True)
    s.save("arp2")
    c = cr("ARP 2", AR2, hot=1, pos="2/2")
    for i, n in enumerate(ARP_N):
        if i in SKIP:
            K.skull(c, 28 + i * 12, 188 - n * 19, 'mid', muted=True)
        else:
            c.text(28 + i * 12, 186 - n * 19, '#', 'text' if i % 4 == 0 else 'amber', z=2)
    for r in range(6):
        c.text(12, 190 - r * 19, "CEGCEG"[r], 'dim')
    c.save("u5_arp2")


# ---------------------------------------------------------------- A1: SHIFT's map of this page
# (key, its job here, kind): kind 0 the same on every page (MID), 1 this page's own (white), 2 a SHIFT combo (lit)
ROWS_ALL = [[("BUTTONS", "PAGES", 0), ("HOLD ONE", "ITS LAYER", 0), ("HOLD SAVE", "UNDO", 0)],
            [("+ SAVE", "TAKE", 2), ("+ REC", "REC SET", 2), ("+ BUTTON", "LOCK LAYER", 2)]]
MAP_ENV = [[("PRESETS", "SOUND", 1), ("SELECT", "PAGE", 0), ("ALGO", "TRACK", 0)],
           [("KEYS", "NOTES", 1), ("OCT- +", "OCTAVE", 0), ("PLAY", "START/STOP", 0)]] + ROWS_ALL
MAP_STEP = [[("PRESETS", "STEP", 1), ("SELECT", "PAGE", 0), ("ALGO", "TRACK", 0)],
            [("KEYS", "STEPS (REC)", 1), ("EDIT", "CLEAR STEP", 1), ("PLAY", "START/STOP", 0)]] + ROWS_ALL
EV = [("ATTACK", "1.0", "MS", 0.1), ("DECAY", "54", "MS", 0.4), ("SUSTAIN", "16", "%", 0.16), ("RELEASE", "8.8", "MS", 0.3)]
ST = [("STEP", "9", "/16", 0.56), ("NOTE", "C3", "", 0.4), ("VELOCITY", "100", "", 0.78), ("CHANCE", "100", "%", 1.0)]


def shift_sk(base, cards, mp, name, pos):
    s = u3.kit("SKIFF_" + base)
    s.key = "U5"
    u3.title(s, "SHIFT")
    u3.cards(s, cards)
    s.box(0, 74, 239, 239, fill=s.c["bg"])
    for r, row in enumerate(mp):
        for k, (key, job, kind) in enumerate(row):
            x0, y0 = 4 + 78 * k, 78 + 34 * r
            lit = kind == 2
            s.box(x0, y0, x0 + 74, y0 + 30, fill=s.c["text"] if lit else s.c["surf"])
            s.text((x0 + 5, y0 + 12), key, "lab", "ink" if lit else "mid")
            s.text((x0 + 5, y0 + 27), job, "name", "ink" if lit else "text" if kind == 1 else "mid")
    s.text((5, 234), "LET GO: MENU", "lab", "mid")
    s.text((235, 234), pos, "lab", "mid", anchor="rs")
    s.save(name)


def shift_cr(cards, mp, name, pos):
    c = K.C(K.B)
    K.header(c, "SHIFT")
    for k, it in enumerate(cards):
        K.card(c, k, *it)
    c.rect(0, 74, W, 146, 'bg')
    for r, row in enumerate(mp):
        for k, (key, job, kind) in enumerate(row):
            x0, y0 = 4 + 78 * k, 78 + 34 * r
            if kind == 2:
                c.rect(x0, y0, 74, 31, 'amber')
                c.frame(x0 + 1, y0 + 1, 72, 29, 'gold')
            else:
                c.stone(x0, y0, 74, 31)
                c.frame(x0, y0, 74, 31, 'line')
            c.text(x0 + 5, y0 + 5, key, 'ink' if kind == 2 else 'dim')
            c.text(x0 + 5, y0 + 17, job, 'ink' if kind == 2 else 'text' if kind == 1 else 'mid')
            if kind == 2:
                c.sprite(x0 + 57, y0 + 4, K.SWORD, {'#': 'ink'})
    c.rect(0, 219, W, 1, 'line')
    K.torch(c, 5, 224, 0)
    c.text(16, 227, "LET GO: MENU", 'mid')
    c.text_r(234, 227, pos, 'dim')
    c.save(name)


def shift_maps():
    shift_sk("env", EV, MAP_ENV, "shift_env", "ENV")
    shift_cr(EV, MAP_ENV, "u5_shift_env", "ENV")
    shift_sk("step_tiles", ST, MAP_STEP, "shift_step", "STEP")
    shift_cr(ST, MAP_STEP, "u5_shift_step", "STEP")


PAGES = [
    (env_dest, ["env_dest"], "ENV DEST: the ENV page's envelope scaled by each amount: CUTOFF up, PITCH down, SHAPE flat. The knob turned is the bright one. CRYPT: a skull on the peak"),
    (lfo_dest, ["lfo_dest"], "LFO DEST: the LFO's wave once per destination, as tall as its amount, a dot where it is now. CRYPT: the snake's head on the knob turned"),
    (delay, ["delay"], "DELAY: the dry hit, then an echo every TIME (1/8 here), each FEEDBACK lower, over the bar's beats. CRYPT: # columns under skulls"),
    (reverb, ["reverb"], "REVERB: the first reflections, then the tail SIZE long, its top dimmed by DAMP; SPRING drawn as a coil (ROOM: none). CRYPT: shade characters # * + : ."),
    (chorus, ["chorus"], "CHORUS: three voices' pitch drifting apart: RATE how fast, DEPTH how far"),
    (glob, ["global"], "GLOBAL: a bar's 16 steps, the off steps pushed late by SWING+ (their straight place marked under them), the beats numbered"),
    (voice, ["voice"], "VOICE: what the mode does (LEG: one voice, no new attack) and the GLIDE between two notes, its time under it"),
    (voice2, ["voice2"], "VOICE 2: the engine's voices, the one the next note takes outlined (ROT: in turn); DETUNE the unison voices' spread. CRYPT: skulls"),
    (osc, ["osc"], "EDIT 1 on ANALOG (OSC): the wave the oscillator makes, the detuned second one under it. Each engine draws its own (ops, grains, bars); one with nothing to draw keeps the scope"),
    (flt, ["flt"], "EDIT 2 on ANALOG (FLT): the filter's curve, its peak at CUTOFF as high as RES"),
    (arp, ["arp", "arp2"], "ARP and ARP 2 share one graph: the arp's notes over a bar (C E G held, UP, 2 octaves) ... on ARP 2 the notes CHANCE skips are outlined (CRYPT: crossed skulls), SWING moves the off notes"),
    (shift_maps, ["shift_env", "shift_step"], "A1: HOME held (SHIFT) maps every control on this page, as the layer maps do: this page's own jobs white (ENV: PRESETS = SOUND; STEP: PRESETS = STEP, KEYS = STEPS, EDIT = CLEAR STEP), the SHIFT combos lit, the rest grey"),
]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    pairs = []
    for fn, names, cap in PAGES:
        fn()
        for i, n in enumerate(names):
            pairs.append((n, cap if i == 0 else ""))
    cols, pad, gap = 2, 22, 10
    capf = mock.font("BarlowCondensed-Medium.ttf", 22)
    pw, ph = 2 * 480 + gap, 480 + 84
    rn = (len(pairs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (pw + pad) + pad, rn * (ph + pad) + pad), (22, 20, 18))
    g = ImageDraw.Draw(sheet)
    for i, (n, cap) in enumerate(pairs):
        r, cc = divmod(i, cols)
        x, y = pad + cc * (pw + pad), pad + r * (ph + pad)
        sheet.paste(Image.open(OUT / "x2" / f"U5_{n}.png"), (x, y))
        sheet.paste(Image.open(OUT / "x2" / f"CR_u5_{n}.png"), (x + 480 + gap, y))
        words, ln, ly = cap.split(), "", y + 480 + 24
        for w_ in words:
            if g.textlength(ln + " " + w_, font=capf) > pw and ln:
                g.text((x, ly), ln, font=capf, fill=(230, 214, 180))
                ln, ly = w_, ly + 25
            else:
                ln = (ln + " " + w_).strip()
        g.text((x, ly), ln, font=capf, fill=(230, 214, 180))
    sheet.save(HERE / "mockups" / "u5_sheet.png")
    print("wrote", len(pairs), "pairs: mockups/u5_sheet.png")
