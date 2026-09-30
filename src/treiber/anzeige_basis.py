"""Grundlagen der Displayanzeige: Schriften, Farben, Hilfsfunktionen zum Zeichnen,
Fußzeile und die Registry der Displayseiten."""


# --------------------------------------------------------------------------- #
# Displayseiten
# --------------------------------------------------------------------------- #
def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format("-Bold" if bold else ""),
        "/usr/share/fonts/truetype/noto/NotoSans-{}.ttf".format("Bold" if bold else "Regular"),
        "/usr/share/fonts/opentype/noto/NotoSans-{}.otf".format("Bold" if bold else "Regular"),
        "/usr/share/fonts/truetype/liberation/LiberationSans-{}.ttf".format("Bold" if bold else "Regular"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# Registry: Seiten-ID → Zeichenfunktion (wird von @page gefüllt)
PAGE_RENDERERS = {}


def page(page_id):
    """Methode als Zeichenfunktion der Displayseite page_id anmelden."""
    def deco(fn):
        PAGE_RENDERERS[page_id] = fn
        return fn
    return deco


# Registry: Seiten-ID → Tastenfunktion(app, pressed) → True = Tasten verarbeitet
# (sonst blättern Rechts/Runter und Links/Hoch die Seiten)
PAGE_KEYS = {}


def page_keys(*page_ids):
    """Funktion als Tastenbehandlung der Displayseite(n) anmelden."""
    def deco(fn):
        for pid in page_ids:
            PAGE_KEYS[pid] = fn
        return fn
    return deco


class RendererBase:
    BG = (8, 10, 16)

    FG = (235, 238, 245)

    DIM = (130, 138, 155)

    def __init__(self):
        self.f_huge = load_font(78, bold=True)
        self.f_large = load_font(58, bold=True)
        self.f_big = load_font(26, bold=True)
        self.f_mid = load_font(20)
        self.f_small = load_font(15)
        self.f_small_b = load_font(15, bold=True)
        self.f_title = load_font(19, bold=True)
        self.f_title_s = load_font(15, bold=True)
        self.f_tiny = load_font(12)
        self.stats = Stats()
        self.media = None
        self.slideshow = None
        self.settings = DEFAULT_SETTINGS
        self.profile_name = ""
        self.weather = None
        self.calendar = None
        self.cal_hidden = set()          # am Display ausgeblendete Kalender (Schlüssel)
        self.hw = Hardware()
        self.visible = None          # Indizes der eingeschalteten Seiten (Reihenfolge)
        self.clock_face = "digital"   # Zifferblatt der Seite „Uhr“ (setzt die App je Profil/Ebene)
        self.timer_badge = ""        # laufender Timer in der Fußzeile, z. B. "+04:12"
        self.mic_muted = False       # Mikrofon stumm → rotes Symbol in der Fußzeile
        self.sleep_badge = ""        # Einschlaftimer, z. B. "29"
        self.cal_sel = None          # markierter Termin auf der Terminseite (Index) oder None
        self.cal_items = []          # zuletzt gezeigte (gefilterte) Termine
        self.news = self.alerts = self.net = self.updates = None      # Poller der neuen Seiten
        self.sel = {"news": None, "warnings": None}                     # markierte Zeile je Seite
        self.list_items = {"news": [], "warnings": []}

    def _center(self, draw, y, text, font, fill):
        w = draw.textlength(text, font=font)
        draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)

    def _fit(self, draw, text, font, max_w):
        if draw.textlength(text, font=font) <= max_w:
            return text
        while text and draw.textlength(text + "…", font=font) > max_w:
            text = text[:-1]
        return text + "…"

    def _footer(self, draw, profile, page, pages):
        color = PROFILE_COLOR.get(profile, self.FG)
        draw.rectangle([0, HEIGHT - FOOTER_H, WIDTH, HEIGHT], fill=(20, 24, 34))
        draw.rectangle([10, HEIGHT - 19, 22, HEIGHT - 7], fill=color)
        label = f"{self.profile_name} · {profile}" if self.profile_name else f"Profil {profile}"
        step = 14 if pages <= 12 else 10               # viele Seiten: Punkte enger
        dots_x = WIDTH - 14 - (pages - 1) * step - 10
        room = dots_x - 36
        if self.timer_badge:
            state, text = self.timer_badge[0], self.timer_badge[1:]
            col = {"+": (240, 170, 60), "~": (62, 207, 126), "=": (150, 156, 170), "!": (255, 80, 80)}[state]
            bw = draw.textlength(text, font=self.f_small_b)
            x = dots_x - bw - 6
            draw.text((x, HEIGHT - 22), text, font=self.f_small_b, fill=col)
            self._icon_clock(draw, x - 16, HEIGHT - 20, 12, col, paused=(state == "="))
            room -= bw + 26
            dots_x = x - 20
        if self.sleep_badge:
            bw = draw.textlength(self.sleep_badge, font=self.f_small_b)
            x = dots_x - bw - 6
            draw.text((x, HEIGHT - 22), self.sleep_badge, font=self.f_small_b, fill=(150, 170, 255))
            self._icon_moon(draw, x - 18, HEIGHT - 20, (150, 170, 255), (20, 24, 34))
            room -= bw + 26
            dots_x = x - 20
        if self.mic_muted:
            self._icon_mic(draw, dots_x - 18, HEIGHT - 21, (255, 70, 70))
            room -= 22
        draw.text((30, HEIGHT - 22), self._fit(draw, label, self.f_small, max(30, room)),
                  font=self.f_small, fill=self.FG)
        for i in range(pages):
            x = WIDTH - 14 - (pages - 1 - i) * step
            fill = self.FG if i == page else self.DIM
            rr = 4 if step == 14 else 3
            draw.ellipse([x - rr, HEIGHT - 13 - rr, x + rr, HEIGHT - 13 + rr], fill=fill)

    def _wrap(self, d, text, font, max_w, max_lines):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = f"{cur} {w}".strip()
            if d.textlength(test, font=font) <= max_w:
                cur = test
                continue
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        consumed = " ".join(lines)
        if len(consumed) < len(" ".join(words)) and lines:
            lines[-1] = self._fit(d, lines[-1] + " …", font, max_w)
        return [self._fit(d, line, font, max_w) for line in lines]

    # ---- Wetter --------------------------------------------------------- #
    def _hint_page(self, symbol, title, text, title_color=None):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        if symbol:
            self._center(d, 30, symbol, self.f_huge, (60, 66, 84))
        self._center(d, 128, title, self.f_big, title_color or self.FG)
        for i, line in enumerate(self._wrap(d, text, self.f_small, WIDTH - 24, 2)):
            self._center(d, 166 + i * 19, line, self.f_small, self.DIM)
        return img

    # ---- Nachrichten ---------------------------------------------------- #
    def _poll_state(self, poller, symbol, title, need=None):
        """(Daten, Fehler) oder fertiges Hinweisbild."""
        if need:
            return None, self._hint_page(symbol, title, need)
        data, err, _ = poller.snapshot() if poller else (None, None, 0)
        if data is None:
            return None, self._hint_page(symbol, f"{title}-Fehler" if err else title, err or "Lade …",
                                         (235, 90, 90) if err else None)
        return data, None

    def _header(self, d, title, right="", warn=False):
        d.text((12, 4), title, font=self.f_title, fill=self.FG)
        if right:
            d.text((WIDTH - 12 - d.textlength(right, font=self.f_small), 8), right, font=self.f_small, fill=self.DIM)
        if warn:
            d.text((12 + d.textlength(title, font=self.f_title) + 8, 8), "⚠", font=self.f_small, fill=(240, 170, 60))

    def _scroll_marks(self, d, more_above, more_below):
        """Kleine Pfeile links/rechts in der Fußzeile: es gibt weitere Einträge."""
        if more_above:
            d.text((8, HEIGHT - 20), "▲", font=self.f_tiny, fill=(240, 170, 60))
        if more_below:
            d.text((WIDTH - 8 - d.textlength("▼", font=self.f_tiny), HEIGHT - 20), "▼",
                   font=self.f_tiny, fill=(240, 170, 60))

    def _heart(self, d, x, y, size, color, outline=(255, 255, 255)):
        r = size / 4
        pts = [(x + size / 2, y + size)]
        d.ellipse([x - 1, y - 1, x + size / 2 + 1, y + size / 2 + 1], fill=outline)
        d.ellipse([x + size / 2 - 1, y - 1, x + size + 1, y + size / 2 + 1], fill=outline)
        d.polygon([(x - 1, y + r), (x + size + 1, y + r), (x + size / 2, y + size + 2)], fill=outline)
        d.ellipse([x, y, x + size / 2, y + size / 2], fill=color)
        d.ellipse([x + size / 2, y, x + size, y + size / 2], fill=color)
        d.polygon([(x, y + r), (x + size, y + r), pts[0]], fill=color)

    def _icon_mic(self, d, x, y, color, muted=True):
        d.rounded_rectangle([x + 4, y, x + 10, y + 9], radius=3, fill=color)
        d.arc([x + 1, y + 3, x + 13, y + 13], 0, 180, fill=color, width=2)
        d.line([(x + 7, y + 13), (x + 7, y + 15)], fill=color, width=2)
        if muted:
            d.line([(x, y + 15), (x + 14, y)], fill=(255, 255, 255), width=2)

    def _icon_moon(self, d, x, y, color, bg):
        d.ellipse([x, y, x + 13, y + 13], fill=color)
        d.ellipse([x + 4, y - 2, x + 16, y + 10], fill=bg)

    def _icon_clock(self, d, x, y, size, color, paused=False):
        d.ellipse([x, y, x + size, y + size], outline=color, width=2)
        cx, cy = x + size / 2, y + size / 2
        if paused:
            d.line([(cx - 2, cy - 2), (cx - 2, cy + 2)], fill=color, width=2)
            d.line([(cx + 2, cy - 2), (cx + 2, cy + 2)], fill=color, width=2)
        else:
            d.line([(cx, cy), (cx, y + 3)], fill=color, width=2)
            d.line([(cx, cy), (x + size - 3, cy)], fill=color, width=2)

    def _icon_bell(self, d, cx, top, color):
        d.pieslice([cx - 26, top, cx + 26, top + 52], 180, 360, fill=color)
        d.rectangle([cx - 26, top + 26, cx + 26, top + 44], fill=color)
        d.polygon([(cx - 34, top + 50), (cx + 34, top + 50), (cx + 26, top + 42), (cx - 26, top + 42)], fill=color)
        d.ellipse([cx - 7, top + 50, cx + 7, top + 62], fill=color)
        d.ellipse([cx - 4, top - 7, cx + 4, top + 1], fill=color)


def move_selection(sel, pressed, n):
    """Markierung einer Liste mit Hoch/Runter bewegen (erste Taste markiert den ersten Eintrag)."""
    if pressed & LKEY_BITS["DOWN"]:
        sel = 0 if sel is None else min(n - 1, sel + 1)
    if pressed & LKEY_BITS["UP"]:
        sel = 0 if sel is None else max(0, sel - 1)
    return sel


def refresh_page(app, page_id):
    """MENU auf einer Infoseite: Daten sofort neu abfragen."""
    app.refreshers[page_id].refresh()
    app.show("Aktualisieren", ["wird neu abgefragt …"], PROFILE_COLOR[app.layer], 1.2)
