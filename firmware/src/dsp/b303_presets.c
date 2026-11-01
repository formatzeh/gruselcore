/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore 303 presets. Pot order (bass303.h): CUTOFF RESO ENVMOD DECAY ACCENT WAVE TUNE VOLUME
 * DRIVE DRVTYPE SLIDE ACCDEC. VOLUME: each preset at -16 dB through the engine's B303_GAIN, as the drum
 * kits (tests/host/presets_test.c). */
#include "bass303.h"

const b303_preset_t b303_presets[] = {
    {"CLASSIC 303", CAT_ACID,  {64, 64, 64, 64, 64, 0, 64, 84, 0, 1, 21, 7}},
    {"ACID SQUEAL", CAT_ACID,  {50, 110, 100, 50, 100, 0, 64, 77, 0, 1, 21, 7}},
    {"DEEP ACID", CAT_ACID,    {30, 90, 70, 80, 64, 0, 64, 83, 0, 1, 30, 10}},
    {"RUBBER BASS", CAT_BASS,  {40, 40, 50, 40, 50, 1, 64, 89, 0, 1, 21, 7}},
    {"SQUARE ACID", CAT_ACID,  {60, 95, 85, 55, 80, 1, 64, 85, 0, 1, 21, 7}},
    {"DIST ACID", CAT_ACID,    {55, 100, 90, 50, 90, 0, 64, 82, 70, 1, 21, 7}},
    {"FUZZ ACID", CAT_ACID,    {50, 105, 95, 45, 100, 0, 64, 111, 110, 1, 21, 7}},
    {"HARDTEK 303", CAT_ACID,  {70, 100, 110, 35, 110, 0, 64, 88, 90, 1, 15, 5}},
    {"MENTAL 303", CAT_ACID,   {45, 120, 120, 30, 120, 1, 64, 87, 80, 1, 10, 4}},
    {"TRIBE 303", CAT_BASS,    {35, 70, 60, 40, 70, 1, 64, 87, 30, 1, 25, 8}},
    {"DARK 303", CAT_ACID,     {20, 85, 50, 90, 60, 0, 64, 84, 20, 1, 40, 15}},
    {"PSY ROLL 303", CAT_BASS, {40, 60, 80, 25, 80, 0, 64, 83, 25, 1, 10, 5}},
    {"SOFT ACID", CAT_ACID,    {70, 50, 40, 70, 40, 0, 64, 88, 0, 1, 40, 10}},
    {"SLIDE MONSTR", CAT_ACID, {45, 100, 90, 60, 90, 0, 64, 78, 40, 1, 90, 20}},
    {"SHORT BLIP", CAT_ACID,   {80, 80, 100, 10, 90, 1, 64, 85, 0, 1, 21, 3}},
    {"LONG SWEEP", CAT_ACID,   {25, 110, 100, 127, 70, 0, 64, 79, 10, 1, 50, 40}},
    {"FOREST 303", CAT_ACID,   {55, 115, 105, 20, 110, 1, 64, 84, 50, 1, 15, 4}},
    {"DUB 303", CAT_BASS,      {15, 60, 40, 100, 40, 1, 64, 91, 0, 1, 60, 20}},
    {"SCREAM 303", CAT_ACID,   {75, 127, 127, 40, 127, 0, 64, 93, 100, 1, 20, 8}},
    {"TRANCE 303", CAT_ACID,   {60, 70, 75, 55, 70, 0, 64, 83, 15, 1, 30, 10}},
};
const int b303_npresets = (int)(sizeof b303_presets / sizeof b303_presets[0]);
