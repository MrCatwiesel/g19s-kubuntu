"""Kalender: iCalendar einlesen, Serientermine, Zeitzonen, Nextcloud/CalDAV-Suche, Abruf."""


# --- Termine aus iCalendar-Adressen (Google, Nextcloud, …) ---------------------
WINDOWS_TZ = {"W. Europe Standard Time": "Europe/Berlin", "Central Europe Standard Time": "Europe/Budapest",
              "Romance Standard Time": "Europe/Paris", "GMT Standard Time": "Europe/London",
              "UTC": "UTC", "Coordinated Universal Time": "UTC"}
WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _ics_unescape(v):
    return (v.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\")).strip()


def _ics_time(value, params):
    """Wert eines DTSTART/DTEND → (datetime mit Zeitzone | date, ganztägig?)"""
    import datetime as dt
    from zoneinfo import ZoneInfo
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return dt.date(int(value[:4]), int(value[4:6]), int(value[6:8])), True
    m = re.fullmatch(r"(\d{8})T(\d{6})(Z?)", value)
    if not m:
        raise ValueError(f"Zeitangabe nicht lesbar: {value}")
    naive = dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    if m.group(3):
        return naive.replace(tzinfo=dt.timezone.utc), False
    tzid = params.get("TZID", "").strip('"')
    if tzid:
        try:
            return naive.replace(tzinfo=ZoneInfo(WINDOWS_TZ.get(tzid, tzid))), False
        except (KeyError, ValueError):       # unbekannte Zeitzone (ZoneInfoNotFoundError ist ein KeyError)
            pass
    return naive.astimezone(), False          # „schwebende“ Zeit = Ortszeit


def parse_ics(text):
    """Liest VEVENTs: [{uid, summary, location, start, end, allday, rrule, exdates, recurrence_id}]"""
    import datetime as dt
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {"exdates": set()}
            continue
        if line == "END:VEVENT":
            if cur and "start" in cur and cur.get("status") != "CANCELLED":
                events.append(cur)
            cur = None
            continue
        if cur is None or ":" not in line:
            continue
        head, value = line.split(":", 1)
        name, *pp = head.split(";")
        params = dict(p.split("=", 1) for p in pp if "=" in p)
        name = name.upper()
        try:
            if name == "DTSTART":
                cur["start"], cur["allday"] = _ics_time(value, params)
            elif name == "DTEND":
                cur["end"], _ = _ics_time(value, params)
            elif name == "DURATION":
                m = re.fullmatch(r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", value.strip())
                if m:
                    w, dd, h, mi, se = (int(x or 0) for x in m.groups())
                    cur["duration"] = dt.timedelta(weeks=w, days=dd, hours=h, minutes=mi, seconds=se)
            elif name == "SUMMARY":
                cur["summary"] = _ics_unescape(value)
            elif name == "LOCATION":
                cur["location"] = _ics_unescape(value)
            elif name == "DESCRIPTION":
                cur["description"] = _ics_unescape(value.replace("\\n", "\x00").replace("\\N", "\x00")).replace("\x00", "\n")[:2000]
            elif name == "UID":
                cur["uid"] = value.strip()
            elif name == "STATUS":
                cur["status"] = value.strip().upper()
            elif name == "RRULE":
                cur["rrule"] = dict(p.split("=", 1) for p in value.strip().split(";") if "=" in p)
            elif name == "EXDATE":
                for v in value.split(","):
                    t, _ = _ics_time(v, params)
                    cur["exdates"].add(t)
            elif name == "RECURRENCE-ID":
                cur["recurrence_id"], _ = _ics_time(value, params)
        except ValueError:
            continue
    for e in events:
        if "end" not in e:
            e["end"] = e["start"] + e.get("duration", dt.timedelta(days=1) if e["allday"] else dt.timedelta(0))
    return events


def _add_months(d, months):
    import calendar
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    if d.day > calendar.monthrange(y, m)[1]:
        return None                                  # z. B. 31. im Februar: fällt aus
    return d.replace(year=y, month=m)


def _rrule_starts(ev, window_end, limit=3000):
    """Erzeugt die Anfangszeitpunkte einer Serie (in der Wandzeit des Originals)."""
    import calendar
    import datetime as dt
    rule, start = ev["rrule"], ev["start"]
    freq = rule.get("FREQ", "").upper()
    interval = max(1, int(rule.get("INTERVAL", "1") or 1))
    count = int(rule["COUNT"]) if rule.get("COUNT", "").isdigit() else None
    until = None
    if rule.get("UNTIL"):
        try:
            until, _ = _ics_time(rule["UNTIL"], {})
        except ValueError:
            until = None
    byday = [x.strip() for x in rule.get("BYDAY", "").split(",") if x.strip()]
    bymonthday = [int(x) for x in rule.get("BYMONTHDAY", "").split(",") if x.strip().lstrip("-").isdigit()]

    def before_until(t):
        if until is None:
            return True
        if isinstance(t, dt.datetime) and not isinstance(until, dt.datetime):
            return t.date() <= until
        if isinstance(t, dt.datetime) and isinstance(until, dt.datetime):
            return t <= until
        return (t.date() if isinstance(t, dt.datetime) else t) <= (until.date() if isinstance(until, dt.datetime) else until)

    def day_of(t):
        return t.date() if isinstance(t, dt.datetime) else t

    def at_day(day):
        return start.replace(year=day.year, month=day.month, day=day.day) if isinstance(start, dt.datetime) else day

    produced = 0
    step = 0
    while produced < limit:
        cands = []
        if freq == "DAILY":
            cands = [at_day(day_of(start) + dt.timedelta(days=step * interval))]
        elif freq == "WEEKLY":
            week0 = day_of(start) - dt.timedelta(days=day_of(start).weekday())
            week = week0 + dt.timedelta(weeks=step * interval)
            days = [WEEKDAY_CODES.index(b[-2:]) for b in byday if b[-2:] in WEEKDAY_CODES] or [day_of(start).weekday()]
            cands = [at_day(week + dt.timedelta(days=wd)) for wd in sorted(set(days))]
        elif freq in ("MONTHLY", "YEARLY"):
            months = step * interval * (12 if freq == "YEARLY" else 1)
            first = _add_months(day_of(start).replace(day=1), months)
            if first is None:
                step += 1
                continue
            last_day = calendar.monthrange(first.year, first.month)[1]
            days = []
            if bymonthday:
                days = [(md if md > 0 else last_day + md + 1) for md in bymonthday]
            elif byday:
                for b in byday:
                    m = re.fullmatch(r"([+-]?\d+)?(MO|TU|WE|TH|FR|SA|SU)", b)
                    if not m:
                        continue
                    wd = WEEKDAY_CODES.index(m.group(2))
                    hits = [dd for dd in range(1, last_day + 1) if first.replace(day=dd).weekday() == wd]
                    n = int(m.group(1)) if m.group(1) else None
                    days += hits if n is None else ([hits[n - 1]] if n > 0 and n <= len(hits) else
                                                    [hits[n]] if n < 0 and -n <= len(hits) else [])
            else:
                days = [day_of(start).day]
            cands = [at_day(first.replace(day=dd)) for dd in sorted(set(days)) if 1 <= dd <= last_day]
        else:
            yield start
            return
        for t in cands:
            if t < start:
                continue
            if not before_until(t) or (count is not None and produced >= count):
                return
            produced += 1
            yield t
        first_c = cands[0] if cands else None
        if first_c is not None and (first_c.date() if isinstance(first_c, dt.datetime) else first_c) > window_end:
            return
        step += 1
        if step > 20000:
            return


def expand_events(events, days_ahead=14, now=None):
    """Alle Termine ab heute (inkl. laufender) bis `days_ahead` Tage, sortiert."""
    import datetime as dt
    now = now or dt.datetime.now().astimezone()
    today = now.date()
    window_end = today + dt.timedelta(days=days_ahead)
    overrides = {}
    for e in events:
        if e.get("recurrence_id") is not None:
            overrides.setdefault(e.get("uid"), set()).add(e["recurrence_id"])
    out = []
    for e in events:
        duration = e["end"] - e["start"]
        starts = _rrule_starts(e, window_end) if e.get("rrule") and e.get("recurrence_id") is None else [e["start"]]
        for s in starts:
            day = s.date() if isinstance(s, dt.datetime) else s
            if day > window_end:
                break
            if s in e["exdates"] or s in overrides.get(e.get("uid"), ()):
                continue
            end = s + duration
            if e["allday"]:
                if end <= today and not (end == s == today):
                    continue
            elif end.astimezone() <= now:
                continue
            if not e["allday"]:
                s, end = s.astimezone(), end.astimezone()      # in Ortszeit anzeigen
            out.append({"start": s, "end": end, "allday": e["allday"],
                        "title": e.get("summary") or "(ohne Titel)", "location": e.get("location", ""),
                        "description": e.get("description", "")})
    key = lambda x: (x["start"] if isinstance(x["start"], dt.datetime) else
                     dt.datetime.combine(x["start"], dt.time.min).astimezone())
    out.sort(key=key)
    return out


def calendar_url(url):
    """Macht aus den üblichen Kalender-Links eine abrufbare .ics-Adresse.

    Nextcloud: öffentliche Freigabe-Links (/apps/calendar/p/TOKEN) werden auf
    /remote.php/dav/public-calendars/TOKEN?export umgeschrieben, CalDAV-Adressen
    (/remote.php/dav/calendars/BENUTZER/KALENDER/) bekommen ?export angehängt."""
    import urllib.parse
    url = str(url or "").strip()
    url = re.sub(r"^webcal(s)?://", "https://", url, flags=re.I)
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parts = urllib.parse.urlsplit(url)
    path = parts.path
    m = re.search(r"^(.*?)/(?:index\.php/)?apps/calendar/(?:p|embed|public)/([A-Za-z0-9]+)", path)
    if m:
        path = f"{m.group(1)}/remote.php/dav/public-calendars/{m.group(2)}"
    if re.search(r"/remote\.php/(?:dav|caldav)/(?:calendars/[^/]+/[^/]+|public-calendars/[^/]+)/?$", path):
        query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
        if "export" not in query:
            q = parts.query + ("&" if parts.query else "") + "export"
            return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, q, ""))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def is_single_calendar(url):
    """True, wenn die Adresse auf genau einen Kalender (bzw. eine .ics-Datei) zeigt."""
    import urllib.parse
    path = urllib.parse.urlsplit(url).path
    if "/remote.php/" not in path and path.strip("/") != "":
        return True                                   # normale .ics-Adresse (Google, Webseite …)
    return bool(re.search(r"/remote\.php/(?:dav|caldav)/(?:calendars/[^/]+/[^/]+|public-calendars/[^/]+)/?$", path))


