#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Skiff's picture for the FM-1 Firmware Hub (fm1.designburgapps.com: a landscape card, 2:1, shown 460..640 px wide and
cropped to its middle square in the hub's drifting lineup), from the firmware's own screens (tests/ui_render.c's ppm,
pixel for pixel) and the logo's squares (design/logo/make_logo.py). Three directions:
  A  THEMES      the lockup over three screens in three themes (CRYPT's fire scope, NEON's FM6 page, QUARK's mixer)
  B  WORKFLOW    the lockup over HOME's six tracks, the SHIFT map, the FM6 page; a line under each
  C  HERO        the FM6 page in NEON in the middle, the icon and the name left, what Skiff has right
Each at 800 x 400 (the screens 1x). The user's pick (2026-10-13): A, as docs/logo/skiff-hub.png and, at 1600 x 800 (the
screens 2x, nearest), skiff-hub-2x.png.

  RENDERS=~/skiff-fm6-ui/build/ui_new/ppm python3 hub_card.py   -> design/mockups/hub_card_{a,b,c}.png, hub_cards.png;
                                                                   docs/logo/skiff-hub.png, skiff-hub-2x.png
The hub shows pictures square, so the 2:1 card came out cropped and squeezed; (2026-10-18) the user's pick for a square
one, E (the icon and the word over HOME and the FM6 page):
  RENDERS=... python3 hub_card.py square   -> docs/logo/skiff-hub-square.png (480), skiff-hub-square-2x.png (960)
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "logo"))
import make_logo as L                                    # noqa: E402

RENDERS = Path(os.path.expanduser(os.environ.get("RENDERS", str(HERE.parent / "build" / "ui_new" / "ppm"))))
FONTS = HERE.parent / "assets" / "fonts"
NIGHT, TEXT, MID, DIM = (12, 12, 12), (255, 255, 255), (184, 184, 184), (110, 110, 110)


def font(bold, px):
    return ImageFont.truetype(str(FONTS / ("BarlowCondensed-Bold.ttf" if bold else "BarlowCondensed-Medium.ttf")), px)


def screen(name, z):
    return Image.open(RENDERS / f"{name}.ppm").convert("RGB").resize((240 * z, 240 * z), Image.NEAREST)


def lockup(im, x, y, h, z):
    """the logo's lockup (the sea, the skiff, the word), h px tall at 1x, its top left at (x, y)"""
    w, hh, r = L.logo(L.WHITE, L.OFF)
    s = h * z / hh
    im.alpha_composite(L.to_png(w, hh, r, s), (round(x * z), round(y * z)))
    return w * s / z


def icon(im, x, y, size, z):
    w, h, r = L.icon(L.WHITE, L.OFF, (24, 24, 24))
    im.alpha_composite(L.to_png(w, h, r, size * z / w), (round(x * z), round(y * z)))


def word(im, x, y, q, z):
    _, x1 = L.letters("SKIFF", 0, 0, q * z, L.WHITE)
    r, _ = L.letters("SKIFF", round(x * z), round(y * z), q * z, L.WHITE)
    d = ImageDraw.Draw(im)
    for rx, ry, rw, rh, c, _ in r:
        d.rectangle([rx, ry, rx + rw - 1, ry + rh - 1], fill=c)


def text(im, xy, s, px, col, z, bold=False, anchor="la"):
    ImageDraw.Draw(im).text((xy[0] * z, xy[1] * z), s, font=font(bold, px * z), fill=col, anchor=anchor)


def frame(im, x, y, z, col=(40, 40, 40)):
    ImageDraw.Draw(im).rectangle([x * z - 1, y * z - 1, (x + 240) * z, (y + 240) * z], outline=col, width=1)


def card_a(z):
    im = Image.new("RGBA", (800 * z, 400 * z), (*NIGHT, 255))
    lockup(im, 24, 22, 40, z)
    text(im, (776, 50), "six tracks · fourteen engines · six themes", 22, MID, z, anchor="rs")
    for i, n in enumerate(["CRYPT_home_scope", "NEON_fm_op_tone", "QUARK_six_mixer"]):
        x = 24 + i * 256
        im.paste(screen(n, z), (x * z, 80 * z))
        frame(im, x, 80, z)
    text(im, (400, 372), "FM6 FROM SCRATCH  ·  SONGS AND PERFORM  ·  A SCREEN THAT SHOWS EVERY CONTROL'S JOB", 20,
         MID, z, anchor="ms")
    return im


