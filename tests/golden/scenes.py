"""Referenzbilder aller Displayseiten, Menüs und Einblendungen.

Aufruf (mit eingefrorener Zeit, siehe tests/run_tests.sh):
    python3 scenes.py TREIBER.py AUSGABEORDNER

Das Skript lädt die angegebene g19s.py, füttert den Renderer mit festen
Testdaten und speichert jede Szene als PNG. Vorher/Nachher-Vergleich zeigt,
ob sich durch ein Refactoring die Anzeige verändert hat.
"""
import importlib.util
import json
import os
import sys

from PIL import Image

DRIVER, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
spec = importlib.util.spec_from_file_location("g19s", DRIVER)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "..", "fixtures")


class Snap:
    """Ersatz für einen Poller: snapshot() liefert feste Daten."""
    def __init__(self, data, err=None):
        self.v = (data, err, 1.0)

    def snapshot(self):
        return self.v

    def touch(self):
        pass

    def refresh(self):
        pass

    def fav_ids(self):
        return {"42"}


class Stats:
    def cpu_percent(self): return 37.5
    def memory(self): return 5.2, 15.5, 33.5
    def load(self): return 0.52, 0.61, 0.70


class Hw:
    def sensors(self):
        return {"cpu": 64.0, "gpu": 47.0, "gpu_load": 23, "nvme": 85.0, "fans": [("cpu", 1650), ("sys", 980)]}
    def network(self): return (12800.0, 33700.0)
    def disks(self): return [("System", 88.0, 271e9), ("Home", 41.0, 1000e9)]


def tz(h, m=0, day=0):
    return (dt.datetime(2026, 10, 1, h, m) + dt.timedelta(days=day)).astimezone()


ICS = open(os.path.join(FIX, "kalender.ics"), encoding="utf-8").read()
events = g.expand_events(g.parse_ics(ICS), 14)
cal_list = [{"key": "k1", "name": "Persönlich", "color": [0, 130, 201]},
            {"key": "k2", "name": "Geburtstage", "color": [233, 50, 45]},
            {"key": "k3", "name": "Marco", "color": [244, 163, 49]}]
for i, ev in enumerate(events):
    ev["cal"] = cal_list[i % 3]["key"]
    ev["color"] = cal_list[i % 3]["color"]
    ev["source"] = 0
calendar_data = {"items": events, "errors": [], "calendars": [], "calendar_list": cal_list}
weather_data = json.load(open(os.path.join(FIX, "wetter.json")))
news_data = {"items": g.parse_feed(open(os.path.join(FIX, "feed.xml"), "rb").read(), "tagesschau"), "errors": []}
alerts_data = {"place": "Leipzig", "alerts": [
    {"id": "a1", "severity": "moderate", "event": "STURMBÖEN", "headline": "Amtliche WARNUNG vor STURMBÖEN",
     "description": "Es treten Sturmböen mit Geschwindigkeiten um 70 km/h auf.", "instruction": "Äste können herabstürzen.",
     "onset": tz(8), "expires": tz(15)},
    {"id": "a2", "severity": "minor", "event": "FROST", "headline": "Amtliche WARNUNG vor FROST", "description": "Leichter Frost.",
     "instruction": "", "onset": tz(22), "expires": tz(8, 0, 1)}]}
net_data = {"hosts": [{"name": "Router", "host": "192.168.178.1", "ok": True, "ms": 1.8},
                      {"name": "NAS", "host": "10.0.0.99", "ok": False, "ms": None},
                      {"name": "Piwigo", "host": "fotos.local:80", "ok": True, "ms": 12.4}], "ip": "192.168.178.23"}
updates_data = {"apt": 4, "security": 2, "packages": ["firefox"], "flatpak": 2, "reboot": True, "checked": "09:12", "apt_ok": True}
photo = Image.new("RGB", (320, 214), (30, 90, 200))
music_info = dict.fromkeys(g.MediaWatcher.FIELDS, "")
music_info.update(title="Thunderstruck", artist="AC/DC", album="The Razors Edge", player="elisa", status="Paused",
                  position=95_000_000, length=292_000_000, fetched=0.0)
radio_info = dict(music_info, title="Schrei nach Liebe", artist="Die Ärzte", player="g19s-radio", station="Radio BOB!",
                  status="Paused", length=0, position=0)
