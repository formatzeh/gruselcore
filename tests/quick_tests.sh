#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# (GruselCore) The quick suite for development builds (a few minutes on GitHub): what keeps an FM-1 safe to update
# and to start, and what GruselCore changes. The whole suite (tests/run_tests.sh, ~13 minutes there) runs for every
# release tag and when the workflow is started by hand with "full tests" ticked.
#   sh tests/quick_tests.sh      (after ./build.sh: needs build/felucca.fwsc, build/felucca.dis, build/gen)
set -u
cd "$(dirname "$0")/.."
OUT=build/host
mkdir -p "$OUT"
CC="${CC:-cc} -O1 -Wall -Wno-unused-function"
fail=0
run() { echo "== $1"; shift; "$@" || { echo "QUICK TEST FAILED: $*"; fail=1; }; }

[ -f build/felucca.fwsc ] && [ -f build/gen/felucca_tables.h ] || { echo "run ./build.sh first"; exit 1; }

# the way back: the loader unchanged, the update entry, the loader writing a package, its screen
run "update loader: Skiff 2.1.1's, unchanged" sh tests/loader_guard.sh
$CC -DOWN_PKG=1 -o "$OUT/ota_test" tests/ota_test.c
run "M-UPGRADE entry (own loader)" "$OUT/ota_test" build/felucca.fwsc
head -c 200000 build/felucca.bin > "$OUT/old_app.bin"
python3 tools/fm1pkg_make.py "$OUT/old_app.bin" build/loader/ota.bin "$OUT/old.fwsc" >/dev/null
$CC -o "$OUT/ldr_test" tests/ldr_test.c
run "update loader: other app -> this build" "$OUT/ldr_test" "$OUT/old.fwsc" build/felucca.fwsc
$CC -o "$OUT/ldr_screen_test" tests/ldr_screen_test.c
run "update loader's screen: UPDATE MODE, WRITING, UPDATE FAILED" "$OUT/ldr_screen_test"
run "installer CLI (fm1_install.py) against a simulated FM-1" python3 tests/install_test.py

# what is stored: flash A/B and torn writes, persistence (no restore after a crash), the pattern bank
$CC -o "$OUT/storage_test" tests/storage_test.c
run "flash storage (A/B, torn writes)" "$OUT/storage_test"
$CC -w -Ibuild/gen -Ifirmware/src -o "$OUT/persistence_test" tests/persistence_test.c -lm
run "persistence: deferred settings, retry, failed-save rollback, no restore after a crash" "$OUT/persistence_test"
$CC -w -Ibuild/gen -Ifirmware/src -o "$OUT/bank_test" tests/bank_test.c -lm
run "pattern bank: patterns kept exactly, torn saves, fallback" "$OUT/bank_test"

# the device itself: keys, the UI, the sounds (golden renders, GruselCore's drums), the editor protocol, the cost
$CC -o "$OUT/input_test" tests/input_test.c
run "keys and buttons" "$OUT/input_test"
$CC -w -Ibuild/gen -Ifirmware/src -o "$OUT/ui_test" tests/ui_test.c -lm
run "UI: sounds, steps, undo, recording, drum grid" "$OUT/ui_test"
$CC -O2 -w -Ibuild/gen -Ifirmware/src -o "$OUT/drum_test" tests/drum_test.c -lm
run "DRUM (GruselCore kits): every kit and lane sounds, ends, no clipping, level; choke, controls" "$OUT/drum_test"
$CC -O2 -w -Ibuild/gen -Ifirmware/src -o "$OUT/regress" tests/regress.c -lm
run "regression: golden renders, health, voices" "$OUT/regress" tests/golden.txt tests/cpu_baseline.txt
$CC -w -Ibuild/gen -Ifirmware/src -o "$OUT/editor_test" tests/editor_test.c -lm
run "editor protocol" env MENU_JSON="$OUT/menu.json" "$OUT/editor_test"
run "target cost of the render loops (pi32v2 disassembly)" python3 tests/target_budget.py \
    build/felucca.dis tests/target_budget.txt

if [ "$fail" != 0 ]; then echo "QUICK TESTS FAILED"; exit 1; fi
echo "quick tests passed (the full suite: tests/run_tests.sh)"
