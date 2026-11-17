"""Eigene Videolisten: YouTube-Links erkennen, Playlist-Feed, Displayseite, Browser- und Display-Wiedergabe (yt-dlp)."""
import os
import stat
import tempfile
import time
from common import g, eq, ok, done
from PIL import Image

V = "dQw4w9WgXcQ"
for url in (f"https://www.youtube.com/watch?v={V}", f"https://youtu.be/{V}?t=42", f"https://m.youtube.com/watch?feature=x&v={V}",
            f"https://www.youtube.com/shorts/{V}", f"https://www.youtube-nocookie.com/embed/{V}", f"https://youtube.com/live/{V}", V):
    eq(g.youtube_id(url), V, f"YouTube-ID aus {url}")
eq(g.youtube_id("https://example.org/film.mp4"), None, "Keine YouTube-Adresse")
eq(g.youtube_playlist_id("https://www.youtube.com/playlist?list=PLabcdefghijk123"), "PLabcdefghijk123", "Playlist-ID aus Link")
eq(g.youtube_playlist_id(f"https://www.youtube.com/watch?v={V}&list=PLabcdefghijk123&index=2"), "PLabcdefghijk123",
   "Playlist-ID aus Video-Link mit Liste")
eq(g.youtube_playlist_id("https://example.org"), None, "Kein Playlist-Link")
FEED = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
<title>Liste</title><author><name>Ersteller</name></author>
<entry><yt:videoId>aaaaaaaaaaa</yt:videoId><title>Erstes  Video</title><author><name>Kanal A</name></author></entry>
<entry><yt:videoId>bbbbbbbbbbb</yt:videoId><title>Zweites</title><author><name>Kanal B</name></author></entry></feed>'''
eq(g.parse_youtube_feed(FEED), [{"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "title": "Erstes Video", "author": "Kanal A"},
                                {"url": "https://www.youtube.com/watch?v=bbbbbbbbbbb", "title": "Zweites", "author": "Kanal B"}],
   "Playlist-Feed gelesen")

# Einstellungen
s = g.load_settings("/nonexistent")
eq((s["video"]["lists"], s["video"]["youtube"], s["video"]["autonext"]), ([], "browser", True), "Ab Werk: keine Listen, Browser")
raw = {"video": {"feeds": [], "youtube": "display", "lists": [
    {"name": "Musik", "items": [{"url": f"https://www.youtube.com/watch?v={V}", "title": "Lied", "author": "Band"},
                                {"url": "", "title": "leer"}, {"url": "https://example.org/film.mp4", "title": ""},
                                {"url": "https://www.youtube.com/watch?v=ccccccccccc", "title": "Zwei"}]},
    {"name": "", "items": [{"url": "https://youtu.be/ddddddddddd"}]}]}}
cfg = g._clean(raw, strict=False)["video"]
eq([l["name"] for l in cfg["lists"]], ["Musik"], "Liste ohne Namen fällt weg")
rows = g.video_list_items(cfg)["Musik"]
eq([(r["title"], r["youtube"], r["index"]) for r in rows],
   [("Lied", V, 0), ("example.org", None, 1), ("Zwei", "ccccccccccc", 2)], "Listeneinträge: leerer Link fällt weg, Titel ergänzt")
eq(g.video_sources(cfg), [("list", "Musik")], "Quellen: nur die Liste (keine Feeds)")
eq(g.video_sources(dict(cfg, feeds=[{"url": "x"}])), [("feeds", "Podcasts"), ("list", "Musik")], "Quellen: Podcasts zuerst")

# Displayseite: Liste mit Vorschaubild
r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
r.settings["video"] = cfg


class Thumbs:
    def get(self, vid):
        return Image.new("RGB", (80, 45), (200, 30, 30)) if vid == V else None


r.thumbs = Thumbs()
r.video_player = g.VideoPlayer(lambda: {"PATH": "/nonexistent"})
r.sel["video"] = 0
img = r.page_video("M1", {})
eq(r.list_items["video"], rows, "Liste für die Tasten gemerkt")
eq(img.getpixel((40, 50)), (200, 30, 30), "Vorschaubild steht links")

# yt-dlp: Nachbau im eigenen Ordner
tmp = tempfile.mkdtemp()
exe = os.path.join(tmp, "yt-dlp")
with open(exe, "w") as f:
    f.write('#!/bin/sh\nfor a; do last="$a"; done\ncase "$last" in *ccccccccccc*) echo "ERROR: Video unavailable" >&2; exit 1;; esac\n'
            'echo 212.0\necho https://stream.example/v.mp4\n')
os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
env = {"PATH": tmp + ":/usr/bin:/bin", "HOME": "/nonexistent"}
eq(g.ytdlp_path(env), exe, "yt-dlp im PATH gefunden")
eq(g.ytdlp_path({"PATH": "/nonexistent", "HOME": tmp + "/home"}), None, "yt-dlp fehlt")
cmd = g.ytdlp_command(exe, "u")
ok("--no-playlist" in cmd and cmd[cmd.index("-f") + 1].startswith("18/"), "yt-dlp: ein Strom mit Bild und Ton, keine Playlist")
eq(g.ytdlp_resolve(f"https://www.youtube.com/watch?v={V}", env), ("https://stream.example/v.mp4", 212.0), "yt-dlp liefert Strom und Dauer")
try:
    g.ytdlp_resolve("https://www.youtube.com/watch?v=ccccccccccc", env)
    ok(False, "Fehler erwartet")
except RuntimeError as ex:
    ok("Video unavailable" in str(ex), f"yt-dlp-Fehler lesbar: {ex}")

# VideoPlayer: YouTube → yt-dlp → ffmpeg (fehlt hier → Fehlermeldung, aber mit der Strom-Adresse)
vp = g.VideoPlayer(lambda: env)
vp.play_youtube(rows[0])
ok(vp.loading or vp.item.get("page_url"), "Während yt-dlp läuft: Lade-Zustand")
for _ in range(50):
    if not vp.loading:
        break
    time.sleep(0.05)
eq((vp.item["url"], vp.item["page_url"], vp.item["duration"]), ("https://stream.example/v.mp4", rows[0]["url"], 212.0),
   "Strom-Adresse an ffmpeg übergeben, Original gemerkt")
eq((vp.item["list"], vp.item["index"]), ("Musik", 0), "Listenplatz bleibt am Video")
vp.stop()
vp.play_youtube(rows[2])
for _ in range(50):
    if not vp.loading:
        break
    time.sleep(0.05)
ok(vp.ended and "Video unavailable" in (vp.error or ""), "Nicht abspielbares Video: Fehler am Display")


# Tasten: Browser- und Display-Modus
class Launcher:
    def __init__(self, e):
        self.calls, self.e = [], e

    def start(self, argv):
        self.calls.append(argv)
        return True

    def _env(self):
        return self.e


class App:
    def __init__(self, mode, e):
        self.cfg = dict(cfg, youtube=mode)
        self.launcher, self.shown, self.started = Launcher(e), [], []
        self.layer, self.next_draw = "M1", 0
        self.renderer = r

    def settings(self):
        return {"video": self.cfg}

    def show(self, title, lines, color, sec):
        self.shown.append((title, lines))

    def log(self, msg):
        pass


orig = g.video_start
g.video_start = lambda app, item: app.started.append(item["url"])
a = App("browser", env)
g.video_open(a, rows[0])
eq(a.launcher.calls, [["xdg-open", rows[0]["url"]]], "Browser-Modus: OK öffnet den Link")
a = App("display", env)
g.video_open(a, rows[0])
eq((a.launcher.calls, a.started), ([], [rows[0]["url"]]), "Display-Modus: spielt auf dem Display")
a = App("display", {"PATH": "/nonexistent", "HOME": "/nonexistent"})
g.video_open(a, rows[0])
ok(a.launcher.calls == [["xdg-open", rows[0]["url"]]] and "yt-dlp fehlt –" in a.shown[0][1], "Ohne yt-dlp: Hinweis und Browser")
a = App("browser", env)
g.video_open(a, rows[1])
eq((a.launcher.calls, a.started), ([], [rows[1]["url"]]), "Direkte Video-Adresse läuft immer auf dem Display")
eq(g._video_next(App("display", env), dict(rows[0])), rows[1], "Danach das nächste Video der Liste")
eq(g._video_next(App("browser", env), dict(rows[1])), None, "Browser-Videos laufen nicht automatisch weiter")
b = App("display", env)
b.cfg["autonext"] = False
eq(g._video_next(b, dict(rows[0])), None, "Automatisch weiter abschaltbar")
g.video_start = orig
eq(g.entry_label({"video": "list:Musik"}, {}), "Video: Musik", "G-Taste zeigt den Listennamen")
done()
