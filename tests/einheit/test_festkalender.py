"""Festkalender der Visualisierung: Geburtstage (Liste der Überraschungsparty) und Freitag, der 13. (Kellertreppe);
Geburtstagsliste im Einstellungsschema."""
import datetime as dt
from common import g, eq, ok, done

D = dt.date
bd = [{"name": "Max", "day": 16, "month": 11, "year": 1974}, {"name": "Anna", "day": 16, "month": 11, "year": 0},
      {"name": "Lea", "day": 29, "month": 2, "year": 2004}, {"name": "", "day": 1, "month": 1, "year": 0}]
eq(g.birthdays_today(bd, D(2026, 11, 16)), [("Max", 52), ("Anna", None)], "Zwei Geburtstage heute, Alter nur mit Jahr")
eq(g.birthdays_today(bd, D(2026, 11, 17)), [], "Morgen keiner")
eq(g.birthdays_today(bd, D(2026, 2, 28)), [("Lea", 22)], "29.2. feiert in Nicht-Schaltjahren am 28.2.")
eq(g.birthdays_today(bd, D(2028, 2, 28)), [], "… in Schaltjahren nicht am 28.2.")
eq(g.birthdays_today(bd, D(2028, 2, 29)), [("Lea", 24)], "… sondern am 29.2.")
eq(g.birthdays_today(bd, D(2026, 1, 1)), [], "Einträge ohne Namen zählen nicht")
eq(g.birthdays_today("kaputt", D(2026, 1, 1)), [], "Kaputte Liste: keine Geburtstage")

vis = {"party": {"auto": True, "birthdays": bd}, "cellar": {"fri13": True}}
eq(g.fest_occasion(vis, D(2026, 11, 16)), ("party", "geb:2026-11-16"), "Geburtstag → Überraschungsparty")
eq(g.fest_occasion(vis, D(2026, 11, 13)), ("cellar", "f13:2026-11-13"), "Freitag, der 13. → Kellertreppe")
eq(g.fest_occasion(vis, D(2026, 10, 13)), None, "Dienstag, der 13.: nichts")
eq(g.fest_occasion({"cellar": {"fri13": False}}, D(2026, 11, 13)), None, "Freitag, der 13., abgeschaltet (Standard)")
eq(g.fest_occasion(dict(vis, party={"auto": False, "birthdays": bd}), D(2026, 11, 16)), None,
   "Geburtstage abgeschaltet")
both = {"party": {"birthdays": [{"name": "Tom", "day": 13, "month": 11, "year": 0}]}, "cellar": {"fri13": True}}
eq(g.fest_occasion(both, D(2026, 11, 13))[0], "party", "Geburtstag geht vor Freitag, dem 13.")
eq(g.fest_occasion(None, D(2026, 11, 13)), None, "Ohne Einstellungen: nichts")
eq(g.fest_occasion({}, D(2026, 11, 13)), None, "Standard: Freitag, der 13., aus")

# Schema: Liste wird geprüft (Verwaltung streng, Treiber tolerant)
s = g.clean_settings({"visual": {"party": {"birthdays": [{"name": "Max", "day": 16, "month": 11, "year": 1974}]}}})
eq(s["visual"]["party"]["birthdays"], [{"name": "Max", "day": 16, "month": 11, "year": 1974}], "Geburtstag gespeichert")
eq(s["visual"]["fest_skip"], "", "fest_skip: Standard leer")
eq(s["visual"]["cellar"], {"level": "2", "fri13": False, "keys": "bulb"}, "Kellertreppe: Standardoptionen")
try:
    g.clean_settings({"visual": {"party": {"birthdays": [{"name": "Max", "day": 31, "month": 4, "year": 0}]}}})
    ok(False, "31.4. muss abgelehnt werden")
except ValueError as e:
    ok("Ungültiges Datum" in str(e) and "Max" in str(e), f"31.4. abgelehnt: {e}")
ok(g.clean_settings({"visual": {"party": {"birthdays": [{"name": "Lea", "day": 29, "month": 2, "year": 0}]}}}),
   "29.2. ist erlaubt")
t = g.load_settings("/nonexistent")
eq(t["visual"]["party"]["birthdays"], [], "Treiber: leere Liste als Standard")
eq([o["key"] for o in g.option_list("visual", "party")], ["auto", "round", "dog", "confetti", "keys"],
   "Display-Optionen der Party ohne die Geburtstagsliste")
done()
