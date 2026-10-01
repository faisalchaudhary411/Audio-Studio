"""
procedural_music.py — code-based (no GPU, no model, no API) music generator.

Replaces the ACE-Step GPU worker as the default backend for the music tool
(see features.MUSIC_GPU_ENABLED; the GPU code in music_engine/music_client/
modal_workers/ace_step is untouched and can be switched back on).

How it works: style tags are parsed into a preset (genre, BPM, major/minor,
instrument choices, drums on/off). The engine then composes a chord
progression, bass line, melody motif and drum pattern, synthesises every
instrument with numpy/scipy, arranges it into intro / main / outro sections,
adds reverb, and masters to a 16-bit stereo WAV. Same tags + same seed =
same track; no seed = a fresh variation every time.

Instrumental only. Typical render time is a few seconds on the VPS CPU.
"""
import hashlib
import io
import re
import wave

import numpy as np
from scipy import signal

SR = 44100

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

# Chord progressions as 0-based scale degrees (one chord per bar).
PROGS = {
    "major": [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 4, 3], [1, 4, 0, 0], [0, 2, 5, 4]],
    "minor": [[0, 5, 2, 6], [0, 3, 6, 2], [0, 6, 5, 6], [1, 4, 0, 0], [0, 2, 3, 6]],
    "dorian": [[0, 3, 0, 6], [0, 1, 3, 0], [0, 6, 3, 0]],
}

# Drum patterns on a 16-step bar grid.
DRUMS = {
    "lofi":   dict(kick=[0, 7, 10], snare=[4, 12], hat=list(range(0, 16, 2)), open=[14]),
    "boom":   dict(kick=[0, 3, 10], snare=[4, 12], hat=list(range(0, 16, 2)), open=[]),
    "four":   dict(kick=[0, 4, 8, 12], snare=[4, 12], hat=[2, 6, 10, 14], open=[2, 6, 10, 14]),
    "pop":    dict(kick=[0, 6, 8, 14], snare=[4, 12], hat=list(range(0, 16, 2)), open=[]),
    "trap":   dict(kick=[0, 7, 11], snare=[8], hat=list(range(0, 16, 1)), open=[]),
    "soft":   dict(kick=[0, 8], snare=[], hat=[4, 12], open=[]),
}

# name -> preset. chords/melody/bass instrument names map to synth functions.
PRESETS = {
    "lofi":      dict(bpm=(70, 86),   mode=("minor", "dorian"), drums="lofi", chords="epiano", melody="epiano", bass="sub",   swing=0.55, lp=7500,  crackle=True,  reverb=0.22, sidechain=0.0,  sevenths=True),
    "chill":     dict(bpm=(84, 100),  mode=("minor", "major"),  drums="soft", chords="pad",    melody="pluck",  bass="sub",   swing=0.2,  lp=11000, crackle=False, reverb=0.30, sidechain=0.0,  sevenths=True),
    "ambient":   dict(bpm=(56, 70),   mode=("major", "minor"),  drums=None,   chords="pad",    melody="bell",   bass="sub",   swing=0.0,  lp=9000,  crackle=False, reverb=0.45, sidechain=0.0,  sevenths=True),
    "cinematic": dict(bpm=(64, 80),   mode=("minor",),          drums="soft", chords="strings", melody="bell", bass="sub",   swing=0.0,  lp=12000, crackle=False, reverb=0.40, sidechain=0.0,  sevenths=False),
    "corporate": dict(bpm=(96, 112),  mode=("major",),          drums="pop",  chords="piano",  melody="pluck",  bass="sub",   swing=0.0,  lp=14000, crackle=False, reverb=0.20, sidechain=0.0,  sevenths=False),
    "upbeat":    dict(bpm=(114, 128), mode=("major",),          drums="pop",  chords="pluck",  melody="pluck",  bass="saw",   swing=0.0,  lp=15000, crackle=False, reverb=0.18, sidechain=0.25, sevenths=False),
    "electronic": dict(bpm=(122, 134), mode=("minor", "major"), drums="four", chords="pad",    melody="saw",    bass="saw",   swing=0.0,  lp=16000, crackle=False, reverb=0.18, sidechain=0.55, sevenths=False),
    "hiphop":    dict(bpm=(78, 94),   mode=("minor",),          drums="boom", chords="epiano", melody="bell",   bass="808",   swing=0.3,  lp=11000, crackle=False, reverb=0.15, sidechain=0.0,  sevenths=True),
    "trap":      dict(bpm=(130, 150), mode=("minor",),          drums="trap", chords="pad",    melody="bell",   bass="808",   swing=0.0,  lp=14000, crackle=False, reverb=0.15, sidechain=0.0,  sevenths=False),
    "acoustic":  dict(bpm=(88, 108),  mode=("major", "dorian"), drums="soft", chords="pluck",  melody="pluck",  bass="sub",   swing=0.1,  lp=13000, crackle=False, reverb=0.22, sidechain=0.0,  sevenths=False),
}

