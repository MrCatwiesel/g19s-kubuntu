"""Profilmenü über SETTINGS, Wechsel per state.json von außen, Farben je Profil."""
from harness import Sim
s = Sim("s03_profile_neu", macros={"profiles": [
    {"name": "Büro", "keys": {"M1": {"G1": {"text": "a"}}}},
    {"name": "Spiele", "colors": {"M1": [255, 0, 0], "M2": [0, 255, 0], "M3": [0, 0, 255]}, "keys": {"M1": {"G1": {"text": "b"}}}},
    {"name": "Grafik", "keys": {"M1": {"G1": {"combo": "KEY_LEFTCTRL+KEY_Z"}}}}]},
    settings={"notifications": {"enabled": False}})
s.gkey(0.6, "G1")
s.key(1.0, "SETTINGS"); s.key(1.4, "DOWN"); s.key(1.8, "OK"); s.gkey(2.2, "G1")
s.key(2.6, "SETTINGS"); s.key(3.0, "UP"); s.key(3.4, "BACK"); s.gkey(3.8, "G1")
s.call(4.2, lambda sim: sim.g.save_state(profile=2)); s.gkey(7.5, "G1")
s.run(9)
s.save({"profilmenue": 1.3})
s.finish(typed=s.typed(), state=s.g.load_state(), backlight=s.seq(s.backlight), log=s.log_lines(r"^Profil"))
