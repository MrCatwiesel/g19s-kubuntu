"""Visualisierung „Muttertag“ (mother, Mixin MotherVisual): Multitasking in der Küche. Mama wendet Pfannkuchen im
Takt (sie fliegen auf den Bass und landen auf dem Stapel), bügelt auf hohe Schläge, telefoniert und gießt die
Blumen – und je lauter die Musik, desto mehr Arme wachsen ihr (2, 4, 6). Höhepunkt: Super-Mama mit Umhang, alles auf
einmal („Alles erledigt!“). Wortbeitrag: Füße hoch, Kaffee, „Fünf Minuten Ruhe …“. Gags: Die Kinder bringen
Frühstück (verkohlter Toast, die Küche qualmt), das Blumenbeet vor dem Fenster wächst im Zeitraffer, ein
selbstgemaltes Bild („Das bist du!“) und die Waschmaschine hüpft durch die Küche und frisst eine Socke.
"""
import math
import random

MO_FLOOR = VIS_H - 18
MO_X = 160                              # Mama
MO_STOVE = (48, 120)                    # Herd (x0, x1), Pfanne auf der Platte
MO_COUNTER_Y = MO_FLOOR - 46
MO_BOARD = (184, 256, MO_FLOOR - 40)    # Bügelbrett x0, x1, Oberkante
MO_WINDOW = (118, 22, 204, 86)
MO_PHONE = (30, 84)
MO_GAGS = {"fruehstueck": 9.0, "blumenbeet": 9.0, "bild": 8.0, "waschmaschine": 8.0}
MO_GAG_FIRST, MO_GAG_PAUSE = 8.0, (12.0, 20.0)
MO_BOOM = 4.0
MO_SKIN = (244, 204, 172)
MO_DRESS = (200, 70, 110)
MO_HAIR = (130, 70, 40)


