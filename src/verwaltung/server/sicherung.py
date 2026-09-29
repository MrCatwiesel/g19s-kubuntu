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


def restore_backup(raw):
    try:
        tar = tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")
    except tarfile.TarError as ex:
        raise ValueError(f"Keine gültige Sicherungsdatei: {ex}")
    allowed = []
    with tar:
        for m in tar.getmembers():
            name = m.name[2:] if m.name.startswith("./") else m.name
            if not m.isfile():
                continue
            if name in BACKUP_FILES or DESKTOP_RE.fullmatch(name):
                allowed.append((name, m))
        if not allowed:
            raise ValueError("Die Datei enthält keine G19s-Dateien")
        # vorherigen Stand sichern
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        safety = os.path.join(HOME, ".config/g19s", f"vor-wiederherstellung-{stamp}.tar.gz")
        os.makedirs(os.path.dirname(safety), exist_ok=True)
        with open(safety, "wb") as f:
            f.write(make_backup())
        restored = []
        for name, m in allowed:
            dest = os.path.join(HOME, name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            data = tar.extractfile(m).read()
            tmp = dest + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            if name.endswith(".py"):
                os.chmod(tmp, 0o755)
            os.replace(tmp, dest)
            restored.append(name)
    return restored, safety
