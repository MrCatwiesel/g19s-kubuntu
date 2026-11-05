"""Menüs und Vollbild-Ansichten am Display: Tastenbehandlung und Zeichnen.

Ein offenes Menü bekommt alle Displaytasten. on_key() verarbeitet einen Report
(pressed = neu gedrückte Tasten, kann auch 0 sein), draw() liefert das Bild.
Menüs schließen sich nach MENU_TIMEOUT Sekunden ohne Tastendruck
(außer der Timer-Anzeige).
"""

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
    """SETTINGS (lang; kurz außerhalb der Uhrseite): Profil wählen."""
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


def option_list(section, item):
    """Am Display änderbare Optionen eines Zifferblatts ("clock") bzw. Stils ("visual");
    die Städteliste der Weltuhr nur in der Verwaltung."""
    src = CLOCK_OPTIONS if section == "clock" else VISUAL_OPTIONS
    return [o for o in src.get(item, []) if o["type"] in ("bool", "choice", "color")]


def clock_option_list(face):
    return option_list("clock", face)


def item_options(settings, section, item):
    """Aktuelle Werte der Optionen eines Zifferblatts bzw. Stils."""
    return clock_options(settings, item) if section == "clock" else visual_options(settings, item)


def _cycle(values, current, step):
    """Nächster (step=1) bzw. voriger (-1) Wert mit Umlauf; ein unbekannter Wert springt an den Anfang/das Ende."""
    try:
        i = values.index(current)
    except ValueError:
        i = -1 if step > 0 else 0
    return values[(i + step) % len(values)]


def option_next(opt, value, step):
    """Neuer Wert einer Zifferblatt-Option nach ◄ (step=-1) bzw. ► / OK (step=1)."""
    if opt["type"] == "bool":
        return not value
    if opt["type"] == "choice":
        return _cycle([c[0] for c in opt["choices"]], value, step)
    return _cycle([c for c, _ in CLOCK_COLOR_CHOICES], value, step)


def option_text(opt, value):
    """Wert einer Zifferblatt-Option als Text fürs Display und das Protokoll."""
    if opt["type"] == "bool":
        return "an" if value else "aus"
    if opt["type"] == "choice":
        return next((label for key, label in opt["choices"] if key == value), str(value))
    if value is None:
        return opt.get("none_label") or "Standard"
    return next((name for c, name in CLOCK_COLOR_CHOICES if c == list(value)), "eigene Farbe")


class ClockMenu(Menu):
    """Uhrseite, MENU oder SETTINGS kurz: Zifferblatt für dieses Profil und diese Ebene wählen."""
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
        face = items[self.cursor]["face"]
        if pressed & LKEY_BITS["OK"]:
            app.menu = None
            app.set_clock_face(face)
        elif pressed & LKEY_BITS["RIGHT"] and clock_option_list(face):
            app.menu = OptionsMenu("clock", face, self.cursor)  # ► Optionen des markierten Zifferblatts
        elif pressed & LKEY_BITS["RIGHT"]:
            self.touch()                    # Zifferblatt ohne Optionen: nichts zu tun
        elif pressed & CLOSE_KEYS:
            app.menu = None
        elif pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        """Vorschau: das markierte Zifferblatt läuft live, darüber Name und Position."""
        items = self.items(app)
        self.cursor = min(self.cursor, len(items) - 1)
        it, r = items[self.cursor], app.renderer
        r.clock_face = it["face"]           # app.draw() setzt beim nächsten Bild wieder das eingestellte
        img = r.render(PAGE_IDS.index("clock"), app.layer, {})
        hint = ("▲▼ blättern · OK übernehmen · ► Optionen" if clock_option_list(it["face"])
                else "▲▼ blättern · OK übernehmen · BACK zurück")
        return r.render_face_preview(img, it["label"], self.cursor + 1, len(items), bool(it["mark"]),
                                     PROFILE_COLOR[app.layer], hint)


