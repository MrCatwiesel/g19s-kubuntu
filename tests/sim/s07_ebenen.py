"""Displayseiten je Ebene M1/M2/M3, zuletzt gezeigte Seite je Ebene."""
from harness import Sim
s = Sim("s07_ebenen", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False},
                  "layer_pages": {"M1": ["clock", "calendar", "hardware"], "M2": ["hardware", "weather"], "M3": ["clock"]}})
s.key(1.0, "RIGHT"); s.gkey(2.0, "M2"); s.key(3.0, "RIGHT"); s.gkey(4.0, "M1"); s.gkey(5.0, "M3"); s.key(6.0, "RIGHT"); s.gkey(7.0, "M2"); s.gkey(8.0, "M1")
s.run(9)
vis = [[p, prof] for p, prof in s.page_seq()]
s.finish(pages=vis, loaded=s.g.load_settings()["pages"])
