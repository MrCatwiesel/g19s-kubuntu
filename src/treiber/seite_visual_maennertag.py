"""Visualisierung „Männertag“ (father, Mixin FatherVisual): Rast auf der Bollerwagentour am Feldweg. Der Grillmeister
wendet die Würstchen im Takt (sie hüpfen auf dem Rost, die Glut glüht mit dem Bass), zwei Kumpels schunkeln am
Bollerwagen, auf dem eine Musikbox im Bass pumpt. Höhepunkt: Der Grill flambiert, die Würstchen fliegen, der
Strohhut qualmt („Medium!“). Wortbeitrag: Alle sitzen auf dem Wagen, einer studiert die Karte („Wo sind wir
eigentlich?“). Gags: Baumarkt-Ballett mit Akkuschrauber, Zollstock und Wasserwaage, der Bollerwagen rollt allein
davon (und kommt mit einer Gans zurück), eine Regenwolke nur über dem Grill und der Zollstock, der sich nicht
zusammenfalten lässt.
"""
import math
import random

FA_FLOOR = VIS_H - 24
FA_GRILL = (96, FA_FLOOR - 46)          # Mitte des Rosts
FA_CHEF = 52
FA_PALS = (178, 222)
FA_CART = 276                           # Mitte des Bollerwagens
FA_GAGS = {"ballett": 10.0, "tour": 9.0, "regen": 8.0, "zollstock": 7.0}
FA_GAG_FIRST, FA_GAG_PAUSE = 8.0, (12.0, 20.0)
FA_BOOM = 4.0
FA_SKIN = (240, 196, 160)
FA_SHIRTS = [(220, 220, 230), (90, 140, 200), (200, 80, 60)]


