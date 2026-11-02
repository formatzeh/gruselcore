#!/usr/bin/env python3
"""QUARK theme mockups: particle physics. A collider's event display at night: particle tracks curling in the field,
bubble-chamber trails, nuclei and their orbitals, decay chains, Feynman diagrams; the six tracks the quarks' colour
charges (red, green, blue) and their anticolours (cyan, magenta, yellow). Skiff's own Barlow faces (no new font).
Two directions:
  A COLLIDER  the event display: cards as the periodic table's cells, beams and bunches on HOME, collisions at the
              playhead, calorimeter towers, decay chains, a hazard sign on what can't be undone
  B LAB       an instrument's readout: cyan on black, plots with axes, ticks and the physicist's annotations (T1/2, PHI)
Everything is drawn at 240 x 240 (what the panel shows), then enlarged without smoothing.
  python3 mock_quark.py       -> out/QK_<screen>.png (x1 x2 x3), mockups/quark_sheet.png
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "out"
FONTS = HERE.parent / "assets" / "fonts"
W = H = 240
NAME = "QUARK"


def mix(a, b, t):
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


# ---------------------------------------------------------------- palettes
A = dict(bg=(3, 7, 12), surf=(10, 21, 32), surf2=(18, 36, 52), line=(22, 44, 64), dim=(54, 86, 108),
         mid=(127, 166, 188), text=(216, 243, 255), cyan=(79, 209, 255), gold=(255, 224, 102), red=(255, 84, 96),
         ink=(3, 7, 12),
         trk=[(255, 84, 96), (70, 220, 130), (90, 140, 255), (60, 220, 240), (230, 96, 230), (250, 220, 80)])
B = dict(bg=(0, 6, 10), surf=(0, 14, 20), surf2=(0, 24, 32), line=(0, 46, 60), dim=(0, 90, 110), mid=(0, 160, 190),
         text=(170, 245, 255), cyan=(0, 230, 255), gold=(0, 230, 255), red=(255, 90, 90), ink=(0, 6, 10),
         trk=[(0, 230, 255)] * 6)
FS = {"S": ("BarlowCondensed-Medium.ttf", 13), "M": ("BarlowCondensed-Bold.ttf", 16),
      "V": ("BarlowCondensed-Bold.ttf", 24), "L": ("BarlowCondensed-Bold.ttf", 34)}
_F = {}


def font(k):
    if k not in _F:
        f, px = FS[k]
        _F[k] = ImageFont.truetype(str(FONTS / f), px)
    return _F[k]


class Q:
    def __init__(self, pal):
        self.p = pal
        self.im = Image.new("RGB", (W, H), pal["bg"])
        self.px = self.im.load()
        self.d = ImageDraw.Draw(self.im)

    def col(self, c):
        return self.p.get(c, c) if isinstance(c, str) else c

    def pset(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[int(x), int(y)] = self.col(c)

    def rect(self, x, y, w, h, c):
        if w > 0 and h > 0:
            self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=self.col(c))

    def frame(self, x, y, w, h, c):
        self.d.rectangle([x, y, x + w - 1, y + h - 1], outline=self.col(c))

    def line(self, x0, y0, x1, y1, c, w=1):
        self.d.line([x0, y0, x1, y1], fill=self.col(c), width=w)

    def poly(self, pts, c, w=1):
        self.d.line(pts, fill=self.col(c), width=w, joint="curve")

    def ellipse(self, cx, cy, rx, ry, c, rot=0.0, n=64, dash=0):
        pts = []
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            x, y = rx * math.cos(a), ry * math.sin(a)
            pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
        if dash:
            for k in range(0, n, 2):
                self.line(*pts[k], *pts[k + 1], c)
        else:
            self.poly(pts, c)

    def disc(self, cx, cy, r, c):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self.col(c))

    def text(self, x, y, s, c, k="S", anchor="la"):
        """y: the baseline (anchor 'ls') or the top"""
        self.d.text((x, y), s, font=font(k), fill=self.col(c), anchor=anchor)
        return self.d.textlength(s, font=font(k))

    def tw(self, s, k="S"):
        return self.d.textlength(s, font=font(k))

    def corners(self, x, y, w, h, c, L=5):
        """a lab instrument's bracket corners"""
        for (cx, cy, dx, dy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
            self.line(cx, cy, cx + dx * (L - 1), cy, c)
            self.line(cx, cy, cx, cy + dy * (L - 1), c)

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        self.im.save(OUT / f"QK_{name}.png")
        for z in (2, 3):
            (OUT / f"x{z}").mkdir(parents=True, exist_ok=True)
            self.im.resize((W * z, H * z), Image.NEAREST).save(OUT / f"x{z}" / f"QK_{name}.png")


# ---------------------------------------------------------------- the motifs: tracks, nuclei, decays, hazard ..
def track(c, x0, y0, ang, r, length, col, bubbles=True, curl=1):
    """a charged particle's track curling in the field: an arc of radius r from (x0, y0), its bubbles a dotted trail
    (thinning as it slows, the curl tightening)"""
    pts, a, x, y = [], ang, x0, y0
    for k in range(length):
        rr = max(4.0, r * (1 - 0.6 * k / length))
        a += curl / rr
        x += math.cos(a)
        y += math.sin(a)
        pts.append((x, y))
    for k, (px, py) in enumerate(pts):
        if not bubbles or k % 2 == 0:
            c.pset(round(px), round(py), mix(c.col(col), c.p["bg"], 0.65 * k / length))
    return pts


def nucleus(c, x, y, col, orbits=2, r=8, e=True):
    for k in range(orbits):
        c.ellipse(x, y, r, r * 0.38, mix(c.col(col), c.p["bg"], 0.35 + 0.2 * k), rot=(k - 0.5) * 1.0)
    for dx, dy, q in ((-1, -1, 0), (1, -1, 1), (0, 1, 2)):
        c.disc(x + dx * 1.6, y + dy * 1.4, 1.4, c.p["trk"][q] if c.p is A else col)
    if e:
        c.disc(x + r * math.cos(0.7), y + r * 0.38 * math.sin(0.7) - 1, 1.2, "gold")


def burst(c, x, y, n=7, seed=3, cols=None, rmax=22):
    """a collision at (x, y): tracks flying out, each curling its own way"""
    rnd = random.Random(seed)
    for k in range(n):
        ang = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        col = (cols or c.p["trk"])[k % len(cols or c.p["trk"])]
        track(c, x, y, ang, rnd.uniform(10, 40), rnd.randint(rmax // 2, rmax), col, bubbles=False,
              curl=rnd.choice((-1, 1)))
    c.disc(x, y, 2, "text")


def hazard(c, x, y, r, col):
    """the radiation trefoil (what can't be undone)"""
    for k in range(3):
        a0 = math.radians(-90 + 120 * k - 30)
        a1 = math.radians(-90 + 120 * k + 30)
        pts = [(x, y)]
        for t in range(9):
            a = a0 + (a1 - a0) * t / 8
            pts.append((x + r * math.cos(a), y + r * math.sin(a)))
        c.d.polygon(pts, fill=c.col(col))
    c.disc(x, y, r * 0.42, "bg")
    c.disc(x, y, r * 0.26, col)


def dots_gauge(c, x, y, w, frac, col, hot=False):
    """a card's gauge: energy levels, a dot every 4 px, lit up to the value"""
    n = (w - 1) // 4
    for k in range(n):
        on = k < round(n * frac)
        c.rect(x + k * 4, y, 2, 2, ("ink" if hot else col) if on else ("surf2" if not hot else mix(c.col("ink"), c.col("cyan"), 0.6)))


# ---------------------------------------------------------------- the shared parts of a screen
TRACKS = [("ACID", "ANALOG"), ("PAD", "FM6"), ("PULSE LD", "LOFI"), ("DRUM KIT", "DRUM"), ("PIANO", "SAMPLE"),
          ("BONE KIT", "DRUM-X")]
STEPS = ["1010001010100010", "1000100010001000", "0010010000100100", "1011101110111011", "1000000010000000",
         "1001001010010010"]


def header(c, title, play=True, rec=False, mark=None):
    if rec:
        c.disc(10, 11, 4, "red")
        c.ellipse(10, 11, 7, 3, mix(c.col("red"), c.p["bg"], 0.4), rot=0.5)
    elif play:
        c.d.polygon([(5, 5), (13, 11), (5, 17)], fill=c.col("cyan"))
    else:
        c.rect(5, 6, 9, 9, "mid")
    c.text(19, 17, "1.2", "text", "M", "ls")
    x = 46 + c.text(46, 17, "124", "cyan", "M", "ls")
    c.text(x + 3, 17, "BPM", "mid", "S", "ls")
    c.text(235, 17, title, "mid", "S", "rs")
    if mark:
        c.text(235 - c.tw(title) - 6, 17, mark, "gold", "S", "rs")
    for i in range(1, W, 3):                       # the beam pipe's scale: a dotted rule
        c.pset(i, 22, "dim")


def footer(c, left, right, track_no=None):
    for i in range(1, W, 3):
        c.pset(i, 218, "dim")
    x = 6
    if track_no is not None:
        x += c.text(6, 235, str(track_no + 1), c.p["trk"][track_no], "M", "ls") + 5
    c.text(x, 234, left, "mid", "S", "ls")
    c.text(234, 234, right, "dim", "S", "rs")


def card(c, k, label, val, unit, frac, hot=False, z=None):
    """the periodic table's cell: its label (the element's name) top left, its index (K1..) top right, the value big
    (the symbol), the unit after it; the gauge energy levels. Hot: the cell lit cyan"""
    x, y, w, h = 3 + 59 * k, 27, 57, 46
    if hot:
        c.rect(x, y, w, h, "cyan")
    else:
        c.rect(x, y, w, h, "surf")
        c.corners(x, y, w, h, "dim")
    ink = "ink" if hot else "mid"
    c.text(x + 4, y + 13, label, ink, "S", "ls")
    if c.tw(label) + c.tw(str(k + 1)) + 6 <= w - 8:     # (its index only where the label leaves room)
        c.text(x + w - 4, y + 13, str(k + 1), "ink" if hot else "dim", "S", "rs")
    c.text(x + 4, y + 37, val, "ink" if hot else "text", "V", "ls")
    if unit:
        c.text(x + w - 4, y + 37, unit, ink, "S", "rs")
    if frac is not None:
        dots_gauge(c, x + 4, y + 40, w - 8, frac, "cyan", hot)


def panel(c, y0=76, y1=216):
    c.rect(3, y0, 234, y1 - y0, "surf")
    c.corners(3, y0, 234, y1 - y0, "dim", 7)


# ---------------------------------------------------------------- A COLLIDER
def a_home(c):
    header(c, NAME + " 01", rec=True, mark="B")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "355", "HZ", 0.62), ("RES", "79", "%", 0.79), ("ATTACK", "1.0", "MS", 0.1),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f, hot=k == 0)
    sel, y, ph = 2, 77, 98 + 8 * 8 + 4
    for k in range(6):
        col = c.p["trk"][k]
        big = k == sel
        h = 30 if big else 18
        if big:                                        # the selected lane the beam: its colour faint, the pipe lit
            c.rect(3, y, 234, h, mix(col, c.p["bg"], 0.8))
            c.line(3, y, 236, y, col)
            c.line(3, y + h - 1, 236, y + h - 1, col)
            c.text(8, y + 23, str(k + 1), col, "V", "ls")
            c.text(26, y + 13, TRACKS[k][0], "text", "M", "ls")
            c.text(26, y + 25, TRACKS[k][1], "mid", "S", "ls")
        else:                                          # the others beam pipes: two rails
            c.line(96, y + h // 2 - 3, 236, y + h // 2 - 3, "line")
            c.line(96, y + h // 2 + 3, 236, y + h // 2 + 3, "line")
            c.text(9, y + 14, str(k + 1), col, "M", "ls")
            c.text(26, y + 14, TRACKS[k][0], "text" if k != 1 else "dim", "S", "ls")
        for j, on in enumerate(STEPS[k]):              # a note a bunch of particles in the pipe
            cx = 98 + j * 8 + (j // 4) * 2 + 3
            cy = y + h // 2
            if on == "1":
                if cx < ph:                            # played: spent, a dim ring
                    c.ellipse(cx, cy, 2.5, 2.5, mix(col, c.p["bg"], 0.5), n=16)
                else:
                    c.disc(cx, cy, 3 if big else 2.4, col)
                    c.pset(cx - 1, cy - 1, mix(col, c.col("text"), 0.6))
            else:
                c.pset(cx, cy, "dim")
        y += h + 3
    for yy in range(77, 216, 2):                       # the playhead: the beam line, dotted
        c.pset(ph, yy, "gold")
    burst(c, ph, 77 + 2 * 21 + 15, n=8, seed=5, rmax=26)   # .. and on the selected lane a collision
    footer(c, "HOLD HOME: SHIFT", "")


def adsr_pts():
    return [(10, 120), (26, 12), (60, 58), (150, 58), (210, 120)]


def env_y(x, pts):
    for k in range(1, len(pts)):
        if pts[k][0] >= x:
            a, b = pts[k - 1], pts[k]
            return a[1] + (b[1] - a[1]) * (x - a[0]) / max(1, b[0] - a[0])
    return pts[-1][1]


def a_env(c):
    header(c, "ENV")
    for k, (l, v, u, f) in enumerate([("ATTACK", "1.0", "MS", 0.1), ("DECAY", "54", "MS", 0.4), ("SUSTAIN", "16", "%", 0.16),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f, hot=k == 2)
    panel(c)
    ox, oy = 12, 84
    pts = [(ox + x, oy + y) for x, y in adsr_pts()]
    rnd = random.Random(7)
    for _ in range(1700):                              # a Monte Carlo fill: the samples under the curve kept
        x, y = rnd.uniform(pts[0][0], pts[-1][0]), rnd.uniform(oy + 6, oy + 120)
        if y > env_y(x, pts) + 1.5:
            c.pset(round(x), round(y), mix(c.col("cyan"), c.p["surf"], rnd.uniform(0.2, 0.6)))
    c.poly(pts, "cyan", 2)
    for k, (x, y) in enumerate(pts[1:4]):               # its points nuclei, the one turned gold
        nucleus(c, x, y, "gold" if k == 2 else "cyan", r=9 if k == 2 else 7)
    c.text(pts[1][0] + 14, pts[1][1] + 6, "T1/2 12 MS", "gold", "S", "ls")
    c.text(pts[3][0] - 4, pts[3][1] - 12, "T1/2 6 MS", "mid", "S", "ls")
    footer(c, "ANALOG  ACID", "1/2", 0)


def a_lfo(c):
    header(c, "LFO")
    for k, (l, v, u, f) in enumerate([("RATE", "1.9", "HZ", 0.4), ("WAVE", "SIN", "", None), ("PHASE", "0", "", 0.0),
                                      ("FADE", "0", "MS", 0.0)]):
        card(c, k, l, v, u, f, hot=k == 0)
    panel(c)
    cx, cy, r, x0 = 46, 146, 34, 92
    ph = math.radians(-50)
    c.ellipse(cx, cy, r, r * 0.34, "line", rot=1.0)
    c.ellipse(cx, cy, r, r * 0.34, "line", rot=-1.0)
    c.ellipse(cx, cy, r, r, "cyan")
    for k, (dx, dy) in enumerate(((0, -2.4), (2.2, 1.4), (-2.2, 1.4))):
        c.disc(cx + dx, cy + dy, 2, c.p["trk"][k])
    ex, ey = cx + r * math.cos(ph), cy + r * math.sin(ph)
    for x in range(int(ex), x0, 3):                    # its projection onto the wave: dashed
        c.pset(x, round(ey), "gold")
    c.line(x0, 84, x0, 208, "line")
    c.line(x0, cy, 232, cy, "line")
    pts = [(x, cy + r * math.sin(ph - (x - x0) / 140 * 2 * math.pi)) for x in range(x0, 233)]
    c.poly(pts, "cyan", 2)
    c.disc(ex, ey, 3, "gold")
    c.disc(x0, ey, 2, "gold")
    c.text(10, 96, "SIN  1.9 HZ", "mid", "S", "ls")
    c.text(232, 96, "PHI 50", "mid", "S", "rs")
    footer(c, "ANALOG  ACID", "1/3", 0)


def a_mixer(c):
    header(c, "MIXER", play=False)
    for k, (l, v, u, f) in enumerate([("LEVEL", "-6.0", "DB", 0.8), ("PAN", "-31", "%", 0.3), ("REVERB", "28", "%", 0.28),
                                      ("MUTE", "OFF", "", None)]):
        card(c, k, l, v, u, f)
    lv = [-6, -14, -24, -1, -6, -9]
    muted = [False, False, True, False, False, False]
    for k in range(6):
        x0, y0 = 4 + 39 * k, 78
        sel = k == 4
        col = c.p["trk"][k]
        c.rect(x0, y0, 36, 138, mix(col, c.p["bg"], 0.82) if sel else "surf")
        if sel:
            c.corners(x0, y0, 36, 138, col, 6)
        c.text(x0 + 4, y0 + 22, str(k + 1), col, "V", "ls")
        c.text(x0 + 4, y0 + 36, TRACKS[k][0].split()[0][:5], "dim" if muted[k] else "text", "S", "ls")
        if muted[k]:                                   # dark matter: there, but nothing shows; its tower dotted
            for yy in range(y0 + 44, y0 + 112, 3):
                c.pset(x0 + 10, yy, "dim")
                c.pset(x0 + 26, yy, "dim")
            c.text(x0 + 18, y0 + 82, "DARK", "dim", "S", "ms")
        else:                                          # a calorimeter tower: its cells, the energy deposited
            n = round(16 * (40 + lv[k]) / 40)
            for s in range(16):
                yy = y0 + 108 - s * 4
                on = s < n
                cc = mix(col, c.col("text"), 0.5 * s / 16) if on else c.col("surf2")
                c.rect(x0 + 10, yy, 16, 3, cc)
            c.rect(x0 + 8, y0 + 108 - n * 4 - 2, 20, 1, "gold")
        c.text(x0 + 18, y0 + 124, "OFF" if muted[k] else str(lv[k]), "text", "M", "ms")
        c.text(x0 + 18, y0 + 136, ["L31", "R37", "C", "L6", "L31", "R20"][k], "dim", "S", "ms")
    footer(c, "SAMPLE  PIANO", "1/5", 4)


def a_delay(c):                                        # the echoes a decay chain
    header(c, "DELAY")
    for k, (l, v, u, f) in enumerate([("TIME", "1/8", "", 0.3), ("FEEDBACK", "47", "%", 0.47), ("COLOR", "55", "%", 0.55),
                                      ("MIX", "71", "%", 0.71)]):
        card(c, k, l, v, u, f, hot=k == 1)
    panel(c)
    x, lvl, prev = 22, 1.0, None
    for i in range(7):
        if lvl < 0.04:
            break
        h = round(90 * lvl)
        y = 196 - h
        col = "text" if i == 0 else mix(c.col("cyan"), c.p["surf"], 0.12 * i)
        c.rect(x - 1, y, 2, h, col)
        nucleus(c, x, y - 8, col if i else "gold", orbits=2 if i < 3 else 1, r=max(4, 9 - i), e=i < 3)
        if prev:                                       # the decay: an arrow from the last
            c.line(prev[0] + 6, prev[1], x - 7, y - 8, "dim")
            c.line(x - 7, y - 8, x - 10, y - 10, "dim")
        prev = (x, y - 8)
        x += 30
        lvl *= 0.47
    pts = [(x, 196 - 90 * 0.47 ** ((x - 22) / 30)) for x in range(22, 222)]
    for k in range(0, len(pts), 3):                    # the exponential it follows, dotted
        c.pset(round(pts[k][0]), round(pts[k][1]), "dim")
    c.line(12, 197, 228, 197, "line")
    c.text(12, 92, "DRY", "mid", "S", "ls")
    c.text(228, 92, "T1/2 0.9 ECHOES", "gold", "S", "rs")
    footer(c, "ANALOG  ACID", "2/5", 0)


def a_dialog(c):
    a_home(c)
    for j in range(24, 217):                           # the page under it, dimmed
        for i in range(W):
            r, g, b = c.px[i, j]
            c.px[i, j] = (r // 4, g // 4, b // 4)
    x0, y0, w, h = 22, 60, 196, 120
    c.rect(x0, y0, w, h, "surf")
    c.frame(x0, y0, w, h, "line")
    c.corners(x0, y0, w, h, "gold", 9)
    hazard(c, x0 + w // 2, y0 + 18, 10, "gold")        # what can't be undone: the hazard sign
    c.text(x0 + w // 2, y0 + 46, "CLEAR T3 PATTERN?", "text", "M", "ms")
    c.text(x0 + w // 2, y0 + 60, "16 steps, 9 notes", "mid", "S", "ms")
    c.text(x0 + w // 2, y0 + 73, "can't be undone", "red", "S", "ms")
    bx = x0 + 14
    c.rect(bx, y0 + 82, 76, 22, "cyan")
    c.text(bx + 38, y0 + 98, "CANCEL", "ink", "M", "ms")
    bx = x0 + w - 14 - 76
    c.frame(bx, y0 + 82, 76, 22, "red")
    c.corners(bx - 2, y0 + 80, 80, 26, "red", 4)
    c.text(bx + 38, y0 + 98, "CLEAR", "red", "M", "ms")
    c.text(x0 + 14 + 38, y0 + 116, "OCT-", "dim", "S", "ms")
    c.text(x0 + w - 14 - 38, y0 + 116, "OCT+", "dim", "S", "ms")


def a_menu(c):                                         # the menu an instrument's settings: readouts in brackets
    c.rect(0, 0, W, H, "bg")
    nucleus(c, 12, 11, "cyan", r=7)
    c.text(24, 17, "MENU", "text", "M", "ls")
    c.text(235, 17, "HOME: CLOSE", "dim", "S", "rs")
    for i in range(1, W, 3):
        c.pset(i, 22, "dim")
    x = 8
    for i, t in enumerate(["DISPLAY", "CONTROL", "AUDIO", "SYSTEM"]):
        tw = c.tw(t) + 12
        if i == 0:
            c.rect(x, 28, tw, 16, "cyan")
        else:
            c.corners(x, 28, tw, 16, "dim", 3)
        c.text(x + 6, 40, t, "ink" if i == 0 else "mid", "S", "ls")
        x += tw + 5
    rows = [("THEME", NAME), ("LARGE", "OFF"), ("ANIM", "ON"), ("LEDS", "INV"), ("SCREEN OFF", "30 MIN"), ("HINTS", "ON")]
    for i, (n, v) in enumerate(rows):
        y = 64 + i * 25
        sel = i == 0
        if sel:
            c.rect(6, y - 13, 228, 19, mix(c.col("cyan"), c.p["bg"], 0.82))
            c.corners(6, y - 13, 228, 19, "cyan", 5)
        c.text(14, y, n, "text" if sel else "mid", "S", "ls")
        vv = "[" + v + "]"
        vx = 226 - c.tw(vv, "M")
        for xx in range(int(14 + c.tw(n) + 5), int(vx - 4), 3):
            c.pset(xx, y - 1, "line")
        c.text(226, y, vv, "gold" if sel else "cyan", "M", "rs")
    footer(c, "ALGO: TAB  PRESETS: ROW", "OCT-/+: VALUE")


def a_splash(c):
    c.rect(0, 0, W, H, "bg")
    cx, cy = 120, 104
    rnd = random.Random(11)
    for k in range(9):                                 # the event: tracks out of the collision
        ang = 2 * math.pi * k / 9 + rnd.uniform(-0.2, 0.2)
        track(c, cx, cy, ang, rnd.uniform(30, 90), rnd.randint(60, 110), c.p["trk"][k % 6], bubbles=True,
              curl=rnd.choice((-1, 1)))
    for k in range(3):                                 # the atom
        c.ellipse(cx, cy, 34, 11, mix(c.col("cyan"), c.p["bg"], 0.2 * k), rot=k * math.pi / 3)
    for k, (dx, dy) in enumerate(((0, -4), (3.6, 2.2), (-3.6, 2.2))):
        c.disc(cx + dx, cy + dy, 3.2, c.p["trk"][k])
    for k in range(3):
        a = 0.6 + k * 2.1
        c.disc(cx + 34 * math.cos(a) * math.cos(k * math.pi / 3) - 11 * math.sin(a) * math.sin(k * math.pi / 3),
               cy + 34 * math.cos(a) * math.sin(k * math.pi / 3) + 11 * math.sin(a) * math.cos(k * math.pi / 3), 2, "gold")
    c.text(120, 52, "SKIFF", "text", "L", "ms")
    c.text(120, 176, NAME, "cyan", "M", "ms")
    c.text(120, 222, "ON FELUCCA 1.1.5", "mid", "S", "ms")


def a_scope(c):                                        # HOME's scope: the sound as an event display
    header(c, "")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "355", "HZ", 0.62), ("RES", "79", "%", 0.79), ("ATTACK", "1.0", "MS", 0.1),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f)
    panel(c)
    cx, cy = 120, 146
    for r, col in ((22, "line"), (36, "line"), (50, "dim")):
        c.ellipse(cx, cy, r, r, col, n=96)
    wave = [12000 * math.sin(i / 100 * 2 * math.pi) + 4500 * math.sin(i / 50 * 2 * math.pi + 0.7) for i in range(200)]
    pts = []
    for k in range(97):                                # the wave wrapped round the detector: its radius the sound
        a = 2 * math.pi * k / 96 - math.pi / 2
        r = 36 + wave[k * 2] / 17000 * 12
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    c.poly(pts, "cyan", 2)
    for k in range(0, 96, 4):                          # the calorimeter's towers outside it: how loud there
        a = 2 * math.pi * k / 96 - math.pi / 2
        e = abs(wave[k * 2]) / 17000
        for s in range(int(1 + e * 7)):
            r = 54 + s * 3
            c.pset(round(cx + r * math.cos(a)), round(cy + r * math.sin(a)), mix(c.col("gold"), c.col("red"), s / 8))
            c.pset(round(cx + r * math.cos(a + 0.03)), round(cy + r * math.sin(a + 0.03)), mix(c.col("gold"), c.col("red"), s / 8))
    burst(c, cx, cy, n=6, seed=9, rmax=18)
    footer(c, "HOLD HOME: SHIFT", "")


def a_roll(c):                                         # a SEQ page: the notes bubble-chamber tracks
    header(c, "ROLL", play=False)
    for k, (l, v, u, f) in enumerate([("STEP", "5", "/16", None), ("NOTE", "F3", "+3", None), ("TIME", "NOTE", "", None),
                                      ("FLAG", "-", "", None)]):
        card(c, k, l, v, u, f, hot=k == 1)
    panel(c)
    for r in range(15):
        y = 82 + r * 8
        blk = r % 12 in (1, 3, 6, 8, 10)
        c.rect(10, y, 8, 7, "line" if blk else "dim")
        if not blk:
            c.rect(22, y, 210, 7, mix(c.col("surf"), c.col("cyan"), 0.04))
    for b in range(17):
        x = 22 + b * 13
        for yy in range(82, 202, 2):
            c.pset(x, yy, "dim" if b % 4 == 0 else "line")
    notes = [(0, 3, 2), (2, 8, 1), (4, 3, 2), (4, 5, 2), (4, 8, 2), (7, 1, 1), (8, 5, 2), (10, 3, 1), (12, 8, 3), (12, 10, 3)]
    for (s, row, ln) in notes:
        x, y = 23 + s * 13, 82 + (14 - row) * 8 + 3
        col = c.col("gold") if s == 4 else c.col("cyan")
        c.disc(x + 1, y, 2, col)                       # the vertex where it starts
        for xx in range(x + 4, x + ln * 13 - 1, 2):     # its bubbles, thinning
            c.pset(xx, y, mix(col, c.p["surf"], 0.5 * (xx - x) / (ln * 13)))
            c.pset(xx, y + 1, mix(col, c.p["surf"], 0.75))
    x = 22 + 4 * 13
    c.corners(x - 1, 79, 16, 126, "gold", 5)
    c.text(10, 214, "C4", "dim", "S", "ls")
    c.text(232, 214, "A MIN", "mid", "S", "rs")
    footer(c, "ANALOG  ACID", "2/7", 0)


def a_parts(c):
    c.rect(0, 0, W, H, "bg")
    c.text(6, 16, "THE MOTIFS", "mid", "S", "ls")
    card(c, 0, "CUTOFF", "355", "HZ", 0.6)
    nucleus(c, 110, 50, "cyan", r=16)
    hazard(c, 180, 50, 14, "gold")
    burst(c, 44, 118, n=8, seed=4, rmax=30)
    dots_gauge(c, 100, 112, 120, 0.7, "cyan")
    for k in range(6):
        track(c, 14 + k * 36, 172, -1.2, 26, 50, c.p["trk"][k], bubbles=True)
    c.text(6, 196, "TRACKS  NUCLEI  DECAYS  HAZARD", "dim", "S", "ls")
    c.text(6, 212, "R G B + ANTI: C M Y", "dim", "S", "ls")
    for k in range(6):
        c.disc(140 + k * 14, 208, 4, c.p["trk"][k])


# ---------------------------------------------------------------- B LAB (an instrument's readout)
def b_home(c):
    header(c, NAME + " 01")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "355", "HZ", 0.62), ("RES", "79", "%", 0.79), ("ATTACK", "1.0", "MS", 0.1),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        x = 3 + 59 * k
        c.corners(x, 27, 57, 46, "cyan" if k == 0 else "dim")
        c.text(x + 4, 40, l, "mid", "S", "ls")
        c.text(x + 4, 64, v, "cyan" if k == 0 else "text", "V", "ls")
        c.text(x + 53, 64, u, "dim", "S", "rs")
        for t in range(0, 48, 4):
            c.rect(x + 4 + t, 68, 1, 3 if t % 16 == 0 else 1, "cyan" if t < 48 * f else "line")
    y = 77
    for k in range(6):
        big = k == 2
        h = 30 if big else 18
        c.corners(3, y, 234, h, "cyan" if big else "line", 4)
        c.text(9, y + (22 if big else 14), str(k + 1), "cyan" if big else "mid", "M" if big else "S", "ls")
        c.text(26, y + (19 if big else 14), TRACKS[k][0], "text" if big else "mid", "S", "ls")
        for j, on in enumerate(STEPS[k]):
            cx = 98 + j * 8 + (j // 4) * 2 + 3
            cy = y + h // 2
            if on == "1":
                c.line(cx, cy - (5 if big else 3), cx, cy + (5 if big else 3), "cyan" if big else "text")
            else:
                c.pset(cx, cy, "line")
        y += h + 3
    c.line(160, 77, 160, 215, "cyan")
    c.text(162, 86, "T 1.2.3", "cyan", "S", "ls")
    footer(c, "HOLD HOME: SHIFT", "")


def b_env(c):
    header(c, "ENV")
    for k, (l, v) in enumerate([("ATTACK", "1.0"), ("DECAY", "54"), ("SUSTAIN", "16"), ("RELEASE", "8.8")]):
        x = 3 + 59 * k
        c.corners(x, 27, 57, 46, "cyan" if k == 2 else "dim")
        c.text(x + 4, 40, l, "mid", "S", "ls")
        c.text(x + 4, 64, v, "cyan" if k == 2 else "text", "V", "ls")
    ox, oy = 26, 84
    pts = [(ox + x * 0.95, oy + y) for x, y in adsr_pts()]
    c.line(ox - 4, oy, ox - 4, oy + 122, "dim")
    c.line(ox - 4, oy + 122, 232, oy + 122, "dim")
    for t in range(0, 210, 20):
        c.line(ox + t, oy + 122, ox + t, oy + 125, "dim")
    for t in range(0, 121, 30):
        c.line(ox - 7, oy + t, ox - 4, oy + t, "dim")
    c.poly(pts, "cyan", 1)
    for (x, y) in pts[1:4]:
        c.line(x - 3, y, x + 3, y, "text")
        c.line(x, y - 3, x, y + 3, "text")
    c.text(pts[1][0] + 8, pts[1][1] + 4, "T1/2 12 MS", "mid", "S", "ls")
    c.text(pts[3][0] - 2, pts[3][1] - 8, "T1/2 6 MS", "mid", "S", "ls")
    c.text(4, oy + 4, "1.0", "dim", "S", "la")
    footer(c, "ANALOG  ACID", "1/2", 0)


def b_mixer(c):
    header(c, "MIXER", play=False)
    lv = [-6, -14, -24, -1, -6, -9]
    for k in range(6):
        x0 = 4 + 39 * k
        sel = k == 4
        c.corners(x0, 30, 36, 186, "cyan" if sel else "line", 5)
        c.text(x0 + 5, 52, str(k + 1), "cyan" if sel else "text", "V", "ls")
        c.text(x0 + 5, 66, TRACKS[k][0].split()[0][:5], "mid", "S", "ls")
        n = 0 if k == 2 else round(26 * (40 + lv[k]) / 40)
        for s in range(26):
            yy = 190 - s * 4
            c.rect(x0 + 10, yy, 16, 1, ("cyan" if sel else "text") if s < n else "line")
        c.text(x0 + 18, 206, "OFF" if k == 2 else str(lv[k]), "cyan" if sel else "text", "M", "ms")


SCREENS = [
    ("a_home", A, a_home, "A COLLIDER · HOME: each lane a beam pipe, a note a bunch of particles (played: spent rings); the playhead the beam line, a collision on the selected lane; cards the periodic table's cells"),
    ("a_env", A, a_env, "A · ENV: a Monte Carlo fill under the curve; its points nuclei, the one turned gold; the half-lives written on it"),
    ("a_lfo", A, a_lfo, "A · LFO: the orbit and its projection: the electron's height drawn out as the wave"),
    ("a_mixer", A, a_mixer, "A · MIXER: each level a calorimeter tower of cells; a muted track dark matter (there, but nothing shows)"),
    ("a_delay", A, a_delay, "A · DELAY: the echoes a decay chain, each nucleus smaller, on the exponential they follow; its half-life"),
    ("a_dialog", A, a_dialog, "A · a dialog: what can't be undone under the radiation sign; CLEAR in red brackets"),
    ("a_menu", A, a_menu, "A · MENU: an instrument's settings, the values readouts in brackets"),
    ("a_splash", A, a_splash, "A · splash: SKIFF over an atom in a collision's tracks"),
    ("a_scope", A, a_scope, "A · HOME's scope: the sound wrapped round the detector, its loudness in the calorimeter's towers, a collision at the heart"),
    ("a_roll", A, a_roll, "A · a SEQ page (ROLL): the notes bubble-chamber tracks from their vertex; the cursor in brackets"),
    ("a_parts", A, a_parts, "A · the motifs: collisions, nuclei, the hazard sign, curling tracks in the six charges (R G B and anti C M Y), the cell, the energy-level gauge"),
    ("b_home", B, b_home, "B LAB · HOME: an instrument's readout, cyan on black, bracket corners, ticks for gauges"),
    ("b_env", B, b_env, "B · ENV: a plot with axes, ticks and the half-lives"),
    ("b_mixer", B, b_mixer, "B · MIXER: hairline level bars, the selected one cyan"),
]

if __name__ == "__main__":
    shots = []
    for name, pal, fn, cap in SCREENS:
        c = Q(pal)
        fn(c)
        c.save(name)
        shots.append((Image.open(OUT / "x2" / f"QK_{name}.png"), cap))
    cols, pad = 4, 24
    capf = ImageFont.truetype(str(FONTS / "BarlowCondensed-Medium.ttf"), 22)
    rows_n = (len(shots) + cols - 1) // cols
    sw, sh = W * 2, H * 2
    sheet = Image.new("RGB", (cols * (sw + pad) + pad, rows_n * (sh + 110) + pad), (6, 14, 22))
    g = ImageDraw.Draw(sheet)
    for i, (im, cap) in enumerate(shots):
        r, cc = divmod(i, cols)
        x, y = pad + cc * (sw + pad), pad + r * (sh + 110)
        sheet.paste(im, (x, y))
        words, line, ly = cap.split(), "", y + sh + 22
        for w_ in words:
            if g.textlength(line + " " + w_, font=capf) > sw and line:
                g.text((x, ly), line, font=capf, fill=(200, 236, 250))
                line, ly = w_, ly + 25
            else:
                line = (line + " " + w_).strip()
        g.text((x, ly), line, font=capf, fill=(200, 236, 250))
    (HERE / "mockups").mkdir(exist_ok=True)
    sheet.save(HERE / "mockups" / "quark_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/quark_sheet.png")
