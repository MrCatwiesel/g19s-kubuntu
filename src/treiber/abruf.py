"""Abruf aus dem Netz: http_get() und Poller (Hintergrund-Thread, der Daten regelmäßig holt,
solange die zugehörige Displayseite eingeschaltet ist)."""
import http.client
import xml.etree.ElementTree as ET

# Fehler beim Abruf aus dem Netz (Verbindung, HTTP, abgebrochene Antwort, Kodierung)
NET_ERRORS = (OSError, ValueError, http.client.HTTPException)
# … und beim Auswerten von XML (Feeds, CalDAV)
FEED_ERRORS = NET_ERRORS + (ET.ParseError,)


# --------------------------------------------------------------------------- #
# Hintergrund-Abrufe für Infoseiten (Wetter, Termine)
# --------------------------------------------------------------------------- #
USER_AGENT = f"g19s/{VERSION}"         # gleiche Kennung für alle Abrufe


def err_text(ex):
    """Kurzer Fehlertext für Meldungen (urllib-Fehler haben den eigentlichen Grund in .reason)."""
    return str(getattr(ex, "reason", None) or ex)


def basic_auth(user, password):
    """Kopfzeile für HTTP-Basic-Anmeldung."""
    import base64
    return "Basic " + base64.b64encode(f"{user}:{password or ''}".encode()).decode()


def _safe_opener():
    """urllib-Opener, der Zugangsdaten nicht an fremde Server weiterreicht: Bei einer Weiterleitung
    auf einen anderen Server oder von https auf http wird die Authorization-Kopfzeile entfernt."""
    import urllib.parse
    import urllib.request

    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new is not None:
                old_u, new_u = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(new.full_url)
                if (old_u.scheme, old_u.netloc) != (new_u.scheme, new_u.netloc):
                    for h in [k for k in new.headers if k.lower() == "authorization"]:
                        del new.headers[h]
                    new.unredirected_hdrs.pop("Authorization", None)
            return new

    return urllib.request.build_opener(SafeRedirect)


def open_url(req, timeout):
    """Wie urllib.request.urlopen, aber mit sicheren Weiterleitungen (siehe _safe_opener)."""
    return _safe_opener().open(req, timeout=timeout)


def same_origin(url, base):
    """True, wenn url auf demselben Server (Schema + Host + Port) liegt wie base."""
    import urllib.parse
    a, b = urllib.parse.urlsplit(url), urllib.parse.urlsplit(base)
    return (a.scheme.lower(), a.netloc.lower()) == (b.scheme.lower(), b.netloc.lower())


REMOTE_IMAGE_PIXELS = 25_000_000       # Bilder aus dem Netz: höchstens 25 Megapixel


def open_remote_image(raw, draft=(1280, 960)):
    """Bild aus dem Netz öffnen und die Größe VOR dem Dekodieren prüfen – ein präpariertes Bild
    (wenige MB, aber Hunderte Megapixel) würde sonst Gigabytes Speicher belegen."""
    import io
    try:
        im = Image.open(io.BytesIO(raw))
    except Image.DecompressionBombError as ex:
        raise ValueError(f"Bild zu groß: {ex}")
    w, h = im.size
    if w * h > REMOTE_IMAGE_PIXELS:
        raise ValueError(f"Bild zu groß ({w}×{h} Pixel)")
    if draft:
        im.draft("RGB", draft)                 # JPEG gleich verkleinert dekodieren
    return im


def http_get(url, timeout=12, user=None, password=None, limit=10 * 1024 * 1024):
    import urllib.request
    headers = {"User-Agent": USER_AGENT}
    if user:
        headers["Authorization"] = basic_auth(user, password)
    req = urllib.request.Request(url, headers=headers)
    with open_url(req, timeout) as r:
        return r.read(limit)


class Poller(threading.Thread):
    """Ruft fetch() alle `interval` Sekunden auf, sofern die Seite eingeschaltet ist."""

    def __init__(self, get_settings, interval, log=print):
        super().__init__(daemon=True)
        self.get_settings, self.interval, self.log = get_settings, interval, log
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.running = True
        self.data, self.error, self.updated = None, None, 0.0
        self.sig = None

    def enabled(self):
        return True

    def signature(self):
        return None

    def fetch(self):
        raise NotImplementedError

    def refresh(self):
        self.updated = 0.0
        self.wake.set()

    def snapshot(self):
        with self.lock:
            return self.data, self.error, self.updated

    def stop(self):
        self.running = False
        self.wake.set()

    def run(self):
        while self.running:
            try:
                sig = self.signature()
                if sig != self.sig:
                    self.sig, self.updated = sig, 0.0
                    with self.lock:
                        self.data, self.error = None, None
                if self.enabled() and time.time() - self.updated >= self.interval:
                    data = self.fetch()
                    with self.lock:
                        self.data, self.error, self.updated = data, None, time.time()
            except Exception as ex:          # Sicherheitsnetz: ein Dienst darf den Treiber nie beenden
                with self.lock:
                    self.error = err_text(ex)
                self.updated = time.time() - self.interval + 120     # nach 2 Minuten erneut
            self.wake.wait(5)
            self.wake.clear()
