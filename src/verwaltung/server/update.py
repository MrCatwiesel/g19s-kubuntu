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
