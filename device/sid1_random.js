// SPDX-License-Identifier: GPL-3.0-only
// SID1 RANDOM panel logic. The rules live in sid1~ ("roll", engine/sid1_random.c); this keeps the panel's settings,
// the history (undo/redo, the last 8 rolls), names the rolls, chooses the chip, rolls on notes or bars, previews,
// and hands a roll to the preset manager to keep.
//
// in : type n | chip n | amount v | bright v | motion v | length v | lock k v | chords n | auto n | bars n
//      roll | mutate | undo | redo | hist i | keep | preview          (from the panel)
//      patch <name> <38>  rolled <TYPE>                                (from sid1~)
//      model n                                                         (the device's chip, from the Chip tab)
//      noteon pitch vel | bar                                          (auto roll)
// out: 0 -> sid1~   1 -> panel displays   2 -> preset manager   3 -> Chip tab (0 6581, 1 8580)
autowatch = 0;
inlets = 1;
outlets = 4;

var TYPES = ["LEAD", "BASS", "PAD", "PLUCK", "ARP", "DRUM", "FX", "ANY"];
var NB = 38, HMAX = 8;
var st = { type: 1, chip: 0, amount: 100, bright: 0, motion: 50, length: 0, locks: 0, chords: 3, auto: 0, bars: 4 };
var model = 0, last = null, lastType = "BASS", hlist = [], idx = -1, barCount = 0, kept = 0;
var counters = {};
var noteOff = new Task(function () { outlet(0, "note", 60, 0); }, this);

var status = "";                       // shown on the result screen when nothing has been rolled
function loadbang() { status = "READY"; show(); post("SID1 RANDOM: ready\n"); }
function grab() { last = null; outlet(0, "dump"); return last; }
function patch() {
    var a = arrayfromargs(arguments);
    if (a.length >= NB + 1) last = { n: String(a[0]), b: a.slice(1, NB + 1).map(function (v) { return v | 0; }) };
}
function rolled(t) { lastType = String(t); }

// ---- settings
function type(n) { st.type = Math.max(0, Math.min(7, n | 0)); }
function chip(n) { st.chip = Math.max(0, Math.min(3, n | 0)); }
function amount(v) { st.amount = v; }
function bright(v) { st.bright = v; }
function motion(v) { st.motion = v; }
function length(v) { st.length = v; }
function lock(k, v) { k = k | 0; if (v) st.locks |= (1 << k); else st.locks &= ~(1 << k); }
function chords(n) { st.chords = n | 0; }
function auto(n) { st.auto = n | 0; barCount = 0; }
function bars(n) { st.bars = Math.max(1, n | 0); }
function msg_int(n) {}

// ---- rolling
function chipFor() {
    var m = model;
    if (st.chip == 1) m = 0; else if (st.chip == 2) m = 1; else if (st.chip == 3) m = Math.random() < 0.5 ? 0 : 1;
    if (m != model) { outlet(3, m); model = m; }   // the Chip tab outputs, and the engine follows
    return m;
}
function nameFor(t) {
    counters[t] = ((counters[t] || 0) % 99) + 1;
    return t + " " + (counters[t] < 10 ? "0" : "") + counters[t];
}
function doRoll(amt, t) {
    var m, p, name;
    if (hlist.length == 0) { p = grab(); if (p) { hlist.push({ n: p.n, b: p.b, tag: "ORIGINAL" }); idx = 0; } }
    m = chipFor();
    last = null;
    outlet(0, "roll", t, amt / 100, st.bright / 100, st.motion / 100, st.length / 100, st.locks, st.chords, m);
    if (!last) {
        post("SID1: the sid1~ external did not answer ROLL - replace it with the one from the SID1 kit\n");
        status = "UPDATE_SID1~"; show(); return;
    }
    name = nameFor(lastType);
    outlet(0, "name", name);
    hlist = hlist.slice(0, idx + 1);
    hlist.push({ n: name, b: last.b, tag: lastType });
    while (hlist.length > HMAX) hlist.shift();
    idx = hlist.length - 1;
    kept = 0;
    outlet(2, "rolled", name);
    show();
}
function roll() { if (status != "UPDATE_SID1~") status = ""; doRoll(st.amount, st.type); }
function mutate() {
    var t = TYPES.indexOf(lastType);
    doRoll(20, t < 0 ? st.type : t);
}
function goTo(i) {
    if (i < 0 || i >= hlist.length) return;
    idx = i;
    outlet(0, ["patch", hlist[i].n].concat(hlist[i].b));
    outlet(0, "name", hlist[i].n);
    outlet(0, "dump");
    outlet(2, "rolled", hlist[i].n);
    kept = 0;
    show();
}
function undo() { goTo(idx - 1); }
function redo() { goTo(idx + 1); }
function hist(i) { goTo(i | 0); }
function anything() {
    var a = arrayfromargs(messagename, arguments);
    post("sid1_random: unknown " + messagename + "\n");
}
function keep() {
    if (idx < 0) return;
    outlet(2, "keepnew");
    kept = 1;
    show();
}
function preview() {
    outlet(0, "note", 60, 100);
    noteOff.cancel();
    noteOff.schedule(450);
}

// ---- auto
function noteon(p, v) { if (st.auto == 1 && v > 0) roll(); }
function bar() {
    if (st.auto != 2) return;
    barCount++;
    if (barCount >= st.bars) { barCount = 0; roll(); }
}
function setmodel(m) { model = m ? 1 : 0; }

// ---- displays: history cells and the result
function tags(b) {
    var t = [], w = b[2] >> 4, names = [];
    if (w & 1) names.push("TRI"); if (w & 2) names.push("SAW"); if (w & 4) names.push("PUL"); if (w & 8) names.push("NOI");
    t.push(names.join("+") || "-");
    if (b[3] & 1) {
        var m = b[9] >> 4, mm = [];
        if (m & 1) mm.push("LP"); if (m & 2) mm.push("BP"); if (m & 4) mm.push("HP");
        t.push(mm.join("+") + " " + b[11] + " R" + b[10]);
    } else t.push("NO FILTER");
    if (b[19]) t.push("WT " + b[19]);
    var tr = b[14] > 127 ? b[14] - 256 : b[14];
    if (tr) t.push("TR " + (tr > 0 ? "+" : "") + tr);
    var L = ["OSC", "ENV", "FLT", "PITCH", "WT"];
    for (var k = 0; k < 5; k++) if (st.locks & (1 << k)) t.push("#" + L[k]);   // # = a locked section
    return t;
}
function show() {
    outlet(1, "hist", hlist.length, idx);
    if (idx < 0 || status == "UPDATE_SID1~") { outlet(1, "result", status || "-", 0, 0, 0); return; }
    var h = hlist[idx];
    outlet(1, ["result", h.n.replace(/ /g, "_"), idx + 1, hlist.length, kept].concat(tags(h.b)));
}
function bang() { show(); }
