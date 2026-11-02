#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
"""The FM-1 controls cheat sheet of the README (1200 px wide, the style of the 1.0 feature sheet: dark
rounded cards, white Inter Tight text, Fukiai line icons). On top the panel, drawn (Skiff U6: the photo of
before is not in this tree), its screen showing Skiff's HOME, each group of controls marked by a coloured
band and its number; below, in two columns, one card per group: rows of a keycap (the pill the device's key
hints use, tools/gen_aa_keycaps.py) and what the control does. Hold actions carry the clock icon.

  gen_panel_diagram.py OUT.svg [--screen HOME.png] [--lang en|ja] [--ja-font NotoSansJP.ttf] [--png OUT.png]
                       [--jpg OUT.jpg]
  gen_panel_diagram.py --strip OUT.svg [--pitch-mm 9.8]

--screen: a render of the screen (tests/ui_render.c's SKIFF_home.ppm), drawn in the panel's screen. Every
control's box (CTRL) was measured on a 1750 x 1050 photo of the panel, in its pixels, and the panel is drawn
from them; each band is its controls' boxes and a small margin. Everything else is in one table (GROUPS),
English and Japanese side by side.
--strip (the review's L7): a key strip to print at 100 % (A4 landscape, a 100 mm bar to check), one strip for
the black keys and one for the white ones, as long as the key bed: what each key is in Skiff (the tracks' mutes
and cuts, the drum grid's lanes; the notes, steps, entries). --pitch-mm: the white keys' centres apart (measure
ten of them and divide; 9.8 mm is the spec's 161.5 mm body over the photo). The text is written as outlines (Inter Tight,
assets/fonts, OFL-1.1; for --lang ja the function texts in Noto Sans JP, OFL-1.1, given with --ja-font;
icons from web/fukiai.ttf, MIT), so the SVG needs no font. --png / --jpg render it with rsvg-convert (or
render the SVG in a browser at its size).
Checked: every text, keycap and icon inside its card (every keycap's label inside its pill), nothing
overlapping, the cards apart, the bands and their numbers on the photo and apart, each band around the
centres of all its group's controls and of no other group's.
"""
import argparse
import base64
import io
import logging
import subprocess
import sys
from pathlib import Path

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

logging.getLogger("fontTools").setLevel(logging.ERROR)   # fukiai.ttf: a harmless post-table note
ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "assets/fonts/InterTight[wght].ttf"
ICONS = ROOT / "web/fukiai.ttf"

W = 1200
BG, CARD = "#1e1e1e", "#484848"                         # sampled from the feature sheet
KEY, INK = "#d7d7d7", "#1e1e1e"                         # keycap: mix(BG, TEXT, 78 %), its label BG (gen_ui_palettes)
R = 17                                                  # card corner radius (feature sheet)
DIM = 0.62                                              # opacity of secondary text
HOLD_ICON = "symbol_clock"

# ------------------------------------------------------------------------------------------------ the table
# A group: its number on the photo (0: none, the clock), its band colour, the column, the title, a note
# beside the title, the bands (each the controls it frames, CTRL below) and the rows. A row: the keycaps
# ("+" between two: pressed together), hold (the clock before them), the text and a second, dim line.
COLORS = {1: "#f2b866", 2: "#7ec8e3", 3: "#f28b82", 4: "#8fd694", 5: "#c9a0f0"}   # 4: PLAY's green

