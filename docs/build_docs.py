#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builds the SID1 user manual and update history PDFs. Usage: python3 docs/build_docs.py <SID1.amxd> <outdir>"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, KeepTogether, Table, TableStyle, PageBreak)

VERSION = "1.1.2"
amxd, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)

# ---- a colour picture of the panel, drawn from the device's own layout
d = open(amxd, "rb").read()
j = json.loads(d[d.index(b"{"):].rstrip(b"\n\x00"))
S, W, H = 3, 1065, 169
def render(boxlist, fname):
    im = Image.new("RGB", (W * S, H * S), (30, 32, 37))
    dr = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 8 * S)
        small = ImageFont.truetype("DejaVuSans.ttf", 6 * S)
    except OSError:
        font = small = ImageFont.load_default()
    rgb = lambda c: tuple(int(v * 255) for v in c[:3])
    for b in boxlist:
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
            dr.arc([cx - r - 2 * S, cy - r - 2 * S, cx + r + 2 * S, cy + r + 2 * S], 135, 405, fill=(15, 16, 20), width=2 * S)
            dr.arc([cx - r - 2 * S, cy - r - 2 * S, cx + r + 2 * S, cy + r + 2 * S], 135, 270, fill=(143, 168, 255), width=2 * S)
            dr.ellipse([cx - r + 2 * S, cy - r + 2 * S, cx + r - 2 * S, cy + r - 2 * S], fill=(188, 191, 198), outline=(225, 227, 232))
            dr.line([cx, cy - 2 * S, cx, cy - r + 4 * S], fill=(20, 22, 28), width=2 * S)
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
        elif k == "live.slider" and not b.get("showname", 1):
            pass                                # (invisible: drawn by the ADSR jsui)
        elif k == "jsui" and "adsr" in b["filename"]:
            vals = [0, 8, 10, 9]; labels = ["2ms", "300ms", "67%", "750ms"]
            top, bot = y + 34 * S, y + 128 * S
            # envelope shape
            pts = [(x + 4 * S, y + 26 * S), (x + 14 * S, y + 4 * S), (x + 48 * S, y + 11 * S), (x + 66 * S, y + 11 * S), (x + w - 4 * S, y + 26 * S)]
            dr.polygon(pts, fill=(48, 56, 92)); dr.line(pts, fill=(143, 168, 255), width=2 * S)
            for i2, vv in enumerate(vals):
                cx = x + (i2 * 28 + 14) * S
                for t in range(16):
                    ty = bot - t / 15 * (bot - top); lg = t % 5 == 0
                    dr.rectangle([cx - (11 if lg else 9) * S, ty, cx - (6 if lg else 6) * S, ty + S - 1], fill=(150, 155, 168) if lg else (80, 84, 96))
                dr.rounded_rectangle([cx - 2.5 * S, top - 4 * S, cx + 2.5 * S, bot + 4 * S], 3 * S, fill=(15, 16, 20))
                cy = bot - vv / 15 * (bot - top)
                dr.rounded_rectangle([cx - 1.5 * S, cy, cx + 1.5 * S, bot + 3 * S], 2 * S, fill=(143, 168, 255))
                dr.rounded_rectangle([cx - 10 * S, cy - 5 * S, cx + 10 * S, cy + 5 * S], 3 * S, fill=(190, 193, 200))
                dr.rectangle([cx - 9 * S, cy - 0.6 * S, cx + 9 * S, cy + 0.6 * S], fill=(20, 22, 28))
                dr.text((cx - 3 * S, bot + 4 * S), "ADSR"[i2], fill=(150, 155, 168), font=small)
                dr.text((cx - 11 * S, y + h - 9 * S), labels[i2], fill=(240, 240, 240), font=small)
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
        elif k == "jsui" and "rresult" in b["filename"]:
            dr.rounded_rectangle([x, y, x + w, y + 44 * S], 6 * S, fill=(64, 49, 141), outline=(120, 105, 196), width=2 * S)
            dr.text((x + 8 * S, y + 5 * S), "ROLL 3 OF 5", fill=(169, 158, 240), font=small)
            dr.text((x + w - 60 * S, y + 5 * S), "NOT SAVED", fill=(255, 179, 71), font=small)
            dr.text((x + 8 * S, y + 18 * S), "BASS 07", fill=(255, 255, 255), font=ImageFont.truetype("DejaVuSansMono-Bold.ttf", 15 * S))
            tx = x
            for t, lk in (("SAW+PUL", 0), ("LP 96 R9", 0), ("ENV LOCKED", 1)):
                tw = len(t) * 5 * S + 8 * S
                dr.rounded_rectangle([tx, y + 50 * S, tx + tw, y + 62 * S], 3 * S, fill=(58, 46, 24) if lk else (42, 44, 50))
                dr.text((tx + 4 * S, y + 51 * S), t, fill=(255, 179, 71) if lk else (240, 240, 240), font=small)
                tx += tw + 4 * S
        elif k == "jsui" and "rhist" in b["filename"]:
            cw = (w - 7 * 3 * S) / 8
            for i2 in range(8):
                xx = x + i2 * (cw + 3 * S)
                dr.rounded_rectangle([xx, y, xx + cw, y + h], 3 * S, fill=(58, 46, 24) if i2 == 3 else (42, 44, 50) if i2 < 5 else (28, 29, 34),
                                     outline=(255, 179, 71) if i2 == 3 else (74, 78, 88))
        elif k == "jsui" and "stripes" in b["filename"]:
            cols = [(135, 56, 51), (219, 115, 69), (237, 240, 120), (148, 224, 138), (120, 105, 196)]
            sl = h * 0.6
            for i, c in enumerate(cols):
                xx = x + w - sl - (5 - i) * 9 * S
                dr.polygon([(xx, y + h), (xx + 6 * S, y + h), (xx + 6 * S + sl, y), (xx + sl, y)], fill=c)
        elif k == "jsui" and "logo" in b["filename"]:
            dr.text((x + 4 * S, y + 4 * S), "⬡ SID1", fill=(240, 240, 240), font=ImageFont.truetype("DejaVuSansMono-Bold.ttf", 16 * S))
    im.save(fname)
    return fname

