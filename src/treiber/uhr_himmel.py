"""Zifferblätter Astro-Uhr, Sonnenuhr, Planetenuhr, Weltzeituhr, Radaruhr."""
import math
import random
import datetime
import zoneinfo
from PIL import ImageFilter

_sky_SYNODIC = 29.530588853                   # synodischer Monat in Tagen
_sky_NEW_MOON = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc).timestamp()
_sky_BERLIN = (52.52, 13.405, "Berlin")
_sky_ZODIAC = [("♈", "Widder"), ("♉", "Stier"), ("♊", "Zwillinge"), ("♋", "Krebs"),
               ("♌", "Löwe"), ("♍", "Jungfrau"), ("♎", "Waage"), ("♏", "Skorpion"),
               ("♐", "Schütze"), ("♑", "Steinbock"), ("♒", "Wassermann"), ("♓", "Fische")]
_sky_PHASES = [                               # (bis Mondalter in Tagen, Name in Zeilen)
    (1.0, ("Neumond",)), (6.38, ("Zunehmende", "Sichel")), (8.38, ("Erstes", "Viertel")),
    (13.77, ("Zunehmender", "Mond")), (15.77, ("Vollmond",)), (21.15, ("Abnehmender", "Mond")),
    (23.15, ("Letztes", "Viertel")), (28.53, ("Abnehmende", "Sichel")), (99, ("Neumond",)),
]


def _sky_fonts():
    """Schriften der Himmels-Zifferblätter nach Rolle (clock_font hält sie im Zwischenspeicher)."""
    s = CLOCK_SS
    return {
        "cond": clock_font("sans-cond", 9 * s, True), "cond_s": clock_font("sans-cond", 8 * s),
        "val": clock_font("sans-cond", 14 * s, True), "glyph": clock_font("sans", 10 * s),
        "glyph_b": clock_font("sans", 11 * s, True), "num": clock_font("serif", 8 * s, True),
        "motto": clock_font("serif", 12 * s, True), "roman": clock_font("serif", 9 * s, True),
        "mono": clock_font("mono", 10 * s, True), "mono_s": clock_font("mono", 8 * s, True),
        "city": clock_font("sans-cond", 11 * s, True), "city_b": clock_font("sans-cond", 16 * s, True),
        "q": clock_font("sans", 20 * s, True),
        "r_val": clock_font("mono", 13, True),              # Radar: ohne Vergrößerung (Displaypixel)
    }


def _sky_sun(ts):
    """Sonnenstand nach NOAA: (Deklination in rad, Zeitgleichung in min, scheinbare ekliptikale Länge in °)."""
    jc = (ts / 86400 + 2440587.5 - 2451545) / 36525
    l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    m = math.radians(357.52911 + jc * (35999.05029 - 0.0001537 * jc))
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    center = (math.sin(m) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + math.sin(2 * m) * (0.019993 - 0.000101 * jc)
              + math.sin(3 * m) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * jc)
    lam = l0 + center - 0.00569 - 0.00478 * math.sin(omega)
    eps0 = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.asin(math.sin(eps) * math.sin(math.radians(lam)))
    y = math.tan(eps / 2) ** 2
    l0r = math.radians(l0)
    eot = 4 * math.degrees(y * math.sin(2 * l0r) - 2 * e * math.sin(m) + 4 * e * y * math.sin(m) * math.cos(2 * l0r)
                           - 0.5 * y * y * math.sin(4 * l0r) - 1.25 * e * e * math.sin(2 * m))
    return decl, eot, lam % 360


def _sky_solar_time(ts, lon):
    """Wahre Ortszeit (Sonnenzeit) in Minuten seit Mitternacht."""
    return ((ts % 86400) / 60 + _sky_sun(ts)[1] + 4 * lon) % 1440


def _sky_sun_dir(ts, lat, lon):
    """(Höhe in °, Richtung Ost, Richtung Nord) der Sonne; die Richtung ist ein Vektor der Länge cos(Höhe)."""
    decl, eot, _ = _sky_sun(ts)
    ha = math.radians(((ts % 86400) / 60 + eot + 4 * lon) / 4 - 180)
    phi = math.radians(lat)
    alt = math.asin(max(-1.0, min(1.0, math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(ha))))
    east = -math.cos(decl) * math.sin(ha)
    north = math.cos(phi) * math.sin(decl) - math.sin(phi) * math.cos(decl) * math.cos(ha)
    return math.degrees(alt), east, north


def _sky_events(day0, lat, lon, zenith=90.833):
    """Sonnenauf- und -untergang (UTC-Zeitstempel) am Tag, der um day0 (00:00 UTC) beginnt.
    Polartag → ("day", None), Polarnacht → ("night", None)."""
    phi = math.radians(lat)
    out = []
    for sign in (1, -1):                      # Aufgang, Untergang
        ts = day0 + (720 - 4 * lon) * 60
        for _ in range(3):                    # mit Deklination zum Ereigniszeitpunkt verfeinern
            decl, eot, _ = _sky_sun(ts)
            cos_h = (math.cos(math.radians(zenith)) / (math.cos(phi) * math.cos(decl) or 1e-9)
                     - math.tan(phi) * math.tan(decl))
            if cos_h > 1:
                return "night", None
            if cos_h < -1:
                return "day", None
            ha = math.degrees(math.acos(cos_h))
            ts = day0 + (720 - 4 * (lon + sign * ha) - eot) * 60
        out.append(ts)
    return out[0], out[1]


def _sky_day0(t):
    """00:00 UTC des lokalen Kalendertags von t."""
    lt = time.localtime(t)
    return datetime.datetime(lt.tm_year, lt.tm_mon, lt.tm_mday, tzinfo=datetime.timezone.utc).timestamp()


def _sky_moon(t):
    """(Mondalter in Tagen, Anteil am synodischen Monat 0…1, beleuchteter Anteil 0…1)."""
    age = ((t - _sky_NEW_MOON) / 86400) % _sky_SYNODIC
    frac = age / _sky_SYNODIC
    return age, frac, (1 - math.cos(2 * math.pi * frac)) / 2


def _sky_phase_name(age):
    for limit, name in _sky_PHASES:
        if age < limit:
            return name
    return ("Neumond",)


def _sky_moon_poly(cx, cy, r, frac, south=False, steps=40):
    """Umriss des beleuchteten Teils der Mondscheibe (Nordhalbkugel: zunehmend rechts hell)."""
    k = math.cos(2 * math.pi * frac)
    right, left = [], []
    for i in range(steps + 1):
        y = -r + 2 * r * i / steps
        w = math.sqrt(max(0.0, r * r - y * y))
        xl, xr = (w * k, w) if frac < 0.5 else (-w, -w * k)
        if south:
            xl, xr = -xr, -xl
        right.append((cx + xr, cy + y))
        left.append((cx + xl, cy + y))
    return right + left[::-1]


def _sky_hhmm(ts):
    lt = time.localtime(ts)
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}"


