"""Stil „Halloween“ (Skelettband, Kürbischor) und Festkalender 25.10.–1.11."""
import datetime as dt
import time
from common import g, eq, ok, done

eq(g.VISUAL_STYLES["halloween"], "Halloween", "Name des Stils")
eq(g.fest_occasion({}, dt.date(2026, 10, 31)), ("halloween", "halloween:2026"), "Festkalender zeigt Halloween")
eq(g.fest_occasion({}, dt.date(2026, 10, 24)), None, "24.10.: noch nicht")
eq(g.fest_occasion({"fest_auto": False}, dt.date(2026, 10, 31)), None, "Festtage abschaltbar")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
r._party_wx = (time.monotonic() + 1e9, (None, None, None))
FPS = 15
T = [0.0]
O = g.visual_options(r.settings, "halloween")


def frame(**kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=1.0)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["halloween"](r, s, O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["halloween"]


def run(seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        st = frame(**kw)
    return st


r._vis_states = {}
t0 = time.perf_counter()
st = run(9.0)
ms = (time.perf_counter() - t0) / (9 * FPS) * 1000
ok(ms < 9, f"Zeichenzeit je Bild {ms:.2f} ms")
ok(r.vis_glow and r.vis_glow[0] == 255, "Kürbisleuchten für die Tastatur")
st["boom"] = 5000 + T[0]
st = run(1.0)
ok(st["vec"], "Höhepunkt: Skelette fallen auseinander")
st = run(3.2)
st["boom"] = -99.0
for name in g.HW_GAGS:
    st["gag"] = (name, 5000 + T[0])
    st = run(g.HW_GAGS[name] + 0.2)
    ok(st["gag"] is None, f"Gag „{name}“ endet")
st["next_gag"] = 1e9
img = None
s = g.demo_snapshot(5000 + T[0], amp=1.0)
s.update(active=True, demo=False, talk=True, talk_t=5000 + T[0] - 2, t=5000 + T[0])
img = g.VISUAL_RENDERERS["halloween"](r, s, O, (0, 255, 90))
eq(img.size, (g.WIDTH, g.HEIGHT), "Wortbeitrag: Bild mit Gespenst")
O2 = dict(O, spooky=False)
st["gag"], st["order"], st["next_gag"] = None, ["fenster"], 0
s = g.demo_snapshot(5000 + T[0], amp=1.0)
s.update(active=True, demo=False, t=5000 + T[0])
g.VISUAL_RENDERERS["halloween"](r, s, O2, (0, 255, 90))
ok(st["gag"] is None or st["gag"][0] != "fenster", "Ohne Gänsehaut kein Fenster-Gag")
ok("gag:fenster" in dict(g.vis_scenes("halloween")), "Vorschau: Gags wählbar")
done()
