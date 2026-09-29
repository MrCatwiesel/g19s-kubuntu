"""Zifferblätter der Uhr: Prüfung in macros.json und Umstellung der alten Uhrenseiten."""
import json, os
from common import g, eq, ok, done, TMP

eq(g.valid_clock_faces({"M1": "station", "M2": "digital", "M3": "gibtsnicht", "M4": "chrono"}), {"M1": "station"},
   "nur gültige Zifferblätter, Digitaluhr ohne Eintrag")
eq(g.valid_clock_faces({"M1": "digital"}), None, "nur Digitaluhr → kein Eintrag")
m = g.clean_macros({"profiles": [{"name": "A", "keys": {}, "clock": {"M3": "binary"}}]})
eq(m["profiles"][0].get("clock"), {"M3": "binary"}, "Verwaltung behält das Zifferblatt beim Speichern")
eq(g.normalize_macros({"profiles": [{"keys": {}, "clock": {"M2": "chrono"}}]})["profiles"][0].get("clock"),
   {"M2": "chrono"}, "Treiber liest das Zifferblatt")
g.PAGE_IDS.index("clock")
ok(not any(p.startswith("clock_") for p in g.PAGE_IDS), "keine eigenen Uhrenseiten mehr")

sp, mp = os.path.join(TMP, "u_settings.json"), os.path.join(TMP, "u_macros.json")
json.dump({"pages": ["clock_station", "news"], "screensaver": {"page": "clock_binary", "enabled": True},
           "layer_pages": {"M1": ["clock", "clock_station", "news"], "M2": ["news"], "M3": ["clock_chrono"]},
           "eigene_notiz": 1}, open(sp, "w"))
json.dump({"profiles": [{"name": "A", "keys": {}},
                        {"name": "B", "keys": {}, "clock": {"M1": "binary"}},
                        {"name": "C", "keys": {}, "pages": {"M1": ["clock_steampunk"], "M2": ["clock"], "M3": ["news"]}}]},
          open(mp, "w"))
logs = []
g.migrate_clock_pages(sp, mp, logs.append)
s, m = json.load(open(sp)), json.load(open(mp))
eq(s["layer_pages"], {"M1": ["clock", "news"], "M2": ["news"], "M3": ["clock"]}, "alte Uhrenseiten → Uhr (doppelt entfernt)")
eq((s["pages"], s["screensaver"]["page"], s["eigene_notiz"]), (["clock", "news"], "clock", 1), "Gesamtliste, Bildschirmschoner, Rest bleibt")
eq([p.get("clock") for p in m["profiles"]], [{"M1": "station", "M3": "chrono"}, {"M1": "binary", "M3": "chrono"}, {"M1": "steampunk"}],
   "Zifferblätter: Standardseiten für Profile ohne eigene Seiten, eigene Wahl bleibt, eigene Seiten eigenes Blatt")
eq(m["profiles"][2]["pages"]["M1"], ["clock"], "eigene Seiten umgestellt")
eq(len(logs), 2, "Umstellung protokolliert")
logs.clear()
g.migrate_clock_pages(sp, mp, logs.append)
eq(logs, [], "zweiter Lauf ändert nichts")
json.dump({"layer_pages": {"M1": ["clock_chrono"]}}, open(sp, "w"))
g.migrate_clock_pages(sp, mp, logs.append)
ok("pages" not in json.load(open(sp)), "fehlende Gesamtliste bleibt fehlend (nicht null)")

# Seite „System“ (bis 2026.09.29-2) → Hardware, Startseite umrechnen
ok("system" not in g.PAGE_IDS, "keine Seite System mehr")
for old_start, want in ((2, "hardware"), (4, "slides"), (11, "updates"), (1, "music")):
    json.dump({"start_page": old_start, "layer_pages": {"M1": ["system", "clock", "hardware"], "M2": ["system"]},
               "screensaver": {"page": "system"}}, open(sp, "w"))
    json.dump({"profiles": [{"name": "A", "keys": {}, "pages": {"M1": ["system"], "M2": ["clock"], "M3": ["news", "system"]}}]}, open(mp, "w"))
    logs.clear()
    g.migrate_system_page(sp, mp, logs.append)
    s2, m2 = json.load(open(sp)), json.load(open(mp))
    eq(g.PAGE_IDS[s2["start_page"]], want, f"Startseite {old_start} → {want}")
