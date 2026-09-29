"""Tastenbelegung (macros.json) mit Profilen und Ebenen, Zustand (state.json), Beschriftung der Einträge."""


def entry_label(entry, settings=None):
    """Kurzbeschriftung einer Tastenbelegung für Display und Oberfläche."""
    if not isinstance(entry, dict):
        return ""
    if entry.get("name"):
        return str(entry["name"])
    if entry.get("open"):
        return domain_of(entry["open"])
    if entry.get("radio"):
        if entry["radio"] == "stop":
            return "Radio aus"
        for st in (settings or {}).get("stations", []):
            if st.get("url") == entry["radio"]:
                return st.get("name") or "Radio"
        return "Radio"
    if entry.get("media"):
        return MEDIA_ACTIONS.get(entry["media"], "Musik")
    if entry.get("volume"):
        return VOLUME_ACTIONS.get(entry["volume"], "Lautstärke")
    if entry.get("snippets"):
        grp = str(entry["snippets"])
        return "Textbausteine" if grp == "*" else grp
    if isinstance(entry.get("timer"), dict):
        return timer_label(entry["timer"])
    if entry.get("sleep"):
        return f"Einschlafen {entry['sleep']} min"
    if entry.get("mic"):
        return "Mikrofon"
    if entry.get("run"):
        return str(entry["run"]).split()[0]
    if entry.get("text"):
        return "Text"
    if entry.get("combo"):
        combo = entry["combo"]
        keys = combo if isinstance(combo, list) else str(combo).split("+")
        return "+".join(key_label(k.strip()) for k in keys)
    if entry.get("steps"):
        return "Makro"
    return ""


def valid_colors(colors):
    """Prüft {"M1": [r,g,b], …} und gibt eine bereinigte Kopie oder None zurück."""
    if not isinstance(colors, dict):
        return None
    out = {}
    for layer in LAYERS:
        c = colors.get(layer)
        if (isinstance(c, (list, tuple)) and len(c) == 3
                and all(isinstance(v, int) and 0 <= v <= 255 for v in c)):
            out[layer] = list(c)
    return out if len(out) == 3 else None


def normalize_macros(data):
    """Bringt macros.json ins Profilformat. Das alte Format (nur M1/M2/M3)
    wird zu „Profil 1“:
    {
      "profiles": [
        {"name": "Profil 1", "colors": {"M1": [r,g,b], …},
         "keys": {"M1": {"G5": {"name": …, "steps": [[0, "KEY_H", "tap"], …]}}, "M2": {…}}}
      ]
    }"""
    if isinstance(data, dict) and isinstance(data.get("profiles"), list):
        raw = data["profiles"]
    elif isinstance(data, dict):
        raw = [{"name": "Profil 1", "keys": {k: v for k, v in data.items() if k in LAYERS}}]
    else:
        raw = []
    profiles = []
    for p in raw[:MAX_PROFILES]:
        if not isinstance(p, dict):
            continue
        keys = p.get("keys") if isinstance(p.get("keys"), dict) else {}
        prof = {"name": str(p.get("name") or f"Profil {len(profiles) + 1}").strip()[:30],
                "keys": {l: keys[l] for l in LAYERS if isinstance(keys.get(l), dict) and keys[l]}}
        colors = valid_colors(p.get("colors"))
        if colors:
            prof["colors"] = colors
        pages = valid_profile_pages(p.get("pages"))
        if pages:
            prof["pages"] = pages
        faces = valid_clock_faces(p.get("clock"))
        if faces:
            prof["clock"] = faces
        profiles.append(prof)
    return {"profiles": profiles or [{"name": "Profil 1", "keys": {}}]}


def valid_profile_pages(pages):
    """Eigene Displayseiten eines Profils: {"M1": [...], "M2": [...], "M3": [...]} oder None."""
    if not isinstance(pages, dict):
        return None
    out = {}
    for layer in LAYERS:
        lst = pages.get(layer)
        lst = list(dict.fromkeys(x for x in (lst if isinstance(lst, list) else []) if x in PAGE_IDS))
        if lst:
            out[layer] = lst
    return out if len(out) == len(LAYERS) else None


def valid_clock_faces(faces):
    """Zifferblätter eines Profils je Ebene: {"M3": "station"} (Digitaluhr = kein Eintrag) oder None."""
    if not isinstance(faces, dict):
        return None
    out = {l: faces[l] for l in LAYERS if faces.get(l) in CLOCK_FACES and faces[l] != "digital"}
    return out or None


