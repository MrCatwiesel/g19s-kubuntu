"""Zugriff auf die G19s über USB: Displaybild senden, Tasten lesen, Beleuchtung, Helligkeit."""


# 512-Byte-Header, der jedem Displaybild vorangestellt wird
LCD_HEADER = bytes(
    [0x10, 0x0F, 0x00, 0x58, 0x02, 0x00, 0x00, 0x00,
     0x00, 0x00, 0x00, 0x3F, 0x01, 0xEF, 0x00, 0x0F]
    + list(range(16, 256))
    + list(range(256))
)
assert len(LCD_HEADER) == 512


class UsbReader(threading.Thread):
    """Liest einen Tasten-Endpunkt blockierend (Zeitlimit READ_TIMEOUT_MS) und legt jeden Report in
    die Warteschlange. So muss die Hauptschleife nicht ständig nachsehen, sondern wacht nur bei einem
    Tastendruck oder zum nächsten Bild auf. Abziehen der Tastatur behandelt Keyboard (read() wartet
    dann nur); ein unerwarteter Fehler landet als ("error", Ausnahme) in der Warteschlange."""

    READ_TIMEOUT_MS = 1000

    def __init__(self, g19, endpoint, size, queue):
        super().__init__(daemon=True)
        self.g19, self.endpoint, self.size, self.queue = g19, endpoint, size, queue
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.g19.read(self.endpoint, self.size, self.READ_TIMEOUT_MS)
            except Exception as ex:          # unerwarteter Fehler: Treiber beenden (systemd startet neu)
                self.queue.put(("error", ex))
                return
            if data:
                self.queue.put((self.endpoint, data))


# --------------------------------------------------------------------------- #
# USB-Zugriff
# --------------------------------------------------------------------------- #
class DeviceMissing(Exception):
    """G19s nicht eingesteckt."""


class DeviceAccess(Exception):
    """G19s gefunden, aber nicht nutzbar (Rechte/udev-Regel)."""


class G19:
    def __init__(self):
        import usb.core
        import usb.util
        self.usb_core, self.usb_util = usb.core, usb.util

        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if dev is None:
            raise DeviceMissing("G19s (046d:c229) nicht gefunden – ist die Tastatur eingesteckt?")
        self.dev = dev

        for intf in (0, 1):
            try:
                if dev.is_kernel_driver_active(intf):
                    dev.detach_kernel_driver(intf)
            except usb.core.USBError as ex:
                usb.util.dispose_resources(dev)
                raise DeviceAccess(
                    f"Kann Interface {intf} nicht übernehmen: {ex}\n"
                    "Ist die udev-Regel installiert und die Tastatur neu eingesteckt?"
                )
        try:
            dev.set_configuration()
        except usb.core.USBError:
            pass  # bereits konfiguriert
        for intf in (0, 1):
            usb.util.claim_interface(dev, intf)

    def read(self, endpoint, size, timeout_ms):
        """Liest einen Interrupt-Report; gibt None bei Timeout zurück."""
        try:
            return bytes(self.dev.read(endpoint, size, timeout=timeout_ms))
        except self.usb_core.USBTimeoutError:
            return None
        except self.usb_core.USBError as ex:
            if ex.errno == 110:  # ETIMEDOUT bei älteren pyusb-Versionen
                return None
            raise

    def send_frame(self, img):
        """Schickt ein 320x240-PIL-Bild ans Display (RGB565, spaltenweise)."""
        a = np.asarray(img.convert("RGB"), dtype=np.uint16)
        rgb565 = ((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5) | (a[:, :, 2] >> 3)
        data = np.ascontiguousarray(rgb565.T).astype("<u2").tobytes()
        self.dev.write(EP_LCD_OUT, LCD_HEADER + data, timeout=1000)

    def set_backlight(self, r, g, b):
        self.dev.ctrl_transfer(0x21, 0x09, 0x0307, 1, bytes([7, r, g, b]))

    def set_m_leds(self, mask):
        self.dev.ctrl_transfer(0x21, 0x09, 0x0305, 1, bytes([5, mask]))

    def set_brightness(self, value):
        """Displayhelligkeit 0–100."""
        value = max(0, min(100, value))
        self.dev.ctrl_transfer(
            0x41, 0x0A, 0x0000, 0x0000,
            bytes([value, 0xE2, 0x12, 0x00, 0x8C, 0x11, 0x00, 0x10, 0x00]),
        )

    def close(self):
        for intf in (0, 1):
            try:
                self.usb_util.release_interface(self.dev, intf)
            except Exception:                    # usb.core.USBError o. Ä.: Gerät evtl. schon weg
                pass
        self.usb_util.dispose_resources(self.dev)


class Keyboard:
    """Die G19s mit Wiederverbindung: Wird die Tastatur abgezogen (oder verschwindet sie beim
    Ruhezustand), läuft der Treiber weiter – Radio, Timer und Einstellungen bleiben erhalten.
    Lesen wartet dann nur, Schreiben wird übersprungen, und die Hauptschleife ruft reconnect()
    auf, bis die Tastatur wieder da ist. Fehlt sie schon beim Start, wird ebenso gewartet."""

    RETRY = 2.0                             # Sekunden zwischen zwei Verbindungsversuchen
    GONE_ERRNOS = {5, 19, 32}               # EIO, ENODEV, EPIPE: Gerät weg

    def __init__(self, factory, log=print):
        self.factory, self.log = factory, log
        self.lock = threading.Lock()
        self.dev, self.next_try = None, 0.0
        try:
            self.dev = factory()
        except DeviceAccess as ex:          # Einrichtungsfehler: mit Hinweis beenden
            sys.exit(str(ex))
        except DeviceMissing as ex:
            self.log(f"{ex} Warte, bis sie eingesteckt wird …")

    @property
    def connected(self):
        return self.dev is not None

    def _call(self, name, *args):
        dev = self.dev
        if dev is None:
            return None
        try:
            return getattr(dev, name)(*args)
        except Exception as ex:
            if getattr(ex, "errno", None) not in self.GONE_ERRNOS:
                raise
            self._lost(dev, ex)
            return None

    def _lost(self, dev, ex):
        with self.lock:
            if self.dev is not dev:         # der andere Lese-Thread war schneller
                return
            self.dev = None
            self.next_try = time.monotonic() + self.RETRY
        try:
            dev.close()
        except Exception:                   # Gerät ist ja schon weg
            pass
        self.log(f"Tastatur getrennt ({ex}) – warte auf Wiederverbindung")

    def reconnect(self, now):
        """Aus der Hauptschleife: neuer Verbindungsversuch, höchstens alle RETRY Sekunden.
        True = Tastatur ist gerade wieder verbunden (Beleuchtung, Bild usw. neu setzen)."""
        if self.dev is not None or now < self.next_try:
            return False
        self.next_try = now + self.RETRY
        try:
            dev = self.factory()
        except Exception:                   # noch nicht da oder Rechte noch nicht gesetzt (udev)
            return False
        with self.lock:
            self.dev = dev
        self.log("Tastatur verbunden")
        return True

    def read(self, endpoint, size, timeout_ms):
        if self.dev is None:
            time.sleep(timeout_ms / 1000)
            return None
        return self._call("read", endpoint, size, timeout_ms)

    def send_frame(self, img):
        self._call("send_frame", img)

    def set_backlight(self, r, g, b):
        self._call("set_backlight", r, g, b)

    def set_m_leds(self, mask):
        self._call("set_m_leds", mask)

    def set_brightness(self, value):
        self._call("set_brightness", value)

    def close(self):
        dev, self.dev = self.dev, None
        if dev is not None:
            dev.close()
