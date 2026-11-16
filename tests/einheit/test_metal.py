"""Stil „Mittelalter-Metal“: Feuer im Takt, Pyro beim Höhepunkt (Drache/Flammensäulen/aus), Gags der Reihe nach,
Herold bei Wortbeiträgen, Blitz in den Helm bei Gewitter, Hofnarr nach Liedwechsel."""
import time
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
r._party_wx = (time.monotonic() + 1e9, (None, None, None))
FPS = 15
T = [0.0]


def opts(**kw):
    r.settings["visual"]["metal"].update(kw)
    return g.visual_options(r.settings, "metal")


O = opts()


def frame(amp=1.0, o=None, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=amp)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    img = g.VISUAL_RENDERERS["metal"](r, s, o or O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["metal"], img


def run(seconds, **kw):
    st = img = None
    for _ in range(int(round(seconds * FPS))):
        st, img = frame(**kw)
    return st, img


eq(g.VISUAL_STYLES["metal"], "Mittelalter-Metal", "Name des Stils")
eq(O, {"pyro": "dragon", "crowd": True, "gags": True, "keys": "fire"}, "Standardoptionen")
r._vis_states = {}
t0 = time.perf_counter()
fires = []
for _ in range(FPS * 6):
    st, _ = frame()
    fires.append(r.vis_fire)
ms = (time.perf_counter() - t0) / (FPS * 6) * 1000
ok(ms < 8, f"Zeichenzeit je Bild {ms:.2f} ms")
ok(max(fires) - min(fires) > 0.3, f"Feuer lodert mit dem Bass ({min(fires):.2f}–{max(fires):.2f})")
st, _ = run(6.0, amp=0.5)
st["boom"] = -99.0
st, _ = run(1.5, amp=1.6)
ok(st["boom"] > 0, "Lauter: Höhepunkt mit Pyro")
eq(r.vis_fire, 1.0, "Feuer voll (Tastatur)")
st, _ = run(4.0)
b = st["boom"]
st, _ = run(5.0)
eq(st["boom"], b, "Sperre: nicht gleich wieder")
r._vis_states = {}
st, _ = frame()
seen = []
for _ in range(len(g.MT_GAGS)):
    st["next_gag"] = 5000 + T[0]
    st, _ = frame()
    seen.append(st["gag"][0])
    st["boom"] = 1e9                                                 # kein Pyro dazwischen
    st, _ = run(g.MT_GAGS[seen[-1]] + 0.2)
    ok(st["gag"] is None, f"Gag „{seen[-1]}“ endet")
    st["boom"] = -99.0
eq(sorted(seen), sorted(g.MT_GAGS), "Jeder Gag einmal je Durchgang")
r._vis_states = {}
st, _ = run(20.0, o=opts(gags=False))
eq(st["gag"], None, "Gags abschaltbar")
O = opts(gags=True)
st, img = run(3.0, talk=True, talk_t=5000 + T[0])
ok(img is not None and st["gag"] is None, "Wortbeitrag: Herold, keine Gags")
r._vis_song = "Ritter – Lied 1"
frame()
r._vis_song = "Ritter – Lied 2"
st, _ = frame()
ok(5000 + T[0] - st["jester"] < 1, "Liedwechsel: Hofnarr mit „Zugabe!“")
r._party_wx = (time.monotonic() + 1e9, ("thunder", 12.0, 10.0))
st, _ = run(8.0)
ok(st["bolt"] > 0, "Gewitter: Blitz in den Helm")
b = st["bolt"]
st, _ = run(10.0)
eq(st["bolt"], b, "… höchstens alle 15 s")
r._vis_states = {}
for k in range(30):
    g.VISUAL_RENDERERS["metal"](r, g.demo_snapshot(100.0 + k / 15), O, (0, 255, 90))
st = r._vis_states["metal"]
ok(st["gag"] is None and st["boom"] < 0, "Vorschau: Band spielt, ohne Gags und Pyro")
done()
