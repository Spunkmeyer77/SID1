/* SPDX-License-Identifier: GPL-3.0-only */
/* SID1 engine. The player is SID-1's (putchdev/sid-1, firmware/src/sid1.c) for one patch on six voices: wavetable,
 * pulse sweep, filter sweep, vibrato and hard restart, run 50 times a second, now clocked by the sample count at any
 * host rate. Register writes go straight to the chips (one thread). */
#include "sid1_engine.h"
#include <string.h>

#define FRAME_HZ 50.0
#define SETTLE_S 0.120                           /* seconds silent after a model change (the 6581's DC thump) */
#define DUCK_S 0.030                             /* seconds of fade-in after the filter routing changes (its DC step) */

static const uint16_t FREQ[108] = {              /* MIDI note -> frequency register at the PAL clock */
    139, 147, 156, 166, 175, 186, 197, 209, 221, 234, 248, 263, 278, 295, 313, 331,
    351, 372, 394, 417, 442, 468, 496, 526, 557, 590, 625, 662, 702, 743, 788, 834,
    884, 937, 992, 1051, 1114, 1180, 1250, 1325, 1403, 1487, 1575, 1669, 1768, 1873, 1985, 2103,
    2228, 2360, 2500, 2649, 2807, 2973, 3150, 3338, 3536, 3746, 3969, 4205, 4455, 4720, 5001, 5298,
    5613, 5947, 6300, 6675, 7072, 7493, 7938, 8410, 8910, 9440, 10001, 10596, 11226, 11894, 12601, 13350,
    14144, 14985, 15876, 16820, 17820, 18880, 20003, 21192, 22452, 23787, 25202, 26700, 28288, 29970, 31752, 33640,
    35641, 37760, 40005, 42384, 44904, 47574, 50403, 53401, 56576, 59940, 63504, 65535,
};

#define WT(...) {__VA_ARGS__}
const sid1_patch_t SID1_FACTORY[] = {           /* SID-1's factory patches */
    {"PWM LEAD", 0x08, 0xA9, 0x40, SID1_PF_HARD, 0x08, 0x00, 24, 0x10, 0xE0, 0x10, 0, 0, 0, 0, 0, 0, 12, 20, 25,
     0, 0, 0, WT(0), WT(0)},
    {"SAW BASS", 0x08, 0x8A, 0x20, SID1_PF_FILTER | SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 10, 0x30, -6, 0x10, -12, 0,
     0, 0, 0, 0, 0, 0, WT(0), WT(0)},
    {"BRASS", 0x28, 0xA8, 0x20, SID1_PF_FILTER | SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 4, 0x10, 12, (int8_t)0x80, 0, 0,
     18, 18, 20, 0, 0, 0, WT(0), WT(0)},
    {"SWEEP PAD", 0x8A, 0xCA, 0x40, SID1_PF_FILTER, 0x04, 0x00, 6, 0x20, 0xC0, 0x10, 12, 0x08, 2, (int8_t)0xA0, 0, 0,
     0, 0, 0, 0, 0, 0, WT(0), WT(0)},
    {"FLUTE", 0x48, 0xA8, 0x10, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 20, 16, 30,
     0, 0, 0, WT(0), WT(0)},
    {"ORGAN", 0x08, 0xF6, 0x40, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, WT(0), WT(0)},
    {"BELL", 0x09, 0x09, 0x50, 0, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 12, 0, 0, 0, 0,
     0, 0, 0, WT(0), WT(0)},
    {"THIN BASS", 0x09, 0x6A, 0x40, SID1_PF_HARD, 0x02, 0x00, 4, 0x02, 0x30, 0x10, 0, 0, 0, 0, -12, 0, 0, 0, 0,
     0, 0, 0, WT(0), WT(0)},
    {"NOISE LEAD", 0x08, 0xA9, 0x40, SID1_PF_HARD, 0x06, 0x00, 16, 0x20, 0xD0, 0x10, 0, 0, 0, 0, 0, 0, 10, 24, 20,
     2, 1, 0, WT(0x81, 0), WT(24, 0)},
    {"ARP MAJOR", 0x08, 0xA9, 0x40, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     3, 0, 0, WT(0, 0, 0), WT(0, 4, 7)},
    {"ARP MINOR", 0x08, 0xA9, 0x40, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     3, 0, 0, WT(0, 0, 0), WT(0, 3, 7)},
    {"KICK", 0x08, 0x00, 0x11, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     6, 6, 0x3F, WT(0x81, 0x11, 0x11, 0x11, 0x11, 0x11), WT(84, 52, 45, 40, 36, 33)},
    {"SNARE", 0x09, 0x00, 0x81, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     4, 4, 0x0F, WT(0x81, 0x41, 0x41, 0x81), WT(96, 50, 47, 90)},
    {"HIHAT", 0x05, 0x00, 0x81, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     1, 1, 0x01, WT(0x81), WT(106)},
    {"TOM", 0x0A, 0x00, 0x11, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     6, 6, 0, WT(0x81, 0x11, 0x11, 0x11, 0x11, 0x11), WT(24, 0, (uint8_t)-2, (uint8_t)-4, (uint8_t)-6, (uint8_t)-8)},
    {"ZAP", 0x09, 0x00, 0x40, SID1_PF_HARD, 0x08, 0x00, 0, 0, 0, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     8, 8, 0, WT(0, 0, 0, 0, 0, 0, 0, 0), WT(36, 30, 24, 18, 12, 6, 0, (uint8_t)-6)},
};
const int SID1_NFACTORY = (int)(sizeof SID1_FACTORY / sizeof SID1_FACTORY[0]);

