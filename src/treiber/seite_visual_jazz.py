"""Visualisierung „Lounge / Jazz-Club“ (jazz, Mixin JazzVisual): Samtvorhang, Holzbühne, ein weicher Spotlight-Kegel.
Links schwingt der Kontrabass im Bass (Saiten vibrieren, der Lichtkreis am Boden weitet sich), in der Mitte wiegt sich
der Saxophonist bzw. die Sängerin mit den Mitten – aus dem Schallbecher steigen goldene Klangfunken –, vorne rechts
glüht die Zigarette im Aschenbecher auf hohe Schläge auf und zieht ihre Rauchfahne, der Eiswürfel im Glas hüpft im
Takt. Höhepunkt: „SOLO!“ – das Licht geht auf, der Solist lehnt sich zurück. Wortbeitrag: Ansage am Mikrofon.
Gags: Der Eiswürfel springt in den Aschenbecher, Trinkgeld klimpert ins Glas, die Zigarette bläst Rauchringe.
"""
import math
import random

JZ_PAL = {
    "red":     {"bg": (18, 5, 8),  "curtain": (75, 14, 26), "spot": (255, 70, 90),  "accent": (255, 195, 90)},
    "amber":   {"bg": (20, 12, 4), "curtain": (80, 44, 12), "spot": (255, 165, 50), "accent": (255, 225, 130)},
    "blue":    {"bg": (6, 10, 24), "curtain": (20, 36, 86), "spot": (70, 135, 255), "accent": (180, 220, 255)},
    "emerald": {"bg": (5, 18, 14), "curtain": (16, 66, 50), "spot": (55, 210, 150), "accent": (220, 245, 175)},
}
JZ_GAGS = {"eis": 6.0, "trinkgeld": 7.0, "rauchring": 6.0}
JZ_GAG_FIRST, JZ_GAG_PAUSE = 8.0, (14.0, 24.0)
JZ_BOOM = 4.0
JZ_SIL = (10, 8, 12)                            # Silhouetten der Musiker
JZ_STAGE = VIS_H - 38                           # Bühnenkante
JZ_BASS_X, JZ_SOLO_X, JZ_TABLE_X, JZ_JAR_X = 82, 165, 266, 30


