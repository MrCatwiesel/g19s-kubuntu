"""Visualisierung „Tänzerin“ (Stil-ID dancer): eine Ballerina an der Stange im Tanzstudio – Spiegelwand mit
Spiegelbild, Schallschutz-Paneele, Holzboden. Die Figur ist räumlich schattiert wie die Weihnachtsfiguren
(_blob/_limb, Arme und Beine über Zielpunkte mit _ik): weinrotes Samttrikot mit Glitzersteinen, schwarzer
Chiffonrock, der mit Trägheit nachschwingt (Bass bläht ihn auf), Spitzenschuhe.
Musik: Bassschlag → nächste Haltung der Choreografie (BAL_CHOREO), hoher Schlag (Hi-Hat/Snare) → kleiner Akzent mit
Hand und Kopf, Höhepunkt (Musik deutlich lauter) → Drehung um die Stange. Wortbeitrag → sie langweilt sich an der
Stange (lehnt, gähnt, dehnt sich, schaut auf die Uhr, setzt sich nach 30 s) – Ablauf aus _bored_pose (seite_visual).
"""

BAL_POLE_X = 112
BAL_FLOOR = VIS_H - 12                  # Fußpunkt der Tänzerin
BAL_HIP_DX = 46                         # Abstand Hüfte – Stange
BAL_SKIN = (172, 114, 84)
BAL_LEO = (128, 16, 40)                 # Samttrikot (Option color ersetzt es)
BAL_SKIRT = (16, 14, 20)
BAL_SHOE = (212, 158, 126)
BAL_HAIR = (38, 24, 18)
BAL_TORSO, BAL_UA, BAL_FA, BAL_TH, BAL_SH = 37, 22, 21, 35, 34    # ≈ 7,5 Kopflängen, lange Beine
BAL_MIRROR = (6, 14, 232, BAL_FLOOR - 58)   # Spiegelwand x0, y0, x1, y1
BAL_SPIN = 2.6                          # Sekunden für eine Drehung um die Stange
# Haltungen: Hände relativ zur Schulter (lp/rp = Anteil „Hand an der Stange“), Füße relativ zum Hüftgelenk,
# lb/rb = Richtung der Kniebeuge, lean = Neigung des Oberkörpers (+ nach rechts), head = Kopfneigung,
# rise = auf der Spitze (0/1), dip = Hüfte tiefer (Plié), hx = Hüfte seitlich
BAL_POSES = {
    "passe": {"lh": (-30, 6), "lp": 1, "rh": (-14, -38), "rp": 0, "lf": (-8, 25), "lb": 1, "rf": (1, 66), "rb": -1,
              "lean": -2, "head": -10, "rise": 1, "dip": 0, "hx": 0},
    "fifth": {"lh": (10, -40), "lp": 0, "rh": (-10, -40), "rp": 0, "lf": (5, 66), "lb": 1, "rf": (-5, 66), "rb": -1,
              "lean": 0, "head": 8, "rise": 1, "dip": 0, "hx": 0},
    "arabesque": {"lh": (-30, 4), "lp": 1, "rh": (30, -26), "rp": 0, "lf": (2, 66), "lb": 1, "rf": (56, -8), "rb": 1,
                  "lean": -16, "head": -6, "rise": 1, "dip": 0, "hx": -4},
    "attitude": {"lh": (-30, 4), "lp": 1, "rh": (-6, -40), "rp": 0, "lf": (2, 66), "lb": 1, "rf": (40, 6), "rb": 1,
                 "lean": -12, "head": 10, "rise": 1, "dip": 0, "hx": -2},
    "battement": {"lh": (-30, 4), "lp": 1, "rh": (32, -6), "rp": 0, "lf": (2, 66), "lb": 1, "rf": (52, -30), "rb": -1,
                  "lean": -14, "head": -12, "rise": 1, "dip": 0, "hx": -4},
    "plie": {"lh": (-30, 6), "lp": 1, "rh": (34, 4), "rp": 0, "lf": (-16, 52), "lb": 1, "rf": (16, 52), "rb": -1,
             "lean": 0, "head": 6, "rise": 0, "dip": 12, "hx": 0},
    "lean": {"lh": (-30, -18), "lp": 1, "rh": (-40, 12), "rp": 0.6, "lf": (-30, 52), "lb": 1, "rf": (6, 66), "rb": -1,
             "lean": 18, "head": 16, "rise": 1, "dip": 0, "hx": 6},
    "port": {"lh": (-30, 4), "lp": 1, "rh": (26, -30), "rp": 0, "lf": (3, 66), "lb": 1, "rf": (-4, 66), "rb": -1,
             "lean": 8, "head": 14, "rise": 1, "dip": 0, "hx": 0},
}
BAL_CHOREO = ["passe", "fifth", "arabesque", "plie", "battement", "passe", "port", "attitude", "lean", "fifth"]
# Haltungen für Figuren an der Stange (BAL_MOVES)
BAL_POSES.update({
    "fireman": {"lh": (-30, -36), "lp": 1, "rh": (-30, -14), "rp": 1, "lf": (14, 26), "lb": -1, "rf": (20, 24), "rb": -1,
                "lean": -10, "head": -14, "rise": 1, "dip": 0, "hx": 0},
    "chair": {"lh": (-30, -32), "lp": 1, "rh": (32, -18), "rp": 0, "lf": (30, 22), "lb": -1, "rf": (36, 20), "rb": -1,
              "lean": -8, "head": 10, "rise": 1, "dip": 0, "hx": 0},
    "hook": {"lh": (-30, -22), "lp": 1, "rh": (40, -8), "rp": 0, "lf": (-46, 16), "lb": 1, "rf": (34, 40), "rb": -1,
             "lean": 22, "head": 22, "rise": 1, "dip": 0, "hx": 0},
    "polesit": {"lh": (-14, -40), "lp": 1, "rh": (-20, -18), "rp": 1, "lf": (-26, 28), "lb": 1, "rf": (-10, 40),
                "rb": 1, "lean": -12, "head": -10, "rise": 1, "dip": 0, "hx": 0},
    "split": {"lh": (-30, -30), "lp": 1, "rh": (8, -40), "rp": 0, "lf": (2, 66), "lb": 1, "rf": (26, -56), "rb": -1,
              "lean": -20, "head": -14, "rise": 1, "dip": 0, "hx": -2},           # Seitspagat im Stand
})
# Figuren an der Stange: Dauer (s), Haltung, Umlauf um die Stange (Anteil Kreis), Abstand zur Stange (Anteil),
# Hub (Pixel nach oben). Alle 8 Schläge kommt die nächste; „spin“ zusätzlich, wenn die Musik deutlich lauter wird.
BAL_MOVES = {
    "spin": (2.6, "attitude", 1.0, 1.0, 0),
    "fireman": (2.6, "fireman", 1.0, 0.75, 16),
    "chair": (2.6, "chair", 1.0, 0.8, 12),
    "hook": (2.4, "hook", 0.45, 0.7, 4),
    "climb": (4.2, "polesit", 0.0, 0.45, 36),
    "wave": (2.6, "lean", 0.0, 0.7, 0),
    "pirouette": (1.6, "fifth", 0.0, 1.0, 0),
    "split": (3.0, "split", 0.0, 0.85, 0),
}
BAL_MOVE_ORDER = ["fireman", "pirouette", "hook", "chair", "climb", "wave", "split", "pirouette"]
# Nach einem Liedwechsel (Titel neu, Musik nach Pause oder Wortbeitrag) erst zuhören: tanzen, sobald so viele Schläge
# gleichmäßig kommen (Abweichung ≤ 12 %), spätestens nach BAL_LISTEN_MAX Sekunden
BAL_LISTEN_BEATS = 5
BAL_LISTEN_MAX = 8.0
BAL_POSES["listen"] = {"lh": (-30, 6), "lp": 1, "rh": (-6, 28), "rp": 0, "lf": (-4, 66), "lb": 1, "rf": (10, 66),
                       "rb": -1, "lean": 3, "head": 6, "rise": 0, "dip": 0, "hx": 0}
