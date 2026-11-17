"""Hauptanwendung: Hauptschleife, Displayausgabe, Beenden.

App setzt sich zusammen aus
    AppCore        (app_kern)    Aufbau, Zustand, Profile/Seiten, Licht, Nachtmodus
    KeyHandling    (app_tasten)  G-/M-Tasten, Makroaufnahme, Displaytasten
    TimedTasks     (app_zeit)    Zeitaufgaben
und zeichnet in draw() das passende Bild (Nacht, Menü, Aufnahme, Einblendung, Seite).
"""
import signal
import time


class App(AppCore, KeyHandling, TimedTasks):
    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.reload_settings()
        self.apply_settings(first=True)
        self.update_night(force=True)
        self.apply_leds()
        try:
            self.page = int(self.settings().get("start_page", 0)) % len(PAGE_IDS)
        except (TypeError, ValueError):
            self.page = 0
        if self.page not in self.visible_pages():
            self.page = self.visible_pages()[0]
        self.log(f"G19s-Treiber {VERSION} läuft. Beenden mit Strg+C.")
        self.log(f"Makrodatei: {MACRO_FILE}")
        import queue
        reports = queue.Queue()
        self.readers = [UsbReader(self.g19, EP_GKEYS, 20, reports), UsbReader(self.g19, EP_LKEYS, 2, reports)]
        for r in self.readers:
            r.start()
        try:
            while self.running:
                try:                        # schlafen bis Tastendruck, nächstes Bild oder spätestens _max_wait
                    item = reports.get(timeout=max(0.0, min(self.next_draw - time.monotonic(), self._max_wait())))
                    while item is not None:
                        self._handle_report(*item)
                        item = reports.get_nowait()
                except queue.Empty:
                    pass
                self.poll_recording()
                now = time.monotonic()
                if not self.g19.connected:
                    self._keyboard_away(now)
                self.tick(now)
                if now >= self.next_draw:
                    self.draw(now)
        finally:
            for r in getattr(self, "readers", []):
                r.running = False
            self.shutdown()

    def _keyboard_away(self, now):
        """Tastatur abgezogen: gedrückte Tasten loslassen, auf Wiederverbindung warten."""
        if self.prev_gm or self.held:
            self.handle_gm_report(bytes([2, 0, 0, 0]))     # wie „alle Tasten losgelassen“
        self.prev_l = 0
        self.settings_down = None
        if self.g19.reconnect(now):         # wieder da: Helligkeit, Licht und Bild neu setzen
            self.set_brightness(self.night_brightness() if self.night_dark() else self.day_brightness())
            self.apply_leds()
            self._last_frame, self.next_draw = None, 0

    def _handle_report(self, source, data):
        if source == "error":
            raise data                      # unerwarteter Fehler aus dem Lese-Thread: beenden
        if source == EP_GKEYS:
            self.handle_gm_report(data)
        else:
            self.handle_display_report(data)

    def _max_wait(self):
        """Wie lange die Hauptschleife höchstens schlafen darf: kurz während Makroaufnahme und
        Blinken bzw. solange SETTINGS gehalten wird, sonst 0,25 s (Zeitaufgaben wie Erinnerungen, Nachtmodus, Menü-Zeitlimit)."""
        if self.rec is not None and self.rec.get("stage") == "record":
            return 0.02
        if self.settings_down is not None:
            return 0.05                     # SETTINGS gehalten: lang gedrückt rechtzeitig erkennen
        if self.alarm["blink_until"]:
            return 0.05
        return 0.25

    def stop(self, *_):
        self.running = False

    def draw(self, now):
        """Das Bild wählen, das gerade gezeigt werden soll, und senden."""
        r, rec, menu = self.renderer, self.rec, self.menu
        r.clock_face = self.clock_face()
        r.visual_style = self.visual_style()
        if not self.media.fast_now and PAGE_IDS[self.page % len(PAGE_IDS)] == "music":
            self.media.fast_now = True
            self.media.wake.set()           # Musikseite wurde gerade sichtbar: sofort abfragen
        if self.night_dark() and (self.settings().get("night") or {}).get("mode") == "off" and not rec and menu is None:
            self._send(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)), now)
            self.next_draw = now + 5
            return
        if not self.g19.connected:          # nichts zeichnen, solange die Tastatur fehlt
            self.next_draw = now + 1.0
            return
        try:
            img = self._compose(now)
            hold = self.settings_hold(now)
            if hold is not None:
                img = r.render_hold_bar(img, hold, PROFILE_COLOR[self.layer])
        except Exception as ex:             # eine fehlerhafte Seite darf Treiber und G-Tasten nie stoppen
            img = self._draw_error(ex)
        self._send(img, now)
        fast = rec or self.flash or (self.menu and self.menu.kind == "timer")
        preview = self.menu is not None and self.menu.kind in ("clocks", "clock_options")   # Vorschau läuft live
        if not fast and (preview or self.menu is None and PAGE_IDS[self.page % len(PAGE_IDS)] == "clock"):
            fps = clock_fps(r.clock_face, self.settings())
            if fps > 1:                     # bewegte Zifferblätter (auch nachts gedimmt flüssig)
                self.next_draw = now + 1.0 / fps
            else:                           # kurz nach jedem Sekundenwechsel, damit kein Sekundenschritt fehlt
                self.next_draw = now + (1.0 - time.time() % 1.0) + 0.02
        else:
            self.next_draw = now + (0.5 if fast else 1.0)
        video_tick(self)
        if not fast and self.menu is None and PAGE_IDS[self.page % len(PAGE_IDS)] == "video" \
                and self.video.item is not None and not self.video.paused:
            self.next_draw = now + 1.0 / VIDEO_FPS         # Video läuft: im Takt der Bilder zeichnen
        if self._visual_shown():
            self.visual.want()              # Ausgang mithören, solange die Visualisierung zu sehen ist
            if not fast:
                vis = self.settings().get("visual") or {}
                fps = int(vis.get("fps") or VISUAL_FPS)
                if vis.get("adaptive", True):           # Stille/Wortbeitrag langsamer, Lastbremse
                    snap = self.visual.snapshot()
                    fps = visual_fps(fps, r.__dict__.get("vis_ms"), not snap.get("active") or bool(snap.get("talk")))
                r.vis_fps_now = fps
                self.next_draw = now + 1.0 / fps
                last = self.__dict__.get("_vis_frame_t")      # tatsächliche Bildrate (Diagnose)
                if last is not None and 0 < now - last < 1.0:
                    self.vis_rate = self.__dict__.get("vis_rate", fps) * 0.9 + 0.1 / (now - last)
                self._vis_frame_t = now
            self._visual_backlight(now)
        else:
            self._visual_backlight_off()
        self._diag_tick(now)
        if self.settings_down is not None:
            self.next_draw = min(self.next_draw, now + 0.05)    # Haltebalken von SETTINGS füllt sich

    def _diag_tick(self, now):
        """Eigene Last einmal je Sekunde für die Hardware-Seite (CPU %, Arbeitsspeicher, Zeichenzeit und Bildrate der
        Visualisierung); solange die Visualisierung läuft, alle DIAG_LOG_EVERY Sekunden eine Zeile ins Protokoll."""
        last = self.__dict__.get("_diag_mark")
        if last and now - last[0] < 1.0:
            return
        cpu_t = time.process_time()
        diag = self.__dict__.get("diag") or {"cpu": 0.0}
        if last:
            cpu = max(0.0, (cpu_t - last[1]) / (now - last[0]) * 100)
            diag["cpu"] = cpu if diag.get("n", 0) < 3 else diag["cpu"] * 0.8 + cpu * 0.2
            diag["n"] = diag.get("n", 0) + 1
        self._diag_mark = (now, cpu_t)
        r = self.renderer
        shown = self._visual_shown()
        diag.update(rss=own_rss_mb(), ms=r.__dict__.get("vis_ms"), fps=self.__dict__.get("vis_rate"),
                    style=self.visual_style(), vis_t=now if shown else diag.get("vis_t"), now=now)
        self.diag = r.g19s_diag = diag
        if shown and diag.get("ms") is not None and now - self.__dict__.get("_diag_log_t", now - DIAG_LOG_EVERY + 30) \
                >= DIAG_LOG_EVERY:
            self._diag_log_t = now
            self.log(f"Visualisierung: Stil {VISUAL_STYLES.get(diag['style'], diag['style'])}, "
                     f"{diag['ms']:.1f} ms je Bild, {diag.get('fps') or 0:.0f} Bilder/s, CPU {diag['cpu']:.0f} %, "
                     f"{diag.get('rss') or 0:.0f} MB")

    def _visual_shown(self):
        if self.menu is not None:
            return self.menu.kind in ("visuals", "visual_options")
        return not self.rec and not self.flash and PAGE_IDS[self.page % len(PAGE_IDS)] == "visual"

    def _visual_backlight(self, now):
        """Tastaturbeleuchtung pulsiert mit dem Bass (Einstellung visual.backlight, Standard an)."""
        s = self.settings()
        if (not (s.get("visual") or {}).get("backlight", True) or self.args.keep_backlight
                or s.get("keep_backlight") or self.rec or self.night_dark()):
            self._visual_backlight_off()
            return
        vstyle = self.visual_style()
        if vstyle == "auto":                                               # Automatik: gewählter Stil
            vstyle = self.renderer.vis_auto_inner or "eq"
        snap = self.visual.snapshot()
        quiet = not snap.get("active") or snap.get("talk") or self.renderer.vis_talk   # Stille, Wortbeitrag
        k = 1.0 if quiet else round((0.15 + 0.85 * snap["bass"]) * 20) / 20
        base = PROFILE_COLOR[self.layer]
        if vstyle == "xmas" and not quiet and \
                visual_options(s, "xmas")["keys"] == "redgreen":    # Weihnachten: rot und grün im Wechsel
            base = (255, 20, 10) if snap["beats"] % 2 else (20, 220, 40)
            if self.renderer.vis_green:                                     # Feierabend: ihm ist schlecht
                base = (20, 220, 40)
        if vstyle == "dancer" and not quiet:                   # Tänzerin: Tastatur nach Wahl
            keys = visual_options(s, "dancer").get("keys", "bass")
            if self.renderer.vis_listen:                                    # sie hört zu: Tastatur atmet
                k = round((0.25 + 0.35 * (1 + math.sin(now * 2.4)) / 2) * 20) / 20
            elif keys == "hats":
                k = round((0.15 + 0.85 * math.exp(-max(0.0, snap["t"] - snap.get("hat_t", -9)) * 9)) * 20) / 20
            if keys == "stage" and self.renderer.vis_stage_color and not self.renderer.vis_listen:
                base = self.renderer.vis_stage_color
        style = vstyle
        if style == "party":                                                # Party: bunt im Takt, versteckt: dunkel
            if self.renderer.vis_party_dark:
                k, base = 0.08, (60, 70, 140)
            elif not quiet and visual_options(s, "party").get("keys", "rainbow") == "rainbow":
                base = _hue(snap["beats"] * 0.13, 0.9, 1.0)
        if style == "cellar":                                               # Keller: Glühbirne bzw. Herzschlag
            keys = visual_options(s, "cellar").get("keys", "bulb")
            if keys == "bulb":
                k, base = round(max(0.04, self.renderer.vis_bulb * (0.55 + 0.45 * k)) * 20) / 20, (255, 160, 60)
            elif keys == "red":
                beat = math.exp(-max(0.0, snap["t"] - snap.get("beat_t", -9)) * 7) if not quiet else 0.0
                k, base = round(max(0.06, beat) * 20) / 20, (255, 10, 10)
        if style == "easter" and not quiet and visual_options(s, "easter").get("keys", "pastel") == "pastel" \
                and self.renderer.vis_pastel:                       # Farbe des zuletzt bemalten Eis
            base = self.renderer.vis_pastel
        if style == "halloween" and not quiet and visual_options(s, "halloween").get("keys", "glow") == "glow" \
                and self.renderer.vis_glow:                         # Kürbisleuchten
            base = self.renderer.vis_glow
        if style == "horror" and not quiet and visual_options(s, "horror").get("keys", "scene") == "scene" \
                and self.renderer.vis_col_horror:                       # Fensterlicht bzw. Puppenrosa
            base = self.renderer.vis_col_horror
        if style == "birthday" and not quiet and visual_options(s, "birthday").get("keys", "candle") == "candle" \
                and self.renderer.vis_candle:                       # Kerzenschein
            base = self.renderer.vis_candle
        if style == "mother" and not quiet and visual_options(s, "mother").get("keys", "rose") == "rose" \
                and self.renderer.vis_rose:                         # Rosa im Takt
            base = self.renderer.vis_rose
        if style == "father" and not quiet and visual_options(s, "father").get("keys", "ember") == "ember" \
                and self.renderer.vis_ember:                        # Grillglut
            base = self.renderer.vis_ember
        if style == "newyear" and not quiet and visual_options(s, "newyear").get("keys", "burst") == "burst" \
                and self.renderer.vis_ny:
            base = self.renderer.vis_ny
        if style == "carnival" and not quiet and visual_options(s, "carnival").get("keys", "bunt") == "bunt" \
                and self.renderer.vis_cv:
            base = self.renderer.vis_cv
        if style == "oktoberfest" and not quiet and visual_options(s, "oktoberfest").get("keys", "rauten") == "rauten" \
                and self.renderer.vis_rauten:
            base = self.renderer.vis_rauten
        if style == "martin" and not quiet and visual_options(s, "martin").get("keys", "lantern") == "lantern" \
                and self.renderer.vis_lantern:
            base = self.renderer.vis_lantern
        if style == "valentine" and not quiet and visual_options(s, "valentine").get("keys", "heart") == "heart" \
                and self.renderer.vis_heart:
            base = self.renderer.vis_heart
        if style == "underwater" and not quiet and visual_options(s, "underwater").get("keys", "sea") == "sea" \
                and self.renderer.vis_sea:
            base = self.renderer.vis_sea
        if style == "farm" and not quiet and visual_options(s, "farm").get("keys", "farm") == "farm" \
                and self.renderer.vis_col_farm:
            base = self.renderer.vis_col_farm
        if style == "space" and not quiet and visual_options(s, "space").get("keys", "space") == "space" \
                and self.renderer.vis_col_space:
            base = self.renderer.vis_col_space
        if style == "arcade" and not quiet and visual_options(s, "arcade").get("keys", "hit") == "hit" \
                and self.renderer.vis_col_arcade:
            base = self.renderer.vis_col_arcade
        if style == "western" and not quiet and visual_options(s, "western").get("keys", "lamp") == "lamp" \
                and self.renderer.vis_col_western:
            base = self.renderer.vis_col_western
        if style == "campfire" and not quiet and visual_options(s, "campfire").get("keys", "fire") == "fire" \
                and self.renderer.vis_fire:
            base = self.renderer.vis_fire
        if style == "cats" and not quiet and visual_options(s, "cats").get("keys", "eyes") == "eyes" \
                and self.renderer.vis_col_cats:
            base = self.renderer.vis_col_cats
        if style == "jazz" and not quiet and visual_options(s, "jazz").get("keys", "mood") != "layer" \
                and self.renderer.vis_col_jazz:                             # Club-Licht bzw. Bläser-Gold
            base, k = tuple(c // 8 * 8 for c in self.renderer.vis_col_jazz), 1.0
        if style in ("silk", "ember", "pulse") and not quiet \
                and visual_options(s, style).get("keys", "glow") == "glow":       # Stimmung: Farbe des Bildes
            col = getattr(self.renderer, "vis_col_" + style, None)
            if col:
                base, k = tuple(c // 8 * 8 for c in col), 1.0              # Helligkeit steckt in der Farbe (gestuft)
        if style == "metal" and visual_options(s, "metal").get("keys", "fire") == "fire":   # Feuerkörbe
            k, base = round(max(0.12, self.renderer.vis_fire) * 20) / 20, (255, 100, 16)
        color = tuple(int(c * k) for c in base)
        strobe = False
        if vstyle in ("lights", "dancer") and not quiet:     # Stroboskop: Tastatur blitzt mit
            lo = visual_options(s, vstyle)
            if lo.get("strobe", "off") != "off" and lo.get("strobe_keys") and \
                    0 <= snap["t"] - self.renderer.vis_strobe_t < 0.12:
                color, strobe = (255, 255, 255), True
        if color != self._vis_light and (strobe or now - self._vis_light_t >= 0.1):  # sonst höchstens 10×/s
            self._vis_light, self._vis_light_t = color, now
            try:
                self.g19.set_backlight(*color)
            except Exception:               # Beleuchtung ist nicht kritisch
                pass

    def _visual_backlight_off(self):
        if self._vis_light is not None:
            self._vis_light = None
            self.apply_leds()               # wieder die normale Farbe der Ebene

    def _compose(self, now):
        """Menü, Aufnahme, Einblendung oder Seite zeichnen."""
        r, rec, menu = self.renderer, self.rec, self.menu
        if menu is not None and not rec:
            img = menu.draw(self, now)      # None = Menü hat sich geschlossen (z. B. Timer beendet)
            if img is None:
                img = r.render(self.page, self.layer, self.store.keys(self.prof_idx))
        elif rec and rec["stage"] == "select":
            img = r.render_message("Makro aufnehmen", [f"Profil {self.layer}", "G-Taste drücken", "MR = abbrechen"],
                                   REC_COLOR)
        elif rec:
            img = r.render_message(f"● Aufnahme {rec['gkey']}", [f"{rec['recorder'].keycount} Tastendrücke",
                                                                "Tasten jetzt tippen", "MR = speichern"], REC_COLOR)
        elif self.flash and now < self.flash[1]:
            img = self.flash[0]()
        else:
            self.flash = None
            img = r.render(self.page, self.layer, self.store.keys(self.prof_idx))
        return img

    def _draw_error(self, ex):
        """Fehlerseite statt Absturz; jeder Fehler steht einmal (mit Ort) im Protokoll."""
        import traceback
        where = self.menu.kind if self.menu is not None else PAGE_NAMES[self.page % len(PAGE_IDS)]
        text = f"{type(ex).__name__}: {ex}"
        if (where, text) != self._last_draw_error:
            self._last_draw_error = (where, text)
            self.log(f"Anzeige-Fehler auf „{where}“: {text}\n" + "".join(traceback.format_exc(limit=-8)).rstrip())   # innerste 8 Ebenen: dort steht die Ursache
        if self.menu is not None:
            self.menu = None                # kaputtes Menü schließen, damit die Tasten wieder gehen
        self.flash = None
        try:
            return self.renderer.render_message("Anzeige-Fehler", [where, text[:40], "Details: Protokoll"], REC_COLOR)
        except Exception:                   # selbst die Meldung geht nicht: schwarzes Bild
            return Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

    FRAME_REFRESH = 10.0            # unverändertes Bild spätestens nach so vielen Sekunden erneut senden

    def _send(self, img, now):
        """Bild nur senden, wenn es sich geändert hat (spart USB-Verkehr und CPU); zur Sicherheit
        – etwa nach kurzem Abziehen der Tastatur – alle FRAME_REFRESH Sekunden trotzdem."""
        data = img.tobytes()
        if data == self._last_frame and now - self._last_sent < self.FRAME_REFRESH:
            return
        self.g19.send_frame(img)
        self._last_frame, self._last_sent = data, now

    def shutdown(self):
        if self.rec and self.rec["stage"] == "record":
            self.rec["recorder"].stop()
        try:
            self.g19.send_frame(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))
        except Exception:                   # Tastatur evtl. schon abgezogen
            pass
        for s in (self.media, self.slideshow, self.weather, self.calendar, self.activity, self.notifier,
                  self.mediakeys, self.visual):
            s.stop()
        self.radio.stop()
        self.ui.close()
        self.g19.close()
        print("Beendet.")


def run(args):
    App(args).run()
