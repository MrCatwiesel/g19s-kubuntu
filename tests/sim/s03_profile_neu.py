"""Profilmenü über SETTINGS (lang gedrückt, die Startseite ist die Uhr), Wechsel per state.json von außen, Farben je Profil."""
from harness import Sim
s = Sim("s03_profile_neu", macros={"profiles": [
    {"name": "Büro", "keys": {"M1": {"G1": {"text": "a"}}}},
    {"name": "Spiele", "colors": {"M1": [255, 0, 0], "M2": [0, 255, 0], "M3": [0, 0, 255]}, "keys": {"M1": {"G1": {"text": "b"}}}},
    {"name": "Grafik", "keys": {"M1": {"G1": {"combo": "KEY_LEFTCTRL+KEY_Z"}}}}]},
    settings={"notifications": {"enabled": False}})
s.gkey(0.6, "G1")
s.key(1.0, "SETTINGS", hold=0.8); s.key(2.0, "DOWN"); s.key(2.4, "OK"); s.gkey(2.8, "G1")
s.key(3.2, "SETTINGS", hold=0.8); s.key(4.2, "UP"); s.key(4.6, "BACK"); s.gkey(5.0, "G1")
s.call(5.4, lambda sim: sim.g.save_state(profile=2)); s.gkey(7.5, "G1")
s.run(9)
s.save({"profilmenue": 2.2})
s.finish(typed=s.typed(), state=s.g.load_state(), backlight=s.seq(s.backlight), log=s.log_lines(r"^Profil"))