def migrate_clock_pages(settings_path=None, macros_path=None, log=print):
    """Version 2026.09.28-8/-9 hatte eigene Uhrenseiten (clock_chrono …). Daraus wird die Seite
    „Uhr“ mit dem passenden Zifferblatt (je Profil und Ebene in macros.json)."""
    settings_path, macros_path = settings_path or SETTINGS_FILE, macros_path or MACRO_FILE

    def read(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None

    def convert(lst, faces, layer):
        if not isinstance(lst, list):
            return lst
        out = []
        for p in lst:
            if p in OLD_CLOCK_PAGES:
                if layer:
                    faces.setdefault(layer, OLD_CLOCK_PAGES[p])
                p = "clock"
            if p not in out:
                out.append(p)
        return out

    def has_old(obj):
        text = json.dumps(obj)
        return any(f'"{p}"' in text for p in OLD_CLOCK_PAGES)

    settings, macros = read(settings_path), read(macros_path)
    global_faces = {}
    if settings and has_old([settings.get("pages"), settings.get("layer_pages"), settings.get("screensaver")]):
        if "pages" in settings:
            settings["pages"] = convert(settings["pages"], {}, None)
        lp = settings.get("layer_pages")
        if isinstance(lp, dict):
            settings["layer_pages"] = {k: convert(v, global_faces, k if k in LAYERS else None) for k, v in lp.items()}
        ss = settings.get("screensaver")
        if isinstance(ss, dict) and ss.get("page") in OLD_CLOCK_PAGES:
            ss["page"] = "clock"
        save_json(settings_path, settings, private=True)
        log("Uhrenseiten in settings.json auf „Uhr“ mit Zifferblatt umgestellt")
    profiles = macros.get("profiles") if macros else None
    if isinstance(profiles, list) and (global_faces or has_old([p.get("pages") for p in profiles if isinstance(p, dict)])):
        for p in profiles:
            if not isinstance(p, dict):
                continue
            own, faces = p.get("pages"), {}
            if isinstance(own, dict):
                p["pages"] = {k: convert(v, faces, k if k in LAYERS else None) for k, v in own.items()}
            use = faces if valid_profile_pages(p.get("pages")) else global_faces
            cur = p.get("clock") if isinstance(p.get("clock"), dict) else {}
            merged = valid_clock_faces(dict(use, **cur))
            if merged:
                p["clock"] = merged
        save_json(macros_path, macros, compact_steps=True)
        log("Uhrenseiten in macros.json auf „Uhr“ mit Zifferblatt umgestellt")


def migrate_system_page(settings_path=None, macros_path=None, log=print):
    """Bis Version 2026.09.29-2 gab es die Seite „System“ (jetzt Teil von „Hardware“) an Position 2.
    Seitenlisten: system → hardware; Startseite (Nummer) auf die neue Seitenliste umrechnen."""
    settings_path, macros_path = settings_path or SETTINGS_FILE, macros_path or MACRO_FILE

    def swap(lst):
        if not isinstance(lst, list):
            return lst
        return list(dict.fromkeys("hardware" if p == "system" else p for p in lst))

    try:
        with open(settings_path, encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = None
    if isinstance(s, dict) and s.get("pages_rev") != PAGES_REV:
        sp = s.get("start_page")
        if isinstance(sp, int) and not isinstance(sp, bool):
            old = OLD_PAGE_IDS_REV1[sp % len(OLD_PAGE_IDS_REV1)]
            s["start_page"] = PAGE_IDS.index("hardware" if old == "system" else old)
        if "pages" in s:
            s["pages"] = swap(s["pages"])
        if isinstance(s.get("layer_pages"), dict):
            s["layer_pages"] = {k: swap(v) for k, v in s["layer_pages"].items()}
        if isinstance(s.get("screensaver"), dict) and s["screensaver"].get("page") == "system":
            s["screensaver"]["page"] = "hardware"
        s["pages_rev"] = PAGES_REV
        save_json(settings_path, s, private=True)
        log("Seite „System“ ist jetzt Teil von „Hardware“ – settings.json umgestellt")
    try:
        with open(macros_path, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return
    profiles = m.get("profiles") if isinstance(m, dict) else None
    if isinstance(profiles, list) and any(isinstance(p, dict) and '"system"' in json.dumps(p.get("pages"))
                                          for p in profiles):
        for p in profiles:
            if isinstance(p, dict) and isinstance(p.get("pages"), dict):
                p["pages"] = {k: swap(v) for k, v in p["pages"].items()}
        save_json(macros_path, m, compact_steps=True)
        log("Seite „System“ ist jetzt Teil von „Hardware“ – macros.json umgestellt")


def migrate_files(log=print):
    """Umstellungen älterer Dateien beim Start (Treiber und Verwaltung, mehrfach aufrufbar)."""
    migrate_system_page(log=log)
    migrate_clock_pages(log=log)


def clean_macros(data):
    """Prüft die von der Seite gesendeten Profile und entfernt leere Einträge."""
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        raise ValueError("Ungültiges Format der Tastenbelegung")
    profiles = data["profiles"]
    if not 1 <= len(profiles) <= MAX_PROFILES:
        raise ValueError(f"Es sind 1 bis {MAX_PROFILES} Profile möglich")
    out = []
    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            raise ValueError("Ungültiges Profil")
        name = str(p.get("name") or "").strip()[:30] or f"Profil {i + 1}"
        keys_in = p.get("keys") if isinstance(p.get("keys"), dict) else {}
        keys = {}
        for layer, gkeys in keys_in.items():
            if layer not in LAYERS or not isinstance(gkeys, dict):
                raise ValueError(f"Ungültige Ebene: {layer}")
            for gkey, entry in gkeys.items():
                if not re.fullmatch(r"G([1-9]|1[0-2])", gkey) or not isinstance(entry, dict):
                    raise ValueError(f"Ungültige Taste: {gkey}")
                entry = {k: v for k, v in entry.items() if v not in (None, "", [])}
                if entry:
                    keys.setdefault(layer, {})[gkey] = entry
        prof = {"name": name, "keys": keys}
        if p.get("pages") is not None:
            pages = valid_profile_pages(p.get("pages"))
            if pages:
                prof["pages"] = pages
        faces = valid_clock_faces(p.get("clock"))
        if faces:
            prof["clock"] = faces
        if p.get("colors") is not None:
            colors = valid_colors(p.get("colors"))
            if not colors:
                raise ValueError(f"Ungültige Farben im Profil „{name}“")
            prof["colors"] = colors
        out.append(prof)
    return {"profiles": out}


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(**values):
    data = load_state()
    data.update(values)
    save_json(STATE_FILE, data)


class MacroStore:
    """Liest und schreibt macros.json (Profile → Ebenen M1–M3 → G-Tasten)."""

    def __init__(self, path, log=print):
        self.path = path
        self.log = log
        self.data = normalize_macros({})
        self.mtime = None
        self.reload()

    @property
    def profiles(self):
        return self.data["profiles"]

    def reload(self):
        """Gibt True zurück, wenn sich die Datei geändert hat."""
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError:
            if self.mtime is not None:
                self.log("Makrodatei entfernt – alle Makros deaktiviert.")
            changed = self.mtime is not None
            self.data, self.mtime = normalize_macros({}), None
            return changed
        if mtime == self.mtime:
            return False
        self.mtime = mtime
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("oberste Ebene muss ein Objekt sein")
            self.data = normalize_macros(data)
            count = sum(len(v) for p in self.profiles for v in p["keys"].values())
            self.log(f"Makros geladen: {len(self.profiles)} Profile, {count} Belegungen")
        except (ValueError, OSError) as ex:
            self.log(f"Makrodatei fehlerhaft, bisherige Makros bleiben aktiv: {ex}")
        return True

    def profile(self, pidx):
        return self.profiles[max(0, min(pidx, len(self.profiles) - 1))]

    def keys(self, pidx):
        """Belegung eines Profils: {"M1": {...}, "M2": {...}, "M3": {...}}"""
        return self.profile(pidx)["keys"]

    def get(self, pidx, layer, gkey):
        macro = self.keys(pidx).get(layer, {}).get(gkey)
        return macro if isinstance(macro, dict) else None

    def set(self, pidx, layer, gkey, macro):
        self.keys(pidx).setdefault(layer, {})[gkey] = macro
        self.save()

    def delete(self, pidx, layer, gkey):
        keys = self.keys(pidx)
        if keys.get(layer, {}).pop(gkey, None) is None:
            return False
        if not keys[layer]:
            del keys[layer]
        self.save()
        return True

    def save(self):
        save_json(self.path, self.data, compact_steps=True)
        self.mtime = os.path.getmtime(self.path)
