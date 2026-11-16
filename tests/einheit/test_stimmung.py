"""Stimmungs-Stile: Seidenschleier, Abendglut, Herzschlag-Aura."""
import time
from common import g, eq, ok, done

r = g.Renderer()
r.settings = g.load_settings("/nonexistent")
FPS = 15
T = [0.0]


def run(style, o, seconds, **kw):
    img = None
    for _ in range(int(round(seconds * FPS))):
        t = 5000 + T[0]
        s = g.demo_snapshot(t, amp=1.0)
        s.update(active=True, demo=False, t=t)
        s.update(kw)
        img = g.VISUAL_RENDERERS[style](r, s, o, (0, 110, 255))
        T[0] += 1 / FPS
    return img


for style in ("silk", "ember", "pulse"):
    ok(style in g.VISUAL_STYLES and style in g.VISUAL_OPTIONS, f"{style}: in Stilliste und Optionen")
    for choice in ([c[0] for c in next(x for x in g.VISUAL_OPTIONS[style] if x["key"] == "colors")["choices"]]):
        o = dict(g.visual_options(r.settings, style), colors=choice)
        r._vis_states = {}
        t0 = time.perf_counter()
        img = run(style, o, 4.0)
        ms = (time.perf_counter() - t0) / (4 * FPS) * 1000
        ok(ms < 10, f"{style}/{choice}: Zeichenzeit je Bild {ms:.2f} ms")
        eq(img.size, (g.WIDTH, g.HEIGHT), f"{style}/{choice}: Bildgröße")
        col = getattr(r, "vis_col_" + style)
        ok(isinstance(col, tuple) and len(col) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in col),
           f"{style}/{choice}: Tastaturfarbe gültig {col}")
    # Bass hebt die Tastaturfarbe, Stille bzw. Wortbeitrag beruhigt sie
    o = g.visual_options(r.settings, style)
    r._vis_states = {}
    run(style, o, 3.0, bass=1.0)
    loud = sum(getattr(r, "vis_col_" + style))
    run(style, o, 4.0, talk=True, talk_t=5000 + T[0])
    calm = sum(getattr(r, "vis_col_" + style))
    ok(calm < loud, f"{style}: Wortbeitrag beruhigt die Tastatur ({loud} → {calm})")
    # ungültige Messwerte stören nicht dauerhaft
    run(style, o, 0.3, bass=float("nan"), level=float("nan"))
    run(style, o, 0.3)
    ok(r._vis_states[style]["bass"] == r._vis_states[style]["bass"], f"{style}: Bass nach NaN-Werten gültig")

# Herzschlag-Aura: jeder Schlag schickt einen Ring los, abschaltbar
o = g.visual_options(r.settings, "pulse")
r._vis_states = {}
run("pulse", o, 3.0)
ok(len(r._vis_states["pulse"]["rings"]) > 0, "Herzschlag-Aura: Schlag-Ringe bei Musik")
r._vis_states = {}
run("pulse", dict(o, beat=False), 3.0)
eq(r._vis_states["pulse"]["rings"], [], "Herzschlag-Aura: ohne Schlag-Ringe, wenn abgeschaltet")
done()
