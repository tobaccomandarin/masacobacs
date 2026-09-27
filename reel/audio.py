"""Score + sound design, synthesised from scratch with numpy (no samples).

A 128 BPM, 8-bar track in F minor that follows the picture beat for beat, plus
foley-style UI/motion sound effects placed on the exact beats the animation uses.
Everything is mixed with extra 150 Hz - 5 kHz content so it still reads on phone
speakers.
"""
import math

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

import scenes
from lib import BEAT, DURATION

SR = 48000
N = int(round(DURATION * SR))
rng = np.random.default_rng(128)


def sec(bt):
    return bt * BEAT


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x)


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def saw(freq, t, phase=0.0):
    ph = (freq * t + phase) % 1.0
    return 2 * ph - 1


def svf_sweep(x, f0, f1, q=0.7, curve=2.0):
    """Resonant low-pass whose cutoff glides exponentially from f0 to f1."""
    n = len(x)
    out = np.empty(n)
    low = band = 0.0
    k = 1.0 / q
    for i in range(n):
        p = (i / max(1, n - 1)) ** curve
        fc = f0 * (f1 / f0) ** p
        f = 2 * math.sin(math.pi * min(fc, SR * 0.2) / SR)
        high = x[i] - low - k * band
        band += f * high
        low += f * band
        out[i] = low
    return out


class Bus:
    def __init__(self):
        self.x = np.zeros((2, N))

    def add(self, sig, t0, gain=1.0, pan=0.0):
        if sig.ndim == 1:
            a = (pan + 1) * math.pi / 4
            sig = np.vstack([sig * math.cos(a), sig * math.sin(a)]) * math.sqrt(2)
        i0 = int(round(t0 * SR))
        if i0 >= N:
            return
        if i0 < 0:
            sig = sig[:, -i0:]
            i0 = 0
        n = min(sig.shape[1], N - i0)
        self.x[:, i0:i0 + n] += sig[:, :n] * gain


# ------------------------------------------------------------------ instruments
def kick(big=False):
    t = tt(0.55 if not big else 0.9)
    f = 48 + 150 * np.exp(-t * 30) + 40 * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * (5.0 if not big else 3.0))
    click = hp(noise(0.006), 2500) * np.exp(-tt(0.006) * 900) * 0.6
    body[:len(click)] += click
    return np.tanh(body * 2.2) * 0.9


def clap():
    out = np.zeros(int(0.35 * SR))
    for k, d in enumerate((0.0, 0.009, 0.019, 0.028)):
        n = bp(noise(0.3), 900, 3200) * np.exp(-tt(0.3) * (60 if k < 3 else 13))
        i = int(d * SR)
        out[i:i + len(n)] += n[:len(out) - i]
    return out * 0.9


def hat(open_=False):
    d = 0.28 if open_ else 0.05
    n = hp(noise(d), 7000, 4) * np.exp(-tt(d) * (11 if open_ else 70))
    return n * 0.7


def bass_note(midi, dur, cutoff=900.0):
    t = tt(dur)
    f = mtof(midi)
    x = 0.55 * saw(f, t) + 0.45 * saw(f * 1.006, t, 0.3)
    x = lp(x, cutoff, 2)
    sub = np.sin(2 * np.pi * f / 2 * t) * 0.55
    env = np.minimum(1, t / 0.004) * np.exp(-t * 2.2) * np.minimum(1, (dur - t) / 0.02 + 0.0)
    return np.tanh((x + sub) * 1.6) * env


def supersaw(midis, dur, cutoff, attack=0.01, release=0.3, voices=5, spread=0.012):
    t = tt(dur + release)
    x = np.zeros((2, len(t)))
    for m in midis:
        f = mtof(m)
        for v in range(voices):
            det = 1 + spread * (v - (voices - 1) / 2) / ((voices - 1) / 2)
            s = saw(f * det, t, rng.random())
            pan = (v / (voices - 1)) * 2 - 1
            a = (pan * 0.8 + 1) * math.pi / 4
            x[0] += s * math.cos(a)
            x[1] += s * math.sin(a)
    x /= len(midis) * voices ** 0.5
    x = np.vstack([lp(x[0], cutoff, 2), lp(x[1], cutoff, 2)])
    env = np.minimum(1, t / attack) * np.clip((dur + release - t) / release, 0, 1) ** 1.5
    return x * env


