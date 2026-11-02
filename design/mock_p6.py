#!/usr/bin/env python3
"""Phase 6 mockups (six tracks; 5 and 6 light), direction B as built. The track screens keep today's sizes and show
four tracks: T1-T4, or with T5 / T6 selected the four ending at it (T2-T5, T3-T6), a scroll bar at the edge saying
where (HOME, SEQ > SONG, PERFORM, the MIXER and its LARGE look, the GLO cards); the key maps (GLO, FX) show all six;
the EDIT layer on track 5; the splash.
The firmware's faces (assets/fonts: Barlow Condensed Medium 13 = S, Bold 16 = M, Bold 24 = V). Screens start from
the firmware's own renders where they keep what they have (tests/ui_render.c, BLOCKS + SKIFF: P6_RENDERS, default
build/ui_new/ppm): a track that only moves is its own lane, strip or card, moved; track 5's is track 1's (or 3's)
recoloured and renamed; the rest is drawn in their geometry. Writes out/P6_<screen>.png (1x, x2, x3) and
mockups/p6_sheet.png.
  P6_RENDERS=~/skiff-fast/build/ui_new/ppm python3 mock_p6.py
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw
import mock
from mock import S, OUT, W, H, mix, HERE, hexc

mock.F = HERE.parent / "assets" / "fonts"
mock.DIRS["B"]["lab"] = ("BarlowCondensed-Medium.ttf", 13)
mock.DIRS["B"]["val"] = ("BarlowCondensed-Bold.ttf", 24)
RENDERS = Path(os.path.expanduser(os.environ.get("P6_RENDERS", str(HERE.parent / "build" / "ui_new" / "ppm"))))
TRK6 = ["#FF5A36", "#22C3B4", "#FFBF00", "#9580FF", "#FF6FAE", "#A3E635"]   # + T5 pink, T6 lime
SEL, TOP = 4, 1                                          # track 5 selected: tracks 2..5 shown
LET = "ABCDEFGHIJKLMNOP"


def q565(c):                                             # (what the panel shows of a colour)
    r, g, b = c
    return ((r >> 3) << 3) | (r >> 5), ((g >> 2) << 2) | (g >> 6), ((b >> 3) << 3) | (b >> 5)


def kit(base=None):
    s = S("B")
    s.trk = [hexc(c) for c in TRK6]
    s.f["m"] = mock.font("BarlowCondensed-Bold.ttf", 16)
    if base:                                             # the firmware's render under what changes
        s.img = Image.open(RENDERS / f"{base}.ppm").convert("RGB")
        s.g = ImageDraw.Draw(s.img)
        s.g.fontmode = "L"
    return s


def redraw(s):
    s.g = ImageDraw.Draw(s.img)
    s.g.fontmode = "L"


def recolour(im, box, a0, a1, b1):
    """the pixels on the line from a0 to a1 (a ground and a colour, and the anti-aliasing between) moved onto the line
    from a0 to b1; others (white text, say) left as they are"""
    x0, y0, x1, y1 = box
    px = im.load()
    d = [a1[i] - a0[i] for i in range(3)]
    dd = sum(v * v for v in d) or 1
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            p = px[x, y]
            t = max(0.0, min(1.0, sum((p[i] - a0[i]) * d[i] for i in range(3)) / dd))
            if sum((p[i] - a0[i] - t * d[i]) ** 2 for i in range(3)) < 400:
                px[x, y] = tuple(round(a0[i] + t * (b1[i] - a0[i])) for i in range(3))


def remap(im, box, a0, a1, b0, b1):
    """the pixels in box between colours a0 (ground) .. a1 (ink) moved onto b0 .. b1, per channel: a cell lit,
    unlit or dimmed"""
    x0, y0, x1, y1 = box
    px = im.load()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            p = px[x, y]
            t = sum((p[i] - a0[i]) / ((a1[i] - a0[i]) or 1) for i in range(3)) / 3
            t = min(1.0, max(0.0, t))
            px[x, y] = tuple(round(b0[i] + (b1[i] - b0[i]) * t) for i in range(3))


def tile(im, seed):
    """the box of the tile under seed: the pixels of its ground colour reached from it (its text is holes in it)"""
    px, c = im.load(), im.getpixel(seed)
    todo, seen = [seed], {seed}
    while todo:
        x, y = todo.pop()
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if q not in seen and 0 <= q[0] < im.width and 0 <= q[1] < im.height and px[q] == c:
                seen.add(q)
                todo.append(q)
    xs, ys = [p[0] for p in seen], [p[1] for p in seen]
    return min(xs), min(ys), max(xs), max(ys)


def icon(src, search, bg):
    """the icon in the search box of a render (the pixels unlike its cell's ground), cropped with its ground"""
    x0, y0, x1, y1 = search
    px = src.load()
    pts = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
           if sum(abs(px[x, y][i] - bg[i]) for i in range(3)) > 24]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return src.crop((min(xs), min(ys), max(xs) + 1, max(ys) + 1))


