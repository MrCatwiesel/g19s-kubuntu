"""Lichtshow mit Stroboskop: Standard aus, Blitze auf kräftige Schläge, Salven bei Höhepunkten, nie mehr als
3 Blitze je Sekunde (auch bei ungültiger Einstellung), Farbe wählbar."""
import numpy as np
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
BASE = g.visual_options(r.settings, "lights")
FPS = 15


def run(seconds, opts, amp=lambda t: 1.0, t0=0.0):
    """Gibt die Zeiten der Blitzbilder (hell) zurück."""
    r._vis_states = {}
    flashes = []
    n = int(seconds * FPS)
    for i in range(n):
        t = 5000 + t0 + i / FPS
        s = g.demo_snapshot(t, amp=amp(i / FPS))
        s.update(active=True, demo=False, t=t)
        img = g.VISUAL_RENDERERS["lights"](r, s, dict(BASE, **opts), (0, 255, 90))
        if np.asarray(img)[:g.VIS_H].mean() > 150:
            flashes.append(i / FPS)
    return flashes


def min_gap(ts):
    return min((b - a for a, b in zip(ts, ts[1:])), default=99)


eq(BASE["strobe"], "off", "Standard: Stroboskop aus")
eq(run(6, {}), [], "Aus: keine harten Blitze")

f = run(10, {"strobe": "beat", "strobe_rate": "3"})
ok(15 <= len(f) <= 30 and min_gap(f) >= 1 / 3 - 1e-6, f"Auf Schläge: {len(f)} Blitze in 10 s, Abstand ≥ 1/3 s")
f = run(10, {"strobe": "beat", "strobe_rate": "1"})
ok(len(f) <= 10 and min_gap(f) >= 1 - 1e-6, f"Höchstens 1 Blitz je Sekunde ({len(f)})")
f = run(10, {"strobe": "beat", "strobe_rate": "9"})
ok(min_gap(f) >= 1 / 3 - 1e-6, "Ungültige Rate: trotzdem höchstens 3 je Sekunde")

# Salve bei Höhepunkt: 8 s leise, dann laut
loud = lambda t: 0.62 if t < 8 else 1.0
f = run(12, {"strobe": "drop", "strobe_rate": "3"}, amp=loud)
ok(not [x for x in f if x < 8] and len([x for x in f if 8 <= x < 10.2]) >= 4,
   f"Salve erst beim Höhepunkt ({f})")
ok(not [x for x in f if x >= 10.4], "Salve dauert etwa 2 Sekunden")

# Farbe der Ebene
r._vis_states = {}
for i in range(FPS * 3):
    t = 5000 + i / FPS
    s = g.demo_snapshot(t)
    s.update(active=True, demo=False, t=t)
    img = g.VISUAL_RENDERERS["lights"](r, s, dict(BASE, strobe="beat", strobe_color="layer"), (0, 255, 90))
    a = np.asarray(img)[:g.VIS_H].reshape(-1, 3).mean(0)
    if a[1] > 150:
        break
ok(a[1] > 150 and a[0] < 120, f"Farbe der Ebene: grüner Blitz ({a.round()})")
ok(r.vis_strobe_t > 0, "Blitz für die Tastatur gemerkt")
done()
