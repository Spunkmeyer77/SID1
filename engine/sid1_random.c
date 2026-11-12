/* SPDX-License-Identifier: GPL-3.0-only */
#include "sid1_random.h"
#include <string.h>

const char *const SID1_RTYPE_NAMES[SID1_R_NTYPES] = {"LEAD", "BASS", "PAD", "PLUCK", "ARP", "DRUM", "FX", "ANY"};

enum { TRI = 0x10, SAW = 0x20, PUL = 0x40, NOI = 0x80, RING = 0x04, SYNC = 0x02 };
enum { LP = 0x10, BP = 0x20, HP = 0x40 };

static uint32_t rnd(uint32_t *s) { *s ^= *s << 13; *s ^= *s >> 17; *s ^= *s << 5; return *s; }
static float rf(uint32_t *s) { return (float)(rnd(s) >> 8) / 16777216.0f; }                 /* 0..1 */
static int ri(uint32_t *s, int lo, int hi) { return lo + (int)(rnd(s) % (uint32_t)(hi - lo + 1)); }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
static int chance(uint32_t *s, float p) { return rf(s) < p; }

static void set_env(sid1_patch_t *p, int a, int d, int s, int r)
{
    p->ad = (uint8_t)(clampi(a, 0, 15) << 4 | clampi(d, 0, 15));
    p->sr = (uint8_t)(clampi(s, 0, 15) << 4 | clampi(r, 0, 15));
}
static void set_pw(sid1_patch_t *p, int pw) { pw = clampi(pw, 0, 4095); p->pw_hi = (uint8_t)(pw >> 8); p->pw_lo = (uint8_t)(pw & 255); }

/* a waveform: darker picks triangle and wide pulses, brighter picks saw and the mixed waves */
static int pick_wave(uint32_t *s, float bright, int allow_mix)
{
    float b = (bright + 1.0f) * 0.5f, x = rf(s);
    if (x < 0.35f * (1.0f - b) + 0.05f) return TRI;
    x = rf(s);
    if (allow_mix && x < 0.15f + 0.2f * b) return chance(s, 0.5f) ? (PUL | SAW) : (SAW | TRI);
    return chance(s, 0.45f + 0.25f * b) ? SAW : PUL;
}

/* pulse width: centre-ish when dark, narrower when bright */
static int pick_pw(uint32_t *s, float bright) { int w = (int)(2048 - (bright + 1.0f) * 600.0f) + ri(s, -350, 350); return clampi(w, 256, 3840); }
static int bright_cut(uint32_t *s, int lo, int hi, float bright) { return clampi(ri(s, lo, hi) + (int)(bright * 50.0f), 4, 250); }

static const int8_t CHORDS[][4] = {
    {0, 4, 7, 0}, {0, 4, 7, 12}, {0, 7, 12, 16}, {0, 4, 7, 11},            /* major family */
    {0, 3, 7, 0}, {0, 3, 7, 12}, {0, 3, 7, 10}, {0, 7, 12, 15},            /* minor family */
    {0, 5, 7, 0}, {0, 2, 7, 0}, {0, 5, 7, 12}, {0, 7, 12, 0},              /* sus and fifths */
};
static const uint8_t CHORD_LEN[] = {3, 4, 4, 4, 3, 4, 4, 4, 3, 3, 4, 3};

