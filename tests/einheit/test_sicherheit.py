"""Sicherheit: Weiterleitungen, Bildgrößen, Eingabeprüfung, Dateirechte, Einspielen von Sicherungen."""
import importlib.util, io, json, os, stat, sys, tarfile
from common import g, eq, ok, done, TMP, PROJ
from PIL import Image

# Zugangsdaten nur an denselben Server
eq(g.http_get("http://127.0.0.1:8812/umleitung-gleich", user="u", password="p"), g.basic_auth("u", "p").encode(),
   "Weiterleitung auf denselben Server: Anmeldung bleibt")
eq(g.http_get("http://127.0.0.1:8812/umleitung-fremd", user="u", password="p"), b"-",
   "Weiterleitung auf anderen Server: Anmeldung wird entfernt")
ok(g.same_origin("https://a.de/x", "https://A.de/y") and not g.same_origin("http://a.de/x", "https://a.de/"),
   "same_origin prüft Schema und Host")

# Bilder aus dem Netz: Größe vor dem Dekodieren
buf = io.BytesIO(); Image.new("1", (6000, 6000)).save(buf, "PNG")          # 36 MP, aber nur wenige KB
try:
    g.open_remote_image(buf.getvalue()); ok(False, "Riesenbild abgelehnt")
except ValueError as ex:
    ok("zu groß" in str(ex), f"Riesenbild abgelehnt ({len(buf.getvalue())} Bytes): {ex}")
buf = io.BytesIO(); Image.new("RGB", (800, 600), (1, 2, 3)).save(buf, "JPEG")
eq(g.open_remote_image(buf.getvalue()).convert("RGB").size, (800, 600), "normales Bild geht")

# Eingaben
st = g.SCHEMA["stations"].clean([{"name": "ok", "url": "https://a.de/s"}, {"name": "böse", "url": "https://a.de/x\n/etc/passwd"},
                                 {"name": "file", "url": "file:///etc/passwd"}], False)
eq([x["name"] for x in st], ["ok"], "tolerant: ungültige Senderadressen entfallen")
try:
    g.clean_settings({"stations": [{"url": "ftp://x"}]}); ok(False, "streng: ungültige Senderadresse abgelehnt")
except ValueError as ex:
    ok("http" in str(ex), "streng: ungültige Senderadresse abgelehnt")
try:
    g.clean_settings({"network": {"hosts": [{"host": "-i0.001"}]}}); ok(False, "ping-Option als Gerät abgelehnt")
except ValueError:
    ok(True, "ping-Option als Gerät abgelehnt")
eq(g.check_host("-c1000"), (False, None), "Treiber pingt keine Option")
eq(g.RadioManager(lambda: dict(os.environ), log=lambda *a: None).play({"url": "https://a.de/x\nfile:///etc/passwd"}, "true"), False,
   "Radio: Adresse mit Zeilenumbruch abgelehnt")
for bad in ('\\\\nas\\share\\a";!rm', "\\\\nas\\share\\a;b", "\\\\na s\\share"):
    try:
        g.SmbTarget(bad, "u", "p", tool="smbclient"); ok(False, f"Freigabe {bad!r} abgelehnt")
    except OSError:
        ok(True, f"Freigabe {bad!r} abgelehnt")
try:
    g.PiwigoClient("http://127.0.0.1:8811", "", "").fetch("file:///etc/passwd"); ok(False, "Piwigo: file:// abgelehnt")
except g.PiwigoError:
    ok(True, "Piwigo: file:// abgelehnt")

# Dateirechte
d = os.path.join(TMP, "bk"); os.makedirs(d)
p = g.auto_backup({"target": "folder", "folder": d}, 3, TMP)
eq(oct(os.stat(p).st_mode & 0o777), "0o600", "Sicherung nur für den Benutzer lesbar")
cfg = os.path.join(TMP, "cfg", "g19s")
g.save_json(os.path.join(cfg, "x.json"), {}, private=True)
eq(oct(os.stat(cfg).st_mode & 0o777), "0o700", "neuer Konfigurationsordner 0700")

# Einspielen einer Sicherung (Verwaltung): Programmdateien nur auf Wunsch, settings.json 0600
home = os.path.join(TMP, "home"); os.makedirs(home)
os.environ["HOME"] = home
spec = importlib.util.spec_from_file_location("gui", os.environ.get("G19S_GUI", os.path.join(PROJ, "dist", "g19s-gui.py")))
gui = importlib.util.module_from_spec(spec); spec.loader.exec_module(gui)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    for name, data in ((".config/g19s/settings.json", b'{"x": 1}'), (".config/g19s/macros.json", b"{}"),
                       (".local/bin/g19s.py", b"print('fremd')"), (".local/share/applications/g19s-x.desktop", b"[Desktop Entry]"),
                       ("../../etc/boese", b"x"), (".config/g19s/gross.json", b"x")):
        ti = tarfile.TarInfo(name); ti.size = len(data); tar.addfile(ti, io.BytesIO(data))
raw = buf.getvalue()
info = gui.restore_backup(raw, inspect=True)
eq((sorted(info["config"]), sorted(info["programs"])),
   ([".config/g19s/macros.json", ".config/g19s/settings.json"], [".local/bin/g19s.py", ".local/share/applications/g19s-x.desktop"]),
   "Einspielen: Inhalt geprüft, fremde Pfade ignoriert")
restored, safety = gui.restore_backup(raw)
ok(sorted(restored) == [".config/g19s/macros.json", ".config/g19s/settings.json"] and not os.path.exists(os.path.join(home, ".local/bin/g19s.py")),
   "ohne Zustimmung keine Programmdateien")
eq(oct(os.stat(os.path.join(home, ".config/g19s/settings.json")).st_mode & 0o777), "0o600", "settings.json nach dem Einspielen 0600")
eq(oct(os.stat(safety).st_mode & 0o777), "0o600", "Sicherheitskopie 0600")
restored, _ = gui.restore_backup(raw, programs=True)
ok(os.path.exists(os.path.join(home, ".local/bin/g19s.py")), "mit Zustimmung auch Programmdateien")
done()
