#!/usr/bin/env python3
"""SMK-37 Pro mockups: the controls and pad LED pass (SMK37.md, "Decisions for the UX pass"). The M-VAVE SMK-37 Pro
drawn from above in Skiff's BLOCKS look (wheels, the screen and its six buttons, K1..K8 over the 16 RGB pads, four
faders over twelve buttons, the 37 keys), each control with its printed name in grey and its job in Skiff in white,
lit pads in the track colours, the screen a firmware render (tests/ui_render.c, SKIFF palette).
Geometry: the panel's layout as on the unit (the kit's notes, github.com/genkigenki/fm1-to-smk37), drawn here.
Writes mockups/smk37_*.png: the panel as built (bring-up), then for each decision its directions, and the sheet.
  SMK_RENDERS=~/skiff-fast/build/ui_new/ppm python3 mock_smk37.py
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "assets" / "fonts"
OUTD = HERE / "mockups"
RENDERS = Path(os.path.expanduser(os.environ.get("SMK_RENDERS", str(HERE.parent / "build" / "ui_new" / "ppm"))))

TRK = ["#FF5A36", "#22C3B4", "#FFBF00", "#9580FF", "#FF6FAE", "#A3E635"]
BG, BODY, EDGE, CTRL, CTRL_HI = "#0C0C0C", "#161616", "#2A2A2A", "#232323", "#3A3A3A"
PRINT, INK, MID, DIM = "#8C8C8C", "#F2F2F2", "#B4B4B4", "#5A5A5A"
REC, GREEN = "#FF3B30", "#30D158"
FONT = {}


def font(bold, px):
    k = (bold, px)
    if k not in FONT:
        FONT[k] = ImageFont.truetype(str(FONTS / ("BarlowCondensed-Bold.ttf" if bold else "BarlowCondensed-Medium.ttf")), px)
    return FONT[k]


def rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):                                   # a toward b by t
    a, b = rgb(a) if isinstance(a, str) else a, rgb(b) if isinstance(b, str) else b
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lum(c):
    r, g, b = rgb(c) if isinstance(c, str) else c
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ------------------------------------------------------------------------------------------- geometry ---
W, H = 1600, 600
KNOB_X = [452 + i * 92 for i in range(8)]
PAD_Y = [152, 222]
FAD_X = [1186, 1276, 1366, 1456]
RB_X = [1168 + i * 58 for i in range(6)]
RB_TOP = ["ARP", "NOTE REPEAT", "SCALE", "CHORD", "GLOBE", "BT"]
RB_BOT = ["PATCH", "PARA", "FX", "SEQ", "SEQ PLAY", "SEQ REC"]
SB = [("KNOB BANK", 0, 0), ("FADER BANK", 1, 0), ("<", 0, 1), (">", 1, 1), ("OCTAVE-", 0, 2), ("OCTAVE+", 1, 2)]
KEY_Y0, KEY_Y1, BLACK_H = 372, 582, 132
WHITE_W = (1570 - 30) / 22
BLACK_OF = [0, 1, 3, 4, 5, 7, 8, 10, 11, 12, 14, 15, 17, 18, 19]   # a black key right of white key j
NOTE = "C C# D D# E F F# G G# A A# B".split()


def key_list():
    """the 37 keys C3..C6: (index, white?, x0, x1, name)"""
    out, s = [], 0
    for j in range(22):
        if s > 36:
            break
        x0 = 30 + j * WHITE_W
        out.append((s, True, x0, x0 + WHITE_W, NOTE[s % 12] + str(3 + s // 12)))
        s += 1
        if j in BLACK_OF and s <= 36:
            cx = 30 + (j + 1) * WHITE_W
            out.append((s, False, cx - 21, cx + 21, NOTE[s % 12] + str(3 + s // 12)))
            s += 1
    return out


KEYS = key_list()
WHITE_INDEX = [k[0] for k in KEYS if k[1]]           # semitone of each white key, left to right


def pad_xy(p):                                       # hardware pad 0..7 the top row, 8..15 the bottom, left to right
    return KNOB_X[p % 8], PAD_Y[p // 8]


class Panel:
    """what one picture shows: set the fields, then draw()"""

    def __init__(self):
        self.pads = [None] * 16                      # (style, colour, text): style off / dim / full / white / ring
        self.knobs = ["MASTER", "SELECT", "TRACK", "SOUND", "KNOB 1", "KNOB 2", "KNOB 3", "KNOB 4"]
        self.faders = [("", 0.5)] * 4                # (job, position 0..1)
        self.wheels = ("", "")
        self.btn = {n: "" for n in RB_TOP + RB_BOT + [s[0] for s in SB]}   # printed -> job
        self.lit = {}                                # printed -> "on" / "glow" / "green" / "red"
        self.keys = {}                               # semitone -> (fill, label)
        self.key_zone = {}                           # semitone -> tint
        self.screen = None
        self.notes = []                              # (x, y, text, colour): free labels

    # --------------------------------------------------------------------------------------------------
    def draw(self, scale=1.0):
        im = Image.new("RGB", (W, H), BG)
        g = ImageDraw.Draw(im)
        g.rounded_rectangle((6, 6, W - 6, H - 6), 30, fill=BODY, outline=EDGE, width=2)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gg = ImageDraw.Draw(glow)
        for p, v in enumerate(self.pads):            # the lit pads' light, under them
            if v and v[0] in ("full", "white"):
                x, y = pad_xy(p)
                c = rgb(INK) if v[0] == "white" else rgb(v[1])
                gg.rounded_rectangle((x - 44, y - 34, x + 44, y + 34), 14, fill=c + (150,))
        for name, st in self.lit.items():
            if st in ("on", "green", "red"):
                x0, y0, x1, y1 = self.btn_box(name)
                c = rgb({"on": INK, "green": GREEN, "red": REC}[st])
                gg.rounded_rectangle((x0 - 4, y0 - 4, x1 + 4, y1 + 4), 6, fill=c + (130,))
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        im.paste(glow, (0, 0), glow)
        g = ImageDraw.Draw(im)
        self.draw_wheels(g)
        self.draw_screen(im, g)
        self.draw_small_buttons(g)
        self.draw_knobs(g)
        self.draw_pads(g)
        self.draw_faders(g)
        self.draw_right_buttons(g)
        self.draw_keys(g)
        for x, y, t, c in self.notes:
            g.text((x, y), t, font=font(True, 15), fill=c, anchor="mm")
        if scale != 1.0:
            im = im.resize((round(W * scale), round(H * scale)), Image.LANCZOS)
        return im

    @staticmethod
    def btn_box(name):
        if name in RB_TOP or name in RB_BOT:
            i = (RB_TOP + RB_BOT).index(name)
            x, y = RB_X[i % 6], (216 if i < 6 else 262)
            return x - 25, y - 11, x + 25, y + 11
        for n, c, r in SB:
            if n == name:
                x0 = 214 + c * 92
                y0 = 228 + r * 42
                return x0, y0, x0 + 76, y0 + 22
        raise KeyError(name)

    def draw_button(self, g, name, printed_above):
        x0, y0, x1, y1 = self.btn_box(name)
        st = self.lit.get(name, "")
        fill = {"on": INK, "green": GREEN, "red": REC, "glow": "#4A4A4A", "mid": "#9A9A9A"}.get(st, CTRL)
        g.rounded_rectangle((x0, y0, x1, y1), 5, fill=fill, outline=CTRL_HI if not st else None)
        job = self.btn[name]
        if job:
            ink = "#111111" if st in ("on", "green", "mid") else INK
            f = font(True, 14)
            while g.textlength(job, font=f) > x1 - x0 - 4 and f.size > 10:
                f = font(True, f.size - 1)
            g.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1), job, font=f, fill=ink, anchor="mm")
        cx = (x0 + x1) / 2
        if printed_above:
            g.text((cx, y0 - 4), name, font=font(False, 11), fill=PRINT, anchor="md")
        else:
            g.text((cx, y1 + 4), name, font=font(False, 11), fill=PRINT, anchor="ma")

    def draw_wheels(self, g):
        for i, (lab, job) in enumerate(zip(("PITCH", "MOD"), self.wheels)):
            x0 = 40 + i * 76
            g.rounded_rectangle((x0, 60, x0 + 56, 236), 14, fill=CTRL, outline=CTRL_HI)
            for k in range(9):
                yy = 84 + k * 16
                g.line((x0 + 10, yy, x0 + 46, yy), fill="#2E2E2E", width=2)
            g.line((x0 + 8, 148, x0 + 48, 148), fill="#505050", width=3)
            g.text((x0 + 28, 246), lab, font=font(False, 12), fill=PRINT, anchor="ma")
            if job:
                g.text((x0 + 28, 266), job, font=font(True, 15), fill=INK, anchor="ma")

    def draw_screen(self, im, g):
        g.rounded_rectangle((200, 24, 388, 212), 8, fill="#050505", outline=CTRL_HI)
        if self.screen is not None:
            im.paste(self.screen.resize((176, 176), Image.LANCZOS), (206, 30))

    def draw_small_buttons(self, g):
        for n, c, r in SB:
            self.draw_button(g, n, printed_above=False)

    def draw_knobs(self, g):
        for i, x in enumerate(KNOB_X):
            g.text((x, 20), f"K{i + 1}", font=font(False, 12), fill=PRINT, anchor="ma")
            g.ellipse((x - 26, 38, x + 26, 90), fill=CTRL, outline=CTRL_HI, width=2)
            g.line((x, 64, x + 13, 46), fill=MID, width=3)
            job = self.knobs[i]
            if job:
                f = font(True, 15)
                while g.textlength(job, font=f) > 88 and f.size > 10:
                    f = font(True, f.size - 1)
                g.text((x, 98), job, font=f, fill=INK, anchor="ma")

    def draw_pads(self, g):
        for p in range(16):
            x, y = pad_xy(p)
            box = (x - 39, y - 29, x + 39, y + 29)
            v = self.pads[p] or ("off", None, "")
            st, c, t = v
            if st == "off":
                g.rounded_rectangle(box, 10, fill="#1B1B1B", outline="#2E2E2E", width=2)
                ink = DIM
            elif st == "dim":
                g.rounded_rectangle(box, 10, fill=mix(BODY, c, 0.28), outline=mix(BODY, c, 0.55), width=2)
                ink = mix(c, INK, 0.55)
            elif st == "faint":
                g.rounded_rectangle(box, 10, fill=mix(BODY, INK, 0.13), outline=mix(BODY, INK, 0.25), width=2)
                ink = MID
            elif st == "half":
                g.rounded_rectangle(box, 10, fill=mix(BODY, c, 0.6), outline=c, width=2)
                ink = INK
            elif st == "ring":
                g.rounded_rectangle(box, 10, fill=mix(BODY, c, 0.28), outline=INK, width=4)
                ink = INK
            elif st == "ringfull":
                g.rounded_rectangle(box, 10, fill=c, outline=INK, width=5)
                ink = "#111111" if lum(c) > 110 else INK
            elif st == "ringfaint":
                g.rounded_rectangle(box, 10, fill=mix(BODY, INK, 0.13), outline=INK, width=5)
                ink = INK
            elif st == "white":
                g.rounded_rectangle(box, 10, fill=INK)
                ink = "#111111"
            else:                                    # full
                g.rounded_rectangle(box, 10, fill=c)
                ink = "#111111" if lum(c) > 110 else INK
            if t:
                f = font(True, 17)
                while g.textlength(t, font=f) > 72 and f.size > 10:
                    f = font(True, f.size - 1)
                g.text((x, y + 1), t, font=f, fill=ink, anchor="mm")

    def draw_faders(self, g):
        for j, x in enumerate(FAD_X):
            job, pos = self.faders[j]
            g.text((x, 14), f"F{j + 1}", font=font(False, 12), fill=PRINT, anchor="ma")
            g.rounded_rectangle((x - 4, 32, x + 4, 146), 4, fill="#080808")
            cy = 136 - pos * 94
            g.rounded_rectangle((x - 26, cy - 10, x + 26, cy + 10), 4, fill="#3C3C3C", outline="#575757")
            g.line((x - 20, cy, x + 20, cy), fill=MID, width=2)
            if job:
                f = font(True, 15)
                while g.textlength(job, font=f) > 86 and f.size > 10:
                    f = font(True, f.size - 1)
                g.text((x, 154), job, font=f, fill=INK, anchor="ma")

    def draw_right_buttons(self, g):
        for n in RB_TOP:
            self.draw_button(g, n, printed_above=True)
        for n in RB_BOT:
            self.draw_button(g, n, printed_above=False)

    def draw_keys(self, g):
        for s, white, x0, x1, name in KEYS:
            if not white:
                continue
            fill = self.keys.get(s, (None, ""))[0] or self.key_zone.get(s) or "#D9D9D9"
            g.rectangle((x0 + 1, KEY_Y0, x1 - 1, KEY_Y1), fill=fill, outline="#0A0A0A")
        for s, white, x0, x1, name in KEYS:
            if white:
                continue
            fill = self.keys.get(s, (None, ""))[0] or (mix(self.key_zone[s], "#000000", 0.55) if s in self.key_zone
                                                        else "#141414")
            g.rectangle((x0, KEY_Y0, x1, KEY_Y0 + BLACK_H), fill=fill, outline="#000000")
        for s, white, x0, x1, name in KEYS:
            lab = self.keys.get(s, (None, ""))[1]
            if not lab:
                continue
            cx = (x0 + x1) / 2
            y = KEY_Y1 - 22 if white else KEY_Y0 + BLACK_H - 20
            fill = self.keys.get(s, (None, ""))[0] or self.key_zone.get(s) or ("#D9D9D9" if white else "#141414")
            ink = "#111111" if lum(fill) > 110 else INK
            for k, part in enumerate(reversed(lab.split("\n"))):
                g.text((cx, y - k * 18), part, font=font(True, 15), fill=ink, anchor="mm")
        for s, white, x0, x1, name in KEYS:           # the octave names under C
            if white and NOTE[s % 12] == "C" and s not in self.keys:
                g.text(((x0 + x1) / 2, KEY_Y1 - 10), name, font=font(False, 12), fill="#777777", anchor="mm")


def screen(name):
    p = RENDERS / f"{name}.ppm"
    return Image.open(p).convert("RGB") if p.exists() else None


# ------------------------------------------------------------------------------------- the jobs as built ---
def as_built():
    """the bring-up default (smk37 8ef4ca4): the FM-1's buttons on their printed counterparts"""
    p = Panel()
    p.btn.update({"FX": "FX", "SCALE": "SEL", "CHORD": "ENV", "NOTE REPEAT": "LFO", "PARA": "EDIT", "GLOBE": "GLO",
                  "PATCH": "HOME", "BT": "SAVE", "ARP": "ARP", "SEQ": "SEQ", "SEQ PLAY": "PLAY", "SEQ REC": "REC",
                  "OCTAVE-": "OCT-", "OCTAVE+": "OCT+"})
    return p


