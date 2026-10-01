"""Texte über die Zwischenablage einfügen: G-Taste „Text“ (Strg+V und Strg+Umschalt+V), Textbaustein,
alte Zwischenablage zurückholen (nicht, wenn inzwischen etwas Neues kopiert wurde), Ersatzweg
wl-copy und Tippen, wenn weder Klipper noch wl-copy da sind."""
import os
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("zwischenablage", "zwischenablage.log", "kein_klipper", "kein_wl"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
open(os.path.join(S, "zwischenablage"), "w").write("alt")
TEXT = "Grüße „G19s“ – 😀\nZeile 2"
s = Sim("s15_zwischenablage", macros={"profiles": [{"name": "P", "keys": {"M1": {
    "G1": {"text": TEXT, "paste": "ctrl+v"}, "G2": {"text": "ls -l", "paste": "ctrl+shift+v"},
    "G3": {"snippets": "*"}, "G4": {"text": "ab", "paste": "ctrl+v"}, "G5": {"text": "xy"}}}}]},
    settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False},
              "snippets": [{"name": "Gruß", "text": "Viele Grüße ✓", "paste": "ctrl+v"},
                           {"name": "Getippt", "text": "ok"}]})
s.gkey(1.0, "G1")
s.gkey(3.5, "G2")
s.gkey(6.0, "G3"); s.key(6.5, "OK")                                   # erster Baustein: Zwischenablage
s.gkey(9.0, "G3"); s.key(9.5, "DOWN"); s.key(10.0, "OK")              # zweiter Baustein: getippt
s.gkey(12.0, "G1")
s.call(12.6, lambda app: open(os.path.join(S, "zwischenablage"), "w").write("neu kopiert"))   # Nutzer kopiert etwas
s.call(14.5, lambda app: open(os.path.join(S, "kein_klipper"), "w").close())
s.gkey(15.0, "G4")                                                     # Ersatzweg wl-copy
s.call(17.5, lambda app: open(os.path.join(S, "kein_wl"), "w").close())
s.gkey(18.0, "G4")                                                     # nichts da: tippen
s.gkey(20.0, "G5")                                                     # ohne „paste“: tippen wie bisher
s.run(21.5)
s.save({"bausteine": 6.4})
s.finish(typed=s.typed(), log=s.log_lines(r"^(Textbaustein|Text:|Es läuft)"),
         zwischenablage=open(os.path.join(S, "zwischenablage.log")).read().splitlines(),
         am_ende=open(os.path.join(S, "zwischenablage")).read())
