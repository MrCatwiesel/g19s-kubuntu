"""Western-Saloon, Lagerfeuer, Katzenchor – und „Gag zeigen“ in der Vorschau für alle Stile mit Gags."""
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


for style, gags, attr in (("western", g.WS_GAGS, "vis_col_western"), ("campfire", {}, "vis_fire"),
                          ("cats", g.KC_GAGS, "vis_col_cats")):
    o = g.visual_options(r.settings, style)
    r._vis_states = {}
    t0 = time.perf_counter()
    st = run(style, o, 6.0)
    ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
    ok(ms < 10, f"{style}: Zeichenzeit je Bild {ms:.2f} ms")
    ok(getattr(r, attr) is not None, f"{style}: Tastaturfarbe gesetzt")
    st["boom"] = 5000 + T[0]
    st = run(style, o, 5.4)
    if gags:
        st["gag"], st["next_gag"] = None, 1e9
        for name, dur in gags.items():
            st["gag"] = (name, 5000 + T[0])
            st = run(style, o, dur + 0.2)
            ok(st["gag"] is None, f"{style}: Gag „{name}“ endet")
    run(style, o, 2.0, talk=True, talk_t=5000 + T[0])
ok(not [sc for sc, _ in g.vis_scenes("campfire") if sc.startswith("gag:")], "Lagerfeuer: keine Gags")
o = g.visual_options(r.settings, "campfire")
r._vis_states = {}
run("campfire", o, 3.0)
loud = r._vis_states["campfire"]["flame"]
run("campfire", o, 3.0, talk=True, talk_t=5000 + T[0])
ok(r._vis_states["campfire"]["flame"] < loud, "Lagerfeuer: bei Wortbeiträgen wird das Feuer ruhig")

# „Gag zeigen“: vis_force muss für jeden Stil mit Gags den Gag setzen
for style in g.VISUAL_STYLES:
    gags = [sc for sc, _ in g.vis_scenes(style) if sc.startswith("gag:")]
    if not gags or style in ("party", "xmas"):
        continue
    o = g.visual_options(r.settings, style)
    r._vis_states = {}
    run(style, o, 0.4)
    name = gags[0].split(":", 1)[1]
    g.vis_force(r, style, gags[0], 5000 + T[0])
    st = r._vis_states[style]
    ok(st.get("gag") and st["gag"][0] == name, f"Vorschau „Gag zeigen“ wirkt bei {style}")

# Tastatur liest Farben vom Renderer: kein Name darf mit einer Zeichenfunktion (vis_<stil>) kollidieren
import re
src = open(g.__file__, encoding="utf-8").read()
fresh = g.Renderer()
for attr in sorted(set(re.findall(r"self\.renderer\.(vis_\w+)", src))):
    ok(not callable(getattr(fresh, attr, None)), f"Tastaturwert {attr} ist keine Funktion")
done()
