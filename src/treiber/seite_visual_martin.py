"""Visualisierung „St. Martin“ (martin, Mixin MartinVisual): Laternenumzug durchs Dorf am Abend. St. Martin reitet
mit rotem Mantel voran, dahinter ziehen Kinder mit Laternen – jede Laterne leuchtet mit ihrem Frequenzband, hohe
Schläge lassen Funken aus dem Martinsfeuer steigen. Ein ruhiger Stil. Höhepunkt: Das Martinsfeuer lodert auf, alle
Laternen strahlen. Wortbeitrag: St. Martin teilt seinen Mantel. Gags: Die Gans flüchtet (und versteckt sich), eine
Laterne fängt Feuer, der Weckmann mit der Pfeife wird lebendig.
"""
import math
import random

SM_FLOOR = VIS_H - 26
SM_FIRE = 282
SM_GAGS = {"gans": 8.0, "laterne": 7.0, "weckmann": 7.0}
SM_GAG_FIRST, SM_GAG_PAUSE = 10.0, (14.0, 22.0)
SM_BOOM = 4.0
SM_PERIOD = 36.0                        # so lange braucht der Zug durchs Bild
SM_LANTERNS = [(250, 120, 60), (250, 200, 60), (240, 90, 150), (120, 200, 250), (180, 120, 250), (130, 220, 120)]