def vbar(s, x, y0, y1, top=TOP):
    """the scroll bar: four of six tracks shown, the thumb where"""
    s.g.rectangle([x, y0, x + 1, y1], fill=s.c["line"])
    h = y1 - y0
    s.g.rectangle([x, y0 + round(h * top / 6), x + 1, y0 + round(h * (top + 4) / 6)], fill=s.c["mid"])


def hbar(s, x0, x1, y, top=TOP):
    s.g.rectangle([x0, y, x1, y + 1], fill=s.c["line"])
    w = x1 - x0
    s.g.rectangle([x0 + round(w * top / 6), y, x0 + round(w * (top + 4) / 6), y + 1], fill=s.c["mid"])


def header(s, title, playing=True, extra=None, sel=SEL):
    s.box(0, 0, 239, 22, fill=s.c["bg"])
    if playing:
        s.g.polygon([(5, 5), (5, 15), (13, 10)], fill=s.c["text"])
    else:
        s.g.rectangle([5, 6, 12, 13], fill=s.c["text"])
    s.text((19, 16), "1.2", "num", "text")
    s.text((45, 16), "124", "num", "text")
    s.text((45 + s.tw("124", "num") + 3, 16), "BPM", "lab", "mid")
    s.text((235, 16), title, "lab", "mid", anchor="rs")
    if extra:
        s.text((235 - s.tw(title, "lab") - 6, 16), extra, "lab", s.trk[sel], anchor="rs")


def footer(s, left, right):
    s.text((5, 234), left, "lab", "mid")
    s.text((235, 234), right, "lab", "mid", anchor="rs")


def gauges(s, frm, to, y0=60, y1=76):
    """the cards' gauges: the selected track's colour"""
    px = s.img.load()
    a, b = q565(frm), q565(to)
    for y in range(y0, y1):
        for x in range(240):
            if px[x, y] == a:
                px[x, y] = b


def footer_track(s, k, eng, name):
    s.box(0, 218, 150, 239, fill=s.c["bg"])
    s.text((9, 235), str(k + 1), "val", s.trk[k])
    s.text((25, 234), eng, "lab", "text")
    s.text((25 + s.tw(eng, "lab") + 9, 234), name, "lab", "text")


# ---------------------------------------------------------------- HOME: today's lanes, four at a time
def home(s):
    src = s.img.copy()
    t1, t5 = s.trk[0], s.trk[4]
    header(s, "SKETCH 01")
    gauges(s, t1, t5)
    s.box(0, 74, 239, 215, fill=s.c["bg"])
    for pos in range(3):                                 # T2..T4: their own lanes, one up
        y = 76 + 34 * (pos + 1)
        s.img.paste(src.crop((0, y, 240, y + 31)), (0, 76 + 34 * pos))
    lane = src.crop((0, 76, 240, 107))                   # T5: T1's band, pink, its name
    recolour(lane, (0, 0, 239, 30), s.c["ink"], t1, t5)
    s.img.paste(lane, (0, 76 + 34 * 3))
    redraw(s)
    y = 76 + 34 * 3
    s.box(4, y + 1, 96, y + 29, fill=q565(t5))
    s.text((9, y + 24), "5", "val", "ink")
    s.text((28, y + 14), "PIANO", "m", "ink")
    s.text((28, y + 26), "SAMPLE", "lab", "ink")
    vbar(s, 238, 76, 208)


