# SID1

Dual MOS SID (6581/8580) synth for Max for Live, with AU/VST3 to follow. Based on the reSID core from [putchdev/sid-1](https://github.com/putchdev/sid-1). GPL-3.0.

## Layout

| Folder | What |
| --- | --- |
| `core/` | The SID chip: `sid.c`, a C port of reSID 0.16 by Dag Lem (GPL-2.0-or-later), from putchdev/sid-1 |
| `engine/` | The synth: two chips, six voices, and SID-1's C64-style patch player (wavetable, pulse and filter sweeps, vibrato, hard restart, 50 frames a second). Plain C, shared by the Max external and the plugin |
| `tests/` | `render_test.c`: plays every factory patch and writes a WAV |

## Test

    cc -O2 -std=c99 tests/render_test.c engine/sid1_engine.c core/sid.c -lm -o render_test && ./render_test

## Licence

GPL-3.0-only (see `LICENSE`). The SID core is GPL-2.0-or-later. The player is ported from SID-1's `firmware/src/sid1.c` (GPL-3.0-only, the SID-1 authors).
