"""Sicherung: Dateiliste, tar.gz erzeugen, automatische Sicherung.

Ziele der automatischen Sicherung (settings.json → "backup" → "target"):
  folder     Ordner auf diesem Rechner (auch ein eingebundenes NAS oder der Nextcloud-Sync-Ordner)
  nextcloud  Nextcloud über WebDAV (Serveradresse, Benutzer, App-Passwort, Ordner – wird angelegt)
  webdav     beliebiger WebDAV-Ordner (z. B. NAS mit WebDAV-Dienst)
  smb        Windows-Freigabe/NAS (\\nas\freigabe\ordner) über smbclient oder KDEs kioclient
"""
import base64
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request


# Dateien einer Sicherung (relativ zum Home-Verzeichnis)
BACKUP_FILES = [
    ".config/g19s/macros.json",
    ".config/g19s/settings.json",
    ".config/g19s/state.json",
    ".config/g19s/songs.json",
    ".config/g19s/favorites.json",
    ".config/kglobalshortcutsrc",
    ".config/systemd/user/g19s.service",
    ".local/bin/g19s.py",
    ".local/bin/g19s-gui.py",
]
DESKTOP_RE = re.compile(r"\.local/share/applications/[A-Za-z0-9._-]+\.desktop")


def backup_members(home=None):
    home = home or os.path.expanduser("~")
    members = [p for p in BACKUP_FILES if os.path.isfile(os.path.join(home, p))]
    appdir = os.path.join(home, ".local/share/applications")
    if os.path.isdir(appdir):
        for name in sorted(os.listdir(appdir)):
            rel = f".local/share/applications/{name}"
            # KDE-Befehle („Befehl oder Skript“) und der eigene Starter
            if DESKTOP_RE.fullmatch(rel) and (name.startswith("net.local.") or name.startswith("g19s")):
                members.append(rel)
    return members


def make_backup(home=None):
    import io
    import tarfile
    home = home or os.path.expanduser("~")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel in backup_members(home):
            tar.add(os.path.join(home, rel), arcname=rel)
    return buf.getvalue()


BACKUP_PATTERN = re.compile(r"g19s-sicherung-.*_.*\.tar\.gz")       # wie bisher: g19s-sicherung-*_*.tar.gz


class BackupError(OSError):
    """Verständliche Fehlermeldung eines Sicherungsziels."""