def melodic_scale_keys(p, notes, colour):
    """keys held: their semitones (0 = C3) lit"""
    for s in notes:
        p.keys[s] = (colour, NOTE[s % 12])


# ------------------------------------------------------------------------------------------- pad contexts ---
T1, T4 = TRK[0], TRK[3]
STEP_T1 = {1: "C2", 3: "C2", 5: "D#2", 6: "G1", 9: "C2+", 10: "tie", 11: "A#1", 14: "C3", 16: "G2"}   # SKIFF_step_tiles
SNARE = {5, 13, 15}
ENTRIES_T1 = {"A": "on", "C": "kept", "F": "staged", "P": "kept"}   # SKIFF_layer_perform: T1 on A, C kept, F staged
LANES = ["BD", "SD", "CP", "CH", "OH", "TM", "RS", "CB"]
SCALE_DEG = ["C", "D", "D#", "F", "G", "G#", "A#", "C"]   # T1's C minor, C3..C4


def grid_pads(p, cells, colour, play=None, edit=None, scheme="A"):
    """16 cells in text order (top row 1..8): cells {step 1..16: text}; the colour scheme of decision 2"""
    for i in range(16):
        s = i + 1
        t = cells.get(s)
        if scheme == "A":                            # as the screen's tiles: empty faint, set the track colour, the
            v = ("faint", None, str(s)) if t is None else ("half", colour, "") if t == "tie" else ("full", colour, t)
            if s == edit:                            # edited step white, the playing one ringed
                v = ("white", None, t or str(s))
            elif s == play:
                v = ("ringfaint", None, str(s)) if t is None else ("ringfull", colour, t if t != "tie" else "")
        elif scheme == "B":                          # dark: empty off, set half, the playhead full
            v = ("off", None, str(s)) if t is None else ("dim", colour, t if t != "tie" else "")
            if s == edit:
                v = ("ring", colour, t or str(s))
            if s == play:
                v = ("full", colour, t if t and t != "tie" else str(s))
        else:                                        # C: the track's ground, steps full, the playhead white
            v = ("dim", colour, str(s)) if t is None else ("full", colour, t if t != "tie" else "")
            if s == edit:
                v = ("ring", colour, t or str(s))
            if s == play:
                v = ("white", None, t if t and t != "tie" else str(s))
        p.pads[i] = v


