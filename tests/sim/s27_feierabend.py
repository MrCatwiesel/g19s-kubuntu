"""Visualisierung „Weihnachten“ mit Option „Feierabend“: die Runde läuft im echten Treiber (Klang vom Fake-
pw-record), Gags folgen aufeinander; solange dem Weihnachtsmann schlecht ist, leuchtet die Tastatur nur grün
statt rot und grün im Takt. Die Runde ist für den Test auf wenige Sekunden verkürzt."""
import os
import time
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.log", "pw-record.still", "pw-record.speech", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
s = Sim("s27_feierabend", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["visual"], "M2": ["visual"], "M3": ["visual"]},
                  "visual": {"style": "xmas", "xmas_auto": False, "xmas": {"party": "on"}}})
g = s.g
STEPS = [("prost", 0.0, 2.0), ("pipi", 2.0, 1.0), ("gruen", 3.0, 4.0), ("noch", 7.0, 20.0)]   # grün ab 5 s
g.party_timeline = lambda length: STEPS                # verkürzte Runde
seen = []
orig = g.VISUAL_RENDERERS["xmas"]


def spy(r, snap, o, color):
    img = orig(r, snap, o, color)
    p = r._vis_states["xmas"].get("party")
    if p is not None:
        seen.append((time.monotonic() - s.t0, p["p"]))
    return img


g.VISUAL_RENDERERS["xmas"] = spy
s.run(8.0)
start = seen[0][0] if seen else 0.0
s.save({"prost": start + 1.0, "uebel": start + 6.0})


def colors(a, b):
    return {c for t, c in s.backlight if start + a <= t < start + b}


def green(c):
    return c[1] > 2 * c[0] and c[1] > 2 * c[2]


s.finish(laeuft=bool(seen) and seen[-1][1] > 4.0,
         vorher_rot_gruen=any(not green(c) for c in colors(0.5, 2.5)) and any(green(c) for c in colors(0.5, 2.5)),
         uebel_nur_gruen=bool(colors(5.4, 6.6)) and all(green(c) for c in colors(5.4, 6.6)),
         log=s.log_lines(r"^Visualisierung: [A-Z][a-z]+$"))
