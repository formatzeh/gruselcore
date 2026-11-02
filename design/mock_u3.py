#!/usr/bin/env python3
"""U3 mockups (the UX review's structure batch), direction B as built:
  N1  six tracks on the track screens: A, all six as rows (the selected one at today's size, the others compact);
      B, today's four and a six-track strip in the header
  N2  the SEQ family reordered by task (a page map)
  R5  AUTOMATION and AUTO LIST as one page: the list, its first row the page's own (PLAY, CLEAR)
  R6  LANES and LANES 2 as one page: eight faders
  N4  the bus effects on GLO: DELAY, then REVERB with CHORUS (A, one page, TYPE on PRESETS) or two pages (B)
  A2  the project in the header: its letter, a dot while there are unsaved changes
Screens start from the firmware's renders (tests/ui_render.c, SKIFF; P6_RENDERS) where they keep what they have.
Writes out/U3_<screen>.png (1x, x2, x3) and mockups/u3_sheet.png.
  P6_RENDERS=../build/ui_new/ppm python3 mock_u3.py
"""
from PIL import Image, ImageDraw
import mock
import mock_p6 as p6
from mock import OUT, W, H, mix, HERE, hexc

TRK = p6.TRK6
TRACKS = [("ACID", "ANALOG"), ("PAD", "FM6"), ("PULSE LD", "LOFI"), ("DRUM KIT", "DRUM"), ("PIANO", "SAMPLE"),
          ("KIT X", "DRUM-X")]
STEPS = ["1010001010100010", "1000100010001000", "0010010000100100", "1011101110111011", "1000000010000000",
         "1001001010010010"]
PLAYHEAD = 9
MUTED = [False, False, True, False, False, False]


def kit(base=None):
    return p6.kit(base)


def cards(s, items, hot=None, k=0):
    """K1..K4 as the firmware draws them (CARD_X 3 + 59c, 57 x 44 at y 28): label S, value V (M when long), unit,
    the gauge in the track's colour; an empty label: an empty card"""
    for c, (lab, val, unit, g) in enumerate(items):
        x0, y0 = 3 + 59 * c, 28
        on = c == hot
        s.box(x0, y0, x0 + 56, y0 + 44, fill=s.c["text"] if on else s.c["surf"])
        if not lab:
            continue
        ink = s.c["ink"] if on else s.c["text"]
        s.text((x0 + 4, y0 + 13), lab, "lab", s.c["ink"] if on else s.c["mid"])
        f = "val" if s.tw(val, "val") + (s.tw(unit, "lab") + 4 if unit else 0) <= 52 else "m"
        s.text((x0 + 4, y0 + 38), val, f, ink)
        if unit:
            s.text((x0 + 54, y0 + 38), unit, "lab", s.c["ink"] if on else s.c["mid"], anchor="rs")
        if g:
            s.g.rectangle([x0, y0 + 42, x0 + round(56 * g), y0 + 44], fill=s.c["ink"] if on else s.trk[k])


def foot(s, left, right):
    s.box(0, 218, 239, 239, fill=s.c["bg"])
    s.text((5, 234), left, "lab", "mid")
    s.text((235, 234), right, "lab", "mid", anchor="rs")


def title(s, t):
    s.box(100, 0, 239, 21, fill=s.c["bg"])
    s.text((235, 16), t, "lab", "mid", anchor="rs")


def panel(s, y0=74, y1=216):
    s.box(0, y0, 239, y1, fill=s.c["bg"])