def pads_A(ctx, scheme="A"):
    """A: the FM-1's 16 white keys (genkigenki's default): a grid in text order on step pages and layers, a second
    keyboard (low notes on the bottom row) on the others; the keybed as the FM-1's keys"""
    p = as_built()
    if ctx == "drum":
        p.screen = screen("SKIFF_drum")
        grid_pads(p, {s: "SD" for s in SNARE}, T4, play=7, scheme=scheme)
    elif ctx == "step":
        p.screen = screen("SKIFF_step_tiles")
        grid_pads(p, STEP_T1, T1, play=10, edit=5, scheme=scheme)
    elif ctx == "perform":
        p.screen = screen("SKIFF_layer_perform")
        perform_pads(p)
    else:                                            # HOME, T1 playing, C minor chord held on the keybed
        p.screen = screen("SKIFF_home")
        held = {12: "C4", 15: "D#4", 19: "G4"}
        whites = WHITE_INDEX[3:19]                   # F3 .. G5: the FM-1's white keys
        for w, sem in enumerate(whites):             # keyboard order: F3..F4 the bottom row, G4..G5 the top
            pad = w + 8 if w < 8 else w - 8
            name = NOTE[sem % 12] + str(3 + sem // 12)
            p.pads[pad] = ("full", T1, name) if sem in held else ("faint", None, name)
        melodic_scale_keys(p, held, T1)
    return p


def perform_pads(p):
    for i, e in enumerate("ABCDEFGHIJKLMNOP"):
        st = ENTRIES_T1.get(e)
        p.pads[i] = (("full", T1, e) if st == "on" else ("dim", T1, e) if st == "kept" else
                     ("ring", T1, e) if st == "staged" else ("off", None, e))
    p.lit["ARP"] = "on"


def pads_B(ctx):
    """B: the pads play: the top row the DRUM track's 8 lanes (a melodic track: its scale's 8 notes from the root),
    the bottom row the six tracks' mutes, FILL and TAP; the keybed keeps every FM-1 key job (steps unlit)"""
    p = as_built()
    drum = ctx == "drum"
    p.screen = screen({"drum": "SKIFF_drum", "step": "SKIFF_step_tiles", "perform": "SKIFF_layer_perform",
                       "home": "SKIFF_home"}[ctx])
    for i in range(8):
        if drum:
            p.pads[i] = ("full", T4, LANES[i]) if i == 1 else ("dim", T4, LANES[i])
        else:
            p.pads[i] = ("full" if i in (0, 7) else "dim", T1, SCALE_DEG[i])
    muted = {2} if ctx != "perform" else {2, 5}
    for t in range(6):
        p.pads[8 + t] = ("dim", TRK[t], f"M{t + 1}") if t in muted else ("full", TRK[t], f"T{t + 1}")
    p.pads[14] = ("faint", None, "FILL")
    p.pads[15] = ("white", None, "TAP") if ctx == "perform" else ("faint", None, "TAP")
    if ctx == "perform":
        p.lit["ARP"] = "on"
    if ctx == "home":
        melodic_scale_keys(p, {12: 0, 15: 0, 19: 0}, T1)
    else:                                            # the white keys F3..G5 do the tiles, unlit
        for w, sem in enumerate(WHITE_INDEX[3:19]):
            p.keys[sem] = (None, "ABCDEFGHIJKLMNOP"[w] if ctx == "perform" else str(w + 1))
    return p


def pads_C(ctx, scheme="A"):
    """C (recommended): the pads are always a grid, never a second keyboard: the steps and tiles as in A, and on
    pages where the FM-1's white keys only play notes, the selected track's 16 steps of the bar with the playhead
    (a tap sets or clears a step: the last note played). The keybed plays notes"""
    if ctx != "home":
        return pads_A(ctx, scheme)
    p = as_built()
    p.screen = screen("SKIFF_home")
    grid_pads(p, STEP_T1, T1, play=10, scheme=scheme)
    melodic_scale_keys(p, {12: 0, 15: 0, 19: 0}, T1)
    return p


# ---------------------------------------------------------------------------------------------- sheets ---
def label_block(g, x, y, w, title, lines, rec=False):
    g.text((x, y), title, font=font(True, 34), fill=INK)
    yy = y + 46
    if rec:
        tw = g.textlength(title, font=font(True, 34))
        tx, ty = (x + tw + 16, y + 6) if tw + 176 <= w else (x, y + 44)   # (no room beside the title: under it)
        g.rounded_rectangle((tx, ty, tx + 160, ty + 32), 6, fill=GREEN)
        g.text((tx + 80, ty + 17), "RECOMMENDED", font=font(True, 20), fill="#0C0C0C", anchor="mm")
        yy = max(yy, ty + 42)
    for ln in lines:
        for part in wrap(g, ln, font(False, 24), w):
            g.text((x, yy), part, font=font(False, 24), fill=MID)
            yy += 30
    return yy


def wrap(g, text, f, w):
    out, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if g.textlength(t, font=f) > w and cur:
            out.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        out.append(cur)
    return out



def save(im, name):
    OUTD.mkdir(exist_ok=True)
    im.save(OUTD / name, optimize=True)
    print("wrote", OUTD / name, im.size)


PADS_BOXES = [(188, 18, 392, 216), (404, 118, 1144, 256)]   # the screen, the pads
CTX = [("drum", "DRUM grid: T4 DRUM KIT, SEQ > STEP, lane SNARE, step 7 playing"),
       ("step", "SEQ > STEP: T1 ACID, step 5 edited, step 10 playing"),
       ("perform", "PERFORM (ARP held): T1's entries, A playing, F staged"),
       ("home", "HOME: T1 ACID playing, C minor held on the keybed")]


def direction_sheet(name, title, lines, make, rec=False):
    """one direction in its four contexts, 2 x 2, the panel's upper half and the keys"""
    tiles = []
    for ctx, cap in CTX:
        p = make(ctx)
        im = p.draw()
        tiles.append((im.resize((1200, 450), Image.LANCZOS), cap))
    sw = 2 * 1200 + 3 * 30
    head = 200
    sh = head + 2 * (450 + 60) + 30
    sheet = Image.new("RGB", (sw, sh), BG)
    g = ImageDraw.Draw(sheet)
    label_block(g, 30, 24, sw - 60, title, lines, rec)
    for i, (im, cap) in enumerate(tiles):
        x = 30 + (i % 2) * 1230
        y = head + (i // 2) * 510
        sheet.paste(im, (x, y))
        g.text((x, y + 458), cap, font=font(False, 24), fill=MID)
    save(sheet, name)
    return sheet


def stacked(panels, boxes):
    """several pictures' parts one under the other"""
    parts = [regions(p.draw(), boxes) for p in panels]
    out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + 12 * (len(parts) - 1)), BG)
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height + 12
    return out


