// SPDX-License-Identifier: GPL-3.0-only
// RANDOM result: the C64-blue screen with the roll's name, its place in the history, and tags (# = locked).
// in: result <NAME_> <i> <count> <kept> <tags...>    free <slot>
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
var name = "-", i = 0, n = 0, kept = 0, tags = [], free = "";
function result() {
    var a = arrayfromargs(arguments);
    name = String(a[0]).replace(/_/g, " "); i = a[1] | 0; n = a[2] | 0; kept = a[3] | 0; tags = a.slice(4).map(String);
    mgraphics.redraw();
}
function free_(s) {}
function anything() { if (messagename == "free") { free = String(arguments[0]); mgraphics.redraw(); } }
function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1], k, x, y;
    with (mgraphics) {
        set_source_rgb(0.471, 0.412, 0.769); rectangle_rounded(0, 0, w, 44, 6, 6); fill();
        set_source_rgb(0.251, 0.192, 0.553); rectangle_rounded(2, 2, w - 4, 40, 5, 5); fill();
        select_font_face("Courier New Bold"); set_font_size(9);
        set_source_rgb(0.66, 0.62, 0.94); move_to(8, 14);
        show_text(n ? (i == 1 ? "ORIGINAL" : "ROLL " + (i - 1) + " OF " + (n - 1)) : "PRESS ROLL");
        if (n) {
            if (kept) { set_source_rgb(0.56, 0.88, 0.54); move_to(w - 40, 14); show_text("KEPT"); }
            else { set_source_rgb(1, 0.70, 0.28); move_to(w - 64, 14); show_text("NOT SAVED"); }
        }
        set_source_rgb(1, 1, 1); set_font_size(17); move_to(8, 35); show_text(n ? name : "SID1");
        // tags
        select_font_face("Arial Bold"); set_font_size(7.5);
        x = 0; y = 50;
        for (k = 0; k < tags.length; k++) {
            var t = tags[k], lockd = t.charAt(0) == "#";
            if (lockd) t = t.substring(1) + " LOCKED";
            var m = text_measure(t), tw = m[0] + 8;
            if (x + tw > w) { x = 0; y += 15; }
            if (y + 12 > h) break;
            if (lockd) set_source_rgb(0.23, 0.18, 0.09); else set_source_rgb(0.165, 0.173, 0.196);
            rectangle_rounded(x, y, tw, 12, 3, 3); fill();
            if (lockd) set_source_rgb(1, 0.70, 0.28); else set_source_rgb(0.95, 0.95, 0.95);
            move_to(x + 4, y + 9); show_text(t);
            x += tw + 4;
        }
        if (free) {
            set_source_rgb(0.60, 0.63, 0.67); set_font_size(7.5);
            var s = "KEEP saves to " + free; m = text_measure(s); move_to(w - m[0], h - 2); show_text(s);
        }
    }
}
