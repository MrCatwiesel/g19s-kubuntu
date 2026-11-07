"""Bühnenlicht-Effekte für die Visualisierung: Verfolgerspot, Moving Heads, Laser, Nebel (Haze), Lauflicht,
Silhouette im Gegenlicht, UV-Schwarzlicht, Farben nach Stimmung, Lichtpunkte der Spiegelkugel, Blinder.
Die Tänzerin wählt sie über Lichtprogramme (Option show) oder einzeln (show = custom, Optionen fx_*), die Lichtshow
über die Option fx. Stimmung, Höhepunkte und die aktuelle Bühnenfarbe liegen in st["fx"]; die Bühnenfarbe
(vis_stage_color) kann die Tastaturbeleuchtung übernehmen.
"""

FX_ALL = ("beams", "follow", "heads", "laser", "haze", "chase", "silhouette", "uv", "mood", "ball", "blinder")
FX_PROGRAMS = {                         # Lichtprogramme der Tänzerin (beams/club wie bisher, dazu neue)
    "off": (), "beams": (), "club": (),
    "ballet": ("follow", "mood", "haze", "silhouette"),
    "night": ("heads", "laser", "haze", "uv", "chase", "ball"),
    "gala": ("follow", "heads", "laser", "haze", "chase", "mood", "ball", "blinder"),
}
FX_LIGHTS = {                           # Zusätze für den Stil „Lichtshow“ (Option fx)
    "classic": (), "heads": ("heads", "haze"), "laser": ("laser", "haze", "chase"),
    "show": ("heads", "laser", "haze", "chase", "blinder", "mood"),
}
FX_HEADS_X = (34, 104, 216, 286)        # Moving Heads an der Decke
FX_LASER = (WIDTH - 24, 8)              # Laser oben rechts


def fx_set(o):
    """Aktive Effekte der Tänzerin aus Programm bzw. eigener Auswahl."""
    prog = o.get("show", "off")
    if prog == "custom":
        return {k for k in FX_ALL if o.get("fx_" + k)}
    return set(FX_PROGRAMS.get(prog, ()))


