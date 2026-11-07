"""Visualisierung „Weihnachten“, Option „Feierabend“: Runden mit Pegel und zufälligen Gags (Regeln, je Runde
einmal, fester Schluss), Prosten je nach Musik (wild/ruhig mit Schunkeln), wechselnde Sprüche, Weihnachtslied im
Radio, Nacht, Silvester, Zwischengags, Wortbeitrag (nüchtern Bank, spät einschlafen → Morgen danach)."""
import time
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
BASE = g.visual_options(r.settings, "xmas")
OPTS = dict(BASE, party="on", party_len="600")
END = [n for n, _d in g.PARTY_END]
T = [0.0]
FPS = 10


def frame(opts=OPTS, talk=False, active=True, amp=1.0):
    s = g.demo_snapshot(5000 + T[0], amp=amp)
    s.update(active=active, demo=False, talk=talk, t=5000 + T[0])
    g.VISUAL_RENDERERS["xmas"](r, s, opts, (255, 255, 255))
    T[0] += 1 / FPS
    return r._vis_states["xmas"]


def party():
    return r._vis_states["xmas"].get("party")


def fresh():
    r._vis_states = {}
    T[0] = 0.0
    frame()


class Clock:
    def __init__(self, mon, day, hour, minute=0):
        self.tm_mon, self.tm_mday, self.tm_hour, self.tm_min = mon, day, hour, minute


real_clock = g.party_clock
g.party_clock = lambda: Clock(11, 20, 21)                     # gewöhnlicher Abend

# Einstellungen, Regeln
eq((BASE["party"], BASE["party_len"]), ("off", "600"), "Standard: Feierabend aus, Runde 10 Minuten")
eq([g.party_active({"party": "evening"}, h) for h in (19, 20, 23, 3, 4, 12)],
   [False, True, True, True, False, False], "Nur abends: 20 bis 4 Uhr")
eq((g.party_mood(0.8, 0.45), g.party_mood(0.5, 0.5), g.party_mood(0.2, 0.5)), ("wild", "normal", "ruhig"),
   "Musik: wild / normal / ruhig")
eq((g.party_song_xmas("Wham! – Last Christmas"), g.party_song_xmas("AC/DC – Thunderstruck")), (True, False),
   "Weihnachtslied am Titel erkannt")
ps = r._party_new(1)
ps["pegel"] = 0.9
eq((g.party_eligible(ps, "rentier"), g.party_eligible(ps, "rutsch"), g.party_eligible(ps, "wichtel")),
   (False, False, False), "Ausrede, Ausrutschen, Wichtel erst nach Spuren")
ps["props"].add("puddle")
eq((g.party_eligible(ps, "rentier"), g.party_eligible(ps, "rutsch"), g.party_eligible(ps, "wichtel")),
   (True, True, True), "… nach der Pfütze möglich")
ps["pegel"] = 0.1
ok(not g.party_eligible(ps, "baumcrash") and g.party_eligible(ps, "groelen", "Last Christmas") and
   not g.party_eligible(ps, "groelen", "Thunderstruck"), "Mindestpegel; Grölen nur bei Weihnachtsliedern")
ok(all(len(g.PARTY_LINES[k]) >= 2 for k in ("prost", "ausrede", "unartig", "neujahr")), "Wechselnde Sprüche")

# Aus: keine Gags
fresh()
for _ in range(20):
    st = frame(BASE)
ok("party" not in st and not r.vis_green, "Aus: keine Gags")

# Drei Runden à 10 Minuten bei wilder Musik (künstliche Musik: laut, 120 Schläge/min)
fresh()
r._vis_song = ""
rounds, seq, greens = [], [], set()
seed, last, n, t0 = party()["seed"], None, 0, time.perf_counter()
while len(rounds) < 3 and n < 60000:
    st = frame()
    n += 1
    p = party()
    cur = p["cur"]["name"] if p["cur"] else None
    if p["seed"] != seed:
        rounds.append(seq)
        seq, seed, last = [], p["seed"], None
    if cur and cur != last:
        seq.append((cur, sorted(p["props"])))
    last = cur
    if r.vis_green:
        greens.add(cur)
ms = (time.perf_counter() - t0) / max(1, n) * 1000
eq(len(rounds), 3, "Drei Runden durchgelaufen")
names = [[x[0] for x in rd] for rd in rounds]
ok(all(rd[-len(END):] == END for rd in names), "Jede Runde endet mit grün → Bescherung → Kater → Morgen → noch")
ok(all(len(set(rd)) == len(rd) for rd in names), "Kein Gag zweimal in einer Runde")
mids = [rd[:-len(END)] for rd in names]
ok(all(len(m) >= 4 for m in mids), f"Je Runde mehrere Gags ({[len(m) for m in mids]})")
ok(len({tuple(m) for m in mids}) == 3, "Reihenfolge ist je Runde anders")
allg = set(x for m in mids for x in m)
ok(len(allg) >= 10, f"Viele verschiedene Gags ({len(allg)}): {sorted(allg)}")
ok("groelen" not in allg, "Ohne Weihnachtslied kein Grölen")


