#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# GruselCore's update path is pinned: the update loader is the one thing that must never break, because it is
# what lets the FM-1 install the next firmware (any firmware, or M-VAVE's own). (Kept from GruselCore 0.1.)
#
# The loader is Skiff 2.1.1's (Felucca's, with Skiff's screen) unchanged. This check preprocesses the loader's
# whole translation unit (loader.c and everything it includes: ldr_core.c, ldr_screen.c, usb.c in its loader form,
# lcd.c, libc.c, the HAL headers) for the FM-1 and the SMK-37 against a fixed stdint stand-in and identity, and
# hashes it, with its start-up code and linker script. Any change to what goes into the loader fails this test.
#
# If a change to the loader is ever truly needed: test the update path on a real FM-1 (install from the Firmware
# Hub, install GruselCore over itself, interrupt an install and resume it, go back to the official firmware), then
# update the hashes below in the same commit, saying why.
set -eu
cd "$(dirname "$0")/.."
CC="${CC:-cc}"
PIN_FM1=8e0fbc48f69568d554b468a7d11f6a9b60a9514a3707096807e68a08f8a1a71a   # Skiff 2.1.1 (48e77fd)
PIN_SMK=9580a765728cf7c4861ef386d6234f086506187edb2a263115cde29c2bd56ffa   # Skiff 2.1.1 (48e77fd)
PIN_ASM=a651fd1b3b70a6d65f722688da4d9b8936e82f4aebf0f91bf436e87e73085996   # Skiff 2.1.1 (48e77fd)
tu() {
    $CC -E -P -nostdinc -Itests/loader_stub -Ifirmware/hal -Ifirmware/src -DBOARD_SMK37=$1 -DFELUCCA_ID='"ota-PIN"' \
        firmware/loader/loader.c | tr -s ' \n' | sha256sum | cut -d' ' -f1
}
ok=1
for b in 0 1; do
    h=$(tu $b)
    want=$PIN_FM1
    [ $b = 1 ] && want=$PIN_SMK
    if [ "$h" != "$want" ]; then
        echo "the update loader's sources changed (BOARD_SMK37=$b: $h, pinned $want)"
        echo "something loader.c includes was edited: ldr_*.c, usb.c / lcd.c (their loader parts), libc.c or a HAL header"
        ok=0
    fi
done
asm=$(cat firmware/loader/crt0_ldr.S firmware/loader/loader.ld | sha256sum | cut -d' ' -f1)
if [ "$asm" != "$PIN_ASM" ]; then
    echo "the update loader's start-up code or linker script changed ($asm, pinned $PIN_ASM)"
    ok=0
fi
[ $ok = 1 ] && echo "update loader: unchanged (Skiff 2.1.1's)"
[ $ok = 1 ]
