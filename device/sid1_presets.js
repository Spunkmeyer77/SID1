// SPDX-License-Identifier: GPL-3.0-only
// SID1 preset manager: 4 banks x 32 slots. Factory patches live in sid1~; slots the user saves are kept here and
// stored in the Live set / device preset through a hidden pattr (one string, no files on disk).
//
// in  : slot n | prev | next | bank n | save | cmp n | init | export <path> | import <path> | edited
//       nfactory n | factoryname i sym | patch <name> <38 ints>   (from sid1~)
//       <stored string>                                            (from the pattr)
//       ready                                                      (after loading: allow loads)
// out : 0 -> sid1~   1 -> display jsui   2 -> pattr   3 -> preset number (live.numbox)   4 -> name field (textedit)
autowatch = 0;
inlets = 1;
outlets = 5;

var NSLOT = 128, BANK = 32, NB = 38;
var lib = [];                 // user slots: {n: name, b: [38]} or undefined
var fnames = [];              // factory names
var nfact = 0;
var cur = 0, edited = 0, cmpOn = 0, ready = 0;
var name = "PWM LEAD";
var last = null;              // the patch dump caught from sid1~
var editBuf = null;           // the edit buffer while comparing
var loading = 0;
var restored = 0;            // the set brought a stored state (else: a fresh device)

