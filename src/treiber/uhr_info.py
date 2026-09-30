"""Zifferblätter Wortuhr, Terminal, Tagesfortschritt, Ringuhr, Tacho-Uhr."""
import colorsys
import math
from PIL import ImageFilter

_info_WHITE = (255, 255, 255)
# Blockziffern 3×5 für das Terminal (Zeilen von oben, je 3 Bit)
_info_BLOCKS = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
    ":": ("0", "1", "0", "1", "0"),
}
_info_PHOSPHOR = {"green": (70, 255, 120), "amber": (255, 176, 40), "white": (225, 235, 245), "blue": (90, 180, 255)}


def _info_hsv(color, dh=0.0, ds=1.0, dv=1.0):
    """Farbton um dh drehen, Sättigung und Helligkeit mit ds/dv skalieren."""
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in color])
    return tuple(round(x * 255) for x in colorsys.hsv_to_rgb((h + dh) % 1, min(1, s * ds), min(1, v * dv)))


def _info_pct(p):
    """Anteil als Prozent mit deutschem Komma: 0.396 → „39,6 %“."""
    return f"{math.floor(p * 1000 + 1e-9) / 10:.1f}".replace(".", ",") + " %"      # abgerundet: 100 % erst am Ende


def _info_span(t, start, end):
    """Anteil von t zwischen zwei lokalen Zeitpunkten (Tupel für mktime, Sommerzeit wird beachtet)."""
    a, b = time.mktime(start[:6] + (0, 0, -1)), time.mktime(end[:6] + (0, 0, -1))
    return min(1.0, max(0.0, (t - a) / (b - a)))


