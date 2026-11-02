#!/usr/bin/env python3
"""#21 mockups: a SAMPLE track's sounds (the zones of a user slot: one sample each, one key each for a kit), each with
its own LEVEL and its own REVERB and DELAY on top of the track's sends. One new EDIT page after EDIT 2, SAMPLES:
KNOB 1 the sample (or play its key), KNOB 2 its LEVEL, KNOB 3 its REVERB, KNOB 4 its DELAY. The panel, two ways:
  A  FADERS  every sample of the slot as a fader, as DRUM's LANES page draws its lanes (its theme motifs too); the
             picked one lit. A+: two thin bars beside each fader, its REVERB and DELAY
  B  WAVE    the picked sample's waveform, as EDIT 1 and 2 draw it, its number and key over it
Screens start from the firmware's renders (tests/ui_render.c, SKIFF; P6_RENDERS) where they keep what they have.
  P6_RENDERS=~/skiff-s21/build/ui_new/ppm python3 mock_s21.py   -> out/S21_*.png, mockups/s21_sheet.png
"""
from PIL import Image, ImageDraw
import mock
import mock_p6 as p6
import mock_u3 as u3
from mock import OUT, W, H, HERE

NOTES = "C C# D D# E F F# G G# A A# B".split()
KIT = [("C4", 100, 0, 0), ("C#4", 72, 0, 0), ("D4", 80, 25, 0), ("D#4", 64, 45, 20), ("E4", 55, 0, 0),
       ("F4", 60, 10, 0), ("F#4", 45, 0, 35), ("G4", 70, 30, 15)]
SEL = 3                                                  # the picked sample: D#4, a clap with its own reverb and delay


def base(s, title="SAMPLES"):
    u3.title(s, title)
    s.box(0, 22, 239, 216, fill=s.c["bg"])
    name, lv, rv, dl = KIT[SEL]
    u3.cards(s, [("SAMPLE", name, "", (SEL + 0.5) / len(KIT)), ("LEVEL", str(lv), "%", lv / 100),
                 ("REVERB", str(rv), "%", rv / 100), ("DELAY", str(dl), "%", dl / 100)], hot=2, k=4)
    u3.foot(s, "", "EDIT 3/3")
    p6.footer_track(s, 4, "SAMPLE", "USR1 KIT")


def faders(s, kit=KIT, sends=False):
    """A: the slot's samples as faders (LANES'); A+: each with its REVERB and DELAY beside it"""
    base(s)
    s.box(3, 76, 236, 198, fill=s.c["surf"])
    n, col = len(kit), s.trk[4]
    step = 232 / max(n, 8)
    for i, (name, lv, rv, dl) in enumerate(kit):
        x = round(4 + step * i + (step - 28) / 2) if n <= 8 else round(4 + step * i)
        on = i == SEL
        y0, y1 = 86, 172
        fx = x + (6 if n <= 8 else 4)
        s.g.rectangle([fx, y0, fx + 3, y1], fill=s.c["line"])
        top = y1 - round((y1 - y0) * lv / 100)
        s.g.rectangle([fx, top, fx + 3, y1], fill=s.c["text"] if on else col)
        cw = 14 if n <= 8 else 9
        s.g.rectangle([fx + 2 - cw // 2, top - 2, fx + 1 + cw // 2, top + 1], fill=s.c["text"] if on else s.c["mid"])
        if sends:                                        # REVERB, DELAY: two thin bars right of the fader
            for j, v in enumerate((rv, dl)):
                bx = fx + 9 + 4 * j
                s.g.rectangle([bx, y0 + 30, bx + 1, y1], fill=s.c["line"])
                if v:
                    s.g.rectangle([bx, y1 - round((y1 - y0 - 30) * v / 100), bx + 1, y1],
                                  fill=s.c["text"] if on else s.c["mid"])
        if n <= 8:
            if on:
                s.box(x - 2, 176, x + 25, 192, fill=s.c["text"])
            s.text((x + 12, 189), name, "lab", "ink" if on else "mid", anchor="ms")
        elif on:
            s.box(fx - 10, 176, fx + 13, 192, fill=s.c["text"])
            s.text((fx + 2, 189), name, "lab", "ink", anchor="ms")
    if sends:
        s.text((233, 210), "BARS: REVERB  DELAY", "lab", "mid", anchor="rs")


def faders_sends(s):
    faders(s, sends=True)


def faders_16(s):
    kit = KIT + [(f"{NOTES[(i + 8) % 12]}{4 + (i + 8) // 12}", 50 + (i * 7) % 50, 0, 0) for i in range(8)]
    faders(s, kit)


def wave(s):
    """B: the picked sample's waveform (EDIT 1's), its number and key over it"""
    src = s.img.copy()
    base(s)
    s.box(3, 76, 236, 198, fill=s.c["surf"])
    s.img.paste(src.crop((6, 84, 234, 190)), (6, 92))   # the firmware's waveform, a little lower
    s.g = ImageDraw.Draw(s.img)
    s.g.fontmode = "L"
    name = KIT[SEL][0]
    s.box(6, 80, 60, 96, fill=s.c["text"])
    s.text((33, 93), f"{SEL + 1}/{len(KIT)}  {name}", "lab", "ink", anchor="ms")
    s.text((233, 93), "D#4 .. D#4", "lab", "mid", anchor="rs")


SCREENS = [
    ("a_faders", "SKIFF_lanes", faders,
     "A · FADERS: the slot's samples as LANES' faders (8 here, the key under each); the picked one lit, its REVERB and DELAY on KNOB 3 and 4"),
    ("a_sends", "SKIFF_lanes", faders_sends,
     "A+ · the same, and each sample's REVERB and DELAY as two thin bars beside its fader"),
    ("a_16", "SKIFF_lanes", faders_16, "A · with 16 samples (a slot's most): thinner faders, the key under the picked one only"),
    ("b_wave", "SKIFF_edit_sample", wave,
     "B · WAVE: the picked sample's waveform, as EDIT 1 and 2 show it, its number and keys over it; the values on the cards"),
]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shots = []
    for name, b, fn, cap in SCREENS:
        s = u3.kit(b)
        fn(s)
        s.key = "S21"
        s.save(name)
        shots.append((Image.open(OUT / "x2" / f"S21_{name}.png"), cap))
    cols, pad = 4, 24
    capf = mock.font("BarlowCondensed-Medium.ttf", 22)
    rows_n = (len(shots) + cols - 1) // cols
    sw, sh = W * 2, H * 2
    sheet = Image.new("RGB", (cols * (sw + pad) + pad, rows_n * (sh + 120) + pad), (24, 24, 24))
    g = ImageDraw.Draw(sheet)
    for i, (im, cap) in enumerate(shots):
        r, c = divmod(i, cols)
        x, y = pad + c * (sw + pad), pad + r * (sh + 120)
        sheet.paste(im, (x, y))
        words, line, ly = cap.split(), "", y + sh + 26
        for w in words:
            if g.textlength(line + " " + w, font=capf) > sw and line:
                g.text((x, ly), line, font=capf, fill=(220, 220, 220))
                line, ly = w, ly + 26
            else:
                line = (line + " " + w).strip()
        g.text((x, ly), line, font=capf, fill=(220, 220, 220))
    sheet.save(HERE / "mockups" / "s21_sheet.png")
    print("wrote", len(shots), "screens to", OUT, "and mockups/s21_sheet.png")
