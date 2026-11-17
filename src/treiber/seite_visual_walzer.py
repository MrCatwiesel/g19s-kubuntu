"""Visualisierung „Walzer“, Teil 2: das Tanzpaar (waltz, Mixin WaltzVisual).

Ein Paar tanzt in geschlossener Tanzhaltung Walzer: Es dreht sich um die gemeinsame Achse (Wiener Walzer: halbe
Drehung je Takt, langsamer Walzer: Vierteldrehung), zieht dabei eine große Runde über die Fläche, hebt und senkt sich
im Dreivierteltakt (Heben und Senken, tief auf der Eins), alle zwölf Takte dreht sie sich unter seinem Arm. Das
Kleid schwingt in den Drehungen aus und schleift hinter der Bewegung her. Höhepunkt der Musik: schnelle Drehungen,
er hebt sie hoch, Glitzer. Wortbeitrag: Verbeugung und Knicks, dann plaudern beide. Die Figuren werden in einer
eigenen Ebene gezeichnet und mit dem Licht des Ortes eingefärbt (nachts dunkel und bläulich, im Saal warm).
Gags (abschaltbar): auf den Fuß getreten, schwindelig gedreht, Tanzen unterm Regenschirm (nur bei Regen draußen)
und je Ort einer: Kellner, Ritter, Kuh, Funkenregen, Huhn, Entenfamilie, Murmeltier, Möwe.
"""
import math
import random

WZ_SKIN = (242, 204, 176)
WZ_OUTFITS = {
    "ball": {"m": {"coat": (26, 26, 34), "trousers": (22, 22, 28), "shirt": (246, 246, 250), "tie": (18, 18, 22),
                   "tails": True, "hat": None, "hair": (52, 36, 26)},
             "w": {"dress": (156, 22, 52), "skirt": "gown", "hair": (96, 56, 28), "updo": True, "hat": None,
                   "sleeve": WZ_SKIN}},
    "tracht": {"m": {"coat": (240, 238, 230), "vest": (40, 92, 54), "trousers": (112, 74, 40), "socks": (240, 238, 228),
                     "short": True, "hat": "tracht", "hair": (90, 60, 34)},
               "w": {"dress": (40, 70, 140), "skirt": "calf", "apron": (236, 226, 206), "blouse": (250, 250, 248),
                     "hair": (214, 170, 90), "braids": True, "hat": None}},
    "summer": {"m": {"coat": (186, 212, 236), "trousers": (214, 198, 160), "hair": (70, 46, 30), "hat": None},
               "w": {"dress": (250, 170, 80), "skirt": "knee", "hair": (120, 70, 36), "loose": True, "hat": None}},
    "medieval": {"m": {"coat": (150, 30, 42), "trousers": (90, 64, 44), "belt": (60, 40, 24), "hair": (110, 70, 36),
                       "hat": None},
                 "w": {"dress": (40, 110, 72), "skirt": "gown", "hair": (170, 70, 36), "loose": True, "circlet": True,
                       "hat": None}},
    "country": {"m": {"coat": (176, 44, 44), "check": True, "trousers": (60, 82, 132), "hair": (90, 60, 34),
                      "hat": "straw"},
                "w": {"dress": (90, 130, 204), "check": True, "skirt": "knee", "hair": (200, 150, 80), "braids": True,
                      "hat": None}},
    "work": {"m": {"coat": (40, 74, 140), "trousers": (40, 74, 140), "hair": (60, 40, 30), "hat": "helmet_y"},
             "w": {"dress": (156, 22, 52), "skirt": "gown", "hair": (96, 56, 28), "updo": True, "hat": "helmet_y",
                   "sleeve": WZ_SKIN}},
}
WZ_PLACE_OUTFIT = {"ballroom": "ball", "castle": "medieval", "alm": "tracht", "steel": "work", "farm": "country",
                   "lake": "summer", "alps": "tracht", "beach": "summer"}
WZ_GAGS = {"fuss": 5.0, "schwindel": 6.0, "regenschirm": 9.0, "kellner": 7.0, "ritter": 8.0, "kuh": 8.0,
           "funken": 6.0, "huhn": 6.0, "ente": 8.0, "murmeltier": 6.0, "moewe": 7.0}
WZ_PLACE_GAG = {"ballroom": "kellner", "castle": "ritter", "alm": "kuh", "steel": "funken", "farm": "huhn",
                "lake": "ente", "alps": "murmeltier", "beach": "moewe"}
WZ_GAG_FIRST, WZ_GAG_PAUSE = 10.0, (14.0, 24.0)
WZ_BOOM = 4.0
WZ_SCALE = 1.15                         # Größe des Paares (1,0 ≈ 80 Pixel)
WZ_SS = 2                               # das Paar wird in doppelter Auflösung gezeichnet (weiche Bewegung, glatte Kanten)
WZ_SS_BOX = (230, 176)                  # Ausschnitt um das Paar (Bildpunkte), Fußpunkt WZ_SS_FOOT über dem unteren Rand
WZ_SS_FOOT = 14
WZ_TEMPO_SMOOTH = 2.5                   # Sekunden: so träge folgt das Tanztempo dem gemessenen Schlagabstand
WZ_BAR_CONF = 0.25                      # ab dieser Sicherheit gilt die Takterkennung (Länge und Eins)
WZ_LEAD = 0.1                           # s: das Paar läuft der Musik so weit voraus (Verzögerung Aufnahme → Display)
WZ_PHASE_TIME = 0.8                     # s: so weich folgt die Phase dem Raster der Musik
WZ_PHASE_PULL = 0.5                     # Anteil der Abweichung, den ein erkannter Schlag (über 0,4 s) ausgleicht
WZ_SWITCH = 300.0                       # „Abwechselnd“ ohne Titelwechsel: spätestens so oft ein neuer Ort
WZ_TURN_EVERY = 12                      # Takte bis zur Drehung unter dem Arm
WZ_TALK = [("m", "Darf ich gleich wieder bitten?"), ("w", "Aber gern – nach der Durchsage."),
           ("w", "Sie führen wunderbar."), ("m", "Ich zähle heimlich mit: eins, zwei, drei …"),
           ("m", "Was für ein Abend!"), ("w", "Meine Füße sagen dasselbe.")]
WZ_SKY_OF_WEATHER = {"sun": "clear", "partly": "partly", "cloud": "cloudy", "fog": "fog", "drizzle": "rain",
                     "rain": "rain", "snow": "snow", "thunder": "thunder"}
WZ_FX_OF_SKY = {"rain": "rain", "thunder": "thunder", "snow": "snow"}          # Nebel malt _wz_backdrop


def _wz_shade(col, k):
    return tuple(max(0, min(255, int(c * k))) for c in col)


