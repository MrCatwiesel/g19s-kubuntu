"""Automatische Sicherung: Ordner, Nextcloud, WebDAV, Windows-Freigabe (smbclient/kioclient) – gegen Nachbauten."""
import os, shutil, tarfile, io
from common import g, eq, ok, done, TMP

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = os.path.join(HERE, "..", "fakes", "bin") + ":" + os.environ["PATH"]
ROOT = os.environ.setdefault("G19S_TEST_ROOT", "/tmp/g19s-test")
HOME = os.path.join(TMP, "home")
os.makedirs(os.path.join(HOME, ".config/g19s"), exist_ok=True)
open(os.path.join(HOME, ".config/g19s/macros.json"), "w").write('{"profiles": []}')
OLD = ["g19s-sicherung-2026-01-0%d_1200.tar.gz" % i for i in range(1, 5)]


def raises(fn, text, label):
    try:
        fn()
        ok(False, f"{label}: Fehler erwartet")
    except OSError as ex:
        ok(text in str(ex), f"{label}: „{ex}“")


def rotation(t, cfg, label):
    for n in OLD:
        t.upload(n, b"alt")
    t.upload("fremd.txt", b"bleibt")
    where = g.auto_backup(cfg, 2, HOME)
    names = sorted(t.names())
    new = [n for n in names if g.BACKUP_PATTERN.fullmatch(n) and n not in OLD]
    eq(len([n for n in names if g.BACKUP_PATTERN.fullmatch(n)]), 2, f"{label}: nur 2 Sicherungen behalten")
    ok(OLD[-1] in names and OLD[0] not in names and "fremd.txt" in names, f"{label}: älteste gelöscht, Fremdes bleibt")
    ok(len(new) == 1 and where.endswith(new[0]), f"{label}: Ort gemeldet: {where}")
    return new[0]


# Ordner
d = os.path.join(TMP, "sich")
os.makedirs(d)
cfg = {"target": "folder", "folder": d}
new = rotation(g.backup_target(cfg), cfg, "Ordner")
with tarfile.open(os.path.join(d, new)) as tar:
    ok(".config/g19s/macros.json" in tar.getnames(), "Ordner: Sicherung enthält macros.json")
raises(lambda: g.auto_backup({"target": "folder", "folder": "/gibt/es/nicht"}, 2, HOME), "eingebunden", "Ordner fehlt")
raises(lambda: g.auto_backup({"target": "folder", "folder": "smb://nas/x"}, 2, HOME), "Windows-Freigabe", "smb:// als Ordner")
eq(os.path.basename(g.auto_backup(d, 3, HOME))[:15], "g19s-sicherung-", "alter Aufruf mit Ordnername geht weiter")

# Nextcloud (WebDAV)
nc = {"target": "nextcloud", "url": "http://127.0.0.1:8812/nc", "user": "mde@example.de", "password": "app-pw",
      "remote_dir": "Backups/G19s"}
t = g.backup_target(nc)
eq(t.url, "http://127.0.0.1:8812/nc/remote.php/dav/files/mde%40example.de/Backups/G19s/", "Nextcloud: Ordneradresse gebildet")
msg = g.test_backup_target(nc)
ok(msg.startswith("Verbindung in Ordnung") and "Backups/G19s" in msg, "Nextcloud: Test legt Ordner an – " + msg)
rotation(t, nc, "Nextcloud")
eq(g.backup_target({"target": "nextcloud", "url": "http://127.0.0.1:8812/nc/index.php/apps/files/?dir=/Backups/G19s&fileid=5",
                    "user": "mde@example.de", "remote_dir": ""}).url, t.url, "Nextcloud: Adresse aus dem Browser")
eq(g.backup_target(dict(nc, url="127.0.0.1:8812/nc/remote.php/webdav")).url.replace("https", "http"), t.url,
   "Nextcloud: alte webdav-Adresse ohne https://")
raises(lambda: g.test_backup_target(dict(nc, password="falsch")), "Anmeldung abgelehnt", "Nextcloud falsches Passwort")
raises(lambda: g.test_backup_target(dict(nc, url="http://127.0.0.1:1/nc")), "nicht erreichbar", "Nextcloud nicht erreichbar")
raises(lambda: g.backup_target(dict(nc, user="")), "Benutzernamen", "Nextcloud ohne Benutzer")

