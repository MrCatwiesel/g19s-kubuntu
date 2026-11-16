"""Weihnachten: jugendfreie Gags ohne Feierabend (Option gags), neue Feierabend-Gags, Sprechblasen mit Umbruch."""
import time
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
r._party_wx = (time.monotonic() + 1e9, (None, None, None))
FPS = 15
T = [0.0]


def opts(**kw):
    r.settings["visual"]["xmas"].update(kw)
    return g.visual_options(r.settings, "xmas")


O = opts()


def frame(o=None, **kw):
    t = 5000 + T[0]
    s = g.demo_snapshot(t)
    s.update(active=True, demo=False, t=t)
    s.update(kw)
    g.VISUAL_RENDERERS["xmas"](r, s, o or O, (0, 255, 90))
    T[0] += 1 / FPS
    return r._vis_states["xmas"]


def run(seconds, **kw):
    st = None
    for _ in range(int(round(seconds * FPS))):
        st = frame(**kw)
    return st


eq(O["gags"], True, "Gags ohne Feierabend: Standard an")
eq(len(g.FUN_GAGS), 10, "10 jugendfreie Gags")
ok(all(n in g.PARTY_GAGS for n in g.FUN_GAGS) and all(n in g.PARTY_GAGS for n in g.FEIER_EXTRA),
   "Neue Gags auch im Feierabend-Topf")
r._vis_states = {}
st = run(10.0)
eq(st["fun"]["cur"], None, "Erst 18 s tanzen")
t0 = time.perf_counter()
st = run(10.0)
ok(st["fun"]["cur"] is not None, "Dann kommt ein Gag: " + str(st["fun"]["cur"] and st["fun"]["cur"]["name"]))
seen = set()
for name in g.FUN_GAGS:                                             # jeder Gag läuft durch und endet
    fs = st["fun"]
    r._xmas_fun_start(fs, name)
    fs["next"] = 1e9
    st = run(g.FUN_GAGS[name] + 0.2)
    ok(st["fun"]["cur"] is None, f"Gag „{name}“ läuft durch und endet")
    seen.add(name)
ms = (time.perf_counter() - t0) / ((10 + sum(g.FUN_GAGS.values()) + 2) * FPS) * 1000
ok(ms < 12, f"Zeichenzeit je Bild {ms:.2f} ms")
fs = st["fun"]
r._xmas_fun_start(fs, "plaetzchen")
st = run(1.0, talk=True, talk_t=5000 + T[0])
eq(st["fun"]["cur"], None, "Wortbeitrag bricht den Gag ab (Bank wie gewohnt)")
r._vis_states = {}
run(25.0, o=opts(gags=False))
ok("fun" not in r._vis_states["xmas"], "Option aus: keine Gags")
O = opts(gags=True)
r._vis_states = {}
s = g.demo_snapshot(100.0)
g.VISUAL_RENDERERS["xmas"](r, s, O, (0, 255, 90))
ok("fun" not in r._vis_states["xmas"], "Vorschau (demo): keine Gags")
P = r._xmas_fun_plan("schornstein", 1.0, 12, g.demo_snapshot(1.0), 1.0)
ok(P["family"] and not P["meter"] and not P["pot"], "Ohne Feierabend: kein Glühwein, kein Barometer")

# Feierabend: die vier neuen Gags laufen durch
O = opts(party="on", party_len="600")
g.party_clock = lambda: type("C", (), {"tm_mon": 11, "tm_mday": 19, "tm_hour": 21, "tm_min": 0, "tm_wday": 3})()
r._vis_states = {}
st = run(2.0)
for name in g.FEIER_EXTRA:
    ps = st["party"]
    ps.update(phase="mid", next=1e9, micro_at=1e9, pegel=0.6)
    r._xmas_party_start(ps, name)
    st = run(g.FEIER_EXTRA[name]["dur"] + 0.3)
    ok(st["party"]["cur"] is None or st["party"]["cur"]["name"] != name, f"Feierabend-Gag „{name}“ endet")

# Sprechblasen: Umbruch bei langen Sätzen
from PIL import Image, ImageDraw
d = ImageDraw.Draw(Image.new("RGB", (320, 240)))
font = g.load_font(g.SAY_FONT, bold=True)
lines = g._wrap_text(d, "Nebenkosten! Nachzahlung: 3 Seelen und noch mehr Text", font, g.SAY_MAX_W)
ok(len(lines) >= 2 and all(d.textlength(x, font=font) <= g.SAY_MAX_W for x in lines), f"Umbruch: {lines}")
eq(g._wrap_text(d, "Hoppla!", font, g.SAY_MAX_W), ["Hoppla!"], "Kurz: eine Zeile")
done()
