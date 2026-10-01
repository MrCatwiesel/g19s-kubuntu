import json, time, os
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
T = ROOT + "/gui"; H = T + "/home"
MAC = H + "/.config/g19s/macros.json"; SET = H + "/.config/g19s/settings.json"
URL = "http://127.0.0.1:8799/#testtoken"
errors = []
def _full(): return json.load(open(MAC))
def macros():
    d = _full()
    return d["profiles"][0]["keys"] if "profiles" in d else d
def ok(cond, msg): print(("OK   " if cond else "FEHL ") + msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="light")
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_selector(".gkey")
    pg.screenshot(path=ROOT + "/shots/01_tasten.png")
    ok(pg.locator(".gkey.has").count() == 3, "3 belegte Tasten angezeigt")
    ok("Test-Satz" in pg.inner_text("#keypad"), "Name Test-Satz sichtbar")

    # G1: vorhandenes Makro mit Schritt-Tabelle
    ok(pg.locator("table.steps tbody tr").count() == 20, "G1: 20 Makroschritte geladen")

    # G4: Text – neu über die Zwischenablage (alle Zeichen), umgestellt auf Tippen mit unbekanntem Zeichen
    pg.click(".gkey >> text=G4")
    pg.click(".types button >> text=Text einfügen")
    pg.fill("textarea", "Grüße an alle! @home ✓")
    ok(pg.input_value("#editor select.pasteMode") == "ctrl+v" and pg.locator("#editor .warnbox").count() == 0,
       "Neuer Text: über Zwischenablage voreingestellt, keine Zeichenwarnung")
    pg.select_option("#editor select.pasteMode", "")
    ok("✓" in pg.inner_text("#editor .warnbox"), "Tippen: Warnung für nicht tippbares Zeichen")
    pg.fill("#editor input[type=text]", "Grußformel")
    pg.click("#applyBtn"); pg.wait_for_timeout(300)
    ok(macros()["M1"]["G4"] == {"name": "Grußformel", "text": "Grüße an alle! @home ✓"}, "G4 Text gespeichert")
    pg.click(".gkey >> text=G1"); pg.click(".gkey >> text=G4")
    ok(pg.input_value("textarea") == "Grüße an alle! @home ✓", "G4 wieder geöffnet: Text steht im Feld")
    ok(pg.input_value("#editor input[type=text]") == "Grußformel", "G4 wieder geöffnet: Name steht im Feld")

    # G5: Kombination aufnehmen (Strg+Umschalt+T)
    pg.click(".gkey >> text=G5"); pg.click(".types button >> text=Tastenkombination")
    pg.click("text=⏺ Kombination aufnehmen")
    pg.keyboard.down("Control"); pg.keyboard.down("Shift"); pg.keyboard.down("KeyT")
    pg.keyboard.up("KeyT"); pg.keyboard.up("Shift"); pg.keyboard.up("Control")
    ok("Strg" in pg.inner_text(".chips") and "Umschalt" in pg.inner_text(".chips"), "Kombination erfasst: " + pg.inner_text(".chips").replace("\n", " "))
    pg.screenshot(path=ROOT + "/shots/02_kombination.png")
    pg.click("#applyBtn"); pg.wait_for_timeout(300)
    ok(macros()["M1"]["G5"] == {"combo": "KEY_LEFTCTRL+KEY_LEFTSHIFT+KEY_T"}, "G5 Kombination gespeichert: %s" % macros()["M1"]["G5"])

    # G6: Makro aufnehmen im Fenster
    pg.click(".gkey >> text=G6"); pg.click(".types button >> text=Makro")
    pg.click("text=⏺ Aufnehmen")
    pg.keyboard.press("KeyH"); pg.wait_for_timeout(80); pg.keyboard.press("KeyZ"); pg.keyboard.press("Enter")
    pg.click("text=■ Aufnahme beenden")
    rows = pg.locator("table.steps tbody tr").count()
    ok(rows == 6, f"Makroaufnahme: {rows} Schritte (erwartet 6)")
    pg.click("text=vereinfachen")
    ok(pg.locator("table.steps tbody tr").count() == 3, "Vereinfachen: 3 Tipp-Schritte")
    pg.click("text=+ Schritt")
    last = pg.locator("table.steps tbody tr").last
    last.locator("select").first.select_option("KEY_F5")
    pg.screenshot(path=ROOT + "/shots/03_makro.png", full_page=True)
    pg.click("#applyBtn"); pg.wait_for_timeout(300)
    st = macros()["M1"]["G6"]["steps"]
    ok([s[1] for s in st] == ["KEY_H", "KEY_Z", "KEY_ENTER", "KEY_F5"] and all(s[2] == "tap" for s in st), "G6 Makro gespeichert: %s" % [s[1] for s in st])

    # G7: Radiosender, G8: Musiksteuerung
    pg.click(".gkey >> text=G7"); pg.click(".types button >> text=Radiosender")
    pg.select_option("#editor select", label="Rockantenne"); pg.click("#applyBtn"); pg.wait_for_timeout(300)
    ok(macros()["M1"]["G7"] == {"radio": "https://stream.rockantenne.de/rockantenne/stream/aacp"}, "G7 Radio gespeichert")
    ok("Rockantenne" in pg.inner_text(".gkey >> nth=6"), "Kachel G7 zeigt Rockantenne")
    pg.click(".gkey >> text=G1"); pg.click(".gkey >> text=G7")
    ok(pg.input_value("#editor select") == "https://stream.rockantenne.de/rockantenne/stream/aacp", "Radio wieder geöffnet: Sender ausgewählt")
    pg.click(".gkey >> text=G8"); pg.click(".types button >> text=Musiksteuerung")
    pg.select_option("#editor select", "next"); pg.click("#applyBtn"); pg.wait_for_timeout(300)
    ok(macros()["M1"]["G8"] == {"media": "next"}, "G8 Musiksteuerung gespeichert")
    pg.click(".gkey >> text=G1"); pg.click(".gkey >> text=G8")
    ok(pg.input_value("#editor select") == "next", "Musiksteuerung wieder geöffnet: Aktion ausgewählt")
    pg.click(".gkey >> text=G1")
    ok(pg.locator("table.steps tbody tr").first.locator("select").first.input_value() == "KEY_RIGHTSHIFT", "Makroschritt: Taste korrekt vorausgewählt")

    # Ungespeicherte Änderung + Tastenwechsel -> Rückfrage (Dialog wird bestätigt)
    pg.click(".gkey >> text=G9"); pg.click(".types button >> text=Programm")
    pg.click("text=Terminal"); pg.click(".gkey >> text=G10")
    ok("G9" not in macros().get("M1", {}), "Verworfene Änderung nicht gespeichert")

    # Profil M2, Webseite
    pg.click(".profiles button >> text=M2"); pg.click(".gkey >> text=G1")
    pg.click(".types button >> text=Webseite"); pg.fill("#editor input[type=url]", "www.golem.de")
    pg.click("#applyBtn"); pg.wait_for_timeout(300)
    ok(macros()["M2"]["G1"] == {"open": "https://www.golem.de"}, "M2/G1 Webseite gespeichert (https ergänzt)")
    pg.click(".gkey >> text=G2"); pg.click(".gkey >> text=G1")
    ok(pg.input_value("#editor input[type=url]") == "https://www.golem.de", "Webseite wieder geöffnet: Adresse steht im Feld")
    ok("Strg+F14" in pg.inner_text("#keypad"), "M2 zeigt Strg+F-Tasten")

    # Belegung entfernen
    pg.click(".gkey >> text=G1"); pg.click("text=Belegung entfernen"); pg.wait_for_timeout(300)
    ok("M2" not in macros(), "M2/G1 entfernt, leeres Profil bereinigt")
    pg.click(".profiles button >> text=M1"); pg.click(".gkey >> text=G1")
    pg.screenshot(path=ROOT + "/shots/04_tasten_belegt.png")

    # Externe Änderung (wie MR-Aufnahme) wird übernommen
    m = _full(); m["profiles"][0]["keys"]["M1"]["G12"] = {"name": "Makro G12", "steps": [[0, "KEY_A", "tap"]]}
    json.dump(m, open(MAC, "w")); os.utime(MAC, (time.time() + 5, time.time() + 5))
    pg.wait_for_timeout(3600)
    ok("Makro G12" in pg.inner_text("#keypad"), "Externe Änderung automatisch geladen")

    # Radio-Reiter
    pg.click("nav >> text=Radiosender")
    pg.click("#addStation")
    inputs = pg.locator("#stations tbody tr").last.locator("input")
    inputs.nth(0).fill("Bayern 3"); inputs.nth(1).fill("https://dispatcher.rndfnk.com/br/br3/live/mp3/mid")
    ok(pg.is_visible("#savebar"), "Speicherleiste erscheint")
    pg.locator("#stations tbody tr").last.locator("button[title=Probehören]").click(); pg.wait_for_timeout(700)
    ok(pg.locator("#stations tr.playing").count() == 1, "Probehören markiert den Sender")
    pg.screenshot(path=ROOT + "/shots/05_radio.png", full_page=True)
    pg.click("#stopTest"); pg.wait_for_timeout(300)
    pg.click("#saveSettings"); pg.wait_for_timeout(300)
    s = json.load(open(SET))
    ok([x["name"] for x in s["stations"]] == ["Rockantenne", "Bayern 3"], "Senderliste gespeichert")
    pg.fill("#searchQ", "rock antenne"); pg.click("#searchForm button"); pg.wait_for_timeout(3000)
    ok(pg.locator("#results .warnbox, #results .res").count() >= 1, "Suche liefert Ergebnis oder saubere Fehlermeldung: " + pg.inner_text("#results")[:90].replace("\n", " "))

    # Einstellungen
    pg.click("nav >> text=Beleuchtung")
    for _ in range(40):
        if (pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"): break
        pg.wait_for_timeout(100)
    ok((pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"), "Display-Vorschau geladen")
    pg.check("#brightOn"); pg.locator("#bright").fill("60"); pg.select_option("#startPage", "1")
    pg.click("#pvProfiles >> text=M2"); pg.wait_for_timeout(700)
    pg.screenshot(path=ROOT + "/shots/06_einstellungen.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(300)
    s = json.load(open(SET))
    ok(s["brightness"] == 60 and s["start_page"] == 1, "Helligkeit/Startseite gespeichert")

    # Dienst
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(600)
    pg.click("[data-svc=stop]"); pg.wait_for_timeout(1200)
    ok("gestoppt" in pg.inner_text("#svcActive"), "Dienst stoppen")
    pg.click("[data-svc=start]"); pg.wait_for_timeout(1200)
    ok("läuft" in pg.inner_text("#svcActive") and "läuft" in pg.inner_text("#svcPill"), "Dienst starten")
    pg.click("#toggleAutostart"); pg.wait_for_timeout(1200)
    ok("aus" in pg.inner_text("#svcEnabled"), "Autostart ausschalten")
    pg.click("#toggleAutostart"); pg.wait_for_timeout(1200)
    with pg.expect_download() as dl:
        pg.click("#backupLink")
    path = dl.value.path(); import tarfile
    names = tarfile.open(path).getnames()
    ok(".config/g19s/macros.json" in names and ".config/g19s/settings.json" in names and ".local/bin/g19s.py" in names, "Sicherung: " + ", ".join(names))
    pg.screenshot(path=ROOT + "/shots/07_dienst.png", full_page=True)
    # Wiederherstellen: Makros kaputt machen, dann Sicherung einspielen
    json.dump({"M1": {}}, open(MAC, "w"))
    pg.set_input_files("#restoreFile", path); pg.wait_for_timeout(1500)
    ok("G6" in macros()["M1"], "Wiederherstellung spielt Makros zurück")
    ok(any(f.startswith("vor-wiederherstellung") for f in os.listdir(H + "/.config/g19s")), "Vorheriger Stand automatisch gesichert")

    # Dunkles Design
    pd = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    pd.on("pageerror", lambda e: errors.append(str(e)))
    pd.goto(URL); pd.wait_for_selector(".gkey"); pd.click(".gkey >> text=G4")
    pd.screenshot(path=ROOT + "/shots/08_dunkel.png")
    # schmales Fenster
    pn = b.new_page(viewport={"width": 760, "height": 1000})
    pn.goto(URL); pn.wait_for_selector(".gkey"); pn.screenshot(path=ROOT + "/shots/09_schmal.png", full_page=True)
    b.close()
print("Konsolenfehler:", errors or "keine")
