"""Automatische Stilwahl (Pseudo-Stil „auto“, Mixin AutoVisual), Albumcover-Farben und Wetter in den Szenen.

Automatisch nach Musik: Nach jedem Liedwechsel (ohne Titel spätestens alle AUTO_SWITCH Sekunden) hört die
Visualisierung AUTO_LISTEN Sekunden zu, schätzt Tempo (Schlagabstand) und Lautstärke und wählt dann einen Stil aus
der passenden Stimmung: ruhig, mittel oder wild (auto_mood). Je Stimmung lässt sich ein fester Stil einstellen.
Coverfarben: Grafikstile bekommen statt der Profilfarbe die kräftigste Farbe des Albumcovers.
Wetter: Draußen-Szenen zeigen das echte Wetter der Wetterseite (Regen, Schnee, Gewitter, Nebel, Wind).
"""
import math
import random

AUTO_POOLS = {"calm": ["campfire", "lights", "ring", "martin", "space", "underwater", "silk", "ember", "pulse"],
              "mid": ["dancer", "farm", "cats", "western", "eq", "oktoberfest", "jazz"],
              "wild": ["metal", "arcade", "carnival", "fireworks", "halloween"]}
AUTO_MOOD_LABEL = {"calm": "ruhig", "mid": "mittel", "wild": "wild"}
AUTO_LISTEN = 6.0
AUTO_SWITCH = 240.0
COVER_STYLES = ("eq", "ring", "vu", "spectro", "scope", "lights", "fireworks")
WEATHER_FX_STYLES = ("easter", "halloween", "father", "newyear", "carnival", "martin", "farm", "cats", "campfire")


def auto_mood(bpm, level):
    """Stimmung aus Tempo (Schläge/min oder None) und mittlerer Lautstärke 0…1: calm, mid oder wild."""
    if level < 0.22 or (bpm is not None and bpm < 95):
        return "calm"
    if bpm is not None and bpm >= 125 and level >= 0.45:
        return "wild"
    if bpm is None and level >= 0.7:
        return "wild"
    return "mid"


