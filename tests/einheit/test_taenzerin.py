"""Stil „Tänzerin an der Stange“: Haltung wechselt auf Bassschläge, hohe Schläge geben Akzente, Höhepunkt löst eine
Drehung um die Stange aus, Wortbeitrag → Langeweile an der Stange (nach 30 s sitzt sie), Rock schwingt nach."""
import time
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

# Höhepunkt → Drehung um die Stange (Hüfte wechselt die Seite der Stange)
r._vis_states = {}
xs = []
for i in range(FPS * 12):
    st = frame(amp=0.62 if i < FPS * 8 else 1.0)
    xs.append(st["hip_x"])
quiet, loud = xs[:FPS * 8], xs[FPS * 8:]
ok(min(quiet) > g.BAL_POLE_X and min(loud) < g.BAL_POLE_X - 10, "Höhepunkt: Drehung um die Stange")
ok(xs[-1] > g.BAL_POLE_X, "Nach der Drehung wieder an ihrem Platz")
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
for _ in range(FPS * 2):
    st = frame()
ok(st.get("bored") is None and st["k"] > k, "Musik zurück: tanzt weiter")
done()
