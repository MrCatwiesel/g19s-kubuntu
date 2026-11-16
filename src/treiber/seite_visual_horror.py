"""Visualisierung „Horror“ (horror, Mixin HorrorVisual) mit zwei Schauplätzen, die bei jedem Liedwechsel wechseln:

Das Haus am Ende der Straße: Die Fenster leuchten je Frequenzband, dahinter tanzen Schatten, die Straßenlaterne
flackert auf hohe Schläge. Höhepunkt: Das Haus erwacht (Fenster werden Augen, die Tür ein Mund, das Dach hebt sich
wie ein Hut). Wortbeitrag: Ein Rabe auf dem Zaun verkündet. Gags: Der Nachbar will mit dem Hund vorbei (der Hund
weigert sich), der Pizzabote liefert an eine sehr lange Hand, und mit Gänsehaut: In allen Fenstern blinzeln Augen.

Das Puppenzimmer: Porzellanpuppen im Regal nicken im Takt, das Schaukelpferd schaukelt, auf der Spieluhr dreht sich
eine Tänzerin. Höhepunkt: Das Schaukelpferd galoppiert, die Puppen headbangen. Wortbeitrag: Eine Puppe zieht an ihrer
Schnur („Ma-ma!“). Gags: Teeparty mit dem Teddy, Springteufel mit Drehwurm, und mit Gänsehaut: Alle Puppen drehen
sich gleichzeitig zum Betrachter – oder das Licht geht aus, und danach sitzen sie plötzlich ganz vorn.
"""
import math
import random

HR_FLOOR = VIS_H - 36                   # Haus: Fuß des Hauses / Puppenzimmer: Boden
HR_WIN = [(124, 100), (160, 100), (196, 100), (124, 138), (196, 138)]   # Fenster des Hauses (Mitte)
HR_ATTIC = (160, 70)
HR_DOOR = 160
HR_SHELF_Y = 86                         # Puppenregal (Oberkante, Puppen sitzen darauf)
HR_DOLLS = [(108, (120, 70, 40), (170, 60, 80)), (148, (230, 200, 120), (90, 120, 190)),
            (188, (40, 30, 30), (120, 160, 110)), (228, (200, 110, 50), (200, 170, 200))]   # (x, Haar, Kleid)
HR_GAGS = {"house": {"hund": 8.0, "pizza": 9.0, "augen": 8.0},
           "dolls": {"teeparty": 8.0, "kasten": 7.0, "drehen": 7.0, "licht": 9.0}}
HR_SPOOKY = {"augen", "drehen", "licht"}
HR_GAG_FIRST, HR_GAG_PAUSE = 10.0, (12.0, 20.0)
HR_BOOM = 4.0
HR_SWITCH = 240.0                       # ohne Liedwechsel spätestens alle 4 Minuten Schauplatz wechseln


def _hr_rot(p, c, a):
    s, co = math.sin(a), math.cos(a)
    return (c[0] + (p[0] - c[0]) * co - (p[1] - c[1]) * s, c[1] + (p[0] - c[0]) * s + (p[1] - c[1]) * co)


