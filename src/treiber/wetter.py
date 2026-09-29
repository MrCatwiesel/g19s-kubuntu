"""Wetter von Open-Meteo: Abruf und Ortssuche."""


# --- Wetter (Open-Meteo, kostenlos, ohne Anmeldung) ---------------------------
WEATHER_URL = os.environ.get("G19S_WEATHER_URL", "https://api.open-meteo.com/v1/forecast")
GEOCODE_URL = os.environ.get("G19S_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")
WEATHER_CODES = {
    0: ("Klar", "sun"), 1: ("Überwiegend klar", "sun"), 2: ("Teilweise bewölkt", "partly"),
    3: ("Bedeckt", "cloud"), 45: ("Nebel", "fog"), 48: ("Reifnebel", "fog"),
    51: ("Leichter Niesel", "drizzle"), 53: ("Nieselregen", "drizzle"), 55: ("Starker Niesel", "drizzle"),
    56: ("Gefrierender Niesel", "drizzle"), 57: ("Gefrierender Niesel", "drizzle"),
    61: ("Leichter Regen", "rain"), 63: ("Regen", "rain"), 65: ("Starker Regen", "rain"),
    66: ("Gefrierender Regen", "rain"), 67: ("Gefrierender Regen", "rain"),
    71: ("Leichter Schnee", "snow"), 73: ("Schneefall", "snow"), 75: ("Starker Schnee", "snow"),
    77: ("Schneegriesel", "snow"), 80: ("Regenschauer", "rain"), 81: ("Kräftige Schauer", "rain"),
    82: ("Heftige Schauer", "rain"), 85: ("Schneeschauer", "snow"), 86: ("Starke Schneeschauer", "snow"),
    95: ("Gewitter", "thunder"), 96: ("Gewitter, Hagel", "thunder"), 99: ("Schweres Gewitter", "thunder"),
}


def geocode(name, count=8):
    """Ortssuche: [{name, lat, lon, label}]"""
    import urllib.parse
    q = urllib.parse.urlencode({"name": name, "count": count, "language": "de", "format": "json"})
    data = json.loads(http_get(f"{GEOCODE_URL}?{q}").decode())
    out = []
    for r in data.get("results") or []:
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        out.append({"name": r.get("name", ""), "lat": r.get("latitude"), "lon": r.get("longitude"),
                    "label": ", ".join(p for p in parts if p)})
    return out


class WeatherPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 900, log)

    def cfg(self):
        return self.get_settings().get("weather") or {}

    def enabled(self):
        c = self.cfg()
        return (c.get("lat") is not None and c.get("lon") is not None
                and "weather" in (self.get_settings().get("pages") or []))

    def signature(self):
        c = self.cfg()
        return (c.get("lat"), c.get("lon"))

    def fetch(self):
        import urllib.parse
        c = self.cfg()
        q = urllib.parse.urlencode({
            "latitude": c["lat"], "longitude": c["lon"], "timezone": "auto", "forecast_days": 4,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,"
                       "wind_speed_10m,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        })
        return json.loads(http_get(f"{WEATHER_URL}?{q}").decode())
