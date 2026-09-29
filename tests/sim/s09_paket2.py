"""Radiowecker, Terminerinnerung, Mikrofon, Song merken, Einschlaftimer, Lieblingsbild, Profilseiten, Sicherung."""
import glob, os, time
from PIL import Image
from harness import Sim, ROOT
mm = os.path.join(ROOT, "state", "micmute")
if os.path.exists(mm): os.remove(mm)
bilder = {}
import io
for i, c in enumerate([(200, 60, 40), (40, 160, 90), (30, 90, 200)]):
    b = io.BytesIO(); Image.new("RGB", (640, 480), c).save(b, "JPEG"); bilder[f"bilder/foto{i + 1}.jpg"] = b.getvalue()
s = Sim("s09_paket2", macros={"profiles": [
    {"name": "Büro", "keys": {"M1": {"G1": {"mic": "toggle"}, "G2": {"media": "remember"}, "G3": {"sleep": 1}}}},
    {"name": "Spiele", "keys": {}, "pages": {"M1": ["hardware"], "M2": ["hardware", "clock"], "M3": ["hardware"]}}]},
    settings={}, files=dict(bilder, **{"bk/.keep": ""}))
import json
json.dump({"layer_pages": {l: ["clock", "music", "slides", "calendar"] for l in ("M1", "M2", "M3")}, "start_page": 0,
           "notifications": {"enabled": False}, "radio_player": "mpv {url}",
           "stations": [{"name": "Rockantenne", "url": "http://127.0.0.1:9/r1"}, {"name": "Radio BOB!", "url": "http://127.0.0.1:9/r2"}],
           "alarm_clock": {"enabled": True, "time": time.strftime("%H:%M"), "days": [0, 1, 2, 3, 4, 5, 6], "station": "http://127.0.0.1:9/r2"},
           "slideshow": {"source": "folder", "folder": s.home + "/bilder", "interval": 60, "shuffle": False},
           "backup": {"enabled": True, "folder": s.home + "/bk", "days": 1, "keep": 3},
           "calendar": {"sources": [{"name": "Arzt", "url": "http://127.0.0.1:8812/bald.ics"}], "days": 7, "remind": 10}},
          open(s.g.SETTINGS_FILE, "w"))
g = s.g
orig = g.MediaWatcher.snapshot
def snap(self):
    r = orig(self)
    info = dict.fromkeys(g.MediaWatcher.FIELDS, "")
    info.update(title="Thunderstruck", artist="AC/DC", player="g19s-radio", status="Playing", station="Radio BOB!",
                length=0, position=0, fetched=time.monotonic())
    return (info,) + tuple(r[1:])
g.MediaWatcher.snapshot = snap
s.gkey(3, "G1"); s.gkey(6, "G2"); s.gkey(8, "G3")
s.key(9.5, "OK"); s.key(10, "RIGHT"); s.key(10.5, "RIGHT"); s.key(13, "BACK"); s.key(15, "DOWN"); s.key(17, "BACK"); s.key(18, "BACK")
s.key(26, "SETTINGS"); s.key(26.5, "DOWN"); s.key(27, "OK")
s.key(30, "SETTINGS"); s.key(30.5, "UP"); s.key(31, "OK")
s.gkey(33, "G1")
s.run(74)
s.save({"erinnerung": 0.9, "wecker": 2.0, "mikro": 3.8, "song": 6.8, "sleep": 8.8, "fussleiste": 9.8, "herz": 14.8,
        "spiele": 28.5, "gutenacht": 70})
st = g.load_state()
s.finish(pages=[p for p, _ in s.page_seq()], mr_led_on=[m for _, m in s.leds if m & 0x10] != [],
         mr_led_end=s.leds[-1][1], songs=[(x["artist"], x["title"], x["source"]) for x in g.load_list(g.SONGS_FILE)],
         favorites=[(f["name"], f["source"]) for f in g.load_list(g.FAVORITES_FILE)],
         backup_files=len(glob.glob(s.home + "/bk/g19s-sicherung-*.tar.gz")), backup_state=bool(st.get("last_backup")),
         log=sorted(s.log_lines(r"^(Terminerinnerung|Radiowecker|Radio:|Mikrofon|Song|Einschlaf|Profil|Lieblingsbild|Automatische|Gute)")))
