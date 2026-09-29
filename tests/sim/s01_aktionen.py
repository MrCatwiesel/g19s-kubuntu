"""Altes Makroformat, Text, Tastenkombination, Radio an/aus, Helligkeit/Farben aus settings.json."""
from harness import Sim
s = Sim("s01_aktionen",
        macros={"M1": {"G1": {"text": "Hi!"}, "G2": {"combo": "KEY_LEFTCTRL+KEY_C"},
                       "G3": {"radio": "https://stream.rockantenne.de/rockantenne/stream/aacp"},
                       "G4": {"radio": "stop"}, "G5": {"media": "play-pause"}, "G6": {"name": "nur Name"}}},
        settings={"colors": {"M1": [10, 20, 30]}, "brightness": 50, "radio_player": "sleep 60 # {url}", "start_page": 1,
                  "notifications": {"enabled": False}})
radio = []
orig = s.g.RadioManager.play
def spy(self, st, cmd, stations=None):
    r = orig(self, st, cmd, stations); radio.append((self.current() or {}).get("url")); return r
s.g.RadioManager.play = spy
t = 0.5
for k in ["G1", "G2", "G3", "G6", "G4"]:
    s.gkey(t, k, hold=0.3); t += 0.6
s.run(4.5)
s.finish(typed=s.typed(), backlight_first=list(s.backlight[0][1]), brightness=[v for _, v in s.brightness],
         radio=radio, pages=s.page_seq()[:1], log=s.log_lines(r"^(Radio|Makros geladen|Einstellungen)"))
