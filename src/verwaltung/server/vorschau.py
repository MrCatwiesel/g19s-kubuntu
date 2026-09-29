"""Display-Vorschau in der Verwaltung und Test der Diashow (nutzt den Renderer des Treibers)."""


class PreviewSlides:
    """Liefert der Displayvorschau ein festes Beispielbild."""

    def __init__(self, img, name, count):
        self.img, self.name, self.count = img, name, count

    def touch(self):
        pass

    def snapshot(self):
        return {"image": self.img, "name": self.name, "index": 1, "count": self.count,
                "status": "", "error": None, "paused": False, "configured": True}


def piwigo_test(cfg):
    import random
    cfg = g.SCHEMA["slideshow"].clean(cfg, strict=True)
    from PIL import Image
    if cfg["source"] == "folder":
        folder = os.path.expanduser(cfg["folder"])
        if not cfg["folder"] or not os.path.isdir(folder):
            raise ValueError("Bitte einen vorhandenen Bilderordner angeben")
        images = g.Slideshow.folder_images(folder, cfg["recursive"])
        if not images:
            return {"count": 0, "image": None}
        pick = random.choice(images) if cfg["shuffle"] else images[0]
        try:
            raw = Image.open(pick["url"])
            raw.load()
        except Exception as ex:
            raise RuntimeError(f"Bild „{os.path.basename(pick['url'])}“ nicht lesbar: {ex}")
    else:
        if not cfg["url"]:
            raise ValueError("Bitte die Adresse der Piwigo-Galerie eintragen")
        if not cfg["albums"]:
            raise ValueError("Bitte mindestens ein Album auswählen")
        client = g.PiwigoClient(cfg["url"], cfg["user"], cfg["password"])
        try:
            images = client.images(cfg["albums"], cfg["recursive"])
            if not images:
                return {"count": 0, "image": None}
            pick = random.choice(images) if cfg["shuffle"] else images[0]
            raw = Image.open(io.BytesIO(client.fetch(pick["url"])))
        except g.PiwigoError as ex:
            raise RuntimeError(str(ex))
    fitted = g.fit_photo(raw, g.Slideshow.AREA, cfg["fit"])
    with _preview_lock:
        r = g.Renderer()
        r.settings = dict(g.load_settings(), slideshow=cfg)
        r.slideshow = PreviewSlides(fitted, pick["name"], len(images))
        img = r.render(g.Renderer.SLIDES_PAGE, "M1", {})
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return {"count": len(images), "image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}


# --------------------------------------------------------------------------- #
# Display-Vorschau
# --------------------------------------------------------------------------- #
_preview_lock = threading.Lock()
_renderer = None


class PreviewData:
    """Wetter/Termine für die Vorschau: einmal abrufen und 5 Minuten merken."""

    def __init__(self, poller_cls):
        self.poller_cls, self.cache = poller_cls, {}

    def get(self, settings):
        poller = self.poller_cls(lambda: settings)
        key = poller.signature()
        hit = self.cache.get(key)
        if hit and time.time() - hit[2] < 300:
            return hit
        try:
            res = (poller.fetch(), None, time.time())
        except Exception as ex:
            res = (None, str(getattr(ex, "reason", None) or ex), time.time())
        self.cache = {key: res}
        return res


class _Snap:
    def __init__(self, res):
        self.res = res

    def snapshot(self):
        return self.res


_preview_weather = PreviewData(g.WeatherPoller)
_preview_calendar = PreviewData(g.CalendarPoller)
_preview_extra = {"news": PreviewData(g.NewsPoller), "warnings": PreviewData(g.WarningsPoller),
                  "network": PreviewData(g.NetworkPoller), "updates": PreviewData(g.UpdatesPoller)}
_PREVIEW_ATTR = {"news": "news", "warnings": "alerts", "network": "net", "updates": "updates"}


def render_preview(page, layer, settings, pidx=0, colors=None, name=None, face=None):
    global _renderer
    with _preview_lock:
        if _renderer is None:
            _renderer = g.Renderer()
        s = clean_settings(settings) if settings else g.load_settings()
        lay = layer if layer in g.LAYERS else "M1"
        macros_pv, _ = read_macros()
        profs = macros_pv["profiles"]
        own = (profs[max(0, min(int(pidx or 0), len(profs) - 1))].get("pages") or {}).get(lay)
        lay_pages = own or s["layer_pages"].get(lay) or s["pages"]
        _renderer.visible = [g.PAGE_IDS.index(p) for p in lay_pages]
        page_id = g.PAGE_IDS[int(page) % len(g.PAGE_IDS)]
        preview_settings = dict(s, pages=list(g.PAGE_IDS))
        if page_id == "weather" and s["weather"].get("lat") is not None:
            _renderer.weather = _Snap(_preview_weather.get(preview_settings))
        if page_id == "calendar" and s["calendar"]["sources"]:
            _renderer.calendar = _Snap(_preview_calendar.get(preview_settings))
        if page_id in _preview_extra:
            setattr(_renderer, _PREVIEW_ATTR[page_id], _Snap(_preview_extra[page_id].get(preview_settings)))
        macros, _ = read_macros()
        profiles = macros["profiles"]
        pidx = max(0, min(int(pidx or 0), len(profiles) - 1))
        prof = profiles[pidx]
        cols = g.valid_colors(colors) or prof.get("colors") or g.valid_colors(s["colors"]) or g.DEFAULT_SETTINGS["colors"]
        for p, color in cols.items():
            g.PROFILE_COLOR[p] = tuple(color)
        _renderer.settings = s
        _renderer.clock_face = (face if face in g.CLOCK_FACES else      # Karte „Uhr“: gezeigtes Zifferblatt
                                (prof.get("clock") or {}).get(lay, "digital"))  # sonst: am Display gewähltes
        _renderer.profile_name = (name if name is not None else prof["name"]) if len(profiles) > 1 else ""
        img = _renderer.render(int(page) % len(g.PAGE_NAMES), layer if layer in g.LAYERS else "M1",
                               prof["keys"])
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