def pluck(midi, dur=0.35, bright=4000.0):
    t = tt(dur)
    f = mtof(midi)
    x = 0.6 * saw(f, t) + 0.4 * np.sign(np.sin(2 * np.pi * f * 1.002 * t))
    x = lp(x, bright, 2) * np.exp(-t * 11)
    return x * np.minimum(1, t / 0.002)


def bell(freq, dur=2.2, index=2.2):
    t = tt(dur)
    mod = np.sin(2 * np.pi * freq * 3.5 * t) * index * np.exp(-t * 3)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 2.4) * np.minimum(1, t / 0.002)


# ------------------------------------------------------------------ sound effects
def whoosh(dur, f0, f1, curve=1.6, shape="up"):
    x = noise(dur)
    x = svf_sweep(x, f0, f1, q=1.6, curve=curve)
    t = np.linspace(0, 1, len(x))
    env = t ** 2.2 if shape == "up" else np.sin(np.pi * t) ** 1.5 if shape == "bell" else (1 - t) ** 2
    return x * env / (np.abs(x).max() + 1e-9)


def impact(scale=1.0):
    t = tt(2.2)
    f = 30 + 60 * np.exp(-t * 7)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.9)
    crash = lp(hp(noise(2.2), 600), 7000) * np.exp(-t * 3.2) * 0.35
    thump = lp(noise(2.2), 250) * np.exp(-t * 14) * 1.5
    return np.tanh((boom * 1.2 + crash + thump) * 1.4) * scale


def tick(freq=3200.0, dur=0.012):
    t = tt(dur)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 400)


def key_click():
    t = tt(0.02)
    n = bp(noise(0.02), 2500, 9000) * np.exp(-t * 380)
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 250) * 0.4
    return n + body


