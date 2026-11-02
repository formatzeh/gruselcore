#!/usr/bin/env python3
"""Phase 8 mockups: editing a DRUM-X sound without looping through pages. Three directions, drawn in BLOCKS (the
firmware's faces: assets/fonts) on track 6 (lime), the kit's snare edited:
  1  PAGES BOTH WAYS  today's three SOUND pages; SELECT turns pages either way (DESIGN.md rule 3, never built), PRESETS
                      or a key picks the sound, a page strip in the footer says where you are
  2  SOUND SHEET      one page per sound: the panel lists all of it, A beside B; SELECT moves the four knobs down the
                      list (K1 K2 = a value's A and B), PRESETS or a key picks the sound
  3  KIT GRID         the whole kit at once: 8 sounds x 6 values; PRESETS picks the sound (column), SELECT the value
                      (row); K1 its A, K2 its B, K3 the sound's LEVEL, K4 the row's switch
Writes out/P8_<screen>.png (1x, x2, x3) and mockups/p8_sheet.png.
  python3 mock_p8.py
"""
from PIL import Image, ImageDraw
import mock
from mock import S, OUT, W, H, mix, HERE, hexc

mock.F = HERE.parent / "assets" / "fonts"
mock.DIRS["B"]["lab"] = ("BarlowCondensed-Medium.ttf", 13)
mock.DIRS["B"]["val"] = ("BarlowCondensed-Bold.ttf", 24)
TRK6 = ["#FF5A36", "#22C3B4", "#FFBF00", "#9580FF", "#FF6FAE", "#A3E635"]
mock.SEL = 5                                             # track 6 (cards' gauges in its colour)
LANES = ["BD", "SD", "CP", "CH", "OH", "TM", "RS", "CB"]
VALS = ["PTCH", "PMOD", "DCAY", "NOIS", "COLR"]
# the factory kit (drumx_voice.c DX_KIT_INIT): A and B {PITCH PMOD DECAY NOISE COLOR}, and each lane's mode
KIT = [((9, 70, 72, 4, 20), (14, 100, 88, 10, 60), "SIN", "LP", 1),
       ((40, 30, 52, 80, 90), (46, 18, 64, 104, 70), "FM", "BP", 0),
       ((60, 0, 46, 127, 84), (54, 0, 58, 127, 76), "SIN", "BP", 0),
       ((100, 0, 22, 96, 116), (108, 0, 14, 112, 122), "MTL", "HP", 0),
       ((100, 0, 62, 96, 112), (108, 0, 74, 112, 118), "MTL", "HP", 0),
       ((30, 40, 66, 10, 30), (36, 60, 76, 20, 50), "SIN", "LP", 1),
       ((63, 10, 14, 16, 46), (70, 24, 20, 30, 60), "BEL", "HP", 1),
       ((69, 0, 72, 0, 40), (74, 0, 84, 12, 56), "MTL", "BP", 0)]
LEVEL = [127, 120, 100, 90, 84, 110, 96, 80]
LANE, MRPH = 1, 40                                       # the snare; MRPH (EDIT 1) at 40


def kit():
    s = S("B")
    s.trk = [hexc(c) for c in TRK6]
    s.f["m"] = mock.font("BarlowCondensed-Bold.ttf", 16)
    s.f["s"] = mock.font("BarlowCondensed-Medium.ttf", 11)
    return s


def header(s, title):
    s.g.polygon([(5, 5), (5, 15), (13, 10)], fill=s.c["text"])
    s.text((19, 16), "1.2", "num", "text")
    s.text((45, 16), "124", "num", "text")
    s.text((45 + s.tw("124", "num") + 3, 16), "BPM", "lab", "mid")
    s.text((235, 16), title, "lab", "mid", anchor="rs")


def footer(s, right):
    s.text((5, 236), "6", "val", s.trk[5])
    s.text((21, 234), "DRUM-X", "lab", "text")
    s.text((21 + s.tw("DRUM-X", "lab") + 7, 234), "DRUM KIT", "lab", "text")
    if right:
        s.text((235, 234), right, "lab", "mid", anchor="rs")


def panel(s):
    s.box(0, 76, 239, 214, fill=s.c["surf"])


