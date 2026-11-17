"""Walzer: Zeichenzeit, alle Orte, Tageszeiten, Wetter und Kleidungen, Takt und Drehung, Höhepunkt, Wortbeitrag,
Gags (je Ort, Regenschirm nur bei Regen draußen, abschaltbar), Ortswechsel, Sonnenstand, eigene Fotos (Treiber und
Verwaltung), Sicherung der Fotos, Tastaturfarben."""
import importlib.util
import io
import math
import os
import time
from common import g, eq, ok, done, TMP, PROJ
from PIL import Image

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def weather(kind, wind=10):
    r._party_wx = (time.monotonic() + 1e9, (kind, 5, wind))


def run(o, seconds, **kw):
    img = None
    for _ in range(int(round(seconds * FPS))):
        t = 5000 + T[0]
        s = g.demo_snapshot(t, amp=1.0)
        s.update(active=True, demo=False, t=t)
        s.update(kw)
        img = g.VISUAL_RENDERERS["waltz"](r, s, o, (0, 255, 90))
        T[0] += 1 / FPS
    return r._vis_states["waltz"], img


ok("waltz" in g.VISUAL_STYLES and "waltz" in g.VISUAL_OPTIONS, "Walzer: in Stilliste und Optionen")
ok("waltz" in g.AUTO_POOLS["calm"] and "waltz" in g.AUTO_POOLS["mid"], "Walzer: in der Automatik (ruhig und mittel)")
eq(sorted(g.WALTZ_PLACES), sorted(g.WZ_PLACE_GAG), "Walzer: jeder Ort hat einen eigenen Gag")
o = dict(g.visual_options(r.settings, "waltz"), daytime="day", weather="clear")
weather("sun")
r._vis_states = {}
run(o, 0.5)                                                       # Hintergrund einmal malen
t0 = time.perf_counter()
st, img = run(o, 6.0)
ms = (time.perf_counter() - t0) / (6 * FPS) * 1000
ok(ms < 15, f"Walzer: Zeichenzeit je Bild {ms:.2f} ms")
eq(img.size, (g.WIDTH, g.HEIGHT), "Walzer: Bildgröße")
ok(st["k"] > 0 and st["bar"] > 0, f"Walzer: zählt Schläge und Takte ({st['k']} Schläge, {st['bar']} Takte)")
phi0, th0 = st["phi"], st["theta"]
run(o, 1.0)
ok(st["phi"] != phi0 and st["theta"] != th0, "Walzer: Paar dreht sich und zieht über die Fläche")

# alle Orte bei allen Tageszeiten, alle Wetter, alle Kleidungen
for place in g.WALTZ_PLACES:
    for dtime in ("morning", "day", "evening", "night"):
        r._vis_states = {}
        _, img = run(dict(o, place=place, daytime=dtime), 0.2)
        eq(img.size, (g.WIDTH, g.HEIGHT), f"Walzer: {place}/{dtime}")
for sky in ("clear", "partly", "cloudy", "rain", "snow", "fog", "thunder"):
    for place in ("ballroom", "alm", "lake"):
        r._vis_states = {}
        run(dict(o, place=place, weather=sky), 0.2)
    ok(True, f"Walzer: Wetter {sky}")
for clothes in ("place", "ball", "tracht", "summer", "medieval", "country", "work"):
    r._vis_states = {}
    _, img = run(dict(o, clothes=clothes, dress=[30, 200, 120]), 0.3)
    ok(img is not None, f"Walzer: Kleidung {clothes}")
for tempo in ("vienna", "slow"):
    r._vis_states = {}
    st, _ = run(dict(o, tempo=tempo), 1.0)
    ok(st["phi"] != 0.0, f"Walzer: Tanz {tempo}")
r._vis_states = {}
a, _ = run(dict(o, tempo="vienna"), 2.0)
fast = a["phi"]
r._vis_states = {}
b, _ = run(dict(o, tempo="slow"), 2.0)
ok((2 * math.pi - fast) % (2 * math.pi) > (2 * math.pi - b["phi"]) % (2 * math.pi),
   "Walzer: Wiener Walzer dreht schneller als der langsame")

# Licht: Nacht dunkler als Tag, Leuchtebene nur nachts; Sonnenstand
_, amb_d, glow_d = r._wz_backdrop("castle", 40.0, -1, "clear", None, 0.0)
_, amb_n, glow_n = r._wz_backdrop("castle", -20.0, 1, "clear", None, 0.0)
ok(sum(amb_n) < sum(amb_d) * 0.5 and glow_n > 0.9 and glow_d < 0.05,
   f"Walzer: Nacht dunkel mit Lichtern ({amb_n}, {glow_n}), Tag hell ohne ({amb_d}, {glow_d})")