# keyword -> preset (first match wins, so order matters)
GENRE_KEYWORDS = [
    ("lofi", "lofi"), ("lo-fi", "lofi"), ("study", "lofi"),
    ("trap", "trap"), ("hip hop", "hiphop"), ("hip-hop", "hiphop"), ("hiphop", "hiphop"), ("rap", "hiphop"),
    ("edm", "electronic"), ("electronic", "electronic"), ("house", "electronic"), ("techno", "electronic"),
    ("dance", "electronic"), ("synthwave", "electronic"),
    ("cinematic", "cinematic"), ("epic", "cinematic"), ("trailer", "cinematic"), ("orchestral", "cinematic"),
    ("ambient", "ambient"), ("meditation", "ambient"), ("relax", "ambient"), ("sleep", "ambient"), ("calm", "ambient"),
    ("corporate", "corporate"), ("business", "corporate"), ("presentation", "corporate"), ("explainer", "corporate"),
    ("upbeat", "upbeat"), ("happy", "upbeat"), ("pop", "upbeat"), ("energetic", "upbeat"), ("fun", "upbeat"),
    ("acoustic", "acoustic"), ("guitar", "acoustic"), ("folk", "acoustic"),
    ("chill", "chill"), ("jazz", "lofi"), ("piano", "chill"),
]
MAJOR_WORDS = ("happy", "uplifting", "bright", "cheerful", "upbeat", "sunny", "positive", "hopeful", "major")
MINOR_WORDS = ("sad", "dark", "melancholic", "melancholy", "moody", "emotional", "tense", "minor", "mysterious")
INSTR_WORDS = {"piano": "piano", "guitar": "pluck", "acoustic": "pluck", "pad": "pad", "synth": "saw",
               "strings": "strings", "bells": "bell", "electric piano": "epiano", "rhodes": "epiano"}


def parse_tags(tags: str) -> dict:
    t = (tags or "").lower()
    name = "chill"
    for kw, preset in GENRE_KEYWORDS:
        if kw in t:
            name = preset
            break
    cfg = dict(PRESETS[name])
    cfg["name"] = name
    m = re.search(r"(\d{2,3})\s*bpm", t)
    cfg["bpm_fixed"] = max(50, min(180, int(m.group(1)))) if m else None
    cfg["mode_forced"] = None
    if any(w in t for w in MINOR_WORDS):
        cfg["mode_forced"] = "minor"
    elif any(w in t for w in MAJOR_WORDS):
        cfg["mode_forced"] = "major"
    for kw, inst in INSTR_WORDS.items():
        if kw in t:
            cfg["chords"] = inst if inst in ("piano", "pad", "strings", "epiano", "pluck") else cfg["chords"]
            if inst in ("piano", "pluck", "bell", "saw", "epiano"):
                cfg["melody"] = inst
            break
    if re.search(r"no drums|without drums|drumless|no percussion", t):
        cfg["drums"] = None
    return cfg


# ── synth voices (all return mono float arrays) ──────────────────────────────

def _t(n):
    return np.arange(n, dtype=np.float64) / SR


def _fade_edges(y, attack=0.005, release=0.03):
    n = len(y)
    a = min(n, int(attack * SR))
    r = min(n, int(release * SR))
    if a > 0:
        y[:a] *= np.linspace(0, 1, a)
    if r > 0:
        y[-r:] *= np.linspace(1, 0, r)
    return y


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def v_epiano(f, dur):
    n = int(dur * SR); t = _t(n)
    idx = 1.4 * np.exp(-t * 5.0) + 0.15
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    y *= np.exp(-t * 1.8)
    y += 0.12 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 11)
    return _fade_edges(y, 0.004, 0.06) * 0.5


def v_piano(f, dur):
    n = int(dur * SR); t = _t(n)
    y = np.zeros(n)
    for k in range(1, 9):
        y += (1.0 / k ** 1.2) * np.sin(2 * np.pi * f * k * (1 + 0.0003 * k * k) * t) * np.exp(-t * (1.4 + 0.9 * k))
    return _fade_edges(y, 0.003, 0.08) * 0.55


def v_pluck(f, dur):
    n = int(dur * SR); t = _t(n)
    y = np.zeros(n)
    for k in range(1, 7):
        y += (1.0 / k) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (3.0 + 2.5 * k))
    return _fade_edges(y, 0.002, 0.05) * 0.7


