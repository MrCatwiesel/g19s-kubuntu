"""Figurenbaukasten für die Themen-Stile (Mixin FigureKit): eine Person mit Pose, Hut und Mund sowie kleine Helfer
(Feuerwerk-Partikel, Sterne). Pose: {"lh", "rh"} Handziel relativ zur Schulter, {"lf", "rf"} Fußziel relativ zur
Hüfte. Hüte: None, "party", "jester", "top", "cowboy", "tracht", "crown", "beanie", "helmet".
"""
import math
import random

FIG_POSE_STAND = {"lh": (-6, 22), "rh": (6, 22), "lf": (-6, 34), "rf": (6, 34)}


def fig_dance_pose(k, up=True, sway=0.0):
    """Einfache Tanzposen im Wechsel (k = Schlagzähler)."""
    p = k % 4
    arm = -18 if up else 12
    return [{"lh": (-14, arm), "rh": (12, 14), "lf": (-6 + sway * 3, 34), "rf": (8 + sway * 3, 30)},
            {"lh": (-12, 14), "rh": (14, arm), "lf": (-8 + sway * 3, 30), "rf": (6 + sway * 3, 34)},
            {"lh": (-14, arm), "rh": (14, arm), "lf": (-7, 34), "rf": (7, 34)},
            {"lh": (-8, 18), "rh": (8, 18), "lf": (-5, 34), "rf": (5, 34)}][p]


