"""Displayseite „Video“: Folgen aus Video-Podcast-Feeds (ab Werk „Tagesschau in 100 Sekunden“) auswählen und
abspielen. Liste: Hoch/Runter markiert, OK spielt ab, MENU lädt neu. Während der Wiedergabe: OK Pause/Weiter,
◀ ▶ zehn Sekunden zurück/vor, BACK beendet. Ein laufendes Radio pausiert und läuft danach weiter."""


def _mmss(sec):
    sec = max(0, int(sec or 0))
    return f"{sec // 60}:{sec % 60:02d}"


class VideoPage:
    video_player = None                         # VideoPlayer (setzt die App)
    videos = None                               # VideoPoller (setzt die App)

    @page("video")
    def page_video(self, profile, macros):
        vp = self.video_player
        if vp is not None and vp.item is not None:
            return self._video_playing(vp, profile)
        cfg = (self.settings or {}).get("video") or {}
        data, hint = self._poll_state(self.videos, "▶", "Video",
                                      None if cfg.get("feeds") else "Video-Feeds in der G19s-Verwaltung eintragen")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        items = data.get("items") or []
        self.list_items["video"] = items
        _, err, _ = self.videos.snapshot()
        self._header(d, "Video", time.strftime("%H:%M"), bool(err or data.get("errors")))
        if not items:
            self._center(d, 100, "Keine Folgen gefunden", self.f_mid, self.DIM)
            return img
        import datetime as dt
        today = dt.date.today()
        sel = self.sel.get("video")
        if sel is not None:
            sel = self.sel["video"] = max(0, min(sel, len(items) - 1))
        start = max(0, sel - 2) if sel is not None else 0
        y, bottom = 32, HEIGHT - 44
        color = PROFILE_COLOR.get(profile, self.FG)
        for idx, it in enumerate(items[start:], start):
            lines = self._wrap(d, it["title"], self.f_small, WIDTH - 24, 2)
            h = 16 + 18 * len(lines) + 4
            if y + h > bottom:
                break
            if idx == sel:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + h - 4], radius=5, fill=(40, 48, 66))
            meta = "▶ " + (it.get("source") or "")
            if it.get("time"):
                t = it["time"].astimezone()
                meta += " · " + (t.strftime("%H:%M") if t.date() == today else t.strftime("%d.%m. %H:%M"))
            if it.get("duration"):
                meta += " · " + _mmss(it["duration"])
            d.text((12, y), meta, font=self.f_tiny, fill=color)
            y += 15
            for line in lines:
                d.text((12, y), line, font=self.f_small, fill=self.FG if idx == sel else (210, 215, 225))
                y += 18
            y += 5
        msg = vp.error if vp is not None and vp.error else "OK spielt ab · MENU lädt neu"
        if vp is not None and not vp.available():
            msg = "ffmpeg fehlt – sudo apt install ffmpeg"
        self._center(d, HEIGHT - 44, msg, self.f_tiny, (240, 170, 60) if msg != "OK spielt ab · MENU lädt neu" else self.DIM)
        return img

    def _video_playing(self, vp, profile):
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        d = ImageDraw.Draw(img)
        frame = vp.frame
        if frame is not None:
            img.paste(frame, (0, 0))
        else:
            self._center(d, VIDEO_H // 2 - 8, vp.error or "Lade …", self.f_small, (240, 170, 60) if vp.error else self.DIM)
        if vp.paused:                                                               # Pausezeichen
            d.rounded_rectangle([WIDTH // 2 - 22, VIDEO_H // 2 - 22, WIDTH // 2 + 22, VIDEO_H // 2 + 22], radius=8,
                                fill=(0, 0, 0))
            d.rectangle([WIDTH // 2 - 11, VIDEO_H // 2 - 13, WIDTH // 2 - 4, VIDEO_H // 2 + 13], fill=(255, 255, 255))
            d.rectangle([WIDTH // 2 + 4, VIDEO_H // 2 - 13, WIDTH // 2 + 11, VIDEO_H // 2 + 13], fill=(255, 255, 255))
        item = vp.item or {}
        pos, dur = vp.position(), item.get("duration")
        right = _mmss(pos) + (f" / {_mmss(dur)}" if dur else "")
        rw = d.textlength(right, font=self.f_tiny)
        title = item.get("title") or ""
        while title and d.textlength(title, font=self.f_tiny) > WIDTH - 24 - rw:
            title = title[:-2] + "…" if len(title) > 2 else ""
        d.text((8, VIDEO_H + 3), title, font=self.f_tiny, fill=(225, 230, 240))
        d.text((WIDTH - 8 - rw, VIDEO_H + 3), right, font=self.f_tiny, fill=self.DIM)
        color = PROFILE_COLOR.get(profile, self.FG)
        d.rectangle([8, VIDEO_H + 22, WIDTH - 8, VIDEO_H + 26], fill=(50, 54, 66))
        if dur:
            k = max(0.0, min(1.0, pos / dur))
            d.rectangle([8, VIDEO_H + 22, 8 + int((WIDTH - 16) * k), VIDEO_H + 26], fill=color)
        return img


@page_keys("video")
def keys_video(app, pressed):
    """Liste: Hoch/Runter, OK spielt, MENU lädt neu. Wiedergabe: OK Pause, ◀ ▶ spulen, BACK Stopp."""
    vp, r = app.video, app.renderer
    if vp.item is not None:
        if pressed & LKEY_BITS["OK"]:
            vp.toggle_pause()
        elif pressed & LKEY_BITS["LEFT"]:
            vp.seek(-VIDEO_SEEK)
        elif pressed & LKEY_BITS["RIGHT"]:
            vp.seek(VIDEO_SEEK)
        elif pressed & (LKEY_BITS["BACK"] | LKEY_BITS["MENU"]):
            video_stop(app)
        app.next_draw = 0
        return True                                 # während der Wiedergabe kein Seitenwechsel
    if pressed & (LKEY_BITS["UP"] | LKEY_BITS["DOWN"] | LKEY_BITS["OK"]):
        items = r.list_items.get("video") or []
        if items:
            sel = move_selection(r.sel.get("video"), pressed, len(items))
            if pressed & LKEY_BITS["OK"]:
                sel = sel or 0
                video_start(app, items[min(sel, len(items) - 1)])
            r.sel["video"] = sel
            app.sel_t["video"] = time.monotonic()
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, "video")
        return True
    return False


def video_start(app, item):
    """Video abspielen; ein laufendes Radio wird angehalten und danach fortgesetzt."""
    if app.radio.playing and app.__dict__.get("_video_radio") is None:
        app._video_radio = app.radio.current()
        app.radio.stop()
        app.log("Video: Radio pausiert")
    if app.video.play(item):
        app.log(f"Video: {item.get('source') or ''} – {item['title']}")
    app.next_draw = 0


def video_stop(app):
    app.video.stop()
    _video_resume_radio(app)
    app.next_draw = 0


def _video_resume_radio(app):
    station = app.__dict__.pop("_video_radio", None)
    if station:
        app.log("Video: Radio läuft weiter")
        app.radio_play(station, announce=False)


def video_tick(app):
    """Aus der Zeichenschleife: zu Ende gespielt → zurück zur Liste, Radio weiter."""
    vp = app.video
    if vp.item is not None and vp.ended and not vp.paused:
        if vp.error:
            vp.item = None                          # Liste mit Fehlermeldung zeigen
            _video_resume_radio(app)
        else:
            video_stop(app)


def video_play_latest(app):
    """G-Taste „Video“: zur Seite springen und die neueste Folge abspielen (lädt die Liste bei Bedarf)."""
    app.videos.wanted = True
    app.page = PAGE_IDS.index("video")
    app.flash = None
    app.next_draw = 0

    def work():
        data, _, _ = app.videos.snapshot()
        if not data:
            try:
                data = app.videos.fetch()
                with app.videos.lock:
                    app.videos.data, app.videos.error, app.videos.updated = data, None, time.time()
            except Exception as ex:
                with app.videos.lock:
                    app.videos.error = err_text(ex)
                app.log(f"Video: {err_text(ex)}")
                return
        items = (data or {}).get("items") or []
        if items:
            video_start(app, items[0])
        else:
            app.show("Video", ["Keine Folge gefunden"], REC_COLOR, 3)
    threading.Thread(target=work, daemon=True).start()
