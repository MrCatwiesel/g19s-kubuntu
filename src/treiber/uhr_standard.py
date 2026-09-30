"""Zifferblätter Chronometer, Steampunk-Uhr, Bahnhofsuhr und Binäruhr."""
import math


class StandardFaces:
    # --- Chronometer ---------------------------------------------------------- #
    CHRONO_DIALS = {   # Zifferblatt, Hilfszifferblätter, Indizes, Schrift hell/dunkel, Viertelsekunden, Zeiger
        "black": ((18, 20, 24), (30, 32, 37), (210, 214, 222), (225, 228, 235), (170, 175, 185), (95, 100, 110), (220, 224, 232)),
        "blue": ((16, 30, 66), (24, 40, 80), (214, 218, 226), (230, 234, 242), (160, 176, 205), (80, 96, 130), (222, 226, 234)),
        "green": ((16, 46, 32), (24, 58, 42), (214, 218, 222), (230, 236, 232), (160, 190, 170), (80, 110, 92), (222, 226, 230)),
        "silver": ((204, 208, 214), (184, 188, 196), (60, 64, 72), (34, 38, 46), (80, 84, 92), (150, 154, 160), (54, 58, 66)),
    }

    def _chrono_dial(self, c, dial):
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        face, sub, idx, txt, txt2, quarter, _hand = self.CHRONO_DIALS[dial]
        steel, steel_hi, steel_lo = (92, 97, 106), (190, 196, 205), (40, 43, 50)
        c.circle(cx, cy, 102, fill=steel_lo)
        c.circle(cx, cy, 100.5, fill=steel)
        c.circle(cx, cy, 100.5, outline=steel_hi, width=1)
        c.circle(cx, cy, 87, fill=(24, 26, 30))
        c.circle(cx, cy, 87, outline=steel_lo, width=1.5)
        for m in range(5, 61, 5):                          # Skala auf der Lünette
            c.text(*[v / CLOCK_SS for v in c.pt(cx, cy, 94, m * 6)], f"{m:02d}" if m < 60 else "60",
                   f["tiny"], (235, 238, 245))
        c.circle(cx, cy, 87, fill=face)
        for q in range(240):                              # Viertelsekunden
            c.radial(cx, cy, 83.5, 86, q * 1.5, 0.35, quarter)
        for m in range(60):
            if m % 5:
                c.radial(cx, cy, 81, 86, m * 6, 0.9, idx)
        for h in range(12):
            if h in (3, 6, 9):
                continue
            deg = h * 30
            if h == 0:
                for off in (-3.2, 3.2):
                    c.hand(cx, cy, deg + off, [(62, 4.2), (80, 4.2)], idx, outline=(90, 94, 102))
            else:
                c.hand(cx, cy, deg, [(62, 5.5), (80, 5.5)], idx, outline=(90, 94, 102))
                c.radial(cx, cy, 65, 77, deg, 2, (230, 240, 210))        # Leuchtmasse
        c.text(cx, cy - 44, "G19s", f["mid"], txt)
        c.text(cx, cy - 32, "CHRONOMETER", f["tiny"], txt2)
        # Hilfszifferblätter: links 24 Stunden, rechts kleine Sekunde
        for sx, labels, ticks in ((cx - 44, [("24", 0), ("6", 90), ("12", 180), ("18", 270)], 24),
                                  (cx + 44, [("60", 0), ("15", 90), ("30", 180), ("45", 270)], 60)):
            c.circle(sx, cy, 23, fill=sub)
            c.circle(sx, cy, 23, outline=(150, 155, 165), width=1)
            for k in range(ticks):
                long_tick = k % (ticks // 12 if ticks == 24 else 5) == 0
                c.radial(sx, cy, 19.5 if long_tick else 21, 23, k * 360 / ticks, 0.8 if long_tick else 0.5,
                         txt2)
            for label, deg in labels:
                x, y = c.pt(sx, cy, 13.5, deg)
                c.text(x / CLOCK_SS, y / CLOCK_SS, label, f["tiny"], txt)
        c.rect(cx - 20, cy + 52, cx + 20, cy + 68, fill=(245, 245, 240), outline=(120, 124, 132), width=1)
        c.radial(cx, cy + 53, 0, -14, 0, 0.8, (170, 172, 176))     # Trennlinie Tag | Datum

    @clock_face("chrono")
    def face_chrono(self, profile):
        opt = self._copt("chrono")
        dial = opt["dial"] if opt["dial"] in self.CHRONO_DIALS else "black"
        c = self._clock_canvas(("chrono", dial), (10, 11, 14), lambda c: self._chrono_dial(c, dial))
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        now = time.localtime(self._clock_now())
        acc = self._ccolor(opt["hand"], profile)
        if opt["side"] in ("both", "date"):               # links Datum
            c.text(31, 90, f"{now.tm_mday}", f["big"], (225, 228, 235))
            c.text(31, 114, MONTH_3[now.tm_mon - 1], f["small"], (150, 156, 170))
            c.text(31, 130, str(now.tm_year), f["tiny"], (110, 116, 130))
        if opt["side"] == "both":                         # rechts Kalenderwoche und Digitalzeit
            c.text(289, 90, time.strftime("%V", now), f["big"], (225, 228, 235))
            c.text(289, 114, "KW", f["small"], (150, 156, 170))
            c.text(289, 130, time.strftime("%H:%M", now), f["tiny"], (110, 116, 130))
        c.text(cx - 10, cy + 60.5, WEEKDAY_2[now.tm_wday], f["small"], (20, 20, 24))
        c.text(cx + 10, cy + 60.5, str(now.tm_mday), f["small"], (180, 30, 30) if now.tm_wday == 6 else (20, 20, 24))
        silver, dark = self.CHRONO_DIALS[dial][6], (60, 64, 72)
        h24 = (now.tm_hour + now.tm_min / 60) * 15
        c.hand(cx - 44, cy, h24, [(-4, 2.2), (17, 1.4), (19, 0)], silver)
        c.circle(cx - 44, cy, 2.2, fill=silver)
        c.hand(cx + 44, cy, now.tm_sec * 6, [(-5, 1.6), (0, 1.2), (19, 0.6)], silver)
        c.circle(cx + 44, cy, 2.2, fill=silver)
        ha, ma, sa = self._clock_angles(now)
        c.hand(cx, cy, ha, [(-10, 4), (0, 7.5), (38, 6.5), (52, 0)], silver, outline=dark)
        c.hand(cx, cy, ha, [(8, 2.4), (40, 2)], (230, 240, 210))
        c.hand(cx, cy, ma, [(-12, 3.5), (0, 6), (64, 4.5), (80, 0)], silver, outline=dark)
        c.hand(cx, cy, ma, [(10, 2), (66, 1.6)], (230, 240, 210))
        c.hand(cx, cy, sa, [(-22, 2.4), (0, 1.6), (84, 0.9)], acc)
        c.circle(*[v / CLOCK_SS for v in c.pt(cx, cy, -18, sa)], 3.2, fill=acc)
        c.circle(cx, cy, 4.2, fill=silver, outline=dark, width=0.8)
        c.circle(cx, cy, 1.6, fill=acc)
        return self._clock_finish(c)

    # --- Steampunk ------------------------------------------------------------ #
    _STEAM_GEARS = [                 # (x, y, Radius, Richtung)
        (30, 50, 44, 1), (38, 122, 34, -1), (18, 172, 22, 1),
        (292, 58, 40, -1), (290, 122, 30, 1), (300, 170, 20, -1),
    ]

    def _steam_dial(self, c):
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        brass, brass_hi, brass_lo = (176, 134, 62), (226, 190, 110), (96, 66, 28)
        c.circle(cx, cy, 102, fill=brass_lo)
        c.circle(cx, cy, 100, fill=brass)
        c.circle(cx, cy, 97, outline=brass_hi, width=1)
        c.circle(cx, cy, 89, fill=brass_lo)
        for k in range(16):                               # Nieten
            x, y = [v / CLOCK_SS for v in c.pt(cx, cy, 94, k * 22.5 + 11.25)]
            c.circle(x, y, 2.6, fill=(120, 86, 38))
            c.circle(x - 0.6, y - 0.6, 1.3, fill=brass_hi)
        for r in range(88, 0, -2):                        # vergilbtes Zifferblatt, zum Rand dunkler
            t = max(0.0, (r - 55) / 33)
            col = tuple(int(a + (b - a) * t) for a, b in zip((236, 224, 192), (196, 172, 124)))
            c.circle(cx, cy, r, fill=col)
        ink = (58, 38, 20)
        c.circle(cx, cy, 83, outline=ink, width=1)
        c.circle(cx, cy, 77, outline=ink, width=0.8)
        for m in range(60):
            c.radial(cx, cy, 77, 83, m * 6, 1.6 if m % 5 == 0 else 0.7, ink)
        for h, num in enumerate(ROMAN_XII):
            if h == 6:
                continue                                  # Platz für das Uhrwerk-Fenster
            x, y = [v / CLOCK_SS for v in c.pt(cx, cy, 63, h * 30)]
            c.text(x, y, num, f["roman"], ink)
        c.text(cx, cy - 34, "G19s", f["serif_s"], ink)
        c.text(cx, cy - 25, "MANUFACTUR", f["tiny"], (110, 80, 45))
        c.circle(cx, cy + 40, 19, fill=brass_lo)
        c.circle(cx, cy + 40, 17, fill=(34, 24, 14))

    @clock_face("steampunk")
    def face_steampunk(self, profile):
        c = self._clock_canvas("steam", (26, 17, 9), self._steam_dial)
        cx, cy = CLOCK_CX, CLOCK_CY
        t = self._clock_now()
        now = time.localtime(t)
        tick = int(t) if self._copt("steampunk")["gears"] else 0
        # Zahnräder hinter und im Zifferblatt drehen sich sekündlich weiter
        layer = _Canvas(Image.new("RGB", c.img.size, (26, 17, 9)))
        for x, y, r, direction in self._STEAM_GEARS:
            layer.gear(x, y, r, max(8, round(r / 3.4)), direction * tick * 6 * 40 / r,
                       (122, 82, 38) if r > 30 else (150, 104, 48), (58, 36, 16))
        def build_mask():
            mask = Image.new("L", c.img.size, 0)
            ImageDraw.Draw(mask).ellipse([(cx - 102.5) * CLOCK_SS, (cy - 102.5) * CLOCK_SS,
                                          (cx + 102.5) * CLOCK_SS, (cy + 102.5) * CLOCK_SS], fill=255)
            return mask
        layer.img.paste(c.img, (0, 0), self._clock_cache("std_steam_mask", 1, build_mask))
        c = layer
        c.gear(cx - 6, cy + 42, 11, 10, tick * 30, (196, 150, 70), (90, 60, 25))      # Unruh-Fenster
        c.gear(cx + 9, cy + 34, 7, 8, -tick * 47, (170, 126, 56), (90, 60, 25))
        c.circle(cx, cy + 40, 17, outline=(226, 190, 110), width=1)
        blue, blue_hi = (28, 34, 78), (70, 84, 150)
        ha, ma, sa = self._clock_angles(now)
        for deg, length, ring in ((ha, 50, 7), (ma, 74, 6)):              # Breguet-Zeiger
            rp = length * 0.72
            c.hand(cx, cy, deg, [(-12, 3), (0, 4), (rp - ring, 2.6)], blue)
            x, y = [v / CLOCK_SS for v in c.pt(cx, cy, rp, deg)]
            c.circle(x, y, ring, outline=blue, width=2.2)
            c.hand(cx, cy, deg, [(rp + ring - 1, 2.6), (length - 8, 3.2), (length, 0)], blue)
            c.hand(cx, cy, deg, [(2, 1), (rp - ring - 2, 0.8)], blue_hi)
        c.hand(cx, cy, sa, [(-20, 1.6), (0, 1.4), (80, 0.8)], (150, 40, 20))
        c.circle(*[v / CLOCK_SS for v in c.pt(cx, cy, 64, sa)], 2.2, fill=(150, 40, 20))
        c.circle(cx, cy, 5, fill=(196, 150, 70), outline=(90, 60, 25), width=1)
        c.radial(cx, cy, -3.5, 3.5, 45, 1, (90, 60, 25))                # Schraubenschlitz
        return self._clock_finish(c)

    # --- Bahnhofsuhr ---------------------------------------------------------- #
    def _station_dial(self, c):
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        c.circle(cx, cy, 103, fill=(28, 30, 34))
        c.circle(cx, cy, 101, fill=(70, 74, 80))
        c.circle(cx, cy, 99, fill=(34, 36, 40))
        c.circle(cx, cy, 96, fill=(246, 246, 243))
        black = (18, 18, 20)
        for m in range(60):
            if m % 5:
                c.radial(cx, cy, 85, 92, m * 6, 2.2, black)
            else:
                c.radial(cx, cy, 66, 92, m * 6, 7.5, black)

    @clock_face("station")
    def face_station(self, profile):
        opt = self._copt("station")
        c = self._clock_canvas("station", (10, 12, 16), self._station_dial)
        f, cx, cy = self._cfonts, CLOCK_CX, CLOCK_CY
        now = time.localtime(self._clock_now())
        if opt["side"]:
            c.text(31, 70, WEEKDAY_DE[now.tm_wday], f["side"], (235, 238, 245))
            c.text(31, 90, f"{now.tm_mday:02d}.{now.tm_mon:02d}.", f["small"], (170, 176, 190))
            c.text(31, 118, "KW", f["small"], (130, 138, 155))
            c.text(31, 138, time.strftime("%V", now), f["side"], (235, 238, 245))
            c.text(289, 80, str(now.tm_year), f["small"], (170, 176, 190))
            c.text(289, 100, MONTH_3[now.tm_mon - 1], f["side"], (235, 238, 245))
        black = (18, 18, 20)
        minute = now.tm_min + (now.tm_sec / 60 if opt["smooth"] else 0)   # springend: nur volle Minuten
        ha, ma, sa = ((now.tm_hour % 12) + minute / 60) * 30, minute * 6, now.tm_sec * 6
        c.hand(cx, cy, ha, [(-18, 10), (58, 8)], black)
        c.hand(cx, cy, ma, [(-22, 8), (86, 6)], black)
        red = (200, 28, 28)
        if opt["seconds"]:
            c.hand(cx, cy, sa, [(-26, 2.2), (70, 2.2)], red)
            c.hand(cx, cy, sa, [(-26, 5), (-16, 5)], red)
            c.circle(cx, cy, 3.5, fill=red)
        else:
            c.circle(cx, cy, 3.5, fill=black)
        return self._clock_finish(c)

    # --- Binäruhr ------------------------------------------------------------- #
    def _led(self, c, x, y, r, color, on, off):
        if on:
            c.circle(x, y, r + 3, fill=mix(color, self.BG, 0.75))
            c.circle(x, y, r, fill=color)
            c.circle(x - r * 3 / 13, y - r * 3 / 13, r * 4 / 13, fill=mix(color, (255, 255, 255), 0.4))
        else:
            c.circle(x, y, r, fill=off, outline=tuple(min(255, v + d) for v, d in zip(off, (28, 30, 36))), width=1.2)

    @clock_face("binary")
    def face_binary(self, profile):
        opt = self._copt("binary")
        c = self._clock_canvas("binary", self.BG, lambda c: None)
        f = self._cfonts
        now = time.localtime(self._clock_now())
        cols = [self._ccolor(opt[k], profile) for k in ("color_h", "color_m", "color_s")]
        off = tuple(opt["color_off"]) if opt["color_off"] else (24, 28, 38)
        if opt["mode"] == "binary":                       # je Zeile eine Binärzahl: 32 16 8 4 2 1
            r, step = 12, 34
            x0 = (WIDTH - 5 * step) / 2 + 8
            top = 34 if opt["digits"] else 50
            for i, v in enumerate((32, 16, 8, 4, 2, 1)):
                c.text(x0 + i * step, top - 22, str(v), f["tiny"], self.DIM)
            for row, (label, val, col) in enumerate((("Std", now.tm_hour, cols[0]), ("Min", now.tm_min, cols[1]),
                                                      ("Sek", now.tm_sec, cols[2]))):
                y = top + row * 44
                c.text(x0 - 36, y, label, f["small"], self.DIM)
                for i, v in enumerate((32, 16, 8, 4, 2, 1)):
                    if row == 0 and v == 32:
                        continue                          # Stunden: höchstens 23 → 5 Bit
                    self._led(c, x0 + i * step, y, r, col, val & v, off)
                if opt["digits"]:
                    c.text(x0 + 5 * step + 40, y, f"{val:02d}", f["led"], col)
            return self._clock_finish(c)
        digits = f"{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}"
        bits = [2, 4, 3, 4, 3, 4]                          # Bits je Ziffer (Zehner-Stunden: 0–2 → 2 Bit)
        step, gap, r = 36, 16, 13
        x0 = (WIDTH - (6 * step + 2 * gap)) / 2 + step / 2 + 10
        dy = 0 if opt["digits"] else 16
        rows = [30 + dy, 70 + dy, 110 + dy, 150 + dy]      # 8, 4, 2, 1
        for i, v in enumerate((8, 4, 2, 1)):
            c.text(x0 - 34, rows[i], str(v), f["small"], self.DIM)
        for col, ch in enumerate(digits):
            x = x0 + col * step + (col // 2) * gap
            n = int(ch)
            for i, v in enumerate((8, 4, 2, 1)):
                if 3 - i < bits[col]:
                    self._led(c, x, rows[i], r, cols[col // 2], n & v, off)
            if opt["digits"]:
                c.text(x, 186, ch, f["led"], self.FG)
        if opt["digits"]:
            for g in (1, 2):                               # Doppelpunkte zwischen den Gruppen
                x = x0 + (2 * g - 1) * step + (g - 1) * gap + step / 2 + gap / 2
                c.text(x, 184, ":", f["led"], self.DIM)
        return self._clock_finish(c)
