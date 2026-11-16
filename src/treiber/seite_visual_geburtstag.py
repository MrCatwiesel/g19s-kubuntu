"""Visualisierung „Geburtstag“ (birthday, Mixin BirthdayVisual): Die lebende Torte. Auf dem Festtisch steht eine
zweistöckige Torte mit Gesicht, die mitsingt (der Mund öffnet sich mit der Lautstärke) und im Takt hüpft; die Kerzen
flackern auf hohe Schläge. Daneben tanzt das Geburtstagskind mit Partyhut, rechts hüpfen die Geschenke. Name und
Kerzenzahl kommen aus der Geburtstagsliste der Überraschungsparty (ab 13 Jahren als Zahlenkerzen).
Höhepunkt: Konfettikanonen, die Kerzen werden zu Wunderkerzen. Wortbeitrag: Die Torte klopft ans Glas und hält eine
Rede. Gags: Älterwerden im Zeitraffer, Auspusten mit Scherzkerzen, die Torte will nicht angeschnitten werden,
Geschenk in Geschenk in Geschenk (Socken) und ein Luftballon, der zu groß wird.
"""
import math
import random

BD_FLOOR = VIS_H - 18
BD_TABLE = (96, 246, BD_FLOOR - 46)     # Tisch: x0, x1, Oberkante
BD_CAKE_X = 170
BD_KID_X = 56
BD_GAGS = {"zeitraffer": 10.0, "auspusten": 8.0, "anschneiden": 8.0, "geschenk": 8.0, "ballon": 7.0}
BD_GAG_FIRST, BD_GAG_PAUSE = 8.0, (12.0, 20.0)
BD_BOOM = 4.0
BD_COLORS = [(230, 60, 80), (250, 200, 50), (60, 160, 230), (110, 200, 90), (220, 110, 220), (250, 140, 60)]
BD_BALLOONS = [(104, 92, (230, 60, 80)), (124, 78, (60, 160, 230)), (238, 86, (250, 200, 50))]
BD_YEARS = ([0, 0.15, 0.3, 0.45, 0.6, 0.8, 1.0], [0, 3, 10, 18, 35, 70, 99])   # Altersstufe → Jahre
BD_AGE_ADULT = 0.6                      # Altersstufe 0 Baby … 0,6 erwachsen … 1 sehr alt


