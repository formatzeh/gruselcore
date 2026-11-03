# GruselCore genre notes (measured from the user's examples)

Measured on 2026-11-03 from 65 example tracks the user picked for their five main genres. Each track was downloaded,
decoded and analysed with `tools/genre_analyze.py` (librosa): a 2-minute stretch from 40 % in (past the intro) for
tempo, step patterns, kick, bass, key and sound; the whole track for the breaks. The audio is deleted afterwards. The
per-track numbers live in `design/genres/<genre>.json`, the heat maps (each track's average bar per lane) in
`design/genres/<genre>_patterns.png`.

**These are measurements, not listening.** Nobody here heard the tracks. The numbers are solid where they check out:
every BPM a title states matches (141, 150, 154, 155, 160, 160, 180). Where a number looks wrong it may be wrong, and
the user's ears decide.

## The user's taste: the rule for every demo, preset and generator
- Dark, hypnotic, trance-like. Repeating patterns that change slowly. Not happy music.
- **Minor over major.** In the examples the analysis finds **Phrygian** most of all: 47 of 65 tracks, with harmonic
  minor next. The few "major" results are probably Phrygian read wrong, from a tuned kick or atonal FX.
- **No long breaks.** The examples agree:
  - in the median track the kick never stops past the intro;
  - where it does, it is gone for **1 bar** (most often), 2–3 bars at times, and at most 4 bars (one Dark Prog track);
  - **nothing** stops for a whole phrase.
- **Tempo up to 300 BPM** (GruselCore's range is 40–300).

## Overview

| Genre | Tracks | BPM median (range) | Key | Kick (pitch sweep, decay) | Brightness | Breaks |
|---|---|---|---|---|---|---|
| Mental / Tribe / Hardtek | 29 | **170** (150–200) | Phrygian 23, harm. minor 4 | 75→56 Hz, **57 ms**, hard | darkest: 1.46 kHz | 1 bar, at most 3 |
| Dark Prog | 10 | **140** (133–142) | Phrygian 9 | ~51–58 Hz, **20 ms**, very short | 1.69 kHz | 1 bar, one of 4 |
| Darkpsy | 10 | **160** (150–200) | Phrygian 6, harm. minor 1 | 78→52 Hz, **31 ms** | brightest: 2.39 kHz | 1 bar, at most 3 |
| Forest | 11 | **148** (146–153; one at 120) | Phrygian 6, harm. minor 1 | 65→51 Hz, **26 ms** | 2.18 kHz | 1–2 bars |
| "Dark techno" | 5 | **160** (132–175) | Phrygian 3 | **105→51 Hz, 94 ms**, long boom | 1.91 kHz | none |

- **Every genre:** RMS about −6 to −8 dBFS with a crest of 9–11 dB, i.e. heavily limited and dense.
- **Stereo:** narrow (side/mid 0.09–0.19): the energy is mono, the width comes from a few panned details.
- **Pump** (how much the bass dips with the kick): 0.73 in tekno, 0.79–0.88 in the psy genres. The bass makes room
  for each kick, whether by sidechain or because the notes stop there.

## Step patterns (16ths of one bar, measured)
Measured hit rate per step: **X** a hit in at least 70 % of bars, **x** in 40–70 %, **.** rarer. The lanes are bands
of the percussive part:
- KICK: 30–120 Hz;
- PERC: 150–600 Hz (toms, congas, the bass's attack);
- SNARE: 1–5 kHz;
- HATS: 6–11 kHz.

The BASS lane is energy, not hits, and is "on" everywhere, so it is left out here. Bass rhythms are in the text.

```
               1 . . . 2 . . . 3 . . . 4 . . .
TEKNO   kick   X . . . X . . . X . . . X . . .
        perc   X . x . X . x . X . x . X . . .
        snare  X . x . X . x . X . x . X . x .     (on the beats: the distorted kick's top)
        hats   x . x . x . x . X . x . x . x .     8ths
DK PROG kick   X x x . X x x . X x x . X x x .     (x: the bass's short notes, k-b-b-.)
        perc   X x X X X x X X X x X X X x x x
        snare  x . . X x x . X . . x x . x . X     a tick on the 16th before the kick
        hats   x x x x x x x x x x x x x x x x     16ths
DARKPSY kick   X x x x X x x x X x x x X x x .     k-b-b-b rolling bass
        perc   x . . . X . . x x . . x X . . x
        snare  . x . x x x . x x x . X x x . x
        hats   x x x x x x x x . x . x x X x x     16ths, busy
FOREST  kick   X x . . X x . . X x . . X x . x     k-b, very short bass
        perc   X x x X X x x X X x x X X x x X     micro-percussion everywhere
        snare  x . x X . . . X . . . X . x . x     the 16th before the kick
        hats   . x . x . x . . x x . x . x . .     off 16ths
"DARK   kick   X . . . X . . . x . x . X . . .
TECHNO" perc   x . x . X . x . X . x . X . x .
        snare  X . X . X . x . . . x . X . X .
        hats   . . X . x . X . . . X . x . X .     offbeat (the "and")
```

## Mental / Tribe / Hardtek (29: Bagă Tek's channel)
- **Examples:**
  - Vremir: W'bin Tribe, Kom' in Tribe, Triola tribe, Dumbrava, Weird ting, Tuff Mental.
  - DisrespecteK: Mental Dissonance, Symphony Of Hell, ATARAXIE.
  - Mental Dystopia: Derailed, The truth, Destruction.
  - DupTek: Lost Ritual, scarsystem.
  - Genetek (Hexentanz), Gandotek (Totem Spirit), Micratek (The Ghost Network), Tekos Lab, CHiKO, KARLSKOV,
    Cartman303, Paratek, Petikon, hateyourfriends, Titi le raiZonable, COLT 45MK vs SLOWMATIC, Diego Pira
    (DOWNgrade, tribecore), Bagă Tek (Bueno, Who Are You?).
- **Tempo:** 170 median.
  - Tribe tekno 160–175; mental 158–173.
  - Hardtek 195–200 (Micratek 195, CHiKO 200); tribecore 190 (Diego Pira).
  - "Mentalcore" as tagged here is not faster (163, 170).
- **Kick:** on every beat, never resting. It falls in pitch (75→56 Hz) and is long and distorted (57 ms to −20 dB on
  average; its top shows in the 1–5 kHz band): the tekno kick that is half bass.
- **Bass:**
  - Energy all along the bar, ducking with the kick (pump 0.73): an offbeat or galloping bass between the kicks.
  - Its notes are the **root most of all**, then **the ♭2 (one semitone up)**, the major 7th below, the minor 3rd,
    the 2nd and the 4th: Phrygian riffs that hammer the root and lean on the ♭2.
- **Percussion:**
  - Toms and congas (150–600 Hz) on the beats and the "and" (steps 3, 7, 11): the tribe gallop.
  - Hats in 8ths.
- **Sound:** the darkest of the five (centroid 1.46 kHz) and the loudest (−5.7 dBFS RMS). All low and mid weight.
- **GruselCore recipe:**
  - **Kits:** HARDTEK KIT, TRIBETEK KIT, MENTALTEK, TRIBE PERC, MENTAL PERC. Set DRIVE and GRIT up, PITCH a little down,
    DECAY long.
  - **Drums:**
    - BD on 1 5 9 13;
    - TM on 3 7 11 (and 15 now and then);
    - CH on every 8th, OH on the "and" of 2 and 4 (7, 15);
    - RS or PC ghost hits on a 3-step cycle for the triola feel.
  - **Bass** (HARDTEK BAS, TRIBE BASS, DRIVE BASS, PD MENTAL):
    - 1/16 with the notes on the three 16ths between the kicks (k-b-b-b), GATE short, DUCK under the kick track;
    - notes: root, root, ♭2, root; now and then the 7th below or the minor 3rd.
  - **Leads:** MENTAL ACID, PD ACID, ACID, SQUELCH, MENTAL SAW, MENTAL STAB, SYNC SCREAM. 1/16 acid with accents and
    slides, in Phrygian.
  - **BPM:** 170, or 190–200 for hardtek.
  - **EVOLVE:** AMOUNT 30–50 on the percussion and acid, 0–10 on the kick track; ARRANGE LIGHT; DRIFT on the acid;
    SWEEP on the acid; ROOT I-IV or OFF.

## Dark Prog (10)
- **Examples:** Pick (Dark Prog, and Tekxture's remix), Smokcid (Spectral Mesh, One Blink), Algia (Drop Attack),
  Braindrop (Dark Prog Monster), Release (Paw Syndicate), Space Organ & Stereodots (StereOrgan), Nuada (The Absolute),
  a "Fear of the Dark" prog remix. Labels Sentimony and Tekxture.
- **Tempo:** **140** (133–142). Tight: almost every track sits at 138–142.
- **Kick:** very short (20 ms) and low (about 51–58 Hz), with almost no click.
- **Bass:** the classic prog roll.
  - The kick, then **two short bass notes on the 2nd and 3rd 16ths**, a gap on the 4th: k-b-b-. (the kick lane's
    x x .).
  - It ducks hard (pump 0.86).
  - Notes: root, then **♭7**, 7, 2nd, ♭5: a dark, minimal line around the root.
- **Percussion:**
  - 16th hats all through.
  - A tick in 1–5 kHz on the **16th before each kick** (steps 4, 8, 12, 16), which pushes into the beat.
  - Busy low percussion.
- **Sound:** mid-bright (1.69 kHz), slightly wider (0.15). Deep, groovy, minimal, hypnotic.
- **GruselCore recipe:**
  - **Kit:** DARK PROG, DK PROG PERC. A short kick: DECAY down, PITCH low.
  - **Drums:**
    - BD on 1 5 9 13;
    - CH on all 16ths, an accent on the offbeat 8ths;
    - RS or CP on 4 8 12 16;
    - percussion sparse and moving.
  - **Bass:** PROG BASS, PD PSY BASS, FM PSYBASS.
    - 1/16, notes on steps 2 and 3 of each beat (b-b-.), GATE short (about 40 %), DUCK on.
    - Root, root; every second bar the ♭7 on one step.
  - **Over it:** DARK PLUCK, HYPNO SEQ, FM HYPNO, DARK FIFTH; pads ABYSS, DARK DRONE, MIST VEIL; FX TUNNEL, VOID WIND.
  - **BPM:** 140.
  - **EVOLVE:** AMOUNT 20–40 on the plucks and percussion; SWEEP on the pluck and pad (the long filter build); PHASE
    −1 on a percussion track; GATE on the bass; ARRANGE LIGHT.

## Darkpsy (10; Horrordelic and others)
- **Examples:** Dark Element (Angry Mode, 150), Yata-Garasu (Scarr 154, Lost in yourself 160), Cyber Buddha (Zara,
  155), Master Of Horror (My Friend Not Dead, 160), BDZ (Gates of Hell), Asamori (Warped Instinct, psycore), Cosmo
  (Acid Monster), Darknesss (Encapsulation Of The Brain, 180), Yoshua E.m (Ancient Rituals in Neo Times, 200).
- **Tempo:** **160** median. 150–160 is darkpsy proper; 177–200 is psycore (Asamori, Cosmo, Darknesss, Yoshua).
- **Kick:** 78→52 Hz, short (31 ms).
- **Bass:** **the full rolling bass, k-b-b-b**: the kick lane shows a hit on every 16th after the kick. Notes: root,
  then ♭2, 2nd, 6th, ♭5: chromatic and tense.
- **Percussion:** the busiest and brightest (centroid 2.39 kHz). 16th hats with accents moving around, a snare-band
  hit on the 16th before beats 3 and 4, and lots of crunchy hits off the grid.
- **Sound:** bright, sharp, chaotic on top; the widest (0.19) and the most dynamic (crest 11.1 dB). The FX and noise
  move around.
- **GruselCore recipe:**
  - **Kit:** DARKPSY KIT, PSY PERC. A short kick, a little GRIT.
  - **Drums:**
    - BD on 1 5 9 13;
    - CH on 16ths with RATCH x2 or x3 now and then;
    - OH on the offbeat 8ths;
    - CP on the 16ths before 9 and 13;
    - RS and PC scattered (CHANCE 50–75 %).
  - **Bass:** PD PSY BASS, FM PSYBASS, FM NEURO, GROWL BASS.
    - 1/16, notes on steps 2, 3 and 4 of each beat, very short GATE, DUCK on.
    - Root, root, root; ♭2 at a bar's end.
  - **Over it:** SQUELCH, SYNC SCREAM, RING DARK, INDUS LEAD, WIRE; FX SCATTER, SPECTRE, STORM HOWL, ZAP.
  - **BPM:** 155–160, or 175–185 for psycore.
  - **EVOLVE:** AMOUNT 40–60 on the leads and percussion; DRIFT 40+; SWEEP; PHASE −1 or −3 on a percussion track; ROOT
    I-VII-VI; ARRANGE FULL (its breakdowns are 2 bars).

## Forest (11; Parvati Records mostly)
- **Examples:** Arjuna & Ectogasmics (The Jungle Came Alive), Jahbo (Voltage), Alchemized (Lunar Sector), Kerlivin
  (Bobi), Third Eye Of Monkey (Xocoyotzin), Gappeq (Those Moments), Ulvae (Utchamau), Mubali & Xelph (The New Ab
  Normal), Necropsycho (Dead Of Night), Fobi (Forest Child, I Think U Know).
- **Tempo:** **148** (146–153).
  - Gappeq's "Those Moments" measures 120. It is either a slower track or a reading of a 240 half-time feel; listen
    before using it.
- **Kick:** 65→51 Hz, short (26 ms), no click: round and soft-edged.
- **Bass:**
  - k-b: **one very short bass note right after each kick** (the kick lane's x on the 2nd 16th), often another on the
    4th.
  - It ducks the most (pump 0.88).
  - Notes: root, the 7th below, the 3rd, ♭2: chromatic tension around the root.
- **Percussion:**
  - **Micro-percussion on almost every 16th** (the 150–600 Hz lane is lit everywhere): wood, clicks, bubbles.
  - A snare-band tick on the 16th before each kick.
  - Hats on the off-16ths (2, 4, 6 …), sparse.
- **Sound:** 2.18 kHz, organic, many small details; mono-centred with panned ornaments (0.15).
- **GruselCore recipe:**
  - **Kits:** FOREST PSY, FOREST PERC; DRUM lanes panned (LANE MIX) for the ornaments.
  - **Drums:**
    - BD on 1 5 9 13, very short;
    - PC, RS and TM on many 16ths at CHANCE 30–60 % with NUDGE;
    - CH on the off-16ths;
    - CP on 4 8 12 16 (soft).
  - **Bass:** PD PSY BASS, FM PSYBASS, KNOCK BASS.
    - 1/16, a note on step 2 of each beat (sometimes 4 as well), the shortest GATE, DUCK on.
    - Root; the 7th below at a bar's end.
  - **Over it:** KALIMBA DRK, PD DARK BEL, NEUTRINO, TRIBE PLUCK; pads FOREST AIR, MOSS BED, SPORE DRIFT; FX DUST,
    WHISPER, CAVE WIND.
  - **BPM:** 148.
  - **EVOLVE:** AMOUNT 50–70 on the percussion tracks (forest lives on small changes); DRIFT on the plucks; PHASE −1 and
    −3 on two percussion tracks (polymeter); ARRANGE LIGHT.

## "Dark techno" (5)
- **Examples:** KILEN (ECLIPSE, "Blood Ritual Dark Techno"), Insane Teknology (The Last Samurai), Sevenum Six (Mutate
  And Survive), Fasotek (Real Underground), l'arsouille (Mental tribe).
- **Four of the five are tekno, not techno:** 158–175 BPM, Phrygian, the tekno kick. Only KILEN is techno, at 132.
  What the user calls dark techno is **dark, industrial tekno**, plus the slower techno side.
- **Kick:** the longest and boomiest: it starts at 105 Hz and falls to 51 Hz over **94 ms**. A kick that is also the
  bass (the rumble or boom kick).
- **Bass:** steady under the bar, root above all, ♭2 next.
- **Percussion:** **hats on the offbeat** (steps 3, 7, 11, 15: the "and"), percussion on the 8ths, a clap-like hit on
  the beats.
- **Sound:** 1.91 kHz, narrow (0.09), loud.
- **GruselCore recipe:**
  - **Kits:** DARK TECHNO, TECHNO KIT, HARDTEK KIT. A long DECAY, PITCH low, DRIVE.
  - **Drums:**
    - BD on 1 5 9 13 (sometimes 11 too);
    - OH or CH on 3 7 11 15;
    - CP on 5 13;
    - RS on the 8ths.
  - **Bass:** RUMBLE, BOOM SUB, DARK MATTER, DIRTY BASS. Root on the offbeats, DUCK hard; or none, the kick's boom is
    enough.
  - **Over it:** INDUS LEAD, WAR HORN, RING DARK; pads DARK DRONE, WRAITH, CRYPT CHOIR.
  - **BPM:** 132 for techno, 160–170 for tekno.
  - **EVOLVE:** AMOUNT 20–40; SWEEP on a drone; GATE on the bass; ARRANGE LIGHT.

## Across the genres (for a generator)
- **The kick never pauses for long:** 1 bar is a break, 4 bars is the most. EVOLVE's ARRANGE follows this (2-bar
  breakdowns, the kick track never taken out).
- **The bass lives between the kicks:**
  - tekno: continuous or galloping;
  - prog: k-b-b-.;
  - darkpsy: k-b-b-b;
  - forest: k-b.

  It always ducks under the kick.
- **Notes:** the root most of all; the ♭2 is the colour (Phrygian); the ♭7 or the 7th below as a turn at a bar's end.
- **Tempo bands:** prog 140, forest 148, darkpsy 160, tekno 170, hardtek and psycore 180–200.
- **The difference between them is in the details:**
  - how short the kick and bass are (prog shortest, techno longest);
  - how busy the 16th percussion is (forest and darkpsy busiest);
  - how bright the top is (darkpsy brightest, tekno darkest).
