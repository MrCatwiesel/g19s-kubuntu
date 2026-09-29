"""Senderliste, Textbausteine, Timer mit Alarm, Termindetails, Stoppuhr, Pomodoro."""
from harness import Sim
s = Sim("s08_paket1", macros={"profiles": [{"name": "P", "keys": {"M1": {
    "G1": {"timer": {"mode": "timer", "minutes": 0.05}}, "G2": {"snippets": "*"},
    "G3": {"timer": {"mode": "stopwatch"}}, "G4": {"timer": {"mode": "pomodoro", "work": 0.05, "break": 0.05}}}}}]},
    settings={"pages": ["music", "calendar", "clock"], "start_page": 1, "notifications": {"enabled": False},
              "radio_player": "mpv {url}",
              "stations": [{"name": "Rockantenne", "url": "http://127.0.0.1:9/r1"}, {"name": "Radio BOB!", "url": "http://127.0.0.1:9/r2"},
                           {"name": "Antenne Bayern", "url": "http://127.0.0.1:9/r3"}],
              "snippets": [{"name": "Grußformel", "text": "Mit freundlichen Grüßen", "group": "Büro"},
                           {"name": "Adresse", "text": "Musterstr. 1", "group": "Privat"}, {"name": "", "text": "ab@c.de"}],
              "calendar": {"sources": [{"name": "NC", "url": "http://127.0.0.1:8812/nc/remote.php/dav", "user": "mde@example.de",
                                        "password": "app-pw"}], "days": 30}})
s.key(1.5, "MENU"); s.key(2.0, "DOWN"); s.key(2.5, "OK")
s.gkey(4.0, "G2"); s.key(4.5, "DOWN"); s.key(5.0, "OK")
s.gkey(6.0, "G1"); s.key(7.0, "BACK")
s.key(11.0, "OK")
s.key(12.0, "RIGHT"); s.key(13.0, "DOWN"); s.key(13.5, "DOWN"); s.key(14.0, "UP"); s.key(14.5, "OK"); s.key(15.0, "DOWN"); s.key(15.5, "DOWN"); s.key(16.2, "BACK")
s.key(17.0, "MENU"); s.key(17.6, "BACK")
s.gkey(18.0, "G3"); s.key(20.0, "OK"); s.key(20.8, "DOWN"); s.key(21.2, "BACK")
s.gkey(22.0, "G4"); s.key(29.0, "DOWN")
s.run(30.5)
s.save({"sender": 2.4, "bausteine": 4.9, "timer": 6.9, "badge": 8.5, "alarm": 10.0, "markiert": 14.4, "details": 14.9,
        "details_scroll": 16.1, "kalender": 17.5, "stoppuhr": 19.9, "gestoppt": 20.7, "pomodoro": 23.5, "pause": 27.5})
blinks = [v for _, v in s.backlight if v in ((255, 30, 30), (255, 200, 40))]
s.finish(typed=s.typed(), sounds=s.sounds, blinked=len(blinks) > 3,
         log=s.log_lines(r"^(Radio:|Textbaustein|Timer|Stoppuhr|Pomodoro)"))
