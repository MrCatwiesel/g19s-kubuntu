"""Zugriff auf die G19s über USB: Displaybild senden, Tasten lesen, Beleuchtung, Helligkeit."""


# 512-Byte-Header, der jedem Displaybild vorangestellt wird
LCD_HEADER = bytes(
    [0x10, 0x0F, 0x00, 0x58, 0x02, 0x00, 0x00, 0x00,
     0x00, 0x00, 0x00, 0x3F, 0x01, 0xEF, 0x00, 0x0F]
    + list(range(16, 256))
    + list(range(256))
)
assert len(LCD_HEADER) == 512


# --------------------------------------------------------------------------- #
# USB-Zugriff
# --------------------------------------------------------------------------- #
class G19:
    def __init__(self):
        import usb.core
        import usb.util
        self.usb_core, self.usb_util = usb.core, usb.util

        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if dev is None:
            sys.exit("G19s (046d:c229) nicht gefunden – ist die Tastatur eingesteckt?")
        self.dev = dev

        for intf in (0, 1):
            try:
                if dev.is_kernel_driver_active(intf):
                    dev.detach_kernel_driver(intf)
            except usb.core.USBError as ex:
                sys.exit(
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
