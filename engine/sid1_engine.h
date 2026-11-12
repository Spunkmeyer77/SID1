/* SPDX-License-Identifier: GPL-3.0-only */
/* SID1 engine: two reSID 0.16 chips (core/sid.c) played as a six-voice synth by a C64-style patch player
 * (50 frames a second). Ported from putchdev/sid-1's firmware (sid1.c), with the FM-1 hardware removed.
 * Plain C, no host code: the Max external and the JUCE plugin both wrap it. */
#ifndef SID1_ENGINE_H
#define SID1_ENGINE_H
#include <stdint.h>
#include "../core/sid.h"

#ifdef __cplusplus
extern "C" {
#endif

#define SID1_WT_MAX 8
enum { SID1_PF_FILTER = 1, SID1_PF_HARD = 2 };   /* through the filter; hard restart */

/* A patch, byte for byte as SID-1's patch_t (so the page's patches and .sid imports carry over) */
typedef struct {
    char name[12];
    uint8_t ad, sr;          /* attack/decay and sustain/release registers */
    uint8_t wave;            /* control register without gate: waveform bits 7-4, ring 2, sync 1, test 3 */
    uint8_t flags;           /* SID1_PF_* */
    uint8_t pw_hi, pw_lo;    /* start pulse width, 12 bits */
    int8_t pw_speed;         /* per frame; bounces between pw_min and pw_max (x16) */
    uint8_t pw_min, pw_max;
    uint8_t mode;            /* filter mode: 0x10 LP, 0x20 BP, 0x40 HP (OR-able) */
    uint8_t res;             /* 0..15 */
    uint8_t cut;             /* start cutoff, top 8 of 11 bits */
    int8_t cut_speed;        /* per frame (x8), until cut_end */
    uint8_t cut_end;
    int8_t transpose, fine;  /* semitones, cents */
    uint8_t vib_delay, vib_speed, vib_depth;   /* frames; 256/speed frames a cycle; cents */
    uint8_t wt_len, wt_loop; /* wavetable steps (0 none); loop step (>= len: hold last) */
    uint8_t wt_abs;          /* bit k: step k's note is absolute */
    uint8_t wt_ctl[SID1_WT_MAX];
    uint8_t wt_note[SID1_WT_MAX];
} sid1_patch_t;

enum { SID1_POLY, SID1_MONO };

typedef struct {
    uint8_t note, on, active, hr;
    uint8_t pos, vib_phase;
    uint16_t frames, pw;
    int16_t pw_step;
    uint32_t t;
    int32_t ctl, freq, pwr;
} sid1_voice_t;

typedef struct {
    sid_t chip[2];
    int32_t owed[2];
    sid1_voice_t vc[6];
    struct { int on; int32_t cut, cutr, reg17, reg18; } flt[2];
    sid1_patch_t p;
    int16_t bend;            /* -8192..8191 */
    uint8_t bend_range;      /* semitones */
    int model, oversample, play_mode;
    double sr;               /* host sample rate */
    int32_t cps;             /* chip cycles a (oversampled) sample, Q16 */
    double frame_len, frame_pos;   /* samples a 50 Hz frame; samples since the last */
    uint32_t clock;          /* note counter, for oldest-voice stealing */
    int32_t hist[2];
    int settle, duck;
    float gain;
    uint8_t held[128];       /* mono: the keys held, in order */
    int nheld;
} sid1_engine_t;

void sid1_init(sid1_engine_t *e, double sample_rate);
void sid1_set_rate(sid1_engine_t *e, double sample_rate);
void sid1_set_model(sid1_engine_t *e, int model);           /* SID_6581 / SID_8580 */
void sid1_set_oversample(sid1_engine_t *e, int on);
void sid1_set_play_mode(sid1_engine_t *e, int mode);        /* SID1_POLY / SID1_MONO */
void sid1_set_patch(sid1_engine_t *e, const sid1_patch_t *p);   /* sounding notes follow */
void sid1_note_on(sid1_engine_t *e, int note, int vel);     /* vel 0 = off */
void sid1_note_off(sid1_engine_t *e, int note);
void sid1_all_off(sid1_engine_t *e);
void sid1_bend(sid1_engine_t *e, int bend14);               /* 0..16383, 8192 centre */
void sid1_set_bend_range(sid1_engine_t *e, int semis);
void sid1_render(sid1_engine_t *e, float *out, int n);      /* mono, adds nothing: writes n samples */

/* factory patches */
extern const sid1_patch_t SID1_FACTORY[];
extern const int SID1_NFACTORY;
void sid1_patch_init(sid1_patch_t *p);                      /* the "INIT" patch */

#ifdef __cplusplus
}
#endif
#endif
