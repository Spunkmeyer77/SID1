// SPDX-License-Identifier: GPL-3.0-only
// SID1 knob: a metal cap like the envelope faders' (shading, shadow, dark pointer), a lit arc with tick dots, the
// name above and the value below. An invisible live.dial on top takes the mouse; this only draws.
// args: lo hi initial accent(0 blue, 1 amber) name unit(0 integer, 1 dB)     in: a number (the value)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var a = jsarguments;
var LO = a.length > 1 ? Number(a[1]) : 0, HI = a.length > 2 ? Number(a[2]) : 127;
var val = a.length > 3 ? Number(a[3]) : 0;
var AMBER = a.length > 4 && Number(a[4]) == 1;
var NAME = a.length > 5 ? String(a[5]) : "";
var UNIT = a.length > 6 ? Number(a[6]) : 0;
var A0 = Math.PI * 0.75, SPAN = Math.PI * 1.5;     // 7:30 to 4:30, clockwise

function msg_float(v) { val = v; mgraphics.redraw(); }
function msg_int(v) { val = v; mgraphics.redraw(); }

function text() {
    if (UNIT == 1) return val <= -69.5 ? "-inf" : (Math.round(val * 10) / 10).toFixed(1) + " dB";
    var n = Math.round(val);
    return (LO < 0 && n > 0 ? "+" : "") + n;
}

function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1];
    var cx = w / 2, cy = h / 2 + 1, r = Math.min(w / 2 - 6, (h - 22) / 2);
    var frac = HI > LO ? Math.max(0, Math.min(1, (val - LO) / (HI - LO))) : 0;
    var lit = AMBER ? [1, 0.70, 0.28] : [0.561, 0.659, 1];
    var from = LO < 0 && HI > 0 ? (0 - LO) / (HI - LO) : 0;   // bipolar knobs light from the centre
    var i, t, ang;
    with (mgraphics) {
        // tick dots around
        for (i = 0; i <= 10; i++) {
            ang = A0 + SPAN * i / 10;
            var on = (i / 10 >= Math.min(from, frac) - 0.001) && (i / 10 <= Math.max(from, frac) + 0.001);
            if (on) set_source_rgb(lit[0], lit[1], lit[2]); else set_source_rgba(0.75, 0.78, 0.85, 0.25);
            ellipse(cx + (r + 5) * Math.cos(ang) - 0.9, cy + (r + 5) * Math.sin(ang) - 0.9, 1.8, 1.8); fill();
        }
        // track and lit arc
        set_line_width(2.2);
        set_source_rgb(0.06, 0.065, 0.08); arc(cx, cy, r + 2, A0, A0 + SPAN); stroke();
        set_source_rgb(lit[0], lit[1], lit[2]);
        var s0 = A0 + SPAN * Math.min(from, frac), s1 = A0 + SPAN * Math.max(from, frac);
        if (s1 - s0 > 0.01) { arc(cx, cy, r + 2, s0, s1); stroke(); }
        // cap: shadow, metal body, rim, pointer
        set_source_rgba(0, 0, 0, 0.45); ellipse(cx - r + 1, cy - r + 2, 2 * r - 2, 2 * r - 2); fill();
        var g = pattern_create_linear(0, cy - r, 0, cy + r);
        g.add_color_stop_rgba(0, 0.92, 0.93, 0.95, 1);
        g.add_color_stop_rgba(0.5, 0.70, 0.72, 0.76, 1);
        g.add_color_stop_rgba(1, 0.48, 0.50, 0.55, 1);
        set_source(g); ellipse(cx - r + 2, cy - r + 2, 2 * r - 4, 2 * r - 4); fill();
        set_source_rgba(1, 1, 1, 0.35); set_line_width(0.8); ellipse(cx - r + 2.5, cy - r + 2.5, 2 * r - 5, 2 * r - 5); stroke();
        ang = A0 + SPAN * frac;
        set_source_rgb(0.08, 0.09, 0.11); set_line_width(2);
        move_to(cx + (r * 0.25) * Math.cos(ang), cy + (r * 0.25) * Math.sin(ang));
        line_to(cx + (r - 3) * Math.cos(ang), cy + (r - 3) * Math.sin(ang)); stroke();
        // name and value
        select_font_face("Arial Bold"); set_font_size(8);
        set_source_rgb(0.79, 0.80, 0.84);
        t = text_measure(NAME); move_to(cx - t[0] / 2, 8); show_text(NAME);
        set_source_rgb(0.95, 0.95, 0.95);
        var s = text(); t = text_measure(s); move_to(cx - t[0] / 2, h - 1); show_text(s);
    }
}
