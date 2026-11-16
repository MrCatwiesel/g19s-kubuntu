"""Stile „Oktoberfest“, „St. Martin“ und „Valentinstag“ samt Festkalender."""
import datetime as dt
import time
from common import g, eq, ok, done

D = dt.date
eq(g.fest_occasion({}, D(2026, 9, 26)), ("oktoberfest", "wiesn:2026"), "Festkalender: Oktoberfest")
eq(g.fest_occasion({}, D(2026, 11, 11)), ("martin", "martin:2026"), "Festkalender: St. Martin")
eq(g.fest_occasion({}, D(2027, 2, 14)), ("valentine", "valentin:2027"), "Festkalender: Valentinstag")
eq(g.fest_occasion({}, D(2026, 2, 14))[0], "carnival", "Valentinstag am Faschingssamstag 2026: Fasching geht vor")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def run(style, o, seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        t = 5000 + T[0]
        s = g.demo_snapshot(t, amp=1.0)
        s.update(active=True, demo=False, t=t)
        s.update(kw)
        g.VISUAL_RENDERERS[style](r, s, o, (0, 255, 90))
        T[0] += 1 / FPS
        st = r._vis_states[style]
    return st


for style, gags, attr in (("oktoberfest", g.OK_GAGS, "vis_rauten"), ("martin", g.SM_GAGS, "vis_lantern"),
                          ("valentine", g.VL_GAGS, "vis_heart")):
    o = g.visual_options(r.settings, style)
    r._vis_states = {}
    t0 = time.perf_counter()
    st = run(style, o, 6.0)
    ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
    ok(ms < 10, f"{style}: Zeichenzeit je Bild {ms:.2f} ms")
    ok(getattr(r, attr) is not None, f"{style}: Tastaturfarbe gesetzt")
    st["gag"], st["next_gag"] = None, 1e9
    st["boom"] = 5000 + T[0]
    st = run(style, o, 4.4)
    for name, dur in gags.items():
        st["gag"] = (name, 5000 + T[0])
        st = run(style, o, dur + 0.2)
        ok(st["gag"] is None, f"{style}: Gag „{name}“ endet")
    run(style, o, 3.0, talk=True, talk_t=5000 + T[0])
    ok(f"gag:{next(iter(gags))}" in dict(g.vis_scenes(style)), f"{style}: Gags in der Vorschau")
o = dict(g.visual_options(r.settings, "valentine"), cupid=False)
st = run("valentine", o, 4.0)
ok(st["arrow"] is None, "Valentinstag: ohne Amor keine Pfeile")
done()
