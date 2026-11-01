/* SPDX-License-Identifier: GPL-3.0-only */
/* tests/loader_guard.sh: a fixed stand-in for the system header, so the preprocessed loader is
 * the same on every machine (only the loader's own sources decide its hash) */
#pragma once
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
typedef unsigned long long uint64_t;
typedef long long int64_t;
typedef unsigned int uintptr_t;
