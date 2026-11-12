/* SPDX-License-Identifier: GPL-3.0-only */
/* sid1~ : two MOS SID chips (reSID 0.16) as a six-voice synth, for Max for Live.
 *
 * Messages (left inlet)
 *   note <pitch> <velocity>        velocity 0 = note off (also: a 2-element list)
 *   bend <0..16383>                8192 = centre
 *   bendrange <semitones>          0..24
 *   model <0|1>                    0 = 6581, 1 = 8580
 *   oversample <0|1>               2x oversampling
 *   mode <0|1>                     0 = poly (6 voices), 1 = mono (legato)
 *   gain <float>                   output gain (linear)
 *   panic                          all notes off
 *   set <field> <value>            edit one field of the current patch (see FIELDS below)
 *   set wtctl|wtnote <step> <v>    edit a wavetable step
 *   name <symbol>                  rename the current patch
 *   patch <name> <38 ints>         load a whole patch (the bytes after the name, as sid1_patch_t)
 *   factory <0..n-1>               load a factory patch (then dumps it)
 *   dump                           output the current patch
 *   nfactory                       output the number of factory patches
 *
 * Outlets: signal (mono, the two chips mixed), then info:
 *   patch <name> <38 ints>, then one "<field> <value>" per field, "name <sym>", "nfactory <n>", "factoryname <i> <sym>"
 *
 * Threading: messages edit a copy of the patch on the main/scheduler thread and post it, with notes and settings,
 * through a lock-free queue the audio thread empties at the start of each vector. */
#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"
#include "ext_critical.h"
#include "../../engine/sid1_engine.h"
#include <string.h>

#define QLEN 512u                                /* power of two */
#define PATCH_BYTES ((long)(sizeof(sid1_patch_t) - 12))

enum { EV_NOTE, EV_BEND, EV_BENDRANGE, EV_MODEL, EV_OS, EV_MODE, EV_GAIN, EV_PANIC, EV_PATCH };
typedef struct { int type, a, b; float f; sid1_patch_t p; } ev_t;

typedef struct _sid1 {
    t_pxobject ob;
    void *info;
    sid1_engine_t *e;                            /* audio thread's */
    sid1_patch_t p;                              /* main thread's copy */
    ev_t q[QLEN];
    volatile unsigned int qw, qr;
    double sr;
    float *buf;
    long buflen;
} t_sid1;

static t_class *sid1_class;

/* ---- queue: one writer (Max's threads, serialised by a critical section), one reader (audio) */
static void push(t_sid1 *x, const ev_t *ev)
{
    critical_enter(0);
    if (x->qw - x->qr < QLEN) {
        x->q[x->qw & (QLEN - 1)] = *ev;
        ATOMIC_INCREMENT_BARRIER((t_int32_atomic *)&x->qw);
    }
    critical_exit(0);
}
static void push3(t_sid1 *x, int type, int a, int b, float f) { ev_t ev; ev.type = type; ev.a = a; ev.b = b; ev.f = f; push(x, &ev); }
static void push_patch(t_sid1 *x) { ev_t ev; ev.type = EV_PATCH; ev.a = ev.b = 0; ev.f = 0; ev.p = x->p; push(x, &ev); }

static void drain(t_sid1 *x)
{
    while (x->qr != x->qw) {
        const ev_t *ev = &x->q[x->qr & (QLEN - 1)];
        switch (ev->type) {
        case EV_NOTE: sid1_note_on(x->e, ev->a, ev->b); break;
        case EV_BEND: sid1_bend(x->e, ev->a); break;
        case EV_BENDRANGE: sid1_set_bend_range(x->e, ev->a); break;
        case EV_MODEL: sid1_set_model(x->e, ev->a ? SID_8580 : SID_6581); break;
        case EV_OS: sid1_set_oversample(x->e, ev->a); break;
        case EV_MODE: sid1_set_play_mode(x->e, ev->a ? SID1_MONO : SID1_POLY); break;
        case EV_GAIN: x->e->gain = ev->f; break;
        case EV_PANIC: sid1_all_off(x->e); break;
        case EV_PATCH: sid1_set_patch(x->e, &ev->p); break;
        }
        ATOMIC_INCREMENT_BARRIER((t_int32_atomic *)&x->qr);
    }
}

