"""Einstellungs-Schema: streng (Verwaltung) und tolerant (Treiber)."""
import json, os
from common import g, eq, ok, done, TMP

def raises(fn, text):
    try:
        fn()
    except ValueError as ex:
        ok(text in str(ex), f"Fehler „{text}“" + ("" if text in str(ex) else f" – ist „{ex}“"))
        return
    ok(False, f"Fehler „{text}“ erwartet")

full = g.clean_settings({})
eq(set(full), set(g.SCHEMA), "streng: alle Schlüssel des Schemas")
eq(full["night"], {"enabled": False, "start": "22:30", "end": "07:00", "mode": "dim", "brightness": 10, "backlight_off": True},
   "Standardwerte Nachtmodus")
raises(lambda: g.clean_settings({"night": {"start": "25:00", "end": "07:00"}}), "HH:MM")
raises(lambda: g.clean_settings({"colors": {"M1": [1, 2, 999]}}), "Ungültige Farbe für M1")
raises(lambda: g.clean_settings({"backup": {"enabled": True, "folder": " "}}), "bitte einen Ordner")
raises(lambda: g.clean_settings({"news": {"feeds": [{"url": "ftp://x"}]}}), "http://")
raises(lambda: g.clean_settings({"network": {"hosts": [{"host": "a b"}]}}), "Ungültiger Gerätename")
raises(lambda: g.clean_settings({"slideshow": {"interval": "oft"}}), "Wechselzeit")
raises(lambda: g.clean_settings({"weather": {"lat": "Nord"}}), "Koordinaten")
raises(lambda: g.clean_settings([]), "Objekt")
s = g.clean_settings({"volume_step": 99, "screensaver": {"minutes": "2.7", "page": "gibtsnicht"}, "unbekannt": 1,
                      "calendar": {"sources": [{"url": " https://x/a.ics ", "color": [1, 2, 3]}, {"url": ""}, {"url": "u", "color": "rot"}],
                                   "remind": 0},
                      "alarm_clock": {"days": [6, "1", "x", 9, 1]}, "slideshow": {"albums": ["3", 1, 3]}})
eq(s["volume_step"], 25, "Zahl begrenzt")
eq(s["screensaver"], {"enabled": False, "minutes": 2, "page": "slides"}, "Minuten ganzzahlig, unbekannte Seite → Standard")
ok("unbekannt" not in s, "unbekannte Schlüssel entfallen (streng)")
eq(s["calendar"]["sources"], [{"name": "Kalender", "url": "https://x/a.ics", "user": "", "password": "", "color": [1, 2, 3]},
                              {"name": "Kalender", "url": "u", "user": "", "password": ""}], "Kalenderquellen: leer entfällt, ungültige Farbe entfällt")
eq(s["calendar"]["remind"], 0, "Erinnerung 0 = aus bleibt 0")
eq(s["alarm_clock"]["days"], [1, 6], "Wochentage bereinigt")
eq(s["slideshow"]["albums"], [1, 3], "Alben sortiert, doppelt entfernt")
path = os.path.join(TMP, "s.json")
json.dump({"night": {"start": "kaputt"}, "slideshow": {"interval": 30}, "screensaver": {"minutes": 0.1},
           "eigene_notiz": "bleibt", "pages": ["news"]}, open(path, "w"))
t = g.load_settings(path)
eq(t["night"]["start"], "22:30", "tolerant: ungültige Zeit → Standard")
eq((t["slideshow"]["interval"], t["slideshow"]["shuffle"]), (30, True), "tolerant: Unterobjekt ergänzt")
eq(t["screensaver"]["minutes"], 0.1, "tolerant: Bruchteile von Minuten bleiben")
eq(t["eigene_notiz"], "bleibt", "tolerant: unbekannte Schlüssel bleiben")
eq(t["layer_pages"]["M3"], ["news"], "Seiten je Ebene aus pages")
json.dump([1, 2], open(path, "w"))
eq(g.load_settings(path)["volume_step"], 5, "tolerant: kaputte Datei → Standardwerte")
eq(g.DEFAULT_SETTINGS["stations"][0]["name"], "Rockantenne", "DEFAULT_SETTINGS aus dem Schema")
m = g.clean_macros({"profiles": [{"name": " ", "keys": {"M1": {"G3": {"text": "a", "name": ""}, "G4": {}}}}]})
eq(m, {"profiles": [{"name": "Profil 1", "keys": {"M1": {"G3": {"text": "a"}}}}]}, "Makros: leere Einträge entfallen")
raises(lambda: g.clean_macros({"profiles": [{"keys": {"M4": {}}}]}), "Ungültige Ebene")
raises(lambda: g.clean_macros({"profiles": []}), "1 bis 10")
# Befunde der Prüfung (Verhalten wie vor dem Umbau)
raises(lambda: g.clean_settings({"volume_step": "viel"}), "gültige Zahl")
s = g.clean_settings({"start_page": -1, "night": {"start": "22:00", "end": "06:00", "brightness": ""},
                      "keep_backlight": 1, "timer_sound": 0, "calendar": {"remind": None}})
eq(s["start_page"], len(g.PAGE_IDS) - 1, "streng: Startseite −1 = letzte Seite")
eq(s["night"]["brightness"], 0, "streng: leere Nachthelligkeit = 0")
eq((s["keep_backlight"], s["timer_sound"]), (True, True), "streng: Wahrheitswerte wie bisher")
eq(s["calendar"]["remind"], 10, "streng: Erinnerung leer → 10")
json.dump({"colors": {"M1": [1, 2, 3]}, "calendar": {"remind": None}, "screensaver": {"minutes": 600},
           "slideshow": {"albums": [7, "x", 2, 7], "eigen": 1}}, open(path, "w"))
t1, t2 = g.load_settings(path), g.load_settings(path)
t1["colors"]["M2"][0] = 99
eq(t2["colors"]["M2"][0], 0, "tolerant: Standardfarben werden nicht geteilt")
eq(g.DEFAULT_SETTINGS["colors"]["M2"][0], 0, "tolerant: DEFAULT_SETTINGS unverändert")
eq(t1["calendar"]["remind"], 0, "tolerant: Erinnerung leer = aus")
eq(t1["screensaver"]["minutes"], 600, "tolerant: Schoner-Minuten ohne Obergrenze")
eq(t1["slideshow"]["albums"], [7, 2], "tolerant: Albenreihenfolge bleibt, Ungültiges übersprungen")
eq(t1["slideshow"]["eigen"], 1, "tolerant: unbekannte Schlüssel in Unterobjekten bleiben")
done()
