"""Visualisierung „Katzenchor“ (cats, Mixin CatsVisual): Vier Katzen singen bei Vollmond auf dem Dach – jede Katze
ein Frequenzband, das Maul geht mit, die Schwänze wippen im Takt, eine dirigiert mit dem Schwanz. Höhepunkt: Der
hohe Ton – MIAUUU! –, das Fell sträubt sich, der Mond wackelt. Wortbeitrag: Die Katzen putzen sich. Gags: Ein Fenster
geht auf („Ruhe da oben!“) und ein Schuh fliegt, der Hund unten bellt (Katzenbuckel), der Mond singt mit, eine
Gräte an der Angel.
"""
import math
import random

KC_ROOF_Y = VIS_H - 70                  # First des Daches
KC_CATS = [(70, (40, 40, 44)), (122, (230, 140, 60)), (178, (240, 240, 240)), (230, (140, 140, 150))]
KC_GAGS = {"schuh": 8.0, "hund": 7.0, "mond": 8.0, "graete": 7.0}
KC_GAG_FIRST, KC_GAG_PAUSE = 8.0, (12.0, 20.0)
KC_BOOM = 3.5


class CatsVisual:
    vis_col_cats = None

    def _kc_scene(self):
        if "_kc_bg" in self.__dict__:
            return self._kc_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([10, 14, 40], np.float32), np.array([50, 40, 90], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(22)
        for _ in range(50):
            d.point((rng.uniform(0, WIDTH), rng.uniform(0, 100)), fill=(200, 200, 230))
        for x in range(0, WIDTH, 40):                                               # Nachbardächer
            h = rng.randint(30, 60)
            d.polygon([(x - 6, VIS_H - 40 - h + 20), (x + 20, VIS_H - 60 - h), (x + 46, VIS_H - 40 - h + 20),
                       (x + 46, VIS_H), (x - 6, VIS_H)], fill=(24, 22, 40))
        d.polygon([(-10, VIS_H + 10), (-10, KC_ROOF_Y + 6), (WIDTH + 10, KC_ROOF_Y + 6), (WIDTH + 10, VIS_H + 10)],
                  fill=(120, 50, 40))                                               # das Dach
        for y in range(KC_ROOF_Y + 10, VIS_H + 10, 8):
            for x in range(-10 + (y // 8 % 2) * 8, WIDTH + 10, 16):
                d.chord([x, y - 4, x + 16, y + 6], 0, 180, fill=(140, 60, 46), outline=(100, 40, 32))
        d.rectangle([-10, KC_ROOF_Y, WIDTH + 10, KC_ROOF_Y + 6], fill=(90, 40, 32))
        d.rectangle([270, KC_ROOF_Y - 40, 296, KC_ROOF_Y + 6], fill=(140, 70, 50))   # Schornstein
        for y in range(KC_ROOF_Y - 36, KC_ROOF_Y, 7):
            d.line([(270, y), (296, y)], fill=(110, 50, 36))
        d.rectangle([266, KC_ROOF_Y - 44, 300, KC_ROOF_Y - 38], fill=(110, 50, 36))
        d.rectangle([20, KC_ROOF_Y + 30, 52, KC_ROOF_Y + 58], fill=(40, 30, 30), outline=(200, 190, 170), width=3)
        self._kc_bg = img
        return img

    def _kc_cat(self, img, d, x, y, t, col, mouth, tail, puff=0.0, lick=False, hiss=False, look=0.0):
        """Sitzende Katze; y = Pfoten auf dem First."""
        s = 1 + puff * 0.25
        self._blob(img, x, y - 14, 24 * s, 26 * s, col, gloss=0.3)
        ta = -math.pi / 2 + tail
        pts = [(x + 10, y - 4)]
        for j in range(1, 6):
            a = ta + j * 0.18 * (1 if tail >= 0 else -1)
            pts.append((pts[-1][0] + math.cos(a) * 6, pts[-1][1] + math.sin(a) * 6))
        d.line(pts, fill=col, width=int(4 + 3 * puff))
        hx, hy = x + look * 2, y - 32
        self._blob(img, hx, hy, 20 * s, 18 * s, col, gloss=0.3)
        for side in (-1, 1):
            d.polygon([(hx + side * 4, hy - 7), (hx + side * 10, hy - 14 - puff * 2), (hx + side * 9, hy - 3)], fill=col)
            d.polygon([(hx + side * 5, hy - 7), (hx + side * 9, hy - 11), (hx + side * 8, hy - 5)], fill=(240, 160, 170))
            if lick:
                d.arc([hx + side * 4 - 3, hy - 4, hx + side * 4 + 3, hy + 1], 200, 340, fill=(30, 30, 30))
            else:
                d.ellipse([hx + side * 4 - 3, hy - 5, hx + side * 4 + 3, hy + 1], fill=(250, 220, 60))
                d.ellipse([hx + side * 4 - 0.8 + look, hy - 4.5, hx + side * 4 + 0.8 + look, hy + 0.5], fill=(10, 10, 10))
            for k in (-1, 1):
                d.line([(hx + side * 3, hy + 3), (hx + side * 12, hy + 2 + k * 2)], fill=(220, 220, 220))
        d.polygon([(hx - 1.5, hy + 1), (hx + 1.5, hy + 1), (hx, hy + 2.5)], fill=(240, 130, 150))
        if mouth > 0.1 or hiss:
            mh = 2 + mouth * 6
            d.ellipse([hx - 3, hy + 3, hx + 3, hy + 3 + mh], fill=(120, 30, 40))
            if hiss:
                d.line([(hx - 2, hy + 3), (hx - 2, hy + 6)], fill=(250, 250, 250))
                d.line([(hx + 2, hy + 3), (hx + 2, hy + 6)], fill=(250, 250, 250))
        if lick:
            self._blob(img, hx + 6, hy + 8, 6, 8, col, gloss=0.3)
            d.ellipse([hx + 1, hy + 4, hx + 4, hy + 7], fill=(240, 120, 140))
        if puff:
            for k in range(10):
                a = k * 0.63
                d.line([(x + math.cos(a) * 12 * s, y - 14 + math.sin(a) * 13 * s),
                        (x + math.cos(a) * 16 * s, y - 14 + math.sin(a) * 17 * s)], fill=col, width=2)
        return (hx, hy)

    @vis_style("cats")
    def vis_cats(self, s, o, color):
        t = s["t"]
        img = self._kc_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("cats", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                            "boom": -99.0, "gag": None, "order": [], "k": 0,
                                            "next_gag": t + KC_GAG_FIRST, "rng": random.Random(191), "start": t})
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
        boom = 0 <= bt < KC_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= KC_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*KC_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(KC_GAGS), len(KC_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["k"] += 1
        say = []
        bands = s.get("bands")
        if bands is None or len(bands) == 0:
            bands = [level] * 8
        # Mond (singt beim Gag mit, wackelt beim Höhepunkt)
        mx, my = 232 + (math.sin(t * 40) * 3 if boom else 0), 46
        self._blob(img, mx, my, 70, 70, (240, 230, 190), alpha=0.18, flat=True)
        self._blob(img, mx, my, 44, 44, (245, 240, 210), gloss=0.15)
        if gname == "mond" or boom:
            for side in (-1, 1):
                d.ellipse([mx + side * 8 - 3, my - 8, mx + side * 8 + 3, my - 2], fill=(90, 80, 60))
            mo = (0.5 + 0.5 * abs(math.sin(t * 7))) if gname == "mond" else 1.0
            d.ellipse([mx - 6, my + 4, mx + 6, my + 6 + 8 * mo], fill=(110, 60, 60))
            if gname == "mond" and 1.0 <= gl < 4.0:
                say.append((mx, my - 30, "Ich sing mit! Uuuuh!"))
            elif gname == "mond" and gl >= 4.6:
                say.append((KC_CATS[0][0], KC_ROOF_Y - 70, "Der Mond ist zu tief."))
        else:
            for ox, oy, r in ((-8, -6, 5), (6, 6, 4)):
                d.ellipse([mx + ox - r, my + oy - r, mx + ox + r, my + oy + r], fill=(228, 220, 190))
        # Die Katzen
        heads = []
        dog = gname == "hund" and 1.5 <= gl < 6.0
        for i, (cx, col) in enumerate(KC_CATS):
            b = bands[min(len(bands) - 1, i * len(bands) // len(KC_CATS))] if playing else 0.0
            mouth = min(1.0, b * 1.6)
            tail = math.sin(t * math.pi / period + i) * 0.6 if playing else 0.2
            if i == 0 and playing:                                                  # die Dirigentin
                tail = math.sin(t * math.pi / period * 2) * 1.2
                mouth = 0.0
            puff = 1.0 if (boom and 0.3 < bt < 2.6) or dog else 0.0
            if boom:
                mouth = 1.0
            duck = 0.0
            if gname == "schuh" and i == 2 and 3.0 <= gl < 4.2:
                duck = 12
            hc = self._kc_cat(img, d, cx, KC_ROOF_Y + duck, t, col, mouth if not talk else 0.0, tail, puff,
                              lick=talk and i % 2 == 0, hiss=dog, look=1.0 if dog else 0.0)
            heads.append(hc)
            if playing and mouth > 0.4 and not boom:
                d.text((hc[0] + 8, hc[1] - 22 - (t * 10 + i * 5) % 10), "♪", font=self.f_tiny, fill=(240, 230, 180))
        if boom and 0.3 < bt < 2.8:
            f2 = load_font(30, bold=True)
            d.text((86, 40), "MIAUUU!", font=f2, fill=(255, 240, 180))
        if talk:
            tl = t - s.get("talk_t", t)
            if tl < 3.0:
                say.append((heads[1][0], heads[1][1] - 22, "Pause. Miau."))
        if gname == "schuh":
            wx, wy = 36, KC_ROOF_Y + 44
            if gl > 0.5:
                d.rectangle([22, KC_ROOF_Y + 32, 50, KC_ROOF_Y + 56], fill=(250, 220, 130))
                self._fig(img, d, wx, KC_ROOF_Y + 76, t, (200, 200, 230), {"lh": (-10, -8), "rh": (14, -20)}, h=0.6,
                          hair=(80, 60, 40), hat="beanie", hat_col=(240, 240, 250))
            if 0.8 <= gl < 2.8:
                say.append((wx + 30, wy - 14, "Ruhe da oben!"))
            if 2.6 <= gl < 4.4:
                k = (gl - 2.6) / 1.8
                sx = wx + k * 200
                sy = wy - math.sin(k * math.pi) * 80
                d.polygon([(sx - 6, sy), (sx + 8, sy), (sx + 8, sy - 4), (sx, sy - 6), (sx - 6, sy - 4)], fill=(90, 60, 40))
            if 4.6 <= gl < 7.0:
                say.append((heads[2][0], heads[2][1] - 22, "Daneben! Zugabe!"))
        elif gname == "hund":
            dx_ = 160 + math.sin(gl * 6) * 4
            self._blob(img, dx_, VIS_H - 6, 30, 20, (160, 110, 60), gloss=0.4)
            self._blob(img, dx_ - 14, VIS_H - 18, 18, 14, (160, 110, 60), gloss=0.4)
            for side in (-1, 1):
                d.ellipse([dx_ - 14 + side * 4 - 1.5, VIS_H - 22, dx_ - 14 + side * 4 + 1.5, VIS_H - 19], fill=(20, 20, 20))
            if 1.0 <= gl < 4.0:
                say.append((dx_ - 20, VIS_H - 34, "WAU! WAU!"))
            elif gl >= 4.4:
                say.append((heads[1][0], heads[1][1] - 22, "Fffffft!"))
        elif gname == "graete":
            k = min(1.0, gl / 2.0)
            gx, gy = 100 + math.sin(gl * 2) * 30, 20 + k * 50
            d.line([(gx, 0), (gx, gy)], fill=(200, 200, 210))
            d.line([(gx - 12, gy + 4), (gx + 12, gy + 4)], fill=(250, 250, 250), width=2)
            for j in range(5):
                d.line([(gx - 8 + j * 4, gy), (gx - 8 + j * 4, gy + 8)], fill=(250, 250, 250))
            d.polygon([(gx + 12, gy + 4), (gx + 18, gy), (gx + 18, gy + 8)], fill=(250, 250, 250))
            if gl > 2.4:
                say.append((heads[3][0] - 20, heads[3][1] - 22, "Nur noch Gräte? Frechheit!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_col_cats = (250, 220, 60) if playing else (60, 60, 120)
        return img
