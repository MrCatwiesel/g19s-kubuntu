"""Visualisierung „Kellertreppe“ (Horror mit Pointe): Eine nackte Glühbirne pendelt im Takt (Bassschläge stoßen sie
an), Licht und Schatten wandern durch den Keller. In den dunklen Ecken blinzeln Augenpaare auf hohe Schläge.
Beim Höhepunkt flackert das Licht und geht aus – nur noch Augen –, dann geht es wieder an: ein Monster mit
Kittelschürze saugt den Keller. Gags: Spinne mit Kopfhörern, Mäuse-Polonaise, Hand mit Staubwedel unter der
Treppe, die Waschmaschine frisst eine Socke. Bei Wortbeiträgen macht das Monster Pause und liest Zeitung.
Gänsehaut-Stufe (Option level): 1 schaurig-nett (wenige, freundliche Augen), 2 gruselig (mehr, glühende Augen,
Flackern), 3 Gänsehaut (rote Augen, Herzschlag am Bildrand, kurzer Schreckmoment im Dunkeln).
Echtes Gewitter laut Wetterseite blitzt durchs Kellerfenster (sanft, höchstens alle paar Sekunden).
"""
import math
import random

CL_FLOOR = VIS_H - 22
CL_CORD = (186, 0)                      # Aufhängung der Glühbirne
CL_CORD_LEN = 80
CL_LIGHT_R = 210                        # Reichweite des Lichts (Pixel)
CL_STEPS = 9                            # Stufen von oben links nach unten
CL_STAIR_X0, CL_STAIR_Y0, CL_STEP_W = 30, 62, 13
CL_STEP_H = (CL_FLOOR - CL_STAIR_Y0) / (CL_STEPS + 1)
CL_WASHER = (246, 142, 296, CL_FLOOR)
CL_BOXES = (158, 150, 200, CL_FLOOR)
CL_WINDOW = (250, 8, 292, 28)
CL_BOOM = 9.5                           # Dauer des Höhepunkts (flackern, dunkel, Monster saugt, geht)
CL_BOOM_LOCK = 20.0                     # frühestens so lange nach dem letzten Höhepunkt der nächste
CL_GAGS = {"spinne": 8.0, "maeuse": 7.0, "staub": 7.0, "socke": 8.0}
CL_GAG_FIRST = 12.0
# Verstecke der Augen (dunkle Ecken); je Stufe sind die ersten 2/4/6 belegt, beim Höhepunkt alle und mehr
CL_EYES = [(34, 176), (88, 184), (306, 40), (226, 182), (14, 100), (300, 118), (66, 158), (122, 120), (210, 40),
           (144, 30), (40, 130), (276, 132)]
CL_MONSTER_SAY = ["Oh! Ich putz nur.", "Schuhe aus!", "Hier wird gesaugt!", "Licht? Brauch ich nicht.",
                  "Nicht auf den Teppich!"]