GROUPS = [
    dict(n=1, col=0, title=("Knobs", "ノブ"), note=None,
         bands=[("SELECT", "MASTER", "ALGORITHM", "PRESETS"), ("KNOB 1", "KNOB 2", "KNOB 3", "KNOB 4")],
         rows=[
             (("SELECT",), 0, ("The page before or after in the family", "ファミリーの前後のページ"),
              ("BPM LOCK OFF: the tempo", "BPM LOCK OFF: テンポ")),
             (("MASTER",), 0, ("Volume", "音量"), None),
             (("ALGORITHM",), 0, ("Track T1–T6, on every page", "トラック T1–T6 を選ぶ（全ページ）"), None),
             (("PRESETS",), 0, ("The track's sound", "トラックの音色"),
              ("step pages: the cursor; lists: the pick", "ステップのページ: カーソル、リスト: 選択")),
             (("KNOB 1–4",), 0, ("The four cards of the page", "ページの 4 枚のカード"), None),
         ]),
    dict(n=2, col=0, title=("Page buttons", "ページボタン"), note=("again: the next page", "もう一度で次のページ"),
         bands=[("FX", "SEL", "ENV", "LFO", "EDIT", "GLO"), ("HOME", "SAVE", "ARP", "SEQ")],
         rows=[
             (("FX",), 0, ("Effects, SLICER, DUCK", "エフェクト、SLICER、DUCK"), None),
             (("SEL",), 0, ("Scale, chord keys", "スケール、コードキー"), None),
             (("ENV",), 0, ("Envelope and its destinations", "エンベロープとその行き先"), None),
             (("LFO",), 0, ("LFO, its destinations, MOD", "LFO、その行き先、MOD"), None),
             (("EDIT",), 0, ("The engine, its voices; from every page", "エンジンとボイス（どのページからも）"), None),
             (("GLO",), 0, ("Mixer, delay, reverb, chorus, global", "ミキサー、ディレイ、リバーブ、コーラス、全体"), None),
             (("HOME",), 0, ("Home: all six tracks", "ホーム: 6 トラック"), None),
             (("SAVE",), 0, ("Presets, user sounds, patterns, projects", "プリセット、ユーザー音色、パターン、プロジェクト"),
              None),
             (("ARP",), 0, ("Arpeggiator; flashes on the beat", "アルペジエーター（拍で点滅）"), None),
             (("SEQ",), 0, ("Step, roll, chance, play, pattern, automation, song",
                           "ステップ、ロール、確率、再生、パターン、オートメーション、ソング"), None),
         ]),
    dict(n=3, col=0, title=("Keys", "鍵盤"), note=None,
         bands=[("KEYS",)],
         rows=[
             (("KEYS",), 0, ("Play the selected track, F3–G5", "選んだトラックを演奏（F3–G5）"),
              ("STEP with REC: write steps (drums: the grid)", "STEP で REC 中: ステップ入力（ドラムはグリッド）")),
         ]),
    dict(n=4, col=1, title=("Transport", "再生・録音"), note=None,
         bands=[("PLAY", "REC")],
         rows=[
             (("PLAY",), 0, ("Start / stop all six tracks", "6 トラックを再生・停止"),
              ("lit green while playing", "再生中は緑に点灯")),
             (("REC",), 0, ("Arm the selected track, on the press", "選んだトラックを録音待機（押した瞬間）"),
              ("stopped: starts playing too", "停止中なら再生も始まる")),
         ]),
    dict(n=5, col=1, title=("Octave", "オクターブ"), note=None,
         bands=[("OCT-", "OCT+")],
         rows=[
             (("OCT−",), 0, ("Octave down", "オクターブ下げ"),
              ("dialogs, action pages: back; undo box: further", "ダイアログ等: 戻る、アンドゥ中: さらに戻す")),
             (("OCT+",), 0, ("Octave up", "オクターブ上げ"),
              ("dialogs, action pages: do it; undo box: redo", "ダイアログ等: 実行、アンドゥ中: やり直し")),
             (("OCT−", "OCT+"), 0, ("Octave reset", "オクターブをリセット"), None),
         ]),
    dict(n=0, col=1, title=("Hold", "長押し"), note=None, bands=[],
         rows=[
             (("FX",), 1, ("Effects on the keys, cuts on the black", "鍵盤でエフェクト、黒鍵でカット"), None),
             (("GLO",), 1, ("Solos, mutes, FILL, tap; KNOB 1–4 levels", "ソロ・ミュート・FILL・タップ、ノブで音量"), None),
             (("SEL",), 1, ("A key sets the root", "鍵盤でルート"), None),
             (("EDIT",), 1, ("A white key picks the engine", "白鍵でエンジンを選ぶ"), None),
             (("ARP",), 1, ("PERFORM: launch patterns, mutes, scenes", "PERFORM: パターン切替、ミュート、シーン"), None),
             (("SEQ",), 1, ("SEQ TOOLS: clear, reverse, random, cook", "SEQ TOOLS: 消去・反転・ランダム・COOK"), None),
             (("SAVE",), 1, ("Undo (8 levels)", "アンドゥ（8 段）"), None),
             (("HOME",), 1, ("SHIFT: what every control does here", "SHIFT: このページの操作一覧"),
              ("let go alone: the MENU", "単独で離すとメニュー")),
             (("GLO", "SELECT"), 1, ("Tempo", "テンポ"), None),
             (("GLO", "PLAY"), 1, ("Restart from the top", "頭から再スタート"), None),
         ]),
    dict(n=0, col=1, title=("SHIFT (HOME held) +", "SHIFT（HOME 長押し）+"), note=None, bands=[],
         rows=[
             (("SAVE",), 0, ("TAKE: keep the loop you just played", "TAKE: いま弾いたループを残す"), None),
             (("REC",), 0, ("The REC layer: clear, click, count-in, feel", "REC レイヤー: 消去・クリック・カウント・FEEL"),
              None),
             (("FX",), 0, ("Or GLO, SEL, EDIT, ARP, SEQ: keep its layer open", "ほかのレイヤーボタンも: 開いたままにする"),
              None),
         ]),
]
TITLE = ("FM-1 controls in Skiff", "Skiff の FM-1 操作")   # the SVG's <title> only

