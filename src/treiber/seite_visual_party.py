"""Visualisierung „Überraschungsparty“ (Geburtstag): Im dunklen Wohnzimmer verstecken sich drei Gäste (und der Hund)
hinter dem Sofa – man sieht nur ihre Augen, die im Takt blinzeln. Beim ersten Höhepunkt der Musik (spätestens nach
PT_HIDE_MAX Sekunden) geht das Licht an: „ÜBERRASCHUNG!“, Konfetti, dann wird getanzt (Tröten auf hohe Schläge).
Gags: der Hund frisst die Torte, Trickkerzen gehen immer wieder an, ein Kastenteufel springt aus dem Geschenk,
Luftballons platzen bei kräftigem Bass, ein Gast verschläft die Überraschung. Bei Wortbeiträgen atmen alle Helium
ein und quieken. Nach einer Runde (Option round) wird es dunkel und alle verstecken sich wieder.
Namen und Alter kommen aus der Geburtstagsliste (Option birthdays, auch für den Festkalender).
"""
import math
import random

PT_FLOOR = VIS_H - 22                   # Fußboden (Fußlinie der Gäste)
PT_SOFA = (148, 298)                    # Sofa von … bis (x)
PT_SOFA_BACK = PT_FLOOR - 68            # Oberkante der Rückenlehne
PT_HIDE_X = (176, 222, 268)             # Verstecke der Gäste hinter dem Sofa
PT_STAND_X = (172, 220, 268)            # Plätze vor dem Sofa
PT_TABLE = (26, 106)                    # Tisch mit der Torte
PT_CAKE_X = 66
PT_GIFT_X = 128                         # Geschenk (Kastenteufel) auf dem Boden
PT_HIDE_MIN, PT_HIDE_MAX = 6.0, 20.0    # so lange (s) verstecken sich die Gäste mindestens/höchstens
PT_SURPRISE = 3.6                       # Dauer „ÜBERRASCHUNG!“
PT_GAG_FIRST = 15.0                     # erster Gag so viele Sekunden nach der Überraschung
PT_GAGS = {"hund": 12.0, "kerzen": 11.0, "geschenk": 9.5}
PT_WALK = 60                            # Gehen (Pixel je Sekunde)
PT_GUESTS = [                           # Hemd, Haut, Haare, Partyhut, Tröte
    {"shirt": (60, 130, 225), "skin": (242, 204, 176), "hair": (70, 46, 30), "hat": (230, 60, 100), "horn": (250, 210, 60)},
    {"shirt": (236, 170, 40), "skin": (198, 146, 108), "hair": (30, 24, 22), "hat": (60, 170, 230), "horn": (240, 80, 160)},
    {"shirt": (110, 190, 90), "skin": (250, 218, 196), "hair": (200, 150, 70), "hat": (250, 200, 60), "horn": (90, 200, 250)},
]
PT_POSES = [                            # Hände relativ zur Schulter, Füße gespreizt
    {"lh": (-6, -22), "rh": (6, -22), "spread": 3},       # Arme hoch
    {"lh": (-13, 8), "rh": (13, 8), "spread": 5},         # Arme seitlich unten
    {"lh": (-4, -21), "rh": (13, 7), "spread": 4},        # Disco-Zeigefinger
    {"lh": (11, 4), "rh": (-11, 4), "spread": 3},         # klatschen
    {"lh": (-16, -5), "rh": (16, -5), "spread": 6},       # Arme aus
    {"lh": (-12, 10), "rh": (8, -20), "spread": 4},       # ein Arm hoch
]
PT_BALLOONS = [((152, 84), (232, 60, 60)), ((168, 72), (70, 130, 240)), ((283, 74), (250, 200, 50)),
               ((298, 88), (80, 200, 110))]
PT_HELIUM = ["Hihi!", "Quiiiek!", "Ich klinge wie 'ne Maus!", "Nochmal!", "Alles Guuute!", "Hüstel … quiek!"]
PT_HIDE_SAY = ["Psst!", "Pssst! Licht aus!", "Wer hat gepupst?", "Psst, er kommt!", "Nicht kichern!"]


def _pt_banner(names):
    if not names:
        return "Alles Gute!"
    if len(names) > 2:
        return "Alles Gute euch allen!"
    return "Alles Gute, " + " & ".join(names) + "!"


