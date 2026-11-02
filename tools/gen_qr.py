#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The ABOUT screen's QR code (firmware/src/ui_menu.c ABOUT_QR): a URL as a QR code, version 3 (29 x 29), error
correction M, byte mode, the mask the standard's penalty picks; printed as the C table, one row a word, the leftmost
module in bit 0.

  gen_qr.py URL            -> the table
  gen_qr.py --check        -> the encoder against the table Felucca shipped (made by CoreImage) for its URL

ponytail: one version, one level, byte mode only (what the screen needs); the general algorithm is the standard's
(ISO/IEC 18004), written after Project Nayuki's QR Code generator (MIT)."""
import sys

SIZE, DATA_CW, EC_CW = 29, 44, 26                    # version 3-M: one block, 44 data + 26 EC codewords
FELUCCA = ("https://hugelton.github.io/Felucca", [
    0x1FCD247F, 0x1059C541, 0x1745765D, 0x1758E85D, 0x174E575D, 0x104C3A41, 0x1FD5557F, 0x000B7000, 0x091BCA55,
    0x1270DC8A, 0x1DB4375A, 0x083E9FA1, 0x1A63124E, 0x12513981, 0x1AE2524D, 0x0A2E78A0, 0x1A7F4FC3, 0x167154B0,
    0x19A228D5, 0x0A561C2A, 0x01F10B4D, 0x1D1B3F00, 0x1B5A467F, 0x1B13F641, 0x11F24D5D, 0x1D1B625D, 0x1389315D,
    0x08DFD641, 0x1813977F])


def gf_mul(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def rs_ec(data, n):
    div = [0] * (n - 1) + [1]                        # the generator polynomial, highest term first (implicit 1)
    root = 1
    for _ in range(n):
        for j in range(n):
            div[j] = gf_mul(div[j], root)
            if j + 1 < n:
                div[j] ^= div[j + 1]
        root = gf_mul(root, 0x02)
    rem = [0] * n
    for b in data:
        f = b ^ rem.pop(0)
        rem.append(0)
        for i, c in enumerate(div):
            rem[i] ^= gf_mul(c, f)
    return rem


def codewords(text):
    b = text.encode("ascii")
    bits = [0, 1, 0, 0] + [(len(b) >> i) & 1 for i in reversed(range(8))]
    for x in b:
        bits += [(x >> i) & 1 for i in reversed(range(8))]
    if len(bits) > DATA_CW * 8:
        raise SystemExit(f"too long for version 3-M: {len(b)} bytes (at most 42)")
    bits += [0] * min(4, DATA_CW * 8 - len(bits))
    bits += [0] * (-len(bits) % 8)
    cw = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    cw += [0xEC, 0x11] * ((DATA_CW - len(cw)) // 2 + 1)
    cw = cw[:DATA_CW]
    return cw + rs_ec(cw, EC_CW)


def base():
    m = [[0] * SIZE for _ in range(SIZE)]
    fn = [[False] * SIZE for _ in range(SIZE)]

    def put(x, y, v):
        m[y][x] = int(v)
        fn[y][x] = True
    for i in range(SIZE):                            # timing
        put(6, i, i % 2 == 0)
        put(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (SIZE - 4, 3), (3, SIZE - 4)):   # finders and their separators
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < SIZE and 0 <= y < SIZE:
                    put(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    for dy in range(-2, 3):                          # the one alignment pattern (22, 22)
        for dx in range(-2, 3):
            put(22 + dx, 22 + dy, max(abs(dx), abs(dy)) != 1)
    format_bits(put, 0)                              # (reserved; drawn again with the mask)
    return m, fn


def format_bits(put, mask):
    data = 0 << 3 | mask                             # M = 00
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    bits = (data << 10 | rem) ^ 0x5412
    bit = lambda i: (bits >> i) & 1
    for i in range(6):
        put(8, i, bit(i))
    put(8, 7, bit(6))
    put(8, 8, bit(7))
    put(7, 8, bit(8))
    for i in range(9, 15):
        put(14 - i, 8, bit(i))
    for i in range(8):
        put(SIZE - 1 - i, 8, bit(i))
    for i in range(8, 15):
        put(8, SIZE - 15 + i, bit(i))
    put(8, SIZE - 8, 1)                              # the dark module


MASKS = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
         lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
         lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
         lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]


def penalty(m):
    s = 0
    lines = m + [list(c) for c in zip(*m)]
    for row in lines:                                # runs of 5+, and the finder-like 1:1:3:1:1 with 4 light
        run, prev = 0, None
        for v in row + [None]:
            if v == prev:
                run += 1
            else:
                if prev is not None and run >= 5:
                    s += 3 + run - 5
                run, prev = 1, v
        r = "".join(map(str, row))
        for pat in ("10111010000", "00001011101"):
            s += 40 * sum(1 for i in range(len(r) - 10) if r[i:i + 11] == pat)
    for y in range(SIZE - 1):                        # 2 x 2 blocks
        for x in range(SIZE - 1):
            if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                s += 3
    dark = sum(map(sum, m))
    k = (abs(dark * 20 - SIZE * SIZE * 10) + SIZE * SIZE - 1) // (SIZE * SIZE) - 1
    return s + 10 * max(k, 0)


def encode(text, mask=None):
    cw = codewords(text)
    m, fn = base()
    bits = [(c >> (7 - i)) & 1 for c in cw for i in range(8)]
    i = 0
    right = SIZE - 1
    while right >= 1:                                # the zig-zag, two columns at a time, past the timing column
        if right == 6:
            right = 5
        for vert in range(SIZE):
            for j in range(2):
                x = right - j
                y = SIZE - 1 - vert if ((right + 1) & 2) == 0 else vert
                if not fn[y][x] and i < len(bits):
                    m[y][x] = bits[i]
                    i += 1
        right -= 2
    best = None
    for k in ([mask] if mask is not None else range(8)):
        t = [row[:] for row in m]
        for y in range(SIZE):
            for x in range(SIZE):
                if not fn[y][x] and MASKS[k](x, y):
                    t[y][x] ^= 1

        def put(x, y, v, t=t):
            t[y][x] = int(v)
        format_bits(put, k)
        p = penalty(t)
        if best is None or p < best[0]:
            best = (p, k, t)
    return best[1], best[2]


def words(m):
    return [sum(v << x for x, v in enumerate(row)) for row in m]


def table(url):
    k, m = encode(url)
    w = words(m)
    out = [f"/* {url}, QR version 3, correction M, mask {k} (tools/gen_qr.py).",
           " * One row per word, leftmost module in bit 0; the constant matrix needs no encoder or RAM. */",
           "static const uint32_t ABOUT_QR[29] = {"]
    for i in range(0, 29, 6):
        out.append("    " + " ".join(f"0x{v:08X}u," for v in w[i:i + 6]))
    out.append("};")
    return "\n".join(out)


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        url, want = FELUCCA
        hits = [k for k in range(8) if words(encode(url, k)[1]) == want]
        chosen = encode(url)[0]
        print(f"Felucca's table == mask {hits} ; the penalty picks mask {chosen}")
        sys.exit(0 if hits else 1)
    print(table(sys.argv[1]))
