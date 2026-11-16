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

# Gags der Reihe nach, jeder einmal je Durchgang (Bewohner-Gags warten, bis Zombie/Skelett bereit sind)
r._vis_states = {}
seen = []
st, _ = run(8.0)
for _ in range(len(g.CL_GAGS)):
    st["next_gag"] = 5000 + T[0]
    for _ in range(FPS * 12):
        st, _ = frame()
        if st["gag"]:
            break
    seen.append(st["gag"][0])
    st, _ = run(g.CL_GAGS[st["gag"][0]] + 0.2)
    ok(st["gag"] is None, f"Gag „{seen[-1]}“ endet")
eq(sorted(seen), sorted(g.CL_GAGS), "Jeder Gag einmal je Durchgang")

# Bewohner: Stufe 1 nur das Skelett, Stufe 2 dazu zwei Zombies, Stufe 3 eine Horde
for lv, n in (("1", 0), ("2", 2), ("3", 4)):
    r._vis_states = {}
    st, _ = run(1.0, o=opts(level=lv))
    eq(sum(c["kind"] == "zombie" for c in st["crew"]), n, f"Stufe {lv}: {n} Zombies")
    eq(st["crew"][0]["kind"], "skel", f"Stufe {lv}: Skelett aus dem Schrank")
O = opts(level="2")
r._vis_states = {}
st, _ = frame()
ok(all(c["mode"] in ("under", "hidden") for c in st["crew"]), "Live: anfangs im Boden bzw. im Schrank")
st, _ = run(6.0)
ok(all(c["mode"] == "idle" for c in st["crew"]), "Nach 6 s sind alle draußen: " + str([c["mode"] for c in st["crew"]]))
st["next_gag"] = 1e9
t0 = time.perf_counter()
st, _ = run(4.0, o=opts(level="3"))
ms = (time.perf_counter() - t0) / (FPS * 4) * 1000
ok(ms < 10, f"Stufe 3 mit Horde: {ms:.2f} ms je Bild")
O = opts(level="2")
r._vis_states = {}
st, _ = run(6.0)
st["next_gag"] = 1e9
st["boom"], st["booms"] = 5000 + T[0] - 2.3, 1                                  # Monster kommt
st, _ = run(1.5)
ok(all(c["mode"] in ("sink", "gone") for c in st["crew"] if c["kind"] == "zombie"), "Höhepunkt: Zombies flüchten in den Boden")
ok(st["crew"][0]["mode"] in ("flee", "gone"), "… das Skelett in den Schrank")
st, _ = run(12.0)
ok(all(c["mode"] == "idle" for c in st["crew"]), "Danach kommen alle wieder")
st, _ = run(10.0, talk=True, talk_t=5000 + T[0])
ok(all(c["x"] < g.CL_ROAM[0] for c in st["crew"]), "Wortbeitrag: alle sitzen auf der Treppe " +
   str([round(c["x"]) for c in st["crew"]]))
st, _ = run(8.0)
ok(all(c["x"] >= g.CL_ROAM[0] - 9 for c in st["crew"]), "Danach wieder unten im Keller")
r._vis_song = "Neues Lied"
st, _ = frame()
ok(any(c["mode"] == "sink" for c in st["crew"]), "Liedwechsel: ein Zombie taucht ab …")
st, _ = run(3.0)
ok(all(c["mode"] in ("idle", "rise") for c in st["crew"]), "… und woanders wieder auf")
st, _ = run(2.0)
st["zerfall"] = -99.0
st, _ = run(3.0, amp=1.6)
ok(st["zerfall"] > 0, "Sehr kräftiger Bass: das Skelett zerfällt")
st["gag"] = ("hausverwalter", 5000 + T[0])
st, _ = run(12.2)
ok(st["note"], "Hausverwalter: Zettel „Ruhezeiten“ hängt")
st["gag"] = ("glas", 5000 + T[0])
st, _ = run(9.7)
eq(st["jars"], 1, "Ein Einmachglas leer gefuttert")
ok(not g.CellarCrew._cl_crew_can(r, {"crew": [{"kind": "skel", "mode": "idle"}], "zerfall": -99, "t_now": 0}, "arm"),
   "Ohne Zombie kein Arm-Gag")

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
