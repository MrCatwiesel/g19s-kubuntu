import json, os, time
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
U = ROOT + "/upd"; H = ROOT + "/gui/home"; BIN = H + "/.local/bin"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
def ver(p): return next((l for l in open(p) if l.startswith("VERSION")), "").strip()
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1000})
    pg.on("dialog", lambda d: d.accept()); pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(800)
    ok(ver(os.environ["G19S_GUI"]).split("\"")[1] in pg.inner_text("#versions"), "Versionen angezeigt: " + pg.inner_text("#versions").replace("\n", " | ")[:90])
    # 1) beschädigte und fremde Dateien werden abgelehnt, nichts wird verändert
    before = open(BIN + "/g19s.py").read()
    pg.set_input_files("#updateFile", f"{U}/abgeschnitten.py"); pg.wait_for_timeout(800)
    ok("unvollständig" in pg.inner_text("#updateResult"), "Abgeschnittene Datei abgelehnt: " + pg.inner_text("#updateResult")[:80])
    pg.set_input_files("#updateFile", f"{U}/fremd.py"); pg.wait_for_timeout(800)
    ok("weder" in pg.inner_text("#updateResult"), "Fremde Datei abgelehnt")
    ok(open(BIN + "/g19s.py").read() == before, "Installierter Treiber unverändert")
    # 2) Treiber + Verwaltung zusammen
    pg.set_input_files("#updateFile", [f"{U}/g19s(7).py", f"{U}/g19s-gui(4).py"])
    pg.wait_for_timeout(1000)
    ok(pg.is_visible("#overlay"), "Hinweis „Verwaltung wird neu gestartet“")
    pg.wait_for_selector(".gkey", timeout=30000); pg.wait_for_timeout(800)
    ok("test" in ver(BIN + "/g19s.py") and "test" in ver(BIN + "/g19s-gui.py"), "Beide Dateien ersetzt")
    ok(any(f.startswith("g19s.py.") for f in os.listdir(H + "/.local/share/g19s/alte-versionen")), "Alte Versionen gesichert")
    ok(open(ROOT + "/state/log").read().count("restart") >= 1, "Treiberdienst neu gestartet")
    cmds = []
    for pid in os.listdir("/proc"):
        try:
            c = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if "g19s-gui.py" in c and "--restarted" in c:
            cmds.append(c)
    ok(cmds and not any("testtoken" in c for c in cmds), "Neustart ohne Schlüssel in der Befehlszeile: " + " | ".join(c[-70:] for c in cmds))
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(800)
    ok("2026.09.27-test" in pg.inner_text("#versions"), "Seite zeigt neue Version nach automatischem Neuladen")
    # 3) Verwaltung, die nicht startet -> alte wird wiederhergestellt
    pg.set_input_files("#updateFile", f"{U}/g19s-gui-crash.py")
    pg.wait_for_timeout(1500); pg.wait_for_selector(".gkey", timeout=40000); pg.wait_for_timeout(800)
    ok("test" in ver(BIN + "/g19s-gui.py"), "Defekte Verwaltung: vorherige Version automatisch zurückgeholt")
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(800)
    ok("2026.09.27-test" in pg.inner_text("#versions"), "Verwaltung läuft weiter")
    pg.screenshot(path=ROOT + "/shots/13_update.png", full_page=True)
    # 4) Update von GitHub (Fake-Server: Release-Liste ROOT/upd/gh/releases.json, Dateien ROOT/upd/gh/<tag>/)
    import re as _re, shutil as _sh
    GH = U + "/gh"; _sh.rmtree(GH, ignore_errors=True); os.makedirs(GH)
    def check():
        pg.click("#updateCheck"); pg.wait_for_timeout(1500); return pg.inner_text("#updateResult")
    t = check()
    ok("nicht abrufbar" in t, "GitHub nicht erreichbar: verständliche Meldung: " + t[:70])
    rels = []
    def release(version, notes="", files=None, draft=False, prerelease=False, swap=None):
        tag = "v" + version; os.makedirs(f"{GH}/{tag}", exist_ok=True); assets = []
        for name, src in (files or {}).items():
            txt = _re.sub(r'^VERSION = "[^"]+"', f'VERSION = "{swap or version}"', open(src).read(), count=1, flags=_re.M)
            open(f"{GH}/{tag}/{name}", "w").write(txt)
            assets.append({"name": name, "browser_download_url": f"http://127.0.0.1:8812/gh/download/{tag}/{name}"})
        rels.insert(0, {"tag_name": tag, "name": version, "draft": draft, "prerelease": prerelease, "body": notes,
                        "published_at": "2026-10-01T10:00:00Z", "html_url": f"https://github.com/x/y/releases/tag/{tag}",
                        "assets": assets})
        json.dump(rels, open(GH + "/releases.json", "w"))
    json.dump([], open(GH + "/releases.json", "w"))
    t = check()
    ok("noch keine Version veröffentlicht" in t, "Kein Release: verständliche Meldung: " + t[:70])
    both = {"g19s.py": BIN + "/g19s.py", "g19s-gui.py": BIN + "/g19s-gui.py"}
    release("2026.09.27-test", "- alt", both)
    t = check()
    ok("Keine neuere Version" in t and not pg.is_visible("#updateResult >> text=Jetzt installieren"), "Gleiche Version: nichts anzubieten")
    release("2099.01.01-1", "## Neu\n- **Erste** Neuerung\n- Zweite mit [Link](https://example.org)\n\nSchlusssatz <script>x()</script>", both)
    release("2099.01.02-1", "- Vorabversion", both, prerelease=True)
    release("2099.01.03-1", "- Entwurf", both, draft=True)
    t = check()
    ok("2099.01.01-1" in t and "2099.01.02" not in t and "2099.01.03" not in t, "Entwurf und Vorabversion übersprungen: " + t.replace("\n", " | ")[:100])
    ok("Was ist neu" in t and "Erste Neuerung" in t and "Zweite mit Link" in t and "<script>" in t and "**" not in t,
       "Was ist neu: Text sauber angezeigt, nichts als HTML: " + t.replace("\n", " | ")[-120:])
    ok(pg.locator("#updateResult .relnotes li").count() == 2 and pg.locator("#updateResult script").count() == 0, "Was ist neu: Aufzählung als Liste")
    ok("alt" not in pg.inner_text("#updateResult .relnotes"), "Was ist neu: installierte Version nicht aufgeführt")
    # Datei passt nicht zum Release -> abbrechen
    release("2099.01.04-1", "- falsche Datei", both, swap="2099.01.01-1")
    t = check()
    ok("statt 2099.01.04-1" in t and not pg.is_visible("#updateResult >> text=Jetzt installieren"), "Falsche Version in der Datei: abgelehnt: " + t[:90])
    rels.pop(0); json.dump(rels, open(GH + "/releases.json", "w"))
    # mehrere Versionen übersprungen: Notizen aller neueren Versionen, neueste zuerst
    release("2099.01.05-1", "- Neuerung fünf", {"g19s.py": os.environ["G19S_DRIVER"], "g19s-gui.py": os.environ["G19S_GUI"]})
    t = check()
    ok("2099.01.05-1" in t and pg.is_visible("#updateResult >> text=Jetzt installieren"), "Neuere Version erkannt: " + t.replace("\n", " | ")[:100])
    ok(t.find("Neuerung fünf") < t.find("Erste Neuerung") and t.find("Erste Neuerung") >= 0, "Was ist neu: alle übersprungenen Versionen, neueste zuerst")
    pg.screenshot(path=ROOT + "/shots/13b_update_github.png", full_page=True)
    pg.click("#updateResult >> text=Jetzt installieren"); pg.wait_for_timeout(1000)
    ok(pg.is_visible("#overlay"), "GitHub-Update: Neustart-Hinweis")
    pg.wait_for_selector(".gkey", timeout=30000); pg.wait_for_timeout(800)
    ok("2099.01.05-1" in ver(BIN + "/g19s.py") and "2099.01.05-1" in ver(BIN + "/g19s-gui.py"), "GitHub-Update: beide Dateien ersetzt (Download über Weiterleitung)")
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(800)
    ok("2099.01.05-1" in pg.inner_text("#versions"), "GitHub-Update: neue Verwaltung läuft")
    t = check()
    ok("Keine neuere Version" in t, "Danach: aktuell")
    b.close()
print("Seitenfehler:", errors or "keine")