cover = Image.new("RGB", (132, 132), (200, 60, 40))
macros = {"M1": {"G1": {"name": "Test-Satz", "steps": [[0, "KEY_A", "tap"]]}, "G2": {"open": "https://www.heise.de"},
                 "G5": {"snippets": "Büro"}, "G6": {"timer": {"mode": "pomodoro", "work": 25, "break": 5}},
                 "G7": {"volume": "up"}, "G8": {"media": "remember"}, "G9": {"sleep": 30}, "G10": {"mic": "toggle"}}}
settings = g.load_settings("/nonexistent")
settings.update({"weather": {"name": "Leipzig", "lat": 51.34, "lon": 12.37},
                 "calendar": {"sources": [{"name": "NC", "url": "x"}], "days": 14, "remind": 10},
                 "slideshow": dict(settings["slideshow"], url="http://x", albums=[1], caption=True)})


def fresh():
    r = g.Renderer()
    r.settings = settings
    r.stats, r.hw = Stats(), Hw()
    r.weather, r.calendar = Snap(weather_data), Snap(calendar_data)
    r.news, r.alerts, r.net, r.updates = Snap(news_data), Snap(alerts_data), Snap(net_data), Snap(updates_data)
    r.media = Snap(None)
    r.media.v = (music_info, cover, None, None)
    sl = Snap(None)
    sl.snapshot = lambda: {"image": photo, "name": "Toskana 2024", "id": 42, "index": 3, "count": 17, "status": "",
                           "error": None, "paused": True, "configured": True}
    r.slideshow = sl
    r.visible = list(range(len(g.PAGE_IDS)))
    return r


def _face(r, face):
    r.clock_face = face                        # Zifferblatt der Seite „Uhr“
    return r.render(0, "M2", macros)


scenes = {}
for i, pid in enumerate(g.PAGE_IDS):
    scenes[f"seite_{pid}"] = lambda r, i=i: r.render(i, "M1", macros)
for face in g.CLOCK_FACES:
    if face != "digital":
        scenes[f"uhr_{face}"] = lambda r, face=face: _face(r, face)


def _face_opt(r, face, opts):
    r.settings = json.loads(json.dumps(settings))
    r.settings.setdefault("clock", json.loads(json.dumps(g.DEFAULT_SETTINGS["clock"])))
    r.settings["clock"][face] = dict(g.DEFAULT_SETTINGS["clock"][face], **opts)
    return _face(r, face)


for name, face, opts in (("digital_ohne_sekunden", "digital", {"seconds": False, "color": [255, 200, 0]}),
                         ("binaer_zeilen", "binary", {"mode": "binary", "color_h": [255, 60, 60], "digits": False}),
                         ("chrono_silber", "chrono", {"dial": "silver", "side": "none", "hand": [0, 200, 120]}),
                         ("bahnhof_ohne_sekunde", "station", {"seconds": False, "smooth": True, "side": False}),
                         ("terminal_bernstein", "terminal", {"color": "amber"}),
                         ("weltzeit_drei", "world", {"cities": [{"name": "Kairo", "tz": "Africa/Cairo"},
                                                                {"name": "Delhi", "tz": "Asia/Kolkata"},
                                                                {"name": "Falsch", "tz": "Mars/Olympus"}]})):
    scenes[f"uhr_opt_{name}"] = lambda r, face=face, opts=opts: _face_opt(r, face, opts)


def s(name):
    def deco(fn):
        scenes[name] = fn
        return fn
    return deco


@s("seite_music_radio")
def _(r):
    r.media.v = (radio_info, None, None, None)
    return r.render(g.PAGE_IDS.index("music"), "M2", macros)

@s("seite_music_leer")
def _(r):
    r.media.v = (None, None, None, None)
    return r.render(g.PAGE_IDS.index("music"), "M1", macros)

@s("fusszeile_profil_timer_mikro")
def _(r):
    r.profile_name, r.timer_badge, r.mic_muted, r.sleep_badge = "Büro", "+04:12", True, "29"
    r.visible = [0, 1, 6]
    return r.render(0, "M3", macros)

@s("seite_calendar_ausgeblendet_markiert")
def _(r):
    r.cal_hidden = {"k2"}
    r.cal_sel = 2
    return r.render(g.PAGE_IDS.index("calendar"), "M1", macros)

@s("seite_news_markiert")
def _(r):
    r.sel["news"] = 1
    return r.render(g.PAGE_IDS.index("news"), "M1", macros)

@s("seite_warnings_leer")
def _(r):
    r.alerts = Snap({"place": "Leipzig", "alerts": []})
    return r.render(g.PAGE_IDS.index("warnings"), "M1", macros)