class BirthdayVisual:
    vis_candle = None                   # Kerzenschein für die Tastatur

    def _bd_room(self, banner):
        cache = self.__dict__.get("_bd_bg")
        if cache and cache[0] == banner:
            return cache[1]
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([250, 214, 180], np.float32), np.array([236, 170, 150], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(21)
        for _ in range(26):                                                         # Tupfen an der Wand
            x, y = rng.uniform(0, WIDTH), rng.uniform(56, BD_FLOOR - 20)
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=rng.choice(BD_COLORS))
        for y in range(BD_FLOOR, HEIGHT, 7):                                        # Holzboden
            d.rectangle([0, y, WIDTH, y + 6], fill=(170, 116, 70) if (y // 7) % 2 else (158, 106, 62))
        d.rectangle([0, BD_FLOOR - 6, WIDTH, BD_FLOOR], fill=(250, 244, 236))
        pts = [(4 + k * (WIDTH - 8) / 16, 12 + 9 * math.sin(math.pi * k / 16)) for k in range(17)]
        d.line(pts, fill=(90, 70, 60))
        for k, (x, y) in enumerate(pts[:-1]):
            d.polygon([(x + 2, y), (x + 16, y + 1), (x + 9, y + 13)], fill=BD_COLORS[k % 6])
        font = load_font(15, bold=True)
        w = d.textlength(banner, font=font) + 22
        bx = (WIDTH - w) / 2
        d.rounded_rectangle([bx, 28, bx + w, 48], radius=5, fill=(255, 250, 240), outline=(230, 60, 100), width=2)
        d.text((bx + 11, 29), banner, font=font, fill=(200, 40, 80))
        x0, x1, ty = BD_TABLE                                                       # Tisch mit Decke
        for lx in (x0 + 8, x1 - 12):
            d.rectangle([lx, ty, lx + 5, BD_FLOOR], fill=(120, 76, 44))
        d.polygon([(x0, ty), (x1, ty), (x1 + 6, ty + 16), (x0 - 6, ty + 16)], fill=(250, 250, 255))
        for x in range(x0 - 6, x1 + 6, 10):
            d.chord([x, ty + 10, x + 10, ty + 22], 0, 180, fill=(250, 250, 255))
            d.ellipse([x + 4, ty + 18, x + 6, ty + 20], fill=(230, 60, 100))
        self._bd_bg = (banner, img)
        return img

    # -- Figuren -------------------------------------------------------------------------- #
    def _bd_person(self, img, d, x, y, t, a, pose=0, hat=True, cheeks=0.0, arm_to=None, sit=False):
        """Geburtstagskind; a = Altersstufe (0 Baby, 0,2 Kind, 0,4 Teenager, 0,6 erwachsen, 1 sehr alt).
        Gibt (Kopfmitte, Hände) zurück."""
        h = (34 + 140 * a if a < 0.3 else 76 + 20 * (a - 0.3)) if a < 0.6 else 82 - 12 * max(0.0, a - 0.75) / 0.25
        bend = max(0.0, (a - 0.8) / 0.2) * 0.25
        head_r = max(7.0, h * (0.2 - 0.07 * min(1.0, a / 0.5)))
        skin = (246, 206, 176)
        hair = (110, 70, 40) if a < 0.7 else ((150, 140, 130) if a < 0.85 else (230, 230, 230))
        shirt = (60, 140, 220) if a >= 0.15 else (250, 250, 250)
        leg = h * 0.38
        hip = (x, y - leg)
        for side in (-1, 1):
            step = (math.sin(t * 6 + side) * 3 if pose % 2 else 0)
            self._limb(img, (hip[0] + side * h * 0.05, hip[1]), (x + side * h * 0.07 + step, y - 2), max(3, h * 0.07),
                       (60, 60, 90) if a >= 0.15 else (250, 250, 250))
            d.ellipse([x + side * h * 0.07 + step - 4, y - 4, x + side * h * 0.07 + step + 4, y], fill=(40, 30, 30))
        neck = (x + bend * h * 0.4, hip[1] - h * 0.32)
        self._blob(img, (hip[0] + neck[0]) / 2, (hip[1] + neck[1]) / 2, h * 0.22, h * 0.36, shirt, gloss=0.3,
                   ang=bend)
        hands = []
        for side in (-1, 1):
            sh = (neck[0] + side * h * 0.09, neck[1] + 3)
            up = (pose + (side > 0)) % 2
            if arm_to and side > 0:
                target = arm_to
            elif a > 0.8:
                target = (sh[0] + side * 6, sh[1] + h * 0.26)
            else:
                target = (sh[0] + side * h * 0.2, sh[1] - (h * 0.22 if up else -h * 0.1))
            elbow, hand = _ik(sh, target, h * 0.15, h * 0.15, side)
            self._limb(img, sh, elbow, max(3, h * 0.06), shirt)
            self._limb(img, elbow, hand, max(2.5, h * 0.05), skin)
            hands.append(hand)
        if a > 0.85:                                                                # Gehstock
            hx, hy = hands[0]
            d.line([(hx, hy), (hx - 3, y)], fill=(110, 70, 40), width=2)
            d.arc([hx - 4, hy - 4, hx + 4, hy + 4], 180, 360, fill=(110, 70, 40), width=2)
        hc = (neck[0] + bend * 6, neck[1] - head_r * 0.9)
        self._blob(img, hc[0], hc[1] - head_r * 0.2, head_r * 2.15, head_r * 1.7, hair, gloss=0.3)
        self._blob(img, hc[0], hc[1], head_r * 1.9, head_r * 2.0, skin, gloss=0.3)
        if a < 0.85 and a > 0.1:
            d.chord([hc[0] - head_r, hc[1] - head_r * 1.05, hc[0] + head_r, hc[1] - head_r * 0.1], 180, 360, fill=hair)
        for side in (-1, 1):
            ex = hc[0] + side * head_r * 0.38
            d.ellipse([ex - 1.5, hc[1] - 2, ex + 1.5, hc[1] + 1], fill=(30, 24, 24))
            if cheeks:
                self._blob(img, hc[0] + side * head_r * 0.55, hc[1] + head_r * 0.35, head_r * 0.8 * cheeks,
                           head_r * 0.7 * cheeks, (250, 180, 170), gloss=0.4)
        if a > 0.65:                                                                # Brille
            for side in (-1, 1):
                ex = hc[0] + side * head_r * 0.38
                d.ellipse([ex - 3.5, hc[1] - 3.5, ex + 3.5, hc[1] + 2.5], outline=(60, 50, 50))
        if cheeks < 0.3:
            d.arc([hc[0] - 3, hc[1] + 2, hc[0] + 3, hc[1] + head_r * 0.5], 10, 170, fill=(160, 60, 60))
        else:
            d.ellipse([hc[0] - 1.5, hc[1] + 3, hc[0] + 1.5, hc[1] + 6], fill=(160, 60, 60))
        if hat:
            hy = hc[1] - head_r * 0.8
            d.polygon([(hc[0] - head_r * 0.6, hy), (hc[0] + head_r * 0.6, hy), (hc[0] + 2, hy - head_r * 1.5)],
                      fill=(230, 60, 120))
            for k in range(3):
                d.ellipse([hc[0] - 4 + k * 3, hy - 4 - k * 4, hc[0] - 2 + k * 3, hy - 2 - k * 4], fill=(250, 220, 60))
            self._blob(img, hc[0] + 2, hy - head_r * 1.55, 5, 5, (250, 220, 60), gloss=0.4)
        return hc, hands

    def _bd_cake(self, img, d, x, y, t, mouth, look, eyes=1.0, hop=0.0, n_candles=5, age=None, lit=None,
                 spark=False, shock=0.0):
        """Torte; y = Unterkante. lit: Liste der Kerzen, die brennen (None = alle)."""
        y -= hop
        cream, sponge, top = (252, 240, 230), (240, 170, 190), (250, 120, 160)
        self._blob(img, x, y - 2, 86, 8, (230, 230, 236), gloss=0.6)                 # Teller
        d.rounded_rectangle([x - 36, y - 36, x + 36, y - 2], radius=6, fill=sponge)
        d.rounded_rectangle([x - 24, y - 60, x + 24, y - 34], radius=6, fill=sponge)
        for tw, ty in ((36, y - 36), (24, y - 60)):                                  # Zuckerguss mit Tropfen
            d.rounded_rectangle([x - tw, ty - 2, x + tw, ty + 5], radius=4, fill=top)
            for k in range(int(tw / 5)):
                dx = x - tw + 4 + k * 10
                d.ellipse([dx - 2.5, ty + 2, dx + 2.5, ty + 7 + (k * 7 % 5)], fill=top)
        for k in range(7):                                                          # Streusel
            sx = x - 30 + k * 10
            d.line([(sx, y - 9 - (k % 2) * 3), (sx + 3, y - 8 - (k % 2) * 3)], fill=BD_COLORS[k % 6], width=2)
        fy = y - 22                                                                 # Gesicht
        for side in (-1, 1):
            ex = x + side * 12
            r = 5 + 2 * shock
            d.ellipse([ex - r, fy - 6 - r * eyes + 1, ex + r, fy - 6 + r * eyes], fill=(255, 255, 255),
                      outline=(120, 60, 70))
            if eyes > 0.3:
                d.ellipse([ex + look * 2 - 2, fy - 7, ex + look * 2 + 2, fy - 3], fill=(40, 24, 30))
            self._blob(img, x + side * 22, fy + 3, 9, 6, (250, 150, 170), gloss=0.2)
        mh = 2 + mouth * 10
        d.chord([x - 9, fy - mh / 2 + 2, x + 9, fy + 2 + mh], 0, 180, fill=(120, 30, 50))
        d.line([(x - 9, fy + 2), (x + 9, fy + 2)], fill=(120, 30, 50), width=2)
        if mouth > 0.3:
            self._blob(img, x, fy + 2 + mh * 0.7, 8, 4, (240, 100, 120), gloss=0.3)
        tops = []                                                                   # Kerzen
        if age is not None and age >= 13:
            font = load_font(22, bold=True)
            txt = str(age)
            w = d.textlength(txt, font=font)
            cx = x - w / 2
            for i, ch in enumerate(txt):
                cw = d.textlength(ch, font=font)
                d.text((cx + 1, y - 86 + 1), ch, font=font, fill=(150, 60, 90))
                d.text((cx, y - 86), ch, font=font, fill=(250, 200, 220))
                tops.append((cx + cw / 2, y - 86))
                cx += cw
        else:
            n = max(1, min(12, n_candles))
            for i in range(n):
                cx = x - 18 + (36 * i / (n - 1) if n > 1 else 18)
                cy = y - 62 - (4 if i % 2 else 0)
                d.rectangle([cx - 1.5, cy - 12, cx + 1.5, cy], fill=BD_COLORS[i % 6])
                tops.append((cx, cy - 12))
        for i, (cx, cy) in enumerate(tops):
            if lit is not None and i not in lit:
                d.line([(cx, cy - 2), (cx + math.sin(t * 3 + i) * 2, cy - 9)], fill=(160, 160, 170))   # Rauch
                continue
            fl = 1 + 0.25 * math.sin(t * 23 + i * 2.1)
            if spark:
                for k in range(6):
                    a = t * 9 + k * 1.05 + i
                    r = 4 + (t * 40 + k * 7) % 9
                    d.point((cx + math.cos(a) * r, cy - 3 + math.sin(a) * r), fill=(255, 250, 200))
            d.polygon([(cx - 2.5, cy - 1), (cx + 2.5, cy - 1), (cx, cy - 8 * fl)], fill=(255, 180, 40))
            d.ellipse([cx - 1.2, cy - 4, cx + 1.2, cy - 1], fill=(255, 250, 200))
        return tops

    def _bd_gift(self, d, x, y, w, col, ribbon, lid=0.0):
        d.rectangle([x - w / 2, y - w * 0.8, x + w / 2, y], fill=col)
        d.rectangle([x - 2, y - w * 0.8, x + 2, y], fill=ribbon)
        ly = y - w * 0.8 - lid
        d.rectangle([x - w / 2 - 2, ly - 5, x + w / 2 + 2, ly], fill=col)
        d.rectangle([x - 2, ly - 5, x + 2, ly], fill=ribbon)
        d.ellipse([x - 7, ly - 10, x - 1, ly - 4], outline=ribbon, width=2)
        d.ellipse([x + 1, ly - 10, x + 7, ly - 4], outline=ribbon, width=2)

    # -- Ablauf ------------------------------------------------------------------------------ #
    @vis_style("birthday")
    def vis_birthday(self, s, o, color):
        t = s["t"]
        names, age = self._pt_people()
        img = self._bd_room(_pt_banner(names)).copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("birthday", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                                "boom": -99.0, "gag": None, "order": [], "pose": 0,
                                                "next_gag": t + BD_GAG_FIRST, "rng": random.Random(41), "start": t,
                                                "conf": [], "hats": s.get("hats", 0), "dim": -1})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
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
        boom = 0 <= bt < BD_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= BD_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*BD_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(BD_GAGS), len(BD_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["pose"] += 1
        if playing and new_hat:
            st["dim"] = st["rng"].randrange(12)
        say = []
        n_candles = age if age is not None else 5
        # Luftballons
        for i, (bx, by, col) in enumerate(BD_BALLOONS):
            if gname == "ballon" and i == 0:
                continue
            yy = by + math.sin(t * 1.5 + i) * 3 - bang * 3 * (i % 2)
            sx = BD_TABLE[0] + 6 if bx < BD_CAKE_X else BD_TABLE[1] - 8
            d.line([(bx, yy + 13), (bx + 2, yy + 30), (sx, BD_TABLE[2])], fill=(140, 120, 120))
            self._blob(img, bx, yy, 20, 25, col, gloss=0.7)
        # Geschenke rechts (hüpfen im Takt)
        gx = 280
        if gname != "geschenk":
            for k, (w, c, r) in enumerate(((30, (60, 160, 230), (250, 220, 60)), (22, (230, 60, 80), (250, 250, 250)))):
                hopk = bang * 4 if (st["pose"] + k) % 2 and playing else 0
                self._bd_gift(d, gx + (k * 6), BD_FLOOR - k * 24 - hopk, w, c, r)
        # Torte
        cx = BD_CAKE_X
        hop = abs(bang) * 5 if playing else 0.0
        mouth = min(1.0, level * 1.5) if playing else 0.0
        look = math.sin(t * 0.8)
        lit = None
        shock = 0.0
        if gname == "anschneiden":
            shock = 1.0 if 2.0 <= gl < 6.0 else 0.0
            look = -1.0
            if 3.4 <= gl < 6.4:
                cx = BD_CAKE_X + min(1.0, (gl - 3.4) / 0.8) * 50 - max(0.0, gl - 5.6) / 0.8 * 50
                hop = abs(math.sin(gl * 9)) * 10
        if gname == "auspusten":
            if 2.6 <= gl < 3.6:
                lit = []
            elif 3.6 <= gl < 5.4:
                lit = list(range(int((gl - 3.6) / 1.8 * 13) + 1))
            elif 5.4 <= gl < 5.8:
                lit = []
            mouth = 0.9 if gl >= 5.8 else mouth
        if talk:
            mouth = 0.6 * abs(math.sin(t * 9)) if t - s.get("talk_t", t) < 6 else 0.0
        if 0 <= st["dim"] and playing and t - s.get("hat_t", -9) < 0.12 and lit is None:
            lit = [i for i in range(14) if i != st["dim"]]
        tops = self._bd_cake(img, d, cx, BD_TABLE[2] + 2, t, mouth, look, hop=hop, n_candles=n_candles, age=age,
                             lit=lit, spark=boom, shock=shock)
        if talk:                                                                    # Rede mit Glas und Gabel
            tl = t - s.get("talk_t", t)
            gx2, gy2 = cx + 52, BD_TABLE[2] - 2
            d.polygon([(gx2 - 6, gy2 - 22), (gx2 + 6, gy2 - 22), (gx2 + 4, gy2 - 6), (gx2 - 4, gy2 - 6)],
                      fill=(220, 230, 250), outline=(150, 160, 180))
            d.line([(gx2, gy2 - 6), (gx2, gy2)], fill=(150, 160, 180), width=2)
            d.line([(gx2 - 7, gy2), (gx2 + 7, gy2)], fill=(150, 160, 180), width=2)
            tap = abs(math.sin(t * 14)) * 4 if tl < 1.6 else 0
            d.line([(gx2 + 22, gy2 - 30), (gx2 + 7, gy2 - 16 - tap)], fill=(190, 190, 200), width=2)
            if tl < 1.6:
                say.append((gx2 + 10, gy2 - 40, "Kling, kling!"))
            elif tl < 5.0:
                say.append((cx, BD_TABLE[2] - 92, "Eine kleine Rede …"))
        # Geburtstagskind
        a = BD_AGE_ADULT
        kx = BD_KID_X
        cheeks, arm_to = 0.0, None
        if gname == "zeitraffer":
            if gl < 1.2:
                a = BD_AGE_ADULT * (1 - gl / 1.2)
            elif gl < 7.0:
                a = (gl - 1.2) / 5.8
            elif gl < 8.6:
                a = 1.0
            else:
                a = BD_AGE_ADULT
        if gname == "auspusten":
            kx = BD_KID_X + min(1.0, gl / 1.0) * 40 if gl < 7.0 else BD_KID_X + 40 - (gl - 7.0) * 40
            cheeks = min(1.0, max(0.0, (gl - 1.2) / 1.0)) if gl < 2.7 else (0.6 if 3.8 <= gl < 5.4 else 0.0)
        if gname == "anschneiden":
            kx = BD_KID_X + min(1.0, gl / 1.2) * 40 if gl < 6.6 else BD_KID_X + 40 - (gl - 6.6) * 28
            arm_to = (kx + 26, BD_TABLE[2] - 34)
        if gname == "ballon":
            arm_to = (kx + 18, BD_FLOOR - 64)
        jump = abs(math.sin(bt * 8)) * 10 if boom else 0.0
        head, hands = self._bd_person(img, d, kx, BD_FLOOR - jump, t, a, pose=st["pose"] if playing else 0,
                                      cheeks=cheeks, arm_to=arm_to)
        if gname == "zeitraffer":
            yrs = int(round(np.interp(a, *BD_YEARS))) if gl < 8.6 else (age or 35)
            d.rounded_rectangle([kx - 22, 54, kx + 22, 74], radius=4, fill=(255, 255, 255), outline=(120, 120, 130))
            d.text((kx - 18, 56), f"{yrs:>2} J.", font=self.f_small_b, fill=(200, 40, 80))
            if 7.0 <= gl < 8.6:
                say.append((head[0] + 20, head[1] - 26, "Ich fühl mich wie 18!"))
            elif 8.6 <= gl < 9.2:
                for k in range(8):
                    a2 = k * 0.785 + gl * 6
                    d.line([(head[0] + math.cos(a2) * 10, head[1] + math.sin(a2) * 10),
                            (head[0] + math.cos(a2) * 18, head[1] + math.sin(a2) * 18)], fill=(255, 230, 80), width=2)
        elif gname == "auspusten":
            if 2.6 <= gl < 3.0:
                for k in range(4):
                    d.line([(head[0] + 12 + k * 8, head[1] + 2), (head[0] + 18 + k * 8, head[1] + 2 + k)],
                           fill=(220, 230, 250))
            if 4.0 <= gl < 5.4:
                say.append((head[0] + 10, head[1] - 26, "Hä?!"))
            elif 5.8 <= gl < 7.8:
                say.append((cx + 20, BD_TABLE[2] - 92, "Scherzkerzen! Hihi!"))
        elif gname == "anschneiden":
            hx, hy = hands[1]
            d.polygon([(hx, hy - 2), (hx + 18, hy - 6), (hx + 18, hy - 2), (hx, hy + 1)], fill=(200, 205, 215))
            d.rectangle([hx - 6, hy - 2, hx, hy + 1], fill=(60, 40, 30))
            if 2.0 <= gl < 3.6:
                say.append((cx, BD_TABLE[2] - 92, "Wag es ja nicht!"))
            elif 6.4 <= gl < 8.0:
                say.append((head[0] + 10, head[1] - 26, "Okay, okay …"))
        elif gname == "geschenk":
            self._bd_gag_gift(img, d, gl, t, say, head)
        elif gname == "ballon":
            self._bd_gag_balloon(img, d, gl, t, say, head, st)
        # Konfetti (Höhepunkt und Ballon)
        if boom and bt < 2.0 and int(bt * 15) % 2 == 0:
            for side in (-1, 1):
                for _ in range(6):
                    st["conf"].append([160 + side * 160, BD_FLOOR - 20, -side * st["rng"].uniform(60, 160),
                                       st["rng"].uniform(-220, -120), st["rng"].randrange(6)])
        if boom and 0.4 < bt < 2.8:
            say.append((BD_CAKE_X, BD_TABLE[2] - 96, "Hoch – hoch – hoch!"))
        for p in st["conf"]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 200 * dt
            p[2] *= 1 - dt * 0.8
        st["conf"] = [p for p in st["conf"] if p[1] < BD_FLOOR][-160:]
        for p in st["conf"]:
            d.rectangle([p[0], p[1], p[0] + 2, p[1] + 3], fill=BD_COLORS[p[4]])
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        fl = 0.8 + 0.2 * math.sin(t * 19) * math.sin(t * 7)
        self.vis_candle = (255, int(150 * fl), int(30 * fl)) if lit != [] else (60, 30, 10)
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _bd_gag_gift(self, img, d, gl, t, say, head):
        """Geschenk im Geschenk im Geschenk … am Ende: Socken."""
        x = 280
        sizes = [(34, (60, 160, 230)), (26, (230, 60, 80)), (18, (110, 200, 90)), (12, (220, 110, 220))]
        step = int(min(4.0, max(0.0, gl - 0.8) / 1.2))
        k = (gl - 0.8) % 1.2 if gl > 0.8 else 0.0
        for i, (w, c) in enumerate(sizes):
            if i < step:
                continue
            lid = min(30.0, k * 60) if i == step and gl > 0.8 and step < 4 else 0.0
            self._bd_gift(d, x, BD_FLOOR, w, c, (250, 220, 60), lid=lid)
            break
        if step >= 4 or gl > 5.6:
            for side in (-1, 1):
                sx = x + side * 8
                d.polygon([(sx - 3, BD_FLOOR - 26), (sx + 3, BD_FLOOR - 26), (sx + 3, BD_FLOOR - 12),
                           (sx + 9, BD_FLOOR - 10), (sx + 9, BD_FLOOR - 6), (sx - 3, BD_FLOOR - 6)],
                          fill=(120, 120, 140))
                d.line([(sx - 3, BD_FLOOR - 22), (sx + 3, BD_FLOOR - 22)], fill=(230, 60, 80), width=2)
            if gl > 5.8:
                say.append((head[0] + 10, head[1] - 26, "Socken. Wie jedes Jahr."))
        elif gl > 1.0:
            say.append((x - 10, BD_FLOOR - 64, ["Oh!", "Noch eins?", "Und noch eins …", "Winzig!"][min(3, step)]))

    def _bd_gag_balloon(self, img, d, gl, t, say, head, st):
        """Ein Ballon wird aufgeblasen, bis er platzt – Haare zu Berge, Konfetti."""
        bx, by = head[0] + 18, head[1] - 4
        if gl < 4.2:
            r = 4 + gl * 9 + math.sin(t * 6) * 1.5
            self._blob(img, bx + r * 0.8, by - r * 0.4, r * 1.6, r * 1.9, BD_BALLOONS[0][2], gloss=0.7)
            if gl > 3.0:
                say.append((head[0] - 4, head[1] - 46 - r * 0.6, "Noch ein bisschen …"))
        elif gl < 4.6:
            d.text((bx + 10, by - 40), "PENG!", font=self.f_big, fill=(230, 40, 60))
            if not st.get("popped"):
                st["popped"] = True
                for _ in range(30):
                    a = st["rng"].uniform(0, 6.28)
                    v = st["rng"].uniform(60, 180)
                    st["conf"].append([bx + 20, by - 20, math.cos(a) * v, math.sin(a) * v - 60, st["rng"].randrange(6)])
        else:
            st["popped"] = False
            for k in range(7):                                                      # Haare zu Berge
                a2 = -math.pi / 2 + (k - 3) * 0.3
                d.line([(head[0] + math.cos(a2) * 8, head[1] - 8 + math.sin(a2) * 4),
                        (head[0] + math.cos(a2) * 18, head[1] - 10 + math.sin(a2) * 16)], fill=(110, 70, 40), width=2)
            if gl < 6.6:
                say.append((head[0] + 10, head[1] - 34, "…"))