class FigureKit:
    def _fig(self, img, d, x, y, t, shirt, pose=None, h=1.0, skin=(240, 200, 170), legs=(60, 62, 90),
             hair=(100, 66, 40), hat=None, hat_col=None, mouth=0.0, lean=0.0, sit=False, dress=None, face=0,
             beard=None, eyes="dot"):
        """Person; y = Fußpunkt, h = Maßstab (1,0 ≈ 74 px). Gibt (Kopfmitte, [linke Hand, rechte Hand]) zurück."""
        pose = pose or FIG_POSE_STAND
        s = h
        hip = (x + lean * 8 * s, y - (20 if sit else 34) * s)
        for side, key in ((-1, "lf"), (1, "rf")):
            hj = (hip[0] + side * 4 * s, hip[1])
            if sit:
                knee, foot = (hj[0] + 14 * s, hj[1] + 1), (hj[0] + 14 * s, y)
            else:
                f = pose.get(key, (side * 6, 34))
                knee, foot = _ik(hj, (hj[0] + f[0] * s, hj[1] + f[1] * s), 17 * s, 17 * s, side)
            self._limb(img, hj, knee, 6 * s, legs)
            self._limb(img, knee, foot, 5 * s, legs)
            d.ellipse([foot[0] - 5 * s, foot[1] - 3 * s, foot[0] + 5 * s, foot[1] + 1], fill=(50, 40, 36))
        neck = (hip[0] + lean * 10 * s, hip[1] - 30 * s)
        if dress:
            d.polygon([(hip[0] - 13 * s, hip[1] + 8 * s), (hip[0] + 13 * s, hip[1] + 8 * s),
                       (neck[0] + 7 * s, neck[1] + 6 * s), (neck[0] - 7 * s, neck[1] + 6 * s)], fill=dress)
        self._blob(img, (hip[0] + neck[0]) / 2, (hip[1] + neck[1]) / 2 + 2 * s, 20 * s, 34 * s, shirt, gloss=0.3,
                   ang=lean * 0.3)
        hands = []
        for side, key in ((-1, "lh"), (1, "rh")):
            sh = (neck[0] + side * 9 * s, neck[1] + 4 * s)
            hh = pose.get(key, (side * 6, 22))
            elbow, hand = _ik(sh, (sh[0] + hh[0] * s, sh[1] + hh[1] * s), 13 * s, 13 * s, -side)
            self._limb(img, sh, elbow, 5 * s, shirt)
            self._limb(img, elbow, hand, 4 * s, skin)
            self._blob(img, hand[0], hand[1], 5 * s, 5 * s, skin, gloss=0.2)
            hands.append(hand)
        hc = (neck[0] + face * 1.5, neck[1] - 9 * s)
        if hair and hat not in ("helmet",):
            self._blob(img, hc[0], hc[1] - 2 * s, 20 * s, 18 * s, hair, gloss=0.3)
        self._blob(img, hc[0], hc[1] + 1 * s, 17 * s, 18 * s, skin, gloss=0.3)
        for side in (-1, 1):
            ex = hc[0] + side * 3.5 * s + face * 1.5
            if eyes == "closed":
                d.line([(ex - 1.5, hc[1]), (ex + 1.5, hc[1])], fill=(30, 24, 24))
            elif eyes == "big":
                d.ellipse([ex - 2.5, hc[1] - 3, ex + 2.5, hc[1] + 2], fill=(250, 250, 250), outline=(30, 24, 24))
                d.ellipse([ex - 1, hc[1] - 1.5, ex + 1, hc[1] + 0.5], fill=(30, 24, 24))
            else:
                d.ellipse([ex - 1.3, hc[1] - 1.5, ex + 1.3, hc[1] + 1], fill=(30, 24, 24))
        if beard:
            d.chord([hc[0] - 8 * s, hc[1] - 2 * s, hc[0] + 8 * s, hc[1] + 12 * s], 0, 180, fill=beard)
        my = hc[1] + 5 * s
        if mouth > 0.15:
            d.ellipse([hc[0] - 2.5 * s, my - 1, hc[0] + 2.5 * s, my + 1 + mouth * 4 * s], fill=(120, 40, 50))
        else:
            d.arc([hc[0] - 3 * s, my - 3, hc[0] + 3 * s, my + 1], 20, 160, fill=(150, 60, 60))
        self._fig_hat(img, d, hc, s, hat, hat_col, t)
        return hc, hands

    def _fig_hat(self, img, d, hc, s, hat, col, t):
        if not hat:
            return
        top = hc[1] - 8 * s
        if hat == "party":
            col = col or (230, 60, 120)
            d.polygon([(hc[0] - 6 * s, top + 2), (hc[0] + 6 * s, top + 2), (hc[0] + 1, top - 14 * s)], fill=col)
            self._blob(img, hc[0] + 1, top - 14 * s, 4 * s, 4 * s, (250, 220, 60), gloss=0.3)
        elif hat == "jester":
            cols = col or ((220, 40, 60), (250, 200, 40))
            for i, side in enumerate((-1, 1)):
                tip = (hc[0] + side * 14 * s, top - 6 * s + math.sin(t * 6 + i) * 2)
                d.polygon([(hc[0] - (4 if side < 0 else -4) * s, top + 3), (hc[0], top - 4 * s), tip],
                          fill=cols[i % 2])
                self._blob(img, tip[0], tip[1] + 2, 4 * s, 4 * s, cols[(i + 1) % 2], gloss=0.4)
            d.rectangle([hc[0] - 9 * s, top + 1, hc[0] + 9 * s, top + 4 * s], fill=cols[1])
        elif hat == "top":
            col = col or (30, 30, 34)
            d.rectangle([hc[0] - 6 * s, top - 12 * s, hc[0] + 6 * s, top + 2], fill=col)
            d.rectangle([hc[0] - 10 * s, top + 1, hc[0] + 10 * s, top + 3 * s], fill=col)
            d.rectangle([hc[0] - 6 * s, top - 2 * s, hc[0] + 6 * s, top], fill=(200, 40, 50))
        elif hat == "cowboy":
            col = col or (150, 100, 56)
            d.ellipse([hc[0] - 14 * s, top - 1, hc[0] + 14 * s, top + 5 * s], fill=col)
            d.chord([hc[0] - 7 * s, top - 11 * s, hc[0] + 7 * s, top + 4 * s], 180, 360, fill=col)
            d.line([(hc[0] - 7 * s, top), (hc[0] + 7 * s, top)], fill=(90, 60, 30), width=2)
        elif hat == "tracht":
            col = col or (60, 80, 50)
            d.ellipse([hc[0] - 10 * s, top - 1, hc[0] + 10 * s, top + 4 * s], fill=col)
            d.chord([hc[0] - 6 * s, top - 9 * s, hc[0] + 6 * s, top + 4 * s], 180, 360, fill=col)
            d.line([(hc[0] + 4 * s, top - 4 * s), (hc[0] + 9 * s, top - 14 * s)], fill=(250, 250, 250), width=2)
        elif hat == "crown":
            col = col or (250, 210, 60)
            d.polygon([(hc[0] - 7 * s, top + 2), (hc[0] + 7 * s, top + 2), (hc[0] + 7 * s, top - 6 * s),
                       (hc[0] + 3.5 * s, top - 2 * s), (hc[0], top - 8 * s), (hc[0] - 3.5 * s, top - 2 * s),
                       (hc[0] - 7 * s, top - 6 * s)], fill=col)
        elif hat == "beanie":
            col = col or (200, 60, 60)
            d.chord([hc[0] - 9 * s, top - 6 * s, hc[0] + 9 * s, top + 8 * s], 180, 360, fill=col)
            self._blob(img, hc[0], top - 7 * s, 5 * s, 5 * s, (250, 250, 250), gloss=0.3)
        elif hat == "helmet":
            col = col or (230, 230, 240)
            d.ellipse([hc[0] - 13 * s, hc[1] - 13 * s, hc[0] + 13 * s, hc[1] + 13 * s], outline=col, width=3)
            self._blob(img, hc[0] + 4 * s, hc[1] - 5 * s, 6 * s, 4 * s, (255, 255, 255), alpha=0.6, flat=True)

    # -- Feuerwerk (Silvester, Oktoberfest-Abschluss …) ----------------------------------- #
    @staticmethod
    def _fx_burst(parts, x, y, col, rng, n=22, speed=60.0):
        for k in range(n):
            a = k / n * 6.283 + rng.uniform(-0.1, 0.1)
            v = speed * rng.uniform(0.6, 1.0)
            parts.append([x, y, math.cos(a) * v, math.sin(a) * v, 1.0, col])

    @staticmethod
    def _fx_step(parts, dt, grav=40.0, fade=0.7, cap=400):
        for p in parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += grav * dt
            p[2] *= 1 - dt * 0.6
            p[4] -= dt * fade
        parts[:] = [p for p in parts if p[4] > 0][-cap:]

    @staticmethod
    def _fx_draw(d, parts):
        for x, y, vx, vy, life, col in parts:
            c = tuple(int(v * min(1.0, life * 1.4)) for v in col)
            d.line([(x, y), (x - vx * 0.03, y - vy * 0.03)], fill=c, width=2 if life > 0.5 else 1)
