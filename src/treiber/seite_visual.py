"""Displayseite „Visualisierung“: acht Stile, die auf die laufende Musik reagieren.

Die Werte kommen von SoundAnalyzer (klanganalyse) über self.visual.snapshot(); ohne Analyse
(Vorschau der Verwaltung, Referenzbilder) zeichnen die Stile mit demo_snapshot(). Ohne Ton (Stille,
Ausgang stumm) steht das letzte Bild abgedunkelt still, mit Hinweis „Keine Wiedergabe“ bzw. „Ton stumm“. Ein Stil wird mit @vis_style("id")
angemeldet (@vis_style) und bekommt (snapshot, optionen, farbe der ebene); er liefert ein Bild WIDTH×HEIGHT,
die Fußzeile zeichnet render(). Zustand zwischen zwei Bildern (Spitzen, Teilchen …) liegt in
self._vstate(stil) und wird beim Stilwechsel verworfen.
"""
import colorsys
import math
import random

VISUAL_RENDERERS = {}
VIS_H = HEIGHT - FOOTER_H          # nutzbare Höhe über der Fußzeile


def vis_style(style_id):
    """Methode als Zeichenfunktion des Stils style_id anmelden."""
    def deco(fn):
        VISUAL_RENDERERS[style_id] = fn
        return fn
    return deco


def visual_options(settings, style):
    """Optionen eines Stils: Standardwerte aus VISUAL_OPTIONS, ergänzt um settings.json → "visual"."""
    out = {o["key"]: o["default"] for o in VISUAL_OPTIONS.get(style, [])}
    user = ((settings or {}).get("visual") or {}).get(style)
    if isinstance(user, dict):
        out.update({k: v for k, v in user.items() if k in out})
    return out


def _hue(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return int(r * 255), int(g * 255), int(b * 255)


def _vec(angle_deg, length):
    """Richtung: 0° = nach unten, 90° = nach rechts, 180° = nach oben."""
    a = math.radians(angle_deg)
    return math.sin(a) * length, math.cos(a) * length


def _smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


# Langeweile bei Wortbeiträgen (Stil „Tänzerin“, Haltungen in seite_visual_ballett.BAL_BORED): an die Stange
# lehnen, gähnen, dehnen, auf die Uhr schauen, nach BORED_SIT_AFTER Sekunden hinsetzen
BORED_CYCLE = [(5, "cross"), (2, "yawn"), (3, "hips"), (2.5, "watch")]     # Sekunden je Haltung, im Kreis
BORED_SIT_AFTER = 30.0                 # so lange Wortbeitrag, dann setzt sie sich auf den Bühnenrand


def _bored_pose(b):
    """Haltung nach b Sekunden Wortbeitrag."""
    if b >= BORED_SIT_AFTER:
        return "sit"
    total = sum(d for d, _ in BORED_CYCLE)
    x = b % total
    for d, name in BORED_CYCLE:
        if x < d:
            return name
        x -= d
    return "cross"


def talk_word(settings, info):
    """Steht eines der Stichwörter (settings.json → visual.talk_words, durch Komma getrennt) in Titel oder
    Künstler des laufenden Titels? Dann ist es ein Wortbeitrag (z. B. Nachrichten, Werbung). Liefert das Wort."""
    if not info:
        return None
    text = f"{info.get('artist') or ''} {info.get('title') or ''}"
    words = str(((settings or {}).get("visual") or {}).get("talk_words") or "").split(",")
    for w in (x.strip() for x in words):
        if w and re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text, re.IGNORECASE):
            return w
    return None


