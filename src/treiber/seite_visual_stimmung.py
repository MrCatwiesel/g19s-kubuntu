"""Visualisierungen der Gruppe „Stimmung“ (Mixin MoodVisual): ruhige, abstrakte Lichtbilder ohne Gags.
silk  „Seidenschleier“  – halbtransparente Lichtbänder in Rubin, Bordeaux und Gold wogen ineinander, der Bass hebt
                          sie langsam an.
ember „Abendglut“       – Glut am unteren Rand atmet mit dem Bass, warme Funken steigen auf und verglimmen.
pulse „Herzschlag-Aura“ – weiche Lichtringe laufen vom Zentrum nach außen, jeder Schlag schickt einen hellen Ring los.
Alle drei folgen dem Bass bewusst träge (sanft statt zappelig) und kommen bei einem Wortbeitrag zur Ruhe.
Gezeichnet wird doppelt aufgelöst und danach verkleinert (weiche Kanten).
"""
import math

MOOD_SS = 2                                     # Überabtastung für weiche Kanten
SILK_PALETTES = {"ruby": [(140, 20, 50), (195, 45, 75), (235, 130, 90), (255, 195, 130)],
                 "night": [(30, 40, 120), (60, 70, 170), (120, 110, 210), (200, 180, 250)]}
EMBER_SPARKS = {"few": 16, "normal": 28, "many": 44}
PULSE_RINGS, PULSE_REACH = 7, 190               # Ringe gleichzeitig, Weg bis zum Verblassen (Pixel)


def _mood_layer_palette(color, n):
    """n Abstufungen der Ebenenfarbe von dunkel nach hell (für „Farbe der Ebene“)."""
    return [tuple(int(min(255, c * (0.35 + 0.55 * k / max(1, n - 1)) + 40 * k / max(1, n - 1))) for c in color)
            for k in range(n)]


