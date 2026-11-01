/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore VA presets. Pot order (gva.h):
 *   WAVE1 WAVE2 TUNE2 DETUNE | MIX SUB NOISE PW | CUTOFF RESO ENV FILTER | F.ATT F.DEC F.SUS KEYTRK |
 *   ATTACK DECAY SUSTN RELEAS | MODE GLIDE ACCENT VOLUME | LFO SHAPE L>PTCH L>CUT
 * TUNE2: 24 = unison with osc 1, 12 = an octave down, 36 = up. VOLUME: each preset at -16 dB (as the
 * drum kits; tests/host/gva_test.c measures it). */
#include "gva.h"

#define S VAW_SAW
#define Q VAW_SQR
#define T VAW_TRI
#define N VAW_SINE
#define MO VAM_MONO
#define CH VAM_CHORD
#define UN VAM_UNISON

const gva_preset_t gva_presets[] = {
    {"ROLLING BASS", {S, Q, 24, 8,   40, 60, 0, 64,   38, 45, 70, VAF_LP24,  0, 38, 0, 40,    0, 45, 0, 12,
                      MO, 0, 80, 114,   7, VAL_TRI, 0, 0}},
    {"OFFBEAT BASS", {S, S, 12, 20,  50, 40, 0, 64,   50, 30, 60, VAF_LP24,  0, 48, 10, 40,   0, 55, 30, 25,
                      MO, 0, 64, 113,   7, VAL_TRI, 0, 0}},
    {"TRANCE LEAD",  {S, S, 24, 55,  50, 0, 0, 64,    95, 20, 25, VAF_LP12,  0, 60, 40, 64,   2, 70, 90, 55,
                      UN, 0, 40, 95,   9, VAL_TRI, 0, 0}},
    {"SUPERSAW PAD", {S, S, 36, 70,  40, 0, 0, 64,    70, 15, 20, VAF_LP12,  60, 90, 60, 40,  70, 90, 100, 85,
                      UN, 0, 0, 83,    2, VAL_TRI, 0, 20}},
    {"PSY PLUCK",    {S, Q, 24, 15,  50, 0, 0, 40,    45, 55, 85, VAF_LP24,  0, 35, 0, 64,    0, 42, 0, 30,
                      CH, 0, 70, 127,   7, VAL_TRI, 0, 0}},
    {"DARK STAB",    {S, Q, 24, 20,  50, 30, 0, 64,   40, 70, 65, VAF_LP24,  0, 50, 0, 50,    0, 52, 0, 35,
                      CH, 0, 64, 115,   7, VAL_TRI, 0, 0}},
    {"FOREST ZAP",   {S, Q, 36, 0,   40, 0, 0, 30,    70, 75, 60, VAF_LP12,  0, 30, 0, 64,    0, 40, 0, 20,
                      MO, 20, 64, 119,  9, VAL_SH, 90, 30}},
    {"DARK DRONE",   {S, Q, 23, 30,  50, 50, 15, 64,  35, 60, 20, VAF_LP24,  80, 100, 50, 30, 90, 100, 110, 85,
                      MO, 60, 0, 89,   1, VAL_TRI, 0, 50}},
    {"HOOVER",       {S, Q, 12, 90,  60, 40, 0, 90,   85, 30, 30, VAF_LP12,  0, 70, 60, 30,   5, 80, 100, 40,
                      UN, 50, 40, 82,  5, VAL_TRI, 10, 0}},
    {"MENTAL ACID",  {Q, S, 24, 5,   30, 0, 0, 40,    30, 105, 75, VAF_LP24, 0, 40, 0, 50,    0, 55, 60, 15,
                      MO, 25, 100, 86, 7, VAL_TRI, 0, 0}},
    {"PSYCHILL KEY", {T, N, 36, 10,  40, 0, 0, 64,    75, 20, 30, VAF_LP12,  0, 65, 30, 64,   3, 75, 50, 60,
                      CH, 0, 30, 93,   4, VAL_TRI, 3, 0}},
    {"SUB BASS",     {N, T, 24, 0,   20, 30, 0, 64,   60, 0, 10, VAF_LP24,   0, 50, 0, 30,    0, 70, 90, 20,
                      MO, 0, 30, 90,   7, VAL_TRI, 0, 0}},
};
const int gva_npresets = (int)(sizeof gva_presets / sizeof gva_presets[0]);
