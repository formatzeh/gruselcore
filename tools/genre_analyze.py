#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""(GruselCore) Measure what a dance track does, for sound and pattern design (design/GENRES.md).

    python tools/genre_analyze.py OUT_DIR GENRE=FILE_OR_DIR [GENRE=FILE_OR_DIR ...] [--titles titles.json] [--jobs N]

Each audio file (anything ffmpeg reads: wav, mp3, m4a, opus, webm) is decoded with ffmpeg. Needs numpy, scipy and
librosa (pip install numpy scipy librosa matplotlib). Per track, from a 2-minute stretch around 40 % into it (past the
intro) and, for the structure, the whole track:

  tempo     BPM from the kick band's periodicity (110..260), refined on a comb over the beats, and the beat's phase
            (each bar then re-aligned on its kicks: a tempo a hair off would smear the steps)
  patterns  the 16 steps of a bar for five lanes (onset strength in a band of the percussive part (HPSS), as a share of
            the bar's strongest, averaged
            over the bars; and how often a step is a hit): KICK 30-120 Hz, BASS 50-300 Hz (energy, between the kicks),
            PERC 150-600 Hz, SNARE 1-5 kHz, HATS 6-11 kHz
  kick      its pitch at 15 ms and at 80 ms (the sweep), its decay to -20 dB, its click (energy above 1 kHz)
  bass      the notes it plays on the 16 steps (pyin), relative to the key's root; its length in steps
  key       root and mode (minor, major, phrygian, harmonic minor) from the harmonic part's chroma
  sound     brightness (spectral centroid), loudness (RMS dBFS), crest (peak / RMS: how squashed), stereo width
            (side / mid), the bass's pump (how much it dips with the kick)
  structure bars with no kick: the intro, the outro and every break in between (bars and seconds)