static void fresh(sid1_patch_t *p, int type, const sid1_roll_t *r, uint32_t *s)
{
    float b = r->bright, m = r->motion, L = r->length;
    int lshift = (int)(L * 3.0f), k;
    sid1_patch_init(p);
    memset(p->name, 0, sizeof p->name);
    p->mode = LP; p->cut = 128; p->cut_end = 128; p->pw_min = 8; p->pw_max = 248;
    switch (type) {
    case SID1_R_LEAD:
        p->wave = (uint8_t)pick_wave(s, b, 1);
        set_env(p, ri(s, 0, 3) + (lshift > 0 ? lshift : 0), ri(s, 6, 10) + lshift, ri(s, 8, 13), ri(s, 5, 9) + lshift);
        p->flags = SID1_PF_HARD;
        set_pw(p, pick_pw(s, b));
        p->pw_speed = (int8_t)(m * ri(s, 8, 40) * (chance(s, 0.5f) ? 1 : -1));
        p->pw_min = (uint8_t)ri(s, 16, 80); p->pw_max = (uint8_t)ri(s, 160, 232);
        if (chance(s, 0.4f)) { p->flags |= SID1_PF_FILTER; p->mode = chance(s, 0.75f) ? LP : BP; p->cut = (uint8_t)bright_cut(s, 90, 200, b); p->res = (uint8_t)ri(s, 0, 9); p->cut_end = p->cut; }
        p->vib_depth = (uint8_t)(m * ri(s, 10, 35)); p->vib_speed = (uint8_t)ri(s, 14, 30); p->vib_delay = (uint8_t)ri(s, 6, 24);
        p->transpose = (int8_t)(chance(s, 0.3f) ? 12 : 0);
        if (chance(s, 0.3f)) {                                   /* the noise attack */
            p->wt_len = 2; p->wt_loop = 1; p->wt_ctl[0] = NOI; p->wt_note[0] = 24; p->wt_ctl[1] = 0; p->wt_note[1] = 0;
        }
        break;
    case SID1_R_BASS:
        p->wave = (uint8_t)(chance(s, 0.15f) ? TRI : pick_wave(s, b, 1));
        set_env(p, ri(s, 0, 1), ri(s, 6, 10) + lshift, ri(s, 4, 12), ri(s, 3, 8) + lshift);
        p->flags = SID1_PF_HARD | SID1_PF_FILTER; p->mode = LP;
        set_pw(p, pick_pw(s, b));
        p->cut = (uint8_t)bright_cut(s, 30, 110, b); p->res = (uint8_t)ri(s, 4, 14);
        p->cut_speed = (int8_t)-(int)(m * ri(s, 2, 10) + (chance(s, 0.6f) ? 1 : 0));
        p->cut_end = (uint8_t)clampi(p->cut - ri(s, 20, 70), 12, 250);
        p->transpose = (int8_t)(chance(s, 0.6f) ? -12 : -24);
        break;
    case SID1_R_PAD:
        p->wave = (uint8_t)(chance(s, 0.5f) ? PUL : pick_wave(s, b, 0));
        set_env(p, ri(s, 8, 12) + (lshift < 0 ? lshift : 0), ri(s, 9, 12), ri(s, 10, 15), ri(s, 9, 12) + (lshift > 0 ? 1 : 0));
        set_pw(p, ri(s, 1200, 2800));
        p->pw_speed = (int8_t)(1 + m * ri(s, 2, 10)); p->pw_min = (uint8_t)ri(s, 32, 96); p->pw_max = (uint8_t)ri(s, 160, 240);
        if (chance(s, 0.6f)) {
            p->flags |= SID1_PF_FILTER; p->mode = chance(s, 0.7f) ? LP : BP;
            p->cut = (uint8_t)bright_cut(s, 50, 150, b); p->res = (uint8_t)ri(s, 2, 10);
            p->cut_speed = (int8_t)((m * ri(s, 1, 3)) * (chance(s, 0.5f) ? 1 : -1)); p->cut_end = (uint8_t)bright_cut(s, 60, 200, b);
        }
        p->vib_depth = (uint8_t)(m * ri(s, 4, 15)); p->vib_speed = (uint8_t)ri(s, 6, 14); p->vib_delay = (uint8_t)ri(s, 20, 60);
        break;
    case SID1_R_PLUCK:
        p->wave = (uint8_t)pick_wave(s, b, 1);
        set_env(p, 0, ri(s, 4, 9) + lshift, ri(s, 0, 4), ri(s, 3, 8) + lshift);
        p->flags = SID1_PF_HARD;
        set_pw(p, pick_pw(s, b));
        if (chance(s, 0.6f)) {
            p->flags |= SID1_PF_FILTER; p->mode = LP;
            p->cut = (uint8_t)bright_cut(s, 120, 220, b); p->res = (uint8_t)ri(s, 2, 12);
            p->cut_speed = (int8_t)-(int)(2 + m * ri(s, 2, 12)); p->cut_end = (uint8_t)ri(s, 20, 70);
        }
        p->transpose = (int8_t)(chance(s, 0.3f) ? 12 : 0);
        break;
    case SID1_R_ARP: {
        int pool_lo = 0, pool_hi = 11, c;
        if (r->chords == SID1_CH_MAJ) { pool_lo = 0; pool_hi = 3; }
        else if (r->chords == SID1_CH_MIN) { pool_lo = 4; pool_hi = 7; }
        else if (r->chords == SID1_CH_SUS) { pool_lo = 8; pool_hi = 11; }
        c = ri(s, pool_lo, pool_hi);
        p->wave = (uint8_t)pick_wave(s, b, 1);
        set_env(p, 0, ri(s, 6, 10) + lshift, ri(s, 9, 14), ri(s, 5, 9) + lshift);
        p->flags = SID1_PF_HARD;
        set_pw(p, pick_pw(s, b));
        p->pw_speed = (int8_t)(m * ri(s, 4, 24));
        p->pw_min = (uint8_t)ri(s, 24, 80); p->pw_max = (uint8_t)ri(s, 160, 232);
        p->wt_len = CHORD_LEN[c]; p->wt_loop = 0;
        for (k = 0; k < p->wt_len; k++) { p->wt_note[k] = (uint8_t)CHORDS[c][k]; p->wt_ctl[k] = 0; }
        if (chance(s, 0.25f) && p->wt_len < 8) {               /* up and down */
            int n = p->wt_len;
            for (k = n - 2; k > 0 && p->wt_len < 8; k--) { p->wt_note[p->wt_len] = p->wt_note[k]; p->wt_ctl[p->wt_len++] = 0; }
        }
        if (chance(s, 0.3f)) { p->flags |= SID1_PF_FILTER; p->mode = LP; p->cut = (uint8_t)bright_cut(s, 100, 200, b); p->res = (uint8_t)ri(s, 0, 8); p->cut_end = p->cut; }
        break;
    }
    case SID1_R_DRUM: {
        int kind = ri(s, 0, 3);
        p->flags = SID1_PF_HARD;
        set_pw(p, 2048);
        if (kind == 0) {                                         /* kick: a click of noise, then a falling triangle */
            int top = ri(s, 48, 56);
            p->wave = TRI;
            set_env(p, 0, ri(s, 7, 9), 0, 0);
            p->wt_len = 6; p->wt_loop = 6; p->wt_abs = 0x3F;
            p->wt_ctl[0] = NOI; p->wt_note[0] = (uint8_t)ri(s, 80, 92);
            for (k = 1; k < 6; k++) { p->wt_ctl[k] = TRI; p->wt_note[k] = (uint8_t)clampi(top - (k - 1) * ri(s, 3, 6), 24, 106); }
        } else if (kind == 1) {                                  /* snare: noise and a pulse body */
            p->wave = NOI;
            set_env(p, 0, ri(s, 7, 9), 0, 0);
            p->wt_len = 4; p->wt_loop = 4; p->wt_abs = 0x0F;
            p->wt_ctl[0] = NOI; p->wt_note[0] = (uint8_t)ri(s, 90, 100);
            p->wt_ctl[1] = PUL; p->wt_note[1] = (uint8_t)ri(s, 46, 54);
            p->wt_ctl[2] = PUL; p->wt_note[2] = (uint8_t)(p->wt_note[1] - 3);
            p->wt_ctl[3] = NOI; p->wt_note[3] = (uint8_t)ri(s, 84, 96);
        } else if (kind == 2) {                                  /* hat: high noise, short */
            p->wave = NOI;
            set_env(p, 0, ri(s, 3, 6), 0, 0);
            p->wt_len = 1; p->wt_loop = 1; p->wt_abs = 0x01; p->wt_ctl[0] = NOI; p->wt_note[0] = (uint8_t)ri(s, 100, 106);
            if (chance(s, 0.4f)) { p->flags |= SID1_PF_FILTER; p->mode = HP; p->cut = (uint8_t)ri(s, 120, 200); p->cut_end = p->cut; }
        } else {                                                 /* tom: relative to the key, falling */
            p->wave = TRI;
            set_env(p, 0, ri(s, 8, 10), 0, 0);
            p->wt_len = 6; p->wt_loop = 6; p->wt_abs = 0;
            p->wt_ctl[0] = NOI; p->wt_note[0] = 24;
            for (k = 1; k < 6; k++) { p->wt_ctl[k] = TRI; p->wt_note[k] = (uint8_t)(int8_t)(-(k - 1) * 2); }
        }
        break;
    }
    case SID1_R_FX:
    default: {
        int n = ri(s, 4, 8);
        p->wave = (uint8_t)(chance(s, 0.25f) ? NOI : pick_wave(s, b, 1));
        if (p->wave == TRI && chance(s, 0.5f)) p->wave |= RING;
        if (!(p->wave & NOI) && chance(s, 0.3f)) p->wave |= SYNC;
        set_env(p, ri(s, 0, 8), ri(s, 4, 12), ri(s, 0, 12), ri(s, 4, 12) + lshift);
        set_pw(p, ri(s, 512, 3584));
        p->pw_speed = (int8_t)(ri(s, 10, 60) * (chance(s, 0.5f) ? 1 : -1));
        if (chance(s, 0.6f)) {
            p->flags |= SID1_PF_FILTER; p->mode = (uint8_t)(chance(s, 0.5f) ? LP : chance(s, 0.5f) ? BP : HP);
            p->cut = (uint8_t)bright_cut(s, 40, 220, b); p->res = (uint8_t)ri(s, 4, 15);
            p->cut_speed = (int8_t)(ri(s, 2, 20) * (chance(s, 0.5f) ? 1 : -1)); p->cut_end = (uint8_t)ri(s, 20, 230);
        }
        p->vib_depth = (uint8_t)(m * ri(s, 20, 90)); p->vib_speed = (uint8_t)ri(s, 8, 60);
        p->wt_len = (uint8_t)n; p->wt_loop = (uint8_t)ri(s, 0, n - 1);
        for (k = 0; k < n; k++) {
            static const int8_t IV[] = {0, 0, 3, 4, 5, 7, 7, 12, 12, -12, 19, 24, -5, 10};
            p->wt_note[k] = (uint8_t)IV[ri(s, 0, (int)sizeof IV - 1)];
            p->wt_ctl[k] = (uint8_t)(chance(s, 0.25f) ? NOI : chance(s, 0.3f) ? pick_wave(s, b, 0) : 0);
        }
        break;
    }
    }
}

