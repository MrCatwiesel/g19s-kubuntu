"""Displayseite „Uhr“: zeigt das Zifferblatt des aktiven Profils und der Ebene (Standard: Digitaluhr)."""


class ClockPage:
    @page("clock")
    def page_clock(self, profile, macros):
        face = getattr(self, "clock_face", "digital")
        fn = CLOCK_RENDERERS.get(face) or CLOCK_RENDERERS["digital"]
        return fn(self, profile)

    @clock_face("digital")
    def face_digital(self, profile):
        """Große Uhrzeit, Sekunden, Wochentag, Datum."""
        opt = self._copt("digital")
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        now = time.localtime(self._clock_now())
        dy = (0 if opt["seconds"] else 14) + (0 if opt["date"] else 48)
        self._center(d, 28 + dy, time.strftime("%H:%M", now), self.f_huge, self._ccolor(opt["color"], profile, self.FG))
        if opt["seconds"]:
            self._center(d, 122 + dy, f":{now.tm_sec:02d}", self.f_mid, self.DIM)
        if opt["date"]:
            y = 152 if opt["seconds"] else 136
            self._center(d, y, WEEKDAYS[now.tm_wday], self.f_big, PROFILE_COLOR.get(profile, self.FG))
            self._center(d, y + 32, f"{now.tm_mday}. {MONTHS[now.tm_mon - 1]} {now.tm_year}", self.f_mid, self.FG)
        return img
