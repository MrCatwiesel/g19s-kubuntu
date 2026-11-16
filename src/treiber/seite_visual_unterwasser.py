"""Visualisierung „Unterwasser“ (underwater, Mixin UnderwaterVisual): Die Band am Meeresgrund. Ein Oktopus trommelt
mit acht Armen auf Muscheln, Quallen pulsieren im Bass (und leuchten bunt), ein Fischschwarm zieht im Takt seine
Bahn, die Krabbe tanzt mit den Scheren, Seegras wiegt sich, Luftblasen steigen auf hohe Schläge, Lichtstrahlen fallen
von oben ein. Höhepunkt: Der Schwarm formt einen riesigen Fisch, die Quallen werden zur Lichtorgel. Wortbeitrag: Ein
Taucher schreibt die Durchsage auf seine Tafel („Blubb.“). Gags: Flaschenpost, ein Kugelfisch erschrickt sich am
Bass, und mit Gänsehaut: Ein Hai kreist – stellt sich aber als Vegetarier heraus.
"""
import math
import random

UW_FLOOR = VIS_H - 20
UW_OCTO = (160, UW_FLOOR - 30)
UW_JELLY = [(46, 70), (276, 60), (226, 108)]
UW_GAGS = {"flaschenpost": 8.0, "kugelfisch": 7.0, "hai": 9.0}
UW_GAG_FIRST, UW_GAG_PAUSE = 8.0, (12.0, 20.0)
UW_BOOM = 5.0
UW_FISH = 22


