"""Grundlagen der Zifferblätter der Seite „Uhr“.

Ein Zifferblatt ist eine Methode, die mit @clock_face("id") angemeldet wird und
ein fertiges Displaybild (320×240, Fußzeile zeichnet render()) liefert:

    class MeineUhren:
        @clock_face("beispiel", fps=1)
        def face_beispiel(self, profile):
            t = self._clock_now()                 # Zeitstempel (nie time.time() direkt!)
            now = time.localtime(t)
            opt = self._copt("beispiel")          # Optionen aus settings.json → "clock"
            c = self._clock_canvas(("beispiel", …), bg, build_static)   # 3-fach vergrößerte Fläche
            … zeichnen mit c.circle / c.hand / c.text …
            return self._clock_finish(c)

Name und Reihenfolge stehen in CLOCK_FACES (konstanten), Optionen in CLOCK_OPTIONS.

Gemeinsame Hilfen (bitte benutzen statt eigener Varianten):
  clock_font(style, size, bold)      Schriften (sans, serif, mono, sans-cond, serif-cond), zwischengespeichert
  self._clock_canvas(key, bg, build) 3-fach vergrößerte Fläche mit zwischengespeichertem Hintergrund
  self._clock_cache(slot, key, build) sonstiges Unveränderliches (je slot nur der jüngste key)
  CLOCK_CX, CLOCK_CY, CLOCK_H         Mitte und Höhe der Uhrfläche; ROMAN_XII römische Ziffern (mit „IIII“)
Top-Level-Namen eines Moduls tragen dessen Präfix (_mech_, _sky_, _disp_, _info_), weil alle Module
einen Namensraum teilen. Zwischenspeicher werden beim Wechsel des Zifferblatts geleert (CLOCK_CACHES); eigene Speicher nicht anlegen.
fps > 1 lässt das Display öfter neu zeichnen (flüssige Bewegungen); fps darf auch
eine Funktion(optionen) sein. Analoge Uhren werden CLOCK_SS-fach gezeichnet und
verkleinert (weiche Kanten); Unveränderliches wird mit _clock_canvas zwischengespeichert.
"""
import math

