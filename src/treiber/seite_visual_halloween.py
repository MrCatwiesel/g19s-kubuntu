"""Visualisierung „Halloween“ (halloween, Mixin HalloweenVisual): Auf dem Friedhof spielt eine Skelettband im
Mondlicht – der Sänger singt an einer Schaufel als Mikrofonständer, einer spielt Xylophon auf den eigenen Rippen,
der Trommler haut mit Knochen auf zwei Grabsteine. Vorn singt der Kürbischor: Jeder Kürbis ist ein Frequenzband und
leuchtet von innen. Fledermäuse flattern auf hohe Schläge, Bodennebel zieht vorbei.
Höhepunkt: Die Skelette fallen auseinander und setzen sich wieder zusammen, die Kürbisse lodern. Wortbeitrag: Ein
Gespenst steigt aus dem Grab („Buuuh – Durchsage!“). Gags: Hexenküche (im Kessel steckt ein Weihnachtsmann-Stiefel),
Süßes oder Saures, dem Sänger fällt der Kopf ab, Kürbis-Solo und – mit Gänsehaut – eine Hand an der beschlagenen
Scheibe.
"""
import math
import random

HW_FLOOR = VIS_H - 34                   # Füße der Band
HW_BAND = {"xylo": 92, "singer": 160, "drums": 232}
HW_PUMPKINS = [(40, 30), (100, 28), (160, 32), (220, 28), (280, 22)]   # (x, Breite) – der kleinste singt Solo
HW_GAGS = {"hexe": 9.0, "suesses": 9.0, "kopf": 8.0, "kuerbis": 7.0, "fenster": 9.0}
HW_GAG_FIRST, HW_GAG_PAUSE = 10.0, (12.0, 20.0)
HW_BOOM = 4.0
HW_BONE = (234, 230, 214)
HW_DARK = (24, 18, 26)
HW_POSES = [
    {"lh": (-8, 14), "rh": (12, -8), "lf": (-6, 28), "rf": (6, 28)},
    {"lh": (-12, -14), "rh": (12, -10), "lf": (-8, 28), "rf": (8, 27)},
    {"lh": (-6, 16), "rh": (14, -14), "lf": (-5, 28), "rf": (10, 22)},
]
HW_PARTS = ("skull", "ribs", "pelvis", "larm", "rarm", "lleg", "rleg")


