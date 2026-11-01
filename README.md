# GruselCore

A lean 8-track groovebox firmware for the M-VAVE FM-1, made for Hardtek, Techno, Dark Techno,
Trance, Psytrance, Psychill, Darkpsy, Forest Psy, Dark Prog, Mentaltek and Tribetek.

> **Status: in development, not ready to install yet.** The first playable version is v0.1.

## What it will be

- **8 tracks**, each freely set to DRUM, 303, VA or FM, changeable while playing. Two drum kits at
  once is two tracks set to DRUM.
- **Synthesized sounds only**: synth drums (8 sounds per kit, each fully editable), a TB-303, a
  virtual-analog synth and a 4-operator FM synth.
- **Sequencer**: one global tempo and swing; 8, 16, 32 or 64 steps per track; pattern changes at
  the end of the bar; mute and solo.
- **Per-track arpeggiator and gate**, locked to the tempo.
- **Effects**: filter, drive, chorus and gate on every track; shared delay and reverb with a send
  per track; per-track delays as far as the RAM allows; master compressor with pump and a DJ filter.
- **Never stops**: every edit happens while the sequencer runs.

The full spec, with the roadmap, is kept with the project owner.

## Roadmap

| Version | Content |
| --- | --- |
| v0.1 | Foundation: 8 tracks (DRUM, 303), lengths, tempo, swing, mutes, pattern queue, filter and drive per track, delay, reverb, pump, OCT− USB rescue |
| v0.2 | VA and FM engines, chords, arpeggiator, gate and chorus per track, per-track delays, genre presets |
| v0.3 | Live polish: controls, copy, undo, save, MIDI clock in, drum rolls |
| Later | Knob recording, song mode, free lengths 1–64, acid line generator, web editor and backup |

## Building

GruselCore is built from this repository by GitHub Actions, with the Firmware Hub's shared build
workflow ([zvenson/fm1-build](https://github.com/zvenson/fm1-build)), which brings the JieLi
toolchain and the AC79 SDK. Every push to `main` builds a development package
(`gruselcore-dev.fwsc`, in the run's artifacts); a `v*` tag builds a signed release.

Locally, the PC simulator and the tests need only a C compiler: `sh tests/run_tests.sh`.
A local firmware build needs the JieLi toolchain: see [BUILDING.md](BUILDING.md).

The firmware identity is `FM-1_966` for development builds and `FM-1_966XXYYZZ` for releases
(0.1 is `FM-1_966000100`). Over USB the FM-1 shows up as **GruselCore FM-1**.

## Safety

The update loader and its USB code are X0X's and Felucca's, unchanged, so every GruselCore build
can install the next firmware. If something goes wrong: X0X's safe mode starts after repeated
crashes, and the FM-1 Firmware Hub's [rescue](https://thefirmwarehub.com/#rescue) puts any
firmware back through the chip's ROM bootloader. Installing custom firmware is at your own risk.

## Credits and licence

GruselCore is a fork of [X0X](https://github.com/charlesvestal/fm1-x0x) by Charles Vestal, itself a
fork of [Felucca](https://github.com/hugelton/Felucca) by Leo Kuroshita (Hügelton Instruments).
X0X's README, with its full credits (9W9, 8W8, Open303, TB-3PO, BB Gen, Optimist, Melodee,
Jangada), is kept in [docs/X0X-README.md](docs/X0X-README.md).

GPL-3.0-only, like X0X and Felucca: see [LICENSE](LICENSE) and [LICENSING.md](LICENSING.md).
Written with Claude (Anthropic).

M-VAVE and FM-1 are trademarks of their owners. TR-808, TR-909 and TB-303 are Roland trademarks,
used only to describe what the sounds are modelled on. GruselCore is not affiliated with M-VAVE,
Roland or Hügelton Instruments.