# Every control's box on the photo (its pixels), measured on it: the knobs are the part darker than the
# panel around them (knob and shadow, the printed names excluded), the buttons and OCT-/+ their bright caps
# between the dark gaps, the keys the bed inside its dark outline. Each contains the anchor the earlier,
# leader-line diagram used for it (panel_en.svg's knobs, OCT- and keys; the buttons on the photo).
CTRL = {
    "MASTER": (124, 117, 219, 237), "SELECT": (299, 117, 394, 240),
    "PRESETS": (114, 287, 217, 410), "ALGORITHM": (286, 286, 394, 413),
    "KNOB 1": (919, 113, 1019, 238), "KNOB 2": (1108, 115, 1203, 238),
    "KNOB 3": (1294, 112, 1389, 238), "KNOB 4": (1477, 113, 1577, 236),
    "FX": (962, 319, 1037, 394), "SEL": (1066, 318, 1141, 393), "ENV": (1170, 318, 1245, 393),
    "LFO": (1274, 318, 1349, 393), "EDIT": (1378, 317, 1452, 392), "GLO": (1482, 317, 1557, 392),
    "HOME": (963, 421, 1038, 497), "SAVE": (1068, 420, 1143, 496), "ARP": (1172, 420, 1247, 496),
    "SEQ": (1276, 420, 1351, 495), "PLAY": (1380, 419, 1455, 495), "REC": (1483, 419, 1559, 495),
    "OCT-": (154, 461, 241, 509), "OCT+": (284, 461, 371, 508),
    "KEYS": (91, 585, 1652, 951),
}
BAND_M = 8                                              # a band: its controls' boxes and this margin


def band_box(names):
    bs = [CTRL[n] for n in names]
    return (min(b[0] for b in bs) - BAND_M, min(b[1] for b in bs) - BAND_M,
            max(b[2] for b in bs) + BAND_M, max(b[3] for b in bs) + BAND_M)

# --------------------------------------------------------------------------------------------- text
class Face:
    def __init__(self, font, tag):
        self.font = font
        self.tag = tag
        self.upm = font["head"].unitsPerEm
        self.cmap = font.getBestCmap()
        self.gs = font.getGlyphSet()
        self.hmtx = font["hmtx"]
        self.ids = {}

    def glyph(self, name):
        """the id of the glyph's path in <defs> (None: an empty glyph)"""
        if name not in self.ids:
            pen = SVGPathPen(self.gs)
            self.gs[name].draw(pen)
            d = pen.getCommands()
            self.ids[name] = f"{self.tag}{len(self.ids)}" if d else None
            if d:
                defs.append(f'<path id="{self.ids[name]}" d="{d}"/>')
        return self.ids[name]

    def bounds(self, name):
        pen = BoundsPen(self.gs)
        self.gs[name].draw(pen)
        return pen.bounds                       # font units, y up; None when empty

    def gname(self, c):
        if ord(c) not in self.cmap:
            raise SystemExit(f"{self.tag}: no glyph for {c!r}")
        return self.cmap[ord(c)]

    def width(self, s, size):
        return sum(self.hmtx[self.gname(c)][0] for c in s) * size / self.upm


defs = []         # glyph outlines, once each
out = []          # svg elements
boxes = []        # (x0, y0, x1, y1, label, container): texts, keycaps, icons, badges
solids = []       # cards and the photo: (x0, y0, x1, y1, name)
marks = []        # bands and badges on the photo: (x0, y0, x1, y1, name)
desc = []         # every text, for <desc>
FACES = {}


