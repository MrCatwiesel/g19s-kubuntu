"""Seite „Video“: Video-Feeds lesen, Dauerangaben, ffmpeg-Aufruf, Seitenbilder (Liste, Wiedergabe, Pause)."""
import types
from common import g, eq, ok, done
from PIL import Image

RSS = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:media="http://search.yahoo.com/mrss/">
<channel><title>tagesschau in 100 Sekunden</title>
<item><title>tagesschau in 100 Sekunden, 17:00 Uhr</title>
  <link>https://www.tagesschau.de/multimedia/sendung/tagesschau_in_100_sekunden/video-1.html</link>
  <enclosure url="https://media.tagesschau.de/video/2026/1116/TV-1-webs.mp4" length="9876543" type="video/mp4"/>
  <itunes:duration>00:01:40</itunes:duration><pubDate>Mon, 16 Nov 2026 16:00:00 GMT</pubDate></item>
<item><title><![CDATA[Folge &amp; mehr]]></title>
  <media:content url="https://media.example.org/b.mp4" type="video/mp4" duration="95"/>
  <itunes:duration>1:35</itunes:duration><pubDate>Mon, 16 Nov 2026 13:00:00 +0100</pubDate></item>
<item><title>Nur Audio</title><enclosure url="https://example.org/a.mp3" type="audio/mpeg"/></item>
<item><title>Ohne Anhang</title><link>https://example.org/x</link></item>
</channel></rss>"""

items = g.parse_video_feed(RSS, "Tagesschau")
eq(len(items), 2, "Feed: nur Einträge mit Video")
eq(items[0]["url"], "https://media.tagesschau.de/video/2026/1116/TV-1-webs.mp4", "Feed: enclosure mit video/mp4")
eq(items[0]["duration"], 100.0, "Feed: Dauer 00:01:40")
eq(items[1]["url"], "https://media.example.org/b.mp4", "Feed: media:content")
eq(items[1]["title"], "Folge & mehr", "Feed: Titel aus CDATA, Entitäten aufgelöst")
eq(items[1]["duration"], 95.0, "Feed: Dauer 1:35")
ok(items[0]["time"] is not None and items[0]["source"] == "Tagesschau", "Feed: Zeit und Quelle")
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom-Folge</title>
<link rel="enclosure" type="video/mp4" href="https://example.org/c.mp4"/><updated>2026-11-16T10:00:00Z</updated></entry></feed>"""
eq([i["url"] for i in g.parse_video_feed(ATOM)], ["https://example.org/c.mp4"], "Feed: Atom mit link rel=enclosure")
for text, want in (("1:40", 100.0), ("00:01:40", 100.0), ("100", 100.0), ("", None), ("x", None), ("0", None)):
    eq(g._duration_s(text), want, f"Dauer „{text}“")
eq(g.load_settings("/nonexistent")["video"]["feeds"][0]["url"], g.VIDEO_DEFAULT_FEED,
   "Ab Werk: Tagesschau in 100 Sekunden")

vp = g.VideoPlayer(lambda: {"PATH": "/nonexistent"})
cmd = vp.command("https://example.org/v.mp4", 12.3)
ok(cmd[0] == "ffmpeg" and cmd[cmd.index("-ss") + 1] == "12.3" and cmd.index("-re") < cmd.index("-i"),
   "ffmpeg: Startstelle und Echtzeit vor der Eingabe")
ok("rawvideo" in cmd and "rgb24" in cmd and "pipe:1" in cmd and "pulse" in cmd, "ffmpeg: Bild über Pipe, Ton über PulseAudio")
ok("320:180" in cmd[cmd.index("-vf") + 1] and f"fps={g.VIDEO_FPS}" in cmd[cmd.index("-vf") + 1], "ffmpeg: 320×180, 15 Bilder je Sekunde")
ok(not vp.available(), "ffmpeg fehlt: erkannt")
ok(not vp.play({"url": "https://example.org/v.mp4", "title": "x"}) and "ffmpeg fehlt" in (vp.error or ""),
   "ffmpeg fehlt: verständliche Meldung")

# Seitenbilder
r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
r.settings["video"] = {"feeds": [{"name": "Tagesschau", "url": "http://x"}]}


class Snap:
    def __init__(self, data):
        self.v = (data, None, 1.0)

    def snapshot(self):
        return self.v


r.videos = Snap({"items": items, "errors": []})
r.video_player = g.VideoPlayer(lambda: {"PATH": "/nonexistent"})
img = r.page_video("M1", {})
eq(img.size, (g.WIDTH, g.HEIGHT), "Liste: Bildgröße")
eq(r.list_items["video"], items, "Liste: Einträge für die Tasten gemerkt")
vp = r.video_player
vp.item, vp.frame = items[0], Image.new("RGB", (g.VIDEO_W, g.VIDEO_H), (200, 30, 30))
vp.base, vp.frames = 30.0, 15
img = r.page_video("M1", {})
eq(img.getpixel((160, 90)), (200, 30, 30), "Wiedergabe: Videobild oben")
ok(img.getpixel((8 + int((g.WIDTH - 16) * 31 / 100) - 2, g.VIDEO_H + 24)) != (50, 54, 66), "Wiedergabe: Fortschrittsbalken")
vp.paused = True
img = r.page_video("M1", {})
eq(img.getpixel((g.WIDTH // 2 - 7, 90)), (255, 255, 255), "Pause: Pausezeichen (linker Balken)")
eq(round(vp.position(), 2), 31.0, "Position: Startstelle + Bilder / 15")

# Spulen bleibt innerhalb der Folge, im Pausenzustand ohne ffmpeg-Start
vp.seek(500)
eq(round(vp.position(), 1), 99.0, "Spulen vor: höchstens bis kurz vor das Ende")
vp.seek(-500)
eq(vp.position(), 0.0, "Spulen zurück: nicht vor den Anfang")
vp.stop()
ok(vp.item is None and vp.frame is None, "Stopp: zurück zur Liste")
eq(g.entry_label({"video": "latest"}), "Video", "G-Taste: Beschriftung")
eq(g.entry_type({"video": "latest"}), "video", "G-Taste: Art „video“")
done()
