"""Visualisierung „Ostern“ (easter, Mixin EasterVisual): Die Eierfabrik auf der Frühlingswiese. Hühner auf dem
Hühnerhaus legen bei jedem Bassschlag ein Ei auf das Fließband, der Osterhase bemalt jedes Ei, das an ihm vorbeiläuft
(Bassschlag = Stempel, hohe Schläge = Farbtupfer), am Ende purzeln die bunten Eier in den Korb. Beim Höhepunkt rast
das Band, die Eier fliegen und der Hase hechtet hinterher. Bei Wortbeiträgen macht er Pause mit Möhre und
„STREIK“-Schild. Gags: ein Küken schlüpft und will nicht bemalt werden, Hühnerdisco mit Hahn als DJ, Jonglage mit
Rührei und – mit Gänsehaut – die Schokohasen im Regal, die sich im Dunkeln alle zum Betrachter drehen.
"""
import math
import random

ES_FLOOR = VIS_H - 22
ES_BELT_Y = ES_FLOOR - 40               # Oberkante des Fließbands (Eier liegen darauf)
ES_BELT = (46, 266)
ES_BUNNY_X = 156
ES_BASKET_X = 290
ES_HOUSE = (2, 58)                      # Hühnerhaus links
ES_GAGS = {"kueken": 8.0, "schokohasen": 10.0, "disco": 9.0, "jonglage": 7.0}
ES_GAG_FIRST, ES_GAG_PAUSE = 10.0, (12.0, 20.0)
ES_COLORS = [(240, 90, 120), (90, 160, 240), (250, 200, 60), (110, 200, 110), (190, 110, 220), (250, 140, 60)]
ES_BOOM = 4.0


