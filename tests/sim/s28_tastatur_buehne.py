"""Tänzerin mit Lichtprogramm „Clubnacht“ und Tastaturbeleuchtung „Farbe des Bühnenlichts“: Die Tastatur übernimmt
die wechselnden Farben der Scheinwerfer statt der Farbe der Ebene."""
import os
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.log", "pw-record.still", "pw-record.speech", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
s = Sim("s28_tastatur_buehne", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["visual"], "M2": ["visual"], "M3": ["visual"]},
                  "visual": {"style": "dancer", "xmas_auto": False, "dancer": {"show": "night", "keys": "stage"}}})
g = s.g
s.run(6.0)
s.save({"clubnacht": 4.0})
layer = tuple(g.PROFILE_COLOR["M1"])
cols = [c for t, c in s.backlight if 2.0 <= t < 6.0 and any(c)]
norm = {tuple(round(x / max(c) * 4) for x in c) for c in cols}
s.finish(farben_wechseln=len(norm) >= 2,
         nicht_ebene=not any(tuple(round(x / max(layer) * 4) for x in layer) == n for n in norm),
         log=s.log_lines(r"^Visualisierung: [A-Z][a-z]+$"))
