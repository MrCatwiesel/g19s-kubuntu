"""Videos: Video-Podcast-Feeds (RSS mit Video-Anhang) abrufen und mit ffmpeg auf dem Display abspielen.
Das Bild kommt als Rohdaten (RGB, 320×180, 15 Bilder je Sekunde) über eine Pipe, der Ton geht im selben ffmpeg-Aufruf
an PipeWire/PulseAudio – so bleiben Bild und Ton beisammen, ohne dass ein Fenster aufgeht.

Eigene Videolisten (video.lists): YouTube-Links und direkte Video-Adressen. YouTube-Videos öffnen je nach video.youtube
im Browser („browser“) oder laufen auf dem Display („display“): yt-dlp ermittelt dafür die Adresse des Videostroms."""

VIDEO_W, VIDEO_H, VIDEO_FPS = 320, 180, 15
VIDEO_SEEK = 10                 # Sekunden je Druck auf ◀ / ▶


def _duration_s(text):
    """itunes:duration „1:40“, „00:01:40“ oder „100“ → Sekunden (None, wenn unbekannt)."""
    parts = str(text or "").strip().split(":")
    try:
        nums = [float(p) for p in parts if p != ""]
    except ValueError:
        return None
    if not nums or len(nums) > 3:
        return None
    sec = 0.0
    for n in nums:
        sec = sec * 60 + n
    return sec if sec > 0 else None


