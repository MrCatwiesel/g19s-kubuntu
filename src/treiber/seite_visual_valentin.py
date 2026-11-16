"""Visualisierung „Valentinstag“ (valentine, Mixin ValentineVisual): Candle-Light-Dinner am Fenster über der Stadt.
Ein Paar sitzt am Tisch, der Geiger spielt (der Bogen streicht mit der Lautstärke), Herzen steigen auf hohe Schläge,
die Kerze flackert im Takt. Amor flattert herum und schießt auf den Bass – und trifft meistens daneben (Kellner,
Blumentopf, Geiger). Höhepunkt: Amor trifft endlich, Herzen explodieren, beide bekommen Herzaugen. Wortbeitrag: Der
Kellner bringt die Rechnung. Gags: Die Nudel reißt (Tomatensoße auf dem Geiger), der Ring fällt in die Suppe, der
Rosenverkäufer kommt immer wieder.
"""
import math
import random

VL_FLOOR = VIS_H - 20
VL_TABLE = (160, VL_FLOOR - 40)
VL_GAGS = {"nudel": 8.0, "ring": 9.0, "rosen": 8.0}
VL_GAG_FIRST, VL_GAG_PAUSE = 8.0, (12.0, 20.0)
VL_BOOM = 4.0
VL_MISS = ["Daneben!", "Ups, der Blumentopf.", "Huch – der Geiger!", "Mist."]


