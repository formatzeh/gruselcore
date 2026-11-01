/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore factory drum kits: 8 sounds x 16 pots each (gdrum.h GP_* order).
 *
 * Scales, to read the numbers (gdrum.c voice_calc):
 *   TUNE   note 12 + 0.75 pot      (24 = 41 Hz, 26 = 50 Hz, 58 = 190 Hz, 80 = 600 Hz)
 *   PITCH  0.57 semitones a step   (85 = 48 semitones = 4 octaves)
 *   P.DEC  0.3 ms * 2^(pot / 16.6) (50 = 2.6 ms, 60 = 3.6 ms, 75 = 6.4 ms)
 *   BODY   0.19 semitones a step   (64 = an octave), over 8 x P.DEC (20..300 ms)
 *   DECAY  5 ms * 2^(pot / 13.8)   (60 = 100 ms, 80 = 280 ms, 90 = 460 ms, 100 = 770 ms)
 *   TONE   100 Hz * 2^(pot / 17.4) (80 = 2.4 kHz, 100 = 5.4 kHz, 115 = 10 kHz)
 *   DRIVE  gain 2^(pot / 21.5)     (60 = 7, 80 = 13, 100 = 25)
 *   PUNCH  hold 0..50 ms           (50 = 20 ms)
 * LEVEL: every sound normalised to one loudness (-16 dB, K-weighted, the loudest 100 ms of a hit at
 * velocity 0.75; tests/host/gdrum_test.c checks it), short hits allowed peaks to 1.5.
 * Order: MODEL LEVEL TUNE PITCH P.DEC BODY DECAY TAIL CLICK TONE NOISE DRIVE CURVE PUNCH ATTACK PAN */
#include "gdrum.h"

#define K GDM_KICK
#define S GDM_SNARE
#define C GDM_CLAP
#define H GDM_HAT
#define T GDM_TOM
#define R GDM_RIM
#define M GDM_METAL
#define Z GDM_ZAP
#define SOFT GDC_SOFT
#define HARD GDC_HARD
#define FOLD GDC_FOLD
#define TUBE GDC_TUBE
#define CRSH GDC_CRUSH

