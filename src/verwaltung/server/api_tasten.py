"""HTTP-Routen: Tastenbelegung, Profile, Einstellungen, Vorschau."""


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