class JazzVisual:
    vis_col_jazz = None

    def _jz_scene(self, mood):
        """Hintergrund je Clublicht (zwischengespeichert): Samtvorhang mit Falten, Holzbühne."""
        cache = self.__dict__.setdefault("_jz_bg", {})
        if mood in cache:
            return cache[mood]
        pal = JZ_PAL[mood]
        img = Image.new("RGB", (WIDTH, HEIGHT), pal["bg"])
        d = ImageDraw.Draw(img)
        for x in range(0, WIDTH, 16):
            for k in range(16):
                shade = math.cos((k - 7.5) / 8 * math.pi / 2)                 # Falte: in der Mitte hell
                d.line([(x + k, 0), (x + k, JZ_STAGE)], fill=tuple(int(v * (0.45 + 0.55 * shade)) for v in pal["curtain"]))
        d.rectangle([0, JZ_STAGE, WIDTH, VIS_H], fill=(24, 15, 10))
        for y in range(JZ_STAGE + 6, VIS_H, 6):
            d.line([(0, y), (WIDTH, y)], fill=(32, 20, 13))
        d.line([(0, JZ_STAGE), (WIDTH, JZ_STAGE)], fill=(65, 42, 26), width=2)
        cache[mood] = img
        return img

    @vis_style("jazz")
    def vis_jazz(self, s, o, color):
        t = s["t"]
        mood = o.get("mood") if o.get("mood") in JZ_PAL else "red"
        pal = JZ_PAL[mood]
        soloist = o.get("soloist", "sax")
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("jazz", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": 0.0, "fast": 0.0,
                                            "boom": -99.0, "gag": None, "order": [], "next_gag": t + JZ_GAG_FIRST,
                                            "rng": random.Random(73), "start": t, "bass": 0.0, "mid": 0.0,
                                            "glow": 0.0, "ice": 0.0})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
        playing = (s.get("active") or demo) and not talk

        def val(key):
            v = float(s.get(key) or 0.0)
            return v if playing and math.isfinite(v) else 0.0

        st["bass"] += (val("bass") - st["bass"]) * min(1.0, dt / 0.15)
        st["mid"] += (val("mid") - st["mid"]) * min(1.0, dt / 0.3)
        bass, mid, treble = st["bass"], st["mid"], val("treble")
        st["glow"] = 1.0 if (new_hat and playing) else max(treble, st["glow"] - dt * 2.5)
        st["ice"] = 1.0 if (new_beat and playing) else max(0.0, st["ice"] - dt * 5)
        level = val("level")
        st["slow"] += (level - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (level - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < JZ_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= JZ_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*JZ_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(JZ_GAGS), len(JZ_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        say = []

        # 1. Spotlight-Kegel (vor den Figuren, weich über einer RGBA-Ebene)
        img = self._jz_scene(mood).copy().convert("RGBA")
        ov = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        spot_x = JZ_BASS_X if soloist == "bass" else JZ_SOLO_X
        spread = 60 + bass * 22 + (28 if boom else 0)
        alpha = int(30 + bass * 42 + (45 if boom else 0))
        od.polygon([(spot_x - 14, 0), (spot_x + 14, 0), (spot_x + spread, VIS_H - 24), (spot_x - spread, VIS_H - 24)],
                   fill=(*pal["spot"], alpha))
        od.ellipse([spot_x - spread, VIS_H - 34, spot_x + spread, VIS_H - 14], fill=(*pal["spot"], min(150, alpha + 30)))
        img = Image.alpha_composite(img, ov)
        d = ImageDraw.Draw(img)

        # 2. Kontrabass mit Bassist (schwingt im Bass, Saiten vibrieren, rechte Hand zupft im Takt)
        bx = JZ_BASS_X + int(math.sin(t * 2.2) * (2 + bass * 5))
        by = VIS_H - 32
        d.ellipse([bx - 24, by - 102, bx - 8, by - 86], fill=JZ_SIL)                  # Kopf
        d.line([(bx - 28, by - 96), (bx - 4, by - 98)], fill=JZ_SIL, width=3)          # Hutkrempe
        d.rectangle([bx - 22, by - 106, bx - 10, by - 97], fill=JZ_SIL)
        d.polygon([(bx - 26, by - 86), (bx - 6, by - 84), (bx - 4, by - 15), (bx - 28, by - 15)], fill=JZ_SIL)
        d.line([(bx - 4, by - 114), (bx + 4, by - 55)], fill=(95, 58, 28), width=4)    # Hals
        d.ellipse([bx - 4, by - 125, bx + 5, by - 115], fill=(95, 58, 28))             # Schnecke
        pulse = int(bass * 3)
        d.ellipse([bx - 16 - pulse, by - 64, bx + 20 + pulse, by - 32], fill=(115, 62, 24), outline=(45, 22, 8))
        d.ellipse([bx - 20 - pulse, by - 40, bx + 24 + pulse, by - 4], fill=(115, 62, 24), outline=(45, 22, 8))
        d.line([(bx + 2, by - 4), (bx + 2, by + 6)], fill=(180, 180, 180), width=2)    # Stachel
        vib = math.sin(t * 45) * bass * 2.5
        for so in (-2, 0, 2):
            d.line([(bx + so, by - 114), (bx + so + vib, by - 22)], fill=(225, 210, 175))
        pluck = 4 * st["ice"]
        d.line([(bx - 12, by - 60), (bx + 2 + pluck, by - 34)], fill=JZ_SIL, width=4)   # Zupfhand
        d.line([(bx - 14, by - 80), (bx - 2, by - 96)], fill=JZ_SIL, width=4)           # Griffhand

        # 3. Solist in der Bühnenmitte
        sx, sy = JZ_SOLO_X, VIS_H - 26
        sway = math.sin(t * (2.6 + mid * 2.0)) * (4 + mid * 7)
        bell = None
        head = (JZ_BASS_X - 16, by - 94)
        if soloist == "sax":
            lean = int(mid * 6 + (8 if boom and 0.3 < bt < 3.4 else 0))
            hx, hy = sx + int(sway) - lean, sy - 98
            head = (hx, hy)
            d.ellipse([hx - 8, hy - 8, hx + 8, hy + 8], fill=JZ_SIL)                     # Kopf mit Fedora
            d.line([(hx - 14, hy - 5), (hx + 14, hy - 7)], fill=JZ_SIL, width=3)
            d.rectangle([hx - 7, hy - 13, hx + 7, hy - 6], fill=JZ_SIL)
            d.polygon([(hx - 10, hy + 8), (hx + 10, hy + 8), (sx + 13, sy - 35), (sx - 13, sy - 35)], fill=JZ_SIL)
            d.line([(sx - 6, sy - 35), (sx - 9, sy)], fill=JZ_SIL, width=6)
            d.line([(sx + 6, sy - 35), (sx + 10, sy)], fill=JZ_SIL, width=6)
            bell = (hx + 18 + int(mid * 4), hy + 34 - int(mid * 5))
            d.line([(hx + 4, hy + 4), (hx + 12, hy + 16), (hx + 10, hy + 36), bell], fill=pal["accent"], width=3)
            d.ellipse([bell[0] - 5, bell[1] - 5, bell[0] + 5, bell[1] + 3], fill=pal["accent"])
            d.line([(hx + 6, hy + 14), (hx + 12, hy + 24)], fill=JZ_SIL, width=4)         # Hände an den Klappen
        elif soloist == "singer":
            hx, hy = sx + int(sway * 0.7), sy - 96
            head = (hx, hy)
            d.line([(sx + 16, sy), (sx + 14, hy + 6)], fill=(160, 160, 170), width=2)    # Mikrofonständer
            d.ellipse([sx + 10, hy + 2, sx + 17, hy + 8], fill=(200, 200, 210))
            d.ellipse([hx - 7, hy - 8, hx + 7, hy + 8], fill=JZ_SIL)
            d.polygon([(hx - 7, hy + 9), (hx + 7, hy + 9), (sx + 14, sy), (sx - 14, sy)], fill=JZ_SIL)
            for k in range(6):                                                          # Pailletten im Licht
                if (int(t * 6) + k * 3) % 5 == 0:
                    px, py = hx - 6 + k * 3, hy + 20 + (k * 11) % 50
                    d.point((px, py), fill=pal["accent"])
            bell = (sx + 14, hy + 2)
        # 4. Bistrotisch vorne rechts: Cocktailglas, Aschenbecher, Zigarette
        tx, ty = JZ_TABLE_X, VIS_H - 6
        d.line([(tx, ty), (tx, ty - 42)], fill=(35, 25, 22), width=4)
        d.ellipse([tx - 34, ty - 47, tx + 34, ty - 37], fill=(48, 30, 22), outline=(95, 62, 42))
        gx, gy = tx - 14, ty - 43
        d.line([(gx, gy), (gx, gy - 11)], fill=(190, 220, 230))
        d.line([(gx - 5, gy), (gx + 5, gy)], fill=(190, 220, 230))
        slosh = math.sin(t * 10) * bass * 2
        d.polygon([(gx - 6, gy - 19 + slosh), (gx + 6, gy - 19 - slosh), (gx, gy - 12)], fill=pal["spot"])
        d.polygon([(gx - 9, gy - 22), (gx + 9, gy - 22), (gx, gy - 11)], outline=(200, 230, 240))
        ax, ay = tx + 13, ty - 42
        ice_gone = gname == "eis" and gl >= 0.6
        if o.get("gags", True) and not ice_gone:                                        # Eiswürfel hüpft im Takt
            iy = gy - 18 - 3 * st["ice"]
            d.rectangle([gx - 2, iy - 2, gx + 2, iy + 2], fill=(235, 248, 255))
        if gname == "eis" and 0.6 <= gl < 1.6:                                          # … und springt davon
            k = (gl - 0.6) / 1.0
            ix, iy = gx + (ax - gx) * k, gy - 18 - math.sin(k * math.pi) * 26
            d.rectangle([ix - 2, iy - 2, ix + 2, iy + 2], fill=(235, 248, 255))
        d.ellipse([ax - 8, ay - 3, ax + 8, ay + 2], fill=(90, 90, 100), outline=(140, 140, 150))
        cx1, cy1, cx2, cy2 = ax - 2, ay - 2, ax + 14, ay - 6
        d.line([(cx1, cy1), (cx2, cy2)], fill=(235, 235, 235), width=2)
        g_ = st["glow"]
        d.ellipse([cx2 - 2, cy2 - 2, cx2 + 2, cy2 + 2], fill=(255, int(70 + 110 * g_), int(10 + 40 * g_)))
        if gname == "eis" and 1.6 <= gl < 4.2:
            say.append((ax, ay - 30, "Zisch!"))
        # 5. Trinkgeldglas vorne links
        jx, jy = JZ_JAR_X, VIS_H - 8
        d.rectangle([jx - 11, jy - 22, jx + 11, jy], outline=(180, 210, 220))
        d.rectangle([jx - 10, jy - 6, jx + 10, jy - 1], fill=(200, 170, 60))
        tw = d.textlength("TIP", font=self.f_tiny)
        d.text((jx - tw / 2, jy - 19), "TIP", font=self.f_tiny, fill=(200, 210, 220))
        if gname == "trinkgeld":
            if gl < 1.2:                                                                # Hand von unten
                d.line([(jx + 30, VIS_H + 4), (jx + 8, jy - 34)], fill=(230, 190, 160), width=5)
            if 0.8 <= gl < 1.6:
                cy = jy - 34 + (gl - 0.8) / 0.8 * 28
                d.ellipse([jx - 3, cy - 3, jx + 3, cy + 3], fill=(255, 215, 80))
            if 1.6 <= gl < 2.6:
                d.text((jx + 12, jy - 30), "kling!", font=self.f_tiny, fill=(255, 230, 120))
            if 2.6 <= gl < 6.0:
                say.append((head[0], head[1] - 22, "Merci, Madame!"))

        # 6. Rauch, Klangfunken und Neonschild (halbtransparent)
        ov = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        smoke = o.get("smoke", "normal")
        if smoke != "off":
            strands = 1 if smoke == "light" else 2
            a = 55 if smoke == "light" else 85
            for k in range(strands):
                pts = [(cx2 + math.sin(t * 1.9 + f * 5.0 + k * 1.7) * (4 + f * 16) - f * 12, cy2 - 3 - f * 115)
                       for f in (j / 17.0 for j in range(18))]
                od.line(pts, fill=(215, 220, 230, a), width=2)
            if smoke == "normal":                                                       # Raumnebel
                for k in range(3):
                    hx_ = (t * (6 + k * 3) + k * 110) % (WIDTH + 160) - 80
                    od.ellipse([hx_ - 70, 40 + k * 30, hx_ + 70, 70 + k * 30], fill=(200, 200, 220, 14))
        if gname == "rauchring":
            for k in range(3):
                age = gl - k * 1.2
                if 0 <= age < 3.5:
                    rr = 4 + age * 5
                    ry = cy2 - 8 - age * 30
                    od.ellipse([cx2 - 10 - rr, ry - rr * 0.5, cx2 - 10 + rr, ry + rr * 0.5],
                               outline=(225, 230, 240, int(200 * (1 - age / 3.5))), width=2)
        if bell and playing and (mid > 0.25 or boom):                                   # goldene Klangfunken
            n = 9 if boom else 4
            for i in range(n):
                ph = (t * 1.8 + i / n) % 1.0
                nx = bell[0] + 6 + math.sin(t * 4 + i) * 8 + ph * 18
                ny = bell[1] - 6 - ph * 42
                a = int((1.0 - ph) * 210 * (1.0 if boom else min(1.0, mid * 1.4)))
                od.ellipse([nx - 2, ny - 2, nx + 2, ny + 2], fill=(*pal["accent"], a))
                if i % 3 == 0:
                    od.text((nx + 3, ny - 8), "♪", font=self.f_tiny, fill=(*pal["accent"], a))
        flicker = 0.25 if int(t * 7) % 53 in (0, 2) else 1.0                            # Neon flackert ab und zu
        na = int((150 + mid * 105) * flicker)
        od.rounded_rectangle([14, 22, 66, 42], radius=5, outline=(*pal["accent"], na), width=2)
        od.text((24, 25), "JAZZ", font=self.f_small_b, fill=(*pal["accent"], na))
        img = Image.alpha_composite(img, ov).convert("RGB")
        d = ImageDraw.Draw(img)
        if boom and 0.3 < bt < 3.2:
            d.text((128, 30), "SOLO!", font=self.f_big, fill=pal["accent"])
        if talk and (t - s.get("talk_t", t)) % 10.0 < 4.0:                              # Ansage, alle 10 s wieder
            say.append((head[0], head[1] - 22, "Danke! Der nächste Song ist für alle Nachteulen."))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)

        # 7. Tastaturbeleuchtung
        keys = o.get("keys", "mood")
        if keys == "brass":
            mix = min(1.0, mid * 0.8 + treble * 0.5)
            self.vis_col_jazz = tuple(int(pal["spot"][i] * (1 - mix) + pal["accent"][i] * mix) for i in range(3))
        else:
            k = 0.35 + 0.65 * min(1.0, bass * 1.15)
            self.vis_col_jazz = tuple(int(c * k) for c in pal["spot"])
        return img