const gd_kit_t gd_kits[] = {
    {{ /* HARDTEK: a hard, distorted kick with a long tail */
        {K,  61, 25, 90, 50, 70, 88, 50, 70,  95,   0,  95, HARD, 60, 0, 64},
        {S,  78, 58, 30, 60, 10, 55,  0, 50,  95,  80,  60, SOFT, 10, 0, 64},
        {C,  78, 60,  0,  0,  0, 58,  0, 20,  88, 127,  40, SOFT,  0, 0, 64},
        {H,  78, 80,  0,  0,  0, 37,  0, 10, 115,  50,  30, HARD,  0, 0, 70},
        {H,  58, 80,  0,  0,  0, 62,  0, 10, 112,  50,  30, HARD,  0, 0, 58},
        {T,  75, 40, 30, 70, 20, 66,  0, 30,  70,   5,  50, SOFT, 15, 0, 54},
        {R,  90, 76, 10, 30,  0, 28,  0, 40, 100,  10,  40, HARD,  0, 0, 74},
        {M,  64, 70, 20, 40,  0, 50,  0, 20, 100,  20,  60, FOLD,  0, 0, 80},
    }},
    {{ /* TRIBETEK: rounder kick with rumble, tribal toms */
        {K,  68, 27, 80, 55, 60, 92, 70, 50,  85,   0,  80, TUBE, 50, 0, 64},
        {S,  84, 56, 25, 60, 10, 58,  0, 40,  90,  75,  50, SOFT, 10, 0, 64},
        {C,  82, 58,  0,  0,  0, 62,  0, 15,  85, 127,  35, SOFT,  0, 0, 64},
        {H,  90, 78,  0,  0,  0, 32,  0,  8, 112,  55,  25, SOFT,  0, 0, 72},
        {H,  59, 78,  0,  0,  0, 66,  0,  8, 110,  55,  25, SOFT,  0, 0, 56},
        {T,  85, 36, 40, 70, 25, 72,  0, 35,  65,   5,  40, TUBE, 20, 0, 48},
        {R,  93, 72, 12, 30,  0, 30,  0, 35,  95,  10,  35, HARD,  0, 0, 76},
        {T,  93, 52, 35, 60, 15, 60,  0, 40,  80,  10,  45, TUBE, 10, 0, 82},
    }},
    {{ /* MENTALTEK: folded, harsh, fast */
        {K,  64, 26, 95, 45, 75, 80, 40, 80, 105,   0,  62, FOLD, 55, 0, 64},
        {S,  71, 60, 40, 50, 15, 50,  0, 60, 100,  85,  80, HARD,  5, 0, 64},
        {C,  60, 62,  0,  0,  0, 52,  0, 25,  95, 127,  70, HARD,  0, 0, 64},
        {H,  66, 84,  0,  0,  0, 26,  0, 15, 118,  40,  70, CRSH,  0, 0, 68},
        {H,  47, 84,  0,  0,  0, 56,  0, 15, 116,  40,  60, CRSH,  0, 0, 60},
        {T,  73, 44, 50, 55, 20, 58,  0, 40,  80,  10,  80, FOLD, 10, 0, 52},
        {R,  77, 80, 15, 25,  0, 24,  0, 50, 105,  15,  70, CRSH,  0, 0, 76},
        {Z,  79, 50, 110, 70, 30, 48, 0, 30, 100,  0,  70, HARD,  0, 0, 84},
    }},
    {{ /* TECHNO: solid, slightly driven */
        {K,  67, 26, 70, 60, 40, 84, 30, 40,  80,   0,  55, SOFT, 35, 0, 64},
        {S,  93, 57, 25, 60,  8, 56,  0, 40,  92,  75,  40, SOFT, 10, 0, 64},
        {C,  84, 60,  0,  0,  0, 64,  0, 15,  86, 127,  30, SOFT,  0, 0, 64},
        {H,  96, 80,  0,  0,  0, 34,  0, 10, 114,  50,  20, SOFT,  0, 0, 70},
        {H,  64, 80,  0,  0,  0, 68,  0, 10, 112,  50,  20, SOFT,  0, 0, 58},
        {T,  80, 40, 30, 70, 20, 66,  0, 30,  70,   5,  40, SOFT, 15, 0, 54},
        {R,  98, 76, 10, 30,  0, 28,  0, 40, 100,  10,  30, HARD,  0, 0, 74},
        {M, 106, 66, 10, 40,  0, 46,  0, 15,  95,  10,  40, SOFT,  0, 0, 80},
    }},
    {{ /* DARK TECHNO: deep kick, long rumble, darker tops */
        {K,  72, 22, 75, 62, 45, 95, 80, 35,  70,   0,  75, TUBE, 40, 0, 64},
        {S,  93, 54, 25, 65, 10, 60,  0, 30,  75,  75,  55, TUBE, 10, 0, 64},
        {C,  84, 56,  0,  0,  0, 66,  0, 10,  78, 127,  45, TUBE,  0, 0, 64},
        {H,  88, 76,  0,  0,  0, 30,  0,  8, 105,  55,  35, TUBE,  0, 0, 70},
        {H,  53, 76,  0,  0,  0, 70,  0,  8, 102,  55,  35, TUBE,  0, 0, 58},
        {T,  81, 34, 35, 75, 20, 72,  0, 25,  60,   5,  50, TUBE, 15, 0, 54},
        {R,  87, 70, 10, 30,  0, 30,  0, 30,  90,  10,  45, HARD,  0, 0, 74},
        {M,  58, 58, 15, 45,  0, 56,  0, 15,  85,  20,  60, FOLD,  0, 0, 80},
    }},
    {{ /* TRANCE: punchy, clean, a big clap and open hat */
        {K,  69, 28, 72, 58, 50, 80, 10, 55, 100,   0,  45, SOFT, 45, 0, 64},
        {S,  98, 58, 25, 60,  8, 58,  0, 40,  98,  75,  30, SOFT, 10, 0, 64},
        {C,  81, 60,  0,  0,  0, 70,  0, 20,  92, 127,  25, SOFT,  0, 0, 64},
        {H, 102, 82,  0,  0,  0, 37,  0, 10, 118,  50,  15, SOFT,  0, 0, 70},
        {H,  66, 82,  0,  0,  0, 74,  0, 10, 116,  50,  15, SOFT,  0, 0, 58},
        {T,  85, 42, 30, 70, 20, 66,  0, 30,  72,   5,  30, SOFT, 15, 0, 54},
        {R, 102, 78, 10, 30,  0, 28,  0, 40, 102,  10,  25, HARD,  0, 0, 74},
        {M, 127, 72, 10, 40,  0, 60,  0, 10, 108,  15,  20, SOFT,  0, 0, 80},
    }},
    {{ /* PSYTRANCE: short, tight kick that leaves room for the rolling bass */
        {K,  67, 30, 85, 50, 55, 66,  0, 75, 105,   0,  60, HARD, 55, 0, 64},
        {S,  86, 60, 35, 50, 10, 52,  0, 55, 102,  80,  45, HARD,  5, 0, 64},
        {C,  80, 62,  0,  0,  0, 56,  0, 25,  95, 127,  35, SOFT,  0, 0, 64},
        {H,  89, 84,  0,  0,  0, 36,  0, 15, 120,  45,  30, SOFT,  0, 0, 70},
        {H,  66, 84,  0,  0,  0, 58,  0, 15, 118,  45,  30, HARD,  0, 0, 58},
        {T,  86, 46, 40, 55, 20, 58,  0, 40,  85,   5,  40, SOFT, 10, 0, 54},
        {R,  91, 80, 12, 25,  0, 24,  0, 45, 108,  10,  40, HARD,  0, 0, 74},
        {Z,  87, 56, 100, 65, 25, 46, 0, 25, 105,  0,  50, HARD,  0, 0, 84},
    }},
    {{ /* DARKPSY / FOREST: very short clicky kick, noisy metal, zaps */
        {K,  69, 28, 85, 48, 50, 62,  0, 85, 110,   0,  70, HARD, 50, 0, 64},
        {S,  80, 62, 40, 45, 10, 48,  0, 60, 105,  85,  60, HARD,  5, 0, 64},
        {C,  65, 64,  0,  0,  0, 50,  0, 30, 100, 127,  55, HARD,  0, 0, 64},
        {H,  78, 88,  0,  0,  0, 22,  0, 20, 122,  60,  50, CRSH,  0, 0, 70},
        {H,  55, 88,  0,  0,  0, 52,  0, 20, 120,  60,  45, CRSH,  0, 0, 58},
        {Z,  80, 44, 90, 60, 30, 56,  0, 30,  90,   0,  60, FOLD,  0, 0, 48},
        {R,  79, 84, 15, 20,  0, 22,  0, 55, 110,  20,  65, CRSH,  0, 0, 76},
        {M,  51, 62, 30, 35,  0, 52,  0, 25, 110,  40,  75, FOLD,  0, 0, 84},
    }},
    {{ /* DARK PROG: warm but punchy: a fast drop, a held body, a firmer snare and clap */
        {K,  73, 27, 84, 52, 55, 74, 12, 70,  98,   0,  62, TUBE, 78, 0, 64},
        {S,  86, 57, 32, 52, 10, 56,  0, 55,  95,  72,  55, TUBE, 20, 0, 64},
        {C,  77, 59,  0,  0,  0, 60,  0, 25,  88, 127,  50, TUBE,  5, 0, 64},
        {H,  91, 78,  0,  0,  0, 28,  0, 10, 108,  50,  25, SOFT,  0, 0, 70},
        {H,  61, 78,  0,  0,  0, 64,  0, 10, 106,  50,  25, SOFT,  0, 0, 58},
        {T,  85, 38, 38, 60, 20, 66,  0, 40,  72,   5,  45, TUBE, 25, 0, 54},
        {R, 105, 74, 12, 28,  0, 28,  0, 45,  98,  10,  40, TUBE,  0, 0, 74},
        {M, 103, 64, 10, 45,  0, 58,  0, 15,  92,  15,  40, TUBE,  0, 0, 80},
    }},
    {{ /* PSYCHILL: soft, round, a little air */
        {K,  82, 26, 50, 75, 30, 82, 20, 20,  60,   0,  20, SOFT, 20, 2, 64},
        {S, 105, 56, 20, 70,  5, 66,  0, 20,  80,  65,  20, SOFT, 15, 1, 64},
        {C, 104, 58,  0,  0,  0, 70,  0,  8,  78, 127,  15, SOFT,  0, 1, 64},
        {H, 102, 78,  0,  0,  0, 32,  0,  5, 104,  60,  10, SOFT,  0, 0, 72},
        {H,  60, 78,  0,  0,  0, 76,  0,  5, 102,  60,  10, SOFT,  0, 2, 56},
        {T,  84, 40, 25, 80, 15, 76,  0, 15,  62,   5,  20, SOFT, 20, 1, 50},
        {R, 116, 74,  8, 35,  0, 34,  0, 20,  90,  10,  15, SOFT,  0, 0, 76},
        {T,  95, 54, 20, 70, 10, 66,  0, 20,  75,  10,  20, SOFT, 10, 0, 82},
    }},
    {{ /* TRIBE PERC: djembe, congas, bongo, shakers, wood, a low tribal tom (for Tribetek) */
        {T,  87, 34, 30, 60, 20, 70, 10, 45,  70,   8,  40, TUBE, 20,  0, 60},
        {T,  93, 52, 18, 45,  8, 60,  0, 50,  85,   6,  30, SOFT, 10,  0, 44},
        {T,  98, 60, 16, 40,  6, 54,  0, 55,  90,   6,  30, SOFT,  8,  0, 84},
        {H,  77, 90,  0,  0,  0, 26,  0,  0, 118, 127,  10, SOFT,  0, 12, 76},
        {H,  63, 90,  0,  0,  0, 44,  0,  0, 116, 127,  10, SOFT,  0, 20, 52},
        {T, 111, 70, 14, 35,  4, 46,  0, 60,  98,   8,  30, SOFT,  5,  0, 90},
        {R, 114, 86,  6, 25,  0, 22,  0, 30, 105,   0,  20, SOFT,  0,  0, 38},
        {T,  76, 30, 40, 70, 25, 80, 20, 35,  65,  10,  50, TUBE, 25,  0, 64},
    }},
    {{ /* MENTAL PERC: zaps, crushed toms and hats, folded metal (for Mentaltek) */
        {Z,  83, 40, 120, 70, 30, 50, 0, 20, 100,   0,  60, HARD,  0,  0, 40},
        {M,  49, 66, 25, 40,  0, 64,  0, 30, 105,  15,  80, FOLD,  0,  0, 84},
        {T,  73, 46, 50, 50, 20, 56,  0, 40,  80,  15,  75, CRSH, 10,  0, 56},
        {H,  77, 92,  0,  0,  0, 18,  0, 20, 122,  30,  80, CRSH,  0,  0, 72},
        {H,  49, 92,  0,  0,  0, 48,  0, 20, 120,  30,  80, CRSH,  0,  0, 56},
        {C,  62, 70,  0,  0,  0, 40,  0, 40, 110, 127,  80, HARD,  0,  0, 88},
        {R,  81, 82, 20, 20,  0, 20,  0, 60, 115,  20,  85, HARD,  0,  0, 30},
        {M,  53, 74, 10, 40,  0, 78, 10, 10, 100,   5,  50, FOLD,  0,  0, 64},
    }},
    {{ /* DARK PROG PERC: dark toms, soft shakers, clave, a dark bell, snap, knock (for Dark Prog) */
        {T,  93, 38, 25, 65, 15, 66, 10, 25,  65,   5,  35, TUBE, 15,  0, 50},
        {T,  97, 48, 22, 60, 12, 60,  0, 25,  70,   5,  35, TUBE, 12,  0, 78},
        {H,  81, 88,  0,  0,  0, 24,  0,  0, 112, 127,   5, SOFT,  0, 10, 72},
        {H,  67, 88,  0,  0,  0, 42,  0,  0, 110, 127,   5, SOFT,  0, 18, 56},
        {R, 118, 84,  4, 25,  0, 26,  0, 25, 100,   0,  15, SOFT,  0,  0, 40},
        {M, 116, 62,  0, 40,  0, 72, 10,  5,  85,   0,  25, TUBE,  0,  2, 86},
        {C, 124, 64,  0,  0,  0, 34,  0, 20,  96, 127,  25, TUBE,  0,  0, 30},
        {R, 114, 66, 10, 30,  0, 26,  0, 35,  85,   5,  30, TUBE,  0,  0, 64},
    }},
    {{ /* FOREST PSY: a tight, clicky kick, snappy snare, crushed hats, zaps and ticks */
        {K,   70, 27, 85, 40, 50, 66, 10, 90, 110,   0,  70, HARD, 30, 0, 64},
        {S,  80, 62, 35, 45, 10, 45,  0, 70, 105,  85,  70, HARD,  5, 0, 64},
        {C,   64, 64,  0,  0,  0, 48,  0, 30, 100, 127,  60, HARD,  0, 0, 64},
        {H,  80, 90,  0,  0,  0, 20,  0, 25, 122,  40,  60, CRSH,  0, 0, 70},
        {H,   53, 90,  0,  0,  0, 50,  0, 25, 120,  40,  60, CRSH,  0, 0, 58},
        {Z,   92, 50,110, 55, 20, 40,  0, 30, 105,   0,  60, HARD,  0, 0, 44},
        {R,  80, 84, 18, 22,  0, 18,  0, 60, 115,  20,  80, HARD,  0, 0, 80},
        {M,  80, 76, 15, 35,  0, 40,  0, 20, 110,  10,  70, FOLD,  0, 0, 30},
    }},
    {{ /* FOREST PERC: clicks, wood, ticks, a bug, shakers, a drop, a creak (for Forest Psy) */
        {R,   94, 90, 10, 15,  0, 14,  0, 90, 120,   0,  40, HARD,  0,  0, 64},
        {T,  127, 70, 14, 30,  4, 30,  0, 60, 100,   5,  40, SOFT,  0,  0, 40},
        {R,   93, 95,  8, 18,  0, 12,  0, 70, 122,  10,  60, CRSH,  0,  0, 88},
        {H,  80, 92,  0,  0,  0, 22,  0,  0, 118, 127,  10, SOFT,  0, 12, 70},
        {H,   64, 92,  0,  0,  0, 42,  0,  0, 116, 127,  10, SOFT,  0, 20, 56},
        {Z,  102, 70, 90, 30, 40, 35,  0, 20, 110,  20,  50, FOLD,  0,  0, 76},
        {T,  127, 64, 60, 40, 40, 34,  0, 30,  95,   5,  30, SOFT,  0,  0, 50},
        {M,   55, 58, 20, 50, 30, 60,  0, 10,  80,  30,  50, FOLD,  0, 10, 84},
    }},
    {{ /* PSY PERC: a rolling tom, zaps, a laser, glitch hats, snap, tick, a ring (psytrance, darkpsy) */
        {T,  80, 44, 45, 55, 20, 52,  0, 40,  80,  10,  60, HARD, 10,  0, 52},
        {Z,   88, 46,115, 65, 30, 46,  0, 20, 100,   0,  55, HARD,  0,  0, 40},
        {Z,  80, 70,127, 80, 50, 40,  0, 10, 115,   0,  70, FOLD,  0,  0, 86},
        {H,   71, 94,  0,  0,  0, 18,  0, 25, 124,  35,  75, CRSH,  0,  0, 72},
        {H,   49, 94,  0,  0,  0, 46,  0, 25, 122,  35,  75, CRSH,  0,  0, 56},
        {C,   65, 72,  0,  0,  0, 36,  0, 45, 112, 127,  75, HARD,  0,  0, 88},
        {R,  80, 86, 16, 20,  0, 18,  0, 70, 118,  15,  80, HARD,  0,  0, 30},
        {M,   59, 70, 10, 40,  0, 70, 10, 10, 104,   5,  55, FOLD,  0,  0, 64},
    }},
};