class MartinVisual:
    vis_lantern = None

    def _sm_scene(self):
        if "_sm_bg" in self.__dict__:
            return self._sm_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([14, 18, 50], np.float32), np.array([70, 60, 100], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(15)
        for _ in range(40):
            d.point((rng.uniform(0, WIDTH), rng.uniform(0, 90)), fill=(200, 200, 230))
        self._blob(img, 54, 34, 22, 22, (240, 236, 210), gloss=0.1)
        x = -10
        while x < WIDTH - 50:                                                       # Dorfhäuser
            w, h = rng.randint(36, 50), rng.randint(40, 60)
            d.rectangle([x, SM_FLOOR - 24 - h, x + w, SM_FLOOR - 20], fill=(46, 40, 60))
            d.polygon([(x - 4, SM_FLOOR - 24 - h), (x + w + 4, SM_FLOOR - 24 - h), (x + w / 2, SM_FLOOR - 50 - h)],
                      fill=(36, 30, 46))
            for wx in (x + 8, x + w - 16):
                if rng.random() < 0.7:
                    d.rectangle([wx, SM_FLOOR - 14 - h, wx + 8, SM_FLOOR - 4 - h], fill=(250, 200, 110))
            x += w + rng.randint(4, 10)
        d.polygon([(250, SM_FLOOR - 30), (262, SM_FLOOR - 120), (274, SM_FLOOR - 30)], fill=(40, 34, 50))  # Kirchturm
        d.rectangle([244, SM_FLOOR - 70, 280, SM_FLOOR - 20], fill=(46, 40, 60))
        d.line([(262, SM_FLOOR - 120), (262, SM_FLOOR - 132)], fill=(200, 180, 100), width=2)
        d.line([(257, SM_FLOOR - 127), (267, SM_FLOOR - 127)], fill=(200, 180, 100), width=2)
        d.rectangle([0, SM_FLOOR - 20, WIDTH, HEIGHT], fill=(50, 48, 56))
        for y in range(SM_FLOOR - 16, HEIGHT, 6):
            for xx in ((y // 6 % 2) * 6, ):
                for x2 in range(xx, WIDTH, 12):
                    d.rectangle([x2, y, x2 + 10, y + 4], outline=(60, 58, 66))
        self._sm_bg = img
        return img

    def _sm_lantern(self, img, d, x, y, col, glow, burn=0.0):
        """Papierlaterne am Stab; (x, y) = Hand."""
        lx, ly = x + 10, y - 22
        d.line([(x, y), (lx, ly - 10)], fill=(110, 80, 50), width=2)
        d.line([(lx, ly - 10), (lx, ly - 4)], fill=(160, 160, 160))
        if glow > 0.05:
            self._blob(img, lx, ly + 6, 34, 30, col, alpha=round(0.35 * glow, 2), flat=True)
        c = tuple(int(v * (0.45 + 0.55 * glow)) for v in col)
        if burn:
            c = (60, 40, 30)
        d.ellipse([lx - 8, ly - 4, lx + 8, ly + 16], fill=c, outline=(80, 60, 40))
        d.line([(lx - 8, ly + 6), (lx + 8, ly + 6)], fill=tuple(min(255, v + 40) for v in c))
        if burn:
            for k in range(3):
                hh = 10 + 8 * abs(math.sin(burn * 12 + k))
                d.polygon([(lx - 6 + k * 6, ly), (lx - 2 + k * 6, ly), (lx - 4 + k * 6, ly - hh)], fill=(255, 140, 30))

    @vis_style("martin")
    def vis_martin(self, s, o, color):
        t = s["t"]
        img = self._sm_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("martin", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                              "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                              "next_gag": t + SM_GAG_FIRST, "rng": random.Random(111), "start": t,
                                              "sparks": []})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
        playing = (s.get("active") or demo) and not talk
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < SM_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= SM_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*SM_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(SM_GAGS), len(SM_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["k"] += 1
        say = []
        bands = s.get("bands")
        if bands is None or len(bands) == 0:
            bands = [level] * 8
        # Martinsfeuer rechts
        fk = 0.5 + 0.5 * level + (0.8 if boom else 0)
        fx, fy = SM_FIRE, SM_FLOOR - 4
        for k in range(6):
            d.line([(fx - 16 + k * 6, fy), (fx - 4 + k * 3, fy - 10)], fill=(90, 60, 40), width=3)
        self._blob(img, fx, fy - 20, 70 * fk, 60 * fk, (255, 150, 60), alpha=0.3, flat=True)
        for k in range(5):
            hh = (18 + 14 * abs(math.sin(t * 7 + k * 1.3))) * fk
            d.polygon([(fx - 14 + k * 7, fy - 6), (fx - 6 + k * 7, fy - 6), (fx - 10 + k * 7 + math.sin(t * 5 + k) * 3,
                                                                           fy - 6 - hh)], fill=(255, 140, 40))
            d.polygon([(fx - 12 + k * 7, fy - 6), (fx - 8 + k * 7, fy - 6), (fx - 10 + k * 7, fy - 6 - hh * 0.6)],
                      fill=(255, 220, 90))
        if (playing and new_hat) or (boom and st["rng"].random() < 0.6):
            for _ in range(4 if boom else 2):
                st["sparks"].append([fx + st["rng"].uniform(-10, 10), fy - 30, st["rng"].uniform(-15, 15),
                                     -st["rng"].uniform(40, 90), 1.0, (255, 200, 90)])
        self._fx_step(st["sparks"], dt, grav=5.0, fade=0.6, cap=80)
        self._fx_draw(d, st["sparks"])
        # Der Zug: St. Martin zu Pferd voran, dahinter die Kinder
        ph = ((t - st["start"]) / SM_PERIOD) % 1.0 if not demo else 0.55
        lead = -60 + ph * (WIDTH + 260)
        if talk:
            lead = 150
        hx = lead
        step = math.sin(t * 5) * 3 if not talk else 0
        self._blob(img, hx, SM_FLOOR - 30, 46, 22, (240, 236, 230), gloss=0.4)     # Schimmel
        for lx in (-16, -8, 10, 18):
            d.line([(hx + lx, SM_FLOOR - 24), (hx + lx + (step if lx % 2 else -step), SM_FLOOR)], fill=(230, 226, 220),
                   width=4)
        self._limb(img, (hx + 18, SM_FLOOR - 34), (hx + 28, SM_FLOOR - 50), 10, (240, 236, 230))
        self._blob(img, hx + 32, SM_FLOOR - 52, 16, 11, (240, 236, 230), gloss=0.4)
        d.point((hx + 32, SM_FLOOR - 54), fill=(0, 0, 0))
        d.line([(hx - 22, SM_FLOOR - 32), (hx - 30, SM_FLOOR - 18)], fill=(220, 220, 220), width=4)
        cape_split = talk
        hc, hands = self._fig(img, d, hx, SM_FLOOR - 26, t, (200, 40, 50), {"lh": (10, 8), "rh": (14, -6)}, h=0.85,
                              sit=True, hat="helmet", hat_col=(220, 200, 90), legs=(200, 40, 50))
        cape = [(hc[0] - 4, hc[1] + 10), (hc[0] + 4, hc[1] + 10), (hc[0] - 16, SM_FLOOR - 26),
                (hc[0] - 30 + math.sin(t * 2) * 3, SM_FLOOR - 28)]
        d.polygon(cape if not cape_split else cape[:2] + [(hc[0] - 14, SM_FLOOR - 40), (hc[0] - 22, SM_FLOOR - 40)],
                  fill=(200, 30, 40))
        if talk:                                                                    # Mantelteilung
            tl = t - s.get("talk_t", t)
            bx = hx + 50
            self._fig(img, d, bx, SM_FLOOR, t, (120, 110, 100), {"lh": (-4, 10), "rh": (-12, -6)}, h=0.85, hair=(90, 90, 90),
                      beard=(150, 150, 150))
            d.polygon([(bx - 10, SM_FLOOR - 56), (bx + 8, SM_FLOOR - 56), (bx + 10, SM_FLOOR - 20), (bx - 12, SM_FLOOR - 20)],
                      fill=(200, 30, 40))
            d.line([(hands[1][0], hands[1][1]), (hands[1][0] + 10, hands[1][1] - 12)], fill=(200, 200, 210), width=2)
            if tl < 3.5:
                say.append((hc[0], hc[1] - 30, "Hier – die Hälfte ist deine."))
            elif tl < 6.5:
                say.append((bx, SM_FLOOR - 92, "Danke! Schön warm."))
        else:
            for i in range(6):
                kx = lead - 60 - i * 34
                if not (-30 < kx < WIDTH + 30):
                    continue
                b = bands[min(len(bands) - 1, i * len(bands) // 6)] if playing else 0.2
                glow = min(1.0, 0.25 + b * 1.4 + (0.6 if boom else 0))
                pose = {"lh": (-6, 18), "rh": (8, -4), "lf": (-6 + math.sin(t * 5 + i) * 5, 34),
                        "rf": (6 - math.sin(t * 5 + i) * 5, 34)}
                hc2, hands2 = self._fig(img, d, kx, SM_FLOOR, t + i, SM_LANTERNS[(i + 2) % 6], pose, h=0.62,
                                        hat="beanie", hat_col=SM_LANTERNS[(i + 4) % 6], mouth=0.6 if playing else 0.0)
                burn = (gl if gname == "laterne" and i == 1 and 1.5 <= gl < 5.0 else 0.0)
                self._sm_lantern(img, d, hands2[1][0], hands2[1][1], SM_LANTERNS[i], glow, burn)
                if gname == "laterne" and i == 1:
                    if 1.6 <= gl < 3.6:
                        say.append((hc2[0], hc2[1] - 26, "Meine Laterne brennt!"))
                    elif 4.0 <= gl < 6.4:
                        say.append((hc2[0], hc2[1] - 26, "Neue Laterne, bitte!"))
            if boom and 0.4 < bt < 3.0:
                say.append((fx - 20, SM_FLOOR - 120, "Ooooh!"))
        if gname == "gans":
            gx = 340 - gl * 60 if gl < 4.0 else 100 - (gl - 4.0) * 10
            gy = SM_FLOOR - abs(math.sin(gl * 12)) * 4
            hide = gl > 5.0
            if not hide:
                self._blob(img, gx, gy - 10, 22, 14, (250, 250, 250), gloss=0.4)
                self._limb(img, (gx - 6, gy - 14), (gx - 12, gy - 28), 4, (250, 250, 250))
                self._blob(img, gx - 13, gy - 30, 8, 7, (250, 250, 250), gloss=0.4)
                d.polygon([(gx - 16, gy - 31), (gx - 22, gy - 29), (gx - 16, gy - 28)], fill=(250, 160, 40))
                for side in (-1, 1):
                    d.line([(gx + side * 3, gy - 4), (gx + side * 3 + math.sin(t * 14) * 3, gy)], fill=(250, 160, 40),
                           width=2)
            else:
                d.rectangle([92, SM_FLOOR - 26, 116, SM_FLOOR], fill=(110, 80, 50))     # Kiste mit Gans
                d.text((95, SM_FLOOR - 24), "Kiste", font=self.f_tiny, fill=(230, 210, 170))
                d.point((104, SM_FLOOR - 30), fill=(250, 250, 250))
            if 1.0 <= gl < 3.6:
                say.append((gx, gy - 46, "Nicht mit mir!"))
            elif gl >= 5.6:
                say.append((104, SM_FLOOR - 50, "Hier ist keine Gans."))
        elif gname == "weckmann":
            wx, wy = 40 + min(1.0, max(0.0, gl - 2.0) / 3.0) * 80, SM_FLOOR
            hop = abs(math.sin(gl * 8)) * 4 if gl > 2.0 else 0
            c = (210, 150, 80)
            self._blob(img, wx, wy - 18 - hop, 18, 24, c, gloss=0.5)
            self._blob(img, wx, wy - 36 - hop, 14, 13, c, gloss=0.5)
            for side in (-1, 1):
                self._limb(img, (wx + side * 6, wy - 24 - hop), (wx + side * 12, wy - 16 - hop - 6 * (gl > 2)), 5, c)
                self._limb(img, (wx + side * 4, wy - 8 - hop), (wx + side * 6, wy), 5, c)
                d.ellipse([wx + side * 3 - 1.5, wy - 39 - hop, wx + side * 3 + 1.5, wy - 36 - hop], fill=(60, 30, 20))
            for k in range(3):
                d.ellipse([wx - 1.5, wy - 26 + k * 6 - hop, wx + 1.5, wy - 23 + k * 6 - hop], fill=(250, 250, 240))
            d.line([(wx + 2, wy - 32 - hop), (wx + 10, wy - 30 - hop)], fill=(250, 250, 240), width=2)   # Pfeife
            d.rectangle([wx + 9, wy - 34 - hop, wx + 13, wy - 29 - hop], fill=(250, 250, 240))
            if 2.2 <= gl < 4.6:
                say.append((wx, wy - 58, "Ich geh mit!"))
            elif gl >= 4.8:
                say.append((wx, wy - 58, "Bloß nicht anbeißen!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_lantern = (255, int(130 + 80 * level), 40)
        return img