function clampName(s) {
    s = String(s).toUpperCase().replace(/[^A-Z0-9 +\-.#]/g, "");
    return s.substring(0, 11) || "INIT";
}
function used(i) { return !!lib[i] || i < nfact; }
function slotName(i) { return lib[i] ? lib[i].n : (i < nfact ? fnames[i] : "EMPTY"); }

function show() {
    var b = "ABCD".charAt(Math.floor(cur / BANK)), s = (cur % BANK) + 1;
    outlet(1, "show", b, s, name, edited, cmpOn, lib[cur] ? 1 : (cur < nfact ? 2 : 0));
}

// ---- persistence: "H,cur,edited,name|i,name,hex|..." (names: spaces as _)
function hex(b) { var s = "", i; for (i = 0; i < b.length; i++) s += ("0" + (b[i] & 255).toString(16)).slice(-2); return s; }
function unhex(s) { var b = [], i; for (i = 0; i + 1 < s.length; i += 2) b.push(parseInt(s.substr(i, 2), 16)); return b; }
function store() {
    var parts = ["H," + cur + "," + edited + "," + name.replace(/ /g, "_")], i;
    for (i = 0; i < NSLOT; i++) if (lib[i]) parts.push(i + "," + lib[i].n.replace(/ /g, "_") + "," + hex(lib[i].b));
    outlet(2, parts.join("|"));
}
function restore(str) {
    var parts = String(str).split("|"), i, f;
    if (parts.length < 1 || parts[0].charAt(0) != "H") return;
    lib = [];
    restored = 1;
    f = parts[0].split(",");
    cur = Math.max(0, Math.min(NSLOT - 1, parseInt(f[1], 10) || 0));
    edited = parseInt(f[2], 10) ? 1 : 0;
    name = clampName((f[3] || "INIT").replace(/_/g, " "));
    for (i = 1; i < parts.length; i++) {
        f = parts[i].split(",");
        if (f.length == 3) {
            var b = unhex(f[2]), k = parseInt(f[0], 10);
            if (b.length == NB && k >= 0 && k < NSLOT) lib[k] = { n: clampName(f[1].replace(/_/g, " ")), b: b };
        }
    }
    outlet(4, "set", name);
    show();
}

// ---- engine
function sendPatch(n, b) { outlet(0, ["patch", n].concat(b)); outlet(0, "dump"); }
function grab() { last = null; outlet(0, "dump"); return last; }   // dump answers at once, into patch()
function loadSlot(i) {
    loading = 1;
    cmpOn = 0;
    editBuf = null;
    if (lib[i]) { sendPatch(lib[i].n, lib[i].b); name = lib[i].n; }
    else if (i < nfact) { outlet(0, "factory", i); name = fnames[i]; }
    else { outlet(0, "init"); name = "INIT"; }
    outlet(0, "name", name);
    edited = 0;
    loading = 0;
    outlet(4, "set", name);
    show();
    store();
}

// ---- messages
function slot(n) {
    n = Math.max(0, Math.min(NSLOT - 1, n | 0));
    var changed = n != cur;
    cur = n;
    if (!ready) { show(); return; }        // (while the set loads, the parameters bring the sound back)
    if (changed || !edited) loadSlot(cur); else show();
}
function step(d) {
    var i = cur, k;
    for (k = 0; k < NSLOT; k++) { i = (i + d + NSLOT) % NSLOT; if (used(i)) break; }
    outlet(3, i);                          // the preset number outputs, and comes back as slot
}
function prev() { step(-1); }
function next() { step(1); }
function bank(n) { outlet(3, (Math.max(0, Math.min(3, n | 0)) * BANK) + (cur % BANK)); }

function save() {
    var p;
    if (cmpOn) cmp(0);
    p = grab();
    if (!p) return;
    lib[cur] = { n: name, b: p.b };
    edited = 0;
    show();
    store();
}
function init() { outlet(0, "init"); name = "INIT"; outlet(0, "name", name); outlet(4, "set", name); edited = 1; show(); store(); }

function cmp(on) {
    on = on ? 1 : 0;
    if (on == cmpOn) return;
    if (on) {
        editBuf = grab();
        if (!editBuf) return;
        loading = 1;
        if (lib[cur]) sendPatch(lib[cur].n, lib[cur].b);
        else if (cur < nfact) outlet(0, "factory", cur);
        else outlet(0, "init");
        loading = 0;
    } else if (editBuf) {
        loading = 1;
        sendPatch(editBuf.n, editBuf.b);
        loading = 0;
        editBuf = null;
    }
    cmpOn = on;
    show();
}

function rename() {
    var a = arrayfromargs(arguments);
    name = clampName(a.join(" "));
    outlet(0, "name", name);
    if (!loading) edited = 1;
    show();
    store();
}

function edited_() {}
function anything() {
    var a = arrayfromargs(messagename, arguments);
    if (messagename == "edited") { if (!loading && !cmpOn && ready) { if (!edited) { edited = 1; show(); store(); } } return; }
    if (messagename.charAt(0) == "H" && messagename.indexOf(",") > 0) { restore(a.join(" ")); return; }
    post("sid1_presets: unknown " + messagename + "\n");
}

function nfactory(n) { nfact = n | 0; }
function factoryname(i, s) { fnames[i | 0] = String(s); show(); }
function patch() {
    var a = arrayfromargs(arguments);
    if (a.length >= NB + 1) last = { n: clampName(a[0]), b: a.slice(1, NB + 1).map(function (v) { return v | 0; }) };
}
function bang() { show(); }
function ready_() {}
function msg_int(n) {}

// ready after the set has loaded: from then on the preset number loads presets
function go() { ready = 1; if (!restored) loadSlot(cur); else show(); }

// ---- files: a bank as text, one line a slot: "<slot 1-32> <NAME_WITH_UNDERSCORES> <hex>"
function exportbank(path) {
    var f = new File(path, "write", "TEXT"), b = Math.floor(cur / BANK), i, p;
    if (!f.isopen) { post("SID1: can't write " + path + "\n"); return; }
    f.eof = 0;
    f.writeline("SID1BANK 1");
    for (i = 0; i < BANK; i++) {
        var k = b * BANK + i;
        if (lib[k]) p = lib[k];
        else if (k < nfact) { loading = 1; outlet(0, "factory", k); p = grab(); loading = 0; }
        else continue;
        if (p) f.writeline((i + 1) + " " + p.n.replace(/ /g, "_") + " " + hex(p.b));
    }
    f.close();
    loadSlot(cur);
}
function importbank(path) {
    var f = new File(path, "read", "TEXT"), b = Math.floor(cur / BANK), line, n = 0;
    if (!f.isopen) { post("SID1: can't read " + path + "\n"); return; }
    line = f.readline();
    if (!line || line.indexOf("SID1BANK") != 0) { post("SID1: not a SID1 bank file\n"); f.close(); return; }
    while ((line = f.readline()) != null && f.position <= f.eof) {
        var w = line.split(" ");
        if (w.length == 3) {
            var s = parseInt(w[0], 10) - 1, by = unhex(w[2]);
            if (s >= 0 && s < BANK && by.length == NB) { lib[b * BANK + s] = { n: clampName(w[1].replace(/_/g, " ")), b: by }; n++; }
        }
        if (f.position >= f.eof) break;
    }
    f.close();
    post("SID1: imported " + n + " presets into bank " + "ABCD".charAt(b) + "\n");
    store();
    loadSlot(cur);
}
