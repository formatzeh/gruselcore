/* SPDX-License-Identifier: GPL-3.0-only */
/* (GruselCore) The DRUM engine's lanes, one hit each, through the whole mix (no sends), as loud as the ear hears
 * them: K-weighted (BS.1770), the loudest 100 ms (tests/gc_loudness.h).
 *   build/host/gc_drum_level [PRESET..]   every DRUM preset by default; prints "PRESET LANE dB peak" */
#define main hostsim_main
#include "hostsim.c"
#undef main
#include "gc_loudness.h"

static const uint8_t LANE_NOTE[8] = {36, 38, 39, 42, 46, 45, 37, 56};

static double hit(uint32_t preset, uint32_t lane, int32_t *peak)
{
    static float l[FS], r[FS];
    uint32_t f, i;
    host_tracks_init();
    host_preset(&trk[3], ENGI_DRUM, preset);
    trk[3].p[P_CHOR] = trk[3].p[P_DLY] = trk[3].p[P_REV] = 0;
    trk_note_on(&trk[3], LANE_NOTE[lane], 100);
    *peak = 0;
    for (f = 0; f + CTL <= FS; f += CTL) {
        int32_t o[2 * CTL];
        if (f == FS / 4u)
            trk_note_off(&trk[3], LANE_NOTE[lane]);
        mix_block(o, CTL);
        for (i = 0; i < CTL; i++) {
            l[f + i] = (float)o[2 * i] / 32768.0f;
            r[f + i] = (float)o[2 * i + 1] / 32768.0f;
            if (abs(o[2 * i]) > *peak) *peak = abs(o[2 * i]);
        }
    }
    return loudness_db(l, r, FS);
}

int main(int argc, char **argv)
{
    uint32_t p, k, n = ENGINES[ENGI_DRUM]->npresets;
    for (p = 0; p < n; p++) {
        if (argc > 1 && (uint32_t)atoi(argv[1]) != p)
            continue;
        for (k = 0; k < 8u; k++) {
            int32_t pk;
            double db = hit(p, k, &pk);
            printf("%-14s %u %6.1f %6d\n", ENGINES[ENGI_DRUM]->presets[p].name, k, db, pk);
        }
    }
    return 0;
}
