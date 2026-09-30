"""Zeitaufgaben der Hauptschleife – werden bei jedem Durchlauf aufgerufen.

Reihenfolge je Durchlauf (tick):
  Menü-/Markierungs-Zeitlimits, Mikrofonstatus, Einschlaftimer,
  Unwetter/Terminerinnerung/Radiowecker (sofort bei neuen Daten, sonst alle 20 s),
  automatische Sicherung (alle 10 min prüfen), Timer und Blinken,
  Dateien neu laden (alle 2 s), Nachtmodus, Bildschirmschoner, Benachrichtigungen.
"""
import os
import threading
import time


class TimedTasks:
    def poll_recording(self):
        """Laufende Makroaufnahme mitlesen (zeigt die Anzahl der Tastendrücke)."""
        if self.rec and self.rec["stage"] == "record":
            before = self.rec["recorder"].keycount
            self.rec["recorder"].poll()
            if self.rec["recorder"].keycount != before:
                self.next_draw = 0

    def tick(self, now):
        self._expire_selections(now)
        if self.mic.pop("changed", False):
            self.apply_leds()
            self.next_draw = 0
        self._sleep_timer(now)
        fresh = (self.calendar.snapshot()[2], self.alerts.snapshot()[2])
        if now >= self.periodic["remind"] or fresh != self.periodic["fresh"]:
            self.periodic["remind"], self.periodic["fresh"] = now + 20, fresh
            self.warn_due()
            self.remind_due()
            self.alarm_clock_due()
        if now >= self.periodic["backup"]:
            self.periodic["backup"] = now + 600
            self.backup_due()
        self._timer_tick(now)
        self._blink(now)
        badge = self.timer.badge(now) if (self.timer.active and not (self.menu and self.menu.kind == "timer")) else ""
        if badge != self.renderer.timer_badge:
            self.renderer.timer_badge = badge
            self.next_draw = min(self.next_draw, now)
        if now >= self.next_reload:
            self._reload_files()
            self.next_reload = now + 2.0
        self._night_rewake(now)
        self._screensaver()
        self._notifications()

    # --- Zeitlimits ------------------------------------------------------- #
    def _expire_selections(self, now):
        if self.menu is not None and self.menu.expired(now):
            self.menu = None                # Menü schließt sich nach 30 s ohne Tastendruck
            self.next_draw = 0
        r = self.renderer
        if r.cal_sel is not None and self.menu is None and now - self.sel_t["calendar"] > SELECTION_TIMEOUT:
            r.cal_sel = None                # Terminmarkierung verschwindet wieder
            self.next_draw = 0
        for k in r.sel:
            if r.sel[k] is not None and self.menu is None and now - self.sel_t[k] > SELECTION_TIMEOUT:
                r.sel[k] = None
                self.next_draw = 0

    # --- Einschlaftimer ------------------------------------------------------ #
    def _sleep_timer(self, now):
        sleep = self.sleep
        if not sleep["until"]:
            return
        left = sleep["until"] - now
        badge = f"{max(1, int(left // 60) + (1 if left % 60 else 0))}"
        if left <= 0:
            sleep["until"] = 0.0
            badge = ""
            info = self.media.snapshot()[0]
            if self.radio.playing:
                self.radio.stop()
                self.media.wake.set()
            elif info and info.get("status") == "Playing":
                threading.Thread(target=self.media.control, args=("play-pause",), daemon=True).start()
            self.log("Einschlaftimer abgelaufen – Musik aus")
            self.show("Gute Nacht", ["Musik ausgeschaltet"], PROFILE_COLOR[self.layer], 3)
        if badge != self.renderer.sleep_badge:
            self.renderer.sleep_badge = badge
            self.next_draw = 0

    # --- Einblendungen mit Vorrang (Unwetter, Termine) ---------------------- #
    def _attention(self, draw_fn, seconds, blink):
        """Wichtige Einblendung: weckt das Display, blinkt, Signalton; nächster Tastendruck bestätigt."""
        self.wake(120)
        self.popup(draw_fn, seconds)
        self.modal = True
        self.alarm.update(blink_until=time.monotonic() + blink, blink_at=0.0)
        if self.settings().get("timer_sound", True):
            play_alarm(self.launcher._env(), 1)

    def warn_due(self):
        """Neue Unwetterwarnung (ab Stufe „markant“) einmal groß einblenden."""
        if not (self.settings().get("warnings") or {}).get("popup", True):
            return
        data = self.alerts.snapshot()[0] or {}
        for a in data.get("alerts") or []:
            if a["id"] in self.seen_alerts:
                continue
            self.seen_alerts.add(a["id"])
            if SEVERITY_RANK.get(a["severity"], 0) < 2:
                continue
            label, color = SEVERITY.get(a["severity"], SEVERITY["minor"])
            until = a["expires"].strftime("%H:%M") if a.get("expires") else ""
            self.log(f"{label}: {a['event']}")
            self._attention(lambda a=a, l=label, c=color, u=until: self.renderer.render_message(
                "⚠ " + l, [a["event"], (f"bis {u} Uhr" if u else ""), "Details: Seite „Unwetter“"], c), 15, 4)
            return

    def remind_due(self):
        """Termine ankündigen, die in den nächsten N Minuten beginnen."""
        import datetime as dt
        minutes = int((self.settings().get("calendar") or {}).get("remind") or 0)
        if minutes <= 0:
            return
        data = self.calendar.snapshot()[0] or {}
        now_dt = dt.datetime.now().astimezone()
        for ev in data.get("items") or []:
            if ev.get("allday") or ev.get("cal") in self.renderer.cal_hidden:
                continue
            delta = (ev["start"] - now_dt).total_seconds()
            key = (ev.get("cal"), ev.get("title"), ev["start"].isoformat())
            if -60 <= delta <= minutes * 60 and key not in self.reminded:
                self.reminded.add(key)
                if delta < -30:
                    continue                # schon angefangen (z. B. nach dem Start des Treibers)
                cal = next((c for c in self.calendar_list() if c["key"] == ev.get("cal")), None)
                mins = max(0, int(round(delta / 60)))
                color = ev.get("color") or (cal or {}).get("color")
                self.log(f"Terminerinnerung: {ev.get('title')} um {ev['start'].strftime('%H:%M')}")
                self._attention(lambda ev=ev, m=mins, c=color, n=(cal or {}).get("name", ""):
                                self.renderer.render_reminder(ev, m, c, n), 20, 3)
                return                      # höchstens eine Erinnerung gleichzeitig

    def alarm_clock_due(self):
        """Radiowecker: zur eingestellten Zeit den gewählten Sender einschalten."""
        a = self.settings().get("alarm_clock") or {}
        if not a.get("enabled"):
            return
        today = time.strftime("%Y-%m-%d")
        if self.periodic["alarm_day"] == today or time.strftime("%H:%M") != str(a.get("time") or ""):
            return
        if time.localtime().tm_wday not in (a.get("days") or []):
            return
        self.periodic["alarm_day"] = today
        stations = [s for s in self.settings().get("stations", []) if s.get("url")]
        st = next((s for s in stations if s["url"] == a.get("station")), stations[0] if stations else None)
        self.log("Radiowecker: " + (st.get("name") or st["url"] if st else "kein Sender"))
        self.wake(600)
        if st:
            threading.Thread(target=self.radio_play, args=(st, False), daemon=True).start()
        self.popup(lambda: self.renderer.render_message("Guten Morgen!", [time.strftime("%H:%M"),
                   (st or {}).get("name") or ""], PROFILE_COLOR[self.layer]), 8)

    def backup_due(self):
        """Automatische Sicherung, wenn die letzte älter als eingestellt ist (läuft im Hintergrund)."""
        b = self.settings().get("backup") or {}
        target = b.get("target") or "folder"
        if not b.get("enabled") or not b.get("folder" if target == "folder" else "url") or self.periodic["backup_busy"]:
            return
        try:
            last = float(load_state().get("last_backup") or 0)
        except (TypeError, ValueError):
            last = 0
        if time.time() - last < max(1, int(b.get("days") or 7)) * 86400:
            return
        self.periodic["backup_busy"] = True

        def work():
            try:
                path = auto_backup(b, b.get("keep", 8))
                save_state(last_backup=time.time(), last_backup_file=path, last_backup_error="")
                self.log(f"Automatische Sicherung: {path}")
            except Exception as ex:         # im Hintergrund: jeden Fehler melden statt still abbrechen
                save_state(last_backup_error=str(ex))
                self.log(f"Automatische Sicherung fehlgeschlagen: {ex}")
            finally:
                try:
                    self.state_mtime = os.path.getmtime(STATE_FILE)
                except OSError:
                    pass
                self.periodic["backup_busy"] = False
        threading.Thread(target=work, daemon=True).start()

    # --- Timer --------------------------------------------------------------- #
    def _timer_tick(self, now):
        tev = self.timer.tick(now)
        if not tev:
            return
        t_color = PROFILE_COLOR[self.layer]
        if self.settings().get("timer_sound", True):
            play_alarm(self.launcher._env(), 3 if tev == "done" else 1)
        if tev == "done":
            self.log(f"{timer_label(self.timer.cfg or {})} abgelaufen")
            self.menu = TimerView()
            self.flash = None
            self.alarm.update(blink_until=now + 20, blink_at=0.0)
            self.wake(120)
        else:
            txt = "Pause!" if tev == "break" else "Weiterarbeiten"
            self.log(f"Pomodoro: {txt}")
            rounds = self.timer.rounds
            self.popup(lambda txt=txt, c=t_color, r=rounds: self.renderer.render_message(
                "Pomodoro", [txt, f"{r} Runde{'' if r == 1 else 'n'} geschafft"], c), 5)
            self.alarm.update(blink_until=now + 4, blink_at=0.0)
        self.next_draw = 0

    def _blink(self, now):
        """Beleuchtung rot/gelb blinken lassen (Timer, Erinnerung, Unwetter)."""
        alarm = self.alarm
        if not alarm["blink_until"]:
            return
        if now >= alarm["blink_until"]:
            alarm["blink_until"] = 0.0
            self.apply_leds()
        elif now >= alarm["blink_at"]:
            alarm["on"] = not alarm["on"]
            alarm["blink_at"] = now + 0.4
            try:
                self.g19.set_backlight(*((255, 30, 30) if alarm["on"] else (255, 200, 40)))
            except Exception:               # Beleuchtung ist nicht kritisch
                pass

    # --- Dateien, Nacht, Bildschirmschoner, Benachrichtigungen --------------- #
    def _reload_files(self):
        """macros.json, state.json und settings.json auf Änderungen prüfen."""
        if self.store.reload():
            self.apply_profile()            # Farben/Namen/Seiten können sich geändert haben
            self.apply_leds()
            self.fix_page()
        self.check_state_file()
        if self.reload_settings():
            self.apply_settings()
            self.update_night(force=True)
            if self.page not in self.visible_pages() and not self.saver["active"]:
                self.page = self.visible_pages()[0]
            self.next_draw = 0
        self.update_night()
        self.launcher.reap()

    def _night_rewake(self, now):
        """Nachts geweckt: nach Ablauf wieder abdunkeln."""
        if self.night["active"] and self.night["wake_until"] and now >= self.night["wake_until"]:
            self.night["wake_until"] = 0.0
            self.set_brightness(self.night_brightness())
            self.apply_leds()
            self.next_draw = 0

    def _screensaver(self):
        ss, saver = self.settings().get("screensaver") or {}, self.saver
        if saver["active"] and self.activity.last > saver["since"]:
            saver["active"] = False
            if saver["page"] is not None:
                self.page = saver["page"]
            self.next_draw = 0
        elif (ss.get("enabled") and not saver["active"] and not self.rec and self.menu is None
              and self.activity.idle() >= max(0.02, float(ss.get("minutes") or 5)) * 60):
            target = PAGE_IDS.index(ss.get("page")) if ss.get("page") in PAGE_IDS else Renderer.SLIDES_PAGE
            if self.page != target:
                saver.update(active=True, page=self.page, since=time.monotonic())
                self.page = target
                self.next_draw = 0

    def _notifications(self):
        if self.popups and not self.rec and self.menu is None:
            app_name, summary, body = self.popups.popleft()
            if not self.night_dark():
                secs = max(2, min(30, int((self.settings().get("notifications") or {}).get("seconds") or 6)))
                color = PROFILE_COLOR[self.layer]
                self.popup(lambda: self.renderer.render_notification(app_name, summary, body, color), secs)
                self.log(f"Benachrichtigung: {app_name} – {summary}")
