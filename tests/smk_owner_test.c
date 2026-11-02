/* SPDX-License-Identifier: GPL-3.0-only
 * SMK-37 Pro port: Copyright (C) 2026 M. Geisler (genkigenki/makkuro); Skiff's family and pool */
/* The SMK-37 Pro store's owner tag (storage.c st_owner_check, build with -DBOARD_SMK37=1) on a simulated flash: another
 * firmware's store, an untagged one and Skiff's own; the stock firmware's mapping in USRFLASH and its marker. Only the
 * store's nine pairs, the pool's sectors that hold a chunk ("SKB1"), the tag and the marker's sectors are ever erased,
 * only the tag ever written; ours is kept, and so are the calibration, the user sample and anything else. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "fm1_cc.h"
#if !BOARD_SMK37
#error "build with -DBOARD_SMK37=1"
#endif
#include "fm1_flash_map.h"

static uint8_t nor[0x100000];
static int bad_write, tag_erases, pool_erases;
static int st_read(uint32_t off, void *dst, uint32_t n) { memcpy(dst, nor + off, n); return 0; }
static int st_erase(uint32_t off)
{
    if ((off & 0xFFFu) || !(FL_IN(off, 0x1000u, 0x9D000u, 0xAF000u) || off == 0xAF000u || off == 0xEA000u ||
                            FL_IN(off, 0x1000u, FL_BANK_LO, FL_BANK_HI)))
        bad_write++;
    tag_erases += off == 0xEA000u;
    pool_erases += FL_IN(off, 0x1000u, FL_BANK_LO, FL_BANK_HI);
    memset(nor + off, 0xFF, 0x1000);
    return 0;
}
static int st_prog(uint32_t off, const void *src, uint32_t n)
{
    const uint8_t *s = src;
    uint32_t i;
    if (off != 0xAF000u)
        bad_write++;
    for (i = 0; i < n; i++)
        nor[off + i] &= s[i];
    return 0;
}
#include "../firmware/src/storage.c"

static int bad;
static void check(const char *what, int ok) { printf("smk owner: %-84s %s\n", what, ok ? "ok" : "FAIL"); bad += !ok; }

static void chunk(uint32_t off) { memcpy(nor + off, "SKB1", 4); memset(nor + off + 4, 0x55, 0x100); }
static void fill(void)
{
    memset(nor, 0xFF, sizeof nor);
    memset(nor + 0x9D000, 0x11, 0x12000);          /* the objects */
    memset(nor + 0xB0000, 0x22, 0x1000);           /* a spare sector (another firmware's data): left alone */
    memset(nor + 0xC1000, 0x33, 0x1000);           /* USRTRIM: never touched */
    memset(nor + 0xC2000, 0x44, 0x1000);           /* the user sample */
    chunk(0xD6000);                                /* two pool chunks */
    chunk(0xE9000);
    memset(nor + 0xDA000, 0x66, 0x1000);           /* a pool sector with something else in it */
}
static int store_erased(void)
{
    uint32_t i;
    for (i = 0x9D000; i < 0xAF000; i++) if (nor[i] != 0xFF) return 0;
    return 1;
}
static int pool_chunks_erased(void) { return nor[0xD6000] == 0xFF && nor[0xE9000] == 0xFF && nor[0xDA000] == 0x66; }
static int others_kept(void)
{
    return nor[0xC1000] == 0x33 && nor[0xC1FFF] == 0x33 && nor[0xC2000] == 0x44 && nor[0xB0000] == 0x22;
}
static int tag_is(const char *t) { return !memcmp(nor + 0xAF000, t, 16); }

static void stock(void)                            /* the stock mapping as V016 writes it */
{
    uint32_t n;
    memset(nor + 0xC2000, 0xFF, 0x29000);
    memset(nor + 0xC2000, 0x07, 0x86);
    nor[0xC2000] = 0xA3; nor[0xC2001] = 0x3A;
    for (n = 0; n < 8u; n++) {
        memset(nor + 0xC3000 + n * 0x5000, 0x01, 0x29E3);
        nor[0xC3000 + n * 0x5000 + 4] = 0x7F;
    }
    memcpy(nor + 0xEAFF8, "usrdata", 8);
}
static int is_stock(void)
{
    static uint8_t keep[0x29000];
    int same;
    memcpy(keep, nor + 0xC2000, sizeof keep);
    stock();
    same = !memcmp(keep, nor + 0xC2000, sizeof keep);
    memcpy(nor + 0xC2000, keep, sizeof keep);
    return same;
}

