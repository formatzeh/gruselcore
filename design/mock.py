#!/usr/bin/env python3
"""UI direction mockups for the FM-1 (240x240 RGB565), rendered pixel-true with Pillow/FreeType.
Three directions share one information architecture (rule 1: K1-K4 legend on top, in knob order) and differ in
type, colour and shape. Writes out/<dir>_<screen>.png (1x) and out/x3/<dir>_<screen>.png (3x, nearest).
  python3 mock.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
F = HERE / "fonts"
OUT = HERE / "out"
W = H = 240


def font(name, size, wght=None):
    f = ImageFont.truetype(str(F / name), size)
    if wght is not None:
        f.set_variation_by_axes([wght])
    return f


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# ---------------------------------------------------------------- the three directions
DIRS = {
    "A": dict(title="A  CONSOLE", aa=False,
              lab=("DepartureMono.otf", 11), name=("DepartureMono.otf", 11), val=("Jersey25.ttf", 25),
              num=("Jersey15.ttf", 15), big=("Jersey25.ttf", 50),
              bg="#000000", surf="#000000", text="#EDE6D9", mid="#9C958A", dim="#4A463F", line="#2B2824",
              accent="#FFB000", rec="#FF4433", ink="#000000",
              trk=["#FF7A45", "#3EC6F2", "#FFD23F", "#C79BF2"], radius=0, card="line"),
    "B": dict(title="B  BLOCKS", aa=True,
              lab=("BarlowCondensed-SemiBold.ttf", 13), name=("BarlowCondensed-Bold.ttf", 15),
              val=("BarlowCondensed-Bold.ttf", 26), num=("BarlowCondensed-Bold.ttf", 16),
              big=("BarlowCondensed-Bold.ttf", 44),
              bg="#0C0C0C", surf="#1E1E1E", text="#FFFFFF", mid="#B8B8B8", dim="#555555", line="#333333",
              accent="#FFFFFF", rec="#FF3B30", ink="#0C0C0C",
              trk=["#FF5A36", "#22C3B4", "#FFBF00", "#9580FF"], radius=0, card="block"),
    "C": dict(title="C  SOFT", aa=True,
              lab=("AtkinsonNext.ttf", 12, 600), name=("AtkinsonNext.ttf", 14, 700),
              val=("AtkinsonNext.ttf", 21, 700), num=("AtkinsonMono.ttf", 13, 600),
              big=("AtkinsonNext.ttf", 40, 700),
              bg="#0E1319", surf="#1A2230", text="#EEF3F8", mid="#9DAABA", dim="#4B5869", line="#263040",
              accent="#5EEAD4", rec="#FF6B6B", ink="#0E1319",
              trk=["#F5A524", "#45B8F5", "#B496FA", "#3DD68C"], radius=6, card="soft"),
}

# ---------------------------------------------------------------- shared content
TRACKS = [("DRUM", "DRUM", [1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0]),
          ("BASS", "ANALOG", [1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1]),
          ("KEYS", "FM6", [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0]),
          ("LEAD", "PHASE", [0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1])]
SEL, PLAYHEAD = 1, 9                    # the selected track (T2), the step playing


class S:
    """one direction's drawing kit"""

    def __init__(self, key):
        d = DIRS[key]
        self.key, self.d = key, d
        self.c = {k: hexc(v) for k, v in d.items() if isinstance(v, str) and v.startswith("#")}
        self.trk = [hexc(v) for v in d["trk"]]
        self.f = {k: font(*d[k]) for k in ("lab", "name", "val", "num", "big")}
        self.img = Image.new("RGB", (W, H), self.c["bg"])
        self.g = ImageDraw.Draw(self.img)
        self.g.fontmode = "L" if d["aa"] else "1"

    # primitives
    def text(self, xy, s, f, col, anchor="ls"):
        self.g.text(xy, s, font=self.f[f], fill=self.c.get(col, col) if isinstance(col, str) else col, anchor=anchor)

    def tw(self, s, f):
        return self.g.textlength(s, font=self.f[f])

    def box(self, x0, y0, x1, y1, fill=None, outline=None, r=None, w=1):
        r = self.d["radius"] if r is None else r
        fill = self.c.get(fill, fill) if isinstance(fill, str) else fill
        outline = self.c.get(outline, outline) if isinstance(outline, str) else outline
        if r:
            self.g.rounded_rectangle([x0, y0, x1, y1], r, fill=fill, outline=outline, width=w)
        else:
            self.g.rectangle([x0, y0, x1, y1], fill=fill, outline=outline, width=w)

    def hline(self, y, col="line", x0=0, x1=W - 1, dotted=False):
        for x in range(x0, x1 + 1, 2 if dotted else 1):
            self.g.point((x, y), fill=self.c[col])

    # ------------------------------------------------ shared components
    def header(self, title, sub=None):
        k = self.key
        y = 15
        # play state + position
        self.g.polygon([(6, 5), (6, 15), (14, 10)], fill=self.c["accent"] if k != "B" else self.c["text"])
        nf = "lab" if k == "A" else "num"          # A: the pixel mono reads cleaner than Jersey this small
        self.text((19, y), "3.2", nf, "text")
        bpm = "118"
        self.text((52, y), bpm, nf, "text")
        self.text((52 + self.tw(bpm, nf) + 3, y), "BPM", "lab", "mid")
        # the page / project title, right
        self.text((234, y), title, "lab", "mid", anchor="rs")
        if k == "A":
            self.hline(20, "line")
        elif k == "B":
            pass
        else:
            self.hline(21, "line")

    def cards(self, items, hot=None, y0=24, h=44):
        """K1..K4: one row of four, in knob order (label, value, unit, gauge 0..1)"""
        k = self.key
        for i, (lab, val, unit, g) in enumerate(items):
            x0 = 1 + i * 60
            x1 = x0 + 57
            on = i == hot
            if k == "A":
                if i:
                    for yy in range(y0 + 2, y0 + h - 2, 2):
                        self.g.point((x0 - 2, yy), fill=self.c["line"])
                self.text((x0 + 3, y0 + 11), f"K{i + 1} {lab}", "lab", "accent" if on else "mid")
                self.text((x0 + 3, y0 + 34), val, "val", "accent" if on else "text")
                if unit:
                    self.text((x0 + 4 + self.tw(val, "val"), y0 + 34), unit, "lab", "mid")
                self.g.rectangle([x0 + 3, y0 + 39, x0 + 3 + round(50 * g), y0 + 40], fill=self.c["accent" if on else "text"])
                self.g.rectangle([x0 + 3 + round(50 * g) + 1, y0 + 39, x0 + 53, y0 + 40], fill=self.c["line"])
            elif k == "B":
                fill = self.c["text"] if on else self.c["surf"]
                ink = self.c["ink"] if on else self.c["text"]
                self.box(x0, y0, x1, y0 + h, fill=fill)
                self.text((x0 + 4, y0 + 13), lab, "lab", self.c["ink"] if on else self.c["mid"])
                self.text((x0 + 4, y0 + 38), val, "val", ink)
                if unit:
                    self.text((x1 - 3, y0 + 38), unit, "lab", self.c["ink"] if on else self.c["mid"], anchor="rs")
                self.g.rectangle([x0, y0 + h - 2, x0 + round(57 * g), y0 + h], fill=self.trk[SEL] if not on else self.c["ink"])
            else:
                self.box(x0, y0, x1, y0 + h, fill=self.c["surf"], outline=self.c["accent"] if on else None, w=1)
                self.text((x0 + 6, y0 + 15), lab, "lab", "accent" if on else "mid")
                if unit:                       # the unit on the label's row: the value keeps the card's width
                    self.text((x1 - 5, y0 + 15), unit, "lab", "mid", anchor="rs")
                self.text((x0 + 6, y0 + 37), val, "val", "text")
                # a small arc-less gauge: 3 px pill
                self.box(x0 + 6, y0 + 40, x1 - 6, y0 + 41, fill=self.c["line"], r=1)
                self.box(x0 + 6, y0 + 40, x0 + 6 + round((51 - 12) * g), y0 + 41,
                         fill=self.c["accent"] if on else self.c["mid"], r=1)

    def footer(self, left, right, y=233):
        k = self.key
        if k == "A":
            self.hline(219, "line")
        elif k == "C":
            self.hline(219, "line")
        self.text((6, y), left, "lab", "mid")
        self.text((234, y), right, "lab", "mid", anchor="rs")

    def chip(self, x, y, n, col, w=13, h=13):
        """a track number on its colour (colour never alone: the number is always there)"""
        k = self.key
        if k == "A":
            self.g.rectangle([x, y, x + w - 1, y + h - 1], fill=col)
            self.text((x + w / 2, y + h - 3), str(n), "lab", "ink", anchor="ms")
        elif k == "B":
            self.g.rectangle([x, y, x + w - 1, y + h - 1], fill=col)
            self.text((x + w / 2, y + h - 2), str(n), "num", "ink", anchor="ms")
        else:
            self.box(x, y, x + w - 1, y + h - 1, fill=col, r=4)
            self.text((x + w / 2 + 0.5, y + h - 3), str(n), "num", "ink", anchor="ms")

    def save(self, name):
        img = self.img.point(lambda v: v)        # RGB565: what the panel can show
        r, g, b = img.split()
        r = r.point(lambda v: ((v >> 3) << 3) | (v >> 5))
        g = g.point(lambda v: ((v >> 2) << 2) | (v >> 6))
        b = b.point(lambda v: ((v >> 3) << 3) | (v >> 5))
        img = Image.merge("RGB", (r, g, b))
        img.save(OUT / f"{self.key}_{name}.png")
        for z in (2, 3):                 # pixel-true enlargements for the review canvas
            (OUT / f"x{z}").mkdir(parents=True, exist_ok=True)
            img.resize((W * z, H * z), Image.NEAREST).save(OUT / f"x{z}" / f"{self.key}_{name}.png")


