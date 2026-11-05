"""Visualisierung in der Weihnachtszeit: zeigt automatisch „Weihnachten“ (statt des gewählten Equalizers), die
Tastatur pulsiert rot und grün im Takt; wählt man am Display einen anderen Stil, bleibt dieser (xmas_skip)."""
import json
import os
import time
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.log", "pw-record.still", "pw-record.speech", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
s = Sim("s25_weihnachten", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["visual"], "M2": ["visual"], "M3": ["visual"]}, "visual": {"style": "eq"}})
g = s.g
g.xmas_season = lambda day=None: 2026                  # „heute“ ist Weihnachtszeit
shown = []
for style in ("xmas", "eq", "fireworks"):
    orig = g.VISUAL_RENDERERS[style]

    def spy(r, snap, o, color, orig=orig, style=style):
        shown.append((time.monotonic() - s.t0, style))
        return orig(r, snap, o, color)
    g.VISUAL_RENDERERS[style] = spy
s.key(4.0, "MENU"); s.key(4.4, "UP"); s.key(4.8, "OK")            # Liste steht auf „Weihnachten“ → Feuerwerk
s.run(7.0)
s.save({"weihnachten": 2.5, "feuerwerk": 6.5})


def styles(t0, t1):
    return sorted({st for t, st in shown if t0 <= t < t1})


light = {c for t, c in s.backlight if 1.5 <= t < 3.8}
st = json.load(open(g.SETTINGS_FILE))["visual"]
s.finish(anfang=styles(1.0, 3.8), danach=styles(5.5, 7.0),
         rot=any(c[0] > 2 * c[1] for c in light), gruen=any(c[1] > 2 * c[0] for c in light),
         gewaehlt=st["style"], ausgesetzt=st.get("xmas_skip"), log=s.log_lines(r"^Visualisierung: [A-Z][a-z]+$"))