class CellarVisual:
    vis_bulb = 0.0                      # Helligkeit der Glühbirne 0…1 (Tastaturbeleuchtung)
    vis_heart = 0.0                     # Herzschlag 0…1 (Stufe 3, Tastatur „Rot im Herzschlag“)

    # -- Hintergrund ---------------------------------------------------------- #
    @staticmethod
    def _cl_step(i):
        """Stufe i (0 = oben): (x0, x1, Oberkante y)."""
        x0 = CL_STAIR_X0 + i * CL_STEP_W
        return x0, x0 + CL_STEP_W, CL_STAIR_Y0 + (i + 1) * CL_STEP_H

    def _cl_scene(self):
        """Keller bei voller Beleuchtung: Ziegelwand, Treppe, Tür, Regal, Waschmaschine, Kisten, Fenster;
        dazu die Maske der Gegenstände (sie werfen Schatten an die Wand) – zwischengespeichert."""
        if "_cl_bg" in self.__dict__:
            return self._cl_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (120, 104, 92))
        d = ImageDraw.Draw(img)
        rng = random.Random(13)
        for row, y in enumerate(range(0, CL_FLOOR, 10)):                            # Ziegel
            off = 0 if row % 2 else 11
            for x in range(-off, WIDTH, 22):
                v = rng.randint(-12, 12)
                d.rectangle([x + 1, y + 1, x + 20, y + 8], fill=(132 + v, 98 + v, 82 + v))
        for y in range(CL_FLOOR, HEIGHT, 8):                                        # Steinboden
            d.rectangle([0, y, WIDTH, y + 7], fill=(96, 92, 90) if (y // 8) % 2 else (88, 86, 84))
            for x in range((y * 13) % 30, WIDTH, 30):
                d.line([(x, y), (x, y + 7)], fill=(70, 68, 66))
        d.polygon([(0, CL_STAIR_Y0 + 14), (CL_STAIR_X0 + CL_STEPS * CL_STEP_W - 18, CL_FLOOR), (0, CL_FLOOR)],
                  fill=(26, 20, 18))                                                # Raum unter der Treppe
        d.rectangle([2, 8, 28, CL_STAIR_Y0], fill=(90, 62, 40))                     # Tür oben
        d.rectangle([5, 12, 25, CL_STAIR_Y0 - 2], fill=(110, 76, 48))
        d.ellipse([20, 34, 24, 38], fill=(200, 180, 90))
        d.rectangle([0, CL_STAIR_Y0, CL_STAIR_X0, CL_STAIR_Y0 + 6], fill=(126, 84, 50))   # Absatz
        for i in range(CL_STEPS):                                                   # Stufen
            x0, x1, y = self._cl_step(i)
            d.rectangle([x0, y, x1 + 1, y + CL_STEP_H], fill=(116, 76, 44))
            d.rectangle([x0, y, x1 + 1, y + 3], fill=(150, 104, 64))
        x_end = CL_STAIR_X0 + CL_STEPS * CL_STEP_W
        d.polygon([(CL_STAIR_X0, CL_STAIR_Y0 + 6), (x_end, CL_FLOOR - CL_STEP_H + 4), (x_end, CL_FLOOR),
                   (x_end - 14, CL_FLOOR), (0, CL_STAIR_Y0 + 20), (0, CL_STAIR_Y0 + 6)], fill=(84, 54, 32))   # Wange
        for i in range(0, CL_STEPS, 2):                                             # Geländer
            x0, _, y = self._cl_step(i)
            d.line([(x0 + 6, y), (x0 + 6, y - 34)], fill=(70, 46, 30), width=2)
        d.line([(CL_STAIR_X0 + 6, CL_STAIR_Y0 - 21), (x_end - 7, CL_FLOOR - CL_STEP_H * 2 - 34)], fill=(96, 64, 40),
               width=4)
        wx0, wy0, wx1, wy1 = CL_WINDOW                                              # Kellerfenster
        d.rectangle([wx0 - 3, wy0 - 3, wx1 + 3, wy1 + 3], fill=(70, 66, 64))
        d.rectangle([wx0, wy0, wx1, wy1], fill=(14, 20, 40))
        d.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], fill=(70, 66, 64), width=2)
        for k in range(4):                                                          # Gitter
            d.line([(wx0 + 4 + k * 11, wy0), (wx0 + 4 + k * 11, wy1)], fill=(40, 38, 38))
        obj = Image.new("L", (WIDTH, VIS_H), 0)
        od = ImageDraw.Draw(obj)
        for y in (60, 92, 124):                                                     # Regal mit Einmachgläsern
            d.rectangle([238, y, 312, y + 4], fill=(110, 74, 44))
            od.rectangle([238, y, 312, y + 4], fill=255)
            for k, x in enumerate(range(242, 308, 13)):
                h = 14 + (k * 7 + y) % 9
                col = [(190, 80, 60), (220, 170, 60), (110, 150, 70), (150, 60, 110)][(k + y // 32) % 4]
                d.rectangle([x, y - h, x + 9, y], fill=col)
                d.rectangle([x - 1, y - h - 3, x + 10, y - h], fill=(200, 196, 180))
                d.line([(x + 2, y - h + 2), (x + 2, y - 3)], fill=(240, 240, 230))
                od.rectangle([x - 1, y - h - 3, x + 10, y], fill=255)
        for x in (238, 309):
            d.rectangle([x, 50, x + 3, CL_WASHER[1] - 6], fill=(96, 64, 38))
        bx0, by0, bx1, by1 = CL_BOXES                                               # Kisten
        d.rectangle([bx0, by0 + 18, bx1, by1], fill=(176, 138, 90))
        d.rectangle([bx0 + 6, by0, bx1 - 4, by0 + 18], fill=(186, 148, 98))
        d.line([(bx0, by0 + 28), (bx1, by0 + 28)], fill=(150, 112, 70), width=2)
        d.text((bx0 + 9, by0 + 4), "XMAS", font=load_font(8, bold=True), fill=(120, 60, 50))
        od.rectangle([bx0, by0 + 18, bx1, by1], fill=255)
        od.rectangle([bx0 + 6, by0, bx1 - 4, by0 + 18], fill=255)
        od.rectangle(CL_WASHER, fill=255)
        self._cl_bg = (img, obj)
        return self._cl_bg

    def _cl_washer(self, img, d, dx, s, t, eyes, level):
        x0, y0, x1, y1 = CL_WASHER
        x0, x1 = x0 + dx, x1 + dx
        d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=(222, 224, 228))
        d.rectangle([x0, y0, x1, y0 + 9], fill=(204, 206, 212))
        d.ellipse([x1 - 12, y0 + 2, x1 - 6, y0 + 7], fill=(80, 80, 90))
        cx, cy = (x0 + x1) / 2, y0 + 30
        d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], fill=(150, 154, 160))
        d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(30, 50, 80))
        a = t * 6
        d.arc([cx - 10, cy - 10, cx + 10, cy + 10], math.degrees(a), math.degrees(a) + 120, fill=(70, 110, 160), width=3)
        if eyes:
            glow = (255, 60, 40) if level >= 3 else (220, 240, 120)
            look = math.sin(t * 2) * 3
            for side in (-1, 1):
                d.ellipse([cx + side * 5 - 3 + look, cy - 3, cx + side * 5 + 3 + look, cy + 2], fill=glow)
        return cx, cy

    # -- Figuren -------------------------------------------------------------- #
    def _cl_monster(self, img, d, x, s, t, mode, level):
        """Zotteliges Monster mit geblümter Kittelschürze. mode: vacuum (saugt), walk, read (sitzt, Zeitung)."""
        fur, dark = (104, 70, 140), (70, 46, 96)
        floor = CL_FLOOR
        sit = mode == "read"
        by = floor - (30 if sit else 44)
        bob = abs(math.sin(t * 9)) * 3 if mode == "walk" else math.sin(t * 4) * 1.5
        self._blob(img, x, floor + 1, 60, 8, (40, 36, 40), gloss=0, alpha=0.6)
        for side in (-1, 1):                                                        # Füße
            fx = x + side * 12 + (math.sin(t * 9) * 4 * side if mode == "walk" else 0)
            if sit:
                fx += side * 6
            self._blob(img, fx, floor - 4, 20, 10, dark, gloss=0.3)
        rng = random.Random(3)
        for k in range(22):                                                         # Zotteln am Rand
            a = k / 22 * math.tau
            self._blob(img, x + math.cos(a) * 26, by - bob + math.sin(a) * 32, 12, 12, dark, gloss=0.2)
        self._blob(img, x, by - bob, 56, 70, fur, gloss=0.25)
        for k in range(8):
            px, py = x + rng.uniform(-18, 18), by - bob + rng.uniform(-24, 26)
            d.line([(px, py), (px + 2, py + 5)], fill=dark)
        apron = [(x - 18, by - bob - 6), (x + 18, by - bob - 6), (x + 22, by - bob + 30), (x - 22, by - bob + 30)]
        d.polygon(apron, fill=(246, 214, 226))                                      # Kittelschürze
        for k in range(9):
            fx = x - 15 + (k % 3) * 14 + (k // 3 % 2) * 4
            fy = by - bob - 1 + (k // 3) * 11
            for a in range(5):
                d.ellipse([fx + math.cos(a * 1.26) * 3 - 1.5, fy + math.sin(a * 1.26) * 3 - 1.5,
                           fx + math.cos(a * 1.26) * 3 + 1.5, fy + math.sin(a * 1.26) * 3 + 1.5], fill=(230, 90, 130))
            d.ellipse([fx - 1, fy - 1, fx + 1, fy + 1], fill=(250, 210, 60))
        d.line([(x - 14, by - bob - 6), (x - 8, by - bob - 30)], fill=(246, 214, 226), width=2)
        d.line([(x + 14, by - bob - 6), (x + 8, by - bob - 30)], fill=(246, 214, 226), width=2)
        hy = by - bob - 30
        for side in (-1, 1):                                                        # Hörner und Augen
            d.polygon([(x + side * 10, hy - 4), (x + side * 18, hy - 22), (x + side * 16, hy - 2)], fill=(236, 220, 180))
            ex = x + side * 9
            d.ellipse([ex - 8, hy - 2, ex + 8, hy + 16], fill=(252, 252, 240))
            look = 2 if mode == "vacuum" else -2 if mode == "read" else 0
            d.ellipse([ex - 3 + look, hy + 6, ex + 3 + look, hy + 13], fill=(20, 16, 24))
            if mode == "read" and s.get("talk") and s["t"] - s.get("talk_t", s["t"]) > 25:
                d.rectangle([ex - 8, hy - 2, ex + 8, hy + 8], fill=fur)               # Lider zu: döst
        my = hy + 22
        d.chord([x - 10, my - 4, x + 10, my + 6], 0, 180, fill=(60, 20, 30))
        for k in range(4):
            tx = x - 8 + k * 5
            d.polygon([(tx, my + 1), (tx + 3, my + 1), (tx + 1.5, my + 4)], fill=(255, 255, 250))
        if mode == "read":                                                          # Zeitung
            d.polygon([(x - 26, by - 8), (x + 26, by - 8), (x + 28, by + 22), (x - 28, by + 22)], fill=(232, 228, 214))
            d.line([(x, by - 8), (x, by + 22)], fill=(170, 166, 150))
            font = self.__dict__.setdefault("_cl_news_font", load_font(7, bold=True))
            d.text((x - 24, by - 6), "KELLER-", font=font, fill=(40, 40, 40))
            d.text((x + 3, by - 6), "BLATT", font=font, fill=(40, 40, 40))
            for k in range(4):
                d.line([(x - 23, by + 5 + k * 4), (x - 3, by + 5 + k * 4)], fill=(120, 120, 120))
                d.line([(x + 3, by + 5 + k * 4), (x + 23, by + 5 + k * 4)], fill=(120, 120, 120))
            return (x, hy)
        hand = (x + 26, by - bob + 6)
        self._limb(img, (x + 18, by - bob - 10), hand, 9, fur)
        self._limb(img, (x - 18, by - bob - 10), (x - 26, by - bob + 12), 9, fur)
        if mode == "vacuum":                                                        # Staubsauger
            nozzle = x + 52 + math.sin(t * math.pi / max(0.3, s.get("period") or 0.5)) * 20
            d.line([hand, (nozzle - 4, floor - 4)], fill=(60, 60, 70), width=3)
            d.rectangle([nozzle - 10, floor - 6, nozzle + 4, floor - 1], fill=(70, 70, 80))
            self._blob(img, x - 40, floor - 12, 26, 20, (210, 40, 50), gloss=0.9)
            d.line([(x - 40, floor - 12), (x - 22, by - bob + 12)], fill=(60, 60, 70), width=2)
            rng2 = random.Random(int(t * 6))
            for _ in range(5):                                                      # Staubwölkchen
                px = nozzle + rng2.uniform(-6, 10)
                py = floor - 6 - rng2.uniform(0, 14)
                self._blob(img, px, py, 6, 6, (200, 196, 190), alpha=0.5, flat=True)
        return (x, hy)

    def _cl_spider(self, img, d, x, y, s, t, level):
        k = 1.6 if level >= 3 else 1.0
        d.line([(x, 0), (x, y - 6 * k)], fill=(200, 200, 210))
        for side in (-1, 1):
            for j in range(4):
                a = math.radians(-50 + j * 30) + math.sin(t * 10 + j) * 0.15
                kx = x + side * math.cos(a) * 9 * k
                ky = y + math.sin(a) * 9 * k
                d.line([(x, y), (kx, ky - 3 * k), (kx + side * 4 * k, ky + 4 * k)], fill=(30, 26, 30), width=2)
        self._blob(img, x, y + 3 * k, 14 * k, 12 * k, (40, 34, 40), gloss=0.6)
        self._blob(img, x, y - 4 * k, 9 * k, 8 * k, (40, 34, 40), gloss=0.6)
        eye = (255, 40, 40) if level >= 3 else (240, 240, 230)
        for side in (-1, 1):
            d.ellipse([x + side * 2 * k - 1, y - 5 * k - 1, x + side * 2 * k + 1, y - 5 * k + 1], fill=eye)
        d.arc([x - 7 * k, y - 12 * k, x + 7 * k, y + 2 * k], 180, 360, fill=(230, 60, 60), width=2)   # Kopfhörer
        for side in (-1, 1):
            self._blob(img, x + side * 6 * k, y - 4 * k, 5 * k, 6 * k, (230, 60, 60), gloss=0.5)
        if int(s.get("beats", 0)) % 2:
            d.text((x + 10 * k, y - 18 * k), "♪", font=self.f_tiny, fill=(240, 240, 250))

    def _cl_mouse(self, img, d, x, y, t, hat):
        d.line([(x + 6, y - 2), (x + 13, y - 5 + math.sin(t * 9 + x) * 2)], fill=(200, 150, 150))
        self._blob(img, x, y - 4, 14, 9, (150, 150, 158), gloss=0.4)
        self._blob(img, x - 7, y - 6, 8, 7, (150, 150, 158), gloss=0.4)
        self._blob(img, x - 6, y - 10, 5, 5, (220, 170, 180), gloss=0.2)
        d.point((x - 9, y - 7), fill=(10, 10, 10))
        d.point((x - 11, y - 5), fill=(240, 120, 140))
        if hat:
            d.polygon([(x - 10, y - 10), (x - 4, y - 10), (x - 8, y - 19)], fill=hat)

    def _cl_hand(self, img, d, k, s, t):
        """Grüne Hand mit Staubwedel kommt unter der Treppe hervor (k 0…1 ausgestreckt)."""
        base = (8, CL_FLOOR - 8)
        tip = (base[0] + 96 * k, CL_FLOOR - 10)
        self._limb(img, base, tip, 10, (90, 150, 70))
        self._blob(img, tip[0], tip[1], 12, 10, (100, 170, 80), gloss=0.3)
        sweep = math.sin(t * math.pi / max(0.3, s.get("period") or 0.5)) * 10
        end = (tip[0] + 18 + sweep, CL_FLOOR - 4)
        d.line([tip, end], fill=(120, 80, 40), width=2)
        for j in range(5):
            self._blob(img, end[0] + 4 + j * 1.5, end[1] - 2 + (j % 2) * 2, 10, 6, (240, 120, 180), gloss=0.1,
                       ang=-20 + j * 10)
        for j in range(3):
            q = (t * 2 + j / 3) % 1.0
            self._blob(img, end[0] + 4 + q * 14, end[1] - 4 - q * 14, 6 + q * 8, 6 + q * 8, (190, 186, 180),
                       alpha=0.4 * (1 - q), flat=True)

    def _cl_scare(self, img):
        """Schreckmoment (Stufe 3): riesiges Gesicht für ein paar Bilder."""
        img = Image.blend(img, Image.new("RGB", img.size, (40, 0, 4)), 0.8)
        d = ImageDraw.Draw(img)
        self._blob(img, WIDTH / 2, VIS_H / 2 + 20, 330, 260, (60, 40, 76), gloss=0.15)
        for side in (-1, 1):
            cx = WIDTH / 2 + side * 62
            self._blob(img, cx, 80, 90, 70, (255, 230, 80), alpha=0.5, flat=True)
            d.ellipse([cx - 30, 58, cx + 30, 104], fill=(255, 220, 60))
            d.ellipse([cx - 5, 60, cx + 5, 102], fill=(10, 4, 8))
        d.chord([60, 120, 260, 220], 0, 180, fill=(30, 4, 10))
        for k in range(12):
            tx = 66 + k * 16
            d.polygon([(tx, 170), (tx + 12, 170), (tx + 6, 192)], fill=(250, 248, 236))
        return img

    # -- Ablauf ---------------------------------------------------------------- #
    @vis_style("cellar")
    def vis_cellar(self, s, o, color):
        t = s["t"]
        level = int(o["level"]) if str(o.get("level")) in ("1", "2", "3") else 2
        bg, objmask = self._cl_scene()
        img = bg.copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        st = self._vstate("cellar", lambda: {"th": 0.3, "om": 0.0, "beats": s["beats"], "slow": s["level"],
                                              "fast": s["level"], "boom": -99.0, "gag": None, "booms": 0,
                                              "next_gag": t + CL_GAG_FIRST, "order": [], "rng": random.Random(29),
                                              "flash": -99.0, "next_flash": t + 4.0, "start": t})
        dt = self._vis_dt(st, t)
        talk = bool(s.get("talk"))
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        # Glühbirne pendelt: Bassschläge stoßen in Bewegungsrichtung an, Reibung bremst, Wortbeitrag: ruhig
        if demo:
            st["th"], st["om"] = 0.32 * math.sin(t * 3.4), 0.0
        else:
            if new_beat and s["bass"] > 0.55 and not talk:
                soft = max(0.0, 1 - abs(st["th"]) / 0.55)                     # weit draußen: kaum noch Schwung
                st["om"] += (0.25 + 0.45 * s["bass"]) * soft * (1 if st["om"] >= 0 else -1)
            st["om"] += (-12.0 * st["th"] - (2.5 if talk else 0.55) * st["om"]) * dt
            st["th"] = max(-0.7, min(0.7, st["th"] + st["om"] * dt))
        bx = CL_CORD[0] + math.sin(st["th"]) * CL_CORD_LEN
        by = CL_CORD[1] + math.cos(st["th"]) * CL_CORD_LEN
        # Höhepunkt
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and not talk and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > CL_BOOM_LOCK \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
            st["booms"] += 1
        bt = t - st["boom"]
        boom = 0 <= bt < CL_BOOM
        # Gags
        gag = st["gag"]
        if gag and t - gag[1] >= CL_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(14, 24)
        if not demo and gag is None and not boom and not talk and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(CL_GAGS), len(CL_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        # Licht: an, flackern (hohe Schläge, ab Stufe 2), aus beim Höhepunkt
        bright = 1.0
        if level >= 2 and 0 <= t - s.get("hat_t", -9) < 0.08 and s.get("hat", 0) > 0.7 and \
                random.Random(s.get("hats", 0) * 7).random() < 0.15:
            bright = 0.15
        if boom:
            if bt < 0.7:
                bright = 1.0 if (0.15 <= bt < 0.3 or 0.45 <= bt < 0.55) else 0.05
            elif bt < 2.2:
                bright = 0.0
        if talk:
            bright = 1.0
        self.vis_bulb = bright
        # Dynamisches vor dem Licht (wird mit beleuchtet)
        shake = math.sin(t * 50) * 2 * (0.4 + s["bass"]) if gag and gag[0] == "socke" else 0.0
        gl = t - gag[1] if gag else 0.0
        eyes_in = bool(gag and gag[0] == "socke" and level >= 2 and 1.0 <= gl < 3.4)
        pc = self._cl_washer(img, d, shake, s, t, eyes_in, level)
        if gag and gag[0] == "socke":
            k = max(0.0, min(1.0, (gl - 3.4) / 1.2))
            if k < 1:
                sx = 222 + (pc[0] - 222) * k
                sy = CL_FLOOR - 3 - math.sin(k * math.pi) * 26 + (pc[1] - CL_FLOOR) * k
                sc = 1 - 0.7 * k
                d.rounded_rectangle([sx - 8 * sc, sy - 3 * sc, sx + 8 * sc, sy + 3 * sc], radius=2, fill=(240, 240, 240))
                for j in range(3):
                    d.line([(sx - 6 * sc + j * 5 * sc, sy - 3 * sc), (sx - 6 * sc + j * 5 * sc, sy + 3 * sc)],
                           fill=(220, 50, 60), width=2)
        if gag and gag[0] == "staub":
            k = min(1.0, gl / 1.2, max(0.0, (CL_GAGS["staub"] - gl) / 1.2))
            self._cl_hand(img, d, k, s, t)
        if gag and gag[0] == "maeuse":
            hats = [(230, 60, 100), (60, 170, 230), (250, 200, 60), (110, 200, 90)]
            ph = (t - s.get("beat_t", t)) / max(0.3, s.get("period") or 0.5)
            for j in range(4):
                mx = -20 + (WIDTH + 60) * gl / CL_GAGS["maeuse"] - j * 18
                hop = abs(math.sin(min(1.0, ph) * math.pi)) * 5 if (j + s["beats"]) % 2 else 0
                self._cl_mouse(img, d, mx, CL_FLOOR - hop, t, hats[j])
        monster = None
        if talk:
            monster = (124, "read")
        elif boom and bt >= 2.2:
            k = (bt - 7.2) / (CL_BOOM - 7.2)
            monster = (150 - 110 * _smooth(k), "walk") if k > 0 else (150, "vacuum")
        head = None
        if monster:
            sh = self._cl_shadow_offset(monster[0], CL_FLOOR - 50, bx, by)
            self._blob(img, monster[0] + sh[0], CL_FLOOR - 50 + sh[1], 60, 80, (40, 32, 34), gloss=0, alpha=0.45)
            head = self._cl_monster(img, d, monster[0], s, t, monster[1], level)
        if gag and gag[0] == "spinne":
            k = min(1.0, gl / 2.5)
            up = max(0.0, (gl - (CL_GAGS["spinne"] - 2.0)) / 2.0)
            y = 20 + 90 * _smooth(k) * (1 - _smooth(up)) + s["bass"] * 6
            self._cl_spider(img, d, 112, y, s, t, level)
        # Licht und Schatten
        img = self._cl_light(img, objmask, bx, by, bright)
        d = ImageDraw.Draw(img)
        self._cl_weather(img, d, st, t, demo)
        # Glühbirne mit Kabel
        d.line([CL_CORD, (bx, by - 6)], fill=(30, 28, 26), width=2)
        d.rectangle([bx - 3, by - 8, bx + 3, by - 3], fill=(120, 116, 100))
        if bright > 0.3:
            self._blob(img, bx, by + 3, 46, 46, (255, 210, 120), alpha=0.5 * bright, flat=True)
            self._blob(img, bx, by + 3, 11, 13, (255, 246, 200), gloss=0.2)
        else:
            self._blob(img, bx, by + 3, 11, 13, (60, 56, 50), gloss=0.4)
        # Augen in der Dunkelheit
        self._cl_eyes(img, d, s, t, level, bx, by, bright, boom and 0.7 <= bt < 2.2, talk)
        if level >= 3 and not talk:                                                 # Herzschlag am Bildrand
            img = self._cl_heart(img, s, t)
            d = ImageDraw.Draw(img)
        else:
            self.vis_heart = 0.0
        # Sprechblasen
        if monster and head:
            if talk:
                tl = s["t"] - s.get("talk_t", s["t"])
                if tl < 3:
                    self._xmas_party_say(d, head[0], head[1] - 22, "Pause.")
                elif tl > 25:
                    self._bal_bubble(d, (head[0] + 4, head[1] + 10), None, t)
            elif 2.4 <= bt < 5.2:
                self._xmas_party_say(d, head[0], head[1] - 22, CL_MONSTER_SAY[(st["booms"] - 1) % len(CL_MONSTER_SAY)])
        if gag and gag[0] == "socke":
            if 4.6 <= gl < 6.0:
                self._xmas_party_say(d, pc[0], CL_WASHER[1] - 8, "MAMPF!")
            elif 6.4 <= gl < 7.8:
                self._xmas_party_say(d, pc[0], CL_WASHER[1] - 8, "Burp.")
        if gag and gag[0] == "staub" and 3.0 <= gl < 5.0:
            self._xmas_party_say(d, 70, CL_FLOOR - 24, "Hier wird's nie sauber.")
        if level >= 3 and boom and 1.7 <= bt < 1.95:
            img = self._cl_scare(img)                                               # Schreckmoment
        return img

    @staticmethod
    def _cl_shadow_offset(x, y, bx, by, k=0.18):
        """Schatten an der Wand: Gegenstand um k × (Abstand zur Glühbirne) versetzt."""
        return (x - bx) * k, (y - by) * k

    def _cl_light(self, img, objmask, bx, by, bright):
        """Kegel der Glühbirne (fällt mit dem Abstand ab) mal Bild; Gegenstände werfen versetzte Schatten an die
        Wand. Dunkle Stellen behalten einen Rest Licht (blaugrau)."""
        spr = self.__dict__.get("_cl_light_spr")
        if spr is None:
            R = CL_LIGHT_R
            yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
            r = np.sqrt(xx * xx + yy * yy) / R
            spr = self._cl_light_spr = Image.fromarray((np.clip(1 - r, 0, 1) ** 1.15 * 255).astype(np.uint8), "L")
        mask = Image.new("L", (WIDTH, VIS_H), 0)
        mask.paste(spr, (int(bx) - CL_LIGHT_R, int(by) - CL_LIGHT_R))
        lit = mask
        sh = Image.new("L", (WIDTH, VIS_H), 255)                                    # Schatten der Gegenstände
        sd = ImageDraw.Draw(sh)
        for x0, y0, x1, y1, k in ((*CL_BOXES, 0.2), (*CL_WASHER, 0.14), (238, 46, 312, 128, 0.08)):
            ox, oy = self._cl_shadow_offset((x0 + x1) / 2, (y0 + y1) / 2, bx, by, k)
            sd.rectangle([x0 + ox, y0 + oy, x1 + ox, min(CL_FLOOR, y1 + oy)], fill=90)   # nur an der Wand
        mask = ImageChops.multiply(mask, sh)
        mask = Image.composite(lit, mask, objmask)                                  # Gegenstände selbst hell
        lut = self.__dict__.setdefault("_cl_lut", {})
        key = round(bright, 2)
        if key not in lut:
            lut.clear()
            lut[key] = [int(16 + (255 - 16) * min(1.0, v / 255 * 1.7) * key) for v in range(256)]
        mask = mask.point(lut[key])
        full = Image.new("L", (WIDTH, HEIGHT), int(16 + 140 * bright))              # Fußzeile egal, Boden unten
        full.paste(mask, (0, 0))
        warm = Image.merge("RGB", (full, full.point(lambda v: int(v * 0.92)), full.point(lambda v: int(v * 0.8 + 10))))
        return ImageChops.multiply(img, warm)

    def _cl_weather(self, img, d, st, t, demo):
        """Wetter der Wetterseite: Regen am Kellerfenster, Gewitter blitzt (sanft, alle 6–15 s)."""
        kind = None if demo else self._party_weather()[0]
        wx0, wy0, wx1, wy1 = CL_WINDOW
        if kind in ("rain", "drizzle", "thunder"):
            rng = random.Random(int(t * 10))
            for _ in range(6):
                x = rng.uniform(wx0 + 1, wx1 - 1)
                y = rng.uniform(wy0, wy1 - 5)
                d.line([(x, y), (x - 1, y + 4)], fill=(120, 140, 190))
        if kind == "thunder" and t >= st["next_flash"]:
            st["flash"], st["next_flash"] = t, t + st["rng"].uniform(6, 15)
        if 0 <= t - st["flash"] < 0.12:
            d.rectangle([wx0, wy0, wx1, wy1], fill=(240, 244, 255))
            img.paste(Image.blend(img, Image.new("RGB", img.size, (200, 210, 255)), 0.22))

    def _cl_eyes(self, img, d, s, t, level, bx, by, bright, blackout, talk):
        """Augenpaare in den dunklen Ecken: sichtbar, wo wenig Licht hinfällt; blinzeln auf hohe Schläge.
        Stufe 1 rund und freundlich, 2 gelbgrün glühend, 3 rot mit Schlitz. Im Dunkeln (Höhepunkt): alle."""
        n = len(CL_EYES) if blackout else (2, 4, 6)[level - 1]
        col = ((246, 246, 240), (210, 240, 110), (255, 50, 40))[level - 1]
        for i, (x, y) in enumerate(CL_EYES[:n]):
            dist = math.hypot(x - bx, y - by) / CL_LIGHT_R
            vis = 1.0 if blackout else max(0.0, min(1.0, (dist - 0.55) / 0.35 + (1 - bright)))
            if vis < 0.15:
                continue
            blink = 0 <= t - s.get("hat_t", -9) < 0.13 and (s.get("hats", 0) + i) % 3 == 0
            half = talk                                                             # Wortbeitrag: dösen
            look = math.sin(t * 0.8 + i * 1.9) * 1.5 + (bx - x) / 160
            k = vis
            c = tuple(int(v * k) for v in col)
            if level >= 2:
                self._blob(img, x, y, 22, 12, col, alpha=round(0.35 * k, 2), flat=True)
            for side in (-1, 1):
                ex = x + side * 5
                if blink:
                    d.line([(ex - 3, y), (ex + 3, y)], fill=c)
                    continue
                top = y - (0 if half else 2.5)
                d.ellipse([ex - 3, top, ex + 3, y + 2.5], fill=c)
                if level == 1:
                    d.ellipse([ex - 1.2 + look, y - 1.2, ex + 1.2 + look, y + 1.2], fill=(10, 10, 14))
                elif level == 3:
                    d.line([(ex + look * 0.5, y - 2), (ex + look * 0.5, y + 2)], fill=(20, 0, 0))

    def _cl_heart(self, img, s, t):
        """Stufe 3: dunkelroter Herzschlag am Bildrand (Doppelschlag auf jeden Bassschlag)."""
        vig = self.__dict__.get("_cl_vig")
        if vig is None:
            yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
            r = np.sqrt(((xx - WIDTH / 2) / (WIDTH / 2)) ** 2 + ((yy - VIS_H / 2) / (VIS_H / 2)) ** 2)
            vig = self._cl_vig = Image.fromarray((np.clip((r - 0.65) / 0.6, 0, 1) * 255).astype(np.uint8), "L")
        a = t - s.get("beat_t", -9)
        k = math.exp(-max(0.0, a) * 9) + (0.6 * math.exp(-(a - 0.22) * 9) if a > 0.22 else 0.0)
        k = max(0.0, min(1.0, k * (0.4 + 0.6 * s["bass"])))
        self.vis_heart = k
        if k < 0.03:
            return img
        m = vig.point([int(v * k * 0.7) for v in range(256)])
        return Image.composite(Image.new("RGB", img.size, (120, 0, 8)), img, m)
