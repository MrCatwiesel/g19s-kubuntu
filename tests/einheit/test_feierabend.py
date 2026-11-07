"""Visualisierung „Weihnachten“, Option „Feierabend“: Ablauf einer Runde (alle Gags in fester Folge), Pause ohne
Musik, Bank bei Wortbeiträgen (nüchtern: Wunschliste/Kakao, später: einschlafen mit Kater, danach „Nur noch
einen …“), Standard aus, „nur abends“."""
import time
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
BASE = g.visual_options(r.settings, "xmas")
OPTS = dict(BASE, party="on", party_len="300")
T = [0.0]


def frame(opts=OPTS, talk=False, active=True):
    s = g.demo_snapshot(5000 + T[0])
    s.update(active=active, demo=False, talk=talk, t=5000 + T[0])
    g.VISUAL_RENDERERS["xmas"](r, s, opts, (255, 255, 255))
    T[0] += 1 / 15
    return r._vis_states["xmas"]


def party():
    return r._vis_states["xmas"].get("party")


# Ablauf und Einstellungen
eq((BASE["party"], BASE["party_len"]), ("off", "600"), "Standard: Feierabend aus, Runde 10 Minuten")
for length in (300, 600, 900, 1200):
    tl = g.party_timeline(length)
    ok(abs(tl[-1][1] + tl[-1][2] - length) < 1e-6 and all(a[1] + a[2] == b[1] for a, b in zip(tl, tl[1:])),
       f"Runde {length} s: Schritte lückenlos, Summe = Rundenlänge")
eq([s[0] for s in g.party_timeline(300)], [s[0] for s in g.PARTY_STEPS], "Reihenfolge der Gags")
ok(min(d for n, s, d in g.party_timeline(120)) >= 6, "Auch die kürzeste Runde lässt jedem Gag Zeit")
eq([g.party_active({"party": "evening"}, h) for h in (19, 20, 23, 3, 4, 12)],
   [False, True, True, True, False, False], "Nur abends: 20 bis 4 Uhr")
eq((g.party_active({"party": "off"}), g.party_active({"party": "on"}), g.party_active({})), (False, True, False),
   "Aus/An/fehlend")

# Option aus: kein Feierabend-Zustand, Tastatur nicht grün
for _ in range(30):
    st = frame(BASE)
ok("party" not in st and not r.vis_green, "Aus: keine Gags")

# Eine ganze Runde (5 Minuten) bei Musik
r._vis_states = {}
seen, states, flags = [], {}, {}
t0 = time.perf_counter()
n = 0
while True:
    st = frame()
    n += 1
    p = party()
    name = next(s[0] for s in g.party_timeline(300) if s[1] <= p["p"] < s[1] + s[2])
    if not seen or seen[-1] != name:
        seen.append(name)
    for who in ("santa", "mrs"):
        states.setdefault(name, set()).add((who, st["acts"][who]["state"]))
    if r.vis_green:
        flags.setdefault("green", set()).add(name)
    if st["acts"]["santa"].get("back"):
        flags.setdefault("back", set()).add(name)
    if len(seen) > len(g.PARTY_STEPS) and n > 100:
        break
ms = (time.perf_counter() - t0) / n * 1000
eq(seen, [s[0] for s in g.PARTY_STEPS] + ["prost"], "Alle Gags der Reihe nach, dann von vorn")
ok(("santa", "p_behind") in states["baum"] and ("mrs", "p_wait") in states["baum"], "Baum: er dahinter, sie wartet")
ok(("mrs", "p_behind") in states["baum2"] and ("santa", "p_whistle") in states["baum2"], "Dann sie, er pfeift")
ok(("mrs", "p_point") in states["rentier"] and ("santa", "p_excuse") in states["rentier"], "„War das Rentier!“")
ok(("santa", "p_write") in states["signatur"], "Signatur im Schnee")
ok(("mrs", "p_tongue") in states["gelb"] and ("santa", "p_grab") in states["gelb"], "Gelber Schnee: er zieht sie weg")
ok(("santa", "p_vomit") in states["bescherung"] and ("mrs", "p_hat") in states["bescherung"],
   "Bescherung: sie hält die Mütze")
ok(("santa", "p_sleep") in states["kater"] and ("mrs", "p_sleep") in states["kater"], "Kater: beide schlafen")
ok(flags.get("green", set()) <= {"gruen", "bescherung", "kater"} and "bescherung" in flags.get("green", ()),
   "Tastatur grün nur, solange ihm schlecht ist")
eq(flags.get("back"), {"noch"}, "„Nur noch einen …“: sie zieht ihn rückwärts zurück")
ok(ms < 5, f"Zeichenzeit je Bild {ms:.2f} ms")

# Ohne Musik bleibt die Runde stehen
p0 = party()["p"]
for _ in range(30):
    frame(active=False)
eq(round(party()["p"], 6), round(p0, 6), "Ohne Musik: Runde steht")

# Wortbeitrag früh in der Runde: Bank wie sonst (Wunschliste, Kakao), Runde pausiert
r._vis_states = {}
for _ in range(15 * 10):
    frame()
p0 = party()["p"]
for _ in range(15 * 6):
    st = frame(talk=True)
eq((st["acts"]["santa"]["state"], st["acts"]["mrs"]["state"]), ("sit", "sit"), "Früh: Bank wie sonst")
eq(round(party()["p"], 6), round(p0, 6), "Wortbeitrag: Runde pausiert")

# Wortbeitrag nach dem grünen Gesicht: einschlafen mit Kater, danach „Nur noch einen …“
tl = {n: (s, d) for n, s, d in g.party_timeline(300)}
party()["p"] = tl["gruen"][0] + 1.0
for _ in range(15 * 6):
    st = frame(talk=True)
eq((st["acts"]["santa"]["state"], st["acts"]["mrs"]["state"], party()["sleep"]), ("p_sleep", "p_sleep", True),
   "Spät: beide schlafen auf der Bank")
frame()
p = party()["p"]
ok(tl["noch"][0] <= p < tl["noch"][0] + 0.2, "Nach dem Wortbeitrag: „Nur noch einen …“")
done()