const char *const gd_kit_names[] = {
    "HARDTEK", "TRIBETEK", "MENTALTEK", "TECHNO", "DARK TECHNO",
    "TRANCE", "PSYTRANCE", "DARKPSY", "DARK PROG", "PSYCHILL",
    "TRIBE PERC", "MENTAL PERC", "DARK PROG PERC", "FOREST PSY", "FOREST PERC", "PSY PERC",
};

/* each kit's names for its 8 sounds (a percussion kit's slots are not kick, snare, ...) */
#define DRUMS {"KICK", "SNARE", "CLAP", "C.HAT", "O.HAT", "TOM", "RIM", "PERC"}
const char *const gd_kit_snd_names[][GD_NSND] = {
    DRUMS, DRUMS, DRUMS, DRUMS, DRUMS, DRUMS, DRUMS, DRUMS, DRUMS, DRUMS,
    {"DJEMBE", "CONGA L", "CONGA H", "SHAKE S", "SHAKE L", "BONGO", "WOOD", "SURDO"},
    {"ZAP", "CLANG", "CR.TOM", "GLT.HAT", "GLT.OPN", "RATTLE", "SNAP", "F.BELL"},
    {"TOM LO", "TOM HI", "SHAKE S", "SHAKE L", "CLAVE", "BELL", "SNAP", "KNOCK"},
    DRUMS,
    {"CLICK", "WOOD", "TICK", "SHAKE S", "SHAKE L", "BUG", "DROP", "CREAK"},
    {"ROLL TOM", "ZAP", "LASER", "GLT.HAT", "GLT.OPN", "SNAP", "TICK", "RING"},
};

const int gd_nkits = (int)(sizeof gd_kits / sizeof gd_kits[0]);
typedef char gd_snd_names_match[(sizeof gd_kit_snd_names / sizeof gd_kit_snd_names[0]) == (sizeof gd_kits / sizeof gd_kits[0]) ? 1 : -1];
typedef char gd_names_match[(sizeof gd_kit_names / sizeof gd_kit_names[0]) == (sizeof gd_kits / sizeof gd_kits[0]) ? 1 : -1];