/* ---- fields: name, get, set (clamped) */
typedef struct { const char *name; int lo, hi; } field_t;
static const field_t FIELDS[] = {
    {"attack", 0, 15}, {"decay", 0, 15}, {"sustain", 0, 15}, {"release", 0, 15},
    {"wave", 0, 15},                             /* waveform bits: 1 tri, 2 saw, 4 pulse, 8 noise (combinations allowed) */
    {"ring", 0, 1}, {"sync", 0, 1}, {"filter", 0, 1}, {"hard", 0, 1},
    {"pw", 0, 4095}, {"pwspeed", -128, 127}, {"pwmin", 0, 255}, {"pwmax", 0, 255},
    {"fmode", 0, 7},                             /* filter mode bits: 1 LP, 2 BP, 4 HP */
    {"res", 0, 15}, {"cut", 0, 255}, {"cutspeed", -128, 127}, {"cutend", 0, 255},
    {"transpose", -48, 48}, {"fine", -100, 100},
    {"vibdelay", 0, 255}, {"vibspeed", 0, 255}, {"vibdepth", 0, 255},
    {"wtlen", 0, SID1_WT_MAX}, {"wtloop", 0, SID1_WT_MAX}, {"wtabs", 0, 255},
    {"tri", 0, 1}, {"saw", 0, 1}, {"pul", 0, 1}, {"noi", 0, 1},   /* single bits of wave, for buttons */
    {"lp", 0, 1}, {"bp", 0, 1}, {"hp", 0, 1},                     /* single bits of fmode */
};
/* wavetable step waveform as a menu index: none, TRI, SAW, PUL, NOI, S+T, P+T, P+S, P+S+T */
static const uint8_t WTWAVE[9] = {0, 1, 2, 4, 8, 3, 5, 6, 7};
#define NFIELDS ((int)(sizeof FIELDS / sizeof FIELDS[0]))

static int field_get(const sid1_patch_t *p, int i)
{
    switch (i) {
    case 0: return p->ad >> 4; case 1: return p->ad & 15; case 2: return p->sr >> 4; case 3: return p->sr & 15;
    case 4: return p->wave >> 4; case 5: return (p->wave >> 2) & 1; case 6: return (p->wave >> 1) & 1;
    case 7: return p->flags & SID1_PF_FILTER ? 1 : 0; case 8: return p->flags & SID1_PF_HARD ? 1 : 0;
    case 9: return (p->pw_hi & 15) << 8 | p->pw_lo; case 10: return p->pw_speed; case 11: return p->pw_min; case 12: return p->pw_max;
    case 13: return (p->mode >> 4) & 7; case 14: return p->res; case 15: return p->cut; case 16: return p->cut_speed; case 17: return p->cut_end;
    case 18: return p->transpose; case 19: return p->fine;
    case 20: return p->vib_delay; case 21: return p->vib_speed; case 22: return p->vib_depth;
    case 23: return p->wt_len; case 24: return p->wt_loop; case 25: return p->wt_abs;
    case 26: case 27: case 28: case 29: return (p->wave >> (4 + i - 26)) & 1;
    case 30: case 31: case 32: return (p->mode >> (4 + i - 30)) & 1;
    }
    return 0;
}