def load_faces(ja_font, ja_text):
    for w in (450, 600):
        FACES["lat", w] = Face(instancer.instantiateVariableFont(TTFont(FONT), {"wght": w}), f"t{w}_")
    if ja_font:
        f = TTFont(ja_font)
        opt = subset.Options()
        opt.layout_features = []
        opt.notdef_outline = False
        sub = subset.Subsetter(opt)
        sub.populate(unicodes=sorted({ord(c) for c in ja_text}))
        sub.subset(f)
        for w in (450, 600):
            FACES["ja", w] = Face(instancer.instantiateVariableFont(f if w == 600 else TTFont(_sub_copy(f)),
                                                                     {"wght": w}), f"j{w}_")
    FACES["icon"] = Face(TTFont(ICONS), "i")


def _sub_copy(f):
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    return buf


def ink(face, items, k, ox, oy):
    """the ink box of glyphs (name, pen_x in font units) drawn at (ox, oy) with scale k, y down"""
    xs, ys = [], []
    for name, px in items:
        b = face.bounds(name)
        if b:
            xs += [ox + (px + b[0]) * k, ox + (px + b[2]) * k]
            ys += [oy - b[3] * k, oy - b[1] * k]
    return min(xs), min(ys), max(xs), max(ys)


def text(s, x, y, size, weight=450, anchor="start", op=1.0, inside=None, fam="lat", fill=None, reg=True):
    """s at baseline y; anchor start / middle / end; inside = the box it must fit in. Returns its ink box."""
    f = FACES[fam, weight]
    w = f.width(s, size)
    x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
    k = size / f.upm
    parts, items, pen_x = [], [], 0.0
    for c in s:
        g = f.gname(c)
        gid = f.glyph(g)
        if gid:
            parts.append(f'<use href="#{gid}" x="{pen_x:.0f}"/>')
            items.append((g, pen_x))
        pen_x += f.hmtx[g][0]
    o = f' fill-opacity="{op}"' if op < 1 else ""
    fl = f' fill="{fill}"' if fill else ""
    out.append(f'<g transform="translate({x0:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})"{fl}{o}>{"".join(parts)}</g>')
    ib = ink(f, items, k, x0, y)
    if reg:
        # the line box (cap height and descenders) or the ink, whichever is larger
        boxes.append((min(x0, ib[0]), min(y - size * 0.74, ib[1]), max(x0 + w, ib[2]), max(y + size * 0.22, ib[3]),
                      s, inside))
        desc.append(s)
    return ib


def icon(name, x, y, size, op=1.0, inside=None):
    """Fukiai glyph name, its em box with the top-left at (x, y)"""
    f = FACES["icon"]
    k = size / f.upm
    asc = f.font["hhea"].ascent
    o = f' fill-opacity="{op}"' if op < 1 else ""
    out.append(f'<use href="#{f.glyph(name)}" transform="translate({x:.2f} {y + asc * k:.2f}) '
               f'scale({k:.5f} {-k:.5f})"{o}/>')
    ix0, iy0, ix1, iy1 = ink(f, [(name, 0)], k, x, y + asc * k)
    boxes.append((min(x, ix0), min(y, iy0), max(x + size, ix1), max(y + size, iy1), name, inside))


def rect(x, y, w, h, r, fill="none", stroke=None, sw=1.5, fop=1.0):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' fill-opacity="{fop}"' if fop < 1 else ""
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" fill="{fill}"{o}{s}/>')
    return (x, y, x + w, y + h)


# ------------------------------------------------------------------------------------------- keycaps
CAP_H, CAP_R, CAP_SIZE, CAP_PAD = 24, 7.5, 14, 6.5     # gen_aa_keycaps' 13 / 4 / 9 / 3 px, about x 1.85
bad_caps = []


def cap_ink(label):
    f = FACES["lat", 600]
    items, pen_x = [], 0.0
    for c in label:
        g = f.gname(c)
        items.append((g, pen_x))
        pen_x += f.hmtx[g][0]
    k = CAP_SIZE / f.upm
    x0, _, x1, _ = ink(f, items, k, 0, 0)
    return x0, x1


def cap_w(label):
    x0, x1 = cap_ink(label)
    return x1 - x0 + 2 * CAP_PAD


