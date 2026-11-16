"""Videos: Video-Podcast-Feeds (RSS mit Video-Anhang) abrufen und mit ffmpeg auf dem Display abspielen.
Das Bild kommt als Rohdaten (RGB, 320×180, 15 Bilder je Sekunde) über eine Pipe, der Ton geht im selben ffmpeg-Aufruf
an PipeWire/PulseAudio – so bleiben Bild und Ton beisammen, ohne dass ein Fenster aufgeht."""

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
                items += parse_video_feed(http_get(url, timeout=20), name)[:20]
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

    def toggle_pause(self):
        """Anhalten bzw. an der gemerkten Stelle weiterspielen."""
        if self.item is None:
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
        if self.item is None:
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
