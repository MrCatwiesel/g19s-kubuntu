"""Visualisierung „Weltraum-Disco“ (space, Mixin SpaceVisual): Ein Ringplanet dient als Spiegelkugel und wirft bunte
Lichtflecken, zwei Astronauten tanzen schwerelos (Saltos in Zeitlupe), die Sterne ziehen je nach Lautstärke schneller
vorbei, Sternschnuppen auf hohe Schläge. Höhepunkt: Turbo-Boost – die Sterne werden zu Streifen. Wortbeitrag: Die
Bodenstation funkt dazwischen. Gags: Ein UFO landet und das Alien tanzt mit, der Kakao schwebt als Kugel davon,
ein Satellit rauscht knapp vorbei.
"""
import math
import random

SP_PLANET = (226, 64)
SP_ASTRO = [(98, 120), (170, 140)]
SP_GAGS = {"alien": 9.0, "kakao": 7.0, "satellit": 7.0}
SP_GAG_FIRST, SP_GAG_PAUSE = 8.0, (12.0, 20.0)
SP_BOOM = 4.0
SP_STARS = 90


class SpaceVisual:
    vis_col_space = None

    def _sp_scene(self):
        if "_sp_bg" in self.__dict__:
            return self._sp_bg
        img = Image.new("RGB", (WIDTH, HEIGHT), (4, 4, 16))
        neb = Image.new("L", (WIDTH, HEIGHT), 0)
        nd = ImageDraw.Draw(neb)
        rng = random.Random(9)
        for _ in range(14):
            x, y, r = rng.uniform(0, WIDTH), rng.uniform(0, VIS_H), rng.uniform(30, 70)
            nd.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=rng.randint(10, 26))
        img.paste((120, 40, 160), (0, 0), neb)
        self._sp_bg = img
        rs = random.Random(10)
        self._sp_stars = [(rs.uniform(0, WIDTH), rs.uniform(0, VIS_H), rs.uniform(0.3, 1.0)) for _ in range(SP_STARS)]
        return img

    def _sp_astro(self, img, d, x, y, t, ang, wave, col):
        """Astronaut im Raumanzug, um ang gedreht (schwerelos)."""
        def R(px, py):
            return _hr_rot((x + px, y + py), (x, y), ang)
        suit = (240, 240, 246)
        self._blob(img, *R(0, 4), 22, 28, suit, gloss=0.4, ang=ang)
        d.rectangle([R(-6, -2)[0] - 2, R(-6, -2)[1] - 2, R(-6, -2)[0] + 4, R(-6, -2)[1] + 4], fill=col)
        for side in (-1, 1):
            a = math.sin(wave + side) * 0.8
            self._limb(img, R(side * 9, -2), R(side * (16 + 4 * math.cos(a)), -10 + 12 * math.sin(a)), 6, suit)
            self._limb(img, R(side * 5, 16), R(side * (8 + 4 * math.sin(wave)), 30), 7, suit)
        hc = R(0, -16)
        self._blob(img, hc[0], hc[1], 20, 20, suit, gloss=0.4)
        self._blob(img, hc[0], hc[1] + 1, 14, 12, (40, 60, 110), gloss=0.9)
        self._blob(img, hc[0] - 3, hc[1] - 2, 4, 3, (255, 255, 255), alpha=0.7, flat=True)
        d.line([R(9, 0), R(18, -4)], fill=(200, 200, 210), width=2)                  # Antenne/Schlauch
        return hc

    @vis_style("space")
    def vis_space(self, s, o, color):
        t = s["t"]
        img = self._sp_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("space", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                             "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                             "next_gag": t + SP_GAG_FIRST, "rng": random.Random(151), "start": t,
                                             "drift": 0.0, "shoot": [], "spin": [0.0, 1.5]})
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
        boom = 0 <= bt < SP_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= SP_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*SP_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(SP_GAGS), len(SP_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        rng = st["rng"]
        say = []
        if playing and new_beat:
            st["k"] += 1
        # Sterne ziehen vorbei (Turbo: Streifen)
        speed = 6 + 60 * level + (400 if boom and 0.5 < bt < 3.2 else 0)
        st["drift"] += dt * speed
        for sx, sy, z in self._sp_stars:
            x = (sx - st["drift"] * z) % WIDTH
            c = int(120 + 135 * z)
            if speed > 120:
                d.line([(x, sy), (x + speed * 0.04 * z, sy)], fill=(c, c, 255))
            else:
                d.point((x, sy), fill=(c, c, c))
        if playing and new_hat and rng.random() < 0.3:
            st["shoot"].append([rng.uniform(40, 320), rng.uniform(0, 60), t])
        for sh in list(st["shoot"]):
            k = (t - sh[2]) / 0.6
            if k > 1:
                st["shoot"].remove(sh)
                continue
            d.line([(sh[0] - k * 80, sh[1] + k * 40), (sh[0] - k * 80 + 14, sh[1] + k * 40 - 7)], fill=(255, 255, 220),
                   width=2)
        # Ringplanet als Spiegelkugel
        px, py = SP_PLANET
        d.ellipse([px - 46, py - 8, px + 46, py + 12], outline=(220, 190, 140), width=3)
        self._blob(img, px, py, 50, 50, (200, 120, 90), gloss=0.5)
        for k in range(4):
            d.arc([px - 25, py - 25 + k * 10, px + 25, py - 15 + k * 10], 200, 340, fill=(170, 90, 70))
        d.arc([px - 46, py - 8, px + 46, py + 12], 0, 180, fill=(230, 200, 150), width=3)
        if playing:
            spots = Image.new("L", img.size, 0)
            sd = ImageDraw.Draw(spots)
            for k in range(10):
                a = t * 0.8 + k * 0.63
                r = 70 + 50 * ((k * 37) % 10) / 10
                x, y = px + math.cos(a) * r * 1.4, py + 40 + math.sin(a) * r * 0.6
                sd.ellipse([x - 4, y - 3, x + 4, y + 3], fill=int(140 * level + 40))
            img.paste(_hue((t * 0.1) % 1.0, 0.6, 1.0), (0, 0), spots)
            d = ImageDraw.Draw(img)
        # Astronauten
        heads = []
        for i, (ax, ay) in enumerate(SP_ASTRO):
            st["spin"][i] += dt * (0.3 + level * 1.4) * (1 if i else -1) * (0 if talk else 1)
            bob = math.sin(t * 0.9 + i * 2) * 10
            hc = self._sp_astro(img, d, ax + math.sin(t * 0.5 + i) * 12, ay + bob, t, st["spin"][i],
                                t * 3 + i if playing else 0, [(230, 60, 60), (60, 140, 230)][i])
            heads.append(hc)
        if talk:
            tl = t - s.get("talk_t", t)
            d.rounded_rectangle([8, VIS_H - 40, 150, VIS_H - 8], radius=4, fill=(20, 30, 40), outline=(90, 200, 120))
            d.text((14, VIS_H - 38), "BODENSTATION", font=self.f_tiny, fill=(90, 200, 120))
            n = int(tl * 12)
            d.text((14, VIS_H - 24), "Achtung, Durchsage …"[:n], font=self.f_tiny, fill=(200, 250, 210))
            if tl > 2.5:
                say.append((heads[0][0], heads[0][1] - 20, "Verstanden. Wir schweben."))
        if boom and 0.5 < bt < 3.0:
            say.append((160, 30, "Turbo-Boost!"))
        if gname == "alien":
            k = min(1.0, gl / 1.5)
            ux, uy = 60, 20 + k * 30
            d.ellipse([ux - 30, uy - 6, ux + 30, uy + 8], fill=(160, 170, 190))
            self._blob(img, ux, uy - 6, 26, 18, (150, 230, 255), gloss=0.8, alpha=0.8)
            for j in range(5):
                d.ellipse([ux - 24 + j * 12 - 2, uy + 1, ux - 24 + j * 12 + 2, uy + 5],
                          fill=_hue((j / 5 + t) % 1.0, 0.8, 1.0))
            if gl > 1.5:
                beam = Image.new("L", img.size, 0)
                ImageDraw.Draw(beam).polygon([(ux - 10, uy + 6), (ux + 10, uy + 6), (ux + 26, uy + 80), (ux - 26, uy + 80)],
                                             fill=60)
                img.paste((180, 255, 180), (0, 0), beam)
                d = ImageDraw.Draw(img)
                ay = uy + 70 - min(1.0, (gl - 1.5) / 1.5) * 10
                self._blob(img, ux, ay, 14, 20, (120, 220, 120), gloss=0.4)
                self._blob(img, ux, ay - 16, 16, 14, (120, 220, 120), gloss=0.4)
                for side in (-1, 1):
                    d.ellipse([ux + side * 4 - 3, ay - 20, ux + side * 4 + 3, ay - 14], fill=(10, 10, 10))
                    d.line([(ux + side * 3, ay - 22), (ux + side * 7, ay - 30)], fill=(120, 220, 120), width=2)
                    robo = (st["k"] + (side > 0)) % 2
                    d.line([(ux + side * 6, ay - 6), (ux + side * 14, ay - (16 if robo else 0))], fill=(120, 220, 120),
                           width=3)
                if 3.0 <= gl < 5.6:
                    say.append((ux + 30, ay - 40, "Bliep! Gute Musik!"))
                elif gl >= 5.8:
                    say.append((heads[0][0], heads[0][1] - 24, "Kennt der den Roboter?"))
        elif gname == "kakao":
            hx, hy = heads[1]
            k = gl / SP_GAGS["kakao"]
            bx, by = hx + 20 + k * 120 + math.sin(gl * 3) * 10, hy - 10 - math.sin(gl * 1.7) * 20
            r = 7 + math.sin(gl * 6) * 1.5
            self._blob(img, bx, by, r * 2.2, r * 1.8, (130, 80, 40), gloss=0.8)
            if gl > 0.5:
                say.append((hx, hy - 24, "Mein Kakao!"))
        elif gname == "satellit":
            k = gl / SP_GAGS["satellit"]
            sx, sy = -40 + k * 420, 40 + k * 60
            d.rectangle([sx - 8, sy - 6, sx + 8, sy + 6], fill=(200, 190, 120))
            for side in (-1, 1):
                p0, p1 = sorted((sx + side * 10, sx + side * 30))
                d.rectangle([p0, sy - 4, p1, sy + 4], fill=(40, 70, 160), outline=(160, 170, 190))
            d.line([(sx, sy - 6), (sx + 4, sy - 16)], fill=(200, 200, 200), width=2)
            if 2.0 <= gl < 4.6:
                say.append((heads[0][0], heads[0][1] - 24, "Ducken!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        self.vis_col_space = _hue((t * 0.1) % 1.0, 0.6, 1.0) if playing else (40, 40, 120)
        return img
