/* SPDX-License-Identifier: GPL-3.0-only */
/* GruselCore project: the settings, the sound and the 32 patterns. After X0X's project.c (Charles
 * Vestal), whose storage scheme it keeps:
 *
 * The settings and the sound are one storage object each. The patterns (~35 KB, mostly empty steps)
 * are one stream packed with lz.c across the four objects OBJ_PAT0, OBJ_PAT1, OBJ_SONG, OBJ_MOTION.
 * The first carries the raw length and a CRC of the raw bytes, so a stream torn by a power cut
 * between two objects, or one that does not unpack, is never loaded as garbage: the objects'
 * previous copies (storage.c keeps two) are tried instead, which give the save before; only when no
 * mix of copies checks out, the defaults. A save packs once to measure (nothing is written if it
 * would not fit: "MEMORY FULL") and once to write; an object whose bytes did not change is not
 * written again.
 *
 * Every object carries GruselCore's own format word (gc.h): what another firmware left in these
 * objects (X0X, Felucca, SLOOP ...) never matches, so it is never parsed; the defaults load. */
#include "gc.h"
#include "lz.c"

project_t proj;

static const uint8_t STREAM_OBJ[] = {OBJ_PAT0, OBJ_PAT1, OBJ_SONG, OBJ_MOTION};
#define NSTREAM ((int)sizeof STREAM_OBJ)
#define STREAM_HDR 16u                  /* in the first object: format, raw length, raw CRC, packed length */
#define STREAM_CAP (NSTREAM * (PLAT_STORE_MAX - 4u) - (STREAM_HDR - 4u))
#define RAW_OFF __builtin_offsetof(project_t, pat)
#define RAW_LEN (sizeof(project_t) - RAW_OFF)   /* the patterns */
typedef char raw_fits[(RAW_LEN < 0xFFFFu) ? 1 : -1];

static uint32_t packed_len;             /* the last save's (or load's) packed stream, bytes */

static void patterns_defaults(void)
{
    int i;
    for (i = 0; i < NPAT; i++)
        gpat_init(&proj.pat[i], proj.sound.ttype);
}

void project_defaults(void)
{
    uint8_t *z = (uint8_t *)&proj.set;
    uint32_t i;
    for (i = 0; i < sizeof proj.set; i++)
        z[i] = 0;
    proj.set.magic = PROJ_MAGIC;
    proj.set.format = PROJ_FORMAT;
    proj.set.palette = 1;
    proj.set.keyled = 1;
    proj.set.clk_out = 1;
    proj.set.bpm_x10 = 1450;
    proj.set.accent_q7 = 88;
    engine_sound_defaults(&proj.sound);
    patterns_defaults();
}

int project_mem_pct(void) { return (int)((packed_len * 100u + STREAM_CAP - 1u) / STREAM_CAP); }

/* object payload: format word + body */
static uint8_t io_buf[PLAT_STORE_MAX] __attribute__((aligned(4)));

/* what each object last held on the flash (a hash of its payload), so a save writes only the
 * objects that changed: an autosave usually erases one or two sectors, not six */
