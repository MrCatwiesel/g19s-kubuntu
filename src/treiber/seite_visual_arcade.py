"""Visualisierung „Retro-Arcade“ (arcade, Mixin ArcadeVisual): Pixelgrafik wie am Automaten (halbe Auflösung,
hochgezogen). Die Alien-Reihen marschieren Schritt für Schritt im Takt, das Raumschiff folgt der Melodie und feuert
auf hohe Schläge, getroffene Aliens zerplatzen in Pixel, der Punktestand zählt mit. Höhepunkt: MEGA-LASER fegt eine
ganze Reihe weg („COMBO!“). Wortbeitrag: PAUSE – INSERT COIN. Gags: Das Mutterschiff fliegt vorbei (+5000), ein
Glitch zerlegt das Bild, Highscore-Eintrag.
Sparsam: wird in 160×107 Pixeln gezeichnet.
"""
import math
import random

AR_W, AR_H = WIDTH // 2, VIS_H // 2
AR_COLS, AR_ROWS = 8, 4
AR_GAGS = {"boss": 8.0, "glitch": 5.0, "highscore": 7.0}
AR_GAG_FIRST, AR_GAG_PAUSE = 8.0, (12.0, 20.0)
AR_BOOM = 3.0
AR_SPRITES = [["..X..X..", "...XX...", "..XXXX..", ".XX.XX.X", "XXXXXXXX", "X.X..X.X"],
              ["...XX...", "..XXXX..", ".X.XX.X.", "XXXXXXXX", "..X..X..", ".X.XX.X."],
              [".XX..XX.", "XXXXXXXX", "XX.XX.XX", "XXXXXXXX", ".X....X.", "X......X"]]
AR_ROWCOL = [(250, 80, 200), (80, 220, 250), (120, 250, 100), (250, 220, 60)]


