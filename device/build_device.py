#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builds SID1.amxd (a Max for Live instrument) from this script: the patcher JSON in the .amxd container.
Usage: python3 device/build_device.py [out.amxd]"""
import json, struct, sys

VERSION = "1.1.1"
H = 169
BG = [0.118, 0.125, 0.145, 1.0]
SEP = [0.20, 0.21, 0.243, 1.0]
BLUE = [0.561, 0.659, 1.0, 1.0]
AMBER = [1.0, 0.702, 0.278, 1.0]
GREY = [0.165, 0.173, 0.196, 1.0]
BORDER = [0.29, 0.306, 0.345, 1.0]
TEXT = [0.79, 0.80, 0.84, 1.0]
DIM = [0.60, 0.63, 0.67, 1.0]
DARK = [0.08, 0.086, 0.10, 1.0]
WHITE = [0.95, 0.95, 0.95, 1.0]

boxes, lines = [], []
_n = [0]
_pp = [20, 20]          # next patching position


def nid():
    _n[0] += 1
    return "obj-%d" % _n[0]


def place(w=60, h=22):
    x, y = _pp
    _pp[0] += w + 20
    if _pp[0] > 1600:
        _pp[0] = 20
        _pp[1] += 60
    return [x, y, w, h]


def add(box):
    box.setdefault("id", nid())
    boxes.append({"box": box})
    return box["id"]


def obj(text, ins, outs, outtype=None, **kw):
    b = {"maxclass": "newobj", "text": text, "numinlets": ins, "numoutlets": outs,
         "outlettype": outtype if outtype is not None else [""] * outs, "patching_rect": place(max(60, 7 * len(text)))}
    b.update(kw)
    return add(b)


def msg(text, **kw):
    b = {"maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1, "outlettype": [""],
         "patching_rect": place(max(50, 7 * len(text)))}
    b.update(kw)
    return add(b)


def wire(a, ao, b, bi=0):
    lines.append({"patchline": {"source": [a, ao], "destination": [b, bi]}})


def pres(rect):
    return {"presentation": 1, "presentation_rect": rect}


def param(longname, short, ptype, lo=0, hi=127, initial=0, enum=None, invisible=0, unit=0, extra=None):
    v = {"parameter_longname": longname, "parameter_shortname": short, "parameter_type": ptype,
         "parameter_initial_enable": 1, "parameter_initial": [initial], "parameter_invisible": invisible}
    if enum is not None:
        v["parameter_enum"] = enum
        v["parameter_mmax"] = len(enum) - 1
    else:
        v["parameter_mmin"] = lo
        v["parameter_mmax"] = hi
        v["parameter_unitstyle"] = unit
    if extra:
        v.update(extra)
    return {"parameter_enable": 1, "saved_attribute_attributes": {"valueof": v}, "varname": longname}


# ---- widgets
def panel(rect, color, name=None, rounded=0):
    b = {"maxclass": "panel", "numinlets": 1, "numoutlets": 0, "bgcolor": color, "mode": 0, "rounded": rounded,
         "border": 0, "patching_rect": place(40, 20), "background": 1, "ignoreclick": 1}
    b.update(pres(rect))
    return add(b)


def comment(rect, text, color=BLUE, size=8.0, bold=True):
    b = {"maxclass": "live.comment", "text": text, "numinlets": 1, "numoutlets": 0, "textcolor": color,
         "fontsize": size, "fontface": 1 if bold else 0, "patching_rect": place(80, 18)}
    b.update(pres(rect))
    return add(b)


KNOB_UI = {}            # live.dial id -> the jsui that draws it
KNOB_OUT = {}           # live.dial id -> the object its value leaves from


def dial(rect, longname, short, lo, hi, initial, unit=0, color=BLUE, invisible=0, ptype=1):
    """a drawn knob (sid1_knob.js) under an invisible live.dial that holds the parameter"""
    ui = add({"maxclass": "jsui", "filename": "sid1_knob.js", "numinlets": 1, "numoutlets": 0, "outlettype": [],
              "jsarguments": [lo, hi, initial, 1 if color == AMBER else 0, short, 1 if unit == 4 else 0],
              "patching_rect": place(44, 50), "parameter_enable": 0, "border": 0, "ignoreclick": 1, **pres(rect)})
    clear = [0.0, 0.0, 0.0, 0.0]
    b = {"maxclass": "live.dial", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
         "patching_rect": place(41, 48), "showname": 0, "shownumber": 0,
         "activedialcolor": clear, "activeneedlecolor": clear, "dialcolor": clear, "needlecolor": clear,
         "textcolor": clear, "focusbordercolor": clear, "fontsize": 8.0}
    b.update(pres(rect))
    extra = {} if ptype == 0 else {"parameter_steps": int(hi - lo + 1)}   # whole numbers, but a float range
    b.update(param(longname, short, 0, lo, hi, initial, invisible=invisible, unit=unit if ptype == 0 else 0, extra=extra))
    d = add(b)
    if ptype != 0:                       # to the engine and the drawing as whole numbers
        r_ = obj("round 1.", 2, 1, ["float"]); i_ = obj("i", 2, 1, ["int"])
        wire(d, 0, r_); wire(r_, 0, i_)
        d_out = i_
    else:
        d_out = d
    KNOB_OUT[d] = d_out
    wire(d_out, 0, ui)
    KNOB_UI[d] = ui
    return d


def toggle(rect, longname, text, initial=0, color=BLUE, button=False, invisible=0, size=8.0):
    b = {"maxclass": "live.text", "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
         "patching_rect": place(44, 15), "text": text, "texton": text, "mode": 0 if button else 1,
         "activebgcolor": GREY, "bgcolor": GREY, "activebgoncolor": color, "bgoncolor": color,
         "activetextcolor": TEXT, "textcolor": TEXT, "activetextoncolor": DARK, "textoncolor": DARK,
         "bordercolor": BORDER, "focusbordercolor": BORDER, "fontsize": size, "fontface": 1, "rounded": 3.0}
    b.update(pres(rect))
    b.update(param(longname, text, 2, initial=initial, enum=["off", "on"], invisible=invisible))
    return add(b)


def tab(rect, longname, short, items, initial=0, invisible=0, color=BLUE, rows=1):
    b = {"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
         "patching_rect": place(100, 15), "num_lines_patching": rows, "num_lines_presentation": rows,
         "activebgcolor": GREY, "bgcolor": GREY, "activebgoncolor": color, "bgoncolor": color,
         "textcolor": TEXT, "textoncolor": DARK, "activetextcolor": TEXT, "activetextoncolor": DARK,
         "bordercolor": BORDER, "fontsize": 8.0, "fontface": 1, "rounded": 3.0}
    b.update(pres(rect))
    b.update(param(longname, short, 2, initial=initial, enum=items, invisible=invisible))
    return add(b)


def slider(rect, longname, short, lo, hi, initial, enum=None, invisible_look=False):
    b = {"maxclass": "live.slider", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
         "patching_rect": place(39, 100), "orientation": 0, "showname": 1, "shownumber": 1,
         "slidercolor": WHITE, "activeslidercolor": BLUE, "tribordercolor": BORDER, "trioncolor": BLUE,
         "textcolor": TEXT, "fontsize": 8.0}
    b.update(pres(rect))
    if invisible_look:                   # drawn by a jsui underneath; the slider only takes the mouse
        clear = [0.0, 0.0, 0.0, 0.0]
        b.update({"showname": 0, "shownumber": 0, "slidercolor": clear, "activeslidercolor": clear,
                  "tribordercolor": clear, "trioncolor": clear, "tricolor": clear, "textcolor": clear})
    b.update(param(longname, short, 2 if enum else 1, lo, hi, initial, enum=enum))
    return add(b)


def numbox(rect, longname, short, lo, hi, initial, invisible=0, color=AMBER):
    b = {"maxclass": "live.numbox", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
         "patching_rect": place(44, 15), "activebgcolor": [0.11, 0.114, 0.133, 1.0], "textcolor": color,
         "activeslidercolor": BLUE, "tricolor": BLUE, "fontsize": 8.0, "fontface": 1, "appearance": 1}
    b.update(pres(rect))
    b.update(param(longname, short, 1, lo, hi, initial, invisible=invisible))
    return add(b)


def menu(rect, longname, short, items, initial=0):
    b = {"maxclass": "live.menu", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
         "patching_rect": place(60, 15), "activebgcolor": GREY, "bgcolor": GREY, "textcolor": TEXT,
         "activetextcolor": TEXT, "tricolor": DIM, "fontsize": 7.0, "fontface": 1}
    b.update(pres(rect))
    b.update(param(longname, short, 2, initial=initial, enum=items))
    return add(b)


def jsui(rect, filename, outs=0, varname=None, hidden=0):
    b = {"maxclass": "jsui", "filename": filename, "numinlets": 1, "numoutlets": outs,
         "outlettype": [""] * outs, "patching_rect": place(rect[2] // 2 + 20, rect[3] // 2 + 10),
         "parameter_enable": 0, "border": 0}
    if varname:
        b["varname"] = varname
    if hidden:
        b["hidden"] = 1
    b.update(pres(rect))
    return add(b)


# ---- the engine and its plumbing
sid = obj("sid1~", 1, 2, ["signal", ""])
midiin = obj("midiin", 1, 1, ["int"])
mparse = obj("midiparse", 1, 8, ["", "", "", "int", "int", "", "int", ""])
xbend = obj("xbendin", 1, 2, ["int", "int"])
pnote = obj("prepend note", 1, 1)
pbend = obj("prepend bend", 1, 1)
wire(midiin, 0, mparse); wire(midiin, 0, xbend)
tnote = obj("t l l", 1, 2)
wire(mparse, 0, tnote); wire(tnote, 0, pnote); wire(pnote, 0, sid)
wire(xbend, 0, pbend); wire(pbend, 0, sid)
out = obj("plugout~", 2, 2, ["signal", "signal"])
wire(sid, 0, out, 0); wire(sid, 0, out, 1)

rcmd = obj("r ---sid1cmd", 0, 1)
tcmd = obj("t l b", 1, 2)
medit = msg("edited")
wire(rcmd, 0, tcmd); wire(tcmd, 0, sid); wire(tcmd, 1, medit)

presets = obj("js sid1_presets.js", 1, 6)
wire(medit, 0, presets)
wire(presets, 0, sid)

# info from sid1~: preset messages to js, field messages to the controls
info_js = obj("route patch nfactory factoryname rolled", 1, 5)
wire(sid, 1, info_js)
for i, sel in enumerate(["patch", "nfactory", "factoryname"]):
    p = obj("prepend " + sel, 1, 1)
    wire(info_js, i, p); wire(p, 0, presets)

FIELD_ROUTE = []        # (field, control id, wt step or None)


def out_of(ctl):
    return KNOB_OUT.get(ctl, ctl)


def field_ctl(ctl, field):
    """a control that edits a patch field: out -> set field -> sid1~ (as an edit); field dumps -> set control"""
    p = obj("prepend set " + field, 1, 1)
    s = obj("s ---sid1cmd", 1, 0)
    wire(out_of(ctl), 0, p); wire(p, 0, s)
    FIELD_ROUTE.append((field, ctl))


def wt_ctl(ctl, field, k):
    p = obj("prepend set %s %d" % (field, k), 1, 1)
    s = obj("s ---sid1cmd", 1, 0)
    wire(ctl, 0, p); wire(p, 0, s)
    FIELD_ROUTE.append(((field, k), ctl))


def direct(ctl, prefix):
    p = obj("prepend " + prefix, 1, 1)
    wire(out_of(ctl), 0, p); wire(p, 0, sid)


def to_js(ctl, message, bang=True):
    t = obj("t b", 1, 1)
    m = msg(message)
    wire(ctl, 0, t); wire(t, 0, m); wire(m, 0, presets)


# ---- presentation: background and sections
SECT = [("", 0, 125), ("PRESET", 125, 200), ("OSCILLATOR", 325, 165), ("ENVELOPE", 490, 115),
        ("FILTER", 605, 100), ("PITCH · VIBRATO", 705, 135), ("WAVETABLE · 50 Hz", 840, 225)]
W = 840 + 225
panel([0, 0, W, H], BG, rounded=0)
for title, x, w in SECT[1:]:
    panel([x, 6, 1, H - 12], SEP)
    comment([x + 6, 4, w - 8, 14], title)

# brand column
jsui([6, 4, 112, 30], "sid1_logo.js")
store = toggle([6, 36, 113, 14], "Store", "ticcoross.gumroad.com ↗", button=True, invisible=2, color=AMBER, size=8.0)
mstore = msg("; max launchbrowser https://ticcoross.gumroad.com/")
tst = obj("t b", 1, 1); wire(store, 0, tst); wire(tst, 0, mstore)
comment([6, 54, 40, 12], "CHIP", DIM)
chip = tab([6, 66, 80, 16], "Chip", "Chip", ["6581", "8580"])
direct(chip, "model")
voices = tab([6, 88, 80, 16], "Voices", "Voices", ["POLY", "MONO"])
direct(voices, "mode")
os2 = toggle([6, 110, 36, 16], "Oversample", "2X")
direct(os2, "oversample")
about_btn = toggle([46, 110, 40, 16], "About", "ABOUT", button=True, invisible=2)
vol = dial([88, 62, 34, 48], "Volume", "VOL", -70, 6, 0, unit=4, ptype=0)
dbt = obj("dbtoa", 1, 1); pg = obj("prepend gain", 1, 1)
wire(out_of(vol), 0, dbt); wire(dbt, 0, pg); wire(pg, 0, sid)
bendr = dial([88, 112, 34, 48], "Bend Range", "BEND", 0, 24, 2)
direct(bendr, "bendrange")
jsui([4, 136, 82, 26], "sid1_stripes.js")

# preset section
disp = jsui([131, 20, 188, 44], "sid1_display.js")
wire(presets, 1, disp)
pnum = numbox([131, 68, 34, 16], "Preset", "Preset", 0, 127, 0, color=WHITE)
pslot = obj("prepend slot", 1, 1); wire(pnum, 0, pslot); wire(pslot, 0, presets)
wire(presets, 3, pnum)
prv = toggle([168, 68, 18, 16], "Prev", "◀", button=True)
nxt = toggle([188, 68, 18, 16], "Next", "▶", button=True)
to_js(prv, "prev"); to_js(nxt, "next")
bankt = tab([210, 68, 109, 16], "Bank", "Bank", ["A", "B", "C", "D"], invisible=1)
pbank = obj("prepend bank", 1, 1); wire(bankt, 0, pbank); wire(pbank, 0, presets)
div = obj("/ 32", 2, 1, ["int"]); pset = obj("prepend set", 1, 1)
wire(pnum, 0, div); wire(div, 0, pset); wire(pset, 0, bankt)
save = toggle([131, 88, 36, 16], "Save", "SAVE", button=True, invisible=2, color=AMBER)
to_js(save, "save")
cmpt = toggle([170, 88, 34, 16], "Compare", "CMP", invisible=2)
pcmp = obj("prepend cmp", 1, 1); wire(cmpt, 0, pcmp); wire(pcmp, 0, presets)
initb = toggle([207, 88, 34, 16], "Init", "INIT", button=True, invisible=2)
to_js(initb, "init")
imp = toggle([244, 88, 36, 16], "Import", "IMP", button=True, invisible=2)
exp = toggle([283, 88, 36, 16], "Export", "EXP", button=True, invisible=2)
od = obj("opendialog TEXT", 1, 2, ["", "bang"]); sd = obj("savedialog TEXT", 1, 3, ["", "", "bang"])
ti = obj("t b", 1, 1); te = obj("t b", 1, 1)
pi = obj("prepend importbank", 1, 1); pe = obj("prepend exportbank", 1, 1)
wire(imp, 0, ti); wire(ti, 0, od); wire(od, 0, pi); wire(pi, 0, presets)
wire(exp, 0, te); wire(te, 0, sd); wire(sd, 0, pe); wire(pe, 0, presets)
comment([131, 110, 40, 12], "NAME", DIM)
name = add(dict(maxclass="textedit", numinlets=1, numoutlets=4, outlettype=["", "int", "", ""],
                patching_rect=place(100, 20), keymode=1, lines=1, wordwrap=0, fontsize=10.0, fontname="Courier New Bold",
                textcolor=WHITE, bgcolor=[0.11, 0.114, 0.133, 1.0], bordercolor=BORDER, rounded=3.0,
                text="PWM LEAD", **pres([131, 122, 188, 18])))
rtext = obj("route text", 1, 2); pren = obj("prepend rename", 1, 1)
wire(name, 0, rtext); wire(rtext, 0, pren); wire(pren, 0, presets)
wire(presets, 4, name)
comment([131, 144, 188, 22], "SAVE keeps the edit in this slot. Set the preset with the number, ◀▶ or a bank.", DIM, 7.0, False)

# pattr: the user library, stored in the Live set / device preset
pat = add(dict(maxclass="newobj", text="pattr sid1lib", numinlets=2, numoutlets=3, outlettype=["", "", ""],
               patching_rect=place(90, 22), parameter_enable=1,
               saved_attribute_attributes={"valueof": {"parameter_longname": "sid1lib", "parameter_shortname": "sid1lib",
                                                       "parameter_type": 3, "parameter_invisible": 1,
                                                       "parameter_initial_enable": 0}},
               varname="sid1lib"))
wire(presets, 2, pat); wire(pat, 0, presets)

# start-up
lb = obj("live.thisdevice", 1, 3, ["bang", "int", "int"])
dl = obj("deferlow", 1, 1)
mnf = msg("nfactory")
wire(lb, 0, dl); wire(dl, 0, mnf); wire(mnf, 0, sid)
dly = obj("delay 1500", 2, 1, ["bang"]); mgo = msg("go")
wire(lb, 0, dly); wire(dly, 0, mgo); wire(mgo, 0, presets)

# oscillator
x0 = 331
for i, (f, t) in enumerate([("tri", "TRI"), ("saw", "SAW"), ("pul", "PUL"), ("noi", "NOI")]):
    c = toggle([x0 + i * 39, 20, 36, 16], "Wave " + t, t, initial=1 if f == "pul" else 0)
    field_ctl(c, f)
for i, (f, t, col) in enumerate([("ring", "RING", BLUE), ("sync", "SYNC", BLUE), ("hard", "HARD", AMBER)]):
    c = toggle([x0 + i * 52, 40, 49, 16], {"ring": "Ring Mod", "sync": "Sync", "hard": "Hard Restart"}[f], t,
               initial=1 if f == "hard" else 0, color=col)
    field_ctl(c, f)
for i, (f, ln, sh, lo, hi, ini) in enumerate([("pw", "Pulse Width", "PW", 0, 4095, 2048), ("pwspeed", "PW Speed", "SPEED", -128, 127, 0),
                                              ("pwmin", "PW Min", "MIN", 0, 255, 0), ("pwmax", "PW Max", "MAX", 0, 255, 255)]):
    field_ctl(dial([x0 + i * 40, 62, 40, 48], ln, sh, lo, hi, ini), f)

# envelope
# the SID's own times (attack; decay and release are 3x), and sustain as 16 levels
ATK = ["2ms", "8ms", "16ms", "24ms", "38ms", "56ms", "68ms", "80ms", "100ms", "250ms", "500ms", "800ms", "1s", "3s", "5s", "8s"]
DR = ["6ms", "24ms", "48ms", "72ms", "114ms", "168ms", "204ms", "240ms", "300ms", "750ms", "1.5s", "2.4s", "3s", "9s", "15s", "24s"]
SUS = ["%d%%" % round(v * 100 / 15) for v in range(16)]
# drawn faders (sid1_adsr.js) under invisible live.sliders: the jsui's travel is y 34..128 inside its box
adsr = jsui([494, 18, 112, 148], "sid1_adsr.js")
boxes[-1]["box"]["ignoreclick"] = 1
ADSR_SLIDERS = {}
for i, (f, ln, sh, ini, en) in enumerate([("attack", "Attack", "A", 0, ATK), ("decay", "Decay", "D", 8, DR),
                                          ("sustain", "Sustain", "S", 10, SUS), ("release", "Release", "R", 9, DR)]):
    sl = slider([494 + i * 28, 18 + 34 - 7, 28, 128 - 34 + 14], ln, sh, 0, 15, ini, enum=en, invisible_look=True)
    field_ctl(sl, f)
    pj = obj("prepend " + f, 1, 1)
    wire(sl, 0, pj); wire(pj, 0, adsr)
    ADSR_SLIDERS[f] = pj

# filter
fx = 611
field_ctl(toggle([fx, 20, 22, 16], "Filter On", "ON"), "filter")
for i, (f, t) in enumerate([("lp", "LP"), ("bp", "BP"), ("hp", "HP")]):
    field_ctl(toggle([fx + 24 + i * 23, 20, 21, 16], "Filter " + t, t, initial=1 if f == "lp" else 0), f)
field_ctl(dial([fx, 40, 44, 48], "Cutoff", "CUTOFF", 0, 255, 128), "cut")
field_ctl(dial([fx + 46, 40, 44, 48], "Resonance", "RES", 0, 15, 0), "res")
field_ctl(dial([fx, 100, 44, 48], "Cutoff Sweep", "SWEEP", -128, 127, 0, color=AMBER), "cutspeed")
field_ctl(dial([fx + 46, 100, 44, 48], "Sweep End", "END", 0, 255, 128, color=AMBER), "cutend")

# pitch / vibrato
px = 711
for i, (f, ln, sh, lo, hi, ini) in enumerate([("vibdepth", "Vib Depth", "DEPTH", 0, 255, 0), ("vibspeed", "Vib Speed", "SPEED", 0, 255, 0),
                                              ("vibdelay", "Vib Delay", "DELAY", 0, 255, 0), ("transpose", "Transpose", "TRANS", -48, 48, 0),
                                              ("fine", "Fine", "FINE", -100, 100, 0)]):
    field_ctl(dial([px + (i % 3) * 42, 20 + (i // 3) * 58, 42, 48], ln, sh, lo, hi, ini), f)

# wavetable
wx = 846
WAVES = ["·", "TRI", "SAW", "PUL", "NOI", "S+T", "P+T", "P+S", "PST"]
for k in range(8):
    x = wx + k * 27
    comment([x + 8, 18, 18, 12], str(k + 1), DIM)
    wt_ctl(menu([x, 30, 26, 15], "Step %d Wave" % (k + 1), "W%d" % (k + 1), WAVES), "wtwave", k)
    wt_ctl(numbox([x, 48, 26, 15], "Step %d Note" % (k + 1), "N%d" % (k + 1), -48, 108, 0), "wtnote", k)
    wt_ctl(toggle([x, 66, 26, 13], "Step %d Abs" % (k + 1), "ABS", color=AMBER, size=7.0), "wtabsk", k)
field_ctl(dial([wx, 88, 44, 48], "WT Length", "LENGTH", 0, 8, 0, color=AMBER), "wtlen")
field_ctl(dial([wx + 48, 88, 44, 48], "WT Loop", "LOOP", 0, 8, 0, color=AMBER), "wtloop")
comment([wx + 98, 90, 118, 60], "One step a frame: wave (· = the patch's), note offset, or ABS = absolute note. LOOP: step after the last.", DIM, 7.0, False)


# ---- RANDOM: the rules are in sid1~ ("roll"); sid1_random.js runs the panel; the panel is a hidden bpatcher
rnd = obj("js sid1_random.js", 1, 4)
wire(rnd, 0, sid)
wire(rnd, 2, presets)
wire(rnd, 3, chip)
pp = obj("prepend patch", 1, 1); wire(info_js, 0, pp); wire(pp, 0, rnd)
prl = obj("prepend rolled", 1, 1); wire(info_js, 3, prl); wire(prl, 0, rnd)
psm = obj("prepend setmodel", 1, 1); wire(chip, 0, psm); wire(psm, 0, rnd)
pno = obj("prepend noteon", 1, 1); wire(tnote, 1, pno); wire(pno, 0, rnd)
met = obj("metro 1m @quantize 1m @autostart 1", 2, 1, ["bang"])
mbar = msg("bar"); wire(met, 0, mbar); wire(mbar, 0, rnd)
rclose_in = obj("t b", 1, 1)        # CLOSE
rnd_btn = toggle([262, 3, 57, 14], "Random", "RANDOM", button=True, invisible=2, color=AMBER)

# the panel's controls live in the main patcher, hidden; RANDOM shows them over the device, CLOSE hides them.
# (An embedded bpatcher worked in Max but not in Live, so no subpatcher and no sends.)
RP_FIRST = len(boxes)
panel([0, 0, W, H], [0.086, 0.09, 0.106, 1.0])


def send_ui(ctl, prefix, bang_msg=None):
    if bang_msg == "close":
        t = obj("t b", 1, 1); wire(ctl, 0, t); wire(t, 0, rclose_in)
    elif bang_msg:
        t = obj("t b", 1, 1); m = msg(bang_msg)
        wire(ctl, 0, t); wire(t, 0, m); wire(m, 0, rnd)
    else:
        p = obj("prepend " + prefix, 1, 1)
        wire(out_of(ctl), 0, p); wire(p, 0, rnd)


RSECT = [("SOUND TYPE", 100, 176), ("CHARACTER", 276, 180), ("LOCK", 456, 145), ("ROLL", 601, 140),
         ("AUTO", 741, 115), ("RESULT", 856, 209)]
for title, x, w in RSECT:
    panel([x, 6, 1, H - 12], SEP)
    comment([x + 6, 4, w - 8, 14], title)
comment([8, 4, 90, 18], "RANDOM", WHITE, 12.0)
comment([8, 24, 90, 12], "New patches by", DIM, 7.0, False)
comment([8, 34, 90, 12], "the rules: inside", DIM, 7.0, False)
comment([8, 44, 90, 12], "safe ranges, never", DIM, 7.0, False)
comment([8, 54, 90, 12], "silent or broken.", DIM, 7.0, False)
send_ui(toggle([8, 74, 84, 16], "Random Close", "CLOSE", button=True, invisible=2), None, "close")
jsui([6, 136, 60, 26], "sid1_stripes.js")

send_ui(tab([106, 20, 164, 34], "Random Type", "Type", ["LEAD", "BASS", "PAD", "PLUCK", "ARP", "DRUM", "FX", "ANY"], initial=1, rows=2), "type")
comment([106, 60, 164, 12], "CHIP FOR THE ROLL", DIM)
send_ui(tab([106, 72, 164, 16], "Random Chip", "Chip", ["KEEP", "6581", "8580", "ANY"]), "chip")
comment([106, 96, 164, 12], "Each type has its own", DIM, 7.0, False)
comment([106, 106, 164, 12], "safe ranges.", DIM, 7.0, False)

for i, (ln, sh, lo, hi, ini, col) in enumerate([("Random Amount", "AMOUNT", 0, 100, 100, BLUE), ("Random Bright", "BRIGHT", -100, 100, 0, BLUE),
                                               ("Random Motion", "MOTION", 0, 100, 50, BLUE), ("Random Length", "LENGTH", -100, 100, 0, AMBER)]):
    send_ui(dial([280 + i * 44, 20, 44, 48], ln, sh, lo, hi, ini, color=col), sh.lower())
comment([282, 76, 170, 12], "AMOUNT: low nudges, high is new.", DIM, 7.0, False)
comment([282, 86, 170, 12], "BRIGHT, MOTION, LENGTH steer it.", DIM, 7.0, False)

for k, t in enumerate(["OSC", "ENV", "FILTER", "PITCH", "WTABLE"]):
    send_ui(toggle([462 + (k % 3) * 46, 20 + (k // 3) * 20, 44, 16], "Lock " + t.title(), t, color=AMBER), "lock %d" % k)
comment([462, 62, 134, 12], "ARP CHORDS", DIM)
send_ui(tab([462, 74, 134, 16], "Random Chords", "Chords", ["MAJ", "MIN", "SUS", "ANY"], initial=3), "chords")

send_ui(toggle([607, 20, 62, 16], "Roll", "ROLL", button=True, color=AMBER), None, "roll")
send_ui(toggle([672, 20, 62, 16], "Mutate", "MUTATE", button=True), None, "mutate")
send_ui(toggle([607, 40, 62, 16], "Undo", "◀ UNDO", button=True, invisible=2), None, "undo")
send_ui(toggle([672, 40, 62, 16], "Redo", "REDO ▶", button=True, invisible=2), None, "redo")
comment([607, 62, 127, 12], "HISTORY", DIM)
hj = jsui([607, 74, 127, 14], "sid1_rhist.js", outs=1)
wire(hj, 0, rnd)

send_ui(tab([747, 20, 103, 16], "Auto Roll", "Auto", ["OFF", "NOTE", "BARS"], invisible=1), "auto")
send_ui(dial([747, 40, 44, 48], "Auto Bars", "BARS", 1, 16, 4, color=AMBER, invisible=1), "bars")
comment([795, 46, 58, 12], "ROLL is", DIM, 7.0, False)
comment([795, 56, 58, 12], "MIDI-mappable", DIM, 7.0, False)

rj = jsui([862, 18, 197, 96], "sid1_rresult.js")
send_ui(toggle([862, 118, 62, 16], "Keep", "KEEP", button=True, invisible=2, color=AMBER), None, "keep")
send_ui(toggle([928, 118, 62, 16], "Preview", "PREVIEW", button=True, invisible=2), None, "preview")

rroute = obj("route hist result free", 1, 4)
wire(rnd, 1, rroute); wire(presets, 5, rroute)
ph = obj("prepend hist", 1, 1); wire(rroute, 0, ph); wire(ph, 0, hj)
pr = obj("prepend result", 1, 1); wire(rroute, 1, pr); wire(pr, 0, rj)
pf = obj("prepend free", 1, 1); wire(rroute, 2, pf); wire(pf, 0, rj)

RP_NAMES = []
for bx in boxes[RP_FIRST:]:
    bb = bx["box"]
    if bb.get("presentation"):
        bb["hidden"] = 1
        if bb.get("maxclass") == "panel":       # on top of the main panel's controls, not in the background layer
            bb["background"] = 0
            if bb["presentation_rect"][2] == W:
                bb["ignoreclick"] = 0           # the backdrop takes the clicks the panel's controls don't
        if "varname" not in bb:
            bb["varname"] = "rp%d" % len(RP_NAMES)
        RP_NAMES.append(bb["varname"])
sub_boxes, sub_lines = [], []


# about overlay (hidden until ABOUT)
about = jsui([0, 0, W, H], "sid1_about.js", outs=1, varname="about", hidden=1)
tp = obj("thispatcher", 1, 2, ["", ""])
tab_ = obj("t b", 1, 1)
mshow = msg("script show about, script bringtofront about")
mhide = msg("script hide about")
wire(about_btn, 0, tab_); wire(tab_, 0, mshow); wire(mshow, 0, tp)
wire(about, 0, mhide); wire(mhide, 0, tp)
trn = obj("t b", 1, 1)
mrshow = msg(", ".join("script show %s, script bringtofront %s" % (n, n) for n in RP_NAMES))
mrhide = msg(", ".join("script hide %s" % n for n in RP_NAMES))
wire(rnd_btn, 0, trn); wire(trn, 0, mrshow); wire(mrshow, 0, tp)
wire(rclose_in, 0, mrhide); wire(mrhide, 0, tp)

# field dumps from sid1~ back to the controls (set: no output, no edit)
plain = [f for f, _ in FIELD_ROUTE if isinstance(f, str)]
rf = obj("route " + " ".join(plain + ["wtwave", "wtnote", "wtabsk"]), 1, len(plain) + 4)
wire(sid, 1, rf)
for i, (f, ctl) in enumerate([(f, c) for f, c in FIELD_ROUTE if isinstance(f, str)]):
    p = obj("prepend set", 1, 1)
    wire(rf, i, p); wire(p, 0, ctl)
    if f in ADSR_SLIDERS:
        wire(rf, i, ADSR_SLIDERS[f])
    if ctl in KNOB_UI:
        wire(rf, i, KNOB_UI[ctl])
for j, wf in enumerate(["wtwave", "wtnote", "wtabsk"]):
    rk = obj("route 0 1 2 3 4 5 6 7", 1, 9)
    wire(rf, len(plain) + j, rk)
    for f, ctl in FIELD_ROUTE:
        if isinstance(f, tuple) and f[0] == wf:
            p = obj("prepend set", 1, 1)
            wire(rk, f[1], p); wire(p, 0, ctl)

patcher = {"patcher": {
    "fileversion": 1,
    "appversion": {"major": 8, "minor": 6, "revision": 5, "architecture": "x64", "modernui": 1},
    "classnamespace": "box", "rect": [40, 80, 1700, 900], "openrect": [0, 0, W, H],
    "bglocked": 0, "openinpresentation": 1, "default_fontsize": 10.0, "default_fontface": 0,
    "default_fontname": "Arial Bold", "gridonopen": 1, "gridsize": [8.0, 8.0], "gridsnaponopen": 1,
    "objectsnaponopen": 1, "statusbarvisible": 2, "toolbarvisible": 1, "lefttoolbarpinned": 0,
    "toptoolbarpinned": 0, "righttoolbarpinned": 0, "bottomtoolbarpinned": 0, "toolbars_unpinned_last_save": 0,
    "tallnewobj": 0, "boxanimatetime": 200, "enablehscroll": 1, "enablevscroll": 1, "devicewidth": float(W),
    "description": "SID1 " + VERSION + " - dual MOS SID synth (Transistor Labs)", "digest": "", "tags": "",
    "style": "", "subpatcher_template": "", "assistshowspatchername": 0,
    "boxes": boxes, "lines": lines,
    "dependency_cache": [
        {"name": "sid1_presets.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_display.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_logo.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_about.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_stripes.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_adsr.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_knob.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_random.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_rhist.js", "type": "TEXT", "implicit": 1},
        {"name": "sid1_rresult.js", "type": "TEXT", "implicit": 1},
        ],
    "latency": 0, "is_mpe": 0, "minimum_live_version": "", "minimum_max_version": "",
    "platform_compatibility": 0, "project": {"version": 1, "creationdate": 3590052493, "modificationdate": 3590052493,
                                             "viewrect": [0, 0, 300, 500], "autoorganize": 1, "hideprojectwindow": 1,
                                             "showdependencies": 1, "autolocalize": 0, "contents": {"patchers": {}, "code": {}},
                                             "layout": {}, "searchpath": {}, "detailsvisible": 0, "amxdtype": 1768515945,
                                             "readonly": 0, "devpathtype": 0, "devpath": ".", "sortmode": 0, "viewmode": 0,
                                             "includepackages": 0},
    "autosave": 0, "saved_attribute_attributes": {"default_plcolor": {"expression": ""}}}}

data = json.dumps(patcher, indent=1).encode("utf-8") + b"\n\x00"
# .amxd container: 'ampf' + 'iiii' (instrument) + meta + ptch
amxd = b"ampf" + struct.pack("<I", 4) + b"iiii" + b"meta" + struct.pack("<I", 4) + struct.pack("<I", 0) + \
       b"ptch" + struct.pack("<I", len(data)) + data
outp = sys.argv[1] if len(sys.argv) > 1 else "SID1.amxd"
open(outp, "wb").write(amxd)

# checks: unique parameter names, wires in range
allb = boxes + sub_boxes
names = [b["box"]["varname"] for b in allb if b["box"].get("parameter_enable")]
assert len(names) == len(set(names)), "duplicate parameter names"
for bx, ln in ((boxes, lines), (sub_boxes, sub_lines)):
  ids = {b["box"]["id"]: b["box"] for b in bx}
  for l in ln:
    s, d = l["patchline"]["source"], l["patchline"]["destination"]
    assert s[1] < ids[s[0]]["numoutlets"], ("outlet", s, ids[s[0]].get("text"))
    assert d[1] < ids[d[0]]["numinlets"], ("inlet", d, ids[d[0]].get("text"), ids[d[0]]["maxclass"])
print("%s: %d boxes, %d lines, %d parameters, %d px wide" % (outp, len(boxes), len(lines), len(names), W))
