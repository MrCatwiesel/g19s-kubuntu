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


# Tanzposen: Oberarm/Unterarm links und rechts, Oberschenkel/Unterschenkel links und rechts,
# Neigung des Oberkörpers, Neigung des Kopfes (Winkel wie _vec, absolut)
DANCE_POSES = [
    (-130, -145, 130, 145, -14, -6, 14, 6, 0, 0),         # Arme hoch (V)
    (-40, 40, 145, 150, -20, 0, 15, 25, 6, -8),           # Disco: rechts nach oben zeigen, links Hand an der Hüfte
    (-95, -70, 95, 70, -8, -8, 25, -10, -4, 6),           # Arme zur Seite, Knie angewinkelt
    (-35, 35, 35, -35, -5, -5, 30, -10, 0, 10),           # Hände an den Hüften
    (-120, -150, 60, 100, -6, -6, 80, 95, -8, -6),        # Kick nach rechts
    (-155, 160, 155, -160, -15, -15, 15, 15, 0, 0),       # Klatschen über dem Kopf
    (-100, -130, 80, 50, -10, 5, 10, -5, 4, 8),           # Welle
    (-60, -120, 60, 120, -25, -5, 10, 30, -6, -10),       # Twist
]


# Langeweile bei Wortbeiträgen (gleicher Aufbau wie DANCE_POSES): Arme verschränkt, Hände an den Hüften,
# gähnen (Hand vor dem Mund), auf die Uhr schauen, auf dem Bühnenrand sitzen
BORED_POSES = {
    "cross": (-20, 95, 20, -95, -6, -4, 10, 6, 0, 8),
    "hips": (-35, 35, 35, -35, -6, -4, 14, 4, 3, -6),
    "yawn": (-20, 95, 125, -92, -6, -4, 10, 6, -3, -12),
    "watch": (-70, 60, 35, -35, -6, -4, 12, 4, 2, 14),
    "sit": (-15, 40, 15, -40, -18, 0, 18, 0, 4, 15),
}
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
            if last and last[0] == style and last[1] == profile:
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

    # -- 2. Tanzendes Mädchen ------------------------------------------------- #
    @vis_style("dancer")
    def vis_dancer(self, s, o, color):
        S = 2                                               # doppelt zeichnen, dann verkleinern (glatte Kanten)
        W, H = WIDTH * S, HEIGHT * S
        t = s["t"]
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        moving = s.get("active") or (s.get("demo") and not s.get("idle"))
        st = self._vstate("dancer", lambda: {"from": DANCE_POSES[0], "to": DANCE_POSES[0], "t0": t,
                                              "beats": s["beats"], "k": 0})

        def step():                                         # nächste Pose (schnell überblendet)
            st["k"] += 1
            k = st["k"]
            st.update({"from": self._dance_pose(st, t), "to": DANCE_POSES[(k * 3 + k // 4) % len(DANCE_POSES)], "t0": t})

        bored = _bored_pose(t - s.get("talk_t", t)) if s.get("talk") else None
        thigh = 34
        floor = (VIS_H - 26) * S
        if bored:                                           # Wortbeitrag: gelangweilt
            if st.get("bored") != bored:
                st.update({"from": self._dance_pose(st, t), "to": BORED_POSES[bored], "t0": t, "bored": bored, "dur": 0.6})
            st["beats"] = s["beats"]
            pose = list(self._dance_pose(st, t))
            pose[8] += math.sin(t * 0.7) * 3                # langsames Gewichtverlagern
            if bored != "sit":
                pose[7] += max(0.0, math.sin(t * 2 * math.pi * 1.4)) * 14     # Fuß tippt ungeduldig
                hip = (WIDTH / 2 * S + math.sin(t * 0.7) * 5 * S, floor - 72 * S)
            else:                                           # sitzt auf dem Bühnenrand, Beine baumeln
                thigh = 12
                pose[5] += math.sin(t * 1.3) * 10
                pose[7] -= math.sin(t * 1.3 + 1) * 10
                hip = (WIDTH / 2 * S, floor - 14 * S)
            energy = 0.0
        else:
            if st.pop("bored", None):                       # Musik ist zurück: aufspringen
                st["dur"] = 0.15
                step()
            if s["beats"] != st["beats"]:
                st["beats"] = s["beats"]
                step()
            elif moving and t - st["t0"] > period * 1.6:
                step()                                      # Schlag nicht erkannt: im Tempo weitertanzen
            energy = 0.35 + 0.65 * s["level"] if moving else 0.25
            phase = ((t - st["t0"]) / period) % 1.0         # 0 = Schlag, 1 = nächster Schlag
            pose = list(self._dance_pose(st, t))
            wig = math.sin(2 * math.pi * phase * 2) * (20 + 30 * (s["mid"] + s["treble"])) * energy
            pose[1] += wig                                  # Unterarme schwingen im Takt
            pose[3] -= wig
            sway = math.sin(math.pi * (st["k"] + phase))    # Gewicht wechselt bei jedem Schlag die Seite
            pose[8] += sway * 9 * energy
            pose[9] += math.sin(2 * math.pi * phase) * 12 * energy
            dip = (1 + math.cos(2 * math.pi * phase)) / 2 * (4 + 12 * energy)   # in die Knie auf dem Schlag
            hip = (WIDTH / 2 * S + sway * 14 * energy * S, floor - 72 * S + dip * S)
        body = tuple(o["color"]) if o.get("color") else color
        stage = self._dance_stage(s, o, dim=bool(bored))
        fig = Image.new("RGBA", (W, H), body + (0,))       # nur die Figur doppelt groß, dann verkleinert
        d = ImageDraw.Draw(fig)
        body = body + (255,)
        lu, lf, ru, rf, lt, ls, rt, rs, lean, head = pose

        def at(p, ang, length):
            dx, dy = _vec(ang, length * S)
            return p[0] + dx, p[1] + dy

        def limb(a, b, w):
            d.line([a, b], fill=body, width=int(w * S))
            r = w * S / 2
            d.ellipse([b[0] - r, b[1] - r, b[0] + r, b[1] + r], fill=body)

        neck = at(hip, 180 - lean, 52)
        if bored != "sit":                                  # Schatten direkt auf die Bühne
            hx, fy = hip[0] / S, floor / S
            ImageDraw.Draw(stage).ellipse([hx - 60, fy - 5, hx + 60, fy + 7], fill=(12, 10, 18))
        for side, (t_ang, s_ang) in ((-1, (lt, ls)), (1, (rt, rs))):           # Beine
            hj = (hip[0] + side * 8 * S, hip[1])
            knee = at(hj, t_ang, thigh)
            foot = at(knee, s_ang, 34)
            limb(hj, knee, 9)
            limb(knee, foot, 8)
            d.line([foot, (foot[0] + side * 7 * S, foot[1] + 1 * S)], fill=body, width=5 * S)
        flare = 1 + s["level"] * 0.45 * (0 if bored else 1)  # Rock schwingt mit der Lautstärke
        waist = at(hip, 180 - lean, 16)
        hem_y = hip[1] + 14 * S
        d.polygon([(waist[0] - 8 * S, waist[1]), (waist[0] + 8 * S, waist[1]),
                   (hip[0] + 24 * S * flare, hem_y), (hip[0] - 24 * S * flare, hem_y)], fill=body)
        sl = at(neck, 180 - lean - 90, 13)
        sr = at(neck, 180 - lean + 90, 13)
        d.polygon([sl, sr, (waist[0] + 8 * S, waist[1]), (waist[0] - 8 * S, waist[1])], fill=body)
        for sh, (u, f) in ((sl, (lu, lf)), (sr, (ru, rf))):                     # Arme
            elbow = at(sh, u, 27)
            hand = at(elbow, f, 25)
            limb(sh, elbow, 7)
            limb(elbow, hand, 6)
        hc = at(neck, 180 - lean - head, 17)
        d.line([neck, hc], fill=body, width=7 * S)
        r = 13 * S
        d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=body)
        tail = (175 + math.sin(t * 1.2) * 4 if bored else
                150 + math.sin(t * 5.5) * 18 + s["bass"] * 25) - lean           # Pferdeschwanz schwingt
        base = at(hc, -125 - head, 11)
        tip = at(base, tail + 180, 26)
        mid = at(base, tail + 165, 14)
        d.polygon([at(base, tail + 90, 5), mid, tip, at(base, tail - 90, 5)], fill=body)
        if bored in ("yawn", "sit"):
            self._dance_bubble(d, hc, S, "Gähn …" if bored == "yawn" else None, t)
        small = fig.reduce(S)
        stage.paste(small, (0, 0), small)
        return stage

    def _dance_bubble(self, d, head, S, text, t):
        """Sprechblase „Gähn …“ bzw. aufsteigende „Z“ neben dem Kopf."""
        font = self.__dict__.setdefault("_bubble_font", load_font(14 * S, bold=True))
        x, y = head[0] + 22 * S, head[1] - 38 * S
        if text:
            w = d.textlength(text, font=font)
            d.rounded_rectangle([x, y, x + w + 16 * S, y + 24 * S], radius=10 * S, fill=(235, 235, 245, 255))
            d.polygon([(x + 8 * S, y + 22 * S), (x + 18 * S, y + 22 * S), (x, y + 34 * S)], fill=(235, 235, 245, 255))
            d.text((x + 8 * S, y + 4 * S), text, font=font, fill=(40, 40, 60, 255))
            return
        for i in range(3):                                  # Zzz steigen auf und verblassen
            k = (t * 0.5 + i / 3) % 1.0
            v = int(220 * (1 - k))
            size = int((10 + 6 * i) * S)
            f = self.__dict__.setdefault(f"_z_font{size}", load_font(size, bold=True))
            d.text((x + (k * 18 + i * 10) * S, y - k * 40 * S + 20 * S), "Z", font=f, fill=(v, v, min(255, v + 30), 255))

    def _dance_pose(self, st, t):
        k = _smooth((t - st["t0"]) / st.get("dur", 0.15))
        return tuple(a + (b - a) * k for a, b in zip(st["from"], st["to"]))

    def _dance_stage(self, s, o, dim=False):
        """Bühne in Displaygröße: Verlauf, Boden, zwei Lichtkegel in wechselnden Farben (dim: Wortbeitrag,
        Licht gedimmt). Nur Bildoperationen in C – kostet weniger als 1 ms."""
        bg = self.__dict__.get("_dance_bg")
        if bg is None:
            ys = np.linspace(0, 1, HEIGHT)[:, None, None]
            top, bot = np.array([26, 10, 40], np.float32), np.array([4, 3, 8], np.float32)
            arr = np.broadcast_to(top * (1 - ys) + bot * ys, (HEIGHT, WIDTH, 3)).copy()
            floor = VIS_H - 26
            arr[floor:, :] = np.array([18, 14, 26], np.float32) * np.linspace(1, 0.4, HEIGHT - floor)[:, None, None]
            bg = self._dance_bg = Image.fromarray(arr.astype(np.uint8), "RGB")
        img = bg.copy()
        if o["stage"]:
            hue = (s["beats"] % 6) / 6
            bright = 0.08 if dim else 0.25 + 0.5 * s["bass"]
            for i, x in enumerate((0.18, 0.82)):
                mask = Image.new("L", (WIDTH, HEIGHT), 0)
                cx = WIDTH / 2 + math.sin(s["t"] * 0.8 + i * 2.1) * 30
                ImageDraw.Draw(mask).polygon([(x * WIDTH - 6, 0), (x * WIDTH + 6, 0), (cx + 70, VIS_H - 22),
                                              (cx - 70, VIS_H - 22)], fill=int(120 * bright))
                img.paste(_hue(hue + i * 0.33, 0.8, 1.0), (0, 0, WIDTH, HEIGHT), mask)
            floor = VIS_H - 26
            spot = Image.new("L", (WIDTH, HEIGHT), 0)
            ImageDraw.Draw(spot).ellipse([WIDTH / 2 - 80, floor - 6, WIDTH / 2 + 80, floor + 14], fill=int(90 * bright + 40))
            img.paste(_hue(hue, 0.4, 1.0), (0, 0, WIDTH, HEIGHT), spot)
        return img

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
    """MENU (wie SETTINGS kurz) öffnet die Auswahl des Stils; sonst blättern die Pfeiltasten."""
    if pressed & LKEY_BITS["MENU"]:
        app.menu = VisualMenu(app)
        app.flash = None
        app.next_draw = 0
        return True
    return False