def keycap(label, x, ymid, inside):
    """the pill CAP_PAD each side of the label's ink, the caps centred on ymid; returns its right edge"""
    f = FACES["lat", 600]
    ix0, ix1 = cap_ink(label)
    w = ix1 - ix0 + 2 * CAP_PAD
    pill = rect(x, ymid - CAP_H / 2, w, CAP_H, CAP_R, fill=KEY)
    cap = f.font["OS/2"].sCapHeight * CAP_SIZE / f.upm
    lb = text(label, x + CAP_PAD - ix0, ymid + cap / 2, CAP_SIZE, 600, fill=INK, reg=False)
    if not (pill[0] + CAP_PAD - 0.5 <= lb[0] and lb[2] <= pill[2] - CAP_PAD + 0.5 and pill[1] + 3 <= lb[1]
            and lb[3] <= pill[3] - 3):
        bad_caps.append(f"label {label!r} off its pill")
    boxes.append(pill + ("cap " + label, inside))
    desc.append(label)
    return pill[2]


def lead_w(caps, hold):
    """the width of a row's lead: the clock, the keycaps and the '+' between them"""
    w = (HOLD_SZ + 8 if hold else 0) + sum(cap_w(c) for c in caps)
    return w + (len(caps) - 1) * PLUS_W


HOLD_SZ, PLUS_W = 20, 22


# --------------------------------------------------------------------------------------------- photo
CROP = (70, 60, 1680, 980)                              # the body, the key bed's bottom edge (951) included
PW = 640
PX, PY = (W - PW) / 2, 24                               # the cards' margin M; no title above
PS = PW / (CROP[2] - CROP[0])
PH = (CROP[3] - CROP[1]) * PS
PHOTO = (PX, PY, PX + PW, PY + PH)


def at(x, y):
    return PX + (x - CROP[0]) * PS, PY + (y - CROP[1]) * PS


SCREEN = (472, 100, 862, 482)                          # the screen's bezel (photo px, measured as CTRL)
WHITE_X0, WHITE_P = 120, 93.6                           # the white keys: the first one's left edge, their pitch
BLACK_Y, WHITE_Y = (603, 754), (767, 930)               # the two key rows
BLACK_AFTER = (0, 1, 2, 4, 5, 7, 8, 9, 11, 12, 14)      # the white keys (from F3) a black key follows
BODY, PART, PRINT = "#2c2c2f", "#454549", "#9a9aa0"


def panel(screen):
    """the FM-1 drawn from CTRL (Skiff U6: no photo): the body, its knobs, buttons and keys with their printed
    names, the screen showing screen (a render, or nothing)"""
    rect(PHOTO[0], PHOTO[1], PW, PH, R, fill=BODY)
    solids.append(PHOTO + ("panel",))
    for n, c in CTRL.items():
        (x0, y0), (x1, y1) = at(c[0], c[1]), at(c[2], c[3])
        if n == "KEYS":
            continue
        if n in ("MASTER", "SELECT", "PRESETS", "ALGORITHM") or n.startswith("KNOB"):
            cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2 + 3, min(x1 - x0, y1 - y0) * 0.36
            out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{PART}" stroke="#5c5c61" stroke-width="1.5"/>')
            out.append(f'<line x1="{cx:.2f}" y1="{cy - r + 2:.2f}" x2="{cx:.2f}" y2="{cy - r * 0.4:.2f}" '
                       f'stroke="{PRINT}" stroke-width="1.5"/>')
            text(n.replace("KNOB ", "KNOB"), cx, cy - r - 4, 8.5, 600, "middle", fill=PRINT, reg=False)
        else:
            rect(x0, y0, x1 - x0, y1 - y0, 3.5, fill=PART)
            text(n.replace("-", "−"), (x0 + x1) / 2, (y0 + y1) / 2 + 3, 8, 600, "middle", fill=PRINT, reg=False)
    for i in range(16):                                 # the keys: the white row under the black one
        (x0, y0), (x1, y1) = at(WHITE_X0 + i * WHITE_P + 8, WHITE_Y[0]), at(WHITE_X0 + (i + 1) * WHITE_P - 8, WHITE_Y[1])
        rect(x0, y0, x1 - x0, y1 - y0, 5, fill=PART)
    for i in BLACK_AFTER:
        (x0, y0), (x1, y1) = (at(WHITE_X0 + (i + 1) * WHITE_P - 31, BLACK_Y[0]),
                              at(WHITE_X0 + (i + 1) * WHITE_P + 31, BLACK_Y[1]))
        rect(x0, y0, x1 - x0, y1 - y0, 5, fill="#38383c")
    (x0, y0), (x1, y1) = at(SCREEN[0], SCREEN[1]), at(SCREEN[2], SCREEN[3])
    rect(x0, y0, x1 - x0, y1 - y0, 9, fill="#111113")
    if screen:
        from PIL import Image
        im = Image.open(screen).convert("RGB").resize((480, 480), Image.NEAREST)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        side = min(x1 - x0, y1 - y0) - 16
        sx, sy = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
        out.append(f'<image x="{sx:.2f}" y="{sy:.2f}" width="{side:.2f}" height="{side:.2f}" '
                   f'href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>')