/* blend the fresh patch n into cur by amount, keeping locked sections */
static int mixi(int a, int b, float t) { return a + (int)((float)(b - a) * t + (b >= a ? 0.5f : -0.5f)); }

int sid1_roll(sid1_patch_t *out, const sid1_patch_t *cur, const sid1_roll_t *r, uint32_t *seed)
{
    sid1_patch_t n;
    int type = r->type, k, L = r->locks;
    float t = r->amount < 0 ? 0 : r->amount > 1 ? 1 : r->amount;
    if (!*seed) *seed = 0x9E3779B9u;
    if (type < 0 || type >= SID1_R_ANY) type = ri(seed, 0, SID1_R_ANY - 1);
    fresh(&n, type, r, seed);
    *out = *cur;
    if (!(L & SID1_LOCK_OSC)) {
        int pwc = (cur->pw_hi & 15) << 8 | cur->pw_lo, pwn = (n.pw_hi & 15) << 8 | n.pw_lo;
        if (t >= 0.999f || chance(seed, t)) out->wave = n.wave;
        set_pw(out, mixi(pwc, pwn, t));
        out->pw_speed = (int8_t)mixi(cur->pw_speed, n.pw_speed, t);
        out->pw_min = (uint8_t)mixi(cur->pw_min, n.pw_min, t);
        out->pw_max = (uint8_t)mixi(cur->pw_max, n.pw_max, t);
        if (t >= 0.999f || chance(seed, t)) out->flags = (uint8_t)((out->flags & ~SID1_PF_HARD) | (n.flags & SID1_PF_HARD));
    }
    if (!(L & SID1_LOCK_ENV)) {
        out->ad = (uint8_t)(mixi(cur->ad >> 4, n.ad >> 4, t) << 4 | mixi(cur->ad & 15, n.ad & 15, t));
        out->sr = (uint8_t)(mixi(cur->sr >> 4, n.sr >> 4, t) << 4 | mixi(cur->sr & 15, n.sr & 15, t));
    }
    if (!(L & SID1_LOCK_FILTER)) {
        if (t >= 0.999f || chance(seed, t)) {
            out->flags = (uint8_t)((out->flags & ~SID1_PF_FILTER) | (n.flags & SID1_PF_FILTER));
            out->mode = n.mode;
        }
        out->res = (uint8_t)mixi(cur->res, n.res, t);
        out->cut = (uint8_t)mixi(cur->cut, n.cut, t);
        out->cut_speed = (int8_t)mixi(cur->cut_speed, n.cut_speed, t);
        out->cut_end = (uint8_t)mixi(cur->cut_end, n.cut_end, t);
    }
    if (!(L & SID1_LOCK_PITCH)) {
        if (t >= 0.999f || chance(seed, t)) out->transpose = n.transpose;
        out->fine = (int8_t)mixi(cur->fine, n.fine, t);
        out->vib_depth = (uint8_t)mixi(cur->vib_depth, n.vib_depth, t);
        out->vib_speed = (uint8_t)mixi(cur->vib_speed, n.vib_speed, t);
        out->vib_delay = (uint8_t)mixi(cur->vib_delay, n.vib_delay, t);
    }
    if (!(L & SID1_LOCK_WT) && (t >= 0.5f || chance(seed, t * 2.0f))) {   /* a wavetable is all or nothing */
        out->wt_len = n.wt_len; out->wt_loop = n.wt_loop; out->wt_abs = n.wt_abs;
        for (k = 0; k < SID1_WT_MAX; k++) { out->wt_ctl[k] = n.wt_ctl[k]; out->wt_note[k] = n.wt_note[k]; }
    }
    sid1_patch_sanitize(out, r->model);
    return type;
}

