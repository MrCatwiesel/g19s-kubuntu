"""Echte G19s (Protokoll vom 2026-10-02): Ein Paket enthält oft zwei Reports – Report 0x03 (7 Bytes,
Tastatur-Report G1 = F1 …) und direkt dahinter Report 0x02 (4 Bytes) mit Loslassen oder neuem Druck.
Jeder Report im Paket muss ausgewertet werden: G8 (ohne Belegung, F20) viermal gedrückt = viermal F20."""
import evdev
from harness import Sim
s = Sim("s19_reports_geklebt", macros={"profiles": [{"name": "P", "keys": {
    "M1": {"G1": {"text": "a"}}}}]},
    settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False}})
H = bytes.fromhex
# G1 mit Belegung, viermal – genau wie im Protokoll
t = 1.0
for _ in range(4):
    s.report(t, H("02 01 00 40"))
    s.report(t + 0.1, H("03 3a 00 00 00 00 00 02 00 00 40"))     # F1 + G-Tasten los
    s.report(t + 0.2, H("03 00 00 00 00 00 00"))
    t += 0.5
# G8 ohne Belegung, viermal – Drücke 2…4 kleben hinter dem leeren Report 0x03
s.report(t, H("02 80 00 40"))
for _ in range(3):
    s.report(t + 0.1, H("03 41 00 00 00 00 00 02 00 00 40"))     # F8 + G-Tasten los
    s.report(t + 0.2, H("03 00 00 00 00 00 00 02 80 00 40"))     # leer + G8 erneut gedrückt
    t += 0.5
s.report(t + 0.1, H("03 41 00 00 00 00 00 02 00 00 40"))
s.report(t + 0.2, H("03 00 00 00 00 00 00"))
s.run(t + 1.0)
s.finish(sent=[f"{k}{'↓' if v else '↑'}" for k, v in evdev.SENT if v in (0, 1)])
