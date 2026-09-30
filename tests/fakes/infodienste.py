import http.server, json, urllib.parse, base64
ICS = """BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:a\r\nSUMMARY:Teamrunde Projekt Nordlicht\r\nLOCATION:Besprechungsraum 2\, 3. OG\r\nDESCRIPTION:Tagesordnung:\\n1. Stand der Arbeiten\\n2. Termine Oktober\\n3. Verschiedenes\\n\\nBitte Unterlagen mitbringen. Zugang über den Seiteneingang\, Code 4711.\r\nDTSTART;TZID=Europe/Berlin:20260901T100000\r\nDTEND;TZID=Europe/Berlin:20260901T110000\r\nRRULE:FREQ=WEEKLY;BYDAY=MO,WE\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nUID:b\r\nSUMMARY:Zahnarzt\r\nDTSTART:20261001T074500Z\r\nDURATION:PT45M\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"""

DAV_DIRS = {"/nc/remote.php/dav/files/mde@example.de/", "/dav/", "/dav/home/", "/dav/home/Sicherungen/"}
DAV_FILES = {}
NCAUTH = "Basic " + base64.b64encode(b"mde@example.de:app-pw").decode()
import datetime as _dt
# Geburtstag immer „morgen“ (sonst fällt er je nach Testdatum aus dem 30-Tage-Fenster)
BDAY = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:bd\r\nSUMMARY:Geburtstag Oma\r\nDTSTART;VALUE=DATE:"
        + (_dt.date.today() + _dt.timedelta(days=1)).strftime("%Y%m%d") + "\r\nRRULE:FREQ=YEARLY\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
def resp(href, props):
    return f"<d:response><d:href>{href}</d:href><d:propstat><d:prop>{props}</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
def ms(*r):
    return '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" xmlns:cal="urn:ietf:params:xml:ns:caldav" xmlns:x1="http://apple.com/ns/ical/" xmlns:s="http://sabredav.org/ns">' + "".join(r) + "</d:multistatus>"