void sid1_patch_sanitize(sid1_patch_t *p, int model)
{
    int w = p->wave & 0xF0, k, pw, a, d, s, rl;
    /* a waveform always; noise alone (noise with other waves goes silent on the chip) */
    if (!w) w = PUL;
    if ((w & NOI) && (w & 0x70)) w = NOI;
    p->wave = (uint8_t)(w | (p->wave & 0x0E));
    p->wave &= (uint8_t)~0x08;                                 /* never the test bit: it silences the oscillator */
    if ((p->wave & RING) && !(w & TRI)) p->wave &= (uint8_t)~RING;   /* ring mod only acts on triangle */
    if (w & NOI) p->wave &= (uint8_t)~(RING | SYNC);
    /* pulse width: never 0 or full (silent), the sweep's limits in order */
    pw = clampi((p->pw_hi & 15) << 8 | p->pw_lo, 128, 3968);
    set_pw(p, pw);
    if (p->pw_min < 8) p->pw_min = 8;
    if (p->pw_max > 248) p->pw_max = 248;
    if (p->pw_min >= p->pw_max) { p->pw_min = 16; p->pw_max = 240; }
    /* envelope: something to hear */
    a = p->ad >> 4; d = p->ad & 15; s = p->sr >> 4; rl = p->sr & 15;
    if (s < 2 && d < 3) d = 3;                                 /* no sustain: give the decay some time */
    if (w == TRI && s < 4 && d < 6) d = 6;
    if (w == NOI && s < 2 && d < 4) d = 4;                     /* a hit of noise needs a few ms to be heard */                     /* a triangle is quiet: a short one needs a longer decay */
    if (s == 0 && a > 9) a = 9;                                /* a long attack with nothing after it is a click */
    set_env(p, a, d, s, rl);
    /* filter: a mode when on, cutoff where the mode passes sound, resonance the chip can take */
    if (p->flags & SID1_PF_FILTER) {
        int m = p->mode & 0x70, all = w, j;
        for (j = 0; j < p->wt_len && j < SID1_WT_MAX; j++) all |= p->wt_ctl[j] & 0xF0;
        if (!m) m = LP;
        /* high-pass and band-pass take most of a triangle (few harmonics) away, the 8580's most of all:
         * high-pass only for noise, band-pass not on a sound with triangle in it */
        if ((m & HP) && (all & 0x70)) m = (all & TRI) ? LP : (m & ~HP) ? (m & ~HP) : BP;
        if ((m & BP) && (all & TRI) && !(m & LP)) m = LP;
        if (model == SID_8580) {                               /* its filter is steeper: keep the sound in the pass band */
            if ((m & BP) && !(m & LP) && (all & 0x70)) m = LP;
            if (m == HP) { if (p->cut > 110) p->cut = 110; if (p->cut_end > 110) p->cut_end = 110; }
        }
        p->mode = (uint8_t)m;
        if (m == LP) { if (p->cut < 16) p->cut = 16; if (p->cut_end < 12) p->cut_end = 12; }
        if (m == HP) { if (p->cut > 220) p->cut = 220; if (p->cut_end > 220) p->cut_end = 220; }
        if (m == BP) { p->cut = (uint8_t)clampi(p->cut, 24, 230); p->cut_end = (uint8_t)clampi(p->cut_end, 24, 230); }
        if (model == SID_8580 && p->res > 12) p->res = 12;
    } else if (!(p->mode & 0x70)) p->mode = LP;
    /* pitch */
    p->transpose = (int8_t)clampi(p->transpose, -36, 36);
    p->fine = (int8_t)clampi(p->fine, -100, 100);
    /* wavetable: length and loop in range, notes playable */
    if (p->wt_len > SID1_WT_MAX) p->wt_len = SID1_WT_MAX;
    if (p->wt_len && p->wt_loop > p->wt_len) p->wt_loop = p->wt_len;
    for (k = 0; k < SID1_WT_MAX; k++) {
        int c = p->wt_ctl[k] & 0xF0;
        if ((c & NOI) && (c & 0x70)) c = NOI;
        p->wt_ctl[k] = (uint8_t)c;
        if (p->wt_abs >> k & 1) p->wt_note[k] = (uint8_t)clampi(p->wt_note[k], 24, 106);
        else p->wt_note[k] = (uint8_t)(int8_t)clampi((int8_t)p->wt_note[k], -36, 36);
    }
}