BADGE_R = 12


def badge(n, cx, cy, reg_list, inside=None):
    color = COLORS[n]
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{BADGE_R}" fill="{color}"/>')
    b = (cx - BADGE_R, cy - BADGE_R, cx + BADGE_R, cy + BADGE_R)
    t = text(str(n), cx, cy + 5.3, 15, 600, "middle", fill=INK, reg=False)
    if not (b[0] + 3 <= t[0] and t[2] <= b[2] - 3 and b[1] + 3 <= t[1] and t[3] <= b[3] - 3):
        bad_caps.append(f"badge {n}: number off its circle")
    reg_list.append(b + (f"badge {n}", inside) if reg_list is boxes else b + (f"badge {n}",))


def bands():
    for g in GROUPS:
        for i, names in enumerate(g["bands"]):
            a, b = (at(*p) for p in zip(*[iter(band_box(names))] * 2))
            rect(a[0], a[1], b[0] - a[0], b[1] - a[1], 7, fill=COLORS[g["n"]], fop=0.13,
                 stroke=COLORS[g["n"]], sw=2)
            marks.append((a[0], a[1], b[0], b[1], f"band {g['n']}.{i}"))
    for g in GROUPS:                                 # the numbers on every band's top-left corner (on the photo)
        for i, names in enumerate(g["bands"]):
            a = at(*band_box(names)[:2])
            badge(g["n"], max(a[0] + 2, PHOTO[0] + BADGE_R + 4), max(a[1] + 2, PHOTO[1] + BADGE_R + 4), marks)


# --------------------------------------------------------------------------------------------- cards
M, GAP, CGAP = 24, 16, 14
CW = (W - 2 * M - GAP) / 2
ROW, SUB = 34, 19
HEAD = 56


def card_h(g):
    return HEAD + sum(ROW + (SUB if r[3] else 0) for r in g["rows"]) + 12


def card(g, x0, y0, L):
    x1, y1 = x0 + CW, y0 + card_h(g)
    rect(x0, y0, CW, y1 - y0, R, fill=CARD)
    box = (x0, y0, x1, y1)
    solids.append(box + (g["title"][0],))
    if g["n"]:
        badge(g["n"], x0 + 20 + BADGE_R, y0 + 28, boxes, box)
    else:
        icon(HOLD_ICON, x0 + 20, y0 + 16, 24, inside=box)
    fam = "ja" if L else "lat"
    text(g["title"][L], x0 + 20 + 2 * BADGE_R + 10, y0 + 35, 20, 600, inside=box, fam=fam)
    if g["note"]:
        text(g["note"][L], x1 - 20, y0 + 34, 14, 450, "end", op=DIM, inside=box, fam=fam)
    tx = x0 + 20 + max(lead_w(r[0], r[1]) for r in g["rows"]) + 14
    y = y0 + HEAD
    for caps, hold, main, sub in g["rows"]:
        mid = y + ROW / 2 - 4
        x = x0 + 20
        if hold:
            icon(HOLD_ICON, x, mid - HOLD_SZ / 2, HOLD_SZ, op=0.85, inside=box)
            x += HOLD_SZ + 8
        for i, c in enumerate(caps):
            if i:
                text("+", x + PLUS_W / 2, mid + 5.5, 16, 600, "middle", op=0.85, inside=box)
                x += PLUS_W
            x = keycap(c, x, mid, box)
        text(main[L], tx, mid + 5.5, 16, 450, inside=box, fam=fam)
        if sub:
            text(sub[L], tx, mid + 5.5 + SUB, 13.5, 450, op=DIM, inside=box, fam=fam)
        y += ROW + (SUB if sub else 0)
    return y1