def lane_tiles(s, y, h=18, x0=9, w=26, gap=2):
    raise_ = mix(s.c["surf"], s.c["text"], 0.12)
    for i, n in enumerate(LANES):
        x = x0 + i * (w + gap)
        on = i == LANE
        s.box(x, y, x + w - 1, y + h - 1, fill=s.trk[5] if on else raise_)
        s.text((x + w / 2, y + h - 4), n, "lab", s.c["ink"] if on else s.c["mid"], anchor="ms")


def heard(a, b):
    return a + (b - a) * MRPH // 127


def save(s, name):
    img = s.img
    img.save(OUT / f"P8_{name}.png")
    for z in (2, 3):
        (OUT / f"x{z}").mkdir(parents=True, exist_ok=True)
        img.resize((W * z, H * z), Image.NEAREST).save(OUT / f"x{z}" / f"P8_{name}.png")
    return img


# ------------------------------------------------ 1: pages both ways (today's pages, SELECT turns them)
def pages(s, page):
    a, b, wave, flt, snap = KIT[LANE]
    raise_ = mix(s.c["surf"], s.c["text"], 0.12)
    if page == 0:
        header(s, "SOUND")
        s.cards([("SIDE", "B", "", 1.0), ("PTCH", str(b[0]), "", b[0] / 127), ("PMOD", str(b[1]), "", b[1] / 127),
                 ("DCAY", str(b[2]), "", b[2] / 127)], hot=1, y0=28)
    panel(s)
    lane_tiles(s, 82)
    for i, v in enumerate(VALS):                        # today's panel: A over B, the side edited white
        y = 108 + i * 15
        s.text((10, y + 11), v, "lab", "mid")
        s.box(50, y + 2, 219, y + 5, fill=raise_)
        s.box(50, y + 8, 219, y + 11, fill=raise_)
        s.box(50, y + 2, 50 + a[i] * 170 // 127, y + 5, fill=s.trk[5])
        s.box(50, y + 8, 50 + b[i] * 170 // 127, y + 11, fill=s.c["text"])
        q = heard(a[i], b[i])
        s.box(50 + q * 169 // 127, y + 1, 50 + q * 169 // 127, y + 12, fill=s.c["text"])
    s.text((120, 207), f"{wave} {flt}{'+' if snap else ''}  PMOD DECAY", "lab", "mid", anchor="ms")
    # the family's pages: a strip in the footer, this one lit; SELECT steps either way
    names = ["E1", "E2", "LN", "LN2", "S1", "S2", "S3", "V", "V2"]
    x = 235 - len(names) * 7
    for i, n in enumerate(names):
        on = i == 4 + page
        s.box(x + i * 7, 226, x + i * 7 + 4, 233, fill=s.trk[5] if on else raise_)
    s.text((x - 6, 234), "SELECT", "s", "mid", anchor="rs")
    s.g.polygon([(x - 50, 229), (x - 46, 226), (x - 46, 232)], fill=s.c["mid"])
    footer(s, None)


# ------------------------------------------------ 2: the sound sheet (one page, the knobs move down it)
def sheet(s, window):
    a, b, wave, flt, snap = KIT[LANE]
    raise_ = mix(s.c["surf"], s.c["text"], 0.12)
    header(s, "SOUND  SD")
    if window == 0:
        s.cards([("PTCH A", str(a[0]), "", a[0] / 127), ("PTCH B", str(b[0]), "", b[0] / 127),
                 ("PMOD A", str(a[1]), "", a[1] / 127), ("PMOD B", str(b[1]), "", b[1] / 127)], hot=1, y0=28)
    else:
        s.cards([("WAVE", wave, "", 0.33), ("FILT", flt, "", 0.5), ("SNAP", "ON" if snap else "OFF", "", 1.0 if snap else 0),
                 ("PSHP", "DECAY", "", 0)], hot=0, y0=28)
    panel(s)
    lane_tiles(s, 80, h=16)
    s.text((77, 108), "A", "s", "mid", anchor="ms")
    s.text((173, 108), "B", "s", "mid", anchor="ms")
    rows = [(v, a[i], b[i]) for i, v in enumerate(VALS)]
    y0 = 110
    win = [0, 1] if window == 0 else [6]
    band = mix(s.c["surf"], s.trk[5], 0.22)
    for r in win:                                      # the four knobs' rows: a band, a marker
        y = y0 + r * 14
        s.box(3, y, 233, y + 13, fill=band)
        s.box(3, y, 4, y + 13, fill=s.trk[5])
    for i, (v, va, vb) in enumerate(rows):
        y = y0 + i * 14
        s.text((10, y + 11), v, "lab", "text" if i in win else "mid")
        for x0, val, col in ((46, va, s.trk[5]), (142, vb, s.c["text"])):
            s.box(x0, y + 5, x0 + 62, y + 8, fill=raise_)
            s.box(x0, y + 5, x0 + val * 62 // 127, y + 8, fill=col)
            s.text((x0 + 84, y + 10), str(val), "s", "mid", anchor="rs")
    y = y0 + 5 * 14                                      # LEVEL and DRV: one value each
    s.text((10, y + 11), "LEVL", "lab", "mid")
    s.box(46, y + 5, 108, y + 8, fill=raise_)
    s.box(46, y + 5, 46 + LEVEL[LANE] * 62 // 127, y + 8, fill=s.c["mid"])
    s.text((130, y + 10), "94%", "s", "mid", anchor="rs")
    s.text((142, y + 11), "DRV", "lab", "mid")
    s.text((172, y + 11), "OFF", "lab", "dim")
    y = y0 + 6 * 14                                      # the switches
    s.text((10, y + 11), "MODE", "lab", "text" if 6 in win else "mid")
    s.text((46, y + 11), f"{wave}   {flt}   SNAP {'ON' if snap else 'OFF'}   PMOD DECAY", "lab", "text" if 6 in win else "mid")
    s.box(236, 80, 237, 210, fill=raise_)               # where the knobs are on the sheet
    top = 80 + (win[0] * 130) // 7
    s.box(236, top, 237, top + 130 * len(win) // 7 + 4, fill=s.c["mid"])
    footer(s, "SELECT: ROWS")


# ------------------------------------------------ 3: the kit grid (every sound, every value)
def grid(s):
    raise_ = mix(s.c["surf"], s.c["text"], 0.12)
    header(s, "KIT")
    a, b, wave, flt, snap = KIT[LANE]
    s.cards([("DCAY A", str(a[2]), "", a[2] / 127), ("DCAY B", str(b[2]), "", b[2] / 127),
             ("LEVL", "94", "%", LEVEL[LANE] / 127), ("SNAP", "OFF", "", 0)], hot=1, y0=28)
    panel(s)
    rows = VALS + ["LEVL"]
    cx0, cw, ry0, rh = 42, 24, 98, 18
    for c, n in enumerate(LANES):                        # the sounds across
        x = cx0 + c * cw
        on = c == LANE
        if on:
            s.box(x, 80, x + cw - 3, 95, fill=s.trk[5])
        s.text((x + (cw - 2) / 2, 92), n, "lab", s.c["ink"] if on else s.c["mid"], anchor="ms")
    for r, v in enumerate(rows):
        y = ry0 + r * rh
        on_r = r == 2
        s.text((8, y + 13), v, "lab", "text" if on_r else "mid")
        for c in range(8):
            x = cx0 + c * cw
            ka, kb = KIT[c][0], KIT[c][1]
            s.box(x, y + 1, x + cw - 3, y + rh - 2, fill=raise_)
            if r < 5:
                va, vb = ka[r], kb[r]
                s.box(x + 2, y + 4, x + 2 + va * (cw - 7) // 127, y + 6, fill=s.trk[5])
                s.box(x + 2, y + 10, x + 2 + vb * (cw - 7) // 127, y + 12, fill=s.c["text"])
            else:
                s.box(x + 2, y + 6, x + 2 + LEVEL[c] * (cw - 7) // 127, y + 10, fill=s.c["mid"])
            if c == LANE and on_r:
                s.g.rectangle([x - 1, y, x + cw - 2, y + rh - 1], outline=s.c["text"], width=1)
    footer(s, "PRESETS  SELECT")


def main():
    shots = []
    for name, fn, arg in (("1_pages", pages, 0), ("2_sheet", sheet, 0), ("2_sheet_modes", sheet, 1), ("3_grid", grid, None)):
        s = kit()
        fn(s, arg) if arg is not None else fn(s)
        shots.append(save(s, name))
    gap, z = 16, 2
    out = Image.new("RGB", (len(shots) * (W * z + gap) + gap, H * z + 2 * gap), (24, 24, 24))
    for i, im in enumerate(shots):
        out.paste(im.resize((W * z, H * z), Image.NEAREST), (gap + i * (W * z + gap), gap))
    out.save(HERE / "mockups" / "p8_sheet.png")
    print("p8_sheet.png", out.size)


if __name__ == "__main__":
    main()