class ValentineVisual:
    vis_heart = None

    def _vl_scene(self):
        if "_vl_bg" in self.__dict__:
            return self._vl_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (120, 40, 60))
        d = ImageDraw.Draw(img)
        for x in range(0, WIDTH, 18):                                               # Tapete
            d.rectangle([x, 0, x + 8, VL_FLOOR], fill=(130, 46, 68))
        d.rectangle([60, 10, 260, 120], fill=(20, 26, 60))                           # großes Fenster
        rng = random.Random(4)
        for _ in range(30):
            d.point((rng.uniform(62, 258), rng.uniform(12, 70)), fill=(200, 200, 230))
        self._blob(img, 230, 34, 16, 16, (240, 236, 210), gloss=0.1)
        x = 60
        while x < 260:
            w, h = rng.randint(12, 24), rng.randint(14, 44)
            d.rectangle([x, 120 - h, min(260, x + w), 120], fill=(30, 30, 50))
            for wy in range(122 - h, 118, 6):
                for wx in range(x + 2, min(258, x + w - 2), 5):
                    if rng.random() < 0.3:
                        d.point((wx, wy), fill=(250, 220, 130))
            x += w
        d.rectangle([56, 6, 264, 124], outline=(200, 170, 120), width=4)
        d.line([(160, 6), (160, 124)], fill=(200, 170, 120), width=3)
        for cx in (40, 280):                                                        # Vorhänge
            d.polygon([(cx - 22, 0), (cx + 22, 0), (cx + 10, VL_FLOOR - 40), (cx - 10, VL_FLOOR - 40)], fill=(170, 30, 50))
        d.rectangle([0, VL_FLOOR, WIDTH, HEIGHT], fill=(90, 50, 40))
        for y in range(VL_FLOOR + 4, HEIGHT, 6):
            d.line([(0, y), (WIDTH, y)], fill=(76, 42, 34))
        x0, y0 = VL_TABLE                                                           # Tisch
        d.polygon([(x0 - 54, y0), (x0 + 54, y0), (x0 + 60, y0 + 30), (x0 - 60, y0 + 30)], fill=(250, 246, 240))
        d.line([(x0, y0 + 30), (x0, VL_FLOOR)], fill=(110, 80, 50), width=4)
        self._blob(img, 22, VL_FLOOR - 14, 22, 26, (180, 100, 70), gloss=0.4)       # Blumentopf
        for k in range(4):
            self._blob(img, 14 + k * 6, VL_FLOOR - 34 - (k % 2) * 6, 10, 10, (70, 150, 60), gloss=0.3)
        self._vl_bg = img
        return img

    @staticmethod
    def _vl_heart(d, x, y, r, col):
        d.ellipse([x - r, y - r, x, y], fill=col)
        d.ellipse([x, y - r, x + r, y], fill=col)
        d.polygon([(x - r, y - r / 2), (x + r, y - r / 2), (x, y + r)], fill=col)

    @vis_style("valentine")
    def vis_valentine(self, s, o, color):
        t = s["t"]
        img = self._vl_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("valentine", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                                 "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                                 "next_gag": t + VL_GAG_FIRST, "rng": random.Random(121),
                                                 "start": t, "hearts": [], "arrow": None, "miss": ""})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
        playing = (s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < VL_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= VL_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*VL_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(VL_GAGS), len(VL_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        rng = st["rng"]
        say = []
        if playing and new_beat:
            st["k"] += 1
            if o.get("cupid", True) and s["bass"] > 0.55 and st["arrow"] is None and not boom and rng.random() < 0.35:
                tx, ty = rng.choice([(22, VL_FLOOR - 30), (270, VL_FLOOR - 70), (40, VL_FLOOR - 90)])
                st["arrow"] = [t, tx, ty]
                st["miss"] = rng.choice(VL_MISS)
        if playing and new_hat and len(st["hearts"]) < 7 and rng.random() < 0.5:
            st["hearts"].append([VL_TABLE[0] + rng.uniform(-40, 40), VL_TABLE[1] - 10, rng.uniform(-8, 8), 0.0])
        x0, y0 = VL_TABLE
        # Paar am Tisch
        hearts_eyes = boom and bt > 0.8
        for side, shirt, hair, dress in ((-1, (40, 40, 60), (60, 40, 30), None), (1, (200, 40, 70), (180, 110, 50),
                                                                                    (200, 40, 70))):
            px = x0 + side * 52
            pose = {"lh": (8 * -side if side > 0 else 10, 6), "rh": (-10 if side > 0 else 10, 6)}
            if gname == "nudel" and gl < 4.0:
                pose = {"lh": (-side * 10, 2), "rh": (-side * 10, 2)}
            hc, hands = self._fig(img, d, px, VL_FLOOR, t, shirt, pose, h=0.95, sit=True, hair=hair, dress=dress,
                                  mouth=0.0, eyes="closed" if (playing and level > 0.6) else "dot", face=-side)
            if side < 0:
                d.rectangle([px - 6, VL_FLOOR - 22, px + 22, VL_FLOOR - 18], fill=(110, 70, 40))   # Stühle
            if hearts_eyes:
                for e in (-1, 1):
                    self._vl_heart(d, hc[0] + e * 3.5 + 1, hc[1] - 1, 3, (240, 30, 60))
        d.polygon([(x0 - 54, y0), (x0 + 54, y0), (x0 + 60, y0 + 30), (x0 - 60, y0 + 30)], fill=(250, 246, 240))
        for side in (-1, 1):                                                        # Teller und Gläser
            d.ellipse([x0 + side * 30 - 12, y0 + 4, x0 + side * 30 + 12, y0 + 12], fill=(255, 255, 255), outline=(200, 200, 210))
            d.polygon([(x0 + side * 14 - 3, y0 - 10), (x0 + side * 14 + 3, y0 - 10), (x0 + side * 14 + 1, y0 - 2),
                       (x0 + side * 14 - 1, y0 - 2)], fill=(180, 30, 50))
            d.line([(x0 + side * 14, y0 - 2), (x0 + side * 14, y0 + 4)], fill=(220, 220, 230))
        fl = 1 + 0.4 * math.sin(t * 17) * (0.3 + level)                             # Kerze
        d.rectangle([x0 - 2, y0 - 16, x0 + 2, y0 + 2], fill=(250, 246, 230))
        self._blob(img, x0, y0 - 22, 40 * fl, 36 * fl, (255, 200, 120), alpha=0.25, flat=True)
        d.polygon([(x0 - 2.5, y0 - 17), (x0 + 2.5, y0 - 17), (x0, y0 - 17 - 8 * fl)], fill=(255, 190, 60))
        # Geiger
        vx = 272
        bow = math.sin(t * 2 * math.pi / period * 0.5) * (6 + 10 * level) if playing else 0
        sauce = gname == "nudel" and gl >= 4.0
        hc, hands = self._fig(img, d, vx, VL_FLOOR, t, (30, 30, 34) if not sauce else (200, 60, 40),
                              {"lh": (-12, -12), "rh": (8 + bow, -2)}, h=0.95, hat=None, hair=(40, 30, 30),
                              beard=(40, 30, 30), eyes="closed" if playing else "dot")
        lx, ly = hands[0]
        d.polygon([(lx - 2, ly), (lx + 14, ly + 10), (lx + 12, ly + 14), (lx - 4, ly + 4)], fill=(150, 80, 30))
        rx, ry = hands[1]
        d.line([(rx - 16, ry + 6), (rx + 10, ry - 4)], fill=(220, 210, 180), width=1)
        if playing:
            for k in range(2):
                ny = hc[1] - 10 - ((t * 20 + k * 12) % 26)
                d.text((hc[0] + 10 + k * 8, ny), "♪", font=self.f_small_b, fill=(250, 220, 160))
        if sauce:
            for k in range(6):
                d.ellipse([hc[0] - 8 + k * 3, hc[1] + 6 + (k % 3) * 6, hc[0] - 4 + k * 3, hc[1] + 10 + (k % 3) * 6],
                          fill=(220, 40, 30))
            if gl < 6.6:
                say.append((hc[0], hc[1] - 26, "Mein Frack!"))
        # Herzen steigen
        for h in st["hearts"]:
            h[0] += h[2] * dt + math.sin(t * 3 + h[1]) * 0.3
            h[1] -= 24 * dt
            h[3] += dt
        st["hearts"] = [h for h in st["hearts"] if h[1] > 0]
        for h in st["hearts"]:
            self._vl_heart(d, h[0], h[1], 3 + min(3.0, h[3] * 2), (250, 80, 120))
        if boom:
            for k in range(14):
                a = k * 0.45 + bt * 2
                r = bt * 70
                self._vl_heart(d, x0 + math.cos(a) * r, y0 - 40 + math.sin(a) * r * 0.6, 5, (250, 60, 100))
            if 0.6 < bt < 3.2:
                say.append((x0, 40, "Volltreffer!"))
        # Amor
        if o.get("cupid", True):
            ax = 30 + 40 * math.sin(t * 0.7) + (x0 - 70 if boom else 0)
            ay = 60 + 12 * math.sin(t * 1.9)
            self._blob(img, ax, ay, 16, 18, (250, 210, 180), gloss=0.4)
            self._blob(img, ax, ay - 14, 12, 12, (250, 210, 180), gloss=0.4)
            d.chord([ax - 6, ay - 22, ax + 6, ay - 12], 180, 360, fill=(250, 220, 120))
            for side in (-1, 1):
                fl2 = math.sin(t * 20) * 4
                d.polygon([(ax + side * 4, ay - 4), (ax + side * 16, ay - 12 + fl2), (ax + side * 12, ay + 2)],
                          fill=(255, 255, 255))
            d.arc([ax + 4, ay - 12, ax + 16, ay + 8], 270, 90, fill=(160, 100, 40), width=2)
            if st["arrow"]:
                k = (t - st["arrow"][0]) / 0.6
                if k >= 1.6:
                    st["arrow"] = None
                else:
                    tx, ty = st["arrow"][1], st["arrow"][2]
                    kk = min(1.0, k)
                    px, py = ax + 16 + (tx - ax - 16) * kk, ay + (ty - ay) * kk - math.sin(kk * math.pi) * 20
                    d.line([(px - 10, py - 2), (px, py)], fill=(160, 100, 40), width=2)
                    self._vl_heart(d, px + 2, py, 2.5, (240, 30, 60))
                    if k >= 1.0:
                        say.append((tx, ty - 24, st["miss"]))
        if talk:
            tl = t - s.get("talk_t", t)
            wx = 30 + min(1.0, tl / 1.5) * 40
            hcw, hw = self._fig(img, d, wx, VL_FLOOR, t, (250, 250, 250), {"lh": (-6, 18), "rh": (16, -4)}, h=0.95,
                                hair=(30, 30, 30))
            d.rectangle([hw[1][0] - 2, hw[1][1] - 14, hw[1][0] + 12, hw[1][1] + 2], fill=(250, 250, 240),
                        outline=(160, 160, 160))
            if 1.0 < tl < 4.5:
                say.append((hcw[0] + 20, hcw[1] - 26, "Die Rechnung, die Herrschaften."))
            elif 4.5 <= tl < 7.5:
                say.append((x0 - 52, VL_FLOOR - 104, "Du lädst ein, oder?"))
        if gname == "nudel" and gl < 4.0:
            k = min(1.0, gl / 3.0)
            mid = (x0 + math.sin(gl * 3) * 4, y0 - 26 - 6 * k)
            d.line([(x0 - 46, y0 - 32), mid, (x0 + 46, y0 - 32)], fill=(240, 210, 120), width=2)
            if gl > 3.6:
                d.text((x0 - 10, y0 - 50), "SCHNAPP!", font=self.f_tiny, fill=(250, 250, 200))
            elif gl > 0.8:
                say.append((x0, y0 - 74, "Schlürf …"))
        elif gname == "ring":
            self._vl_gag_ring(img, d, gl, t, say)
        elif gname == "rosen":
            self._vl_gag_roses(img, d, gl, t, say)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_heart = (255, int(40 + 60 * level), int(90 + 40 * level))
        return img

    def _vl_gag_ring(self, img, d, gl, t, say):
        """Er holt den Ring heraus – der fällt in die Suppe, der Kellner fischt ihn mit der Kelle."""
        x0, y0 = VL_TABLE
        bx, by = x0 - 30, y0 - 10
        d.ellipse([x0 - 42, y0 + 2, x0 - 18, y0 + 10], fill=(230, 150, 60))          # Suppe
        if gl < 2.6:
            d.rectangle([bx - 5, by - 4, bx + 5, by + 4], fill=(150, 30, 40))
            if gl > 1.0:
                d.rectangle([bx - 5, by - 10, bx + 5, by - 4], fill=(150, 30, 40))
                d.ellipse([bx - 3, by - 6, bx + 3, by], outline=(250, 220, 80), width=2)
                say.append((x0 - 52, y0 - 64, "Ich wollte dich etwas fragen …"))
        elif gl < 3.4:
            k = (gl - 2.6) / 0.8
            d.ellipse([bx - 3, by - 6 + k * 18, bx + 3, by + k * 18], outline=(250, 220, 80), width=2)
            d.text((x0 - 40, y0 - 6), "plitsch", font=self.f_tiny, fill=(250, 240, 200))
        elif gl < 6.0:
            say.append((x0 + 52, y0 - 64, "Ist da … was in meiner Suppe?"))
        else:
            k = min(1.0, (gl - 6.0) / 1.0)
            wx = -20 + k * 80
            self._fig(img, d, wx, VL_FLOOR, t, (250, 250, 250), {"lh": (-6, 18), "rh": (20, -8)}, h=0.95, hair=(30, 30, 30))
            d.line([(wx + 22, VL_FLOOR - 66), (x0 - 30, y0 + 4)], fill=(190, 190, 200), width=2)
            if gl > 7.0:
                d.ellipse([x0 - 33, y0 - 12, x0 - 27, y0 - 6], outline=(250, 220, 80), width=2)
                say.append((x0, y0 - 74, "Ja! Ja! Ja!"))

    def _vl_gag_roses(self, img, d, gl, t, say):
        """Der Rosenverkäufer kommt – und kommt – und kommt wieder."""
        k = gl % 2.6
        rx = 330 - k / 2.6 * 380
        hc, hands = self._fig(img, d, rx, VL_FLOOR, t, (90, 140, 90), {"lh": (-14, -10), "rh": (8, 18),
                                                                       "lf": (-6 + 6 * math.sin(t * 9), 34),
                                                                       "rf": (6 - 6 * math.sin(t * 9), 34)}, h=0.95,
                              hat="cowboy", hat_col=(80, 60, 40))
        hx, hy = hands[0]
        for j in range(5):
            d.line([(hx, hy), (hx - 6 + j * 3, hy - 16)], fill=(70, 140, 60), width=1)
            self._blob(img, hx - 6 + j * 3, hy - 18, 5, 5, (220, 30, 50), gloss=0.4)
        n = int(gl / 2.6)
        say.append((hc[0], hc[1] - 26, ["Rose für die Dame?", "Rose? Ganz frisch!", "Letzte Chance!", "…"][min(3, n)]))
