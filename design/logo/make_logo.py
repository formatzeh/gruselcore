#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Skiff's logo (concept C, STEPS, the user's pick of four, 2026-10-12): sixteen steps of a sequencer as the sea, lit to
the swell in the six tracks' colours (the SKIFF palette, tools/gen_ui_palettes.py), a pixel skiff riding the crest, the
word in the screen's 5 x 7 letters. All squares: one list of them makes the SVGs and, pixel for pixel, the PNGs.

  python3 make_logo.py   -> docs/logo/: skiff-logo.svg (white, for dark), skiff-logo-light.svg (ink, for light),
                            skiff-icon.svg + skiff-icon-512.png (the square), skiff-social.png (GitHub's 1280 x 640)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "logo"
TRK = [(255, 90, 54), (34, 195, 180), (255, 191, 0), (149, 128, 255), (255, 111, 174), (163, 230, 53)]
WHITE, INK, OFF, OFF_LIGHT, SLATE, NIGHT = (255,) * 3, (22,) * 3, (44,) * 3, (214, 206, 190), (30,) * 3, (12,) * 3
BOAT = ["..............X",                              # the skiff: its raked bow at the right, a square stern
        "XXXXXXXXXXXXXX.",
        ".XXXXXXXXXXXX..",
        "..XXXXXXXXXX..."]
GLYPH = {"S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
         "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
         "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
         "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"]}


def sea(n, lit, x0, base, step, cell, off):
    """n steps (columns), each lit up to lit[i] (0..3) of its four, in the tracks' colours left to right"""
    return [(x0 + i * step, base - r * step, cell, cell, TRK[i * 6 // n] if r <= lit[i] else off, 3 * cell / 18)
            for i in range(n) for r in range(4)]


def boat(x0, y0, p, c):
    return [(x0 + j * p, y0 + r * p, p, p, c, 0) for r, row in enumerate(BOAT) for j, ch in enumerate(row) if ch == "X"]


def letters(text, x0, y0, q, c):
    out = []
    for ch in text:
        out += [(x0 + j * q, y0 + r * q, q, q, c, 0) for r, row in enumerate(GLYPH[ch]) for j, b in enumerate(row) if b == "1"]
        x0 += 6 * q
    return out, x0 - q


def logo(ink, off):
    """the lockup: 760 x 200 (the sea 16 steps, the skiff on its crest at steps 9..12, the word)"""
    r = sea(16, [2, 3, 3, 2, 1, 0, 0, 1, 2, 3, 3, 2, 1, 0, 0, 1], 0, 176, 22, 18, off) + boat(176, 68, 10, ink)
    w, x1 = letters("SKIFF", 380, 58, 16, ink)
    return x1 + 2, 200, r + w


def icon(ink, off, bg):
    """the square, 200 x 200 on its card: eight steps, the skiff on their crest"""
    r = [(0, 0, 200, 200, bg, 40)]
    r += sea(8, [1, 2, 3, 3, 2, 1, 0, 0], 13, 142, 22, 18, off) + boat(20, 40, 8, ink)
    return 200, 200, r


def to_svg(w, h, rects):
    def one(x, y, rw, rh, c, rx):
        a = f' rx="{rx:g}"' if rx else ""
        return f'<rect x="{x:g}" y="{y:g}" width="{rw:g}" height="{rh:g}"{a} fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" width="{w:g}" height="{h:g}">'
            + "".join(one(*r) for r in rects) + "</svg>\n")


def to_png(w, h, rects, scale, bg=None, size=None, at=(0, 0)):
    im = Image.new("RGBA", size or (round(w * scale), round(h * scale)), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x, y, rw, rh, c, rx in rects:
        box = [at[0] + x * scale, at[1] + y * scale, at[0] + (x + rw) * scale - 1, at[1] + (y + rh) * scale - 1]
        if rx:
            d.rounded_rectangle(box, radius=rx * scale, fill=c)
        else:
            d.rectangle(box, fill=c)
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "skiff-logo.svg").write_text(to_svg(*logo(WHITE, OFF)), encoding="utf-8")
    (OUT / "skiff-logo-light.svg").write_text(to_svg(*logo(INK, OFF_LIGHT)), encoding="utf-8")
    (OUT / "skiff-icon.svg").write_text(to_svg(*icon(WHITE, OFF, SLATE)), encoding="utf-8")
    to_png(*icon(WHITE, OFF, SLATE), 512 / 200).save(OUT / "skiff-icon-512.png")
    w, h, r = logo(WHITE, OFF)                       # GitHub's social preview: the lockup over the line, on the night
    soc = to_png(w, h, r, 1.2, (*NIGHT, 255), (1280, 640), ((1280 - w * 1.2) / 2, 150))
    font = ImageFont.truetype(str(ROOT / "assets" / "fonts" / "BarlowCondensed-Medium.ttf"), 46)
    line = "A six-track groovebox firmware for the M-VAVE FM-1"
    d = ImageDraw.Draw(soc)
    d.text(((1280 - d.textlength(line, font=font)) / 2, 470), line, font=font, fill=(200, 200, 200))
    soc.convert("RGB").save(OUT / "skiff-social.png")
    print("wrote", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
