"""iCalendar: Einlesen, Serientermine, Ausnahmen, Zeitzonen, Nextcloud-Adressen."""
import datetime as dt
import os
from common import g, eq, ok, done, PROJ

berlin = dt.datetime(2026, 10, 1, 9, 30).astimezone()          # TZ=Europe/Berlin
ics = open(os.path.join(PROJ, "tests", "fixtures", "kalender.ics"), encoding="utf-8").read()
evs = g.parse_ics(ics)
eq(len(evs), 5, "5 Termine eingelesen")
team = [e for e in evs if e.get("uid") == "a"][0]
eq(team["location"], "Besprechungsraum 2, 3. OG", "Komma im Ort entschlüsselt")
ok("1. Stand der Arbeiten\n2. Termine" in team["description"], "Zeilenumbrüche in der Beschreibung")
items = g.expand_events(evs, 14, now=berlin)
titles = [(i["start"].strftime("%a %d. %H:%M") if not i["allday"] else i["start"].strftime("%a %d. ganztags"), i["title"]) for i in items]
eq(titles[:4], [("Thu 01. ganztags", "Müllabfuhr Papier"), ("Thu 01. 09:00", "Yoga"), ("Thu 01. 09:45", "Zahnarzt"),
                ("Thu 01. 10:00", "Teamrunde Projekt Nordlicht")], "Heute: Reihenfolge, UTC → Ortszeit, laufender Termin")
ok(("Fri 02. ganztags", "Geburtstag Oma") in titles, "Jährlicher Serientermin")
ok(not any(t[1] == "Yoga" and t[0].startswith("Thu 08.") for t in titles), "EXDATE nimmt 8.10. aus")
ok(("Mon 05. 10:00", "Teamrunde Projekt Nordlicht") in titles, "Wöchentlich BYDAY")
eq([t[0] for t in titles if t[1] == "Yoga"], ["Thu 01. 09:00", "Thu 15. 09:00"], "Windows-Zeitzone, COUNT, EXDATE: 1.10. und 15.10.")
eq(g.calendar_url("https://c.de/remote.php/dav/calendars/mde/personal/"), "https://c.de/remote.php/dav/calendars/mde/personal/?export", "CalDAV-Adresse + ?export")
eq(g.calendar_url("https://c.de/index.php/apps/calendar/p/AbC123"), "https://c.de/remote.php/dav/public-calendars/AbC123?export", "Freigabelink umgeschrieben")
eq(g.calendar_url("webcal://c.de/a.ics"), "https://c.de/a.ics", "webcal://")
ok(not g.is_single_calendar("https://c.de/remote.php/dav"), "DAV-Wurzel ist kein einzelner Kalender")
ok(g.is_single_calendar("https://calendar.google.com/x/basic.ics"), "Google-Adresse ist ein Kalender")
eq(len(g.calendar_key("https://x/a.ics")), 12, "Kalenderschlüssel")
done()
