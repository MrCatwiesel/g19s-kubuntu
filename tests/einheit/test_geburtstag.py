"""Stil „Geburtstag“ (lebende Torte) und Festkalender: Torte statt Party an Geburtstagen."""
import datetime as dt
import time
from common import g, eq, ok, done

D = dt.date(2027, 6, 3)
LIST = [{"name": "Anna", "day": 3, "month": 6, "year": 1985}]
eq(g.VISUAL_STYLES["birthday"], "Geburtstag", "Name des Stils")
eq(g.fest_occasion({"party": {"birthdays": LIST}}, D)[0], "party", "Ab Werk: Überraschungsparty")
eq(g.fest_occasion({"party": {"birthdays": LIST}, "birthday": {"auto": True}}, D),
   ("birthday", "geb:2027-06-03"), "Schalter an: lebende Torte")
eq(g.fest_occasion({"party": {"birthdays": LIST, "auto": False}, "birthday": {"auto": True}}, D), None,
   "Party-Automatik aus: gar nichts")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]
O = g.visual_options(r.settings, "birthday")
eq(O["auto"], False, "Ab Werk nicht automatisch")


def frame(**kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=1.0)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["birthday"](r, s, O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["birthday"]


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
ok(r.vis_candle is not None, "Kerzenschein für die Tastatur")
st["gag"], st["next_gag"] = None, 1e9
st["boom"] = 5000 + T[0]
st = run(1.0)
ok(len(st["conf"]) > 20, f"Höhepunkt: Konfetti ({len(st['conf'])})")
st = run(3.2)
for name, dur in g.BD_GAGS.items():
    st["gag"] = (name, 5000 + T[0])
    st = run(dur + 0.2)
    ok(st["gag"] is None, f"Gag „{name}“ endet")
eq(round(float(g.np.interp(g.BD_AGE_ADULT, *g.BD_YEARS))), 35, "Zeitraffer: erwachsen = 35 Jahre")
st = run(2.0, talk=True, talk_t=5000 + T[0])
ok(st["gag"] is None, "Wortbeitrag: keine Gags")
ok("gag:zeitraffer" in dict(g.vis_scenes("birthday")), "Vorschau: Gags wählbar")
done()