def regions(im, boxes):
    """the panel's parts in boxes, side by side (each box a part: the screen, the faders ..)"""
    parts = [im.crop(b) for b in boxes]
    out = Image.new("RGB", (sum(p.width for p in parts) + 12 * (len(parts) - 1), max(p.height for p in parts)), BG)
    x = 0
    for p in parts:
        out.paste(p, (x, 0))
        x += p.width + 12
    return out


OVERVIEW = []                                        # (decision, [(picture, title, recommended)]) for the sheet


def options_sheet(name, heading, options, crop_box, scale=1.0, rows=False):
    """a decision's directions side by side (rows: one under the other, the words at the right): each a crop of
    the panel (crop_box: one box, or a list of boxes put side by side) and its words"""
    ims = []
    for title, lines, make, rec in options:
        im = make()
        if not isinstance(im, Image.Image):          # a Panel: drawn and cropped (an Image: as it is)
            im = im.draw()
            im = regions(im, crop_box) if isinstance(crop_box, list) else im.crop(crop_box)
        if scale != 1.0:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        ims.append((im, title, lines, rec))
    OVERVIEW.append((heading, [(i[0], i[1], i[3]) for i in ims]))
    if rows:
        tw = 760
        sw = ims[0][0].width + tw + 90
        sh = 110 + sum(max(i[0].height, 260) + 30 for i in ims) + 20
        sheet = Image.new("RGB", (sw, sh), BG)
        g = ImageDraw.Draw(sheet)
        g.text((30, 24), heading, font=font(True, 44), fill=INK)
        y = 110
        for im, title, lines, rec in ims:
            sheet.paste(im, (30, y))
            label_block(g, im.width + 60, y, tw, title, lines, rec)
            y += max(im.height, 260) + 30
        save(sheet, name)
        return sheet
    cw = max(i[0].width for i in ims)
    sw = len(ims) * cw + (len(ims) + 1) * 30
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    text_h = max(len([w for ln in o[2] for w in wrap(tmp, ln, font(False, 24), cw)]) for o in ims) * 30 + 70
    sh = 110 + max(i[0].height for i in ims) + text_h + 80
    sheet = Image.new("RGB", (sw, sh), BG)
    g = ImageDraw.Draw(sheet)
    g.text((30, 24), heading, font=font(True, 44), fill=INK)
    for k, (im, title, lines, rec) in enumerate(ims):
        x = 30 + k * (cw + 30)
        sheet.paste(im, (x, 110))
        label_block(g, x, 110 + im.height + 20, cw, title, lines, rec)
    save(sheet, name)
    return sheet


