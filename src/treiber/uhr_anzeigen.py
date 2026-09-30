"""Zifferblätter Klappzahlenuhr, Nixie-Röhrenuhr, LED-Radiowecker, LED-Matrix, Zählwerk.

Das Unveränderliche wird einmal CLOCK_SS-fach gezeichnet und verkleinert; je Bild werden nur fertige,
zwischengespeicherte Einzelteile (Karten, Röhrenziffern, Segmente, Leuchtpunkte, Rollen) in Displaygröße
aufgesetzt – so bleiben auch die Zifferblätter mit fps 5 schnell.
"""
import math
import random
from PIL import ImageFilter

_disp_cond = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed{}.ttf"
_disp_sans = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"


def _disp_shrink(img, w, h):
    """CLOCK_SS-fach gezeichnetes Bild auf w×h verkleinern (RGBA mit vormultipliziertem Alpha)."""
    if img.mode == "RGBA":
        return img.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
    return img.resize((w, h), Image.LANCZOS)


def _disp_grad(img, box, radius, stops, mask=None):
    """Senkrechter Verlauf in einem abgerundeten Rechteck (vergrößerte Pixel); stops = [(0…1, Farbe), …]."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    col = []
    for i in range(h):
        u = i / max(1, h - 1)
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if u <= b or (b, cb) == stops[-1]:
                col.append(mix(ca, cb, 0 if b == a else min(1, max(0, (u - a) / (b - a)))))
                break
    g = Image.new("RGB", (1, h))
    g.putdata(col)
    g = g.resize((w, h), Image.NEAREST)
    if mask is None:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    img.paste(g, (x0, y0), mask)


def _disp_wood(img, box, radius, base, seed):
    """Holz mit Maserung (vergrößerte Pixel)."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = x1 - x0, y1 - y0
    rnd = random.Random(seed)
    wood = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(wood)
    y = -6
    while y < h + 6:
        amp, per, ph = rnd.uniform(1, 7), rnd.uniform(150, 500), rnd.uniform(0, 6.3)
        col = mix(base, (0, 0, 0) if rnd.random() < 0.65 else (255, 214, 170), rnd.uniform(0.06, 0.28))
        d.line([(x, y + amp * math.sin(x / per * 6.283 + ph)) for x in range(-20, w + 40, 20)],
               fill=col, width=rnd.randint(1, 4))
        y += rnd.randint(3, 8)
    wood = wood.filter(ImageFilter.GaussianBlur(1.3))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    img.paste(wood, (x0, y0), mask)


def _disp_tint(img, color, mask, f=1.0, pos=(0, 0)):
    """Farbe durch eine Maske (L) auf das RGBA-Bild img legen (echtes Überblenden)."""
    if f != 1.0:
        mask = mask.point([int(v * f) for v in range(256)])
    layer = Image.new("RGBA", mask.size, tuple(color[:3]) + (0,))
    layer.putalpha(mask)
    img.alpha_composite(layer, pos)


def _disp_darken(img, f):
    """RGBA-Bild um den Faktor f (0…1) abdunkeln."""
    r, g, b, a = img.split()
    lut = [int(v * f) for v in range(256)]
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


def _disp_engrave(c, x, y, txt, font, dark, light):
    """Gravierter Text (mittig): Lichtkante unten rechts, darüber die dunkle Kerbe."""
    c.text(x + 0.45, y + 0.45, txt, font, light)
    c.text(x, y, txt, font, dark)


def _disp_screw(c, x, y, r, deg):
    """Schlitzschraube."""
    c.circle(x + 0.4, y + 0.6, r + 0.6, fill=(40, 42, 46))
    c.circle(x, y, r, fill=(150, 154, 160), outline=(70, 72, 78), width=0.6)
    c.circle(x - r * 0.25, y - r * 0.25, r * 0.55, fill=(186, 190, 196))
    c.radial(x, y, -r * 0.8, r * 0.8, deg, max(0.8, r * 0.28), (54, 56, 60))


