"""Diashow: Bildliste (Piwigo, Ordner oder Lieblingsbilder), Bildwechsel, Zwischenspeicher, Albenliste."""


# --------------------------------------------------------------------------- #
# Diashow aus Piwigo-Alben
# --------------------------------------------------------------------------- #
class Slideshow(threading.Thread):
    """Lädt die Bildliste der gewählten Alben und wechselt die Bilder.
    Netzwerkzugriffe gibt es nur, solange die Displayseite „Bilder“ sichtbar ist."""

    AREA = (WIDTH, HEIGHT - FOOTER_H)  # Fläche über der Fußzeile
    LIST_REFRESH = 1800               # Bildliste alle 30 Minuten neu laden
    RETRY = 60                        # nach einem Fehler erneut versuchen
    CACHE_MAX = 400                   # höchstens so viele Bilder zwischenspeichern

    def __init__(self, get_settings, log=print):
        super().__init__(daemon=True)
        self.get_settings, self.log = get_settings, log
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.running = True
        self.images, self.order, self.pos = [], [], -1
        self.sig, self.loaded_at, self.retry_at = None, 0.0, 0.0
        self.client = None
        self.current = None           # {"id", "name", "raw": PIL-Bild}
        self.fitted = (None, None)    # (Schlüssel, fertig eingepasstes Bild)
        self.status, self.error = "", None
        self.paused = False
        self.last_switch = 0.0
        self.active_until = 0.0
        self.request = None           # "next" / "previous"
        self.cache_dir = os.path.join(CACHE_DIR, "piwigo")
        self.album_state = {"list": None, "error": None, "loading": False, "at": 0.0}
        self.fav = {"ids": set(), "mtime": None}

    def fav_ids(self):
        """IDs der Lieblingsbilder (neu eingelesen, wenn sich favorites.json geändert hat)."""
        try:
            mtime = os.path.getmtime(FAVORITES_FILE)
        except OSError:
            mtime = None
        if mtime != self.fav["mtime"]:
            self.fav = {"ids": {str(f.get("id")) for f in load_list(FAVORITES_FILE)}, "mtime": mtime}
        return self.fav["ids"]

    def source_key(self, cfg=None):
        cfg = cfg or self.cfg()
        return "folder" if cfg.get("source") == "folder" else "piwigo:" + str(cfg.get("url") or "").rstrip("/")

    def favorites(self, cfg=None):
        key = self.source_key(cfg)
        return [f for f in load_list(FAVORITES_FILE) if f.get("source") == key and f.get("url")]

    def favorite_current(self):
        """Aktuelles Bild als Lieblingsbild merken/entfernen. True/False, None = kein Bild."""
        with self.lock:
            cur = self.current
        if not cur or not cur.get("info"):
            return None
        info = dict(cur["info"])
        cfg = self.cfg()
        if not info.get("local"):
            info["page"] = f"{str(cfg.get('url') or '').rstrip('/')}/picture.php?/{info['id']}"
        else:
            info["page"] = info["url"]
        return toggle_favorite(info, self.source_key(cfg))

    def request_albums(self):
        """Albenliste für die Auswahl am Display laden (im Hintergrund, 5 Minuten zwischengespeichert)."""
        st = self.album_state
        if st["loading"] or (st["list"] is not None and time.monotonic() - st["at"] < 300):
            return
        cfg = self.cfg()
        st.update(loading=True, error=None)

        def work():
            try:
                albums = PiwigoClient(cfg["url"], cfg.get("user"), cfg.get("password")).albums()
                st.update(list=albums, at=time.monotonic())
            except Exception as ex:          # Fehlermeldung im Menü statt Absturz des Threads
                st["error"] = str(ex)
            finally:
                st["loading"] = False
        threading.Thread(target=work, daemon=True).start()

    # -- öffentlich -------------------------------------------------------- #
    def cfg(self):
        return dict(DEFAULT_SETTINGS["slideshow"], **(self.get_settings().get("slideshow") or {}))

    def touch(self):
        was_idle = time.monotonic() > self.active_until
        self.active_until = time.monotonic() + 3
        if was_idle:
            self.wake.set()

    def command(self, action):
        if action in ("play-pause", "toggle"):
            self.paused = not self.paused
            self.last_switch = time.monotonic()
        elif action in ("next", "previous"):
            self.request = action
            self.wake.set()

    @staticmethod
    def is_configured(cfg):
        if cfg.get("source") == "folder":
            return bool(cfg.get("folder")) and os.path.isdir(os.path.expanduser(str(cfg.get("folder"))))
        return bool(cfg.get("url") and (cfg.get("albums") or cfg.get("favorites_only")))

    IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")

    @classmethod
    def folder_images(cls, folder, recursive=True, limit=20000):
        folder = os.path.expanduser(str(folder))
        out = []
        for root, dirs, files in os.walk(folder):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for f in sorted(files):
                if f.lower().endswith(cls.IMAGE_EXT) and not f.startswith("."):
                    path = os.path.join(root, f)
                    out.append({"id": path, "name": os.path.splitext(f)[0], "url": path, "local": True})
                    if len(out) >= limit:
                        return out
            if not recursive:
                break
        return out

    def snapshot(self):
        cfg = self.cfg()
        with self.lock:
            cur = self.current
            img = None
            if cur is not None:
                key = (cur["id"], cfg.get("fit"))
                if self.fitted[0] != key:
                    self.fitted = (key, fit_photo(cur["raw"], self.AREA, cfg.get("fit", "contain")))
                img = self.fitted[1]
            return {"image": img, "name": cur["name"] if cur else "", "id": cur["id"] if cur else None,
                    "index": self.pos + 1, "count": len(self.order),
                    "status": self.status, "error": self.error, "paused": self.paused,
                    "configured": self.is_configured(cfg)}

    def stop(self):
        self.running = False
        self.wake.set()

    # -- intern ------------------------------------------------------------ #
    def run(self):
        while self.running:
            try:
                self._step()
            except Exception as ex:          # Diashow darf den Treiber nie stören
                with self.lock:
                    self.error = str(ex)
                self.retry_at = time.monotonic() + self.RETRY
            self.wake.wait(0.5)
            self.wake.clear()

    def _step(self):
        cfg = self.cfg()
        now = time.monotonic()
        if cfg.get("favorites_only"):
            self.fav_ids()                    # Änderungen an favorites.json bemerken
        sig = (cfg.get("url"), cfg.get("user"), cfg.get("password"),
               tuple(cfg.get("albums") or []), bool(cfg.get("recursive")), bool(cfg.get("shuffle")),
               cfg.get("source"), cfg.get("folder"), bool(cfg.get("favorites_only")),
               self.fav["mtime"] if cfg.get("favorites_only") else None)
        if not self.is_configured(cfg):
            with self.lock:
                self.images, self.order, self.pos, self.current = [], [], -1, None
                self.status, self.error, self.sig = "", None, None
            return
        if now > self.active_until:
            return                            # Seite nicht sichtbar: nichts laden
        if now < self.retry_at and self.error:
            return
        if sig != self.sig or now - self.loaded_at > self.LIST_REFRESH:
            self._load_list(cfg, sig)
            if not self.order:
                return
        interval = max(3, int(cfg.get("interval") or 10))
        request, self.request = self.request, None
        due = self.current is None or (not self.paused and now - self.last_switch >= interval)
        if request or due:
            self._show(-1 if request == "previous" else 1)

    def _load_list(self, cfg, sig):
        import random
        with self.lock:
            self.status, self.error = "Lade Bildliste …", None
        if cfg.get("favorites_only"):
            images = [{"id": f["id"], "name": f.get("name", ""), "url": f["url"], "local": bool(f.get("local"))}
                      for f in self.favorites(cfg)]
            if cfg.get("source") != "folder" and (sig[:3] != (self.sig or (None,) * 3)[:3] or self.client is None):
                self.client = PiwigoClient(cfg["url"], cfg.get("user"), cfg.get("password"))
        elif cfg.get("source") == "folder":
            images = self.folder_images(cfg["folder"], bool(cfg.get("recursive")))
        else:
            if sig[:3] != (self.sig or (None,) * 3)[:3] or self.client is None:
                self.client = PiwigoClient(cfg["url"], cfg.get("user"), cfg.get("password"))
            images = self.client.images(cfg.get("albums") or [], bool(cfg.get("recursive")))
        order = list(range(len(images)))
        if cfg.get("shuffle"):
            random.shuffle(order)
        cur_id = self.current["id"] if self.current else None
        pos = next((i for i, o in enumerate(order) if images[o]["id"] == cur_id), -1)
        with self.lock:
            self.images, self.order, self.pos = images, order, pos
            self.sig, self.loaded_at = sig, time.monotonic()
            self.status = "" if images else ("Noch keine Lieblingsbilder" if cfg.get("favorites_only")
                                             else "Keine Bilder in den gewählten Alben")
            if pos < 0:
                self.last_switch = 0.0        # aktuelles Bild gehört nicht mehr dazu: sofort wechseln
                if not images:
                    self.current = None
        self.log(f"Diashow: {len(images)} Bilder gefunden")

    def _show(self, direction):
        if not self.order:
            return
        for _ in range(min(5, len(self.order))):          # defekte Bilder überspringen
            pos = (self.pos + direction) % len(self.order)
            info = self.images[self.order[pos]]
            with self.lock:
                self.pos = pos
                if self.current is None:
                    self.status = "Lade Bild …"
            try:
                raw = self._load_image(info)
            except Exception as ex:          # defektes Bild überspringen (Netz, PIL, Datei)
                self.log(f"Diashow: Bild übersprungen ({ex})")
                continue
            with self.lock:
                self.current = {"id": info["id"], "name": info["name"], "raw": raw, "info": info}
                self.status, self.error = "", None
            self.last_switch = time.monotonic()
            return

    def _load_image(self, info):
        import hashlib
        import io
        if info.get("local"):
            from PIL import ImageOps
            with Image.open(info["url"]) as im:
                im.draft("RGB", (1280, 960))              # große JPEGs schneller dekodieren
                img = ImageOps.exif_transpose(im).convert("RGB")
            img.thumbnail((640, 480), Image.LANCZOS)
            return img
        name = hashlib.sha1(str(info["url"]).encode()).hexdigest() + ".jpg"
        path = os.path.join(self.cache_dir, name)
        if os.path.exists(path):
            os.utime(path)
            return Image.open(path).convert("RGB")
        img = open_remote_image(self.client.fetch(info["url"]))
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((640, 480), Image.LANCZOS)          # klein speichern, reicht fürs Display
        os.makedirs(self.cache_dir, exist_ok=True)
        img.save(path, "JPEG", quality=88)
        self._prune_cache()
        return img

    def _prune_cache(self):
        try:
            files = [os.path.join(self.cache_dir, f) for f in os.listdir(self.cache_dir)]
            if len(files) > self.CACHE_MAX:
                files.sort(key=os.path.getmtime)
                for f in files[:len(files) - self.CACHE_MAX]:
                    os.remove(f)
        except OSError:
            pass
