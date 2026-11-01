# GruselCore – quick guide

An 8-track groovebox for the M-VAVE FM-1. Every track is a **DRUM** kit, a **303** or a **VA** synth;
tracks can be switched off. Everything can be edited while the sequencer plays.

## Always

| Control | Does |
| --- | --- |
| PLAY | Start / stop |
| ALGORITHM knob | Select the track (1–8) |
| GLO + SELECT knob | The tempo (locked otherwise, so it can't be changed by accident) |
| SAVE | Save the project. While playing, it saves the moment you stop (writing to the FM-1's memory pauses the sound for a moment) |
| REC | On a 303 or VA track: the keys play it and write the notes into the steps |
| ARP | The selected 303 or VA track's arpeggiator (SEQ's second page); again: back |
| HOME, SEQ, EDIT, FX, LFO, GLO | Open a screen (below) |
| KNOB 1–4 | The four values at the bottom of the screen |

Changes are also saved by themselves when the sequencer is stopped and you have not touched
anything for a few seconds.

## HOME – all 8 tracks, and the keyboard

- **Top line:** play / stop, **bar.beat** (the bars since PLAY, and the beat), the tempo,
  the keyboard's octave (when not 0), the selected track and its pattern.
- **Each track's lane:** its number, its name (the kit, or 303 BASS; M when muted) and its steps; the
  selected track has a bar at its edge.
- **KNOB 1–4 play the selected track's main controls:**
  - drum track: the kit's **TUNE, DECAY, DRIVE, TONE**. Each moves all 8 sounds from their own
    settings at once; 0 is the kit as it is.
  - 303 track: **CUTOFF, RESO, ENV MOD, DECAY**.
  - VA track: **CUTOFF, RESO, ENV** (the filter envelope's amount), **F.DEC** (its decay).
- **The keyboard plays the selected track.** A drum track: its 8 sounds on the black keys 1–8 and on
  the white keys 1–8 (again on 9–16). A 303 or VA: chromatic from F; a VA in CHORD mode plays the keys
  held together as a chord. **OCT− / OCT+:** the octave, −3 to +3. On a VA track, **PRESETS** loads a
  preset here too.
  With **REC** on, what you play is recorded into the steps.
- **Hold HOME** and press a **white key:** the selected track's next pattern. It switches at the end
  of the bar (at once when stopped) and starts from its first step; the other tracks keep playing.
  Hold HOME and press **OCT− / OCT+:** patterns 1–16 or 17–32.
- **Hold HOME + SEL** and press a **white key:** every track switches to that pattern at the bar.
- While HOME is held, the screen shows every track's pattern and the change waiting for the bar.
- **Hold HOME** and press a **black key 1–8:** mute / unmute that track.

## SEQ – the steps of the selected track

**DRUM track**
- **Black keys 1–8:** pick the sound (kick, snare, …; a percussion kit has its own sounds). You hear it,
  playing or stopped. With **REC** on while playing, the hit is also written into the step that plays.
- **White keys 1–16:** set / clear its steps. Hold **ENV** for accents.
- **OCT− / OCT+:** steps 17–32, 33–48, 49–64.
- **Knobs:** LENGTH (8, 16, 32, 64), RATE (1/16, 1/16T, 1/32, 1/8T, 1/8), SWING on/off for this track.
- **PRESETS knob:** load another kit, while playing.

**303 and VA tracks** (the same steps: changing a track between 303 and VA keeps them)
- **White key:** switches a step on / off. **Hold it** and turn the knobs: NOTE, GATE (rest, note,
  tie), **CHORD**, SLIDE. **ENV + white key:** the step's accent.
- **CHORD:** – (the note alone), OCT, 5TH, 5+8, MIN, MAJ, SUS2, SUS4, MIN7, MAJ7, DOM7, MIN9, ADD9,
  DIM, AUG, PHRYG (root, minor second, fifth: dark psy). A VA plays the chord; a 303 plays its root
  (or, with the arpeggiator, the chord's notes one after another).
- Not holding a step, the knobs are LENGTH, RATE, SWING and TRANSPOSE.
- **SELECT knob, or ARP:** the arpeggiator's page: **ARP** (OFF, UP, DOWN, UP-DN, RAND), **NOTES** a
  step (1–4), **OCTAVES** (1–3), DIR (the steps' direction). The arpeggiator plays each step's chord
  (or its note alone, over the octaves) as notes; it carries on through TIE steps.

## EDIT – the selected track's sound

- 4 values a page; the **SELECT knob** turns the pages.
- The keyboard plays the track, as on HOME; on a drum track the key also picks the sound to edit.
  **PRESETS** loads a kit. Each sound has MODEL, LEVEL, TUNE,
  PITCH, P.DEC, BODY, DECAY, TAIL, CLICK, TONE, NOISE, DRIVE, CURVE, PUNCH, ATTACK, PAN.

**VA** – **PRESETS** loads a preset: ROLLING BASS, OFFBEAT BASS, TRANCE LEAD, SUPERSAW PAD, PSY PLUCK,
DARK STAB, FOREST ZAP, DARK DRONE, HOOVER, MENTAL ACID, PSYCHILL KEY, SUB BASS. Seven pages:

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 |
| --- | --- | --- | --- | --- |
| Oscillators | WAVE 1 (SAW, SQR, TRI, SINE) | WAVE 2 | TUNE 2 (±24 semitones) | DETUNE |
| Mix | MIX (osc 1 ↔ osc 2) | SUB (an octave under osc 1) | NOISE | PW (pulse width) |
| Filter | CUTOFF | RESO | ENV (the envelope's amount) | FILTER (LP24, LP12, BP, HP) |
| Filter envelope | F.ATT | F.DEC | F.SUS | KEYTRK |
| Amp envelope | ATTACK | DECAY | SUSTN | RELEAS |
| Voice | MODE (MONO, CHORD, UNISN) | GLIDE | ACCENT | VOLUME |
| LFO | LFO (8 BAR … 1/32, with the tempo) | SHAPE (TRI, SAW, SQR, S&H) | L>PTCH | L>CUT |

MONO plays one note (a slide, or a key pressed while another is held, glides); CHORD up to four notes;
UNISN four detuned voices on one note (DETUNE spreads them: a supersaw). If the CPU runs short, CHORD
and UNISN play one voice until it recovers.

## FX

- Page 1: the track's FILTER (low-pass left, high-pass right), RESO, DRIVE, LEVEL.
- Page 2: PAN, the reverb send, the delay send.
- **FX again** (or the SELECT knob): the shared reverb, delay and master pages.

## LFO – mixer

Levels and meters of all 8 tracks. **Black keys** mute. Knobs: the selected track's LEVEL, PAN, REV,
DLY.

## GLO – track settings, then global

GLO opens when you let go of it (held with SELECT, it sets the tempo instead).

- **Page 1:** KNOB 1 the track's type (OFF, DRUM, 303, VA), then **SEL** to apply it (a new type clears
  that track's steps in every pattern, except between 303 and VA); KNOB 2 its MIDI channel; KNOB 3 MIDI
  clock out; KNOB 4 notes out.
- **GLO again, page 2:** SWING (one for all tracks), the master FILTER (low-pass left, high-pass
  right), PUMP (ducks everything on the kick), TEMPO; version, pattern memory and CPU load.

## Safety and the way back

- **OCT− held while switching on:** safe mode (no sound, USB on): install any firmware or the
  official one. In safe mode, **PLAY** starts normally, **REC** starts once without your saved
  project (it stays untouched).
- **OCT− + OCT+ held for 5 seconds:** update mode.
- If GruselCore crashes twice while starting, it starts in safe mode by itself.
- Last resort: the FM-1 Firmware Hub's rescue through the chip's own bootloader.
