// SPDX-License-Identifier: GPL-3.0-only
// The C64 rainbow, as on the About panel: slanted stripes, drawn as vectors
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
var COLS = [[0.53, 0.22, 0.20], [0.86, 0.45, 0.27], [0.93, 0.94, 0.47], [0.58, 0.88, 0.54], [0.47, 0.41, 0.77]];
function paint() {
    var w = box.rect[2] - box.rect[0], h = box.rect[3] - box.rect[1], i, sw = 6, gap = 3, slant = h * 0.6;
    with (mgraphics) {
        for (i = 0; i < 5; i++) {
            var x = w - slant - (5 - i) * (sw + gap);
            set_source_rgb(COLS[i][0], COLS[i][1], COLS[i][2]);
            move_to(x, h); line_to(x + sw, h); line_to(x + sw + slant, 0); line_to(x + slant, 0); close_path(); fill();
        }
    }
}
