import json, os
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
H = ROOT + "/gui/home"; MAC = H + "/.config/g19s/macros.json"; ST = H + "/.config/g19s/state.json"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
answers = []
def on_dialog(d):
    d.accept(answers.pop(0)) if d.type == "prompt" and answers else d.accept()
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1100})
    pg.on("dialog", on_dialog); pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.goto("http://127.0.0.1:8799/#testtoken"); pg.wait_for_selector(".gkey")
    opts = pg.locator("#profSel option")
    ok(opts.count() == 1 and "Profil 1" in opts.first.inner_text() and "aktiv" in opts.first.inner_text(), "Alte Datei: ein Profil „Profil 1“, aktiv")
    ok(pg.locator(".gkey.has").count() == 3, "Bisherige 3 Belegungen übernommen")
    # neues Profil
    answers.append("Spiele"); pg.click("#profNew"); pg.wait_for_timeout(500)
    d = json.load(open(MAC))
    ok([x["name"] for x in d["profiles"]] == ["Profil 1", "Spiele"], "Neues Profil „Spiele“ gespeichert (Datei im neuen Format)")
    ok(pg.locator(".gkey.has").count() == 0 and pg.input_value("#profSel") == "1", "Leeres neues Profil ausgewählt")
    pg.click(".gkey >> text=G1"); pg.click(".types button >> text=Text tippen"); pg.fill("textarea", "gg"); pg.click("#applyBtn"); pg.wait_for_timeout(400)
    ok(json.load(open(MAC))["profiles"][1]["keys"]["M1"]["G1"] == {"text": "gg"}, "G1 im Profil „Spiele“ belegt")
    ok(json.load(open(MAC))["profiles"][0]["keys"]["M1"]["G1"]["name"] == "Test-Satz", "Profil 1 unverändert")
    # Farbe
    pg.locator("#profColors input").nth(0).evaluate("(e) => { e.value = '#ff0000'; e.dispatchEvent(new Event('change', {bubbles: true})); }"); pg.wait_for_timeout(400)
    ok(json.load(open(MAC))["profiles"][1]["colors"]["M1"] == [255, 0, 0], "Eigene Farbe für „Spiele“ gespeichert")
    # aktivieren
    pg.click("text=An der Tastatur aktivieren"); pg.wait_for_timeout(300)
    ok(json.load(open(ST)) == {"profile": 1}, "„Spiele“ an der Tastatur aktiviert (state.json)")
    ok("An der Tastatur aktiv" in pg.inner_text("#profActive"), "Anzeige „An der Tastatur aktiv“")
    # kopieren, umbenennen
    answers.append("Spiele 2"); pg.click("#profCopy"); pg.wait_for_timeout(500)
    d = json.load(open(MAC))
    ok([x["name"] for x in d["profiles"]] == ["Profil 1", "Spiele", "Spiele 2"] and d["profiles"][2]["keys"] == d["profiles"][1]["keys"], "Kopie enthält dieselben Belegungen")
    answers.append("Rennspiele"); pg.click("#profRename"); pg.wait_for_timeout(400)
    ok(json.load(open(MAC))["profiles"][2]["name"] == "Rennspiele", "Umbenannt")
    # verschieben: Rennspiele nach oben -> aktives Profil (Spiele) wandert mit
    pg.click("#profUp"); pg.wait_for_timeout(500)
    d = json.load(open(MAC))
    ok([x["name"] for x in d["profiles"]] == ["Profil 1", "Rennspiele", "Spiele"], "Nach oben verschoben")
    ok(json.load(open(ST))["profile"] == 2, "Aktives Profil zeigt weiter auf „Spiele“")
    # löschen (Rennspiele, liegt vor dem aktiven)
    pg.click("#profDel"); pg.wait_for_timeout(500)
    ok([x["name"] for x in json.load(open(MAC))["profiles"]] == ["Profil 1", "Spiele"], "Gelöscht")
    ok(json.load(open(ST))["profile"] == 1, "Aktives Profil nach Löschen korrigiert")
    # Wechsel an der Tastatur (Treiber schreibt state.json) wird angezeigt
    json.dump({"profile": 0}, open(ST, "w")); pg.wait_for_timeout(3500)
    ok("aktiv" in pg.locator("#profSel option").nth(0).inner_text(), "Wechsel an der Tastatur wird übernommen")
    # Profilwahl im Menü zeigt andere Belegung
    pg.select_option("#profSel", "0"); pg.wait_for_timeout(200)
    ok("Test-Satz" in pg.inner_text("#keypad"), "Profil 1 zeigt seine Belegung")
    pg.select_option("#profSel", "1"); pg.wait_for_timeout(200)
    ok("Test-Satz" not in pg.inner_text("#keypad") and "Text" in pg.inner_text("#keypad"), "„Spiele“ zeigt seine Belegung")
    pg.screenshot(path=ROOT + "/shots/11_profile.png")
    # Obergrenze 10
    for i in range(8):
        answers.append(f"P{i + 3}"); pg.click("#profNew"); pg.wait_for_timeout(350)
    ok(len(json.load(open(MAC))["profiles"]) == 10 and pg.is_disabled("#profNew"), "Höchstens 10 Profile („+ Neu“ gesperrt)")
    # Vorschau nutzt Profilfarben/-namen
    pg.select_option("#profSel", "1"); pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(900)
    ok((pg.get_attribute("#lcd", "src") or "").startswith("data:image/png"), "Displayvorschau mit Profil")
    pg.screenshot(path=ROOT + "/shots/12_vorschau.png")
    b.close()
print("Seitenfehler:", errors or "keine")
