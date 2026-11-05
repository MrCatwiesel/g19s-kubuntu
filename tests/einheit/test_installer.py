"""Installer dist/install.sh: Installieren (aus dist/ und per Download), Aktualisieren mit Sicherung,
beschädigter Download, Deinstallieren (mit und ohne --alles). sudo, Paketverwaltung, udevadm, usermod und
systemctl sind Attrappen, die ihre Aufrufe protokollieren; alles landet in einem leeren Home-Verzeichnis."""
import os
import shutil
import subprocess
import sys
import tempfile
from common import PROJ, eq, ok, done

DIST = os.path.join(PROJ, "dist")
ROOT = tempfile.mkdtemp(prefix="g19s-installer-")
STUBS, LOG = os.path.join(ROOT, "stubs"), os.path.join(ROOT, "aufrufe.log")
os.makedirs(STUBS)
PYSTUBS = os.path.join(ROOT, "py")                      # leeres Modul „usb“ für die Prüfung der Python-Module
os.makedirs(os.path.join(PYSTUBS, "usb"))
open(os.path.join(PYSTUBS, "usb", "__init__.py"), "w").close()
for name, body in {
    "sudo": 'echo "sudo $*" >> "$LOG"; "$@"',
    "apt-get": 'echo "apt-get $*" >> "$LOG"',
    "usermod": 'echo "usermod $*" >> "$LOG"',
    "udevadm": 'echo "udevadm $*" >> "$LOG"',
    "update-desktop-database": 'true',
    "systemctl": 'echo "systemctl $*" >> "$LOG"; case "$2" in is-active) exit 1;; esac; exit 0',
}.items():
    path = os.path.join(STUBS, name)
    open(path, "w").write(f'#!/bin/sh\n{body}\n')
    os.chmod(path, 0o755)


