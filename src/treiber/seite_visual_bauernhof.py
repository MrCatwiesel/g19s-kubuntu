"""Visualisierung „Bauernhof“ (farm, Mixin FarmVisual): Die Hofband vor der Scheune. Die Kuh spielt Bass (der Bass
lässt die Glocke bimmeln), das Schwein trommelt auf Milchkannen, drei Hühner auf dem Zaun sind der Chor, die
Vogelscheuche wippt mit. Höhepunkt: Der Traktor fährt mit Lichtorgel vor. Wortbeitrag: Der Bauer ruft zur Fütterung.
Gags: Der Fuchs schleicht sich an (und wird von den Hühnern verjagt), das Schwein springt in die Schlammpfütze
(die Kuh wird nass), ein Schaf zählt Menschen und schläft ein.
"""
import math
import random

FM_FLOOR = VIS_H - 20
FM_COW, FM_PIG = 100, 210
FM_HENS = (250, 274, 298)
FM_GAGS = {"fuchs": 8.0, "schlamm": 7.0, "schaf": 8.0}
FM_GAG_FIRST, FM_GAG_PAUSE = 8.0, (12.0, 20.0)
FM_BOOM = 5.0


class FarmVisual:
    vis_col_farm = None

    def _fm_scene(self):
        if "_fm_bg" in self.__dict__:
            return self._fm_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([120, 180, 240], np.float32), np.array([220, 236, 250], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        self._blob(img, 290, 26, 24, 24, (255, 240, 150), gloss=0.1)
        d.polygon([(0, FM_FLOOR - 40), (140, FM_FLOOR - 60), (320, FM_FLOOR - 44), (320, HEIGHT), (0, HEIGHT)],
                  fill=(130, 190, 90))
        d.rectangle([0, FM_FLOOR - 10, WIDTH, HEIGHT], fill=(120, 176, 80))
        bx0, bx1 = 120, 236                                                         # Scheune
        d.rectangle([bx0, FM_FLOOR - 96, bx1, FM_FLOOR - 10], fill=(180, 50, 40))
        d.polygon([(bx0 - 8, FM_FLOOR - 96), (bx1 + 8, FM_FLOOR - 96), ((bx0 + bx1) / 2, FM_FLOOR - 140)],
                  fill=(120, 40, 30))
        for x in range(bx0 + 6, bx1, 10):
            d.line([(x, FM_FLOOR - 94), (x, FM_FLOOR - 10)], fill=(150, 40, 32))
        d.rectangle([158, FM_FLOOR - 70, 198, FM_FLOOR - 10], fill=(110, 36, 28), outline=(250, 250, 240), width=3)
        d.line([(158, FM_FLOOR - 70), (198, FM_FLOOR - 10)], fill=(250, 250, 240), width=3)
        d.line([(198, FM_FLOOR - 70), (158, FM_FLOOR - 10)], fill=(250, 250, 240), width=3)
        d.ellipse([170, FM_FLOOR - 124, 186, FM_FLOOR - 108], fill=(250, 250, 240))
        for x in range(240, WIDTH, 14):                                             # Zaun
            d.rectangle([x, FM_FLOOR - 30, x + 4, FM_FLOOR - 6], fill=(170, 130, 80))
        d.rectangle([240, FM_FLOOR - 26, WIDTH, FM_FLOOR - 22], fill=(170, 130, 80))
        for x, y in ((20, FM_FLOOR - 22), (44, FM_FLOOR - 16)):                     # Strohballen
            d.rounded_rectangle([x - 16, y - 14, x + 16, y + 6], radius=4, fill=(230, 200, 100), outline=(190, 160, 70))
        self._fm_bg = img
        return img

    def _fm_cow(self, img, d, x, y, t, bang, wet=0.0, pluck=0.0):
        white, spot = (250, 250, 246), (40, 36, 40)
        self._blob(img, x, y - 40, 34, 46, white, gloss=0.3)
        for ox, oy, r in ((-6, -50, 6), (8, -36, 5), (-4, -26, 4)):
            d.ellipse([x + ox - r, y + oy - r, x + ox + r, y + oy + r], fill=spot)
        for side in (-1, 1):
            self._limb(img, (x + side * 7, y - 20), (x + side * 8, y), 7, white)
            d.ellipse([x + side * 8 - 4, y - 3, x + side * 8 + 4, y + 1], fill=spot)
        hy = y - 74 + bang * 3
        self._blob(img, x, hy, 28, 26, white, gloss=0.3)
        self._blob(img, x, hy + 10, 22, 12, (250, 190, 190), gloss=0.3)
        for side in (-1, 1):
            d.line([(x + side * 10, hy - 10), (x + side * 16, hy - 18)], fill=(230, 220, 190), width=3)
            self._blob(img, x + side * 16, hy - 4, 10, 6, white, gloss=0.2)
            d.ellipse([x + side * 6 - 2, hy - 4, x + side * 6 + 2, hy], fill=(20, 20, 20))
            d.ellipse([x + side * 4 - 1, hy + 9, x + side * 4 + 1, hy + 11], fill=(150, 80, 80))
        bell = y - 60
        d.polygon([(x - 4, bell), (x + 4, bell), (x + 6, bell + 8), (x - 6, bell + 8)], fill=(230, 190, 60))
        if bang > 0.6:
            d.text((x + 8, bell), "bim", font=self.f_tiny, fill=(120, 90, 20))
        gx, gy = x + 4, y - 40                                                      # Bassgitarre
        d.line([(gx - 22, gy + 12), (gx + 30, gy - 24)], fill=(110, 70, 40), width=4)
        self._blob(img, gx - 14, gy + 8, 22, 16, (180, 60, 40), gloss=0.5, ang=-0.6)
        for k in range(2):
            d.line([(gx - 18 + k * 2, gy + 10), (gx + 30 + k * 2, gy - 22)], fill=(230, 230, 230))
        self._limb(img, (x - 10, y - 50), (gx - 8, gy + 4 - pluck * 4), 6, white)
        self._limb(img, (x + 10, y - 50), (gx + 22, gy - 16), 6, white)
        if wet:
            for k in range(8):
                d.ellipse([x - 14 + k * 4, y - 60 + (k * 13 % 40), x - 10 + k * 4, y - 56 + (k * 13 % 40)],
                          fill=(110, 80, 50))

    def _fm_pig(self, img, d, x, y, t, k, hit, mud=0.0):
        pink = (250, 170, 180) if not mud else (130, 96, 60)
        self._blob(img, x, y - 26, 40, 30, pink, gloss=0.4)
        for side in (-1, 1):
            self._limb(img, (x + side * 10, y - 14), (x + side * 11, y), 6, pink)
        hx, hy = x, y - 50
        self._blob(img, hx, hy, 28, 24, pink, gloss=0.4)
        self._blob(img, hx, hy + 6, 12, 8, (240, 130, 150), gloss=0.4)
        for side in (-1, 1):
            d.polygon([(hx + side * 6, hy - 10), (hx + side * 14, hy - 16), (hx + side * 12, hy - 6)], fill=pink)
            d.ellipse([hx + side * 5 - 1.5, hy - 3, hx + side * 5 + 1.5, hy], fill=(20, 20, 20))
            d.ellipse([hx + side * 2 - 1, hy + 5, hx + side * 2 + 1, hy + 7], fill=(160, 70, 90))
        for side in (-1, 1):                                                        # Arme mit Stöcken
            down = hit == (side > 0)
            hand = (x + side * 24, y - (26 if down else 40))
            self._limb(img, (x + side * 12, y - 34), hand, 6, pink)
            d.line([hand, (hand[0] + side * 4, hand[1] - 12)], fill=(150, 110, 60), width=2)
        for side in (-1, 1):                                                        # Milchkannen
            cx = x + side * 30
            d.rectangle([cx - 7, y - 26, cx + 7, y], fill=(200, 205, 214), outline=(140, 145, 150))
            d.ellipse([cx - 8, y - 30, cx + 8, y - 24], fill=(220, 224, 230))
        d.arc([x + 16, y - 34, x + 26, y - 24], 180, 450, fill=(240, 130, 150), width=2)

    def _fm_hen(self, img, d, x, y, t, sing, face=-1):
        self._blob(img, x, y - 8, 18, 14, (250, 246, 236), gloss=0.4)
        self._blob(img, x + face * 7, y - 17, 10, 10, (250, 246, 236), gloss=0.4)
        d.polygon([(x + face * 11, y - 18), (x + face * (16 + 3 * sing), y - 17 - 2 * sing), (x + face * 11, y - 15)],
                  fill=(250, 170, 40))
        if sing > 0.3:
            d.polygon([(x + face * 11, y - 16), (x + face * (15 + 3 * sing), y - 13), (x + face * 11, y - 14)],
                      fill=(250, 170, 40))
        for k in range(3):
            d.ellipse([x + face * (5 + k * 2) - 2, y - 26 + abs(k - 1), x + face * (5 + k * 2) + 2, y - 22], fill=(220, 40, 40))
        d.point((x + face * 9, y - 19), fill=(20, 20, 20))

    @vis_style("farm")
    def vis_farm(self, s, o, color):
        t = s["t"]
        img = self._fm_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("farm", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                            "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                            "next_gag": t + FM_GAG_FIRST, "rng": random.Random(141), "start": t})
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
        boom = 0 <= bt < FM_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= FM_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*FM_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(FM_GAGS), len(FM_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["k"] += 1
        say = []
        # Vogelscheuche
        sx = 64
        sw = math.sin(t * math.pi / period) * 0.15 if playing else 0.0
        top = (sx + sw * 30, FM_FLOOR - 92)
        d.line([(sx, FM_FLOOR - 6), top], fill=(120, 80, 40), width=3)
        d.line([(top[0] - 22, top[1] + 20 + 6 * bang), (top[0] + 22, top[1] + 20 - 6 * bang)], fill=(120, 80, 40), width=3)
        d.polygon([(top[0] - 12, top[1] + 14), (top[0] + 12, top[1] + 14), (top[0] + 9, top[1] + 46),
                   (top[0] - 9, top[1] + 46)], fill=(90, 120, 200))
        self._blob(img, top[0], top[1] + 4, 16, 16, (230, 200, 130), gloss=0.2)
        d.ellipse([top[0] - 13, top[1] - 4, top[0] + 13, top[1] + 1], fill=(200, 160, 70))
        d.chord([top[0] - 8, top[1] - 14, top[0] + 8, top[1] + 1], 180, 360, fill=(200, 160, 70))
        for side in (-1, 1):
            d.line([(top[0] + side * 3 - 1.5, top[1] + 2), (top[0] + side * 3 + 1.5, top[1] + 5)], fill=(40, 30, 20))
            d.line([(top[0] + side * 3 + 1.5, top[1] + 2), (top[0] + side * 3 - 1.5, top[1] + 5)], fill=(40, 30, 20))
        # Traktor mit Lichtorgel (Höhepunkt)
        if boom:
            k = min(1.0, bt / 1.0, (FM_BOOM - bt) / 0.8)
            tx = WIDTH + 60 - k * 120
            d.rectangle([tx - 30, FM_FLOOR - 40, tx + 20, FM_FLOOR - 16], fill=(40, 140, 60))
            d.rectangle([tx - 30, FM_FLOOR - 66, tx - 6, FM_FLOOR - 40], outline=(40, 140, 60), width=3)
            d.ellipse([tx - 32, FM_FLOOR - 30, tx - 6, FM_FLOOR - 4], fill=(30, 30, 30))
            d.ellipse([tx + 6, FM_FLOOR - 20, tx + 22, FM_FLOOR - 4], fill=(30, 30, 30))
            for j in range(6):
                c = _hue((j / 6 + t * 2) % 1.0, 0.8, 1.0)
                d.ellipse([tx - 30 + j * 5, FM_FLOOR - 72, tx - 26 + j * 5, FM_FLOOR - 68], fill=c)
                beam = Image.new("L", img.size, 0)
                a = -math.pi / 2 + math.sin(t * 3 + j) * 1.0
                ImageDraw.Draw(beam).polygon([(tx - 28 + j * 5, FM_FLOOR - 70), (tx - 28 + j * 5 + math.cos(a - 0.1) * 200,
                                              FM_FLOOR - 70 + math.sin(a - 0.1) * 200),
                                              (tx - 28 + j * 5 + math.cos(a + 0.1) * 200, FM_FLOOR - 70 + math.sin(a + 0.1) * 200)],
                                             fill=50)
                img.paste(c, (0, 0), beam)
            d = ImageDraw.Draw(img)
            if 1.0 < bt < 3.6:
                say.append((tx - 10, FM_FLOOR - 92, "Tuuut! Party!"))
        # Kuh, Schwein, Hühner
        wet = gname == "schlamm" and gl > 3.0
        pluck = max(0.0, 1 - (t - s.get("beat_t", -9)) / 0.15) if playing else 0.0
        self._fm_cow(img, d, FM_COW, FM_FLOOR, t, bang, wet=wet, pluck=pluck)
        mud = gname == "schlamm" and gl > 2.6
        if gname == "schlamm":
            d.ellipse([FM_PIG - 40, FM_FLOOR - 4, FM_PIG + 40, FM_FLOOR + 8], fill=(110, 80, 50))
            jump = math.sin(min(1.0, max(0.0, gl - 1.6) / 1.0) * math.pi) * 40 if gl < 2.6 else 0
            self._fm_pig(img, d, FM_PIG, FM_FLOOR - jump, t, st["k"], False, mud=mud)
            if 2.6 <= gl < 3.2:
                for k in range(10):
                    a = -math.pi * (k / 9)
                    r = (gl - 2.6) * 120
                    d.ellipse([FM_PIG + math.cos(a) * r - 3, FM_FLOOR + math.sin(a) * r * 0.6 - 3,
                               FM_PIG + math.cos(a) * r + 3, FM_FLOOR + math.sin(a) * r * 0.6 + 3], fill=(110, 80, 50))
            if 0.6 <= gl < 2.4:
                say.append((FM_PIG, FM_FLOOR - 80, "Arschbombe!"))
            elif gl >= 3.6:
                say.append((FM_COW, FM_FLOOR - 100, "Muuuh! Danke auch."))
        else:
            self._fm_pig(img, d, FM_PIG, FM_FLOOR, t, st["k"], st["k"] % 2 == 0 and playing)
        fox = gname == "fuchs"
        for i, hx in enumerate(FM_HENS):
            sing = min(1.0, level * 1.5) * (0.5 + 0.5 * math.sin(t * 9 + i)) if playing else 0.0
            if fox and gl > 3.5:                                                    # Hühner verjagen den Fuchs
                hx2 = hx - (gl - 3.5) * 70 - i * 10
                hy = FM_FLOOR - 2 - abs(math.sin(t * 14 + i)) * 6
                self._fm_hen(img, d, hx2, hy, t, 1.0, face=-1)
            else:
                self._fm_hen(img, d, hx, FM_FLOOR - 28, t, sing)
        if playing and not gname and int(t / 2.5) % 3 == 0:
            say.append((FM_HENS[1], FM_FLOOR - 66, "Gack-gack-gaaack!"))
        if fox:
            fx = 330 - gl * 30 if gl < 3.5 else 225 - (gl - 3.5) * 90
            fy = FM_FLOOR
            col = (220, 110, 40)
            self._blob(img, fx, fy - 12, 30, 14, col, gloss=0.4)
            self._blob(img, fx - 16, fy - 18, 14, 12, col, gloss=0.4)
            d.polygon([(fx - 24, fy - 18), (fx - 30, fy - 16), (fx - 22, fy - 14)], fill=(40, 30, 30))
            for side in (-1, 1):
                d.polygon([(fx - 16 + side * 4, fy - 22), (fx - 16 + side * 6, fy - 30), (fx - 16 + side * 1, fy - 24)],
                          fill=col)
            d.line([(fx + 14, fy - 14), (fx + 28, fy - 22)], fill=col, width=5)
            d.ellipse([fx + 24, fy - 26, fx + 30, fy - 20], fill=(250, 250, 250))
            for k in (-8, -2, 6, 12):
                d.line([(fx + k, fy - 6), (fx + k + math.sin(t * 12 + k) * 3, fy)], fill=col, width=2)
            if 1.0 <= gl < 3.4:
                say.append((fx, fy - 40, "Psst … nur mal gucken."))
            elif gl >= 3.6:
                say.append((fx + 40, fy - 50, "Hilfe! Die sind ja wild!"))
        if gname == "schaf":
            shx, shy = 30, FM_FLOOR - 36
            self._blob(img, shx, shy, 30, 22, (250, 250, 250), gloss=0.2)
            for k in range(6):
                self._blob(img, shx - 12 + k * 5, shy - 8 + (k % 2) * 3, 10, 10, (250, 250, 250), gloss=0.2)
            self._blob(img, shx + 16, shy - 2, 10, 10, (60, 50, 50), gloss=0.3)
            n = min(3, int(gl / 1.4) + 1)
            if gl < 5.0:
                say.append((shx + 30, shy - 30, ["Ein Mensch …", "Zwei Menschen …", "Drei Mensch…"][n - 1]))
            else:
                for k in range(3):
                    zy = shy - 20 - ((gl * 14 + k * 10) % 30)
                    d.text((shx + 20 + k * 4, zy), "z", font=self.f_small_b, fill=(80, 80, 120))
        if talk:
            tl = t - s.get("talk_t", t)
            hc, hands = self._fig(img, d, 290, FM_FLOOR + 4, t, (60, 110, 190), {"lh": (-14, -16), "rh": (12, 10)},
                                  h=1.0, hat="cowboy", hat_col=(220, 190, 110), beard=(120, 90, 60), legs=(70, 90, 140))
            d.line([(hands[1][0], hands[1][1] - 30), (hands[1][0], hands[1][1] + 30)], fill=(140, 100, 60), width=2)
            for k in range(3):
                d.line([(hands[1][0] - 4 + k * 4, hands[1][1] - 30), (hands[1][0] - 4 + k * 4, hands[1][1] - 40)],
                       fill=(170, 170, 180), width=2)
            if tl < 3.5:
                say.append((hc[0] - 20, hc[1] - 30, "Fütterung! Alle mal herhören!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_col_farm = (255, 170, 180) if st["k"] % 2 else (120, 200, 90)
        return img
