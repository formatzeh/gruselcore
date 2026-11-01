# GruselCore – quick guide

An 8-track groovebox for the M-VAVE FM-1. Every track is a **DRUM** kit or a synth (**303**, **VA**, **FM**,
**PHYS**); tracks can be switched off. Everything can be edited while the sequencer plays.

## Always

| Control | Does |
| --- | --- |
| PLAY | Start / stop |
| ALGORITHM knob | Select the track (1–8) |
| GLO + SELECT knob | The tempo, 1 BPM a step (locked otherwise, so it can't be changed by accident) |
| PRESETS knob | The selected track's kit or synth sound, on every screen, while playing; SEL + PRESETS: the list (ALL, BASS, ACID, LEAD, …) |
| SAVE | Save the project. While playing, it saves the moment you stop (writing to the FM-1's memory pauses the sound for a moment) |
| REC | On a synth track: the keys play it and write the notes into the steps |
| ARP | The selected synth track's arpeggiator (SEQ's second page); again: back |
| HOME, SEQ, EDIT, FX, LFO, GLO | Open a screen (below) |
| KNOB 1–4 | The four values at the bottom of the screen |

Changes are also saved by themselves when the sequencer is stopped and you have not touched
anything for a few seconds.

## HOME – all 8 tracks, and the keyboard

- **Top line:** play / stop, **bar.beat** (where the selected track is in its pattern: 16 steps run
  1.1–1.4, 32 steps 1.1–2.4, then again), the tempo,
  the keyboard's octave (when not 0), the selected track and its pattern.
- **Each track's lane:** its number, its name (the kit, or 303 BASS; M when muted) and its steps; the
  selected track has a bar at its edge.
- **KNOB 1–4 play the selected track's main controls:**
  - drum track: the kit's **TUNE, DECAY, DRIVE, TONE**. Each moves all 8 sounds from their own
    settings at once; 0 is the kit as it is.
  - 303 track: **CUTOFF, RESO, ENV MOD, DECAY**.
  - VA track: **CUTOFF, RESO, ENV** (the filter envelope's amount), **F.DEC** (its decay).
  - FM track: **LEVEL2, DECAY2** (how bright, and for how long), **FEEDBK, RELEAS**.
  - PHYS track: **DECAY, TONE, HARD, CUTOFF**.
- **The keyboard plays the selected track.** A drum track: its 8 sounds on the black keys 1–8 and on
  the white keys 1–8 (again on 9–16). A synth: chromatic from F; in CHORD mode the keys held sound
  together as a chord. **OCT− / OCT+:** the octave, −3 to +3.
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

**Synth tracks: 303, VA, FM, PHYS** (the same steps: changing a track between them keeps them)
- **White key:** switches a step on / off. **Hold it** and turn the knobs: NOTE, GATE (rest, note,
  tie), **CHORD**, SLIDE. **ENV + white key:** the step's accent.
- **CHORD:** – (the note alone), OCT, 5TH, 5+8, MIN, MAJ, SUS2, SUS4, MIN7, MAJ7, DOM7, MIN9, ADD9,
  DIM, AUG, PHRYG (root, minor second, fifth: dark psy). VA, FM and PHYS play the chord; a 303 plays its root
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

## Sounds

**Drum kits (16):** HARDTEK, TRIBETEK, MENTALTEK, TECHNO, DARK TECHNO, TRANCE, PSYTRANCE, DARKPSY, DARK PROG,
PSYCHILL, FOREST PSY, and the percussion kits TRIBE PERC, MENTAL PERC, DARK PROG PERC, FOREST PERC, PSY PERC.
**PRESETS** on a drum track steps through them.

**Synth sounds (188), one list as on Skiff.** On a 303, VA, FM or PHYS track, **PRESETS** steps through
every synth sound, grouped by kind: BASS, ACID, LEAD, PLUCK, STAB, PAD, PERC, FX. **SEL + PRESETS** picks
the list: ALL or one kind (it stays after a power-off). A sound of another engine switches the track to
that engine; its steps stay. The top line shows e.g. "BASS 3/30 FM" and the sound's name.

| Engine | Sounds | What it is |
| --- | --- | --- |
| 303 | 20 | The TB-303: acid lines, from soft to screaming |
| VA | 78 | Two oscillators, sub, noise, a filter with its envelope; MONO, CHORD, UNISN, HYPER (seven saws) |
| FM | 50 | Four operators, eight algorithms: psy basses, metallic leads, bells, keys, stabs, zaps |
| PHYS | 40 | Physical models: plucked strings, mallets, bells, hand drums (tuned, with a pitch drop) |

Every sound is as loud as the drum kits.

**VA pages**

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 |
| --- | --- | --- | --- | --- |
| Oscillators | WAVE 1 (SAW, SQR, TRI, SINE) | WAVE 2 | TUNE 2 (±24 semitones) | DETUNE |
| Mix | MIX (osc 1 ↔ osc 2) | SUB (an octave under osc 1) | NOISE | PW (pulse width) |
| Filter | CUTOFF | RESO | ENV (the envelope's amount) | FILTER (LP24, LP12, BP, HP) |
| Filter envelope | F.ATT | F.DEC | F.SUS | KEYTRK |
| Amp envelope | ATTACK | DECAY | SUSTN | RELEAS |
| Voice | MODE (MONO, CHORD, UNISN, HYPER) | GLIDE | ACCENT | VOLUME |
| LFO | LFO (8 BAR … 1/32, with the tempo) | SHAPE (TRI, SAW, SQR, S&H) | L>PTCH | L>CUT |

MONO plays one note (a slide, or a key pressed while another is held, glides); CHORD up to four notes;
UNISN four detuned voices on one note; HYPER seven, spread twice as wide (DETUNE: how far).
HOME's knobs: CUTOFF, RESO, ENV, F.DEC.

**FM pages**

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 |
| --- | --- | --- | --- | --- |
| Algorithm | ALGO (1–8) | FEEDBK (operator 4) | MODE (MONO, CHORD) | GLIDE |
| Operator 1–4 (4 pages) | RATIO (0.25 … 16) | LEVEL | DECAY | SUSTN |
| Envelope | ATTACK | RELEAS | ACCENT | VOLUME |
| LFO | LFO (with the tempo) | L>PTCH | L>MOD (the modulation depth) | DETUNE |

Algorithms: 1 4>3>2>1 · 2 (3+4)>2>1 · 3 4>3>1 and 2>1 · 4 4>2>1 and 3>1 · 5 two stacks 4>3, 2>1 ·
6 4 modulates 1, 2, 3 · 7 4>3 with 1 and 2 · 8 all four heard (additive). A carrier's LEVEL is its
loudness, a modulator's is how bright it makes the sound. HOME's knobs: LEVEL2, DECAY2, FEEDBK, RELEAS.

**PHYS pages**

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 |
| --- | --- | --- | --- | --- |
| Model | MODEL (PLUCK, MALLT, BELL, DRUM) | DECAY | TONE | POS (where it is struck) |
| Strike | HARD | INHARM | BODY (a wooden body) | STRUM (CHORD: the notes apart) |
| Drop | DROP (the drum's pitch drop) | DROPT (its time) | DAMP (on release) | VOLUME |
| Voice | MODE (MONO, CHORD) | ACCENT | CUTOFF | RESO |

HOME's knobs: DECAY, TONE, HARD, CUTOFF. If the CPU runs short, CHORD, UNISN and HYPER play one voice
until it recovers.

## FX

- Page 1: the track's FILTER (low-pass left, high-pass right), RESO, DRIVE, LEVEL.
- Page 2: PAN, the reverb send, the delay send.
- **FX again** (or the SELECT knob): the shared reverb, delay and master pages.

## LFO – mixer

Levels and meters of all 8 tracks. **Black keys** mute. Knobs: the selected track's LEVEL, PAN, REV,
DLY.

## GLO – track settings, then global

GLO opens when you let go of it (held with SELECT, it sets the tempo instead).

- **Page 1:** KNOB 1 the track's type (OFF, DRUM, 303, VA, FM, PHYS), then **SEL** to apply it (a new type
  clears that track's steps in every pattern, except between the synths); KNOB 2 its MIDI channel; KNOB 3 MIDI
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
