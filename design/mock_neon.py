#!/usr/bin/env python3
"""Synthwave theme mockups (THEME NEON): an 80s night drive. Neon pink and cyan on a purple night; a striped
sun on a perspective grid, palms, a sports car and its light trails, chrome italic numbers, segmented dash gauges, VU
meters, sparkles, scanlines. Our own 5x7 font (mock_crypt.py's), slanted for the values. Two directions:
  A SUNSET  the full picture: sunset gradients, glass cards, chrome values, the sun and the grid behind the graphs
  B VECTOR  a vector arcade monitor: black, outlines only (cyan, pink), glow, scanlines
Everything is drawn pixel by pixel at 240 x 240 (what the panel shows), then enlarged without smoothing.
  python3 mock_neon.py        -> out/OR_<screen>.png (x1 x2 x3), mockups/neon_sheet.png
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from mock_crypt import G, C as Canvas, TRACKS, STEPS, text_w, W, H

HERE = Path(__file__).parent
NAME = "NEON"                                         # the THEME row's word (to pick: NEON, TURBO, SUNSET ..)
OUT = HERE / "out"


def mix(a, b, t):
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def ramp(stops, t):
    """a colour along a list of stops (0..1)"""
    t = min(1.0, max(0.0, t))
    n = len(stops) - 1
    k = min(n - 1, int(t * n))
    return mix(stops[k], stops[k + 1], t * n - k)


# ---------------------------------------------------------------- palettes
A = dict(bg=(12, 4, 26), surf=(30, 12, 50), surf2=(48, 20, 76), line=(74, 30, 110), dim=(118, 72, 160),
         mid=(176, 150, 220), text=(244, 236, 255), cyan=(48, 224, 255), pink=(255, 64, 176), violet=(150, 70, 255),
         orange=(255, 128, 56), yellow=(255, 222, 90), red=(255, 40, 80), ink=(16, 4, 30),
         trk=[(255, 64, 176), (48, 224, 255), (255, 222, 90), (255, 128, 56), (170, 100, 255), (80, 255, 170)])
B = dict(bg=(0, 0, 8), surf=(0, 0, 8), surf2=(6, 6, 22), line=(22, 40, 74), dim=(40, 92, 124), mid=(90, 176, 210),
         text=(190, 255, 255), cyan=(0, 255, 240), pink=(255, 20, 200), violet=(130, 70, 255), orange=(255, 130, 0),
         yellow=(255, 240, 40), red=(255, 20, 70), ink=(0, 0, 8),
         trk=[(255, 20, 200), (0, 255, 240), (255, 240, 40), (255, 130, 0), (150, 90, 255), (60, 255, 150)])
CHROME = [(255, 255, 255), (196, 232, 255), (130, 186, 255), (176, 140, 255), (255, 128, 84), (255, 184, 96),
          (255, 236, 150)]                           # sky, the horizon, the sunlit ground: 80s chrome (the horizon kept
                                                     # light: a dark one cut the 8s and the minus signs in two)
SUNSET = [(255, 232, 96), (255, 150, 60), (255, 64, 150), (170, 40, 200)]


class O(Canvas):
    def save(self, name):
        OUT.mkdir(exist_ok=True)
        self.im.save(OUT / f"OR_{name}.png")
        for z in (2, 3):
            (OUT / f"x{z}").mkdir(parents=True, exist_ok=True)
            self.im.resize((W * z, H * z), Image.NEAREST).save(OUT / f"x{z}" / f"OR_{name}.png")

    def get(self, x, y):
        return self.px[x, y] if 0 <= x < W and 0 <= y < H else self.p['bg']

    def line(self, x0, y0, x1, y1, c, w=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        e = dx + dy
        while True:
            self.rect(x0 - (w - 1) // 2, y0 - (w - 1) // 2, w, w, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * e
            if e2 >= dy:
                e += dy; x0 += sx
            if e2 <= dx:
                e += dx; y0 += sy

    def neon(self, pts, c, core='text', halo=0.6):
        """a neon tube along the points: a 3 px halo, the colour, a white-hot core where it is brightest"""
        c = self.col(c)
        h = mix(c, self.p['bg'], halo)
        for i in range(len(pts) - 1):
            self.line(*pts[i], *pts[i + 1], h, 4)
        for i in range(len(pts) - 1):
            self.line(*pts[i], *pts[i + 1], c, 2)
        if core:
            for i in range(len(pts) - 1):
                self.line(*pts[i], *pts[i + 1], mix(c, self.col(core), 0.55), 1)

    def scanlines(self, k=0.72):
        for j in range(1, H, 2):
            for i in range(W):
                r, g, b = self.px[i, j]
                self.px[i, j] = (int(r * k), int(g * k), int(b * k))

    def ftext(self, x, y, s, col=None, z=1, sp=1, grad=None, slant=False, halo=None, outline=None, shadow=None):
        """our font with effects: slanted (italic, a pixel every 3 rows), a gradient down its rows (chrome), a 1 px
        outline, a glow halo, a drop shadow"""
        rows = 7 * z
        mask = {}
        cx = x
        for ch in s:
            g = G.get(ch, G['?'])
            for j, row in enumerate(g):
                for i, v in enumerate(row):
                    if v == ' ':
                        continue
                    for dy in range(z):
                        r = j * z + dy
                        sh = (rows - 1 - r) // 3 if slant else 0
                        for dx in range(z):
                            mask[(cx + i * z + dx + sh, y + r)] = r
            cx += (len(g[0]) + sp) * z
        if shadow:
            for (px, py) in mask:
                self.pset(px + max(1, z // 2), py + max(1, z // 2), shadow)
        for ring, colr in ((2, halo), (1, outline)):
            if not colr:
                continue
            for (px, py) in mask:
                for ddx in range(-ring, ring + 1):
                    for ddy in range(-ring, ring + 1):
                        if (px + ddx, py + ddy) not in mask and (ring == 1 or abs(ddx) + abs(ddy) <= 2):
                            self.pset(px + ddx, py + ddy, colr)
        for (px, py), r in mask.items():
            self.pset(px, py, ramp(grad, r / max(1, rows - 1)) if grad else col)
        return cx - sp * z + ((rows - 1) // 3 if slant else 0)

    def ftext_r(self, x, y, s, col=None, z=1, **kw):
        w = text_w(s, z) + ((7 * z - 1) // 3 if kw.get('slant') else 0)
        return self.ftext(x - w, y, s, col, z, **kw)

    def ftext_c(self, x0, x1, y, s, col=None, z=1, **kw):
        w = text_w(s, z) + ((7 * z - 1) // 3 if kw.get('slant') else 0)
        return self.ftext((x0 + x1 - w) // 2, y, s, col, z, **kw)

    def vgrad(self, x, y, w, h, stops, stripes=False):
        """a vertical gradient; stripes: the sun's, gaps growing toward the bottom"""
        for j in range(h):
            t = j / max(1, h - 1)
            if stripes and t > 0.4 and (j % 6) < 1 + int((t - 0.4) * 7):
                continue
            self.rect(x, y + j, w, 1, ramp(stops, t))

    def hgrad(self, x, y, w, h, stops):
        for i in range(w):
            self.rect(x + i, y, 1, h, ramp(stops, i / max(1, w - 1)))