# ---------------------------------------------------------------- SEQ > SONG: today's rows, four at a time
LISTS = [[(1, 2), (2, 1), (1, 1), (3, 2)] + [None] * 12,
         [(5, 1), (5, 1), (6, 2), (7, 1), (6, 1)] + [None] * 11,
         [(9, 4), (10, 4)] + [None] * 14,
         [(13, 1), None, (14, 1), (15, 1), (16, 1), (14, 1)] + [None] * 10,
         [(17, 2), (18, 1)] + [None] * 14,
         [(19, 1), (19, 1), (20, 1), (21, 3)] + [None] * 12]
CUR = [1, 2, 0, 3, 0, 2]
NXT = [2, 3, 1, 4, 1, 3]


def song(s, cursor=1):
    header(s, "SONG", True, "SONG ON")
    s.cards([("ENTRY", LET[cursor], "", (cursor + 0.5) / 16), ("PATTERN", "18", "", 18 / 64), ("REPS", "1", "x", 1 / 16),
             ("SONG", "ON", "", 1.0)], hot=None, y0=28)
    gauges(s, s.trk[1], s.trk[SEL])
    for r in range(4):
        i = TOP + r
        lst, y = LISTS[i], 80 + 27 * r                   # 24 px bands, 27 apart: y 80 .. 184 (today's)
        col, band = s.trk[i], i == SEL
        if band:
            s.box(0, y, 236, y + 23, fill=col)
        s.text((5, y + 18), str(i + 1), "m", s.c["ink"] if band else col)
        for p, e in enumerate(lst):
            x0 = 22 + (p * 134 + 5) // 10                # (13.4 apart: the scroll bar at 238)
            x1, ty = x0 + 12, y + 2
            if e is None:
                s.g.rectangle([x0 + 5, ty + 8, x0 + 6, ty + 9], fill=mix(col, s.c["ink"], 0.55) if band else s.c["dim"])
                if band and p == cursor:
                    s.box(x0, ty, x1, ty + 17, outline=s.c["text"])
                continue
            pid, reps = e
            if band and p == cursor:
                fill, ink = s.c["text"], s.c["ink"]
            elif p == CUR[i]:
                fill, ink = (s.c["ink"], col) if band else (col, s.c["ink"])
            elif band:
                fill, ink = mix(col, s.c["ink"], 0.35), s.c["ink"]
            else:
                fill, ink = s.c["surf"], s.c["mid"]
            s.box(x0, ty, x1, ty + 17, fill=fill)
            s.text(((x0 + x1) / 2 + 0.5, ty + 13), f"{pid:02d}", "lab", ink, anchor="ms")
            if p == NXT[i]:
                s.box(x0 - 1, ty - 1, x1 + 1, ty + 18, outline=s.c["ink"] if band else col)
            for k in range(min(reps, 4) - 1):
                s.g.rectangle([x0 + 1 + 3 * k, ty + 19, x0 + 2 + 3 * k, ty + 19], fill=s.c["ink"] if band else col)
    vbar(s, 238, 80, 184)
    footer(s, "OCT+: PLAY  EDIT: CLEAR", "SONG 5/8")