class OptionsMenu(Menu):
    """Zifferblatt- bzw. Stil-Liste, ►: Optionen ändern (jede Änderung wird gleich gespeichert und ist
    in der Vorschau zu sehen). BACK zurück zur Liste, MENU/SETTINGS schließen.
    section = "clock" (Zifferblatt der Uhr) oder "visual" (Stil der Visualisierung)."""

    def __init__(self, section, item, back_cursor):
        super().__init__()
        self.section, self.item, self.back = section, item, back_cursor
        self.kind = "clock_options" if section == "clock" else "visual_options"

    def on_key(self, app, pressed):
        opts = option_list(self.section, self.item)
        self.cursor = self.step(self.cursor, pressed, len(opts))
        step = -1 if pressed & LKEY_BITS["LEFT"] else 1 if pressed & (LKEY_BITS["RIGHT"] | LKEY_BITS["OK"]) else 0
        if step:
            opt = opts[self.cursor]
            value = item_options(app.settings(), self.section, self.item)[opt["key"]]
            app.set_item_option(self.section, self.item, opt, option_next(opt, value, step))
        elif pressed & LKEY_BITS["BACK"]:
            app.menu = (ClockMenu if self.section == "clock" else VisualMenu)(app)
            app.menu.cursor = self.back
        elif pressed & (LKEY_BITS["MENU"] | LKEY_BITS["SETTINGS"]):
            app.menu = None
        if pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        opts = option_list(self.section, self.item)
        self.cursor = min(self.cursor, len(opts) - 1)
        opt = opts[self.cursor]
        value = item_options(app.settings(), self.section, self.item)[opt["key"]]
        r = app.renderer
        if self.section == "clock":
            r.clock_face = self.item        # app.draw() setzt beim nächsten Bild wieder das eingestellte
            name, page_id = CLOCK_FACES[self.item], "clock"
        else:
            r.visual_style = self.item
            name, page_id = VISUAL_STYLES[self.item], "visual"
        img = r.render(PAGE_IDS.index(page_id), app.layer, {})
        swatch = tuple(value) if opt["type"] == "color" and value else None
        return r.render_option_overlay(img, name, opt["label"], option_text(opt, value),
                                       self.cursor + 1, len(opts), swatch, PROFILE_COLOR[app.layer])


class VisualMenu(Menu):
    """Visualisierung, MENU oder SETTINGS kurz: Stil wählen (Vorschau läuft live), ► Optionen."""
    kind = "visuals"

    def __init__(self, app):
        super().__init__()
        styles = list(VISUAL_STYLES)
        cur = app.visual_style()
        self.cursor = styles.index(cur) if cur in styles else 0

    @staticmethod
    def items(app):
        cur = app.visual_style()
        return [{"label": label, "style": st, "mark": "▶" if st == cur else ""} for st, label in VISUAL_STYLES.items()]

    def on_key(self, app, pressed):
        items = self.items(app)
        self.cursor = self.step(self.cursor, pressed, len(items))
        style = items[self.cursor]["style"]
        if pressed & LKEY_BITS["OK"]:
            app.menu = None
            app.set_visual_style(style)
        elif pressed & LKEY_BITS["RIGHT"] and option_list("visual", style):
            app.menu = OptionsMenu("visual", style, self.cursor)
        elif pressed & CLOSE_KEYS:
            app.menu = None
        elif pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        items = self.items(app)
        self.cursor = min(self.cursor, len(items) - 1)
        it, r = items[self.cursor], app.renderer
        r.visual_style = it["style"]        # app.draw() setzt beim nächsten Bild wieder den eingestellten
        img = r.render(PAGE_IDS.index("visual"), app.layer, {})
        return r.render_face_preview(img, it["label"], self.cursor + 1, len(items), bool(it["mark"]),
                                     PROFILE_COLOR[app.layer], "▲▼ blättern · OK übernehmen · ► Optionen",
                                     title="Stil")


