"""Deutsches Tastaturlayout (QWERTZ): Text und Tastenkombinationen in Makroschritte übersetzen, Tastennamen."""


# --------------------------------------------------------------------------- #
# Deutsches Tastaturlayout (QWERTZ): Zeichen -> Tastenfolge
# evdev benennt Tasten nach ihrer Position auf der US-Tastatur.
# --------------------------------------------------------------------------- #
_S, _A = "KEY_LEFTSHIFT", "KEY_RIGHTALT"   # Umschalt, AltGr
DE_CHARS = {" ": ("KEY_SPACE",), "\n": ("KEY_ENTER",), "\t": ("KEY_TAB",)}
for _c in "abcdefghijklmnopqrstuvwx":
    DE_CHARS[_c] = (f"KEY_{_c.upper()}",)
    DE_CHARS[_c.upper()] = (_S, f"KEY_{_c.upper()}")
DE_CHARS.update({"y": ("KEY_Z",), "Y": (_S, "KEY_Z"), "z": ("KEY_Y",), "Z": (_S, "KEY_Y")})
for _c, _shifted in zip("1234567890", '!"§$%&/()='):
    DE_CHARS[_c] = (f"KEY_{_c}",)
    DE_CHARS[_shifted] = (_S, f"KEY_{_c}")
DE_CHARS.update({
    "ß": ("KEY_MINUS",), "?": (_S, "KEY_MINUS"), "\\": (_A, "KEY_MINUS"),
    "ü": ("KEY_LEFTBRACE",), "Ü": (_S, "KEY_LEFTBRACE"),
    "+": ("KEY_RIGHTBRACE",), "*": (_S, "KEY_RIGHTBRACE"),
    "ö": ("KEY_SEMICOLON",), "Ö": (_S, "KEY_SEMICOLON"),
    "ä": ("KEY_APOSTROPHE",), "Ä": (_S, "KEY_APOSTROPHE"),
    "#": ("KEY_BACKSLASH",), "'": (_S, "KEY_BACKSLASH"),
    "<": ("KEY_102ND",), ">": (_S, "KEY_102ND"), "|": (_A, "KEY_102ND"),
    ",": ("KEY_COMMA",), ";": (_S, "KEY_COMMA"),
    ".": ("KEY_DOT",), ":": (_S, "KEY_DOT"),
    "-": ("KEY_SLASH",), "_": (_S, "KEY_SLASH"),
    "°": (_S, "KEY_GRAVE"),
    "@": (_A, "KEY_Q"), "€": (_A, "KEY_E"), "µ": (_A, "KEY_M"),
    "²": (_A, "KEY_2"), "³": (_A, "KEY_3"),
    "{": (_A, "KEY_7"), "[": (_A, "KEY_8"), "]": (_A, "KEY_9"), "}": (_A, "KEY_0"),
})
# Tottasten: Taste drücken, danach Leertaste, damit das Zeichen allein erscheint
DE_DEAD = {"^": ("KEY_GRAVE",), "´": ("KEY_EQUAL",), "`": (_S, "KEY_EQUAL"),
           "~": (_A, "KEY_RIGHTBRACE")}


# Anzeigenamen der Tasten auf einer deutschen Tastatur
KEY_LABELS = {
    "KEY_LEFTCTRL": "Strg", "KEY_RIGHTCTRL": "Strg rechts", "KEY_LEFTSHIFT": "Umschalt",
    "KEY_RIGHTSHIFT": "Umschalt rechts", "KEY_LEFTALT": "Alt", "KEY_RIGHTALT": "AltGr",
    "KEY_LEFTMETA": "Meta", "KEY_RIGHTMETA": "Meta rechts", "KEY_COMPOSE": "Menü",
    "KEY_ENTER": "Enter", "KEY_KPENTER": "Enter (Ziffernblock)", "KEY_SPACE": "Leertaste",
    "KEY_TAB": "Tab", "KEY_BACKSPACE": "Rücktaste", "KEY_ESC": "Esc", "KEY_DELETE": "Entf",
    "KEY_INSERT": "Einfg", "KEY_HOME": "Pos1", "KEY_END": "Ende", "KEY_PAGEUP": "Bild ↑",
    "KEY_PAGEDOWN": "Bild ↓", "KEY_UP": "Pfeil ↑", "KEY_DOWN": "Pfeil ↓", "KEY_LEFT": "Pfeil ←",
    "KEY_RIGHT": "Pfeil →", "KEY_CAPSLOCK": "Feststelltaste", "KEY_NUMLOCK": "Num",
    "KEY_SCROLLLOCK": "Rollen", "KEY_SYSRQ": "Druck", "KEY_PRINT": "Druck", "KEY_PAUSE": "Pause",
    "KEY_Y": "Z", "KEY_Z": "Y", "KEY_SEMICOLON": "Ö", "KEY_APOSTROPHE": "Ä",
    "KEY_LEFTBRACE": "Ü", "KEY_RIGHTBRACE": "+", "KEY_MINUS": "ß", "KEY_EQUAL": "´",
    "KEY_BACKSLASH": "#", "KEY_GRAVE": "^", "KEY_102ND": "<", "KEY_COMMA": ",",
    "KEY_DOT": ".", "KEY_SLASH": "-",
    "KEY_MUTE": "Stumm", "KEY_VOLUMEUP": "Lauter", "KEY_VOLUMEDOWN": "Leiser",
    "KEY_PLAYPAUSE": "Play/Pause", "KEY_NEXTSONG": "Nächster Titel",
    "KEY_PREVIOUSSONG": "Vorheriger Titel", "KEY_STOPCD": "Stopp",
}
for _n in range(10):
    KEY_LABELS[f"KEY_KP{_n}"] = f"{_n} (Ziffernblock)"
