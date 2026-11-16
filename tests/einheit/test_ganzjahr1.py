"""Ganzjährige Stile: Unterwasser-Band, Bauernhof-Band, Weltraum-Disco, Retro-Arcade."""
import time
from common import g, eq, ok, done

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


for style, gags, attr in (("underwater", g.UW_GAGS, "vis_sea"), ("farm", g.FM_GAGS, "vis_col_farm"),
                          ("space", g.SP_GAGS, "vis_col_space"), ("arcade", g.AR_GAGS, "vis_col_arcade")):
    o = g.visual_options(r.settings, style)
    r._vis_states = {}
    t0 = time.perf_counter()
    st = run(style, o, 6.0)
    ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
    ok(ms < 10, f"{style}: Zeichenzeit je Bild {ms:.2f} ms")
    ok(getattr(r, attr) is not None, f"{style}: Tastaturfarbe gesetzt")
    st["gag"], st["next_gag"] = None, 1e9
    st["boom"] = 5000 + T[0]
    st = run(style, o, 5.4)
    for name, dur in gags.items():
        st["gag"] = (name, 5000 + T[0])
        st = run(style, o, dur + 0.2)
        ok(st["gag"] is None, f"{style}: Gag „{name}“ endet")
    run(style, o, 2.0, talk=True, talk_t=5000 + T[0])
    ok(f"gag:{next(iter(gags))}" in dict(g.vis_scenes(style)), f"{style}: Gags in der Vorschau")

st = r._vis_states["arcade"]
ok(st["score"] > 0, f"Arcade: Treffer zählen ({st['score']})")
# Pillow aus Kubuntu: resize(…, NEAREST) meldete gelegentlich „SystemError … returned NULL“ – Arcade braucht kein resize
o = g.visual_options(r.settings, "arcade")
real_resize = g.Image.Image.resize
def broken_resize(*a, **k):
    raise SystemError("<method 'resize' of 'ImagingCore' objects> returned NULL without setting an exception")
g.Image.Image.resize = broken_resize
try:
    for scan in (True, False):
        r._vis_states = {}
        run("arcade", dict(o, scanlines=scan), 0.5)
    ok(True, "Arcade: zeichnet ohne Image.resize (mit und ohne Röhren-Zeilen)")
except SystemError as ex:
    ok(False, f"Arcade: braucht noch Image.resize ({ex})")
finally:
    g.Image.Image.resize = real_resize
# kaputte Messwerte (NaN) dürfen das Raumschiff nicht dauerhaft zerstören
r._vis_states = {}
run("arcade", o, 0.3, bands=[float("nan")] * 16)
st = run("arcade", o, 0.3)
ok(st["ship"] == st["ship"], f"Arcade: Raumschiff nach ungültigen Messwerten weiter gültig ({st['ship']:.1f})")
o = dict(g.visual_options(r.settings, "underwater"), spooky=False)
r._vis_states = {}
st = run("underwater", o, 0.2)
picked = set()
for _ in range(10):
    st["gag"], st["next_gag"] = None, 0
    st = run("underwater", o, 0.2)
    if st["gag"]:
        picked.add(st["gag"][0])
ok(picked and "hai" not in picked, f"Unterwasser ohne Gänsehaut: kein Hai ({sorted(picked)})")
done()
