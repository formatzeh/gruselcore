#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# GruselCore's update path is pinned: the update loader is the one thing that must never break,
# because it is what lets the FM-1 install the next firmware (any firmware, or M-VAVE's own).
#
# The loader is X0X's (Felucca's) unchanged. This check preprocesses the loader's whole translation
# unit (loader.c and everything it includes: usb.c in its FELUCCA_LOADER form, ota.c, libc.c, the HAL
# headers) against a fixed stdint stand-in, and hashes it, together with its start-up code and linker
# script. Any change to what goes into the loader changes the hash, and this test fails.
#
# If a change to the loader is ever truly needed: test the update path on a real FM-1 (install from
# the Firmware Hub, install GruselCore over itself, interrupt an install and resume it, go back to the
# official V15), then update the two hashes below in the same commit, saying why.
set -eu
cd "$(dirname "$0")/.."
CC="${CC:-cc}"
TU_PIN=f140d66659b1756f1fdc5672f183b84ab7a21d45d48d95b7a98a01f939a44fc5   # X0X @ ca2d377
ASM_PIN=a651fd1b3b70a6d65f722688da4d9b8936e82f4aebf0f91bf436e87e73085996  # X0X @ ca2d377
tu=$($CC -E -P -nostdinc -Itests/loader_stub -Ifirmware/hal -Ifirmware/src firmware/loader/loader.c \
     | tr -s ' \n' | sha256sum | cut -d' ' -f1)
asm=$(cat firmware/loader/crt0_ldr.S firmware/loader/loader.ld | sha256sum | cut -d' ' -f1)
ok=1
if [ "$tu" != "$TU_PIN" ]; then
    echo "the update loader's sources changed (preprocessed hash $tu, pinned $TU_PIN)"
    echo "something loader.c includes was edited: usb.c (its FELUCCA_LOADER parts), ota.c, libc.c or a HAL header"
    ok=0
fi
if [ "$asm" != "$ASM_PIN" ]; then
    echo "the update loader's start-up code or linker script changed ($asm, pinned $ASM_PIN)"
    ok=0
fi
[ $ok = 1 ] && echo "update loader: unchanged (X0X / Felucca's)"
[ $ok = 1 ]
