"""Einblendungen über der aktuellen Seite: Meldungen, Lautstärke, Mikrofon, Timer, Termine, Benachrichtigungen."""


class OverlayViews:
    def render_timer(self, t, color, now=None):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        if t.alarm:
            blink = int(time.monotonic() * 2) % 2 == 0
            d.rectangle([0, 0, WIDTH, HEIGHT], fill=(120, 20, 20) if blink else self.BG)
            self._icon_bell(d, WIDTH // 2, 36, self.FG)
            self._center(d, 120, "Zeit abgelaufen!", self.f_big, self.FG)
            self._center(d, 158, timer_label(t.cfg or {}), self.f_mid, (230, 200, 200))
            d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
            self._center(d, HEIGHT - 20, "beliebige Displaytaste = OK", self.f_tiny, self.DIM)
            return img
        if t.mode == "pomodoro":
            title = "Pomodoro · " + ("Arbeiten" if t.phase == "work" else "Pause")
            accent = color if t.phase == "work" else (62, 207, 126)
        else:
            title, accent = ("Stoppuhr" if t.mode == "stopwatch" else timer_label(t.cfg or {})), color
        d.text((12, 6), title, font=self.f_title, fill=self.FG)
        state = "läuft" if t.running else "angehalten"
        d.text((WIDTH - 12 - d.textlength(state, font=self.f_small), 9), state, font=self.f_small,
               fill=(80, 220, 130) if t.running else (240, 170, 60))
        value = fmt_clock(t.display_value(now))
        font = self.f_huge if d.textlength(value, font=self.f_huge) <= WIDTH - 20 else self.f_large
        self._center(d, 52, value, font, self.FG if t.running else (170, 176, 190))
        if t.mode != "stopwatch" and t.total:
            frac = 1 - t.remaining(now) / t.total
            d.rounded_rectangle([20, 160, WIDTH - 20, 172], radius=6, fill=(35, 40, 55))
            if frac > 0:
                d.rounded_rectangle([20, 160, 20 + max(12, int((WIDTH - 40) * frac)), 172], radius=6, fill=accent)
        if t.mode == "pomodoro":
            self._center(d, 182, f"{t.rounds} Runde{'n' if t.rounds != 1 else ''} geschafft", self.f_small, self.DIM)
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        hint = ("OK Start/Stopp · ▼ auf 0 · BACK zurück" if t.mode == "stopwatch" else
                "OK Pause · ▲ +1 min · ▼ beenden · BACK zurück")
        self._center(d, HEIGHT - 20, hint, self.f_tiny, self.DIM)
        return img

    def render_event(self, ev, cal_name, color, scroll=0):
        """Termindetails: Titel, Zeit, Ort, Kalender, Beschreibung (mit Hoch/Runter blätterbar)."""
        import datetime as dt
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = tuple(color or self.CAL_COLORS[0])
        d.rectangle([0, 0, 6, HEIGHT - 22], fill=color)
        lines = []                                  # (Text, Schrift, Farbe)
        for t in self._wrap(d, ev.get("title") or "", self.f_title, WIDTH - 28, 3):
            lines.append((t, self.f_title, self.FG, 23))
        s, e = ev["start"], ev["end"]
        if ev.get("allday"):
            last = e - dt.timedelta(days=1) if isinstance(e, dt.date) and e > s else s
            when = f"{WEEKDAY_DE[s.weekday()]} {s.day:02d}.{s.month:02d}." + (
                f" – {WEEKDAY_DE[last.weekday()]} {last.day:02d}.{last.month:02d}." if last != s else "") + " · ganztägig"
        else:
            when = f"{WEEKDAY_DE[s.weekday()]} {s.day:02d}.{s.month:02d}. {s.strftime('%H:%M')}"
            when += f"–{e.strftime('%H:%M')}" if e.date() == s.date() else \
                f" – {WEEKDAY_DE[e.weekday()]} {e.day:02d}.{e.month:02d}. {e.strftime('%H:%M')}"
        lines.append(("", self.f_tiny, self.FG, 4))
        lines.append((when, self.f_small_b, color, 20))
        if ev.get("location"):
            for t in self._wrap(d, "Ort: " + ev["location"], self.f_small, WIDTH - 28, 2):
                lines.append((t, self.f_small, (200, 205, 215), 19))
        if cal_name:
            lines.append((cal_name, self.f_small, self.DIM, 19))
        desc = (ev.get("description") or "").strip()
        if desc:
            lines.append(("", self.f_tiny, self.FG, 6))
            for para in desc.split("\n"):
                for t in (self._wrap(d, para, self.f_small, WIDTH - 28, 40) if para.strip() else [""]):
                    lines.append((t, self.f_small, (200, 205, 215), 19))
        area = HEIGHT - 22 - 8
        heights = [h for *_, h in lines]
        max_scroll = 0
        while sum(heights[max_scroll:]) > area and max_scroll < len(lines) - 1:
            max_scroll += 1
        scroll = max(0, min(scroll, max_scroll))
        y = 8
        for text, font, fill, h in lines[scroll:]:
            if y + h > area + 8:
                break
            d.text((16, y), text, font=font, fill=fill)
            y += h
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ blättern · BACK zurück" if max_scroll else "BACK zurück", self.f_tiny, self.DIM)
        self._scroll_marks(d, scroll > 0, scroll < max_scroll)
        return img, max_scroll

    def render_reminder(self, ev, minutes, color, cal_name=""):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = tuple(color or self.CAL_COLORS[0])
        d.rectangle([0, 0, WIDTH, 34], fill=color)
        head = "Termin jetzt" if minutes <= 0 else f"Termin in {minutes} Min."
        d.text((12, 6), head, font=self.f_title, fill=(255, 255, 255))
        d.text((WIDTH - 12 - d.textlength(ev["start"].strftime("%H:%M"), font=self.f_title), 6),
               ev["start"].strftime("%H:%M"), font=self.f_title, fill=(255, 255, 255))
        y = 46
        for t in self._wrap(d, ev.get("title") or "", self.f_big, WIDTH - 24, 3):
            d.text((12, y), t, font=self.f_big, fill=self.FG)
            y += 30
        y += 4
        if ev.get("location"):
            for t in self._wrap(d, "Ort: " + ev["location"], self.f_small, WIDTH - 24, 2):
                d.text((12, y), t, font=self.f_small, fill=(200, 205, 215))
                y += 19
        if cal_name:
            d.text((12, y), cal_name, font=self.f_small, fill=self.DIM)
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "beliebige Displaytaste = OK", self.f_tiny, self.DIM)
        return img

    def render_mic(self, muted, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), (90, 16, 16) if muted else self.BG)
        d = ImageDraw.Draw(img)
        cx, top = WIDTH // 2, 36
        col = (255, 255, 255) if muted else color
        d.rounded_rectangle([cx - 18, top, cx + 18, top + 62], radius=18, fill=col)
        d.arc([cx - 34, top + 20, cx + 34, top + 88], 0, 180, fill=col, width=6)
        d.line([(cx, top + 88), (cx, top + 104)], fill=col, width=6)
        d.line([(cx - 22, top + 106), (cx + 22, top + 106)], fill=col, width=6)
        if muted:
            d.line([(cx - 48, top + 104), (cx + 48, top - 6)], fill=(255, 80, 80), width=9)
        self._center(d, 162, "Mikrofon stumm" if muted else "Mikrofon an", self.f_big, self.FG)
        return img

    def render_notification(self, app, summary, body, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, WIDTH, 30], fill=(24, 29, 40))
        d.rectangle([0, 0, 5, 30], fill=color)
        d.text((14, 6), self._fit(d, app or "Benachrichtigung", self.f_small_b, WIDTH - 80), font=self.f_small_b, fill=self.DIM)
        now = time.strftime("%H:%M")
        d.text((WIDTH - 10 - d.textlength(now, font=self.f_small), 6), now, font=self.f_small, fill=self.DIM)
        y = 40
        for line in self._wrap(d, summary or "", self.f_title, WIDTH - 24, 2):
            d.text((12, y), line, font=self.f_title, fill=self.FG)
            y += 24
        y += 4
        for line in self._wrap(d, body or "", self.f_small, WIDTH - 24, max(1, (HEIGHT - y - 8) // 19)):
            d.text((12, y), line, font=self.f_small, fill=(200, 205, 215))
            y += 19
        return img

    def render_volume(self, pct, muted, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        # Lautsprecher-Symbol
        cx, cy = 60, 104
        d.rectangle([cx - 22, cy - 14, cx - 8, cy + 14], fill=self.FG)
        d.polygon([(cx - 8, cy - 14), (cx + 14, cy - 34), (cx + 14, cy + 34), (cx - 8, cy + 14)], fill=self.FG)
        if muted:
            d.line([cx + 26, cy - 16, cx + 58, cy + 16], fill=(235, 80, 80), width=6)
            d.line([cx + 26, cy + 16, cx + 58, cy - 16], fill=(235, 80, 80), width=6)
        else:
            for i, r in enumerate((20, 34, 48)):
                if pct > i * 33:
                    d.arc([cx + 14 - r, cy - r, cx + 14 + r, cy + r], -45, 45, fill=self.FG, width=5)
        if muted:
            d.text((140, 88), "Stumm", font=self.f_big, fill=self.FG)
        else:
            num = str(pct)
            font, top = (self.f_huge, 58) if len(num) < 3 else (self.f_large, 70)
            nw = d.textlength(num, font=font)
            x = 140 + (160 - nw - 26) / 2
            d.text((x, top), num, font=font, fill=self.FG)
            d.text((x + nw + 4, 102), "%", font=self.f_big, fill=self.DIM)
        d.rounded_rectangle([20, 170, WIDTH - 20, 186], radius=8, fill=(35, 40, 55))
        w = int((WIDTH - 40) * max(0, min(100, pct)) / 100)
        if w > 12:
            d.rounded_rectangle([20, 170, 20 + w, 186], radius=8, fill=(110, 118, 135) if muted else color)
        return img

    def render_message(self, title, lines, color):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, WIDTH, 6], fill=color)
        self._center(d, 34, title, self.f_big, color)
        y = 92
        for line in lines:
            self._center(d, y, self._fit(d, line, self.f_mid, WIDTH - 24), self.f_mid, self.FG)
            y += 32
        return img
