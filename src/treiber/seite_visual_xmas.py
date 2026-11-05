"""Visualisierung „Weihnachten“: Weihnachtsmann und Weihnachtsfrau tanzen (einzeln oder als Paar) neben einem
Weihnachtsbaum im Schneefall. Die Figuren bestehen aus räumlich schattierten Körperteilen (Ellipsoide mit Licht
von links oben, Glanzpunkt und Schatten) – so wirken sie plastisch, ohne echte 3D-Grafik. Arme und Beine
werden über Zielpunkte für Hände und Füße gesetzt (zweigliedrige inverse Kinematik).
Bei Wortbeiträgen gehen beide zu einer Bank: er liest die Wunschliste, sie trinkt Kakao. Wechselt der Tanz
(Paar, er allein, sie allein), verabschiedet sich, wer gehen soll, winkt und geht aus dem Bild (er nach links,
sie nach rechts); wer dazukommt, geht herein. Beim Öffnen der Seite kommen beide ins Bild gelaufen.
"""
import math
import random

XMAS_LIGHT = np.array([-0.45, -0.65, 0.62]) / np.linalg.norm([-0.45, -0.65, 0.62])
XMAS_HALF = (XMAS_LIGHT + np.array([0, 0, 1.0])) / np.linalg.norm(XMAS_LIGHT + np.array([0, 0, 1.0]))
XMAS_FLOOR = VIS_H - 30                 # Höhe des Schneebodens unter den Füßen
XMAS_RED, XMAS_FUR, XMAS_SKIN = (205, 24, 30), (246, 246, 250), (246, 204, 176)
XMAS_TREE_X = 58
XMAS_BENCH_X = 196
XMAS_WALK_SPEED = 70                    # Gehen ins Bild und hinaus (Pixel je Sekunde)
XMAS_OFF_MARGIN = 48
XMAS_OFF = {"santa": -XMAS_OFF_MARGIN, "mrs": WIDTH + XMAS_OFF_MARGIN}   # er geht links, sie rechts hinaus

# Posen: Hände relativ zur jeweiligen Schulter, Füße relativ zum Hüftgelenk (Pixel), Neigung, Kopf, Wippen
SANTA_POSES = [
    {"lh": (14, 22), "rh": (-14, 22), "lf": (-2, 40), "rf": (2, 40), "lean": 0, "head": 4},     # Hände am Bauch
    {"lh": (-10, -32), "rh": (10, -32), "lf": (-6, 39), "rf": (6, 39), "lean": 0, "head": -6},  # Arme hoch
    {"lh": (10, 24), "rh": (22, -26), "lf": (-4, 40), "rf": (8, 36), "lean": 4, "head": 8},     # winken
    {"lh": (-30, 6), "rh": (30, 6), "lf": (-12, 38), "rf": (12, 38), "lean": -4, "head": -4},   # Arme aus, Grätsche
    {"lh": (-26, -10), "rh": (26, 2), "lf": (-2, 40), "rf": (20, 26), "lean": -6, "head": 6},   # Kick
    {"lh": (8, 34), "rh": (-8, 34), "lf": (-6, 39), "rf": (10, 34), "lean": 5, "head": -8},     # Hände an die Hüften
]
MRS_POSES = [
    {"lh": (14, -34), "rh": (-14, -34), "lf": (-2, 22), "rf": (2, 22), "lean": 0, "head": 0},   # Arme über dem Kopf
    {"lh": (-8, 30), "rh": (8, 30), "lf": (-4, 22), "rf": (5, 20), "lean": 3, "head": 8},       # Rock fassen
    {"lh": (-24, 10), "rh": (10, -34), "lf": (-3, 22), "rf": (4, 21), "lean": -4, "head": -8},  # ein Arm hoch
    {"lh": (18, 8), "rh": (-18, 8), "lf": (-2, 22), "rf": (3, 22), "lean": 0, "head": 6},       # klatschen
    {"lh": (-28, -4), "rh": (28, -4), "lf": (-5, 21), "rf": (5, 21), "lean": 5, "head": -6},    # Arme aus
]
XMAS_LIGHT_COLORS = [(255, 60, 50), (255, 210, 60), (70, 160, 255), (60, 230, 110), (255, 120, 220)]


def _ik(shoulder, target, l1, l2, bend):
    """Zweigliedriger Arm/Bein: Ellbogen bzw. Knie und Endpunkt, Ziel notfalls auf Reichweite gekürzt.
    bend = +1/−1 wählt, zu welcher Seite das Gelenk knickt."""
    dx, dy = target[0] - shoulder[0], target[1] - shoulder[1]
    d = max(1e-3, min(l1 + l2 - 0.01, math.hypot(dx, dy)))
    base = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    a = base + bend * math.acos(cos_a)
    elbow = (shoulder[0] + math.cos(a) * l1, shoulder[1] + math.sin(a) * l1)
    end = (shoulder[0] + math.cos(base) * d, shoulder[1] + math.sin(base) * d)
    return elbow, end


