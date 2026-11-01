/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore sound categories: every synth preset is one kind, so the PRESETS list can show only the
 * basses, only the pads, ... across the engines. */
#pragma once
enum { CAT_BASS, CAT_ACID, CAT_LEAD, CAT_PLUCK, CAT_STAB, CAT_PAD, CAT_PERC, CAT_FX, NCAT };
#define CAT_NAMES {"BASS", "ACID", "LEAD", "PLUCK", "STAB", "PAD", "PERC", "FX"}