static uint32_t stored_hash[OBJ_NOBJ];
static uint8_t stored_known[OBJ_NOBJ];
static uint32_t hash_of(const uint8_t *p, uint32_t n)        /* FNV-1a */
{
    uint32_t h = 2166136261u;
    while (n--)
        h = (h ^ *p++) * 16777619u;
    return h;
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static uint32_t crc32_of(const uint8_t *p, uint32_t n)       /* zlib CRC-32, 4 bits per step */
{
    static const uint32_t T[16] = {
        0x00000000u, 0x1DB71064u, 0x3B6E20C8u, 0x26D930ACu, 0x76DC4190u, 0x6B6B51F4u, 0x4DB26158u, 0x5005713Cu,
        0xEDB88320u, 0xF00F9344u, 0xD6D6A3E8u, 0xCB61B38Cu, 0x9B64C2B0u, 0x86D3D2D4u, 0xA00AE278u, 0xBDBDF21Cu};
    uint32_t c = 0xFFFFFFFFu;
    while (n--) {
        c ^= *p++;
        c = (c >> 4) ^ T[c & 15u];
        c = (c >> 4) ^ T[c & 15u];
    }
    return ~c;
}

/* the object is the n bytes of io_buf, format word included; written only if they changed */
static int save_buf(uint32_t obj, uint32_t n)
{
    uint32_t h = hash_of(io_buf, n);
    int rc;
    if (stored_known[obj] && stored_hash[obj] == h)
        return 0;                                    /* the flash already holds exactly this */
    rc = plat_store_save(obj, io_buf, n);
    stored_known[obj] = rc == 0;
    stored_hash[obj] = h;
    return rc;
}

static int load_obj(uint32_t obj, void *dst, uint32_t len)
{
    int n = plat_store_load(obj, io_buf, sizeof io_buf);
    uint32_t i;
    if (n < 0 || (uint32_t)n != len + 4u || get32(io_buf) != PROJ_FORMAT)
        return -1;
    for (i = 0; i < len; i++)
        ((uint8_t *)dst)[i] = io_buf[4u + i];
    stored_known[obj] = 1;
    stored_hash[obj] = hash_of(io_buf, len + 4u);
    return 0;
}

/* the settings may have grown since they were saved: a shorter payload of this format loads into
 * the front of dst, and the rest keeps what dst held (zeros: the new settings' defaults) */
static int load_settings(settings_t *dst)
{
    int n = plat_store_load(OBJ_SET, io_buf, sizeof io_buf);
    uint32_t i;
    if (n < 20 || (uint32_t)n > sizeof *dst + 4u || get32(io_buf) != PROJ_FORMAT)
        return -1;
    for (i = 0; i + 4u < (uint32_t)n; i++)
        ((uint8_t *)dst)[i] = io_buf[4u + i];
    if ((uint32_t)n == sizeof *dst + 4u) {           /* exactly what a save of these settings writes */
        stored_known[OBJ_SET] = 1;
        stored_hash[OBJ_SET] = hash_of(io_buf, (uint32_t)n);
    }
    return 0;
}

static int save_obj(uint32_t obj, const void *src, uint32_t len)
{
    uint32_t i;
    if (len + 4u > sizeof io_buf)
        return -1;
    put32(io_buf, PROJ_FORMAT);
    for (i = 0; i < len; i++)
        io_buf[4u + i] = ((const uint8_t *)src)[i];
    return save_buf(obj, len + 4u);
}

typedef char sound_fits[(sizeof(sound_t) + 4u <= PLAT_STORE_MAX) ? 1 : -1];


/* ---- the packed stream ---------------------------------------------------------------------- */

/* the writer: fills io_buf after the object's header and writes it when full (measure: counts only) */
typedef struct {
    int measure, k, err;
    uint32_t fill, total;
} st_out_t;

static int st_flush(st_out_t *o)
{
    int rc = save_buf(STREAM_OBJ[o->k], o->fill);
    o->k++;
    o->fill = 4u;
    put32(io_buf, PROJ_STREAM);
    return rc;
}

static int st_put(void *ctx, const uint8_t *p, uint32_t n)
{
    st_out_t *o = ctx;
    o->total += n;
    if (o->measure)
        return o->total > STREAM_CAP ? -1 : 0;
    while (n) {
        if (o->fill == PLAT_STORE_MAX) {
            if (o->k + 1 >= NSTREAM || st_flush(o)) {
                o->err = 1;
                return -1;
            }
        }
        io_buf[o->fill++] = *p++;
        n--;
    }
    return 0;
}

static int save_stream(void)
{
    const uint8_t *raw = (const uint8_t *)&proj + RAW_OFF;
    uint32_t crc = crc32_of(raw, RAW_LEN);
    st_out_t o = {1, 0, 0, 0, 0};
    lz_sink_t sink = {st_put, &o};
    if (lz_compress(raw, RAW_LEN, &sink))
        return -7;                                    /* would not fit: nothing written */
    packed_len = o.total;
    o.measure = 0;
    o.total = 0;
    o.fill = STREAM_HDR;
    put32(io_buf, PROJ_STREAM);
    put32(io_buf + 4, RAW_LEN);
    put32(io_buf + 8, crc);
    put32(io_buf + 12, packed_len);
    if (lz_compress(raw, RAW_LEN, &sink) || o.err || st_flush(&o))
        return -3;
    while (o.k < NSTREAM)                             /* the objects past the stream: empty */
        if (st_flush(&o))
            return -3;
    return 0;
}

/* the reader: the objects in turn, from io_buf */
typedef struct {
    int k, n;
    uint32_t pos, left, prev;                         /* prev: bit k, object k from its previous copy */
} st_in_t;

static int stream_obj_load(int k, uint32_t prev)      /* object k of the stream into io_buf, its copy per prev */
{
    return (prev >> k) & 1u ? plat_store_load_prev(STREAM_OBJ[k], io_buf, sizeof io_buf)
                            : plat_store_load(STREAM_OBJ[k], io_buf, sizeof io_buf);
}

static int st_get(void *ctx)
{
    st_in_t *s = ctx;
    if (!s->left)
        return -1;
    while (s->pos >= (uint32_t)s->n) {
        if (++s->k >= NSTREAM)
            return -1;
        s->n = stream_obj_load(s->k, s->prev);
        if (s->n < 4 || get32(io_buf) != PROJ_STREAM)
            return -1;
        stored_known[STREAM_OBJ[s->k]] = !((s->prev >> s->k) & 1u);   /* a previous copy: written again next save */
        stored_hash[STREAM_OBJ[s->k]] = hash_of(io_buf, (uint32_t)s->n);
        s->pos = 4u;
    }
    s->left--;
    return io_buf[s->pos++];
}

/* 0 = loaded; -1 = not there or not good (proj's patterns and arrangement then hold garbage) */
static int load_stream(int n, uint32_t prev)
{
    uint8_t *raw = (uint8_t *)&proj + RAW_OFF;
    uint32_t crc = get32(io_buf + 8), plen = get32(io_buf + 12);
    st_in_t s = {0, n, STREAM_HDR, plen, prev};
    lz_src_t src = {st_get, &s};
    if (n < (int)STREAM_HDR || get32(io_buf + 4) != RAW_LEN || plen > STREAM_CAP)
        return -1;
    stored_known[STREAM_OBJ[0]] = !(prev & 1u);
    stored_hash[STREAM_OBJ[0]] = hash_of(io_buf, (uint32_t)n);
    if (lz_decompress(&src, raw, RAW_LEN) || crc32_of(raw, RAW_LEN) != crc)
        return -1;
    packed_len = plen;
    return 0;
}


typedef char sound_fits[(sizeof(sound_t) + 4u <= PLAT_STORE_MAX) ? 1 : -1];

void project_flash_changed(void)
{
    int i;
    for (i = 0; i < OBJ_NOBJ; i++)
        stored_known[i] = 0;
}

/* the sound as loaded may hold values no engine takes (another version): each pot clamped, every
 * type known, so nothing out of range reaches the engines */
static void sound_sanitize(sound_t *s)
{
    int t, v, i;
    for (t = 0; t < NTRK; t++) {
        if (s->ttype[t] >= NTT)
            s->ttype[t] = TT_OFF;
        if (s->kit[t] >= gd_nkits)
            s->kit[t] = 0;
        for (v = 0; v < NDSND; v++)
            for (i = 0; i < GP_N; i++)
                if (s->drum[t][v][i] > gdrum_param(i)->max)
                    s->drum[t][v][i] = gdrum_param(i)->max;
        for (i = 0; i < MX_NPARAMS; i++)
            if (s->mix[t][i] > 127)
                s->mix[t][i] = 127;
    }
}

/* the patterns as loaded: lengths and rates in range */
static void patterns_sanitize(void)
{
    int p, t;
    for (p = 0; p < NPAT; p++)
        for (t = 0; t < NTRK; t++) {
            tpart_t *k = &proj.pat[p].t[t];
            if (k->len < 1 || k->len > NSTEPS)
                k->len = 16;
            if (k->rate >= NRATES)
                k->rate = RATE_16;
            if (k->dir >= NDIRS)
                k->dir = DIR_FWD;
        }
}

int project_load(void)
{
    int bad = 0, n;
    settings_t set;
    project_defaults();
    packed_len = 0;
    set = proj.set;
    if (load_settings(&set) == 0 && set.magic == PROJ_MAGIC)
        proj.set = set;
    else
        bad = 1;
    if (load_obj(OBJ_SOUND, &proj.sound, sizeof proj.sound) != 0) {
        engine_sound_defaults(&proj.sound);
        bad = 1;
    }
    sound_sanitize(&proj.sound);
    n = plat_store_load(OBJ_PAT0, io_buf, sizeof io_buf);
    if (n >= 4 && get32(io_buf) == PROJ_STREAM) {
        if (load_stream(n, 0)) {                      /* torn (a power cut mid-save) or broken: the previous
                                                       * copies, fewest first (the newest save that checks out) */
            uint32_t prev = 0;
            int ok = 0, b;
            for (b = 1; b <= NSTREAM && !ok; b++)
                for (prev = 1; prev < (1u << NSTREAM) && !ok; prev++) {
                    if ((uint32_t)__builtin_popcount(prev) != (uint32_t)b)
                        continue;
                    n = stream_obj_load(0, prev);
                    ok = n >= 4 && get32(io_buf) == PROJ_STREAM && load_stream(n, prev) == 0;
                }
            if (!ok) {
                patterns_defaults();
                bad = 1;
            }
        }
    } else {
        patterns_defaults();
        bad = 1;
    }
    patterns_sanitize();
    for (n = 0; n < NTRK; n++)
        if (proj.set.tpat[n] >= NPAT)
            proj.set.tpat[n] = 0;
    if (proj.set.swing > 100)
        proj.set.swing = 0;
    return bad ? -1 : 0;
}

void project_apply_io(void)
{
    int t;
    seq.send_clock = proj.set.clk_out;
    seq.send_notes = proj.set.notes_out;
    for (t = 0; t < NTRK; t++) {
        int v = proj.set.midi_ch[t];
        seq.ch[t] = (uint8_t)(!v ? t : v > 16 ? SEQ_CH_OFF : v - 1);
    }
    seq.swing = proj.set.swing;
    for (t = 0; t < NTRK; t++)
        seq.tpat[t] = proj.set.tpat[t];
    engine_out_loud(proj.set.out_loud);
    engine_usb_full(proj.set.usb_full);
}

int project_save(void)
{
    int t;
    for (t = 0; t < NTRK; t++)
        proj.set.midi_ch[t] = (uint8_t)(seq.ch[t] == SEQ_CH_OFF ? 17 : seq.ch[t] + 1);
    proj.set.bpm_x10 = (uint16_t)(seq.bpm * 10.0f + 0.5f);
    proj.set.accent_q7 = seq.accent_q7;
    proj.set.clk_out = seq.send_clock;
    proj.set.notes_out = seq.send_notes;
    proj.set.swing = seq.swing;
    for (t = 0; t < NTRK; t++)
        proj.set.tpat[t] = seq.tpat[t];
    if (save_obj(OBJ_SET, &proj.set, sizeof proj.set))
        return -1;
    if (save_obj(OBJ_SOUND, &proj.sound, sizeof proj.sound))
        return -2;
    return save_stream();
}

int project_save_settings(void) { return save_obj(OBJ_SET, &proj.set, sizeof proj.set); }

/* a track's type changes: its steps in every pattern are cleared to the new type's empty form (the
 * union would read the old type's bytes as the new one's), the sound mirror and the engine follow.
 * The sequencer reads the steps in the ISR: the engine switches the type first (the queue), and the
 * steps are cleared after, so a step that fires in between plays the new type's empty step */
void project_set_type(int t, int tt)
{
    int p;
    if (t < 0 || t >= NTRK || tt < 0 || tt >= NTT || proj.sound.ttype[t] == tt)
        return;
    proj.sound.ttype[t] = (uint8_t)tt;
    engine_set(T_TRK, t, TK_TYPE, tt);
    for (p = 0; p < NPAT; p++)
        gpat_track_clear(&proj.pat[p].t[t], tt);
}
