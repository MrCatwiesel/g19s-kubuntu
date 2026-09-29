"""Makroaufnahme mit MR (speichern, löschen, abbrechen) und F-Tasten mit Strg/Alt in M2/M3."""
import json
from harness import Sim
s = Sim("s11_aufnahme", macros={"profiles": [{"name": "P", "keys": {"M1": {"G2": {"name": "Alt", "text": "x"}}}}]},
        settings={"notifications": {"enabled": False}, "pages": ["clock"]})


class FakeRecorder:
    """Ersatz für die echte Aufnahme (die liest /dev/input): liefert zwei Tastendrücke."""
    runs = []

    def __init__(self):
        self.keycount, self.error = 0, ""

    def start(self):
        FakeRecorder.runs.append(self)
        return True

    def poll(self):
        if len(FakeRecorder.runs) == 1 and self.keycount < 2:
            self.keycount += 1

    def stop(self):
        return [[0, "KEY_A", "down"], [30, "KEY_A", "up"], [20, "KEY_B", "down"], [30, "KEY_B", "up"]][: self.keycount * 2]


s.g.Recorder = FakeRecorder
s.gkey(1.0, "MR"); s.gkey(1.5, "G1"); s.gkey(2.5, "MR")              # aufnehmen → G1 = 2 Tastendrücke
s.gkey(3.5, "MR"); s.gkey(4.0, "G2"); s.gkey(4.5, "MR")              # nichts tippen → G2 gelöscht
s.gkey(5.5, "MR"); s.gkey(6.0, "MR")                                 # abbrechen
s.gkey(7.0, "M2"); s.gkey(7.5, "G3"); s.gkey(8.0, "M3"); s.gkey(8.5, "G4"); s.gkey(9.0, "M1"); s.gkey(9.5, "G1")
s.run(11)
s.save({"waehlen": 1.3, "aufnahme": 2.2, "gespeichert": 2.8})
import evdev
events = [[k, v] for k, v in evdev.SENT]
s.finish(macros=json.load(open(s.g.MACRO_FILE))["profiles"][0]["keys"], events=events,
         leds=s.seq(s.leds), backlight=s.seq(s.backlight), log=s.log_lines(r"^(Makro|Aufnahme)"))
