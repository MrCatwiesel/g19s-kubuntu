"""Textbausteine auf G-Tasten: ein einzelner Baustein wird bei jedem Druck sofort eingefügt (ohne Liste),
eine Liste mit „offen lassen“ bleibt nach OK offen (mehrmals OK, anderen Baustein wählen, BACK schließt),
ein gelöschter Baustein meldet sich auf dem Display."""
import os
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("zwischenablage", "zwischenablage.log", "kein_klipper", "kein_wl"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
open(os.path.join(S, "zwischenablage"), "w").write("alt")
s = Sim("s17_textbaustein_direkt", macros={"profiles": [{"name": "P", "keys": {"M1": {
    "G1": {"snippets": "*", "snippet": "Gruß"}, "G2": {"snippets": "*", "snippet": "ok"},
    "G3": {"snippets": "*", "keep_open": True}, "G4": {"snippets": "*", "snippet": "Gelöscht"}}}}]},
    settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False},
              "snippets": [{"name": "Gruß", "text": "Viele Grüße", "paste": "ctrl+v"},
                           {"name": "", "text": "ok\nzweite Zeile"},
                           {"name": "Kurz", "text": "K", "paste": "ctrl+v"}]})
s.gkey(1.0, "G1"); s.gkey(2.5, "G1"); s.gkey(4.0, "G1")              # jeder Druck fügt ein
s.gkey(5.5, "G2")                                                    # ohne Namen (erste Zeile), getippt
s.gkey(8.0, "G3"); s.key(8.5, "OK"); s.key(10.0, "OK")               # Liste bleibt offen: zweimal Gruß
s.key(11.5, "DOWN"); s.key(11.7, "DOWN"); s.key(12.0, "OK")          # dann Kurz
s.key(13.6, "BACK")                                                  # schließt die Liste
s.gkey(15.0, "G4")                                                   # gelöschter Baustein
s.run(16.5)
s.save({"liste_offen": 11.0, "fehlt": 15.5})
s.finish(typed=s.typed(), log=s.log_lines(r"^(Textbaustein|G\d+[ :]|Es läuft|Klipper)"),
         gesetzt=open(os.path.join(S, "zwischenablage.log")).read().splitlines())
