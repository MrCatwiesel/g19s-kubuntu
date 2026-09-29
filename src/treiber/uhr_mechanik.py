"""Zifferblätter Pendeluhr, Kuckucksuhr, Taschenuhr, Sanduhr, Kerzenuhr."""
import math
import random

_MECH_ROMAN = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
_MECH_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_MECH_SERIF_C = "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf"


def _mech_bezier(p0, p1, p2, p3, n):
    """Punkte einer kubischen Bézierkurve (Displaykoordinaten)."""
    out = []
    for i in range(n + 1):
        u = i / n
        v = 1 - u
        out.append((v ** 3 * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u ** 3 * p3[0],
                    v ** 3 * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u ** 3 * p3[1]))
    return out


def _mech_wave(t, parts):
    """Deterministisches „Rauschen“ aus Sinuswellen [(Frequenz, Phase, Gewicht), …] → etwa −1…1."""
    return sum(w * math.sin(2 * math.pi * fr * t + ph) for fr, ph, w in parts)


class MechanicalFaces:
    # --- Hilfen --------------------------------------------------------------- #
    def _mech_fonts(self):
        if not hasattr(self, "_mech_f"):
            s = CLOCK_SS
            try:
                mono = ImageFont.truetype(_MECH_MONO, 20 * s)
            except OSError:
                mono = load_font(20 * s, bold=True)
            cond = (lambda n: ImageFont.truetype(_MECH_SERIF_C, n * s)) if os.path.exists(_MECH_SERIF_C) \
                else (lambda n: load_serif((n - 1) * s, bold=True))
            self._mech_f = {"arab": load_serif(13 * s, bold=True), "mono": mono,
                            "label": load_font(9 * s, bold=True), "date": load_font(11 * s, bold=True),
                            "romc9": cond(9), "romc8": cond(8)}
        return self._mech_f

    @staticmethod
    def _mech_poly(c, pts, fill=None, outline=None, width=1):
        s = CLOCK_SS
        c.d.polygon([(x * s, y * s) for x, y in pts], fill=fill, outline=outline,
                    width=max(1, round(width * s)) if outline else 0)

    @staticmethod
    def _mech_line(c, pts, fill, width=1):
        s = CLOCK_SS
        c.d.line([(x * s, y * s) for x, y in pts], fill=fill, width=max(1, round(width * s)), joint="curve")

    @staticmethod
    def _mech_ellipse(c, x0, y0, x1, y1, fill=None, outline=None, width=1):
        s = CLOCK_SS
        c.d.ellipse([x0 * s, y0 * s, x1 * s, y1 * s], fill=fill, outline=outline,
                    width=max(1, round(width * s)) if outline else 0)

    @staticmethod
    def _mech_at(c, cx, cy, r, deg):
        return [v / CLOCK_SS for v in c.pt(cx, cy, r, deg)]

    @staticmethod
    def _mech_text_rot(c, x, y, txt, font, fill, deg):
        """Text mittig um (x, y), um deg gedreht (Kopf nach außen wie auf alten Zifferblättern)."""
        w = int(font.getlength(txt)) + 8
        h = int(font.size * 1.5) + 8
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text((w / 2, h / 2), txt, font=font, fill=255, anchor="mm")
        m = m.rotate(-deg, resample=Image.BICUBIC, expand=True)
        c.img.paste(fill, (int(x * CLOCK_SS - m.width / 2), int(y * CLOCK_SS - m.height / 2)), m)

    @staticmethod
    def _mech_vgrad(c, x0, y0, x1, y1, top, bottom):
        """Senkrechter Farbverlauf."""
        s = CLOCK_SS
        n = max(1, int((y1 - y0) * s))
        for i in range(n):
            c.d.line([(x0 * s, y0 * s + i), (x1 * s - 1, y0 * s + i)], fill=mix(top, bottom, i / n))

    @staticmethod
    def _mech_hgrad(c, x0, y0, x1, y1, edge, mid, light=0.35):
        """Waagerechter Verlauf wie ein Zylinder (Glanzlicht bei light, 0…1)."""
        s = CLOCK_SS
        n = max(1, int((x1 - x0) * s))
        span = max(light, 1 - light)
        for i in range(n):
            k = math.cos(min(1.0, abs(i / n - light) / span) * math.pi / 2)
            c.d.line([(x0 * s + i, y0 * s), (x0 * s + i, y1 * s - 1)], fill=mix(edge, mid, k))

    @staticmethod
    def _mech_wood(c, x0, y0, x1, y1, base, seed, vertical=True, strength=16):
        """Holzfläche mit Maserung."""
        s = CLOCK_SS
        c.rect(x0, y0, x1, y1, fill=base)
        rnd = random.Random(seed)
        length, across = ((y1 - y0), (x1 - x0)) if vertical else ((x1 - x0), (y1 - y0))
        for _ in range(int(across * 1.4)):
            off, d = rnd.uniform(0, across), rnd.uniform(-strength, strength * 0.6)
            col = tuple(max(0, min(255, int(v + d))) for v in base)
            amp, fr, ph = rnd.uniform(0.2, 1.6), rnd.uniform(0.02, 0.09), rnd.uniform(0, 6.3)
            pts = []
            for i in range(0, int(length) + 3, 3):
                w = min(max(off + amp * math.sin(min(i, length) * fr + ph), 0), across)
                i = min(i, length)
                pts.append(((x0 + w) * s, (y0 + i) * s) if vertical else ((x0 + i) * s, (y0 + w) * s))
            c.d.line(pts, fill=col, width=rnd.choice((1, 1, 2, 3)))

    def _mech_wood_poly(self, c, pts, base, seed, vertical=True, strength=16):
        """Holzfläche in Form eines Vielecks."""
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        tmp = _Canvas(Image.new("RGB", c.img.size, base))
        self._mech_wood(tmp, min(xs), min(ys), max(xs), max(ys), base, seed, vertical, strength)
        mask = Image.new("L", c.img.size, 0)
        ImageDraw.Draw(mask).polygon([(x * CLOCK_SS, y * CLOCK_SS) for x, y in pts], fill=255)
        c.img.paste(tmp.img, (0, 0), mask)

    def _mech_radial_fill(self, c, cx, cy, r, inner, outer, start=0.0, step=1.5):
        """Kreisfläche mit Verlauf von innen nach außen (ab start·r)."""
        rr = r
        while rr > 0:
            k = max(0.0, (rr / r - start) / (1 - start)) if start < 1 else 1
            c.circle(cx, cy, rr, fill=mix(inner, outer, k))
            rr -= step

    def _mech_metal_ring(self, c, cx, cy, r0, r1, light, dark, fill_inner=None, light_deg=315):
        """Metallring zwischen r0 und r1 mit Licht von light_deg (0 = oben)."""
        s = CLOCK_SS
        box = [(cx - r1) * s, (cy - r1) * s, (cx + r1) * s, (cy + r1) * s]
        for a in range(0, 360, 4):
            k = (math.cos(math.radians(a + 2 - light_deg)) + 1) / 2
            c.d.pieslice(box, a - 90, a - 90 + 5, fill=mix(dark, light, k ** 1.3))
        if fill_inner is not None:
            c.circle(cx, cy, r0, fill=fill_inner)

    def _mech_side_date(self, c, now, col, dim):
        """Dezentes Datum links und rechts neben einem schmalen Gehäuse."""
        f, mf = self._cfonts, self._mech_fonts()
        c.text(50, 88, WEEKDAYS[now.tm_wday], mf["date"], dim)
        c.text(50, 114, str(now.tm_mday), f["big"], col)
        c.text(270, 100, MONTHS[now.tm_mon - 1], mf["date"], dim)
        c.text(270, 118, str(now.tm_year), f["tiny"], dim)

    # --- Pendeluhr ------------------------------------------------------------ #
    _MECH_PEND = (160, 84, 96, 9.5)              # Aufhängung x, y, Pendellänge, Ausschlag (Grad)
    _MECH_PEND_WIN = (124, 142, 196, 194)        # Glasfenster

    def _mech_pendulum_static(self, c):
        f, mf = self._cfonts, self._mech_fonts()
        cx, cy = 160, 84
        self._mech_vgrad(c, 0, 0, WIDTH, CLOCK_H, (30, 23, 20), (12, 10, 10))
        walnut, dark, light = (104, 58, 30), (52, 28, 14), (150, 96, 54)
        brass, brass_hi, brass_lo = (190, 146, 66), (240, 204, 124), (110, 76, 30)
        c.rect(110, 36, 220, 204, fill=(8, 6, 6))                          # Schatten an der Wand
        self._mech_wood(c, 106, 32, 214, 200, walnut, 1)
        # Kranz mit Giebel, Rosette und Knäufen
        self._mech_wood_poly(c, [(98, 30), (160, 7), (222, 30)], (120, 70, 36), 2, vertical=False)
        self._mech_line(c, [(98, 30), (160, 7), (222, 30)], light, 1.2)
        self._mech_poly(c, [(114, 27), (160, 12), (206, 27)], fill=(84, 46, 22))
        self._mech_line(c, [(114, 27), (160, 12), (206, 27), (114, 27)], dark, 0.8)
        for x in (138, 182):                                               # geschnitzte Ranken im Giebel
            d = -1 if x < 160 else 1
            self._mech_line(c, _mech_bezier((160 + d * 6, 22), (x, 14), (x - d * 12, 30), (x + d * 10, 24), 12),
                            (150, 100, 58), 1.3)
        c.circle(cx, 20.5, 4.2, fill=brass_lo)
        c.circle(cx, 20.5, 3.4, fill=brass)
        c.circle(cx - 0.8, 19.7, 1.3, fill=brass_hi)
        for x, y, r in ((100, 26, 3.2), (220, 26, 3.2), (160, 5, 3)):
            c.rect(x - 1.5, y, x + 1.5, y + 4, fill=dark)
            c.circle(x, y, r, fill=light, outline=dark, width=0.6)
        c.rect(94, 30, 226, 35, fill=light)
        c.rect(94, 34, 226, 36, fill=dark)
        c.rect(100, 36, 220, 38, fill=(76, 42, 20))
        # Zifferblattfeld mit Messingzwickeln
        c.rect(110, 40, 210, 130, outline=dark, width=0.8)
        for sx, sy in ((113, 43), (207, 43), (113, 127), (207, 127)):
            dx, dy = (1 if sx < 160 else -1), (1 if sy < 84 else -1)
            for k, (ox, oy) in enumerate(((0, 0), (7, 1.5), (1.5, 7))):
                c.circle(sx + dx * ox, sy + dy * oy, 3.2 if k == 0 else 2.2, fill=brass_lo)
                c.circle(sx + dx * ox - 0.4, sy + dy * oy - 0.4, 2.3 if k == 0 else 1.5, fill=brass)
        self._mech_metal_ring(c, cx, cy, 45, 49, brass_hi, brass_lo)
        c.circle(cx, cy, 49, outline=(70, 46, 18), width=0.8)
        c.circle(cx, cy, 45.5, fill=brass_lo)
        self._mech_radial_fill(c, cx, cy, 45, (246, 238, 218), (222, 208, 176), start=0.55)
        ink = (40, 30, 26)
        c.circle(cx, cy, 42, outline=ink, width=0.7)
        c.circle(cx, cy, 38.5, outline=ink, width=0.6)
        for m in range(60):
            c.radial(cx, cy, 38.5, 42, m * 6, 1.4 if m % 5 == 0 else 0.5, ink)
        for h, num in enumerate(_MECH_ROMAN):
            x, y = self._mech_at(c, cx, cy, 32.5, h * 30)
            self._mech_text_rot(c, x, y, num, mf["romc9"], ink, h * 30)
        c.text(cx, cy - 15, "G19s", f["serif_s"], (110, 80, 50))
        # Gesims zwischen Zifferblatt und Fenster
        c.rect(104, 132, 216, 137, fill=light)
        c.rect(104, 136, 216, 137.6, fill=dark)
        # Fenster mit Säulen
        x0, y0, x1, y1 = self._MECH_PEND_WIN
        c.rect(x0 - 5, y0 - 4, x1 + 5, y1 + 4, fill=dark)
        c.rect(x0 - 3, y0 - 2, x1 + 3, y1 + 2, fill=(132, 84, 44))
        self._mech_vgrad(c, x0, y0, x1, y1, (60, 36, 20), (34, 20, 12))
        for k in range(1, 6):                                              # Rückwand-Bretter
            c.rect(x0 + k * 12, y0, x0 + k * 12 + 0.5, y1, fill=(44, 26, 14))
        c.rect(x0, y1 - 8, x1, y1 - 7.6, fill=(80, 56, 30))               # Abfallskala
        for k in range(-6, 7):
            c.radial(cx + k * 3.2, y1 - 7.6, 0, -2.5 if k % 3 else -4, 0, 0.5, (190, 150, 80))
        for px in (108, 204):
            self._mech_hgrad(c, px, 140, px + 8, 196, (70, 38, 18), (170, 112, 62))
            for yy in (140, 146, 190):
                self._mech_hgrad(c, px - 1, yy, px + 9, yy + 4, (60, 32, 14), (186, 128, 74))
        # Sockel mit Abhängling
        c.rect(98, 198, 222, 204, fill=light)
        c.rect(98, 203, 222, 204.5, fill=dark)
        self._mech_poly(c, [(110, 204), (210, 204), (196, 209), (124, 209)], fill=walnut, outline=dark, width=0.6)
        self._mech_poly(c, [(150, 209), (170, 209), (160, 214)], fill=light)

    def _mech_glass_mask(self, key, w, h, stripes):
        """Maske für einen Glasreflex (schräge Streifen), zwischengespeichert."""
        if key not in self._cdials:
            s = CLOCK_SS
            m = Image.new("L", (int(w * s), int(h * s)), 0)
            d = ImageDraw.Draw(m)
            for x, width, alpha in stripes:
                d.polygon([(x * s, 0), ((x + width) * s, 0), ((x + width - h * 0.45) * s, h * s),
                           ((x - h * 0.45) * s, h * s)], fill=alpha)
            self._cdials[key] = m
        return self._cdials[key]

    @clock_face("pendulum", fps=lambda o: 5 if o["swing"] else 1)
    def face_pendulum(self, profile):
        opt = self._copt("pendulum")
        c = self._clock_canvas("mech_pendulum", (12, 10, 10), self._mech_pendulum_static)
        t = self._clock_now()
        now = time.localtime(t)
        px, py, length, amp = self._MECH_PEND
        x0, y0, x1, y1 = self._MECH_PEND_WIN
        # Halbschwingung je Sekunde: an vollen Sekunden im Umkehrpunkt
        if opt["swing"]:
            deg = amp * math.cos(math.pi * (t % 2))
        else:
            deg = amp if int(t) % 2 == 0 else -amp
        a = math.radians(deg)
        bx, by = px + length * math.sin(a), py + length * math.cos(a)
        top_x = px + (y0 - py) * math.tan(a)
        brass, brass_hi, brass_lo = (196, 152, 70), (246, 214, 140), (118, 82, 32)
        self._mech_line(c, [(top_x, y0), (bx, by)], brass_lo, 2.6)
        self._mech_line(c, [(top_x, y0), (bx, by)], brass, 1.4)
        c.circle(bx + 1, by + 1.5, 11.5, fill=(26, 15, 8))                 # Schatten auf der Rückwand
        c.circle(bx, by, 11, fill=brass_lo)
        c.circle(bx - 0.6, by - 0.6, 10, fill=brass)
        c.circle(bx - 2.2, by - 2.2, 6, fill=mix(brass, brass_hi, 0.55))
        c.circle(bx - 3.4, by - 3.4, 2.6, fill=brass_hi)
        c.circle(bx, by, 11, outline=(90, 60, 24), width=0.6)
        c.hand(bx, by, 0, [(-11, 2.2), (-14, 2.2)], brass_lo)            # Regulierschraube
        mask = self._mech_glass_mask("mech_pend_glass", x1 - x0, y1 - y0, ((16, 7, 34), (27, 2.5, 22), (58, 12, 16)))
        c.img.paste((255, 244, 226), (x0 * CLOCK_SS, y0 * CLOCK_SS), mask)
        # Zeiger (geschwärzt, mit Ring)
        cx, cy = 160, 84
        ha, ma, _ = self._clock_angles(now)
        ink, dial = (26, 22, 24), (238, 228, 204)
        c.hand(cx, cy, ha, [(-8, 3.2), (0, 3.4), (14, 2), (17, 5.5), (23, 1.6), (26, 0)], ink)
        x, y = self._mech_at(c, cx, cy, 11, ha)
        c.circle(x, y, 3.4, fill=ink)
        c.circle(x, y, 1.6, fill=dial)
        c.hand(cx, cy, ma, [(-10, 2.6), (0, 2.8), (24, 1.4), (28, 3.8), (31, 1.1), (37, 0)], ink)
        x, y = self._mech_at(c, cx, cy, 16, ma)
        c.circle(x, y, 2.8, fill=ink)
        c.circle(x, y, 1.3, fill=dial)
        c.circle(cx, cy, 3, fill=ink)
        c.circle(cx, cy, 1.2, fill=brass)
        self._mech_side_date(c, now, (214, 184, 140), (150, 124, 96))
        return self._clock_finish(c)

    # --- Kuckucksuhr ---------------------------------------------------------- #
    _MECH_CU = {"dial": (160, 105, 38), "door": (151, 42, 169, 62), "pend": (160, 152, 46),
                "chains": (132, 188), "bottom": 150}

    def _mech_leaf(self, c, x, y, deg, length, width, fill, vein):
        """Geschnitztes Blatt ab (x, y) in Richtung deg."""
        c.hand(x, y, deg, [(0, 0.8), (length * 0.25, width * 0.8), (length * 0.55, width),
                           (length * 0.85, width * 0.5), (length, 0)], fill, outline=vein)
        c.hand(x, y, deg, [(0, 0.6), (length * 0.85, 0.4)], vein)

    def _mech_cone_sprite(self):
        """Tannenzapfen-Gewicht als Bild mit Maske (dreifach vergrößert)."""
        if "mech_cone" not in self._cdials:
            s, w, h = CLOCK_SS, 18, 34
            img = Image.new("RGB", (w * s, h * s), (0, 0, 0))
            mask = Image.new("L", (w * s, h * s), 0)
            cc, md = _Canvas(img), ImageDraw.Draw(mask)
            body = [(9 + 7 * math.sin(math.pi * min(1, (y - 4) / 26) ** 0.7) * (1 if side else -1), y)
                    for side in (0, 1) for y in (range(4, 33) if side else range(32, 3, -1))]
            md.polygon([(x * s, y * s) for x, y in body], fill=255)
            md.ellipse([6 * s, 0, 12 * s, 6 * s], fill=255)
            cc.circle(9, 3, 2.6, outline=(150, 150, 150), width=1)                  # Haken
            self._mech_poly(cc, body, fill=(70, 40, 18))
            for row in range(9):                                                    # Schuppen
                y = 7 + row * 3
                wdt = 7 * math.sin(math.pi * min(1, (y - 4) / 26) ** 0.7)
                n = max(2, int(wdt / 2.2))
                for k in range(n + 1):
                    x = 9 - wdt + 1 + k * (2 * wdt - 2) / max(1, n) + (1 if row % 2 else 0)
                    if abs(x - 9) < wdt - 0.5:
                        self._mech_ellipse(cc, x - 2, y - 1.2, x + 2, y + 2.2, fill=(122, 76, 38),
                                           outline=(58, 32, 14), width=0.5)
                        self._mech_ellipse(cc, x - 1, y - 0.6, x + 0.5, y + 0.6, fill=(150, 100, 56))
            self._cdials["mech_cone"] = (img, mask)
        return self._cdials["mech_cone"]

    def _mech_cuckoo_static(self, c):
        cx, cy, r = self._MECH_CU["dial"]
        f, mf = self._cfonts, self._mech_fonts()
        self._mech_vgrad(c, 0, 0, WIDTH, CLOCK_H, (30, 42, 34), (14, 20, 16))
        rnd = random.Random(7)
        for yy in range(8, CLOCK_H, 22):                                            # Tapetenmuster
            for xx in range(8 + (11 if (yy // 22) % 2 else 0), WIDTH, 22):
                c.hand(xx, yy, 0, [(-3, 0), (0, 3), (3, 0)], (36, 50, 40))
        wood, wood_d, wood_l = (118, 72, 38), (58, 32, 14), (160, 108, 60)
        bottom = self._MECH_CU["bottom"]
        # Vorderseite (Giebelfläche)
        front = [(108, bottom), (108, 72), (160, 34), (212, 72), (212, bottom)]
        self._mech_poly(c, [(x + 3, y + 3) for x, y in front], fill=(10, 14, 10))
        self._mech_wood_poly(c, front, wood, 11)
        self._mech_line(c, front, wood_d, 0.8)
        # Dach mit Schindeln
        outer_l, outer_r, apex_o, apex_i = (82, 78), (238, 78), (160, 16), (160, 32)
        inner_l, inner_r = (98, 82), (222, 82)
        roof = [outer_l, apex_o, outer_r, inner_r, apex_i, inner_l]
        self._mech_poly(c, [(x + 3, y + 3) for x, y in roof], fill=(10, 14, 10))
        tmp = _Canvas(Image.new("RGB", c.img.size, (60, 34, 16)))
        for side in (-1, 1):
            ex, ey = (outer_l if side < 0 else outer_r)
            ln = math.hypot(ex - 160, ey - 16)
            dx, dy = (ex - 160) / ln, (ey - 16) / ln
            nx, ny = 0, 1
            for row in range(5):
                for k in range(-1, int(ln / 5.5) + 2):
                    off = k * 5.5 + (2.75 if row % 2 else 0)
                    x = 160 + dx * off + nx * (row * 3.8 + 1)
                    y = 16 + dy * off + ny * (row * 3.8 + 1)
                    shade = rnd.randint(-10, 10)
                    col = (96 + shade, 58 + shade // 2, 30 + shade // 3)
                    self._mech_ellipse(tmp, x - 3.2, y - 1, x + 3.2, y + 5, fill=col, outline=(46, 24, 10), width=0.5)
        mask = Image.new("L", c.img.size, 0)
        ImageDraw.Draw(mask).polygon([(x * CLOCK_SS, y * CLOCK_SS) for x, y in roof], fill=255)
        c.img.paste(tmp.img, (0, 0), mask)
        self._mech_line(c, [outer_l, apex_o, outer_r], wood_l, 1.6)
        self._mech_line(c, [inner_l, apex_i, inner_r], wood_d, 1)
        for side in (-1, 1):                                                        # Zierleiste unter dem Dach
            ex, ey = inner_l if side < 0 else inner_r
            for k in range(1, 12):
                u = k / 12
                x, y = 160 + (ex - 160) * u, 32 + (ey - 32) * u
                c.circle(x, y + 1.6, 1.6, fill=wood_l, outline=wood_d, width=0.4)
        # Schnitzwerk: Blätter auf dem First, an den Seiten und unten
        leaf, vein = (136, 88, 44), (60, 34, 14)
        for deg, ln in ((-60, 11), (-25, 13), (0, 12), (25, 13), (60, 11)):
            self._mech_leaf(c, 160, 17, deg, ln, 5, leaf, vein)
        c.circle(160, 16, 2.6, fill=(170, 116, 64), outline=vein, width=0.5)
        for side in (-1, 1):
            bx = 160 + side * 50
            for deg, ln, yy in ((side * 20, 14, 136), (side * 60, 13, 142), (side * 100, 12, 147),
                                (side * 150, 12, 124), (side * -170, 10, 110)):
                self._mech_leaf(c, bx, yy, deg, ln, 5, leaf, vein)
            self._mech_leaf(c, 160 + side * 42, 72, side * 60, 11, 4.5, leaf, vein)
            self._mech_leaf(c, 160 + side * 42, 74, side * 110, 10, 4, leaf, vein)
        for k in range(9):                                                          # Schürze
            x = 116 + k * 11
            self._mech_leaf(c, x, bottom - 3, 180 + (k - 4) * 6, 10, 5, leaf, vein)
        c.rect(106, bottom - 4, 214, bottom, fill=wood_l, outline=wood_d, width=0.6)
        # Tür (geschlossen)
        d0, d1, d2, d3 = self._MECH_CU["door"]
        self._mech_ellipse(c, d0 - 2.5, d1 - 2.5, d2 + 2.5, d1 + (d2 - d0) + 1, fill=wood_d)
        c.rect(d0 - 2.5, d1 + 7, d2 + 2.5, d3 + 2, fill=wood_d)
        self._mech_ellipse(c, d0, d1, d2, d1 + (d2 - d0), fill=(132, 84, 44))
        c.rect(d0, d1 + 8, d2, d3, fill=(132, 84, 44))
        c.rect(159.6, d1 + 1, 160.4, d3, fill=wood_d)
        c.circle(163, (d1 + d3) / 2 + 2, 1, fill=(200, 170, 100))
        # Zifferblatt: dunkles Holz mit Beinziffern
        bone = (234, 222, 192)
        c.circle(cx + 2, cy + 2, r + 3, fill=(40, 22, 10))
        for k in range(24):                                                         # geschnitzter Kranz
            x, y = self._mech_at(c, cx, cy, r + 0.5, k * 15)
            c.circle(x, y, 3, fill=wood_l if k % 2 else (140, 90, 48), outline=wood_d, width=0.4)
        c.circle(cx, cy, r - 2, fill=(64, 36, 16))
        self._mech_radial_fill(c, cx, cy, r - 3, (92, 56, 28), (70, 40, 18), start=0.3)
        for m in range(60):
            if m % 5:
                x, y = self._mech_at(c, cx, cy, r - 5.5, m * 6)
                c.circle(x, y, 0.5, fill=bone)
        for h, num in enumerate(_MECH_ROMAN):
            x, y = self._mech_at(c, cx, cy, r - 12, h * 30)
            self._mech_text_rot(c, x, y, num, mf["romc8"], bone, h * 30)
            x, y = self._mech_at(c, cx, cy, r - 5.5, h * 30)
            c.circle(x, y, 1.1, fill=bone)
        # Aufhängung der Ketten
        for x in self._MECH_CU["chains"]:
            c.rect(x - 3, bottom, x + 3, bottom + 2, fill=wood_d)

    def _mech_chain_v(self, c, x, y0, y1, col, dark):
        """Senkrechte Kette von y0 bis y1."""
        y, k = y0, 0
        while y < y1:
            if k % 2:
                c.rect(x - 0.5, y, x + 0.5, y + 3.2, fill=col)
            else:
                self._mech_ellipse(c, x - 1.4, y, x + 1.4, y + 3.4, outline=col, width=0.6)
            y += 2.6
            k += 1

    @clock_face("cuckoo", fps=5)
    def face_cuckoo(self, profile):
        c = self._clock_canvas("mech_cuckoo", (14, 20, 16), self._mech_cuckoo_static)
        f, mf = self._cfonts, self._mech_fonts()
        t = self._clock_now()
        now = time.localtime(t)
        cx, cy, r = self._MECH_CU["dial"]
        bottom = self._MECH_CU["bottom"]
        wood_d, bone = (58, 32, 14), (234, 222, 192)
        # Gewichte sinken im Lauf des Tages, die freien Kettenenden steigen
        day = (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) / 86400
        steel, steel_d = (170, 170, 164), (90, 90, 86)
        cone, mask = self._mech_cone_sprite()
        for k, x in enumerate(self._MECH_CU["chains"]):
            frac = min(1.0, day + (0.04 if k else 0))
            top = bottom + 10 + 28 * frac
            free_end = bottom + 10 + 28 * (1 - frac)
            fx = x + (-7 if k == 0 else 7)
            self._mech_chain_v(c, fx, bottom + 1, free_end, steel_d, steel_d)
            c.circle(fx, free_end + 2.2, 2.2, outline=steel, width=0.8)
            self._mech_chain_v(c, x, bottom + 1, top + 1, steel, steel_d)
            c.img.paste(cone, (int((x - 9) * CLOCK_SS), int(top * CLOCK_SS)), mask)
        # Pendel (Periode 1 s)
        px, py, length = self._MECH_CU["pend"]
        a = math.radians(9 * math.sin(2 * math.pi * (t % 1)))
        bx, by = px + length * math.sin(a), py + length * math.cos(a)
        rod0 = (px + 6 * math.sin(a), py + 6 * math.cos(a))
        self._mech_line(c, [rod0, (bx, by)], (40, 22, 10), 1.8)
        leaf, vein = (136, 88, 44), (60, 34, 14)
        deg = 180 - math.degrees(a)
        for off, ln in ((-40, 10), (0, 13), (40, 10)):
            self._mech_leaf(c, bx, by - 3, deg + off, ln, 5.5, leaf, vein)
        c.circle(bx, by - 3, 2.6, fill=(170, 116, 64), outline=vein, width=0.5)
        # Tür offen: zur vollen Stunde 30 s, zur halben Stunde 10 s
        is_open = (now.tm_min == 0 and now.tm_sec < 30) or (now.tm_min == 30 and now.tm_sec < 10)
        if is_open:
            d0, d1, d2, d3 = self._MECH_CU["door"]
            self._mech_ellipse(c, d0, d1, d2, d1 + (d2 - d0), fill=(22, 12, 6))
            c.rect(d0, d1 + 8, d2, d3, fill=(22, 12, 6))
            self._mech_poly(c, [(d0, d1 + 6), (d0 - 6, d1 + 3), (d0 - 6, d3 + 2), (d0, d3)],
                            fill=(150, 98, 52), outline=wood_d, width=0.5)          # aufgeklappte Tür
            # Vogel auf der Stange, schaut nach links heraus
            self._mech_line(c, [(d0 + 2, d3 - 1), (d0 - 10, d3 - 1)], (150, 110, 60), 1.2)
            bird, bird_d = (120, 84, 50), (70, 46, 24)
            self._mech_poly(c, [(166, 50), (174, 46), (172, 52)], fill=bird_d)       # Schwanz
            self._mech_ellipse(c, 148, 48, 168, 60, fill=bird)
            self._mech_ellipse(c, 154, 50, 166, 57, fill=bird_d)                     # Flügel
            c.circle(149, 48, 5.2, fill=bird)
            self._mech_ellipse(c, 144, 50, 152, 57, fill=(214, 190, 150))            # Brust
            beak_open = int(t * 2) % 2 == 0
            self._mech_poly(c, [(144.5, 46), (138, 47 if beak_open else 48), (144.5, 48.5)], fill=(236, 180, 40))
            if beak_open:
                self._mech_poly(c, [(144.5, 49), (139, 50.5), (144.5, 50)], fill=(236, 180, 40))
            c.circle(147.5, 46.5, 1.3, fill=(250, 250, 250))
            c.circle(147.2, 46.5, 0.7, fill=(10, 10, 10))
            c.text(262, 40, "Kuckuck!", f["side"], (236, 214, 160))
        # Zeiger (bein, verziert)
        ha, ma, _ = self._clock_angles(now)
        out = (60, 38, 18)
        c.hand(cx, cy, ha, [(-7, 3.2), (0, 3.6), (9, 2), (13, 6.6), (17, 2), (19.5, 4.4), (23, 0)], bone, outline=out)
        c.hand(cx, cy, ma, [(-9, 2.8), (0, 3.2), (21, 1.6), (25, 4.8), (28, 1.4), (34, 0)], bone, outline=out)
        c.circle(cx, cy, 3.2, fill=bone, outline=out, width=0.5)
        c.circle(cx, cy, 1.2, fill=out)
        # dezent: Datum links, Uhrzeit rechts
        c.text(44, 96, WEEKDAYS[now.tm_wday], mf["date"], (170, 180, 160))
        c.text(44, 118, f"{now.tm_mday}. {MONTH_3[now.tm_mon - 1].title()}", mf["date"], (130, 142, 124))
        c.text(276, 106, time.strftime("%H:%M", now), f["side"], (170, 180, 160))
        return self._clock_finish(c)

    # --- Taschenuhr ----------------------------------------------------------- #
    _MECH_PO = (150, 132, 78)                    # Mittelpunkt und Radius des Gehäuses

    def _mech_pocket_static(self, c):
        cx, cy, R = self._MECH_PO
        f, mf = self._cfonts, self._mech_fonts()
        gold, gold_hi, gold_lo = (212, 168, 78), (252, 226, 150), (112, 78, 24)
        for rr in range(260, 0, -4):                                                # Samt mit Lichtkegel
            k = min(1.0, rr / 230)
            c.circle(cx + 10, cy - 10, rr, fill=mix((70, 20, 30), (16, 5, 8), k ** 0.8))
        # Kette hängt links herab (Glieder abwechselnd flach und hochkant)
        pts = _mech_bezier((140, 18), (92, -8), (14, 36), (30, 150), 400)
        dist, last, k = 0.0, pts[0], 0
        for p in pts[1:]:
            dist += math.hypot(p[0] - last[0], p[1] - last[1])
            last = p
            if dist >= 4.6:
                dist, i = 0.0, pts.index(p)
                q = pts[min(len(pts) - 1, i + 3)]
                deg = math.degrees(math.atan2(q[0] - p[0], -(q[1] - p[1])))
                ln, wd = 3.4, (2.1 if k % 2 == 0 else 0.8)
                c.circle(p[0] + 1.5, p[1] + 2, 2.4, fill=mix((40, 12, 16), (16, 5, 8), 0.5))
                if k % 2 == 0:
                    c.hand(p[0], p[1], deg, [(-ln, 0.6), (-ln * 0.6, wd * 2), (ln * 0.6, wd * 2), (ln, 0.6)], gold_lo)
                    c.hand(p[0], p[1], deg, [(-ln * 0.7, 0.4), (-ln * 0.4, 1.4), (ln * 0.4, 1.4), (ln * 0.7, 0.4)],
                           (70, 22, 30))
                    c.hand(p[0] - 0.4, p[1] - 0.4, deg, [(-ln * 0.3, 0.6), (ln * 0.3, 0.6)], gold_hi)
                else:
                    c.hand(p[0], p[1], deg, [(-ln, 1.6), (ln, 1.6)], gold)
                k += 1
        c.circle(30, 153, 3.4, outline=gold, width=1.2)                             # Ring und Knebel
        c.hand(30, 159, 90, [(-13, 2.2), (-11, 3.4), (11, 3.4), (13, 2.2)], gold_lo)
        c.hand(30, 158.6, 90, [(-12, 1.2), (12, 1.2)], gold_hi)
        c.circle(30, 159, 2.4, fill=gold, outline=gold_lo, width=0.5)
        # Bügel, Krone, Pendant
        c.circle(cx + 4, 25, 15, outline=(20, 6, 10), width=3.6)
        c.circle(cx, 22, 14, outline=gold_lo, width=3.8)
        c.circle(cx, 22, 13.6, outline=gold, width=2.4)
        self._mech_ellipse(c, cx - 13.5, 12, cx - 11, 20, fill=gold_hi)
        self._mech_hgrad(c, cx - 8, 32, cx + 8, 45, gold_lo, gold_hi, 0.4)
        for k in range(9):
            x = cx - 7 + k * 1.75
            c.rect(x, 32, x + 0.5, 45, fill=gold_lo)
        c.rect(cx - 8.5, 31, cx + 8.5, 33, fill=gold)
        self._mech_poly(c, [(cx - 6, 45), (cx + 6, 45), (cx + 9, cy - R + 2), (cx - 9, cy - R + 2)], fill=gold)
        self._mech_hgrad(c, cx - 5, 45, cx + 5, cy - R + 2, gold_lo, gold_hi, 0.4)
        # Gehäuse, Lünette, Emaille-Zifferblatt
        c.circle(cx + 4, cy + 5, R + 1, fill=(16, 4, 8))
        c.circle(cx, cy, R, fill=gold_lo)
        self._mech_metal_ring(c, cx, cy, R - 9, R - 0.8, gold_hi, (150, 108, 40))
        c.circle(cx, cy, R - 5, outline=gold_lo, width=0.6)
        c.circle(cx, cy, R - 9, fill=gold_lo)
        self._mech_radial_fill(c, cx, cy, R - 10, (252, 251, 247), (228, 224, 214), start=0.7, step=1)
        ink = (18, 18, 22)
        c.circle(cx, cy, R - 13, outline=ink, width=0.7)
        c.circle(cx, cy, R - 17, outline=ink, width=0.6)
        for m in range(60):
            c.radial(cx, cy, R - 17, R - 13, m * 6, 0.6 if m % 5 else 1.8, ink)
        for h in range(1, 13):
            if h == 6:
                continue
            x, y = self._mech_at(c, cx, cy, R - 27, h * 30)
            c.text(x, y + 0.5, str(h), mf["arab"], ink)
        c.text(cx, cy - 26, "G19s", f["serif_s"], (60, 60, 70))
        sy, sr = cy + 29, 14
        sx = cx
        c.circle(sx, sy, sr + 0.8, fill=(214, 210, 200))
        c.circle(sx, sy, sr, fill=(244, 242, 236))
        for m in range(60):
            c.radial(sx, sy, sr - (3 if m % 5 == 0 else 1.6), sr, m * 6, 0.9 if m % 5 == 0 else 0.4, ink)

    @clock_face("pocket")
    def face_pocket(self, profile):
        c = self._clock_canvas("mech_pocket", (16, 5, 8), self._mech_pocket_static)
        f, mf = self._cfonts, self._mech_fonts()
        cx, cy, R = self._MECH_PO
        now = time.localtime(self._clock_now())
        ha, ma, sa = self._clock_angles(now)
        blue, blue_hi = (26, 40, 112), (74, 100, 180)
        # Spaten-Stundenzeiger, schlanker Minutenzeiger, kleine Sekunde bei der 6
        c.hand(cx, cy, ha, [(-9, 3.6), (0, 3.4), (24, 2), (27, 3), (32, 8), (38, 5.6), (42, 1.4), (45, 0)], blue)
        c.hand(cx, cy, ha, [(2, 0.8), (22, 0.7)], blue_hi)
        c.hand(cx, cy, ma, [(-12, 3.2), (0, 3.2), (10, 2.2), (60, 0.8), (64, 0)], blue)
        c.hand(cx, cy, ma, [(2, 0.7), (40, 0.5)], blue_hi)
        x, y = self._mech_at(c, cx, cy, -10, ma)
        c.circle(x, y, 3, fill=blue)
        c.circle(cx, cy, 4, fill=blue)
        c.circle(cx, cy, 1.6, fill=(212, 168, 78))
        sy = cy + 29
        c.hand(cx, sy, sa, [(-4, 1.2), (0, 1), (12, 0.4)], blue)
        c.circle(cx, sy, 1.6, fill=blue)
        mask = self._cdials.get("mech_pocket_glass")
        if mask is None:                                                            # Glasreflex oben links
            s, r = CLOCK_SS, R - 10
            mask = Image.new("L", (int(2 * r * s), int(2 * r * s)), 0)
            d = ImageDraw.Draw(mask)
            d.ellipse([0, 0, 2 * r * s, 2 * r * s], fill=34)
            d.ellipse([10 * s, 12 * s, (2 * r + 18) * s, (2 * r + 22) * s], fill=0)
            self._cdials["mech_pocket_glass"] = mask
        c.img.paste((255, 255, 255), (int((cx - R + 10) * CLOCK_SS), int((cy - R + 10) * CLOCK_SS)), mask)
        gold, dim = (226, 190, 118), (168, 128, 90)
        c.text(282, 88, WEEKDAYS[now.tm_wday], mf["date"], dim)
        c.text(282, 114, str(now.tm_mday), f["big"], gold)
        c.text(282, 140, MONTHS[now.tm_mon - 1], mf["date"], dim)
        c.text(282, 156, str(now.tm_year), f["tiny"], dim)
        return self._clock_finish(c)

    # --- Sanduhr -------------------------------------------------------------- #
    _MECH_HG = (100, 24, 190, 44, 2.2)            # Mitte x, Glas oben, Glas unten, halbe Breite, Engstelle

    def _mech_hg_w(self, y):
        """Halbe Glasbreite in Höhe y."""
        cx, top, bot, wmax, neck = self._MECH_HG
        mid, half = (top + bot) / 2, (bot - top) / 2
        s = min(1.0, abs(y - mid) / half)
        return neck + (wmax - neck) * math.sin(0.62 * math.pi * s) / 1.0

    def _mech_hg_level(self, amount, upper):
        """Sandhöhe für amount (0…1 der Füllung) im oberen bzw. unteren Kolben."""
        key = "mech_hg_tab"
        if key not in self._cdials:
            cx, top, bot, wmax, neck = self._MECH_HG
            mid = (top + bot) / 2
            tabs = []
            for ys in ((mid - k * 0.25 for k in range(int((mid - top) * 4) + 1)),
                       (bot - k * 0.25 for k in range(int((bot - mid) * 4) + 1))):
                acc, tab = 0.0, []
                for y in ys:
                    acc += 2 * self._mech_hg_w(y) * 0.25
                    tab.append((acc, y))
                tabs.append(tab)
            self._cdials[key] = tabs
        tab = self._cdials[key][0 if upper else 1]
        target = amount * tab[-1][0] * 0.78
        for acc, y in tab:
            if acc >= target:
                return y
        return tab[-1][1]

    def _mech_turned_post(self, c, x, y0, y1, wood, dark, light):
        """Gedrechselte Säule (Profil aus Wülsten)."""
        s = CLOCK_SS
        n = int((y1 - y0) * s)
        for i in range(n):
            u = i / n
            r = 2.6 + 3 * sum(math.exp(-((u - m) / 0.03) ** 2) for m in (0.04, 0.5, 0.96)) \
                + 1.5 * sum(math.exp(-((u - m) / 0.09) ** 2) for m in (0.26, 0.74))
            y = y0 * s + i
            c.d.line([((x - r) * s, y), ((x + r) * s, y)], fill=wood)
            c.d.line([((x - r) * s, y), ((x - r * 0.45) * s, y)], fill=mix(wood, dark, 0.5))
            c.d.line([((x + r * 0.55) * s, y), ((x + r) * s, y)], fill=mix(wood, dark, 0.7))
            c.d.line([((x - r * 0.2) * s, y), ((x + r * 0.05) * s, y)], fill=light)

    def _mech_hourglass_static(self, c):
        cx, top, bot, wmax, neck = self._MECH_HG
        self._mech_vgrad(c, 0, 0, WIDTH, 198, (26, 22, 24), (14, 12, 14))
        self._mech_vgrad(c, 0, 198, WIDTH, CLOCK_H, (58, 38, 24), (34, 22, 14))    # Tischplatte
        c.rect(0, 198, WIDTH, 198.6, fill=(84, 58, 36))
        wood, dark, light = (150, 98, 52), (70, 40, 18), (206, 150, 90)
        self._mech_ellipse(c, cx - 76, 201, cx + 76, 211, fill=(22, 14, 10))       # Schatten
        # Glas (hinter den Säulen)
        left = [(cx - self._mech_hg_w(y), y) for y in range(top, bot + 1)]
        right = [(cx + self._mech_hg_w(y), y) for y in range(bot, top - 1, -1)]
        self._mech_poly(c, left + right, fill=(34, 38, 48))
        self._mech_line(c, left, (120, 136, 156), 0.9)
        self._mech_line(c, right, (120, 136, 156), 0.9)
        for px in (cx - 62, cx + 62):
            self._mech_turned_post(c, px, 18, 196, wood, dark, light)
        for y0 in (6, 190):                                                         # Platten oben und unten
            c.rect(cx - 72, y0 + 2, cx + 72, y0 + 10, fill=dark)
            self._mech_vgrad(c, cx - 71, y0 + 2.5, cx + 71, y0 + 9.5, light, wood)
            c.rect(cx - 66, y0, cx + 66, y0 + 2.5, fill=wood)
            c.rect(cx - 66, y0 + 9.5, cx + 66, y0 + 12, fill=wood)
            c.rect(cx - 72, y0 + 5.8, cx + 72, y0 + 6.3, fill=(110, 70, 36))

    @clock_face("hourglass", fps=5)
    def face_hourglass(self, profile):
        c = self._clock_canvas("mech_hourglass", (14, 12, 14), self._mech_hourglass_static)
        f, mf = self._cfonts, self._mech_fonts()
        t = self._clock_now()
        now = time.localtime(t)
        cx, top, bot, wmax, neck = self._MECH_HG
        mid = (top + bot) / 2
        into = now.tm_min * 60 + now.tm_sec + (t % 1)
        rest = max(0.0, 1 - into / 3600)
        sand, sand_d, sand_l = (224, 186, 120), (176, 136, 80), (244, 216, 160)
        # oben: verbleibender Sand mit Trichter in der Mitte
        yl = self._mech_hg_level(rest, True)
        if rest > 0.002:
            wl = self._mech_hg_w(yl)
            dip = min(7.0, (mid - yl) * 0.35)
            pts = [(cx - self._mech_hg_w(y) + 0.8, y) for y in _mech_frange(mid, yl, -1)]
            surf = [(cx + x, yl + dip * (1 - (x / wl) ** 2) ** 1.5) for x in _mech_frange(-wl + 0.8, wl - 0.8, 1)]
            pts += surf + [(cx + self._mech_hg_w(y) - 0.8, y) for y in _mech_frange(yl, mid, 1)]
            self._mech_poly(c, pts, fill=sand)
            self._mech_line(c, surf, sand_l, 0.8)
        # unten: Sandhügel wächst
        done = 1 - rest
        yb = self._mech_hg_level(done, False)
        m = min(14.0, 3 + 40 * done) if done > 0.001 else 1.5
        wb = self._mech_hg_w(yb) - 0.8
        pile = [(cx + x, yb - m * (1 - (x / wb) ** 2) ** 1.6) for x in _mech_frange(-wb, wb, 1)]
        pts = [(cx - self._mech_hg_w(y) + 0.8, y) for y in _mech_frange(bot - 0.5, yb, -1)] + pile
        pts += [(cx + self._mech_hg_w(y) - 0.8, y) for y in _mech_frange(yb, bot - 0.5, 1)]
        self._mech_poly(c, pts, fill=sand)
        self._mech_line(c, pile, sand_l, 0.8)
        self._mech_line(c, [(cx - wb * 0.2, yb - m * 0.9), (cx - wb * 0.55, yb - m * 0.4)], sand_d, 0.6)
        # rieselnder Strahl mit wandernden Körnchen
        peak = yb - m
        if rest > 0.002 and peak > mid + 2:
            length = peak - mid
            self._mech_line(c, [(cx, mid), (cx, peak)], sand_d, 0.5)
            rnd = random.Random(3)
            for k in range(14):
                y = mid + ((t * 70 + k * length / 14) % length)
                x = cx + rnd.uniform(-0.9, 0.9) * (0.3 + (y - mid) / length)
                c.circle(x, y, 0.6, fill=sand_l)
            rnd = random.Random(int(t * 5))                                         # Spritzer am Hügel
            for _ in range(3):
                c.circle(cx + rnd.uniform(-4, 4), peak + rnd.uniform(-2.5, 0.5), 0.5, fill=sand_l)
        # Glanzlichter auf dem Glas
        glare = (170, 190, 210)
        for y0, y1 in ((top + 6, mid - 22), (mid + 22, bot - 6)):
            self._mech_line(c, [(cx - self._mech_hg_w(y) + 3.5, y) for y in _mech_frange(y0, y1, 2)], glare, 0.9)
        c.rect(cx - 4, top - 3, cx + 4, top + 1, fill=(84, 54, 28))
        c.rect(cx - 4, bot - 1, cx + 4, bot + 3, fill=(84, 54, 28))
        # daneben: Uhrzeit und verbleibende Zeit
        tx = 246
        acc = PROFILE_COLOR.get(profile, self.FG)
        c.text(tx, 74, time.strftime("%H:%M:%S", now), mf["mono"], (238, 222, 190))
        left_s = 3600 - now.tm_min * 60 - now.tm_sec
        txt = f"noch {left_s} Sek." if left_s < 60 else f"noch {math.ceil(left_s / 60)} Min."
        c.text(tx, 102, txt, f["mid"], (214, 186, 130))
        c.text(tx, 118, f"bis {(now.tm_hour + 1) % 24:02d}:00 Uhr", f["tiny"], (150, 136, 116))
        c.rect(tx - 50, 132, tx + 50, 135, fill=(44, 40, 40))
        c.rect(tx - 50, 132, tx - 50 + 100 * rest, 135, fill=acc)
        c.text(tx, 158, f"{WEEKDAY_DE[now.tm_wday]}, {now.tm_mday:02d}.{now.tm_mon:02d}.{now.tm_year}",
               mf["date"], (150, 136, 116))
        return self._clock_finish(c)

    # --- Kerzenuhr ------------------------------------------------------------ #
    _MECH_CA = (100, 36, 178, 16)                 # Mitte x, Docht bei 0 Uhr, Fuß, halbe Kerzenbreite

    def _mech_candle_static(self, c):
        cx, top, base, hw = self._MECH_CA
        mf = self._mech_fonts()
        for rr in range(300, 0, -4):                                                # dunkle Wand
            c.circle(cx, 120, rr, fill=mix((34, 24, 18), (10, 8, 8), min(1.0, rr / 260)))
        self._mech_vgrad(c, 0, 198, WIDTH, CLOCK_H, (54, 34, 20), (28, 18, 10))
        c.rect(0, 198, WIDTH, 198.6, fill=(80, 54, 32))
        self._cdials["mech_candle_bg"] = c.img.copy()
        # Kerze in voller Länge mit Stundenmarken
        wax_e, wax_m = (200, 170, 126), (250, 238, 212)
        self._mech_hgrad(c, cx - hw, top, cx + hw, base + 2, wax_e, wax_m, 0.35)
        paint = (158, 38, 30)
        step = (base - top) / 24
        for h in range(1, 24):
            y = top + h * step
            if h % 3 == 0:
                c.rect(cx - hw, y - 0.35, cx - hw + 9, y + 0.35, fill=paint)
                c.rect(cx + hw - 5, y - 0.35, cx + hw, y + 0.35, fill=paint)
                c.text(cx + 1.5, y, str(h), mf["label"], paint)
            else:
                c.rect(cx - hw, y - 0.25, cx - hw + 4.5, y + 0.25, fill=mix(paint, wax_m, 0.35))
        # Halter aus Messing (Teller, Tülle, Griffring)
        brass, brass_hi, brass_lo = (190, 146, 66), (246, 212, 140), (100, 68, 26)
        self._mech_ellipse(c, cx - 58, 196, cx + 62, 208, fill=(18, 12, 8))
        c.circle(cx + 58, 190, 7.5, outline=brass_lo, width=3.2)
        c.circle(cx + 58, 190, 7.5, outline=brass, width=1.8)
        self._mech_ellipse(c, cx - 56, 186, cx + 56, 204, fill=brass_lo)
        self._mech_ellipse(c, cx - 56, 185, cx + 56, 201, fill=brass)
        self._mech_ellipse(c, cx - 48, 187, cx + 48, 199, fill=mix(brass, brass_lo, 0.35))
        self._mech_ellipse(c, cx - 40, 188, cx + 30, 196, fill=mix(brass, brass_hi, 0.25))
        self._mech_hgrad(c, cx - hw - 3, base, cx + hw + 3, 193, brass_lo, brass_hi, 0.35)
        self._mech_ellipse(c, cx - hw - 3, 190, cx + hw + 3, 196, fill=mix(brass, brass_lo, 0.3))
        self._mech_hgrad(c, cx - hw - 3, base, cx + hw + 3, 192, brass_lo, brass_hi, 0.35)
        self._mech_ellipse(c, cx - hw - 5, base - 3, cx + hw + 5, base + 3, fill=brass_hi, outline=brass_lo, width=0.6)
        c.rect(cx - hw, base - 2, cx + hw, base, fill=wax_e)

    def _mech_glow_mask(self, r):
        key = ("mech_glow", r)
        if key not in self._cdials:
            s = CLOCK_SS
            m = Image.new("L", (2 * r * s, 2 * r * s), 0)
            d = ImageDraw.Draw(m)
            for k in range(r * s, 0, -3):
                d.ellipse([r * s - k, r * s - k, r * s + k, r * s + k], fill=int(120 * (1 - k / (r * s)) ** 2.2))
            self._cdials[key] = m
        return self._cdials[key]

    @clock_face("candle", fps=5)
    def face_candle(self, profile):
        c = self._clock_canvas("mech_candle", (10, 8, 8), self._mech_candle_static)
        f, mf = self._cfonts, self._mech_fonts()
        t = self._clock_now()
        now = time.localtime(t)
        cx, top, base, hw = self._MECH_CA
        s = CLOCK_SS
        day = (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) / 86400
        yt = top + (base - top) * day
        # abgebrannter Teil: Wand wieder herstellen
        bg = self._cdials["mech_candle_bg"]
        box = (int((cx - hw - 3) * s), 0, int((cx + hw + 3) * s), int(yt * s) + 1)
        c.img.paste(bg.crop(box), box[:2])
        # Flackern (deterministisch aus der Zeit)
        n1 = _mech_wave(t, ((1.3, 0.0, 0.5), (2.9, 1.0, 0.3), (5.3, 2.0, 0.2)))
        n2 = _mech_wave(t, ((0.7, 0.5, 0.5), (1.9, 2.2, 0.3), (4.1, 0.3, 0.2)))
        fh, sway = 17 + 3.5 * n1, 1.8 * n2
        fy = yt - 3                                       # Fuß der Flamme
        r = 70
        glow = self._mech_glow_mask(r)
        gx, gy = cx + sway * 0.6, fy - 8
        c.img.paste((255, 170 + int(12 * n1), 80), (int((gx - r) * s), int((gy - r) * s)), glow)
        # Kerzenkopf mit Wachsmulde und Tropfen
        wax, wax_d = (248, 236, 210), (214, 190, 150)
        if yt < base - 1:
            rnd = random.Random(11)
            for _ in range(5):
                side = rnd.choice((-1, 1))
                x = cx + side * (hw - rnd.uniform(0, 3))
                ln = rnd.uniform(5, 16) * min(1.0, (base - yt) / 20)
                self._mech_line(c, [(x, yt), (x, yt + ln)], wax_d, 3)
                self._mech_line(c, [(x - 0.4, yt), (x - 0.4, yt + ln)], wax, 2)
                c.circle(x, yt + ln, 1.7, fill=wax)
            self._mech_ellipse(c, cx - hw - 0.5, yt - 3, cx + hw + 0.5, yt + 3, fill=wax_d)
            self._mech_ellipse(c, cx - hw + 2, yt - 2, cx + hw - 2, yt + 2, fill=(255, 244, 210))
        pool = 4 + 10 * day                                # Wachs sammelt sich an der Tülle
        self._mech_ellipse(c, cx - hw - 4, base - 2.5, cx - hw - 4 + pool, base + 3, fill=wax)
        # Docht und Flamme
        tip = (cx + sway, fy - fh)
        self._mech_line(c, [(cx, yt), (cx, fy - 4), (cx + sway * 0.3 + 1, fy - 6)], (40, 30, 24), 1.2)
        for scale, col in ((1.0, (255, 150, 40)), (0.72, (255, 206, 96)), (0.42, (255, 248, 220))):
            w = 4.6 * scale
            hh = fh * (0.55 + 0.45 * scale)
            b = fy - (1 - scale) * 2
            tp = (cx + sway * (0.6 + 0.4 * scale), b - hh)
            side_l = _mech_bezier((cx - w, b - w), (cx - w, b - w - hh * 0.35), (tp[0] - w * 0.2, tp[1] + hh * 0.3), tp, 10)
            side_r = _mech_bezier(tp, (tp[0] + w * 0.2, tp[1] + hh * 0.3), (cx + w, b - w - hh * 0.35), (cx + w, b - w), 10)
            arc = [(cx + w * math.cos(math.radians(a)), b - w + w * math.sin(math.radians(a))) for a in range(0, 181, 15)]
            self._mech_poly(c, side_l + side_r + arc, fill=col)
        self._mech_ellipse(c, cx - 2.2, fy - 4, cx + 2.2, fy + 0.5, fill=(80, 110, 220))  # blauer Flammenfuß
        c.circle(cx, fy - 4, 1, fill=(60, 40, 30))
        # daneben: Uhrzeit, Datum, Rest des Tages
        tx = 238
        c.text(tx, 78, time.strftime("%H:%M:%S", now), mf["mono"], (248, 222, 172))
        c.text(tx, 104, f"{WEEKDAY_DE[now.tm_wday]}, {now.tm_mday}. {MONTHS[now.tm_mon - 1]}", f["small"],
               (200, 166, 120))
        left = 86400 - int(day * 86400)
        mins = math.ceil(left / 60)
        txt = f"noch {left} Sek." if left < 60 else (f"noch {mins} Min." if mins < 60 else
                                                     f"noch {mins // 60} Std. {mins % 60} Min.")
        c.text(tx, 124, txt, f["tiny"], (150, 124, 96))
        return self._clock_finish(c)


def _mech_frange(a, b, step):
    """Gleitkomma-Bereich von a bis b (einschließlich b) mit Schritt ±step."""
    step = abs(step) if b >= a else -abs(step)
    out, x = [], a
    while (x < b) if step > 0 else (x > b):
        out.append(x)
        x += step
    out.append(b)
    return out