def pop(f0=420.0, f1=1100.0, dur=0.07):
    t = tt(dur)
    f = f0 + (f1 - f0) * (1 - np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * np.minimum(1, t / 0.001)


def glide(f0, f1, dur, decay=4.0):
    t = tt(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay) * np.minimum(1, t / 0.003)


def boing():
    t = tt(0.32)
    thud = np.sin(2 * np.pi * np.cumsum(140 * np.exp(-t * 9) + 55) / SR) * np.exp(-t * 16)
    f = 520 * np.exp(-t * 5) + 180 + 22 * np.sin(2 * np.pi * 26 * t)
    squeak = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.35
    return thud + squeak


def zip_sfx(dur=0.22):
    t = tt(dur)
    f = 250 * (7 ** (t / dur))
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    return lp(x, 3500) * np.sin(np.pi * t / dur) ** 0.7 * 0.5


def glitch(dur=0.075):
    t = tt(dur)
    x = np.sign(np.sin(2 * np.pi * 1750 * t)) * (np.floor(t * 420) % 2)
    x += hp(noise(dur), 3000) * 0.5
    return x * 0.35


def reverse_swell(dur):
    x = hp(noise(dur), 3000) + 0.4 * bp(noise(dur), 500, 3000)
    t = np.linspace(0, 1, len(x))
    return x * t ** 3.2


# ------------------------------------------------------------------ score
CHORDS = {
    "Fm": [53, 56, 60, 63, 67],
    "Db": [49, 53, 56, 60, 65],
    "Eb": [51, 55, 58, 62, 65],
    "Ab": [56, 60, 63, 67, 72],
}
ROOT = {"Fm": 29, "Db": 25, "Eb": 27, "Ab": 32}
# (start beat, length in beats, chord)
PROGRESSION = [(0, 4, "Fm"), (4, 4, "Fm"), (8, 4, "Db"), (12, 4, "Eb"),
               (16, 4, "Fm"), (20, 2, "Db"), (22, 2, "Eb"), (24, 4, "Db"), (28, 4, "Fm")]


def chord_at(bt):
    for b0, ln, c in PROGRESSION:
        if b0 <= bt < b0 + ln:
            return c
    return "Fm"


def kick_beats():
    ks = [0, 1, 2, 3] + list(range(4, 12)) + [12, 13, 14, 14.5, 15, 15.25, 15.5]
    ks += list(range(16, 24)) + [26, 27, 27.5, 27.75] + [28, 29, 30]
    return ks


def build():
    drums, bass, music, sfx, send = Bus(), Bus(), Bus(), Bus(), Bus()
    K = kick()

    # ---------------------------------------------------------------- drums
    for b in kick_beats():
        g = 0.55 if b < 4 else 1.0
        if b == 16 or b == 28:
            drums.add(kick(big=True), sec(b), 1.1)
        else:
            k = K if b >= 4 else lp(K, 900)
            drums.add(k, sec(b), g)
    CL = clap()
    for b in (5, 7, 9, 11, 17, 19, 21, 23, 29):
        drums.add(CL, sec(b), 0.55, 0.05)
        send.add(CL, sec(b), 0.18)
    for i in range(8):  # snare roll into the drop
        b = 14 + i * 0.25
        drums.add(CL, sec(b), 0.12 + 0.35 * i / 7, 0.1)
    for i in range(16):  # roll into the finale
        b = 26 + i * 0.125
        drums.add(CL, sec(b), 0.06 + 0.3 * (i / 15) ** 2, -0.1)
    HC, HO = hat(), hat(True)
    for b8 in range(8, 32 * 2):
        b = b8 / 2
        if not (4 <= b < 15.75 or 16 <= b < 24 or 26 <= b < 28):
            continue
        if b % 1 == 0.5:
            drums.add(HO if b >= 16 and b < 24 else HC, sec(b), 0.22, 0.35)

    # ---------------------------------------------------------------- bass
    for b8 in range(4 * 2, 32 * 2):
        b = b8 / 2
        root = ROOT[chord_at(b)]
        if 4 <= b < 12 and b % 1 == 0.5:
            bass.add(bass_note(root + 12, sec(0.45), 700), sec(b), 0.55)
        elif 12 <= b < 15.75:
            bass.add(bass_note(root + 12 + (12 if b8 % 2 else 0), sec(0.45), 500 + 120 * (b - 12)), sec(b), 0.5)
    for b8 in range(16 * 2, 24 * 2):
        b = b8 / 2
        if b8 % 2:
            root = ROOT[chord_at(b)]
            bass.add(bass_note(root + 12, sec(0.45), 1100), sec(b), 0.55)
    bass.add(bass_note(ROOT["Fm"] + 12, sec(3.0), 800), sec(28), 0.7)

    # ---------------------------------------------------------------- harmony
    for b0, ln, c in PROGRESSION:
        notes = CHORDS[c]
        if b0 < 4:
            music.add(supersaw(notes, sec(ln), 700, attack=0.4), sec(b0), 0.35)
        elif b0 < 16:
            music.add(supersaw(notes, sec(ln), 1300 + 300 * (b0 - 4) / 4, attack=0.05), sec(b0), 0.3)
        elif b0 < 24:
            music.add(supersaw(notes, sec(ln), 3200, attack=0.01), sec(b0), 0.33)
            for k in range(int(ln * 2)):  # off-beat chord stabs
                bb = b0 + k * 0.5 + (0.5 if k % 2 == 0 else 0)
                if bb < b0 + ln:
                    music.add(supersaw([n + 12 for n in notes[:4]], 0.09, 5000, release=0.12), sec(bb), 0.28)
        elif b0 < 28:
            music.add(supersaw(notes, sec(ln), 2400, attack=0.3), sec(b0), 0.62)
        else:
            music.add(supersaw(notes + [notes[0] + 24], sec(ln) - 0.2, 4200, attack=0.005, release=0.2), sec(b0), 0.42)
    # arps for the builds
    for i in range(16):
        b = 12 + i * 0.25
        notes = CHORDS[chord_at(b)]
        music.add(pluck(notes[i % 4] + 12, bright=1500 + 250 * i), sec(b), 0.22, 0.4 * math.sin(i))
    for i in range(16):
        b = 24 + i * 0.25
        notes = CHORDS[chord_at(b)]
        m = notes[[0, 2, 4, 2][i % 4]] + (12 if i >= 8 else 0)
        music.add(pluck(m, 0.4, 1800 + 200 * i), sec(b), 0.42, -0.3 * math.cos(i))
        send.add(pluck(m, 0.4, 1800 + 200 * i), sec(b), 0.12)

    # risers into the drop and the finale
    r = whoosh(sec(4), 300, 9000, curve=2.4)
    sfx.add(r, sec(12), 0.2)
    riser_tone = glide(mtof(53), mtof(77), sec(3.75), decay=0.0) * np.linspace(0, 1, int(sec(3.75) * SR)) ** 2
    sfx.add(lp(riser_tone, 3000), sec(12), 0.12)
    sfx.add(reverse_swell(sec(1.0)), sec(15.0), 0.4)
    sfx.add(whoosh(sec(2), 400, 8000, curve=2.0), sec(26), 0.3)

    # ---------------------------------------------------------------- foley / UI
    # bar 1: bouncing ball
    for b in scenes.IMPACTS:
        sfx.add(boing(), sec(b), 0.6, (scenes._dot_xy(b)[0] - 540) / 540)
    sfx.add(whoosh(0.25, 300, 1400, shape="bell"), sec(0.15), 0.15)
    sfx.add(glide(300, 900, 0.22, decay=6), sec(3.0), 0.25)
    sfx.add(whoosh(sec(0.45), 200, 6000, curve=2.5), sec(3.55), 0.55)
    sfx.add(impact(0.55), sec(4.0), 0.6)

    # bar 2: kinetic type
    for li, (text, start) in enumerate(zip(scenes.TYPE_LINES, scenes.TYPE_STARTS)):
        sfx.add(lp(noise(0.08), 900) * np.exp(-tt(0.08) * 50), sec(start), 0.5)
        for gi, ch in enumerate(text):
            if ch != " ":
                sfx.add(tick(2600 + 180 * gi, 0.01), sec(start + gi * scenes.LETTER_STAGGER), 0.12,
                        -0.6 + 1.2 * gi / max(1, len(text) - 1))
    sfx.add(pop(900, 2200), sec(scenes.DIAMOND_T), 0.3, 0.6)
    for wi in range(4):
        sfx.add(tick(1800, 0.015), sec(scenes.PAYOFF_T + wi * 0.12), 0.1)
    sfx.add(whoosh(sec(0.55), 150, 5000, curve=1.8), sec(7.45), 0.5)
    sfx.add(lp(kick(), 400), sec(8.0), 0.4)

    # bar 3: graph editor
    for i in range(9):
        sfx.add(tick(4200 - i * 180, 0.008), sec(8.0 + i * 0.03), 0.09, -0.8 + 0.2 * i)
    for tch in scenes.typed_char_times(scenes.BEZIER_TXT, scenes.BEZIER_T):
        sfx.add(key_click(), sec(tch), 0.22, rng.uniform(-0.3, 0.3))
    for b, a0, a1 in scenes.LIN_MOVES:
        sfx.add(whoosh(sec(scenes.MOVE_LEN), 500, 900, shape="bell"), sec(b), 0.12, a1 * 2 - 1)
    for b, a0, a1 in scenes.EASE_MOVES:
        sfx.add(whoosh(0.25, 4000, 600, curve=0.6, shape="down"), sec(b), 0.3, a1 * 2 - 1)
    sfx.add(zip_sfx(), sec(10.0), 0.35)
    sfx.add(pop(500, 1300), sec(10.0), 0.3, -0.5)
    sfx.add(pop(600, 1500), sec(10.12), 0.3, 0.5)
    sfx.add(whoosh(sec(0.45), 300, 7000, curve=2.5), sec(11.55), 0.5)
    sfx.add(impact(0.45), sec(12.0), 0.5)

    # bar 4: stagger grid ripples
    for k, b in enumerate(scenes.GRID_BEATS):
        for i in range(7):
            sfx.add(tick(1500 * 2 ** ((k * 2 + i) / 12), 0.03), sec(b + i * 0.05), 0.07,
                    math.sin(i * 1.7) * 0.7)
    sfx.add(glide(1200, 180, sec(0.45), decay=1.5), sec(15.5), 0.18)

    # bar 5: the drop
    sfx.add(impact(1.0), sec(16.0), 0.9)
    send.add(impact(1.0), sec(16.0), 0.25)
    sfx.add(lp(noise(0.3), 1500) * np.exp(-tt(0.3) * 14), sec(18), 0.45)
    for k in range(6):
        sfx.add(whoosh(0.18, 3000, 500, curve=0.7, shape="down"), sec(19.72 + k * 0.03), 0.13,
                1 if k % 2 == 0 else -1)

    # bar 6: parallax
    sfx.add(pop(350, 900, 0.12), sec(20.6), 0.35)
    sfx.add(bell(mtof(84), 1.0, 1.2), sec(20.75), 0.07)
    sfx.add(whoosh(0.6, 800, 2500, shape="bell"), sec(22), 0.14, 0.4)
    sfx.add(whoosh(sec(0.6), 200, 12000, curve=3.0), sec(23.4), 0.6)
    sfx.add(glide(200, 1600, sec(0.6), decay=0), sec(23.4), 0.08)

    # bar 7: construction
    for t0, pan in ((24.05, -0.5), (24.15, 0.5)):
        sfx.add(bp(noise(0.35), 2000, 6000) * np.sin(np.linspace(0, np.pi, int(0.35 * SR))) ** 2, sec(t0), 0.12, pan)
    for k in range(4):
        sfx.add(bp(noise(0.3), 1500, 5000) * np.sin(np.linspace(0, np.pi, int(0.3 * SR))), sec(24.3 + k * 0.14), 0.06)
    for i in range(12):
        sfx.add(tick(2400, 0.01), sec(25.45 + i * 0.03), 0.06, math.cos(i * TAU12))
    penta = [65, 68, 70, 72, 75, 77, 80, 82, 84, 87, 89, 92]
    for i in range(12):  # each spark ray plays a note
        p = pluck(penta[i], 0.5, 5000)
        sfx.add(p, sec(26.0 + i * 0.065), 0.17, math.sin(i * TAU12))
        send.add(p, sec(26.0 + i * 0.065), 0.1)
    sfx.add(reverse_swell(sec(0.5)), sec(27.5), 0.35)

    # bar 8: signature
    sfx.add(impact(0.9), sec(28.0), 0.85)
    send.add(impact(0.9), sec(28.0), 0.3)
    shimmer = bell(mtof(89), 2.5, 1.6) * 0.5 + bell(mtof(96), 2.5, 1.0) * 0.3
    sfx.add(shimmer, sec(28.0), 0.18)
    send.add(shimmer, sec(28.0), 0.25)
    for i in range(6):
        sfx.add(tick(1500 + 120 * i, 0.012), sec(28.05 + i * 0.045), 0.1)
    for i, m in enumerate([77, 80, 84, 87, 89, 92, 96]):
        c = bell(mtof(m), 1.2, 0.8)
        sfx.add(c, sec(scenes.JP_T + i * 0.07), 0.06, -0.5 + i / 6)
        send.add(c, sec(scenes.JP_T + i * 0.07), 0.05)
    # outro: each retracting ray replays its build note, now descending
    for i, t0 in enumerate(scenes.retract_times()):
        p = pluck(penta[i], 0.45, 3500)
        sfx.add(p, sec(t0), 0.12, math.sin(i * TAU12))
        send.add(p, sec(t0), 0.09)
    sfx.add(whoosh(sec(0.65), 3000, 250, curve=0.8, shape="bell"), sec(scenes.DARK_T[0]), 0.16)
    ding = bell(mtof(84), 1.4, 1.5)
    sfx.add(ding, sec(scenes.DOT_T[1]), 0.22)
    send.add(ding, sec(scenes.DOT_T[1]), 0.2)

    # ---------------------------------------------------------------- sidechain
    t = np.arange(N) / SR
    duck = np.ones(N)
    for b in kick_beats():
        i0 = int(sec(b) * SR)
        seg = t[i0:] - t[i0]
        env = 1 - 0.75 * np.exp(-seg / 0.09)
        duck[i0:] = np.minimum(duck[i0:], env)
    bass.x *= duck
    music.x *= 0.35 + 0.65 * duck

    # ---------------------------------------------------------------- reverb
    ir_t = tt(2.4)
    ir = np.vstack([lp(rng.standard_normal(len(ir_t)), 6000) * np.exp(-ir_t * 2.6) for _ in range(2)])
    ir[:, :int(0.02 * SR)] = 0
    ir /= np.abs(ir).sum(axis=1, keepdims=True) ** 0.5 * 10
    rev_in = send.x + 0.25 * music.x
    wet = np.vstack([fftconvolve(rev_in[c], ir[c])[:N] for c in range(2)])

    # ---------------------------------------------------------------- master
    mix = drums.x * 1.0 + bass.x * 0.9 + music.x * 0.8 + sfx.x * 1.0 + wet * 0.6
    mix = np.vstack([hp(mix[c], 28) for c in range(2)])
    # presence lift so it survives phone speakers
    mix += np.vstack([bp(mix[c], 1800, 5000) for c in range(2)]) * 0.15
    peak = np.abs(mix).max()
    mix = np.tanh(mix / peak * 1.9) / np.tanh(1.9)
    fade = np.ones(N)
    fl = int(0.25 * SR)
    fade[-fl:] = np.linspace(1, 0.0, fl) ** 1.5
    mix *= fade * 10 ** (-1.0 / 20)
    return mix.astype(np.float32)


TAU12 = 2 * math.pi / 12


def write_wav(path):
    from scipy.io import wavfile
    mix = build()
    wavfile.write(path, SR, (mix.T * 32767).astype(np.int16))
    return path


if __name__ == "__main__":
    import sys
    write_wav(sys.argv[1] if len(sys.argv) > 1 else "out/reel.wav")
