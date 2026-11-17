"""Visualisierung „Walzer“, Teil 1: die Orte (Mixin WaltzPlaces).

Jeder Ort wird einmal in Ebenen gemalt (_wz_paint_<ort>): Landschaft (RGBA, durchsichtig wo Himmel ist),
Leuchtebene (Fenster, Laternen, Fackeln, Kronleuchter – wirkt in Dämmerung und Nacht), Schneemaske (wo bei Schnee
Schnee liegt) und Wassermaske (spiegelt den Himmel). _wz_backdrop setzt daraus das Bild für Sonnenhöhe und Wetter
zusammen: Himmel nach Sonnenstand (Farben wie die Uhr „Himmel“), Sonne bzw. Mond und Sterne, Wolken, Umgebungslicht
(Tag weiß, Dämmerung golden, Nacht blau und dunkel), Leuchtebene, Schnee. Das Ergebnis wird je Ort, Lichtstufe und
Wetter zwischengespeichert; je Bild kommen nur Paar, Flammen und Wetterteilchen dazu.
Eigene Fotos (WALTZ_PHOTO_DIR/<ort>.jpg, hochgeladen in der Verwaltung) ersetzen Landschaft und Himmel; sie werden
nach Tageszeit abgedunkelt und eingefärbt.
"""
import math
import random

from PIL import ImageFilter

WZ_FLOOR = VIS_H - 24                   # Fußlinie des Paares (Mitte der Tanzrunde)
WZ_TIMES = {"morning": (4.0, -1), "day": (42.0, -1), "evening": (-1.0, 1), "night": (-24.0, 1)}   # Sonnenhöhe, Seite
WZ_NIGHT_AMB = (0.17, 0.21, 0.38)
WZ_GLOW_COLS = {"ballroom": (255, 196, 110), "castle": (255, 130, 40), "alm": (255, 190, 100),
                "steel": (255, 110, 30), "farm": (255, 200, 120), "lake": (255, 214, 140),
                "alps": (255, 200, 130), "beach": (255, 150, 200)}
WZ_CACHE_MAX = 6                        # fertige Hintergründe (Ort, Lichtstufe, Wetter)
WZ_LAYERS_MAX = 3                       # gemalte Orte im Speicher