# ---------------------------------------------------------------- PERFORM: today's rows, four tracks and the scenes
def perform(s):
    header(s, "PERFORM BAR")
    s.cards([("CUT", "+12", "", 0.7), ("VERB", "+0", "", 0.5), ("DLY", "+0", "", 0.5), ("DRV", "+0", "", 0.5)],
            hot=None, y0=28)
    gauges(s, s.trk[1], s.trk[SEL])
    kept = [[0, 2, 15], [0, 1, 2], [0, 1], [0, 1, 2, 3], [0, 1], [0, 1, 2, 3]]
    cur = [2, 1, 0, 3, 0, 2]
    nxt = [5, None, None, None, 1, None]
    muted = [False, True, False, False, False, False]
    arm = [False, False, True, False, False, True]
    for r in range(5):
        y = 80 + 27 * r                                  # 22 px rows, 27 apart: y 80 .. 210 (today's)
        ty = y + 3
        if r == 4:
            s.text((6, y + 15), "SCN", "lab", "mid")
            for p in range(16):
                x = 28 + 13 * p
                if p in (0, 4):
                    s.box(x, ty, x + 11, ty + 15, outline=s.c["dim"])
                    s.text((x + 6, ty + 12), str(p + 1), "lab", "mid", anchor="ms")
                else:
                    s.g.rectangle([x + 5, y + 10, x + 6, y + 11], fill=s.c["dim"])
            break
        i = TOP + r
        col, band = s.trk[i], i == SEL
        if band:
            s.box(3, y, 236, y + 21, fill=col)
        s.text((6, y + 17), str(i + 1), "m", s.c["ink"] if band else col)
        for p in range(16):
            x = 17 + 13 * p
            if p == nxt[i]:
                s.box(x, ty, x + 11, ty + 15, outline=s.c["ink"] if band else col)
                s.text((x + 6, ty + 12), LET[p], "lab", s.c["ink"] if band else col, anchor="ms")
            elif p == cur[i]:
                tile_c = s.c["ink"] if band else s.c["dim"] if muted[i] else col
                s.box(x, ty, x + 11, ty + 15, fill=tile_c)
                s.text((x + 6, ty + 12), LET[p], "lab", col if band else s.c["text"] if muted[i] else s.c["ink"],
                       anchor="ms")
            elif p in kept[i]:
                s.text((x + 6, ty + 12), LET[p], "lab", s.c["ink"] if band else s.c["mid"], anchor="ms")
            else:
                s.g.rectangle([x + 5, y + 10, x + 6, y + 11], fill=mix(col, s.c["ink"], 0.55) if band else s.c["dim"])
        if muted[i] or arm[i]:
            x = 17 + 13 * 16
            if arm[i]:
                s.box(x, ty, x + 11, ty + 15, outline=s.c["ink"] if band else s.c["rec"])
            s.text((x + 6, ty + 12), "M", "lab", s.c["ink"] if band else s.c["rec"] if muted[i] else s.c["mid"],
                   anchor="ms")
    vbar(s, 238, 80, 183)
    footer(s, "WHITE: PATTERN", "BLACK: MUTE")


# ---------------------------------------------------------------- MIXER: today's four strips, scrolled
def strips(s, y0, y1, num, name):
    """T2..T4's strips moved one left; T5's is T1's with its number and name (num, name: their places in a strip)"""
    src = s.img.copy()
    for pos in range(3):
        x = 3 + 59 * (pos + 1)
        s.img.paste(src.crop((x, y0, x + 57, y1)), (3 + 59 * pos, y0))
    s.img.paste(src.crop((3, y0, 60, y1)), (3 + 59 * 3, y0))
    redraw(s)
    x0 = 3 + 59 * 3
    g = s.img.getpixel((x0 + 2, y0 + 2))
    (nx, nb), (mx, mb, mf) = num, name
    s.box(x0 + 2, nb - 19, x0 + 30, nb + 1, fill=g)
    s.box(x0 + 2, mb - 11, x0 + 55, mb + 2, fill=g)
    s.text((x0 + nx, nb), "5", "val", s.trk[4])
    s.text((x0 + mx, mb), "PIANO", mf, "text")


def mixer(s):
    gauges(s, s.trk[0], s.trk[4])
    strips(s, 76, 214, (9, 105), (8, 118, "lab"))
    footer_track(s, 4, "SAMPLE", "PIANO")
    hbar(s, 3, 236, 215)


def mixer_large(s):
    strips(s, 136, 214, (5, 157), (5, 170, "lab"))
    footer_track(s, 4, "SAMPLE", "PIANO")
    hbar(s, 3, 236, 215)


# ---------------------------------------------------------------- GLO and FX layers: all six tracks on the keys
SOLO_KEYS = ["F", "G", "A", "B", "E", "G"]
MUTE_KEYS = ["F#", "G#", "A#", "C#", "D#", "F#"]


