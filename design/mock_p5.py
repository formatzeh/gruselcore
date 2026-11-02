#!/usr/bin/env python3
"""Phase 5 mockups (patterns at the core), direction B as built: the SONG page, the pattern pool, the dialogs and the
step page's pattern mark. Uses mock.py's drawing kit. Writes out/P5_<screen>.png (1x, x2, x3) and mockups/p5_sheet.png.
  python3 mock_p5.py
"""
from PIL import Image, ImageDraw
import mock
from mock import S, OUT, W, H, mix, HERE

if not (HERE / "fonts").is_dir():            # (fetch_fonts.sh not run: the firmware's own Barlow, Medium for SemiBold)
    mock.F = HERE.parent / "assets" / "fonts"
    mock.DIRS["B"]["lab"] = ("BarlowCondensed-Medium.ttf", 13)


def font(name, size):
    return mock.font(name if (mock.F / name).exists() else "BarlowCondensed-Medium.ttf", size)

LET = "ABCDEFGHIJKLMNOP"
# each track's list: (pattern id or None, reps); the entry each track is on; the one staged next (playing)
LISTS = [[(1, 2), (2, 1), (1, 1), (3, 2)] + [(None, 1)] * 12,
         [(5, 1), (5, 1), (6, 2), (7, 1), (6, 1)] + [(None, 1)] * 11,
         [(9, 4), (10, 4)] + [(None, 1)] * 14,
         [(13, 1), (None, 1), (14, 1), (15, 1), (16, 1), (14, 1)] + [(None, 1)] * 10]
CUR = [1, 2, 0, 3]
NEXT = [2, 3, 1, 4]
SEL, CURSOR = 1, 2                       # track 2 selected, entry C under the cursor


def header(s, title, playing=False, right_extra=None):
    """the B header as built: transport mark, bar.beat, BPM; the title at the right (battery only when low)"""
    if playing:
        s.g.polygon([(5, 5), (5, 15), (13, 10)], fill=s.c["text"])
    else:
        s.g.rectangle([5, 6, 12, 13], fill=s.c["text"])
    s.text((19, 16), "2.3" if playing else "1.1", "num", "text")
    s.text((45, 16), "124", "num", "text")
    s.text((45 + s.tw("124", "num") + 3, 16), "BPM", "lab", "mid")
    x = 235
    s.text((x, 16), title, "lab", "mid", anchor="rs")
    if right_extra:
        x -= s.tw(title, "lab") + 6
        s.text((x, 16), right_extra, "lab", s.trk[SEL], anchor="rs")


def footer(s, left, right):
    s.text((5, 234), left, "lab", "mid")
    s.text((235, 234), right, "lab", "mid", anchor="rs")


def rows(s, playing):
    """the four lists, drawn as the PERFORM map: the track's number, then 16 entries; an entry shows its pattern"""
    for i, lst in enumerate(LISTS):
        y = 82 + i * 27
        col = s.trk[i]
        sel = i == SEL
        if sel:
            s.box(0, y - 2, 239, y + 21, fill=col)
        s.text((5, y + 16), str(i + 1), "name", s.c["ink"] if sel else col)
        for p, (pid, reps) in enumerate(lst):
            x = 22 + p * 13.6
            x0, x1 = round(x), round(x + 12)
            here = p == CUR[i]
            nxt = playing and p == NEXT[i]
            cursor = sel and p == CURSOR
            ink = s.c["ink"]
            if pid is None:
                dot = mix(s.c["ink"], col, 0.45) if sel else s.c["dim"]
                s.g.rectangle([x0 + 5, y + 8, x0 + 6, y + 9], fill=dot)
                if cursor:
                    s.box(x0, y, x1, y + 17, outline=s.c["text"], w=1)
                continue
            if cursor:
                fill, tcol = s.c["text"], ink
            elif here:
                fill, tcol = (s.c["ink"], col) if sel else (col, ink)
            elif sel:
                fill, tcol = mix(col, s.c["ink"], 0.35), ink
            else:
                fill, tcol = s.c["surf"], s.c["mid"]
            s.box(x0, y, x1, y + 17, fill=fill)
            s.text(((x0 + x1) / 2 + 0.5, y + 13), f"{pid:02d}", "lab", tcol, anchor="ms")
            if nxt:                                   # staged: comes in at this track's loop end
                s.box(x0 - 1, y - 1, x1 + 1, y + 18, outline=s.c["ink"] if sel else col, w=1)
            for r in range(min(reps, 4) - 1):          # repeats: a tick each under the tile
                yy = y + 19
                s.g.rectangle([x0 + 1 + r * 3, yy, x0 + 2 + r * 3, yy], fill=s.c["ink"] if sel else col)


