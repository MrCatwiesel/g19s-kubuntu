"""Kern der Hauptanwendung: Aufbau aller Teile, Zustand, Profile/Ebenen/Seiten,
Beleuchtung und Nachtmodus, Einstellungen neu laden, Hilfen für Menüs.

Der gesamte Laufzeitzustand steht als Attribut an einer Stelle:
    layer        aktive Ebene M1/M2/M3            prof_idx   aktives Profil (Index)
    page         angezeigte Seite (Index in PAGE_IDS)
    menu         offenes Menü (menue_logik) oder None
    flash        Einblendung (Zeichenfunktion, bis-Zeitpunkt) oder None
    rec          laufende Makroaufnahme oder None
    next_draw    Zeitpunkt der nächsten Displayaktualisierung

Threads: Die Hauptschleife besitzt den Zustand. Hintergrund-Threads (Lautstärke,
Mikrofon, Radio starten) melden sich nur über popup()/show() und einfache
Zuweisungen; Benachrichtigungen laufen über die Warteschlange popups.
"""
import os
import sys
import threading
import time
from collections import deque


class AppCore:
    def __init__(self, args):
        from evdev import UInput, ecodes as e
        self.args, self.e = args, e
        migrate_files()                     # ältere settings.json/macros.json umstellen
        self.fkeys = [getattr(e, f"KEY_F{n}") for n in range(13, 25)]
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
            time.sleep(5)

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