# ------------------------------------------------------------------------------------- the other decisions ---
def faders(opt):
    p = as_built()
    if opt == "A":
        p.screen = screen("SKIFF_mixer")
        p.faders = [("T1 LEVEL", 0.78), ("T2 LEVEL", 0.6), ("T3 LEVEL", 0.42), ("T4 LEVEL", 0.7)]
        p.btn["FADER BANK"] = "LEVEL"
    elif opt == "B":
        p.screen = screen("SKIFF_home")
        p.faders = [("CUTOFF", 0.65), ("RES", 0.4), ("ATTACK", 0.1), ("RELEASE", 0.5)]
        p.btn["FADER BANK"] = "NEXT 4"
    else:
        p.screen = screen("SKIFF_perform_held")
        p.faders = [("THROW CUT", 0.5), ("THROW REV", 0.2), ("THROW DLY", 0.35), ("THROW DRV", 0.0)]
        p.btn["FADER BANK"] = "T1 / ALL"
    return p


def wheels(opt):
    p = as_built()
    p.screen = screen("SKIFF_home")
    p.wheels = {"A": ("BEND", "MOD CC1"), "B": ("BEND", "CUTOFF"), "C": ("BEND", "FX DEPTH")}[opt]
    return p


def outer(opt):
    p = as_built()
    low, high = list(range(0, 5)), list(range(32, 37))
    for s in range(5, 32):
        p.key_zone[s] = "#9FD8D2"
    if opt == "A":
        for s in low + high:
            p.key_zone[s] = "#E9C46A"
        p.keys[0] = ("#E9C46A", "C3")
        p.keys[36] = ("#E9C46A", "C6")
        p.keys[5] = ("#9FD8D2", "F3")
        p.keys[31] = ("#9FD8D2", "G5")
    elif opt == "B":
        names = {0: "BD", 2: "SD", 4: "CH", 1: "CP", 3: "OH", 32: "TM", 34: "RS", 36: "CB", 33: "FILL", 35: "TAP"}
        for s, n in names.items():
            p.keys[s] = (TRK[3] if n not in ("FILL", "TAP") else "#E9C46A", n)
    else:
        for s in low + high:
            p.keys[s] = ("#6A6A6A" if s in (0, 2, 4, 33, 35, 36, 32, 34) else "#2A2A2A", "")
        p.keys[0] = ("#6A6A6A", "OFF")
        p.keys[36] = ("#6A6A6A", "OFF")
    return p