def _mix_pose(a, b, k):
    out = {}
    for key, va in a.items():
        vb = b.get(key, va)
        out[key] = tuple(x + (y - x) * k for x, y in zip(va, vb)) if isinstance(va, tuple) else va + (vb - va) * k
    return out


def _mix_pose_spin(a, b, k):
    """Wie _mix_pose; eine Drehung über ±180° (Ende einer Pirouette) wird nicht zurückgespult."""
    out = _mix_pose(a, b, k)
    if abs(b["spin"] - a["spin"]) > 180:
        out["spin"] = b["spin"]
    return out


class XmasVisual:
    # -- Räumlich schattierte Körperteile ------------------------------------ #
    def _blob_sprite(self, w, h, ang, color, gloss, alpha_k=1.0, flat=False):
        """Ellipse w×h (Pixel), um ang Grad gedreht, als beleuchtetes Ellipsoid (RGBA, zwischengespeichert).
        flat: ohne Licht, nach außen weich auslaufend (Lichtschein)."""
        key = (int(round(w)), int(round(h)), int(round(ang / 6)) * 6 if abs(w - h) > 1 else 0, color, gloss,
               round(alpha_k, 2), flat)
        cache = self.__dict__.setdefault("_blob_cache", {})
        hit = cache.get(key)
        if hit is not None:
            return hit
        if len(cache) > 2500:
            cache.clear()
        a, b = max(1.0, key[0] / 2), max(1.0, key[1] / 2)
        R = int(math.ceil(max(a, b))) + 2
        ys, xs = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        c, s = math.cos(math.radians(key[2])), math.sin(math.radians(key[2]))
        u, v = (xs * c + ys * s) / a, (-xs * s + ys * c) / b
        r = np.sqrt(u * u + v * v)
        alpha = (np.clip(1 - r, 0, 1) ** 1.5 if flat else np.clip((1 - r) * min(a, b) + 0.5, 0, 1)) * alpha_k
        z = np.sqrt(np.clip(1 - r * r, 0, 1))
        nx, ny = u * c - v * s, u * s + v * c
        norm = np.sqrt(nx * nx + ny * ny + z * z) + 1e-6
        nx, ny, nz = nx / norm, ny / norm, z / norm
        diff = np.clip(nx * XMAS_LIGHT[0] + ny * XMAS_LIGHT[1] + nz * XMAS_LIGHT[2], 0, 1)
        spec = np.clip(nx * XMAS_HALF[0] + ny * XMAS_HALF[1] + nz * XMAS_HALF[2], 0, 1) ** 22 * gloss
        light = np.ones_like(diff) if flat else 0.3 + 0.8 * diff
        rgb = np.array(color, np.float32)[None, None, :] * light[..., None] + (0 * spec if flat else 230 * spec)[..., None]
        rgba = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")
        cache[key] = (img, R)
        return cache[key]

    def _blob(self, img, cx, cy, w, h, color, ang=0.0, gloss=0.5, alpha=1.0, flat=False):
        spr, R = self._blob_sprite(w, h, ang, color, gloss, alpha, flat)
        img.paste(spr, (int(round(cx)) - R, int(round(cy)) - R), spr)

    def _limb(self, img, p1, p2, thick, color, gloss=0.35):
        """Glied von p1 nach p2 als längliches Ellipsoid."""
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        self._blob(img, (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, math.hypot(dx, dy) + thick, thick, color,
                   math.degrees(math.atan2(dy, dx)), gloss)

    # -- Figuren ------------------------------------------------------------- #
    def _santa(self, img, d, x, floor, pose, t, sitting=False, scroll=False):
        """Weihnachtsmann: roter Mantel mit Fell, Gürtel, Stiefel, Bart, Mütze mit Bommel."""
        hip = (x, floor - (22 if sitting else 44) + pose.get("bob", 0))
        self._blob(img, x, floor + 2, 62, 10, (150, 165, 190), gloss=0)              # Schatten
        for side in (-1, 1):                                                        # Beine
            hj = (hip[0] + side * 9, hip[1] + 4)
            if sitting:
                knee, foot = (hj[0] + side * 3, hj[1] + 6), (hj[0] + side * 4, floor - 2)
            else:
                f = pose["lf" if side < 0 else "rf"]
                knee, foot = _ik(hj, (hj[0] + f[0], hj[1] + f[1]), 20, 21, -side)
            self._limb(img, hj, knee, 15, XMAS_RED)
            self._limb(img, knee, foot, 13, XMAS_RED)
            self._blob(img, foot[0] + side * 4, foot[1] + 1, 19, 11, (34, 26, 24), gloss=0.9)  # Stiefel
        lean = pose.get("lean", 0)
        body = (hip[0] + math.sin(math.radians(lean)) * 22, hip[1] - 22)
        self._blob(img, body[0], body[1], 52, 54, XMAS_RED, gloss=0.4)              # Bauch
        self._blob(img, hip[0], hip[1] + 2, 54, 11, XMAS_FUR, gloss=0.1)            # Fellsaum
        self._blob(img, body[0], body[1] + 8, 50, 9, (30, 24, 22), gloss=0.7)       # Gürtel
        self._blob(img, body[0], body[1] + 8, 11, 10, (240, 196, 60), gloss=1.2)    # Schnalle
        self._blob(img, body[0], body[1] - 6, 9, 32, XMAS_FUR, gloss=0.1)           # Fellstreifen
        neck = (body[0] + math.sin(math.radians(lean)) * 22, body[1] - 22)
        hands = []
        for side in (-1, 1):                                                        # Arme
            sh = (neck[0] + side * 21, neck[1] + 6)
            h = pose["lh" if side < 0 else "rh"]
            elbow, hand = _ik(sh, (sh[0] + h[0], sh[1] + h[1]), 18, 18, side)
            self._limb(img, sh, elbow, 13, XMAS_RED)
            self._limb(img, elbow, hand, 12, XMAS_RED)
            self._blob(img, hand[0], hand[1], 12, 12, XMAS_FUR, gloss=0.2)          # Ärmelfell
            self._blob(img, hand[0] + (hand[0] - elbow[0]) * 0.25, hand[1] + (hand[1] - elbow[1]) * 0.25,
                       10, 10, (240, 240, 244), gloss=0.3)                          # Handschuh
            hands.append(hand)
        if scroll:                                                                  # Wunschliste
            (x1, y1), (x2, y2) = hands
            d.polygon([(x1, y1), (x2, y2), (x2 + 2, floor + 4), (x1 - 2, floor + 4)], fill=(244, 236, 214))
            for k in range(5):
                yy = min(y1, y2) + 6 + k * 6
                d.line([(min(x1, x2) + 3, yy), (max(x1, x2) - 3 - (k % 3) * 3, yy)], fill=(120, 110, 140))
        hd = pose.get("head", 0)
        head = (neck[0] + math.sin(math.radians(lean + hd)) * 14, neck[1] - 13)
        self._blob(img, head[0], head[1], 28, 28, XMAS_SKIN, gloss=0.3)             # Kopf
        self._blob(img, head[0], head[1] + 11, 32, 26, XMAS_FUR, gloss=0.15)        # Bart
        for side in (-1, 1):
            self._blob(img, head[0] + side * 5, head[1] + 3, 12, 6, XMAS_FUR, gloss=0.2)   # Schnurrbart
            d.ellipse([head[0] + side * 5 - 2, head[1] - 5, head[0] + side * 5 + 2, head[1] - 1], fill=(30, 30, 40))
            d.line([(head[0] + side * 3, head[1] - 8), (head[0] + side * 8, head[1] - 9)], fill=XMAS_FUR, width=2)
        self._blob(img, head[0], head[1] + 0, 7, 6, (226, 110, 100), gloss=0.8)    # Nase
        tip_ang = math.radians(-60 + math.sin(t * 3.0) * 25 + hd)                   # Mütze, Spitze schwingt
        base_l, base_r = (head[0] - 14, head[1] - 9), (head[0] + 14, head[1] - 9)
        tip = (head[0] + math.cos(tip_ang) * 30, head[1] - 12 + math.sin(tip_ang) * 30)
        d.polygon([base_l, base_r, tip], fill=XMAS_RED)
        d.polygon([(head[0], head[1] - 10), base_r, tip], fill=(165, 16, 24))
        self._blob(img, head[0], head[1] - 9, 32, 10, XMAS_FUR, gloss=0.1)          # Fellrand
        self._blob(img, tip[0], tip[1], 10, 10, XMAS_FUR, gloss=0.2)                # Bommel
        return hands

    def _mrs(self, img, d, x, floor, pose, t, spin=0.0, sitting=False, mug=False):
        """Weihnachtsfrau: rotes Kleid mit weißer Schürze und Fellsaum, silbernes Haar mit Knoten, Brille.
        spin = Drehung um die eigene Achse (Grad); von hinten sieht man nur Haar und Kleid."""
        sx = math.cos(math.radians(spin))
        front = sx >= 0
        w = max(0.35, abs(sx))
        hip = (x, floor - (20 if sitting else 40) + pose.get("bob", 0))
        self._blob(img, x, floor + 2, 54, 9, (150, 165, 190), gloss=0)              # Schatten
        for side in (-1, 1):                                                        # Unterschenkel
            if sitting:
                knee, foot = (hip[0] + side * 7, hip[1] + 6), (hip[0] + side * 8, floor - 2)
            else:
                f = pose["lf" if side < 0 else "rf"]
                knee = (hip[0] + side * 7 * w, hip[1] + 14)
                foot = (knee[0] + f[0] * w * 0.4, knee[1] + f[1])
            self._limb(img, knee, foot, 9, (60, 50, 60))
            self._blob(img, foot[0] + side * 3, foot[1] + 1, 14, 8, (180, 20, 26), gloss=1.0)   # Schuh
        flare = 1 + 0.25 * abs(math.sin(math.radians(spin)))                        # Rock schwingt beim Drehen
        self._blob(img, hip[0], hip[1] + 6, 58 * flare * (w * 0.6 + 0.4), 40, XMAS_RED, gloss=0.35)
        self._blob(img, hip[0], hip[1] + 24, 60 * flare * (w * 0.6 + 0.4), 9, XMAS_FUR, gloss=0.1)
        lean = pose.get("lean", 0)
        body = (hip[0] + math.sin(math.radians(lean)) * 18, hip[1] - 18)
        if front:                                                                   # Schürze auf dem Rock
            self._blob(img, hip[0], hip[1] + 8, 26 * w, 30, (248, 244, 236), gloss=0)
        self._blob(img, body[0], body[1], 32 * w + 4, 38, XMAS_RED, gloss=0.4)
        if front:
            self._blob(img, body[0], body[1] - 14, 20 * w + 2, 8, XMAS_FUR, gloss=0)  # Kragen
        neck = (body[0] + math.sin(math.radians(lean)) * 18, body[1] - 17)
        hands = []
        for side in (-1, 1):
            sh = (neck[0] + side * 14 * w, neck[1] + 5)
            h = pose["lh" if side < 0 else "rh"]
            elbow, hand = _ik(sh, (sh[0] + h[0], sh[1] + h[1]), 15, 15, side)
            self._limb(img, sh, elbow, 9, XMAS_RED)
            self._limb(img, elbow, hand, 8, XMAS_RED)
            self._blob(img, hand[0], hand[1], 8, 8, XMAS_SKIN, gloss=0.3)
            hands.append(hand)
        if mug:                                                                     # Kakao mit Dampf
            mx, my = (hands[0][0] + hands[1][0]) / 2, (hands[0][1] + hands[1][1]) / 2 - 4
            self._blob(img, mx, my, 12, 13, (250, 250, 250), gloss=0.8)
            self._blob(img, mx, my - 2, 8, 6, (230, 40, 40), gloss=0.4)
            for k in range(3):
                pts = [(mx - 3 + k * 3 + math.sin(t * 3 + yy * 0.3 + k) * 2, my - 8 - yy) for yy in range(0, 18, 2)]
                d.line(pts, fill=(200, 205, 220), width=1)
        hd = pose.get("head", 0)
        head = (neck[0] + math.sin(math.radians(lean + hd)) * 12, neck[1] - 11)
        hair = (200, 200, 212)
        if not front:
            self._blob(img, head[0], head[1], 26 * w + 2, 26, hair, gloss=0.5)
            self._blob(img, head[0], head[1] - 12, 14, 13, hair, gloss=0.6)
            return hands
        self._blob(img, head[0], head[1] - 3, 28 * w + 2, 22, hair, gloss=0.15)    # Haar hinten
        self._blob(img, head[0], head[1] - 15, 13, 12, hair, gloss=0.2)            # Knoten
        self._blob(img, head[0], head[1] + 2, 23 * w + 1, 24, XMAS_SKIN, gloss=0.3)  # Gesicht
        for side in (-1, 1):                                                        # Haar seitlich gescheitelt
            self._blob(img, head[0] + side * 6 * w, head[1] - 8, 15 * w + 1, 7, hair, ang=side * 14, gloss=0.15)
        for side in (-1, 1):
            ex = head[0] + side * 5 * w
            d.ellipse([ex - 4, head[1] - 4, ex + 4, head[1] + 3], outline=(90, 70, 60))   # Brille
            d.ellipse([ex - 1, head[1] - 1, ex + 1, head[1] + 1], fill=(40, 40, 50))
            self._blob(img, head[0] + side * 7 * w, head[1] + 5, 6, 4, (240, 150, 150), gloss=0)  # Wangen
        d.arc([head[0] - 4, head[1] + 3, head[0] + 4, head[1] + 9], 20, 160, fill=(170, 60, 60), width=1)
        return hands

    # -- Szene --------------------------------------------------------------- #
    def _xmas_scene(self):
        """Nachthimmel, Hügel, Schneeboden, Weihnachtsbaum, Geschenke, Bank (unbeweglich, zwischengespeichert)."""
        if "_xmas_bg" in self.__dict__:
            return self._xmas_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        arr = np.broadcast_to(np.array([6, 10, 34], np.float32) * (1 - ys) + np.array([28, 34, 70], np.float32) * ys,
                              (HEIGHT, WIDTH, 3)).copy()
        img = Image.fromarray(arr.astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(11)
        for _ in range(40):                                                         # Sterne
            x, y = rng.randrange(WIDTH), rng.randrange(0, 80)
            v = rng.randint(110, 220)
            d.point((x, y), fill=(v, v, v + 20 if v < 235 else 255))
        self._blob(img, 250, XMAS_FLOOR + 8, 260, 70, (190, 205, 235), gloss=0.05)  # Hügel
        self._blob(img, 40, XMAS_FLOOR + 14, 220, 60, (205, 215, 240), gloss=0.05)
        snow = np.linspace(1.0, 0.75, HEIGHT - XMAS_FLOOR + 6)[:, None]
        ground = (np.array([232, 238, 250], np.float32)[None, :] * snow).astype(np.uint8)
        img.paste(Image.fromarray(np.broadcast_to(ground[:, None, :], (len(ground), WIDTH, 3)).copy(), "RGB"),
                  (0, XMAS_FLOOR - 6))
        x0 = XMAS_TREE_X                                                            # Baum
        self._blob(img, x0, XMAS_FLOOR - 4, 70, 10, (160, 172, 200), gloss=0)
        d.rectangle([x0 - 5, XMAS_FLOOR - 22, x0 + 5, XMAS_FLOOR - 4], fill=(96, 60, 36))
        tiers = [(XMAS_FLOOR - 20, 46, 40), (XMAS_FLOOR - 50, 38, 36), (XMAS_FLOOR - 78, 28, 32), (XMAS_FLOOR - 102, 18, 26)]
        for base, half, height in tiers:
            d.polygon([(x0 - half, base), (x0 + half, base), (x0, base - height)], fill=(24, 110, 52))
            d.polygon([(x0, base), (x0 + half, base), (x0, base - height)], fill=(14, 78, 38))
            for k in range(-half + 4, half - 2, 7):                                 # Schnee auf den Zweigen
                d.ellipse([x0 + k - 3, base - 3, x0 + k + 3, base + 1], fill=(236, 242, 252))
        for gx, gw, gh, col, rib in ((x0 - 34, 18, 14, (60, 120, 220), (250, 220, 70)),
                                     (x0 + 22, 22, 16, (220, 50, 60), (250, 250, 250)),
                                     (x0 - 6, 16, 11, (240, 200, 50), (220, 40, 50))):
            d.rectangle([gx, XMAS_FLOOR - gh, gx + gw, XMAS_FLOOR], fill=col)
            d.rectangle([gx + gw * 0.65, XMAS_FLOOR - gh, gx + gw, XMAS_FLOOR], fill=tuple(int(c * 0.75) for c in col))
            d.rectangle([gx + gw // 2 - 1, XMAS_FLOOR - gh, gx + gw // 2 + 1, XMAS_FLOOR], fill=rib)
            d.rectangle([gx, XMAS_FLOOR - gh // 2 - 1, gx + gw, XMAS_FLOOR - gh // 2 + 1], fill=rib)
            d.ellipse([gx + gw // 2 - 4, XMAS_FLOOR - gh - 4, gx + gw // 2 + 4, XMAS_FLOOR - gh + 1], outline=rib, width=2)
        lights = []                                                                 # Lichterkette
        rng = random.Random(5)
        for base, half, height in tiers:
            for k in range(5):
                f = (k + 0.5) / 5
                lights.append((x0 + (f * 2 - 1) * half * 0.85, base - 6 - rng.uniform(0, height * 0.35),
                               XMAS_LIGHT_COLORS[len(lights) % len(XMAS_LIGHT_COLORS)]))
        self._xmas_bg = (img, lights, (x0, tiers[-1][0] - tiers[-1][2] - 2))
        return self._xmas_bg

    def _xmas_bench(self, img, d, x, floor):
        """Holzbank im Schnee (bei Wortbeiträgen)."""
        for lx in (x - 34, x + 30):
            d.rectangle([lx, floor - 18, lx + 5, floor], fill=(80, 50, 30))
        self._blob(img, x, floor - 20, 82, 9, (130, 86, 50), gloss=0.3)
        self._blob(img, x, floor - 22, 76, 4, (240, 244, 252), gloss=0)

    def _xmas_snow(self, st, s, dt, img, o, front):
        """Schneeflocken in zwei Ebenen (hinten klein und langsam, vorne groß); Bass wirbelt sie auf."""
        n_back, n_front = {"light": (35, 8), "normal": (70, 18), "heavy": (130, 34)}[o["snow"]]
        key = "front" if front else "back"
        n = n_front if front else n_back
        flakes = st.get(key)
        if flakes is None or len(flakes) != n:
            rng = np.random.default_rng(3 if front else 4)
            flakes = st[key] = np.column_stack([rng.uniform(0, WIDTH, n), rng.uniform(0, VIS_H, n),
                                                rng.uniform(0, 6.28, n)])
        speed = 26 if front else 12
        gust = st.get("gust", 0.0)
        flakes[:, 1] += dt * speed * (1 + 0.6 * s["bass"])
        flakes[:, 0] += dt * (np.sin(s["t"] * 0.9 + flakes[:, 2]) * (10 if front else 5) + gust * (40 if front else 25))
        flakes[:, 0] %= WIDTH
        wrap = flakes[:, 1] > VIS_H
        flakes[wrap, 1] -= VIS_H + 4
        d = ImageDraw.Draw(img)
        r = 1.6 if front else 0.8
        col = (250, 252, 255) if front else (200, 210, 235)
        for x, y, _ in flakes:
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)

    # -- Tanz ---------------------------------------------------------------- #
    @vis_style("xmas")
    def vis_xmas(self, s, o, color):
        t = s["t"]
        bg, lights, star = self._xmas_scene()
        img = bg.copy()
        d = ImageDraw.Draw(img)
        st = self._vstate("xmas", lambda: {"beats": s["beats"], "k": 0, "t0": t, "spin_t": -9.0, "twirl_t": -9.0,
                                           "start": t, "gust": 0.0})
        dt = self._vis_dt(st, t)
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        moving = s.get("active") or (s.get("demo") and not s.get("idle"))
        talk = bool(s.get("talk"))
        new_beat = s["beats"] != st["beats"]
        if new_beat:
            st["beats"] = s["beats"]
        if not talk and (new_beat or (moving and t - st["t0"] > period * 1.6)):
            st["k"] += 1
            st["t0"] = t
            if st["k"] % 8 == 0:
                st["spin_t"] = t                      # Pirouette bzw. Drehung unter dem Arm
            if s["bass"] > 0.75:
                st["gust"] = (1 if st["k"] % 2 else -1) * 1.0
        st["gust"] *= max(0.0, 1 - dt * 2.5)
        self._xmas_snow(st, s, dt, img, o, front=False)
        # Lichterkette und Stern
        for i, (lx, ly, lc) in enumerate(lights):
            on = (not o["lights"]) or ((i * 7 + s["beats"] * 3) % 5 != 0)
            k = (0.55 + 0.45 * s["level"]) if on else 0.18
            c = tuple(int(x * k) for x in lc)
            if on:
                self._blob(img, lx, ly, 12, 12, lc, alpha=round(0.45 * k, 1), flat=True)
            d.ellipse([lx - 2, ly - 2, lx + 2, ly + 2], fill=c)
        glow = 10 + 14 * s["bass"]
        self._blob(img, star[0], star[1], glow * 2, glow * 2, (255, 230, 120), alpha=0.55, flat=True)
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = 9 if k % 2 == 0 else 4
            pts.append((star[0] + math.cos(a) * rr, star[1] + math.sin(a) * rr))
        d.polygon(pts, fill=(255, 220, 70))
        mode = o["dance"]
        if mode == "auto":
            mode = ("pair", "santa", "mrs")[int((t - st["start"]) // 60) % 3]
        enter = self.__dict__.pop("_vis_enter", False) and not s.get("demo")
        acts = self._xmas_actors(st, t, dt, mode, talk, enter, period)
        floor = XMAS_FLOOR
        bench_on = talk or any(a["state"] == "sit" for a in acts.values())
        st["bench"] = max(0.0, min(1.0, st["bench"] + (dt if bench_on else -dt) / 0.5))
        if st["bench"] > 0:                                                         # Bank blendet weich ein/aus
            if st["bench"] >= 1:
                self._xmas_bench(img, d, XMAS_BENCH_X, floor)
            else:
                benched = img.copy()
                self._xmas_bench(benched, ImageDraw.Draw(benched), XMAS_BENCH_X, floor)
                img = Image.blend(img, benched, st["bench"])
                d = ImageDraw.Draw(img)
        energy = 0.35 + 0.65 * s["level"] if moving else 0.25
        phase = ((t - st["t0"]) / period) % 1.0
        bob = (1 + math.cos(2 * math.pi * phase)) / 2 * (2 + 6 * energy)
        sway = math.sin(math.pi * (st["k"] + phase)) * energy
        k = _smooth((t - st["t0"]) / 0.18)
        spin_k = (t - st["spin_t"]) / (period * 2)
        spin = 360 * _smooth(spin_k) if 0 <= spin_k < 1 else 0.0
        poses = self._xmas_dance_poses(st, t, floor, mode, acts, bob, sway, k, spin, energy)
        for who in ("santa", "mrs"):
            a = acts[who]
            pose = self._xmas_target(who, a, st, t, poses[who])
            if a["pose"] is None or t - a["state_t"] > 0.35:
                a["pose"] = pose
            else:                                                                   # Haltungswechsel weich
                a["pose"] = _mix_pose_spin(a["pose"], pose, 1 - math.exp(-dt * 12))
            x = a["x"] + a["pose"]["dx"]
            if not -XMAS_OFF_MARGIN < x < WIDTH + XMAS_OFF_MARGIN:
                continue                                                            # ganz außerhalb des Bildes
            p = dict(a["pose"])
            p.pop("dx")
            sp = p.pop("spin")
            sitting = a["state"] == "sit"
            if who == "santa":
                self._santa(img, d, x, floor - 20 if sitting else floor, p, t * 0.3 if sitting else t,
                            sitting=sitting, scroll=sitting)
            else:
                self._mrs(img, d, x, floor - 20 if sitting else floor, p, t, spin=sp, sitting=sitting, mug=sitting)
        self._xmas_snow(st, s, dt, img, o, front=True)
        return img

    @staticmethod
    def _xmas_wave(pose, t, energy):
        """Arme schwingen etwas im Takt (wie bei der Tänzerin)."""
        out = dict(pose)
        w = math.sin(t * 9) * 4 * energy
        out["lh"] = (pose["lh"][0], pose["lh"][1] + w)
        out["rh"] = (pose["rh"][0], pose["rh"][1] - w)
        return out

    # -- Auftritte: ins Bild gehen, hinausgehen, zur Bank -------------------- #
    @staticmethod
    def _xmas_goals(mode, talk):
        """Zielposition je Figur: Bank bei Wortbeiträgen, sonst je Tanzmodus (außerhalb = XMAS_OFF)."""
        if talk:
            return {"santa": XMAS_BENCH_X - 18, "mrs": XMAS_BENCH_X + 24}
        return {"pair": {"santa": 160, "mrs": 226}, "santa": {"santa": 190, "mrs": XMAS_OFF["mrs"]},
                "mrs": {"santa": XMAS_OFF["santa"], "mrs": 190}}[mode]

    def _xmas_actors(self, st, t, dt, mode, talk, enter, period):
        """Position und Zustand (dance/wave/walk/sit) beider Figuren. Wer gehen soll, winkt erst zum Abschied;
        wer neu hereinkommt, wartet, bis der andere sich verabschiedet hat, und winkt beim Ankommen."""
        goals = self._xmas_goals(mode, talk)
        acts = st.get("acts")
        if acts is None or enter:
            acts = st["acts"] = {}
            for who, delay in (("santa", 0.3), ("mrs", 0.8)):
                acts[who] = {"x": XMAS_OFF[who] if enter else goals[who], "goal": goals[who], "go_t": t + delay,
                             "wave_t": -9.0, "came": enter, "dir": 1, "state": "", "state_t": t, "pose": None}
            st["hold"] = 1.0 if mode == "pair" and not talk and not enter else 0.0
            st["bench"] = 1.0 if talk and not enter else 0.0
            st["gait"] = 0.0
        on = {w: a["x"] != XMAS_OFF[w] for w, a in acts.items()}
        leaving = {w: on[w] and goals[w] == XMAS_OFF[w] and a["goal"] != goals[w] for w, a in acts.items()}
        for who, a in acts.items():
            if goals[who] == a["goal"]:
                continue
            a["goal"], a["came"] = goals[who], not on[who]
            other = "mrs" if who == "santa" else "santa"
            if leaving[who]:
                a["wave_t"] = a["go_t"] = t + 0.9                                   # erst winken, dann gehen
            elif on[who]:
                a["go_t"] = t + 0.4                                                 # Hand loslassen, aufstehen
            else:
                a["go_t"] = t + (1.5 if leaving[other] else 0.3)
        st["gait"] += dt / max(0.4, min(0.8, period)) * math.pi                     # ein Schritt je Schlag
        for who, a in acts.items():
            dist = a["goal"] - a["x"]
            walking = t >= a["go_t"] and dist != 0
            if walking:
                a["dir"] = 1 if dist > 0 else -1
                a["x"] = a["goal"] if abs(dist) <= XMAS_WALK_SPEED * dt else a["x"] + a["dir"] * XMAS_WALK_SPEED * dt
                if a["x"] == a["goal"]:
                    walking = False
                    if a["came"] and not talk and mode != "pair":
                        a["wave_t"] = t + 0.8                                       # „Hallo!“
                    a["came"] = False
            at_goal = a["x"] == a["goal"]
            state = "walk" if walking else "wave" if t < a["wave_t"] else "sit" if talk and at_goal else "dance"
            if state != a["state"]:
                a["state"], a["state_t"] = state, t
        together = mode == "pair" and not talk and all(a["state"] == "dance" and a["x"] == a["goal"]
                                                       for a in acts.values())
        st["hold"] = max(0.0, min(1.0, st["hold"] + (dt if together else -dt) / 0.4))
        return acts

    def _xmas_dance_poses(self, st, t, floor, mode, acts, bob, sway, k, spin, energy):
        """Tanzhaltung beider Figuren; im Paar mit gehaltenen Händen (Anteil st["hold"])."""
        n = st["k"]
        santa = _mix_pose(SANTA_POSES[(n - 1) % len(SANTA_POSES)], SANTA_POSES[n % len(SANTA_POSES)], k)
        santa = self._xmas_wave(santa, t, energy)
        santa.update(bob=bob, lean=santa["lean"] + sway * 6, dx=sway * (8 if mode == "pair" else 10), spin=0.0)
        hold = st["hold"]
        mrs = _mix_pose(MRS_POSES[(n - 1) % len(MRS_POSES)], MRS_POSES[n % len(MRS_POSES)], k)
        if spin:
            mrs = dict(MRS_POSES[0])                                                # Pirouette allein
        mrs.update(bob=bob, lean=mrs["lean"] + sway * 6, dx=sway * (8 if mode == "pair" else 12), spin=spin)
        if hold > 0:
            sx, mx = acts["santa"]["x"] + sway * 8, acts["mrs"]["x"] + sway * 8
            ps, pm = self._xmas_pair_poses(st, floor, bob, sway, spin if hold >= 1 else 0.0, sx, mx)
            ps.update(dx=sway * 8, spin=0.0)
            pm.update(dx=sway * 8, spin=spin if hold >= 1 else 0.0)
            if hold >= 1:
                santa, mrs = ps, pm
            else:
                santa, mrs = _mix_pose(santa, ps, hold), _mix_pose(mrs, pm, hold)
                mrs["spin"] = 0.0
        return {"santa": santa, "mrs": mrs}

    @staticmethod
    def _xmas_target(who, a, st, t, dance):
        """Zielhaltung je Zustand: tanzen, winken, gehen (Schritt im Takt) oder sitzen."""
        state = a["state"]
        if state == "dance":
            return dance
        if state == "sit":
            sit = {"lh": (14, 22), "rh": (-14, 22), "lf": (0, 0), "rf": (0, 0), "lean": 0, "head": 10,
                   "bob": math.sin(t * 0.8) * 0.8, "dx": 0.0, "spin": 0.0}
            return sit if who == "santa" else dict(sit, lh=(10, 16), rh=(-10, 16), head=-8)
        if state == "wave":
            w = math.sin(t * 10)
            if who == "santa":
                return dict(SANTA_POSES[2], rh=(22 + w * 6, -26), bob=0.0, dx=0.0, spin=0.0)
            return dict(MRS_POSES[2], rh=(10 + w * 7, -34), bob=0.0, dx=0.0, spin=0.0)
        g, dr = st["gait"], a["dir"]                                                # gehen
        sg = math.sin(g)
        lift_l, lift_r = max(0.0, sg), max(0.0, -sg)
        bob = 2.5 * abs(math.cos(g))
        if who == "santa":
            return {"lh": (-4 + dr * 6 * sg, 30), "rh": (4 - dr * 6 * sg, 30), "lf": (-3 + dr * 3, 40 - 10 * lift_l),
                    "rf": (3 + dr * 3, 40 - 10 * lift_r), "lean": dr * 5, "head": dr * 10, "bob": bob,
                    "dx": 0.0, "spin": 0.0}
        return {"lh": (-6 + dr * 5 * sg, 28), "rh": (6 - dr * 5 * sg, 28), "lf": (dr * 3, 22 - 7 * lift_l),
                "rf": (dr * 3, 22 - 7 * lift_r), "lean": dr * 4, "head": dr * 8, "bob": bob, "dx": 0.0,
                "spin": dr * 50.0}

    def _xmas_pair_poses(self, st, floor, bob, sway, spin, sx, mx):
        """Paartanz: Hand in Hand, beide wiegen sich; jeden 8. Schritt dreht sie sich unter seinem Arm."""
        twirl = spin != 0.0
        joint = ((sx + mx) / 2, floor - (128 if twirl else 78) - bob)               # gehaltene Hände
        free = SANTA_POSES[st["k"] % 3]
        santa = dict(free, bob=bob, lean=sway * 5, head=6)
        santa["rh"] = (joint[0] - (sx + 21), joint[1] - (floor - 44 + bob - 22 - 22 + 6))
        if twirl:
            santa["lh"] = (14, 22)
        mrs_free = MRS_POSES[(st["k"] + 1) % len(MRS_POSES)]
        mrs = dict(mrs_free, bob=bob, lean=-sway * 5, head=-6)
        mrs["lh"] = (joint[0] - (mx - 14), joint[1] - (floor - 40 + bob - 18 - 17 + 5))
        if twirl:
            mrs["rh"] = (8, 30)
        return santa, mrs
