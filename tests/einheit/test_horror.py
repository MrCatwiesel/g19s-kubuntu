"""Stil „Horror“: Haus am Ende der Straße und Puppenzimmer, Wechsel bei Liedwechsel."""
import time
from common import g, eq, ok, done

eq(g.VISUAL_STYLES["horror"], "Horror", "Name des Stils")
r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def frame(o, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=1.0)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["horror"](r, s, o, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["horror"]


def run(o, seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        st = frame(o, **kw)
    return st


O = g.visual_options(r.settings, "horror")
eq(O["place"], "switch", "Standard: Schauplätze wechseln")
r._vis_states = {}
r._vis_song = "Lied A"
t0 = time.perf_counter()
st = run(O, 4.0)
ms = (time.perf_counter() - t0) / (4 * FPS) * 1000
ok(ms < 9, f"Haus: Zeichenzeit je Bild {ms:.2f} ms")
eq(st["place"], "house", "Beginnt am Haus")
r._vis_song = "Lied B"
st = run(O, 1.0)
eq(st["place"], "dolls", "Liedwechsel → Puppenzimmer")
t0 = time.perf_counter()
st = run(O, 4.0)
ms = (time.perf_counter() - t0) / (4 * FPS) * 1000
ok(ms < 9, f"Puppenzimmer: Zeichenzeit je Bild {ms:.2f} ms")
st["since"] -= g.HR_SWITCH + 1
st = run(O, 0.2)
eq(st["place"], "house", "Ohne Liedwechsel nach 4 Minuten zurück zum Haus")
for place in ("house", "dolls"):
    o = dict(O, place=place)
    st = run(o, 0.2)
    eq(st["place"], place, f"Fester Schauplatz {place}")
    st["boom"] = 5000 + T[0]
    st = run(o, g.HR_BOOM + 0.2)
    for name, dur in g.HR_GAGS[place].items():
        st["gag"] = (name, 5000 + T[0])
        st = run(o, dur + 0.2)
        ok(st["gag"] is None, f"Gag „{name}“ endet")
    st = run(o, 2.0, talk=True, talk_t=5000 + T[0])
    ok(r.vis_horror is not None, f"{place}: Tastaturfarbe gesetzt")
o = dict(O, place="dolls", spooky=False)
st = run(o, 0.2)
st["gag"], st["order"], st["next_gag"] = None, [], 0
picked = set()
for _ in range(12):
    st = run(o, 0.2)
    if st["gag"]:
        picked.add(st["gag"][0])
        st["gag"], st["next_gag"] = None, 0
ok(picked and not picked & g.HR_SPOOKY, f"Ohne Gänsehaut nur harmlose Gags ({sorted(picked)})")
sc = dict(g.vis_scenes("horror"))
ok("gag:hund" in sc and "gag:licht" in sc, "Vorschau: Gags beider Schauplätze")
done()