def extra(opt):
    p = as_built()
    p.screen = screen("SKIFF_song_playing")
    jobs = {"A": ("SHIFT", "LEVEL", "ENTRY <", "ENTRY >"), "B": ("SHIFT", "LEVEL", "UNDO", "REDO"),
            "C": ("MENU", "LEVEL", "PAGE <", "PAGE >")}[opt]
    for n, j in zip(("KNOB BANK", "FADER BANK", "<", ">"), jobs):
        p.btn[n] = j
    return p


def leds(opt):
    p = as_built()
    p.screen = screen("SKIFF_step_tiles")
    on = {"SEQ": "on", "SEQ PLAY": "green", "SEQ REC": "red"}      # the SEQ page, playing, a track armed
    p.lit.update(on)
    if opt == "B":                                    # the idle ones glow
        for n in RB_TOP + RB_BOT + [s[0] for s in SB]:
            p.lit.setdefault(n, "glow")
    if opt == "C":                                    # glow and a breath (ARP's layer open: mid-way through it)
        for n in RB_TOP + RB_BOT + [s[0] for s in SB]:
            p.lit.setdefault(n, "glow")
        p.lit["ARP"] = "mid"
    return p


def main():
    p = as_built()
    p.screen = screen("SKIFF_home")
    for i in range(16):
        p.pads[i] = ("faint", None, str(i + 1))
    save(p.draw(), "smk37_panel.png")
    direction_sheet("smk37_pads_A.png", "PADS A: the FM-1's white keys, a second keyboard",
                    ["Pads are the 16 white keys F3-G5 everywhere (the layer's default): steps and tiles read like "
                     "text (top row 1-8); on HOME and the sound pages they are a keyboard, low notes on the bottom "
                     "row, lit where a note sounds. The keybed does what the FM-1's keys do. The FM-1 manual holds "
                     "word for word; HOME's pads only repeat the keybed."], pads_A)
    direction_sheet("smk37_pads_B.png", "PADS B: drum pads and mutes",
                    ["The top row plays: a DRUM track's 8 lanes (with velocity), a melodic track's scale from its "
                     "root. The bottom row: the six tracks' mutes, FILL and TAP, always. The keybed keeps every FM-1 "
                     "key job (steps, entries, effects), unlit: only the screen shows them."], pads_B)
    direction_sheet("smk37_pads_C.png", "PADS C: always the grid, never a second keyboard",
                    ["As A on step pages, the drum grid and every layer (PERFORM, FX, GLO, EDIT, SEL: their white "
                     "keys' tiles). Where the FM-1's white keys only play notes (HOME, sound pages), the pads show the "
                     "selected track's 16 steps of the bar with the playhead; a tap sets or clears a step with the "
                     "last note played. The keybed plays."], pads_C, rec=True)
    OVERVIEW.append(("PADS", [(regions(pads_A("home").draw(), PADS_BOXES), "A: a second keyboard", False),
                              (regions(pads_B("home").draw(), PADS_BOXES), "B: drum pads and mutes", False),
                              (regions(pads_C("home").draw(), PADS_BOXES), "C: always the grid", True)]))
    options_sheet("smk37_pad_colours.png", "PAD COLOURS: the DRUM grid and SEQ > STEP", [
        ("A: as the screen's tiles", ["Empty faint white, a step in the track's colour, a tie half, the edited "
                                      "step white, the playing step ringed white. The same picture as the STEP "
                                      "tiles on the screen."],
         lambda: stacked([pads_C("drum", "A"), pads_C("step", "A")], PADS_BOXES), True),
        ("B: dark until it plays", ["Empty off, a step at half, the playing step full: the darkest, the playhead "
                                    "the brightest thing on the panel."],
         lambda: stacked([pads_C("drum", "B"), pads_C("step", "B")], PADS_BOXES), False),
        ("C: the track's ground", ["Every pad in the track's colour, dim; a step full, the playhead white: the "
                                   "selected track is the whole surface."],
         lambda: stacked([pads_C("drum", "C"), pads_C("step", "C")], PADS_BOXES), False),
    ], None, 0.8)
    options_sheet("smk37_faders.png", "FADERS and FADER BANK", [
        ("A: a mixer", ["F1-F4 the LEVEL of the four tracks the screen shows (T1-T4; the six-track window: T2-T5, "
                        "T3-T6). FADER BANK steps LEVEL, PAN, REVERB, DELAY; its LED lit off LEVEL, the header "
                        "names it. A fader acts once it reaches the value (no jumps)."], lambda: faders("A"), True),
        ("B: the page's cards", ["F1-F4 the four cards of the page, as KNOB 1-4 (faders for sweeps); FADER BANK "
                                 "the next four. Doubles the knobs."], lambda: faders("B"), False),
        ("C: throws", ["F1-F4 PERFORM's throws (CUTOFF, REVERB, DELAY, DRIVE offsets) of the selected track, "
                       "always live; FADER BANK: the selected track or all."], lambda: faders("C"), False),
    ], [(188, 18, 392, 216), (1132, 8, 1504, 300)], 1.15)
    options_sheet("smk37_wheels.png", "WHEELS", [
        ("A: as MIDI in", ["Pitch: the selected track's bend, as a MIDI controller on its channel bends it (2 "
                           "semitones, or what RPN set). Mod: the MOD matrix's MODW source (its vibrato routing), "
                           "as CC1. Nothing new to learn."],
         lambda: wheels("A"), True),
        ("B: bend and CUTOFF", ["Pitch bends; mod opens the selected track's CUTOFF (up = open), back where it "
                                "was at the bottom."], lambda: wheels("B"), False),
        ("C: bend and the FX", ["Pitch bends; mod is the held effect's DEPTH (the FX layer's), the throws' "
                                "amount when none is held."], lambda: wheels("C"), False),
    ], (24, 14, 396, 284), 1.4)
    options_sheet("smk37_outer_keys.png", "THE TEN OUTER KEYS (C3-E3, G#5-C6; teal: the FM-1's 27, F3-G5)", [
        ("A: more range", ["The keybed plays C3-C6: the FM-1's F3-G5 keep their notes, the outer keys add a "
                           "fourth and a fifth. In layers they do nothing (the tiles are F3-G5's)."],
         lambda: outer("A"), True),
        ("B: left-hand drums", ["The DRUM track's lanes on any track: BD CP SD OH CH low, TM RS CB high, FILL and "
                                "TAP between."], lambda: outer("B"), False),
        ("C: off", ["Only the FM-1's 27 keys play; the outer ten are dead. Nothing to learn, nothing gained."],
         lambda: outer("C"), False),
    ], (20, 362, W - 20, 592), 0.75, rows=True)
    options_sheet("smk37_extra_buttons.png", "THE FOUR EXTRA BUTTONS", [
        ("A: SHIFT and the song", ["KNOB BANK is SHIFT (HOME held, as a button: HOME taps go home). FADER BANK: "
                                   "the faders' bank. < > the selected track's entry before and after, launched "
                                   "at the LAUNCH point (stopped: at once)."], lambda: extra("A"), True),
        ("B: SHIFT and undo", ["KNOB BANK SHIFT, FADER BANK the bank, < UNDO and > REDO in one press (now SAVE "
                               "held, then OCT- / OCT+ in the undo box)."], lambda: extra("B"), False),
        ("C: MENU and pages", ["KNOB BANK opens the MENU, FADER BANK the bank, < > the page before and after "
                               "(SELECT's job twice)."], lambda: extra("C"), False),
    ], (188, 14, 396, 362), 1.6)
    options_sheet("smk37_button_leds.png", "BUTTON LEDS (on or off only: no glow, no breath in the hardware)", [
        ("A: on or off", ["Lit and breathing show on; the glow and the mid level dark. MENU > LEDS hidden on the "
                          "SMK. As built."], lambda: leds("A"), True),
        ("B: a glow by frames", ["The idle buttons lit 1 frame in 4 (~78 Hz, a dim glow) so the labels read in the "
                                 "dark; to be checked on the unit for flicker."], lambda: leds("B"), False),
        ("C: glow and breath by frames", ["Four levels from skipped frames (all, 1 in 2, 1 in 4, 1 in 8): the "
                                          "idle glow, and a breath that steps through them (ARP's open layer, "
                                          "OCT+ in a dialog). The most like the FM-1; the most flicker to check."],
         lambda: leds("C"), False),
    ], [(188, 214, 396, 362), (1132, 186, 1504, 300)], 1.5)
    overview("smk37_sheet.png")


