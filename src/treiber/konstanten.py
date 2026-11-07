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
FOOTER_H = 26               # Höhe der Fußzeile (Profil, Seitenpunkte) unten auf jeder Seite
FKEY_BASE = 13              # G1 sendet F13, G12 sendet F24
SELECTION_TIMEOUT = 30      # Sekunden, nach denen eine Markierung (Termin, Meldung) verschwindet

# G-/M-Tasten (Report-ID 0x02): Wert = d[1] | d[2] << 8
#   d[1]: G1–G8, d[2]: G9–G12 (Bits 0–3), M1/M2/M3/MR (Bits 4–7)
GKEY_BITS = {f"G{i + 1}": 1 << i for i in range(12)}
GKEY_MASK = 0x0FFF
MKEY_BITS = {"M1": 0x1000, "M2": 0x2000, "M3": 0x4000, "MR": 0x8000}

# Displaytasten: erstes Byte
LKEY_BITS = {
    "SETTINGS": 0x01, "BACK": 0x02, "MENU": 0x04, "OK": 0x08,
    "RIGHT": 0x10, "LEFT": 0x20, "DOWN": 0x40, "UP": 0x80,
}
MPV_BUFFER = "--demuxer-max-bytes=4MiB --demuxer-max-back-bytes=1MiB"   # an mpv angehängt (außer eigene Puffer-Angaben)
LAYER_OVERLAY_SECONDS = 2.0  # M1/M2/M3: so lange die Belegung der G-Tasten einblenden ("layer_overlay")
HOLD_BAR_AFTER = 0.25       # SETTINGS so lange gehalten: Balken bis zur Profilauswahl zeigen
LONG_PRESS = 1.0            # Sekunden: SETTINGS so lange halten = Profilauswahl (kurz: Uhrseite → Zifferblätter)

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
            "news", "warnings", "network", "updates", "visual"]
