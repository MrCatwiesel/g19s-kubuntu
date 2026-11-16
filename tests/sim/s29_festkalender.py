"""Festkalender: Hat heute jemand aus der Geburtstagsliste Geburtstag, zeigt die Visualisierung automatisch die
„Überraschungsparty“ (statt des gewählten Equalizers); die Gäste verstecken sich im Dunkeln, die Tastatur ist fast
aus. Wählt man am Display einen anderen Stil (hier die Kellertreppe), gilt er für diesen Tag (fest_skip); die
Tastatur leuchtet dann warm wie die Glühbirne."""
import datetime
import json
import os
import time
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.log", "pw-record.still", "pw-record.speech", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
s = Sim("s29_festkalender", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["visual"], "M2": ["visual"], "M3": ["visual"]},
                  "visual": {"style": "eq", "party": {"birthdays": [
                      {"name": "Max", "day": 1, "month": 10, "year": 1974}]}}})
g = s.g
g.fest_today = lambda: datetime.date(2026, 10, 1)      # „heute“ hat Max Geburtstag
g.xmas_season = lambda day=None: None
shown = []
for style in ("party", "eq", "cellar"):
    orig = g.VISUAL_RENDERERS[style]

    def spy(r, snap, o, color, orig=orig, style=style):
        shown.append((time.monotonic() - s.t0, style))
        return orig(r, snap, o, color)
    g.VISUAL_RENDERERS[style] = spy
s.key(4.0, "MENU"); s.key(4.4, "DOWN"); s.key(4.8, "OK")         # Liste steht auf der Party → Kellertreppe
s.run(7.5)
s.save({"party": 2.5, "keller": 7.0})


def styles(t0, t1):
    return sorted({st for t, st in shown if t0 <= t < t1})


hidden = [c for t, c in s.backlight if t <= 3.0][-1:]                # Farbe, die bei 3 s leuchtet
bulb = [c for t, c in s.backlight if 5.5 <= t < 7.5]
st = json.load(open(g.SETTINGS_FILE))["visual"]

s.finish(anfang=styles(1.0, 3.8), danach=styles(5.5, 7.5),
         dunkel=bool(hidden) and all(max(c) <= 40 for c in hidden),
         warm=bool(bulb) and any(c[0] > c[1] > c[2] for c in bulb),
         gewaehlt=st["style"], ausgesetzt=st.get("fest_skip"),
         log=s.log_lines(r"^Visualisierung: [A-ZÄÖÜ][a-zäöü]+$"))