def cover_color(img):
    """Kräftigste, häufige Farbe eines Bildes (für Grafikstile), auf volle Helligkeit gezogen."""
    import colorsys
    arr = np.asarray(img.convert("RGB"))                # ohne resize (Kubuntu-Pillow, siehe _disp_grad)
    sy, sx = max(1, arr.shape[0] // 24), max(1, arr.shape[1] // 24)
    small = (arr[::sy, ::sx] // 16 * 16 + 8).reshape(-1, 3)
    cols, counts = np.unique(small, axis=0, return_counts=True)
    best, score = (255, 255, 255), -1.0
    for count, (r, g_, b) in zip(counts.tolist(), cols.tolist()):
        h, s, v = colorsys.rgb_to_hsv(r / 255, g_ / 255, b / 255)
        sc = count * (0.15 + s) * (0.25 + v)
        if sc > score:
            best, score = (h, max(0.55, s), 1.0), sc
    if score < 0:
        return (255, 255, 255)
    r, g_, b = colorsys.hsv_to_rgb(*best)
    return (int(r * 255), int(g_ * 255), int(b * 255))


class AutoVisual:
    vis_auto_inner = None               # gerade gewählter Stil (für Tastatur und Anzeige)

    def _vis_auto_pick(self, s, o):
        t = s["t"]
        st = self.__dict__.get("_auto")
        song = self.__dict__.get("_vis_song", "")
        if st is None:
            st = self._auto = {"song": song, "since": t, "lvl": 0.0, "per": [], "n": 0, "style": None, "mood": None,
                               "label_t": -99.0, "rng": random.Random(201)}
        if song != st["song"] or t - st["since"] > AUTO_SWITCH:
            st.update(song=song, since=t, lvl=0.0, per=[], n=0, decided=False)
        if s.get("active") and not s.get("talk"):
            st["n"] += 1
            st["lvl"] += (s["level"] - st["lvl"]) / min(st["n"], 30)
            if s.get("period"):
                st["per"].append(s["period"])
        if st["style"] is None or (not st.get("decided") and t - st["since"] >= AUTO_LISTEN):
            per = sorted(st["per"])[len(st["per"]) // 2] if st["per"] else None
            bpm = 60.0 / per if per else None
            mood = auto_mood(bpm, st["lvl"]) if st["n"] else "mid"
            want = o.get(mood, "mix")
            if want in VISUAL_RENDERERS and want != "auto":
                style = want
            else:
                pool = [x for x in AUTO_POOLS[mood] if x in VISUAL_RENDERERS and x != st["style"]]
                style = st["rng"].choice(pool) if pool else "eq"
            if style != st["style"]:
                st["label_t"] = t
            st.update(style=style, mood=mood, decided=t - st["since"] >= AUTO_LISTEN)  # erste Wahl nur vorläufig
        self.vis_auto_inner = st["style"]
        return st["style"], st["mood"], t - st["label_t"]

    @vis_style("auto")
    def vis_auto(self, s, o, color):
        inner, mood, since = self._vis_auto_pick(s, o)
        img = VISUAL_RENDERERS[inner](self, s, visual_options(self.settings, inner), color)
        if o.get("label", True) and since < 4.0:
            d = ImageDraw.Draw(img)
            text = f"Automatisch: {VISUAL_STYLES.get(inner, inner)} ({AUTO_MOOD_LABEL.get(mood, mood)})"
            w = d.textlength(text, font=self.f_tiny) + 14
            d.rounded_rectangle([(WIDTH - w) / 2, VIS_H - 22, (WIDTH + w) / 2, VIS_H - 6], radius=6,
                                fill=(20, 24, 34), outline=(90, 100, 120))
            d.text(((WIDTH - w) / 2 + 7, VIS_H - 21), text, font=self.f_tiny, fill=(225, 230, 240))
        return img

    # -- Albumcover-Farbe --------------------------------------------------------------- #
    def _vis_cover_color(self):
        cover = self.media.snapshot()[1] if self.media is not None else None
        if cover is None:
            return None
        cached = self.__dict__.get("_cover_col")
        if cached and cached[0] is cover:
            return cached[1]
        col = cover_color(cover)
        self._cover_col = (cover, col)
        return col

    # -- Wetter in den Szenen -------------------------------------------------------------- #
    def _vis_weather_fx(self, img, t):
        kind, temp, wind = self._party_weather()
        if kind not in ("rain", "drizzle", "snow", "thunder", "fog"):
            return img
        st = self.__dict__.get("_wfx")
        if st is None or st.get("kind") != kind:
            rng = random.Random(211)
            n = {"rain": 70, "drizzle": 30, "snow": 60, "thunder": 90, "fog": 0}[kind]
            st = self._wfx = {"kind": kind, "t": t, "p": [[rng.uniform(0, WIDTH), rng.uniform(0, VIS_H),
                                                            rng.uniform(0.6, 1.0)] for _ in range(n)],
                              "rng": rng, "flash": -99.0}
        dt = max(0.0, min(0.2, t - st["t"]))
        st["t"] = t
        slant = max(-1.0, min(1.0, (wind or 0) / 40.0))
        if kind != "fog":                                                           # trüber Himmel
            gray = Image.new("RGB", (WIDTH, VIS_H), (90, 96, 110))
            top = img.crop((0, 0, WIDTH, VIS_H))
            img.paste(Image.blend(top, gray, {"drizzle": 0.15, "snow": 0.2}.get(kind, 0.3)), (0, 0))
        d = ImageDraw.Draw(img)
        if kind == "fog":
            haze = Image.new("L", img.size, 0)
            hd = ImageDraw.Draw(haze)
            for y in range(0, VIS_H, 4):
                hd.rectangle([0, y, WIDTH, y + 4], fill=int(40 + 80 * y / VIS_H))
            img.paste((200, 205, 215), (0, 0), haze)
            return img
        snow = kind == "snow"
        for p in st["p"]:
            sp = (38 if snow else 260) * p[2]
            p[1] += sp * dt
            p[0] += (slant * (40 if snow else 120) + (math.sin(t + p[2] * 9) * 12 if snow else 0)) * dt * p[2]
            if p[1] > VIS_H:
                p[1] -= VIS_H
                p[0] = st["rng"].uniform(-40, WIDTH + 40)
            p[0] = (p[0] + 60) % (WIDTH + 120) - 60
            if snow:
                r = 1.0 + p[2]
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(245, 245, 255))
            else:
                ln = 6 + 6 * p[2]
                d.line([(p[0], p[1]), (p[0] - slant * ln * 0.5, p[1] - ln)], fill=(170, 190, 230))
        if kind == "thunder":
            if t - st["flash"] > 7 and st["rng"].random() < dt / 3:
                st["flash"] = t
            k = t - st["flash"]
            if k < 0.25:
                img = Image.blend(img, Image.new("RGB", img.size, (240, 240, 255)), 0.55 * (1 - k / 0.25))
        return img