CLOCK_SS = 3                                # Vergrößerung beim Zeichnen (Kantenglättung)
CLOCK_H = HEIGHT - FOOTER_H                 # Fläche über der Fußzeile
CLOCK_CX, CLOCK_CY = WIDTH / 2, CLOCK_H / 2   # Mitte der Uhrfläche (160, 107)
ROMAN_XII = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]   # Uhren-„IIII“
WEEKDAY_2 = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]
MONTH_3 = ["JAN", "FEB", "MÄR", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEZ"]


def load_serif(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif{}.ttf".format("-Bold" if bold else ""),
        "/usr/share/fonts/truetype/liberation/LiberationSerif-{}.ttf".format("Bold" if bold else "Regular"),
        "/usr/share/fonts/truetype/noto/NotoSerif-{}.ttf".format("Bold" if bold else "Regular"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return load_font(size, bold)


_CLOCK_FONT_FILES = {"sans": "DejaVuSans", "serif": "DejaVuSerif", "mono": "DejaVuSansMono",
                     "sans-cond": "DejaVuSansCondensed", "serif-cond": "DejaVuSerifCondensed"}
_CLOCK_FONTS = {}


def clock_font(style, size, bold=False):
    """Schrift für Zifferblätter (einmal geladen, dann aus dem Zwischenspeicher).
    style: sans, serif, mono, sans-cond, serif-cond (DejaVu); size in Pixeln – auf der 3-fach
    vergrößerten Fläche also z. B. 10 * CLOCK_SS. Fehlt die Datei: load_font bzw. load_serif."""
    key = (style, int(size), bool(bold))
    font = _CLOCK_FONTS.get(key)
    if font is None:
        path = f"/usr/share/fonts/truetype/dejavu/{_CLOCK_FONT_FILES[style]}{'-Bold' if bold else ''}.ttf"
        if os.path.exists(path):
            font = ImageFont.truetype(path, int(size))
        else:
            font = (load_serif if style.startswith("serif") else load_font)(int(size), bold)
        _CLOCK_FONTS[key] = font
    return font


class _Canvas:
    """Zeichenfläche in Displaykoordinaten, intern CLOCK_SS-fach vergrößert."""

    def __init__(self, img):
        self.img, self.d, self.s = img, ImageDraw.Draw(img), CLOCK_SS

    def pt(self, cx, cy, r, deg):
        """Punkt im Abstand r vom Mittelpunkt; deg = 0 bei 12 Uhr, im Uhrzeigersinn."""
        a = math.radians(deg)
        return ((cx + r * math.sin(a)) * self.s, (cy - r * math.cos(a)) * self.s)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        s = self.s
        self.d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=fill, outline=outline,
                       width=max(1, round(width * s)) if outline else 0)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        s = self.s
        self.d.rectangle([x0 * s, y0 * s, x1 * s, y1 * s], fill=fill, outline=outline,
                         width=max(1, round(width * s)) if outline else 0)

    def radial(self, cx, cy, r0, r1, deg, width, fill):
        """Strich von Radius r0 bis r1 in Richtung deg (als Viereck, damit er gerade Enden hat)."""
        self.hand(cx, cy, deg, [(r0, width), (r1, width)], fill)

    def hand(self, cx, cy, deg, profile, fill, outline=None):
        """Zeiger aus einem Profil [(abstand, breite), …] entlang der Richtung deg."""
        a = math.radians(deg)
        dx, dy, px, py = math.sin(a), -math.cos(a), math.cos(a), math.sin(a)
        left = [((cx + r * dx + w / 2 * px) * self.s, (cy + r * dy + w / 2 * py) * self.s) for r, w in profile]
        right = [((cx + r * dx - w / 2 * px) * self.s, (cy + r * dy - w / 2 * py) * self.s) for r, w in reversed(profile)]
        self.d.polygon(left + right, fill=fill, outline=outline)

    def text(self, cx, cy, txt, font, fill):
        """Text mittig um (cx, cy)."""
        self.d.text((cx * self.s, cy * self.s), txt, font=font, fill=fill, anchor="mm")

    def gear(self, cx, cy, r, teeth, deg, fill, dark):
        """Zahnrad mit Speichen; deg = Drehung."""
        pts, pitch, depth = [], 360 / teeth, min(5, max(1.5, r * 0.18))
        for i in range(teeth):
            b = deg + i * pitch
            for rr, off in ((r - depth, 0), (r, 0.18), (r, 0.47), (r - depth, 0.65)):
                pts.append(self.pt(cx, cy, rr, b + off * pitch))
        self.d.polygon(pts, fill=fill, outline=dark)
        if r >= 14:                                 # große Räder: ausgespart mit Speichen
            self.circle(cx, cy, r - 2 * depth, fill=dark)
            for k in range(5):
                self.radial(cx, cy, 0, r - 2 * depth + 1, deg + k * 72, max(3, r / 7), fill)
        self.circle(cx, cy, max(4, r / 4), fill=fill, outline=dark, width=1)
        self.circle(cx, cy, max(1.5, r / 12), fill=dark)



# Registry: Zifferblatt-ID → Zeichenfunktion(self, profile); Bilder je Sekunde
CLOCK_RENDERERS = {}
CLOCK_FPS = {}


def clock_face(face_id, fps=1):
    """Methode als Zeichenfunktion des Zifferblatts face_id anmelden."""
    def deco(fn):
        CLOCK_RENDERERS[face_id] = fn
        CLOCK_FPS[face_id] = fps
        return fn
    return deco


def clock_options(settings, face):
    """Optionen eines Zifferblatts: Standardwerte aus CLOCK_OPTIONS, ergänzt um settings.json."""
    out = {o["key"]: o["default"] for o in CLOCK_OPTIONS.get(face, [])}
    user = ((settings or {}).get("clock") or {}).get(face)
    if isinstance(user, dict):
        out.update({k: v for k, v in user.items() if k in out})
    return out


def clock_fps(face, settings):
    """Wie oft das Zifferblatt je Sekunde neu gezeichnet werden soll."""
    fps = CLOCK_FPS.get(face, 1)
    return fps(clock_options(settings, face)) if callable(fps) else fps


def mix(a, b, t):
    """Farbe zwischen a (t=0) und b (t=1)."""
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class ClockBase:
    """Hilfen für alle Zifferblätter (Schriften, Zwischenspeicher, Zeit, Optionen, Farben)."""

    def _clock_fonts(self):
        if not hasattr(self, "_cfonts"):
            s = CLOCK_SS
            self._cfonts = {"tiny": load_font(8 * s), "small": load_font(10 * s, bold=True),
                            "mid": load_font(13 * s, bold=True), "big": load_font(24 * s, bold=True),
                            "side": load_font(15 * s, bold=True), "roman": load_serif(13 * s, bold=True),
                            "serif_s": load_serif(9 * s, bold=True), "led": load_font(20 * s, bold=True)}
            self._cdials = {}
        return self._cfonts

    def _clock_canvas(self, key, bg, build):
        """Zwischengespeichertes Zifferblatt kopieren (build zeichnet es beim ersten Mal)."""
        self._clock_fonts()
        if key not in self._cdials and len(self._cdials) >= 8:
            self._cdials.clear()                  # z. B. nach vielen Farbwechseln: Speicher begrenzen
        if key not in self._cdials:
            c = _Canvas(Image.new("RGB", (WIDTH * CLOCK_SS, CLOCK_H * CLOCK_SS), bg))
            build(c)
            self._cdials[key] = c.img
        return _Canvas(self._cdials[key].copy())

    # Zwischenspeicher der Zifferblatt-Module (je ~2–3 MB pro Eintrag); Schriften bleiben erhalten
    CLOCK_CACHES = ("_cdials", "_clock_slots")

    def _clock_cache(self, slot, key, build):
        """Zwischenspeicher für Unveränderliches (Hintergründe, Masken, vorberechnete Bilder):
        je slot nur der jüngste key – ändert sich z. B. eine Farbe, wird neu gebaut statt angesammelt."""
        slots = self.__dict__.setdefault("_clock_slots", {})
        hit = slots.get(slot)
        if hit is None or hit[0] != key:
            hit = slots[slot] = (key, build())
        return hit[1]

    def _clock_drop_caches(self):
        """Beim Wechsel des Zifferblatts die Zwischenspeicher der anderen Zifferblätter freigeben."""
        for name in self.CLOCK_CACHES:
            cache = self.__dict__.get(name)
            if isinstance(cache, dict):
                cache.clear()

    def _clock_finish(self, c):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        img.paste(c.img.reduce(CLOCK_SS), (0, 0))     # Mittelwert je 3×3 – 15× schneller als LANCZOS
        return img

    @staticmethod
    def _clock_angles(now):
        sec = now.tm_sec
        minute = now.tm_min + sec / 60
        hour = (now.tm_hour % 12) + minute / 60
        return hour * 30, minute * 6, sec * 6

    def _clock_now(self):
        """Aktuelle Zeit als Zeitstempel. Tests setzen fixed_time für feste Bilder."""
        fixed = getattr(self, "fixed_time", None)
        return fixed if fixed is not None else time.time()

    def _copt(self, face):
        return clock_options(self.settings, face)

    def _ccolor(self, value, profile, default=None):
        """Farbe aus einer Option: gesetzt → diese, sonst default bzw. die Farbe der Ebene."""
        if value:
            return tuple(value)
        return tuple(default) if default else PROFILE_COLOR.get(profile, self.FG)


@page_keys("clock")
def keys_clock(app, pressed):
    """MENU öffnet die Auswahl des Zifferblatts; sonst blättern die Pfeiltasten."""
    if pressed & LKEY_BITS["MENU"]:
        app.menu = ClockMenu(app)
        app.flash = None
        app.next_draw = 0
        return True
    return False
