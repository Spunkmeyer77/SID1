// SPDX-License-Identifier: GPL-3.0-only
// SID1 envelope: four drawn faders (recessed slot, tick scale, lit fill, metal cap, the SID time below) and the
// envelope's shape above them. The live.sliders that hold the parameters sit on top, invisible; this only draws.
// in: attack|decay|sustain|release <0..15>
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var v = [0, 8, 10, 9];
var ATK = ["2ms", "8ms", "16ms", "24ms", "38ms", "56ms", "68ms", "80ms", "100ms", "250ms", "500ms", "800ms", "1s", "3s", "5s", "8s"];
var DR = ["6ms", "24ms", "48ms", "72ms", "114ms", "168ms", "204ms", "240ms", "300ms", "750ms", "1.5s", "2.4s", "3s", "9s", "15s", "24s"];
var ATK_MS = [2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000];
var NAMES = ["A", "D", "S", "R"];

// layout, shared with build_device.py: faders FX0 + i*FW wide, travel from TOP to BOT
var FW = 28, TOP = 34, BOT = 128, CAPH = 10;

function set(i, n) { v[i] = Math.max(0, Math.min(15, n | 0)); mgraphics.redraw(); }
function attack(n) { set(0, n); }
function decay(n) { set(1, n); }
function sustain(n) { set(2, n); }
function release(n) { set(3, n); }

function label(i) { return i == 0 ? ATK[v[0]] : i == 2 ? Math.round(v[2] * 100 / 15) + "%" : DR[v[i]]; }

function curve(w) {   // the envelope, times on a log scale so short and long both read
    var lg = function (ms) { return Math.log(1 + ms) / Math.log(1 + 24000); };
    var a = lg(ATK_MS[v[0]]), d = lg(ATK_MS[v[1]] * 3), r = lg(ATK_MS[v[3]] * 3), hold = 0.18;
    var tot = a + d + hold + r, x0 = 4, ww = w - 8, y0 = 26, yt = 4, s = v[2] / 15;
    var xa = x0 + ww * a / tot, xd = xa + ww * d / tot, xh = xd + ww * hold / tot, xr = x0 + ww;
    var ys = y0 - (y0 - yt) * s;
    with (mgraphics) {
        set_source_rgba(0.561, 0.659, 1, 0.16);
        move_to(x0, y0); line_to(xa, yt); line_to(xd, ys); line_to(xh, ys); line_to(xr, y0); close_path(); fill();
        set_source_rgb(0.561, 0.659, 1); set_line_width(1.4);
        move_to(x0, y0); line_to(xa, yt); line_to(xd, ys); line_to(xh, ys); line_to(xr, y0); stroke();
        set_source_rgb(1, 0.70, 0.28);
        var pts = [[xa, yt], [xd, ys], [xh, ys]];
        for (var k = 0; k < 3; k++) { ellipse(pts[k][0] - 1.8, pts[k][1] - 1.8, 3.6, 3.6); fill(); }
    }
}

function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1], i, t;
    curve(w);
    for (i = 0; i < 4; i++) {
        var cx = i * FW + FW / 2, frac = v[i] / 15;
        var capY = BOT - frac * (BOT - TOP);           // centre of the cap
        with (mgraphics) {
            // tick scale (left of the slot): long ticks at 0, 5, 10, 15
            for (t = 0; t <= 15; t++) {
                var ty = BOT - t / 15 * (BOT - TOP), long = t % 5 == 0;
                set_source_rgba(0.75, 0.78, 0.85, long ? 0.55 : 0.22);
                rectangle(cx - (long ? 11 : 9), ty - 0.5, long ? 5 : 3, 1); fill();
            }
            // recessed slot
            set_source_rgb(0.06, 0.065, 0.08); rectangle_rounded(cx - 2.5, TOP - 4, 5, BOT - TOP + 8, 3, 3); fill();
            set_source_rgba(1, 1, 1, 0.07); rectangle_rounded(cx - 2.5, TOP - 4, 5, BOT - TOP + 8, 3, 3); set_line_width(1); stroke();
            // lit fill: from the bottom to the cap, with a soft glow
            set_source_rgba(0.561, 0.659, 1, 0.18); rectangle_rounded(cx - 4.5, capY, 9, BOT + 4 - capY, 4, 4); fill();
            set_source_rgb(0.561, 0.659, 1); rectangle_rounded(cx - 1.5, capY, 3, BOT + 3 - capY, 2, 2); fill();
            // cap: shadow, metal body, grip lines, lit centre line
            set_source_rgba(0, 0, 0, 0.45); rectangle_rounded(cx - 10, capY - CAPH / 2 + 1.5, 20, CAPH, 2.5, 2.5); fill();
            var g = pattern_create_linear(0, capY - CAPH / 2, 0, capY + CAPH / 2);
            g.add_color_stop_rgba(0, 0.92, 0.93, 0.95, 1);
            g.add_color_stop_rgba(0.5, 0.70, 0.72, 0.76, 1);
            g.add_color_stop_rgba(1, 0.48, 0.50, 0.55, 1);
            set_source(g); rectangle_rounded(cx - 10, capY - CAPH / 2, 20, CAPH, 2.5, 2.5); fill();
            set_source_rgba(0, 0, 0, 0.25);
            rectangle(cx - 7, capY - 3, 14, 0.8); fill(); rectangle(cx - 7, capY + 2.2, 14, 0.8); fill();
            set_source_rgb(0.08, 0.09, 0.11); rectangle(cx - 9, capY - 0.6, 18, 1.2); fill();
            // name and value
            select_font_face("Arial Bold"); set_font_size(8);
            set_source_rgb(0.95, 0.95, 0.95);
            var s = label(i), m = text_measure(s); move_to(cx - m[0] / 2, h - 1); show_text(s);
            set_source_rgb(0.60, 0.63, 0.67); set_font_size(7.5);
            m = text_measure(NAMES[i]); move_to(cx - m[0] / 2, BOT + 11); show_text(NAMES[i]);
        }
    }
}
