import json, os
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
H = ROOT + "/gui/home"; SET = H + "/.config/g19s/settings.json"; MAC = H + "/.config/g19s/macros.json"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
def cfg(): return json.load(open(SET))
def keys(): return json.load(open(MAC))["profiles"][0]["keys"]["M1"]
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1100})
    pg.on("dialog", lambda d: d.accept()); pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    # Textbausteine anlegen
    pg.click("nav >> text=Textbausteine"); pg.wait_for_timeout(300)
    ok("Noch keine Textbausteine" in pg.inner_text("#snippetList"), "Leere Liste")
    for name, grp, text in [("Grußformel", "Büro", "Mit freundlichen Grüßen\nMax Mustermann"), ("Adresse", "Privat", "Musterstr. 1"), ("IBAN", "Büro", "DE00 1234")]:
        pg.click("#addSnippet"); row = pg.locator(".snip").last
        row.locator("input").nth(0).fill(name); row.locator("input").nth(1).fill(grp); row.locator("textarea").fill(text)
    pg.locator(".snip").nth(2).locator("button[title='nach oben']").click()
    ok(pg.locator("#savebar.show").count() == 1, "Speicherleiste erscheint")
    pg.screenshot(path=ROOT + "/shots/19_textbausteine.png", full_page=True)
    pg.click("#saveSettings"); pg.wait_for_timeout(400)
    sn = cfg()["snippets"]
    ok([x["name"] for x in sn] == ["Grußformel", "IBAN", "Adresse"], "Reihenfolge gespeichert: " + ", ".join(x["name"] for x in sn))
    ok(sn[0]["text"] == "Mit freundlichen Grüßen\nMax Mustermann" and sn[0]["group"] == "Büro", "Text mit Zeilenumbruch und Gruppe")
    ok(all(x["paste"] == "ctrl+v" for x in sn), "Neue Textbausteine: über Zwischenablage voreingestellt")
    # Einfügeart je Baustein, Zwischenablage zurückholen abschalten
    pg.locator(".snip").nth(1).locator("select.pasteMode").select_option("ctrl+shift+v")
    pg.locator(".snip").nth(2).locator("select.pasteMode").select_option("")
    ok(not pg.is_checked("#clipRestore"), "Zwischenablage zurückholen: standardmäßig aus (Text bleibt)")
    pg.check("#clipRestore"); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    sn = cfg()["snippets"]
    ok([x["paste"] for x in sn] == ["ctrl+v", "ctrl+shift+v", ""] and cfg()["paste_restore"] is True,
       "Einfügeart je Baustein und Schalter gespeichert: " + json.dumps([x["paste"] for x in sn]))
    pg.reload(); pg.wait_for_selector(".gkey"); pg.click("nav >> text=Textbausteine"); pg.wait_for_timeout(300)
    ok(pg.locator(".snip").nth(1).locator("select.pasteMode").input_value() == "ctrl+shift+v" and pg.is_checked("#clipRestore"),
       "Nach Neuladen: Einfügeart und Schalter wieder da")
    pg.uncheck("#clipRestore"); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    # Aktion Textbausteine
    pg.click("nav >> text=Tasten"); pg.wait_for_timeout(300)
    pg.click(".gkey >> text=G5"); pg.click(".types button >> text=Textbausteine")
    opts = pg.locator("#snipSel option").all_inner_texts()
    ok(opts == ["Liste: alle (3)", "Liste: Gruppe Büro", "Liste: Gruppe Privat", "Direkt einfügen: Grußformel",
                "Direkt einfügen: IBAN", "Direkt einfügen: Adresse"], "Gruppen und einzelne Bausteine zur Auswahl: " + ", ".join(opts))
    pg.select_option("#snipSel", "g:Büro"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(keys()["G5"] == {"snippets": "Büro"}, "G5 = Textbausteine Büro")
    ok("Büro" in pg.inner_text(".gkey >> nth=4"), "Kachel zeigt „Büro“")
    pg.check("#snipKeepOpen"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(keys()["G5"] == {"snippets": "Büro", "keep_open": True}, "G5: Liste bleibt offen")
    pg.click(".gkey >> text=G9"); pg.click(".types button >> text=Textbausteine")
    pg.select_option("#snipSel", "s:IBAN")
    ok(pg.locator("#snipKeepOpen").count() == 0, "Einzelner Baustein: kein Schalter „offen lassen“")
    pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(keys()["G9"] == {"snippets": "*", "snippet": "IBAN"}, "G9 = Baustein IBAN direkt: " + json.dumps(keys().get("G9")))
    ok("IBAN" in pg.inner_text(".gkey >> nth=8"), "Kachel zeigt „IBAN“")
    pg.click(".gkey >> text=G5"); pg.wait_for_timeout(200)
    ok(pg.input_value("#snipSel") == "g:Büro" and pg.is_checked("#snipKeepOpen"), "G5 beim erneuten Öffnen: Gruppe und Schalter")
    # Aktion Timer
    pg.click(".gkey >> text=G6"); pg.click(".types button >> text=Timer")
    pg.click("#editor .seg >> text=Pomodoro")
    nums = pg.locator("#editor input[type=number]"); nums.nth(0).fill("50"); nums.nth(1).fill("10")
    pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(keys()["G6"] == {"timer": {"mode": "pomodoro", "work": 50, "break": 10}}, "G6 = Pomodoro 50/10: " + json.dumps(keys().get("G6")))
    ok("Pomodoro 50/10" in pg.inner_text(".gkey >> nth=5"), "Kachel zeigt Pomodoro")
    pg.click(".gkey >> text=G7"); pg.click(".types button >> text=Timer")
    pg.locator("#editor input[type=number]").fill("15"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(keys()["G7"] == {"timer": {"mode": "timer", "minutes": 15}}, "G7 = Countdown 15 min")
    pg.click(".gkey >> text=G8"); pg.click(".types button >> text=Timer"); pg.click("#editor .seg >> text=Stoppuhr")
    pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(keys()["G8"] == {"timer": {"mode": "stopwatch"}}, "G8 = Stoppuhr")
    pg.click(".gkey >> text=G6"); pg.wait_for_timeout(200)
    ok("active" in pg.get_attribute("#editor .seg >> text=Pomodoro", "class"), "Pomodoro beim erneuten Öffnen gewählt")
    pg.screenshot(path=ROOT + "/shots/20_timer.png", full_page=True)
    # Signalton
    pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(300)
    ok(pg.is_checked("#timerSound"), "Signalton standardmäßig an")
    pg.uncheck("#timerSound"); pg.click("#saveSettings"); pg.wait_for_timeout(400)
    ok(cfg()["timer_sound"] is False, "Signalton aus gespeichert")
    b.close()
print("Seitenfehler:", errors or "keine")
