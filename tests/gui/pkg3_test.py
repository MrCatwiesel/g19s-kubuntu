import json
from playwright.sync_api import sync_playwright
H = "/tmp/g19s-test/gui/home"; SET = H + "/.config/g19s/settings.json"
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
    pg.screenshot(path="/tmp/g19s-test/shots/24_infoseiten_neu.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(500)
    s = cfg()
    ok([f["url"] for f in s["news"]["feeds"]] == ["http://127.0.0.1:8812/rss.xml", "https://www.heise.de/rss/heise-atom.xml"], "Feeds gespeichert")
    ok(s["warnings"] == {"popup": False} and s["updates"] == {"flatpak": False}, "Unwetter/Updates-Optionen gespeichert")
    ok(s["network"]["hosts"][-1] == {"name": "NAS", "host": "10.0.0.99"}, "Gerät gespeichert")
    # neue Seiten in der Seitenliste und Vorschau
    pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(400)
    names = pg.locator(".pagerow .pn").all_inner_texts()
    ok(all(n in names for n in ["Nachrichten", "Unwetter", "Netzwerk", "Updates"]), "Neue Seiten in der Liste")
    ok(pg.locator(".pagerow.off", has_text="Nachrichten").count() == 1, "Neue Seiten zunächst aus")
    for i, nm in [(7, "Nachrichten"), (8, "Unwetter"), (9, "Netzwerk"), (10, "Updates")]:
        pg.evaluate("document.querySelector('#lcd').removeAttribute('src')")
        pg.select_option("#pvPages", str(i))
        for _ in range(40):
            if (pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"): break
            pg.wait_for_timeout(150)
        ok((pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"), f"Vorschau {nm}")
        pg.locator("#lcd").screenshot(path=f"/tmp/g19s-test/shots/pv_{i}.png")
    pg.locator(".pagerow", has_text="Nachrichten").locator("input").check(); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ok("news" in cfg()["layer_pages"]["M1"] and "news" in cfg()["pages"], "Nachrichten eingeschaltet")
    b.close()
print("Seitenfehler:", errors or "keine")
