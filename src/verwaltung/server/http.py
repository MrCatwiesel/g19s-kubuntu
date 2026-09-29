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
        token = self.headers.get("X-Token") or query.get("token", [""])[0]
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
            return self._send(200, PAGE_HTML, "text/html; charset=utf-8",
                              {"Content-Security-Policy":
                               "default-src 'self'; img-src 'self' data: https: http:; "
                               "style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                               "media-src https: http:"})
        if not url.path.startswith("/api/"):
            return self._send(404, {"error": "Nicht gefunden"})
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
