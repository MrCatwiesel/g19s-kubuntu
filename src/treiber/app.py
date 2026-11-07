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
        if self._visual_shown():
            self.visual.want()              # Ausgang mithören, solange die Visualisierung zu sehen ist
            if not fast:
                fps = int((self.settings().get("visual") or {}).get("fps") or VISUAL_FPS)
                self.next_draw = now + 1.0 / fps
            self._visual_backlight(now)
        else:
            self._visual_backlight_off()
        if self.settings_down is not None:
            self.next_draw = min(self.next_draw, now + 0.05)    # Haltebalken von SETTINGS füllt sich

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
        snap = self.visual.snapshot()
        quiet = not snap.get("active") or snap.get("talk") or self.renderer.vis_talk   # Stille, Wortbeitrag
        k = 1.0 if quiet else round((0.15 + 0.85 * snap["bass"]) * 20) / 20
        base = PROFILE_COLOR[self.layer]
        if self.visual_style() == "xmas" and not quiet and \
                visual_options(s, "xmas")["keys"] == "redgreen":    # Weihnachten: rot und grün im Wechsel
            base = (255, 20, 10) if snap["beats"] % 2 else (20, 220, 40)
            if self.renderer.vis_green:                                     # Feierabend: ihm ist schlecht
                base = (20, 220, 40)
        if self.visual_style() == "dancer" and not quiet:                   # Tänzerin: Tastatur nach Wahl
            keys = visual_options(s, "dancer").get("keys", "bass")
            if self.renderer.vis_listen:                                    # sie hört zu: Tastatur atmet
                k = round((0.25 + 0.35 * (1 + math.sin(now * 2.4)) / 2) * 20) / 20
            elif keys == "hats":
                k = round((0.15 + 0.85 * math.exp(-max(0.0, snap["t"] - snap.get("hat_t", -9)) * 9)) * 20) / 20
            if keys == "stage" and self.renderer.vis_stage_color and not self.renderer.vis_listen:
                base = self.renderer.vis_stage_color
        color = tuple(int(c * k) for c in base)
        strobe = False
        if self.visual_style() in ("lights", "dancer") and not quiet:     # Stroboskop: Tastatur blitzt mit
            lo = visual_options(s, self.visual_style())
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
            self.log(f"Anzeige-Fehler auf „{where}“: {text}\n" + "".join(traceback.format_exc(limit=4)).rstrip())
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
