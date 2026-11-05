#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
"""Build the SAMPLER engine's sample sets from WAV files into a C header.

Samples are stored as IMA ADPCM (4 bit) at their native rate; loop points
and roots come from the WAV 'smpl' chunk and the file name (C3 = MIDI 60
naming), single-cycle waves get their root from rate / loop length.
The ADPCM state at the loop start is stored so loops restart exactly.

Libraries:
  cc0        assets/samples-cc0/ (tools/fetch_cc0.py, Versilian Studios, CC0):
             PIANO, FLUTE, SAX (set 1, once TRANH, and set 4, once PERC, are aliases of PIANO)
SAMPLE's factory presets end before set 4 (SMP_PERC_SLOT); every sample set and SET / USR
index stays in its original place.
A retired set keeps its index as an alias: the original's name and zones (no data), and a
preset equal to the original's (SMP_SET_ORIG), so old projects and presets play it and
browsing skips it (params.c enum_orig, ui.c preset_orig).
Set 4 was PERC, the GM-mapped drum kit (Felucca's generated drums and CC0 hand percussion,
~66 KB of flash): retired, the DRUM engine plays the same GM map. A sound that selected it
loads as DRUM with its default kit (core.h drum_from_perc); what that cannot reach (GRAIN's
SRC, a value sent live) plays the alias, PIANO.

(GruselCore) The SLICE engine has no built-in loops any more (BREAK, FUNK and PIANO were retired):
it plays the user slots only, so nothing of it is written here.

The header is cached (build/gen_samples.cache) under a hash of every
input file, this script, sampleio.py and the Python version, so unchanged
inputs skip the slow pitch detection.
"""
import hashlib
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sampleio as sio  # noqa: E402
from sampleio import detect_hz, hz_to_midi, ima_encode, key_split, onset, peak, read_any_wav, resample  # noqa: E402

SRC = Path(__file__).resolve().parents[1]
CACHE = SRC / "build" / "gen_samples.cache"
CC0 = SRC / "assets" / "samples-cc0"
TR = 22050                                   # stored sample rate

# CC0 library: set -> kind ("oneshot" decaying, "sus" looped sustain, "kit" one sample per key)
# Built-in sets (piano, flute, sax); the other slots of the 8 are for the user (USR1-3, loaded
# from the web editor). TRANH was removed (66 KB of flash); its index 1 stays, an alias of PIANO
# ("alias": the set named). PERC (the GM kit) was removed (66 KB); its index 4 stays, an alias of
# PIANO too (PERC_SLOT; its sounds load as the DRUM engine)
CC0_SETS = [("PIANO", "oneshot"), ("PIANO", "alias"), ("FLUTE", "sus"), ("SAX", "sus"), ("PIANO", "alias")]
PERC_SLOT = 4                                # core.h SMP_SET_PERC: SAMPLE's factory presets end before it
MEASURED_TUNING = ()                         # sets whose recordings are not at A440 (was TRANH, ~+35 ct)

KIT_BASE = 53                     # F3, the lowest FM-1 key

NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


ENV = {"wave":(5, 80, 100, 50), "kit": (0, 127, 127, 60), "multi": (0, 85, 0, 75),
       "oneshot": (0, 127, 127, 70), "sus": (12, 80, 120, 60)}
SET_TAG = {"PIANO": "PT_KEYS", "FLUTE": "PT_LEAD", "SAX": "PT_LEAD"}   # (Skiff phase 9) core.h PT_*: PRESETS' LIST
SET_HIDE = True    # (GruselCore) SAMPLE lists no presets: its set presets stay (SET numbers, aliases, the engine's
                   # default) but carry PT_HIDE (ui.c preset_skip)
SET_VARIANTS = []  # (GruselCore) Skiff's LOFI PIANO, MUSIC BOX, FLUTE PAD, DARK SAX and KOTO removed

# PIANO's notes cut to 0.75 s (saves flash), faded out over the last SET_FADE s; (Skiff 1.3) FLUTE's and SAX's to 0.68 s:
# their sustain loops (from 0.40 s) half as long, 0.28 s (18 KB of flash for 1.3's features)
SET_KEEP = {"PIANO": 0.75, "FLUTE": 0.68, "SAX": 0.68}
SET_FADE = {"PIANO": 0.15}

_wavs = {}


def cos_fade(x, fade):
    """fade the last `fade` samples of x out on a raised cosine (no corner at either end)"""
    n = len(x)
    for i in range(fade):
        x[n - fade + i] *= 0.5 + 0.5 * math.cos(math.pi * (i + 1) / fade)


def wav(path):
    """read_any_wav, once per file and run (the CC0 pass reads every file twice)"""
    if path not in _wavs:
        _wavs[path] = read_any_wav(path)
    return _wavs[path]


def name_note(name):
    """'_C#3' in a CC0 file name -> (octave, pitch class)"""
    m = re.search(r"_([A-G]#?)(-?\d)", name)
    return (int(m.group(2)), NOTE[m.group(1)]) if m else None


