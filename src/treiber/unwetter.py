"""Amtliche Unwetterwarnungen des DWD (über Bright Sky) für den Wetterort."""


# --- Unwetterwarnungen (DWD, bereitgestellt von Bright Sky) --------------------
ALERTS_URL = os.environ.get("G19S_ALERTS_URL", "https://api.brightsky.dev/alerts")
SEVERITY = {"minor": ("Wetterwarnung", (240, 200, 40)), "moderate": ("Markante Warnung", (245, 140, 30)),
            "severe": ("Unwetterwarnung", (230, 50, 50)), "extreme": ("Extremes Unwetter", (170, 60, 200))}
SEVERITY_RANK = {"minor": 1, "moderate": 2, "severe": 3, "extreme": 4}


class WarningsPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 600, log)

    def enabled(self):
        s = self.get_settings()
        w = s.get("weather") or {}
        return (w.get("lat") is not None and w.get("lon") is not None and
                ("warnings" in (s.get("pages") or []) or (s.get("warnings") or {}).get("popup", True)))

    def signature(self):
        w = self.get_settings().get("weather") or {}
        return (w.get("lat"), w.get("lon"))

    def fetch(self):
        import datetime as dt
        import urllib.parse
        w = self.get_settings().get("weather") or {}
        q = urllib.parse.urlencode({"lat": w["lat"], "lon": w["lon"]})
        data = json.loads(http_get(f"{ALERTS_URL}?{q}").decode())
        now = dt.datetime.now().astimezone()

        def when(v):
            try:
                return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone() if v else None
            except ValueError:
                return None
        alerts = []
        for a in data.get("alerts") or []:
            if a.get("status", "actual") != "actual":
                continue
            onset, expires = when(a.get("onset") or a.get("effective")), when(a.get("expires"))
            if expires and expires < now:
                continue
            alerts.append({"id": str(a.get("alert_id") or a.get("id")), "severity": a.get("severity") or "minor",
                           "event": a.get("event_de") or a.get("event_en") or "Warnung",
                           "headline": a.get("headline_de") or a.get("headline_en") or "",
                           "description": a.get("description_de") or a.get("description_en") or "",
                           "instruction": a.get("instruction_de") or a.get("instruction_en") or "",
                           "onset": onset or now, "expires": expires})
        alerts.sort(key=lambda a: (-SEVERITY_RANK.get(a["severity"], 0), a["onset"]))
        loc = data.get("location") or {}
        return {"alerts": alerts, "place": loc.get("name") or w.get("name") or ""}
