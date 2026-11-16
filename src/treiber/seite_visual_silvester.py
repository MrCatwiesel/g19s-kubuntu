"""Visualisierung „Silvester“ (newyear, Mixin NewYearVisual): Party auf der Dachterrasse über der Stadt. Raketen
steigen auf den Bass, hohe Schläge lassen kleine Sterne platzen, Sektkorken knallen. Die Anzeigetafel zählt am
31. Dezember die echte Zeit bis Mitternacht herunter (die letzten zehn Sekunden groß), danach „Frohes neues Jahr“.
Höhepunkt: Countdown 3-2-1 mit großem Feuerwerk. Wortbeitrag: ein Trinkspruch. Gags: Wachsgießen mit Deutung,
Vorsätze (sofort durchgestrichen), Wunderkerze schreibt die Jahreszahl, eine Rakete fliegt waagerecht über die Terrasse.
"""
import math
import random

NY_FLOOR = VIS_H - 22
NY_PEOPLE = [(118, (200, 40, 60), "party"), (156, (60, 90, 200), "top"), (226, (240, 200, 60), None)]
NY_TABLE = 270
NY_GAGS = {"wachs": 10.0, "vorsaetze": 8.0, "wunderkerze": 8.0, "rakete": 8.0}
NY_GAG_FIRST, NY_GAG_PAUSE = 8.0, (12.0, 20.0)
NY_BOOM = 6.0
NY_COLORS = [(255, 80, 80), (255, 210, 60), (90, 200, 255), (120, 255, 140), (230, 120, 255), (255, 255, 255)]
NY_WAX = [("Ein Schiff", "Du gehst auf Reisen!"), ("Ein Toaster?", "Wärme im neuen Jahr!"),
          ("Ein Herz", "Die Liebe klopft an!"), ("Ein Klumpen", "Bedeutet … Überraschung!"),
          ("Ein Schwein", "Glück, viel Glück!")]


def _ny_year(day):
    """Das kommende Jahr (am Neujahrstag das gerade begonnene)."""
    return day.year if (day.month, day.day) == (1, 1) else day.year + 1