@s("seite_weather_fehler")
def _(r):
    r.weather = Snap(None, "Wetterdienst nicht erreichbar")
    return r.render(g.PAGE_IDS.index("weather"), "M1", macros)

@s("seite_slides_nicht_eingerichtet")
def _(r):
    r.slideshow.snapshot = lambda: {"image": None, "configured": False, "status": "", "error": None}
    return r.render(g.PAGE_IDS.index("slides"), "M1", macros)

@s("meldung")
def _(r): return r.render_message("Radio", ["Radio BOB!", "zweite Zeile"], (0, 110, 255))

@s("lautstaerke")
def _(r): return r.render_volume(45, False, (0, 110, 255))

@s("lautstaerke_stumm")
def _(r): return r.render_volume(100, True, (0, 255, 90))

@s("benachrichtigung")
def _(r): return r.render_notification("Thunderbird", "Neue E-Mail von Anna", "Hallo Max, anbei die Unterlagen für morgen.", (0, 110, 255))

@s("profilmenue")
def _(r): return r.render_profile_menu(["Büro", "Spiele", "Grafik"], 1, 0, lambda i: g.DEFAULT_SETTINGS["colors"])

@s("kalendermenue")
def _(r): return r.render_calendar_menu(cal_list * 3, {"k2"}, 4)

@s("albenmenue")
def _(r):
    albums = [{"id": i + 1, "name": f"Album {i}", "level": i % 3, "parent": (i if i % 3 else None), "total": i * 7} for i in range(12)]
    return r.render_album_menu(albums, {1, 5}, 6, True, (0, 110, 255))

@s("albenmenue_laden")
def _(r): return r.render_album_menu([], set(), 0, True, (0, 110, 255), "Alben werden geladen …")

@s("listenmenue_sender")
def _(r):
    items = [{"label": "Rockantenne", "station": {}, "mark": "▶"}, {"label": "Radio BOB!", "station": {}},
             {"label": "Radio ausschalten", "stop": True, "mark": "■", "color": (235, 90, 90)}]
    return r.render_list_menu("Radiosender", items, 1, "▲▼ wählen · OK abspielen · BACK zurück", "2 Sender", (0, 110, 255))

@s("listenmenue_bausteine")
def _(r):
    items = [{"label": f"Baustein {i}", "sub": "Büro" if i % 2 else ""} for i in range(10)]
    return r.render_list_menu("Textbausteine", items, 8, "▲▼ wählen · OK einfügen · BACK zurück", "10", (0, 110, 255))

def _timer(mode, **kw):
    t = g.Timer()
    t.start(dict({"mode": mode}, **kw))
    t.running, t.since, t.acc = False, None, 83.0
    return t

@s("timer_countdown")
def _(r): return r.render_timer(_timer("timer", minutes=5), (0, 110, 255), 0.0)

@s("timer_stoppuhr")
def _(r): return r.render_timer(_timer("stopwatch"), (0, 110, 255), 0.0)

@s("timer_pomodoro_pause")
def _(r):
    t = _timer("pomodoro", work=25, **{"break": 5})
    t.phase, t.rounds, t.total = "break", 3, 300.0
    return r.render_timer(t, (0, 110, 255), 0.0)

@s("timer_alarm")
def _(r):
    t = _timer("timer", minutes=5)
    t.alarm = True
    img = r.render_timer(t, (0, 110, 255), 0.0)
    return img

@s("termindetails")
def _(r):
    ev = [e for e in events if e.get("description")][0]
    return r.render_event(ev, "Persönlich", [0, 130, 201], 0)[0]

@s("termindetails_geblaettert")
def _(r):
    ev = [e for e in events if e.get("description")][0]
    return r.render_event(ev, "Persönlich", [0, 130, 201], 3)[0]

@s("terminerinnerung")
def _(r):
    ev = {"title": "Zahnarzt Dr. Müller – Kontrolltermin", "start": tz(9, 40), "location": "Hauptstr. 5, Leipzig"}
    return r.render_reminder(ev, 10, [233, 50, 45], "Persönlich")

@s("mikrofon_stumm")
def _(r): return r.render_mic(True, (0, 110, 255))

@s("mikrofon_an")
def _(r): return r.render_mic(False, (0, 110, 255))


names = sys.argv[3:] or list(scenes)
for name in names:
    img = scenes[name](fresh())
    if name == "timer_alarm":
        pass
    img.save(os.path.join(OUT, name + ".png"))
print(f"{len(names)} Szenen gespeichert in {OUT}")