def v_bell(f, dur):
    n = int(dur * SR); t = _t(n)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2)
    y += 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3.5)
    y += 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 6)
    return _fade_edges(y, 0.002, 0.1) * 0.5


def v_saw(f, dur):
    n = int(dur * SR); t = _t(n)
    y = sum(signal.sawtooth(2 * np.pi * f * (1 + c) * t) for c in (-0.004, 0.0, 0.004)) / 3
    sos = signal.butter(2, min(3200, SR / 2 - 100), fs=SR, output="sos")
    y = signal.sosfilt(sos, y) * np.exp(-t * 3.0)
    return _fade_edges(y, 0.004, 0.05) * 0.5


def v_pad(f, dur, attack=0.35, cutoff=1800):
    n = int(dur * SR); t = _t(n)
    y = sum(signal.sawtooth(2 * np.pi * f * (1 + c) * t) for c in (-0.006, 0.0, 0.006)) / 3
    sos = signal.butter(2, cutoff, fs=SR, output="sos")
    y = signal.sosfilt(sos, y)
    return _fade_edges(y, attack, 0.5) * 0.35


def v_strings(f, dur):
    return v_pad(f, dur, attack=0.7, cutoff=2600)


def v_sub(f, dur):
    n = int(dur * SR); t = _t(n)
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    y *= np.exp(-t * 1.2)
    return _fade_edges(y, 0.01, 0.05) * 0.6


def v_bsaw(f, dur):
    n = int(dur * SR); t = _t(n)
    y = signal.sawtooth(2 * np.pi * f * t)
    sos = signal.butter(2, 500, fs=SR, output="sos")
    y = signal.sosfilt(sos, y) * 0.9 + 0.4 * np.sin(2 * np.pi * f * t)
    return _fade_edges(y, 0.004, 0.04) * 0.5


def v_808(f, dur):
    n = int(dur * SR); t = _t(n)
    fr = f * (1 + 1.2 * np.exp(-t * 35))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 1.6)
    y = np.tanh(y * 1.8) * 0.7
    return _fade_edges(y, 0.002, 0.05)


VOICES = dict(epiano=v_epiano, piano=v_piano, pluck=v_pluck, bell=v_bell, saw=v_saw,
              pad=v_pad, strings=v_strings, sub=v_sub, bass_saw=v_bsaw, **{"808": v_808})
BASS_VOICES = dict(sub=v_sub, saw=v_bsaw, **{"808": v_808})


def _drum_kit(rng, soft=False):
    t = _t(int(0.4 * SR))
    ph = 2 * np.pi * np.cumsum(45 + 110 * np.exp(-t * 28)) / SR
    kick = np.sin(ph) * np.exp(-t * 8.5)
    kick[:60] += 0.3 * rng.standard_normal(60) * np.linspace(1, 0, 60)
    kick = np.tanh(kick * 1.6) * 0.9

    ts = _t(int(0.28 * SR))
    noise = rng.standard_normal(len(ts))
    sos = signal.butter(2, [1500, 7500], btype="band", fs=SR, output="sos")
    snare = signal.sosfilt(sos, noise) * np.exp(-ts * 22) * 0.7 + 0.5 * np.sin(2 * np.pi * 190 * ts) * np.exp(-ts * 26)
    if soft:
        sos2 = signal.butter(2, 4500, fs=SR, output="sos")
        snare = signal.sosfilt(sos2, snare) * 0.8

    th = _t(int(0.06 * SR))
    hn = rng.standard_normal(len(th))
    hn = signal.sosfilt(signal.butter(2, 7000, btype="high", fs=SR, output="sos"), hn)
    hat = hn * np.exp(-th * 75) * 0.35

    to = _t(int(0.25 * SR))
    on = signal.sosfilt(signal.butter(2, 6500, btype="high", fs=SR, output="sos"), rng.standard_normal(len(to)))
    open_hat = on * np.exp(-to * 16) * 0.3
    return dict(kick=kick, snare=snare, hat=hat, open=open_hat)


# ── composition helpers ──────────────────────────────────────────────────────

def _deg_midi(root, scale, deg):
    octv, idx = divmod(deg, len(scale))
    return root + 12 * octv + scale[idx]


def _chord_notes(root, scale, deg, sevenths):
    ks = (0, 2, 4, 6) if sevenths else (0, 2, 4)
    notes = [_deg_midi(root, scale, deg + k) for k in ks]
    out = []
    for n in notes:
        while n > 70:
            n -= 12
        while n < 52:
            n += 12
        out.append(n)
    return sorted(out)