def dav_request(url, method, body, user, password, depth="0", timeout=30):
    import urllib.request
    headers = {"User-Agent": USER_AGENT, "Depth": depth, "Content-Type": "application/xml; charset=utf-8"}
    if user:
        headers["Authorization"] = basic_auth(user, password)
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method=method)
    with open_url(req, timeout) as r:
        return r.read(4 * 1024 * 1024)


def discover_calendars(url, user, password):
    """Sucht über CalDAV alle Terminkalender eines Kontos (z. B. Nextcloud).

    Nimmt eine allgemeine Adresse wie https://cloud.example.de/remote.php/dav oder
    https://cloud.example.de und liefert [{"name", "url", "color"}] mit Export-Adressen."""
    import urllib.parse
    import xml.etree.ElementTree as ET
    D, C, A = "{DAV:}", "{urn:ietf:params:xml:ns:caldav}", "{http://apple.com/ns/ical/}"
    parts = urllib.parse.urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    path = parts.path
    m = re.search(r"^(.*?)/remote\.php/", path)
    prefix = m.group(1) if m else path.rstrip("/")
    dav = f"{origin}{prefix}/remote.php/dav/"

    def props(href, xml_props, depth="0"):
        body = ('<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" '
                f'xmlns:a="http://apple.com/ns/ical/"><d:prop>{xml_props}</d:prop></d:propfind>')
        target = urllib.parse.urljoin(origin, href)
        if not same_origin(target, origin):         # Zugangsdaten nie an einen anderen Server schicken
            raise ValueError("Der Server verweist auf einen anderen Server – Kalendersuche abgebrochen")
        raw = dav_request(target, "PROPFIND", body, user, password, depth)
        try:
            return ET.fromstring(raw).findall(f"{D}response")
        except ET.ParseError:
            raise ValueError("Die Adresse ist kein CalDAV-Zugang – bitte die Adresse der Nextcloud eintragen")

    home = None
    if not user:
        raise ValueError("Für die Kalendersuche Benutzer und App-Passwort eintragen "
                         "(oder die Adresse eines einzelnen Kalenders)")
    resp = props(dav, "<d:current-user-principal/>")
    href = next((e.text for r in resp for e in r.iter(f"{D}href")
                 if e.text and "principals" in e.text), None)
    if href:
        resp = props(href, "<c:calendar-home-set/>")
        home = next((e.text for r in resp for h in r.iter(f"{C}calendar-home-set")
                     for e in h.iter(f"{D}href") if e.text), None)
    if not home:
        home = f"{prefix}/remote.php/dav/calendars/{urllib.parse.quote(user)}/"
    found = []
    for r in props(home, "<d:resourcetype/><d:displayname/><c:supported-calendar-component-set/>"
                         "<a:calendar-color/>", depth="1"):
        rtype = r.find(f".//{D}resourcetype")
        if rtype is None or rtype.find(f"{C}calendar") is None:
            continue                                    # Posteingang, Papierkorb, Abos …
        comps = [c.get("name") for c in r.iter(f"{C}comp")]
        if comps and "VEVENT" not in comps:
            continue                                    # reine Aufgabenlisten
        h = r.findtext(f"{D}href") or ""
        name = (r.findtext(f".//{D}displayname") or "").strip() or urllib.parse.unquote(h.rstrip("/").split("/")[-1])
        color = None
        cm = re.match(r"#?([0-9a-fA-F]{6})", (r.findtext(f".//{A}calendar-color") or "").strip())
        if cm:
            color = [int(cm.group(1)[i:i + 2], 16) for i in (0, 2, 4)]
        cal_url = urllib.parse.urljoin(origin, h)
        if not same_origin(cal_url, origin):
            continue                                    # Kalender auf fremdem Server: ignorieren
        found.append({"name": name, "url": cal_url + "?export", "color": color})
    if not found:
        raise ValueError("Keine Terminkalender in diesem Konto gefunden")
    return found