def mute_row(s, y0, spk, lit=()):
    for c in range(6):                                   # MUTE 1-6 on the black keys, 36 px cells
        x0 = 4 + 39 * c
        on = c in lit
        g = s.c["mid"] if on else s.c["surf"]
        s.box(x0, y0, x0 + 35, y0 + 21, fill=g)
        s.text((x0 + 3, y0 + 15), MUTE_KEYS[c], "lab", s.c["ink"] if on else s.c["mid"])
        ic = spk.copy()
        if on:
            remap(ic, (0, 0, ic.width - 1, ic.height - 1), s.c["surf"], s.c["mid"], g, s.c["ink"])
        s.img.paste(ic, (x0 + 18, y0 + 6))
        s.text((x0 + 33, y0 + 16), str(c + 1), "m", s.c["ink"] if on else s.trk[c], anchor="rs")


def glo(s):
    src = s.img.copy()
    spk = icon(src, (30, 184, 41, 197), src.getpixel((8, 182)))
    ic = [icon(src, b, src.getpixel((8, 136))) for b in ((27, 136, 40, 152), (83, 136, 100, 154), (199, 136, 216, 154))]
    for pos in range(3):                                 # the cards: the four tracks shown, T2..T5
        x = 3 + 59 * (pos + 1)
        s.img.paste(src.crop((x, 26, x + 57, 74)), (3 + 59 * pos, 26))
    card = src.crop((3 + 59 * 2, 26, 3 + 59 * 2 + 57, 74))          # T5's: T3's card, pink, its number
    recolour(card, (0, 0, 56, 47), src.getpixel((3 + 59 * 2 + 30, 30)), s.trk[2], s.trk[4])
    s.img.paste(card, (3 + 59 * 3, 26))
    redraw(s)
    x0 = 3 + 59 * 3
    s.box(x0 + 3, 30, x0 + 13, 44, fill=src.getpixel((3 + 59 * 2 + 30, 30)))
    s.text((x0 + 4, 42), "5", "m", s.trk[4])
    s.box(0, 74, 239, 215, fill=s.c["bg"])
    for c in range(6):                                   # SOLO 1-6: F G A B, then E and G above C D
        x0 = 4 + 39 * c
        held = c == 4
        g = s.c["text"] if held else s.c["surf"]
        s.box(x0, 88, x0 + 35, 129, fill=g)
        s.text((x0 + 4, 104), SOLO_KEYS[c], "lab", s.c["ink"] if held else s.c["mid"])
        s.text((x0 + 22, 109), str(c + 1), "val", s.c["ink"] if held else s.trk[c], anchor="ms")
        s.text((x0 + 18, 125), "SOLO", "lab", s.c["ink"] if held else s.c["text"], anchor="ms")
        s.g.polygon([(x0 + 29, 90), (x0 + 33, 90), (x0 + 33, 94)], fill=s.c["ink"] if held else s.c["text"])
    for q, (key, word) in enumerate((("C", "ALL"), ("D", "FILL"), ("F", "TAP"))):
        x0 = 4 + 78 * q                                  # the three that stay, two columns each
        s.box(x0, 134, x0 + 74, 175, fill=s.c["surf"])
        s.text((x0 + 6, 150), key, "lab", "mid")
        s.img.paste(ic[q], (x0 + 20, 152 - ic[q].height))
        s.text((x0 + 37, 169), word, "m", "text", anchor="ms")
    mute_row(s, 180, spk, lit=(1, 3))


def fx(s):
    src = s.img.copy()
    spk = icon(src, (30, 184, 41, 197), src.getpixel((8, 182)))
    s.box(0, 178, 239, 203, fill=s.c["bg"])
    mute_row(s, 180, spk)


# ---------------------------------------------------------------- EDIT layer on track 5: PHYS and GRAIN dimmed
def edit_t5(s, said=False):
    text, ink, dim = s.c["text"], s.c["ink"], s.c["dim"]
    surf = s.img.getpixel((8, 112))                      # (the cells' ground as the firmware draws it)
    cells = {k: tile(s.img, p) for k, p in (("FM6", (66, 90)), ("SMPL", (8, 114)), ("GRAN", (8, 138)),
                                              ("PHYS", (66, 138)))}
    remap(s.img, cells["FM6"], text, ink, surf, text)     # FM6 no longer the engine: unlit
    remap(s.img, cells["SMPL"], surf, text, text, ink)    # SAMPLE is: lit
    remap(s.img, cells["GRAN"], surf, text, surf, dim)    # T1-T4 only: dimmed
    remap(s.img, cells["PHYS"], surf, text, surf, dim)
    s.box(0, 22, 239, 74, fill=s.c["bg"])
    s.cards([("ENG", "SMPL", "", 0.3), ("No.", "1", "/5", 0.2), ("FAV", "OFF", "", 0), ("", "", "", 0)], hot=0, y0=28)
    gauges(s, s.trk[1], s.trk[4])
    s.box(6, 188, 234, 206, fill=text)
    s.text((14, 202), "01", "lab", "ink")
    s.text((52, 202), "PIANO", "lab", "ink")
    if said:
        s.box(100, 0, 239, 21, fill=s.c["bg"])
        s.text((235, 16), "PHYS: T1-T4 ONLY", "lab", "text", anchor="rs")


