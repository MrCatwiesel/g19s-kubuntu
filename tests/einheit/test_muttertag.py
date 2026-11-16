"""Stil „Muttertag“ (Multitasking) und Festkalender 2. Sonntag im Mai."""
import datetime as dt
import time
from common import g, eq, ok, done

eq(g.VISUAL_STYLES["mother"], "Muttertag", "Name des Stils")
eq(g.fest_occasion({}, dt.date(2027, 5, 9)), ("mother", "mutter:2027-05-09"), "Festkalender: Muttertag 2027")
eq(g.fest_occasion({}, dt.date(2026, 5, 10)), ("mother", "mutter:2026-05-10"), "Festkalender: Muttertag 2026")
eq(g.fest_occasion({}, dt.date(2026, 5, 3)), None, "1. Sonntag im Mai: nichts")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]
O = g.visual_options(r.settings, "mother")


def frame(o=O, amp=1.0, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=amp)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["mother"](r, s, o, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["mother"]


def run(seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        st = frame(**kw)
    return st


r._vis_states = {}
t0 = time.perf_counter()
st = run(6.0)
ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
ok(ms < 9, f"Zeichenzeit je Bild {ms:.2f} ms")
st["gag"], st["next_gag"] = None, 1e9
st = run(3.0, amp=1.0)
loud = st["extra"]
st = run(4.0, amp=0.15)
ok(loud > st["extra"] + 0.3, f"Laut mehr Arme als leise ({loud:.2f} > {st['extra']:.2f})")
st = run(3.0, o=dict(O, arms=False))
ok(st["extra"] < 0.1, "Ohne Multitasking-Option bleibt es bei zwei Armen")
n = st["stack"]
st = run(4.0)
ok(st["stack"] != n, "Pfannkuchen landen auf dem Stapel")
st["boom"] = 5000 + T[0]
st = run(2.0)
ok(st["extra"] > 1.5, "Höhepunkt: alle sechs Arme")
st = run(2.2)
for name, dur in g.MO_GAGS.items():
    st["gag"] = (name, 5000 + T[0])
    st = run(dur + 0.2)
    ok(st["gag"] is None, f"Gag „{name}“ endet")
st = run(2.0, talk=True, talk_t=5000 + T[0])
ok(r.vis_rose is not None, "Tastaturfarbe gesetzt")
ok("gag:waschmaschine" in dict(g.vis_scenes("mother")), "Vorschau: Gags wählbar")
done()
