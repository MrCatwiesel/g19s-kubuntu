"""Stil „Männertag“ (Bollerwagentour) und Festkalender Christi Himmelfahrt."""
import datetime as dt
import time
from common import g, eq, ok, done

eq(g.VISUAL_STYLES["father"], "Männertag", "Name des Stils")
eq(g.fest_occasion({}, dt.date(2027, 5, 6)), ("father", "maenner:2027-05-06"), "Festkalender: Himmelfahrt 2027")
eq(g.fest_occasion({}, dt.date(2026, 5, 14)), ("father", "maenner:2026-05-14"), "Festkalender: Himmelfahrt 2026")
eq(g.fest_occasion({"fest_auto": False}, dt.date(2026, 5, 14)), None, "Festtage abschaltbar")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]
O = g.visual_options(r.settings, "father")


def frame(**kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=1.0)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["father"](r, s, O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["father"]


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
ok(st["k"] > 5, "Takt wird gezählt")
ok(st["flip"] > 5000, "Würstchen hüpfen auf den Bass")
b = list(st["brown"])
st["gag"], st["next_gag"] = None, 1e9
st = run(4.0)
ok(all(x2 >= x1 for x1, x2 in zip(b, st["brown"])), "Würstchen werden brauner")
st["boom"] = 5000 + T[0]
st = run(4.2)
for name, dur in g.FA_GAGS.items():
    st["gag"] = (name, 5000 + T[0])
    st = run(dur + 0.2)
    ok(st["gag"] is None, f"Gag „{name}“ endet")
st = run(2.0, talk=True, talk_t=5000 + T[0])
ok(r.vis_ember is not None and r.vis_ember[0] == 255, "Grillglut für die Tastatur")
ok("gag:ballett" in dict(g.vis_scenes("father")), "Vorschau: Gags wählbar")
done()
