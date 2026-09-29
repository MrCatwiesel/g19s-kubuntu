"""HTTP-Routen: Infoseiten: Wetter, Termine, Ordner, Benachrichtigungen, Hardware, Nachrichten, Unwetter, Netzwerk, Updates, Songs, Lieblingsbilder."""


class ApiInfo:
    # -- API: Infoseiten --------------------------------------------------- #
    def api_get_weather_search(self, q):
        name = q.get("q", [""])[0].strip()
        if len(name) < 2:
            raise ValueError("Bitte mindestens zwei Buchstaben eingeben")
        try:
            self._send(200, {"results": g.geocode(name)})
        except Exception as ex:
            raise RuntimeError(f"Ortssuche nicht erreichbar: {getattr(ex, 'reason', None) or ex}")

    def api_post_weather_test(self, q):
        w = self._json()
        poller = g.WeatherPoller(lambda: {"weather": w, "pages": ["weather"]})
        try:
            data = poller.fetch()
        except Exception as ex:
            raise RuntimeError(f"Wetterdienst nicht erreichbar: {getattr(ex, 'reason', None) or ex}")
        cur = data.get("current") or {}
        desc = g.WEATHER_CODES.get(int(cur.get("weather_code") or 0), ("", ""))[0]
        self._send(200, {"temp": cur.get("temperature_2m"), "desc": desc})

    def api_post_calendar_test(self, q):
        src = self._json()
        s = {"calendar": {"sources": [src], "days": 30}, "pages": ["calendar"]}
        try:
            data = g.CalendarPoller(lambda: s).fetch()
        except Exception as ex:
            raise RuntimeError(str(ex))
        if data["errors"]:
            raise RuntimeError(data["errors"][0])
        nxt = []
        for it in data["items"][:3]:
            st = it["start"]
            when = st.strftime("%d.%m.") if it["allday"] else st.strftime("%d.%m. %H:%M")
            nxt.append(f"{when} {it['title']}")
        self._send(200, {"count": len(data["items"]), "next": nxt, "calendars": data.get("calendars") or []})

    def api_get_folder_list(self, q):
        path = os.path.expanduser(q.get("path", ["~"])[0] or "~")
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            raise ValueError("Ordner nicht gefunden")
        try:
            names = sorted(n for n in os.listdir(path) if not n.startswith("."))
        except OSError as ex:
            raise ValueError(f"Ordner nicht lesbar: {ex.strerror}")
        dirs = [n for n in names if os.path.isdir(os.path.join(path, n))]
        images = sum(1 for n in names if n.lower().endswith(g.Slideshow.IMAGE_EXT))
        home = os.path.realpath(HOME)
        shown = "~" + path[len(home):] if path == home or path.startswith(home + "/") else path
        self._send(200, {"path": shown, "parent": os.path.dirname(path) if path != "/" else None,
                         "dirs": dirs[:500], "images": images})

    def api_post_notify_test(self, q):
        if not shutil.which("notify-send"):
            raise RuntimeError("notify-send fehlt (Paket libnotify-bin)")
        code, out = run(["notify-send", "-a", "G19s-Verwaltung", "Testbenachrichtigung",
                         "So sieht eine Benachrichtigung auf dem Display aus."])
        if code:
            raise RuntimeError(out or "notify-send meldet einen Fehler")
        self._send(200, {"ok": True})

    def api_get_hardware(self, q):
        hw = g.Hardware()
        s = hw.sensors()
        self._send(200, {"sensors": s, "disks": [(l, round(p), round(t / 1e9)) for l, p, t in hw.disks()]})

    def api_post_news_test(self, q):
        f = self._json()
        url = str(f.get("url") or "").strip()
        if not re.match(r"^https?://", url, re.I):
            raise ValueError("Die Adresse muss mit http:// oder https:// beginnen")
        try:
            items = g.parse_feed(g.http_get(url, timeout=20), f.get("name") or "")
        except Exception as ex:
            raise RuntimeError(f"Feed nicht lesbar: {getattr(ex, 'reason', None) or ex}")
        if not items:
            raise RuntimeError("Keine Meldungen gefunden – ist das ein RSS- oder Atom-Feed?")
        self._send(200, {"count": len(items), "first": items[0]["title"]})

    def api_post_warnings_test(self, q):
        s = clean_settings(self._json().get("settings") or g.load_settings())
        if s["weather"].get("lat") is None:
            raise ValueError("Zuerst oben einen Wetter-Ort wählen")
        try:
            data = g.WarningsPoller(lambda: s).fetch()
        except Exception as ex:
            raise RuntimeError(f"Warndienst nicht erreichbar: {getattr(ex, 'reason', None) or ex}")
        self._send(200, {"place": data["place"], "alerts": [f"{g.SEVERITY.get(a['severity'], ('', ''))[0]}: {a['event']}"
                                                             for a in data["alerts"]]})

    def api_post_network_test(self, q):
        s = clean_settings(self._json().get("settings") or g.load_settings())
        s["pages"] = ["network"]
        self._send(200, g.NetworkPoller(lambda: s).fetch())

    def api_post_updates_test(self, q):
        s = clean_settings(self._json().get("settings") or g.load_settings())
        self._send(200, g.UpdatesPoller(lambda: s).fetch())

    def api_get_songs(self, q):
        self._send(200, {"songs": g.load_list(g.SONGS_FILE)})

    def api_post_songs(self, q):
        songs = self._json().get("songs")
        if not isinstance(songs, list):
            raise ValueError("Ungültige Liste")
        keep = [{k: str(x.get(k) or "")[:300] for k in ("time", "artist", "title", "source")}
                for x in songs if isinstance(x, dict)]
        g.save_json(g.SONGS_FILE, keep)
        self._send(200, {"songs": keep})

    def api_get_favorites(self, q):
        self._send(200, {"favorites": g.load_list(g.FAVORITES_FILE)})

    def api_post_favorites(self, q):
        remove = {str(x) for x in (self._json().get("remove") or [])}
        favs = [f for f in g.load_list(g.FAVORITES_FILE) if str(f.get("id")) not in remove]
        g.save_json(g.FAVORITES_FILE, favs)
        self._send(200, {"favorites": favs})
