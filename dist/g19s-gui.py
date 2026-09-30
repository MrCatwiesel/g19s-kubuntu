#!/usr/bin/env python3
"""
g19s-gui.py – Grafische Verwaltung für den Logitech-G19s-Treiber (g19s.py)

Startet einen kleinen Webserver nur auf diesem Rechner (127.0.0.1) und öffnet
die Oberfläche als App-Fenster im Browser. Damit lassen sich verwalten:
  * Belegung der G-Tasten je Profil (Text, Tastenkombination, Makro, Webseite,
    Programm, Radiosender, Musiksteuerung, KDE-Kurzbefehl)
  * Radiosender (inkl. Suche im Radio-Browser-Verzeichnis und Probehören)
  * Beleuchtungsfarben, Displayhelligkeit, Startseite (mit Display-Vorschau)
  * Treiber-Dienst (Start/Stopp/Autostart, Log) und Sicherung/Wiederherstellung

Aufruf:
  g19s-gui.py                    Oberfläche öffnen
  g19s-gui.py --install-desktop  Eintrag „G19s-Verwaltung“ im Anwendungsmenü anlegen
  g19s-gui.py --no-browser       nur Server starten und Adresse ausgeben

Benötigt: g19s.py im selben Ordner (dieselben Pakete wie der Treiber)
"""

import argparse
import base64
import datetime
import http.server
import importlib.util
import io
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
import urllib.parse
import urllib.request

G19S_COMPONENT = "gui"        # Kennung für den Update-Knopf
VERSION = "2026.09.30-1"

