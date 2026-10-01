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
        """Vorschau: das markierte Zifferblatt läuft live, darüber Name und Position."""
        items = self.items(app)
        self.cursor = min(self.cursor, len(items) - 1)
        it, r = items[self.cursor], app.renderer
        r.clock_face = it["face"]           # app.draw() setzt beim nächsten Bild wieder das eingestellte
        img = r.render(PAGE_IDS.index("clock"), app.layer, {})
        return r.render_face_preview(img, it["label"], self.cursor + 1, len(items), bool(it["mark"]),
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
        if not insert_text(app, item["text"], item.get("paste"), "Textbaustein"):
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
