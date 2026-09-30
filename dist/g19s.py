#!/usr/bin/env python3
"""
g19s.py – Userspace-Treiber für die Logitech G19 / G19s unter Linux

  * Display (320×240): Uhr, Musik/Radio, Wetter, Termine, System, Hardware, Makros,
    Diashow, Nachrichten, Unwetter, Netzwerk, Updates – Auswahl je Ebene und Profil.
  * G1–G12: Makros, Text, Tastenkombinationen, Webseiten, Programme, Radio,
    Musiksteuerung, Lautstärke, Mikrofon, Timer, Textbausteine, Einschlaftimer –
    sonst F13–F24 (M2: Strg+, M3: Alt+) für KDE-Kurzbefehle.
  * M1/M2/M3: Ebenen, SETTINGS: bis zu 10 Profile, MR: Makro aufnehmen.
  * Nachtmodus, Bildschirmschoner, Benachrichtigungen, Terminerinnerung, Radiowecker,
    automatische Sicherung.

Dateien: ~/.config/g19s/macros.json (Belegung), settings.json (Einstellungen),
state.json (Zustand), songs.json, favorites.json. Bearbeiten am einfachsten mit
der Verwaltung g19s-gui.py; Änderungen übernimmt der Treiber sofort.

Aufruf:
  python3 g19s.py              normaler Betrieb
  python3 g19s.py --debug      zeigt die Rohdaten jeder Taste (zum Prüfen der Belegung)
  python3 g19s.py --preview x  rendert die Displayseiten als PNG (ohne Tastatur)

Benötigt: python3-usb python3-evdev python3-pil python3-numpy playerctl mpv

Diese Datei wird aus den Modulen in src/treiber/ zusammengesetzt (build.py);
jedes Modul beginnt unten mit einer Überschrift „Modul …“.
"""

import argparse
import json
import os
import re
import shutil
import signal
import sys
import subprocess
import threading
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

G19S_COMPONENT = "driver"     # Kennung für den Update-Knopf der Verwaltung
VERSION = "2026.09.30-4"

# Weitere Importe der Module
import http.client
import xml.etree.ElementTree as ET
import base64
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import math
import random
import datetime
import zoneinfo
from PIL import ImageFilter
import colorsys
from collections import deque


# ═══════════════════════════════════════════════════════════════════════════
# Modul konstanten
#   Feste Werte: USB-Kennungen und Endpunkte, Tastenbits, Displaygröße, Farben, Dateipfade, Seiten-IDs.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Hardware-Konstanten
# --------------------------------------------------------------------------- #
VENDOR_ID = 0x046D
PRODUCT_ID = 0xC229          # "G19 Gaming Keyboard Macro Interface"
KEYBOARD_PRODUCT_ID = 0xC228  # normale Tastatur (für die Makroaufnahme)

EP_LCD_OUT = 0x02            # Bulk OUT, Interface 0: Displaybild
EP_LKEYS = 0x81              # Interrupt IN, Interface 0: Displaytasten
EP_GKEYS = 0x83              # Interrupt IN, Interface 1: G-/M-Tasten

WIDTH, HEIGHT = 320, 240
FOOTER_H = 26               # Höhe der Fußzeile (Profil, Seitenpunkte) unten auf jeder Seite
FKEY_BASE = 13              # G1 sendet F13, G12 sendet F24
SELECTION_TIMEOUT = 30      # Sekunden, nach denen eine Markierung (Termin, Meldung) verschwindet

# G-/M-Tasten (Report-ID 0x02): Wert = d[1] | d[2] << 8
#   d[1]: G1–G8, d[2]: G9–G12 (Bits 0–3), M1/M2/M3/MR (Bits 4–7)
GKEY_BITS = {f"G{i + 1}": 1 << i for i in range(12)}
MKEY_BITS = {"M1": 0x1000, "M2": 0x2000, "M3": 0x4000, "MR": 0x8000}

# Displaytasten: erstes Byte
LKEY_BITS = {
    "SETTINGS": 0x01, "BACK": 0x02, "MENU": 0x04, "OK": 0x08,
    "RIGHT": 0x10, "LEFT": 0x20, "DOWN": 0x40, "UP": 0x80,
}

# LED-Bits der M-Tasten
M_LED = {"M1": 0x80, "M2": 0x40, "M3": 0x20, "MR": 0x10}

# Farbe der Tastaturbeleuchtung je Profil (R, G, B)
PROFILE_COLOR = {"M1": (0, 110, 255), "M2": (0, 255, 90), "M3": (255, 70, 0)}
REC_COLOR = (255, 40, 40)

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "g19s")
MACRO_FILE = os.path.join(CONFIG_DIR, "macros.json")

SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

MAX_WAIT_MS = 5000   # längste Pause beim Abspielen
MIN_WAIT_MS = 5      # kürzeste Pause zwischen zwei Ereignissen
TAP_MS = 20          # Haltezeit bei Schritten vom Typ "tap"
TEXT_DELAY_MS = 12   # Pause zwischen zwei Zeichen bei "text"

PAGE_IDS = ["clock", "music", "macros", "slides", "weather", "calendar", "hardware",
            "news", "warnings", "network", "updates"]
PAGE_NAMES = ["Uhr", "Musik", "Makros", "Bilder", "Wetter", "Termine", "Hardware",
              "Nachrichten", "Unwetter", "Netzwerk", "Updates"]
# Zifferblätter der Seite „Uhr“ (Auswahl am Display mit MENU, gespeichert je Profil und Ebene).
# Reihenfolge = Reihenfolge im Displaymenü und in der Verwaltung.
CLOCK_FACES = {
    "digital": "Digitaluhr", "chrono": "Chronometer", "steampunk": "Steampunk-Uhr", "station": "Bahnhofsuhr",
    "binary": "Binäruhr",
    "pendulum": "Pendeluhr", "cuckoo": "Kuckucksuhr", "pocket": "Taschenuhr", "hourglass": "Sanduhr",
    "candle": "Kerzenuhr",
    "astro": "Astro-Uhr", "sundial": "Sonnenuhr", "planets": "Planetenuhr", "world": "Weltzeituhr",
    "radar": "Radaruhr",
    "flip": "Klappzahlenuhr", "nixie": "Nixie-Röhrenuhr", "seg7": "LED-Radiowecker", "matrix": "LED-Matrix",
    "counter": "Zählwerk",
    "words": "Wortuhr", "terminal": "Terminal", "progress": "Tagesfortschritt", "rings": "Ringuhr",
    "gauge": "Tacho-Uhr",
}

# Städte der Weltzeituhr (Name, Zeitzone)
WORLD_CITIES = [
    ("Berlin", "Europe/Berlin"), ("London", "Europe/London"), ("Lissabon", "Europe/Lisbon"), ("Paris", "Europe/Paris"),
    ("Madrid", "Europe/Madrid"), ("Rom", "Europe/Rome"), ("Athen", "Europe/Athens"), ("Istanbul", "Europe/Istanbul"),
    ("Moskau", "Europe/Moscow"), ("Reykjavík", "Atlantic/Reykjavik"), ("Kairo", "Africa/Cairo"),
    ("Nairobi", "Africa/Nairobi"), ("Lagos", "Africa/Lagos"), ("Kapstadt", "Africa/Johannesburg"),
    ("Dubai", "Asia/Dubai"), ("Delhi", "Asia/Kolkata"), ("Bangkok", "Asia/Bangkok"), ("Singapur", "Asia/Singapore"),
    ("Peking", "Asia/Shanghai"), ("Hongkong", "Asia/Hong_Kong"), ("Seoul", "Asia/Seoul"), ("Tokio", "Asia/Tokyo"),
    ("Sydney", "Australia/Sydney"), ("Perth", "Australia/Perth"), ("Auckland", "Pacific/Auckland"),
    ("Honolulu", "Pacific/Honolulu"), ("Anchorage", "America/Anchorage"), ("Los Angeles", "America/Los_Angeles"),
    ("Denver", "America/Denver"), ("Chicago", "America/Chicago"), ("New York", "America/New_York"),
    ("Toronto", "America/Toronto"), ("Mexiko-Stadt", "America/Mexico_City"), ("Bogotá", "America/Bogota"),
    ("São Paulo", "America/Sao_Paulo"), ("Buenos Aires", "America/Argentina/Buenos_Aires"), ("UTC", "UTC"),
]

# Einstellungen je Zifferblatt (Verwaltung → Beleuchtung & Display → Uhr). Aus dieser Liste entstehen
# das Einstellungsschema (settings.json → "clock") und die Formularfelder der Verwaltung.
#   bool: Schalter · color: Farbe, None = Standard (none_label) · choice: Auswahl · cities: Städteliste
_LAYER = "Farbe der Ebene"
CLOCK_OPTIONS = {
    "digital": [
        {"key": "seconds", "label": "Sekunden anzeigen", "type": "bool", "default": True},
        {"key": "date", "label": "Wochentag und Datum anzeigen", "type": "bool", "default": True},
        {"key": "color", "label": "Farbe der Uhrzeit", "type": "color", "default": None, "none_label": "Weiß (Standard)"},
    ],
    "binary": [
        {"key": "color_h", "label": "Farbe Stunden", "type": "color", "default": None, "none_label": _LAYER},
        {"key": "color_m", "label": "Farbe Minuten", "type": "color", "default": None, "none_label": _LAYER},
        {"key": "color_s", "label": "Farbe Sekunden", "type": "color", "default": None, "none_label": _LAYER},
        {"key": "color_off", "label": "Farbe ausgeschalteter Punkte", "type": "color", "default": None,
         "none_label": "Dunkelgrau (Standard)"},
        {"key": "mode", "label": "Darstellung", "type": "choice", "default": "bcd",
         "choices": [["bcd", "Spalten je Ziffer (8-4-2-1)"], ["binary", "Binärzahl je Zeile (Stunde, Minute, Sekunde)"]]},
        {"key": "digits", "label": "Uhrzeit als Ziffern darunter", "type": "bool", "default": True},
    ],
    "chrono": [
        {"key": "dial", "label": "Zifferblatt", "type": "choice", "default": "black",
         "choices": [["black", "Schwarz"], ["blue", "Blau"], ["green", "Grün"], ["silver", "Silber"]]},
        {"key": "hand", "label": "Farbe des Sekundenzeigers", "type": "color", "default": None, "none_label": _LAYER},
        {"key": "side", "label": "Neben der Uhr", "type": "choice", "default": "both",
         "choices": [["both", "Datum und Kalenderwoche"], ["date", "nur Datum"], ["none", "nichts"]]},
    ],
    "station": [
        {"key": "seconds", "label": "Sekundenzeiger", "type": "bool", "default": True},
        {"key": "smooth", "label": "Minutenzeiger gleitend (statt springend)", "type": "bool", "default": False},
        {"key": "side", "label": "Datum und Kalenderwoche neben der Uhr", "type": "bool", "default": True},
    ],
    "steampunk": [
        {"key": "gears", "label": "Zahnräder drehen sich", "type": "bool", "default": True},
    ],
    "pendulum": [
        {"key": "swing", "label": "Pendel schwingt flüssig (etwas mehr Rechenzeit)", "type": "bool", "default": True},
    ],
    "world": [
        {"key": "cities", "label": "Städte", "type": "cities",
         "default": [{"name": n, "tz": z} for n, z in (("Berlin", "Europe/Berlin"), ("London", "Europe/London"),
                                                       ("New York", "America/New_York"), ("Los Angeles", "America/Los_Angeles"),
                                                       ("Tokio", "Asia/Tokyo"), ("Sydney", "Australia/Sydney"))]},
    ],
    "seg7": [
        {"key": "color", "label": "Farbe der Ziffern", "type": "color", "default": None, "none_label": "Rot (Standard)"},
    ],
    "matrix": [
        {"key": "color", "label": "Farbe der Leuchtpunkte", "type": "color", "default": None, "none_label": _LAYER},
    ],
    "terminal": [
        {"key": "color", "label": "Farbe", "type": "choice", "default": "green",
         "choices": [["green", "Grün"], ["amber", "Bernstein"], ["white", "Weiß"], ["blue", "Blau"]]},
    ],
    "words": [
        {"key": "color", "label": "Farbe der leuchtenden Wörter", "type": "color", "default": None, "none_label": _LAYER},
    ],
}
OLD_CLOCK_PAGES = {"clock_chrono": "chrono", "clock_steampunk": "steampunk",      # Version 2026.09.28-8/-9
                   "clock_station": "station", "clock_binary": "binary"}
DEFAULT_PAGE_ORDER = ["clock", "music", "weather", "calendar", "hardware", "macros", "slides"]
# Seitenliste bis Version 2026.09.29-2 (mit „System“, heute Teil von „Hardware“) – für die Umstellung
# alter Startseiten-Nummern in settings.json; PAGES_REV markiert umgestellte Dateien.
OLD_PAGE_IDS_REV1 = ["clock", "music", "system", "macros", "slides", "weather", "calendar", "hardware",
                     "news", "warnings", "network", "updates"]
PAGES_REV = 2

CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "g19s")
VOLUME_ACTIONS = {"up": "Lauter", "down": "Leiser", "mute": "Stumm"}
MEDIA_ACTIONS = {"play-pause": "Play/Pause", "next": "Nächster Titel",
                 "previous": "Vorheriger Titel", "stop": "Stopp", "remember": "Song merken"}
SONGS_FILE = os.path.join(CONFIG_DIR, "songs.json")          # gemerkte Radiotitel
FAVORITES_FILE = os.path.join(CONFIG_DIR, "favorites.json")  # Lieblingsbilder der Diashow


MAX_PROFILES = 10
LAYERS = ("M1", "M2", "M3")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")
WEEKDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


# ═══════════════════════════════════════════════════════════════════════════
# Modul einstellungen
#   Einstellungen (settings.json): ein Schema für Treiber und Verwaltung.
#
#   Jedes Feld steht genau einmal in SCHEMA – mit Standardwert, erlaubten Werten
#   und der Fehlermeldung für die Verwaltung. Daraus entstehen:
#
#     * DEFAULT_SETTINGS        die Standardwerte
#     * load_settings()         Treiber: liest settings.json tolerant
#                               (Ungültiges → Standardwert, unbekannte Schlüssel bleiben)
#     * clean_settings(data)    Verwaltung: prüft streng (Ungültiges → ValueError mit
#                               verständlicher Meldung), unbekannte Schlüssel entfallen
# ═══════════════════════════════════════════════════════════════════════════

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
            item = self.item.clean(v, strict)
            if self.required and not str(item.get(self.required) or "").strip():
                continue                            # Pflichtfeld nach der Prüfung ungültig (tolerant)
            out.append(item)
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
URL_RE = r"(?i)https?://\S+"                  # Senderadressen: keine Leerzeichen/Zeilenumbrüche (m3u!)


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
                      Entry({"name": Str(), "url": Str(pattern=URL_RE, msg="Senderadressen müssen mit http:// oder "
                                                                             "https:// beginnen (ohne Leerzeichen)"),
                             "logo": Str()}), required="url"),
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
        if not re.fullmatch(r"[A-Za-z0-9\[][A-Za-z0-9._:\-\[\]]*", h["host"]):    # nie mit „-“ beginnend
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
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)   # neu angelegt: nur für den Benutzer
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


# ═══════════════════════════════════════════════════════════════════════════
# Modul hilfen
#   Kleine Hilfsfunktionen ohne eigenes Thema.
# ═══════════════════════════════════════════════════════════════════════════

def domain_of(url):
    return re.sub(r"^[a-z]+://(www\.)?", "", str(url), flags=re.I).split("/")[0]


def in_time_window(now_hm, start, end):
    """Liegt die Uhrzeit (HH:MM) im Zeitraum? Funktioniert auch über Mitternacht."""
    def mins(s):
        h, m = str(s).split(":")
        return int(h) * 60 + int(m)
    try:
        n, a, b = mins(now_hm), mins(start), mins(end)
    except (ValueError, AttributeError):
        return False
    if a == b:
        return False
    return a <= n < b if a < b else (n >= a or n < b)


# ═══════════════════════════════════════════════════════════════════════════
# Modul tastatur
#   Deutsches Tastaturlayout (QWERTZ): Text und Tastenkombinationen in Makroschritte übersetzen, Tastennamen.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Deutsches Tastaturlayout (QWERTZ): Zeichen -> Tastenfolge
# evdev benennt Tasten nach ihrer Position auf der US-Tastatur.
# --------------------------------------------------------------------------- #
_S, _A = "KEY_LEFTSHIFT", "KEY_RIGHTALT"   # Umschalt, AltGr
DE_CHARS = {" ": ("KEY_SPACE",), "\n": ("KEY_ENTER",), "\t": ("KEY_TAB",)}
for _c in "abcdefghijklmnopqrstuvwx":
    DE_CHARS[_c] = (f"KEY_{_c.upper()}",)
    DE_CHARS[_c.upper()] = (_S, f"KEY_{_c.upper()}")
DE_CHARS.update({"y": ("KEY_Z",), "Y": (_S, "KEY_Z"), "z": ("KEY_Y",), "Z": (_S, "KEY_Y")})
for _c, _shifted in zip("1234567890", '!"§$%&/()='):
    DE_CHARS[_c] = (f"KEY_{_c}",)
    DE_CHARS[_shifted] = (_S, f"KEY_{_c}")
DE_CHARS.update({
    "ß": ("KEY_MINUS",), "?": (_S, "KEY_MINUS"), "\\": (_A, "KEY_MINUS"),
    "ü": ("KEY_LEFTBRACE",), "Ü": (_S, "KEY_LEFTBRACE"),
    "+": ("KEY_RIGHTBRACE",), "*": (_S, "KEY_RIGHTBRACE"),
    "ö": ("KEY_SEMICOLON",), "Ö": (_S, "KEY_SEMICOLON"),
    "ä": ("KEY_APOSTROPHE",), "Ä": (_S, "KEY_APOSTROPHE"),
    "#": ("KEY_BACKSLASH",), "'": (_S, "KEY_BACKSLASH"),
    "<": ("KEY_102ND",), ">": (_S, "KEY_102ND"), "|": (_A, "KEY_102ND"),
    ",": ("KEY_COMMA",), ";": (_S, "KEY_COMMA"),
    ".": ("KEY_DOT",), ":": (_S, "KEY_DOT"),
    "-": ("KEY_SLASH",), "_": (_S, "KEY_SLASH"),
    "°": (_S, "KEY_GRAVE"),
    "@": (_A, "KEY_Q"), "€": (_A, "KEY_E"), "µ": (_A, "KEY_M"),
    "²": (_A, "KEY_2"), "³": (_A, "KEY_3"),
    "{": (_A, "KEY_7"), "[": (_A, "KEY_8"), "]": (_A, "KEY_9"), "}": (_A, "KEY_0"),
})
# Tottasten: Taste drücken, danach Leertaste, damit das Zeichen allein erscheint
DE_DEAD = {"^": ("KEY_GRAVE",), "´": ("KEY_EQUAL",), "`": (_S, "KEY_EQUAL"),
           "~": (_A, "KEY_RIGHTBRACE")}


# Anzeigenamen der Tasten auf einer deutschen Tastatur
KEY_LABELS = {
    "KEY_LEFTCTRL": "Strg", "KEY_RIGHTCTRL": "Strg rechts", "KEY_LEFTSHIFT": "Umschalt",
    "KEY_RIGHTSHIFT": "Umschalt rechts", "KEY_LEFTALT": "Alt", "KEY_RIGHTALT": "AltGr",
    "KEY_LEFTMETA": "Meta", "KEY_RIGHTMETA": "Meta rechts", "KEY_COMPOSE": "Menü",
    "KEY_ENTER": "Enter", "KEY_KPENTER": "Enter (Ziffernblock)", "KEY_SPACE": "Leertaste",
    "KEY_TAB": "Tab", "KEY_BACKSPACE": "Rücktaste", "KEY_ESC": "Esc", "KEY_DELETE": "Entf",
    "KEY_INSERT": "Einfg", "KEY_HOME": "Pos1", "KEY_END": "Ende", "KEY_PAGEUP": "Bild ↑",
    "KEY_PAGEDOWN": "Bild ↓", "KEY_UP": "Pfeil ↑", "KEY_DOWN": "Pfeil ↓", "KEY_LEFT": "Pfeil ←",
    "KEY_RIGHT": "Pfeil →", "KEY_CAPSLOCK": "Feststelltaste", "KEY_NUMLOCK": "Num",
    "KEY_SCROLLLOCK": "Rollen", "KEY_SYSRQ": "Druck", "KEY_PRINT": "Druck", "KEY_PAUSE": "Pause",
    "KEY_Y": "Z", "KEY_Z": "Y", "KEY_SEMICOLON": "Ö", "KEY_APOSTROPHE": "Ä",
    "KEY_LEFTBRACE": "Ü", "KEY_RIGHTBRACE": "+", "KEY_MINUS": "ß", "KEY_EQUAL": "´",
    "KEY_BACKSLASH": "#", "KEY_GRAVE": "^", "KEY_102ND": "<", "KEY_COMMA": ",",
    "KEY_DOT": ".", "KEY_SLASH": "-",
    "KEY_MUTE": "Stumm", "KEY_VOLUMEUP": "Lauter", "KEY_VOLUMEDOWN": "Leiser",
    "KEY_PLAYPAUSE": "Play/Pause", "KEY_NEXTSONG": "Nächster Titel",
    "KEY_PREVIOUSSONG": "Vorheriger Titel", "KEY_STOPCD": "Stopp",
}
for _n in range(10):
    KEY_LABELS[f"KEY_KP{_n}"] = f"{_n} (Ziffernblock)"
KEY_LABELS.update({"KEY_KPPLUS": "+ (Ziffernblock)", "KEY_KPMINUS": "- (Ziffernblock)",
                   "KEY_KPASTERISK": "* (Ziffernblock)", "KEY_KPSLASH": "/ (Ziffernblock)",
                   "KEY_KPDOT": ", (Ziffernblock)"})


def key_label(name):
    name = str(name)
    if name in KEY_LABELS:
        return KEY_LABELS[name]
    short = name.replace("KEY_", "").replace("BTN_", "Maus ")
    return short if len(short) <= 3 else short.capitalize()


def text_to_steps(text):
    """Wandelt Text in Makroschritte um (deutsches Layout). Gibt (Schritte, unbekannte Zeichen) zurück."""
    steps, unknown = [], []
    for ch in text.replace("\r\n", "\n"):
        combo = DE_CHARS.get(ch) or DE_DEAD.get(ch)
        if not combo:
            if ch not in unknown:
                unknown.append(ch)
            continue
        steps += combo_to_steps(list(combo), first_wait=TEXT_DELAY_MS)
        if ch in DE_DEAD:
            steps.append([5, "KEY_SPACE", "tap"])
    return steps, unknown


def combo_to_steps(keys, first_wait=0):
    """Tastenkombination (z. B. ["KEY_LEFTCTRL", "KEY_C"]) als Schritte."""
    keys = [k for k in keys if k]
    if not keys:
        return []
    if len(keys) == 1:
        return [[first_wait, keys[0], "tap"]]
    steps = [[first_wait if i == 0 else 5, k, "down"] for i, k in enumerate(keys)]
    steps += [[TAP_MS if i == 0 else 5, k, "up"] for i, k in enumerate(reversed(keys))]
    return steps


def entry_steps(entry, log=print):
    """Liefert die abzuspielenden Schritte eines Eintrags (steps, text oder combo)."""
    if entry.get("text"):
        steps, unknown = text_to_steps(str(entry["text"]))
        if unknown:
            log(f"Zeichen ohne Tastenzuordnung übersprungen: {''.join(unknown)!r}")
        return steps
    if entry.get("combo"):
        return combo_to_steps(combo_keys(entry["combo"]))
    return entry.get("steps") or []


# --------------------------------------------------------------------------- #
# Makros: Speicherung, Aufnahme, Wiedergabe
# --------------------------------------------------------------------------- #
def key_name(code):
    from evdev import ecodes
    name = ecodes.KEY.get(code) or ecodes.BTN.get(code)
    if isinstance(name, (list, tuple)):
        name = name[0]
    return name or str(code)


def key_code(name):
    from evdev import ecodes
    if isinstance(name, int):
        return name
    name = str(name).strip()
    if name.isdigit():
        return int(name)
    if not name.startswith(("KEY_", "BTN_")):
        name = "KEY_" + name.upper()
    return ecodes.ecodes.get(name)


def compile_steps(macro, log=print):
    """Wandelt die Schritte eines Eintrags in (Pause_ms, Code, Wert)-Tupel um."""
    out = []
    for step in entry_steps(macro, log):
        try:
            wait, name, action = step
            wait = max(0, int(wait))
        except (TypeError, ValueError):
            log(f"Ungültiger Makroschritt übersprungen: {step!r}")
            continue
        code = key_code(name)
        if code is None:
            log(f"Unbekannte Taste im Makro übersprungen: {name!r}")
            continue
        action = str(action).lower()
        if action in ("down", "1"):
            out.append((wait, code, 1))
        elif action in ("up", "0"):
            out.append((wait, code, 0))
        elif action == "tap":
            out.append((wait, code, 1))
            out.append((TAP_MS, code, 0))
        else:
            log(f"Unbekannte Aktion {action!r} übersprungen (erlaubt: down, up, tap)")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Modul makros
#   Tastenbelegung (macros.json) mit Profilen und Ebenen, Zustand (state.json), Beschriftung der Einträge.
# ═══════════════════════════════════════════════════════════════════════════

# Arten von Tastenbelegungen in der Reihenfolge, in der sie erkannt werden. Gilt für die Ausführung
# (aktionen.py), die Beschriftung (entry_label) und die Verwaltung (bekommt die Liste über /api/state).
# Ein Eintrag hat normalerweise genau eine davon; „timer“ muss ein Objekt sein.
ENTRY_TYPES = ["timer", "snippets", "open", "run", "radio", "media", "mic", "sleep", "volume",
               "text", "combo", "steps"]


def entry_type(entry):
    """Art einer Tastenbelegung (siehe ENTRY_TYPES) oder None (Taste sendet F13–F24)."""
    if not isinstance(entry, dict):
        return None
    for t in ENTRY_TYPES:
        v = entry.get(t)
        if t == "timer" and not isinstance(v, dict):
            continue
        if v:
            return t
    return None


def combo_keys(combo):
    """Tastenkombination als Liste: ["KEY_LEFTCTRL", "KEY_C"] oder "KEY_LEFTCTRL+KEY_C"."""
    keys = combo if isinstance(combo, list) else str(combo or "").split("+")
    return [str(k).strip() for k in keys if str(k).strip()]


def entry_label(entry, settings=None):
    """Kurzbeschriftung einer Tastenbelegung für Display und Oberfläche.
    Die Verwaltung hat dieselben Regeln in seite/js/02_hilfen.js (entryLabel) – ein Test vergleicht beide."""
    if not isinstance(entry, dict):
        return ""
    if entry.get("name"):
        return str(entry["name"])
    t = entry_type(entry)
    if t == "open":
        return domain_of(entry["open"])
    if t == "radio":
        if entry["radio"] == "stop":
            return "Radio aus"
        for st in (settings or {}).get("stations", []):
            if st.get("url") == entry["radio"]:
                return st.get("name") or domain_of(entry["radio"])
        return domain_of(entry["radio"])
    if t == "media":
        return MEDIA_ACTIONS.get(entry["media"], "Musik")
    if t == "volume":
        return VOLUME_ACTIONS.get(entry["volume"], "Lautstärke")
    if t == "snippets":
        grp = str(entry["snippets"])
        return "Textbausteine" if grp == "*" else grp
    if t == "timer":
        return timer_label(entry["timer"])
    if t == "sleep":
        return f"Einschlafen {entry['sleep']} min"
    if t == "mic":
        return "Mikrofon"
    if t == "run":
        return (str(entry["run"]).split() or [""])[0]
    if t == "text":
        return "Text"
    if t == "combo":
        return "+".join(key_label(k) for k in combo_keys(entry["combo"]))
    if t == "steps":
        return "Makro"
    return ""


def valid_colors(colors):
    """Prüft {"M1": [r,g,b], …} und gibt eine bereinigte Kopie oder None zurück."""
    if not isinstance(colors, dict):
        return None
    out = {}
    for layer in LAYERS:
        c = colors.get(layer)
        if (isinstance(c, (list, tuple)) and len(c) == 3
                and all(isinstance(v, int) and 0 <= v <= 255 for v in c)):
            out[layer] = list(c)
    return out if len(out) == 3 else None


def normalize_macros(data):
    """Bringt macros.json ins Profilformat. Das alte Format (nur M1/M2/M3)
    wird zu „Profil 1“:
    {
      "profiles": [
        {"name": "Profil 1", "colors": {"M1": [r,g,b], …},
         "keys": {"M1": {"G5": {"name": …, "steps": [[0, "KEY_H", "tap"], …]}}, "M2": {…}}}
      ]
    }"""
    if isinstance(data, dict) and isinstance(data.get("profiles"), list):
        raw = data["profiles"]
    elif isinstance(data, dict):
        raw = [{"name": "Profil 1", "keys": {k: v for k, v in data.items() if k in LAYERS}}]
    else:
        raw = []
    profiles = []
    for p in raw[:MAX_PROFILES]:
        if not isinstance(p, dict):
            continue
        keys = p.get("keys") if isinstance(p.get("keys"), dict) else {}
        prof = {"name": str(p.get("name") or f"Profil {len(profiles) + 1}").strip()[:30],
                "keys": {l: keys[l] for l in LAYERS if isinstance(keys.get(l), dict) and keys[l]}}
        colors = valid_colors(p.get("colors"))
        if colors:
            prof["colors"] = colors
        pages = valid_profile_pages(p.get("pages"))
        if pages:
            prof["pages"] = pages
        faces = valid_clock_faces(p.get("clock"))
        if faces:
            prof["clock"] = faces
        profiles.append(prof)
    return {"profiles": profiles or [{"name": "Profil 1", "keys": {}}]}


def valid_profile_pages(pages):
    """Eigene Displayseiten eines Profils: {"M1": [...], "M2": [...], "M3": [...]} oder None."""
    if not isinstance(pages, dict):
        return None
    out = {}
    for layer in LAYERS:
        lst = pages.get(layer)
        lst = list(dict.fromkeys(x for x in (lst if isinstance(lst, list) else []) if x in PAGE_IDS))
        if lst:
            out[layer] = lst
    return out if len(out) == len(LAYERS) else None


def valid_clock_faces(faces):
    """Zifferblätter eines Profils je Ebene: {"M3": "station"} (Digitaluhr = kein Eintrag) oder None."""
    if not isinstance(faces, dict):
        return None
    out = {l: faces[l] for l in LAYERS if faces.get(l) in CLOCK_FACES and faces[l] != "digital"}
    return out or None


def migrate_clock_pages(settings_path=None, macros_path=None, log=print):
    """Version 2026.09.28-8/-9 hatte eigene Uhrenseiten (clock_chrono …). Daraus wird die Seite
    „Uhr“ mit dem passenden Zifferblatt (je Profil und Ebene in macros.json)."""
    settings_path, macros_path = settings_path or SETTINGS_FILE, macros_path or MACRO_FILE

    def read(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None

    def convert(lst, faces, layer):
        if not isinstance(lst, list):
            return lst
        out = []
        for p in lst:
            if p in OLD_CLOCK_PAGES:
                if layer:
                    faces.setdefault(layer, OLD_CLOCK_PAGES[p])
                p = "clock"
            if p not in out:
                out.append(p)
        return out

    def has_old(obj):
        text = json.dumps(obj)
        return any(f'"{p}"' in text for p in OLD_CLOCK_PAGES)

    settings, macros = read(settings_path), read(macros_path)
    global_faces = {}
    if settings and has_old([settings.get("pages"), settings.get("layer_pages"), settings.get("screensaver")]):
        if "pages" in settings:
            settings["pages"] = convert(settings["pages"], {}, None)
        lp = settings.get("layer_pages")
        if isinstance(lp, dict):
            settings["layer_pages"] = {k: convert(v, global_faces, k if k in LAYERS else None) for k, v in lp.items()}
        ss = settings.get("screensaver")
        if isinstance(ss, dict) and ss.get("page") in OLD_CLOCK_PAGES:
            ss["page"] = "clock"
        save_json(settings_path, settings, private=True)
        log("Uhrenseiten in settings.json auf „Uhr“ mit Zifferblatt umgestellt")
    profiles = macros.get("profiles") if macros else None
    if isinstance(profiles, list) and (global_faces or has_old([p.get("pages") for p in profiles if isinstance(p, dict)])):
        for p in profiles:
            if not isinstance(p, dict):
                continue
            own, faces = p.get("pages"), {}
            if isinstance(own, dict):
                p["pages"] = {k: convert(v, faces, k if k in LAYERS else None) for k, v in own.items()}
            use = faces if valid_profile_pages(p.get("pages")) else global_faces
            cur = p.get("clock") if isinstance(p.get("clock"), dict) else {}
            merged = valid_clock_faces(dict(use, **cur))
            if merged:
                p["clock"] = merged
        save_json(macros_path, macros, compact_steps=True)
        log("Uhrenseiten in macros.json auf „Uhr“ mit Zifferblatt umgestellt")


def migrate_system_page(settings_path=None, macros_path=None, log=print):
    """Bis Version 2026.09.29-2 gab es die Seite „System“ (jetzt Teil von „Hardware“) an Position 2.
    Seitenlisten: system → hardware; Startseite (Nummer) auf die neue Seitenliste umrechnen."""
    settings_path, macros_path = settings_path or SETTINGS_FILE, macros_path or MACRO_FILE

    def swap(lst):
        if not isinstance(lst, list):
            return lst
        return list(dict.fromkeys("hardware" if p == "system" else p for p in lst))

    try:
        with open(settings_path, encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = None
    if isinstance(s, dict) and s.get("pages_rev") != PAGES_REV:
        sp = s.get("start_page")
        if isinstance(sp, int) and not isinstance(sp, bool):
            old = OLD_PAGE_IDS_REV1[sp % len(OLD_PAGE_IDS_REV1)]
            s["start_page"] = PAGE_IDS.index("hardware" if old == "system" else old)
        if "pages" in s:
            s["pages"] = swap(s["pages"])
        if isinstance(s.get("layer_pages"), dict):
            s["layer_pages"] = {k: swap(v) for k, v in s["layer_pages"].items()}
        if isinstance(s.get("screensaver"), dict) and s["screensaver"].get("page") == "system":
            s["screensaver"]["page"] = "hardware"
        s["pages_rev"] = PAGES_REV
        save_json(settings_path, s, private=True)
        log("Seite „System“ ist jetzt Teil von „Hardware“ – settings.json umgestellt")
    try:
        with open(macros_path, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return
    profiles = m.get("profiles") if isinstance(m, dict) else None
    if isinstance(profiles, list) and any(isinstance(p, dict) and '"system"' in json.dumps(p.get("pages"))
                                          for p in profiles):
        for p in profiles:
            if isinstance(p, dict) and isinstance(p.get("pages"), dict):
                p["pages"] = {k: swap(v) for k, v in p["pages"].items()}
        save_json(macros_path, m, compact_steps=True)
        log("Seite „System“ ist jetzt Teil von „Hardware“ – macros.json umgestellt")


def migrate_files(log=print):
    """Umstellungen älterer Dateien beim Start (Treiber und Verwaltung, mehrfach aufrufbar)."""
    try:                                     # Konfigurationsordner (enthält Passwörter) nur für den Benutzer
        if os.path.isdir(CONFIG_DIR) and os.stat(CONFIG_DIR).st_mode & 0o077:
            os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass
    migrate_system_page(log=log)
    migrate_clock_pages(log=log)


def clean_macros(data):
    """Prüft die von der Seite gesendeten Profile und entfernt leere Einträge."""
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        raise ValueError("Ungültiges Format der Tastenbelegung")
    profiles = data["profiles"]
    if not 1 <= len(profiles) <= MAX_PROFILES:
        raise ValueError(f"Es sind 1 bis {MAX_PROFILES} Profile möglich")
    out = []
    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            raise ValueError("Ungültiges Profil")
        name = str(p.get("name") or "").strip()[:30] or f"Profil {i + 1}"
        keys_in = p.get("keys") if isinstance(p.get("keys"), dict) else {}
        keys = {}
        for layer, gkeys in keys_in.items():
            if layer not in LAYERS or not isinstance(gkeys, dict):
                raise ValueError(f"Ungültige Ebene: {layer}")
            for gkey, entry in gkeys.items():
                if not re.fullmatch(r"G([1-9]|1[0-2])", gkey) or not isinstance(entry, dict):
                    raise ValueError(f"Ungültige Taste: {gkey}")
                entry = {k: v for k, v in entry.items() if v not in (None, "", [])}
                if entry:
                    keys.setdefault(layer, {})[gkey] = entry
        prof = {"name": name, "keys": keys}
        if p.get("pages") is not None:
            pages = valid_profile_pages(p.get("pages"))
            if pages:
                prof["pages"] = pages
        faces = valid_clock_faces(p.get("clock"))
        if faces:
            prof["clock"] = faces
        if p.get("colors") is not None:
            colors = valid_colors(p.get("colors"))
            if not colors:
                raise ValueError(f"Ungültige Farben im Profil „{name}“")
            prof["colors"] = colors
        out.append(prof)
    return {"profiles": out}


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(**values):
    data = load_state()
    data.update(values)
    save_json(STATE_FILE, data)


class MacroStore:
    """Liest und schreibt macros.json (Profile → Ebenen M1–M3 → G-Tasten)."""

    def __init__(self, path, log=print):
        self.path = path
        self.log = log
        self.data = normalize_macros({})
        self.mtime = None
        self.reload()

    @property
    def profiles(self):
        return self.data["profiles"]

    def reload(self):
        """Gibt True zurück, wenn sich die Datei geändert hat."""
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError:
            if self.mtime is not None:
                self.log("Makrodatei entfernt – alle Makros deaktiviert.")
            changed = self.mtime is not None
            self.data, self.mtime = normalize_macros({}), None
            return changed
        if mtime == self.mtime:
            return False
        self.mtime = mtime
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("oberste Ebene muss ein Objekt sein")
            self.data = normalize_macros(data)
            count = sum(len(v) for p in self.profiles for v in p["keys"].values())
            self.log(f"Makros geladen: {len(self.profiles)} Profile, {count} Belegungen")
        except (ValueError, OSError) as ex:
            self.log(f"Makrodatei fehlerhaft, bisherige Makros bleiben aktiv: {ex}")
        return True

    def profile(self, pidx):
        return self.profiles[max(0, min(pidx, len(self.profiles) - 1))]

    def keys(self, pidx):
        """Belegung eines Profils: {"M1": {...}, "M2": {...}, "M3": {...}}"""
        return self.profile(pidx)["keys"]

    def get(self, pidx, layer, gkey):
        macro = self.keys(pidx).get(layer, {}).get(gkey)
        return macro if isinstance(macro, dict) else None

    def set(self, pidx, layer, gkey, macro):
        self.keys(pidx).setdefault(layer, {})[gkey] = macro
        self.save()

    def delete(self, pidx, layer, gkey):
        keys = self.keys(pidx)
        if keys.get(layer, {}).pop(gkey, None) is None:
            return False
        if not keys[layer]:
            del keys[layer]
        self.save()
        return True

    def save(self):
        save_json(self.path, self.data, compact_steps=True)
        self.mtime = os.path.getmtime(self.path)


# ═══════════════════════════════════════════════════════════════════════════
# Modul timer
#   Countdown, Stoppuhr und Pomodoro (Zustand und Zeitrechnung, ohne Anzeige).
# ═══════════════════════════════════════════════════════════════════════════

def timer_label(cfg):
    mode = cfg.get("mode")
    if mode == "stopwatch":
        return "Stoppuhr"
    if mode == "pomodoro":
        return f"Pomodoro {_num(cfg.get('work'), 25):g}/{_num(cfg.get('break'), 5):g}"
    return f"Timer {fmt_minutes(cfg.get('minutes') or 5)}"


def _num(v, default):
    try:
        return float(v) if v else default
    except (TypeError, ValueError):
        return default


def fmt_minutes(m):
    m = _num(m, 5)
    return f"{m:g} min" if m >= 1 else f"{round(m * 60)} s"


def fmt_clock(seconds):
    seconds = max(0, int(round(seconds)))
    h, rest = divmod(seconds, 3600)
    return f"{h}:{rest // 60:02d}:{rest % 60:02d}" if h else f"{rest // 60:02d}:{rest % 60:02d}"


class Timer:
    """Countdown, Stoppuhr oder Pomodoro – wird von der Hauptschleife fortgeschrieben."""

    def __init__(self):
        self.cfg = None            # Aktionseintrag {"mode", "minutes" | "work", "break"}
        self.mode = None
        self.running = False
        self.alarm = False         # Countdown abgelaufen, wartet auf Bestätigung
        self.phase = "work"        # Pomodoro: work / break
        self.rounds = 0            # abgeschlossene Arbeitsphasen
        self.total = 0.0           # Länge der aktuellen Phase (s)
        self.acc = 0.0             # bisher gelaufene Zeit (s), ohne laufenden Abschnitt
        self.since = None          # Start des laufenden Abschnitts (monotonic)

    @property
    def active(self):
        return self.mode is not None

    def _phase_len(self):
        c = self.cfg or {}
        if self.mode == "pomodoro":
            return 60 * max(1 / 60, float(c.get("work" if self.phase == "work" else "break") or (25 if self.phase == "work" else 5)))
        if self.mode == "timer":
            return 60 * max(1 / 60, float(c.get("minutes") or 5))
        return 0.0

    def start(self, cfg):
        self.cfg = dict(cfg)
        self.mode = cfg.get("mode") if cfg.get("mode") in ("timer", "stopwatch", "pomodoro") else "timer"
        self.phase, self.rounds, self.alarm = "work", 0, False
        self.total, self.acc = self._phase_len(), 0.0
        self.running, self.since = True, time.monotonic()

    def same(self, cfg):
        return self.active and self.cfg == dict(cfg)

    def elapsed(self, now=None):
        now = now or time.monotonic()
        return self.acc + (now - self.since if self.running and self.since else 0.0)

    def remaining(self, now=None):
        return max(0.0, self.total - self.elapsed(now))

    def toggle(self):
        if not self.active or self.alarm:
            return
        if self.running:
            self.acc, self.running = self.elapsed(), False
        else:
            self.running, self.since = True, time.monotonic()

    def reset(self):
        """Stoppuhr auf 0 bzw. Timer/Pomodoro beenden."""
        if self.mode == "stopwatch":
            self.acc, self.since = 0.0, time.monotonic()
            return True
        self.stop()
        return False

    def stop(self):
        self.__init__()

    def add_minute(self):
        if self.mode in ("timer", "pomodoro") and not self.alarm:
            self.total += 60

    def tick(self, now):
        """Liefert "done" (Timer abgelaufen) bzw. "work"/"break" (Pomodoro-Phase gewechselt)."""
        if not self.running or self.mode == "stopwatch":
            return None
        if self.elapsed(now) < self.total:
            return None
        if self.mode == "timer":
            self.acc, self.running, self.alarm = self.total, False, True
            return "done"
        if self.phase == "work":
            self.rounds += 1
            self.phase = "break"
        else:
            self.phase = "work"
        self.total, self.acc, self.since = self._phase_len(), 0.0, now
        return self.phase

    def display_value(self, now=None):
        return self.elapsed(now) if self.mode == "stopwatch" else self.remaining(now)

    def badge(self, now=None):
        if not self.active:
            return ""
        if self.alarm:
            return "!00:00"
        state = "=" if not self.running else ("~" if self.mode == "pomodoro" and self.phase == "break" else "+")
        return state + fmt_clock(self.display_value(now))


# ═══════════════════════════════════════════════════════════════════════════
# Modul audio
#   Signalton, Lautstärke und Mikrofon (PipeWire/wpctl, sonst PulseAudio/pactl).
# ═══════════════════════════════════════════════════════════════════════════

ALARM_SOUNDS = ["/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
                "/usr/share/sounds/freedesktop/stereo/complete.oga",
                "/usr/share/sounds/freedesktop/stereo/bell.oga",
                "/usr/share/sounds/Oxygen-Im-Nudge.ogg"]


def play_alarm(env, repeat=2):
    """Signalton über PipeWire/PulseAudio (im Hintergrund, Fehler werden ignoriert)."""
    sound = next((f for f in ALARM_SOUNDS if os.path.exists(f)), None)
    player = next((p for p in ("pw-play", "paplay", "canberra-gtk-play") if shutil.which(p)), None)
    if not sound or not player:
        return False

    def work():
        for _ in range(repeat):
            args = [player, "-f", sound] if player == "canberra-gtk-play" else [player, sound]
            try:
                subprocess.run(args, env=env, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (OSError, subprocess.TimeoutExpired):
                return
    threading.Thread(target=work, daemon=True).start()
    return True


# --------------------------------------------------------------------------- #
# Lautstärke (PipeWire/wpctl, sonst PulseAudio/pactl)
# --------------------------------------------------------------------------- #
def change_volume(action, step=5, env=None):
    """action: up, down, mute. Gibt (Prozent, stumm) zurück oder None."""
    import shutil
    run = lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env)
    step = max(1, min(25, int(step or 5)))
    try:
        if shutil.which("wpctl"):
            sink = "@DEFAULT_AUDIO_SINK@"
            if action == "mute":
                run(["wpctl", "set-mute", sink, "toggle"])
            elif action in ("up", "down"):
                run(["wpctl", "set-volume", "-l", "1.0", sink, f"{step}%{'+' if action == 'up' else '-'}"])
            out = run(["wpctl", "get-volume", sink]).stdout
            m = re.search(r"Volume:\s*([\d.]+)", out)
            return (round(float(m.group(1)) * 100), "MUTED" in out) if m else None
        if shutil.which("pactl"):
            sink = "@DEFAULT_SINK@"
            if action == "mute":
                run(["pactl", "set-sink-mute", sink, "toggle"])
            elif action in ("up", "down"):
                run(["pactl", "set-sink-volume", sink, f"{'+' if action == 'up' else '-'}{step}%"])
            vol = re.search(r"(\d+)%", run(["pactl", "get-sink-volume", sink]).stdout)
            mute = "yes" in run(["pactl", "get-sink-mute", sink]).stdout
            return (int(vol.group(1)), mute) if vol else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return None


def mic_state(env=None, toggle=False):
    """Mikrofon (Standardquelle) abfragen bzw. umschalten. True = stumm, None = unbekannt."""
    run = lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env)
    try:
        if shutil.which("wpctl"):
            src = "@DEFAULT_AUDIO_SOURCE@"
            if toggle:
                run(["wpctl", "set-mute", src, "toggle"])
            out = run(["wpctl", "get-volume", src]).stdout
            return "MUTED" in out if "Volume" in out else None
        if shutil.which("pactl"):
            src = "@DEFAULT_SOURCE@"
            if toggle:
                run(["pactl", "set-source-mute", src, "toggle"])
            out = run(["pactl", "get-source-mute", src]).stdout
            return ("yes" in out) if out else None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Modul geraet
#   Zugriff auf die G19s über USB: Displaybild senden, Tasten lesen, Beleuchtung, Helligkeit.
# ═══════════════════════════════════════════════════════════════════════════

# 512-Byte-Header, der jedem Displaybild vorangestellt wird
LCD_HEADER = bytes(
    [0x10, 0x0F, 0x00, 0x58, 0x02, 0x00, 0x00, 0x00,
     0x00, 0x00, 0x00, 0x3F, 0x01, 0xEF, 0x00, 0x0F]
    + list(range(16, 256))
    + list(range(256))
)
assert len(LCD_HEADER) == 512


class UsbReader(threading.Thread):
    """Liest einen Tasten-Endpunkt blockierend (Zeitlimit READ_TIMEOUT_MS) und legt jeden Report in
    die Warteschlange. So muss die Hauptschleife nicht ständig nachsehen, sondern wacht nur bei einem
    Tastendruck oder zum nächsten Bild auf. Ein USB-Fehler (z. B. Tastatur abgezogen) landet als
    ("error", Ausnahme) in der Warteschlange; die Hauptschleife beendet sich dann wie bisher."""

    READ_TIMEOUT_MS = 1000

    def __init__(self, g19, endpoint, size, queue):
        super().__init__(daemon=True)
        self.g19, self.endpoint, self.size, self.queue = g19, endpoint, size, queue
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.g19.read(self.endpoint, self.size, self.READ_TIMEOUT_MS)
            except Exception as ex:          # jeder USB-Fehler beendet den Treiber (systemd startet neu)
                self.queue.put(("error", ex))
                return
            if data:
                self.queue.put((self.endpoint, data))


# --------------------------------------------------------------------------- #
# USB-Zugriff
# --------------------------------------------------------------------------- #
class G19:
    def __init__(self):
        import usb.core
        import usb.util
        self.usb_core, self.usb_util = usb.core, usb.util

        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if dev is None:
            sys.exit("G19s (046d:c229) nicht gefunden – ist die Tastatur eingesteckt?")
        self.dev = dev

        for intf in (0, 1):
            try:
                if dev.is_kernel_driver_active(intf):
                    dev.detach_kernel_driver(intf)
            except usb.core.USBError as ex:
                sys.exit(
                    f"Kann Interface {intf} nicht übernehmen: {ex}\n"
                    "Ist die udev-Regel installiert und die Tastatur neu eingesteckt?"
                )
        try:
            dev.set_configuration()
        except usb.core.USBError:
            pass  # bereits konfiguriert
        for intf in (0, 1):
            usb.util.claim_interface(dev, intf)

    def read(self, endpoint, size, timeout_ms):
        """Liest einen Interrupt-Report; gibt None bei Timeout zurück."""
        try:
            return bytes(self.dev.read(endpoint, size, timeout=timeout_ms))
        except self.usb_core.USBTimeoutError:
            return None
        except self.usb_core.USBError as ex:
            if ex.errno == 110:  # ETIMEDOUT bei älteren pyusb-Versionen
                return None
            raise

    def send_frame(self, img):
        """Schickt ein 320x240-PIL-Bild ans Display (RGB565, spaltenweise)."""
        a = np.asarray(img.convert("RGB"), dtype=np.uint16)
        rgb565 = ((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5) | (a[:, :, 2] >> 3)
        data = np.ascontiguousarray(rgb565.T).astype("<u2").tobytes()
        self.dev.write(EP_LCD_OUT, LCD_HEADER + data, timeout=1000)

    def set_backlight(self, r, g, b):
        self.dev.ctrl_transfer(0x21, 0x09, 0x0307, 1, bytes([7, r, g, b]))

    def set_m_leds(self, mask):
        self.dev.ctrl_transfer(0x21, 0x09, 0x0305, 1, bytes([5, mask]))

    def set_brightness(self, value):
        """Displayhelligkeit 0–100."""
        value = max(0, min(100, value))
        self.dev.ctrl_transfer(
            0x41, 0x0A, 0x0000, 0x0000,
            bytes([value, 0xE2, 0x12, 0x00, 0x8C, 0x11, 0x00, 0x10, 0x00]),
        )

    def close(self):
        for intf in (0, 1):
            try:
                self.usb_util.release_interface(self.dev, intf)
            except Exception:                    # usb.core.USBError o. Ä.: Gerät evtl. schon weg
                pass
        self.usb_util.dispose_resources(self.dev)


# ═══════════════════════════════════════════════════════════════════════════
# Modul eingabe
#   Eingaben: Makroaufnahme (liest die Tastatur mit), Makro abspielen, Aktivität für den Bildschirmschoner.
# ═══════════════════════════════════════════════════════════════════════════

class Recorder:
    """Liest während der Aufnahme die normale Tastatur (046d:c228) mit."""

    def __init__(self):
        self.devices = []
        self.steps = []
        self.down = set()
        self.last = None
        self.error = None

    def start(self):
        from evdev import InputDevice, list_devices, ecodes as e
        self.devices, self.steps, self.down, self.last = [], [], set(), None
        denied = False
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except PermissionError:
                denied = True
                continue
            except OSError:
                continue
            if (dev.info.vendor == VENDOR_ID and dev.info.product == KEYBOARD_PRODUCT_ID
                    and e.EV_KEY in dev.capabilities()):
                self.devices.append(dev)
            else:
                dev.close()
        if not self.devices:
            # list_devices() liefert nur lesbare Geräte – fehlende Rechte sehen
            # daher genauso aus wie eine nicht gefundene Tastatur
            self.error = "Kein Lesezugriff auf Tastatur"
            return False
        return True

    def poll(self):
        from evdev import ecodes as e
        for dev in self.devices:
            try:
                for ev in dev.read():
                    if ev.type != e.EV_KEY or ev.value not in (0, 1):
                        continue
                    if ev.value == 0 and ev.code not in self.down:
                        continue  # Loslassen einer Taste, die vor der Aufnahme gedrückt war
                    t = ev.timestamp()
                    wait = 0 if self.last is None else int(round((t - self.last) * 1000))
                    self.last = t
                    if ev.value == 1:
                        self.down.add(ev.code)
                    else:
                        self.down.discard(ev.code)
                    self.steps.append([wait, key_name(ev.code), "down" if ev.value else "up"])
            except BlockingIOError:
                pass
            except OSError:
                pass

    def stop(self):
        self.poll()
        for code in list(self.down):
            self.steps.append([TAP_MS, key_name(code), "up"])
        for dev in self.devices:
            try:
                dev.close()
            except Exception:               # Gerät evtl. schon weg – Aufnahme trotzdem beenden
                pass
        self.devices = []
        return self.steps

    @property
    def keycount(self):
        return sum(1 for s in self.steps if s[2] == "down")


class Player:
    def __init__(self, ui, lock):
        self.ui, self.lock = ui, lock
        self.thread = None

    @property
    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def play(self, steps):
        if self.busy:
            return False
        self.thread = threading.Thread(target=self._run, args=(steps,), daemon=True)
        self.thread.start()
        return True

    def _run(self, steps):
        from evdev import ecodes as e
        pressed = set()
        try:
            for wait, code, value in steps:
                time.sleep(max(MIN_WAIT_MS, min(wait, MAX_WAIT_MS)) / 1000)
                with self.lock:
                    self.ui.write(e.EV_KEY, code, value)
                    self.ui.syn()
                (pressed.add if value else pressed.discard)(code)
        finally:
            with self.lock:
                for code in pressed:
                    self.ui.write(e.EV_KEY, code, 0)
                self.ui.syn()


# --------------------------------------------------------------------------- #
# Aktivität an Tastatur/Maus erkennen (für den Bildschirmschoner)
# --------------------------------------------------------------------------- #
class ActivityWatcher(threading.Thread):
    """Merkt sich nur den Zeitpunkt der letzten Eingabe – Tasteninhalte werden verworfen."""

    def __init__(self, log=print):
        super().__init__(daemon=True)
        self.log = log
        self.running = True
        self.last = time.monotonic()
        self.available = None           # None = unbekannt, False = keine Leserechte

    def touch(self):
        self.last = time.monotonic()

    def idle(self):
        return time.monotonic() - self.last

    def stop(self):
        self.running = False

    def _open_devices(self):
        from evdev import InputDevice, list_devices, ecodes as e
        devs = []
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except OSError:
                continue
            caps = dev.capabilities()
            if e.EV_KEY in caps or e.EV_REL in caps or e.EV_ABS in caps:
                devs.append(dev)
            else:
                dev.close()
        return devs

    def run(self):
        import select
        devs, rescan = [], 0.0
        while self.running:
            now = time.monotonic()
            if now >= rescan:
                for d in devs:
                    try:
                        d.close()
                    except Exception:       # Thread darf nie abbrechen
                        pass
                try:
                    devs = self._open_devices()
                except Exception:           # z. B. evdev-Fehler beim Abfragen der Fähigkeiten
                    devs = []
                if not devs and self.available is not False:
                    self.log("Bildschirmschoner: keine Eingabegeräte lesbar – zählt nur G-19s-Tasten")
                self.available = bool(devs)
                rescan = now + 60
            if not devs:
                time.sleep(2)
                continue
            try:
                ready, _, _ = select.select(devs, [], [], 1.0)
            except (OSError, ValueError):
                rescan = 0
                continue
            for d in ready:
                try:
                    for _ in d.read():
                        pass
                    self.last = time.monotonic()
                except (BlockingIOError, OSError):
                    pass
            if ready:
                # Aktivität erkannt – für den Bildschirmschoner reicht Sekundengenauigkeit. Ohne diese
                # Pause wacht der Thread bei Mausbewegung Hunderte Male pro Sekunde auf.
                time.sleep(1.0)


# ═══════════════════════════════════════════════════════════════════════════
# Modul programme
#   Programme und Webseiten starten (mit der Umgebung der Desktop-Sitzung), mpv-mpris finden.
# ═══════════════════════════════════════════════════════════════════════════

class Launcher:
    """Startet Webseiten/Befehle in der laufenden Desktop-Sitzung."""

    SESSION_VARS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
                    "XDG_RUNTIME_DIR", "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE",
                    "XDG_DATA_DIRS", "XDG_CONFIG_DIRS", "KDE_FULL_SESSION",
                    "KDE_SESSION_VERSION", "DESKTOP_SESSION", "PATH", "LANG", "LANGUAGE")

    def __init__(self, log=print):
        self.log = log
        self.children = []

    ENV_TTL = 30            # Sekunden, die die Sitzungsumgebung zwischengespeichert wird

    def _env(self):
        """Umgebung der Desktop-Sitzung (systemctl --user show-environment), 30 s zwischengespeichert."""
        now = time.monotonic()
        cached = getattr(self, "_env_cache", None)
        if cached and now - cached[0] < self.ENV_TTL:
            return dict(cached[1])
        env = self._session_env()
        self._env_cache = (now, env)
        return dict(env)

    def _session_env(self):
        env = dict(os.environ)
        try:
            out = subprocess.run(["systemctl", "--user", "show-environment"],
                                 capture_output=True, text=True, timeout=3).stdout
        except (OSError, subprocess.SubprocessError):
            return env
        for line in out.splitlines():
            key, sep, value = line.partition("=")
            if sep and key in self.SESSION_VARS and not value.startswith("$'"):
                env[key] = value
        return env

    def start(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd, shell=isinstance(cmd, str), env=self._env(),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
                cwd=os.path.expanduser("~"))
        except OSError as ex:
            self.log(f"Start fehlgeschlagen: {ex}")
            return False
        self.children.append(proc)
        return True

    def reap(self):
        self.children = [p for p in self.children if p.poll() is None]


def find_mpris_plugin():
    """Sucht das mpv-Plugin (Paket mpv-mpris), mit dem sich mpv bei KDE als Player anmeldet."""
    import glob
    patterns = ["/etc/mpv/scripts/mpris.so", "/usr/share/mpv/scripts/mpris.so",
                "/usr/lib/mpv-mpris/mpris.so", "/usr/lib/*/mpv-mpris/mpris.so",
                "/usr/lib/*/mpv/scripts/mpris.so", "/usr/local/lib/mpv-mpris/mpris.so",
                os.path.expanduser("~/.config/mpv/scripts/mpris.so")]
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            if os.path.isfile(path):
                return path
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Modul piwigo
#   Piwigo-Galerie: Anmeldung, Alben, Bildlisten, Bilder laden; Bild ins Display einpassen.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Piwigo: Alben und Bilder über die Web-API (ws.php) abrufen
# --------------------------------------------------------------------------- #
class PiwigoError(Exception):
    pass


class PiwigoClient:
    """Minimaler Client für die Piwigo-API. Funktioniert mit öffentlichen
    Alben ohne Anmeldung und mit privaten Alben über Benutzer/Passwort."""

    SIZES = ("medium", "large", "small", "xlarge", "2small", "xsmall", "thumb")

    def __init__(self, url, user="", password="", timeout=15):
        import http.cookiejar
        import urllib.request
        url = str(url or "").strip().rstrip("/")
        if not url:
            raise PiwigoError("Keine Piwigo-Adresse eingetragen")
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + url
        url = re.sub(r"/(ws\.php|index\.php)$", "", url)
        self.base = url
        self.user, self.password, self.timeout = user or "", password or "", timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", USER_AGENT)]
        self.logged_in = False

    def _call(self, method, params=None, post=False):
        import urllib.error
        import urllib.parse
        query = [("format", "json"), ("method", method)]
        body = None
        items = []
        for k, v in (params or {}).items():
            if isinstance(v, (list, tuple)):
                items += [(f"{k}[]", str(x)) for x in v]
            else:
                items.append((k, str(v).lower() if isinstance(v, bool) else str(v)))
        if post:
            body = urllib.parse.urlencode(items).encode()
        else:
            query += items
        url = f"{self.base}/ws.php?{urllib.parse.urlencode(query)}"
        try:
            with self.opener.open(url, data=body, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as ex:
            raise PiwigoError(f"Piwigo antwortet mit Fehler {ex.code} ({url.split('?')[0]})")
        except NET_ERRORS as ex:
            reason = err_text(ex)
            if "WRONG_VERSION_NUMBER" in reason or "wrong version number" in reason:
                raise PiwigoError("Die Galerie unterstützt kein https – Adresse mit http:// eintragen")
            if "CERTIFICATE_VERIFY_FAILED" in reason:
                raise PiwigoError("Das Zertifikat der Galerie ist ungültig oder selbst signiert")
            raise PiwigoError(f"Piwigo nicht erreichbar: {reason}")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            raise PiwigoError("Keine gültige Antwort – ist die Adresse eine Piwigo-Galerie?")
        if data.get("stat") != "ok":
            raise PiwigoError(f"Piwigo: {data.get('message') or data.get('err') or 'Fehler'}")
        return data.get("result")

    def login(self):
        if self.logged_in or not self.user:
            return
        try:
            self._call("pwg.session.login", {"username": self.user, "password": self.password}, post=True)
        except PiwigoError as ex:
            raise PiwigoError(f"Anmeldung fehlgeschlagen – Benutzer oder Passwort prüfen ({ex})")
        self.logged_in = True

    def albums(self):
        """Alle sichtbaren Alben: [{id, name, parent, level, images, total, path}]"""
        self.login()
        res = self._call("pwg.categories.getList", {"recursive": True, "fullname": False})
        cats = res.get("categories", []) if isinstance(res, dict) else res or []
        by_id = {}
        for c in cats:
            try:
                cid = int(c["id"])
            except (KeyError, TypeError, ValueError):
                continue
            parent = c.get("id_uppercat")
            by_id[cid] = {"id": cid, "name": re.sub(r"<[^>]+>", "", str(c.get("name", ""))).strip(),
                          "parent": int(parent) if str(parent or "").isdigit() else None,
                          "images": int(c.get("nb_images") or 0),
                          "total": int(c.get("total_nb_images") or c.get("nb_images") or 0),
                          "rank": str(c.get("global_rank") or "")}

        def path(cid, seen=()):
            a = by_id[cid]
            if a["parent"] in by_id and a["parent"] not in seen:
                return path(a["parent"], seen + (cid,)) + [a["name"]]
            return [a["name"]]

        out = []
        for cid, a in by_id.items():
            p = path(cid)
            out.append(dict(a, path=" / ".join(p), level=len(p) - 1))
        # Baumreihenfolge: nach global_rank, sonst nach Pfad
        out.sort(key=lambda a: ([int(x) for x in a["rank"].split(".") if x.isdigit()] or [9999], a["path"].lower()))
        for a in out:
            a.pop("rank", None)
        return out

    def images(self, album_ids, recursive=True, limit=5000):
        """Bilder der Alben: [{id, name, url, album}] – url zeigt auf eine passende Größe."""
        self.login()
        out, seen = [], set()
        for aid in album_ids:
            page = 0
            while len(out) < limit:
                res = self._call("pwg.categories.getImages",
                                 {"cat_id": int(aid), "recursive": bool(recursive),
                                  "per_page": 500, "page": page})
                imgs = res.get("images", []) if isinstance(res, dict) else []
                for im in imgs:
                    iid = im.get("id")
                    if iid in seen:
                        continue
                    seen.add(iid)
                    url = None
                    der = im.get("derivatives") or {}
                    for size in self.SIZES:
                        if isinstance(der.get(size), dict) and der[size].get("url"):
                            url = der[size]["url"]
                            break
                    url = url or im.get("element_url")
                    if url:
                        out.append({"id": iid, "name": str(im.get("name") or im.get("file") or ""),
                                    "url": url})
                paging = res.get("paging", {}) if isinstance(res, dict) else {}
                count = int(paging.get("count") or len(imgs))
                if count < 500 or not imgs:
                    break
                page += 1
        return out

    def fetch(self, url, limit=20 * 1024 * 1024):
        import urllib.parse
        if not re.match(r"^https?://", url, re.I):
            url = urllib.parse.urljoin(self.base + "/", url)
        if not re.match(r"^https?://", url, re.I):        # z. B. file:// aus der Serverantwort
            raise PiwigoError("Ungültige Bildadresse vom Server")
        try:
            with self.opener.open(url, timeout=self.timeout) as r:
                return r.read(limit)
        except NET_ERRORS as ex:
            raise PiwigoError(f"Bild nicht abrufbar: {err_text(ex)}")


def fit_photo(img, size, mode="contain"):
    """Bild auf die Displayfläche bringen: contain = ganz sichtbar mit unscharfem
    Hintergrund, cover = Fläche füllen (Ränder werden abgeschnitten)."""
    from PIL import ImageEnhance, ImageFilter, ImageOps
    img = ImageOps.exif_transpose(img).convert("RGB")
    if mode == "cover":
        return ImageOps.fit(img, size, Image.LANCZOS)
    bg = ImageOps.fit(img, size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(12))
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    fg = ImageOps.contain(img, size, Image.LANCZOS)
    bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
    return bg


# ═══════════════════════════════════════════════════════════════════════════
# Modul radio
#   Eigener Radioplayer (mpv mit Senderliste als Wiedergabeliste).
# ═══════════════════════════════════════════════════════════════════════════

class RadioManager:
    """Spielt Radiosender über einen externen Player (Standard: mpv) ab.

    Mit mpv wird die ganze Senderliste als Wiedergabeliste übergeben. Ist das
    Plugin mpv-mpris installiert, meldet sich mpv bei KDE als Player an: die
    Medientasten der Tastatur (Play/Pause, Vor/Zurück, Stop) und die
    KDE-Medienwiedergabe steuern dann auch das Radio.
    """

    def __init__(self, env_func, log=print):
        self.env_func, self.log = env_func, log
        self.proc = None
        self.station = None        # {"name", "url", "logo"}
        self.playlist = []         # Senderliste, die mpv als Wiedergabeliste bekommen hat
        self.lock = threading.Lock()

    @property
    def playing(self):
        return self.proc is not None and self.proc.poll() is None

    def current(self):
        with self.lock:
            return dict(self.station) if self.station and self.playing else None

    def playlist_urls(self):
        with self.lock:
            return [s["url"] for s in self.playlist]

    def follow(self, url):
        """mpv hat selbst den Sender gewechselt (z. B. per Medientaste) – mitziehen."""
        with self.lock:
            if not self.station or url == self.station.get("url"):
                return
            for s in self.playlist:
                if s["url"] == url:
                    self.station = dict(s)
                    self.log(f"Radio: {s.get('name') or url}")
                    return

    def _build_cmd(self, cmd, url, stations):
        import shlex
        try:
            is_mpv = os.path.basename(shlex.split(cmd)[0]) == "mpv"
        except (ValueError, IndexError):
            is_mpv = False
        urls = [s["url"] for s in stations]
        if is_mpv and url in urls:
            playlist = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or CACHE_DIR, "g19s-radio.m3u")
            os.makedirs(os.path.dirname(playlist), exist_ok=True)
            with open(playlist, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for s in stations:
                    name = (s.get("name") or s["url"]).replace("\n", " ")
                    f.write(f"#EXTINF:-1,{name}\n{s['url']}\n")
            arg = (f"--playlist={shlex.quote(playlist)} --playlist-start={urls.index(url)} "
                   f"--loop-playlist=inf")
            if "--load-scripts=no" in cmd:
                plugin = find_mpris_plugin()
                if plugin:
                    arg += f" --script={shlex.quote(plugin)}"
            return (cmd.replace("{url}", arg) if "{url}" in cmd else f"{cmd} {arg}"), True
        quoted = shlex.quote(url)
        return (cmd.replace("{url}", quoted) if "{url}" in cmd else f"{cmd} {quoted}"), False

    def play(self, station, player_cmd, stations=None):
        self.stop()
        url = station.get("url", "")
        if not url or not re.fullmatch(URL_RE, url):
            if url:
                self.log(f"Radio: ungültige Senderadresse ignoriert: {url[:80]!r}")
            return False
        stations = [dict(s) for s in (stations or []) if isinstance(s, dict)
                    and re.fullmatch(URL_RE, str(s.get("url") or ""))]
        if url not in [s["url"] for s in stations]:
            stations = [dict(station)]
        cmd, uses_list = self._build_cmd(player_cmd or DEFAULT_SETTINGS["radio_player"], url, stations)
        try:
            proc = subprocess.Popen(cmd, shell=True, env=self.env_func(),
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as ex:
            self.log(f"Radio konnte nicht gestartet werden: {ex}")
            return False
        time.sleep(0.3)
        if proc.poll() is not None:
            self.log(f"Radioplayer beendet sich sofort (Befehl: {cmd}) – ist er installiert?")
            return False
        with self.lock:
            self.proc, self.station = proc, dict(station)
            self.playlist = stations if uses_list else [dict(station)]
        self.log(f"Radio: {station.get('name') or url}")
        return True

    def stop(self):
        with self.lock:
            proc, self.proc, self.station = self.proc, None, None
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired, PermissionError):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

    def step(self, stations, player_cmd, direction):
        """Zum nächsten (+1) bzw. vorherigen (-1) Sender der Liste wechseln."""
        stations = [s for s in stations if s.get("url")]
        if not stations:
            return None
        cur = self.current()
        urls = [s["url"] for s in stations]
        idx = urls.index(cur["url"]) + direction if cur and cur["url"] in urls else 0
        station = stations[idx % len(stations)]
        return station if self.play(station, player_cmd, stations) else None


# ═══════════════════════════════════════════════════════════════════════════
# Modul musik
#   Aktuelle Wiedergabe über MPRIS/playerctl, Cover, Songtitel aus dem Radiostream (ICY).
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Aktuelle Wiedergabe (MPRIS über playerctl)
# --------------------------------------------------------------------------- #
class MediaWatcher(threading.Thread):
    """Fragt ab, was gerade läuft, und lädt das Cover: jede Sekunde, solange want_fast() gilt
    (Musikseite sichtbar oder Radio an), sonst alle SLOW_INTERVAL Sekunden – playerctl weckt
    bei jedem Aufruf alle Player über D-Bus."""

    SLOW_INTERVAL = 5

    FIELDS = ("player", "status", "title", "artist", "album", "art", "position", "length", "url")
    FMT = "\t".join(["{{playerName}}", "{{status}}", "{{title}}", "{{artist}}",
                     "{{album}}", "{{mpris:artUrl}}", "{{position}}", "{{mpris:length}}",
                     "{{xesam:url}}"])
    COVER_SIZE = 132
    ICY_INTERVAL = 30       # Sekunden zwischen zwei Abfragen beim Radiosender (je eine neue Verbindung)

    RADIO_PLAYER = "g19s-radio"

    def __init__(self, env_func, log=print, radio=None, radio_control=None):
        super().__init__(daemon=True)
        self.env_func, self.log = env_func, log
        self.radio = radio                   # RadioManager des Treibers
        self.radio_control = radio_control   # Funktion(action) für den eigenen Radioplayer
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.running = True
        self.want_fast = lambda: True       # setzt der Treiber (Musikseite sichtbar / Radio an)
        self.fast_now = True
        self.info = None
        self.error = None
        self.cover_url = None
        self.cover = None
        self.cover_bg = None
        self.env = None
        self.env_time = 0.0
        self.icy_url = None      # Stream, für den icy_title gilt
        self.icy_title = None    # z. B. "AC/DC - Thunderstruck"
        self.icy_next = 0.0
        self.icy_busy = False

    # -- öffentlich -------------------------------------------------------- #
    def snapshot(self):
        with self.lock:
            return self.info, self.cover, self.cover_bg, self.error

    def control(self, action):
        with self.lock:
            info = self.info
        if not info:
            return
        target = info["player"]
        if target == self.RADIO_PLAYER:
            if info.get("mpris"):
                target = info["mpris"]        # mpv direkt steuern (Pause, Sender vor/zurück)
            else:
                if self.radio_control:
                    self.radio_control(action)
                self.wake.set()
                return
        try:
            subprocess.Popen(["playerctl", "-p", target, action], env=self._env(),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            return
        time.sleep(0.15)
        self.wake.set()

    def stop(self):
        self.running = False
        self.wake.set()

    # -- intern ------------------------------------------------------------ #
    def _env(self):
        now = time.monotonic()
        if self.env is None or now - self.env_time > 30:
            self.env, self.env_time = self.env_func(), now
        return self.env

    def run(self):
        while self.running:
            try:
                self._poll()
            except Exception as ex:  # Sicherheitsnetz: nie wegen der Musikseite abstürzen
                with self.lock:
                    self.error = str(ex)
            self.fast_now = bool(self.want_fast())
            self.wake.wait(1.0 if self.fast_now else self.SLOW_INTERVAL)
            self.wake.clear()

    def refresh(self):
        """Sofort abfragen (z. B. vor „Song merken“), im aufrufenden Thread."""
        try:
            self._poll()
        except Exception as ex:             # wie in run(): nie wegen der Musikabfrage abstürzen
            with self.lock:
                self.error = str(ex)

    def _poll(self):
        error = None
        try:
            out = subprocess.run(["playerctl", "-a", "metadata", "--format", self.FMT],
                                 capture_output=True, text=True, timeout=3,
                                 env=self._env()).stdout
        except FileNotFoundError:
            out, error = "", "playerctl fehlt"
        except subprocess.TimeoutExpired:
            return

        players = []
        station = self.radio.current() if self.radio else None
        radio_urls = set(self.radio.playlist_urls()) if station else set()
        parsed = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == len(self.FIELDS):
                parsed.append(dict(zip(self.FIELDS, parts)))

        # Der eigene Radioplayer (mpv) meldet sich mit mpv-mpris bei KDE an: diesen
        # Eintrag erkennen, damit Pause und Senderwechsel per Medientaste ankommen.
        mpris_radio = None
        if station:
            for p in parsed:
                if p["player"].split(".")[0] == "mpv" and (p["url"] in radio_urls or not p["url"]):
                    mpris_radio = p
                    break
            if mpris_radio and mpris_radio["url"]:
                self.radio.follow(mpris_radio["url"])
                station = self.radio.current() or station
            status = mpris_radio["status"] if mpris_radio and mpris_radio["status"] in ("Playing", "Paused") else "Playing"
            # eigener Radioplayer hat Vorrang, er wurde zuletzt per Taste gestartet
            players.append({"player": self.RADIO_PLAYER, "status": status,
                            "title": station.get("name") or "Radio", "artist": "",
                            "album": "", "art": station.get("logo") or "", "position": 0,
                            "length": 0, "url": station["url"], "fetched": time.monotonic(),
                            "mpris": mpris_radio["player"] if mpris_radio else None})
        for p in parsed:
            if p is mpris_radio:
                continue
            if p["status"] not in ("Playing", "Paused") or not (p["title"] or p["artist"]):
                continue
            if station and p["url"] in radio_urls:
                continue  # derselbe Stream wie das eigene Radio
            for key in ("position", "length"):
                try:
                    p[key] = max(0, int(float(p[key] or 0)))
                except ValueError:
                    p[key] = 0
            p["fetched"] = time.monotonic()
            players.append(p)
        players.sort(key=lambda p: (p["player"] != self.RADIO_PLAYER, p["status"] != "Playing"))
        info = players[0] if players else None
        if info:
            self._apply_radio(info)

        art = info["art"] if info else None
        if art != self.cover_url:
            cover, bg = self._load_cover(art) if art else (None, None)
            with self.lock:
                self.cover_url, self.cover, self.cover_bg = art, cover, bg
        with self.lock:
            self.info, self.error = info, (None if info else error)

    # -- Internetradio: aktuellen Song aus dem Stream lesen (ICY-Metadaten) -- #
    @staticmethod
    def _is_radio(info):
        return (info["url"].startswith(("http://", "https://"))
                and not info["artist"] and not info["length"])

    def _apply_radio(self, info):
        info["station"] = None
        if not self._is_radio(info):
            return
        url = info["url"]
        now = time.monotonic()
        if url != self.icy_url:
            self.icy_url, self.icy_title, self.icy_next = url, None, 0.0
        if now >= self.icy_next and not self.icy_busy and info["status"] == "Playing":
            self.icy_busy = True
            self.icy_next = now + self.ICY_INTERVAL
            threading.Thread(target=self._fetch_icy, args=(url,), daemon=True).start()

        title = self.icy_title
        if not title:
            return
        info["station"] = info["title"]
        artist, sep, song = title.partition(" - ")
        if sep and artist.strip() and song.strip():
            info["artist"], info["title"] = artist.strip(), song.strip()
        else:
            info["title"] = title

    def _fetch_icy(self, url):
        import urllib.request
        title = None
        try:
            req = urllib.request.Request(url, headers={"Icy-MetaData": "1",
                                                       "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as r:
                metaint = int(r.headers.get("icy-metaint") or 0)
                if 0 < metaint <= 256 * 1024:      # übliche Werte 8–64 KiB; mehr = kein Titel
                    remaining = metaint
                    while remaining > 0:          # Audiodaten bis zum Metadatenblock überspringen
                        chunk = r.read(min(remaining, 16384))
                        if not chunk:
                            raise EOFError
                        remaining -= len(chunk)
                    length = r.read(1)[0] * 16
                    meta = r.read(length) if length else b""
                    try:
                        text = meta.rstrip(b"\0").decode("utf-8")
                    except UnicodeDecodeError:
                        text = meta.rstrip(b"\0").decode("latin-1")
                    m = re.search(r"StreamTitle='(.*?)';", text, re.S)
                    if m and m.group(1).strip():
                        title = " ".join(m.group(1).split())
        except NET_ERRORS as ex:
            self.log(f"Radio-Titel nicht abrufbar: {ex}")
        finally:
            if url == self.icy_url:
                if title or not self.icy_title:
                    self.icy_title = title
                if title:
                    self.wake.set()   # sofort anzeigen
            self.icy_busy = False

    def _load_cover(self, url):
        import io
        import urllib.parse
        import urllib.request
        from PIL import ImageEnhance, ImageFilter, ImageOps
        try:
            if url.startswith("file://"):
                path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
                if not os.path.isfile(path):
                    return None, None
                with open(path, "rb") as f:
                    raw = f.read(8 * 1024 * 1024)
            elif url.startswith(("http://", "https://")):
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=5) as r:
                    raw = r.read(8 * 1024 * 1024)
            else:
                return None, None
            img = open_remote_image(raw, draft=(640, 640)).convert("RGB")
        except (NET_ERRORS + (Image.DecompressionBombError,)) as ex:    # PIL meldet kaputte Bilder als OSError
            self.log(f"Cover konnte nicht geladen werden: {ex}")
            return None, None
        cover = ImageOps.fit(img, (self.COVER_SIZE, self.COVER_SIZE), Image.LANCZOS)
        bg = ImageOps.fit(img, (WIDTH, HEIGHT), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
        bg = ImageEnhance.Brightness(bg).enhance(0.35)
        return cover, bg


# ═══════════════════════════════════════════════════════════════════════════
# Modul diashow
#   Diashow: Bildliste (Piwigo, Ordner oder Lieblingsbilder), Bildwechsel, Zwischenspeicher, Albenliste.
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# Modul abruf
#   Abruf aus dem Netz: http_get() und Poller (Hintergrund-Thread, der Daten regelmäßig holt,
#   solange die zugehörige Displayseite eingeschaltet ist).
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# Modul wetter
#   Wetter von Open-Meteo: Abruf und Ortssuche.
# ═══════════════════════════════════════════════════════════════════════════

# --- Wetter (Open-Meteo, kostenlos, ohne Anmeldung) ---------------------------
WEATHER_URL = os.environ.get("G19S_WEATHER_URL", "https://api.open-meteo.com/v1/forecast")
GEOCODE_URL = os.environ.get("G19S_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")
WEATHER_CODES = {
    0: ("Klar", "sun"), 1: ("Überwiegend klar", "sun"), 2: ("Teilweise bewölkt", "partly"),
    3: ("Bedeckt", "cloud"), 45: ("Nebel", "fog"), 48: ("Reifnebel", "fog"),
    51: ("Leichter Niesel", "drizzle"), 53: ("Nieselregen", "drizzle"), 55: ("Starker Niesel", "drizzle"),
    56: ("Gefrierender Niesel", "drizzle"), 57: ("Gefrierender Niesel", "drizzle"),
    61: ("Leichter Regen", "rain"), 63: ("Regen", "rain"), 65: ("Starker Regen", "rain"),
    66: ("Gefrierender Regen", "rain"), 67: ("Gefrierender Regen", "rain"),
    71: ("Leichter Schnee", "snow"), 73: ("Schneefall", "snow"), 75: ("Starker Schnee", "snow"),
    77: ("Schneegriesel", "snow"), 80: ("Regenschauer", "rain"), 81: ("Kräftige Schauer", "rain"),
    82: ("Heftige Schauer", "rain"), 85: ("Schneeschauer", "snow"), 86: ("Starke Schneeschauer", "snow"),
    95: ("Gewitter", "thunder"), 96: ("Gewitter, Hagel", "thunder"), 99: ("Schweres Gewitter", "thunder"),
}


def geocode(name, count=8):
    """Ortssuche: [{name, lat, lon, label}]"""
    import urllib.parse
    q = urllib.parse.urlencode({"name": name, "count": count, "language": "de", "format": "json"})
    data = json.loads(http_get(f"{GEOCODE_URL}?{q}").decode())
    out = []
    for r in data.get("results") or []:
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        out.append({"name": r.get("name", ""), "lat": r.get("latitude"), "lon": r.get("longitude"),
                    "label": ", ".join(p for p in parts if p)})
    return out


class WeatherPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 900, log)

    def cfg(self):
        return self.get_settings().get("weather") or {}

    def enabled(self):
        c = self.cfg()
        return (c.get("lat") is not None and c.get("lon") is not None
                and "weather" in (self.get_settings().get("pages") or []))

    def signature(self):
        c = self.cfg()
        return (c.get("lat"), c.get("lon"))

    def fetch(self):
        import urllib.parse
        c = self.cfg()
        q = urllib.parse.urlencode({
            "latitude": c["lat"], "longitude": c["lon"], "timezone": "auto", "forecast_days": 4,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,"
                       "wind_speed_10m,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        })
        return json.loads(http_get(f"{WEATHER_URL}?{q}").decode())


# ═══════════════════════════════════════════════════════════════════════════
# Modul nachrichten
#   Nachrichten: RSS/Atom einlesen und regelmäßig abrufen.
# ═══════════════════════════════════════════════════════════════════════════

# --- Nachrichten (RSS/Atom) ---------------------------------------------------
def parse_feed(raw, source=""):
    """RSS 2.0, RSS 1.0 (RDF) und Atom: [{title, link, time, source}]"""
    import email.utils
    import datetime as dt
    import xml.etree.ElementTree as ET
    root = ET.fromstring(raw)
    local = lambda tag: tag.rsplit("}", 1)[-1]
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title, link, when = "", "", None
        for ch in el:
            name = local(ch.tag)
            if name == "title":
                import html
                title = re.sub(r"<[^>]+>", "", html.unescape("".join(ch.itertext()))).strip()
            elif name == "link":
                href = ch.get("href")
                if href and (ch.get("rel") in (None, "alternate") or not link):
                    link = href
                elif (ch.text or "").strip() and not link:
                    link = ch.text.strip()
            elif name in ("pubDate", "date", "updated", "published") and ch.text and when is None:
                t = ch.text.strip()
                try:
                    when = email.utils.parsedate_to_datetime(t)
                    if when.tzinfo is None:           # RFC 822 ohne Zone („-0000“) = UTC
                        when = when.replace(tzinfo=dt.timezone.utc)
                except (TypeError, ValueError, IndexError):
                    try:
                        when = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
                        if when.tzinfo is None:
                            when = when.astimezone()
                    except ValueError:
                        when = None
        if title:
            out.append({"title": " ".join(title.split()), "link": link, "time": when, "source": source})
    return out


class NewsPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 900, log)

    def cfg(self):
        return self.get_settings().get("news") or {}

    def enabled(self):
        return bool(self.cfg().get("feeds")) and "news" in (self.get_settings().get("pages") or [])

    def signature(self):
        return json.dumps(self.cfg().get("feeds"), sort_keys=True)

    def fetch(self):
        import datetime as dt
        items, errors = [], []
        for f in self.cfg().get("feeds") or []:
            url = str(f.get("url") or "").strip()
            if not url:
                continue
            name = str(f.get("name") or domain_of(url))
            try:
                items += parse_feed(http_get(url, timeout=20), name)
            except FEED_ERRORS as ex:
                errors.append(f"{name}: {err_text(ex)}")
        if errors and not items:
            raise RuntimeError("; ".join(errors))
        old = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        items.sort(key=lambda x: x["time"] or old, reverse=True)
        return {"items": items[:max(5, min(100, int(self.cfg().get("count") or 30)))], "errors": errors}


# ═══════════════════════════════════════════════════════════════════════════
# Modul unwetter
#   Amtliche Unwetterwarnungen des DWD (über Bright Sky) für den Wetterort.
# ═══════════════════════════════════════════════════════════════════════════

# --- Unwetterwarnungen (DWD, bereitgestellt von Bright Sky) --------------------
ALERTS_URL = os.environ.get("G19S_ALERTS_URL", "https://api.brightsky.dev/alerts")
SEVERITY = {"minor": ("Wetterwarnung", (240, 200, 40)), "moderate": ("Markante Warnung", (245, 140, 30)),
            "severe": ("Unwetterwarnung", (230, 50, 50)), "extreme": ("Extremes Unwetter", (170, 60, 200))}
SEVERITY_RANK = {"minor": 1, "moderate": 2, "severe": 3, "extreme": 4}


class WarningsPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 600, log)

    def enabled(self):
        s = self.get_settings()
        w = s.get("weather") or {}
        return (w.get("lat") is not None and w.get("lon") is not None and
                ("warnings" in (s.get("pages") or []) or (s.get("warnings") or {}).get("popup", True)))

    def signature(self):
        w = self.get_settings().get("weather") or {}
        return (w.get("lat"), w.get("lon"))

    def fetch(self):
        import datetime as dt
        import urllib.parse
        w = self.get_settings().get("weather") or {}
        q = urllib.parse.urlencode({"lat": w["lat"], "lon": w["lon"]})
        data = json.loads(http_get(f"{ALERTS_URL}?{q}").decode())
        now = dt.datetime.now().astimezone()

        def when(v):
            try:
                return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone() if v else None
            except ValueError:
                return None
        alerts = []
        for a in data.get("alerts") or []:
            if a.get("status", "actual") != "actual":
                continue
            onset, expires = when(a.get("onset") or a.get("effective")), when(a.get("expires"))
            if expires and expires < now:
                continue
            alerts.append({"id": str(a.get("alert_id") or a.get("id")), "severity": a.get("severity") or "minor",
                           "event": a.get("event_de") or a.get("event_en") or "Warnung",
                           "headline": a.get("headline_de") or a.get("headline_en") or "",
                           "description": a.get("description_de") or a.get("description_en") or "",
                           "instruction": a.get("instruction_de") or a.get("instruction_en") or "",
                           "onset": onset or now, "expires": expires})
        alerts.sort(key=lambda a: (-SEVERITY_RANK.get(a["severity"], 0), a["onset"]))
        loc = data.get("location") or {}
        return {"alerts": alerts, "place": loc.get("name") or w.get("name") or ""}


# ═══════════════════════════════════════════════════════════════════════════
# Modul netzwerk
#   Erreichbarkeit von Geräten (Ping oder TCP-Port), Router und eigene Adresse ermitteln.
# ═══════════════════════════════════════════════════════════════════════════

# --- Netzwerk: Erreichbarkeit von Geräten ---------------------------------------
def default_gateway(proc_root="/proc"):
    try:
        with open(os.path.join(proc_root, "net/route")) as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) > 3 and parts[1] == "00000000" and int(parts[3], 16) & 2:
                    g = bytes.fromhex(parts[2])[::-1]
                    return ".".join(str(b) for b in g)
    except (OSError, ValueError):
        pass
    return None


def local_ip():
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))           # sendet nichts, ermittelt nur die eigene Adresse
            return s.getsockname()[0]
    except OSError:
        return ""


def check_host(host, timeout=2):
    """(erreichbar, Millisekunden). host = Name/IP (Ping) oder Name:Port (TCP-Verbindung)."""
    import socket
    m = re.fullmatch(r"(.+):(\d{1,5})", host)
    if m and not host.count(":") > 1:
        t0 = time.monotonic()
        try:
            with socket.create_connection((m.group(1), int(m.group(2))), timeout=timeout):
                return True, (time.monotonic() - t0) * 1000
        except OSError:
            return False, None
    if host.startswith("-"):
        return False, None                   # wäre eine ping-Option
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", str(timeout), "--", host], capture_output=True, text=True,
                           timeout=timeout + 3, env=dict(os.environ, LC_ALL="C"))
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    ms = re.search(r"time[=<]([\d.]+)\s*ms", r.stdout)
    return r.returncode == 0, float(ms.group(1)) if ms else None


class NetworkPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 60, log)

    def enabled(self):
        return "network" in (self.get_settings().get("pages") or [])

    def signature(self):
        return json.dumps((self.get_settings().get("network") or {}).get("hosts"), sort_keys=True)

    def fetch(self):
        hosts = [h for h in (self.get_settings().get("network") or {}).get("hosts") or []
                 if isinstance(h, dict) and str(h.get("host") or "").strip()][:12]
        results = [None] * len(hosts)

        def work(i, h):
            host = str(h["host"]).strip()
            if host == "gateway":
                host = default_gateway() or ""
            ok, ms = check_host(host) if host else (False, None)
            results[i] = {"name": h.get("name") or host, "host": host or "(kein Router gefunden)", "ok": ok, "ms": ms}
        threads = [threading.Thread(target=work, args=(i, h), daemon=True) for i, h in enumerate(hosts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        return {"hosts": [r for r in results if r], "ip": local_ip()}


# ═══════════════════════════════════════════════════════════════════════════
# Modul updates
#   Verfügbare Systemupdates (apt, Flatpak) und „Neustart erforderlich“.
# ═══════════════════════════════════════════════════════════════════════════

# --- Systemupdates (apt, Flatpak) -----------------------------------------------
class UpdatesPoller(Poller):
    FLATPAK_INTERVAL = 6 * 3600     # flatpak remote-ls fragt die Server im Netz ab – seltener als apt

    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 3600, log)
        self._flatpak = (-1e9, None)             # (Zeitpunkt, Anzahl)

    def refresh(self):
        self._flatpak = (-1e9, None)             # MENU auf der Seite: alles neu abfragen
        super().refresh()

    def enabled(self):
        return "updates" in (self.get_settings().get("pages") or [])

    def fetch(self):
        env = dict(os.environ, LC_ALL="C")
        pkgs, security = [], 0
        if shutil.which("apt"):
            r = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True, timeout=120, env=env)
            for line in r.stdout.splitlines():
                if "/" in line and "[upgradable" in line:
                    pkgs.append(line.split("/", 1)[0])
                    if "-security" in line.split(" ", 1)[0]:
                        security += 1
        flatpak = None
        if (self.get_settings().get("updates") or {}).get("flatpak", True) and shutil.which("flatpak"):
            if time.monotonic() - self._flatpak[0] < self.FLATPAK_INTERVAL:
                flatpak = self._flatpak[1]
            else:
                try:
                    r = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application"],
                                       capture_output=True, text=True, timeout=120, env=env)
                    flatpak = len([l for l in r.stdout.splitlines() if l.strip()]) if r.returncode == 0 else None
                except (OSError, subprocess.TimeoutExpired):
                    flatpak = None
                if flatpak is not None:
                    self._flatpak = (time.monotonic(), flatpak)
        reboot = os.path.exists("/var/run/reboot-required")
        return {"apt": len(pkgs), "security": security, "packages": pkgs[:60], "flatpak": flatpak,
                "reboot": reboot, "checked": time.strftime("%H:%M"), "apt_ok": bool(shutil.which("apt"))}


# ═══════════════════════════════════════════════════════════════════════════
# Modul kalender
#   Kalender: iCalendar einlesen, Serientermine, Zeitzonen, Nextcloud/CalDAV-Suche, Abruf.
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# Modul hardware
#   Hardware-Werte: Temperaturen und Lüfter (hwmon, nvidia-smi), Netzwerk, Datenträger, CPU/RAM.
# ═══════════════════════════════════════════════════════════════════════════

# --- Hardware-Sensoren (hwmon) ------------------------------------------------
class Hardware:
    def __init__(self, sys_root="/sys", proc_root="/proc"):
        self.sys, self.proc = sys_root, proc_root
        self._net = None
        self._nvidia = (0.0, None)

    def _read(self, path):
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return None

    def sensors(self):
        """{"cpu": °C, "gpu": °C, "gpu_load": %, "nvme": °C, "fans": [(Name, U/min)]}"""
        import glob
        out = {"cpu": None, "gpu": None, "gpu_load": None, "nvme": None, "fans": []}
        for hw in sorted(glob.glob(os.path.join(self.sys, "class/hwmon/hwmon*"))):
            name = self._read(os.path.join(hw, "name")) or ""
            temps = {}
            for f in sorted(glob.glob(os.path.join(hw, "temp*_input"))):
                v = self._read(f)
                label = self._read(f.replace("_input", "_label")) or os.path.basename(f).split("_")[0]
                if v and v.lstrip("-").isdigit():
                    temps[label] = int(v) / 1000
            if name in ("k10temp", "zenpower", "coretemp", "cpu_thermal") and temps and out["cpu"] is None:
                for pref in ("Tctl", "Tdie", "Package id 0", "Tccd1"):
                    if pref in temps:
                        out["cpu"] = temps[pref]
                        break
                else:
                    out["cpu"] = max(temps.values())
            elif name in ("amdgpu", "nouveau", "radeon") and temps and out["gpu"] is None:
                out["gpu"] = temps.get("edge") or temps.get("junction") or max(temps.values())
            elif name == "nvme" and temps and out["nvme"] is None:
                out["nvme"] = temps.get("Composite") or max(temps.values())
            for f in sorted(glob.glob(os.path.join(hw, "fan*_input"))):
                v = self._read(f)
                if v and v.isdigit() and int(v) > 0:
                    label = self._read(f.replace("_input", "_label")) or f"Lüfter {os.path.basename(f)[3:-6]}"
                    out["fans"].append((label, int(v)))
        for f in sorted(glob.glob(os.path.join(self.sys, "class/drm/card*/device/gpu_busy_percent"))):
            v = self._read(f)
            if v and v.isdigit():
                out["gpu_load"] = int(v)
                break
        if out["gpu"] is None:
            self._nvidia_query(out)
        return out

    def _nvidia_query(self, out):
        import shutil
        now = time.monotonic()
        if now - self._nvidia[0] > 30:          # nvidia-smi ist teuer und kann die Grafikkarte wecken
            val = None
            if shutil.which("nvidia-smi"):
                try:
                    r = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
                                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
                    t, u = [x.strip() for x in r.stdout.splitlines()[0].split(",")[:2]]
                    val = (float(t), int(float(u)))
                except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                    val = None
            self._nvidia = (now, val)
        if self._nvidia[1]:
            out["gpu"], out["gpu_load"] = self._nvidia[1]

    def network(self):
        """Datenrate in Bytes/s (empfangen, gesendet) seit dem letzten Aufruf."""
        rx = tx = 0
        try:
            with open(os.path.join(self.proc, "net/dev")) as f:
                for line in f.readlines()[2:]:
                    iface, data = line.split(":", 1)
                    iface = iface.strip()
                    if iface == "lo" or iface.startswith(("docker", "veth", "virbr", "br-")):
                        continue
                    v = data.split()
                    rx += int(v[0])
                    tx += int(v[8])
        except (OSError, ValueError, IndexError):
            return None
        now = time.monotonic()
        prev, self._net = self._net, (now, rx, tx)
        if not prev or now - prev[0] <= 0:
            return 0.0, 0.0
        dt_ = now - prev[0]
        return max(0.0, (rx - prev[1]) / dt_), max(0.0, (tx - prev[2]) / dt_)

    @staticmethod
    def disks():
        seen, out = set(), []
        for label, path in (("System", "/"), ("Home", os.path.expanduser("~"))):
            try:
                st = os.statvfs(path)
                dev = os.stat(path).st_dev
            except OSError:
                continue
            if dev in seen:
                continue
            seen.add(dev)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            if total:
                out.append((label, (total - free) / total * 100, total))
        return out


# --------------------------------------------------------------------------- #
# Systemwerte (ohne Zusatzpakete, direkt aus /proc)
# --------------------------------------------------------------------------- #
class Stats:
    def __init__(self):
        self._prev = self._cpu_times()

    @staticmethod
    def _cpu_times():
        with open("/proc/stat") as f:
            vals = [int(x) for x in f.readline().split()[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return sum(vals), idle

    def cpu_percent(self):
        total, idle = self._cpu_times()
        pt, pi = self._prev
        self._prev = (total, idle)
        dt = total - pt
        return 0.0 if dt <= 0 else max(0.0, min(100.0, 100.0 * (1 - (idle - pi) / dt)))

    @staticmethod
    def memory():
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, val = line.split(":", 1)
                info[key] = int(val.split()[0])  # kB
        total = info["MemTotal"]
        used = total - info.get("MemAvailable", info.get("MemFree", 0))
        return used / 1048576, total / 1048576, 100.0 * used / total

    @staticmethod
    def load():
        return os.getloadavg()


# ═══════════════════════════════════════════════════════════════════════════
# Modul benachrichtigungen
#   KDE-Benachrichtigungen mitlesen (dbus-monitor).
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Benachrichtigungen: KDE-Meldungen mitlesen (dbus-monitor)
# --------------------------------------------------------------------------- #
class NotificationWatcher(threading.Thread):
    """Beobachtet org.freedesktop.Notifications.Notify auf dem Sitzungsbus."""

    RULE = "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"

    def __init__(self, env_func, on_notify, log=print):
        super().__init__(daemon=True)
        self.env_func, self.on_notify, self.log = env_func, on_notify, log
        self.running = True
        self.proc = None

    def stop(self):
        self.running = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    @staticmethod
    def parse(lines):
        """Wertet dbus-monitor-Ausgabe aus und liefert (App, Titel, Text) je Meldung."""
        args, cur, active = [], None, False
        for line in lines:
            line = line.rstrip("\n")
            if cur is not None:                       # mehrzeiliger String
                if line.endswith('"'):
                    cur.append(line[:-1])
                    args.append("\n".join(cur))
                    cur = None
                else:
                    cur.append(line)
                continue
            if line.startswith(("method call", "signal", "method return", "error")):
                if active and len(args) >= 3:
                    yield NotificationWatcher._emit(args)
                active = "member=Notify" in line
                args = []
                continue
            if not active:
                continue
            m = re.match(r'^\s{3}string "(.*)$', line)
            if m and len(args) < 4:
                rest = m.group(1)
                if rest.endswith('"'):
                    args.append(rest[:-1])
                else:
                    cur = [rest]
                if len(args) == 4:
                    yield NotificationWatcher._emit(args)
                    active, args = False, []
        if active and len(args) >= 3:
            yield NotificationWatcher._emit(args)

    @staticmethod
    def _emit(args):
        # Reihenfolge bei Notify: app_name, (replaces_id), app_icon, summary, body
        app, _icon, summary = args[0], args[1], args[2]
        body = args[3] if len(args) > 3 else ""
        body = re.sub(r"<[^>]+>", "", body)             # einfache HTML-Auszeichnung entfernen
        return app.strip(), summary.strip(), " ".join(body.split())

    def run(self):
        import shutil
        if not shutil.which("dbus-monitor"):
            self.log("Benachrichtigungen: dbus-monitor fehlt (Paket dbus-bin)")
            return
        while self.running:
            try:
                self.proc = subprocess.Popen(["dbus-monitor", "--session", self.RULE], env=self.env_func(),
                                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                                             errors="replace")
                for app, summary, body in self.parse(self.proc.stdout):
                    try:
                        self.on_notify(app, summary, body)
                    except Exception as ex:  # Sicherheitsnetz für den Rückruf in die Hauptanwendung
                        self.log(f"Benachrichtigung nicht angezeigt: {ex}")
            except OSError as ex:
                self.log(f"Benachrichtigungen nicht verfügbar: {ex}")
            for _ in range(20):                         # nach Abbruch in 10 s neu verbinden
                if not self.running:
                    return
                time.sleep(0.5)


# ═══════════════════════════════════════════════════════════════════════════
# Modul sammlungen
#   Gemerkte Songs und Lieblingsbilder (songs.json, favorites.json).
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Gemerkte Songs, Lieblingsbilder, Sicherung
# --------------------------------------------------------------------------- #
def load_list(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def remember_song(info, station=None):
    """Aktuellen Titel an songs.json anhängen. Liefert den Eintrag oder None (nichts läuft / schon gemerkt)."""
    if not info or not (info.get("title") or info.get("artist")):
        return None
    title, artist = str(info.get("title") or "").strip(), str(info.get("artist") or "").strip()
    if not artist and " - " in title:
        artist, title = [x.strip() for x in title.split(" - ", 1)]
    songs = load_list(SONGS_FILE)
    entry = {"time": time.strftime("%Y-%m-%d %H:%M"), "artist": artist, "title": title,
             "source": (station or {}).get("name") or str(info.get("player") or "")}
    if songs and songs[-1].get("artist") == artist and songs[-1].get("title") == title:
        return None
    songs.append(entry)
    save_json(SONGS_FILE, songs[-500:])
    return entry


def toggle_favorite(info, source):
    """Bild zu den Lieblingsbildern hinzufügen bzw. entfernen. True = ist jetzt Favorit."""
    favs = load_list(FAVORITES_FILE)
    key = str(info["id"])
    rest = [f for f in favs if str(f.get("id")) != key]
    if len(rest) != len(favs):
        save_json(FAVORITES_FILE, rest)
        return False
    rest.append({"id": info["id"], "name": info.get("name", ""), "url": info.get("url", ""),
                 "local": bool(info.get("local")), "source": source, "page": info.get("page", ""),
                 "time": time.strftime("%Y-%m-%d %H:%M")})
    save_json(FAVORITES_FILE, rest)
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Modul sicherung
#   Sicherung: Dateiliste, tar.gz erzeugen, automatische Sicherung.
#
#   Ziele der automatischen Sicherung (settings.json → "backup" → "target"):
#     folder     Ordner auf diesem Rechner (auch ein eingebundenes NAS oder der Nextcloud-Sync-Ordner)
#     nextcloud  Nextcloud über WebDAV (Serveradresse, Benutzer, App-Passwort, Ordner – wird angelegt)
#     webdav     beliebiger WebDAV-Ordner (z. B. NAS mit WebDAV-Dienst)
#     smb        Windows-Freigabe/NAS (\nasreigabe\ordner) über smbclient oder KDEs kioclient
# ═══════════════════════════════════════════════════════════════════════════

# Dateien einer Sicherung (relativ zum Home-Verzeichnis)
BACKUP_FILES = [
    ".config/g19s/macros.json",
    ".config/g19s/settings.json",
    ".config/g19s/state.json",
    ".config/g19s/songs.json",
    ".config/g19s/favorites.json",
    ".config/kglobalshortcutsrc",
    ".config/systemd/user/g19s.service",
    ".local/bin/g19s.py",
    ".local/bin/g19s-gui.py",
]
DESKTOP_RE = re.compile(r"\.local/share/applications/[A-Za-z0-9._-]+\.desktop")


def backup_members(home=None):
    home = home or os.path.expanduser("~")
    members = [p for p in BACKUP_FILES if os.path.isfile(os.path.join(home, p))]
    appdir = os.path.join(home, ".local/share/applications")
    if os.path.isdir(appdir):
        for name in sorted(os.listdir(appdir)):
            rel = f".local/share/applications/{name}"
            # KDE-Befehle („Befehl oder Skript“) und der eigene Starter
            if DESKTOP_RE.fullmatch(rel) and (name.startswith("net.local.") or name.startswith("g19s")):
                members.append(rel)
    return members


def make_backup(home=None):
    import io
    import tarfile
    home = home or os.path.expanduser("~")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel in backup_members(home):
            tar.add(os.path.join(home, rel), arcname=rel)
    return buf.getvalue()


BACKUP_PATTERN = re.compile(r"g19s-sicherung-.*_.*\.tar\.gz")       # wie bisher: g19s-sicherung-*_*.tar.gz


class BackupError(OSError):
    """Verständliche Fehlermeldung eines Sicherungsziels."""


class FolderTarget:
    def __init__(self, folder):
        self.folder = os.path.expanduser(str(folder or "").strip())
        if re.match(r"^(smb|https?|webdavs?)://|^\\\\", self.folder, re.I):
            raise BackupError("Das ist keine Ordneradresse auf diesem Rechner – bitte als Ziel „NAS (Windows-Freigabe)“, "
                              "„Nextcloud“ oder „WebDAV“ wählen")

    def describe(self):
        return self.folder

    def location(self, name):
        return os.path.join(self.folder, name)

    def prepare(self):
        if not self.folder or not os.path.isdir(self.folder):
            raise BackupError(f"Ordner nicht gefunden: {self.folder or '(leer)'} – ist das NAS eingebunden?")

    def upload(self, name, data):
        """Nur für den Benutzer lesbar (0600) – die Sicherung enthält Passwörter aus settings.json."""
        path = os.path.join(self.folder, name)
        fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(path + ".tmp", path)

    def names(self):
        return os.listdir(self.folder)

    def delete(self, name):
        os.remove(os.path.join(self.folder, name))


class WebDavTarget:
    """WebDAV-Ordner (Nextcloud, NAS). nextcloud=True: url ist die Serveradresse, dir der Ordner darin."""

    def __init__(self, url, user="", password="", remote_dir="", nextcloud=False):
        url = str(url or "").strip()
        if not url:
            raise BackupError("Bitte die Adresse angeben")
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + re.sub(r"^webdavs?://", "", url, flags=re.I)
        self.user, self.password = str(user or "").strip(), str(password or "")
        self.parts = []                      # Ordner, die angelegt werden dürfen (Nextcloud)
        if nextcloud:
            u = urllib.parse.urlsplit(url)
            path = u.path
            q = urllib.parse.parse_qs(u.query)
            if "/apps/files" in path:        # aus der Adresszeile des Browsers kopiert: dort gezeigter Ordner
                path = path.split("/apps/files")[0]
                if q.get("dir"):
                    remote_dir = q["dir"][0]
            path = re.sub(r"/index\.php$", "", path.rstrip("/"))
            if "/remote.php/dav/files/" in path:
                root = path.rstrip("/")
            else:
                path = re.sub(r"/remote\.php/(web)?dav$", "", path)
                if not self.user:
                    raise BackupError("Bitte den Nextcloud-Benutzernamen angeben")
                root = f"{path}/remote.php/dav/files/{urllib.parse.quote(self.user)}"
            self.parts = [p for p in str(remote_dir or "").replace("\\", "/").split("/") if p.strip()]
            path = root + "".join("/" + urllib.parse.quote(p.strip()) for p in self.parts)
            self.base = urllib.parse.urlunsplit((u.scheme, u.netloc, root, "", ""))
            url = urllib.parse.urlunsplit((u.scheme, u.netloc, path, "", ""))
        self.url = url.rstrip("/") + "/"

    def describe(self):
        return urllib.parse.unquote(self.url)

    def location(self, name):
        return self.describe() + name

    def _req(self, method, url, data=None, headers=None, ok=(200, 201, 204, 207)):
        h = dict(headers or {}, **{"User-Agent": USER_AGENT})
        if self.user:
            h["Authorization"] = basic_auth(self.user, self.password)
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with open_url(req, 60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as ex:
            if ex.code in ok:
                return ex.code, ex.read()
            if ex.code == 401:
                raise BackupError("Anmeldung abgelehnt – Benutzername und (App-)Passwort prüfen")
            if ex.code == 403:
                raise BackupError("Zugriff verweigert – fehlen Schreibrechte für den Ordner?")
            if ex.code == 404:
                raise BackupError(f"Ordner nicht gefunden: {urllib.parse.unquote(url)}")
            if ex.code == 507:
                raise BackupError("Kein Speicherplatz mehr auf dem Server")
            raise BackupError(f"Server meldet {ex.code} {ex.reason} für {urllib.parse.unquote(url)}")
        except urllib.error.URLError as ex:
            raise BackupError(f"Server nicht erreichbar: {ex.reason}")
        except (OSError, http.client.HTTPException) as ex:
            raise BackupError(f"Verbindung fehlgeschlagen: {ex}")

    def prepare(self):
        """Ordner anlegen (Nextcloud: jede fehlende Ebene), sonst prüfen, dass er existiert."""
        if self.parts:
            url = self.base
            for p in self.parts:
                url += "/" + urllib.parse.quote(p.strip())
                self._req("MKCOL", url, ok=(201, 405))     # 405 = gibt es schon
        self._req("PROPFIND", self.url, b"", {"Depth": "0"})

    def upload(self, name, data):
        self._req("PUT", self.url + urllib.parse.quote(name), data, {"Content-Type": "application/gzip"})

    def names(self):
        _, body = self._req("PROPFIND", self.url, b"", {"Depth": "1"})
        out = []
        for href in re.findall(rb"<(?:\w+:)?href>([^<]+)</(?:\w+:)?href>", body):
            name = urllib.parse.unquote(href.decode("utf-8", "replace").rstrip("/").rsplit("/", 1)[-1])
            if name:
                out.append(name)
        return out

    def delete(self, name):
        self._req("DELETE", self.url + urllib.parse.quote(name), ok=(200, 204, 404))


class SmbTarget:
    """Windows-Freigabe (NAS). Nutzt smbclient, sonst KDEs kioclient (Plasma)."""

    def __init__(self, url, user="", password="", tool=None):
        raw = str(url or "").strip().replace("\\", "/")
        raw = re.sub(r"^smb:", "", raw, flags=re.I).lstrip("/")
        parts = [p for p in raw.split("/") if p]
        if len(parts) < 2:
            raise BackupError("Bitte die Freigabe angeben, z. B. \\\\nas\\freigabe\\Sicherungen")
        self.host, self.share, self.dir = parts[0], parts[1], "/".join(parts[2:])
        if any(c in raw for c in '";\n\r') or not re.fullmatch(r"[\w.\-\[\]:]+", self.host):
            raise BackupError("Die Freigabe enthält ungültige Zeichen (\" ; oder Zeilenumbruch)")
        self.user, self.password = str(user or "").strip(), str(password or "")
        self.tool = tool or ("smbclient" if shutil.which("smbclient") else
                             next((t for t in ("kioclient", "kioclient5") if shutil.which(t)), None))
        if not self.tool:
            raise BackupError("Für Windows-Freigaben fehlt das Programm smbclient – bitte installieren: "
                              "sudo apt install smbclient")

    def describe(self):
        return f"\\\\{self.host}\\{self.share}" + "".join("\\" + p for p in self.dir.split("/") if p)

    def location(self, name):
        return self.describe() + "\\" + name

    # smbclient -------------------------------------------------------------- #
    def _smb(self, commands):
        cd = f'cd "{self.dir}"; ' if self.dir else ""
        cmd = ["smbclient", f"//{self.host}/{self.share}", "-c", cd + commands]
        env = dict(os.environ)
        if self.user:
            cmd += ["-U", self.user]
            env["PASSWD"] = self.password    # Passwort nicht in der Befehlszeile
        else:
            cmd.append("-N")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        except (OSError, subprocess.SubprocessError) as ex:
            raise BackupError(f"smbclient: {ex}")
        out = r.stdout + r.stderr
        for code, msg in (("NT_STATUS_LOGON_FAILURE", "Anmeldung abgelehnt – Benutzername und Passwort prüfen"),
                          ("NT_STATUS_BAD_NETWORK_NAME", f"Freigabe „{self.share}“ nicht gefunden"),
                          ("NT_STATUS_OBJECT_NAME_NOT_FOUND", "Ordner nicht gefunden"),
                          ("NT_STATUS_OBJECT_PATH_NOT_FOUND", "Ordner nicht gefunden"),
                          ("NT_STATUS_ACCESS_DENIED", "Zugriff verweigert – fehlen Schreibrechte?"),
                          ("NT_STATUS_HOST_UNREACHABLE", f"NAS „{self.host}“ nicht erreichbar"),
                          ("NT_STATUS_IO_TIMEOUT", f"NAS „{self.host}“ antwortet nicht"),
                          ("NT_STATUS_CONNECTION_REFUSED", f"NAS „{self.host}“ lehnt die Verbindung ab"),
                          ("Connection to", f"NAS „{self.host}“ nicht erreichbar")):
            if code in out:
                raise BackupError(msg)
        if r.returncode:
            raise BackupError("smbclient: " + (out.strip().splitlines() or ["Fehler"])[-1])
        return r.stdout

    # kioclient -------------------------------------------------------------- #
    # Das Passwort kommt NICHT in die Adresse (sie stünde für alle Benutzer sichtbar in der
    # Prozessliste). kioclient holt es aus KWallet – dafür die Freigabe einmal in Dolphin öffnen
    # und das Passwort speichern. Sicherer und ohne diesen Schritt: smbclient installieren.
    def _kio_url(self, name=""):
        cred = urllib.parse.quote(self.user, safe="") + "@" if self.user else ""
        path = "/".join(urllib.parse.quote(p) for p in [self.share] + [d for d in self.dir.split("/") if d])
        return f"smb://{cred}{self.host}/{path}/" + urllib.parse.quote(name)

    def _kio(self, *args):
        try:
            env = Launcher()._env()               # DBus/KWallet der Sitzung
        except Exception:                          # ohne Sitzung: eigene Umgebung
            env = dict(os.environ)
        try:
            r = subprocess.run([self.tool, "--noninteractive", *args], capture_output=True, text=True,
                               timeout=120, env=env)
        except (OSError, subprocess.SubprocessError) as ex:
            raise BackupError(f"{self.tool}: {ex}")
        if r.returncode:
            msg = (r.stderr.strip().splitlines() or [""])[-1] or f"Fehler {r.returncode}"
            raise BackupError(f"NAS: {msg} – Tipp: smbclient installieren (sudo apt install smbclient) "
                              "oder die Freigabe einmal in Dolphin öffnen und das Passwort speichern")
        return r.stdout

    def prepare(self):
        self.names()

    def upload(self, name, data):
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
            f.write(data)
            local = f.name
        try:
            if self.tool == "smbclient":
                self._smb(f'put "{local}" "{name}"')
            else:
                self._kio("copy", "file://" + urllib.parse.quote(local), self._kio_url(name))
        finally:
            os.remove(local)

    def names(self):
        if self.tool == "smbclient":
            out = self._smb("ls")
            return [m.group(1) for m in re.finditer(r"^\s+(\S.*?)\s+[A-Z]*\s+\d+\s+\w{3} \w{3}", out, re.M)]
        return [l.strip().rstrip("/") for l in self._kio("ls", self._kio_url()).splitlines() if l.strip()]

    def delete(self, name):
        if self.tool == "smbclient":
            self._smb(f'del "{name}"')
        else:
            self._kio("remove", self._kio_url(name))


def backup_target(cfg):
    """Sicherungsziel aus den Einstellungen ("backup") – oder aus einem Ordnernamen (ältere Aufrufer)."""
    if not isinstance(cfg, dict):
        return FolderTarget(cfg)
    t = cfg.get("target") or "folder"
    if t == "nextcloud":
        return WebDavTarget(cfg.get("url"), cfg.get("user"), cfg.get("password"),
                            cfg.get("remote_dir") or "G19s-Sicherung", nextcloud=True)
    if t == "webdav":
        return WebDavTarget(cfg.get("url"), cfg.get("user"), cfg.get("password"))
    if t == "smb":
        return SmbTarget(cfg.get("url"), cfg.get("user"), cfg.get("password"))
    return FolderTarget(cfg.get("folder"))


def auto_backup(target, keep=8, home=None):
    """Sicherung ins Ziel schreiben und alte automatische Sicherungen dort aufräumen.
    target: Einstellungen "backup" (dict) oder ein Ordner. Liefert den Ort der Sicherung."""
    t = backup_target(target)
    t.prepare()
    name = f"g19s-sicherung-{time.strftime('%Y-%m-%d_%H%M')}.tar.gz"
    t.upload(name, make_backup(home))
    try:
        old = sorted(n for n in t.names() if BACKUP_PATTERN.fullmatch(n))
        for n in old[:max(0, len(old) - max(1, int(keep or 8)))]:
            try:
                t.delete(n)
            except OSError:
                pass
    except OSError:
        pass                                 # Aufräumen ist nicht kritisch
    return t.location(name)


def test_backup_target(cfg):
    """Verbindung prüfen: Ordner vorbereiten, Probedatei schreiben, wieder löschen. Liefert eine Meldung."""
    t = backup_target(cfg)
    t.prepare()
    probe = f"g19s-test-{int(time.time())}.txt"
    t.upload(probe, b"G19s: Test der Sicherung\n")
    found = probe in t.names()
    t.delete(probe)
    count = len([n for n in t.names() if BACKUP_PATTERN.fullmatch(n)])
    if not found:
        raise BackupError("Probedatei geschrieben, aber im Ordner nicht wiedergefunden")
    return f"Verbindung in Ordnung: {t.describe()} ({count} vorhandene Sicherungen)"


# ═══════════════════════════════════════════════════════════════════════════
# Modul anzeige_basis
#   Grundlagen der Displayanzeige: Schriften, Farben, Hilfsfunktionen zum Zeichnen,
#   Fußzeile und die Registry der Displayseiten.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Displayseiten
# --------------------------------------------------------------------------- #
def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format("-Bold" if bold else ""),
        "/usr/share/fonts/truetype/noto/NotoSans-{}.ttf".format("Bold" if bold else "Regular"),
        "/usr/share/fonts/opentype/noto/NotoSans-{}.otf".format("Bold" if bold else "Regular"),
        "/usr/share/fonts/truetype/liberation/LiberationSans-{}.ttf".format("Bold" if bold else "Regular"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# Registry: Seiten-ID → Zeichenfunktion (wird von @page gefüllt)
PAGE_RENDERERS = {}


def page(page_id):
    """Methode als Zeichenfunktion der Displayseite page_id anmelden."""
    def deco(fn):
        PAGE_RENDERERS[page_id] = fn
        return fn
    return deco


# Registry: Seiten-ID → Tastenfunktion(app, pressed) → True = Tasten verarbeitet
# (sonst blättern Rechts/Runter und Links/Hoch die Seiten)
PAGE_KEYS = {}


def page_keys(*page_ids):
    """Funktion als Tastenbehandlung der Displayseite(n) anmelden."""
    def deco(fn):
        for pid in page_ids:
            PAGE_KEYS[pid] = fn
        return fn
    return deco


class RendererBase:
    BG = (8, 10, 16)

    FG = (235, 238, 245)

    DIM = (130, 138, 155)

    def __init__(self):
        self.f_huge = load_font(78, bold=True)
        self.f_large = load_font(58, bold=True)
        self.f_big = load_font(26, bold=True)
        self.f_mid = load_font(20)
        self.f_small = load_font(15)
        self.f_small_b = load_font(15, bold=True)
        self.f_title = load_font(19, bold=True)
        self.f_title_s = load_font(15, bold=True)
        self.f_tiny = load_font(12)
        self.stats = Stats()
        self.media = None
        self.slideshow = None
        self.settings = DEFAULT_SETTINGS
        self.profile_name = ""
        self.weather = None
        self.calendar = None
        self.cal_hidden = set()          # am Display ausgeblendete Kalender (Schlüssel)
        self.hw = Hardware()
        self.visible = None          # Indizes der eingeschalteten Seiten (Reihenfolge)
        self.clock_face = "digital"   # Zifferblatt der Seite „Uhr“ (setzt die App je Profil/Ebene)
        self.timer_badge = ""        # laufender Timer in der Fußzeile, z. B. "+04:12"
        self.mic_muted = False       # Mikrofon stumm → rotes Symbol in der Fußzeile
        self.sleep_badge = ""        # Einschlaftimer, z. B. "29"
        self.cal_sel = None          # markierter Termin auf der Terminseite (Index) oder None
        self.cal_items = []          # zuletzt gezeigte (gefilterte) Termine
        self.news = self.alerts = self.net = self.updates = None      # Poller der neuen Seiten
        self.sel = {"news": None, "warnings": None}                     # markierte Zeile je Seite
        self.list_items = {"news": [], "warnings": []}

    def _center(self, draw, y, text, font, fill):
        w = draw.textlength(text, font=font)
        draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)

    def _fit(self, draw, text, font, max_w):
        if draw.textlength(text, font=font) <= max_w:
            return text
        while text and draw.textlength(text + "…", font=font) > max_w:
            text = text[:-1]
        return text + "…"

    def _footer(self, draw, profile, page, pages):
        color = PROFILE_COLOR.get(profile, self.FG)
        draw.rectangle([0, HEIGHT - FOOTER_H, WIDTH, HEIGHT], fill=(20, 24, 34))
        draw.rectangle([10, HEIGHT - 19, 22, HEIGHT - 7], fill=color)
        label = f"{self.profile_name} · {profile}" if self.profile_name else f"Profil {profile}"
        step = 14 if pages <= 12 else 10               # viele Seiten: Punkte enger
        dots_x = WIDTH - 14 - (pages - 1) * step - 10
        room = dots_x - 36
        if self.timer_badge:
            state, text = self.timer_badge[0], self.timer_badge[1:]
            col = {"+": (240, 170, 60), "~": (62, 207, 126), "=": (150, 156, 170), "!": (255, 80, 80)}[state]
            bw = draw.textlength(text, font=self.f_small_b)
            x = dots_x - bw - 6
            draw.text((x, HEIGHT - 22), text, font=self.f_small_b, fill=col)
            self._icon_clock(draw, x - 16, HEIGHT - 20, 12, col, paused=(state == "="))
            room -= bw + 26
            dots_x = x - 20
        if self.sleep_badge:
            bw = draw.textlength(self.sleep_badge, font=self.f_small_b)
            x = dots_x - bw - 6
            draw.text((x, HEIGHT - 22), self.sleep_badge, font=self.f_small_b, fill=(150, 170, 255))
            self._icon_moon(draw, x - 18, HEIGHT - 20, (150, 170, 255), (20, 24, 34))
            room -= bw + 26
            dots_x = x - 20
        if self.mic_muted:
            self._icon_mic(draw, dots_x - 18, HEIGHT - 21, (255, 70, 70))
            room -= 22
        draw.text((30, HEIGHT - 22), self._fit(draw, label, self.f_small, max(30, room)),
                  font=self.f_small, fill=self.FG)
        for i in range(pages):
            x = WIDTH - 14 - (pages - 1 - i) * step
            fill = self.FG if i == page else self.DIM
            rr = 4 if step == 14 else 3
            draw.ellipse([x - rr, HEIGHT - 13 - rr, x + rr, HEIGHT - 13 + rr], fill=fill)

    def _wrap(self, d, text, font, max_w, max_lines):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = f"{cur} {w}".strip()
            if d.textlength(test, font=font) <= max_w:
                cur = test
                continue
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        consumed = " ".join(lines)
        if len(consumed) < len(" ".join(words)) and lines:
            lines[-1] = self._fit(d, lines[-1] + " …", font, max_w)
        return [self._fit(d, line, font, max_w) for line in lines]

    # ---- Wetter --------------------------------------------------------- #
    def _hint_page(self, symbol, title, text, title_color=None):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        if symbol:
            self._center(d, 30, symbol, self.f_huge, (60, 66, 84))
        self._center(d, 128, title, self.f_big, title_color or self.FG)
        for i, line in enumerate(self._wrap(d, text, self.f_small, WIDTH - 24, 2)):
            self._center(d, 166 + i * 19, line, self.f_small, self.DIM)
        return img

    # ---- Nachrichten ---------------------------------------------------- #
    def _poll_state(self, poller, symbol, title, need=None):
        """(Daten, Fehler) oder fertiges Hinweisbild."""
        if need:
            return None, self._hint_page(symbol, title, need)
        data, err, _ = poller.snapshot() if poller else (None, None, 0)
        if data is None:
            return None, self._hint_page(symbol, f"{title}-Fehler" if err else title, err or "Lade …",
                                         (235, 90, 90) if err else None)
        return data, None

    def _header(self, d, title, right="", warn=False):
        d.text((12, 4), title, font=self.f_title, fill=self.FG)
        if right:
            d.text((WIDTH - 12 - d.textlength(right, font=self.f_small), 8), right, font=self.f_small, fill=self.DIM)
        if warn:
            d.text((12 + d.textlength(title, font=self.f_title) + 8, 8), "⚠", font=self.f_small, fill=(240, 170, 60))

    def _scroll_marks(self, d, more_above, more_below):
        """Kleine Pfeile links/rechts in der Fußzeile: es gibt weitere Einträge."""
        if more_above:
            d.text((8, HEIGHT - 20), "▲", font=self.f_tiny, fill=(240, 170, 60))
        if more_below:
            d.text((WIDTH - 8 - d.textlength("▼", font=self.f_tiny), HEIGHT - 20), "▼",
                   font=self.f_tiny, fill=(240, 170, 60))

    def _heart(self, d, x, y, size, color, outline=(255, 255, 255)):
        r = size / 4
        pts = [(x + size / 2, y + size)]
        d.ellipse([x - 1, y - 1, x + size / 2 + 1, y + size / 2 + 1], fill=outline)
        d.ellipse([x + size / 2 - 1, y - 1, x + size + 1, y + size / 2 + 1], fill=outline)
        d.polygon([(x - 1, y + r), (x + size + 1, y + r), (x + size / 2, y + size + 2)], fill=outline)
        d.ellipse([x, y, x + size / 2, y + size / 2], fill=color)
        d.ellipse([x + size / 2, y, x + size, y + size / 2], fill=color)
        d.polygon([(x, y + r), (x + size, y + r), pts[0]], fill=color)

    def _icon_mic(self, d, x, y, color, muted=True):
        d.rounded_rectangle([x + 4, y, x + 10, y + 9], radius=3, fill=color)
        d.arc([x + 1, y + 3, x + 13, y + 13], 0, 180, fill=color, width=2)
        d.line([(x + 7, y + 13), (x + 7, y + 15)], fill=color, width=2)
        if muted:
            d.line([(x, y + 15), (x + 14, y)], fill=(255, 255, 255), width=2)

    def _icon_moon(self, d, x, y, color, bg):
        d.ellipse([x, y, x + 13, y + 13], fill=color)
        d.ellipse([x + 4, y - 2, x + 16, y + 10], fill=bg)

    def _icon_clock(self, d, x, y, size, color, paused=False):
        d.ellipse([x, y, x + size, y + size], outline=color, width=2)
        cx, cy = x + size / 2, y + size / 2
        if paused:
            d.line([(cx - 2, cy - 2), (cx - 2, cy + 2)], fill=color, width=2)
            d.line([(cx + 2, cy - 2), (cx + 2, cy + 2)], fill=color, width=2)
        else:
            d.line([(cx, cy), (cx, y + 3)], fill=color, width=2)
            d.line([(cx, cy), (x + size - 3, cy)], fill=color, width=2)

    def _icon_bell(self, d, cx, top, color):
        d.pieslice([cx - 26, top, cx + 26, top + 52], 180, 360, fill=color)
        d.rectangle([cx - 26, top + 26, cx + 26, top + 44], fill=color)
        d.polygon([(cx - 34, top + 50), (cx + 34, top + 50), (cx + 26, top + 42), (cx - 26, top + 42)], fill=color)
        d.ellipse([cx - 7, top + 50, cx + 7, top + 62], fill=color)
        d.ellipse([cx - 4, top - 7, cx + 4, top + 1], fill=color)


def move_selection(sel, pressed, n):
    """Markierung einer Liste mit Hoch/Runter bewegen (erste Taste markiert den ersten Eintrag)."""
    if pressed & LKEY_BITS["DOWN"]:
        sel = 0 if sel is None else min(n - 1, sel + 1)
    if pressed & LKEY_BITS["UP"]:
        sel = 0 if sel is None else max(0, sel - 1)
    return sel


def refresh_page(app, page_id):
    """MENU auf einer Infoseite: Daten sofort neu abfragen."""
    app.refreshers[page_id].refresh()
    app.show("Aktualisieren", ["wird neu abgefragt …"], PROFILE_COLOR[app.layer], 1.2)


# ═══════════════════════════════════════════════════════════════════════════
# Modul uhr_basis
#   Grundlagen der Zifferblätter der Seite „Uhr“.
#
#   Ein Zifferblatt ist eine Methode, die mit @clock_face("id") angemeldet wird und
#   ein fertiges Displaybild (320×240, Fußzeile zeichnet render()) liefert:
#
#       class MeineUhren:
#           @clock_face("beispiel", fps=1)
#           def face_beispiel(self, profile):
#               t = self._clock_now()                 # Zeitstempel (nie time.time() direkt!)
#               now = time.localtime(t)
#               opt = self._copt("beispiel")          # Optionen aus settings.json → "clock"
#               c = self._clock_canvas(("beispiel", …), bg, build_static)   # 3-fach vergrößerte Fläche
#               … zeichnen mit c.circle / c.hand / c.text …
#               return self._clock_finish(c)
#
#   Name und Reihenfolge stehen in CLOCK_FACES (konstanten), Optionen in CLOCK_OPTIONS.
#
#   Gemeinsame Hilfen (bitte benutzen statt eigener Varianten):
#     clock_font(style, size, bold)      Schriften (sans, serif, mono, sans-cond, serif-cond), zwischengespeichert
#     self._clock_canvas(key, bg, build) 3-fach vergrößerte Fläche mit zwischengespeichertem Hintergrund
#     self._clock_cache(slot, key, build) sonstiges Unveränderliches (je slot nur der jüngste key)
#     CLOCK_CX, CLOCK_CY, CLOCK_H         Mitte und Höhe der Uhrfläche; ROMAN_XII römische Ziffern (mit „IIII“)
#   Top-Level-Namen eines Moduls tragen dessen Präfix (_mech_, _sky_, _disp_, _info_), weil alle Module
#   einen Namensraum teilen. Zwischenspeicher werden beim Wechsel des Zifferblatts geleert (CLOCK_CACHES); eigene Speicher nicht anlegen.
#   fps > 1 lässt das Display öfter neu zeichnen (flüssige Bewegungen); fps darf auch
#   eine Funktion(optionen) sein. Analoge Uhren werden CLOCK_SS-fach gezeichnet und
#   verkleinert (weiche Kanten); Unveränderliches wird mit _clock_canvas zwischengespeichert.
# ═══════════════════════════════════════════════════════════════════════════

CLOCK_SS = 3                                # Vergrößerung beim Zeichnen (Kantenglättung)
CLOCK_H = HEIGHT - FOOTER_H                 # Fläche über der Fußzeile
CLOCK_CX, CLOCK_CY = WIDTH / 2, CLOCK_H / 2   # Mitte der Uhrfläche (160, 107)
ROMAN_XII = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]   # Uhren-„IIII“
WEEKDAY_2 = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]
MONTH_3 = ["JAN", "FEB", "MÄR", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEZ"]


def load_serif(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif{}.ttf".format("-Bold" if bold else ""),
        "/usr/share/fonts/truetype/liberation/LiberationSerif-{}.ttf".format("Bold" if bold else "Regular"),
        "/usr/share/fonts/truetype/noto/NotoSerif-{}.ttf".format("Bold" if bold else "Regular"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return load_font(size, bold)


_CLOCK_FONT_FILES = {"sans": "DejaVuSans", "serif": "DejaVuSerif", "mono": "DejaVuSansMono",
                     "sans-cond": "DejaVuSansCondensed", "serif-cond": "DejaVuSerifCondensed"}
_CLOCK_FONTS = {}


def clock_font(style, size, bold=False):
    """Schrift für Zifferblätter (einmal geladen, dann aus dem Zwischenspeicher).
    style: sans, serif, mono, sans-cond, serif-cond (DejaVu); size in Pixeln – auf der 3-fach
    vergrößerten Fläche also z. B. 10 * CLOCK_SS. Fehlt die Datei: load_font bzw. load_serif."""
    key = (style, int(size), bool(bold))
    font = _CLOCK_FONTS.get(key)
    if font is None:
        path = f"/usr/share/fonts/truetype/dejavu/{_CLOCK_FONT_FILES[style]}{'-Bold' if bold else ''}.ttf"
        if os.path.exists(path):
            font = ImageFont.truetype(path, int(size))
        else:
            font = (load_serif if style.startswith("serif") else load_font)(int(size), bold)
        _CLOCK_FONTS[key] = font
    return font


class _Canvas:
    """Zeichenfläche in Displaykoordinaten, intern CLOCK_SS-fach vergrößert."""

    def __init__(self, img):
        self.img, self.d, self.s = img, ImageDraw.Draw(img), CLOCK_SS

    def pt(self, cx, cy, r, deg):
        """Punkt im Abstand r vom Mittelpunkt; deg = 0 bei 12 Uhr, im Uhrzeigersinn."""
        a = math.radians(deg)
        return ((cx + r * math.sin(a)) * self.s, (cy - r * math.cos(a)) * self.s)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        s = self.s
        self.d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=fill, outline=outline,
                       width=max(1, round(width * s)) if outline else 0)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        s = self.s
        self.d.rectangle([x0 * s, y0 * s, x1 * s, y1 * s], fill=fill, outline=outline,
                         width=max(1, round(width * s)) if outline else 0)

    def radial(self, cx, cy, r0, r1, deg, width, fill):
        """Strich von Radius r0 bis r1 in Richtung deg (als Viereck, damit er gerade Enden hat)."""
        self.hand(cx, cy, deg, [(r0, width), (r1, width)], fill)

    def hand(self, cx, cy, deg, profile, fill, outline=None):
        """Zeiger aus einem Profil [(abstand, breite), …] entlang der Richtung deg."""
        a = math.radians(deg)
        dx, dy, px, py = math.sin(a), -math.cos(a), math.cos(a), math.sin(a)
        left = [((cx + r * dx + w / 2 * px) * self.s, (cy + r * dy + w / 2 * py) * self.s) for r, w in profile]
        right = [((cx + r * dx - w / 2 * px) * self.s, (cy + r * dy - w / 2 * py) * self.s) for r, w in reversed(profile)]
        self.d.polygon(left + right, fill=fill, outline=outline)

    def text(self, cx, cy, txt, font, fill):
        """Text mittig um (cx, cy)."""
        self.d.text((cx * self.s, cy * self.s), txt, font=font, fill=fill, anchor="mm")

    def gear(self, cx, cy, r, teeth, deg, fill, dark):
        """Zahnrad mit Speichen; deg = Drehung."""
        pts, pitch, depth = [], 360 / teeth, min(5, max(1.5, r * 0.18))
        for i in range(teeth):
            b = deg + i * pitch
            for rr, off in ((r - depth, 0), (r, 0.18), (r, 0.47), (r - depth, 0.65)):
                pts.append(self.pt(cx, cy, rr, b + off * pitch))
        self.d.polygon(pts, fill=fill, outline=dark)
        if r >= 14:                                 # große Räder: ausgespart mit Speichen
            self.circle(cx, cy, r - 2 * depth, fill=dark)
            for k in range(5):
                self.radial(cx, cy, 0, r - 2 * depth + 1, deg + k * 72, max(3, r / 7), fill)
        self.circle(cx, cy, max(4, r / 4), fill=fill, outline=dark, width=1)
        self.circle(cx, cy, max(1.5, r / 12), fill=dark)



# Registry: Zifferblatt-ID → Zeichenfunktion(self, profile); Bilder je Sekunde
CLOCK_RENDERERS = {}
CLOCK_FPS = {}


def clock_face(face_id, fps=1):
    """Methode als Zeichenfunktion des Zifferblatts face_id anmelden."""
    def deco(fn):
        CLOCK_RENDERERS[face_id] = fn
        CLOCK_FPS[face_id] = fps
        return fn
    return deco


def clock_options(settings, face):
    """Optionen eines Zifferblatts: Standardwerte aus CLOCK_OPTIONS, ergänzt um settings.json."""
    out = {o["key"]: o["default"] for o in CLOCK_OPTIONS.get(face, [])}
    user = ((settings or {}).get("clock") or {}).get(face)
    if isinstance(user, dict):
        out.update({k: v for k, v in user.items() if k in out})
    return out


def clock_fps(face, settings):
    """Wie oft das Zifferblatt je Sekunde neu gezeichnet werden soll."""
    fps = CLOCK_FPS.get(face, 1)
    return fps(clock_options(settings, face)) if callable(fps) else fps


def mix(a, b, t):
    """Farbe zwischen a (t=0) und b (t=1)."""
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class ClockBase:
    """Hilfen für alle Zifferblätter (Schriften, Zwischenspeicher, Zeit, Optionen, Farben)."""

    def _clock_fonts(self):
        if not hasattr(self, "_cfonts"):
            s = CLOCK_SS
            self._cfonts = {"tiny": load_font(8 * s), "small": load_font(10 * s, bold=True),
                            "mid": load_font(13 * s, bold=True), "big": load_font(24 * s, bold=True),
                            "side": load_font(15 * s, bold=True), "roman": load_serif(13 * s, bold=True),
                            "serif_s": load_serif(9 * s, bold=True), "led": load_font(20 * s, bold=True)}
            self._cdials = {}
        return self._cfonts

    def _clock_canvas(self, key, bg, build):
        """Zwischengespeichertes Zifferblatt kopieren (build zeichnet es beim ersten Mal)."""
        self._clock_fonts()
        if key not in self._cdials and len(self._cdials) >= 8:
            self._cdials.clear()                  # z. B. nach vielen Farbwechseln: Speicher begrenzen
        if key not in self._cdials:
            c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), bg))
            build(c)
            self._cdials[key] = c.img
        return _Canvas(self._cdials[key].copy())

    # Zwischenspeicher der Zifferblatt-Module (je ~2–3 MB pro Eintrag); Schriften bleiben erhalten
    CLOCK_CACHES = ("_cdials", "_clock_slots")

    def _clock_cache(self, slot, key, build):
        """Zwischenspeicher für Unveränderliches (Hintergründe, Masken, vorberechnete Bilder):
        je slot nur der jüngste key – ändert sich z. B. eine Farbe, wird neu gebaut statt angesammelt."""
        slots = self.__dict__.setdefault("_clock_slots", {})
        hit = slots.get(slot)
        if hit is None or hit[0] != key:
            hit = slots[slot] = (key, build())
        return hit[1]

    def _clock_drop_caches(self):
        """Beim Wechsel des Zifferblatts die Zwischenspeicher der anderen Zifferblätter freigeben."""
        for name in self.CLOCK_CACHES:
            cache = self.__dict__.get(name)
            if isinstance(cache, dict):
                cache.clear()

    def _clock_finish(self, c):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        img.paste(c.img.reduce(CLOCK_SS), (0, 0))     # Mittelwert je 3×3 – 15× schneller als LANCZOS
        return img

    @staticmethod
    def _clock_angles(now):
        sec = now.tm_sec
        minute = now.tm_min + sec / 60
        hour = (now.tm_hour % 12) + minute / 60
        return hour * 30, minute * 6, sec * 6

    def _clock_now(self):
        """Aktuelle Zeit als Zeitstempel. Tests setzen fixed_time für feste Bilder."""
        fixed = getattr(self, "fixed_time", None)
        return fixed if fixed is not None else time.time()

    def _copt(self, face):
        return clock_options(self.settings, face)

    def _ccolor(self, value, profile, default=None):
        """Farbe aus einer Option: gesetzt → diese, sonst default bzw. die Farbe der Ebene."""
        if value:
            return tuple(value)
        return tuple(default) if default else PROFILE_COLOR.get(profile, self.FG)


@page_keys("clock")
def keys_clock(app, pressed):
    """MENU öffnet die Auswahl des Zifferblatts; sonst blättern die Pfeiltasten."""
    if pressed & LKEY_BITS["MENU"]:
        app.menu = ClockMenu(app)
        app.flash = None
        app.next_draw = 0
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_uhr
#   Displayseite „Uhr“: zeigt das Zifferblatt des aktiven Profils und der Ebene (Standard: Digitaluhr).
# ═══════════════════════════════════════════════════════════════════════════

class ClockPage:
    @page("clock")
    def page_clock(self, profile, macros):
        face = getattr(self, "clock_face", "digital")
        if face != getattr(self, "_clock_last", None):
            self._clock_drop_caches()                 # anderes Zifferblatt: Speicher freigeben
            self._clock_last = face
        fn = CLOCK_RENDERERS.get(face) or CLOCK_RENDERERS["digital"]
        return fn(self, profile)

    @clock_face("digital")
    def face_digital(self, profile):
        """Große Uhrzeit, Sekunden, Wochentag, Datum."""
        opt = self._copt("digital")
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        now = time.localtime(self._clock_now())
        dy = (0 if opt["seconds"] else 14) + (0 if opt["date"] else 48)
        self._center(d, 28 + dy, time.strftime("%H:%M", now), self.f_huge, self._ccolor(opt["color"], profile, self.FG))
        if opt["seconds"]:
            self._center(d, 122 + dy, f":{now.tm_sec:02d}", self.f_mid, self.DIM)
        if opt["date"]:
            y = 152 if opt["seconds"] else 136
            self._center(d, y, WEEKDAYS[now.tm_wday], self.f_big, PROFILE_COLOR.get(profile, self.FG))
            self._center(d, y + 32, f"{now.tm_mday}. {MONTHS[now.tm_mon - 1]} {now.tm_year}", self.f_mid, self.FG)
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul uhr_standard
#   Zifferblätter Chronometer, Steampunk-Uhr, Bahnhofsuhr und Binäruhr.
# ═══════════════════════════════════════════════════════════════════════════

class StandardFaces:
    # --- Chronometer ---------------------------------------------------------- #
    CHRONO_DIALS = {   # Zifferblatt, Hilfszifferblätter, Indizes, Schrift hell/dunkel, Viertelsekunden, Zeiger
        "black": ((18, 20, 24), (30, 32, 37), (210, 214, 222), (225, 228, 235), (170, 175, 185), (95, 100, 110), (220, 224, 232)),
        "blue": ((16, 30, 66), (24, 40, 80), (214, 218, 226), (230, 234, 242), (160, 176, 205), (80, 96, 130), (222, 226, 234)),
        "green": ((16, 46, 32), (24, 58, 42), (214, 218, 222), (230, 236, 232), (160, 190, 170), (80, 110, 92), (222, 226, 230)),
        "silver": ((204, 208, 214), (184, 188, 196), (60, 64, 72), (34, 38, 46), (80, 84, 92), (150, 154, 160), (54, 58, 66)),
    }

    def _chrono_dial(self, c, dial):
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        face, sub, idx, txt, txt2, quarter, _hand = self.CHRONO_DIALS[dial]
        steel, steel_hi, steel_lo = (92, 97, 106), (190, 196, 205), (40, 43, 50)
        c.circle(cx, cy, 102, fill=steel_lo)
        c.circle(cx, cy, 100.5, fill=steel)
        c.circle(cx, cy, 100.5, outline=steel_hi, width=1)
        c.circle(cx, cy, 87, fill=(24, 26, 30))
        c.circle(cx, cy, 87, outline=steel_lo, width=1.5)
        for m in range(5, 61, 5):                          # Skala auf der Lünette
            c.text(*[v / CLOCK_SS for v in c.pt(cx, cy, 94, m * 6)], f"{m:02d}" if m < 60 else "60",
                   f["tiny"], (235, 238, 245))
        c.circle(cx, cy, 87, fill=face)
        for q in range(240):                              # Viertelsekunden
            c.radial(cx, cy, 83.5, 86, q * 1.5, 0.35, quarter)
        for m in range(60):
            if m % 5:
                c.radial(cx, cy, 81, 86, m * 6, 0.9, idx)
        for h in range(12):
            if h in (3, 6, 9):
                continue
            deg = h * 30
            if h == 0:
                for off in (-3.2, 3.2):
                    c.hand(cx, cy, deg + off, [(62, 4.2), (80, 4.2)], idx, outline=(90, 94, 102))
            else:
                c.hand(cx, cy, deg, [(62, 5.5), (80, 5.5)], idx, outline=(90, 94, 102))
                c.radial(cx, cy, 65, 77, deg, 2, (230, 240, 210))        # Leuchtmasse
        c.text(cx, cy - 44, "G19s", f["mid"], txt)
        c.text(cx, cy - 32, "CHRONOMETER", f["tiny"], txt2)
        # Hilfszifferblätter: links 24 Stunden, rechts kleine Sekunde
        for sx, labels, ticks in ((cx - 44, [("24", 0), ("6", 90), ("12", 180), ("18", 270)], 24),
                                  (cx + 44, [("60", 0), ("15", 90), ("30", 180), ("45", 270)], 60)):
            c.circle(sx, cy, 23, fill=sub)
            c.circle(sx, cy, 23, outline=(150, 155, 165), width=1)
            for k in range(ticks):
                long_tick = k % (ticks // 12 if ticks == 24 else 5) == 0
                c.radial(sx, cy, 19.5 if long_tick else 21, 23, k * 360 / ticks, 0.8 if long_tick else 0.5,
                         txt2)
            for label, deg in labels:
                x, y = c.pt(sx, cy, 13.5, deg)
                c.text(x / CLOCK_SS, y / CLOCK_SS, label, f["tiny"], txt)
        c.rect(cx - 20, cy + 52, cx + 20, cy + 68, fill=(245, 245, 240), outline=(120, 124, 132), width=1)
        c.radial(cx, cy + 53, 0, -14, 0, 0.8, (170, 172, 176))     # Trennlinie Tag | Datum

    @clock_face("chrono")
    def face_chrono(self, profile):
        opt = self._copt("chrono")
        dial = opt["dial"] if opt["dial"] in self.CHRONO_DIALS else "black"
        c = self._clock_canvas(("chrono", dial), (10, 11, 14), lambda c: self._chrono_dial(c, dial))
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        now = time.localtime(self._clock_now())
        acc = self._ccolor(opt["hand"], profile)
        if opt["side"] in ("both", "date"):               # links Datum
            c.text(31, 90, f"{now.tm_mday}", f["big"], (225, 228, 235))
            c.text(31, 114, MONTH_3[now.tm_mon - 1], f["small"], (150, 156, 170))
            c.text(31, 130, str(now.tm_year), f["tiny"], (110, 116, 130))
        if opt["side"] == "both":                         # rechts Kalenderwoche und Digitalzeit
            c.text(289, 90, time.strftime("%V", now), f["big"], (225, 228, 235))
            c.text(289, 114, "KW", f["small"], (150, 156, 170))
            c.text(289, 130, time.strftime("%H:%M", now), f["tiny"], (110, 116, 130))
        c.text(cx - 10, cy + 60.5, WEEKDAY_2[now.tm_wday], f["small"], (20, 20, 24))
        c.text(cx + 10, cy + 60.5, str(now.tm_mday), f["small"], (180, 30, 30) if now.tm_wday == 6 else (20, 20, 24))
        silver, dark = self.CHRONO_DIALS[dial][6], (60, 64, 72)
        h24 = (now.tm_hour + now.tm_min / 60) * 15
        c.hand(cx - 44, cy, h24, [(-4, 2.2), (17, 1.4), (19, 0)], silver)
        c.circle(cx - 44, cy, 2.2, fill=silver)
        c.hand(cx + 44, cy, now.tm_sec * 6, [(-5, 1.6), (0, 1.2), (19, 0.6)], silver)
        c.circle(cx + 44, cy, 2.2, fill=silver)
        ha, ma, sa = self._clock_angles(now)
        c.hand(cx, cy, ha, [(-10, 4), (0, 7.5), (38, 6.5), (52, 0)], silver, outline=dark)
        c.hand(cx, cy, ha, [(8, 2.4), (40, 2)], (230, 240, 210))
        c.hand(cx, cy, ma, [(-12, 3.5), (0, 6), (64, 4.5), (80, 0)], silver, outline=dark)
        c.hand(cx, cy, ma, [(10, 2), (66, 1.6)], (230, 240, 210))
        c.hand(cx, cy, sa, [(-22, 2.4), (0, 1.6), (84, 0.9)], acc)
        c.circle(*[v / CLOCK_SS for v in c.pt(cx, cy, -18, sa)], 3.2, fill=acc)
        c.circle(cx, cy, 4.2, fill=silver, outline=dark, width=0.8)
        c.circle(cx, cy, 1.6, fill=acc)
        return self._clock_finish(c)

    # --- Steampunk ------------------------------------------------------------ #
    _STEAM_GEARS = [                 # (x, y, Radius, Richtung)
        (30, 50, 44, 1), (38, 122, 34, -1), (18, 172, 22, 1),
        (292, 58, 40, -1), (290, 122, 30, 1), (300, 170, 20, -1),
    ]

    def _steam_dial(self, c):
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        brass, brass_hi, brass_lo = (176, 134, 62), (226, 190, 110), (96, 66, 28)
        c.circle(cx, cy, 102, fill=brass_lo)
        c.circle(cx, cy, 100, fill=brass)
        c.circle(cx, cy, 97, outline=brass_hi, width=1)
        c.circle(cx, cy, 89, fill=brass_lo)
        for k in range(16):                               # Nieten
            x, y = [v / CLOCK_SS for v in c.pt(cx, cy, 94, k * 22.5 + 11.25)]
            c.circle(x, y, 2.6, fill=(120, 86, 38))
            c.circle(x - 0.6, y - 0.6, 1.3, fill=brass_hi)
        for r in range(88, 0, -2):                        # vergilbtes Zifferblatt, zum Rand dunkler
            t = max(0.0, (r - 55) / 33)
            col = tuple(int(a + (b - a) * t) for a, b in zip((236, 224, 192), (196, 172, 124)))
            c.circle(cx, cy, r, fill=col)
        ink = (58, 38, 20)
        c.circle(cx, cy, 83, outline=ink, width=1)
        c.circle(cx, cy, 77, outline=ink, width=0.8)
        for m in range(60):
            c.radial(cx, cy, 77, 83, m * 6, 1.6 if m % 5 == 0 else 0.7, ink)
        for h, num in enumerate(ROMAN_XII):
            if h == 6:
                continue                                  # Platz für das Uhrwerk-Fenster
            x, y = [v / CLOCK_SS for v in c.pt(cx, cy, 63, h * 30)]
            c.text(x, y, num, f["roman"], ink)
        c.text(cx, cy - 34, "G19s", f["serif_s"], ink)
        c.text(cx, cy - 25, "MANUFACTUR", f["tiny"], (110, 80, 45))
        c.circle(cx, cy + 40, 19, fill=brass_lo)
        c.circle(cx, cy + 40, 17, fill=(34, 24, 14))

    @clock_face("steampunk")
    def face_steampunk(self, profile):
        c = self._clock_canvas("steam", (26, 17, 9), self._steam_dial)
        cx, cy = CLOCK_CX, CLOCK_CY
        t = self._clock_now()
        now = time.localtime(t)
        tick = int(t) if self._copt("steampunk")["gears"] else 0
        # Zahnräder hinter und im Zifferblatt drehen sich sekündlich weiter
        layer = _Canvas(Image.new("RGB", c.img.size, (26, 17, 9)))
        for x, y, r, direction in self._STEAM_GEARS:
            layer.gear(x, y, r, max(8, round(r / 3.4)), direction * tick * 6 * 40 / r,
                       (122, 82, 38) if r > 30 else (150, 104, 48), (58, 36, 16))
        def build_mask():
            mask = Image.new("L", c.img.size, 0)
            ImageDraw.Draw(mask).ellipse([(cx - 102.5) * CLOCK_SS, (cy - 102.5) * CLOCK_SS,
                                          (cx + 102.5) * CLOCK_SS, (cy + 102.5) * CLOCK_SS], fill=255)
            return mask
        layer.img.paste(c.img, (0, 0), self._clock_cache("std_steam_mask", 1, build_mask))
        c = layer
        c.gear(cx - 6, cy + 42, 11, 10, tick * 30, (196, 150, 70), (90, 60, 25))      # Unruh-Fenster
        c.gear(cx + 9, cy + 34, 7, 8, -tick * 47, (170, 126, 56), (90, 60, 25))
        c.circle(cx, cy + 40, 17, outline=(226, 190, 110), width=1)
        blue, blue_hi = (28, 34, 78), (70, 84, 150)
        ha, ma, sa = self._clock_angles(now)
        for deg, length, ring in ((ha, 50, 7), (ma, 74, 6)):              # Breguet-Zeiger
            rp = length * 0.72
            c.hand(cx, cy, deg, [(-12, 3), (0, 4), (rp - ring, 2.6)], blue)
            x, y = [v / CLOCK_SS for v in c.pt(cx, cy, rp, deg)]
            c.circle(x, y, ring, outline=blue, width=2.2)
            c.hand(cx, cy, deg, [(rp + ring - 1, 2.6), (length - 8, 3.2), (length, 0)], blue)
            c.hand(cx, cy, deg, [(2, 1), (rp - ring - 2, 0.8)], blue_hi)
        c.hand(cx, cy, sa, [(-20, 1.6), (0, 1.4), (80, 0.8)], (150, 40, 20))
        c.circle(*[v / CLOCK_SS for v in c.pt(cx, cy, 64, sa)], 2.2, fill=(150, 40, 20))
        c.circle(cx, cy, 5, fill=(196, 150, 70), outline=(90, 60, 25), width=1)
        c.radial(cx, cy, -3.5, 3.5, 45, 1, (90, 60, 25))                # Schraubenschlitz
        return self._clock_finish(c)

    # --- Bahnhofsuhr ---------------------------------------------------------- #
    def _station_dial(self, c):
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        c.circle(cx, cy, 103, fill=(28, 30, 34))
        c.circle(cx, cy, 101, fill=(70, 74, 80))
        c.circle(cx, cy, 99, fill=(34, 36, 40))
        c.circle(cx, cy, 96, fill=(246, 246, 243))
        black = (18, 18, 20)
        for m in range(60):
            if m % 5:
                c.radial(cx, cy, 85, 92, m * 6, 2.2, black)
            else:
                c.radial(cx, cy, 66, 92, m * 6, 7.5, black)

    @clock_face("station")
    def face_station(self, profile):
        opt = self._copt("station")
        c = self._clock_canvas("station", (10, 12, 16), self._station_dial)
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        now = time.localtime(self._clock_now())
        if opt["side"]:
            c.text(31, 70, WEEKDAY_DE[now.tm_wday], f["side"], (235, 238, 245))
            c.text(31, 90, f"{now.tm_mday:02d}.{now.tm_mon:02d}.", f["small"], (170, 176, 190))
            c.text(31, 118, "KW", f["small"], (130, 138, 155))
            c.text(31, 138, time.strftime("%V", now), f["side"], (235, 238, 245))
            c.text(289, 80, str(now.tm_year), f["small"], (170, 176, 190))
            c.text(289, 100, MONTH_3[now.tm_mon - 1], f["side"], (235, 238, 245))
        black = (18, 18, 20)
        minute = now.tm_min + (now.tm_sec / 60 if opt["smooth"] else 0)   # springend: nur volle Minuten
        ha, ma, sa = ((now.tm_hour % 12) + minute / 60) * 30, minute * 6, now.tm_sec * 6
        c.hand(cx, cy, ha, [(-18, 10), (58, 8)], black)
        c.hand(cx, cy, ma, [(-22, 8), (86, 6)], black)
        red = (200, 28, 28)
        if opt["seconds"]:
            c.hand(cx, cy, sa, [(-26, 2.2), (70, 2.2)], red)
            c.hand(cx, cy, sa, [(-26, 5), (-16, 5)], red)
            c.circle(cx, cy, 3.5, fill=red)
        else:
            c.circle(cx, cy, 3.5, fill=black)
        return self._clock_finish(c)

    # --- Binäruhr ------------------------------------------------------------- #
    def _led(self, c, x, y, r, color, on, off):
        if on:
            c.circle(x, y, r + 3, fill=mix(color, self.BG, 0.75))
            c.circle(x, y, r, fill=color)
            c.circle(x - r * 3 / 13, y - r * 3 / 13, r * 4 / 13, fill=mix(color, (255, 255, 255), 0.4))
        else:
            c.circle(x, y, r, fill=off, outline=tuple(min(255, v + d) for v, d in zip(off, (28, 30, 36))), width=1.2)

    @clock_face("binary")
    def face_binary(self, profile):
        opt = self._copt("binary")
        c = self._clock_canvas("binary", self.BG, lambda c: None)
        f = self._cfonts
        now = time.localtime(self._clock_now())
        cols = [self._ccolor(opt[k], profile) for k in ("color_h", "color_m", "color_s")]
        off = tuple(opt["color_off"]) if opt["color_off"] else (24, 28, 38)
        if opt["mode"] == "binary":                       # je Zeile eine Binärzahl: 32 16 8 4 2 1
            r, step = 12, 34
            x0 = (WIDTH - 5 * step) / 2 + 8
            top = 34 if opt["digits"] else 50
            for i, v in enumerate((32, 16, 8, 4, 2, 1)):
                c.text(x0 + i * step, top - 22, str(v), f["tiny"], self.DIM)
            for row, (label, val, col) in enumerate((("Std", now.tm_hour, cols[0]), ("Min", now.tm_min, cols[1]),
                                                      ("Sek", now.tm_sec, cols[2]))):
                y = top + row * 44
                c.text(x0 - 36, y, label, f["small"], self.DIM)
                for i, v in enumerate((32, 16, 8, 4, 2, 1)):
                    if row == 0 and v == 32:
                        continue                          # Stunden: höchstens 23 → 5 Bit
                    self._led(c, x0 + i * step, y, r, col, val & v, off)
                if opt["digits"]:
                    c.text(x0 + 5 * step + 40, y, f"{val:02d}", f["led"], col)
            return self._clock_finish(c)
        digits = f"{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}"
        bits = [2, 4, 3, 4, 3, 4]                          # Bits je Ziffer (Zehner-Stunden: 0–2 → 2 Bit)
        step, gap, r = 36, 16, 13
        x0 = (WIDTH - (6 * step + 2 * gap)) / 2 + step / 2 + 10
        dy = 0 if opt["digits"] else 16
        rows = [30 + dy, 70 + dy, 110 + dy, 150 + dy]      # 8, 4, 2, 1
        for i, v in enumerate((8, 4, 2, 1)):
            c.text(x0 - 34, rows[i], str(v), f["small"], self.DIM)
        for col, ch in enumerate(digits):
            x = x0 + col * step + (col // 2) * gap
            n = int(ch)
            for i, v in enumerate((8, 4, 2, 1)):
                if 3 - i < bits[col]:
                    self._led(c, x, rows[i], r, cols[col // 2], n & v, off)
            if opt["digits"]:
                c.text(x, 186, ch, f["led"], self.FG)
        if opt["digits"]:
            for g in (1, 2):                               # Doppelpunkte zwischen den Gruppen
                x = x0 + (2 * g - 1) * step + (g - 1) * gap + step / 2 + gap / 2
                c.text(x, 184, ":", f["led"], self.DIM)
        return self._clock_finish(c)


# ═══════════════════════════════════════════════════════════════════════════
# Modul uhr_mechanik
#   Zifferblätter Pendeluhr, Kuckucksuhr, Taschenuhr, Sanduhr, Kerzenuhr.
# ═══════════════════════════════════════════════════════════════════════════

def _mech_bezier(p0, p1, p2, p3, n):
    """Punkte einer kubischen Bézierkurve (Displaykoordinaten)."""
    out = []
    for i in range(n + 1):
        u = i / n
        v = 1 - u
        out.append((v ** 3 * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u ** 3 * p3[0],
                    v ** 3 * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u ** 3 * p3[1]))
    return out


def _mech_wave(t, parts):
    """Deterministisches „Rauschen“ aus Sinuswellen [(Frequenz, Phase, Gewicht), …] → etwa −1…1."""
    return sum(w * math.sin(2 * math.pi * fr * t + ph) for fr, ph, w in parts)


class MechanicalFaces:
    # --- Hilfen --------------------------------------------------------------- #
    @staticmethod
    def _mech_poly(c, pts, fill=None, outline=None, width=1):
        s = CLOCK_SS
        c.d.polygon([(x * s, y * s) for x, y in pts], fill=fill, outline=outline,
                    width=max(1, round(width * s)) if outline else 0)

    @staticmethod
    def _mech_line(c, pts, fill, width=1):
        s = CLOCK_SS
        c.d.line([(x * s, y * s) for x, y in pts], fill=fill, width=max(1, round(width * s)), joint="curve")

    @staticmethod
    def _mech_ellipse(c, x0, y0, x1, y1, fill=None, outline=None, width=1):
        s = CLOCK_SS
        c.d.ellipse([x0 * s, y0 * s, x1 * s, y1 * s], fill=fill, outline=outline,
                    width=max(1, round(width * s)) if outline else 0)

    @staticmethod
    def _mech_at(c, cx, cy, r, deg):
        return [v / CLOCK_SS for v in c.pt(cx, cy, r, deg)]

    @staticmethod
    def _mech_text_rot(c, x, y, txt, font, fill, deg):
        """Text mittig um (x, y), um deg gedreht (Kopf nach außen wie auf alten Zifferblättern)."""
        w = int(font.getlength(txt)) + 8
        h = int(font.size * 1.5) + 8
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text((w / 2, h / 2), txt, font=font, fill=255, anchor="mm")
        m = m.rotate(-deg, resample=Image.BICUBIC, expand=True)
        c.img.paste(fill, (int(x * CLOCK_SS - m.width / 2), int(y * CLOCK_SS - m.height / 2)), m)

    @staticmethod
    def _mech_vgrad(c, x0, y0, x1, y1, top, bottom):
        """Senkrechter Farbverlauf."""
        s = CLOCK_SS
        n = max(1, int((y1 - y0) * s))
        for i in range(n):
            c.d.line([(x0 * s, y0 * s + i), (x1 * s - 1, y0 * s + i)], fill=mix(top, bottom, i / n))

    @staticmethod
    def _mech_hgrad(c, x0, y0, x1, y1, edge, mid, light=0.35):
        """Waagerechter Verlauf wie ein Zylinder (Glanzlicht bei light, 0…1)."""
        s = CLOCK_SS
        n = max(1, int((x1 - x0) * s))
        span = max(light, 1 - light)
        for i in range(n):
            k = math.cos(min(1.0, abs(i / n - light) / span) * math.pi / 2)
            c.d.line([(x0 * s + i, y0 * s), (x0 * s + i, y1 * s - 1)], fill=mix(edge, mid, k))

    @staticmethod
    def _mech_wood(c, x0, y0, x1, y1, base, seed, vertical=True, strength=16):
        """Holzfläche mit Maserung."""
        s = CLOCK_SS
        c.rect(x0, y0, x1, y1, fill=base)
        rnd = random.Random(seed)
        length, across = ((y1 - y0), (x1 - x0)) if vertical else ((x1 - x0), (y1 - y0))
        for _ in range(int(across * 1.4)):
            off, d = rnd.uniform(0, across), rnd.uniform(-strength, strength * 0.6)
            col = tuple(max(0, min(255, int(v + d))) for v in base)
            amp, fr, ph = rnd.uniform(0.2, 1.6), rnd.uniform(0.02, 0.09), rnd.uniform(0, 6.3)
            pts = []
            for i in range(0, int(length) + 3, 3):
                w = min(max(off + amp * math.sin(min(i, length) * fr + ph), 0), across)
                i = min(i, length)
                pts.append(((x0 + w) * s, (y0 + i) * s) if vertical else ((x0 + i) * s, (y0 + w) * s))
            c.d.line(pts, fill=col, width=rnd.choice((1, 1, 2, 3)))

    def _mech_wood_poly(self, c, pts, base, seed, vertical=True, strength=16):
        """Holzfläche in Form eines Vielecks."""
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        tmp = _Canvas(Image.new("RGB", c.img.size, base))
        self._mech_wood(tmp, min(xs), min(ys), max(xs), max(ys), base, seed, vertical, strength)
        mask = Image.new("L", c.img.size, 0)
        ImageDraw.Draw(mask).polygon([(x * CLOCK_SS, y * CLOCK_SS) for x, y in pts], fill=255)
        c.img.paste(tmp.img, (0, 0), mask)

    def _mech_radial_fill(self, c, cx, cy, r, inner, outer, start=0.0, step=1.5):
        """Kreisfläche mit Verlauf von innen nach außen (ab start·r)."""
        rr = r
        while rr > 0:
            k = max(0.0, (rr / r - start) / (1 - start)) if start < 1 else 1
            c.circle(cx, cy, rr, fill=mix(inner, outer, k))
            rr -= step

    def _mech_metal_ring(self, c, cx, cy, r0, r1, light, dark, fill_inner=None, light_deg=315):
        """Metallring zwischen r0 und r1 mit Licht von light_deg (0 = oben)."""
        s = CLOCK_SS
        box = [(cx - r1) * s, (cy - r1) * s, (cx + r1) * s, (cy + r1) * s]
        for a in range(0, 360, 4):
            k = (math.cos(math.radians(a + 2 - light_deg)) + 1) / 2
            c.d.pieslice(box, a - 90, a - 90 + 5, fill=mix(dark, light, k ** 1.3))
        if fill_inner is not None:
            c.circle(cx, cy, r0, fill=fill_inner)

    def _mech_side_date(self, c, now, col, dim):
        """Dezentes Datum links und rechts neben einem schmalen Gehäuse."""
        f = self._cfonts
        date_f = clock_font("sans", 11 * CLOCK_SS, True)
        c.text(50, 88, WEEKDAYS[now.tm_wday], date_f, dim)
        c.text(50, 114, str(now.tm_mday), f["big"], col)
        c.text(270, 100, MONTHS[now.tm_mon - 1], date_f, dim)
        c.text(270, 118, str(now.tm_year), f["tiny"], dim)

    # --- Pendeluhr ------------------------------------------------------------ #
    _MECH_PEND = (CLOCK_CX, 84, 96, 9.5)         # Aufhängung x, y, Pendellänge, Ausschlag (Grad)
    _MECH_PEND_WIN = (124, 142, 196, 194)        # Glasfenster

    def _mech_pendulum_static(self, c):
        f = self._cfonts
        cx, cy = CLOCK_CX, 84
        self._mech_vgrad(c, 0, 0, WIDTH, CLOCK_H, (30, 23, 20), (12, 10, 10))
        walnut, dark, light = (104, 58, 30), (52, 28, 14), (150, 96, 54)
        brass, brass_hi, brass_lo = (190, 146, 66), (240, 204, 124), (110, 76, 30)
        c.rect(110, 36, 220, 204, fill=(8, 6, 6))                          # Schatten an der Wand
        self._mech_wood(c, 106, 32, 214, 200, walnut, 1)
        # Kranz mit Giebel, Rosette und Knäufen
        self._mech_wood_poly(c, [(98, 30), (cx, 7), (222, 30)], (120, 70, 36), 2, vertical=False)
        self._mech_line(c, [(98, 30), (cx, 7), (222, 30)], light, 1.2)
        self._mech_poly(c, [(114, 27), (cx, 12), (206, 27)], fill=(84, 46, 22))
        self._mech_line(c, [(114, 27), (cx, 12), (206, 27), (114, 27)], dark, 0.8)
        for x in (138, 182):                                               # geschnitzte Ranken im Giebel
            d = -1 if x < cx else 1
            self._mech_line(c, _mech_bezier((cx + d * 6, 22), (x, 14), (x - d * 12, 30), (x + d * 10, 24), 12),
                            (150, 100, 58), 1.3)
        c.circle(cx, 20.5, 4.2, fill=brass_lo)
        c.circle(cx, 20.5, 3.4, fill=brass)
        c.circle(cx - 0.8, 19.7, 1.3, fill=brass_hi)
        for x, y, r in ((100, 26, 3.2), (220, 26, 3.2), (cx, 5, 3)):
            c.rect(x - 1.5, y, x + 1.5, y + 4, fill=dark)
            c.circle(x, y, r, fill=light, outline=dark, width=0.6)
        c.rect(94, 30, 226, 35, fill=light)
        c.rect(94, 34, 226, 36, fill=dark)
        c.rect(100, 36, 220, 38, fill=(76, 42, 20))
        # Zifferblattfeld mit Messingzwickeln
        c.rect(110, 40, 210, 130, outline=dark, width=0.8)
        for sx, sy in ((113, 43), (207, 43), (113, 127), (207, 127)):
            dx, dy = (1 if sx < cx else -1), (1 if sy < 84 else -1)
            for k, (ox, oy) in enumerate(((0, 0), (7, 1.5), (1.5, 7))):
                c.circle(sx + dx * ox, sy + dy * oy, 3.2 if k == 0 else 2.2, fill=brass_lo)
                c.circle(sx + dx * ox - 0.4, sy + dy * oy - 0.4, 2.3 if k == 0 else 1.5, fill=brass)
        self._mech_metal_ring(c, cx, cy, 45, 49, brass_hi, brass_lo)
        c.circle(cx, cy, 49, outline=(70, 46, 18), width=0.8)
        c.circle(cx, cy, 45.5, fill=brass_lo)
        self._mech_radial_fill(c, cx, cy, 45, (246, 238, 218), (222, 208, 176), start=0.55)
        ink = (40, 30, 26)
        c.circle(cx, cy, 42, outline=ink, width=0.7)
        c.circle(cx, cy, 38.5, outline=ink, width=0.6)
        for m in range(60):
            c.radial(cx, cy, 38.5, 42, m * 6, 1.4 if m % 5 == 0 else 0.5, ink)
        roman = clock_font("serif-cond", 9 * CLOCK_SS, True)
        for h, num in enumerate(ROMAN_XII):
            x, y = self._mech_at(c, cx, cy, 32.5, h * 30)
            self._mech_text_rot(c, x, y, num, roman, ink, h * 30)
        c.text(cx, cy - 15, "G19s", f["serif_s"], (110, 80, 50))
        # Gesims zwischen Zifferblatt und Fenster
        c.rect(104, 132, 216, 137, fill=light)
        c.rect(104, 136, 216, 137.6, fill=dark)
        # Fenster mit Säulen
        x0, y0, x1, y1 = self._MECH_PEND_WIN
        c.rect(x0 - 5, y0 - 4, x1 + 5, y1 + 4, fill=dark)
        c.rect(x0 - 3, y0 - 2, x1 + 3, y1 + 2, fill=(132, 84, 44))
        self._mech_vgrad(c, x0, y0, x1, y1, (60, 36, 20), (34, 20, 12))
        for k in range(1, 6):                                              # Rückwand-Bretter
            c.rect(x0 + k * 12, y0, x0 + k * 12 + 0.5, y1, fill=(44, 26, 14))
        c.rect(x0, y1 - 8, x1, y1 - 7.6, fill=(80, 56, 30))               # Abfallskala
        for k in range(-6, 7):
            c.radial(cx + k * 3.2, y1 - 7.6, 0, -2.5 if k % 3 else -4, 0, 0.5, (190, 150, 80))
        for px in (108, 204):
            self._mech_hgrad(c, px, 140, px + 8, 196, (70, 38, 18), (170, 112, 62))
            for yy in (140, 146, 190):
                self._mech_hgrad(c, px - 1, yy, px + 9, yy + 4, (60, 32, 14), (186, 128, 74))
        # Sockel mit Abhängling
        c.rect(98, 198, 222, 204, fill=light)
        c.rect(98, 203, 222, 204.5, fill=dark)
        self._mech_poly(c, [(110, 204), (210, 204), (196, 209), (124, 209)], fill=walnut, outline=dark, width=0.6)
        self._mech_poly(c, [(150, 209), (170, 209), (cx, 214)], fill=light)

    @staticmethod
    def _mech_glass_mask(w, h, stripes):
        """Maske für einen Glasreflex (schräge Streifen [(x, Breite, Deckkraft), …])."""
        s = CLOCK_SS
        m = Image.new("L", (int(w * s), int(h * s)), 0)
        d = ImageDraw.Draw(m)
        for x, width, alpha in stripes:
            d.polygon([(x * s, 0), ((x + width) * s, 0), ((x + width - h * 0.45) * s, h * s),
                       ((x - h * 0.45) * s, h * s)], fill=alpha)
        return m

    @clock_face("pendulum", fps=lambda o: 5 if o["swing"] else 1)
    def face_pendulum(self, profile):
        opt = self._copt("pendulum")
        c = self._clock_canvas("mech_pendulum", (12, 10, 10), self._mech_pendulum_static)
        t = self._clock_now()
        now = time.localtime(t)
        px, py, length, amp = self._MECH_PEND
        x0, y0, x1, y1 = self._MECH_PEND_WIN
        # Halbschwingung je Sekunde: an vollen Sekunden im Umkehrpunkt
        if opt["swing"]:
            deg = amp * math.cos(math.pi * (t % 2))
        else:
            deg = amp if int(t) % 2 == 0 else -amp
        a = math.radians(deg)
        bx, by = px + length * math.sin(a), py + length * math.cos(a)
        top_x = px + (y0 - py) * math.tan(a)
        brass, brass_hi, brass_lo = (196, 152, 70), (246, 214, 140), (118, 82, 32)
        self._mech_line(c, [(top_x, y0), (bx, by)], brass_lo, 2.6)
        self._mech_line(c, [(top_x, y0), (bx, by)], brass, 1.4)
        c.circle(bx + 1, by + 1.5, 11.5, fill=(26, 15, 8))                 # Schatten auf der Rückwand
        c.circle(bx, by, 11, fill=brass_lo)
        c.circle(bx - 0.6, by - 0.6, 10, fill=brass)
        c.circle(bx - 2.2, by - 2.2, 6, fill=mix(brass, brass_hi, 0.55))
        c.circle(bx - 3.4, by - 3.4, 2.6, fill=brass_hi)
        c.circle(bx, by, 11, outline=(90, 60, 24), width=0.6)
        c.hand(bx, by, 0, [(-11, 2.2), (-14, 2.2)], brass_lo)            # Regulierschraube
        mask = self._clock_cache("mech_pend_glass", None, lambda: self._mech_glass_mask(
            x1 - x0, y1 - y0, ((16, 7, 34), (27, 2.5, 22), (58, 12, 16))))
        c.img.paste((255, 244, 226), (x0 * CLOCK_SS, y0 * CLOCK_SS), mask)
        # Zeiger (geschwärzt, mit Ring)
        cx, cy = CLOCK_CX, 84
        ha, ma, _ = self._clock_angles(now)
        ink, dial = (26, 22, 24), (238, 228, 204)
        c.hand(cx, cy, ha, [(-8, 3.2), (0, 3.4), (14, 2), (17, 5.5), (23, 1.6), (26, 0)], ink)
        x, y = self._mech_at(c, cx, cy, 11, ha)
        c.circle(x, y, 3.4, fill=ink)
        c.circle(x, y, 1.6, fill=dial)
        c.hand(cx, cy, ma, [(-10, 2.6), (0, 2.8), (24, 1.4), (28, 3.8), (31, 1.1), (37, 0)], ink)
        x, y = self._mech_at(c, cx, cy, 16, ma)
        c.circle(x, y, 2.8, fill=ink)
        c.circle(x, y, 1.3, fill=dial)
        c.circle(cx, cy, 3, fill=ink)
        c.circle(cx, cy, 1.2, fill=brass)
        self._mech_side_date(c, now, (214, 184, 140), (150, 124, 96))
        return self._clock_finish(c)

    # --- Kuckucksuhr ---------------------------------------------------------- #
    _MECH_CU = {"dial": (CLOCK_CX, 105, 38), "door": (151, 42, 169, 62), "pend": (CLOCK_CX, 152, 46),
                "chains": (132, 188), "bottom": 150}

    def _mech_leaf(self, c, x, y, deg, length, width, fill, vein):
        """Geschnitztes Blatt ab (x, y) in Richtung deg."""
        c.hand(x, y, deg, [(0, 0.8), (length * 0.25, width * 0.8), (length * 0.55, width),
                           (length * 0.85, width * 0.5), (length, 0)], fill, outline=vein)
        c.hand(x, y, deg, [(0, 0.6), (length * 0.85, 0.4)], vein)

    def _mech_cone_sprite(self):
        """Tannenzapfen-Gewicht als Bild mit Maske (dreifach vergrößert)."""
        s, w, h = CLOCK_SS, 18, 34
        img = Image.new("RGB", (w * s, h * s), (0, 0, 0))
        mask = Image.new("L", (w * s, h * s), 0)
        cc, md = _Canvas(img), ImageDraw.Draw(mask)
        body = [(9 + 7 * math.sin(math.pi * min(1, (y - 4) / 26) ** 0.7) * (1 if side else -1), y)
                for side in (0, 1) for y in (range(4, 33) if side else range(32, 3, -1))]
        md.polygon([(x * s, y * s) for x, y in body], fill=255)
        md.ellipse([6 * s, 0, 12 * s, 6 * s], fill=255)
        cc.circle(9, 3, 2.6, outline=(150, 150, 150), width=1)                  # Haken
        self._mech_poly(cc, body, fill=(70, 40, 18))
        for row in range(9):                                                    # Schuppen
            y = 7 + row * 3
            wdt = 7 * math.sin(math.pi * min(1, (y - 4) / 26) ** 0.7)
            n = max(2, int(wdt / 2.2))
            for k in range(n + 1):
                x = 9 - wdt + 1 + k * (2 * wdt - 2) / max(1, n) + (1 if row % 2 else 0)
                if abs(x - 9) < wdt - 0.5:
                    self._mech_ellipse(cc, x - 2, y - 1.2, x + 2, y + 2.2, fill=(122, 76, 38),
                                       outline=(58, 32, 14), width=0.5)
                    self._mech_ellipse(cc, x - 1, y - 0.6, x + 0.5, y + 0.6, fill=(150, 100, 56))
        return img, mask

    def _mech_cuckoo_static(self, c):
        cx, cy, r = self._MECH_CU["dial"]
        self._mech_vgrad(c, 0, 0, WIDTH, CLOCK_H, (30, 42, 34), (14, 20, 16))
        rnd = random.Random(7)
        for yy in range(8, CLOCK_H, 22):                                            # Tapetenmuster
            for xx in range(8 + (11 if (yy // 22) % 2 else 0), WIDTH, 22):
                c.hand(xx, yy, 0, [(-3, 0), (0, 3), (3, 0)], (36, 50, 40))
        wood, wood_d, wood_l = (118, 72, 38), (58, 32, 14), (160, 108, 60)
        bottom = self._MECH_CU["bottom"]
        # Vorderseite (Giebelfläche)
        front = [(108, bottom), (108, 72), (cx, 34), (212, 72), (212, bottom)]
        self._mech_poly(c, [(x + 3, y + 3) for x, y in front], fill=(10, 14, 10))
        self._mech_wood_poly(c, front, wood, 11)
        self._mech_line(c, front, wood_d, 0.8)
        # Dach mit Schindeln
        outer_l, outer_r, apex_o, apex_i = (82, 78), (238, 78), (cx, 16), (cx, 32)
        inner_l, inner_r = (98, 82), (222, 82)
        roof = [outer_l, apex_o, outer_r, inner_r, apex_i, inner_l]
        self._mech_poly(c, [(x + 3, y + 3) for x, y in roof], fill=(10, 14, 10))
        tmp = _Canvas(Image.new("RGB", c.img.size, (60, 34, 16)))
        for side in (-1, 1):
            ex, ey = (outer_l if side < 0 else outer_r)
            ln = math.hypot(ex - cx, ey - 16)
            dx, dy = (ex - cx) / ln, (ey - 16) / ln
            nx, ny = 0, 1
            for row in range(5):
                for k in range(-1, int(ln / 5.5) + 2):
                    off = k * 5.5 + (2.75 if row % 2 else 0)
                    x = cx + dx * off + nx * (row * 3.8 + 1)
                    y = 16 + dy * off + ny * (row * 3.8 + 1)
                    shade = rnd.randint(-10, 10)
                    col = (96 + shade, 58 + shade // 2, 30 + shade // 3)
                    self._mech_ellipse(tmp, x - 3.2, y - 1, x + 3.2, y + 5, fill=col, outline=(46, 24, 10), width=0.5)
        mask = Image.new("L", c.img.size, 0)
        ImageDraw.Draw(mask).polygon([(x * CLOCK_SS, y * CLOCK_SS) for x, y in roof], fill=255)
        c.img.paste(tmp.img, (0, 0), mask)
        self._mech_line(c, [outer_l, apex_o, outer_r], wood_l, 1.6)
        self._mech_line(c, [inner_l, apex_i, inner_r], wood_d, 1)
        for side in (-1, 1):                                                        # Zierleiste unter dem Dach
            ex, ey = inner_l if side < 0 else inner_r
            for k in range(1, 12):
                u = k / 12
                x, y = cx + (ex - cx) * u, 32 + (ey - 32) * u
                c.circle(x, y + 1.6, 1.6, fill=wood_l, outline=wood_d, width=0.4)
        # Schnitzwerk: Blätter auf dem First, an den Seiten und unten
        leaf, vein = (136, 88, 44), (60, 34, 14)
        for deg, ln in ((-60, 11), (-25, 13), (0, 12), (25, 13), (60, 11)):
            self._mech_leaf(c, cx, 17, deg, ln, 5, leaf, vein)
        c.circle(cx, 16, 2.6, fill=(170, 116, 64), outline=vein, width=0.5)
        for side in (-1, 1):
            bx = cx + side * 50
            for deg, ln, yy in ((side * 20, 14, 136), (side * 60, 13, 142), (side * 100, 12, 147),
                                (side * 150, 12, 124), (side * -170, 10, 110)):
                self._mech_leaf(c, bx, yy, deg, ln, 5, leaf, vein)
            self._mech_leaf(c, cx + side * 42, 72, side * 60, 11, 4.5, leaf, vein)
            self._mech_leaf(c, cx + side * 42, 74, side * 110, 10, 4, leaf, vein)
        for k in range(9):                                                          # Schürze
            x = 116 + k * 11
            self._mech_leaf(c, x, bottom - 3, 180 + (k - 4) * 6, 10, 5, leaf, vein)
        c.rect(106, bottom - 4, 214, bottom, fill=wood_l, outline=wood_d, width=0.6)
        # Tür (geschlossen)
        d0, d1, d2, d3 = self._MECH_CU["door"]
        self._mech_ellipse(c, d0 - 2.5, d1 - 2.5, d2 + 2.5, d1 + (d2 - d0) + 1, fill=wood_d)
        c.rect(d0 - 2.5, d1 + 7, d2 + 2.5, d3 + 2, fill=wood_d)
        self._mech_ellipse(c, d0, d1, d2, d1 + (d2 - d0), fill=(132, 84, 44))
        c.rect(d0, d1 + 8, d2, d3, fill=(132, 84, 44))
        c.rect(cx - 0.4, d1 + 1, cx + 0.4, d3, fill=wood_d)
        c.circle(163, (d1 + d3) / 2 + 2, 1, fill=(200, 170, 100))
        # Zifferblatt: dunkles Holz mit Beinziffern
        bone = (234, 222, 192)
        c.circle(cx + 2, cy + 2, r + 3, fill=(40, 22, 10))
        for k in range(24):                                                         # geschnitzter Kranz
            x, y = self._mech_at(c, cx, cy, r + 0.5, k * 15)
            c.circle(x, y, 3, fill=wood_l if k % 2 else (140, 90, 48), outline=wood_d, width=0.4)
        c.circle(cx, cy, r - 2, fill=(64, 36, 16))
        self._mech_radial_fill(c, cx, cy, r - 3, (92, 56, 28), (70, 40, 18), start=0.3)
        for m in range(60):
            if m % 5:
                x, y = self._mech_at(c, cx, cy, r - 5.5, m * 6)
                c.circle(x, y, 0.5, fill=bone)
        roman = clock_font("serif-cond", 8 * CLOCK_SS, True)
        for h, num in enumerate(ROMAN_XII):
            x, y = self._mech_at(c, cx, cy, r - 12, h * 30)
            self._mech_text_rot(c, x, y, num, roman, bone, h * 30)
            x, y = self._mech_at(c, cx, cy, r - 5.5, h * 30)
            c.circle(x, y, 1.1, fill=bone)
        # Aufhängung der Ketten
        for x in self._MECH_CU["chains"]:
            c.rect(x - 3, bottom, x + 3, bottom + 2, fill=wood_d)

    def _mech_chain_v(self, c, x, y0, y1, col):
        """Senkrechte Kette von y0 bis y1."""
        y, k = y0, 0
        while y < y1:
            if k % 2:
                c.rect(x - 0.5, y, x + 0.5, y + 3.2, fill=col)
            else:
                self._mech_ellipse(c, x - 1.4, y, x + 1.4, y + 3.4, outline=col, width=0.6)
            y += 2.6
            k += 1

    @clock_face("cuckoo", fps=5)
    def face_cuckoo(self, profile):
        c = self._clock_canvas("mech_cuckoo", (14, 20, 16), self._mech_cuckoo_static)
        f = self._cfonts
        date_f = clock_font("sans", 11 * CLOCK_SS, True)
        t = self._clock_now()
        now = time.localtime(t)
        cx, cy, r = self._MECH_CU["dial"]
        bottom = self._MECH_CU["bottom"]
        wood_d, bone = (58, 32, 14), (234, 222, 192)
        # Gewichte sinken im Lauf des Tages, die freien Kettenenden steigen
        day = (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) / 86400
        steel, steel_d = (170, 170, 164), (90, 90, 86)
        cone, mask = self._clock_cache("mech_cone", None, self._mech_cone_sprite)
        for k, x in enumerate(self._MECH_CU["chains"]):
            frac = min(1.0, day + (0.04 if k else 0))
            top = bottom + 10 + 28 * frac
            free_end = bottom + 10 + 28 * (1 - frac)
            fx = x + (-7 if k == 0 else 7)
            self._mech_chain_v(c, fx, bottom + 1, free_end, steel_d)
            c.circle(fx, free_end + 2.2, 2.2, outline=steel, width=0.8)
            self._mech_chain_v(c, x, bottom + 1, top + 1, steel)
            c.img.paste(cone, (int((x - 9) * CLOCK_SS), int(top * CLOCK_SS)), mask)
        # Pendel (Periode 1 s)
        px, py, length = self._MECH_CU["pend"]
        a = math.radians(9 * math.sin(2 * math.pi * (t % 1)))
        bx, by = px + length * math.sin(a), py + length * math.cos(a)
        rod0 = (px + 6 * math.sin(a), py + 6 * math.cos(a))
        self._mech_line(c, [rod0, (bx, by)], (40, 22, 10), 1.8)
        leaf, vein = (136, 88, 44), (60, 34, 14)
        deg = 180 - math.degrees(a)
        for off, ln in ((-40, 10), (0, 13), (40, 10)):
            self._mech_leaf(c, bx, by - 3, deg + off, ln, 5.5, leaf, vein)
        c.circle(bx, by - 3, 2.6, fill=(170, 116, 64), outline=vein, width=0.5)
        # Tür offen: zur vollen Stunde 30 s, zur halben Stunde 10 s
        is_open = (now.tm_min == 0 and now.tm_sec < 30) or (now.tm_min == 30 and now.tm_sec < 10)
        if is_open:
            d0, d1, d2, d3 = self._MECH_CU["door"]
            self._mech_ellipse(c, d0, d1, d2, d1 + (d2 - d0), fill=(22, 12, 6))
            c.rect(d0, d1 + 8, d2, d3, fill=(22, 12, 6))
            self._mech_poly(c, [(d0, d1 + 6), (d0 - 6, d1 + 3), (d0 - 6, d3 + 2), (d0, d3)],
                            fill=(150, 98, 52), outline=wood_d, width=0.5)          # aufgeklappte Tür
            # Vogel auf der Stange, schaut nach links heraus
            self._mech_line(c, [(d0 + 2, d3 - 1), (d0 - 10, d3 - 1)], (150, 110, 60), 1.2)
            bird, bird_d = (120, 84, 50), (70, 46, 24)
            self._mech_poly(c, [(166, 50), (174, 46), (172, 52)], fill=bird_d)       # Schwanz
            self._mech_ellipse(c, 148, 48, 168, 60, fill=bird)
            self._mech_ellipse(c, 154, 50, 166, 57, fill=bird_d)                     # Flügel
            c.circle(149, 48, 5.2, fill=bird)
            self._mech_ellipse(c, 144, 50, 152, 57, fill=(214, 190, 150))            # Brust
            beak_open = int(t * 2) % 2 == 0
            self._mech_poly(c, [(144.5, 46), (138, 47 if beak_open else 48), (144.5, 48.5)], fill=(236, 180, 40))
            if beak_open:
                self._mech_poly(c, [(144.5, 49), (139, 50.5), (144.5, 50)], fill=(236, 180, 40))
            c.circle(147.5, 46.5, 1.3, fill=(250, 250, 250))
            c.circle(147.2, 46.5, 0.7, fill=(10, 10, 10))
            c.text(262, 40, "Kuckuck!", f["side"], (236, 214, 160))
        # Zeiger (bein, verziert)
        ha, ma, _ = self._clock_angles(now)
        out = (60, 38, 18)
        c.hand(cx, cy, ha, [(-7, 3.2), (0, 3.6), (9, 2), (13, 6.6), (17, 2), (19.5, 4.4), (23, 0)], bone, outline=out)
        c.hand(cx, cy, ma, [(-9, 2.8), (0, 3.2), (21, 1.6), (25, 4.8), (28, 1.4), (34, 0)], bone, outline=out)
        c.circle(cx, cy, 3.2, fill=bone, outline=out, width=0.5)
        c.circle(cx, cy, 1.2, fill=out)
        # dezent: Datum links, Uhrzeit rechts
        c.text(44, 96, WEEKDAYS[now.tm_wday], date_f, (170, 180, 160))
        c.text(44, 118, f"{now.tm_mday}. {MONTH_3[now.tm_mon - 1].title()}", date_f, (130, 142, 124))
        c.text(276, 106, time.strftime("%H:%M", now), f["side"], (170, 180, 160))
        return self._clock_finish(c)

    # --- Taschenuhr ----------------------------------------------------------- #
    _MECH_PO = (150, 132, 78)                    # Mittelpunkt und Radius des Gehäuses

    def _mech_pocket_static(self, c):
        cx, cy, R = self._MECH_PO
        f = self._cfonts
        gold, gold_hi, gold_lo = (212, 168, 78), (252, 226, 150), (112, 78, 24)
        for rr in range(260, 0, -4):                                                # Samt mit Lichtkegel
            k = min(1.0, rr / 230)
            c.circle(cx + 10, cy - 10, rr, fill=mix((70, 20, 30), (16, 5, 8), k ** 0.8))
        # Kette hängt links herab (Glieder abwechselnd flach und hochkant)
        pts = _mech_bezier((140, 18), (92, -8), (14, 36), (30, 150), 400)
        dist, last, k = 0.0, pts[0], 0
        for p in pts[1:]:
            dist += math.hypot(p[0] - last[0], p[1] - last[1])
            last = p
            if dist >= 4.6:
                dist, i = 0.0, pts.index(p)
                q = pts[min(len(pts) - 1, i + 3)]
                deg = math.degrees(math.atan2(q[0] - p[0], -(q[1] - p[1])))
                ln, wd = 3.4, (2.1 if k % 2 == 0 else 0.8)
                c.circle(p[0] + 1.5, p[1] + 2, 2.4, fill=mix((40, 12, 16), (16, 5, 8), 0.5))
                if k % 2 == 0:
                    c.hand(p[0], p[1], deg, [(-ln, 0.6), (-ln * 0.6, wd * 2), (ln * 0.6, wd * 2), (ln, 0.6)], gold_lo)
                    c.hand(p[0], p[1], deg, [(-ln * 0.7, 0.4), (-ln * 0.4, 1.4), (ln * 0.4, 1.4), (ln * 0.7, 0.4)],
                           (70, 22, 30))
                    c.hand(p[0] - 0.4, p[1] - 0.4, deg, [(-ln * 0.3, 0.6), (ln * 0.3, 0.6)], gold_hi)
                else:
                    c.hand(p[0], p[1], deg, [(-ln, 1.6), (ln, 1.6)], gold)
                k += 1
        c.circle(30, 153, 3.4, outline=gold, width=1.2)                             # Ring und Knebel
        c.hand(30, 159, 90, [(-13, 2.2), (-11, 3.4), (11, 3.4), (13, 2.2)], gold_lo)
        c.hand(30, 158.6, 90, [(-12, 1.2), (12, 1.2)], gold_hi)
        c.circle(30, 159, 2.4, fill=gold, outline=gold_lo, width=0.5)
        # Bügel, Krone, Pendant
        c.circle(cx + 4, 25, 15, outline=(20, 6, 10), width=3.6)
        c.circle(cx, 22, 14, outline=gold_lo, width=3.8)
        c.circle(cx, 22, 13.6, outline=gold, width=2.4)
        self._mech_ellipse(c, cx - 13.5, 12, cx - 11, 20, fill=gold_hi)
        self._mech_hgrad(c, cx - 8, 32, cx + 8, 45, gold_lo, gold_hi, 0.4)
        for k in range(9):
            x = cx - 7 + k * 1.75
            c.rect(x, 32, x + 0.5, 45, fill=gold_lo)
        c.rect(cx - 8.5, 31, cx + 8.5, 33, fill=gold)
        self._mech_poly(c, [(cx - 6, 45), (cx + 6, 45), (cx + 9, cy - R + 2), (cx - 9, cy - R + 2)], fill=gold)
        self._mech_hgrad(c, cx - 5, 45, cx + 5, cy - R + 2, gold_lo, gold_hi, 0.4)
        # Gehäuse, Lünette, Emaille-Zifferblatt
        c.circle(cx + 4, cy + 5, R + 1, fill=(16, 4, 8))
        c.circle(cx, cy, R, fill=gold_lo)
        self._mech_metal_ring(c, cx, cy, R - 9, R - 0.8, gold_hi, (150, 108, 40))
        c.circle(cx, cy, R - 5, outline=gold_lo, width=0.6)
        c.circle(cx, cy, R - 9, fill=gold_lo)
        self._mech_radial_fill(c, cx, cy, R - 10, (252, 251, 247), (228, 224, 214), start=0.7, step=1)
        ink = (18, 18, 22)
        c.circle(cx, cy, R - 13, outline=ink, width=0.7)
        c.circle(cx, cy, R - 17, outline=ink, width=0.6)
        for m in range(60):
            c.radial(cx, cy, R - 17, R - 13, m * 6, 0.6 if m % 5 else 1.8, ink)
        arab = clock_font("serif", 13 * CLOCK_SS, True)
        for h in range(1, 13):
            if h == 6:
                continue
            x, y = self._mech_at(c, cx, cy, R - 27, h * 30)
            c.text(x, y + 0.5, str(h), arab, ink)
        c.text(cx, cy - 26, "G19s", f["serif_s"], (60, 60, 70))
        sy, sr = cy + 29, 14
        sx = cx
        c.circle(sx, sy, sr + 0.8, fill=(214, 210, 200))
        c.circle(sx, sy, sr, fill=(244, 242, 236))
        for m in range(60):
            c.radial(sx, sy, sr - (3 if m % 5 == 0 else 1.6), sr, m * 6, 0.9 if m % 5 == 0 else 0.4, ink)

    def _mech_pocket_glass(self):
        """Maske des Glasreflexes: Kreis ohne versetzten Kreis – eine Sichel oben links."""
        s, r = CLOCK_SS, self._MECH_PO[2] - 10
        mask = Image.new("L", (int(2 * r * s), int(2 * r * s)), 0)
        d = ImageDraw.Draw(mask)
        d.ellipse([0, 0, 2 * r * s, 2 * r * s], fill=34)
        d.ellipse([10 * s, 12 * s, (2 * r + 18) * s, (2 * r + 22) * s], fill=0)
        return mask

    @clock_face("pocket")
    def face_pocket(self, profile):
        c = self._clock_canvas("mech_pocket", (16, 5, 8), self._mech_pocket_static)
        f = self._cfonts
        date_f = clock_font("sans", 11 * CLOCK_SS, True)
        cx, cy, R = self._MECH_PO
        now = time.localtime(self._clock_now())
        ha, ma, sa = self._clock_angles(now)
        blue, blue_hi = (26, 40, 112), (74, 100, 180)
        # Spaten-Stundenzeiger, schlanker Minutenzeiger, kleine Sekunde bei der 6
        c.hand(cx, cy, ha, [(-9, 3.6), (0, 3.4), (24, 2), (27, 3), (32, 8), (38, 5.6), (42, 1.4), (45, 0)], blue)
        c.hand(cx, cy, ha, [(2, 0.8), (22, 0.7)], blue_hi)
        c.hand(cx, cy, ma, [(-12, 3.2), (0, 3.2), (10, 2.2), (60, 0.8), (64, 0)], blue)
        c.hand(cx, cy, ma, [(2, 0.7), (40, 0.5)], blue_hi)
        x, y = self._mech_at(c, cx, cy, -10, ma)
        c.circle(x, y, 3, fill=blue)
        c.circle(cx, cy, 4, fill=blue)
        c.circle(cx, cy, 1.6, fill=(212, 168, 78))
        sy = cy + 29
        c.hand(cx, sy, sa, [(-4, 1.2), (0, 1), (12, 0.4)], blue)
        c.circle(cx, sy, 1.6, fill=blue)
        mask = self._clock_cache("mech_pocket_glass", None, self._mech_pocket_glass)   # Glasreflex oben links
        c.img.paste((255, 255, 255), (int((cx - R + 10) * CLOCK_SS), int((cy - R + 10) * CLOCK_SS)), mask)
        gold, dim = (226, 190, 118), (168, 128, 90)
        c.text(282, 88, WEEKDAYS[now.tm_wday], date_f, dim)
        c.text(282, 114, str(now.tm_mday), f["big"], gold)
        c.text(282, 140, MONTHS[now.tm_mon - 1], date_f, dim)
        c.text(282, 156, str(now.tm_year), f["tiny"], dim)
        return self._clock_finish(c)

    # --- Sanduhr -------------------------------------------------------------- #
    _MECH_HG = (100, 24, 190, 44, 2.2)            # Mitte x, Glas oben, Glas unten, halbe Breite, Engstelle

    def _mech_hg_w(self, y):
        """Halbe Glasbreite in Höhe y."""
        cx, top, bot, wmax, neck = self._MECH_HG
        mid, half = (top + bot) / 2, (bot - top) / 2
        s = min(1.0, abs(y - mid) / half)
        return neck + (wmax - neck) * math.sin(0.62 * math.pi * s) / 1.0

    def _mech_hg_tables(self):
        """Je Kolben (oben, unten): [(Sandmenge bis y, y), …] in Schritten von 0,25 ab Engstelle bzw. Boden."""
        cx, top, bot, wmax, neck = self._MECH_HG
        mid = (top + bot) / 2
        tabs = []
        for ys in ((mid - k * 0.25 for k in range(int((mid - top) * 4) + 1)),
                   (bot - k * 0.25 for k in range(int((bot - mid) * 4) + 1))):
            acc, tab = 0.0, []
            for y in ys:
                acc += 2 * self._mech_hg_w(y) * 0.25
                tab.append((acc, y))
            tabs.append(tab)
        return tabs

    def _mech_hg_level(self, amount, upper):
        """Sandhöhe für amount (0…1 der Füllung) im oberen bzw. unteren Kolben."""
        tab = self._clock_cache("mech_hg_tab", None, self._mech_hg_tables)[0 if upper else 1]
        target = amount * tab[-1][0] * 0.78
        for acc, y in tab:
            if acc >= target:
                return y
        return tab[-1][1]

    def _mech_turned_post(self, c, x, y0, y1, wood, dark, light):
        """Gedrechselte Säule (Profil aus Wülsten)."""
        s = CLOCK_SS
        n = int((y1 - y0) * s)
        for i in range(n):
            u = i / n
            r = 2.6 + 3 * sum(math.exp(-((u - m) / 0.03) ** 2) for m in (0.04, 0.5, 0.96)) \
                + 1.5 * sum(math.exp(-((u - m) / 0.09) ** 2) for m in (0.26, 0.74))
            y = y0 * s + i
            c.d.line([((x - r) * s, y), ((x + r) * s, y)], fill=wood)
            c.d.line([((x - r) * s, y), ((x - r * 0.45) * s, y)], fill=mix(wood, dark, 0.5))
            c.d.line([((x + r * 0.55) * s, y), ((x + r) * s, y)], fill=mix(wood, dark, 0.7))
            c.d.line([((x - r * 0.2) * s, y), ((x + r * 0.05) * s, y)], fill=light)

    def _mech_hourglass_static(self, c):
        cx, top, bot, wmax, neck = self._MECH_HG
        self._mech_vgrad(c, 0, 0, WIDTH, 198, (26, 22, 24), (14, 12, 14))
        self._mech_vgrad(c, 0, 198, WIDTH, CLOCK_H, (58, 38, 24), (34, 22, 14))    # Tischplatte
        c.rect(0, 198, WIDTH, 198.6, fill=(84, 58, 36))
        wood, dark, light = (150, 98, 52), (70, 40, 18), (206, 150, 90)
        self._mech_ellipse(c, cx - 76, 201, cx + 76, 211, fill=(22, 14, 10))       # Schatten
        # Glas (hinter den Säulen)
        left = [(cx - self._mech_hg_w(y), y) for y in range(top, bot + 1)]
        right = [(cx + self._mech_hg_w(y), y) for y in range(bot, top - 1, -1)]
        self._mech_poly(c, left + right, fill=(34, 38, 48))
        self._mech_line(c, left, (120, 136, 156), 0.9)
        self._mech_line(c, right, (120, 136, 156), 0.9)
        for px in (cx - 62, cx + 62):
            self._mech_turned_post(c, px, 18, 196, wood, dark, light)
        for y0 in (6, 190):                                                         # Platten oben und unten
            c.rect(cx - 72, y0 + 2, cx + 72, y0 + 10, fill=dark)
            self._mech_vgrad(c, cx - 71, y0 + 2.5, cx + 71, y0 + 9.5, light, wood)
            c.rect(cx - 66, y0, cx + 66, y0 + 2.5, fill=wood)
            c.rect(cx - 66, y0 + 9.5, cx + 66, y0 + 12, fill=wood)
            c.rect(cx - 72, y0 + 5.8, cx + 72, y0 + 6.3, fill=(110, 70, 36))

    @clock_face("hourglass", fps=5)
    def face_hourglass(self, profile):
        c = self._clock_canvas("mech_hourglass", (14, 12, 14), self._mech_hourglass_static)
        f = self._cfonts
        date_f = clock_font("sans", 11 * CLOCK_SS, True)
        t = self._clock_now()
        now = time.localtime(t)
        cx, top, bot, wmax, neck = self._MECH_HG
        mid = (top + bot) / 2
        into = now.tm_min * 60 + now.tm_sec + (t % 1)
        rest = max(0.0, 1 - into / 3600)
        sand, sand_d, sand_l = (224, 186, 120), (176, 136, 80), (244, 216, 160)
        # oben: verbleibender Sand mit Trichter in der Mitte
        yl = self._mech_hg_level(rest, True)
        if rest > 0.002:
            wl = self._mech_hg_w(yl)
            dip = min(7.0, (mid - yl) * 0.35)
            pts = [(cx - self._mech_hg_w(y) + 0.8, y) for y in _mech_frange(mid, yl, -1)]
            surf = [(cx + x, yl + dip * (1 - (x / wl) ** 2) ** 1.5) for x in _mech_frange(-wl + 0.8, wl - 0.8, 1)]
            pts += surf + [(cx + self._mech_hg_w(y) - 0.8, y) for y in _mech_frange(yl, mid, 1)]
            self._mech_poly(c, pts, fill=sand)
            self._mech_line(c, surf, sand_l, 0.8)
        # unten: Sandhügel wächst
        done = 1 - rest
        yb = self._mech_hg_level(done, False)
        m = min(14.0, 3 + 40 * done) if done > 0.001 else 1.5
        wb = self._mech_hg_w(yb) - 0.8
        pile = [(cx + x, yb - m * (1 - (x / wb) ** 2) ** 1.6) for x in _mech_frange(-wb, wb, 1)]
        pts = [(cx - self._mech_hg_w(y) + 0.8, y) for y in _mech_frange(bot - 0.5, yb, -1)] + pile
        pts += [(cx + self._mech_hg_w(y) - 0.8, y) for y in _mech_frange(yb, bot - 0.5, 1)]
        self._mech_poly(c, pts, fill=sand)
        self._mech_line(c, pile, sand_l, 0.8)
        self._mech_line(c, [(cx - wb * 0.2, yb - m * 0.9), (cx - wb * 0.55, yb - m * 0.4)], sand_d, 0.6)
        # rieselnder Strahl mit wandernden Körnchen
        peak = yb - m
        if rest > 0.002 and peak > mid + 2:
            length = peak - mid
            self._mech_line(c, [(cx, mid), (cx, peak)], sand_d, 0.5)
            rnd = random.Random(3)
            for k in range(14):
                y = mid + ((t * 70 + k * length / 14) % length)
                x = cx + rnd.uniform(-0.9, 0.9) * (0.3 + (y - mid) / length)
                c.circle(x, y, 0.6, fill=sand_l)
            rnd = random.Random(int(t * 5))                                         # Spritzer am Hügel
            for _ in range(3):
                c.circle(cx + rnd.uniform(-4, 4), peak + rnd.uniform(-2.5, 0.5), 0.5, fill=sand_l)
        # Glanzlichter auf dem Glas
        glare = (170, 190, 210)
        for y0, y1 in ((top + 6, mid - 22), (mid + 22, bot - 6)):
            self._mech_line(c, [(cx - self._mech_hg_w(y) + 3.5, y) for y in _mech_frange(y0, y1, 2)], glare, 0.9)
        c.rect(cx - 4, top - 3, cx + 4, top + 1, fill=(84, 54, 28))
        c.rect(cx - 4, bot - 1, cx + 4, bot + 3, fill=(84, 54, 28))
        # daneben: Uhrzeit und verbleibende Zeit
        tx = 246
        acc = PROFILE_COLOR.get(profile, self.FG)
        c.text(tx, 74, time.strftime("%H:%M:%S", now), clock_font("mono", 20 * CLOCK_SS, True),
               (238, 222, 190))
        left_s = 3600 - now.tm_min * 60 - now.tm_sec
        txt = f"noch {left_s} Sek." if left_s < 60 else f"noch {math.ceil(left_s / 60)} Min."
        c.text(tx, 102, txt, f["mid"], (214, 186, 130))
        c.text(tx, 118, f"bis {(now.tm_hour + 1) % 24:02d}:00 Uhr", f["tiny"], (150, 136, 116))
        c.rect(tx - 50, 132, tx + 50, 135, fill=(44, 40, 40))
        c.rect(tx - 50, 132, tx - 50 + 100 * rest, 135, fill=acc)
        c.text(tx, 158, f"{WEEKDAY_DE[now.tm_wday]}, {now.tm_mday:02d}.{now.tm_mon:02d}.{now.tm_year}",
               date_f, (150, 136, 116))
        return self._clock_finish(c)

    # --- Kerzenuhr ------------------------------------------------------------ #
    _MECH_CA = (100, 36, 178, 16)                 # Mitte x, Docht bei 0 Uhr, Fuß, halbe Kerzenbreite

    def _mech_candle_wall(self):
        """Dunkle Wand mit Tisch ohne Kerze (füllt die ganze Fläche; dort, wo die Kerze abgebrannt ist)."""
        c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), (10, 8, 8)))
        for rr in range(300, 0, -4):
            c.circle(self._MECH_CA[0], 120, rr, fill=mix((34, 24, 18), (10, 8, 8), min(1.0, rr / 260)))
        self._mech_vgrad(c, 0, 198, WIDTH, CLOCK_H, (54, 34, 20), (28, 18, 10))
        c.rect(0, 198, WIDTH, 198.6, fill=(80, 54, 32))
        return c.img

    def _mech_candle_static(self, c):
        cx, top, base, hw = self._MECH_CA
        c.img.paste(self._clock_cache("mech_candle_bg", None, self._mech_candle_wall))
        # Kerze in voller Länge mit Stundenmarken
        wax_e, wax_m = (200, 170, 126), (250, 238, 212)
        self._mech_hgrad(c, cx - hw, top, cx + hw, base + 2, wax_e, wax_m, 0.35)
        paint = (158, 38, 30)
        step = (base - top) / 24
        label = clock_font("sans", 9 * CLOCK_SS, True)
        for h in range(1, 24):
            y = top + h * step
            if h % 3 == 0:
                c.rect(cx - hw, y - 0.35, cx - hw + 9, y + 0.35, fill=paint)
                c.rect(cx + hw - 5, y - 0.35, cx + hw, y + 0.35, fill=paint)
                c.text(cx + 1.5, y, str(h), label, paint)
            else:
                c.rect(cx - hw, y - 0.25, cx - hw + 4.5, y + 0.25, fill=mix(paint, wax_m, 0.35))
        # Halter aus Messing (Teller, Tülle, Griffring)
        brass, brass_hi, brass_lo = (190, 146, 66), (246, 212, 140), (100, 68, 26)
        self._mech_ellipse(c, cx - 58, 196, cx + 62, 208, fill=(18, 12, 8))
        c.circle(cx + 58, 190, 7.5, outline=brass_lo, width=3.2)
        c.circle(cx + 58, 190, 7.5, outline=brass, width=1.8)
        self._mech_ellipse(c, cx - 56, 186, cx + 56, 204, fill=brass_lo)
        self._mech_ellipse(c, cx - 56, 185, cx + 56, 201, fill=brass)
        self._mech_ellipse(c, cx - 48, 187, cx + 48, 199, fill=mix(brass, brass_lo, 0.35))
        self._mech_ellipse(c, cx - 40, 188, cx + 30, 196, fill=mix(brass, brass_hi, 0.25))
        self._mech_hgrad(c, cx - hw - 3, base, cx + hw + 3, 193, brass_lo, brass_hi, 0.35)
        self._mech_ellipse(c, cx - hw - 3, 190, cx + hw + 3, 196, fill=mix(brass, brass_lo, 0.3))
        self._mech_hgrad(c, cx - hw - 3, base, cx + hw + 3, 192, brass_lo, brass_hi, 0.35)
        self._mech_ellipse(c, cx - hw - 5, base - 3, cx + hw + 5, base + 3, fill=brass_hi, outline=brass_lo, width=0.6)
        c.rect(cx - hw, base - 2, cx + hw, base, fill=wax_e)

    @staticmethod
    def _mech_glow_mask(r):
        """Maske für den Lichtschein der Flamme (Radius r, zur Mitte hin heller)."""
        s = CLOCK_SS
        m = Image.new("L", (2 * r * s, 2 * r * s), 0)
        d = ImageDraw.Draw(m)
        for k in range(r * s, 0, -3):
            d.ellipse([r * s - k, r * s - k, r * s + k, r * s + k], fill=int(120 * (1 - k / (r * s)) ** 2.2))
        return m

    @clock_face("candle", fps=5)
    def face_candle(self, profile):
        c = self._clock_canvas("mech_candle", (10, 8, 8), self._mech_candle_static)
        f = self._cfonts
        t = self._clock_now()
        now = time.localtime(t)
        cx, top, base, hw = self._MECH_CA
        s = CLOCK_SS
        day = (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) / 86400
        yt = top + (base - top) * day
        # abgebrannter Teil: Wand wieder herstellen
        bg = self._clock_cache("mech_candle_bg", None, self._mech_candle_wall)
        box = (int((cx - hw - 3) * s), 0, int((cx + hw + 3) * s), int(yt * s) + 1)
        c.img.paste(bg.crop(box), box[:2])
        # Flackern (deterministisch aus der Zeit)
        n1 = _mech_wave(t, ((1.3, 0.0, 0.5), (2.9, 1.0, 0.3), (5.3, 2.0, 0.2)))
        n2 = _mech_wave(t, ((0.7, 0.5, 0.5), (1.9, 2.2, 0.3), (4.1, 0.3, 0.2)))
        fh, sway = 17 + 3.5 * n1, 1.8 * n2
        fy = yt - 3                                       # Fuß der Flamme
        r = 70
        glow = self._clock_cache("mech_glow", r, lambda: self._mech_glow_mask(r))
        gx, gy = cx + sway * 0.6, fy - 8
        c.img.paste((255, 170 + int(12 * n1), 80), (int((gx - r) * s), int((gy - r) * s)), glow)
        # Kerzenkopf mit Wachsmulde und Tropfen
        wax, wax_d = (248, 236, 210), (214, 190, 150)
        if yt < base - 1:
            rnd = random.Random(11)
            for _ in range(5):
                side = rnd.choice((-1, 1))
                x = cx + side * (hw - rnd.uniform(0, 3))
                ln = rnd.uniform(5, 16) * min(1.0, (base - yt) / 20)
                self._mech_line(c, [(x, yt), (x, yt + ln)], wax_d, 3)
                self._mech_line(c, [(x - 0.4, yt), (x - 0.4, yt + ln)], wax, 2)
                c.circle(x, yt + ln, 1.7, fill=wax)
            self._mech_ellipse(c, cx - hw - 0.5, yt - 3, cx + hw + 0.5, yt + 3, fill=wax_d)
            self._mech_ellipse(c, cx - hw + 2, yt - 2, cx + hw - 2, yt + 2, fill=(255, 244, 210))
        pool = 4 + 10 * day                                # Wachs sammelt sich an der Tülle
        self._mech_ellipse(c, cx - hw - 4, base - 2.5, cx - hw - 4 + pool, base + 3, fill=wax)
        # Docht und Flamme
        self._mech_line(c, [(cx, yt), (cx, fy - 4), (cx + sway * 0.3 + 1, fy - 6)], (40, 30, 24), 1.2)
        for scale, col in ((1.0, (255, 150, 40)), (0.72, (255, 206, 96)), (0.42, (255, 248, 220))):
            w = 4.6 * scale
            hh = fh * (0.55 + 0.45 * scale)
            b = fy - (1 - scale) * 2
            tp = (cx + sway * (0.6 + 0.4 * scale), b - hh)
            side_l = _mech_bezier((cx - w, b - w), (cx - w, b - w - hh * 0.35), (tp[0] - w * 0.2, tp[1] + hh * 0.3), tp, 10)
            side_r = _mech_bezier(tp, (tp[0] + w * 0.2, tp[1] + hh * 0.3), (cx + w, b - w - hh * 0.35), (cx + w, b - w), 10)
            arc = [(cx + w * math.cos(math.radians(a)), b - w + w * math.sin(math.radians(a))) for a in range(0, 181, 15)]
            self._mech_poly(c, side_l + side_r + arc, fill=col)
        self._mech_ellipse(c, cx - 2.2, fy - 4, cx + 2.2, fy + 0.5, fill=(80, 110, 220))  # blauer Flammenfuß
        c.circle(cx, fy - 4, 1, fill=(60, 40, 30))
        # daneben: Uhrzeit, Datum, Rest des Tages
        tx = 238
        c.text(tx, 78, time.strftime("%H:%M:%S", now), clock_font("mono", 20 * CLOCK_SS, True),
               (248, 222, 172))
        c.text(tx, 104, f"{WEEKDAY_DE[now.tm_wday]}, {now.tm_mday}. {MONTHS[now.tm_mon - 1]}", f["small"],
               (200, 166, 120))
        left = 86400 - int(day * 86400)
        mins = math.ceil(left / 60)
        txt = f"noch {left} Sek." if left < 60 else (f"noch {mins} Min." if mins < 60 else
                                                     f"noch {mins // 60} Std. {mins % 60} Min.")
        c.text(tx, 124, txt, f["tiny"], (150, 124, 96))
        return self._clock_finish(c)


def _mech_frange(a, b, step):
    """Gleitkomma-Bereich von a bis b (einschließlich b) mit Schritt ±step."""
    step = abs(step) if b >= a else -abs(step)
    out, x = [], a
    while (x < b) if step > 0 else (x > b):
        out.append(x)
        x += step
    out.append(b)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Modul uhr_himmel
#   Zifferblätter Astro-Uhr, Sonnenuhr, Planetenuhr, Weltzeituhr, Radaruhr.
# ═══════════════════════════════════════════════════════════════════════════

_sky_SYNODIC = 29.530588853                   # synodischer Monat in Tagen
_sky_NEW_MOON = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc).timestamp()
_sky_BERLIN = (52.52, 13.405, "Berlin")
_sky_ZODIAC = [("♈", "Widder"), ("♉", "Stier"), ("♊", "Zwillinge"), ("♋", "Krebs"),
               ("♌", "Löwe"), ("♍", "Jungfrau"), ("♎", "Waage"), ("♏", "Skorpion"),
               ("♐", "Schütze"), ("♑", "Steinbock"), ("♒", "Wassermann"), ("♓", "Fische")]
_sky_PHASES = [                               # (bis Mondalter in Tagen, Name in Zeilen)
    (1.0, ("Neumond",)), (6.38, ("Zunehmende", "Sichel")), (8.38, ("Erstes", "Viertel")),
    (13.77, ("Zunehmender", "Mond")), (15.77, ("Vollmond",)), (21.15, ("Abnehmender", "Mond")),
    (23.15, ("Letztes", "Viertel")), (28.53, ("Abnehmende", "Sichel")), (99, ("Neumond",)),
]


def _sky_fonts():
    """Schriften der Himmels-Zifferblätter nach Rolle (clock_font hält sie im Zwischenspeicher)."""
    s = CLOCK_SS
    return {
        "cond": clock_font("sans-cond", 9 * s, True), "cond_s": clock_font("sans-cond", 8 * s),
        "val": clock_font("sans-cond", 14 * s, True), "glyph": clock_font("sans", 10 * s),
        "glyph_b": clock_font("sans", 11 * s, True), "num": clock_font("serif", 8 * s, True),
        "motto": clock_font("serif", 12 * s, True), "roman": clock_font("serif", 9 * s, True),
        "mono": clock_font("mono", 10 * s, True), "mono_s": clock_font("mono", 8 * s, True),
        "city": clock_font("sans-cond", 11 * s, True), "city_b": clock_font("sans-cond", 16 * s, True),
        "q": clock_font("sans", 20 * s, True),
        "r_val": clock_font("mono", 13, True),              # Radar: ohne Vergrößerung (Displaypixel)
    }


def _sky_sun(ts):
    """Sonnenstand nach NOAA: (Deklination in rad, Zeitgleichung in min, scheinbare ekliptikale Länge in °)."""
    jc = (ts / 86400 + 2440587.5 - 2451545) / 36525
    l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    m = math.radians(357.52911 + jc * (35999.05029 - 0.0001537 * jc))
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    center = (math.sin(m) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + math.sin(2 * m) * (0.019993 - 0.000101 * jc)
              + math.sin(3 * m) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * jc)
    lam = l0 + center - 0.00569 - 0.00478 * math.sin(omega)
    eps0 = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.asin(math.sin(eps) * math.sin(math.radians(lam)))
    y = math.tan(eps / 2) ** 2
    l0r = math.radians(l0)
    eot = 4 * math.degrees(y * math.sin(2 * l0r) - 2 * e * math.sin(m) + 4 * e * y * math.sin(m) * math.cos(2 * l0r)
                           - 0.5 * y * y * math.sin(4 * l0r) - 1.25 * e * e * math.sin(2 * m))
    return decl, eot, lam % 360


def _sky_solar_time(ts, lon):
    """Wahre Ortszeit (Sonnenzeit) in Minuten seit Mitternacht."""
    return ((ts % 86400) / 60 + _sky_sun(ts)[1] + 4 * lon) % 1440


def _sky_sun_dir(ts, lat, lon):
    """(Höhe in °, Richtung Ost, Richtung Nord) der Sonne; die Richtung ist ein Vektor der Länge cos(Höhe)."""
    decl, eot, _ = _sky_sun(ts)
    ha = math.radians(((ts % 86400) / 60 + eot + 4 * lon) / 4 - 180)
    phi = math.radians(lat)
    alt = math.asin(max(-1.0, min(1.0, math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(ha))))
    east = -math.cos(decl) * math.sin(ha)
    north = math.cos(phi) * math.sin(decl) - math.sin(phi) * math.cos(decl) * math.cos(ha)
    return math.degrees(alt), east, north


def _sky_events(day0, lat, lon, zenith=90.833):
    """Sonnenauf- und -untergang (UTC-Zeitstempel) am Tag, der um day0 (00:00 UTC) beginnt.
    Polartag → ("day", None), Polarnacht → ("night", None)."""
    phi = math.radians(lat)
    out = []
    for sign in (1, -1):                      # Aufgang, Untergang
        ts = day0 + (720 - 4 * lon) * 60
        for _ in range(3):                    # mit Deklination zum Ereigniszeitpunkt verfeinern
            decl, eot, _ = _sky_sun(ts)
            cos_h = (math.cos(math.radians(zenith)) / (math.cos(phi) * math.cos(decl) or 1e-9)
                     - math.tan(phi) * math.tan(decl))
            if cos_h > 1:
                return "night", None
            if cos_h < -1:
                return "day", None
            ha = math.degrees(math.acos(cos_h))
            ts = day0 + (720 - 4 * (lon + sign * ha) - eot) * 60
        out.append(ts)
    return out[0], out[1]


def _sky_day0(t):
    """00:00 UTC des lokalen Kalendertags von t."""
    lt = time.localtime(t)
    return datetime.datetime(lt.tm_year, lt.tm_mon, lt.tm_mday, tzinfo=datetime.timezone.utc).timestamp()


def _sky_moon(t):
    """(Mondalter in Tagen, Anteil am synodischen Monat 0…1, beleuchteter Anteil 0…1)."""
    age = ((t - _sky_NEW_MOON) / 86400) % _sky_SYNODIC
    frac = age / _sky_SYNODIC
    return age, frac, (1 - math.cos(2 * math.pi * frac)) / 2


def _sky_phase_name(age):
    for limit, name in _sky_PHASES:
        if age < limit:
            return name
    return ("Neumond",)


def _sky_moon_poly(cx, cy, r, frac, south=False, steps=40):
    """Umriss des beleuchteten Teils der Mondscheibe (Nordhalbkugel: zunehmend rechts hell)."""
    k = math.cos(2 * math.pi * frac)
    right, left = [], []
    for i in range(steps + 1):
        y = -r + 2 * r * i / steps
        w = math.sqrt(max(0.0, r * r - y * y))
        xl, xr = (w * k, w) if frac < 0.5 else (-w, -w * k)
        if south:
            xl, xr = -xr, -xl
        right.append((cx + xr, cy + y))
        left.append((cx + xl, cy + y))
    return right + left[::-1]


def _sky_hhmm(ts):
    lt = time.localtime(ts)
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}"


def _sky_grad(stops, v):
    """Farbe aus Farbstopps [(wert, farbe), …] (aufsteigend) für den Wert v."""
    if v <= stops[0][0]:
        return stops[0][1]
    for (v0, c0), (v1, c1) in zip(stops, stops[1:]):
        if v <= v1:
            return mix(c0, c1, (v - v0) / (v1 - v0))
    return stops[-1][1]


# Himmelsfarbe nach Sonnenhöhe (Nacht → astronomische, nautische, bürgerliche Dämmerung → Tag)
_sky_SKY_STOPS = [(-18, (8, 10, 28)), (-12, (18, 24, 62)), (-6, (44, 50, 112)), (-2.5, (150, 96, 120)),
                  (-0.8, (226, 140, 84)), (0.5, (120, 168, 218)), (15, (70, 138, 214)), (50, (44, 112, 206))]


class SkyFaces:
    # --- gemeinsame Hilfen ---------------------------------------------------- #
    def _sky_place(self):
        """(Breite, Länge, Name) aus den Wetter-Einstellungen, sonst Berlin."""
        w = self.settings.get("weather") if isinstance(self.settings, dict) else None
        try:
            lat, lon = float(w["lat"]), float(w["lon"])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, str(w.get("name") or "")
        except (TypeError, KeyError, ValueError):
            pass
        return _sky_BERLIN

    @staticmethod
    def _sky_fit(c, txt, fonts, maxw):
        """Erste Schrift aus fonts, in der txt höchstens maxw Displaypixel breit ist."""
        for f in fonts:
            if c.d.textlength(txt, font=f) <= maxw * CLOCK_SS:
                return f
        return fonts[-1]

    @staticmethod
    def _sky_trunc(c, txt, font, maxw):
        """txt, nötigenfalls mit „…“ gekürzt, sodass es höchstens maxw Displaypixel breit ist."""
        if c.d.textlength(txt, font=font) <= maxw * CLOCK_SS:
            return txt
        while txt and c.d.textlength(txt + "…", font=font) > maxw * CLOCK_SS:
            txt = txt[:-1]
        return txt.rstrip() + "…"

    def _sky_label(self, c, x, y, label, value, lab_col, val_col, maxw=56):
        f = _sky_fonts()
        c.text(x, y, label, self._sky_fit(c, label, [f["cond"], f["cond_s"]], maxw), lab_col)
        c.text(x, y + 14, value, self._sky_fit(c, value, [f["val"], f["city"], f["cond"]], maxw), val_col)

    # --- Astro-Uhr ------------------------------------------------------------ #
    @staticmethod
    def _sky_clockdeg(ts):
        """Winkel auf dem 24-Stunden-Ring (Mittag oben, im Uhrzeigersinn) für die Ortszeit von ts."""
        lt = time.localtime(ts)
        h = lt.tm_hour + lt.tm_min / 60 + lt.tm_sec / 3600
        return (h * 15 + 180) % 360

    def _sky_astro_static(self, c, t, lat, lon):
        """Hintergrund der Astro-Uhr für den Tag von t: Ring, Himmelsscheibe, Sterne, Auf-/Untergangsmarken."""
        f, cx, cy = _sky_fonts(), CLOCK_CX, CLOCK_CY
        s, gold, gold_d = CLOCK_SS, (214, 176, 98), (120, 94, 48)
        for r in range(112, 60, -4):                     # Schimmer hinter der Uhr
            c.circle(cx, cy, r, fill=mix((7, 9, 20), (22, 24, 44), (112 - r) / 52))
        c.circle(cx, cy, 102, fill=gold_d)             # 24-Stunden-Ring
        c.circle(cx, cy, 101, fill=(18, 20, 38))
        # Himmelsscheibe: je 6 Minuten Ortszeit die Farbe nach der Sonnenhöhe
        lt = time.localtime(t)
        alts = []
        for i in range(240):
            ts = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, i // 10, (i % 10) * 6 + 3, 0, 0, 0, -1))
            alt = _sky_sun_dir(ts, lat, lon)[0]
            alts.append(alt)
            a0 = (i * 1.5 + 180) % 360 - 90
            c.d.pieslice([(cx - 73) * s, (cy - 73) * s, (cx + 73) * s, (cy + 73) * s], a0, a0 + 1.7,
                         fill=_sky_grad(_sky_SKY_STOPS, alt))
        # Sterne im dunklen Teil
        rnd = random.Random(42)
        for _ in range(110):
            deg, rr, b = rnd.uniform(0, 360), 28 + 44 * math.sqrt(rnd.random()), rnd.uniform(0.35, 1)
            alt = alts[int(((deg - 180) % 360) / 1.5) % 240]
            if alt < -7:
                x, y = [v / s for v in c.pt(cx, cy, rr, deg)]
                col = mix(_sky_grad(_sky_SKY_STOPS, alt), (235, 238, 255), b * min(1, (-7 - alt) / 6))
                c.circle(x, y, 0.45 + 0.5 * b, fill=col)
        # Horizontmarken bei Sonnenauf- und -untergang
        rise, sset = _sky_events(_sky_day0(t), lat, lon)
        if rise not in ("day", "night"):
            for ev in (rise, sset):
                c.radial(cx, cy, 58, 73, self._sky_clockdeg(ev), 1.2, (250, 236, 200))
        c.circle(cx, cy, 73, outline=gold_d, width=1)
        c.circle(cx, cy, 101, outline=gold, width=0.8)
        c.circle(cx, cy, 88, outline=gold, width=0.8)
        for q in range(96):
            if q % 4:
                c.radial(cx, cy, 99, 101, q * 3.75, 0.5, gold_d)
        for h in range(24):
            deg = (h * 15 + 180) % 360
            c.radial(cx, cy, 98, 101, deg, 0.9, gold)
            x, y = [v / s for v in c.pt(cx, cy, 93.5, deg)]
            c.text(x, y, str(h or 24), f["num"], (240, 214, 150) if h % 6 == 0 else gold)

    def _sky_zodiac(self, c, cx, cy, sun_deg, sun_lon):
        """Tierkreisring: ekliptikale Länge wächst gegen den Uhrzeigersinn, die Sonne steht unter dem Sonnenzeiger."""
        f, s = _sky_fonts(), CLOCK_SS
        box = [(cx - 87) * s, (cy - 87) * s, (cx + 87) * s, (cy + 87) * s]
        cur = int(sun_lon // 30) % 12
        for k in range(12):
            d1 = sun_deg - (30 * k - sun_lon)             # Beginn des Zeichens
            fill = (196, 156, 78) if k == cur else ((30, 34, 60) if k % 2 else (24, 27, 50))
            c.d.arc(box, d1 - 30 - 90, d1 - 90, fill=fill, width=13 * s)
        for k in range(12):
            d1 = sun_deg - (30 * k - sun_lon)
            c.radial(cx, cy, 74, 87, d1, 0.7, (120, 94, 48))
            x, y = [v / s for v in c.pt(cx, cy, 80.5, d1 - 15)]
            c.text(x, y + 0.4, _sky_ZODIAC[k][0], f["glyph_b"] if k == cur else f["glyph"],
                   (28, 20, 8) if k == cur else (170, 150, 110))
        c.circle(cx, cy, 87, outline=(120, 94, 48), width=0.8)

    def _sky_moon_textures(self, r):
        """Mondscheibe hell und dunkel (mit Meeren), Größe 2r vergrößert, und Kreismaske."""
        return self._clock_cache("sky_moontex", r, lambda: self._sky_moon_build(r))

    @staticmethod
    def _sky_moon_build(r):
        n = int(2 * r * CLOCK_SS)
        rnd = random.Random(7)
        maria = [(0.30, -0.35, 0.28), (-0.05, -0.30, 0.22), (0.25, 0.10, 0.26), (-0.30, 0.05, 0.18),
                 (-0.15, 0.40, 0.16), (0.45, -0.05, 0.14), (0.05, 0.02, 0.12)]
        out = []
        for base, sea in (((232, 228, 208), (176, 172, 158)), ((44, 48, 66), (34, 38, 54))):
            img = Image.new("RGB", (n, n), base)
            d = ImageDraw.Draw(img)
            for mx, my, mr in maria:
                d.ellipse([(0.5 + mx - mr) * n, (0.5 + my - mr) * n, (0.5 + mx + mr) * n, (0.5 + my + mr) * n],
                          fill=sea)
            img = img.filter(ImageFilter.GaussianBlur(n / 30))
            d = ImageDraw.Draw(img)
            for _ in range(14):                       # kleine Krater
                x, y, cr = rnd.uniform(0.15, 0.85), rnd.uniform(0.15, 0.85), rnd.uniform(0.012, 0.035)
                d.ellipse([(x - cr) * n, (y - cr) * n, (x + cr) * n, (y + cr) * n], outline=mix(base, sea, 0.8),
                          width=max(1, n // 90))
            out.append(img)
        mask = Image.new("L", (n, n), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, n - 1, n - 1], fill=255)
        return out[0], out[1], mask

    def _sky_moon_big(self, c, cx, cy, r, frac, south):
        lit, dark, mask = self._sky_moon_textures(r)
        s, n = CLOCK_SS, lit.size[0]
        pos = (int(round((cx - r) * s)), int(round((cy - r) * s)))
        c.img.paste(dark, pos, mask)
        lm = Image.new("L", (n, n), 0)
        ImageDraw.Draw(lm).polygon(_sky_moon_poly(n / 2, n / 2, n / 2 - 0.5, frac, south, 60), fill=255)
        c.img.paste(lit, pos, lm)

    def _sky_moon_small(self, c, x, y, r, frac, south):
        s = CLOCK_SS
        c.circle(x, y, r + 0.8, fill=(12, 14, 26))
        c.circle(x, y, r, fill=(52, 56, 74))
        c.d.polygon([(px * s, py * s) for px, py in _sky_moon_poly(x, y, r, frac, south, 16)], fill=(236, 232, 214))

    @clock_face("astro", fps=1)
    def face_astro(self, profile):
        f = _sky_fonts()
        t = self._clock_now()
        lat, lon, place = self._sky_place()
        lt = time.localtime(t)
        key = ("sky_astro", lt.tm_year, lt.tm_yday, round(lat, 3), round(lon, 3))
        c = self._clock_canvas(key, (7, 9, 20), lambda c: self._sky_astro_static(c, t, lat, lon))
        cx, cy, s = CLOCK_CX, CLOCK_CY, CLOCK_SS
        gold, dim, white = (214, 176, 98), (128, 136, 160), (236, 232, 220)
        _, _, sun_lon = _sky_sun(t)
        age, frac, lit = _sky_moon(t)
        south = lat < 0
        sun_deg = self._sky_clockdeg(t)
        moon_deg = (sun_deg - frac * 360) % 360          # Mond bleibt pro Tag um Mondalter·360° hinter der Sonne
        self._sky_zodiac(c, cx, cy, sun_deg, sun_lon)
        # Zeiger: Mond (silbern) und Sonne (golden)
        c.hand(cx, cy, moon_deg, [(24, 2.2), (86, 1.2)], (170, 176, 196))
        c.hand(cx, cy, sun_deg, [(24, 3.0), (80, 2.2), (87, 0.8)], gold)
        mx, my = [v / s for v in c.pt(cx, cy, 94.5, moon_deg)]
        self._sky_moon_small(c, mx, my, 5.6, frac, south)
        sx, sy = [v / s for v in c.pt(cx, cy, 94.5, sun_deg)]
        for k in range(12):                              # Sonnenstrahlen
            c.hand(sx, sy, k * 30 + 15, [(4.5, 1.8), (8.6, 0)], (255, 206, 90))
        c.circle(sx, sy, 5.6, fill=(255, 196, 60), outline=(150, 96, 20), width=0.7)
        c.circle(sx - 1.2, sy - 1.2, 2.2, fill=(255, 236, 160))
        # Mitte: Mondphase
        c.circle(cx, cy, 25.5, fill=(10, 12, 24))
        self._sky_moon_big(c, cx, cy, 23, frac, south)
        c.circle(cx, cy, 25.5, outline=gold, width=1)
        # Seitentexte
        rise, sset = _sky_events(_sky_day0(t), lat, lon)
        if rise == "day":
            r_txt, s_txt, day_len = "—", "—", "24:00 h"
            self._sky_label(c, 29, 132, "POLARTAG", day_len, dim, white)
        elif rise == "night":
            r_txt, s_txt, day_len = "—", "—", "0:00 h"
            self._sky_label(c, 29, 132, "POLARNACHT", day_len, dim, white)
        else:
            r_txt, s_txt = _sky_hhmm(rise), _sky_hhmm(sset)
            mins = int(round((sset - rise) / 60))
            self._sky_label(c, 29, 132, "TAGESLÄNGE", f"{mins // 60}:{mins % 60:02d} h", dim, white)
        self._sky_label(c, 29, 28, "AUFGANG", r_txt, dim, (255, 206, 110))
        self._sky_label(c, 29, 80, "UNTERGANG", s_txt, dim, (240, 150, 90))
        c.text(29, 196, self._sky_trunc(c, place, f["cond_s"], 56), f["cond_s"], (90, 98, 124))
        c.text(291, 28, "MOND", f["cond"], dim)
        name = _sky_phase_name(age)
        for i, line in enumerate(name):
            c.text(291, 42 + i * 11 + (5 if len(name) == 1 else 0), line,
                   self._sky_fit(c, line, [f["cond"], f["cond_s"]], 58), white)
        c.text(291, 80, "BELEUCHTET", self._sky_fit(c, "BELEUCHTET", [f["cond"], f["cond_s"]], 56), dim)
        c.text(291, 94, f"{round(lit * 100)} %", f["val"], (206, 212, 236))
        sign, sname = _sky_ZODIAC[int(sun_lon // 30) % 12]
        c.text(291, 132, "SONNE IM", f["cond"], dim)
        c.text(291, 146, sign + " " + sname, self._sky_fit(c, sign + " " + sname, [f["cond"], f["cond_s"]], 58), gold)
        c.text(291, 196, f"{lt.tm_mday:02d}.{lt.tm_mon:02d}. {lt.tm_hour:02d}:{lt.tm_min:02d}", f["cond_s"],
               (90, 98, 124))
        return self._clock_finish(c)

    # --- Sonnenuhr ------------------------------------------------------------ #
    _sky_SD = (CLOCK_CX, 94, 86, 0.8, 0.24, -0.50)      # Mitte x/y, Plattenradius, Stauchung, Höhe → Bild (x, y)

    def _sky_sd_pt(self, x, y, z=0.0):
        """Punkt der Platte (x Ost, y Nord, z Höhe; Displaypixel) → vergrößerte Bildkoordinaten."""
        cx, cy, _, sy, kx, ky = self._sky_SD
        return ((cx + x + z * kx) * CLOCK_SS, (cy - y * sy + z * ky) * CLOCK_SS)

    def _sky_sd_ellipse(self, c, r, dy=0.0, **kw):
        cx, cy, _, sy, _, _ = self._sky_SD
        s = CLOCK_SS
        c.d.ellipse([(cx - r) * s, (cy - r * sy + dy) * s, (cx + r) * s, (cy + r * sy + dy) * s], **kw)

    def _sky_sd_geometry(self, lat):
        """Fußpunkt, Stablänge, Stabhöhe und Richtung der Stundenlinie zur Stunde h (Sonnenzeit)."""
        _, _, R, _, _, _ = self._sky_SD
        phi = math.radians(max(1.0, min(80.0, abs(lat))))
        sgn = 1 if lat >= 0 else -1                    # Südhalbkugel: Süden oben, Stunden gespiegelt
        foot, length = (0.0, -0.30 * R), 0.62 * R
        height = min(1.1 * R, length * math.tan(phi))

        def ray(h):
            ha = math.radians(15 * (h - 12))
            th = math.atan2(math.sin(phi) * math.sin(ha), math.cos(ha))   # tan θ = sin φ · tan(15°·(h−12))
            return sgn * math.sin(th), math.cos(th)
        return foot, length, height, ray

    @staticmethod
    def _sky_ray_circle(foot, u, rho):
        """Abstand vom Fußpunkt entlang u bis zum Kreis mit Radius rho um die Plattenmitte."""
        b = foot[0] * u[0] + foot[1] * u[1]
        return -b + math.sqrt(max(0.0, b * b - (foot[0] ** 2 + foot[1] ** 2) + rho * rho))

    def _sky_sundial_static(self, lat, lon):
        f = _sky_fonts()
        cx, cy, R, sy, _, _ = self._sky_SD
        s = CLOCK_SS
        c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), (14, 20, 17)))
        for k in range(24):                             # Hintergrund: dunkler Garten, unten heller
            c.rect(0, CLOCK_H * k / 24, WIDTH, CLOCK_H * (k + 1) / 24 + 1,
                   fill=mix((10, 14, 16), (26, 36, 28), k / 23))
        # Steinsockel (Zylinder) mit Körnung
        rs, depth = R * 1.13, 15
        for k in range(int(rs * 2)):                   # Seitenfläche, seitlich schattiert
            x = cx - rs + k
            light = 0.55 + 0.45 * math.cos((k / (2 * rs) - 0.35) * math.pi)
            col = mix((52, 50, 46), (128, 124, 116), max(0.0, light))
            yb = cy + 2 + rs * sy * math.sqrt(max(0.0, 1 - ((x - cx) / rs) ** 2))
            c.rect(x, cy + 2, x + 1.2, yb + depth, fill=col)
        self._sky_sd_ellipse(c, rs, 2, fill=(138, 134, 124))
        rnd = random.Random(42)
        for _ in range(420):
            a, rr = rnd.uniform(0, 2 * math.pi), rs * math.sqrt(rnd.random())
            x, y = cx + rr * math.cos(a), cy + 2 + rr * math.sin(a) * sy
            g = rnd.choice(((118, 114, 106), (156, 152, 142), (104, 100, 94)))
            c.circle(x, y, rnd.uniform(0.3, 0.8), fill=g)
        self._sky_sd_ellipse(c, rs, 2, outline=(170, 166, 156), width=s)
        # Bronzeplatte: Dicke, Farbverlauf, Rand
        self._sky_sd_ellipse(c, R, 3.5, fill=(80, 54, 24))
        for k in range(30):
            t = k / 29
            self._sky_sd_ellipse(c, R * (1 - t * 0.98), -t * 4, fill=mix((132, 94, 44), (196, 152, 82), t ** 0.7))
        self._sky_sd_ellipse(c, R, 0, outline=(222, 184, 112), width=s)
        ink, hi = (74, 50, 22), (226, 190, 120)
        for rho in (0.95 * R, 0.74 * R):                 # Ziffernring
            self._sky_sd_ellipse(c, rho, 0.6, outline=hi, width=2)
            self._sky_sd_ellipse(c, rho, 0, outline=ink, width=4)
        foot, length, height, ray = self._sky_sd_geometry(lat)

        def engrave(p0, p1, w):
            c.d.line([(p0[0], p0[1] + 0.7 * s), (p1[0], p1[1] + 0.7 * s)], fill=hi, width=max(1, round(w * 0.6 * s)))
            c.d.line([p0, p1], fill=ink, width=max(1, round(w * s)))
        for q in range(6 * 4, 18 * 4 + 1):               # Viertelstunden, halbe und volle Stunden
            h = q / 4
            u = ray(h)
            end = self._sky_ray_circle(foot, u, 0.74 * R)
            if q % 4 == 0:
                start, w = 7, 1.4
            elif q % 2 == 0:
                start, w = end * 0.55, 0.8
            else:
                start, w = end - 4, 0.6
            engrave(self._sky_sd_pt(foot[0] + u[0] * start, foot[1] + u[1] * start),
                    self._sky_sd_pt(foot[0] + u[0] * end, foot[1] + u[1] * end), w)
            if q % 4 == 0:
                d = self._sky_ray_circle(foot, u, 0.845 * R)
                x, y = self._sky_sd_pt(foot[0] + u[0] * d, foot[1] + u[1] * d)
                c.d.text((x, y + 0.6 * s), ROMAN_XII[int(h) % 12], font=f["roman"], fill=hi, anchor="mm")
                c.d.text((x, y), ROMAN_XII[int(h) % 12], font=f["roman"], fill=ink, anchor="mm")
        # Spruch und Breite im südlichen Teil
        for txt, font, yy in (("CARPE DIEM", f["motto"], -0.47 * R), (self._sky_latlon(lat, lon), f["cond_s"], -0.64 * R)):
            x, y = self._sky_sd_pt(0, yy)
            c.d.text((x, y + 0.7 * s), txt, font=font, fill=hi, anchor="mm")
            c.d.text((x, y), txt, font=font, fill=ink, anchor="mm")
        fx, fy = self._sky_sd_pt(*foot)
        c.d.ellipse([fx - 3 * s, fy - 2 * s, fx + 3 * s, fy + 2 * s], fill=ink)
        return c.img

    @staticmethod
    def _sky_latlon(lat, lon):
        return (f"{abs(lat):.1f}° {'N' if lat >= 0 else 'S'} · {abs(lon):.1f}° {'O' if lon >= 0 else 'W'}"
                .replace(".", ","))

    def _sky_sundial_images(self, lat, lon):
        """Tagbild, Schattenbild (dunkler) und Nachtbild der Platte sowie die Maske der Steinoberfläche."""
        day = self._sky_sundial_static(lat, lon)
        arr = np.asarray(day).astype(np.float32)
        shade = Image.fromarray((arr * np.array([0.50, 0.50, 0.56], np.float32)).astype(np.uint8))
        night = Image.fromarray(np.clip(arr * np.array([0.21, 0.28, 0.47], np.float32) + np.array([2, 4, 10], np.float32), 0, 255).astype(np.uint8))
        surf = Image.new("L", day.size, 0)
        cx, cy, R, sy, _, _ = self._sky_SD
        s, rs = CLOCK_SS, R * 1.13
        ImageDraw.Draw(surf).ellipse([(cx - rs) * s, (cy + 2 - rs * sy) * s, (cx + rs) * s, (cy + 2 + rs * sy) * s],
                                     fill=255)
        return day, shade, night, np.asarray(surf)

    def _sky_gnomon(self, c, foot, length, height, lit, night):
        """Dreieckiger Schattenstab; lit: 1 = Ostseite in der Sonne, 0 = im Schatten."""
        b = (foot[0], foot[1] + length)
        p_f, p_b, p_a = self._sky_sd_pt(*foot), self._sky_sd_pt(*b), self._sky_sd_pt(b[0], b[1], height)
        face = mix((110, 76, 34), (214, 170, 96), lit)
        edge = (240, 206, 140)
        if night:
            face, edge = mix(face, (30, 34, 52), 0.7), (96, 100, 124)
        s = CLOCK_SS
        c.d.polygon([(p_f[0] - 1.2 * s, p_f[1]), (p_b[0] - 1.2 * s, p_b[1]), (p_a[0] - 1.2 * s, p_a[1])],
                    fill=mix(face, (20, 14, 6), 0.55))
        c.d.polygon([p_f, p_b, p_a], fill=face)
        c.d.line([p_f, p_a], fill=edge, width=round(1.1 * s))
        c.d.line([p_b, p_a], fill=mix(face, (30, 20, 8), 0.4), width=s)

    @clock_face("sundial", fps=1)
    def face_sundial(self, profile):
        f = _sky_fonts()
        t = self._clock_now()
        lat, lon, place = self._sky_place()
        day, shade, night, surf = self._clock_cache("sky_sundial", (round(lat, 3), round(lon, 3)),
                                                    lambda: self._sky_sundial_images(lat, lon))
        alt, east, north = _sky_sun_dir(t, lat, lon)
        foot, length, height, _ = self._sky_sd_geometry(lat)
        is_night = alt <= 0.0
        lt = time.localtime(t)
        dim, white, warm = (128, 138, 130), (236, 232, 220), (240, 200, 120)
        if is_night:
            c = _Canvas(night.copy())
        else:
            c = _Canvas(day.copy())
            sgn = 1 if lat >= 0 else -1
            dx, dy = -sgn * east, -sgn * north             # Schattenrichtung auf der Platte
            k = min(3.2 * self._sky_SD[2], height / max(math.sin(math.radians(alt)), 1e-3))
            norm = math.hypot(dx, dy) or 1.0
            b = (foot[0], foot[1] + length)
            tip = (b[0] + dx / norm * k * math.cos(math.radians(alt)), b[1] + dy / norm * k * math.cos(math.radians(alt)))
            mask = Image.new("L", c.img.size, 0)
            strength = int(255 * min(1.0, 0.35 + alt / 8))
            ImageDraw.Draw(mask).polygon([self._sky_sd_pt(*foot), self._sky_sd_pt(*b), self._sky_sd_pt(*tip)],
                                         fill=strength)
            box = mask.getbbox()
            if box:
                pad = 12
                box = (max(0, box[0] - pad), max(0, box[1] - pad), min(mask.size[0], box[2] + pad),
                       min(mask.size[1], box[3] + pad))
                mask.paste(mask.crop(box).filter(ImageFilter.GaussianBlur(2.2 * CLOCK_SS / 2)), box[:2])
                mask = Image.fromarray(np.minimum(np.asarray(mask), surf))
                c.img = Image.composite(shade, c.img, mask)
                c.d = ImageDraw.Draw(c.img)
        self._sky_gnomon(c, foot, length, height, 1.0 if (east > 0) == (lat >= 0) else 0.25, is_night)
        # Seitentexte
        st = _sky_solar_time(t, lon)
        self._sky_label(c, 29, 44, "SONNENZEIT", f"{int(st // 60):02d}:{int(st % 60):02d}", dim, warm)
        eot = _sky_sun(t)[1]
        sec = int(round(abs(eot) * 60))
        self._sky_label(c, 29, 104, "ZEITGL.", f"{'+' if eot >= 0 else '−'}{sec // 60}:{sec % 60:02d}", dim, white)
        self._sky_label(c, 291, 44, "UHRZEIT", f"{lt.tm_hour:02d}:{lt.tm_min:02d}", dim, white)
        self._sky_label(c, 291, 104, "SOMMERZEIT" if lt.tm_isdst > 0 else "WINTERZEIT",
                        f"{lt.tm_mday:02d}.{lt.tm_mon:02d}.", dim, white)
        if is_night:
            rise, _ = _sky_events(_sky_day0(t), lat, lon)
            if rise == "night":
                msg = "Die Sonnenuhr ruht – Polarnacht"
            else:
                if rise == "day" or rise < t:
                    rise, _ = _sky_events(_sky_day0(t) + 86400, lat, lon)
                msg = "Die Sonnenuhr ruht – Sonnenaufgang " + (_sky_hhmm(rise) if rise not in ("day", "night") else "—")
            c.text(CLOCK_CX, 203, msg, f["cond"], (150, 164, 200))
        else:
            c.text(CLOCK_CX, 203, self._sky_trunc(c, place or "", f["cond_s"], 200), f["cond_s"], dim)
        return self._clock_finish(c)

    # --- Planetenuhr ---------------------------------------------------------- #
    _sky_ORBITS = ((52, 19), (94, 34), (140, 51))   # Halbachsen: Stunden, Minuten, Sekunden
    _sky_PC = (CLOCK_CX, 106)                            # Sonne

    def _sky_orbit_pt(self, k, deg):
        (a, b), (cx, cy) = self._sky_ORBITS[k], self._sky_PC
        rad = math.radians(deg)
        return cx + a * math.sin(rad), cy - b * math.cos(rad), -math.cos(rad)

    def _sky_orbit_marks(self, c, front):
        """Umlaufbahnen (vordere oder hintere Hälfte) mit Teilungspunkten."""
        cx, cy = self._sky_PC
        s = CLOCK_SS
        for k, (a, b) in enumerate(self._sky_ORBITS):
            col = (92, 104, 140) if front else (50, 58, 84)
            c.d.arc([(cx - a) * s, (cy - b) * s, (cx + a) * s, (cy + b) * s], 0 if front else 180,
                     180 if front else 360, fill=col, width=round(0.8 * s))
            for m in range(12):
                x, y, depth = self._sky_orbit_pt(k, m * 30)
                if (depth > 0) == front or abs(depth) < 1e-9 and front:
                    big = m % 3 == 0
                    c.circle(x, y, (1.5 if big else 0.9) * (1 + 0.15 * depth),
                             fill=mix(col, (220, 226, 250), 0.5 if big else 0.2))

    def _sky_planets_static(self):
        s = CLOCK_SS
        w, h = WIDTH * s, CLOCK_H * s
        img = Image.new("RGB", (w, h), (4, 5, 12))
        neb = Image.new("RGB", (w // 4, h // 4), (0, 0, 0))    # Nebelschleier, weich gezeichnet
        nd = ImageDraw.Draw(neb)
        for x, y, rx, ry, col in ((60, 40, 70, 30, (40, 16, 60)), (270, 170, 80, 36, (12, 30, 58)),
                                  (230, 30, 50, 22, (40, 20, 44)), (40, 180, 60, 26, (10, 34, 44))):
            nd.ellipse([(x - rx) * s / 4, (y - ry) * s / 4, (x + rx) * s / 4, (y + ry) * s / 4], fill=col)
        neb = neb.filter(ImageFilter.GaussianBlur(9)).resize((w, h), Image.BILINEAR)
        img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16) + np.asarray(neb), 0, 255).astype(np.uint8))
        c = _Canvas(img)
        rnd = random.Random(42)
        for _ in range(170):
            x, y, b = rnd.uniform(0, WIDTH), rnd.uniform(0, CLOCK_H), rnd.random() ** 2.2
            tint = rnd.choice(((255, 255, 255), (200, 216, 255), (255, 232, 200)))
            c.circle(x, y, 0.35 + 0.8 * b, fill=mix((30, 34, 50), tint, 0.35 + 0.65 * b))
            if b > 0.8:                                          # helle Sterne mit Kreuzschein
                c.radial(x, y, -3, 3, 0, 0.3, mix((20, 22, 34), tint, 0.5))
                c.radial(x, y, -3, 3, 90, 0.3, mix((20, 22, 34), tint, 0.5))
        self._sky_orbit_marks(c, False)
        # Sonne mit Glühen als RGBA-Bild
        n = 50 * s * 2
        glow = Image.new("L", (n, n), 0)
        gd = ImageDraw.Draw(glow)
        for r in range(50 * s, 0, -s):
            gd.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r], fill=int(200 * (1 - r / (50 * s)) ** 2.2))
        sun = Image.new("RGBA", (n, n), (255, 170, 60, 0))
        sun.putalpha(glow)
        sd = ImageDraw.Draw(sun)
        for r in range(15 * s, 0, -s):
            t = r / (15 * s)
            col = mix((255, 250, 220), (255, 150, 30), t ** 1.6)
            sd.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r], fill=col + (255,))
        return img, sun

    def _sky_planet(self, c, x, y, r, dark, light, spot=None):
        """Kugel, von der Sonne her beleuchtet."""
        cx, cy = self._sky_PC
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        c.circle(x, y, r + 1.6, fill=mix(dark, (4, 5, 12), 0.72))
        c.circle(x, y, r, fill=dark)
        c.circle(x + ux * r * 0.28, y + uy * r * 0.28, r * 0.74, fill=light)
        if spot:
            c.circle(x + ux * r * 0.18 - 0.25 * r, y + uy * r * 0.18 + 0.2 * r, r * 0.28, fill=spot)
        c.circle(x + ux * r * 0.48, y + uy * r * 0.48, r * 0.25, fill=mix(light, (255, 255, 255), 0.55))

    @clock_face("planets", fps=5)
    def face_planets(self, profile):
        f = _sky_fonts()
        bg, sun = self._clock_cache("sky_planets", 1, self._sky_planets_static)
        c = _Canvas(bg.copy())
        t = self._clock_now()
        lt = time.localtime(t)
        sec = lt.tm_sec + (t % 1)
        minute = lt.tm_min + sec / 60
        hour = lt.tm_hour % 12 + minute / 60
        s, (cx, cy) = CLOCK_SS, self._sky_PC
        bodies = []                                              # (Tiefe, Zeichenfunktion)
        # Stundenplanet (rot), Minutenplanet (blau, mit Mond), Sekundenplanet (golden, mit Ring)
        x, y, dep = self._sky_orbit_pt(0, hour * 30)
        bodies.append((dep, lambda x=x, y=y, dep=dep: self._sky_planet(
            c, x, y, 6.5 * (1 + 0.14 * dep), (96, 34, 20), (222, 110, 64), (170, 70, 40))))
        x, y, dep = self._sky_orbit_pt(1, minute * 6)
        mdeg = math.radians(t % 20 * 18)                         # Mond: ein Umlauf in 20 s
        mx, my, mdep = x + 15 * math.sin(mdeg), y - 5.5 * math.cos(mdeg), dep - 0.3 * math.cos(mdeg)
        bodies.append((dep, lambda x=x, y=y, dep=dep: self._sky_planet(
            c, x, y, 8 * (1 + 0.14 * dep), (20, 50, 110), (70, 140, 230), (90, 170, 110))))
        bodies.append((mdep, lambda: self._sky_planet(c, mx, my, 2.4, (80, 80, 88), (214, 214, 220))))
        x, y, dep = self._sky_orbit_pt(2, sec * 6)

        def saturn(x=x, y=y, dep=dep):
            r = 5.6 * (1 + 0.14 * dep)
            box = [(x - 2.3 * r) * s, (y - 0.75 * r) * s, (x + 2.3 * r) * s, (y + 0.75 * r) * s]
            c.d.arc(box, 180, 360, fill=(170, 150, 110), width=round(1.1 * s))
            self._sky_planet(c, x, y, r, (110, 86, 40), (236, 204, 132))
            c.d.arc(box, 0, 180, fill=(226, 204, 150), width=round(1.1 * s))
        bodies.append((dep, saturn))
        bodies.sort(key=lambda b: b[0])
        for dep, draw in bodies:
            if dep <= 0:
                draw()
        n = sun.size[0]
        c.img.paste(sun, (int(cx * s - n / 2), int(cy * s - n / 2)), sun)
        self._sky_orbit_marks(c, True)
        for dep, draw in bodies:
            if dep > 0:
                draw()
        # Legende und Uhrzeit dezent in den Ecken
        for i, (col, txt) in enumerate((((222, 110, 64), "STD"), ((70, 140, 230), "MIN"), ((236, 204, 132), "SEK"))):
            c.circle(8, 10 + i * 11, 2.6, fill=col)
            c.d.text((14 * s, (10 + i * 11) * s), txt, font=f["cond_s"], fill=(110, 118, 146), anchor="lm")
        c.d.text((312 * s, 204 * s), f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}", font=f["mono"],
                 fill=(120, 130, 160), anchor="rm")
        return self._clock_finish(c)

    # --- Weltzeituhr ---------------------------------------------------------- #
    def _sky_world_cities(self):
        """Städte aus der Option (höchstens 6; leer/ungültig → Standardliste) mit Zeitzone oder None."""
        raw = self._copt("world").get("cities")
        cities = [x for x in raw if isinstance(x, dict) and x.get("tz")] if isinstance(raw, list) else []
        if not cities:
            cities = next(o["default"] for o in CLOCK_OPTIONS["world"] if o["key"] == "cities")
        out = []
        for city in cities[:6]:
            try:
                tz = zoneinfo.ZoneInfo(str(city["tz"]))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError, TypeError, OSError):
                tz = None
            out.append((str(city.get("name") or city["tz"]), str(city["tz"]), tz))
        return out

    @staticmethod
    def _sky_world_grid(n):
        """Zellen (Mitte x, Mitte y, Breite, Höhe) für n Städte."""
        rows = [[1], [2], [3], [2, 2], [3, 2], [3, 3]][max(1, n) - 1]
        h = CLOCK_H / len(rows)
        cells = []
        for r, cols in enumerate(rows):
            w = WIDTH / (3 if n >= 5 else cols)
            x0 = (WIDTH - cols * w) / 2
            cells += [(x0 + (k + 0.5) * w, (r + 0.5) * h, w, h) for k in range(cols)]
        return cells[:n]

    @staticmethod
    def _sky_world_layout(x, y, w, h):
        """(Radius, Mitte y des Zifferblatts, y des Namens, y der Zeitzeile, groß?) – Block senkrecht mittig."""
        r = min(w * 0.34, (h - 38) / 2)
        big = r > 50
        name_off, time_off = (16, 36) if big else (10, 23)
        top = y - (2 * r + time_off + 7) / 2
        return r, top + r, top + 2 * r + name_off, top + 2 * r + time_off, big

    def _sky_world_static(self, c, cities, days):
        """Hintergrund der Weltzeituhr: je Stadt Feld, Zifferblatt (Tag/Nacht) und Name."""
        f = _sky_fonts()
        cells = self._sky_world_grid(len(cities))
        for (name, _, tz), (x, y, w, h), day in zip(cities, cells, days):
            c.rect(x - w / 2 + 2, y - h / 2 + 2, x + w / 2 - 2, y + h / 2 - 2, fill=(16, 20, 32))
            r, dy, ny, _, big = self._sky_world_layout(x, y, w, h)
            if tz is None:
                face, ink, rim = (40, 42, 50), (140, 144, 156), (70, 74, 86)
            elif day:
                face, ink, rim = (238, 234, 222), (40, 42, 50), (150, 154, 166)
            else:
                face, ink, rim = (26, 34, 64), (190, 200, 230), (70, 84, 130)
            c.circle(x, dy, r + 1.5, fill=rim)
            c.circle(x, dy, r, fill=face)
            for m in range(60 if r > 40 else 12):
                big = m % (5 if r > 40 else 1) == 0
                if big or r > 40:
                    step = 360 / (60 if r > 40 else 12)
                    c.radial(x, dy, r * (0.80 if big else 0.9), r * 0.96, m * step, (1.4 if big else 0.5) * max(1, r / 40),
                             ink)
            if tz is None:
                c.text(x, dy, "?", f["q"], ink)
            elif day:                                           # Sonne bzw. Mond im Zifferblatt
                c.circle(x, dy + r * 0.45, max(2, r * 0.11), fill=(250, 190, 60))
            else:
                c.circle(x, dy + r * 0.45, max(2, r * 0.11), fill=(230, 226, 200))
                c.circle(x + r * 0.05, dy + r * 0.42, max(2, r * 0.11), fill=face)
            font = f["city_b"] if big else f["city"]
            c.text(x, ny, self._sky_trunc(c, name, font, w - 8), font, (230, 232, 240))

    @clock_face("world", fps=1)
    def face_world(self, profile):
        f = _sky_fonts()
        t = self._clock_now()
        cities = self._sky_world_cities()
        local = datetime.datetime.fromtimestamp(t).date()
        nows = [datetime.datetime.fromtimestamp(t, tz) if tz else None for _, _, tz in cities]
        days = tuple(bool(n and 6 <= n.hour < 18) for n in nows)
        key = ("sky_world", tuple(z for _, z, _ in cities), tuple(n for n, _, _ in cities), days)
        c = self._clock_canvas(key, (10, 13, 22), lambda c: self._sky_world_static(c, cities, days))
        acc = PROFILE_COLOR.get(profile, self.FG)
        for _, (x, y, w, h), now, day in zip(cities, self._sky_world_grid(len(cities)), nows, days):
            r, dy, _, ty, big = self._sky_world_layout(x, y, w, h)
            if now is None:
                c.text(x, ty, "unbekannte Zone", f["cond_s"], (170, 120, 120))
                continue
            ink = (30, 32, 40) if day else (220, 226, 245)
            ha = (now.hour % 12 + now.minute / 60) * 30
            ma = (now.minute + now.second / 60) * 6
            c.hand(x, dy, ha, [(-r * 0.12, r * 0.12), (r * 0.45, r * 0.10), (r * 0.56, 0)], ink)
            c.hand(x, dy, ma, [(-r * 0.14, r * 0.09), (r * 0.74, r * 0.06), (r * 0.84, 0)], ink)
            c.hand(x, dy, now.second * 6, [(-r * 0.2, max(0.7, r * 0.03)), (r * 0.86, max(0.5, r * 0.02))], acc)
            c.circle(x, dy, max(1.6, r * 0.07), fill=acc)
            off = now.utcoffset().total_seconds() / 60
            sign, off = ("+" if off >= 0 else "−"), abs(int(off))
            utc = f"UTC{sign}{off // 60}" + (f":{off % 60:02d}" if off % 60 else "")
            txt = f"{now.hour:02d}:{now.minute:02d}"
            tfont, ufont = (f["val"], f["cond"]) if big else (f["city"], f["cond_s"])
            tw = c.d.textlength(txt, font=tfont) / CLOCK_SS
            uw = c.d.textlength(utc, font=ufont) / CLOCK_SS
            x0 = x - (tw + 5 + uw) / 2
            c.d.text((x0 * CLOCK_SS, ty * CLOCK_SS), txt, font=tfont, fill=(236, 232, 220), anchor="lm")
            c.d.text(((x0 + tw + 5) * CLOCK_SS, ty * CLOCK_SS), utc, font=ufont, fill=(130, 138, 160), anchor="lm")
            diff = (now.date() - local).days
            if diff:                                          # anderer Kalendertag als hier
                bx, by = x + r * 0.92, dy - r * 0.86
                c.d.rounded_rectangle([(bx - 9) * CLOCK_SS, (by - 6) * CLOCK_SS, (bx + 9) * CLOCK_SS,
                                       (by + 6) * CLOCK_SS], radius=3 * CLOCK_SS, fill=acc,
                                      outline=(16, 20, 32), width=CLOCK_SS)
                c.text(bx, by, ("+" if diff > 0 else "−") + str(abs(diff)), f["cond"], (255, 255, 255))
        return self._clock_finish(c)

    # --- Radaruhr ------------------------------------------------------------- #
    _sky_RC = (108, CLOCK_CY, 99)                      # Mitte x/y und Radius des Schirms (Displaypixel)
    _sky_R_ROWS = (("ZEIT", 22), ("DATUM", 62), ("PEILUNG", 102), ("ZIEL STD", 142), ("ZIEL MIN", 180))

    def _sky_radar_static(self):
        """Schirm und Pult einmal zeichnen (vergrößert), verkleinert als Zahlenfeld."""
        f = _sky_fonts()
        cx, cy, R = self._sky_RC
        c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), (20, 23, 22)))
        for k in range(20):                                      # gebürstetes Pult
            c.rect(0, CLOCK_H * k / 20, WIDTH, CLOCK_H * (k + 1) / 20 + 1, fill=mix((30, 34, 32), (16, 19, 18), k / 19))
        c.circle(cx, cy, R + 6.5, fill=(52, 58, 55))
        c.circle(cx, cy, R + 5, fill=(34, 38, 36))
        c.circle(cx, cy, R + 2, fill=(4, 8, 6))
        for r in range(int(R), 0, -3):                           # Schirm, in der Mitte etwas heller
            c.circle(cx, cy, r, fill=mix((0, 30, 12), (1, 11, 5), (r / R) ** 1.5))
        line, faint = (20, 110, 52), (10, 62, 30)
        for k in (0.25, 0.5, 0.75, 1.0):
            c.circle(cx, cy, R * k, outline=line if k in (0.5, 1.0) else faint, width=0.7)
        for deg in (0, 90):
            c.radial(cx, cy, -R, R, deg, 0.6, faint)
        for deg in range(0, 360, 5):
            big = deg % 30 == 0
            c.radial(cx, cy, R - (6 if big else 3 if deg % 10 == 0 else 1.8), R, deg, 0.9 if big else 0.6, line)
            if big:
                x, y = [v / CLOCK_SS for v in c.pt(cx, cy, R - 12, deg)]
                c.text(x, y, f"{deg:03d}", f["mono_s"], (26, 130, 62))
        for (lab, y) in self._sky_R_ROWS:                      # Anzeigefelder
            c.d.rounded_rectangle([222 * CLOCK_SS, (y - 7) * CLOCK_SS, 314 * CLOCK_SS, (y + 25) * CLOCK_SS],
                                  radius=3 * CLOCK_SS, fill=(6, 14, 9), outline=(48, 56, 52), width=CLOCK_SS)
            c.d.text((228 * CLOCK_SS, (y + 1) * CLOCK_SS), lab, font=f["mono_s"], fill=(34, 120, 60), anchor="lm")
        for x, y in ((6, 6), (6, 208), (314, 6), (314, 208)):   # Schrauben
            c.circle(x, y, 3, fill=(64, 70, 66), outline=(24, 28, 26), width=0.6)
            c.radial(x, y, -2.2, 2.2, 60, 0.7, (24, 28, 26))
        img = c.img.resize((WIDTH, CLOCK_H), Image.LANCZOS)
        # Blip-Formen (Gauß-Flecken)
        def blob(sigma, n):
            ax = np.arange(n, dtype=np.float32) - (n - 1) / 2
            return np.exp(-(ax[None, :] ** 2 + ax[:, None] ** 2) / (2 * sigma * sigma))
        rnd = random.Random(42)
        clutter = [(rnd.uniform(0, 360), R * rnd.uniform(0.05, 0.3) ** 1.2 * 1.4, rnd.uniform(0.3, 0.8))
                   for _ in range(26)]
        return np.asarray(img).astype(np.float32), blob(2.6, 17), blob(1.8, 13), blob(0.9, 7), clutter

    @staticmethod
    def _sky_stamp(arr, x, y, sprite, amp):
        """Fleck sprite mit Stärke amp bei (x, y) aufaddieren (am Rand abgeschnitten)."""
        n = sprite.shape[0]
        x0, y0 = int(round(x)) - n // 2, int(round(y)) - n // 2
        h, w = arr.shape
        sx0, sy0 = max(0, -x0), max(0, -y0)
        sx1, sy1 = min(n, w - x0), min(n, h - y0)
        if sx0 < sx1 and sy0 < sy1:
            arr[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] += sprite[sy0:sy1, sx0:sx1] * amp

    @clock_face("radar", fps=5)
    def face_radar(self, profile):
        f = _sky_fonts()
        base, blob_h, blob_m, core, clutter = self._clock_cache("sky_radar", 1, self._sky_radar_static)
        t = self._clock_now()
        lt = time.localtime(t)
        cx, cy, R = self._sky_RC
        beam = (lt.tm_sec + t % 1) * 6
        # Nachleuchtender Fächer (doppelte Auflösung, dann verkleinert)
        fan = Image.new("L", (WIDTH * 2, CLOCK_H * 2), 0)
        fd = ImageDraw.Draw(fan)
        box = [(cx - R) * 2, (cy - R) * 2, (cx + R) * 2, (cy + R) * 2]
        for k in range(44, -1, -1):
            a1 = beam - k * 2.2
            fd.pieslice(box, a1 - 2.4 - 90, a1 - 90, fill=int(118 * math.exp(-k / 11)))
        green = np.asarray(fan.resize((WIDTH, CLOCK_H), Image.BILINEAR)).astype(np.float32)
        white = np.zeros_like(green)
        rad = math.radians(beam)
        for k in range(int(R)):                                  # heller Strahl
            self._sky_stamp(white, cx + k * math.sin(rad), cy - k * math.cos(rad), core, 70)

        def glow(deg):
            """Nachleuchten 0…1 eines Echos: hell, wenn der Strahl es gerade überstrichen hat."""
            age = ((beam - deg) % 360) / 6
            return math.exp(-age / 9)
        for deg, r, amp in clutter:
            g = glow(deg)
            self._sky_stamp(green, cx + r * math.sin(math.radians(deg)), cy - r * math.cos(math.radians(deg)), core,
                            amp * (40 + 150 * g))
        h_deg = (lt.tm_hour % 12 + lt.tm_min / 60) * 30
        m_deg = (lt.tm_min + lt.tm_sec / 60) * 6
        for deg, r, sprite in ((h_deg, 0.45 * R, blob_h), (m_deg, 0.80 * R, blob_m)):
            g = glow(deg)
            x, y = cx + r * math.sin(math.radians(deg)), cy - r * math.cos(math.radians(deg))
            self._sky_stamp(green, x, y, sprite, 150 + 330 * g)
            self._sky_stamp(white, x, y, core, 40 + 260 * g ** 2)
        out = (base + green[..., None] * np.array([0.22, 1.0, 0.42], np.float32)
               + white[..., None] * np.array([0.75, 1.0, 0.8], np.float32))
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        img.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), (0, 0))
        d = ImageDraw.Draw(img)
        vals = (f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}", f"{lt.tm_mday:02d}.{lt.tm_mon:02d}.{lt.tm_year % 100:02d}",
                f"{int(beam) % 360:03d}°", f"{int(h_deg) % 360:03d}° {lt.tm_hour:02d}h",
                f"{int(m_deg) % 360:03d}° {lt.tm_min:02d}m")
        for (lab, y), v in zip(self._sky_R_ROWS, vals):
            d.text((268, y + 13), v, font=f["r_val"], fill=(90, 255, 140), anchor="mm")
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul uhr_anzeigen
#   Zifferblätter Klappzahlenuhr, Nixie-Röhrenuhr, LED-Radiowecker, LED-Matrix, Zählwerk.
#
#   Das Unveränderliche wird einmal CLOCK_SS-fach gezeichnet und verkleinert; je Bild werden nur fertige,
#   zwischengespeicherte Einzelteile (Karten, Röhrenziffern, Segmente, Leuchtpunkte, Rollen) in Displaygröße
#   aufgesetzt – so bleiben auch die Zifferblätter mit fps 5 schnell.
# ═══════════════════════════════════════════════════════════════════════════

def _disp_sprite(w, h, build, bg=(0, 0, 0, 0)):
    """Bild w×h (RGBA, Displaygröße): build(c) zeichnet CLOCK_SS-fach auf bg, dann verkleinert
    (mit vormultipliziertem Alpha, damit transparente Ränder nicht dunkel ausfransen)."""
    c = _Canvas(Image.new("RGBA", (w * CLOCK_SS, h * CLOCK_SS), bg))
    build(c)
    return c.img.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")


def _disp_grad(img, box, radius, stops, mask=None):
    """Senkrechter Verlauf in einem abgerundeten Rechteck (vergrößerte Pixel); stops = [(0…1, Farbe), …]."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    col = []
    for i in range(h):
        u = i / max(1, h - 1)
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if u <= b or (b, cb) == stops[-1]:
                col.append(mix(ca, cb, 0 if b == a else min(1, max(0, (u - a) / (b - a)))))
                break
    g = Image.new("RGB", (1, h))
    g.putdata(col)
    g = g.resize((w, h), Image.NEAREST)
    if mask is None:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    img.paste(g, (x0, y0), mask)


def _disp_wood(img, box, radius, base, seed):
    """Holz mit Maserung (vergrößerte Pixel)."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = x1 - x0, y1 - y0
    rnd = random.Random(seed)
    wood = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(wood)
    y = -6
    while y < h + 6:
        amp, per, ph = rnd.uniform(1, 7), rnd.uniform(150, 500), rnd.uniform(0, 6.3)
        col = mix(base, (0, 0, 0) if rnd.random() < 0.65 else (255, 214, 170), rnd.uniform(0.06, 0.28))
        d.line([(x, y + amp * math.sin(x / per * 6.283 + ph)) for x in range(-20, w + 40, 20)],
               fill=col, width=rnd.randint(1, 4))
        y += rnd.randint(3, 8)
    wood = wood.filter(ImageFilter.GaussianBlur(1.3))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    img.paste(wood, (x0, y0), mask)


def _disp_tint(img, color, mask, f=1.0, pos=(0, 0)):
    """Farbe durch eine Maske (L) auf das RGBA-Bild img legen (echtes Überblenden)."""
    if f != 1.0:
        mask = mask.point([int(v * f) for v in range(256)])
    layer = Image.new("RGBA", mask.size, tuple(color[:3]) + (0,))
    layer.putalpha(mask)
    img.alpha_composite(layer, pos)


def _disp_darken(img, f):
    """RGBA-Bild um den Faktor f (0…1) abdunkeln."""
    r, g, b, a = img.split()
    lut = [int(v * f) for v in range(256)]
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


def _disp_engrave(c, x, y, txt, font, dark, light):
    """Gravierter Text (mittig): Lichtkante unten rechts, darüber die dunkle Kerbe."""
    c.text(x + 0.45, y + 0.45, txt, font, light)
    c.text(x, y, txt, font, dark)


def _disp_screw(c, x, y, r, deg):
    """Schlitzschraube."""
    c.circle(x + 0.4, y + 0.6, r + 0.6, fill=(40, 42, 46))
    c.circle(x, y, r, fill=(150, 154, 160), outline=(70, 72, 78), width=0.6)
    c.circle(x - r * 0.25, y - r * 0.25, r * 0.55, fill=(186, 190, 196))
    c.radial(x, y, -r * 0.8, r * 0.8, deg, max(0.8, r * 0.28), (54, 56, 60))


# Schaltbilder der Pixelschriften (1 = Leuchtpunkt an)
_disp_font57 = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}
_disp_font35 = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "A": ["010", "101", "111", "101", "101"], "B": ["110", "101", "110", "101", "110"],
    "D": ["110", "101", "101", "101", "110"], "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"], "G": ["011", "100", "101", "101", "011"],
    "I": ["111", "010", "010", "010", "111"], "J": ["001", "001", "001", "101", "010"],
    "K": ["101", "101", "110", "101", "101"], "L": ["100", "100", "100", "100", "111"],
    "M": ["101", "111", "111", "101", "101"], "N": ["110", "101", "101", "101", "101"],
    "O": ["010", "101", "101", "101", "010"], "P": ["110", "101", "110", "100", "100"],
    "R": ["110", "101", "110", "101", "101"], "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"], "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"], "W": ["101", "101", "111", "111", "101"],
    "Z": ["111", "001", "010", "100", "111"], ".": ["0", "0", "0", "0", "1"], " ": ["00"] * 5,
}
_disp_month3 = ["JAN", "FEB", "MRZ", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEZ"]

# Segmente der 7-Segment-Ziffern
_disp_seg_map = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg",
                 "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def _disp_seg_polys(x, y, w, h, t, gap, skew):
    """Die sieben Segmente a–g als Polygone (Displaykoordinaten), um skew je Pixel Höhe nach rechts geneigt."""
    ht = t / 2

    def hseg(yc):
        x0, x1 = ht + gap, w - ht - gap
        return [(x0, yc), (x0 + ht, yc - ht), (x1 - ht, yc - ht), (x1, yc), (x1 - ht, yc + ht), (x0 + ht, yc + ht)]

    def vseg(xc, y0, y1):
        return [(xc, y0), (xc + ht, y0 + ht), (xc + ht, y1 - ht), (xc, y1), (xc - ht, y1 - ht), (xc - ht, y0 + ht)]

    m = h / 2
    segs = {"a": hseg(ht), "g": hseg(m), "d": hseg(h - ht),
            "f": vseg(ht, ht + gap, m - gap), "b": vseg(w - ht, ht + gap, m - gap),
            "e": vseg(ht, m + gap, h - ht - gap), "c": vseg(w - ht, m + gap, h - ht - gap)}
    return {k: [(x + px + (h - py) * skew, y + py) for px, py in pts] for k, pts in segs.items()}


class DisplayFaces:
    # --- gemeinsame Hilfen ---------------------------------------------------- #
    # Alle Einzelteile liegen in self._clock_cache: der Slot benennt das Teil (z. B. ("disp_seg", "big", "7")),
    # der Schlüssel die veränderlichen Farben – ein Farbwechsel ersetzt also, statt anzusammeln.
    def _disp_part(self, slot, key, w, h, build):
        """Einzelteil w×h (RGBA, Displaygröße), build(c) zeichnet es CLOCK_SS-fach auf Transparenz."""
        return self._clock_cache(slot, key, lambda: _disp_sprite(w, h, build))

    def _disp_glyph(self, txt, style, bold, bw, bh, dh, maxw, ref="0123456789"):
        """Zeichen als Maske (L, bw×bh): Ziffernhöhe dh, mittig; breiter als maxw (gemessen an ref) → gestaucht.
        style wie bei clock_font; die Schriftgröße ergibt sich aus der Höhe der „0“ bei 200 px."""
        def build():
            x0, y0, x1, y1 = clock_font(style, 200, bold).getbbox("0")
            font = clock_font(style, max(4, round(200 * dh / (y1 - y0))), bold)
            refw = max(font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in ref)
            tw = max(bw, round(bw / min(1.0, maxw / refw)))
            m = Image.new("L", (tw, bh), 0)
            ImageDraw.Draw(m).text((tw / 2, (bh + dh) / 2), txt, font=font, fill=255, anchor="ms")
            return m.resize((bw, bh), Image.LANCZOS) if tw != bw else m
        return self._clock_cache(("disp_glyph", txt, style, bold, bw, bh, dh, maxw, ref), None, build)

    def _disp_base(self, face, key, bg, build):
        """Hintergrund (RGBA 320×CLOCK_H) einmal CLOCK_SS-fach zeichnen, verkleinert zwischenspeichern; Kopie."""
        return self._clock_cache(("disp_base", face), key,
                                 lambda: _disp_sprite(WIDTH, CLOCK_H, build, tuple(bg) + (255,))).copy()

    def _disp_out(self, img):
        """Displaybild 320×240 (die Fußzeile zeichnet der Aufrufer)."""
        out = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        out.paste(img.convert("RGB"), (0, 0))
        return out

    @staticmethod
    def _disp_step(t, dur):
        """Fortschritt 0…1 einer Bewegung in den ersten dur Sekunden nach dem Sekundenwechsel."""
        return min(1.0, (t - math.floor(t) + 0.2) / dur)

    # --- Klappzahlenuhr ------------------------------------------------------- #
    # Kartenart: Breite, Höhe, Ziffernhöhe, Ziffernbreite höchstens, Eckradius
    _disp_flip_kinds = {"big": (62, 110, 80, 50, 6), "sec": (26, 36, 24, 19, 3), "date": (20, 30, 19, 15, 3)}

    @staticmethod
    def _disp_flip_slots():
        """(Kartenart, x, y) aller Karten: HH MM, Sekunden, Wochentag Tag Monat."""
        slots = [("big", x, 8) for x in (17, 84, 174, 241)]
        slots += [("sec", 132, 128), ("sec", 161, 128)]
        x = 76
        for n in (2, 2, 3):
            for _ in range(n):
                slots.append(("date", x, 175))
                x += 22
            x += 8
        return slots

    @staticmethod
    def _disp_flip_text(now):
        return (f"{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}" + WEEKDAY_2[now.tm_wday]
                + f"{now.tm_mday:02d}" + MONTH_3[now.tm_mon - 1])

    def _disp_flip_card(self, kind, ch, ink):
        """Karte mit Zeichen ch: (ganz, obere Hälfte, untere Hälfte) als RGBA."""
        w, h, dh, dw, r = self._disp_flip_kinds[kind]
        s = CLOCK_SS

        def draw(c):
            _disp_grad(c.img, (0, 0, w * s, h * s), r * s, [(0, (60, 60, 65)), (0.5, (40, 40, 44)),
                                                           (0.5, (34, 34, 38)), (1, (22, 22, 25))])
            c.rect(r * 0.6, 0, w - r * 0.6, 0.4, fill=(84, 84, 90))           # Lichtkante oben
            _disp_tint(c.img, ink, self._disp_glyph(ch, "sans-cond", True, w * s, h * s, dh * s, dw * s))
            c.rect(0, h / 2 - 0.7, w, h / 2 + 0.5, fill=(6, 6, 8))           # Trennfuge
            c.rect(0, h / 2 + 0.5, w, h / 2 + 0.9, fill=(58, 58, 62))

        def build():
            full = _disp_sprite(w, h, draw)
            return full, full.crop((0, 0, w, h // 2)), full.crop((0, h // 2, w, h))
        return self._clock_cache(("disp_flip", kind, ch), ink, build)

    def _disp_flip_draw(self, img, kind, x, y, old, new, p, ink):
        """Karte zeichnen; wechselt das Zeichen, klappt die obere Hälfte um (p = 0…1)."""
        full, top, bot = self._disp_flip_card(kind, new, ink)
        if old == new or p >= 1:
            img.alpha_composite(full, (x, y))
            return
        _, otop, obot = self._disp_flip_card(kind, old, ink)
        w, hh = top.size
        img.alpha_composite(top, (x, y))
        if p < 0.5:                                        # alte obere Hälfte fällt nach vorn
            k = math.cos(p * math.pi)
            img.alpha_composite(_disp_darken(obot, 1 - 0.3 * (1 - k)), (x, y + hh))
            fh = max(1, round(hh * k))
            fw = w + 2 * round(w * 0.02 * math.sin(p * math.pi))
            flap = _disp_darken(otop.resize((fw, fh), Image.BILINEAR), 1 - 0.4 * (1 - k))
            img.alpha_composite(flap, (x - (fw - w) // 2, y + hh - fh))
        else:                                              # neue untere Hälfte klappt herunter
            k = -math.cos(p * math.pi)
            img.alpha_composite(_disp_darken(obot, 1 - 0.3 * (1 - k)), (x, y + hh))
            fh = max(1, round(hh * k))
            fw = w + 2 * round(w * 0.02 * math.sin(p * math.pi))
            flap = _disp_darken(bot.resize((fw, fh), Image.BILINEAR), 1 - 0.5 * (1 - k))
            img.alpha_composite(flap, (x - (fw - w) // 2, y + hh))

    def _disp_flip_static(self, c):
        s = CLOCK_SS
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (30, 30, 34)), (1, (12, 12, 14))])
        shadow = Image.new("L", c.img.size, 0)
        sd = ImageDraw.Draw(shadow)
        for kind, x, y in self._disp_flip_slots():
            w, h, _dh, _dw, r = self._disp_flip_kinds[kind]
            sd.rounded_rectangle([(x - 1) * s, (y + 2) * s, (x + w + 1) * s, (y + h + 4) * s], r * s, fill=190)
        shadow = shadow.filter(ImageFilter.GaussianBlur(4 * s))
        _disp_tint(c.img, (0, 0, 0), shadow)
        for kind, x, y in self._disp_flip_slots():
            w, h, _dh, _dw, r = self._disp_flip_kinds[kind]
            for k, col in ((2.4, (18, 18, 20)), (1.2, (28, 28, 31))):     # weitere Blätter darunter
                c.d.rounded_rectangle([(x + k) * s, (y + h - 4) * s, (x + w - k) * s, (y + h + k) * s],
                                      r * s, fill=col)
            hy, hw, hl = y + h / 2, (3 if kind == "big" else 1.6), (8 if kind == "big" else 4)
            for hx in (x - hw, x + w):                                     # Scharniere
                c.rect(hx, hy - hl / 2, hx + hw, hy + hl / 2, fill=(92, 92, 98), outline=(18, 18, 20), width=0.5)
                c.rect(hx, hy - 0.4, hx + hw, hy + 0.4, fill=(40, 40, 44))
        cx = CLOCK_CX
        for cy in (46, 80):                                                # Doppelpunkt
            c.d.rounded_rectangle([(cx - 4.5) * s, (cy - 4.5) * s, (cx + 4.5) * s, (cy + 4.5) * s],
                                  2 * s, fill=(62, 62, 68))
            c.d.rounded_rectangle([(cx - 3.5) * s, (cy - 3.5) * s, (cx + 3.5) * s, (cy + 1) * s],
                                  1.5 * s, fill=(84, 84, 92))

    @clock_face("flip", fps=5)
    def face_flip(self, profile):
        t = self._clock_now()
        now, prev = time.localtime(t), time.localtime(math.floor(t) - 1)
        p = self._disp_step(t, 0.5)
        acc = PROFILE_COLOR.get(profile, self.FG)
        img = self._disp_base("flip", None, (20, 20, 24), self._disp_flip_static)
        white, sec_ink = (238, 236, 228), mix(acc, (255, 255, 255), 0.45)
        for (kind, x, y), a, b in zip(self._disp_flip_slots(), self._disp_flip_text(prev), self._disp_flip_text(now)):
            self._disp_flip_draw(img, kind, x, y, a, b, p, sec_ink if kind == "sec" else white)
        d = ImageDraw.Draw(img)
        small, big = clock_font("sans-cond", 10, True), clock_font("sans-cond", 17, True)
        d.text((88, 139), "KW", font=small, fill=(120, 124, 134), anchor="mm")
        d.text((88, 155), time.strftime("%V", now), font=big, fill=(200, 202, 208), anchor="mm")
        d.text((232, 139), "JAHR", font=small, fill=(120, 124, 134), anchor="mm")
        d.text((232, 155), str(now.tm_year), font=big, fill=(200, 202, 208), anchor="mm")
        return self._disp_out(img)

    # --- Nixie-Röhrenuhr ------------------------------------------------------ #
    _disp_nixie_x = (10, 55, 117, 162, 224, 269)      # linke Kante der Röhren (40 breit)
    _disp_nixie_colon = (106, 213)

    def _disp_nixie_mask(self, ch):
        """Ziffernmaske einer Kathode (CLOCK_SS-fach, 40×80 Displaypixel)."""
        s = CLOCK_SS
        return self._disp_glyph(ch, "sans", False, 40 * s, 80 * s, 58 * s, 25 * s)

    def _disp_nixie_lit(self, ch):
        """Leuchtende Ziffer mit Glühen (RGBA 40×80)."""
        def build(c):
            m = self._disp_nixie_mask(ch)
            wide = m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10 * CLOCK_SS))
            near = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2.5 * CLOCK_SS))
            _disp_tint(c.img, (255, 70, 0), wide, 0.55)
            _disp_tint(c.img, (255, 110, 20), near, 0.9)
            _disp_tint(c.img, (255, 150, 50), m.filter(ImageFilter.MaxFilter(3)))
            _disp_tint(c.img, (255, 222, 170), m.filter(ImageFilter.MinFilter(3)), 0.85)
        return self._disp_part(("disp_nixie_lit", ch), None, 40, 80, build)

    @staticmethod
    def _disp_nixie_shape(d, x, s, fill=None, outline=None, width=0, inset=0):
        """Umriss des Glaskolbens (runde Kuppe) auf ImageDraw d."""
        i = inset
        d.rounded_rectangle([(x + i) * s, (8 + i) * s, (x + 40 - i) * s, (166 - i) * s], (20 - i) * s,
                            fill=fill, outline=outline, width=width)

    def _disp_nixie_static(self, c, acc):
        s = CLOCK_SS
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (24, 19, 17)), (0.8, (12, 10, 10)), (1, (8, 7, 7))])
        # Holzsockel: Oberseite und Vorderkante
        _disp_wood(c.img, (0, 172 * s, WIDTH * s, 184 * s), 0, (96, 58, 32), 11)
        _disp_wood(c.img, (0, 184 * s, WIDTH * s, CLOCK_H * s), 0, (62, 36, 20), 12)
        c.rect(0, 183.6, WIDTH, 184.4, fill=(130, 86, 52))
        c.rect(0, 172, WIDTH, 172.5, fill=(40, 26, 16))
        glow = Image.new("L", c.img.size, 0)                  # Widerschein der Röhren auf dem Holz
        gd = ImageDraw.Draw(glow)
        for x in self._disp_nixie_x:
            gd.ellipse([(x + 2) * s, 170 * s, (x + 38) * s, 186 * s], fill=150)
        _disp_tint(c.img, (255, 90, 20), glow.filter(ImageFilter.GaussianBlur(5 * s)), 0.45)
        # Messingschild und Betriebsleuchte
        _disp_grad(c.img, (116 * s, 190 * s, 204 * s, 206 * s), 2 * s,
                   [(0, (214, 178, 102)), (0.5, (176, 138, 64)), (1, (120, 88, 38))])
        for sx in (120, 200):
            c.circle(sx, 198, 1.3, fill=(92, 66, 28))
        f = clock_font("sans", 8 * s, True)
        _disp_engrave(c, 34, 198, "G19s", f, (200, 168, 110), (26, 14, 8))
        c.circle(292, 198, 3.2, fill=(20, 14, 10))
        c.circle(292, 198, 2.2, fill=acc)
        c.circle(291.4, 197.4, 0.8, fill=mix(acc, (255, 255, 255), 0.6))
        for x in self._disp_nixie_x:
            # Fassung mit Stiften
            c.d.rounded_rectangle([(x + 5) * s, 169 * s, (x + 35) * s, 180 * s], 3 * s, fill=(16, 16, 18))
            c.rect(x + 7, 169.5, x + 33, 170.4, fill=(58, 58, 62))
            for k in range(7):
                px = x + 9 + k * 3.7
                c.rect(px - 0.35, 164, px + 0.35, 170, fill=(170, 166, 150))
            # Kolben innen, Glimmerscheiben, Haltedrähte
            self._disp_nixie_shape(c.d, x, s, fill=(20, 16, 15))
            c.rect(x + 6, 160, x + 34, 166, fill=(34, 30, 28))                   # Quetschfuß
            for py in (38, 136):
                c.d.rounded_rectangle([(x + 4) * s, py * s, (x + 36) * s, (py + 3) * s], 1 * s, fill=(70, 66, 60))
            for px in (x + 7, x + 33):
                c.rect(px - 0.4, 41, px + 0.4, 160, fill=(80, 76, 70))
            unlit = Image.new("L", (40 * s, 80 * s), 0)
            for ch in "0123456789":
                unlit = Image.fromarray(np.maximum(np.asarray(unlit), np.asarray(self._disp_nixie_mask(ch))))
            _disp_tint(c.img, (84, 72, 62), unlit, 0.7, (x * s, 48 * s))
        # Neon-Doppelpunkte
        dots = Image.new("L", c.img.size, 0)
        dd = ImageDraw.Draw(dots)
        for cx in self._disp_nixie_colon:
            for cy in (72, 104):
                c.d.rounded_rectangle([(cx - 4) * s, (cy - 7) * s, (cx + 4) * s, (cy + 7) * s], 4 * s,
                                      fill=(26, 20, 18), outline=(92, 96, 104), width=2)
                dd.ellipse([(cx - 2.2) * s, (cy - 2.2) * s, (cx + 2.2) * s, (cy + 2.2) * s], fill=255)
                c.rect(cx - 0.3, cy + 7, cx + 0.3, 169, fill=(120, 116, 106))
        _disp_tint(c.img, (255, 80, 10), dots.filter(ImageFilter.GaussianBlur(4 * s)), 0.9)
        _disp_tint(c.img, (255, 150, 60), dots)
        _disp_tint(c.img, (255, 220, 170), dots.filter(ImageFilter.MinFilter(5)), 0.8)

    def _disp_nixie_front(self):
        """Vorderes Gitter und Glasspiegelungen (RGBA über dem ganzen Bild)."""
        def build(c):
            s = CLOCK_SS
            mesh = Image.new("L", c.img.size, 0)
            md = ImageDraw.Draw(mesh)
            for k in range(-80, 330, 3):                        # Rautengitter
                md.line([(k * s, 30 * s), ((k + 110) * s, 140 * s)], fill=255, width=2)
                md.line([((k + 110) * s, 30 * s), (k * s, 140 * s)], fill=255, width=2)
            clip = Image.new("L", c.img.size, 0)
            cd = ImageDraw.Draw(clip)
            for x in self._disp_nixie_x:
                cd.rectangle([(x + 5) * s, 41 * s, (x + 35) * s, 136 * s], fill=255)
            _disp_tint(c.img, (60, 56, 52), Image.composite(mesh, clip, clip), 0.5)
            for x in self._disp_nixie_x:
                c.rect(x + 5, 41, x + 35, 41.6, fill=(84, 80, 74, 255))
                glass = Image.new("L", c.img.size, 0)
                gd = ImageDraw.Draw(glass)
                self._disp_nixie_shape(gd, x, s, outline=255, width=3)
                _disp_tint(c.img, (190, 200, 215), glass, 0.35)
                hi = Image.new("L", c.img.size, 0)
                hd = ImageDraw.Draw(hi)
                hd.rounded_rectangle([(x + 5) * s, 24 * s, (x + 9) * s, 150 * s], 2 * s, fill=150)
                hd.rounded_rectangle([(x + 33) * s, 30 * s, (x + 34.2) * s, 146 * s], 1 * s, fill=70)
                hd.arc([(x + 5) * s, 11 * s, (x + 35) * s, 41 * s], 200, 290, fill=200, width=int(1.6 * s))
                _disp_tint(c.img, (255, 255, 255), hi.filter(ImageFilter.GaussianBlur(0.8 * s)), 0.35)
                getter = Image.new("L", c.img.size, 0)          # Getterspiegel in der Kuppe
                ImageDraw.Draw(getter).ellipse([(x + 9) * s, 10 * s, (x + 31) * s, 22 * s], fill=255)
                _disp_tint(c.img, (150, 150, 158), getter.filter(ImageFilter.GaussianBlur(2 * s)), 0.45)
        return self._disp_part("disp_nixie_front", None, WIDTH, CLOCK_H, build)

    @clock_face("nixie", fps=1)
    def face_nixie(self, profile):
        now = time.localtime(self._clock_now())
        acc = PROFILE_COLOR.get(profile, self.FG)
        img = self._disp_base("nixie", acc, (12, 10, 10), lambda c: self._disp_nixie_static(c, acc))
        for x, ch in zip(self._disp_nixie_x, f"{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}"):
            img.alpha_composite(self._disp_nixie_lit(ch), (x, 48))
        img.alpha_composite(self._disp_nixie_front())
        d = ImageDraw.Draw(img)
        txt = f"{WEEKDAY_2[now.tm_wday]} {now.tm_mday:02d}.{now.tm_mon:02d}.{now.tm_year}"
        f = clock_font("sans-cond", 9, True)
        d.text((CLOCK_CX + 0.5, 198.5), txt, font=f, fill=(236, 206, 140), anchor="mm")   # Lichtkante
        d.text((CLOCK_CX, 198), txt, font=f, fill=(70, 46, 16), anchor="mm")
        return self._disp_out(img)

    # --- LED-Radiowecker ------------------------------------------------------ #
    # Ziffernart: Breite, Höhe, Segmentdicke, Fuge
    _disp_seg_kinds = {"big": (40, 84, 9, 1.3), "small": (13, 24, 3.4, 0.6)}
    _disp_seg_skew = 0.1
    _disp_seg_big_x = (26, 74, 134, 182)
    _disp_seg_small_x = (196, 213)

    def _disp_seg_sprite(self, kind, what, color):
        """Leuchtende Segmente (Ziffer oder „:“) mit Glühen, RGBA; linke obere Ecke der Ziffer bei (8, 8)."""
        w, h, t, gap = self._disp_seg_kinds[kind]
        pad, sk = 8, self._disp_seg_skew
        W, H = int(w + h * sk + 2 * pad), int(h + 2 * pad)

        def build(c):
            s = CLOCK_SS
            m = Image.new("L", c.img.size, 0)
            md = ImageDraw.Draw(m)
            if what == ":":
                for fy in (0.3, 0.7):
                    yc, xc = h * fy, w / 2 + h * (1 - fy) * sk
                    md.polygon([((pad + xc + dx - dy * sk) * s, (pad + yc + dy) * s)
                                for dx, dy in ((-t / 2, -t / 2), (t / 2, -t / 2), (t / 2, t / 2), (-t / 2, t / 2))],
                               fill=255)
            else:
                polys = _disp_seg_polys(pad, pad, w, h, t, gap, sk)
                for seg in _disp_seg_map[what]:
                    md.polygon([(px * s, py * s) for px, py in polys[seg]], fill=255)
            _disp_tint(c.img, color, m.filter(ImageFilter.GaussianBlur(t * 0.9 * s)), 0.7)
            _disp_tint(c.img, color, m)
            _disp_tint(c.img, mix(color, (255, 255, 255), 0.45),
                       m.filter(ImageFilter.MinFilter(int(t * 0.45 * s) * 2 + 1)).filter(ImageFilter.GaussianBlur(s)),
                       0.7)
        return self._disp_part(("disp_seg", kind, what), color, W, H, build)

    def _disp_seg_static(self, c, color):
        s, sk = CLOCK_SS, self._disp_seg_skew
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (16, 14, 14)), (1, (8, 8, 9))])
        _disp_wood(c.img, (4 * s, 4 * s, 316 * s, 210 * s), 14 * s, (70, 40, 22), 21)
        c.d.rounded_rectangle([4 * s, 4 * s, 316 * s, 210 * s], 14 * s, outline=(30, 18, 10), width=s)
        _disp_grad(c.img, (12 * s, 12 * s, 308 * s, 202 * s), 8 * s, [(0, (34, 32, 32)), (1, (18, 17, 17))])
        c.d.rounded_rectangle([12 * s, 12 * s, 308 * s, 202 * s], 8 * s, outline=(8, 8, 8), width=s)
        # Rauchglasfenster
        c.d.rounded_rectangle([18 * s, 18 * s, 238 * s, 152 * s], 7 * s, fill=(120, 120, 124))
        _disp_grad(c.img, (19 * s, 19 * s, 237 * s, 151 * s), 6 * s, [(0, (22, 12, 12)), (1, (12, 8, 8))])
        shimmer = mix(color, (14, 9, 9), 0.9)
        for kind, xs, y in (("big", self._disp_seg_big_x, 30), ("small", self._disp_seg_small_x, 122)):
            w, h, t, gap = self._disp_seg_kinds[kind]
            for x in xs:
                for pts in _disp_seg_polys(x, y, w, h, t, gap, sk).values():
                    c.d.polygon([(px * s, py * s) for px, py in pts], fill=shimmer)
        w, h, t, _g = self._disp_seg_kinds["big"]
        for fy in (0.3, 0.7):
            yc, xc = 30 + h * fy, 124 + h * (1 - fy) * sk
            c.d.polygon([((xc + dx - dy * sk) * s, (yc + dy) * s)
                         for dx, dy in ((-t / 2, -t / 2), (t / 2, -t / 2), (t / 2, t / 2), (-t / 2, t / 2))],
                        fill=shimmer)
        # Glockensymbol und Aufschrift (unbeleuchtet)
        self._disp_seg_bell(c, 32, 134, shimmer)
        c.d.text((42 * s, 134 * s), "ALARM", font=clock_font("sans-cond", 11 * s, True), fill=shimmer,
                 anchor="lm")
        # Senderskala
        _disp_grad(c.img, (18 * s, 160 * s, 238 * s, 196 * s), 5 * s, [(0, (40, 34, 26)), (1, (26, 22, 18))])
        c.d.rounded_rectangle([18 * s, 160 * s, 238 * s, 196 * s], 5 * s, outline=(90, 90, 94), width=s)
        tiny = clock_font("sans-cond", 8 * s, True)
        ink = (214, 196, 150)
        c.d.text((24 * s, 184 * s), "UKW", font=tiny, fill=ink, anchor="lm")
        c.d.text((232 * s, 184 * s), "MHz", font=tiny, fill=ink, anchor="rm")
        x0, x1 = 50, 206
        for k in range(88 * 2, 108 * 2 + 1):
            x = x0 + (k / 2 - 88) / 20 * (x1 - x0)
            major = k % 8 == 0
            c.rect(x - 0.3, 176 - (5 if major else 2.5), x + 0.3, 176, fill=ink)
            if major:
                c.text(x, 167.5, str(k // 2), tiny, ink)
        c.rect(x0, 176, x1, 176.6, fill=ink)
        nx = x0 + (101.3 - 88) / 20 * (x1 - x0)
        c.rect(nx - 0.7, 163, nx + 0.7, 193, fill=(230, 60, 30))
        c.d.text(((x0 + x1) / 2 * s, 186 * s), "G19s", font=tiny, fill=(150, 136, 104), anchor="mm")
        # Lautsprechergitter und Knöpfe
        c.d.rounded_rectangle([246 * s, 18 * s, 302 * s, 162 * s], 6 * s, fill=(26, 26, 28), outline=(70, 70, 74),
                              width=s)
        for j in range(24):
            for i in range(8):
                x, y = 252 + i * 6.3 + (3.1 if j % 2 else 0), 24 + j * 5.8
                if x < 298:
                    c.circle(x, y, 1.8, fill=(6, 6, 7))
                    c.circle(x + 0.4, y + 0.5, 1.8, outline=(52, 52, 56), width=0.4)
        for kx in (259, 289):
            c.circle(kx, 182, 11.5, fill=(10, 10, 10))
            c.circle(kx, 182, 10, fill=(58, 58, 62))
            for k in range(24):
                c.radial(kx, 182, 8.2, 10, k * 15, 0.7, (34, 34, 36))
            c.circle(kx, 182, 7.8, fill=(76, 76, 82))
            c.circle(kx - 1.5, 180.5, 4, fill=(96, 96, 102))
            c.radial(kx, 182, 3, 7, 40 if kx < 270 else -60, 1.2, (220, 220, 225))

    @staticmethod
    def _disp_seg_bell(c, x, y, col):
        """Kleine Weckerglocke."""
        c.d.chord([(x - 4.5) * c.s, (y - 5.5) * c.s, (x + 4.5) * c.s, (y + 5) * c.s], 180, 360, fill=col)
        c.rect(x - 4.5, y - 0.3, x + 4.5, y + 3, fill=col)
        c.rect(x - 5.5, y + 3, x + 5.5, y + 4.2, fill=col)
        c.circle(x, y + 5.2, 1.3, fill=col)

    def _disp_seg_glass(self):
        """Spiegelung auf dem Rauchglas (RGBA)."""
        def build(c):
            s = CLOCK_SS
            m = Image.new("L", c.img.size, 0)
            md = ImageDraw.Draw(m)
            md.polygon([(70 * s, 19 * s), (130 * s, 19 * s), (60 * s, 151 * s), (0, 151 * s)], fill=16)
            md.polygon([(142 * s, 19 * s), (156 * s, 19 * s), (86 * s, 151 * s), (72 * s, 151 * s)], fill=10)
            clip = Image.new("L", c.img.size, 0)
            ImageDraw.Draw(clip).rounded_rectangle([19 * s, 19 * s, 237 * s, 151 * s], 6 * s, fill=255)
            _disp_tint(c.img, (255, 255, 255), Image.composite(m, clip, clip))
            c.rect(24, 19.4, 232, 20.2, fill=(255, 255, 255, 40))
        return self._disp_part("disp_seg_glass", None, WIDTH, CLOCK_H, build)

    @clock_face("seg7", fps=1)
    def face_seg7(self, profile):
        now = time.localtime(self._clock_now())
        color = self._ccolor(self._copt("seg7")["color"], profile, (255, 40, 30))
        img = self._disp_base("seg7", color, (10, 9, 9), lambda c: self._disp_seg_static(c, color))
        for x, ch in zip(self._disp_seg_big_x, f"{now.tm_hour:02d}{now.tm_min:02d}"):
            img.alpha_composite(self._disp_seg_sprite("big", ch, color), (x - 8, 30 - 8))
        if now.tm_sec % 2 == 0:
            w = self._disp_seg_kinds["big"][0]
            img.alpha_composite(self._disp_seg_sprite("big", ":", color), (round(124 - w / 2) - 8, 30 - 8))
        for x, ch in zip(self._disp_seg_small_x, f"{now.tm_sec:02d}"):
            img.alpha_composite(self._disp_seg_sprite("small", ch, color), (x - 8, 122 - 8))
        alarm = (self.settings or {}).get("alarm_clock") or {}
        if alarm.get("enabled"):
            def build(c):
                s = CLOCK_SS
                m = Image.new("L", c.img.size, 0)
                mc = _Canvas(m)
                self._disp_seg_bell(mc, 10, 12, 255)
                mc.d.text((20 * s, 12 * s), "ALARM  " + str(alarm.get("time") or "07:00"),
                          font=clock_font("sans-cond", 11 * s, True), fill=255, anchor="lm")
                _disp_tint(c.img, color, m.filter(ImageFilter.GaussianBlur(2 * s)), 0.6)
                _disp_tint(c.img, mix(color, (255, 255, 255), 0.15), m)
            img.alpha_composite(self._disp_part("disp_seg_alarm", (str(alarm.get("time")), color), 110, 24, build),
                                (22, 122))
        img.alpha_composite(self._disp_seg_glass())
        return self._disp_out(img)

    # --- LED-Matrix ----------------------------------------------------------- #
    _disp_mx_big = (17, 16, 11, 27, 9)          # erste Mitte x, y, Abstand, Spalten, Zeilen
    _disp_mx_small = (12, 122, 5, 60, 7)
    _disp_mx_sec_y = 170

    def _disp_mx_led(self, big, color, hot=False):
        """Leuchtpunkt mit Glühen (RGBA, Mitte im Bildmittelpunkt)."""
        size, r = (22, 4.3) if big else (10, 2.0)

        def build(c):
            s, m = CLOCK_SS, size / 2
            halo = Image.new("L", c.img.size, 0)
            ImageDraw.Draw(halo).ellipse([(m - r * 1.3) * s, (m - r * 1.3) * s, (m + r * 1.3) * s,
                                          (m + r * 1.3) * s], fill=255)
            _disp_tint(c.img, color, halo.filter(ImageFilter.GaussianBlur(r * 0.8 * s)), 0.55)
            c.circle(m, m, r, fill=mix(color, (255, 255, 255), 0.5) if hot else color)
            c.circle(m - r * 0.25, m - r * 0.25, r * 0.4, fill=mix(color, (255, 255, 255), 0.55 if not hot else 0.85))
        return self._disp_part(("disp_mx_led", big, hot), color, size, size, build)

    def _disp_mx_static(self, c, color):
        s = CLOCK_SS
        off = mix(color, (0, 0, 0), 0.86)
        rim = mix(off, (60, 60, 64), 0.5)
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (26, 26, 28)), (1, (14, 14, 16))])
        c.d.rounded_rectangle([3 * s, 3 * s, 317 * s, 211 * s], 6 * s, fill=(10, 10, 11), outline=(80, 82, 88),
                              width=2 * s)
        for sx, sy in ((9, 9), (311, 9), (9, 205), (311, 205)):
            _disp_screw(c, sx, sy, 2.2, 45)
        panels = []
        x0, y0, p, nc, nr = self._disp_mx_big
        panels.append((x0, y0, p, nc, nr, 4.3))
        x0, y0, p, nc, nr = self._disp_mx_small
        panels.append((x0, y0, p, nc, nr, 2.0))
        panels.append((12, self._disp_mx_sec_y, 5, 60, 1, 2.0))
        for x0, y0, p, nc, nr, r in panels:
            c.d.rounded_rectangle([(x0 - p / 2 - 1) * s, (y0 - p / 2 - 1) * s, (x0 + (nc - 0.5) * p + 1) * s,
                                   (y0 + (nr - 0.5) * p + 1) * s], 2 * s, fill=(4, 4, 5), outline=(34, 34, 38),
                                  width=s)
            for j in range(nr):
                for i in range(nc):
                    x, y = x0 + i * p, y0 + j * p
                    c.circle(x, y, r, fill=off, outline=rim, width=0.4)
        tiny = clock_font("sans-cond", 8 * s, True)
        silk = (150, 152, 158)
        for k in (0, 15, 30, 45):
            c.d.text(((12 + k * 5) * s, 181 * s), str(k), font=tiny, fill=silk, anchor="mm")
            c.rect(12 + k * 5 - 0.3, 175, 12 + k * 5 + 0.3, 177, fill=silk)
        c.d.text(((12 + 59 * 5) * s, 181 * s), "59", font=tiny, fill=silk, anchor="mm")
        c.d.text((12 * s, 198 * s), "G19s", font=tiny, fill=silk, anchor="lm")
        c.d.text((308 * s, 198 * s), "LED 27×9 · 60×7 · 60", font=tiny, fill=(96, 98, 104), anchor="rm")

    def _disp_mx_text(self, txt, font):
        """Punkte (Spalte, Zeile) eines Textes in einer Pixelschrift und seine Breite in Spalten."""
        pts, col = [], 0
        for ch in txt:
            rows = font.get(ch, font.get(" "))
            for j, row in enumerate(rows):
                for i, v in enumerate(row):
                    if v == "1":
                        pts.append((col + i, j))
            col += len(rows[0]) + 1
        return pts, col - 1

    @clock_face("matrix", fps=1)
    def face_matrix(self, profile):
        now = time.localtime(self._clock_now())
        color = self._ccolor(self._copt("matrix")["color"], profile)
        img = self._disp_base("matrix", color, (14, 14, 16), lambda c: self._disp_mx_static(c, color))
        big, small = self._disp_mx_led(True, color), self._disp_mx_led(False, color)
        x0, y0, p, _nc, _nr = self._disp_mx_big
        pts = []
        for ch, col in zip(f"{now.tm_hour:02d}{now.tm_min:02d}", (1, 7, 15, 21)):
            pts += [(col + i, 1 + j) for i, j in self._disp_mx_text(ch, _disp_font57)[0]]
        if now.tm_sec % 2 == 0:
            pts += [(13, 3), (13, 5)]
        for i, j in pts:
            img.alpha_composite(big, (x0 + i * p - 11, y0 + j * p - 11))
        x0, y0, p, nc, _nr = self._disp_mx_small
        txt = f"{WEEKDAY_2[now.tm_wday]} {now.tm_mday:02d} {_disp_month3[now.tm_mon - 1]} {now.tm_year}"
        pts, width = self._disp_mx_text(txt, _disp_font35)
        off = (nc - width) // 2
        for i, j in pts:
            img.alpha_composite(small, (x0 + (off + i) * p - 5, y0 + (1 + j) * p - 5))
        hot = self._disp_mx_led(False, color, hot=True)
        for i in range(now.tm_sec + 1):
            img.alpha_composite(hot if i == now.tm_sec else small, (12 + i * 5 - 5, self._disp_mx_sec_y - 5))
        return self._disp_out(img)

    # --- Zählwerk ------------------------------------------------------------- #
    # Rollenart: Breite, Fensterhöhe, Ziffernabstand, Ziffernhöhe
    _disp_roll_kinds = {"big": (34, 60, 46, 32), "small": (20, 32, 25, 17)}
    _disp_cnt_groups = (37, 125, 213)            # linke Kante der Rollenpaare (Stunden, Minuten, Sekunden)
    _disp_cnt_small = ((88, 3), (212, 2))        # zweites Zählwerk: (x, Rollen) für TAG und KW

    def _disp_roll_cell(self, kind, ch, red):
        w, _wh, pitch, dh = self._disp_roll_kinds[kind]
        bg = (150, 24, 20) if red else (18, 18, 19)

        def build(c):
            s = CLOCK_SS
            c.rect(0, 0, w, pitch, fill=bg)
            _disp_tint(c.img, (240, 238, 230), self._disp_glyph(ch, "sans-cond", True, w * s, pitch * s, dh * s,
                                                                 w * 0.66 * s))
        return self._disp_part(("disp_roll", kind, ch, red), None, w, pitch, build)

    def _disp_roll_shade(self, kind):
        """Wölbung der Rolle: oben und unten dunkler, Glanzstreifen über der Mitte (RGBA)."""
        def build():
            w, wh, _p, _dh = self._disp_roll_kinds[kind]
            shade = Image.new("RGBA", (w, wh), (0, 0, 0, 0))
            for y in range(wh):
                u = (y + 0.5) / wh * 2 - 1
                dark = int(255 * min(1, 0.95 * abs(u) ** 2.2))
                shine = int(60 * math.exp(-((u + 0.38) / 0.16) ** 2))
                for x in range(w):
                    edge = 1 - 0.35 * (abs((x + 0.5) / w * 2 - 1) ** 6)
                    if shine > dark:
                        shade.putpixel((x, y), (255, 255, 255, int(shine * edge)))
                    else:
                        shade.putpixel((x, y), (0, 0, 0, min(255, dark + int(70 * (1 - edge)))))
            return shade
        return self._clock_cache(("disp_roll_shade", kind), None, build)

    def _disp_roll(self, img, x, y, kind, old, new, mod, p, red=False):
        """Zahlenrolle im Fenster ab (x, y); wechselt die Ziffer, rollt sie von unten nach (p = 0…1)."""
        w, wh, pitch, _dh = self._disp_roll_kinds[kind]
        a, b = int(old), int(new)
        if a == b or p >= 1:
            seq, pos = [(b - 1) % mod, b, (b + 1) % mod], 1.0
        else:
            e = p * p * (3 - 2 * p)
            seq, pos = [(a - 1) % mod, a, b, (b + 1) % mod], 1 + e
        win = Image.new("RGBA", (w, wh))
        for k, v in enumerate(seq):
            top = round(wh / 2 + (k - pos) * pitch - pitch / 2)
            if -pitch < top < wh:
                win.paste(self._disp_roll_cell(kind, str(v), red), (0, top))
        win.alpha_composite(self._disp_roll_shade(kind))
        img.paste(win, (x, y))

    def _disp_cnt_window(self, c, x0, y0, x1, y1):
        """Vertieftes Fenster in der Platte."""
        s = CLOCK_SS
        c.d.rounded_rectangle([(x0 - 3) * s, (y0 - 3) * s, (x1 + 3) * s, (y1 + 3) * s], 4 * s, fill=(70, 72, 76))
        c.d.rounded_rectangle([(x0 - 2) * s, (y0 - 2) * s, (x1 + 3) * s, (y1 + 3) * s], 3.5 * s, fill=(196, 200, 206))
        c.d.rounded_rectangle([(x0 - 2) * s, (y0 - 2) * s, (x1 + 2) * s, (y1 + 2) * s], 3 * s, fill=(46, 48, 52))
        c.rect(x0, y0, x1, y1, fill=(6, 6, 6))

    def _disp_cnt_static(self, c, acc):
        s = CLOCK_SS
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (22, 22, 24)), (1, (12, 12, 13))])
        # gebürstete Stahlplatte
        plate = Image.new("RGB", ((WIDTH - 8) * s, (CLOCK_H - 8) * s), (132, 136, 142))
        pd = ImageDraw.Draw(plate)
        rnd = random.Random(7)
        for y in range(plate.size[1]):
            v = rnd.randint(-10, 10)
            pd.line([(0, y), (plate.size[0], y)], fill=(132 + v, 136 + v, 142 + v))
        plate = Image.composite(Image.new("RGB", plate.size, (0, 0, 0)), plate,     # unten etwas dunkler
                                Image.linear_gradient("L").resize(plate.size).point(lambda v: v // 5))
        mask = Image.new("L", plate.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, plate.size[0] - 1, plate.size[1] - 1], 10 * s, fill=255)
        c.d.rounded_rectangle([3 * s, 5 * s, 317 * s, (CLOCK_H - 2) * s], 11 * s, fill=(6, 6, 7))
        c.img.paste(plate, (4 * s, 4 * s), mask)
        c.d.rounded_rectangle([4 * s, 4 * s, (WIDTH - 4) * s, (CLOCK_H - 4) * s], 10 * s, outline=(190, 194, 200),
                              width=s)
        rnd = random.Random(3)
        for sx, sy in ((14, 14), (306, 14), (14, 200), (306, 200)):
            _disp_screw(c, sx, sy, 4.2, rnd.uniform(0, 180))
        dark, light = (36, 38, 42), (190, 194, 200)
        lab = clock_font("sans-cond", 9 * s, True)
        # Hauptzählwerk
        for g, (x, name) in enumerate(zip(self._disp_cnt_groups, ("STUNDEN", "MINUTEN", "SEKUNDEN"))):
            _disp_engrave(c, x + 35, 23, name, lab, dark, light)
            self._disp_cnt_window(c, x, 32, x + 70, 92)
            if g:
                for cy in (54, 70):
                    c.circle(x - 9, cy, 2.3, fill=light)
                    c.circle(x - 9.3, cy - 0.3, 2.1, fill=dark)
        # zweites Zählwerk
        for (x, n), name in zip(self._disp_cnt_small, ("TAG", "KW")):
            _disp_engrave(c, x - 18, 130, name, lab, dark, light)
            self._disp_cnt_window(c, x, 114, x + n * 22 - 2, 146)
        # Typenschild
        _disp_grad(c.img, (66 * s, 158 * s, 254 * s, 202 * s), 3 * s,
                   [(0, (212, 206, 190)), (0.5, (186, 180, 164)), (1, (150, 144, 128))])
        c.d.rounded_rectangle([66 * s, 158 * s, 254 * s, 202 * s], 3 * s, outline=(90, 86, 76), width=s)
        c.rect(70, 162, 74, 198, fill=acc)
        for rx, ry in ((80, 163), (248, 163), (80, 197), (248, 197)):
            c.circle(rx, ry, 1.9, fill=(110, 104, 92))
            c.circle(rx - 0.4, ry - 0.4, 1.1, fill=(230, 226, 214))
        big = clock_font("sans", 13 * s, True)
        tiny = clock_font("sans-cond", 8 * s, True)
        ink, glint = (44, 40, 34), (240, 236, 224)
        _disp_engrave(c, 164, 172, "G19s  ZÄHLWERK", big, ink, glint)
        _disp_engrave(c, 164, 188, "TYP ZW 6-5  ·  24 STD  ·  Nr. 0419", tiny, ink, glint)

    @clock_face("counter", fps=5)
    def face_counter(self, profile):
        t = self._clock_now()
        now, prev = time.localtime(t), time.localtime(math.floor(t) - 1)
        p = self._disp_step(t, 0.4)
        acc = PROFILE_COLOR.get(profile, self.FG)
        img = self._disp_base("counter", acc, (14, 14, 15), lambda c: self._disp_cnt_static(c, acc))
        fmt = "{0.tm_hour:02d}{0.tm_min:02d}{0.tm_sec:02d}"
        a, b = fmt.format(prev), fmt.format(now)
        mods = (3, 10, 6, 10, 6, 10)
        for k in range(6):
            x = self._disp_cnt_groups[k // 2] + (k % 2) * 36
            self._disp_roll(img, x, 32, "big", a[k], b[k], mods[k], p, red=k >= 4)
        small = (f"{prev.tm_yday:03d}" + time.strftime("%V", prev), f"{now.tm_yday:03d}" + time.strftime("%V", now))
        mods = (4, 10, 10, 6, 10)
        k = 0
        for x, n in self._disp_cnt_small:
            for i in range(n):
                self._disp_roll(img, x + i * 22, 114, "small", small[0][k], small[1][k], mods[k], p)
                k += 1
        return self._disp_out(img)


# ═══════════════════════════════════════════════════════════════════════════
# Modul uhr_info
#   Zifferblätter Wortuhr, Terminal, Tagesfortschritt, Ringuhr, Tacho-Uhr.
# ═══════════════════════════════════════════════════════════════════════════

_info_WHITE = (255, 255, 255)
# Blockziffern 3×5 für das Terminal (Zeilen von oben, je 3 Bit)
_info_BLOCKS = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
    ":": ("0", "1", "0", "1", "0"),
}
_info_PHOSPHOR = {"green": (70, 255, 120), "amber": (255, 176, 40), "white": (225, 235, 245), "blue": (90, 180, 255)}


def _info_hsv(color, dh=0.0, ds=1.0, dv=1.0):
    """Farbton um dh drehen, Sättigung und Helligkeit mit ds/dv skalieren."""
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in color])
    return tuple(round(x * 255) for x in colorsys.hsv_to_rgb((h + dh) % 1, min(1, s * ds), min(1, v * dv)))


def _info_pct(p):
    """Anteil als Prozent mit deutschem Komma: 0.396 → „39,6 %“."""
    return f"{math.floor(p * 1000 + 1e-9) / 10:.1f}".replace(".", ",") + " %"      # abgerundet: 100 % erst am Ende


def _info_span(t, start, end):
    """Anteil von t zwischen zwei lokalen Zeitpunkten (Tupel für mktime, Sommerzeit wird beachtet)."""
    a, b = time.mktime(start[:6] + (0, 0, -1)), time.mktime(end[:6] + (0, 0, -1))
    return min(1.0, max(0.0, (t - a) / (b - a)))


class InfoFaces:
    @staticmethod
    def _info_font(size, bold=False, mono=False, scale=CLOCK_SS):
        """DejaVu Sans bzw. Sans Mono; size in Displaypixeln, scale = Vergrößerung der Fläche."""
        return clock_font("mono" if mono else "sans", round(size * scale), bold)

    def _info_out(self, arr):
        """Fläche (numpy, CLOCK_H×WIDTH×3) ins Displaybild setzen."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, 0))
        return img

    # --- Wortuhr -------------------------------------------------------------- #
    _info_GRID = ["ESKISTAFÜNF", "ZEHNZWANZIG", "DREIVIERTEL", "TGNACHVORJM", "HALBXZWÖLFP",
                  "ZWEINSIEBEN", "KDREIRHFÜNF", "ELFNEUNVIER", "WACHTZEHNRS", "BSECHSFMUHR"]
    _info_WORD = {"ES": (0, 0, 2), "IST": (0, 3, 3), "M5": (0, 7, 4), "M10": (1, 0, 4), "M20": (1, 4, 7),
                  "VIERTEL": (2, 4, 7), "NACH": (3, 2, 4), "VOR": (3, 6, 3), "HALB": (4, 0, 4),
                  "EIN": (5, 2, 3), "UHR": (9, 8, 3)}                # (Zeile, Spalte, Länge)
    _info_HOUR = [None, (5, 2, 4), (5, 0, 4), (6, 1, 4), (7, 7, 4), (6, 7, 4), (9, 1, 5), (5, 5, 6),
                  (8, 1, 4), (7, 3, 4), (8, 5, 4), (7, 0, 3), (4, 5, 5)]    # EINS … ZWÖLF
    _info_MINW = {0: [], 5: ["M5", "NACH"], 10: ["M10", "NACH"], 15: ["VIERTEL", "NACH"], 20: ["M20", "NACH"],
                  25: ["M5", "VOR", "HALB"], 30: ["HALB"], 35: ["M5", "NACH", "HALB"], 40: ["M20", "VOR"],
                  45: ["VIERTEL", "VOR"], 50: ["M10", "VOR"], 55: ["M5", "VOR"]}
    _info_CW, _info_CH, _info_X0, _info_Y0 = 24, 19.4, 28, 10      # Rasterzelle und Ursprung
    _info_DOTS = [(13, 9), (307, 9), (307, 205), (13, 205)]       # Minute 1–4: im Uhrzeigersinn ab oben links

    def _info_words_lit(self, hour, minute):
        """Leuchtende Rasterzellen {(zeile, spalte)} für die Uhrzeit."""
        m5 = minute - minute % 5
        h = (hour + (1 if m5 >= 25 else 0)) % 12 or 12
        spans = [self._info_WORD[w] for w in ["ES", "IST"] + self._info_MINW[m5]]
        if m5 == 0:
            spans += [self._info_WORD["EIN"] if h == 1 else self._info_HOUR[h], self._info_WORD["UHR"]]
        else:
            spans.append(self._info_HOUR[h])
        return {(r, c + k) for r, c, n in spans for k in range(n)}

    def _info_words_draw(self, d, cells, dots, fill, font):
        for r, row in enumerate(self._info_GRID):
            for c, ch in enumerate(row):
                if cells is None or (r, c) in cells:
                    d.text((self._info_X0 + (c + 0.5) * self._info_CW, self._info_Y0 + (r + 0.5) * self._info_CH),
                           ch, font=font, fill=fill, anchor="mm")
        for x, y in self._info_DOTS[:dots]:
            d.ellipse([x - 2.6, y - 2.6, x + 2.6, y + 2.6], fill=fill)

    def _info_words_plate(self, font):
        """Frontplatte mit dunklen Buchstaben (numpy-Feld)."""
        base = Image.new("RGB", (WIDTH, CLOCK_H), self.BG)
        yy, xx = np.mgrid[0:CLOCK_H, 0:WIDTH]
        v = 1 - 0.55 * (((xx - CLOCK_CX) / 200) ** 2 + ((yy - CLOCK_CY) / 150) ** 2)
        arr = np.asarray(base, np.float32) * np.clip(v, 0.5, 1.2)[..., None] + np.array([4, 4, 6])
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        self._info_words_draw(ImageDraw.Draw(base), None, 4, (26, 29, 37), font)
        return np.asarray(base, np.float32)

    @clock_face("words", fps=1)
    def face_words(self, profile):
        now = time.localtime(self._clock_now())
        col = self._ccolor(self._copt("words")["color"], profile)
        font = self._info_font(15, True, scale=1)
        plate = self._clock_cache("info_words", self.BG, lambda: self._info_words_plate(font))
        mask = Image.new("L", (WIDTH, CLOCK_H), 0)
        self._info_words_draw(ImageDraw.Draw(mask), self._info_words_lit(now.tm_hour, now.tm_min),
                              now.tm_min % 5, 255, font)
        m = np.asarray(mask, np.float32)[..., None] / 255
        glow = np.asarray(mask.filter(ImageFilter.GaussianBlur(4)), np.float32)[..., None] / 255
        core = np.array(mix(col, _info_WHITE, 0.35), np.float32)
        out = plate * (1 - m) + core * m + np.array(col, np.float32) * glow * 0.8
        return self._info_out(out)

    # --- Terminal ------------------------------------------------------------- #
    @staticmethod
    def _info_term_static(col):
        """Röhrenbildschirm: Gehäuse, gewölbt wirkender Schirm, Zeilenraster (als numpy-Felder)."""
        s = CLOCK_SS
        img = Image.new("RGB", (WIDTH * s, CLOCK_H * s), (22, 23, 26))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1 * s, 1 * s, (WIDTH - 1) * s, (CLOCK_H - 1) * s], 10 * s, fill=(34, 35, 39))
        d.rounded_rectangle([4 * s, 4 * s, (WIDTH - 4) * s, (CLOCK_H - 4) * s], 16 * s, fill=(12, 12, 14))
        d.rounded_rectangle([6 * s, 6 * s, (WIDTH - 6) * s, (CLOCK_H - 6) * s], 15 * s, fill=(255, 255, 255))
        img = img.resize((WIDTH, CLOCK_H), Image.LANCZOS)
        a = np.asarray(img, np.float32)
        screen = np.clip((a.min(axis=2) - 40) / 215, 0, 1)[..., None]        # 1 = Schirmfläche
        yy, xx = np.mgrid[0:CLOCK_H, 0:WIDTH]
        vign = np.clip(1 - 0.9 * (((xx - CLOCK_CX) / 175) ** 4 + ((yy - CLOCK_CY) / 125) ** 4), 0.25, 1)[..., None]
        glass = np.array(mix((5, 7, 6), col, 0.06), np.float32) * vign * 1.3
        bg = a * (1 - screen) + glass * screen
        scan = 1 - 0.32 * (yy % 2)[..., None] * screen
        return bg, scan, vign * screen

    def _info_term_big(self, d, x, y, txt, b):
        """Uhrzeit aus 3×5-Blockziffern (Kantenlänge b)."""
        for ch in txt:
            rows = _info_BLOCKS[ch]
            for r, bits in enumerate(rows):
                for k, bit in enumerate(bits):
                    if bit == "1":
                        d.rectangle([x + k * b, y + r * b, x + k * b + b - 2, y + r * b + b - 2], fill=255)
            x += len(rows[0]) * b + b

    @clock_face("terminal", fps=2)
    def face_terminal(self, profile):
        t = self._clock_now()
        now = time.localtime(t)
        col = _info_PHOSPHOR.get(self._copt("terminal")["color"], _info_PHOSPHOR["green"])
        bg, scan, screen = self._clock_cache("info_term", col, lambda: self._info_term_static(col))
        f, fb = self._info_font(12, mono=True, scale=1), self._info_font(12, True, True, scale=1)
        mask = Image.new("L", (WIDTH, CLOCK_H), 0)
        d = ImageDraw.Draw(mask)
        cw = fb.getlength("0")
        prompt = "g19s@kubuntu:~$ "
        x0, lh = 16, 16
        y = 22

        def cmd(y, text):
            d.text((x0, y), prompt, font=fb, fill=255, anchor="ls")
            d.text((x0 + cw * len(prompt), y), text, font=f, fill=215, anchor="ls")

        date = (f"{WEEKDAY_DE[now.tm_wday]} {now.tm_mday}. {MONTH_3[now.tm_mon - 1].capitalize()} "
                f"{time.strftime('%H:%M:%S %Z %Y', now)}")
        cmd(y, "date")
        d.text((x0, y + lh), date, font=f, fill=170, anchor="ls")
        cmd(y + 2.25 * lh, "uhr")
        self._info_term_big(d, x0 + 2, y + 2.25 * lh + 9, time.strftime("%H:%M:%S", now), 8)
        days = 366 if now.tm_year % 4 == 0 and (now.tm_year % 100 or now.tm_year % 400 == 0) else 365
        yi = y + 2.25 * lh + 9 + 40 + 14
        d.text((x0, yi), f"KW {time.strftime('%V', now)} · Tag {now.tm_yday}/{days}", font=f, fill=170, anchor="ls")
        cmd(yi + 1.25 * lh, "date +%s")
        d.text((x0, yi + 2.25 * lh), str(int(t)), font=f, fill=170, anchor="ls")
        cmd(yi + 3.5 * lh, "")
        if t % 1 < 0.5:                                     # blinkender Block-Cursor
            cx = x0 + cw * len(prompt)
            d.rectangle([cx, yi + 3.5 * lh - 11, cx + cw - 1, yi + 3.5 * lh + 2], fill=235)
        m = np.asarray(mask, np.float32)[..., None] / 255
        glow = np.asarray(mask.filter(ImageFilter.GaussianBlur(2.2)), np.float32)[..., None] / 255
        c = np.array(col, np.float32)
        out = bg + (mix(col, _info_WHITE, 0.3) - bg) * m * 0.92 + c * glow * 0.75 * screen
        return self._info_out(out * scan)

    # --- Tagesfortschritt ----------------------------------------------------- #
    def _info_bar(self, c, x0, y0, x1, h, p, col, ticks):
        """Waagrechter Balken mit Spur, Verlauf bis zum Stand p und Teilstrichen darunter."""
        s = CLOCK_SS
        track = mix(col, self.BG, 0.84)
        c.d.rounded_rectangle([x0 * s, y0 * s, x1 * s, (y0 + h) * s], h * s / 2, fill=track)
        w = max(h, (x1 - x0) * p) if p > 0 else 0
        if w:
            W, H = round(w * s), round(h * s)
            ramp = np.linspace(0, 1, W, dtype=np.float32)[None, :, None] ** 0.8
            a, b = np.array(mix(col, self.BG, 0.55), np.float32), np.array(mix(col, _info_WHITE, 0.3), np.float32)
            grad = a + (b - a) * ramp
            shade = np.linspace(1.25, 0.8, H, dtype=np.float32)[:, None, None]          # leichte Wölbung
            grad = np.clip(grad * shade, 0, 255).astype(np.uint8)
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], H / 2, fill=255)
            c.img.paste(Image.fromarray(np.ascontiguousarray(np.broadcast_to(grad, (H, W, 3)))),
                        (round(x0 * s), round(y0 * s)), m)
            c.circle(x0 + w - h / 2, y0 + h / 2, h / 2 - 1.8, fill=mix(col, _info_WHITE, 0.7))   # Leuchtpunkt
        for k in range(1, ticks):
            x = x0 + (x1 - x0) * k / ticks
            c.rect(x - 0.3, y0 + h + 2, x + 0.3, y0 + h + 4, fill=(60, 66, 80))

    @clock_face("progress", fps=1)
    def face_progress(self, profile):
        t = self._clock_now()
        now = time.localtime(t)
        col = PROFILE_COLOR.get(profile, self.FG)
        c = self._clock_canvas("info_progress", self.BG, lambda c: None)
        s = CLOCK_SS
        y, mo, dd, hh = now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour
        big, secf = self._info_font(30, True), self._info_font(15, True)
        c.d.text((14 * s, 40 * s), time.strftime("%H:%M", now), font=big, fill=self.FG, anchor="ls")
        xw = 14 + big.getlength(time.strftime("%H:%M", now)) / s
        c.d.text(((xw + 3) * s, 40 * s), time.strftime("%S", now), font=secf, fill=mix(col, _info_WHITE, 0.45),
                 anchor="ls")
        c.d.text((306 * s, 23 * s), WEEKDAYS[now.tm_wday], font=self._info_font(13, True), fill=self.FG, anchor="rs")
        c.d.text((306 * s, 39 * s), f"{dd}. {MONTHS[mo - 1]} {y}", font=self._info_font(11), fill=self.DIM,
                 anchor="rs")
        c.rect(14, 50, 306, 50.6, fill=(40, 44, 56))
        mdays = (time.mktime((y + (mo == 12), mo % 12 + 1, 1, 12, 0, 0, 0, 0, -1))
                 - time.mktime((y, mo, 1, 12, 0, 0, 0, 0, -1))) / 86400
        ydays = 366 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 365
        rows = [
            ("Stunde", f"{hh:02d}–{(hh + 1) % 24:02d} Uhr", (now.tm_min * 60 + now.tm_sec + t % 1) / 3600, 4),
            ("Tag", WEEKDAYS[now.tm_wday], _info_span(t, (y, mo, dd, 0, 0, 0, 0), (y, mo, dd + 1, 0, 0, 0, 0)), 4),
            (f"Woche (KW {time.strftime('%V', now)})", "Mo–So",
             _info_span(t, (y, mo, dd - now.tm_wday, 0, 0, 0, 0), (y, mo, dd - now.tm_wday + 7, 0, 0, 0, 0)), 7),
            (MONTHS[mo - 1], f"Tag {dd}/{round(mdays)}",
             _info_span(t, (y, mo, 1, 0, 0, 0, 0), (y + (mo == 12), mo % 12 + 1, 1, 0, 0, 0, 0)), round(mdays)),
            (str(y), f"Tag {now.tm_yday}/{ydays}", _info_span(t, (y, 1, 1, 0, 0, 0, 0), (y + 1, 1, 1, 0, 0, 0, 0)), 12),
        ]
        lab, sub, pf = self._info_font(11, True), self._info_font(9), self._info_font(11, True)
        for i, (label, detail, p, ticks) in enumerate(rows):
            yb = 70 + i * 29
            c.d.text((14 * s, yb * s), label, font=lab, fill=self.FG, anchor="ls")
            c.d.text((14 * s + lab.getlength(label) + 6 * s, yb * s), detail, font=sub, fill=self.DIM, anchor="ls")
            c.d.text((306 * s, yb * s), _info_pct(p), font=pf, fill=mix(col, _info_WHITE, 0.5), anchor="rs")
            self._info_bar(c, 14, yb + 4, 306, 9, p, col, ticks)
        return self._clock_finish(c)

    # --- Ringuhr -------------------------------------------------------------- #
    def _info_arc(self, c, cx, cy, r, w, deg0, deg1, fill):
        """Bogen (Mittenradius r, Breite w) von deg0 bis deg1 (0 = 12 Uhr)."""
        s, R = CLOCK_SS, r + w / 2
        c.d.arc([(cx - R) * s, (cy - R) * s, (cx + R) * s, (cy + R) * s], deg0 - 90, deg1 - 90, fill=fill,
                width=round(w * s))

    def _info_ring_colors(self, col):
        """Stunden-, Minuten-, Sekundenfarbe: benachbarte Farbtöne der Ebenenfarbe."""
        return (_info_hsv(col, 0.0, 0.95, 1.0), _info_hsv(col, -0.07, 0.8, 1.15), _info_hsv(col, 0.09, 0.7, 1.2))

    _info_RINGS = ((62, 12, 12), (80, 12, 60), (98, 11, 60))      # Stunden, Minuten, Sekunden: Radius, Breite, Teilung

    def _info_rings_dial(self, c, col):
        cx, cy = CLOCK_CX, CLOCK_CY
        for (r, w, n), rc in zip(self._info_RINGS, self._info_ring_colors(col)):
            self._info_arc(c, cx, cy, r, w + 2, 0, 360, (16, 18, 24))
            self._info_arc(c, cx, cy, r, w, 0, 360, mix(rc, self.BG, 0.86))
            for k in range(n):
                big = n == 12 or k % 5 == 0
                c.radial(cx, cy, r - w / 2 + (1 if big else 3), r + w / 2 - (1 if big else 3), k * 360 / n,
                         0.9 if big else 0.5, mix(rc, self.BG, 0.7))
        f = self._cfonts
        cols = self._info_ring_colors(col)
        for i, (name, rc) in enumerate((("STD", cols[0]), ("MIN", cols[1]), ("SEK", cols[2]))):
            c.circle(12, 78 + i * 26, 3.5, fill=rc)
            c.d.text((20 * CLOCK_SS, (78 + i * 26) * CLOCK_SS), name, font=f["tiny"], fill=self.DIM, anchor="lm")

    @clock_face("rings", fps=1)
    def face_rings(self, profile):
        col = PROFILE_COLOR.get(profile, self.FG)
        c = self._clock_canvas(("info_rings", col), self.BG, lambda c: self._info_rings_dial(c, col))
        cx, cy, s = CLOCK_CX, CLOCK_CY, CLOCK_SS
        now = time.localtime(self._clock_now())
        vals = ((now.tm_hour % 12 + now.tm_min / 60) / 12, (now.tm_min + now.tm_sec / 60) / 60, now.tm_sec / 60)
        for (r, w, n), rc, v in zip(self._info_RINGS, self._info_ring_colors(col), vals):
            deg = v * 360
            if deg > 0.5:
                self._info_arc(c, cx, cy, r, w + 3, 0, deg, mix(rc, self.BG, 0.72))     # Schein
                self._info_arc(c, cx, cy, r, w, 0, deg, rc)
                for k in range(n):                                                      # Teilung auf dem Bogen
                    if 0 < k * 360 / n < deg - 2:
                        big = n == 12 or k % 5 == 0
                        c.radial(cx, cy, r - w / 2, r + w / 2, k * 360 / n, 0.9 if big else 0.45, mix(rc, self.BG, 0.35))
            x0, y0 = [v / s for v in c.pt(cx, cy, r, 0)]
            c.circle(x0, y0, w / 2, fill=rc if deg > 0.5 else mix(rc, self.BG, 0.4))
            x1, y1 = [v / s for v in c.pt(cx, cy, r, deg)]
            c.circle(x1, y1, w / 2 + 1, fill=mix(rc, self.BG, 0.5))
            c.circle(x1, y1, w / 2, fill=rc)
            c.circle(x1, y1, w / 2 - 3, fill=mix(rc, _info_WHITE, 0.6))                 # heller Kopf
        c.text(cx, cy - 9, time.strftime("%H:%M", now), self._info_font(27, True), self.FG)
        c.text(cx, cy + 15, time.strftime(":%S", now), self._info_font(13, True), self._info_ring_colors(col)[2])
        c.text(cx, cy + 31, f"{WEEKDAY_DE[now.tm_wday]} {now.tm_mday:02d}.{now.tm_mon:02d}.", self._cfonts["tiny"],
               self.DIM)
        f = self._cfonts
        c.text(296, 86, "KW", f["tiny"], self.DIM)
        c.text(296, 102, time.strftime("%V", now), f["side"], self.FG)
        c.text(296, 128, str(now.tm_year), f["tiny"], self.DIM)
        return self._clock_finish(c)

    # --- Tacho-Uhr ------------------------------------------------------------ #
    _info_GL, _info_GR, _info_GY, _info_GRAD = 82, 238, 92, 73     # Mittelpunkte, Höhe, Radius

    def _info_chrome(self, c, cx, cy, r_out, r_in):
        """Chromring mit senkrechtem Glanzverlauf."""
        s = CLOCK_SS
        x0, y0, n = round((cx - r_out) * s), round((cy - r_out) * s), round(2 * r_out * s) + 1
        yy = np.linspace(0, 1, n, dtype=np.float32)[:, None]
        xx = np.linspace(0, 1, n, dtype=np.float32)[None, :]
        v = np.interp(yy, [0, 0.3, 0.48, 0.56, 0.75, 1], [240, 170, 70, 110, 200, 120]) + 18 * np.sin(xx * math.pi)
        arr = np.clip(np.stack([v, v + 2, v + 8], axis=2), 0, 255).astype(np.uint8)
        m = Image.new("L", (n, n), 0)
        md = ImageDraw.Draw(m)
        md.ellipse([0, 0, n - 1, n - 1], fill=255)
        k = (r_out - r_in) * s
        md.ellipse([k, k, n - 1 - k, n - 1 - k], fill=0)
        c.img.paste(Image.fromarray(arr), (x0, y0), m)

    @staticmethod
    def _info_gdeg(v, vmax):
        return -135 + 270 * v / vmax

    def _info_gauge_dial(self, c, cx, cy, vmax, major, minor, labels, red, unit, col):
        f, R = self._cfonts, self._info_GRAD
        c.circle(cx, cy, R + 4, fill=(6, 6, 8))
        self._info_chrome(c, cx, cy, R + 3, R - 3)
        c.circle(cx, cy, R - 3, fill=(4, 4, 6))
        for r in range(round(R - 4), 0, -2):                     # Zifferblatt, zur Mitte heller
            c.circle(cx, cy, r, fill=mix((30, 32, 38), (12, 13, 16), r / (R - 4)))
        self._info_arc(c, cx, cy, R - 7, 1.2, -135, 135, mix(col, (0, 0, 0), 0.35))      # Leuchtring
        if red:
            self._info_arc(c, cx, cy, R - 12, 5, self._info_gdeg(red, vmax), 135, (205, 30, 30))
        n = round(vmax / minor)
        for k in range(n + 1):
            v = k * minor
            deg = self._info_gdeg(v, vmax)
            is_major = abs(v / major - round(v / major)) < 1e-6
            tc = (235, 60, 50) if red and v >= red else (236, 238, 242)
            c.radial(cx, cy, R - (19 if is_major else 14), R - 9, deg, 1.8 if is_major else 0.8, tc)
        for v in labels:
            x, y = [p / CLOCK_SS for p in c.pt(cx, cy, R - 29, self._info_gdeg(v, vmax))]
            c.text(x, y, str(v), f["small"], (235, 60, 50) if red and v >= red else (236, 238, 242))
        c.text(cx, cy + 25, unit, f["tiny"], (150, 156, 170))

    def _info_gauge_static(self, c, col):
        s = CLOCK_SS
        h, w = CLOCK_H * s, WIDTH * s                            # Carbon-Geflecht
        yy, xx = np.mgrid[0:h, 0:w]
        cell = 4 * s
        a = ((xx // cell) + (yy // cell)) % 2
        ph = np.where(a == 0, (xx % cell) / cell, (yy % cell) / cell)
        v = 17 + 10 * np.sin(ph * math.pi)
        v *= np.clip(1.15 - 0.6 * (((xx / w - 0.5) * 1.6) ** 2 + ((yy / h - 0.45) * 1.4) ** 2), 0.4, 1.2)
        c.img.paste(Image.fromarray(np.stack([v, v, v * 1.08], axis=2).clip(0, 255).astype(np.uint8)), (0, 0))
        cy = self._info_GY
        self._info_gauge_dial(c, self._info_GL, cy, 24, 2, 0.5, range(0, 25, 2), 22, "STD", col)
        self._info_gauge_dial(c, self._info_GR, cy, 60, 5, 1, range(0, 61, 10), None, "MIN", col)
        c.d.rounded_rectangle([66 * s, 174 * s, 254 * s, 208 * s], 7 * s, fill=(70, 72, 78))    # LC-Display
        c.d.rounded_rectangle([67.5 * s, 175.5 * s, 252.5 * s, 206.5 * s], 6 * s, fill=(8, 9, 11))
        c.d.rounded_rectangle([70 * s, 178 * s, 250 * s, 204 * s], 4 * s, fill=mix(col, (4, 5, 7), 0.9))
        for x in (116, 196):
            c.rect(x, 181, x + 0.5, 201, fill=mix(col, (4, 5, 7), 0.7))

    def _info_needle(self, c, cx, cy, deg):
        R, red = self._info_GRAD, (255, 64, 24)
        prof = [(-14, 4.2), (0, 3.6), (R - 14, 1.3)]
        for grow, t in ((4.5, 0.86), (2.8, 0.7), (1.4, 0.45)):     # Glühen
            c.hand(cx, cy, deg, [(r - grow / 2, w + grow) for r, w in prof[:2]] + [(R - 14 + grow / 2, 1.3 + grow)],
                   mix(red, (14, 15, 18), t))
        c.hand(cx, cy, deg, prof, red)
        c.hand(cx, cy, deg, [(0, 1), (R - 18, 0.5)], (255, 190, 150))
        c.circle(cx, cy, 8, fill=(26, 27, 31), outline=(150, 154, 162), width=1.2)
        c.circle(cx, cy, 3, fill=(60, 62, 68))

    @clock_face("gauge", fps=1)
    def face_gauge(self, profile):
        col = PROFILE_COLOR.get(profile, self.FG)
        c = self._clock_canvas(("info_gauge", col), self.BG, lambda c: self._info_gauge_static(c, col))
        now = time.localtime(self._clock_now())
        f, cy, s = self._cfonts, self._info_GY, CLOCK_SS
        hours = now.tm_hour + now.tm_min / 60 + now.tm_sec / 3600
        mins = now.tm_min + now.tm_sec / 60
        lcd = mix(col, _info_WHITE, 0.55)
        for cx, val, txt in ((self._info_GL, hours / 24, f"{now.tm_hour:02d}"),
                             (self._info_GR, mins / 60, f"{now.tm_min:02d}")):
            c.text(cx, cy + 42, txt, self._info_font(17, True), lcd)
            self._info_needle(c, cx, cy, -135 + 270 * val)
        seg = self._info_font(15, True, True)
        c.d.text((76 * s, 191 * s), f"{now.tm_sec:02d}", font=seg, fill=lcd, anchor="lm")
        c.d.text((96 * s, 192 * s), "SEK", font=f["tiny"], fill=mix(col, _info_WHITE, 0.2), anchor="lm")
        c.text(156, 191, f"{WEEKDAY_DE[now.tm_wday]} {now.tm_mday:02d}.{now.tm_mon:02d}.{now.tm_year % 100:02d}",
               self._info_font(11, True, True), lcd)
        c.d.text((203 * s, 191 * s), "TAG", font=f["tiny"], fill=mix(col, _info_WHITE, 0.2), anchor="lm")
        for i, ch in enumerate(f"{now.tm_yday:03d}"):             # Zählwerk wie ein Kilometerzähler
            x = 223 + i * 9
            last = i == 2
            c.rect(x, 183, x + 8, 199, fill=(236, 236, 232) if last else (14, 14, 16), outline=(90, 92, 98), width=0.6)
            c.text(x + 4.2, 191.3, ch, self._info_font(11, True, True), (20, 20, 22) if last else (236, 238, 242))
        return self._clock_finish(c)


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_makros
#   Displayseite „Makros“: Belegung der zwölf G-Tasten in der aktiven Ebene.
# ═══════════════════════════════════════════════════════════════════════════

class MacrosPage:
    @page("macros")
    def page_macros(self, profile, macros):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = PROFILE_COLOR.get(profile, self.FG)
        if self.profile_name:
            name_font = self.f_big if d.textlength(f"{self.profile_name} · {profile}", font=self.f_big) <= WIDTH - 24 else self.f_title
            suffix = f" · {profile}"
            name = self._fit(d, self.profile_name, name_font, WIDTH - 24 - d.textlength(suffix, font=name_font))
            d.text((12, 8 if name_font is self.f_big else 12), name + suffix, font=name_font, fill=color)
        else:
            d.text((12, 8), f"Makros {profile}", font=self.f_big, fill=color)
        profile_macros = macros.get(profile, {}) if isinstance(macros, dict) else {}
        col_w = (WIDTH - 24) // 2
        for i in range(12):
            gkey = f"G{i + 1}"
            col, row = divmod(i, 6)
            x = 12 + col * (col_w + 8) - (4 if col else 0)
            y = 46 + row * 28
            m = profile_macros.get(gkey)
            d.text((x, y), gkey, font=self.f_small_b, fill=self.FG)
            if isinstance(m, dict) and entry_label(m, self.settings):
                label = self._fit(d, entry_label(m, self.settings), self.f_small, col_w - 48)
                d.text((x + 42, y), label, font=self.f_small, fill=self.FG)
            else:
                d.text((x + 42, y), f"F{FKEY_BASE + i}", font=self.f_small, fill=self.DIM)
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_musik
#   Displayseite „Musik“: aktueller Titel mit Cover, Fortschritt bzw. LIVE beim Radio.
# ═══════════════════════════════════════════════════════════════════════════

class MusicPage:
    @staticmethod
    def _fmt_time(us):
        s = int(us // 1_000_000)
        return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"

    @page("music")
    def page_music(self, profile, macros):
        info, cover, bg, error = self.media.snapshot() if self.media else (None, None, None, None)
        img = bg.copy() if info and bg is not None else Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = PROFILE_COLOR.get(profile, self.FG)

        if not info:
            self._center(d, 34, "♪", self.f_huge, (60, 66, 84))
            self._center(d, 132, "Keine Wiedergabe", self.f_big, self.FG)
            self._center(d, 170, error or "Spotify, Elisa, VLC, Browser …", self.f_small, self.DIM)
            return img

        # Cover
        size = MediaWatcher.COVER_SIZE
        x0, y0 = 12, 12
        if cover is not None:
            d.rectangle([x0 - 1, y0 - 1, x0 + size, y0 + size], fill=(0, 0, 0))
            img.paste(cover, (x0, y0))
        else:
            d.rounded_rectangle([x0, y0, x0 + size, y0 + size], radius=10, fill=(30, 34, 48))
            w = d.textlength("♪", font=self.f_huge)
            d.text((x0 + (size - w) / 2, y0 + 16), "♪", font=self.f_huge, fill=(80, 88, 110))

        # Texte
        tx = x0 + size + 12
        tw = WIDTH - tx - 10
        y = 12
        title = info["title"] or "Unbekannter Titel"
        font, lh = self.f_title, 24
        if any(d.textlength(w, font=font) > tw for w in title.split()):
            font, lh = self.f_title_s, 19   # sehr lange Wörter: kleinere Schrift
        for line in self._wrap(d, title, font, tw, 3):
            d.text((tx, y), line, font=font, fill=self.FG)
            y += lh
        y += 6
        if info["artist"]:
            d.text((tx, y), self._fit(d, info["artist"], self.f_small, tw), font=self.f_small, fill=color)
            y += 20
        second = info.get("station") or info["album"]
        if second:
            d.text((tx, y), self._fit(d, second, self.f_small, tw), font=self.f_small, fill=self.DIM)
        d.text((tx, y0 + size - 16), self._fit(d, info["player"].capitalize(), self.f_tiny, tw),
               font=self.f_tiny, fill=self.DIM)

        # Fortschritt
        pos, length = info["position"], info["length"]
        if info["status"] == "Playing":
            pos += (time.monotonic() - info["fetched"]) * 1_000_000
        if length:
            pos = min(pos, length)
        by = 160
        d.rounded_rectangle([12, by, WIDTH - 12, by + 6], radius=3,
                            fill=(60, 66, 84) if length else color)
        if length:
            fx = 12 + int((WIDTH - 24) * pos / length)
            if fx > 16:
                d.rounded_rectangle([12, by, fx, by + 6], radius=3, fill=color)
            d.text((12, by + 14), self._fmt_time(pos), font=self.f_small, fill=self.FG)
        else:
            d.ellipse([12, by + 19, 22, by + 29], fill=(235, 50, 50))
            d.text((28, by + 14), "LIVE", font=self.f_small_b, fill=self.FG)
        if length:
            t = self._fmt_time(length)
            d.text((WIDTH - 12 - d.textlength(t, font=self.f_small), by + 14), t,
                   font=self.f_small, fill=self.FG)

        # Status-Symbol (Play/Pause) mittig
        cx, cy = WIDTH // 2, by + 24
        if info["status"] == "Playing":
            d.rectangle([cx - 8, cy - 9, cx - 3, cy + 9], fill=self.FG)
            d.rectangle([cx + 3, cy - 9, cx + 8, cy + 9], fill=self.FG)
        else:
            d.polygon([(cx - 7, cy - 10), (cx - 7, cy + 10), (cx + 10, cy)], fill=self.FG)
        return img


@page_keys("music")
def keys_music(app, pressed):
    """OK = Play/Pause, Hoch/Runter = Titel zurück/vor, MENU = Senderliste, BACK = Radio aus."""
    if pressed & LKEY_BITS["MENU"]:
        items = app.station_items()
        if items:
            cur = app.radio.current()
            pos = next((i for i, it in enumerate(items) if cur and it.get("station", {}).get("url") == cur["url"]), 0)
            app.menu = StationMenu(pos)
            app.flash = None
        else:
            app.show("Radio", ["keine Sender angelegt"], PROFILE_COLOR[app.layer], 2)
        app.next_draw = 0
        return True
    for bit, action in ((LKEY_BITS["OK"], "play-pause"), (LKEY_BITS["UP"], "previous"), (LKEY_BITS["DOWN"], "next")):
        if pressed & bit:
            threading.Thread(target=app.media.control, args=(action,), daemon=True).start()
            app.next_draw = time.monotonic() + 0.3
    if pressed & LKEY_BITS["BACK"] and app.radio.playing:
        app.radio.stop()
        app.media.wake.set()
        app.next_draw = time.monotonic() + 0.3
    app.nav_keys(pressed, LKEY_BITS["RIGHT"], LKEY_BITS["LEFT"])
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_bilder
#   Displayseite „Bilder“: Diashow (Piwigo oder Ordner) mit Titel, Pause- und Lieblingsbild-Anzeige.
# ═══════════════════════════════════════════════════════════════════════════

class SlidesPage:
    @page("slides")
    def page_slides(self, profile, macros):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        if self.slideshow is None:
            snap = {"image": None, "configured": False, "status": "", "error": None}
        else:
            self.slideshow.touch()
            snap = self.slideshow.snapshot()
        if snap["image"] is not None:
            img.paste(snap["image"], (0, 0))
            cfg = (self.settings or {}).get("slideshow") or {}
            top = []
            if snap["error"]:
                top.append("⚠ " + snap["error"])
            elif cfg.get("caption", True) and snap["name"]:
                top.append(snap["name"])
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            if top or snap["paused"]:
                od.rectangle([0, 0, WIDTH, 26], fill=(0, 0, 0, 150))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            d = ImageDraw.Draw(img)
            right = f"{snap['index']}/{snap['count']}"
            rw = d.textlength(right, font=self.f_tiny)
            if top:
                d.text((8, 5), self._fit(d, top[0], self.f_small, WIDTH - rw - 40), font=self.f_small,
                       fill=(255, 120, 120) if snap["error"] else self.FG)
                d.text((WIDTH - rw - 8, 7), right, font=self.f_tiny, fill=self.DIM)
            if snap["paused"]:
                x = WIDTH - rw - 26 if top else WIDTH - 22
                d.rectangle([x, 7, x + 4, 19], fill=self.FG)
                d.rectangle([x + 8, 7, x + 12, 19], fill=self.FG)
            if snap.get("id") is not None and self.slideshow and str(snap["id"]) in self.slideshow.fav_ids():
                self._heart(d, 10, HEIGHT - 50, 22, (235, 60, 90))
            return img
        d = ImageDraw.Draw(img)
        self._center(d, 30, "▣", self.f_huge, (60, 66, 84))
        if not snap["configured"]:
            self._center(d, 128, "Diashow", self.f_big, self.FG)
            self._center(d, 166, "In der G19s-Verwaltung einrichten", self.f_small, self.DIM)
        elif snap["error"]:
            self._center(d, 128, "Piwigo-Fehler", self.f_big, (235, 90, 90))
            for i, line in enumerate(self._wrap(d, snap["error"], self.f_small, WIDTH - 24, 2)):
                self._center(d, 164 + i * 19, line, self.f_small, self.DIM)
        else:
            self._center(d, 140, snap["status"] or "Lade Bilder …", self.f_mid, self.FG)
        return img


@page_keys("slides")
def keys_slides(app, pressed):
    """OK = Pause/Weiter, Hoch/Runter = Bild zurück/vor, BACK = Lieblingsbild, MENU = Albenauswahl."""
    sl = app.slideshow
    if pressed & LKEY_BITS["MENU"]:
        cfg = sl.cfg()
        if cfg.get("source") == "folder":
            app.show("Alben", ["Auswahl nur für", "Piwigo-Alben"], PROFILE_COLOR[app.layer], 2)
        elif not cfg.get("url"):
            app.show("Alben", ["Piwigo zuerst in der", "Verwaltung einrichten"], PROFILE_COLOR[app.layer], 2.5)
        else:
            sl.request_albums()
            selected = set()
            for a in cfg.get("albums") or []:
                try:
                    selected.add(int(a))
                except (TypeError, ValueError):
                    pass
            app.menu = AlbumMenu(selected)
            app.flash = None
        app.next_draw = 0
        return True
    for bit, action in ((LKEY_BITS["OK"], "toggle"), (LKEY_BITS["UP"], "previous"), (LKEY_BITS["DOWN"], "next")):
        if pressed & bit:
            sl.command(action)
            app.next_draw = time.monotonic() + (0.05 if action == "toggle" else 0.4)
    if pressed & LKEY_BITS["BACK"]:
        fav = sl.favorite_current()
        if fav is not None:
            app.log(f"Lieblingsbild {'gemerkt' if fav else 'entfernt'}: {sl.snapshot()['name']}")
            app.show("♥ Lieblingsbild" if fav else "Lieblingsbild", ["gemerkt" if fav else "entfernt"],
                     (235, 60, 90) if fav else PROFILE_COLOR[app.layer], 1.2)
    app.nav_keys(pressed, LKEY_BITS["RIGHT"], LKEY_BITS["LEFT"])
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_wetter
#   Displayseite „Wetter“: aktuelles Wetter und die nächsten Tage (Open-Meteo) mit gezeichneten Symbolen.
# ═══════════════════════════════════════════════════════════════════════════

def draw_weather_icon(d, x, y, s, kind, night=False):
    """Einfache Wettersymbole aus Grundformen. (x, y) = linke obere Ecke, s = Größe."""
    sun, cloud, dark = (255, 200, 40), (215, 222, 235), (150, 160, 180)
    def disc(cx, cy, r, fill):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    def sunshape(cx, cy, r):
        if night:
            disc(cx, cy, r, (235, 235, 210))
            disc(cx + r * 0.45, cy - r * 0.3, r * 0.85, (8, 10, 16))
            return
        import math
        for i in range(8):
            a = i * math.pi / 4
            d.line([cx + math.cos(a) * r * 1.25, cy + math.sin(a) * r * 1.25,
                    cx + math.cos(a) * r * 1.7, cy + math.sin(a) * r * 1.7], fill=sun, width=max(2, int(s / 22)))
        disc(cx, cy, r, sun)
    def cloudshape(cx, cy, w, fill):
        h = w * 0.55
        disc(cx - w * 0.22, cy, h * 0.42, fill)
        disc(cx + w * 0.05, cy - h * 0.18, h * 0.55, fill)
        disc(cx + w * 0.28, cy + h * 0.02, h * 0.38, fill)
        d.rounded_rectangle([cx - w * 0.42, cy, cx + w * 0.45, cy + h * 0.42], radius=h * 0.2, fill=fill)
    c = (x + s / 2, y + s / 2)
    if kind == "sun":
        sunshape(c[0], c[1], s * 0.24)
        return
    if kind == "partly":
        sunshape(x + s * 0.36, y + s * 0.34, s * 0.19)
        cloudshape(x + s * 0.56, y + s * 0.58, s * 0.62, cloud)
        return
    fill = dark if kind in ("rain", "thunder", "drizzle") else cloud
    cloudshape(c[0], y + s * 0.42, s * 0.8, fill)
    base = y + s * 0.7
    if kind in ("rain", "drizzle"):
        n = 3 if kind == "rain" else 2
        for i in range(n):
            px = x + s * (0.3 + i * 0.2)
            d.line([px, base, px - s * 0.06, base + s * (0.2 if kind == "rain" else 0.12)],
                   fill=(90, 160, 255), width=max(2, int(s / 18)))
    elif kind == "snow":
        for i in range(3):
            disc(x + s * (0.3 + i * 0.2), base + s * 0.1, s * 0.05, (245, 248, 255))
    elif kind == "thunder":
        d.polygon([(x + s * 0.52, base - s * 0.02), (x + s * 0.4, base + s * 0.16), (x + s * 0.5, base + s * 0.16),
                   (x + s * 0.42, base + s * 0.3), (x + s * 0.62, base + s * 0.1), (x + s * 0.52, base + s * 0.1)],
                  fill=(255, 210, 40))
    elif kind == "fog":
        for i in range(3):
            yy = base + i * s * 0.09
            d.line([x + s * 0.18, yy, x + s * 0.82, yy], fill=(190, 198, 210), width=max(2, int(s / 20)))


class WeatherPage:
    @page("weather")
    def page_weather(self, profile, macros):
        cfg = (self.settings or {}).get("weather") or {}
        if cfg.get("lat") is None:
            return self._hint_page("☀", "Wetter", "Ort in der G19s-Verwaltung einstellen")
        data, err, _ = self.weather.snapshot() if self.weather else (None, None, 0)
        if not data:
            return self._hint_page("☀", "Wetter-Fehler" if err else "Wetter", err or "Lade Wetterdaten …",
                                   (235, 90, 90) if err else None)
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        cur = data.get("current") or {}
        desc, kind = WEATHER_CODES.get(int(cur.get("weather_code") or 0), ("", "cloud"))
        night = not cur.get("is_day", 1)
        d.text((12, 6), self._fit(d, cfg.get("name") or "", self.f_small, WIDTH - 40), font=self.f_small, fill=self.DIM)
        if err:
            d.text((WIDTH - 22, 6), "⚠", font=self.f_small, fill=(240, 170, 60))
        draw_weather_icon(d, 6, 26, 92, kind, night)
        temp = cur.get("temperature_2m")
        d.text((112, 20), f"{round(temp)}°" if temp is not None else "–", font=self.f_huge, fill=self.FG)
        d.text((114, 104), self._fit(d, desc, self.f_mid, WIDTH - 124), font=self.f_mid, fill=PROFILE_COLOR.get(profile, self.FG))
        bits = []
        if cur.get("apparent_temperature") is not None:
            bits.append(f"gefühlt {round(cur['apparent_temperature'])}°")
        if cur.get("wind_speed_10m") is not None:
            bits.append(f"{round(cur['wind_speed_10m'])} km/h")
        if cur.get("relative_humidity_2m") is not None:
            bits.append(f"{round(cur['relative_humidity_2m'])} %")
        d.text((114, 130), self._fit(d, " · ".join(bits), self.f_small, WIDTH - 122), font=self.f_small, fill=self.DIM)
        daily = data.get("daily") or {}
        import datetime as dt
        days = daily.get("time") or []
        d.line([8, 156, WIDTH - 8, 156], fill=(40, 46, 60))
        col_w = (WIDTH - 16) // 3
        for i in range(min(3, len(days))):
            x = 8 + i * col_w
            try:
                day = dt.date.fromisoformat(days[i])
                label = "Heute" if i == 0 else "Morgen" if i == 1 else WEEKDAY_DE[day.weekday()]
            except ValueError:
                label = days[i]
            code = (daily.get("weather_code") or [0] * 3)[i] or 0
            draw_weather_icon(d, x - 2, 166, 32, WEATHER_CODES.get(int(code), ("", "cloud"))[1])
            tx, tw = x + 32, col_w - 36
            d.text((tx, 160), self._fit(d, label, self.f_small_b, tw), font=self.f_small_b, fill=self.FG)
            tmax = (daily.get("temperature_2m_max") or [None] * 3)[i]
            tmin = (daily.get("temperature_2m_min") or [None] * 3)[i]
            if tmax is not None and tmin is not None:
                d.text((tx, 178), self._fit(d, f"{round(tmax)}°/{round(tmin)}°", self.f_small, tw),
                       font=self.f_small, fill=self.FG)
            rain = (daily.get("precipitation_probability_max") or [None] * 3)[i]
            if rain is not None:
                d.text((tx, 197), f"☂ {rain} %", font=self.f_tiny, fill=(120, 170, 255))
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_termine
#   Displayseite „Termine“: nächste Termine aller sichtbaren Kalender, optional mit markiertem Termin.
# ═══════════════════════════════════════════════════════════════════════════

class CalendarPage:
    # ---- Termine -------------------------------------------------------- #
    CAL_COLORS = CAL_COLORS

    @page("calendar")
    def page_calendar(self, profile, macros):
        import datetime as dt
        cfg = (self.settings or {}).get("calendar") or {}
        if not cfg.get("sources"):
            return self._hint_page("▦", "Termine", "Kalender in der G19s-Verwaltung eintragen")
        data, err, _ = self.calendar.snapshot() if self.calendar else (None, None, 0)
        if data is None:
            return self._hint_page("▦", "Kalender-Fehler" if err else "Termine", err or "Lade Termine …",
                                   (235, 90, 90) if err else None)
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        now = dt.datetime.now().astimezone()
        today = now.date()
        d.text((12, 4), "Termine", font=self.f_title, fill=self.FG)
        head = f"{WEEKDAY_DE[today.weekday()]} {today.day}. {MONTHS[today.month - 1]}"
        d.text((WIDTH - 12 - d.textlength(head, font=self.f_small), 8), head, font=self.f_small, fill=self.DIM)
        if err or data.get("errors"):
            d.text((96, 8), "⚠", font=self.f_small, fill=(240, 170, 60))
        cals = data.get("calendar_list") or []
        shown = [c for c in cals if c["key"] not in self.cal_hidden]
        if len(cals) > 1:
            info = f"{len(shown)}/{len(cals)}" if len(shown) < len(cals) else ""
            if info:
                d.text((12 + d.textlength("Termine", font=self.f_title) + 8, 8), info, font=self.f_small,
                       fill=(240, 170, 60))
        items = [x for x in data.get("items", [])
                 if (x["end"] > now if not x["allday"] else x["end"] > today)
                 and x.get("cal") not in self.cal_hidden]
        self.cal_items = items
        if self.cal_sel is not None:
            self.cal_sel = max(0, min(self.cal_sel, len(items) - 1)) if items else None
        if not items:
            if cals and not shown:
                self._center(d, 90, "Alle Kalender ausgeblendet", self.f_mid, self.DIM)
                self._center(d, 122, "OK = Kalender wählen", self.f_small, self.DIM)
            else:
                self._center(d, 100, "Keine Termine", self.f_mid, self.DIM)
            return img
        y, last_day, bottom = 32, None, HEIGHT - 30
        sources = cfg.get("sources") or []
        sel = self.cal_sel
        start = max(0, sel - 4) if sel is not None else 0
        for idx, it in enumerate(items[start:], start):
            day = it["start"] if it["allday"] else it["start"].date()
            ongoing = (it["allday"] and day <= today) or (not it["allday"] and it["start"] <= now)
            day = max(day, today) if ongoing else day
            if day != last_day:
                if y + 38 > bottom:
                    break
                label = ("Heute" if day == today else "Morgen" if day == today + dt.timedelta(days=1)
                         else f"{WEEKDAY_DE[day.weekday()]} {day.day:02d}.{day.month:02d}.")
                d.text((12, y), label, font=self.f_small_b, fill=PROFILE_COLOR.get(profile, self.FG))
                y += 19
                last_day = day
            if y + 19 > bottom:
                break
            if it["allday"]:
                when = "ganztags"
            elif ongoing:
                when = f"bis {it['end'].strftime('%H:%M')}"
            else:
                when = it["start"].strftime("%H:%M")
            src = it.get("source", 0)
            color = self.CAL_COLORS[src % len(self.CAL_COLORS)]
            if src < len(sources) and isinstance(sources[src].get("color"), list):
                color = tuple(sources[src]["color"])
            if isinstance(it.get("color"), list):
                color = tuple(it["color"])
            if idx == sel:
                d.rounded_rectangle([6, y - 1, WIDTH - 6, y + 18], radius=4, fill=(40, 48, 66))
            d.text((16, y), self._fit(d, when, self.f_small, 76), font=self.f_small,
                   fill=self.FG if idx == sel else self.DIM)
            d.rectangle([96, y + 3, 99, y + 16], fill=color)
            title = it["title"] + (f" · {it['location']}" if it.get("location") else "")
            d.text((106, y), self._fit(d, title, self.f_small, WIDTH - 114), font=self.f_small, fill=self.FG)
            y += 19
        return img


@page_keys("calendar")
def keys_calendar(app, pressed):
    """Hoch/Runter = Termin markieren, OK = Details, MENU = Kalenderauswahl."""
    r = app.renderer
    if pressed & (LKEY_BITS["UP"] | LKEY_BITS["DOWN"] | LKEY_BITS["OK"]):
        n = len(r.cal_items)
        if n:
            sel = move_selection(r.cal_sel, pressed, n)
            if pressed & LKEY_BITS["OK"]:
                sel = 0 if sel is None else sel
                app.menu = DetailView(r.cal_items[min(sel, n - 1)])
                app.flash = None
            r.cal_sel = sel
            app.sel_t["calendar"] = time.monotonic()
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["MENU"]:
        if app.calendar_list():
            app.menu = CalendarMenu()
            app.flash = None
        else:
            app.show("Kalender", ["noch keine Kalender geladen"], PROFILE_COLOR[app.layer], 2)
        app.next_draw = 0
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_hardware
#   Displayseite „Hardware“: Prozessor (Temperatur, Auslastung), Grafikkarte, SSD, Arbeitsspeicher,
#   Lüfter, Netzwerkdurchsatz, Datenträger. (Enthält auch die frühere Seite „System“.)
# ═══════════════════════════════════════════════════════════════════════════

class HardwarePage:
    # ---- Hardware ------------------------------------------------------- #
    def _temp_row(self, d, y, label, temp, extra=""):
        d.text((12, y), label, font=self.f_small_b, fill=self.FG)
        if temp is None:
            d.text((80, y), "nicht verfügbar", font=self.f_small, fill=self.DIM)
            return
        pct = max(0.0, min(1.0, (temp - 20) / 70))
        color = (62, 207, 126) if temp < 60 else (240, 169, 59) if temp < 80 else (235, 80, 80)
        txt = f"{temp:.0f} °C" + (f" · {extra}" if extra else "")
        tx = WIDTH - 12 - d.textlength(txt, font=self.f_small)
        end = int(min(230, tx - 10))
        d.rounded_rectangle([80, y + 5, end, y + 13], radius=4, fill=(35, 40, 55))
        if pct > 0.03:
            d.rounded_rectangle([80, y + 5, 80 + int((end - 80) * pct), y + 13], radius=4, fill=color)
        d.text((tx, y), txt, font=self.f_small, fill=self.FG)

    @staticmethod
    def _rate(b):
        for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
            if b < 1000 or unit == "GB/s":
                return f"{b:.0f} {unit}" if unit == "B/s" else f"{b:.1f} {unit}"
            b /= 1000

    def _usage_row(self, d, y, label, pct, txt, profile):
        """Zeile mit Balken in der Farbe der Ebene (rot ab 90 %) und Text rechts."""
        d.text((12, y), label, font=self.f_small_b, fill=self.FG)
        tx = WIDTH - 12 - d.textlength(txt, font=self.f_tiny)
        end = int(min(230, tx - 10))
        d.rounded_rectangle([80, y + 5, end, y + 13], radius=4, fill=(35, 40, 55))
        color = PROFILE_COLOR.get(profile, self.FG) if pct < 90 else (235, 80, 80)
        d.rounded_rectangle([80, y + 5, 80 + max(8, int((end - 80) * min(100, pct) / 100)), y + 13], radius=4, fill=color)
        d.text((tx, y + 2), txt, font=self.f_tiny, fill=self.DIM)

    @page("hardware")
    def page_hardware(self, profile, macros):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        s, row = self.hw.sensors(), 22
        self._temp_row(d, 8, "CPU", s["cpu"], f"{self.stats.cpu_percent():.0f} %")
        self._temp_row(d, 8 + row, "GPU", s["gpu"], f"{s['gpu_load']} %" if s["gpu_load"] is not None else "")
        y = 8 + 2 * row
        if s["nvme"] is not None:
            self._temp_row(d, y, "SSD", s["nvme"])
            y += row
        used, total, mem_pct = self.stats.memory()
        self._usage_row(d, y, "RAM", mem_pct, f"{used:.1f} / {total:.1f} GiB", profile)
        y += row
        if s["fans"]:
            fans = " · ".join(f"{rpm} U/min" for _, rpm in s["fans"][:3])
            d.text((12, y), "Lüfter", font=self.f_small_b, fill=self.FG)
            d.text((80, y), self._fit(d, fans, self.f_small, WIDTH - 92), font=self.f_small, fill=self.FG)
            y += row
        net = self.hw.network()
        if net:
            d.text((12, y), "Netz", font=self.f_small_b, fill=self.FG)
            d.text((80, y), f"↓ {self._rate(net[0])}   ↑ {self._rate(net[1])}", font=self.f_small, fill=self.FG)
            y += row
        for label, pct, total in self.hw.disks()[:2]:
            if y > HEIGHT - 48:
                break
            self._usage_row(d, y, label, pct, f"{pct:.0f} % v. {total / 1e9:.0f} GB", profile)
            y += row
        l1, l5, l15 = self.stats.load()
        if y <= HEIGHT - 48:
            d.text((12, y), "Last", font=self.f_small_b, fill=self.FG)
            d.text((80, y), f"{l1:.2f}  {l5:.2f}  {l15:.2f}", font=self.f_small, fill=self.DIM)
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_nachrichten
#   Displayseite „Nachrichten“: Schlagzeilen aus RSS-/Atom-Feeds, optional markierte Meldung.
# ═══════════════════════════════════════════════════════════════════════════

class NewsPage:
    @page("news")
    def page_news(self, profile, macros):
        cfg = (self.settings or {}).get("news") or {}
        data, hint = self._poll_state(self.news, "≡", "Nachrichten",
                                      None if cfg.get("feeds") else "Nachrichtenquellen in der G19s-Verwaltung eintragen")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        items = data.get("items") or []
        self.list_items["news"] = items
        _, err, _ = self.news.snapshot()
        self._header(d, "Nachrichten", time.strftime("%H:%M"), bool(err or data.get("errors")))
        if not items:
            self._center(d, 100, "Keine Meldungen", self.f_mid, self.DIM)
            return img
        import datetime as dt
        today = dt.date.today()
        sel = self.sel["news"]
        if sel is not None:
            sel = self.sel["news"] = max(0, min(sel, len(items) - 1))
        start = max(0, sel - 2) if sel is not None else 0
        y, bottom = 32, HEIGHT - 30
        color = PROFILE_COLOR.get(profile, self.FG)
        for idx, it in enumerate(items[start:], start):
            lines = self._wrap(d, it["title"], self.f_small, WIDTH - 24, 2)
            h = 16 + 18 * len(lines) + 4
            if y + h > bottom:
                break
            if idx == sel:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + h - 4], radius=5, fill=(40, 48, 66))
            meta = it.get("source") or ""
            if it.get("time"):
                t = it["time"].astimezone()
                meta += " · " + (t.strftime("%H:%M") if t.date() == today else t.strftime("%d.%m. %H:%M"))
            d.text((12, y), meta, font=self.f_tiny, fill=color)
            y += 15
            for line in lines:
                d.text((12, y), line, font=self.f_small, fill=self.FG if idx == sel else (210, 215, 225))
                y += 18
            y += 5
        return img


@page_keys("news", "warnings")
def keys_news_warnings(app, pressed):
    """Nachrichten/Unwetter: Hoch/Runter markiert, OK öffnet (Browser bzw. Details), MENU lädt neu."""
    page_id = PAGE_IDS[app.page % len(PAGE_IDS)]
    r = app.renderer
    if pressed & (LKEY_BITS["UP"] | LKEY_BITS["DOWN"] | LKEY_BITS["OK"]):
        items = r.list_items.get(page_id) or []
        if items:
            sel = move_selection(r.sel[page_id], pressed, len(items))
            if pressed & LKEY_BITS["OK"]:
                if sel is None:
                    sel = 0                 # erster Druck markiert nur
                else:
                    open_list_item(app, page_id, items[min(sel, len(items) - 1)])
            r.sel[page_id] = sel
            app.sel_t[page_id] = time.monotonic()
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, page_id)
        return True
    return False


def open_list_item(app, page_id, it):
    if page_id == "news" and it.get("link"):
        if app.launcher.start(["xdg-open", it["link"]]):
            app.show("Öffne", [it.get("source") or domain_of(it["link"])], PROFILE_COLOR[app.layer], 1.5)
            app.log(f"Nachricht geöffnet: {it['title']}")
    elif page_id == "warnings":
        label, color = SEVERITY.get(it["severity"], SEVERITY["minor"])
        body = it["description"] + ("\n\n" + it["instruction"] if it.get("instruction") else "")
        app.menu = DetailView({"title": it["headline"] or it["event"], "start": it["onset"],
                               "end": it["expires"] or it["onset"], "allday": False, "location": "",
                               "description": body, "color": list(color), "label": f"{label} · {it['event']}"})
        app.flash = None


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_unwetter
#   Displayseite „Unwetter“: DWD-Warnungen für den Wetterort, farbig nach Stufe.
# ═══════════════════════════════════════════════════════════════════════════

class WarningsPage:
    # ---- Unwetter ------------------------------------------------------- #
    @page("warnings")
    def page_warnings(self, profile, macros):
        w = (self.settings or {}).get("weather") or {}
        data, hint = self._poll_state(self.alerts, "⚠", "Unwetter",
                                      None if w.get("lat") is not None else "Ort in der G19s-Verwaltung einstellen (Infoseiten → Wetter)")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        alerts = data.get("alerts") or []
        self.list_items["warnings"] = alerts
        place = data.get("place") or w.get("name") or ""
        self._header(d, "Unwetter", self._fit(d, place, self.f_small, 170))
        if not alerts:
            cx = WIDTH // 2
            d.ellipse([cx - 34, 50, cx + 34, 118], fill=(40, 170, 90))
            d.line([(cx - 16, 84), (cx - 4, 98), (cx + 18, 70)], fill=(255, 255, 255), width=7)
            self._center(d, 132, "Keine Warnungen", self.f_big, self.FG)
            self._center(d, 168, "Deutscher Wetterdienst", self.f_small, self.DIM)
            return img
        sel = self.sel["warnings"]
        if sel is not None:
            sel = self.sel["warnings"] = max(0, min(sel, len(alerts) - 1))
        start = max(0, sel - 2) if sel is not None else 0
        y, bottom = 32, HEIGHT - 30
        for idx, a in enumerate(alerts[start:], start):
            if y + 44 > bottom:
                break
            label, color = SEVERITY.get(a["severity"], SEVERITY["minor"])
            if idx == sel:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + 42], radius=5, fill=(40, 48, 66))
            d.rectangle([10, y, 15, y + 38], fill=color)
            d.text((24, y), self._fit(d, a["event"], self.f_small_b, WIDTH - 36), font=self.f_small_b, fill=self.FG)
            span = f"{WEEKDAY_DE[a['onset'].weekday()]} {a['onset'].strftime('%H:%M')}"
            if a.get("expires"):
                e = a["expires"]
                span += " – " + (e.strftime("%H:%M") if e.date() == a["onset"].date() else
                                 f"{WEEKDAY_DE[e.weekday()]} {e.strftime('%H:%M')}")
            d.text((24, y + 20), f"{label} · {span}", font=self.f_tiny, fill=color)
            y += 48
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_netzwerk
#   Displayseite „Netzwerk“: Erreichbarkeit der eingetragenen Geräte mit Antwortzeit.
# ═══════════════════════════════════════════════════════════════════════════

class NetworkPage:
    # ---- Netzwerk ------------------------------------------------------- #
    @page("network")
    def page_network(self, profile, macros):
        data, hint = self._poll_state(self.net, "◎", "Netzwerk")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        hosts = data.get("hosts") or []
        up = sum(1 for h in hosts if h["ok"])
        self._header(d, "Netzwerk", f"{up}/{len(hosts)} erreichbar")
        y = 34
        for h in hosts[:8]:
            col = (62, 207, 126) if h["ok"] else (235, 80, 80)
            d.ellipse([14, y + 4, 26, y + 16], fill=col)
            ms = (f"{h['ms']:.0f} ms" if h["ms"] is not None else "ok") if h["ok"] else "offline"
            mw = d.textlength(ms, font=self.f_small)
            d.text((WIDTH - 12 - mw, y), ms, font=self.f_small, fill=col if not h["ok"] else self.DIM)
            d.text((34, y), self._fit(d, h["name"], self.f_small_b, 110), font=self.f_small_b, fill=self.FG)
            d.text((150, y + 2), self._fit(d, h["host"], self.f_tiny, WIDTH - 170 - mw), font=self.f_tiny, fill=self.DIM)
            y += 22
        if data.get("ip"):
            d.text((12, HEIGHT - 48), f"Dieser PC: {data['ip']}", font=self.f_small, fill=self.DIM)
        return img


@page_keys("network")
def keys_network(app, pressed):
    """MENU = neu prüfen."""
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, "network")
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Modul seite_updates
#   Displayseite „Updates“: verfügbare Paket- und Flatpak-Updates, Neustart-Hinweis.
# ═══════════════════════════════════════════════════════════════════════════

class UpdatesPage:
    # ---- Updates -------------------------------------------------------- #
    @page("updates")
    def page_updates(self, profile, macros):
        data, hint = self._poll_state(self.updates, "↻", "Updates")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        self._header(d, "Updates", "geprüft " + data.get("checked", ""))
        n = data.get("apt", 0) + (data.get("flatpak") or 0)
        color = (62, 207, 126) if n == 0 else PROFILE_COLOR.get(profile, self.FG)
        self._center(d, 30, str(n), self.f_huge, color)
        self._center(d, 112, "System ist aktuell" if n == 0 else ("Update verfügbar" if n == 1 else "Updates verfügbar"),
                     self.f_mid, self.FG)
        y = 142
        parts = [f"Pakete: {data.get('apt', 0)}"]
        if data.get("flatpak") is not None:
            parts.append(f"Flatpak: {data['flatpak']}")
        self._center(d, y, " · ".join(parts), self.f_small, self.DIM)
        y += 22
        if data.get("security"):
            self._center(d, y, f"davon {data['security']} Sicherheitsupdate{'s' if data['security'] != 1 else ''}",
                         self.f_small_b, (240, 120, 80))
            y += 22
        if data.get("reboot"):
            d.rounded_rectangle([40, y, WIDTH - 40, y + 22], radius=6, fill=(150, 40, 40))
            self._center(d, y + 2, "Neustart erforderlich", self.f_small_b, (255, 255, 255))
        return img


@page_keys("updates")
def keys_updates(app, pressed):
    """MENU = neu prüfen, OK = Aktualisierung öffnen (Discover)."""
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, "updates")
        return True
    if pressed & LKEY_BITS["OK"]:
        cmd = "plasma-discover --mode update" if shutil.which("plasma-discover") else "konsole -e sudo apt full-upgrade"
        if app.launcher.start(cmd):
            app.show("Updates", ["Discover wird geöffnet"], PROFILE_COLOR[app.layer], 1.8)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Modul menues
#   Auswahllisten auf dem Display: Profile, Kalender, Alben und allgemeine Listen (Sender, Textbausteine).
# ═══════════════════════════════════════════════════════════════════════════

class MenuViews:
    def render_album_menu(self, albums, selected, cursor, recursive, color, status=None):
        """Albenauswahl der Bilderseite: albums = [{id, name, level, total, parent}]."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), "Alben", font=self.f_big, fill=self.FG)
        if status or not albums:
            d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
            self._center(d, HEIGHT - 20, "BACK zurück", self.f_tiny, self.DIM)
            lines = self._wrap(d, status or "Keine Alben gefunden", self.f_small, WIDTH - 32, 5)
            for i, line in enumerate(lines):
                self._center(d, 90 + i * 20, line, self.f_small, self.DIM)
            return img
        by_id = {a["id"]: a for a in albums}

        def implied(a):                    # über ein gewähltes Oberalbum enthalten
            p, seen = a.get("parent"), set()
            while recursive and p in by_id and p not in seen:
                if p in selected:
                    return True
                seen.add(p)
                p = by_id[p].get("parent")
            return False
        cnt = f"{sum(1 for a in albums if a['id'] in selected)} gewählt"
        d.text((WIDTH - 12 - d.textlength(cnt, font=self.f_small), 14), cnt, font=self.f_small, fill=self.DIM)
        row_h, top, rows = 24, 44, 7
        first = max(0, min(cursor - rows // 2, len(albums) - rows))
        for n, a in enumerate(albums[first:first + rows]):
            i = first + n
            y = top + n * row_h
            on, inh = a["id"] in selected, implied(a)
            if i == cursor:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + row_h - 4], radius=5, fill=(40, 48, 66))
            x = 14 + min(int(a.get("level") or 0), 3) * 12
            box = [x, y + 2, x + 16, y + 18]
            if on:
                d.rounded_rectangle(box, radius=3, fill=color)
                d.line([(x + 4, y + 10), (x + 7, y + 14), (x + 13, y + 6)], fill=self.BG, width=2)
            elif inh:
                d.rounded_rectangle(box, radius=3, outline=color, width=2)
                d.rectangle([x + 5, y + 7, x + 11, y + 13], fill=color)
            else:
                d.rounded_rectangle(box, radius=3, outline=(110, 116, 130), width=2)
            num = str(a.get("total") or 0)
            nw = d.textlength(num, font=self.f_tiny)
            d.text((WIDTH - 16 - nw, y + 3), num, font=self.f_tiny, fill=self.DIM)
            d.text((x + 26, y), self._fit(d, a["name"], self.f_small, WIDTH - x - 50 - nw), font=self.f_small,
                   fill=self.FG if (on or inh) else (150, 156, 170))
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ wählen · OK ein/aus · BACK fertig", self.f_tiny, self.DIM)
        self._scroll_marks(d, first > 0, first + rows < len(albums))
        return img

    def render_list_menu(self, title, items, cursor, hint, info="", color=None):
        """Allgemeine Auswahlliste: items = [{"label", "sub"?, "mark"?, "color"?, "dim"?}]."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), title, font=self.f_big, fill=self.FG)
        if info:
            d.text((WIDTH - 12 - d.textlength(info, font=self.f_small), 14), info, font=self.f_small, fill=self.DIM)
        if not items:
            self._center(d, 100, "Keine Einträge", self.f_mid, self.DIM)
        row_h, top, rows = 24, 44, 7
        first = max(0, min(cursor - rows // 2, len(items) - rows))
        for n, it in enumerate(items[first:first + rows]):
            i = first + n
            y = top + n * row_h
            if i == cursor:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + row_h - 4], radius=5, fill=(40, 48, 66))
            mark = it.get("mark") or ""
            mcol = tuple(it.get("color") or color or self.FG)
            if mark:
                d.text((14, y), mark, font=self.f_small_b, fill=mcol)
            sub = it.get("sub") or ""
            sw = d.textlength(sub, font=self.f_tiny) if sub else 0
            if sub:
                d.text((WIDTH - 16 - sw, y + 3), sub, font=self.f_tiny, fill=self.DIM)
            fill = (110, 116, 130) if it.get("dim") else (self.FG if i == cursor else (200, 205, 215))
            d.text((34, y), self._fit(d, it["label"], self.f_small, WIDTH - 50 - sw), font=self.f_small, fill=fill)
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, hint, self.f_tiny, self.DIM)
        self._scroll_marks(d, first > 0, first + rows < len(items))
        return img

    def render_calendar_menu(self, cals, hidden, cursor):
        """Kalenderauswahl der Terminseite: cals = [{key, name, color}]."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), "Kalender", font=self.f_big, fill=self.FG)
        on = sum(1 for c in cals if c["key"] not in hidden)
        cnt = f"{on} von {len(cals)} sichtbar"
        d.text((WIDTH - 12 - d.textlength(cnt, font=self.f_small), 14), cnt, font=self.f_small, fill=self.DIM)
        row_h, top, rows = 24, 44, 7
        first = max(0, min(cursor - rows // 2, len(cals) - rows))
        for n, c in enumerate(cals[first:first + rows]):
            i = first + n
            y = top + n * row_h
            visible = c["key"] not in hidden
            color = tuple(c.get("color") or self.CAL_COLORS[i % len(self.CAL_COLORS)])
            if i == cursor:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + row_h - 4], radius=5, fill=(40, 48, 66))
            box = [16, y + 2, 32, y + 18]
            if visible:
                d.rounded_rectangle(box, radius=3, fill=color)
                d.line([(20, y + 10), (23, y + 14), (29, y + 6)], fill=self.BG, width=2)
            else:
                d.rounded_rectangle(box, radius=3, outline=color, width=2)
            d.text((42, y), self._fit(d, c["name"], self.f_small, WIDTH - 56), font=self.f_small,
                   fill=(self.FG if i == cursor else (200, 205, 215)) if visible else (110, 116, 130))
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ wählen · OK ein/aus · BACK fertig", self.f_tiny, self.DIM)
        self._scroll_marks(d, first > 0, first + rows < len(cals))
        return img

    def render_profile_menu(self, profiles, cursor, active, colors_of):
        """Profilauswahl: profiles = Liste der Namen, colors_of(i) = Farben des Profils."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), "Profil wählen", font=self.f_big, fill=self.FG)
        n = len(profiles)
        row_h = 17 if n > 8 else 21
        top = 42
        for i, name in enumerate(profiles):
            y = top + i * row_h
            if i == cursor:
                d.rounded_rectangle([6, y - 1, WIDTH - 6, y + row_h - 3], radius=5, fill=(40, 48, 66))
            cols = colors_of(i)
            for j, layer in enumerate(LAYERS):
                d.rectangle([14 + j * 7, y + 3, 19 + j * 7, y + row_h - 7], fill=tuple(cols[layer]))
            num = f"{i + 1}"
            d.text((62 - d.textlength(num, font=self.f_small_b), y), num, font=self.f_small_b, fill=self.DIM)
            d.text((72, y), self._fit(d, name, self.f_small, WIDTH - 112), font=self.f_small,
                   fill=self.FG if i == cursor else (200, 205, 215))
            if i == active:
                d.text((WIDTH - 30, y), "✓", font=self.f_small_b, fill=(80, 220, 130))
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ wählen · OK aktivieren · BACK zurück", self.f_tiny, self.DIM)
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul einblendungen
#   Einblendungen über der aktuellen Seite: Meldungen, Lautstärke, Mikrofon, Timer, Termine, Benachrichtigungen.
# ═══════════════════════════════════════════════════════════════════════════

class OverlayViews:
    def render_timer(self, t, color, now=None):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        if t.alarm:
            blink = int(time.monotonic() * 2) % 2 == 0
            d.rectangle([0, 0, WIDTH, HEIGHT], fill=(120, 20, 20) if blink else self.BG)
            self._icon_bell(d, WIDTH // 2, 36, self.FG)
            self._center(d, 120, "Zeit abgelaufen!", self.f_big, self.FG)
            self._center(d, 158, timer_label(t.cfg or {}), self.f_mid, (230, 200, 200))
            d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
            self._center(d, HEIGHT - 20, "beliebige Displaytaste = OK", self.f_tiny, self.DIM)
            return img
        if t.mode == "pomodoro":
            title = "Pomodoro · " + ("Arbeiten" if t.phase == "work" else "Pause")
            accent = color if t.phase == "work" else (62, 207, 126)
        else:
            title, accent = ("Stoppuhr" if t.mode == "stopwatch" else timer_label(t.cfg or {})), color
        d.text((12, 6), title, font=self.f_title, fill=self.FG)
        state = "läuft" if t.running else "angehalten"
        d.text((WIDTH - 12 - d.textlength(state, font=self.f_small), 9), state, font=self.f_small,
               fill=(80, 220, 130) if t.running else (240, 170, 60))
        value = fmt_clock(t.display_value(now))
        font = self.f_huge if d.textlength(value, font=self.f_huge) <= WIDTH - 20 else self.f_large
        self._center(d, 52, value, font, self.FG if t.running else (170, 176, 190))
        if t.mode != "stopwatch" and t.total:
            frac = 1 - t.remaining(now) / t.total
            d.rounded_rectangle([20, 160, WIDTH - 20, 172], radius=6, fill=(35, 40, 55))
            if frac > 0:
                d.rounded_rectangle([20, 160, 20 + max(12, int((WIDTH - 40) * frac)), 172], radius=6, fill=accent)
        if t.mode == "pomodoro":
            self._center(d, 182, f"{t.rounds} Runde{'n' if t.rounds != 1 else ''} geschafft", self.f_small, self.DIM)
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        hint = ("OK Start/Stopp · ▼ auf 0 · BACK zurück" if t.mode == "stopwatch" else
                "OK Pause · ▲ +1 min · ▼ beenden · BACK zurück")
        self._center(d, HEIGHT - 20, hint, self.f_tiny, self.DIM)
        return img

    def render_event(self, ev, cal_name, color, scroll=0):
        """Termindetails: Titel, Zeit, Ort, Kalender, Beschreibung (mit Hoch/Runter blätterbar)."""
        import datetime as dt
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = tuple(color or self.CAL_COLORS[0])
        d.rectangle([0, 0, 6, HEIGHT - 22], fill=color)
        lines = []                                  # (Text, Schrift, Farbe)
        for t in self._wrap(d, ev.get("title") or "", self.f_title, WIDTH - 28, 3):
            lines.append((t, self.f_title, self.FG, 23))
        s, e = ev["start"], ev["end"]
        if ev.get("allday"):
            last = e - dt.timedelta(days=1) if isinstance(e, dt.date) and e > s else s
            when = f"{WEEKDAY_DE[s.weekday()]} {s.day:02d}.{s.month:02d}." + (
                f" – {WEEKDAY_DE[last.weekday()]} {last.day:02d}.{last.month:02d}." if last != s else "") + " · ganztägig"
        else:
            when = f"{WEEKDAY_DE[s.weekday()]} {s.day:02d}.{s.month:02d}. {s.strftime('%H:%M')}"
            when += f"–{e.strftime('%H:%M')}" if e.date() == s.date() else \
                f" – {WEEKDAY_DE[e.weekday()]} {e.day:02d}.{e.month:02d}. {e.strftime('%H:%M')}"
        lines.append(("", self.f_tiny, self.FG, 4))
        lines.append((when, self.f_small_b, color, 20))
        if ev.get("location"):
            for t in self._wrap(d, "Ort: " + ev["location"], self.f_small, WIDTH - 28, 2):
                lines.append((t, self.f_small, (200, 205, 215), 19))
        if cal_name:
            lines.append((cal_name, self.f_small, self.DIM, 19))
        desc = (ev.get("description") or "").strip()
        if desc:
            lines.append(("", self.f_tiny, self.FG, 6))
            for para in desc.split("\n"):
                for t in (self._wrap(d, para, self.f_small, WIDTH - 28, 40) if para.strip() else [""]):
                    lines.append((t, self.f_small, (200, 205, 215), 19))
        area = HEIGHT - 22 - 8
        heights = [h for *_, h in lines]
        max_scroll = 0
        while sum(heights[max_scroll:]) > area and max_scroll < len(lines) - 1:
            max_scroll += 1
        scroll = max(0, min(scroll, max_scroll))
        y = 8
        for text, font, fill, h in lines[scroll:]:
            if y + h > area + 8:
                break
            d.text((16, y), text, font=font, fill=fill)
            y += h
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ blättern · BACK zurück" if max_scroll else "BACK zurück", self.f_tiny, self.DIM)
        self._scroll_marks(d, scroll > 0, scroll < max_scroll)
        return img, max_scroll

    def render_reminder(self, ev, minutes, color, cal_name=""):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = tuple(color or self.CAL_COLORS[0])
        d.rectangle([0, 0, WIDTH, 34], fill=color)
        head = "Termin jetzt" if minutes <= 0 else f"Termin in {minutes} Min."
        d.text((12, 6), head, font=self.f_title, fill=(255, 255, 255))
        d.text((WIDTH - 12 - d.textlength(ev["start"].strftime("%H:%M"), font=self.f_title), 6),
               ev["start"].strftime("%H:%M"), font=self.f_title, fill=(255, 255, 255))
        y = 46
        for t in self._wrap(d, ev.get("title") or "", self.f_big, WIDTH - 24, 3):
            d.text((12, y), t, font=self.f_big, fill=self.FG)
            y += 30
        y += 4
        if ev.get("location"):
            for t in self._wrap(d, "Ort: " + ev["location"], self.f_small, WIDTH - 24, 2):
                d.text((12, y), t, font=self.f_small, fill=(200, 205, 215))
                y += 19
        if cal_name:
            d.text((12, y), cal_name, font=self.f_small, fill=self.DIM)
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "beliebige Displaytaste = OK", self.f_tiny, self.DIM)
        return img

    def render_mic(self, muted, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), (90, 16, 16) if muted else self.BG)
        d = ImageDraw.Draw(img)
        cx, top = WIDTH // 2, 36
        col = (255, 255, 255) if muted else color
        d.rounded_rectangle([cx - 18, top, cx + 18, top + 62], radius=18, fill=col)
        d.arc([cx - 34, top + 20, cx + 34, top + 88], 0, 180, fill=col, width=6)
        d.line([(cx, top + 88), (cx, top + 104)], fill=col, width=6)
        d.line([(cx - 22, top + 106), (cx + 22, top + 106)], fill=col, width=6)
        if muted:
            d.line([(cx - 48, top + 104), (cx + 48, top - 6)], fill=(255, 80, 80), width=9)
        self._center(d, 162, "Mikrofon stumm" if muted else "Mikrofon an", self.f_big, self.FG)
        return img

    def render_notification(self, app, summary, body, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, WIDTH, 30], fill=(24, 29, 40))
        d.rectangle([0, 0, 5, 30], fill=color)
        d.text((14, 6), self._fit(d, app or "Benachrichtigung", self.f_small_b, WIDTH - 80), font=self.f_small_b, fill=self.DIM)
        now = time.strftime("%H:%M")
        d.text((WIDTH - 10 - d.textlength(now, font=self.f_small), 6), now, font=self.f_small, fill=self.DIM)
        y = 40
        for line in self._wrap(d, summary or "", self.f_title, WIDTH - 24, 2):
            d.text((12, y), line, font=self.f_title, fill=self.FG)
            y += 24
        y += 4
        for line in self._wrap(d, body or "", self.f_small, WIDTH - 24, max(1, (HEIGHT - y - 8) // 19)):
            d.text((12, y), line, font=self.f_small, fill=(200, 205, 215))
            y += 19
        return img

    def render_volume(self, pct, muted, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        # Lautsprecher-Symbol
        cx, cy = 60, 104
        d.rectangle([cx - 22, cy - 14, cx - 8, cy + 14], fill=self.FG)
        d.polygon([(cx - 8, cy - 14), (cx + 14, cy - 34), (cx + 14, cy + 34), (cx - 8, cy + 14)], fill=self.FG)
        if muted:
            d.line([cx + 26, cy - 16, cx + 58, cy + 16], fill=(235, 80, 80), width=6)
            d.line([cx + 26, cy + 16, cx + 58, cy - 16], fill=(235, 80, 80), width=6)
        else:
            for i, r in enumerate((20, 34, 48)):
                if pct > i * 33:
                    d.arc([cx + 14 - r, cy - r, cx + 14 + r, cy + r], -45, 45, fill=self.FG, width=5)
        if muted:
            d.text((140, 88), "Stumm", font=self.f_big, fill=self.FG)
        else:
            num = str(pct)
            font, top = (self.f_huge, 58) if len(num) < 3 else (self.f_large, 70)
            nw = d.textlength(num, font=font)
            x = 140 + (160 - nw - 26) / 2
            d.text((x, top), num, font=font, fill=self.FG)
            d.text((x + nw + 4, 102), "%", font=self.f_big, fill=self.DIM)
        d.rounded_rectangle([20, 170, WIDTH - 20, 186], radius=8, fill=(35, 40, 55))
        w = int((WIDTH - 40) * max(0, min(100, pct)) / 100)
        if w > 12:
            d.rounded_rectangle([20, 170, 20 + w, 186], radius=8, fill=(110, 118, 135) if muted else color)
        return img

    def render_message(self, title, lines, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, WIDTH, 6], fill=color)
        self._center(d, 34, title, self.f_big, color)
        y = 92
        for line in lines:
            self._center(d, y, self._fit(d, line, self.f_mid, WIDTH - 24), self.f_mid, self.FG)
            y += 32
        return img


# ═══════════════════════════════════════════════════════════════════════════
# Modul anzeige
#   Renderer: setzt Grundlagen, alle Displayseiten, Menüs und Einblendungen zu einer Klasse zusammen.
#
#   render(page, profile, macros) zeichnet eine Seite samt Fußzeile; render_*() zeichnet Menüs und Einblendungen.
# ═══════════════════════════════════════════════════════════════════════════

class Renderer(RendererBase,
               ClockPage, ClockBase, StandardFaces, MechanicalFaces, SkyFaces, DisplayFaces, InfoFaces,
               MacrosPage, MusicPage, SlidesPage, WeatherPage, CalendarPage, HardwarePage,
               NewsPage, WarningsPage, NetworkPage, UpdatesPage,
               MenuViews, OverlayViews):
    PAGES = len(PAGE_IDS)
    MUSIC_PAGE = PAGE_IDS.index("music")
    SLIDES_PAGE = PAGE_IDS.index("slides")

    def render(self, page, profile, macros=None):
        page %= len(PAGE_IDS)
        img = PAGE_RENDERERS[PAGE_IDS[page]](self, profile, macros or {})
        visible = self.visible or list(range(len(PAGE_IDS)))
        pos = visible.index(page) if page in visible else -1
        self._footer(ImageDraw.Draw(img), profile, pos, len(visible))
        return img


assert all(f in CLOCK_RENDERERS for f in CLOCK_FACES), \
    f"Zifferblätter ohne Zeichenfunktion: {[f for f in CLOCK_FACES if f not in CLOCK_RENDERERS]}"
assert all(p in PAGE_RENDERERS for p in PAGE_IDS), \
    f"Displayseiten ohne Zeichenfunktion: {[p for p in PAGE_IDS if p not in PAGE_RENDERERS]}"


# ═══════════════════════════════════════════════════════════════════════════
# Modul menue_logik
#   Menüs und Vollbild-Ansichten am Display: Tastenbehandlung und Zeichnen.
#
#   Ein offenes Menü bekommt alle Displaytasten. on_key() verarbeitet einen Report
#   (pressed = neu gedrückte Tasten, kann auch 0 sein), draw() liefert das Bild.
#   Menüs schließen sich nach MENU_TIMEOUT Sekunden ohne Tastendruck
#   (außer der Timer-Anzeige).
# ═══════════════════════════════════════════════════════════════════════════

MENU_TIMEOUT = 30
CLOSE_KEYS = LKEY_BITS["BACK"] | LKEY_BITS["MENU"] | LKEY_BITS["SETTINGS"] | LKEY_BITS["LEFT"] | LKEY_BITS["RIGHT"]


class Menu:
    kind = ""
    timeout = MENU_TIMEOUT

    def __init__(self, cursor=0):
        self.cursor = cursor
        self.t = time.monotonic()           # letzte Aktivität (für das Zeitlimit)

    def touch(self):
        self.t = time.monotonic()

    def expired(self, now):
        return self.timeout is not None and now - self.t > self.timeout

    @staticmethod
    def step(cursor, pressed, n):
        """Hoch/Runter mit Umlauf."""
        if pressed & LKEY_BITS["UP"]:
            cursor = (cursor - 1) % n
        if pressed & LKEY_BITS["DOWN"]:
            cursor = (cursor + 1) % n
        return cursor

    def on_key(self, app, pressed):
        raise NotImplementedError

    def draw(self, app, now):
        raise NotImplementedError


class ProfileMenu(Menu):
    """SETTINGS: Profil wählen."""
    kind = "profile"

    def on_key(self, app, pressed):
        self.touch()                        # jeder Report (auch Loslassen) zählt als Aktivität
        self.cursor = self.step(self.cursor, pressed, len(app.store.profiles))
        if pressed & LKEY_BITS["OK"]:
            app.menu = None
            if self.cursor != app.prof_idx:
                app.set_profile(self.cursor)
        elif pressed & (LKEY_BITS["BACK"] | LKEY_BITS["SETTINGS"] | LKEY_BITS["MENU"]):
            app.menu = None
        app.next_draw = 0

    def draw(self, app, now):
        self.cursor = min(self.cursor, len(app.store.profiles) - 1)
        return app.renderer.render_profile_menu([p["name"] for p in app.store.profiles],
                                                self.cursor, app.prof_idx, app.profile_colors)


class ClockMenu(Menu):
    """Uhrseite, MENU: Zifferblatt für dieses Profil und diese Ebene wählen."""
    kind = "clocks"

    def __init__(self, app):
        super().__init__()
        faces = [it["face"] for it in self.items(app)]
        self.cursor = faces.index(app.clock_face()) if app.clock_face() in faces else 0

    @staticmethod
    def items(app):
        """Zifferblätter fürs Menü: in der Verwaltung ausgewählte (leer = alle), das aktuelle immer."""
        cur = app.clock_face()
        chosen = set((app.settings().get("clock") or {}).get("menu") or CLOCK_FACES)
        return [{"label": label, "face": face, "mark": "▶" if face == cur else ""}
                for face, label in CLOCK_FACES.items() if face in chosen or face == cur]

    def on_key(self, app, pressed):
        items = self.items(app)
        self.cursor = self.step(self.cursor, pressed, len(items))
        if pressed & LKEY_BITS["OK"]:
            app.menu = None
            app.set_clock_face(items[self.cursor]["face"])
        elif pressed & CLOSE_KEYS:
            app.menu = None
        elif pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        return app.renderer.render_list_menu("Zifferblatt", self.items(app), self.cursor,
                                             "▲▼ wählen · OK übernehmen · BACK zurück", f"{self.cursor + 1}/{len(self.items(app))} · {app.layer}",
                                             PROFILE_COLOR[app.layer])


class CalendarMenu(Menu):
    """Terminseite, MENU: Kalender ein-/ausblenden."""
    kind = "calendar"

    def on_key(self, app, pressed):
        cals = app.calendar_list()
        self.cursor = self.step(self.cursor, pressed, max(1, len(cals)))
        if pressed & LKEY_BITS["OK"] and cals:
            app.renderer.cal_hidden ^= {cals[min(self.cursor, len(cals) - 1)]["key"]}
            app.save_calendar_hidden(cals)
        if pressed & CLOSE_KEYS:
            app.menu = None
        elif pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        cals = app.calendar_list()
        self.cursor = min(self.cursor, max(0, len(cals) - 1))
        return app.renderer.render_calendar_menu(cals, app.renderer.cal_hidden, self.cursor)


class AlbumMenu(Menu):
    """Bilderseite, MENU: Piwigo-Alben der Diashow wählen."""
    kind = "albums"

    def __init__(self, selected):
        super().__init__()
        self.sel = selected

    def on_key(self, app, pressed):
        albums = app.slideshow.album_state["list"] or []
        self.cursor = self.step(self.cursor, pressed, max(1, len(albums)))
        if pressed & LKEY_BITS["OK"] and albums:
            self.sel ^= {albums[min(self.cursor, len(albums) - 1)]["id"]}
            app.save_albums(self.sel, albums)
        if pressed & CLOSE_KEYS:
            app.menu = None
        elif pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        st = app.slideshow.album_state
        albums = st["list"] or []
        status = ("Alben werden geladen …" if st["loading"] and not albums else
                  st["error"] if st["error"] and not albums else None)
        self.cursor = min(self.cursor, max(0, len(albums) - 1))
        return app.renderer.render_album_menu(albums, self.sel, self.cursor, bool(app.slideshow.cfg().get("recursive")),
                                              PROFILE_COLOR[app.layer], status)


class PickMenu(Menu):
    """Liste, aus der OK einen Eintrag ausführt und schließt (Sender, Textbausteine)."""

    def items(self, app):
        raise NotImplementedError

    def choose(self, app, item):
        raise NotImplementedError

    def on_key(self, app, pressed):
        items = self.items(app)
        self.cursor = self.step(self.cursor, pressed, max(1, len(items)))
        if pressed & LKEY_BITS["OK"] and items:
            app.menu = None
            self.choose(app, items[min(self.cursor, len(items) - 1)])
        elif pressed & CLOSE_KEYS:
            app.menu = None
        elif pressed:
            self.touch()
        app.next_draw = time.monotonic() + (0.6 if app.menu is None else 0)


class StationMenu(PickMenu):
    """Musikseite, MENU: Radiosender wählen."""
    kind = "stations"

    def items(self, app):
        return app.station_items()

    def choose(self, app, item):
        if item.get("stop"):
            app.radio.stop()
            app.media.wake.set()
            app.show("Radio", ["ausgeschaltet"], PROFILE_COLOR[app.layer], 1.2)
        else:
            threading.Thread(target=app.radio_play, args=(item["station"],), daemon=True).start()

    def draw(self, app, now):
        items = self.items(app)
        self.cursor = min(self.cursor, max(0, len(items) - 1))
        return app.renderer.render_list_menu("Radiosender", items, self.cursor, "▲▼ wählen · OK abspielen · BACK zurück",
                                             f"{len([i for i in items if 'station' in i])} Sender", PROFILE_COLOR[app.layer])


class SnippetMenu(PickMenu):
    """G-Taste „Textbausteine“: Text wählen und einfügen."""
    kind = "snippets"

    def __init__(self, group, title):
        super().__init__()
        self.group, self.title = group, title

    def items(self, app):
        return app.snippet_list(self.group)

    def choose(self, app, item):
        if not app.player.play(compile_steps({"text": item["text"]}, app.log)):
            app.log("Es läuft bereits ein Makro – ignoriert")
        else:
            app.log(f"Textbaustein: {item['name']}")

    def draw(self, app, now):
        items = self.items(app)
        self.cursor = min(self.cursor, max(0, len(items) - 1))
        return app.renderer.render_list_menu(self.title or "Textbausteine", items, self.cursor,
                                             "▲▼ wählen · OK einfügen · BACK zurück", f"{len(items)}", PROFILE_COLOR[app.layer])


class DetailView(Menu):
    """Vollbild-Text: Termindetails bzw. Unwetterwarnung; Hoch/Runter blättern."""
    kind = "event"

    def __init__(self, item):
        super().__init__()
        self.item, self.scroll, self.max = item, 0, 0

    def on_key(self, app, pressed):
        if pressed & LKEY_BITS["UP"]:
            self.scroll = max(0, self.scroll - 1)
        if pressed & LKEY_BITS["DOWN"]:
            self.scroll = min(self.max, self.scroll + 1)
        if pressed & (CLOSE_KEYS | LKEY_BITS["OK"]):
            app.menu = None
            app.sel_t["calendar"] = time.monotonic()
        elif pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        ev = self.item
        cal = next((c for c in app.calendar_list() if c["key"] == ev.get("cal")), None)
        img, self.max = app.renderer.render_event(ev, cal["name"] if cal else ev.get("label", ""),
                                                  ev.get("color") or (cal or {}).get("color"), self.scroll)
        return img


class TimerView(Menu):
    """Große Timer-Anzeige (G-Taste „Timer“). Schließt sich nicht von selbst."""
    kind = "timer"
    timeout = None

    def on_key(self, app, pressed):
        t = app.timer
        if pressed & LKEY_BITS["OK"]:
            t.toggle()
        if pressed & LKEY_BITS["UP"]:
            t.add_minute()
        if pressed & LKEY_BITS["DOWN"]:
            if not t.reset():
                app.log("Timer beendet")
                app.menu = None
                if app.alarm["blink_until"]:
                    app.alarm["blink_until"] = 0.0
                    app.apply_leds()
        if pressed & CLOSE_KEYS:
            app.menu = None                 # Timer läuft weiter (Anzeige in der Fußzeile)
        app.next_draw = 0

    def draw(self, app, now):
        if not app.timer.active:
            app.menu = None
            return None
        return app.renderer.render_timer(app.timer, PROFILE_COLOR[app.layer], now)


# ═══════════════════════════════════════════════════════════════════════════
# Modul aktionen
#   G-Tasten-Aktionen: welcher Eintrag in macros.json was auslöst.
#
#   Die Art eines Eintrags bestimmt entry_type() (Reihenfolge in ENTRY_TYPES, makros.py);
#   GKEY_ACTIONS ordnet jeder Art ihre Ausführung zu. Ohne Art sendet die Taste F13–F24
#   (bzw. mit Strg/Alt in M2/M3) für KDE-Kurzbefehle. Neue Aktion: Art in ENTRY_TYPES
#   eintragen und hier mit @gkey_action("art") anmelden.
# ═══════════════════════════════════════════════════════════════════════════

GKEY_ACTIONS = {}


def gkey_action(*types):
    """Ausführung für Einträge der Art(en) types anmelden."""
    def deco(fn):
        for t in types:
            GKEY_ACTIONS[t] = fn
        return fn
    return deco


@gkey_action("timer")
def act_timer(app, macro, name):
    tcfg = macro["timer"]
    if app.timer.alarm:
        app.dismiss_alarm()
    elif app.timer.same(tcfg):
        if app.menu is not None and app.menu.kind == "timer":
            app.timer.toggle()
        else:
            app.menu = TimerView()
    else:
        app.timer.start(tcfg)
        app.log(f"{timer_label(tcfg)} gestartet")
        app.menu = TimerView()
    app.flash = None
    app.next_draw = 0


@gkey_action("snippets")
def act_snippets(app, macro, name):
    if app.menu is not None and app.menu.kind == "snippets":
        app.menu = None                     # zweiter Druck schließt die Liste
    elif app.snippet_list(macro["snippets"]):
        app.menu = SnippetMenu(macro["snippets"], entry_label(macro, app.settings()))
        app.flash = None
    else:
        app.show("Textbausteine", ["keine Textbausteine", "in der Verwaltung anlegen"], PROFILE_COLOR[app.layer], 2.5)
    app.next_draw = 0


@gkey_action("open", "run")
def act_open_run(app, macro, name):
    label = str(macro.get("name") or macro.get("open") or "Befehl")
    if macro.get("open"):
        cmd, verb = ["xdg-open", str(macro["open"])], "Öffne"
    else:
        cmd, verb = str(macro["run"]), "Starte"
    if app.launcher.start(cmd):
        app.show(verb, [label], PROFILE_COLOR[app.layer], 1.5)
        app.log(f"{name}: {verb} {label}")
    else:
        app.show("Fehler", [f"{label} ließ sich", "nicht starten"], REC_COLOR, 3)


@gkey_action("radio")
def act_radio(app, macro, name):
    cur = app.radio.current()
    if macro["radio"] == "stop" or (cur and cur["url"] == macro["radio"]):
        app.radio.stop()                    # „Radio aus“ bzw. gleiche Taste nochmal = aus
        app.show("Radio", ["ausgeschaltet"], app.renderer.DIM, 1.5)
    else:
        station = next((s for s in app.settings().get("stations", []) if s.get("url") == macro["radio"]),
                       {"name": macro.get("name", ""), "url": macro["radio"]})
        app.radio_play(station)
    app.media.wake.set()


def act_remember_song(app, macro, name):
    app.media.refresh()                     # aktuellen Titel holen (im Hintergrund evtl. 5 s alt)
    info = app.media.snapshot()[0]
    entry = remember_song(info, app.radio.current())
    if entry:
        app.log(f"Song gemerkt: {entry['artist']} – {entry['title']}")
        app.show("♥ Gemerkt", [entry["title"] or entry["artist"], entry["artist"] if entry["title"] else ""],
                 PROFILE_COLOR[app.layer], 2.5)
    else:
        app.show("Song merken", ["schon gemerkt" if info else "es läuft nichts"], PROFILE_COLOR[app.layer], 1.8)


@gkey_action("media")
def act_media(app, macro, name):
    if macro["media"] == "remember":
        return act_remember_song(app, macro, name)
    threading.Thread(target=app.media.control, args=(macro["media"],), daemon=True).start()


@gkey_action("mic")
def act_mic(app, macro, name):
    color = PROFILE_COLOR[app.layer]

    def work():
        state = mic_state(app.launcher._env(), toggle=True)
        if state is None:
            app.show("Mikrofon", ["wpctl/pactl nicht gefunden"], REC_COLOR, 3)
            return
        app.mic.update(muted=state, known=True, changed=True)
        app.renderer.mic_muted = state
        app.log("Mikrofon " + ("stumm" if state else "an"))
        app.popup(lambda: app.renderer.render_mic(state, color), 1.5)
    threading.Thread(target=work, daemon=True).start()


@gkey_action("sleep")
def act_sleep(app, macro, name):
    sleep = app.sleep
    if sleep["until"]:
        sleep["until"] = 0.0
        app.renderer.sleep_badge = ""
        app.show("Einschlaftimer", ["aus"], PROFILE_COLOR[app.layer], 1.8)
        app.log("Einschlaftimer aus")
    else:
        try:
            minutes = max(1, min(240, int(macro["sleep"])))
        except (TypeError, ValueError):
            minutes = 30
        sleep.update(until=time.monotonic() + minutes * 60, minutes=minutes)
        info = app.media.snapshot()[0]
        if not app.radio.playing and not (info and info.get("status") == "Playing"):
            args = ("play-pause",) if app.last_station else ("next",)   # zuletzt gehörten bzw. ersten Sender starten
            threading.Thread(target=app.radio_control, args=args, daemon=True).start()
        app.show("Einschlaftimer", [f"Musik aus in {minutes} Min.", "gleiche Taste = abbrechen"], PROFILE_COLOR[app.layer], 2.5)
        app.log(f"Einschlaftimer: {minutes} Minuten")
    app.next_draw = 0


@gkey_action("volume")
def act_volume(app, macro, name):
    action, color = macro["volume"], PROFILE_COLOR[app.layer]

    def work():
        res = change_volume(action, app.settings().get("volume_step", 5), app.launcher._env())
        if res:
            pct, muted = res
            app.popup(lambda: app.renderer.render_volume(pct, muted, color), 1.6)
        else:
            app.show("Lautstärke", ["wpctl/pactl nicht gefunden"], REC_COLOR, 3)
    threading.Thread(target=work, daemon=True).start()


@gkey_action("text", "combo", "steps")
def act_keys(app, macro, name):
    if app.args.debug:
        print(f"  {name} -> „{entry_label(macro, app.settings())}“")
    if not app.player.play(compile_steps(macro, app.log)):
        app.log("Es läuft bereits ein Makro – ignoriert")


def run_gkey_action(app, macro, name):
    """Passende Aktion ausführen. False = keine Aktion (Taste sendet F13–F24)."""
    fn = GKEY_ACTIONS.get(entry_type(macro))
    if fn is None:
        return False
    fn(app, macro, name)
    return True


assert set(GKEY_ACTIONS) == set(ENTRY_TYPES), \
    f"G-Tasten-Arten ohne Ausführung: {set(ENTRY_TYPES) - set(GKEY_ACTIONS)}"


# ═══════════════════════════════════════════════════════════════════════════
# Modul app_kern
#   Kern der Hauptanwendung: Aufbau aller Teile, Zustand, Profile/Ebenen/Seiten,
#   Beleuchtung und Nachtmodus, Einstellungen neu laden, Hilfen für Menüs.
#
#   Der gesamte Laufzeitzustand steht als Attribut an einer Stelle:
#       layer        aktive Ebene M1/M2/M3            prof_idx   aktives Profil (Index)
#       page         angezeigte Seite (Index in PAGE_IDS)
#       menu         offenes Menü (menue_logik) oder None
#       flash        Einblendung (Zeichenfunktion, bis-Zeitpunkt) oder None
#       rec          laufende Makroaufnahme oder None
#       next_draw    Zeitpunkt der nächsten Displayaktualisierung
#
#   Threads: Die Hauptschleife besitzt den Zustand. Hintergrund-Threads (Lautstärke,
#   Mikrofon, Radio starten) melden sich nur über popup()/show() und einfache
#   Zuweisungen; Benachrichtigungen laufen über die Warteschlange popups.
# ═══════════════════════════════════════════════════════════════════════════

class AppCore:
    def __init__(self, args):
        from evdev import UInput, ecodes as e
        self.args, self.e = args, e
        migrate_files()                     # ältere settings.json/macros.json umstellen
        self.fkeys = [getattr(e, f"KEY_F{FKEY_BASE + i}") for i in range(12)]
        self.modifiers = {"M1": None, "M2": e.KEY_LEFTCTRL, "M3": e.KEY_LEFTALT}

        # --- Zustand ---
        self.layer = "M1"                   # aktive Ebene (M1/M2/M3) innerhalb des Profils
        self.page = 0
        self.layer_page = {}                # zuletzt gezeigte Seite je Ebene
        self.prof_idx, self.state_mtime = 0, None
        self.timer = Timer()                # Countdown / Stoppuhr / Pomodoro
        self.alarm = {"blink_until": 0.0, "blink_at": 0.0, "on": False}
        self.sleep = {"until": 0.0, "minutes": 0}          # Einschlaftimer
        self.reminded = set()               # schon angekündigte Termine
        self.seen_alerts = set()            # schon eingeblendete Unwetterwarnungen
        self.periodic = {"remind": 0.0, "backup": time.monotonic() + 60, "alarm_day": "", "backup_busy": False,
                         "fresh": None}
        self.modal = False                  # nächster Tastendruck schließt nur die Einblendung
        self.sel_t = {"calendar": 0.0, "news": 0.0, "warnings": 0.0}   # letzte Bewegung der Markierung
        self.rec = None                     # None | {"stage": "select"} | {"stage": "record", "gkey", "recorder"}
        self.flash = None                   # (Zeichenfunktion, bis-Zeitpunkt)
        self.menu = None
        self.night = {"active": False, "wake_until": 0.0}
        self.saver = {"active": False, "page": None, "since": 0.0}
        self.mic = {"muted": False, "known": False}
        self.popups = deque()               # Benachrichtigungen aus dem Hintergrund-Thread (threadsicher)
        self.next_draw = 0.0
        self._last_frame, self._last_sent = None, 0.0   # zuletzt gesendetes Bild (siehe App._send)
        self._last_draw_error = None                    # zuletzt protokollierter Anzeige-Fehler
        self.running = True
        self.prev_gm = self.prev_l = 0
        self.held = {}                      # G-Taste -> Modifier, mit dem sie gedrückt wurde
        self.next_reload = 0.0
        self.last_station = None
        self._settings, self.settings_mtime = load_settings(), None

        # --- Geräte und Dienste ---
        self.g19 = G19()
        # alle üblichen Tastaturcodes freischalten, damit Makros jede Taste senden können
        self.ui = UInput({e.EV_KEY: list(range(1, 249))}, name="Logitech G19s G-Keys")
        self.ui_lock = threading.Lock()
        self.player = Player(self.ui, self.ui_lock)
        self.store = MacroStore(MACRO_FILE, log=self.log)
        self.launcher = Launcher(log=self.log)
        self.renderer = r = Renderer()
        self.radio = RadioManager(self.launcher._env, log=self.log)
        threading.Thread(target=self._mic_poll, daemon=True).start()
        self.media = r.media = MediaWatcher(self.launcher._env, log=self.log, radio=self.radio,
                                            radio_control=self.radio_control)
        self.media.want_fast = lambda: PAGE_IDS[self.page % len(PAGE_IDS)] == "music" or self.radio.playing
        self.slideshow = r.slideshow = Slideshow(self.settings, log=self.log)
        self.weather = r.weather = WeatherPoller(self.settings, log=self.log)
        self.calendar = r.calendar = CalendarPoller(self.settings, log=self.log)
        self.news = r.news = NewsPoller(self.settings, log=self.log)
        self.alerts = r.alerts = WarningsPoller(self.settings, log=self.log)
        self.netpoll = r.net = NetworkPoller(self.settings, log=self.log)
        self.updates = r.updates = UpdatesPoller(self.settings, log=self.log)
        self.activity = ActivityWatcher(log=self.log)
        self.services = [self.media, self.slideshow, self.weather, self.calendar, self.news, self.alerts,
                         self.netpoll, self.updates, self.activity]
        for s in self.services:
            s.start()
        self.notifier = NotificationWatcher(self.launcher._env, self._on_notify, log=self.log)
        self.notifier.start()
        self.refreshers = {"news": self.news, "warnings": self.alerts, "network": self.netpoll, "updates": self.updates}

        r.cal_hidden = set(str(k) for k in (load_state().get("calendar_hidden") or []))
        try:
            self.prof_idx = int(load_state().get("profile", 0))
            self.state_mtime = os.path.getmtime(STATE_FILE)
        except (TypeError, ValueError, OSError):
            self.prof_idx = 0

    # --- Grundlegendes ------------------------------------------------------ #
    @staticmethod
    def log(msg):
        print(msg, flush=True)

    def settings(self):
        return self._settings

    def popup(self, draw_fn, seconds=2.5):
        self.flash = (draw_fn, time.monotonic() + seconds)
        self.next_draw = 0

    def show(self, title, lines, color, seconds=2.5):
        self.popup(lambda: self.renderer.render_message(title, lines, color), seconds)

    def _on_notify(self, app_name, summary, body):
        n = self.settings().get("notifications") or {}
        if not n.get("enabled", True):
            return
        ignore = [x.strip().lower() for x in str(n.get("ignore") or "").split(",") if x.strip()]
        if app_name.lower() in ignore or (not summary and not body):
            return
        self.popups.append((app_name, summary, body))

    def _mic_poll(self):
        while True:
            state = mic_state(self.launcher._env())
            if state is not None and (state != self.mic["muted"] or not self.mic["known"]):
                self.mic.update(muted=state, known=True)
                self.renderer.mic_muted = state
                self.mic["changed"] = True
            time.sleep(15)                  # nur für Änderungen von außen; die G-Taste meldet sofort

    # --- Radio ---------------------------------------------------------------- #
    def radio_play(self, station, announce=True):
        if self.radio.play(station, self.settings().get("radio_player"), self.settings().get("stations", [])):
            self.last_station = station
            if announce:
                self.show("Radio", [station.get("name") or domain_of(station["url"])], PROFILE_COLOR[self.layer], 1.5)
            return True
        self.show("Fehler", ["Radioplayer startet nicht", "mpv installiert?"], REC_COLOR, 4)
        return False

    def radio_control(self, action):
        stations = self.settings().get("stations", [])
        if action in ("next", "previous"):
            st = self.radio.step(stations, self.settings().get("radio_player"), 1 if action == "next" else -1)
            if st:
                self.last_station = st
        elif action in ("play-pause", "stop"):
            if self.radio.playing:
                self.radio.stop()
            elif action == "play-pause" and self.last_station:
                self.radio_play(self.last_station)

    # --- Profile, Ebenen, Seiten ------------------------------------------- #
    def profile_colors(self, i):
        """Farben eines Profils; ohne eigene Farben gelten die aus settings.json."""
        own = self.store.profile(i).get("colors") if 0 <= i < len(self.store.profiles) else None
        base = valid_colors(self.settings().get("colors")) or DEFAULT_SETTINGS["colors"]
        return own or base

    def apply_profile(self):
        """Farben und Name des aktiven Profils übernehmen."""
        self.prof_idx = max(0, min(self.prof_idx, len(self.store.profiles) - 1))
        for layer, color in self.profile_colors(self.prof_idx).items():
            PROFILE_COLOR[layer] = tuple(color)
        self.renderer.profile_name = self.store.profile(self.prof_idx)["name"] if len(self.store.profiles) > 1 else ""
        self.update_page_union()

    def set_profile(self, i, announce=True):
        self.prof_idx = i % len(self.store.profiles)
        self.apply_profile()
        try:
            save_state(profile=self.prof_idx)
            self.state_mtime = os.path.getmtime(STATE_FILE)
        except OSError as ex:
            self.log(f"Aktives Profil konnte nicht gespeichert werden: {ex}")
        self.apply_leds()
        self.fix_page()
        name = self.store.profile(self.prof_idx)["name"]
        self.log(f"Profil {self.prof_idx + 1}: {name}")
        if announce:
            self.show(f"Profil {self.prof_idx + 1}", [name], PROFILE_COLOR[self.layer], 1.8)

    def check_state_file(self):
        """Die Verwaltung kann ein Profil aktivieren, indem sie state.json schreibt."""
        try:
            mtime = os.path.getmtime(STATE_FILE)
        except OSError:
            return
        if mtime == self.state_mtime:
            return
        self.state_mtime = mtime
        self.renderer.cal_hidden = set(str(k) for k in (load_state().get("calendar_hidden") or []))
        try:
            wanted = int(load_state().get("profile", 0))
        except (TypeError, ValueError):
            return
        if wanted != self.prof_idx and 0 <= wanted < len(self.store.profiles):
            self.set_profile(wanted)

    def visible_pages(self, layer=None):
        """Indizes der eingeschalteten Seiten der (aktiven) Ebene in der eingestellten Reihenfolge."""
        s = self.settings()
        layer = layer or self.layer
        own = self.store.profile(self.prof_idx).get("pages") or {}
        lst = own.get(layer) or (s.get("layer_pages") or {}).get(layer) or s.get("pages") or []
        order = [PAGE_IDS.index(p) for p in lst if p in PAGE_IDS]
        return order or [PAGE_IDS.index("clock")]

    def fix_page(self):
        """Nach Profil-/Einstellungswechsel: nur Seiten zeigen, die in Profil und Ebene eingeschaltet sind."""
        order = self.visible_pages()
        self.renderer.visible = order
        if self.page not in order and not self.saver["active"]:
            self.page = order[0]
        self.next_draw = 0

    def update_page_union(self):
        """Alle Seiten, die irgendwo sichtbar sind – danach richten sich Wetter-/Kalenderabruf."""
        s = self.settings()
        lists = list((s.get("layer_pages") or {}).values())
        for p in self.store.profiles:
            lists += list((p.get("pages") or {}).values())
        s["pages"] = list(dict.fromkeys(x for lst in lists for x in lst if x in PAGE_IDS)) or ["clock"]

    def switch_layer(self, name):
        """M-Taste: Ebene wechseln; Display auf die Seiten dieser Ebene umstellen."""
        self.layer_page[self.layer] = self.page
        self.layer = name
        order = self.visible_pages()
        self.renderer.visible = order
        if self.page not in order and not self.saver["active"]:
            back = self.layer_page.get(name)
            self.page = back if back in order else order[0]

    def nav(self, direction):
        """Zur nächsten/vorherigen eingeschalteten Seite blättern."""
        order = self.visible_pages()
        pos = order.index(self.page) if self.page in order else -1
        self.page = order[(pos + direction) % len(order)]
        self.flash = None
        self.saver["active"] = False        # manuelles Blättern beendet den Bildschirmschoner
        self.next_draw = 0

    def nav_keys(self, pressed, next_keys, prev_keys):
        if pressed & next_keys:
            self.nav(1)
        if pressed & prev_keys:
            self.nav(-1)

    # --- Helligkeit, Beleuchtung, Nachtmodus -------------------------------- #
    def set_brightness(self, value):
        try:
            self.g19.set_brightness(int(value))
        except Exception as ex:             # USB-Fehler dürfen den Treiber nicht beenden
            self.log(f"Helligkeit konnte nicht gesetzt werden: {ex}")

    def day_brightness(self):
        b = self.args.brightness if self.args.brightness is not None else self.settings().get("brightness")
        return 100 if b is None else b

    def night_dark(self):
        """Nachtmodus aktiv und nicht gerade per Tastendruck geweckt?"""
        return self.night["active"] and time.monotonic() >= self.night["wake_until"]

    def apply_leds(self):
        try:
            n = self.settings().get("night") or {}
            if self.night_dark() and n.get("backlight_off", True) and not self.rec:
                self.g19.set_m_leds(0)
                self.g19.set_backlight(0, 0, 0)
                return
            # MR leuchtet während einer Aufnahme und solange das Mikrofon stumm ist
            mask = M_LED[self.layer] | (M_LED["MR"] if self.rec or self.mic["muted"] else 0)
            self.g19.set_m_leds(mask)
            if not (self.args.keep_backlight or self.settings().get("keep_backlight")):
                self.g19.set_backlight(*(REC_COLOR if self.rec else PROFILE_COLOR[self.layer]))
        except Exception as ex:             # Beleuchtung ist nicht kritisch
            print(f"Hinweis: Beleuchtung konnte nicht gesetzt werden: {ex}", file=sys.stderr)

    def night_brightness(self):
        n = self.settings().get("night") or {}
        return 0 if n.get("mode") == "off" else int(n.get("brightness", 10))

    def update_night(self, force=False):
        """Nachtmodus nach Uhrzeit ein-/ausschalten."""
        n = self.settings().get("night") or {}
        active = bool(n.get("enabled")) and in_time_window(time.strftime("%H:%M"), n.get("start"), n.get("end"))
        if active == self.night["active"] and not force:
            return
        self.night["active"] = active
        if active:
            self.log("Nachtmodus an")
            self.set_brightness(self.night_brightness())
        else:
            self.log("Nachtmodus aus")
            self.set_brightness(self.day_brightness())
        self.apply_leds()
        self.next_draw = 0

    def wake(self, seconds=60):
        """Tastendruck in der Nacht: Display für kurze Zeit normal anzeigen. True = war dunkel."""
        if self.night["active"]:
            was_dark = self.night_dark()
            self.night["wake_until"] = time.monotonic() + seconds
            if was_dark:
                self.set_brightness(self.day_brightness())
                self.apply_leds()
            return was_dark
        return False

    # --- Einstellungen ------------------------------------------------------ #
    def apply_settings(self, first=False):
        s = self.settings()
        self.apply_profile()
        self.renderer.settings = s
        self.renderer.visible = self.visible_pages()
        if not self.night["active"]:
            if self.args.brightness is not None or s.get("brightness") is not None or not first:
                self.set_brightness(self.day_brightness())
        if not first:
            self.apply_leds()

    def reload_settings(self):
        try:
            mtime = os.path.getmtime(SETTINGS_FILE)
        except FileNotFoundError:
            mtime = None
        if mtime == self.settings_mtime:
            return False
        self.settings_mtime = mtime
        try:
            self._settings = load_settings()
            self.log("Einstellungen geladen")
        except (ValueError, OSError) as ex:
            self.log(f"settings.json fehlerhaft, bisherige Einstellungen bleiben aktiv: {ex}")
            return False
        return True

    # --- Listen für Menüs, Speichern von Auswahlen -------------------------- #
    def calendar_list(self):
        data, _err, _ = self.calendar.snapshot()
        return (data or {}).get("calendar_list") or []

    def save_calendar_hidden(self, cals):
        keep = sorted(self.renderer.cal_hidden)
        try:
            save_state(calendar_hidden=keep)
            self.state_mtime = os.path.getmtime(STATE_FILE)
        except OSError as ex:
            self.log(f"Kalenderauswahl konnte nicht gespeichert werden: {ex}")
        shown = [c["name"] for c in cals if c["key"] not in self.renderer.cal_hidden]
        self.log(f"Kalender sichtbar: {', '.join(shown) or 'keine'}")

    def station_items(self):
        stations = [st for st in self.settings().get("stations", []) if isinstance(st, dict) and st.get("url")]
        cur = self.radio.current()
        items = [{"label": st.get("name") or domain_of(st["url"]), "station": st,
                  "mark": "▶" if cur and cur["url"] == st["url"] else ""} for st in stations]
        if cur:
            items.append({"label": "Radio ausschalten", "stop": True, "mark": "■", "color": (235, 90, 90)})
        return items

    def snippet_list(self, group="*"):
        all_groups = group in (None, "", "*", True)
        out = []
        for sn in self.settings().get("snippets") or []:
            if not isinstance(sn, dict) or not str(sn.get("text") or ""):
                continue
            if not all_groups and str(sn.get("group") or "") != str(group):
                continue
            name = str(sn.get("name") or "").strip() or str(sn["text"]).split("\n")[0][:40]
            out.append({"label": name, "name": name, "text": str(sn["text"]),
                        "sub": str(sn.get("group") or "") if all_groups else ""})
        return out

    def save_albums(self, selected, albums):
        """Albenauswahl in settings.json schreiben (die Verwaltung liest sie von dort)."""
        try:
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    raw = json.load(f)
            except FileNotFoundError:
                raw = {}
            if not isinstance(raw, dict):
                raise ValueError("settings.json ist kein JSON-Objekt")
            sl = raw.get("slideshow") if isinstance(raw.get("slideshow"), dict) else {}
            order = [a["id"] for a in albums]
            sl["albums"] = sorted(selected, key=lambda i: order.index(i) if i in order else 1e9)
            raw["slideshow"] = sl
            save_json(SETTINGS_FILE, raw, private=True)
        except (OSError, ValueError) as ex:
            self.log(f"Albenauswahl konnte nicht gespeichert werden: {ex}")
            return
        names = [a["name"] for a in albums if a["id"] in selected]
        self.log(f"Diashow-Alben: {', '.join(names) or 'keine'}")

    def clock_face(self, layer=None):
        """Zifferblatt der Uhr im aktiven Profil und in der (aktiven) Ebene."""
        face = (self.store.profile(self.prof_idx).get("clock") or {}).get(layer or self.layer)
        return face if face in CLOCK_FACES else "digital"

    def set_clock_face(self, face):
        """Zifferblatt in macros.json beim Profil speichern (die Verwaltung übernimmt es beim Abgleich)."""
        prof = self.store.profile(self.prof_idx)
        faces = dict(prof.get("clock") or {})
        if face == "digital":
            faces.pop(self.layer, None)
        else:
            faces[self.layer] = face
        if faces:
            prof["clock"] = faces
        else:
            prof.pop("clock", None)
        try:
            self.store.save()
        except OSError as ex:
            self.log(f"Zifferblatt konnte nicht gespeichert werden: {ex}")
        self.flash = None
        self.next_draw = 0
        self.log(f"Uhr: {CLOCK_FACES[face]} ({prof['name']}, {self.layer})")

    def dismiss_alarm(self):
        """Abgelaufenen Timer bestätigen."""
        self.timer.stop()
        self.alarm["blink_until"] = 0.0
        if self.menu is not None and self.menu.kind == "timer":
            self.menu = None
        self.apply_leds()
        self.next_draw = 0


# ═══════════════════════════════════════════════════════════════════════════
# Modul app_tasten
#   Tasten der Tastatur: G-/M-Tasten (inkl. Makroaufnahme mit MR) und Displaytasten.
#
#   Displaytasten gehen der Reihe nach an:
#     1. Vorrang-Regeln: nachts weckt der erste Druck nur, der Bildschirmschoner
#        endet nur, ein abgelaufener Timer bzw. eine Erinnerung wird nur bestätigt
#     2. SETTINGS öffnet (ohne offenes Menü) das Profilmenü
#     3. das offene Menü (menue_logik)
#     4. die Tasten der angezeigten Seite (@page_keys in den Seitenmodulen)
#     5. sonst: Rechts/Runter = nächste Seite, Links/Hoch = vorige Seite
# ═══════════════════════════════════════════════════════════════════════════

class KeyHandling:
    # --- G- und M-Tasten ----------------------------------------------------- #
    def handle_gm_report(self, data):
        # Nur Report-ID 0x02 enthält die G-/M-Bits. Report 0x03 ist ein
        # zusätzlicher Tastatur-Report (G1 = F1 usw.) und wird ignoriert.
        if not (data and len(data) >= 4 and data[0] == 0x02):
            return
        if self.args.debug:
            print("G/M-Report:", data.hex(" "))
        value = (data[1] | (data[2] << 8)) & 0xFFFF
        pressed = value & ~self.prev_gm
        released = self.prev_gm & ~value
        self.prev_gm = value
        if pressed:
            self.activity.touch()
            self.wake()
        if pressed & MKEY_BITS["MR"]:
            self._record_key()
        for i, (name, bit) in enumerate(GKEY_BITS.items()):
            if pressed & bit:
                self._gkey_down(i, name)
            if released & bit and name in self.held:
                self._gkey_up(i, name)
        for name, bit in MKEY_BITS.items():
            if pressed & bit and name in self.modifiers:
                if self.args.debug:
                    print(f"  {name} gedrückt")
                if self.rec is None:
                    self.switch_layer(name)
                    self.apply_leds()
                    self.next_draw = 0

    def _record_key(self):
        """MR: Aufnahme starten / beenden / abbrechen."""
        rec, store, layer = self.rec, self.store, self.layer
        if rec is None:
            self.rec = {"stage": "select"}
            self.log("Makroaufnahme: G-Taste wählen")
        elif rec["stage"] == "select":
            self.rec = None
            self.show("Abgebrochen", ["Keine Aufnahme"], self.renderer.DIM, 1.5)
            self.log("Makroaufnahme abgebrochen")
        else:
            gkey = rec["gkey"]
            steps = rec["recorder"].stop()
            self.rec = None
            if steps:
                store.set(self.prof_idx, layer, gkey, {"name": f"Makro {gkey}", "steps": steps})
                n = sum(1 for s in steps if s[2] == "down")
                self.show("Gespeichert", [f"{gkey} im Profil {layer}", f"{n} Tastendrücke"], PROFILE_COLOR[layer])
                self.log(f"Makro {layer}/{gkey} gespeichert ({n} Tastendrücke)")
            elif store.delete(self.prof_idx, layer, gkey):
                self.show("Gelöscht", [f"{gkey} im Profil {layer}", f"sendet wieder F{FKEY_BASE - 1 + int(gkey[1:])}"], self.renderer.DIM)
                self.log(f"Makro {layer}/{gkey} gelöscht")
            else:
                self.show("Nichts aufgenommen", ["Kein Makro gespeichert"], self.renderer.DIM)
        self.apply_leds()
        self.next_draw = 0

    def _gkey_down(self, i, name):
        if self.rec is not None:
            if self.rec["stage"] == "select":
                recorder = Recorder()
                if recorder.start():
                    self.rec = {"stage": "record", "gkey": name, "recorder": recorder}
                    self.log(f"Aufnahme für {self.layer}/{name} läuft – MR zum Beenden")
                else:
                    self.rec = None
                    self.apply_leds()
                    self.show("Fehler", [recorder.error, "udev-Regel prüfen"], REC_COLOR, 4)
                    self.log(f"Aufnahme nicht möglich: {recorder.error}")
                self.next_draw = 0
            return                          # G-Tasten lösen während der Aufnahme nichts aus
        macro = self.store.get(self.prof_idx, self.layer, name)
        if run_gkey_action(self, macro, name):
            return
        # Eintrag nur mit "name" (oder keiner): die Taste sendet F13–F24 (für KDE-Kurzbefehle)
        e, mod = self.e, self.modifiers[self.layer]
        self.held[name] = mod
        with self.ui_lock:
            if mod:
                self.ui.write(e.EV_KEY, mod, 1)
            self.ui.write(e.EV_KEY, self.fkeys[i], 1)
            self.ui.syn()
        if self.args.debug:
            print(f"  {name} gedrückt -> {'Strg+' if mod == e.KEY_LEFTCTRL else 'Alt+' if mod else ''}F{FKEY_BASE + i}")

    def _gkey_up(self, i, name):
        e, mod = self.e, self.held.pop(name)
        with self.ui_lock:
            self.ui.write(e.EV_KEY, self.fkeys[i], 0)
            if mod:
                self.ui.write(e.EV_KEY, mod, 0)
            self.ui.syn()
        if self.args.debug:
            print(f"  {name} losgelassen")

    # --- Displaytasten ------------------------------------------------------- #
    def handle_display_report(self, data):
        if not data:
            return
        if self.args.debug:
            print("Display-Report:", data.hex(" "))
        value = data[0]
        pressed = value & ~self.prev_l
        self.prev_l = value
        if pressed:
            pressed = self._key_precedence(pressed)
        if self.menu is None and pressed & LKEY_BITS["SETTINGS"]:
            self.menu = ProfileMenu(self.prof_idx)          # SETTINGS öffnet die Profilauswahl
            self.flash = None
            self.next_draw = 0
        elif self.menu is not None:
            self.menu.on_key(self, pressed)
        else:
            handler = PAGE_KEYS.get(PAGE_IDS[self.page % len(PAGE_IDS)])
            if not (handler and handler(self, pressed)):
                self.nav_keys(pressed, LKEY_BITS["RIGHT"] | LKEY_BITS["DOWN"], LKEY_BITS["LEFT"] | LKEY_BITS["UP"])
        if self.args.debug:
            for name, bit in LKEY_BITS.items():
                if pressed & bit:
                    print(f"  Displaytaste {name}")

    def _key_precedence(self, pressed):
        """Tastendrücke, die nur wecken/beenden/bestätigen, werden hier verbraucht (→ 0)."""
        self.activity.touch()
        if self.wake():
            pressed = 0                     # erster Druck in der Nacht weckt nur das Display
            self.next_draw = 0
        if self.saver["active"]:
            pressed = 0                     # Bildschirmschoner: Tastendruck beendet ihn nur
        if self.timer.alarm and pressed:
            self.dismiss_alarm()            # abgelaufenen Timer bestätigen
            pressed = 0
        if self.modal and pressed:
            self.modal = False
            if self.flash and time.monotonic() < self.flash[1]:
                self.flash = None           # Terminerinnerung / Unwetter bestätigen
                pressed = 0
                self.next_draw = 0
        return pressed


# ═══════════════════════════════════════════════════════════════════════════
# Modul app_zeit
#   Zeitaufgaben der Hauptschleife – werden bei jedem Durchlauf aufgerufen.
#
#   Reihenfolge je Durchlauf (tick):
#     Menü-/Markierungs-Zeitlimits, Mikrofonstatus, Einschlaftimer,
#     Unwetter/Terminerinnerung/Radiowecker (sofort bei neuen Daten, sonst alle 20 s),
#     automatische Sicherung (alle 10 min prüfen), Timer und Blinken,
#     Dateien neu laden (alle 2 s), Nachtmodus, Bildschirmschoner, Benachrichtigungen.
# ═══════════════════════════════════════════════════════════════════════════

class TimedTasks:
    def poll_recording(self):
        """Laufende Makroaufnahme mitlesen (zeigt die Anzahl der Tastendrücke)."""
        if self.rec and self.rec["stage"] == "record":
            before = self.rec["recorder"].keycount
            self.rec["recorder"].poll()
            if self.rec["recorder"].keycount != before:
                self.next_draw = 0

    def tick(self, now):
        self._expire_selections(now)
        if self.mic.pop("changed", False):
            self.apply_leds()
            self.next_draw = 0
        self._sleep_timer(now)
        fresh = (self.calendar.snapshot()[2], self.alerts.snapshot()[2])
        if now >= self.periodic["remind"] or fresh != self.periodic["fresh"]:
            self.periodic["remind"], self.periodic["fresh"] = now + 20, fresh
            self.warn_due()
            self.remind_due()
            self.alarm_clock_due()
        if now >= self.periodic["backup"]:
            self.periodic["backup"] = now + 600
            self.backup_due()
        self._timer_tick(now)
        self._blink(now)
        badge = self.timer.badge(now) if (self.timer.active and not (self.menu and self.menu.kind == "timer")) else ""
        if badge != self.renderer.timer_badge:
            self.renderer.timer_badge = badge
            self.next_draw = min(self.next_draw, now)
        if now >= self.next_reload:
            self._reload_files()
            self.next_reload = now + 2.0
        self._night_rewake(now)
        self._screensaver()
        self._notifications()

    # --- Zeitlimits ------------------------------------------------------- #
    def _expire_selections(self, now):
        if self.menu is not None and self.menu.expired(now):
            self.menu = None                # Menü schließt sich nach 30 s ohne Tastendruck
            self.next_draw = 0
        r = self.renderer
        if r.cal_sel is not None and self.menu is None and now - self.sel_t["calendar"] > SELECTION_TIMEOUT:
            r.cal_sel = None                # Terminmarkierung verschwindet wieder
            self.next_draw = 0
        for k in r.sel:
            if r.sel[k] is not None and self.menu is None and now - self.sel_t[k] > SELECTION_TIMEOUT:
                r.sel[k] = None
                self.next_draw = 0

    # --- Einschlaftimer ------------------------------------------------------ #
    def _sleep_timer(self, now):
        sleep = self.sleep
        if not sleep["until"]:
            return
        left = sleep["until"] - now
        badge = f"{max(1, int(left // 60) + (1 if left % 60 else 0))}"
        if left <= 0:
            sleep["until"] = 0.0
            badge = ""
            info = self.media.snapshot()[0]
            if self.radio.playing:
                self.radio.stop()
                self.media.wake.set()
            elif info and info.get("status") == "Playing":
                threading.Thread(target=self.media.control, args=("play-pause",), daemon=True).start()
            self.log("Einschlaftimer abgelaufen – Musik aus")
            self.show("Gute Nacht", ["Musik ausgeschaltet"], PROFILE_COLOR[self.layer], 3)
        if badge != self.renderer.sleep_badge:
            self.renderer.sleep_badge = badge
            self.next_draw = 0

    # --- Einblendungen mit Vorrang (Unwetter, Termine) ---------------------- #
    def _attention(self, draw_fn, seconds, blink):
        """Wichtige Einblendung: weckt das Display, blinkt, Signalton; nächster Tastendruck bestätigt."""
        self.wake(120)
        self.popup(draw_fn, seconds)
        self.modal = True
        self.alarm.update(blink_until=time.monotonic() + blink, blink_at=0.0)
        if self.settings().get("timer_sound", True):
            play_alarm(self.launcher._env(), 1)

    def warn_due(self):
        """Neue Unwetterwarnung (ab Stufe „markant“) einmal groß einblenden."""
        if not (self.settings().get("warnings") or {}).get("popup", True):
            return
        data = self.alerts.snapshot()[0] or {}
        for a in data.get("alerts") or []:
            if a["id"] in self.seen_alerts:
                continue
            self.seen_alerts.add(a["id"])
            if SEVERITY_RANK.get(a["severity"], 0) < 2:
                continue
            label, color = SEVERITY.get(a["severity"], SEVERITY["minor"])
            until = a["expires"].strftime("%H:%M") if a.get("expires") else ""
            self.log(f"{label}: {a['event']}")
            self._attention(lambda a=a, l=label, c=color, u=until: self.renderer.render_message(
                "⚠ " + l, [a["event"], (f"bis {u} Uhr" if u else ""), "Details: Seite „Unwetter“"], c), 15, 4)
            return

    def remind_due(self):
        """Termine ankündigen, die in den nächsten N Minuten beginnen."""
        import datetime as dt
        minutes = int((self.settings().get("calendar") or {}).get("remind") or 0)
        if minutes <= 0:
            return
        data = self.calendar.snapshot()[0] or {}
        now_dt = dt.datetime.now().astimezone()
        for ev in data.get("items") or []:
            if ev.get("allday") or ev.get("cal") in self.renderer.cal_hidden:
                continue
            delta = (ev["start"] - now_dt).total_seconds()
            key = (ev.get("cal"), ev.get("title"), ev["start"].isoformat())
            if -60 <= delta <= minutes * 60 and key not in self.reminded:
                self.reminded.add(key)
                if delta < -30:
                    continue                # schon angefangen (z. B. nach dem Start des Treibers)
                cal = next((c for c in self.calendar_list() if c["key"] == ev.get("cal")), None)
                mins = max(0, int(round(delta / 60)))
                color = ev.get("color") or (cal or {}).get("color")
                self.log(f"Terminerinnerung: {ev.get('title')} um {ev['start'].strftime('%H:%M')}")
                self._attention(lambda ev=ev, m=mins, c=color, n=(cal or {}).get("name", ""):
                                self.renderer.render_reminder(ev, m, c, n), 20, 3)
                return                      # höchstens eine Erinnerung gleichzeitig

    def alarm_clock_due(self):
        """Radiowecker: zur eingestellten Zeit den gewählten Sender einschalten."""
        a = self.settings().get("alarm_clock") or {}
        if not a.get("enabled"):
            return
        today = time.strftime("%Y-%m-%d")
        if self.periodic["alarm_day"] == today or time.strftime("%H:%M") != str(a.get("time") or ""):
            return
        if time.localtime().tm_wday not in (a.get("days") or []):
            return
        self.periodic["alarm_day"] = today
        stations = [s for s in self.settings().get("stations", []) if s.get("url")]
        st = next((s for s in stations if s["url"] == a.get("station")), stations[0] if stations else None)
        self.log("Radiowecker: " + (st.get("name") or st["url"] if st else "kein Sender"))
        self.wake(600)
        if st:
            threading.Thread(target=self.radio_play, args=(st, False), daemon=True).start()
        self.popup(lambda: self.renderer.render_message("Guten Morgen!", [time.strftime("%H:%M"),
                   (st or {}).get("name") or ""], PROFILE_COLOR[self.layer]), 8)

    def backup_due(self):
        """Automatische Sicherung, wenn die letzte älter als eingestellt ist (läuft im Hintergrund)."""
        b = self.settings().get("backup") or {}
        target = b.get("target") or "folder"
        if not b.get("enabled") or not b.get("folder" if target == "folder" else "url") or self.periodic["backup_busy"]:
            return
        try:
            last = float(load_state().get("last_backup") or 0)
        except (TypeError, ValueError):
            last = 0
        if time.time() - last < max(1, int(b.get("days") or 7)) * 86400:
            return
        self.periodic["backup_busy"] = True

        def work():
            try:
                path = auto_backup(b, b.get("keep", 8))
                save_state(last_backup=time.time(), last_backup_file=path, last_backup_error="")
                self.log(f"Automatische Sicherung: {path}")
            except Exception as ex:         # im Hintergrund: jeden Fehler melden statt still abbrechen
                save_state(last_backup_error=str(ex))
                self.log(f"Automatische Sicherung fehlgeschlagen: {ex}")
            finally:
                try:
                    self.state_mtime = os.path.getmtime(STATE_FILE)
                except OSError:
                    pass
                self.periodic["backup_busy"] = False
        threading.Thread(target=work, daemon=True).start()

    # --- Timer --------------------------------------------------------------- #
    def _timer_tick(self, now):
        tev = self.timer.tick(now)
        if not tev:
            return
        t_color = PROFILE_COLOR[self.layer]
        if self.settings().get("timer_sound", True):
            play_alarm(self.launcher._env(), 3 if tev == "done" else 1)
        if tev == "done":
            self.log(f"{timer_label(self.timer.cfg or {})} abgelaufen")
            self.menu = TimerView()
            self.flash = None
            self.alarm.update(blink_until=now + 20, blink_at=0.0)
            self.wake(120)
        else:
            txt = "Pause!" if tev == "break" else "Weiterarbeiten"
            self.log(f"Pomodoro: {txt}")
            rounds = self.timer.rounds
            self.popup(lambda txt=txt, c=t_color, r=rounds: self.renderer.render_message(
                "Pomodoro", [txt, f"{r} Runde{'' if r == 1 else 'n'} geschafft"], c), 5)
            self.alarm.update(blink_until=now + 4, blink_at=0.0)
        self.next_draw = 0

    def _blink(self, now):
        """Beleuchtung rot/gelb blinken lassen (Timer, Erinnerung, Unwetter)."""
        alarm = self.alarm
        if not alarm["blink_until"]:
            return
        if now >= alarm["blink_until"]:
            alarm["blink_until"] = 0.0
            self.apply_leds()
        elif now >= alarm["blink_at"]:
            alarm["on"] = not alarm["on"]
            alarm["blink_at"] = now + 0.4
            try:
                self.g19.set_backlight(*((255, 30, 30) if alarm["on"] else (255, 200, 40)))
            except Exception:               # Beleuchtung ist nicht kritisch
                pass

    # --- Dateien, Nacht, Bildschirmschoner, Benachrichtigungen --------------- #
    def _reload_files(self):
        """macros.json, state.json und settings.json auf Änderungen prüfen."""
        if self.store.reload():
            self.apply_profile()            # Farben/Namen/Seiten können sich geändert haben
            self.apply_leds()
            self.fix_page()
        self.check_state_file()
        if self.reload_settings():
            self.apply_settings()
            self.update_night(force=True)
            if self.page not in self.visible_pages() and not self.saver["active"]:
                self.page = self.visible_pages()[0]
            self.next_draw = 0
        self.update_night()
        self.launcher.reap()

    def _night_rewake(self, now):
        """Nachts geweckt: nach Ablauf wieder abdunkeln."""
        if self.night["active"] and self.night["wake_until"] and now >= self.night["wake_until"]:
            self.night["wake_until"] = 0.0
            self.set_brightness(self.night_brightness())
            self.apply_leds()
            self.next_draw = 0

    def _screensaver(self):
        ss, saver = self.settings().get("screensaver") or {}, self.saver
        if saver["active"] and self.activity.last > saver["since"]:
            saver["active"] = False
            if saver["page"] is not None:
                self.page = saver["page"]
            self.next_draw = 0
        elif (ss.get("enabled") and not saver["active"] and not self.rec and self.menu is None
              and self.activity.idle() >= max(0.02, float(ss.get("minutes") or 5)) * 60):
            target = PAGE_IDS.index(ss.get("page")) if ss.get("page") in PAGE_IDS else Renderer.SLIDES_PAGE
            if self.page != target:
                saver.update(active=True, page=self.page, since=time.monotonic())
                self.page = target
                self.next_draw = 0

    def _notifications(self):
        if self.popups and not self.rec and self.menu is None:
            app_name, summary, body = self.popups.popleft()
            if not self.night_dark():
                secs = max(2, min(30, int((self.settings().get("notifications") or {}).get("seconds") or 6)))
                color = PROFILE_COLOR[self.layer]
                self.popup(lambda: self.renderer.render_notification(app_name, summary, body, color), secs)
                self.log(f"Benachrichtigung: {app_name} – {summary}")


# ═══════════════════════════════════════════════════════════════════════════
# Modul app
#   Hauptanwendung: Hauptschleife, Displayausgabe, Beenden.
#
#   App setzt sich zusammen aus
#       AppCore        (app_kern)    Aufbau, Zustand, Profile/Seiten, Licht, Nachtmodus
#       KeyHandling    (app_tasten)  G-/M-Tasten, Makroaufnahme, Displaytasten
#       TimedTasks     (app_zeit)    Zeitaufgaben
#   und zeichnet in draw() das passende Bild (Nacht, Menü, Aufnahme, Einblendung, Seite).
# ═══════════════════════════════════════════════════════════════════════════

class App(AppCore, KeyHandling, TimedTasks):
    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.reload_settings()
        self.apply_settings(first=True)
        self.update_night(force=True)
        self.apply_leds()
        try:
            self.page = int(self.settings().get("start_page", 0)) % len(PAGE_IDS)
        except (TypeError, ValueError):
            self.page = 0
        if self.page not in self.visible_pages():
            self.page = self.visible_pages()[0]
        self.log("G19s-Treiber läuft. Beenden mit Strg+C.")
        self.log(f"Makrodatei: {MACRO_FILE}")
        import queue
        reports = queue.Queue()
        self.readers = [UsbReader(self.g19, EP_GKEYS, 20, reports), UsbReader(self.g19, EP_LKEYS, 2, reports)]
        for r in self.readers:
            r.start()
        try:
            while self.running:
                try:                        # schlafen bis Tastendruck, nächstes Bild oder spätestens _max_wait
                    item = reports.get(timeout=max(0.0, min(self.next_draw - time.monotonic(), self._max_wait())))
                    while item is not None:
                        self._handle_report(*item)
                        item = reports.get_nowait()
                except queue.Empty:
                    pass
                self.poll_recording()
                now = time.monotonic()
                self.tick(now)
                if now >= self.next_draw:
                    self.draw(now)
        finally:
            for r in getattr(self, "readers", []):
                r.running = False
            self.shutdown()

    def _handle_report(self, source, data):
        if source == "error":
            raise data                      # USB-Fehler aus dem Lese-Thread: wie bisher beenden
        if source == EP_GKEYS:
            self.handle_gm_report(data)
        else:
            self.handle_display_report(data)

    def _max_wait(self):
        """Wie lange die Hauptschleife höchstens schlafen darf: kurz während Makroaufnahme und
        Blinken, sonst 0,25 s (Zeitaufgaben wie Erinnerungen, Nachtmodus, Menü-Zeitlimit)."""
        if self.rec is not None and self.rec.get("stage") == "record":
            return 0.02
        if self.alarm["blink_until"]:
            return 0.05
        return 0.25

    def stop(self, *_):
        self.running = False

    def draw(self, now):
        """Das Bild wählen, das gerade gezeigt werden soll, und senden."""
        r, rec, menu = self.renderer, self.rec, self.menu
        r.clock_face = self.clock_face()
        if not self.media.fast_now and PAGE_IDS[self.page % len(PAGE_IDS)] == "music":
            self.media.fast_now = True
            self.media.wake.set()           # Musikseite wurde gerade sichtbar: sofort abfragen
        if self.night_dark() and (self.settings().get("night") or {}).get("mode") == "off" and not rec and menu is None:
            self._send(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)), now)
            self.next_draw = now + 5
            return
        try:
            img = self._compose(now)
        except Exception as ex:             # eine fehlerhafte Seite darf Treiber und G-Tasten nie stoppen
            img = self._draw_error(ex)
        self._send(img, now)
        fast = rec or self.flash or (self.menu and self.menu.kind == "timer")
        if not fast and self.menu is None and PAGE_IDS[self.page % len(PAGE_IDS)] == "clock":
            fps = clock_fps(r.clock_face, self.settings())
            if fps > 1 and not self.night_dark():   # bewegte Zifferblätter; nachts (gedimmt) 1 Bild/s
                self.next_draw = now + 1.0 / fps
            else:                           # kurz nach jedem Sekundenwechsel, damit kein Sekundenschritt fehlt
                self.next_draw = now + (1.0 - time.time() % 1.0) + 0.02
        else:
            self.next_draw = now + (0.5 if fast else 1.0)

    def _compose(self, now):
        """Menü, Aufnahme, Einblendung oder Seite zeichnen."""
        r, rec, menu = self.renderer, self.rec, self.menu
        if menu is not None and not rec:
            img = menu.draw(self, now)      # None = Menü hat sich geschlossen (z. B. Timer beendet)
            if img is None:
                img = r.render(self.page, self.layer, self.store.keys(self.prof_idx))
        elif rec and rec["stage"] == "select":
            img = r.render_message("Makro aufnehmen", [f"Profil {self.layer}", "G-Taste drücken", "MR = abbrechen"],
                                   REC_COLOR)
        elif rec:
            img = r.render_message(f"● Aufnahme {rec['gkey']}", [f"{rec['recorder'].keycount} Tastendrücke",
                                                                "Tasten jetzt tippen", "MR = speichern"], REC_COLOR)
        elif self.flash and now < self.flash[1]:
            img = self.flash[0]()
        else:
            self.flash = None
            img = r.render(self.page, self.layer, self.store.keys(self.prof_idx))
        return img

    def _draw_error(self, ex):
        """Fehlerseite statt Absturz; jeder Fehler steht einmal (mit Ort) im Protokoll."""
        import traceback
        where = self.menu.kind if self.menu is not None else PAGE_NAMES[self.page % len(PAGE_IDS)]
        text = f"{type(ex).__name__}: {ex}"
        if (where, text) != self._last_draw_error:
            self._last_draw_error = (where, text)
            self.log(f"Anzeige-Fehler auf „{where}“: {text}\n" + "".join(traceback.format_exc(limit=4)).rstrip())
        if self.menu is not None:
            self.menu = None                # kaputtes Menü schließen, damit die Tasten wieder gehen
        self.flash = None
        try:
            return self.renderer.render_message("Anzeige-Fehler", [where, text[:40], "Details: Protokoll"], REC_COLOR)
        except Exception:                   # selbst die Meldung geht nicht: schwarzes Bild
            return Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

    FRAME_REFRESH = 10.0            # unverändertes Bild spätestens nach so vielen Sekunden erneut senden

    def _send(self, img, now):
        """Bild nur senden, wenn es sich geändert hat (spart USB-Verkehr und CPU); zur Sicherheit
        – etwa nach kurzem Abziehen der Tastatur – alle FRAME_REFRESH Sekunden trotzdem."""
        data = img.tobytes()
        if data == self._last_frame and now - self._last_sent < self.FRAME_REFRESH:
            return
        self.g19.send_frame(img)
        self._last_frame, self._last_sent = data, now

    def shutdown(self):
        if self.rec and self.rec["stage"] == "record":
            self.rec["recorder"].stop()
        try:
            self.g19.send_frame(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))
        except Exception:                   # Tastatur evtl. schon abgezogen
            pass
        for s in (self.media, self.slideshow, self.weather, self.calendar, self.activity, self.notifier):
            s.stop()
        self.radio.stop()
        self.ui.close()
        self.g19.close()
        print("Beendet.")


def run(args):
    App(args).run()


# ═══════════════════════════════════════════════════════════════════════════
# Modul start
#   Aufruf von der Kommandozeile: Optionen, Vorschau-Bilder, Start des Treibers.
# ═══════════════════════════════════════════════════════════════════════════

def preview(prefix):
    r = Renderer()
    r.stats.cpu_percent()
    time.sleep(0.2)
    demo = {"M1": {"G1": {"name": "Test-Satz"}, "G2": {"open": "https://www.heise.de/news"},
                   "G3": {"name": "Golem", "open": "https://www.golem.de"},
                   "G5": {"name": "Makro G5"},
                   "G9": {"name": "Sehr langer Makroname zum Testen"}}}
    media = MediaWatcher(lambda: dict(os.environ))
    media._poll()          # einmal abfragen (zeigt echte Wiedergabe, falls vorhanden)
    r.media = media
    for p in range(Renderer.PAGES):
        path = f"{prefix}_{p + 1}.png"
        r.render(p, "M1", demo).save(path)
        print("gespeichert:", path)
    r.render_message("● Aufnahme G5", ["3 Tastendrücke", "Tasten jetzt tippen",
                                        "MR = speichern"], REC_COLOR).save(f"{prefix}_rec.png")
    print("gespeichert:", f"{prefix}_rec.png")


def main():
    ap = argparse.ArgumentParser(description="Treiber für Logitech G19/G19s (Display + G-Tasten)")
    ap.add_argument("--debug", action="store_true", help="Rohdaten der Tasten ausgeben")
    ap.add_argument("--brightness", type=int, metavar="0-100", help="Displayhelligkeit setzen")
    ap.add_argument("--keep-backlight", action="store_true",
                    help="Tastaturbeleuchtung nicht je Profil umfärben")
    ap.add_argument("--preview", metavar="PREFIX", help="Displayseiten als PNG speichern (ohne Tastatur)")
    args = ap.parse_args()
    if args.preview:
        preview(args.preview)
    else:
        run(args)


if __name__ == "__main__":
    main()


# G19S-DATEIENDE (diese Zeile zeigt, dass die Datei vollständig ist)