class QuickMenu(Menu):
    """MENU auf Seiten ohne eigene MENU-Funktion (Makros, Wetter, Hardware): häufige Einstellungen."""
    kind = "quick"

    @staticmethod
    def items(app):
        night = bool((app.settings().get("night") or {}).get("enabled"))
        return [{"id": "brightness", "label": "Helligkeit", "sub": f"◄ {app.day_brightness()} % ►"},
                {"id": "night", "label": "Nachtmodus (Zeitplan)", "sub": "an" if night else "aus"},
                {"id": "slides", "label": "Diashow", "sub": "pausiert" if app.slideshow.paused else "läuft"},
                {"id": "saver", "label": "Bildschirmschoner jetzt"},
                {"id": "profile", "label": "Profil wählen"}]

    def on_key(self, app, pressed):
        items = self.items(app)
        self.cursor = self.step(self.cursor, pressed, len(items))
        it = items[self.cursor]["id"]
        step = -1 if pressed & LKEY_BITS["LEFT"] else 1 if pressed & (LKEY_BITS["RIGHT"] | LKEY_BITS["OK"]) else 0
        if pressed & (LKEY_BITS["BACK"] | LKEY_BITS["MENU"] | LKEY_BITS["SETTINGS"]):
            app.menu = None
        elif step and it == "brightness":
            value = max(10, min(100, (app.day_brightness() + 5) // 10 * 10 + 10 * step))
            if app.save_setting(["brightness"], value):
                app.log(f"Helligkeit: {value} %")
        elif step and it == "night":
            on = not (app.settings().get("night") or {}).get("enabled")
            if app.save_setting(["night", "enabled"], on):
                app.log(f"Nachtmodus (Zeitplan): {'an' if on else 'aus'}")
                app.update_night(force=True)
        elif step and it == "slides":
            app.slideshow.command("toggle")
            app.log(f"Diashow: {'pausiert' if app.slideshow.paused else 'läuft'}")
        elif pressed & LKEY_BITS["OK"] and it == "saver":
            app.menu = None
            app.start_screensaver()
        elif pressed & LKEY_BITS["OK"] and it == "profile":
            app.menu = ProfileMenu(app.prof_idx)
        if pressed:
            self.touch()
        app.next_draw = 0

    def draw(self, app, now):
        items = self.items(app)
        self.cursor = min(self.cursor, len(items) - 1)
        return app.renderer.render_list_menu("Schnellmenü", items, self.cursor,
                                             "▲▼ wählen · ◄► / OK ändern · BACK zurück",
                                             color=PROFILE_COLOR[app.layer])


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
    """Liste, aus der OK einen Eintrag ausführt und schließt (Sender, Textbausteine).
    keep_open: Liste bleibt nach OK offen (mehrfach ausführen, BACK schließt)."""
    keep_open = False

    def items(self, app):
        raise NotImplementedError

    def choose(self, app, item):
        raise NotImplementedError

    def on_key(self, app, pressed):
        items = self.items(app)
        self.cursor = self.step(self.cursor, pressed, max(1, len(items)))
        if pressed & LKEY_BITS["OK"] and items:
            if self.keep_open:
                self.touch()
            else:
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
    """G-Taste „Textbausteine“: Text wählen und einfügen (mit keep_open bleibt die Liste offen)."""
    kind = "snippets"

    def __init__(self, group, title, keep_open=False):
        super().__init__()
        self.group, self.title, self.keep_open = group, title, keep_open

    def items(self, app):
        return app.snippet_list(self.group)

    def choose(self, app, item):
        if not insert_text(app, item["text"], item.get("paste"), "Textbaustein"):
            app.log("Es läuft bereits ein Makro – ignoriert")
        else:
            app.log(f"Textbaustein: {item['name']}")

    def draw(self, app, now):
        items = self.items(app)
        self.cursor = min(self.cursor, max(0, len(items) - 1))
        return app.renderer.render_list_menu(self.title or "Textbausteine", items, self.cursor,
                                             "▲▼ wählen · OK einfügen · BACK " + ("schließen" if self.keep_open else "zurück"),
                                             f"{len(items)}", PROFILE_COLOR[app.layer])


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
