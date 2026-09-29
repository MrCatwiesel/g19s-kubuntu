"""Altes Format (nur M1/M2/M3) wird als „Profil 1“ gelesen und nicht umgeschrieben."""
import json
from harness import Sim
s = Sim("s02_profile_alt", macros={"M1": {"G1": {"text": "a"}, "G2": {"open": "https://x.de"}}},
        settings={"notifications": {"enabled": False}})
s.gkey(0.6, "G1")
s.run(2.5)
s.finish(typed=s.typed(), file_keys=sorted(json.load(open(s.g.MACRO_FILE))), state=s.g.load_state(),
         backlight=sorted({tuple(v) for _, v in s.backlight}))
