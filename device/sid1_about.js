// SPDX-License-Identifier: GPL-3.0-only
// SID1 About panel: covers the device; a click anywhere closes it (outlet: bang)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
outlets = 1;
var VERSION = "1.0.1";
function hexagon(cx, cy, r) {
    var i, a;
    for (i = 0; i < 6; i++) { a = Math.PI / 3 * i - Math.PI / 2; if (i == 0) mgraphics.move_to(cx + r * Math.cos(a), cy + r * Math.sin(a)); else mgraphics.line_to(cx + r * Math.cos(a), cy + r * Math.sin(a)); }
    mgraphics.close_path();
}
function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1], i;
    with (mgraphics) {
        set_source_rgb(0.08, 0.085, 0.10); rectangle(0, 0, w, h); fill();
        // C64 rainbow stripes
        var cols = [[0.53, 0.22, 0.20], [0.86, 0.45, 0.27], [0.93, 0.94, 0.47], [0.58, 0.88, 0.54], [0.47, 0.41, 0.77]];
        for (i = 0; i < 5; i++) { set_source_rgb(cols[i][0], cols[i][1], cols[i][2]); rectangle(w - 260 + i * 14, 0, 8, h); fill(); }
        set_source_rgb(0.95, 0.95, 0.95); set_line_width(3); hexagon(70, h / 2, 42); stroke();
        select_font_face("Arial Black"); set_font_size(28);
        var t = text_measure("TR"); move_to(70 - t[0] / 2, h / 2 + 10); show_text("TR");
        select_font_face("Courier New Bold"); set_font_size(34); move_to(135, 50); show_text("SID1");
        set_font_size(12); set_source_rgb(0.56, 0.66, 1); move_to(246, 50); show_text("v" + VERSION);
        select_font_face("Arial"); set_font_size(11); set_source_rgb(0.80, 0.82, 0.86);
        var L = ["Dual MOS SID 6581 / 8580 synthesizer — Transistor Labs",
                 "SID core: reSID 0.16 by Dag Lem, via putchdev/sid-1. Player from SID-1.",
                 "Free software, GPL-3.0. Source: github.com/Spunkmeyer77/SID1",
                 "ticcoross@gmail.com"];
        for (i = 0; i < L.length; i++) { move_to(135, 74 + i * 17); show_text(L[i]); }
        set_source_rgb(1, 0.70, 0.28); select_font_face("Arial Bold"); move_to(135, 74 + 4 * 17 + 4); show_text("ticcoross.gumroad.com");
        set_source_rgb(0.55, 0.58, 0.64); select_font_face("Arial"); set_font_size(9); move_to(w - 270 - 110, h - 10); show_text("click to close");
    }
}
function onclick() { outlet(0, "bang"); }