noon = 1781949600.0                                               # 20. Juni 2026, 12:00 MESZ (10:00 UTC)
r.settings = dict(r.settings, weather={"lat": 52.5, "lon": 13.4, "name": "Berlin"})
alt_noon, _ = r._wz_sun({"daytime": "real"}, noon)
alt_night, _ = r._wz_sun({"daytime": "real"}, noon + 12 * 3600)
ok(alt_noon > 50 and alt_night < -5, f"Walzer: Sonnenstand echt (Mittag {alt_noon:.0f}°, Nacht {alt_night:.0f}°)")
eq(r._wz_sun({"daytime": "night"}), g.WZ_TIMES["night"], "Walzer: Tageszeit fest wählbar")
weather("snow")
eq(r._wz_weather({}, {"weather": "real"})[0], "snow", "Walzer: echtes Wetter von der Wetterseite")
eq(r._wz_weather({}, {"weather": "fog"})[0], "fog", "Walzer: Wetter fest wählbar")
weather("sun")

# Höhepunkt, Drehung unter dem Arm, Wortbeitrag
r._vis_states = {}
st, _ = run(o, 1.0)
st["gag"], st["next_gag"], st["boom"] = None, 1e9, 5000 + T[0]
st, _ = run(o, 2.0)
ok(len(st["sparks"]) > 0, "Walzer: Höhepunkt mit Glitzer")
st, _ = run(o, 3.0)
ok(not (0 <= 5000 + T[0] - st["boom"] < g.WZ_BOOM), "Walzer: Höhepunkt endet")
st["turn"] = 5000 + T[0]
st, _ = run(o, 0.5)
ok(st["turn"] is not None, "Walzer: Drehung unter dem Arm läuft")
st, _ = run(o, 3.0)
ok(st["turn"] is None, "Walzer: Drehung endet")
run(o, 4.0, talk=True, talk_t=5000 + T[0])
ok(st["energy"] < 0.1, "Walzer: Wortbeitrag – das Paar steht")

# Gags: jeder endet; ortsgebundene nur am eigenen Ort; Regenschirm nur bei Regen draußen; abschaltbar
for name, dur in g.WZ_GAGS.items():
    place = next((p for p, n in g.WZ_PLACE_GAG.items() if n == name), "lake")
    r._vis_states = {}
    weather("rain" if name == "regenschirm" else "sun")
    oo = dict(o, place=place, weather="rain" if name == "regenschirm" else "clear")
    st, _ = run(oo, 0.3)
    st["gag"], st["next_gag"] = (name, 5000 + T[0]), 1e9
    st, _ = run(oo, 1.0)
    ok(st["gag"] is not None and st["gag"][0] == name, f"Walzer: Gag „{name}“ läuft")
    st, _ = run(oo, dur)
    ok(st["gag"] is None, f"Walzer: Gag „{name}“ endet")
weather("sun")
seen = set()
for place in g.WALTZ_PLACES:
    r._vis_states = {}
    st, _ = run(dict(o, place=place), 0.2)
    for _ in range(12):
        st["next_gag"] = 0
        st, _ = run(dict(o, place=place), 0.2)
        if st["gag"]:
            seen.add((place, st["gag"][0]))
            st["gag"] = None
bad = [(p, n) for p, n in seen if n not in ("fuss", "schwindel", g.WZ_PLACE_GAG[p])]
ok(not bad and len(seen) >= 12, f"Walzer: Gags passen zum Ort ({len(seen)} gesehen, falsch: {bad})")
r._vis_states = {}
st, _ = run(dict(o, place="ballroom", weather="rain"), 0.2)
st["gag"] = ("regenschirm", 5000 + T[0])
st, _ = run(dict(o, place="ballroom", weather="rain"), 0.2)
ok(st["gag"] is None, "Walzer: kein Regenschirm im Saal")
r._vis_states = {}
st, _ = run(dict(o, gags=False), 0.2)
st["next_gag"] = 0
st, _ = run(dict(o, gags=False), 3.0)
ok(st["gag"] is None, "Walzer: Gags abschaltbar")
labels = dict(g.vis_scenes("waltz"))
ok(all(f"gag:{n}" in labels for n in g.WZ_GAGS), "Walzer: alle Gags in der bewegten Vorschau")

# Ort „Abwechselnd“: neuer Ort beim Liedwechsel
r._vis_states = {}
r._vis_song = "A – Eins"
st, _ = run(dict(o, place="switch"), 0.2)
p1 = st["place"]
r._vis_song = "B – Zwei"
st, _ = run(dict(o, place="switch"), 0.2)
ok(p1 in g.WALTZ_PLACES and st["place"] != p1, f"Walzer: Ortswechsel beim Liedwechsel ({p1} → {st['place']})")
r._vis_song = ""

