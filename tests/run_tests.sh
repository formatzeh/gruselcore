#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# GruselCore host tests: the update loader pinned, the maths, the drum engine, the sequencer, the
# engine, the 303 against its reference (needs SCHWUNG303, see tests/host/run_bass303.sh), storage,
# backup, the update path (with build/x0x.fwsc), and the whole app in the simulator
# (tests/gc/*.gc: UI, patterns, saving), with screenshots in build/gc/.
#   tests/run_tests.sh
set -u
cd "$(dirname "$0")/.."
CC="${CC:-cc}"
FAIL=0
OUT=build/host
mkdir -p "$OUT" build/scenarios
run() {
    name="$1"; shift
    if "$@" > "$OUT/$name.log" 2>&1; then
        echo "  ok   $name"
    else
        echo "  FAIL $name (see $OUT/$name.log)"
        tail -15 "$OUT/$name.log" | sed 's/^/       /'
        FAIL=1
    fi
}
W="-O2 -ffp-contract=off -Wall -Wextra -Wdouble-promotion -Werror"
run loader-guard sh tests/loader_guard.sh   # the update loader must stay X0X's / Felucca's (the way to any other firmware)
run fastmath sh -c "$CC -O2 -ffp-contract=off -Wall -Wextra -Werror -o $OUT/fastmath_test tests/host/fastmath_test.c -lm && $OUT/fastmath_test"
run gdrum sh -c "$CC $W -Wno-double-promotion -Ifirmware/src/dsp -o $OUT/gdrum_test tests/host/gdrum_test.c firmware/src/dsp/gdrum.c firmware/src/dsp/gdrum_kits.c firmware/src/dsp/bass303.c -lm && mkdir -p build/gdrum && $OUT/gdrum_test build/gdrum"
run gdrum-groove sh -c "$CC $W -o $OUT/gdrum_groove tests/host/gdrum_groove.c firmware/src/dsp/gdrum.c firmware/src/dsp/gdrum_kits.c -lm && $OUT/gdrum_groove build/gdrum"
run gva sh -c "$CC $W -std=c99 -D_DEFAULT_SOURCE -Wno-double-promotion -Ifirmware/src/dsp -o $OUT/gva_test tests/host/gva_test.c firmware/src/dsp/gva.c firmware/src/dsp/gva_presets.c -lm && mkdir -p build/gva && $OUT/gva_test build/gva"
run gseq sh -c "$CC $W -o $OUT/gseq_test tests/host/gseq_test.c firmware/src/seq/gseq.c firmware/src/seq/gpat.c && $OUT/gseq_test"
run encoder sh -c "$CC -O2 -w -Ifirmware/hal -o $OUT/encoder_test tests/host/encoder_test.c && $OUT/encoder_test"
run uac sh -c "$CC -O2 -w -Ifirmware/src -Ifirmware/hal -o $OUT/uac_test tests/host/uac_test.c -lm && $OUT/uac_test"
run trs sh -c "$CC -O2 -w -Ifirmware/src -Ifirmware/hal -o $OUT/trs_test tests/host/trs_test.c && $OUT/trs_test"
run lz sh -c "$CC $W -o $OUT/lz_test tests/host/lz_test.c && $OUT/lz_test"
# the tables the DSP below includes (build/gen, as the build makes them): a fresh checkout has none yet
[ -f build/gen/x0x_drum_tables.h ] || { mkdir -p build/gen && python3 tools/gen_drum_samples.py build/gen/x0x_drum_samples.h >/dev/null; }
[ -f build/gen/felucca_font.h ] || python3 tools/gen_font.py build/gen/felucca_font.h >/dev/null
run stereo sh -c "$CC -O2 -ffp-contract=off -w -Ifirmware/src/dsp -Ifirmware/src -Ibuild/gen -o $OUT/stereo_test tests/host/stereo_test.c firmware/src/dsp/master.c firmware/src/dsp/fxbus.c -lm && $OUT/stereo_test"
run reverb sh -c "$CC $W -Wno-double-promotion -Ifirmware/src/dsp -Ifirmware/src -Ibuild/gen -o $OUT/reverb_test tests/host/reverb_test.c -lm && $OUT/reverb_test"
run master sh -c "$CC $W -Wno-double-promotion -o $OUT/master_test tests/host/master_test.c firmware/src/dsp/master.c -lm && $OUT/master_test"
[ -f tests/host/run_bass303.sh ] && run bass303 sh tests/host/run_bass303.sh
ENG="firmware/src/app/gengine.c firmware/src/seq/gseq.c firmware/src/seq/gpat.c firmware/src/dsp/gdrum.c \
    firmware/src/dsp/gdrum_kits.c firmware/src/dsp/bass303.c firmware/src/dsp/fxbus.c firmware/src/dsp/master.c \
    firmware/src/dsp/x0x_tables.c firmware/src/dsp/gva.c firmware/src/dsp/gva_presets.c"
