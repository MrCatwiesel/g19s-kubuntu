"""Eingaben: Makroaufnahme (liest die Tastatur mit), Makro abspielen, Aktivität für den Bildschirmschoner."""


class Recorder:
    """Liest während der Aufnahme die normale Tastatur (046d:c228) mit."""

    def __init__(self):
        self.devices = []
        self.steps = []
        self.down = set()
        self.last = None
        self.error = None

    def start(self):
        from evdev import InputDevice, list_devices, ecodes as e
        self.devices, self.steps, self.down, self.last = [], [], set(), None
        denied = False
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except PermissionError:
                denied = True
                continue
            except OSError:
                continue
            if (dev.info.vendor == VENDOR_ID and dev.info.product == KEYBOARD_PRODUCT_ID
                    and e.EV_KEY in dev.capabilities()):
                self.devices.append(dev)
            else:
                dev.close()
        if not self.devices:
            # list_devices() liefert nur lesbare Geräte – fehlende Rechte sehen
            # daher genauso aus wie eine nicht gefundene Tastatur
            self.error = "Kein Lesezugriff auf Tastatur"
            return False
        return True

    def poll(self):
        from evdev import ecodes as e
        for dev in self.devices:
            try:
                for ev in dev.read():
                    if ev.type != e.EV_KEY or ev.value not in (0, 1):
                        continue
                    if ev.value == 0 and ev.code not in self.down:
                        continue  # Loslassen einer Taste, die vor der Aufnahme gedrückt war
                    t = ev.timestamp()
                    wait = 0 if self.last is None else int(round((t - self.last) * 1000))
                    self.last = t
                    if ev.value == 1:
                        self.down.add(ev.code)
                    else:
                        self.down.discard(ev.code)
                    self.steps.append([wait, key_name(ev.code), "down" if ev.value else "up"])
            except BlockingIOError:
                pass
            except OSError:
                pass

    def stop(self):
        self.poll()
        for code in list(self.down):
            self.steps.append([TAP_MS, key_name(code), "up"])
        for dev in self.devices:
            try:
                dev.close()
            except Exception:               # Gerät evtl. schon weg – Aufnahme trotzdem beenden
                pass
        self.devices = []
        return self.steps

    @property
    def keycount(self):
        return sum(1 for s in self.steps if s[2] == "down")


class Player:
    def __init__(self, ui, lock):
        self.ui, self.lock = ui, lock
        self.thread = None

    @property
    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def play(self, steps):
        if self.busy:
            return False
        self.thread = threading.Thread(target=self._run, args=(steps,), daemon=True)
        self.thread.start()
        return True

    def _run(self, steps):
        from evdev import ecodes as e
        pressed = set()
        try:
            for wait, code, value in steps:
                time.sleep(max(MIN_WAIT_MS, min(wait, MAX_WAIT_MS)) / 1000)
                with self.lock:
                    self.ui.write(e.EV_KEY, code, value)
                    self.ui.syn()
                (pressed.add if value else pressed.discard)(code)
        finally:
            with self.lock:
                for code in pressed:
                    self.ui.write(e.EV_KEY, code, 0)
                self.ui.syn()


# --------------------------------------------------------------------------- #
# Aktivität an Tastatur/Maus erkennen (für den Bildschirmschoner)
# --------------------------------------------------------------------------- #
class ActivityWatcher(threading.Thread):
    """Merkt sich nur den Zeitpunkt der letzten Eingabe – Tasteninhalte werden verworfen."""

    def __init__(self, log=print):
        super().__init__(daemon=True)
        self.log = log
        self.running = True
        self.last = time.monotonic()
        self.available = None           # None = unbekannt, False = keine Leserechte

    def touch(self):
        self.last = time.monotonic()

    def idle(self):
        return time.monotonic() - self.last

    def stop(self):
        self.running = False

    def _open_devices(self):
        from evdev import InputDevice, list_devices, ecodes as e
        devs = []
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except OSError:
                continue
            caps = dev.capabilities()
            if e.EV_KEY in caps or e.EV_REL in caps or e.EV_ABS in caps:
                devs.append(dev)
            else:
                dev.close()
        return devs

    def run(self):
        import select
        devs, rescan = [], 0.0
        while self.running:
            now = time.monotonic()
            if now >= rescan:
                for d in devs:
                    try:
                        d.close()
                    except Exception:       # Thread darf nie abbrechen
                        pass
                try:
                    devs = self._open_devices()
                except Exception:           # z. B. evdev-Fehler beim Abfragen der Fähigkeiten
                    devs = []
                if not devs and self.available is not False:
                    self.log("Bildschirmschoner: keine Eingabegeräte lesbar – zählt nur G-19s-Tasten")
                self.available = bool(devs)
                rescan = now + 60
            if not devs:
                time.sleep(2)
                continue
            try:
                ready, _, _ = select.select(devs, [], [], 1.0)
            except (OSError, ValueError):
                rescan = 0
                continue
            for d in ready:
                try:
                    for _ in d.read():
                        pass
                    self.last = time.monotonic()
                except (BlockingIOError, OSError):
                    pass
