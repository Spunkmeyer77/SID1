// SPDX-License-Identifier: GPL-3.0-only
// RANDOM history: 8 cells, the current one lit amber; click a cell to go back to it.
// in: hist <count> <current>      out: hist <i>
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
outlets = 1;
var n = 0, cur = -1, N = 8;
function hist(c, i) { n = c | 0; cur = i | 0; mgraphics.redraw(); }
function cellw() { return (box.rect[2] - box.rect[0] - (N - 1) * 3) / N; }
function paint() {
    var h = box.rect[3] - box.rect[1], w = cellw(), i;
    with (mgraphics) {
        for (i = 0; i < N; i++) {
            var x = i * (w + 3);
            if (i == cur && i < n) set_source_rgb(0.23, 0.18, 0.09); else if (i < n) set_source_rgb(0.165, 0.173, 0.196); else set_source_rgb(0.11, 0.114, 0.133);
            rectangle_rounded(x, 0, w, h, 3, 3); fill();
            if (i == cur && i < n) set_source_rgb(1, 0.70, 0.28); else set_source_rgb(0.29, 0.31, 0.35);
            set_line_width(1); rectangle_rounded(x + 0.5, 0.5, w - 1, h - 1, 3, 3); stroke();
            if (i < n) {
                select_font_face("Arial Bold"); set_font_size(7.5);
                set_source_rgb(i == cur ? 1 : 0.79, i == cur ? 0.70 : 0.80, i == cur ? 0.28 : 0.84);
                var s = i == 0 ? "O" : String(i), m = text_measure(s); move_to(x + w / 2 - m[0] / 2, h / 2 + 3); show_text(s);
            }
        }
    }
}
function onclick(x, y) { var i = Math.floor(x / (cellw() + 3)); if (i >= 0 && i < n) outlet(0, "hist", i); }