void sid1_patch_init(sid1_patch_t *p)
{
    memset(p, 0, sizeof *p);
    memcpy(p->name, "INIT", 5);
    p->ad = 0x08; p->sr = 0xA9; p->wave = 0x20; p->pw_hi = 0x08; p->mode = 0x10; p->cut = 0x80; p->cut_end = 0x80;
}

/* ---- registers */
static void voice_reg(sid1_engine_t *e, int v, int reg, uint32_t val) { sid_write(&e->chip[v / 3], (uint32_t)((v % 3) * 7 + reg), val & 0xFFu); }

static uint32_t pitch(const sid1_engine_t *e, const sid1_voice_t *v)
{
    const sid1_patch_t *p = &e->p;
    int32_t c, n, frac;
    if (p->wt_len && (p->wt_abs >> v->pos & 1u)) c = (int32_t)p->wt_note[v->pos] * 100 + p->fine;
    else {
        c = ((int32_t)v->note + p->transpose + (p->wt_len ? (int8_t)p->wt_note[v->pos] : 0)) * 100 + p->fine;
        if (p->vib_depth && v->frames >= p->vib_delay) {
            int32_t ph = v->vib_phase, tri = ph < 128 ? ph - 64 : 191 - ph;
            c += tri * p->vib_depth / 64;
        }
        c += e->bend * e->bend_range * 100 / 8192;
    }
    if (c < 0) c = 0;
    if (c > 106 * 100 + 99) c = 106 * 100 + 99;
    n = c / 100;
    frac = c % 100;
    return FREQ[n] + (uint32_t)(((int32_t)FREQ[n + 1] - FREQ[n]) * frac / 100);
}

static void voice_update(sid1_engine_t *e, int k)
{
    sid1_voice_t *v = &e->vc[k];
    const sid1_patch_t *p = &e->p;
    int32_t ctl = ((p->wt_len && p->wt_ctl[v->pos] ? p->wt_ctl[v->pos] : p->wave) & 0xF0) | (p->wave & 0x0E);
    int32_t f = (int32_t)pitch(e, v);
    ctl |= v->on;
    if (f != v->freq) { voice_reg(e, k, 0, (uint32_t)f); voice_reg(e, k, 1, (uint32_t)f >> 8); v->freq = f; }
    if (v->pw != v->pwr) { voice_reg(e, k, 2, v->pw); voice_reg(e, k, 3, v->pw >> 8u); v->pwr = v->pw; }
    if (ctl != v->ctl) { voice_reg(e, k, 4, (uint32_t)ctl); v->ctl = ctl; }
}

