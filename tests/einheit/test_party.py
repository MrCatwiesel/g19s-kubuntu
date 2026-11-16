"""Stil „Überraschungsparty“: verstecken im Dunkeln → Überraschung beim Höhepunkt (spätestens nach 20 s) → Party
mit Gags (Hund frisst die Torte, Trickkerzen, Kastenteufel), platzende Ballons bei kräftigem Bass, Helium bei
Wortbeiträgen, nach einer Runde wieder verstecken; Banner und Alter aus der Geburtstagsliste."""
import datetime as dt
import time
from PIL import ImageStat
from common import g, eq, ok, done

g.fest_today = lambda: dt.date(2026, 11, 16)
r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def opts(**kw):
    r.settings["visual"]["party"].update(kw)
    return g.visual_options(r.settings, "party")


O = opts()


def frame(amp=1.0, o=None, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t, amp=amp)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    img = g.VISUAL_RENDERERS["party"](r, s, o or O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["party"], img


def run(seconds, **kw):
    st = img = None
    for _ in range(int(round(seconds * FPS))):
        st, img = frame(**kw)
    return st, img


eq(g.VISUAL_STYLES["party"], "Überraschungsparty", "Name des Stils")
r._vis_states = {}
st, img = frame()
eq(st["phase"], "hide", "Live: erst verstecken sich alle")
ok(r.vis_party_dark, "Tastatur: im Versteck dunkel")
dark = ImageStat.Stat(img.convert("L").crop((0, 0, 320, 200))).mean[0]
ok(dark < 45, f"Raum ist dunkel ({dark:.0f})")
t0 = time.perf_counter()
st, _ = run(5.0)
eq(st["phase"], "hide", "Mindestens 6 s versteckt, auch bei gleichmäßiger Musik")
st, _ = run(19.0)
eq(st["phase"], "party", "Spätestens nach 20 s: Überraschung und Party")
ms = (time.perf_counter() - t0) / (24 * FPS) * 1000
ok(ms < 8, f"Zeichenzeit je Bild {ms:.2f} ms")
ok(not r.vis_party_dark, "Licht ist an")

# Höhepunkt (lauter werdende Musik) löst die Überraschung früher aus
r._vis_states = {}
st, _ = run(7.0, amp=0.55)
eq(st["phase"], "hide", "Leise Musik: noch versteckt")
st, img = run(1.0, amp=1.0)
eq(st["phase"], "surprise", "Höhepunkt nach 7 s: ÜBERRASCHUNG!")
ok(len(st["confetti"]) > 30, "Konfetti fliegt")
st, _ = run(4.0)
eq(st["phase"], "party", "Danach Party")
ok(st["next_gag"] is not None, "Erster Gag geplant")

# Gags der Reihe nach erzwingen
for name in ("hund", "kerzen", "geschenk"):
    st["gag"], st["next_gag"] = (name, 5000 + T[0]), None
    st, _ = run(g.PT_GAGS[name] + 0.2)
    ok(st["gag"] is None, f"Gag „{name}“ läuft durch und endet")
eq(st["eaten"], 1.0, "Hund hat die Torte gefressen")
eq(st["dog"], "lie", "… und liegt satt in der Ecke")
eq(r._pt_candles_out(("kerzen", 0.0), 3.0), 1.0, "Trickkerzen: ausgepustet …")
eq(r._pt_candles_out(("kerzen", 0.0), 4.0), 0.0, "… und wieder an")

# Ballon platzt bei kräftigem Bass (nicht in den ersten 20 s der Party, Sperre 25 s)
st["phase_t"] = 5000 + T[0] - 30
st["pop_t"] = -99.0
n = sum(st["balloons"])
st, _ = run(2.0)
ok(sum(st["balloons"]) == n - 1, f"Ein Ballon ist geplatzt ({n} → {sum(st['balloons'])})")
st, _ = run(5.0)
ok(sum(st["balloons"]) == n - 1, "Sperre: nicht gleich der nächste")

# Wortbeitrag: Helium, nach 25 s sitzen alle am Boden
st, img = run(3.0, talk=True, talk_t=5000 + T[0])
ok(img is not None, "Wortbeitrag: Heliumstimmen")
heads = {}
st["gag"] = None
st, _ = run(1.0, talk=True, talk_t=5000 + T[0] - 30)
ok(all(gg["pose"]["bob"] == 0.0 for gg in st["guests"]), "Lange Wortbeiträge: alle sitzen ruhig")

# Runde zu Ende → verstecken, neue Torte, Ballons wieder da
st["phase_t"] -= 400
st["gag"] = None
st, _ = frame()
eq(st["phase"], "hide", "Nach der Runde: wieder verstecken")
eq(st["eaten"], 0.0, "Neue Torte")
ok(all(st["balloons"]), "Alle Ballons wieder da")
eq(st["round"], 2, "Zweite Runde")

# Hund abgeschaltet: Gag „hund“ entfällt
r._vis_states = {}
O2 = opts(dog=False)
st, _ = frame(o=O2)
st.update(phase="party", phase_t=5000 + T[0] - 30, next_gag=5000 + T[0], order=["hund", "kerzen"])
st, _ = frame(o=O2)
eq(st["gag"][0], "kerzen", "Ohne Hund: nächster Gag statt Hund")

# Vorschau (demo): gleich Party, ohne Gags
r._vis_states = {}
s = g.demo_snapshot(100.0)
g.VISUAL_RENDERERS["party"](r, s, O, (0, 255, 90))
eq(r._vis_states["party"]["phase"], "party", "Vorschau zeigt die Party")

# Banner und Alter
eq(g._pt_banner([]), "Alles Gute!", "Banner ohne Geburtstag")
eq(g._pt_banner(["Max"]), "Alles Gute, Max!", "Banner mit Namen")
eq(g._pt_banner(["Max", "Anna"]), "Alles Gute, Max & Anna!", "Zwei Namen")
eq(g._pt_banner(["A", "B", "C"]), "Alles Gute euch allen!", "Mehr als zwei")
opts(birthdays=[{"name": "Max", "day": 16, "month": 11, "year": 1974}], dog=True)
eq(r._pt_people(), (["Max"], 52), "Geburtstagskind von heute mit Alter")
done()