eq(s2["layer_pages"], {"M1": ["hardware", "clock"], "M2": ["hardware"]}, "System → Hardware, doppelt entfernt")
eq((s2["screensaver"]["page"], s2["pages_rev"], "pages" in s2), ("hardware", 2, False), "Schoner, Marker, keine neue Gesamtliste")
eq(m2["profiles"][0]["pages"], {"M1": ["hardware"], "M2": ["clock"], "M3": ["news", "hardware"]}, "eigene Seiten im Profil umgestellt")
eq(len(logs), 2, "Umstellung protokolliert")
logs.clear()
g.migrate_system_page(sp, mp, logs.append)
eq((logs, json.load(open(sp))["start_page"]), ([], g.PAGE_IDS.index("updates") if False else s2["start_page"]), "zweiter Lauf ändert nichts")
eq(g.clean_settings({})["pages_rev"], 2, "Verwaltung speichert den Marker mit")

# Optionen, Schema, fps
eq(set(g.CLOCK_RENDERERS), set(g.CLOCK_FACES), "alle 25 Zifferblätter haben eine Zeichenfunktion")
eq(len(g.CLOCK_FACES), 25, "25 Zifferblätter")
st = g.clean_settings({"clock": {"binary": {"color_h": [1, 2, 3], "mode": "quatsch"}, "menu": ["radar", "gibtsnicht", "radar"]}})
eq((st["clock"]["binary"]["color_h"], st["clock"]["binary"]["mode"], st["clock"]["menu"]), ([1, 2, 3], "bcd", ["radar"]),
   "Schema: Farbe, ungültige Auswahl → Standard, Menüliste bereinigt")
try:
    g.clean_settings({"clock": {"world": {"cities": [{"name": "X", "tz": "Mars/Olympus"}]}}})
    ok(False, "unbekannte Zeitzone abgelehnt")
except ValueError as ex:
    ok("Zeitzone" in str(ex), "unbekannte Zeitzone abgelehnt")
try:
    g.clean_settings({"clock": {"binary": {"color_s": [1, 2]}}})
    ok(False, "ungültige Farbe abgelehnt")
except ValueError as ex:
    ok("Farbe Sekunden" in str(ex), "ungültige Farbe abgelehnt: " + str(ex))
eq(g.clock_options({"clock": {"station": {"smooth": True, "fremd": 1}}}, "station"),
   {"seconds": True, "smooth": True, "side": True}, "Optionen: Standard + eigene, Fremdes ignoriert")
eq((g.clock_fps("pendulum", {}), g.clock_fps("pendulum", {"clock": {"pendulum": {"swing": False}}}), g.clock_fps("digital", {})),
   (5, 1, 1), "fps je Zifferblatt/Option")
ok(all(1 <= g.clock_fps(f, {}) <= 5 for f in g.CLOCK_FACES), "fps zwischen 1 und 5")

# Jedes Zifferblatt zu kritischen Zeiten und in allen Ebenen zeichnen (darf nie abstürzen, < 250 ms)
import datetime as dt, time as _t
os.environ["TZ"] = "Europe/Berlin"; _t.tzset()
r = g.Renderer()
times = ["2026-01-01 00:00:00", "2026-03-29 02:30:00", "2026-03-29 03:00:01", "2026-06-21 12:00:00",
         "2026-10-25 02:30:00", "2026-12-31 23:59:59", "2027-02-28 13:05:30"]
bad, slow = [], []
for variant in ({}, {"weather": {"name": "Tromsø", "lat": 69.65, "lon": 18.96}}, {"weather": {"name": "", "lat": None, "lon": None}}):
    r.settings = dict(g.DEFAULT_SETTINGS, **variant)
    for face in g.CLOCK_FACES:
        r.clock_face = face
        for i, ts in enumerate(times):
            r.fixed_time = dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").timestamp() + 0.37 * i
            try:
                t0 = _t.perf_counter()
                img = r.render(0, ("M1", "M2", "M3")[i % 3], {})
                if i and _t.perf_counter() - t0 > 0.25:
                    slow.append(f"{face} {ts}")
                if img.size != (320, 240):
                    bad.append(f"{face}: Größe {img.size}")
            except Exception as ex:
                bad.append(f"{face} {ts}: {type(ex).__name__}: {ex}")
eq(bad, [], "alle Zifferblätter zu allen Testzeiten gezeichnet")
eq(slow, [], "kein Bild langsamer als 250 ms")
done()
