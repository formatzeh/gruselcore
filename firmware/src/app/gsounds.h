/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore's synth sounds: every engine's presets (303, VA, FM, PHYS) in one list, as Skiff's.
 * A sound's id is its place in that list (engine by engine), stored in sound_t.kit of a synth track.
 * The PRESETS knob walks the list in browse order: by kind (CAT_*), then engine, then preset; with a
 * kind chosen (LIST), only that kind. A sound of another engine switches the track's engine (the
 * steps stay: every synth engine plays the same note steps). */
#pragma once
#include <stdint.h>
#include "../dsp/gcat.h"

int gs_count(void);
int gs_type(int id);                       /* TT_303, TT_VA, TT_FM, TT_PHYS */
int gs_cat(int id);
const char *gs_name(int id);
const uint8_t *gs_pots(int id, int *n);    /* the preset's pots and how many */
int gs_first(int tt);                      /* the engine's first sound */
int gs_step(int id, int d, int cat);       /* d sounds on in browse order, within cat (-1: all) */
int gs_pos(int id, int cat, int *total);   /* id's place (0..) in that order, and the order's length */
const char *gs_cat_name(int cat);          /* "BASS", ...; -1: "ALL" */
const char *gs_engine_name(int tt);        /* "303", "VA", "FM", "PHYS" */
