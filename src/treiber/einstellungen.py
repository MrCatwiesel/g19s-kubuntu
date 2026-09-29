"""Einstellungen (settings.json): ein Schema für Treiber und Verwaltung.

Jedes Feld steht genau einmal in SCHEMA – mit Standardwert, erlaubten Werten
und der Fehlermeldung für die Verwaltung. Daraus entstehen:

  * DEFAULT_SETTINGS        die Standardwerte
  * load_settings()         Treiber: liest settings.json tolerant
                            (Ungültiges → Standardwert, unbekannte Schlüssel bleiben)
  * clean_settings(data)    Verwaltung: prüft streng (Ungültiges → ValueError mit
                            verständlicher Meldung), unbekannte Schlüssel entfallen
"""
import json
import os
import re


class Invalid(ValueError):
    """Ungültiger Wert; die Meldung ist für die Verwaltung formuliert."""


# --- Feldtypen --------------------------------------------------------------- #
class Field:
    def __init__(self, default, msg=None):
        self.default, self.msg = default, msg

    def fail(self, strict):
        if strict and self.msg:
            raise Invalid(self.msg)
        return json.loads(json.dumps(self.default))

    def clean(self, value, strict):
        return value


class Bool(Field):
    """Ja/Nein wie bisher: jeder „wahre“ Wert gilt als ja.
    only_false=True: alles außer false gilt als ja (Schalter, die standardmäßig an sind)."""
    def __init__(self, default, only_false=False):
        super().__init__(default)
        self.only_false = only_false

    def clean(self, value, strict):
        return value is not False if self.only_false else bool(value)


class Int(Field):
    """Ganze Zahl; außerhalb der Grenzen wird sie begrenzt, 0/leer = Standard (wenn zero=False).
    empty: Wert für leer/None (Standard: default); empty_lenient: dasselbe nur im Treiber."""
    def __init__(self, default, lo, hi, msg="Bitte eine gültige Zahl eingeben", zero=True, allow_none=False,
                 via_float=False, empty=Field, empty_lenient=Field):
        super().__init__(default, msg)
        self.lo, self.hi, self.zero, self.allow_none, self.via_float = lo, hi, zero, allow_none, via_float
        self.empty = default if empty is Field else empty
        self.empty_lenient = self.empty if empty_lenient is Field else empty_lenient

    def clean(self, value, strict):
        if value is None and self.allow_none:
            return None
        if value in (None, ""):
            return self.empty if strict else self.empty_lenient
        if not self.zero and value == 0:
            return self.default
        try:
            n = int(float(value)) if self.via_float else int(value)
        except (TypeError, ValueError):
            return self.fail(strict)
        return max(self.lo, min(self.hi, n))


class Minutes(Int):
    """Minuten: in der Verwaltung ganze Zahlen, von Hand in settings.json auch Bruchteile (z. B. 0.5)."""
    def clean(self, value, strict):
        if strict:
            return super().clean(value, strict)
        try:                                        # ohne Obergrenze, wie bisher im Treiber
            return max(0.02, float(value)) if value not in (None, "", 0) else self.default
        except (TypeError, ValueError):
            return self.default


class Float(Field):
    def clean(self, value, strict):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return self.fail(strict)


class Str(Field):
    def __init__(self, default="", maxlen=None, strip=True, msg=None, pattern=None, empty_default=False):
        super().__init__(default, msg)
        self.maxlen, self.strip, self.pattern, self.empty_default = maxlen, strip, pattern, empty_default

    def clean(self, value, strict):
        s = "" if value is None else str(value)
        if self.strip:
            s = s.strip()
        if not s and self.empty_default:
            s = self.default
        if self.pattern and not re.fullmatch(self.pattern, s):
            return self.fail(strict)
        return s[:self.maxlen] if self.maxlen else s


class Choice(Field):
    def __init__(self, default, options):
        super().__init__(default)
        self.options = options

    def clean(self, value, strict):
        return value if value in self.options() else self.default


class Color(Field):
    def clean(self, value, strict):
        if isinstance(value, list) and len(value) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in value):
            return value
        return self.fail(strict)


class ColorOrNone(Field):
    """Farbe oder None (= Standardfarbe des Zifferblatts, z. B. die Farbe der Ebene)."""
    def clean(self, value, strict):
        if value is None:
            return None
        if isinstance(value, list) and len(value) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in value):
            return value
        return self.fail(strict)


class FaceList(Field):
    """Liste von Zifferblättern (für das Displaymenü); leer = alle."""
    def clean(self, value, strict):
        return [f for f in dict.fromkeys(value if isinstance(value, list) else []) if f in CLOCK_FACES]


