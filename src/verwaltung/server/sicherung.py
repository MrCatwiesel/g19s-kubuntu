"""Sicherung herunterladen/einspielen (die Dateiliste kommt aus dem Treiber)."""


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
