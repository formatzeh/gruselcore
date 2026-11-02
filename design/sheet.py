#!/usr/bin/env python3
"""one review sheet per direction: its six screens at 2x, 3 columns x 2 rows"""
from pathlib import Path
from PIL import Image

OUT = Path(__file__).parent / "out"
NAMES = ["home", "sound", "step", "perform", "take", "confirm"]
for key in "ABC":
    sheet = Image.new("RGB", (3 * 480 + 4 * 16, 2 * 480 + 3 * 16), (40, 40, 40))
    for i, n in enumerate(NAMES):
        im = Image.open(OUT / f"{key}_{n}.png").resize((480, 480), Image.NEAREST)
        sheet.paste(im, (16 + (i % 3) * 496, 16 + (i // 3) * 496))
    sheet.save(OUT / f"sheet_{key}.png")
print("sheets written")