KEY_LABELS.update({"KEY_KPPLUS": "+ (Ziffernblock)", "KEY_KPMINUS": "- (Ziffernblock)",
                   "KEY_KPASTERISK": "* (Ziffernblock)", "KEY_KPSLASH": "/ (Ziffernblock)",
                   "KEY_KPDOT": ", (Ziffernblock)"})


def key_label(name):
    name = str(name)
    if name in KEY_LABELS:
        return KEY_LABELS[name]
    short = name.replace("KEY_", "").replace("BTN_", "Maus ")
    return short if len(short) <= 3 else short.capitalize()


def text_to_steps(text):
    """Wandelt Text in Makroschritte um (deutsches Layout). Gibt (Schritte, unbekannte Zeichen) zurück."""
    steps, unknown = [], []
    for ch in text.replace("\r\n", "\n"):
        combo = DE_CHARS.get(ch) or DE_DEAD.get(ch)
        if not combo:
            if ch not in unknown:
                unknown.append(ch)
            continue
        steps += combo_to_steps(list(combo), first_wait=TEXT_DELAY_MS)
        if ch in DE_DEAD:
            steps.append([5, "KEY_SPACE", "tap"])
    return steps, unknown


def combo_to_steps(keys, first_wait=0):
    """Tastenkombination (z. B. ["KEY_LEFTCTRL", "KEY_C"]) als Schritte."""
    keys = [k for k in keys if k]
    if not keys:
        return []
    if len(keys) == 1:
        return [[first_wait, keys[0], "tap"]]
    steps = [[first_wait if i == 0 else 5, k, "down"] for i, k in enumerate(keys)]
    steps += [[TAP_MS if i == 0 else 5, k, "up"] for i, k in enumerate(reversed(keys))]
    return steps


def entry_steps(entry, log=print):
    """Liefert die abzuspielenden Schritte eines Eintrags (steps, text oder combo)."""
    if entry.get("text"):
        steps, unknown = text_to_steps(str(entry["text"]))
        if unknown:
            log(f"Zeichen ohne Tastenzuordnung übersprungen: {''.join(unknown)!r}")
        return steps
    if entry.get("combo"):
        return combo_to_steps(combo_keys(entry["combo"]))
    return entry.get("steps") or []


# --------------------------------------------------------------------------- #
# Makros: Speicherung, Aufnahme, Wiedergabe
# --------------------------------------------------------------------------- #
def key_name(code):
    from evdev import ecodes
    name = ecodes.KEY.get(code) or ecodes.BTN.get(code)
    if isinstance(name, (list, tuple)):
        name = name[0]
    return name or str(code)


def key_code(name):
    from evdev import ecodes
    if isinstance(name, int):
        return name
    name = str(name).strip()
    if name.isdigit():
        return int(name)
    if not name.startswith(("KEY_", "BTN_")):
        name = "KEY_" + name.upper()
    return ecodes.ecodes.get(name)


def compile_steps(macro, log=print):
    """Wandelt die Schritte eines Eintrags in (Pause_ms, Code, Wert)-Tupel um."""
    out = []
    for step in entry_steps(macro, log):
        try:
            wait, name, action = step
            wait = max(0, int(wait))
        except (TypeError, ValueError):
            log(f"Ungültiger Makroschritt übersprungen: {step!r}")
            continue
        code = key_code(name)
        if code is None:
            log(f"Unbekannte Taste im Makro übersprungen: {name!r}")
            continue
        action = str(action).lower()
        if action in ("down", "1"):
            out.append((wait, code, 1))
        elif action in ("up", "0"):
            out.append((wait, code, 0))
        elif action == "tap":
            out.append((wait, code, 1))
            out.append((TAP_MS, code, 0))
        else:
            log(f"Unbekannte Aktion {action!r} übersprungen (erlaubt: down, up, tap)")
    return out