class FolderTarget:
    def __init__(self, folder):
        self.folder = os.path.expanduser(str(folder or "").strip())
        if re.match(r"^(smb|https?|webdavs?)://|^\\\\", self.folder, re.I):
            raise BackupError("Das ist keine Ordneradresse auf diesem Rechner – bitte als Ziel „NAS (Windows-Freigabe)“, "
                              "„Nextcloud“ oder „WebDAV“ wählen")

    def describe(self):
        return self.folder

    def location(self, name):
        return os.path.join(self.folder, name)

    def prepare(self):
        if not self.folder or not os.path.isdir(self.folder):
            raise BackupError(f"Ordner nicht gefunden: {self.folder or '(leer)'} – ist das NAS eingebunden?")

    def upload(self, name, data):
        path = os.path.join(self.folder, name)
        with open(path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(path + ".tmp", path)

    def names(self):
        return os.listdir(self.folder)

    def delete(self, name):
        os.remove(os.path.join(self.folder, name))


class WebDavTarget:
    """WebDAV-Ordner (Nextcloud, NAS). nextcloud=True: url ist die Serveradresse, dir der Ordner darin."""

    def __init__(self, url, user="", password="", remote_dir="", nextcloud=False):
        url = str(url or "").strip()
        if not url:
            raise BackupError("Bitte die Adresse angeben")
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + re.sub(r"^webdavs?://", "", url, flags=re.I)
        self.user, self.password = str(user or "").strip(), str(password or "")
        self.parts = []                      # Ordner, die angelegt werden dürfen (Nextcloud)
        if nextcloud:
            u = urllib.parse.urlsplit(url)
            path = u.path
            q = urllib.parse.parse_qs(u.query)
            if "/apps/files" in path:        # aus der Adresszeile des Browsers kopiert: dort gezeigter Ordner
                path = path.split("/apps/files")[0]
                if q.get("dir"):
                    remote_dir = q["dir"][0]
            path = re.sub(r"/index\.php$", "", path.rstrip("/"))
            if "/remote.php/dav/files/" in path:
                root = path.rstrip("/")
            else:
                path = re.sub(r"/remote\.php/(web)?dav$", "", path)
                if not self.user:
                    raise BackupError("Bitte den Nextcloud-Benutzernamen angeben")
                root = f"{path}/remote.php/dav/files/{urllib.parse.quote(self.user)}"
            self.parts = [p for p in str(remote_dir or "").replace("\\", "/").split("/") if p.strip()]
            path = root + "".join("/" + urllib.parse.quote(p.strip()) for p in self.parts)
            self.base = urllib.parse.urlunsplit((u.scheme, u.netloc, root, "", ""))
            url = urllib.parse.urlunsplit((u.scheme, u.netloc, path, "", ""))
        self.url = url.rstrip("/") + "/"

    def describe(self):
        return urllib.parse.unquote(self.url)

    def location(self, name):
        return self.describe() + name

    def _req(self, method, url, data=None, headers=None, ok=(200, 201, 204, 207)):
        h = dict(headers or {})
        if self.user:
            h["Authorization"] = "Basic " + base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as ex:
            if ex.code in ok:
                return ex.code, ex.read()
            if ex.code == 401:
                raise BackupError("Anmeldung abgelehnt – Benutzername und (App-)Passwort prüfen")
            if ex.code == 403:
                raise BackupError("Zugriff verweigert – fehlen Schreibrechte für den Ordner?")
            if ex.code == 404:
                raise BackupError(f"Ordner nicht gefunden: {urllib.parse.unquote(url)}")
            if ex.code == 507:
                raise BackupError("Kein Speicherplatz mehr auf dem Server")
            raise BackupError(f"Server meldet {ex.code} {ex.reason} für {urllib.parse.unquote(url)}")
        except urllib.error.URLError as ex:
            raise BackupError(f"Server nicht erreichbar: {ex.reason}")
        except (OSError, http.client.HTTPException) as ex:
            raise BackupError(f"Verbindung fehlgeschlagen: {ex}")

    def prepare(self):
        """Ordner anlegen (Nextcloud: jede fehlende Ebene), sonst prüfen, dass er existiert."""
        if self.parts:
            url = self.base
            for p in self.parts:
                url += "/" + urllib.parse.quote(p.strip())
                self._req("MKCOL", url, ok=(201, 405))     # 405 = gibt es schon
        self._req("PROPFIND", self.url, b"", {"Depth": "0"})

    def upload(self, name, data):
        self._req("PUT", self.url + urllib.parse.quote(name), data, {"Content-Type": "application/gzip"})

    def names(self):
        _, body = self._req("PROPFIND", self.url, b"", {"Depth": "1"})
        out = []
        for href in re.findall(rb"<(?:\w+:)?href>([^<]+)</(?:\w+:)?href>", body):
            name = urllib.parse.unquote(href.decode("utf-8", "replace").rstrip("/").rsplit("/", 1)[-1])
            if name:
                out.append(name)
        return out

    def delete(self, name):
        self._req("DELETE", self.url + urllib.parse.quote(name), ok=(200, 204, 404))


class SmbTarget:
    """Windows-Freigabe (NAS). Nutzt smbclient, sonst KDEs kioclient (Plasma)."""

    def __init__(self, url, user="", password="", tool=None):
        raw = str(url or "").strip().replace("\\", "/")
        raw = re.sub(r"^smb:", "", raw, flags=re.I).lstrip("/")
        parts = [p for p in raw.split("/") if p]
        if len(parts) < 2:
            raise BackupError("Bitte die Freigabe angeben, z. B. \\\\nas\\freigabe\\Sicherungen")
        self.host, self.share, self.dir = parts[0], parts[1], "/".join(parts[2:])
        self.user, self.password = str(user or "").strip(), str(password or "")
        self.tool = tool or ("smbclient" if shutil.which("smbclient") else
                             next((t for t in ("kioclient", "kioclient5") if shutil.which(t)), None))
        if not self.tool:
            raise BackupError("Für Windows-Freigaben fehlt das Programm smbclient – bitte installieren: "
                              "sudo apt install smbclient")

    def describe(self):
        return f"\\\\{self.host}\\{self.share}" + "".join("\\" + p for p in self.dir.split("/") if p)

    def location(self, name):
        return self.describe() + "\\" + name

    # smbclient -------------------------------------------------------------- #
    def _smb(self, commands):
        cd = f'cd "{self.dir}"; ' if self.dir else ""
        cmd = ["smbclient", f"//{self.host}/{self.share}", "-c", cd + commands]
        env = dict(os.environ)
        if self.user:
            cmd += ["-U", self.user]
            env["PASSWD"] = self.password    # Passwort nicht in der Befehlszeile
        else:
            cmd.append("-N")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        except (OSError, subprocess.SubprocessError) as ex:
            raise BackupError(f"smbclient: {ex}")
        out = r.stdout + r.stderr
        for code, msg in (("NT_STATUS_LOGON_FAILURE", "Anmeldung abgelehnt – Benutzername und Passwort prüfen"),
                          ("NT_STATUS_BAD_NETWORK_NAME", f"Freigabe „{self.share}“ nicht gefunden"),
                          ("NT_STATUS_OBJECT_NAME_NOT_FOUND", "Ordner nicht gefunden"),
                          ("NT_STATUS_OBJECT_PATH_NOT_FOUND", "Ordner nicht gefunden"),
                          ("NT_STATUS_ACCESS_DENIED", "Zugriff verweigert – fehlen Schreibrechte?"),
                          ("NT_STATUS_HOST_UNREACHABLE", f"NAS „{self.host}“ nicht erreichbar"),
                          ("NT_STATUS_IO_TIMEOUT", f"NAS „{self.host}“ antwortet nicht"),
                          ("NT_STATUS_CONNECTION_REFUSED", f"NAS „{self.host}“ lehnt die Verbindung ab"),
                          ("Connection to", f"NAS „{self.host}“ nicht erreichbar")):
            if code in out:
                raise BackupError(msg)
        if r.returncode:
            raise BackupError("smbclient: " + (out.strip().splitlines() or ["Fehler"])[-1])
        return r.stdout

    # kioclient -------------------------------------------------------------- #
    def _kio_url(self, name=""):
        cred = ""
        if self.user:
            cred = urllib.parse.quote(self.user, safe="") + ":" + urllib.parse.quote(self.password, safe="") + "@"
        path = "/".join(urllib.parse.quote(p) for p in [self.share] + [d for d in self.dir.split("/") if d])
        return f"smb://{cred}{self.host}/{path}/" + urllib.parse.quote(name)

    def _kio(self, *args):
        try:
            env = Launcher()._env()               # DBus/KWallet der Sitzung
        except Exception:                          # ohne Sitzung: eigene Umgebung
            env = dict(os.environ)
        try:
            r = subprocess.run([self.tool, "--noninteractive", *args], capture_output=True, text=True,
                               timeout=120, env=env)
        except (OSError, subprocess.SubprocessError) as ex:
            raise BackupError(f"{self.tool}: {ex}")
        if r.returncode:
            msg = (r.stderr.strip().splitlines() or [""])[-1] or f"Fehler {r.returncode}"
            raise BackupError(f"NAS: {msg.replace(self.password, '***') if self.password else msg}")
        return r.stdout

    def prepare(self):
        self.names()

    def upload(self, name, data):
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
            f.write(data)
            local = f.name
        try:
            if self.tool == "smbclient":
                self._smb(f'put "{local}" "{name}"')
            else:
                self._kio("copy", "file://" + urllib.parse.quote(local), self._kio_url(name))
        finally:
            os.remove(local)

    def names(self):
        if self.tool == "smbclient":
            out = self._smb("ls")
            return [m.group(1) for m in re.finditer(r"^\s+(\S.*?)\s+[A-Z]*\s+\d+\s+\w{3} \w{3}", out, re.M)]
        return [l.strip().rstrip("/") for l in self._kio("ls", self._kio_url()).splitlines() if l.strip()]

    def delete(self, name):
        if self.tool == "smbclient":
            self._smb(f'del "{name}"')
        else:
            self._kio("remove", self._kio_url(name))


def backup_target(cfg):
    """Sicherungsziel aus den Einstellungen ("backup") – oder aus einem Ordnernamen (ältere Aufrufer)."""
    if not isinstance(cfg, dict):
        return FolderTarget(cfg)
    t = cfg.get("target") or "folder"
    if t == "nextcloud":
        return WebDavTarget(cfg.get("url"), cfg.get("user"), cfg.get("password"),
                            cfg.get("remote_dir") or "G19s-Sicherung", nextcloud=True)
    if t == "webdav":
        return WebDavTarget(cfg.get("url"), cfg.get("user"), cfg.get("password"))
    if t == "smb":
        return SmbTarget(cfg.get("url"), cfg.get("user"), cfg.get("password"))
    return FolderTarget(cfg.get("folder"))


def auto_backup(target, keep=8, home=None):
    """Sicherung ins Ziel schreiben und alte automatische Sicherungen dort aufräumen.
    target: Einstellungen "backup" (dict) oder ein Ordner. Liefert den Ort der Sicherung."""
    t = backup_target(target)
    t.prepare()
    name = f"g19s-sicherung-{time.strftime('%Y-%m-%d_%H%M')}.tar.gz"
    t.upload(name, make_backup(home))
    try:
        old = sorted(n for n in t.names() if BACKUP_PATTERN.fullmatch(n))
        for n in old[:max(0, len(old) - max(1, int(keep or 8)))]:
            try:
                t.delete(n)
            except OSError:
                pass
    except OSError:
        pass                                 # Aufräumen ist nicht kritisch
    return t.location(name)


def test_backup_target(cfg):
    """Verbindung prüfen: Ordner vorbereiten, Probedatei schreiben, wieder löschen. Liefert eine Meldung."""
    t = backup_target(cfg)
    t.prepare()
    probe = f"g19s-test-{int(time.time())}.txt"
    t.upload(probe, b"G19s: Test der Sicherung\n")
    found = probe in t.names()
    t.delete(probe)
    count = len([n for n in t.names() if BACKUP_PATTERN.fullmatch(n)])
    if not found:
        raise BackupError("Probedatei geschrieben, aber im Ordner nicht wiedergefunden")
    return f"Verbindung in Ordnung: {t.describe()} ({count} vorhandene Sicherungen)"
