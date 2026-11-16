"""Stil „Ostern“ (Eierfabrik) und Festkalender: Ostern, Himmelfahrt, Muttertag, Halloween."""
import datetime as dt
import time
from common import g, eq, ok, done

D = dt.date
eq(g.easter_sunday(2026), D(2026, 4, 5), "Ostersonntag 2026")
eq(g.easter_sunday(2027), D(2027, 3, 28), "Ostersonntag 2027")
eq(g.easter_sunday(2030), D(2030, 4, 21), "Ostersonntag 2030")
eq(g.fest_days(D(2027, 3, 25)), [("easter", "ostern:2027")], "Gründonnerstag: Ostern")
eq(g.fest_days(D(2027, 3, 29)), [("easter", "ostern:2027")], "Ostermontag: Ostern")
eq(g.fest_days(D(2027, 3, 24)), [], "Mittwoch davor: nichts")
eq(g.fest_days(D(2027, 5, 6)), [("father", "maenner:2027-05-06")], "Himmelfahrt 2027: Männertag")
eq(g.fest_days(D(2027, 5, 9)), [("mother", "mutter:2027-05-09")], "Muttertag 2027 (2. Sonntag im Mai)")
eq(g.fest_days(D(2027, 5, 2)), [], "1. Sonntag im Mai: nichts")
eq(g.fest_days(D(2026, 10, 31)), [("halloween", "halloween:2026")], "Halloween")
eq(g.fest_days(D(2026, 11, 1))[0][0], "halloween", "1.11. noch Halloween")
eq(g.fest_occasion({}, D(2027, 3, 28)), ("easter", "ostern:2027"), "Festkalender zeigt Ostern")
eq(g.fest_occasion({"fest_auto": False}, D(2027, 3, 28)), None, "Festtage abschaltbar")
ok(g.fest_occasion({}, D(2026, 10, 31)) in (None, ("halloween", "halloween:2026")),
   "Halloween nur, wenn der Stil schon gebaut ist")
eq(g.fest_occasion({"party": {"birthdays": [{"name": "A", "day": 28, "month": 3, "year": 0}]}}, D(2027, 3, 28))[0],
   "party", "Geburtstag geht vor Ostern")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
r._party_wx = (time.monotonic() + 1e9, (None, None, None))
FPS = 15
T = [0.0]
O = g.visual_options(r.settings, "easter")


def frame(amp=1.0, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=amp)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["easter"](r, s, O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["easter"]


def run(seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        st = frame(**kw)
    return st


eq(g.VISUAL_STYLES["easter"], "Ostern", "Name des Stils")
r._vis_states = {}
t0 = time.perf_counter()
st = run(9.0)
ms = (time.perf_counter() - t0) / (9 * FPS) * 1000
ok(ms < 8, f"Zeichenzeit je Bild {ms:.2f} ms")
ok(len(st["eggs"]) >= 3, f"Hühner legen Eier aufs Band ({len(st['eggs'])})")
ok(st["paint_i"] >= 2, f"Der Hase bemalt Eier ({st['paint_i']})")
st["gag"], st["next_gag"] = None, 1e9
st = run(12.0)
ok(st["basket"] >= 3, f"Bunte Eier im Korb ({st['basket']})")
st["boom"] = 5000 + T[0]
st = run(3.0)
ok(st["flying"] or st["basket"] > 3, "Höhepunkt: Band rast, Eier fliegen")
st["boom"] = -99.0
for name in g.ES_GAGS:
    st["gag"] = (name, 5000 + T[0])
    st = run(g.ES_GAGS[name] + 0.2)
    ok(st["gag"] is None, f"Gag „{name}“ endet")
n = len(st["eggs"])
st = run(3.0, talk=True, talk_t=5000 + T[0])
ok(len(st["eggs"]) <= n, "Wortbeitrag: Band steht, keine neuen Eier (STREIK)")
ok("gag:schokohasen" in dict(g.vis_scenes("easter")), "Vorschau: Gags wählbar")
done()
