// SPDX-License-Identifier: GPL-3.0-only
// SID1 preset display: C64-blue screen. in: show <bank> <slot> <name> <edited> <cmp> <kind 0 empty 1 user 2 factory>
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
var st = { b: "A", s: 1, n: "PWM LEAD", e: 0, c: 0, k: 2 };
function show(b, s, n, e, c, k) { st = { b: String(b), s: s, n: String(n), e: e, c: c, k: k }; mgraphics.redraw(); }
function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1];
    with (mgraphics) {
        set_source_rgb(0.471, 0.412, 0.769); rectangle_rounded(0, 0, w, h, 6, 6); fill();          // #7869C4 border
        set_source_rgb(0.251, 0.192, 0.553); rectangle_rounded(2, 2, w - 4, h - 4, 5, 5); fill();  // #40318D screen
        select_font_face("Courier New Bold"); set_font_size(9);
        set_source_rgb(0.66, 0.62, 0.94);
        move_to(8, 14); show_text("BANK " + st.b + " · " + (st.s < 10 ? "0" : "") + st.s + (st.k == 1 ? "  USER" : st.k == 2 ? "  FACTORY" : ""));
        if (st.c) { set_source_rgb(0.56, 0.66, 1); move_to(w - 52, 14); show_text("COMPARE"); }
        else if (st.e) { set_source_rgb(1, 0.70, 0.28); move_to(w - 48, 14); show_text("EDITED"); }
        set_source_rgb(1, 1, 1); set_font_size(17);
        move_to(8, h - 10); show_text(st.n);
    }
}