class PartyVisual:
    vis_party_dark = False              # Gäste verstecken sich im Dunkeln (Tastatur fast aus)

    # -- Hintergrund ---------------------------------------------------------- #
    def _pt_room(self, banner):
        """Wohnzimmer mit Fenster, Tisch, Sofa und Girlande (zwischengespeichert je Bannertext)."""
        cache = self.__dict__.get("_pt_room_img")
        if cache and cache[0] == banner:
            return cache[1]
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        arr = np.broadcast_to(np.array([196, 150, 110], np.float32) * (1 - ys * 0.25), (HEIGHT, WIDTH, 3)).copy()
        arr[:, ::12] *= 0.9                                                         # Tapete mit Streifen
        arr[:, 6::12] *= 1.04
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        for x in range(0, WIDTH, 24):                                               # Tapetenmuster
            for y in range(52 + (x // 24 % 2) * 12, PT_FLOOR - 20, 24):
                d.ellipse([x + 10, y, x + 14, y + 4], fill=(214, 172, 130))
        d.rectangle([0, PT_FLOOR - 10, WIDTH, PT_FLOOR - 2], fill=(236, 226, 210))  # Fußleiste
        for y in range(PT_FLOOR - 2, HEIGHT, 7):                                    # Holzboden
            d.rectangle([0, y, WIDTH, y + 6], fill=(150, 98, 58) if (y // 7) % 2 else (140, 90, 52))
            off = (y * 37) % 60
            for x in range(off, WIDTH, 60):
                d.line([(x, y), (x, y + 6)], fill=(110, 70, 40))
        wx0, wy0, wx1, wy1 = 16, 52, 82, 118                                        # Fenster bei Nacht
        d.rectangle([wx0 - 4, wy0 - 4, wx1 + 4, wy1 + 4], fill=(246, 240, 230))
        d.rectangle([wx0, wy0, wx1, wy1], fill=(18, 26, 60))
        rng = random.Random(9)
        for _ in range(14):
            d.point((rng.randrange(wx0 + 2, wx1 - 2), rng.randrange(wy0 + 2, wy1 - 20)), fill=(220, 220, 240))
        self._blob(img, 64, 68, 14, 14, (250, 240, 200), gloss=0.1)                 # Mond
        d.rectangle([wx0 - 6, wy1 + 2, wx1 + 6, wy1 + 7], fill=(230, 222, 210))
        d.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], fill=(246, 240, 230), width=3)
        d.line([(wx0, (wy0 + wy1) / 2), (wx1, (wy0 + wy1) / 2)], fill=(246, 240, 230), width=3)
        tx0, tx1, ty = PT_TABLE[0], PT_TABLE[1], PT_FLOOR - 40                      # Tisch
        for lx in (tx0 + 6, tx1 - 10):
            d.rectangle([lx, ty, lx + 4, PT_FLOOR], fill=(110, 66, 36))
        d.rectangle([tx0, ty - 4, tx1, ty + 2], fill=(140, 86, 46))
        d.polygon([(tx0 + 2, ty - 4), (tx1 - 2, ty - 4), (tx1 + 4, ty + 10), (tx0 - 4, ty + 10)], fill=(240, 240, 250))
        for x in range(tx0 - 2, tx1 + 4, 8):                                       # Tischdecke mit Zacken
            d.polygon([(x, ty + 10), (x + 8, ty + 10), (x + 4, ty + 15)], fill=(240, 240, 250))
        sx0, sx1 = PT_SOFA                                                          # Sofa
        self._blob(img, (sx0 + sx1) / 2, PT_FLOOR + 1, sx1 - sx0 + 20, 10, (90, 60, 40), gloss=0)
        d.rounded_rectangle([sx0 + 4, PT_SOFA_BACK, sx1 - 4, PT_FLOOR - 30], radius=10, fill=(150, 40, 60))
        d.rounded_rectangle([sx0 + 4, PT_SOFA_BACK, sx1 - 4, PT_SOFA_BACK + 8], radius=6, fill=(176, 56, 78))
        for k in range(3):                                                          # Kissen der Lehne
            cx = sx0 + 30 + k * (sx1 - sx0 - 60) / 2
            d.line([(cx + (sx1 - sx0 - 60) / 4, PT_SOFA_BACK + 10), (cx + (sx1 - sx0 - 60) / 4, PT_FLOOR - 34)],
                   fill=(120, 30, 48), width=2)
        d.rounded_rectangle([sx0 + 8, PT_FLOOR - 36, sx1 - 8, PT_FLOOR - 14], radius=6, fill=(170, 50, 72))
        d.line([((sx0 + sx1) / 2, PT_FLOOR - 34), ((sx0 + sx1) / 2, PT_FLOOR - 16)], fill=(130, 36, 54), width=2)
        for ax in (sx0, sx1 - 18):                                                  # Armlehnen
            d.rounded_rectangle([ax, PT_FLOOR - 50, ax + 18, PT_FLOOR - 12], radius=7, fill=(136, 34, 54))
            d.rounded_rectangle([ax, PT_FLOOR - 50, ax + 18, PT_FLOOR - 42], radius=6, fill=(160, 46, 66))
        for fx in (sx0 + 6, sx1 - 12):
            d.rectangle([fx, PT_FLOOR - 12, fx + 6, PT_FLOOR - 2], fill=(60, 36, 24))
        lx = 228                                                                    # Deckenlampe
        d.line([(lx, 0), (lx, 12)], fill=(60, 50, 40), width=2)
        d.chord([lx - 16, 6, lx + 16, 30], 180, 360, fill=(246, 214, 140))
        self._blob(img, lx, 20, 70, 40, (255, 240, 190), alpha=0.35, flat=True)
        pts = []                                                                    # Girlande mit Wimpeln
        for k in range(17):
            x = 6 + k * (WIDTH - 12) / 16
            pts.append((x, 24 + 10 * math.sin(math.pi * k / 16)))
        d.line(pts, fill=(90, 70, 60), width=1)
        cols = [(230, 60, 80), (250, 200, 50), (60, 160, 230), (110, 200, 90), (220, 110, 220)]
        for k, (x, y) in enumerate(pts[:-1]):
            d.polygon([(x + 2, y), (x + 16, y + 1), (x + 9, y + 13)], fill=cols[k % len(cols)])
        font = load_font(13, bold=True)
        w = d.textlength(banner, font=font) + 20
        bx = (WIDTH - w) / 2
        d.rounded_rectangle([bx, 36, bx + w, 54], radius=4, fill=(250, 246, 236), outline=(230, 60, 100), width=2)
        d.text((bx + 10, 37), banner, font=font, fill=(200, 40, 80))
        self._pt_room_img = (banner, img)
        return img

    # -- Figuren -------------------------------------------------------------- #
    def _pt_guest(self, img, d, x, floor, pose, spec, t, sit=False):
        """Gast mit Partyhut: Beine und Arme per IK, Tröte im Mund (pose["horn"] 0…1 = ausgerollt)."""
        bob = pose.get("bob", 0.0)
        hip = (x, floor - (10 if sit else 26) - bob)                              # sit: im Schneidersitz am Boden
        self._blob(img, x, floor + 1, 30, 6, (90, 60, 40), gloss=0, alpha=0.5)
        pants = (54, 56, 78)
        for side in (-1, 1):
            hj = (hip[0] + side * 5, hip[1])
            if sit:
                knee, foot = (hj[0] + side * 11, floor - 5), (hj[0] - side * 3, floor - 2)
            else:
                knee, foot = _ik(hj, (hj[0] + side * pose.get("spread", 4), floor - 2), 13, 13, -side)
            self._limb(img, hj, knee, 8, pants)
            self._limb(img, knee, foot, 7, pants)
            self._blob(img, foot[0] + side * 2, foot[1] + 1, 10, 6, (40, 30, 30), gloss=0.6)
        lean = pose.get("lean", 0.0)
        body = (hip[0] + lean, hip[1] - 13)
        self._blob(img, body[0], body[1], 24, 30, spec["shirt"], gloss=0.3)
        neck = (body[0] + lean * 0.5, body[1] - 12)
        hands = []
        for side in (-1, 1):
            sh = (neck[0] + side * 10, neck[1] + 3)
            h = pose["lh" if side < 0 else "rh"]
            elbow, hand = _ik(sh, (sh[0] + h[0], sh[1] + h[1]), 11, 11, side)
            self._limb(img, sh, elbow, 7, spec["shirt"])
            self._limb(img, elbow, hand, 6, spec["skin"])
            self._blob(img, hand[0], hand[1], 7, 7, spec["skin"], gloss=0.2)
            hands.append(hand)
        head = (neck[0] + lean * 0.3, neck[1] - 10)
        self._blob(img, head[0], head[1] - 6, 22, 12, spec["hair"], gloss=0.3)
        self._blob(img, head[0], head[1], 19, 20, pose.get("face") or spec["skin"], gloss=0.25)
        if pose.get("cheeks"):                                                      # pustet: dicke Backen
            for side in (-1, 1):
                self._blob(img, head[0] + side * 7, head[1] + 4, 8, 8, _lerp(spec["skin"], (240, 120, 110), 0.4))
        if pose.get("sleep"):
            for side in (-1, 1):
                d.line([(head[0] + side * 4 - 2, head[1] - 1), (head[0] + side * 4 + 2, head[1] - 1)], fill=(30, 30, 40))
        else:
            for side in (-1, 1):
                ex = head[0] + side * 4 + pose.get("look", 0)
                d.ellipse([ex - 1.5, head[1] - 3, ex + 1.5, head[1] + 1], fill=(30, 30, 40))
        mouth = pose.get("mouth", 0.0)
        if mouth > 0.5:
            d.ellipse([head[0] - 3, head[1] + 4, head[0] + 3, head[1] + 9], fill=(110, 30, 40))
        elif not pose.get("cheeks"):
            d.arc([head[0] - 4, head[1] + 1, head[0] + 4, head[1] + 7], 20, 160, fill=(110, 40, 40))
        horn = pose.get("horn", 0.0)
        if horn > 0.05:                                                             # Tröte rollt sich aus
            x0, y0 = head[0] + 2, head[1] + 6
            ln = 4 + 18 * horn
            d.line([(x0, y0), (x0 + ln, y0 + 2)], fill=spec["horn"], width=3)
            d.polygon([(x0 + ln, y0 - 1), (x0 + ln + 5, y0 - 3), (x0 + ln + 5, y0 + 7), (x0 + ln, y0 + 5)],
                      fill=spec["hat"])
        if not pose.get("nohat"):
            tilt = lean * 0.6 + pose.get("hat_tilt", 0.0)
            base_l, base_r = (head[0] - 8, head[1] - 8), (head[0] + 8, head[1] - 8)
            tip = (head[0] + tilt * 1.5 + 2, head[1] - 30)
            d.polygon([base_l, base_r, tip], fill=spec["hat"])
            for k in (0.35, 0.65):                                                  # Streifen
                a = (base_l[0] + (tip[0] - base_l[0]) * k, base_l[1] + (tip[1] - base_l[1]) * k)
                b = (base_r[0] + (tip[0] - base_r[0]) * k, base_r[1] + (tip[1] - base_r[1]) * k)
                d.line([a, b], fill=(250, 250, 250), width=2)
            self._blob(img, tip[0], tip[1], 7, 7, (250, 250, 250), gloss=0.2)
        return head, hands

    def _pt_dog(self, img, d, x, floor, mode, t, cream=False):
        """Dackel, schaut nach links. mode: walk, beg (Vorderpfoten auf dem Tisch), lie (schläft satt)."""
        brown, dark = (156, 92, 44), (96, 54, 26)
        if mode == "beg":
            self._blob(img, x + 4, floor - 18, 16, 34, brown, ang=-30, gloss=0.3)
            head = (x - 10, PT_FLOOR - 46)
            for lx in (x + 2, x + 10):
                d.line([(lx, floor - 6), (lx - 1, floor)], fill=dark, width=3)
            d.line([(x - 2, floor - 30), (x - 12, PT_FLOOR - 40)], fill=dark, width=3)
            tail = (x + 14, floor - 6)
        elif mode == "lie":
            self._blob(img, x, floor - 6, 40, 12, brown, gloss=0.3)
            head = (x - 22, floor - 8)
            tail = (x + 20, floor - 6)
        else:
            step = math.sin(t * 14)
            self._blob(img, x, floor - 11, 40, 14, brown, gloss=0.3)
            for k, lx in enumerate((x - 13, x - 7, x + 9, x + 15)):
                sw = step * 3 * (1 if k % 2 else -1)
                d.line([(lx, floor - 6), (lx + sw, floor)], fill=dark, width=3)
            head = (x - 22, floor - 18)
            tail = (x + 20, floor - 13)
        wag = math.sin(t * 18) * 6
        d.line([tail, (tail[0] + 9, tail[1] - 6 + wag)], fill=brown, width=3)
        self._blob(img, head[0], head[1], 14, 12, brown, gloss=0.3)
        self._blob(img, head[0] - 7, head[1] + 2, 11, 7, brown, gloss=0.3)
        self._blob(img, head[0] + 3, head[1] + 2, 6, 11, dark, gloss=0.2)            # Ohr
        d.ellipse([head[0] - 13, head[1] + 0, head[0] - 10, head[1] + 3], fill=(20, 16, 16))     # Nase
        if mode == "lie":
            d.line([(head[0] - 4, head[1] - 2), (head[0] - 1, head[1] - 2)], fill=(20, 16, 16))
        else:
            d.ellipse([head[0] - 4, head[1] - 4, head[0] - 1, head[1] - 1], fill=(20, 16, 16))
        if cream:
            self._blob(img, head[0] - 8, head[1] + 4, 10, 6, (252, 246, 236), gloss=0.2)
        return head

    def _pt_cake(self, img, d, s, t, age, eaten, out_k):
        """Torte auf dem Tisch; Kerzenflammen flackern mit den Frequenzbändern. eaten 0…1 (Hund), out_k: Kerzen
        ausgepustet (0 = brennen, 1 = aus)."""
        cx, base = PT_CAKE_X, PT_FLOOR - 44
        w = 42 * (1 - 0.55 * eaten)
        if eaten < 0.98:
            d.rectangle([cx - w / 2, base - 18, cx + w / 2, base], fill=(250, 214, 226))
            d.rectangle([cx - w / 2, base - 9, cx + w / 2, base - 7], fill=(230, 80, 120))
            self._blob(img, cx, base - 18, w + 2, 9, (254, 246, 250), gloss=0.3)
            for k in range(int(w // 6)):
                d.ellipse([cx - w / 2 + 2 + k * 6, base - 16, cx - w / 2 + 5 + k * 6, base - 12], fill=(254, 246, 250))
            n = max(1, min(12, age or 5))
            for k in range(min(n, int(n * (1 - eaten) + 0.5))):
                kx = cx - w / 2 + 5 + k * (w - 10) / max(1, n - 1) if n > 1 else cx
                d.rectangle([kx - 1, base - 30, kx + 1, base - 20], fill=(120, 190, 250) if k % 2 else (250, 120, 160))
                if out_k < 0.5:
                    b = s["bands"][int(k * (len(s["bands"]) - 1) / max(1, n - 1))] if n > 1 else s["bass"]
                    fh = 4 + 6 * float(b)
                    self._blob(img, kx, base - 31 - fh / 3, 8, 8 + fh, (255, 200, 80), alpha=0.5, flat=True)
                    d.ellipse([kx - 2, base - 31 - fh, kx + 2, base - 30], fill=(255, 220, 110))
                else:                                                               # Rauchfaden
                    for j in range(3):
                        yy = base - 32 - j * 5 - (t * 12) % 5
                        d.point((kx + math.sin(t * 5 + j + k) * 2, yy), fill=(200, 200, 210))
            if age and age >= 40 and out_k < 0.5:                                   # ab 40: es qualmt
                for j in range(4):
                    k = (t * 0.6 + j / 4) % 1.0
                    v = int(170 * (1 - k))
                    self._blob(img, cx - 6 + j * 4 + k * 10, base - 40 - k * 40, 10 + k * 14, 8 + k * 10,
                               (v + 40, v + 40, v + 50), alpha=0.35 * (1 - k), flat=True)
        else:
            d.ellipse([cx - 22, base - 3, cx + 22, base + 2], fill=(244, 244, 250))  # leerer Teller
        if eaten > 0.05:
            for k in range(6):                                                      # Krümel
                d.ellipse([cx + 10 + k * 5, base - 1 - (k % 2), cx + 12 + k * 5, base + 1], fill=(230, 180, 190))

    def _pt_gift(self, img, d, s, t, gag):
        """Geschenk; beim Gag „geschenk“ wackelt es und ein Kastenteufel springt heraus."""
        x, y1 = PT_GIFT_X, PT_FLOOR - 2
        lt = t - gag[1] if gag and gag[0] == "geschenk" else -1
        shake = 0.0
        if 0 <= lt < 4:
            shake = math.sin(t * 40) * (1 + lt) * (0.5 + s["bass"])
        d.rectangle([x - 14 + shake, y1 - 24, x + 14 + shake, y1], fill=(70, 120, 220))
        d.rectangle([x - 2 + shake, y1 - 24, x + 2 + shake, y1], fill=(250, 220, 70))
        if lt < 4 or lt >= PT_GAGS["geschenk"] - 0.6:
            d.rectangle([x - 16 + shake, y1 - 29, x + 16 + shake, y1 - 23], fill=(90, 140, 236))
            d.ellipse([x - 8 + shake, y1 - 36, x + shake, y1 - 28], outline=(250, 220, 70), width=2)
            d.ellipse([x + shake, y1 - 36, x + 8 + shake, y1 - 28], outline=(250, 220, 70), width=2)
            return None
        k = lt - 4                                                                  # Deckel fliegt, Teufel springt
        lid_x, lid_y = x - 20 - k * 30, y1 - 29 - max(0, 60 * k - 40 * k * k)
        if lid_y < y1 - 4:
            d.polygon([(lid_x - 16, lid_y), (lid_x + 16, lid_y - 6 * math.sin(k * 6)),
                       (lid_x + 16, lid_y + 6 - 6 * math.sin(k * 6)), (lid_x - 16, lid_y + 6)], fill=(90, 140, 236))
        sink = max(0.0, (lt - (PT_GAGS["geschenk"] - 1.4)) / 0.8)
        hgt = (54 + 10 * math.sin(t * 9) + 10 * s["bass"]) * (1 - min(1.0, sink)) * min(1.0, k * 4)
        top = y1 - 24 - hgt
        pts = [(x + (5 if i % 2 else -5), y1 - 24 - hgt * i / 8) for i in range(9)]
        d.line(pts, fill=(200, 200, 210), width=2)                                  # Feder
        if hgt > 10:
            self._blob(img, x, top - 10, 24, 24, (226, 240, 200), gloss=0.3)
            for side in (-1, 1):
                self._blob(img, x + side * 8, top - 22, 10, 12, (230, 50, 60), gloss=0.4)  # Haarbüschel
                d.ellipse([x + side * 6 - 4, top - 17, x + side * 6 + 4, top - 8], fill=(255, 255, 255))
                px = x + side * 6 + math.sin(t * 7 + side) * 2
                d.ellipse([px - 1.5, top - 14, px + 1.5, top - 11], fill=(20, 20, 20))
            d.chord([x - 9, top - 9, x + 9, top + 1], 0, 180, fill=(120, 20, 30))
            for k2 in range(5):                                                     # Zähne
                tx = x - 7 + k2 * 3.5
                d.polygon([(tx, top - 4), (tx + 3, top - 4), (tx + 1.5, top - 1)], fill=(255, 255, 255))
        return top

    # -- Ablauf ---------------------------------------------------------------- #
    def _pt_people(self):
        """Geburtstagskinder von heute aus der Liste: (Namen, Alter bei genau einer Person mit Geburtsjahr)."""
        today = birthdays_today(visual_options(self.settings, "party").get("birthdays"), fest_today())
        names = [n for n, _ in today]
        age = today[0][1] if len(today) == 1 else None
        return names, age

    @staticmethod
    def _pt_new_round(st, t, seed, phase="hide"):
        rng = random.Random(seed)
        st.update(phase=phase, phase_t=t, gag=None, next_gag=None, eaten=0.0, dog=None, sleeper=rng.random() < 0.5,
                  balloons=[True] * len(PT_BALLOONS), pops=[], order=rng.sample(list(PT_GAGS), len(PT_GAGS)),
                  rng=rng, round=st.get("round", 0) + 1, say=None)

    @vis_style("party")
    def vis_party(self, s, o, color):
        t = s["t"]
        names, age = self._pt_people()
        img = self._pt_room(_pt_banner(names)).copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        st = self._vstate("party", dict)
        if "phase" not in st:
            st.update(beats=s["beats"], k=0, t0=t, slow=s["level"], fast=s["level"], pop_t=-99.0,
                      confetti=np.zeros((0, 6), np.float32), guests=[{"x": float(x)} for x in PT_STAND_X])
            self._pt_new_round(st, t - (25.0 if demo else 0.0), 17, "party" if demo else "hide")
        dt = self._vis_dt(st, t)
        talk = bool(s.get("talk"))
        new_beat = s["beats"] != st["beats"]
        if new_beat:
            st["beats"] = s["beats"]
            if not talk:
                st["k"] += 1
                st["t0"] = t
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        surge = st["fast"] > st["slow"] * 1.2 + 0.04
        lt = t - st["phase_t"]
        # Ablauf: verstecken → Überraschung → Party → (nach einer Runde) wieder verstecken
        if st["phase"] == "hide" and not demo and lt >= PT_HIDE_MIN and (surge or lt >= PT_HIDE_MAX) and not talk:
            st["phase"], st["phase_t"], lt = "surprise", t, 0.0
            self._pt_confetti(st, 70, burst=True)
        elif st["phase"] == "surprise" and lt >= PT_SURPRISE:
            st["phase"], st["phase_t"], lt = "party", t, 0.0
            st["next_gag"] = t + PT_GAG_FIRST
        elif st["phase"] == "party":
            length = int(o["round"]) if str(o.get("round")).isdigit() else 300
            if lt > max(60, length) and st["gag"] is None and not demo:
                self._pt_new_round(st, t, st["round"] * 31 + 5)
                lt = 0.0
        phase = st["phase"]
        self.vis_party_dark = phase == "hide"
        gag = st["gag"]
        if gag and t - gag[1] >= PT_GAGS[gag[0]]:
            if gag[0] == "hund":
                st["eaten"], st["dog"] = 1.0, "lie"
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(14, 22)
        if phase == "party" and gag is None and not demo and not talk and st["next_gag"] and t >= st["next_gag"]:
            while st["order"]:
                name = st["order"].pop(0)
                if name == "hund" and (not o.get("dog", True) or st["eaten"] > 0):
                    continue
                st["gag"] = gag = (name, t)
                break
            else:
                st["next_gag"] = None
        if phase == "party" and not demo and new_beat and s["bass"] > 0.88 and t - st["pop_t"] > 25 \
                and lt > 20 and sum(st["balloons"]) >= 2 and gag is None:
            alive = [i for i, a in enumerate(st["balloons"]) if a]
            i = alive[st["rng"].randrange(len(alive))]
            st["balloons"][i] = False
            st["pops"].append((i, t))
            st["pop_t"] = t
        # Ballons, Geschenk, Torte
        for i, ((bx, by), bc) in enumerate(PT_BALLOONS):
            if not st["balloons"][i]:
                continue
            yy = by + math.sin(t * 1.3 + i) * 3 - s["bass"] * 4
            xx = bx + math.sin(t * 0.9 + i * 2) * 2
            anchor = (PT_SOFA[0] + 9, PT_FLOOR - 50) if bx < 200 else (PT_SOFA[1] - 9, PT_FLOOR - 50)
            d.line([(xx, yy + 11), anchor], fill=(80, 70, 70))
            self._blob(img, xx, yy, 18, 22, bc, gloss=0.9)
        if age:                                                                     # Zahlenballons (Alter)
            self._pt_age_balloons(img, d, str(age), t, s)
        lid_top = self._pt_gift(img, d, s, t, gag)
        out_k = self._pt_candles_out(gag, t)
        self._pt_cake(img, d, s, t, age, self._pt_eaten(st, gag, t), out_k)
        if gag and gag[0] == "kerzen" and age and age >= 50 and t - gag[1] > 8.5:
            on = int(t * 3) % 2 == 0                                                # Rauchmelder piept
            d.ellipse([214, 0, 230, 8], fill=(240, 240, 240))
            d.ellipse([220, 2, 224, 6], fill=(255, 40, 40) if on else (90, 30, 30))
            if on:
                self._xmas_party_say(d, 222, 30, "PIEP! PIEP!")
        heads = self._pt_guests_draw(img, d, st, s, t, dt, phase, lt, gag, talk, o)
        dog = self._pt_dog_state(st, gag, t)
        if dog:
            self._pt_dog(img, d, dog[0], PT_FLOOR, dog[1], t, cream=dog[2])
        for i, pt in list(st["pops"]):                                              # PENG!
            k = t - pt
            if k > 1.2:
                st["pops"].remove((i, pt))
                continue
            (bx, by), bc = PT_BALLOONS[i]
            r = 6 + 22 * min(1.0, k * 4)
            pts = [(bx + math.cos(a * math.pi / 6) * (r if a % 2 else r * 0.5),
                    by + math.sin(a * math.pi / 6) * (r if a % 2 else r * 0.5)) for a in range(12)]
            if k < 0.5:
                d.polygon(pts, fill=(255, 240, 120))
            self._xmas_party_say(d, bx, by - 14, "PENG!")
        if lid_top is not None and gag and t - gag[1] < 7:
            self._xmas_party_say(d, PT_STAND_X[2], PT_FLOOR - 96, "AAAH!")
        # Konfetti
        if o.get("confetti", True) and phase != "hide":
            if phase == "party" and not talk and new_beat and s["bass"] > 0.7:
                self._pt_confetti(st, 3 + int(5 * s["level"]))
            self._pt_confetti_step(st, dt, d)
        # Sprechblasen
        self._pt_talk(st, s, t, d, heads, phase, lt, talk)
        if phase == "hide":
            img = self._pt_dark(img, st, s, t, lt, o)
        elif phase == "surprise":
            img = self._pt_surprise(img, st, t, lt)
        return img

    # -- Bausteine des Ablaufs -------------------------------------------------- #
    @staticmethod
    def _pt_candles_out(gag, t):
        """Trickkerzen: dreimal ausgepustet, gehen jedes Mal wieder an."""
        if not gag or gag[0] != "kerzen":
            return 0.0
        lt = t - gag[1]
        for a in (2.6, 4.8, 7.0):
            if a <= lt < a + 1.0:
                return 1.0
        return 0.0

    @staticmethod
    def _pt_eaten(st, gag, t):
        if gag and gag[0] == "hund":
            return max(0.0, min(1.0, (t - gag[1] - 5.0) / 4.0))
        return st["eaten"]

    @staticmethod
    def _pt_dog_state(st, gag, t):
        """Hund: (x, Haltung, Sahne) oder None."""
        if gag and gag[0] == "hund":
            lt = t - gag[1]
            if lt < 5:
                return (WIDTH + 30 - (WIDTH + 30 - 112) * lt / 5, "walk", False)
            if lt < 9:
                return (112, "beg", lt > 6)
            k = min(1.0, (lt - 9) / 3)
            return (112 + (300 - 112) * k, "walk" if k < 1 else "lie", True)
        if st.get("dog") == "lie":
            return (300, "lie", True)
        return None

    def _pt_age_balloons(self, img, d, digits, t, s):
        font = self.__dict__.setdefault("_pt_digit_font", load_font(38, bold=True))
        x = 112
        for k, ch in enumerate(digits[:3]):
            yy = 64 + math.sin(t * 1.1 + k * 1.7) * 3 - s["bass"] * 3
            w = d.textlength(ch, font=font)
            d.line([(x + w / 2, yy + 42), (PT_GIFT_X, PT_FLOOR - 30)], fill=(90, 80, 70))
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                d.text((x + ox, yy + oy), ch, font=font, fill=(150, 110, 20))
            d.text((x, yy), ch, font=font, fill=(250, 210, 70))
            d.line([(x + 6, yy + 12), (x + 9, yy + 8)], fill=(255, 250, 220), width=2)
            x += w + 2

    def _pt_guests_draw(self, img, d, st, s, t, dt, phase, lt, gag, talk, o):
        """Gäste: verstecken (nicht gezeichnet, nur Augen in _pt_dark), aufspringen, tanzen, Helium, Gags."""
        if phase == "hide":
            return {}
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        energy = 0.4 + 0.6 * s["level"] if s.get("active") or s.get("demo") else 0.3
        ph = ((t - st["t0"]) / period) % 1.0
        heads = {}
        sitting = talk and s["t"] - s.get("talk_t", s["t"]) > 25
        startle = 0 <= t - st["pop_t"] < 0.7
        for i, spec in enumerate(PT_GUESTS):
            g = st["guests"][i]
            goal = PT_STAND_X[i]
            if gag and gag[0] == "kerzen" and i == 1 and t - gag[1] < PT_GAGS["kerzen"] - 1.5:
                goal = PT_CAKE_X + 46
            if gag and gag[0] == "geschenk" and 4 <= t - gag[1] < 7:
                goal = PT_STAND_X[i] + 14                                           # zurückweichen
            walking = abs(goal - g["x"]) > 1
            if walking:
                g["x"] += max(-PT_WALK * dt, min(PT_WALK * dt, goal - g["x"]))
            pose = dict(PT_POSES[(st["k"] + i * 2) % len(PT_POSES)])
            prev = g.get("pose")
            k = _smooth((t - st["t0"]) / 0.18)
            if prev is not None and not walking:
                pose = _mix_pose(prev, pose, k) if k < 1 else pose
            pose["bob"] = (1 + math.cos(2 * math.pi * ph)) / 2 * (2 + 5 * energy)
            pose["horn"] = max(0.0, 1 - (t - s.get("hat_t", -9)) / 0.25) if s.get("hats", 0) % 3 == i else 0.0
            pose["lean"] = math.sin(math.pi * (st["k"] + ph) + i) * 2 * energy
            if phase == "surprise":                                                 # aufspringen!
                if i == 2 and st["sleeper"] and lt < 2.4:
                    continue                                                        # verschläft es (Zzz in _pt_talk)
                jl = lt - (2.4 if i == 2 and st["sleeper"] else 0.0)
                jump = max(0.0, math.sin(min(1.0, jl / 0.6) * math.pi)) * 18
                pose = {"lh": (-8, -24), "rh": (8, -24), "spread": 6, "bob": jump, "mouth": 1.0, "horn": 1.0}
                if i == 2 and st["sleeper"]:
                    pose.update(lh=(-12, 8), rh=(13, 6), mouth=0.0, horn=0.0, hat_tilt=8)
            elif talk and (gag is None or gag[0] != "kerzen"):
                pose = {"lh": (-10, 10), "rh": (10, 10), "spread": 3, "bob": 0.0}
                if (int((t - s.get("talk_t", t)) / 2.5)) % 3 == i:
                    pose.update(mouth=1.0, lh=(-4, -6) if i == 1 else (-10, 10))
            elif walking:
                pose = {"lh": (-6, 10), "rh": (6, 10), "spread": 3 + 3 * math.sin(t * 12), "bob": abs(math.sin(t * 12)) * 2}
            if gag and gag[0] == "kerzen" and i == 1 and not walking:
                gl = t - gag[1]
                blowing = any(a - 0.8 <= gl < a + 0.2 for a in (2.6, 4.8, 7.0))
                red = min(1.0, max(0.0, (gl - 4.8) / 3))
                pose = {"lh": (-12, 2), "rh": (4, 12), "spread": 4, "bob": 0.0, "lean": -3, "cheeks": blowing,
                        "face": _lerp(spec["skin"], (230, 70, 60), red), "look": -1}
            if gag and gag[0] == "hund" and 6 <= t - gag[1] < 9 and i == 0:
                pose.update(lh=(-16, -8), rh=(4, 10), mouth=1.0, look=-1)          # „HEY!“
            if gag and gag[0] == "geschenk" and 4 <= t - gag[1] < 7:
                pose.update(lh=(-6, -22), rh=(6, -22), mouth=1.0, bob=2.0)
            if startle:
                pose.update(lh=(-8, -24), rh=(8, -24), mouth=1.0, bob=10 * math.sin((t - st["pop_t"]) / 0.7 * math.pi))
            g["pose"] = pose
            heads[i] = self._pt_guest(img, d, g["x"], PT_FLOOR, pose, spec, t, sit=sitting and not walking)[0]
        return heads

    def _pt_talk(self, st, s, t, d, heads, phase, lt, talk):
        """Sprechblasen: Psst (Versteck), verschlafen, Helium, Gags."""
        gag = st["gag"]
        if phase == "hide":
            n = int(lt / 7.0)
            if lt % 7.0 > 4.5 and lt > 3:
                return ("say", PT_HIDE_X[n % 3], PT_SOFA_BACK - 14, PT_HIDE_SAY[n % len(PT_HIDE_SAY)])
            return None
        if phase == "surprise":
            if st["sleeper"] and lt < 2.4:
                self._bal_bubble(d, (PT_STAND_X[2] - 10, PT_SOFA_BACK + 12), None, t)
            elif st["sleeper"] and lt >= 2.4 and 2 in heads:
                self._xmas_party_say(d, heads[2][0], heads[2][1] - 34, "… Überraschung?")
            return None
        if gag and gag[0] == "hund" and 6 <= t - gag[1] < 9 and 0 in heads:
            self._xmas_party_say(d, heads[0][0], heads[0][1] - 34, "HEY! Die Torte!")
        elif gag and gag[0] == "hund" and 10 <= t - gag[1] < 12:
            self._xmas_party_say(d, 250, PT_FLOOR - 30, "Burp.")
        elif gag and gag[0] == "kerzen" and 1 in heads:
            gl = t - gag[1]
            if 8.2 <= gl < 10.5:
                self._xmas_party_say(d, heads[1][0], heads[1][1] - 34, "Trickkerzen?!")
            elif 0.5 <= gl < 2.0:
                self._xmas_party_say(d, heads[1][0], heads[1][1] - 34, "Ich puste!")
            for a in (2.6, 4.8, 7.0):                                               # Pustewind
                if a - 0.8 <= gl < a + 0.2:
                    x0, y0 = heads[1][0] - 12, heads[1][1] + 4
                    for j in range(3):
                        d.line([(x0 - j * 2, y0 - 4 + j * 4), (x0 - 14 - j * 2, y0 - 6 + j * 4)], fill=(250, 250, 255))
        elif talk and heads:
            n = int((t - s.get("talk_t", t)) / 2.5)
            i = n % 3
            if i in heads:
                font = self.__dict__.setdefault("_pt_helium_font", load_font(9, bold=True))
                text = PT_HELIUM[n % len(PT_HELIUM)]
                hx, hy = heads[i][0], heads[i][1] - 30
                w = d.textlength(text, font=font) + 10
                bx = max(2, min(WIDTH - w - 2, hx - w / 2))
                wob = math.sin(t * 20) * 1.5                                        # zittrige Heliumblase
                d.rounded_rectangle([bx, hy + wob, bx + w, hy + 14 + wob], radius=7, fill=(236, 246, 255),
                                    outline=(150, 200, 250))
                d.text((bx + 5, hy + 2 + wob), text, font=font, fill=(60, 90, 160))
        return None

    def _pt_dark(self, img, st, s, t, lt, o):
        """Versteck: Raum dunkel, nur die Augen hinter dem Sofa (blinzeln auf hohe Schläge) und das Mondlicht."""
        dark = Image.blend(img, Image.new("RGB", img.size, (6, 8, 22)), 0.88)
        d = ImageDraw.Draw(dark)
        spots = [(x, PT_SOFA_BACK - 4) for x in PT_HIDE_X]
        if o.get("dog", True):
            spots.append((PT_SOFA[1] - 4, PT_FLOOR - 8))                           # Hund unterm Sofa
        for i, (x, y) in enumerate(spots):
            blink = 0 <= t - s.get("hat_t", -9) < 0.12 and (s.get("hats", 0) + i) % 4 == 0
            look = math.sin(t * 0.7 + i * 2.1) * 2
            pop = math.sin(min(1.0, max(0.0, (lt - i * 0.4) / 0.5)) * math.pi / 2)  # tauchen nacheinander auf
            yy = y + (1 - pop) * 6
            if pop < 0.2:
                continue
            for side in (-1, 1):
                ex = x + side * (3 if i == 3 else 4)
                if blink:
                    d.line([(ex - 2, yy), (ex + 2, yy)], fill=(200, 200, 210))
                else:
                    d.ellipse([ex - 2.5, yy - 2, ex + 2.5, yy + 2], fill=(236, 236, 230))
                    d.ellipse([ex - 1 + look, yy - 1, ex + 1 + look, yy + 1], fill=(10, 10, 14))
        say = self._pt_talk(st, s, t, d, {}, "hide", lt, False)
        if say:
            self._xmas_party_say(d, say[1], say[2], say[3])
        return dark

    def _pt_surprise(self, img, st, t, lt):
        """Licht an (kurzer Lichtstoß), „ÜBERRASCHUNG!“ in großen Buchstaben."""
        if lt < 0.3:
            k = lt / 0.3
            img = Image.blend(Image.blend(img, Image.new("RGB", img.size, (6, 8, 22)), 0.84 * (1 - k)),
                              Image.new("RGB", img.size, (255, 250, 230)), 0.35 * k)
        if lt < 2.8:
            d = ImageDraw.Draw(img)
            font = self.__dict__.setdefault("_pt_big_font", load_font(26, bold=True))
            text = "ÜBERRASCHUNG!"
            sc = min(1.0, lt / 0.25)
            w = d.textlength(text, font=font)
            x, y = (WIDTH - w) / 2, 64 - 6 * math.sin(min(1.0, lt / 0.4) * math.pi)
            if sc > 0.3:
                d.rounded_rectangle([x - 10, y - 4, x + w + 10, y + 34], radius=12, fill=(255, 250, 236),
                                    outline=(230, 60, 100), width=3)
                hue = int(lt * 8) % 3
                d.text((x, y), text, font=font, fill=((230, 50, 90), (40, 120, 220), (230, 150, 20))[hue])
        return img

    def _pt_confetti(self, st, n, burst=False):
        rng = st["rng"]
        rows = []
        for _ in range(n):
            if burst:
                x = rng.choice(PT_HIDE_X) + rng.uniform(-14, 14)
                rows.append([x, PT_SOFA_BACK - 10, rng.uniform(-70, 70), rng.uniform(-190, -90), rng.randrange(6),
                             rng.uniform(0, 6)])
            else:
                rows.append([rng.uniform(0, WIDTH), -4, rng.uniform(-10, 10), rng.uniform(20, 50), rng.randrange(6),
                             rng.uniform(0, 6)])
        st["confetti"] = np.concatenate([st["confetti"], np.array(rows, np.float32)])[-160:]

    @staticmethod
    def _pt_confetti_step(st, dt, d):
        c = st["confetti"]
        if not len(c):
            return
        c[:, 3] = np.minimum(c[:, 3] + 160 * dt, 45)                                # fallen, bremsen
        c[:, 2] *= max(0.0, 1 - 1.5 * dt)
        c[:, 0] += c[:, 2] * dt + np.sin(c[:, 5] * 3) * 0.6
        c[:, 1] += c[:, 3] * dt
        c[:, 5] += dt * 4
        st["confetti"] = c = c[c[:, 1] < PT_FLOOR + 6]
        cols = [(240, 70, 90), (250, 210, 60), (70, 150, 240), (110, 210, 100), (230, 120, 230), (255, 255, 255)]
        for x, y, _, _, ci, sp in c:
            w = 1 + abs(math.sin(sp)) * 2
            d.rectangle([x, y, x + w, y + 2], fill=cols[int(ci) % 6])
