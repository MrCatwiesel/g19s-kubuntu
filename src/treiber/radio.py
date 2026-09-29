"""Eigener Radioplayer (mpv mit Senderliste als Wiedergabeliste)."""


class RadioManager:
    """Spielt Radiosender über einen externen Player (Standard: mpv) ab.

    Mit mpv wird die ganze Senderliste als Wiedergabeliste übergeben. Ist das
    Plugin mpv-mpris installiert, meldet sich mpv bei KDE als Player an: die
    Medientasten der Tastatur (Play/Pause, Vor/Zurück, Stop) und die
    KDE-Medienwiedergabe steuern dann auch das Radio.
    """

    def __init__(self, env_func, log=print):
        self.env_func, self.log = env_func, log
        self.proc = None
        self.station = None        # {"name", "url", "logo"}
        self.playlist = []         # Senderliste, die mpv als Wiedergabeliste bekommen hat
        self.lock = threading.Lock()

    @property
    def playing(self):
        return self.proc is not None and self.proc.poll() is None

    def current(self):
        with self.lock:
            return dict(self.station) if self.station and self.playing else None

    def playlist_urls(self):
        with self.lock:
            return [s["url"] for s in self.playlist]

    def follow(self, url):
        """mpv hat selbst den Sender gewechselt (z. B. per Medientaste) – mitziehen."""
        with self.lock:
            if not self.station or url == self.station.get("url"):
                return
            for s in self.playlist:
                if s["url"] == url:
                    self.station = dict(s)
                    self.log(f"Radio: {s.get('name') or url}")
                    return

    def _build_cmd(self, cmd, url, stations):
        import shlex
        try:
            is_mpv = os.path.basename(shlex.split(cmd)[0]) == "mpv"
        except (ValueError, IndexError):
            is_mpv = False
        urls = [s["url"] for s in stations]
        if is_mpv and url in urls:
            playlist = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "g19s-radio.m3u")
            with open(playlist, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for s in stations:
                    name = (s.get("name") or s["url"]).replace("\n", " ")
                    f.write(f"#EXTINF:-1,{name}\n{s['url']}\n")
            arg = (f"--playlist={shlex.quote(playlist)} --playlist-start={urls.index(url)} "
                   f"--loop-playlist=inf")
            if "--load-scripts=no" in cmd:
                plugin = find_mpris_plugin()
                if plugin:
                    arg += f" --script={shlex.quote(plugin)}"
            return (cmd.replace("{url}", arg) if "{url}" in cmd else f"{cmd} {arg}"), True
        quoted = shlex.quote(url)
        return (cmd.replace("{url}", quoted) if "{url}" in cmd else f"{cmd} {quoted}"), False

    def play(self, station, player_cmd, stations=None):
        self.stop()
        url = station.get("url", "")
        if not url:
            return False
        stations = [dict(s) for s in (stations or []) if isinstance(s, dict) and s.get("url")]
        if url not in [s["url"] for s in stations]:
            stations = [dict(station)]
        cmd, uses_list = self._build_cmd(player_cmd or DEFAULT_SETTINGS["radio_player"], url, stations)
        try:
            proc = subprocess.Popen(cmd, shell=True, env=self.env_func(),
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as ex:
            self.log(f"Radio konnte nicht gestartet werden: {ex}")
            return False
        time.sleep(0.3)
        if proc.poll() is not None:
            self.log(f"Radioplayer beendet sich sofort (Befehl: {cmd}) – ist er installiert?")
            return False
        with self.lock:
            self.proc, self.station = proc, dict(station)
            self.playlist = stations if uses_list else [dict(station)]
        self.log(f"Radio: {station.get('name') or url}")
        return True

    def stop(self):
        with self.lock:
            proc, self.proc, self.station = self.proc, None, None
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired, PermissionError):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

    def step(self, stations, player_cmd, direction):
        """Zum nächsten (+1) bzw. vorherigen (-1) Sender der Liste wechseln."""
        stations = [s for s in stations if s.get("url")]
        if not stations:
            return None
        cur = self.current()
        urls = [s["url"] for s in stations]
        idx = urls.index(cur["url"]) + direction if cur and cur["url"] in urls else 0
        station = stations[idx % len(stations)]
        return station if self.play(station, player_cmd, stations) else None