static void filter_update(sid1_engine_t *e, int c)
{
    const sid1_patch_t *p = &e->p;
    int32_t route = (p->flags & SID1_PF_FILTER) ? 7 : 0;
    int32_t r17 = (int32_t)((uint32_t)p->res << 4 | (uint32_t)route), r18 = (p->mode & 0x70) | 15;
    if (e->flt[c].cut != e->flt[c].cutr) {
        sid_write(&e->chip[c], 0x15, (uint32_t)e->flt[c].cut & 7u);
        sid_write(&e->chip[c], 0x16, (uint32_t)e->flt[c].cut >> 3);
        e->flt[c].cutr = e->flt[c].cut;
    }
    if ((r17 & 7) != (e->flt[c].reg17 & 7) && e->flt[c].reg17 >= 0) e->duck = (int)(e->sr * DUCK_S);
    if (r17 != e->flt[c].reg17) { sid_write(&e->chip[c], 0x17, (uint32_t)r17); e->flt[c].reg17 = r17; }
    if (r18 != e->flt[c].reg18) { sid_write(&e->chip[c], 0x18, (uint32_t)r18); e->flt[c].reg18 = r18; }
}

static void voice_start(sid1_engine_t *e, int k)
{
    voice_reg(e, k, 5, e->p.ad);
    voice_reg(e, k, 6, e->p.sr);
    e->vc[k].ctl = -1;
    voice_update(e, k);
}

static void voice_on(sid1_engine_t *e, int k, int note)
{
    sid1_voice_t *v = &e->vc[k];
    const sid1_patch_t *p = &e->p;
    v->note = (uint8_t)note;
    v->pos = 0;
    v->frames = 0;
    v->vib_phase = 64;
    v->pw = (uint16_t)((p->pw_hi & 15u) << 8 | p->pw_lo);
    v->pw_step = p->pw_speed;
    v->t = ++e->clock;
    v->on = 1;
    if (p->flags & SID1_PF_FILTER) { e->flt[k / 3].on = 1; e->flt[k / 3].cut = p->cut << 3; }
    filter_update(e, k / 3);
    if ((p->flags & SID1_PF_HARD) && v->active) {
        voice_reg(e, k, 5, 0);
        voice_reg(e, k, 6, 0);
        voice_reg(e, k, 4, 0x08);
        v->ctl = 0x08;
        v->hr = 1;
    } else {
        v->hr = 0;
        voice_start(e, k);
    }
    v->active = 1;
}

static void voice_off(sid1_engine_t *e, int k)
{
    e->vc[k].on = 0;
    e->vc[k].t = ++e->clock;
    if (!e->vc[k].hr) voice_update(e, k);
}

static void frame(sid1_engine_t *e)
{
    int k, c;
    const sid1_patch_t *p = &e->p;
    for (k = 0; k < 6; k++) {
        sid1_voice_t *v = &e->vc[k];
        int32_t lo = p->pw_min * 16, hi = p->pw_max * 16;
        if (!v->active) continue;
        if (v->hr) { v->hr = 0; voice_start(e, k); continue; }
        v->frames++;
        if (p->wt_len) {
            if (++v->pos >= p->wt_len) v->pos = (uint8_t)(p->wt_loop < p->wt_len ? p->wt_loop : p->wt_len - 1u);
        } else v->pos = 0;
        if (v->pw_step) {
            int32_t w = (int32_t)v->pw + v->pw_step;
            if (w >= hi || w > 4095) { w = hi < 4095 ? hi : 4095; v->pw_step = (int16_t)-(v->pw_step < 0 ? -v->pw_step : v->pw_step); }
            if (w <= lo || w < 0) { w = lo > 0 ? lo : 0; v->pw_step = (int16_t)(v->pw_step < 0 ? -v->pw_step : v->pw_step); }
            v->pw = (uint16_t)w;
        }
        if (p->vib_depth && v->frames >= p->vib_delay) v->vib_phase = (uint8_t)(v->vib_phase + p->vib_speed);
        voice_update(e, k);
        if (!v->on && v->frames > 2000u) v->active = 0;
    }
    for (c = 0; c < 2; c++) {
        int32_t end = p->cut_end << 3, s = p->cut_speed;
        if (!e->flt[c].on) continue;
        if (s > 0 && e->flt[c].cut < end) e->flt[c].cut = e->flt[c].cut + s < end ? e->flt[c].cut + s : end;
        if (s < 0 && e->flt[c].cut > end) e->flt[c].cut = e->flt[c].cut + s > end ? e->flt[c].cut + s : end;
        filter_update(e, c);
    }
}

