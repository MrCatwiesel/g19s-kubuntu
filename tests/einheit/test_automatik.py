"""Automatische Stilwahl nach Musik, Albumcover-Farben und echtes Wetter in Draußen-Szenen."""
import time
from common import g, eq, ok, done
from PIL import Image

eq(g.auto_mood(80, 0.6), "calm", "Langsam: ruhig")
eq(g.auto_mood(120, 0.1), "calm", "Sehr leise: ruhig")
eq(g.auto_mood(110, 0.5), "mid", "Mittleres Tempo: mittel")
eq(g.auto_mood(140, 0.7), "wild", "Schnell und laut: wild")
eq(g.auto_mood(140, 0.3), "mid", "Schnell, aber leise: mittel")
eq(g.auto_mood(None, 0.8), "wild", "Ohne Tempo, sehr laut: wild")
eq(g.VISUAL_STYLES["auto"], "Automatisch nach Musik", "Name des Stils")
for mood, pool in g.AUTO_POOLS.items():
    ok(all(x in g.VISUAL_RENDERERS for x in pool), f"Pool {mood}: alle Stile vorhanden")

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def run(seconds, amp=1.0, o=None, style="auto", **kw):
    o = o or g.visual_options(r.settings, style)
    img = None
    for _ in range(int(round(seconds * FPS))):
        t = 5000 + T[0]
        s = g.demo_snapshot(t, amp=amp)
        s.update(active=True, demo=False, t=t)
        s.update(kw)
        img = g.VISUAL_RENDERERS[style](r, s, o, (0, 255, 90))
        T[0] += 1 / FPS
    return img


r._vis_song = "Leises Lied"
run(1.0, amp=0.12)
ok(not r._auto["decided"], "Erste Wahl ist vorläufig (es wird noch zugehört)")
run(6.0, amp=0.12)
ok(r._auto["decided"], "Nach sechs Sekunden steht die Wahl")
eq(r._auto["mood"], "calm", "Leises Lied: ruhige Stimmung")
ok(r.vis_auto_inner in g.AUTO_POOLS["calm"], f"… und ein ruhiger Stil ({r.vis_auto_inner})")
first = r.vis_auto_inner
r._vis_song = "Nächstes Lied"
run(0.2, amp=0.12)
ok(not r._auto.get("decided"), "Liedwechsel: es wird neu zugehört")
run(7.0, amp=0.12)
ok(r._auto["decided"] and r.vis_auto_inner != first, f"Neuer Stil nach dem Liedwechsel ({first} → {r.vis_auto_inner})")
o = dict(g.visual_options(r.settings, "auto"), calm="lights")
r._vis_song = "Drittes Lied"
run(7.0, amp=0.12, o=o)
eq(r.vis_auto_inner, "lights", "Fester Stil für ruhige Musik wird genommen")
t0 = time.perf_counter()
run(3.0, o=o)
ms = (time.perf_counter() - t0) / (3 * FPS) * 1000
ok(ms < 12, f"Automatik: Zeichenzeit je Bild {ms:.2f} ms")
ok("label" in g.visual_options(r.settings, "auto"), "Option: gewählten Stil einblenden")

# Coverfarbe
cov = Image.new("RGB", (100, 100), (20, 20, 20))
cov.paste((30, 60, 200), (10, 10, 90, 90))
c = g.cover_color(cov)
ok(c[2] > 200 and c[0] < 100, f"Coverfarbe: kräftiges Blau ({c})")


class FakeMedia:
    def snapshot(self):
        return {"title": "x"}, cov, None, None


r.media = FakeMedia()
c1 = r._vis_cover_color()
eq(c1, c, "Renderer liest die Coverfarbe")
ok(r._vis_cover_color() is c1, "… und merkt sie sich")
r.media = None
eq(r._vis_cover_color(), None, "Ohne Cover: keine Farbe")
ok(r.settings["visual"].get("cover_colors") is False, "Coverfarben ab Werk aus")
ok(r.settings["visual"].get("weather_fx") is True, "Wetter ab Werk an")

# Wetter
base = run(1.0, style="farm")
for kind in ("rain", "snow", "thunder", "fog"):
    r._party_wx = (time.monotonic() + 1e9, (kind, 5, 20))
    out = r._vis_weather_fx(base.copy(), 5000 + T[0])
    ok(out.tobytes() != base.tobytes(), f"Wetter „{kind}“ ist zu sehen")
r._party_wx = (time.monotonic() + 1e9, ("sun", 20, 5))
ok(r._vis_weather_fx(base.copy(), 5000 + T[0]).tobytes() == base.tobytes(), "Sonne: Bild bleibt unverändert")
ok("farm" in g.WEATHER_FX_STYLES and "oktoberfest" not in g.WEATHER_FX_STYLES, "Wetter nur in Draußen-Szenen")
done()
