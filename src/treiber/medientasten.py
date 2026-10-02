"""Medientasten der Tastatur übernehmen: Lautstärkerad, Stumm, Play/Pause, Weiter, Zurück, Stopp.

Die G19s meldet diese Tasten über ein eigenes Eingabegerät „G19s Gaming Keyboard Consumer Control“
(046d:c228, ohne normale Tasten). Der Treiber übernimmt es exklusiv (grab): Die Tasten wirken dann
immer auf diesen Rechner – auch wenn ein Remote-Desktop-Fenster (xfreerdp) die Tastatur für sich
beansprucht und KDE seine Tastenkürzel abschaltet. Tippen, Tastenkürzel und die Zwischenablage laufen
weiter über das normale Tastaturgerät und bleiben unberührt.

Abschaltbar mit "media_keys": false – dann gibt der Treiber das Gerät sofort frei und KDE übernimmt
wieder. Beendet sich der Treiber, gibt Linux das Gerät von selbst frei.
"""

# Taste -> (Art, Aktion). Andere Tasten des Geräts werden unverändert weitergegeben.
MEDIA_KEYS = {"KEY_VOLUMEUP": ("volume", "up"), "KEY_VOLUMEDOWN": ("volume", "down"),
              "KEY_MUTE": ("volume", "mute"), "KEY_PLAYPAUSE": ("media", "play-pause"),
              "KEY_NEXTSONG": ("media", "next"), "KEY_PREVIOUSSONG": ("media", "previous"),
              "KEY_STOPCD": ("media", "stop")}


def playerctl_any(action, env=None):
    """Medientaste ohne bekannten Player: an irgendeinen MPRIS-Player geben (wie KDE)."""
    import shutil
    if not shutil.which("playerctl"):
        return False
    try:
        subprocess.Popen(["playerctl", action], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def plasma_volume_osd(pct, env=None):
    """KDE-Lautstärkeanzeige auslösen (best effort; Plasma 6 erwartet zwei Werte, ältere einen)."""
    import shutil
    q = shutil.which("qdbus6") or shutil.which("qdbus")
    if not q:
        return
    base = [q, "org.kde.plasmashell", "/org/kde/osdService", "org.kde.osdService.volumeChanged", str(int(pct))]
    for cmd in (base + ["100"], base):
        try:
            if subprocess.run(cmd, env=env, capture_output=True, timeout=2).returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            return


class MediaKeys(threading.Thread):
    """Liest das Medientasten-Gerät exklusiv und meldet jede Taste an on_key(code, value)."""
    RESCAN = 5.0                    # so oft nach dem Gerät suchen, solange es fehlt

    def __init__(self, enabled, on_key, log=print):
        super().__init__(daemon=True)
        self.enabled, self.on_key, self.log = enabled, on_key, log
        self.dev = None
        self.running = True
        self._said = None           # zuletzt gemeldeter Zustand (gegen Wiederholungen im Protokoll)

    def stop(self):
        self.running = False

    def _say(self, key, msg):
        if self._said != key:
            self._said = key
            self.log(msg)

    @staticmethod
    def find_device():
        """Das Consumer-Control-Gerät der G19s: 046d:c228, hat Medientasten, aber keine Buchstaben."""
        from evdev import InputDevice, list_devices, ecodes as e
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except OSError:
                continue
            keys = dev.capabilities().get(e.EV_KEY, [])
            if (dev.info.vendor == VENDOR_ID and dev.info.product == KEYBOARD_PRODUCT_ID
                    and (e.KEY_VOLUMEUP in keys or e.KEY_PLAYPAUSE in keys) and e.KEY_A not in keys):
                return dev
            dev.close()
        return None

    def _release(self, msg=None):
        dev, self.dev = self.dev, None
        if dev is None:
            return
        for fn in (dev.ungrab, dev.close):
            try:
                fn()
            except OSError:             # Gerät schon weg (abgezogen) – nichts mehr freizugeben
                pass
        if msg:
            self._say(msg, msg)

    def _take(self):
        try:
            dev = self.find_device()
        except Exception as ex:         # evdev-Fehler beim Abfragen darf den Faden nie beenden
            self._say("err", f"Medientasten: Suche fehlgeschlagen ({ex})")
            return
        if dev is None:
            self._say("none", "Medientasten: Gerät nicht gefunden – KDE behält sie")
            return
        try:
            dev.grab()
        except OSError as ex:           # z. B. EBUSY: ein anderes Programm hat es schon
            self._say("busy", f"Medientasten: nicht übernommen ({ex}) – KDE behält sie")
            dev.close()
            return
        self.dev = dev
        self._say("ok", f"Medientasten übernommen ({dev.name}) – wirken auch im Remote-Desktop")

    def run(self):
        import select
        from evdev import ecodes as e
        next_scan = 0.0
        try:
            while self.running:
                want = bool(self.enabled())
                if self.dev is not None and not want:
                    self._release("Medientasten an KDE zurückgegeben")
                if self.dev is None:
                    now = time.monotonic()
                    if want and now >= next_scan:
                        next_scan = now + self.RESCAN
                        self._take()
                    if self.dev is None:
                        time.sleep(0.5)
                        continue
                try:
                    ready, _, _ = select.select([self.dev], [], [], 1.0)
                except (OSError, ValueError):
                    self._release("Medientasten: Gerät getrennt – suche erneut")
                    continue
                if not ready:
                    continue
                try:
                    events = list(self.dev.read())
                except BlockingIOError:
                    continue
                except OSError:
                    self._release("Medientasten: Gerät getrennt – suche erneut")
                    continue
                for ev in events:
                    if ev.type == e.EV_KEY:
                        try:
                            self.on_key(ev.code, ev.value)
                        except Exception as ex:     # eine fehlgeschlagene Aktion darf die Tasten nie lahmlegen
                            self.log(f"Medientaste: Fehler {type(ex).__name__}: {ex}")
        finally:
            self._release()