BAL_HAIR_COLORS = {
    "dark": (38, 24, 18), "black": (14, 12, 14), "brown": (92, 56, 30), "auburn": (130, 52, 24), "red": (176, 50, 30),
    "blond": (214, 176, 102), "platinum": (232, 222, 196), "silver": (184, 186, 196), "pink": (232, 104, 168),
    "blue": (60, 110, 220),
}
# Langeweile bei Wortbeiträgen (Namen wie _bored_pose: cross, yawn, hips = dehnen, watch, sit)
BAL_BORED = {
    "cross": {"lh": (12, 18), "lp": 0, "rh": (-12, 18), "rp": 0, "lf": (-12, 66), "lb": 1, "rf": (4, 66), "rb": -1,
              "lean": -8, "head": 8, "rise": 0, "dip": 0, "hx": -16},
    "yawn": {"lh": (12, 18), "lp": 0, "rh": (-14, -16), "rp": 0, "lf": (-12, 66), "lb": 1, "rf": (4, 66), "rb": -1,
             "lean": -8, "head": -12, "rise": 0, "dip": 0, "hx": -16},
    "hips": {"lh": (-34, -6), "lp": 1, "rh": (-38, -2), "rp": 0, "lf": (-52, -6), "lb": -1, "rf": (2, 66), "rb": -1,
             "lean": -26, "head": -10, "rise": 0, "dip": 0, "hx": 4},
    "watch": {"lh": (-30, 6), "lp": 1, "rh": (-16, -6), "rp": 0, "lf": (-2, 66), "lb": 1, "rf": (6, 66), "rb": -1,
              "lean": 2, "head": 14, "rise": 0, "dip": 0, "hx": -6},
    "sit": {"lh": (-20, 20), "lp": 0, "rh": (18, 24), "rp": 0, "lf": (40, 4), "lb": -1, "rf": (52, 2), "rb": -1,
            "lean": -10, "head": 18, "rise": 0, "dip": 54, "hx": -18},
}