def song(s, playing=False):
    header(s, "SONG", playing, "SONG ON" if playing else None)
    s.cards([("ENTRY", "C", "", (CURSOR + 0.5) / 16), ("PATTERN", "06", "", 0.3), ("REPS", "2", "x", 2 / 16),
             ("SONG", "ON", "", 1.0)], hot=0)
    rows(s, playing)
    footer(s, "OCT+: PLAY  EDIT: CLEAR", "SONG 5/8")


def song_pick(s):
    """K2 turned: a pattern picked for the entry, applied with OCT+ (COPY: a copy of the entry's pattern, new number)"""
    header(s, "SONG")
    s.cards([("ENTRY", "C", "", (CURSOR + 0.5) / 16), ("PATTERN", "COPY", "", 1.0), ("REPS", "2", "x", 2 / 16),
             ("SONG", "ON", "", 1.0)], hot=1)
    rows(s, False)
    footer(s, "OCT+: COPY 06 TO 17", "SONG 5/8")


def pool(s):
    """SAVE > PATTERNS: the 64 shared patterns; a used one shows its LEN, how many entries use it as a bar"""
    header(s, "PATTERNS")
    s.cards([("PATTERN", "23", "", 23 / 64), ("LEN", "16", "", 0.25), ("USED", "0", "x", 0.0), ("CLEAR", "OCT+", "", 0)],
            hot=3)
    used = {1: 3, 2: 1, 3: 1, 5: 2, 6: 2, 7: 1, 9: 1, 10: 1, 13: 1, 14: 2, 15: 1, 16: 1, 17: 0, 21: 4, 22: 4, 23: 0,
            24: 1, 31: 1, 33: 0}
    for n in range(64):
        r, c = divmod(n, 8)
        x0 = 1 + c * 30
        y0 = 78 + r * 17
        pid = n + 1
        if pid in used:
            pick = pid == 23
            fill = s.c["text"] if pick else s.c["surf"]
            s.box(x0, y0, x0 + 27, y0 + 14, fill=fill)
            s.text((x0 + 14, y0 + 12), f"{pid:02d}", "lab", s.c["ink"] if pick else s.c["text"] if used[pid] else
                   s.c["mid"], anchor="ms")
            if not used[pid]:                       # nothing uses it: free to clear
                s.box(x0, y0, x0 + 27, y0 + 14, outline=s.c["dim"] if not pick else s.c["text"])
        else:
            s.g.rectangle([x0 + 13, y0 + 7, x0 + 14, y0 + 8], fill=s.c["dim"])
    footer(s, "OCT+: CLEAR  OCT-: BACK", "PATTERNS 3/5")


def dim_under(s):
    ov = Image.new("RGB", (W, H), s.c["bg"])
    s.img = Image.blend(s.img, ov, 0.7)
    s.g = ImageDraw.Draw(s.img)
    s.g.fontmode = "L"


def dialog(s, title, l1, l2, verb):
    x0, y0, x1, y1 = 16, 56, 223, 196
    s.box(x0, y0, x1, y1, fill=s.c["surf"])
    s.text((120, y0 + 30), title, "name", "text", anchor="ms")
    s.text((120, y0 + 50), l1, "lab", "mid", anchor="ms")
    s.text((120, y0 + 64), l2, "lab", "mid", anchor="ms")
    bw, by = 88, y0 + 80
    s.box(x0 + 12, by, x0 + 12 + bw, by + 28, fill=s.c["text"])
    s.text((x0 + 12 + bw / 2, by + 19), "CANCEL", "name", "ink", anchor="ms")
    s.box(x1 - 12 - bw, by, x1 - 12, by + 28, outline=s.c["rec"], w=1)
    s.text((x1 - 12 - bw / 2, by + 19), verb, "name", "rec", anchor="ms")
    s.text((x0 + 12 + bw / 2, by + 42), "OCT-", "lab", "mid", anchor="ms")
    s.text((x1 - 12 - bw / 2, by + 42), "OCT+", "lab", "mid", anchor="ms")