class HorrorVisual:
    vis_horror = None                   # Farbe für die Tastatur

    # -- Hintergründe ------------------------------------------------------------------------ #
    def _hr_street(self):
        if "_hr_bg_house" in self.__dict__:
            return self._hr_bg_house
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([8, 14, 26], np.float32), np.array([40, 50, 60], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(7)
        for _ in range(30):
            d.point((rng.uniform(0, WIDTH), rng.uniform(0, 80)), fill=(170, 180, 200))
        self._blob(img, 282, 30, 22, 22, (230, 230, 200), gloss=0.1)                # Mondsichel
        self._blob(img, 288, 26, 20, 20, (14, 20, 32), gloss=0.0, flat=True)
        d.rectangle([0, HR_FLOOR - 4, WIDTH, HEIGHT], fill=(26, 30, 30))
        d.polygon([(118, HR_FLOOR), (202, HR_FLOOR), (WIDTH + 40, HEIGHT), (-40, HEIGHT)], fill=(52, 54, 60))
        for k in range(5):                                                          # Mittelstreifen
            y0 = HR_FLOOR + 4 + k * k * 2.2 + k * 3
            d.line([(160, y0), (160, y0 + 2 + k)], fill=(120, 120, 110), width=1 + k // 2)
        for x0, s in ((14, 1.0), (300, 0.8)):                                       # kahle Bäume
            tr = (18, 20, 24)
            d.line([(x0, HR_FLOOR), (x0, HR_FLOOR - 90 * s)], fill=tr, width=4)
            for a, ln in ((-0.6, 40), (0.5, 34), (-0.2, 28), (0.9, 22)):
                y1 = HR_FLOOR - 90 * s + 20 + a * 10
                d.line([(x0, y1), (x0 + math.sin(a) * ln * s, y1 - math.cos(a) * ln * s)], fill=tr, width=2)
        for x0, x1 in ((0, 96), (226, WIDTH)):                                      # Zaun
            for x in range(x0 + 4, x1, 9):
                d.polygon([(x - 3, HR_FLOOR + 22), (x + 3, HR_FLOOR + 22), (x + 3, HR_FLOOR + 4), (x, HR_FLOOR),
                           (x - 3, HR_FLOOR + 4)], fill=(180, 176, 160))
            d.line([(x0, HR_FLOOR + 8), (x1, HR_FLOOR + 8)], fill=(150, 146, 130), width=2)
        d.rectangle([254, HR_FLOOR + 6, 257, HR_FLOOR + 30], fill=(60, 50, 40))       # Briefkasten
        d.rounded_rectangle([244, HR_FLOOR - 4, 268, HR_FLOOR + 8], radius=5, fill=(70, 80, 90))
        d.line([(50, HR_FLOOR + 22), (50, HR_FLOOR - 74)], fill=(30, 30, 36), width=3)  # Laterne
        d.line([(50, HR_FLOOR - 74), (62, HR_FLOOR - 78)], fill=(30, 30, 36), width=3)
        d.polygon([(58, HR_FLOOR - 78), (68, HR_FLOOR - 78), (66, HR_FLOOR - 70), (60, HR_FLOOR - 70)],
                  fill=(40, 40, 46))
        # Haus als Bausteine (Körper und Dach wackeln getrennt)
        body = Image.new("RGBA", (124, 100), (0, 0, 0, 0))
        bd = ImageDraw.Draw(body)
        bd.rectangle([6, 4, 118, 99], fill=(70, 60, 72))
        for y in range(8, 99, 6):
            bd.line([(6, y), (118, y)], fill=(58, 50, 60))
        bd.rectangle([0, 0, 124, 6], fill=(46, 40, 48))
        bd.line([(40, 30), (84, 10)], fill=(40, 34, 42))                             # Riss
        self._hr_body = body
        roof = Image.new("RGBA", (140, 54), (0, 0, 0, 0))
        rd = ImageDraw.Draw(roof)
        rd.polygon([(0, 53), (140, 53), (70, 0)], fill=(36, 30, 40))
        rd.rectangle([96, 6, 108, 34], fill=(50, 42, 46))                          # Schornstein
        rd.ellipse([60, 22, 80, 42], fill=(24, 20, 26))
        for k in range(6):
            rd.line([(70 - k * 12, 53 - k * 9 + 2), (70 + k * 12, 53 - k * 9 + 2)], fill=(28, 24, 30))
        self._hr_roof = roof
        self._hr_bg_house = img
        return img

    def _hr_room(self):
        if "_hr_bg_dolls" in self.__dict__:
            return self._hr_bg_dolls
        img = Image.new("RGB", (WIDTH, HEIGHT), (96, 70, 78))
        d = ImageDraw.Draw(img)
        for x in range(0, WIDTH, 16):                                              # verblasste Tapete
            d.rectangle([x, 0, x + 7, HR_FLOOR], fill=(104, 78, 86))
            for y in range(10, HR_FLOOR, 24):
                d.ellipse([x + 10, y, x + 14, y + 4], fill=(120, 92, 96))
        d.rectangle([0, HR_FLOOR, WIDTH, HEIGHT], fill=(78, 54, 40))                 # Dielen
        for y in range(HR_FLOOR + 6, HEIGHT, 8):
            d.line([(0, y), (WIDTH, y)], fill=(64, 44, 32))
        d.rectangle([0, HR_FLOOR - 6, WIDTH, HR_FLOOR], fill=(60, 40, 34))           # Fußleiste
        d.rectangle([258, 20, 312, 92], fill=(30, 40, 70))                         # Fenster mit Mond
        self._blob(img, 290, 42, 14, 14, (220, 225, 240), gloss=0.1)
        d.line([(285, 20), (285, 92)], fill=(70, 50, 44), width=3)
        d.line([(258, 56), (312, 56)], fill=(70, 50, 44), width=3)
        d.rectangle([256, 18, 314, 94], outline=(70, 50, 44), width=3)
        d.polygon([(250, 12), (266, 12), (262, 100), (246, 104)], fill=(130, 40, 60))   # Vorhang
        light = Image.new("L", (WIDTH, HEIGHT), 0)                                  # Mondlicht auf dem Boden
        ImageDraw.Draw(light).polygon([(258, 92), (312, 92), (240, HEIGHT), (130, HEIGHT)], fill=40)
        img.paste((200, 210, 240), (0, 0), light)
        d.rectangle([88, HR_SHELF_Y, 248, HR_SHELF_Y + 5], fill=(110, 76, 50))       # Regal
        for x in (96, 240):
            d.polygon([(x, HR_SHELF_Y + 5), (x + 3, HR_SHELF_Y + 5), (x + 3, HR_SHELF_Y + 18)], fill=(90, 60, 40))
        d.rectangle([236, HR_FLOOR - 26, 280, HR_FLOOR - 22], fill=(110, 76, 50))   # Tischchen (Spieluhr)
        for x in (240, 274):
            d.line([(x, HR_FLOOR - 22), (x, HR_FLOOR + 4)], fill=(90, 60, 40), width=3)
        for k in range(4):                                                          # Bauklötze
            x = 150 + k * 13
            c = [(200, 60, 60), (60, 120, 200), (220, 190, 60), (80, 160, 90)][k]
            d.rectangle([x, HR_FLOOR + 10 - (k == 2) * 10, x + 10, HR_FLOOR + 20 - (k == 2) * 10], fill=c)
            d.text((x + 2, HR_FLOOR + 9 - (k == 2) * 10), "ABCD"[k], font=self.f_tiny, fill=(250, 250, 240))
        shade = Image.new("L", (WIDTH, HEIGHT), 0)                                  # dunkle Ecken
        sd = ImageDraw.Draw(shade)
        for r in range(8):
            sd.rectangle([r * 6, r * 4, WIDTH - r * 6, HEIGHT - r * 4], outline=110 - r * 13, width=6)
        img.paste((10, 6, 10), (0, 0), shade)
        self._hr_bg_dolls = img
        return img

    # -- Figuren -------------------------------------------------------------------------- #
    def _hr_doll(self, img, d, x, y, hair, dress, tilt=0.0, look=-0.5, stare=0.0, glow=False, scale=1.0,
                 pull=False):
        """Porzellanpuppe, sitzend; y = Sitzfläche. look: Blickrichtung (-1 … 1), stare: Augen weit/schwarz."""
        s = scale
        self._blob(img, x, y - 9 * s, 18 * s, 18 * s, dress, gloss=0.4)
        d.polygon([(x - 11 * s, y), (x + 11 * s, y), (x + 7 * s, y - 10 * s), (x - 7 * s, y - 10 * s)], fill=dress)
        for side in (-1, 1):                                                        # Beine baumeln
            d.line([(x + side * 4 * s, y), (x + side * 5 * s, y + 9 * s)], fill=(240, 236, 232), width=int(3 * s))
            d.ellipse([x + side * 5 * s - 3 * s, y + 8 * s, x + side * 5 * s + 3 * s, y + 11 * s], fill=(30, 26, 30))
        hx, hy = x + math.sin(tilt) * 4 * s, y - 24 * s
        self._blob(img, hx, hy + 2 * s, 26 * s, 30 * s, hair, gloss=0.5, ang=tilt)      # Locken bis auf die Schultern
        self._blob(img, hx, hy + 1 * s, 16 * s, 17 * s, (244, 236, 230), gloss=0.6, ang=tilt)
        d.chord([hx - 8 * s, hy - 10 * s, hx + 8 * s, hy - 1 * s], 180, 360, fill=hair)       # Pony
        for side in (-1, 1):
            ex, ey = hx + side * 3.6 * s, hy
            r = (2.6 + stare * 0.8) * s
            d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(250, 250, 250) if not stare else (20, 10, 14))
            px = ex + look * 1.2 * s * (1 - stare)
            if glow:
                d.ellipse([ex - 1.6 * s, ey - 1.6 * s, ex + 1.6 * s, ey + 1.6 * s], fill=(255, 60, 40))
            elif not stare:
                d.ellipse([px - 1.4 * s, ey - 1.4 * s, px + 1.4 * s, ey + 1.4 * s], fill=(40, 70, 120))
            else:
                d.point((ex, ey), fill=(250, 250, 250))
            d.line([(ex - r, ey - r - 1), (ex - r - 1.5 * s, ey - r - 2.5 * s)], fill=(30, 20, 20))
            d.ellipse([hx + side * 5 * s - 2 * s, hy + 3 * s, hx + side * 5 * s + 2 * s, hy + 5 * s], fill=(240, 170, 170))
        d.ellipse([hx - 1.5 * s, hy + 5 * s, hx + 1.5 * s, hy + 7 * s], fill=(190, 50, 60))
        if pull:                                                                    # Schnur am Rücken
            d.line([(x + 8 * s, y - 14 * s), (x + 18 * s, y - 8 * s)], fill=(230, 230, 220))
            d.ellipse([x + 16 * s, y - 10 * s, x + 21 * s, y - 5 * s], outline=(230, 230, 220))

    def _hr_horse(self, img, d, x, y, ang):
        """Schaukelpferd; (x, y) = Mitte der Kufe am Boden, ang = Neigung."""
        c = (x, y - 8)
        R = lambda px, py: _hr_rot((x + px, y + py), c, ang)
        d.arc([x - 34, y - 30, x + 34, y + 4], 20, 160, fill=(120, 70, 40), width=4)
        for lx in (-18, -8, 8, 18):
            d.line([R(lx * 1.2, -4), R(lx, -26)], fill=(210, 200, 190), width=4)
        body = [R(-24, -34), R(20, -34), R(24, -24), R(-22, -22)]
        d.polygon(body, fill=(236, 230, 220))
        d.polygon([R(16, -34), R(28, -54), R(38, -50), R(26, -28)], fill=(236, 230, 220))   # Hals/Kopf
        d.polygon([R(30, -54), R(40, -48), R(36, -44)], fill=(236, 230, 220))
        for k in range(5):
            d.line([R(16 + k * 2.5, -36 - k * 4), R(12 + k * 2.5, -32 - k * 4)], fill=(150, 60, 50), width=3)
        d.line([R(-24, -30), R(-34, -20)], fill=(150, 60, 50), width=4)
        d.ellipse([R(31, -51)[0] - 1.5, R(31, -51)[1] - 1.5, R(31, -51)[0] + 1.5, R(31, -51)[1] + 1.5], fill=(20, 20, 20))
        d.polygon([R(-6, -36), R(8, -36), R(6, -30), R(-4, -30)], fill=(190, 40, 50))     # Sattel

    def _hr_musicbox(self, img, d, x, y, spin, level):
        d.rectangle([x - 14, y - 12, x + 14, y], fill=(140, 40, 60), outline=(90, 20, 40))
        d.polygon([(x - 14, y - 12), (x + 14, y - 12), (x + 18, y - 34), (x - 10, y - 34)], fill=(150, 50, 70))
        w = abs(math.cos(spin)) * 6 + 1
        d.line([(x, y - 12), (x, y - 26)], fill=(250, 240, 250), width=2)
        d.polygon([(x - w, y - 16), (x + w, y - 16), (x, y - 22)], fill=(250, 200, 220))
        d.line([(x - w * 1.2, y - 24), (x + w * 1.2, y - 24)], fill=(250, 240, 250), width=1)
        self._blob(img, x, y - 28, 4, 4, (250, 230, 220), gloss=0.2)

    def _hr_teddy(self, img, d, x, y, arm=0.0):
        fur = (150, 100, 60)
        self._blob(img, x, y - 10, 20, 20, fur, gloss=0.3)
        self._blob(img, x, y - 26, 16, 15, fur, gloss=0.3)
        for side in (-1, 1):
            self._blob(img, x + side * 7, y - 32, 6, 6, fur, gloss=0.2)
            d.point((x + side * 3, y - 27), fill=(10, 10, 10))
        d.ellipse([x - 3, y - 24, x + 3, y - 20], fill=(200, 160, 120))
        hand = (x + 12, y - 16 - arm * 10)
        self._limb(img, (x + 7, y - 14), hand, 6, fur)
        return hand

    # -- Ablauf ------------------------------------------------------------------------------ #
    @vis_style("horror")
    def vis_horror(self, s, o, color):
        t = s["t"]
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        want = o.get("place", "switch")
        st = self._vstate("horror", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                              "boom": -99.0, "gag": None, "order": [], "song": None,
                                              "next_gag": t + HR_GAG_FIRST, "rng": random.Random(23), "start": t,
                                              "place": "dolls" if want == "dolls" else "house", "since": t,
                                              "pose": 0, "flick": 1.0})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        playing = (s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        bang = math.sin(math.pi * min(1.0, (t - s.get("beat_t", t)) / (period * 0.6))) if playing else 0.0
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        # Schauplatz: fest oder Wechsel bei Liedwechsel (spätestens nach HR_SWITCH)
        song = getattr(self, "_vis_song", "")
        if want in ("house", "dolls"):
            st["place"] = want
        elif not demo and st["gag"] is None and ((st["song"] is not None and song and song != st["song"])
                                                 or t - st["since"] > HR_SWITCH):
            st["place"] = "dolls" if st["place"] == "house" else "house"
            st["since"], st["order"] = t, []
        st["song"] = song
        place = st["place"]
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < HR_BOOM
        gags = HR_GAGS[place]
        gag = st["gag"]
        if gag and (gag[0] not in gags or t - gag[1] >= gags[gag[0]]):
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*HR_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                pool = [g_ for g_ in gags if o.get("spooky", True) or g_ not in HR_SPOOKY]
                st["order"] = st["rng"].sample(pool, len(pool))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["pose"] = (st["pose"] + 1) % 4
        if s.get("hats") != st.get("hats"):
            st["hats"] = s.get("hats")
            if playing and st["rng"].random() < 0.4:
                st["flick"] = 0.15
        st["flick"] = min(1.0, st["flick"] + dt * 5)
        say = []
        args = (s, o, st, t, dt, playing, bang, level, boom, bt, talk, gname, gl, say)
        img = self._hr_house(*args) if place == "house" else self._hr_dolls(*args)
        d = ImageDraw.Draw(img)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        fade = t - st["since"]
        if fade < 0.6 and not demo and t - st["start"] > 1:                         # Überblendung beim Wechsel
            img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 1 - fade / 0.6)
        return img

    # -- Haus am Ende der Straße ---------------------------------------------------------------- #
    def _hr_house(self, s, o, st, t, dt, playing, bang, level, boom, bt, talk, gname, gl, say):
        img = self._hr_street().copy()
        d = ImageDraw.Draw(img)
        bands = s.get("bands")
        if bands is None or len(bands) == 0:
            bands = [level] * 8
        k = min(1.0, bt / 0.5, (HR_BOOM - bt) / 0.5) if boom else 0.0
        oy = -bang * 3 * (1 + 2 * k)
        lift = k * 16 + (bang * 5 if boom else 0)
        dark = gname == "augen" and 0.5 <= gl < 6.5
        lamp = 0.0 if dark else st["flick"]
        self._blob(img, 63, HR_FLOOR - 66, 70, 60, (255, 210, 120), alpha=round(0.3 * lamp, 2), flat=True)
        if lamp > 0.3:
            cone = Image.new("L", img.size, 0)
            ImageDraw.Draw(cone).polygon([(59, HR_FLOOR - 70), (67, HR_FLOOR - 70), (96, HR_FLOOR + 24),
                                          (30, HR_FLOOR + 24)], fill=int(46 * lamp))
            img.paste((255, 220, 140), (0, 0), cone)
        img.paste(self._hr_body, (98, int(HR_FLOOR - 98 + oy)), self._hr_body)
        img.paste(self._hr_roof, (90, int(HR_FLOOR - 146 + oy - lift)), self._hr_roof)
        d = ImageDraw.Draw(img)
        # Fenster: Licht je Frequenzband, dahinter tanzende Schatten
        wins = HR_WIN + [HR_ATTIC]
        for i, (wx, wy) in enumerate(wins):
            wy += oy - (lift if i == 5 else 0)
            b = bands[min(len(bands) - 1, i * len(bands) // len(wins))] if playing else 0.12
            on = 0.0 if dark else min(1.0, 0.15 + b * 1.4)
            if talk:
                on = 0.6 if i == 3 else 0.05
            col = (int(40 + 215 * on), int(30 + 170 * on), int(30 + 60 * on))
            if talk and i == 3:
                col = (90 + int(60 * abs(math.sin(t * 9))), 120, 200)                # Fernseher flimmert
            if i == 5:
                d.ellipse([wx - 9, wy - 9, wx + 9, wy + 9], fill=col)
            else:
                d.rectangle([wx - 9, wy - 11, wx + 9, wy + 11], fill=col, outline=(30, 24, 30))
            if boom and i in (0, 2):                                                # Haus erwacht: Augen
                self._blob(img, wx, wy, 16, 18, (250, 250, 240), gloss=0.3)
                px = wx + math.sin(t * 3) * 3
                d.ellipse([px - 4, wy - 3, px + 4, wy + 5], fill=(20, 10, 10))
                d.line([(wx - 10, wy - 14 - 4 * bang), (wx + 10, wy - 12 + (4 if i == 0 else -4))],
                       fill=(30, 24, 30), width=3)
                continue
            if on > 0.35 and i != 5 and not talk:                                   # Schatten tanzt
                p = (st["pose"] + i) % 4
                sx, sy = wx + (p % 2) * 3 - 1.5, wy + 11
                d.ellipse([sx - 3, sy - 17, sx + 3, sy - 11], fill=(20, 14, 18))
                d.rectangle([sx - 3, sy - 11, sx + 3, sy], fill=(20, 14, 18))
                for side in (-1, 1):
                    up = (p + (side > 0)) % 2
                    d.line([(sx + side * 3, sy - 9), (sx + side * 8, sy - (16 if up else 4))], fill=(20, 14, 18),
                           width=2)
            if not dark:
                d.line([(wx, wy - 11), (wx, wy + 11)], fill=(30, 24, 30))
                d.line([(wx - 9, wy), (wx + 9, wy)], fill=(30, 24, 30))
        if dark:                                                                    # Gänsehaut: Augen in allen Fenstern
            for i, (wx, wy) in enumerate(wins):
                wy += oy
                blink = math.sin(t * 2.3 + i * 1.7) > -0.85 and gl > 1.0 + i * 0.4
                if blink:
                    for side in (-1, 1):
                        d.ellipse([wx + side * 3 - 1.6, wy - 2, wx + side * 3 + 1.6, wy + 1], fill=(240, 230, 120))
        if gname == "augen" and 6.5 <= gl < 8:
            say.append((HR_WIN[1][0], HR_WIN[1][1] - 20, "Huhu!"))
        # Tür (beim Höhepunkt ein Mund)
        dy = HR_FLOOR + oy
        if boom:
            mo = 6 + level * 14 + bang * 6
            d.rectangle([HR_DOOR - 12, dy - 40, HR_DOOR + 12, dy], fill=(70, 60, 72))
            d.chord([HR_DOOR - 16, dy - 26 - mo / 2, HR_DOOR + 16, dy - 14 + mo], 0, 180, fill=(40, 6, 12))
            for k2 in range(4):
                d.rectangle([HR_DOOR - 12 + k2 * 7, dy - 20 + mo / 2 - 4, HR_DOOR - 8 + k2 * 7, dy - 20 + mo / 2],
                            fill=(240, 236, 220))
            if 0.6 < bt < 3.0:
                say.append((HR_DOOR, dy - 110 - lift, "HAUSPARTY!"))
        else:
            open_k = 0.0
            if gname == "pizza" and 3.0 <= gl < 6.4:
                open_k = min(1.0, (gl - 3.0) / 0.4, (6.4 - gl) / 0.3)
            d.rectangle([HR_DOOR - 11, dy - 38, HR_DOOR + 11, dy], fill=(10, 6, 8))
            if open_k < 1:
                w = 22 * (1 - open_k)
                d.rectangle([HR_DOOR - 11, dy - 38, HR_DOOR - 11 + w, dy], fill=(90, 50, 40), outline=(50, 30, 24))
                d.ellipse([HR_DOOR - 11 + w - 5, dy - 20, HR_DOOR - 11 + w - 2, dy - 17], fill=(200, 170, 80))
        d.rectangle([HR_DOOR - 20, dy, HR_DOOR + 20, dy + 4], fill=(60, 54, 60))     # Stufe
        # Rabe (Wortbeitrag)
        if talk:
            tl = t - s.get("talk_t", t)
            rx, ry = 250, HR_FLOOR - 6
            self._blob(img, rx, ry - 8, 16, 12, (14, 12, 18), gloss=0.5)
            self._blob(img, rx + 7, ry - 15, 9, 9, (14, 12, 18), gloss=0.5)
            d.polygon([(rx + 11, ry - 16), (rx + 18, ry - 14 - (2 if int(t * 6) % 2 else 0)), (rx + 11, ry - 13)],
                      fill=(70, 66, 60))
            d.point((rx + 8, ry - 17), fill=(250, 220, 80))
            d.polygon([(rx - 7, ry - 8), (rx - 16, ry - 2), (rx - 6, ry - 4)], fill=(14, 12, 18))
            if tl < 3.5:
                say.append((rx, ry - 26, "Krah! Durchsage!"))
        if gname == "hund":
            self._hr_gag_dog(img, d, gl, t, say)
        elif gname == "pizza":
            self._hr_gag_pizza(img, d, gl, t, say, dy)
        self.vis_horror = (255, int(150 * min(1.0, 0.2 + level)), 40) if not dark else (60, 0, 0)
        return img

    def _hr_walker(self, img, d, x, y, t, face, walk, robe=(120, 60, 70), cap=None):
        step = math.sin(t * 10) * 4 * walk
        for side in (-1, 1):
            d.line([(x + side * 2, y - 14), (x + side * 2 + side * step, y)], fill=(40, 36, 40), width=3)
        d.polygon([(x - 7, y - 12), (x + 7, y - 12), (x + 5, y - 32), (x - 5, y - 32)], fill=robe)
        self._blob(img, x, y - 38, 11, 11, (236, 200, 170), gloss=0.3)
        d.point((x + face * 3, y - 39), fill=(20, 20, 20))
        if cap:
            d.chord([x - 6, y - 46, x + 6, y - 36], 180, 360, fill=cap)
            d.line([(x, y - 41), (x + face * 8, y - 41)], fill=cap, width=2)
        else:
            d.chord([x - 6, y - 45, x + 6, y - 37], 180, 360, fill=(90, 80, 70))
        return (x + face * 6, y - 24)

    def _hr_gag_dog(self, img, d, gl, t, say):
        """Der Nachbar im Bademantel will mit dem Hund am Haus vorbei – der Hund stemmt sich dagegen."""
        y = HEIGHT - 32
        if gl < 2.4:
            x, walk = 340 - gl * 60, 1.0
        elif gl < 6.0:
            x, walk = 196 + math.sin(gl * 8) * 2, 0.3
        else:
            x, walk = 196 + (gl - 6.0) * 110, 1.6
        face = -1 if gl < 6.0 else 1
        hand = self._hr_walker(img, d, x, y, t, face, walk)
        if gl < 2.4:
            dx = x - 26
        elif gl < 6.0:
            dx = 236 - 4 * abs(math.sin(gl * 6))                                    # Hund stemmt sich
        else:
            dx = x + 30
        lean = 0.0 if gl < 2.4 or gl >= 6.0 else 1.0
        dy = y - 6
        self._blob(img, dx, dy, 20, 11, (160, 120, 70), gloss=0.4)
        hx = dx - 10 if gl < 6.0 else dx + 10
        self._blob(img, hx + lean * 4, dy - 6, 10, 9, (160, 120, 70), gloss=0.4)
        d.polygon([(hx - 3 + lean * 4, dy - 10), (hx + 2 + lean * 4, dy - 9), (hx + lean * 4, dy - 4)],
                  fill=(110, 80, 50))
        for k in (-6, -2, 3, 7):
            d.line([(dx + k, dy + 4), (dx + k + lean * 4, dy + 10)], fill=(120, 90, 50), width=2)
        d.line([hand, (hx + lean * 4, dy - 4)], fill=(200, 40, 40))
        if 2.6 <= gl < 4.6:
            say.append((x, y - 56, "Komm schon, Bello!"))
        elif 4.6 <= gl < 6.0:
            say.append((dx, dy - 20, "Wuff … nö."))

    def _hr_gag_pizza(self, img, d, gl, t, say, dy):
        """Pizzabote klingelt, die Tür geht auf, eine sehr lange Hand nimmt die Pizza."""
        y = dy + 4
        if gl < 2.6:
            x, walk = 340 - gl / 2.6 * 160, 1.0
        elif gl < 6.6:
            x, walk = 180.0, 0.0
        else:
            x, walk = 180 + (gl - 6.6) * 140, 2.0
        hand = self._hr_walker(img, d, x, y, t, -1 if gl < 6.6 else 1, walk, robe=(200, 40, 40), cap=(200, 40, 40))
        if gl < 4.2:
            px, py = hand[0] - 6, hand[1] - 2
        elif gl < 5.4:
            f = (gl - 4.2) / 1.2
            px, py = HR_DOOR - 6 + (hand[0] - HR_DOOR) * (1 - f), hand[1] - 2 - f * 4
        else:
            px = None
        if 4.0 <= gl < 5.6:                                                         # sehr lange Hand
            f = min(1.0, (gl - 4.0) / 0.3) if gl < 4.2 else (1.0 if gl < 5.4 else 1 - (gl - 5.4) / 0.2)
            tip = (HR_DOOR + (hand[0] - 8 - HR_DOOR) * f, y - 26)
            d.line([(HR_DOOR, y - 26), tip], fill=(170, 180, 170), width=3)
            for k in range(4):
                d.line([tip, (tip[0] + 3, tip[1] - 4 + k * 2.5)], fill=(170, 180, 170))
        if px is not None:
            d.rectangle([px - 9, py - 3, px + 9, py + 1], fill=(240, 230, 210), outline=(150, 120, 80))
        if 2.6 <= gl < 3.6:
            say.append((x, y - 56, "Pizza! Ding-dong!"))
        elif 5.6 <= gl < 6.6:
            for k in range(2):
                d.ellipse([x - 8 + k * 6, y - 60 + (gl - 5.6) * 30, x - 4 + k * 6, y - 56 + (gl - 5.6) * 30],
                          fill=(230, 200, 60))
            say.append((x, y - 56, "Stimmt so …?"))
        elif gl >= 6.6:
            say.append((x, y - 56, "Aaaah!"))

    # -- Puppenzimmer ------------------------------------------------------------------------------ #
    def _hr_dolls(self, s, o, st, t, dt, playing, bang, level, boom, bt, talk, gname, gl, say):
        img = self._hr_room().copy()
        d = ImageDraw.Draw(img)
        lights_out = gname == "licht" and (1.0 <= gl < 2.6 or 6.4 <= gl < 7.4)
        front = gname == "licht" and 2.6 <= gl < 6.4
        stare = 0.0
        if gname == "drehen":
            stare = min(1.0, max(0.0, (gl - 1.2) / 0.2)) if gl < 6.0 else 0.0
        # Schaukelpferd und Spieluhr
        ang = (math.sin(t * math.pi / max(0.3, s.get("period") or 0.5)) * (0.12 + 0.12 * level)
               if playing else math.sin(t * 0.8) * 0.02)
        if boom:
            ang = math.sin(t * 14) * 0.32
        if stare:
            ang = 0.0
        self._hr_horse(img, d, 54, HR_FLOOR + 10, ang)
        if boom and 0.4 < bt < 2.6:
            say.append((70, HR_FLOOR - 60, "Hüüü-hott!"))
        st["spin"] = st.get("spin", 0.0) + dt * (2 + 10 * level + (20 if boom else 0)) * (0 if stare else 1)
        self._hr_musicbox(img, d, 258, HR_FLOOR - 26, st["spin"], level)
        # Puppen im Regal (oder plötzlich vorn)
        for i, (x, hair, dress) in enumerate(HR_DOLLS):
            if gname == "teeparty" and i == 1:
                continue
            tilt = (math.sin(t * 2 + i) * 0.1 + (0.25 * bang * (1 if (st["pose"] + i) % 2 else -1)))
            if boom:
                tilt = math.sin(t * 16 + i) * 0.45
            if talk:
                tilt = 0.05 * math.sin(t + i)
            look = math.sin(t * 0.7 + i * 1.3)
            if stare:
                tilt, look = (0.35 if i % 2 else -0.35) * stare, 0.0
            if front:
                fx = 40 + i * 76
                self._hr_doll(img, d, fx, VIS_H + 6, hair, dress, tilt=0.1 * (i - 1.5), look=0, scale=2.0)
                continue
            self._hr_doll(img, d, x, HR_SHELF_Y, hair, dress, tilt, look, stare, glow=lights_out,
                          pull=talk and i == 2)
        if front and 2.8 <= gl < 5.6:
            say.append((WIDTH / 2, 70, "Wir waren das nicht."))
        if stare and 1.6 <= gl < 5.0:
            say.append((168, HR_SHELF_Y - 56, "Spiel mit uns …"))
        if talk:
            tl = t - s.get("talk_t", t)
            if tl < 3.0:
                say.append((HR_DOLLS[2][0], HR_SHELF_Y - 50, "Ma-ma!"))
        # Teddy, Teeparty, Springteufel
        teddy = (196, HR_FLOOR + 14)
        arm = 0.0
        if gname == "teeparty":
            arm = min(1.0, gl / 1.0) if gl < 6.5 else 0.0
            tx = 150
            d.rectangle([tx - 20, HR_FLOOR + 2, tx + 20, HR_FLOOR + 6], fill=(240, 230, 230))
            for x in (tx - 18, tx + 18):
                d.line([(x, HR_FLOOR + 6), (x, HR_FLOOR + 18)], fill=(200, 190, 190), width=2)
            x, hair, dress = HR_DOLLS[1]
            self._hr_doll(img, d, tx - 34, HR_FLOOR + 10, hair, dress, tilt=0.15, look=1.0)
            d.rectangle([tx - 4, HR_FLOOR - 4, tx + 4, HR_FLOOR + 2], fill=(250, 250, 250))   # Tasse
            if 1.4 <= gl < 6.0:
                spill = max(0.0, gl - 3.4)
                d.line([(teddy[0] - 22, teddy[1] - 30), (tx, HR_FLOOR - 4)], fill=(170, 110, 60), width=2)
                if spill:
                    self._blob(img, tx + 2, HR_FLOOR + 4, min(40.0, 10 + spill * 14), 5, (170, 110, 60),
                               gloss=0.6, flat=True)
            if 1.2 <= gl < 3.2:
                say.append((teddy[0], teddy[1] - 48, "Noch ein Tässchen?"))
            elif 4.0 <= gl < 6.4:
                say.append((tx - 34, HR_FLOOR - 40, "Es läuft über …"))
        hand = self._hr_teddy(img, d, teddy[0], teddy[1], arm) if not front else teddy
        if gname == "teeparty" and arm > 0:
            self._blob(img, hand[0] - 12, hand[1] - 2, 16, 12, (250, 250, 250), gloss=0.5)   # Teekanne
            d.line([(hand[0] - 20, hand[1] - 2), (hand[0] - 26, hand[1] - 8)], fill=(250, 250, 250), width=3)
        if gname == "kasten":
            self._hr_gag_jack(img, d, gl, t, say)
        if lights_out:
            img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.92)
            d = ImageDraw.Draw(img)
            for x, _, _ in HR_DOLLS:
                for side in (-1, 1):
                    d.ellipse([x + side * 3.6 - 1.8, HR_SHELF_Y - 26, x + side * 3.6 + 1.8, HR_SHELF_Y - 22],
                              fill=(255, 60, 40))
        elif stare:
            vign = Image.new("L", img.size, 0)
            vd = ImageDraw.Draw(vign)
            for r in range(10):
                vd.rectangle([r * 10, r * 7, WIDTH - r * 10, HEIGHT - r * 7], outline=int(200 - r * 20), width=10)
            img.paste((0, 0, 0), (0, 0), vign.point(lambda v: int(v * stare)))
        self.vis_horror = (255, 120, 170) if not (lights_out or stare) else (80, 0, 0)
        return img

    def _hr_gag_jack(self, img, d, gl, t, say):
        """Springteufel: Kiste wackelt, Clown springt heraus („Buh!“), wackelt nach und ist schwindlig."""
        x, y = 120, HR_FLOOR + 22
        d.rectangle([x - 12, y - 20, x + 12, y], fill=(60, 120, 200), outline=(30, 60, 120))
        d.text((x - 4, y - 18), "?", font=self.f_small_b, fill=(250, 220, 60))
        d.line([(x + 12, y - 10), (x + 18, y - 10 + math.sin(gl * 12) * 4)], fill=(200, 200, 200), width=2)
        if gl < 2.0:
            if gl > 1.0:
                for k in range(2):
                    d.line([(x - 14 - k * 4, y - 22), (x - 18 - k * 4, y - 26)], fill=(240, 240, 240))
            return
        k = gl - 2.0
        h = 36 + 10 * math.sin(k * 10) * math.exp(-k * 0.7)
        sway = math.sin(k * 7) * 8 * math.exp(-k * 0.4)
        top = (x + sway, y - 20 - h)
        for i in range(8):                                                          # Feder
            yy = y - 20 - h * i / 8
            d.line([(x - 5 + sway * i / 8, yy), (x + 5 + sway * i / 8, yy - h / 16)], fill=(200, 200, 210), width=2)
        self._blob(img, top[0], top[1], 20, 20, (250, 246, 240), gloss=0.4)
        for side in (-1, 1):
            self._blob(img, top[0] + side * 11, top[1] - 3, 9, 9, (240, 120, 40), gloss=0.3)
            if k > 2.4:
                d.line([(top[0] + side * 4 - 2, top[1] - 4), (top[0] + side * 4 + 2, top[1])], fill=(20, 20, 20))
                d.line([(top[0] + side * 4 + 2, top[1] - 4), (top[0] + side * 4 - 2, top[1])], fill=(20, 20, 20))
            else:
                d.ellipse([top[0] + side * 4 - 1.5, top[1] - 4, top[0] + side * 4 + 1.5, top[1] - 1], fill=(20, 20, 20))
        self._blob(img, top[0], top[1] + 1, 5, 5, (230, 40, 40), gloss=0.6)
        d.arc([top[0] - 6, top[1] + 1, top[0] + 6, top[1] + 8], 0, 180, fill=(200, 40, 60), width=2)
        d.polygon([(top[0] - 6, top[1] - 9), (top[0] + 6, top[1] - 9), (top[0], top[1] - 22)], fill=(80, 60, 200))
        if k < 1.4:
            say.append((top[0], top[1] - 24, "BUH!"))
        elif 2.6 <= k < 4.8:
            say.append((top[0], top[1] - 24, "Mir ist schwindlig …"))