def parse_video_feed(raw, source=""):
    """RSS/Atom mit Video-Anhang (enclosure bzw. media:content/link rel=enclosure):
    [{title, url, time, duration, source}] – Einträge ohne Video werden übersprungen."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(raw)
    local = lambda tag: tag.rsplit("}", 1)[-1]
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title, url, when, dur = "", "", None, None
        for ch in el.iter():
            name = local(ch.tag)
            if name == "title" and not title:
                import html
                title = re.sub(r"<[^>]+>", "", html.unescape("".join(ch.itertext()))).strip()
            elif name in ("enclosure", "content", "link") and not url:
                href = ch.get("url") or ch.get("href") or ""
                kind = (ch.get("type") or "").lower()
                if href and (kind.startswith("video/") or (name == "link" and ch.get("rel") == "enclosure")
                             or (not kind and re.search(r"\.(mp4|m4v|webm|mov)(\?|$)", href, re.I))):
                    url = href
            elif name == "duration" and dur is None:
                dur = _duration_s(ch.text)
            elif name in ("pubDate", "date", "updated", "published") and ch.text and when is None:
                when = _feed_time(ch.text)
        if title and url.startswith(("http://", "https://")):
            out.append({"title": " ".join(title.split()), "url": url, "time": when, "duration": dur, "source": source})
    return out


def _feed_time(text):
    import email.utils
    import datetime as dt
    t = text.strip()
    try:
        when = email.utils.parsedate_to_datetime(t)
        return when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError, IndexError):
        try:
            when = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
            return when if when.tzinfo else when.astimezone()
        except ValueError:
            return None


_YT_ID = re.compile(r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?(?:[^#]*&)?v=|embed/|shorts/|live/|v/))"
                    r"([A-Za-z0-9_-]{11})")
YOUTUBE_BASE = os.environ.get("G19S_YOUTUBE_URL", "https://www.youtube.com")    # Tests: Nachbau
YOUTUBE_FEED = YOUTUBE_BASE + "/feeds/videos.xml?playlist_id={}"
YOUTUBE_OEMBED = YOUTUBE_BASE + "/oembed?format=json&url=https://www.youtube.com/watch%3Fv%3D{}"
YTDLP_FORMAT = "18/best[height<=480][vcodec!=none][acodec!=none]/best"   # ein Strom mit Bild und Ton


def youtube_id(url):
    """Video-ID aus einem YouTube-Link (watch, youtu.be, shorts, embed, live) oder einer nackten ID; sonst None."""
    text = str(url or "").strip()
    m = _YT_ID.search(text)
    if m:
        return m.group(1)
    return text if re.fullmatch(r"[A-Za-z0-9_-]{11}", text) else None


def youtube_playlist_id(url):
    text = str(url or "").strip()
    m = re.search(r"[?&]list=([A-Za-z0-9_-]{10,})", text)
    if m:
        return m.group(1)
    return text if re.fullmatch(r"(?:PL|UU|OL|FL|LL|RD)[A-Za-z0-9_-]{10,}", text) else None


def youtube_url(vid):
    return f"https://www.youtube.com/watch?v={vid}"


def youtube_thumb_url(vid):
    return f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"


def youtube_lookup(url):
    """Titel und Kanal eines YouTube-Videos über die offizielle oEmbed-Schnittstelle (ohne Schlüssel)."""
    vid = youtube_id(url)
    if vid is None:
        raise ValueError("Kein YouTube-Link")
    data = json.loads(http_get(YOUTUBE_OEMBED.format(vid), timeout=15))
    return {"url": youtube_url(vid), "title": " ".join(str(data.get("title") or vid).split())[:150],
            "author": str(data.get("author_name") or "")[:80]}


def parse_youtube_feed(raw):
    """Atom-Feed einer YouTube-Playlist → [{url, title, author}] (YouTube liefert die neuesten 15)."""
    import xml.etree.ElementTree as ET
    local = lambda tag: tag.rsplit("}", 1)[-1]
    out = []
    for el in ET.fromstring(raw).iter():
        if local(el.tag) != "entry":
            continue
        vid, title, author = None, "", ""
        for ch in el.iter():
            name = local(ch.tag)
            if name == "videoId" and ch.text:
                vid = ch.text.strip()
            elif name == "title" and not title and ch.text:
                title = " ".join(ch.text.split())
            elif name == "name" and not author and ch.text:
                author = ch.text.strip()
        if vid and youtube_id(vid):
            out.append({"url": youtube_url(vid), "title": (title or vid)[:150], "author": author[:80]})
    return out


def video_list_items(cfg):
    """Einträge der eigenen Listen für die Displayseite: {name: [{title, url, author, source, youtube, list, index}]}."""
    out = {}
    for lst in cfg.get("lists") or []:
        name = str(lst.get("name") or "").strip()
        if not name:
            continue
        rows = []
        for i, e in enumerate(lst.get("items") or []):
            url = str(e.get("url") or "").strip()
            vid = youtube_id(url)
            if not vid and not url.startswith(("http://", "https://")):
                continue
            rows.append({"title": str(e.get("title") or "").strip() or (vid or domain_of(url)), "url": url,
                         "author": str(e.get("author") or ""), "source": name, "youtube": vid, "list": name,
                         "index": len(rows), "time": None, "duration": None})
        if rows:
            out[name] = rows
    return out


def ytdlp_path(env):
    """yt-dlp im PATH der Sitzung oder in ~/.local/bin (pipx/pip --user); None, wenn nicht installiert."""
    path = (env or {}).get("PATH") or os.environ.get("PATH", "")
    home = (env or {}).get("HOME") or os.path.expanduser("~")
    return shutil.which("yt-dlp", path=path + os.pathsep + os.path.join(home, ".local", "bin"))


def ytdlp_command(exe, url):
    return [exe, "-f", YTDLP_FORMAT, "--no-playlist", "--no-warnings", "--print", "duration", "--print", "urls", url]


def ytdlp_resolve(url, env, timeout=45):
    """(Adresse des Videostroms, Dauer in Sekunden oder None) über yt-dlp. RuntimeError mit lesbarer Meldung."""
    exe = ytdlp_path(env)
    if exe is None:
        raise RuntimeError("yt-dlp fehlt – siehe Anleitung (pipx install yt-dlp)")
    try:
        res = subprocess.run(ytdlp_command(exe, url), capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise RuntimeError("yt-dlp antwortet nicht")
    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    if res.returncode or len(lines) < 2 or not lines[1].startswith("http"):
        err = [ln for ln in res.stderr.splitlines() if ln.strip()]
        raise RuntimeError(("yt-dlp: " + err[-1].replace("ERROR: ", "")) [:110] if err else "yt-dlp fand kein Video")
    try:
        dur = float(lines[0])
    except ValueError:
        dur = None
    return lines[1], dur


class ThumbCache:
    """Vorschaubilder (80×45) der YouTube-Videos: werden einmal im Hintergrund geladen und gemerkt."""

    def __init__(self, log=print):
        self.log, self.lock, self.imgs, self.busy = log, threading.Lock(), {}, set()

    def get(self, vid):
        with self.lock:
            if vid in self.imgs or vid in self.busy:
                return self.imgs.get(vid)
            if len(self.busy) >= 3:
                return None
            self.busy.add(vid)
        threading.Thread(target=self._load, args=(vid,), daemon=True).start()
        return None

    def _load(self, vid):
        import io
        img = None
        try:
            src = Image.open(io.BytesIO(http_get(youtube_thumb_url(vid), timeout=15))).convert("RGB")
            if src.size == (320, 180):
                img = src.reduce(4)                 # ganzzahlig verkleinern – kein resize (Kubuntu-Pillow)
            else:
                src.thumbnail((80, 45), Image.LANCZOS)
                img = src
        except Exception as ex:                 # Netz/Bild: ohne Vorschau weiter
            self.log(f"Video: Vorschaubild {vid}: {err_text(ex)}")
        with self.lock:
            self.busy.discard(vid)
            self.imgs[vid] = img


def feed_problem(url, raw=None):
    """Verständlicher Grund, warum eine Adresse kein Video-Feed ist (sonst None): YouTube-Links gehören in eine eigene
    Videoliste, eine Webseite (HTML) ist kein RSS-Feed."""
    if youtube_id(url) or youtube_playlist_id(url):
        return "Das ist ein YouTube-Link, kein Podcast-Feed – bitte unter „Eigene Videolisten“ eintragen"
    head = (raw or b"")[:2000].lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html")) or b"<html" in head:
        return "Das ist eine Webseite, kein Video-Feed – gesucht ist die Adresse des RSS-Feeds (z. B. „…/podcast.xml“)"
    return None


def read_video_feed(url, name=""):
    """Feed abrufen und lesen; bei YouTube-Links und Webseiten mit verständlicher Meldung (ValueError)."""
    problem = feed_problem(url)
    if problem:
        raise ValueError(problem)
    raw = http_get(url, timeout=20)
    try:
        return parse_video_feed(raw, name)
    except ET.ParseError:
        raise ValueError(feed_problem(url, raw) or "Kein lesbarer RSS-/Atom-Feed")


class VideoPoller(Poller):
    """Ruft die Video-Feeds stündlich ab – solange die Seite „Video“ eingeschaltet ist oder eine G-Taste
    ein Video angefordert hat (wanted)."""

    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 3600, log)
        self.wanted = False

    def cfg(self):
        return self.get_settings().get("video") or {}

    def enabled(self):
        return bool(self.cfg().get("feeds")) and (self.wanted or "video" in (self.get_settings().get("pages") or []))

    def signature(self):
        return json.dumps(self.cfg().get("feeds"), sort_keys=True)

    def fetch(self):
        import datetime as dt
        items, errors = [], []
        for f in self.cfg().get("feeds") or []:
            url = str(f.get("url") or "").strip()
            if not url:
                continue
            name = str(f.get("name") or domain_of(url))
            try:
                items += read_video_feed(url, name)[:20]
            except FEED_ERRORS as ex:
                errors.append(f"{name}: {err_text(ex)}")
        if errors and not items:
            raise RuntimeError("; ".join(errors))
        old = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        items.sort(key=lambda x: x["time"] or old, reverse=True)
        return {"items": items[:30], "errors": errors}


class VideoPlayer:
    """Spielt ein Video mit ffmpeg ab. Pause und Spulen beenden ffmpeg und starten es an der gemerkten Stelle
    neu (-ss) – ein angehaltenes ffmpeg mit -re würde nach dem Weiterlaufen im Zeitraffer aufholen."""

    def __init__(self, env, log=print):
        self.env, self.log = env, log           # env(): Umgebung der Desktop-Sitzung (Ton über PipeWire)
        self.lock = threading.Lock()
        self.proc = None
        self.item = None                        # laufendes bzw. angehaltenes Video
        self.frame = None                       # letztes Bild (PIL, VIDEO_W×VIDEO_H)
        self.base, self.frames = 0.0, 0         # Startstelle in Sekunden, seither gelesene Bilder
        self.paused = self.ended = False
        self.error = None
        self.gen = 0                            # zählt ffmpeg-Starts (alte Lesefäden geben auf)
        self.stderr = []
        self.loading = False                    # yt-dlp ermittelt gerade den Videostrom

    def available(self):
        return shutil.which("ffmpeg", path=self.env().get("PATH")) is not None

    def command(self, url, start):
        vf = (f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
              f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={VIDEO_FPS}")
        return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{start:.1f}", "-re", "-i", url,
                "-map", "0:v:0", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
                "-map", "0:a:0?", "-f", "pulse", "G19s Video"]

    def position(self):
        with self.lock:
            return self.base + self.frames / VIDEO_FPS

    def play(self, item, start=0.0):
        """Video ab start Sekunden abspielen. False = ffmpeg fehlt bzw. startet nicht."""
        self._kill()
        env = self.env()
        with self.lock:
            self.gen += 1
            gen = self.gen
            self.item, self.base, self.frames = item, max(0.0, start), 0
            self.paused = self.ended = False
            self.error, self.stderr = None, []
        try:
            proc = subprocess.Popen(self.command(item["url"], max(0.0, start)), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, start_new_session=True)
        except OSError as ex:
            with self.lock:
                self.error = "ffmpeg fehlt – sudo apt install ffmpeg" if isinstance(ex, FileNotFoundError) else str(ex)
                self.ended = True
            return False
        self.proc = proc
        threading.Thread(target=self._read, args=(proc, gen), daemon=True).start()
        threading.Thread(target=self._read_err, args=(proc,), daemon=True).start()
        return True

    def _read(self, proc, gen):
        size = VIDEO_W * VIDEO_H * 3
        out = proc.stdout
        while True:
            buf = b""
            while len(buf) < size:
                chunk = out.read(size - len(buf))
                if not chunk:
                    break
                buf += chunk
            if len(buf) < size:
                break
            img = Image.frombytes("RGB", (VIDEO_W, VIDEO_H), buf)
            with self.lock:
                if gen != self.gen:
                    return
                self.frame = img
                self.frames += 1
        rc = proc.wait()
        with self.lock:
            if gen != self.gen:
                return                          # absichtlich beendet (Pause, Spulen, Stopp)
            self.proc = None
            self.ended = True
            if rc and self.frames == 0:
                self.error = (self.stderr[-1] if self.stderr else f"ffmpeg beendet ({rc})")[:120]
        if self.error:
            self.log(f"Video: {self.error}")

    def _read_err(self, proc):
        for line in proc.stderr:
            text = line.decode("utf-8", "replace").strip()
            if text:
                with self.lock:
                    self.stderr = (self.stderr + [text])[-5:]

    def play_youtube(self, item):
        """YouTube-Video auf dem Display: yt-dlp ermittelt im Hintergrund den Videostrom, dann spielt ffmpeg ihn."""
        self._kill()
        with self.lock:
            self.gen += 1
            gen = self.gen
            self.item, self.base, self.frames, self.frame = item, 0.0, 0, None
            self.paused = self.ended = False
            self.error, self.stderr, self.loading = None, [], True

        def work():
            try:
                stream, dur = ytdlp_resolve(item["url"], self.env())
            except RuntimeError as ex:
                with self.lock:
                    if gen == self.gen:
                        self.error, self.ended, self.loading = str(ex), True, False
                self.log(f"Video: {ex}")
                return
            with self.lock:
                if gen != self.gen:
                    return                      # inzwischen gestoppt oder anderes Video
                self.loading = False
            self.play(dict(item, url=stream, duration=dur or item.get("duration"), page_url=item["url"]))
        threading.Thread(target=work, daemon=True).start()
        return True

    def toggle_pause(self):
        """Anhalten bzw. an der gemerkten Stelle weiterspielen."""
        if self.item is None or self.loading:
            return
        if self.paused:
            frame = self.frame
            self.play(self.item, self.base)
            self.frame = frame                  # bis zum ersten neuen Bild das alte zeigen
            return
        pos = self.position()
        self._kill()
        with self.lock:
            self.base, self.frames, self.paused = pos, 0, True

    def seek(self, delta):
        if self.item is None or self.loading:
            return
        pos = self.position() + delta
        dur = self.item.get("duration")
        if dur:
            pos = min(pos, max(0.0, dur - 1))
        pos = max(0.0, pos)
        if self.paused:
            with self.lock:
                self.base, self.frames = pos, 0
        else:
            frame = self.frame
            self.play(self.item, pos)
            self.frame = frame

    def stop(self):
        self._kill()
        with self.lock:
            self.item, self.frame, self.paused, self.ended, self.error = None, None, False, False, None
            self.loading = False

    def _kill(self):
        with self.lock:
            self.gen += 1
            proc, self.proc = self.proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