OUT_DIR gets one JSON per track (OUT_DIR/GENRE/ID.json), OUT_DIR/GENRE.json (every track and the genre's medians) and
OUT_DIR/GENRE_patterns.png (each track's average bar per lane, as a heat map). Measured, not heard: a number that looks
wrong usually is (a half or double tempo, a key from a tuned kick)."""
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

SR = 22050
HOP = 256
LANES = {"kick": (30, 120), "bass": (50, 300), "perc": (150, 600), "snare": (1000, 5000), "hats": (6000, 11000)}
NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Kessler key profiles; phrygian and harmonic minor from the minor's weights moved onto their steps
P_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
P_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
P_PHR = P_MIN.copy(); P_PHR[1], P_PHR[2] = P_MIN[2], P_MIN[1]
P_HMI = P_MIN.copy(); P_HMI[10], P_HMI[11] = P_MIN[11], P_MIN[10]
MODES = {"minor": P_MIN, "major": P_MAJ, "phrygian": P_PHR, "harmonic minor": P_HMI}


def decode(path, start=None, dur=None, ch=1):
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.2f}"]
    if dur is not None:
        cmd += ["-t", f"{dur:.2f}"]
    cmd += ["-i", path, "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    return x.reshape(-1, ch).T if ch > 1 else x


def band_env(S, freqs, lo, hi, flux=True):
    """onset strength (positive spectral flux) or energy of the band, per frame"""
    m = S[(freqs >= lo) & (freqs < hi)]
    if not flux:
        return np.sqrt(np.mean(m ** 2, axis=0))
    lm = np.log1p(100.0 * m)
    d = np.maximum(0.0, np.diff(lm, axis=1, prepend=lm[:, :1]))
    return d.mean(axis=0)


def tempo_of(env):
    """BPM (110..260) from the envelope's autocorrelation, the strongest period, its octave chosen by the comb"""
    e = env - env.mean()
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    fps = SR / HOP
    lags = np.arange(len(ac))
    ok = (lags >= fps * 60 / 260) & (lags <= fps * 60 / 110)
    lag = lags[ok][np.argmax(ac[ok])]
    if 0 < lag < len(ac) - 1:                            # parabolic refinement
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        lag = lag + 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else lag
    return 60 * fps / lag


def comb(env, bpm, phase):
    fps = SR / HOP
    t = np.arange(phase, len(env) / fps, 60 / bpm)
    i = np.clip(np.round(t * fps).astype(int), 0, len(env) - 1)
    return env[i].mean()


def grid(env, bpm0):
    """tempo and phase that put the kick envelope's peaks on the beats"""
    best = (0, bpm0, 0)
    for bpm in np.arange(bpm0 - 1.0, bpm0 + 1.0, 0.02):
        for ph in np.arange(0, 60 / bpm, 0.004):
            v = comb(env, bpm, ph)
            if v > best[0]:
                best = (v, bpm, ph)
    return best[1], best[2]


def bar_offsets(kenv, bpm, phase, nbars):
    """each bar's own small shift (a tempo a hair off drifts over two minutes): where its four beats meet the kick
    best, within half a 16th, smoothed over 5 bars"""
    fps = SR / HOP
    step = 60 / bpm / 4
    offs = np.zeros(nbars)
    cand = np.arange(-0.5 * step, 0.5 * step, 0.002)
    for b in range(nbars):
        best, bo = -1.0, 0.0
        for o in cand:
            i = [int((phase + o + (b * 16 + k * 4) * step) * fps) for k in range(4)]
            if i[0] < 0 or i[-1] >= len(kenv):
                continue
            v = sum(kenv[j] for j in i)
            if v > best:
                best, bo = v, o
        offs[b] = bo
    from scipy.signal import medfilt
    return medfilt(offs, 5) if nbars >= 5 else offs


def slot_values(env, bpm, phase, nbars, win=0.025, offs=None):
    """[bar][16] the envelope's peak around each 16th"""
    fps = SR / HOP
    step = 60 / bpm / 4
    out = np.zeros((nbars, 16))
    for b in range(nbars):
        for s in range(16):
            t = phase + (offs[b] if offs is not None else 0.0) + (b * 16 + s) * step
            i0, i1 = int((t - win) * fps), int((t + win) * fps) + 1
            if i0 < 0 or i1 >= len(env):
                out[b, s] = np.nan
                continue
            out[b, s] = env[i0:i1].max()
    return out


def lane_pattern(v):
    """the average bar (each bar as a share of its strongest step) and how often each step is a hit"""
    v = v[~np.isnan(v).any(axis=1)]
    if not len(v):
        return [0.0] * 16, [0.0] * 16
    n = v / np.maximum(v.max(axis=1, keepdims=True), 1e-9)
    return [round(float(x), 2) for x in n.mean(axis=0)], [round(float(x), 2) for x in (n > 0.5).mean(axis=0)]


def key_of(y):
    import librosa
    h = librosa.effects.harmonic(y, margin=3.0)
    c = librosa.feature.chroma_cqt(y=h, sr=SR, hop_length=1024).mean(axis=1)
    best = (-2, 0, "minor", [])
    scores = []
    for mode, p in MODES.items():
        for r in range(12):
            s = float(np.corrcoef(c, np.roll(p, r))[0, 1])
            scores.append((s, r, mode))
            if s > best[0]:
                best = (s, r, mode)
    scores.sort(reverse=True)
    return {"root": NOTE[best[1]], "mode": best[2], "fit": round(best[0], 2),
            "runner_up": f"{NOTE[scores[1][1]]} {scores[1][2]} ({scores[1][0]:.2f})",
            "chroma": [round(float(x / c.max()), 2) for x in c]}


def kick_of(y, bpm, phase):
    beat = 60 / bpm
    n = int(0.25 * SR)
    hits = [y[int((phase + k * beat) * SR):int((phase + k * beat) * SR) + n] for k in range(int((len(y) / SR - phase) / beat))]
    hits = [h for h in hits if len(h) == n]
    if not hits:
        return {}
    k = np.mean(hits, axis=0)

    def pitch_at(t):
        w = k[int(t * SR):int(t * SR) + 1024] * np.hanning(1024)
        sp = np.abs(np.fft.rfft(w, 8192))
        f = np.fft.rfftfreq(8192, 1 / SR)
        ok = (f > 30) & (f < 400)
        return float(f[ok][np.argmax(sp[ok])])

    env = np.abs(k)
    env = np.convolve(env, np.ones(64) / 64, "same")
    pk = int(np.argmax(env))
    below = np.nonzero(env[pk:] < env[pk] * 0.1)[0]
    sp = np.abs(np.fft.rfft(k[: int(0.03 * SR)], 4096)) ** 2
    f = np.fft.rfftfreq(4096, 1 / SR)
    return {"pitch_start_hz": round(pitch_at(0.008), 1), "pitch_end_hz": round(pitch_at(0.08), 1),
            "decay_ms": round(1000 * (below[0] if len(below) else len(env) - pk) / SR),
            "click": round(float(sp[f > 1000].sum() / max(sp.sum(), 1e-12)), 3)}


def bass_of(y, bpm, phase, root):
    """pyin over 20 s of the 50..300 Hz band: the note on each 16th (not those with the kick), as semitones over the
    key's root; and how many 16ths a note lasts"""
    import librosa
    from scipy.signal import butter, sosfilt
    seg = y[: 20 * SR]
    lp = sosfilt(butter(6, [40, 300], "bandpass", fs=SR, output="sos"), seg)
    f0, vflag, _ = librosa.pyin(lp, fmin=35, fmax=300, sr=SR, frame_length=2048, hop_length=HOP)
    fps = SR / HOP
    step = 60 / bpm / 4
    per = [[] for _ in range(16)]
    for i in range(int((len(seg) / SR - phase) / step)):
        t = phase + (i + 0.5) * step
        j = int(t * fps)
        if j < len(f0) and vflag[j] and not np.isnan(f0[j]):
            per[i % 16].append(int(round(librosa.hz_to_midi(f0[j]))))
    r = NOTE.index(root)
    notes = []
    for s in range(16):
        if len(per[s]) >= 3:
            m = int(np.bincount(per[s]).argmax())
            notes.append((m - r) % 12)
        else:
            notes.append(None)
    voiced = float(np.nanmean(vflag)) if len(vflag) else 0.0
    return {"steps_semitones_over_root": notes, "voiced": round(voiced, 2)}


def width_of(path, start, dur):
    st = decode(path, start, dur, ch=2)
    m, s = (st[0] + st[1]) / 2, (st[0] - st[1]) / 2
    return round(float(np.sqrt(np.mean(s ** 2)) / max(np.sqrt(np.mean(m ** 2)), 1e-9)), 3)


def structure_of(y, bpm):
    """bars with no kick (the kick band's onsets under a third of the track's median bar): intro, outro, breaks"""
    import librosa
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=1024)
    env = band_env(S, freqs, 30, 120)
    fps = SR / HOP
    bar = 4 * 60 / bpm
    n = int(len(env) / fps / bar)
    e = np.array([env[int(b * bar * fps):int((b + 1) * bar * fps)].mean() for b in range(n)])
    on = e > np.median(e) / 3
    runs, b = [], 0
    while b < n:
        if not on[b]:
            c = b
            while c < n and not on[c]:
                c += 1
            runs.append((b, c - b))
            b = c
        else:
            b += 1
    intro = runs[0][1] if runs and runs[0][0] == 0 else 0
    outro = runs[-1][1] if runs and runs[-1][0] + runs[-1][1] == n else 0
    mid = [L for (s, L) in runs if s != 0 and s + L != n]
    return {"bars": n, "intro_bars": intro, "outro_bars": outro, "breaks_bars": mid,
            "break_share": round(float(sum(mid)) / max(n - intro - outro, 1), 3),
            "longest_break_s": round(max(mid) * bar, 1) if mid else 0.0,
            "kick_bars_profile": "".join("#" if x else "." for x in on)}


def analyse(job):
    import librosa
    path, genre, title = job
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True, check=True).stdout.strip())
    start = max(20.0, dur * 0.4 - 60.0)
    seg = min(120.0, dur - start - 5.0)
    y = decode(path, start, seg)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    Sh, Sp = librosa.decompose.hpss(S, margin=2.0)      # (the hits from the percussive part: a rolling bass in the kick's
    envs = {k: band_env(S if k == "bass" else Sp, freqs, lo, hi, flux=(k != "bass"))   # band would hide its attacks)
            for k, (lo, hi) in LANES.items()}
    bpm0 = tempo_of(envs["kick"])
    bpm, phase = grid(envs["kick"], bpm0)
    nbars = int((seg - phase) / (240 / bpm)) - 1
    offs = bar_offsets(envs["kick"], bpm, phase, nbars)
    pats = {}
    for k, env in envs.items():
        avg, hit = lane_pattern(slot_values(env, bpm, phase, nbars, 0.02 if k == "bass" else 0.012, offs))
        pats[k] = {"avg": avg, "hit": hit}
    key = key_of(y)
    rms = float(np.sqrt(np.mean(y ** 2)))
    cent = librosa.feature.spectral_centroid(S=S, sr=SR)[0]
    # the bass's pump: 120..300 Hz energy folded over a beat (32 bins), 1 - min / max
    be = band_env(S, freqs, 120, 300, flux=False)
    fps = SR / HOP
    ph = (((np.arange(len(be)) / fps - phase) % (60 / bpm)) / (60 / bpm) * 32).astype(int) % 32
    fold = np.array([be[ph == i].mean() for i in range(32)])
    full = decode(path)
    out = {"title": title, "file": os.path.basename(path), "duration_s": round(dur, 1),
           "bpm": round(bpm, 2), "bpm_autocorr": round(bpm0, 2), "patterns": pats,
           "kick": kick_of(y, bpm, phase), "key": key,
           "bass": bass_of(y, bpm, phase, key["root"]),
           "sound": {"centroid_hz": round(float(np.median(cent))), "rms_dbfs": round(20 * np.log10(max(rms, 1e-9)), 1),
                     "crest_db": round(20 * np.log10(float(np.max(np.abs(y))) / max(rms, 1e-9)), 1),
                     "width": width_of(path, start, min(seg, 60.0)),
                     "pump": round(float(1 - fold.min() / max(fold.max(), 1e-9)), 2)},
           "structure": structure_of(full, bpm)}
    return genre, path, out


