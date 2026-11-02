#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
"""Load WAV files into a Felucca user sample slot (USR1..USR3) over USB-MIDI.

  fm1_sample_upload.py info
  fm1_sample_upload.py load SLOT NAME file.wav[:ROOT[:LO-HI]] ...   (SLOT 1..3)
  fm1_sample_upload.py erase SLOT
  fm1_sample_upload.py mix SLOT [SOUND LEVEL [REV [DLY]]]          (Skiff: a sound's level and sends)
  fm1_sample_upload.py build NAME OUT_PREFIX file.wav[...] ...      (no device: writes OUT_PREFIX.hdr / .bin)

Each file becomes one zone: mono, 22050 Hz, IMA ADPCM (sampleio.py, the same encoder
as the built-in sets and the web editor). ROOT is a MIDI note (default: from the file
name, C4 = 60, else 60); without LO-HI the zones split the keyboard between their roots.
A slot holds 80 KiB (about 7 s at 22050 Hz). Protocol: web/EDITOR_PROTOCOL.md, cmds 11..15.
mix lists the slot's sounds (zones, lowest keys first) with their LEVEL, REV and DLY, or sets
those of sound SOUND (1..16), in % as the unit shows them: LEVEL 100 plays it as loaded, REV and
DLY are added to the track's REVERB and DELAY sends (cmd 81: Skiff after 1.3.3).
Needs mido (and a backend such as python-rtmidi) for the device commands.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sampleio as sio  # noqa: E402

HDR = [0x7D, 0x46, 0x4C]
RC = {1: "size", 2: "header", 3: "data CRC", 4: "flash", 5: "zones"}


def printable(b):
    """bytes from the device as text for the terminal: printable ASCII only (no escape sequences)"""
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in b)


def slot_info(r):
    """the SMP_INFO reply -> one line per slot; ValueError when it is malformed"""
    try:
        n, i, out = r[0], 2, []
        for k in range(n):
            nz = r[i]
            j = r.index(0, i + 1)
            out.append(f"USR{k + 1}: {'empty' if not nz else f'{nz} zones, {printable(r[i + 1:j])}, {r[j + 1]} KiB'}")
            i = j + 2
        return out
    except (IndexError, ValueError):
        raise ValueError("malformed SMP_INFO reply from the device") from None


NOTES = "C C# D D# E F F# G G# A A# B".split()
pct = lambda v: (v * 100 + 63) // 127                       # noqa: E731  a 0..127 value as the unit shows it (%)
raw = lambda p: (p * 127 + 50) // 100                       # noqa: E731  .. and back (every % 0..100 round trips)


def mix_rows(r):
    """the SMP_MIX reply (slot, rc, nz, nz x (lo, hi), LEVEL x 16, REV x 16, DLY x 16) -> (rc, [(lo, hi, LEVEL, REV,
    DLY)] per sound, the 48 values); ValueError when it is malformed"""
    if len(r) < 3 or r[2] > 16 or len(r) != 3 + 2 * r[2] + 48:
        raise ValueError("malformed SMP_MIX reply from the device")
    v = r[3 + 2 * r[2]:]
    return r[1], [(r[3 + 2 * i], r[4 + 2 * i], v[i], v[16 + i], v[32 + i]) for i in range(r[2])], v


def mix_lines(slot, rows):
    name = lambda n: f"{NOTES[n % 12]}{n // 12 - 1}"        # noqa: E731  (C4 = 60)
    return [f"USR{slot + 1} sound {i + 1:2}  {name(lo)}-{name(hi)}  LEVEL {pct(lv)} %  REV +{pct(rv)} %  DLY +{pct(dl)} %"
            for i, (lo, hi, lv, rv, dl) in enumerate(rows)] or [f"USR{slot + 1}: empty"]


def pack7(b):
    """groups of up to 7 bytes, each preceded by their top bits"""
    out = []
    for i in range(0, len(b), 7):
        g = b[i:i + 7]
        out.append(sum(((x >> 7) & 1) << j for j, x in enumerate(g)))
        out += [x & 0x7F for x in g]
    return out


class Link:
    def __init__(self):
        try:
            import mido
        except ImportError:
            sys.exit("needs mido: pip install mido python-rtmidi")
        self.mido = mido
        outs = [n for n in mido.get_output_names() if "Felucca" in n]
        ins = [n for n in mido.get_input_names() if "Felucca" in n]
        if not outs or not ins:
            sys.exit("no MIDI port named Felucca: connect the FM-1 (running Felucca) by USB")
        self.o = mido.open_output(outs[0])
        self.i = mido.open_input(ins[0])
        for _ in range(3):                          # the first frame after opening the port can be lost
            try:
                self.req(1, [], 1.0)
                break
            except TimeoutError:
                pass

    def req(self, cmd, args, timeout=3.0):
        for _ in self.i.iter_pending():
            pass
        self.o.send(self.mido.Message("sysex", data=HDR + [cmd] + list(args)))
        t0 = time.time()
        while time.time() - t0 < timeout:
            for m in self.i.iter_pending():
                if m.type == "sysex" and list(m.data[:4]) == HDR + [cmd]:
                    return list(m.data[4:])
            time.sleep(0.002)
        raise TimeoutError(f"no reply to cmd {cmd}")


def build(name, specs):
    """specs: "file.wav[:ROOT[:LO-HI]]" -> (header, ADPCM data) for SMP_END / SMP_WRITE"""
    zones = []
    for spec in specs:
        parts = spec.split(":")
        path = Path(parts[0])
        root = int(parts[1]) if len(parts) > 1 and parts[1] else sio.note_from_name(path.stem)
        lo, hi = (int(v) for v in parts[2].split("-")) if len(parts) > 2 else (None, None)
        sr, x = sio.read_any_wav(path)
        x = sio.resample(x, sr, sio.SLOT_RATE)
        if not x:
            raise ValueError(f"{path}: no audio")
        zones.append((sio.to_int16(x), root, lo, hi))
    return sio.user_slot(name, zones)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("info", "load", "erase", "mix", "build"):
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd in ("load", "build"):
        if len(sys.argv) < 5:
            sys.exit(__doc__)
        try:
            hdr, data = build(sys.argv[3] if cmd == "load" else sys.argv[2], sys.argv[4:])
        except (OSError, ValueError) as e:
            sys.exit(f"cannot build the slot: {e}")
        if cmd == "build":
            Path(sys.argv[3] + ".hdr").write_bytes(hdr)
            Path(sys.argv[3] + ".bin").write_bytes(data)
            print(f"{sys.argv[2]}: {len(data)} B ADPCM, {hdr[6]} zones")
            return
    if cmd != "info":
        if len(sys.argv) < 3 or sys.argv[2] not in ("1", "2", "3"):
            sys.exit("SLOT is 1, 2 or 3")
        slot = int(sys.argv[2]) - 1
    link = Link()
    if cmd == "info":
        try:
            print("\n".join(slot_info(link.req(15, []))))
        except ValueError as e:
            sys.exit(str(e))
        return
    if cmd == "erase":
        print("erase:", "ok" if link.req(14, [slot], 10)[1] == 0 else "FAILED")
        return
    if cmd == "mix":
        try:
            want = [int(v) for v in sys.argv[3:7]]
            if want and (len(want) < 2 or not 1 <= want[0] <= 16 or not all(0 <= v <= 100 for v in want[1:])):
                raise ValueError
        except ValueError:
            sys.exit("mix SLOT [SOUND LEVEL [REV [DLY]]]: SOUND 1..16, the rest 0..100 (%)")
        try:
            rc, rows, v = mix_rows(link.req(81, [slot]))
            if want:
                if want[0] > len(rows):
                    sys.exit(f"USR{slot + 1} has {len(rows)} sounds")
                for w, p in enumerate(want[1:]):
                    v[16 * w + want[0] - 1] = raw(p)
                rc, rows, v = mix_rows(link.req(81, [slot] + v))
        except ValueError as e:
            sys.exit(str(e))
        except TimeoutError:
            sys.exit("no reply to mix: this firmware has no per-sound levels (Skiff after 1.3.3 has them)")
        if rc == 1:
            sys.exit("mix: refused")
        print("\n".join(mix_lines(slot, rows)))
        if rc == 2:
            print("  (the sample fills the slot: these values stay until the power goes)")
        return
    print(f"USR{slot + 1} {sys.argv[3]}: {len(data)} B ADPCM, {hdr[6]} zones")
    if link.req(11, [slot])[1]:
        sys.exit("begin failed")
    t0 = time.time()
    for off in range(0, len(data), 256):
        a = sio.SLOT_DATA_OFF + off
        r = link.req(12, [slot, a & 0x7F, (a >> 7) & 0x7F, (a >> 14) & 0x7F] + pack7(data[off:off + 256]))
        if r[4]:
            sys.exit(f"write at {a:#x} failed ({r[4]})")
        print(f"\r  {min(off + 256, len(data))} / {len(data)}", end="", flush=True)
    r = link.req(13, [slot] + pack7(hdr), 5)
    print(f"\n  {time.time() - t0:.1f} s, end:", "ok" if r[1] == 0 else f"FAILED ({r[1]}, {RC.get(r[1], '?')})")


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        sys.exit(f"{e}: is Felucca running, and no other app using its MIDI port?")