# ---------------------------------------------------------------- the motifs (ours): sun, grid, palm, car, sparkle ..
def sun(c, cx, hy, r, stops=SUNSET):
    """the striped sun: a half disc on the horizon hy, yellow to pink, its bands cut by gaps that widen downward"""
    for y in range(hy - r, hy):
        t = (y - (hy - r)) / r
        if t > 0.42 and (y % 5) < 1 + int((t - 0.42) * 6):
            continue
        hw = int(math.sqrt(max(0, r * r - (hy - y) ** 2)))
        c.rect(cx - hw, y, 2 * hw + 1, 1, ramp(stops, t))


def grid(c, x0, x1, hy, y1, col='pink', n=7, fade=True):
    """the perspective floor: rays from the vanishing point, rungs closer toward the horizon"""
    cx = (x0 + x1) // 2
    colr = c.col(col)
    for i in range(-14, 15):
        xb = cx + i * 26
        steps = max(1, y1 - hy)
        for k in range(steps + 1):
            y = hy + k
            x = round(cx + (xb - cx) * k / steps)
            if x0 <= x < x1:
                c.pset(x, y, mix(colr, c.p['bg'], 0.75 * (1 - k / steps)) if fade else colr)
    for k in range(1, n + 1):
        y = hy + round((y1 - hy) * (k / n) ** 2)
        c.rect(x0, y, x1 - x0, 1, mix(colr, c.p['bg'], 0.75 * (1 - k / n)) if fade else colr)


PALM = ["      ##  ##      ",
        "    ##########    ",
        "  ####  ##  ####  ",
        " ##    ####    ## ",
        "##    ## # ##   ##",
        "#    ##  #  ##   #",
        "    ##   #   ##   ",
        "    #    #    #   ",
        "         ##       ",
        "         ##       ",
        "        ##        ",
        "        ##        ",
        "        ##        ",
        "       ##         ",
        "       ##         ",
        "       ##         ",
        "       ##         ",
        "      ####        "]
CAR = ["      ######      ",               # side view, facing right: T tail light, H headlight, . glass, O wheels
       "    ##.. ...##    ",
       "  ##############  ",
       "T################H",
       " ###OO######OO### ",
       "    OO      OO    "]
SPARK = ["   #   ", "   #   ", "  #W#  ", "##WWW##", "  #W#  ", "   #   ", "   #   "]
BOLT = ["   ##", "  ## ", " ##  ", "#####", "  ## ", " ##  ", "##   "]
TAPE = ["##############",                  # a cassette: the window, its two reels
        "#............#",
        "#.##......##.#",
        "#.#O#....#O#.#",
        "#.##......##.#",
        "#............#",
        "##############"]


def palm(c, x, y, col='ink', z=1):
    c.sprite(x, y, PALM, {'#': col}, z)


def car(c, x, y, body='pink', z=1, trail=60, outline=False):
    """the car and its light trails behind it: the tail light's red, a cyan streak, fading (outline: in a dark 1 px
    edge, to show on a lit band)"""
    if outline:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            c.sprite(x + dx, y + dy, CAR, {k: 'ink' for k in '#.THO'}, z)
    for i in range(trail):
        t = i / trail
        c.rect(x - 1 - i * z, y + 3 * z, z, z, mix(c.col('red'), c.p['bg'], t))
        c.rect(x - 1 - i * z, y + 4 * z + 1, z, 1, mix(c.col('cyan'), c.p['bg'], min(1, t * 1.4)))
    c.sprite(x, y, CAR, {'#': body, '.': 'cyan', 'T': 'red', 'H': 'yellow', 'O': 'ink'}, z)


def spark(c, x, y, col='cyan', z=1):
    c.sprite(x - 3 * z, y - 3 * z, SPARK, {'#': col, 'W': 'text'}, z)