class Section(Field):
    """Unterobjekt aus Feldern; check(result, strict) prüft Regeln über mehrere Felder."""
    def __init__(self, fields, check=None):
        super().__init__({k: f.default for k, f in fields.items()})
        self.fields, self.check = fields, check

    def clean(self, value, strict):
        value = value if isinstance(value, dict) else {}
        # Treiber: unbekannte Schlüssel (z. B. von Hand ergänzt) bleiben erhalten
        out = {} if strict else {k: v for k, v in value.items() if k not in self.fields}
        for k, f in self.fields.items():
            if k in value:
                out[k] = f.clean(value[k], strict)
            else:                                   # fehlt: Standardwert
                out[k] = json.loads(json.dumps(f.default))
        if self.check:
            self.check(out, strict)
        return out


class Items(Field):
    """Liste von Einträgen; Einträge ohne Pflichtfeld werden übersprungen."""
    def __init__(self, default, item, required=None, limit=None):
        super().__init__(default)
        self.item, self.required, self.limit = item, required, limit

    def clean(self, value, strict):
        out = []
        for v in value if isinstance(value, list) else []:
            if not isinstance(v, dict):
                continue
            if self.required and not str(v.get(self.required) or "").strip():
                continue
            out.append(self.item.clean(v, strict))
        return out[:self.limit] if self.limit else out


class IntList(Field):
    def __init__(self, default, lo=None, hi=None, msg=None, lenient_items=False):
        super().__init__(default, msg)
        self.lo, self.hi, self.lenient_items = lo, hi, lenient_items

    """Zahlenliste. Verwaltung: sortiert, ungültige Einträge → Fehlermeldung
    (bzw. übersprungen bei lenient_items). Treiber: Reihenfolge bleibt, Ungültiges wird übersprungen."""
    def clean(self, value, strict):
        out = []
        for v in value if isinstance(value, list) else []:
            try:
                n = int(v)
            except (TypeError, ValueError):
                if self.lenient_items or not strict:
                    continue
                return self.fail(strict)
            if (self.lo is None or n >= self.lo) and (self.hi is None or n <= self.hi) and n not in out:
                out.append(n)
        return sorted(out) if strict else out


class Optional(Field):
    """Feld, das nur gespeichert wird, wenn es gültig ist (z. B. Kalenderfarbe)."""
    def __init__(self, field):
        super().__init__(None)
        self.field = field


# --- Regeln über mehrere Felder --------------------------------------------- #
TIME_RE = r"([01]\d|2[0-3]):[0-5]\d"


def _check_backup(b, strict):
    if not (strict and b["enabled"]):
        return
    if b["target"] == "folder" and not b["folder"]:
        raise Invalid("Für die automatische Sicherung bitte einen Ordner wählen")
    if b["target"] != "folder" and not b["url"]:
        raise Invalid("Für die automatische Sicherung bitte die Adresse des Ziels angeben")
    if b["target"] == "nextcloud" and not b["user"]:
        raise Invalid("Für die Sicherung in die Nextcloud bitte den Benutzernamen angeben")


class Entry(Section):
    """Listeneintrag mit optionalen Feldern (fehlen im Ergebnis, wenn ungültig)."""
    def clean(self, value, strict):
        out = {}
        for k, f in self.fields.items():
            if isinstance(f, Optional):
                if k in value and f.field.clean(value[k], False) is not None:
                    out[k] = value[k]               # nur gültige Werte übernehmen
                continue
            out[k] = f.clean(value.get(k, f.default), strict)
        return out


def _page_ids():
    return PAGE_IDS


def _clock_section():
    """settings.json → "clock": {"menu": [...], "<zifferblatt>": {<optionen>}} aus CLOCK_OPTIONS."""
    faces = {}
    for face, opts in CLOCK_OPTIONS.items():
        fields = {}
        for o in opts:
            if o["type"] == "bool":
                fields[o["key"]] = Bool(o["default"])
            elif o["type"] == "color":
                fields[o["key"]] = ColorOrNone(o["default"], f"Ungültige Farbe: {o['label']}")
            elif o["type"] == "choice":
                fields[o["key"]] = Choice(o["default"], lambda o=o: [c[0] for c in o["choices"]])
            elif o["type"] == "cities":
                fields[o["key"]] = Items(o["default"], Entry({"name": Str(maxlen=24), "tz": Str()}), required="tz", limit=6)
        faces[face] = Section(fields)
    return Section(dict(menu=FaceList([]), **faces))


