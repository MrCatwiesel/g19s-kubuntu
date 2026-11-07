"""Lichteffekte (Tänzerin und Lichtshow): Programme und eigene Auswahl, Silhouette bei ruhigen Stellen, Blinder beim
Höhepunkt, Bühnenfarbe und „Zuhören“ für die Tastatur, Zeichenzeit."""
import time
import numpy as np
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
BD = g.visual_options(r.settings, "dancer")
BL = g.visual_options(r.settings, "lights")
FPS = 15


def run(style, opts, seconds, amp=lambda i: 1.0):
    r._vis_states = {}
    img, tm = None, []
    for i in range(int(seconds * FPS)):
        t = 5000 + i / FPS
        s = g.demo_snapshot(t, amp=amp(i / FPS))
        s.update(active=True, demo=False, t=t)
        t0 = time.perf_counter()
        img = g.VISUAL_RENDERERS[style](r, s, dict(BD if style == "dancer" else BL, **opts), (0, 255, 90))
        tm.append(time.perf_counter() - t0)
    return np.asarray(img).astype(int), sum(tm) / len(tm) * 1000


eq(g.fx_set({"show": "off"}), set(), "Studio: keine Effekte")
eq(g.fx_set({"show": "night"}), {"heads", "laser", "haze", "uv", "chase", "ball"}, "Clubnacht")
eq(g.fx_set({"show": "custom", "fx_laser": True, "fx_follow": True}), {"laser", "follow"}, "Eigene Auswahl")
eq((BD["show"], BD["keys"], BL["fx"]), ("off", "bass", "classic"), "Standard: Studio, Tastatur pulsiert, Lichtshow klassisch")
studio, _ = run("dancer", {}, 2)
for prog in ("ballet", "night", "gala"):
    img, ms = run("dancer", {"show": prog}, 2)
    ok(np.abs(img - studio).mean() > 8 and ms < 15, f"Programm {prog}: sichtbar anders, {ms:.1f} ms je Bild")
for k in g.FX_ALL:
    img, ms = run("dancer", {"show": "custom", "fx_" + k: True}, 1.5)
    ok(np.abs(img - studio).mean() > 0.5, f"Eigene Auswahl {k}: wirkt ({ms:.1f} ms)")
classic, _ = run("lights", {}, 2)
for fx in ("heads", "laser", "show"):
    img, ms = run("lights", {"fx": fx}, 2)
    ok(np.abs(img - classic).mean() > 3 and ms < 15, f"Lichtshow + {fx}: sichtbar anders, {ms:.1f} ms")

# Silhouette: bei ruhiger Musik fast schwarz vor farbigem Hintergrund
run("dancer", {"show": "ballet"}, 8, amp=lambda t: 0.3)
ok(r._vis_states["dancer"]["fx"]["sil"] > 0.8, "Ruhige Stelle: Silhouette im Gegenlicht")
run("dancer", {"show": "ballet"}, 4)
ok(r._vis_states["dancer"]["fx"]["sil"] < 0.2, "Laute Musik: wieder voll beleuchtet")

# Blinder beim Höhepunkt
quiet_end, _ = run("dancer", {"show": "gala"}, 10.0, amp=lambda t: 0.6)
boom, _ = run("dancer", {"show": "gala"}, 11.0, amp=lambda t: 0.6 if t < 10 else 1.0)
ok(r._vis_states["dancer"]["fx"]["surge"] > 0.5 and boom[:g.VIS_H].mean() > quiet_end[:g.VIS_H].mean() + 5,
   "Höhepunkt: Blinder hellen kurz auf")

# Tastatur: Bühnenfarbe, Zuhören
run("dancer", {"show": "night"}, 1)
ok(r.vis_stage_color is not None, "Bühnenfarbe für die Tastatur gesetzt")
run("dancer", {}, 1)
ok(r.vis_stage_color is None, "Studio: keine Bühnenfarbe")
r._vis_states = {}
for i in range(FPS * 2):
    t = 5000 + i / FPS + (3.0 if i == FPS else 0)
    s = g.demo_snapshot(t)
    s.update(active=True, demo=False, t=t)
    g.VISUAL_RENDERERS["dancer"](r, s, BD, (0, 255, 90))
    if i == FPS:
        ok(r.vis_listen, "Nach einer Pause hört sie zu: Tastatur atmet")
eq(sum(1 for o in g.VISUAL_OPTIONS["dancer"] if o["key"].startswith("fx_")), len(g.FX_ALL), "Jeder Effekt einzeln wählbar")
done()