static void field_set(sid1_patch_t *p, int i, int v)
{
    if (v < FIELDS[i].lo) v = FIELDS[i].lo;
    if (v > FIELDS[i].hi) v = FIELDS[i].hi;
    switch (i) {
    case 0: p->ad = (uint8_t)(v << 4 | (p->ad & 15)); break;
    case 1: p->ad = (uint8_t)((p->ad & 0xF0) | v); break;
    case 2: p->sr = (uint8_t)(v << 4 | (p->sr & 15)); break;
    case 3: p->sr = (uint8_t)((p->sr & 0xF0) | v); break;
    case 4: p->wave = (uint8_t)(v << 4 | (p->wave & 0x0F)); break;
    case 5: p->wave = (uint8_t)((p->wave & ~0x04) | (v << 2)); break;
    case 6: p->wave = (uint8_t)((p->wave & ~0x02) | (v << 1)); break;
    case 7: p->flags = (uint8_t)((p->flags & ~SID1_PF_FILTER) | (v ? SID1_PF_FILTER : 0)); break;
    case 8: p->flags = (uint8_t)((p->flags & ~SID1_PF_HARD) | (v ? SID1_PF_HARD : 0)); break;
    case 9: p->pw_hi = (uint8_t)(v >> 8); p->pw_lo = (uint8_t)(v & 255); break;
    case 10: p->pw_speed = (int8_t)v; break;
    case 11: p->pw_min = (uint8_t)v; break;
    case 12: p->pw_max = (uint8_t)v; break;
    case 13: p->mode = (uint8_t)(v << 4); break;
    case 14: p->res = (uint8_t)v; break;
    case 15: p->cut = (uint8_t)v; break;
    case 16: p->cut_speed = (int8_t)v; break;
    case 17: p->cut_end = (uint8_t)v; break;
    case 18: p->transpose = (int8_t)v; break;
    case 19: p->fine = (int8_t)v; break;
    case 20: p->vib_delay = (uint8_t)v; break;
    case 21: p->vib_speed = (uint8_t)v; break;
    case 22: p->vib_depth = (uint8_t)v; break;
    case 23: p->wt_len = (uint8_t)v; break;
    case 24: p->wt_loop = (uint8_t)v; break;
    case 25: p->wt_abs = (uint8_t)v; break;
    case 26: case 27: case 28: case 29: p->wave = (uint8_t)((p->wave & ~(1 << (4 + i - 26))) | (v << (4 + i - 26))); break;
    case 30: case 31: case 32: p->mode = (uint8_t)((p->mode & ~(1 << (4 + i - 30))) | (v << (4 + i - 30))); break;
    }
}

/* ---- output */
static void dump(t_sid1 *x)
{
    t_atom a[PATCH_BYTES + 1];
    const uint8_t *b = (const uint8_t *)&x->p + 12;
    long i;
    char nm[13];
    memcpy(nm, x->p.name, 12); nm[12] = 0;
    atom_setsym(a, gensym(nm[0] ? nm : "INIT"));
    for (i = 0; i < PATCH_BYTES; i++) atom_setlong(a + 1 + i, b[i]);
    outlet_anything(x->info, gensym("patch"), PATCH_BYTES + 1, a);
    for (i = 0; i < NFIELDS; i++) { atom_setlong(a, field_get(&x->p, (int)i)); outlet_anything(x->info, gensym(FIELDS[i].name), 1, a); }
    for (i = 0; i < SID1_WT_MAX; i++) {
        atom_setlong(a, i); atom_setlong(a + 1, x->p.wt_ctl[i] >> 4); outlet_anything(x->info, gensym("wtctl"), 2, a);
        atom_setlong(a + 1, (int8_t)x->p.wt_note[i]); outlet_anything(x->info, gensym("wtnote"), 2, a);
        atom_setlong(a + 1, (x->p.wt_abs >> i) & 1); outlet_anything(x->info, gensym("wtabsk"), 2, a);
        {
            long w, nib = x->p.wt_ctl[i] >> 4, idx = 0;
            for (w = 0; w < 9; w++) if (WTWAVE[w] == nib) idx = w;
            atom_setlong(a + 1, idx); outlet_anything(x->info, gensym("wtwave"), 2, a);
        }
    }
    atom_setsym(a, gensym(nm[0] ? nm : "INIT"));
    outlet_anything(x->info, gensym("name"), 1, a);
}

/* ---- messages */
static void m_note(t_sid1 *x, long pitch, long vel) { push3(x, EV_NOTE, (int)pitch, (int)vel, 0); }
static void m_list(t_sid1 *x, t_symbol *s, long argc, t_atom *argv)
{
    (void)s;
    if (argc >= 2) push3(x, EV_NOTE, (int)atom_getlong(argv), (int)atom_getlong(argv + 1), 0);
}
static void m_bend(t_sid1 *x, long v) { push3(x, EV_BEND, (int)(v < 0 ? 0 : v > 16383 ? 16383 : v), 0, 0); }
static void m_bendrange(t_sid1 *x, long v) { push3(x, EV_BENDRANGE, (int)v, 0, 0); }
static void m_model(t_sid1 *x, long v) { push3(x, EV_MODEL, v != 0, 0, 0); }
static void m_oversample(t_sid1 *x, long v) { push3(x, EV_OS, v != 0, 0, 0); }
static void m_mode(t_sid1 *x, long v) { push3(x, EV_MODE, v != 0, 0, 0); }
static void m_gain(t_sid1 *x, double f) { push3(x, EV_GAIN, 0, 0, (float)(f < 0 ? 0 : f > 4 ? 4 : f)); }
static void m_panic(t_sid1 *x) { push3(x, EV_PANIC, 0, 0, 0); }

