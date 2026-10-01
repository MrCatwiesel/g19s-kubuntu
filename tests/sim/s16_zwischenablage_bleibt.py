"""Einfügen über die Zwischenablage im Standard: Der Text bleibt in der Zwischenablage (mehrfach selbst
einfügbar). Schnell hintereinander gedrückte G-Tasten werden alle eingefügt, nichts wird ignoriert;
mit „zurückholen“ kommt der ursprüngliche Inhalt erst nach dem letzten Druck zurück."""
import json
import os
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("zwischenablage", "zwischenablage.log", "kein_klipper", "kein_wl"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
open(os.path.join(S, "zwischenablage"), "w").write("alt")
s = Sim("s16_zwischenablage_bleibt", macros={"profiles": [{"name": "P", "keys": {"M1": {
    "G1": {"text": "Eins", "paste": "ctrl+v"}, "G2": {"text": "Zwei", "paste": "ctrl+v"}}}}]},
    settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False}})
clip = []
def look(app): clip.append(open(os.path.join(S, "zwischenablage")).read())
def restore_on(app):
    cfg = json.load(open(s.g.SETTINGS_FILE)); cfg["paste_restore"] = True; json.dump(cfg, open(s.g.SETTINGS_FILE, "w"))
s.gkey(1.0, "G1")
s.call(3.0, look)                          # Text bleibt in der Zwischenablage
s.gkey(4.0, "G1"); s.gkey(4.3, "G2")       # schnell hintereinander: beide werden eingefügt
s.call(6.5, look)
s.call(7.0, lambda app: open(os.path.join(S, "zwischenablage"), "w").write("alt"))
s.call(7.2, restore_on)
s.gkey(9.0, "G1"); s.gkey(9.4, "G2"); s.gkey(9.8, "G1")
s.call(10.4, look)                         # noch nicht zurückgeholt
s.run(13.5)
look(None)                                 # nach dem letzten Druck: ursprünglicher Inhalt zurück
s.finish(typed=s.typed(), log=s.log_lines(r"^(G\d+:|Es läuft|Klipper)"), zwischenablage_zu=clip,
         gesetzt=open(os.path.join(S, "zwischenablage.log")).read().splitlines())
