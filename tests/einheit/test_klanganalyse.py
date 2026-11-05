"""Klanganalyse der Visualisierung: Frequenzbänder, Pegel links/rechts, Takt, Stille, Einstellungen."""
import math
import numpy as np
from common import g, eq, ok, done

RATE, BLOCK = g.AUDIO_RATE, g.SoundAnalyzer.BLOCK
a = g.SoundAnalyzer(lambda: {}, log=lambda m: None)


def blocks(seconds, fn):
    """Stereo-Blöcke wie von pw-record (L, R abwechselnd) aus fn(t) -> (l, r)."""
    n = 0
    while n < seconds * RATE:
        t = (np.arange(n, n + BLOCK)) / RATE
        l, r = fn(t)
        out = np.empty(BLOCK * 2, np.float32)
        out[0::2], out[1::2] = l, r
        yield out, n / RATE
        n += BLOCK


# 1 kHz nur links: stärkstes Band bei 1 kHz, linker Pegel deutlich höher
for samples, t in blocks(1.0, lambda t: (0.5 * np.sin(2 * np.pi * 1000 * t), 0.02 * np.sin(2 * np.pi * 1000 * t))):
    a.feed(samples, t)
s = a.snapshot()
lo, hi = a.edges[int(np.argmax(s["bands"]))]
freq = (lo + hi) / 2 * RATE / g.AUDIO_FFT
ok(800 < freq < 1250, f"stärkstes Band bei 1 kHz (ist {freq:.0f} Hz)")
ok(s["active"] and s["left"] > s["right"] + 0.2, f"Pegel links {s['left']:.2f} > rechts {s['right']:.2f}")
ok(s["bands"][:4].max() < 0.5, "tiefe Bänder bleiben ruhig")

# Bass-Schlag alle 0,5 s: Takt wird erkannt (etwa 2 je Sekunde)
a.reset()
kick = lambda t: (0.8 * np.exp(-(t % 0.5) * 14) * np.sin(2 * np.pi * 55 * t) + 0.05 * np.sin(2 * np.pi * 900 * t),) * 2
for samples, t in blocks(4.0, kick):
    a.feed(samples, t)
s = a.snapshot()
ok(5 <= s["beats"] <= 8, f"Takt erkannt: {s['beats']} Schläge in 4 s (1 s Anlauf)")
ok(s["bass"] > s["treble"], "Bass stärker als Höhen")
ok(abs(s["period"] - 0.5) < 0.03, f"Tempo erkannt: {s['period']:.3f} s je Schlag")

# dichte Musik (Bass klingt durch, Rauschen): Schläge trotzdem erkannt; Dauerton: keine falschen Schläge
rng = np.random.default_rng(1)
dense = lambda t: (0.7 * np.exp(-(t % (60 / 140)) * 14) * np.sin(2 * np.pi * 55 * t) + 0.35 * np.sin(2 * np.pi * 82 * t)
                   + 0.2 * rng.standard_normal(len(t)),) * 2
a.reset()
for samples, t in blocks(8.0, dense):
    a.feed(samples, t + 10)
s = a.snapshot()
ok(s["beats"] >= 14 and abs(s["period"] - 60 / 140) < 0.03, f"dichte Musik 140/min: {s['beats']} Schläge, {s['period']:.3f} s")
a.reset()
for samples, t in blocks(6.0, lambda t: (0.5 * np.sin(2 * np.pi * 82 * t) + 0.1 * rng.standard_normal(len(t)),) * 2):
    a.feed(samples, t + 20)
eq(a.snapshot()["beats"], 0, "Dauerton ohne Schläge")

# Stille: nicht aktiv, Bänder fallen ab
for samples, t in blocks(1.0, lambda t: (t * 0, t * 0)):
    a.feed(samples, t + 30)
s = a.snapshot()
ok(not s["active"] and s["bands"].max() < 0.05, "Stille: inaktiv, Bänder bei null")

# künstliche Werte (Vorschau): gleiche Zeit → gleiche Werte, Form wie echte
d1, d2 = g.demo_snapshot(100.25), g.demo_snapshot(100.25)
ok(np.array_equal(d1["bands"], d2["bands"]) and d1["beats"] == 200, "demo_snapshot ist reproduzierbar")
eq(set(d1) >= set(s), True, "demo_snapshot hat alle Felder der echten Analyse")

# Wortbeiträge: Sprache (auch mit leiser Musik darunter) wird nach einigen Sekunden erkannt, Musik nie
import klang_signale as ks


def talk_seq(parts):
    """Je Sekunde: T = Wortbeitrag, m = Musik."""
    an = g.SoundAnalyzer(lambda: {}, log=lambda m: None)
    x, out = np.concatenate(parts), ""
    for i in range(0, len(x) - BLOCK, BLOCK):
        blk = x[i:i + BLOCK].astype(np.float32)
        st = np.empty(BLOCK * 2, np.float32)
        st[0::2], st[1::2] = blk, blk
        an.feed(st, i / RATE)
        if i % RATE < BLOCK:
            out += "T" if an.talk else "m"
    return out


