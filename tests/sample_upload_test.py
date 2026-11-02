#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
"""tools/fm1_sample_upload.py `mix` (Skiff, #21) against a fake device: the SMP_MIX reply read, a sound's LEVEL / REV /
DLY set in % (the others as they were), every % 0..100 back as the unit shows it, malformed replies and arguments
refused.  tests/sample_upload_test.py"""
import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fm1_sample_upload as U  # noqa: E402

failed = 0


def ok(cond, what):
    global failed
    print(f"sample upload: {what:<70} {'ok' if cond else 'FAIL'}")
    failed += not cond


class FakeLink:
    """SMP_MIX (81) as editor.c ed_smp_mix answers it: slot, rc, nz, nz x (lo, hi), 48 values"""
    def __init__(self, nz=3, rc=0):
        self.mix, self.nz, self.rc, self.sent = [127] * 16 + [0] * 32, nz, rc, []

    def req(self, cmd, args, timeout=3.0):
        self.sent.append((cmd, list(args)))
        if len(args) == 49 and self.rc != 1:
            self.mix = list(args[1:])
        return [args[0], self.rc if len(args) == 49 else 0, self.nz] + sum(([60 + i, 60 + i] for i in range(self.nz)), []) \
            + self.mix


def cli(argv, link):
    U.Link = lambda: link
    sys.argv = ["fm1_sample_upload.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    rc = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            U.main()
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
            if not isinstance(e.code, int):
                err.write(str(e.code))
    return rc, out.getvalue(), err.getvalue()


ok(all(U.pct(U.raw(p)) == p for p in range(101)) and sorted({U.pct(v) for v in range(128)}) == list(range(101)),
   "every % 0..100 is a value the unit shows as that %")
rc, rows, v = U.mix_rows([0, 0, 2, 60, 60, 62, 64] + list(range(48)))
ok(rc == 0 and rows == [(60, 60, 0, 16, 32), (62, 64, 1, 17, 33)] and v == list(range(48)),
   "SMP_MIX reply: each sound's keys, LEVEL, REV, DLY")
for bad in ([0, 0], [0, 0, 2, 60, 60] + [0] * 48, [0, 0, 1, 60, 60] + [0] * 47):
    try:
        U.mix_rows(bad)
        ok(False, "a malformed SMP_MIX reply is an error")
    except ValueError:
        ok(True, "a malformed SMP_MIX reply is an error")

dev = FakeLink()
rc, out, err = cli(["mix", "1"], dev)
ok(rc == 0 and dev.sent == [(81, [0])] and out.splitlines()[0].split() == "USR1 sound 1 C4-C4 LEVEL 100 % REV +0 % DLY +0 %".split()
   and len(out.splitlines()) == 3, "mix 1: lists the slot's sounds")
rc, out, err = cli(["mix", "1", "2", "50", "20"], dev)
want = [127, U.raw(50), 127] + [127] * 13 + [0, U.raw(20)] + [0] * 14 + [0] * 16
ok(rc == 0 and dev.sent[-1] == (81, [0] + want) and "LEVEL 50 %  REV +20 %  DLY +0 %" in out.splitlines()[1],
   "mix 1 2 50 20: sound 2's LEVEL and REV set, its DLY and the others kept")
rc, out, err = cli(["mix", "1", "3", "100", "0", "75"], dev)
ok(rc == 0 and dev.mix[2] == 127 and dev.mix[32 + 2] == U.raw(75) and dev.mix[1] == U.raw(50), "mix 1 3 100 0 75: DLY too")
n = len(dev.sent)
for args in (["mix", "1", "4", "50"], ["mix", "1", "2", "101"], ["mix", "1", "0", "50"], ["mix", "1", "2"], ["mix", "1", "x", "5"]):
    rc, out, err = cli(args, dev)
    ok(rc != 0 and len(dev.sent) - n <= 1 and all(c[1] == [0] for c in dev.sent[n:]), f"{' '.join(args)}: refused, nothing set")
    n = len(dev.sent)
rc, out, err = cli(["mix", "1", "1", "80"], FakeLink(rc=2))
ok(rc == 0 and "until the power goes" in out, "rc 2: said that the values stay until the power goes")
rc, out, err = cli(["mix", "1", "1", "80"], FakeLink(rc=1))
ok(rc != 0 and "refused" in err, "rc 1: refused")

print("SAMPLE UPLOAD TEST FAILED" if failed else "sample upload test passed")
sys.exit(1 if failed else 0)
