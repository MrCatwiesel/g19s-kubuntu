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
        self.log("G19s-Treiber läuft. Beenden mit Strg+C.")
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
                self.tick(now)
                if now >= self.next_draw:
                    self.draw(now)
        finally:
            for r in getattr(self, "readers", []):
                r.running = False
            self.shutdown()

    def _handle_report(self, source, data):
        if source == "error":
            raise data                      # USB-Fehler aus dem Lese-Thread: wie bisher beenden
        if source == EP_GKEYS:
            self.handle_gm_report(data)
        else:
            self.handle_display_report(data)

    def _max_wait(self):
        """Wie lange die Hauptschleife höchstens schlafen darf: kurz während Makroaufnahme und
        Blinken, sonst 0,25 s (Zeitaufgaben wie Erinnerungen, Nachtmodus, Menü-Zeitlimit)."""
        if self.rec is not None and self.rec.get("stage") == "record":
            return 0.02
        if self.alarm["blink_until"]:
            return 0.05
        return 0.25

    def stop(self, *_):
        self.running = False

    def draw(self, now):
        """Das Bild wählen, das gerade gezeigt werden soll, und senden."""
        r, rec, menu = self.renderer, self.rec, self.menu
        r.clock_face = self.clock_face()
        if not self.media.fast_now and PAGE_IDS[self.page % len(PAGE_IDS)] == "music":
            self.media.fast_now = True
            self.media.wake.set()           # Musikseite wurde gerade sichtbar: sofort abfragen
        if self.night_dark() and (self.settings().get("night") or {}).get("mode") == "off" and not rec and menu is None:
            self._send(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)), now)
            self.next_draw = now + 5
            return
        try:
            img = self._compose(now)
        except Exception as ex:             # eine fehlerhafte Seite darf Treiber und G-Tasten nie stoppen
            img = self._draw_error(ex)
        self._send(img, now)
        fast = rec or self.flash or (self.menu and self.menu.kind == "timer")
        preview = self.menu is not None and self.menu.kind == "clocks"   # Zifferblatt-Vorschau läuft live
        if not fast and (preview or self.menu is None and PAGE_IDS[self.page % len(PAGE_IDS)] == "clock"):
            fps = clock_fps(r.clock_face, self.settings())
            if fps > 1 and not self.night_dark():   # bewegte Zifferblätter; nachts (gedimmt) 1 Bild/s
                self.next_draw = now + 1.0 / fps
            else:                           # kurz nach jedem Sekundenwechsel, damit kein Sekundenschritt fehlt
                self.next_draw = now + (1.0 - time.time() % 1.0) + 0.02
        else:
            self.next_draw = now + (0.5 if fast else 1.0)

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
        for s in (self.media, self.slideshow, self.weather, self.calendar, self.activity, self.notifier):
            s.stop()
        self.radio.stop()
        self.ui.close()
        self.g19.close()
        print("Beendet.")


def run(args):
    App(args).run()
