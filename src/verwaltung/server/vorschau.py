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
        except Exception as ex:         # beliebige Bilddatei: jeden Lesefehler melden
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
            raw = g.open_remote_image(client.fetch(pick["url"]))
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
        except Exception as ex:         # Dienst im Netz: Fehler in der Vorschau anzeigen
            res = (None, g.err_text(ex), time.time())
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


def _lenient(settings):
    """Entwurf der Einstellungen für Vorschauen: streng geprüft, bei Eingabefehlern (z. B. 31.4.) nachsichtig – die
    Vorschau soll weiterlaufen, die Meldung kommt beim Speichern."""
    if not settings:
        return g.load_settings()
    try:
        return clean_settings(settings)
    except ValueError:
        return g._clean(settings, strict=False)


class _SceneAudio:
    """Klang für die bewegte Vorschau: Demo-Musik, die als „läuft gerade“ gilt; bei „boom“ kurz lauter."""
    def __init__(self, scene):
        self.t, self.scene, self.t0 = 1000.0, scene, None

    def snapshot(self):
        amp = 1.6 if self.scene == "boom" and self.t0 is not None and self.t - self.t0 < 2.0 else 1.0
        s = g.demo_snapshot(self.t, amp=amp)
        s.update(active=True, demo=False, t=self.t)
        if self.scene == "talk" and self.t0 is not None:
            s.update(talk=True, talk_t=self.t0)
        return s

    def want(self):
        pass


_scene = {"key": None, "r": None, "audio": None, "steps": 0}
SCENE_FPS = 10                           # Bilder je Sekunde der bewegten Vorschau (je Abruf ein Bild)


def render_scene(style, settings, scene, step):
    """Bewegte Vorschau: Bild Nummer step der Szene (Abspielen, Höhepunkt, Wortbeitrag, Gag). step 0 beginnt neu:
    1,5 s Vorlauf (Figuren kommen ins Bild), dann wird die Szene erzwungen (vis_force)."""
    with _preview_lock:
        s = _lenient(settings)
        style = style if style in g.VISUAL_STYLES else s["visual"]["style"]
        scene = scene if any(scene == sid for sid, _ in g.vis_scenes(style)) else "play"
        if scene.startswith("feier:"):
            s["visual"]["xmas"]["party"] = "on"
        key = (style, scene)
        if int(step) == 0 or _scene["key"] != key or _scene["r"] is None:
            r = g.Renderer()
            r.settings = s
            r.visual_style = style
            r.visible = [g.PAGE_IDS.index("visual")]
            r.profile_name = ""
            audio = _SceneAudio(scene)
            r.visual = audio
            r._party_wx = (time.monotonic() + 1e9, (None, None, None))
            for _ in range(int(1.5 * 15)):
                audio.t += 1 / 15
                r.render(g.PAGE_IDS.index("visual"), "M1", {})
            audio.t0 = audio.t
            g.vis_force(r, style, scene, audio.t)
            _scene.update(key=key, r=r, audio=audio, steps=0)
        r, audio = _scene["r"], _scene["audio"]
        r.settings = s
        audio.t += 1 / SCENE_FPS
        img = r.render(g.PAGE_IDS.index("visual"), "M1", {})
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()


def render_preview(page, layer, settings, pidx=0, colors=None, name=None, face=None, style=None):
    global _renderer
    with _preview_lock:
        if _renderer is None:
            _renderer = g.Renderer()
        s = _lenient(settings)
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
        _renderer.visual_style = style if style in g.VISUAL_STYLES else s["visual"]["style"]
        _renderer.profile_name = (name if name is not None else prof["name"]) if len(profiles) > 1 else ""
        img = _renderer.render(int(page) % len(g.PAGE_NAMES), layer if layer in g.LAYERS else "M1",
                               prof["keys"])
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
