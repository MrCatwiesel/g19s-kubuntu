"""Seite „Video“: G-Taste spielt die neueste Folge (Radio pausiert), OK hält an und spielt weiter, ▶ spult,
Ende → zurück zur Liste und Radio läuft weiter; Folge aus der Liste wählen; G-Taste nochmal = Stopp;
kaputte Adresse → Fehlermeldung."""
import os
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("ffmpeg.log", "ffmpeg.dauer"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
open(os.path.join(S, "ffmpeg.dauer"), "w").write("8")
s = Sim("s30_video", macros={"profiles": [{"name": "P", "keys": {"M1": {
    "G1": {"video": "latest"}, "G2": {"radio": "http://127.0.0.1:9/r1"}}}}]},
    settings={"start_page": 0, "notifications": {"enabled": False}, "radio_player": "mpv {url}",
              "stations": [{"name": "Rockantenne", "url": "http://127.0.0.1:9/r1"}],
              "layer_pages": {l: ["clock", "video"] for l in ("M1", "M2", "M3")},
              "video": {"feeds": [{"name": "Tagesschau", "url": "http://127.0.0.1:8812/video.xml"}]}})
s.gkey(1.0, "G2")                            # Radio an
s.gkey(2.0, "G1")                            # neueste Folge, Radio pausiert
s.key(4.0, "OK")                             # Pause
s.key(5.5, "OK")                             # weiter
s.key(6.5, "RIGHT")                          # +10 s: hinter dem Ende (8 s) → Folge endet, Radio weiter
s.key(9.0, "DOWN"); s.key(9.3, "DOWN"); s.key(9.6, "OK")   # zweite Folge (erster Druck markiert)
s.gkey(11.0, "G1")                           # G-Taste nochmal: Stopp
s.run(13.0)
s.save({"video_laeuft": 3.6, "video_pause": 5.0, "video_liste": 8.6, "video_folge2": 10.6})
calls = [l.split() for l in open(os.path.join(S, "ffmpeg.log")).read().splitlines()]


def start_of(a):
    ss = float(a[a.index("-ss") + 1])
    return "0" if ss < 0.5 else "über 10" if ss >= 10 else "Mitte"


s.finish(log=s.log_lines(r"^(Video|Radio:)"),
         ffmpeg=[[os.path.basename(a[a.index("-i") + 1]), start_of(a), "pulse" in a, "rawvideo" in a] for a in calls],
         pages=[p for p in s.page_seq()][:6])