class StageFx:
    vis_stage_color = None             # Farbe des Bühnenlichts (für die Tastatur), None = keine
    vis_listen = False                 # Tänzerin hört gerade zu (Tastatur atmet)

    # -- Zustand: Stimmung, Höhepunkt ---------------------------------------- #
    def _fx_update(self, st, s, t, dt, fx):
        """Stimmung (0 ruhig … 1 wild, aus Pegel und Tempo), Höhepunkt (Blinder, Laser weit), Silhouette."""
        f = st.setdefault("fx", {"slow": s["level"], "fast": s["level"], "boom": -99.0, "sil": 0.0})
        f["slow"] += (s["level"] - f["slow"]) * min(1.0, dt / 6)
        f["fast"] += (s["level"] - f["fast"]) * min(1.0, dt / 0.4)
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        k = max(0.0, min(1.0, (f["slow"] - 0.3) / 0.45)) * 0.7 + max(0.0, min(1.0, (0.75 - period) / 0.35)) * 0.3
        f["mood"] = k
        if f["fast"] > f["slow"] * 1.2 + 0.04 and t - f["boom"] > 8:
            f["boom"] = t                                       # Höhepunkt
        f["surge"] = max(0.0, 1 - (t - f["boom"]) / 2.5) if t >= f["boom"] else 0.0
        calm = f["fast"] < 0.32 or k < 0.22
        f["sil"] += ((1.0 if calm and "silhouette" in fx else 0.0) - f["sil"]) * min(1.0, dt * 1.5)
        if "mood" in fx:                                        # blau/violett (ruhig) … magenta … rot (wild)
            f["hue"] = (0.66 + 0.34 * k + 0.03 * math.sin(s["beats"] * 1.7)) % 1.0
        else:
            f["hue"] = (s["beats"] * 0.13) % 1.0
        f["color"] = _hue(f["hue"], 0.85, 1.0)
        return f

    # -- hinter der Figur ----------------------------------------------------- #
    def _fx_back(self, img, s, st, fx, t, focus, floor_y, chase_y):
        """Effekte, die hinter der Figur liegen: UV/abgedunkelt, Gegenlicht, Lichtkegel (Moving Heads, Laser) im
        Nebel, Lauflicht, Verfolgerspot. img = ganzes Bild; gibt das neue Bild zurück."""
        f = st["fx"]
        if "uv" in fx:                                          # Schwarzlicht: dunkles Blauviolett
            img = Image.blend(img, Image.new("RGB", img.size, (10, 4, 40)), 0.72)
        elif {"heads", "laser"} & fx:                           # Club: Raum dunkler, damit Licht wirkt
            img = Image.blend(img, Image.new("RGB", img.size, (4, 3, 10)), 0.5)
        if f["sil"] > 0.01:                                     # Gegenlicht: farbiger Hintergrund
            back = self.__dict__.get("_fx_back_grad")
            if back is None:
                ys = np.linspace(1.0, 0.25, HEIGHT)[:, None, None]
                back = self._fx_back_grad = np.broadcast_to(ys, (HEIGHT, WIDTH, 1)).astype(np.float32)
            col = np.array(_hue(f["hue"], 0.75, 1.0), np.float32)
            flood = Image.fromarray(np.clip(back * col, 0, 255).astype(np.uint8), "RGB")
            img = Image.blend(img, flood, 0.7 * f["sil"])
        layer = Image.new("RGB", (WIDTH, VIS_H), (0, 0, 0))
        if "heads" in fx:
            layer = self._fx_heads(layer, s, f, t, focus)
        if "laser" in fx:
            self._fx_laser(layer, s, f, t)
        if "haze" in fx:                                        # Nebel: Strahlen werden fleckig sichtbar
            haze = self._fx_haze(t)
            layer = ImageChops.multiply(layer, haze)
            glow = ImageChops.multiply(haze, Image.new("RGB", haze.size, tuple(int(c * 0.09) for c in f["color"])))
            layer = ImageChops.add(layer, glow)
        if layer.getbbox():
            img.paste(ImageChops.add(img.crop((0, 0, WIDTH, VIS_H)), layer), (0, 0))
        if "chase" in fx:
            self._fx_chase(img, s, f, t, chase_y)
        if "follow" in fx:
            img = self._fx_follow(img, f, focus, floor_y)
        if "heads" in fx or "laser" in fx:
            d = ImageDraw.Draw(img)                             # Scheinwerfer-Gehäuse an der Decke
            for x in FX_HEADS_X if "heads" in fx else ():
                d.rounded_rectangle([x - 5, 0, x + 5, 7], radius=2, fill=(30, 30, 36), outline=(80, 80, 92))
            if "laser" in fx:
                d.rectangle([FX_LASER[0] - 6, 0, FX_LASER[0] + 6, FX_LASER[1]], fill=(28, 28, 34), outline=(80, 80, 92))
        self.vis_stage_color = f["color"] if fx else None
        return img

    def _fx_heads(self, layer, s, f, t, focus):
        """Vier Moving Heads fahren Figuren (Fächer, Kreuz, Kreis, auf die Tänzerin), Farbe wechselt im Takt."""
        fall = self.__dict__.get("_lights_fall")
        if fall is None:
            fall = self._lights_fall = Image.fromarray(
                np.broadcast_to(np.linspace(255, 89, VIS_H)[:, None], (VIS_H, WIDTH)).astype(np.uint8), "L")
        pat = (s["beats"] // 8) % 4
        beat = math.exp(-max(0.0, t - s.get("beat_t", -9)) * 6)
        bright = 0.45 + 0.35 * s["bass"] + 0.2 * beat + 0.3 * f["surge"]
        col = f["color"]
        for i, x in enumerate(FX_HEADS_X):
            if pat == 0:                                        # Fächer
                ang = (i - 1.5) * (14 + 10 * math.sin(t * 1.1))
            elif pat == 1:                                      # Kreuz
                ang = (1 if i % 2 else -1) * 28 * math.sin(t * 1.5)
            elif pat == 2:                                      # Kreis
                ang = 30 * math.sin(t * 2 + i * math.pi / 2)
            else:                                               # alle auf die Tänzerin
                ang = math.degrees(math.atan2(focus[0] - x, max(20, focus[1] - 6))) + math.sin(t * 3 + i) * 3
            dx1, dy1 = _vec(ang - 3.5, 280)
            dx2, dy2 = _vec(ang + 3.5, 280)
            mask = Image.new("L", (WIDTH, VIS_H), 0)
            ImageDraw.Draw(mask).polygon([(x - 2, 6), (x + 2, 6), (x + dx2, 6 + dy2), (x + dx1, 6 + dy1)],
                                         fill=int(min(255, 150 * bright)))
            mask = ImageChops.multiply(mask, fall)
            layer = ImageChops.add(layer, ImageChops.multiply(Image.new("RGB", layer.size, col), mask.convert("RGB")))
        return layer

    def _fx_laser(self, layer, s, f, t):
        """Laserfächer von oben rechts; spreizt bei Höhepunkten weit auf. Grün, alle 8 Schläge rot."""
        d = ImageDraw.Draw(layer)
        col = (60, 255, 90) if (s["beats"] // 8) % 2 == 0 else (255, 50, 60)
        n = 10
        spread = 40 + 60 * f["surge"]
        base = -38 + math.sin(t * 0.9) * 18                     # Grad wie _vec (0 = nach unten, −90 = nach links)
        x0, y0 = FX_LASER
        for i in range(n):
            ang = base + (i / (n - 1) - 0.5) * spread
            dx, dy = _vec(ang, 420)
            d.line([(x0, y0), (x0 + dx, y0 + dy)], fill=col, width=1)
        for i in range(0, n, 2):                                # Punkte, wo die Strahlen den Boden treffen
            ang = base + (i / (n - 1) - 0.5) * spread
            dx, dy = _vec(ang, 1)
            k = (VIS_H - 2 - y0) / max(0.05, abs(dy))
            px = x0 + dx * k
            if 0 <= px < WIDTH:
                d.ellipse([px - 1.5, VIS_H - 4, px + 1.5, VIS_H - 1], fill=col)

    def _fx_haze(self, t):
        """Nebelschwaden: weiches Rauschen, das langsam zieht (RGB, 90…255)."""
        tex = self.__dict__.get("_fx_haze_tex")
        if tex is None:
            rng = np.random.default_rng(7)
            small = Image.fromarray((rng.random((9, 16)) * 255).astype(np.uint8), "L")
            big = small.resize((WIDTH * 2, VIS_H), Image.BICUBIC).point(lambda v: int(90 + v * 0.65))
            tex = self._fx_haze_tex = big
        off = int(t * 7) % WIDTH
        return tex.crop((off, 0, off + WIDTH, VIS_H)).convert("RGB")

    def _fx_chase(self, img, s, f, t, y):
        """Lauflicht an der Bodenkante: läuft im Takt, beim Höhepunkt doppelt so schnell."""
        speed = (2 / max(0.3, s.get("period") or 0.5)) * (2 if f["surge"] > 0 else 1)
        head = int(t * speed * 2)
        for i in range(27):
            x = 6 + i * 12
            age = (head - i) % 9
            col = _hue(f["hue"] + i * 0.01, 0.8, 1.0)
            if age < 3:
                k = 1.0 - age * 0.35
                self._blob(img, x, y, 10, 6, col, alpha=round(0.6 * k, 1), flat=True)
                ImageDraw.Draw(img).ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=tuple(int(c * k) for c in col))
            else:
                ImageDraw.Draw(img).point((x, y), fill=(60, 60, 70))

    def _fx_follow(self, img, f, focus, floor_y):
        """Verfolgerspot: hartes, rundes Licht auf der Tänzerin, die Bühne drumherum dunkel."""
        spr = self.__dict__.get("_fx_spot")
        if spr is None:
            w, h = 120, 230
            ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
            r = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2)
            spr = self._fx_spot = Image.fromarray((np.clip((1.05 - r) * 6, 0, 1) * 255).astype(np.uint8), "L")
        mask = Image.new("L", img.size, 0)
        mask.paste(spr, (int(focus[0] - spr.width / 2), int(focus[1] - spr.height / 2 + 6)))
        dark = img.point(lambda v: v * 0.32)
        lit = Image.blend(img, Image.new("RGB", img.size, (255, 236, 205)), 0.12)
        img = Image.composite(lit, dark, mask)
        self._blob(img, focus[0], floor_y + 3, 92, 16, (255, 230, 190), alpha=0.35, flat=True)   # Lichtkreis am Boden
        return img

    # -- vor der Figur -------------------------------------------------------- #
    def _fx_figure(self, fig, st):
        """Silhouette: Figur im Gegenlicht fast schwarz (nur RGB, Deckkraft bleibt)."""
        sil = st["fx"]["sil"]
        if sil < 0.01:
            return fig
        r, g_, b, a = fig.split()
        k = 1 - 0.88 * sil
        return Image.merge("RGBA", (r.point(lambda v: v * k), g_.point(lambda v: v * k), b.point(lambda v: v * k), a))

    def _fx_front(self, img, s, st, fx, t, focus, hem=None, ball=None):
        """Effekte vor der Figur: Lichtpunkte der Spiegelkugel (auch auf ihr), UV-Leuchten von Saum und Gürtel,
        Spiegelkugel, Blinder beim Höhepunkt."""
        f = st["fx"]
        d = ImageDraw.Draw(img)
        if "uv" in fx and hem:                                  # Neon im Schwarzlicht
            d.line(hem, fill=(90, 255, 250), width=2)
            wx, wy = focus[0], focus[1] - 12
            for k in range(-6, 7):
                d.point((wx + k * 2, wy + (k % 2)), fill=(255, 90, 240))
        if "ball" in fx:
            bx, by = ball or (WIDTH // 2, 12)
            for i in range(28):                                 # wandernde Lichtpunkte
                a = i * 2.39996 + t * 0.55
                rr = 30 + (i * 37) % 150
                x = bx + math.cos(a) * rr * 1.4
                y = by + 30 + abs(math.sin(a * 0.7 + i)) * (VIS_H - 40)
                if 0 <= x < WIDTH and y < VIS_H:
                    c = _hue(f["hue"] + i * 0.03, 0.25, 1.0)
                    self._blob(img, x, y, 7, 5, c, alpha=0.7, flat=True)
                    d.point((x, y), fill=(255, 255, 255))
            self._lights_ball(d, t, bx, by, 10)
        if "blinder" in fx and f["surge"] > 0:                  # warmer Lichtstoß (kein Stroboskop)
            k = f["surge"] ** 2
            for x in (14, WIDTH - 14):
                self._blob(img, x, 10, 60, 40, (255, 220, 160), alpha=round(0.9 * k, 2), flat=True)
                d.ellipse([x - 6, 4, x + 6, 16], fill=(255, 240, 200))
            img = Image.blend(img, Image.new("RGB", img.size, (255, 226, 180)), 0.35 * k)
        return img
