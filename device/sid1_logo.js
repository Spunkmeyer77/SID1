// SPDX-License-Identifier: GPL-3.0-only
// Transistor Labs hexagon "TR" + the SID1 name, drawn as vectors (no image files, survives freezing)
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
function paint() {
    var cx = 12, cy = 14, r = 11, i, a;
    with (mgraphics) {
        set_source_rgb(0.95, 0.95, 0.95); set_line_width(1.6);
        for (i = 0; i < 6; i++) { a = Math.PI / 3 * i - Math.PI / 2; if (i == 0) move_to(cx + r * Math.cos(a), cy + r * Math.sin(a)); else line_to(cx + r * Math.cos(a), cy + r * Math.sin(a)); }
        close_path(); stroke();
        select_font_face("Arial Black"); set_font_size(8);
        var t = text_measure("TR"); move_to(cx - t[0] / 2, cy + 3); show_text("TR");
        select_font_face("Courier New Bold"); set_font_size(20);
        move_to(30, cy + 7); show_text("SID1");
    }
}