PAGE_NAMES = ["Uhr", "Musik", "Makros", "Bilder", "Wetter", "Termine", "Hardware",
              "Nachrichten", "Unwetter", "Netzwerk", "Updates", "Visualisierung"]
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
# Farben, die am Display für Farb-Optionen der Zifferblätter durchgeschaltet werden (None = Standard)
CLOCK_COLOR_CHOICES = [
    (None, "Standard"), ([255, 255, 255], "Weiß"), ([230, 40, 40], "Rot"), ([255, 140, 0], "Orange"),
    ([255, 215, 0], "Gelb"), ([40, 200, 80], "Grün"), ([0, 200, 200], "Türkis"), ([30, 120, 255], "Blau"),
    ([150, 80, 255], "Violett"), ([255, 80, 180], "Pink"),
]
# Stile der Seite „Visualisierung“ (Auswahl am Display mit MENU, gespeichert in settings.json → "visual")
VISUAL_STYLES = {
    "eq": "Grafik-Equalizer", "dancer": "Tanzendes Mädchen", "lights": "Lichtshow", "scope": "Oszilloskop",
    "ring": "Kreis-Spektrum", "vu": "VU-Meter", "spectro": "Spektrogramm", "fireworks": "Feuerwerk",
    "xmas": "Weihnachten",
}
VISUAL_FPS = 15             # Bilder je Sekunde der Visualisierung (Standard; einstellbar 10–25: visual.fps)
# Stichwörter im Titel des Senders, die einen Wortbeitrag anzeigen (Tänzerin langweilt sich); änderbar
TALK_WORDS = "Nachrichten, News, Werbung, Werbepause, Verkehr, Wetter"
# Einstellungen je Stil (Verwaltung → Beleuchtung & Display → Visualisierung, am Display ►), wie CLOCK_OPTIONS
VISUAL_OPTIONS = {
    "eq": [
        {"key": "bars", "label": "Anzahl der Balken", "type": "choice", "default": "32",
         "choices": [["16", "16"], ["24", "24"], ["32", "32"], ["48", "48"]]},
        {"key": "colors", "label": "Farben", "type": "choice", "default": "led",
         "choices": [["led", "Grün-Gelb-Rot (LED)"], ["rainbow", "Regenbogen"], ["layer", "Farbe der Ebene"]]},
        {"key": "mirror", "label": "Gespiegelt (von der Mitte aus)", "type": "bool", "default": False},
        {"key": "peaks", "label": "Spitzenmarken", "type": "bool", "default": True},
    ],
    "dancer": [
        {"key": "color", "label": "Farbe der Tänzerin", "type": "color", "default": None, "none_label": _LAYER},
        {"key": "stage", "label": "Bühnenlicht", "type": "bool", "default": True},
    ],
    "lights": [
        {"key": "beams", "label": "Scheinwerfer", "type": "choice", "default": "5",
         "choices": [["3", "3"], ["5", "5"], ["7", "7"]]},
        {"key": "flash", "label": "Sanfter Blitz bei kräftigen Schlägen", "type": "bool", "default": True},
        {"key": "strobe", "label": "Stroboskop (Vorsicht bei Lichtempfindlichkeit)", "type": "choice", "default": "off",
         "choices": [["off", "Aus"], ["beat", "Auf hohe Schläge (Hi-Hat, Snare)"], ["drop", "Salven bei Höhepunkten"],
                     ["both", "Hohe Schläge und Salven"]]},
        {"key": "strobe_rate", "label": "Stroboskop: höchstens … Blitze je Sekunde", "type": "choice", "default": "2",
         "choices": [["1", "1"], ["2", "2"], ["3", "3"]]},
        {"key": "strobe_color", "label": "Stroboskop: Farbe", "type": "choice", "default": "white",
         "choices": [["white", "Weiß"], ["beam", "Farbe der Scheinwerfer"], ["layer", "Farbe der Ebene"]]},
        {"key": "strobe_keys", "label": "Stroboskop: Tastaturbeleuchtung blitzt mit", "type": "bool", "default": False},
    ],
    "scope": [
        {"key": "mode", "label": "Darstellung", "type": "choice", "default": "line",
         "choices": [["line", "Schwingung"], ["xy", "Stereo-Figur (links/rechts)"]]},
        {"key": "color", "label": "Farbe", "type": "color", "default": None, "none_label": "Grün (Standard)"},
        {"key": "glow", "label": "Nachleuchten", "type": "bool", "default": True},
    ],
    "ring": [
        {"key": "colors", "label": "Farben", "type": "choice", "default": "rainbow",
         "choices": [["rainbow", "Regenbogen"], ["layer", "Farbe der Ebene"]]},
    ],
    "vu": [
        {"key": "dial", "label": "Skala", "type": "choice", "default": "cream",
         "choices": [["cream", "Hell (klassisch)"], ["dark", "Dunkel mit bernsteinfarbenem Licht"]]},
    ],
    "spectro": [
        {"key": "palette", "label": "Farben", "type": "choice", "default": "fire",
         "choices": [["fire", "Glut"], ["ice", "Eis"], ["rainbow", "Regenbogen"]]},
    ],
    "fireworks": [
        {"key": "trails", "label": "Leuchtspuren", "type": "bool", "default": True},
    ],
    "xmas": [
        {"key": "dance", "label": "Tanz", "type": "choice", "default": "auto",
         "choices": [["auto", "Abwechselnd"], ["pair", "Paartanz"], ["santa", "Weihnachtsmann allein"],
                     ["mrs", "Weihnachtsfrau allein"]]},
        {"key": "every", "label": "Wechsel bei „Abwechselnd“", "type": "choice", "default": "60",
         "choices": [["30", "alle 30 Sekunden"], ["60", "jede Minute"], ["120", "alle 2 Minuten"],
                     ["300", "alle 5 Minuten"], ["600", "alle 10 Minuten"]]},
        {"key": "snow", "label": "Schneefall", "type": "choice", "default": "normal",
         "choices": [["light", "Leicht"], ["normal", "Normal"], ["heavy", "Dicht"]]},
        {"key": "lights", "label": "Lichterkette blinkt im Takt", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "redgreen",
         "choices": [["redgreen", "Rot und Grün im Takt"], ["layer", "Farbe der Ebene"]]},
        {"key": "party", "label": "Feierabend: Glühwein-Gags (derber Humor)", "type": "choice", "default": "off",
         "choices": [["off", "Aus"], ["on", "An"], ["evening", "Nur abends (20 bis 4 Uhr)"]]},
        {"key": "party_len", "label": "Dauer einer Feierabend-Runde", "type": "choice", "default": "600",
         "choices": [["300", "5 Minuten"], ["600", "10 Minuten"], ["900", "15 Minuten"], ["1200", "20 Minuten"]]},
        {"key": "party_meter", "label": "Feierabend: Glühwein-Barometer und Becherzähler", "type": "bool",
         "default": True},
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
