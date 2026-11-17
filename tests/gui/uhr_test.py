"""Karte „Uhr“: Zifferblatt-Optionen, Vorschau, Auswahl fürs Displaymenü, Speichern."""
import json
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
H = ROOT + "/gui/home"; SET = H + "/.config/g19s/settings.json"
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
    pg.click("nav >> text=Beleuchtung"); pg.evaluate("document.querySelectorAll('#tab-settings .card[data-sub]').forEach(c => c.hidden = false)"); pg.wait_for_timeout(500)
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
    pg.locator("#clkLcd").screenshot(path=ROOT + "/shots/uhr_binaer.png")
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
    pg.screenshot(path=ROOT + "/shots/uhr_karte.png", full_page=True)
    ok(pg.is_visible("#saveTop") and pg.is_visible("#saveSettings"), "Speichern oben und unten sichtbar")
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    box = pg.locator("#saveTop").bounding_box()
    ok(box is not None and 0 <= box["y"] < 80, f"Speichern oben bleibt beim Scrollen im Bild ({box})")
    pg.click("#saveTop"); pg.wait_for_timeout(600)
    ok(not pg.is_visible("#saveTop") and not pg.is_visible("#saveSettings"), "Nach dem Speichern beide ausgeblendet")
    c = cfg()["clock"]
    ok(c["binary"]["color_h"] == [255, 48, 48] and c["binary"]["mode"] == "binary" and c["binary"]["digits"] is False,
       "Binäruhr gespeichert: " + json.dumps(c["binary"]))
    ok(c["world"]["cities"][5] == {"name": "Dubai", "tz": "Asia/Dubai"}, "Stadt gespeichert")
    ok(len(c["menu"]) == 24 and "terminal" not in c["menu"], "Menüauswahl gespeichert")
    pg.click("#clkAll"); pg.click("#saveSettings"); pg.wait_for_timeout(500)
    ok(cfg()["clock"]["menu"] == [], "Alle anhaken → leere Liste (= alle)")
    # Visualisierung „Überraschungsparty“: Geburtstagsliste (Festkalender)
    pg.select_option("#visStyle", "party"); pg.wait_for_timeout(300)
    ok("Geburtstage" in pg.inner_text("#visOpts"), "Party: Geburtstagsliste in den Optionen")
    pg.click("#visOpts >> text=+ Geburtstag"); pg.wait_for_timeout(100)
    row = pg.locator("#visOpts .bdayrow").nth(0)
    row.locator("input[type=text]").fill("Max")
    nums = row.locator("input[type=number]")
    nums.nth(0).fill("24"); nums.nth(1).fill("12"); nums.nth(2).fill("1974")
    pg.click("#visOpts >> text=+ Geburtstag"); pg.wait_for_timeout(100)
    pg.locator("#visOpts .bdayrow").nth(1).locator("input[type=text]").fill("Weg")
    pg.locator("#visOpts .bdayrow").nth(1).locator("button").click(); pg.wait_for_timeout(100)
    ok(pg.locator("#visOpts .bdayrow").count() == 1, "Geburtstag entfernen")
    ok(wait_img(pg, "#visLcd"), "Vorschau der Party")
    pg.locator("#visLcd").screenshot(path=ROOT + "/shots/vis_party.png")
    pg.click("#saveSettings"); pg.wait_for_timeout(600)
    v = cfg()["visual"]
    ok(v["style"] == "party" and v["party"]["birthdays"] == [{"name": "Max", "day": 24, "month": 12, "year": 1974}],
       "Geburtstag gespeichert: " + json.dumps(v["party"]["birthdays"]))
    pg.locator("#visOpts .bdayrow").nth(0).locator("input[type=number]").nth(0).fill("31")
    pg.locator("#visOpts .bdayrow").nth(0).locator("input[type=number]").nth(1).fill("4")
    pg.click("#saveSettings"); pg.wait_for_timeout(600)
    ok(cfg()["visual"]["party"]["birthdays"][0]["day"] == 24, "31.4. wird nicht gespeichert")
    ok("Ungültiges Datum" in pg.inner_text("body"), "… mit Meldung")
    pg.click("#discardSettings"); pg.wait_for_timeout(400)              # 31.4. verwerfen
    # Bewegte Vorschau: Gag gezielt zeigen
    pg.select_option("#visStyle", "cellar"); pg.wait_for_timeout(300)
    ok(pg.locator("#visGag option").count() == 12, f"Keller: 12 Gags wählbar ({pg.locator('#visGag option').count()})")
    pg.select_option("#visGag", "gag:vampir")
    first = pg.get_attribute("#visLcd", "src")
    pg.click("#visGagGo"); pg.wait_for_timeout(1500)
    ok(pg.is_visible("#visStop"), "Szene läuft (Stopp sichtbar)")
    srcs = set()
    for _ in range(4):
        srcs.add(pg.get_attribute("#visLcd", "src")); pg.wait_for_timeout(250)
    ok(len(srcs) >= 2 and first not in srcs, "Bilder wechseln (bewegte Vorschau)")
    pg.locator("#visLcd").screenshot(path=ROOT + "/shots/vis_szene_vampir.png")
    pg.click("#visStop"); pg.wait_for_timeout(400)
    ok(not pg.is_visible("#visStop"), "Stopp beendet die Szene")
    pg.select_option("#visStyle", "eq"); pg.wait_for_timeout(300)
    ok(pg.is_disabled("#visGagGo"), "Equalizer: keine Gags")
    # Nur wirksame Optionen: Tänzerin zeigt die Einzeleffekte erst bei „Eigene Auswahl“
    pg.select_option("#visStyle", "dancer"); pg.wait_for_timeout(300)
    n0 = pg.locator("#visOpts .clkopt").count()
    fx = pg.locator("#visOpts label", has_text="Eigene Auswahl:")
    ok(fx.count() == 0, f"Tänzerin: Einzeleffekte ausgeblendet ({n0} Optionen)")
    pg.locator("#visOpts select").nth(2).select_option("custom"); pg.wait_for_timeout(300)
    ok(fx.count() == 11 and pg.locator("#visOpts .clkopt").count() > n0 + 8,
       f"„Eigene Auswahl“ zeigt die Einzeleffekte ({fx.count()})")
    ok(pg.locator("#visOpts .optgroup").count() >= 3 and pg.locator("#visOpts .helpi").count() >= 1,
       "Optionen in Gruppen, mit Hilfe (i)")
    # Fertige Kombination
    pg.click("#visPresets >> text=Gruselabend"); pg.wait_for_timeout(300)
    ok(pg.input_value("#visStyle") == "cellar", "Kombination „Gruselabend“ wählt die Kellertreppe")
    # Walzer: eigenes Foto je Ort hochladen, Vorschau, entfernen
    pg.click("#visPresets >> text=Walzerabend"); pg.wait_for_timeout(600)
    ok(pg.input_value("#visStyle") == "waltz", "Kombination „Walzerabend“ wählt den Walzer")
    ok(pg.locator("#visOpts .wzphoto").count() == 8, f"Walzer: 8 Orte mit Foto ({pg.locator('#visOpts .wzphoto').count()})")
    from PIL import Image as _Im
    _Im.new("RGB", (1600, 1000), (220, 30, 30)).save(ROOT + "/walzer_foto.jpg")
    photo = H + "/.config/g19s/walzer/ballroom.jpg"
    first = pg.locator("#visOpts .wzphoto").nth(0)
    first.locator("input[type=file]").set_input_files(ROOT + "/walzer_foto.jpg")
    for _ in range(30):
        if _os.path.exists(photo):
            break
        pg.wait_for_timeout(150)
    pg.wait_for_timeout(300)
    ok(_os.path.exists(photo) and _Im.open(photo).size == (320, 214), "Walzer: Foto zugeschnitten gespeichert")
    ok(first.locator("img.wzthumb").is_visible(), "Walzer: Vorschaubild des Fotos sichtbar")
    pg.evaluate("document.querySelector('#visLcd').removeAttribute('src')"); pg.wait_for_timeout(100)
    pg.locator("#visOpts select").nth(0).select_option("ballroom")
    ok(wait_img(pg, "#visLcd"), "Walzer: Vorschau mit Foto")
    pg.locator("#visLcd").screenshot(path=ROOT + "/shots/vis_walzer_foto.png")
    first.locator("button[title='Foto entfernen']").click(); pg.wait_for_timeout(600)
    ok(not _os.path.exists(photo) and not first.locator("img.wzthumb").is_visible(), "Walzer: Foto entfernt")
    pg.locator("#visOpts label", has_text="Eigenes Foto").locator("input").uncheck(); pg.wait_for_timeout(300)
    ok(pg.locator("#visOpts .wzphoto").count() == 0, "Walzer: ohne „Eigenes Foto“ keine Fotoliste")
    # Unterreiter, Suche, Einklappen, Änderungspunkt
    pg.click("#setSub >> text=Uhr"); pg.wait_for_timeout(300)
    ok(pg.is_visible("#clkFace") and not pg.is_visible("#visStyle"), "Unterreiter „Uhr“ zeigt nur die Uhr")
    ok(pg.locator("#setSub button.dirty").count() >= 1, "Änderungspunkt am Unterreiter „Visualisierung“")
    pg.fill("#setSearch", "Lautstärke"); pg.wait_for_timeout(300)
    ok(not pg.is_visible("#clkFace") and pg.locator("#tab-settings .card:visible").count() >= 1,
       "Suche zeigt nur passende Karten")
    pg.fill("#setSearch", ""); pg.wait_for_timeout(300)
    pg.click("#tab-settings .card[data-sub=clock] h2"); pg.wait_for_timeout(200)
    ok(not pg.is_visible("#clkFace"), "Karte eingeklappt")
    pg.click("#tab-settings .card[data-sub=clock] h2"); pg.wait_for_timeout(200)
    ok(pg.is_visible("#clkFace"), "… und wieder aufgeklappt")
    pg.click("#saveSettings"); pg.wait_for_timeout(600)
    ok(pg.locator("#tab-settings .card.dirty").count() == 0, "Nach dem Speichern keine Änderungspunkte")
    pg.screenshot(path=ROOT + "/shots/beleuchtung_unterreiter.png", full_page=True)
    b.close()
print("Seitenfehler:", errors or "keine")
ok(not errors, "keine JavaScript-Fehler")