def cells(s, y, h, k, band, x0=100):
    col = s.trk[k]
    for j, on in enumerate(STEPS[k]):
        cx = x0 + j * 8 + (j // 4) * 2
        if band:
            fill = s.c["ink"] if on == "1" else mix(col, s.c["ink"], 0.55)
        else:
            fill = (s.c["dim"] if MUTED[k] else col) if on == "1" else s.c["line"]
        s.g.rectangle([cx, y, cx + 5, y + h - 1], fill=fill)
    px = x0 + PLAYHEAD * 8 + (PLAYHEAD // 4) * 2 - 2
    s.g.rectangle([px, y - 2, px, y + h + 1], fill=s.c["ink"] if band else s.c["text"])


# ---------------------------------------------------------------- N1 A: all six as rows
def home_six(s, sel=2):
    p6.gauges(s, s.trk[0], s.trk[sel])
    panel(s)
    y = 76
    for k in range(6):
        col = s.trk[k]
        if k == sel:                                     # today's lane: 31 px, the band
            s.box(0, y, 239, y + 30, fill=col)
            s.text((9, y + 24), str(k + 1), "val", "ink")
            s.text((28, y + 14), TRACKS[k][0], "m", "ink")
            s.text((28, y + 27), TRACKS[k][1], "lab", "ink")
            cells(s, y + 8, 16, k, True)
            y += 34
        else:                                            # compact: 18 px, the number and name in a line
            s.box(0, y, 239, y + 17, fill=s.c["surf"])
            s.text((9, y + 15), str(k + 1), "m", s.c["dim"] if MUTED[k] else col)
            s.text((28, y + 14), TRACKS[k][0], "lab", "mid" if MUTED[k] else "text")
            if MUTED[k]:
                s.text((92, y + 14), "M", "lab", "mid", anchor="rs")
            cells(s, y + 3, 12, k, False)
            y += 21


def perform_six(s, sel=4):
    panel(s, 74, 214)
    kept = [[0, 2, 15], [0, 1, 2], [0, 1], [0, 1, 2, 3], [0, 1], [0, 1, 2, 3]]
    cur, nxt = [2, 1, 0, 3, 0, 2], [5, None, None, None, 1, None]
    muted, arm = [False, True, False, False, False, False], [False, False, True, False, False, True]
    for r in range(7):
        y = 78 + 19 * r                                  # 17 px rows, 19 apart: y 78 .. 210
        ty = y + 2
        if r == 6:
            s.text((6, y + 13), "SCN", "lab", "mid")
            for p in range(16):
                x = 28 + 13 * p
                if p in (0, 4):
                    s.box(x, ty, x + 11, ty + 13, outline=s.c["dim"])
                    s.text((x + 6, ty + 11), str(p + 1), "lab", "mid", anchor="ms")
                else:
                    s.g.rectangle([x + 5, y + 8, x + 6, y + 9], fill=s.c["dim"])
            break
        col, band = s.trk[r], r == sel
        if band:
            s.box(3, y, 236, y + 16, fill=col)
        s.text((6, y + 14), str(r + 1), "m", s.c["ink"] if band else col)
        for p in range(16):
            x = 17 + 13 * p
            if p == nxt[r]:
                s.box(x, ty, x + 11, ty + 13, outline=s.c["ink"] if band else col)
                s.text((x + 6, ty + 11), p6.LET[p], "lab", s.c["ink"] if band else col, anchor="ms")
            elif p == cur[r]:
                s.box(x, ty, x + 11, ty + 13, fill=s.c["ink"] if band else s.c["dim"] if muted[r] else col)
                s.text((x + 6, ty + 11), p6.LET[p], "lab", col if band else s.c["text"] if muted[r] else s.c["ink"],
                       anchor="ms")
            elif p in kept[r]:
                s.text((x + 6, ty + 11), p6.LET[p], "lab", s.c["ink"] if band else s.c["mid"], anchor="ms")
            else:
                s.g.rectangle([x + 5, y + 8, x + 6, y + 9], fill=mix(col, s.c["ink"], 0.55) if band else s.c["dim"])
        if muted[r] or arm[r]:
            x = 17 + 13 * 16
            if arm[r]:
                s.box(x, ty, x + 11, ty + 13, outline=s.c["ink"] if band else s.c["rec"])
            s.text((x + 6, ty + 11), "M", "lab", s.c["ink"] if band else s.c["rec"] if muted[r] else s.c["mid"],
                   anchor="ms")


def song_six(s, sel=4, cursor=1):
    panel(s, 74, 214)
    for i in range(6):
        lst, y = p6.LISTS[i], 78 + 22 * i                 # 20 px bands, 22 apart: y 78 .. 208
        col, band = s.trk[i], i == sel
        if band:
            s.box(0, y, 239, y + 19, fill=col)
        s.text((5, y + 16), str(i + 1), "m", s.c["ink"] if band else col)
        for p, e in enumerate(lst):
            x0 = 22 + (p * 134 + 5) // 10
            x1, ty = x0 + 12, y + 2
            if e is None:
                s.g.rectangle([x0 + 5, ty + 7, x0 + 6, ty + 8], fill=mix(col, s.c["ink"], 0.55) if band else s.c["dim"])
                if band and p == cursor:
                    s.box(x0, ty, x1, ty + 15, outline=s.c["text"])
                continue
            pid, reps = e
            if band and p == cursor:
                fill, ink = s.c["text"], s.c["ink"]
            elif p == p6.CUR[i]:
                fill, ink = (s.c["ink"], col) if band else (col, s.c["ink"])
            elif band:
                fill, ink = mix(col, s.c["ink"], 0.35), s.c["ink"]
            else:
                fill, ink = s.c["surf"], s.c["mid"]
            s.box(x0, ty, x1, ty + 15, fill=fill)
            s.text(((x0 + x1) / 2 + 0.5, ty + 12), f"{pid:02d}", "lab", ink, anchor="ms")
            if p == p6.NXT[i]:
                s.box(x0 - 1, ty - 1, x1 + 1, ty + 16, outline=s.c["ink"] if band else col)
    s.box(150, 218, 239, 239, fill=s.c["bg"])
    s.text((235, 234), "SONG 7/7", "lab", "mid", anchor="rs")


MIX = dict(level=[-6, -14, -24, -1, -6, -9], pan=[-31, 37, 0, -6, -31, 20], rec=[False, True, False, True, False, False],
           mute=[False, False, True, False, False, False])


def mixer_six(s, sel=4):
    panel(s, 74, 216)
    for c in range(6):                                   # 36 px strips at the layer maps' columns (4 + 39c)
        x0, y0, y1 = 4 + 39 * c, 78, 212
        col, band, muted = s.trk[c], c == sel, MIX["mute"][c]
        ink = s.c["ink"] if band else None
        s.box(x0, y0, x0 + 35, y1, fill=col if band else s.c["surf"])
        s.text((x0 + 4, y0 + 22), str(c + 1), "val", ink or (s.c["dim"] if muted else col))
        if MIX["rec"][c]:
            s.g.ellipse([x0 + 25, y0 + 9, x0 + 31, y0 + 15], fill=ink or s.c["rec"])
        if muted:
            s.text((x0 + 32, y0 + 17), "M", "lab", ink or s.c["mid"], anchor="rs")
        name = TRACKS[c][0].split()[0]
        s.text((x0 + 4, y0 + 38), name, "lab", ink or (s.c["mid"] if muted else s.c["text"]))
        fx0, fy0, fy1 = x0 + 14, y0 + 46, y0 + 102       # the level: a fader, 0 dB at the top, -40 at the foot
        s.g.rectangle([fx0, fy0, fx0 + 7, fy1], fill=mix(col, s.c["ink"], 0.6) if band else s.c["line"])
        lv = fy1 - round((fy1 - fy0) * (40 + MIX["level"][c]) / 40)
        s.g.rectangle([fx0, lv, fx0 + 7, fy1], fill=ink or (s.c["dim"] if muted else col))
        s.g.rectangle([fx0 - 3, lv - 1, fx0 + 10, lv], fill=ink or s.c["text"])
        s.text((x0 + 18, y0 + 120), str(MIX["level"][c]), "m", ink or s.c["text"], anchor="ms")
        p = MIX["pan"][c]
        pan = "C" if not p else f"{'L' if p < 0 else 'R'}{abs(p)}"
        s.text((x0 + 18, y0 + 132), pan, "lab", ink or s.c["mid"], anchor="ms")


# ---------------------------------------------------------------- N1 B: today's four, a six-track strip in the header
def strip(s, x=104, lit=(0, 3, 4), muted=(2,)):
    for k in range(6):
        x0 = x + 7 * k
        if k in muted:
            s.box(x0, 6, x0 + 4, 15, outline=s.c["dim"])
        elif k in lit:
            s.g.rectangle([x0, 6, x0 + 4, 15], fill=s.trk[k])
        else:
            s.g.rectangle([x0, 6, x0 + 4, 15], fill=mix(s.trk[k], s.c["bg"], 0.6))


def home_strip(s):
    strip(s)


def perform_strip(s):
    strip(s)


# ---------------------------------------------------------------- N2: the SEQ family's pages
def seq_map(s):
    s.box(0, 0, 239, 239, fill=s.c["bg"])
    s.text((8, 18), "SEQ PAGES", "m", "text")
    cols = [("TODAY", ["STEP", "ROLL", "PATTERN", "PLAY", "SONG", "CHANCE", "AUTOMATION", "AUTO LIST"], None),
            ("SYNTH", ["STEP", "ROLL", "CHANCE", "PLAY", "PATTERN", "AUTOMATION", "SONG"], None),
            ("DRUM", ["STEP", "CHANCE", "PLAY", "PATTERN", "AUTOMATION", "SONG"], None)]
    for c, (head, pages, _) in enumerate(cols):
        x = 8 + 78 * c
        s.text((x, 42), head, "lab", "mid")
        for i, p in enumerate(pages):
            y = 50 + 21 * i
            new = c > 0 and p in ("AUTOMATION",)
            s.box(x, y, x + 72, y + 17, fill=s.c["text"] if (c > 0 and p == "SONG") else s.c["surf"])
            s.text((x + 5, y + 13), f"{i + 1} {p}", "lab", "ink" if (c > 0 and p == "SONG") else "text")
            if new:
                s.g.rectangle([x + 68, y + 2, x + 70, y + 15], fill=s.trk[1])
    s.text((8, 234), "AUTOMATION: THE LIST (R5)", "lab", "mid")


# ---------------------------------------------------------------- R5: AUTOMATION = the list, its top row the page's
REC5 = [("AUTO", "01", "LFO RATE", "1.99Hz"), ("LOCK", "03", "ENV FLT", "-46%"), ("LOCK", "03", "REV", "79%"),
        ("LOCK", "07", "ENV ATK", "683ms"), ("LOCK", "07", "CUT", "81Hz"), ("AUTO", "09", "PAN", "-62%"),
        ("LOCK", "12", "LFO FLT", "+78%")]


def automation(s, top=False):
    title(s, "AUTOMATION")
    if top:
        cards(s, [("ROW", "ALL", "", 0.0), ("PLAY", "ON", "", 1.0), ("", "", "", 0), ("CLEAR", "—", "", 0)], hot=1)
    s.box(0, 74, 239, 216, fill=s.c["bg"])
    s.box(3, 76, 236, 214, fill=s.c["surf"])
    y = 80
    s.box(6, y, 233, y + 15, fill=s.c["text"] if top else s.c["surf"], outline=None if top else s.c["line"])
    ink = "ink" if top else "text"
    s.g.polygon([(12, y + 4), (12, y + 12), (18, y + 8)], fill=s.c[ink])
    s.text((24, y + 12), "PLAY ON", "lab", ink)
    s.text((229, y + 12), "7 RECORDS", "lab", "ink" if top else "mid", anchor="rs")
    for i, (kind, st, par, val) in enumerate(REC5):
        y = 99 + 16 * i
        on = (not top) and i == 3
        if on:
            s.box(6, y - 1, 233, y + 14, fill=s.c["text"])
        c = "ink" if on else "text"
        s.text((14, y + 11), kind, "lab", "ink" if on else "mid")
        s.text((50, y + 11), st, "lab", c)
        s.text((78, y + 11), par, "lab", c)
        s.text((229, y + 11), val, "lab", c, anchor="rs")
    foot(s, "OCT+: CLEAR   OCT-: HOME" if top else "OCT+: AUTO   OCT-: HOME", "AUTOMATION 5/6")


# ---------------------------------------------------------------- R6: one LANES page, eight faders
def lanes(s, sel=1):
    title(s, "LANES")
    s.box(0, 22, 239, 216, fill=s.c["bg"])
    names = ["BD", "SD", "CP", "CH", "OH", "TM", "RS", "CB"]
    lv = [100, 80, 64, 72, 55, 70, 40, 50]
    cards(s, [("LANE", names[sel], "", (sel + 0.5) / 8), ("LEVEL", str(lv[sel]), "%", lv[sel] / 100), ("", "", "", 0),
              ("", "", "", 0)], hot=1, k=3)
    s.box(3, 76, 236, 198, fill=s.c["surf"])
    for i in range(8):
        x = 14 + 28 * i
        on = i == sel
        y0, y1 = 86, 172
        s.g.rectangle([x + 6, y0, x + 9, y1], fill=s.c["line"])
        top = y1 - round((y1 - y0) * lv[i] / 100)
        s.g.rectangle([x + 6, top, x + 9, y1], fill=s.c["text"] if on else s.trk[3])
        s.g.rectangle([x + 1, top - 2, x + 14, top + 1], fill=s.c["text"] if on else s.c["mid"])
        if on:
            s.box(x - 2, 176, x + 17, 192, fill=s.c["text"])
        s.text((x + 8, 189), names[i], "lab", "ink" if on else "mid", anchor="ms")
    foot(s, "", "EDIT 3/3")
    p6.footer_track(s, 3, "DRUM", "DRUM KIT")


# ---------------------------------------------------------------- N4: the bus effects on GLO
def scope(s, src, box, to):
    """the firmware's scope (the graph today; V1 gives these pages their own graphs, U5) cropped into box"""
    im = src.crop((6, 80, 234, 194)).resize((to[2] - to[0], to[3] - to[1]))
    s.img.paste(im, (to[0], to[1]))


def delay(s):
    title(s, "DELAY")
    s.box(150, 218, 239, 239, fill=s.c["bg"])
    s.text((235, 234), "GLO 2/4", "lab", "mid", anchor="rs")


def reverb_one(s):
    src = s.img.copy()
    s.box(0, 22, 239, 216, fill=s.c["bg"])
    title(s, "REVERB")
    cards(s, [("SIZE", "71", "%", 0.71), ("DAMP", "47", "%", 0.47), ("RATE", "30", "%", 0.3), ("DEPTH", "55", "%", 0.55)])
    s.box(3, 76, 118, 198, fill=s.c["surf"])
    s.box(121, 76, 236, 198, fill=s.c["surf"])
    scope(s, src, None, (6, 96, 115, 192))
    scope(s, src, None, (124, 96, 233, 192))
    s.text((8, 90), "REVERB", "lab", "mid")
    s.box(70, 79, 115, 93, fill=s.c["text"])
    s.text((92, 90), "SPRING", "lab", "ink", anchor="ms")
    s.text((126, 90), "CHORUS", "lab", "mid")
    foot(s, "PRESETS: TYPE", "GLO 3/4")


def reverb_two(s):
    s.box(150, 218, 239, 239, fill=s.c["bg"])
    s.text((235, 234), "GLO 3/5", "lab", "mid", anchor="rs")


def chorus_two(s):
    src = s.img.copy()
    s.box(0, 22, 239, 216, fill=s.c["bg"])
    title(s, "CHORUS")
    cards(s, [("RATE", "30", "%", 0.3), ("DEPTH", "55", "%", 0.55), ("", "", "", 0), ("", "", "", 0)])
    s.box(3, 76, 236, 198, fill=s.c["surf"])
    scope(s, src, None, (6, 80, 233, 194))
    s.box(150, 218, 239, 239, fill=s.c["bg"])
    s.text((235, 234), "GLO 4/5", "lab", "mid", anchor="rs")


# ---------------------------------------------------------------- A2: the project in the header
def proj_mark(s, title, dirty, letter="B"):
    tw = s.tw(title, "lab")
    x1 = 235 - tw - 6
    s.box(x1 - 13, 4, x1, 18, outline=s.c["mid"])
    s.text((x1 - 6, 16), letter, "lab", "text", anchor="ms")
    if dirty:
        s.g.rectangle([x1 - 2, 2, x1 + 2, 6], fill=s.c["text"])


def home_proj(s):
    title(s, "SKETCH 01")
    proj_mark(s, "SKETCH 01", False)


def env_proj(s):
    title(s, "ENV")
    proj_mark(s, "ENV", True)


SCREENS = [
    ("n1a_home", "SKIFF_home", home_six, "N1 A · HOME: all six; the selected track at today's size, the others 18 px rows (name, pattern)"),
    ("n1a_perform", "SKIFF_six_perform", perform_six, "N1 A · PERFORM: six rows and SCN, 17 px rows (today 22)"),
    ("n1a_song", "SKIFF_six_song", song_six, "N1 A · SONG: six rows, 20 px (today 24)"),
    ("n1a_mixer", "SKIFF_six_mixer", mixer_six, "N1 A · MIXER: six 36 px strips: level fader and pan; REV only on the cards"),
    ("n1b_home", "SKIFF_six_home", home_strip, "N1 B · today's four (T2-T5), and a six-track strip after the BPM on every screen: lit = playing, outline = muted"),
    ("n1b_perform", "SKIFF_six_perform", perform_strip, "N1 B · PERFORM: today's four, the same strip"),
    ("n2_map", None, seq_map, "N2 · SEQ by task: STEP, ROLL (synth only), CHANCE, PLAY, PATTERN, AUTOMATION, SONG last. 7 pages on a synth, 6 on a drum track"),
    ("r5_list", "SKIFF_auto_list", automation, "R5 · AUTOMATION is the list: KNOB 1 its rows (as AUTO LIST)"),
    ("r5_top", "SKIFF_auto_list", lambda s: automation(s, True), "R5 · ... its top row is the page's own: PLAY on KNOB 2, CLEAR on KNOB 4"),
    ("r6_lanes", "SKIFF_drum", lanes, "R6 · one LANES page: KNOB 1 the lane, KNOB 2 its level, all eight as faders (DRUM-X: hidden, its sheet has LEVL)"),
    ("n4_delay", "SKIFF_dly", delay, "N4 · GLO: MIXER, DELAY, REVERB, GLOBAL (SYSTEM gone, R2); FX keeps FX, SLICER, DUCK"),
    ("n4a_reverb", "SKIFF_reverb_spring", reverb_one, "N4 A · REVERB and CHORUS on one page; TYPE on the PRESETS knob, shown in the graph"),
    ("n4b_reverb", "SKIFF_reverb_spring", reverb_two, "N4 B · or two pages: REVERB as today (TYPE SIZE DAMP) ..."),
    ("n4b_chorus", "SKIFF_reverb_spring", chorus_two, "N4 B · ... and CHORUS: RATE, DEPTH (were CRT, CDP)"),
    ("a2_home", "SKIFF_home", home_proj, "A2 · the project's letter before the title (HOME: its name), saved"),
    ("a2_env", "SKIFF_env", env_proj, "A2 · a dot on it while there are unsaved changes"),
]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shots = []
    for name, base, fn, cap in SCREENS:
        s = kit(base)
        fn(s)
        s.key = "U3"
        s.save(name)
        shots.append((Image.open(OUT / "x2" / f"U3_{name}.png"), cap))
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
    sheet.save(HERE / "mockups" / "u3_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/u3_sheet.png")
