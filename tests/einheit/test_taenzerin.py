"""Stil „Tänzerin an der Stange“: Haltung wechselt auf Bassschläge, hohe Schläge geben Akzente, Höhepunkt löst eine
Drehung um die Stange aus, Wortbeitrag → Langeweile an der Stange (nach 30 s sitzt sie), Rock schwingt nach;
Lichtshow (Scheinwerfer, Disco mit Spiegelkugel) und Stroboskop über das Optionsmenü; Figuren an der Stange
(alle 8 Schläge die nächste), Haarfarbe."""
import time
import numpy as np
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
O = g.visual_options(r.settings, "dancer")
FPS = 15
T = [0.0]


def frame(amp=1.0, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=amp)
    s.update(active=True, demo=False, t=t, **kw)
    g.VISUAL_RENDERERS["dancer"](r, s, O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["dancer"]


eq(g.VISUAL_STYLES["dancer"], "Tänzerin an der Stange", "Name des Stils")
r._vis_states = {}
poses, t0 = set(), time.perf_counter()
for _ in range(FPS * 6):
    st = frame()
    poses.add(st["k"])
ms = (time.perf_counter() - t0) / (FPS * 6) * 1000
ok(len(poses) >= 10, f"Haltung wechselt auf Bassschläge ({len(poses)} Wechsel in 6 s bei 120/min)")
ok(ms < 8, f"Zeichenzeit je Bild {ms:.2f} ms")

# hoher Schlag → Akzent
st = frame(hats=st["hats"] + 1, hat=0.9)
ok(st["accent"] > 0.5, "Hoher Schlag: Akzent mit Hand und Kopf")
st = frame(hats=st["hats"] + 1, hat=0.1)
st2 = frame(hats=st["hats"] + 1, hat=0.1)
ok(st2["accent"] < 0.5, "Ganz leiser hoher Schlag: kein neuer Akzent")

# Höhepunkt → Drehung um die Stange (zusätzlich zu den Figuren alle 8 Schläge)
r._vis_states = {}
spins = []
for i in range(FPS * 12):
    st = frame(amp=0.62 if i < FPS * 8 else 1.0)
    if st.get("move") and st["move"][0] == "spin":
        spins.append(i / FPS)
ok(spins and min(spins) >= 8.0, f"Höhepunkt: Drehung um die Stange erst, als es lauter wird ({spins[:1]})")
for _ in range(FPS * 4):
    st = frame()
ok(st["hip_x"] > g.BAL_POLE_X, "Nach der Drehung wieder an ihrem Platz")
hem = st["hem"]
ok(len(hem) == 9 and all(len(p) == 4 for p in hem), "Rock: Saumpunkte mit Geschwindigkeit (Nachschwingen)")

# Wortbeitrag → gelangweilt an der Stange, nach 30 s sitzen
r._vis_states = {}
T[0] = 0.0
for _ in range(FPS * 2):
    st = frame(talk=True, talk_t=5000.0)
eq(st.get("bored"), "cross", "Wortbeitrag: lehnt mit verschränkten Armen")
T[0] = 40.0
for _ in range(FPS * 2):
    st = frame(talk=True, talk_t=5000.0)
eq(st.get("bored"), "sit", "Nach 30 s: sitzt an der Stange")
k = st["k"]
st = frame()
ok(st.get("bored") is None and st.get("listen"), "Musik zurück: erst zuhören")
for _ in range(FPS * 4):
    st = frame()
ok(not st.get("listen") and st["k"] > k, "… dann tanzt sie weiter")

# Liedwechsel: erst den Takt hören (5 gleichmäßige Schläge), dann im gefundenen Tempo tanzen
r._vis_states = {}
r._vis_song = "AC/DC – Thunderstruck"
for _ in range(FPS * 3):
    st = frame()
k = st["k"]
r._vis_song = "Queen – Bohemian Rhapsody"
st = frame()
ok(st.get("listen"), "Neues Lied: sie hört zu")
listen_frames = 0
while st.get("listen") and listen_frames < FPS * 10:
    st = frame()
    listen_frames += 1
eq(st["k"], k, "Beim Zuhören keine neuen Schritte")
ok(1.8 <= listen_frames / FPS <= 3.0, f"Takt nach {listen_frames / FPS:.1f} s gefunden (5 Schläge bei 120/min)")
ok(abs(st.get("tempo", 0) - 0.5) < 0.03, f"Tempo erkannt: {st.get('tempo')}")
for _ in range(FPS):
    st = frame()
ok(st["k"] > k, "Danach tanzt sie im Takt")

# Unregelmäßige Schläge: spätestens nach 8 s geht es trotzdem los
r._vis_states = {}
r._vis_song = "A"
frame()
r._vis_song = "B"
import random
rnd = random.Random(3)
bt, beats, n = 5000.0, 0, 0
while True:
    t = 5000 + T[0]
    if t >= bt:
        beats += 1
        bt = t + rnd.uniform(0.3, 0.9)
    st = frame(beats=beats, beat_t=t)
    n += 1
    if not st.get("listen") or n > FPS * 12:
        break
ok(7.5 <= n / FPS <= 8.5, f"Ohne klaren Takt: Start nach {n / FPS:.1f} s")
r._vis_song = ""

# Lichtshow aus dem Optionsmenü
eq((O["show"], O["strobe"]), ("off", "off"), "Standard: Studio ohne Lichtshow, kein Stroboskop")
ok({"show", "beams", "strobe", "strobe_rate", "strobe_color", "strobe_keys"} <= {x["key"] for x in g.VISUAL_OPTIONS["dancer"]},
   "Optionen: Lichtshow, Scheinwerfer, Stroboskop")


def img_with(opts, talk=False, at=1.0):
    r._vis_states = {}
    img = None
    for i in range(int(at * FPS)):
        t = 5000 + i / FPS
        s = g.demo_snapshot(t)
        s.update(active=True, demo=False, t=t, talk=talk, talk_t=4990.0)
        img = g.VISUAL_RENDERERS["dancer"](r, s, dict(O, **opts), (0, 255, 90))
    return np.asarray(img).astype(int)


studio, club = img_with({}), img_with({"show": "club"})
ok(np.abs(studio - club).mean() > 10, "Disco: Raum und Licht sichtbar anders")
ball = club[2:22, g.BAL_POLE_X + 86:g.BAL_POLE_X + 106]
ok(ball.max() > 150, "Disco: Spiegelkugel funkelt")
ok(club[:g.VIS_H, :, :].mean() < studio[:g.VIS_H, :, :].mean(), "Disco: abgedunkelt")
ok(np.abs(img_with({}, talk=True) - img_with({"show": "club"}, talk=True)).mean() < 1,
   "Wortbeitrag: Lichtshow ruht")
r._vis_states = {}
flashes = []
for i in range(FPS * 10):
    t = 5000 + i / FPS
    s = g.demo_snapshot(t)
    s.update(active=True, demo=False, t=t)
    im = g.VISUAL_RENDERERS["dancer"](r, s, dict(O, show="club", strobe="beat", strobe_rate="3"), (0, 255, 90))
    if np.asarray(im)[:g.VIS_H].mean() > 150:
        flashes.append(i / FPS)
gaps = [b - a for a, b in zip(flashes, flashes[1:])]
ok(len(flashes) >= 10 and min(gaps) >= 1 / 3 - 1e-6, f"Stroboskop bei der Tänzerin: {len(flashes)} Blitze, ≤ 3 je Sekunde")

# Figuren an der Stange: alle 8 Schläge die nächste, alle kommen vor
r._vis_states = {}
T[0] = 0.0
seen = set()
for _ in range(FPS * 40):
    st = frame()
    mv = st.get("move")
    if mv:
        seen.add(mv[0])
eq(seen >= set(g.BAL_MOVE_ORDER), True, f"Alle Figuren an der Stange in 40 s: {sorted(seen)}")
ok(all(m in g.BAL_MOVES for m in g.BAL_MOVE_ORDER) and all(p[1] in g.BAL_POSES for p in g.BAL_MOVES.values()),
   "Jede Figur hat eine Haltung")

# Klettern: sie ist ein gutes Stück über dem Boden
r._vis_states = {}
frame()
r._vis_states["dancer"]["move"] = ("climb", 5000 + T[0])
low = 999
for _ in range(int(FPS * 2.1)):
    st = frame()
    low = min(low, min(p[1] for p in st["hem"]))
ok(low < 132, f"Klettern: Rocksaum hoch über dem Boden ({low:.0f})")

# Haarfarbe
dark = img_with({})
blond = img_with({"hair": "blond"})
diff = np.abs(dark - blond).sum(axis=2) > 60
ys, xs = np.nonzero(diff[:g.VIS_H])
ok(diff.sum() > 20 and ys.mean() < 110, f"Haarfarbe ändert nur den Kopf ({diff.sum()} Pixel)")
eq(O["hair"], "dark", "Standard: dunkles Haar")
done()
