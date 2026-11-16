"""Visualisierung „Oktoberfest“ (oktoberfest, Mixin OktoberfestVisual): Im Festzelt unter weiß-blauen Rauten spielt
die Blaskapelle (der Tubatrichter pumpt im Bass, die Trompete glänzt auf hohe Schläge), an den Bierbänken schunkeln
die Gäste im Takt, Lebkuchenherzen baumeln. Höhepunkt: Alle steigen auf die Bänke und heben die Krüge („Oans, zwoa,
g'suffa!“). Wortbeitrag: Brotzeit – die Kapelle macht Pause. Gags: Maßkrugstemmen, die Bedienung mit zehn Krügen im
Slalom, Schuhplattler im Takt, ein Brathendl macht sich davon.
"""
import math
import random

OK_FLOOR = VIS_H - 18
OK_STAGE_Y = 114                        # Podium der Kapelle (Füße)
OK_BAND = (110, 160, 210)               # Tuba, Trompete, Trommel
OK_BENCH_Y = OK_FLOOR - 10              # Gäste sitzen hier (Fußpunkt)
OK_GUESTS = [30, 66, 102, 218, 254, 290]
OK_GAGS = {"stemmen": 8.0, "bedienung": 8.0, "plattler": 8.0, "hendl": 7.0}
OK_GAG_FIRST, OK_GAG_PAUSE = 8.0, (12.0, 20.0)
OK_BOOM = 4.0
OK_BLUE, OK_WHITE = (60, 120, 210), (245, 248, 252)
OK_SHIRTS = [(250, 250, 250), (200, 60, 70), (90, 150, 210), (250, 250, 250), (100, 160, 90), (230, 200, 120)]


