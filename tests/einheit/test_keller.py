"""Stil „Kellertreppe“: Glühbirne pendelt im Takt (Bassschläge stoßen an, Wortbeitrag beruhigt), Höhepunkt =
Licht flackert und geht aus, dann saugt das Monster; Gags der Reihe nach; Gänsehaut-Stufe 3 mit Herzschlag und
Schreckmoment; Gewitter (Wetterseite) blitzt durchs Kellerfenster."""
import time
from PIL import ImageStat
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def opts(**kw):
    r.settings["visual"]["cellar"].update(kw)
    return g.visual_options(r.settings, "cellar")


O = opts()


def frame(amp=1.0, o=None, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=amp)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    img = g.VISUAL_RENDERERS["cellar"](r, s, o or O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["cellar"], img


def run(seconds, **kw):
    st = img = None
    for _ in range(int(round(seconds * FPS))):
        st, img = frame(**kw)
    return st, img


eq(g.VISUAL_STYLES["cellar"], "Kellertreppe", "Name des Stils")
r._vis_states = {}
t0 = time.perf_counter()
amp = 0.0
for _ in range(FPS * 6):
    st, _ = frame()
    amp = max(amp, abs(st["th"]))
ms = (time.perf_counter() - t0) / (FPS * 6) * 1000
ok(ms < 8, f"Zeichenzeit je Bild {ms:.2f} ms")
ok(amp > 0.35, f"Bassschläge bringen die Glühbirne ins Pendeln ({amp:.2f} rad)")
ok(amp < 0.7, "… aber sanft begrenzt (unter 0,7 rad)")
st, _ = run(6.0, talk=True, talk_t=5000 + T[0])
ok(abs(st["th"]) < 0.1, f"Wortbeitrag: Glühbirne kommt zur Ruhe ({st['th']:.2f})")

# Höhepunkt: lauter werdende Musik → flackern, dunkel, Monster
r._vis_states = {}
st, _ = run(8.0, amp=0.5)
eq(st["booms"], 0, "Gleichmäßig leise: kein Höhepunkt")
st, _ = run(0.5, amp=1.0)
eq(st["booms"], 1, "Lauter: Höhepunkt")
st, img = run(1.0)
eq(r.vis_bulb, 0.0, "Licht ist aus")
light = ImageStat.Stat(img.convert("L").crop((0, 0, 320, 200))).mean[0]
ok(light < 25, f"Keller ist dunkel, nur Augen ({light:.0f})")
st, img = run(1.5)
eq(r.vis_bulb, 1.0, "Licht wieder an (Monster saugt)")
st, _ = run(8.0)
eq(st["booms"], 1, "Sperre: nicht gleich wieder")

# Gags der Reihe nach, alle vier je Durchgang
r._vis_states = {}
seen = []
st, _ = frame()
for _ in range(4):
    st["next_gag"] = 5000 + T[0]
    st, _ = frame()
    seen.append(st["gag"][0])
    st, _ = run(g.CL_GAGS[st["gag"][0]] + 0.2)
    ok(st["gag"] is None, f"Gag „{seen[-1]}“ endet")
eq(sorted(seen), sorted(g.CL_GAGS), "Jeder Gag einmal je Durchgang")

# Stufe 3: Herzschlag und Schreckmoment; Stufe 1 ohne
r._vis_states = {}
O3 = opts(level="3")
beat = max(frame(o=O3)[0] and r.vis_heart for _ in range(FPS))
ok(beat > 0.3, f"Stufe 3: Herzschlag ({beat:.2f})")
st, _ = frame(o=O3)
st["boom"], st["booms"] = 5000 + T[0] - 1.8, 1
_, img = frame(o=O3)
red = ImageStat.Stat(img.crop((0, 0, 320, 200))).mean
ok(red[0] > 40 and red[0] > red[2] * 0.6, f"Schreckmoment: großes Gesicht im Dunkeln ({red[0]:.0f})")
r._vis_states = {}
O1 = opts(level="1")
run(1.0, o=O1)
eq(r.vis_heart, 0.0, "Stufe 1: kein Herzschlag")
st, _ = frame(o=O1)
st["boom"], st["booms"] = 5000 + T[0] - 1.8, 1
_, img = frame(o=O1)
ok(ImageStat.Stat(img.crop((0, 0, 320, 200))).mean[0] < 25, "Stufe 1: kein Schreckmoment")

# Gewitter laut Wetterseite: Blitz im Kellerfenster, höchstens alle 6 s
r._vis_states = {}
opts(level="2")
r._party_weather = lambda: ("thunder", 12.0, 10.0)
flashes, last = [], -99
for _ in range(FPS * 25):
    st, _ = frame()
    if st["flash"] != last:
        flashes.append(st["flash"])
        last = st["flash"]
ok(2 <= len(flashes) <= 4, f"Gewitter: {len(flashes)} Blitze in 25 s")
ok(all(b - a >= 6 for a, b in zip(flashes, flashes[1:])), "Mindestens 6 s zwischen zwei Blitzen")
del r._party_weather

# Vorschau (demo) ohne Gags und Höhepunkt
r._vis_states = {}
for k in range(30):
    g.VISUAL_RENDERERS["cellar"](r, g.demo_snapshot(100.0 + k / 15), O, (0, 255, 90))
st = r._vis_states["cellar"]
ok(st["gag"] is None and st["booms"] == 0, "Vorschau: ruhig pendelnde Glühbirne")
done()