def build(screen, L):
    top = PY + PH + 20
    hs = [top, top]
    for g in GROUPS:
        hs[g["col"]] += card_h(g) + CGAP
    H = round(max(hs) - CGAP + M)
    out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    panel(screen)
    bands()
    ys = [top, top]
    for g in GROUPS:
        c = g["col"]
        ys[c] = card(g, M + c * (CW + GAP), ys[c], L) + CGAP
    return H


# --------------------------------------------------------------------------------------------- checks
def check(H):
    bad = list(bad_caps)

    def over(a, b, e=0.5):
        return a[0] < b[2] - e and b[0] < a[2] - e and a[1] < b[3] - e and b[1] < a[3] - e

    for b in boxes:
        x0, y0, x1, y1, s, c = b
        if not (0 <= x0 and x1 <= W and 0 <= y0 and y1 <= H):
            bad.append(f"off the canvas: {s!r}")
        if c and not (c[0] + 12 <= x0 and x1 <= c[2] - 12 and c[1] + 8 <= y0 and y1 <= c[3] - 6):
            bad.append(f"outside its card: {s!r} {tuple(round(v) for v in b[:4])} in {tuple(round(v) for v in c)}")
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if over(a, b):
                bad.append(f"overlap: {a[4]!r} / {b[4]!r}")
    for i, a in enumerate(solids):
        if not (0 <= a[0] and a[2] <= W and 0 <= a[1] and a[3] <= H):
            bad.append(f"card off the canvas: {a[4]}")
        for b in solids[i + 1:]:
            if over(a, b, -6):                       # at least 6 px apart
                bad.append(f"cards too close: {a[4]} / {b[4]}")
    for i, a in enumerate(marks):
        if not (PHOTO[0] + 2 <= a[0] and a[2] <= PHOTO[2] - 2 and PHOTO[1] + 2 <= a[1] and a[3] <= PHOTO[3] - 2):
            bad.append(f"off the panel: {a[4]}")
        for b in marks[i + 1:]:
            if a[4].startswith("band") and b[4].startswith("band") and over(a, b, -3):
                bad.append(f"bands touch: {a[4]} / {b[4]}")
            if a[4].startswith("badge") and b[4].startswith("badge") and over(a, b, -2):
                bad.append(f"badges touch: {a[4]} / {b[4]}")
    for g in GROUPS:                                 # each band frames its controls and no other group's
        for i, names in enumerate(g["bands"]):
            x0, y0, x1, y1 = band_box(names)
            for h in GROUPS:
                for n in (n for nn in h["bands"] for n in nn):
                    c = CTRL[n]
                    cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
                    inside = x0 < cx < x1 and y0 < cy < y1
                    if n in names and not inside or h is not g and inside:
                        bad.append(f"band {g['n']}.{i}: {n} {'inside' if inside else 'outside'}")
    return bad


# ------------------------------------------------------------------------------------------- key strip
STRIP_BLACK = [("T1", "BD"), ("T2", "SD"), ("T3", "CP"), ("T4", "CH"), ("T5", "OH"), ("T6", "TM"), ("", "RS"),
               ("", "CB"), ("", "ACC"), ("", "PG−"), ("", "PG+")]
NOTES = "FGABCDEFGABCDEFG"


