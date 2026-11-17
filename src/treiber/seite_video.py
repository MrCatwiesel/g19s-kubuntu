"""Displayseite „Video“: Folgen aus Video-Podcast-Feeds (ab Werk „Tagesschau in 100 Sekunden“) und eigene
Videolisten (YouTube-Links, direkte Video-Adressen) auswählen und abspielen. Liste: Hoch/Runter markiert, OK spielt ab
(YouTube je nach Einstellung im Browser oder auf dem Display), MENU wechselt zur nächsten Liste (bei nur einer: lädt
neu). Während der Wiedergabe: OK Pause/Weiter, ◀ ▶ zehn Sekunden zurück/vor, BACK beendet. Ein laufendes Radio
pausiert und läuft danach weiter."""


def _mmss(sec):
    sec = max(0, int(sec or 0))
    return f"{sec // 60}:{sec % 60:02d}"


def video_sources(cfg):
    """Quellen der Seite „Video“ in Anzeige-Reihenfolge: ("feeds", "Podcasts") und je eigene Liste ("list", Name)."""
    out = [("feeds", "Podcasts")] if cfg.get("feeds") else []
    return out + [("list", name) for name in video_list_items(cfg)]


class VideoPage:
    video_player = None                         # VideoPlayer (setzt die App)
    videos = None                               # VideoPoller (setzt die App)
    thumbs = None                               # ThumbCache für YouTube-Vorschaubilder (setzt die App)
    video_src = 0                               # gewählte Quelle (MENU schaltet weiter)

    @page("video")
    def page_video(self, profile, macros):
        vp = self.video_player
        if vp is not None and vp.item is not None:
            return self._video_playing(vp, profile)
        cfg = (self.settings or {}).get("video") or {}
        srcs = video_sources(cfg)
        kind, name = srcs[self.video_src % len(srcs)] if srcs else ("feeds", "")
        if kind == "list":
            return self._video_list(cfg, name, srcs, profile)
        data, hint = self._poll_state(self.videos, "▶", "Video",
                                      None if cfg.get("feeds") else "Video-Feeds oder eigene Listen in der G19s-Verwaltung eintragen")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        items = data.get("items") or []
        self.list_items["video"] = items
        _, err, _ = self.videos.snapshot()
        self._header(d, "Video" if len(srcs) < 2 else "Video · Podcasts", time.strftime("%H:%M"),
                     bool(err or data.get("errors")))
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
        hint = "OK spielt ab · MENU " + ("nächste Liste" if len(srcs) > 1 else "lädt neu")
        msg = vp.error if vp is not None and vp.error else hint
        if vp is not None and not vp.available():
            msg = "ffmpeg fehlt – sudo apt install ffmpeg"
        self._center(d, HEIGHT - 44, msg, self.f_tiny, (240, 170, 60) if msg != hint else self.DIM)
        return img

    def _video_list(self, cfg, name, srcs, profile):
        """Eigene Liste: Vorschaubild, Titel, Kanal; YouTube öffnet im Browser oder läuft auf dem Display."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        items = video_list_items(cfg).get(name) or []
        self.list_items["video"] = items
        self._header(d, f"Video · {name}", time.strftime("%H:%M"), False)
        sel = self.sel.get("video")
        if sel is not None:
            sel = self.sel["video"] = max(0, min(sel, len(items) - 1))
        start = max(0, sel - 1) if sel is not None else 0
        y, bottom = 32, HEIGHT - 44
        color = PROFILE_COLOR.get(profile, self.FG)
        for idx, it in enumerate(items[start:], start):
            h = 52
            if y + h > bottom:
                break
            if idx == sel:
                d.rounded_rectangle([6, y - 3, WIDTH - 6, y + h - 5], radius=5, fill=(40, 48, 66))
            th = self.thumbs.get(it["youtube"]) if (self.thumbs is not None and it.get("youtube")) else None
            if th is not None:
                img.paste(th, (10, y))
            else:
                d.rectangle([10, y, 89, y + 44], fill=(28, 32, 42))
                d.polygon([(44, y + 14), (44, y + 30), (58, y + 22)], fill=(200, 60, 60) if it.get("youtube") else self.DIM)
            tx = 98
            meta = it.get("author") or ("YouTube" if it.get("youtube") else domain_of(it["url"]))
            d.text((tx, y), meta[:34], font=self.f_tiny, fill=color)
            yy = y + 14
            for line in self._wrap(d, it["title"], self.f_small, WIDTH - tx - 10, 2):
                d.text((tx, yy), line, font=self.f_small, fill=self.FG if idx == sel else (210, 215, 225))
                yy += 17
            y += h
        vp = self.video_player
        browser = cfg.get("youtube", "browser") != "display"
        hint = ("OK öffnet im Browser" if browser else "OK spielt ab") + \
            (" · MENU nächste Liste" if len(srcs) > 1 else "")
        msg = vp.error if vp is not None and vp.error else hint
        self._center(d, HEIGHT - 44, msg, self.f_tiny, (240, 170, 60) if msg != hint else self.DIM)
        return img

    def _video_playing(self, vp, profile):
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        d = ImageDraw.Draw(img)
        frame = vp.frame
        if frame is not None:
            img.paste(frame, (0, 0))
        else:
            wait = "Hole Video von YouTube …" if vp.loading else "Lade …"
            self._center(d, VIDEO_H // 2 - 8, vp.error or wait, self.f_small, (240, 170, 60) if vp.error else self.DIM)
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
                video_open(app, items[min(sel, len(items) - 1)])
            r.sel["video"] = sel
            app.sel_t["video"] = time.monotonic()
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["MENU"]:
        if len(video_sources(app.settings().get("video") or {})) > 1:
            r.video_src += 1                        # nächste Liste
            r.sel["video"] = None
            app.next_draw = 0
        else:
            refresh_page(app, "video")
        return True
    return False


def video_open(app, item):
    """Eintrag öffnen: YouTube je nach Einstellung im Browser oder auf dem Display, sonst auf dem Display."""
    cfg = app.settings().get("video") or {}
    if item.get("youtube"):
        if cfg.get("youtube", "browser") == "display":
            if ytdlp_path(app.launcher._env()) is not None:
                video_start(app, item)
                return
            app.show("Video", ["yt-dlp fehlt –", "öffne im Browser"], REC_COLOR, 2.5)
        if app.launcher.start(["xdg-open", item["url"]]):
            if cfg.get("youtube", "browser") != "display":
                app.show("Öffne im Browser", [item["title"][:32]], PROFILE_COLOR[app.layer], 1.5)
            app.log(f"Video im Browser: {item['title']}")
        return
    video_start(app, item)


def video_start(app, item):
    """Video abspielen; ein laufendes Radio wird angehalten und danach fortgesetzt."""
    if app.radio.playing and app.__dict__.get("_video_radio") is None:
        app._video_radio = app.radio.current()
        app.radio.stop()
        app.log("Video: Radio pausiert")
    if (app.video.play_youtube if item.get("youtube") else app.video.play)(item):
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
            return
        nxt = _video_next(app, vp.item)
        if nxt is not None:                         # eigene Liste: gleich das nächste Video
            app.log(f"Video: weiter mit „{nxt['title']}“")
            video_start(app, nxt)
            app.renderer.sel["video"] = nxt["index"]
        else:
            video_stop(app)


def _video_next(app, item):
    cfg = app.settings().get("video") or {}
    if not cfg.get("autonext", True) or item.get("list") is None:
        return None
    rows = video_list_items(cfg).get(item["list"]) or []
    i = item.get("index", -1) + 1
    if i >= len(rows):
        return None
    nxt = rows[i]
    if nxt.get("youtube") and (cfg.get("youtube", "browser") != "display" or ytdlp_path(app.launcher._env()) is None):
        return None                                 # Browser-Videos laufen nicht automatisch weiter
    return nxt


def video_play_list(app, name):
    """G-Taste „Videoliste“: zur Liste springen; Display-Modus spielt ab dem ersten Video, im Browser-Modus öffnet
    jeder Druck das nächste Video der Liste."""
    cfg = app.settings().get("video") or {}
    rows = video_list_items(cfg).get(name) or []
    if not rows:
        app.show("Video", [f"Liste „{name}“ ist leer"], REC_COLOR, 3)
        return
    srcs = video_sources(cfg)
    app.page = PAGE_IDS.index("video")
    app.renderer.video_src = srcs.index(("list", name))
    app.flash = None
    pos = app.__dict__.setdefault("_video_list_pos", {})
    browser = rows[0].get("youtube") and (cfg.get("youtube", "browser") != "display"
                                          or ytdlp_path(app.launcher._env()) is None)
    i = (pos.get(name, -1) + 1) % len(rows) if browser else 0
    pos[name] = i
    app.renderer.sel["video"] = i
    video_open(app, rows[i])
    app.next_draw = 0


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