class FatherVisual:
    vis_ember = None                    # Glut für die Tastatur

    def _fa_scene(self):
        if "_fa_bg" in self.__dict__:
            return self._fa_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([110, 170, 240], np.float32), np.array([210, 230, 250], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        self._blob(img, 40, 30, 28, 28, (255, 240, 150), gloss=0.1)
        self._blob(img, 40, 30, 70, 70, (255, 240, 170), alpha=0.25, flat=True)
        for cx, cy, w in ((150, 24, 46), (250, 36, 40)):
            for k in range(3):
                self._blob(img, cx + k * w / 3, cy - (k == 1) * 5, w / 1.6, w / 2.8, (252, 252, 255), gloss=0.1)
        d.polygon([(0, FA_FLOOR - 70), (110, FA_FLOOR - 92), (230, FA_FLOOR - 74), (320, FA_FLOOR - 88),
                   (320, HEIGHT), (0, HEIGHT)], fill=(150, 196, 100))                 # Hügel
        d.polygon([(0, FA_FLOOR - 50), (160, FA_FLOOR - 62), (320, FA_FLOOR - 48), (320, HEIGHT), (0, HEIGHT)],
                  fill=(200, 190, 90))                                               # Rapsfeld
        rng = random.Random(8)
        for _ in range(70):
            x, y = rng.uniform(0, WIDTH), rng.uniform(FA_FLOOR - 56, FA_FLOOR - 30)
            d.point((x, y), fill=(250, 230, 60))
        d.rectangle([0, FA_FLOOR - 30, WIDTH, HEIGHT], fill=(120, 176, 80))           # Wiese
        d.polygon([(130, FA_FLOOR - 30), (190, FA_FLOOR - 30), (250, HEIGHT), (60, HEIGHT)], fill=(196, 170, 120))
        for _ in range(50):
            x, y = rng.uniform(0, WIDTH), rng.uniform(FA_FLOOR - 28, HEIGHT)
            d.line([(x, y), (x + rng.uniform(-2, 2), y - 4)], fill=(90, 150, 60))
        for tx, s in ((300, 1.0), (14, 0.7)):                                       # Bäume
            d.rectangle([tx - 3 * s, FA_FLOOR - 70 * s - 20, tx + 3 * s, FA_FLOOR - 30], fill=(110, 76, 50))
            for ox, oy, r in ((0, -80, 20), (-12, -68, 16), (12, -66, 16)):
                self._blob(img, tx + ox * s, FA_FLOOR + oy * s - 20, r * 2 * s, r * 1.8 * s, (70, 140, 60), gloss=0.3)
        d.line([(140, FA_FLOOR - 30), (140, FA_FLOOR - 96)], fill=(120, 90, 60), width=3)   # Wegweiser
        d.polygon([(118, FA_FLOOR - 96), (164, FA_FLOOR - 96), (170, FA_FLOOR - 90), (164, FA_FLOOR - 84),
                   (118, FA_FLOOR - 84)], fill=(250, 246, 230), outline=(120, 90, 60))
        d.text((121, FA_FLOOR - 97), "Badesee 3", font=self.f_tiny, fill=(60, 50, 40))
        self._fa_bg = img
        return img

    # -- Figuren -------------------------------------------------------------------------- #
    def _fa_man(self, img, d, x, y, t, shirt, pose, hat=True, lean=0.0, apron=False, sit=False, smoke=0.0):
        """Mann mit Bauch und Strohhut. pose: {"lh": (dx, dy), "rh": …, "lf": …, "rf": …} relativ zu Schulter/Hüfte."""
        hip = (x + lean * 6, y - (22 if sit else 36))
        for side, key in ((-1, "lf"), (1, "rf")):
            hj = (hip[0] + side * 5, hip[1])
            if sit:
                knee, foot = (hj[0] + 14, hj[1] + 2), (hj[0] + 14, y)
            else:
                f = pose.get(key, (side * 6, 36))
                knee, foot = _ik(hj, (hj[0] + f[0], hj[1] + f[1]), 18, 18, side)
            self._limb(img, hj, knee, 7, (70, 90, 130))
            self._limb(img, knee, foot, 6, (70, 90, 130))
            d.ellipse([foot[0] - 6, foot[1] - 4, foot[0] + 5, foot[1] + 1], fill=(80, 60, 40))
        neck = (hip[0] + lean * 10, hip[1] - 34)
        self._blob(img, (hip[0] + neck[0]) / 2 + 3, hip[1] - 14, 30, 30, shirt, gloss=0.3)   # Bauch
        self._blob(img, (hip[0] + neck[0]) / 2, neck[1] + 10, 24, 22, shirt, gloss=0.3)
        if apron:
            d.polygon([(neck[0] - 8, neck[1] + 8), (neck[0] + 8, neck[1] + 8), (hip[0] + 12, hip[1] + 4),
                       (hip[0] - 10, hip[1] + 4)], fill=(250, 250, 250))
            d.text((neck[0] - 9, neck[1] + 14), "CHEF", font=self.f_tiny, fill=(200, 40, 40))
        hands = []
        for side, key in ((-1, "lh"), (1, "rh")):
            sh = (neck[0] + side * 10, neck[1] + 5)
            h = pose.get(key, (side * 6, 22))
            elbow, hand = _ik(sh, (sh[0] + h[0], sh[1] + h[1]), 14, 14, -side)
            self._limb(img, sh, elbow, 6, shirt)
            self._limb(img, elbow, hand, 5, FA_SKIN)
            self._blob(img, hand[0], hand[1], 6, 6, FA_SKIN, gloss=0.2)
            hands.append(hand)
        hc = (neck[0], neck[1] - 9)
        self._blob(img, hc[0], hc[1], 20, 21, FA_SKIN, gloss=0.3)
        for side in (-1, 1):
            d.ellipse([hc[0] + side * 4 - 1.5, hc[1] - 2, hc[0] + side * 4 + 1.5, hc[1] + 1], fill=(30, 24, 24))
        d.line([(hc[0] - 6, hc[1] + 3), (hc[0] + 6, hc[1] + 3)], fill=(120, 80, 50), width=3)   # Schnurrbart
        d.arc([hc[0] - 4, hc[1] + 3, hc[0] + 4, hc[1] + 9], 10, 170, fill=(150, 60, 60))
        if hat:
            d.ellipse([hc[0] - 16, hc[1] - 10, hc[0] + 16, hc[1] - 4], fill=(230, 200, 110))
            d.chord([hc[0] - 9, hc[1] - 20, hc[0] + 9, hc[1] - 2], 180, 360, fill=(230, 200, 110))
            d.line([(hc[0] - 9, hc[1] - 9), (hc[0] + 9, hc[1] - 9)], fill=(200, 60, 60), width=2)
            if smoke:
                for k in range(3):
                    self._blob(img, hc[0] + math.sin(t * 3 + k) * 4, hc[1] - 22 - k * 8 - (t * 20 % 8),
                               10 + k * 3, 8 + k * 2, (90, 90, 90), alpha=round(0.6 * smoke, 2), flat=True)
        return hc, hands

    def _fa_cart(self, img, d, x, y, bass, tilt=0.0, goose=False):
        """Bollerwagen mit Getränkekiste und Musikbox; Deichsel nach links."""
        def R(px, py):
            return _hr_rot((x + px, y + py), (x, y), tilt)
        d.polygon([R(-30, -22), R(30, -22), R(28, -8), R(-28, -8)], fill=(150, 100, 60))
        for k in range(4):
            d.line([R(-30, -18 + k * 3), R(30, -18 + k * 3)], fill=(120, 80, 46))
        for wx in (-20, 20):
            c = R(wx, -6)
            d.ellipse([c[0] - 7, c[1] - 7, c[0] + 7, c[1] + 7], fill=(50, 50, 54))
            d.ellipse([c[0] - 2, c[1] - 2, c[0] + 2, c[1] + 2], fill=(200, 200, 200))
        d.line([R(-30, -14), R(-52, -4)], fill=(80, 80, 86), width=3)
        d.line([R(-52, -4), R(-56, -14)], fill=(80, 80, 86), width=3)
        p = R(-22, -22)                                                             # Kiste
        d.rectangle([p[0], p[1] - 14, p[0] + 22, p[1]], fill=(240, 200, 40))
        for k in range(4):
            d.rectangle([p[0] + 2 + k * 5, p[1] - 22, p[0] + 5 + k * 5, p[1] - 12], fill=(90, 60, 30))
            d.rectangle([p[0] + 2.5 + k * 5, p[1] - 24, p[0] + 4.5 + k * 5, p[1] - 21], fill=(230, 230, 230))
        b = R(8, -22)                                                               # Musikbox
        d.rounded_rectangle([b[0], b[1] - 20, b[0] + 22, b[1]], radius=3, fill=(40, 40, 46))
        for k, cy in enumerate((b[1] - 14, b[1] - 6)):
            r = 3 + bass * 2.5 if k == 0 else 4 + bass * 3
            d.ellipse([b[0] + 11 - r, cy - r, b[0] + 11 + r, cy + r], fill=(90, 90, 100), outline=(160, 160, 170))
        if goose:
            g = R(-8, -36)
            self._blob(img, g[0], g[1], 20, 13, (250, 250, 250), gloss=0.4)
            self._limb(img, (g[0] + 6, g[1] - 3), (g[0] + 10, g[1] - 16), 4, (250, 250, 250))
            self._blob(img, g[0] + 11, g[1] - 18, 8, 7, (250, 250, 250), gloss=0.4)
            d.polygon([(g[0] + 14, g[1] - 19), (g[0] + 20, g[1] - 17), (g[0] + 14, g[1] - 16)], fill=(250, 160, 40))
            d.point((g[0] + 12, g[1] - 19), fill=(0, 0, 0))

    # -- Ablauf ------------------------------------------------------------------------------ #
    @vis_style("father")
    def vis_father(self, s, o, color):
        t = s["t"]
        img = self._fa_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("father", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                              "boom": -99.0, "gag": None, "order": [], "k": 0, "flip": -9.0,
                                              "next_gag": t + FA_GAG_FIRST, "rng": random.Random(61), "start": t,
                                              "brown": [0.2, 0.4, 0.1, 0.3]})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        playing = (s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        bang = math.sin(math.pi * min(1.0, (t - s.get("beat_t", t)) / (period * 0.6))) if playing else 0.0
        level = s["level"] if playing else 0.0
        bass = s["bass"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < FA_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= FA_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*FA_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(FA_GAGS), len(FA_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["k"] += 1
            if s["bass"] > 0.5:
                st["flip"] = t
                st["fi"] = st["k"] % 4
        say = []
        # Bollerwagen (rollt beim Gag „tour“ davon)
        cx, tilt, goose = FA_CART, 0.0, False
        if gname == "tour":
            if gl < 4.0:
                cx = FA_CART + (gl / 4.0) ** 2 * 120
            elif gl < 6.0:
                cx = FA_CART + 120
            else:
                cx, goose = FA_CART + 120 - min(1.0, (gl - 6.0) / 1.6) * 120, True
            tilt = math.sin(t * 20) * 0.03
        self._fa_cart(img, d, cx, FA_FLOOR, bass if playing else 0.0, tilt, goose)
        # Grill
        gx, gy = FA_GRILL
        for lx in (-14, 14):
            d.line([(gx + lx, gy + 14), (gx + lx * 1.5, FA_FLOOR)], fill=(40, 40, 44), width=3)
        d.chord([gx - 24, gy - 18, gx + 24, gy + 22], 0, 180, fill=(30, 30, 34))
        glow = min(1.0, 0.3 + bass * 0.9) if not (gname == "regen" and gl > 2.0) else 0.1
        d.ellipse([gx - 20, gy - 3, gx + 20, gy + 5], fill=(int(120 + 135 * glow), int(40 + 80 * glow), 20))
        if gname == "regen" and gl > 2.0:
            d.chord([gx - 24, gy - 26, gx + 24, gy + 8], 180, 360, fill=(30, 30, 34))   # Deckel zu
            d.ellipse([gx - 3, gy - 30, gx + 3, gy - 24], fill=(30, 30, 34))
        else:
            for k in range(5):
                d.line([(gx - 22 + k * 11, gy - 2), (gx - 22 + k * 11, gy + 2)], fill=(150, 150, 156))
            d.line([(gx - 23, gy - 1), (gx + 23, gy - 1)], fill=(150, 150, 156))
            for i in range(4):                                                      # Würstchen
                if boom and 0.3 < bt < 3.4:
                    k = bt - 0.3
                    wx = gx - 15 + i * 10 + (i - 1.5) * 30 * k
                    wy = gy - 4 - 90 * k + 70 * k * k
                    if wy > gy - 4:
                        wy = gy - 4
                else:
                    wx, wy = gx - 15 + i * 10, gy - 4
                    if t - st["flip"] < 0.4 and st.get("fi") == i:
                        wy -= math.sin((t - st["flip"]) / 0.4 * math.pi) * 18
                st["brown"][i] = min(1.0, st["brown"][i] + dt * 0.01 * (1 if playing else 0))
                b = st["brown"][i]
                col = (int(220 - 100 * b), int(130 - 70 * b), int(90 - 50 * b))
                self._blob(img, wx, wy, 6, 16, col, ang=0.3 if i % 2 else -0.3, gloss=0.5)
            if playing and not boom:                                                # Rauch auf Schläge
                for k in range(3):
                    sy = gy - 12 - ((t * 24 + k * 14) % 42)
                    self._blob(img, gx + math.sin(t * 2 + k) * 8, sy, 14 + k * 3, 10, (200, 200, 205),
                               alpha=round(0.35 * (1 - (gy - 12 - sy) / 42), 2), flat=True)
            if boom:
                k = min(1.0, bt * 3, (FA_BOOM - bt) * 2)
                for i in range(5):
                    fx = gx - 16 + i * 8
                    hh = (30 + 20 * abs(math.sin(t * 13 + i * 2))) * k
                    d.polygon([(fx - 6, gy - 2), (fx + 6, gy - 2), (fx + math.sin(t * 9 + i) * 4, gy - 2 - hh)],
                              fill=(255, 130, 30))
                    d.polygon([(fx - 3, gy - 2), (fx + 3, gy - 2), (fx, gy - 2 - hh * 0.6)], fill=(255, 230, 90))
        # Figuren
        sway = math.sin(t * math.pi / period) if playing else 0.0
        if gname == "ballett":
            self._fa_gag_ballet(img, d, gl, t, say, bang)
        else:
            chef_pose = {"lh": (8, 20), "rh": (gx - FA_CHEF - 30, gy - FA_FLOOR + 50 - bang * 6)}
            smoke = 1.0 if boom and bt > 0.8 else 0.0
            sit = talk
            if sit:
                chef_pose = {"lh": (8, 18), "rh": (-6, 18)}
            head, hands = self._fa_man(img, d, FA_CHEF + (20 if sit else 0), FA_FLOOR, t, FA_SHIRTS[0], chef_pose,
                                       apron=True, lean=-0.3 * bang if playing else 0.0, smoke=smoke, sit=False)
            if not sit:                                                             # Grillzange
                hx, hy = hands[1]
                d.line([(hx, hy), (hx + 20, hy + 4)], fill=(170, 170, 176), width=2)
                d.line([(hx, hy), (hx + 20, hy + 1 - 2 * bang)], fill=(170, 170, 176), width=2)
            if boom and 1.0 < bt < 3.4:
                say.append((head[0] + 10, head[1] - 26, "Medium!"))
            for i, px in enumerate(FA_PALS):
                if gname == "tour" and gl < 6.0 and i == 1:
                    px = px + min(1.0, max(0.0, gl - 1.0) / 2.0) * 80                # rennt dem Wagen nach
                if gname == "zollstock" and i == 0:
                    pose = {"lh": (-16, 0), "rh": (16, -2), "lf": (-6, 36), "rf": (6, 36)}
                elif talk:
                    pose = {"lh": (-4, 16), "rh": (10, -6) if i == 0 else (6, 18)}
                else:
                    up = (st["k"] + i) % 2
                    pose = {"lh": (-12, -18 if up and level > 0.5 else 14), "rh": (12, -18 if up and level > 0.5 else 14),
                            "lf": (-6 + sway * 3, 36), "rf": (6 + sway * 3, 36)}
                if talk:
                    head2, hands2 = self._fa_man(img, d, FA_CART - 14 + i * 26, FA_FLOOR - 18, t, FA_SHIRTS[1 + i],
                                                 pose, sit=True)
                    if i == 0:                                                      # Landkarte
                        hx, hy = hands2[1]
                        d.polygon([(hx - 14, hy - 14), (hx + 6, hy - 18), (hx + 8, hy), (hx - 12, hy + 4)],
                                  fill=(240, 236, 210), outline=(150, 140, 110))
                        d.line([(hx - 10, hy - 8), (hx + 4, hy - 12)], fill=(200, 60, 60))
                        tl = t - s.get("talk_t", t)
                        if tl < 4.0:
                            say.append((head2[0], head2[1] - 26, "Wo sind wir eigentlich?"))
                    continue
                head2, hands2 = self._fa_man(img, d, px + sway * 4, FA_FLOOR, t, FA_SHIRTS[1 + i], pose,
                                             lean=sway * 0.4)
                if gname == "zollstock" and i == 0:
                    self._fa_gag_rule(img, d, gl, t, say, head2, hands2)
            if gname == "tour":
                if 1.0 <= gl < 3.2:
                    say.append((FA_PALS[1] + 40, FA_FLOOR - 104, "Der Wagen!"))
                elif 6.4 <= gl < 8.6:
                    say.append((cx, FA_FLOOR - 70, "Schnatter!"))
        if gname == "regen":
            self._fa_gag_rain(img, d, gl, t, say)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_ember = (255, int(60 + 120 * glow), 10)
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _fa_gag_ballet(self, img, d, gl, t, say, bang):
        """Baumarkt-Ballett: Drei Männer in Reihe – Akkuschrauber, Zollstock, Wasserwaage – Arabesque im Takt."""
        ph = int(gl * 2) % 4
        for i, x in enumerate((70, 150, 230)):
            k = min(1.0, gl / 0.8, max(0.0, (FA_GAGS["ballett"] - gl) / 0.8))
            if ph in (1, 3):                                                       # Arabesque
                pose = {"lh": (-22, -4), "rh": (8, -26), "lf": (0, 36), "rf": (26 * k, 10)}
            else:                                                                  # Pirouette, Arme gerundet
                pose = {"lh": (6, -24), "rh": (-6, -24), "lf": (-2, 36), "rf": (6, 24 - 8 * k)}
            lean = -0.3 * k if ph in (1, 3) else 0.0
            head, hands = self._fa_man(img, d, x, FA_FLOOR - 2 * bang, t, FA_SHIRTS[i], pose, lean=lean)
            d.polygon([(x - 18, FA_FLOOR - 36), (x + 18, FA_FLOOR - 36), (x + 8, FA_FLOOR - 44),
                       (x - 8, FA_FLOOR - 44)], fill=(250, 170, 200))              # Tutu
            hx, hy = hands[1]
            if i == 0:                                                             # Akkuschrauber
                d.rectangle([hx - 3, hy - 4, hx + 9, hy + 2], fill=(40, 130, 200))
                d.rectangle([hx - 2, hy + 2, hx + 2, hy + 9], fill=(40, 40, 44))
                d.line([(hx + 9, hy - 1), (hx + 15, hy - 1)], fill=(180, 180, 190), width=2)
                if int(t * 10) % 2:
                    d.line([(hx + 16, hy - 4), (hx + 19, hy + 2)], fill=(250, 250, 250))
            elif i == 1:                                                           # Zollstock
                pts = [(hx, hy)]
                for k2 in range(5):
                    a = math.sin(t * 4 + k2) * 0.6 + k2 * 0.4
                    pts.append((pts[-1][0] + math.cos(a) * 9, pts[-1][1] - math.sin(a) * 9))
                d.line(pts, fill=(250, 220, 60), width=3)
            else:                                                                  # Wasserwaage
                d.rectangle([hx - 16, hy - 3, hx + 16, hy + 2], fill=(220, 60, 50))
                d.rectangle([hx - 3, hy - 2, hx + 3, hy + 1], fill=(170, 230, 120))
        if 0.6 <= gl < 3.0:
            say.append((150, FA_FLOOR - 110, "Und eins – und zwei …"))
        elif 6.0 <= gl < 8.4:
            say.append((230, FA_FLOOR - 110, "Wasserwaage sagt: gerade!"))

    def _fa_gag_rain(self, img, d, gl, t, say):
        """Eine kleine Regenwolke nur über dem Grill; der Deckel geht zu, der Grillmeister nimmt es gelassen."""
        gx, gy = FA_GRILL
        k = min(1.0, gl / 1.2, max(0.0, (FA_GAGS["regen"] - gl) / 1.0))
        cx, cy = gx - 10 + math.sin(t * 0.8) * 6, 40 + (1 - k) * -40
        for i in range(4):
            self._blob(img, cx - 24 + i * 16, cy - (i % 2) * 6, 30, 22, (120, 124, 136), gloss=0.2)
        if gl > 1.2:
            for i in range(14):
                rx = cx - 30 + (i * 37 % 60)
                ry = cy + 10 + ((t * 160 + i * 23) % (FA_FLOOR - cy - 10))
                d.line([(rx, ry), (rx - 1, ry + 5)], fill=(150, 180, 240))
        if 2.4 <= gl < 4.6:
            say.append((FA_CHEF + 10, FA_FLOOR - 104, "Typisch Männertag."))
        elif 4.6 <= gl < 6.8:
            say.append((FA_PALS[0], FA_FLOOR - 104, "Hier scheint die Sonne!"))

    def _fa_gag_rule(self, img, d, gl, t, say, head, hands):
        """Der Zollstock lässt sich nicht zusammenfalten – er wird zum Zickzack."""
        (lx, ly), (rx, ry) = hands
        n = 8
        pts = []
        for k in range(n + 1):
            f = k / n
            zz = (6 + 10 * min(1.0, gl / 3.0)) * (1 if k % 2 else -1) * math.sin(min(1.0, gl / 2.0) * math.pi / 2)
            pts.append((lx + (rx - lx) * f, ly + (ry - ly) * f + zz))
        d.line(pts, fill=(250, 220, 60), width=3)
        for p in pts:
            d.ellipse([p[0] - 1.5, p[1] - 1.5, p[0] + 1.5, p[1] + 1.5], fill=(160, 120, 40))
        if 1.0 <= gl < 3.6:
            say.append((head[0], head[1] - 26, "Moment … der geht so …"))
        elif 3.6 <= gl < 6.4:
            say.append((head[0], head[1] - 26, "Ist der kaputt?"))