# --- Das Schema ------------------------------------------------------------- #
SCHEMA = {
    "colors": Section({layer: Color(c, f"Ungültige Farbe für {layer}")
                       for layer, c in (("M1", [0, 110, 255]), ("M2", [0, 255, 90]), ("M3", [255, 70, 0]))}),
    "brightness": Int(None, 0, 100, allow_none=True),     # None = Helligkeit nicht verändern
    "keep_backlight": Bool(False),
    "start_page": Int(0, -10 ** 6, 10 ** 6),             # Index in PAGE_IDS (modulo Anzahl, −1 = letzte)
    "radio_player": Str("mpv --no-video --really-quiet --load-scripts=no {url}", strip=False, empty_default=True),
    "stations": Items([{"name": "Rockantenne", "url": "https://stream.rockantenne.de/rockantenne/stream/aacp", "logo": ""}],
                      Entry({"name": Str(), "url": Str(), "logo": Str()}), required="url"),
    "slideshow": Section({
        "url": Str(),                     # Adresse der Piwigo-Galerie
        "user": Str(),                    # leer = nur öffentliche Alben
        "password": Str(strip=False),
        "albums": IntList([], msg="Ungültige Albenauswahl"),
        "recursive": Bool(True),          # Unteralben einbeziehen
        "interval": Int(10, 3, 3600, "Die Wechselzeit muss eine Zahl sein", zero=False),
        "shuffle": Bool(True),
        "fit": Choice("contain", lambda: ("contain", "cover")),   # ganzes Bild / Display füllen
        "caption": Bool(True),            # Bildtitel einblenden
        "source": Choice("piwigo", lambda: ("piwigo", "folder")),
        "folder": Str(),                  # Bilderordner für source = folder
        "favorites_only": Bool(False),    # nur Lieblingsbilder zeigen
    }),
    "pages": Field(list(DEFAULT_PAGE_ORDER)),   # alle Seiten, die in irgendeiner Ebene sichtbar sind
    "layer_pages": Field({}),                   # je Ebene eigene Seitenliste (siehe normalize_pages)
    "snippets": Items([], Entry({"name": Str(maxlen=40), "group": Str(maxlen=30), "text": Str(strip=False, maxlen=5000)}),
                      required="text", limit=200),
    "timer_sound": Bool(True, only_false=True),                  # Signalton, wenn ein Timer abläuft
    "news": Section({
        "feeds": Items([{"name": "tagesschau", "url": "https://www.tagesschau.de/index~rss2.xml"}],
                       Entry({"name": Str(maxlen=30), "url": Str()}), required="url", limit=12),
        "count": Int(30, 5, 100, zero=False),
    }),
    "warnings": Section({"popup": Bool(True, only_false=True)}),   # Unwetterwarnungen (DWD über Bright Sky)
    "network": Section({
        "hosts": Items([{"name": "Router", "host": "gateway"}, {"name": "Internet", "host": "1.1.1.1"}],
                       Entry({"name": Str(maxlen=30), "host": Str()}), required="host", limit=12),
    }),
    "updates": Section({"flatpak": Bool(True, only_false=True)}),
    "backup": Section({"enabled": Bool(False),
                       "target": Choice("folder", lambda: ("folder", "nextcloud", "smb", "webdav")),
                       "folder": Str(),                       # target folder
                       "url": Str(),                          # nextcloud: Server · smb: \\nas\freigabe\ordner · webdav: Ordner
                       "user": Str(), "password": Str(strip=False),
                       "remote_dir": Str("G19s-Sicherung", empty_default=True),   # Ordner in der Nextcloud
                       "days": Int(7, 1, 90, zero=False), "keep": Int(8, 1, 100, zero=False)}, _check_backup),
    "alarm_clock": Section({"enabled": Bool(False), "time": Str("07:00", pattern=TIME_RE, msg="Ungültige Weckzeit",
                                                                  empty_default=True),
                            "days": IntList([0, 1, 2, 3, 4], 0, 6, lenient_items=True), "station": Str(strip=False)}),
    "weather": Section({"name": Str(maxlen=60, strip=False),
                        "lat": Float(None, "Ungültige Koordinaten für das Wetter"),
                        "lon": Float(None, "Ungültige Koordinaten für das Wetter")}),
    "calendar": Section({
        "sources": Items([], Entry({"name": Str("Kalender", maxlen=40, empty_default=True), "url": Str(), "user": Str(),
                                    "password": Str(strip=False), "color": Optional(Color(None))}), required="url"),
        "days": Int(14, 1, 60, zero=False),
        "remind": Int(10, 0, 240, empty_lenient=0),   # Minuten vor Terminbeginn (0 = aus; im Treiber leer = aus)
    }),
    "notifications": Section({"enabled": Bool(True), "seconds": Int(6, 2, 30, zero=False), "ignore": Str(maxlen=300, strip=False)}),
    "night": Section({"enabled": Bool(False),
                      "start": Str("22:30", pattern=TIME_RE, msg="Bitte die Uhrzeiten des Nachtmodus im Format HH:MM angeben"),
                      "end": Str("07:00", pattern=TIME_RE, msg="Bitte die Uhrzeiten des Nachtmodus im Format HH:MM angeben"),
                      "mode": Choice("dim", lambda: ("dim", "off")),
                      "brightness": Int(10, 0, 100, empty=0), "backlight_off": Bool(True)}),
    "screensaver": Section({"enabled": Bool(False), "minutes": Minutes(5, 1, 240, zero=False, via_float=True),
                            "page": Choice("slides", _page_ids)}),
    "volume_step": Int(5, 1, 25, zero=False),
    "pages_rev": Int(PAGES_REV, PAGES_REV, PAGES_REV),  # Stand der Seitenliste (für Umstellungen)
    "clock": _clock_section(),                  # Zifferblätter der Uhr: Auswahl fürs Displaymenü, Optionen
}

