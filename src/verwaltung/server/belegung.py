"""Tastenbelegung und Einstellungen lesen/prüfen (die Regeln stehen im Treiber), Tastenkatalog für den Editor."""


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
