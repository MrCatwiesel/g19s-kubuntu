"""Lounge / Jazz-Club: Zeichenzeit, Höhepunkt, Gags, Wortbeitrag, alle Bühnen, Clublichter und Tastaturfarben."""
import time
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def run(o, seconds, **kw):
    for _ in range(int(round(seconds * FPS))):
        t = 5000 + T[0]
        s = g.demo_snapshot(t, amp=1.0)
        s.update(active=True, demo=False, t=t)
        s.update(kw)
        img = g.VISUAL_RENDERERS["jazz"](r, s, o, (0, 255, 90))
        T[0] += 1 / FPS
    return r._vis_states["jazz"], img


ok("jazz" in g.VISUAL_STYLES and "jazz" in g.VISUAL_OPTIONS, "Jazz-Club: in Stilliste und Optionen")
o = g.visual_options(r.settings, "jazz")
r._vis_states = {}
t0 = time.perf_counter()
st, img = run(o, 6.0)
ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
ok(ms < 10, f"Jazz-Club: Zeichenzeit je Bild {ms:.2f} ms")
eq(img.size, (g.WIDTH, g.HEIGHT), "Jazz-Club: Bildgröße")
st["gag"], st["next_gag"] = None, 1e9
st["boom"] = 5000 + T[0]
st, _ = run(o, 5.4)
ok(not (0 <= 5000 + T[0] - st["boom"] < g.JZ_BOOM), "Jazz-Club: Höhepunkt endet")
for name, dur in g.JZ_GAGS.items():
    st["gag"] = (name, 5000 + T[0])
    st, _ = run(o, dur + 0.2)
    ok(st["gag"] is None, f"Jazz-Club: Gag „{name}“ endet")
run(o, 2.0, talk=True, talk_t=5000 + T[0])

# alle Bühnen, Clublichter, Rauchstufen
for soloist in ("sax", "singer", "bass"):
    for mood in ("red", "amber", "blue", "emerald"):
        r._vis_states = {}
        _, img = run(dict(o, soloist=soloist, mood=mood, smoke="light"), 0.4)
        eq(img.size, (g.WIDTH, g.HEIGHT), f"Jazz-Club: {soloist}/{mood}")
r._vis_states = {}
run(dict(o, smoke="off", gags=False), 0.4)
ok(True, "Jazz-Club: ohne Rauch und Gags")

# Tastatur: Club-Licht folgt dem Bass, Bläser-Gold den Mitten/Höhen
for keys in ("mood", "brass"):
    r._vis_states = {}
    run(dict(o, keys=keys), 1.0, bass=1.0, mid=1.0, treble=1.0)
    hi = r.vis_col_jazz
    run(dict(o, keys=keys), 1.0, bass=0.0, mid=0.0, treble=0.0)
    lo = r.vis_col_jazz
    ok(isinstance(hi, tuple) and len(hi) == 3 and all(0 <= c <= 255 for c in hi + lo), f"Jazz-Club/{keys}: Farben gültig")
    ok(hi != lo, f"Jazz-Club/{keys}: Tastatur reagiert auf die Musik ({lo} → {hi})")

# ungültige Messwerte
r._vis_states = {}
run(o, 0.3, bass=float("nan"), mid=float("nan"), treble=float("nan"), level=float("nan"))
st, _ = run(o, 0.3)
ok(st["bass"] == st["bass"] and st["mid"] == st["mid"], "Jazz-Club: nach NaN-Werten wieder gültig")
ok([sc for sc, _ in g.vis_scenes("jazz") if sc.startswith("gag:")], "Jazz-Club: Gags in der Vorschau")
done()
