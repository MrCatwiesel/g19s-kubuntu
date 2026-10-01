"""Echte G19s: Das Loslassen einer G-Taste fehlt oft in Report 0x02 – beim nächsten Druck kommt derselbe
Report noch einmal (Byte 3 = 0x40), oder das Loslassen kommt nur als Report 0x03 ohne Taste.
Jeder Druck muss trotzdem genau einmal auslösen; eine Taste ohne Belegung (F13) wird sauber losgelassen."""
import evdev
from harness import Sim
s = Sim("s18_g19s_loslassen", macros={"profiles": [{"name": "P", "keys": {
    "M1": {"G1": {"text": "a"}}, "M2": {"G1": {"text": "b"}}}}]},
    settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False}})
G1, G2, M1, M2 = [2, 1, 0, 0x40], [2, 2, 0, 0x40], [2, 0, 0x10, 0x40], [2, 0, 0x20, 0x40]
NONE, KBD_UP = [2, 0, 0, 0x40], [3, 0, 0, 0, 0, 0, 0, 0, 0]
s.report(1.0, G1); s.report(1.5, G1); s.report(2.0, G1)          # dreimal G1, Loslassen nie gemeldet
s.report(2.5, M2); s.report(2.6, NONE)                           # M2 (Loslassen wird gemeldet)
s.report(3.0, G1); s.report(3.1, KBD_UP); s.report(3.5, G1)       # Loslassen nur als Report 0x03
s.report(4.0, M1); s.report(4.1, NONE)
s.report(4.5, G2); s.report(5.0, G2); s.report(5.1, KBD_UP)       # G2 ohne Belegung: F14 zweimal, dann los
s.gkey(6.0, "G1"); s.gkey(6.5, "G1")                              # sauber gemeldet (wie bisher)
s.run(7.5)
s.finish(sent=[f"{k}{'↓' if v else '↑'}" for k, v in evdev.SENT if v in (0, 1)])