class OktoberfestVisual:
    vis_rauten = None

    def _ok_scene(self):
        if "_ok_bg" in self.__dict__:
            return self._ok_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (220, 196, 150))
        d = ImageDraw.Draw(img)
        for y0 in range(-15, 30, 15):                                               # Rauten-Himmel
            for x0 in range(-15 if (y0 // 15) % 2 else 0, WIDTH, 30):
                d.polygon([(x0 + 15, y0), (x0 + 30, y0 + 15), (x0 + 15, y0 + 30), (x0, y0 + 15)],
                          fill=OK_BLUE if (x0 // 30 + y0 // 15) % 2 else OK_WHITE)
        for x in range(0, WIDTH, 40):                                               # Stoffbahnen
            d.chord([x - 20, 26, x + 20, 50], 0, 180, fill=OK_WHITE)
            d.chord([x, 26, x + 40, 48], 0, 180, fill=OK_BLUE)
        for x in range(20, WIDTH, 60):                                              # Lebkuchenherzen
            d.line([(x - 8, 48), (x, 56), (x + 8, 48)], fill=(200, 60, 60))
            d.ellipse([x - 9, 54, x + 1, 64], fill=(160, 90, 50))
            d.ellipse([x - 1, 54, x + 9, 64], fill=(160, 90, 50))
            d.polygon([(x - 9, 60), (x + 9, 60), (x, 72)], fill=(160, 90, 50))
            d.arc([x - 6, 57, x + 6, 67], 200, 340, fill=(250, 250, 250))
        d.rectangle([70, OK_STAGE_Y, 250, OK_STAGE_Y + 10], fill=(140, 90, 50))     # Podium
        d.rectangle([70, OK_STAGE_Y + 10, 250, OK_STAGE_Y + 14], fill=(110, 70, 40))
        for x in range(0, WIDTH, 16):                                              # Dielen
            d.line([(x, OK_STAGE_Y + 14), (x - 30, HEIGHT)], fill=(196, 170, 126))
        self._ok_bg = img
        return img

    def _ok_mug(self, d, x, y, s=1.0, foam=True):
        d.rectangle([x - 4 * s, y - 11 * s, x + 4 * s, y], fill=(250, 210, 80), outline=(200, 200, 210))
        d.arc([x + 2 * s, y - 9 * s, x + 9 * s, y - 2 * s], 270, 90, fill=(200, 200, 210), width=2)
        if foam:
            d.ellipse([x - 5 * s, y - 14 * s, x + 5 * s, y - 9 * s], fill=(255, 255, 250))

    def _ok_table(self, d, x0, x1, y):
        d.rectangle([x0, y - 26, x1, y - 22], fill=(170, 120, 70))
        for lx in (x0 + 6, x1 - 8):
            d.line([(lx, y - 22), (lx, y + 6)], fill=(120, 80, 46), width=3)

    @vis_style("oktoberfest")
    def vis_oktoberfest(self, s, o, color):
        t = s["t"]
        img = self._ok_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("oktoberfest", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                                   "fast": s["level"], "boom": -99.0, "gag": None, "order": [],
                                                   "k": 0, "next_gag": t + OK_GAG_FIRST, "rng": random.Random(91),
                                                   "start": t, "tp": -9.0})
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
        boom = 0 <= bt < OK_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= OK_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*OK_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(OK_GAGS), len(OK_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        if playing and new_beat:
            st["k"] += 1
        if playing and new_hat:
            st["tp"] = t
        say = []
        # Blaskapelle
        tx, px, dx = OK_BAND
        if talk:
            for x in OK_BAND:
                self._fig(img, d, x, OK_STAGE_Y, t, OK_WHITE, {"lh": (-6, 20), "rh": (10, 10)}, h=0.75,
                          hat="tracht", legs=(110, 80, 50), sit=False)
            say.append((160, OK_STAGE_Y - 70, "Brotzeit! Pause!"))
        else:
            sway = math.sin(t * math.pi / period) if playing else 0.0
            hc, hands = self._fig(img, d, tx + sway * 2, OK_STAGE_Y, t, OK_WHITE, {"lh": (4, 6), "rh": (16, 4)},
                                  h=0.75, hat="tracht", legs=(110, 80, 50), mouth=0.0)
            bell = 9 + 5 * s["bass"] if playing else 9                              # Tuba
            d.ellipse([tx - 2, OK_STAGE_Y - 44, tx + 14, OK_STAGE_Y - 26], outline=(230, 190, 70), width=4)
            d.line([(tx + 12, OK_STAGE_Y - 42), (tx + 18, OK_STAGE_Y - 62)], fill=(230, 190, 70), width=5)
            d.ellipse([tx + 18 - bell, OK_STAGE_Y - 66 - bell * 0.6, tx + 18 + bell, OK_STAGE_Y - 62 + bell * 0.3],
                      fill=(250, 210, 90), outline=(200, 150, 40))
            hc, hands = self._fig(img, d, px + sway * 2, OK_STAGE_Y, t, OK_WHITE, {"lh": (6, -4), "rh": (14, -6)},
                                  h=0.75, hat="tracht", legs=(110, 80, 50))
            shine = max(0.0, 1 - (t - st["tp"]) / 0.2)
            d.line([(hc[0] + 4, hc[1] + 4), (hc[0] + 28, hc[1] - 2 - 4 * bang)], fill=(240, 200, 80), width=3)
            d.ellipse([hc[0] + 26, hc[1] - 9 - 4 * bang, hc[0] + 34, hc[1] + 3 - 4 * bang], fill=(250, 210, 90))
            if shine:
                for k in range(4):
                    a = k * 1.57 + t * 4
                    d.line([(hc[0] + 30, hc[1] - 3), (hc[0] + 30 + math.cos(a) * 8 * shine,
                                                      hc[1] - 3 + math.sin(a) * 8 * shine)], fill=(255, 255, 220))
            hit = st["k"] % 2
            self._fig(img, d, dx, OK_STAGE_Y, t, OK_WHITE, {"lh": (-8, 10 if hit else 2), "rh": (8, 2 if hit else 10)},
                      h=0.75, hat="tracht", legs=(110, 80, 50))
            d.ellipse([dx - 12, OK_STAGE_Y - 26, dx + 12, OK_STAGE_Y - 8], fill=(230, 220, 200), outline=(170, 40, 40),
                      width=3)
            if playing and t - s.get("beat_t", -9) < 0.1:
                d.text((dx + 14, OK_STAGE_Y - 36), "bumm", font=self.f_tiny, fill=(140, 40, 30))
        # Bierbänke mit schunkelnden Gästen
        self._ok_table(d, 10, 122, OK_FLOOR)
        self._ok_table(d, 198, 310, OK_FLOOR)
        stand = boom and 0.4 < bt
        bar = (st["k"] // 2) % 2
        schunkel = (1 if bar else -1) * (math.sin(math.pi * ((t - s.get("beat_t", t)) / period)) if playing else 0)
        for i, gx in enumerate(OK_GUESTS):
            if gname == "plattler" and i in (2, 3):
                continue
            lean = schunkel * 0.5 if not stand else 0.0
            pose = {"lh": (-14, 0), "rh": (14, 0)}
            if stand:
                pose = {"lh": (-6, -24), "rh": (8, -26)}
            elif gname == "stemmen" and i == 1:
                sink = min(1.0, max(0.0, (gl - 2.0) / 5.0))
                pose = {"lh": (-6, 14), "rh": (22, -2 + 18 * sink)}
            hc, hands = self._fig(img, d, gx, OK_BENCH_Y - (14 if stand else 0), t, OK_SHIRTS[i], pose, h=0.85,
                                  lean=lean, sit=not stand, hat="tracht" if i % 3 == 0 else None,
                                  dress=(200, 60, 90) if i % 3 == 1 else None, legs=(110, 80, 50),
                                  mouth=level if playing else 0.0)
            if stand or (gname == "stemmen" and i == 1):
                hx, hy = hands[1]
                self._ok_mug(d, hx, hy + 4)
            else:
                self._ok_mug(d, gx + 12, OK_FLOOR - 26)
            if gname == "stemmen" and i == 1:
                shake = math.sin(t * 40) * min(1.0, gl / 3)
                d.text((hc[0] - 4 + shake, hc[1] - 30), f"{max(0, int(gl * 20))} s", font=self.f_tiny,
                       fill=(60, 40, 30))
                if 3.0 <= gl < 5.6:
                    say.append((hc[0] + 10, hc[1] - 38, "Ich halt das ewig …"))
                elif gl >= 6.2:
                    say.append((hc[0] + 10, hc[1] - 38, "… oder auch nicht."))
        if stand and bt < 3.6:
            say.append((160, OK_STAGE_Y - 66, "Oans, zwoa, g'suffa!"))
        if gname == "bedienung":
            self._ok_gag_waitress(img, d, gl, t, say)
        elif gname == "plattler":
            self._ok_gag_plattler(img, d, gl, t, say, st, bang)
        elif gname == "hendl":
            self._ok_gag_chicken(img, d, gl, t, say)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_rauten = OK_BLUE if st["k"] % 2 else OK_WHITE
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _ok_gag_waitress(self, img, d, gl, t, say):
        """Die Bedienung trägt zehn Krüge im Slalom durchs Zelt."""
        x = -30 + gl / OK_GAGS["bedienung"] * 380
        y = OK_FLOOR + 14
        hc, hands = self._fig(img, d, x, y, t, (250, 250, 250), {"lh": (-14, -2), "rh": (14, -2),
                                                                  "lf": (-6 + 6 * math.sin(t * 10), 34),
                                                                  "rf": (6 - 6 * math.sin(t * 10), 34)},
                              h=0.95, dress=(40, 120, 70), hair=(200, 150, 70))
        wob = math.sin(gl * 3) * 2
        for side, (hx, hy) in zip((-1, 1), hands):
            for k in range(5):
                self._ok_mug(d, hx + side * (k * 7) + wob, hy + 2, s=0.8)
        if 2.5 <= gl < 4.5:
            say.append((hc[0], hc[1] - 30, "Vorsicht, heiß und kalt!"))

    def _ok_gag_plattler(self, img, d, gl, t, say, st, bang):
        """Zwei Burschen im Schuhplattler – Klatsch auf Schenkel und Sohle im Takt."""
        for i, x in enumerate((130, 190)):
            k = (st["k"] + i) % 4
            if k == 0:
                pose = {"lh": (2, 30), "rh": (-2, 30), "lf": (-6, 34), "rf": (10, 18)}
            elif k == 1:
                pose = {"lh": (-14, 8), "rh": (6, 34), "lf": (-6, 34), "rf": (16, 22)}
            elif k == 2:
                pose = {"lh": (-14, -18), "rh": (14, -18), "lf": (-10, 30), "rf": (10, 30)}
            else:
                pose = {"lh": (-4, 30), "rh": (4, 30), "lf": (-14, 24), "rf": (6, 34)}
            self._fig(img, d, x, OK_FLOOR + 4 - bang * 4, t, OK_WHITE, pose, h=0.9, hat="tracht",
                      legs=(110, 80, 50))
            if bang > 0.8:
                d.text((x + 10, OK_FLOOR - 40), "klatsch!", font=self.f_tiny, fill=(120, 40, 30))
        if 1.0 <= gl < 3.0:
            say.append((160, OK_FLOOR - 92, "Hollaradiridi!"))

    def _ok_gag_chicken(self, img, d, gl, t, say):
        """Ein Brathendl springt vom Teller und läuft davon – der Gast jagt hinterher."""
        x = 230 + max(0.0, gl - 1.0) * 70
        y = OK_FLOOR - 26 - (abs(math.sin(gl * 10)) * 6 if gl > 1.0 else 0)
        d.ellipse([214, OK_FLOOR - 28, 246, OK_FLOOR - 22], fill=(250, 250, 250))
        self._blob(img, x, y - 6, 20, 14, (200, 120, 50), gloss=0.6)
        for side in (-1, 1):
            leg = math.sin(t * 14 + side) * 4 if gl > 1.0 else 0
            d.line([(x + side * 5, y - 2), (x + side * 7 + leg, y + 6)], fill=(200, 120, 50), width=3)
            d.ellipse([x + side * 7 + leg - 2, y + 4, x + side * 7 + leg + 3, y + 8], fill=(250, 240, 220))
        if 1.0 <= gl < 3.2:
            say.append((x, y - 22, "Tschüss!"))
        elif gl >= 3.4:
            say.append((250, OK_FLOOR - 90, "Mei Hendl!"))