def before(rd, a, need):
    return all(any(y[0] in need for y in rd[:i]) for i, y in enumerate(rd) if y[0] == a)


ok(all(before(rd, "rentier", ("baum",)) and before(rd, "rutsch", ("baum",)) for rd in rounds),
   "Ausrede und Ausrutschen erst nach dem Baum")
ok(all(before(rd, "wichtel", ("baum", "signatur")) for rd in rounds), "Wichtel erst nach Pfütze oder Signatur")
ok(greens <= {"gruen", "bescherung", "kater"} and "bescherung" in greens, "Tastatur grün nur, solange ihm schlecht ist")
ok(ms < 5, f"Zeichenzeit je Bild {ms:.2f} ms")

# Ohne Musik bleibt die Runde stehen
p0 = party()["p"]
for _ in range(20):
    frame(active=False)
eq(round(party()["p"], 6), round(p0, 6), "Ohne Musik: Runde steht")

# B: wilde Musik → prosten, Pegel steigt; ruhige Musik → schunkeln, kaum Pegel
fresh()
for _ in range(FPS * 120):
    frame()
wild = party()["pegel"]
fresh()
for _ in range(FPS * 120):
    frame(amp=0.3)
quiet = party()["pegel"]
ok(wild > 3 * quiet and wild > 0.15, f"Pegel nach 2 min: wild {wild:.2f}, ruhig {quiet:.2f}")
P = r._xmas_party(r._vis_states["xmas"], dict(g.demo_snapshot(5000 + T[0], amp=0.3), active=True), T[0], 0.1,
                  OPTS, True, False, False, False)
ok(P.get("schunkel") and P.get("prost") is None, "Ruhig: schunkeln statt prosten")

# E: Zwischengags beim Tanzen
fresh()
party()["pegel"] = 0.5
micros = set()
for _ in range(FPS * 90):
    frame()
    m = party()["micro"]
    if m:
        micros.add(m[0])
ok({"stolpern", "takt", "spill", "hicks"} & micros and len(micros) >= 3, f"Zwischengags: {sorted(micros)}")
ok("gaehn" not in micros, "Abends kein Gähnen")

# D: Weihnachtslied im Radio → grölen (einmal je Lied)
fresh()
r._vis_song = "Wham! – Last Christmas"
party().update(phase="mid", p=30.0, next=30.0, pegel=0.3)
sung = 0
for _ in range(FPS * 60):
    frame()
    c = party()["cur"]
    if c and c["name"] == "groelen" and c.get("_seen") is None:
        c["_seen"] = True
        sung += 1
eq(sung, 1, "Weihnachtslied: beide grölen einmal mit")
r._vis_song = ""

# D: nach Mitternacht gähnen sie, Silvester Feuerwerk
g.party_clock = lambda: Clock(11, 20, 2)
fresh()
party()["pegel"] = 0.5
gaehn = False
for _ in range(FPS * 90):
    frame()
    m = party()["micro"]
    gaehn = gaehn or bool(m and m[0] == "gaehn")
ok(party()["sleepy"] and gaehn, "Nachts: schläfrig, gähnen zwischendurch")
g.party_clock = lambda: Clock(12, 31, 23, 30)
P = r._xmas_party(r._vis_states["xmas"], dict(g.demo_snapshot(5000), active=True), 5000.0, 0.1, OPTS, True,
                  False, False, False)
ok(P.get("fireworks"), "Silvester: Feuerwerk")
g.party_clock = lambda: Clock(1, 1, 0, 2)
P = r._xmas_party(r._vis_states["xmas"], dict(g.demo_snapshot(5004), active=True), 5004.0, 0.1, OPTS, True,
                  False, False, False)
ok(P.get("fireworks") and any(t in g.PARTY_LINES["neujahr"] for _w, t in P["say"]), "Neujahr: „Frohes Neues!“")
g.party_clock = lambda: Clock(11, 20, 21)

# Wortbeitrag: früh Bank wie sonst, spät einschlafen und danach „Der Morgen danach“
fresh()
for _ in range(FPS * 10):
    frame()
p0 = party()["p"]
for _ in range(FPS * 6):
    st = frame(talk=True)
eq((st["acts"]["santa"]["state"], st["acts"]["mrs"]["state"]), ("sit", "sit"), "Früh: Bank wie sonst")
eq(round(party()["p"], 6), round(p0, 6), "Wortbeitrag: Runde pausiert")
party()["pegel"] = 0.95
for _ in range(FPS * 6):
    st = frame(talk=True)
eq((st["acts"]["santa"]["state"], st["acts"]["mrs"]["state"], party()["sleep"]), ("p_sleep", "p_sleep", True),
   "Spät: beide schlafen auf der Bank")
frame()
eq(party()["cur"]["name"], "morgen", "Nach dem Wortbeitrag: Der Morgen danach")
g.party_clock = real_clock
done()
