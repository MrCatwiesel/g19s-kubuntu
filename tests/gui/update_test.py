import json, os, time
from playwright.sync_api import sync_playwright
U = "/tmp/g19s-test/upd"; H = "/tmp/g19s-test/gui/home"; BIN = H + "/.local/bin"
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
    ok(open("/tmp/g19s-test/state/log").read().count("restart") >= 1, "Treiberdienst neu gestartet")
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(800)
    ok("2026.09.27-test" in pg.inner_text("#versions"), "Seite zeigt neue Version nach automatischem Neuladen")
    # 3) Verwaltung, die nicht startet -> alte wird wiederhergestellt
    pg.set_input_files("#updateFile", f"{U}/g19s-gui-crash.py")
    pg.wait_for_timeout(1500); pg.wait_for_selector(".gkey", timeout=40000); pg.wait_for_timeout(800)
    ok("test" in ver(BIN + "/g19s-gui.py"), "Defekte Verwaltung: vorherige Version automatisch zurückgeholt")
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(800)
    ok("2026.09.27-test" in pg.inner_text("#versions"), "Verwaltung läuft weiter")
    pg.screenshot(path="/tmp/g19s-test/shots/13_update.png", full_page=True)
    b.close()
print("Seitenfehler:", errors or "keine")
