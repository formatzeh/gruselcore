#!/usr/bin/env python3
"""(#28) SEQ > SONG with a REST entry: two looks for the pick, from the firmware's own renders (tests/ui_render.c
song_rest, song_rest_pick; graph_song then had a switch, MOCK_REST_TILE 0 for A and 1 for B, rendered into
REST_RENDERS/A and /B):
  A  a REST is a dash, as the rests between patterns are today
  B  a REST is a tile like a pattern's, a dash in it (the rests between patterns stay a bare dash)
Both: KNOB 2 (PATTERN) picks --, REST, 01 .. 64, COPY, CLEAR; the card says REST; OCT+ SET REST; REPS its passes.
The user picked B (2026-10-20); the firmware draws only B since, so the sheet stays as it was shown.
Writes mockups/rest_sheet.png.
  REST_RENDERS=~/song29-mock python3 mock_rest.py
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
RENDERS = Path(os.path.expanduser(os.environ.get("REST_RENDERS", str(HERE.parent / "build" / "mock_rest"))))
FONT = HERE.parent / "assets" / "fonts" / "BarlowCondensed-Medium.ttf"
LOOKS = [("A", "A  ·  a dash, as the rests between patterns are today"),
         ("B", "B  ·  a tile like a pattern's, a dash in it (the rests between patterns stay a bare dash)")]
SHOTS = [("SKIFF_song_rest", "Playing, SONG ON: T3 starts two passes later (its A, a REST x2, picked), T4 and T6 end "
                             "sooner (a REST after their last pattern)"),
         ("SKIFF_song_rest_pick", "Stopped: T3 on its REST; KNOB 2 on T2's G turned to REST, OCT+ SET REST"),
         ("CRYPT_song_rest", "CRYPT"), ("NEON_song_rest", "NEON"), ("QUARK_song_rest", "QUARK")]

if __name__ == "__main__":
    sw = sh = 480
    pad, head, capf, titf = 24, 56, ImageFont.truetype(str(FONT), 22), ImageFont.truetype(str(FONT), 30)
    sheet = Image.new("RGB", (len(SHOTS) * (sw + pad) + pad, len(LOOKS) * (head + sh + 100) + pad), (24, 24, 24))
    g = ImageDraw.Draw(sheet)
    for r, (look, title) in enumerate(LOOKS):
        y0 = pad + r * (head + sh + 100)
        g.text((pad, y0 + 8), title, font=titf, fill=(255, 255, 255))
        for c, (name, cap) in enumerate(SHOTS):
            im = Image.open(RENDERS / look / "ppm" / f"{name}.ppm").convert("RGB").resize((sw, sh), Image.NEAREST)
            x, y = pad + c * (sw + pad), y0 + head
            sheet.paste(im, (x, y))
            words, line, ly = cap.split(), "", y + sh + 12
            for w in words:
                if g.textlength(line + " " + w, font=capf) > sw and line:
                    g.text((x, ly), line, font=capf, fill=(220, 220, 220))
                    line, ly = w, ly + 26
                else:
                    line = (line + " " + w).strip()
            g.text((x, ly), line, font=capf, fill=(220, 220, 220))
    sheet.save(HERE / "mockups" / "rest_sheet.png")
    print("wrote mockups/rest_sheet.png")
