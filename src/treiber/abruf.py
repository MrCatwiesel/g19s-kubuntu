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
def http_get(url, timeout=12, user=None, password=None, limit=10 * 1024 * 1024):
    import base64
    import urllib.request
    headers = {"User-Agent": "g19s/1.0"}
    if user:
        token = base64.b64encode(f"{user}:{password or ''}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
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
                    self.error = str(getattr(ex, "reason", None) or ex)
                self.updated = time.time() - self.interval + 120     # nach 2 Minuten erneut
            self.wake.wait(5)
            self.wake.clear()