def dash_gauge(c, x, y, w, frac, hot=False):
    """a card's gauge as an 80s dash bargraph: slanted segments, cyan to violet to pink as they climb"""
    n = (w - 2) // 4
    lit = round(n * frac)
    for k in range(n):
        col = ('ink' if hot else ramp([c.col('cyan'), c.col('violet'), c.col('pink')], k / max(1, n - 1))) \
            if k < lit else ('surf2' if not hot else mix(c.col('ink'), c.col('orange'), 0.6))
        for r in range(5):
            c.rect(x + k * 4 + (4 - r) // 2, y + r, 3, 1, col)


def vu(c, x, y, w, h, frac, seg=4, peak=None):
    """a VU column: segments from the foot, cyan, violet, pink, yellow at the top; a peak segment held white"""
    n = h // seg
    lit = round(n * frac)
    for k in range(n):
        yy = y + h - (k + 1) * seg
        col = ramp([c.col('cyan'), c.col('violet'), c.col('pink'), c.col('yellow')], k / max(1, n - 1)) \
            if k < lit else c.col('surf2')
        c.rect(x, yy, w, seg - 1, col)
    if peak is not None and peak > lit:
        c.rect(x, y + h - peak * seg, w, seg - 1, 'text')


def noise(c, x, y, w, h, seed=7):
    """VHS snow: no signal (a muted track)"""
    s = seed
    for j in range(y, y + h):
        for i in range(x, x + w):
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            v = (s >> 16) & 255
            if v > 150:
                c.pset(i, j, mix(c.p['bg'], c.col('mid'), v / 255 * 0.6))


# ---------------------------------------------------------------- the shared parts of a screen
def header(c, title, play=True, rec=False, mark=None):
    c.rect(0, 0, W, 24, 'bg')
    if rec:
        for d, colr in ((5, mix(c.col('red'), c.p['bg'], 0.6)), (3, 'red')):
            for yy in range(-d, d + 1):
                hw = int(math.sqrt(d * d - yy * yy))
                c.rect(8 - hw, 10 + yy, 2 * hw + 1, 1, colr)
    elif play:
        c.sprite(4, 4, ["#     ", "###   ", "##### ", "######", "##### ", "###   ", "#     "],
                 {'#': mix(c.col('cyan'), c.p['bg'], 0.6)}, 1)
        c.sprite(5, 5, ["#   ", "### ", "####", "### ", "#   "], {'#': 'cyan'})
    else:
        c.rect(5, 6, 7, 7, 'mid')
    c.ftext(18, 7, "1.2", 'text')
    x = c.ftext(38, 7, "124", 'cyan', slant=True)
    c.ftext(x + 3, 7, "BPM", 'dim')
    x = c.ftext_r(235, 7, title, 'mid')
    if mark:
        c.ftext_r(235 - text_w(title) - 7, 7, mark, 'pink')
    c.hgrad(0, 21, W, 1, [c.col('pink'), c.col('violet'), c.col('cyan')])
    c.rect(0, 23, W, 1, 'line')


def footer(c, left, right, track=None):
    c.rect(0, 219, W, 21, 'bg')
    c.hgrad(0, 219, W, 1, [c.col('cyan'), c.col('violet'), c.col('pink')])
    x = 6
    if track is not None:
        x = c.ftext(6, 227, str(track + 1), c.p['trk'][track], slant=True) + 4
    c.ftext(x, 227, left, 'mid')
    c.ftext_r(234, 227, right, 'dim')


def card(c, k, label, val, unit, frac, hot=False):
    """glass: a dark tile, a lit top edge; the value 2x chrome, slanted; a dash bargraph. Hot: a sunset, ink on it"""
    x, y, w, h = 3 + 59 * k, 27, 57, 46
    if hot:
        c.vgrad(x, y, w, h, [c.col('yellow'), c.col('orange'), c.col('pink')])
        c.frame(x, y, w, h, 'text')
    else:
        c.rect(x, y, w, h, 'surf')
        c.rect(x, y, w, 1, 'surf2')
        c.rect(x + 1, y + 1, w - 2, 1, mix(c.col('surf2'), c.col('violet'), 0.3))
        c.rect(x, y + h - 1, w, 1, 'line')
    if not label:
        return
    c.ftext(x + 4, y + 5, label, 'ink' if hot else 'mid')
    if hot:
        c.ftext(x + 4, y + 15, val, 'ink', z=2, slant=True)
    else:
        c.ftext(x + 4, y + 15, val, z=2, slant=True, grad=CHROME, outline=c.col('ink'))
    if unit:
        c.ftext_r(x + w - 4, y + 22, unit, 'ink' if hot else 'dim')
    if frac is not None:
        dash_gauge(c, x + 4, y + 36, w - 8, frac, hot)


def panel(c, y0=76, y1=216, floor=None, sun_r=0):
    """the night: the panel dark; a grid floor from `floor` down, a sun on its horizon"""
    c.rect(3, y0, 234, y1 - y0, 'surf')
    c.vgrad(3, y0, 234, y1 - y0, [c.col('ink'), c.col('surf')])
    if floor:
        if sun_r:
            sun(c, 120, floor, sun_r, [mix(s, c.p['surf'], 0.55) for s in SUNSET])
        grid(c, 3, 237, floor, y1, 'violet')
    c.rect(3, y0, 234, 1, 'line')


# ---------------------------------------------------------------- A SUNSET
def a_home(c):
    header(c, NAME + " 01", rec=True, mark="B")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "355", "HZ", 0.62), ("RES", "79", "%", 0.79), ("ATTACK", "1.0", "MS", 0.1),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f, hot=k == 0)
    sel, y, ph = 2, 77, 4 * 8 + 98 + 2 * 1 + 26
    for k in range(6):
        col = c.p['trk'][k]
        big = k == sel
        h = 30 if big else 18
        if big:                                       # the selected lane a neon sign: its colour into violet, lit rows
            c.hgrad(3, y, 234, h, [col, mix(col, c.col('violet'), 0.7)])
            for j in range(y + 1, y + h, 2):
                for i in range(3, 237):
                    r, g, b = c.px[i, j]
                    c.px[i, j] = (r * 7 // 8, g * 7 // 8, b * 7 // 8)
            c.ftext(8, y + 8, str(k + 1), 'ink', z=2, slant=True)
            c.ftext(26, y + 6, TRACKS[k][0], 'ink')
            c.ftext(26, y + 17, TRACKS[k][1], 'ink')
        else:                                         # the others: asphalt, the lane's paint between them
            c.rect(3, y, 234, h, 'surf')
            c.ftext(9, y + 6, str(k + 1), col, slant=True)
            c.ftext(26, y + 6, TRACKS[k][0], 'text' if k != 1 else 'dim')
        for j, on in enumerate(STEPS[k]):
            cx = 98 + j * 8 + (j // 4) * 2
            ch = 12 if big else 8
            cy = y + (h - ch) // 2
            if on == '1':
                if big:
                    c.rect(cx, cy, 6, ch, 'ink')
                else:                                 # a lit tube: halo, colour, a hot top
                    c.rect(cx - 1, cy - 1, 8, ch + 2, mix(col, c.p['surf'], 0.65))
                    c.rect(cx, cy, 6, ch, col)
                    c.rect(cx + 1, cy + 1, 4, 1, mix(col, c.col('text'), 0.6))
            else:
                c.rect(cx + 2, cy + ch // 2, 2, 1, 'ink' if big else 'line')
        y += h + 3
        if k < 5:
            for i in range(6, 234, 10):               # the lane markings
                c.rect(i, y - 2, 5, 1, mix(c.col('yellow'), c.p['bg'], 0.65))
    c.rect(ph - 1, 77, 3, 140, mix(c.col('cyan'), c.p['bg'], 0.7))   # the playhead: a laser
    c.rect(ph, 77, 1, 140, 'cyan')
    car(c, ph - 4, 77 + 2 * 21 + 9, 'text', z=2, trail=30, outline=True)   # .. and on the selected lane the car, its trails behind it
    footer(c, "HOLD HOME: SHIFT", "")


def adsr_pts():
    return [(10, 120), (26, 12), (60, 58), (150, 58), (210, 120)]


def a_env(c):
    header(c, "ENV")
    for k, (l, v, u, f) in enumerate([("ATTACK", "1.0", "MS", 0.1), ("DECAY", "54", "MS", 0.4), ("SUSTAIN", "16", "%", 0.16),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f, hot=k == 2)
    panel(c)
    ox, oy = 12, 84
    pts = [(ox + x, oy + y) for x, y in adsr_pts()]
    base = oy + 120
    for i in range(len(pts) - 1):                     # under the curve: the sun's bands, yellow at the top to pink
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        for x in range(x0, x1 + 1):
            yy = round(y0 + (y1 - y0) * (x - x0) / max(1, x1 - x0))
            for y in range(yy + 2, base):
                t = (y - (oy + 10)) / (base - oy - 10)
                if t > 0.35 and (y % 5) < 1 + int((t - 0.35) * 6):
                    continue
                c.pset(x, y, mix(ramp(SUNSET, t), c.p['surf'], 0.35))
    grid(c, 3, 237, base, 216, 'pink', n=3)
    c.neon(pts, 'cyan')
    for k, (x, y) in enumerate(pts[1:4]):             # the points: sparkles, the one turned big and white
        spark(c, x, y, 'pink' if k == 2 else 'cyan', z=2 if k == 2 else 1)
    footer(c, "ANALOG  ACID", "1/2", track=0)


def a_lfo(c):
    header(c, "LFO")
    for k, (l, v, u, f) in enumerate([("RATE", "1.9", "HZ", 0.4), ("WAVE", "SINE", "", None), ("PHASE", "0", "", 0.0),
                                      ("FADE", "0", "MS", 0.0)]):
        card(c, k, l, v, u, f, hot=k == 0)
    panel(c, floor=176, sun_r=0)
    cy, a, now = 130, 38, 150
    pts = [(14 + i, round(cy - a * math.sin(i / 212 * 2 * math.pi * 2))) for i in range(0, 213)]
    for x, y in pts[::4]:                             # vector mountains: the wave a ridge, wireframe under it
        c.rect(x, y + 3, 1, 176 - y - 3, mix(c.col('violet'), c.p['surf'], 0.55))
    c.neon(pts[now:], 'violet', core=None, halo=0.8)  # still to come: dim
    c.neon(pts[:now + 1], 'pink')
    for i in range(36):                               # the light trail behind the light: white-hot, fading
        x, y = pts[now - i]
        c.rect(x, y - 1, 1, 3, mix(c.col('text'), c.col('pink'), i / 36))
    spark(c, *pts[now], 'cyan', z=2)
    footer(c, "ANALOG  ACID", "1/3", track=0)


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
        col = c.p['trk'][k]
        if sel:
            c.vgrad(x0, y0, 36, 138, [col, mix(col, c.col('violet'), 0.75)])
        else:
            c.rect(x0, y0, 36, 138, 'surf')
            c.rect(x0, y0, 36, 1, 'surf2')
        c.ftext(x0 + 4, y0 + 4, str(k + 1), 'ink' if sel else col, z=2, slant=True)
        c.ftext(x0 + 4, y0 + 22, TRACKS[k][0].split()[0][:5], 'ink' if sel else ('dim' if muted[k] else 'text'))
        if muted[k]:                                  # no signal
            noise(c, x0 + 3, y0 + 34, 30, 76, seed=k + 3)
            c.ftext_c(x0, x0 + 36, y0 + 68, "MUTE", 'pink', halo=c.p['bg'])
        else:
            vu(c, x0 + 8, y0 + 34, 9, 76, (40 + lv[k]) / 40, peak=round(19 * (44 + lv[k]) / 40))
            vu(c, x0 + 19, y0 + 34, 9, 76, (37 + lv[k]) / 40)
        c.ftext_c(x0, x0 + 36, y0 + 118, "OFF" if muted[k] else str(lv[k]), 'ink' if sel else 'text')
        c.ftext_c(x0, x0 + 36, y0 + 128, ["L31", "R37", "C", "L6", "L31", "R20"][k], 'ink' if sel else 'dim')
    footer(c, "SAMPLE  PIANO", "1/5", track=4)


def a_fx(c):
    header(c, "FX HOLD")
    for k, (l, v, u, f) in enumerate([("FILTER", "40", "LP", 0.5), ("CRUSH", "25", "%", 0.25), ("THROW", "OFF", "", None),
                                      ("DEPTH", "70", "%", 0.7)]):
        card(c, k, l, v, u, f, hot=k == 0)
    c.rect(0, 76, W, 143, 'bg')
    names = [("F", "1/8"), ("G", "1/16"), ("A", "1/32"), ("B", "RVRS"), ("C", "LOW"),
             ("D", "HIGH"), ("E", "STOP"), ("F", "FREEZE"), ("G", "UP"), ("A", "DOWN")]
    ic = [["#####", "#   #", "# # #", "#   #", "#####"]] * 3 + [
        ["  # #", " # # ", "# #  ", " # # ", "  # #"], ["###  ", "   # ", "    #", "    #", "    #"],
        ["    #", "    #", "   # ", "###  ", "     "], ["## ##", "## ##", "## ##", "## ##", "## ##"],
        ["# # #", " ### ", "#####", " ### ", "# # #"], ["  #  ", " ### ", "# # #", "  #  ", "  #  "],
        ["  #  ", "  #  ", "# # #", " ### ", "  #  "]]
    for i, (key, nm) in enumerate(names):
        x0, y0 = 4 + 47 * (i % 5), 80 + 40 * (i // 5)
        on = i in (1, 4)
        if on:
            c.vgrad(x0, y0, 44, 36, [c.col('cyan'), c.col('violet')])
        else:
            c.rect(x0, y0, 44, 36, 'surf')
            c.rect(x0, y0, 44, 1, 'surf2')
        c.ftext(x0 + 3, y0 + 3, key, 'ink' if on else 'dim')
        c.ftext_c(x0, x0 + 44, y0 + 27, nm, 'ink' if on else 'text')
        if not on:                                    # the icon a neon sign: its glow first
            for dx in (-1, 1):
                c.sprite(x0 + 15 + dx, y0 + 8, ic[i], {'#': mix(c.col('pink'), c.p['surf'], 0.6)}, z=3)
        c.sprite(x0 + 15, y0 + 8, ic[i], {'#': 'ink' if on else 'pink'}, z=3)
    for k in range(6):                                # the cuts on the black keys: a bolt (held: lit)
        x0, y0 = 4 + 39 * k, 168
        held = k == 1
        if held:
            c.vgrad(x0, y0, 36, 22, [c.col('pink'), c.col('violet')])
        else:
            c.rect(x0, y0, 36, 22, 'surf')
        c.ftext(x0 + 3, y0 + 8, ["F#", "G#", "A#", "C#", "D#", "F#"][k], 'ink' if held else 'dim')
        c.sprite(x0 + 16, y0 + 7, BOLT, {'#': 'yellow' if held else 'line'})
        c.ftext_r(x0 + 33, y0 + 8, str(k + 1), 'ink' if held else c.p['trk'][k], slant=True)
    footer(c, "KEYS: EFFECTS", "K1-4: MACROS")


def a_perform(c):
    header(c, "PERFORM BAR")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "+12", "", 0.7), ("REVERB", "+0", "", 0.5), ("DELAY", "+0", "", 0.5),
                                      ("DIST", "+0", "", 0.5)]):
        card(c, k, l, v, u, f)
    c.rect(0, 76, W, 143, 'bg')
    kept = [[0, 2, 15], [0, 1, 2], [0, 1], [0, 1, 2, 3], [0, 1], [0, 1, 2, 3]]
    cur, nxt = [2, 1, 0, 3, 0, 2], [5, None, None, None, 1, None]
    for r in range(7):
        y = 79 + 19 * r
        if r == 6:
            c.ftext(5, y + 5, "SCN", 'dim')
            for p in range(16):
                x = 28 + 13 * p
                if p in (0, 4):
                    c.frame(x, y + 1, 11, 14, 'cyan')
                    c.ftext_c(x, x + 11, y + 5, str(p + 1), 'cyan')
                else:
                    c.pset(x + 5, y + 8, 'line')
            break
        col, band = c.p['trk'][r], r == 4
        if band:
            c.hgrad(3, y, 234, 17, [col, mix(col, c.col('violet'), 0.7)])
        if r == 1:
            noise(c, 17, y + 1, 220, 15, seed=11)
        c.ftext(5, y + 5, str(r + 1), 'ink' if band else col, slant=True)
        for p in range(16):
            x = 17 + 13 * p
            L = "ABCDEFGHIJKLMNOP"[p]
            if p == nxt[r]:                           # the next: a neon outline, glowing
                c.frame(x - 1, y, 13, 17, mix(col, c.p['bg'], 0.6) if not band else 'ink')
                c.frame(x, y + 1, 11, 15, 'ink' if band else col)
                c.ftext_c(x, x + 11, y + 5, L, 'ink' if band else col)
            elif p == cur[r]:
                c.rect(x, y + 1, 11, 15, 'ink' if band else col)
                c.ftext_c(x, x + 11, y + 5, L, col if band else 'ink')
            elif p in kept[r]:
                c.ftext_c(x, x + 11, y + 5, L, 'ink' if band else 'mid')
            else:
                c.pset(x + 5, y + 8, 'ink' if band else 'line')
        if r == 1:                                    # a muted track: no signal, its row in snow (under its letters)
            c.ftext(206, y + 5, "MUTE", 'pink', halo=c.p['bg'])
    footer(c, "WHITE: PATTERN", "BLACK: MUTE")


def a_delay(c):                                       # a V1 graph: the echoes run off to the horizon, ghosting
    header(c, "DELAY")
    for k, (l, v, u, f) in enumerate([("TIME", "1/8", "", 0.3), ("FEEDBACK", "47", "%", 0.47), ("COLOR", "55", "%", 0.55),
                                      ("MIX", "71", "%", 0.71)]):
        card(c, k, l, v, u, f, hot=k == 1)
    panel(c, floor=110, sun_r=26)
    x, lvl = 26.0, 1.0
    for i in range(8):
        if lvl < 0.03:
            break
        d = 1 - 0.09 * i                              # further down the road: shorter, closer together, nearer the horizon
        h = round(86 * lvl * d)
        foot = round(206 - 92 * (1 - d))
        xi = round(x)
        g = i                                         # the VHS ghost grows: cyan left, pink right
        c.rect(xi - g, foot - h, 4, h, mix(c.col('cyan'), c.p['surf'], 0.3))
        c.rect(xi + g, foot - h, 4, h, mix(c.col('pink'), c.p['surf'], 0.3))
        c.rect(xi, foot - h, 4, h, 'text' if i == 0 else mix(c.col('text'), c.col('violet'), 0.3))
        x += 30 * d
        lvl *= 0.47
    c.ftext(12, 82, "DRY", 'mid')
    footer(c, "ANALOG  ACID", "2/5", track=0)


def a_dialog(c):
    a_home(c)
    for j in range(24, 219):                          # the page under it, darkened, every other line out (a VHS pause)
        for i in range(W):
            r, g, b = c.px[i, j]
            k = 3 if j % 2 else 2
            c.px[i, j] = (r * k // 8, g * k // 8, b * k // 8)
    x0, y0, w, h = 20, 62, 200, 116
    c.rect(x0, y0, w, h, 'bg')
    c.vgrad(x0, y0, w, h, [c.col('ink'), c.col('surf')])
    c.frame(x0 - 1, y0 - 1, w + 2, h + 2, mix(c.col('cyan'), c.p['bg'], 0.6))
    c.frame(x0, y0, w, h, 'cyan')
    c.frame(x0 + 3, y0 + 3, w - 6, h - 6, 'pink')
    spark(c, x0 + w // 2, y0 + 14, 'pink', z=1)
    c.ftext_c(x0, x0 + w, y0 + 26, "CLEAR T3 PATTERN?", 'text', halo=mix(c.col('violet'), c.p['bg'], 0.5))
    c.ftext_c(x0, x0 + w, y0 + 40, "16 STEPS, 9 NOTES", 'mid')
    c.ftext_c(x0, x0 + w, y0 + 52, "HOLD SAVE: UNDO", 'dim')
    bx = x0 + 14
    c.vgrad(bx, y0 + 68, 78, 22, [c.col('cyan'), mix(c.col('cyan'), c.col('violet'), 0.6)])
    c.ftext_c(bx, bx + 78, y0 + 76, "CANCEL", 'ink')
    c.ftext_c(bx, bx + 78, y0 + 96, "OCT-", 'dim')
    bx = x0 + w - 14 - 78
    c.frame(bx - 1, y0 + 67, 80, 24, mix(c.col('red'), c.p['bg'], 0.6))
    c.frame(bx, y0 + 68, 78, 22, 'red')
    c.ftext_c(bx, bx + 78, y0 + 76, "CLEAR", 'red')
    c.ftext_c(bx, bx + 78, y0 + 96, "OCT+", 'dim')


def a_menu(c):                                        # the menu as an arcade's high score table
    c.rect(0, 0, W, H, 'bg')
    c.ftext(6, 5, "MENU", z=2, slant=True, grad=CHROME, outline=c.col('ink'))
    c.ftext_r(235, 8, "HOME: CLOSE", 'dim')
    c.hgrad(0, 22, W, 1, [c.col('pink'), c.col('violet'), c.col('cyan')])
    x = 8
    for i, t in enumerate(["DISPLAY", "CONTROL", "AUDIO", "SYSTEM"]):
        on = i == 0
        tw = text_w(t) + 10
        if on:
            c.hgrad(x, 29, tw, 13, [c.col('pink'), c.col('violet')])
        else:
            c.frame(x, 29, tw, 13, 'line')
        c.ftext(x + 5, 32, t, 'ink' if on else 'dim')
        x += tw + 4
    rows = [("THEME", NAME), ("LARGE", "OFF"), ("ANIM", "ON"), ("LEDS", "INV"), ("SCREEN OFF", "30 MIN"), ("HINTS", "ON")]
    for i, (n, v) in enumerate(rows):
        y = 54 + i * 26
        sel = i == 0
        rank = ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH"][i]
        if sel:
            c.hgrad(6, y - 6, 228, 19, [c.col('pink'), c.col('violet'), mix(c.col('violet'), c.col('cyan'), 0.5)])
        c.ftext(12, y, rank, 'ink' if sel else c.p['trk'][i], slant=True)
        c.ftext(38, y, n, 'ink' if sel else 'text')
        lx0, lx1 = 38 + text_w(n) + 4, 228 - text_w(v) - 4
        for xx in range(lx0, lx1, 3):
            c.pset(xx, y + 6, 'ink' if sel else 'line')
        c.ftext_r(228, y, v, 'ink' if sel else 'cyan', slant=True)
    footer(c, "ALGO: TAB  PRESETS: ROW", "OCT-/+: VALUE")


def a_splash(c):
    c.rect(0, 0, W, H, 'bg')
    hy = 150
    c.vgrad(0, 0, W, hy, [c.col('bg'), c.col('surf'), (90, 20, 100), (200, 50, 120)])
    for i in range(40):                               # stars
        sx, sy = (i * 97) % W, (i * 53) % 90
        c.pset(sx, sy, mix(c.col('text'), c.p['bg'], (i % 4) / 5))
    sun(c, 120, hy, 56)
    c.rect(0, hy, W, H - hy, 'ink')
    grid(c, 0, W, hy, H, 'pink', n=8)
    c.rect(0, hy, W, 1, 'pink')
    palm(c, 6, hy - 50, 'ink', z=2)
    palm(c, 196, hy - 36, 'ink', z=2)
    c.ftext_c(0, W, 28, "SKIFF", z=5, slant=True, grad=CHROME, outline=c.col('ink'))
    c.ftext_c(0, W, 74, NAME, 'pink', z=2, slant=True, halo=mix(c.col('pink'), c.p['bg'], 0.55))
    car(c, 70, 196, 'pink', z=2, trail=36)
    c.ftext_c(0, W, 224, "ON FELUCCA 1.1.5", 'mid')


def a_roll(c):                                        # a SEQ page: the piano roll in neon
    header(c, "ROLL", play=False)
    for k, (l, v, u, f) in enumerate([("STEP", "5", "/16", None), ("NOTE", "F3", "+3", None), ("TIME", "NOTE", "", None),
                                      ("FLAG", "-", "", None)]):
        card(c, k, l, v, u, f, hot=k == 1)
    panel(c)
    for r in range(15):                               # the keys, the rows: the black ones darker
        y = 82 + r * 8
        blk = r % 12 in (1, 3, 6, 8, 10)
        c.rect(10, y, 8, 7, 'line' if blk else 'dim')
        c.rect(22, y, 210, 7, 'ink' if blk else 'surf')
    for b in range(17):
        x = 22 + b * 13
        c.rect(x, 82, 1, 120, 'violet' if b % 4 == 0 else 'surf2')
    notes = [(0, 3, 2), (2, 8, 1), (4, 3, 2), (4, 5, 2), (4, 8, 2), (7, 1, 1), (8, 5, 2), (10, 3, 1), (12, 8, 3), (12, 10, 3)]
    for (s, row, ln) in notes:
        x, y = 23 + s * 13, 82 + (14 - row) * 8
        sel = s == 4
        col = c.col('cyan') if sel else c.col('pink')
        c.rect(x - 1, y - 1, ln * 13 + 1, 9, mix(col, c.p['surf'], 0.6))
        c.rect(x, y, ln * 13 - 1, 7, col)
        c.rect(x + 1, y + 1, ln * 13 - 3, 1, mix(col, c.col('text'), 0.6))
    x = 22 + 4 * 13                                   # the cursor: a cyan laser column
    c.frame(x, 80, 14, 124, 'cyan')
    c.frame(x - 1, 79, 16, 126, mix(c.col('cyan'), c.p['bg'], 0.65))
    c.ftext(10, 206, "C4", 'dim')
    c.ftext_r(232, 206, "A MIN", 'mid')
    footer(c, "ANALOG  ACID", "2/7", track=0)


def a_parts(c):                                       # the motifs, to pick from
    c.rect(0, 0, W, H, 'bg')
    c.ftext(6, 6, "THE MOTIFS", 'mid')
    sun(c, 44, 70, 34)
    c.rect(4, 70, 80, 1, 'pink')
    grid(c, 4, 84, 70, 100, 'pink', n=4)
    palm(c, 96, 40, 'violet', z=2)
    car(c, 150, 60, 'pink', z=2, trail=10)
    c.ftext(6, 108, "124", z=3, slant=True, grad=CHROME, outline=c.col('ink'))
    for i, col in enumerate(['cyan', 'pink', 'yellow']):
        spark(c, 92 + i * 16, 120, col, z=1 if i else 2)
    c.sprite(146, 106, TAPE, {'#': 'mid', '.': 'surf2', 'O': 'pink'}, z=2)
    dash_gauge(c, 6, 140, 108, 0.7)
    vu(c, 130, 136, 9, 60, 0.75, peak=13)
    vu(c, 142, 136, 9, 60, 0.55)
    noise(c, 160, 136, 36, 60)
    c.ftext(168, 162, "MUTE", 'pink')
    c.neon([(6, 186), (40, 156), (70, 176), (110, 166)], 'cyan')
    c.ftext(6, 200, "SUN GRID PALM CAR TRAIL CHROME", 'dim')
    c.ftext(6, 212, "SPARK TAPE DASH VU SNOW NEON", 'dim')


# ---------------------------------------------------------------- B VECTOR (outlines on black, glow, scanlines)
def b_home(c):
    c.rect(0, 0, W, H, 'bg')
    c.ftext(18, 7, "1.2", 'cyan')
    x = c.ftext(38, 7, "124", 'pink', slant=True)
    c.ftext(x + 3, 7, "BPM", 'dim')
    c.sprite(5, 5, ["#   ", "##  ", "# # ", "#  #", "# # ", "##  ", "#   "], {'#': 'cyan'})
    c.ftext_r(235, 7, NAME + " 01", 'mid')
    c.rect(0, 21, W, 1, 'cyan')
    for k, (l, v) in enumerate([("CUTOFF", "355"), ("RES", "79"), ("ATTACK", "1.0"), ("RELEASE", "8.8")]):
        x0 = 3 + 59 * k
        c.frame(x0, 27, 57, 46, 'pink' if k == 0 else 'line')
        if k == 0:
            c.frame(x0 - 1, 26, 59, 48, mix(c.col('pink'), c.p['bg'], 0.65))
        c.ftext(x0 + 4, 32, l, 'mid')
        c.ftext(x0 + 4, 43, v, 'pink' if k == 0 else 'cyan', z=2, slant=True,
                halo=mix(c.col('pink' if k == 0 else 'cyan'), c.p['bg'], 0.75))
        for s in range(12):                           # an outline bargraph
            c.frame(x0 + 4 + s * 4, 64, 3, 4, 'cyan' if s < (9, 7, 2, 4)[k] else 'line')
    y = 77
    for k in range(6):
        col = c.p['trk'][k]
        big = k == 2
        h = 30 if big else 18
        c.frame(3, y, 234, h, col if big else 'line')
        if big:
            c.frame(2, y - 1, 236, h + 2, mix(col, c.p['bg'], 0.6))
        c.ftext(9, y + (h - 7) // 2, str(k + 1), col, slant=True)
        c.ftext(26, y + (h - 7) // 2, TRACKS[k][0], 'text' if big else 'mid')
        for j, on in enumerate(STEPS[k]):
            cx = 98 + j * 8 + (j // 4) * 2
            ch = 12 if big else 8
            cy = y + (h - ch) // 2
            if on == '1':
                c.frame(cx, cy, 6, ch, col)
                if big:
                    c.rect(cx + 2, cy + 2, 2, ch - 4, col)
            else:
                c.pset(cx + 3, cy + ch // 2, 'line')
        y += h + 3
    c.rect(161, 77, 1, 140, 'cyan')
    c.rect(160, 77, 3, 140, mix(c.col('cyan'), c.p['bg'], 0.75))
    c.rect(161, 77, 1, 140, 'cyan')
    c.rect(0, 219, W, 1, 'cyan')
    c.ftext(6, 227, "HOLD HOME: SHIFT", 'mid')
    c.scanlines()


def b_env(c):
    c.rect(0, 0, W, H, 'bg')
    c.ftext(18, 7, "1.2", 'cyan')
    x = c.ftext(38, 7, "124", 'pink', slant=True)
    c.ftext(x + 3, 7, "BPM", 'dim')
    c.ftext_r(235, 7, "ENV", 'mid')
    c.rect(0, 21, W, 1, 'cyan')
    for k, (l, v) in enumerate([("ATTACK", "1.0"), ("DECAY", "54"), ("SUSTAIN", "16"), ("RELEASE", "8.8")]):
        x0 = 3 + 59 * k
        c.frame(x0, 27, 57, 46, 'pink' if k == 2 else 'line')
        c.ftext(x0 + 4, 32, l, 'mid')
        c.ftext(x0 + 4, 43, v, 'pink' if k == 2 else 'cyan', z=2, slant=True)
    grid(c, 0, W, 120, 216, 'violet', n=6)
    ox, oy = 12, 84
    pts = [(ox + x, oy + y) for x, y in adsr_pts()]
    c.neon(pts, 'cyan')
    for k, (x, y) in enumerate(pts[1:4]):
        c.line(x - 3, y - 3, x + 3, y + 3, 'pink' if k == 2 else 'text')
        c.line(x - 3, y + 3, x + 3, y - 3, 'pink' if k == 2 else 'text')
    c.rect(0, 219, W, 1, 'cyan')
    c.ftext(6, 227, "1 ANALOG ACID", 'mid')
    c.ftext_r(234, 227, "1/2", 'dim')
    c.scanlines()


def b_mixer(c):
    c.rect(0, 0, W, H, 'bg')
    c.ftext(18, 7, "1.2", 'cyan')
    x = c.ftext(38, 7, "124", 'pink', slant=True)
    c.ftext(x + 3, 7, "BPM", 'dim')
    c.ftext_r(235, 7, "MIXER", 'mid')
    c.rect(0, 21, W, 1, 'cyan')
    lv = [-6, -14, -24, -1, -6, -9]
    for k in range(6):
        x0, y0 = 4 + 39 * k, 30
        sel = k == 4
        col = c.p['trk'][k]
        c.frame(x0, y0, 36, 186, col if sel else 'line')
        c.ftext(x0 + 4, y0 + 5, str(k + 1), col, z=2, slant=True)
        c.ftext(x0 + 4, y0 + 24, TRACKS[k][0].split()[0][:5], 'text' if sel else 'mid')
        n = 0 if k == 2 else round(24 * (40 + lv[k]) / 40)
        for s in range(24):
            yy = y0 + 160 - s * 5
            c.frame(x0 + 10, yy, 16, 4, (col if s < n else 'line'))
        if k == 2:
            c.line(x0 + 8, y0 + 46, x0 + 28, y0 + 158, 'red')
            c.line(x0 + 28, y0 + 46, x0 + 8, y0 + 158, 'red')
        c.ftext_c(x0, x0 + 36, y0 + 172, "OFF" if k == 2 else str(lv[k]), col if sel else 'text')
    c.scanlines()


SCREENS = [
    ("a_home", A, a_home, "A SUNSET · HOME: the lanes a highway (lit tubes for steps, lane paint between), the selected one a neon sign; the playhead a laser, the car on the selected lane with its light trails"),
    ("a_env", A, a_env, "A · ENV: the cyan neon curve over the sun's bands (yellow to pink, gaps widening) on a grid floor; the points sparkles, the one turned big"),
    ("a_lfo", A, a_lfo, "A · LFO: the wave a ridge of vector mountains; lit pink up to now with a white-hot light trail, dim after; a sparkle where the LFO is"),
    ("a_mixer", A, a_mixer, "A · MIXER: twin VU columns (cyan to yellow), a held peak; a muted track no signal: VHS snow"),
    ("a_fx", A, a_fx, "A · FX held: the effects as neon signs; on, a cyan-violet tile; the cuts bolts, a held one lit"),
    ("a_perform", A, a_perform, "A · PERFORM: the playing pattern lit, the next a glowing outline; a muted row snow"),
    ("a_delay", A, a_delay, "A · DELAY: the echoes run off down the road to the sun, shorter and nearer the horizon, each ghosting wider (cyan, pink)"),
    ("a_dialog", A, a_dialog, "A · a dialog: the page paused like a VHS tape; a double neon frame, CANCEL lit cyan, CLEAR in red neon"),
    ("a_menu", A, a_menu, "A · MENU: an arcade's high score table: ranks, leaders, values in cyan; the row a sunset bar"),
    ("a_splash", A, a_splash, "A · splash: SKIFF in chrome over the striped sun, palms, the grid, the car with its trails"),
    ("a_roll", A, a_roll, "A · a SEQ page (ROLL): notes lit tubes, the step's ones cyan, the cursor a laser column"),
    ("a_parts", A, a_parts, "A · the motifs, to keep or drop: sun, grid, palm, car + trails, chrome numbers, sparkles, tape, dash bargraph, VU, snow, neon"),
    ("b_home", B, b_home, "B VECTOR · HOME: an arcade vector monitor: outlines only, glow, scanlines"),
    ("b_env", B, b_env, "B · ENV: the neon curve over a full grid, its points crosses"),
    ("b_mixer", B, b_mixer, "B · MIXER: outline segments, a muted track crossed out in red"),
]

if __name__ == "__main__":
    shots = []
    for name, pal, fn, cap in SCREENS:
        c = O(pal)
        fn(c)
        c.save(name)
        shots.append((Image.open(OUT / "x2" / f"OR_{name}.png"), cap))
    cols, pad = 4, 24
    try:
        capf = ImageFont.truetype(str(HERE.parent / "assets" / "fonts" / "BarlowCondensed-Medium.ttf"), 22)
    except OSError:
        capf = ImageFont.load_default()
    rows_n = (len(shots) + cols - 1) // cols
    sw, sh = W * 2, H * 2
    sheet = Image.new("RGB", (cols * (sw + pad) + pad, rows_n * (sh + 110) + pad), (18, 8, 30))
    g = ImageDraw.Draw(sheet)
    for i, (im, cap) in enumerate(shots):
        r, cc = divmod(i, cols)
        x, y = pad + cc * (sw + pad), pad + r * (sh + 110)
        sheet.paste(im, (x, y))
        words, line, ly = cap.split(), "", y + sh + 22
        for w_ in words:
            if g.textlength(line + " " + w_, font=capf) > sw and line:
                g.text((x, ly), line, font=capf, fill=(236, 220, 255))
                line, ly = w_, ly + 25
            else:
                line = (line + " " + w_).strip()
        g.text((x, ly), line, font=capf, fill=(236, 220, 255))
    (HERE / "mockups").mkdir(exist_ok=True)
    sheet.save(HERE / "mockups" / "neon_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/neon_sheet.png")
