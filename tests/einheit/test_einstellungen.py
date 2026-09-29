"""Einstellungen und Makrodatei: Standardwerte, Seiten je Ebene/Profil, altes Format."""
import json
from common import g, eq, ok, done

s = g.load_settings("/gibt/es/nicht")
eq(s["layer_pages"]["M2"], g.DEFAULT_PAGE_ORDER, "Standard: alle Ebenen mit Standardseiten")
ok(s["slideshow"]["favorites_only"] is False and s["timer_sound"] is True, "Standardwerte vorhanden")
data = g.normalize_pages({"pages": ["clock", "news", "unsinn"], "layer_pages": {"M3": ["hardware"]}})
eq(data["layer_pages"], {"M1": ["clock", "news"], "M2": ["clock", "news"], "M3": ["hardware"]}, "Seiten je Ebene ergänzt, Unbekanntes entfernt")
eq(data["pages"], ["clock", "news", "hardware"], "Gesamtliste = alle Ebenen")
m = g.normalize_macros({"M1": {"G1": {"text": "a"}}, "Unsinn": 1})
eq(m, {"profiles": [{"name": "Profil 1", "keys": {"M1": {"G1": {"text": "a"}}}}]}, "altes Format → Profil 1")
m = g.normalize_macros({"profiles": [{"name": "X" * 40, "keys": {}, "pages": {"M1": ["clock"], "M2": ["clock"], "M3": ["news"]},
                                      "colors": {"M1": [1, 2, 3], "M2": [1, 2, 3], "M3": [1, 2, 300]}}] * 12})
eq(len(m["profiles"]), g.MAX_PROFILES, "höchstens 10 Profile")
eq(len(m["profiles"][0]["name"]), 30, "Name gekürzt")
ok("colors" not in m["profiles"][0], "ungültige Farben verworfen")
eq(m["profiles"][0]["pages"]["M3"], ["news"], "Profilseiten übernommen")
eq(g.valid_profile_pages({"M1": ["clock"]}), None, "unvollständige Profilseiten verworfen")
ok(g.in_time_window("23:30", "22:00", "07:00") and g.in_time_window("06:59", "22:00", "07:00"), "Zeitfenster über Mitternacht")
ok(not g.in_time_window("07:00", "22:00", "07:00") and not g.in_time_window("12:00", "12:00", "12:00"), "Zeitfenster: Ende/leer")
done()