class NewYearVisual:
    vis_ny = None

    def _ny_scene(self):
        if "_ny_bg" in self.__dict__:
            return self._ny_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([6, 8, 30], np.float32), np.array([40, 30, 70], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(3)
        for _ in range(50):
            d.point((rng.uniform(0, WIDTH), rng.uniform(0, 110)), fill=(190, 190, 220))
        x = 0
        while x < WIDTH:                                                            # Skyline
            w, h = rng.randint(16, 34), rng.randint(30, 80)
            d.rectangle([x, NY_FLOOR - 24 - h, x + w, NY_FLOOR], fill=(22, 22, 36))
            if rng.random() < 0.3:
                d.line([(x + w / 2, NY_FLOOR - 24 - h), (x + w / 2, NY_FLOOR - 34 - h)], fill=(22, 22, 36), width=2)
            for wy in range(NY_FLOOR - 20 - h, NY_FLOOR - 26, 7):
                for wx in range(x + 3, x + w - 3, 6):
                    if rng.random() < 0.35:
                        d.rectangle([wx, wy, wx + 2, wy + 3], fill=(250, 220, 120))
            x += w + rng.randint(0, 4)
        d.rectangle([0, NY_FLOOR - 26, WIDTH, NY_FLOOR - 22], fill=(150, 150, 160))   # Geländer
        for x in range(0, WIDTH, 10):
            d.line([(x, NY_FLOOR - 22), (x, NY_FLOOR)], fill=(110, 110, 120), width=2)
        d.rectangle([0, NY_FLOOR, WIDTH, HEIGHT], fill=(70, 60, 64))
        for x in range(0, WIDTH, 20):
            d.line([(x, NY_FLOOR), (x - 8, HEIGHT)], fill=(56, 48, 52))
        for k in range(14):                                                         # Lichterkette
            lx = 6 + k * 23
            ly = 64 + 8 * math.sin(k * 0.9)
            d.ellipse([lx - 2, ly - 2, lx + 2, ly + 2], fill=NY_COLORS[k % 5])
        tx = NY_TABLE                                                               # Stehtisch
        d.ellipse([tx - 22, NY_FLOOR - 42, tx + 22, NY_FLOOR - 36], fill=(240, 240, 245))
        d.line([(tx, NY_FLOOR - 38), (tx, NY_FLOOR)], fill=(160, 160, 170), width=3)
        d.line([(tx - 12, NY_FLOOR), (tx + 12, NY_FLOOR)], fill=(160, 160, 170), width=3)
        self._ny_bg = img
        return img

    def _ny_board(self, d, t, st, s):
        """Anzeigetafel oben links: echter Countdown am 31.12., sonst die Uhrzeit mit Jahreszahl."""
        now = fest_now()
        day = fest_today()
        year = _ny_year(day)
        d.rounded_rectangle([6, 20, 134, 46], radius=4, fill=(10, 10, 14), outline=(80, 80, 90))
        big = None
        if day.month == 12 and day.day == 31:
            left = max(0, int((24 * 3600) - (now.hour * 3600 + now.minute * 60 + now.second)))
            txt = f"{left // 3600:02d}:{left // 60 % 60:02d}:{left % 60:02d}"
            if left <= 10:
                big = str(left) if left > 0 else None
        elif day.month == 1 and day.day == 1 and now.hour == 0 and now.minute < 15:
            txt = f"Prosit {day.year}!"
        else:
            txt = f"{now.hour:02d}:{now.minute:02d} → {year}"
        d.text((12, 22), txt, font=self.f_mid, fill=(255, 90, 60))
        return big, (day.month == 1 and day.day == 1 and now.hour == 0 and now.minute < 15)

    @vis_style("newyear")
    def vis_newyear(self, s, o, color):
        t = s["t"]
        img = self._ny_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("newyear", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                               "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                               "next_gag": t + NY_GAG_FIRST, "rng": random.Random(71), "start": t,
                                               "rockets": [], "parts": [], "cork": -9.0, "wax": 0})
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
        boom = 0 <= bt < NY_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= NY_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*NY_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(NY_GAGS), len(NY_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
            if gag[0] == "wachs":
                st["wax"] = st["rng"].randrange(len(NY_WAX))
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        say = []
        big, newyear = self._ny_board(d, t, st, s) if o.get("countdown", True) else (None, False)
        rng = st["rng"]
        # Raketen: Bass startet eine, oben platzt sie
        if playing and new_beat:
            st["k"] += 1
            if s["bass"] > 0.45 and len(st["rockets"]) < 6:
                st["rockets"].append([rng.uniform(20, 300), NY_FLOOR - 30, rng.uniform(-10, 10),
                                      -rng.uniform(150, 200), rng.choice(NY_COLORS)])
            if s["bass"] > 0.6 and rng.random() < 0.3:
                st["cork"] = t
        if playing and new_hat and rng.random() < 0.5:
            self._fx_burst(st["parts"], rng.uniform(30, 290), rng.uniform(30, 100), rng.choice(NY_COLORS), rng, 10, 30)
        if (boom and 3.0 <= bt < 5.5 and int(bt * 6) != int((bt - dt) * 6)) or (newyear and rng.random() < 0.2):
            self._fx_burst(st["parts"], rng.uniform(40, 280), rng.uniform(30, 90), rng.choice(NY_COLORS), rng, 30, 80)
        for r in list(st["rockets"]):
            r[0] += r[2] * dt
            r[1] += r[3] * dt
            r[3] += 60 * dt
            if r[3] > -40 or r[1] < 30:
                st["rockets"].remove(r)
                self._fx_burst(st["parts"], r[0], r[1], r[4], rng, 22, 60)
                self.vis_ny = r[4]
                continue
            d.line([(r[0], r[1]), (r[0] - r[2] * 0.05, r[1] + 8)], fill=(255, 230, 150), width=2)
        self._fx_step(st["parts"], dt)
        self._fx_draw(d, st["parts"])
        # Sekt auf dem Tisch, Korken knallt
        tx = NY_TABLE
        d.rectangle([tx + 6, NY_FLOOR - 62, tx + 14, NY_FLOOR - 42], fill=(40, 90, 50))
        d.rectangle([tx + 8, NY_FLOOR - 70, tx + 12, NY_FLOOR - 62], fill=(40, 90, 50))
        d.rectangle([tx + 7, NY_FLOOR - 70, tx + 13, NY_FLOOR - 66], fill=(230, 200, 80))
        ck = (t - st["cork"]) / 0.8
        if 0 <= ck < 1:
            cx, cy = tx + 10 - ck * 60, NY_FLOOR - 72 - math.sin(ck * math.pi) * 60
            d.rectangle([cx - 2, cy - 3, cx + 2, cy + 3], fill=(200, 160, 100))
            if ck < 0.3:
                d.text((tx - 6, NY_FLOOR - 92), "PLOPP", font=self.f_tiny, fill=(255, 240, 200))
                for k in range(5):
                    d.point((tx + 10 + k - 2, NY_FLOOR - 72 - k * 2), fill=(250, 250, 220))
        d.ellipse([tx - 18, NY_FLOOR - 46, tx - 6, NY_FLOOR - 42], fill=(250, 240, 200))   # Schüssel (Wachs)
        d.line([(tx - 2, NY_FLOOR - 50), (tx - 2, NY_FLOOR - 42)], fill=(250, 250, 240), width=3)   # Kerze
        d.polygon([(tx - 4, NY_FLOOR - 51), (tx, NY_FLOOR - 51), (tx - 2, NY_FLOOR - 57)], fill=(255, 190, 60))
        # Leute
        sway = math.sin(t * math.pi / period) if playing else 0.0
        heads = []
        for i, (px, shirt, hat) in enumerate(NY_PEOPLE):
            pose = fig_dance_pose(st["k"] + i, level > 0.4, sway) if playing else dict(FIG_POSE_STAND)
            if i < 2 and (playing or talk):
                pose = dict(pose, rh=(14, -8) if i == 0 else pose["rh"], lh=(-14, -8) if i == 1 else pose["lh"])
            duck = 0.0
            if gname == "rakete" and 2.0 <= gl < 4.6:
                pose = {"lh": (-10, -16), "rh": (10, -16), "lf": (-10, 22), "rf": (10, 22)}
                duck = 1.0
            if gname == "wachs" and i == 2 and gl < 4.0:
                pose = {"lh": (-6, 20), "rh": (18, 0)}
            if gname in ("vorsaetze", "wunderkerze") and i == 2:
                pose = {"lh": (-8, 16), "rh": (16, -18 if gname == "wunderkerze" else 4)}
            hc, hands = self._fig(img, d, px + sway * 2, NY_FLOOR + duck * 0, t, shirt, pose, h=1.0 - 0.15 * duck,
                                  hat=hat, mouth=level if playing else 0.0, eyes="big" if duck else "dot")
            heads.append((hc, hands))
            if i < 2 and (playing or talk):                                         # Sektgläser
                hx, hy = hands[1] if i == 0 else hands[0]
                d.polygon([(hx - 3, hy - 9), (hx + 3, hy - 9), (hx + 1, hy - 2), (hx - 1, hy - 2)],
                          fill=(250, 230, 140))
                d.line([(hx, hy - 2), (hx, hy + 3)], fill=(220, 220, 230))
        if playing and t - s.get("beat_t", -9) < 0.12 and st["k"] % 4 == 0:
            d.text((134, NY_FLOOR - 104), "kling!", font=self.f_tiny, fill=(255, 240, 180))
        if talk:
            tl = t - s.get("talk_t", t)
            if tl < 3.0:
                say.append((heads[1][0][0], heads[1][0][1] - 28, "Ein Toast aufs neue Jahr!"))
            elif tl < 6.0:
                say.append((heads[0][0][0], heads[0][0][1] - 28, "… und aufs alte!"))
        # Höhepunkt: Countdown 3-2-1
        if boom:
            n = 3 - int(bt)
            font = load_font(64, bold=True)
            txt = str(n) if n > 0 else "PROSIT!"
            f2 = font if n > 0 else load_font(40, bold=True)
            w = d.textlength(txt, font=f2)
            d.text(((WIDTH - w) / 2 + 2, 52), txt, font=f2, fill=(80, 20, 20))
            d.text(((WIDTH - w) / 2, 50), txt, font=f2, fill=(255, 220, 80))
        if big:
            f2 = load_font(80, bold=True)
            w = d.textlength(big, font=f2)
            d.text(((WIDTH - w) / 2, 40), big, font=f2, fill=(255, 240, 200))
        if newyear:
            f2 = load_font(24, bold=True)
            txt = f"Frohes neues Jahr {fest_today().year}!"
            w = d.textlength(txt, font=f2)
            d.text(((WIDTH - w) / 2, 50), txt, font=f2, fill=(255, 230, 120))
        # Gags
        if gname == "wachs":
            self._ny_gag_wax(img, d, gl, t, say, heads[2], st)
        elif gname == "vorsaetze":
            self._ny_gag_resolutions(img, d, gl, t, say, heads[2])
        elif gname == "wunderkerze":
            self._ny_gag_sparkler(img, d, gl, t, say, heads[2], st)
        elif gname == "rakete":
            self._ny_gag_rocket(img, d, gl, t, say, st)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _ny_gag_wax(self, img, d, gl, t, say, who, st):
        """Wachsgießen: Löffel über der Kerze, ins Wasser, Figur hochhalten und deuten."""
        hc, hands = who
        hx, hy = hands[1]
        shape, meaning = NY_WAX[st["wax"] % len(NY_WAX)]
        if gl < 4.0:
            d.line([(hx, hy), (hx + 14, hy + 6)], fill=(200, 200, 210), width=2)
            d.ellipse([hx + 12, hy + 3, hx + 20, hy + 9], fill=(200, 200, 210))
            if gl < 3.0:
                d.ellipse([hx + 14, hy + 4, hx + 18, hy + 7], fill=(250, 200, 80))
            else:
                d.line([(hx + 16, hy + 8), (hx + 16, NY_FLOOR - 44)], fill=(250, 200, 80), width=2)
                d.text((hx + 20, hy - 6), "zisch!", font=self.f_tiny, fill=(220, 230, 250))
            if gl < 2.0:
                say.append((hc[0], hc[1] - 28, "Wachs, nicht Blei – Blei ist verboten!"))
            return
        cx, cy, r = 58, 82, 30                                                      # Lupe mit der Figur
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 240), outline=(140, 120, 80), width=4)
        d.line([(cx + r * 0.7, cy + r * 0.7), (cx + r * 1.2, cy + r * 1.2)], fill=(140, 120, 80), width=6)
        c = (230, 190, 80)
        if shape.endswith("Schiff"):
            d.polygon([(cx - 20, cy + 4), (cx + 20, cy + 4), (cx + 12, cy + 16), (cx - 12, cy + 16)], fill=c)
            d.polygon([(cx - 2, cy + 4), (cx - 2, cy - 20), (cx + 14, cy + 2)], fill=c)
        elif shape.endswith("Toaster?"):
            d.rounded_rectangle([cx - 18, cy - 10, cx + 18, cy + 14], radius=5, fill=c)
            for k in (-7, 5):
                d.rectangle([cx + k - 1, cy - 9, cx + k + 3, cy - 4], fill=(150, 110, 40))
        elif shape.endswith("Herz"):
            d.ellipse([cx - 16, cy - 14, cx, cy + 2], fill=c)
            d.ellipse([cx, cy - 14, cx + 16, cy + 2], fill=c)
            d.polygon([(cx - 16, cy - 4), (cx + 16, cy - 4), (cx, cy + 18)], fill=c)
        elif shape.endswith("Schwein"):
            self._blob(img, cx, cy + 2, 34, 22, c, gloss=0.5)
            self._blob(img, cx + 16, cy - 2, 12, 10, c, gloss=0.5)
            for k in (-10, 8):
                d.line([(cx + k, cy + 10), (cx + k, cy + 18)], fill=c, width=3)
        else:
            for k in range(5):
                self._blob(img, cx - 10 + k * 5, cy - 4 + (k % 2) * 8, 14, 12, c, gloss=0.5)
        if 4.4 <= gl < 6.6:
            say.append((cx, cy - r - 8, shape))
        elif gl >= 6.6:
            say.append((hc[0] - 20, hc[1] - 28, meaning))

    def _ny_gag_resolutions(self, img, d, gl, t, say, who):
        hc, hands = who
        hx, hy = hands[1]
        items = ["Mehr Sport", "Weniger Chips", "Früher ins Bett", "Keller aufräumen"]
        ln = min(1.0, gl / 1.2)
        x0, y0 = 222, 40
        d.line([(hx, hy), (x0 + 30, y0 + 66 * ln)], fill=(250, 246, 230))
        d.rectangle([x0, y0, x0 + 94, y0 + 8 + 60 * ln], fill=(250, 246, 230), outline=(180, 170, 140))
        for i, it in enumerate(items):
            yy = y0 + 4 + i * 14
            if yy > y0 + 60 * ln:
                break
            d.text((x0 + 3, yy), it, font=self.f_tiny, fill=(40, 40, 60))
            if gl > 3.0 + i * 0.6:
                d.line([(x0 + 2, yy + 7), (x0 + 92, yy + 7)], fill=(220, 40, 40), width=2)
        if 1.2 <= gl < 3.0:
            say.append((hc[0], hc[1] - 28, "Dieses Jahr wird alles anders!"))
        elif gl >= 5.6:
            say.append((hc[0], hc[1] - 28, "Ab morgen. Ganz bestimmt."))

    def _ny_gag_sparkler(self, img, d, gl, t, say, who, st):
        """Die Wunderkerze schreibt die Jahreszahl in die Luft."""
        hc, hands = who
        year = str(_ny_year(fest_today()))
        font = load_font(34, bold=True)
        k = min(1.0, gl / 5.0)
        x0, y0 = 150, 60
        mask = Image.new("L", (130, 44), 0)
        ImageDraw.Draw(mask).text((2, 0), year, font=font, fill=255)
        w = int(130 * k)
        if w > 0:
            glow = Image.new("RGB", (w, 44), (255, 230, 140))
            img.paste(glow, (x0, y0), mask.crop((0, 0, w, 44)))
        hx, hy = hands[1]
        tip = (x0 + w, y0 + 20 + math.sin(gl * 9) * 10)
        d.line([(hx, hy), tip], fill=(130, 130, 140), width=1)
        for kk in range(10):
            a = gl * 30 + kk * 0.63
            r = 2 + (gl * 50 + kk * 5) % 8
            d.point((tip[0] + math.cos(a) * r, tip[1] + math.sin(a) * r), fill=(255, 250, 200))
        if gl > 5.6:
            say.append((hc[0], hc[1] - 28, "Schön, oder?"))

    def _ny_gag_rocket(self, img, d, gl, t, say, st):
        """Eine Rakete in der Flasche kippt um und saust waagerecht über die Terrasse."""
        bx, by = 40, NY_FLOOR - 26
        tip = 0.0 if gl < 2.0 else min(1.0, (gl - 2.0) / 0.3)
        a = -math.pi / 2 + tip * math.pi / 2
        d.polygon([(bx - 4, by), (bx + 4, by), (bx + 3, by - 14), (bx - 3, by - 14)], fill=(50, 110, 60))
        if gl < 2.2:
            rx, ry = bx + math.cos(a) * 16, by - 14 + math.sin(a) * 16 + 14
            d.line([(bx, by - 14), (rx, ry - 6)], fill=(200, 60, 60), width=3)
            for k in range(4):
                d.point((bx + st["rng"].uniform(-3, 3), by - 14 + st["rng"].uniform(-3, 3)), fill=(255, 220, 120))
            if gl < 1.6:
                say.append((bx + 10, by - 40, "Zündschnur brennt …"))
        elif gl < 4.6:
            f = (gl - 2.2) / 2.4
            rx = bx + f * 320
            ry = NY_FLOOR - 50 + math.sin(f * 20) * 12
            d.line([(rx - 14, ry), (rx, ry)], fill=(200, 60, 60), width=3)
            for k in range(8):
                d.point((rx - 16 - k * 4, ry + st["rng"].uniform(-3, 3)), fill=(255, 200, 80))
            say.append((160, NY_FLOOR - 120, "Andersrum!!"))
        elif gl < 5.2:
            img.paste((255, 250, 230), (0, 0, WIDTH, VIS_H), Image.new("L", (WIDTH, VIS_H), int(120 * (5.2 - gl))))