class WaltzVisual:
    vis_col_waltz = None

    # -- Personen ------------------------------------------------------------- #
    def _wz_person(self, img, d, who, x, foot, s, face, outfit, pose):
        """Tänzer (who = "m") bzw. Tänzerin ("w"); face = Blickrichtung (x, Tiefe) als Einheitsvektor, Tiefe > 0 =
        vom Betrachter weg. pose: bob, lift, step, lh/rh (Handziele, Bildpunkte), flare, swing, bow, wobble.
        Gibt Kopf und Hände zurück."""
        fx, fz = face
        fr = -fz                                                    # 1 = Gesicht zum Betrachter, −1 = Rücken
        rx = fz                                                     # Bildrichtung seiner rechten Seite (x-Anteil)
        far_right = -fx > 0                                         # rechte Seite liegt hinten
        man = who == "m"
        o = outfit
        lift = pose.get("lift", 0.0)
        y0 = foot - lift
        bow = pose.get("bow", 0.0)
        wob = pose.get("wobble", 0.0)
        hip = (x + wob * 0.4, y0 - (41 if man else 37) * s + pose.get("bob", 0.0))
        lean = fx * bow * 7 * s + wob
        sh_y = hip[1] - (28 if man else 25) * s + bow * 5 * s
        sh_x = x + lean * 0.6
        head = (x + lean, sh_y - 9 * s + bow * 3 * s)
        aw = abs(fr)
        self._blob(img, x, foot + 1, 30 * s, 6 * s, (8, 8, 12), alpha=0.5, flat=True)          # Schatten
        skirt = None if man else o.get("skirt")
        step = pose.get("step", 0.0)
        legs = o.get("trousers", (40, 40, 48)) if man else WZ_SKIN
        # Beine (bei langem Kleid verdeckt; Füße schauen heraus)
        sides = (1, -1) if far_right else (-1, 1)
        for side in sides:
            hj = (hip[0] + side * rx * 4 * s, hip[1] + 2 * s)
            fpos = (hj[0] + fx * side * step * 5 * s, y0)
            knee, ft = _ik(hj, fpos, 18 * s, 19 * s, 1 if fx >= 0 else -1)
            if skirt != "gown":
                if man and o.get("short"):                                         # Lederhose und Kniestrümpfe
                    self._limb(img, hj, knee, 7 * s, legs)
                    self._limb(img, knee, ft, 5.5 * s, o.get("socks", WZ_SKIN))
                else:
                    self._limb(img, hj, knee, (7 if man else 5) * s, legs)
                    self._limb(img, knee, ft, (6 if man else 4.5) * s, legs)
            shoe = (20, 20, 24) if man else _wz_shade(o["dress"], 0.6)
            self._blob(img, ft[0] + fx * 3 * s, ft[1], 9 * s, 4.5 * s, shoe, gloss=0.8)
        if man and o.get("tails") and fr > -0.2:                                   # Frackschöße hinten
            self._wz_tails(img, d, hip, s, fx, rx, pose, o)
        if skirt:
            self._wz_skirt(img, d, hip, y0, s, fx, fr, pose, o)
        # Arme: hinterer zuerst, dann Körper, dann vorderer
        sh = {side: (sh_x + side * rx * (9 if man else 7.5) * s, sh_y + 2 * s) for side in (-1, 1)}
        targets = {-1: pose.get("lh"), 1: pose.get("rh")}
        sleeve = o["coat"] if man else o.get("blouse", o.get("sleeve", o["dress"]))
        hands = {}

        def arm(side):
            p = sh[side]
            tgt = targets[side] or (p[0] + side * rx * 3 * s + fx * 2 * s, p[1] + 24 * s)
            el, hd = _ik(p, tgt, 13 * s, 13 * s, 1 if side * rx >= 0 else -1)
            self._limb(img, p, el, (5.5 if man else 4.5) * s, sleeve)
            self._limb(img, el, hd, (5 if man else 4) * s, sleeve if man else WZ_SKIN)
            self._blob(img, hd[0], hd[1], 5 * s, 5 * s, WZ_SKIN, gloss=0.2)
            hands[side] = hd
        far, near = (1, -1) if far_right else (-1, 1)
        arm(far)
        body_c = ((hip[0] + sh_x) / 2, (hip[1] + sh_y) / 2 + 1 * s)
        self._blob(img, head[0], sh_y - 1 * s, 5 * s, 7 * s, WZ_SKIN, gloss=0.2)                # Hals
        if man:
            self._blob(img, body_c[0], body_c[1], (12 + 7 * aw) * s, 33 * s, o["coat"], gloss=0.35, ang=lean)
            self._blob(img, sh_x, sh_y + 3 * s, (11 + 8 * aw) * s, 8 * s, o["coat"], gloss=0.3)   # Schultern
            if o.get("check"):                                                      # kariertes Hemd
                for k in range(-2, 3):
                    d.line([(body_c[0] + k * 3 * s * aw, body_c[1] - 12 * s), (body_c[0] + k * 3 * s * aw, body_c[1] + 12 * s)],
                           fill=_wz_shade(o["coat"], 0.7))
            if o.get("vest") and fr > -0.2:
                self._blob(img, body_c[0] + fx * 2 * s, body_c[1] - 1 * s, (8 + 6 * aw) * s, 24 * s, o["vest"], gloss=0.3)
            if o.get("belt"):
                d.line([(body_c[0] - (6 + 3 * aw) * s, hip[1] - 2 * s), (body_c[0] + (6 + 3 * aw) * s, hip[1] - 2 * s)],
                       fill=o["belt"], width=max(1, int(2 * s)))
            if o.get("tails") and fr > 0.15:                                       # Hemdbrust und Fliege
                self._blob(img, body_c[0] + fx * 3 * s, sh_y + 8 * s, 6 * s * fr + 1, 14 * s, o["shirt"], gloss=0.2)
                if not pose.get("no_tie"):
                    d.polygon([(head[0] - 4 * s, sh_y + 1), (head[0] + 4 * s, sh_y + 3 * s), (head[0] + 4 * s, sh_y + 1),
                               (head[0] - 4 * s, sh_y + 3 * s)], fill=o["tie"])
        else:
            self._blob(img, hip[0] + lean * 0.2, hip[1] - 9 * s, (7 + 3 * aw) * s, 12 * s, o["dress"], gloss=0.4)
            self._blob(img, sh_x, sh_y + 3 * s, (9 + 6 * aw) * s, 6 * s, sleeve, gloss=0.3)        # Schultern
            self._blob(img, sh_x, sh_y + 7 * s, (10 + 5 * aw) * s, 15 * s, o["dress"], gloss=0.45)   # Mieder
            if o.get("blouse") and fr > 0.1:
                self._blob(img, body_c[0], sh_y + 3 * s, (8 + 4 * aw) * s, 6 * s, o["blouse"], gloss=0.2)
            elif fr > 0.3:
                self._blob(img, head[0], sh_y + 2 * s, 7 * s * aw, 5 * s, WZ_SKIN, gloss=0.2)
        if man and o.get("tails") and fr <= -0.2:                                  # von hinten: Schöße vorn
            self._wz_tails(img, d, hip, s, fx, rx, pose, o)
        arm(near)
        self._wz_head(img, d, who, head, s, fx, fr, o, pose)
        return head, (hands[-1], hands[1])

    def _wz_tails(self, img, d, hip, s, fx, rx, pose, o):
        sw = pose.get("swing", 0.0) * 0.6 - fx * (3 + 7 * pose.get("flare", 0.0)) * s
        for side in (-1, 1):
            x0 = hip[0] + side * rx * 4 * s
            d.polygon([(x0 - 2.5 * s, hip[1] - 3 * s), (x0 + 2.5 * s, hip[1] - 3 * s),
                       (x0 + sw + 1.5 * s, hip[1] + 22 * s), (x0 + sw - 2 * s, hip[1] + 20 * s)], fill=o["coat"])

    def _wz_skirt(self, img, d, hip, y0, s, fx, fr, pose, o):
        kind = o["skirt"]
        hem_y = y0 - {"gown": 1, "calf": 11, "knee": 19}[kind] * s
        waist_y = hip[1] - 5 * s
        flare = pose.get("flare", 0.0)
        hw = {"gown": 19, "calf": 15, "knee": 13}[kind] * s * (1 + 0.6 * flare)
        sw = pose.get("swing", 0.0)
        top = 7 * s
        cx = hip[0]
        n = 9
        hem = []
        for k in range(n):
            u = k / (n - 1)
            hx = cx - hw + 2 * hw * u + sw
            wave = math.sin(u * math.pi * 4 + pose.get("phase", 0.0)) * (1.2 + 2.5 * flare) * s
            hem.append((hx, hem_y + wave))
        mid_y = waist_y + (hem_y - waist_y) * 0.5
        left, right = [], []
        for k in range(1, 5):                                                       # Glockenform
            u = k / 5
            yy = waist_y + (hem_y - waist_y) * u
            wd = top + (hw - top) * u ** 0.55
            left.append((cx - wd + sw * u * u, yy))
            right.append((cx + wd + sw * u * u, yy))
        left = [(cx - top, waist_y)] + left
        right = right[::-1] + [(cx + top, waist_y)]
        col = o["dress"]
        d.polygon(left + hem + right, fill=col)
        mid = [(cx + sw * (k / 5) ** 2 + (hw - top) * 0.15 * k / 5, waist_y + (hem_y - waist_y) * k / 5) for k in range(5)]
        d.polygon(mid + hem[n // 2 + 1:] + right, fill=_wz_shade(col, 0.74))      # Licht von links
        d.polygon([(cx - top + 1, waist_y + 1), (cx - top - (hw - top) * 0.3 + sw * 0.3, mid_y), (cx - 2, mid_y)],
                  fill=_wz_shade(col, 1.18))
        d.line(hem, fill=_wz_shade(col, 1.35), width=max(1, int(1.5 * s)))
        if o.get("check"):
            for k in range(1, 4):
                yy = waist_y + (hem_y - waist_y) * k / 4
                d.line([(cx - top - (hw - top) * k / 4 + sw * k / 4, yy), (cx + top + (hw - top) * k / 4 + sw * k / 4, yy)],
                       fill=(240, 240, 250))
        if o.get("apron") and fr > 0.1:
            aw = hw * 0.45 * fr
            d.polygon([(cx - 5 * s * fr, waist_y + 1), (cx + 5 * s * fr, waist_y + 1), (cx + aw + sw * 0.8, hem_y - 3 * s),
                       (cx - aw + sw * 0.8, hem_y - 3 * s)], fill=o["apron"])

    def _wz_head(self, img, d, who, head, s, fx, fr, o, pose):
        hx, hy = head
        hair = o["hair"]
        back = _smooth((0.35 - fr) / 0.9)                                          # 0 = Gesicht … 1 = Hinterkopf
        loose = who == "w" and o.get("loose")
        if loose and back < 0.5:                                                    # offenes Haar hinter dem Kopf
            self._blob(img, hx - fx * 2 * s, hy + 6 * s, 17 * s, 24 * s, hair, gloss=0.3)
        if who == "w" and o.get("updo") and fr > 0:                                # Dutt hinter dem Kopf
            self._blob(img, hx - fx * 6 * s, hy - 7 * s, 9 * s, 8 * s, hair, gloss=0.5)
        self._blob(img, hx, hy, 14 * s, 16 * s, WZ_SKIN, gloss=0.3)
        if abs(fx) > 0.5 and back < 0.5:                                            # Nase im Profil
            self._blob(img, hx + fx * 7 * s, hy + 1 * s, 3 * s, 3 * s, WZ_SKIN, gloss=0.2)
        if back < 0.6 and fr > 0.1:                                                 # Augen, Mund
            er = 0.9 * s
            for side in (-1, 1):
                ex = hx + fx * 2.5 * s + side * 3 * s * fr
                d.ellipse([ex - er, hy - er, ex + er, hy + er], fill=(40, 30, 30))
            if fr > 0.45:
                d.arc([hx - 2.5 * s + fx * 2 * s, hy + 2 * s, hx + 2.5 * s + fx * 2 * s, hy + 5 * s], 20, 160,
                      fill=(170, 70, 70), width=max(1, int(s * 0.8)))
        cap_y = hy - (5 if who == "m" else 4) * s * (1 - back)                     # Haar wächst über den Kopf
        self._blob(img, hx - fx * 2 * s * (1 - back), cap_y, 15 * s, (9 + 8 * back) * s, hair, gloss=0.45 - 0.05 * back)
        if loose and back >= 0.5:
            self._blob(img, hx, hy + 9 * s, 16 * s, 22 * s, hair, gloss=0.35)
        if who == "w" and o.get("updo") and fr <= 0:
            self._blob(img, hx - fx * 6 * s, hy - 7 * s, 9 * s, 8 * s, hair, gloss=0.5)
        if who == "w" and o.get("braids"):
            for side in (-1, 1):
                bx = hx + side * 5 * s - fx * 2 * s
                self._limb(img, (bx, hy), (bx + side * 1 * s, hy + 18 * s), 3.5 * s, hair, gloss=0.4)
        if who == "w" and o.get("circlet") and fr > -0.25:
            d.line([(hx - 7 * s, hy - 5 * s), (hx + 7 * s, hy - 5 * s)], fill=(240, 200, 70), width=max(1, int(1.5 * s)))
        hat = o.get("hat")
        top = hy - 7 * s
        if hat == "tracht":
            self._fig_hat(img, d, (hx, hy + 1 * s), s, "tracht", (60, 82, 52), 0)
        elif hat == "straw":
            d.ellipse([hx - 12 * s, top, hx + 12 * s, top + 4 * s], fill=(226, 196, 110))
            d.chord([hx - 6 * s, top - 7 * s, hx + 6 * s, top + 4 * s], 180, 360, fill=(214, 182, 96))
            d.line([(hx - 6 * s, top), (hx + 6 * s, top)], fill=(170, 40, 40), width=max(1, int(1.5 * s)))
        elif hat == "helmet_y":
            d.chord([hx - 9 * s, top - 6 * s, hx + 9 * s, top + 7 * s], 180, 360, fill=(250, 204, 30))
            d.line([(hx - 11 * s, top + 1 * s), (hx + 11 * s, top + 1 * s)], fill=(230, 180, 20), width=max(1, int(2 * s)))

    # -- Tanzpaar ------------------------------------------------------------- #
    def _wz_couple(self, f, fd, st, cx, foot, s, outfits, pose_m, pose_w, phi, spin, sep):
        """Beide in Tanzhaltung um die Achse phi; spin = Eigendrehung der Tänzerin (Drehung unter dem Arm)."""
        r = (7.5 + sep) * s
        c, sn = math.cos(phi), math.sin(phi)
        mx, mz = cx + r * c, r * sn
        wx, wz = cx - r * c, -r * sn
        face_m = (-c, -sn)
        a = phi + spin
        face_w = (math.cos(a), math.sin(a))
        sh_m = foot - 69 * s
        joint_up = spin != 0.0 or sep > 4
        jx = cx + sn * 17 * s * (0.6 if joint_up else 1.0)
        jy = sh_m - (24 * s if joint_up else 2 * s)
        if pose_m.get("lh") is None:
            pose_m["lh"] = (jx, jy)
        if pose_w.get("rh") is None:
            pose_w["rh"] = (jx, jy)
        if not joint_up:
            pose_m.setdefault("rh", (wx - face_w[0] * 4 * s, foot - 58 * s))     # Hand auf ihrem Rücken
            pose_w.setdefault("lh", (mx - sn * 9 * s, sh_m + 3 * s))                # Hand auf seiner Schulter
        foot_m, foot_w = foot - mz * 0.5, foot - wz * 0.5
        order = sorted((("m", mx, foot_m, mz, face_m, pose_m), ("w", wx, foot_w, wz, face_w, pose_w)),
                       key=lambda e: -e[3])                                         # hinten zuerst
        heads = {}
        for who, x, ft, z, face, pose in order:
            hd, hands = self._wz_person(f, fd, who, x, ft, s * (1 - z * 0.004), face, outfits[who], pose)
            heads[who] = (hd, hands)
        return heads

    # -- Feinzeichnung: Paar in WZ_SS-facher Auflösung, dann gemittelt (Bewegung in Bruchteilen von Pixeln) -- #
    @staticmethod
    def _wz_ss_begin(cx, foot):
        bw, bh = WZ_SS_BOX
        x0 = int(round(cx)) - bw // 2
        y0 = int(round(foot)) + WZ_SS_FOOT - bh
        img = Image.new("RGBA", (bw * WZ_SS, bh * WZ_SS), (0, 0, 0, 0))
        return {"img": img, "draw": ImageDraw.Draw(img), "x0": x0, "y0": y0,
                "to": lambda p: ((p[0] - x0) * WZ_SS, (p[1] - y0) * WZ_SS),
                "back": lambda p: (p[0] / WZ_SS + x0, p[1] / WZ_SS + y0)}

    @staticmethod
    def _wz_ss_pose(pose, to):
        """Pose in die Feinzeichnung umrechnen: Abstände (Pixel) vervielfachen, Handziele verschieben."""
        q = dict(pose)
        for k in ("bob", "lift", "wobble", "swing"):
            if k in q:
                q[k] *= WZ_SS
        for k in ("lh", "rh"):
            if q.get(k) is not None:
                q[k] = to(q[k])
        return q

    @staticmethod
    def _wz_ss_end(f, ss):
        """Feinzeichnung verkleinern (Farben nach Deckkraft gewichtet) und in die Figurenebene setzen."""
        k = WZ_SS
        bb = ss["img"].getbbox()                                                    # nur der bemalte Teil
        if not bb:
            return
        l, t = bb[0] // k * k, bb[1] // k * k
        r, b = -(-bb[2] // k) * k, -(-bb[3] // k) * k
        a = np.asarray(ss["img"].crop((l, t, r, b)), np.float32)
        pm = np.empty_like(a)
        pm[..., 3] = a[..., 3]
        pm[..., :3] = a[..., :3] * a[..., 3:4]                                     # Farben nach Deckkraft gewichtet
        acc = pm[0::k, 0::k].copy()
        for dy in range(k):
            for dx in range(k):
                if dx or dy:
                    acc += pm[dy::k, dx::k]
        asum = acc[..., 3:4]
        out = np.empty_like(acc)
        out[..., :3] = acc[..., :3] / np.maximum(asum, 1e-3)
        out[..., 3] = asum[..., 0] / (k * k)
        f.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA"), (ss["x0"] + l // k, ss["y0"] + t // k))

    def _wz_outfits(self, o, place):
        key = o.get("clothes", "place")
        key = WZ_PLACE_OUTFIT.get(place, "ball") if key == "place" else key
        base = WZ_OUTFITS.get(key, WZ_OUTFITS["ball"])
        w = dict(base["w"])
        if o.get("dress"):
            w["dress"] = tuple(o["dress"])
        return {"m": dict(base["m"]), "w": w}

    # -- Ort, Licht und Wetter ------------------------------------------------ #
    def _wz_place(self, st, o, t):
        if st.get("force_place"):
            return st["force_place"]
        place = o.get("place", "ballroom")
        if place in WALTZ_PLACES:
            return place
        song = self.__dict__.get("_vis_song") or ""
        if st.get("place") is None or (song and song != st.get("song")) or t - st.get("place_t", t) > WZ_SWITCH:
            order = list(WALTZ_PLACES)
            cur = st.get("place")
            st["place"] = order[(order.index(cur) + 1) % len(order)] if cur in order else order[0]
            st["song"], st["place_t"] = song, t
        return st["place"]

    def _wz_weather(self, st, o):
        if st.get("force_sky"):
            return st["force_sky"], 10
        mode = o.get("weather", "real")
        if mode != "real":
            return mode, 12
        kind, _, wind = self._party_weather()
        return WZ_SKY_OF_WEATHER.get(kind, "clear"), wind or 0

    # -- Hauptfunktion -------------------------------------------------------- #
    @vis_style("waltz")
    def vis_waltz(self, s, o, color):
        t = s["t"]
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("waltz", lambda: {"beats": s["beats"], "k": 0, "bar": 0, "phi": 0.0, "theta": math.pi / 2,
                                             "energy": 0.0, "turn": None, "boom": -99.0, "gag": None, "order": [],
                                             "next_gag": t + WZ_GAG_FIRST, "rng": random.Random(191), "start": t,
                                             "slow": 0.0, "fast": 0.0, "place": None, "song": None,
                                             "wx": None, "swing": 0.0, "sparks": [], "bass": 0.0,
                                             "per": 0.5, "ph": 0.0, "vienna": False})
        dt = self._vis_dt(st, t)
        place = self._wz_place(st, o, t)
        sky, wind = self._wz_weather(st, o)
        alt, side = self._wz_sun(o)
        photo = self._wz_photo(place) if o.get("photo", True) else None
        bg, amb, glow = self._wz_backdrop(place, alt, side, sky, photo, time.time())
        img = bg.copy()
        L = self._wz_place_layers(place)
        indoor = L["indoor"] and photo is None
        level = s["level"] if s["level"] == s["level"] else 0.0
        bass = s.get("bass", 0.0)
        bass = bass if bass == bass else 0.0
        st["bass"] += (bass - st["bass"]) * min(1.0, dt / 0.25)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        playing = bool(s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        st["slow"] += (level - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (level - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < WZ_BOOM
        # Gags
        gag = st["gag"]
        if gag and t - gag[1] >= WZ_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*WZ_GAG_PAUSE)
            st.pop("force_place", None)
            st.pop("force_sky", None)
        raining = sky in ("rain", "thunder") and not indoor
        if gname_ := (gag[0] if gag else None):
            if gname_ == "regenschirm" and not raining:                          # drinnen bzw. trocken: kein Schirm
                st["gag"] = gag = None
        pool = ["fuss", "schwindel", WZ_PLACE_GAG[place]] + (["regenschirm"] if raining else [])
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not any(g_ in pool for g_ in st["order"]):
                st["order"] = st["rng"].sample(pool, len(pool))
            while st["order"] and gag is None:
                name = st["order"].pop(0)
                if name in pool:
                    st["gag"] = gag = (name, t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        # Tanz: Takt, Drehung, Runde
        if playing and new_beat:
            st["k"] += 1
            if st["k"] % 3 == 0:
                st["bar"] += 1
                if st["bar"] % WZ_TURN_EVERY == 0 and st["turn"] is None and not boom:
                    st["turn"] = t
        stop = gname in ("fuss", "schwindel") or (gname == "ritter" and 2.5 <= gl < 6.3)
        target = 1.0 if playing and not stop else 0.0
        st["energy"] += (target - st["energy"]) * min(1.0, dt / 0.7)
        en = st["energy"]
        # Tempo und Takt: bevorzugt aus der Takterkennung der Klanganalyse (Taktlänge und Lage der Eins), sonst aus
        # den Bassschlägen. Die Phase läuft gleichmäßig weiter und wird nur weich zum Raster der Musik nachgezogen.
        bar, conf = s.get("bar"), s.get("bar_conf") or 0.0
        grid = bool(bar) and conf >= WZ_BAR_CONF and bar == bar
        tgt_per = bar / 3.0 if grid else period
        if abs(tgt_per - st["per"]) > st["per"] * 0.25:                             # neues Stück: gleich umstellen
            st["per"] = tgt_per
        st["per"] += (tgt_per - st["per"]) * min(1.0, dt / WZ_TEMPO_SMOOTH)
        per = st["per"]
        if playing:
            st["ph"] = (st["ph"] + dt / per) % 3.0
            if grid:                                                                # Eins der Musik = Phase 0
                want = ((t + WZ_LEAD - s.get("down_t", t)) / per) % 3.0
                err = (want - st["ph"] + 1.5) % 3.0 - 1.5
                st["ph"] = (st["ph"] + err * min(1.0, dt / WZ_PHASE_TIME)) % 3.0
            else:
                if new_beat:                                                        # Abweichung merken …
                    st["drift"] = (round(st["ph"]) - st["ph"]) * WZ_PHASE_PULL
                corr = st.get("drift", 0.0) * min(1.0, dt / 0.4)                   # … und weich ausgleichen
                st["drift"] = st.get("drift", 0.0) - corr
                st["ph"] = (st["ph"] + corr) % 3.0
        st["grid"] = grid
        mode = o.get("tempo", "auto")
        if per < 0.47:                          # Wiener ≈ 0,33 s je Schlag, langsamer ≈ 0,67 s; Puffer gegen Pendeln
            st["vienna"] = True
        elif per > 0.53:
            st["vienna"] = False
        vienna = mode == "vienna" or (mode == "auto" and st["vienna"])
        target_ang = (math.pi if vienna else math.pi / 2) / (3 * per) * (1.9 if boom else 1.0)
        target_ang = max(0.6, min(6.5, target_ang))
        st["ang"] = st.get("ang", target_ang) + (target_ang - st.get("ang", target_ang)) * min(1.0, dt / 0.6)
        ang = st["ang"]
        st["phi"] = (st["phi"] - ang * en * dt) % (2 * math.pi)
        st["theta"] = (st["theta"] + (2 * math.pi / (36 if vienna else 52)) * en * dt) % (2 * math.pi)
        barph = st["ph"] / 3.0
        bob = 3.0 * math.cos(2 * math.pi * barph) * en
        spin = 0.0
        if st["turn"] is not None:
            tl = (t - st["turn"]) / (3 * per * (1 if vienna else 1.5))
            if tl >= 1 or not playing:
                st["turn"] = None
            else:
                spin = -2 * math.pi * _smooth(tl)
        # Lage auf der Fläche
        if talk:
            cx = max(70.0, min(WIDTH - 70.0, WIDTH / 2 + 96 * math.cos(st["theta"])))
            z = 0.0
        else:
            cx = WIDTH / 2 + 96 * math.cos(st["theta"])
            z = 12 * math.sin(st["theta"])
        foot = WZ_FLOOR - z * 0.9
        sc = WZ_SCALE * (1.0 - z * 0.008)
        outfits = self._wz_outfits(o, place)
        say = []
        # Figuren in eigener Ebene (wird mit dem Licht des Ortes eingefärbt)
        f = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        fd = ImageDraw.Draw(f)
        ss = self._wz_ss_begin(cx, foot)                                            # Paar in doppelter Auflösung
        big, bd, X = ss["img"], ss["draw"], ss["to"]
        K = WZ_SS
        if talk:
            tl = t - s.get("talk_t", t)
            bowk = math.sin(math.pi * min(1.0, tl / 2.2)) if tl < 2.2 else 0.0
            pm = {"bow": bowk, "bob": 0.0}
            pw = {"bob": bowk * 6 * sc, "lh": (cx + 8 * sc, WZ_FLOOR - 42 * sc), "rh": (cx + 24 * sc, WZ_FLOOR - 42 * sc)}
            hm, _ = self._wz_person(big, bd, "m", *X((cx - 15 * sc, foot)), sc * K, (0.45, -0.89), outfits["m"],
                                    self._wz_ss_pose(pm, X))
            hw, _ = self._wz_person(big, bd, "w", *X((cx + 15 * sc, foot)), sc * K, (-0.45, -0.89), outfits["w"],
                                    self._wz_ss_pose(pw, X))
            hm, hw = ss["back"](hm), ss["back"](hw)
            self._wz_ss_end(f, ss)
            if tl >= 2.4:
                i = int((tl - 2.4) / 3.2) % len(WZ_TALK)
                who, text = WZ_TALK[i]
                h = hm if who == "m" else hw
                say.append((h[0], h[1] - 24, text))
        else:
            wob_m = wob_w = 0.0
            sep = 0.0
            lift_w = 0.0
            if spin:
                sep = 6.0 * math.sin(-spin / 2)
            if gname == "schwindel" and gl > 0.5:
                wob_m, wob_w = math.sin(gl * 3.1) * 6, math.sin(gl * 3.1 + 1.2) * 6
                sep = 5.0
            if boom and 1.0 < bt < 2.8:
                lift_w = 22 * math.sin(math.pi * (bt - 1.0) / 1.8)
            # Schwung des Kleides: hinter der Bewegung her
            wxp = cx - 7.5 * sc * math.cos(st["phi"])
            if st["wx"] is not None and dt > 0:
                v = (wxp - st["wx"]) / dt
                st["swing"] += (max(-11.0, min(11.0, -v * 0.09)) - st["swing"]) * min(1.0, dt / 0.25)
            st["wx"] = wxp
            flare = min(1.0, ang * en / 4.0) * 0.8 + (0.6 if spin else 0.0) + (0.3 if boom else 0.0)
            stepk = math.sin(2 * math.pi * barph * 1.5) * en
            pm = {"bob": bob, "step": stepk, "wobble": wob_m, "flare": flare}
            pw = {"bob": bob, "step": -stepk, "wobble": wob_w, "flare": min(1.2, flare), "swing": st["swing"] * sc,
                  "lift": lift_w, "phase": st["phi"] * 3}
            if gname == "fuss" and 0.3 < gl < 3.4:                                  # sie hüpft auf einem Bein
                pw["lift"] = abs(math.sin(gl * 7)) * 6
                pw["step"] = 2.4
            if gname == "moewe" and gl > 2.6:
                pm["no_tie"] = True
            if gname == "funken" and 1.5 < gl < 3.4:
                pm["lift"] = abs(math.sin(gl * 9)) * 7
            if gname == "regenschirm":
                pm["rh"] = (cx + 2 * sc, WZ_FLOOR - 100 * sc)
            bx, by = X((cx, foot))
            heads = self._wz_couple(big, bd, st, bx, by, sc * K, outfits, self._wz_ss_pose(pm, X),
                                    self._wz_ss_pose(pw, X), st["phi"], spin, sep)
            hm, hw = ss["back"](heads["m"][0]), ss["back"](heads["w"][0])
            if gname == "regenschirm":
                self._wz_umbrella(big, bd, *X((cx, WZ_FLOOR - 108 * sc)), sc * K)
            self._wz_ss_end(f, ss)
            if gname == "regenschirm" and 1.0 < gl < 4.5:
                say.append((cx, hm[1] - 46, "Wir tanzen im Regen!"))
            if gname == "fuss":
                if 0.3 < gl < 2.2:
                    say.append((hw[0], hw[1] - 24, "Autsch!"))
                elif 2.2 <= gl < 4.4:
                    say.append((hm[0], hm[1] - 24, "Pardon, Madame!"))
            if gname == "schwindel":
                for who, h in (("m", hm), ("w", hw)):
                    for k in range(3):
                        a = gl * 4 + k * 2.1
                        sx, sy = h[0] + math.cos(a) * 10, h[1] - 14 + math.sin(a) * 3
                        fd.text((sx - 3, sy - 6), "*", font=self.f_small_b, fill=(255, 230, 90))
                if 0.8 < gl < 3.0:
                    say.append((hw[0], hw[1] - 30, "Mir ist schwindlig …"))
                elif 3.0 <= gl < 5.2:
                    say.append((hm[0], hm[1] - 30, "Die Wände tanzen mit!"))
            if boom:
                self._wz_glitter(st, cx, foot, sc, bt, dt)
                if 1.2 < bt < 3.0:
                    say.append((hw[0], hw[1] - 30, "Hui!"))
        self._wz_draw_sparks(st, fd, dt)
        if gname in ("kellner", "ritter", "kuh", "funken", "huhn", "ente", "murmeltier", "moewe"):
            getattr(self, "_wz_gag_" + gname)(f, fd, t, gl, cx, foot, sc, say, st, L)
        # Licht: Figuren einfärben, Flammen und Glühwürmchen leuchten selbst
        tint = np.array(amb, np.float32)
        if indoor:
            tint = np.array(_wz_lerp((0.86, 0.74, 0.6), (1.0, 0.97, 0.93), _smooth((alt + 5) / 15)), np.float32)
        else:
            gc = np.array(WZ_GLOW_COLS[place], np.float32) / 255
            tint = np.clip(tint * 0.85 + gc * glow * 0.32 + 0.05, 0, 1.1)
        if np.any(np.abs(tint - 1) > 0.02):
            arr = np.asarray(f).astype(np.float32)
            arr[..., :3] *= tint[None, None, :]
            f = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        d = ImageDraw.Draw(img)
        if photo is None:
            self._wz_flames(img, d, L, t, glow)
            if L.get("fireflies") and glow > 0.5 and sky not in ("rain", "thunder", "snow"):
                rng = random.Random(5)
                for k in range(14):
                    x = (rng.uniform(0, WIDTH) + math.sin(t * 0.4 + k) * 20) % WIDTH
                    y = rng.uniform(110, VIS_H - 10) + math.cos(t * 0.6 + k * 1.7) * 6
                    if math.sin(t * 2 + k * 2.3) > 0.2:
                        self._blob(img, x, y, 5, 5, (220, 255, 120), alpha=0.8, flat=True)
                        d.point((x, y), fill=(250, 255, 200))
            if L.get("shore"):                                                      # Brandung am Strand
                y = L["shore"] - 1
                pts = [(x, y + 2 * math.sin(x * 0.07 + t * 1.6)) for x in range(0, WIDTH + 8, 8)]
                foam = _wz_shade((240, 244, 250), max(0.3, sum(amb) / 3))
                d.line(pts, fill=foam, width=2)
        img.paste(f, (0, 0), f)
        fxk = WZ_FX_OF_SKY.get(sky)
        if fxk:                                                                     # Regen, Schnee, Nebel, Blitze
            if indoor:
                win = L.get("_win_img")
                if win is None:
                    win = L["_win_img"] = Image.fromarray((L["windows"] * 255).astype(np.uint8), "L")
                outside = self._vis_weather_fx(img.copy(), t, fxk, wind, dim=False)
                img.paste(outside, (0, 0), win)
            else:
                img = self._vis_weather_fx(img, t, fxk, wind, dim=False)
        d = ImageDraw.Draw(img)
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        # Tastatur: Licht des Ortes, pulsiert mit dem Bass
        if glow > 0.45 or indoor:
            base = WZ_GLOW_COLS[place]
        elif sky in ("clear", "partly"):
            base = (110, 170, 255)
        else:
            base = (170, 176, 190)
        k = 0.5 + 0.5 * st["bass"] if playing else 0.4
        self.vis_col_waltz = tuple(int(c * k) // 8 * 8 for c in base)
        return img

    # -- Effekte -------------------------------------------------------------- #
    def _wz_flames(self, img, d, L, t, glow):
        for k, (x, y, size) in enumerate(L["flames"]):
            fl = 0.8 + 0.2 * math.sin(t * 13 + k * 2.1) + 0.1 * math.sin(t * 29 + k)
            self._blob(img, x, y - 2 * size, 14 * size * fl, 18 * size * fl, (255, 150, 40), alpha=0.55, flat=True)
            self._blob(img, x, y, 6 * size, 10 * size * fl, (255, 120, 30), gloss=0.0)
            self._blob(img, x, y + 1, 3 * size, 5 * size * fl, (255, 236, 150), gloss=0.0)

    def _wz_glitter(self, st, cx, foot, s, bt, dt):
        rng = st["rng"]
        if bt < 2.6:
            for _ in range(4):
                a = rng.uniform(0, 2 * math.pi)
                v = rng.uniform(30, 80)
                st["sparks"].append([cx, foot - 60 * s, math.cos(a) * v, math.sin(a) * v - 30, 1.0,
                                     rng.choice([(255, 230, 120), (255, 255, 255), (255, 170, 200)])])

    def _wz_draw_sparks(self, st, d, dt):
        self._fx_step(st["sparks"], dt, grav=60.0, fade=0.8, cap=160)
        for x, y, _, _, life, col in st["sparks"]:
            r = 1.2 if life > 0.5 else 0.8
            d.ellipse([x - r, y - r, x + r, y + r], fill=_wz_shade(col, 0.5 + life * 0.5))

    def _wz_umbrella(self, f, d, cx, y, s):
        w = 34 * s
        for k in range(6):
            a0, a1 = 180 + k * 30, 180 + (k + 1) * 30
            d.pieslice([cx - w, y - w * 0.6, cx + w, y + w * 0.6], a0, a1,
                       fill=(200, 30, 40) if k % 2 == 0 else (245, 245, 245))
        d.line([(cx, y), (cx, y + 30 * s)], fill=(60, 40, 30), width=max(1, int(2 * s)))
        d.arc([cx - 4 * s, y + 26 * s, cx + 2 * s, y + 34 * s], 0, 180, fill=(60, 40, 30), width=max(1, int(2 * s)))

    # -- Gags je Ort ---------------------------------------------------------- #
    def _wz_gag_kellner(self, f, d, t, gl, cx, foot, s, say, st, L):
        x = -30 + gl * 56
        dodge = max(0.0, 1 - abs(x - cx) / 40)
        y = WZ_FLOOR + 10
        hc, hands = self._fig(f, d, x, y, t, (250, 250, 250), {"lh": (-12, 16), "rh": (14, -16 - 4 * dodge)}, h=1.05,
                              legs=(24, 24, 30), hair=(40, 30, 26), lean=-0.3 * dodge)
        tx, ty = hands[1]
        wob = math.sin(gl * 14) * 3 * dodge
        d.ellipse([tx - 13, ty - 2 + wob * 0.3, tx + 13, ty + 2 + wob * 0.3], fill=(200, 200, 210))
        for k in (-7, 0, 7):
            gx = tx + k + wob
            d.polygon([(gx - 2, ty - 10), (gx + 2, ty - 10), (gx + 0.5, ty - 4), (gx - 0.5, ty - 4)], fill=(250, 236, 170))
            d.line([(gx, ty - 4), (gx, ty - 1)], fill=(220, 220, 230))
        if 3.0 < gl < 4.2:                                                      # ein Glas fliegt – gefangen
            k = (gl - 3.0) / 1.2
            gx, gy = tx + 30 * k, ty - 10 - 40 * math.sin(math.pi * k)
            d.polygon([(gx - 2, gy - 6), (gx + 2, gy - 6), (gx, gy)], fill=(250, 236, 170))
        if 0.6 < gl < 2.8:
            say.append((hc[0], hc[1] - 26, "Champagner gefällig?"))
        elif 3.0 <= gl < 5.0:
            say.append((hc[0], hc[1] - 26, "Hoppla – gerade noch!"))

    def _wz_gag_ritter(self, f, d, t, gl, cx, foot, s, say, st, L):
        if gl < 2.5:
            x = WIDTH + 30 - (WIDTH + 30 - (cx + 46)) * gl / 2.5
        elif gl < 6.3:
            x = cx + 46
        else:
            x = cx + 46 + (gl - 6.3) * 120
        x = min(x, WIDTH + 40)
        walking = gl < 2.5 or gl >= 6.3
        sw = math.sin(gl * 9) * 5 if walking else 0
        bow = 2.5 <= gl < 4.6
        pose = {"lh": (-8, 20), "rh": (10 if not bow else 16, 18 if not bow else 6), "lf": (-6 + sw, 34),
                "rf": (6 - sw, 34)}
        hc, _ = self._fig(f, d, x, WZ_FLOOR + 6, t, (170, 176, 188), pose, h=1.1, legs=(150, 156, 168), hair=None,
                          lean=-0.35 if bow else 0.0, face=-1)
        d.ellipse([hc[0] - 9, hc[1] - 10, hc[0] + 9, hc[1] + 9], fill=(178, 184, 196), outline=(110, 114, 126))
        d.line([(hc[0] - 6, hc[1] - 1), (hc[0] + 4, hc[1] - 1)], fill=(30, 30, 36), width=2)
        for k in range(4):
            d.line([(hc[0] + 2, hc[1] - 10), (hc[0] - 4 - k * 3, hc[1] - 18 - k * 2 + math.sin(t * 6 + k))],
                   fill=(210, 30, 40), width=2)
        if walking and int(gl * 4) % 2 == 0:
            d.text((x - 24, WZ_FLOOR - 4), "klirr", font=self.f_tiny, fill=(230, 230, 240))
        if 2.6 < gl < 4.6:
            say.append((hc[0], hc[1] - 24, "Darf ich um diesen Tanz bitten?"))
        elif 4.6 <= gl < 6.4:
            say.append((cx - 10, WZ_FLOOR - 104, "Später, Herr Ritter!"))

    def _wz_gag_kuh(self, f, d, t, gl, cx, foot, s, say, st, L):
        x = -50 + min(1.0, gl / 2.0) * 90 if gl < 6.6 else 40 - (gl - 6.6) * 70
        y = WZ_FLOOR - 20
        sway = math.sin(t * math.pi * 2 / 1.5) * 4 if 2.0 <= gl < 6.6 else 0
        for lx in (-16, -8, 10, 18):
            step = math.sin(t * 9 + lx) * 3 if gl < 2.0 or gl >= 6.6 else 0
            d.line([(x + lx, y + 6), (x + lx + step, y + 22)], fill=(60, 50, 46), width=4)
        self._blob(f, x, y, 52, 28, (246, 244, 238), gloss=0.3, ang=sway)
        for ox, oy, w in ((-10, -4, 12), (8, 2, 14), (16, -6, 8)):
            self._blob(f, x + ox, y + oy, w, w * 0.7, (34, 30, 30), gloss=0.2)
        hx, hy = x + 30 + sway, y - 10
        self._blob(f, hx, hy, 18, 16, (246, 244, 238), gloss=0.3)
        self._blob(f, hx + 4, hy + 5, 12, 8, (236, 170, 170), gloss=0.3)
        d.line([(hx - 6, hy - 8), (hx - 10, hy - 14)], fill=(240, 230, 200), width=2)
        d.line([(hx + 4, hy - 8), (hx + 8, hy - 14)], fill=(240, 230, 200), width=2)
        d.point((hx - 2, hy - 2), fill=(0, 0, 0))
        self._blob(f, hx - 4, hy + 12, 7, 8, (230, 190, 60), gloss=0.9)             # Glocke
        if 2.0 <= gl < 6.6:
            for k in range(2):
                ny = hy - 10 - ((t * 20 + k * 12) % 24)
                d.text((hx + 8 + k * 8, ny), "♪", font=self.f_small_b, fill=(250, 240, 180))
        if 3.0 < gl < 5.0:
            say.append((hx, hy - 16, "Muuuh!"))

    def _wz_gag_funken(self, f, d, t, gl, cx, foot, s, say, st, L):
        rng = random.Random(int(gl * 15))
        if gl < 1.8:
            for _ in range(10):
                x = cx + rng.uniform(-30, 30)
                y = (gl * 150 + rng.uniform(0, 120)) % (foot - 20)
                d.line([(x, y), (x + 1, y + 4)], fill=(255, 200, 80), width=2)
        if 1.4 < gl < 5.0:                                                       # Rauch aus dem Frack
            for k in range(4):
                a = (gl - 1.4) * 1.2 + k * 0.4
                self._blob(f, cx + 10 + math.sin(a * 3) * 4, foot - 38 - a * 26, 10 + a * 4, 8 + a * 3, (150, 150, 156),
                           alpha=max(0.0, 0.7 - a * 0.15), flat=True)
        if 1.6 < gl < 3.6:
            say.append((cx + 10, foot - 110, "Heiß! Heiß!"))
        elif 3.6 <= gl < 5.6:
            say.append((cx - 10, foot - 110, "Ein feuriger Tänzer!"))

    def _wz_gag_huhn(self, f, d, t, gl, cx, foot, s, say, st, L):
        x = WIDTH + 20 - gl * 75
        y = WZ_FLOOR + 6 + abs(math.sin(gl * 10)) * -4
        zig = math.sin(gl * 6) * 6
        self._blob(f, x + zig, y - 8, 18, 14, (250, 250, 246), gloss=0.3)
        self._blob(f, x + zig - 8, y - 16, 9, 9, (250, 250, 246), gloss=0.3)
        d.polygon([(x + zig - 13, y - 16), (x + zig - 18, y - 14), (x + zig - 13, y - 13)], fill=(240, 170, 40))
        d.ellipse([x + zig - 10, y - 22, x + zig - 6, y - 18], fill=(220, 40, 40))
        for lx in (-2, 3):
            d.line([(x + zig + lx, y - 2), (x + zig + lx + math.sin(gl * 20 + lx) * 3, y + 4)], fill=(240, 170, 40), width=2)
        if abs(x - cx) < 40:
            rng = random.Random(3)
            for k in range(6):
                fx_, fy_ = cx + rng.uniform(-30, 30), foot - 10 - rng.uniform(0, 40) + (gl * 20 % 30)
                d.ellipse([fx_ - 2, fy_ - 1, fx_ + 2, fy_ + 1], fill=(250, 250, 250))
        if 1.0 < gl < 3.4:
            say.append((x + zig, y - 30, "Gack!"))

    def _wz_gag_ente(self, f, d, t, gl, cx, foot, s, say, st, L):
        y0 = 128
        x0 = WIDTH + 20 - gl * 48
        for k in range(4):
            big = k == 0
            x = x0 + k * 18
            y = y0 + (0 if big else 3) + abs(math.sin(t * math.pi * 2 + k * 0.7)) * -2
            w = 16 if big else 9
            self._blob(f, x, y, w, w * 0.55, (150, 120, 80) if big else (240, 220, 90), gloss=0.3)
            self._blob(f, x - w * 0.45, y - w * 0.45, w * 0.5, w * 0.5, (40, 110, 60) if big else (240, 220, 90), gloss=0.4)
            d.polygon([(x - w * 0.7, y - w * 0.45), (x - w * 0.95, y - w * 0.38), (x - w * 0.7, y - w * 0.32)],
                      fill=(240, 150, 40))
            d.arc([x - w, y + 1, x + w, y + 5], 0, 180, fill=(200, 220, 240))
        if 3.0 < gl < 4.8:
            say.append((x0, y0 - 14, "Quak!"))

    def _wz_gag_murmeltier(self, f, d, t, gl, cx, foot, s, say, st, L):
        x, y = 34, WZ_FLOOR + 12
        up = min(1.0, gl / 0.8) if gl < 4.6 else max(0.0, 1 - (gl - 4.6) / 0.6)
        d.ellipse([x - 12, y - 3, x + 12, y + 4], fill=(70, 54, 40))
        if up > 0:
            h = 26 * up
            self._blob(f, x, y - h / 2, 15, h, (160, 120, 80), gloss=0.3)
            self._blob(f, x, y - h + 2, 13, 12, (166, 126, 86), gloss=0.3)
            d.point((x - 3, y - h + 1), fill=(0, 0, 0))
            d.point((x + 3, y - h + 1), fill=(0, 0, 0))
            d.ellipse([x - 2, y - h + 4, x + 2, y - h + 7], fill=(60, 40, 30))
            if 1.0 < gl < 3.2:
                for k in range(3):
                    r = 8 + k * 6 + (gl * 20 % 6)
                    d.arc([x - r, y - h - r * 0.6, x + r, y - h + r * 0.6], 300, 360, fill=(250, 250, 250))
                say.append((x + 24, y - 54, "Pfiiiiff!"))
        if 3.2 <= gl < 4.8:
            say.append((cx, foot - 110, "Huch! Was war das?"))

    def _wz_gag_moewe(self, f, d, t, gl, cx, foot, s, say, st, L):
        if gl < 2.6:
            k = gl / 2.6
            x, y = WIDTH + 20 - (WIDTH + 20 - cx) * k, 20 + (foot - 100) * k * k
        else:
            k = (gl - 2.6) / 4.4
            x, y = cx - k * (cx + 40), foot - 100 - k * 90
        flap = math.sin(t * 14) * 8
        self._blob(f, x, y, 16, 8, (246, 246, 250), gloss=0.3)
        self._blob(f, x - 8, y - 3, 7, 6, (246, 246, 250), gloss=0.3)
        d.polygon([(x - 11, y - 3), (x - 16, y - 2), (x - 11, y - 1)], fill=(240, 190, 40))
        for sd in (-1, 1):
            d.line([(x - 2, y - 2), (x + sd * 6, y - 10 - flap * sd * 0.2 - abs(flap)), (x + sd * 14, y - 6 - flap)],
                   fill=(200, 200, 210), width=2)
        if gl >= 2.6:
            d.polygon([(x - 14, y + 2), (x - 6, y + 4), (x - 14, y + 6), (x - 6, y + 2)], fill=(20, 20, 24))
        if 2.8 < gl < 5.4:
            say.append((min(WIDTH - 60, cx + 70), foot - 70, "Hey! Gib das zurück!"))