seq = talk_seq([ks.music(10), ks.speech(20), ks.music(10, seed=4)])
ok(set(seq[:13]) == {"m"} and set(seq[16:30]) == {"T"} and set(seq[34:]) == {"m"},
   f"Musik → Sprache → Musik: {seq} (Wortbeitrag nach ≈ 4–6 s, Musik nach ≈ 3–4 s)")
for name, sig in (("Musik 140/min", ks.music(30, bpm=140, seed=3)), ("Ballade ohne Schlagzeug", ks.music(20, drums=False))):
    eq(set(talk_seq([sig])), {"m"}, f"{name}: nie Wortbeitrag")
brk = ks.music(30)
brk[10 * RATE:int(11.5 * RATE)] = 0
eq(set(talk_seq([brk])), {"m"}, "Musik mit 1,5 s Pause: kein Wortbeitrag")
ok(talk_seq([ks.music(5), ks.speech(20, bed=0.3, seed=9)]).endswith("T" * 10), "Sprache mit Musikbett: Wortbeitrag")
sp = ks.speech(20, seed=4)                   # wie am echten Radio: Moderation mit Bass (Bassanteil ≈ 0,25)
tt = np.arange(len(sp)) / RATE
ok(talk_seq([ks.music(5), sp + 0.12 * np.sin(2 * np.pi * 55 * tt) * (np.abs(sp) > 0.02)]).endswith("T" * 10),
   "Sprache mit Bass (Moderation über Musikbett): Wortbeitrag")

# Stichwörter im Sendertitel
w = {"visual": {"talk_words": "Nachrichten, News, Werbung"}}
eq(g.talk_word(w, {"artist": "Radio Bob", "title": "BOB News um 15 Uhr"}), "News", "Stichwort im Titel erkannt")
eq(g.talk_word(w, {"artist": "Die Band", "title": "Newsletter"}), None, "nur ganze Wörter („Newsletter“ ≠ „News“)")
eq(g.talk_word(w, {"artist": "WERBUNG", "title": ""}), "Werbung", "Groß-/Kleinschreibung egal")
eq(g.talk_word({"visual": {"talk_words": ""}}, {"title": "Nachrichten"}), None, "ohne Stichwörter nie")
eq([g._bored_pose(b) for b in (0, 6, 8, 11, 31)], ["cross", "yawn", "hips", "watch", "sit"], "Haltungen der Langeweile")

# Weihnachtszeit: 1. Advent bis 6. Januar
import datetime as dt
D = dt.date
eq([g.xmas_season(D(2026, 11, 28)), g.xmas_season(D(2026, 11, 29)), g.xmas_season(D(2026, 12, 31)),
    g.xmas_season(D(2027, 1, 6)), g.xmas_season(D(2027, 1, 7))], [None, 2026, 2026, 2026, None],
   "2026: 1. Advent am 29.11., Ende am 6.1.")
eq([g.xmas_season(D(2022, 11, 26)), g.xmas_season(D(2022, 11, 27))], [None, 2022],
   "2022 (Weihnachten an einem Sonntag): 1. Advent am 27.11.")
eq(g.xmas_season(D(2025, 11, 30)), 2025, "2025: 1. Advent am 30.11.")
xp = [g._ik((0, 0), (20, 25), 18, 18, 1)[1], g._ik((0, 0), (100, 0), 18, 18, 1)[1]]
ok(abs(xp[0][0] - 20) < 0.01 and abs(xp[0][1] - 25) < 0.01, "IK: erreichbares Ziel wird getroffen")
ok(abs(math.hypot(*xp[1]) - 35.99) < 0.1, "IK: zu fernes Ziel – Arm gestreckt in Zielrichtung")

# Einstellungen: Standardwerte und ungültige Werte
st = g.clean_settings({"visual": {"style": "gibtsnicht", "eq": {"bars": "999", "mirror": True}}})
eq(st["visual"]["style"], "eq", "unbekannter Stil → Grafik-Equalizer")
eq(st["visual"]["eq"]["bars"], "32", "ungültige Balkenzahl → Standard")
eq(st["visual"]["eq"]["mirror"], True, "gültige Option bleibt")
eq(st["visual"]["backlight"], True, "Tastaturlicht im Takt: Standard an")
eq(g.visual_options(st, "eq")["mirror"], True, "visual_options liest settings.json")
ok(all(s in g.VISUAL_RENDERERS for s in g.VISUAL_STYLES), "jeder Stil hat eine Zeichenfunktion")
ok("visual" in g.PAGE_IDS and len(g.PAGE_IDS) == len(g.PAGE_NAMES), "Seite „Visualisierung“ angemeldet")
done()