def _sky_grad(stops, v):
    """Farbe aus Farbstopps [(wert, farbe), …] (aufsteigend) für den Wert v."""
    if v <= stops[0][0]:
        return stops[0][1]
    for (v0, c0), (v1, c1) in zip(stops, stops[1:]):
        if v <= v1:
            return mix(c0, c1, (v - v0) / (v1 - v0))
    return stops[-1][1]


# Himmelsfarbe nach Sonnenhöhe (Nacht → astronomische, nautische, bürgerliche Dämmerung → Tag)
_sky_SKY_STOPS = [(-18, (8, 10, 28)), (-12, (18, 24, 62)), (-6, (44, 50, 112)), (-2.5, (150, 96, 120)),
                  (-0.8, (226, 140, 84)), (0.5, (120, 168, 218)), (15, (70, 138, 214)), (50, (44, 112, 206))]


class SkyFaces:
    # --- gemeinsame Hilfen ---------------------------------------------------- #
    def _sky_place(self):
        """(Breite, Länge, Name) aus den Wetter-Einstellungen, sonst Berlin."""
        w = self.settings.get("weather") if isinstance(self.settings, dict) else None
        try:
            lat, lon = float(w["lat"]), float(w["lon"])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, str(w.get("name") or "")
        except (TypeError, KeyError, ValueError):
            pass
        return _sky_BERLIN

    @staticmethod
    def _sky_fit(c, txt, fonts, maxw):
        """Erste Schrift aus fonts, in der txt höchstens maxw Displaypixel breit ist."""
        for f in fonts:
            if c.d.textlength(txt, font=f) <= maxw * CLOCK_SS:
                return f
        return fonts[-1]

    @staticmethod
    def _sky_trunc(c, txt, font, maxw):
        """txt, nötigenfalls mit „…“ gekürzt, sodass es höchstens maxw Displaypixel breit ist."""
        if c.d.textlength(txt, font=font) <= maxw * CLOCK_SS:
            return txt
        while txt and c.d.textlength(txt + "…", font=font) > maxw * CLOCK_SS:
            txt = txt[:-1]
        return txt.rstrip() + "…"

    def _sky_label(self, c, x, y, label, value, lab_col, val_col, maxw=56):
        f = _sky_fonts()
        c.text(x, y, label, self._sky_fit(c, label, [f["cond"], f["cond_s"]], maxw), lab_col)
        c.text(x, y + 14, value, self._sky_fit(c, value, [f["val"], f["city"], f["cond"]], maxw), val_col)

    # --- Astro-Uhr ------------------------------------------------------------ #
    @staticmethod
    def _sky_clockdeg(ts):
        """Winkel auf dem 24-Stunden-Ring (Mittag oben, im Uhrzeigersinn) für die Ortszeit von ts."""
        lt = time.localtime(ts)
        h = lt.tm_hour + lt.tm_min / 60 + lt.tm_sec / 3600
        return (h * 15 + 180) % 360

    def _sky_astro_static(self, c, t, lat, lon):
        """Hintergrund der Astro-Uhr für den Tag von t: Ring, Himmelsscheibe, Sterne, Auf-/Untergangsmarken."""
        f, cx, cy = _sky_fonts(), CLOCK_CX, CLOCK_CY
        s, gold, gold_d = CLOCK_SS, (214, 176, 98), (120, 94, 48)
        for r in range(112, 60, -4):                     # Schimmer hinter der Uhr
            c.circle(cx, cy, r, fill=mix((7, 9, 20), (22, 24, 44), (112 - r) / 52))
        c.circle(cx, cy, 102, fill=gold_d)             # 24-Stunden-Ring
        c.circle(cx, cy, 101, fill=(18, 20, 38))
        # Himmelsscheibe: je 6 Minuten Ortszeit die Farbe nach der Sonnenhöhe
        lt = time.localtime(t)
        alts = []
        for i in range(240):
            ts = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, i // 10, (i % 10) * 6 + 3, 0, 0, 0, -1))
            alt = _sky_sun_dir(ts, lat, lon)[0]
            alts.append(alt)
            a0 = (i * 1.5 + 180) % 360 - 90
            c.d.pieslice([(cx - 73) * s, (cy - 73) * s, (cx + 73) * s, (cy + 73) * s], a0, a0 + 1.7,
                         fill=_sky_grad(_sky_SKY_STOPS, alt))
        # Sterne im dunklen Teil
        rnd = random.Random(42)
        for _ in range(110):
            deg, rr, b = rnd.uniform(0, 360), 28 + 44 * math.sqrt(rnd.random()), rnd.uniform(0.35, 1)
            alt = alts[int(((deg - 180) % 360) / 1.5) % 240]
            if alt < -7:
                x, y = [v / s for v in c.pt(cx, cy, rr, deg)]
                col = mix(_sky_grad(_sky_SKY_STOPS, alt), (235, 238, 255), b * min(1, (-7 - alt) / 6))
                c.circle(x, y, 0.45 + 0.5 * b, fill=col)
        # Horizontmarken bei Sonnenauf- und -untergang
        rise, sset = _sky_events(_sky_day0(t), lat, lon)
        if rise not in ("day", "night"):
            for ev in (rise, sset):
                c.radial(cx, cy, 58, 73, self._sky_clockdeg(ev), 1.2, (250, 236, 200))
        c.circle(cx, cy, 73, outline=gold_d, width=1)
        c.circle(cx, cy, 101, outline=gold, width=0.8)
        c.circle(cx, cy, 88, outline=gold, width=0.8)
        for q in range(96):
            if q % 4:
                c.radial(cx, cy, 99, 101, q * 3.75, 0.5, gold_d)
        for h in range(24):
            deg = (h * 15 + 180) % 360
            c.radial(cx, cy, 98, 101, deg, 0.9, gold)
            x, y = [v / s for v in c.pt(cx, cy, 93.5, deg)]
            c.text(x, y, str(h or 24), f["num"], (240, 214, 150) if h % 6 == 0 else gold)

    def _sky_zodiac(self, c, cx, cy, sun_deg, sun_lon):
        """Tierkreisring: ekliptikale Länge wächst gegen den Uhrzeigersinn, die Sonne steht unter dem Sonnenzeiger."""
        f, s = _sky_fonts(), CLOCK_SS
        box = [(cx - 87) * s, (cy - 87) * s, (cx + 87) * s, (cy + 87) * s]
        cur = int(sun_lon // 30) % 12
        for k in range(12):
            d1 = sun_deg - (30 * k - sun_lon)             # Beginn des Zeichens
            fill = (196, 156, 78) if k == cur else ((30, 34, 60) if k % 2 else (24, 27, 50))
            c.d.arc(box, d1 - 30 - 90, d1 - 90, fill=fill, width=13 * s)
        for k in range(12):
            d1 = sun_deg - (30 * k - sun_lon)
            c.radial(cx, cy, 74, 87, d1, 0.7, (120, 94, 48))
            x, y = [v / s for v in c.pt(cx, cy, 80.5, d1 - 15)]
            c.text(x, y + 0.4, _sky_ZODIAC[k][0], f["glyph_b"] if k == cur else f["glyph"],
                   (28, 20, 8) if k == cur else (170, 150, 110))
        c.circle(cx, cy, 87, outline=(120, 94, 48), width=0.8)

    def _sky_moon_textures(self, r):
        """Mondscheibe hell und dunkel (mit Meeren), Größe 2r vergrößert, und Kreismaske."""
        return self._clock_cache("sky_moontex", r, lambda: self._sky_moon_build(r))

    @staticmethod
    def _sky_moon_build(r):
        n = int(2 * r * CLOCK_SS)
        rnd = random.Random(7)
        maria = [(0.30, -0.35, 0.28), (-0.05, -0.30, 0.22), (0.25, 0.10, 0.26), (-0.30, 0.05, 0.18),
                 (-0.15, 0.40, 0.16), (0.45, -0.05, 0.14), (0.05, 0.02, 0.12)]
        out = []
        for base, sea in (((232, 228, 208), (176, 172, 158)), ((44, 48, 66), (34, 38, 54))):
            img = Image.new("RGB", (n, n), base)
            d = ImageDraw.Draw(img)
            for mx, my, mr in maria:
                d.ellipse([(0.5 + mx - mr) * n, (0.5 + my - mr) * n, (0.5 + mx + mr) * n, (0.5 + my + mr) * n],
                          fill=sea)
            img = img.filter(ImageFilter.GaussianBlur(n / 30))
            d = ImageDraw.Draw(img)
            for _ in range(14):                       # kleine Krater
                x, y, cr = rnd.uniform(0.15, 0.85), rnd.uniform(0.15, 0.85), rnd.uniform(0.012, 0.035)
                d.ellipse([(x - cr) * n, (y - cr) * n, (x + cr) * n, (y + cr) * n], outline=mix(base, sea, 0.8),
                          width=max(1, n // 90))
            out.append(img)
        mask = Image.new("L", (n, n), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, n - 1, n - 1], fill=255)
        return out[0], out[1], mask

    def _sky_moon_big(self, c, cx, cy, r, frac, south):
        lit, dark, mask = self._sky_moon_textures(r)
        s, n = CLOCK_SS, lit.size[0]
        pos = (int(round((cx - r) * s)), int(round((cy - r) * s)))
        c.img.paste(dark, pos, mask)
        lm = Image.new("L", (n, n), 0)
        ImageDraw.Draw(lm).polygon(_sky_moon_poly(n / 2, n / 2, n / 2 - 0.5, frac, south, 60), fill=255)
        c.img.paste(lit, pos, lm)

    def _sky_moon_small(self, c, x, y, r, frac, south):
        s = CLOCK_SS
        c.circle(x, y, r + 0.8, fill=(12, 14, 26))
        c.circle(x, y, r, fill=(52, 56, 74))
        c.d.polygon([(px * s, py * s) for px, py in _sky_moon_poly(x, y, r, frac, south, 16)], fill=(236, 232, 214))

    @clock_face("astro", fps=1)
    def face_astro(self, profile):
        f = _sky_fonts()
        t = self._clock_now()
        lat, lon, place = self._sky_place()
        lt = time.localtime(t)
        key = ("sky_astro", lt.tm_year, lt.tm_yday, round(lat, 3), round(lon, 3))
        c = self._clock_canvas(key, (7, 9, 20), lambda c: self._sky_astro_static(c, t, lat, lon))
        cx, cy, s = CLOCK_CX, CLOCK_CY, CLOCK_SS
        gold, dim, white = (214, 176, 98), (128, 136, 160), (236, 232, 220)
        _, _, sun_lon = _sky_sun(t)
        age, frac, lit = _sky_moon(t)
        south = lat < 0
        sun_deg = self._sky_clockdeg(t)
        moon_deg = (sun_deg - frac * 360) % 360          # Mond bleibt pro Tag um Mondalter·360° hinter der Sonne
        self._sky_zodiac(c, cx, cy, sun_deg, sun_lon)
        # Zeiger: Mond (silbern) und Sonne (golden)
        c.hand(cx, cy, moon_deg, [(24, 2.2), (86, 1.2)], (170, 176, 196))
        c.hand(cx, cy, sun_deg, [(24, 3.0), (80, 2.2), (87, 0.8)], gold)
        mx, my = [v / s for v in c.pt(cx, cy, 94.5, moon_deg)]
        self._sky_moon_small(c, mx, my, 5.6, frac, south)
        sx, sy = [v / s for v in c.pt(cx, cy, 94.5, sun_deg)]
        for k in range(12):                              # Sonnenstrahlen
            c.hand(sx, sy, k * 30 + 15, [(4.5, 1.8), (8.6, 0)], (255, 206, 90))
        c.circle(sx, sy, 5.6, fill=(255, 196, 60), outline=(150, 96, 20), width=0.7)
        c.circle(sx - 1.2, sy - 1.2, 2.2, fill=(255, 236, 160))
        # Mitte: Mondphase
        c.circle(cx, cy, 25.5, fill=(10, 12, 24))
        self._sky_moon_big(c, cx, cy, 23, frac, south)
        c.circle(cx, cy, 25.5, outline=gold, width=1)
        # Seitentexte
        rise, sset = _sky_events(_sky_day0(t), lat, lon)
        if rise == "day":
            r_txt, s_txt, day_len = "—", "—", "24:00 h"
            self._sky_label(c, 29, 132, "POLARTAG", day_len, dim, white)
        elif rise == "night":
            r_txt, s_txt, day_len = "—", "—", "0:00 h"
            self._sky_label(c, 29, 132, "POLARNACHT", day_len, dim, white)
        else:
            r_txt, s_txt = _sky_hhmm(rise), _sky_hhmm(sset)
            mins = int(round((sset - rise) / 60))
            self._sky_label(c, 29, 132, "TAGESLÄNGE", f"{mins // 60}:{mins % 60:02d} h", dim, white)
        self._sky_label(c, 29, 28, "AUFGANG", r_txt, dim, (255, 206, 110))
        self._sky_label(c, 29, 80, "UNTERGANG", s_txt, dim, (240, 150, 90))
        c.text(29, 196, self._sky_trunc(c, place, f["cond_s"], 56), f["cond_s"], (90, 98, 124))
        c.text(291, 28, "MOND", f["cond"], dim)
        name = _sky_phase_name(age)
        for i, line in enumerate(name):
            c.text(291, 42 + i * 11 + (5 if len(name) == 1 else 0), line,
                   self._sky_fit(c, line, [f["cond"], f["cond_s"]], 58), white)
        c.text(291, 80, "BELEUCHTET", self._sky_fit(c, "BELEUCHTET", [f["cond"], f["cond_s"]], 56), dim)
        c.text(291, 94, f"{round(lit * 100)} %", f["val"], (206, 212, 236))
        sign, sname = _sky_ZODIAC[int(sun_lon // 30) % 12]
        c.text(291, 132, "SONNE IM", f["cond"], dim)
        c.text(291, 146, sign + " " + sname, self._sky_fit(c, sign + " " + sname, [f["cond"], f["cond_s"]], 58), gold)
        c.text(291, 196, f"{lt.tm_mday:02d}.{lt.tm_mon:02d}. {lt.tm_hour:02d}:{lt.tm_min:02d}", f["cond_s"],
               (90, 98, 124))
        return self._clock_finish(c)

    # --- Sonnenuhr ------------------------------------------------------------ #
    _sky_SD = (CLOCK_CX, 94, 86, 0.8, 0.24, -0.50)      # Mitte x/y, Plattenradius, Stauchung, Höhe → Bild (x, y)

    def _sky_sd_pt(self, x, y, z=0.0):
        """Punkt der Platte (x Ost, y Nord, z Höhe; Displaypixel) → vergrößerte Bildkoordinaten."""
        cx, cy, _, sy, kx, ky = self._sky_SD
        return ((cx + x + z * kx) * CLOCK_SS, (cy - y * sy + z * ky) * CLOCK_SS)

    def _sky_sd_ellipse(self, c, r, dy=0.0, **kw):
        cx, cy, _, sy, _, _ = self._sky_SD
        s = CLOCK_SS
        c.d.ellipse([(cx - r) * s, (cy - r * sy + dy) * s, (cx + r) * s, (cy + r * sy + dy) * s], **kw)

    def _sky_sd_geometry(self, lat):
        """Fußpunkt, Stablänge, Stabhöhe und Richtung der Stundenlinie zur Stunde h (Sonnenzeit)."""
        _, _, R, _, _, _ = self._sky_SD
        phi = math.radians(max(1.0, min(80.0, abs(lat))))
        sgn = 1 if lat >= 0 else -1                    # Südhalbkugel: Süden oben, Stunden gespiegelt
        foot, length = (0.0, -0.30 * R), 0.62 * R
        height = min(1.1 * R, length * math.tan(phi))

        def ray(h):
            ha = math.radians(15 * (h - 12))
            th = math.atan2(math.sin(phi) * math.sin(ha), math.cos(ha))   # tan θ = sin φ · tan(15°·(h−12))
            return sgn * math.sin(th), math.cos(th)
        return foot, length, height, ray

    @staticmethod
    def _sky_ray_circle(foot, u, rho):
        """Abstand vom Fußpunkt entlang u bis zum Kreis mit Radius rho um die Plattenmitte."""
        b = foot[0] * u[0] + foot[1] * u[1]
        return -b + math.sqrt(max(0.0, b * b - (foot[0] ** 2 + foot[1] ** 2) + rho * rho))

    def _sky_sundial_static(self, lat, lon):
        f = _sky_fonts()
        cx, cy, R, sy, _, _ = self._sky_SD
        s = CLOCK_SS
        c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), (14, 20, 17)))
        for k in range(24):                             # Hintergrund: dunkler Garten, unten heller
            c.rect(0, CLOCK_H * k / 24, WIDTH, CLOCK_H * (k + 1) / 24 + 1,
                   fill=mix((10, 14, 16), (26, 36, 28), k / 23))
        # Steinsockel (Zylinder) mit Körnung
        rs, depth = R * 1.13, 15
        for k in range(int(rs * 2)):                   # Seitenfläche, seitlich schattiert
            x = cx - rs + k
            light = 0.55 + 0.45 * math.cos((k / (2 * rs) - 0.35) * math.pi)
            col = mix((52, 50, 46), (128, 124, 116), max(0.0, light))
            yb = cy + 2 + rs * sy * math.sqrt(max(0.0, 1 - ((x - cx) / rs) ** 2))
            c.rect(x, cy + 2, x + 1.2, yb + depth, fill=col)
        self._sky_sd_ellipse(c, rs, 2, fill=(138, 134, 124))
        rnd = random.Random(42)
        for _ in range(420):
            a, rr = rnd.uniform(0, 2 * math.pi), rs * math.sqrt(rnd.random())
            x, y = cx + rr * math.cos(a), cy + 2 + rr * math.sin(a) * sy
            g = rnd.choice(((118, 114, 106), (156, 152, 142), (104, 100, 94)))
            c.circle(x, y, rnd.uniform(0.3, 0.8), fill=g)
        self._sky_sd_ellipse(c, rs, 2, outline=(170, 166, 156), width=s)
        # Bronzeplatte: Dicke, Farbverlauf, Rand
        self._sky_sd_ellipse(c, R, 3.5, fill=(80, 54, 24))
        for k in range(30):
            t = k / 29
            self._sky_sd_ellipse(c, R * (1 - t * 0.98), -t * 4, fill=mix((132, 94, 44), (196, 152, 82), t ** 0.7))
        self._sky_sd_ellipse(c, R, 0, outline=(222, 184, 112), width=s)
        ink, hi = (74, 50, 22), (226, 190, 120)
        for rho in (0.95 * R, 0.74 * R):                 # Ziffernring
            self._sky_sd_ellipse(c, rho, 0.6, outline=hi, width=2)
            self._sky_sd_ellipse(c, rho, 0, outline=ink, width=4)
        foot, length, height, ray = self._sky_sd_geometry(lat)

        def engrave(p0, p1, w):
            c.d.line([(p0[0], p0[1] + 0.7 * s), (p1[0], p1[1] + 0.7 * s)], fill=hi, width=max(1, round(w * 0.6 * s)))
            c.d.line([p0, p1], fill=ink, width=max(1, round(w * s)))
        for q in range(6 * 4, 18 * 4 + 1):               # Viertelstunden, halbe und volle Stunden
            h = q / 4
            u = ray(h)
            end = self._sky_ray_circle(foot, u, 0.74 * R)
            if q % 4 == 0:
                start, w = 7, 1.4
            elif q % 2 == 0:
                start, w = end * 0.55, 0.8
            else:
                start, w = end - 4, 0.6
            engrave(self._sky_sd_pt(foot[0] + u[0] * start, foot[1] + u[1] * start),
                    self._sky_sd_pt(foot[0] + u[0] * end, foot[1] + u[1] * end), w)
            if q % 4 == 0:
                d = self._sky_ray_circle(foot, u, 0.845 * R)
                x, y = self._sky_sd_pt(foot[0] + u[0] * d, foot[1] + u[1] * d)
                c.d.text((x, y + 0.6 * s), ROMAN_XII[int(h) % 12], font=f["roman"], fill=hi, anchor="mm")
                c.d.text((x, y), ROMAN_XII[int(h) % 12], font=f["roman"], fill=ink, anchor="mm")
        # Spruch und Breite im südlichen Teil
        for txt, font, yy in (("CARPE DIEM", f["motto"], -0.47 * R), (self._sky_latlon(lat, lon), f["cond_s"], -0.64 * R)):
            x, y = self._sky_sd_pt(0, yy)
            c.d.text((x, y + 0.7 * s), txt, font=font, fill=hi, anchor="mm")
            c.d.text((x, y), txt, font=font, fill=ink, anchor="mm")
        fx, fy = self._sky_sd_pt(*foot)
        c.d.ellipse([fx - 3 * s, fy - 2 * s, fx + 3 * s, fy + 2 * s], fill=ink)
        return c.img

    @staticmethod
    def _sky_latlon(lat, lon):
        return (f"{abs(lat):.1f}° {'N' if lat >= 0 else 'S'} · {abs(lon):.1f}° {'O' if lon >= 0 else 'W'}"
                .replace(".", ","))

    def _sky_sundial_images(self, lat, lon):
        """Tagbild, Schattenbild (dunkler) und Nachtbild der Platte sowie die Maske der Steinoberfläche."""
        day = self._sky_sundial_static(lat, lon)
        arr = np.asarray(day).astype(np.float32)
        shade = Image.fromarray((arr * np.array([0.50, 0.50, 0.56], np.float32)).astype(np.uint8))
        night = Image.fromarray(np.clip(arr * np.array([0.21, 0.28, 0.47], np.float32) + np.array([2, 4, 10], np.float32), 0, 255).astype(np.uint8))
        surf = Image.new("L", day.size, 0)
        cx, cy, R, sy, _, _ = self._sky_SD
        s, rs = CLOCK_SS, R * 1.13
        ImageDraw.Draw(surf).ellipse([(cx - rs) * s, (cy + 2 - rs * sy) * s, (cx + rs) * s, (cy + 2 + rs * sy) * s],
                                     fill=255)
        return day, shade, night, np.asarray(surf)

    def _sky_gnomon(self, c, foot, length, height, lit, night):
        """Dreieckiger Schattenstab; lit: 1 = Ostseite in der Sonne, 0 = im Schatten."""
        b = (foot[0], foot[1] + length)
        p_f, p_b, p_a = self._sky_sd_pt(*foot), self._sky_sd_pt(*b), self._sky_sd_pt(b[0], b[1], height)
        face = mix((110, 76, 34), (214, 170, 96), lit)
        edge = (240, 206, 140)
        if night:
            face, edge = mix(face, (30, 34, 52), 0.7), (96, 100, 124)
        s = CLOCK_SS
        c.d.polygon([(p_f[0] - 1.2 * s, p_f[1]), (p_b[0] - 1.2 * s, p_b[1]), (p_a[0] - 1.2 * s, p_a[1])],
                    fill=mix(face, (20, 14, 6), 0.55))
        c.d.polygon([p_f, p_b, p_a], fill=face)
        c.d.line([p_f, p_a], fill=edge, width=round(1.1 * s))
        c.d.line([p_b, p_a], fill=mix(face, (30, 20, 8), 0.4), width=s)

    @clock_face("sundial", fps=1)
    def face_sundial(self, profile):
        f = _sky_fonts()
        t = self._clock_now()
        lat, lon, place = self._sky_place()
        day, shade, night, surf = self._clock_cache("sky_sundial", (round(lat, 3), round(lon, 3)),
                                                    lambda: self._sky_sundial_images(lat, lon))
        alt, east, north = _sky_sun_dir(t, lat, lon)
        foot, length, height, _ = self._sky_sd_geometry(lat)
        is_night = alt <= 0.0
        lt = time.localtime(t)
        dim, white, warm = (128, 138, 130), (236, 232, 220), (240, 200, 120)
        if is_night:
            c = _Canvas(night.copy())
        else:
            c = _Canvas(day.copy())
            sgn = 1 if lat >= 0 else -1
            dx, dy = -sgn * east, -sgn * north             # Schattenrichtung auf der Platte
            k = min(3.2 * self._sky_SD[2], height / max(math.sin(math.radians(alt)), 1e-3))
            norm = math.hypot(dx, dy) or 1.0
            b = (foot[0], foot[1] + length)
            tip = (b[0] + dx / norm * k * math.cos(math.radians(alt)), b[1] + dy / norm * k * math.cos(math.radians(alt)))
            mask = Image.new("L", c.img.size, 0)
            strength = int(255 * min(1.0, 0.35 + alt / 8))
            ImageDraw.Draw(mask).polygon([self._sky_sd_pt(*foot), self._sky_sd_pt(*b), self._sky_sd_pt(*tip)],
                                         fill=strength)
            box = mask.getbbox()
            if box:
                pad = 12
                box = (max(0, box[0] - pad), max(0, box[1] - pad), min(mask.size[0], box[2] + pad),
                       min(mask.size[1], box[3] + pad))
                mask.paste(mask.crop(box).filter(ImageFilter.GaussianBlur(2.2 * CLOCK_SS / 2)), box[:2])
                mask = Image.fromarray(np.minimum(np.asarray(mask), surf))
                c.img = Image.composite(shade, c.img, mask)
                c.d = ImageDraw.Draw(c.img)
        self._sky_gnomon(c, foot, length, height, 1.0 if (east > 0) == (lat >= 0) else 0.25, is_night)
        # Seitentexte
        st = _sky_solar_time(t, lon)
        self._sky_label(c, 29, 44, "SONNENZEIT", f"{int(st // 60):02d}:{int(st % 60):02d}", dim, warm)
        eot = _sky_sun(t)[1]
        sec = int(round(abs(eot) * 60))
        self._sky_label(c, 29, 104, "ZEITGL.", f"{'+' if eot >= 0 else '−'}{sec // 60}:{sec % 60:02d}", dim, white)
        self._sky_label(c, 291, 44, "UHRZEIT", f"{lt.tm_hour:02d}:{lt.tm_min:02d}", dim, white)
        self._sky_label(c, 291, 104, "SOMMERZEIT" if lt.tm_isdst > 0 else "WINTERZEIT",
                        f"{lt.tm_mday:02d}.{lt.tm_mon:02d}.", dim, white)
        if is_night:
            rise, _ = _sky_events(_sky_day0(t), lat, lon)
            if rise == "night":
                msg = "Die Sonnenuhr ruht – Polarnacht"
            else:
                if rise == "day" or rise < t:
                    rise, _ = _sky_events(_sky_day0(t) + 86400, lat, lon)
                msg = "Die Sonnenuhr ruht – Sonnenaufgang " + (_sky_hhmm(rise) if rise not in ("day", "night") else "—")
            c.text(CLOCK_CX, 203, msg, f["cond"], (150, 164, 200))
        else:
            c.text(CLOCK_CX, 203, self._sky_trunc(c, place or "", f["cond_s"], 200), f["cond_s"], dim)
        return self._clock_finish(c)

    # --- Planetenuhr ---------------------------------------------------------- #
    _sky_ORBITS = ((52, 19), (94, 34), (140, 51))   # Halbachsen: Stunden, Minuten, Sekunden
    _sky_PC = (CLOCK_CX, 106)                            # Sonne

    def _sky_orbit_pt(self, k, deg):
        (a, b), (cx, cy) = self._sky_ORBITS[k], self._sky_PC
        rad = math.radians(deg)
        return cx + a * math.sin(rad), cy - b * math.cos(rad), -math.cos(rad)

    def _sky_orbit_marks(self, c, front):
        """Umlaufbahnen (vordere oder hintere Hälfte) mit Teilungspunkten."""
        cx, cy = self._sky_PC
        s = CLOCK_SS
        for k, (a, b) in enumerate(self._sky_ORBITS):
            col = (92, 104, 140) if front else (50, 58, 84)
            c.d.arc([(cx - a) * s, (cy - b) * s, (cx + a) * s, (cy + b) * s], 0 if front else 180,
                     180 if front else 360, fill=col, width=round(0.8 * s))
            for m in range(12):
                x, y, depth = self._sky_orbit_pt(k, m * 30)
                if (depth > 0) == front or abs(depth) < 1e-9 and front:
                    big = m % 3 == 0
                    c.circle(x, y, (1.5 if big else 0.9) * (1 + 0.15 * depth),
                             fill=mix(col, (220, 226, 250), 0.5 if big else 0.2))

    def _sky_planets_static(self):
        s = CLOCK_SS
        w, h = WIDTH * s, CLOCK_H * s
        img = Image.new("RGB", (w, h), (4, 5, 12))
        neb = Image.new("RGB", (w // 4, h // 4), (0, 0, 0))    # Nebelschleier, weich gezeichnet
        nd = ImageDraw.Draw(neb)
        for x, y, rx, ry, col in ((60, 40, 70, 30, (40, 16, 60)), (270, 170, 80, 36, (12, 30, 58)),
                                  (230, 30, 50, 22, (40, 20, 44)), (40, 180, 60, 26, (10, 34, 44))):
            nd.ellipse([(x - rx) * s / 4, (y - ry) * s / 4, (x + rx) * s / 4, (y + ry) * s / 4], fill=col)
        neb = neb.filter(ImageFilter.GaussianBlur(9)).resize((w, h), Image.BILINEAR)
        img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16) + np.asarray(neb), 0, 255).astype(np.uint8))
        c = _Canvas(img)
        rnd = random.Random(42)
        for _ in range(170):
            x, y, b = rnd.uniform(0, WIDTH), rnd.uniform(0, CLOCK_H), rnd.random() ** 2.2
            tint = rnd.choice(((255, 255, 255), (200, 216, 255), (255, 232, 200)))
            c.circle(x, y, 0.35 + 0.8 * b, fill=mix((30, 34, 50), tint, 0.35 + 0.65 * b))
            if b > 0.8:                                          # helle Sterne mit Kreuzschein
                c.radial(x, y, -3, 3, 0, 0.3, mix((20, 22, 34), tint, 0.5))
                c.radial(x, y, -3, 3, 90, 0.3, mix((20, 22, 34), tint, 0.5))
        self._sky_orbit_marks(c, False)
        # Sonne mit Glühen als RGBA-Bild
        n = 50 * s * 2
        glow = Image.new("L", (n, n), 0)
        gd = ImageDraw.Draw(glow)
        for r in range(50 * s, 0, -s):
            gd.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r], fill=int(200 * (1 - r / (50 * s)) ** 2.2))
        sun = Image.new("RGBA", (n, n), (255, 170, 60, 0))
        sun.putalpha(glow)
        sd = ImageDraw.Draw(sun)
        for r in range(15 * s, 0, -s):
            t = r / (15 * s)
            col = mix((255, 250, 220), (255, 150, 30), t ** 1.6)
            sd.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r], fill=col + (255,))
        return img, sun

    def _sky_planet(self, c, x, y, r, dark, light, spot=None):
        """Kugel, von der Sonne her beleuchtet."""
        cx, cy = self._sky_PC
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        c.circle(x, y, r + 1.6, fill=mix(dark, (4, 5, 12), 0.72))
        c.circle(x, y, r, fill=dark)
        c.circle(x + ux * r * 0.28, y + uy * r * 0.28, r * 0.74, fill=light)
        if spot:
            c.circle(x + ux * r * 0.18 - 0.25 * r, y + uy * r * 0.18 + 0.2 * r, r * 0.28, fill=spot)
        c.circle(x + ux * r * 0.48, y + uy * r * 0.48, r * 0.25, fill=mix(light, (255, 255, 255), 0.55))

    @clock_face("planets", fps=5)
    def face_planets(self, profile):
        f = _sky_fonts()
        bg, sun = self._clock_cache("sky_planets", 1, self._sky_planets_static)
        c = _Canvas(bg.copy())
        t = self._clock_now()
        lt = time.localtime(t)
        sec = lt.tm_sec + (t % 1)
        minute = lt.tm_min + sec / 60
        hour = lt.tm_hour % 12 + minute / 60
        s, (cx, cy) = CLOCK_SS, self._sky_PC
        bodies = []                                              # (Tiefe, Zeichenfunktion)
        # Stundenplanet (rot), Minutenplanet (blau, mit Mond), Sekundenplanet (golden, mit Ring)
        x, y, dep = self._sky_orbit_pt(0, hour * 30)
        bodies.append((dep, lambda x=x, y=y, dep=dep: self._sky_planet(
            c, x, y, 6.5 * (1 + 0.14 * dep), (96, 34, 20), (222, 110, 64), (170, 70, 40))))
        x, y, dep = self._sky_orbit_pt(1, minute * 6)
        mdeg = math.radians(t % 20 * 18)                         # Mond: ein Umlauf in 20 s
        mx, my, mdep = x + 15 * math.sin(mdeg), y - 5.5 * math.cos(mdeg), dep - 0.3 * math.cos(mdeg)
        bodies.append((dep, lambda x=x, y=y, dep=dep: self._sky_planet(
            c, x, y, 8 * (1 + 0.14 * dep), (20, 50, 110), (70, 140, 230), (90, 170, 110))))
        bodies.append((mdep, lambda: self._sky_planet(c, mx, my, 2.4, (80, 80, 88), (214, 214, 220))))
        x, y, dep = self._sky_orbit_pt(2, sec * 6)

        def saturn(x=x, y=y, dep=dep):
            r = 5.6 * (1 + 0.14 * dep)
            box = [(x - 2.3 * r) * s, (y - 0.75 * r) * s, (x + 2.3 * r) * s, (y + 0.75 * r) * s]
            c.d.arc(box, 180, 360, fill=(170, 150, 110), width=round(1.1 * s))
            self._sky_planet(c, x, y, r, (110, 86, 40), (236, 204, 132))
            c.d.arc(box, 0, 180, fill=(226, 204, 150), width=round(1.1 * s))
        bodies.append((dep, saturn))
        bodies.sort(key=lambda b: b[0])
        for dep, draw in bodies:
            if dep <= 0:
                draw()
        n = sun.size[0]
        c.img.paste(sun, (int(cx * s - n / 2), int(cy * s - n / 2)), sun)
        self._sky_orbit_marks(c, True)
        for dep, draw in bodies:
            if dep > 0:
                draw()
        # Legende und Uhrzeit dezent in den Ecken
        for i, (col, txt) in enumerate((((222, 110, 64), "STD"), ((70, 140, 230), "MIN"), ((236, 204, 132), "SEK"))):
            c.circle(8, 10 + i * 11, 2.6, fill=col)
            c.d.text((14 * s, (10 + i * 11) * s), txt, font=f["cond_s"], fill=(110, 118, 146), anchor="lm")
        c.d.text((312 * s, 204 * s), f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}", font=f["mono"],
                 fill=(120, 130, 160), anchor="rm")
        return self._clock_finish(c)

    # --- Weltzeituhr ---------------------------------------------------------- #
    def _sky_world_cities(self):
        """Städte aus der Option (höchstens 6; leer/ungültig → Standardliste) mit Zeitzone oder None."""
        raw = self._copt("world").get("cities")
        cities = [x for x in raw if isinstance(x, dict) and x.get("tz")] if isinstance(raw, list) else []
        if not cities:
            cities = next(o["default"] for o in CLOCK_OPTIONS["world"] if o["key"] == "cities")
        out = []
        for city in cities[:6]:
            try:
                tz = zoneinfo.ZoneInfo(str(city["tz"]))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError, TypeError, OSError):
                tz = None
            out.append((str(city.get("name") or city["tz"]), str(city["tz"]), tz))
        return out

    @staticmethod
    def _sky_world_grid(n):
        """Zellen (Mitte x, Mitte y, Breite, Höhe) für n Städte."""
        rows = [[1], [2], [3], [2, 2], [3, 2], [3, 3]][max(1, n) - 1]
        h = CLOCK_H / len(rows)
        cells = []
        for r, cols in enumerate(rows):
            w = WIDTH / (3 if n >= 5 else cols)
            x0 = (WIDTH - cols * w) / 2
            cells += [(x0 + (k + 0.5) * w, (r + 0.5) * h, w, h) for k in range(cols)]
        return cells[:n]

    @staticmethod
    def _sky_world_layout(x, y, w, h):
        """(Radius, Mitte y des Zifferblatts, y des Namens, y der Zeitzeile, groß?) – Block senkrecht mittig."""
        r = min(w * 0.34, (h - 38) / 2)
        big = r > 50
        name_off, time_off = (16, 36) if big else (10, 23)
        top = y - (2 * r + time_off + 7) / 2
        return r, top + r, top + 2 * r + name_off, top + 2 * r + time_off, big

    def _sky_world_static(self, c, cities, days):
        """Hintergrund der Weltzeituhr: je Stadt Feld, Zifferblatt (Tag/Nacht) und Name."""
        f = _sky_fonts()
        cells = self._sky_world_grid(len(cities))
        for (name, _, tz), (x, y, w, h), day in zip(cities, cells, days):
            c.rect(x - w / 2 + 2, y - h / 2 + 2, x + w / 2 - 2, y + h / 2 - 2, fill=(16, 20, 32))
            r, dy, ny, _, big = self._sky_world_layout(x, y, w, h)
            if tz is None:
                face, ink, rim = (40, 42, 50), (140, 144, 156), (70, 74, 86)
            elif day:
                face, ink, rim = (238, 234, 222), (40, 42, 50), (150, 154, 166)
            else:
                face, ink, rim = (26, 34, 64), (190, 200, 230), (70, 84, 130)
            c.circle(x, dy, r + 1.5, fill=rim)
            c.circle(x, dy, r, fill=face)
            for m in range(60 if r > 40 else 12):
                big = m % (5 if r > 40 else 1) == 0
                if big or r > 40:
                    step = 360 / (60 if r > 40 else 12)
                    c.radial(x, dy, r * (0.80 if big else 0.9), r * 0.96, m * step, (1.4 if big else 0.5) * max(1, r / 40),
                             ink)
            if tz is None:
                c.text(x, dy, "?", f["q"], ink)
            elif day:                                           # Sonne bzw. Mond im Zifferblatt
                c.circle(x, dy + r * 0.45, max(2, r * 0.11), fill=(250, 190, 60))
            else:
                c.circle(x, dy + r * 0.45, max(2, r * 0.11), fill=(230, 226, 200))
                c.circle(x + r * 0.05, dy + r * 0.42, max(2, r * 0.11), fill=face)
            font = f["city_b"] if big else f["city"]
            c.text(x, ny, self._sky_trunc(c, name, font, w - 8), font, (230, 232, 240))

    @clock_face("world", fps=1)
    def face_world(self, profile):
        f = _sky_fonts()
        t = self._clock_now()
        cities = self._sky_world_cities()
        local = datetime.datetime.fromtimestamp(t).date()
        nows = [datetime.datetime.fromtimestamp(t, tz) if tz else None for _, _, tz in cities]
        days = tuple(bool(n and 6 <= n.hour < 18) for n in nows)
        key = ("sky_world", tuple(z for _, z, _ in cities), tuple(n for n, _, _ in cities), days)
        c = self._clock_canvas(key, (10, 13, 22), lambda c: self._sky_world_static(c, cities, days))
        acc = PROFILE_COLOR.get(profile, self.FG)
        for _, (x, y, w, h), now, day in zip(cities, self._sky_world_grid(len(cities)), nows, days):
            r, dy, _, ty, big = self._sky_world_layout(x, y, w, h)
            if now is None:
                c.text(x, ty, "unbekannte Zone", f["cond_s"], (170, 120, 120))
                continue
            ink = (30, 32, 40) if day else (220, 226, 245)
            ha = (now.hour % 12 + now.minute / 60) * 30
            ma = (now.minute + now.second / 60) * 6
            c.hand(x, dy, ha, [(-r * 0.12, r * 0.12), (r * 0.45, r * 0.10), (r * 0.56, 0)], ink)
            c.hand(x, dy, ma, [(-r * 0.14, r * 0.09), (r * 0.74, r * 0.06), (r * 0.84, 0)], ink)
            c.hand(x, dy, now.second * 6, [(-r * 0.2, max(0.7, r * 0.03)), (r * 0.86, max(0.5, r * 0.02))], acc)
            c.circle(x, dy, max(1.6, r * 0.07), fill=acc)
            off = now.utcoffset().total_seconds() / 60
            sign, off = ("+" if off >= 0 else "−"), abs(int(off))
            utc = f"UTC{sign}{off // 60}" + (f":{off % 60:02d}" if off % 60 else "")
            txt = f"{now.hour:02d}:{now.minute:02d}"
            tfont, ufont = (f["val"], f["cond"]) if big else (f["city"], f["cond_s"])
            tw = c.d.textlength(txt, font=tfont) / CLOCK_SS
            uw = c.d.textlength(utc, font=ufont) / CLOCK_SS
            x0 = x - (tw + 5 + uw) / 2
            c.d.text((x0 * CLOCK_SS, ty * CLOCK_SS), txt, font=tfont, fill=(236, 232, 220), anchor="lm")
            c.d.text(((x0 + tw + 5) * CLOCK_SS, ty * CLOCK_SS), utc, font=ufont, fill=(130, 138, 160), anchor="lm")
            diff = (now.date() - local).days
            if diff:                                          # anderer Kalendertag als hier
                bx, by = x + r * 0.92, dy - r * 0.86
                c.d.rounded_rectangle([(bx - 9) * CLOCK_SS, (by - 6) * CLOCK_SS, (bx + 9) * CLOCK_SS,
                                       (by + 6) * CLOCK_SS], radius=3 * CLOCK_SS, fill=acc,
                                      outline=(16, 20, 32), width=CLOCK_SS)
                c.text(bx, by, ("+" if diff > 0 else "−") + str(abs(diff)), f["cond"], (255, 255, 255))
        return self._clock_finish(c)

    # --- Radaruhr ------------------------------------------------------------- #
    _sky_RC = (108, CLOCK_CY, 99)                      # Mitte x/y und Radius des Schirms (Displaypixel)
    _sky_R_ROWS = (("ZEIT", 22), ("DATUM", 62), ("PEILUNG", 102), ("ZIEL STD", 142), ("ZIEL MIN", 180))

    def _sky_radar_static(self):
        """Schirm und Pult einmal zeichnen (vergrößert), verkleinert als Zahlenfeld."""
        f = _sky_fonts()
        cx, cy, R = self._sky_RC
        c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), (20, 23, 22)))
        for k in range(20):                                      # gebürstetes Pult
            c.rect(0, CLOCK_H * k / 20, WIDTH, CLOCK_H * (k + 1) / 20 + 1, fill=mix((30, 34, 32), (16, 19, 18), k / 19))
        c.circle(cx, cy, R + 6.5, fill=(52, 58, 55))
        c.circle(cx, cy, R + 5, fill=(34, 38, 36))
        c.circle(cx, cy, R + 2, fill=(4, 8, 6))
        for r in range(int(R), 0, -3):                           # Schirm, in der Mitte etwas heller
            c.circle(cx, cy, r, fill=mix((0, 30, 12), (1, 11, 5), (r / R) ** 1.5))
        line, faint = (20, 110, 52), (10, 62, 30)
        for k in (0.25, 0.5, 0.75, 1.0):
            c.circle(cx, cy, R * k, outline=line if k in (0.5, 1.0) else faint, width=0.7)
        for deg in (0, 90):
            c.radial(cx, cy, -R, R, deg, 0.6, faint)
        for deg in range(0, 360, 5):
            big = deg % 30 == 0
            c.radial(cx, cy, R - (6 if big else 3 if deg % 10 == 0 else 1.8), R, deg, 0.9 if big else 0.6, line)
            if big:
                x, y = [v / CLOCK_SS for v in c.pt(cx, cy, R - 12, deg)]
                c.text(x, y, f"{deg:03d}", f["mono_s"], (26, 130, 62))
        for (lab, y) in self._sky_R_ROWS:                      # Anzeigefelder
            c.d.rounded_rectangle([222 * CLOCK_SS, (y - 7) * CLOCK_SS, 314 * CLOCK_SS, (y + 25) * CLOCK_SS],
                                  radius=3 * CLOCK_SS, fill=(6, 14, 9), outline=(48, 56, 52), width=CLOCK_SS)
            c.d.text((228 * CLOCK_SS, (y + 1) * CLOCK_SS), lab, font=f["mono_s"], fill=(34, 120, 60), anchor="lm")
        for x, y in ((6, 6), (6, 208), (314, 6), (314, 208)):   # Schrauben
            c.circle(x, y, 3, fill=(64, 70, 66), outline=(24, 28, 26), width=0.6)
            c.radial(x, y, -2.2, 2.2, 60, 0.7, (24, 28, 26))
        img = c.img.resize((WIDTH, CLOCK_H), Image.LANCZOS)
        # Blip-Formen (Gauß-Flecken)
        def blob(sigma, n):
            ax = np.arange(n, dtype=np.float32) - (n - 1) / 2
            return np.exp(-(ax[None, :] ** 2 + ax[:, None] ** 2) / (2 * sigma * sigma))
        rnd = random.Random(42)
        clutter = [(rnd.uniform(0, 360), R * rnd.uniform(0.05, 0.3) ** 1.2 * 1.4, rnd.uniform(0.3, 0.8))
                   for _ in range(26)]
        return np.asarray(img).astype(np.float32), blob(2.6, 17), blob(1.8, 13), blob(0.9, 7), clutter

    @staticmethod
    def _sky_stamp(arr, x, y, sprite, amp):
        """Fleck sprite mit Stärke amp bei (x, y) aufaddieren (am Rand abgeschnitten)."""
        n = sprite.shape[0]
        x0, y0 = int(round(x)) - n // 2, int(round(y)) - n // 2
        h, w = arr.shape
        sx0, sy0 = max(0, -x0), max(0, -y0)
        sx1, sy1 = min(n, w - x0), min(n, h - y0)
        if sx0 < sx1 and sy0 < sy1:
            arr[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] += sprite[sy0:sy1, sx0:sx1] * amp

    @clock_face("radar", fps=5)
    def face_radar(self, profile):
        f = _sky_fonts()
        base, blob_h, blob_m, core, clutter = self._clock_cache("sky_radar", 1, self._sky_radar_static)
        t = self._clock_now()
        lt = time.localtime(t)
        cx, cy, R = self._sky_RC
        beam = (lt.tm_sec + t % 1) * 6
        # Nachleuchtender Fächer (doppelte Auflösung, dann verkleinert)
        fan = Image.new("L", (WIDTH * 2, CLOCK_H * 2), 0)
        fd = ImageDraw.Draw(fan)
        box = [(cx - R) * 2, (cy - R) * 2, (cx + R) * 2, (cy + R) * 2]
        for k in range(44, -1, -1):
            a1 = beam - k * 2.2
            fd.pieslice(box, a1 - 2.4 - 90, a1 - 90, fill=int(118 * math.exp(-k / 11)))
        green = np.asarray(fan.resize((WIDTH, CLOCK_H), Image.BILINEAR)).astype(np.float32)
        white = np.zeros_like(green)
        rad = math.radians(beam)
        for k in range(int(R)):                                  # heller Strahl
            self._sky_stamp(white, cx + k * math.sin(rad), cy - k * math.cos(rad), core, 70)

        def glow(deg):
            """Nachleuchten 0…1 eines Echos: hell, wenn der Strahl es gerade überstrichen hat."""
            age = ((beam - deg) % 360) / 6
            return math.exp(-age / 9)
        for deg, r, amp in clutter:
            g = glow(deg)
            self._sky_stamp(green, cx + r * math.sin(math.radians(deg)), cy - r * math.cos(math.radians(deg)), core,
                            amp * (40 + 150 * g))
        h_deg = (lt.tm_hour % 12 + lt.tm_min / 60) * 30
        m_deg = (lt.tm_min + lt.tm_sec / 60) * 6
        for deg, r, sprite in ((h_deg, 0.45 * R, blob_h), (m_deg, 0.80 * R, blob_m)):
            g = glow(deg)
            x, y = cx + r * math.sin(math.radians(deg)), cy - r * math.cos(math.radians(deg))
            self._sky_stamp(green, x, y, sprite, 150 + 330 * g)
            self._sky_stamp(white, x, y, core, 40 + 260 * g ** 2)
        out = (base + green[..., None] * np.array([0.22, 1.0, 0.42], np.float32)
               + white[..., None] * np.array([0.75, 1.0, 0.8], np.float32))
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        img.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), (0, 0))
        d = ImageDraw.Draw(img)
        vals = (f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}", f"{lt.tm_mday:02d}.{lt.tm_mon:02d}.{lt.tm_year % 100:02d}",
                f"{int(beam) % 360:03d}°", f"{int(h_deg) % 360:03d}° {lt.tm_hour:02d}h",
                f"{int(m_deg) % 360:03d}° {lt.tm_min:02d}m")
        for (lab, y), v in zip(self._sky_R_ROWS, vals):
            d.text((268, y + 13), v, font=f["r_val"], fill=(90, 255, 140), anchor="mm")
        return img
