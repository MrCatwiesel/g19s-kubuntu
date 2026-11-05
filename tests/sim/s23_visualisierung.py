"""Seite „Visualisierung“: hört den Ausgang über (Fake-)pw-record mit, erkennt den Takt, die Tastatur pulsiert,
MENU/SETTINGS kurz = Stilwahl, ► Optionen; Ausgang stumm bzw. Stille = Leerlauf; beim Verlassen endet die Aufnahme, das Licht wird normal."""
import json
import os
import time
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("pw-record.log", "pw-record.still", "sinkmute"):
    if os.path.exists(os.path.join(S, f)):
        os.remove(os.path.join(S, f))
s = Sim("s23_visualisierung", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"start_page": 0, "notifications": {"enabled": False}, "layer_overlay": False,
                  "layer_pages": {"M1": ["clock", "visual"], "M2": ["clock"], "M3": ["clock"]}})
g = s.g
beats = []
orig_feed = g.SoundAnalyzer.feed


def feed(self, samples, now):
    orig_feed(self, samples, now)
    beats.append(self.beats)


g.SoundAnalyzer.feed = feed
states = []                                  # (Zeit, Leerlauf, stumm) je gezeichnetem Bild
orig_snap = g.Renderer._vis_snapshot


def vis_snap(r):
    snap = orig_snap(r)
    states.append((time.monotonic() - s.t0, bool(snap.get("idle")), bool(snap.get("muted"))))
    return snap


g.Renderer._vis_snapshot = vis_snap


def running(sim):
    """Läuft das (Fake-)Aufnahmeprogramm gerade?"""
    for pid in os.listdir("/proc"):
        try:
            if pid.isdigit() and b"bin/pw-record" in open(f"/proc/{pid}/cmdline", "rb").read():
                return True
        except OSError:
            pass
    return False


s.key(1.0, "RIGHT")                                                   # → Visualisierung
s.call(2.8, lambda sim: sim.summary.update(laeuft=running(sim)))
s.key(3.0, "MENU"); s.key(3.4, "DOWN"); s.key(3.8, "RIGHT")            # Stile → Tanzendes Mädchen → Optionen
s.key(4.2, "DOWN"); s.key(4.6, "RIGHT"); s.key(5.0, "BACK"); s.key(5.4, "OK")   # Bühnenlicht aus, übernehmen
s.key(6.0, "SETTINGS"); s.key(6.4, "BACK")                             # SETTINGS kurz = Stile
s.call(6.8, lambda sim: open(os.path.join(S, "sinkmute"), "w").close())         # Ausgang stumm (Musik läuft weiter)
s.call(8.0, lambda sim: (os.remove(os.path.join(S, "sinkmute")),
                         open(os.path.join(S, "pw-record.still"), "w").close()))  # wieder laut, aber Stille
s.key(9.0, "LEFT")                                                    # zurück zur Uhr
s.call(12.6, lambda sim: sim.summary.update(nach_verlassen=running(sim)))
s.run(13.5)
s.save({"musik": 2.5, "stile": 3.6, "stumm": 7.9, "stille": 8.9})


def phase(t0, t1):
    return sorted({("stumm" if m else "leerlauf") if i else "musik" for t, i, m in states if t0 <= t < t1})



light = [(t, c) for t, c in s.backlight]
pulse = {c for t, c in light if 1.8 <= t < 2.9}
st = json.load(open(g.SETTINGS_FILE))
s.finish(takt=max(beats or [0]) >= 4, puls=len(pulse) >= 3, still_volle_farbe=[c for t, c in light if t < 7.95][-1],
         am_ende=light[-1][1], vorher=phase(2.0, 3.0), bei_stumm=phase(7.9, 8.0), bei_stille=phase(8.6, 9.0), stil=st["visual"]["style"], optionen=st["visual"].get("dancer"),
         aufruf_monitor="stream.capture.sink = true" in open(os.path.join(S, "pw-record.log")).read(),
         log=s.log_lines(r"^Visualisierung"))