class ArcadeVisual:
    vis_col_arcade = None

    def _ar_wave(self, st):
        st["aliens"] = [[c, r, True] for r in range(AR_ROWS) for c in range(AR_COLS)]
        st["ax"], st["ay"], st["adir"] = 10, 12, 1
        st["wave"] = st.get("wave", 0) + 1

    @staticmethod
    def _ar_sprite(d, x, y, rows, col, frame):
        for j, line in enumerate(rows):
            if frame and j == len(rows) - 1:
                line = line[::-1]
            for i, ch in enumerate(line):
                if ch == "X":
                    d.point((x + i, y + j), fill=col)

    @vis_style("arcade")
    def vis_arcade(self, s, o, color):
        t = s["t"]
        demo = bool(s.get("demo"))
        talk = bool(s.get("talk"))
        st = self._vstate("arcade", lambda: {"beats": s["beats"], "hats": s.get("hats", 0), "slow": s["level"],
                                              "fast": s["level"], "boom": -99.0, "gag": None, "order": [], "k": 0,
                                              "next_gag": t + AR_GAG_FIRST, "rng": random.Random(161), "start": t,
                                              "shots": [], "boomp": [], "score": 0, "ship": AR_W / 2, "hi": 9900})
        if "aliens" not in st:
            self._ar_wave(st)
        dt = self._vis_dt(st, t)
        new_beat = s["beats"] != st["beats"]
        st["beats"] = s["beats"]
        new_hat = s.get("hats", 0) != st["hats"]
        st["hats"] = s.get("hats", 0)
        playing = (s.get("active") or demo) and not talk
        level = s["level"] if playing else 0.0
        st["slow"] += (s["level"] - st["slow"]) * min(1.0, dt / 6)
        st["fast"] += (s["level"] - st["fast"]) * min(1.0, dt / 0.4)
        if not demo and playing and st["fast"] > st["slow"] * 1.2 + 0.04 and t - st["boom"] > 15 \
                and t - st["start"] > 5 and st["gag"] is None:
            st["boom"] = t
        bt = t - st["boom"]
        boom = 0 <= bt < AR_BOOM
        gag = st["gag"]
        if gag and t - gag[1] >= AR_GAGS[gag[0]]:
            st["gag"] = gag = None
            st["next_gag"] = t + st["rng"].uniform(*AR_GAG_PAUSE)
        if not demo and o.get("gags", True) and gag is None and playing and not boom and t >= st["next_gag"]:
            if not st["order"]:
                st["order"] = st["rng"].sample(list(AR_GAGS), len(AR_GAGS))
            st["gag"] = gag = (st["order"].pop(0), t)
        gname = gag[0] if gag else None
        gl = t - gag[1] if gag else 0.0
        rng = st["rng"]
        low = Image.new("RGB", (AR_W, AR_H), (0, 0, 0))
        d = ImageDraw.Draw(low)
        for k in range(30):                                                         # Sterne
            d.point(((k * 53) % AR_W, (k * 29 + int(t * 4)) % AR_H), fill=(60, 60, 90))
        # Aliens marschieren im Takt
        if playing and new_beat:
            st["k"] += 1
            alive = [a for a in st["aliens"] if a[2]]
            xs = [a[0] for a in alive]
            if xs:
                left, right = st["ax"] + min(xs) * 12, st["ax"] + max(xs) * 12 + 8
                if (st["adir"] > 0 and right + 3 > AR_W - 2) or (st["adir"] < 0 and left - 3 < 2):
                    st["adir"] = -st["adir"]
                    st["ay"] = min(st["ay"] + 3, 40)
                else:
                    st["ax"] += 3 * st["adir"]
        frame = st["k"] % 2
        for c, r, alive in st["aliens"]:
            if alive:
                self._ar_sprite(d, st["ax"] + c * 12, st["ay"] + r * 9, AR_SPRITES[r % 3], AR_ROWCOL[r], frame)
        if not any(a[2] for a in st["aliens"]):
            self._ar_wave(st)
        # Raumschiff folgt der Melodie
        bands = s.get("bands")
        if bands is not None and len(bands) and playing:
            w = np.asarray(bands, dtype=float)
            target = 10 + (AR_W - 20) * float((w * np.arange(len(w))).sum() / max(1e-6, w.sum()) / max(1, len(w) - 1))
        else:
            target = AR_W / 2 + math.sin(t * 0.7) * 30
        st["ship"] += (target - st["ship"]) * min(1.0, dt * 4)
        sx, sy = int(st["ship"]), AR_H - 18
        d.rectangle([sx - 5, sy + 2, sx + 5, sy + 4], fill=(90, 250, 120))
        d.rectangle([sx - 1, sy - 1, sx + 1, sy + 2], fill=(90, 250, 120))
        for bx in (24, 64, 104, 144):                                               # Bunker
            d.rectangle([bx - 6, AR_H - 32, bx + 6, AR_H - 27], fill=(60, 200, 90))
            d.rectangle([bx - 2, AR_H - 28, bx + 2, AR_H - 27], fill=(0, 0, 0))
        d.line([(0, AR_H - 12), (AR_W, AR_H - 12)], fill=(60, 200, 90))
        if playing and new_hat and len(st["shots"]) < 4:
            st["shots"].append([sx, sy - 2])
        for sh in st["shots"]:
            sh[1] -= 90 * dt
        hit_any = None
        for sh in st["shots"]:
            for a in st["aliens"]:
                if a[2] and abs(sh[0] - (st["ax"] + a[0] * 12 + 4)) < 5 and abs(sh[1] - (st["ay"] + a[1] * 9 + 3)) < 4:
                    a[2] = False
                    sh[1] = -10
                    st["score"] += 100
                    hit_any = AR_ROWCOL[a[1]]
                    for _ in range(8):
                        st["boomp"].append([sh[0], st["ay"] + a[1] * 9 + 3, rng.uniform(-30, 30), rng.uniform(-30, 30),
                                            0.6, AR_ROWCOL[a[1]]])
                    break
        st["shots"] = [sh for sh in st["shots"] if sh[1] > 0]
        for x, y in st["shots"]:
            d.line([(x, y), (x, y - 3)], fill=(255, 255, 255))
        if boom:                                                                    # MEGA-LASER
            if 0.3 < bt < 1.6:
                d.rectangle([sx - 2, 0, sx + 2, sy - 2], fill=(255, 120, 255))
                row = max((a[1] for a in st["aliens"] if a[2]), default=None)
                if row is not None and bt > 0.6:
                    for a in st["aliens"]:
                        if a[2] and a[1] == row:
                            a[2] = False
                            st["score"] += 200
        for p in st["boomp"]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        st["boomp"] = [p for p in st["boomp"] if p[4] > 0]
        for x, y, vx, vy, life, col in st["boomp"]:
            d.point((x, y), fill=col)
        if gname == "boss":
            mx = -20 + gl / AR_GAGS["boss"] * (AR_W + 40)
            if gl < 5.0:
                d.ellipse([mx - 10, 3, mx + 10, 9], fill=(250, 60, 60))
                d.rectangle([mx - 4, 1, mx + 4, 4], fill=(250, 120, 120))
                if gl > 4.4:
                    d.line([(mx, 9), (mx, AR_H - 18)], fill=(255, 255, 255))
        big = low.resize((WIDTH, VIS_H), Image.NEAREST)
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        img.paste(big, (0, 0))
        if o.get("scanlines", True):                                                # Röhren-Zeilen
            arr = np.asarray(img).copy()
            arr[1:VIS_H:2] = (arr[1:VIS_H:2] * 0.72).astype(np.uint8)
            img = Image.fromarray(arr, "RGB")
        d = ImageDraw.Draw(img)
        d.text((8, VIS_H - 18), f"SCORE {st['score']:06d}", font=self.f_tiny, fill=(255, 255, 255))
        d.text((200, VIS_H - 18), f"HI {max(st['hi'], st['score']):06d}", font=self.f_tiny, fill=(255, 220, 80))
        d.text((128, VIS_H - 18), f"WAVE {st['wave']}", font=self.f_tiny, fill=(120, 250, 140))
        if boom and bt < 2.6:
            d.text((110, 70), "MEGA-LASER!", font=self.f_small_b, fill=(255, 120, 255))
            d.text((130, 90), "COMBO x8", font=self.f_small_b, fill=(255, 255, 120))
        if talk:
            tl = t - s.get("talk_t", t)
            if int(tl * 2) % 2 == 0:
                d.text((128, 80), "PAUSE", font=self.f_big, fill=(255, 255, 255))
            d.text((110, 120), "INSERT COIN", font=self.f_small_b, fill=(255, 200, 60))
        if gname == "boss" and 4.4 <= gl < 6.4:
            d.text((140, 26), "+5000", font=self.f_small_b, fill=(255, 80, 80))
            if gl < 4.5:
                st["score"] += 5000
        elif gname == "glitch" and gl < 4.0:
            arr = np.asarray(img).copy()
            for k in range(8):
                y0 = (k * 27 + int(gl * 50)) % (VIS_H - 10)
                arr[y0:y0 + 6] = np.roll(arr[y0:y0 + 6], int(20 * math.sin(gl * 9 + k)), axis=1)
            if int(gl * 6) % 3 == 0:
                arr[:VIS_H] = 255 - arr[:VIS_H]
            img = Image.fromarray(arr, "RGB")
            d = ImageDraw.Draw(img)
            d.text((60, 96), "ERROR 404: BASS NOT FOUND", font=self.f_tiny, fill=(255, 60, 60))
        elif gname == "highscore":
            d.rectangle([70, 50, 250, 150], fill=(0, 0, 0), outline=(255, 255, 255))
            d.text((100, 56), "NEW HIGHSCORE!", font=self.f_small_b, fill=(255, 220, 80))
            name = "G19"[:max(0, min(3, int(gl / 1.0)))]
            blink = "_" if int(gl * 3) % 2 and len(name) < 3 else ""
            d.text((130, 90), name + blink, font=self.f_big, fill=(255, 255, 255))
            if gl > 4.0:
                d.text((96, 130), "Gut gemacht, Spieler 1!", font=self.f_tiny, fill=(120, 250, 140))
        st["hi"] = max(st["hi"], st["score"])
        self.vis_col_arcade = hit_any or getattr(self, "vis_col_arcade", None) or (90, 250, 120)
        return img
