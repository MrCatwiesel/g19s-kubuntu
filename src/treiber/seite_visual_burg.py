"""Visualisierung „Mittelalter-Metal“ (metal, Mixin MetalVisual): Eine Ritter-Band spielt nachts im Burghof.
Sänger in Rüstung (Visier, Federbusch, Lanze als Mikrofonständer), Gitarrist im Kettenhemd mit wehenden Haaren und
Flying-V, Dudelsackspieler (der Sack bläht sich mit der Lautstärke), Trommler mit Hörnerhelm an zwei Fasstrommeln.
Feuerkörbe lodern mit dem Bass, Funken stieben auf hohe Schläge, vorn headbangt das Publikum mit der Pommesgabel.
Höhepunkt: Pyro – je nach Option schießen die Feuerkörbe Flammensäulen oder ein Drache auf dem Turm speit Feuer.
Wortbeitrag: Ein Herold verliest eine Bekanntmachung, die Band trinkt Met aus Hörnern.
Gags: Visier klappt zu, Mönch beim Crowdsurfen, Ritter auf Steckenpferd, Katapult schießt einen Kohlkopf,
Gitarrensolo mit gerissener Saite, Wall of Death, Burgfräulein wirft eine Rose, Drache headbangt mit, Trommler trinkt
Met und verpasst den Takt. Echtes Gewitter laut Wetterseite: Der Blitz schlägt in den Helm des Sängers.
"""
import math
import random

MT_STAGE = VIS_H - 64                   # Bühnenboden (Füße der Band)
MT_BAND = {"guitar": 74, "singer": 150, "piper": 222, "drums": 278}
MT_FIRE_X = (18, 302)                   # Feuerkörbe am Bühnenrand
MT_TOWERS = ((0, 44), (276, 320))       # Türme links/rechts (x von … bis)
MT_WALL_Y = 74                          # Oberkante der Burgmauer
MT_BOOM = 3.2                           # Pyro beim Höhepunkt (s)
MT_BOOM_LOCK = 12.0
MT_GAGS = {"visier": 5.0, "moench": 8.0, "steckenpferd": 7.0, "katapult": 7.0, "solo": 8.0, "walldeath": 7.0,
           "fraeulein": 7.0, "drache": 6.0, "met": 6.0}
MT_GAG_FIRST, MT_GAG_PAUSE = 8.0, (9.0, 15.0)
MT_HERALD = ["Hört, hört! Eine Bekanntmachung!", "Der König lässt verkünden …", "… Met ist heute billiger!",
             "Hört, hört! Wer hat sein Pferd im Halteverbot?"]
MT_STEEL, MT_STEEL_D = (176, 182, 196), (110, 116, 130)