class VisualPage:
    visual = None                      # SoundAnalyzer (setzt die App) oder None = künstliche Werte
    visual_style = "eq"
    vis_talk = False                   # gerade Wortbeitrag (Klang oder Stichwort) – Tastatur pulsiert dann nicht
    vis_strobe_t = -99.0               # Zeit des letzten Stroboskop-Blitzes der Lichtshow (Tastaturbeleuchtung)

    # -- Grundlagen ---------------------------------------------------------- #
    def _vstate(self, style, make):
        st = self.__dict__.setdefault("_vis_states", {})
        if st.get("_style") != style:
            st.clear()
            st["_style"] = style
        if style not in st:
            st[style] = make()
        return st[style]

    def _vis_snapshot(self):
        snap = self.visual.snapshot() if self.visual is not None else None
        now = time.time()
        if snap is None:
            return demo_snapshot(now)                       # Vorschau: als liefe Musik
        if snap.get("active"):
            return snap
        idle = demo_snapshot(0.0, amp=0.22)                 # Stille: nur für ein erstes Standbild
        idle.update(idle=True, error=snap.get("error"), muted=snap.get("muted", False))
        return idle

    def _vis_dt(self, st, t):
        dt = max(0.0, min(0.2, t - st.get("t", t)))
        st["t"] = t
        return dt

    @page("visual")
    def page_visual(self, profile, macros):
        now = time.monotonic()
        if now - self.__dict__.get("_vis_page_t", -99.0) > 1.5:
            self._vis_enter = True                          # Seite neu geöffnet (Weihnachten: Auftritt)
        self._vis_page_t = now
        snap = self._vis_snapshot()
        style = self.visual_style if self.visual_style in VISUAL_RENDERERS else "eq"
        color = PROFILE_COLOR.get(profile, self.FG)
        if snap.get("idle"):
            self.vis_talk = False
            return self._vis_still(snap, style, profile, color)
        vis = (self.settings or {}).get("visual") or {}
        info = self.media.snapshot()[0] if self.media is not None else None
        word = talk_word(self.settings, info)
        if word:                                            # Sender meldet Nachrichten/Werbung
            if self.__dict__.get("_title_talk_t") is None:
                self._title_talk_t = snap["t"]
            if not snap.get("talk"):
                snap = dict(snap, talk=True, talk_t=self._title_talk_t)
        else:
            self._title_talk_t = None
        self.vis_talk = bool(snap.get("talk"))
        self._vis_song = " – ".join(x for x in (info.get("artist"), info.get("title")) if x) if info else ""
        img = VISUAL_RENDERERS[style](self, snap, visual_options(self.settings, style), color)
        self._vis_last = (style, profile, img.copy())      # für das Standbild, wenn der Ton aufhört
        d = ImageDraw.Draw(img)
        if info and info.get("title") and vis.get("title", True):
            text = " – ".join(x for x in (info.get("artist"), info.get("title")) if x)
            text = self._fit(d, text, self.f_tiny, WIDTH - 16)
            d.text((9, 4), text, font=self.f_tiny, fill=(0, 0, 0))
            d.text((8, 3), text, font=self.f_tiny, fill=(225, 230, 240))
        return img

    def _vis_still(self, snap, style, profile, color):
        """Ohne Ton: letztes Bild dieses Stils abgedunkelt mit Hinweis (zwischengespeichert, keine Bewegung)."""
        text = snap["error"] if snap.get("error") else "Ton stumm" if snap.get("muted") else "Keine Wiedergabe"
        last = self.__dict__.get("_vis_last")
        key = (style, profile, text, id(last))
        cached = self.__dict__.get("_vis_still_img")
        if cached is None or cached[0] != key:
            if style == "xmas" and snap.get("muted") and party_active(visual_options(self.settings, style)):
                base = VISUAL_RENDERERS[style](self, snap, visual_options(self.settings, style), color)  # schlafen
            elif last and last[0] == style and last[1] == profile:
                base = last[2]
            else:                                           # noch kein Bild mit Ton: ruhiges Standbild
                base = VISUAL_RENDERERS[style](self, snap, visual_options(self.settings, style), color)
            img = Image.blend(base, Image.new("RGB", base.size, (0, 0, 0)), 0.55)
            d = ImageDraw.Draw(img)
            w = d.textlength(text, font=self.f_small) + 24
            y = VIS_H // 2 - 14
            d.rounded_rectangle([(WIDTH - w) / 2, y, (WIDTH + w) / 2, y + 28], radius=8, fill=(20, 24, 34))
            self._center(d, y + 5, self._fit(d, text, self.f_small, WIDTH - 40), self.f_small,
                         (235, 120, 90) if snap.get("error") else self.FG)
            self._vis_still_img = cached = (key, img)
        return cached[1].copy()

    # -- 1. Grafik-Equalizer ------------------------------------------------- #
    def _eq_layers(self, n, colors, mirror, color):
        """Bild aller leuchtenden LED-Segmente und dasselbe gedimmt (zwischengespeichert)."""
        key = (n, colors, mirror, tuple(color))
        cache = self.__dict__.setdefault("_eq_cache", {})
        if key in cache:
            return cache[key]
        top, bottom = 24, VIS_H - 6
        lit = np.zeros((HEIGHT, WIDTH, 3), np.float32)
        gap = 2
        bw = (WIDTH - 12 - gap * (n - 1)) / n
        ys = np.arange(HEIGHT)
        if mirror:
            mid = (top + bottom) / 2
            frac = np.clip(np.abs(ys - mid) / ((bottom - top) / 2), 0, 1)
            seg = (np.abs(ys - mid).astype(int) % 6) < 4
        else:
            frac = np.clip((bottom - ys) / (bottom - top), 0, 1)
            seg = ((bottom - ys) % 6) < 4
        seg &= (ys >= top) & (ys < bottom)
        cols = []
        for i in range(n):
            x0 = int(round(6 + i * (bw + gap)))
            x1 = int(round(6 + i * (bw + gap) + bw))
            cols.append((x0, max(x0 + 1, x1)))
            for y in np.nonzero(seg)[0]:
                f = frac[y]
                if colors == "led":
                    c = (255, 40, 30) if f > 0.86 else (255, 200, 0) if f > 0.62 else (40, 220, 70)
                elif colors == "rainbow":
                    c = _hue(0.75 * i / max(1, n - 1), 0.85, 0.65 + 0.35 * f)
                else:
                    c = mix(tuple(int(x * 0.45) for x in color), color, f)
                lit[y, cols[-1][0]:cols[-1][1]] = c
        dim = lit * 0.11 + np.array([6, 8, 12], np.float32)
        dim[~seg] = (6, 8, 12)
        cache.clear()
        cache[key] = (lit, dim, cols, top, bottom)
        return cache[key]

    @vis_style("eq")
    def vis_eq(self, s, o, color):
        n = int(o["bars"])
        lit, dim, cols, top, bottom = self._eq_layers(n, o["colors"], bool(o["mirror"]), color)
        b = np.interp(np.linspace(0, AUDIO_BANDS - 1, n), np.arange(AUDIO_BANDS), s["bands"])
        st = self._vstate("eq", dict)
        dt = self._vis_dt(st, s["t"])
        if len(st.get("peak", [])) != n:
            st["peak"], st["hold"] = b.copy(), np.zeros(n)
        peak, hold = st["peak"], st["hold"]
        up = b >= peak
        peak[up], hold[up] = b[up], 0.35
        hold[~up] -= dt
        fall = ~up & (hold <= 0)
        peak[fall] = np.maximum(b[fall], peak[fall] - dt * 0.6)
        arr = dim.copy()
        avail = bottom - top
        for i, (x0, x1) in enumerate(cols):
            h = int(b[i] * avail)
            if h <= 0:
                continue
            if o["mirror"]:
                mid = (top + bottom) // 2
                arr[mid - h // 2:mid + h // 2 + 1, x0:x1] = lit[mid - h // 2:mid + h // 2 + 1, x0:x1]
            else:
                arr[bottom - h:bottom, x0:x1] = lit[bottom - h:bottom, x0:x1]
        img = Image.fromarray(arr.astype(np.uint8), "RGB")
        if o["peaks"]:
            d = ImageDraw.Draw(img)
            for i, (x0, x1) in enumerate(cols):
                ph = int(peak[i] * avail)
                if ph < 3:
                    continue
                if o["mirror"]:
                    mid = (top + bottom) // 2
                    for y in (mid - ph // 2 - 3, mid + ph // 2 + 2):
                        d.rectangle([x0, y, x1 - 1, y + 1], fill=(235, 238, 245))
                else:
                    y = bottom - ph - 3
                    d.rectangle([x0, y, x1 - 1, y + 1], fill=(235, 238, 245))
        return img

    # -- 2. Tänzerin: in seite_visual_ballett.py (BalletVisual) ----------------- #

    # -- 3. Lichtshow -------------------------------------------------------- #
    @vis_style("lights")
    def vis_lights(self, s, o, color):
        t, n = s["t"], int(o["beams"])
        st = self._vstate("lights", dict)
        self._vis_dt(st, t)
        fall = self.__dict__.get("_lights_fall")
        if fall is None:                                    # Kegel werden nach unten schwächer
            fall = self._lights_fall = Image.fromarray(
                np.broadcast_to(np.linspace(255, 89, VIS_H)[:, None], (VIS_H, WIDTH)).astype(np.uint8), "L")
        beams = Image.new("RGB", (WIDTH, VIS_H), (5, 4, 10))
        bright = 0.35 + 0.65 * s["bass"]
        for i in range(n):
            ox = 30 + i * (WIDTH - 60) / max(1, n - 1)
            ang = math.sin(t * (0.8 + 0.13 * i) + i * 1.7) * 38
            dx1, dy1 = _vec(ang - 8, 300)
            dx2, dy2 = _vec(ang + 8, 300)
            mask = Image.new("L", (WIDTH, VIS_H), 0)
            ImageDraw.Draw(mask).polygon([(ox - 3, 0), (ox + 3, 0), (ox + dx2, dy2), (ox + dx1, dy1)],
                                         fill=int(150 * bright))
            mask = ImageChops.multiply(mask, fall)
            c = _hue(i / n + s["beats"] * 0.13, 0.85, 1.0)
            beams = ImageChops.add(beams, ImageChops.multiply(Image.new("RGB", beams.size, c), mask.convert("RGB")))
        d = ImageDraw.Draw(beams)
        rng = random.Random(s["beats"])                     # Lichtpunkte, neu bei jedem Schlag
        for _ in range(40):
            x, y = rng.randrange(WIDTH), rng.randrange(30, VIS_H)
            tw = 0.5 + 0.5 * math.sin(t * rng.uniform(4, 9) + rng.uniform(0, 6))
            c = _hue(rng.random(), 0.5, tw * (0.4 + 0.6 * s["level"]))
            d.rectangle([x, y, x + 1, y + 1], fill=c)
        since = t - s["beat_t"]
        if o["flash"] and 0 <= since < 0.15 and s["bass"] > 0.6 and t - st.get("flash", -9) > 0.5:
            st["flash"] = s["beat_t"]
        fl = t - st.get("flash", -9)
        if 0 <= fl < 0.15:
            f = 1 - fl / 0.15                               # sanft, kein hartes Stroboskop
            beams = beams.point(lambda v: min(255, int(v * (1 + 0.7 * f) + 22 * f)))
        strobe = self._lights_strobe(st, s, o, t)
        if strobe:                                          # Stroboskop: harter Blitz, ein bis zwei Bilder lang
            k, col = strobe
            if col == "beam":
                col = _hue(s["beats"] * 0.13, 0.5, 1.0)
            elif col == "layer":
                col = tuple(color)
            else:
                col = (255, 255, 255)
            beams = Image.blend(beams, Image.new("RGB", beams.size, col), 0.9 * k)
        img = Image.new("RGB", (WIDTH, HEIGHT), (5, 4, 10))
        img.paste(beams, (0, 0))
        d = ImageDraw.Draw(img)
        cx, cy, r = WIDTH // 2, 12, 11                      # Spiegelkugel
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(70, 70, 80))
        for gx in range(-r, r, 4):
            for gy in range(-r, r, 4):
                if gx * gx + gy * gy < r * r:
                    v = 110 + int(120 * (0.5 + 0.5 * math.sin(t * 6 + gx * 0.7 + gy * 1.3)))
                    d.rectangle([cx + gx, cy + gy, cx + gx + 2, cy + gy + 2], fill=(v, v, min(255, v + 20)))
        return img

    def _lights_strobe(self, st, s, o, t):
        """Stroboskop der Lichtshow: Blitz auf hohe Schläge (Hi-Hat, Snare, Klatschen – wie ein echtes Stroboskop
        am Mischpult, nicht auf den Bass) und/oder Salven, wenn die Musik deutlich lauter und heller wird (Höhepunkt).
        Höchstens strobe_rate (≤ 3) Blitze je Sekunde – mehr gilt als riskant für Lichtempfindliche. Bei
        Wortbeiträgen blitzt nichts. Gibt (Stärke 0…1, Farbwahl) zurück oder None; vis_strobe_t merkt sich den
        Blitz (für die Tastatur)."""
        mode = o.get("strobe", "off")
        if mode not in ("beat", "drop", "both") or not s.get("active", s.get("demo")) or s.get("talk"):
            return None
        rate = min(3, max(1, int(o["strobe_rate"]) if str(o.get("strobe_rate")).isdigit() else 2))
        gap = 1.0 / rate
        avg = st.get("avg")                                 # gleitendes Mittel des Pegels (≈ 4 s)
        st["avg"] = s["level"] if avg is None else avg + (s["level"] - avg) * min(1.0, (t - st.get("avg_t", t)) / 4)
        st["avg_t"] = t
        if mode in ("drop", "both") and avg is not None and s["level"] > avg * 1.3 + 0.05 \
                and s.get("treble", 0) > 0.3 and t - st.get("burst_end", -99) > 6:
            st["burst_end"] = t + 2.0                         # Salve: 2 s lang so schnell wie erlaubt
        burst = t < st.get("burst_end", -99)
        last = st.get("strobe", -99)
        hit = 0 <= t - s.get("hat_t", -99) < 0.12          # gerade ein hoher Schlag
        beat = mode in ("beat", "both") and hit and s.get("hat", 0) >= 0.4
        if burst and not hit and t - max(last, s.get("hat_t", -99)) < gap * 1.5:
            burst = False                                   # Salve folgt den hohen Schlägen, sonst im Takt der Rate
        if t - last >= gap and (beat or burst):
            st["strobe"] = last = t
            self.vis_strobe_t = t
        age = t - last
        frame = 1.0 / max(1, int((self.settings or {}).get("visual", {}).get("fps") or VISUAL_FPS))
        if 0 <= age < frame * 0.99:
            return 1.0, o.get("strobe_color", "white")
        if age < frame * 1.99:
            return 0.25, o.get("strobe_color", "white")      # kurzes Nachglühen im nächsten Bild
        return None

    # -- 4. Oszilloskop ------------------------------------------------------ #
    def _scope_bg(self):
        if "_scope_bg_img" not in self.__dict__:
            img = Image.new("RGB", (WIDTH, VIS_H), (4, 12, 8))
            d = ImageDraw.Draw(img)
            for x in range(0, WIDTH, 32):
                d.line([(x, 0), (x, VIS_H)], fill=(12, 34, 22))
            for y in range(VIS_H // 2 % 30, VIS_H, 30):
                d.line([(0, y), (WIDTH, y)], fill=(12, 34, 22))
            d.line([(0, VIS_H // 2), (WIDTH, VIS_H // 2)], fill=(20, 52, 34))
            self._scope_bg_img = np.asarray(img, np.float32)
        return self._scope_bg_img

    @vis_style("scope")
    def vis_scope(self, s, o, color):
        c = tuple(o["color"]) if o.get("color") else (60, 255, 120)
        bg = self._scope_bg()
        st = self._vstate("scope", dict)
        prev = st.get("glow")
        layer = Image.new("RGB", (WIDTH, VIS_H), (0, 0, 0))
        d = ImageDraw.Draw(layer)
        if o["mode"] == "xy":
            cx, cy, k = WIDTH / 2, VIS_H / 2, 70
            pts = [(cx + float(l) * k, cy - float(r) * k) for l, r in zip(s["wave_l"], s["wave_r"])]
        else:
            w = s["wave"][::2]
            xs = np.linspace(4, WIDTH - 4, len(w))
            ys = np.clip(VIS_H / 2 - w * (VIS_H * 0.42), 2, VIS_H - 3)
            pts = list(zip(xs.tolist(), ys.tolist()))
        d.line(pts, fill=tuple(int(x * 0.35) for x in c), width=5)
        d.line(pts, fill=c, width=2)
        cur = np.asarray(layer, np.float32)
        glow = np.maximum(cur, prev * 0.55) if (o["glow"] and prev is not None) else cur
        st["glow"] = glow
        arr = np.maximum(bg, glow)
        img = Image.new("RGB", (WIDTH, HEIGHT), (4, 12, 8))
        img.paste(Image.fromarray(arr.astype(np.uint8), "RGB"), (0, 0))
        return img

    # -- 5. Kreis-Spektrum --------------------------------------------------- #
    @vis_style("ring")
    def vis_ring(self, s, o, color):
        S = 2
        img = Image.new("RGB", (WIDTH * S, HEIGHT * S), (6, 6, 12))
        d = ImageDraw.Draw(img)
        cx, cy = WIDTH / 2 * S, (VIS_H / 2 + 6) * S
        t = s["t"]
        r0 = (34 + s["bass"] * 12) * S
        since = t - s["beat_t"]
        if 0 <= since < 0.6:                                # Welle bei jedem Schlag
            rr = r0 + since / 0.6 * 120 * S
            fade = 1 - since / 0.6
            c = color if o["colors"] == "layer" else _hue(s["beats"] * 0.11, 0.6, 1)
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=tuple(int(x * fade * 0.6) for x in c), width=2 * S)
        b = s["bands"]
        vals = np.concatenate([b, b[::-1]])
        n = len(vals)
        rot = t * 0.15
        for i, v in enumerate(vals):
            a = 2 * math.pi * i / n - math.pi / 2 + rot
            ln = (4 + v * 64) * S
            x1, y1 = cx + math.cos(a) * r0, cy + math.sin(a) * r0
            x2, y2 = cx + math.cos(a) * (r0 + ln), cy + math.sin(a) * (r0 + ln)
            c = _hue(i / n + t * 0.03, 0.85, 0.45 + 0.55 * v) if o["colors"] == "rainbow" else \
                tuple(int(x * (0.35 + 0.65 * v)) for x in color)
            d.line([(x1, y1), (x2, y2)], fill=c, width=3 * S)
        ri = r0 - 6 * S
        inner = _hue(t * 0.03, 0.7, 0.25 + 0.4 * s["bass"]) if o["colors"] == "rainbow" else \
            tuple(int(x * (0.2 + 0.4 * s["bass"])) for x in color)
        d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=inner)
        return img.reduce(S)

    # -- 6. VU-Meter --------------------------------------------------------- #
    def _vu_face(self, dark):
        key = ("vu", dark)
        cache = self.__dict__.setdefault("_vu_cache", {})
        if key in cache:
            return cache[key]
        S = 2
        img = Image.new("RGB", (WIDTH * S, HEIGHT * S), (10, 10, 14))
        d = ImageDraw.Draw(img)
        face = (32, 24, 12) if dark else (238, 226, 192)
        ink = (255, 176, 60) if dark else (40, 34, 28)
        red = (255, 80, 40) if dark else (200, 30, 25)
        font = load_font(10 * S, bold=True)
        big = load_font(14 * S, bold=True)
        for k, label in enumerate(("L", "R")):
            x0, y0, x1, y1 = (8 + k * 156) * S, 24 * S, (156 + k * 156) * S, (VIS_H - 8) * S
            d.rounded_rectangle([x0, y0, x1, y1], radius=8 * S, fill=face, outline=(90, 80, 60), width=2 * S)
            px, py = (x0 + x1) / 2, y1 - 22 * S
            rad = 74 * S
            for db, lab in ((-20, "20"), (-10, "10"), (-7, "7"), (-5, "5"), (-3, "3"), (-2, ""), (-1, ""), (0, "0"),
                            (1, ""), (2, ""), (3, "+3")):
                a = math.radians(self._vu_angle(10 ** (db / 20) / 10 ** (3 / 20)))
                col = red if db >= 0 else ink
                ox, oy = px + math.sin(a) * rad, py - math.cos(a) * rad
                ix, iy = px + math.sin(a) * (rad - 9 * S), py - math.cos(a) * (rad - 9 * S)
                d.line([(ix, iy), (ox, oy)], fill=col, width=2 * S)
                if lab:
                    tx, ty = px + math.sin(a) * (rad + 9 * S), py - math.cos(a) * (rad + 9 * S)
                    w = d.textlength(lab, font=font)
                    d.text((tx - w / 2, ty - 7 * S), lab, font=font, fill=col)
            a0 = self._vu_angle(1 / 10 ** (3 / 20))
            d.arc([px - rad, py - rad, px + rad, py + rad], -90 - 50, -90 + 50, fill=ink, width=S)
            d.arc([px - rad + 2 * S, py - rad + 2 * S, px + rad - 2 * S, py + rad - 2 * S], -90 + a0, -90 + 50,
                  fill=red, width=4 * S)
            w = d.textlength("VU", font=big)
            d.text((px - w / 2, py - 40 * S), "VU", font=big, fill=ink)
            d.text((x0 + 10 * S, y1 - 22 * S), label, font=big, fill=ink)
        cache.clear()
        cache[key] = (img, ink, red)
        return cache[key]

    @staticmethod
    def _vu_angle(v):
        """Zeigerwinkel (−50° … +50°) für einen Pegel 0…1 (oben gestaucht wie bei echten VU-Metern)."""
        return -50 + 100 * max(0.0, min(1.05, v)) ** 0.7

    @vis_style("vu")
    def vis_vu(self, s, o, color):
        S = 2
        face, ink, red = self._vu_face(o["dial"] == "dark")
        img = face.copy()
        d = ImageDraw.Draw(img)
        st = self._vstate("vu", lambda: {"n": [s["left"], s["right"]]})
        dt = self._vis_dt(st, s["t"])
        for k, lvl in enumerate((s["left"], s["right"])):
            st["n"][k] += (lvl - st["n"][k]) * min(1.0, dt * 9 if dt else 1.0)   # träger Zeiger
            x0, x1, y1 = (8 + k * 156) * S, (156 + k * 156) * S, (VIS_H - 8) * S
            px, py = (x0 + x1) / 2, y1 - 22 * S
            a = math.radians(self._vu_angle(st["n"][k]))
            tip = (px + math.sin(a) * 80 * S, py - math.cos(a) * 80 * S)
            d.line([(px, py), tip], fill=(20, 20, 20) if o["dial"] != "dark" else (255, 220, 160), width=2 * S)
            d.ellipse([px - 7 * S, py - 7 * S, px + 7 * S, py + 7 * S], fill=(30, 30, 30))
            led = red if lvl > 0.92 else (70, 30, 25)
            d.ellipse([x1 - 22 * S, (24 + 10) * S, x1 - 12 * S, (24 + 20) * S], fill=led)
        return img.reduce(S)

    # -- 7. Spektrogramm ----------------------------------------------------- #
    @staticmethod
    def _spectro_lut(name):
        x = np.linspace(0, 1, 256)[:, None]
        if name == "ice":
            stops = [(0, (0, 0, 0)), (0.35, (10, 30, 110)), (0.7, (40, 190, 230)), (1, (240, 255, 255))]
        elif name == "rainbow":
            return np.array([_hue(0.72 - 0.72 * v, 0.9, min(1.0, v * 1.6)) for v in x[:, 0]], np.uint8)
        else:
            stops = [(0, (0, 0, 0)), (0.3, (120, 0, 20)), (0.6, (240, 90, 0)), (0.85, (255, 210, 40)), (1, (255, 255, 230))]
        pos = [p for p, _ in stops]
        return np.stack([np.interp(x[:, 0], pos, [c[i] for _, c in stops]) for i in range(3)], 1).astype(np.uint8)

    @vis_style("spectro")
    def vis_spectro(self, s, o, color):
        top = 20
        rows = VIS_H - top
        st = self._vstate("spectro", dict)
        if st.get("palette") != o["palette"]:
            st["palette"], st["lut"] = o["palette"], self._spectro_lut(o["palette"])
        lut = st["lut"]
        yy = np.linspace(AUDIO_BANDS - 1, 0, rows)

        def column(bands):
            return lut[(np.clip(np.interp(yy, np.arange(AUDIO_BANDS), bands), 0, 1) * 255).astype(int)]

        if "hist" not in st:
            st["hist"] = np.zeros((rows, WIDTH, 3), np.uint8)
            if s.get("demo"):                               # Vorschau: Verlauf gleich gefüllt
                for k in range(WIDTH // 2):
                    col = column(demo_snapshot(s["t"] - (WIDTH // 2 - k) * 0.05, 0.22 if s.get("idle") else 1)["bands"])
                    st["hist"][:, 2 * k:2 * k + 2] = col[:, None]
        h = st["hist"]
        h[:, :-2] = h[:, 2:]
        h[:, -2:] = column(s["bands"])[:, None]
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        img.paste(Image.fromarray(h, "RGB"), (0, top))
        d = ImageDraw.Draw(img)
        for f, lab in ((100, "100"), (1000, "1k"), (10000, "10k")):
            band = math.log(f / 40) / math.log(11000 / 40) * AUDIO_BANDS
            y = top + rows - 1 - band / (AUDIO_BANDS - 1) * (rows - 1)
            d.line([(0, y), (4, y)], fill=(160, 160, 170))
            d.text((6, y - 7), lab, font=self.f_tiny, fill=(160, 160, 170))
        return img

    # -- 8. Feuerwerk -------------------------------------------------------- #
    def _fw_bg(self):
        if "_fw_bg_img" not in self.__dict__:
            ys = np.linspace(0, 1, VIS_H)[:, None, None]
            arr = np.broadcast_to(np.array([2, 3, 14], np.float32) * (1 - ys) + np.array([16, 14, 40], np.float32) * ys,
                                  (VIS_H, WIDTH, 3)).copy()
            sky = Image.new("L", (WIDTH, VIS_H), 0)
            d = ImageDraw.Draw(sky)
            rng = random.Random(7)
            x = 0
            while x < WIDTH:                               # Häuser am unteren Rand
                w, h = rng.randint(14, 34), rng.randint(12, 44)
                d.rectangle([x, VIS_H - h, x + w, VIS_H], fill=255)
                x += w + rng.randint(0, 3)
            self._fw_bg_img = (arr, np.asarray(sky) > 0)
        return self._fw_bg_img

    def _fw_burst(self, st, t, seed, level):
        rng = random.Random(seed)
        n = 36 + int(level * 30)
        x, y = rng.uniform(50, WIDTH - 50), rng.uniform(30, 105)
        ang = np.array([rng.uniform(0, 2 * math.pi) for _ in range(n)])
        spd = np.array([rng.uniform(45, 95 + level * 50) for _ in range(n)])
        hue = rng.random()
        cols = np.array([_hue(hue + rng.uniform(-0.05, 0.05), rng.uniform(0.5, 1.0), 1.0) for _ in range(n)], np.float32)
        new = {"x": np.full(n, x), "y": np.full(n, y), "vx": np.cos(ang) * spd, "vy": np.sin(ang) * spd,
               "age": np.zeros(n), "life": np.array([rng.uniform(0.9, 1.6) for _ in range(n)]), "c": cols}
        p = st["p"]
        for k in p:
            p[k] = np.concatenate([p[k], new[k]]) if len(p[k]) else new[k]

    def _fw_step(self, st, dt):
        p = st["p"]
        if not len(p["x"]):
            return
        p["vy"] = p["vy"] + 55 * dt
        p["vx"] = p["vx"] * (1 - 0.9 * dt)
        p["x"] = p["x"] + p["vx"] * dt
        p["y"] = p["y"] + p["vy"] * dt
        p["age"] = p["age"] + dt
        keep = p["age"] < p["life"]
        for k in p:
            p[k] = p[k][keep]

    @vis_style("fireworks")
    def vis_fireworks(self, s, o, color):
        t = s["t"]
        bg, sky = self._fw_bg()
        empty = {k: np.zeros(0) for k in ("x", "y", "vx", "vy", "age", "life")}
        st = self._vstate("fireworks", lambda: {"p": dict(empty, c=np.zeros((0, 3), np.float32)), "beats": s["beats"],
                                                 "last": t, "n": 0, "glow": None})
        if "t" not in st:                                   # erstes Bild: zwei Raketen sind schon explodiert
            st["t"] = t
            for k, age in enumerate((0.55, 0.2)):
                self._fw_burst(st, t, s["beats"] * 31 + k, s["level"])
                for _ in range(int(age / 0.05)):
                    self._fw_step(st, 0.05)
        dt = self._vis_dt(st, t)
        if s["beats"] != st["beats"] or t - st["last"] > 1.4:
            st["beats"], st["last"], st["n"] = s["beats"], t, st["n"] + 1
            self._fw_burst(st, t, s["beats"] * 31 + st["n"], s["level"])
        self._fw_step(st, dt)
        glow = st["glow"]
        glow = glow * 0.72 if (o["trails"] and glow is not None) else np.zeros((VIS_H, WIDTH, 3), np.float32)
        p = st["p"]
        if len(p["x"]):
            fade = np.sqrt(np.clip(1 - p["age"] / p["life"], 0, 1))[:, None]
            c = np.minimum(255, p["c"] * fade + 90 * np.clip(1 - p["age"] / 0.35, 0, 1)[:, None])  # jung: heller Kern
            xi, yi = p["x"].astype(int), p["y"].astype(int)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
                ok = (xi + dx >= 0) & (xi + dx < WIDTH) & (yi + dy >= 0) & (yi + dy < VIS_H)
                glow[yi[ok] + dy, xi[ok] + dx] = np.maximum(glow[yi[ok] + dy, xi[ok] + dx], c[ok])
        st["glow"] = glow
        arr = np.maximum(bg, glow)
        arr[sky] = (3, 3, 8)
        img = Image.new("RGB", (WIDTH, HEIGHT), (3, 3, 8))
        img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB"), (0, 0))
        return img


@page_keys("visual")
def keys_visual(app, pressed):
    """MENU (wie SETTINGS kurz) öffnet die Auswahl des Stils; OK löst bei Weihnachten/Feierabend sofort einen Gag
    aus; sonst blättern die Pfeiltasten."""
    if pressed & LKEY_BITS["MENU"]:
        app.menu = VisualMenu(app)
        app.flash = None
        app.next_draw = 0
        return True
    if pressed & LKEY_BITS["OK"] and app.visual_style() == "xmas" and \
            party_active(visual_options(app.settings(), "xmas")):
        app.renderer._party_poke = True                     # Feierabend: Gag auf Bestellung
        app.next_draw = 0
        return True
    return False