def median(v):
    v = [x for x in v if x is not None]
    return round(float(np.median(v)), 2) if v else None


def summarise(tracks):
    s = {"tracks": len(tracks)}
    s["bpm"] = {"median": median([t["bpm"] for t in tracks]), "min": min(t["bpm"] for t in tracks),
                "max": max(t["bpm"] for t in tracks)}
    for lane in LANES:
        s[lane] = {"avg": [median([t["patterns"][lane]["avg"][i] for t in tracks]) for i in range(16)],
                   "hit": [median([t["patterns"][lane]["hit"][i] for t in tracks]) for i in range(16)]}
    for k in ("pitch_start_hz", "pitch_end_hz", "decay_ms", "click"):
        s.setdefault("kick", {})[k] = median([t["kick"].get(k) for t in tracks])
    for k in ("centroid_hz", "rms_dbfs", "crest_db", "width", "pump"):
        s.setdefault("sound", {})[k] = median([t["sound"][k] for t in tracks])
    modes = {}
    for t in tracks:
        modes[t["key"]["mode"]] = modes.get(t["key"]["mode"], 0) + 1
    s["modes"] = modes
    s["break_share"] = median([t["structure"]["break_share"] for t in tracks])
    s["longest_break_s"] = median([t["structure"]["longest_break_s"] for t in tracks])
    s["intro_bars"] = median([t["structure"]["intro_bars"] for t in tracks])
    return s


