"""Displayseite „Unwetter“: DWD-Warnungen für den Wetterort, farbig nach Stufe."""


class WarningsPage:
    # ---- Unwetter ------------------------------------------------------- #
    @page("warnings")
    def page_warnings(self, profile, macros):
        w = (self.settings or {}).get("weather") or {}
        data, hint = self._poll_state(self.alerts, "⚠", "Unwetter",
                                      None if w.get("lat") is not None else "Ort in der G19s-Verwaltung einstellen (Infoseiten → Wetter)")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        alerts = data.get("alerts") or []
        self.list_items["warnings"] = alerts
        place = data.get("place") or w.get("name") or ""
        self._header(d, "Unwetter", self._fit(d, place, self.f_small, 170))
        if not alerts:
            cx = WIDTH // 2
            d.ellipse([cx - 34, 50, cx + 34, 118], fill=(40, 170, 90))
            d.line([(cx - 16, 84), (cx - 4, 98), (cx + 18, 70)], fill=(255, 255, 255), width=7)
            self._center(d, 132, "Keine Warnungen", self.f_big, self.FG)
            self._center(d, 168, "Deutscher Wetterdienst", self.f_small, self.DIM)
            return img
        sel = self.sel["warnings"]
        if sel is not None:
            sel = self.sel["warnings"] = max(0, min(sel, len(alerts) - 1))
        start = max(0, sel - 2) if sel is not None else 0
        y, bottom = 32, HEIGHT - 30
        for idx, a in enumerate(alerts[start:], start):
            if y + 44 > bottom:
                break
            label, color = SEVERITY.get(a["severity"], SEVERITY["minor"])
            if idx == sel:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + 42], radius=5, fill=(40, 48, 66))
            d.rectangle([10, y, 15, y + 38], fill=color)
            d.text((24, y), self._fit(d, a["event"], self.f_small_b, WIDTH - 36), font=self.f_small_b, fill=self.FG)
            span = f"{WEEKDAY_DE[a['onset'].weekday()]} {a['onset'].strftime('%H:%M')}"
            if a.get("expires"):
                e = a["expires"]
                span += " – " + (e.strftime("%H:%M") if e.date() == a["onset"].date() else
                                 f"{WEEKDAY_DE[e.weekday()]} {e.strftime('%H:%M')}")
            d.text((24, y + 20), f"{label} · {span}", font=self.f_tiny, fill=color)
            y += 48
        return img
