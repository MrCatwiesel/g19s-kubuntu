"""Displayseite „Termine“: nächste Termine aller sichtbaren Kalender, optional mit markiertem Termin."""


class CalendarPage:
    # ---- Termine -------------------------------------------------------- #
    CAL_COLORS = CAL_COLORS

    @page("calendar")
    def page_calendar(self, profile, macros):
        import datetime as dt
        cfg = (self.settings or {}).get("calendar") or {}
        if not cfg.get("sources"):
            return self._hint_page("▦", "Termine", "Kalender in der G19s-Verwaltung eintragen")
        data, err, _ = self.calendar.snapshot() if self.calendar else (None, None, 0)
        if data is None:
            return self._hint_page("▦", "Kalender-Fehler" if err else "Termine", err or "Lade Termine …",
                                   (235, 90, 90) if err else None)
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        now = dt.datetime.now().astimezone()
        today = now.date()
        d.text((12, 4), "Termine", font=self.f_title, fill=self.FG)
        head = f"{WEEKDAY_DE[today.weekday()]} {today.day}. {MONTHS[today.month - 1]}"
        d.text((WIDTH - 12 - d.textlength(head, font=self.f_small), 8), head, font=self.f_small, fill=self.DIM)
        if err or data.get("errors"):
            d.text((96, 8), "⚠", font=self.f_small, fill=(240, 170, 60))
        cals = data.get("calendar_list") or []
        shown = [c for c in cals if c["key"] not in self.cal_hidden]
        if len(cals) > 1:
            info = f"{len(shown)}/{len(cals)}" if len(shown) < len(cals) else ""
            if info:
                d.text((12 + d.textlength("Termine", font=self.f_title) + 8, 8), info, font=self.f_small,
                       fill=(240, 170, 60))
        items = [x for x in data.get("items", [])
                 if (x["end"] > now if not x["allday"] else x["end"] > today)
                 and x.get("cal") not in self.cal_hidden]
        self.cal_items = items
        if self.cal_sel is not None:
            self.cal_sel = max(0, min(self.cal_sel, len(items) - 1)) if items else None
        if not items:
            if cals and not shown:
                self._center(d, 90, "Alle Kalender ausgeblendet", self.f_mid, self.DIM)
                self._center(d, 122, "OK = Kalender wählen", self.f_small, self.DIM)
            else:
                self._center(d, 100, "Keine Termine", self.f_mid, self.DIM)
            return img
        y, last_day, bottom = 32, None, HEIGHT - 30
        sources = cfg.get("sources") or []
        sel = self.cal_sel
        start = max(0, sel - 4) if sel is not None else 0
        for idx, it in enumerate(items[start:], start):
            day = it["start"] if it["allday"] else it["start"].date()
            ongoing = (it["allday"] and day <= today) or (not it["allday"] and it["start"] <= now)
            day = max(day, today) if ongoing else day
            if day != last_day:
                if y + 38 > bottom:
                    break
                label = ("Heute" if day == today else "Morgen" if day == today + dt.timedelta(days=1)
                         else f"{WEEKDAY_DE[day.weekday()]} {day.day:02d}.{day.month:02d}.")
                d.text((12, y), label, font=self.f_small_b, fill=PROFILE_COLOR.get(profile, self.FG))
                y += 19
                last_day = day
            if y + 19 > bottom:
                break
            if it["allday"]:
                when = "ganztags"
            elif ongoing:
                when = f"bis {it['end'].strftime('%H:%M')}"
            else:
                when = it["start"].strftime("%H:%M")
            src = it.get("source", 0)
            color = self.CAL_COLORS[src % len(self.CAL_COLORS)]
            if src < len(sources) and isinstance(sources[src].get("color"), list):
                color = tuple(sources[src]["color"])
            if isinstance(it.get("color"), list):
                color = tuple(it["color"])
            if idx == sel:
                d.rounded_rectangle([6, y - 1, WIDTH - 6, y + 18], radius=4, fill=(40, 48, 66))
            d.text((16, y), self._fit(d, when, self.f_small, 76), font=self.f_small,
                   fill=self.FG if idx == sel else self.DIM)
            d.rectangle([96, y + 3, 99, y + 16], fill=color)
            title = it["title"] + (f" · {it['location']}" if it.get("location") else "")
            d.text((106, y), self._fit(d, title, self.f_small, WIDTH - 114), font=self.f_small, fill=self.FG)
            y += 19
        return img


@page_keys("calendar")
def keys_calendar(app, pressed):
    """Hoch/Runter = Termin markieren, OK = Details, MENU = Kalenderauswahl."""
    r = app.renderer
    if pressed & (LKEY_BITS["UP"] | LKEY_BITS["DOWN"] | LKEY_BITS["OK"]):
        n = len(r.cal_items)
        if n:
            sel = move_selection(r.cal_sel, pressed, n)
            if pressed & LKEY_BITS["OK"]:
                sel = 0 if sel is None else sel
                app.menu = DetailView(r.cal_items[min(sel, n - 1)])
                app.flash = None
            r.cal_sel = sel
            app.sel_t["calendar"] = time.monotonic()
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["MENU"]:
        if app.calendar_list():
            app.menu = CalendarMenu()
            app.flash = None
        else:
            app.show("Kalender", ["noch keine Kalender geladen"], PROFILE_COLOR[app.layer], 2)
        app.next_draw = 0
        return True
    return False
