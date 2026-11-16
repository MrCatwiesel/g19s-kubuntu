"""Visualisierung „Lagerfeuer“ (campfire, Mixin CampfireVisual): Der ruhige Stil für den Abend. An einem See im Wald
brennt ein Lagerfeuer – die Flammen wachsen mit der Lautstärke, Funken stieben auf hohe Schläge, das Feuer spiegelt
sich im Wasser. Glühwürmchen tanzen, die Sterne drehen sich langsam, ab und zu fällt eine Sternschnuppe, eine Eule
blinzelt. Auf Wunsch sitzen zwei Leute am Feuer und rösten Marshmallows. Keine Gags. Höhepunkt: Das Feuer lodert auf,
die Funken steigen in einer Spirale. Wortbeitrag: Das Feuer wird ruhig, die Eule ruft leise.
"""
import math
import random

CF_FLOOR = VIS_H - 30
CF_FIRE = (160, CF_FLOOR + 6)
CF_LAKE_Y = VIS_H - 18
CF_BOOM = 5.0


class CampfireVisual:
    vis_fire = None

    def _cf_scene(self):
        if "_cf_bg" in self.__dict__:
            return self._cf_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([4, 6, 22], np.float32), np.array([30, 30, 60], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        self._blob(img, 262, 30, 20, 20, (240, 236, 210), gloss=0.1)
        self._blob(img, 262, 30, 60, 60, (200, 200, 230), alpha=0.12, flat=True)
        rng = random.Random(21)
        for x in range(-10, WIDTH + 20, 18):                                        # Waldsilhouette
            h = rng.randint(50, 90)
            d.polygon([(x - 14, CF_FLOOR - 30), (x + 14, CF_FLOOR - 30), (x, CF_FLOOR - 30 - h)], fill=(10, 20, 18))
        d.rectangle([0, CF_FLOOR - 32, WIDTH, CF_FLOOR + 10], fill=(18, 30, 22))
        d.rectangle([0, CF_LAKE_Y - 8, WIDTH, HEIGHT], fill=(10, 16, 36))              # See
        for k in range(10):
            y = CF_LAKE_Y - 4 + k * 3
            d.line([(rng.uniform(0, 200), y), (rng.uniform(120, 320), y)], fill=(20, 28, 56))
        d.polygon([(30, CF_FLOOR - 4), (70, CF_FLOOR - 4), (50, CF_FLOOR - 40)], fill=(150, 90, 50))   # Zelt
        d.polygon([(46, CF_FLOOR - 4), (54, CF_FLOOR - 4), (50, CF_FLOOR - 22)], fill=(40, 24, 14))
        d.line([(50, CF_FLOOR - 40), (50, CF_FLOOR - 46)], fill=(120, 80, 40), width=2)
        d.rounded_rectangle([206, CF_FLOOR - 8, 266, CF_FLOOR + 2], radius=4, fill=(90, 60, 36))  # Baumstamm
        d.ellipse([260, CF_FLOOR - 8, 270, CF_FLOOR + 2], fill=(150, 110, 70))
        gx, gy = 276, CF_FLOOR - 4                                                  # Gitarre am Stamm
        d.line([(gx, gy), (gx + 18, gy - 40)], fill=(80, 50, 30), width=3)
        self._blob(img, gx - 2, gy - 4, 16, 20, (170, 110, 50), gloss=0.5, ang=0.4)
        self._blob(img, gx + 4, gy - 14, 12, 14, (170, 110, 50), gloss=0.5, ang=0.4)
        d.ellipse([gx - 1, gy - 10, gx + 5, gy - 4], fill=(40, 24, 14))
        stars = [(rng.uniform(-200, 200), rng.uniform(-200, 200), rng.uniform(0.4, 1.0)) for _ in range(70)]
        self._cf_stars = stars
        self._cf_bg = img
        return img

    @vis_style("campfire")
    def vis_campfire(self, s, o, color):
        t = s["t"]
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        img = self._cf_scene().copy()
        d = ImageDraw.Draw(img)
        st = self._vstate("campfire", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                                "fast": s["level"], "boom": -99.0, "rng": random.Random(181),
                                                "start": t, "sparks": [], "flies": [], "flame": 0.4,
                                                "shoot": None, "owl": -9.0})
        dt = self._vis_dt(st, t)
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
        playing = (s.get("active") or demo) and not talk
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 20 \
                and t - st["start"] > 5:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < CF_BOOM
        rng = st["rng"]
        # Sterne drehen sich langsam um den Polarstern
        cx, cy = 60, -40
        a0 = t * 0.004
        for sx, sy, z in self._cf_stars:
            x = cx + sx * math.cos(a0) - sy * math.sin(a0)
            y = cy + sx * math.sin(a0) + sy * math.cos(a0) + 120
            if 0 <= x < WIDTH and 0 <= y < CF_FLOOR - 70:
                tw = 0.7 + 0.3 * math.sin(t * 2 + sx)
                c = int(200 * z * tw)
                d.point((x, y), fill=(c, c, min(255, c + 30)))
        if st["shoot"] is None and rng.random() < dt / 25:
            st["shoot"] = (t, rng.uniform(80, 300), rng.uniform(10, 50))
        if st["shoot"]:
            k = (t - st["shoot"][0]) / 0.8
            if k > 1:
                st["shoot"] = None
            else:
                x, y = st["shoot"][1] - k * 90, st["shoot"][2] + k * 30
                d.line([(x, y), (x + 16, y - 5)], fill=(255, 255, 230), width=1)
        # Feuer
        want = (0.3 + 0.9 * level) if not talk else 0.25
        if boom:
            want = 1.6
        st["flame"] += (want - st["flame"]) * min(1.0, dt * 3)
        fk = st["flame"]
        fx, fy = CF_FIRE
        self._blob(img, fx, fy - 20, 180 + 120 * min(1.4, fk), 90 + 60 * min(1.4, fk), (255, 150, 60),
                   alpha=round(min(0.45, 0.18 + 0.15 * fk), 2), flat=True)
        d = ImageDraw.Draw(img)
        for k in range(5):                                                          # Holzscheite und Steine
            a = k * 1.26
            d.ellipse([fx + math.cos(a) * 18 - 5, fy + math.sin(a) * 4 - 3, fx + math.cos(a) * 18 + 5,
                       fy + math.sin(a) * 4 + 3], fill=(90, 90, 96))
        d.line([(fx - 14, fy), (fx + 12, fy - 6)], fill=(80, 50, 30), width=4)
        d.line([(fx + 14, fy), (fx - 12, fy - 6)], fill=(70, 44, 26), width=4)
        for layer, col, w in ((0, (230, 70, 20), 1.0), (1, (255, 150, 40), 0.7), (2, (255, 230, 120), 0.4)):
            for k in range(5):
                hh = (22 + 14 * abs(math.sin(t * (6 + k) + k * 1.7 + layer))) * fk * w + 4
                bx = fx - 12 * w + k * 6 * w
                sway = math.sin(t * 3 + k + layer) * 3
                d.polygon([(bx - 5 * w, fy - 4), (bx + 5 * w, fy - 4), (bx + sway, fy - 4 - hh)], fill=col)
        if (playing and new_hat) or (boom and rng.random() < 0.7):
            for _ in range(3 if boom else 2):
                st["sparks"].append([fx + rng.uniform(-6, 6), fy - 20 * fk, rng.uniform(-10, 10), -rng.uniform(30, 70),
                                     1.0, (255, 200, 90)])
        for p in st["sparks"]:
            if boom:
                p[2] += math.cos(t * 4 + p[1] * 0.1) * 30 * dt
        self._fx_step(st["sparks"], dt, grav=-4.0, fade=0.5, cap=90)
        for x, y, vx, vy, life, col in st["sparks"]:
            d.point((x, y), fill=tuple(int(v * life) for v in col))
        # Spiegelung im See
        refl = Image.new("L", img.size, 0)
        rd = ImageDraw.Draw(refl)
        for k in range(6):
            y = CF_LAKE_Y + 2 + k * 3
            w = (20 + 10 * fk) * (1 - k / 8) + math.sin(t * 3 + k) * 4
            rd.line([(fx - w, y), (fx + w, y)], fill=int(90 * fk * (1 - k / 7)), width=2)
        img.paste((255, 160, 70), (0, 0), refl)
        d = ImageDraw.Draw(img)
        # Leute am Feuer mit Marshmallows
        if o.get("people", True):
            for side, shirt, hat in ((-1, (60, 90, 140), "beanie"), (1, (150, 60, 60), None)):
                x = fx + side * 52
                stick = (fx + side * 10, fy - 26 - 4 * math.sin(t * 0.7 + side))
                pose = {"lh": (side * 4 if side > 0 else 12, 10), "rh": (-12 if side > 0 else 4, 10)}
                hc, hands = self._fig(img, d, x, CF_FLOOR + 2, t, shirt, pose, h=0.85, sit=True, hat=hat,
                                      hat_col=(200, 80, 60), face=-side, eyes="closed" if level < 0.2 else "dot")
                hx, hy = hands[1] if side < 0 else hands[0]
                d.line([(hx, hy), stick], fill=(140, 100, 60), width=2)
                roast = min(1.0, (t % 30) / 30)
                d.rounded_rectangle([stick[0] - 3, stick[1] - 3, stick[0] + 3, stick[1] + 3], radius=2,
                                    fill=(int(250 - 90 * roast), int(246 - 140 * roast), int(236 - 180 * roast)))
        # Glühwürmchen
        if playing and new_hat and len(st["flies"]) < 14:
            st["flies"].append([rng.uniform(0, WIDTH), rng.uniform(CF_FLOOR - 70, CF_FLOOR - 10), rng.uniform(0, 6), t])
        st["flies"] = [f for f in st["flies"] if t - f[3] < 8]
        for x, y, ph, t0 in st["flies"]:
            k = t - t0
            fx2 = x + math.sin(t * 0.8 + ph) * 14
            fy2 = y + math.cos(t * 1.1 + ph) * 8
            br = max(0.0, math.sin(t * 3 + ph)) * min(1.0, k, 8 - k)
            if br > 0.1:
                self._blob(img, fx2, fy2, 8, 8, (200, 255, 120), alpha=round(0.5 * br, 2), flat=True)
                d.point((fx2, fy2), fill=(230, 255, 180))
        # Eule im Baum
        ox, oy = 296, CF_FLOOR - 92
        d.line([(280, oy + 10), (318, oy + 8)], fill=(20, 26, 20), width=3)
        self._blob(img, ox, oy, 16, 20, (90, 70, 50), gloss=0.3)
        blink = (t % 7) < 0.15 or (talk and int((t - s.get("talk_t", t)) / 3) % 2 == 0 and (t % 3) < 0.15)
        for side in (-1, 1):
            if blink:
                d.line([(ox + side * 4 - 2, oy - 3), (ox + side * 4 + 2, oy - 3)], fill=(30, 20, 10))
            else:
                d.ellipse([ox + side * 4 - 3, oy - 6, ox + side * 4 + 3, oy], fill=(250, 220, 90))
                d.point((ox + side * 4, oy - 3), fill=(10, 10, 10))
        if talk and (t - s.get("talk_t", t)) % 6 < 1.5:
            d.text((ox - 36, oy - 22), "huu-huu", font=self.f_tiny, fill=(200, 200, 220))
        self.vis_fire = (255, int(60 + 80 * min(1.0, fk)), 10)
        return img