HERE = os.path.dirname(os.path.realpath(__file__))
SERVICE = "g19s.service"
HOME = os.path.expanduser("~")
# Laufzeitordner des Benutzers; ohne XDG_RUNTIME_DIR nicht /tmp (dort könnte ein anderer Benutzer
# die Instanzdatei vorher anlegen), sondern der eigene Cache-Ordner
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or os.path.join(
    os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache")), "g19s")
INSTANCE_FILE = os.path.join(RUNTIME_DIR, "g19s-gui.json")
IDLE_TIMEOUT = 45          # Sekunden ohne Lebenszeichen der Seite -> Server beenden
FIRST_CONTACT_TIMEOUT = 180


def load_driver():
    path = os.path.join(HERE, "g19s.py")
    if not os.path.exists(path):
        sys.exit(f"g19s.py nicht gefunden (erwartet in {HERE})")
    spec = importlib.util.spec_from_file_location("g19s", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [name for name in DRIVER_API if not hasattr(mod, name)]
    if missing:
        sys.exit("Die installierte g19s.py ist zu alt für die Oberfläche – bitte aktualisieren "
                 f"(es fehlt: {', '.join(missing[:5])}).")
    return mod


# Alle Namen des Treibers, die die Verwaltung benutzt (g.<name>) – build.py trägt sie beim Bauen ein
DRIVER_API = "BACKUP_FILES CLOCK_FACES CLOCK_OPTIONS CalendarPoller DEFAULT_SETTINGS DESKTOP_RE DE_CHARS DE_DEAD FAVORITES_FILE Hardware LAYERS MACRO_FILE MAX_PROFILES MEDIA_ACTIONS NetworkPoller NewsPoller PAGE_IDS PAGE_NAMES PROFILE_COLOR PiwigoClient PiwigoError RadioManager Renderer SCHEMA SETTINGS_FILE SEVERITY SONGS_FILE Slideshow USER_AGENT UpdatesPoller VOLUME_ACTIONS WEATHER_CODES WORLD_CITIES WarningsPoller WeatherPoller auto_backup backup_members clean_macros clean_settings err_text find_mpris_plugin fit_photo geocode http_get key_label load_list load_settings load_state make_backup migrate_files normalize_macros open_remote_image parse_feed save_json save_state test_backup_target valid_colors".split()


g = load_driver()


# ═══════════════════════════════════════════════════════════════════════════
# Modul belegung
#   Tastenbelegung und Einstellungen lesen/prüfen (die Regeln stehen im Treiber), Tastenkatalog für den Editor.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Tastenkatalog für die Auswahllisten
# --------------------------------------------------------------------------- #
def key_catalog():
    groups = [
        ("Buchstaben", sorted((f"KEY_{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                              key=g.key_label)),
        ("Ziffern", [f"KEY_{n}" for n in "1234567890"]),
        ("Sonderzeichen", ["KEY_MINUS", "KEY_EQUAL", "KEY_LEFTBRACE", "KEY_RIGHTBRACE",
                           "KEY_SEMICOLON", "KEY_APOSTROPHE", "KEY_BACKSLASH", "KEY_GRAVE",
                           "KEY_102ND", "KEY_COMMA", "KEY_DOT", "KEY_SLASH", "KEY_SPACE"]),
        ("Steuertasten", ["KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT",
                          "KEY_LEFTALT", "KEY_RIGHTALT", "KEY_LEFTMETA", "KEY_RIGHTMETA",
                          "KEY_COMPOSE", "KEY_ENTER", "KEY_TAB", "KEY_BACKSPACE", "KEY_ESC",
                          "KEY_CAPSLOCK"]),
        ("Navigation", ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_HOME", "KEY_END",
                        "KEY_PAGEUP", "KEY_PAGEDOWN", "KEY_INSERT", "KEY_DELETE"]),
        ("Funktionstasten", [f"KEY_F{n}" for n in range(1, 25)]),
        ("Ziffernblock", [f"KEY_KP{n}" for n in range(10)]
         + ["KEY_KPPLUS", "KEY_KPMINUS", "KEY_KPASTERISK", "KEY_KPSLASH", "KEY_KPDOT",
            "KEY_KPENTER", "KEY_NUMLOCK"]),
        ("Medien", ["KEY_MUTE", "KEY_VOLUMEDOWN", "KEY_VOLUMEUP", "KEY_PLAYPAUSE",
                    "KEY_PREVIOUSSONG", "KEY_NEXTSONG", "KEY_STOPCD"]),
        ("Sonstige", ["KEY_SYSRQ", "KEY_SCROLLLOCK", "KEY_PAUSE"]),
    ]
    return [{"name": n, "label": g.key_label(n), "group": grp} for grp, names in groups for n in names]


# --------------------------------------------------------------------------- #
# Dateien
# --------------------------------------------------------------------------- #
def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def read_macros():
    """Liefert die Makros immer im Profilformat (altes Format wird umgewandelt)."""
    try:
        with open(g.MACRO_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return g.normalize_macros(data), None
    except FileNotFoundError:
        return g.normalize_macros({}), None
    except (ValueError, OSError) as ex:
        return g.normalize_macros({}), f"macros.json ist fehlerhaft: {ex}"


def clean_macros(data):
    """Tastenbelegung prüfen – die Regeln stehen im Treiber (Modul makros)."""
    return g.clean_macros(data)


def active_profile(count):
    try:
        i = int(g.load_state().get("profile", 0))
    except (TypeError, ValueError):
        i = 0
    return i if 0 <= i < count else 0


def clean_settings(data):
    """Einstellungen prüfen – das Schema steht im Treiber (Modul einstellungen)."""
    return g.clean_settings(data)


# ═══════════════════════════════════════════════════════════════════════════
# Modul dienst
#   Den systemd-Benutzerdienst des Treibers steuern und sein Protokoll lesen.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Dienst
# --------------------------------------------------------------------------- #
def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]} nicht gefunden"
    except subprocess.TimeoutExpired:
        return 124, "Zeitüberschreitung"


_service_cache = [0.0, None]


def service_status(max_age=0.0):
    """Zustand des Dienstes; max_age > 0: so lange zwischengespeichert (für die regelmäßige Abfrage)."""
    now = time.monotonic()
    if _service_cache[1] is not None and now - _service_cache[0] < max_age:
        return _service_cache[1]
    _, active = run(["systemctl", "--user", "is-active", SERVICE])
    _, enabled = run(["systemctl", "--user", "is-enabled", SERVICE])
    st = {"active": active.splitlines()[0] if active else "unbekannt",
          "enabled": enabled.splitlines()[0] if enabled else "unbekannt"}
    _service_cache[:] = [now, st]
    return st


def service_log(lines=80):
    _, out = run(["journalctl", "--user", "-u", SERVICE, "-n", str(lines), "--no-pager",
                  "-o", "short"])
    return out


def service_action(action):
    cmds = {
        "start": ["systemctl", "--user", "start", SERVICE],
        "stop": ["systemctl", "--user", "stop", SERVICE],
        "restart": ["systemctl", "--user", "restart", SERVICE],
        "enable": ["systemctl", "--user", "enable", SERVICE],
        "disable": ["systemctl", "--user", "disable", SERVICE],
    }
    if action not in cmds:
        raise ValueError("Unbekannte Aktion")
    code, out = run(cmds[action], timeout=20)
    if code != 0:
        raise RuntimeError(out or f"systemctl meldet Fehler {code}")


# ═══════════════════════════════════════════════════════════════════════════
# Modul sicherung
#   Sicherung herunterladen/einspielen (die Dateiliste kommt aus dem Treiber).
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Sicherung
# --------------------------------------------------------------------------- #
BACKUP_FILES = g.BACKUP_FILES
DESKTOP_RE = g.DESKTOP_RE


def backup_members():
    return g.backup_members(HOME)


def make_backup():
    return g.make_backup(HOME)


# Dateien, die Programmcode oder Befehle enthalten: nur nach ausdrücklicher Zustimmung einspielen
# (ein ausgetauschtes Archiv auf einem NAS dürfte sonst beliebige Programme unterschieben)
PROGRAM_FILES = {".local/bin/g19s.py", ".local/bin/g19s-gui.py", ".config/systemd/user/g19s.service",
                 ".config/kglobalshortcutsrc"}
MAX_MEMBER = 5 * 1024 * 1024
PRIVATE_FILES = {".config/g19s/settings.json"}          # enthält Passwörter


def is_program_file(name):
    return name in PROGRAM_FILES or bool(DESKTOP_RE.fullmatch(name))


def _write_private(path, data):
    """Datei nur für den Benutzer lesbar schreiben (0600)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(path, 0o600)


def restore_backup(raw, programs=False, inspect=False):
    """Sicherung einspielen. inspect=True: nur Inhalt melden ({"config": [...], "programs": [...]}).
    programs=False: Programmdateien, Dienst, KDE-Kurzbefehle und Starter werden übersprungen."""
    try:
        tar = tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")
    except tarfile.TarError as ex:
        raise ValueError(f"Keine gültige Sicherungsdatei: {ex}")
    allowed = []
    with tar:
        for m in tar.getmembers():
            name = m.name[2:] if m.name.startswith("./") else m.name
            if not m.isfile() or m.size > MAX_MEMBER:
                continue
            if name in BACKUP_FILES or DESKTOP_RE.fullmatch(name):
                allowed.append((name, m))
        if not allowed:
            raise ValueError("Die Datei enthält keine G19s-Dateien")
        if inspect:
            return {"config": [n for n, _ in allowed if not is_program_file(n)],
                    "programs": [n for n, _ in allowed if is_program_file(n)]}
        if not programs:
            allowed = [(n, m) for n, m in allowed if not is_program_file(n)]
            if not allowed:
                raise ValueError("Die Sicherung enthält nur Programmdateien – nichts eingespielt")
        # vorherigen Stand sichern (enthält Passwörter → 0600)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        safety = os.path.join(HOME, ".config/g19s", f"vor-wiederherstellung-{stamp}.tar.gz")
        os.makedirs(os.path.dirname(safety), mode=0o700, exist_ok=True)
        _write_private(safety, make_backup())
        restored = []
        for name, m in allowed:
            dest = os.path.join(HOME, name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            data = tar.extractfile(m).read(MAX_MEMBER + 1)
            if len(data) > MAX_MEMBER:
                continue
            tmp = dest + ".tmp"
            if name in PRIVATE_FILES:
                _write_private(tmp, data)
            else:
                with open(tmp, "wb") as f:
                    f.write(data)
            if name.endswith(".py"):
                os.chmod(tmp, 0o755)
            os.replace(tmp, dest)
            restored.append(name)
    return restored, safety


# ═══════════════════════════════════════════════════════════════════════════
# Modul update
#   Update-Knopf: neue Programmdateien erkennen, prüfen, installieren (mit Sicherung der alten Version).
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Update: neue Programmdateien einspielen
# --------------------------------------------------------------------------- #
UPDATE_BACKUP_DIR = os.path.join(HOME, ".local/share/g19s/alte-versionen")
END_MARKER = "# G19S-DATEIENDE (diese Zeile zeigt, dass die Datei vollständig ist)"


def component_of(text):
    m = re.search(r'^G19S_COMPONENT\s*=\s*"(driver|gui)"', text, re.M)
    if m:
        return m.group(1)
    if "PAGE_HTML" in text and "class Handler" in text:       # ältere Versionen ohne Kennung
        return "gui"
    if "class G19:" in text and "def run(args)" in text:
        return "driver"
    return None


def version_of(text):
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', text or "", re.M)
    return m.group(1) if m else "älter (ohne Versionsangabe)"


def file_version(path):
    try:
        with open(path, encoding="utf-8") as f:
            return version_of(f.read())
    except OSError:
        return "nicht installiert"


def install_update(files):
    """files: [(Dateiname, Bytes)]. Prüft alle Dateien, bevor etwas geschrieben wird."""
    checked = {}
    for name, raw in files:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as ex:
            if ex.start >= len(raw) - 3:          # mitten in einem Umlaut abgeschnitten
                raise ValueError(f"„{name}“ ist unvollständig (Download abgebrochen?) – bitte erneut herunterladen")
            raise ValueError(f"„{name}“ ist keine Textdatei")
        comp = component_of(text)
        if comp is None:
            raise ValueError(f"„{name}“ ist weder der G19s-Treiber noch die G19s-Verwaltung")
        if not text.rstrip().endswith(END_MARKER):
            raise ValueError(f"„{name}“ ist unvollständig (Download abgebrochen?) – bitte erneut herunterladen")
        if comp in checked:
            raise ValueError("Bitte je Programmteil nur eine Datei auswählen")
        try:
            compile(text, name, "exec")
        except SyntaxError as ex:
            raise ValueError(f"„{name}“ ist beschädigt (Zeile {ex.lineno}) – bitte erneut herunterladen")
        checked[comp] = (name, text)
    if "gui" in checked and "driver" not in checked:
        # neue Verwaltung braucht passende Treiberfunktionen
        needed = re.findall(r'for needed in \(([^)]*)\)', checked["gui"][1])
        names = re.findall(r'"(\w+)"', needed[0]) if needed else []
        missing = [n for n in names if not hasattr(g, n)]
        if missing:
            raise ValueError("Diese Verwaltung braucht einen neueren Treiber – bitte g19s.py mit auswählen")
    targets = {"driver": os.path.join(HERE, "g19s.py"), "gui": os.path.realpath(__file__)}
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(UPDATE_BACKUP_DIR, exist_ok=True)
    result = []
    for comp, (name, text) in checked.items():
        target = targets[comp]
        old = file_version(target)
        backup = None
        if os.path.exists(target):
            backup = os.path.join(UPDATE_BACKUP_DIR, f"{os.path.basename(target)}.{stamp}")
            shutil.copy2(target, backup)
        tmp = target + ".neu"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o755)
        os.replace(tmp, target)
        result.append({"component": comp, "file": name, "old": old, "new": version_of(text),
                       "backup": backup})
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Modul radio
#   Radiosender probehören und im Verzeichnis radio-browser.info suchen.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Radio: Probehören und Suche im Radio-Browser-Verzeichnis
# --------------------------------------------------------------------------- #
class Launcher:
    """Umgebung der Desktop-Sitzung (für mpv usw.)."""

    @staticmethod
    def env():
        return dict(os.environ)


test_radio = g.RadioManager(Launcher.env, log=lambda m: print(m, flush=True))

RADIO_BROWSER_HOSTS = ["de1.api.radio-browser.info", "at1.api.radio-browser.info",
                       "nl1.api.radio-browser.info", "all.api.radio-browser.info"]


def radio_search(query):
    params = urllib.parse.urlencode({"name": query, "limit": 40, "hidebroken": "true",
                                     "order": "clickcount", "reverse": "true"})
    last = None
    for host in RADIO_BROWSER_HOSTS:
        url = f"https://{host}/json/stations/search?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": g.USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as r:
                items = json.load(r)
            break
        except Exception as ex:         # nächsten Server des Radio-Verzeichnisses versuchen
            last = ex
    else:
        raise RuntimeError(f"Radio-Verzeichnis nicht erreichbar: {last}")
    out, seen = [], set()
    for it in items:
        url = (it.get("url_resolved") or it.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append({"name": (it.get("name") or "").strip(), "url": url,
                    "logo": (it.get("favicon") or "").strip(),
                    "country": it.get("countrycode") or it.get("country") or "",
                    "codec": it.get("codec") or "", "bitrate": it.get("bitrate") or 0,
                    "tags": (it.get("tags") or "")[:60]})
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Modul vorschau
#   Display-Vorschau in der Verwaltung und Test der Diashow (nutzt den Renderer des Treibers).
# ═══════════════════════════════════════════════════════════════════════════

class PreviewSlides:
    """Liefert der Displayvorschau ein festes Beispielbild."""

    def __init__(self, img, name, count):
        self.img, self.name, self.count = img, name, count

    def touch(self):
        pass

    def snapshot(self):
        return {"image": self.img, "name": self.name, "index": 1, "count": self.count,
                "status": "", "error": None, "paused": False, "configured": True}


def piwigo_test(cfg):
    import random
    cfg = g.SCHEMA["slideshow"].clean(cfg, strict=True)
    from PIL import Image
    if cfg["source"] == "folder":
        folder = os.path.expanduser(cfg["folder"])
        if not cfg["folder"] or not os.path.isdir(folder):
            raise ValueError("Bitte einen vorhandenen Bilderordner angeben")
        images = g.Slideshow.folder_images(folder, cfg["recursive"])
        if not images:
            return {"count": 0, "image": None}
        pick = random.choice(images) if cfg["shuffle"] else images[0]
        try:
            raw = Image.open(pick["url"])
            raw.load()
        except Exception as ex:         # beliebige Bilddatei: jeden Lesefehler melden
            raise RuntimeError(f"Bild „{os.path.basename(pick['url'])}“ nicht lesbar: {ex}")
    else:
        if not cfg["url"]:
            raise ValueError("Bitte die Adresse der Piwigo-Galerie eintragen")
        if not cfg["albums"]:
            raise ValueError("Bitte mindestens ein Album auswählen")
        client = g.PiwigoClient(cfg["url"], cfg["user"], cfg["password"])
        try:
            images = client.images(cfg["albums"], cfg["recursive"])
            if not images:
                return {"count": 0, "image": None}
            pick = random.choice(images) if cfg["shuffle"] else images[0]
            raw = g.open_remote_image(client.fetch(pick["url"]))
        except g.PiwigoError as ex:
            raise RuntimeError(str(ex))
    fitted = g.fit_photo(raw, g.Slideshow.AREA, cfg["fit"])
    with _preview_lock:
        r = g.Renderer()
        r.settings = dict(g.load_settings(), slideshow=cfg)
        r.slideshow = PreviewSlides(fitted, pick["name"], len(images))
        img = r.render(g.Renderer.SLIDES_PAGE, "M1", {})
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return {"count": len(images), "image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}


# --------------------------------------------------------------------------- #
# Display-Vorschau
# --------------------------------------------------------------------------- #
_preview_lock = threading.Lock()
_renderer = None


class PreviewData:
    """Wetter/Termine für die Vorschau: einmal abrufen und 5 Minuten merken."""

    def __init__(self, poller_cls):
        self.poller_cls, self.cache = poller_cls, {}

    def get(self, settings):
        poller = self.poller_cls(lambda: settings)
        key = poller.signature()
        hit = self.cache.get(key)
        if hit and time.time() - hit[2] < 300:
            return hit
        try:
            res = (poller.fetch(), None, time.time())
        except Exception as ex:         # Dienst im Netz: Fehler in der Vorschau anzeigen
            res = (None, g.err_text(ex), time.time())
        self.cache = {key: res}
        return res


class _Snap:
    def __init__(self, res):
        self.res = res

    def snapshot(self):
        return self.res


_preview_weather = PreviewData(g.WeatherPoller)
_preview_calendar = PreviewData(g.CalendarPoller)
_preview_extra = {"news": PreviewData(g.NewsPoller), "warnings": PreviewData(g.WarningsPoller),
                  "network": PreviewData(g.NetworkPoller), "updates": PreviewData(g.UpdatesPoller)}
_PREVIEW_ATTR = {"news": "news", "warnings": "alerts", "network": "net", "updates": "updates"}


def render_preview(page, layer, settings, pidx=0, colors=None, name=None, face=None):
    global _renderer
    with _preview_lock:
        if _renderer is None:
            _renderer = g.Renderer()
        s = clean_settings(settings) if settings else g.load_settings()
        lay = layer if layer in g.LAYERS else "M1"
        macros_pv, _ = read_macros()
        profs = macros_pv["profiles"]
        own = (profs[max(0, min(int(pidx or 0), len(profs) - 1))].get("pages") or {}).get(lay)
        lay_pages = own or s["layer_pages"].get(lay) or s["pages"]
        _renderer.visible = [g.PAGE_IDS.index(p) for p in lay_pages]
        page_id = g.PAGE_IDS[int(page) % len(g.PAGE_IDS)]
        preview_settings = dict(s, pages=list(g.PAGE_IDS))
        if page_id == "weather" and s["weather"].get("lat") is not None:
            _renderer.weather = _Snap(_preview_weather.get(preview_settings))
        if page_id == "calendar" and s["calendar"]["sources"]:
            _renderer.calendar = _Snap(_preview_calendar.get(preview_settings))
        if page_id in _preview_extra:
            setattr(_renderer, _PREVIEW_ATTR[page_id], _Snap(_preview_extra[page_id].get(preview_settings)))
        macros, _ = read_macros()
        profiles = macros["profiles"]
        pidx = max(0, min(int(pidx or 0), len(profiles) - 1))
        prof = profiles[pidx]
        cols = g.valid_colors(colors) or prof.get("colors") or g.valid_colors(s["colors"]) or g.DEFAULT_SETTINGS["colors"]
        for p, color in cols.items():
            g.PROFILE_COLOR[p] = tuple(color)
        _renderer.settings = s
        _renderer.clock_face = (face if face in g.CLOCK_FACES else      # Karte „Uhr“: gezeigtes Zifferblatt
                                (prof.get("clock") or {}).get(lay, "digital"))  # sonst: am Display gewähltes
        _renderer.profile_name = (name if name is not None else prof["name"]) if len(profiles) > 1 else ""
        img = _renderer.render(int(page) % len(g.PAGE_NAMES), layer if layer in g.LAYERS else "M1",
                               prof["keys"])
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# Modul api_tasten
#   HTTP-Routen: Tastenbelegung, Profile, Einstellungen, Vorschau.
# ═══════════════════════════════════════════════════════════════════════════

class ApiKeys:
    # -- API: Zustand ------------------------------------------------------ #
    def api_get_state(self, q):
        macros, err = read_macros()
        self._send(200, {
            "macros": macros, "macros_error": err,
            "active": active_profile(len(macros["profiles"])), "max_profiles": g.MAX_PROFILES,
            "settings": g.load_settings(),
            "defaults": g.DEFAULT_SETTINGS,
            "keys": key_catalog(),
            "chars": list(g.DE_CHARS.keys()), "dead": list(g.DE_DEAD.keys()),
            "pages": g.PAGE_NAMES, "page_ids": g.PAGE_IDS, "media": g.MEDIA_ACTIONS,
            "volume": g.VOLUME_ACTIONS,
            "clock_faces": list(g.CLOCK_FACES.items()), "clock_options": g.CLOCK_OPTIONS,
            "world_cities": g.WORLD_CITIES,
            "mtimes": {"macros": mtime(g.MACRO_FILE), "settings": mtime(g.SETTINGS_FILE)},
            "paths": {"macros": g.MACRO_FILE, "settings": g.SETTINGS_FILE,
                      "driver": os.path.join(HERE, "g19s.py")},
            "service": service_status(),
            "tools": dict({t: bool(shutil.which(t)) for t in ("mpv", "playerctl", "systemctl")},
                          mpris=bool(g.find_mpris_plugin())),
        })

    def api_post_active(self, q):
        macros, _ = read_macros()
        i = int(self._json().get("index", 0))
        if not 0 <= i < len(macros["profiles"]):
            raise ValueError("Unbekanntes Profil")
        g.save_state(profile=i)
        self._send(200, {"active": i})

    def api_get_poll(self, q):
        macros, _ = read_macros()
        self._send(200, {"mtimes": {"macros": mtime(g.MACRO_FILE),
                                    "settings": mtime(g.SETTINGS_FILE)},
                         "active": active_profile(len(macros["profiles"])),
                         "version": VERSION,
                         "service": service_status(max_age=10),
                         "radio": test_radio.current()})

    def api_post_macros(self, q):
        data = clean_macros(self._json().get("macros"))
        g.save_json(g.MACRO_FILE, data, compact_steps=True)
        self._send(200, {"ok": True, "macros": data, "mtime": mtime(g.MACRO_FILE)})

    def api_post_settings(self, q):
        data = clean_settings(self._json().get("settings"))
        g.save_json(g.SETTINGS_FILE, data, compact_steps=True, private=True)
        self._send(200, {"ok": True, "settings": data, "mtime": mtime(g.SETTINGS_FILE)})

    # -- API: Vorschau ----------------------------------------------------- #
    def api_post_preview(self, q):
        body = self._json()
        png = render_preview(body.get("page", 0), body.get("profile", "M1"), body.get("settings"),
                             body.get("pidx", 0), body.get("colors"), body.get("name"), body.get("face"))
        self._send(200, {"image": "data:image/png;base64," + base64.b64encode(png).decode()})


# ═══════════════════════════════════════════════════════════════════════════
# Modul api_radio
#   HTTP-Routen: Probehören und Sendersuche.
# ═══════════════════════════════════════════════════════════════════════════

class ApiRadio:
    # -- API: Radio -------------------------------------------------------- #
    def api_post_radio_play(self, q):
        body = self._json()
        station = {"name": str(body.get("name", "")), "url": str(body.get("url", "")).strip()}
        if not station["url"].startswith(("http://", "https://")):
            raise ValueError("Bitte eine Stream-Adresse mit http:// oder https:// angeben")
        player = str(body.get("player") or g.DEFAULT_SETTINGS["radio_player"])
        if not test_radio.play(station, player):
            raise RuntimeError("Der Radioplayer ließ sich nicht starten. Ist mpv installiert "
                               "(sudo apt install mpv)?")
        self._send(200, {"ok": True})

    def api_post_radio_stop(self, q):
        test_radio.stop()
        self._send(200, {"ok": True})

    def api_get_radio_search(self, q):
        query = q.get("q", [""])[0].strip()
        if len(query) < 2:
            raise ValueError("Bitte mindestens zwei Zeichen eingeben")
        self._send(200, {"results": radio_search(query)})


# ═══════════════════════════════════════════════════════════════════════════
# Modul api_info
#   HTTP-Routen: Infoseiten: Wetter, Termine, Ordner, Benachrichtigungen, Hardware, Nachrichten, Unwetter, Netzwerk, Updates, Songs, Lieblingsbilder.
# ═══════════════════════════════════════════════════════════════════════════

class ApiInfo:
    # -- API: Infoseiten --------------------------------------------------- #
    def api_get_weather_search(self, q):
        name = q.get("q", [""])[0].strip()
        if len(name) < 2:
            raise ValueError("Bitte mindestens zwei Buchstaben eingeben")
        try:
            results = g.geocode(name)
        except Exception as ex:         # Dienst im Netz: jeden Fehler als Meldung anzeigen
            raise RuntimeError(f"Ortssuche nicht erreichbar: {g.err_text(ex)}")
        self._send(200, {"results": results})

    def api_post_weather_test(self, q):
        w = self._json()
        poller = g.WeatherPoller(lambda: {"weather": w, "pages": ["weather"]})
        try:
            data = poller.fetch()
        except Exception as ex:         # Dienst im Netz: jeden Fehler als Meldung anzeigen
            raise RuntimeError(f"Wetterdienst nicht erreichbar: {g.err_text(ex)}")
        cur = data.get("current") or {}
        desc = g.WEATHER_CODES.get(int(cur.get("weather_code") or 0), ("", ""))[0]
        self._send(200, {"temp": cur.get("temperature_2m"), "desc": desc})

    def api_post_calendar_test(self, q):
        src = self._json()
        s = {"calendar": {"sources": [src], "days": 30}, "pages": ["calendar"]}
        try:
            data = g.CalendarPoller(lambda: s).fetch()
        except Exception as ex:         # Dienst im Netz: jeden Fehler als Meldung anzeigen
            raise RuntimeError(str(ex))
        if data["errors"]:
            raise RuntimeError(data["errors"][0])
        nxt = []
        for it in data["items"][:3]:
            st = it["start"]
            when = st.strftime("%d.%m.") if it["allday"] else st.strftime("%d.%m. %H:%M")
            nxt.append(f"{when} {it['title']}")
        self._send(200, {"count": len(data["items"]), "next": nxt, "calendars": data.get("calendars") or []})

    def api_get_folder_list(self, q):
        path = os.path.expanduser(q.get("path", ["~"])[0] or "~")
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            raise ValueError("Ordner nicht gefunden")
        try:
            names = sorted(n for n in os.listdir(path) if not n.startswith("."))
        except OSError as ex:
            raise ValueError(f"Ordner nicht lesbar: {ex.strerror}")
        dirs = [n for n in names if os.path.isdir(os.path.join(path, n))]
        images = sum(1 for n in names if n.lower().endswith(g.Slideshow.IMAGE_EXT))
        home = os.path.realpath(HOME)
        shown = "~" + path[len(home):] if path == home or path.startswith(home + "/") else path
        self._send(200, {"path": shown, "parent": os.path.dirname(path) if path != "/" else None,
                         "dirs": dirs[:500], "images": images})

    def api_post_notify_test(self, q):
        if not shutil.which("notify-send"):
            raise RuntimeError("notify-send fehlt (Paket libnotify-bin)")
        code, out = run(["notify-send", "-a", "G19s-Verwaltung", "Testbenachrichtigung",
                         "So sieht eine Benachrichtigung auf dem Display aus."])
        if code:
            raise RuntimeError(out or "notify-send meldet einen Fehler")
        self._send(200, {"ok": True})

    def api_get_hardware(self, q):
        hw = g.Hardware()
        s = hw.sensors()
        self._send(200, {"sensors": s, "disks": [(l, round(p), round(t / 1e9)) for l, p, t in hw.disks()]})

    def api_post_news_test(self, q):
        f = self._json()
        url = str(f.get("url") or "").strip()
        if not re.match(r"^https?://", url, re.I):
            raise ValueError("Die Adresse muss mit http:// oder https:// beginnen")
        try:
            items = g.parse_feed(g.http_get(url, timeout=20), f.get("name") or "")
        except Exception as ex:         # Dienst im Netz: jeden Fehler als Meldung anzeigen
            raise RuntimeError(f"Feed nicht lesbar: {g.err_text(ex)}")
        if not items:
            raise RuntimeError("Keine Meldungen gefunden – ist das ein RSS- oder Atom-Feed?")
        self._send(200, {"count": len(items), "first": items[0]["title"]})

    def api_post_warnings_test(self, q):
        s = clean_settings(self._json().get("settings") or g.load_settings())
        if s["weather"].get("lat") is None:
            raise ValueError("Zuerst oben einen Wetter-Ort wählen")
        try:
            data = g.WarningsPoller(lambda: s).fetch()
        except Exception as ex:         # Dienst im Netz: jeden Fehler als Meldung anzeigen
            raise RuntimeError(f"Warndienst nicht erreichbar: {g.err_text(ex)}")
        self._send(200, {"place": data["place"], "alerts": [f"{g.SEVERITY.get(a['severity'], ('', ''))[0]}: {a['event']}"
                                                             for a in data["alerts"]]})

    def api_post_network_test(self, q):
        s = clean_settings(self._json().get("settings") or g.load_settings())
        s["pages"] = ["network"]
        self._send(200, g.NetworkPoller(lambda: s).fetch())

    def api_post_updates_test(self, q):
        s = clean_settings(self._json().get("settings") or g.load_settings())
        self._send(200, g.UpdatesPoller(lambda: s).fetch())

    def api_get_songs(self, q):
        self._send(200, {"songs": g.load_list(g.SONGS_FILE)})

    def api_post_songs(self, q):
        songs = self._json().get("songs")
        if not isinstance(songs, list):
            raise ValueError("Ungültige Liste")
        keep = [{k: str(x.get(k) or "")[:300] for k in ("time", "artist", "title", "source")}
                for x in songs if isinstance(x, dict)]
        g.save_json(g.SONGS_FILE, keep)
        self._send(200, {"songs": keep})

    def api_get_favorites(self, q):
        self._send(200, {"favorites": g.load_list(g.FAVORITES_FILE)})

    def api_post_favorites(self, q):
        remove = {str(x) for x in (self._json().get("remove") or [])}
        favs = [f for f in g.load_list(g.FAVORITES_FILE) if str(f.get("id")) not in remove]
        g.save_json(g.FAVORITES_FILE, favs)
        self._send(200, {"favorites": favs})


# ═══════════════════════════════════════════════════════════════════════════
# Modul api_diashow
#   HTTP-Routen: Piwigo-Alben und Diashow-Test.
# ═══════════════════════════════════════════════════════════════════════════

class ApiSlides:
    # -- API: Piwigo ------------------------------------------------------- #
    def api_post_piwigo_albums(self, q):
        body = self._json()
        try:
            client = g.PiwigoClient(body.get("url"), body.get("user"), body.get("password"))
            albums = client.albums()
        except g.PiwigoError as ex:
            raise RuntimeError(str(ex))
        self._send(200, {"albums": albums})

    def api_post_piwigo_test(self, q):
        self._send(200, piwigo_test(self._json().get("slideshow")))


# ═══════════════════════════════════════════════════════════════════════════
# Modul api_dienst
#   HTTP-Routen: Treiberdienst, Sicherung, Update, Beenden.
# ═══════════════════════════════════════════════════════════════════════════

class ApiService:
    # -- API: Dienst ------------------------------------------------------- #
    def api_get_service(self, q):
        self._send(200, {"status": service_status(), "log": service_log()})

    def api_post_service(self, q):
        service_action(self._json().get("action"))
        time.sleep(0.8)
        self._send(200, {"status": service_status(), "log": service_log()})

    # -- API: Sicherung ---------------------------------------------------- #
    def api_get_backup(self, q):
        data = make_backup()
        name = f"g19s-sicherung-{datetime.datetime.now():%Y-%m-%d}.tar.gz"
        self._send(200, data, "application/gzip",
                   {"Content-Disposition": f'attachment; filename="{name}"'})

    def _backup_cfg(self):
        """Sicherungsziel aus der Anfrage (Formular, noch nicht gespeichert) oder aus settings.json."""
        body = self._json() if self.headers.get("Content-Length") not in (None, "0") else {}
        cfg = body.get("backup") if isinstance(body.get("backup"), dict) else {}
        if not cfg and body.get("folder"):                   # ältere Seite: nur Ordner
            cfg = {"target": "folder", "folder": body["folder"], "keep": body.get("keep")}
        return g.SCHEMA["backup"].clean(cfg or g.load_settings()["backup"], False)

    def api_post_backup_now(self, q):
        b = self._backup_cfg()
        try:
            path = g.auto_backup(b, b["keep"], HOME)
        except OSError as ex:
            g.save_state(last_backup_error=str(ex))
            raise RuntimeError(str(ex))
        g.save_state(last_backup=time.time(), last_backup_file=path, last_backup_error="")
        self._send(200, {"path": path})

    def api_post_backup_test(self, q):
        try:
            msg = g.test_backup_target(self._backup_cfg())
        except OSError as ex:
            raise RuntimeError(str(ex))
        self._send(200, {"message": msg})

    def api_get_backup_status(self, q):
        st = g.load_state()
        self._send(200, {"last": st.get("last_backup"), "file": st.get("last_backup_file", ""),
                         "error": st.get("last_backup_error", "")})

    def api_get_backupinfo(self, q):
        self._send(200, {"files": backup_members()})

    def api_post_restore(self, q):
        raw = self._body()
        if q.get("inspect") == ["1"]:
            return self._send(200, restore_backup(raw, inspect=True))
        restored, safety = restore_backup(raw, programs=q.get("programs") == ["1"])
        self._send(200, {"restored": restored, "safety": safety})

    def api_get_versions(self, q):
        self._send(200, {"driver": file_version(os.path.join(HERE, "g19s.py")),
                         "driver_running": getattr(g, "VERSION", "älter"),
                         "gui": VERSION, "backups": UPDATE_BACKUP_DIR})

    def api_post_update(self, q):
        body = self._json()
        files = []
        for f in body.get("files") or []:
            try:
                files.append((str(f.get("name") or "datei.py"), base64.b64decode(f.get("data") or "")))
            except (ValueError, TypeError):
                raise ValueError("Datei konnte nicht gelesen werden")
        if not files:
            raise ValueError("Keine Datei ausgewählt")
        result = install_update(files)
        comps = {r["component"] for r in result}
        if "driver" in comps:
            try:
                service_action("restart")
            except RuntimeError as ex:
                for r in result:
                    if r["component"] == "driver":
                        r["warning"] = f"Treiber-Neustart fehlgeschlagen: {ex}"
        restart_gui = "gui" in comps
        self._send(200, {"installed": result, "restart_gui": restart_gui})
        if restart_gui:
            backup = next(r["backup"] for r in result if r["component"] == "gui")
            self.app.restart = {"backup": backup}
            threading.Thread(target=lambda: (time.sleep(0.4), self.app.server.shutdown()),
                             daemon=True).start()

    def api_post_quit(self, q):
        self._send(200, {"ok": True})
        threading.Thread(target=lambda: (time.sleep(0.2), self.app.server.shutdown()), daemon=True).start()

    def api_post_bye(self, q):
        self.app.last_contact = time.monotonic() - IDLE_TIMEOUT + 5   # bald beenden
        self._send(200, {"ok": True})


# ═══════════════════════════════════════════════════════════════════════════
# Modul http
#   HTTP-Server der Verwaltung: Anfragen prüfen (Host, Zugangsschlüssel) und an die api_*-Methoden verteilen.
#
#   Eine Route /api/a/b mit Methode POST ruft api_post_a_b() auf; die Routen stehen nach Themen in api_*.py.
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# Modul start
#   Start der Verwaltung: vorhandene Instanz finden, Server starten, Browserfenster öffnen, Neustart nach Update.
# ═══════════════════════════════════════════════════════════════════════════

# --------------------------------------------------------------------------- #
# Start
# --------------------------------------------------------------------------- #
def open_window(url, browser=None):
    if browser:
        cmd = shlex.split(browser) + [url]
    else:
        cmd = None
        for b in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                  "brave-browser", "microsoft-edge"):
            if shutil.which(b):
                cmd = [b, f"--app={url}", "--window-size=1200,860"]
                break
        if cmd is None:
            cmd = ["xdg-open", url]
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as ex:
        print(f"Browser konnte nicht geöffnet werden ({ex}). Adresse: {url}")


def _local(path, info, data=None, timeout=2):
    req = urllib.request.Request(f"http://127.0.0.1:{info['port']}{path}", data=data,
                                 headers={"X-Token": info["token"]})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def existing_instance():
    """Laufende Verwaltung derselben Version finden. Eine ältere Version wird beendet,
    damit nach einem Update nicht versehentlich die alte Oberfläche erscheint."""
    try:
        with open(INSTANCE_FILE) as f:
            info = json.load(f)
        state = _local("/api/poll", info)
    except Exception:                   # keine oder abgestürzte Instanz: neu starten
        return None
    if state.get("version") == VERSION:
        return info
    print(f"Ältere Verwaltung ({state.get('version') or 'ohne Version'}) wird beendet …", flush=True)
    try:
        _local("/api/quit", info, data=b"{}")
    except Exception:                   # alte Instanz reagiert nicht auf /api/quit
        try:
            os.kill(int(info.get("pid")), signal.SIGTERM)    # alte Versionen ohne /api/quit
        except (OSError, TypeError, ValueError):
            pass
    for _ in range(30):
        time.sleep(0.2)
        try:
            _local("/api/poll", info, timeout=0.5)
        except Exception:               # nicht mehr erreichbar = beendet
            break
    return None


def bind_server(port, tries=40):
    """Beim Neustart nach einem Update ist der Port evtl. noch kurz belegt."""
    for i in range(tries):
        try:
            return http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            if not port or i == tries - 1:
                raise
            time.sleep(0.25)


def restart_after_update(app, args):
    """Neue Verwaltung mit gleicher Adresse starten; startet sie nicht, alte Version zurückholen."""
    script = os.path.realpath(__file__)
    cmd = [sys.executable, script, "--restarted", "--port", str(app.port), "--token", app.token]
    backup = (app.restart or {}).get("backup")
    for attempt in ("neu", "zurück"):
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Neue Verwaltung läuft." if attempt == "neu" else "Alte Verwaltung wiederhergestellt.", flush=True)
            return
        if attempt == "neu" and backup and os.path.exists(backup):
            print("Neue Verwaltung startet nicht – stelle die vorherige Version wieder her.", flush=True)
            shutil.copy2(backup, script)
        else:
            return


def install_desktop():
    path = os.path.join(HOME, ".local/share/applications/g19s-gui.desktop")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    script = os.path.realpath(__file__)
    with open(path, "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\n"
                "Type=Application\n"
                "Name=G19s-Verwaltung\n"
                "GenericName=Tastatur-Einstellungen\n"
                "Comment=Logitech G19s: G-Tasten, Makros, Radiosender und Display verwalten\n"
                f"Exec=/usr/bin/python3 {shlex.quote(script)}\n"
                "Icon=input-keyboard\n"
                "Terminal=false\n"
                "Categories=Settings;HardwareSettings;Utility;\n"
                "Keywords=Logitech;G19;Tastatur;Makro;Radio;\n")
    subprocess.run(["update-desktop-database", os.path.dirname(path)],
                   capture_output=True) if shutil.which("update-desktop-database") else None
    print(f"Menüeintrag angelegt: {path}")


def main():
    ap = argparse.ArgumentParser(description="Grafische Verwaltung für die Logitech G19s")
    ap.add_argument("--no-browser", action="store_true", help="Browser nicht öffnen")
    ap.add_argument("--browser", help="Browserbefehl, z. B. 'firefox --new-window'")
    ap.add_argument("--port", type=int, default=0, help="fester Port (Standard: zufällig)")
    ap.add_argument("--token", help=argparse.SUPPRESS)
    ap.add_argument("--restarted", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--install-desktop", action="store_true",
                    help="Eintrag im Anwendungsmenü anlegen")
    args = ap.parse_args()

    if args.install_desktop:
        install_desktop()
        return

    if args.restarted:
        args.no_browser = True
    info = None if args.no_browser else existing_instance()
    if info:
        open_window(f"http://127.0.0.1:{info['port']}/#{info['token']}", args.browser)
        return

    try:
        g.migrate_files()                   # ältere settings.json/macros.json umstellen (wie der Treiber)
    except (OSError, ValueError) as ex:
        print(f"Umstellung älterer Dateien nicht möglich: {ex}")
    app = App(args.token or secrets.token_urlsafe(24))
    Handler.app = app
    server = bind_server(args.port)
    server.daemon_threads = True
    app.port = server.server_address[1]
    app.server = server
    url = f"http://127.0.0.1:{app.port}/#{app.token}"

    try:
        os.makedirs(RUNTIME_DIR, mode=0o700, exist_ok=True)
        fd = os.open(INSTANCE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"port": app.port, "token": app.token, "pid": os.getpid()}, f)
    except OSError:
        pass

    def watchdog():
        while True:
            time.sleep(3)
            now = time.monotonic()
            if app.first_contact is None:
                if (args.restarted or not args.no_browser) and now - app.started > FIRST_CONTACT_TIMEOUT:
                    break
            elif now - app.last_contact > IDLE_TIMEOUT:
                break
        server.shutdown()

    threading.Thread(target=watchdog, daemon=True).start()
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown).start())

    print(f"G19s-Verwaltung läuft: {url}", flush=True)
    if not args.no_browser:
        open_window(url, args.browser)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        test_radio.stop()
        server.server_close()
        try:
            with open(INSTANCE_FILE) as f:
                if json.load(f).get("pid") == os.getpid():
                    os.remove(INSTANCE_FILE)
        except (OSError, ValueError):
            pass
        if app.restart:
            restart_after_update(app, args)
        else:
            print("G19s-Verwaltung beendet.")


PAGE_HTML = r'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>G19s-Verwaltung</title>
<style>
:root {
  --bg: #f3f4f7; --panel: #ffffff; --panel2: #f7f8fa; --text: #1b2130; --muted: #5f6b7d;
  --line: #e1e5ec; --line2: #cfd5df; --accent: #1f6feb; --accent-text: #ffffff;
  --danger: #c93434; --ok: #1d8a4e; --warn: #b26a00; --shadow: 0 1px 2px rgba(20,30,50,.06), 0 4px 16px rgba(20,30,50,.05);
  --radius: 12px; --mono: ui-monospace, "JetBrains Mono", "DejaVu Sans Mono", monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111418; --panel: #1a1e25; --panel2: #20252e; --text: #e7eaf0; --muted: #98a2b3;
    --line: #2a303b; --line2: #394150; --accent: #4c8dff; --accent-text: #0b1220;
    --danger: #ff6b6b; --ok: #3ecf7e; --warn: #f0a93b; --shadow: 0 1px 2px rgba(0,0,0,.3);
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.45 "Noto Sans", "Segoe UI", system-ui, sans-serif; }
button, input, select, textarea { font: inherit; color: inherit; }
header { display: flex; align-items: center; gap: 16px; padding: 14px 22px 0; }
header h1 { font-size: 18px; margin: 0; font-weight: 650; letter-spacing: .2px; }
header .sub { color: var(--muted); font-size: 13px; }
.spacer { flex: 1; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 99px;
  font-size: 12.5px; background: var(--panel2); border: 1px solid var(--line); white-space: nowrap; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); display: inline-block; }
.dot.ok { background: var(--ok); } .dot.bad { background: var(--danger); } .dot.warn { background: var(--warn); }
nav { display: flex; gap: 4px; padding: 12px 22px 0; border-bottom: 1px solid var(--line); overflow-x: auto; }
nav button { background: none; border: 0; padding: 9px 14px; border-bottom: 2px solid transparent;
  color: var(--muted); cursor: pointer; font-weight: 550; white-space: nowrap; }
nav button.active { color: var(--text); border-bottom-color: var(--accent); }
nav button .badge { display: none; width: 7px; height: 7px; border-radius: 50%; background: var(--warn);
  margin-left: 6px; vertical-align: middle; }
nav button.dirty .badge { display: inline-block; }
main { padding: 18px 22px 90px; max-width: 1280px; }
.tab { display: none; } .tab.active { display: block; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 16px 18px; margin-bottom: 16px; }
.card h2 { font-size: 15px; margin: 0 0 4px; font-weight: 650; }
.card .hint, .hint { color: var(--muted); font-size: 13px; margin: 0 0 12px; }
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.grid2 { display: grid; grid-template-columns: 380px 1fr; gap: 16px; align-items: start; }
@media (max-width: 900px) { .grid2 { grid-template-columns: 1fr; } }
label.field { display: block; margin: 0 0 12px; }
label.field > span { display: block; font-size: 12.5px; color: var(--muted); margin-bottom: 4px; font-weight: 550; }
input[type=text], input[type=url], input[type=number], input[type=password], select, textarea {
  background: var(--panel2); border: 1px solid var(--line2); border-radius: 8px; padding: 7px 10px;
  width: 100%; outline: none; }
input:focus, select:focus, textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent); }
textarea { min-height: 110px; resize: vertical; font-family: var(--mono); font-size: 13px; }
.btn { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line2); background: var(--panel2);
  border-radius: 8px; padding: 7px 13px; cursor: pointer; font-weight: 550; white-space: nowrap; }
.btn:hover { border-color: var(--accent); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-text); }
.btn.danger { color: var(--danger); }
.btn.small { padding: 4px 9px; font-size: 13px; }
.btn.icon { padding: 4px 8px; min-width: 30px; justify-content: center; }
.btn:disabled { opacity: .45; cursor: default; }
.btn.rec { background: var(--danger); border-color: var(--danger); color: #fff; }
/* Profile */
.profiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 14px;
  background: var(--panel2); padding: 4px; border-radius: 10px; border: 1px solid var(--line); }
.profiles button { border: 0; background: none; padding: 8px 6px; border-radius: 7px; cursor: pointer;
  font-weight: 650; display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--muted); }
.profiles button.active { background: var(--panel); color: var(--text); box-shadow: var(--shadow); }
.swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; border: 1px solid rgba(0,0,0,.2); }
/* G-Tasten */
.keypad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.gkey { position: relative; text-align: left; border: 1px solid var(--line2); background: var(--panel2);
  border-radius: 10px; padding: 9px 10px 8px; cursor: pointer; min-height: 70px; overflow: hidden; }
.gkey:hover { border-color: var(--pc, var(--accent)); }
.gkey.sel { border-color: var(--pc, var(--accent)); box-shadow: 0 0 0 2px var(--pc, var(--accent)) inset; }
.gkey .gnum { font-weight: 750; font-size: 13px; }
.gkey .gic { position: absolute; right: 8px; top: 7px; font-size: 13px; opacity: .8; }
.gkey .glabel { display: block; margin-top: 6px; font-size: 12.5px; color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gkey.has .glabel { color: var(--text); font-weight: 550; }
.gkey .bar { position: absolute; left: 0; bottom: 0; height: 3px; width: 100%; background: var(--pc); opacity: 0; }
.gkey.has .bar { opacity: .9; }
.legend { margin-top: 12px; font-size: 12.5px; color: var(--muted); }
/* Editor */
.edhead { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.edhead h2 { margin: 0; font-size: 17px; }
.types { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 14px; }
@media (max-width: 1100px) { .types { grid-template-columns: repeat(2, 1fr); } }
.types button { border: 1px solid var(--line2); background: var(--panel2); border-radius: 9px; padding: 8px;
  cursor: pointer; text-align: left; font-size: 13px; display: flex; gap: 8px; align-items: center; }
.types button.active { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent) inset; font-weight: 650; }
.types .ti { width: 20px; text-align: center; }
.note { background: var(--panel2); border: 1px dashed var(--line2); border-radius: 9px; padding: 10px 12px;
  color: var(--muted); font-size: 13px; margin-bottom: 12px; }
.note b { color: var(--text); }
.warnbox { background: color-mix(in srgb, var(--warn) 12%, transparent); border: 1px solid color-mix(in srgb, var(--warn) 45%, transparent);
  border-radius: 9px; padding: 8px 12px; font-size: 13px; margin: 8px 0 12px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line); }
.chips { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; min-height: 38px; padding: 5px;
  border: 1px solid var(--line2); border-radius: 8px; background: var(--panel2); }
.chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 4px 3px 9px; border-radius: 6px;
  background: var(--panel); border: 1px solid var(--line2); font-weight: 600; font-size: 13px; }
.chip button { border: 0; background: none; cursor: pointer; color: var(--muted); padding: 0 4px; }
.plus { color: var(--muted); }
.capture { border: 2px dashed var(--line2); border-radius: 10px; padding: 14px; text-align: center; color: var(--muted);
  margin: 8px 0; }
.capture.on { border-color: var(--danger); color: var(--text); background: color-mix(in srgb, var(--danger) 8%, transparent); }
table.steps { width: 100%; border-collapse: collapse; font-size: 13px; }
table.steps th { text-align: left; font-size: 12px; color: var(--muted); font-weight: 600; padding: 4px 6px; }
table.steps td { padding: 3px 4px; border-top: 1px solid var(--line); }
table.steps td.n { color: var(--muted); width: 30px; text-align: right; padding-right: 8px; }
table.steps input[type=number] { width: 84px; padding: 4px 6px; }
table.steps select { padding: 4px 6px; }
.stepsbox { max-height: 380px; overflow: auto; border: 1px solid var(--line); border-radius: 9px; }
.tools { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0; align-items: center; }
.tools input[type=number] { width: 80px; padding: 5px 8px; }
/* Radio */
table.list { width: 100%; border-collapse: collapse; }
table.list th { text-align: left; font-size: 12px; color: var(--muted); font-weight: 600; padding: 6px; }
table.list td { padding: 5px 6px; border-top: 1px solid var(--line); vertical-align: middle; }
table.list tr.playing td { background: color-mix(in srgb, var(--ok) 10%, transparent); }
.logo { width: 34px; height: 34px; border-radius: 6px; object-fit: cover; background: var(--panel2);
  border: 1px solid var(--line); display: block; }
.results { max-height: 420px; overflow: auto; }
.res { display: flex; gap: 10px; align-items: center; padding: 8px 4px; border-top: 1px solid var(--line); }
.res .meta { color: var(--muted); font-size: 12.5px; }
.res .grow { flex: 1; min-width: 0; }
.res .name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* Einstellungen */
.colors { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.colorbox { border: 1px solid var(--line); border-radius: 10px; padding: 10px; display: flex; gap: 10px; align-items: center; }
.colorbox input[type=color] { width: 46px; height: 34px; border: 1px solid var(--line2); border-radius: 7px; background: none; padding: 2px; cursor: pointer; }
.preview { display: flex; gap: 18px; align-items: flex-start; flex-wrap: wrap; }
.lcd { width: 320px; height: 240px; border-radius: 6px; background: #000; border: 8px solid #2b2f36;
  box-sizing: content-box; image-rendering: auto; box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.seg { display: inline-flex; border: 1px solid var(--line2); border-radius: 8px; overflow: hidden; }
.seg button { border: 0; background: var(--panel2); padding: 6px 11px; cursor: pointer; border-right: 1px solid var(--line2); }
.seg button:last-child { border-right: 0; }
.seg button.active { background: var(--accent); color: var(--accent-text); font-weight: 650; }
input[type=range] { width: 220px; accent-color: var(--accent); }
.check { display: flex; gap: 8px; align-items: center; margin: 6px 0 12px; cursor: pointer; }
.check input { width: 16px; height: 16px; accent-color: var(--accent); }
/* Dienst */
.log { background: #0e1116; color: #d7dde8; padding: 12px; border-radius: 9px; max-height: 360px; overflow: auto;
  font: 12px/1.45 var(--mono); white-space: pre-wrap; margin: 0; }
.kv { display: grid; grid-template-columns: 160px 1fr; gap: 6px 12px; font-size: 13px; }
.kv div:nth-child(odd) { color: var(--muted); }
code { font-family: var(--mono); font-size: 12.5px; background: var(--panel2); padding: 1px 5px; border-radius: 4px;
  border: 1px solid var(--line); word-break: break-all; }
/* Leiste, Hinweise */
.savebar { position: fixed; left: 0; right: 0; bottom: 0; display: none; justify-content: center; padding: 12px;
  background: color-mix(in srgb, var(--panel) 92%, transparent); border-top: 1px solid var(--line); backdrop-filter: blur(6px); z-index: 5; }
.savebar.show { display: flex; }
.savebar .row { max-width: 1280px; width: 100%; justify-content: flex-end; }
.toasts { position: fixed; right: 18px; bottom: 84px; display: flex; flex-direction: column; gap: 8px; z-index: 20; }
.toast { background: var(--text); color: var(--bg); padding: 10px 14px; border-radius: 9px; max-width: 420px;
  box-shadow: 0 6px 24px rgba(0,0,0,.25); font-size: 13.5px; animation: pop .18s ease-out; }
.toast.err { background: var(--danger); color: #fff; }
@keyframes pop { from { transform: translateY(8px); opacity: 0; } to { transform: none; opacity: 1; } }
.banner { display: none; margin-bottom: 14px; }
.banner.show { display: flex; }
.overlay { position: fixed; inset: 0; background: rgba(10,12,16,.72); display: none; align-items: center;
  justify-content: center; z-index: 30; }
.overlay.show { display: flex; }
.overlay .card { max-width: 440px; }
.muted { color: var(--muted); }
.pagelist { border: 1px solid var(--line); border-radius: 9px; }
.snip { border: 1px solid var(--line); border-radius: 9px; padding: 10px; margin-bottom: 10px; display: grid; gap: 8px; }
.snip textarea { width: 100%; resize: vertical; font: inherit; }
.pagerow { display: flex; align-items: center; gap: 10px; padding: 6px 10px; border-top: 1px solid var(--line); }
.pagerow:first-child { border-top: 0; }
.pagerow.off .pn { color: var(--muted); }
.pagerow .pn { flex: 1; font-weight: 600; }
.pagerow input { width: 16px; height: 16px; accent-color: var(--accent); }
input[type=time] { background: var(--panel2); border: 1px solid var(--line2); border-radius: 8px; padding: 6px 8px; }
.fbrowser { border: 1px solid var(--line); border-radius: 9px; margin-top: 10px; max-height: 300px; overflow: auto; }
.fbrowser .frow { display: flex; gap: 8px; padding: 6px 12px; border-top: 1px solid var(--line); cursor: pointer; }
.fbrowser .frow:hover { background: var(--panel2); }
.fbrowser .fhead { display: flex; gap: 8px; align-items: center; padding: 8px 12px; background: var(--panel2); position: sticky; top: 0; }
.srcrow { display: grid; grid-template-columns: 1.1fr 2.4fr 1fr 1fr auto auto; gap: 6px; align-items: center; margin-bottom: 6px; }
.feedrow { margin-bottom: 8px; } .feedrow .muted { display: block; margin: 3px 0 0 4px; font-size: 12.5px; }
.srcrow input[type=color] { width: 38px; height: 32px; border: 1px solid var(--line2); border-radius: 6px; padding: 1px; background: none; }
@media (max-width: 900px) { .srcrow { grid-template-columns: 1fr 1fr; } }
.georesults .res { cursor: pointer; }
.profcolors { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.profcolors label { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line); border-radius: 8px;
  padding: 4px 6px; font-weight: 650; font-size: 13px; cursor: pointer; }
.profcolors input[type=color] { width: 30px; height: 24px; border: 1px solid var(--line2); border-radius: 5px; padding: 1px; background: none; cursor: pointer; }
.activebadge { display: inline-flex; align-items: center; gap: 6px; color: var(--ok); font-weight: 600; font-size: 13px; }
.pwgrid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 12px; }
@media (max-width: 800px) { .pwgrid { grid-template-columns: 1fr; } }
.albums { max-height: 380px; overflow: auto; border: 1px solid var(--line); border-radius: 9px; padding: 4px 0; }
.album { display: flex; align-items: center; gap: 9px; padding: 6px 12px; cursor: pointer; }
.album:hover { background: var(--panel2); }
.album input { width: 16px; height: 16px; accent-color: var(--accent); flex: none; }
.album .an { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.album .ac { color: var(--muted); font-size: 12.5px; white-space: nowrap; }
.album.missing .an { color: var(--muted); font-style: italic; }
.lcd[src=""], .lcd:not([src]) { visibility: hidden; }
.empty { color: var(--muted); padding: 14px 6px; text-align: center; }

/* Karte „Uhr“ */
.clkgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 4px 12px; }
.clkgrid label { display: flex; align-items: center; gap: 7px; cursor: pointer; }
.clkgrid input { width: 16px; height: 16px; accent-color: var(--accent); }
.clkopt { margin-bottom: 10px; }
.clkopt .row { gap: 8px; }
.clkopt input[type=color] { width: 42px; height: 28px; padding: 0; border: 1px solid var(--line); border-radius: 6px; background: none; }
.clkcities { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 10px; max-width: 360px; }
.okbox { background: color-mix(in srgb, #3ecf7e 12%, transparent); border: 1px solid color-mix(in srgb, #3ecf7e 45%, transparent);
  border-radius: 9px; padding: 8px 12px; font-size: 13px; margin: 8px 0 12px; }

</style>
</head>
<body>
<header>
  <div>
    <h1>G19s-Verwaltung</h1>
    <div class="sub">Logitech G19s · G-Tasten, Makros, Radio und Display</div>
  </div>
  <div class="spacer"></div>
  <span class="pill" id="svcPill"><span class="dot"></span><span>Treiber …</span></span>
</header>
<nav id="nav">
  <button data-tab="keys" class="active">Tasten<span class="badge"></span></button>
  <button data-tab="radio">Radiosender<span class="badge"></span></button>
  <button data-tab="snippets">Textbausteine<span class="badge"></span></button>
  <button data-tab="settings">Beleuchtung & Display<span class="badge"></span></button>
  <button data-tab="slides">Diashow<span class="badge"></span></button>
  <button data-tab="info">Infoseiten<span class="badge"></span></button>
  <button data-tab="service">Dienst & Sicherung</button>
</nav>
<main>
  <div class="warnbox banner row" id="extBanner">
    <span style="flex:1">Die Tastenbelegung wurde außerhalb geändert (z. B. durch eine MR-Aufnahme an der Tastatur).</span>
    <button class="btn small" id="extReload">Neu laden (eigene Änderungen verwerfen)</button>
  </div>

  <!-- ===================== Tasten ===================== -->
  <section class="tab active" id="tab-keys">
    <div class="grid2">
      <div class="card">
        <h2>Profil</h2>
        <p class="hint">Bis zu 10 Profile mit je 36 Belegungen. An der Tastatur wechselt die Displaytaste SETTINGS das Profil.</p>
        <div class="row" style="flex-wrap:nowrap; gap:6px">
          <select id="profSel" style="flex:1; min-width:0"></select>
          <button class="btn icon small" id="profUp" title="Profil nach oben">↑</button>
          <button class="btn icon small" id="profDown" title="Profil nach unten">↓</button>
        </div>
        <div class="row" style="gap:6px; margin:8px 0 10px">
          <button class="btn small" id="profNew">+ Neu</button>
          <button class="btn small" id="profCopy">Kopieren</button>
          <button class="btn small" id="profRename">Umbenennen</button>
          <button class="btn small danger" id="profDel">Löschen</button>
        </div>
        <div class="profcolors" id="profColors"></div>
        <div id="profActive" style="margin:10px 0 4px"></div>
        <h2 style="margin-top:16px">Ebene & G-Taste</h2>
        <p class="hint">Ebene M1–M3 wählen (wie die M-Tasten), dann eine G-Taste anklicken.</p>
        <div class="profiles" id="profiles"></div>
        <div class="keypad" id="keypad"></div>
        <div class="legend">Tasten ohne Belegung senden F13–F24 (M2: Strg+, M3: Alt+) und können in den KDE-Kurzbefehlen belegt werden.</div>
      </div>
      <div class="card" id="editor"></div>
    </div>
  </section>

  <!-- ===================== Radio ===================== -->
  <section class="tab" id="tab-radio">
    <div class="card">
      <h2>Meine Radiosender</h2>
      <p class="hint">Diese Sender stehen im Reiter „Tasten“ zur Auswahl. Auf der Musikseite des Displays öffnet die Taste MENU diese Liste zum Auswählen, BACK schaltet das Radio aus.</p>
      <table class="list" id="stations"></table>
      <div class="row" style="margin-top:10px">
        <button class="btn" id="addStation">+ Sender hinzufügen</button>
        <button class="btn" id="stopTest" style="display:none">■ Probehören beenden</button>
      </div>
    </div>
    <div class="card">
      <h2>Sender suchen</h2>
      <p class="hint">Durchsucht das freie Verzeichnis radio-browser.info (über 40.000 Sender).</p>
      <form class="row" id="searchForm">
        <input type="text" id="searchQ" placeholder="z. B. Rock Antenne, Bayern 3, SWR3 …" style="flex:1; min-width:220px">
        <button class="btn primary" type="submit">Suchen</button>
      </form>
      <div class="results" id="results"></div>
    </div>
    <div class="card">
      <h2>Radiowecker</h2>
      <p class="hint">Schaltet zur eingestellten Zeit den gewählten Sender ein und weckt das Display. Der PC muss dafür laufen (nicht im Ruhezustand).</p>
      <label class="check"><input type="checkbox" id="acOn"> Radiowecker verwenden</label>
      <div class="row" style="margin-bottom:10px">
        <label class="field" style="margin:0">um <input type="time" id="acTime" style="width:auto"></label>
        <label class="field" style="margin:0">Sender <select id="acStation" style="width:auto"></select></label>
      </div>
      <div class="seg" id="acDays"></div>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between; margin-bottom:6px">
        <h2>Gemerkte Songs</h2>
        <div class="row"><button class="btn small" id="songsRefresh">↻</button><button class="btn small danger" id="songsClear">Liste leeren</button></div>
      </div>
      <p class="hint">Titel, die du mit einer G-Taste (Aktion „Musiksteuerung → Song merken“) gespeichert hast – mit Links zur Suche.</p>
      <div id="songs"></div>
    </div>
    <div class="card">
      <h2>Wiedergabe</h2>
      <p class="hint">Befehl, mit dem Radiosender abgespielt werden. <code>{url}</code> wird durch die Stream-Adresse ersetzt.</p>
      <label class="field"><span>Player-Befehl</span><input type="text" id="player"></label>
      <div id="mpvHint"></div>
    </div>
  </section>

  <!-- ===================== Textbausteine ===================== -->
  <section class="tab" id="tab-snippets">
    <div class="card">
      <h2>Textbausteine</h2>
      <p class="hint">Texte, die du am Display auswählst und einfügst: Lege im Reiter „Tasten“ eine G-Taste mit der Aktion <b>Textbausteine</b> an. Ein Druck darauf zeigt die Liste auf dem Display, <b>Hoch/Runter</b> wählt, <b>OK</b> tippt den Text in das gerade aktive Fenster. Mit <b>Gruppen</b> kannst du verschiedenen G-Tasten verschiedene Listen geben.</p>
      <div id="snippetList"></div>
      <div class="row" style="margin-top:10px"><button class="btn" id="addSnippet">+ Textbaustein hinzufügen</button></div>
    </div>
  </section>

  <!-- ===================== Einstellungen ===================== -->
  <section class="tab" id="tab-settings">
    <div class="card">
      <h2>Tastaturbeleuchtung</h2>
      <p class="hint">Die Farben für M1/M2/M3 legst du je Profil im Reiter „Tasten“ fest.</p>
      <label class="check"><input type="checkbox" id="keepBacklight"> Beleuchtung nicht umfärben (eigene Farbe der Tastatur behalten)</label>
    </div>
    <div class="card">
      <h2>Display</h2>
      <div class="preview">
        <div>
          <label class="check"><input type="checkbox" id="brightOn"> Helligkeit festlegen</label>
          <div class="row" style="margin-bottom:14px"><input type="range" id="bright" min="0" max="100" step="5"> <span id="brightVal" class="muted"></span></div>
          <label class="field" style="max-width:260px"><span>Startseite nach dem Start (Ebene M1)</span><select id="startPage"></select></label>
          <p class="hint" style="max-width:300px">Displaytasten: Links/Rechts blättern. Musikseite: OK = Play/Pause, Hoch/Runter = Titel, MENU = Senderliste, BACK = Radio aus. Terminseite: Hoch/Runter = Termin markieren, OK = Details, MENU = Kalender wählen.</p>
        </div>
        <div>
          <div class="row" style="margin-bottom:10px">
            <select id="pvPages" style="width:auto"></select>
            <div class="seg" id="pvProfiles"></div>
          </div>
          <img class="lcd" id="lcd" alt="Display-Vorschau">
          <div class="hint" style="margin-top:6px">Vorschau für das im Reiter „Tasten“ gewählte Profil.</div>
        </div>
      </div>
    </div>
    <div class="card">
      <h2>Displayseiten</h2>
      <p class="hint">Welche Seiten mit Links/Rechts durchgeblättert werden, und in welcher Reihenfolge – für jede Ebene (M1/M2/M3) getrennt. Beim Umschalten mit der M-Taste zeigt das Display die Seiten dieser Ebene.</p>
      <div class="row" style="margin-bottom:10px">
        <span class="muted">Gilt für:</span><select id="plScope" style="width:auto"></select>
        <button class="btn small" id="plOwnOff" style="display:none">Wieder Standard verwenden</button>
      </div>
      <div class="row" style="margin-bottom:10px">
        <span class="muted">Ebene:</span><div class="seg" id="plLayers"></div>
        <button class="btn small" id="plCopy" style="margin-left:auto">Auf alle Ebenen übertragen</button>
      </div>
      <div class="pagelist" id="pageList"></div>
    </div>
    <div class="card">
      <h2>Uhr</h2>
      <p class="hint">Aussehen der Zifferblätter der Seite „Uhr“. Welches Zifferblatt das Display zeigt, wählst du an der Tastatur: auf der Uhr <b>MENU</b> drücken – getrennt für jedes Profil und jede Ebene.</p>
      <div class="preview">
        <div>
          <label class="field" style="max-width:300px"><span>Zifferblatt</span><select id="clkFace"></select></label>
          <div id="clkOpts"></div>
        </div>
        <div>
          <img class="lcd" id="clkLcd" alt="Vorschau des Zifferblatts">
          <div class="hint" style="margin-top:6px">Vorschau mit der Farbe der gewählten Ebene.</div>
        </div>
      </div>
      <h3 style="margin:16px 0 4px">Im Displaymenü anbieten</h3>
      <p class="hint">Nur angehakte Zifferblätter erscheinen in der Liste, die MENU auf der Uhr öffnet.</p>
      <div class="clkgrid" id="clkMenu"></div>
      <div class="row" style="margin-top:8px"><button class="btn small" id="clkAll">Alle anhaken</button></div>
    </div>
    <div class="card">
      <h2>Nachtmodus</h2>
      <p class="hint">Zu festen Zeiten Display und Beleuchtung abdunkeln. Ein Tastendruck weckt beides für eine Minute.</p>
      <label class="check"><input type="checkbox" id="nightOn"> Nachtmodus verwenden</label>
      <div class="row" style="margin-bottom:12px">
        <label class="field" style="margin:0">von <input type="time" id="nightStart" style="width:auto"></label>
        <label class="field" style="margin:0">bis <input type="time" id="nightEnd" style="width:auto"></label>
      </div>
      <div class="seg" id="nightMode" style="margin-bottom:10px"><button data-mode="dim">Display dimmen</button><button data-mode="off">Display ausschalten</button></div>
      <div class="row" id="nightDimRow" style="margin-bottom:8px"><span class="muted">Helligkeit nachts</span><input type="range" id="nightBright" min="0" max="60" step="1"><span class="muted" id="nightBrightVal"></span></div>
      <label class="check"><input type="checkbox" id="nightBacklight"> Tastaturbeleuchtung nachts ausschalten</label>
    </div>
    <div class="card">
      <h2>Bildschirmschoner</h2>
      <p class="hint">Wenn eine Weile weder Tastatur noch Maus benutzt wurden, zeigt das Display eine bestimmte Seite – z. B. die Diashow. Beim nächsten Tastendruck geht es zurück.</p>
      <label class="check"><input type="checkbox" id="saverOn"> Bildschirmschoner verwenden</label>
      <div class="row">
        <label class="field" style="margin:0">nach <input type="number" id="saverMin" min="1" max="240" style="width:80px"> Minuten</label>
        <label class="field" style="margin:0">Seite <select id="saverPage" style="width:auto"></select></label>
      </div>
    </div>
    <div class="card">
      <h2>Lautstärke</h2>
      <label class="field" style="max-width:320px"><span>Schrittweite der G-Tasten-Aktion „Lautstärke“ (Prozent)</span><input type="number" id="volStep" min="1" max="25"></label>
      <label class="check"><input type="checkbox" id="timerSound"> Signalton, wenn ein Timer abläuft oder eine Pomodoro-Phase wechselt</label>
    </div>
  </section>

  <!-- ===================== Diashow ===================== -->
  <section class="tab" id="tab-slides">
    <div class="card">
      <h2>Bildquelle</h2>
      <div class="seg" id="slSource"><button data-src="piwigo">Piwigo-Galerie</button><button data-src="folder">Ordner auf diesem Rechner</button></div>
    </div>
    <div class="card" id="folderBlock">
      <h2>Bilderordner</h2>
      <p class="hint">JPG, PNG, WebP, GIF, BMP und TIFF werden angezeigt – mit „Unteralben einbeziehen“ auch aus Unterordnern.</p>
      <div class="row" style="flex-wrap:nowrap">
        <input type="text" id="fdPath" placeholder="~/Bilder" style="flex:1">
        <button class="btn" id="fdBrowse">Durchsuchen …</button>
      </div>
      <div id="fdBrowser"></div>
    </div>
    <div id="pwBlock">
    <div class="card">
      <h2>Piwigo-Galerie</h2>
      <p class="hint">Bilder aus deinen Piwigo-Alben erscheinen auf der Displayseite „Bilder“. Benutzer und Passwort nur für private Alben nötig.</p>
      <div class="pwgrid">
        <label class="field"><span>Adresse der Galerie</span><input type="url" id="pwUrl" placeholder="https://fotos.example.de"></label>
        <label class="field"><span>Benutzer (optional)</span><input type="text" id="pwUser" autocomplete="username"></label>
        <label class="field"><span>Passwort (optional)</span><input type="password" id="pwPass" autocomplete="current-password"></label>
      </div>
      <div class="row"><button class="btn primary" id="pwLoad">Alben laden</button><span class="muted" id="pwState"></span></div>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between; margin-bottom:6px">
        <h2>Alben</h2>
        <div class="row"><span class="muted" id="albumSum"></span>
          <button class="btn small" id="albAll">alle</button><button class="btn small" id="albNone">keine</button></div>
      </div>
      <div class="albums" id="albums"><div class="empty">Zuerst „Alben laden“ klicken.</div></div>
    </div>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between; margin-bottom:6px">
        <h2>Lieblingsbilder</h2><button class="btn small" id="favRefresh">↻</button>
      </div>
      <p class="hint">Am Display auf der Seite „Bilder“ merkt <b>BACK</b> das gezeigte Bild als Lieblingsbild (♥), nochmal BACK entfernt es.</p>
      <label class="check"><input type="checkbox" id="favOnly"> Diashow zeigt nur Lieblingsbilder</label>
      <div id="favs"></div>
    </div>
    <div class="card">
      <h2>Anzeige</h2>
      <div class="preview">
        <div style="min-width:280px">
          <label class="field" style="max-width:220px"><span>Bildwechsel alle … Sekunden</span><input type="number" id="slInterval" min="3" max="3600" step="1"></label>
          <label class="check"><input type="checkbox" id="slShuffle"> Zufällige Reihenfolge</label>
          <label class="check"><input type="checkbox" id="slRecursive"> Unteralben / Unterordner einbeziehen</label>
          <label class="check"><input type="checkbox" id="slCaption"> Bildtitel einblenden</label>
          <div class="field"><span class="muted" style="font-size:12.5px; font-weight:550; display:block; margin-bottom:4px">Darstellung</span>
            <div class="seg" id="slFit"><button data-fit="contain">Ganzes Bild</button><button data-fit="cover">Display füllen</button></div></div>
          <p class="hint" style="max-width:300px; margin-top:12px">Displaytasten auf der Seite „Bilder“: OK = Pause/Weiter, Hoch/Runter = Bild zurück/vor, MENU = Piwigo-Alben am Display auswählen.</p>
          <button class="btn" id="slTest">Testen</button> <span class="muted" id="slTestInfo"></span>
        </div>
        <div><img class="lcd" id="slPreview" alt="Vorschau der Diashow"></div>
      </div>
    </div>
  </section>

  <!-- ===================== Infoseiten ===================== -->
  <section class="tab" id="tab-info">
    <div class="card">
      <h2>Wetter</h2>
      <p class="hint">Daten von Open-Meteo (kostenlos, ohne Anmeldung), alle 15 Minuten aktualisiert.</p>
      <div class="row" style="margin-bottom:8px"><span class="muted">Ort:</span> <b id="wxName">–</b> <span class="muted" id="wxTest"></span></div>
      <form class="row" id="wxForm" style="flex-wrap:nowrap">
        <input type="text" id="wxQ" placeholder="Ort suchen, z. B. Leipzig oder 04109" style="flex:1">
        <button class="btn primary" type="submit">Suchen</button>
      </form>
      <div class="results georesults" id="wxResults"></div>
    </div>
    <div class="card">
      <h2>Termine</h2>
      <p class="hint">iCalendar-Adressen (<code>.ics</code>): bei Google „Geheime Adresse im iCal-Format“ (Kalendereinstellungen), bei <b>Nextcloud</b> reicht die Adresse der Nextcloud (z. B. <code>https://cloud.example.de</code>) plus Benutzername und <b>App-Passwort</b> (Persönliche Einstellungen → Sicherheit) – dann werden alle Terminkalender des Kontos in ihren Nextcloud-Farben angezeigt. Für einen einzelnen Kalender: im Kalender-Menü (⋯) „Interne Adresse kopieren“. Am Display blendet <b>MENU</b> auf der Terminseite einzelne Kalender ein und aus; Hoch/Runter markiert einen Termin, OK zeigt Ort und Beschreibung.</p>
      <div id="calSources"></div>
      <div class="row" style="margin-top:8px">
        <button class="btn" id="calAdd">+ Kalender hinzufügen</button>
        <label class="field" style="margin:0 0 0 auto">Erinnerung <select id="calRemind" style="width:auto">
          <option value="0">aus</option><option value="5">5 Min. vorher</option><option value="10">10 Min. vorher</option>
          <option value="15">15 Min. vorher</option><option value="30">30 Min. vorher</option><option value="60">1 Std. vorher</option></select></label>
        <label class="field" style="margin:0">Zeitraum <select id="calDays" style="width:auto">
          <option value="7">7 Tage</option><option value="14">14 Tage</option><option value="30">30 Tage</option><option value="60">60 Tage</option></select></label>
      </div>
    </div>
    <div class="card">
      <h2>Benachrichtigungen</h2>
      <p class="hint">KDE-Benachrichtigungen (E-Mail, Messenger, Updates …) erscheinen kurz auf dem Display.</p>
      <label class="check"><input type="checkbox" id="ntOn"> Benachrichtigungen auf dem Display anzeigen</label>
      <div class="row" style="margin-bottom:10px">
        <label class="field" style="margin:0">Anzeigedauer <input type="number" id="ntSec" min="2" max="30" style="width:70px"> Sekunden</label>
      </div>
      <label class="field"><span>Nicht anzeigen von (Programmnamen, durch Komma getrennt)</span><input type="text" id="ntIgnore" placeholder="z. B. Discover, Spectacle"></label>
      <button class="btn" id="ntTest">Testbenachrichtigung senden</button>
    </div>
    <div class="card">
      <h2>Nachrichten</h2>
      <p class="hint">RSS- oder Atom-Feeds für die Displayseite „Nachrichten“ (alle 15 Minuten aktualisiert). Am Display: Hoch/Runter markiert eine Meldung, OK öffnet sie im Browser, MENU lädt neu.</p>
      <div id="newsFeeds"></div>
      <div class="row" style="margin-top:8px">
        <button class="btn" id="newsAdd">+ Feed hinzufügen</button>
        <span class="muted">Schnell hinzufügen:</span><div class="row" id="newsPresets"></div>
      </div>
    </div>
    <div class="card">
      <h2>Unwetterwarnungen</h2>
      <p class="hint">Amtliche Warnungen des Deutschen Wetterdienstes für den oben gewählten Wetter-Ort (über den freien Dienst Bright Sky, alle 10 Minuten). Die Displayseite heißt „Unwetter“; OK zeigt die Details einer Warnung.</p>
      <label class="check"><input type="checkbox" id="warnPopup"> Neue markante Warnungen und Unwetter groß auf dem Display einblenden (auch wenn die Seite ausgeschaltet ist)</label>
      <button class="btn" id="warnTest">Jetzt prüfen</button> <span class="muted" id="warnInfo"></span>
    </div>
    <div class="card">
      <h2>Netzwerk</h2>
      <p class="hint">Geräte, deren Erreichbarkeit die Displayseite „Netzwerk“ jede Minute prüft. <code>gateway</code> = dein Router (automatisch erkannt); <code>Name:Port</code> prüft einen Dienst, z. B. <code>nas.local:5000</code>.</p>
      <div id="netHosts"></div>
      <div class="row" style="margin-top:8px">
        <button class="btn" id="netAdd">+ Gerät hinzufügen</button>
        <button class="btn" id="netPiwigo" style="display:none">+ Piwigo-Server</button>
        <button class="btn" id="netTest">Jetzt prüfen</button>
      </div>
      <div id="netInfo" style="margin-top:8px"></div>
    </div>
    <div class="card">
      <h2>Systemupdates</h2>
      <p class="hint">Die Displayseite „Updates“ zeigt stündlich, wie viele Paket- und Flatpak-Updates bereitstehen und ob ein Neustart nötig ist. Am Display öffnet OK die Aktualisierung (Discover), MENU prüft neu.</p>
      <label class="check"><input type="checkbox" id="updFlatpak"> Auch Flatpak-Programme prüfen</label>
      <button class="btn" id="updTest">Jetzt prüfen</button> <span class="muted" id="updInfo"></span>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between; margin-bottom:6px"><h2>Hardware</h2><button class="btn small" id="hwRefresh">↻ Aktualisieren</button></div>
      <p class="hint">Diese Werte zeigt die Seite „Hardware“ auf dem Display.</p>
      <div class="kv" id="hwInfo"></div>
    </div>
  </section>

  <!-- ===================== Dienst ===================== -->
  <section class="tab" id="tab-service">
    <div class="card">
      <h2>Treiber-Dienst</h2>
      <div class="kv" style="margin:10px 0 14px">
        <div>Status</div><div id="svcActive">…</div>
        <div>Autostart</div><div id="svcEnabled">…</div>
        <div>Radioplayer (mpv)</div><div id="toolMpv">…</div>
        <div>Musikanzeige (playerctl)</div><div id="toolPlayerctl">…</div>
        <div>Medientasten fürs Radio</div><div id="toolMpris">…</div>
      </div>
      <div class="row">
        <button class="btn" data-svc="start">▶ Starten</button>
        <button class="btn" data-svc="stop">■ Stoppen</button>
        <button class="btn" data-svc="restart">↻ Neu starten</button>
        <button class="btn" id="toggleAutostart">Autostart …</button>
      </div>
    </div>
    <div class="card">
      <div class="row" style="justify-content:space-between; margin-bottom:8px">
        <h2>Protokoll</h2><button class="btn small" id="logRefresh">↻ Aktualisieren</button>
      </div>
      <div class="log" id="log">…</div>
    </div>
    <div class="card">
      <h2>Programm aktualisieren</h2>
      <p class="hint">Neue Versionen von <code>g19s.py</code> und <code>g19s-gui.py</code> hier auswählen – einzeln oder beide zusammen, der Dateiname spielt keine Rolle (auch <code>g19s(3).py</code> ist in Ordnung). Die Dateien werden geprüft, die alten Versionen gesichert und alles neu gestartet.</p>
      <div class="kv" id="versions" style="margin-bottom:12px"></div>
      <label class="btn primary">⬆ Update-Dateien auswählen …<input type="file" id="updateFile" accept=".py" multiple hidden></label>
      <div id="updateResult" style="margin-top:10px"></div>
    </div>
    <div class="card">
      <h2>Sicherung</h2>
      <p class="hint">Sichert Tastenbelegung, Einstellungen, Treiber, Autostart und KDE-Kurzbefehle in eine Datei – für den Fall einer Neuinstallation.</p>
      <div class="row" style="margin-bottom:10px">
        <a class="btn primary" id="backupLink" download>⬇ Sicherung herunterladen</a>
        <label class="btn">⬆ Sicherung einspielen …<input type="file" id="restoreFile" accept=".gz,.tgz,application/gzip" hidden></label>
      </div>
      <div class="hint" id="backupFiles"></div>
    </div>
    <div class="card">
      <h2>Automatische Sicherung</h2>
      <p class="hint">Der Treiber legt regelmäßig eine Sicherung ab – in einem Ordner, auf dem NAS oder in der Nextcloud. Ältere automatische Sicherungen werden dort aufgeräumt. Sicherungen enthalten auch die gespeicherten Passwörter – nur an Orten ablegen, auf die sonst niemand Zugriff hat.</p>
      <label class="check"><input type="checkbox" id="abOn"> Automatisch sichern</label>
      <label class="field" style="max-width:420px"><span>Ziel</span>
        <select id="abTarget">
          <option value="folder">Ordner auf diesem Rechner (auch eingebundenes NAS, Nextcloud-Sync-Ordner)</option>
          <option value="nextcloud">Nextcloud (direkt über das Internet)</option>
          <option value="smb">NAS – Windows-Freigabe (SMB)</option>
          <option value="webdav">WebDAV-Server (z. B. NAS mit WebDAV-Dienst)</option>
        </select></label>
      <div id="abFolderBox">
        <div class="row" style="flex-wrap:nowrap; margin-bottom:8px">
          <input type="text" id="abFolder" placeholder="~/Nextcloud/Sicherungen" style="flex:1">
          <button class="btn" id="abBrowse">Durchsuchen …</button>
        </div>
        <div id="abBrowser"></div>
      </div>
      <div id="abRemoteBox">
        <label class="field"><span id="abUrlLabel">Adresse</span><input type="text" id="abUrl"></label>
        <div class="row" style="margin-bottom:8px">
          <label class="field" style="margin:0; flex:1"><span>Benutzername</span><input type="text" id="abUser" autocomplete="off"></label>
          <label class="field" style="margin:0; flex:1"><span id="abPwLabel">Passwort</span><input type="password" id="abPw" autocomplete="new-password"></label>
        </div>
        <label class="field" id="abDirBox"><span>Ordner in der Nextcloud (wird angelegt)</span><input type="text" id="abDir" placeholder="G19s-Sicherung"></label>
      </div>
      <p class="hint" id="abHint"></p>
      <div class="row" style="margin-bottom:8px">
        <label class="field" style="margin:0">alle <select id="abDays" style="width:auto"><option value="1">1 Tag</option><option value="3">3 Tage</option><option value="7">7 Tage</option><option value="14">14 Tage</option><option value="30">30 Tage</option></select></label>
        <label class="field" style="margin:0">aufheben: <input type="number" id="abKeep" min="1" max="100" style="width:70px"> Sicherungen</label>
        <button class="btn" id="abTest">Verbindung testen</button>
        <button class="btn" id="abNow">Jetzt sichern</button>
      </div>
      <div class="hint" id="abStatus"></div>
    </div>
    <div class="card">
      <h2>Dateien</h2>
      <div class="kv" id="paths"></div>
    </div>
  </section>
</main>

<div class="savebar" id="savebar"><div class="row">
  <span class="muted" id="saveText" style="flex:1">Ungespeicherte Änderungen</span>
  <button class="btn" id="discardSettings">Verwerfen</button>
  <button class="btn primary" id="saveSettings">Änderungen speichern</button>
</div></div>
<div class="toasts" id="toasts"></div>
<div class="overlay" id="overlay"><div class="card"><h2 id="ovTitle">Verbindung verloren</h2>
  <p class="hint" id="ovText">Die Verwaltung wurde beendet. Bitte über das Anwendungsmenü „G19s-Verwaltung“ neu öffnen.</p></div></div>

<script>
"use strict";
const TOKEN = location.hash.slice(1);
const GKEYS = Array.from({length: 12}, (_, i) => "G" + (i + 1));
const PROFILES = ["M1", "M2", "M3"];
const TYPES = [
  {id: "default", label: "KDE-Kurzbefehl", icon: "⌨"},
  {id: "text", label: "Text tippen", icon: "✎"},
  {id: "combo", label: "Tastenkombination", icon: "⌘"},
  {id: "steps", label: "Makro", icon: "⏺"},
  {id: "open", label: "Webseite", icon: "🌐"},
  {id: "run", label: "Programm", icon: "▶"},
  {id: "radio", label: "Radiosender", icon: "📻"},
  {id: "media", label: "Musiksteuerung", icon: "♫"},
  {id: "volume", label: "Lautstärke", icon: "🔊"},
  {id: "snippets", label: "Textbausteine", icon: "☰"},
  {id: "timer", label: "Timer", icon: "⏱"},
  {id: "sleep", label: "Einschlaftimer", icon: "☾"},
  {id: "mic", label: "Mikrofon stumm", icon: "🎙"},
];
const TYPE_BY_ID = Object.fromEntries(TYPES.map(t => [t.id, t]));
// KeyboardEvent.code -> evdev-Name (Position auf der Tastatur, unabhängig vom Layout)
const CODE_MAP = (() => {
  const m = {Enter: "KEY_ENTER", Space: "KEY_SPACE", Tab: "KEY_TAB", Backspace: "KEY_BACKSPACE",
    Escape: "KEY_ESC", Delete: "KEY_DELETE", Insert: "KEY_INSERT", Home: "KEY_HOME", End: "KEY_END",
    PageUp: "KEY_PAGEUP", PageDown: "KEY_PAGEDOWN", ArrowUp: "KEY_UP", ArrowDown: "KEY_DOWN",
    ArrowLeft: "KEY_LEFT", ArrowRight: "KEY_RIGHT", ShiftLeft: "KEY_LEFTSHIFT", ShiftRight: "KEY_RIGHTSHIFT",
    ControlLeft: "KEY_LEFTCTRL", ControlRight: "KEY_RIGHTCTRL", AltLeft: "KEY_LEFTALT", AltRight: "KEY_RIGHTALT",
    MetaLeft: "KEY_LEFTMETA", MetaRight: "KEY_RIGHTMETA", OSLeft: "KEY_LEFTMETA", OSRight: "KEY_RIGHTMETA",
    ContextMenu: "KEY_COMPOSE", CapsLock: "KEY_CAPSLOCK", Minus: "KEY_MINUS", Equal: "KEY_EQUAL",
    BracketLeft: "KEY_LEFTBRACE", BracketRight: "KEY_RIGHTBRACE", Backslash: "KEY_BACKSLASH",
    Semicolon: "KEY_SEMICOLON", Quote: "KEY_APOSTROPHE", Backquote: "KEY_GRAVE", Comma: "KEY_COMMA",
    Period: "KEY_DOT", Slash: "KEY_SLASH", IntlBackslash: "KEY_102ND", NumpadAdd: "KEY_KPPLUS",
    NumpadSubtract: "KEY_KPMINUS", NumpadMultiply: "KEY_KPASTERISK", NumpadDivide: "KEY_KPSLASH",
    NumpadDecimal: "KEY_KPDOT", NumpadEnter: "KEY_KPENTER", NumLock: "KEY_NUMLOCK", ScrollLock: "KEY_SCROLLLOCK",
    Pause: "KEY_PAUSE", PrintScreen: "KEY_SYSRQ", AudioVolumeMute: "KEY_MUTE", AudioVolumeUp: "KEY_VOLUMEUP",
    AudioVolumeDown: "KEY_VOLUMEDOWN", MediaPlayPause: "KEY_PLAYPAUSE", MediaTrackNext: "KEY_NEXTSONG",
    MediaTrackPrevious: "KEY_PREVIOUSSONG", MediaStop: "KEY_STOPCD"};
  for (const c of "ABCDEFGHIJKLMNOPQRSTUVWXYZ") m["Key" + c] = "KEY_" + c;
  for (let i = 0; i < 10; i++) { m["Digit" + i] = "KEY_" + i; m["Numpad" + i] = "KEY_KP" + i; }
  for (let i = 1; i <= 24; i++) m["F" + i] = "KEY_F" + i;
  return m;
})();

const S = {macros: {}, settings: null, keys: [], keyLabel: {}, chars: new Set(), media: {}, pages: [],
  mtimes: {}, service: {}, tools: {}, paths: {}};
const UI = {tab: "keys", profile: "M1", gkey: "G1", draft: null, draftDirty: false,
  sdraft: null, sDirty: false, recording: null, pvPage: 3, pvProfile: "M1", testing: null};

// ---------------------------------------------------------------- Hilfen
const $ = (s, r = document) => r.querySelector(s);
function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  let value;
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "value") value = v;          // erst nach den Kindern setzen (select, textarea)
    else if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e && typeof v !== "string") e[k] = v;
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false)
    e.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  if (value !== undefined) e.value = value;
  return e;
}
const clone = o => JSON.parse(JSON.stringify(o));
const hex = rgb => "#" + rgb.map(c => c.toString(16).padStart(2, "0")).join("");
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
// Profile: S.macros = {profiles: [{name, colors, keys: {M1: {...}, M2: {...}, M3: {...}}}]}
const P = (i = UI.pidx) => S.macros.profiles[i];
const layerKeys = () => (P().keys || {})[UI.profile] || {};
function profColors(i = UI.pidx) {
  const p = S.macros.profiles[i];
  return (p && p.colors) || ((UI.sdraft || S.settings) || {}).colors || {M1: [0, 110, 255], M2: [0, 255, 90], M3: [255, 70, 0]};
}
function profileColor(layer) { return hex(profColors()[layer] || [80, 120, 200]); }
function toast(msg, err = false) {
  const t = el("div", {class: "toast" + (err ? " err" : ""), text: msg});
  const box = $("#toasts");
  box.append(t);
  while (box.children.length > 3) box.firstChild.remove();
  setTimeout(() => t.remove(), err ? 7000 : 3500);
}
async function api(path, opts = {}) {
  const o = {method: opts.method || (opts.body !== undefined ? "POST" : "GET"),
    headers: {"X-Token": TOKEN}, keepalive: !!opts.keepalive};
  if (opts.body !== undefined) {
    if (opts.raw) o.body = opts.body;
    else { o.body = JSON.stringify(opts.body); o.headers["Content-Type"] = "application/json"; }
  }
  let r;
  try { r = await fetch(path, o); }
  catch (e) { lost("Verbindung verloren", "Die Verwaltung läuft nicht mehr. Bitte über das Anwendungsmenü „G19s-Verwaltung“ neu öffnen."); throw e; }
  const data = await r.json().catch(() => ({}));
  if (r.status === 401) { lost("Sitzung ungültig", data.error || ""); throw new Error(data.error); }
  if (!r.ok) throw new Error(data.error || ("Fehler " + r.status));
  return data;
}
function lost(title, text) { $("#ovTitle").textContent = title; $("#ovText").textContent = text; $("#overlay").classList.add("show"); }
const keyLabel = name => S.keyLabel[name] || String(name).replace(/^KEY_/, "");
function fKeyText(gkey, p) {
  const f = "F" + (12 + parseInt(gkey.slice(1)));
  return {M1: f, M2: "Strg+" + f, M3: "Alt+" + f}[p];
}
function domainOf(u) { return String(u).replace(/^[a-z]+:\/\/(www\.)?/i, "").split("/")[0]; }
function stationName(url) {
  const s = ((UI.sdraft || S.settings).stations || []).find(x => x.url === url);
  return s ? (s.name || domainOf(url)) : domainOf(url);
}
function typeOf(e) {
  if (!e) return "default";
  for (const t of ["radio", "media", "volume", "snippets", "timer", "sleep", "mic", "open", "run", "text", "combo", "steps"]) {
    const v = e[t]; if (v && (!Array.isArray(v) || v.length)) return t;
  }
  return "default";
}
function timerLabel(t) {
  t = t || {};
  if (t.mode === "stopwatch") return "Stoppuhr";
  if (t.mode === "pomodoro") return `Pomodoro ${t.work || 25}/${t.break || 5}`;
  return `Timer ${t.minutes || 5} min`;
}
function snippetGroups() {
  const sd = UI.sdraft || S.settings;
  return [...new Set(sd.snippets.map(x => (x.group || "").trim()).filter(Boolean))].sort();
}
function comboList(c) { return Array.isArray(c) ? c : String(c || "").split("+").map(s => s.trim()).filter(Boolean); }
function entryLabel(e) {
  if (!e) return "";
  if (e.name) return e.name;
  const t = typeOf(e);
  if (t === "open") return domainOf(e.open);
  if (t === "radio") return e.radio === "stop" ? "Radio aus" : stationName(e.radio);
  if (t === "media") return S.media[e.media] || "Musik";
  if (t === "volume") return S.volume[e.volume] || "Lautstärke";
  if (t === "snippets") return e.snippets === "*" ? "Textbausteine" : String(e.snippets);
  if (t === "timer") return timerLabel(e.timer);
  if (t === "sleep") return `Einschlafen ${e.sleep} min`;
  if (t === "mic") return "Mikrofon";
  if (t === "run") return String(e.run).split(/\s+/)[0];
  if (t === "text") return "Text";
  if (t === "combo") return comboList(e.combo).map(keyLabel).join("+");
  if (t === "steps") return "Makro";
  return "";
}

// ---------------------------------------------------------------- Laden
async function loadState() {
  const d = await api("/api/state");
  S.macros = d.macros; S.settings = d.settings; S.keys = d.keys; S.media = d.media; S.pages = d.pages; S.pageIds = d.page_ids; S.volume = d.volume;
  S.clockFaces = d.clock_faces; S.clockOptions = d.clock_options; S.worldCities = d.world_cities;
  S.active = d.active; S.maxProfiles = d.max_profiles;
  if (UI.pidx === undefined) UI.pidx = d.active;
  UI.pidx = Math.min(UI.pidx, S.macros.profiles.length - 1);
  S.keyLabel = Object.fromEntries(d.keys.map(k => [k.name, k.label]));
  S.chars = new Set([...d.chars, ...d.dead]); S.mtimes = d.mtimes; S.service = d.service;
  S.tools = d.tools; S.paths = d.paths;
  if (d.macros_error) toast(d.macros_error, true);
  UI.sdraft = clone(S.settings); UI.sDirty = false;
  selectKey(UI.gkey, true);
  renderAll();
}
function renderAll() {
  renderProfiles(); renderKeypad(); renderEditor(); renderStations(); renderAlarmClock(); renderSnippets(); renderSettings(); renderSlides(); renderInfo();
  renderAutoBackup(); renderFavs();
  renderServiceInfo(); renderSavebar(); renderPaths();
}

// ---------------------------------------------------------------- Reiter
$("#nav").addEventListener("click", e => {
  const b = e.target.closest("button[data-tab]"); if (!b) return;
  UI.tab = b.dataset.tab;
  document.querySelectorAll("#nav button").forEach(x => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.id === "tab-" + UI.tab));
  if (UI.tab === "service") { refreshService(); loadBackupStatus(); }
  if (UI.tab === "radio") loadSongs();
  if (UI.tab === "slides") loadFavs();
  if (UI.tab === "settings") { refreshPreview(); clockPreview(); }
  if (UI.tab === "info") refreshHardware();
  if (UI.tab === "slides" && !UI.albums && slCfg().url && slCfg().source !== "folder") loadAlbums(true);
  renderSavebar();
});
function markTabs() {
  const n = id => $(`#nav button[data-tab=${id}]`);
  n("keys").classList.toggle("dirty", UI.draftDirty);
  n("radio").classList.toggle("dirty", UI.sDirty);
  n("snippets").classList.toggle("dirty", UI.sDirty);
  n("settings").classList.toggle("dirty", UI.sDirty);
  n("slides").classList.toggle("dirty", UI.sDirty);
  n("info").classList.toggle("dirty", UI.sDirty);
}

// ---------------------------------------------------------------- Tasten: Profile & Tastenfeld
function renderProfiles() {
  renderProfileCard();
  const box = $("#profiles"); box.replaceChildren();
  for (const p of PROFILES) box.append(el("button", {class: p === UI.profile ? "active" : "",
    onclick: () => { if (confirmLeave()) { UI.profile = p; selectKey(UI.gkey, true); renderProfiles(); renderKeypad(); renderEditor(); } }},
    el("span", {class: "swatch", style: {background: profileColor(p)}}), p));
}
function renderProfileCard() {
  const list = S.macros.profiles, n = list.length;
  $("#profSel").replaceChildren(...list.map((p, i) => el("option", {value: i, selected: i === UI.pidx,
    text: `${i + 1}. ${p.name}${i === S.active ? "   ✓ aktiv" : ""}`})));
  $("#profUp").disabled = UI.pidx === 0; $("#profDown").disabled = UI.pidx === n - 1;
  $("#profDel").disabled = n <= 1; $("#profNew").disabled = $("#profCopy").disabled = n >= S.maxProfiles;
  const cols = profColors();
  $("#profColors").replaceChildren(...PROFILES.map(layer => el("label", {title: "Beleuchtungsfarbe für " + layer},
    el("input", {type: "color", value: hex(cols[layer]), onchange: e => setProfileColor(layer, e.target.value)}), layer)));
  $("#profActive").replaceChildren(UI.pidx === S.active
    ? el("span", {class: "activebadge"}, el("span", {class: "dot ok"}), "An der Tastatur aktiv")
    : el("button", {class: "btn small primary", onclick: activateProfile}, "An der Tastatur aktivieren"));
}
function renderKeypad() {
  const box = $("#keypad"); box.replaceChildren();
  const prof = layerKeys();
  for (const k of GKEYS) {
    const e = prof[k], t = typeOf(e), label = entryLabel(e);
    const b = el("button", {class: "gkey" + (k === UI.gkey ? " sel" : "") + (e ? " has" : ""),
      style: {"--pc": profileColor(UI.profile)}, title: TYPE_BY_ID[t].label,
      onclick: () => { if (k !== UI.gkey && confirmLeave()) { selectKey(k, true); renderKeypad(); renderEditor(); } }},
      el("span", {class: "gnum", text: k}),
      el("span", {class: "gic", text: e ? TYPE_BY_ID[t].icon : ""}),
      el("span", {class: "glabel", text: label || fKeyText(k, UI.profile)}),
      el("span", {class: "bar"}));
    box.append(b);
  }
}
function confirmLeave() {
  if (!UI.draftDirty) return true;
  if (confirm("Die Änderungen an " + UI.gkey + " wurden noch nicht übernommen. Verwerfen?")) { UI.draftDirty = false; markTabs(); return true; }
  return false;
}
function selectKey(k, reset) {
  stopRecording(false);
  UI.gkey = k;
  if (reset) {
    const e = layerKeys()[k];
    UI.draft = {name: (e && e.name) || "", type: typeOf(e), text: (e && e.text) || "",
      combo: comboList(e && e.combo), steps: clone((e && e.steps) || []), open: (e && e.open) || "",
      run: (e && e.run) || "", radio: (e && e.radio) || "", media: (e && e.media) || "play-pause",
      volume: (e && e.volume) || "up", snippets: (e && e.snippets) || "*",
      timer: Object.assign({mode: "timer", minutes: 5, work: 25, break: 5}, (e && e.timer) || {}),
      sleep: (e && e.sleep) || 30};
    UI.draftDirty = false; markTabs();
  }
}
function touchDraft() { UI.draftDirty = true; markTabs(); updateApplyState(); }

// ---------------------------------------------------------------- Tasten: Editor
function renderEditor() {
  const d = UI.draft, box = $("#editor"); box.replaceChildren();
  if (!d) return;
  box.append(el("div", {class: "edhead"},
    el("h2", {text: `${UI.gkey} · ${P().name} · ${UI.profile}`}),
    el("span", {class: "swatch", style: {background: profileColor(UI.profile)}})));
  const types = el("div", {class: "types"});
  for (const t of TYPES) types.append(el("button", {class: d.type === t.id ? "active" : "",
    onclick: () => { stopRecording(false); d.type = t.id; touchDraft(); renderEditor(); }},
    el("span", {class: "ti", text: t.icon}), t.label));
  box.append(types);
  box.append(el("label", {class: "field"}, el("span", {text: "Name auf dem Display (optional)"}),
    el("input", {type: "text", value: d.name, maxlength: 40, placeholder: autoName(d) || "z. B. Firefox",
      oninput: e => { d.name = e.target.value; touchDraft(); }})));
  const body = el("div");
  ({default: edDefault, text: edText, combo: edCombo, steps: edSteps, open: edOpen, run: edRun,
    radio: edRadio, media: edMedia, volume: edVolume, snippets: edSnippets, timer: edTimer, sleep: edSleep, mic: edMic})[d.type](body, d);
  box.append(body);
  const exists = !!layerKeys()[UI.gkey];
  box.append(el("div", {class: "actions"},
    el("button", {class: "btn primary", id: "applyBtn", onclick: applyDraft}, "Übernehmen"),
    el("button", {class: "btn", id: "revertBtn", onclick: () => { selectKey(UI.gkey, true); renderEditor(); }}, "Verwerfen"),
    el("div", {class: "spacer"}),
    exists ? el("button", {class: "btn danger", onclick: clearKey}, "Belegung entfernen") : null));
  updateApplyState();
}
function updateApplyState() {
  const a = $("#applyBtn"), r = $("#revertBtn");
  if (a) a.disabled = !UI.draftDirty; if (r) r.disabled = !UI.draftDirty;
}
function autoName(d) { const e = draftToEntry(Object.assign({}, d, {name: ""})); return e ? entryLabel(e) : ""; }

function edDefault(box) {
  box.append(el("div", {class: "note"}, "Diese Taste sendet ", el("b", {text: fKeyText(UI.gkey, UI.profile)}),
    ". Belege sie in den ", el("b", {text: "KDE-Systemeinstellungen → Tastatur → Kurzbefehle"}),
    " oder direkt in einem Programm (Spiele, OBS …). Ein Name hier erscheint nur als Beschriftung auf dem Display."));
}
function edText(box, d) {
  const warn = el("div");
  const check = () => {
    const bad = [...new Set([...d.text].filter(c => !S.chars.has(c) && c !== "\r"))];
    warn.replaceChildren(bad.length ? el("div", {class: "warnbox"}, "Diese Zeichen können nicht getippt werden und werden übersprungen: ",
      el("b", {text: bad.join(" ")})) : "");
  };
  box.append(el("label", {class: "field"}, el("span", {text: "Text, der getippt wird (Zeilenumbruch = Enter)"}),
    el("textarea", {value: d.text, placeholder: "z. B. Mit freundlichen Grüßen\nMax Mustermann",
      oninput: e => { d.text = e.target.value; touchDraft(); check(); }})), warn,
    el("p", {class: "hint", text: "Umlaute, ß, @, € und Sonderzeichen werden für das deutsche Tastaturlayout umgesetzt."}));
  check();
}
function edCombo(box, d) {
  const chips = el("div", {class: "chips"});
  const draw = () => {
    chips.replaceChildren();
    d.combo.forEach((k, i) => {
      if (i) chips.append(el("span", {class: "plus", text: "+"}));
      chips.append(el("span", {class: "chip"}, keyLabel(k),
        el("button", {title: "entfernen", onclick: () => { d.combo.splice(i, 1); touchDraft(); draw(); }}, "×")));
    });
    if (!d.combo.length) chips.append(el("span", {class: "muted", text: "noch keine Taste"}));
  };
  draw();
  const cap = el("div", {class: "capture", id: "capture"}, "Klicke auf „Kombination aufnehmen“ und drücke die Tasten gleichzeitig, z. B. Strg+Umschalt+T.");
  const recBtn = el("button", {class: "btn", onclick: () => {
    if (UI.recording) { stopRecording(true); return; }
    startRecording("combo", cap, recBtn, keys => { d.combo = keys; touchDraft(); draw(); });
  }}, "⏺ Kombination aufnehmen");
  box.append(el("label", {class: "field"}, el("span", {text: "Tastenkombination"}), chips),
    el("div", {class: "row"}, recBtn, keySelect("", k => { if (k && !d.combo.includes(k)) { d.combo.push(k); touchDraft(); draw(); } }, "+ Taste hinzufügen …")),
    cap);
}
function edSteps(box, d) {
  const tbody = el("tbody");
  const count = el("span", {class: "muted"});
  const draw = () => {
    tbody.replaceChildren();
    d.steps.forEach((s, i) => {
      tbody.append(el("tr", {},
        el("td", {class: "n", text: i + 1}),
        el("td", {}, el("input", {type: "number", min: 0, max: 5000, step: 10, value: s[0],
          oninput: e => { s[0] = Math.max(0, Math.min(5000, parseInt(e.target.value) || 0)); touchDraft(); }})),
        el("td", {}, keySelect(s[1], k => { s[1] = k; touchDraft(); })),
        el("td", {}, actionSelect(s[2], a => { s[2] = a; touchDraft(); })),
        el("td", {style: {whiteSpace: "nowrap"}},
          el("button", {class: "btn icon small", title: "nach oben", disabled: i === 0,
            onclick: () => { [d.steps[i - 1], d.steps[i]] = [d.steps[i], d.steps[i - 1]]; touchDraft(); draw(); }}, "↑"),
          el("button", {class: "btn icon small", title: "nach unten", disabled: i === d.steps.length - 1,
            onclick: () => { [d.steps[i + 1], d.steps[i]] = [d.steps[i], d.steps[i + 1]]; touchDraft(); draw(); }}, "↓"),
          el("button", {class: "btn icon small danger", title: "löschen",
            onclick: () => { d.steps.splice(i, 1); touchDraft(); draw(); }}, "✕"))));
    });
    if (!d.steps.length) tbody.append(el("tr", {}, el("td", {colspan: 5, class: "empty", text: "Noch keine Schritte – aufnehmen oder hinzufügen."})));
    const downs = d.steps.filter(s => s[2] !== "up").length;
    const total = d.steps.reduce((a, s) => a + (s[0] || 0), 0);
    count.textContent = `${d.steps.length} Schritte · ${downs} Tastendrücke · Dauer ca. ${(total / 1000).toFixed(1)} s`;
  };
  const cap = el("div", {class: "capture", id: "capture"}, "„Aufnehmen“ klicken, Tasten drücken, dann „Aufnahme beenden“ klicken. Pausen werden mit aufgezeichnet.");
  const recBtn = el("button", {class: "btn", onclick: () => {
    if (UI.recording) { stopRecording(true); return; }
    startRecording("steps", cap, recBtn, steps => { d.steps = d.steps.concat(steps); touchDraft(); draw(); });
  }}, "⏺ Aufnehmen");
  const pause = el("input", {type: "number", value: 30, min: 0, max: 5000, step: 10, title: "Pause in ms"});
  box.append(
    el("div", {class: "tools"}, recBtn,
      el("button", {class: "btn", onclick: () => { d.steps.push([50, "KEY_A", "tap"]); touchDraft(); draw(); }}, "+ Schritt"),
      el("span", {class: "muted", style: {marginLeft: "8px"}, text: "Alle Pausen auf"}), pause,
      el("span", {class: "muted", text: "ms"}),
      el("button", {class: "btn small", onclick: () => { const v = Math.max(0, parseInt(pause.value) || 0);
        d.steps.forEach((s, i) => s[0] = i === 0 ? 0 : v); touchDraft(); draw(); }}, "angleichen"),
      el("button", {class: "btn small", title: "Drücken+Loslassen derselben Taste zu einem Tipp zusammenfassen",
        onclick: () => { d.steps = compactSteps(d.steps); touchDraft(); draw(); }}, "vereinfachen"),
      el("button", {class: "btn small danger", onclick: () => { if (confirm("Alle Schritte löschen?")) { d.steps = []; touchDraft(); draw(); } }}, "alle löschen")),
    cap,
    el("div", {class: "stepsbox"}, el("table", {class: "steps"},
      el("thead", {}, el("tr", {}, el("th", {}, "#"), el("th", {}, "Pause (ms)"), el("th", {}, "Taste"), el("th", {}, "Aktion"), el("th", {}))),
      tbody)),
    el("p", {class: "hint", style: {marginTop: "8px"}}, count,
      el("br"), "„Tippen“ = kurz drücken. Für gehaltene Tasten (z. B. Umschalt) „drücken“ und später „loslassen“ verwenden."));
  draw();
}
function compactSteps(steps) {
  const out = [];
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i], n = steps[i + 1];
    if (s[2] === "down" && n && n[2] === "up" && n[1] === s[1]) { out.push([s[0], s[1], "tap"]); i++; }
    else out.push(s.slice());
  }
  return out;
}
function edOpen(box, d) {
  const inp = el("input", {type: "url", value: d.open, placeholder: "https://www.example.de",
    oninput: e => { d.open = e.target.value.trim(); touchDraft(); }});
  box.append(el("label", {class: "field"}, el("span", {text: "Adresse der Webseite"}), inp),
    el("div", {class: "row"}, el("button", {class: "btn", onclick: () => {
      let u = inp.value.trim(); if (!u) return;
      if (!/^[a-z]+:\/\//i.test(u)) { u = "https://" + u; inp.value = u; d.open = u; touchDraft(); }
      window.open(u, "_blank", "noopener");
    }}, "Testen")),
    el("p", {class: "hint", style: {marginTop: "10px"}, text: "Öffnet sich im Standardbrowser."}));
}
function edRun(box, d) {
  const inp = el("input", {type: "text", value: d.run, placeholder: "z. B. konsole",
    oninput: e => { d.run = e.target.value; touchDraft(); }});
  const ex = [["Terminal", "konsole"], ["Dateimanager", "dolphin"], ["Bildschirmfoto", "spectacle"],
    ["Rechner", "kcalc"], ["Stumm schalten", "pactl set-sink-mute @DEFAULT_SINK@ toggle"],
    ["Bildschirm sperren", "loginctl lock-session"], ["Firefox privat", "firefox --private-window"]];
  box.append(el("label", {class: "field"}, el("span", {text: "Befehl"}), inp),
    el("div", {class: "hint", text: "Beispiele (anklicken zum Übernehmen):"}),
    el("div", {class: "row"}, ex.map(([n, c]) => el("button", {class: "btn small", title: c,
      onclick: () => { inp.value = c; d.run = c; if (!d.name) d.name = n; touchDraft(); renderEditor(); }}, n))));
}
function edRadio(box, d) {
  const st = (UI.sdraft || S.settings).stations || [];
  if (!st.length) {
    box.append(el("div", {class: "note"}, "Noch keine Radiosender angelegt. Lege sie im Reiter ", el("b", {text: "Radiosender"}), " an."));
  }
  const sel = el("select", {onchange: e => { d.radio = e.target.value; touchDraft(); }},
    el("option", {value: "", text: "– Sender wählen –"}),
    st.map(s => el("option", {value: s.url, text: s.name || s.url, selected: s.url === d.radio})),
    el("option", {value: "stop", text: "■ Radio ausschalten", selected: d.radio === "stop"}));
  if (d.radio && d.radio !== "stop" && !st.some(s => s.url === d.radio))
    sel.append(el("option", {value: d.radio, text: domainOf(d.radio) + " (nicht in der Liste)", selected: true}));
  box.append(el("label", {class: "field"}, el("span", {text: "Radiosender"}), sel),
    el("p", {class: "hint", text: "Drücken startet den Sender, nochmal drücken schaltet ihn aus. Der aktuelle Song erscheint auf der Musikseite des Displays."}));
  if (!S.tools.mpv) box.append(el("div", {class: "warnbox"}, "Für Radiosender wird ", el("b", {text: "mpv"}), " benötigt: ", el("code", {text: "sudo apt install mpv"})));
}
function edMedia(box, d) {
  box.append(el("label", {class: "field"}, el("span", {text: "Aktion"}),
    el("select", {onchange: e => { d.media = e.target.value; touchDraft(); }},
      Object.entries(S.media).map(([k, v]) => el("option", {value: k, text: v, selected: d.media === k})))),
    el("p", {class: "hint", text: "Steuert den gerade laufenden Player (Elisa, Spotify, VLC, Browser …) bzw. das eigene Radio."}));
}
function edVolume(box, d) {
  box.append(el("label", {class: "field"}, el("span", {text: "Aktion"}),
    el("select", {onchange: e => { d.volume = e.target.value; touchDraft(); }},
      Object.entries(S.volume).map(([k, v]) => el("option", {value: k, text: v, selected: d.volume === k})))),
    el("p", {class: "hint", text: `Ändert die Systemlautstärke um ${(UI.sdraft || S.settings).volume_step || 5} % und zeigt sie kurz groß auf dem Display. Die Schrittweite stellst du unter „Beleuchtung & Display“ ein.`}));
}
function edSnippets(box, d) {
  const groups = snippetGroups(), n = ((UI.sdraft || S.settings).snippets || []).length;
  box.append(el("label", {class: "field"}, el("span", {text: "Welche Textbausteine?"}),
    el("select", {onchange: e => { d.snippets = e.target.value; touchDraft(); }},
      el("option", {value: "*", text: `Alle (${n})`, selected: d.snippets === "*"}),
      ...groups.map(g => el("option", {value: g, text: "Gruppe: " + g, selected: d.snippets === g})))),
    el("p", {class: "hint", text: "Ein Druck auf die G-Taste zeigt die Liste auf dem Display: Hoch/Runter wählen, OK tippt den Text ins aktive Fenster, BACK oder die G-Taste schließen die Liste. Die Texte legst du im Reiter „Textbausteine“ an."}));
  if (!n) box.append(el("div", {class: "warnbox"}, "Es gibt noch keine Textbausteine – im Reiter „Textbausteine“ anlegen."));
}
function edSleep(box, d) {
  box.append(el("label", {class: "field", style: {maxWidth: "220px"}}, el("span", {text: "Musik ausschalten nach … Minuten"}),
    el("input", {type: "number", min: 1, max: 240, value: d.sleep, oninput: e => {
      d.sleep = Math.max(1, Math.min(240, parseInt(e.target.value) || 30)); touchDraft(); }})),
    el("p", {class: "hint", text: "Startet den Einschlaftimer (läuft nichts, startet der zuletzt gehörte bzw. erste Radiosender). Nach Ablauf wird das Radio bzw. der Player ausgeschaltet. Die restlichen Minuten stehen mit Mondsymbol in der Fußzeile. Nochmal drücken = abbrechen."}));
}
function edMic(box, d) {
  box.append(el("p", {class: "hint", text: "Schaltet das Mikrofon (Standard-Eingang) stumm bzw. wieder an – praktisch für Videokonferenzen. Solange es stumm ist, leuchtet die MR-Taste und die Fußzeile zeigt ein rotes Mikrofon. Das funktioniert auch, wenn das Mikrofon in KDE oder in einem Programm stummgeschaltet wurde."}));
}
function edTimer(box, d) {
  const t = d.timer;
  const num = (key, label, min, max) => el("label", {class: "field", style: {maxWidth: "200px"}}, el("span", {text: label}),
    el("input", {type: "number", min, max, value: t[key], oninput: e => {
      t[key] = Math.max(min, Math.min(max, parseInt(e.target.value) || min)); touchDraft(); }}));
  box.append(el("div", {class: "seg", style: {marginBottom: "12px"}},
    ...[["timer", "Countdown"], ["stopwatch", "Stoppuhr"], ["pomodoro", "Pomodoro"]].map(([m, l]) =>
      el("button", {class: t.mode === m ? "active" : "", text: l, onclick: () => { t.mode = m; touchDraft(); renderEditor(); }}))));
  if (t.mode === "timer") box.append(num("minutes", "Minuten", 1, 600));
  if (t.mode === "pomodoro") box.append(el("div", {class: "row"}, num("work", "Arbeiten (Minuten)", 1, 180), num("break", "Pause (Minuten)", 1, 60)));
  box.append(el("p", {class: "hint", text: {
    timer: "Startet den Countdown und zeigt ihn groß auf dem Display. Am Ende: Signalton, Beleuchtung blinkt, Displaytaste bestätigt. Während der Anzeige: OK = Pause, Hoch = +1 Minute, Runter = beenden, BACK = zurück (der Timer läuft in der Fußzeile weiter).",
    stopwatch: "Startet die Stoppuhr. OK = Start/Stopp, Runter = auf 0, BACK = zurück (läuft in der Fußzeile weiter).",
    pomodoro: "Wechselt automatisch zwischen Arbeits- und Pausenphase und zählt die Runden. Bei jedem Wechsel: Signalton und kurze Einblendung. Runter = beenden."}[t.mode]}),
    el("p", {class: "hint", text: "Ein zweiter Druck auf dieselbe G-Taste hält an bzw. zeigt den Timer wieder an."}));
}
function keySelect(value, onchange, placeholder) {
  const sel = el("select", {onchange: e => { onchange(e.target.value); if (placeholder) e.target.value = ""; }});
  if (placeholder) sel.append(el("option", {value: "", text: placeholder}));
  const groups = {};
  for (const k of S.keys) (groups[k.group] = groups[k.group] || []).push(k);
  if (value && !S.keyLabel[value]) sel.append(el("option", {value, text: value, selected: true}));
  for (const [g, ks] of Object.entries(groups))
    sel.append(el("optgroup", {label: g}, ks.map(k => el("option", {value: k.name, text: k.label, selected: k.name === value}))));
  if (!placeholder) sel.style.minWidth = "150px";
  return sel;
}
function actionSelect(value, onchange) {
  return el("select", {onchange: e => onchange(e.target.value)},
    [["tap", "tippen"], ["down", "drücken"], ["up", "loslassen"]].map(([v, t]) => el("option", {value: v, text: t, selected: v === value})));
}

// ---------------------------------------------------------------- Aufnahme im Fenster
function startRecording(mode, capEl, btn, done) {
  const rec = {mode, capEl, btn, done, steps: [], combo: [], held: new Set(), last: null, unknown: 0};
  UI.recording = rec;
  capEl.classList.add("on");
  capEl.textContent = mode === "combo" ? "● Jetzt die Kombination drücken …" : "● Aufnahme läuft – Tasten drücken …";
  btn.classList.add("rec"); btn.textContent = mode === "combo" ? "■ Abbrechen" : "■ Aufnahme beenden";
  document.activeElement && document.activeElement.blur();
}
function stopRecording(apply) {
  const rec = UI.recording; if (!rec) return;
  UI.recording = null;
  if (apply && rec.mode === "steps") {
    for (const k of rec.held) rec.steps.push([20, k, "up"]);
    if (rec.steps.length) rec.done(rec.steps);
  }
  if (rec.capEl.isConnected) {
    rec.capEl.classList.remove("on");
    rec.capEl.textContent = rec.unknown ? `Aufnahme beendet (${rec.unknown} unbekannte Tasten übersprungen).` : "Aufnahme beendet.";
    rec.btn.classList.remove("rec");
    rec.btn.textContent = rec.mode === "combo" ? "⏺ Kombination aufnehmen" : "⏺ Aufnehmen";
  }
}
function onKey(e) {
  const rec = UI.recording; if (!rec) return;
  e.preventDefault(); e.stopPropagation();
  if (e.repeat) return;
  const k = CODE_MAP[e.code];
  if (!k) { if (e.type === "keydown") rec.unknown++; return; }
  const now = performance.now();
  if (rec.mode === "combo") {
    if (e.type === "keydown") { if (!rec.combo.includes(k)) rec.combo.push(k); rec.held.add(k);
      rec.capEl.textContent = "● " + rec.combo.map(keyLabel).join(" + "); }
    else { rec.held.delete(k); if (!rec.held.size && rec.combo.length) { rec.done(rec.combo.slice()); stopRecording(false); } }
    return;
  }
  if (e.type === "keyup" && !rec.held.has(k)) return;
  const wait = rec.last === null ? 0 : Math.round(now - rec.last);
  rec.last = now;
  if (e.type === "keydown") rec.held.add(k); else rec.held.delete(k);
  rec.steps.push([Math.min(wait, 5000), k, e.type === "keydown" ? "down" : "up"]);
  const n = rec.steps.filter(s => s[2] === "down").length;
  rec.capEl.textContent = `● Aufnahme läuft – ${n} Tastendrücke …`;
}
window.addEventListener("keydown", onKey, true);
window.addEventListener("keyup", onKey, true);

// ---------------------------------------------------------------- Übernehmen
function draftToEntry(d) {
  const e = {};
  if (d.name && d.name.trim()) e.name = d.name.trim();
  switch (d.type) {
    case "text": if (d.text) e.text = d.text; break;
    case "combo": if (d.combo.length) e.combo = d.combo.join("+"); break;
    case "steps": if (d.steps.length) e.steps = d.steps; break;
    case "open": if (d.open) e.open = /^[a-z]+:\/\//i.test(d.open) ? d.open : "https://" + d.open; break;
    case "run": if (d.run.trim()) e.run = d.run.trim(); break;
    case "radio": if (d.radio) e.radio = d.radio; break;
    case "media": if (d.media) e.media = d.media; break;
    case "volume": if (d.volume) e.volume = d.volume; break;
    case "snippets": e.snippets = d.snippets || "*"; break;
    case "sleep": e.sleep = d.sleep || 30; break;
    case "mic": e.mic = "toggle"; break;
    case "timer": {
      const t = d.timer;
      e.timer = t.mode === "stopwatch" ? {mode: "stopwatch"} :
        t.mode === "pomodoro" ? {mode: "pomodoro", work: t.work, break: t.break} : {mode: "timer", minutes: t.minutes};
      break; }
  }
  return Object.keys(e).length ? e : null;
}
function draftProblem(d) {
  const need = {text: [d.text, "Bitte einen Text eingeben."], combo: [d.combo.length, "Bitte eine Tastenkombination aufnehmen oder auswählen."],
    steps: [d.steps.length, "Das Makro hat noch keine Schritte."], open: [d.open, "Bitte eine Webadresse eingeben."],
    run: [d.run.trim(), "Bitte einen Befehl eingeben."], radio: [d.radio, "Bitte einen Sender wählen."]}[d.type];
  return need && !need[0] ? need[1] : null;
}
async function saveMacros(macros, msg) {
  const r = await api("/api/macros", {body: {macros}});
  S.macros = r.macros; S.mtimes.macros = r.mtime;
  $("#extBanner").classList.remove("show");
  toast(msg);
}
async function applyDraft() {
  stopRecording(true);
  const d = UI.draft, problem = draftProblem(d);
  if (problem) { toast(problem, true); return; }
  const m = clone(S.macros), e = draftToEntry(d), keys = m.profiles[UI.pidx].keys;
  keys[UI.profile] = keys[UI.profile] || {};
  if (e) keys[UI.profile][UI.gkey] = e; else delete keys[UI.profile][UI.gkey];
  try {
    await saveMacros(m, `${UI.gkey} (${P().name}, ${UI.profile}) gespeichert – der Treiber übernimmt es sofort.`);
    selectKey(UI.gkey, true); renderKeypad(); renderEditor();
  } catch (err) { toast(err.message, true); }
}
async function clearKey() {
  if (!confirm(`Belegung von ${UI.gkey} (${P().name}, ${UI.profile}) entfernen? Die Taste sendet danach wieder ${fKeyText(UI.gkey, UI.profile)}.`)) return;
  const m = clone(S.macros), keys = m.profiles[UI.pidx].keys;
  if (keys[UI.profile]) delete keys[UI.profile][UI.gkey];
  try { await saveMacros(m, `${UI.gkey} (${P().name}, ${UI.profile}) zurückgesetzt.`); selectKey(UI.gkey, true); renderKeypad(); renderEditor(); }
  catch (err) { toast(err.message, true); }
}

// ---------------------------------------------------------------- Profile verwalten
function afterProfileChange() { selectKey(UI.gkey, true); renderProfiles(); renderKeypad(); renderEditor(); }
async function setActive(i, quiet) {
  const r = await api("/api/active", {body: {index: i}});
  S.active = r.active;
  if (!quiet) toast(`„${P(i).name}“ ist jetzt an der Tastatur aktiv.`);
  renderProfileCard();
}
async function activateProfile() { try { await setActive(UI.pidx); } catch (e) { toast(e.message, true); } }
async function saveProfiles(m, msg, newPidx, newActive) {
  try {
    await saveMacros(m, msg);
    UI.pidx = Math.max(0, Math.min(newPidx, S.macros.profiles.length - 1));
    if (newActive !== S.active) await setActive(Math.max(0, Math.min(newActive, S.macros.profiles.length - 1)), true);
    afterProfileChange();
  } catch (e) { toast(e.message, true); }
}
function askName(title, value) {
  const name = prompt(title, value);
  if (name === null) return null;
  const t = name.trim().slice(0, 30);
  if (!t) { toast("Der Name darf nicht leer sein.", true); return null; }
  return t;
}
$("#profSel").addEventListener("change", e => {
  if (!confirmLeave()) { e.target.value = UI.pidx; return; }
  UI.pidx = parseInt(e.target.value); afterProfileChange();
});
$("#profNew").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const name = askName("Name des neuen Profils:", `Profil ${S.macros.profiles.length + 1}`); if (!name) return;
  const m = clone(S.macros);
  m.profiles.push({name, colors: clone((UI.sdraft || S.settings).colors), keys: {}});
  saveProfiles(m, `Profil „${name}“ angelegt.`, m.profiles.length - 1, S.active);
});
$("#profCopy").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const name = askName("Name der Kopie:", `${P().name} (Kopie)`.slice(0, 30)); if (!name) return;
  const m = clone(S.macros), copy = clone(P());
  copy.name = name; copy.colors = clone(profColors());
  m.profiles.splice(UI.pidx + 1, 0, copy);
  saveProfiles(m, `Profil „${name}“ angelegt (Kopie von „${P().name}“).`, UI.pidx + 1, S.active > UI.pidx ? S.active + 1 : S.active);
});
$("#profRename").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const name = askName("Neuer Name des Profils:", P().name); if (!name) return;
  const m = clone(S.macros); m.profiles[UI.pidx].name = name;
  saveProfiles(m, `Profil umbenannt in „${name}“.`, UI.pidx, S.active);
});
$("#profDel").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const cnt = Object.values(P().keys || {}).reduce((a, l) => a + Object.keys(l).length, 0);
  if (!confirm(`Profil „${P().name}“ mit ${cnt} Belegungen löschen?`)) return;
  const m = clone(S.macros), i = UI.pidx; m.profiles.splice(i, 1);
  const act = S.active === i ? 0 : (S.active > i ? S.active - 1 : S.active);
  saveProfiles(m, `Profil „${P().name}“ gelöscht.`, Math.max(0, i - 1), act);
});
function moveProfile(dir) {
  if (!confirmLeave()) return;
  const i = UI.pidx, j = i + dir, m = clone(S.macros);
  if (j < 0 || j >= m.profiles.length) return;
  [m.profiles[i], m.profiles[j]] = [m.profiles[j], m.profiles[i]];
  const act = S.active === i ? j : (S.active === j ? i : S.active);
  saveProfiles(m, "Reihenfolge geändert.", j, act);
}
$("#profUp").addEventListener("click", () => moveProfile(-1));
$("#profDown").addEventListener("click", () => moveProfile(1));
function setProfileColor(layer, value) {
  if (!confirmLeave()) { renderProfileCard(); return; }
  const m = clone(S.macros), p = m.profiles[UI.pidx];
  p.colors = clone(profColors()); p.colors[layer] = rgb(value);
  saveProfiles(m, `Farbe für ${layer} gespeichert.`, UI.pidx, S.active);
}

// ---------------------------------------------------------------- Radiosender
function touchSettings() { UI.sDirty = true; markTabs(); renderSavebar(); schedulePreview(); }
function renderStations() {
  const t = $("#stations"), sd = UI.sdraft; if (!sd) return;
  t.replaceChildren(el("thead", {}, el("tr", {}, el("th", {}), el("th", {}, "Name"), el("th", {}, "Stream-Adresse"), el("th", {}, "Logo (optional)"), el("th", {}))));
  const tb = el("tbody");
  sd.stations.forEach((s, i) => {
    const playing = UI.testing && UI.testing.url === s.url;
    const img = el("img", {class: "logo", src: s.logo || "", alt: "", onerror: e => e.target.style.visibility = "hidden"});
    tb.append(el("tr", {class: playing ? "playing" : ""},
      el("td", {style: {width: "44px"}}, img),
      el("td", {style: {width: "22%"}}, el("input", {type: "text", value: s.name, placeholder: "Name",
        oninput: e => { s.name = e.target.value; touchSettings(); }})),
      el("td", {}, el("input", {type: "url", value: s.url, placeholder: "https://…",
        oninput: e => { s.url = e.target.value.trim(); touchSettings(); }})),
      el("td", {style: {width: "22%"}}, el("input", {type: "url", value: s.logo || "", placeholder: "https://…/logo.png",
        oninput: e => { s.logo = e.target.value.trim(); img.style.visibility = ""; img.src = s.logo; touchSettings(); }})),
      el("td", {style: {whiteSpace: "nowrap"}},
        el("button", {class: "btn icon small", title: playing ? "Probehören beenden" : "Probehören",
          onclick: () => playing ? stopTest() : testStation(s)}, playing ? "■" : "▶"),
        el("button", {class: "btn icon small", title: "nach oben", disabled: i === 0,
          onclick: () => { [sd.stations[i - 1], sd.stations[i]] = [sd.stations[i], sd.stations[i - 1]]; touchSettings(); renderStations(); }}, "↑"),
        el("button", {class: "btn icon small", title: "nach unten", disabled: i === sd.stations.length - 1,
          onclick: () => { [sd.stations[i + 1], sd.stations[i]] = [sd.stations[i], sd.stations[i + 1]]; touchSettings(); renderStations(); }}, "↓"),
        el("button", {class: "btn icon small danger", title: "löschen",
          onclick: () => { if (confirm(`Sender „${s.name || s.url}“ löschen?`)) { sd.stations.splice(i, 1); touchSettings(); renderStations(); } }}, "✕"))));
  });
  if (!sd.stations.length) tb.append(el("tr", {}, el("td", {colspan: 5, class: "empty", text: "Noch keine Sender – unten suchen oder hinzufügen."})));
  t.append(tb);
  $("#player").value = sd.radio_player || "";
  $("#stopTest").style.display = UI.testing ? "" : "none";
  $("#mpvHint").replaceChildren(
    S.tools.mpv ? el("p", {class: "hint", text: "✓ mpv ist installiert."}) :
      el("div", {class: "warnbox"}, "mpv ist nicht installiert. Installieren mit ", el("code", {text: "sudo apt install mpv"})),
    S.tools.mpris ? el("p", {class: "hint", text: "✓ Medientasten der Tastatur steuern das Radio (Play/Pause, Vor/Zurück = Sender wechseln, Stop)."}) :
      el("div", {class: "warnbox"}, "Damit die Medientasten der Tastatur das Radio steuern: ", el("code", {text: "sudo apt install mpv-mpris"})));
  renderAlarmClock();
}
// Radiowecker und gemerkte Songs
const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
function renderAlarmClock() {
  const sd = UI.sdraft; if (!sd) return;
  const a = sd.alarm_clock;                 // vollständig vom Server (Schema im Treiber)
  $("#acOn").checked = !!a.enabled; $("#acTime").value = a.time;
  const st = sd.stations.filter(x => x.url);
  $("#acStation").replaceChildren(...(st.length ? st.map(x => el("option", {value: x.url, text: x.name || domainOf(x.url), selected: x.url === a.station}))
    : [el("option", {value: "", text: "– erst Sender anlegen –"})]));
  if (st.length && !st.some(x => x.url === a.station)) a.station = st[0].url;
  $("#acDays").replaceChildren(...WEEKDAYS.map((n, i) => el("button", {class: a.days.includes(i) ? "active" : "", text: n,
    onclick: () => { a.days = a.days.includes(i) ? a.days.filter(x => x !== i) : [...a.days, i].sort(); touchSettings(); renderAlarmClock(); }})));
}
$("#acOn").addEventListener("change", e => { UI.sdraft.alarm_clock.enabled = e.target.checked; touchSettings(); });
$("#acTime").addEventListener("change", e => { UI.sdraft.alarm_clock.time = e.target.value || "07:00"; touchSettings(); });
$("#acStation").addEventListener("change", e => { UI.sdraft.alarm_clock.station = e.target.value; touchSettings(); });
async function loadSongs() {
  try { UI.songs = (await api("/api/songs")).songs; } catch (e) { UI.songs = []; }
  renderSongs();
}
function renderSongs() {
  const box = $("#songs"), songs = UI.songs || [];
  if (!songs.length) { box.replaceChildren(el("div", {class: "empty", text: "Noch keine Songs gemerkt."})); return; }
  box.replaceChildren(el("table", {class: "list"}, el("tbody", {}, ...songs.slice().reverse().map(sg => {
    const q = encodeURIComponent(`${sg.artist} ${sg.title}`.trim());
    return el("tr", {},
      el("td", {class: "muted", style: {whiteSpace: "nowrap", width: "1%"}, text: sg.time}),
      el("td", {}, el("b", {text: sg.title || "–"}), el("div", {class: "muted", text: [sg.artist, sg.source].filter(Boolean).join(" · ")})),
      el("td", {style: {whiteSpace: "nowrap", width: "1%"}},
        el("a", {class: "btn small", href: `https://www.youtube.com/results?search_query=${q}`, target: "_blank", rel: "noopener"}, "YouTube"),
        el("a", {class: "btn small", href: `https://open.spotify.com/search/${q}`, target: "_blank", rel: "noopener"}, "Spotify"),
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => saveSongs(songs.filter(x => x !== sg))}, "✕")));
  }))));
}
async function saveSongs(list) {
  try { UI.songs = (await api("/api/songs", {body: {songs: list}})).songs; renderSongs(); } catch (e) { toast(e.message, true); }
}
$("#songsRefresh").addEventListener("click", loadSongs);
$("#songsClear").addEventListener("click", () => { if ((UI.songs || []).length && confirm("Alle gemerkten Songs löschen?")) saveSongs([]); });
$("#addStation").addEventListener("click", () => { UI.sdraft.stations.push({name: "", url: "", logo: ""}); touchSettings(); renderStations();
  const rows = $("#stations").querySelectorAll("tbody tr"); rows[rows.length - 1].querySelector("input").focus(); });
$("#player").addEventListener("input", e => { UI.sdraft.radio_player = e.target.value; touchSettings(); });
$("#stopTest").addEventListener("click", () => stopTest());
async function testStation(s) {
  if (!s.url) { toast("Bitte zuerst eine Stream-Adresse eingeben.", true); return; }
  try { await api("/api/radio/play", {body: {name: s.name, url: s.url, player: UI.sdraft.radio_player}});
    UI.testing = {url: s.url, name: s.name}; toast("Probehören: " + (s.name || s.url)); }
  catch (e) { toast(e.message, true); }
  renderStations(); renderResults();
}
async function stopTest() { try { await api("/api/radio/stop", {body: {}}); } catch (e) {} UI.testing = null; renderStations(); renderResults(); }
let lastResults = [];
$("#searchForm").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("#searchQ").value.trim(); if (!q) return;
  $("#results").replaceChildren(el("div", {class: "empty", text: "Suche …"}));
  try { lastResults = (await api("/api/radio/search?q=" + encodeURIComponent(q))).results; renderResults(); }
  catch (err) { $("#results").replaceChildren(el("div", {class: "warnbox", text: err.message})); }
});
function renderResults() {
  const box = $("#results"); if (!lastResults.length) { if (box.querySelector(".res")) box.replaceChildren(); return; }
  box.replaceChildren();
  for (const r of lastResults) {
    const have = UI.sdraft.stations.some(s => s.url === r.url);
    const playing = UI.testing && UI.testing.url === r.url;
    box.append(el("div", {class: "res"},
      el("img", {class: "logo", src: r.logo || "", alt: "", onerror: e => e.target.style.visibility = "hidden"}),
      el("div", {class: "grow"}, el("div", {class: "name", text: r.name || r.url}),
        el("div", {class: "meta", text: [r.country, r.codec && (r.codec + (r.bitrate ? " " + r.bitrate + " kbit/s" : "")), r.tags].filter(Boolean).join(" · ")})),
      el("button", {class: "btn icon small", title: playing ? "Probehören beenden" : "Probehören",
        onclick: () => playing ? stopTest() : testStation(r)}, playing ? "■" : "▶"),
      el("button", {class: "btn small" + (have ? "" : " primary"), disabled: have,
        onclick: () => { UI.sdraft.stations.push({name: r.name, url: r.url, logo: r.logo}); touchSettings(); renderStations(); renderResults();
          toast(`„${r.name}“ hinzugefügt – zum Übernehmen unten speichern.`); }}, have ? "✓ in der Liste" : "+ Hinzufügen")));
  }
}

// ---------------------------------------------------------------- Textbausteine
function renderSnippets() {
  const sd = UI.sdraft, box = $("#snippetList"); if (!sd) return;
  const groups = snippetGroups();
  box.replaceChildren(el("datalist", {id: "snipGroups"}, ...groups.map(g => el("option", {value: g}))));
  if (!sd.snippets.length) box.append(el("div", {class: "empty", text: "Noch keine Textbausteine."}));
  sd.snippets.forEach((sn, i) => {
    box.append(el("div", {class: "snip"},
      el("div", {class: "row", style: {flexWrap: "nowrap"}},
        el("input", {type: "text", value: sn.name || "", placeholder: "Name auf dem Display", style: {flex: "2"}, maxlength: 40,
          oninput: e => { sn.name = e.target.value; touchSettings(); }}),
        el("input", {type: "text", value: sn.group || "", placeholder: "Gruppe (optional)", list: "snipGroups", style: {flex: "1"}, maxlength: 30,
          oninput: e => { sn.group = e.target.value; touchSettings(); }}),
        el("button", {class: "btn icon small", title: "nach oben", disabled: i === 0,
          onclick: () => { [sd.snippets[i - 1], sd.snippets[i]] = [sd.snippets[i], sd.snippets[i - 1]]; touchSettings(); renderSnippets(); }}, "↑"),
        el("button", {class: "btn icon small", title: "nach unten", disabled: i === sd.snippets.length - 1,
          onclick: () => { [sd.snippets[i + 1], sd.snippets[i]] = [sd.snippets[i], sd.snippets[i + 1]]; touchSettings(); renderSnippets(); }}, "↓"),
        el("button", {class: "btn icon small danger", title: "löschen",
          onclick: () => { if (confirm(`Textbaustein „${sn.name || sn.text.slice(0, 30)}“ löschen?`)) { sd.snippets.splice(i, 1); touchSettings(); renderSnippets(); } }}, "✕")),
      el("textarea", {rows: 3, placeholder: "Text, der eingefügt wird (Umlaute, ß, @, € und Zeilenumbrüche sind möglich)",
        oninput: e => { sn.text = e.target.value; touchSettings(); }}, sn.text || "")));
  });
}
$("#addSnippet").addEventListener("click", () => {
  UI.sdraft.snippets.push({name: "", group: "", text: ""}); touchSettings(); renderSnippets();
  const ins = $("#snippetList").querySelectorAll(".snip input[type=text]"); ins[ins.length - 2].focus(); });

// ---------------------------------------------------------------- Beleuchtung & Display
function renderSettings() {
  const sd = UI.sdraft; if (!sd) return;
  $("#keepBacklight").checked = !!sd.keep_backlight;
  const on = sd.brightness !== null && sd.brightness !== undefined;
  $("#brightOn").checked = on; $("#bright").disabled = !on;
  $("#bright").value = on ? sd.brightness : 100;
  $("#brightVal").textContent = on ? sd.brightness + " %" : "unverändert";
  const enabled = layerPages().M1;
  const sp = $("#startPage");
  sp.replaceChildren(...enabled.map(id => { const i = S.pageIds.indexOf(id);
    return el("option", {value: i, text: S.pages[i], selected: i === sd.start_page}); }));
  if (!enabled.includes(S.pageIds[sd.start_page])) sp.selectedIndex = 0;
  $("#pvPages").replaceChildren(...S.pages.map((n, i) => el("option", {value: i, text: "Vorschau: " + n, selected: i === UI.pvPage})));
  renderPageList();
  renderClock();
  const n = sd.night;
  $("#nightOn").checked = !!n.enabled; $("#nightStart").value = n.start; $("#nightEnd").value = n.end;
  document.querySelectorAll("#nightMode button").forEach(b => b.classList.toggle("active", b.dataset.mode === n.mode));
  $("#nightDimRow").style.display = n.mode === "dim" ? "" : "none";
  $("#nightBright").value = n.brightness; $("#nightBrightVal").textContent = n.brightness + " %";
  $("#nightBacklight").checked = !!n.backlight_off;
  const ss = sd.screensaver;
  $("#saverOn").checked = !!ss.enabled; $("#saverMin").value = ss.minutes;
  $("#saverPage").replaceChildren(...S.pageIds.map((id, i) => el("option", {value: id, text: S.pages[i], selected: id === ss.page})));
  $("#volStep").value = sd.volume_step;
  $("#timerSound").checked = sd.timer_sound;
  $("#pvProfiles").replaceChildren(...PROFILES.map(p => el("button", {class: p === UI.pvProfile ? "active" : "", text: p,
    onclick: () => { UI.pvProfile = p; renderSettings(); refreshPreview(); }})));
}
function layerPages() { return UI.sdraft.layer_pages; }   // vom Server immer für M1–M3 vollständig
function pageTarget() {
  const profs = S.macros.profiles;
  if (UI.pageScope === undefined || UI.pageScope >= profs.length) UI.pageScope = -1;
  if (UI.pageScope === -1) return {lp: layerPages(), commit: () => { touchSettings(); renderSettings(); refreshPreview(); }};
  const p = profs[UI.pageScope];
  if (!p.pages) return {lp: null, profile: p};
  const lp = clone(p.pages);
  return {lp, profile: p, commit: () => setProfilePages(UI.pageScope, lp)};
}
async function setProfilePages(i, pages) {
  const m = clone(S.macros), p = m.profiles[i];
  if (pages) p.pages = pages; else delete p.pages;
  await saveProfiles(m, pages ? `Displayseiten für „${p.name}“ gespeichert.` : `„${p.name}“ verwendet wieder die Standard-Seiten.`, UI.pidx, S.active);
  renderSettings(); refreshPreview();
}
function renderPageList() {
  const L = UI.pvProfile, t = pageTarget(), profs = S.macros.profiles;
  $("#plScope").replaceChildren(el("option", {value: -1, text: "Alle Profile (Standard)", selected: UI.pageScope === -1}),
    ...profs.map((p, i) => el("option", {value: i, text: `Profil ${i + 1}: ${p.name}` + (p.pages ? " – eigene Seiten" : ""), selected: UI.pageScope === i})));
  $("#plOwnOff").style.display = t.lp && t.profile ? "" : "none";
  $("#plCopy").style.display = t.lp ? "" : "none";
  $("#plLayers").replaceChildren(...PROFILES.map(p => el("button", {class: p === L ? "active" : "", text: p,
    onclick: () => { UI.pvProfile = p; renderSettings(); refreshPreview(); }})));
  if (!t.lp) {
    $("#pageList").replaceChildren(el("div", {class: "empty"},
      `„${t.profile.name}“ verwendet die Standard-Seiten (Alle Profile). `,
      el("button", {class: "btn small primary", onclick: () => setProfilePages(UI.pageScope, clone(layerPages()))}, "Eigene Seiten für dieses Profil festlegen")));
    return;
  }
  const lp = t.lp, on = lp[L];
  const order = [...on, ...S.pageIds.filter(id => !on.includes(id))];
  $("#pageList").replaceChildren(...order.map(id => {
    const enabled = on.includes(id), pos = on.indexOf(id);
    return el("div", {class: "pagerow" + (enabled ? "" : " off")},
      el("input", {type: "checkbox", checked: enabled, onchange: e => {
        if (e.target.checked) lp[L].push(id);
        else if (lp[L].length > 1) lp[L] = lp[L].filter(x => x !== id);
        else { e.target.checked = true; toast("Mindestens eine Seite muss eingeschaltet bleiben.", true); return; }
        t.commit(); }}),
      el("span", {class: "pn", text: S.pages[S.pageIds.indexOf(id)]}),
      el("button", {class: "btn icon small", title: "nach oben", disabled: !enabled || pos === 0,
        onclick: () => { [lp[L][pos - 1], lp[L][pos]] = [lp[L][pos], lp[L][pos - 1]]; t.commit(); }}, "↑"),
      el("button", {class: "btn icon small", title: "nach unten", disabled: !enabled || pos === on.length - 1,
        onclick: () => { [lp[L][pos + 1], lp[L][pos]] = [lp[L][pos], lp[L][pos + 1]]; t.commit(); }}, "↓"));
  }));
}
$("#plScope").addEventListener("change", e => { UI.pageScope = parseInt(e.target.value); renderSettings(); });
$("#plOwnOff").addEventListener("click", () => { if (confirm("Eigene Seiten dieses Profils löschen und wieder die Standard-Seiten verwenden?")) setProfilePages(UI.pageScope, null); });
$("#plCopy").addEventListener("click", () => {
  const t = pageTarget(); if (!t.lp) return;
  const src = t.lp[UI.pvProfile];
  for (const l of PROFILES) t.lp[l] = [...src];
  t.commit(); toast(`Seiten von ${UI.pvProfile} für alle Ebenen übernommen.`);
});
$("#keepBacklight").addEventListener("change", e => { UI.sdraft.keep_backlight = e.target.checked; touchSettings(); });
$("#brightOn").addEventListener("change", e => { UI.sdraft.brightness = e.target.checked ? 100 : null; touchSettings(); renderSettings(); });
$("#bright").addEventListener("input", e => { UI.sdraft.brightness = parseInt(e.target.value); $("#brightVal").textContent = e.target.value + " %"; touchSettings(); });
$("#startPage").addEventListener("change", e => { UI.sdraft.start_page = parseInt(e.target.value); touchSettings(); });
$("#pvPages").addEventListener("change", e => { UI.pvPage = parseInt(e.target.value); refreshPreview(); });
$("#nightOn").addEventListener("change", e => { UI.sdraft.night.enabled = e.target.checked; touchSettings(); });
$("#nightStart").addEventListener("change", e => { UI.sdraft.night.start = e.target.value; touchSettings(); });
$("#nightEnd").addEventListener("change", e => { UI.sdraft.night.end = e.target.value; touchSettings(); });
$("#nightMode").addEventListener("click", e => { const b = e.target.closest("button[data-mode]"); if (!b) return;
  UI.sdraft.night.mode = b.dataset.mode; touchSettings(); renderSettings(); });
$("#nightBright").addEventListener("input", e => { UI.sdraft.night.brightness = parseInt(e.target.value);
  $("#nightBrightVal").textContent = e.target.value + " %"; touchSettings(); });
$("#nightBacklight").addEventListener("change", e => { UI.sdraft.night.backlight_off = e.target.checked; touchSettings(); });
$("#saverOn").addEventListener("change", e => { UI.sdraft.screensaver.enabled = e.target.checked; touchSettings(); });
$("#saverMin").addEventListener("input", e => { UI.sdraft.screensaver.minutes = Math.max(1, parseInt(e.target.value) || 5); touchSettings(); });
$("#saverPage").addEventListener("change", e => { UI.sdraft.screensaver.page = e.target.value; touchSettings(); });
$("#volStep").addEventListener("input", e => { UI.sdraft.volume_step = Math.max(1, Math.min(25, parseInt(e.target.value) || 5)); touchSettings(); });
// Vorschau nach Änderungen an den Einstellungen verzögert neu laden (touchSettings ruft das auf)
let pvTimer = null;
function schedulePreview() { clearTimeout(pvTimer); pvTimer = setTimeout(refreshPreview, 250); }
async function refreshPreview() {
  if (UI.tab !== "settings") return;
  try { $("#lcd").src = (await api("/api/preview", {body: {page: UI.pvPage, profile: UI.pvProfile, settings: UI.sdraft,
    pidx: UI.pidx}})).image; }
  catch (e) { /* Vorschau ist nicht kritisch */ }
}
$("#timerSound").addEventListener("change", e => { UI.sdraft.timer_sound = e.target.checked; touchSettings(); });

// ---------------------------------------------------------------- Uhr: Zifferblätter
// Optionen je Zifferblatt kommen aus CLOCK_OPTIONS des Treibers (S.clockOptions) und werden
// in UI.sdraft.clock[<zifferblatt>] bearbeitet; gespeichert wird mit den übrigen Einstellungen.
function clockDraft(face) {
  const c = UI.sdraft.clock;
  if (!c[face]) c[face] = {};
  return c[face];
}
function renderClock() {
  const sd = UI.sdraft; if (!sd || !S.clockFaces) return;
  if (!UI.clkFace) UI.clkFace = "digital";
  $("#clkFace").replaceChildren(...S.clockFaces.map(([id, label]) =>
    el("option", {value: id, text: label + (S.clockOptions[id] ? "" : " (ohne Einstellungen)"), selected: id === UI.clkFace})));
  renderClockOptions();
  const menu = sd.clock.menu && sd.clock.menu.length ? sd.clock.menu : S.clockFaces.map(f => f[0]);
  $("#clkMenu").replaceChildren(...S.clockFaces.map(([id, label]) => el("label", {},
    el("input", {type: "checkbox", checked: menu.includes(id), onchange: e => {
      let m = S.clockFaces.map(f => f[0]).filter(f => f === id ? e.target.checked : menu.includes(f));
      if (!m.length) { e.target.checked = true; toast("Mindestens ein Zifferblatt muss angeboten werden.", true); return; }
      sd.clock.menu = m.length === S.clockFaces.length ? [] : m;     // leer = alle
      touchSettings(); renderClock(); }}),
    el("span", {text: label}))));
  clockPreview();
}
function renderClockOptions() {
  const face = UI.clkFace, opts = S.clockOptions[face] || [], d = clockDraft(face);
  const box = $("#clkOpts");
  if (!opts.length) { box.replaceChildren(el("p", {class: "hint", text: "Für dieses Zifferblatt gibt es keine Einstellungen."})); return; }
  const changed = () => { touchSettings(); clockPreview(); };
  box.replaceChildren(...opts.map(o => {
    const val = o.key in d ? d[o.key] : o.default;
    if (o.type === "bool")
      return el("label", {class: "check clkopt"}, el("input", {type: "checkbox", checked: !!val,
        onchange: e => { d[o.key] = e.target.checked; changed(); }}), " " + o.label);
    if (o.type === "choice")
      return el("label", {class: "field clkopt", style: {maxWidth: "300px"}}, el("span", {text: o.label}),
        el("select", {value: val, onchange: e => { d[o.key] = e.target.value; changed(); }},
          o.choices.map(([v, l]) => el("option", {value: v, text: l}))));
    if (o.type === "color") {
      const pick = el("input", {type: "color", value: hex(val || [255, 255, 255]), disabled: !val,
        oninput: e => { d[o.key] = rgb(e.target.value); changed(); }});
      const sel = el("select", {value: val ? "own" : "std", style: {width: "auto"}, onchange: e => {
        d[o.key] = e.target.value === "own" ? rgb(pick.value) : null;
        pick.disabled = e.target.value !== "own"; changed(); }},
        el("option", {value: "std", text: o.none_label}), el("option", {value: "own", text: "Eigene Farbe"}));
      return el("div", {class: "field clkopt"}, el("span", {text: o.label}), el("div", {class: "row"}, sel, pick));
    }
    if (o.type === "cities") {
      const list = (val && val.length ? val : o.default).slice();
      const opts6 = [...list, ...Array(Math.max(0, 6 - list.length)).fill(null)].slice(0, 6);
      return el("div", {class: "field clkopt"}, el("span", {text: o.label + " (bis zu 6)"}),
        el("div", {class: "clkcities"}, opts6.map((c, i) => el("select", {value: c ? c.tz : "", onchange: e => {
          opts6[i] = e.target.value ? {name: S.worldCities.find(w => w[1] === e.target.value)[0], tz: e.target.value} : null;
          const next = opts6.filter(Boolean);
          if (!next.length) { toast("Mindestens eine Stadt wählen.", true); e.target.value = c ? c.tz : ""; return; }
          d[o.key] = next; changed(); }},
          el("option", {value: "", text: "—"}),
          S.worldCities.map(([n, tz]) => el("option", {value: tz, text: n}))))));
    }
    return null;
  }));
}
let clkTimer = null;
function clockPreview() {
  clearTimeout(clkTimer);
  clkTimer = setTimeout(async () => {
    if (UI.tab !== "settings") return;
    try { $("#clkLcd").src = (await api("/api/preview", {body: {page: S.pageIds.indexOf("clock"), profile: UI.pvProfile || "M1",
      settings: UI.sdraft, pidx: UI.pidx, face: UI.clkFace}})).image; }
    catch (e) { /* Vorschau ist nicht kritisch */ }
  }, 200);
}
$("#clkFace").addEventListener("change", e => { UI.clkFace = e.target.value; renderClockOptions(); clockPreview(); });
$("#clkAll").addEventListener("click", () => { UI.sdraft.clock.menu = []; touchSettings(); renderClock(); });

// ---------------------------------------------------------------- Diashow (Piwigo)
UI.albums = null;
const slCfg = () => UI.sdraft.slideshow;
function renderSlides() {
  if (!UI.sdraft) return;
  const c = slCfg();
  $("#pwUrl").value = c.url || ""; $("#pwUser").value = c.user || ""; $("#pwPass").value = c.password || "";
  $("#slInterval").value = c.interval; $("#slShuffle").checked = !!c.shuffle;
  $("#slRecursive").checked = !!c.recursive; $("#slCaption").checked = !!c.caption;
  document.querySelectorAll("#slFit button").forEach(b => b.classList.toggle("active", b.dataset.fit === c.fit));
  renderSource();
  renderAlbums();
}
function renderSource() {
  const c = slCfg(), folder = c.source === "folder";
  document.querySelectorAll("#slSource button").forEach(b => b.classList.toggle("active", b.dataset.src === (c.source || "piwigo")));
  $("#folderBlock").style.display = folder ? "" : "none";
  $("#pwBlock").style.display = folder ? "none" : "";
  $("#fdPath").value = c.folder || "";
}
$("#slSource").addEventListener("click", e => { const b = e.target.closest("button[data-src]"); if (!b) return;
  slCfg().source = b.dataset.src; touchSettings(); renderSource(); });
$("#fdPath").addEventListener("input", e => { slCfg().folder = e.target.value.trim(); touchSettings(); });
async function browseFolder(path, opts) {
  opts = Object.assign({box: "#fdBrowser", images: true, pick: p => { slCfg().folder = p; touchSettings(); renderSource();
    toast("Ordner übernommen – zum Übernehmen unten speichern."); }}, opts || {});
  const box = $(opts.box);
  let r;
  try { r = await api("/api/folder/list?path=" + encodeURIComponent(path || "~")); }
  catch (err) { box.replaceChildren(el("div", {class: "warnbox", text: err.message})); return; }
  box.replaceChildren(el("div", {class: "fbrowser"},
    el("div", {class: "fhead"},
      r.parent ? el("button", {class: "btn small", onclick: () => browseFolder(r.parent, opts)}, "↑") : null,
      el("b", {style: {flex: "1", wordBreak: "break-all"}, text: r.path}),
      opts.images ? el("span", {class: "muted", text: r.images === 1 ? "1 Bild" : `${r.images} Bilder`}) : null,
      el("button", {class: "btn small primary", onclick: () => { box.replaceChildren(); opts.pick(r.path); }}, "Diesen Ordner wählen")),
    r.dirs.length ? r.dirs.map(dname => el("div", {class: "frow", onclick: () => browseFolder(r.path.replace(/\/$/, "") + "/" + dname, opts)},
      el("span", {text: "📁"}), el("span", {text: dname}))) : el("div", {class: "empty", text: "Keine Unterordner"})));
}
$("#fdBrowse").addEventListener("click", () => browseFolder(slCfg().folder || "~"));
function renderAlbums() {
  const c = slCfg(), box = $("#albums"), sel = new Set(c.albums || []);
  $("#albumSum").textContent = sel.size ? `${sel.size} ausgewählt` : "";
  if (!UI.albums) {
    box.replaceChildren(el("div", {class: "empty", text: sel.size
      ? `${sel.size} Alben ausgewählt – „Alben laden“ klicken, um sie anzuzeigen.` : "Zuerst „Alben laden“ klicken."}));
    return;
  }
  if (!UI.albums.length) { box.replaceChildren(el("div", {class: "empty", text: "Keine Alben sichtbar – bei privaten Alben Benutzer und Passwort eintragen."})); return; }
  const known = new Set(UI.albums.map(a => a.id));
  const rows = UI.albums.map(a => {
    const n = c.recursive ? a.total : a.images;
    return el("label", {class: "album", style: {paddingLeft: (12 + a.level * 22) + "px"}},
      el("input", {type: "checkbox", checked: sel.has(a.id), onchange: e => toggleAlbum(a.id, e.target.checked)}),
      el("span", {class: "an", text: a.name, title: a.path}),
      el("span", {class: "ac", text: n === 1 ? "1 Bild" : `${n} Bilder`}));
  });
  for (const id of sel) if (!known.has(id)) rows.push(el("label", {class: "album missing"},
    el("input", {type: "checkbox", checked: true, onchange: e => toggleAlbum(id, e.target.checked)}),
    el("span", {class: "an", text: `Album #${id} (nicht mehr gefunden)`}), el("span", {class: "ac"})));
  box.replaceChildren(...rows);
}
function toggleAlbum(id, on) {
  const s = new Set(slCfg().albums || []);
  on ? s.add(id) : s.delete(id);
  slCfg().albums = [...s].sort((a, b) => a - b); touchSettings(); renderAlbums();
}
async function loadAlbums(quiet) {
  const c = slCfg();
  if (!c.url) { if (!quiet) toast("Bitte die Adresse der Piwigo-Galerie eintragen.", true); return; }
  $("#pwState").textContent = "Lade Alben …";
  try {
    UI.albums = (await api("/api/piwigo/albums", {body: {url: c.url, user: c.user, password: c.password}})).albums;
    $("#pwState").textContent = `✓ ${UI.albums.length} Alben gefunden`;
  } catch (e) { UI.albums = null; $("#pwState").textContent = ""; if (!quiet) toast(e.message, true); else $("#pwState").textContent = "⚠ " + e.message; }
  renderAlbums();
}
[["#pwUrl", "url"], ["#pwUser", "user"], ["#pwPass", "password"]].forEach(([s, k]) =>
  $(s).addEventListener("input", e => { slCfg()[k] = k === "password" ? e.target.value : e.target.value.trim(); touchSettings(); }));
$("#pwLoad").addEventListener("click", () => loadAlbums(false));
$("#albAll").addEventListener("click", () => { if (UI.albums) { slCfg().albums = UI.albums.map(a => a.id); touchSettings(); renderAlbums(); } });
$("#albNone").addEventListener("click", () => { slCfg().albums = []; touchSettings(); renderAlbums(); });
$("#slInterval").addEventListener("input", e => { slCfg().interval = Math.max(3, parseInt(e.target.value) || 10); touchSettings(); });
$("#slShuffle").addEventListener("change", e => { slCfg().shuffle = e.target.checked; touchSettings(); });
$("#slRecursive").addEventListener("change", e => { slCfg().recursive = e.target.checked; touchSettings(); renderAlbums(); });
$("#slCaption").addEventListener("change", e => { slCfg().caption = e.target.checked; touchSettings(); });
$("#slFit").addEventListener("click", e => { const b = e.target.closest("button[data-fit]"); if (!b) return;
  slCfg().fit = b.dataset.fit; touchSettings(); renderSlides(); });
$("#slTest").addEventListener("click", async () => {
  $("#slTestInfo").textContent = "Teste …";
  try {
    const r = await api("/api/piwigo/test", {body: {slideshow: slCfg()}});
    if (r.image) $("#slPreview").src = r.image;
    $("#slTestInfo").textContent = r.count ? `✓ ${r.count} Bilder gefunden` : "Keine Bilder in den gewählten Alben";
  } catch (e) { $("#slTestInfo").textContent = ""; toast(e.message, true); }
});
// Lieblingsbilder
async function loadFavs() {
  try { UI.favs = (await api("/api/favorites")).favorites; } catch (e) { UI.favs = []; }
  renderFavs();
}
function renderFavs() {
  const box = $("#favs"), favs = UI.favs || [];
  if (UI.sdraft) $("#favOnly").checked = !!slCfg().favorites_only;
  if (!favs.length) { box.replaceChildren(el("div", {class: "empty", text: "Noch keine Lieblingsbilder."})); return; }
  box.replaceChildren(el("div", {class: "muted", style: {margin: "6px 0"}, text: `${favs.length} Lieblingsbild${favs.length === 1 ? "" : "er"}`}),
    el("table", {class: "list"}, el("tbody", {}, ...favs.slice().reverse().map(f => el("tr", {},
      el("td", {style: {width: "1%"}, text: "♥"}),
      el("td", {}, el("b", {text: f.name || String(f.id)}), el("div", {class: "muted", text: (f.source === "folder" ? "Ordner" : "Piwigo") + " · " + (f.time || "")})),
      el("td", {style: {whiteSpace: "nowrap", width: "1%"}},
        f.page && /^https?:/.test(f.page) ? el("a", {class: "btn small", href: f.page, target: "_blank", rel: "noopener"}, "In Piwigo öffnen") : null,
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: async () => {
          try { UI.favs = (await api("/api/favorites", {body: {remove: [f.id]}})).favorites; renderFavs(); } catch (e) { toast(e.message, true); } }}, "✕")))))));
}
$("#favRefresh").addEventListener("click", loadFavs);
$("#favOnly").addEventListener("change", e => { slCfg().favorites_only = e.target.checked; touchSettings(); });

// ---------------------------------------------------------------- Infoseiten
const NEWS_PRESETS = [["tagesschau", "https://www.tagesschau.de/index~rss2.xml"], ["heise", "https://www.heise.de/rss/heise-atom.xml"],
  ["SPIEGEL", "https://www.spiegel.de/schlagzeilen/index.rss"], ["Golem", "https://rss.golem.de/rss.php?feed=RSS2.0"]];
function renderNews() {
  const sd = UI.sdraft;
  const feeds = sd.news.feeds, box = $("#newsFeeds");
  box.replaceChildren(...feeds.map((f, i) => {
    const info = el("span", {class: "muted"});
    return el("div", {class: "feedrow"},
      el("div", {class: "row", style: {flexWrap: "nowrap"}},
        el("input", {type: "text", value: f.name || "", placeholder: "Name", style: {flex: "1"}, oninput: e => { f.name = e.target.value; touchSettings(); }}),
        el("input", {type: "url", value: f.url || "", placeholder: "https://…/rss.xml", style: {flex: "3"}, oninput: e => { f.url = e.target.value.trim(); touchSettings(); }}),
        el("button", {class: "btn small", onclick: async () => { info.textContent = "prüfe …";
          try { const r = await api("/api/news/test", {body: f}); info.textContent = `✓ ${r.count} Meldungen – „${r.first}“`; }
          catch (e) { info.textContent = "✗ " + e.message; } }}, "Testen"),
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => { feeds.splice(i, 1); touchSettings(); renderNews(); }}, "✕")),
      info);
  }));
  if (!feeds.length) box.append(el("div", {class: "empty", text: "Keine Feeds – unten hinzufügen."}));
  $("#newsPresets").replaceChildren(...NEWS_PRESETS.filter(([n, u]) => !feeds.some(f => f.url === u)).map(([n, u]) =>
    el("button", {class: "btn small", onclick: () => { feeds.push({name: n, url: u}); touchSettings(); renderNews(); }}, "+ " + n)));
}
$("#newsAdd").addEventListener("click", () => { UI.sdraft.news.feeds.push({name: "", url: ""}); touchSettings(); renderNews(); });
function renderNet() {
  const sd = UI.sdraft;
  const hosts = sd.network.hosts, box = $("#netHosts");
  box.replaceChildren(...hosts.map((h, i) => el("div", {class: "row", style: {flexWrap: "nowrap", marginBottom: "6px"}},
    el("input", {type: "text", value: h.name || "", placeholder: "Name (z. B. NAS)", style: {flex: "1"}, oninput: e => { h.name = e.target.value; touchSettings(); }}),
    el("input", {type: "text", value: h.host || "", placeholder: "Adresse oder Name, z. B. 192.168.178.20", style: {flex: "2"}, oninput: e => { h.host = e.target.value.trim(); touchSettings(); }}),
    el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => { hosts.splice(i, 1); touchSettings(); renderNet(); }}, "✕"))));
  if (!hosts.length) box.append(el("div", {class: "empty", text: "Keine Geräte."}));
  const pw = (sd.slideshow || {}).url, m = pw && /^https?:\/\/([^/:]+)(?::(\d+))?/i.exec(pw);
  const pwHost = m ? m[1] + ":" + (m[2] || (/^https/i.test(pw) ? "443" : "80")) : "";
  $("#netPiwigo").style.display = pwHost && !hosts.some(h => h.host === pwHost) ? "" : "none";
  $("#netPiwigo").onclick = () => { hosts.push({name: "Piwigo", host: pwHost}); touchSettings(); renderNet(); };
}
$("#netAdd").addEventListener("click", () => { UI.sdraft.network.hosts.push({name: "", host: ""}); touchSettings(); renderNet(); });
$("#netTest").addEventListener("click", async () => {
  $("#netInfo").textContent = "prüfe …";
  try {
    const r = await api("/api/network/test", {body: {settings: UI.sdraft}});
    $("#netInfo").replaceChildren(el("div", {class: "kv"}, ...r.hosts.flatMap(h => [el("div", {text: h.name}),
      el("div", {text: h.ok ? `✓ ${h.host}${h.ms !== null ? " – " + Math.round(h.ms) + " ms" : ""}` : `✗ ${h.host} – nicht erreichbar`})]),
      el("div", {text: "Dieser PC"}), el("div", {text: r.ip || "–"})));
  } catch (e) { $("#netInfo").textContent = "✗ " + e.message; }
});
$("#warnPopup").addEventListener("change", e => { UI.sdraft.warnings = {popup: e.target.checked}; touchSettings(); });
$("#warnTest").addEventListener("click", async () => {
  $("#warnInfo").textContent = "prüfe …";
  try { const r = await api("/api/warnings/test", {body: {settings: UI.sdraft}});
    $("#warnInfo").textContent = `✓ ${r.place}: ` + (r.alerts.length ? r.alerts.join(", ") : "keine Warnungen"); }
  catch (e) { $("#warnInfo").textContent = "✗ " + e.message; }
});
$("#updFlatpak").addEventListener("change", e => { UI.sdraft.updates = {flatpak: e.target.checked}; touchSettings(); });
$("#updTest").addEventListener("click", async () => {
  $("#updInfo").textContent = "prüfe … (kann etwas dauern)";
  try { const r = await api("/api/updates/test", {body: {settings: UI.sdraft}});
    $("#updInfo").textContent = `✓ ${r.apt} Paket-Updates` + (r.security ? ` (davon ${r.security} Sicherheit)` : "") +
      (r.flatpak !== null ? `, ${r.flatpak} Flatpak` : "") + (r.reboot ? " – Neustart erforderlich" : ""); }
  catch (e) { $("#updInfo").textContent = "✗ " + e.message; }
});
function renderInfo() {
  const sd = UI.sdraft; if (!sd) return;
  renderNews(); renderNet();
  $("#warnPopup").checked = sd.warnings.popup;
  $("#updFlatpak").checked = sd.updates.flatpak;
  const w = sd.weather;
  $("#wxName").textContent = w.lat !== null && w.lat !== undefined ? (w.name || `${w.lat}, ${w.lon}`) : "noch nicht eingestellt";
  renderCalSources();
  $("#calDays").value = String(sd.calendar.days);
  $("#calRemind").value = String(sd.calendar.remind);
  const n = sd.notifications;
  $("#ntOn").checked = !!n.enabled; $("#ntSec").value = n.seconds; $("#ntIgnore").value = n.ignore || "";
}
$("#wxForm").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("#wxQ").value.trim(); if (!q) return;
  $("#wxResults").replaceChildren(el("div", {class: "empty", text: "Suche …"}));
  let r;
  try { r = (await api("/api/weather/search?q=" + encodeURIComponent(q))).results; }
  catch (err) { $("#wxResults").replaceChildren(el("div", {class: "warnbox", text: err.message})); return; }
  if (!r.length) { $("#wxResults").replaceChildren(el("div", {class: "empty", text: "Kein Ort gefunden."})); return; }
  $("#wxResults").replaceChildren(...r.map(x => el("div", {class: "res", onclick: async () => {
    UI.sdraft.weather = {name: x.name, lat: x.lat, lon: x.lon}; touchSettings(); renderInfo();
    $("#wxResults").replaceChildren(); $("#wxTest").textContent = "prüfe …";
    try { const t = await api("/api/weather/test", {body: UI.sdraft.weather});
      $("#wxTest").textContent = `✓ jetzt ${Math.round(t.temp)}°, ${t.desc}`; }
    catch (err) { $("#wxTest").textContent = "⚠ " + err.message; }
  }}, el("div", {class: "grow"}, el("div", {class: "name", text: x.name}), el("div", {class: "meta", text: x.label})),
     el("span", {class: "btn small", text: "Wählen"}))));
});
function calColor(i, src) { return src.color ? hex(src.color) : ["#4c8dff", "#3ecf7e", "#f0a93b", "#eb5a96", "#a078ff", "#3cc8dc"][i % 6]; }
function renderCalSources() {
  const list = UI.sdraft.calendar.sources, box = $("#calSources");
  if (!list.length) { box.replaceChildren(el("div", {class: "empty", text: "Noch kein Kalender eingetragen."})); return; }
  box.replaceChildren(...list.map((src, i) => {
    const info = el("div", {class: "hint", style: {margin: "0 0 10px", gridColumn: "1 / -1"}});
    return el("div", {},
      el("div", {class: "srcrow"},
        el("input", {type: "text", value: src.name || "", placeholder: "Name", oninput: e => { src.name = e.target.value; touchSettings(); }}),
        el("input", {type: "url", value: src.url || "", placeholder: "https://…/basic.ics", oninput: e => { src.url = e.target.value.trim(); touchSettings(); }}),
        el("input", {type: "text", value: src.user || "", placeholder: "Benutzer (optional)", autocomplete: "off", oninput: e => { src.user = e.target.value.trim(); touchSettings(); }}),
        el("input", {type: "password", value: src.password || "", placeholder: "Passwort", autocomplete: "new-password", oninput: e => { src.password = e.target.value; touchSettings(); }}),
        el("input", {type: "color", value: calColor(i, src), title: "Farbe", oninput: e => { src.color = rgb(e.target.value); touchSettings(); }}),
        el("div", {class: "row", style: {flexWrap: "nowrap", gap: "4px"}},
          el("button", {class: "btn small", onclick: async () => {
            if (!src.url) { toast("Bitte zuerst die Adresse eintragen.", true); return; }
            info.textContent = "prüfe …";
            try { const r = await api("/api/calendar/test", {body: src});
              info.replaceChildren(`✓ ${r.count} Termine in den nächsten 30 Tagen`, ...(r.calendars && r.calendars.length ? [el("br"), `aus ${r.calendars.length} Kalendern: ${r.calendars.join(", ")}`] : []), ...r.next.map(t => [el("br"), "• " + t]).flat()); }
            catch (err) { info.textContent = "⚠ " + err.message; }
          }}, "Testen"),
          el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => {
            if (confirm(`Kalender „${src.name || src.url}“ entfernen?`)) { list.splice(i, 1); touchSettings(); renderCalSources(); } }}, "✕"))),
      info);
  }));
}
$("#calAdd").addEventListener("click", () => { UI.sdraft.calendar.sources.push({name: "", url: "", user: "", password: ""}); touchSettings(); renderCalSources(); });
$("#calDays").addEventListener("change", e => { UI.sdraft.calendar.days = parseInt(e.target.value); touchSettings(); });
$("#calRemind").addEventListener("change", e => { UI.sdraft.calendar.remind = parseInt(e.target.value); touchSettings(); });
$("#ntOn").addEventListener("change", e => { UI.sdraft.notifications.enabled = e.target.checked; touchSettings(); });
$("#ntSec").addEventListener("input", e => { UI.sdraft.notifications.seconds = Math.max(2, Math.min(30, parseInt(e.target.value) || 6)); touchSettings(); });
$("#ntIgnore").addEventListener("input", e => { UI.sdraft.notifications.ignore = e.target.value; touchSettings(); });
$("#ntTest").addEventListener("click", async () => {
  try { await api("/api/notify/test", {body: {}}); toast("Testbenachrichtigung gesendet – schau aufs Display."); }
  catch (e) { toast(e.message, true); }
});
async function refreshHardware() {
  try {
    const r = await api("/api/hardware"), s = r.sensors, t = v => v === null || v === undefined ? "nicht gefunden" : `${Math.round(v)} °C`;
    $("#hwInfo").replaceChildren(
      el("div", {text: "CPU"}), el("div", {text: t(s.cpu)}),
      el("div", {text: "Grafikkarte"}), el("div", {text: t(s.gpu) + (s.gpu_load !== null && s.gpu_load !== undefined ? ` · ${s.gpu_load} % Last` : "")}),
      el("div", {text: "SSD"}), el("div", {text: t(s.nvme)}),
      el("div", {text: "Lüfter"}), el("div", {text: s.fans.length ? s.fans.map(f => `${f[0]}: ${f[1]} U/min`).join(" · ") : "keine gefunden"}),
      el("div", {text: "Laufwerke"}), el("div", {text: r.disks.map(d => `${d[0]} ${d[1]} % von ${d[2]} GB`).join(" · ")}));
  } catch (e) { $("#hwInfo").replaceChildren(el("div", {class: "warnbox", text: e.message})); }
}
$("#hwRefresh").addEventListener("click", refreshHardware);

// ---------------------------------------------------------------- Speichern (Einstellungen + Sender)
function renderSavebar() {
  const show = UI.sDirty && ["radio", "snippets", "settings", "slides", "info", "service"].includes(UI.tab);
  $("#savebar").classList.toggle("show", show);
}
$("#saveSettings").addEventListener("click", async () => {
  const bad = UI.sdraft.stations.find(s => s.url && !/^https?:\/\//i.test(s.url));
  if (bad) { toast(`Die Stream-Adresse von „${bad.name || bad.url}“ muss mit http:// oder https:// beginnen.`, true); return; }
  const empty = UI.sdraft.stations.filter(s => !s.url).length;
  try {
    const r = await api("/api/settings", {body: {settings: UI.sdraft}});
    S.settings = r.settings; S.mtimes.settings = r.mtime; UI.sdraft = clone(r.settings); UI.sDirty = false;
    markTabs(); renderAll();
    toast("Gespeichert – der Treiber übernimmt die Einstellungen sofort." + (empty ? ` (${empty} Sender ohne Adresse entfernt)` : ""));
  } catch (e) { toast(e.message, true); }
});
$("#discardSettings").addEventListener("click", () => {
  UI.sdraft = clone(S.settings); UI.sDirty = false; markTabs(); renderAll(); refreshPreview();
});

// ---------------------------------------------------------------- Dienst & Sicherung
function renderServiceInfo() {
  const s = S.service || {}, active = s.active === "active";
  $("#svcPill").replaceChildren(el("span", {class: "dot " + (active ? "ok" : (s.active === "activating" ? "warn" : "bad"))}),
    el("span", {text: active ? "Treiber läuft" : s.active === "activating" ? "Treiber startet …" : "Treiber gestoppt"}));
  $("#svcActive").replaceChildren(el("span", {class: "dot " + (active ? "ok" : "bad")}), " ",
    {active: "läuft", inactive: "gestoppt", failed: "abgestürzt", activating: "startet"}[s.active] || s.active || "?");
  const en = s.enabled === "enabled";
  $("#svcEnabled").textContent = en ? "an (startet bei der Anmeldung)" : "aus";
  $("#toggleAutostart").textContent = en ? "Autostart ausschalten" : "Autostart einschalten";
  $("#toolMpv").innerHTML = ""; $("#toolMpv").append(S.tools.mpv ? "installiert" : el("span", {}, "fehlt – ", el("code", {text: "sudo apt install mpv"})));
  $("#toolPlayerctl").innerHTML = ""; $("#toolPlayerctl").append(S.tools.playerctl ? "installiert" : el("span", {}, "fehlt – ", el("code", {text: "sudo apt install playerctl"})));
  $("#toolMpris").innerHTML = ""; $("#toolMpris").append(S.tools.mpris ? "aktiv (mpv-mpris installiert)" : el("span", {}, "aus – ", el("code", {text: "sudo apt install mpv-mpris"})));
}
async function refreshService() {
  try { const r = await api("/api/service"); S.service = r.status; renderServiceInfo(); $("#log").textContent = r.log || "(kein Protokoll)";
    const lg = $("#log"); lg.scrollTop = lg.scrollHeight; } catch (e) {}
  try { const v = await api("/api/versions");
    $("#versions").replaceChildren(
      el("div", {text: "Treiber"}), el("div", {}, v.driver, v.driver !== v.driver_running
        ? el("span", {class: "muted", text: " (Verwaltung kennt noch " + v.driver_running + " – wird beim nächsten Start übernommen)"}) : ""),
      el("div", {text: "Verwaltung"}), el("div", {text: v.gui}),
      el("div", {text: "Alte Versionen"}), el("div", {}, el("code", {text: v.backups})));
  } catch (e) {}
  try { const b = await api("/api/backupinfo");
    $("#backupFiles").replaceChildren("Enthält: ", ...b.files.map((f, i) => [i ? ", " : "", el("code", {text: "~/" + f})]).flat()); } catch (e) {}
}
document.querySelectorAll("[data-svc]").forEach(b => b.addEventListener("click", () => svc(b.dataset.svc)));
$("#toggleAutostart").addEventListener("click", () => svc(S.service.enabled === "enabled" ? "disable" : "enable"));
$("#logRefresh").addEventListener("click", refreshService);
async function svc(action) {
  try { const r = await api("/api/service", {body: {action}}); S.service = r.status; renderServiceInfo();
    $("#log").textContent = r.log || ""; const lg = $("#log"); lg.scrollTop = lg.scrollHeight;
    toast({start: "Treiber gestartet", stop: "Treiber gestoppt", restart: "Treiber neu gestartet",
      enable: "Autostart eingeschaltet", disable: "Autostart ausgeschaltet"}[action]); }
  catch (e) { toast(e.message, true); }
}
$("#restoreFile").addEventListener("change", async e => {
  const f = e.target.files[0]; e.target.value = ""; if (!f) return;
  if (!confirm(`Sicherung „${f.name}“ einspielen? Die aktuellen Dateien werden vorher automatisch gesichert.`)) return;
  try {
    const body = await f.arrayBuffer();
    const info = await api("/api/restore?inspect=1", {body, raw: true});
    let programs = false;
    if (info.programs.length)
      programs = confirm("Die Sicherung enthält auch Programmdateien und KDE-Kurzbefehle:\n\n" +
        info.programs.map(p => "~/" + p).join("\n") +
        "\n\nDiese nur einspielen, wenn die Sicherung sicher von dir stammt (z. B. nach einer Neuinstallation)." +
        "\n\nOK = mit einspielen · Abbrechen = nur Einstellungen und Makros");
    const r = await api("/api/restore?programs=" + (programs ? "1" : "0"), {body, raw: true});
    toast(`Wiederhergestellt: ${r.restored.length} Dateien. Treiber neu starten, damit alles greift.`);
    await loadState(); refreshService();
  } catch (err) { toast(err.message, true); }
});
function toBase64(buf) {
  const bytes = new Uint8Array(buf); let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
$("#updateFile").addEventListener("change", async e => {
  const files = [...e.target.files]; e.target.value = ""; if (!files.length) return;
  if (UI.draftDirty || UI.sDirty) { toast("Bitte zuerst die offenen Änderungen speichern oder verwerfen.", true); return; }
  if (!confirm(`${files.map(f => f.name).join(" und ")} einspielen? Treiber bzw. Verwaltung werden dabei neu gestartet.`)) return;
  const box = $("#updateResult"); box.replaceChildren(el("span", {class: "muted", text: "Spiele Update ein …"}));
  let r;
  try {
    const payload = [];
    for (const f of files) payload.push({name: f.name, data: toBase64(await f.arrayBuffer())});
    r = await api("/api/update", {body: {files: payload}});
  } catch (err) { box.replaceChildren(el("div", {class: "warnbox", text: err.message})); return; }
  box.replaceChildren(...r.installed.map(x => el("div", {class: "hint", style: {margin: "2px 0"}},
    "✓ ", el("b", {text: x.component === "driver" ? "Treiber" : "Verwaltung"}), ` aktualisiert: ${x.old} → ${x.new}`,
    x.warning ? el("span", {style: {color: "var(--danger)"}, text: " – " + x.warning}) : "")));
  if (!r.restart_gui) { toast("Update eingespielt, der Treiber wurde neu gestartet."); refreshService(); return; }
  $("#ovTitle").textContent = "Verwaltung wird neu gestartet …";
  $("#ovText").textContent = "Einen Moment bitte, die Seite lädt gleich von selbst neu.";
  $("#overlay").classList.add("show");
  const until = Date.now() + 30000;
  await new Promise(res => setTimeout(res, 1500));
  while (Date.now() < until) {
    try { const p = await fetch("/api/poll", {headers: {"X-Token": TOKEN}}); if (p.ok) { location.reload(); return; } } catch (err) {}
    await new Promise(res => setTimeout(res, 700));
  }
  $("#ovTitle").textContent = "Neustart dauert ungewöhnlich lange";
  $("#ovText").textContent = "Bitte die Verwaltung über das Anwendungsmenü neu öffnen.";
});
function renderPaths() {
  $("#backupLink").href = "/api/backup?token=" + encodeURIComponent(TOKEN);
  const p = S.paths || {};
  $("#paths").replaceChildren(
    el("div", {text: "Tastenbelegung"}), el("div", {}, el("code", {text: p.macros || ""})),
    el("div", {text: "Einstellungen"}), el("div", {}, el("code", {text: p.settings || ""})),
    el("div", {text: "Treiber"}), el("div", {}, el("code", {text: p.driver || ""})));
}
// Automatische Sicherung
const AB_HINTS = {
  folder: "Ein Ordner auf diesem Rechner. Ein NAS muss dafür eingebunden sein (z. B. per /etc/fstab unter /mnt/nas); ein Nextcloud-Ordner, den der Nextcloud-Client synchronisiert, funktioniert direkt (z. B. ~/Nextcloud/Sicherungen). Hinweis: Freigaben, die nur in Dolphin geöffnet sind (smb://…), sind kein Ordner – dafür „NAS – Windows-Freigabe“ wählen.",
  nextcloud: "Adresse deiner Nextcloud (z. B. https://cloud.example.de – auch die Adresse aus dem Browser geht), dein Benutzername und am besten ein App-Passwort: Nextcloud → Persönliche Einstellungen → Sicherheit → „Neues App-Passwort erstellen“. Der Ordner wird bei Bedarf angelegt.",
  smb: "Freigabe und Ordner wie im Dateimanager, z. B. \\\\nas\\backup\\G19s oder smb://nas/backup/G19s – der Ordner muss vorhanden sein. Benötigt das Programm smbclient (sudo apt install smbclient). Ohne smbclient wird KDEs kioclient benutzt – dann die Freigabe einmal in Dolphin öffnen und das Passwort speichern (das Passwort hier wird aus Sicherheitsgründen nicht an kioclient übergeben).",
  webdav: "Vollständige Adresse des Ordners, z. B. https://nas.local:5006/home/Sicherungen (Synology: Paket „WebDAV Server“, QNAP: WebDAV in den Freigabe-Einstellungen). Der Ordner muss vorhanden sein.",
};
const AB_URL = {nextcloud: ["Adresse der Nextcloud", "https://cloud.example.de"], smb: ["Freigabe und Ordner", "\\\\nas\\backup\\G19s"],
  webdav: ["Adresse des Ordners", "https://nas.local:5006/home/Sicherungen"]};
function renderAutoBackup() {
  const sd = UI.sdraft; if (!sd) return;
  const b = sd.backup, t = b.target || "folder";
  $("#abOn").checked = !!b.enabled; $("#abTarget").value = t;
  $("#abFolder").value = b.folder; $("#abDays").value = String(b.days); $("#abKeep").value = b.keep;
  $("#abFolderBox").style.display = t === "folder" ? "" : "none";
  $("#abRemoteBox").style.display = t === "folder" ? "none" : "";
  $("#abDirBox").style.display = t === "nextcloud" ? "" : "none";
  if (t !== "folder") {
    $("#abUrlLabel").textContent = AB_URL[t][0]; $("#abUrl").placeholder = AB_URL[t][1];
    $("#abPwLabel").textContent = t === "nextcloud" ? "App-Passwort" : "Passwort";
    $("#abUrl").value = b.url || ""; $("#abUser").value = b.user || ""; $("#abPw").value = b.password || "";
    $("#abDir").value = b.remote_dir || "";
  }
  $("#abHint").textContent = AB_HINTS[t];
}
async function loadBackupStatus() {
  try {
    const r = await api("/api/backup/status");
    $("#abStatus").replaceChildren(r.error ? el("div", {class: "warnbox", text: "Letzter Versuch fehlgeschlagen: " + r.error}) :
      r.last ? el("span", {text: `Letzte Sicherung: ${new Date(r.last * 1000).toLocaleString("de-DE")} – ${r.file}`}) : el("span", {text: "Noch keine automatische Sicherung."}));
  } catch (e) { /* nicht kritisch */ }
}
$("#abOn").addEventListener("change", e => { UI.sdraft.backup.enabled = e.target.checked; touchSettings(); });
$("#abFolder").addEventListener("input", e => { UI.sdraft.backup.folder = e.target.value.trim(); touchSettings(); });
$("#abTarget").addEventListener("change", e => { UI.sdraft.backup.target = e.target.value; touchSettings(); renderAutoBackup(); });
for (const [id, key] of [["#abUrl", "url"], ["#abUser", "user"], ["#abPw", "password"], ["#abDir", "remote_dir"]])
  $(id).addEventListener("input", e => { UI.sdraft.backup[key] = key === "password" ? e.target.value : e.target.value.trim(); touchSettings(); });
$("#abDays").addEventListener("change", e => { UI.sdraft.backup.days = parseInt(e.target.value); touchSettings(); });
$("#abKeep").addEventListener("input", e => { UI.sdraft.backup.keep = Math.max(1, Math.min(100, parseInt(e.target.value) || 8)); touchSettings(); });
$("#abBrowse").addEventListener("click", () => browseFolder(UI.sdraft.backup.folder || "~", {box: "#abBrowser", images: false,
  pick: path => { UI.sdraft.backup.folder = path; touchSettings(); renderAutoBackup(); toast("Ordner übernommen – zum Übernehmen unten speichern."); }}));
function abReady() {
  const b = UI.sdraft.backup;
  if ((b.target || "folder") === "folder" ? !b.folder : !b.url) { toast(b.target === "folder" || !b.target ? "Bitte zuerst einen Ordner wählen." : "Bitte zuerst die Adresse angeben.", true); return null; }
  return b;
}
$("#abNow").addEventListener("click", async () => {
  const b = abReady(); if (!b) return;
  $("#abNow").disabled = true;
  try { const r = await api("/api/backup/now", {body: {backup: b}}); toast("Gesichert: " + r.path); }
  catch (e) { toast(e.message, true); }
  finally { $("#abNow").disabled = false; loadBackupStatus(); }
});
$("#abTest").addEventListener("click", async () => {
  const b = abReady(); if (!b) return;
  $("#abTest").disabled = true; $("#abStatus").textContent = "Teste …";
  try { const r = await api("/api/backup/test", {body: {backup: b}});
    $("#abStatus").replaceChildren(el("div", {class: "okbox", text: "✓ " + r.message})); }
  catch (e) { $("#abStatus").replaceChildren(el("div", {class: "warnbox", text: "✗ " + e.message})); }
  finally { $("#abTest").disabled = false; }
});

// ---------------------------------------------------------------- Abgleich im Hintergrund
$("#extReload").addEventListener("click", async () => {
  const d = await api("/api/state"); S.macros = d.macros; S.mtimes.macros = d.mtimes.macros; S.active = d.active;
  UI.pidx = Math.min(UI.pidx, S.macros.profiles.length - 1);
  afterProfileChange(); $("#extBanner").classList.remove("show");
});
async function poll() {
  let d; try { d = await api("/api/poll"); } catch (e) { return; }
  if (d.service.active !== S.service.active || d.service.enabled !== S.service.enabled) { S.service = d.service; renderServiceInfo(); }
  if (d.mtimes.macros !== S.mtimes.macros) {
    if (UI.draftDirty) $("#extBanner").classList.add("show");
    else { const s = await api("/api/state"); S.macros = s.macros; S.mtimes.macros = s.mtimes.macros; S.active = s.active;
      UI.pidx = Math.min(UI.pidx, S.macros.profiles.length - 1);
      afterProfileChange(); toast("Tastenbelegung wurde aktualisiert (z. B. durch MR-Aufnahme)."); }
  }
  if (d.active !== S.active) { S.active = d.active; renderProfileCard(); }
  if (d.mtimes.settings !== S.mtimes.settings && !UI.sDirty) {
    const s = await api("/api/state"); S.settings = s.settings; S.mtimes.settings = s.mtimes.settings; UI.sdraft = clone(S.settings); renderAll();
  }
  const cur = d.radio ? d.radio.url : null;
  if ((UI.testing && UI.testing.url) !== cur) { UI.testing = d.radio; renderStations(); renderResults(); }
}
// Abgleich alle 3 s; im Hintergrund-Tab nur alle 15 s (hält die Sitzung am Leben, spart Prozessaufrufe)
let pollHidden = 0;
setInterval(() => { if (!document.hidden || ++pollHidden % 5 === 0) poll(); }, 3000);
window.addEventListener("beforeunload", e => {
  fetch("/api/bye", {method: "POST", headers: {"X-Token": TOKEN}, keepalive: true}).catch(() => {});
  if (UI.draftDirty || UI.sDirty) { e.preventDefault(); e.returnValue = ""; }
});
if (!TOKEN) lost("Sitzung fehlt", "Bitte die Verwaltung über das Anwendungsmenü „G19s-Verwaltung“ öffnen.");
else loadState().catch(e => toast(e.message, true));

</script>
</body>
</html>
'''

if __name__ == "__main__":
    main()


# G19S-DATEIENDE (diese Zeile zeigt, dass die Datei vollständig ist)