static int voice_pick(sid1_engine_t *e, int note)   /* the same note's voice; else free, then oldest */
{
    int k, best = 0;
    uint32_t cost, best_cost = 99;
    for (k = 0; k < 6; k++) {
        const sid1_voice_t *v = &e->vc[k];
        if (v->on && v->note == note) return k;
        cost = v->on ? 4u : 0u;
        if (cost < best_cost || (cost == best_cost && (int32_t)(v->t - e->vc[best].t) < 0)) { best = k; best_cost = cost; }
    }
    return best;
}

/* ---- public */
void sid1_set_rate(sid1_engine_t *e, double sr)
{
    if (sr < 8000.0) sr = 44100.0;
    e->sr = sr;
    e->cps = (int32_t)((double)SID_CLOCK_PAL / (sr * (e->oversample ? 2.0 : 1.0)) * 65536.0 + 0.5);
    e->frame_len = sr / FRAME_HZ;
}

void sid1_init(sid1_engine_t *e, double sr)
{
    int k;
    memset(e, 0, sizeof *e);
    e->model = SID_6581;
    sid_init(&e->chip[0], e->model);
    sid_init(&e->chip[1], e->model);
    for (k = 0; k < 6; k++) { e->vc[k].ctl = e->vc[k].freq = e->vc[k].pwr = -1; }
    for (k = 0; k < 2; k++) { e->flt[k].cutr = e->flt[k].reg17 = e->flt[k].reg18 = -1; }
    e->bend_range = 2;
    e->gain = 1.0f;
    sid1_patch_init(&e->p);
    sid1_set_rate(e, sr);
    e->settle = (int)(e->sr * SETTLE_S);
    filter_update(e, 0);
    filter_update(e, 1);
}

void sid1_set_model(sid1_engine_t *e, int model)
{
    if (model == e->model) return;
    e->model = model;
    sid_set_model(&e->chip[0], model);
    sid_set_model(&e->chip[1], model);
    e->settle = (int)(e->sr * SETTLE_S);
}

void sid1_set_oversample(sid1_engine_t *e, int on) { e->oversample = on ? 1 : 0; sid1_set_rate(e, e->sr); }

void sid1_set_play_mode(sid1_engine_t *e, int mode) { if (mode != e->play_mode) { sid1_all_off(e); e->play_mode = mode; } }

void sid1_set_patch(sid1_engine_t *e, const sid1_patch_t *p)
{
    int k, c;
    e->p = *p;
    e->p.name[11] = 0;
    for (k = 0; k < 6; k++)
        if (e->vc[k].active && !e->vc[k].hr) { voice_reg(e, k, 5, p->ad); voice_reg(e, k, 6, p->sr); voice_update(e, k); }
    for (c = 0; c < 2; c++) {
        if (!(p->flags & SID1_PF_FILTER)) e->flt[c].on = 0;
        else if (!e->flt[c].on) { e->flt[c].on = 1; e->flt[c].cut = p->cut << 3; }
        filter_update(e, c);
    }
}

static void mono_play(sid1_engine_t *e, int note, int retrig)
{
    sid1_voice_t *v = &e->vc[0];
    if (retrig || !v->on) voice_on(e, 0, note);
    else { v->note = (uint8_t)note; voice_update(e, 0); }   /* legato */
}

