"""Displayseite „Nachrichten“: Schlagzeilen aus RSS-/Atom-Feeds, optional markierte Meldung."""


class NewsPage:
    @page("news")
    def page_news(self, profile, macros):
        cfg = (self.settings or {}).get("news") or {}
        data, hint = self._poll_state(self.news, "≡", "Nachrichten",
                                      None if cfg.get("feeds") else "Nachrichtenquellen in der G19s-Verwaltung eintragen")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        items = data.get("items") or []
        self.list_items["news"] = items
        _, err, _ = self.news.snapshot()
        self._header(d, "Nachrichten", time.strftime("%H:%M"), bool(err or data.get("errors")))
        if not items:
            self._center(d, 100, "Keine Meldungen", self.f_mid, self.DIM)
            return img
        import datetime as dt
        today = dt.date.today()
        sel = self.sel["news"]
        if sel is not None:
            sel = self.sel["news"] = max(0, min(sel, len(items) - 1))
        start = max(0, sel - 2) if sel is not None else 0
        y, bottom = 32, HEIGHT - 30
        color = PROFILE_COLOR.get(profile, self.FG)
        for idx, it in enumerate(items[start:], start):
            lines = self._wrap(d, it["title"], self.f_small, WIDTH - 24, 2)
            h = 16 + 18 * len(lines) + 4
            if y + h > bottom:
                break
            if idx == sel:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + h - 4], radius=5, fill=(40, 48, 66))
            meta = it.get("source") or ""
            if it.get("time"):
                t = it["time"].astimezone()
                meta += " · " + (t.strftime("%H:%M") if t.date() == today else t.strftime("%d.%m. %H:%M"))
            d.text((12, y), meta, font=self.f_tiny, fill=color)
            y += 15
            for line in lines:
                d.text((12, y), line, font=self.f_small, fill=self.FG if idx == sel else (210, 215, 225))
                y += 18
            y += 5
        return img


@page_keys("news", "warnings")
def keys_news_warnings(app, pressed):
    """Nachrichten/Unwetter: Hoch/Runter markiert, OK öffnet (Browser bzw. Details), MENU lädt neu."""
    page_id = PAGE_IDS[app.page % len(PAGE_IDS)]
    r = app.renderer
    if pressed & (LKEY_BITS["UP"] | LKEY_BITS["DOWN"] | LKEY_BITS["OK"]):
        items = r.list_items.get(page_id) or []
        if items:
            sel = move_selection(r.sel[page_id], pressed, len(items))
            if pressed & LKEY_BITS["OK"]:
                if sel is None:
                    sel = 0                 # erster Druck markiert nur
                else:
                    open_list_item(app, page_id, items[min(sel, len(items) - 1)])
            r.sel[page_id] = sel
            app.sel_t[page_id] = time.monotonic()
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, page_id)
        return True
    return False


def open_list_item(app, page_id, it):
    if page_id == "news" and it.get("link"):
        if app.launcher.start(["xdg-open", it["link"]]):
            app.show("Öffne", [it.get("source") or domain_of(it["link"])], PROFILE_COLOR[app.layer], 1.5)
            app.log(f"Nachricht geöffnet: {it['title']}")
    elif page_id == "warnings":
        label, color = SEVERITY.get(it["severity"], SEVERITY["minor"])
        body = it["description"] + ("\n\n" + it["instruction"] if it.get("instruction") else "")
        app.menu = DetailView({"title": it["headline"] or it["event"], "start": it["onset"],
                               "end": it["expires"] or it["onset"], "allday": False, "location": "",
                               "description": body, "color": list(color), "label": f"{label} · {it['event']}"})
        app.flash = None