class MetalVisual:
    vis_fire = 0.0                      # Feuerstärke 0…1 (Tastatur „Feuer“)

    # -- Hintergrund ------------------------------------------------------------------- #
    def _mt_scene(self):
        """Nachthimmel mit Mond, Burgmauer mit Zinnen, zwei Türme mit Bannern, Holzbühne (zwischengespeichert)."""
        if "_mt_bg" in self.__dict__:
            return self._mt_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([16, 12, 40], np.float32), np.array([70, 34, 60], np.float32)
        arr = np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)).copy()
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(4)
        for _ in range(40):
            d.point((rng.randrange(WIDTH), rng.randrange(MT_WALL_Y)), fill=(200, 200, 230))
        self._blob(img, 236, 30, 26, 26, (250, 240, 210), gloss=0.1)               # Vollmond
        self._blob(img, 236, 30, 60, 60, (200, 190, 230), alpha=0.18, flat=True)
        stone, dark = (92, 86, 98), (66, 60, 74)
        d.rectangle([0, MT_WALL_Y, WIDTH, MT_STAGE], fill=stone)                    # Mauer
        for row, y in enumerate(range(MT_WALL_Y + 2, MT_STAGE, 9)):
            off = 0 if row % 2 else 9
            for x in range(-off, WIDTH, 18):
                v = rng.randint(-8, 8)
                d.rectangle([x + 1, y, x + 16, y + 7], fill=(stone[0] + v, stone[1] + v, stone[2] + v))
        for x in range(0, WIDTH, 20):                                               # Zinnen
            d.rectangle([x, MT_WALL_Y - 10, x + 11, MT_WALL_Y], fill=stone)
        for x0, x1 in MT_TOWERS:                                                    # Türme mit Dach und Banner
            d.rectangle([x0, 20, x1, MT_STAGE], fill=dark)
            for y in range(24, MT_STAGE, 9):
                d.line([(x0, y), (x1, y)], fill=(54, 50, 62))
            d.polygon([(x0 - 4, 22), (x1 + 4, 22), ((x0 + x1) / 2, -14)], fill=(110, 40, 50))
            cx = (x0 + x1) / 2
            d.rectangle([cx - 4, 38, cx + 4, 50], fill=(30, 26, 30))                 # Fenster
            d.polygon([(cx - 9, 60), (cx + 9, 60), (cx + 9, 96), (cx, 90), (cx - 9, 96)], fill=(150, 30, 40))
            d.polygon([(cx - 4, 70), (cx + 4, 70), (cx, 80)], fill=(240, 200, 70))
        d.rectangle([0, MT_STAGE, WIDTH, MT_STAGE + 10], fill=(110, 72, 42))       # Bühne
        for x in range(0, WIDTH, 24):
            d.line([(x, MT_STAGE), (x, MT_STAGE + 10)], fill=(80, 52, 30))
        d.line([(0, MT_STAGE), (WIDTH, MT_STAGE)], fill=(150, 104, 60), width=2)
        d.rectangle([0, MT_STAGE + 10, WIDTH, HEIGHT], fill=(30, 22, 26))
        rx = MT_BAND["drums"]                                                       # Podest des Trommlers
        d.rectangle([rx - 30, MT_STAGE - 8, rx + 30, MT_STAGE], fill=(96, 62, 36))
        self._mt_bg = img
        return img

    # -- Figuren ------------------------------------------------------------------------ #
    def _mt_legs(self, img, x, feet, hip, spread, color, boot=(40, 32, 30)):
        for side in (-1, 1):
            hj = (x + side * 5, hip)
            knee, foot = _ik(hj, (x + side * spread, feet - 1), 13, 13, side)
            self._limb(img, hj, knee, 7, color)
            self._limb(img, knee, foot, 6, color)
            self._blob(img, foot[0] + side * 2, foot[1], 11, 6, boot, gloss=0.6)

    def _mt_arm(self, img, sh, target, side, upper, lower, hand):
        elbow, h = _ik(sh, target, 12, 12, side)
        self._limb(img, sh, elbow, 6, upper)
        self._limb(img, elbow, h, 5, lower)
        self._blob(img, h[0], h[1], 7, 7, hand, gloss=0.5)
        return h

    def _mt_singer(self, img, d, x, feet, t, bang, visor, glow=0.0, raise_arm=0.0, drink=False):
        """Ritter in Rüstung mit Federbusch, singt an der Lanze; visor 0…1 = Visier zu."""
        hip = feet - 27
        self._mt_legs(img, x, feet, hip, 7, MT_STEEL)
        self._blob(img, x, hip - 14, 26, 32, MT_STEEL, gloss=0.8)
        d.polygon([(x - 10, hip - 26), (x + 10, hip - 26), (x + 12, hip + 6), (x - 12, hip + 6)], fill=(140, 26, 36))
        d.polygon([(x - 4, hip - 18), (x + 4, hip - 18), (x, hip - 6)], fill=(240, 200, 70))   # Wappen
        for side in (-1, 1):
            self._blob(img, x + side * 13, hip - 25, 12, 10, MT_STEEL, gloss=0.9)    # Schulterpanzer
        lx = x + 18                                                                   # Lanze als Mikrofonständer
        d.line([(lx, feet), (lx - 4, hip - 40)], fill=(120, 84, 50), width=3)
        d.polygon([(lx - 6, hip - 40), (lx - 2, hip - 40), (lx - 4, hip - 50)], fill=MT_STEEL_D)
        self._blob(img, lx - 8, hip - 36, 6, 7, (50, 50, 56), gloss=0.8)             # Mikrofon
        if drink:
            hand = self._mt_arm(img, (x + 11, hip - 24), (x + 4, hip - 40), 1, MT_STEEL, MT_STEEL, MT_STEEL_D)
            self._mt_horn(img, d, hand)
        else:
            self._mt_arm(img, (x + 11, hip - 24), (lx - 6, hip - 34), 1, MT_STEEL, MT_STEEL, MT_STEEL_D)
        ltarget = (x - 22, hip - 52) if raise_arm > 0.5 else (x - 18 - 6 * bang, hip - 6 - 10 * bang)
        hand = self._mt_arm(img, (x - 11, hip - 24), ltarget, -1, MT_STEEL, MT_STEEL, MT_STEEL_D)
        if raise_arm > 0.5:                                                           # Schwert in die Höhe
            d.line([hand, (hand[0] - 4, hand[1] - 30)], fill=(220, 224, 236), width=3)
            d.line([(hand[0] - 6, hand[1] - 2), (hand[0] + 4, hand[1] - 2)], fill=(200, 160, 60), width=3)
        hy = hip - 40 + 7 * bang
        hx = x + 2 * bang
        self._blob(img, hx, hy, 19, 21, MT_STEEL, gloss=0.9)                         # Helm
        if glow:
            self._blob(img, hx, hy, 40, 40, (180, 220, 255), alpha=round(0.6 * glow, 2), flat=True)
        if visor < 0.5:
            d.rectangle([hx - 7, hy - 2, hx + 7, hy + 5], fill=(40, 34, 40))
            d.ellipse([hx - 4, hy, hx - 1, hy + 2], fill=(240, 220, 200))
            d.ellipse([hx + 1, hy, hx + 4, hy + 2], fill=(240, 220, 200))
        else:
            d.line([(hx - 7, hy + 1), (hx + 7, hy + 1)], fill=(60, 64, 74), width=2)
            for k in range(3):
                d.point((hx - 3 + k * 3, hy + 4), fill=(60, 64, 74))
        for k in range(4):                                                            # Federbusch
            a = -0.4 + k * 0.3 + math.sin(t * 6) * 0.1 - bang * 0.4
            d.line([(hx, hy - 10), (hx + math.sin(a) * 14, hy - 10 - math.cos(a) * 14)], fill=(220, 40, 50), width=3)
        return (hx, hy)

    def _mt_guitarist(self, img, d, x, feet, t, bang, strum, kneel=0.0, drink=False):
        """Kettenhemd, lange Haare (fliegen beim Headbangen), Flying-V."""
        hip = feet - 27 + 12 * kneel
        self._mt_legs(img, x, feet, hip, 9 - 4 * kneel, (50, 44, 40))
        mail = (130, 134, 140)
        self._blob(img, x, hip - 14, 24, 30, mail, gloss=0.5)
        for k in range(10):                                                           # Kettenglieder
            d.point((x - 8 + (k * 7) % 17, hip - 22 + (k * 5) % 18), fill=(90, 94, 100))
        gx, gy = x + 2, hip - 8                                                       # Gitarre
        body = [(gx - 4, gy - 4), (gx + 16, gy - 12), (gx + 12, gy), (gx + 16, gy + 10), (gx - 4, gy + 4)]
        d.polygon(body, fill=(150, 20, 30))
        d.line([(gx - 2, gy), (gx - 30, gy - 8)], fill=(90, 60, 40), width=3)
        d.line([(gx - 30, gy - 8), (gx - 36, gy - 12)], fill=(40, 30, 30), width=4)
        skin = (236, 196, 166)
        if drink:
            hand = self._mt_arm(img, (x + 10, hip - 24), (x + 2, hip - 40), 1, mail, skin, skin)
            self._mt_horn(img, d, hand)
        else:
            self._mt_arm(img, (x + 10, hip - 24), (gx + 6, gy - 2 + 6 * strum), 1, mail, skin, skin)
        self._mt_arm(img, (x - 10, hip - 24), (gx - 24, gy - 8), -1, mail, skin, skin)
        hy = hip - 38 + 8 * bang
        hx = x + 3 * bang
        hair = (60, 36, 24)
        for k in range(5):                                                            # fliegende Haare
            a = -1.0 + k * 0.5
            ln = 14 + 8 * bang
            d.line([(hx, hy - 4), (hx + math.sin(a + bang) * ln, hy - 4 + abs(math.cos(a)) * ln * (2 * bang - 0.6))],
                   fill=hair, width=4)
        self._blob(img, hx, hy, 15, 17, skin, gloss=0.3)
        self._blob(img, hx, hy - 6, 17, 9, hair, gloss=0.3)
        d.line([(hx - 4, hy + 1), (hx - 1, hy + 1)], fill=(30, 20, 20))
        d.line([(hx + 1, hy + 1), (hx + 4, hy + 1)], fill=(30, 20, 20))
        d.ellipse([hx - 2, hy + 4, hx + 2, hy + 7], fill=(80, 20, 20))
        return (hx, hy)

    def _mt_piper(self, img, d, x, feet, t, bang, puff, drink=False):
        """Dudelsackspieler: grüner Wams, Hut mit Feder; der Sack bläht sich mit der Lautstärke."""
        hip = feet - 27
        self._mt_legs(img, x, feet, hip, 7, (70, 60, 44))
        tunic, skin = (50, 110, 60), (236, 196, 166)
        self._blob(img, x, hip - 14, 24, 32, tunic, gloss=0.3)
        d.line([(x - 12, hip - 2), (x + 12, hip - 2)], fill=(90, 60, 30), width=3)
        bag = (x - 12, hip - 18)
        self._blob(img, bag[0], bag[1], 16 + 8 * puff, 14 + 6 * puff, (120, 40, 60), gloss=0.5)
        for k in range(3):                                                            # Bordunpfeifen
            d.line([(bag[0] - 2 + k * 3, bag[1] - 4), (bag[0] - 10 + k * 7, bag[1] - 34 + k * 4)], fill=(40, 30, 26),
                   width=2)
        if drink:
            hand = self._mt_arm(img, (x + 10, hip - 24), (x + 2, hip - 40), 1, tunic, skin, skin)
            self._mt_horn(img, d, hand)
        else:
            self._mt_arm(img, (x + 10, hip - 24), (x + 4, hip - 6), 1, tunic, skin, skin)
            d.line([(x + 4, hip - 6), (x - 1, hip - 34)], fill=(40, 30, 26), width=2)  # Spielpfeife
        self._mt_arm(img, (x - 10, hip - 24), (x - 4, hip - 16), -1, tunic, skin, skin)
        hy = hip - 38 + 5 * bang
        self._blob(img, x, hy, 15, 17, skin, gloss=0.3)
        for side in (-1, 1):
            self._blob(img, x + side * 5, hy + 3, 6, 5 + 3 * puff, _lerp(skin, (240, 140, 130), 0.4))   # Backen
        d.polygon([(x - 10, hy - 6), (x + 10, hy - 6), (x + 4, hy - 14), (x - 6, hy - 13)], fill=(40, 70, 40))
        d.line([(x + 4, hy - 12), (x + 16, hy - 24)], fill=(230, 220, 160), width=2)
        d.point((x - 3, hy), fill=(20, 20, 20))
        d.point((x + 3, hy), fill=(20, 20, 20))
        return (x, hy)

    def _mt_drummer(self, img, d, x, feet, t, hit_l, hit_r, drink=False):
        """Trommler mit Hörnerhelm und Fellweste an zwei Fasstrommeln."""
        hip = feet - 25
        skin = (226, 180, 146)
        self._blob(img, x, hip - 12, 26, 30, (110, 80, 50), gloss=0.2)               # Fellweste
        hy = hip - 36
        self._blob(img, x, hy, 16, 17, skin, gloss=0.3)
        self._blob(img, x, hy + 8, 14, 10, (170, 90, 40), gloss=0.2)                 # Bart
        self._blob(img, x, hy - 5, 18, 10, MT_STEEL, gloss=0.9)
        for side in (-1, 1):                                                          # Hörner
            d.line([(x + side * 8, hy - 6), (x + side * 14, hy - 12), (x + side * 13, hy - 20)], fill=(240, 230, 200),
                   width=3)
        d.point((x - 3, hy), fill=(20, 20, 20))
        d.point((x + 3, hy), fill=(20, 20, 20))
        for side, hit in ((-1, hit_l), (1, hit_r)):                                   # Trommeln vor ihm
            dx = x + side * 15
            d.rectangle([dx - 11, feet - 22, dx + 11, feet], fill=(130, 84, 46))
            d.ellipse([dx - 11, feet - 26, dx + 11, feet - 18], fill=(230, 214, 180))
            for yy in (feet - 16, feet - 6):
                d.line([(dx - 11, yy), (dx + 11, yy)], fill=(70, 60, 50), width=2)
            if drink and side == 1:
                hand = self._mt_arm(img, (x + 11, hip - 22), (x + 4, hip - 38), 1, skin, skin, skin)
                self._mt_horn(img, d, hand)
                continue
            target = (dx, feet - 24 - (1 - hit) * 14)
            hand = self._mt_arm(img, (x + side * 11, hip - 22), target, side, skin, skin, skin)
            d.line([hand, (hand[0] + side * 6, hand[1] - 10 + 12 * hit)], fill=(200, 170, 120), width=2)
        return (x, hy)

    def _mt_horn(self, img, d, hand):
        hx, hy = hand
        d.polygon([(hx - 2, hy - 2), (hx + 6, hy - 6), (hx + 12, hy - 14), (hx + 8, hy - 2)], fill=(230, 210, 160))
        d.line([(hx + 6, hy - 6), (hx + 12, hy - 14)], fill=(140, 110, 70), width=1)

    def _mt_fire(self, img, d, x, y, k, t):
        """Feuerkorb mit Flamme der Stärke k (0…1, beim Pyro bis 2)."""
        d.line([(x, y + 34), (x, y + 6)], fill=(40, 34, 34), width=3)
        d.polygon([(x - 10, y), (x + 10, y), (x + 6, y + 8), (x - 6, y + 8)], fill=(50, 44, 44))
        for j in range(3):
            d.line([(x - 9 + j * 9, y), (x - 5 + j * 5, y + 8)], fill=(80, 70, 66))
        h = 14 + 22 * k
        for j in range(4):
            q = j / 3
            fx = x + math.sin(t * 9 + j * 2) * 3 * (1 - q)
            fy = y - h * q * 0.8
            col = _lerp((255, 90, 20), (255, 230, 120), q)
            self._blob(img, fx, fy - 2, 16 - 8 * q, h * (1 - q * 0.6), col, alpha=0.75, flat=True)
        self._blob(img, x, y - h / 2, 60 + 40 * k, 60 + 40 * k, (255, 120, 40), alpha=round(0.12 + 0.1 * k, 2), flat=True)

    def _mt_crowd(self, img, d, st, s, t, gag, gl):
        """Publikum vorn: Köpfe und Schultern, Hörnerhelme, Pommesgabel auf jeden Schlag; Wall of Death."""
        rng = random.Random(8)
        beat_age = t - s.get("beat_t", t)
        jump = max(0.0, 1 - beat_age / 0.25) if s.get("active") or s.get("demo") else 0.0
        talk = bool(s.get("talk"))
        n = 11
        for i in range(n):
            base = 10 + i * (WIDTH - 20) / (n - 1) + rng.uniform(-6, 6)
            x = base
            if gag and gag[0] == "walldeath":                                       # auseinander, dann zusammen
                side = -1 if base < WIDTH / 2 else 1
                if gl < 3:
                    x = base + side * 40 * _smooth(gl / 3)
                elif gl < 4:
                    x = base + side * 40 * (1 - _smooth((gl - 3) / 1))
            y = MT_STAGE + 26 - (0 if talk else (jump * (6 if i % 2 else 3) + rng.uniform(0, 3)))
            col = (64 + i % 3 * 10, 44, 56)                                         # vom Feuer angestrahlt
            self._blob(img, x, y + 20, 30, 34, col, gloss=0.25)
            self._blob(img, x, y - 2, 15, 16, col, gloss=0.3)
            if i % 3 == 0:                                                           # Hörnerhelm
                for side in (-1, 1):
                    d.line([(x + side * 6, y - 6), (x + side * 11, y - 14)], fill=(200, 190, 170), width=2)
            if not talk and (i + s.get("beats", 0)) % 2 == 0:                       # Pommesgabel
                ax = x + (8 if i % 2 else -8)
                d.line([(x, y + 6), (ax, y - 18 - 4 * jump)], fill=col, width=4)
                d.line([(ax - 2, y - 18 - 4 * jump), (ax - 3, y - 26 - 4 * jump)], fill=col, width=2)
                d.line([(ax + 2, y - 18 - 4 * jump), (ax + 3, y - 26 - 4 * jump)], fill=col, width=2)
        if gag and gag[0] == "walldeath" and 3.6 <= gl < 4.6:                         # Zusammenprall
            for j in range(6):
                self._blob(img, WIDTH / 2 + (j - 2.5) * 14, MT_STAGE + 30 - j % 2 * 6, 22, 16, (150, 130, 110),
                           alpha=0.5, flat=True)

    # -- Ablauf ---------------------------------------------------------------------------- #
    @vis_style("metal")
    def vis_metal(self, s, o, color):
        t = s["t"]
        img = self._mt_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("metal", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                             "boom": -99.0, "gag": None, "next_gag": t + MT_GAG_FIRST, "order": [],
                                             "rng": random.Random(31), "sparks": [], "bolt": -99.0,
                                             "next_bolt": t + 6.0, "start": t, "song": None, "jester": -99.0})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        ph = ((t - s.get("beat_t", t)) / period) % 1.0
        playing = (s.get("active") or demo) and not talk
        bang = (math.sin(math.pi * min(1.0, (t - s.get("beat_t", t)) / (period * 0.6)))) if playing else 0.0
        # Höhepunkt → Pyro
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and not talk and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > MT_BOOM_LOCK \
                and t - st["start"] > 4:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < MT_BOOM and o.get("pyro", "dragon") != "off"
        # Gags
        gag = st["gag"]
        if gag and t - gag[1] >= MT_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*MT_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and not talk and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(MT_GAGS), len(MT_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gl = t - gag[1] if gag else 0.0
        # Liedwechsel: der Hofnarr läuft mit „Zugabe!“-Schild über die Bühne
        song = getattr(self, "_vis_song", "")
        if st["song"] is not None and song and song != st["song"] and not demo:
            st["jester"] = t
        st["song"] = song
        # Feuer
        fire = (0.3 + 0.7 * s["bass"]) if playing else 0.25
        if boom and o.get("pyro", "dragon") in ("fire", "dragon"):
            fire = 1.0 + 0.8 * math.sin(min(1.0, bt / MT_BOOM) * math.pi)
        self.vis_fire = min(1.0, fire)
        if 0 <= t - s.get("hat_t", -9) < 0.05 and playing:                           # Funken auf hohe Schläge
            for fx in MT_FIRE_X:
                for _ in range(3):
                    st["sparks"].append([fx + st["rng"].uniform(-4, 4), MT_STAGE - 46, st["rng"].uniform(-20, 20),
                                         st["rng"].uniform(-90, -50), t])
        say = []
        # Turm links: Burgfräulein; Turm rechts: Drache
        if gag and gag[0] == "fraeulein":
            self._mt_lady(img, d, gl, say, t)
        dragon_k = 0.0
        if gag and gag[0] == "drache":
            dragon_k = min(1.0, gl / 0.8, (MT_GAGS["drache"] - gl) / 0.8)
        if boom and o.get("pyro", "dragon") == "dragon":
            dragon_k = min(1.0, bt / 0.4, (MT_BOOM - bt) / 0.4 + 0.01)
        if dragon_k > 0:
            peek = not boom
            self._mt_dragon(img, d, dragon_k, t, bang if peek else 0.0, breathe=boom, peek=peek)
            if gag and gag[0] == "drache" and 1.0 <= gl < 4.5:
                say.append((240, MT_WALL_Y - 34, "Hörner hoch!"))
        if gag and gag[0] == "katapult":
            self._mt_catapult(img, d, gl, t, say)
        # Feuerkörbe
        for fx in MT_FIRE_X:
            self._mt_fire(img, d, fx, MT_STAGE - 40, fire, t)
        # Band
        drink = talk
        lvl = s["level"] if playing else 0.0
        strum = abs(math.sin(t * 20)) if playing and t - s.get("hat_t", -9) < 0.2 else 0.0
        heads = {}
        solo = gag and gag[0] == "solo"
        gx = MT_BAND["guitar"] + (26 * min(1.0, gl / 1.0) if solo and gl < 7 else 0)
        heads["guitar"] = self._mt_guitarist(img, d, gx, MT_STAGE, t, bang, strum,
                                             kneel=min(1.0, max(0.0, (gl - 1.0) / 0.6)) if solo and gl < 7 else 0.0,
                                             drink=drink)
        if solo and 1.6 <= gl < 6 and t - s.get("hat_t", -9) < 0.15:
            for _ in range(2):
                st["sparks"].append([gx + 16, MT_STAGE - 34, st["rng"].uniform(-40, 40), st["rng"].uniform(-80, -30), t])
        missed = gag and gag[0] == "met"
        hit = max(0.0, 1 - (t - s.get("beat_t", -9)) / 0.15) if playing and not missed else 0.0
        heads["drums"] = self._mt_drummer(img, d, MT_BAND["drums"], MT_STAGE - 8, t,
                                          hit if s["beats"] % 2 else 0.0, hit if s["beats"] % 2 == 0 else 0.0,
                                          drink=drink or (missed and gl < 3.6))
        heads["piper"] = self._mt_piper(img, d, MT_BAND["piper"], MT_STAGE, t, bang * 0.6, lvl, drink=drink)
        visor = 1.0 if (gag and gag[0] == "visier" and gl < 4.2) else 0.0
        glow = max(0.0, 1 - (t - st["bolt"]) / 1.2)
        heads["singer"] = self._mt_singer(img, d, MT_BAND["singer"], MT_STAGE, t, bang, visor, glow,
                                          raise_arm=1.0 if boom else 0.0, drink=drink)
        if gag and gag[0] == "steckenpferd":
            self._mt_hobbyhorse(img, d, -30 + (WIDTH + 60) * gl / MT_GAGS["steckenpferd"], MT_STAGE, t, say)
        # Herold bei Wortbeiträgen
        if talk:
            tl = s["t"] - s.get("talk_t", s["t"])
            hx = min(150.0, -20 + tl * 60)
            self._mt_herald(img, d, hx, MT_STAGE + 4, t)
            if hx >= 150:
                say.append((hx, MT_STAGE - 70, MT_HERALD[int(tl / 4) % len(MT_HERALD)]))
        # Hofnarr nach Liedwechsel
        jt = t - st["jester"]
        if 0 <= jt < 4 and not talk:
            self._mt_jester(img, d, -20 + (WIDTH + 40) * jt / 4, MT_STAGE, t)
        # Publikum
        if o.get("crowd", True):
            self._mt_crowd(img, d, st, s, t, gag, gl)
        if gag and gag[0] == "moench":
            self._mt_monk(img, d, -30 + (WIDTH + 60) * gl / MT_GAGS["moench"], MT_STAGE + 18, t, say)
        # Funken
        alive = []
        for sp in st["sparks"]:
            sp[3] += 160 * dt
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            if t - sp[4] < 1.2 and sp[1] < MT_STAGE + 20:
                alive.append(sp)
                c = int(255 * (1 - (t - sp[4]) / 1.2))
                d.point((sp[0], sp[1]), fill=(255, max(0, c), max(0, c // 3)))
        st["sparks"] = alive[-120:]
        # Drachenfeuer über die Bühne
        if boom and o.get("pyro", "dragon") == "dragon" and 0.4 <= bt < MT_BOOM - 0.4:
            self._mt_breath(img, d, bt, t)
        if boom:
            k = math.sin(min(1.0, bt / MT_BOOM) * math.pi)
            img = ImageChops.add(img, Image.new("RGB", img.size, (int(60 * k), int(26 * k), 0)))
            d = ImageDraw.Draw(img)
        # Gewitter: Blitz in den Helm
        if not demo and self._party_weather()[0] == "thunder" and t >= st["next_bolt"] and not talk:
            st["bolt"], st["next_bolt"] = t, t + st["rng"].uniform(15, 30)
        if 0 <= t - st["bolt"] < 0.25:
            sx, sy = heads["singer"]
            pts, y = [(sx + 30, 0)], 0
            r2 = random.Random(int(st["bolt"] * 10))
            while y < sy - 12:
                y += 14
                pts.append((sx + (sy - y) * 0.3 + r2.uniform(-6, 6), y))
            d.line(pts, fill=(230, 240, 255), width=2)
            img = Image.blend(img, Image.new("RGB", img.size, (220, 230, 255)), 0.18)
            d = ImageDraw.Draw(img)
        if 0.2 <= t - st["bolt"] < 2.2:
            say.append((heads["singer"][0], heads["singer"][1] - 20, "Bzzzt!"))
        # Sprechblasen der Band
        if gag:
            name = gag[0]
            if name == "visier" and 0.8 <= gl < 3.6:
                say.append((heads["singer"][0], heads["singer"][1] - 20, "Mmmpf mmpf!"))
            elif name == "visier" and 3.0 <= gl < 4.8:
                say.append((heads["guitar"][0], heads["guitar"][1] - 22, "Hahaha!"))
            elif name == "solo" and 0.2 <= gl < 2.0:
                say.append((heads["singer"][0], heads["singer"][1] - 20, "Solo!"))
            elif name == "solo" and 5.6 <= gl < 7.6:
                say.append((heads["guitar"][0], heads["guitar"][1] - 22, "PLING! Saite …"))
            elif name == "met" and 2.0 <= gl < 5.0:
                say.append((heads["drums"][0], heads["drums"][1] - 22, "Hups – wo war ich?"))
        if boom and o.get("pyro", "dragon") == "dragon" and 0.6 <= bt < 2.6:
            say.append((heads["singer"][0], heads["singer"][1] - 24, "FEUER!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        return img

    # -- Gäste und Requisiten --------------------------------------------------------------- #
    def _mt_dragon(self, img, d, k, t, bang, breathe=False, peek=False):
        """Drachenkopf: speit vom rechten Turm Feuer bzw. (peek) schaut hinter der Mauer hervor und headbangt mit."""
        if peek:
            x, y = 246, MT_WALL_Y - 18 + (1 - k) * 46
        else:
            x, y = 298, 20 + (1 - k) * 40
        green, dark = (60, 140, 70), (36, 90, 44)
        if y > 58 and not peek:
            return
        self._blob(img, x + 10, y + 26, 22, 34, green, gloss=0.4)                   # Hals
        hy = y + 6 * bang
        self._blob(img, x - 4, hy, 30, 20, green, gloss=0.5)
        self._blob(img, x - 18, hy + 4, 18, 12, green, gloss=0.5)                   # Schnauze
        for side in (0, 1):
            d.polygon([(x + 2 + side * 8, hy - 8), (x + 8 + side * 8, hy - 22), (x + 10 + side * 8, hy - 6)], fill=dark)
        d.ellipse([x - 8, hy - 5, x - 2, hy + 1], fill=(255, 220, 60))
        d.line([(x - 5, hy - 5), (x - 5, hy + 1)], fill=(20, 20, 20))
        if breathe:
            d.chord([x - 28, hy + 2, x - 10, hy + 14], 0, 180, fill=(120, 20, 20))
        for j in range(3):                                                           # Rauch aus den Nüstern
            q = (t * 1.5 + j / 3) % 1.0
            self._blob(img, x - 26 - q * 10, hy - q * 12, 4 + q * 6, 4 + q * 6, (150, 150, 160), alpha=0.5 * (1 - q),
                       flat=True)
        if peek:                                                                     # Mauer davor
            img.paste(self._mt_scene().crop((x - 44, MT_WALL_Y - 10, x + 30, MT_WALL_Y + 40)), (x - 44, MT_WALL_Y - 10))

    def _mt_breath(self, img, d, bt, t):
        """Feuerstoß des Drachen quer über die Bühne (Flammenkegel aus Blobs)."""
        reach = min(1.0, (bt - 0.4) / 0.6)
        x0, y0 = 270, 30
        for j in range(16):
            q = j / 15 * reach
            x = x0 - q * 250
            y = y0 + q * 30 + math.sin(t * 12 + j) * 4
            r = 8 + q * 26
            col = _lerp((255, 240, 160), (255, 80, 20), q)
            self._blob(img, x, y, r, r * 0.8, col, alpha=0.7, flat=True)

    def _mt_lady(self, img, d, gl, say, t):
        """Burgfräulein im linken Turm wirft eine Rose – für den Trommler."""
        cx = (MT_TOWERS[0][0] + MT_TOWERS[0][1]) / 2
        d.rectangle([cx - 4, 38, cx + 4, 50], fill=(250, 210, 120))
        self._blob(img, cx, 44, 7, 7, (240, 210, 180), gloss=0.3)
        d.polygon([(cx - 4, 41), (cx + 4, 41), (cx, 28)], fill=(200, 80, 160))     # Hennin (Spitzhut)
        if 1.4 <= gl < 3.6:
            k = (gl - 1.4) / 2.2
            tx, ty = MT_BAND["drums"], MT_STAGE - 50
            x = cx + (tx - cx) * k
            y = 46 + (ty - 46) * k - math.sin(k * math.pi) * 50
            d.line([(x - 4, y + 2), (x + 4, y - 2)], fill=(40, 120, 40), width=2)
            self._blob(img, x + 4, y - 3, 6, 6, (220, 30, 50), gloss=0.5)
        if 0.4 <= gl < 2.4:
            say.append((cx + 30, 36, "Für den Trommler!"))
        if 3.8 <= gl < 6.4:
            say.append((MT_BAND["drums"], MT_STAGE - 72, "Für mich?!"))

    def _mt_catapult(self, img, d, gl, t, say):
        """Katapult auf dem linken Turm schießt einen Kohlkopf ins Publikum."""
        x, y = 24, 18
        arm = -0.9 if 1.0 <= gl else -0.1
        d.rectangle([x - 10, y, x + 10, y + 4], fill=(110, 70, 40))
        d.line([(x, y), (x + math.cos(arm) * 18, y + math.sin(arm) * 18)], fill=(130, 90, 50), width=3)
        if gl < 1.0:
            self._blob(img, x + 16, y - 2, 8, 8, (120, 180, 80), gloss=0.4)
        elif gl < 3.4:
            k = (gl - 1.0) / 2.4
            bx = x + 16 + (190 - x - 16) * k
            by = y - 2 + (MT_STAGE + 22 - y) * k - math.sin(k * math.pi) * 60
            self._blob(img, bx, by, 9, 9, (120, 180, 80), gloss=0.4)
        else:
            self._blob(img, 190, MT_STAGE + 6, 9, 9, (120, 180, 80), gloss=0.4)
            if gl < 6.4:
                say.append((190, MT_STAGE - 4, "Gemüse!"))

    def _mt_hobbyhorse(self, img, d, x, feet, t, say):
        """Ritter auf dem Steckenpferd galoppiert über die Bühne."""
        hop = abs(math.sin(t * 9)) * 4
        y = feet - hop
        self._mt_legs(img, x, y, y - 26, 6 + 4 * math.sin(t * 9), MT_STEEL)
        self._blob(img, x, y - 40, 20, 26, MT_STEEL, gloss=0.8)
        self._blob(img, x, y - 60, 15, 16, MT_STEEL, gloss=0.9)
        d.line([(x - 6, y - 59), (x + 6, y - 59)], fill=(40, 40, 50), width=2)
        d.line([(x - 14, y - 6), (x + 16, y - 34)], fill=(120, 84, 50), width=3)   # Stecken
        self._blob(img, x + 20, y - 38, 14, 10, (200, 160, 110), gloss=0.3)          # Pferdekopf
        d.line([(x + 14, y - 40), (x + 12, y - 28)], fill=(90, 60, 40), width=3)    # Mähne
        say.append((x, y - 84, "Hü-hott!"))

    def _mt_monk(self, img, d, x, y, t, say):
        """Mönch beim Crowdsurfen, auf Händen über das Publikum getragen."""
        robe, skin = (110, 74, 46), (236, 196, 166)
        y += math.sin(t * 6) * 2
        self._blob(img, x, y, 44, 14, robe, gloss=0.3)
        self._blob(img, x + 26, y - 2, 13, 13, skin, gloss=0.3)
        d.arc([x + 19, y - 9, x + 33, y + 5], 200, 340, fill=(90, 60, 40), width=2)  # Tonsur
        for j in range(4):                                                           # Hände darunter
            hx = x - 18 + j * 12
            d.line([(hx, y + 6), (hx + 2, y + 18)], fill=(30, 22, 26), width=3)
        say.append((x + 26, y - 14, "Halleluja!"))

    def _mt_herald(self, img, d, x, feet, t):
        """Herold mit Wappenrock und Schriftrolle."""
        hip = feet - 26
        self._mt_legs(img, x, feet, hip, 6, (40, 40, 80))
        self._blob(img, x, hip - 14, 24, 30, (40, 60, 150), gloss=0.3)
        d.polygon([(x - 6, hip - 22), (x + 6, hip - 22), (x, hip - 8)], fill=(240, 200, 70))
        skin = (236, 196, 166)
        for side in (-1, 1):
            self._mt_arm(img, (x + side * 10, hip - 24), (x + side * 10, hip - 14), side, (40, 60, 150), skin, skin)
        d.rectangle([x - 10, hip - 22, x + 10, hip - 4], fill=(240, 228, 196))      # Schriftrolle
        for k in range(4):
            d.line([(x - 7, hip - 19 + k * 4), (x + 7, hip - 19 + k * 4)], fill=(120, 80, 60))
        hy = hip - 38
        self._blob(img, x, hy, 15, 16, skin, gloss=0.3)
        d.polygon([(x - 9, hy - 5), (x + 9, hy - 5), (x + 2, hy - 13)], fill=(150, 30, 40))
        d.ellipse([x - 2, hy + 3, x + 2, hy + 6], fill=(90, 20, 20))

    def _mt_jester(self, img, d, x, feet, t):
        """Hofnarr hüpft mit einem Schild „Zugabe!“ über die Bühne."""
        hop = abs(math.sin(t * 10)) * 6
        y = feet - hop
        self._mt_legs(img, x, y, y - 24, 6 + 3 * math.sin(t * 10), (200, 40, 40), boot=(240, 200, 60))
        self._blob(img, x, y - 36, 18, 24, (60, 120, 220), gloss=0.3)
        self._blob(img, x, y - 54, 13, 14, (240, 210, 180), gloss=0.3)
        for side in (-1, 1):
            d.line([(x, y - 60), (x + side * 10, y - 70)], fill=(200, 40, 40) if side < 0 else (240, 200, 60), width=4)
            self._blob(img, x + side * 11, y - 71, 5, 5, (250, 230, 80), gloss=0.5)
        d.line([(x + 8, y - 40), (x + 8, y - 74)], fill=(120, 84, 50), width=2)
        d.rectangle([x - 6, y - 92, x + 34, y - 74], fill=(250, 240, 210))
        d.text((x - 3, y - 90), "Zugabe!", font=self.f_tiny, fill=(160, 30, 30))