def strip(path, pitch):
    """the key strip, in mm on an A4 landscape page: the black keys' (their tracks for FX / GLO / PERFORM's mutes and
    cuts, the drum grid's lanes) and the white keys' (notes, steps, entries); each cell centred on its key"""
    load_faces(None, "")
    pw, ph, x0 = 297.0, 210.0, 60.0
    ln = 16 * pitch

    def cells(y, h, rows, centres, heads):
        rect(x0, y, ln, h, 1.5, stroke="#000", sw=0.25)
        for j, (head, size) in enumerate(heads):
            text(head, x0 - 3, y + (j + 1) * h / (len(heads) + 1) + size * 0.35, size, 600, "end", fill="#555", reg=False)
        for cx, lines in zip(centres, rows):
            for j, t in enumerate(lines):
                size = heads[j][1]
                if t:
                    text(t, cx, y + (j + 1) * h / (len(lines) + 1) + size * 0.35, size, 600 if j == 0 else 450,
                         "middle", fill="#000", reg=False)

    out.append(f'<rect width="{pw}" height="{ph}" fill="#fff"/>')
    text("Skiff key strip: the FM-1's keys F3 to G5", 20, 22, 6, 600, fill="#000", reg=False)
    text(f"Print at 100 %: the bar must measure 100 mm. White keys {pitch:g} mm apart (--pitch-mm). Cut along the "
         "frames.", 20, 30, 3.6, 450, fill="#000", reg=False)
    rect(20, 36, 100, 2, 0, fill="#000")
    text("100 mm", 124, 38.3, 3.2, 450, fill="#000", reg=False)
    whites = [x0 + (i + 0.5) * pitch for i in range(16)]
    blacks = [x0 + (i + 1) * pitch for i in BLACK_AFTER]
    cells(56, 16, STRIP_BLACK, blacks, [("MUTE / CUT", 3.4), ("DRUM GRID", 2.8)])
    cells(84, 22, [(NOTES[i], str(i + 1), "ABCDEFGHIJKLMNOP"[i]) for i in range(16)], whites,
          [("NOTE", 3.4), ("STEP", 2.8), ("ENTRY, SCENE", 2.8)])
    for cx in blacks:                                   # tick marks: each black key's centre
        rect(cx - 0.15, 52, 0.3, 3, 0, fill="#000")
    for cx in whites:
        rect(cx - 0.15, 80, 0.3, 3, 0, fill="#000")
    text("Black keys: T1–T6 mute (GLO, PERFORM) or cut (FX) their track; on a drum track's grid they pick the lane "
         "(BD .. CB), ACC, and the grid's page.", 20, 125, 3.4, 450, fill="#000", reg=False)
    text("White keys: notes from F3; on STEP with REC and the drum grid, steps 1–16; PERFORM's entries A–P and "
         "scenes 1–16.", 20, 132, 3.4, 450, fill="#000", reg=False)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw}mm" height="{ph}mm" viewBox="0 0 {pw} {ph}">'
           f'<title>Skiff key strip</title>\n<defs>{"".join(defs)}</defs>\n' + "\n".join(out) + "\n</svg>\n")
    Path(path).write_text(svg, encoding="utf-8")
    print(f"{path}: A4, strips {ln:.1f} mm long")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", nargs="?")
    ap.add_argument("--screen", help="a render of the screen, drawn in the panel's (SKIFF_home.ppm)")
    ap.add_argument("--strip", help="write the key strip (SVG, mm) instead")
    ap.add_argument("--pitch-mm", type=float, default=9.8, help="the key strip: the white keys' centres apart")
    ap.add_argument("--lang", choices=("en", "ja"), default="en")
    ap.add_argument("--ja-font", help="Noto Sans JP (variable, wght), for --lang ja")
    ap.add_argument("--png")
    ap.add_argument("--jpg")
    a = ap.parse_args()
    if a.strip:
        strip(a.strip, a.pitch_mm)
        return
    if not a.svg:
        ap.error("the card needs OUT.svg")
    L = a.lang == "ja"
    if L and not a.ja_font:
        ap.error("--lang ja needs --ja-font")
    ja_text = ""
    if L:
        ja_text = "".join(g["title"][1] + (g["note"][1] if g["note"] else "") +
                                     "".join(r[2][1] + (r[3][1] if r[3] else "") for r in g["rows"]) for g in GROUPS)
    load_faces(a.ja_font if L else None, ja_text)
    H = build(a.screen, L)
    bad = check(H)
    if bad:
        print("\n".join(bad), file=sys.stderr)
        sys.exit(1)
    d = " / ".join(desc).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = TITLE[L].replace("&", "&amp;")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="#fff">'
           f'<title>{t}</title><desc>{d}</desc>\n'
           f'<defs>{"".join(defs)}</defs>\n' + "\n".join(out) + "\n</svg>\n")
    Path(a.svg).write_text(svg, encoding="utf-8")
    print(f"{a.svg}: {W} x {H}, {len(boxes)} texts / keycaps / icons, {len(solids)} cards, {len(marks)} marks "
          f"checked, {len(svg)} bytes")
    for out_path in (a.png, a.jpg):
        if not out_path:
            continue
        png = out_path + ".tmp.png"
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", png, a.svg], check=True)
        from PIL import Image
        im = Image.open(png).convert("RGB")
        if out_path == a.jpg:
            im.save(out_path, "JPEG", quality=90, optimize=True, progressive=True, subsampling=0)
        else:
            im.save(out_path, "PNG", optimize=True)
        Path(png).unlink()
        print(f"{out_path}: {Path(out_path).stat().st_size} bytes")


if __name__ == "__main__":
    main()
