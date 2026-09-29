"""Displayseite „Wetter“: aktuelles Wetter und die nächsten Tage (Open-Meteo) mit gezeichneten Symbolen."""


def draw_weather_icon(d, x, y, s, kind, night=False):
    """Einfache Wettersymbole aus Grundformen. (x, y) = linke obere Ecke, s = Größe."""
    sun, cloud, dark = (255, 200, 40), (215, 222, 235), (150, 160, 180)
    def disc(cx, cy, r, fill):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    def sunshape(cx, cy, r):
        if night:
            disc(cx, cy, r, (235, 235, 210))
            disc(cx + r * 0.45, cy - r * 0.3, r * 0.85, (8, 10, 16))
            return
        import math
        for i in range(8):
            a = i * math.pi / 4
            d.line([cx + math.cos(a) * r * 1.25, cy + math.sin(a) * r * 1.25,
                    cx + math.cos(a) * r * 1.7, cy + math.sin(a) * r * 1.7], fill=sun, width=max(2, int(s / 22)))
        disc(cx, cy, r, sun)
    def cloudshape(cx, cy, w, fill):
        h = w * 0.55
        disc(cx - w * 0.22, cy, h * 0.42, fill)
        disc(cx + w * 0.05, cy - h * 0.18, h * 0.55, fill)
        disc(cx + w * 0.28, cy + h * 0.02, h * 0.38, fill)
        d.rounded_rectangle([cx - w * 0.42, cy, cx + w * 0.45, cy + h * 0.42], radius=h * 0.2, fill=fill)
    c = (x + s / 2, y + s / 2)
    if kind == "sun":
        sunshape(c[0], c[1], s * 0.24)
        return
    if kind == "partly":
        sunshape(x + s * 0.36, y + s * 0.34, s * 0.19)
        cloudshape(x + s * 0.56, y + s * 0.58, s * 0.62, cloud)
        return
    fill = dark if kind in ("rain", "thunder", "drizzle") else cloud
    cloudshape(c[0], y + s * 0.42, s * 0.8, fill)
    base = y + s * 0.7
    if kind in ("rain", "drizzle"):
        n = 3 if kind == "rain" else 2
        for i in range(n):
            px = x + s * (0.3 + i * 0.2)
            d.line([px, base, px - s * 0.06, base + s * (0.2 if kind == "rain" else 0.12)],
                   fill=(90, 160, 255), width=max(2, int(s / 18)))
    elif kind == "snow":
        for i in range(3):
            disc(x + s * (0.3 + i * 0.2), base + s * 0.1, s * 0.05, (245, 248, 255))
    elif kind == "thunder":
        d.polygon([(x + s * 0.52, base - s * 0.02), (x + s * 0.4, base + s * 0.16), (x + s * 0.5, base + s * 0.16),
                   (x + s * 0.42, base + s * 0.3), (x + s * 0.62, base + s * 0.1), (x + s * 0.52, base + s * 0.1)],
                  fill=(255, 210, 40))
    elif kind == "fog":
        for i in range(3):
            yy = base + i * s * 0.09
            d.line([x + s * 0.18, yy, x + s * 0.82, yy], fill=(190, 198, 210), width=max(2, int(s / 20)))


class WeatherPage:
    @page("weather")
    def page_weather(self, profile, macros):
        cfg = (self.settings or {}).get("weather") or {}
        if cfg.get("lat") is None:
            return self._hint_page("☀", "Wetter", "Ort in der G19s-Verwaltung einstellen")
        data, err, _ = self.weather.snapshot() if self.weather else (None, None, 0)
        if not data:
            return self._hint_page("☀", "Wetter-Fehler" if err else "Wetter", err or "Lade Wetterdaten …",
                                   (235, 90, 90) if err else None)
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        cur = data.get("current") or {}
        desc, kind = WEATHER_CODES.get(int(cur.get("weather_code") or 0), ("", "cloud"))
        night = not cur.get("is_day", 1)
        d.text((12, 6), self._fit(d, cfg.get("name") or "", self.f_small, WIDTH - 40), font=self.f_small, fill=self.DIM)
        if err:
            d.text((WIDTH - 22, 6), "⚠", font=self.f_small, fill=(240, 170, 60))
        draw_weather_icon(d, 6, 26, 92, kind, night)
        temp = cur.get("temperature_2m")
        d.text((112, 20), f"{round(temp)}°" if temp is not None else "–", font=self.f_huge, fill=self.FG)
        d.text((114, 104), self._fit(d, desc, self.f_mid, WIDTH - 124), font=self.f_mid, fill=PROFILE_COLOR.get(profile, self.FG))
        bits = []
        if cur.get("apparent_temperature") is not None:
            bits.append(f"gefühlt {round(cur['apparent_temperature'])}°")
        if cur.get("wind_speed_10m") is not None:
            bits.append(f"{round(cur['wind_speed_10m'])} km/h")
        if cur.get("relative_humidity_2m") is not None:
            bits.append(f"{round(cur['relative_humidity_2m'])} %")
        d.text((114, 130), self._fit(d, " · ".join(bits), self.f_small, WIDTH - 122), font=self.f_small, fill=self.DIM)
        daily = data.get("daily") or {}
        import datetime as dt
        days = daily.get("time") or []
        d.line([8, 156, WIDTH - 8, 156], fill=(40, 46, 60))
        col_w = (WIDTH - 16) // 3
        for i in range(min(3, len(days))):
            x = 8 + i * col_w
            try:
                day = dt.date.fromisoformat(days[i])
                label = "Heute" if i == 0 else "Morgen" if i == 1 else WEEKDAY_DE[day.weekday()]
            except ValueError:
                label = days[i]
            code = (daily.get("weather_code") or [0] * 3)[i] or 0
            draw_weather_icon(d, x - 2, 166, 32, WEATHER_CODES.get(int(code), ("", "cloud"))[1])
            tx, tw = x + 32, col_w - 36
            d.text((tx, 160), self._fit(d, label, self.f_small_b, tw), font=self.f_small_b, fill=self.FG)
            tmax = (daily.get("temperature_2m_max") or [None] * 3)[i]
            tmin = (daily.get("temperature_2m_min") or [None] * 3)[i]
            if tmax is not None and tmin is not None:
                d.text((tx, 178), self._fit(d, f"{round(tmax)}°/{round(tmin)}°", self.f_small, tw),
                       font=self.f_small, fill=self.FG)
            rain = (daily.get("precipitation_probability_max") or [None] * 3)[i]
            if rain is not None:
                d.text((tx, 197), f"☂ {rain} %", font=self.f_tiny, fill=(120, 170, 255))
        return img