class HalloweenVisual:
    vis_glow = None                     # Kürbisleuchten für die Tastatur

    def _hw_scene(self):
        """Mondnacht auf dem Friedhof: Himmel, Mond, toter Baum, Zaun, Grabsteine (zwischengespeichert)."""
        if "_hw_bg" in self.__dict__:
            return self._hw_bg
        ys = np.linspace(0, 1, HEIGHT)[:, None, None]
        top, bot = np.array([16, 10, 40], np.float32), np.array([70, 44, 90], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(top + (bot - top) * ys, (HEIGHT, WIDTH, 3)), 0, 255)
                              .astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        rng = random.Random(13)
        for _ in range(40):
            x, y = rng.uniform(0, WIDTH), rng.uniform(0, 90)
            d.point((x, y), fill=(200, 200, 230))
        self._blob(img, 262, 40, 110, 110, (240, 220, 160), alpha=0.18, flat=True)  # Mond mit Hof
        self._blob(img, 262, 40, 44, 44, (250, 240, 200), gloss=0.15)
        for ox, oy, r in ((-8, -6, 5), (6, 4, 4), (-2, 10, 3)):
            d.ellipse([262 + ox - r, 40 + oy - r, 262 + ox + r, 40 + oy + r], fill=(228, 216, 176))
        d.polygon([(0, HW_FLOOR - 30), (90, HW_FLOOR - 46), (200, HW_FLOOR - 36), (320, HW_FLOOR - 50),
                   (320, HEIGHT), (0, HEIGHT)], fill=(36, 30, 50))                      # Hügel
        d.rectangle([0, HW_FLOOR - 8, WIDTH, HEIGHT], fill=(30, 40, 34))
        tr = (40, 46, 40)                                                             # toter Baum links
        d.polygon([(14, HW_FLOOR), (30, HW_FLOOR), (26, HW_FLOOR - 70), (19, HW_FLOOR - 70)], fill=tr)
        for p in ([(22, HW_FLOOR - 66), (2, HW_FLOOR - 96), (-6, HW_FLOOR - 100)],
                  [(24, HW_FLOOR - 70), (40, HW_FLOOR - 108), (54, HW_FLOOR - 114)],
                  [(36, HW_FLOOR - 96), (28, HW_FLOOR - 120)], [(8, HW_FLOOR - 88), (16, HW_FLOOR - 110)],
                  [(26, HW_FLOOR - 50), (52, HW_FLOOR - 70), (64, HW_FLOOR - 68)]):
            d.line(p, fill=tr, width=3)
        for x in range(60, WIDTH, 12):                                                # Zaun
            d.line([(x, HW_FLOOR - 16), (x, HW_FLOOR - 40)], fill=(20, 16, 24), width=2)
            d.polygon([(x - 2, HW_FLOOR - 40), (x + 2, HW_FLOOR - 40), (x, HW_FLOOR - 45)], fill=(20, 16, 24))
        d.line([(60, HW_FLOOR - 34), (WIDTH, HW_FLOOR - 34)], fill=(20, 16, 24), width=2)
        d.line([(60, HW_FLOOR - 22), (WIDTH, HW_FLOOR - 22)], fill=(20, 16, 24), width=2)
        for gx, gw, gh in ((126, 18, 24), (196, 16, 20), (300, 20, 26), (64, 14, 18)):  # Grabsteine hinten
            d.rounded_rectangle([gx - gw / 2, HW_FLOOR - 8 - gh, gx + gw / 2, HW_FLOOR - 4], radius=6,
                                fill=(96, 96, 108), outline=(60, 60, 70))
            d.line([(gx, HW_FLOOR - gh), (gx, HW_FLOOR - gh + 10)], fill=(60, 60, 70))
            d.line([(gx - 3, HW_FLOOR - gh + 3), (gx + 3, HW_FLOOR - gh + 3)], fill=(60, 60, 70))
        fog = Image.new("RGBA", (WIDTH * 2, 34), (0, 0, 0, 0))                       # Bodennebel (Streifen)
        fd = ImageDraw.Draw(fog)
        for _ in range(26):
            x, y, w = rng.uniform(0, WIDTH * 2), rng.uniform(8, 26), rng.uniform(40, 90)
            fd.ellipse([x - w / 2, y - 7, x + w / 2, y + 7], fill=(200, 200, 220, 34))
        self._hw_fog = fog
        self._hw_bg = img
        return img

    # -- Figuren -------------------------------------------------------------------------- #
    @staticmethod
    def _hw_bone(d, p1, p2, w=3, col=HW_BONE):
        d.line([p1, p2], fill=col, width=w)
        for p in (p1, p2):
            d.ellipse([p[0] - w * 0.8, p[1] - w * 0.8, p[0] + w * 0.8, p[1] + w * 0.8], fill=col)

    def _hw_skel(self, img, d, x, y, pose, jaw=0.0, bob=0.0, missing=(), off=None, sticks=False, ribs_col=None):
        """Skelett (etwa 72 px). off: Versatz je Teil (Auseinanderfallen), missing: fehlende Teile."""
        off = off or {}

        def o(part, p):
            dx, dy = off.get(part, (0, 0))
            return (p[0] + dx, p[1] + dy)
        hip = (x, y - 29)
        top = (x, hip[1] - 22)
        for side, key, part in ((-1, "lf", "lleg"), (1, "rf", "rleg")):
            if part in missing:
                continue
            hj = (hip[0] + side * 5, hip[1] + 2)
            f = pose[key]
            knee, foot = _ik(hj, (hip[0] + f[0], hip[1] + f[1]), 15, 15, side)
            hj, knee, foot = o(part, hj), o(part, knee), o(part, foot)
            self._hw_bone(d, hj, knee)
            self._hw_bone(d, knee, foot)
            d.ellipse([foot[0] - 5, foot[1] - 2, foot[0] + 4, foot[1] + 1], fill=HW_BONE)
        p = o("pelvis", hip)
        self._blob(img, p[0], p[1], 17, 9, HW_BONE, gloss=0.4)
        rb = o("ribs", top)
        d.line([(rb[0], rb[1]), (rb[0], rb[1] + 22)], fill=HW_BONE, width=3)          # Wirbelsäule
        for k in range(5):
            yy = rb[1] + 3 + k * 3.6
            w = 10 - abs(k - 1.5) * 1.3
            col = ribs_col[k] if ribs_col else HW_BONE
            d.arc([rb[0] - w, yy - 2, rb[0] + w, yy + 4], 200, 340, fill=col, width=2)
        hands = {}
        for side, key, part in ((-1, "lh", "larm"), (1, "rh", "rarm")):
            if part in missing:
                continue
            sh = (top[0] + side * 9, top[1] + 1)
            h = pose[key]
            elbow, hand = _ik(sh, (sh[0] + h[0], sh[1] + h[1]), 12, 12, -side)
            sh, elbow, hand = o(part, sh), o(part, elbow), o(part, hand)
            self._hw_bone(d, sh, elbow, 2)
            self._hw_bone(d, elbow, hand, 2)
            d.ellipse([hand[0] - 3, hand[1] - 3, hand[0] + 3, hand[1] + 3], fill=HW_BONE)
            if sticks:                                                              # Knochen als Schlegel
                self._hw_bone(d, hand, (hand[0] - side * 3, hand[1] - 11), 2)
            hands[key] = hand
        sk = o("skull", (top[0], top[1] - 10 + bob))
        if "skull" not in missing:
            self._hw_skull(img, d, sk, jaw)
        return sk, hands, rb

    def _hw_skull(self, img, d, sk, jaw=0.0):
        self._blob(img, sk[0], sk[1], 17, 16, HW_BONE, gloss=0.35)
        for side in (-1, 1):
            d.ellipse([sk[0] + side * 4 - 3, sk[1] - 4, sk[0] + side * 4 + 3, sk[1] + 2], fill=HW_DARK)
        d.polygon([(sk[0], sk[1] + 1), (sk[0] - 2, sk[1] + 4), (sk[0] + 2, sk[1] + 4)], fill=HW_DARK)
        jy = sk[1] + 7 + 4 * jaw
        d.rectangle([sk[0] - 5, jy - 1, sk[0] + 5, jy + 2], fill=HW_BONE)
        for k in range(5):
            d.line([(sk[0] - 4 + k * 2, sk[1] + 6), (sk[0] - 4 + k * 2, jy)], fill=HW_DARK)

    def _hw_pumpkin(self, img, d, x, y, w, mouth, glow, look=0.0, blush=0.0):
        """Kürbis mit Gesicht; y = Unterkante. mouth 0…1 öffnet den Mund, glow 0…1 Licht von innen."""
        h = w * 0.8
        cy = y - h / 2
        if glow > 0.05:
            self._blob(img, x, cy, w * 2.0, h * 1.8, (255, 150, 40), alpha=round(0.32 * glow, 2), flat=True)
        body = (int(226 + 29 * blush), int(116 - 60 * blush), 24)
        self._blob(img, x, cy, w, h, body, gloss=0.4)
        for k in (-1, 1):
            d.arc([x - w * 0.28 + k * w * 0.18, cy - h / 2, x + w * 0.28 + k * w * 0.18, cy + h / 2], 100, 260,
                  fill=(180, 80, 16))
        d.line([(x, cy - h / 2 + 1), (x + 2, cy - h / 2 - 5)], fill=(80, 90, 40), width=3)
        lit = (255, int(170 + 70 * glow), int(40 + 60 * glow)) if glow > 0.15 else (60, 30, 8)
        ex = look * w * 0.06
        for side in (-1, 1):
            cx = x + side * w * 0.2 + ex
            d.polygon([(cx - w * 0.1, cy - h * 0.02), (cx + w * 0.1, cy - h * 0.02), (cx, cy - h * 0.24)], fill=lit)
        mh = 2 + mouth * h * 0.3
        my = cy + h * 0.14
        pts = [(x - w * 0.3 + ex, my)]
        for k in range(1, 6):
            pts.append((x - w * 0.3 + k * w * 0.12 + ex, my + (3 if k % 2 else 0)))
        pts += [(x + w * 0.24 + ex, my + mh), (x - w * 0.24 + ex, my + mh)]
        d.polygon(pts, fill=lit)

    def _hw_ghost(self, img, d, x, y, t, alpha=0.85, mouth=0.0):
        """Gespenst (Laken); y = Unterkante."""
        col = (240, 240, 250)
        self._blob(img, x, y - 24, 32, 44, col, gloss=0.3, alpha=alpha)
        for k in range(4):
            self._blob(img, x - 12 + k * 8, y - 3 + math.sin(t * 6 + k) * 2, 9, 8, col, gloss=0.2, alpha=alpha)
        for side in (-1, 1):
            d.ellipse([x + side * 6 - 3, y - 36, x + side * 6 + 3, y - 28], fill=HW_DARK)
        d.ellipse([x - 3, y - 25, x + 3, y - 21 + 6 * mouth], fill=HW_DARK)

    def _hw_flames(self, d, x, y, w, t, k):
        for i in range(3):
            fx = x - w / 3 + i * w / 3
            hh = (10 + 8 * abs(math.sin(t * 13 + i * 2))) * k
            d.polygon([(fx - 5, y), (fx + 5, y), (fx + math.sin(t * 9 + i) * 3, y - hh)], fill=(255, 140, 30))
            d.polygon([(fx - 2.5, y), (fx + 2.5, y), (fx, y - hh * 0.6)], fill=(255, 230, 90))

    # -- Ablauf ------------------------------------------------------------------------------ #
    @vis_style("halloween")
    def vis_halloween(self, s, o, color):
        t = s["t"]
        img = self._hw_scene().copy()
        d = ImageDraw.Draw(img)
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("halloween", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                                 "fast": s["level"], "boom": -99.0, "gag": None, "order": [],
                                                 "next_gag": t + HW_GAG_FIRST, "rng": random.Random(31),
                                                 "start": t, "bats": [], "pose": 0, "hit": -9.0, "side": 1,
                                                 "vec": {}})
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
        playing = (s.get("active") or demo) and not talk
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        bang = math.sin(math.pi * min(1.0, (t - s.get("beat_t", t)) / (period * 0.6))) if playing else 0.0
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < HW_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= HW_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*HW_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(HW_GAGS), len(HW_GAGS))
            name = st["order"].pop(0)
            if name == "fenster" and not o.get("spooky", True):
                name = st["order"].pop(0) if st["order"] else "kuerbis"
            st["gag"] = gag = (name, t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        say = []
        if playing and new_beat:
            st["pose"] = (st["pose"] + 1) % len(HW_POSES)
            st["side"] = -st["side"]
            st["hit"] = t
        flick = 0.5 + 0.5 * math.sin(t * 17) * math.sin(t * 7.3)
        self.vis_glow = (255, int(70 + 70 * level + 20 * flick), 0)
        # Auseinanderfallen beim Höhepunkt
        offs = {}
        if boom:
            k = min(1.0, bt / 0.6) if bt < 2.8 else max(0.0, 1 - (bt - 2.8) / 1.0)
            k = k * k * (3 - 2 * k)
            for who in HW_BAND:
                if who not in st["vec"]:
                    r = random.Random(sum(map(ord, who)))
                    st["vec"][who] = {p: (r.uniform(-34, 34), r.uniform(-6, 26) if p != "skull" else
                                          r.uniform(-30, -10)) for p in HW_PARTS}
                rat = math.sin(t * 40) * 1.5 if 0.6 < bt < 2.8 else 0.0
                offs[who] = {p: (v[0] * k + rat, v[1] * k) for p, v in st["vec"][who].items()}
        # Gespenst hinter der Band (Wortbeitrag)
        if talk:
            tl = t - s.get("talk_t", t)
            rise = min(1.0, tl / 1.5)
            gx = 196 + math.sin(t * 1.3) * 10
            self._hw_ghost(img, d, gx, HW_FLOOR - 10 - 40 * rise + math.sin(t * 2) * 3, t, alpha=0.4 + 0.45 * rise)
            if 0.8 < tl < 4.0:
                say.append((gx, HW_FLOOR - 104, "Buuuh – Durchsage!"))
        # Band
        pose = HW_POSES[st["pose"]] if playing else HW_POSES[0]
        bob = 3 * bang
        # Xylophon auf den eigenen Rippen
        hit_k = max(0.0, 1 - (t - st["hit"]) / 0.15) if playing else 0.0
        xp = dict(HW_POSES[0])
        xp["rh"] = (-4, 6 - 6 * hit_k)
        xp["lh"] = (-12, -6 + 4 * math.sin(t * 4))
        ribs = None
        if playing and new_hat:
            st["rib"] = (st.get("rib", 0) + 1 + st["rng"].randint(0, 2)) % 5
            st["rib_t"] = t
        if playing and t - st.get("rib_t", -9) < 0.25:
            ribs = [HW_BONE] * 5
            ribs[st["rib"]] = _hue(st["rib"] / 5, 0.7, 1.0)
        sk, hands, rb = self._hw_skel(img, d, HW_BAND["xylo"], HW_FLOOR, xp, jaw=0.2, bob=bob * 0.6,
                                      off=offs.get("xylo"), ribs_col=ribs)
        if "rh" in hands and not boom:                                              # Schlegel
            hx, hy = hands["rh"]
            self._hw_bone(d, (hx, hy), (hx - 9, hy + 3 + 3 * hit_k), 2)
        # Sänger an der Schaufel
        sx = HW_BAND["singer"]
        d.line([(sx + 18, HW_FLOOR + 2), (sx + 14, HW_FLOOR - 62)], fill=(110, 80, 50), width=3)
        d.polygon([(sx + 13, HW_FLOOR - 4), (sx + 23, HW_FLOOR - 4), (sx + 19, HW_FLOOR + 6)], fill=(130, 130, 140))
        d.rounded_rectangle([sx + 9, HW_FLOOR - 70, sx + 19, HW_FLOOR - 60], radius=4, fill=(60, 60, 70))
        sp = dict(pose)
        sp["rh"] = (6, -10)
        missing = ()
        if gname == "kopf" and gl >= 0.6:
            missing = ("skull",)
            if gl < 5.0:
                sp = {"lh": (-14, 2 + 6 * math.sin(t * 5)), "rh": (14, 2 + 6 * math.cos(t * 5)),
                      "lf": (-6 + 4 * math.sin(t * 3), 28), "rf": (6, 28)}
        jaw = min(1.0, level * 1.6) if playing else 0.0
        ssk, shands, _ = self._hw_skel(img, d, sx, HW_FLOOR, sp, jaw=jaw, bob=bob, missing=missing,
                                       off=offs.get("singer"))
        # Trommler an den Grabsteinen
        dx_ = HW_BAND["drums"]
        dp = dict(pose)
        hitl = st["side"] < 0 and playing and t - st["hit"] < 0.12
        hitr = st["side"] > 0 and playing and t - st["hit"] < 0.12
        dp["lh"] = (-10, 8 if hitl else -6)
        dp["rh"] = (10, 8 if hitr else -6)
        arm_gone = gname == "suesses" and gl >= 6.0
        dsk, dhands, _ = self._hw_skel(img, d, dx_, HW_FLOOR, dp, jaw=0.3 * bang, bob=bob, sticks=not boom,
                                       off=offs.get("drums"), missing=("rarm",) if arm_gone else ())
        for gx, hit in ((dx_ - 17, hitl), (dx_ + 17, hitr)):
            gy = HW_FLOOR - 18 + (1 if hit else 0)
            d.rounded_rectangle([gx - 9, gy, gx + 9, HW_FLOOR + 2], radius=7, fill=(120, 120, 132),
                                outline=(70, 70, 80))
            d.text((gx - 6, gy + 4), "RIP", font=self.f_tiny, fill=(70, 70, 80))
            if hit:
                for k in range(3):
                    d.point((gx - 6 + k * 6, gy - 3 - k % 2 * 2), fill=(200, 200, 200))
        if boom and 1.0 < bt < 2.8:
            say.append((HW_BAND["singer"], 70, "Alle wieder zusammen!"))
        # Bodennebel
        fx = int(t * 8) % WIDTH
        fog = self._hw_fog.crop((fx, 0, fx + WIDTH, 34))
        img.paste(fog, (0, HW_FLOOR - 22), fog)
        # Kürbischor
        bands = s.get("bands")
        if bands is None or len(bands) == 0:
            bands = [level] * 8
        for i, (px, pw) in enumerate(HW_PUMPKINS):
            if gname == "kopf" and i == 2 and gl >= 4.4:
                continue
            b = bands[min(len(bands) - 1, i * len(bands) // len(HW_PUMPKINS))] if playing else 0.0
            mouth = min(1.0, b * 1.4)
            look, blush = 0.0, 0.0
            if gname == "kuerbis":
                if i == 4:
                    mouth = 0.6 + 0.4 * abs(math.sin(t * 9))
                    blush = min(1.0, max(0.0, gl - 4.0))
                else:
                    look, mouth = 1.0, (0.0 if gl > 4.0 else mouth * 0.3)
            glow = 0.35 + 0.65 * min(1.0, level * 1.3) * (0.8 + 0.2 * flick) if (playing or demo) else 0.25
            self._hw_pumpkin(img, d, px, VIS_H - 2, pw, mouth, glow, look, blush)
            if boom:
                self._hw_flames(d, px, VIS_H - 2 - pw * 0.8, pw, t + i, min(1.0, bt * 3, (HW_BOOM - bt) * 2))
        # Fledermäuse
        if playing and new_hat and len(st["bats"]) < 4 and st["rng"].random() < 0.35:
            st["bats"].append({"x": 30.0, "y": HW_FLOOR - 100.0, "vx": st["rng"].uniform(50, 90),
                               "ph": st["rng"].uniform(0, 6)})
        for b in list(st["bats"]):
            b["x"] += b["vx"] * dt
            if b["x"] > WIDTH + 12:
                st["bats"].remove(b)
                continue
            self._cl_bat(img, d, b["x"], b["y"] - 40 * math.sin(b["x"] / 90) + math.sin(t * 5 + b["ph"]) * 6, t)
        # Gags
        if gname == "hexe":
            self._hw_gag_witch(img, d, gl, t, say)
        elif gname == "suesses":
            self._hw_gag_trick(img, d, gl, t, say, dsk, dhands)
        elif gname == "kopf":
            self._hw_gag_head(img, d, gl, t, say, ssk)
        elif gname == "kuerbis":
            px, pw = HW_PUMPKINS[4]
            if gl < 4.0:
                for k in range(3):
                    ny = VIS_H - 30 - ((gl * 30 + k * 14) % 42)
                    d.text((px - 6 + k * 5 + math.sin(t * 3 + k) * 4, ny), "♪", font=self.f_small_b,
                           fill=(250, 230, 140))
                if 0.4 < gl < 3.2:
                    say.append((px - 22, VIS_H - 58, "Laaa-laaa-LAAA!"))
            elif gl < 6.6:
                say.append((HW_PUMPKINS[2][0], VIS_H - 58, "Psst!"))
        for x, y, text in say:
            self._xmas_party_say(d, x, y, text)
        if gname == "fenster":
            img = self._hw_gag_window(img, gl, t)
        return img

    # -- Gags ------------------------------------------------------------------------------------- #
    def _hw_gag_witch(self, img, d, gl, t, say):
        """Hexe rührt im Kessel – heraus kommt ein Weihnachtsmann-Stiefel („Huch – falsche Saison!“), dann ein Frosch."""
        x = -30 + min(1.0, gl) * 70 if gl < 8.2 else 40 - (gl - 8.2) * 90
        cx, cy = x + 26, HW_FLOOR - 4
        brew = (90, 220, 80)
        self._blob(img, cx, cy - 4, 46, 16, brew, alpha=0.35, flat=True)
        for k in range(4):                                                          # Blasen
            by = cy - 14 - ((t * 20 + k * 9) % 30)
            d.ellipse([cx - 10 + k * 6 - 2, by - 2, cx - 10 + k * 6 + 2, by + 2], outline=brew)
        # Hexe
        d.polygon([(x - 12, HW_FLOOR), (x + 12, HW_FLOOR), (x + 4, HW_FLOOR - 40), (x - 4, HW_FLOOR - 40)],
                  fill=(30, 20, 40))
        self._blob(img, x, HW_FLOOR - 48, 15, 15, (130, 190, 110), gloss=0.3)
        d.polygon([(x + 6, HW_FLOOR - 49), (x + 13, HW_FLOOR - 46), (x + 6, HW_FLOOR - 45)], fill=(110, 170, 90))
        d.point((x + 3, HW_FLOOR - 51), fill=(250, 220, 40))
        d.line([(x - 16, HW_FLOOR - 54), (x + 14, HW_FLOOR - 54)], fill=(30, 20, 40), width=3)
        d.polygon([(x - 8, HW_FLOOR - 54), (x + 8, HW_FLOOR - 54), (x - 6, HW_FLOOR - 82)], fill=(30, 20, 40))
        for k in range(4):
            d.line([(x - 7, HW_FLOOR - 48 + k * 3), (x - 12, HW_FLOOR - 40 + k * 4)], fill=(150, 150, 160))
        stir = (cx + math.cos(t * 4) * 8, cy - 14 + math.sin(t * 4) * 2) if 1.0 <= gl < 3.5 else (cx, cy - 18)
        d.line([(x + 6, HW_FLOOR - 34), stir], fill=(30, 20, 40), width=3)
        d.line([stir, (stir[0], stir[1] + 14)], fill=(140, 100, 60), width=2)
        # Kessel
        self._blob(img, cx, cy - 8, 32, 22, (34, 30, 36), gloss=0.5)
        d.ellipse([cx - 16, cy - 20, cx + 16, cy - 14], fill=(70, 160, 60), outline=(20, 18, 22))
        d.line([(cx - 10, cy + 2), (cx - 14, cy + 6)], fill=(20, 18, 22), width=2)
        d.line([(cx + 10, cy + 2), (cx + 14, cy + 6)], fill=(20, 18, 22), width=2)
        if 3.5 <= gl < 7.2:                                                         # der Stiefel
            k = min(1.0, (gl - 3.5) / 1.0)
            bx, by = cx, cy - 18 - 24 * k
            if gl >= 6.5:
                f = gl - 6.5
                bx, by = bx - f * 120, by - f * 140 + f * f * 120
            d.rectangle([bx - 4, by - 16, bx + 4, by], fill=(200, 30, 40))
            d.rectangle([bx - 4, by, bx + 10, by + 6], fill=(200, 30, 40))
            d.rectangle([bx - 6, by - 20, bx + 6, by - 15], fill=(250, 250, 250))
            if 4.5 <= gl < 6.5:
                say.append((x + 4, HW_FLOOR - 92, "Huch – falsche Saison!"))
        if 7.0 <= gl:
            fy = cy - 18 - abs(math.sin((gl - 7.0) * 4)) * 16
            fx = cx + (gl - 7.0) * 20
            self._blob(img, fx, fy, 12, 9, (80, 170, 60), gloss=0.5)
            d.point((fx - 2, fy - 3), fill=(0, 0, 0))
            d.point((fx + 2, fy - 3), fill=(0, 0, 0))
            if gl < 8.6:
                say.append((fx, fy - 10, "Quak!"))

    def _hw_kid(self, img, d, x, y, t, kind, walk, scared=0.0):
        step = math.sin(t * 12) * 3 * walk
        for side in (-1, 1):
            d.line([(x + side * 3, y - 10), (x + side * 3 + side * step, y)], fill=(40, 40, 50), width=3)
        if kind == "geist":
            self._blob(img, x, y - 20, 18, 26, (246, 246, 250), gloss=0.2)
            for side in (-1, 1):
                d.ellipse([x + side * 3 - 2, y - 28 - scared * 2, x + side * 3 + 2, y - 24], fill=HW_DARK)
        else:
            self._blob(img, x, y - 18, 20, 18, (240, 130, 30), gloss=0.4)
            self._blob(img, x, y - 32, 12, 12, (250, 210, 180), gloss=0.3)
            d.line([(x, y - 39), (x + 2, y - 43)], fill=(70, 110, 40), width=3)
            for side in (-1, 1):
                d.point((x + side * 2, y - 33), fill=(20, 20, 20))
            if scared:
                d.ellipse([x - 2, y - 30, x + 2, y - 27], fill=(20, 20, 20))
        bx = x - 10
        d.polygon([(bx - 5, y - 14), (bx + 5, y - 14), (bx + 6, y - 2), (bx - 6, y - 2)], fill=(240, 130, 30))
        return bx

    def _hw_gag_trick(self, img, d, gl, t, say, dsk, dhands):
        """Süßes oder Saures: Zwei verkleidete Kinder klingeln beim Trommler. Er reicht Süßes – samt Arm."""
        if gl < 2.5:
            x, walk = 340 - gl / 2.5 * 70, 1.0
        elif gl < 6.2:
            x, walk = 270.0, 0.0
        else:
            x, walk = 270 + (gl - 6.2) * 80, 1.6
        scared = 1.0 if gl >= 6.2 else 0.0
        self._hw_kid(img, d, x + 22, HW_FLOOR, t, "geist", walk, scared)
        bag = self._hw_kid(img, d, x, HW_FLOOR, t + 0.4, "kuerbis", walk, scared)
        if 2.5 <= gl < 4.4:
            say.append((x + 10, HW_FLOOR - 58, "Süßes oder Saures!"))
        if 4.4 <= gl < 6.2:
            hx = dsk[0] + 24 + min(1.0, (gl - 4.4) / 0.8) * (bag - dsk[0] - 30)
            hy = HW_FLOOR - 40
            self._hw_bone(d, (dsk[0] + 9, dsk[1] + 11), (hx, hy), 2)
            for k, c in enumerate(((240, 60, 80), (60, 160, 240), (250, 210, 40))):
                d.rectangle([hx - 4 + k * 4, hy - 4, hx - 1 + k * 4, hy - 1], fill=c)
            say.append((dsk[0], dsk[1] - 18, "Bedient euch!"))
        if gl >= 6.2:
            self._hw_bone(d, (bag - 2, HW_FLOOR - 14), (bag + 6, HW_FLOOR - 30), 2)       # Arm steckt in der Tüte
            if gl < 7.6:
                say.append((x + 10, HW_FLOOR - 58, "Aaaah!"))
            else:
                say.append((dsk[0], dsk[1] - 18, "He! Mein Arm!"))

    def _hw_gag_head(self, img, d, gl, t, say, ssk):
        """Dem Sänger fällt der Kopf ab und rollt zu den Kürbissen; ein Kürbis springt als Ersatz auf den Hals."""
        sx = HW_BAND["singer"]
        if gl < 0.6:
            return
        k = gl - 0.6
        if k < 0.5:
            x, y = sx, ssk[1] + (HW_FLOOR - 4 - ssk[1]) * (k / 0.5) ** 2
        else:
            x, y = sx + min(1.0, (k - 0.5) / 1.6) * 90, HW_FLOOR - 4 - abs(math.sin(k * 6)) * 4 * max(0.0, 1 - k / 2)
        self._hw_skull(img, d, (x, y), 0.4 if 2.6 < gl < 4.2 else 0.0)
        if 2.6 <= gl < 4.2:
            say.append((x, y - 14, "Hallo? Hier unten!"))
        px, pw = HW_PUMPKINS[2]
        if 4.4 <= gl < 5.0:
            f = (gl - 4.4) / 0.6
            self._hw_pumpkin(img, d, px, VIS_H - 2 - (VIS_H - 2 - ssk[1] - 10) * f - math.sin(f * math.pi) * 30,
                             pw * (1 - 0.35 * f), 0.2, 0.8)
        elif gl >= 5.0:
            self._hw_pumpkin(img, d, sx, ssk[1] + 10, pw * 0.65, 0.5, 0.9)
            if gl < 7.5:
                say.append((sx, ssk[1] - 14, "Passt!"))

    def _hw_gag_window(self, img, gl, t):
        """Gänsehaut: Die Scheibe beschlägt, eine Hand drückt sich von innen dagegen, Finger ziehen Spuren und
        schreiben „LASS MICH REIN“. Dann klart es wieder auf."""
        k = min(1.0, gl / 1.4, max(0.0, (HW_GAGS["fenster"] - gl) / 1.4))
        if k <= 0:
            return img
        dim = Image.blend(img, Image.new("RGB", img.size, (8, 6, 14)), 0.5 * k)
        fog = Image.blend(dim, Image.new("RGB", img.size, (170, 176, 190)), 0.62 * k)
        mask = Image.new("L", img.size, 0)
        md = ImageDraw.Draw(mask)
        if gl >= 1.8:
            hx, hy = 90, 92
            a = int(230 * min(1.0, (gl - 1.8) / 0.2))
            md.ellipse([hx - 13, hy - 2, hx + 13, hy + 24], fill=a)                # Handballen
            drag = max(0.0, min(1.0, (gl - 2.6) / 2.2)) * 46
            for fx, fy, ln, w in ((-12, 2, 14, 2.6), (-6, -4, 20, 2.8), (1, -6, 22, 2.8), (8, -4, 20, 2.7),
                                  (13, 6, 12, 2.5)):
                x0, y0 = hx + fx, hy + fy
                md.line([(x0 + (fx - 2) * 0.25, y0 - ln), (x0, y0)], fill=a, width=int(w * 2))
                md.ellipse([x0 + (fx - 2) * 0.25 - w, y0 - ln - w, x0 + (fx - 2) * 0.25 + w, y0 - ln + w], fill=a)
                if drag and fy < 4:                                                 # Finger ziehen Spuren
                    md.line([(x0, y0 + 20), (x0 + math.sin(fx) * 2, y0 + 20 + drag)], fill=int(a * 0.8),
                            width=int(w * 1.6))
            text = "LASS MICH\nREIN …"
            n = int(max(0.0, min(1.0, (gl - 4.0) / 2.6)) * len(text))
            if n:
                md.multiline_text((150, 54), text[:n], font=self.f_big, fill=210, spacing=8)
        clear = Image.blend(img, Image.new("RGB", img.size, (200, 210, 230)), 0.12)  # klare Stellen der Scheibe
        fog.paste(clear, (0, 0), mask)
        return fog