# eigene Fotos (Treiber): wird benutzt, nachts abgedunkelt; kaputte Datei → gemalter Ort
os.makedirs(g.WALTZ_PHOTO_DIR, exist_ok=True)
path = os.path.join(g.WALTZ_PHOTO_DIR, "alm.jpg")
Image.new("RGB", (800, 500), (200, 40, 40)).save(path, "JPEG")
photo = r._wz_photo("alm")
eq(photo.size, g.WALTZ_PHOTO_SIZE, "Walzer: Foto auf Displaygröße gebracht")
img_d, _, _ = r._wz_backdrop("alm", 40.0, -1, "clear", photo, 0.0)
img_n, _, _ = r._wz_backdrop("alm", -20.0, 1, "clear", photo, 0.0)
pd, pn = img_d.getpixel((160, 60)), img_n.getpixel((160, 60))
ok(pd[0] > 150 and pd[1] < 80, f"Walzer: Foto als Hintergrund ({pd})")
ok(sum(pn) < sum(pd) * 0.6, f"Walzer: Foto nachts abgedunkelt ({pn})")
r._vis_states = {}
_, img = run(dict(o, place="alm"), 0.2)
ok(img.getpixel((5, 40))[0] > 150, "Walzer: Foto im Bild")
_, img = run(dict(o, place="alm", photo=False), 0.2)
ok(img.getpixel((5, 40))[0] < 150, "Walzer: Foto abschaltbar")
time.sleep(0.01)
open(path, "wb").write(b"kein Bild")
os.utime(path, (time.time() + 5, time.time() + 5))
eq(r._wz_photo("alm"), None, "Walzer: kaputtes Foto → gemalter Ort")
os.remove(path)
eq(r._wz_photo("alm"), None, "Walzer: ohne Foto gemalter Ort")

# eigene Fotos (Verwaltung): hochladen, zuschneiden, löschen; nur bekannte Orte; Sicherung
spec = importlib.util.spec_from_file_location("gui", os.environ.get("G19S_GUI", os.path.join(PROJ, "dist", "g19s-gui.py")))
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)
buf = io.BytesIO()
Image.new("RGB", (1200, 900), (20, 120, 220)).save(buf, "PNG")
import base64
url = gui.save_waltz_photo("beach", "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
ok(url and url.startswith("data:image/jpeg;base64,"), "Verwaltung: Foto gespeichert")
saved = Image.open(os.path.join(gui.g.WALTZ_PHOTO_DIR, "beach.jpg"))
eq(saved.size, g.WALTZ_PHOTO_SIZE, "Verwaltung: Foto auf Displaygröße zugeschnitten")
eq(r._wz_photo("beach").getpixel((10, 10))[2] > 180, True, "Treiber sieht das hochgeladene Foto")
for bad_url, why in (("data:text/plain;base64,QUJD", "kein Bild"), ("data:image/png;base64,QUJD", "unlesbar")):
    try:
        gui.save_waltz_photo("beach", bad_url)
        ok(False, f"Verwaltung: {why} abgelehnt")
    except ValueError as ex:
        ok(True, f"Verwaltung: {why} abgelehnt ({ex})")
ok(gui.g.WALTZ_PHOTO_RE.fullmatch(".config/g19s/walzer/beach.jpg")
   and not gui.g.WALTZ_PHOTO_RE.fullmatch(".config/g19s/walzer/../x.jpg"), "Sicherung: nur Fotos der Orte")
home = os.path.join(TMP, "home-walzer")
os.makedirs(os.path.join(home, ".config/g19s/walzer"))
open(os.path.join(home, ".config/g19s/walzer/lake.jpg"), "wb").write(b"x")
open(os.path.join(home, ".config/g19s/walzer/fremd.jpg"), "wb").write(b"x")
mem = g.backup_members(home)
ok(".config/g19s/walzer/lake.jpg" in mem and ".config/g19s/walzer/fremd.jpg" not in mem, "Sicherung: Fotos der Orte dabei")
eq(gui.save_waltz_photo("beach", None), None, "Verwaltung: Foto gelöscht")
ok(not os.path.exists(os.path.join(gui.g.WALTZ_PHOTO_DIR, "beach.jpg")), "Verwaltung: Datei entfernt")
eq(gui.save_waltz_photo("beach", None), None, "Verwaltung: Löschen ohne Foto geht")

# Tastatur: Licht des Ortes, nachts warm, pulsiert mit dem Bass
r._vis_states = {}
run(dict(o, place="castle", daytime="night"), 1.0, bass=1.0)
hi = r.vis_col_waltz
run(dict(o, place="castle", daytime="night"), 1.5, bass=0.0)
lo = r.vis_col_waltz
ok(all(0 <= c <= 255 and c % 8 == 0 for c in hi + lo), f"Walzer: Tastaturfarben gültig und gestuft ({hi}, {lo})")
ok(sum(hi) > sum(lo) and hi[0] > hi[2], f"Walzer: Tastatur warm, pulsiert mit dem Bass ({lo} → {hi})")

# ungültige Messwerte
r._vis_states = {}
run(o, 0.3, bass=float("nan"), level=float("nan"))
st, _ = run(o, 0.3)
ok(st["bass"] == st["bass"] and st["slow"] == st["slow"], "Walzer: nach NaN-Werten wieder gültig")
done()
