"""Displayseite „Bilder“: Diashow (Piwigo oder Ordner) mit Titel, Pause- und Lieblingsbild-Anzeige."""


class SlidesPage:
    @page("slides")
    def page_slides(self, profile, macros):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        if self.slideshow is None:
            snap = {"image": None, "configured": False, "status": "", "error": None}
        else:
            self.slideshow.touch()
            snap = self.slideshow.snapshot()
        if snap["image"] is not None:
            img.paste(snap["image"], (0, 0))
            cfg = (self.settings or {}).get("slideshow") or {}
            top = []
            if snap["error"]:
                top.append("⚠ " + snap["error"])
            elif cfg.get("caption", True) and snap["name"]:
                top.append(snap["name"])
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            if top or snap["paused"]:
                od.rectangle([0, 0, WIDTH, 26], fill=(0, 0, 0, 150))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            d = ImageDraw.Draw(img)
            right = f"{snap['index']}/{snap['count']}"
            rw = d.textlength(right, font=self.f_tiny)
            if top:
                d.text((8, 5), self._fit(d, top[0], self.f_small, WIDTH - rw - 40), font=self.f_small,
                       fill=(255, 120, 120) if snap["error"] else self.FG)
                d.text((WIDTH - rw - 8, 7), right, font=self.f_tiny, fill=self.DIM)
            if snap["paused"]:
                x = WIDTH - rw - 26 if top else WIDTH - 22
                d.rectangle([x, 7, x + 4, 19], fill=self.FG)
                d.rectangle([x + 8, 7, x + 12, 19], fill=self.FG)
            if snap.get("id") is not None and self.slideshow and str(snap["id"]) in self.slideshow.fav_ids():
                self._heart(d, 10, HEIGHT - 50, 22, (235, 60, 90))
            return img
        d = ImageDraw.Draw(img)
        self._center(d, 30, "▣", self.f_huge, (60, 66, 84))
        if not snap["configured"]:
            self._center(d, 128, "Diashow", self.f_big, self.FG)
            self._center(d, 166, "In der G19s-Verwaltung einrichten", self.f_small, self.DIM)
        elif snap["error"]:
            self._center(d, 128, "Piwigo-Fehler", self.f_big, (235, 90, 90))
            for i, line in enumerate(self._wrap(d, snap["error"], self.f_small, WIDTH - 24, 2)):
                self._center(d, 164 + i * 19, line, self.f_small, self.DIM)
        else:
            self._center(d, 140, snap["status"] or "Lade Bilder …", self.f_mid, self.FG)
        return img


@page_keys("slides")
def keys_slides(app, pressed):
    """OK = Pause/Weiter, Hoch/Runter = Bild zurück/vor, BACK = Lieblingsbild, MENU = Albenauswahl."""
    sl = app.slideshow
    if pressed & LKEY_BITS["MENU"]:
        cfg = sl.cfg()
        if cfg.get("source") == "folder":
            app.show("Alben", ["Auswahl nur für", "Piwigo-Alben"], PROFILE_COLOR[app.layer], 2)
        elif not cfg.get("url"):
            app.show("Alben", ["Piwigo zuerst in der", "Verwaltung einrichten"], PROFILE_COLOR[app.layer], 2.5)
        else:
            sl.request_albums()
            selected = set()
            for a in cfg.get("albums") or []:
                try:
                    selected.add(int(a))
                except (TypeError, ValueError):
                    pass
            app.menu = AlbumMenu(selected)
            app.flash = None
        app.next_draw = 0
        return True
    for bit, action in ((LKEY_BITS["OK"], "toggle"), (LKEY_BITS["UP"], "previous"), (LKEY_BITS["DOWN"], "next")):
        if pressed & bit:
            sl.command(action)
            app.next_draw = time.monotonic() + (0.05 if action == "toggle" else 0.4)
    if pressed & LKEY_BITS["BACK"]:
        fav = sl.favorite_current()
        if fav is not None:
            app.log(f"Lieblingsbild {'gemerkt' if fav else 'entfernt'}: {sl.snapshot()['name']}")
            app.show("♥ Lieblingsbild" if fav else "Lieblingsbild", ["gemerkt" if fav else "entfernt"],
                     (235, 60, 90) if fav else PROFILE_COLOR[app.layer], 1.2)
    app.nav_keys(pressed, LKEY_BITS["RIGHT"], LKEY_BITS["LEFT"])
    return True
