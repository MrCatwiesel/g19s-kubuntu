"""Künstliche Signale (Sprache, Musik) zum Abstimmen der Spracherkennung – 22050 Hz mono, −1…1."""
import numpy as np

R = 22050


def speech(seconds, seed=1, bed=0.0):
    """Sprache: Silben (Grundton 110–140 Hz mit Obertönen, Formant-Färbung, Zischlaute), Wort- und Satzpausen,
    wie im Radio komprimiert. bed = leise Musik darunter (0…1)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * R)
    out = np.zeros(n)
    i = 0
    while i < n:
        phrase = rng.uniform(1.2, 3.0)
        end = min(n, i + int(phrase * R))
        while i < end:
            syl = int(rng.uniform(0.12, 0.26) * R)
            t = np.arange(syl) / R
            f0 = rng.uniform(105, 145) * (1 + 0.05 * np.sin(2 * np.pi * 3 * t))
            ph = 2 * np.pi * np.cumsum(f0) / R
            v = sum(np.sin(k * ph) * (1.0 / k) * (2.2 if 4 <= k <= 8 else 1.0) for k in range(1, 26))
            if rng.random() < 0.3:
                v = v * 0.4 + rng.standard_normal(syl) * 0.8 * np.linspace(0, 1, syl)  # Zischlaut
            env = np.sin(np.pi * np.linspace(0, 1, syl)) ** 0.6
            seg = v * env
            j = min(n, i + syl)
            out[i:j] = seg[:j - i]
            i = j + int(rng.uniform(0.02, 0.09) * R)
        i = end + int(rng.uniform(0.25, 0.6) * R)
    out = np.tanh(out / (np.percentile(np.abs(out), 99) + 1e-9) * 1.5) * 0.6
    if bed:
        out = out + bed * music(seconds, seed + 7, drums=False)[:n]
    return out


def music(seconds, seed=2, bpm=120, drums=True):
    """Musik: Kick, Bass, Akkorde, Hi-Hat (drums=False: nur Flächen und Melodie, z. B. Ballade)."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * R)) / R
    p = 60 / bpm
    out = 0.25 * (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 277 * t) + np.sin(2 * np.pi * 330 * t)) / 3
    out += 0.2 * np.sin(2 * np.pi * (440 + 110 * np.sign(np.sin(2 * np.pi * t / (2 * p)))) * t)
    if drums:
        out += 0.8 * np.exp(-(t % p) * 14) * np.sin(2 * np.pi * 55 * t)
        out += 0.35 * np.sin(2 * np.pi * 82 * t)
        out += 0.08 * rng.standard_normal(len(t)) * np.exp(-((t + p / 2) % (p / 2)) * 30)
    else:
        out += 0.25 * np.sin(2 * np.pi * 110 * t)
    return np.tanh(out * 1.2) * 0.6


def waltz(seconds, bpm=180, seed=3, swing=0.0, start=0.0):
    """Walzer („Umm-pa-pa“): Bass auf der Eins, Begleitakkord auf zwei und drei, Melodie darüber.
    bpm = Schläge (Viertel) je Minute; start = Zeitpunkt der ersten Eins (s); swing = Zittern der Schläge (s)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * R)
    t = np.arange(n) / R
    p = 60 / bpm
    out = 0.12 * np.sin(2 * np.pi * (330 + 55 * np.sign(np.sin(2 * np.pi * t / (6 * p)))) * t)   # Melodie
    k = 0
    beat = start
    while beat < seconds:
        i = int(max(0.0, beat + rng.uniform(-swing, swing)) * R)
        d = t[i:i + R] - t[i]
        if k % 3 == 0:                                                  # Umm: tiefer Bass
            f = [55.0, 73.4, 61.7][(k // 3) % 3]
            seg = 0.9 * np.exp(-d * 6) * np.sin(2 * np.pi * f * d)
        else:                                                           # pa: kurzer Akkord in der Mitte
            seg = 0.35 * np.exp(-d * 18) * (np.sin(2 * np.pi * 262 * d) + np.sin(2 * np.pi * 330 * d)
                                              + np.sin(2 * np.pi * 392 * d)) / 3
        out[i:i + len(seg)] += seg
        k += 1
        beat += p
    return np.tanh(out * 1.3) * 0.6
