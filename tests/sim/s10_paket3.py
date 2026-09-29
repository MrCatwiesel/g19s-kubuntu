"""Nachrichten, Unwetter (mit Einblendung), Netzwerk, Updates."""
import os
os.environ["G19S_ALERTS_URL"] = "http://127.0.0.1:8812/alerts"
from harness import Sim
s = Sim("s10_paket3", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"layer_pages": {l: ["news", "warnings", "network", "updates"] for l in ("M1", "M2", "M3")}, "start_page": 8,
                  "notifications": {"enabled": False}, "weather": {"name": "Leipzig", "lat": 51.34, "lon": 12.37},
                  "news": {"feeds": [{"name": "tagesschau", "url": "http://127.0.0.1:8812/rss.xml"}, {"name": "heise", "url": "http://127.0.0.1:8812/atom.xml"},
                                     {"name": "kaputt", "url": "http://127.0.0.1:8812/gibtsnicht.xml"}]},
                  "network": {"hosts": [{"name": "Router", "host": "gateway"}, {"name": "NAS", "host": "10.0.0.99"},
                                        {"name": "Piwigo", "host": "127.0.0.1:8811"}, {"name": "Internet", "host": "1.1.1.1"}]}})
s.key(3.5, "OK")
s.key(5, "DOWN"); s.key(5.5, "DOWN"); s.key(6, "OK")
s.key(8, "RIGHT"); s.key(9, "DOWN"); s.key(9.5, "OK"); s.key(11, "DOWN"); s.key(12, "BACK")
s.key(13, "RIGHT"); s.key(15, "RIGHT"); s.key(17, "OK")
s.run(19)
s.save({"warnung": 3.0, "news": 4.8, "news_sel": 5.9, "unwetter": 8.8, "details": 10.8, "netz": 14.8, "updates": 16.8})
s.finish(opened=s.opened, pages=[p for p, _ in s.page_seq()], log=s.log_lines(r"^(Markante|Nachricht|Unwetter)"))