run gengine sh -c "$CC -O2 -ffp-contract=off -std=c99 -D_DEFAULT_SOURCE -Wall -Wextra -Wno-unused-function -DX0X_HOST \
    -Ifirmware/src -Ifirmware/src/dsp -Ibuild/gen -o $OUT/gengine_test tests/host/gengine_test.c $ENG -lm && \
    mkdir -p build/gengine && $OUT/gengine_test build/gengine"
run storage sh -c "$CC -O2 -o $OUT/storage_test tests/storage_test.c && $OUT/storage_test"
# backup and restore over USB (firmware/src/backup.c) on storage.c over a simulated flash: the stream's frames, a
# restore refused, cut or damaged changing nothing, SEL restoring it all, a power cut at each write: the old project
# or the new, whole. Then tools/x0x_backup.py against a simulated X0X, on that image
run backup sh -c "$CC -std=c99 -Wall -Wextra -Werror -Wno-unused-function -O2 -o $OUT/backup_test tests/backup_test.c && $OUT/backup_test $OUT/backup.x0b"
run x0x-backup python3 tests/x0x_backup_test.py $OUT/backup.x0b
# the web backup page (web/backup/index.html): the same bytes as x0x_backup.py's on that conversation, replayed;
# then a simulated X0X: a backup and a restore byte for byte, STOP FIRST, HOME, a damaged or another firmware's file
# not sent
if command -v node >/dev/null 2>&1; then
    run backup-page sh -c "python3 tests/x0x_backup_record.py $OUT/backup.x0b $OUT/backup_transcript.json && \
        node tests/host/backup_page_test.mjs $OUT/backup_transcript.json"
fi
# the update path, against the firmware package (Felucca's tests; needs ./build.sh)
if [ -f build/x0x.fwsc ]; then
    run ota-entry sh -c "$CC -o $OUT/ota_test tests/ota_test.c && $OUT/ota_test build/x0x.fwsc"
    if [ -z "${AC79_SDK:-}" ]; then
        echo "  skip update-loader (needs AC79_SDK, as the build)"
    else
    run update-loader sh -c "head -c 200000 build/x0x.bin > $OUT/old_app.bin && \
        python3 tools/fm1pkg_make.py $OUT/old_app.bin build/loader/ota.bin $OUT/old.fwsc >/dev/null && \
        $CC -o $OUT/ldr_test tests/ldr_test.c && $OUT/ldr_test $OUT/old.fwsc build/x0x.fwsc"
    fi
    run installer python3 tests/install_test.py
else
    echo "  skip update-path tests (no build/x0x.fwsc: run ./build.sh)"
fi
run host-build sh -c "$CC -O1 -ffp-contract=off -std=c99 -D_DEFAULT_SOURCE -Wall -Wno-unused-function -Wno-unused-parameter \
    -DX0X_HOST -Ifirmware/src -Ifirmware/src/app -Ifirmware/src/dsp -Ibuild/gen -o $OUT/gc_host host/gc_host.c $ENG -lm"
for s in tests/gc/*.gc; do
    n=$(basename "$s" .gc)
    mkdir -p "build/gc/$n"
    run "scenario-$n" $OUT/gc_host "$s" "build/gc/$n"
done
[ $FAIL -eq 0 ] && echo "all tests passed" || echo "TESTS FAILED"
exit $FAIL
