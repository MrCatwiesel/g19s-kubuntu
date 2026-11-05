"""Nachtmodus „gedimmt“: die Visualisierung läuft flüssig weiter (nur dunkler), der erste Tastendruck wirkt sofort
(im Modus „Display aus“ weckt er weiterhin nur – das prüft s04 nicht, dort weckt eine G-Taste)."""
import os
import time
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.still", "pw-record.speech", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
hm = time.strftime("%H:%M"); later = time.strftime("%H:%M", time.localtime(time.time() + 3600))
s = Sim("s26_nacht_gedimmt", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["visual", "hardware"], "M2": ["visual"], "M3": ["visual"]},
                  "visual": {"style": "eq", "xmas_auto": False, "fps": "15"},
                  "night": {"enabled": True, "start": hm, "end": later, "mode": "dim", "brightness": 10}})
s.key(4.0, "RIGHT")                                         # erster Druck in der Nacht → sofort nächste Seite
s.run(5.5)
frames = [t for t, _ in s.frames if 1.0 <= t < 4.0]
s.finish(bilder_je_sekunde_gedimmt=round(len(frames) / 3) >= 10, helligkeit=s.seq(s.brightness),
         seiten=[p for p, _ in s.page_seq()])
