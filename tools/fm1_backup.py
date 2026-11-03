#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""(GruselCore) A whole FM-1 backed up to a file and restored from it, from the terminal, over the editor protocol
(web/EDITOR_PROTOCOL.md: BACKUP_LIST / GET / PUT and the sample commands). The file is the browser editor's backup
format (web/fm1backup.js): either one restores what the other saved.

    python tools/fm1_backup.py backup FILE.json     everything: the music, settings, projects, user sounds, the pattern
                                                    bank, the sample slots
    python tools/fm1_backup.py restore FILE.json    all of it back (every object checked before the first write; the
                                                    music last, as the editor does)

Needs mido and python-rtmidi (as tools/fm1_install.py). Playback must be stopped."""
import base64
import json
import sys
import time
import zlib

import mido

HDR = [0x7D, 0x46, 0x4C]


class FM1:
    def __init__(self):
        outs = [n for n in mido.get_output_names() if "Felucca" in n or "FM-1" in n]
        ins = [n for n in mido.get_input_names() if "Felucca" in n or "FM-1" in n]
        if not outs or not ins:
            sys.exit("no FM-1 found (USB, MIDI)")
        self.o, self.i = mido.open_output(outs[0]), mido.open_input(ins[0])

    def req(self, cmd, *args, timeout=2.0, tries=3):
        """one request, its reply's arguments (None: no reply)"""
        for _ in range(tries):
            for _m in self.i.iter_pending():
                pass
            self.o.send(mido.Message("sysex", data=HDR + [cmd] + [int(a) & 127 for a in args]))
            t = time.time()
            while time.time() - t < timeout:
                for m in self.i.iter_pending():
                    if m.type == "sysex" and list(m.data[:4]) == HDR + [cmd]:
                        return list(m.data[4:])
                time.sleep(0.002)
        return None


def u32(n):
    return [(n >> (7 * i)) & (15 if i == 4 else 127) for i in range(5)]


def r32(a, o=0):
    return a[o] | a[o + 1] << 7 | a[o + 2] << 14 | a[o + 3] << 21 | a[o + 4] << 28


def unpack7(a, size):
    out, i = bytearray(), 0
    while len(out) < size:
        n, mask = min(7, size - len(out)), a[i]
        i += 1
        for k in range(n):
            out.append(a[i] | ((mask >> k) & 1) << 7)
            i += 1
    return bytes(out)


def pack7(b):
    out = []
    for o in range(0, len(b), 7):
        c = b[o:o + 7]
        out.append(sum(((x >> 7) & 1) << i for i, x in enumerate(c)))
        out += [x & 127 for x in c]
    return out


def restore(dev, path):
    """a backup file back onto the FM-1 as the browser editor restores it (web/fm1backup.js restoreBackup): every
    object checked first; then all but the settings and the music, the settings, the music last"""
    f = json.load(open(path))
    if f.get("format") != "felucca-backup" or f.get("version") != 1:
        sys.exit("not a Felucca backup")
    objs = []
    for o in f["objects"]:
        b = base64.b64decode(o["data"])
        if len(b) != o["size"] or zlib.crc32(b) & 0xFFFFFFFF != o["crc"]:
            sys.exit(f"backup object {o['id']}: checksum mismatch, nothing written")
        objs.append((o["id"], b, o["crc"]))
    must(dev.req(76, 2), "STOP")

    def put(*a):
        r = must(dev.req(67, *a, timeout=4.0, tries=1), "BACKUP_PUT")
        return r[2]
    for oid, b, crc in objs[2:] + [objs[1], objs[0]]:
        if oid >= 32:                                   # a sample slot: by the sample commands
            slot = oid - 32
            if not b:
                must(dev.req(14, slot, timeout=6.0, tries=1), "SMP_ERASE")
            else:
                must(dev.req(11, slot, timeout=6.0, tries=1), "SMP_BEGIN")
                for off in range(512, len(b), 256):
                    must(dev.req(12, slot, off & 127, off >> 7 & 127, off >> 14 & 127, *pack7(b[off:off + 256]),
                                 timeout=4.0, tries=1), "SMP_WRITE")
                must(dev.req(13, slot, *pack7(b[:480]), timeout=6.0, tries=1), "SMP_END")
            print(f"  sample slot {slot}: {len(b)} bytes")
            continue
        rc = put(0, oid, *u32(len(b)), *u32(crc))
        if rc == 1 and (oid == 9 or 16 <= oid < 32):    # (as the editor: an object this firmware doesn't take)
            continue
        if rc:
            sys.exit(f"object {oid}: begin refused (rc {rc})")
        try:
            for off in range(0, len(b), 256):
                if put(1, oid, *u32(off), *pack7(b[off:off + 256])):
                    raise RuntimeError(f"object {oid} at {off}")
            if put(2, oid):
                raise RuntimeError(f"object {oid}: commit")
        except RuntimeError as e:
            put(3, oid)
            sys.exit(f"restore stopped: {e}")
        print(f"  object {oid:2d}: {len(b)} bytes")
    print(f"restored {path}")


IDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] + list(range(16, 32)) + [32, 33, 34]


def backup(dev, path):
    """the browser editor's backup file (web/fm1backup.js captureBackup), every object read and checked"""
    a = dev.req(65, timeout=3.0)
    if not a or a[0] != 1 or a[1]:
        sys.exit(f"backup refused (rc {a[1] if a else 'none'}): stop playback first")
    n = a[2]
    objs = []
    for k in range(n):
        p = 3 + k * 11
        oid, size, crc = a[p], r32(a, p + 1), r32(a, p + 6)
        data = bytearray()
        for off in range(0, size, 256):
            c = min(256, size - off)
            r = dev.req(66, oid, *u32(off), c & 127, c >> 7, timeout=1.0)
            if not r or r[0] != oid or r[1] or r32(r, 2) != off:
                sys.exit(f"backup: object {oid} at {off} failed")
            data += unpack7(r[9:], c)
        if zlib.crc32(bytes(data)) & 0xFFFFFFFF != crc:
            sys.exit(f"backup: object {oid} changed while reading (stop playback, try again)")
        objs.append({"id": oid, "size": size, "crc": crc, "data": base64.b64encode(bytes(data)).decode()})
        print(f"  object {oid:2d}: {size} bytes")
    info = dev.req(1)
    fw = bytes(info[: info.index(0)]).decode() if info else "?"
    json.dump({"format": "felucca-backup", "version": 1, "firmware": fw,
               "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "objects": objs}, open(path, "w"))
    print(f"backup: {len(objs)} objects -> {path}")


def must(r, what):
    if r is None:
        sys.exit(f"no reply: {what}")
    return r


def main(argv):
    if len(argv) == 3 and argv[1] == "backup":
        backup(FM1(), argv[2])
    elif len(argv) == 3 and argv[1] == "restore":
        restore(FM1(), argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