# Zusätzliche Prüfungen, die nur beim Speichern aus der Verwaltung gelten
STRICT_RULES = []


def _strict_rule(fn):
    STRICT_RULES.append(fn)
    return fn


@_strict_rule
def _check_feeds(s):
    for f in s["news"]["feeds"]:
        if not re.match(r"^https?://", f["url"], re.I):
            raise Invalid(f"Die Adresse „{f['url']}“ muss mit http:// oder https:// beginnen")


@_strict_rule
def _check_hosts(s):
    for h in s["network"]["hosts"]:
        if not re.fullmatch(r"[A-Za-z0-9._:\-\[\]]+", h["host"]):
            raise Invalid(f"Ungültiger Gerätename: {h['host']}")


@_strict_rule
def _check_world_cities(s):
    import zoneinfo
    for c in s["clock"]["world"]["cities"]:
        try:
            zoneinfo.ZoneInfo(c["tz"])
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            raise Invalid(f"Unbekannte Zeitzone für die Weltzeituhr: {c['tz']}")


DEFAULT_SETTINGS = {k: json.loads(json.dumps(f.default)) for k, f in SCHEMA.items()}


def _clean(data, strict):
    out = {}
    for key, field in SCHEMA.items():
        if key in data:
            out[key] = field.clean(data[key], strict)
        elif isinstance(field, Section):
            out[key] = field.clean({}, strict)
        else:
            out[key] = json.loads(json.dumps(field.default))
    out["start_page"] = out["start_page"] % len(PAGE_IDS)
    out["pages"], out["layer_pages"] = data.get("pages", out["pages"]), data.get("layer_pages", {})
    normalize_pages(out)
    return out


def clean_settings(data):
    """Streng prüfen (Verwaltung). Liefert vollständige Einstellungen oder wirft ValueError."""
    if not isinstance(data, dict):
        raise Invalid("Einstellungen müssen ein Objekt sein")
    s = _clean(data, strict=True)
    for rule in STRICT_RULES:
        rule(s)
    return s


def load_settings(path=SETTINGS_FILE):
    """Liest settings.json tolerant (Treiber): fehlende oder ungültige Werte → Standardwerte.
    Unterobjekte werden ergänzt, nicht ersetzt; unbekannte Schlüssel bleiben erhalten."""
    try:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
    except FileNotFoundError:
        user = {}
    if not isinstance(user, dict):
        user = {}
    merged = dict(user)
    for key, field in SCHEMA.items():
        if isinstance(field, Section) and isinstance(user.get(key), dict):
            merged[key] = dict(json.loads(json.dumps(field.default)), **user[key])   # Kopie, nie teilen
    data = _clean(merged, strict=False)
    for key, value in user.items():
        if key not in SCHEMA:
            data[key] = value
    return data


def normalize_pages(data):
    """Seitenlisten je Ebene prüfen; "pages" = alle Seiten, die in einer Ebene vorkommen."""
    def clean(lst):
        return list(dict.fromkeys(p for p in (lst if isinstance(lst, list) else []) if p in PAGE_IDS))
    base = clean(data.get("pages")) or ["clock"]
    lp = data.get("layer_pages") if isinstance(data.get("layer_pages"), dict) else {}
    layer_pages = {layer: clean(lp.get(layer)) or list(base) for layer in ("M1", "M2", "M3")}
    data["layer_pages"] = layer_pages
    data["pages"] = list(dict.fromkeys(p for layer in ("M1", "M2", "M3") for p in layer_pages[layer]))
    return data


def save_json(path, data, compact_steps=False, private=False):
    """Schreibt JSON atomar (erst temporäre Datei, dann umbenennen).
    private=True: nur für den Benutzer lesbar (z. B. wegen Piwigo-Passwort)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if compact_steps:
        # innerste Listen (einzelne Schritte, Farben) auf eine Zeile zusammenziehen
        text = re.sub(r"\[\s+([^\[\]{}]*?)\s+\]",
                      lambda m: "[" + re.sub(r",\s*\n\s*", ", ", m.group(1)) + "]", text)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    if private:
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)
