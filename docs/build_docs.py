#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builds the SID1 user manual and update history PDFs. Usage: python3 docs/build_docs.py <SID1.amxd> <outdir>"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, KeepTogether, Table, TableStyle)

VERSION = "1.0.1"
amxd, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)

# ---- a colour picture of the panel, drawn from the device's own layout
d = open(amxd, "rb").read()
j = json.loads(d[d.index(b"{"):].rstrip(b"\n\x00"))
S, W, H = 3, 1065, 169
im = Image.new("RGB", (W * S, H * S), (30, 32, 37))
dr = ImageDraw.Draw(im)
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 8 * S)
    small = ImageFont.truetype("DejaVuSans.ttf", 6 * S)
except OSError:
    font = small = ImageFont.load_default()
rgb = lambda c: tuple(int(v * 255) for v in c[:3])
for b in j["patcher"]["boxes"]:
    b = b["box"]
    if not b.get("presentation") or b.get("hidden"):
        continue
    x, y, w, h = [v * S for v in b["presentation_rect"]]
    k = b["maxclass"]
    if k == "panel":
        dr.rectangle([x, y, x + w - 1, y + h - 1], fill=rgb(b["bgcolor"]))
    elif k == "live.comment":
        dr.text((x, y), b["text"][:40], fill=rgb(b["textcolor"]), font=font if b.get("fontface") else small)
    elif k == "live.dial":
        r = min(w, h - 16 * S) / 2 - S
        cx, cy = x + w / 2, y + 10 * S + r
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(42, 44, 50), outline=rgb(b["activedialcolor"]), width=2 * S)
        dr.line([cx, cy, cx, cy - r + 2 * S], fill=(240, 240, 240), width=S)
        dr.text((x + 2 * S, y), b["saved_attribute_attributes"]["valueof"]["parameter_shortname"], fill=(200, 204, 214), font=small)
    elif k == "live.text":
        on = b["saved_attribute_attributes"]["valueof"]["parameter_initial"][0]
        dr.rounded_rectangle([x, y, x + w, y + h], 3 * S, fill=rgb(b["bgoncolor"]) if on else (42, 44, 50), outline=rgb(b["bordercolor"]))
        dr.text((x + 3 * S, y + 3 * S), b["text"][:22], fill=(20, 22, 26) if on else (200, 204, 214), font=small)
    elif k == "live.tab":
        items = b["saved_attribute_attributes"]["valueof"]["parameter_enum"]
        cw = w / len(items)
        for i, t in enumerate(items):
            dr.rectangle([x + i * cw, y, x + (i + 1) * cw - S, y + h], fill=rgb(b["bgoncolor"]) if i == 0 else (42, 44, 50))
            dr.text((x + i * cw + 3 * S, y + 3 * S), t, fill=(20, 22, 26) if i == 0 else (200, 204, 214), font=small)
    elif k == "live.slider":
        dr.rectangle([x + w / 2 - 3 * S, y + 10 * S, x + w / 2 + 3 * S, y + h - 12 * S], fill=(42, 44, 50), outline=(74, 78, 88))
        dr.rectangle([x + w / 2 - 3 * S, y + h / 2, x + w / 2 + 3 * S, y + h - 12 * S], fill=(143, 168, 255))
        dr.text((x + w / 2 - 3 * S, y + h - 10 * S), b["saved_attribute_attributes"]["valueof"]["parameter_shortname"], fill=(200, 204, 214), font=small)
    elif k in ("live.numbox", "live.menu", "textedit"):
        dr.rectangle([x, y, x + w, y + h], fill=(28, 29, 34), outline=(74, 78, 88))
    elif k == "jsui" and "display" in b["filename"]:
        dr.rounded_rectangle([x, y, x + w, y + h], 6 * S, fill=(64, 49, 141), outline=(120, 105, 196), width=2 * S)
        dr.text((x + 8 * S, y + 6 * S), "BANK A · 01  FACTORY", fill=(169, 158, 240), font=small)
        dr.text((x + 8 * S, y + 22 * S), "PWM LEAD", fill=(255, 255, 255), font=ImageFont.truetype("DejaVuSansMono-Bold.ttf", 15 * S))
    elif k == "jsui" and "stripes" in b["filename"]:
        cols = [(135, 56, 51), (219, 115, 69), (237, 240, 120), (148, 224, 138), (120, 105, 196)]
        sl = h * 0.6
        for i, c in enumerate(cols):
            xx = x + w - sl - (5 - i) * 9 * S
            dr.polygon([(xx, y + h), (xx + 6 * S, y + h), (xx + 6 * S + sl, y), (xx + sl, y)], fill=c)
    elif k == "jsui" and "logo" in b["filename"]:
        dr.text((x + 4 * S, y + 4 * S), "⬡ SID1", fill=(240, 240, 240), font=ImageFont.truetype("DejaVuSansMono-Bold.ttf", 16 * S))