def cc0_entries(setname, kind):
    """-> [(file name, int16 samples at TR, loop or None, root)]"""
    files = sorted((CC0 / setname).glob("*.wav"))
    out = []
    if kind != "kit":
        # octave convention of this set (C4 = 60 or C3 = 60): YIN votes, the names give the notes
        votes = {1: 0, 2: 0}
        for p in files:
            nn = name_note(p.name)
            if not nn:
                continue
            sr, x = wav(p)
            det = hz_to_midi(detect_hz(x[onset(x):], sr))
            for o in (1, 2):
                if abs(det - ((nn[0] + o) * 12 + nn[1])) < 1.0:
                    votes[o] += 1
        conv = 2 if votes[2] >= votes[1] else 1
    for k, p in enumerate(files):
        sr, x = wav(p)
        x = x[max(0, onset(x) - 16):]
        nn = name_note(p.name)
        if kind == "kit":
            root = KIT_BASE + k
        elif nn:
            root = (nn[0] + conv) * 12 + nn[1]
            if setname in MEASURED_TUNING:              # tuned off A440: the measured pitch near the named note
                det = hz_to_midi(detect_hz(x, sr))
                if abs(det - root) < 1.0:
                    root = det
        else:
            root = hz_to_midi(detect_hz(x, sr))
        x = resample(x, sr, TR)
        keep = SET_KEEP.get(setname) or {"oneshot": 1.0, "sus": 0.95, "kit": 0.6}[kind]
        x = x[:int(keep * TR)]
        n = len(x)
        if kind == "sus":                            # crossfaded sustain loop in the steady part
            ls, le, xf = int(0.40 * TR), n - 1, int(0.06 * TR)
            for i in range(xf):
                a = i / xf
                x[le - xf + i] = x[le - xf + i] * (1 - a) + x[ls - xf + i] * a
            loop = (ls, le)
        else:
            if setname in SET_FADE:                  # a shortened set: a long raised-cosine fade-out
                cos_fade(x, int(SET_FADE[setname] * TR))
            else:
                fade = int(0.08 * TR)
                for i in range(fade):
                    x[n - fade + i] *= 1 - i / fade
            loop = None
        pk = peak(x)
        out.append((p.name, [int(v * 30000 / pk) for v in x], loop, root))
    return out


