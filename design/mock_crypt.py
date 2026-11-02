#!/usr/bin/env python3
"""CRYPT theme mockups (U5): an old, dark, esoteric fantasy metal video game. Warm: amber, ember, bone, blood on
black-brown; graphics as ASCII art and pixel icons (skulls, snakes, torches, swords); our own 5x7 pixel font (drawn
here, no font file), 2x for the values. Two directions:
  B TORCHLIT  the warm palette, icons, dithered stone tiles, ASCII double-line borders
  A AMBER     one amber phosphor on black, ASCII art only (a roguelike on an amber terminal)
Everything is drawn pixel by pixel at 240 x 240 (what the panel shows), then enlarged without smoothing.
  python3 mock_crypt.py       -> out/CR_<screen>.png (x1 x2 x3), mockups/crypt_sheet.png
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "out"
W = H = 240

# ---------------------------------------------------------------- the 5x7 font (ours), and its sizes
G = {
    'A': [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'B': ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    'C': [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    'D': ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    'E': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    'F': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    'G': [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"],
    'H': ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'I': ["###", " # ", " # ", " # ", " # ", " # ", "###"],
    'J': ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    'K': ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    'L': ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    'M': ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    'N': ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    'O': [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'P': ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    'Q': [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    'R': ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    'S': [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    'U': ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'V': ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    'W': ["#   #", "#   #", "#   #", "# # #", "# # #", "# # #", " # # "],
    'X': ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    'Y': ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    'Z': ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    '0': [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    '1': [" # ", "## ", " # ", " # ", " # ", " # ", "###"],
    '2': [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    '3': ["#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "],
    '4': ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    '5': ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    '6': ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
    '7': ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    '8': [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    '9': [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    '.': [" ", " ", " ", " ", " ", " ", "#"],
    ',': [" ", " ", " ", " ", " ", "#", "#"],
    ':': [" ", " ", "#", " ", " ", "#", " "],
    '-': ["   ", "   ", "   ", "###", "   ", "   ", "   "],
    '+': ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    '/': ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    '%': ["##  #", "##  #", "   # ", "  #  ", " #   ", "#  ##", "#  ##"],
    '#': [" # # ", "#####", " # # ", " # # ", " # # ", "#####", " # # "],
    '!': ["#", "#", "#", "#", "#", " ", "#"],
    '?': [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "],
    '(': ["  #", " # ", "#  ", "#  ", "#  ", " # ", "  #"],
    ')': ["#  ", " # ", "  #", "  #", "  #", " # ", "#  "],
    '[': ["###", "#  ", "#  ", "#  ", "#  ", "#  ", "###"],
    ']': ["###", "  #", "  #", "  #", "  #", "  #", "###"],
    '>': ["#   ", " #  ", "  # ", "   #", "  # ", " #  ", "#   "],
    '<': ["   #", "  # ", " #  ", "#   ", " #  ", "  # ", "   #"],
    '=': ["     ", "     ", "#####", "     ", "#####", "     ", "     "],
    '_': ["     ", "     ", "     ", "     ", "     ", "     ", "#####"],
    "'": ["#", "#", " ", " ", " ", " ", " "],
    '*': ["     ", "# # #", " ### ", "#####", " ### ", "# # #", "     "],
    '~': ["     ", "     ", " #  #", "# ## ", "     ", "     ", "     "],
    '·': [" ", " ", " ", "#", " ", " ", " "],
    ' ': ["  ", "  ", "  ", "  ", "  ", "  ", "  "],
}


def gw(ch):
    return len(G.get(ch, G['?'])[0])


def text_w(s, z=1, sp=1):
    return sum((gw(c) + sp) * z for c in s) - sp * z if s else 0


# ---------------------------------------------------------------- palettes
B = dict(bg=(10, 7, 5), stone=(30, 21, 14), stone2=(42, 30, 19), line=(60, 42, 26), dim=(98, 72, 44),
         mid=(168, 128, 78), text=(236, 218, 176), amber=(255, 176, 32), ember=(232, 96, 36), blood=(176, 34, 28),
         gold=(255, 214, 96), flame=(255, 238, 150), ink=(16, 10, 6),
         trk=[(232, 100, 42), (240, 178, 52), (216, 200, 160), (186, 52, 40), (150, 150, 78), (166, 104, 140)])
A = dict(bg=(4, 3, 1), stone=(24, 16, 2), stone2=(34, 23, 3), line=(70, 46, 6), dim=(110, 72, 8),
         mid=(180, 118, 14), text=(255, 184, 40), amber=(255, 184, 40), ember=(255, 140, 20), blood=(255, 96, 16),
         gold=(255, 214, 110), flame=(255, 230, 160), ink=(4, 3, 1),
         trk=[(255, 184, 40)] * 6)


class C:
    """a 240 x 240 pixel canvas in one direction's palette"""

    def __init__(self, pal):
        self.p = pal
        self.im = Image.new("RGB", (W, H), pal['bg'])
        self.px = self.im.load()

    def col(self, c):
        return self.p.get(c, c) if isinstance(c, str) else c

    def pset(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[x, y] = self.col(c)

    def rect(self, x, y, w, h, c):
        c = self.col(c)
        for j in range(max(0, y), min(H, y + h)):
            for i in range(max(0, x), min(W, x + w)):
                self.px[i, j] = c

    def dither(self, x, y, w, h, c, lvl):
        """lvl 1..3: 25 %, 50 %, 75 % of the pixels in c (an ordered pattern: the ASCII shade blocks)"""
        c = self.col(c)
        for j in range(y, y + h):
            for i in range(x, x + w):
                on = (lvl == 2 and (i + j) % 2 == 0) or (lvl == 1 and i % 2 == 0 and j % 2 == 0) or \
                     (lvl == 3 and not (i % 2 == 1 and j % 2 == 1))
                if on and 0 <= i < W and 0 <= j < H:
                    self.px[i, j] = c

    def frame(self, x, y, w, h, c):
        self.rect(x, y, w, 1, c); self.rect(x, y + h - 1, w, 1, c)
        self.rect(x, y, 1, h, c); self.rect(x + w - 1, y, 1, h, c)

    def frame2(self, x, y, w, h, c):
        """the ASCII double line (╔═╗): two frames 2 px apart, the corners joined"""
        self.frame(x, y, w, h, c)
        self.frame(x + 2, y + 2, w - 4, h - 4, c)

    def stone(self, x, y, w, h, c1='stone', c2='stone2'):
        """a dithered stone tile: the base, a few lighter specks in a fixed pattern"""
        self.rect(x, y, w, h, c1)
        for j in range(y, y + h):
            for i in range(x, x + w):
                if (i * 7 + j * 13) % 23 == 0 or (i * 11 + j * 5) % 31 == 0:
                    self.pset(i, j, c2)

    def text(self, x, y, s, c, z=1, sp=1, shadow=None):
        for ch in s:
            g = G.get(ch, G['?'])
            for j, row in enumerate(g):
                for i, v in enumerate(row):
                    if v != ' ':
                        if shadow:
                            self.rect(x + i * z + 1, y + j * z + 1, z, z, shadow)
                        self.rect(x + i * z, y + j * z, z, z, c)
            x += (len(g[0]) + sp) * z
        return x

    def text_r(self, x, y, s, c, z=1, sp=1, shadow=None):
        return self.text(x - text_w(s, z, sp), y, s, c, z, sp, shadow)

    def text_c(self, x0, x1, y, s, c, z=1, sp=1):
        return self.text((x0 + x1 - text_w(s, z, sp)) // 2, y, s, c, z, sp)

    def sprite(self, x, y, rows, key, z=1):
        for j, row in enumerate(rows):
            for i, v in enumerate(row):
                if v in key and key[v] is not None:
                    self.rect(x + i * z, y + j * z, z, z, key[v])

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        self.im.save(OUT / f"CR_{name}.png")
        for z in (2, 3):
            (OUT / f"x{z}").mkdir(parents=True, exist_ok=True)
            self.im.resize((W * z, H * z), Image.NEAREST).save(OUT / f"x{z}" / f"CR_{name}.png")


# ---------------------------------------------------------------- the sprites (ours): skull, torch, sword, snake, ..
SKULL = ["  #####  ",
         " ####### ",
         "#########",
         "#..###..#",
         "#..###..#",
         "####.####",
         " ####### ",
         "  #.#.#  ",
         "  #####  "]
SKULL_X = ["  #####  ",          # muted: crossed eyes
           " ####### ",
           "#########",
           "#.#####.#",
           "##.###.##",
           "####.####",
           " ####### ",
           "  #.#.#  ",
           "  #####  "]
TORCH = [["  Y  ", " YYY ", " YFY ", "YFFFY", "YORFY", " ORO ", " BBB ", "  B  ", "  B  ", " BBB ", "  B  ", "  B  "],
         ["   Y ", "  YY ", " YYY ", "YFFFY", "YOFRY", " ORO ", " BBB ", "  B  ", "  B  ", " BBB ", "  B  ", "  B  "]]
TORCH_K = {'Y': 'gold', 'F': 'flame', 'O': 'amber', 'R': 'ember', 'B': 'dim'}
SWORD = ["  #           ",       # pommel, grip, crossguard: the blade drawn after it
         " ### ##       ",
         "##########    ",
         " ### ##       ",
         "  #           "]
SNAKE_HEAD = [" ## ", "####", "#.##", "####", " ## "]
CANDLE = [" Y ", " F ", "WWW", "WWW", "WWW", "WWW"]
RUNE = {  # tiny runes for the lanes' steps (3x5)
    0: ["# #", "###", "# #", "# #", "# #"], 1: ["###", "#  ", "## ", "#  ", "#  "],
    2: ["# #", "## ", "#  ", "## ", "# #"], 3: [" # ", "###", " # ", " # ", " # "]}
EYE = ["  ###  ", " #...# ", "#..#..#", " #...# ", "  ###  "]
CHALICE = ["#####", "#####", " ### ", "  #  ", "  #  ", " ### "]
DAGGER = ["  #  ", "  #  ", "  #  ", "  #  ", "#####", "  #  ", "  #  "]
MOON = [" ### ", "##   ", "#    ", "##   ", " ### "]
BAT = ["#   #", "## ##", "#####", " # # "]
SPIKE = ["#", "#", "##", "#"]


def skull(c, x, y, col, ink=None, z=1, muted=False):
    c.sprite(x, y, SKULL_X if muted else SKULL, {'#': col, '.': ink or c.p['bg']}, z)


def torch(c, x, y, frame=0, z=1):
    c.sprite(x, y, TORCH[frame], {k: c.p[v] for k, v in TORCH_K.items()}, z)


def sword_gauge(c, x, y, w, frac, col, hot=False):
    """a card's gauge as a sword: the hilt at the left, the blade to the value (its edge brighter), the rest a groove"""
    c.rect(x + 12, y + 2, w - 14, 1, 'line')
    blade = max(0, round((w - 14) * frac))
    c.rect(x + 12, y + 1, blade, 3, col)
    c.rect(x + 12, y + 1, blade, 1, 'flame' if hot else 'gold')
    if blade:
        c.pset(x + 12 + blade, y + 2, col)
    c.sprite(x, y, SWORD, {'#': 'mid'})


# ---------------------------------------------------------------- the shared parts of a screen
TRACKS = [("ACID", "ANALOG"), ("PAD", "FM6"), ("PULSE LD", "LOFI"), ("DRUM KIT", "DRUM"), ("PIANO", "SAMPLE"),
          ("BONE KIT", "DRUM-X")]
STEPS = ["1010001010100010", "1000100010001000", "0010010000100100", "1011101110111011", "1000000010000000",
         "1001001010010010"]


def header(c, title, play=True, mark=None, rec=False):
    c.rect(0, 0, W, 22, 'bg')
    if rec:
        c.sprite(4, 6, ["  #  ", " ### ", "#####", "#####", " ### "], {'#': 'blood'})   # a blood drop
    elif play:
        c.sprite(5, 6, ["#   ", "##  ", "### ", "####", "### ", "##  ", "#   "], {'#': 'amber'})
    else:
        c.rect(5, 7, 7, 7, 'mid')
    c.text(17, 7, "1.2", 'text')
    x = c.text(37, 7, "124", 'amber')
    c.text(x + 3, 7, "BPM", 'dim')
    x = c.text_r(235, 7, title, 'mid')
    if mark:
        c.text_r(235 - text_w(title) - 7, 7, mark, 'amber')
    c.rect(0, 21, W, 1, 'line')
    for i in range(0, W, 4):                       # a row of crenels under the header: a castle wall
        c.rect(i, 22, 2, 1, 'line')


def footer(c, left, right, track=None):
    c.rect(0, 220, W, 20, 'bg')
    c.rect(0, 219, W, 1, 'line')
    x = 6
    if track is not None:
        x = c.text(6, 227, str(track + 1), c.p['trk'][track], z=1) + 4
    c.text(x, 227, left, 'mid')
    c.text_r(234, 227, right, 'dim')


def card(c, k, label, val, unit, frac, hot=False, ztext=2, col=None):
    """a knob's tile: a stone slab framed in LINE; the label 1x, the value 2x (our font), the unit 1x; a sword gauge"""
    x, y, w, h = 3 + 59 * k, 27, 57, 46
    if hot:
        c.rect(x, y, w, h, 'amber')
        c.frame(x + 1, y + 1, w - 2, h - 2, 'gold')
    else:
        c.stone(x, y, w, h)
        c.frame(x, y, w, h, 'line')
    if not label:
        return
    ink = 'ink' if hot else 'mid'
    c.text(x + 4, y + 4, label, ink)
    vx = c.text(x + 4, y + 15, val, 'ink' if hot else (col or 'text'), z=ztext,
                shadow=None if hot else 'ink')
    if unit:
        c.text_r(x + w - 4, y + 22, unit, ink)
    if frac is not None:
        sword_gauge(c, x + 3, y + 37, w - 6, frac, 'ink' if hot else (col or 'amber'), hot)


def panel(c, y0=76, y1=216, frame=True):
    c.rect(3, y0, 234, y1 - y0, 'bg')
    c.stone(3, y0, 234, y1 - y0, 'stone', 'stone2')
    if frame:
        c.frame2(3, y0, 234, y1 - y0, 'line')


# ---------------------------------------------------------------- B TORCHLIT
def b_home(c):
    header(c, "CRYPT 01", rec=True, mark="B")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "355", "HZ", 0.62), ("RES", "79", "%", 0.79), ("ATTACK", "1.0", "MS", 0.1),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f, hot=k == 0)
    sel = 2
    y = 77
    for k in range(6):
        col = c.p['trk'][k]
        big = k == sel
        h = 30 if big else 18
        if big:
            c.rect(3, y, 234, h, col)
            c.dither(3, y, 234, h, tuple(max(0, v - 60) for v in col), 1)
            c.text(8, y + 8, str(k + 1), 'ink', z=2)
            c.text(26, y + 6, TRACKS[k][0], 'ink')
            c.text(26, y + 17, TRACKS[k][1], 'ink')
        else:
            c.stone(3, y, 234, h)
            c.text(9, y + 6, str(k + 1), col)
            c.text(26, y + 6, TRACKS[k][0], 'text' if k != 1 else 'dim')
        for j, on in enumerate(STEPS[k]):
            cx = 98 + j * 8 + (j // 4) * 2
            ch = 12 if big else 8
            cy = y + (h - ch) // 2
            if on == '1':
                c.rect(cx, cy, 6, ch, 'ink' if big else col)
                if not big:
                    c.rect(cx, cy, 6, 1, 'flame' if k == 0 else tuple(min(255, v + 50) for v in col))
            else:
                c.rect(cx + 2, cy + ch // 2, 2, 1, 'ink' if big else 'line')
        y += h + 3
    torch(c, 162, 79, 0)                            # the playhead: a torch over the step playing
    c.rect(164, 92, 1, 122, 'gold')
    c.dither(161, 92, 7, 122, 'amber', 1)
    footer(c, "HOLD HOME: SHIFT", "")


def adsr_pts():
    return [(10, 100), (24, 8), (56, 42), (150, 42), (210, 100)]


def b_env(c):
    header(c, "ENV")
    for k, (l, v, u, f) in enumerate([("ATTACK", "1.0", "MS", 0.1), ("DECAY", "54", "MS", 0.4), ("SUSTAIN", "16", "%", 0.16),
                                      ("RELEASE", "8.8", "MS", 0.3)]):
        card(c, k, l, v, u, f, hot=k == 2)
    panel(c)
    ox, oy = 12, 92
    pts = [(ox + x, oy + y) for x, y in adsr_pts()]
    # the envelope a ziggurat of ASCII shade blocks under the line: dark at its foot, brighter up its steps
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        for x in range(x0, x1 + 1):
            t = (x - x0) / max(1, x1 - x0)
            y = round(y0 + (y1 - y0) * t)
            yb = oy + 100
            for yy in range(y, yb):
                d = (yb - yy) / 100
                lvl = 3 if d > 0.66 else 2 if d > 0.33 else 1
                if (lvl == 3 and not (x % 2 and yy % 2)) or (lvl == 2 and (x + yy) % 2 == 0) or (lvl == 1 and x % 2 == 0 and yy % 2 == 0):
                    c.pset(x, yy, 'ember' if d > 0.5 else 'blood')
            c.rect(x, y - 1, 1, 2, 'gold')
    for k, (x, y) in enumerate(pts[1:4]):            # the points: little skulls (the one turned: bright)
        skull(c, x - 4, y - 4, 'flame' if k == 2 else 'text')
    c.text(14, 200, "A", 'dim'); c.text(34, 200, "D", 'dim'); c.text(110, 200, "S", 'amber'); c.text(200, 200, "R", 'dim')
    footer(c, "ANALOG  ACID", "1/2", track=0)


def b_lfo(c):
    header(c, "LFO")
    for k, (l, v, u, f) in enumerate([("RATE", "1.9", "HZ", 0.4), ("WAVE", "SINE", "", 0.0), ("PHASE", "0", "", 0.0),
                                      ("FADE", "0", "MS", 0.0)]):
        card(c, k, l, v, u, f if k != 1 else None, hot=k == 0)
    panel(c)
    # the wave a snake: from a thin tail it thickens; scales on its back by turns (gold, ember), its belly blood; the
    # head where the LFO is now, an eye and a forked tongue
    cy, a, n, hx = 146, 34, 200, 160
    ys = [round(cy - a * math.sin(i / n * 2 * math.pi * 1.5)) for i in range(n)]
    c.rect(18, cy, 200, 1, 'line')
    for i in range(hx):
        x, y = 18 + i, ys[i]
        r = 1 if i < 12 else 2 if i < 30 else 3
        for d in range(-r, r + 1):
            col = 'blood' if d == r else 'ember'
            if d < r and ((i // 3) + (d + 3)) % 4 == 0:
                col = 'gold'
            c.pset(x, y + d, col)
        c.pset(x, y - r - 1, 'ink')
    x, y = 18 + hx, ys[hx]
    c.sprite(x - 2, y - 4, ["  ####  ", " ###### ", "########", "##.#####", "########", " ###### ", "  ####  "],
             {'#': 'amber', '.': 'ink'})
    c.rect(x + 6, y, 4, 1, 'blood'); c.pset(x + 10, y - 1, 'blood'); c.pset(x + 10, y + 1, 'blood')
    footer(c, "ANALOG  ACID", "1/3", track=0)


def b_mixer(c):
    header(c, "MIXER", play=False)
    for k, (l, v, u, f) in enumerate([("LEVEL", "-6.0", "DB", 0.8), ("PAN", "-31", "%", 0.3), ("REVERB", "28", "%", 0.28),
                                      ("MUTE", "OFF", "", None)]):
        card(c, k, l, v, u, f, hot=False)
    lv = [-6, -14, -24, -1, -6, -9]
    muted = [False, False, True, False, False, False]
    for k in range(6):
        x0, y0 = 4 + 39 * k, 78
        sel = k == 4
        col = c.p['trk'][k]
        if sel:
            c.rect(x0, y0, 36, 138, col)
            c.dither(x0, y0, 36, 138, tuple(max(0, v - 70) for v in col), 1)
        else:
            c.stone(x0, y0, 36, 138)
            c.frame(x0, y0, 36, 138, 'line')
        ink = 'ink' if sel else None
        c.text(x0 + 4, y0 + 4, str(k + 1), ink or col, z=2)
        if muted[k]:
            skull(c, x0 + 24, y0 + 5, 'blood', muted=True)
        c.text(x0 + 4, y0 + 22, TRACKS[k][0].split()[0][:5], ink or ('dim' if muted[k] else 'text'))
        # the level a torch: its flame as tall as the level (dB), the sconce below
        h = 0 if muted[k] else round(60 * (40 + lv[k]) / 40)
        fx, fy = x0 + 13, y0 + 100
        c.rect(fx + 3, fy, 3, 14, 'dim' if not sel else 'ink')
        c.rect(fx, fy, 9, 2, 'mid' if not sel else 'ink')
        for j in range(h):
            yy = fy - 1 - j
            wdt = 7 if j < h * 0.4 else 5 if j < h * 0.75 else 3 if j < h - 2 else 1
            cx = fx + 4 - wdt // 2 + (1 if (j // 5) % 2 and j > h * 0.5 else 0)
            col2 = 'blood' if j < 3 else 'ember' if j < h * 0.35 else 'amber' if j < h * 0.7 else 'gold'
            c.rect(cx, yy, wdt, 1, col2)
            if j > 3 and (j % 3 == 0):
                c.pset(cx + wdt // 2, yy, 'flame')
        c.text_c(x0, x0 + 36, y0 + 118, "OFF" if muted[k] else str(lv[k]), ink or 'text')
        c.text_c(x0, x0 + 36, y0 + 128, ["L31", "R37", "C", "L6", "L31", "R20"][k], ink or 'dim')
    footer(c, "SAMPLE  PIANO", "1/5", track=4)


def b_fx(c):
    header(c, "FX HOLD")
    for k, (l, v, u, f) in enumerate([("FILTER", "40", "LP", 0.5), ("CRUSH", "25", "%", 0.25), ("THROW", "OFF", "", None),
                                      ("DEPTH", "70", "%", 0.7)]):
        card(c, k, l, v, u, f, hot=k == 0)
    c.rect(0, 76, W, 144, 'bg')
    names = [("F", "1/8"), ("G", "1/16"), ("A", "1/32"), ("B", "RVRS"), ("C", "LOW"),
             ("D", "HIGH"), ("E", "STOP"), ("F", "FREEZE"), ("G", "UP"), ("A", "DOWN")]
    icons = ["REP", "REP", "REP", "<<", "LP", "HP", "STP", "ICE", "UP", "DN"]
    for i, (key, nm) in enumerate(names):
        x0 = 4 + 47 * (i % 5)
        y0 = 80 + 40 * (i // 5)
        on = i in (1, 4)
        if on:
            c.rect(x0, y0, 44, 36, 'amber')
        else:
            c.stone(x0, y0, 44, 36)
            c.frame(x0, y0, 44, 36, 'line')
        c.text(x0 + 3, y0 + 3, key, 'ink' if on else 'dim')
        c.text_c(x0, x0 + 44, y0 + 26, nm, 'ink' if on else 'text')
        # ASCII-art icons for the effects
        ic = {'REP': ["#####", "#   #", "# # #", "#   #", "#####"], '<<': ["  # #", " # # ", "# #  ", " # # ", "  # #"],
              'LP': ["###  ", "   # ", "    #", "    #", "    #"], 'HP': ["    #", "    #", "   # ", "###  ", "     "],
              'STP': ["#####", "#####", "#####", "#####", "#####"], 'ICE': ["# # #", " ### ", "#####", " ### ", "# # #"],
              'UP': ["  #  ", " ### ", "# # #", "  #  ", "  #  "], 'DN': ["  #  ", "  #  ", "# # #", " ### ", "  #  "]}[icons[i]]
        c.sprite(x0 + 14, y0 + 8, ic, {'#': 'ink' if on else 'amber'}, z=3)
    for k in range(6):                                # the cuts on the black keys: a dagger (held: a skull)
        x0, y0 = 4 + 39 * k, 168
        held = k == 1
        if held:
            c.rect(x0, y0, 36, 22, 'blood')
        else:
            c.stone(x0, y0, 36, 22)
            c.frame(x0, y0, 36, 22, 'line')
        c.text(x0 + 3, y0 + 8, ["F#", "G#", "A#", "C#", "D#", "F#"][k], 'text' if held else 'dim')
        if held:
            skull(c, x0 + 15, y0 + 7, 'text', ink='blood')
        else:
            c.sprite(x0 + 17, y0 + 6, DAGGER, {'#': 'mid'}, z=1)
        c.text_r(x0 + 33, y0 + 8, str(k + 1), c.p['trk'][k])
    footer(c, "KEYS: EFFECTS", "K1-4: MACROS")


def b_dialog(c):
    b_home(c)
    for j in range(22, 220):                          # the page under it, darkened (every other pixel to BG)
        for i in range(W):
            if (i + j) % 2 == 0:
                c.pset(i, j, 'bg')
    x0, y0, w, h = 22, 64, 196, 112
    c.stone(x0, y0, w, h, 'stone', 'stone2')
    c.frame2(x0, y0, w, h, 'mid')
    skull(c, x0 + w // 2 - 4, y0 + 8, 'text')
    c.text_c(x0, x0 + w, y0 + 24, "CLEAR T3 PATTERN?", 'text')
    c.text_c(x0, x0 + w, y0 + 38, "16 STEPS, 9 NOTES", 'mid')
    c.text_c(x0, x0 + w, y0 + 50, "HOLD SAVE: UNDO", 'dim')
    bx = x0 + 14
    c.rect(bx, y0 + 66, 76, 22, 'mid')
    c.text_c(bx, bx + 76, y0 + 74, "CANCEL", 'ink')
    c.text_c(bx, bx + 76, y0 + 94, "OCT-", 'dim')
    bx = x0 + w - 14 - 76
    c.frame2(bx, y0 + 66, 76, 22, 'blood')
    c.sprite(bx + 6, y0 + 72, ["  #   ", "  #   ", "  #   ", "  #   ", "##### ", "  #   ", "  #   "], {'#': 'blood'})
    c.text_c(bx + 8, bx + 76, y0 + 74, "CLEAR", 'blood')
    c.text_c(bx, bx + 76, y0 + 94, "OCT+", 'dim')


def b_menu(c):
    c.rect(0, 0, W, H, 'bg')
    c.sprite(4, 5, SKULL, {'#': 'amber', '.': 'bg'})
    c.text(17, 7, "MENU", 'text')
    c.text_r(235, 7, "HOME: CLOSE", 'dim')
    c.rect(0, 21, W, 1, 'line')
    tabs = ["DISPLAY", "CONTROL", "AUDIO", "SYSTEM"]
    x = 8
    for i, t in enumerate(tabs):
        on = i == 0
        tw = text_w(t) + 8
        if on:
            c.rect(x, 28, tw, 13, 'amber')
        c.text(x + 4, 31, t, 'ink' if on else 'dim')
        x += tw + 4
    rows = [("COLOR", "CRYPT"), ("LARGE", "OFF"), ("ANIM", "ON"), ("LEDS", "DIM HI"), ("SCREEN OFF", "30 MIN"), ("HINTS", "ON")]
    for i, (n, v) in enumerate(rows):
        y = 52 + i * 26
        sel = i == 0
        if sel:
            c.stone(6, y - 5, 228, 19)
            c.frame2(6, y - 5, 228, 19, 'amber')
            torch(c, 10, y - 4, 1)
        c.text(20, y + 1, n, 'text' if sel else 'mid')
        lx0, lx1 = 20 + text_w(n) + 4, 228 - text_w(v) - 4   # dotted leaders, the old book's table of contents
        for xx in range(lx0, lx1, 3):
            c.pset(xx, y + 7, 'line')
        c.text_r(228, y + 1, v, 'amber' if sel else 'text')
    footer(c, "ALGO: TAB  PRESETS: ROW", "OCT-/+: VALUE")


def b_perform(c):
    header(c, "PERFORM BAR")
    for k, (l, v, u, f) in enumerate([("CUTOFF", "+12", "", 0.7), ("REVERB", "+0", "", 0.5), ("DELAY", "+0", "", 0.5),
                                      ("DIST", "+0", "", 0.5)]):
        card(c, k, l, v, u, f)
    c.rect(0, 76, W, 144, 'bg')
    kept = [[0, 2, 15], [0, 1, 2], [0, 1], [0, 1, 2, 3], [0, 1], [0, 1, 2, 3]]
    cur, nxt = [2, 1, 0, 3, 0, 2], [5, None, None, None, 1, None]
    for r in range(7):
        y = 79 + 19 * r
        if r == 6:
            c.text(5, y + 5, "SCN", 'dim')
            for p in range(16):
                x = 28 + 13 * p
                if p in (0, 4):
                    c.frame(x, y + 1, 11, 14, 'dim')
                    c.text_c(x, x + 11, y + 5, str(p + 1), 'mid')
                else:
                    c.pset(x + 5, y + 8, 'line')
            break
        col, band = c.p['trk'][r], r == 4
        if band:
            c.rect(3, y, 234, 17, col)
        c.text(5, y + 5, str(r + 1), 'ink' if band else col)
        for p in range(16):
            x = 17 + 13 * p
            L = "ABCDEFGHIJKLMNOP"[p]
            if p == nxt[r]:
                c.frame(x, y + 1, 11, 15, 'ink' if band else col)
                c.text_c(x, x + 11, y + 5, L, 'ink' if band else col)
            elif p == cur[r]:
                c.rect(x, y + 1, 11, 15, 'ink' if band else col)
                c.text_c(x, x + 11, y + 5, L, col if band else 'ink')
            elif p in kept[r]:
                c.text_c(x, x + 11, y + 5, L, 'ink' if band else 'mid')
            else:
                c.pset(x + 5, y + 8, 'ink' if band else 'line')
        if r == 1:
            skull(c, 225, y + 4, 'blood', muted=True)
    footer(c, "WHITE: PATTERN", "BLACK: MUTE")


def b_splash(c):
    c.rect(0, 0, W, H, 'bg')
    c.stone(28, 28, 184, 184)
    c.frame2(28, 28, 184, 184, 'line')
    torch(c, 40, 44, 0, z=2)
    torch(c, 190, 44, 1, z=2)
    skull(c, 102, 50, 'text', z=4)
    c.text_c(28, 212, 104, "SKIFF", 'amber', z=4, sp=1)
    c.rect(56, 138, 128, 1, 'line')
    c.text_c(28, 212, 146, "CRYPT", 'ember', z=2)
    c.text_c(28, 212, 172, "ON FELUCCA 1.1.5", 'mid')
    c.text_c(28, 212, 186, "HUGELTON + COMMUNITY", 'dim')


def b_delay(c):                                       # a V1 graph in CRYPT: the echo taps, fading skulls
    header(c, "DELAY")
    for k, (l, v, u, f) in enumerate([("TIME", "1/8", "", 0.3), ("FEEDBACK", "47", "%", 0.47), ("COLOR", "55", "%", 0.55),
                                      ("MIX", "71", "%", 0.71)]):
        card(c, k, l, v, u, f, hot=k == 1)
    panel(c)
    x, size = 20, 1.0
    for i in range(8):
        lvl = 0.47 ** i
        if lvl < 0.03:
            break
        h = round(90 * lvl)
        c.rect(x + 4, 196 - h, 3, h, 'amber' if i == 0 else 'ember')
        if i:
            c.dither(x + 4, 196 - h, 3, h, 'bg', 1 if lvl > 0.3 else 2)
        z = 2 if lvl > 0.4 else 1
        skull(c, x + 5 - 4 * z, 196 - h - 10 * z, 'text' if i == 0 else 'mid' if lvl > 0.2 else 'dim', z=z)
        x += 26
    c.rect(12, 197, 216, 1, 'line')
    footer(c, "ANALOG  ACID", "2/5", track=0)


# ---------------------------------------------------------------- A AMBER (one phosphor, ASCII only)
def a_home(c):
    c.rect(0, 0, W, H, 'bg')
    c.text(4, 6, ">", 'amber'); c.text(12, 6, "1.2  124 BPM", 'amber')
    c.text_r(236, 6, "[B]* CRYPT 01", 'mid')
    c.rect(0, 17, W, 1, 'line'); c.rect(0, 19, W, 1, 'line')
    for k, (l, v) in enumerate([("CUTOFF", "355"), ("RES", "79"), ("ATTACK", "1.0"), ("RELEASE", "8.8")]):
        x = 2 + 60 * k
        c.text(x, 26, l, 'mid')
        c.text(x, 37, v, 'amber' if k else 'gold', z=2)
        bar = "#" * (1 + k * 2) + "." * (8 - k * 2)
        c.text(x, 56, "[" + bar[:7] + "]", 'dim')
    c.rect(0, 70, W, 1, 'line')
    for k in range(6):
        y = 78 + k * 22
        sel = k == 2
        pre = ">" if sel else " "
        c.text(2, y, pre + str(k + 1), 'gold' if sel else 'mid')
        c.text(18, y, TRACKS[k][0][:8], 'amber' if sel else 'mid')
        s = "".join("#" if v == "1" else "." for v in STEPS[k])
        s = s[:4] + " " + s[4:8] + " " + s[8:12] + " " + s[12:]
        c.text(70, y, s, 'amber' if sel else 'dim', sp=1)
        if sel:
            c.text(18, y + 10, TRACKS[k][1], 'dim')
    c.rect(0, 216, W, 1, 'line')
    c.text(2, 226, "HOLD HOME: SHIFT", 'dim')
    for j in range(0, H, 2):                          # scanlines
        for i in range(W):
            r, g, b = c.px[i, j]
            c.px[i, j] = (r * 3 // 4, g * 3 // 4, b * 3 // 4)


def a_env(c):
    c.rect(0, 0, W, H, 'bg')
    c.text(4, 6, ">", 'amber'); c.text(12, 6, "1.2  124 BPM", 'amber')
    c.text_r(236, 6, "ENV", 'mid')
    c.rect(0, 17, W, 1, 'line'); c.rect(0, 19, W, 1, 'line')
    for k, (l, v) in enumerate([("ATTACK", "1.0"), ("DECAY", "54"), ("SUSTAIN", "16"), ("RELEASE", "8.8")]):
        x = 2 + 60 * k
        c.text(x, 26, l, 'gold' if k == 2 else 'mid')
        c.text(x, 37, v, 'gold' if k == 2 else 'amber', z=2)
    c.rect(0, 62, W, 1, 'line')
    art = ["  /\\",
           " /  \\",
           "/    \\__________",
           "                \\",
           "                 \\_"]
    for j, row in enumerate(art):                    # the envelope in ASCII art (our font's / \ _ as lines)
        y = 86 + j * 20
        for i, ch in enumerate(row):
            x = 14 + i * 10
            if ch == '/':
                for t in range(10):
                    c.rect(x + t, y + 18 - t * 2, 2, 2, 'amber')
            elif ch == '\\':
                for t in range(10):
                    c.rect(x + t, y + t * 2, 2, 2, 'amber')
            elif ch == '_':
                c.rect(x, y + 18, 10, 2, 'amber')
    c.text(14, 200, "A   D     S             R", 'dim')
    c.rect(0, 216, W, 1, 'line')
    c.text(2, 226, "1 ANALOG ACID", 'mid')
    c.text_r(236, 226, "1/2", 'dim')
    for j in range(0, H, 2):
        for i in range(W):
            r, g, b = c.px[i, j]
            c.px[i, j] = (r * 3 // 4, g * 3 // 4, b * 3 // 4)


def a_mixer(c):
    c.rect(0, 0, W, H, 'bg')
    c.text(4, 6, "#", 'amber'); c.text(12, 6, "1.2  124 BPM", 'amber')
    c.text_r(236, 6, "MIXER", 'mid')
    c.rect(0, 17, W, 1, 'line'); c.rect(0, 19, W, 1, 'line')
    lv = [-6, -14, -24, -1, -6, -9]
    for k in range(6):
        x = 4 + 39 * k
        sel = k == 4
        c.text(x, 26, ("[" if sel else " ") + str(k + 1) + ("]" if sel else " "), 'gold' if sel else 'amber', z=1)
        c.text(x, 38, TRACKS[k][0][:5], 'mid')
        n = 0 if k == 2 else round(10 * (40 + lv[k]) / 40)
        for r in range(10):                           # the level in ASCII: a column of # from the foot
            y = 160 - r * 10
            ch = "#" if r < n else ":"
            c.text(x + 10, y, ch, 'amber' if r < n else 'line')
        c.text(x + 2, 176, "OFF" if k == 2 else str(lv[k]), 'amber' if sel else 'mid')
        if k == 2:
            c.text(x + 4, 60, "X_X", 'blood')
    c.rect(0, 216, W, 1, 'line')
    c.text(2, 226, "5 SAMPLE PIANO", 'mid')
    c.text_r(236, 226, "1/5", 'dim')
    for j in range(0, H, 2):
        for i in range(W):
            r, g, b = c.px[i, j]
            c.px[i, j] = (r * 3 // 4, g * 3 // 4, b * 3 // 4)


SCREENS = [("b_home", B, b_home, "B TORCHLIT · HOME: the lanes on stone, the selected one a band; a torch over the step playing; the header's REC a blood drop"),
           ("b_env", B, b_env, "B · ENV: the envelope a ziggurat of ASCII shade blocks (ember, blood), its points little skulls, the one turned lit"),
           ("b_lfo", B, b_lfo, "B · LFO: the wave a snake, its head where the LFO is now"),
           ("b_mixer", B, b_mixer, "B · MIXER: each level a torch, the flame as tall as the level; a muted track's skull crossed"),
           ("b_fx", B, b_fx, "B · FX held: the effects in ASCII-art icons; the cuts daggers, a held one a skull on blood"),
           ("b_perform", B, b_perform, "B · PERFORM: the rows as today in the font; a muted track's crossed skull"),
           ("b_delay", B, b_delay, "B · DELAY (a V1 graph): the echoes as skulls, each smaller and fainter by FEEDBACK"),
           ("b_dialog", B, b_dialog, "B · a dialog: a stone tablet in a double ASCII border, CLEAR outlined in blood"),
           ("b_menu", B, b_menu, "B · MENU: dotted leaders like an old book's contents; the row a torch lights"),
           ("b_splash", B, b_splash, "B · splash: SKIFF under a skull between two torches"),
           ("a_home", A, a_home, "A AMBER · HOME: one phosphor, ASCII only: [####...] gauges, # and . for the steps, scanlines"),
           ("a_env", A, a_env, "A · ENV in ASCII art: / \\ _ drawn as the font's strokes"),
           ("a_mixer", A, a_mixer, "A · MIXER: each level a column of #, X_X for a muted track")]

if __name__ == "__main__":
    shots = []
    for name, pal, fn, cap in SCREENS:
        c = C(pal)
        fn(c)
        c.save(name)
        shots.append((Image.open(OUT / "x2" / f"CR_{name}.png"), cap))
    cols, pad = 4, 24
    try:
        capf = ImageFont.truetype(str(HERE.parent / "assets" / "fonts" / "BarlowCondensed-Medium.ttf"), 22)
    except OSError:
        capf = ImageFont.load_default()
    rows_n = (len(shots) + cols - 1) // cols
    sw, sh = W * 2, H * 2
    sheet = Image.new("RGB", (cols * (sw + pad) + pad, rows_n * (sh + 90) + pad), (24, 20, 16))
    g = ImageDraw.Draw(sheet)
    for i, (im, cap) in enumerate(shots):
        r, cc = divmod(i, cols)
        x, y = pad + cc * (sw + pad), pad + r * (sh + 90)
        sheet.paste(im, (x, y))
        words, line, ly = cap.split(), "", y + sh + 26
        for w_ in words:
            if g.textlength(line + " " + w_, font=capf) > sw and line:
                g.text((x, ly), line, font=capf, fill=(230, 210, 170))
                line, ly = w_, ly + 26
            else:
                line = (line + " " + w_).strip()
        g.text((x, ly), line, font=capf, fill=(230, 210, 170))
    (HERE / "mockups").mkdir(exist_ok=True)
    sheet.save(HERE / "mockups" / "crypt_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/crypt_sheet.png")