def overview(name):
    """the one sheet: a row per decision, its directions small, the recommended one framed"""
    th, cw, lw, gap = 220, 680, 330, 30
    rows = []
    for heading, opts in OVERVIEW:
        thumbs = []
        for im, t, r in opts:                        # each fitted into cw x th
            k = min(th / im.height, cw / im.width)
            thumbs.append((im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS), t, r))
        rows.append((heading, thumbs))
    sw = 30 + lw + 3 * (cw + gap) + 30
    sh = 130 + sum(max(t[0].height for t in thumbs) + 72 for _, thumbs in rows) + 20
    sheet = Image.new("RGB", (sw, sh), BG)
    g = ImageDraw.Draw(sheet)
    g.text((30, 24), "SKIFF ON THE SMK-37: THE CONTROLS PASS", font=font(True, 48), fill=INK)
    g.text((30, 80), "One pick per row; the framed one is recommended. Every row has its own sheet (design/mockups/"
           "smk37_*.png) and its words in design/SMK37_UX.md.", font=font(False, 24), fill=MID)
    y = 130
    for heading, thumbs in rows:
        for k, part in enumerate(wrap(g, heading.split(" (")[0].split(":")[0], font(True, 30), lw - 20)):
            g.text((30, y + 10 + k * 34), part, font=font(True, 30), fill=INK)
        for i, (im, t, r) in enumerate(thumbs):
            x = 30 + lw + i * (cw + gap)
            sheet.paste(im, (x, y))
            if r:
                g.rectangle((x - 5, y - 5, x + im.width + 4, y + im.height + 4), outline=GREEN, width=5)
            g.text((x, y + im.height + 10), t, font=font(True, 26), fill=GREEN if r else MID)
        y += max(t[0].height for t in thumbs) + 72
    save(sheet, name)


if __name__ == "__main__":
    main()