# ---------------------------------------------------------------- screens
HOME_K = [("CUT", "2.4", "k", 0.62), ("RES", "34", "%", 0.34), ("ATK", "4", "ms", 0.08), ("REL", "180", "ms", 0.3)]


def lanes(s, y0=74, lh=34):
    k = s.key
    for i, (name, eng, steps) in enumerate(TRACKS):
        y = y0 + i * lh
        col = s.trk[i]
        sel = i == SEL
        if k == "C":
            s.box(3, y, 236, y + lh - 4, fill=s.c["surf"], outline=s.c["text"] if sel else None)
        elif k == "B":
            s.box(0, y, 239, y + lh - 3, fill=col if sel else s.c["surf"])
        elif sel:
            s.g.rectangle([1, y - 1, 238, y + lh - 3], outline=s.c["text"])
        # number + name + engine
        ink_name = s.c["ink"] if (k == "B" and sel) else s.c["text"]
        ink_eng = s.c["ink"] if (k == "B" and sel) else s.c["mid"]
        if k == "B":
            s.text((6, y + 20), str(i + 1), "val", ink_name if sel else col)
            s.text((24, y + 13), name, "name", ink_name)
            s.text((24, y + 26), eng, "lab", ink_eng)
        else:
            s.chip(6, y + 4, i + 1, col)
            s.text((24, y + 14), name, "name", ink_name)
            s.text((6, y + 27), eng, "lab", ink_eng)
        # the bar's 16 steps
        x0, cw = 80, 9
        for j, on in enumerate(steps):
            cx = x0 + j * cw + (j // 4) * 2
            cy = y + 8
            if k == "A":
                if on:
                    s.g.rectangle([cx, cy, cx + cw - 3, cy + 12], fill=col)
                else:
                    s.g.rectangle([cx + 3, cy + 5, cx + cw - 6, cy + 7], fill=s.c["dim"])
            elif k == "B":
                fill = (s.c["ink"] if sel else col) if on else (mix(col, s.c["ink"], 0.55) if sel else s.c["line"])
                s.g.rectangle([cx, cy - 1, cx + cw - 3, cy + 14], fill=fill)
            else:
                fill = col if on else s.c["line"]
                s.box(cx, cy + (0 if on else 4), cx + cw - 3, cy + (12 if on else 8), fill=fill, r=2)
        # the playhead over the step playing
        px = x0 + PLAYHEAD * cw + (PLAYHEAD // 4) * 2 - 2
        if k == "B":
            s.g.rectangle([px, y + 2, px, y + lh - 6], fill=s.c["ink"] if sel else s.c["text"])
        else:
            s.g.rectangle([px, y + 3, px, y + lh - 7], fill=s.c["rec"])


def home(s, title="SKETCH 01"):
    s.header(title)
    s.cards(HOME_K, hot=0)
    lanes(s)
    s.footer("HOLD HOME: SHIFT", "HOME")


def sound(s):
    s.header("ENV")
    s.cards([("ATK", "4", "ms", 0.08), ("DEC", "320", "ms", 0.45), ("SUS", "62", "%", 0.62), ("REL", "180", "ms", 0.3)], hot=1)
    k = s.key
    x0, y0, x1, y1 = 8, 82, 231, 206
    if k == "C":
        s.box(3, 74, 236, 212, fill=s.c["surf"])
    elif k == "B":
        s.box(0, 74, 239, 212, fill=s.c["surf"])
    for gy in (y0, (y0 + y1) // 2, y1):
        s.hline(gy, "line", x0, x1, dotted=(k != "B"))
    sus = y0 + round((y1 - y0) * (1 - 0.62))
    pts = [(x0, y1), (x0 + 6, y0 + 2), (x0 + 74, sus), (x0 + 168, sus), (x1, y1)]
    col = s.trk[SEL]
    s.g.line(pts, fill=col, width=2 if k != "A" else 1, joint="curve")
    for p in pts[1:4]:
        s.box(p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2, fill=s.c["accent"] if p == pts[2] else col, r=2 if k == "C" else 0)
    s.footer(f"{SEL + 1} BASS  ANALOG  ACID", "ENV 1/2")


def step(s):
    s.header("STEP")
    s.cards([("STEP", "5", "/16", 0.3), ("NOTE", "C2", "", 0.4), ("VELO", "96", "", 0.75), ("CHNC", "75", "%", 0.75)], hot=1)
    k = s.key
    notes = ["C2", "", "C2", "", "D#2", "G1", "", "", "C2", "", "A#1", "", "", "C3", "", "G2"]
    cw, ch = 28, 32
    for j, n in enumerate(notes):
        r, c = divmod(j, 8)
        x = 4 + c * (cw + 1)
        y = 80 + r * (ch + 26)
        cur, play = j == 4, j == PLAYHEAD - 1 + 1
        col = s.trk[SEL]
        if k == "A":
            if n:
                s.g.rectangle([x, y, x + cw - 2, y + ch], fill=col)
            else:
                s.g.rectangle([x, y, x + cw - 2, y + ch], outline=s.c["dim"])
            if cur:
                s.g.rectangle([x - 1, y - 1, x + cw - 1, y + ch + 1], outline=s.c["accent"])
                s.g.rectangle([x - 2, y - 2, x + cw, y + ch + 2], outline=s.c["accent"])
            s.text((x + cw / 2 - 1, y + ch - 4), n, "lab", "ink", anchor="ms")
        elif k == "B":
            fill = col if n else s.c["surf"]
            if cur:
                fill = s.c["text"]
            s.g.rectangle([x, y, x + cw - 2, y + ch], fill=fill)
            s.text((x + cw / 2 - 1, y + ch - 5), n, "lab", "ink", anchor="ms")
        else:
            s.box(x, y, x + cw - 2, y + ch, fill=col if n else s.c["surf"],
                  outline=s.c["accent"] if cur else None, w=2 if cur else 1, r=4)
            s.text((x + cw / 2 - 1, y + ch - 5), n, "lab", "ink" if n else "dim", anchor="ms")
        # step number under each cell; the playing step marked
        s.text((x + cw / 2 - 1, y + ch + 13), str(j + 1), "lab", "rec" if play else "mid", anchor="ms")
        if j == 2 or j == 13:   # chance under 100 %
            s.g.rectangle([x + 2, y + 2, x + 5, y + 5], fill=s.c["ink"])
    s.footer("PRESETS: STEP", "STEP 1/2")


def perform(s):
    s.header("PERFORM  BAR")
    s.cards([("CUT", "+0", "", 0.5), ("VERB", "+18", "", 0.68), ("DLY", "+0", "", 0.5), ("DRV", "+30", "", 0.8)], hot=3)
    k = s.key
    cur = [0, 1, 0, 2]      # pattern playing per track (A, B, A, C)
    nxt = [None, 2, None, None]
    muted = [False, False, True, False]
    for i, (name, _, _) in enumerate(TRACKS):
        y = 78 + i * 26
        col = s.trk[i]
        if k == "B":
            s.text((6, y + 16), str(i + 1), "name", col)
        else:
            s.chip(4, y + 3, i + 1, col)
        for p in range(16):
            x = 24 + p * 13
            letter = "ABCDEFGHIJKLMNOP"[p]
            is_cur, is_next = p == cur[i], p == nxt[i]
            if is_cur:
                fill = s.c["dim"] if muted[i] else col
                s.box(x, y + 2, x + 11, y + 17, fill=fill, r=3 if k == "C" else 0)
                s.text((x + 6, y + 14), letter, "lab", "ink", anchor="ms")
            elif is_next:
                s.box(x, y + 2, x + 11, y + 17, outline=col, r=3 if k == "C" else 0)
                s.text((x + 6, y + 14), letter, "lab", col, anchor="ms")
            elif p < 4:
                s.text((x + 6, y + 14), letter, "lab", "mid", anchor="ms")
            else:
                s.g.rectangle([x + 5, y + 9, x + 6, y + 10], fill=s.c["dim"])
        if muted[i]:
            s.text((236, y + 14), "M", "lab", "rec", anchor="rs")
    # scenes
    yS = 186
    s.text((6, yS + 12), "SCN", "lab", "mid")
    for n in range(8):
        x = 34 + n * 25
        on = n == 2
        s.box(x, yS + 1, x + 21, yS + 16, fill=s.c["text"] if on else None, outline=s.c["dim"] if not on else None,
              r=3 if k == "C" else 0)
        s.text((x + 11, yS + 13), str(n + 1), "lab", "ink" if on else "mid", anchor="ms")
    s.footer("WHITE: PATTERN", "BLACK: MUTE")


def take(s):
    home(s)
    k = s.key
    x0, y0, x1, y1 = 20, 84, 219, 156
    s.box(x0 - 1, y0 - 1, x1 + 1, y1 + 1, fill=s.c["bg"], r=s.d["radius"] + 1 if s.d["radius"] else 0)
    s.box(x0, y0, x1, y1, fill=s.c["text"] if k != "C" else s.c["surf"],
          outline=s.c["accent"] if k == "C" else None, w=2)
    ink = s.c["ink"] if k != "C" else s.c["text"]
    s.chip(x0 + 10, y0 + 9, SEL + 1, s.trk[SEL], w=16, h=16)
    s.text((x0 + 33, y0 + 23), "TAKE KEPT", "name", ink)
    s.text((x0 + 10, y0 + 44), "14 notes, 3 knob moves", "lab", ink if k != "C" else s.c["mid"])
    s.text((x0 + 10, y0 + 62), "HOLD SAVE: UNDO", "lab", ink if k != "C" else s.c["accent"])


def confirm(s):
    step(s)
    k = s.key
    # dim the page under the dialog
    ov = Image.new("RGB", (W, H), s.c["bg"])
    s.img = Image.blend(s.img, ov, 0.7)
    s.g = ImageDraw.Draw(s.img)
    s.g.fontmode = "L" if s.d["aa"] else "1"
    x0, y0, x1, y1 = 16, 56, 223, 196
    s.box(x0, y0, x1, y1, fill=s.c["surf"] if k != "A" else s.c["bg"], outline=s.c["text"] if k == "A" else None)
    s.text((120, y0 + 30), "CLEAR TRACK 2?", "name", "text", anchor="ms")
    s.text((120, y0 + 50), "16 steps, 9 notes", "lab", "mid", anchor="ms")
    s.text((120, y0 + 64), "undo: hold SAVE", "lab", "mid", anchor="ms")
    bw, by = 88, y0 + 80
    # CANCEL is the default: filled
    s.box(x0 + 12, by, x0 + 12 + bw, by + 28, fill=s.c["text"])
    s.text((x0 + 12 + bw / 2, by + 19), "CANCEL", "name", "ink", anchor="ms")
    s.box(x1 - 12 - bw, by, x1 - 12, by + 28, outline=s.c["rec"], w=1)
    s.text((x1 - 12 - bw / 2, by + 19), "CLEAR", "name", "rec", anchor="ms")
    s.text((x0 + 12 + bw / 2, by + 42), "OCT-", "lab", "mid", anchor="ms")
    s.text((x1 - 12 - bw / 2, by + 42), "OCT+", "lab", "mid", anchor="ms")


SCREENS = [("home", home), ("sound", sound), ("step", step), ("perform", perform), ("take", take), ("confirm", confirm)]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for key in DIRS:
        for name, fn in SCREENS:
            s = S(key)
            fn(s)
            s.save(name)
    print("wrote", len(DIRS) * len(SCREENS), "screens to", OUT)
