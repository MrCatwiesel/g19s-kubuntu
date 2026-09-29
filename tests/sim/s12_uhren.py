"""Zifferblatt der Uhr am Display (MENU), gespeichert je Profil und Ebene; Umstellung alter Uhrenseiten."""
import json
from harness import Sim
s = Sim("s12_uhren", macros={"profiles": [
    {"name": "Standard", "keys": {}},
    {"name": "Eigen", "keys": {}, "pages": {"M1": ["clock"], "M2": ["clock_binary", "weather"], "M3": ["clock"]}}]},
    settings={"start_page": 0, "notifications": {"enabled": False},
              "layer_pages": {"M1": ["clock", "hardware"], "M2": ["clock_chrono"], "M3": ["clock"]}})
# M1: Digitaluhr → Bahnhofsuhr, blättern (Seite bleibt „Uhr“), dann Steampunk
s.key(1.0, "MENU"); s.key(1.4, "DOWN"); s.key(1.8, "DOWN"); s.key(2.2, "DOWN"); s.key(2.6, "OK")
s.key(3.2, "RIGHT"); s.key(3.8, "RIGHT")
s.key(4.4, "MENU"); s.key(4.8, "UP"); s.key(5.2, "OK")
# M2: aus der alten Seite „Chronometer“ wurde Uhr mit Zifferblatt Chronometer → Digitaluhr
s.gkey(5.8, "M2"); s.key(6.4, "MENU"); s.key(6.8, "UP"); s.key(7.2, "OK")
# SETTINGS öffnet auf der Uhr direkt die Profilauswahl, BACK schließt das Zifferblatt-Menü
s.key(7.8, "SETTINGS"); s.key(8.2, "BACK"); s.key(8.8, "MENU"); s.key(9.2, "DOWN"); s.key(9.6, "BACK")
# Profil mit eigenen Seiten: Binäruhr (umgestellt) → Bahnhofsuhr
s.call(10.0, lambda sim: sim.g.save_state(profile=1))
s.key(14.0, "MENU"); s.key(14.4, "UP"); s.key(14.8, "OK")
s.run(16)
s.save({"zifferblatt": 2.4, "profil": 8.0, "bahnhof": 3.0})
m = json.load(open(s.g.MACRO_FILE))
s.finish(pages=[[p, prof] for p, prof in s.page_seq()],
         layer_pages=s.g.load_settings()["layer_pages"],
         faces=[p.get("clock") for p in m["profiles"]], own_pages=m["profiles"][1]["pages"],
         log=s.log_lines(r"^(Uhr|Profil)"))
