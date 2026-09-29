"""Nachtmodus (Dimmen, Aufwecken), Bildschirmschoner, Lautstärke, Benachrichtigungen mit Ausnahmen."""
import os, time
from harness import Sim, ROOT
hm = time.strftime("%H:%M"); later = time.strftime("%H:%M", time.localtime(time.time() + 3600))
for f in ("vol", "wpctl.log"):
    p = os.path.join(ROOT, "state", f)
    if os.path.exists(p): os.remove(p)
s = Sim("s04_nacht_schoner", macros={"profiles": [{"name": "P", "keys": {"M1": {"G1": {"volume": "up"}, "G2": {"volume": "down"}}}}]},
        settings={"pages": ["clock", "hardware", "weather"], "start_page": 7,
                  "notifications": {"enabled": True, "seconds": 2, "ignore": "discover"},
                  "night": {"enabled": True, "start": hm, "end": later, "mode": "dim", "brightness": 7, "backlight_off": True},
                  "screensaver": {"enabled": True, "minutes": 0.1, "page": "clock"}})
s.gkey(1.0, "G1", 0.2); s.key(2.5, "RIGHT", 0.2); s.key(3.0, "RIGHT", 0.2); s.gkey(3.6, "G1", 0.2); s.gkey(4.0, "G2", 0.2)
s.key(4.5, "RIGHT", 0.2); s.key(13.0, "RIGHT", 0.2)
s.run(16)
s.save({"lautstaerke": 1.8, "benachrichtigung": 6.0})
s.finish(pages=[p for p, _ in s.page_seq()], brightness=s.seq(s.brightness), backlight=s.seq(s.backlight),
         volume=open(os.path.join(ROOT, "state", "wpctl.log")).read().split("\n")[:3],
         log=s.log_lines(r"^(Benachrichtigung|Nachtmodus)"))