static void m_set(t_sid1 *x, t_symbol *s, long argc, t_atom *argv)
{
    t_symbol *f;
    int i;
    (void)s;
    if (argc < 2 || atom_gettype(argv) != A_SYM) return;
    f = atom_getsym(argv);
    if ((f == gensym("wtwave") || f == gensym("wtabsk")) && argc >= 3) {
        long k = atom_getlong(argv + 1), v = atom_getlong(argv + 2);
        if (k < 0 || k >= SID1_WT_MAX) return;
        if (f == gensym("wtwave")) x->p.wt_ctl[k] = (uint8_t)(WTWAVE[v < 0 ? 0 : v > 8 ? 8 : v] << 4);
        else x->p.wt_abs = (uint8_t)((x->p.wt_abs & ~(1u << k)) | ((v ? 1u : 0u) << k));
        push_patch(x);
        return;
    }
    if ((f == gensym("wtctl") || f == gensym("wtnote")) && argc >= 3) {
        long k = atom_getlong(argv + 1), v = atom_getlong(argv + 2);
        if (k < 0 || k >= SID1_WT_MAX) return;
        if (f == gensym("wtctl")) x->p.wt_ctl[k] = (uint8_t)((v < 0 ? 0 : v > 15 ? 15 : v) << 4);
        else x->p.wt_note[k] = (uint8_t)(int8_t)(v < -128 ? -128 : v > 127 ? 127 : v);
        push_patch(x);
        return;
    }
    for (i = 0; i < NFIELDS; i++)
        if (f == gensym(FIELDS[i].name)) { field_set(&x->p, i, (int)atom_getlong(argv + 1)); push_patch(x); return; }
    object_error((t_object *)x, "set: no field %s", f->s_name);
}

static void m_name(t_sid1 *x, t_symbol *s)
{
    memset(x->p.name, 0, sizeof x->p.name);
    strncpy(x->p.name, s->s_name, sizeof x->p.name - 1);
}

static void m_patch(t_sid1 *x, t_symbol *s, long argc, t_atom *argv)
{
    uint8_t *b = (uint8_t *)&x->p + 12;
    long i;
    (void)s;
    if (argc < PATCH_BYTES + 1) { object_error((t_object *)x, "patch: needs a name and %ld values", PATCH_BYTES); return; }
    m_name(x, atom_gettype(argv) == A_SYM ? atom_getsym(argv) : gensym("PATCH"));
    for (i = 0; i < PATCH_BYTES; i++) b[i] = (uint8_t)(atom_getlong(argv + 1 + i) & 255);
    push_patch(x);
}

static void m_factory(t_sid1 *x, long n)
{
    if (n < 0 || n >= SID1_NFACTORY) return;
    x->p = SID1_FACTORY[n];
    push_patch(x);
    dump(x);
}

static void m_nfactory(t_sid1 *x)
{
    t_atom a[2];
    long i;
    atom_setlong(a, SID1_NFACTORY);
    outlet_anything(x->info, gensym("nfactory"), 1, a);
    for (i = 0; i < SID1_NFACTORY; i++) {
        char nm[13];
        memcpy(nm, SID1_FACTORY[i].name, 12); nm[12] = 0;
        atom_setlong(a, i); atom_setsym(a + 1, gensym(nm));
        outlet_anything(x->info, gensym("factoryname"), 2, a);
    }
}

static void m_init(t_sid1 *x) { sid1_patch_init(&x->p); push_patch(x); dump(x); }

