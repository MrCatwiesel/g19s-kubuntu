"""Stile „Silvester“ und „Fasching“, Festkalender für alle neuen Festtage."""
import datetime as dt
import time
from common import g, eq, ok, done

D = dt.date
# Festkalender: Termine (Stile, die noch fehlen, sind vorgemerkt)
eq(g.oktoberfest_days(2026), (D(2026, 9, 19), D(2026, 10, 4)), "Oktoberfest 2026: 19.9.–4.10.")
eq(g.oktoberfest_days(2027), (D(2027, 9, 18), D(2027, 10, 3)), "Oktoberfest 2027: 18.9.–3.10.")
eq(g.fest_days(D(2027, 2, 8)), [("carnival", "fasching:2027")], "Rosenmontag 2027")
eq(g.fest_days(D(2027, 2, 4)), [("carnival", "fasching:2027")], "Weiberfastnacht 2027")
eq(g.fest_days(D(2027, 2, 10)), [], "Aschermittwoch: vorbei")
eq(g.fest_days(D(2027, 2, 14)), [("valentine", "valentin:2027")], "Valentinstag")
eq(g.fest_days(D(2026, 11, 11)), [("martin", "martin:2026")], "St. Martin")
eq(g.fest_days(D(2026, 12, 31)), [("newyear", "silvester:2026")], "Silvester")
eq(g.fest_occasion({}, D(2026, 12, 31)), ("newyear", "silvester:2026"), "Festkalender zeigt Silvester")
eq(g.fest_occasion({}, D(2027, 2, 8)), ("carnival", "fasching:2027"), "Festkalender zeigt Fasching")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def frame(style, o, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=1.0)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    img = g.VISUAL_RENDERERS[style](r, s, o, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states[style], img


def run(style, o, seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        st, _ = frame(style, o, **kw)
    return st


states = {}
for style, gags in (("newyear", g.NY_GAGS), ("carnival", g.CV_GAGS)):
    o = g.visual_options(r.settings, style)
    r._vis_states = {}
    t0 = time.perf_counter()
    st = run(style, o, 6.0)
    ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
    ok(ms < 10, f"{style}: Zeichenzeit je Bild {ms:.2f} ms")
    st["gag"], st["next_gag"] = None, 1e9
    st["boom"] = 5000 + T[0]
    st = run(style, o, 6.4)
    for name, dur in gags.items():
        st["gag"] = (name, 5000 + T[0])
        st = run(style, o, dur + 0.2)
        ok(st["gag"] is None, f"{style}: Gag „{name}“ endet")
    states[style] = run(style, o, 2.0, talk=True, talk_t=5000 + T[0])
    ok(f"gag:{next(iter(gags))}" in dict(g.vis_scenes(style)), f"{style}: Gags in der Vorschau")

st = states["newyear"]
ok(len(st["parts"]) > 0 or st["rockets"], "Silvester: Feuerwerk läuft")
# Countdown an der Tafel
o = g.visual_options(r.settings, "newyear")
g.fest_today = lambda: D(2026, 12, 31)
g.fest_now = lambda: dt.datetime(2026, 12, 31, 23, 59, 55)
d = g.ImageDraw.Draw(g.Image.new("RGB", (g.WIDTH, g.HEIGHT)))
big, ny = r._ny_board(d, 0, {}, {})
eq((big, ny), ("5", False), "Die letzten Sekunden groß")
g.fest_today = lambda: D(2027, 1, 1)
g.fest_now = lambda: dt.datetime(2027, 1, 1, 0, 3, 0)
big, ny = r._ny_board(d, 0, {}, {})
ok(big is None and ny, "Nach Mitternacht: Frohes neues Jahr")
eq(g._ny_year(D(2026, 11, 16)), 2027, "Im November zählt die Tafel auf 2027")
done()
