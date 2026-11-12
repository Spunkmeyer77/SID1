#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builds SID1.amxd (a Max for Live instrument) from this script: the patcher JSON in the .amxd container.
Usage: python3 device/build_device.py [out.amxd]"""
import json, struct, sys

VERSION = "1.0.1"
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


def dial(rect, longname, short, lo, hi, initial, unit=0, color=BLUE, invisible=0, ptype=1):
    b = {"maxclass": "live.dial", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
         "patching_rect": place(41, 48), "activedialcolor": color, "activeneedlecolor": WHITE,
         "dialcolor": [0.23, 0.24, 0.27, 1.0], "textcolor": TEXT, "fontsize": 8.0, "showname": 1, "shownumber": 1}
    b.update(pres(rect))
    b.update(param(longname, short, ptype, lo, hi, initial, invisible=invisible, unit=unit))
    return add(b)


def toggle(rect, longname, text, initial=0, color=BLUE, button=False, invisible=0, size=8.0):
    b = {"maxclass": "live.text", "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
         "patching_rect": place(44, 15), "text": text, "texton": text, "mode": 0 if button else 1,
         "activebgcolor": GREY, "bgcolor": GREY, "activebgoncolor": color, "bgoncolor": color,
         "activetextcolor": TEXT, "textcolor": TEXT, "activetextoncolor": DARK, "textoncolor": DARK,
         "bordercolor": BORDER, "focusbordercolor": BORDER, "fontsize": size, "fontface": 1, "rounded": 3.0}
    b.update(pres(rect))
    b.update(param(longname, text, 2, initial=initial, enum=["off", "on"], invisible=invisible))
    return add(b)


def tab(rect, longname, short, items, initial=0, invisible=0, color=BLUE):
    b = {"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
         "patching_rect": place(100, 15), "num_lines_patching": 1, "num_lines_presentation": 1,
         "activebgcolor": GREY, "bgcolor": GREY, "activebgoncolor": color, "bgoncolor": color,
         "textcolor": TEXT, "textoncolor": DARK, "activetextcolor": TEXT, "activetextoncolor": DARK,
         "bordercolor": BORDER, "fontsize": 8.0, "fontface": 1, "rounded": 3.0}
    b.update(pres(rect))
    b.update(param(longname, short, 2, initial=initial, enum=items, invisible=invisible))
    return add(b)


def slider(rect, longname, short, lo, hi, initial, enum=None):
    b = {"maxclass": "live.slider", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
         "patching_rect": place(39, 100), "orientation": 0, "showname": 1, "shownumber": 1,
         "slidercolor": WHITE, "activeslidercolor": BLUE, "tribordercolor": BORDER, "trioncolor": BLUE,
         "textcolor": TEXT, "fontsize": 8.0}
    b.update(pres(rect))
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
wire(mparse, 0, pnote); wire(pnote, 0, sid)
wire(xbend, 0, pbend); wire(pbend, 0, sid)
out = obj("plugout~", 2, 2, ["signal", "signal"])
wire(sid, 0, out, 0); wire(sid, 0, out, 1)

rcmd = obj("r ---sid1cmd", 0, 1)
tcmd = obj("t l b", 1, 2)
medit = msg("edited")
wire(rcmd, 0, tcmd); wire(tcmd, 0, sid); wire(tcmd, 1, medit)

presets = obj("js sid1_presets.js", 1, 5)
wire(medit, 0, presets)
wire(presets, 0, sid)

# info from sid1~: preset messages to js, field messages to the controls
info_js = obj("route patch nfactory factoryname", 1, 4)
wire(sid, 1, info_js)
for i, sel in enumerate(["patch", "nfactory", "factoryname"]):
    p = obj("prepend " + sel, 1, 1)
    wire(info_js, i, p); wire(p, 0, presets)

FIELD_ROUTE = []        # (field, control id, wt step or None)


def field_ctl(ctl, field):
    """a control that edits a patch field: out -> set field -> sid1~ (as an edit); field dumps -> set control"""
    p = obj("prepend set " + field, 1, 1)
    s = obj("s ---sid1cmd", 1, 0)
    wire(ctl, 0, p); wire(p, 0, s)
    FIELD_ROUTE.append((field, ctl))


def wt_ctl(ctl, field, k):
    p = obj("prepend set %s %d" % (field, k), 1, 1)
    s = obj("s ---sid1cmd", 1, 0)
    wire(ctl, 0, p); wire(p, 0, s)
    FIELD_ROUTE.append(((field, k), ctl))


def direct(ctl, prefix):
    p = obj("prepend " + prefix, 1, 1)
    wire(ctl, 0, p); wire(p, 0, sid)


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
wire(vol, 0, dbt); wire(dbt, 0, pg); wire(pg, 0, sid)
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
comment([x0, 116, 155, 40], "PW sweeps between MIN and MAX at SPEED (per 50 Hz frame). HARD = hard restart.", DIM, 7.0, False)

# envelope
# the SID's own times (attack; decay and release are 3x), and sustain as 16 levels
ATK = ["2ms", "8ms", "16ms", "24ms", "38ms", "56ms", "68ms", "80ms", "100ms", "250ms", "500ms", "800ms", "1s", "3s", "5s", "8s"]
DR = ["6ms", "24ms", "48ms", "72ms", "114ms", "168ms", "204ms", "240ms", "300ms", "750ms", "1.5s", "2.4s", "3s", "9s", "15s", "24s"]
SUS = ["%d%%" % round(v * 100 / 15) for v in range(16)]
for i, (f, ln, sh, ini, en) in enumerate([("attack", "Attack", "A", 0, ATK), ("decay", "Decay", "D", 8, DR),
                                          ("sustain", "Sustain", "S", 10, SUS), ("release", "Release", "R", 9, DR)]):
    field_ctl(slider([494 + i * 28, 20, 28, 144], ln, sh, 0, 15, ini, enum=en), f)

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

# about overlay (hidden until ABOUT)
about = jsui([0, 0, W, H], "sid1_about.js", outs=1, varname="about", hidden=1)
tp = obj("thispatcher", 1, 2, ["", ""])
tab_ = obj("t b", 1, 1)
mshow = msg("script show about, script bringtofront about")
mhide = msg("script hide about")
wire(about_btn, 0, tab_); wire(tab_, 0, mshow); wire(mshow, 0, tp)
wire(about, 0, mhide); wire(mhide, 0, tp)

# field dumps from sid1~ back to the controls (set: no output, no edit)
plain = [f for f, _ in FIELD_ROUTE if isinstance(f, str)]
rf = obj("route " + " ".join(plain + ["wtwave", "wtnote", "wtabsk"]), 1, len(plain) + 4)
wire(sid, 1, rf)
for i, (f, ctl) in enumerate([(f, c) for f, c in FIELD_ROUTE if isinstance(f, str)]):
    p = obj("prepend set", 1, 1)
    wire(rf, i, p); wire(p, 0, ctl)
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
names = [b["box"]["varname"] for b in boxes if b["box"].get("parameter_enable")]
assert len(names) == len(set(names)), "duplicate parameter names"
ids = {b["box"]["id"]: b["box"] for b in boxes}
for l in lines:
    s, d = l["patchline"]["source"], l["patchline"]["destination"]
    assert s[1] < ids[s[0]]["numoutlets"], ("outlet", s, ids[s[0]].get("text"))
    assert d[1] < ids[d[0]]["numinlets"], ("inlet", d, ids[d[0]].get("text"), ids[d[0]]["maxclass"])
print("%s: %d boxes, %d lines, %d parameters, %d px wide" % (outp, len(boxes), len(lines), len(names), W))