def run(script, *args, home=None, url=None):
    env = {"HOME": home, "PATH": STUBS + ":" + os.path.dirname(sys.executable) + ":/usr/bin:/bin", "LOG": LOG, "G19S_INSTALL_TEST": "1", "USER": "tester",
           "G19S_UDEV_DIR": os.path.join(home, "udev"), "PYTHONPATH": PYSTUBS + ":" + os.path.join(PROJ, "tests", "stubs"),
           "LANG": "C.UTF-8"}
    if url:
        env["G19S_DOWNLOAD_URL"] = url
    os.makedirs(env["G19S_UDEV_DIR"], exist_ok=True)
    open(LOG, "w").close()
    r = subprocess.run(["bash", script, *args], env=env, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr, open(LOG).read()


def exists(home, *parts):
    return os.path.exists(os.path.join(home, *parts))


# 1. Installieren aus dist/
home = os.path.join(ROOT, "home1")
os.makedirs(home)
code, out, log = run(os.path.join(DIST, "install.sh"), "--ja", home=home)
eq(code, 0, "Installation läuft durch" + ("" if code == 0 else ": " + out[-600:]))
ok(exists(home, ".local/bin/g19s.py") and exists(home, ".local/bin/g19s-gui.py"), "Programme in ~/.local/bin")
ok(os.access(os.path.join(home, ".local/bin/g19s.py"), os.X_OK), "Treiber ausführbar")
eq(open(os.path.join(home, ".local/bin/g19s.py")).read(), open(os.path.join(DIST, "g19s.py")).read(), "Treiber unverändert kopiert")
eq(open(os.path.join(home, ".config/systemd/user/g19s.service")).read().strip(),
   open(os.path.join(PROJ, "dateien/g19s.service")).read().strip(), "Dienstdatei wie dateien/g19s.service")
eq(open(os.path.join(home, "udev/70-g19s.rules")).read().strip(),
   open(os.path.join(PROJ, "dateien/70-g19s.rules")).read().strip(), "udev-Regel wie dateien/70-g19s.rules")
ok(exists(home, ".local/share/applications/g19s-gui.desktop"), "Menüeintrag angelegt")
ok("apt-get install -y python3-usb" in log and "mpv-mpris" in log, "Pakete per apt-get")
ok("usermod -aG input tester" in log, "Gruppe input")
ok("systemctl --user enable g19s.service" in log and "udevadm control --reload-rules" in log, "Dienst aktiviert, udev neu geladen")
ok("neu starten" in out and "Fertig" in out, "Hinweis auf Neustart")
ok(exists(home, ".local/share/g19s/install.sh"), "Installer für späteres Entfernen aufgehoben")

# 2. erneut ausführen = aktualisieren: alte Version gesichert, udev-Regel schon aktuell
code, out, log = run(os.path.join(home, ".local/share/g19s/install.sh"), "--ja", "--ohne-pakete", home=home,
                     url="file://" + DIST)
eq(code, 0, "Aktualisieren läuft durch")
backups = os.listdir(os.path.join(home, ".local/share/g19s/alte-versionen"))
ok(any(b.startswith("g19s.py.") for b in backups) and any(b.startswith("g19s-gui.py.") for b in backups),
   f"vorherige Version gesichert ({len(backups)} Dateien)")
ok("udev-Regel ist aktuell" in out and "apt-get" not in log, "keine Pakete, udev-Regel unverändert")

# 3. nur install.sh vorhanden: Programme werden heruntergeladen (hier per file://)
home3 = os.path.join(ROOT, "home3")
alone = os.path.join(ROOT, "nur-installer")
os.makedirs(home3)
os.makedirs(alone)
shutil.copy(os.path.join(DIST, "install.sh"), alone)
code, out, log = run(os.path.join(alone, "install.sh"), "--ja", "--ohne-pakete", home=home3, url="file://" + DIST)
eq(code, 0, "Installation per Download" + ("" if code == 0 else ": " + out[-600:]))
ok(exists(home3, ".local/bin/g19s.py"), "heruntergeladener Treiber installiert")

# 3b. Dateien mit Browser-Namen neben dem Installer werden am Inhalt erkannt (kein Download)
renamed = os.path.join(ROOT, "downloads")
os.makedirs(renamed)
shutil.copy(os.path.join(DIST, "install.sh"), renamed)
shutil.copy(os.path.join(DIST, "g19s.py"), os.path.join(renamed, "g19s(1).py"))
shutil.copy(os.path.join(DIST, "g19s-gui.py"), os.path.join(renamed, "g19s-gui(2).py"))
home3b = os.path.join(ROOT, "home3b")
os.makedirs(home3b)
code, out, log = run(os.path.join(renamed, "install.sh"), "--ja", "--ohne-pakete", home=home3b, url="file:///gibt/es/nicht")
ok(code == 0 and "aus g19s(1).py" in out and exists(home3b, ".local/bin/g19s-gui.py"), "Browser-Namen wie „g19s(1).py“ erkannt")
code, out, log = run(os.path.join(alone, "install.sh"), "--ja", "--ohne-pakete", home=home3b, url="file:///gibt/es/nicht")
ok(code != 0 and "ein paar" in out, "Version noch nicht auf GitHub: verständliche Meldung")

# 4. beschädigter Download wird abgelehnt, nichts installiert
broken = os.path.join(ROOT, "kaputt")
os.makedirs(broken)
for f in ("g19s.py", "g19s-gui.py"):
    open(os.path.join(broken, f), "w").write(open(os.path.join(DIST, f)).read()[:5000])
home4 = os.path.join(ROOT, "home4")
os.makedirs(home4)
code, out, log = run(os.path.join(alone, "install.sh"), "--ja", "--ohne-pakete", home=home4, url="file://" + broken)
ok(code != 0 and "unvollständig" in out and not exists(home4, ".local/bin/g19s.py"), "abgebrochener Download abgelehnt")

# 5. Deinstallieren: Einstellungen bleiben, mit --alles weg
os.makedirs(os.path.join(home, ".config/g19s"), exist_ok=True)
open(os.path.join(home, ".config/g19s/macros.json"), "w").write("{}")
code, out, log = run(os.path.join(home, ".local/share/g19s/install.sh"), "--deinstallieren", "--ja", home=home)
eq(code, 0, "Deinstallieren läuft durch")
ok(not exists(home, ".local/bin/g19s.py") and not exists(home, ".config/systemd/user/g19s.service")
   and not exists(home, "udev/70-g19s.rules") and not exists(home, ".local/share/applications/g19s-gui.desktop"),
   "Programme, Dienst, udev-Regel und Menüeintrag entfernt")
ok(exists(home, ".config/g19s/macros.json") and "systemctl --user disable --now g19s.service" in log,
   "Dienst gestoppt, Einstellungen behalten")
code, out, log = run(os.path.join(DIST, "install.sh"), "--deinstallieren", "--alles", "--ja", home=home)
ok(code == 0 and not exists(home, ".config/g19s") and not exists(home, ".local/share/g19s"), "--alles löscht Einstellungen und Daten")
shutil.rmtree(ROOT, ignore_errors=True)
done()
