"""Feste Werte: USB-Kennungen und Endpunkte, Tastenbits, Displaygröße, Farben, Dateipfade, Seiten-IDs."""


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