CAL = '<d:resourcetype><d:collection/><cal:calendar/></d:resourcetype>'
def comps(*c): return "<cal:supported-calendar-component-set>" + "".join(f'<cal:comp name="{x}"/>' for x in c) + "</cal:supported-calendar-component-set>"
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body, ctype="application/json", code=200):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", len(b)); self.end_headers(); self.wfile.write(b)

    # --- WebDAV-Dateien (Nextcloud /nc/remote.php/dav/files/<user>/…, NAS /dav/…) für die Sicherung ---
    def _dav(self):
        p = urllib.parse.unquote(self.path.split("?")[0])
        if p.startswith("/nc/remote.php/dav/files/"):
            return p, NCAUTH
        if p.startswith("/dav/"):
            return p, "Basic " + base64.b64encode(b"nas:pw").decode()
        return None, None
    def _dav_auth(self):
        p, auth = self._dav()
        if p is None:
            return None
        if self.headers.get("Authorization") != auth:
            self.send("<d:error/>", "application/xml", 401); return False
        return p
    def do_MKCOL(self):
        p = self._dav_auth()
        if not p: return p is None and self.send("nope", "text/plain", 404)
        p = p.rstrip("/") + "/"
        if p in DAV_DIRS: return self.send("", "text/plain", 405)
        if p.rstrip("/").rsplit("/", 1)[0] + "/" not in DAV_DIRS: return self.send("", "text/plain", 409)
        DAV_DIRS.add(p); self.send("", "text/plain", 201)
    def do_PUT(self):
        p = self._dav_auth()
        if not p: return p is None and self.send("nope", "text/plain", 404)
        data = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if p.rsplit("/", 1)[0] + "/" not in DAV_DIRS: return self.send("", "text/plain", 409)
        DAV_FILES[p] = data; self.send("", "text/plain", 201)
    def do_DELETE(self):
        p = self._dav_auth()
        if not p: return p is None and self.send("nope", "text/plain", 404)
        if DAV_FILES.pop(p, None) is None: return self.send("", "text/plain", 404)
        self.send("", "text/plain", 204)
    def do_PROPFIND(self):
        n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
        if self._dav()[0] is not None:
            p = self._dav_auth()
            if not p: return
            d = p.rstrip("/") + "/"
            if d not in DAV_DIRS: return self.send("nope", "text/plain", 404)
            kids = [f for f in DAV_FILES if f.rsplit("/", 1)[0] + "/" == d] if self.headers.get("Depth") == "1" else []
            return self.send(ms(resp(urllib.parse.quote(d), "<d:resourcetype><d:collection/></d:resourcetype>"),
                                *[resp(urllib.parse.quote(k), "<d:resourcetype/>") for k in kids]), "application/xml", 207)
        if self.headers.get("Authorization") != NCAUTH:
            return self.send("<d:error/>", "application/xml", 401)
        p = self.path.split("?")[0]
        if p in ("/nc/remote.php/dav/", "/nc/remote.php/dav"):
            return self.send(ms(resp("/nc/remote.php/dav/", "<d:current-user-principal><d:href>/nc/remote.php/dav/principals/users/mde/</d:href></d:current-user-principal>")), "application/xml", 207)
        if p == "/nc/remote.php/dav/principals/users/mde/":
            return self.send(ms(resp(p, "<cal:calendar-home-set><d:href>/nc/remote.php/dav/calendars/mde/</d:href></cal:calendar-home-set>")), "application/xml", 207)
        if p == "/nc/remote.php/dav/calendars/mde/" and self.headers.get("Depth") == "1":
            return self.send(ms(
                resp(p, "<d:resourcetype><d:collection/></d:resourcetype>"),
                resp(p + "personal/", CAL + "<d:displayname>Persönlich</d:displayname>" + comps("VEVENT", "VTODO") + "<x1:calendar-color>#0082C9</x1:calendar-color>"),
                resp(p + "aufgaben/", CAL + "<d:displayname>Aufgaben</d:displayname>" + comps("VTODO")),
                resp(p + "contact_birthdays/", CAL + "<d:displayname>Geburtstage von Kontakten</d:displayname>" + comps("VEVENT") + "<x1:calendar-color>#E9322DFF</x1:calendar-color>"),
                resp(p + "marco/", CAL + "<d:displayname>Marco</d:displayname>" + comps("VEVENT") + "<x1:calendar-color>#F4A331</x1:calendar-color>"),
                resp(p + "birgit-marco_shared_by_birgit/", CAL + "<d:displayname>Birgit &amp; Marco</d:displayname>" + comps("VEVENT") + "<x1:calendar-color>#A56DE4</x1:calendar-color>"),
                resp(p + "birgit_shared_by_birgit/", CAL + "<d:displayname>Birgit</d:displayname>" + comps("VEVENT") + "<x1:calendar-color>#E454A5</x1:calendar-color>"),
                resp(p + "geburtstage/", CAL + "<d:displayname>Geburtstage</d:displayname>" + comps("VEVENT") + "<x1:calendar-color>#31CC7C</x1:calendar-color>"),
                resp(p + "inbox/", '<d:resourcetype><d:collection/><cal:schedule-inbox/></d:resourcetype>'),
                resp(p + "trashbin/", '<d:resourcetype><d:collection/><s:deleted-calendars/></d:resourcetype>')), "application/xml", 207)
        self.send("nope", "text/plain", 404)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        # Weiterleitungen für den Sicherheitstest: fremder Host (localhost statt 127.0.0.1) bzw. gleicher Host
        if u.path in ("/umleitung-fremd", "/umleitung-gleich"):
            host = "localhost" if u.path.endswith("fremd") else "127.0.0.1"
            self.send_response(302); self.send_header("Location", f"http://{host}:8812/echo-auth")
            self.send_header("Content-Length", "0"); self.end_headers(); return
        if u.path == "/echo-auth":
            return self.send(self.headers.get("Authorization") or "-", "text/plain")
        if u.path == "/v1/search":
            res = [{"name": "Leipzig", "latitude": 51.34, "longitude": 12.37, "admin1": "Sachsen", "country": "Deutschland"},
                   {"name": "Leipzig", "latitude": 46.9, "longitude": 29.4, "country": "Ukraine"}] if "leip" in q["name"][0].lower() else []
            return self.send(json.dumps({"results": res}))
        if u.path == "/v1/forecast":
            return self.send(json.dumps({"current": {"temperature_2m": 14.6, "apparent_temperature": 13, "relative_humidity_2m": 70, "weather_code": 3, "wind_speed_10m": 9, "is_day": 1},
                                         "daily": {"time": ["2026-09-27", "2026-09-28", "2026-09-29"], "weather_code": [3, 61, 0], "temperature_2m_max": [16, 14, 19], "temperature_2m_min": [8, 9, 7], "precipitation_probability_max": [20, 70, 5]}}))
        if u.path == "/privat.ics":
            if self.headers.get("Authorization") != "Basic " + base64.b64encode(b"max:geheim").decode():
                return self.send("unauthorized", "text/plain", 401)
            return self.send(ICS, "text/calendar")
        if u.path.startswith("/remote.php/dav/calendars/max/personal"):
            if self.headers.get("Authorization") != "Basic " + base64.b64encode(b"max:app-passwort").decode():
                return self.send("<?xml version='1.0'?><d:error>NotAuthenticated</d:error>", "application/xml", 401)
            if "export" not in q and "export" not in u.query:
                return self.send("<!DOCTYPE html><html><body>sabre/dav Nodes</body></html>", "text/html")
            return self.send(ICS, "text/calendar")
        if u.path.startswith("/remote.php/dav/public-calendars/TOK123"):
            if "export" not in u.query:
                return self.send("<!DOCTYPE html><html>Browser</html>", "text/html", 501)
            return self.send(ICS, "text/calendar")
        if u.path.startswith("/nc/remote.php/dav"):
            if u.path.rstrip("/") == "/nc/remote.php/dav":
                return self.send("This is the WebDAV interface. It can only be accessed by WebDAV clients such as the Nextcloud desktop sync client.", "text/html; charset=UTF-8")
            if self.headers.get("Authorization") != NCAUTH:
                return self.send("<d:error/>", "application/xml", 401)
            if u.path == "/nc/remote.php/dav/calendars/mde/personal/" and u.query == "export":
                return self.send(ICS, "text/calendar")
            extra = {"marco": ("Fußball Training", "20261001T180000"), "birgit-marco_shared_by_birgit": ("Elternabend", "20261002T193000"),
                     "birgit_shared_by_birgit": ("Yoga", "20260930T090000"), "geburtstage": ("Geburtstag Tante Erna", None)}
            nm = u.path.rstrip("/").split("/")[-1]
            if nm in extra and u.query == "export":
                t, st = extra[nm]
                dt = f"DTSTART;TZID=Europe/Berlin:{st}" if st else "DTSTART;VALUE=DATE:20261003"
                return self.send(f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:{nm}\r\nSUMMARY:{t}\r\n{dt}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n", "text/calendar")
            if u.path == "/nc/remote.php/dav/calendars/mde/contact_birthdays/" and u.query == "export":
                return self.send(BDAY, "text/calendar")
            return self.send("nope", "text/plain", 404)
        if u.path == "/bald.ics":
            import datetime as _dt
            st = (_dt.datetime.utcnow() + _dt.timedelta(minutes=8)).strftime("%Y%m%dT%H%M00Z")
            return self.send(f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:bald\r\nSUMMARY:Zahnarzt Dr. Müller\r\nLOCATION:Hauptstr. 5\r\nDTSTART:{st}\r\nDURATION:PT30M\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n", "text/calendar")
        if u.path == "/rss.xml":
            import email.utils as _eu, time as _t
            now = _t.time()
            items = "".join(f"<item><title>{t}</title><link>https://www.tagesschau.de/artikel{i}.html</link><pubDate>{_eu.formatdate(now - i * 1500)}</pubDate></item>"
                            for i, t in enumerate(["Bundestag beschließt Haushalt für 2027 nach langer Debatte", "Sturmtief zieht über Norddeutschland – Bahn stellt Fernverkehr teilweise ein",
                                                   "DAX schließt mit leichtem Plus", "Neue Regeln für E-Scooter ab Oktober"]))
            return self.send(f'<?xml version="1.0"?><rss version="2.0"><channel><title>tagesschau</title>{items}</channel></rss>', "application/rss+xml")
        if u.path == "/atom.xml":
            import datetime as _dt
            ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            return self.send(f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>heise</title><entry><title type="html">Linux-Kernel 7.2 &amp;lt;b&amp;gt;freigegeben&amp;lt;/b&amp;gt;</title>'
                             f'<link rel="alternate" href="https://www.heise.de/news/kernel.html"/><updated>{ts}</updated></entry></feed>', "application/atom+xml")
        if u.path == "/alerts":
            import datetime as _dt
            n = _dt.datetime.now(_dt.timezone.utc)
            iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            al = [{"id": 1, "alert_id": "a1", "status": "actual", "onset": iso(n - _dt.timedelta(hours=1)), "expires": iso(n + _dt.timedelta(hours=5)),
                   "severity": "moderate", "event_de": "STURMBÖEN", "headline_de": "Amtliche WARNUNG vor STURMBÖEN",
                   "description_de": "Es treten Sturmböen mit Geschwindigkeiten um 70 km/h aus westlicher Richtung auf.",
                   "instruction_de": "ACHTUNG! Hinweis auf mögliche Gefahren: Es können zum Beispiel einzelne Äste herabstürzen."},
                  {"id": 2, "alert_id": "a2", "status": "actual", "onset": iso(n + _dt.timedelta(hours=2)), "expires": iso(n + _dt.timedelta(hours=9)),
                   "severity": "minor", "event_de": "FROST", "headline_de": "Amtliche WARNUNG vor FROST", "description_de": "Es tritt leichter Frost um -2 °C auf.", "instruction_de": ""},
                  {"id": 3, "alert_id": "alt", "status": "actual", "onset": iso(n - _dt.timedelta(hours=9)), "expires": iso(n - _dt.timedelta(hours=1)),
                   "severity": "severe", "event_de": "GEWITTER", "headline_de": "abgelaufen", "description_de": "", "instruction_de": ""}]
            if "lat=0" in u.query: al = []
            return self.send(json.dumps({"alerts": al, "location": {"name": "Leipzig", "warn_cell_id": 814713000}}))
        if u.path == "/kaputt.ics":
            return self.send("<html>Login</html>", "text/html")
        self.send("nope", "text/plain", 404)
http.server.ThreadingHTTPServer(("127.0.0.1", 8812), H).serve_forever()
