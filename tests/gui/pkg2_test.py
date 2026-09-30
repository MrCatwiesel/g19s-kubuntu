import json, os, glob, shutil
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
H = ROOT + "/gui/home"; C = H + "/.config/g19s"; SET = C + "/settings.json"; MAC = C + "/macros.json"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
def cfg(): return json.load(open(SET))
def mac(): return json.load(open(MAC))
json.dump([{"time": "2026-09-27 21:14", "artist": "AC/DC", "title": "Thunderstruck", "source": "Rockantenne"},
           {"time": "2026-09-28 08:02", "artist": "Die Ärzte", "title": "Schrei nach Liebe", "source": "Radio BOB!"}], open(C + "/songs.json", "w"))
json.dump([{"id": 201, "name": "Foto 201", "url": "http://127.0.0.1:8811/upload/201.jpg", "local": False,
            "source": "piwigo:http://127.0.0.1:8811", "page": "http://127.0.0.1:8811/picture.php?/201", "time": "2026-09-28 09:00"},
           {"id": 102, "name": "Foto 102", "url": "http://127.0.0.1:8811/upload/102.jpg", "local": False,
            "source": "piwigo:http://127.0.0.1:8811", "page": "http://127.0.0.1:8811/picture.php?/102", "time": "2026-09-28 09:05"}], open(C + "/favorites.json", "w"))
