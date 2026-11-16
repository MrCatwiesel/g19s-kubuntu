"""Visualisierung „Fasching“ (carnival, Mixin CarnivalVisual): Rosenmontagszug in der Altstadt. Ein Umzugswagen mit
riesigem Narrenkopf (nickt im Takt) rollt durchs Bild, vom Wagen fliegen Kamelle auf den Bass, vorn tanzt die
Funkengarde mit Beinwurf, ganz vorn jubelt das Publikum. Höhepunkt: Polonaise quer durchs Bild („Helau!“ oder
„Alaaf!“). Wortbeitrag: Büttenrede mit Tusch. Gags: Pferdekostüm (die Hälften laufen auseinander), ein riesiger Orden,
der umgedrehte Regenschirm füllt sich mit Kamelle.
"""
import math
import random

CV_FLOOR = VIS_H - 30
CV_GARDE = (96, 160, 224)
CV_GAGS = {"pferd": 8.0, "orden": 7.0, "schirm": 8.0}
CV_GAG_FIRST, CV_GAG_PAUSE = 8.0, (12.0, 20.0)
CV_BOOM = 6.0
CV_FLOAT_PERIOD = 28.0
CV_COLORS = [(230, 50, 60), (250, 200, 40), (60, 140, 230), (90, 190, 90), (220, 100, 200), (250, 140, 40)]