# ---------------------------------------------------------------- the splash: six blocks
def splash(s):
    s.box(32, 32, 208, 208, fill=hexc("#2E302E"))
    s.text((50, 60), "Skiff", "m", "text")
    s.text((50, 80), "v0.1", "m", "text")
    for c in range(6):
        x0 = 50 + 25 * c
        s.g.rectangle([x0, 108, x0 + 19, 127], fill=s.trk[c])
    s.text((50, 172), "on Felucca 1.1.5", "m", "text")
    s.text((50, 192), "Hügelton + community", "m", "text")


SCREENS = [("home", "BLOCKS_SKIFF_home", home, "HOME: today's lanes, four at a time; T5 selected shows T2-T5 (the bar at the right)"),
           ("song", None, song, "SEQ > SONG playing: today's rows, T2-T5 shown; T5 on its A, B next"),
           ("perform", None, perform, "PERFORM: T2-T5 and SCN; T2 muted, T3's mute staged"),
           ("mixer", "BLOCKS_SKIFF_mixer", mixer, "MIXER: today's strips, T2-T5 shown (the bar under them)"),
           ("mixer_large", "LARGE-BLOCKS_SKIFF_mixer", mixer_large, "LARGE MIXER: the same, scrolled"),
           ("glo", "BLOCKS_SKIFF_layer_glo_active", glo, "GLO held: the cards are the four shown (T2-T5); SOLO 1-6 on F G A B E G, MUTE 1-6 on the black keys"),
           ("fx", "BLOCKS_SKIFF_layer_lock_fx", fx, "FX held: the effects as now; MUTE 1-6, T5 and T6 on D# and F#"),
           ("edit_t5", "BLOCKS_SKIFF_layer_edit_active", edit_t5, "EDIT held on T5 (SAMPLE): GRAN and PHYS dimmed, T1-T4 only"),
           ("edit_t5_said", "BLOCKS_SKIFF_layer_edit_active", lambda s: edit_t5(s, True), "... a dimmed key pressed says why"),
           ("splash", None, splash, "Splash: six blocks; T5 pink, T6 lime")]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shots = []
    for name, base, fn, cap in SCREENS:
        s = kit(base)
        fn(s)
        s.key = "P6"
        s.save(name)
        shots.append((Image.open(OUT / "x2" / f"P6_{name}.png"), cap))
    cols, pad = 4, 24
    capf = mock.font("BarlowCondensed-Medium.ttf", 22)
    rows_n = (len(shots) + cols - 1) // cols
    sw, sh = W * 2, H * 2
    sheet = Image.new("RGB", (cols * (sw + pad) + pad, rows_n * (sh + 90) + pad), (24, 24, 24))
    g = ImageDraw.Draw(sheet)
    for i, (im, cap) in enumerate(shots):
        r, c = divmod(i, cols)
        x, y = pad + c * (sw + pad), pad + r * (sh + 90)
        sheet.paste(im, (x, y))
        words, line, ly = cap.split(), "", y + sh + 26
        for w in words:
            if g.textlength(line + " " + w, font=capf) > sw and line:
                g.text((x, ly), line, font=capf, fill=(220, 220, 220))
                line, ly = w, ly + 26
            else:
                line = (line + " " + w).strip()
        g.text((x, ly), line, font=capf, fill=(220, 220, 220))
    sheet.save(HERE / "mockups" / "p6_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/p6_sheet.png")
