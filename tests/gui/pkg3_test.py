import json
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
H = ROOT + "/gui/home"; SET = H + "/.config/g19s/settings.json"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
def cfg(): return json.load(open(SET))
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1100})
    pg.on("dialog", lambda d: d.accept()); pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    pg.click("nav >> text=Infoseiten"); pg.wait_for_timeout(400)
    ok(pg.locator("#newsFeeds input[type=url]").first.input_value() == "https://www.tagesschau.de/index~rss2.xml", "Standard-Feed tagesschau")
    presets = pg.locator("#newsPresets button").all_inner_texts()
    ok(presets == ["+ heise", "+ SPIEGEL", "+ Golem"], "Vorschläge ohne schon vorhandene: " + ", ".join(presets))
    pg.click("#newsPresets >> text=heise"); pg.wait_for_timeout(200)
    ok(pg.locator("#newsFeeds .feedrow").count() == 2, "heise hinzugefügt")
    row = pg.locator("#newsFeeds .feedrow").first
    row.locator("input[type=url]").fill("http://127.0.0.1:8812/rss.xml")
    row.locator("text=Testen").click(); pg.wait_for_timeout(800)
    ok("✓ 4 Meldungen" in row.inner_text(), "Feed getestet: " + row.inner_text().replace("\n", " ")[-70:])
    pg.click("#newsAdd"); r2 = pg.locator("#newsFeeds .feedrow").last
    r2.locator("input[type=url]").fill("http://127.0.0.1:8812/v1/forecast"); r2.locator("text=Testen").click(); pg.wait_for_timeout(800)
    ok("✗" in r2.inner_text(), "Kein Feed erkannt: " + r2.inner_text().replace("\n", " ")[-60:])
    r2.locator("button[title=entfernen]").click()
    # Video-Feeds: Tagesschau in 100 Sekunden ab Werk, Testen gegen den Nachbau
    vrow = pg.locator("#videoFeeds .feedrow").first
    ok("tagesschau_in_100_sekunden" in vrow.locator("input[type=url]").input_value(), "Video: Tagesschau in 100 Sekunden ab Werk")
    ok(pg.locator("#videoPresets button").count() == 0, "Video: Vorschlag schon vorhanden, nicht doppelt angeboten")
    pg.click("#videoAdd"); vr = pg.locator("#videoFeeds .feedrow").last
    vr.locator("input[type=text]").fill("Test-Videos"); vr.locator("input[type=url]").fill("http://127.0.0.1:8812/video.xml")
    vr.locator("text=Testen").click(); pg.wait_for_timeout(800)
    ok("✓ 3 Videos" in vr.inner_text(), "Video-Feed getestet: " + vr.inner_text().replace("\n", " ")[-70:])
    pg.click("#videoAdd"); vk = pg.locator("#videoFeeds .feedrow").last
    vk.locator("input[type=url]").fill("http://127.0.0.1:8812/rss.xml"); vk.locator("text=Testen").click(); pg.wait_for_timeout(800)
    ok("Keine Videos" in vk.inner_text(), "Feed ohne Videos erkannt: " + vk.inner_text().replace("\n", " ")[-60:])
    vk.locator("button[title=entfernen]").click()
    # Eigene Videolisten: YouTube-Link nachschlagen, Playlist übernehmen, sortieren, Wiedergabe wählen
    ok(pg.input_value("#videoMode") == "browser", "Videolisten: ab Werk im Browser öffnen")
    pg.click("#videoListAdd"); vl = pg.locator("#videoLists .videolist").last
    vl.locator("input[type=text]").first.fill("Musik")
    vl.locator("input[placeholder^='YouTube-Link']").fill("https://youtu.be/dQw4w9WgXcQ?t=5")
    vl.locator("text=Hinzufügen").click(); pg.wait_for_timeout(800)
    vl = pg.locator("#videoLists .videolist").last
    ok("Testkanal" in vl.inner_text() and vl.locator(".videoitem input").first.input_value() == "Testvideo dQw4w9WgXcQ",
       "Videoliste: Titel und Kanal geholt")
    vl.locator("input[placeholder^='YouTube-Link']").fill("https://www.youtube.com/watch?v=xxxxxxxxxxx")
    vl.locator("text=Hinzufügen").click(); pg.wait_for_timeout(800)
    ok("✗" in pg.locator("#videoLists .videolist").last.inner_text(), "Videoliste: unbekanntes Video gemeldet")
    vl = pg.locator("#videoLists .videolist").last
    vl.locator("input[placeholder^='Playlist']").fill("https://www.youtube.com/playlist?list=PLtestliste1234")
    vl.locator("text=Aus Playlist übernehmen").click(); pg.wait_for_timeout(800)
    vl = pg.locator("#videoLists .videolist").last
    ok(vl.locator(".videoitem").count() == 4, f"Videoliste: Playlist übernommen ({vl.locator('.videoitem').count()} Einträge)")
    vl.locator(".videoitem").nth(3).locator("button[title='nach oben']").click()
    vl = pg.locator("#videoLists .videolist").last
    ok(vl.locator(".videoitem input").nth(2).input_value() == "Playlist-Video 3", "Videoliste: Reihenfolge änderbar")
    pg.select_option("#videoMode", "display"); pg.wait_for_timeout(500)
    ok(pg.is_visible("#ytdlpHint") and "pipx install yt-dlp" in pg.inner_text("#ytdlpHint"), "Display-Modus: Hinweis auf yt-dlp")
    ok("yt-dlp" in pg.inner_text("#ytdlpState"), "yt-dlp-Prüfung: " + pg.inner_text("#ytdlpState"))
    pg.uncheck("#videoAutonext")
    # Wetterort für Unwetter
    pg.fill("#wxQ", "leipzig"); pg.click("#wxForm button"); pg.wait_for_timeout(700)
    pg.locator("#wxResults .res").first.click(); pg.wait_for_timeout(900)
    pg.click("#warnTest"); pg.wait_for_timeout(900)
    ok("Markante Warnung: STURMBÖEN" in pg.inner_text("#warnInfo") and "GEWITTER" not in pg.inner_text("#warnInfo"), "Unwetter geprüft: " + pg.inner_text("#warnInfo"))
    pg.uncheck("#warnPopup")
    # Netzwerk
    ok(pg.locator("#netHosts input").nth(1).input_value() == "gateway", "Standard: Router")
    pg.click("#netAdd"); rows = pg.locator("#netHosts .row")
    rows.last.locator("input").nth(0).fill("NAS"); rows.last.locator("input").nth(1).fill("10.0.0.99")
    pg.click("#netTest"); pg.wait_for_timeout(2500)
    t = pg.inner_text("#netInfo")
    ok("✗ 10.0.0.99" in t and "✓ 1.1.1.1" in t, "Netzwerk geprüft: " + t.replace("\n", " | ")[:120])
    # Updates
    pg.uncheck("#updFlatpak"); pg.click("#updTest"); pg.wait_for_timeout(2500)
    ok("4 Paket-Updates (davon 2 Sicherheit)" in pg.inner_text("#updInfo"), "Updates geprüft: " + pg.inner_text("#updInfo"))
    pg.screenshot(path=ROOT + "/shots/24_infoseiten_neu.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(500)
    s = cfg()
    ok([f["url"] for f in s["news"]["feeds"]] == ["http://127.0.0.1:8812/rss.xml", "https://www.heise.de/rss/heise-atom.xml"], "Feeds gespeichert")
    ok(s["warnings"] == {"popup": False} and s["updates"] == {"flatpak": False, "g19s": True}, "Unwetter/Updates-Optionen gespeichert")
    ok(s["network"]["hosts"][-1] == {"name": "NAS", "host": "10.0.0.99"}, "Gerät gespeichert")
    ok([f["url"] for f in s["video"]["feeds"]][1:] == ["http://127.0.0.1:8812/video.xml"], "Video-Feeds gespeichert")
    lst = s["video"]["lists"][0]
    ok(lst["name"] == "Musik" and [i["title"] for i in lst["items"]] == ["Testvideo dQw4w9WgXcQ", "Playlist-Video 1",
       "Playlist-Video 3", "Playlist-Video 2"], "Videoliste gespeichert: " + json.dumps([i["title"] for i in lst["items"]]))
    ok(lst["items"][0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ" and lst["items"][0]["author"] == "Testkanal",
       "Videoliste: Link vereinheitlicht")
    ok(s["video"]["youtube"] == "display" and s["video"]["autonext"] is False, "Wiedergabe-Modus gespeichert")
    # G-Tasten-Art „Video abspielen“
    pg.click("nav >> text=Tasten"); pg.wait_for_timeout(300)
    pg.click(".gkey >> text=G11"); pg.click(".types button >> text=Video abspielen")
    ok("neueste Folge" in pg.inner_text("#editor"), "Video: Erklärung im Editor")
    ok("Eigene Liste: Musik" in pg.inner_text("#editor select"), "Video: eigene Liste wählbar")
    pg.click("#applyBtn"); pg.wait_for_timeout(400)
    mk = json.load(open(H + "/.config/g19s/macros.json"))
    keys = mk["profiles"][0]["keys"]["M1"] if "profiles" in mk else mk["M1"]
    ok(keys.get("G11") == {"video": "latest"}, "G11 = Video abspielen: " + json.dumps(keys.get("G11")))
    ok("Video" in pg.inner_text(".gkey >> nth=10"), "Kachel zeigt „Video“")
    pg.click("nav >> text=Infoseiten"); pg.wait_for_timeout(300)
    # neue Seiten in der Seitenliste und Vorschau
    pg.click("nav >> text=Beleuchtung"); pg.evaluate("document.querySelectorAll('#tab-settings .card[data-sub]').forEach(c => c.hidden = false)"); pg.wait_for_timeout(400)
    names = pg.locator(".pagerow .pn").all_inner_texts()
    ok(all(n in names for n in ["Nachrichten", "Unwetter", "Netzwerk", "Updates", "Video"]), "Neue Seiten in der Liste")
    ok(pg.locator(".pagerow.off", has_text="Nachrichten").count() == 1, "Neue Seiten zunächst aus")
    for i, nm in [(7, "Nachrichten"), (8, "Unwetter"), (9, "Netzwerk"), (10, "Updates")]:
        pg.evaluate("document.querySelector('#lcd').removeAttribute('src')")
        pg.select_option("#pvPages", str(i))
        for _ in range(40):
            if (pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"): break
            pg.wait_for_timeout(150)
        ok((pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"), f"Vorschau {nm}")
        pg.locator("#lcd").screenshot(path=f"{ROOT}/shots/pv_{i}.png")
    pg.locator(".pagerow", has_text="Nachrichten").locator("input").check(); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ok("news" in cfg()["layer_pages"]["M1"] and "news" in cfg()["pages"], "Nachrichten eingeschaltet")
    b.close()
print("Seitenfehler:", errors or "keine")