pic = render(j["patcher"]["boxes"], os.path.join(outdir, "panel.png"))
_rp = []
for b in j["patcher"]["boxes"]:              # the RANDOM panel: the hidden controls (not the About overlay)
    if b["box"].get("hidden") and b["box"].get("varname") != "about":
        bb = dict(b["box"]); bb.pop("hidden"); _rp.append({"box": bb})
rpic = render(_rp, os.path.join(outdir, "random.png")) if _rp else None

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


def cover(c, doc):
    """page 1: a dark cover with the C64 rainbow, the Transistor Labs hexagon and the title"""
    import math
    pw, ph = A4
    c.saveState()
    c.setFillColor(colors.HexColor("#15161A")); c.rect(0, 0, pw, ph, stroke=0, fill=1)
    cols = ["#873833", "#DB7345", "#EDF078", "#94E08A", "#7869C4"]
    sw, gap, x0 = 16 * mm, 4 * mm, pw * 0.42
    for i, col in enumerate(cols):
        x = x0 + i * (sw + gap)
        c.setFillColor(colors.HexColor(col))
        p = c.beginPath(); p.moveTo(x, 0); p.lineTo(x + sw, 0); p.lineTo(x + sw + pw * 0.45, ph); p.lineTo(x + pw * 0.45, ph); p.close()
        c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#40318D")); c.rect(0, ph * 0.30, pw, ph * 0.40, stroke=0, fill=1)
    cx, cy, r = 34 * mm, ph * 0.61, 13 * mm
    c.setStrokeColor(colors.white); c.setLineWidth(3)
    p = c.beginPath()
    for i in range(6):
        a = math.pi / 3 * i + math.pi / 2
        (p.moveTo if i == 0 else p.lineTo)(cx + r * math.cos(a), cy + r * math.sin(a))
    p.close(); c.drawPath(p, stroke=1, fill=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 20); c.drawCentredString(cx, cy - 7, "TR")
    c.setFont("Courier-Bold", 96); c.drawString(20 * mm, ph * 0.43, "SID1")
    c.setFont("Helvetica", 15); c.setFillColor(colors.HexColor("#C9C4F5"))
    c.drawString(21 * mm, ph * 0.38, "Dual MOS SID synthesizer for Max for Live")
    c.drawString(21 * mm, ph * 0.38 - 20, "User Manual \u2014 version %s" % VERSION)
    for i, col in enumerate(cols):
        c.setFillColor(colors.HexColor(col)); c.rect(0, ph * 0.30 - (i + 1) * 3 * mm, pw, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 13); c.drawString(20 * mm, 22 * mm, "Transistor Labs")
    c.setFillColor(colors.HexColor("#FFB347")); c.setFont("Helvetica", 11); c.drawString(20 * mm, 16 * mm, "ticcoross.gumroad.com")
    c.restoreState()


