"""Profilmenü über SETTINGS (lang gedrückt, die Startseite ist die Uhr), Wechsel per state.json von außen, Farben je Profil."""
from harness import Sim
s = Sim("s03_profile_neu", macros={"profiles": [
    {"name": "Büro", "keys": {"M1": {"G1": {"text": "a"}}}},
    {"name": "Spiele", "colors": {"M1": [255, 0, 0], "M2": [0, 255, 0], "M3": [0, 0, 255]}, "keys": {"M1": {"G1": {"text": "b"}}}},
    {"name": "Grafik", "keys": {"M1": {"G1": {"combo": "KEY_LEFTCTRL+KEY_Z"}}}}]},
    settings={"notifications": {"enabled": False}})
s.gkey(0.6, "G1")
s.key(1.0, "SETTINGS", hold=1.3); s.key(2.6, "DOWN"); s.key(3.0, "OK"); s.gkey(3.4, "G1")
s.key(3.8, "SETTINGS", hold=1.3); s.key(5.4, "UP"); s.key(5.8, "BACK"); s.gkey(6.2, "G1")
s.call(6.6, lambda sim: sim.g.save_state(profile=2)); s.gkey(9.9, "G1")
s.run(11.5)
s.save({"profilmenue": 2.8})
s.finish(typed=s.typed(), state=s.g.load_state(), backlight=s.seq(s.backlight), log=s.log_lines(r"^Profil"))
