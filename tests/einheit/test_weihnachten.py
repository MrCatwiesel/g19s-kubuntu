"""Visualisierung „Weihnachten“: Figuren gehen ins Bild und hinaus statt zu verschwinden, gehen zur Bank,
kommen beim Öffnen der Seite herein; Vorschau ohne Ton (demo) zeigt sie sofort am Platz."""
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
OPTS = g.visual_options(r.settings, "xmas")
OFF = g.XMAS_OFF
T = [0.0]


def run(seconds, mode, talk=False, demo=False, enter=False):
    """Bilder mit 15 fps; gibt je Bild (t, Zustand santa, x santa, Zustand mrs, x mrs) zurück."""
    if enter:
        r._vis_enter = True
    out = []
    end = T[0] + seconds
    while T[0] < end - 1e-9:
        s = g.demo_snapshot(5000 + T[0])
        s.update(active=True, demo=demo, talk=talk, t=5000 + T[0])
        g.VISUAL_RENDERERS["xmas"](r, s, dict(OPTS, dance=mode), (255, 255, 255))
        a = r._vis_states["xmas"]["acts"]
        out.append((T[0], a["santa"]["state"], a["santa"]["x"], a["mrs"]["state"], a["mrs"]["x"]))
        T[0] += 1 / 15
    return out


def last():
    a = r._vis_states["xmas"]
    return a["acts"]["santa"], a["acts"]["mrs"], a


# Vorschau ohne Analyse (demo): kein Auftritt, beide sofort am Platz und Hand in Hand
run(0.2, "pair", demo=True, enter=True)
sa, mr, st = last()
eq((sa["x"], mr["x"], st["hold"]), (160, 226, 1.0), "Vorschau: Paar sofort am Platz, Hände gehalten")

# Seite geöffnet (live): beide kommen von außen herein, er von links, sie von rechts
f = run(6.0, "pair", enter=True)
eq((f[0][2], f[0][4]), (OFF["santa"], OFF["mrs"]), "Auftritt: beide starten außerhalb des Bildes")
ok(any(x[1] == "walk" for x in f) and any(x[3] == "walk" for x in f), "Auftritt: beide gehen")
sa, mr, st = last()
eq((sa["x"], mr["x"], sa["state"], mr["state"], st["hold"]), (160, 226, "dance", "dance", 1.0),
   "Auftritt: am Platz angekommen, tanzen Hand in Hand")

# Paar → er allein: sie winkt erst, dann geht sie rechts hinaus; er rückt in die Mitte
f = run(6.0, "santa")
waves = [x for x in f if x[3] == "wave"]
walks = [x for x in f if x[3] == "walk"]
ok(waves and walks and waves[0][0] < walks[0][0], "Abschied: sie winkt, bevor sie geht")
ok(all(b[4] >= a[4] for a, b in zip(f, f[1:])), "Abschied: sie geht nur nach rechts")
sa, mr, st = last()
eq((sa["x"], mr["x"], st["hold"]), (190, OFF["mrs"], 0.0), "Er allein in der Mitte, sie außerhalb")

# Er → sie: er geht links hinaus, sie kommt erst nach seinem Abschied herein und winkt beim Ankommen
f = run(7.0, "mrs")
first_walk_mrs = next(x[0] for x in f if x[3] == "walk")
first_walk_santa = next(x[0] for x in f if x[1] == "walk")
ok(first_walk_mrs > first_walk_santa, "Wechsel: sie kommt erst, als er schon geht")
ok(all(b[2] <= a[2] for a, b in zip(f, f[1:])), "Wechsel: er geht nach links hinaus")
ok(any(x[3] == "wave" and x[4] == 190 for x in f), "Wechsel: sie winkt beim Ankommen")
ok(min(abs(x[2] - x[4]) for x in f) > 60, "Wechsel: die beiden laufen nicht ineinander")
sa, mr, st = last()
eq((sa["x"], mr["x"]), (OFF["santa"], 190), "Sie allein in der Mitte, er außerhalb")

# Wortbeitrag: wer fehlt, kommt herein; beide gehen zur Bank und setzen sich
f = run(6.0, "mrs", talk=True)
ok(any(x[1] == "walk" for x in f), "Bank: er kommt dafür herein")
sa, mr, st = last()
eq((sa["state"], mr["state"], sa["x"], mr["x"], st["bench"]), ("sit", "sit", 178, 220, 1.0),
   "Bank: beide sitzen")

# Ende des Wortbeitrags: aufstehen, er verabschiedet sich (Modus „sie allein“), Bank blendet aus
f = run(6.0, "mrs")
ok(any(x[1] == "wave" for x in f[:15]), "Nach der Bank: er winkt zum Abschied")
sa, mr, st = last()
eq((sa["x"], mr["x"], mr["state"], st["bench"]), (OFF["santa"], 190, "dance", 0.0),
   "Nach der Bank: sie tanzt allein, Bank ausgeblendet")

# Seite verlassen und wieder geöffnet (page_visual setzt _vis_enter nach > 1,5 s Pause): neuer Auftritt
f = run(0.5, "mrs", enter=True)
eq(f[0][4], OFF["mrs"], "Wieder geöffnet: sie kommt erneut herein")
done()
