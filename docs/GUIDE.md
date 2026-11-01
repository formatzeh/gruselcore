# GruselCore v0.1 – quick guide

An 8-track groovebox for the M-VAVE FM-1. Every track is a **DRUM** kit or a **303**; tracks can be
switched off. Everything can be edited while the sequencer plays.

## Always

| Control | Does |
| --- | --- |
| PLAY | Start / stop |
| ALGORITHM knob | Select the track (1–8) |
| SAVE | Save the project. While playing, it saves the moment you stop (writing to the FM-1's memory pauses the sound for a moment) |
| REC | On a 303 track: the keys play the 303 and write the notes into the steps |
| HOME, SEQ, EDIT, FX, LFO, GLO | Open a screen (below) |
| KNOB 1–4 | The four values at the bottom of the screen |

Changes are also saved by themselves when the sequencer is stopped and you have not touched
anything for a few seconds.

## HOME – all 8 tracks, and the keyboard

- **The keyboard plays the selected track.** A drum track: its 8 sounds on the black keys 1–8 and on
  the white keys 1–8 (again on 9–16). A 303: the keys from F, chromatic; **OCT− / OCT+** the octave.
  With **REC** on, what you play is recorded into the steps.
- **Hold HOME** and press a **white key:** the next pattern. It starts at the end of the bar (at once
  when stopped). Hold HOME and press **OCT− / OCT+:** patterns 1–16 or 17–32.
- **Hold HOME** and press a **black key 1–8:** mute / unmute that track.
- **Knobs:** TEMPO, SWING, the master FILTER (low-pass left, high-pass right), PUMP (ducks
  everything on the kick).

## SEQ – the steps of the selected track

**DRUM track**
- **Black keys 1–8:** pick the sound (kick, snare, …; a percussion kit has its own sounds). You hear it,
  playing or stopped. With **REC** on while playing, the hit is also written into the step that plays.
- **White keys 1–16:** set / clear its steps. Hold **ENV** for accents.
- **OCT− / OCT+:** steps 17–32, 33–48, 49–64.
- **Knobs:** LENGTH (8, 16, 32, 64), RATE (1/16, 1/16T, 1/32, 1/8T, 1/8), SWING on/off for this track.
- **PRESETS knob:** load another kit, while playing.

**303 track**
- **White key:** switches a step on / off. **Hold it** and turn the knobs: NOTE, GATE (rest, note,
  tie), ACCENT, SLIDE.
- Not holding a step, the knobs are LENGTH, RATE, SWING and TRANSPOSE.

## EDIT – the selected track's sound

- 4 values a page; the **SELECT knob** turns the pages.
- The keyboard plays the track, as on HOME; on a drum track the key also picks the sound to edit.
  **PRESETS** loads a kit. Each sound has MODEL, LEVEL, TUNE,
  PITCH, P.DEC, BODY, DECAY, TAIL, CLICK, TONE, NOISE, DRIVE, CURVE, PUNCH, ATTACK, PAN.

## FX

- Page 1: the track's FILTER (low-pass left, high-pass right), RESO, DRIVE, LEVEL.
- Page 2: PAN, the reverb send, the delay send.
- **FX again** (or the SELECT knob): the shared reverb, delay and master pages.

## LFO – mixer

Levels and meters of all 8 tracks. **Black keys** mute. Knobs: the selected track's LEVEL, PAN, REV,
DLY.

## GLO – track settings

- **KNOB 1:** the track's type (OFF, DRUM, 303), then **SEL** to apply it. A new type clears that
  track's steps in every pattern.
- KNOB 2: its MIDI channel. KNOB 3: MIDI clock out. KNOB 4: notes out.
- **GLO again:** version, pattern memory used, CPU load.

## Safety and the way back

- **OCT− held while switching on:** safe mode (no sound, USB on): install any firmware or the
  official one. In safe mode, **PLAY** starts normally, **REC** starts once without your saved
  project (it stays untouched).
- **OCT− + OCT+ held for 5 seconds:** update mode.
- If GruselCore crashes twice while starting, it starts in safe mode by itself.
- Last resort: the FM-1 Firmware Hub's rescue through the chip's own bootloader.