# WebDAV (NAS)
wd = {"target": "webdav", "url": "http://127.0.0.1:8812/dav/home/Sicherungen", "user": "nas", "password": "pw"}
ok(g.test_backup_target(wd).startswith("Verbindung in Ordnung"), "WebDAV: Test")
rotation(g.backup_target(wd), wd, "WebDAV")
raises(lambda: g.test_backup_target(dict(wd, url="http://127.0.0.1:8812/dav/home/Fehlt")), "Ordner nicht gefunden", "WebDAV Ordner fehlt")

# Windows-Freigabe über smbclient
share = os.path.join(ROOT, "smb", "nas", "backup")
shutil.rmtree(os.path.join(ROOT, "smb"), ignore_errors=True)
os.makedirs(os.path.join(share, "G19s Sicherung"))
sm = {"target": "smb", "url": "\\\\nas\\backup\\G19s Sicherung", "user": "nas", "password": "geh%eim"}
t = g.backup_target(sm)
eq((t.tool, t.host, t.share, t.dir), ("smbclient", "nas", "backup", "G19s Sicherung"), "SMB: Freigabe zerlegt")
eq(g.backup_target(dict(sm, url="smb://nas/backup/G19s Sicherung/")).dir, "G19s Sicherung", "SMB: smb://-Adresse")
ok(g.test_backup_target(sm).startswith("Verbindung in Ordnung"), "SMB: Test")
new = rotation(t, sm, "SMB")
ok(os.path.isfile(os.path.join(share, "G19s Sicherung", new)), "SMB: Datei liegt auf der Freigabe")
raises(lambda: g.test_backup_target(dict(sm, password="x")), "Anmeldung abgelehnt", "SMB falsches Passwort")
raises(lambda: g.test_backup_target(dict(sm, url="\\\\nas\\backup\\Fehlt")), "Ordner nicht gefunden", "SMB Ordner fehlt")
raises(lambda: g.test_backup_target(dict(sm, url="\\\\nas\\gibtsnicht")), "nicht gefunden", "SMB Freigabe fehlt")
raises(lambda: g.test_backup_target(dict(sm, url="\\\\offline\\backup")), "nicht erreichbar", "SMB NAS aus")
raises(lambda: g.backup_target(dict(sm, url="nas")), "Freigabe angeben", "SMB ohne Freigabe")

# Windows-Freigabe über kioclient (ohne smbclient)
open(os.path.join(ROOT, "smb", "wallet"), "w").write("nas")          # Passwort in „KWallet“ gespeichert
k = g.SmbTarget("smb://nas/backup/G19s Sicherung", "nas", "geh%eim", tool="kioclient")
ok("geh" not in k._kio_url("x"), "kioclient: Passwort nicht in der Adresse: " + k._kio_url("x"))
k.prepare()
k.upload("probe.txt", b"x")
ok("probe.txt" in k.names() and os.path.isfile(os.path.join(share, "G19s Sicherung", "probe.txt")), "kioclient: hochgeladen und gelistet")
k.delete("probe.txt")
ok("probe.txt" not in k.names(), "kioclient: gelöscht")
os.remove(os.path.join(ROOT, "smb", "wallet"))
raises(lambda: g.SmbTarget("smb://nas/backup/G19s Sicherung", "nas", "geh%eim", tool="kioclient").prepare(), "Dolphin", "kioclient ohne gespeichertes Passwort")

# Einstellungen
try:
    g.clean_settings({"backup": {"enabled": True, "target": "smb", "url": ""}})
    ok(False, "Ziel ohne Adresse abgelehnt")
except ValueError as ex:
    ok("Adresse" in str(ex), "Ziel ohne Adresse abgelehnt")
eq(g.clean_settings({"backup": {"target": "quatsch"}})["backup"]["target"], "folder", "unbekanntes Ziel → Ordner")
eq(g.clean_settings({})["backup"]["remote_dir"], "G19s-Sicherung", "Standardordner in der Nextcloud")
done()
