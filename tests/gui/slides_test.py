import json, os, stat
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
H = ROOT + "/gui/home"; SET = H + "/.config/g19s/settings.json"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1000})
    pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e))); pg.on("dialog", lambda d: d.accept())
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    pg.click("nav >> text=Diashow")
    pg.fill("#pwUrl", "127.0.0.1:8811/galerie")          # ohne http:// -> soll trotzdem klappen? (https) -> Fehler erwartet
    pg.click("#pwLoad"); pg.wait_for_timeout(1500)
    ok("⚠" in pg.inner_text("#pwState") or pg.locator(".toast.err").count() > 0 or "Alben" in pg.inner_text("#pwState"), "Adresse ohne http: " + (pg.inner_text("#pwState") or pg.locator(".toast").last.inner_text())[:80])
    pg.fill("#pwUrl", "http://127.0.0.1:8811/galerie"); pg.click("#pwLoad"); pg.wait_for_timeout(800)
    ok(pg.locator(".album").count() == 2, "Öffentliche Alben ohne Anmeldung: %d" % pg.locator(".album").count())
    pg.fill("#pwUser", "max"); pg.fill("#pwPass", "falsch"); pg.click("#pwLoad"); pg.wait_for_timeout(800)
    ok("Anmeldung fehlgeschlagen" in pg.locator(".toast.err").last.inner_text(), "Falsches Passwort wird gemeldet")
    pg.fill("#pwPass", "geheim"); pg.click("#pwLoad"); pg.wait_for_timeout(800)
    ok(pg.locator(".album").count() == 3, "Mit Anmeldung: 3 Alben inkl. privat")
    ok("Italien" in pg.locator(".album").nth(1).inner_text() and "5 Bilder" in pg.locator(".album").nth(0).inner_text(), "Unteralbum eingerückt, Bildanzahl mit Unteralben")
    pg.locator(".album input").nth(0).check(); pg.locator(".album input").nth(2).check()
    ok("2 ausgewählt" in pg.inner_text("#albumSum"), "Auswahl gezählt")
    pg.fill("#slInterval", "15"); pg.uncheck("#slShuffle"); pg.click("#slFit >> text=Display füllen")
    pg.click("#slTest"); pg.wait_for_timeout(1500)
    ok("6 Bilder" in pg.inner_text("#slTestInfo"), "Test: " + pg.inner_text("#slTestInfo"))
    ok((pg.get_attribute("#slPreview", "src") or "").startswith("data:image/png"), "Vorschaubild angezeigt")
    pg.screenshot(path=ROOT + "/shots/10_diashow.png", full_page=True)
    ok(pg.is_visible("#savebar"), "Speicherleiste sichtbar")
    pg.click("#saveSettings"); pg.wait_for_timeout(400)
    s = json.load(open(SET))["slideshow"]
    ok(s == {"url": "http://127.0.0.1:8811/galerie", "user": "max", "password": "geheim", "albums": [1, 3], "recursive": True,
             "interval": 15, "shuffle": False, "fit": "cover", "caption": True, "source": "piwigo", "folder": "", "favorites_only": False}, "Gespeichert: %s" % s)
    mode = stat.S_IMODE(os.stat(SET).st_mode); ok(mode == 0o600, "settings.json nur für den Benutzer lesbar (%o)" % mode)
    # neu laden: Auswahl bleibt, Alben werden automatisch geladen
    pg.reload(); pg.wait_for_selector(".gkey"); pg.click("nav >> text=Diashow"); pg.wait_for_timeout(1200)
    ok(pg.locator(".album input:checked").count() == 2, "Nach Neustart: Alben automatisch geladen, Auswahl erhalten")
    pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(300)
    ok(pg.locator("#pvPages option").count() == 11 and "Bilder" in pg.inner_text("#startPage"), "Seite Bilder als Startseite/Vorschau wählbar")
    b.close()
print("Seitenfehler:", errors or "keine")