CAL_COLORS = [(76, 141, 255), (62, 207, 126), (240, 169, 59), (235, 90, 150), (160, 120, 255), (60, 200, 220)]


def calendar_key(url):
    """Kurzer, stabiler Schlüssel je Kalender (die Adresse selbst kann geheim sein)."""
    import hashlib
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def calendar_error(ex, url):
    """Verständliche Fehlermeldung für den Kalenderabruf."""
    import urllib.error
    nc = "/remote.php/" in url
    if isinstance(ex, urllib.error.HTTPError):
        if ex.code == 401:
            return ("Anmeldung fehlgeschlagen – bei Nextcloud den Benutzernamen und ein App-Passwort "
                    "verwenden (Persönliche Einstellungen → Sicherheit)" if nc else
                    "Anmeldung fehlgeschlagen – Benutzer/Passwort prüfen")
        if ex.code == 403:
            return "Zugriff verweigert (403) – ist der Kalender für diesen Benutzer freigegeben?"
        if ex.code == 404:
            return ("Kalender nicht gefunden (404) – Adresse über „Interne Adresse kopieren“ "
                    "bzw. „Link kopieren“ in der Nextcloud-Kalender-App holen" if nc else
                    "Kalender nicht gefunden (404) – Adresse prüfen")
        if ex.code == 429:
            return "Zu viele Fehlversuche – Nextcloud bremst gerade, in einigen Minuten erneut versuchen"
        return f"Server antwortet mit Fehler {ex.code}"
    reason = err_text(ex)
    if "CERTIFICATE_VERIFY_FAILED" in reason:
        return "Das Zertifikat des Servers ist ungültig oder selbst signiert"
    if "WRONG_VERSION_NUMBER" in reason or "wrong version number" in reason:
        return "Der Server unterstützt kein https – Adresse mit http:// eintragen"
    if "timed out" in reason:
        return "Keine Antwort vom Server (Zeitüberschreitung)"
    if "Name or service not known" in reason or "Temporary failure in name resolution" in reason:
        return "Servername unbekannt – Adresse prüfen"
    return reason


class CalendarPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 900, log)

    def cfg(self):
        return self.get_settings().get("calendar") or {}

    def enabled(self):
        return bool(self.cfg().get("sources")) and "calendar" in (self.get_settings().get("pages") or [])

    def signature(self):
        c = self.cfg()
        return json.dumps([c.get("sources"), c.get("days")], sort_keys=True)

    def fetch(self):
        c = self.cfg()
        items, errors, found, cal_list = [], [], [], []
        for i, src in enumerate(c.get("sources") or []):
            url = str(src.get("url") or "").strip()
            if not url:
                continue
            url = calendar_url(url)
            user, password = src.get("user"), src.get("password")
            try:
                if is_single_calendar(url):
                    targets = [{"name": None, "url": url, "color": None}]
                    if user and "/remote.php/" not in url and not url.lower().split("?")[0].endswith(".ics"):
                        try:                         # evtl. nur die Adresse der Nextcloud eingetragen
                            text = http_get(url, timeout=30, user=user, password=password).decode("utf-8", "replace")
                            probe_ok = "BEGIN:VCALENDAR" in text
                        except NET_ERRORS:
                            probe_ok = False
                        if not probe_ok:
                            try:
                                targets = discover_calendars(url, user, password)
                                found.extend(t["name"] for t in targets)
                            except FEED_ERRORS:
                                pass                 # kein CalDAV: normale Fehlermeldung unten
                else:
                    targets = discover_calendars(url, user, password)   # ganzes Nextcloud-Konto
                    found.extend(t["name"] for t in targets)
            except Exception as ex:                  # ein kaputter Kalender darf die anderen nicht verhindern
                msg = str(ex) if isinstance(ex, ValueError) else calendar_error(ex, url)
                errors.append(f"{src.get('name') or 'Kalender'}: {msg}")
                continue
            src_color = src.get("color") if isinstance(src.get("color"), list) else None
            for t in targets:
                url = t["url"]
                key = calendar_key(url)
                multi = len(targets) > 1
                name = (t["name"] if multi else None) or src.get("name") or "Kalender"
                color = (t["color"] if multi else None) or src_color or list(CAL_COLORS[len(cal_list) % len(CAL_COLORS)])
                cal_list.append({"key": key, "name": name, "color": color})
                try:
                    text = http_get(url, timeout=30, user=user, password=password).decode("utf-8", "replace")
                    if "BEGIN:VCALENDAR" not in text:
                        if re.search(r"WebDAV interface|<html|<!doctype", text[:2000], re.I):
                            raise ValueError("Die Adresse liefert eine Webseite statt Kalenderdaten – bei Nextcloud "
                                             "die Adresse der Nextcloud (mit Benutzer und App-Passwort) oder im "
                                             "Kalender-Menü „Interne Adresse kopieren“ verwenden")
                        raise ValueError("keine iCalendar-Daten")
                    for ev in expand_events(parse_ics(text), int(c.get("days") or 14)):
                        ev["source"], ev["cal"], ev["color"] = i, key, color
                        items.append(ev)
                except Exception as ex:              # dito, je einzelnem Kalender
                    msg = str(ex) if isinstance(ex, ValueError) else calendar_error(ex, url)
                    errors.append(f"{name}: {msg}")
        if errors and not items:
            raise RuntimeError("; ".join(errors))
        import datetime as dt
        items.sort(key=lambda x: (x["start"] if isinstance(x["start"], dt.datetime) else
                                  dt.datetime.combine(x["start"], dt.time.min).astimezone()))
        return {"items": items, "errors": errors, "calendars": found, "calendar_list": cal_list}