def picture(genre, tracks, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, len(LANES), figsize=(3.2 * len(LANES), 0.28 * len(tracks) + 1.2))
    for ax, lane in zip(axs, LANES):
        m = np.array([t["patterns"][lane]["avg"] for t in tracks])
        ax.imshow(m, aspect="auto", cmap="magma", vmin=0, vmax=1)
        ax.set_title(f"{genre}: {lane}")
        ax.set_xticks(range(16))
        ax.set_xticklabels([str(i + 1) for i in range(16)], fontsize=6)
        ax.set_yticks(range(len(tracks)))
        ax.set_yticklabels([t["title"][:28] for t in tracks] if lane == "kick" else [""] * len(tracks), fontsize=6)
        for x in (3.5, 7.5, 11.5):
            ax.axvline(x, color="white", lw=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    out = argv[1]
    titles, jobs_n, specs, i = {}, os.cpu_count() or 2, [], 2
    while i < len(argv):
        if argv[i] == "--titles":
            titles = json.load(open(argv[i + 1]))
            i += 2
        elif argv[i] == "--jobs":
            jobs_n = int(argv[i + 1])
            i += 2
        else:
            specs.append(argv[i].split("=", 1))
            i += 1
    jobs = []
    for genre, src in specs:
        files = [os.path.join(src, f) for f in sorted(os.listdir(src))] if os.path.isdir(src) else [src]
        for f in files:
            tid = os.path.splitext(os.path.basename(f))[0]
            jobs.append((f, genre, titles.get(tid, tid)))
    res = {}
    with ProcessPoolExecutor(jobs_n) as ex:
        for fut in [ex.submit(analyse, j) for j in jobs]:
            try:
                genre, path, r = fut.result()
            except Exception as e:                         # (one bad file: said, the rest go on)
                print("FAILED", e, file=sys.stderr)
                continue
            res.setdefault(genre, []).append(r)
            os.makedirs(os.path.join(out, genre), exist_ok=True)
            json.dump(r, open(os.path.join(out, genre, os.path.splitext(r["file"])[0] + ".json"), "w"), indent=1)
            print(f"{genre:10s} {r['bpm']:6.1f} BPM  {r['key']['root']:2s} {r['key']['mode']:14s} {r['title'][:60]}")
    for genre, tracks in res.items():
        json.dump({"summary": summarise(tracks), "tracks": tracks}, open(os.path.join(out, genre + ".json"), "w"), indent=1)
        picture(genre, tracks, os.path.join(out, genre + "_patterns.png"))


if __name__ == "__main__":
    main(sys.argv)
