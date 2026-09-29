"""Tasten der Tastatur: G-/M-Tasten (inkl. Makroaufnahme mit MR) und Displaytasten.

Displaytasten gehen der Reihe nach an:
  1. Vorrang-Regeln: nachts weckt der erste Druck nur, der Bildschirmschoner
     endet nur, ein abgelaufener Timer bzw. eine Erinnerung wird nur bestätigt
  2. SETTINGS öffnet (ohne offenes Menü) das Profilmenü
  3. das offene Menü (menue_logik)
  4. die Tasten der angezeigten Seite (@page_keys in den Seitenmodulen)
  5. sonst: Rechts/Runter = nächste Seite, Links/Hoch = vorige Seite
"""
import time


class KeyHandling:
    # --- G- und M-Tasten ----------------------------------------------------- #
    def handle_gm_report(self, data):
        # Nur Report-ID 0x02 enthält die G-/M-Bits. Report 0x03 ist ein
        # zusätzlicher Tastatur-Report (G1 = F1 usw.) und wird ignoriert.
        if not (data and len(data) >= 4 and data[0] == 0x02):
            return
        if self.args.debug:
            print("G/M-Report:", data.hex(" "))
        value = (data[1] | (data[2] << 8)) & 0xFFFF
        pressed = value & ~self.prev_gm
        released = self.prev_gm & ~value
        self.prev_gm = value
        if pressed:
            self.activity.touch()
            self.wake()
        if pressed & MKEY_BITS["MR"]:
            self._record_key()
        for i, (name, bit) in enumerate(GKEY_BITS.items()):
            if pressed & bit:
                self._gkey_down(i, name)
            if released & bit and name in self.held:
                self._gkey_up(i, name)
        for name, bit in MKEY_BITS.items():
            if pressed & bit and name in self.modifiers:
                if self.args.debug:
                    print(f"  {name} gedrückt")
                if self.rec is None:
                    self.switch_layer(name)
                    self.apply_leds()
                    self.next_draw = 0

    def _record_key(self):
        """MR: Aufnahme starten / beenden / abbrechen."""
        rec, store, layer = self.rec, self.store, self.layer
        if rec is None:
            self.rec = {"stage": "select"}
            self.log("Makroaufnahme: G-Taste wählen")
        elif rec["stage"] == "select":
            self.rec = None
            self.show("Abgebrochen", ["Keine Aufnahme"], self.renderer.DIM, 1.5)
            self.log("Makroaufnahme abgebrochen")
        else:
            gkey = rec["gkey"]
            steps = rec["recorder"].stop()
            self.rec = None
            if steps:
                store.set(self.prof_idx, layer, gkey, {"name": f"Makro {gkey}", "steps": steps})
                n = sum(1 for s in steps if s[2] == "down")
                self.show("Gespeichert", [f"{gkey} im Profil {layer}", f"{n} Tastendrücke"], PROFILE_COLOR[layer])
                self.log(f"Makro {layer}/{gkey} gespeichert ({n} Tastendrücke)")
            elif store.delete(self.prof_idx, layer, gkey):
                self.show("Gelöscht", [f"{gkey} im Profil {layer}", f"sendet wieder F{12 + int(gkey[1:])}"], self.renderer.DIM)
                self.log(f"Makro {layer}/{gkey} gelöscht")
            else:
                self.show("Nichts aufgenommen", ["Kein Makro gespeichert"], self.renderer.DIM)
        self.apply_leds()
        self.next_draw = 0

    def _gkey_down(self, i, name):
        if self.rec is not None:
            if self.rec["stage"] == "select":
                recorder = Recorder()
                if recorder.start():
                    self.rec = {"stage": "record", "gkey": name, "recorder": recorder}
                    self.log(f"Aufnahme für {self.layer}/{name} läuft – MR zum Beenden")
                else:
                    self.rec = None
                    self.apply_leds()
                    self.show("Fehler", [recorder.error, "udev-Regel prüfen"], REC_COLOR, 4)
                    self.log(f"Aufnahme nicht möglich: {recorder.error}")
                self.next_draw = 0
            return                          # G-Tasten lösen während der Aufnahme nichts aus
        macro = self.store.get(self.prof_idx, self.layer, name)
        if run_gkey_action(self, macro, name):
            return
        # Eintrag nur mit "name" (oder keiner): die Taste sendet F13–F24 (für KDE-Kurzbefehle)
        e, mod = self.e, self.modifiers[self.layer]
        self.held[name] = mod
        with self.ui_lock:
            if mod:
                self.ui.write(e.EV_KEY, mod, 1)
            self.ui.write(e.EV_KEY, self.fkeys[i], 1)
            self.ui.syn()
        if self.args.debug:
            print(f"  {name} gedrückt -> {'Strg+' if mod == e.KEY_LEFTCTRL else 'Alt+' if mod else ''}F{13 + i}")

    def _gkey_up(self, i, name):
        e, mod = self.e, self.held.pop(name)
        with self.ui_lock:
            self.ui.write(e.EV_KEY, self.fkeys[i], 0)
            if mod:
                self.ui.write(e.EV_KEY, mod, 0)
            self.ui.syn()
        if self.args.debug:
            print(f"  {name} losgelassen")

    # --- Displaytasten ------------------------------------------------------- #
    def handle_display_report(self, data):
        if not data:
            return
        if self.args.debug:
            print("Display-Report:", data.hex(" "))
        value = data[0]
        pressed = value & ~self.prev_l
        self.prev_l = value
        if pressed:
            pressed = self._key_precedence(pressed)
        if self.menu is None and pressed & LKEY_BITS["SETTINGS"]:
            self.menu = ProfileMenu(self.prof_idx)          # SETTINGS öffnet die Profilauswahl
            self.flash = None
            self.next_draw = 0
        elif self.menu is not None:
            self.menu.on_key(self, pressed)
        else:
            handler = PAGE_KEYS.get(PAGE_IDS[self.page % len(PAGE_IDS)])
            if not (handler and handler(self, pressed)):
                self.nav_keys(pressed, LKEY_BITS["RIGHT"] | LKEY_BITS["DOWN"], LKEY_BITS["LEFT"] | LKEY_BITS["UP"])
        if self.args.debug:
            for name, bit in LKEY_BITS.items():
                if pressed & bit:
                    print(f"  Displaytaste {name}")

    def _key_precedence(self, pressed):
        """Tastendrücke, die nur wecken/beenden/bestätigen, werden hier verbraucht (→ 0)."""
        self.activity.touch()
        if self.wake():
            pressed = 0                     # erster Druck in der Nacht weckt nur das Display
            self.next_draw = 0
        if self.saver["active"]:
            pressed = 0                     # Bildschirmschoner: Tastendruck beendet ihn nur
        if self.timer.alarm and pressed:
            self.dismiss_alarm()            # abgelaufenen Timer bestätigen
            pressed = 0
        if self.modal and pressed:
            self.modal = False
            if self.flash and time.monotonic() < self.flash[1]:
                self.flash = None           # Terminerinnerung / Unwetter bestätigen
                pressed = 0
                self.next_draw = 0
        return pressed
