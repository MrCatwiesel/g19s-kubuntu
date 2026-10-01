"""Tastatur fehlt beim Start, wird eingesteckt, mit gedrückter G-Taste abgezogen und wieder
eingesteckt: Der Treiber läuft durch, lässt die Taste los, setzt Licht und Bild neu."""
from harness import Sim
s = Sim("s14_abziehen", macros={"profiles": [{"name": "P", "keys": {"M1": {"G2": {"text": "da"}}}}]},
        settings={"start_page": 0, "brightness": 70, "notifications": {"enabled": False},
                  "layer_pages": {l: ["clock"] for l in ("M1", "M2", "M3")}})
s.unplug(0)                                  # beim Start nicht eingesteckt
s.unplug(1.5, plugged=True)
s.gkey(3.0, "G1", hold=4.0)                  # G1 (KDE-Kurzbefehl F13) gedrückt halten …
s.unplug(4.0)                                # … und dabei abziehen
s.unplug(6.0, plugged=True)
s.gkey(8.5, "G2")
s.run(10)
s.save({"wieder_da": 9.5})
import evdev
gaps = [round(b[0] - a[0], 1) for a, b in zip(s.frames, s.frames[1:]) if b[0] - a[0] > 1.5]
s.finish(log=s.log_lines(r"Tastatur|nicht gefunden"),
         f13=[v for k, v in evdev.SENT if k == "KEY_F13"],
         typed=s.typed(),
         brightness=[v for _, v in s.brightness], backlight=s.seq(s.backlight),
         frames_before_plug=sum(1 for f in s.frames if f[0] < 1.5),
         frames_gap_while_unplugged=bool(gaps), frames_after=sum(1 for f in s.frames if f[0] > 6.5) > 0)
