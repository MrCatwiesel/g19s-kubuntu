"""Feeds, Benachrichtigungen, Timer, Lieblingsbilder/Songs, Sicherung."""
import os, tarfile, io
from common import g, eq, ok, done, PROJ, TMP

raw = open(os.path.join(PROJ, "tests", "fixtures", "feed.xml"), "rb").read()
items = g.parse_feed(raw, "t")
eq(len(items), 4, "RSS: 4 Meldungen")
eq(items[2]["title"], "Linux-Kernel 7.2 freigegeben", "HTML im Titel entfernt")
ok(items[0]["time"].tzinfo is not None, "Zeit mit Zeitzone")
atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title><link rel="alternate" href="https://x/a"/><updated>2026-10-01T08:00:00Z</updated></entry></feed>'
eq([(i["title"], i["link"]) for i in g.parse_feed(atom)], [("A", "https://x/a")], "Atom")
lines = ['method call time=1 sender=:1.5 -> destination=:1.2 serial=1 path=/org/freedesktop/Notifications; interface=org.freedesktop.Notifications; member=Notify',
         '   string "Thunderbird"', '   uint32 0', '   string ""', '   string "Neue Mail"', '   string "Hallo"', '   array [', '   ]']
eq(list(g.NotificationWatcher.parse(lines)), [("Thunderbird", "Neue Mail", "Hallo")], "dbus-Benachrichtigung")
t = g.Timer()
t.start({"mode": "timer", "minutes": 1})
t.since -= 61
eq(t.tick(t.since + 61), "done", "Countdown läuft ab")
ok(t.alarm and t.badge() == "!00:00", "Alarm-Anzeige")
t.start({"mode": "pomodoro", "work": 1, "break": 1})
eq(t.tick(t.since + 60.001), "break", "Pomodoro: Pause")
eq((t.phase, t.rounds), ("break", 1), "Runde gezählt")
eq(t.tick(t.since + 60.001), "work", "Pomodoro: weiter")
t.start({"mode": "stopwatch"})
eq(t.tick(t.since + 999), None, "Stoppuhr läuft nie ab")
ok(t.reset() is True and t.active, "Stoppuhr auf 0")
eq(g.fmt_clock(3725), "1:02:05", "Zeitformat")
e = g.remember_song({"title": "Die Ärzte - Schrei nach Liebe", "artist": ""}, {"name": "BOB"})
eq((e["artist"], e["title"], e["source"]), ("Die Ärzte", "Schrei nach Liebe", "BOB"), "Song aus Radiotitel getrennt")
eq(g.remember_song({"title": "Schrei nach Liebe", "artist": "Die Ärzte"}), None, "gleicher Song nicht doppelt")
ok(g.toggle_favorite({"id": 7, "name": "x", "url": "u"}, "folder") is True, "Lieblingsbild gemerkt")
ok(g.toggle_favorite({"id": 7, "name": "x", "url": "u"}, "folder") is False, "Lieblingsbild entfernt")
home = os.path.join(TMP, "home")
os.makedirs(home + "/.config/g19s"); open(home + "/.config/g19s/macros.json", "w").write("{}")
os.makedirs(home + "/bk")
for i in range(4):
    p = g.auto_backup(home + "/bk", keep=2, home=home)
    os.rename(p, p.replace("sicherung-", f"sicherung-0{i}"))
p = g.auto_backup(home + "/bk", keep=2, home=home)
names = tarfile.open(p).getnames()
eq(names, [".config/g19s/macros.json"], "Sicherung enthält vorhandene Dateien")
eq(len([f for f in os.listdir(home + "/bk") if f.endswith(".tar.gz")]), 2, "alte Sicherungen aufgeräumt")
done()