class EasterVisual:
    vis_pastel = None                   # Farbe des zuletzt bemalten Eis (Tastatur „Pastell“)

    def _es_scene(self):
        """Frühlingsmorgen: Himmel, Hügel, Blumen, Hühnerhaus, Fließband mit Rollen, Korb (zwischengespeichert)."""
        if "_es_bg" in self.__dict__:
            return self._es_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([150, 200, 250], np.float32), np.array([250, 230, 200], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        self._blob(img, 262, 34, 30, 30, (255, 236, 150), gloss=0.1)               # Sonne
        self._blob(img, 262, 34, 80, 80, (255, 240, 180), alpha=0.3, flat=True)
        for cx, cy, w in ((60, 26, 50), (130, 40, 40), (200, 20, 34)):              # Wolken
            for k in range(3):
                self._blob(img, cx + k * w / 3, cy - (k == 1) * 6, w / 1.6, w / 2.6, (252, 252, 255), gloss=0.1)
        d.ellipse([-80, ES_FLOOR - 90, 200, ES_FLOOR + 60], fill=(140, 200, 110))  # Hügel
        d.ellipse([120, ES_FLOOR - 70, 420, ES_FLOOR + 70], fill=(120, 186, 96))
        d.rectangle([0, ES_FLOOR - 8, WIDTH, HEIGHT], fill=(110, 176, 86))
        rng = random.Random(5)
        for _ in range(60):                                                         # Gras und Blumen
            x, y = rng.uniform(0, WIDTH), rng.uniform(ES_FLOOR - 30, VIS_H)
            d.line([(x, y), (x + rng.uniform(-2, 2), y - 5)], fill=(80, 150, 60))
        for _ in range(18):
            x, y = rng.uniform(0, WIDTH), rng.uniform(ES_FLOOR - 40, VIS_H - 2)
            c = rng.choice([(250, 250, 250), (250, 220, 60), (240, 140, 180), (180, 160, 240)])
            for a in range(5):
                d.ellipse([x + math.cos(a * 1.26) * 2.5 - 1.6, y + math.sin(a * 1.26) * 2.5 - 1.6,
                           x + math.cos(a * 1.26) * 2.5 + 1.6, y + math.sin(a * 1.26) * 2.5 + 1.6], fill=c)
            d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(250, 200, 40))
        x0, x1 = ES_HOUSE                                                           # Hühnerhaus
        d.rectangle([x0, ES_BELT_Y - 30, x1, ES_FLOOR], fill=(190, 80, 60))
        for y in range(ES_BELT_Y - 26, ES_FLOOR, 7):
            d.line([(x0, y), (x1, y)], fill=(160, 60, 46))
        d.polygon([(x0 - 6, ES_BELT_Y - 30), (x1 + 6, ES_BELT_Y - 30), ((x0 + x1) / 2, ES_BELT_Y - 56)],
                  fill=(120, 70, 40))
        d.ellipse([x0 + 18, ES_BELT_Y - 12, x1 - 18, ES_BELT_Y + 12], fill=(60, 30, 20))
        d.line([(x1, ES_BELT_Y - 2), (ES_BELT[0] + 6, ES_BELT_Y - 2)], fill=(120, 70, 40), width=3)   # Rutsche
        b0, b1 = ES_BELT                                                            # Fließband
        d.rectangle([b0, ES_BELT_Y, b1, ES_BELT_Y + 8], fill=(80, 84, 92))
        d.rectangle([b0 + 4, ES_BELT_Y + 8, b1 - 4, ES_FLOOR], fill=(150, 156, 168))
        for x in range(b0 + 10, b1 - 4, 30):
            d.rectangle([x, ES_BELT_Y + 10, x + 16, ES_BELT_Y + 22], outline=(110, 116, 128))
        for lx in (b0 + 8, b1 - 12):
            d.rectangle([lx, ES_FLOOR - 4, lx + 6, ES_FLOOR + 2], fill=(70, 70, 76))
        bx = ES_BASKET_X                                                            # Korb
        d.chord([bx - 26, ES_FLOOR - 40, bx + 26, ES_FLOOR + 4], 0, 180, fill=(190, 140, 70))
        for k in range(5):
            d.arc([bx - 26, ES_FLOOR - 40 + k * 3, bx + 26, ES_FLOOR + 4 + k * 3], 10, 170, fill=(160, 110, 50))
        d.arc([bx - 22, ES_FLOOR - 64, bx + 22, ES_FLOOR - 4], 180, 360, fill=(170, 120, 60), width=3)
        self._es_bg = img
        return img

    # -- Figuren -------------------------------------------------------------------------- #
    def _es_egg(self, img, d, x, y, col, pattern, rot=0.0, scale=1.0):
        """Ei (unbemalt: weiß); pattern: None, "stripes", "dots", "zigzag"."""
        w, h = 11 * scale, 14 * scale
        self._blob(img, x, y - h / 2, w, h, col, ang=rot, gloss=0.6)
        if pattern == "stripes":
            d.line([(x - w / 2 + 1, y - h / 2), (x + w / 2 - 1, y - h / 2)], fill=(255, 255, 255), width=2)
        elif pattern == "dots":
            for ox, oy in ((-2, -9), (2, -5), (-1, -3)):
                d.ellipse([x + ox * scale - 1, y + oy * scale - 1, x + ox * scale + 1, y + oy * scale + 1],
                          fill=(255, 255, 255))
        elif pattern == "zigzag":
            pts = [(x - w / 2 + 1 + k * w / 5, y - h / 2 + (2 if k % 2 else -2)) for k in range(6)]
            d.line(pts, fill=(255, 255, 255), width=1)

    def _es_bunny(self, img, d, x, y, t, bang, brush=None, pose="paint", jump=0.0):
        """Osterhase hinter dem Band (Oberkörper), lange Ohren wippen im Takt. pose: paint, break, chase, juggle."""
        fur, belly, ear = (170, 150, 130), (240, 230, 214), (240, 180, 190)
        y -= jump
        self._blob(img, x, y - 16, 30, 34, fur, gloss=0.3)
        self._blob(img, x, y - 10, 18, 22, belly, gloss=0.2)
        hy = y - 40 + 2 * bang
        for side in (-1, 1):                                                       # Ohren
            a = side * (0.15 + 0.25 * bang) + math.sin(t * 3 + side) * 0.05
            tip = (x + side * 6 + math.sin(a) * 24, hy - 8 - math.cos(a) * 24)
            self._limb(img, (x + side * 5, hy - 6), tip, 8, fur)
            self._limb(img, (x + side * 5, hy - 8), (tip[0] - math.sin(a) * 4, tip[1] + 4), 4, ear)
        self._blob(img, x, hy, 22, 20, fur, gloss=0.3)
        self._blob(img, x, hy + 5, 12, 8, belly, gloss=0.2)
        for side in (-1, 1):
            d.ellipse([x + side * 5 - 2, hy - 4, x + side * 5 + 2, hy + 1], fill=(30, 24, 24))
            d.line([(x + side * 3, hy + 4), (x + side * 11, hy + 2 + side)], fill=(120, 110, 100))
        d.ellipse([x - 2, hy + 2, x + 2, hy + 5], fill=(240, 130, 150))
        hands = []
        for side in (-1, 1):
            sh = (x + side * 12, y - 26)
            if pose == "break":
                target = (x + side * 4, y - 22 - (side < 0) * 6)
            elif pose == "chase":
                target = (sh[0] + side * 14, sh[1] - 16)
            elif pose == "juggle":
                target = (sh[0] + side * 4, sh[1] - 10 - 6 * abs(math.sin(t * 8 + side)))
            else:
                target = brush if (brush and side > 0) else (sh[0] + side * 6, sh[1] + 14)
            elbow, hand = _ik(sh, target, 10, 10, side)
            self._limb(img, sh, elbow, 6, fur)
            self._limb(img, elbow, hand, 5, fur)
            self._blob(img, hand[0], hand[1], 7, 7, belly, gloss=0.2)
            hands.append(hand)
        if pose == "paint":                                                        # Pinsel
            hx, hy2 = hands[1]
            d.line([(hx, hy2), (hx + 4, hy2 + 10)], fill=(140, 90, 50), width=2)
            d.ellipse([hx + 2, hy2 + 9, hx + 7, hy2 + 14], fill=self.vis_pastel or (240, 90, 120))
        return (x, hy), hands

    def _es_hen(self, img, d, x, y, t, face=1, dance=0.0, rooster=False):
        body = (250, 246, 236) if not rooster else (170, 90, 40)
        bob = abs(math.sin(t * 6)) * 3 * dance
        self._blob(img, x, y - 10 - bob, 22, 16, body, gloss=0.4)
        self._blob(img, x + face * 9, y - 20 - bob, 11, 11, body, gloss=0.4)
        d.polygon([(x + face * 14, y - 21 - bob), (x + face * 19, y - 19 - bob), (x + face * 14, y - 17 - bob)],
                  fill=(250, 170, 40))
        for k in range(3):
            d.ellipse([x + face * (6 + k * 2) - 2, y - 30 - bob + abs(k - 1), x + face * (6 + k * 2) + 2,
                       y - 25 - bob + abs(k - 1)], fill=(230, 40, 40))
        d.point((x + face * 11, y - 22 - bob), fill=(20, 20, 20))
        if rooster:
            for k in range(4):
                d.line([(x - face * 10, y - 12 - bob), (x - face * (16 + k * 2), y - 26 - bob + k * 4)],
                       fill=[(40, 120, 60), (200, 60, 30), (40, 60, 160), (220, 160, 40)][k], width=3)
        for side in (-1, 1):
            lx = x + side * 4 + (math.sin(t * 9 + side) * 3 * dance)
            d.line([(x + side * 4, y - 4 - bob), (lx, y)], fill=(240, 160, 40), width=2)

    def _es_chocobunny(self, img, d, x, y, k_turn, bitten, t, glow):
        """Schokohase im Regal; k_turn 0…1 = dreht sich zum Betrachter (Gesicht, glühende Augen)."""
        choc = (110, 64, 36)
        self._blob(img, x, y - 10, 14, 20, choc, gloss=0.7)
        self._blob(img, x, y - 24, 12, 11, choc, gloss=0.7)
        for side in (-1, 1):
            if bitten and side > 0:
                continue
            self._limb(img, (x + side * 3, y - 28), (x + side * 5, y - 40), 4, choc)
        d.line([(x - 6, y - 4), (x + 6, y - 4)], fill=(220, 40, 50), width=2)        # Schleife
        if k_turn > 0.2:
            for side in (-1, 1):
                ex = x + side * 2.5
                if glow:
                    self._blob(img, ex, y - 25, 6, 5, (255, 60, 40), alpha=round(0.6 * k_turn, 2), flat=True)
                d.ellipse([ex - 1.2, y - 26.2, ex + 1.2, y - 23.8], fill=(255, 80, 60) if glow else (250, 240, 220))

    # -- Ablauf ------------------------------------------------------------------------------ #
    @vis_style("easter")
    def vis_easter(self, s, o, color):
        t = s["t"]
        img = self._es_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("easter", lambda: {"beats": s["beats"], "eggs": [], "basket": 0, "slow": s["level"],
                                              "fast": s["level"], "boom": -99.0, "gag": None, "order": [],
                                              "next_gag": t + ES_GAG_FIRST, "rng": random.Random(11), "start": t,
                                              "paint_i": 0, "splat": None, "flying": []})
        if demo and not st["eggs"]:                                                 # Vorschau: Band schon voll
            for i, x in enumerate(range(ES_BELT[0] + 10, ES_BELT[1] - 10, 34)):
                st["eggs"].append({"x": float(x), "col": ES_COLORS[i % 6] if x > ES_BUNNY_X else None,
                                   "pat": ("stripes", "dots", "zigzag")[i % 3] if x > ES_BUNNY_X else None})
            st["basket"] = 9
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        playing = (s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        bang = math.sin(math.pi * min(1.0, (t - s.get("beat_t", t)) / (period * 0.6))) if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < ES_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= ES_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*ES_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(ES_GAGS), len(ES_GAGS))
            name = st["order"].pop(0)
            if name == "schokohasen" and not o.get("spooky", True):
                name = st["order"].pop(0) if st["order"] else "kueken"
            st["gag"] = gag = (name, t)
        gl = t - gag[1] if gag else 0.0
        say = []
        # Hühner legen Eier (Bass), Band läuft im Takt
        speed = (0 if not playing else 26 / period * 0.5) * (4.0 if boom else 1.0)
        if playing and new_beat and s["bass"] > 0.5 and not boom:
            if not st["eggs"] or st["eggs"][-1]["x"] > ES_BELT[0] + 26:
                st["eggs"].append({"x": float(ES_BELT[0] + 6), "col": None, "pat": None})
        for e in st["eggs"]:
            e["x"] += speed * dt
            if e["col"] is None and abs(e["x"] - (ES_BUNNY_X + 12)) < 8 and playing and not boom:
                if not (gag and gag[0] == "kueken" and e.get("chick")):
                    i = st["paint_i"]
                    e["col"], e["pat"] = ES_COLORS[i % 6], ("stripes", "dots", "zigzag", None)[i % 4]
                    st["paint_i"] += 1
                    self.vis_pastel = e["col"]
        done = [e for e in st["eggs"] if e["x"] > ES_BELT[1] - 4]
        for e in done:
            if boom:                                                                # fliegt im Bogen weg
                st["flying"].append({"x": e["x"], "t": t, "col": e["col"] or (250, 250, 245), "pat": e["pat"],
                                     "vx": st["rng"].uniform(40, 120), "vy": st["rng"].uniform(-160, -90)})
            else:
                st["basket"] = min(30, st["basket"] + 1)
        st["eggs"] = [e for e in st["eggs"] if e["x"] <= ES_BELT[1] - 4]
        # Hühner auf dem Hühnerhaus (legen auf jeden Schlag mit Hopser)
        hop = max(0.0, 1 - (t - s.get("beat_t", -9)) / 0.2) if playing else 0.0
        disco = gag and gag[0] == "disco"
        if not disco:
            self._es_hen(img, d, 18, ES_BELT_Y - 30 - hop * 3, t, 1)
            self._es_hen(img, d, 42, ES_BELT_Y - 30, t, 1, dance=0.3 if playing else 0)
        # Korb mit Eiern
        rng = random.Random(3)
        for i in range(min(st["basket"], 24)):
            bx = ES_BASKET_X - 18 + (i * 7) % 36 + rng.uniform(-2, 2)
            by = ES_FLOOR - 22 - (i // 6) * 5
            self._es_egg(img, d, bx, by, ES_COLORS[i % 6], ("stripes", "dots", "zigzag", None)[i % 4], scale=0.8)
        # Hase
        pose, jump, bx = "paint", 0.0, ES_BUNNY_X
        if talk:
            pose = "break"
        elif boom:
            pose, bx = "chase", ES_BUNNY_X + 40 * math.sin(min(1.0, bt / ES_BOOM) * math.pi)
            jump = abs(math.sin(bt * 6)) * 14
        elif gag and gag[0] == "jonglage":
            pose = "juggle"
        brush = (ES_BUNNY_X + 12, ES_BELT_Y - 8 - 4 * bang) if pose == "paint" else None
        head, hands = self._es_bunny(img, d, bx, ES_BELT_Y + 2, t, bang, brush, pose, jump)
        d.rectangle([ES_BELT[0], ES_BELT_Y, ES_BELT[1], ES_BELT_Y + 8], fill=(80, 84, 92))   # Band vor dem Hasen
        off = (t * speed) % 12
        for x in range(int(ES_BELT[0] + off), ES_BELT[1], 12):
            d.line([(x, ES_BELT_Y + 1), (x, ES_BELT_Y + 7)], fill=(110, 114, 124))
        for e in st["eggs"]:
            wob = math.sin(t * 30) * 3 if boom else 0.0
            if gag and gag[0] == "kueken" and e.get("chick"):
                continue
            self._es_egg(img, d, e["x"], ES_BELT_Y - (abs(math.sin(t * 20 + e["x"])) * 6 if boom else 0),
                         e["col"] or (252, 250, 244), e["pat"], rot=wob)
        for f in list(st["flying"]):                                                # fliegende Eier
            k = t - f["t"]
            x, y = f["x"] + f["vx"] * k, ES_BELT_Y + f["vy"] * k + 260 * k * k
            if y > ES_FLOOR + 10:
                st["flying"].remove(f)
                st["basket"] = min(30, st["basket"] + 1)
                continue
            self._es_egg(img, d, x, y, f["col"], f["pat"], rot=k * 400)
        if talk:                                                                    # Pause: Möhre und Schild
            hx, hy = hands[0]
            d.polygon([(hx - 2, hy - 2), (hx + 4, hy - 2), (hx + 1, hy + 16)], fill=(250, 130, 30))
            d.line([(hx + 1, hy - 2), (hx - 2, hy - 8)], fill=(80, 160, 60), width=2)
            d.line([(bx + 34, ES_BELT_Y), (bx + 34, ES_BELT_Y - 46)], fill=(140, 100, 60), width=3)
            d.rectangle([bx + 6, ES_BELT_Y - 62, bx + 74, ES_BELT_Y - 44], fill=(250, 246, 230), outline=(140, 100, 60))
            d.text((bx + 11, ES_BELT_Y - 60), "STREIK", font=self.f_small_b, fill=(200, 40, 40))
            tl = s["t"] - s.get("talk_t", s["t"])
            if tl < 3:
                say.append((head[0], head[1] - 26, "Mampf. Pause!"))
        if boom and bt < 2.6:
            say.append((head[0], head[1] - 30, "Halt! Zu schnell!"))
        # Gags
        if gag:
            name = gag[0]
            if name == "kueken":
                self._es_gag_chick(img, d, st, gl, t, say)
            elif name == "jonglage":
                self._es_gag_juggle(img, d, st, gl, t, hands, head, say)
            elif name == "disco":
                self._es_gag_disco(img, d, gl, t, s, say)
            elif name == "schokohasen":
                img = self._es_gag_choco(img, gl, t, s, say, o)
                d = ImageDraw.Draw(img)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _es_gag_chick(self, img, d, st, gl, t, say):
        """Ein Ei wackelt, ein Küken schlüpft („Nicht anmalen!“) und läuft davon."""
        x = ES_BUNNY_X - 20
        if gl < 1.0:
            for e in st["eggs"]:
                if abs(e["x"] - x) < 30 and e["col"] is None:
                    e["chick"] = True
                    break
        if gl < 2.4:
            wob = math.sin(t * 30) * 12 * min(1.0, gl)
            self._es_egg(img, d, x, ES_BELT_Y, (252, 250, 244), None, rot=wob)
            if gl > 1.6:
                d.line([(x - 4, ES_BELT_Y - 8), (x, ES_BELT_Y - 5), (x + 4, ES_BELT_Y - 9)], fill=(90, 80, 70))
            return
        k = gl - 2.4
        cx = x - max(0.0, k - 2.2) * 70
        cy = ES_BELT_Y - 8 - abs(math.sin(t * 12)) * (4 if k > 2.2 else 0)
        if k < 2.2:                                                                 # Schalenhälften
            self._blob(img, x - 6, ES_BELT_Y - 3, 9, 7, (252, 250, 244), gloss=0.4)
            self._blob(img, x + 6, ES_BELT_Y - 3, 9, 7, (252, 250, 244), gloss=0.4)
        self._blob(img, cx, cy, 13, 12, (255, 220, 60), gloss=0.4)
        d.polygon([(cx - 6, cy - 1), (cx - 10, cy + 1), (cx - 6, cy + 2)], fill=(250, 150, 40))
        d.point((cx - 3, cy - 3), fill=(20, 20, 20))
        if 0.4 <= k < 2.6:
            say.append((cx, cy - 14, "Nicht anmalen!"))

    def _es_gag_juggle(self, img, d, st, gl, t, hands, head, say):
        """Er jongliert drei Eier – eins fällt: Rührei."""
        cx = head[0]
        for i in range(3):
            if i == 2 and gl > 4.0:
                continue
            ph = t * 4 + i * 2.1
            x = cx + math.cos(ph) * 16
            y = head[1] - 20 - abs(math.sin(ph)) * 26
            self._es_egg(img, d, x, y, ES_COLORS[i], ("dots", "stripes", "zigzag")[i], rot=ph * 60)
        if 4.0 <= gl < 4.6:
            k = (gl - 4.0) / 0.6
            self._es_egg(img, d, cx + 10, head[1] - 20 + k * (ES_FLOOR - head[1] + 14), ES_COLORS[2], "zigzag")
        if gl >= 4.6:
            self._blob(img, cx + 12, ES_FLOOR - 2, 30, 8, (255, 250, 240), gloss=0.2)
            self._blob(img, cx + 14, ES_FLOOR - 3, 10, 6, (255, 200, 40), gloss=0.5)
            if gl < 6.6:
                say.append((head[0], head[1] - 26, "Rührei …"))
        elif gl > 0.6:
            say.append((head[0], head[1] - 70, "Ganz einfach!"))

    def _es_gag_disco(self, img, d, gl, t, s, say):
        """Hühnerdisco: Spiegelkugel, drei Hühner tanzen in einer Reihe, der Hahn legt auf dem Dach auf."""
        bx, by = 150, 22
        d.line([(bx, 0), (bx, by - 8)], fill=(120, 120, 130))
        self._blob(img, bx, by, 16, 16, (200, 210, 230), gloss=0.9)
        rng = random.Random(int(t * 4))
        for _ in range(16):
            x, y = rng.uniform(0, WIDTH), rng.uniform(30, ES_FLOOR)
            d.rectangle([x, y, x + 2, y + 2], fill=_hue(rng.random(), 0.5, 1.0))
        self._es_hen(img, d, 30, ES_BELT_Y - 30, t, 1, rooster=True)
        d.arc([20, ES_BELT_Y - 64, 40, ES_BELT_Y - 46], 180, 360, fill=(40, 40, 50), width=2)   # Kopfhörer
        for i in range(3):
            x = 90 + i * 70 - min(60.0, max(0.0, 2 - gl) * 30)
            self._es_hen(img, d, x, ES_FLOOR + 4, t + i * 0.3, 1 if int(t * 2) % 2 else -1, dance=1.0)
        if 1.0 <= gl < 4.0:
            say.append((30, ES_BELT_Y - 70, "Kikeriki – Bass!"))
        elif 5.0 <= gl < 7.5:
            say.append((160, ES_FLOOR - 40, "Gack-gack-gack!"))

    def _es_gag_choco(self, img, gl, t, s, say, o):
        """Schokohasen im Regal (Gänsehaut): wippen, im Dunkeln drehen sich alle zum Betrachter, danach fehlt einem
        ein Ohr. Ist es draußen warm (Wetterseite > 20 °C), schmilzt einer."""
        d = ImageDraw.Draw(img)
        x0, y0 = 70, 70
        d.rectangle([x0 - 6, y0, x0 + 150, y0 + 5], fill=(140, 96, 56))
        for x in (x0 - 4, x0 + 146):
            d.line([(x, y0 + 5), (x - 6, y0 + 20)], fill=(120, 80, 46), width=2)
        dark = 0.0
        if 3.0 <= gl < 6.4:
            dark = min(1.0, (gl - 3.0) / 0.6, (6.4 - gl) / 0.4)
        turn = min(1.0, max(0.0, (gl - 3.4) / 0.8)) if gl < 6.4 else 0.0
        temp = self._party_weather()[1]
        warm = temp is not None and temp > 20
        for i in range(5):
            x = x0 + 10 + i * 30
            bob = abs(math.sin(t * 6 + i)) * 3 if gl < 3.0 else 0.0
            bitten = i == 2 and gl >= 6.4
            if warm and i == 4 and gl >= 7.0:
                self._blob(img, x, y0 - 2, 18, 6, (110, 64, 36), gloss=0.6)
                continue
            self._es_chocobunny(img, d, x, y0 - bob, turn, bitten, t, glow=True)
        if dark > 0:
            img = Image.blend(img, Image.new("RGB", img.size, (10, 6, 20)), 0.75 * dark)
            d = ImageDraw.Draw(img)
            for i in range(5):                                                      # nur die Augen leuchten
                x = x0 + 10 + i * 30
                for side in (-1, 1):
                    d.ellipse([x + side * 2.5 - 1.5, y0 - 27, x + side * 2.5 + 1.5, y0 - 23], fill=(255, 70, 50))
        if 6.6 <= gl < 8.6:
            say.append((x0 + 76, y0 - 44, "Knack!"))
        elif 8.6 <= gl < 10 and warm:
            say.append((x0 + 130, y0 - 44, "Mir ist warm …"))
        return img