def _wz_noise(h, w, seed, cell=8):
    """Wertrauschen −1…1, bilinear aus einem groben Gitter (Gras, Stein, Sand)."""
    rng = np.random.RandomState(seed)
    grid = rng.uniform(-1, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    ys, xs = np.arange(h) / cell, np.arange(w) / cell
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a, b = grid[y0][:, x0], grid[y0][:, x0 + 1]
    c, d = grid[y0 + 1][:, x0], grid[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _wz_lerp(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


class _WzCanvas:
    """Malfläche eines Ortes: Farbe, Deckkraft, Leuchten, Schnee- und Wassermaske (numpy, float)."""

    def __init__(self, seed):
        self.rgb = np.zeros((HEIGHT, WIDTH, 3), np.float32)
        self.a = np.zeros((HEIGHT, WIDTH), np.float32)
        self.glow = np.zeros((HEIGHT, WIDTH, 3), np.float32)
        self.snow = np.zeros((HEIGHT, WIDTH), np.float32)
        self.water = np.zeros((HEIGHT, WIDTH), np.float32)
        self.fine = np.random.RandomState(seed).uniform(-1, 1, (HEIGHT, WIDTH)).astype(np.float32)
        self.seed = seed
        self.ys = np.arange(HEIGHT, dtype=np.float32)[:, None]
        self.xs = np.arange(WIDTH, dtype=np.float32)[None, :]

    @staticmethod
    def mask(draw):
        m = Image.new("L", (WIDTH, HEIGHT), 0)
        draw(ImageDraw.Draw(m))
        return np.asarray(m, np.float32) / 255

    def fill(self, m, color, tex=None, k=0.0, fine=0.0, bottom=None, y0=0, y1=HEIGHT, snow=0.0, shade=None):
        """Fläche m in color (bzw. senkrechter Verlauf color → bottom zwischen y0 und y1), mit Struktur tex·k und
        Körnung fine; shade: zusätzlicher Helligkeitsfaktor (Array) – Licht von links oben. snow: Anteil Schnee bei
        Schneewetter (None = Schneemaske darunter behalten, z. B. Blumen auf der Wiese)."""
        col = np.array(color, np.float32)[None, None, :]
        if bottom is not None:
            f = np.clip((self.ys - y0) / max(1, y1 - y0), 0, 1)[..., None]
            col = col * (1 - f) + np.array(bottom, np.float32)[None, None, :] * f
        mul = 1.0
        if tex is not None and k:
            mul = mul + tex * k
        if fine:
            mul = mul + self.fine * fine
        if shade is not None:
            mul = mul * shade
        col = col * (mul[..., None] if not np.isscalar(mul) else mul)
        m3 = m[..., None]
        self.rgb = self.rgb * (1 - m3) + col * m3
        self.a = np.maximum(self.a, m)
        if snow is not None:
            self.snow = self.snow * (1 - m) + snow * m
        self.water *= (1 - m)

    def lamp(self, x, y, r, color, k=1.0):
        """Weicher Lichtschein (nur in der Leuchtebene)."""
        d2 = ((self.xs - x) ** 2 + (self.ys - y) ** 2) / (r * r)
        self.glow += np.exp(-d2 * 2.2)[..., None] * np.array(color, np.float32)[None, None, :] * k

    def glow_fill(self, m, color, k=1.0):
        self.glow += m[..., None] * np.array(color, np.float32)[None, None, :] * k

    def water_fill(self, m):
        self.water = np.maximum(self.water, m)
        self.a *= (1 - m)

    def image(self):
        rgba = np.dstack([np.clip(self.rgb, 0, 255), np.clip(self.a, 0, 1) * 255]).astype(np.uint8)
        return Image.fromarray(rgba, "RGBA")


class WaltzPlaces:
    # -- Licht -------------------------------------------------------------- #
    def _wz_sun(self, o, t_wall=None):
        """(Sonnenhöhe in °, Seite −1 = Osten/links, +1 = Westen/rechts) nach Option Tageszeit."""
        mode = o.get("daytime", "real")
        if mode in WZ_TIMES:
            return WZ_TIMES[mode]
        ts = time.time() if t_wall is None else t_wall
        lat, lon, _ = self._sky_place()
        alt, east, _ = _sky_sun_dir(ts, lat, lon)
        return alt, (-1 if east > 0 else 1)

    @staticmethod
    def _wz_light(alt, sky):
        """Umgebungslicht (r, g, b Faktoren) und Stärke der Leuchtebene für Sonnenhöhe und Himmel."""
        day = _smooth((alt + 9) / 18)
        gold = max(0.0, 1 - abs(alt - 2.0) / 8.0) * (0.35 if sky in ("cloudy", "rain", "snow", "thunder", "fog") else 1)
        amb = _wz_lerp(WZ_NIGHT_AMB, (1.0, 1.0, 1.0), day)
        amb = _wz_lerp(amb, (amb[0] * 1.05, amb[1] * 0.8, amb[2] * 0.6), gold * 0.75)
        dull = {"cloudy": 0.3, "rain": 0.42, "thunder": 0.55, "snow": 0.25, "fog": 0.3, "partly": 0.08}.get(sky, 0.0)
        if dull:
            m = sum(amb) / 3
            amb = tuple((c * (1 - dull * 0.6) + m * dull * 0.6) * (1 - dull * 0.45) for c in amb)
        glow = max(0.0, min(1.0, (4.0 - alt) / 10.0))
        if dull:
            glow = max(glow, dull * 0.5)
        return amb, glow

    @staticmethod
    def _wz_sky(alt, sky, horizon, side, t_wall):
        """Himmel (RGB-Array HEIGHT×WIDTH) mit Sonne bzw. Mond und Sternen, Wolken."""
        base = _sky_grad(_sky_SKY_STOPS, alt)
        top = tuple(c * 0.72 for c in base)
        gold = max(0.0, 1 - abs(alt - 1.0) / 7.0)
        hor = _wz_lerp(tuple(min(255, c * 1.25 + 18) for c in base), (255, 170, 110), gold * 0.8)
        if sky in ("cloudy", "rain", "snow", "thunder", "fog"):
            lum = (sum(base) / 3) * (0.9 if sky != "thunder" else 0.6)
            g = {"fog": (205, 208, 214), "snow": (200, 204, 214)}.get(sky, (165, 170, 182))
            k = max(0.08, min(1.0, lum / 150))
            top = tuple(c * k * (0.8 if sky != "fog" else 0.95) for c in g)
            hor = tuple(c * k for c in g)
        ys = np.clip(np.arange(HEIGHT, dtype=np.float32) / max(1, horizon), 0, 1)[:, None, None] ** 1.3
        arr = np.array(top, np.float32)[None, None, :] * (1 - ys) + np.array(hor, np.float32)[None, None, :] * ys
        arr = np.broadcast_to(arr, (HEIGHT, WIDTH, 3)).copy()
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        clear = sky in ("clear", "partly")
        rng = random.Random(77)
        if alt < -4 and clear:                                                      # Sterne
            k = min(1.0, (-4 - alt) / 8)
            for _ in range(70):
                x, y = rng.randrange(WIDTH), rng.randrange(0, max(10, horizon - 8))
                v = int(rng.randint(120, 240) * k)
                bg = img.getpixel((x, y))
                d.point((x, y), fill=tuple(max(c, v) for c in bg))
        sx = WIDTH * (0.5 + side * 0.32)
        if alt > -2 and sky != "fog":                                               # Sonne mit Schein
            sy = horizon - 6 - max(0.0, min(1.0, alt / 40)) * (horizon - 30)
            col = tuple(int(c) for c in _wz_lerp((255, 248, 220), (255, 150, 70), gold))
            halo = Image.new("L", (WIDTH, HEIGHT), 0)
            ImageDraw.Draw(halo).ellipse([sx - 34, sy - 34, sx + 34, sy + 34], fill=110 if clear else 50)
            halo = halo.filter(ImageFilter.GaussianBlur(14))
            img.paste(col, (0, 0), halo)
            if clear:
                d.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=col)
        elif alt < -6 and clear:                                                    # Mond mit Phase
            _, frac, lit = _sky_moon(t_wall)
            mx, my = WIDTH - sx, 34
            d.ellipse([mx - 10, my - 10, mx + 10, my + 10], fill=tuple(int(c * 1.6 + 10) for c in top))
            d.polygon(_sky_moon_poly(mx, my, 10, frac), fill=(236, 234, 214))
            glow = Image.new("L", (WIDTH, HEIGHT), 0)
            ImageDraw.Draw(glow).ellipse([mx - 22, my - 22, mx + 22, my + 22], fill=int(40 * lit))
            img.paste((220, 225, 240), (0, 0), glow.filter(ImageFilter.GaussianBlur(8)))
        if sky in ("partly", "cloudy", "rain", "thunder", "snow"):                  # Wolken
            n = {"partly": 5, "cloudy": 10}.get(sky, 12)
            lum = max(0.15, min(1.0, (sum(base) / 3) / 140))
            dark = {"partly": 1.0, "cloudy": 0.85, "snow": 0.85}.get(sky, 0.6)
            cl = Image.new("L", (WIDTH, HEIGHT), 0)
            cd = ImageDraw.Draw(cl)
            rng = random.Random(31)
            for _ in range(n):
                cx, cy = rng.uniform(-20, WIDTH + 20), rng.uniform(8, max(20, horizon * 0.6))
                w = rng.uniform(40, 90)
                for j in range(4):
                    ox = (j - 1.5) * w * 0.28
                    r = w * (0.22 + 0.1 * (j % 2))
                    cd.ellipse([cx + ox - r, cy - r * 0.7, cx + ox + r, cy + r * 0.5], fill=200)
            cl = cl.filter(ImageFilter.GaussianBlur(5))
            ccol = tuple(int(c * lum * dark) for c in (236, 238, 245))
            if gold and sky == "partly":
                ccol = tuple(int(c) for c in _wz_lerp(ccol, (255, 160, 120), gold * 0.6))
            img.paste(ccol, (0, 0), cl)
        return img

    # -- Zusammensetzen ------------------------------------------------------ #
    def _wz_place_layers(self, place):
        cache = self.__dict__.setdefault("_wz_layers", {})
        if place not in cache:
            if len(cache) >= WZ_LAYERS_MAX:                                     # je Ort ≈ 3 MB
                cache.pop(next(iter(cache)))
            cache[place] = getattr(self, "_wz_paint_" + place)()
        return cache[place]

    def _wz_photo(self, place):
        """Eigenes Foto des Ortes (Displaygröße) oder None; neu gelesen, wenn sich die Datei ändert."""
        path = os.path.join(WALTZ_PHOTO_DIR, place + ".jpg")
        try:
            mt = os.stat(path).st_mtime
        except OSError:
            return None
        cache = self.__dict__.setdefault("_wz_photos", {})
        hit = cache.get(place)
        if hit and hit[0] == mt:
            return hit[1]
        try:
            raw = Image.open(path)
            raw.load()
            img = raw.convert("RGB")
            if img.size != WALTZ_PHOTO_SIZE:
                img = fit_photo(img, WALTZ_PHOTO_SIZE, "cover")
        except Exception:                                               # kaputte Datei: gemalter Ort
            img = None
        cache[place] = (mt, img)
        return img

    def _wz_backdrop(self, place, alt, side, sky, photo, t_wall):
        """Fertiger Hintergrund (RGB) für Ort, Sonnenhöhe (in Stufen), Himmel und Foto (zwischengespeichert)."""
        key = (place, round(alt) if -20 < alt < 25 else (25 if alt >= 25 else -20), side, sky,
               id(photo) if photo is not None else None)
        cache = self.__dict__.setdefault("_wz_bg", {})
        if key in cache:
            return cache[key]
        if len(cache) >= WZ_CACHE_MAX:
            cache.pop(next(iter(cache)))
        amb, glow = self._wz_light(alt, sky)
        if photo is not None:
            arr = np.zeros((HEIGHT, WIDTH, 3), np.float32)
            arr[:VIS_H] = np.asarray(photo, np.float32)
            arr[VIS_H:] = arr[VIS_H - 1:VIS_H]
            k = np.array(amb, np.float32) ** 0.8
            gray = arr.mean(axis=2, keepdims=True)
            night = 1 - _smooth((alt + 5) / 15)
            arr = (arr * (1 - night * 0.35) + gray * night * 0.35) * k[None, None, :]
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
            cache[key] = (img, amb, glow)
            return cache[key]
        L = self._wz_place_layers(place)
        sky_img = self._wz_sky(alt, sky, L["horizon"], side, t_wall)
        out = np.asarray(sky_img, np.float32).copy()
        if L["water"] is not None:                                                  # Wasser spiegelt den Himmel
            h = L["horizon"]
            src = np.clip(2 * h - np.arange(HEIGHT), 0, HEIGHT - 1)
            wcol = np.array((18, 58, 96), np.float32) * np.array(amb, np.float32)
            refl = out[src] * 0.5 + wcol[None, None, :] * 0.5
            ripple = 1 + 0.05 * _wz_noise(HEIGHT, WIDTH, 51, 3) * np.clip((np.arange(HEIGHT)[:, None] - h) / 30, 0.3, 1.5)
            refl = refl * ripple[..., None]
            if alt > -3 and sky in ("clear", "partly"):                             # Glitzern der Sonne
                sx = WIDTH * (0.5 + side * 0.32)
                band = np.exp(-((np.arange(WIDTH) - sx) / 10.0) ** 2)[None, :] * (np.arange(HEIGHT) > h)[:, None]
                spark = (L["fine"] > 0.55) * band
                refl += spark[..., None] * np.array((255, 200, 140), np.float32)[None, None, :] * 0.8
            w = L["water"][..., None]
            out = out * (1 - w) + refl * w
        land = L["rgb"] * np.array(amb, np.float32)[None, None, :]
        if sky == "snow":                                                           # Schnee liegt
            sn = (L["snow"] * 0.85)[..., None]
            land = land * (1 - sn) + np.array((238, 242, 250), np.float32)[None, None, :] * np.array(amb)[None, None, :] * sn
        if L["indoor"]:                                                             # Saal: Kerzenlicht drinnen
            inner = _wz_lerp((0.82, 0.68, 0.52), (1.0, 0.97, 0.92), _smooth((alt + 5) / 15))
            land = L["rgb"] * np.array(inner, np.float32)[None, None, :]
            glow = max(0.55, glow)
        a = L["a"][..., None]
        out = out * (1 - a) + land * a
        if sky == "fog":
            fog = np.clip((np.arange(HEIGHT) / VIS_H) * 0.25 + 0.3, 0, 0.6)[:, None, None] * (0 if L["indoor"] else 1)
            out = out * (1 - fog) + np.array((200, 204, 212), np.float32) * np.array(amb)[None, None, :] * fog
        out += L["glow"] * glow
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
        cache[key] = (img, amb, glow)
        return cache[key]

    @staticmethod
    def _wz_done(c, horizon, indoor=False, flames=(), extra=None):
        out = {"rgb": c.rgb, "a": c.a, "glow": c.glow, "snow": c.snow, "fine": c.fine,
               "water": c.water if c.water.any() else None, "horizon": horizon, "indoor": indoor,
               "flames": list(flames)}
        out.update(extra or {})
        return out

    @staticmethod
    def _wz_pines(c, xs_y, color, seed, snow=0.6):
        """Tannen als Dreiecksstapel: xs_y = [(x, Fuß-y, Höhe), …]."""
        def draw(d):
            for x, y, h in xs_y:
                for k in range(3):
                    w = h * (0.34 - k * 0.08)
                    yy = y - h * k * 0.28
                    d.polygon([(x - w, yy), (x + w, yy), (x, yy - h * 0.55)], fill=255)
        m = c.mask(draw)
        c.fill(m, color, fine=0.12, snow=snow, shade=1 + 0.18 * np.sin(c.xs * 0.9))

    # -- 1. Ballsaal --------------------------------------------------------- #
    def _wz_paint_ballroom(self):
        c = _WzCanvas(41)
        fy = 128
        tex = _wz_noise(HEIGHT, WIDTH, 3, 6)
        c.fill(c.mask(lambda d: d.rectangle([0, 0, WIDTH, fy], fill=255)), (232, 212, 174), tex, 0.03, 0.02)
        c.fill(c.mask(lambda d: d.rectangle([0, 0, WIDTH, 10], fill=255)), (196, 160, 80), bottom=(150, 118, 50),
               y0=0, y1=10)                                                         # Gesims
        c.fill(c.mask(lambda d: d.rectangle([0, fy - 20, WIDTH, fy], fill=255)), (176, 140, 98), tex, 0.04)
        for px in range(0, WIDTH + 1, 80):                                          # Pilaster
            c.fill(c.mask(lambda d, px=px: d.rectangle([px - 8, 10, px + 8, fy - 20], fill=255)), (246, 232, 200),
                   shade=np.clip(1.05 - (c.xs - px + 8) / 60, 0.8, 1.1))
            c.fill(c.mask(lambda d, px=px: d.rectangle([px - 10, 10, px + 10, 16], fill=255)), (210, 172, 90))
        windows = []
        for wx in (40, 120, 200, 280):                                              # hohe Bogenfenster
            box = [wx - 17, 26, wx + 17, 104]
            m = c.mask(lambda d, b=box: (d.rectangle([b[0], b[1] + 17, b[2], b[3]], fill=255),
                                         d.ellipse([b[0], b[1], b[2], b[1] + 34], fill=255)))
            c.fill(m, (170, 140, 80))
            inner = c.mask(lambda d, b=box: (d.rectangle([b[0] + 3, b[1] + 17, b[2] - 3, b[3] - 3], fill=255),
                                             d.ellipse([b[0] + 3, b[1] + 3, b[2] - 3, b[1] + 31], fill=255)))
            c.rgb *= (1 - inner)[..., None]
            c.a *= (1 - inner)
            windows.append(inner)
            for k in (0, 1):                                                        # Sprossen
                c.fill(c.mask(lambda d, wx=wx, b=box: d.line([(wx, b[1] + 3), (wx, b[3])], fill=255, width=2)),
                       (190, 160, 96))
                c.fill(c.mask(lambda d, b=box: d.line([(b[0], 66), (b[2], 66)], fill=255, width=2)), (190, 160, 96))
            for sd in (-1, 1):                                                      # Vorhänge
                x0 = wx + sd * 17
                m = c.mask(lambda d, x0=x0, sd=sd: d.polygon([(x0 - sd * 2, 18), (x0 + sd * 9, 18), (x0 + sd * 8, 108),
                                                               (x0 - sd * 6, 108), (x0 - sd * 1, 60)], fill=255))
                c.fill(m, (150, 22, 34), shade=0.85 + 0.25 * np.sin(c.xs * 1.3) ** 2)
            c.fill(c.mask(lambda d, wx=wx: d.rectangle([wx - 27, 14, wx + 27, 20], fill=255)), (200, 160, 70))
        # Parkett in Fluchtpunktperspektive mit Glanz
        floor = c.mask(lambda d: d.rectangle([0, fy, WIDTH, HEIGHT], fill=255))
        vx, vy = WIDTH / 2, fy - 90
        ang = np.arctan2(c.xs - vx, c.ys - vy + 1e-3)
        planks = (np.floor(ang * 26) % 2) * 0.08
        depth = (c.ys - fy) / (HEIGHT - fy)
        shade = (0.86 + planks + 0.16 * depth) * (1 + 0.05 * np.sin(np.clip(c.ys - fy, 0, None) ** 0.8 * 3))
        c.fill(floor, (150, 92, 48), _wz_noise(HEIGHT, WIDTH, 9, 3), 0.05, shade=shade)
        gloss = np.zeros((HEIGHT, WIDTH), np.float32)
        for wx in (40, 120, 200, 280):                                              # Fensterlicht spiegelt sich
            gloss += np.exp(-((c.xs - wx) / 9) ** 2) * np.clip(1 - (c.ys - fy) / 70, 0, 1) * (c.ys > fy)
        c.rgb += (gloss * 40)[..., None]
        c.fill(c.mask(lambda d: d.rectangle([0, fy - 2, WIDTH, fy + 1], fill=255)), (110, 80, 50))
        # Kronleuchter
        for cx in (100, 220):
            c.fill(c.mask(lambda d, cx=cx: d.line([(cx, 0), (cx, 24)], fill=255, width=1)), (150, 120, 60))
            c.fill(c.mask(lambda d, cx=cx: d.ellipse([cx - 22, 22, cx + 22, 34], fill=255)), (220, 182, 80),
                   shade=np.clip(1.2 - (c.ys - 22) / 14, 0.7, 1.2))
            c.fill(c.mask(lambda d, cx=cx: d.polygon([(cx - 8, 34), (cx + 8, 34), (cx, 46)], fill=255)),
                   (230, 230, 240), fine=0.3)
            for k in range(-3, 4):
                bx = cx + k * 7
                c.fill(c.mask(lambda d, bx=bx: d.rectangle([bx - 1, 16, bx + 1, 22], fill=255)), (250, 245, 230))
                c.lamp(bx, 15, 5, (255, 220, 150), 0.9)
            c.lamp(cx, 30, 46, (255, 196, 110), 0.55)
        for px in range(80, WIDTH, 80):                                             # Wandleuchter
            c.fill(c.mask(lambda d, px=px: d.rectangle([px - 3, 60, px + 3, 68], fill=255)), (200, 160, 70))
            c.lamp(px, 56, 18, (255, 200, 120), 0.8)
        c.lamp(WIDTH / 2, fy + 40, 120, (255, 190, 110), 0.12)                    # Licht auf dem Parkett
        return self._wz_done(c, 104, indoor=True, extra={"windows": sum(windows).clip(0, 1)})

    # -- 2. Burghof ---------------------------------------------------------- #
    def _wz_paint_castle(self):
        c = _WzCanvas(42)
        gy = 138
        stone = _wz_noise(HEIGHT, WIDTH, 5, 5)
        mortar = ((c.ys.astype(int) % 9 == 0) | (((c.xs.astype(int) + (c.ys.astype(int) // 9) * 7) % 18) == 0))
        wall_shade = 1 - mortar * 0.25

        def wall(d):
            d.rectangle([0, 64, WIDTH, gy], fill=255)
            for x in range(0, WIDTH, 26):
                d.rectangle([x, 54, x + 13, 64], fill=255)
        c.fill(c.mask(wall), (140, 128, 110), stone, 0.10, 0.05, shade=wall_shade, snow=0.0)
        c.fill(c.mask(lambda d: [d.rectangle([x, 53, x + 13, 55], fill=255) for x in range(0, WIDTH, 26)]),
               (150, 140, 124), snow=1.0)
        for tx, tw, top, roof in ((10, 56, 18, None), (262, 50, 26, (60, 66, 92))):   # Türme
            c.fill(c.mask(lambda d, tx=tx, tw=tw, top=top: d.rectangle([tx, top, tx + tw, gy], fill=255)), (132, 120, 104),
                   stone, 0.1, 0.05, shade=wall_shade * np.clip(1.1 - (c.xs - tx) / (tw * 3), 0.75, 1.1))
            if roof:
                c.fill(c.mask(lambda d, tx=tx, tw=tw, top=top: d.polygon([(tx - 4, top), (tx + tw + 4, top),
                                                                           (tx + tw / 2, top - 34)], fill=255)),
                       roof, fine=0.08, snow=0.8, shade=np.clip(1.15 - (c.xs - tx) / tw * 0.5, 0.6, 1.2))
            else:
                c.fill(c.mask(lambda d, tx=tx, tw=tw, top=top: [d.rectangle([x, top - 9, x + 9, top], fill=255)
                                                                for x in range(tx, tx + tw - 4, 16)]), (132, 120, 104))
            for wy in (top + 22, top + 50):                                         # Fensterschlitze
                m = c.mask(lambda d, tx=tx, tw=tw, wy=wy: d.rectangle([tx + tw / 2 - 2, wy, tx + tw / 2 + 2, wy + 12], fill=255))
                c.fill(m, (30, 26, 24))
                c.glow_fill(m, (255, 180, 80), 0.9)
                c.lamp(tx + tw / 2, wy + 6, 10, (255, 160, 60), 0.4)
        c.fill(c.mask(lambda d: (d.rectangle([140, 96, 180, gy], fill=255), d.ellipse([140, 80, 180, 112], fill=255))),
               (70, 46, 30), _wz_noise(HEIGHT, WIDTH, 2, 2), 0.1, shade=1 - (c.xs.astype(int) % 6 == 0) * 0.3)
        for bx, col in ((110, (170, 30, 36)), (210, (30, 60, 150))):                # Banner
            c.fill(c.mask(lambda d, bx=bx: d.polygon([(bx - 8, 66), (bx + 8, 66), (bx + 8, 100), (bx, 94), (bx - 8, 100)],
                                                     fill=255)), col, shade=0.85 + 0.2 * np.sin(c.xs * 0.8) ** 2)
            c.fill(c.mask(lambda d, bx=bx: d.ellipse([bx - 4, 74, bx + 4, 82], fill=255)), (230, 190, 60))
        floor = c.mask(lambda d: d.rectangle([0, gy, WIDTH, HEIGHT], fill=255))   # Kopfsteinpflaster
        cob = np.abs(np.sin(c.xs * (0.55 - 0.0012 * (c.ys - gy)) + (c.ys // 5) * 1.3) * np.sin(c.ys * 0.65))
        c.fill(floor, (128, 118, 104), bottom=(110, 100, 88), y0=gy, y1=HEIGHT, fine=0.06,
               shade=0.78 + 0.3 * cob, snow=1.0)
        flames = []
        for fx in (96, 224):                                                        # Fackeln
            c.fill(c.mask(lambda d, fx=fx: d.polygon([(fx - 2, 104), (fx + 2, 104), (fx + 1, 120), (fx - 1, 120)],
                                                     fill=255)), (70, 50, 34))
            c.lamp(fx, 100, 30, (255, 140, 40), 0.9)
            flames.append((fx, 102, 1.0))
        return self._wz_done(c, gy - 70, flames=flames)

    # -- 3. Alm -------------------------------------------------------------- #
    def _wz_paint_alm(self):
        c = _WzCanvas(43)
        xs = np.arange(WIDTH)
        ridge = 52 + 18 * np.sin(xs * 0.021 + 1) + 10 * np.sin(xs * 0.057) + 4 * np.sin(xs * 0.19)
        mtn = (c.ys >= ridge[None, :]).astype(np.float32) * (c.ys < 120)
        rock = _wz_noise(HEIGHT, WIDTH, 7, 5)
        c.fill(mtn, (126, 134, 156), rock, 0.12, 0.04, shade=1 + 0.25 * np.sign(np.gradient(ridge))[None, :] * -0.5)
        capm = mtn * (c.ys < ridge[None, :] + 14 + 6 * rock)
        c.fill(capm, (236, 240, 248), rock, 0.05)
        hill = 96 + 6 * np.sin(xs * 0.03) + 3 * np.sin(xs * 0.11)
        c.fill((c.ys >= hill[None, :]).astype(np.float32), (88, 132, 66), _wz_noise(HEIGHT, WIDTH, 8, 6), 0.1, 0.05,
               snow=1.0)
        rng = random.Random(4)
        self._wz_pines(c, [(x, hill[min(WIDTH - 1, max(0, int(x)))] + 4, rng.uniform(14, 22))
                           for x in range(-4, WIDTH, 9) if not 200 < x < 300], (34, 74, 44), 4)
        mg = 128
        meadow = (c.ys >= mg).astype(np.float32)
        c.fill(meadow, (118, 176, 72), _wz_noise(HEIGHT, WIDTH, 12, 4), 0.12, 0.08, bottom=(92, 156, 58), y0=mg,
               y1=HEIGHT, snow=1.0)
        # Hütte
        hx0, hx1, hy0, hy1 = 214, 304, 84, 134
        logs = 0.85 + 0.2 * ((c.ys.astype(int) - hy0) % 7 > 1)
        c.fill(c.mask(lambda d: d.rectangle([hx0, hy0, hx1, hy1], fill=255)), (134, 84, 46), _wz_noise(HEIGHT, WIDTH, 13, 3),
               0.12, shade=logs)
        c.fill(c.mask(lambda d: d.polygon([(hx0 - 10, hy0 + 2), (hx1 + 10, hy0 + 2), ((hx0 + hx1) / 2, hy0 - 26)],
                                          fill=255)), (76, 60, 54), fine=0.12, snow=1.0,
               shade=np.clip(1.15 - (c.xs - hx0) / 200, 0.7, 1.2))
        c.fill(c.mask(lambda d: d.rectangle([hx1 - 22, hy0 - 30, hx1 - 14, hy0 - 10], fill=255)), (110, 100, 96))
        for wx in (228, 266):                                                       # Fenster mit Geranien
            m = c.mask(lambda d, wx=wx: d.rectangle([wx, 98, wx + 16, 112], fill=255))
            c.fill(m, (34, 30, 30))
            c.glow_fill(m, (255, 200, 110), 1.0)
            c.lamp(wx + 8, 106, 18, (255, 180, 90), 0.45)
            c.fill(c.mask(lambda d, wx=wx: d.line([(wx + 8, 98), (wx + 8, 112)], fill=255)), (230, 220, 200))
            c.fill(c.mask(lambda d, wx=wx: d.rectangle([wx - 2, 112, wx + 18, 116], fill=255)), (110, 70, 40))
            c.fill(c.mask(lambda d, wx=wx: [d.ellipse([wx - 2 + k * 4, 108, wx + 2 + k * 4, 113], fill=255)
                                            for k in range(5)]), (220, 40, 50), fine=0.2)
        c.fill(c.mask(lambda d: d.rectangle([286, 104, 298, hy1], fill=255)), (96, 60, 34))
        for x in range(8, 120, 22):                                                 # Zaun
            c.fill(c.mask(lambda d, x=x: d.rectangle([x, 128, x + 3, 146], fill=255)), (120, 86, 52), snow=0.3)
        c.fill(c.mask(lambda d: (d.line([(6, 134), (124, 134)], fill=255, width=2), d.line([(6, 141), (124, 141)], fill=255, width=2))),
               (130, 96, 60))
        rng = random.Random(9)
        flowers = c.mask(lambda d: [d.point((rng.randrange(WIDTH), rng.randrange(mg + 4, HEIGHT)), fill=255) for _ in range(260)])
        c.fill(flowers, (250, 250, 240), snow=None)
        rng = random.Random(10)
        c.fill(c.mask(lambda d: [d.point((rng.randrange(WIDTH), rng.randrange(mg + 4, HEIGHT)), fill=255) for _ in range(160)]),
               (250, 210, 60), snow=None)
        rng = random.Random(11)
        c.fill(c.mask(lambda d: [d.point((rng.randrange(WIDTH), rng.randrange(mg + 10, HEIGHT)), fill=255) for _ in range(90)]),
               (150, 90, 210), snow=None)
        return self._wz_done(c, 100)

    # -- 4. Stahlwerk -------------------------------------------------------- #
    def _wz_paint_steel(self):
        c = _WzCanvas(44)
        gy = 140
        rust = _wz_noise(HEIGHT, WIDTH, 15, 4)
        for x0, w, top, col in ((226, 9, 10, (150, 60, 44)), (250, 8, 22, (130, 56, 40))):   # Schlote
            c.fill(c.mask(lambda d, x0=x0, w=w, top=top: d.rectangle([x0, top, x0 + w, 90], fill=255)), col, rust, 0.15,
                   shade=np.clip(1.15 - (c.xs - x0) / w * 0.5, 0.6, 1.2))
            for by in range(top + 6, 90, 22):
                c.fill(c.mask(lambda d, x0=x0, w=w, by=by: d.rectangle([x0, by, x0 + w, by + 4], fill=255)), (220, 210, 200))
        # Hochofen mit Gerüst
        c.fill(c.mask(lambda d: d.polygon([(40, gy), (110, gy), (100, 40), (50, 40)], fill=255)), (96, 72, 60), rust, 0.2,
               shade=np.clip(1.25 - (c.xs - 40) / 70, 0.55, 1.25))
        c.fill(c.mask(lambda d: d.rectangle([60, 14, 90, 40], fill=255)), (88, 66, 56), rust, 0.2)
        c.fill(c.mask(lambda d: (d.line([(90, 26), (160, 60), (160, gy)], fill=255, width=4),
                                 d.line([(110, 70), (150, 70)], fill=255, width=2))), (70, 66, 70))
        lattice = c.mask(lambda d: [d.line([(x, 40), (x + 20, gy)], fill=255) for x in range(20, 130, 14)]
                         + [d.line([(x + 20, 40), (x, gy)], fill=255) for x in range(20, 130, 14)])
        c.fill(lattice * 0.7, (60, 58, 64))
        # Halle mit glühendem Tor
        c.fill(c.mask(lambda d: d.polygon([(176, gy), (176, 84), (248, 66), (320, 84), (320, gy)], fill=255)), (92, 98, 108),
               shade=0.88 + 0.12 * (c.xs.astype(int) % 5 < 3), fine=0.04, snow=0.0)
        c.fill(c.mask(lambda d: d.polygon([(174, 86), (248, 66), (322, 86), (322, 82), (248, 62), (174, 82)], fill=255)),
               (70, 70, 76), snow=1.0)
        door = c.mask(lambda d: d.rectangle([222, 100, 276, gy], fill=255))
        c.fill(door, (120, 50, 20), bottom=(255, 150, 40), y0=100, y1=gy)
        c.glow_fill(door, (255, 120, 30), 0.6)
        c.lamp(249, 128, 60, (255, 110, 30), 0.8)
        for k in range(6):                                                          # Lichtinstallation (nachts)
            x = 30 + k * 52
            c.lamp(x, 40 + (k % 2) * 30, 40, [(60, 90, 255), (220, 40, 200), (40, 200, 140)][k % 3], 0.32)
        floor = c.mask(lambda d: d.rectangle([0, gy, WIDTH, HEIGHT], fill=255))
        c.fill(floor, (128, 126, 122), _wz_noise(HEIGHT, WIDTH, 16, 7), 0.08, 0.06, bottom=(104, 102, 98), y0=gy,
               y1=HEIGHT, snow=1.0)
        for x0 in (80, 112):                                                        # Gleise
            c.fill(c.mask(lambda d, x0=x0: d.line([(x0, gy), (x0 - 70, HEIGHT)], fill=255, width=2)), (70, 64, 60))
        for k in range(10):
            y = gy + 3 + k * k * 0.9
            c.fill(c.mask(lambda d, y=y: d.line([(80 - (y - gy) * 0.95, y), (112 - (y - gy) * 0.95, y)], fill=255, width=2)),
                   (96, 76, 60))
        for lx in (150, 300):                                                       # Laternen
            c.fill(c.mask(lambda d, lx=lx: d.line([(lx, 92), (lx, gy + 6)], fill=255, width=2)), (50, 50, 56))
            c.fill(c.mask(lambda d, lx=lx: d.rectangle([lx - 4, 88, lx + 4, 94], fill=255)), (220, 220, 200))
            c.lamp(lx, 92, 26, (255, 210, 150), 0.9)
        return self._wz_done(c, gy - 40, flames=[(230, 8, 0.8)])

    # -- 5. Bauernhof -------------------------------------------------------- #
    def _wz_paint_farm(self):
        c = _WzCanvas(45)
        gy = 132
        xs = np.arange(WIDTH)
        hill = 98 + 5 * np.sin(xs * 0.02 + 2)
        fields = (c.ys >= hill[None, :]).astype(np.float32) * (c.ys < gy)
        stripes = ((c.ys - hill[None, :]) // 5 % 3)
        c.fill(fields, (150, 170, 80), shade=0.82 + 0.18 * (stripes == 0) + 0.25 * (stripes == 2) * 0.8, fine=0.05,
               snow=1.0)
        gold = fields * (stripes == 2)
        c.fill(gold * (c.xs > 150), (214, 186, 92), fine=0.08, snow=1.0)
        rng = random.Random(6)
        for _ in range(7):                                                          # Bäume am Horizont
            tx = rng.uniform(150, 320)
            ty = hill[int(min(WIDTH - 1, tx))]
            c.fill(c.mask(lambda d, tx=tx, ty=ty: d.ellipse([tx - 9, ty - 18, tx + 9, ty + 2], fill=255)), (50, 96, 50),
                   fine=0.15, snow=0.5, shade=np.clip(1.2 - (c.xs - tx + 9) / 18 * 0.5, 0.7, 1.2))
        # Scheune
        c.fill(c.mask(lambda d: d.rectangle([24, 70, 136, gy], fill=255)), (164, 42, 34), fine=0.05,
               shade=0.82 + 0.2 * (c.xs.astype(int) % 6 > 0))
        c.fill(c.mask(lambda d: d.polygon([(16, 72), (40, 46), (120, 46), (144, 72)], fill=255)), (70, 70, 76), fine=0.06,
               snow=1.0)
        c.fill(c.mask(lambda d: d.polygon([(40, 46), (60, 30), (100, 30), (120, 46)], fill=255)), (84, 84, 90), snow=1.0)
        door = c.mask(lambda d: d.rectangle([58, 92, 102, gy], fill=255))
        c.fill(door, (150, 36, 30))
        c.fill(c.mask(lambda d: (d.rectangle([58, 92, 102, gy], outline=255, width=3), d.line([(58, 92), (102, gy)], fill=255, width=3),
                                 d.line([(102, 92), (58, gy)], fill=255, width=3))), (240, 236, 226))
        c.fill(c.mask(lambda d: d.rectangle([70, 52, 90, 66], fill=255)), (230, 190, 90), fine=0.3)
        c.lamp(80, 86, 20, (255, 210, 130), 0.9)
        c.fill(c.mask(lambda d: d.rectangle([76, 82, 84, 86], fill=255)), (250, 240, 200))
        # Silo
        c.fill(c.mask(lambda d: (d.rectangle([140, 36, 168, gy], fill=255), d.ellipse([140, 26, 168, 46], fill=255))),
               (170, 172, 176), shade=np.clip(1.25 - (c.xs - 140) / 28 * 0.6, 0.6, 1.3)
               * (1 - 0.08 * ((c.ys.astype(int) % 12) == 0)), snow=0.0)
        # Wohnhaus mit Fachwerk
        c.fill(c.mask(lambda d: d.rectangle([234, 80, 310, gy], fill=255)), (236, 230, 214), fine=0.03)
        c.fill(c.mask(lambda d: (d.rectangle([234, 80, 310, gy], outline=255, width=3), d.line([(234, 106), (310, 106)], fill=255, width=3),
                                 d.line([(234, 80), (262, 106)], fill=255, width=3), d.line([(310, 80), (282, 106)], fill=255, width=3),
                                 d.line([(272, 80), (272, gy)], fill=255, width=3))), (96, 60, 36))
        c.fill(c.mask(lambda d: d.polygon([(226, 82), (318, 82), (272, 48)], fill=255)), (170, 64, 44), fine=0.06, snow=1.0,
               shade=0.9 + 0.12 * ((c.ys.astype(int) % 5) < 3))
        for wx, wy in ((244, 86), (284, 86), (244, 112), (284, 112)):
            m = c.mask(lambda d, wx=wx, wy=wy: d.rectangle([wx, wy, wx + 14, wy + 14], fill=255))
            c.fill(m, (40, 46, 60))
            c.glow_fill(m, (255, 210, 120), 1.0)
            c.lamp(wx + 7, wy + 7, 14, (255, 190, 100), 0.35)
        # Strohballen, Traktor
        for bx in (196, 214):
            c.fill(c.mask(lambda d, bx=bx: d.ellipse([bx - 9, gy - 14, bx + 9, gy + 2], fill=255)), (214, 180, 90),
                   _wz_noise(HEIGHT, WIDTH, 21, 2), 0.15, snow=0.6)
        floor = c.mask(lambda d: d.rectangle([0, gy, WIDTH, HEIGHT], fill=255))
        c.fill(floor, (120, 146, 70), _wz_noise(HEIGHT, WIDTH, 22, 5), 0.14, 0.08, bottom=(104, 130, 58), y0=gy, y1=HEIGHT,
               snow=1.0)
        c.fill(c.mask(lambda d: d.polygon([(70, gy), (96, gy), (150, HEIGHT), (60, HEIGHT)], fill=255)), (150, 124, 88),
               _wz_noise(HEIGHT, WIDTH, 23, 3), 0.12, snow=1.0)
        return self._wz_done(c, gy - 34)

    # -- 6. Wiese am See ----------------------------------------------------- #
    def _wz_paint_lake(self):
        c = _WzCanvas(46)
        h = 108
        xs = np.arange(WIDTH)
        far = 92 + 8 * np.sin(xs * 0.018) + 4 * np.sin(xs * 0.07)
        c.fill(((c.ys >= far[None, :]) & (c.ys < h)).astype(np.float32), (96, 126, 112), fine=0.04, snow=0.9)
        rng = random.Random(8)
        bank = c.mask(lambda d: [d.ellipse([x - 7, h - 12 - rng.uniform(0, 8), x + 7, h + 2], fill=255)
                                 for x in range(-6, WIDTH + 6, 7)])
        c.fill(bank, (44, 84, 54), _wz_noise(HEIGHT, WIDTH, 25, 3), 0.15, snow=0.6)
        c.water_fill(((c.ys >= h) & (c.ys < 152)).astype(np.float32))
        c.lamp(150, h - 4, 6, (255, 220, 150), 0.7)                                 # Licht am anderen Ufer
        c.lamp(196, h - 3, 5, (255, 220, 150), 0.6)
        shore = 152
        meadow = (c.ys >= shore - 2 + 2 * np.sin(c.xs * 0.08)).astype(np.float32)
        c.fill(meadow, (110, 168, 72), _wz_noise(HEIGHT, WIDTH, 26, 4), 0.12, 0.08, bottom=(84, 146, 56), y0=shore,
               y1=HEIGHT, snow=1.0)
        # Steg
        c.fill(c.mask(lambda d: d.polygon([(232, 156), (258, 156), (300, 116), (288, 116)], fill=255)), (140, 104, 70),
               shade=0.85 + 0.2 * ((c.ys.astype(int) % 4) > 0), snow=0.8)
        for px, py in ((236, 160), (256, 160), (290, 120), (300, 120)):
            c.fill(c.mask(lambda d, px=px, py=py: d.rectangle([px - 1, py - 4, px + 1, py + 6], fill=255)), (90, 66, 44))
        c.fill(c.mask(lambda d: d.line([(296, 116), (296, 100)], fill=255, width=2)), (60, 50, 44))
        c.fill(c.mask(lambda d: d.rectangle([292, 94, 300, 102], fill=255)), (230, 220, 180))
        c.lamp(296, 98, 22, (255, 200, 120), 1.0)
        # Weide links
        c.fill(c.mask(lambda d: d.polygon([(26, 160), (40, 160), (38, 90), (30, 90)], fill=255)), (86, 66, 50), fine=0.1)
        crown = c.mask(lambda d: [d.ellipse([20 + k * 9 - 22, 40 + (k % 3) * 8, 20 + k * 9 + 22, 110 + (k % 2) * 12], fill=255)
                                  for k in range(5)])
        c.fill(crown, (70, 120, 60), _wz_noise(HEIGHT, WIDTH, 27, 2), 0.25, snow=0.5,
               shade=np.clip(1.2 - (c.xs - 10) / 90, 0.7, 1.2))
        rng = random.Random(12)                                                     # Schilf
        reeds = c.mask(lambda d: [d.line([(x, 160), (x + rng.uniform(-3, 3), 160 - rng.uniform(16, 30))], fill=255)
                                  for x in range(80, 130, 3)])
        c.fill(reeds, (96, 120, 60))
        rng = random.Random(13)
        c.fill(c.mask(lambda d: [d.ellipse([x - 1, 128 + rng.uniform(0, 8), x + 2, 136 + rng.uniform(0, 8)], fill=255)
                                 for x in range(84, 128, 9)]), (110, 70, 40))
        rng = random.Random(14)
        c.fill(c.mask(lambda d: [d.point((rng.randrange(WIDTH), rng.randrange(shore + 4, HEIGHT)), fill=255)
                                 for _ in range(220)]), (250, 240, 120), snow=None)
        return self._wz_done(c, h, extra={"fireflies": True})

    # -- 7. Alpenlandschaft -------------------------------------------------- #
    def _wz_paint_alps(self):
        c = _WzCanvas(47)
        h = 128
        xs = np.arange(WIDTH, dtype=np.float32)
        rock = _wz_noise(HEIGHT, WIDTH, 31, 4)
        drift = _wz_noise(HEIGHT, WIDTH, 34, 9) + 0.4 * _wz_noise(HEIGHT, WIDTH, 35, 4)
        for peak_x, peak_y, w, col in ((90, 18, 150, (120, 128, 150)), (230, 30, 130, (110, 118, 140)),
                                       (320, 60, 90, (126, 132, 152))):
            ridge = peak_y + np.abs(xs - peak_x) / w * 90 + 6 * np.sin(xs * 0.13) * (np.abs(xs - peak_x) > 6)
            m = ((c.ys >= ridge[None, :]) & (c.ys < h)).astype(np.float32)
            sd = np.where(xs[None, :] > peak_x, 0.72, 1.12)                         # Licht von links
            c.fill(m, col, rock, 0.14, 0.04, shade=sd + 0.06 * rock)
            line = ridge[None, :] + 30 + 16 * drift
            snow = m * np.clip((line - c.ys) / 3.0, 0, 1)                           # weicher Schneerand
            c.fill(snow, (240, 244, 252), shade=np.where(xs[None, :] > peak_x, 0.78, 1.0) + 0.05 * drift)
        slope = 112 + 10 * np.sin(xs * 0.025 + 1)
        c.fill(((c.ys >= slope[None, :])).astype(np.float32), (40, 82, 52), _wz_noise(HEIGHT, WIDTH, 32, 3), 0.15, 0.06,
               snow=0.9)
        rng = random.Random(15)
        self._wz_pines(c, [(x, slope[int(min(WIDTH - 1, max(0, x)))] + 8 + rng.uniform(0, 8), rng.uniform(12, 20))
                           for x in range(-4, WIDTH, 6)], (30, 66, 42), 15, snow=0.7)
        # Dorf mit Kirche
        c.fill(c.mask(lambda d: d.rectangle([196, 112, 212, 136], fill=255)), (240, 236, 226))
        c.fill(c.mask(lambda d: (d.ellipse([197, 98, 211, 112], fill=255), d.line([(204, 92), (204, 98)], fill=255))),
               (70, 90, 70))
        for hx in (170, 220, 236):
            c.fill(c.mask(lambda d, hx=hx: d.rectangle([hx, 124, hx + 12, 136], fill=255)), (236, 226, 206))
            c.fill(c.mask(lambda d, hx=hx: d.polygon([(hx - 2, 124), (hx + 14, 124), (hx + 6, 117)], fill=255)),
                   (120, 70, 50), snow=1.0)
            m = c.mask(lambda d, hx=hx: d.rectangle([hx + 4, 128, hx + 7, 131], fill=255))
            c.glow_fill(m, (255, 210, 120), 1.0)
            c.lamp(hx + 6, 130, 7, (255, 200, 110), 0.5)
        mg = 146
        meadow = (c.ys >= mg + 3 * np.sin(c.xs * 0.05)).astype(np.float32)
        c.fill(meadow, (112, 164, 70), _wz_noise(HEIGHT, WIDTH, 33, 4), 0.12, 0.08, bottom=(90, 144, 56), y0=mg, y1=HEIGHT,
               snow=1.0)
        rng = random.Random(16)
        for _ in range(6):                                                          # Felsbrocken
            x, y = rng.uniform(0, WIDTH), rng.uniform(mg + 6, HEIGHT - 20)
            if 70 < x < 250:
                continue
            c.fill(c.mask(lambda d, x=x, y=y: d.ellipse([x - 8, y - 5, x + 8, y + 4], fill=255)), (140, 140, 146), rock, 0.1,
                   snow=0.8, shade=np.clip(1.2 - (c.ys - y + 5) / 9 * 0.5, 0.6, 1.2))
        rng = random.Random(17)
        c.fill(c.mask(lambda d: [d.point((rng.randrange(WIDTH), rng.randrange(mg + 4, HEIGHT)), fill=255) for _ in range(160)]),
               (60, 90, 230), snow=None)                                                       # Enzian
        rng = random.Random(18)
        c.fill(c.mask(lambda d: [d.point((rng.randrange(WIDTH), rng.randrange(mg + 4, HEIGHT)), fill=255) for _ in range(140)]),
               (250, 250, 250), snow=None)                                                     # Edelweiß
        return self._wz_done(c, h)

    # -- 8. Strand ----------------------------------------------------------- #
    def _wz_paint_beach(self):
        c = _WzCanvas(48)
        h = 106
        c.fill(c.mask(lambda d: d.polygon([(190, h), (214, h - 9), (236, h - 12), (262, h - 6), (280, h)], fill=255)),
               (70, 96, 90), fine=0.05, snow=0.5)                                   # Insel
        c.water_fill(((c.ys >= h) & (c.ys < 150)).astype(np.float32))
        shore = 148
        sand = (c.ys >= shore + 3 * np.sin(c.xs * 0.04)).astype(np.float32)
        c.fill(sand, (220, 196, 146), _wz_noise(HEIGHT, WIDTH, 35, 3), 0.06, 0.06, bottom=(236, 214, 166), y0=shore,
               y1=HEIGHT, snow=1.0)
        wet = sand * (c.ys < shore + 8)
        c.fill(wet, (184, 160, 120), fine=0.05)
        # Strandbar
        c.fill(c.mask(lambda d: d.rectangle([236, 112, 300, 152], fill=255)), (170, 130, 80),
               shade=0.85 + 0.2 * (c.xs.astype(int) % 4 > 0))
        c.fill(c.mask(lambda d: d.polygon([(226, 114), (310, 114), (290, 92), (246, 92)], fill=255)), (200, 170, 100),
               _wz_noise(HEIGHT, WIDTH, 36, 2), 0.2, snow=1.0)
        c.fill(c.mask(lambda d: d.rectangle([232, 130, 304, 134], fill=255)), (130, 90, 56))
        for k in range(8):                                                          # Lichterkette
            x = 232 + k * 10
            y = 116 + 3 * math.sin(k * 0.9)
            col = [(255, 80, 80), (255, 210, 60), (80, 200, 255), (120, 255, 120)][k % 4]
            m = c.mask(lambda d, x=x, y=y: d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=255))
            c.fill(m, (90, 80, 70))
            c.glow_fill(m, col, 1.0)
            c.lamp(x, y, 6, col, 0.6)
        c.lamp(268, 128, 34, (255, 170, 110), 0.5)
        # Palmen
        for px, lean in ((26, 1), (300, -1)):
            pts = [(px + lean * (k ** 1.6) * 0.9, 190 - k * 12) for k in range(10)]
            c.fill(c.mask(lambda d, pts=pts: d.line(pts, fill=255, width=7)), (130, 100, 70),
                   shade=0.85 + 0.25 * ((c.ys.astype(int) % 6) < 3))
            tx, ty = pts[-1]
            fr = c.mask(lambda d, tx=tx, ty=ty: [d.polygon([(tx, ty), (tx + math.cos(a) * 42, ty + math.sin(a) * 18 + 14),
                                                             (tx + math.cos(a + 0.18) * 30, ty + math.sin(a + 0.18) * 12 + 2)],
                                                            fill=255) for a in np.linspace(0.0, 2 * math.pi, 9)[:-1]])
            c.fill(fr, (46, 120, 52), fine=0.15, snow=0.5, shade=np.clip(1.2 - (c.ys - ty + 20) / 50, 0.7, 1.2))
            for k in (-1, 1):
                c.fill(c.mask(lambda d, tx=tx, ty=ty, k=k: d.ellipse([tx + k * 4 - 3, ty, tx + k * 4 + 3, ty + 6], fill=255)),
                       (110, 76, 40))
        return self._wz_done(c, h, extra={"shore": shore})