P = lambda s: Paragraph(s, st["p"])
img_w = A4[0] - 36 * mm
story = [
    PageBreak(),
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
    chapter("What Is a SID?",
            "The SID (Sound Interface Device) is the sound chip of the Commodore 64, the best-selling home computer of all "
            "time. It was designed in 1981 by Bob Yannes at MOS Technology, Commodore's chip maker, and arrived in the C64 "
            "in 1982. Yannes, a synthesizer enthusiast, built it as a small synth on a chip rather than the simple beepers "
            "of other computers of the time; he later co-founded the synth maker Ensoniq.",
            "Each SID has three voices. Every voice has an oscillator with four waveforms (triangle, sawtooth, pulse with "
            "variable width, and noise), its own ADSR envelope, ring modulation and hard sync. The three voices share one "
            "analogue multimode filter (low-pass, band-pass, high-pass) with resonance. Three voices is not much, so C64 "
            "composers learned tricks: fast arpeggios that sound like chords, drums built from a frame of noise and a "
            "falling pitch, pulse-width sweeps for movement, and the filter swept by software.",
            "Composers such as Rob Hubbard, Martin Galway, Ben Daglish, Chris H\u00fclsbeck and Jeroen Tel turned these "
            "limits into a style of their own in 1980s game music. The demoscene kept it alive, and the SID sound is still "
            "loved today in chiptune, electro and techno. SID1 plays the chip the way those composers did: a player program "
            "updates every voice 50 times a second, the PAL C64's screen rate."),
    chapter("The Two SID Chips: 6581 and 8580",
            "The C64 was built with two different SID chips, and they sound clearly different. Musicians have strong "
            "preferences, so SID1 lets you choose with the CHIP switch.",
            table([["", "6581 (1982\u201386)", "8580 (from 1986, C64C)"],
                   ["Filter", "Analogue and imprecise: dark, gritty, slightly distorted. Real chips varied from one to another.",
                    "Cleaner and more predictable, with stronger, sharper resonance. More \u201csynth-like\u201d."],
                   ["DC offset", "Strong. A side effect let programmers play drum samples through the volume register.",
                    "Almost none: those volume-register samples are nearly silent."],
                   ["Combined waveforms", "Weak and thin (saw+triangle and the like).", "Louder and much more usable."],
                   ["Classic use", "Most famous C64 music was written on and for the 6581.", "Later C64 models and many modern SID players."]],
                  [30 * mm, (img_w - 30 * mm) / 2, (img_w - 30 * mm) / 2]),
            Spacer(1, 4),
            "A tune written for one chip can sound wrong on the other: filters too muddy or too sharp, or samples missing. "
            "In SID1, treat the switch as a character choice: the <b>6581</b> for warm, dirty classic C64 basses and leads, "
            "the <b>8580</b> for cleaner, resonant filter sweeps and the combined waveforms. Switching the chip mutes the "
            "output for a moment, to hide the thump of the 6581's DC offset."),
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
                   ["RANDOM", "Opens the RANDOM panel: new patches by the rules. See the chapter Random."],
                   ["Preset", "The display shows bank, slot, name, and EDITED when the sound differs from its slot. See Presets."],
                   ["Oscillator", "TRI, SAW, PUL, NOI: the waveforms (combine them for the SID's mixed waves). RING: ring modulation. SYNC: hard sync. HARD: hard restart, which makes every note attack cleanly. PW: pulse width. SPEED, MIN, MAX: the pulse-width sweep."],
                   ["Envelope", "Attack, Decay, Sustain, Release in the chip's 16 steps, shown as the real SID times: attack 2 ms to 8 s, decay and release 6 ms to 24 s, sustain as a level in %. Above the faders, a drawing shows the envelope's shape as you move them."],
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
    chapter("Random: New Patches by the Rules",
            "Press <b>RANDOM</b> (top of the PRESET section) to open the RANDOM panel over the device; CLOSE hides it. "
            "A roll is not a throw of the dice on every control: it builds a patch for the chosen sound type inside that "
            "type's safe ranges, follows the SID's own limits (always a waveform, never a silent pulse width, filters that "
            "let the sound through, playable wavetable notes), and is never silent, clipping or broken.",
            RLImage(rpic, width=img_w, height=img_w * H / W) if rpic else Spacer(1, 1),
            Paragraph("Figure 2. The RANDOM panel.", st["cap"]),
            table([["Control", "What it does"],
                   ["SOUND TYPE", "LEAD, BASS, PAD, PLUCK, ARP, DRUM, FX or ANY. Each has its own ranges: a BASS is low with the filter on, a PAD slow with a moving pulse, a DRUM a kick, snare, hat or tom built in the wavetable."],
                   ["CHIP FOR THE ROLL", "KEEP the device's chip, roll for the 6581 or the 8580, or ANY (chosen per roll)."],
                   ["AMOUNT", "Low values nudge the current sound into a variation; high values build a new sound."],
                   ["BRIGHT, MOTION, LENGTH", "Steer the roll: darker or brighter waves and cutoff; more or less movement (sweeps, vibrato); shorter or longer envelopes."],
                   ["LOCK", "Keep a section as it is: OSC, ENV, FILTER, PITCH, WTABLE."],
                   ["ARP CHORDS", "The chords an ARP roll may use: major, minor, sus, or any."],
                   ["ROLL, MUTATE", "ROLL makes a new sound; MUTATE makes a small variation of the last roll."],
                   ["UNDO, REDO, HISTORY", "Step through the last 8 rolls, or click a cell (O is the sound before the first roll)."],
                   ["AUTO", "Roll on every note (NOTE) or every few bars while Live plays (BARS)."],
                   ["KEEP, PREVIEW", "KEEP saves the roll in the next free preset slot (shown under the screen). PREVIEW plays a note."]],
                  [34 * mm, img_w - 34 * mm]),
            Spacer(1, 4),
            "A roll replaces the sound being edited, like turning the knobs: SAVE or KEEP it to keep it. ROLL can be "
            "MIDI-mapped, to roll new sounds from a pad while you play."),
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
doc.build(story, onFirstPage=cover, onLaterPages=footer)

# ---- update history (no dates)
HISTORY = [("1.1.2", ["RANDOM panel: all its controls appear and respond in Live (type, chip, locks, chords, auto, CLOSE and the knobs), and the main panel no longer shows through it."]),
           ("1.1.1", ["RANDOM panel works inside Live (before, it only answered when the device was open in Max).",
                      "Knobs show and send their full range: PW goes up to 4095, and the RANDOM knobs start where they should (AMOUNT 100, BRIGHT 0, MOTION 50, LENGTH 0, BARS 4).",
                      "A clear message in the Max console if the sid1~ external is older than the device."]),
           ("1.1.0", ["RANDOM panel: new patches by the rules for 8 sound types, with AMOUNT, BRIGHT, MOTION, LENGTH, section locks, arp chords, chip choice, mutate, undo/redo and an 8-roll history, auto roll on notes or bars, keep to the next free slot, and preview.",
                      "Tested: thousands of rolls on both chips, none silent, clipping or broken."]),
           ("1.0.5", ["Every knob redrawn in the style of the envelope faders: metal caps with a pointer, a lit arc and tick dots; bipolar knobs light from the centre."]),
           ("1.0.4", ["New envelope faders: recessed slots with a scale, lit fill and metal caps, the SID times below, and a live drawing of the envelope shape above."]),
           ("1.0.3", ["Manual: new cover, a chapter on the SID chip and its history, and a comparison of the 6581 and 8580 models."]),
           ("1.0.2", ["The envelope faders no longer cover a help text from the oscillator section."]),
           ("1.0.1", ["The filter cutoff knob now acts at once on held notes (before, only from the next note).",
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
