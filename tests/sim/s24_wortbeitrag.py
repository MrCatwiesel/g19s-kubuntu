"""Visualisierung „Tanzendes Mädchen“: Sprache statt Musik (Nachrichten, Moderation) → Wortbeitrag, die Tänzerin
langweilt sich, die Tastatur pulsiert nicht; Musik zurück → tanzt wieder; Stichwort im Sendertitel → ebenfalls gelangweilt."""
import os
import time
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.log", "pw-record.still", "pw-record.speech", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
s = Sim("s24_wortbeitrag", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["visual"], "M2": ["visual"], "M3": ["visual"]},
                  "visual": {"style": "dancer"}})
g = s.g
title = {"title": "Song", "artist": "Band"}
orig = g.MediaWatcher.snapshot


def snap(self):
    r = orig(self)
    info = dict.fromkeys(g.MediaWatcher.FIELDS, "")
    info.update(title=title["title"], artist=title["artist"], player="g19s-radio", status="Playing",
                length=0, position=0, fetched=time.monotonic())
    return (info,) + tuple(r[1:])


g.MediaWatcher.snapshot = snap
moods = []                                   # (Zeit, Haltung) – None = tanzt
orig_pose = g._bored_pose


def bored_pose(b):
    p = orig_pose(b)
    moods.append((time.monotonic() - s.t0, p))
    return p


g._bored_pose = bored_pose
orig_dancer = g.VISUAL_RENDERERS["dancer"]


def dancer(r, snap_, o, color):
    if not snap_.get("talk"):
        moods.append((time.monotonic() - s.t0, None))
    return orig_dancer(r, snap_, o, color)


g.VISUAL_RENDERERS["dancer"] = dancer
s.call(3.0, lambda sim: open(os.path.join(S, "pw-record.speech"), "w").close())          # Sprache
s.call(13.0, lambda sim: os.remove(os.path.join(S, "pw-record.speech")))                  # Musik
s.call(22.5, lambda sim: title.update(title="BOB Nachrichten", artist="Radio Bob"))      # Sender meldet Nachrichten
s.run(25.6)
s.save({"tanzt": 2.5, "gelangweilt": 10.5, "nachrichten": 25.0})


def mood(t0, t1):
    return sorted({m or "tanzt" for t, m in moods if t0 <= t < t1}, key=str)


light = [(t, c) for t, c in s.backlight]
s.finish(anfang=mood(1.5, 3.0), sprache=mood(9.5, 12.5), musik=mood(20.0, 22.4), titel=mood(23.5, 25.4),
         puls_bei_musik=len({c for t, c in light if 1.5 <= t < 3.0}) >= 3,
         ruhig_bei_sprache=len({c for t, c in light if 9.5 <= t < 12.5}) <= 1,
         ruhig_bei_titel=len({c for t, c in light if 23.6 <= t < 25.4}) <= 1,
         log=[l.split(" (")[0] for l in s.log_lines(r"^Visualisierung: (Wortbeitrag|Musik)")])