pic = os.path.join(outdir, "panel.png")
im.save(pic)

# ---- styles
BL = colors.HexColor("#40318D")
st = {
    "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=BL),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=12, leading=16, textColor=colors.HexColor("#555555")),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=BL, spaceBefore=10, spaceAfter=5),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=5),
    "b": ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=14, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "cap": ParagraphStyle("c", fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=colors.HexColor("#666666")),
}


def chapter(title, *items):
    """a chapter: kept on one page (moved whole to the next page if it doesn't fit)"""
    out = [Paragraph(title, st["h"])]
    for it in items:
        if isinstance(it, str):
            out.append(Paragraph(it, st["p"]))
        elif isinstance(it, list):
            out += [Paragraph(x, st["b"], bulletText="•") for x in it]
        else:
            out.append(it)
    return KeepTogether(out)


def table(rows, widths):
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=12)
    head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=9, leading=12)
    rows = [[Paragraph(c, head if r == 0 or i == 0 else cell) for i, c in enumerate(row)] for r, row in enumerate(rows)]
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 9), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E6F7")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBCC")), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def footer(c, doc):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawString(18 * mm, 10 * mm, "SID1 %s — Transistor Labs — ticcoross.gumroad.com" % VERSION)
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    c.restoreState()


P = lambda s: Paragraph(s, st["p"])
img_w = A4[0] - 36 * mm
story = [
    Paragraph("SID1", st["title"]),
    Paragraph("Dual MOS SID synthesizer for Ableton Live — User Manual, version %s" % VERSION, st["sub"]),
    Spacer(1, 8),
    RLImage(pic, width=img_w, height=img_w * H / W),
    Paragraph("Figure 1. The SID1 panel.", st["cap"]),
    chapter("Introduction",
            "SID1 is a Max for Live instrument built on two emulated MOS SID chips, the sound chip of the Commodore 64. "
            "Each chip has three voices, so SID1 plays up to six notes at once. Choose the original 6581 chip, with its "
            "dirty, characterful filter, or the cleaner 8580.",
            "Sounds are played the way C64 music players played them: 50 times a second, SID1 updates each voice's "
            "pulse width, filter cutoff, vibrato and wavetable. That is where the classic arpeggios, drum sounds and "
            "sweeping leads come from."),
    chapter("System Requirements",
            ["Ableton Live 12 Suite, or Live 12 Standard with Max for Live",
             "macOS 10.13 or later, Intel or Apple Silicon",
             "Windows 10 or 11, 64-bit",
             "SID1 runs on a computer only: it does not run on Push 3 in Standalone Mode (Push 3 works in Control Mode)."]),
    chapter("Installation",
            "Drag <b>SID1.amxd</b> onto a MIDI track in Live, or put it in your User Library to keep it in the browser.",
            "<b>macOS security warning.</b> SID1 contains a compiled sound engine that is not notarised by Apple. If macOS "
            "says the component “cannot be opened because the developer cannot be verified”, open System Settings "
            "› Privacy &amp; Security, scroll to the message about sid1~, click <b>Open Anyway</b>, then load the "
            "device again. On older macOS versions this is in System Preferences › Security &amp; Privacy › General."),
    chapter("The Panel",
            table([["Section", "What it does"],
                   ["Brand", "CHIP: 6581 or 8580. POLY (six voices) or MONO (one voice, legato). 2X: oversampling, a cleaner top end for more CPU. VOL: output level. BEND: pitch bend range in semitones. ABOUT: version and credits. The store link opens ticcoross.gumroad.com."],
                   ["Preset", "The display shows bank, slot, name, and EDITED when the sound differs from its slot. See Presets."],
                   ["Oscillator", "TRI, SAW, PUL, NOI: the waveforms (combine them for the SID's mixed waves). RING: ring modulation. SYNC: hard sync. HARD: hard restart, which makes every note attack cleanly. PW: pulse width. SPEED, MIN, MAX: the pulse-width sweep."],
                   ["Envelope", "Attack, Decay, Sustain, Release in the chip's 16 steps, shown as the real SID times: attack 2 ms to 8 s, decay and release 6 ms to 24 s, sustain as a level in %."],
                   ["Filter", "ON sends the voices through the filter. LP, BP, HP: the modes, which can be combined. CUTOFF, RES. SWEEP moves the cutoff each frame from CUTOFF towards END."],
                   ["Pitch · Vibrato", "DEPTH (cents), SPEED and DELAY (frames before it starts). TRANS: transpose in semitones. FINE: tuning in cents."],
                   ["Wavetable", "Up to 8 steps, one per frame (1/50 s). Each step sets a waveform (· keeps the patch's) and a note: an offset from the key played, or with ABS an absolute note. LENGTH: steps used. LOOP: the step to jump back to after the last."]],
                  [32 * mm, img_w - 32 * mm])),
    chapter("Presets",
            "SID1 has 4 banks (A–D) of 32 presets. Bank A starts with 16 factory sounds: leads, basses, pads, arpeggios and drums.",
            ["Choose a preset with the number box, the arrow buttons (they skip empty slots), or a bank button.",
             "Edit any control: the display shows EDITED.",
             "Type a name in NAME and press Return.",
             "SAVE stores the sound in the current slot. CMP switches between your edit and the stored sound.",
             "INIT starts from a plain sound.",
             "EXP saves the current bank to a text file. IMP loads a bank file into the current bank, to back up or share sounds."],
            "Your presets are saved with the Live Set and in Live device presets, so they travel with your projects. "
            "The preset number can be automated, to change sounds during a song."),
    chapter("Tips",
            ["Arpeggio chords from one key: wavetable LENGTH 3, notes 0, 4, 7, LOOP 1. See factory ARP MAJOR.",
             "Drums: a first step of NOI with a high ABS note, then TRI or PUL steps falling in pitch. See KICK and SNARE.",
             "The famous noise attack: step 1 NOI two octaves up, step 2 the patch's own wave. See NOISE LEAD.",
             "Filtered sounds on the 6581 vary from chip to chip on real hardware; SID1 models a typical one."]),
    chapter("Automation and MIDI",
            "Every control is a Live parameter: automate it, map it to MIDI (Cmd/Ctrl+M) or to Push in Control Mode. "
            "SID1 responds to notes and pitch bend on any channel."),
    chapter("Credits and Licence",
            "SID1 is free software under the GNU General Public License, version 3. Its source code is at "
            "<b>github.com/Spunkmeyer77/SID1</b>. The SID chip emulation is reSID 0.16 by Dag Lem (GPL-2.0-or-later), "
            "through the C port in SID-1 by the SID-1 authors (putchdev/sid-1), whose patch player SID1 also uses.",
            "Commodore 64 is a trademark of its owners; SID1 is not made or endorsed by them.",
            "Contact: ticcoross@gmail.com — more devices: ticcoross.gumroad.com"),
]
doc = SimpleDocTemplate(os.path.join(outdir, "SID1 User Manual.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=16 * mm, bottomMargin=18 * mm, title="SID1 User Manual", author="Transistor Labs")
doc.build(story, onFirstPage=footer, onLaterPages=footer)

# ---- update history (no dates)
HISTORY = [("1.0.1", ["The filter cutoff knob now acts at once on held notes (before, only from the next note).",
                      "Envelope faders are vertical and show the SID's real times (attack 2 ms to 8 s, decay and release 6 ms to 24 s, sustain in %).",
                      "C64 rainbow stripes on the panel.",
                      "The preset name field no longer shows quotes; an overlapping help text is gone."]),
           ("1.0.0", ["First release.",
                      "Two SID chips (reSID 0.16), 6581 or 8580, six voices, poly or mono legato.",
                      "C64-style patch player: wavetable, pulse-width sweep, filter sweep, vibrato, hard restart.",
                      "Presets: 4 banks of 32 with 16 factory sounds, save, compare, init, bank import and export.",
                      "2x oversampling, pitch bend range, every control automatable."])]
story = [Paragraph("SID1 — Update History", st["title"]), Spacer(1, 10)]
for v, items in HISTORY:
    story.append(chapter("Version " + v, items))
doc = SimpleDocTemplate(os.path.join(outdir, "SID1 Update History.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=16 * mm, bottomMargin=18 * mm, title="SID1 Update History", author="Transistor Labs")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("docs written to", outdir)