/* ---- dsp */
static void perform64(t_sid1 *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts,
                      long n, long flags, void *up)
{
    double *out = outs[0];
    long i;
    (void)dsp64; (void)ins; (void)numins; (void)numouts; (void)flags; (void)up;
    drain(x);
    if (n > x->buflen) { for (i = 0; i < n; i++) out[i] = 0; return; }
    sid1_render(x->e, x->buf, (int)n);
    for (i = 0; i < n; i++) out[i] = x->buf[i];
}

static void dsp64(t_sid1 *x, t_object *dsp64, short *count, double sr, long maxvec, long flags)
{
    (void)count; (void)flags;
    if (maxvec > x->buflen) {
        if (x->buf) sysmem_freeptr(x->buf);
        x->buf = (float *)sysmem_newptrclear(maxvec * (long)sizeof(float));
        x->buflen = x->buf ? maxvec : 0;
    }
    if (sr != x->sr) { x->sr = sr; sid1_set_rate(x->e, sr); }   /* (audio is off here: safe) */
    object_method(dsp64, gensym("dsp_add64"), x, perform64, 0, NULL);
}

static void assist(t_sid1 *x, void *b, long m, long a, char *s)
{
    (void)x; (void)b;
    if (m == ASSIST_INLET) strcpy(s, "note, bend, set <field> <value>, patch, factory, model, oversample, mode...");
    else if (a == 0) strcpy(s, "(signal) SID output, mono");
    else strcpy(s, "patch dump and info");
}

static void *sid1_new(t_symbol *s, long argc, t_atom *argv)
{
    t_sid1 *x = (t_sid1 *)object_alloc(sid1_class);
    (void)s; (void)argc; (void)argv;
    if (!x) return NULL;
    dsp_setup((t_pxobject *)x, 0);
    x->info = outlet_new(x, NULL);
    outlet_new(x, "signal");
    x->e = (sid1_engine_t *)sysmem_newptrclear((long)sizeof(sid1_engine_t));
    x->sr = sys_getsr() > 0 ? sys_getsr() : 44100.0;
    sid1_init(x->e, x->sr);
    x->p = SID1_FACTORY[0];
    sid1_set_patch(x->e, &x->p);
    x->qw = x->qr = 0;
    x->buf = NULL;
    x->buflen = 0;
    return x;
}

static void sid1_free(t_sid1 *x)
{
    dsp_free((t_pxobject *)x);
    if (x->buf) sysmem_freeptr(x->buf);
    if (x->e) sysmem_freeptr(x->e);
}

void ext_main(void *r)
{
    t_class *c = class_new("sid1~", (method)sid1_new, (method)sid1_free, (long)sizeof(t_sid1), 0L, A_GIMME, 0);
    (void)r;
    class_addmethod(c, (method)m_note, "note", A_LONG, A_LONG, 0);
    class_addmethod(c, (method)m_list, "list", A_GIMME, 0);
    class_addmethod(c, (method)m_bend, "bend", A_LONG, 0);
    class_addmethod(c, (method)m_bendrange, "bendrange", A_LONG, 0);
    class_addmethod(c, (method)m_model, "model", A_LONG, 0);
    class_addmethod(c, (method)m_oversample, "oversample", A_LONG, 0);
    class_addmethod(c, (method)m_mode, "mode", A_LONG, 0);
    class_addmethod(c, (method)m_gain, "gain", A_FLOAT, 0);
    class_addmethod(c, (method)m_panic, "panic", 0);
    class_addmethod(c, (method)m_set, "set", A_GIMME, 0);
    class_addmethod(c, (method)m_name, "name", A_SYM, 0);
    class_addmethod(c, (method)m_patch, "patch", A_GIMME, 0);
    class_addmethod(c, (method)m_factory, "factory", A_LONG, 0);
    class_addmethod(c, (method)m_nfactory, "nfactory", 0);
    class_addmethod(c, (method)dump, "dump", 0);
    class_addmethod(c, (method)m_init, "init", 0);
    class_addmethod(c, (method)dsp64, "dsp64", A_CANT, 0);
    class_addmethod(c, (method)assist, "assist", A_CANT, 0);
    class_dspinit(c);
    class_register(CLASS_BOX, c);
    sid1_class = c;
}