def _bal_mix(a, b, k):
    out = {}
    for key, va in a.items():
        vb = b[key]
        out[key] = tuple(x + (y - x) * k for x, y in zip(va, vb)) if isinstance(va, tuple) else va + (vb - va) * k
    return out


class BalletVisual:
    # -- Studio -------------------------------------------------------------- #
    def _bal_studio(self, s, o, dim):
        """Wand mit Paneelen, Spiegelwand, Holzboden (zwischengespeichert) und auf Wunsch warmes Bühnenlicht."""
        bg = self.__dict__.get("_bal_bg")
        if bg is None:
            ys = np.linspace(0, 1, HEIGHT)[:, None, None]
            arr = np.broadcast_to(np.array([70, 64, 62], np.float32) * (1 - ys) + np.array([46, 42, 42], np.float32) * ys,
                                  (HEIGHT, WIDTH, 3)).copy()
            img = Image.fromarray(arr.astype(np.uint8), "RGB")
            d = ImageDraw.Draw(img)
            for x in range(-20, WIDTH, 58):                      # Schallschutz-Paneele
                d.rounded_rectangle([x + 4, 6, x + 52, 70], radius=3, fill=(84, 78, 74), outline=(58, 54, 52))
                d.rounded_rectangle([x + 4, 76, x + 52, BAL_FLOOR - 62], radius=3, fill=(80, 74, 70), outline=(58, 54, 52))
            x0, y0, x1, y1 = BAL_MIRROR                          # Spiegel: dunkler, kühler Raum dahinter
            m = np.broadcast_to(np.array([34, 36, 44], np.float32) * (1 - np.linspace(0, 1, y1 - y0)[:, None, None] * 0.3),
                                (y1 - y0, x1 - x0, 3)).astype(np.uint8)
            img.paste(Image.fromarray(np.ascontiguousarray(m), "RGB"), (x0, y0))
            for k in range(3):                                   # Spiegelbild der Paneele, schwach
                px = x0 + 20 + k * 74
                d.rectangle([px, y0 + 8, px + 40, y0 + 56], fill=(42, 44, 52))
            d.rectangle([x0, y1 - 26, x1, y1], fill=(40, 30, 26))   # Boden im Spiegel
            d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], outline=(150, 150, 158), width=2)
            for k in range(2):                                   # Lichtreflexe auf dem Glas
                gx = x0 + 60 + k * 90
                d.line([(gx, y0 + 4), (gx + 24, y1 - 30)], fill=(58, 62, 74), width=6)
            top = BAL_FLOOR - 56                                 # Holzboden mit Dielen und Glanz
            fl = np.zeros((HEIGHT - top, WIDTH, 3), np.float32)
            fl[:] = np.array([92, 54, 32], np.float32) * np.linspace(0.7, 1.05, HEIGHT - top)[:, None, None]
            img.paste(Image.fromarray(fl.astype(np.uint8), "RGB"), (0, top))
            d.line([(0, top), (WIDTH, top)], fill=(140, 136, 132), width=2)     # Sockelleiste
            for j in range(1, 7):
                y = top + int((j / 7) ** 1.6 * (HEIGHT - top))
                d.line([(0, y), (WIDTH, y)], fill=(70, 40, 24))
            for j in range(-8, 9):                               # Dielenfugen in Fluchtperspektive
                d.line([(WIDTH / 2 + j * 22, top), (WIDTH / 2 + j * 60, HEIGHT)], fill=(76, 44, 26))
            bg = self._bal_bg = img
        img = bg.copy()
        if o.get("stage", True):                                 # warmer Lichtkegel, pulsiert mit dem Bass
            k = 0.25 if dim else 0.55 + 0.45 * s["bass"]
            mask = Image.new("L", (WIDTH, HEIGHT), 0)
            md = ImageDraw.Draw(mask)
            cx = BAL_POLE_X + BAL_HIP_DX - 6
            md.polygon([(cx - 10, 0), (cx + 10, 0), (cx + 80, BAL_FLOOR + 6), (cx - 80, BAL_FLOOR + 6)], fill=int(34 * k))
            md.ellipse([cx - 82, BAL_FLOOR - 12, cx + 82, BAL_FLOOR + 14], fill=int(80 * k))
            img.paste((255, 214, 160), (0, 0, WIDTH, HEIGHT), mask)
            hue = (s["beats"] % 8) / 8                           # farbiges Streiflicht an der Wand, weich
            self._blob(img, WIDTH - 30, 70, 150, 150, _hue(hue, 0.7, 1.0), alpha=round(0.3 * k, 2), flat=True)
        return img

    def _bal_pole(self, img, d, x, top=0, bottom=BAL_FLOOR + 2):
        """Verchromte Stange mit Fußplatte."""
        for dx, c in ((-3, (110, 114, 124)), (-2, (170, 174, 184)), (-1, (235, 238, 245)), (0, (200, 204, 214)),
                      (1, (150, 154, 164)), (2, (96, 100, 110)), (3, (70, 72, 80))):
            d.line([(x + dx, top), (x + dx, bottom)], fill=c)
        self._blob(img, x, bottom + 1, 26, 6, (180, 184, 194), gloss=1.0)

    # -- Figur --------------------------------------------------------------- #
    def _bal_figure(self, img, d, hip, pose, t, skirt, leo, pole_x, hair=BAL_HAIR):
        """Ballerina zeichnen: Rock (hinten), Beine, Rumpf mit Trikot, Arme, Kopf. Gibt Kopf und Hände zurück."""
        hx, hy = hip
        lean = math.radians(pose["lean"])
        sitting = pose["dip"] > 40
        if skirt:                                                 # Chiffonrock: schwebt hinter den Beinen
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            waist = (hx + math.sin(lean) * 12, hy - 12)
            top = [(waist[0] - 13, waist[1]), (waist[0] + 13, waist[1])]
            hem = skirt
            ld.polygon([top[0]] + hem + [top[1]], fill=BAL_SKIRT + (180,))
            for i in range(1, len(hem) - 1, 2):                   # Falten
                ld.line([(waist[0] - 12 + 24 * i / (len(hem) - 1), waist[1] + 2), hem[i]], fill=(64, 60, 72, 150))
            ld.line(hem, fill=(84, 80, 92, 200), width=1)
            img.alpha_composite(layer) if img.mode == "RGBA" else img.paste(layer, (0, 0), layer)
        feet = []
        for side, f, b in ((-1, "lf", "lb"), (1, "rf", "rb")):    # Beine mit Spitzenschuhen
            hj = (hx + side * 7, hy + 2)
            tx, ty = pose[f]
            knee, foot = _ik(hj, (hj[0] + tx, hj[1] + ty), BAL_TH, BAL_SH, pose[b])
            self._taper(img, hj, knee, 12, 8, BAL_SKIN)               # Oberschenkel verjüngt sich zum Knie
            calf = (knee[0] + (foot[0] - knee[0]) * 0.32, knee[1] + (foot[1] - knee[1]) * 0.32)
            self._taper(img, knee, calf, 8, 9, BAL_SKIN)              # Wade leicht gerundet
            self._taper(img, calf, foot, 9, 5, BAL_SKIN)              # schlanke Fessel
            dx, dy = foot[0] - knee[0], foot[1] - knee[1]
            n = math.hypot(dx, dy) or 1
            point = pose["rise"] > 0.5 or sitting or ty < 40      # auf der Spitze: Fuß verlängert das Bein
            tip = (foot[0] + dx / n * 9, foot[1] + dy / n * 9) if point else (foot[0] + side * 8, foot[1] + 2)
            self._limb(img, foot, tip, 7, BAL_SHOE, gloss=0.9)
            d.line([(foot[0] - 3, foot[1] - 4), (foot[0] + 3, foot[1] - 1)], fill=(236, 190, 160))   # Bänder
            feet.append(tip)
        self._blob(img, hx, hy - 2, 24, 17, leo, gloss=0.6)         # Becken im Trikot
        chest = (hx + math.sin(lean) * 22, hy - 24)
        neck = (hx + math.sin(lean) * BAL_TORSO, hy - BAL_TORSO * math.cos(lean))
        self._blob(img, (hx + chest[0]) / 2, (hy + chest[1]) / 2, 14, 20, leo, ang=math.degrees(lean), gloss=0.6)  # Taille
        self._blob(img, chest[0], chest[1], 22, 27, leo, ang=math.degrees(lean), gloss=0.7)     # Brustkorb
        d.polygon([(neck[0] - 7, neck[1] + 3), (neck[0] + 7, neck[1] + 3), (chest[0], chest[1] + 8)],
                  fill=tuple(int(c * 0.8) for c in BAL_SKIN))       # transparenter V-Einsatz
        for k in range(6):                                          # Glitzersteine: V-Ausschnitt und Gürtel
            f = k / 5
            for side in (-1, 1):
                x = neck[0] + side * 7 * (1 - f) + (chest[0] - neck[0]) * f
                y = neck[1] + 3 + (chest[1] + 8 - neck[1] - 3) * f
                d.point((x, y), fill=(255, 240, 250))
        wy = hy - 12
        wx = hx + math.sin(lean) * 12
        for k in range(-6, 7):
            d.point((wx + k * 2, wy + (k % 2)), fill=(255, 236, 246) if k % 2 else (220, 180, 200))
        hands = []
        for side, h, p in ((-1, "lh", "lp"), (1, "rh", "rp")):     # Arme
            sh = (neck[0] + side * 13, neck[1] + 5)
            rx, ry = pose[h]
            tgt = (sh[0] + rx, sh[1] + ry)
            if pose[p] > 0:                                         # Hand an der Stange
                tgt = (tgt[0] + (pole_x + 3 - tgt[0]) * pose[p], tgt[1])
            elbow, hand = _ik(sh, tgt, BAL_UA, BAL_FA, side)
            self._blob(img, sh[0], sh[1], 8, 8, BAL_SKIN, gloss=0.5)     # Schulter (Trikot ärmellos)
            self._taper(img, sh, elbow, 7, 5.5, BAL_SKIN)             # Oberarm
            self._taper(img, elbow, hand, 5.5, 4, BAL_SKIN)           # Unterarm, zartes Handgelenk
            self._blob(img, hand[0], hand[1], 6, 6, BAL_SKIN, gloss=0.4)
            hands.append(hand)
        self._taper(img, (neck[0], neck[1] + 4), (neck[0], neck[1] - 9), 7, 5.5, BAL_SKIN)        # langer Hals
        d.line([(neck[0] - 5, neck[1] - 1), (neck[0] + 5, neck[1] - 1)], fill=leo, width=3)   # Halsband
        for k in range(-2, 3):
            d.point((neck[0] + k * 2, neck[1] - 1), fill=(255, 240, 250))
        hd = math.radians(pose["head"] + pose["lean"])
        head = (neck[0] + math.sin(hd) * 11, neck[1] - 15)
        self._blob(img, head[0], head[1], 15, 19, BAL_SKIN, gloss=0.4)
        self._blob(img, head[0] - math.sin(hd) * 2, head[1] - 7, 18, 11, hair, gloss=0.7)     # Haar
        self._blob(img, head[0] - math.sin(hd) * 4 - 2, head[1] - 12, 10, 9, hair, gloss=0.8)  # Dutt
        ex = head[0] + math.sin(hd) * 3
        for side in (-1, 1):
            d.line([(ex + side * 3 - 1, head[1] - 1), (ex + side * 3 + 1, head[1] - 1)], fill=(40, 24, 20))
        d.point((ex, head[1] + 5), fill=(150, 60, 60))
        return head, hands, feet

    def _taper(self, img, p1, p2, w1, w2, color):
        """Glied, das sich von Breite w1 auf w2 verjüngt: das ganze Glied in der schmalen Breite, darüber der kräftige
        Teil zur dicken Seite hin (weit überlappend, wenig Glanz – keine sichtbaren Streifen)."""
        thin, thick = (p2, p1) if w1 >= w2 else (p1, p2)
        wt, wk = min(w1, w2), max(w1, w2)
        self._limb(img, p1, p2, wt, color, gloss=0.25)
        if wk - wt > 0.6:
            mid = (thick[0] + (thin[0] - thick[0]) * 0.6, thick[1] + (thin[1] - thick[1]) * 0.6)
            self._limb(img, thick, mid, wk, color, gloss=0.25)

    @staticmethod
    def _bal_listen_start(st, s, t):
        st["listen"] = {"t": t, "beats": [], "last": s["beats"]}
        st["move"] = None

    @staticmethod
    def _bal_listen(st, s, t):
        """Schläge sammeln; True, sobald BAL_LISTEN_BEATS gleichmäßig kommen (Tempo → st["tempo"]) oder die
        Wartezeit um ist. Dann endet das Zuhören."""
        li = st["listen"]
        if s["beats"] != li["last"]:
            li["last"] = s["beats"]
            li["beats"].append(s.get("beat_t", t))
        b = li["beats"][-BAL_LISTEN_BEATS:]
        if len(b) >= BAL_LISTEN_BEATS:
            gaps = sorted(y - x for x, y in zip(b, b[1:]))
            m = gaps[len(gaps) // 2]
            if 0.25 <= m <= 1.2 and all(abs(gp - m) <= 0.12 * m for gp in gaps):
                st["tempo"] = m
                st.pop("listen")
                return True
        if t - li["t"] >= BAL_LISTEN_MAX:
            st.pop("listen")
            return True
        return False

    # -- Rock: Saum mit Trägheit -------------------------------------------- #
    def _bal_skirt(self, st, hip, lean, dt, flare, swirl, sitting):
        """Saumpunkte (links → rechts) mit Feder und Dämpfung; folgen der Taille mit Verzögerung."""
        n = 9
        waist = (hip[0] + math.sin(math.radians(lean)) * 12, hip[1] - 12)
        length = 40 if sitting else 66
        rest = []
        for i in range(n):
            u = i / (n - 1) * 2 - 1                                 # −1 … 1
            spread = 18 + 30 * flare
            side = 1.25 if u > 0 else 0.85                          # wie im Studio: mehr Stoff nach rechts
            x = waist[0] + u * spread * side + swirl * 34 * (1 - abs(u)) + 10 * u * abs(u)
            y = waist[1] + length * (0.92 + 0.08 * math.cos(u * 3)) - 22 * flare * abs(u) - abs(swirl) * 18 * abs(u)
            rest.append((x, y))
        pts = st.get("hem")
        if pts is None or len(pts) != n:
            st["hem"] = [list(p) + [0.0, 0.0] for p in rest]
            pts = st["hem"]
        steps = max(1, int(dt / 0.02))
        h = dt / steps
        for _ in range(steps):
            for p, r in zip(pts, rest):
                ax = (r[0] - p[0]) * 90 - p[2] * 9
                ay = (r[1] - p[1]) * 90 - p[3] * 9
                p[2] += ax * h
                p[3] += ay * h
                p[0] += p[2] * h
                p[1] += p[3] * h
        return [(p[0], p[1]) for p in pts]

    # -- Stil ---------------------------------------------------------------- #
    @vis_style("dancer")
    def vis_dancer(self, s, o, color):
        t = s["t"]
        st = self._vstate("dancer", lambda: {"k": 0, "beats": s["beats"], "hats": s.get("hats", 0), "t0": t,
                                              "from": BAL_POSES["passe"], "to": BAL_POSES["passe"], "dur": 0.25,
                                              "accent": 0.0, "spin_t": -99.0, "avg": None})
        dt = self._vis_dt(st, t)
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        moving = s.get("active") or (s.get("demo") and not s.get("idle"))
        bored = _bored_pose(t - s.get("talk_t", t)) if s.get("talk") else None

        def go(pose, dur):
            cur = _bal_mix(st["from"], st["to"], _smooth((t - st["t0"]) / st["dur"]))
            st.update({"from": cur, "to": pose, "t0": t, "dur": dur})

        if not s.get("demo"):                                     # Liedwechsel? Dann erst den Takt hören
            song = self.__dict__.get("_vis_song") or ""
            changed = st.get("song") not in (None, song) and bool(song)
            st["song"] = song
            gap = t - st.get("seen", t) > 1.5                     # Musik setzt nach einer Pause wieder ein
            st["seen"] = t
            if (changed or gap) and not bored:
                self._bal_listen_start(st, s, t)
        if bored:                                                 # Wortbeitrag: Langeweile an der Stange
            if st.get("bored") != bored:
                go(BAL_BORED[bored], 0.7)
                st["bored"] = bored
            st["beats"] = s["beats"]
            st.pop("listen", None)
            energy = 0.0
        elif st.get("listen"):                                    # zuhören: nicken und mit dem Fuß tippen
            if st.pop("bored", None) or st["to"] is not BAL_POSES["listen"]:
                go(BAL_POSES["listen"], 0.5)
            self._bal_listen(st, s, t)                            # Takt gefunden → ab dem nächsten Schlag tanzen
            st["beats"] = s["beats"]
            energy = 0.2
            period = st.get("tempo") or period
        else:
            if st.pop("bored", None):
                if not s.get("demo"):
                    self._bal_listen_start(st, s, t)             # nach dem Wortbeitrag: erst zuhören
                else:
                    go(BAL_POSES[BAL_CHOREO[st["k"] % len(BAL_CHOREO)]], 0.35)
            period = st.get("tempo") or period
            if not st.get("listen") and (s["beats"] != st["beats"] or (moving and t - st["t0"] > period * 2.2)):
                st["beats"] = s["beats"]
                st["k"] += 1
                go(BAL_POSES[BAL_CHOREO[st["k"] % len(BAL_CHOREO)]], min(0.4, period * 0.6))
                mv = st.get("move")
                if st["k"] % 8 == 4 and moving and (mv is None or t - mv[1] > BAL_MOVES[mv[0]][0]):
                    st["mi"] = st.get("mi", -1) + 1                  # nächste Figur an der Stange
                    st["move"] = (BAL_MOVE_ORDER[st["mi"] % len(BAL_MOVE_ORDER)], t)
            energy = 0.35 + 0.65 * s["level"] if moving else 0.2
        hats = s.get("hats", 0)                                   # hoher Schlag: Akzent
        if hats != st["hats"]:
            st["hats"] = hats
            if not bored and s.get("hat", 0) >= 0.3:
                st["accent"] = 1.0
        st["accent"] *= math.exp(-dt * 9)
        avg = st["avg"]                                           # Höhepunkt: Drehung um die Stange
        st["avg"] = s["level"] if avg is None else avg + (s["level"] - avg) * min(1.0, dt / 6)     # langsam (≈ 6 s)
        fast = st.get("fast")
        st["fast"] = fast = s["level"] if fast is None else fast + (s["level"] - fast) * min(1.0, dt / 0.6)
        listening = bool(st.get("listen"))
        if listening:
            st["move"] = None
        if not bored and not listening and moving and avg is not None and fast > avg * 1.25 + 0.05 \
                and t - st["spin_t"] > 8:
            st["spin_t"] = t
            st["move"] = ("spin", t)                                 # Höhepunkt: Drehung um die Stange
        pose = _bal_mix(st["from"], st["to"], _smooth((t - st["t0"]) / st["dur"]))
        mv = st.get("move")
        ang, radius, lift, turn = 0.0, 1.0, 0.0, False
        spinning = False
        if mv and not bored:
            dur, mpose, circle, radius, hub = BAL_MOVES[mv[0]]
            mk = (t - mv[1]) / dur
            if 0 <= mk < 1:
                spinning = True
                w = min(1.0, mk * 6, (1 - mk) * 6)
                target = dict(BAL_POSES[mpose])
                if mv[0] == "wave":                                  # Körperwelle an der Stange
                    target["lean"] = 10 + 16 * math.sin(mk * 4 * math.pi)
                    target["dip"] = 6 * max(0.0, math.sin(mk * 4 * math.pi + 1))
                if mv[0] == "hook":                                  # hinausschwingen und zurück
                    ang = math.sin(mk * math.pi) * circle * 2 * math.pi
                else:
                    ang = _smooth(mk) * circle * 2 * math.pi
                pose = _bal_mix(pose, target, w)
                radius = 1 + (radius - 1) * w
                lift = hub * math.sin(mk * math.pi) ** (0.6 if mv[0] == "climb" else 1)
                turn = mv[0] == "pirouette" and 0.25 <= mk < 0.75   # Pirouette: halbe Zeit von hinten/anders herum
                spin_k = mk
            else:
                st["move"] = None
        pose = dict(pose)
        if listening:                                             # nickt im Takt, Fuß tippt
            nod = math.exp(-max(0.0, t - s.get("beat_t", -9)) * 8)
            pose["head"] += 12 * nod
            pose["rf"] = (pose["rf"][0], pose["rf"][1] - 6 * nod)
        elif not bored:                                           # Atmen, Port de bras, Akzent
            a = st["accent"]
            pose["rh"] = (pose["rh"][0], pose["rh"][1] - 7 * a + math.sin(t * 2.2) * 3 * energy)
            pose["head"] += 10 * a + math.sin(t * 1.7) * 4 * energy
            phase = ((t - st["t0"]) / period) % 1.0
            pose["dip"] += (1 - pose["rise"]) * math.cos(2 * math.pi * phase) * 3 * energy
        orbit = BAL_HIP_DX * radius * math.cos(ang)
        depth = math.sin(ang)                                     # > 0: hinter der Stange
        sitting = pose["dip"] > 40
        rise = 6 * pose["rise"]
        hip = (BAL_POLE_X + orbit + pose["hx"] * (1 if orbit >= 0 else -1),
               BAL_FLOOR - BAL_TH - BAL_SH - 1 - rise + pose["dip"] - lift)
        flip = (orbit < 0) != turn
        if flip:                                                  # auf der anderen Seite: gespiegelte Haltung
            pose = {**pose, "lean": -pose["lean"], "head": -pose["head"],
                    "lh": (-pose["rh"][0], pose["rh"][1]), "rh": (-pose["lh"][0], pose["lh"][1]),
                    "lp": pose["rp"], "rp": pose["lp"], "lf": (-pose["rf"][0], pose["rf"][1]),
                    "rf": (-pose["lf"][0], pose["lf"][1]), "lb": -pose["rb"], "rb": -pose["lb"]}
        dx = hip[0] - st.get("hip_x", hip[0])                     # Rock: Fliehkraft und Nachschwingen
        st["hip_x"] = hip[0]
        swirl = max(-1.0, min(1.0, -dx / max(dt, 1e-3) / 120)) if dt > 0 else 0.0
        flare = (0.15 + 0.6 * s["bass"] * energy) if not bored else 0.05
        if spinning:
            flare += 0.5 * math.sin(spin_k * math.pi) * (1.0 if ang or turn else 0.4)
        hem = self._bal_skirt(st, hip, pose["lean"], dt, flare, swirl, sitting)
        leo = tuple(o["color"]) if o.get("color") else BAL_LEO
        img = self._bal_studio(s, o, bool(bored))
        show = o.get("show", "off") if not bored else "off"       # Lichtshow (im Wortbeitrag ruhig)
        if show in ("beams", "club"):
            if show == "club":                                    # Disco: Raum abgedunkelt
                img = Image.blend(img, Image.new("RGB", img.size, (4, 3, 10)), 0.6)
            n = int(o["beams"]) if str(o.get("beams")).isdigit() else 5
            beams = self._lights_beams(s, t, n, Image.new("RGB", (WIDTH, VIS_H), (0, 0, 0)),
                                       dots=40 if show == "club" else 0)
            if show == "beams":
                beams = beams.point(lambda v: v * 0.55)
            img.paste(ImageChops.add(img.crop((0, 0, WIDTH, VIS_H)), beams), (0, 0))
        fig = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fig)
        shadow_x = hip[0]
        sw = (56 if not sitting else 70) * (1 - min(0.4, lift / 120))     # Schatten wird kleiner, wenn sie klettert
        self._blob(fig, shadow_x, BAL_FLOOR + 3, sw, 8, (30, 18, 12), gloss=0, alpha=0.6, flat=True)
        behind = depth > 0.15 and spinning
        if not behind:
            self._bal_pole(fig, fd, BAL_POLE_X)
        hair = BAL_HAIR_COLORS.get(o.get("hair"), BAL_HAIR)
        head, hands, _feet = self._bal_figure(fig, fd, hip, pose, t, hem, leo, BAL_POLE_X, hair)
        if behind:
            self._bal_pole(fig, fd, BAL_POLE_X)
        x0, y0, x1, y1 = BAL_MIRROR                               # Spiegelbild: kleiner, gespiegelt, gedämpft
        sc = 0.72
        small = fig.resize((int(WIDTH * sc), int(HEIGHT * sc)), Image.BILINEAR).transpose(Image.FLIP_LEFT_RIGHT)
        r, g_, b, a = small.split()
        a = a.point(lambda v: v * 0.55)
        small = Image.merge("RGBA", (r.point(lambda v: v * 0.8), g_.point(lambda v: v * 0.82),
                                     b.point(lambda v: v * 0.95), a))
        mx = int(x0 + (x1 - x0) * 0.42 - (WIDTH - BAL_POLE_X) * sc)
        my = int(y1 - 4 - BAL_FLOOR * sc)
        mirror = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        mirror.paste(small, (mx, my))
        clip = Image.new("L", (WIDTH, HEIGHT), 0)
        ImageDraw.Draw(clip).rectangle([x0, y0, x1, y1], fill=255)
        mirror.putalpha(ImageChops.multiply(mirror.getchannel("A"), clip))
        img.paste(mirror, (0, 0), mirror)
        img.paste(fig, (0, 0), fig)
        if show == "club":
            self._lights_ball(ImageDraw.Draw(img), t, BAL_POLE_X + 96, 12, 10)
        img = self._lights_strobe_apply(img, self._lights_strobe(st.setdefault("strobe", {}), s, o, t), s, leo)
        if bored in ("yawn", "sit"):
            self._bal_bubble(ImageDraw.Draw(img), head, "Gähn …" if bored == "yawn" else None, t)
        return img

    def _bal_bubble(self, d, head, text, t):
        """Sprechblase „Gähn …“ bzw. aufsteigende „Z“ neben dem Kopf."""
        font = self.__dict__.setdefault("_bal_bubble_font", load_font(12, bold=True))
        x, y = head[0] + 14, head[1] - 34
        if text:
            w = d.textlength(text, font=font)
            d.rounded_rectangle([x, y, x + w + 12, y + 19], radius=8, fill=(235, 235, 245))
            d.polygon([(x + 6, y + 18), (x + 14, y + 18), (x, y + 27)], fill=(235, 235, 245))
            d.text((x + 6, y + 3), text, font=font, fill=(40, 40, 60))
            return
        for i in range(3):                                        # Zzz steigen auf und verblassen
            k = (t * 0.5 + i / 3) % 1.0
            v = int(220 * (1 - k))
            size = 9 + 4 * i
            f = self.__dict__.setdefault(f"_bal_z{size}", load_font(size, bold=True))
            d.text((x + k * 12 + i * 6, y - k * 26 + 14), "Z", font=f, fill=(v, v, min(255, v + 30)))
