"""HTTP-Server der Verwaltung: Anfragen prüfen (Host, Zugangsschlüssel) und an die api_*-Methoden verteilen.

Eine Route /api/a/b mit Methode POST ruft api_post_a_b() auf; die Routen stehen nach Themen in api_*.py."""


# --------------------------------------------------------------------------- #
# HTTP-Server
# --------------------------------------------------------------------------- #
class App:
    def __init__(self, token):
        self.token = token
        self.port = 0
        self.first_contact = None
        self.last_contact = time.monotonic()
        self.started = time.monotonic()
        self.server = None
        self.restart = None       # nach einem Update: {"backup": Pfad der alten Verwaltung}
        self.github_update = None # von GitHub geladene neuere Dateien {Bauteil: (Name, Bytes)}
        self.tickets = {}         # Einmal-Code → Ablaufzeit (zum Öffnen im Browser, siehe new_ticket)

    TICKET_TTL = 120

    def new_ticket(self):
        """Einmal-Code für die Browser-Adresse: Die Adresse steht in der Prozessliste (für alle Benutzer
        sichtbar), der Code taugt aber nur für einen Aufruf innerhalb von TICKET_TTL Sekunden."""
        now = time.monotonic()
        self.tickets = {k: v for k, v in self.tickets.items() if v > now}
        ticket = secrets.token_urlsafe(18)
        self.tickets[ticket] = now + self.TICKET_TTL
        return ticket

    def redeem_ticket(self, ticket):
        expires = self.tickets.pop(str(ticket or ""), 0)
        return self.token if expires > time.monotonic() else None


class Handler(ApiKeys, ApiRadio, ApiInfo, ApiSlides, ApiService, http.server.BaseHTTPRequestHandler):
    app: App = None
    server_version = "g19s-gui"

    def log_message(self, fmt, *args):
        pass

    # -- Hilfen ------------------------------------------------------------ #
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host in (f"127.0.0.1:{self.app.port}", f"localhost:{self.app.port}")

    def _auth(self, query):
        token = self.headers.get("X-Token") or ""        # nie in der Adresse (Verlauf, Downloadliste)
        return secrets.compare_digest(token, self.app.token)

    def _body(self, limit=20 * 1024 * 1024):
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise ValueError("Anfrage zu groß")
        return self.rfile.read(length)

    def _json(self):
        raw = self._body()
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _touch(self):
        now = time.monotonic()
        self.app.last_contact = now
        if self.app.first_contact is None:
            self.app.first_contact = now

    # -- Routing ----------------------------------------------------------- #
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        if not self._host_ok():
            return self._send(403, {"error": "Zugriff verweigert"})
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)
        if method == "GET" and url.path in ("/", "/index.html"):
            # Nur das eigene Skript /app.js darf laufen (kein Inline-Skript); Bilder/Ton dürfen von außen
            # kommen (Senderlogos, Probehören), Einbetten in fremde Seiten ist verboten.
            return self._send(200, PAGE_HTML, "text/html; charset=utf-8",
                              {"Content-Security-Policy":
                               "default-src 'none'; script-src 'self'; connect-src 'self'; "
                               "style-src 'unsafe-inline'; img-src 'self' data: blob: https: http:; "
                               "media-src https: http:; frame-ancestors 'none'; base-uri 'none'; "
                               "form-action 'none'",
                               "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})
        if method == "GET" and url.path == "/app.js":           # enthält keine Geheimnisse
            return self._send(200, PAGE_JS, "text/javascript; charset=utf-8")
        if not url.path.startswith("/api/"):
            return self._send(404, {"error": "Nicht gefunden"})
        if method == "POST" and url.path == "/api/ticket":     # Einmal-Code gegen Schlüssel tauschen
            try:
                token = self.app.redeem_ticket(self._json().get("ticket"))
            except (ValueError, AttributeError):
                token = None
            return self._send(200, {"token": token}) if token else self._send(403, {"error": "Code ungültig"})
        if not self._auth(query):
            return self._send(401, {"error": "Sitzung ungültig – bitte die Verwaltung neu öffnen"})
        self._touch()
        route = getattr(self, f"api_{method.lower()}_{url.path[5:].replace('/', '_').replace('.', '_')}", None)
        if route is None:
            return self._send(404, {"error": "Unbekannte Funktion"})
        try:
            route(query)
        except (ValueError, RuntimeError) as ex:
            self._send(400, {"error": str(ex)})
        except Exception as ex:  # unerwartet – trotzdem sauber antworten
            self._send(500, {"error": f"{type(ex).__name__}: {ex}"})
