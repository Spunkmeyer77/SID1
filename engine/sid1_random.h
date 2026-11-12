/* SPDX-License-Identifier: GPL-3.0-only */
/* SID1 randomizer: new patches by rules, not by dice alone. A roll builds a fresh patch for a sound type inside
 * that type's ranges, steered by the character controls, blends it with the current patch by AMOUNT, keeps the
 * locked sections, then makes it valid for the chip (nothing silent, nothing broken). */
#ifndef SID1_RANDOM_H
#define SID1_RANDOM_H
#include <stdint.h>
#include "sid1_engine.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { SID1_R_LEAD, SID1_R_BASS, SID1_R_PAD, SID1_R_PLUCK, SID1_R_ARP, SID1_R_DRUM, SID1_R_FX, SID1_R_ANY, SID1_R_NTYPES };
enum { SID1_LOCK_OSC = 1, SID1_LOCK_ENV = 2, SID1_LOCK_FILTER = 4, SID1_LOCK_PITCH = 8, SID1_LOCK_WT = 16 };
enum { SID1_CH_MAJ, SID1_CH_MIN, SID1_CH_SUS, SID1_CH_ANY };

typedef struct {
    int type;          /* SID1_R_* */
    float amount;      /* 0 nudge .. 1 new */
    float bright;      /* -1 dark .. 1 bright */
    float motion;      /* 0 still .. 1 moving */
    float length;      /* -1 short .. 1 long */
    int locks;         /* SID1_LOCK_* */
    int chords;        /* SID1_CH_* */
    int model;         /* SID_6581 / SID_8580: the chip it is rolled for */
} sid1_roll_t;

/* out = a roll from cur; *seed advances. Returns the type actually used (ANY picks one). */
int sid1_roll(sid1_patch_t *out, const sid1_patch_t *cur, const sid1_roll_t *r, uint32_t *seed);
void sid1_patch_sanitize(sid1_patch_t *p, int model);
extern const char *const SID1_RTYPE_NAMES[SID1_R_NTYPES];

#ifdef __cplusplus
}
#endif
#endif