int main(void)
{
    uint8_t want[16];
    st_owner_tag(want);
    check("the tag: \"SMK37DATA\" + the family SKIFF, zero padded to 16 bytes",
          !memcmp(want, "SMK37DATASKIFF\0\0", 16) && !strcmp(SMK_DATA_FAMILY, "SKIFF"));
    fill();
    memcpy(nor + 0xAF000, "SMK37DATAFELUCCA", 16);  /* (genkigenki's Felucca port: another family) */
    st_owner_check();
    check("another firmware's store (Felucca's tag): cleared, tagged SKIFF", store_erased() && st_owner_cleared &&
          tag_is("SMK37DATASKIFF\0\0"));
    check("... the pool's chunks erased, its other sectors left (their first erase is the pool's)", pool_chunks_erased());
    check("... calibration (USRTRIM), the user sample and a spare sector untouched", others_kept());
    fill();
    memcpy(nor + 0xAF000, "SMK37DATASKIFF\0\0", 16);
    st_owner_cleared = 0;
    pool_erases = 0;
    st_owner_check();
    check("our own store: kept as it is, the pool too", nor[0x9D000] == 0x11 && nor[0xD6000] == 'S' &&
          !st_owner_cleared && pool_erases == 0);
    fill();
    st_owner_check();
    check("an untagged store (FELUCCA_DATA_UNTAGGED_OK 0): cleared, tagged", store_erased() &&
          tag_is("SMK37DATASKIFF\0\0") && others_kept());
    fill();
    memcpy(nor + 0xAF000, "SMK37DATASKIFFX\0", 16);   /* (one byte more: not ours) */
    st_owner_cleared = 0;
    st_owner_check();
    check("a tag that only starts with ours: not ours", st_owner_cleared && store_erased());

    /* the stock firmware's mapping in USRFLASH: kept while intact, its marker released over anything else */
    fill();
    stock();
    memcpy(nor + 0xAF000, "SMK37DATAOTHER\0\0", 16);
    tag_erases = pool_erases = 0;
    st_owner_check();
    check("the first boot over the intact stock mapping: USRFLASH and its marker kept, no pool erase",
          is_stock() && tag_erases == 0 && pool_erases == 0 && st_stock_intact());
    st_owner_check();
    check("... and at the next boot (ours now)", is_stock() && tag_erases == 0);
    st_stock_release();                            /* the first erase in USRFLASH (storage_hw.c, editor.c) */
    check("the first write into USRFLASH: the marker's sector erased, once", tag_erases == 1 && !st_stock_tagged() &&
          nor[0xC2000] == 0xA3);
    st_stock_release();
    check("... and only once", tag_erases == 1);
    {
        static const uint32_t HIT[] = {0xC2000u, 0xC6000u, 0xD6000u, 0xDB000u, 0xE5000u, 0xE9000u};
        uint32_t h, ok = 1;
        for (h = 0; h < sizeof HIT / sizeof HIT[0]; h++) {
            stock();
            nor[HIT[h]] = 0x46;                    /* (a sample or a pool chunk over the stock layout) */
            ok &= !st_stock_intact();
        }
        stock();
        memset(nor + 0xC8000, 0xFF, 0x1000);       /* (an erased preset head) */
        ok &= !st_stock_intact();
        check("the stock layout checked: its settings' magic, each preset's head and erased tail", ok);
    }
    stock();
    chunk(0xD6000);                                /* a pool chunk written over the stock presets */
    memcpy(nor + 0xAF000, "SMK37DATASKIFF\0\0", 16);
    tag_erases = 0;
    st_owner_check();
    check("the marker over our pool: released at boot, the pool kept", tag_erases == 1 && !st_stock_tagged() &&
          nor[0xD6000] == 'S');
    fill();
    tag_erases = 0;
    st_owner_check();
    check("no marker: its sector never erased", tag_erases == 0);
    check("nothing erased or written outside the pairs, the pool, the tag and the marker", bad_write == 0);
    printf("%s\n", bad ? "SMK OWNER TEST FAILED" : "smk owner test passed");
    return bad != 0;
}