void sid1_note_on(sid1_engine_t *e, int note, int vel)
{
    int i;
    if (note < 0 || note > 127) return;
    if (vel <= 0) { sid1_note_off(e, note); return; }
    if (e->play_mode == SID1_MONO) {
        for (i = 0; i < e->nheld; i++) if (e->held[i] == note) { memmove(&e->held[i], &e->held[i + 1], (size_t)(e->nheld - i - 1)); e->nheld--; break; }
        if (e->nheld < 128) e->held[e->nheld++] = (uint8_t)note;
        mono_play(e, note, e->nheld == 1);
        return;
    }
    voice_on(e, voice_pick(e, note), note);
}

void sid1_note_off(sid1_engine_t *e, int note)
{
    int k, i;
    if (e->play_mode == SID1_MONO) {
        for (i = 0; i < e->nheld; i++) if (e->held[i] == note) { memmove(&e->held[i], &e->held[i + 1], (size_t)(e->nheld - i - 1)); e->nheld--; break; }
        if (e->nheld) { if (e->vc[0].note == note) mono_play(e, e->held[e->nheld - 1], 0); }
        else if (e->vc[0].on) voice_off(e, 0);
        return;
    }
    for (k = 0; k < 6; k++) if (e->vc[k].on && e->vc[k].note == note) voice_off(e, k);
}

void sid1_all_off(sid1_engine_t *e)
{
    int k;
    e->nheld = 0;
    for (k = 0; k < 6; k++) if (e->vc[k].on) voice_off(e, k);
}

void sid1_bend(sid1_engine_t *e, int b)
{
    int k;
    e->bend = (int16_t)(b - 8192);
    for (k = 0; k < 6; k++) if (e->vc[k].active && !e->vc[k].hr) voice_update(e, k);
}

void sid1_set_bend_range(sid1_engine_t *e, int s) { e->bend_range = (uint8_t)(s < 0 ? 0 : s > 24 ? 24 : s); }

#define CHUNK 256
static void chip_render(sid1_engine_t *e, int c, int16_t *out, int m)
{
    int made = 0;
    while (made < m) {
        made += sid_render(&e->chip[c], &e->owed[c], e->cps, out + made, m - made, 1);
        if (made < m) e->owed[c] += 1024;
    }
}

void sid1_render(sid1_engine_t *e, float *out, int n)
{
    int16_t b0[2 * CHUNK + 4], b1[2 * CHUNK + 4];
    int os = e->oversample ? 2 : 1;
    const float scale = (181.0f / 256.0f) / 32768.0f;
    while (n > 0) {
        int m = n < CHUNK ? n : CHUNK, i;
        double left = e->frame_len - e->frame_pos;
        if (left <= 0.0) { frame(e); e->frame_pos -= e->frame_len; continue; }
        if ((double)m > left) m = (int)left < 1 ? 1 : (int)left;
        chip_render(e, 0, b0, m * os);
        chip_render(e, 1, b1, m * os);
        for (i = 0; i < m; i++) {
            int32_t v;
            if (os == 2) {
                int32_t a = e->hist[0], b = e->hist[1];
                e->hist[0] = b0[2 * i] + b1[2 * i];
                e->hist[1] = b0[2 * i + 1] + b1[2 * i + 1];
                v = (a + 3 * b + 3 * e->hist[0] + e->hist[1]) >> 3;
            } else v = b0[i] + b1[i];
            if (e->settle > 0) { e->settle--; out[i] = 0.0f; continue; }
            out[i] = (float)v * scale * e->gain;
            if (e->duck > 0) {                  /* silent for the first half, then a linear fade-in */
                int len = (int)(e->sr * DUCK_S), d = e->duck--;
                out[i] *= d > len / 2 ? 0.0f : 1.0f - (float)d / (float)(len / 2);
            }
        }
        out += m;
        n -= m;
        e->frame_pos += m;
    }
}
