"""Aktuelle Wiedergabe über MPRIS/playerctl, Cover, Songtitel aus dem Radiostream (ICY)."""


# --------------------------------------------------------------------------- #
# Aktuelle Wiedergabe (MPRIS über playerctl)
# --------------------------------------------------------------------------- #
class MediaWatcher(threading.Thread):
    """Fragt ab, was gerade läuft, und lädt das Cover: jede Sekunde, solange want_fast() gilt
    (Musikseite sichtbar oder Radio an), sonst alle SLOW_INTERVAL Sekunden – playerctl weckt
    bei jedem Aufruf alle Player über D-Bus."""

    SLOW_INTERVAL = 5

    FIELDS = ("player", "status", "title", "artist", "album", "art", "position", "length", "url")
    FMT = "\t".join(["{{playerName}}", "{{status}}", "{{title}}", "{{artist}}",
                     "{{album}}", "{{mpris:artUrl}}", "{{position}}", "{{mpris:length}}",
                     "{{xesam:url}}"])
    COVER_SIZE = 132
    ICY_INTERVAL = 30       # Sekunden zwischen zwei Abfragen beim Radiosender (je eine neue Verbindung)

    RADIO_PLAYER = "g19s-radio"

    def __init__(self, env_func, log=print, radio=None, radio_control=None):
        super().__init__(daemon=True)
        self.env_func, self.log = env_func, log
        self.radio = radio                   # RadioManager des Treibers
        self.radio_control = radio_control   # Funktion(action) für den eigenen Radioplayer
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.running = True
        self.want_fast = lambda: True       # setzt der Treiber (Musikseite sichtbar / Radio an)
        self.fast_now = True
        self.info = None
        self.error = None
        self.cover_url = None
        self.cover = None
        self.cover_bg = None
        self.env = None
        self.env_time = 0.0
        self.icy_url = None      # Stream, für den icy_title gilt
        self.icy_title = None    # z. B. "AC/DC - Thunderstruck"
        self.icy_next = 0.0
        self.icy_busy = False

    # -- öffentlich -------------------------------------------------------- #
    def snapshot(self):
        with self.lock:
            return self.info, self.cover, self.cover_bg, self.error

    def control(self, action):
        with self.lock:
            info = self.info
        if not info:
            return
        target = info["player"]
        if target == self.RADIO_PLAYER:
            if info.get("mpris"):
                target = info["mpris"]        # mpv direkt steuern (Pause, Sender vor/zurück)
            else:
                if self.radio_control:
                    self.radio_control(action)
                self.wake.set()
                return
        try:
            subprocess.Popen(["playerctl", "-p", target, action], env=self._env(),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            return
        time.sleep(0.15)
        self.wake.set()

    def stop(self):
        self.running = False
        self.wake.set()

    # -- intern ------------------------------------------------------------ #
    def _env(self):
        now = time.monotonic()
        if self.env is None or now - self.env_time > 30:
            self.env, self.env_time = self.env_func(), now
        return self.env

    def run(self):
        while self.running:
            try:
                self._poll()
            except Exception as ex:  # Sicherheitsnetz: nie wegen der Musikseite abstürzen
                with self.lock:
                    self.error = str(ex)
            self.fast_now = bool(self.want_fast())
            self.wake.wait(1.0 if self.fast_now else self.SLOW_INTERVAL)
            self.wake.clear()

    def refresh(self):
        """Sofort abfragen (z. B. vor „Song merken“), im aufrufenden Thread."""
        try:
            self._poll()
        except Exception as ex:             # wie in run(): nie wegen der Musikabfrage abstürzen
            with self.lock:
                self.error = str(ex)

    def _poll(self):
        error = None
        try:
            out = subprocess.run(["playerctl", "-a", "metadata", "--format", self.FMT],
                                 capture_output=True, text=True, timeout=3,
                                 env=self._env()).stdout
        except FileNotFoundError:
            out, error = "", "playerctl fehlt"
        except subprocess.TimeoutExpired:
            return

        players = []
        station = self.radio.current() if self.radio else None
        radio_urls = set(self.radio.playlist_urls()) if station else set()
        parsed = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == len(self.FIELDS):
                parsed.append(dict(zip(self.FIELDS, parts)))

        # Der eigene Radioplayer (mpv) meldet sich mit mpv-mpris bei KDE an: diesen
        # Eintrag erkennen, damit Pause und Senderwechsel per Medientaste ankommen.
        mpris_radio = None
        if station:
            for p in parsed:
                if p["player"].split(".")[0] == "mpv" and (p["url"] in radio_urls or not p["url"]):
                    mpris_radio = p
                    break
            if mpris_radio and mpris_radio["url"]:
                self.radio.follow(mpris_radio["url"])
                station = self.radio.current() or station
            status = mpris_radio["status"] if mpris_radio and mpris_radio["status"] in ("Playing", "Paused") else "Playing"
            # eigener Radioplayer hat Vorrang, er wurde zuletzt per Taste gestartet
            players.append({"player": self.RADIO_PLAYER, "status": status,
                            "title": station.get("name") or "Radio", "artist": "",
                            "album": "", "art": station.get("logo") or "", "position": 0,
                            "length": 0, "url": station["url"], "fetched": time.monotonic(),
                            "mpris": mpris_radio["player"] if mpris_radio else None})
        for p in parsed:
            if p is mpris_radio:
                continue
            if p["status"] not in ("Playing", "Paused") or not (p["title"] or p["artist"]):
                continue
            if station and p["url"] in radio_urls:
                continue  # derselbe Stream wie das eigene Radio
            for key in ("position", "length"):
                try:
                    p[key] = max(0, int(float(p[key] or 0)))
                except ValueError:
                    p[key] = 0
            p["fetched"] = time.monotonic()
            players.append(p)
        players.sort(key=lambda p: (p["player"] != self.RADIO_PLAYER, p["status"] != "Playing"))
        info = players[0] if players else None
        if info:
            self._apply_radio(info)

        art = info["art"] if info else None
        if art != self.cover_url:
            cover, bg = self._load_cover(art) if art else (None, None)
            with self.lock:
                self.cover_url, self.cover, self.cover_bg = art, cover, bg
        with self.lock:
            self.info, self.error = info, (None if info else error)

    # -- Internetradio: aktuellen Song aus dem Stream lesen (ICY-Metadaten) -- #
    @staticmethod
    def _is_radio(info):
        return (info["url"].startswith(("http://", "https://"))
                and not info["artist"] and not info["length"])

    def _apply_radio(self, info):
        info["station"] = None
        if not self._is_radio(info):
            return
        url = info["url"]
        now = time.monotonic()
        if url != self.icy_url:
            self.icy_url, self.icy_title, self.icy_next = url, None, 0.0
        if now >= self.icy_next and not self.icy_busy and info["status"] == "Playing":
            self.icy_busy = True
            self.icy_next = now + self.ICY_INTERVAL
            threading.Thread(target=self._fetch_icy, args=(url,), daemon=True).start()

        title = self.icy_title
        if not title:
            return
        info["station"] = info["title"]
        artist, sep, song = title.partition(" - ")
        if sep and artist.strip() and song.strip():
            info["artist"], info["title"] = artist.strip(), song.strip()
        else:
            info["title"] = title

    def _fetch_icy(self, url):
        import urllib.request
        title = None
        try:
            req = urllib.request.Request(url, headers={"Icy-MetaData": "1",
                                                       "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as r:
                metaint = int(r.headers.get("icy-metaint") or 0)
                if 0 < metaint <= 256 * 1024:      # übliche Werte 8–64 KiB; mehr = kein Titel
                    remaining = metaint
                    while remaining > 0:          # Audiodaten bis zum Metadatenblock überspringen
                        chunk = r.read(min(remaining, 16384))
                        if not chunk:
                            raise EOFError
                        remaining -= len(chunk)
                    length = r.read(1)[0] * 16
                    meta = r.read(length) if length else b""
                    try:
                        text = meta.rstrip(b"\0").decode("utf-8")
                    except UnicodeDecodeError:
                        text = meta.rstrip(b"\0").decode("latin-1")
                    m = re.search(r"StreamTitle='(.*?)';", text, re.S)
                    if m and m.group(1).strip():
                        title = " ".join(m.group(1).split())
        except NET_ERRORS as ex:
            self.log(f"Radio-Titel nicht abrufbar: {ex}")
        finally:
            if url == self.icy_url:
                if title or not self.icy_title:
                    self.icy_title = title
                if title:
                    self.wake.set()   # sofort anzeigen
            self.icy_busy = False

    def _load_cover(self, url):
        import io
        import urllib.parse
        import urllib.request
        from PIL import ImageEnhance, ImageFilter, ImageOps
        try:
            if url.startswith("file://"):
                path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
                if not os.path.isfile(path):
                    return None, None
                with open(path, "rb") as f:
                    raw = f.read(8 * 1024 * 1024)
            elif url.startswith(("http://", "https://")):
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=5) as r:
                    raw = r.read(8 * 1024 * 1024)
            else:
                return None, None
            img = open_remote_image(raw, draft=(640, 640)).convert("RGB")
        except (NET_ERRORS + (Image.DecompressionBombError,)) as ex:    # PIL meldet kaputte Bilder als OSError
            self.log(f"Cover konnte nicht geladen werden: {ex}")
            return None, None
        cover = ImageOps.fit(img, (self.COVER_SIZE, self.COVER_SIZE), Image.LANCZOS)
        bg = ImageOps.fit(img, (WIDTH, HEIGHT), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
        bg = ImageEnhance.Brightness(bg).enhance(0.35)
        return cover, bg