class MotherVisual:
    vis_rose = None                     # Farbe für die Tastatur

    def _mo_kitchen(self):
        if "_mo_bg" in self.__dict__:
            return self._mo_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (246, 236, 214))
        d = ImageDraw.Draw(img)
        for y in range(0, MO_COUNTER_Y, 14):                                       # Fliesenspiegel
            for x in range((y // 14 % 2) * 7, WIDTH, 14):
                d.rectangle([x, y, x + 13, y + 13], outline=(232, 220, 196))
        for y in range(MO_FLOOR, HEIGHT, 12):                                       # Schachbrettboden
            for x in range(((y - MO_FLOOR) // 12 % 2) * 12, WIDTH, 24):
                d.rectangle([x, y, x + 11, y + 11], fill=(200, 196, 190))
        d.rectangle([0, MO_FLOOR, WIDTH, MO_FLOOR + 2], fill=(170, 160, 150))
        x0, y0, x1, y1 = MO_WINDOW                                                  # Fenster mit Garten
        d.rectangle([x0, y0, x1, y1], fill=(170, 214, 250))
        d.rectangle([x0, y1 - 22, x1, y1], fill=(120, 190, 90))
        self._blob(img, x0 + 66, y0 + 14, 14, 14, (255, 240, 160), gloss=0.1)
        d.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], outline=(250, 250, 250), width=4)
        d.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=(250, 250, 250), width=3)
        d.rectangle([x0 - 8, y1 + 2, x1 + 8, y1 + 7], fill=(236, 230, 220))         # Fensterbank
        for sx in (x0 - 16, x1 + 6):                                                # Gardinen
            d.polygon([(sx, y0 - 8), (sx + 12, y0 - 8), (sx + 8, y1 + 6), (sx + 2, y1 + 6)], fill=(240, 120, 140))
        sx0, sx1 = MO_STOVE                                                         # Herd
        d.rectangle([sx0, MO_COUNTER_Y, sx1, MO_FLOOR], fill=(250, 250, 250), outline=(180, 180, 180))
        d.rectangle([sx0 + 8, MO_COUNTER_Y + 16, sx1 - 8, MO_FLOOR - 8], fill=(60, 60, 66))
        d.rectangle([sx0 + 12, MO_COUNTER_Y + 20, sx1 - 12, MO_FLOOR - 12], fill=(90, 90, 98))
        d.rectangle([sx0 - 2, MO_COUNTER_Y - 4, sx1 + 2, MO_COUNTER_Y], fill=(70, 70, 76))
        for k in range(4):
            d.ellipse([sx0 + 10 + k * 16, MO_COUNTER_Y + 6, sx0 + 16 + k * 16, MO_COUNTER_Y + 12], fill=(40, 40, 44))
        d.rectangle([sx1 + 2, MO_COUNTER_Y, sx1 + 10, MO_FLOOR], fill=(220, 190, 150))   # Schrankseite
        px, py = MO_PHONE                                                           # Wandtelefon
        d.rounded_rectangle([px - 8, py - 12, px + 8, py + 14], radius=3, fill=(220, 60, 70))
        d.ellipse([px - 5, py - 4, px + 5, py + 6], fill=(240, 240, 240))
        bx0, bx1, by = MO_BOARD                                                     # Bügelbrett
        d.line([(bx0 + 10, by + 4), (bx1 - 14, MO_FLOOR)], fill=(150, 150, 160), width=2)
        d.line([(bx1 - 14, by + 4), (bx0 + 10, MO_FLOOR)], fill=(150, 150, 160), width=2)
        d.polygon([(bx0, by), (bx1 - 10, by), (bx1, by + 3), (bx1 - 10, by + 6), (bx0, by + 6)], fill=(120, 170, 220))
        for k in range(6):
            d.ellipse([bx0 + 6 + k * 11, by + 1, bx0 + 9 + k * 11, by + 4], fill=(250, 250, 250))
        d.rectangle([0, MO_COUNTER_Y - 4, sx0 - 2, MO_FLOOR], fill=(220, 190, 150))
        d.rectangle([0, MO_COUNTER_Y - 6, sx0 - 2, MO_COUNTER_Y - 2], fill=(180, 140, 100))
        d.rectangle([250, 22, 296, 70], fill=(252, 252, 250), outline=(200, 200, 200))   # Kalender
        d.rectangle([250, 22, 296, 34], fill=(220, 60, 80))
        d.text((256, 22), "MAI", font=self.f_tiny, fill=(255, 255, 255))
        cx, cy = 273, 52
        d.ellipse([cx - 9, cy - 8, cx + 1, cy + 2], fill=(230, 60, 100))
        d.ellipse([cx - 1, cy - 8, cx + 9, cy + 2], fill=(230, 60, 100))
        d.polygon([(cx - 9, cy - 2), (cx + 9, cy - 2), (cx, cy + 10)], fill=(230, 60, 100))
        self._mo_bg = img
        return img

    # -- Figuren -------------------------------------------------------------------------- #
    def _mo_mom(self, img, d, x, y, t, bang, targets, cape=0.0, sit=False, extra=0.0):
        """Mama mit Haarknoten und Schürze; targets: Liste von Handzielen (Paare links/rechts). Gibt Kopf zurück."""
        if cape:
            fl = math.sin(t * 9) * 6
            d.polygon([(x - 10, y - 66), (x + 10, y - 66), (x + 26 + fl, y - 6), (x - 26 + fl, y - 8)],
                      fill=(220, 40, 60))
        hip = (x, y - (20 if sit else 40))
        if sit:
            for side in (-1, 1):
                knee = (x + 22, y - 28 + side * 2)
                self._limb(img, (x + side * 4, hip[1]), knee, 7, MO_DRESS)
                self._limb(img, knee, (x + 44, y - 26 + side * 3), 5, MO_SKIN)
        else:
            for side in (-1, 1):
                step = math.sin(t * 6) * 2 * side * bang
                self._limb(img, (x + side * 5, hip[1]), (x + side * 7 + step, y - 3), 6, MO_SKIN)
                d.ellipse([x + side * 7 + step - 5, y - 5, x + side * 7 + step + 5, y], fill=(200, 40, 70))
        d.polygon([(x - 16, hip[1] + 6), (x + 16, hip[1] + 6), (x + 9, hip[1] - 34), (x - 9, hip[1] - 34)],
                  fill=MO_DRESS)
        d.polygon([(x - 10, hip[1] + 4), (x + 10, hip[1] + 4), (x + 7, hip[1] - 22), (x - 7, hip[1] - 22)],
                  fill=(250, 250, 250))                                             # Schürze
        d.ellipse([x - 3, hip[1] - 14, x + 3, hip[1] - 8], fill=(240, 120, 140))
        if cape:
            d.ellipse([x - 7, hip[1] - 32, x + 7, hip[1] - 20], fill=(250, 220, 60))
            d.text((x - 4, hip[1] - 33), "M", font=self.f_tiny, fill=(200, 40, 60))
        neck = (x, hip[1] - 36)
        hands = []
        for i, tgt in enumerate(targets):
            side = -1 if i % 2 == 0 else 1
            pair = i // 2
            sh = (x + side * 9, neck[1] + 3 + pair * 4)
            if tgt is None:
                tgt = (sh[0] + side * 8, sh[1] + 20)
            col = MO_DRESS if pair == 0 else (230, 110, 150)
            alpha = 1.0 if pair == 0 else min(1.0, extra * 2 - pair + 1)
            if alpha <= 0:
                hands.append(None)
                continue
            elbow, hand = _ik(sh, tgt, 22, 22, side if pair != 1 else -side)
            self._limb(img, sh, elbow, 5, col)
            self._limb(img, elbow, hand, 4, MO_SKIN)
            hands.append(hand)
        hc = (x, neck[1] - 11 - bang * 1.5)
        self._blob(img, hc[0], hc[1] - 2, 22, 20, MO_HAIR, gloss=0.3)
        self._blob(img, hc[0], hc[1] - 14, 12, 11, MO_HAIR, gloss=0.4)               # Haarknoten
        self._blob(img, hc[0], hc[1] + 1, 18, 19, MO_SKIN, gloss=0.3)
        d.chord([hc[0] - 9, hc[1] - 10, hc[0] + 9, hc[1] - 1], 180, 360, fill=MO_HAIR)
        for side in (-1, 1):
            d.ellipse([hc[0] + side * 4 - 1.5, hc[1] - 1, hc[0] + side * 4 + 1.5, hc[1] + 2], fill=(40, 30, 30))
            self._blob(img, hc[0] + side * 6, hc[1] + 4, 5, 4, (250, 170, 170), gloss=0.2)
        d.arc([hc[0] - 4, hc[1] + 2, hc[0] + 4, hc[1] + 8], 10, 170, fill=(180, 60, 70), width=2)
        return hc, hands

    def _mo_kid(self, img, d, x, y, t, walk, shirt, hair, h=50):
        step = math.sin(t * 10) * 3 * walk
        for side in (-1, 1):
            self._limb(img, (x + side * 3, y - h * 0.4), (x + side * 3 + side * step, y - 2), 4, (60, 70, 120))
        self._blob(img, x, y - h * 0.58, 16, h * 0.36, shirt, gloss=0.3)
        hc = (x, y - h * 0.86)
        self._blob(img, hc[0], hc[1] - 2, 17, 15, hair, gloss=0.3)
        self._blob(img, hc[0], hc[1] + 1, 14, 14, MO_SKIN, gloss=0.3)
        for side in (-1, 1):
            d.point((hc[0] + side * 3, hc[1]), fill=(30, 20, 20))
        d.arc([hc[0] - 3, hc[1] + 1, hc[0] + 3, hc[1] + 6], 10, 170, fill=(180, 60, 70))
        return hc, (x - 10, y - h * 0.6), (x + 10, y - h * 0.6)

    # -- Ablauf ------------------------------------------------------------------------------ #
    @vis_style("mother")
    def vis_mother(self, s, o, color):
        t = s["t"]
        img = self._mo_kitchen().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("mother", lambda: {"beats": s["beats"], "slow": s["level"], "fast": s["level"],
                                              "boom": -99.0, "gag": None, "order": [], "flip": -9.0, "stack": 3,
                                              "next_gag": t + MO_GAG_FIRST, "rng": random.Random(51), "start": t,
                                              "extra": 0.0, "iron": 0.0, "hats": s.get("hats", 0), "plant": 0.3})
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
        boom = 0 <= bt < MO_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= MO_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*MO_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(MO_GAGS), len(MO_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        say = []
        # Wie viele Arme? (Lautstärke, beim Höhepunkt alle)
        want = 0.0 if not playing else (2.0 if boom else min(2.0, max(0.0, (level - 0.25) * 3.2)))
        if o.get("arms", True) is False:
            want = 0.0
        st["extra"] += (want - st["extra"]) * min(1.0, dt * 2.5)
        if demo:
            st["extra"] = 1.0
        # Wanduhr: Die Zeit rast mit der Lautstärke
        st["clock"] = st.get("clock", 0.0) + dt * (0.3 + 12 * level + (30 if boom else 0))
        ux, uy = 70, 46
        d.ellipse([ux - 16, uy - 16, ux + 16, uy + 16], fill=(252, 252, 250), outline=(120, 90, 70), width=3)
        for k in range(12):
            a = k * math.pi / 6
            d.point((ux + math.cos(a) * 12, uy + math.sin(a) * 12), fill=(60, 50, 50))
        for ln, sp, w in ((8, 1 / 12, 3), (12, 1.0, 2)):
            a = st["clock"] * sp - math.pi / 2
            d.line([(ux, uy), (ux + math.cos(a) * ln, uy + math.sin(a) * ln)], fill=(40, 30, 30), width=w)
        # Pfannkuchen: Bass wirft ihn hoch
        if playing and new_beat and s["bass"] > 0.5 and t - st["flip"] > period * 1.5:
            st["flip"] = t
        fk = (t - st["flip"]) / 0.7
        if 1.0 <= fk and st.get("landed") != st["flip"]:
            st["landed"] = st["flip"]
            st["stack"] = st["stack"] + 1 if st["stack"] < 12 else 3
        pan = (MO_STOVE[1] - 22, MO_COUNTER_Y - 6)
        d.ellipse([pan[0] - 16, pan[1] - 4, pan[0] + 16, pan[1] + 4], fill=(50, 50, 56))
        d.line([(pan[0] + 14, pan[1]), (pan[0] + 32, pan[1] - 6)], fill=(50, 50, 56), width=3)
        if 0 <= fk < 1.0:
            py = pan[1] - 2 - math.sin(fk * math.pi) * 50
            w = abs(math.cos(fk * math.pi * 2)) * 12 + 2
            d.ellipse([pan[0] - w, py - 2, pan[0] + w, py + 2], fill=(236, 190, 110), outline=(200, 140, 70))
        else:
            d.ellipse([pan[0] - 11, pan[1] - 4, pan[0] + 11, pan[1]], fill=(236, 190, 110))
        smoke = gname == "fruehstueck" and gl > 2.0
        for k in range(st["stack"]):                                                # Stapel auf der Anrichte
            d.ellipse([10, MO_COUNTER_Y - 10 - k * 3, 34, MO_COUNTER_Y - 4 - k * 3], fill=(236, 190, 110),
                      outline=(200, 140, 70))
        if smoke:
            for k in range(5):
                sy = MO_COUNTER_Y - 20 - ((gl * 30 + k * 16) % 70)
                self._blob(img, pan[0] + math.sin(gl * 2 + k) * 8, sy, 18 + k * 2, 14, (110, 110, 116),
                           alpha=0.6, flat=True)
        # Blumen auf der Fensterbank (wachsen mit dem Gießen)
        x0, y0, x1, y1 = MO_WINDOW
        if gname == "blumenbeet":
            self._mo_gag_garden(img, d, gl, t, say)
        pot = (x1 - 16, y1 + 2)
        d.polygon([(pot[0] - 7, pot[1] - 10), (pot[0] + 7, pot[1] - 10), (pot[0] + 5, pot[1]), (pot[0] - 5, pot[1])],
                  fill=(200, 110, 70))
        if playing and st["extra"] > 0.6:
            st["plant"] = min(1.0, st["plant"] + dt * 0.05)
        ph = 8 + st["plant"] * 14
        d.line([(pot[0], pot[1] - 10), (pot[0], pot[1] - 10 - ph)], fill=(70, 150, 60), width=2)
        for k, c in enumerate(((240, 80, 120), (250, 200, 60), (180, 110, 230))):
            fx = pot[0] + (k - 1) * 6
            fy = pot[1] - 12 - ph + abs(k - 1) * 4 - bang * 2
            for a in range(5):
                d.ellipse([fx + math.cos(a * 1.26) * 3 - 2, fy + math.sin(a * 1.26) * 3 - 2,
                           fx + math.cos(a * 1.26) * 3 + 2, fy + math.sin(a * 1.26) * 3 + 2], fill=c)
            d.ellipse([fx - 1.2, fy - 1.2, fx + 1.2, fy + 1.2], fill=(250, 240, 120))
        # Bügeleisen: hohe Schläge schieben es
        if playing and new_hat:
            st["iron"] = 1.0 - st["iron"] if st["rng"].random() < 0.8 else st["iron"]
        st["iron_x"] = st.get("iron_x", 0.0) + (st["iron"] - st.get("iron_x", 0.0)) * min(1.0, dt * 10)
        bx0, bx1, by = MO_BOARD
        ix = bx0 + 16 + st["iron_x"] * 22
        d.polygon([(ix - 10, by), (ix + 12, by), (ix + 8, by - 8), (ix - 8, by - 8)], fill=(200, 200, 210))
        d.arc([ix - 6, by - 16, ix + 6, by - 4], 180, 360, fill=(60, 60, 70), width=3)
        if playing and abs(st["iron"] - st["iron_x"]) > 0.2:
            self._blob(img, ix - 12, by - 8, 10, 8, (240, 240, 250), alpha=0.6, flat=True)
        # Hände: Paar 1 Pfanne + Bügeleisen, Paar 2 Telefon + Gießkanne, Paar 3 Kochlöffel + Staubwedel
        mx = MO_X
        sit = talk
        if gname == "waschmaschine":
            self._mo_gag_washer(img, d, gl, t, say, bang)
        targets = [(pan[0] + 30, pan[1] - 6 - bang * 4), (ix, by - 14)]
        if st["extra"] > 0.05:
            targets += [(mx - 12, MO_FLOOR - 104), (pot[0] - 14, pot[1] - 6)]
        if st["extra"] > 1.05:
            targets += [(mx - 34, MO_FLOOR - 70 + math.sin(t * 9) * 6), (mx + 36, MO_FLOOR - 80 + math.cos(t * 7) * 8)]
        if sit:
            targets = [None, (mx + 14, MO_FLOOR - 52)]
        if gname == "bild" and 2.0 <= gl < 7.0 or gname == "fruehstueck" and 4.6 <= gl < 8.0:
            targets[0] = (mx - 10, MO_FLOOR - 60)
            targets[1] = (mx + 10, MO_FLOOR - 60)
        if sit:                                                                     # Sessel
            d.rounded_rectangle([mx - 22, MO_FLOOR - 44, mx + 22, MO_FLOOR - 4], radius=8, fill=(110, 140, 120))
            d.rectangle([mx + 40, MO_FLOOR - 24, mx + 56, MO_FLOOR - 2], fill=(140, 100, 60))
        head, hands = self._mo_mom(img, d, mx, MO_FLOOR - (8 if sit else 0), t, bang if not sit else 0.0, targets,
                                   cape=boom, sit=sit, extra=st["extra"])
        if len(hands) > 2 and hands[2]:                                             # Telefonhörer mit Kabel
            hx, hy = hands[2]
            pts = []
            for k in range(13):
                f = k / 12
                pts.append((MO_PHONE[0] + (hx - MO_PHONE[0]) * f + math.sin(f * 30) * 2,
                            MO_PHONE[1] + 10 + (hy - MO_PHONE[1] - 10) * f + 10 * math.sin(f * math.pi)))
            d.line(pts, fill=(220, 60, 70), width=1)
            d.rounded_rectangle([hx - 3, hy - 9, hx + 3, hy + 3], radius=2, fill=(220, 60, 70))
        if len(hands) > 3 and hands[3]:                                             # Gießkanne
            hx, hy = hands[3]
            d.rectangle([hx - 4, hy, hx + 6, hy + 9], fill=(90, 160, 200))
            d.line([(hx + 6, hy + 2), (hx + 13, hy + 7)], fill=(90, 160, 200), width=2)
            if playing:
                for k in range(3):
                    wy = hy + 8 + ((t * 40 + k * 5) % 14)
                    d.point((hx + 14, wy), fill=(120, 180, 250))
        if len(hands) > 5 and hands[4] and hands[5]:                                # Kochlöffel, Staubwedel
            hx, hy = hands[4]
            d.line([(hx, hy), (hx - 6, hy - 14)], fill=(170, 120, 70), width=2)
            d.ellipse([hx - 9, hy - 19, hx - 3, hy - 12], fill=(170, 120, 70))
            hx, hy = hands[5]
            d.line([(hx, hy), (hx + 4, hy - 10)], fill=(120, 80, 50), width=2)
            for k in range(5):
                d.line([(hx + 4, hy - 10), (hx + 4 + (k - 2) * 3, hy - 18)], fill=[(240, 80, 120), (250, 200, 60),
                       (90, 160, 220), (110, 200, 90), (200, 110, 220)][k], width=2)
        if sit:                                                                     # Kaffee
            hx, hy = hands[1]
            d.rectangle([hx - 4, hy - 8, hx + 4, hy], fill=(250, 250, 250))
            d.arc([hx + 2, hy - 7, hx + 8, hy - 2], 270, 90, fill=(250, 250, 250), width=2)
            for k in range(2):
                d.arc([hx - 3 + k * 4, hy - 16, hx + 1 + k * 4, hy - 9], 90, 270, fill=(200, 200, 210))
            tl = t - s.get("talk_t", t)
            if tl < 3.0:
                say.append((head[0], head[1] - 22, "Fünf Minuten Ruhe …"))
        elif st["extra"] > 0.6 and playing and int(t / 3) % 3 == 0 and not gname and not boom:
            say.append((head[0] - 30, head[1] - 22, "Ja … mhm … ja …"))
        if boom and 0.6 < bt < 3.0:
            say.append((head[0], head[1] - 26, "Alles erledigt!"))
        if boom:
            for k in range(8):
                a = t * 3 + k * 0.785
                r = 40 + 6 * math.sin(t * 5 + k)
                cx, cy = head[0] + math.cos(a) * r, head[1] + 30 + math.sin(a) * r * 0.6
                d.line([(cx - 3, cy), (cx + 3, cy)], fill=(250, 220, 60), width=2)
                d.line([(cx, cy - 3), (cx, cy + 3)], fill=(250, 220, 60), width=2)
        if gname == "fruehstueck":
            self._mo_gag_breakfast(img, d, gl, t, say, head)
        elif gname == "bild":
            self._mo_gag_picture(img, d, gl, t, say, head)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_rose = (255, int(60 + 60 * level), int(110 + 40 * level)) if not boom else (255, 200, 40)
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _mo_gag_breakfast(self, img, d, gl, t, say, head):
        """Die Kinder bringen Frühstück: verkohlter Toast, überschwappender Kaffee – und die Küche qualmt."""
        if gl < 2.4:
            x, walk = 340 - gl / 2.4 * 110, 1.0
        elif gl < 8.2:
            x, walk = 230.0, 0.0
        else:
            x, walk = 230 + (gl - 8.2) * 140, 1.4
        wob = math.sin(t * 7) * (3 if gl < 2.4 else 1)
        self._mo_kid(img, d, x + 22, MO_FLOOR, t + 0.3, walk, (90, 180, 110), (60, 40, 30), 46)
        hc, lh, rh = self._mo_kid(img, d, x, MO_FLOOR, t, walk, (250, 200, 60), (200, 150, 60), 54)
        tx, ty = x - 4, MO_FLOOR - 36 + wob * 0.3
        d.polygon([(tx - 20, ty), (tx + 20, ty), (tx + 18, ty + 4), (tx - 18, ty + 4)], fill=(200, 160, 110))
        d.rectangle([tx - 16, ty - 8, tx - 4, ty], fill=(50, 34, 24))              # Toast, verkohlt
        d.rectangle([tx + 2, ty - 12, tx + 10, ty], fill=(250, 250, 250))           # Kaffee
        d.line([(tx + 6, ty - 12), (tx + 6 + wob, ty - 6)], fill=(140, 90, 50), width=2)
        d.line([(tx + 14, ty), (tx + 14, ty - 14)], fill=(70, 150, 60), width=2)     # Blume
        self._blob(img, tx + 14, ty - 16, 7, 7, (240, 80, 120), gloss=0.3)
        for k in range(2):
            self._blob(img, tx - 10 + k * 4, ty - 14 - ((gl * 20 + k * 6) % 16), 6, 6, (90, 90, 96), alpha=0.6,
                       flat=True)
        if 2.4 <= gl < 4.6:
            say.append((x + 10, MO_FLOOR - 70, "Frühstück! Alles Gute!"))
        elif 4.6 <= gl < 6.6:
            say.append((head[0], head[1] - 22, "Oh, wie lieb … riecht's hier verbrannt?"))
        elif 6.6 <= gl < 8.4:
            say.append((x + 10, MO_FLOOR - 70, "Die Küche räumen wir später auf!"))

    def _mo_gag_garden(self, img, d, gl, t, say):
        """Das Blumenbeet vor dem Fenster wächst im Zeitraffer, bis eine Riesenblume hereinschaut."""
        x0, y0, x1, y1 = MO_WINDOW
        g = min(1.0, gl / 5.0)
        for k in range(5):
            fx = x0 + 10 + k * 16
            h = 6 + g * (20 + k * 6) * (1.6 if k == 2 else 1.0)
            if k == 2 and gl > 4.0:
                continue
            d.line([(fx, y1), (fx + math.sin(t * 2 + k) * 2, y1 - h)], fill=(70, 150, 60), width=2)
            c = [(240, 80, 120), (250, 200, 60), (180, 110, 230), (250, 140, 60), (240, 240, 250)][k]
            r = 2 + g * 4
            for a in range(6):
                cx = fx + math.cos(a * 1.05) * r * 0.9
                cy = y1 - h + math.sin(a * 1.05) * r * 0.9
                d.ellipse([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], fill=c)
            d.ellipse([fx - r * 0.5, y1 - h - r * 0.5, fx + r * 0.5, y1 - h + r * 0.5], fill=(250, 220, 80))
        if gl > 4.0:                                                                # Riesenblume schaut herein
            k = min(1.0, (gl - 4.0) / 1.2)
            fx, fy = x0 + 42 + k * 30, y0 + 30 + k * 20
            d.line([(x0 + 42, y1), (fx, fy)], fill=(70, 150, 60), width=4)
            for a in range(8):
                cx, cy = fx + math.cos(a * 0.785 + t) * 12, fy + math.sin(a * 0.785 + t) * 12
                self._blob(img, cx, cy, 12, 12, (250, 200, 60), gloss=0.4)
            self._blob(img, fx, fy, 16, 16, (150, 90, 40), gloss=0.4)
            for side in (-1, 1):
                d.ellipse([fx + side * 3 - 1.5, fy - 3, fx + side * 3 + 1.5, fy], fill=(20, 20, 20))
            d.arc([fx - 3, fy + 1, fx + 3, fy + 5], 10, 170, fill=(20, 20, 20))
            if 5.4 <= gl < 7.4:
                say.append((fx, fy - 18, "*schnüffel* Hallo!"))
            elif gl >= 7.4:
                say.append((MO_X, MO_FLOOR - 120, "Danke … glaub ich."))

    def _mo_gag_picture(self, img, d, gl, t, say, head):
        """Ein Kind schenkt ein selbstgemaltes Bild: „Das bist du!“"""
        x = 340 - min(1.0, gl / 1.6) * 110 if gl < 7.0 else 230 + (gl - 7.0) * 140
        hc, lh, rh = self._mo_kid(img, d, x, MO_FLOOR, t, 1.0 if gl < 1.6 or gl >= 7.0 else 0.0, (90, 160, 230),
                                  (140, 80, 40), 48)
        if 1.8 <= gl < 7.0:                                                         # das Bild, groß
            bx0, by0 = 186, 40
            d.rectangle([bx0, by0, bx0 + 80, by0 + 64], fill=(252, 252, 246), outline=(200, 200, 190))
            cx, cy = bx0 + 40, by0 + 34
            d.ellipse([cx - 14, cy - 26, cx + 14, cy - 2], outline=(140, 80, 40), width=3)   # Riesenfrisur
            d.ellipse([cx - 7, cy - 18, cx + 7, cy - 4], outline=(240, 160, 120), width=2)
            d.point((cx - 3, cy - 12), fill=(0, 0, 0))
            d.point((cx + 3, cy - 12), fill=(0, 0, 0))
            d.arc([cx - 4, cy - 10, cx + 4, cy - 6], 10, 170, fill=(220, 40, 40))
            d.line([(cx, cy - 4), (cx, cy + 14)], fill=(200, 70, 110), width=2)
            for side in (-1, 1):                                                    # acht Arme
                for k in range(4):
                    d.line([(cx, cy), (cx + side * 22, cy - 10 + k * 7)], fill=(200, 70, 110), width=1)
                d.line([(cx, cy + 14), (cx + side * 6, cy + 26)], fill=(200, 70, 110), width=2)
            d.text((bx0 + 4, by0 + 50), "MAMA", font=self.f_tiny, fill=(230, 60, 80))
            self._blob(img, bx0 + 68, by0 + 12, 10, 10, (250, 210, 60), gloss=0.1)
            if gl < 4.0:
                say.append((x, MO_FLOOR - 66, "Das bist du!"))
            elif gl < 6.6:
                say.append((head[0], head[1] - 22, "Wie … treffend."))

    def _mo_gag_washer(self, img, d, gl, t, say, bang):
        """Die Waschmaschine schleudert, hüpft durch die Küche und frisst eine Socke."""
        k = min(1.0, gl / 3.0) if gl < 6.0 else max(0.0, 1 - (gl - 6.0) / 1.6)
        x = 300 - k * 60 + math.sin(t * 30) * 2 * (gl < 6.0)
        y = MO_FLOOR - abs(math.sin(t * 14)) * 4 * (gl < 6.0)
        d.rectangle([x - 20, y - 44, x + 20, y], fill=(246, 246, 250), outline=(170, 170, 180))
        d.rectangle([x - 20, y - 44, x + 20, y - 36], fill=(220, 220, 228))
        d.ellipse([x - 13, y - 32, x + 13, y - 6], fill=(150, 170, 190), outline=(110, 110, 120), width=2)
        for kk in range(3):
            a = t * 12 + kk * 2.1
            d.rectangle([x + math.cos(a) * 6 - 2, y - 19 + math.sin(a) * 6 - 2, x + math.cos(a) * 6 + 2,
                         y - 19 + math.sin(a) * 6 + 2], fill=[(240, 80, 120), (90, 160, 220), (250, 200, 60)][kk])
        if 3.0 <= gl < 4.4:                                                         # Socke wird eingesaugt
            f = (gl - 3.0) / 1.4
            sx = x - 50 + f * 50
            d.polygon([(sx - 4, y - 20), (sx + 2, y - 20), (sx + 2, y - 10), (sx + 8, y - 8), (sx + 8, y - 4),
                       (sx - 4, y - 4)], fill=(240, 80, 120))
        if 4.4 <= gl < 6.2:
            say.append((x, y - 52, "Mampf. Socke weg."))
