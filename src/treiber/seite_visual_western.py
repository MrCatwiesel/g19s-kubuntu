"""Visualisierung „Western-Saloon“ (western, Mixin WesternVisual): Im Saloon hämmert der Klavierspieler (Tasten je
Frequenzband), die Schwingtüren schlagen im Bass, der Wirt schiebt Gläser über den Tresen, zwei Cowboys tanzen
Line-Dance, durchs Fenster sieht man die Wüste. Höhepunkt: Alle tanzen, Hüte fliegen („Yeehaw!“). Wortbeitrag: Der
Sheriff schafft Ruhe. Gags: Duell (gezogen wird eine Banane), das Glas rutscht über den Tresen hinaus, ein Pferd
bestellt ein Wasser, ein Steppenläufer rollt durch.
"""
import math
import random

WS_FLOOR = VIS_H - 22
WS_PIANO = 60
WS_BAR = (178, 310, WS_FLOOR - 40)
WS_DOOR = 136
WS_DANCERS = (110, 160)
WS_GAGS = {"duell": 8.0, "glas": 6.0, "pferd": 8.0, "steppe": 6.0}
WS_GAG_FIRST, WS_GAG_PAUSE = 8.0, (12.0, 20.0)
WS_BOOM = 4.0


class WesternVisual:
    vis_col_western = None

    def _ws_scene(self):
        if "_ws_bg" in self.__dict__:
            return self._ws_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (150, 96, 56))
        d = ImageDraw.Draw(img)
        for x in range(0, WIDTH, 14):                                               # Holzwände
            d.rectangle([x, 0, x + 13, WS_FLOOR], fill=(150 + (x * 7 % 20), 96 + (x * 3 % 12), 56))
            d.line([(x, 0), (x, WS_FLOOR)], fill=(110, 70, 40))
        d.rectangle([0, WS_FLOOR, WIDTH, HEIGHT], fill=(110, 72, 42))
        for x in range(0, WIDTH, 24):
            d.line([(x, WS_FLOOR), (x - 20, HEIGHT)], fill=(90, 58, 34))
        d.rectangle([196, 18, 290, 70], fill=(250, 200, 130))                        # Fenster mit Wüste
        d.polygon([(196, 56), (230, 40), (260, 50), (290, 38), (290, 70), (196, 70)], fill=(210, 140, 80))
        for cx in (220, 270):
            d.line([(cx, 70), (cx, 52)], fill=(70, 130, 60), width=4)
            d.line([(cx, 60), (cx - 6, 56), (cx - 6, 50)], fill=(70, 130, 60), width=3)
            d.line([(cx, 58), (cx + 6, 54), (cx + 6, 48)], fill=(70, 130, 60), width=3)
        d.rectangle([194, 16, 292, 72], outline=(90, 56, 30), width=4)
        d.line([(243, 16), (243, 72)], fill=(90, 56, 30), width=3)
        d.rectangle([90, 24, 176, 44], fill=(60, 36, 20))                           # Schild
        d.text((100, 26), "SALOON", font=self.f_small_b, fill=(250, 210, 120))
        x0, x1, ty = WS_BAR                                                         # Tresen
        d.rectangle([x0, ty, x1, WS_FLOOR], fill=(110, 60, 30))
        d.rectangle([x0 - 4, ty - 6, x1 + 4, ty], fill=(150, 90, 46))
        for x in range(x0 + 10, x1, 20):
            d.rectangle([x, ty + 8, x + 12, WS_FLOOR - 6], outline=(90, 50, 26))
        for k, c in enumerate(((120, 60, 40), (90, 120, 60), (170, 130, 50), (60, 90, 120))):  # Flaschenregal
            d.rectangle([204 + k * 22, 84, 210 + k * 22, 104], fill=c)
            d.rectangle([206 + k * 22, 78, 208 + k * 22, 84], fill=c)
        d.rectangle([196, 104, 300, 108], fill=(110, 60, 30))
        px = WS_PIANO                                                               # Klavier
        d.rectangle([px - 34, WS_FLOOR - 62, px + 34, WS_FLOOR], fill=(70, 40, 24))
        d.rectangle([px - 34, WS_FLOOR - 66, px + 34, WS_FLOOR - 62], fill=(90, 54, 32))
        self._ws_bg = img
        return img

    @vis_style("western")
    def vis_western(self, s, o, color):
        t = s["t"]
        img = self._ws_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("western", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                               "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                               "next_gag": t + WS_GAG_FIRST, "rng": random.Random(171), "start": t,
                                               "door": 0.0, "glass": None})
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
        boom = 0 <= bt < WS_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= WS_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*WS_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(WS_GAGS), len(WS_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        say = []
        if playing and new_beat:
            st["k"] += 1
            if s["bass"] > 0.5:
                st["door"] = 1.0
        st["door"] = max(0.0, st["door"] - dt * 2.5)
        bands = s.get("bands")
        if bands is None or len(bands) == 0:
            bands = [level] * 8
        # Klavierspieler
        px = WS_PIANO
        d.rectangle([px - 30, WS_FLOOR - 58, px + 30, WS_FLOOR - 52], fill=(250, 246, 236))
        for k in range(12):
            b = bands[min(len(bands) - 1, k * len(bands) // 12)] if playing else 0.0
            x = px - 29 + k * 5
            down = b > 0.5
            d.line([(x, WS_FLOOR - 58), (x, WS_FLOOR - 52 + (1 if down else 0))], fill=(120, 110, 100))
            if k % 3 != 2:
                d.rectangle([x + 2, WS_FLOOR - 58, x + 4, WS_FLOOR - 55 + (1 if down else 0)], fill=(20, 20, 20))
        hand_y = WS_FLOOR - 58 - 6 * bang
        self._fig(img, d, px, WS_FLOOR - 4, t, (200, 200, 200), {"lh": (-10 + 6 * math.sin(t * 9), 14 - 6 * bang),
                                                                  "rh": (10 + 6 * math.cos(t * 7), 14 - 6 * bang)},
                  h=0.9, sit=True, hat="top", hat_col=(40, 40, 40), beard=(60, 40, 30), face=-1)
        if playing:
            for k in range(2):
                ny = WS_FLOOR - 90 - ((t * 24 + k * 14) % 30)
                d.text((px + 20 + k * 10, ny), "♪", font=self.f_small_b, fill=(250, 230, 160))
        # Schwingtüren
        dw = 10 * math.cos(st["door"] * 2.5)
        for side in (-1, 1):
            hx = WS_DOOR + side * 1
            d.polygon([(hx, WS_FLOOR - 56), (hx + side * abs(dw) * 1.6, WS_FLOOR - 54), (hx + side * abs(dw) * 1.6,
                                                                                      WS_FLOOR - 26), (hx, WS_FLOOR - 28)],
                      fill=(170, 110, 60), outline=(100, 60, 30))
        # Wirt hinter dem Tresen
        x0, x1, ty = WS_BAR
        hcw, hw = self._fig(img, d, 280, ty + 30, t, (250, 250, 250), {"lh": (-16, 8), "rh": (8, 14)}, h=0.9,
                            hair=(40, 30, 30), beard=(40, 30, 30))
        d.rectangle([x0, ty, x1, WS_FLOOR], fill=(110, 60, 30))                  # Tresen vor dem Wirt
        for x in range(x0 + 10, x1, 20):
            d.rectangle([x, ty + 8, x + 12, WS_FLOOR - 6], outline=(90, 50, 26))
        d.rectangle([x0 - 4, ty - 6, x1 + 4, ty], fill=(150, 90, 46))
        if playing and new_hat and st["glass"] is None and gname != "glas":
            st["glass"] = t
        if st["glass"] is not None:
            k = (t - st["glass"]) / 0.9
            if k > 1:
                st["glass"] = None
            else:
                gx = 268 - k * 70
                d.rectangle([gx - 3, ty - 14, gx + 3, ty - 6], fill=(250, 210, 90), outline=(220, 220, 230))
        # Tänzer (Line-Dance)
        for i, x in enumerate(WS_DANCERS):
            step = st["k"] % 4
            pose = [{"lh": (-6, 12), "rh": (6, 12), "lf": (-14, 30), "rf": (6, 34)},
                    {"lh": (-6, 12), "rh": (6, 12), "lf": (-6, 34), "rf": (6, 34)},
                    {"lh": (-6, 12), "rh": (6, 12), "lf": (-6, 34), "rf": (16, 26)},
                    {"lh": (-14, -12), "rh": (14, -12), "lf": (-6, 34), "rf": (6, 34)}][step] if playing else None
            if boom:
                pose = {"lh": (-14, -24), "rh": (14, -24), "lf": (-10 + 8 * math.sin(t * 12), 30), "rf": (10, 34)}
            if gname == "duell":
                continue
            hc, _ = self._fig(img, d, x + (st["k"] % 8 < 4) * 4, WS_FLOOR, t, [(200, 60, 50), (60, 110, 180)][i], pose,
                              h=1.0, hat="cowboy" if not boom else None, hat_col=[(150, 100, 56), (90, 60, 40)][i],
                              beard=(90, 60, 30) if i else None)
            if boom:                                                                # Hüte fliegen
                hy = hc[1] - 16 - math.sin(min(1.0, bt / 2.0) * math.pi) * 50
                d.ellipse([hc[0] - 14, hy - 1, hc[0] + 14, hy + 5], fill=[(150, 100, 56), (90, 60, 40)][i])
                d.chord([hc[0] - 7, hy - 11, hc[0] + 7, hy + 4], 180, 360, fill=[(150, 100, 56), (90, 60, 40)][i])
        if boom and 0.4 < bt < 3.0:
            say.append((140, 60, "Yeehaw!"))
        if talk:
            tl = t - s.get("talk_t", t)
            hc, hands = self._fig(img, d, WS_DOOR + 6, WS_FLOOR, t, (90, 80, 70), {"lh": (-12, 16), "rh": (14, -14)}, h=1.0,
                                  hat="cowboy", hat_col=(60, 50, 40), beard=(110, 80, 50))
            d.polygon([(hc[0] - 4, hc[1] + 20), (hc[0] + 4, hc[1] + 20), (hc[0], hc[1] + 28)], fill=(240, 210, 60))
            if tl < 3.5:
                say.append((hc[0], hc[1] - 30, "Ruhe im Saloon! Durchsage!"))
        if gname == "duell":
            self._ws_gag_duel(img, d, gl, t, say)
        elif gname == "glas":
            k = gl / 1.6
            gx = 268 - k * 120
            gy = ty - 6 if gx > x0 - 4 else ty - 6 + (x0 - 4 - gx) ** 2 * 0.05
            if gy < WS_FLOOR - 2:
                d.rectangle([gx - 3, gy - 8, gx + 3, gy], fill=(250, 210, 90), outline=(220, 220, 230))
            else:
                for k2 in range(6):
                    d.line([(x0 - 40, WS_FLOOR - 2), (x0 - 40 + math.cos(k2) * 10, WS_FLOOR - 2 - abs(math.sin(k2)) * 8)],
                           fill=(220, 230, 240))
                say.append((x0 - 40, WS_FLOOR - 30, "Klirr!"))
            if gl > 3.6:
                say.append((hcw[0] - 10, hcw[1] - 26, "Zu viel Schwung …"))
        elif gname == "pferd":
            hx = 340 - min(1.0, gl / 2.0) * 160 if gl < 6.6 else 180 + (gl - 6.6) * 120
            self._blob(img, hx, WS_FLOOR - 34, 50, 26, (150, 100, 60), gloss=0.4)
            for lx in (-18, -8, 10, 20):
                step = math.sin(t * 10 + lx) * 3 if gl < 2.0 or gl > 6.6 else 0
                d.line([(hx + lx, WS_FLOOR - 26), (hx + lx + step, WS_FLOOR)], fill=(130, 84, 50), width=4)
            self._limb(img, (hx - 20, WS_FLOOR - 40), (hx - 30, WS_FLOOR - 58), 10, (150, 100, 60))
            self._blob(img, hx - 36, WS_FLOOR - 62, 20, 12, (150, 100, 60), gloss=0.4)
            d.point((hx - 38, WS_FLOOR - 65), fill=(0, 0, 0))
            d.line([(hx + 24, WS_FLOOR - 40), (hx + 32, WS_FLOOR - 24)], fill=(80, 50, 30), width=4)
            if 2.4 <= gl < 4.6:
                say.append((hx - 30, WS_FLOOR - 90, "Ein Wasser, bitte."))
            elif 4.6 <= gl < 6.6:
                say.append((hcw[0] - 10, hcw[1] - 26, "Mit Eis?"))
        elif gname == "steppe":
            k = gl / WS_GAGS["steppe"]
            tx = 360 - k * 420
            ty2 = WS_FLOOR - 12 - abs(math.sin(gl * 6)) * 14
            for j in range(10):
                a = j * 0.6 + gl * 8
                d.arc([tx - 12 + math.cos(a) * 2, ty2 - 12 + math.sin(a) * 2, tx + 12, ty2 + 12], j * 36, j * 36 + 200,
                      fill=(170, 130, 70), width=2)
            if 2.0 <= gl < 4.0:
                say.append((WS_DANCERS[1], WS_FLOOR - 100, "Wer hat die Tür offen gelassen?"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_col_western = (255, int(140 + 80 * level), 40)
        return img

    def _ws_gag_duel(self, img, d, gl, t, say):
        """Zwei Cowboys stehen sich gegenüber – gezogen wird eine Banane."""
        draw = gl > 3.2
        for i, (x, face) in enumerate(((80, 1), (200, -1))):
            hand = (face * 18, 0) if draw else (face * 4, 18)
            pose = {"lh": (-6, 16) if face > 0 else hand, "rh": hand if face > 0 else (6, 16)}
            hc, hands = self._fig(img, d, x, WS_FLOOR, t, [(200, 60, 50), (60, 110, 180)][i], pose, h=1.0,
                                  hat="cowboy", hat_col=[(150, 100, 56), (90, 60, 40)][i], face=face,
                                  eyes="closed" if 1.0 < gl < 3.0 else "dot", beard=(90, 60, 30) if i else None)
            if draw:
                hx, hy = hands[1] if face > 0 else hands[0]
                if i == 0:
                    d.arc([hx - 2, hy - 8, hx + 18, hy + 6], 200, 340, fill=(250, 220, 60), width=4)
                else:
                    d.rectangle([hx - 12, hy - 3, hx, hy + 1], fill=(80, 80, 90))
                    d.text((hx - 26, hy - 18), "klick", font=self.f_tiny, fill=(250, 250, 240))
        if gl < 3.0:
            say.append((140, 70, "Diese Stadt ist zu klein für uns zwei."))
        elif gl >= 3.6:
            say.append((80, 70, "Peng! Peng!"))
            if gl >= 5.4:
                say.append((200, 110, "… Ist das eine Banane?"))