class UnderwaterVisual:
    vis_sea = None

    def _uw_scene(self):
        if "_uw_bg" in self.__dict__:
            return self._uw_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([40, 140, 190], np.float32), np.array([6, 30, 70], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        d.polygon([(0, UW_FLOOR - 6), (80, UW_FLOOR - 14), (200, UW_FLOOR - 4), (320, UW_FLOOR - 12), (320, HEIGHT),
                   (0, HEIGHT)], fill=(194, 176, 120))
        rng = random.Random(6)
        for _ in range(60):
            x, y = rng.uniform(0, WIDTH), rng.uniform(UW_FLOOR - 4, HEIGHT)
            d.point((x, y), fill=(170, 150, 100))
        for x, w, h in ((20, 40, 22), (290, 50, 30), (110, 30, 14)):                # Felsen
            self._blob(img, x, UW_FLOOR - h / 3, w, h, (90, 90, 100), gloss=0.3)
        for x, c in ((70, (240, 110, 120)), (250, (250, 170, 80)), (200, (190, 110, 220))):   # Korallen
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.35
                d.line([(x, UW_FLOOR - 4), (x + math.cos(a) * 18, UW_FLOOR - 4 + math.sin(a) * 22)], fill=c, width=4)
                self._blob(img, x + math.cos(a) * 18, UW_FLOOR - 4 + math.sin(a) * 22, 6, 6, c, gloss=0.4)
        rays = Image.new("L", (WIDTH, HEIGHT), 0)                                   # Lichtstrahlen
        rd = ImageDraw.Draw(rays)
        for x in (40, 120, 210, 280):
            rd.polygon([(x - 6, 0), (x + 10, 0), (x + 40, UW_FLOOR), (x + 10, UW_FLOOR)], fill=26)
        img.paste((220, 250, 255), (0, 0), rays)
        self._uw_bg = img
        return img

    def _uw_fish(self, d, x, y, face, col, s=1.0):
        d.ellipse([x - 6 * s, y - 3 * s, x + 6 * s, y + 3 * s], fill=col)
        d.polygon([(x - face * 5 * s, y), (x - face * 10 * s, y - 4 * s), (x - face * 10 * s, y + 4 * s)], fill=col)
        d.point((x + face * 3 * s, y - 1), fill=(10, 10, 20))

    def _uw_jelly(self, img, d, x, y, t, pulse, col):
        w = 26 - 8 * pulse
        h = 16 + 4 * pulse
        self._blob(img, x, y, w * 2.2, h * 2.2, col, alpha=0.25, flat=True)
        d.chord([x - w / 2, y - h, x + w / 2, y + h * 0.3], 180, 360, fill=col)
        for k in range(5):
            tx = x - w / 2 + 3 + k * (w - 6) / 4
            pts = [(tx + math.sin(t * 3 + k + j * 0.8) * 3, y + j * 6) for j in range(5)]
            d.line(pts, fill=col, width=1)

    @vis_style("underwater")
    def vis_underwater(self, s, o, color):
        t = s["t"]
        img = self._uw_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("underwater", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                                  "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                                  "next_gag": t + UW_GAG_FIRST, "rng": random.Random(131), "start": t,
                                                  "bubbles": [], "ph": 0.0, "dir": 1, "puff": -9.0})
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
        boom = 0 <= bt < UW_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= UW_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*UW_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                pool = [g_ for g_ in UW_GAGS if o.get("spooky", True) or g_ != "hai"]
                st["order"] = st["rng"].sample(pool, len(pool))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        rng = st["rng"]
        say = []
        if playing and new_beat:
            st["k"] += 1
            if st["k"] % 8 == 0:
                st["dir"] = -st["dir"]
        dark = 0.0
        if gname == "hai":
            dark = min(1.0, gl / 1.0, max(0.0, (6.0 - gl) / 0.8))
        # Seegras
        for x in (14, 96, 136, 186, 236, 300):
            pts = [(x + math.sin(t * 1.5 + x + j * 0.6) * (2 + j) * (1 + level), UW_FLOOR - 4 - j * 10)
                   for j in range(6)]
            d.line(pts, fill=(60, 150, 80), width=3)
        # Quallen
        for i, (jx, jy) in enumerate(UW_JELLY):
            pulse = max(0.0, 1 - (t - s.get("beat_t", -9)) / 0.3) if playing else 0.0
            col = _hue((t * 0.1 + i / 3) % 1.0, 0.5, 1.0) if boom else [(240, 160, 220), (160, 200, 255), (200, 170, 255)][i]
            self._uw_jelly(img, d, jx + math.sin(t * 0.4 + i) * 10, jy + math.sin(t * 0.7 + i * 2) * 8 - pulse * 6, t,
                           pulse, col)
        # Fischschwarm
        st["ph"] += dt * st["dir"] * (0.4 + level * 1.2) * (0 if gname == "hai" and gl > 1.5 else 1)
        cols = [(250, 200, 60), (250, 140, 60), (120, 200, 250)]
        for i in range(UW_FISH):
            a = st["ph"] + i * 0.28
            if boom:                                                                # Großer Fisch aus Fischen
                k = min(1.0, bt / 0.8, (UW_BOOM - bt) / 0.8)
                u = i / UW_FISH * 6.283
                bx_, by_ = 160 + math.cos(u) * 70, 80 + math.sin(u) * 26
                if i > UW_FISH - 5:
                    bx_, by_ = 90 - (i - UW_FISH + 5) * 6, 80 + ((i % 2) * 2 - 1) * (i - UW_FISH + 5) * 7
                fx = bx_ * k + (160 + math.cos(a) * 120) * (1 - k)
                fy = by_ * k + (90 + math.sin(a * 2) * 30) * (1 - k)
                face = 1
            else:
                fx = 160 + math.cos(a) * 120
                fy = 90 + math.sin(a * 2) * 30 + math.sin(i) * 8
                if gname == "hai" and gl > 1.5:
                    fx += math.cos(i) * 200 * min(1.0, (gl - 1.5) / 1.0)
                face = -1 if math.sin(a) * st["dir"] > 0 else 1
            self._uw_fish(d, fx, fy, face, cols[i % 3])
        if boom and 1.0 < bt < 3.6:
            say.append((160, 40, "Wir sind ein großer Fisch!"))
        # Oktopus am Muschel-Schlagzeug
        ox, oy = UW_OCTO
        for k, sx in enumerate((-40, -20, 20, 40)):                                 # Muscheltrommeln
            d.chord([ox + sx - 11, oy + 6, ox + sx + 11, oy + 26], 180, 360, fill=[(250, 200, 190), (240, 220, 180)][k % 2])
            for j in range(4):
                d.line([(ox + sx, oy + 16), (ox + sx - 10 + j * 7, oy + 8)], fill=(200, 150, 140))
        for k in range(8):
            side = -1 if k < 4 else 1
            base = (ox + side * 8, oy + 2)
            hit = playing and (st["k"] + k) % 4 == 0
            tgt = (ox + [-40, -20, 20, 40][(k % 4)] + side * 2, oy + (8 if hit else -2 - 6 * bang))
            if talk:
                tgt = (ox + side * (18 + k % 4 * 6), oy + 22)
            pts = []
            for j in range(6):
                f = j / 5
                pts.append((base[0] + (tgt[0] - base[0]) * f + math.sin(t * 4 + k + f * 3) * 4 * (1 - f),
                            base[1] + (tgt[1] - base[1]) * f - math.sin(f * math.pi) * 10))
            d.line(pts, fill=(200, 70, 110), width=5)
        self._blob(img, ox, oy - 16 - bang * 3, 36, 40, (220, 80, 120), gloss=0.5)
        for side in (-1, 1):
            d.ellipse([ox + side * 7 - 5, oy - 20, ox + side * 7 + 5, oy - 10], fill=(255, 255, 255))
            d.ellipse([ox + side * 7 - 2, oy - 17, ox + side * 7 + 2, oy - 12], fill=(20, 20, 30))
        d.arc([ox - 6, oy - 10, ox + 6, oy - 2], 10, 170, fill=(120, 30, 60), width=2)
        # Krabbe tanzt
        cx = 250 + math.sin(t * 2) * 10
        self._blob(img, cx, UW_FLOOR - 8, 22, 12, (230, 80, 50), gloss=0.5)
        for side in (-1, 1):
            up = (st["k"] % 2 == (side > 0)) and playing
            d.line([(cx + side * 8, UW_FLOOR - 10), (cx + side * 16, UW_FLOOR - 22 - (8 if up else 0))], fill=(230, 80, 50),
                   width=3)
            self._blob(img, cx + side * 17, UW_FLOOR - 26 - (8 if up else 0), 9, 7, (230, 80, 50), gloss=0.5)
            for j in range(3):
                d.line([(cx + side * (4 + j * 3), UW_FLOOR - 6), (cx + side * (8 + j * 3), UW_FLOOR)], fill=(200, 60, 40))
            d.line([(cx + side * 3, UW_FLOOR - 13), (cx + side * 4, UW_FLOOR - 19)], fill=(230, 80, 50))
            d.ellipse([cx + side * 4 - 1.5, UW_FLOOR - 21, cx + side * 4 + 1.5, UW_FLOOR - 18], fill=(10, 10, 10))
        # Luftblasen
        if playing and new_hat:
            for _ in range(2):
                st["bubbles"].append([rng.uniform(20, 300), UW_FLOOR - 10, rng.uniform(2, 4)])
        for b in st["bubbles"]:
            b[1] -= (30 + b[2] * 6) * dt
            b[0] += math.sin(t * 3 + b[1] * 0.1) * 0.4
        st["bubbles"] = [b for b in st["bubbles"] if b[1] > -5][-40:]
        for x, y, r in st["bubbles"]:
            d.ellipse([x - r, y - r, x + r, y + r], outline=(220, 240, 255))
        # Taucher bei Wortbeiträgen
        if talk:
            tl = t - s.get("talk_t", t)
            dx_, dy_ = 70 + math.sin(t * 0.8) * 6, 120 + math.sin(t * 1.3) * 4
            hc, hands = self._fig(img, d, dx_, dy_, t, (30, 30, 40), {"lh": (-12, 4), "rh": (14, -6),
                                                                       "lf": (-14, 26), "rf": (10, 30)},
                                  h=0.85, hat="helmet", hat_col=(200, 220, 240), legs=(30, 30, 40))
            d.rectangle([dx_ - 18, dy_ - 46, dx_ - 6, dy_ - 22], fill=(240, 200, 40))   # Flasche
            hx, hy = hands[1]
            d.rectangle([hx, hy - 20, hx + 40, hy + 4], fill=(240, 240, 240), outline=(100, 100, 110))
            d.text((hx + 3, hy - 18), "DURCH-", font=self.f_tiny, fill=(20, 40, 120))
            d.text((hx + 3, hy - 7), "SAGE", font=self.f_tiny, fill=(20, 40, 120))
            for k in range(3):
                by = hc[1] - 14 - ((t * 30 + k * 10) % 40)
                d.ellipse([hc[0] - 2 + k, by - 2, hc[0] + 2 + k, by + 2], outline=(220, 240, 255))
            if tl < 3.0:
                say.append((hc[0], hc[1] - 30, "Blubb."))
        if gname == "flaschenpost":
            k = min(1.0, gl / 2.0)
            bx, by = 120, 10 + k * (UW_FLOOR - 16)
            d.rectangle([bx - 3, by - 14, bx + 3, by], fill=(120, 180, 120), outline=(70, 120, 70))
            d.rectangle([bx - 1.5, by - 18, bx + 1.5, by - 14], fill=(150, 110, 60))
            if gl > 2.4:
                d.rectangle([bx - 50, by - 64, bx + 62, by - 34], fill=(240, 230, 200), outline=(170, 150, 110))
                d.text((bx - 46, by - 62), "Bitte leiser,", font=self.f_tiny, fill=(60, 40, 30))
                d.text((bx - 46, by - 49), "die Wale schlafen!", font=self.f_tiny, fill=(60, 40, 30))
            if gl > 5.0:
                say.append((cx, UW_FLOOR - 40, "Pfff. Lauter!"))
        elif gname == "kugelfisch":
            px, py = 90 + math.sin(gl * 2) * 20, 140
            puff = 0.0
            if gl > 1.5:
                puff = min(1.0, (gl - 1.5) / 0.3) if gl < 5.0 else max(0.0, 1 - (gl - 5.0) / 1.0)
            r = 8 + 10 * puff
            self._blob(img, px, py, r * 2, r * 2, (230, 200, 90), gloss=0.5)
            if puff > 0.3:
                for k in range(12):
                    a = k * 0.52
                    d.line([(px + math.cos(a) * r, py + math.sin(a) * r),
                            (px + math.cos(a) * (r + 5), py + math.sin(a) * (r + 5))], fill=(200, 160, 60))
            d.ellipse([px + r * 0.3 - 2, py - r * 0.4 - 2, px + r * 0.3 + 2, py - r * 0.4 + 2], fill=(10, 10, 20))
            if 1.6 <= gl < 4.0:
                say.append((px, py - r - 14, "Huch! Der Bass!"))
        elif gname == "hai" and dark:
            img = Image.blend(img, Image.new("RGB", img.size, (2, 10, 30)), 0.6 * dark)
            d = ImageDraw.Draw(img)
            a = gl * 1.4
            sx, sy = 160 + math.cos(a) * 110, 70 + math.sin(a) * 20
            face = -1 if math.sin(a) > 0 else 1
            self._blob(img, sx, sy, 80, 24, (110, 120, 140), gloss=0.4)
            d.polygon([(sx - 4, sy - 10), (sx + 8, sy - 10), (sx, sy - 28)], fill=(110, 120, 140))
            d.polygon([(sx - face * 38, sy), (sx - face * 52, sy - 14), (sx - face * 52, sy + 12)], fill=(110, 120, 140))
            d.ellipse([sx + face * 26 - 2, sy - 6, sx + face * 26 + 2, sy - 2], fill=(10, 10, 10))
            if gl > 4.0:
                mx0, mx1 = sorted((sx + face * 14, sx + face * 34))
                d.arc([mx0, sy - 2, mx1, sy + 8], 0, 180, fill=(250, 250, 250), width=2)
        if gname == "hai" and gl > 4.0:
            say.append((160, 44, "Keine Angst – ich bin Vegetarier!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_sea = (0, int(120 + 100 * level), 255) if not boom else _hue((t * 0.2) % 1.0, 0.7, 1.0)
        return img
