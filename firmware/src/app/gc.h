/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore app: the project (everything that is saved) and the app-level entry points.
 * Included by the unity build after gfx.c, so drawing helpers are in scope. */
#pragma once
#include <stdint.h>
#include "plat.h"
#include "gengine.h"
#include "gsounds.h"
#include "../seq/gpat.h"
#include "../seq/gseq.h"

#ifndef X0X_VERSION                     /* a release build passes its own (tools/build.py --release) */
#define X0X_VERSION "DEV"
#endif
#define GC_VERSION X0X_VERSION
/* GruselCore's own format markers: X0X's (or any other firmware's) saved objects carry other words,
 * so they are never read as a GruselCore project; the defaults load instead */
#define PROJ_MAGIC 0x4C535247u           /* "GRSL" */
#define PROJ_FORMAT 0x47430001u          /* the settings and sound objects */
#define PROJ_STREAM 0x47430101u          /* the packed patterns */

typedef struct {
    uint32_t magic, format;
    uint8_t palette, keyled, clk_out, notes_out;   /* keyled: 0 off, 1 keys and the buttons' glow, 2 keys only */
    uint16_t bpm_x10;
    uint8_t accent_q7;
    uint8_t autosave_off;                /* 0: saves by itself while stopped and idle */
    uint8_t midi_ch[NTRK];               /* each track's MIDI channel: 0 = its default (track n on n), 1-16, 17 = OFF */
    uint8_t out_loud;                    /* unused: the output is always at the codec's full scale */
    uint8_t usb_full;                    /* 1: USB audio at full level, the MASTER knob for the FM-1's own outputs */
    uint8_t one_core;                    /* 1: the second core stays off (after it crashed beside it) */
    uint8_t swing;                       /* the global swing, 0..100 */
    uint8_t tpat[NTRK];                  /* the pattern each track was playing */
    uint8_t list;                        /* the PRESETS list: 0 every kind, 1 + CAT_* one kind */
    uint8_t rsv[3];
} settings_t;

typedef struct {
    settings_t set;
    sound_t sound;
    pattern_t pat[NPAT];
} project_t;

extern project_t proj;

void project_defaults(void);
int project_load(void);                  /* 0 = loaded; else defaults are in place */
int project_save(void);                  /* 0 = saved and verified; -7 = too much to fit (nothing written) */
int project_save_settings(void);
void project_apply_io(void);             /* the settings into the sequencer and the engine: MIDI, the output */
int project_mem_pct(void);               /* how full the room for patterns is, % */
void project_flash_changed(void);        /* a restore wrote the flash: the next save writes every object */
void project_set_type(int trk, int tt);  /* a track's new type: its steps in every pattern cleared, the engine told */
void project_load_sound(int trk, int id); /* a synth sound (gsounds.h) onto a synth track, its engine switched if need be */

void ui_init(void);
void ui_frame(void);
void ui_input_only(void);
int ui_dirty(void);
void ui_say(const char *a, const char *b);
void ui_warn(const char *a, const char *b);
void ui_flush(void);                     /* stopped: the unsaved changes saved now (a backup takes the flash's) */
void ui_hold_saves(int on);              /* 1: no save until 0 (a backup streams the flash) */
void ui_redraw(void);
void app_restored(void);                 /* a restore wrote the project: loaded again, as at power-on */
extern uint8_t ui_autosave_block;        /* 1: no autosave (started without the saved project) */