# Schaltbilder der Pixelschriften (1 = Leuchtpunkt an)
_disp_font57 = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}
_disp_font35 = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "A": ["010", "101", "111", "101", "101"], "B": ["110", "101", "110", "101", "110"],
    "D": ["110", "101", "101", "101", "110"], "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"], "G": ["011", "100", "101", "101", "011"],
    "I": ["111", "010", "010", "010", "111"], "J": ["001", "001", "001", "101", "010"],
    "K": ["101", "101", "110", "101", "101"], "L": ["100", "100", "100", "100", "111"],
    "M": ["101", "111", "111", "101", "101"], "N": ["110", "101", "101", "101", "101"],
    "O": ["010", "101", "101", "101", "010"], "P": ["110", "101", "110", "100", "100"],
    "R": ["110", "101", "110", "101", "101"], "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"], "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"], "W": ["101", "101", "111", "111", "101"],
    "Z": ["111", "001", "010", "100", "111"], ".": ["0", "0", "0", "0", "1"], " ": ["00"] * 5,
}
_disp_month3 = ["JAN", "FEB", "MRZ", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEZ"]

# Segmente der 7-Segment-Ziffern
_disp_seg_map = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg",
                 "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def _disp_seg_polys(x, y, w, h, t, gap, skew):
    """Die sieben Segmente a–g als Polygone (Displaykoordinaten), um skew je Pixel Höhe nach rechts geneigt."""
    ht = t / 2

    def hseg(yc):
        x0, x1 = ht + gap, w - ht - gap
        return [(x0, yc), (x0 + ht, yc - ht), (x1 - ht, yc - ht), (x1, yc), (x1 - ht, yc + ht), (x0 + ht, yc + ht)]

    def vseg(xc, y0, y1):
        return [(xc, y0), (xc + ht, y0 + ht), (xc + ht, y1 - ht), (xc, y1), (xc - ht, y1 - ht), (xc - ht, y0 + ht)]

    m = h / 2
    segs = {"a": hseg(ht), "g": hseg(m), "d": hseg(h - ht),
            "f": vseg(ht, ht + gap, m - gap), "b": vseg(w - ht, ht + gap, m - gap),
            "e": vseg(ht, m + gap, h - ht - gap), "c": vseg(w - ht, m + gap, h - ht - gap)}
    return {k: [(x + px + (h - py) * skew, y + py) for px, py in pts] for k, pts in segs.items()}


class DisplayFaces:
    # --- gemeinsame Hilfen ---------------------------------------------------- #
    def _disp_store(self):
        """Zwischenspeicher dieser Zifferblätter (Schriften, Hintergründe, Einzelteile)."""
        if "_disp_mem" not in self.__dict__:
            self._disp_mem = {}
        return self._disp_mem

    def _disp_font(self, path, size, bold=False):
        """Schrift aus path ({} → „-Bold“); fehlt die Datei, DejaVu Sans über load_font."""
        mem, key = self._disp_store(), ("font", path, size, bold)
        if key not in mem:
            p = path.format("-Bold" if bold else "")
            mem[key] = ImageFont.truetype(p, size) if os.path.exists(p) else load_font(size, bold)
        return mem[key]

    def _disp_glyph(self, txt, path, bold, bw, bh, dh, maxw, ref="0123456789"):
        """Zeichen als Maske (L, bw×bh): Ziffernhöhe dh, mittig; breiter als maxw (gemessen an ref) → gestaucht."""
        mem = self._disp_store()
        key = ("glyph", txt, path, bold, bw, bh, dh, maxw, ref)
        if key not in mem:
            x0, y0, x1, y1 = self._disp_font(path, 200, bold).getbbox("0")
            font = self._disp_font(path, max(4, round(200 * dh / (y1 - y0))), bold)
            refw = max(font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in ref)
            fx = min(1.0, maxw / refw)
            tw = max(bw, round(bw / fx))
            m = Image.new("L", (tw, bh), 0)
            ImageDraw.Draw(m).text((tw / 2, (bh + dh) / 2), txt, font=font, fill=255, anchor="ms")
            mem[key] = m.resize((bw, bh), Image.LANCZOS) if tw != bw else m
        return mem[key]

    def _disp_part(self, key, w, h, build):
        """Einzelteil w×h (RGBA, Displaygröße), build(c) zeichnet es CLOCK_SS-fach auf Transparenz."""
        mem = self._disp_store()
        if key not in mem:
            c = _Canvas(Image.new("RGBA", (w * CLOCK_SS, h * CLOCK_SS), (0, 0, 0, 0)))
            build(c)
            mem[key] = _disp_shrink(c.img, w, h)
        return mem[key]

    def _disp_base(self, key, bg, build):
        """Hintergrund (RGBA 320×CLOCK_H) einmal CLOCK_SS-fach zeichnen, verkleinert zwischenspeichern; Kopie."""
        mem = self._disp_store()
        if key not in mem:
            c = _Canvas(Image.new("RGBA", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), tuple(bg) + (255,)))
            build(c)
            mem[key] = _disp_shrink(c.img, WIDTH, CLOCK_H)
        return mem[key].copy()

    def _disp_out(self, img):
        """Displaybild 320×240 (die Fußzeile zeichnet der Aufrufer)."""
        out = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        out.paste(img.convert("RGB"), (0, 0))
        return out

    @staticmethod
    def _disp_step(t, dur):
        """Fortschritt 0…1 einer Bewegung in den ersten dur Sekunden nach dem Sekundenwechsel."""
        return min(1.0, (t - math.floor(t) + 0.2) / dur)

    # --- Klappzahlenuhr ------------------------------------------------------- #
    # Kartenart: Breite, Höhe, Ziffernhöhe, Ziffernbreite höchstens, Eckradius
    _disp_flip_kinds = {"big": (62, 110, 80, 50, 6), "sec": (26, 36, 24, 19, 3), "date": (20, 30, 19, 15, 3)}

    @staticmethod
    def _disp_flip_slots():
        """(Kartenart, x, y) aller Karten: HH MM, Sekunden, Wochentag Tag Monat."""
        slots = [("big", x, 8) for x in (17, 84, 174, 241)]
        slots += [("sec", 132, 128), ("sec", 161, 128)]
        x = 76
        for n in (2, 2, 3):
            for _ in range(n):
                slots.append(("date", x, 175))
                x += 22
            x += 8
        return slots

    @staticmethod
    def _disp_flip_text(now):
        return (f"{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}" + WEEKDAY_2[now.tm_wday]
                + f"{now.tm_mday:02d}" + MONTH_3[now.tm_mon - 1])

    def _disp_flip_card(self, kind, ch, ink):
        """Karte mit Zeichen ch: (ganz, obere Hälfte, untere Hälfte) als RGBA."""
        mem, key = self._disp_store(), ("flip", kind, ch, ink)
        if key not in mem:
            w, h, dh, dw, r = self._disp_flip_kinds[kind]
            s = CLOCK_SS

            def build(c):
                _disp_grad(c.img, (0, 0, w * s, h * s), r * s, [(0, (60, 60, 65)), (0.5, (40, 40, 44)),
                                                               (0.5, (34, 34, 38)), (1, (22, 22, 25))])
                c.rect(r * 0.6, 0, w - r * 0.6, 0.4, fill=(84, 84, 90))           # Lichtkante oben
                glyph = self._disp_glyph(ch, _disp_cond, True, w * s, h * s, dh * s, dw * s)
                _disp_tint(c.img, ink, glyph)
                c.rect(0, h / 2 - 0.7, w, h / 2 + 0.5, fill=(6, 6, 8))           # Trennfuge
                c.rect(0, h / 2 + 0.5, w, h / 2 + 0.9, fill=(58, 58, 62))

            full = self._disp_part(key + ("full",), w, h, build)
            mem[key] = (full, full.crop((0, 0, w, h // 2)), full.crop((0, h // 2, w, h)))
        return mem[key]

    def _disp_flip_draw(self, img, kind, x, y, old, new, p, ink):
        """Karte zeichnen; wechselt das Zeichen, klappt die obere Hälfte um (p = 0…1)."""
        full, top, bot = self._disp_flip_card(kind, new, ink)
        if old == new or p >= 1:
            img.alpha_composite(full, (x, y))
            return
        _, otop, obot = self._disp_flip_card(kind, old, ink)
        w, hh = top.size
        img.alpha_composite(top, (x, y))
        if p < 0.5:                                        # alte obere Hälfte fällt nach vorn
            k = math.cos(p * math.pi)
            img.alpha_composite(_disp_darken(obot, 1 - 0.3 * (1 - k)), (x, y + hh))
            fh = max(1, round(hh * k))
            fw = w + 2 * round(w * 0.02 * math.sin(p * math.pi))
            flap = _disp_darken(otop.resize((fw, fh), Image.BILINEAR), 1 - 0.4 * (1 - k))
            img.alpha_composite(flap, (x - (fw - w) // 2, y + hh - fh))
        else:                                              # neue untere Hälfte klappt herunter
            k = -math.cos(p * math.pi)
            img.alpha_composite(_disp_darken(obot, 1 - 0.3 * (1 - k)), (x, y + hh))
            fh = max(1, round(hh * k))
            fw = w + 2 * round(w * 0.02 * math.sin(p * math.pi))
            flap = _disp_darken(bot.resize((fw, fh), Image.BILINEAR), 1 - 0.5 * (1 - k))
            img.alpha_composite(flap, (x - (fw - w) // 2, y + hh))

    def _disp_flip_static(self, c):
        s = CLOCK_SS
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (30, 30, 34)), (1, (12, 12, 14))])
        shadow = Image.new("L", c.img.size, 0)
        sd = ImageDraw.Draw(shadow)
        for kind, x, y in self._disp_flip_slots():
            w, h, _dh, _dw, r = self._disp_flip_kinds[kind]
            sd.rounded_rectangle([(x - 1) * s, (y + 2) * s, (x + w + 1) * s, (y + h + 4) * s], r * s, fill=190)
        shadow = shadow.filter(ImageFilter.GaussianBlur(4 * s))
        _disp_tint(c.img, (0, 0, 0), shadow)
        for kind, x, y in self._disp_flip_slots():
            w, h, _dh, _dw, r = self._disp_flip_kinds[kind]
            for k, col in ((2.4, (18, 18, 20)), (1.2, (28, 28, 31))):     # weitere Blätter darunter
                c.d.rounded_rectangle([(x + k) * s, (y + h - 4) * s, (x + w - k) * s, (y + h + k) * s],
                                      r * s, fill=col)
            hy, hw, hl = y + h / 2, (3 if kind == "big" else 1.6), (8 if kind == "big" else 4)
            for hx in (x - hw, x + w):                                     # Scharniere
                c.rect(hx, hy - hl / 2, hx + hw, hy + hl / 2, fill=(92, 92, 98), outline=(18, 18, 20), width=0.5)
                c.rect(hx, hy - 0.4, hx + hw, hy + 0.4, fill=(40, 40, 44))
        for cy in (46, 80):                                                # Doppelpunkt
            c.d.rounded_rectangle([(160 - 4.5) * s, (cy - 4.5) * s, (160 + 4.5) * s, (cy + 4.5) * s],
                                  2 * s, fill=(62, 62, 68))
            c.d.rounded_rectangle([(160 - 3.5) * s, (cy - 3.5) * s, (160 + 3.5) * s, (cy + 1) * s],
                                  1.5 * s, fill=(84, 84, 92))

    @clock_face("flip", fps=5)
    def face_flip(self, profile):
        t = self._clock_now()
        now, prev = time.localtime(t), time.localtime(math.floor(t) - 1)
        p = self._disp_step(t, 0.5)
        acc = PROFILE_COLOR.get(profile, self.FG)
        img = self._disp_base("flip", (20, 20, 24), self._disp_flip_static)
        white, sec_ink = (238, 236, 228), mix(acc, (255, 255, 255), 0.45)
        for (kind, x, y), a, b in zip(self._disp_flip_slots(), self._disp_flip_text(prev), self._disp_flip_text(now)):
            self._disp_flip_draw(img, kind, x, y, a, b, p, sec_ink if kind == "sec" else white)
        d = ImageDraw.Draw(img)
        small, big = self._disp_font(_disp_cond, 10, True), self._disp_font(_disp_cond, 17, True)
        d.text((88, 139), "KW", font=small, fill=(120, 124, 134), anchor="mm")
        d.text((88, 155), time.strftime("%V", now), font=big, fill=(200, 202, 208), anchor="mm")
        d.text((232, 139), "JAHR", font=small, fill=(120, 124, 134), anchor="mm")
        d.text((232, 155), str(now.tm_year), font=big, fill=(200, 202, 208), anchor="mm")
        return self._disp_out(img)

    # --- Nixie-Röhrenuhr ------------------------------------------------------ #
    _disp_nixie_x = (10, 55, 117, 162, 224, 269)      # linke Kante der Röhren (40 breit)
    _disp_nixie_colon = (106, 213)

    def _disp_nixie_mask(self, ch):
        """Ziffernmaske einer Kathode (CLOCK_SS-fach, 40×80 Displaypixel)."""
        s = CLOCK_SS
        return self._disp_glyph(ch, _disp_sans, False, 40 * s, 80 * s, 58 * s, 25 * s)

    def _disp_nixie_lit(self, ch):
        """Leuchtende Ziffer mit Glühen (RGBA 40×80)."""
        def build(c):
            m = self._disp_nixie_mask(ch)
            wide = m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10 * CLOCK_SS))
            near = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2.5 * CLOCK_SS))
            _disp_tint(c.img, (255, 70, 0), wide, 0.55)
            _disp_tint(c.img, (255, 110, 20), near, 0.9)
            _disp_tint(c.img, (255, 150, 50), m.filter(ImageFilter.MaxFilter(3)))
            _disp_tint(c.img, (255, 222, 170), m.filter(ImageFilter.MinFilter(3)), 0.85)
        return self._disp_part(("nixie_lit", ch), 40, 80, build)

    @staticmethod
    def _disp_nixie_shape(d, x, s, fill=None, outline=None, width=0, inset=0):
        """Umriss des Glaskolbens (runde Kuppe) auf ImageDraw d."""
        i = inset
        d.rounded_rectangle([(x + i) * s, (8 + i) * s, (x + 40 - i) * s, (166 - i) * s], (20 - i) * s,
                            fill=fill, outline=outline, width=width)

    def _disp_nixie_static(self, c, acc):
        s = CLOCK_SS
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (24, 19, 17)), (0.8, (12, 10, 10)), (1, (8, 7, 7))])
        # Holzsockel: Oberseite und Vorderkante
        _disp_wood(c.img, (0, 172 * s, WIDTH * s, 184 * s), 0, (96, 58, 32), 11)
        _disp_wood(c.img, (0, 184 * s, WIDTH * s, CLOCK_H * s), 0, (62, 36, 20), 12)
        c.rect(0, 183.6, WIDTH, 184.4, fill=(130, 86, 52))
        c.rect(0, 172, WIDTH, 172.5, fill=(40, 26, 16))
        glow = Image.new("L", c.img.size, 0)                  # Widerschein der Röhren auf dem Holz
        gd = ImageDraw.Draw(glow)
        for x in self._disp_nixie_x:
            gd.ellipse([(x + 2) * s, 170 * s, (x + 38) * s, 186 * s], fill=150)
        _disp_tint(c.img, (255, 90, 20), glow.filter(ImageFilter.GaussianBlur(5 * s)), 0.45)
        # Messingschild und Betriebsleuchte
        _disp_grad(c.img, (116 * s, 190 * s, 204 * s, 206 * s), 2 * s,
                   [(0, (214, 178, 102)), (0.5, (176, 138, 64)), (1, (120, 88, 38))])
        for sx in (120, 200):
            c.circle(sx, 198, 1.3, fill=(92, 66, 28))
        f = self._disp_font(_disp_sans, 8 * s, True)
        _disp_engrave(c, 34, 198, "G19s", f, (200, 168, 110), (26, 14, 8))
        c.circle(292, 198, 3.2, fill=(20, 14, 10))
        c.circle(292, 198, 2.2, fill=acc)
        c.circle(291.4, 197.4, 0.8, fill=mix(acc, (255, 255, 255), 0.6))
        for x in self._disp_nixie_x:
            # Fassung mit Stiften
            c.d.rounded_rectangle([(x + 5) * s, 169 * s, (x + 35) * s, 180 * s], 3 * s, fill=(16, 16, 18))
            c.rect(x + 7, 169.5, x + 33, 170.4, fill=(58, 58, 62))
            for k in range(7):
                px = x + 9 + k * 3.7
                c.rect(px - 0.35, 164, px + 0.35, 170, fill=(170, 166, 150))
            # Kolben innen, Glimmerscheiben, Haltedrähte
            self._disp_nixie_shape(c.d, x, s, fill=(20, 16, 15))
            c.rect(x + 6, 160, x + 34, 166, fill=(34, 30, 28))                   # Quetschfuß
            for py in (38, 136):
                c.d.rounded_rectangle([(x + 4) * s, py * s, (x + 36) * s, (py + 3) * s], 1 * s, fill=(70, 66, 60))
            for px in (x + 7, x + 33):
                c.rect(px - 0.4, 41, px + 0.4, 160, fill=(80, 76, 70))
            unlit = Image.new("L", (40 * s, 80 * s), 0)
            for ch in "0123456789":
                unlit = Image.fromarray(np.maximum(np.asarray(unlit), np.asarray(self._disp_nixie_mask(ch))))
            _disp_tint(c.img, (84, 72, 62), unlit, 0.7, (x * s, 48 * s))
        # Neon-Doppelpunkte
        dots = Image.new("L", c.img.size, 0)
        dd = ImageDraw.Draw(dots)
        for cx in self._disp_nixie_colon:
            for cy in (72, 104):
                c.d.rounded_rectangle([(cx - 4) * s, (cy - 7) * s, (cx + 4) * s, (cy + 7) * s], 4 * s,
                                      fill=(26, 20, 18), outline=(92, 96, 104), width=2)
                dd.ellipse([(cx - 2.2) * s, (cy - 2.2) * s, (cx + 2.2) * s, (cy + 2.2) * s], fill=255)
                c.rect(cx - 0.3, cy + 7, cx + 0.3, 169, fill=(120, 116, 106))
        _disp_tint(c.img, (255, 80, 10), dots.filter(ImageFilter.GaussianBlur(4 * s)), 0.9)
        _disp_tint(c.img, (255, 150, 60), dots)
        _disp_tint(c.img, (255, 220, 170), dots.filter(ImageFilter.MinFilter(5)), 0.8)

    def _disp_nixie_front(self):
        """Vorderes Gitter und Glasspiegelungen (RGBA über dem ganzen Bild)."""
        def build(c):
            s = CLOCK_SS
            mesh = Image.new("L", c.img.size, 0)
            md = ImageDraw.Draw(mesh)
            for k in range(-80, 330, 3):                        # Rautengitter
                md.line([(k * s, 30 * s), ((k + 110) * s, 140 * s)], fill=255, width=2)
                md.line([((k + 110) * s, 30 * s), (k * s, 140 * s)], fill=255, width=2)
            clip = Image.new("L", c.img.size, 0)
            cd = ImageDraw.Draw(clip)
            for x in self._disp_nixie_x:
                cd.rectangle([(x + 5) * s, 41 * s, (x + 35) * s, 136 * s], fill=255)
            _disp_tint(c.img, (60, 56, 52), Image.composite(mesh, clip, clip), 0.5)
            for x in self._disp_nixie_x:
                c.rect(x + 5, 41, x + 35, 41.6, fill=(84, 80, 74, 255))
                glass = Image.new("L", c.img.size, 0)
                gd = ImageDraw.Draw(glass)
                self._disp_nixie_shape(gd, x, s, outline=255, width=3)
                _disp_tint(c.img, (190, 200, 215), glass, 0.35)
                hi = Image.new("L", c.img.size, 0)
                hd = ImageDraw.Draw(hi)
                hd.rounded_rectangle([(x + 5) * s, 24 * s, (x + 9) * s, 150 * s], 2 * s, fill=150)
                hd.rounded_rectangle([(x + 33) * s, 30 * s, (x + 34.2) * s, 146 * s], 1 * s, fill=70)
                hd.arc([(x + 5) * s, 11 * s, (x + 35) * s, 41 * s], 200, 290, fill=200, width=int(1.6 * s))
                _disp_tint(c.img, (255, 255, 255), hi.filter(ImageFilter.GaussianBlur(0.8 * s)), 0.35)
                getter = Image.new("L", c.img.size, 0)          # Getterspiegel in der Kuppe
                ImageDraw.Draw(getter).ellipse([(x + 9) * s, 10 * s, (x + 31) * s, 22 * s], fill=255)
                _disp_tint(c.img, (150, 150, 158), getter.filter(ImageFilter.GaussianBlur(2 * s)), 0.45)
        return self._disp_part("nixie_front", WIDTH, CLOCK_H, build)

    @clock_face("nixie", fps=1)
    def face_nixie(self, profile):
        now = time.localtime(self._clock_now())
        acc = PROFILE_COLOR.get(profile, self.FG)
        img = self._disp_base(("nixie", acc), (12, 10, 10), lambda c: self._disp_nixie_static(c, acc))
        for x, ch in zip(self._disp_nixie_x, f"{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}"):
            img.alpha_composite(self._disp_nixie_lit(ch), (x, 48))
        img.alpha_composite(self._disp_nixie_front())
        d = ImageDraw.Draw(img)
        txt = f"{WEEKDAY_2[now.tm_wday]} {now.tm_mday:02d}.{now.tm_mon:02d}.{now.tm_year}"
        f = self._disp_font(_disp_cond, 9, True)
        d.text((160.5, 198.5), txt, font=f, fill=(236, 206, 140), anchor="mm")
        d.text((160, 198), txt, font=f, fill=(70, 46, 16), anchor="mm")
        return self._disp_out(img)

    # --- LED-Radiowecker ------------------------------------------------------ #
    # Ziffernart: Breite, Höhe, Segmentdicke, Fuge
    _disp_seg_kinds = {"big": (40, 84, 9, 1.3), "small": (13, 24, 3.4, 0.6)}
    _disp_seg_skew = 0.1
    _disp_seg_big_x = (26, 74, 134, 182)
    _disp_seg_small_x = (196, 213)

    def _disp_seg_sprite(self, kind, what, color):
        """Leuchtende Segmente (Ziffer oder „:“) mit Glühen, RGBA; linke obere Ecke der Ziffer bei (8, 8)."""
        w, h, t, gap = self._disp_seg_kinds[kind]
        pad, sk = 8, self._disp_seg_skew
        W, H = int(w + h * sk + 2 * pad), int(h + 2 * pad)

        def build(c):
            s = CLOCK_SS
            m = Image.new("L", c.img.size, 0)
            md = ImageDraw.Draw(m)
            if what == ":":
                for fy in (0.3, 0.7):
                    yc, xc = h * fy, w / 2 + h * (1 - fy) * sk
                    md.polygon([((pad + xc + dx - dy * sk) * s, (pad + yc + dy) * s)
                                for dx, dy in ((-t / 2, -t / 2), (t / 2, -t / 2), (t / 2, t / 2), (-t / 2, t / 2))],
                               fill=255)
            else:
                polys = _disp_seg_polys(pad, pad, w, h, t, gap, sk)
                for seg in _disp_seg_map[what]:
                    md.polygon([(px * s, py * s) for px, py in polys[seg]], fill=255)
            _disp_tint(c.img, color, m.filter(ImageFilter.GaussianBlur(t * 0.9 * s)), 0.7)
            _disp_tint(c.img, color, m)
            _disp_tint(c.img, mix(color, (255, 255, 255), 0.45),
                       m.filter(ImageFilter.MinFilter(int(t * 0.45 * s) * 2 + 1)).filter(ImageFilter.GaussianBlur(s)),
                       0.7)
        return self._disp_part(("seg", kind, what, color), W, H, build)

    def _disp_seg_static(self, c, color):
        s, sk = CLOCK_SS, self._disp_seg_skew
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (16, 14, 14)), (1, (8, 8, 9))])
        _disp_wood(c.img, (4 * s, 4 * s, 316 * s, 210 * s), 14 * s, (70, 40, 22), 21)
        c.d.rounded_rectangle([4 * s, 4 * s, 316 * s, 210 * s], 14 * s, outline=(30, 18, 10), width=s)
        _disp_grad(c.img, (12 * s, 12 * s, 308 * s, 202 * s), 8 * s, [(0, (34, 32, 32)), (1, (18, 17, 17))])
        c.d.rounded_rectangle([12 * s, 12 * s, 308 * s, 202 * s], 8 * s, outline=(8, 8, 8), width=s)
        # Rauchglasfenster
        c.d.rounded_rectangle([18 * s, 18 * s, 238 * s, 152 * s], 7 * s, fill=(120, 120, 124))
        _disp_grad(c.img, (19 * s, 19 * s, 237 * s, 151 * s), 6 * s, [(0, (22, 12, 12)), (1, (12, 8, 8))])
        shimmer = mix(color, (14, 9, 9), 0.9)
        for kind, xs, y in (("big", self._disp_seg_big_x, 30), ("small", self._disp_seg_small_x, 122)):
            w, h, t, gap = self._disp_seg_kinds[kind]
            for x in xs:
                for pts in _disp_seg_polys(x, y, w, h, t, gap, sk).values():
                    c.d.polygon([(px * s, py * s) for px, py in pts], fill=shimmer)
        w, h, t, _g = self._disp_seg_kinds["big"]
        for fy in (0.3, 0.7):
            yc, xc = 30 + h * fy, 124 + h * (1 - fy) * sk
            c.d.polygon([((xc + dx - dy * sk) * s, (yc + dy) * s)
                         for dx, dy in ((-t / 2, -t / 2), (t / 2, -t / 2), (t / 2, t / 2), (-t / 2, t / 2))],
                        fill=shimmer)
        # Glockensymbol und Aufschrift (unbeleuchtet)
        self._disp_seg_bell(c, 32, 134, shimmer)
        c.d.text((42 * s, 134 * s), "ALARM", font=self._disp_font(_disp_cond, 11 * s, True), fill=shimmer,
                 anchor="lm")
        # Senderskala
        _disp_grad(c.img, (18 * s, 160 * s, 238 * s, 196 * s), 5 * s, [(0, (40, 34, 26)), (1, (26, 22, 18))])
        c.d.rounded_rectangle([18 * s, 160 * s, 238 * s, 196 * s], 5 * s, outline=(90, 90, 94), width=s)
        tiny = self._disp_font(_disp_cond, 8 * s, True)
        ink = (214, 196, 150)
        c.d.text((24 * s, 184 * s), "UKW", font=tiny, fill=ink, anchor="lm")
        c.d.text((232 * s, 184 * s), "MHz", font=tiny, fill=ink, anchor="rm")
        x0, x1 = 50, 206
        for k in range(88 * 2, 108 * 2 + 1):
            x = x0 + (k / 2 - 88) / 20 * (x1 - x0)
            major = k % 8 == 0
            c.rect(x - 0.3, 176 - (5 if major else 2.5), x + 0.3, 176, fill=ink)
            if major:
                c.text(x, 167.5, str(k // 2), tiny, ink)
        c.rect(x0, 176, x1, 176.6, fill=ink)
        nx = x0 + (101.3 - 88) / 20 * (x1 - x0)
        c.rect(nx - 0.7, 163, nx + 0.7, 193, fill=(230, 60, 30))
        c.d.text(((x0 + x1) / 2 * s, 186 * s), "G19s", font=tiny, fill=(150, 136, 104), anchor="mm")
        # Lautsprechergitter und Knöpfe
        c.d.rounded_rectangle([246 * s, 18 * s, 302 * s, 162 * s], 6 * s, fill=(26, 26, 28), outline=(70, 70, 74),
                              width=s)
        for j in range(24):
            for i in range(8):
                x, y = 252 + i * 6.3 + (3.1 if j % 2 else 0), 24 + j * 5.8
                if x < 298:
                    c.circle(x, y, 1.8, fill=(6, 6, 7))
                    c.circle(x + 0.4, y + 0.5, 1.8, outline=(52, 52, 56), width=0.4)
        for kx in (259, 289):
            c.circle(kx, 182, 11.5, fill=(10, 10, 10))
            c.circle(kx, 182, 10, fill=(58, 58, 62))
            for k in range(24):
                c.radial(kx, 182, 8.2, 10, k * 15, 0.7, (34, 34, 36))
            c.circle(kx, 182, 7.8, fill=(76, 76, 82))
            c.circle(kx - 1.5, 180.5, 4, fill=(96, 96, 102))
            c.radial(kx, 182, 3, 7, 40 if kx < 270 else -60, 1.2, (220, 220, 225))

    @staticmethod
    def _disp_seg_bell(c, x, y, col):
        """Kleine Weckerglocke."""
        c.d.chord([(x - 4.5) * c.s, (y - 5.5) * c.s, (x + 4.5) * c.s, (y + 5) * c.s], 180, 360, fill=col)
        c.rect(x - 4.5, y - 0.3, x + 4.5, y + 3, fill=col)
        c.rect(x - 5.5, y + 3, x + 5.5, y + 4.2, fill=col)
        c.circle(x, y + 5.2, 1.3, fill=col)

    def _disp_seg_glass(self):
        """Spiegelung auf dem Rauchglas (RGBA)."""
        def build(c):
            s = CLOCK_SS
            m = Image.new("L", c.img.size, 0)
            md = ImageDraw.Draw(m)
            md.polygon([(70 * s, 19 * s), (130 * s, 19 * s), (60 * s, 151 * s), (0, 151 * s)], fill=16)
            md.polygon([(142 * s, 19 * s), (156 * s, 19 * s), (86 * s, 151 * s), (72 * s, 151 * s)], fill=10)
            clip = Image.new("L", c.img.size, 0)
            ImageDraw.Draw(clip).rounded_rectangle([19 * s, 19 * s, 237 * s, 151 * s], 6 * s, fill=255)
            _disp_tint(c.img, (255, 255, 255), Image.composite(m, clip, clip))
            c.rect(24, 19.4, 232, 20.2, fill=(255, 255, 255, 40))
        return self._disp_part("seg_glass", WIDTH, CLOCK_H, build)

    @clock_face("seg7", fps=1)
    def face_seg7(self, profile):
        now = time.localtime(self._clock_now())
        color = self._ccolor(self._copt("seg7")["color"], profile, (255, 40, 30))
        img = self._disp_base(("seg7", color), (10, 9, 9), lambda c: self._disp_seg_static(c, color))
        for x, ch in zip(self._disp_seg_big_x, f"{now.tm_hour:02d}{now.tm_min:02d}"):
            img.alpha_composite(self._disp_seg_sprite("big", ch, color), (x - 8, 30 - 8))
        if now.tm_sec % 2 == 0:
            w, h, t, _g = self._disp_seg_kinds["big"]
            img.alpha_composite(self._disp_seg_sprite("big", ":", color), (round(124 - w / 2) - 8, 30 - 8))
        for x, ch in zip(self._disp_seg_small_x, f"{now.tm_sec:02d}"):
            img.alpha_composite(self._disp_seg_sprite("small", ch, color), (x - 8, 122 - 8))
        alarm = (self.settings or {}).get("alarm_clock") or {}
        if alarm.get("enabled"):
            def build(c):
                s = CLOCK_SS
                m = Image.new("L", c.img.size, 0)
                mc = _Canvas(m)
                self._disp_seg_bell(mc, 10, 12, 255)
                mc.d.text((20 * s, 12 * s), "ALARM  " + str(alarm.get("time") or "07:00"),
                          font=self._disp_font(_disp_cond, 11 * s, True), fill=255, anchor="lm")
                _disp_tint(c.img, color, m.filter(ImageFilter.GaussianBlur(2 * s)), 0.6)
                _disp_tint(c.img, mix(color, (255, 255, 255), 0.15), m)
            img.alpha_composite(self._disp_part(("seg_alarm", str(alarm.get("time")), color), 110, 24, build),
                                (22, 122))
        img.alpha_composite(self._disp_seg_glass())
        return self._disp_out(img)

    # --- LED-Matrix ----------------------------------------------------------- #
    _disp_mx_big = (17, 16, 11, 27, 9)          # erste Mitte x, y, Abstand, Spalten, Zeilen
    _disp_mx_small = (12, 122, 5, 60, 7)
    _disp_mx_sec_y = 170

    def _disp_mx_led(self, big, color, hot=False):
        """Leuchtpunkt mit Glühen (RGBA, Mitte im Bildmittelpunkt)."""
        size, r = (22, 4.3) if big else (10, 2.0)

        def build(c):
            s, m = CLOCK_SS, size / 2
            halo = Image.new("L", c.img.size, 0)
            ImageDraw.Draw(halo).ellipse([(m - r * 1.3) * s, (m - r * 1.3) * s, (m + r * 1.3) * s,
                                          (m + r * 1.3) * s], fill=255)
            _disp_tint(c.img, color, halo.filter(ImageFilter.GaussianBlur(r * 0.8 * s)), 0.55)
            c.circle(m, m, r, fill=mix(color, (255, 255, 255), 0.5) if hot else color)
            c.circle(m - r * 0.25, m - r * 0.25, r * 0.4, fill=mix(color, (255, 255, 255), 0.55 if not hot else 0.85))
        return self._disp_part(("mx_led", big, color, hot), size, size, build)

    def _disp_mx_static(self, c, color):
        s = CLOCK_SS
        off = mix(color, (0, 0, 0), 0.86)
        rim = mix(off, (60, 60, 64), 0.5)
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (26, 26, 28)), (1, (14, 14, 16))])
        c.d.rounded_rectangle([3 * s, 3 * s, 317 * s, 211 * s], 6 * s, fill=(10, 10, 11), outline=(80, 82, 88),
                              width=2 * s)
        for sx, sy in ((9, 9), (311, 9), (9, 205), (311, 205)):
            _disp_screw(c, sx, sy, 2.2, 45)
        panels = []
        x0, y0, p, nc, nr = self._disp_mx_big
        panels.append((x0, y0, p, nc, nr, 4.3))
        x0, y0, p, nc, nr = self._disp_mx_small
        panels.append((x0, y0, p, nc, nr, 2.0))
        panels.append((12, self._disp_mx_sec_y, 5, 60, 1, 2.0))
        for x0, y0, p, nc, nr, r in panels:
            c.d.rounded_rectangle([(x0 - p / 2 - 1) * s, (y0 - p / 2 - 1) * s, (x0 + (nc - 0.5) * p + 1) * s,
                                   (y0 + (nr - 0.5) * p + 1) * s], 2 * s, fill=(4, 4, 5), outline=(34, 34, 38),
                                  width=s)
            for j in range(nr):
                for i in range(nc):
                    x, y = x0 + i * p, y0 + j * p
                    c.circle(x, y, r, fill=off, outline=rim, width=0.4)
        tiny = self._disp_font(_disp_cond, 8 * s, True)
        silk = (150, 152, 158)
        for k in (0, 15, 30, 45):
            c.d.text(((12 + k * 5) * s, 181 * s), str(k), font=tiny, fill=silk, anchor="mm")
            c.rect(12 + k * 5 - 0.3, 175, 12 + k * 5 + 0.3, 177, fill=silk)
        c.d.text(((12 + 59 * 5) * s, 181 * s), "59", font=tiny, fill=silk, anchor="mm")
        c.d.text((12 * s, 198 * s), "G19s", font=tiny, fill=silk, anchor="lm")
        c.d.text((308 * s, 198 * s), "LED 27×9 · 60×7 · 60", font=tiny, fill=(96, 98, 104), anchor="rm")

    def _disp_mx_text(self, txt, font):
        """Punkte (Spalte, Zeile) eines Textes in einer Pixelschrift und seine Breite in Spalten."""
        pts, col = [], 0
        for ch in txt:
            rows = font.get(ch, font.get(" "))
            for j, row in enumerate(rows):
                for i, v in enumerate(row):
                    if v == "1":
                        pts.append((col + i, j))
            col += len(rows[0]) + 1
        return pts, col - 1

    @clock_face("matrix", fps=1)
    def face_matrix(self, profile):
        now = time.localtime(self._clock_now())
        color = self._ccolor(self._copt("matrix")["color"], profile)
        img = self._disp_base(("matrix", color), (14, 14, 16), lambda c: self._disp_mx_static(c, color))
        big, small = self._disp_mx_led(True, color), self._disp_mx_led(False, color)
        x0, y0, p, _nc, _nr = self._disp_mx_big
        pts = []
        for ch, col in zip(f"{now.tm_hour:02d}{now.tm_min:02d}", (1, 7, 15, 21)):
            pts += [(col + i, 1 + j) for i, j in self._disp_mx_text(ch, _disp_font57)[0]]
        if now.tm_sec % 2 == 0:
            pts += [(13, 3), (13, 5)]
        for i, j in pts:
            img.alpha_composite(big, (x0 + i * p - 11, y0 + j * p - 11))
        x0, y0, p, nc, _nr = self._disp_mx_small
        txt = f"{WEEKDAY_2[now.tm_wday]} {now.tm_mday:02d} {_disp_month3[now.tm_mon - 1]} {now.tm_year}"
        pts, width = self._disp_mx_text(txt, _disp_font35)
        off = (nc - width) // 2
        for i, j in pts:
            img.alpha_composite(small, (x0 + (off + i) * p - 5, y0 + (1 + j) * p - 5))
        hot = self._disp_mx_led(False, color, hot=True)
        for i in range(now.tm_sec + 1):
            img.alpha_composite(hot if i == now.tm_sec else small, (12 + i * 5 - 5, self._disp_mx_sec_y - 5))
        return self._disp_out(img)

    # --- Zählwerk ------------------------------------------------------------- #
    # Rollenart: Breite, Fensterhöhe, Ziffernabstand, Ziffernhöhe
    _disp_roll_kinds = {"big": (34, 60, 46, 32), "small": (20, 32, 25, 17)}
    _disp_cnt_groups = (37, 125, 213)            # linke Kante der Rollenpaare (Stunden, Minuten, Sekunden)
    _disp_cnt_small = ((88, 3), (212, 2))        # zweites Zählwerk: (x, Rollen) für TAG und KW

    def _disp_roll_cell(self, kind, ch, red):
        w, _wh, pitch, dh = self._disp_roll_kinds[kind]
        bg = (150, 24, 20) if red else (18, 18, 19)

        def build(c):
            s = CLOCK_SS
            c.rect(0, 0, w, pitch, fill=bg)
            _disp_tint(c.img, (240, 238, 230), self._disp_glyph(ch, _disp_cond, True, w * s, pitch * s, dh * s,
                                                                 w * 0.66 * s))
        return self._disp_part(("roll", kind, ch, red), w, pitch, build)

    def _disp_roll_shade(self, kind):
        """Wölbung der Rolle: oben und unten dunkler, Glanzstreifen über der Mitte (RGBA)."""
        mem, key = self._disp_store(), ("roll_shade", kind)
        if key not in mem:
            w, wh, _p, _dh = self._disp_roll_kinds[kind]
            shade = Image.new("RGBA", (w, wh), (0, 0, 0, 0))
            for y in range(wh):
                u = (y + 0.5) / wh * 2 - 1
                dark = int(255 * min(1, 0.95 * abs(u) ** 2.2))
                shine = int(60 * math.exp(-((u + 0.38) / 0.16) ** 2))
                for x in range(w):
                    edge = 1 - 0.35 * (abs((x + 0.5) / w * 2 - 1) ** 6)
                    if shine > dark:
                        shade.putpixel((x, y), (255, 255, 255, int(shine * edge)))
                    else:
                        shade.putpixel((x, y), (0, 0, 0, min(255, dark + int(70 * (1 - edge)))))
            mem[key] = shade
        return mem[key]

    def _disp_roll(self, img, x, y, kind, old, new, mod, p, red=False):
        """Zahlenrolle im Fenster ab (x, y); wechselt die Ziffer, rollt sie von unten nach (p = 0…1)."""
        w, wh, pitch, _dh = self._disp_roll_kinds[kind]
        a, b = int(old), int(new)
        if a == b or p >= 1:
            seq, pos = [(b - 1) % mod, b, (b + 1) % mod], 1.0
        else:
            e = p * p * (3 - 2 * p)
            seq, pos = [(a - 1) % mod, a, b, (b + 1) % mod], 1 + e
        win = Image.new("RGBA", (w, wh))
        for k, v in enumerate(seq):
            top = round(wh / 2 + (k - pos) * pitch - pitch / 2)
            if -pitch < top < wh:
                win.paste(self._disp_roll_cell(kind, str(v), red), (0, top))
        win.alpha_composite(self._disp_roll_shade(kind))
        img.paste(win, (x, y))

    def _disp_cnt_window(self, c, x0, y0, x1, y1):
        """Vertieftes Fenster in der Platte."""
        s = CLOCK_SS
        c.d.rounded_rectangle([(x0 - 3) * s, (y0 - 3) * s, (x1 + 3) * s, (y1 + 3) * s], 4 * s, fill=(70, 72, 76))
        c.d.rounded_rectangle([(x0 - 2) * s, (y0 - 2) * s, (x1 + 3) * s, (y1 + 3) * s], 3.5 * s, fill=(196, 200, 206))
        c.d.rounded_rectangle([(x0 - 2) * s, (y0 - 2) * s, (x1 + 2) * s, (y1 + 2) * s], 3 * s, fill=(46, 48, 52))
        c.rect(x0, y0, x1, y1, fill=(6, 6, 6))

    def _disp_cnt_static(self, c, acc):
        s = CLOCK_SS
        _disp_grad(c.img, (0, 0, WIDTH * s, CLOCK_H * s), 0, [(0, (22, 22, 24)), (1, (12, 12, 13))])
        # gebürstete Stahlplatte
        plate = Image.new("RGB", ((WIDTH - 8) * s, (CLOCK_H - 8) * s), (132, 136, 142))
        pd = ImageDraw.Draw(plate)
        rnd = random.Random(7)
        for y in range(plate.size[1]):
            v = rnd.randint(-10, 10)
            pd.line([(0, y), (plate.size[0], y)], fill=(132 + v, 136 + v, 142 + v))
        plate = Image.composite(Image.new("RGB", plate.size, (0, 0, 0)), plate,     # unten etwas dunkler
                                Image.linear_gradient("L").resize(plate.size).point(lambda v: v // 5))
        mask = Image.new("L", plate.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, plate.size[0] - 1, plate.size[1] - 1], 10 * s, fill=255)
        c.d.rounded_rectangle([3 * s, 5 * s, 317 * s, (CLOCK_H - 2) * s], 11 * s, fill=(6, 6, 7))
        c.img.paste(plate, (4 * s, 4 * s), mask)
        c.d.rounded_rectangle([4 * s, 4 * s, (WIDTH - 4) * s, (CLOCK_H - 4) * s], 10 * s, outline=(190, 194, 200),
                              width=s)
        rnd = random.Random(3)
        for sx, sy in ((14, 14), (306, 14), (14, 200), (306, 200)):
            _disp_screw(c, sx, sy, 4.2, rnd.uniform(0, 180))
        dark, light = (36, 38, 42), (190, 194, 200)
        lab = self._disp_font(_disp_cond, 9 * s, True)
        # Hauptzählwerk
        for g, (x, name) in enumerate(zip(self._disp_cnt_groups, ("STUNDEN", "MINUTEN", "SEKUNDEN"))):
            _disp_engrave(c, x + 35, 23, name, lab, dark, light)
            self._disp_cnt_window(c, x, 32, x + 70, 92)
            if g:
                for cy in (54, 70):
                    c.circle(x - 9, cy, 2.3, fill=light)
                    c.circle(x - 9.3, cy - 0.3, 2.1, fill=dark)
        # zweites Zählwerk
        for (x, n), name in zip(self._disp_cnt_small, ("TAG", "KW")):
            _disp_engrave(c, x - 18, 130, name, lab, dark, light)
            self._disp_cnt_window(c, x, 114, x + n * 22 - 2, 146)
        # Typenschild
        _disp_grad(c.img, (66 * s, 158 * s, 254 * s, 202 * s), 3 * s,
                   [(0, (212, 206, 190)), (0.5, (186, 180, 164)), (1, (150, 144, 128))])
        c.d.rounded_rectangle([66 * s, 158 * s, 254 * s, 202 * s], 3 * s, outline=(90, 86, 76), width=s)
        c.rect(70, 162, 74, 198, fill=acc)
        for rx, ry in ((80, 163), (248, 163), (80, 197), (248, 197)):
            c.circle(rx, ry, 1.9, fill=(110, 104, 92))
            c.circle(rx - 0.4, ry - 0.4, 1.1, fill=(230, 226, 214))
        big = self._disp_font(_disp_sans, 13 * s, True)
        tiny = self._disp_font(_disp_cond, 8 * s, True)
        ink, glint = (44, 40, 34), (240, 236, 224)
        _disp_engrave(c, 164, 172, "G19s  ZÄHLWERK", big, ink, glint)
        _disp_engrave(c, 164, 188, "TYP ZW 6-5  ·  24 STD  ·  Nr. 0419", tiny, ink, glint)

    @clock_face("counter", fps=5)
    def face_counter(self, profile):
        t = self._clock_now()
        now, prev = time.localtime(t), time.localtime(math.floor(t) - 1)
        p = self._disp_step(t, 0.4)
        acc = PROFILE_COLOR.get(profile, self.FG)
        img = self._disp_base(("counter", acc), (14, 14, 15), lambda c: self._disp_cnt_static(c, acc))
        fmt = "{0.tm_hour:02d}{0.tm_min:02d}{0.tm_sec:02d}"
        a, b = fmt.format(prev), fmt.format(now)
        mods = (3, 10, 6, 10, 6, 10)
        for k in range(6):
            x = self._disp_cnt_groups[k // 2] + (k % 2) * 36
            self._disp_roll(img, x, 32, "big", a[k], b[k], mods[k], p, red=k >= 4)
        small = (f"{prev.tm_yday:03d}" + time.strftime("%V", prev), f"{now.tm_yday:03d}" + time.strftime("%V", now))
        mods = (4, 10, 10, 6, 10)
        k = 0
        for x, n in self._disp_cnt_small:
            for i in range(n):
                self._disp_roll(img, x + i * 22, 114, "small", small[0][k], small[1][k], mods[k], p)
                k += 1
        return self._disp_out(img)
