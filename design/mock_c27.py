#!/usr/bin/env python3
"""#27 (@tradiuz): THEME CUSTOM, the user's colours from the web editor, and a switch for HOME's figure at the playhead.
One sheet of firmware renders (tests/ui_render.c: CUSTOM_<look>_*, PHLINE_<palette>_*, the THEMEs' own) and the
editor's Settings > Device display (mockups/c27_editor.png, the editor on its mock device), with the choices to make.
  C27_RENDERS=~/skiff-c27/build/ui_new python3 mock_c27.py   -> mockups/c27_sheet.png
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "assets" / "fonts"
OUTD = HERE / "mockups"
RENDERS = Path(os.path.expanduser(os.environ.get("C27_RENDERS", str(HERE.parent / "build" / "ui_new"))))
BG, INK, MID, DIM, GREEN = "#0C0C0C", "#F2F2F2", "#B4B4B4", "#5A5A5A", "#30D158"
FONT = {}


def font(bold, px):
    k = (bold, px)
    if k not in FONT:
        FONT[k] = ImageFont.truetype(str(FONTS / ("BarlowCondensed-Bold.ttf" if bold else "BarlowCondensed-Medium.ttf")), px)
    return FONT[k]


def shot(path, z=2):
    im = Image.open(RENDERS / path).convert("RGB")
    return im.resize((im.width * z, im.height * z), Image.NEAREST)


def option(g, x, y, key, title, rec=False):
    g.text((x, y), f"{key}  {title}", font=font(True, 30), fill=INK)
    if rec:
        tx = x + g.textlength(f"{key}  {title}", font=font(True, 30)) + 14
        g.rounded_rectangle((tx, y + 4, tx + 150, y + 34), 6, fill=GREEN)
        g.text((tx + 75, y + 19), "RECOMMENDED", font=font(True, 19), fill=BG, anchor="mm")


def lines(g, x, y, text, w=1500, px=22, fill=MID):
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            t = (cur + " " + word).strip()
            if g.textlength(t, font=font(False, px)) > w and cur:
                g.text((x, y), cur, font=font(False, px), fill=fill)
                y += px + 6
                cur = word
            else:
                cur = t
        g.text((x, y), cur, font=font(False, px), fill=fill)
        y += px + 6
    return y


def caption(g, x, y, text):
    g.text((x + 240, y), text, font=font(True, 22), fill=MID, anchor="mt")


def main():
    W, PAD, S = 2080, 40, 480
    sheet = Image.new("RGB", (W, 4200), BG)
    g = ImageDraw.Draw(sheet)
    g.text((PAD, 30), "#27  THEME CUSTOM AND PLAYHEAD", font=font(True, 56), fill=INK)
    lines(g, PAD, 100, "@tradiuz: a custom colour set for the theme, as Felucca's web editor has; and a way to turn off the "
          "figure at the playhead (\"a bit distracting for the vaporwave and quark schemes\"). Every screen below is the "
          "firmware's own render. Answer with a letter for each of 1, 2 and 3 (e.g. A A A).", w=W - 2 * PAD)

    y = 190
    g.text((PAD, y), "1  THEME CUSTOM: WHOSE LOOK?", font=font(True, 40), fill=INK)
    y = lines(g, PAD, y + 54, "The web editor stores eleven colours on the unit: BG SURF TEXT THEME ACCENT and the six tracks'. "
              "THEME gets CUSTOM as its last value once a set is stored (MENU > DISPLAY > THEME wraps through it, the "
              "editor's Theme list too). Kept with the settings; firmware before shows the look's own THEME and keeps the bytes.",
              w=W - 2 * PAD) + 10
    option(g, PAD, y, "A", "THE LOOK YOU PICK IN THE EDITOR: SKIFF, CRYPT, NEON OR QUARK, ITS FACES AND WIDGETS IN YOUR COLOURS", rec=True)
    y += 50
    for i, look in enumerate(["SKIFF", "CRYPT", "NEON", "QUARK"]):
        x = PAD + i * (S + 30)
        sheet.paste(shot(f"CUSTOM_{look}/six_home.png"), (x, y))
        caption(g, x, y + S + 8, f"CUSTOM in {look}'s look")
    y += S + 50
    for i, look in enumerate(["SKIFF", "CRYPT", "NEON", "QUARK"]):
        x = PAD + i * (S + 30)
        sheet.paste(shot(f"CUSTOM_{look}/env.png"), (x, y))
    y += S + 30
    y = lines(g, PAD, y, "The motifs stay: CRYPT's skulls, torch, stone and pixel letters; NEON's chrome, sunset bands and "
              "high score table; QUARK's brackets, Monte Carlo fill and collisions. Their art keeps its own colours (the "
              "torch's flame, the sun's bands); everything that follows the THEME follows yours, on the SMK-37's pads too.",
              w=W - 2 * PAD) + 14
    option(g, PAD, y, "B", "ALWAYS SKIFF'S PLAIN LOOK (FELUCCA'S CUSTOM): YOUR COLOURS ON BLOCKS ONLY, THE FIRST PICTURE ABOVE")
    y += 70

    g.text((PAD, y), "2  PLAYHEAD: HOME'S FIGURE ON THE SELECTED LANE", font=font(True, 40), fill=INK)
    y = lines(g, PAD, y + 54, "MENU > DISPLAY > PLAYHEAD THEME (as now: CRYPT's torch, NEON's car, QUARK's collision) or LINE "
              "(the playhead's line only). SKIFF, HI-CON and PAPER draw no figure either way. Left of each pair THEME, "
              "right LINE.", w=W - 2 * PAD) + 10
    for i, p in enumerate(["NEON", "QUARK", "CRYPT"]):   # (the lanes only, 2x: y 76..214 of the screen)
        x, yy = PAD + (i % 2) * 1010, y + (i // 2) * 330
        for k, f in enumerate([f"{p}/six_home.png", f"PHLINE_{p}/six_home.png"]):
            sheet.paste(shot(f).crop((0, 152, 480, 428)), (x + k * 495, yy))
            g.text((x + k * 495 + 240, yy + 284), f"{p}: {'THEME' if not k else 'LINE'}", font=font(True, 22), fill=MID,
                   anchor="mt")
    y += 2 * 330 + 10
    sheet.paste(shot("CUSTOM_SKIFF/menu.png"), (PAD, y))
    caption(g, PAD, y + S + 8, "MENU > DISPLAY (THEME CUSTOM in use)")
    x0 = PAD + S + 50
    option(g, x0, y, "A", "PLAYHEAD: THEME / LINE, RIGHT UNDER THEME", rec=True)
    yy = lines(g, x0, y + 46, "DISPLAY's rows become seven, so the tab scrolls (as SYSTEM's seven and MIDI's ten do): HINTS "
               "is the one under the fold. PLAYHEAD is Skiff's word for it (\"cursor\" is the step cursor on the SEQ pages).",
               w=W - x0 - PAD) + 16
    option(g, x0, yy, "B", "THE SAME ROW LAST IN DISPLAY, AFTER HINTS")
    yy = lines(g, x0, yy + 46, "THEME's neighbours stay as they are; the new row is the one under the fold.", w=W - x0 - PAD) + 16
    option(g, x0, yy, "C", "CURSOR: ON / OFF, THE ISSUE'S WORD")
    yy = lines(g, x0, yy + 46, "Reads as the request; but it is the playhead's figure, not the step cursor.", w=W - x0 - PAD)
    y += S + 70

    g.text((PAD, y), "3  WHICH FIGURES DOES LINE TAKE AWAY?", font=font(True, 40), fill=INK)
    y += 60
    option(g, PAD, y, "A", "ALL THREE: CRYPT'S TORCH, NEON'S CAR, QUARK'S COLLISION", rec=True)
    y = lines(g, PAD, y + 46, "One switch, one meaning in every THEME.", w=W - 2 * PAD) + 10
    option(g, PAD, y, "B", "NEON'S CAR AND QUARK'S COLLISION ONLY (THE TWO THE ISSUE NAMES); CRYPT KEEPS ITS TORCH")
    y += 80

    g.text((PAD, y), "THE WEB EDITOR: SETTINGS > DEVICE DISPLAY", font=font(True, 40), fill=INK)
    y = lines(g, PAD, y + 54, "Eleven colour wells, Look (whose faces and widgets), Start from... (a THEME's own colours), "
              "Show on the device (the unit shows each change at once, RAM only), Save, Revert, Remove. Colours hard to read "
              "get a warning; the unit keeps what it is given. The editor wears CUSTOM too while it is in use (here QUARK's "
              "look: the dotted rule under the headings). After Felucca 1.6's custom palette.", w=W - 2 * PAD) + 10
    ed = Image.open(OUTD / "c27_editor.png").convert("RGB")
    ed = ed.resize((ed.width * 2, ed.height * 2), Image.LANCZOS)
    sheet.paste(ed, (PAD, y))
    y += ed.height + PAD
    sheet = sheet.crop((0, 0, W, y))
    sheet.save(OUTD / "c27_sheet.png", optimize=True)
    print(f"mockups/c27_sheet.png {sheet.width} x {sheet.height}")


if __name__ == "__main__":
    main()