class InfoFaces:
    @staticmethod
    def _info_font(size, bold=False, mono=False, scale=CLOCK_SS):
        """DejaVu Sans bzw. Sans Mono; size in Displaypixeln, scale = Vergrößerung der Fläche."""
        return clock_font("mono" if mono else "sans", round(size * scale), bold)

    def _info_out(self, arr):
        """Fläche (numpy, CLOCK_H×WIDTH×3) ins Displaybild setzen."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, 0))
        return img

    # --- Wortuhr -------------------------------------------------------------- #
    _info_GRID = ["ESKISTAFÜNF", "ZEHNZWANZIG", "DREIVIERTEL", "TGNACHVORJM", "HALBXZWÖLFP",
                  "ZWEINSIEBEN", "KDREIRHFÜNF", "ELFNEUNVIER", "WACHTZEHNRS", "BSECHSFMUHR"]
    _info_WORD = {"ES": (0, 0, 2), "IST": (0, 3, 3), "M5": (0, 7, 4), "M10": (1, 0, 4), "M20": (1, 4, 7),
                  "VIERTEL": (2, 4, 7), "NACH": (3, 2, 4), "VOR": (3, 6, 3), "HALB": (4, 0, 4),
                  "EIN": (5, 2, 3), "UHR": (9, 8, 3)}                # (Zeile, Spalte, Länge)
    _info_HOUR = [None, (5, 2, 4), (5, 0, 4), (6, 1, 4), (7, 7, 4), (6, 7, 4), (9, 1, 5), (5, 5, 6),
                  (8, 1, 4), (7, 3, 4), (8, 5, 4), (7, 0, 3), (4, 5, 5)]    # EINS … ZWÖLF
    _info_MINW = {0: [], 5: ["M5", "NACH"], 10: ["M10", "NACH"], 15: ["VIERTEL", "NACH"], 20: ["M20", "NACH"],
                  25: ["M5", "VOR", "HALB"], 30: ["HALB"], 35: ["M5", "NACH", "HALB"], 40: ["M20", "VOR"],
                  45: ["VIERTEL", "VOR"], 50: ["M10", "VOR"], 55: ["M5", "VOR"]}
    _info_CW, _info_CH, _info_X0, _info_Y0 = 24, 19.4, 28, 10      # Rasterzelle und Ursprung
    _info_DOTS = [(13, 9), (307, 9), (307, 205), (13, 205)]       # Minute 1–4: im Uhrzeigersinn ab oben links

    def _info_words_lit(self, hour, minute):
        """Leuchtende Rasterzellen {(zeile, spalte)} für die Uhrzeit."""
        m5 = minute - minute % 5
        h = (hour + (1 if m5 >= 25 else 0)) % 12 or 12
        spans = [self._info_WORD[w] for w in ["ES", "IST"] + self._info_MINW[m5]]
        if m5 == 0:
            spans += [self._info_WORD["EIN"] if h == 1 else self._info_HOUR[h], self._info_WORD["UHR"]]
        else:
            spans.append(self._info_HOUR[h])
        return {(r, c + k) for r, c, n in spans for k in range(n)}

    def _info_words_draw(self, d, cells, dots, fill, font):
        for r, row in enumerate(self._info_GRID):
            for c, ch in enumerate(row):
                if cells is None or (r, c) in cells:
                    d.text((self._info_X0 + (c + 0.5) * self._info_CW, self._info_Y0 + (r + 0.5) * self._info_CH),
                           ch, font=font, fill=fill, anchor="mm")
        for x, y in self._info_DOTS[:dots]:
            d.ellipse([x - 2.6, y - 2.6, x + 2.6, y + 2.6], fill=fill)

    def _info_words_plate(self, font):
        """Frontplatte mit dunklen Buchstaben (numpy-Feld)."""
        base = Image.new("RGB", (WIDTH, CLOCK_H), self.BG)
        yy, xx = np.mgrid[0:CLOCK_H, 0:WIDTH]
        v = 1 - 0.55 * (((xx - CLOCK_CX) / 200) ** 2 + ((yy - CLOCK_CY) / 150) ** 2)
        arr = np.asarray(base, np.float32) * np.clip(v, 0.5, 1.2)[..., None] + np.array([4, 4, 6])
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        self._info_words_draw(ImageDraw.Draw(base), None, 4, (26, 29, 37), font)
        return np.asarray(base, np.float32)

    @clock_face("words", fps=1)
    def face_words(self, profile):
        now = time.localtime(self._clock_now())
        col = self._ccolor(self._copt("words")["color"], profile)
        font = self._info_font(15, True, scale=1)
        plate = self._clock_cache("info_words", self.BG, lambda: self._info_words_plate(font))
        mask = Image.new("L", (WIDTH, CLOCK_H), 0)
        self._info_words_draw(ImageDraw.Draw(mask), self._info_words_lit(now.tm_hour, now.tm_min),
                              now.tm_min % 5, 255, font)
        m = np.asarray(mask, np.float32)[..., None] / 255
        glow = np.asarray(mask.filter(ImageFilter.GaussianBlur(4)), np.float32)[..., None] / 255
        core = np.array(mix(col, _info_WHITE, 0.35), np.float32)
        out = plate * (1 - m) + core * m + np.array(col, np.float32) * glow * 0.8
        return self._info_out(out)

    # --- Terminal ------------------------------------------------------------- #
    @staticmethod
    def _info_term_static(col):
        """Röhrenbildschirm: Gehäuse, gewölbt wirkender Schirm, Zeilenraster (als numpy-Felder)."""
        s = CLOCK_SS
        img = Image.new("RGB", (WIDTH * s, CLOCK_H * s), (22, 23, 26))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1 * s, 1 * s, (WIDTH - 1) * s, (CLOCK_H - 1) * s], 10 * s, fill=(34, 35, 39))
        d.rounded_rectangle([4 * s, 4 * s, (WIDTH - 4) * s, (CLOCK_H - 4) * s], 16 * s, fill=(12, 12, 14))
        d.rounded_rectangle([6 * s, 6 * s, (WIDTH - 6) * s, (CLOCK_H - 6) * s], 15 * s, fill=(255, 255, 255))
        img = img.resize((WIDTH, CLOCK_H), Image.LANCZOS)
        a = np.asarray(img, np.float32)
        screen = np.clip((a.min(axis=2) - 40) / 215, 0, 1)[..., None]        # 1 = Schirmfläche
        yy, xx = np.mgrid[0:CLOCK_H, 0:WIDTH]
        vign = np.clip(1 - 0.9 * (((xx - CLOCK_CX) / 175) ** 4 + ((yy - CLOCK_CY) / 125) ** 4), 0.25, 1)[..., None]
        glass = np.array(mix((5, 7, 6), col, 0.06), np.float32) * vign * 1.3
        bg = a * (1 - screen) + glass * screen
        scan = 1 - 0.32 * (yy % 2)[..., None] * screen
        return bg, scan, vign * screen

    def _info_term_big(self, d, x, y, txt, b):
        """Uhrzeit aus 3×5-Blockziffern (Kantenlänge b)."""
        for ch in txt:
            rows = _info_BLOCKS[ch]
            for r, bits in enumerate(rows):
                for k, bit in enumerate(bits):
                    if bit == "1":
                        d.rectangle([x + k * b, y + r * b, x + k * b + b - 2, y + r * b + b - 2], fill=255)
            x += len(rows[0]) * b + b

    @clock_face("terminal", fps=2)
    def face_terminal(self, profile):
        t = self._clock_now()
        now = time.localtime(t)
        col = _info_PHOSPHOR.get(self._copt("terminal")["color"], _info_PHOSPHOR["green"])
        bg, scan, screen = self._clock_cache("info_term", col, lambda: self._info_term_static(col))
        f, fb = self._info_font(12, mono=True, scale=1), self._info_font(12, True, True, scale=1)
        mask = Image.new("L", (WIDTH, CLOCK_H), 0)
        d = ImageDraw.Draw(mask)
        cw = fb.getlength("0")
        prompt = "g19s@kubuntu:~$ "
        x0, lh = 16, 16
        y = 22

        def cmd(y, text):
            d.text((x0, y), prompt, font=fb, fill=255, anchor="ls")
            d.text((x0 + cw * len(prompt), y), text, font=f, fill=215, anchor="ls")

        date = (f"{WEEKDAY_DE[now.tm_wday]} {now.tm_mday}. {MONTH_3[now.tm_mon - 1].capitalize()} "
                f"{time.strftime('%H:%M:%S %Z %Y', now)}")
        cmd(y, "date")
        d.text((x0, y + lh), date, font=f, fill=170, anchor="ls")
        cmd(y + 2.25 * lh, "uhr")
        self._info_term_big(d, x0 + 2, y + 2.25 * lh + 9, time.strftime("%H:%M:%S", now), 8)
        days = 366 if now.tm_year % 4 == 0 and (now.tm_year % 100 or now.tm_year % 400 == 0) else 365
        yi = y + 2.25 * lh + 9 + 40 + 14
        d.text((x0, yi), f"KW {time.strftime('%V', now)} · Tag {now.tm_yday}/{days}", font=f, fill=170, anchor="ls")
        cmd(yi + 1.25 * lh, "date +%s")
        d.text((x0, yi + 2.25 * lh), str(int(t)), font=f, fill=170, anchor="ls")
        cmd(yi + 3.5 * lh, "")
        if t % 1 < 0.5:                                     # blinkender Block-Cursor
            cx = x0 + cw * len(prompt)
            d.rectangle([cx, yi + 3.5 * lh - 11, cx + cw - 1, yi + 3.5 * lh + 2], fill=235)
        m = np.asarray(mask, np.float32)[..., None] / 255
        glow = np.asarray(mask.filter(ImageFilter.GaussianBlur(2.2)), np.float32)[..., None] / 255
        c = np.array(col, np.float32)
        out = bg + (mix(col, _info_WHITE, 0.3) - bg) * m * 0.92 + c * glow * 0.75 * screen
        return self._info_out(out * scan)

    # --- Tagesfortschritt ----------------------------------------------------- #
    def _info_bar(self, c, x0, y0, x1, h, p, col, ticks):
        """Waagrechter Balken mit Spur, Verlauf bis zum Stand p und Teilstrichen darunter."""
        s = CLOCK_SS
        track = mix(col, self.BG, 0.84)
        c.d.rounded_rectangle([x0 * s, y0 * s, x1 * s, (y0 + h) * s], h * s / 2, fill=track)
        w = max(h, (x1 - x0) * p) if p > 0 else 0
        if w:
            W, H = round(w * s), round(h * s)
            ramp = np.linspace(0, 1, W, dtype=np.float32)[None, :, None] ** 0.8
            a, b = np.array(mix(col, self.BG, 0.55), np.float32), np.array(mix(col, _info_WHITE, 0.3), np.float32)
            grad = a + (b - a) * ramp
            shade = np.linspace(1.25, 0.8, H, dtype=np.float32)[:, None, None]          # leichte Wölbung
            grad = np.clip(grad * shade, 0, 255).astype(np.uint8)
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], H / 2, fill=255)
            c.img.paste(Image.fromarray(np.ascontiguousarray(np.broadcast_to(grad, (H, W, 3)))),
                        (round(x0 * s), round(y0 * s)), m)
            c.circle(x0 + w - h / 2, y0 + h / 2, h / 2 - 1.8, fill=mix(col, _info_WHITE, 0.7))   # Leuchtpunkt
        for k in range(1, ticks):
            x = x0 + (x1 - x0) * k / ticks
            c.rect(x - 0.3, y0 + h + 2, x + 0.3, y0 + h + 4, fill=(60, 66, 80))

    @clock_face("progress", fps=1)
    def face_progress(self, profile):
        t = self._clock_now()
        now = time.localtime(t)
        col = PROFILE_COLOR.get(profile, self.FG)
        c = self._clock_canvas("info_progress", self.BG, lambda c: None)
        s = CLOCK_SS
        y, mo, dd, hh = now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour
        big, secf = self._info_font(30, True), self._info_font(15, True)
        c.d.text((14 * s, 40 * s), time.strftime("%H:%M", now), font=big, fill=self.FG, anchor="ls")
        xw = 14 + big.getlength(time.strftime("%H:%M", now)) / s
        c.d.text(((xw + 3) * s, 40 * s), time.strftime("%S", now), font=secf, fill=mix(col, _info_WHITE, 0.45),
                 anchor="ls")
        c.d.text((306 * s, 23 * s), WEEKDAYS[now.tm_wday], font=self._info_font(13, True), fill=self.FG, anchor="rs")
        c.d.text((306 * s, 39 * s), f"{dd}. {MONTHS[mo - 1]} {y}", font=self._info_font(11), fill=self.DIM,
                 anchor="rs")
        c.rect(14, 50, 306, 50.6, fill=(40, 44, 56))
        mdays = (time.mktime((y + (mo == 12), mo % 12 + 1, 1, 12, 0, 0, 0, 0, -1))
                 - time.mktime((y, mo, 1, 12, 0, 0, 0, 0, -1))) / 86400
        ydays = 366 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 365
        rows = [
            ("Stunde", f"{hh:02d}–{(hh + 1) % 24:02d} Uhr", (now.tm_min * 60 + now.tm_sec + t % 1) / 3600, 4),
            ("Tag", WEEKDAYS[now.tm_wday], _info_span(t, (y, mo, dd, 0, 0, 0, 0), (y, mo, dd + 1, 0, 0, 0, 0)), 4),
            (f"Woche (KW {time.strftime('%V', now)})", "Mo–So",
             _info_span(t, (y, mo, dd - now.tm_wday, 0, 0, 0, 0), (y, mo, dd - now.tm_wday + 7, 0, 0, 0, 0)), 7),
            (MONTHS[mo - 1], f"Tag {dd}/{round(mdays)}",
             _info_span(t, (y, mo, 1, 0, 0, 0, 0), (y + (mo == 12), mo % 12 + 1, 1, 0, 0, 0, 0)), round(mdays)),
            (str(y), f"Tag {now.tm_yday}/{ydays}", _info_span(t, (y, 1, 1, 0, 0, 0, 0), (y + 1, 1, 1, 0, 0, 0, 0)), 12),
        ]
        lab, sub, pf = self._info_font(11, True), self._info_font(9), self._info_font(11, True)
        for i, (label, detail, p, ticks) in enumerate(rows):
            yb = 70 + i * 29
            c.d.text((14 * s, yb * s), label, font=lab, fill=self.FG, anchor="ls")
            c.d.text((14 * s + lab.getlength(label) + 6 * s, yb * s), detail, font=sub, fill=self.DIM, anchor="ls")
            c.d.text((306 * s, yb * s), _info_pct(p), font=pf, fill=mix(col, _info_WHITE, 0.5), anchor="rs")
            self._info_bar(c, 14, yb + 4, 306, 9, p, col, ticks)
        return self._clock_finish(c)

    # --- Ringuhr -------------------------------------------------------------- #
    def _info_arc(self, c, cx, cy, r, w, deg0, deg1, fill):
        """Bogen (Mittenradius r, Breite w) von deg0 bis deg1 (0 = 12 Uhr)."""
        s, R = CLOCK_SS, r + w / 2
        c.d.arc([(cx - R) * s, (cy - R) * s, (cx + R) * s, (cy + R) * s], deg0 - 90, deg1 - 90, fill=fill,
                width=round(w * s))

    def _info_ring_colors(self, col):
        """Stunden-, Minuten-, Sekundenfarbe: benachbarte Farbtöne der Ebenenfarbe."""
        return (_info_hsv(col, 0.0, 0.95, 1.0), _info_hsv(col, -0.07, 0.8, 1.15), _info_hsv(col, 0.09, 0.7, 1.2))

    _info_RINGS = ((62, 12, 12), (80, 12, 60), (98, 11, 60))      # Stunden, Minuten, Sekunden: Radius, Breite, Teilung

    def _info_rings_dial(self, c, col):
        cx, cy = CLOCK_CX, CLOCK_CY
        for (r, w, n), rc in zip(self._info_RINGS, self._info_ring_colors(col)):
            self._info_arc(c, cx, cy, r, w + 2, 0, 360, (16, 18, 24))
            self._info_arc(c, cx, cy, r, w, 0, 360, mix(rc, self.BG, 0.86))
            for k in range(n):
                big = n == 12 or k % 5 == 0
                c.radial(cx, cy, r - w / 2 + (1 if big else 3), r + w / 2 - (1 if big else 3), k * 360 / n,
                         0.9 if big else 0.5, mix(rc, self.BG, 0.7))
        f = self._cfonts
        cols = self._info_ring_colors(col)
        for i, (name, rc) in enumerate((("STD", cols[0]), ("MIN", cols[1]), ("SEK", cols[2]))):
            c.circle(12, 78 + i * 26, 3.5, fill=rc)
            c.d.text((20 * CLOCK_SS, (78 + i * 26) * CLOCK_SS), name, font=f["tiny"], fill=self.DIM, anchor="lm")

    @clock_face("rings", fps=1)
    def face_rings(self, profile):
        col = PROFILE_COLOR.get(profile, self.FG)
        c = self._clock_canvas(("info_rings", col), self.BG, lambda c: self._info_rings_dial(c, col))
        cx, cy, s = CLOCK_CX, CLOCK_CY, CLOCK_SS
        now = time.localtime(self._clock_now())
        vals = ((now.tm_hour % 12 + now.tm_min / 60) / 12, (now.tm_min + now.tm_sec / 60) / 60, now.tm_sec / 60)
        for (r, w, n), rc, v in zip(self._info_RINGS, self._info_ring_colors(col), vals):
            deg = v * 360
            if deg > 0.5:
                self._info_arc(c, cx, cy, r, w + 3, 0, deg, mix(rc, self.BG, 0.72))     # Schein
                self._info_arc(c, cx, cy, r, w, 0, deg, rc)
                for k in range(n):                                                      # Teilung auf dem Bogen
                    if 0 < k * 360 / n < deg - 2:
                        big = n == 12 or k % 5 == 0
                        c.radial(cx, cy, r - w / 2, r + w / 2, k * 360 / n, 0.9 if big else 0.45, mix(rc, self.BG, 0.35))
            x0, y0 = [v / s for v in c.pt(cx, cy, r, 0)]
            c.circle(x0, y0, w / 2, fill=rc if deg > 0.5 else mix(rc, self.BG, 0.4))
            x1, y1 = [v / s for v in c.pt(cx, cy, r, deg)]
            c.circle(x1, y1, w / 2 + 1, fill=mix(rc, self.BG, 0.5))
            c.circle(x1, y1, w / 2, fill=rc)
            c.circle(x1, y1, w / 2 - 3, fill=mix(rc, _info_WHITE, 0.6))                 # heller Kopf
        c.text(cx, cy - 9, time.strftime("%H:%M", now), self._info_font(27, True), self.FG)
        c.text(cx, cy + 15, time.strftime(":%S", now), self._info_font(13, True), self._info_ring_colors(col)[2])
        c.text(cx, cy + 31, f"{WEEKDAY_DE[now.tm_wday]} {now.tm_mday:02d}.{now.tm_mon:02d}.", self._cfonts["tiny"],
               self.DIM)
        f = self._cfonts
        c.text(296, 86, "KW", f["tiny"], self.DIM)
        c.text(296, 102, time.strftime("%V", now), f["side"], self.FG)
        c.text(296, 128, str(now.tm_year), f["tiny"], self.DIM)
        return self._clock_finish(c)

    # --- Tacho-Uhr ------------------------------------------------------------ #
    _info_GL, _info_GR, _info_GY, _info_GRAD = 82, 238, 92, 73     # Mittelpunkte, Höhe, Radius

    def _info_chrome(self, c, cx, cy, r_out, r_in):
        """Chromring mit senkrechtem Glanzverlauf."""
        s = CLOCK_SS
        x0, y0, n = round((cx - r_out) * s), round((cy - r_out) * s), round(2 * r_out * s) + 1
        yy = np.linspace(0, 1, n, dtype=np.float32)[:, None]
        xx = np.linspace(0, 1, n, dtype=np.float32)[None, :]
        v = np.interp(yy, [0, 0.3, 0.48, 0.56, 0.75, 1], [240, 170, 70, 110, 200, 120]) + 18 * np.sin(xx * math.pi)
        arr = np.clip(np.stack([v, v + 2, v + 8], axis=2), 0, 255).astype(np.uint8)
        m = Image.new("L", (n, n), 0)
        md = ImageDraw.Draw(m)
        md.ellipse([0, 0, n - 1, n - 1], fill=255)
        k = (r_out - r_in) * s
        md.ellipse([k, k, n - 1 - k, n - 1 - k], fill=0)
        c.img.paste(Image.fromarray(arr), (x0, y0), m)

    @staticmethod
    def _info_gdeg(v, vmax):
        return -135 + 270 * v / vmax

    def _info_gauge_dial(self, c, cx, cy, vmax, major, minor, labels, red, unit, col):
        f, R = self._cfonts, self._info_GRAD
        c.circle(cx, cy, R + 4, fill=(6, 6, 8))
        self._info_chrome(c, cx, cy, R + 3, R - 3)
        c.circle(cx, cy, R - 3, fill=(4, 4, 6))
        for r in range(round(R - 4), 0, -2):                     # Zifferblatt, zur Mitte heller
            c.circle(cx, cy, r, fill=mix((30, 32, 38), (12, 13, 16), r / (R - 4)))
        self._info_arc(c, cx, cy, R - 7, 1.2, -135, 135, mix(col, (0, 0, 0), 0.35))      # Leuchtring
        if red:
            self._info_arc(c, cx, cy, R - 12, 5, self._info_gdeg(red, vmax), 135, (205, 30, 30))
        n = round(vmax / minor)
        for k in range(n + 1):
            v = k * minor
            deg = self._info_gdeg(v, vmax)
            is_major = abs(v / major - round(v / major)) < 1e-6
            tc = (235, 60, 50) if red and v >= red else (236, 238, 242)
            c.radial(cx, cy, R - (19 if is_major else 14), R - 9, deg, 1.8 if is_major else 0.8, tc)
        for v in labels:
            x, y = [p / CLOCK_SS for p in c.pt(cx, cy, R - 29, self._info_gdeg(v, vmax))]
            c.text(x, y, str(v), f["small"], (235, 60, 50) if red and v >= red else (236, 238, 242))
        c.text(cx, cy + 25, unit, f["tiny"], (150, 156, 170))

    def _info_gauge_static(self, c, col):
        s = CLOCK_SS
        h, w = CLOCK_H * s, WIDTH * s                            # Carbon-Geflecht
        yy, xx = np.mgrid[0:h, 0:w]
        cell = 4 * s
        a = ((xx // cell) + (yy // cell)) % 2
        ph = np.where(a == 0, (xx % cell) / cell, (yy % cell) / cell)
        v = 17 + 10 * np.sin(ph * math.pi)
        v *= np.clip(1.15 - 0.6 * (((xx / w - 0.5) * 1.6) ** 2 + ((yy / h - 0.45) * 1.4) ** 2), 0.4, 1.2)
        c.img.paste(Image.fromarray(np.stack([v, v, v * 1.08], axis=2).clip(0, 255).astype(np.uint8)), (0, 0))
        cy = self._info_GY
        self._info_gauge_dial(c, self._info_GL, cy, 24, 2, 0.5, range(0, 25, 2), 22, "STD", col)
        self._info_gauge_dial(c, self._info_GR, cy, 60, 5, 1, range(0, 61, 10), None, "MIN", col)
        c.d.rounded_rectangle([66 * s, 174 * s, 254 * s, 208 * s], 7 * s, fill=(70, 72, 78))    # LC-Display
        c.d.rounded_rectangle([67.5 * s, 175.5 * s, 252.5 * s, 206.5 * s], 6 * s, fill=(8, 9, 11))
        c.d.rounded_rectangle([70 * s, 178 * s, 250 * s, 204 * s], 4 * s, fill=mix(col, (4, 5, 7), 0.9))
        for x in (116, 196):
            c.rect(x, 181, x + 0.5, 201, fill=mix(col, (4, 5, 7), 0.7))

    def _info_needle(self, c, cx, cy, deg):
        R, red = self._info_GRAD, (255, 64, 24)
        prof = [(-14, 4.2), (0, 3.6), (R - 14, 1.3)]
        for grow, t in ((4.5, 0.86), (2.8, 0.7), (1.4, 0.45)):     # Glühen
            c.hand(cx, cy, deg, [(r - grow / 2, w + grow) for r, w in prof[:2]] + [(R - 14 + grow / 2, 1.3 + grow)],
                   mix(red, (14, 15, 18), t))
        c.hand(cx, cy, deg, prof, red)
        c.hand(cx, cy, deg, [(0, 1), (R - 18, 0.5)], (255, 190, 150))
        c.circle(cx, cy, 8, fill=(26, 27, 31), outline=(150, 154, 162), width=1.2)
        c.circle(cx, cy, 3, fill=(60, 62, 68))

    @clock_face("gauge", fps=1)
    def face_gauge(self, profile):
        col = PROFILE_COLOR.get(profile, self.FG)
        c = self._clock_canvas(("info_gauge", col), self.BG, lambda c: self._info_gauge_static(c, col))
        now = time.localtime(self._clock_now())
        f, cy, s = self._cfonts, self._info_GY, CLOCK_SS
        hours = now.tm_hour + now.tm_min / 60 + now.tm_sec / 3600
        mins = now.tm_min + now.tm_sec / 60
        lcd = mix(col, _info_WHITE, 0.55)
        for cx, val, txt in ((self._info_GL, hours / 24, f"{now.tm_hour:02d}"),
                             (self._info_GR, mins / 60, f"{now.tm_min:02d}")):
            c.text(cx, cy + 42, txt, self._info_font(17, True), lcd)
            self._info_needle(c, cx, cy, -135 + 270 * val)
        seg = self._info_font(15, True, True)
        c.d.text((76 * s, 191 * s), f"{now.tm_sec:02d}", font=seg, fill=lcd, anchor="lm")
        c.d.text((96 * s, 192 * s), "SEK", font=f["tiny"], fill=mix(col, _info_WHITE, 0.2), anchor="lm")
        c.text(156, 191, f"{WEEKDAY_DE[now.tm_wday]} {now.tm_mday:02d}.{now.tm_mon:02d}.{now.tm_year % 100:02d}",
               self._info_font(11, True, True), lcd)
        c.d.text((203 * s, 191 * s), "TAG", font=f["tiny"], fill=mix(col, _info_WHITE, 0.2), anchor="lm")
        for i, ch in enumerate(f"{now.tm_yday:03d}"):             # Zählwerk wie ein Kilometerzähler
            x = 223 + i * 9
            last = i == 2
            c.rect(x, 183, x + 8, 199, fill=(236, 236, 232) if last else (14, 14, 16), outline=(90, 92, 98), width=0.6)
            c.text(x + 4.2, 191.3, ch, self._info_font(11, True, True), (20, 20, 22) if last else (236, 238, 242))
        return self._clock_finish(c)
