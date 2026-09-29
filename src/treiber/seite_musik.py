"""Displayseite „Musik“: aktueller Titel mit Cover, Fortschritt bzw. LIVE beim Radio."""


class MusicPage:
    @staticmethod
    def _fmt_time(us):
        s = int(us // 1_000_000)
        return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"

    @page("music")
    def page_music(self, profile, macros):
        info, cover, bg, error = self.media.snapshot() if self.media else (None, None, None, None)
        img = bg.copy() if info and bg is not None else Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = PROFILE_COLOR.get(profile, self.FG)

        if not info:
            self._center(d, 34, "♪", self.f_huge, (60, 66, 84))
            self._center(d, 132, "Keine Wiedergabe", self.f_big, self.FG)
            self._center(d, 170, error or "Spotify, Elisa, VLC, Browser …", self.f_small, self.DIM)
            return img

        # Cover
        size = MediaWatcher.COVER_SIZE
        x0, y0 = 12, 12
        if cover is not None:
            d.rectangle([x0 - 1, y0 - 1, x0 + size, y0 + size], fill=(0, 0, 0))
            img.paste(cover, (x0, y0))
        else:
            d.rounded_rectangle([x0, y0, x0 + size, y0 + size], radius=10, fill=(30, 34, 48))
            w = d.textlength("♪", font=self.f_huge)
            d.text((x0 + (size - w) / 2, y0 + 16), "♪", font=self.f_huge, fill=(80, 88, 110))

        # Texte
        tx = x0 + size + 12
        tw = WIDTH - tx - 10
        y = 12
        title = info["title"] or "Unbekannter Titel"
        font, lh = self.f_title, 24
        if any(d.textlength(w, font=font) > tw for w in title.split()):
            font, lh = self.f_title_s, 19   # sehr lange Wörter: kleinere Schrift
        for line in self._wrap(d, title, font, tw, 3):
            d.text((tx, y), line, font=font, fill=self.FG)
            y += lh
        y += 6
        if info["artist"]:
            d.text((tx, y), self._fit(d, info["artist"], self.f_small, tw), font=self.f_small, fill=color)
            y += 20
        second = info.get("station") or info["album"]
        if second:
            d.text((tx, y), self._fit(d, second, self.f_small, tw), font=self.f_small, fill=self.DIM)
        d.text((tx, y0 + size - 16), self._fit(d, info["player"].capitalize(), self.f_tiny, tw),
               font=self.f_tiny, fill=self.DIM)

        # Fortschritt
        pos, length = info["position"], info["length"]
        if info["status"] == "Playing":
            pos += (time.monotonic() - info["fetched"]) * 1_000_000
        if length:
            pos = min(pos, length)
        by = 160
        d.rounded_rectangle([12, by, WIDTH - 12, by + 6], radius=3,
                            fill=(60, 66, 84) if length else color)
        if length:
            fx = 12 + int((WIDTH - 24) * pos / length)
            if fx > 16:
                d.rounded_rectangle([12, by, fx, by + 6], radius=3, fill=color)
            d.text((12, by + 14), self._fmt_time(pos), font=self.f_small, fill=self.FG)
        else:
            d.ellipse([12, by + 19, 22, by + 29], fill=(235, 50, 50))
            d.text((28, by + 14), "LIVE", font=self.f_small_b, fill=self.FG)
        if length:
            t = self._fmt_time(length)
            d.text((WIDTH - 12 - d.textlength(t, font=self.f_small), by + 14), t,
                   font=self.f_small, fill=self.FG)

        # Status-Symbol (Play/Pause) mittig
        cx, cy = WIDTH // 2, by + 24
        if info["status"] == "Playing":
            d.rectangle([cx - 8, cy - 9, cx - 3, cy + 9], fill=self.FG)
            d.rectangle([cx + 3, cy - 9, cx + 8, cy + 9], fill=self.FG)
        else:
            d.polygon([(cx - 7, cy - 10), (cx - 7, cy + 10), (cx + 10, cy)], fill=self.FG)
        return img


@page_keys("music")
def keys_music(app, pressed):
    """OK = Play/Pause, Hoch/Runter = Titel zurück/vor, MENU = Senderliste, BACK = Radio aus."""
    if pressed & LKEY_BITS["MENU"]:
        items = app.station_items()
        if items:
            cur = app.radio.current()
            pos = next((i for i, it in enumerate(items) if cur and it.get("station", {}).get("url") == cur["url"]), 0)
            app.menu = StationMenu(pos)
            app.flash = None
        else:
            app.show("Radio", ["keine Sender angelegt"], PROFILE_COLOR[app.layer], 2)
        app.next_draw = 0
        return True
    for bit, action in ((LKEY_BITS["OK"], "play-pause"), (LKEY_BITS["UP"], "previous"), (LKEY_BITS["DOWN"], "next")):
        if pressed & bit:
            threading.Thread(target=app.media.control, args=(action,), daemon=True).start()
            app.next_draw = time.monotonic() + 0.3
    if pressed & LKEY_BITS["BACK"] and app.radio.playing:
        app.radio.stop()
        app.media.wake.set()
        app.next_draw = time.monotonic() + 0.3
    app.nav_keys(pressed, LKEY_BITS["RIGHT"], LKEY_BITS["LEFT"])
    return True