def confirm_entry(s):
    song(s)
    dim_under(s)
    dialog(s, "CLEAR ENTRY C?", "pattern 06 stays:", "entries D and E use it", "CLEAR")


def confirm_entry_last(s):
    song(s)
    dim_under(s)
    dialog(s, "CLEAR ENTRY C?", "erases pattern 06 too", "can't be undone", "CLEAR")


def confirm_pool(s):
    pool(s)
    dim_under(s)
    dialog(s, "CLEAR PATTERN 23?", "no entry uses it", "can't be undone", "CLEAR")


def step_mark(s):
    """SEQ > STEP: the header names the pattern being edited, with how many entries share it"""
    header(s, "STEP", False, "C · 06 · 2x")
    s.cards([("STEP", "5", "/16", 0.3), ("NOTE", "C2", "", 0.4), ("VELO", "96", "", 0.75), ("CHNC", "75", "%", 0.75)],
            hot=1)
    notes = ["C2", "", "C2", "", "D#2", "G1", "", "", "C2", "", "A#1", "", "", "C3", "", "G2"]
    cw, ch = 28, 32
    for j, n in enumerate(notes):
        r, c = divmod(j, 8)
        x = 4 + c * (cw + 1)
        y = 80 + r * (ch + 26)
        fill = s.trk[SEL] if n else s.c["surf"]
        if j == 4:
            fill = s.c["text"]
        s.g.rectangle([x, y, x + cw - 2, y + ch], fill=fill)
        s.text((x + cw / 2 - 1, y + ch - 5), n, "lab", "ink", anchor="ms")
        s.text((x + cw / 2 - 1, y + ch + 13), str(j + 1), "lab", "mid", anchor="ms")
    footer(s, "PRESETS: STEP", "STEP 1/8")


SCREENS = [("song", song, "SONG, stopped: K1 picks the entry (white); a filled tile is the entry each track is on"),
           ("song_playing", lambda s: song(s, True), "SONG playing, SONG ON: outlined = next in, at that track's loop end"),
           ("song_copy", song_pick, "K2 turned to COPY: OCT+ makes pattern 17, a copy of 06, for entry C"),
           ("confirm_entry", confirm_entry, "EDIT on an entry whose pattern other entries use"),
           ("confirm_entry_last", confirm_entry_last, "EDIT on the last entry using its pattern"),
           ("pool", pool, "SAVE > PATTERNS: all 64; outlined = no entry uses it (CLEAR works only on those)"),
           ("confirm_pool", confirm_pool, "CLEAR on an unused pattern"),
           ("step_mark", step_mark, "STEP: the header says which pattern you're editing and that 2 entries share it")]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shots = []
    for name, fn, cap in SCREENS:
        s = S("B")
        fn(s)
        s.key = "P5"
        s.save(name)
        shots.append((Image.open(OUT / "x2" / f"P5_{name}.png"), cap))
    # the review sheet: 2x screens, a caption under each
    cols, pad, capf = 4, 24, font("BarlowCondensed-SemiBold.ttf", 22)
    rows_n = (len(shots) + cols - 1) // cols
    sw, sh = W * 2, H * 2
    sheet = Image.new("RGB", (cols * (sw + pad) + pad, rows_n * (sh + 90) + pad), (24, 24, 24))
    g = ImageDraw.Draw(sheet)
    for i, (im, cap) in enumerate(shots):
        r, c = divmod(i, cols)
        x, y = pad + c * (sw + pad), pad + r * (sh + 90)
        sheet.paste(im, (x, y))
        words, line, ly = cap.split(), "", y + sh + 26
        for w in words:                                # wrap the caption to the screen's width
            if g.textlength(line + " " + w, font=capf) > sw and line:
                g.text((x, ly), line, font=capf, fill=(220, 220, 220))
                line, ly = w, ly + 26
            else:
                line = (line + " " + w).strip()
        g.text((x, ly), line, font=capf, fill=(220, 220, 220))
    sheet.save(HERE / "mockups" / "p5_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/p5_sheet.png")