def card_b(z):
    im = Image.new("RGBA", (800 * z, 400 * z), (*NIGHT, 255))
    lockup(im, 24, 18, 40, z)
    text(im, (776, 46), "a six-track groovebox for the M-VAVE FM-1", 22, MID, z, anchor="rs")
    caps = [("SIX TRACKS", "fourteen engines, songs, PERFORM"), ("HOLD HOME", "every control's job, on screen"),
            ("FM6 FROM SCRATCH", "the sound drawn as it plays")]
    for i, n in enumerate(["SKIFF_six_home", "SKIFF_shift_home", "NEON_fm_op_tone"]):
        x = 24 + i * 256
        im.paste(screen(n, z), (x * z, 74 * z))
        frame(im, x, 74, z)
        text(im, (x, 342), caps[i][0], 22, TEXT, z, bold=True, anchor="ls")
        text(im, (x, 366), caps[i][1], 19, MID, z, anchor="ls")
    return im


def card_c(z):
    im = Image.new("RGBA", (800 * z, 400 * z), (*NIGHT, 255))
    icon(im, 52, 70, 168, z)
    word(im, 54, 262, 6, z)
    text(im, (138, 340), "for the M-VAVE FM-1", 20, MID, z, anchor="ms")
    im.paste(screen("NEON_fm_op_tone", z), (280 * z, 80 * z))
    frame(im, 280, 80, z, (90, 40, 150))
    lines = [("6", "tracks, 14 engines"), ("FM6", "built on the unit"), ("SONG", "lists, scenes, PERFORM"),
             ("6", "themes: CRYPT, NEON, QUARK"), ("WEB", "editor and installer")]
    for i, (big, small) in enumerate(lines):
        y = 112 + i * 44
        text(im, (546, y), big, 30, TEXT, z, bold=True, anchor="ls")
        bw = ImageDraw.Draw(im).textlength(big, font=font(True, 30 * z)) / z
        text(im, (546 + bw + 8, y), small, 21, MID, z, anchor="ls")
    return im


def card_square(z):
    """(2026-10-18, the user's pick E) square, as the hub shows a picture (img/<id>.png: its lineup crops to 1:1, its list
    is a 60 px box; the 2:1 card came out cropped and squeezed): the icon and the word over HOME and the FM6 page, 480 x
    480 at z 1 (the screens 0.9x: drawn at z 2 and scaled down, so z 1 is z 2 resized)"""
    im = Image.new("RGBA", (480 * z, 480 * z), (*NIGHT, 255))
    icon(im, 20, 20, 176, z)
    word(im, 214, 40, 6, z)
    text(im, (216, 128), "six-track groovebox", 27, MID, z)
    text(im, (216, 160), "for the M-VAVE FM-1", 27, MID, z)
    for x, n in ((16, "SKIFF_six_home"), (248, "NEON_fm_op_tone")):
        im.paste(screen(n, 2).resize((216 * z, 216 * z), Image.LANCZOS), (x * z, 248 * z))
        ImageDraw.Draw(im).rectangle([x * z - 1, 248 * z - 1, (x + 216) * z, (248 + 216) * z], outline=(40, 40, 40))
    return im


def main():
    if "square" in sys.argv[1:]:                         # hub_card.py square: only the square picture
        big = card_square(2).convert("RGB")
        big.save(HERE.parent / "docs" / "logo" / "skiff-hub-square-2x.png", optimize=True)
        big.resize((480, 480), Image.LANCZOS).save(HERE.parent / "docs" / "logo" / "skiff-hub-square.png", optimize=True)
        print("skiff-hub-square.png, skiff-hub-square-2x.png")
        return
    out = HERE / "mockups"
    for k, fn in (("a", card_a), ("b", card_b), ("c", card_c)):
        fn(1).convert("RGB").save(out / f"hub_card_{k}.png", optimize=True)
    card_a(1).convert("RGB").save(HERE.parent / "docs" / "logo" / "skiff-hub.png", optimize=True)
    card_a(2).convert("RGB").save(HERE.parent / "docs" / "logo" / "skiff-hub-2x.png", optimize=True)
    sheet = Image.new("RGB", (800 + 32, 3 * 400 + 4 * 16), (40, 40, 40))
    for i, k in enumerate("abc"):
        sheet.paste(Image.open(out / f"hub_card_{k}.png"), (16, 16 + i * 416))
    sheet.save(out / "hub_cards.png", optimize=True)
    print("hub_card_{a,b,c}.png, hub_cards.png")


if __name__ == "__main__":
    main()
