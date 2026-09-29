"""Albenauswahl der Diashow am Display (MENU), Speichern in settings.json."""
import json
from harness import Sim
s = Sim("s06_alben", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"pages": ["slides", "clock"], "start_page": 4, "notifications": {"enabled": False},
                  "slideshow": {"url": "http://127.0.0.1:8811", "user": "max", "password": "geheim", "albums": [2],
                                "recursive": True, "interval": 60}})
holder = {}
orig = s.g.Slideshow.__init__
def init(self, *a, **k): orig(self, *a, **k); holder["s"] = self
s.g.Slideshow.__init__ = init
s.key(2.0, "MENU"); s.key(3.5, "OK"); s.key(4.2, "DOWN"); s.key(4.8, "OK"); s.key(5.4, "DOWN"); s.key(6.0, "OK"); s.key(7.0, "BACK")
s.key(9.5, "OK")
s.run(11)
s.save({"laden": 2.1, "menue": 3.4, "urlaub": 4.1, "italien_aus": 5.3, "familie": 6.9, "pause": 10.8})
snap = holder["s"].snapshot()
s.finish(albums=json.load(open(s.g.SETTINGS_FILE))["slideshow"]["albums"], count=snap["count"], paused=snap["paused"],
         log=s.log_lines(r"^Diashow"))