def _place(buf, sig, start, gain=1.0):
    if start >= len(buf) or start < 0:
        return
    end = min(len(buf), start + len(sig))
    buf[start:end] += sig[: end - start] * gain


def _reverb(x_stereo, rng, decay=1.6, mix=0.25):
    n = int(decay * SR)
    t = _t(n)
    out = np.empty_like(x_stereo)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * (6.0 / decay))
        ir = signal.sosfilt(signal.butter(1, 5000, fs=SR, output="sos"), ir)
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        wet = signal.fftconvolve(x_stereo[ch], ir)[: x_stereo.shape[1]]
        out[ch] = x_stereo[ch] * (1 - mix) + wet * mix * 1.6
    return out


def generate_wav(tags: str, duration: int = 30, seed: int = None) -> bytes:
    """Render a track and return WAV bytes (16-bit stereo, 44.1 kHz)."""
    duration = int(max(10, min(180, duration)))
    cfg = parse_tags(tags)
    if seed is None:
        seed = int.from_bytes(hashlib.sha256(np.random.bytes(8)).digest()[:4], "big")
    rng = np.random.default_rng(seed)
    pyr = np.random.RandomState(seed % (2 ** 32))

    mode = cfg["mode_forced"] or cfg["mode"][pyr.randint(len(cfg["mode"]))]
    scale = SCALES[mode]
    bpm = cfg["bpm_fixed"] or pyr.randint(cfg["bpm"][0], cfg["bpm"][1] + 1)
    prog = PROGS[mode][pyr.randint(len(PROGS[mode]))]
    root = 48 + pyr.randint(0, 12)  # C3..B3

    beat = 60.0 / bpm
    bar_s = beat * 4
    step = bar_s / 16
    bars = int(np.ceil(duration / bar_s)) + 1
    N = int((bars * bar_s + 3) * SR)
    swing = cfg["swing"]

    def step_pos(bar, st):
        s = st
        off = 0.0
        if st % 2 == 1:
            off = swing * 0.5 * step
        return int((bar * bar_s + s * step + off) * SR)

    drums_buf = np.zeros(N)
    bass_buf = np.zeros(N)
    chord_l, chord_r = np.zeros(N), np.zeros(N)
    mel_buf = np.zeros(N)
    kick_times = []

    kit = _drum_kit(rng, soft=cfg["name"] in ("lofi", "chill", "acoustic"))
    chord_voice = VOICES[cfg["chords"]]
    mel_voice = VOICES[cfg["melody"]]
    bass_voice = BASS_VOICES[cfg["bass"]]
    pattern = DRUMS.get(cfg["drums"]) if cfg["drums"] else None
    sustained = cfg["chords"] in ("pad", "strings")

    intro = 2 if bars >= 8 else 1 if bars >= 5 else 0
    outro_bar = bars - 2

    # melody motif: rhythm (steps) + degree offsets relative to the chord root
    rhythms = [[0, 6, 10], [0, 4, 8, 11], [2, 6, 12], [0, 3, 8, 10, 14], [0, 8, 12], [4, 8, 14]]
    rhythm = rhythms[pyr.randint(len(rhythms))]
    offsets = [int(pyr.choice([0, 2, 4, 1, 3, 7, 9])) for _ in rhythm]
    alt_offsets = offsets[:-1] + [int(pyr.choice([0, 2, 4]))]

    for bar in range(bars):
        deg = prog[bar % len(prog)]
        notes = _chord_notes(root, scale, deg, cfg["sevenths"])
        t0 = step_pos(bar, 0)
        full = bar >= intro and bar < outro_bar
        # chords
        if sustained:
            dur = bar_s * 1.05
            for n in notes:
                v = chord_voice(hz(n), dur)
                _place(chord_l, v, t0, 0.5)
                _place(chord_r, v, t0 + 300, 0.5)
        else:
            strum = [0, 0, 0, 0] if cfg["chords"] in ("epiano", "piano") else [0, 2, 4, 6]
            hits = [0] if cfg["chords"] in ("epiano", "piano") and cfg["name"] != "upbeat" else [0, 6, 10]
            if cfg["name"] in ("upbeat", "acoustic", "corporate"):
                hits = [0, 4, 8, 12] if cfg["name"] == "upbeat" else [0, 3, 6, 8, 11, 14]
            for h in hits:
                for i, n in enumerate(notes):
                    st_off = int((i * 0.012 + (strum[i % 4] * 0.004)) * SR)
                    v = chord_voice(hz(n), min(bar_s * 1.2, 2.4))
                    p = step_pos(bar, h) + st_off
                    _place(chord_l, v, p, 0.45 if h == 0 else 0.3)
                    _place(chord_r, v, p + 220, 0.45 if h == 0 else 0.3)
        # bass
        if full or (bar >= intro and bar < bars - 1):
            broot = _deg_midi(root, scale, deg) - 24
            while broot < 28:
                broot += 12
            bsteps = [0, 6, 10] if cfg["drums"] else [0]
            if cfg["bass"] == "saw":
                bsteps = [0, 4, 8, 12] if cfg["name"] == "electronic" else [0, 6, 8, 14]
            for h in bsteps:
                d = bar_s / 2 if h == 0 else step * 4
                _place(bass_buf, bass_voice(hz(broot), d), step_pos(bar, h), 0.7)
        # drums
        if pattern and full:
            fill = (bar % 8 == 7)
            for st in pattern["kick"]:
                if fill and st != 0:
                    continue
                p = step_pos(bar, st)
                _place(drums_buf, kit["kick"], p, 0.95)
                kick_times.append(p)
            for st in pattern["snare"]:
                _place(drums_buf, kit["snare"], step_pos(bar, st), 0.8)
            for st in pattern["hat"]:
                vel = 0.55 + 0.35 * (st % 4 == 0) + 0.1 * rng.random()
                _place(drums_buf, kit["hat"], step_pos(bar, st), vel)
            for st in pattern["open"]:
                _place(drums_buf, kit["open"], step_pos(bar, st), 0.7)
            if fill:
                for st in (12, 13, 14, 15):
                    _place(drums_buf, kit["snare"], step_pos(bar, st), 0.35 + 0.1 * (st - 12))
        # melody: phrase of 2 bars, silent every 4th phrase for breathing room
        phrase = bar // 2
        if full and (phrase % 4 != 3) and bar >= intro:
            use = offsets if bar % 2 == 0 else alt_offsets
            for st, off in zip(rhythm, use):
                midi = _deg_midi(root + 12, scale, deg + off)
                while midi > 88:
                    midi -= 12
                dur = min(1.6, step * (4 if cfg["melody"] != "bell" else 6))
                if cfg["melody"] == "bell":
                    dur = 1.8
                _place(mel_buf, mel_voice(hz(midi), dur), step_pos(bar, st), 0.55)

    # sidechain pump on harmonic bus + bass
    if cfg["sidechain"] > 0 and kick_times:
        env = np.ones(N)
        L = int(0.28 * SR)
        shape = 1 - cfg["sidechain"] * np.exp(-_t(L) * 11)
        for p in kick_times:
            e = min(N, p + L)
            env[p:e] = np.minimum(env[p:e], shape[: e - p])
        chord_l *= env; chord_r *= env; bass_buf *= env

    # texture
    tex = np.zeros(N)
    if cfg["crackle"]:
        hiss = signal.sosfilt(signal.butter(2, [800, 6000], btype="band", fs=SR, output="sos"), rng.standard_normal(N)) * 0.004
        pops = (rng.random(N) < 0.00018) * rng.standard_normal(N) * 0.05
        tex = hiss + pops
    elif cfg["name"] in ("ambient", "cinematic"):
        sw = signal.sosfilt(signal.butter(2, [200, 1500], btype="band", fs=SR, output="sos"), rng.standard_normal(N))
        tex = sw * (0.012 + 0.01 * np.sin(2 * np.pi * _t(N) / (bar_s * 4)))

    # stereo mix
    harm = np.vstack([chord_l, chord_r])
    mel = np.vstack([mel_buf, np.roll(mel_buf, int(0.011 * SR))])  # Haas width
    harm_mel = _reverb(harm * 0.9 + mel * 0.7, rng, decay=1.8 if cfg["reverb"] > 0.3 else 1.1, mix=cfg["reverb"])
    mix = harm_mel + np.vstack([bass_buf, bass_buf]) * 0.9 + np.vstack([drums_buf, drums_buf]) * 0.75
    mix += np.vstack([tex, np.roll(tex, 700)])

    # master: HPF, tone, soft clip, trim, fades, normalise
    mix = signal.sosfilt(signal.butter(2, 30, btype="high", fs=SR, output="sos"), mix, axis=1)
    mix = signal.sosfilt(signal.butter(2, min(cfg["lp"], SR / 2 - 200), fs=SR, output="sos"), mix, axis=1)
    mix = np.tanh(mix * 1.15)
    total = int(duration * SR)
    mix = mix[:, :total]
    fo = min(total, int(min(3.0, duration * 0.12) * SR))
    mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    fi = int(0.03 * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi)
    peak = np.max(np.abs(mix)) or 1.0
    mix = mix / peak * 0.89

    pcm = (mix.T * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
