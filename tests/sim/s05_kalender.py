"""Kalenderauswahl am Display (MENU), Speichern in state.json."""
from harness import Sim
s = Sim("s05_kalender", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"pages": ["calendar", "clock"], "start_page": 6, "notifications": {"enabled": False},
                  "calendar": {"sources": [{"name": "Nextcloud", "url": "http://127.0.0.1:8812/nc/remote.php/dav",
                                            "user": "mde@example.de", "password": "app-pw"}], "days": 30}})
s.key(3.0, "MENU"); s.key(3.6, "DOWN"); s.key(4.0, "DOWN"); s.key(4.5, "OK")
for t in (5.0, 5.3, 5.6, 5.9): s.key(t, "DOWN")
s.key(6.4, "BACK"); s.key(8.0, "RIGHT"); s.key(9.0, "OK"); s.key(10.0, "LEFT"); s.key(11.0, "MENU"); s.key(11.5, "OK"); s.key(12.0, "LEFT")
s.run(14)
s.save({"menue": 3.4, "ausgeblendet": 4.9, "seite": 7.5, "menue2": 11.9, "seite2": 13.5})
s.finish(state=s.g.load_state(), pages=[p for p, _ in s.page_seq()], log=s.log_lines(r"^Kalender sichtbar"))