class Builder:
    def __init__(self):
        self.zones, self.sets, self.blob, self.kinds = [], [], bytearray(), {}
        self.alias = {}                         # set index -> the set index it aliases

    def add(self, s, loop_start):
        """ADPCM-encode s into the blob (each sample starts on an even offset) -> (offset, state at loop_start)"""
        enc, st = ima_encode(s, loop_start)
        off = len(self.blob)
        self.blob += enc
        if len(self.blob) & 1:
            self.blob.append(0)
        return off, st

    def add_set(self, name, kind, entries):
        """entries: zone dicts with root16 (and key for a kit); assigns the key ranges"""
        if not entries:
            return
        if kind == "kit":
            for e in entries:
                e["lo"] = e["hi"] = e["key"]
        else:
            entries.sort(key=lambda e: e["root16"])
            for e, (lo, hi) in zip(entries, key_split([e["root16"] // 16 for e in entries])):
                e["lo"], e["hi"] = lo, hi
        self.sets.append((name, len(self.zones), len(entries)))
        self.zones += entries
        self.kinds[name] = kind

    def alias_set(self, name):
        """a retired set's index: the zones of the earlier set `name` (no data of its own)"""
        orig = next(i for i, (n, _, _) in enumerate(self.sets) if n == name)
        self.alias[len(self.sets)] = orig
        self.sets.append(self.sets[orig])

    def cc0_set(self, name, kind):
        entries = []
        for k, (_, s, loop, root) in enumerate(cc0_entries(name, kind)):
            ls, le = loop if loop else (len(s), len(s))
            off, st = self.add(s, ls)
            entries.append(dict(off=off, n=len(s), ls=ls, le=le, looped=bool(loop), sr=TR,
                                root16=int(round(root * 16)), pred=st[0], idx=st[1],
                                key=KIT_BASE + k if kind == "kit" else None))
        self.add_set(name, kind, entries)

    def header(self):
        zones, sets, blob = self.zones, self.sets, self.blob
        L = ["/* generated by tools/gen_samples.py: IMA ADPCM sample sets */", "#pragma once",
             "#include <stdint.h>", ""]
        L.append(f"static const uint8_t SMP_DATA[{max(1, len(blob))}] = {{")
        for i in range(0, len(blob), 32):
            L.append("    " + ",".join(map(str, blob[i:i + 32])) + ",")
        if not blob:
            L.append("    0,")
        L.append("};")
        L.append("static const smp_zone_t SMP_ZONES[] = {")
        for e in zones:
            rate = int(round(e["sr"] / 44100 * 65536))
            L.append(f"    {{{e['off']}, {e['n']}, {e['ls']}, {e['le']}, {rate}, {e['root16']}, {e['pred']}, "
                     f"{e['idx']}, {e['lo']}, {e['hi']}, {1 if e['looped'] else 0}}},")
        if not zones:
            L.append("    {0, 0, 0, 0, 65536, 960, 0, 0, 0, 127, 0},")
        L.append("};")
        L.append("static const smp_set_t SMP_SETS[] = {")
        for name, z0, nz in sets:
            L.append(f'    {{"{name}", {z0}, {nz}}},')
        if not sets:
            L.append('    {"NONE", 0, 1},')
        L.append("};")
        L.append(f"#define SMP_NSETS {max(1, len(sets))}")
        named = sets or [("NONE", 0, 0)]
        perc = PERC_SLOT if len(named) > PERC_SLOT else len(named)
        # (Skiff phase 9) the variations follow PERC's slot, only with the CC0 sets their SET values name (PERC's
        # alias then is a preset among them, hidden as the other alias)
        full = len(named) == PERC_SLOT + 1
        var = SET_VARIANTS if full else []
        npre = len(named) + len(var) if full else perc   # (GruselCore) PERC's alias stays preset 4 without variations
        L.append(f"#define SMP_NPRESETS {npre}")
        if len(named) > PERC_SLOT:
            L.append(f"#define SMP_PERC_SLOT {PERC_SLOT}   /* once PERC (the GM kit): an alias, its sounds load as DRUM */")
        L.append("/* a preset per set (an alias: its original's, hidden by its name; PERC's past SMP_NPRESETS unless")
        L.append(" * variations follow, ui.c apply_preset_to loads it as DRUM), (Skiff phase 9) then the variations */")
        L.append("static const preset_t SMP_PRESET_TABLE[] = {")
        for i, (name, _, _) in enumerate(named):
            k = self.kinds.get(name, "wave")
            a, d, s_, r = ENV[k]
            loop = 0 if k == "kit" else 1
            si = self.alias.get(i, i)                   # an alias: the original's preset (hidden by its name)
            L.append(f'    {{"{name}", {{{si}, 0, 0, {loop}, 127, 0, 0, 0}}, {{{a}, {d}, {s_}, {r}}}, 0, 0, '
                     f'TAG({SET_TAG.get(name, "PT_NONE")}{" | PT_HIDE" if SET_HIDE else ""})}},')
        for name, e, env, mono, fx, tag, *more in var:  # (more: [(id, value)], as the engines' MORE)
            mo = ", ".join(f"{{{i}, {v}}}" for i, v in more[0]) if more else ""
            L.append(f'    {{"{name}", {{{", ".join(map(str, e))}}}, {{{", ".join(map(str, env))}}}, 0, {mono}, '
                     f'FX({", ".join(map(str, fx))}), ' + (f"MORE({mo}), " if mo else "") + f'TAG({tag})}},')
        L.append("};")
        orig = [self.alias.get(i, i) for i in range(len(named))]
        L.append("/* SET i plays SMP_SET_ORIG[i]: != i for a retired set kept as an alias (its preset i too) */")
        L.append("static const uint8_t SMP_SET_ORIG[] = {" + ", ".join(map(str, orig)) + "};")
        L.append(f"#define SMP_NALIAS {sum(1 for i, o in enumerate(orig) if o != i and i < npre)}   /* among the presets */")
        names = ", ".join(f'"{n}"' for n, _, _ in named)
        L.append("#define SMP_SET_NAMES_INIT " + names)
        L.append("static const char *const SMP_SET_NAMES[] = {" + names + "};")
        return "\n".join(L) + "\n"

    def summary(self):
        return f"samples: {len(self.sets)} sets, {len(self.zones)} zones, {len(self.blob)} B ADPCM"


def input_key(have_cc0):
    """hash of everything the header depends on"""
    h = hashlib.sha256()
    here = Path(__file__).resolve().parent
    for p in (here / "gen_samples.py", here / "sampleio.py"):
        h.update(p.read_bytes())
    h.update(repr((sys.version_info[:2], have_cc0)).encode())   # sum() differs across versions
    files = sorted(CC0.glob("*/*.wav")) if have_cc0 else []
    for p in files:
        h.update(str(p.relative_to(SRC)).encode() + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def main(out):
    have_cc0 = CC0.exists() and any(CC0.glob("*/*.wav"))
    if not have_cc0:
        print("samples: CC0 library not fetched (tools/fetch_cc0.py) - no SAMPLE sets")
    key = input_key(have_cc0)
    try:
        ck, summary, text = CACHE.read_text().split("\n", 2)
        if ck == key:
            Path(out).write_text(text)
            print(summary + " (cached)")
            return
    except (OSError, ValueError):
        pass
    b = Builder()
    if have_cc0:
        for name, kind in CC0_SETS:
            if kind == "alias":
                b.alias_set(name)
            else:
                b.cc0_set(name, kind)
    text = b.header()
    Path(out).write_text(text)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(f"{key}\n{b.summary()}\n{text}")
    print(b.summary())


if __name__ == "__main__":
    main(sys.argv[1])
