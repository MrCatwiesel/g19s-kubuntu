"""Update-Knopf: neue Programmdateien erkennen, prüfen, installieren (mit Sicherung der alten Version)."""


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
        m = re.search(r'^DRIVER_API = "([^"]*)"', checked["gui"][1], re.M)
        missing = [n for n in (m.group(1).split() if m else []) if not hasattr(g, n)]
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


# --------------------------------------------------------------------------- #
# Update direkt von GitHub (veröffentlichte Releases)
# --------------------------------------------------------------------------- #
UPDATE_URL = os.environ.get("G19S_UPDATE_URL",
                            "https://api.github.com/repos/MrCatwiesel/g19s-kubuntu/releases")
UPDATE_FILES = {"driver": "g19s.py", "gui": "g19s-gui.py"}
UPDATE_LIMIT = 8 * 1024 * 1024
UPDATE_NOTES_LIMIT = 10                  # „Was ist neu“: höchstens so viele Versionen


def version_key(v):
    """„2026.09.30-5“ → (2026, 9, 30, 5); unbekannt → ()."""
    return tuple(int(x) for x in re.findall(r"\d+", v or "")) if re.match(r"\d", v or "") else ()


def github_releases():
    """Veröffentlichte Releases (ohne Entwürfe und Vorabversionen), neueste zuerst."""
    try:
        raw = g.http_get(UPDATE_URL + "?per_page=30", timeout=20, limit=UPDATE_LIMIT)
        data = json.loads(raw.decode("utf-8"))
    except Exception as ex:
        raise RuntimeError(f"GitHub nicht abrufbar: {g.err_text(ex)}")
    if not isinstance(data, list):
        raise RuntimeError("GitHub hat unerwartet geantwortet")
    releases = []
    for r in data:
        if not isinstance(r, dict) or r.get("draft") or r.get("prerelease"):
            continue
        version = str(r.get("tag_name") or "").lstrip("vV")
        if not version_key(version):
            continue
        assets = {a.get("name"): a.get("browser_download_url") for a in r.get("assets") or []
                  if isinstance(a, dict)}
        releases.append({"version": version, "date": str(r.get("published_at") or "")[:10],
                         "notes": str(r.get("body") or "").strip(), "url": r.get("html_url") or "",
                         "assets": assets})
    releases.sort(key=lambda r: version_key(r["version"]), reverse=True)
    return releases


def download_asset(release, name):
    url = release["assets"].get(name)
    if not url:
        raise RuntimeError(f"{name} fehlt in Version {release['version']} auf GitHub")
    if urllib.parse.urlsplit(url).scheme not in ("https", urllib.parse.urlsplit(UPDATE_URL).scheme):
        raise RuntimeError(f"{name}: unsichere Download-Adresse")
    try:
        raw = g.http_get(url, timeout=30, limit=UPDATE_LIMIT)
    except Exception as ex:
        raise RuntimeError(f"{name} nicht abrufbar: {g.err_text(ex)}")
    found = version_of(raw.decode("utf-8", "replace"))
    if found != release["version"]:
        raise RuntimeError(f"{name} auf GitHub hat Version {found} statt {release['version']} – Update abgebrochen")
    return raw


def check_github():
    """Fragt die Releases auf GitHub ab und lädt die Dateien der neuesten Version, falls sie neuer ist.
    Rückgabe: (Info fürs Fenster, {Bauteil: (Dateiname, Bytes)} der neueren Dateien)."""
    installed = {"driver": file_version(os.path.join(HERE, "g19s.py")), "gui": VERSION}
    releases = github_releases()
    if not releases:
        raise RuntimeError("Auf GitHub ist noch keine Version veröffentlicht")
    latest = releases[0]
    info, newer = {"source": latest["url"], "latest": latest["version"], "components": []}, {}
    for comp, name in UPDATE_FILES.items():
        is_newer = version_key(latest["version"]) > version_key(installed[comp])
        info["components"].append({"component": comp, "file": name, "installed": installed[comp],
                                   "available": latest["version"], "newer": is_newer})
        if is_newer:
            newer[comp] = (name, download_asset(latest, name))
    oldest = min((version_key(v) for v in installed.values()), default=())
    info["notes"] = [{k: r[k] for k in ("version", "date", "notes", "url")}
                     for r in releases if version_key(r["version"]) > oldest][:UPDATE_NOTES_LIMIT]
    info["update"] = bool(newer)
    return info, newer