class MoodVisual:
    vis_col_silk = None
    vis_col_ember = None
    vis_col_pulse = None

    def _mood_state(self, style, s):
        """Gemeinsamer Zustand: Bass träge nachgeführt, bei Stille/Wortbeitrag gegen 0."""
        st = self._vstate(style, lambda: {"bass": 0.0, "level": 0.0, "beats": s["beats"], "rings": []})
        dt = self._vis_dt(st, s["t"])
        playing = (s.get("active") or s.get("demo")) and not s.get("talk")
        bass = float(s.get("bass") or 0.0) if playing else 0.0
        level = float(s.get("level") or 0.0) if playing else 0.0
        if not math.isfinite(bass):
            bass = 0.0
        if not math.isfinite(level):
            level = 0.0
        st["bass"] += (bass - st["bass"]) * min(1.0, dt / (0.25 if bass > st["bass"] else 0.9))
        st["level"] += (level - st["level"]) * min(1.0, dt / 0.8)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        return st, dt, playing, new_beat and playing

    # -- Seidenschleier ----------------------------------------------------- #
    @vis_style("silk")
    def vis_silk(self, s, o, color):
        t = s["t"]
        st, dt, playing, beat = self._mood_state("silk", s)
        bass = st["bass"]
        S = MOOD_SS
        img = Image.new("RGB", (WIDTH * S, VIS_H * S), (14, 4, 10))
        d = ImageDraw.Draw(img, "RGBA")
        pal = _mood_layer_palette(color, 4) if o.get("colors") == "layer" else \
            SILK_PALETTES.get(o.get("colors"), SILK_PALETTES["ruby"])
        alpha = 150 if o.get("veil", True) else 255
        for layer, col in enumerate(pal):
            amp = (14 + layer * 6 + bass * 22) * S
            freq = (0.012 + layer * 0.003) / S
            phase = t * (0.45 + layer * 0.12)
            base_y = VIS_H * S * (0.30 + layer * 0.16) - bass * 10 * S
            pts = [(x, base_y + math.sin(x * freq + phase) * amp + math.cos(x * 0.007 / S - phase * 0.6) * 10 * S)
                   for x in range(0, WIDTH * S + 8 * S, 8 * S)]
            d.polygon(pts + [(WIDTH * S, VIS_H * S), (0, VIS_H * S)], fill=(*col, alpha))
            glow = tuple(min(255, c + 50) for c in col)                         # Glanzkante oben am Band
            d.line(pts, fill=(*glow, int(90 + 120 * bass)), width=S)
        out = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        out.paste(img.reduce(S), (0, 0))
        self.vis_col_silk = tuple(int(c * (0.35 + 0.65 * min(1.0, bass * 1.2))) for c in pal[1])
        return out

    # -- Abendglut ---------------------------------------------------------- #
    @vis_style("ember")
    def vis_ember(self, s, o, color):
        t = s["t"]
        st, dt, playing, beat = self._mood_state("ember", s)
        bass = st["bass"]
        S = MOOD_SS
        W, H = WIDTH * S, VIS_H * S
        img = Image.new("RGB", (W, H), (12, 5, 3))
        d = ImageDraw.Draw(img, "RGBA")
        warm = o.get("colors") != "layer"
        base = (255, 110, 30) if warm else color
        for i in range(6):                                                      # Glut-Horizont, außen dunkler
            r = (150 + i * 26 + bass * 40) * S
            tone = max(0.1, 0.95 - i * 0.15) * (0.55 + 0.45 * min(1.0, bass * 1.3 + 0.2))
            col = tuple(int(c * tone * (0.75 if warm and k == 1 else 1.0)) for k, c in enumerate(base))
            y0 = H - (26 + i * 11) * S - bass * 10 * S
            d.ellipse((W / 2 - r, y0, W / 2 + r, H + 90 * S), fill=(*col, 70))
        n = EMBER_SPARKS.get(o.get("sparks"), EMBER_SPARKS["normal"])
        for i in range(n):                                                      # aufsteigende Funken
            speed = (14 + (i % 7) * 4) * (1 + bass * 0.6)
            y = VIS_H - ((t * speed + i * 37) % (VIS_H + 20))
            x = ((i * 53) % WIDTH) + math.sin(t * 1.1 + i) * 12
            size = (1.3 + (i % 3) * 0.7) * S
            fade = max(0.0, min(1.0, y / VIS_H)) ** 0.7                         # oben verglimmen sie
            col = (255, int(120 + 90 * fade), int(40 + 60 * fade)) if warm else \
                tuple(min(255, int(c * 0.7 + 90 * fade)) for c in color)
            X, Y = x * S, y * S
            d.ellipse((X - size * 3, Y - size * 3, X + size * 3, Y + size * 3), fill=(*col, int(35 * fade)))
            d.ellipse((X - size, Y - size, X + size, Y + size), fill=(*col, int(255 * fade)))
        out = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        out.paste(img.reduce(S), (0, 0))
        k = 0.3 + 0.7 * min(1.0, bass * 1.3)
        self.vis_col_ember = tuple(int(c * k) for c in ((255, 90, 20) if warm else color))
        return out

    # -- Herzschlag-Aura ---------------------------------------------------- #
    @vis_style("pulse")
    def vis_pulse(self, s, o, color):
        t = s["t"]
        st, dt, playing, beat = self._mood_state("pulse", s)
        bass = st["bass"]
        S = MOOD_SS
        W, H = WIDTH * S, VIS_H * S
        img = Image.new("RGB", (W, H), (16, 6, 14))
        d = ImageDraw.Draw(img, "RGBA")
        warm = o.get("colors") != "layer"
        base = (220, 55, 95) if warm else color
        cx, cy = W / 2, H / 2
        if beat and o.get("beat", True):                                       # jeder Schlag: ein heller Ring
            st["rings"].append(t)
        st["rings"] = [b for b in st["rings"] if t - b < 2.0][-6:]
        d.ellipse((cx - (30 + bass * 26) * S, cy - (22 + bass * 20) * S, cx + (30 + bass * 26) * S,
                   cy + (22 + bass * 20) * S), fill=(*base, int(40 + 90 * bass)))   # warmer Kern
        for ring in range(PULSE_RINGS, 0, -1):                                  # gleichmäßig wandernde Ringe
            radius = ((t * 22 + ring * PULSE_REACH / PULSE_RINGS) % PULSE_REACH) + bass * 18
            k = max(0.0, 1.0 - radius / PULSE_REACH)
            r = radius * S
            d.ellipse((cx - r, cy - r * 0.75, cx + r, cy + r * 0.75), outline=(*base, int(230 * k)), width=3 * S)
        for b in st["rings"]:                                                   # Schlag-Ringe, schneller und heller
            age = t - b
            r = (20 + age * 110) * S
            k = max(0.0, 1.0 - age / 2.0)
            hi = tuple(min(255, int(c * 0.6 + 120)) for c in base)
            d.ellipse((cx - r, cy - r * 0.75, cx + r, cy + r * 0.75), outline=(*hi, int(200 * k)), width=2 * S)
        out = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        out.paste(img.reduce(S), (0, 0))
        k = 0.25 + 0.75 * min(1.0, bass * 1.2 + (0.3 if st["rings"] and t - st["rings"][-1] < 0.25 else 0.0))
        self.vis_col_pulse = tuple(int(c * min(1.0, k)) for c in base)
        return out
