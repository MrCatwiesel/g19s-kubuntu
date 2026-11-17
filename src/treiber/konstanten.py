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
            "news", "warnings", "network", "updates", "visual", "video"]
PAGE_NAMES = ["Uhr", "Musik", "Makros", "Bilder", "Wetter", "Termine", "Hardware",
              "Nachrichten", "Unwetter", "Netzwerk", "Updates", "Visualisierung", "Video"]
# Seite „Video“: ab Werk die „Tagesschau in 100 Sekunden“ (Video-Podcast der ARD)
VIDEO_DEFAULT_FEED = ("https://www.tagesschau.de/multimedia/sendung/tagesschau_in_100_sekunden/"
                      "podcast-ts100-video-100~podcast.xml")
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
#   birthdays: Geburtstagsliste (Name, Tag, Monat, Geburtsjahr oder 0)
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
    "eq": "Grafik-Equalizer", "dancer": "Tänzerin an der Stange", "lights": "Lichtshow", "scope": "Oszilloskop",
    "ring": "Kreis-Spektrum", "vu": "VU-Meter", "spectro": "Spektrogramm", "fireworks": "Feuerwerk",
    "xmas": "Weihnachten", "party": "Überraschungsparty", "cellar": "Kellertreppe",
    "metal": "Mittelalter-Metal", "easter": "Ostern",
    "halloween": "Halloween", "horror": "Horror",
    "birthday": "Geburtstag", "mother": "Muttertag", "father": "Männertag",
    "newyear": "Silvester",
    "carnival": "Fasching",
    "oktoberfest": "Oktoberfest",
    "martin": "St. Martin",
    "valentine": "Valentinstag",
    "underwater": "Unterwasser-Band",
    "farm": "Bauernhof-Band",
    "space": "Weltraum-Disco",
    "arcade": "Retro-Arcade",
    "western": "Western-Saloon",
    "campfire": "Lagerfeuer",
    "cats": "Katzenchor",
    "silk": "Seidenschleier",
    "ember": "Abendglut",
    "pulse": "Herzschlag-Aura",
    "jazz": "Lounge / Jazz-Club",
    "auto": "Automatisch nach Musik",
}
VISUAL_FPS = 15             # Bilder je Sekunde der Visualisierung (Standard; einstellbar 10–25: visual.fps)
VISUAL_FPS_QUIET = 8        # anpassende Bildrate (visual.adaptive): bei Stille/Wortbeitrag …
VISUAL_FPS_MIN = 8          # … und als Untergrenze der Lastbremse
VISUAL_LOAD_SHARE = 0.5     # Lastbremse: Zeichnen darf höchstens diesen Anteil der Bildzeit brauchen
DIAG_LOG_EVERY = 600        # Diagnosewerte der Visualisierung so oft (s) ins Protokoll
# Stichwörter im Titel des Senders, die einen Wortbeitrag anzeigen (Tänzerin langweilt sich); änderbar
TALK_WORDS = "Nachrichten, News, Werbung, Werbepause, Verkehr, Wetter"
# Stroboskop (Lichtshow und Tänzerin): höchstens 3 Blitze je Sekunde – mehr gilt als riskant für Lichtempfindliche
_STROBE_OPTIONS = [
    {"key": "strobe", "label": "Stroboskop (Vorsicht bei Lichtempfindlichkeit)", "type": "choice", "default": "off",
     "choices": [["off", "Aus"], ["beat", "Auf hohe Schläge (Hi-Hat, Snare)"], ["drop", "Salven bei Höhepunkten"],
                 ["both", "Hohe Schläge und Salven"]]},
    {"key": "strobe_rate", "label": "Stroboskop: höchstens … Blitze je Sekunde", "type": "choice", "default": "2",
     "choices": [["1", "1"], ["2", "2"], ["3", "3"]]},
    {"key": "strobe_color", "label": "Stroboskop: Farbe", "type": "choice", "default": "white",
     "choices": [["white", "Weiß"], ["beam", "Farbe der Scheinwerfer"], ["layer", "Farbe der Ebene"]]},
    {"key": "strobe_keys", "label": "Stroboskop: Tastaturbeleuchtung blitzt mit", "type": "bool", "default": False},
]
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
        {"key": "color", "label": "Farbe des Trikots", "type": "color", "default": None,
         "none_label": "Weinrot (Standard)"},
        {"key": "stage", "label": "Bühnenlicht", "type": "bool", "default": True},
        {"key": "hair", "label": "Haarfarbe", "type": "choice", "default": "dark",
         "choices": [["dark", "Dunkelbraun"], ["black", "Schwarz"], ["brown", "Braun"], ["auburn", "Kupfer"],
                     ["red", "Rot"], ["blond", "Blond"], ["platinum", "Platinblond"], ["silver", "Silbergrau"],
                     ["pink", "Pink"], ["blue", "Blau"]]},
        {"key": "show", "label": "Lichtprogramm", "type": "choice", "default": "off",
         "choices": [["off", "Aus (Studio)"], ["beams", "Scheinwerfer"],
                     ["club", "Disco (abgedunkelt, Scheinwerfer, Spiegelkugel, Lichtpunkte)"],
                     ["ballet", "Ballett (Verfolgerspot, Stimmungsfarben, Nebel, Gegenlicht)"],
                     ["night", "Clubnacht (Moving Heads, Laser, Nebel, Schwarzlicht, Lauflicht)"],
                     ["gala", "Show (Verfolgerspot, Moving Heads, Laser, Nebel, Blinder …)"],
                     ["custom", "Eigene Auswahl (Effekte unten)"]]},
        {"key": "beams", "label": "Lichtshow: Scheinwerfer", "type": "choice", "default": "5",
         "choices": [["3", "3"], ["5", "5"], ["7", "7"]]},
    ] + [{"key": "fx_" + k, "label": "Eigene Auswahl: " + label, "type": "bool", "default": False} for k, label in (
        ("beams", "Scheinwerferkegel"), ("follow", "Verfolgerspot"), ("heads", "Moving Heads"), ("laser", "Laser"),
        ("haze", "Nebel"), ("chase", "Lauflicht am Boden"), ("silhouette", "Silhouette im Gegenlicht bei ruhigen Stellen"),
        ("uv", "Schwarzlicht (UV)"), ("mood", "Farben nach Stimmung"), ("ball", "Spiegelkugel mit Lichtpunkten"),
        ("blinder", "Blinder beim Höhepunkt"))] + [
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "bass",
         "choices": [["bass", "Pulsiert mit dem Bass"], ["stage", "Farbe des Bühnenlichts"],
                     ["hats", "Blitzt auf hohe Schläge (Hi-Hat, Snare)"]]},
    ] + _STROBE_OPTIONS,
    "lights": [
        {"key": "beams", "label": "Scheinwerfer", "type": "choice", "default": "5",
         "choices": [["3", "3"], ["5", "5"], ["7", "7"]]},
        {"key": "flash", "label": "Sanfter Blitz bei kräftigen Schlägen", "type": "bool", "default": True},
        {"key": "fx", "label": "Zusätzliche Effekte", "type": "choice", "default": "classic",
         "choices": [["classic", "Keine (klassisch)"], ["heads", "Moving Heads im Nebel"],
                     ["laser", "Laser, Nebel, Lauflicht"], ["show", "Show: Moving Heads, Laser, Nebel, Lauflicht, Blinder"]]},
    ] + _STROBE_OPTIONS,
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
        {"key": "gags", "label": "Gags beim Tanzen (jugendfrei: Schornstein, Plätzchen, Glatteis …)", "type": "bool",
         "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "redgreen",
         "choices": [["redgreen", "Rot und Grün im Takt"], ["layer", "Farbe der Ebene"]]},
        {"key": "party", "label": "Feierabend: Glühwein-Gags (derber Humor)", "type": "choice", "default": "off",
         "choices": [["off", "Aus"], ["on", "An"], ["evening", "Nur abends (20 bis 4 Uhr)"]]},
        {"key": "party_len", "label": "Dauer einer Feierabend-Runde", "type": "choice", "default": "600",
         "choices": [["300", "5 Minuten"], ["600", "10 Minuten"], ["900", "15 Minuten"], ["1200", "20 Minuten"]]},
        {"key": "party_meter", "label": "Feierabend: Glühwein-Barometer und Becherzähler", "type": "bool",
         "default": True},
    ],
    "party": [
        {"key": "auto", "label": "An Geburtstagen automatisch zeigen (Liste unten)", "type": "bool", "default": True},
        {"key": "birthdays", "label": "Geburtstage", "type": "birthdays", "default": []},
        {"key": "round", "label": "Dauer einer Party-Runde (danach verstecken sich alle wieder)", "type": "choice",
         "default": "300", "choices": [["180", "3 Minuten"], ["300", "5 Minuten"], ["600", "10 Minuten"]]},
        {"key": "dog", "label": "Hund (hat Hunger auf Torte)", "type": "bool", "default": True},
        {"key": "confetti", "label": "Konfetti", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "rainbow",
         "choices": [["rainbow", "Bunt im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "cellar": [
        {"key": "level", "label": "Gänsehaut-Stufe", "type": "choice", "default": "2",
         "choices": [["1", "Schaurig-nett"], ["2", "Gruselig"], ["3", "Gänsehaut (Schreckmoment, Herzschlag)"]]},
        {"key": "fri13", "label": "An jedem Freitag, den 13., automatisch zeigen", "type": "bool", "default": False},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "bulb",
         "choices": [["bulb", "Wie die Glühbirne"], ["red", "Rot im Herzschlag"], ["layer", "Farbe der Ebene"]]},
    ],
    "metal": [
        {"key": "pyro", "label": "Pyro beim Höhepunkt", "type": "choice", "default": "dragon",
         "choices": [["dragon", "Drache speit Feuer"], ["fire", "Flammensäulen aus den Feuerkörben"], ["off", "Aus"]]},
        {"key": "crowd", "label": "Publikum (headbangt mit Pommesgabel)", "type": "bool", "default": True},
        {"key": "gags", "label": "Gags (Visier, Mönch, Steckenpferd, Katapult …)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "fire",
         "choices": [["fire", "Feuer im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "easter": [
        {"key": "gags", "label": "Gags (Küken, Hühnerdisco, Jonglage, Schokohasen)", "type": "bool", "default": True},
        {"key": "spooky", "label": "Schokohasen mit Gänsehaut (drehen sich im Dunkeln um)", "type": "bool",
         "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "pastel",
         "choices": [["pastel", "Farbe des zuletzt bemalten Eis"], ["layer", "Farbe der Ebene"]]},
    ],
    "halloween": [
        {"key": "gags", "label": "Gags (Hexenküche, Süßes oder Saures, Kopf ab, Kürbis-Solo, Fenster)", "type": "bool",
         "default": True},
        {"key": "spooky", "label": "Gänsehaut: Hand an der beschlagenen Scheibe", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "glow",
         "choices": [["glow", "Kürbisleuchten (flackert)"], ["layer", "Farbe der Ebene"]]},
    ],
    "horror": [
        {"key": "place", "label": "Schauplatz", "type": "choice", "default": "switch",
         "choices": [["switch", "Abwechselnd (bei jedem Liedwechsel)"], ["house", "Das Haus am Ende der Straße"],
                     ["dolls", "Das Puppenzimmer"]]},
        {"key": "gags", "label": "Gags (Nachbar mit Hund, Pizzabote, Teeparty, Springteufel …)", "type": "bool",
         "default": True},
        {"key": "spooky", "label": "Gänsehaut-Gags (Augen in den Fenstern, Puppen drehen sich, Licht aus)",
         "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "scene",
         "choices": [["scene", "Licht des Schauplatzes"], ["layer", "Farbe der Ebene"]]},
    ],
    "birthday": [
        {"key": "auto", "label": "An Geburtstagen aus der Liste statt der Überraschungsparty zeigen", "type": "bool",
         "default": False, "help": "Die Geburtstagsliste steht beim Stil „Überraschungsparty“. Ist dieser Schalter an, "
                                   "erscheint an Geburtstagen die lebende Torte statt der Party – mit Namen und "
                                   "Kerzen für das Alter."},
        {"key": "gags", "label": "Gags (Zeitraffer, Auspusten, Anschneiden, Geschenk, Ballon)", "type": "bool",
         "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "candle",
         "choices": [["candle", "Kerzenschein (flackert)"], ["layer", "Farbe der Ebene"]]},
    ],
    "mother": [
        {"key": "arms", "label": "Multitasking: mehr Arme bei lauter Musik", "type": "bool", "default": True},
        {"key": "gags", "label": "Gags (Frühstück, Blumenbeet, Bild, Waschmaschine)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "rose",
         "choices": [["rose", "Rosa im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "father": [
        {"key": "gags", "label": "Gags (Baumarkt-Ballett, Bollerwagen, Regenwolke, Zollstock)", "type": "bool",
         "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "ember",
         "choices": [["ember", "Grillglut im Bass"], ["layer", "Farbe der Ebene"]]},
    ],
    "newyear": [
        {"key": "countdown", "label": "Anzeigetafel (am 31.12. Countdown bis Mitternacht)", "type": "bool", "default": True},
        {"key": "gags", "label": "Gags (Wachsgießen, Vorsätze, Wunderkerze, Rakete)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "burst", "choices": [["burst", "Farbe der letzten Rakete"], ["layer", "Farbe der Ebene"]]},
    ],
    "carnival": [
        {"key": "call", "label": "Narrenruf", "type": "choice", "default": "helau", "choices": [["helau", "Helau!"], ["alaaf", "Alaaf!"]]},
        {"key": "gags", "label": "Gags (Pferdekostüm, Orden, Regenschirm)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "bunt", "choices": [["bunt", "Bunt im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "oktoberfest": [
        {"key": "gags", "label": "Gags (Maßkrugstemmen, Bedienung, Schuhplattler, Hendl)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "rauten", "choices": [["rauten", "Weiß-blau im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "martin": [
        {"key": "gags", "label": "Gags (Gans, brennende Laterne, Weckmann)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "lantern", "choices": [["lantern", "Laternenschein"], ["layer", "Farbe der Ebene"]]},
    ],
    "valentine": [
        {"key": "cupid", "label": "Amor schießt auf den Bass (meist daneben)", "type": "bool", "default": True},
        {"key": "gags", "label": "Gags (Nudel, Ring in der Suppe, Rosenverkäufer)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "heart", "choices": [["heart", "Rot-Rosa im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "underwater": [
        {"key": "gags", "label": "Gags (Flaschenpost, Kugelfisch, Hai)", "type": "bool", "default": True},
        {"key": "spooky", "label": "Gänsehaut: Ein Hai kreist", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "sea", "choices": [["sea", "Meeresblau im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "farm": [
        {"key": "gags", "label": "Gags (Fuchs, Schlammpfütze, Schaf)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "farm", "choices": [["farm", "Rosa und Grün im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "space": [
        {"key": "gags", "label": "Gags (Alien, Kakao, Satellit)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "space", "choices": [["space", "Wandernde Discofarben"], ["layer", "Farbe der Ebene"]]},
    ],
    "arcade": [
        {"key": "scanlines", "label": "Röhren-Zeilen (Scanlines)", "type": "bool", "default": True},
        {"key": "gags", "label": "Gags (Mutterschiff, Glitch, Highscore)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "hit", "choices": [["hit", "Farbe des letzten Treffers"], ["layer", "Farbe der Ebene"]]},
    ],
    "western": [
        {"key": "gags", "label": "Gags (Duell, Glas, Pferd, Steppenläufer)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "lamp", "choices": [["lamp", "Petroleumlampe"], ["layer", "Farbe der Ebene"]]},
    ],
    "campfire": [
        {"key": "people", "label": "Zwei Leute am Feuer (Marshmallows)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "fire", "choices": [["fire", "Feuerschein"], ["layer", "Farbe der Ebene"]]},
    ],
    "cats": [
        {"key": "gags", "label": "Gags (Schuh, Hund, Mond, Gräte)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "eyes", "choices": [["eyes", "Katzenaugen-Gelb"], ["layer", "Farbe der Ebene"]]},
    ],
    "silk": [
        {"key": "colors", "label": "Farben", "type": "choice", "default": "ruby",
         "choices": [["ruby", "Rubin, Bordeaux und Gold"], ["night", "Nachtblau und Flieder"], ["layer", "Farbe der Ebene"]]},
        {"key": "veil", "label": "Bänder durchscheinend (Schleier)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "glow",
         "choices": [["glow", "Farbe der Seide, atmet mit dem Bass"], ["layer", "Farbe der Ebene"]]},
    ],
    "ember": [
        {"key": "colors", "label": "Farben", "type": "choice", "default": "warm",
         "choices": [["warm", "Warme Glut"], ["layer", "Farbe der Ebene"]]},
        {"key": "sparks", "label": "Funken", "type": "choice", "default": "normal",
         "choices": [["few", "Wenige"], ["normal", "Normal"], ["many", "Viele"]]},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "glow",
         "choices": [["glow", "Glut, atmet mit dem Bass"], ["layer", "Farbe der Ebene"]]},
    ],
    "pulse": [
        {"key": "colors", "label": "Farben", "type": "choice", "default": "warm",
         "choices": [["warm", "Warmes Rosé"], ["layer", "Farbe der Ebene"]]},
        {"key": "beat", "label": "Heller Ring bei jedem Schlag", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "glow",
         "choices": [["glow", "Farbe der Aura, pulsiert im Takt"], ["layer", "Farbe der Ebene"]]},
    ],
    "jazz": [
        {"key": "mood", "label": "Club-Licht", "type": "choice", "default": "red",
         "choices": [["red", "Samtrot (klassisch)"], ["amber", "Bernstein / Whisky"], ["blue", "Midnight Blue"],
                     ["emerald", "Smaragd-Lounge"]]},
        {"key": "soloist", "label": "Bühne", "type": "choice", "default": "sax",
         "choices": [["sax", "Saxophonist und Kontrabass"], ["singer", "Sängerin am Mikrofon und Kontrabass"],
                     ["bass", "Nur der Kontrabass im Spotlight"]]},
        {"key": "smoke", "label": "Rauchschwaden", "type": "choice", "default": "normal",
         "choices": [["off", "Aus"], ["light", "Dezent"], ["normal", "Dicht (Club-Atmosphäre)"]]},
        {"key": "gags", "label": "Gags (Eiswürfel, Trinkgeld, Rauchringe)", "type": "bool", "default": True},
        {"key": "keys", "label": "Tastaturbeleuchtung", "type": "choice", "default": "mood",
         "choices": [["mood", "Warmes Club-Licht pulsiert zum Bass"], ["brass", "Gold- und Bläser-Akzente zu Mitten und Höhen"],
                     ["layer", "Farbe der Ebene"]]},
    ],
}
_AUTO_CHOICES = [["mix", "Abwechselnd (passende Auswahl)"]] + [[k, v] for k, v in VISUAL_STYLES.items() if k != "auto"]
VISUAL_OPTIONS["auto"] = [
    {"key": "calm", "label": "Bei ruhiger Musik", "type": "choice", "default": "mix", "choices": _AUTO_CHOICES,
     "help": "Langsam oder leise (unter 95 Schlägen/min): ab Werk Lagerfeuer, Lichtshow, Kreis-Spektrum, St. Martin, "
             "Weltraum, Unterwasser, Seidenschleier, Abendglut oder Herzschlag-Aura."},
    {"key": "mid", "label": "Bei mittlerer Musik", "type": "choice", "default": "mix", "choices": _AUTO_CHOICES,
     "help": "Ab Werk Tänzerin, Bauernhof, Katzenchor, Western, Equalizer, Oktoberfest oder Jazz-Club."},
    {"key": "wild", "label": "Bei wilder Musik", "type": "choice", "default": "mix", "choices": _AUTO_CHOICES,
     "help": "Schnell und laut (ab 125 Schlägen/min): ab Werk Mittelalter-Metal, Arcade, Fasching, Feuerwerk oder "
             "Halloween."},
    {"key": "label", "label": "Gewählten Stil kurz einblenden", "type": "bool", "default": True},
]


# Wann eine Option wirkt (B8: sonst ausgeblendet – in der Verwaltung und im Display-Menü), Gruppen (B9) und
# Hilfetexte. when: {"key": Option, "in": [Werte]} oder {"key": Option, "not": [Werte]}.
_OPTION_WHEN = {
    ("underwater", "spooky"): {"key": "gags", "in": [True]},
    ("dancer", "beams"): {"key": "show", "in": ["beams", "club", "custom"]},
    ("xmas", "every"): {"key": "dance", "in": ["auto"]},
    ("xmas", "party_len"): {"key": "party", "not": ["off"]},
    ("xmas", "party_meter"): {"key": "party", "not": ["off"]},
    ("easter", "spooky"): {"key": "gags", "in": [True]},
    ("halloween", "spooky"): {"key": "gags", "in": [True]},
    ("horror", "spooky"): {"key": "gags", "in": [True]},
}
for _k in ("follow", "heads", "laser", "haze", "chase", "silhouette", "uv", "mood", "ball", "blinder", "beams"):
    _OPTION_WHEN[("dancer", "fx_" + _k)] = {"key": "show", "in": ["custom"]}
for _st in ("dancer", "lights"):
    for _k in ("strobe_rate", "strobe_color", "strobe_keys"):
        _OPTION_WHEN[(_st, _k)] = {"key": "strobe", "not": ["off"]}
_OPTION_GROUP = {"keys": "Tastatur", "strobe": "Stroboskop", "strobe_rate": "Stroboskop", "strobe_color": "Stroboskop",
                 "strobe_keys": "Stroboskop", "stage": "Licht", "show": "Licht", "beams": "Licht", "flash": "Licht",
                 "fx": "Licht", "lights": "Licht", "pyro": "Licht", "dance": "Ablauf", "every": "Ablauf",
                 "gags": "Ablauf", "party": "Feierabend", "party_len": "Feierabend", "party_meter": "Feierabend",
                 "round": "Ablauf", "auto": "Festkalender", "birthdays": "Festkalender", "fri13": "Festkalender",
                 "level": "Ablauf", "dog": "Ablauf", "spooky": "Ablauf", "confetti": "Aussehen", "crowd": "Aussehen"}
_OPTION_HELP = {
    "strobe": "Harte Blitze, höchstens 3 je Sekunde. Vorsicht bei Lichtempfindlichkeit (Epilepsie).",
    "show": "Lichtprogramm der Bühne. „Eigene Auswahl“ blendet die einzelnen Effekte zum An- und Abschalten ein.",
    "party": "Derber Humor rund um Glühwein – ab Werk aus. „Nur abends“: 20 bis 4 Uhr.",
    "gags": "Kleine Szenen zwischendurch, etwa alle 15–25 Sekunden Musik.",
    "level": "Stufe 3 bringt rote Augen, Herzschlag am Bildrand und einen kurzen Schreckmoment im Dunkeln.",
    "pyro": "Beim Höhepunkt der Musik (wenn es deutlich lauter wird).",
    "every": "Wie lange ein Tanz läuft, bevor die Figuren wechseln.",
    "fri13": "An jedem Freitag, dem 13., zeigt die Visualisierung automatisch die Kellertreppe.",
    "auto": "Hat jemand aus der Liste heute Geburtstag, erscheint die Party automatisch.",
}
for _st, _opts in VISUAL_OPTIONS.items():
    for _o in _opts:
        if (_st, _o["key"]) in _OPTION_WHEN:
            _o["when"] = _OPTION_WHEN[(_st, _o["key"])]
        _o.setdefault("group", "Licht" if _o["key"].startswith("fx_") else _OPTION_GROUP.get(_o["key"], "Aussehen"))
        if _o["key"] in _OPTION_HELP:
            _o.setdefault("help", _OPTION_HELP[_o["key"]])


def option_visible(o, values):
    """Wirkt die Option bei diesen Werten (sonst ausblenden)?"""
    w = o.get("when")
    if not w:
        return True
    v = (values or {}).get(w["key"])
    return v in w["in"] if "in" in w else v not in w.get("not", [])
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