class CarnivalVisual:
    vis_cv = None

    def _cv_scene(self):
        if "_cv_bg" in self.__dict__:
            return self._cv_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (150, 200, 245))
        d = ImageDraw.Draw(img)
        rng = random.Random(12)
        x = -6
        while x < WIDTH:                                                            # Fachwerk-Häuser
            w = rng.randint(40, 56)
            h = rng.randint(70, 100)
            col = rng.choice([(240, 220, 180), (230, 190, 170), (210, 220, 200), (240, 240, 230)])
            d.rectangle([x, CV_FLOOR - 20 - h, x + w, CV_FLOOR], fill=col, outline=(110, 80, 60))
            d.polygon([(x - 3, CV_FLOOR - 20 - h), (x + w + 3, CV_FLOOR - 20 - h), (x + w / 2, CV_FLOOR - 46 - h)],
                      fill=(170, 70, 50))
            for k in range(1, 4):
                d.line([(x, CV_FLOOR - 20 - h + k * h / 4), (x + w, CV_FLOOR - 20 - h + k * h / 4)],
                       fill=(110, 80, 60), width=2)
            d.line([(x, CV_FLOOR - 20 - h), (x + w, CV_FLOOR - 20)], fill=(110, 80, 60), width=2)
            for wy in (CV_FLOOR - 14 - h + 8, CV_FLOOR - 14 - h * 0.5):
                for wx in (x + 8, x + w - 18):
                    d.rectangle([wx, wy, wx + 10, wy + 12], fill=(120, 160, 200), outline=(250, 250, 250))
            x += w
        d.rectangle([0, CV_FLOOR - 20, WIDTH, HEIGHT], fill=(150, 146, 140))         # Straße
        for y in range(CV_FLOOR - 16, HEIGHT, 6):
            for xx in range((y // 6 % 2) * 6, WIDTH, 12):
                d.rectangle([xx, y, xx + 10, y + 4], outline=(130, 126, 120))
        for row, y0 in enumerate((22, 40)):                                         # Wimpelketten
            pts = [(k * 20 - 4, y0 + 6 * math.sin(k * 0.8 + row)) for k in range(18)]
            d.line(pts, fill=(80, 70, 60))
            for k, (px, py) in enumerate(pts[:-1]):
                d.polygon([(px, py), (px + 12, py), (px + 6, py + 10)], fill=CV_COLORS[(k + row) % 6])
        self._cv_bg = img
        return img

    def _cv_float(self, img, d, x, t, bang, mouth, ouch=0.0):
        """Umzugswagen mit Narrenkopf; x = Mitte."""
        y = CV_FLOOR - 16
        d.rectangle([x - 50, y - 26, x + 50, y], fill=(60, 140, 230))
        for k in range(10):
            d.polygon([(x - 50 + k * 10, y), (x - 40 + k * 10, y), (x - 45 + k * 10, y + 6)], fill=CV_COLORS[k % 6])
        for wx in (-34, 34):
            d.ellipse([x + wx - 9, y - 4, x + wx + 9, y + 14], fill=(40, 40, 44))
        hx, hy = x, y - 58 + bang * 3
        self._blob(img, hx, hy, 58, 54, (250, 214, 180), gloss=0.4, ang=math.sin(t * 2) * 0.05)
        for side, c in ((-1, (230, 50, 60)), (1, (250, 200, 40))):                  # Kappe
            tip = (hx + side * 40, hy - 40 + math.sin(t * 4 + side) * 4)
            d.polygon([(hx - 24 * (side < 0) + 2 * (side > 0), hy - 18), (hx + 24 * (side > 0) - 2 * (side < 0), hy - 18),
                       tip], fill=c)
            self._blob(img, tip[0], tip[1] + 3, 9, 9, (250, 250, 250), gloss=0.4)
        d.rectangle([hx - 28, hy - 22, hx + 28, hy - 14], fill=(90, 190, 90))
        for side in (-1, 1):
            d.ellipse([hx + side * 11 - 6, hy - 10, hx + side * 11 + 6, hy + 2], fill=(255, 255, 255))
            d.ellipse([hx + side * 11 - 2.5, hy - 6, hx + side * 11 + 2.5, hy - 1], fill=(30, 30, 40))
            self._blob(img, hx + side * 18, hy + 8, 10, 8, (240, 120, 130), gloss=0.2)
        self._blob(img, hx, hy + 2, 12 + 4 * ouch, 11 + 4 * ouch, (230, 40, 50), gloss=0.6)
        d.chord([hx - 14, hy + 6 - mouth * 4, hx + 14, hy + 18 + mouth * 6], 0, 180, fill=(120, 30, 40))
        return (hx, hy)

    @vis_style("carnival")
    def vis_carnival(self, s, o, color):
        t = s["t"]
        img = self._cv_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        call = "Alaaf!" if o.get("call", "helau") == "alaaf" else "Helau!"
        st = self._vstate("carnival", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                                "boom": -99.0, "gag": None, "order": [], "k": 0, "candy": [],
                                                "next_gag": t + CV_GAG_FIRST, "rng": random.Random(81), "start": t,
                                                "conf": [], "fill": 0})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        playing = (s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        bang = math.sin(math.pi * min(1.0, (t - s.get("beat_t", t)) / (period * 0.6))) if playing else 0.0
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < CV_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= CV_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*CV_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(CV_GAGS), len(CV_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
            st["fill"] = 0
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        say = []
        rng = st["rng"]
        # Umzugswagen (fährt langsam von rechts nach links durch, dann von vorn)
        ph = ((t - st["start"]) / CV_FLOAT_PERIOD + 0.45) % 1.0 if not demo else 0.45
        fx = WIDTH + 80 - ph * (WIDTH + 160)
        mouth = min(1.0, level * 1.5) if playing else (0.5 * abs(math.sin(t * 8)) if talk else 0.0)
        head = self._cv_float(img, d, fx, t, bang, mouth)
        for k, side in enumerate((-1, 1)):                                          # Werfer auf dem Wagen
            pose = {"lh": (-12, -14 if (st["k"] + k) % 2 else 10), "rh": (12, -14 if (st["k"] + k + 1) % 2 else 10)}
            self._fig(img, d, fx + side * 36, CV_FLOOR - 42, t, CV_COLORS[k + 2], pose, h=0.7, hat="jester")
        if playing and new_beat:
            st["k"] += 1
            if s["bass"] > 0.4 and -40 < fx < WIDTH + 40:
                for _ in range(3):
                    st["candy"].append([fx + rng.uniform(-30, 30), CV_FLOOR - 70, rng.uniform(-70, 70),
                                        rng.uniform(-150, -90), rng.randrange(6)])
        for c in st["candy"]:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[3] += 300 * dt
        st["candy"] = [c for c in st["candy"] if c[1] < VIS_H + 10][-60:]
        # Funkengarde mit Beinwurf
        if not boom:
            for i, gx in enumerate(CV_GARDE):
                kick = playing and (st["k"] + i) % 2 == 0
                kk = bang if kick else 0.0
                pose = {"lh": (-14, -16), "rh": (14, -16), "lf": (-4, 34), "rf": (18 * kk + 4, 34 - 40 * kk)}
                self._fig(img, d, gx, CV_FLOOR - 4, t, (230, 40, 50), pose, h=0.95, dress=(250, 250, 250),
                          hat="top", hat_col=(230, 40, 50), legs=(250, 240, 230), hair=(220, 180, 80))
        # Kamelle
        for x, y, vx, vy, ci in st["candy"]:
            d.rectangle([x - 2, y - 1, x + 2, y + 1], fill=CV_COLORS[ci])
            d.line([(x - 4, y - 2), (x - 2, y)], fill=CV_COLORS[ci])
            d.line([(x + 2, y), (x + 4, y + 2)], fill=CV_COLORS[ci])
        # Publikum ganz vorn
        for i in range(7):
            px = 18 + i * 48 + (6 if i % 2 else 0)
            up = playing and (st["k"] + i) % 2 == 0
            pose = {"lh": (-10, -18 if up else 8), "rh": (10, -18 if up else 8)}
            hat = ("jester", "party", "cowboy", "crown", None, "top", "party")[i]
            hair = [(250, 120, 180), (60, 200, 230), (120, 70, 40), (240, 200, 60), (230, 90, 40), (40, 30, 30),
                    (180, 120, 250)][i]
            if gname == "schirm" and i == 4:
                self._cv_gag_umbrella(img, d, gl, t, say, px, st)
                continue
            self._fig(img, d, px, VIS_H + 40, t, CV_COLORS[i % 6], pose, h=0.8, hat=hat, hair=hair,
                      mouth=0.8 if up else 0.0)
        # Höhepunkt: Polonaise
        if boom:
            for i in range(7):
                x = -40 + (bt / CV_BOOM) * (WIDTH + 140) - i * 26
                pose = {"lh": (16, 2), "rh": (18, 0), "lf": (-6 + 6 * math.sin(t * 10 + i), 34),
                        "rf": (6 - 6 * math.sin(t * 10 + i), 34)}
                self._fig(img, d, x, CV_FLOOR, t, CV_COLORS[i % 6], pose, h=0.85, hat=("party", "jester", "top")[i % 3])
            if 0.4 < bt < 4.0:
                say.append((160, 70, call))
        # Büttenrede
        if talk:
            tl = t - s.get("talk_t", t)
            bx = 40
            d.rectangle([bx - 18, CV_FLOOR - 40, bx + 18, CV_FLOOR], fill=(150, 100, 60))
            for k in range(3):
                d.line([(bx - 18, CV_FLOOR - 34 + k * 14), (bx + 18, CV_FLOOR - 34 + k * 14)], fill=(90, 70, 50), width=2)
            hc, _ = self._fig(img, d, bx, CV_FLOOR - 36, t, (230, 50, 60), {"lh": (-12, -10), "rh": (12, 4)}, h=0.7,
                              hat="jester", mouth=abs(math.sin(t * 9)))
            if int(tl / 3.0) % 2 == 1 and tl % 3.0 < 1.2:
                say.append((bx + 60, CV_FLOOR - 90, "Tusch! Täterätä!"))
            elif tl < 2.5:
                say.append((hc[0] + 10, hc[1] - 24, "Liebe Närrinnen und Narrhalesen …"))
        if gname == "pferd":
            self._cv_gag_horse(img, d, gl, t, say)
        elif gname == "orden":
            self._cv_gag_medal(img, d, gl, t, say)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_cv = CV_COLORS[st["k"] % 6]
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _cv_gag_horse(self, img, d, gl, t, say):
        """Pferdekostüm: Vorder- und Hinterteil laufen auseinander."""
        split = 0.0 if gl < 2.6 else min(1.0, (gl - 2.6) / 2.0)
        x = 340 - min(1.0, gl / 2.6) * 180
        y = CV_FLOOR
        col = (170, 110, 60)
        for part in ("front", "back"):
            px = x - 14 - split * 70 if part == "front" else x + 14 + split * 50
            for k in (-6, 6):
                step = math.sin(t * 10 + k) * 4
                d.line([(px + k, y - 26), (px + k + step, y)], fill=(70, 62, 90), width=4)
            self._blob(img, px, y - 32, 30, 20, col, gloss=0.4)
            if part == "front":
                self._limb(img, (px - 10, y - 36), (px - 18, y - 56), 9, col)
                self._blob(img, px - 22, y - 58, 16, 12, col, gloss=0.4)
                d.point((px - 24, y - 61), fill=(0, 0, 0))
                for k in range(4):
                    d.line([(px - 12, y - 52 + k * 4), (px - 6, y - 48 + k * 4)], fill=(80, 50, 30), width=2)
            else:
                d.line([(px + 14, y - 34), (px + 22, y - 22 + math.sin(t * 6) * 3)], fill=(80, 50, 30), width=3)
        if 3.4 <= gl < 5.4:
            say.append((x - 60, y - 80, "Wo willst du hin?!"))
        elif gl >= 5.4:
            say.append((x + 60, y - 70, "Zur Kamelle!"))

    def _cv_gag_medal(self, img, d, gl, t, say):
        """Ein Narr bekommt einen riesigen Orden – und kippt unter dem Gewicht um."""
        x, y = 250, CV_FLOOR
        tip = 0.0 if gl < 3.0 else min(1.0, (gl - 3.0) / 0.6)
        lean = tip * 1.2
        hc, hands = self._fig(img, d, x, y, t, (90, 190, 90), {"lh": (-10, 14), "rh": (10, 14)}, h=0.9,
                              hat="jester", lean=lean, eyes="big" if tip else "dot")
        r = 4 + min(1.0, gl / 2.0) * 14
        mx, my = hc[0] + 6 * lean, hc[1] + 30
        d.line([(hc[0] - 6, hc[1] + 8), (mx, my - r)], fill=(230, 50, 60), width=3)
        d.line([(hc[0] + 6, hc[1] + 8), (mx, my - r)], fill=(250, 200, 40), width=3)
        self._blob(img, mx, my, r * 2, r * 2, (250, 210, 60), gloss=0.7)
        if r > 10:
            d.text((mx - 8, my - 8), "★", font=self.f_small_b, fill=(200, 140, 20))
        if 0.6 <= gl < 2.8:
            say.append((hc[0], hc[1] - 26, "Für besondere Verdienste!"))
        elif gl >= 3.8:
            say.append((hc[0] + 20, hc[1] - 20, "Schwer, die Ehre …"))

    def _cv_gag_umbrella(self, img, d, gl, t, say, px, st):
        """Umgedrehter Regenschirm fängt Kamelle, bis er umkippt."""
        hc, hands = self._fig(img, d, px, VIS_H + 40, t, (220, 100, 200), {"lh": (-4, -20), "rh": (4, -20)}, h=0.8,
                              hat="crown", hair=(230, 90, 40))
        hx, hy = hands[0]
        k = min(1.0, gl / 5.0)
        tilt = 0.0 if gl < 5.2 else min(1.0, (gl - 5.2) / 0.4)
        cx, cy = hx + tilt * 20, hy - 26
        d.line([(hx, hy), (cx, cy)], fill=(60, 60, 70), width=2)
        d.chord([cx - 22, cy - 18, cx + 22, cy + 14], 0, 180, fill=(60, 140, 230))
        rng = random.Random(5)
        for i in range(int(k * 26)):
            qx, qy = cx - 16 + rng.uniform(0, 32), cy + rng.uniform(0, 8) - k * 10
            d.rectangle([qx - 2, qy - 1, qx + 2, qy + 1], fill=CV_COLORS[i % 6])
        if 1.0 <= gl < 4.6:
            say.append((hc[0], hc[1] - 50, "Mehr! Mehr!"))
        elif gl >= 5.4:
            say.append((hc[0], hc[1] - 50, "Volltreffer …"))