shutil.rmtree(H + "/Sicherungen", ignore_errors=True); os.makedirs(H + "/Sicherungen")
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1100})
    pg.on("dialog", lambda d: d.accept()); pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    # neue Aktionen
    pg.click(".gkey >> text=G9"); pg.click(".types button >> text=Einschlaftimer")
    pg.locator("#editor input[type=number]").fill("45"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    k = mac()["profiles"][0]["keys"]["M1"]
    ok(k.get("G9") == {"sleep": 45}, "G9 = Einschlaftimer 45")
    pg.click(".gkey >> text=G10"); pg.click(".types button >> text=Mikrofon stumm"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(mac()["profiles"][0]["keys"]["M1"].get("G10") == {"mic": "toggle"}, "G10 = Mikrofon")
    pg.click(".gkey >> text=G11"); pg.click(".types button >> text=Musiksteuerung")
    pg.select_option("#editor select", "remember"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(mac()["profiles"][0]["keys"]["M1"].get("G11") == {"media": "remember"}, "G11 = Song merken")
    ok("Song merken" in pg.inner_text(".gkey >> nth=10"), "Kachel „Song merken“")
    # Seiten je Profil
    pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(400)
    ok(pg.locator("#plScope option").count() == 2, "Auswahl: Standard + 1 Profil")
    pg.select_option("#plScope", "0"); pg.wait_for_timeout(200)
    ok("verwendet die Standard-Seiten" in pg.inner_text("#pageList"), "Profil nutzt zunächst Standard")
    pg.click("#pageList >> text=Eigene Seiten für dieses Profil festlegen"); pg.wait_for_timeout(600)
    ok(isinstance(mac()["profiles"][0].get("pages"), dict), "Profil hat eigene Seiten (macros.json)")
    pg.locator(".pagerow", has=pg.get_by_text("Uhr", exact=True)).locator("input").uncheck(); pg.wait_for_timeout(600)
    pp = mac()["profiles"][0]["pages"]
    ok("clock" not in pp["M1"] and "clock" in pp["M2"], "Uhr nur in M1 des Profils aus: " + ",".join(pp["M1"]))
    ok("clock" in cfg().get("layer_pages", {}).get("M1", ["clock"]) if os.path.exists(SET) else True, "Standard unverändert")
    ok("eigene Seiten" in pg.inner_text("#plScope"), "Auswahl zeigt „eigene Seiten“")
    pg.screenshot(path=ROOT + "/shots/21_seiten_profil.png", full_page=True)
    pg.click("#plOwnOff"); pg.wait_for_timeout(600)
    ok("pages" not in mac()["profiles"][0], "Wieder Standard verwendet")
    # Terminerinnerung
    pg.click("nav >> text=Infoseiten"); pg.wait_for_timeout(300)
    pg.select_option("#calRemind", "15"); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ok(cfg()["calendar"]["remind"] == 15, "Erinnerung 15 Min. gespeichert")
    # Radiowecker und Songs
    pg.click("nav >> text=Radiosender"); pg.wait_for_timeout(700)
    ok("Thunderstruck" in pg.inner_text("#songs") and "Schrei nach Liebe" in pg.inner_text("#songs"), "Gemerkte Songs angezeigt")
    ok(pg.locator("#songs a", has_text="YouTube").first.get_attribute("href").endswith("Die%20%C3%84rzte%20Schrei%20nach%20Liebe"), "YouTube-Link (neuester zuerst)")
    pg.click("#addStation"); rows = pg.locator("#stations tbody tr")
    rows.last.locator("input").nth(0).fill("Rockantenne"); rows.last.locator("input").nth(1).fill("https://stream.rockantenne.de/rockantenne/stream/mp3")
    pg.check("#acOn"); pg.fill("#acTime", "06:30"); pg.click("#acDays >> text=Sa")
    pg.wait_for_timeout(200)
    pg.screenshot(path=ROOT + "/shots/22_radiowecker.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ac = cfg()["alarm_clock"]
    ok({k: ac[k] for k in ("enabled", "time", "days")} == {"enabled": True, "time": "06:30", "days": [0, 1, 2, 3, 4, 5]}
       and ac["station"] in [x["url"] for x in cfg()["stations"]], "Radiowecker gespeichert: " + json.dumps(ac))
    pg.locator("#songs tr", has_text="Thunderstruck").locator("button").click(); pg.wait_for_timeout(400)
    ok([x["title"] for x in json.load(open(C + "/songs.json"))] == ["Schrei nach Liebe"], "Song entfernt")
    # Lieblingsbilder
    pg.click("nav >> text=Diashow"); pg.wait_for_timeout(700)
    ok("2 Lieblingsbilder" in pg.inner_text("#favs"), "Lieblingsbilder angezeigt")
    ok(pg.locator("#favs a").first.get_attribute("href") == "http://127.0.0.1:8811/picture.php?/102", "Link zu Piwigo")
    pg.check("#favOnly"); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ok(cfg()["slideshow"]["favorites_only"] is True, "Nur Lieblingsbilder gespeichert")
    pg.locator("#favs tr", has_text="Foto 201").locator("button").click(); pg.wait_for_timeout(400)
    ok([f["id"] for f in json.load(open(C + "/favorites.json"))] == [102], "Lieblingsbild entfernt")
    # automatische Sicherung
    pg.click("nav >> text=Dienst"); pg.wait_for_timeout(700)
    ok("Noch keine automatische Sicherung" in pg.inner_text("#abStatus"), "Status: noch keine")
    pg.check("#abOn"); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ok("bitte einen Ordner" in pg.inner_text("#toasts") and "enabled" not in (cfg().get("backup") or {}) or not cfg()["backup"]["enabled"], "Ohne Ordner abgelehnt")
    pg.click("#abBrowse"); pg.wait_for_timeout(500)
    pg.click("#abBrowser .frow >> text=Sicherungen"); pg.wait_for_timeout(400)
    pg.click("#abBrowser >> text=Diesen Ordner wählen"); pg.wait_for_timeout(200)
    ok(pg.input_value("#abFolder") == "~/Sicherungen", "Ordner gewählt")
    pg.select_option("#abDays", "3"); pg.fill("#abKeep", "5")
    pg.click("#saveSettings"); pg.wait_for_timeout(400)
    bk = cfg()["backup"]
    ok({k: bk[k] for k in ("enabled", "target", "folder", "days", "keep")} == {"enabled": True, "target": "folder", "folder": "~/Sicherungen", "days": 3, "keep": 5}, "Sicherung eingestellt: " + json.dumps(bk))
    pg.click("#abNow"); pg.wait_for_timeout(900)
    files = glob.glob(H + "/Sicherungen/g19s-sicherung-*.tar.gz")
    ok(len(files) == 1, "Jetzt sichern: Datei angelegt")
    ok("Letzte Sicherung" in pg.inner_text("#abStatus"), "Status aktualisiert")
    import tarfile
    names = tarfile.open(files[0]).getnames() if files else []
    ok(".config/g19s/songs.json" in names and ".config/g19s/favorites.json" in names, "Songs und Lieblingsbilder mitgesichert")
    # Nextcloud: Verbindung testen, sichern, speichern
    pg.select_option("#abTarget", "nextcloud"); pg.wait_for_timeout(200)
    ok(not pg.is_visible("#abFolder") and pg.is_visible("#abDir") and "App-Passwort" in pg.inner_text("#abHint"), "Nextcloud-Felder sichtbar")
    pg.fill("#abUrl", "http://127.0.0.1:8812/nc"); pg.fill("#abUser", "mde@example.de"); pg.fill("#abPw", "falsch")
    pg.click("#abTest"); pg.wait_for_timeout(1200)
    ok("Anmeldung abgelehnt" in pg.inner_text("#abStatus"), "Test mit falschem Passwort: " + pg.inner_text("#abStatus"))
    pg.fill("#abPw", "app-pw"); pg.fill("#abDir", "Backups/G19s")
    pg.click("#abTest"); pg.wait_for_timeout(1200)
    ok("Verbindung in Ordnung" in pg.inner_text("#abStatus"), "Test Nextcloud: " + pg.inner_text("#abStatus"))
    pg.click("#abNow"); pg.wait_for_timeout(1500)
    ok("remote.php/dav/files/mde@example.de/Backups/G19s/g19s-sicherung-" in pg.inner_text("#abStatus"), "In die Nextcloud gesichert: " + pg.inner_text("#abStatus"))
    pg.screenshot(path=ROOT + "/shots/23_autosicherung.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(500)
    bk = cfg()["backup"]
    ok((bk["target"], bk["url"], bk["user"], bk["password"], bk["remote_dir"]) == ("nextcloud", "http://127.0.0.1:8812/nc", "mde@example.de", "app-pw", "Backups/G19s"), "Nextcloud gespeichert")
    # NAS (SMB): Freigabe fehlt → verständliche Meldung, dann richtig
    shutil.rmtree(ROOT + "/smb/nas/backup/G19s", ignore_errors=True); os.makedirs(ROOT + "/smb/nas/backup/G19s")
    pg.select_option("#abTarget", "smb"); pg.wait_for_timeout(200)
    pg.fill("#abUrl", "\\\\nas\\backup\\Fehlt"); pg.fill("#abUser", "nas"); pg.fill("#abPw", "geh%eim")
    pg.click("#abTest"); pg.wait_for_timeout(1200)
    ok("Ordner nicht gefunden" in pg.inner_text("#abStatus"), "SMB Ordner fehlt: " + pg.inner_text("#abStatus"))
    pg.fill("#abUrl", "\\\\nas\\backup\\G19s"); pg.click("#abNow"); pg.wait_for_timeout(1500)
    ok(len(glob.glob(ROOT + "/smb/nas/backup/G19s/g19s-sicherung-*.tar.gz")) == 1, "Auf das NAS gesichert: " + pg.inner_text("#abStatus"))
    b.close()
print("Seitenfehler:", errors or "keine")
