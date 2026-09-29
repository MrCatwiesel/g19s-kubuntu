"""Karte „Uhr“: Zifferblatt-Optionen, Vorschau, Auswahl fürs Displaymenü, Speichern."""
import json
from playwright.sync_api import sync_playwright
H = "/tmp/g19s-test/gui/home"; SET = H + "/.config/g19s/settings.json"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
def cfg(): return json.load(open(SET))
errors = []


def wait_img(pg, sel):
    for _ in range(40):
        if (pg.get_attribute(sel, "src") or "").startswith("data:image/png"):
            return True
        pg.wait_for_timeout(150)
    return False


with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1100})
    pg.on("dialog", lambda d: d.accept()); pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(500)
    ok(pg.locator("#clkFace option").count() == 25, "25 Zifferblätter wählbar")
    ok(pg.locator(".pagerow .pn").all_inner_texts().count("Uhr") == 1, "in der Seitenliste nur „Uhr“")
    ok(wait_img(pg, "#clkLcd"), "Vorschau Digitaluhr")
    # Binäruhr: Farben für Stunden/Minuten/Sekunden, Darstellung
    pg.select_option("#clkFace", "binary"); pg.wait_for_timeout(300)
    opts = pg.locator("#clkOpts .clkopt")
    ok(opts.count() == 6, f"Binäruhr: 6 Einstellungen ({opts.count()})")
    row = opts.nth(0)
    ok("Farbe der Ebene" in row.inner_text(), "Standard: Farbe der Ebene")
    row.locator("select").select_option("own")
    row.locator("input[type=color]").evaluate("e => { e.value = '#ff3030'; e.dispatchEvent(new Event('input')); }")
    opts.nth(4).locator("select").select_option("binary")
    pg.evaluate("document.querySelector('#clkLcd').removeAttribute('src')"); pg.wait_for_timeout(100)
    opts.nth(5).locator("input").uncheck()
    ok(wait_img(pg, "#clkLcd"), "Vorschau Binäruhr aktualisiert")
    pg.locator("#clkLcd").screenshot(path="/tmp/g19s-test/shots/uhr_binaer.png")
    # Weltzeituhr: Stadt tauschen
    pg.select_option("#clkFace", "world"); pg.wait_for_timeout(300)
    sels = pg.locator("#clkOpts .clkcities select")
    ok(sels.count() == 6 and sels.nth(0).input_value() == "Europe/Berlin", "Weltzeituhr: 6 Städte, Berlin zuerst")
    sels.nth(5).select_option("Asia/Dubai")
    # Displaymenü: Terminal abwählen
    pg.locator("#clkMenu label", has_text="Terminal").locator("input").uncheck()
    # Zifferblatt ohne Einstellungen
    pg.select_option("#clkFace", "radar"); pg.wait_for_timeout(300)
    ok("keine Einstellungen" in pg.inner_text("#clkOpts"), "Radaruhr ohne Einstellungen")
    pg.screenshot(path="/tmp/g19s-test/shots/uhr_karte.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(600)
    c = cfg()["clock"]
    ok(c["binary"]["color_h"] == [255, 48, 48] and c["binary"]["mode"] == "binary" and c["binary"]["digits"] is False,
       "Binäruhr gespeichert: " + json.dumps(c["binary"]))
    ok(c["world"]["cities"][5] == {"name": "Dubai", "tz": "Asia/Dubai"}, "Stadt gespeichert")
    ok(len(c["menu"]) == 24 and "terminal" not in c["menu"], "Menüauswahl gespeichert")
    pg.click("#clkAll"); pg.click("#saveSettings"); pg.wait_for_timeout(500)
    ok(cfg()["clock"]["menu"] == [], "Alle anhaken → leere Liste (= alle)")
    # Vorschau der Seite „Uhr“ zeigt das am Display gewählte Zifferblatt des Profils
    b.close()
print("Seitenfehler:", errors or "keine")
ok(not errors, "keine JavaScript-Fehler")
