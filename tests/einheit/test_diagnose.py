"""Anpassende Bildrate, Diagnosewerte, täglicher G19s-Update-Hinweis, Diashow-Speichergrenze, Szenen der Vorschau."""
import json
import os
import tempfile
from common import g, eq, ok, done

# Anpassende Bildrate
eq(g.visual_fps(15), 15, "Ohne Messwert: eingestellte Bildrate")
eq(g.visual_fps(15, 3.0), 15, "3 ms je Bild: volle 15 Bilder/s")
eq(g.visual_fps(15, 3.0, quiet=True), g.VISUAL_FPS_QUIET, "Stille/Wortbeitrag: langsamer")
eq(g.visual_fps(25, 40.0), 12, "Lastbremse: 40 ms je Bild → 12 Bilder/s")
eq(g.visual_fps(15, 200.0), g.VISUAL_FPS_MIN, "Nie unter der Untergrenze")
eq(g.visual_fps(10, 30.0), 10, "Passt noch: unverändert")
ok((g.own_rss_mb() or 0) > 5, f"Eigener Arbeitsspeicher: {g.own_rss_mb():.0f} MB")
s = g.load_settings("/nonexistent")
eq((s["visual"]["adaptive"], s["updates"]["g19s"]), (True, True), "Standard: anpassende Bildrate und Update-Hinweis an")

# Update-Hinweis (Antwort wie GitHub)
rel = [{"tag_name": "v2099.01.01-1", "draft": False, "prerelease": False},
       {"tag_name": "v2099.02.01-1", "draft": True}, {"tag_name": "v2099.03.01-1", "prerelease": True},
       {"tag_name": "v2026.01.01-1"}]
eq(g.g19s_newest(json.dumps(rel).encode()), "2099.01.01-1", "Neuere Version gefunden (ohne Entwürfe/Vorabversionen)")
eq(g.g19s_newest(json.dumps(rel[3:]).encode()), None, "Ältere Version: kein Hinweis")
eq(g.g19s_newest(b"kaputt"), None, "Kaputte Antwort: kein Hinweis")
eq(g.g19s_version_key("2026.11.16-4"), (2026, 11, 16, 4), "Versionsschlüssel")

# Diashow: Speichergrenze nach Größe
d = tempfile.mkdtemp()
show = g.Slideshow.__new__(g.Slideshow)
show.cache_dir = d
show.CACHE_MAX, show.CACHE_MAX_MB = 400, 1
for i in range(6):
    p = os.path.join(d, f"{i}.jpg")
    open(p, "wb").write(b"x" * 300_000)
    os.utime(p, (1000 + i, 1000 + i))
show._prune_cache()
eq(sorted(os.listdir(d)), ["3.jpg", "4.jpg", "5.jpg"], "Älteste Bilder gelöscht, bis höchstens 1 MB übrig ist")

# Szenen der bewegten Vorschau
sc = dict(g.vis_scenes("cellar"))
ok(sc["gag:vampir"] == "Graf Kellerstein" and "boom" in sc and "talk" in sc, "Keller: Höhepunkt, Wortbeitrag, Gags")
eq(len([k for k in sc if k.startswith("gag:")]), len(g.CL_GAGS), "Alle Kellergags wählbar")
ok(any(k.startswith("feier:") for k, _ in g.vis_scenes("xmas")), "Weihnachten: auch Feierabend-Gags")
eq([k for k, _ in g.vis_scenes("eq")], ["play", "boom", "talk"], "Equalizer: ohne Gags")
r = g.Renderer()
r._vis_states = {"cellar": {"crew": [{"mode": "hidden"}], "gag": None, "boom": -99, "booms": 0},
                 "metal": {"gag": None, "boom": -99}}
g.vis_force(r, "cellar", "gag:mumie", 50.0)
eq((r._vis_states["cellar"]["gag"], r._vis_states["cellar"]["crew"][0]["mode"]), (("mumie", 50.0), "idle"),
   "Keller: Gag erzwungen, Bewohner draußen")
g.vis_force(r, "metal", "boom", 60.0)
eq(r._vis_states["metal"]["boom"], 60.0, "Metal: Höhepunkt erzwungen")
done()
