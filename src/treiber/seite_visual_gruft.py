"""Bewohner der „Kellertreppe“ (Mixin CellarCrew): Zombies steigen aus dem Boden und schlurfen im Takt, ein Skelett
tanzt aus dem Kellerschrank. Wie viele dauerhaft da sind, hängt von der Gänsehaut-Stufe ab (1: Skelett, 2: Skelett und
zwei Zombies, 3: Skelett und eine Horde von vier Zombies). Beim Höhepunkt flüchten die Zombies vor dem Staubsauger
zurück in den Boden und das Skelett in den Schrank; bei Wortbeiträgen sitzen alle auf der Treppe und hören dem
zeitunglesenden Monster zu; bei einem Liedwechsel taucht ein Zombie ab und an anderer Stelle wieder auf.
Gags (zusätzlich zu Spinne, Mäusen, Staubwedel, Socke): Zombie verliert den Arm, Zombie futtert Einmachgläser,
Zombie in der Mäuse-Polonaise, Skelett-Xylophon, Skelett zerfällt (auch bei sehr kräftigem Bass) und setzt sich falsch
zusammen, Besuch vom Hausverwalter-Zombie (Nebenkosten, Zettel „Ruhezeiten beachten!“), Graf Kellerstein (stößt sich
den Kopf am Balken) und die Mumie (wickelt sich beim Tanzen ab).
"""
import math
import random

CL_CREW = {1: 0, 2: 2, 3: 4}            # Zombies je Gänsehaut-Stufe (dazu immer das Skelett)
CL_ROAM = (152, 234)                    # hier schlurfen die Bewohner herum
CL_SEATS = [62, 88, 114, 140, 75]       # Plätze auf der Treppe (x) bei Wortbeiträgen
CL_CLOSET = (202, 96, 236, CL_FLOOR)    # Kellerschrank (Skelett)
CL_BEAM = (44, 22, 120, 31)             # niedriger Deckenbalken über der Treppe
CL_DOOR_X = 14                          # Tür oben links (Besuch kommt hier herein)
CL_RISE, CL_SINK = 1.8, 0.9             # aus dem Boden steigen / versinken (s)
CL_ZOMBIE_H = 65                        # Höhe einer stehenden Figur (Füße bis Scheitel)
CL_SK_POSES = [                         # Skelett: Hände/Füße relativ zu Schulter/Hüfte
    {"lh": (-10, -16), "rh": (10, -16), "lf": (-5, 24), "rf": (5, 24)},
    {"lh": (-12, 8), "rh": (12, 8), "lf": (-7, 24), "rf": (9, 14)},
    {"lh": (-4, -18), "rh": (14, 4), "lf": (-9, 14), "rf": (5, 24)},
    {"lh": (-14, -4), "rh": (14, -4), "lf": (-6, 24), "rf": (6, 24)},
]
CL_ZOMBIE_SAY = ["Hiiirn …", "Uuuarg.", "Mmmh, Keller.", "Wo ist die Party?"]


def _cl_surface(x):
    """Höhe des Bodens bei x: Treppenabsatz, Stufe oder Kellerboden (Füße stehen darauf)."""
    if x < CL_STAIR_X0:
        return CL_STAIR_Y0
    i = int((x - CL_STAIR_X0) // CL_STEP_W)
    if i < CL_STEPS:
        return CL_STAIR_Y0 + (i + 1) * CL_STEP_H
    return CL_FLOOR


class CellarCrew:
    # -- Figuren --------------------------------------------------------------- #
    def _cl_zombie(self, img, d, x, y, t, face, gait, level, arm=True, sit=False, reach=None, suit=False,
                   duck=0.0, mouth=0.5):
        """Zombie (oder mit suit=True der Hausverwalter im grauen Anzug). face = Blickrichtung ±1, gait = Phase
        der Schritte, reach = (x, y) Ziel einer Hand (sonst Arme nach vorn), duck 0…1 = geduckt."""
        skin = (150, 160, 120) if suit else (124, 158, 104)
        cloth = (104, 106, 116) if suit else (96, 84, 116)
        pants = (84, 86, 96) if suit else (64, 62, 84)
        hip = (x, y - (0 if sit else 24 - 4 * duck))
        for side in (-1, 1):
            hj = (hip[0] + side * 4, hip[1])
            if sit:
                knee, foot = (hj[0] + side * 4, hj[1] + 3), (hj[0] + side * 5, y + CL_STEP_H - 1)
            else:
                swing = math.sin(gait) * 4 * side
                knee, foot = _ik(hj, (hj[0] + swing + face, y - 1), 12, 13, face)
            self._limb(img, hj, knee, 6, pants)
            self._limb(img, knee, foot, 5, pants)
            self._blob(img, foot[0] + face * 2, foot[1], 9, 5, (40, 36, 34), gloss=0.4)
        top = hip[1] - 21 + 5 * duck
        self._blob(img, x + face, hip[1] - 11, 19, 25, cloth, gloss=0.25)
        if suit:                                                                    # Hemd und Krawatte
            d.polygon([(x - 3 + face, top + 1), (x + 3 + face, top + 1), (x + face, top + 9)], fill=(236, 236, 230))
            d.line([(x + face, top + 3), (x + face, top + 13)], fill=(180, 30, 40), width=2)
        else:                                                                       # Risse im Hemd
            d.line([(x - 6, hip[1] - 6), (x - 2, hip[1] - 2), (x - 5, hip[1] + 1)], fill=(60, 50, 76))
            d.line([(x + 4, hip[1] - 16), (x + 7, hip[1] - 12)], fill=(60, 50, 76))
        hands = []
        for side in (-1, 1):
            sh = (x + side * 8, top + 2)
            if not arm and side == face:
                self._blob(img, sh[0], sh[1] + 2, 6, 6, cloth, gloss=0.2)            # Stumpf
                hands.append(None)
                continue
            if reach is not None and side == face:
                target = reach
            elif sit:
                target = (sh[0] + side * 2, sh[1] + 14)
            else:
                target = (sh[0] + face * 18, sh[1] + 2 + math.sin(t * 2.3 + side) * 2)
            elbow, hand = _ik(sh, target, 10, 10, -side)
            self._limb(img, sh, elbow, 5, cloth)
            self._limb(img, elbow, hand, 4, skin)
            self._blob(img, hand[0], hand[1], 6, 6, skin, gloss=0.2)
            hands.append(hand)
        head = (x + face * 2, top - 11 + math.sin(t * 1.7) * 1.2)
        self._blob(img, head[0], head[1], 15, 16, skin, gloss=0.25)
        if suit:                                                                    # Seitenscheitel
            d.chord([head[0] - 8, head[1] - 9, head[0] + 8, head[1] - 1], 180, 360, fill=(70, 66, 60))
            d.line([(head[0] - 7, head[1] - 4), (head[0] + 7, head[1] - 6)], fill=(70, 66, 60), width=1)
        else:
            for k in (-4, 0, 3):
                d.line([(head[0] + k, head[1] - 8), (head[0] + k - 1, head[1] - 11)], fill=(50, 46, 40))
            d.line([(head[0] + 2, head[1] - 4), (head[0] + 6, head[1] + 1)], fill=(80, 60, 60))     # Narbe
        for side in (-1, 1):
            ex = head[0] + side * 3.5 + face
            if level >= 3 and not suit:
                self._blob(img, ex, head[1] - 1, 7, 6, (255, 60, 40), alpha=0.6, flat=True)
                d.ellipse([ex - 1.5, head[1] - 2.5, ex + 1.5, head[1] + 0.5], fill=(255, 70, 50))
            else:
                d.ellipse([ex - 2, head[1] - 3, ex + 2, head[1] + 1], fill=(238, 236, 214))
                d.point((ex + face * 0.8, head[1] - 1), fill=(20, 20, 20))
        mh = 1 + 4 * mouth
        d.ellipse([head[0] - 3 + face, head[1] + 3, head[0] + 3 + face, head[1] + 3 + mh], fill=(50, 20, 24))
        return head, hands

    def _cl_skeleton(self, img, d, x, y, t, pose, sit=False, scramble=False, jaw=0.0, sticks=False):
        """Skelett. scramble: falsch zusammengesetzt (Schädel am Knie, Fußknochen auf dem Hals)."""
        bone, dark = (232, 228, 212), (30, 26, 24)
        hip = (x, y - (0 if sit else 25))
        self._blob(img, hip[0], hip[1], 15, 8, bone, gloss=0.4)                     # Becken
        knees = []
        for side, key in ((-1, "lf"), (1, "rf")):
            hj = (hip[0] + side * 4, hip[1] + 2)
            if sit:
                knee, foot = (hj[0] + side * 4, hj[1] + 3), (hj[0] + side * 5, y + CL_STEP_H - 1)
            else:
                f = pose[key]
                knee, foot = _ik(hj, (hip[0] + f[0], hip[1] + f[1]), 12, 13, side)
            d.line([hj, knee, foot], fill=bone, width=3)
            d.ellipse([knee[0] - 2, knee[1] - 2, knee[0] + 2, knee[1] + 2], fill=bone)
            d.ellipse([foot[0] - 4, foot[1] - 2, foot[0] + 3, foot[1] + 1], fill=bone)
            knees.append(knee)
        top = hip[1] - 20
        d.line([hip, (x, top)], fill=bone, width=3)                                 # Wirbelsäule
        for k in range(4):                                                          # Rippen
            yy = top + 3 + k * 3.5
            w = 9 - abs(k - 1.2) * 1.2
            d.arc([x - w, yy - 2, x + w, yy + 4], 200, 340, fill=bone, width=2)
        hands = []
        for side, key in ((-1, "lh"), (1, "rh")):
            sh = (x + side * 8, top + 1)
            h = pose[key]
            elbow, hand = _ik(sh, (sh[0] + h[0], sh[1] + h[1]), 10, 10, -side)
            d.line([sh, elbow, hand], fill=bone, width=2)
            d.ellipse([hand[0] - 2.5, hand[1] - 2.5, hand[0] + 2.5, hand[1] + 2.5], fill=bone)
            if sticks:                                                              # Knochen als Schlegel
                d.line([hand, (hand[0] - side * 2, hand[1] - 9)], fill=bone, width=2)
                d.ellipse([hand[0] - side * 2 - 2, hand[1] - 11, hand[0] - side * 2 + 2, hand[1] - 7], fill=bone)
            hands.append(hand)
        if scramble:
            d.line([(x - 4, top - 2), (x + 5, top - 9)], fill=bone, width=3)        # Fußknochen statt Kopf
            sk = (knees[0][0] - 6, knees[0][1] - 1)
        else:
            sk = (x, top - 9)
        self._blob(img, sk[0], sk[1], 15, 14, bone, gloss=0.35)
        for side in (-1, 1):
            d.ellipse([sk[0] + side * 3.5 - 2.5, sk[1] - 3, sk[0] + side * 3.5 + 2.5, sk[1] + 1.5], fill=dark)
        d.polygon([(sk[0], sk[1] + 1), (sk[0] - 1.5, sk[1] + 3.5), (sk[0] + 1.5, sk[1] + 3.5)], fill=dark)
        jy = sk[1] + 6 + 3 * jaw                                                    # Unterkiefer klappert
        d.rectangle([sk[0] - 4, jy - 1, sk[0] + 4, jy + 2], fill=bone)
        for k in range(4):
            d.line([(sk[0] - 3 + k * 2, sk[1] + 5), (sk[0] - 3 + k * 2, jy)], fill=dark)
        return sk, hands

    def _cl_vampire(self, img, d, x, y, t, face, gait, duck=0.0, shield=False):
        """Graf Kellerstein: Umhang, hoher roter Kragen, bleiches Gesicht, Eckzähne."""
        hip = (x, y - 24 + 4 * duck)
        for side in (-1, 1):
            hj = (hip[0] + side * 4, hip[1])
            knee, foot = _ik(hj, (hj[0] + math.sin(gait) * 4 * side, y - 1), 12, 13, face)
            self._limb(img, hj, knee, 6, (30, 28, 34))
            self._limb(img, knee, foot, 5, (30, 28, 34))
            self._blob(img, foot[0] + face * 2, foot[1], 10, 5, (16, 14, 18), gloss=0.8)
        top = hip[1] - 22 + 5 * duck
        spread = 16 if shield else 10 + math.sin(t * 3) * 1.5
        d.polygon([(x - 8, top), (x + 8, top), (x + spread, hip[1] + 18), (x - spread, hip[1] + 18)], fill=(24, 18, 30))
        d.polygon([(x - 7, top + 1), (x + 7, top + 1), (x + spread - 3, hip[1] + 15), (x - spread + 3, hip[1] + 15)],
                  fill=(150, 20, 34))
        self._blob(img, x, hip[1] - 10, 16, 24, (36, 32, 40), gloss=0.4)
        d.polygon([(x - 9, top - 4), (x - 3, top + 2), (x - 11, top + 4)], fill=(170, 20, 40))      # Kragen
        d.polygon([(x + 9, top - 4), (x + 3, top + 2), (x + 11, top + 4)], fill=(170, 20, 40))
        head = (x + face * 2, top - 10)
        self._blob(img, head[0], head[1], 14, 16, (226, 226, 236), gloss=0.3)
        d.chord([head[0] - 8, head[1] - 10, head[0] + 8, head[1] + 2], 180, 360, fill=(20, 18, 24))
        d.polygon([(head[0] - 2, head[1] - 8), (head[0] + 2, head[1] - 8), (head[0], head[1] - 3)], fill=(20, 18, 24))
        for side in (-1, 1):
            ex = head[0] + side * 3.5 + face
            d.line([(ex - 2, head[1] - 1), (ex + 2, head[1])], fill=(170, 20, 40), width=2)
        d.line([(head[0] - 3, head[1] + 5), (head[0] + 3, head[1] + 5)], fill=(120, 20, 30))
        for side in (-1, 1):
            d.polygon([(head[0] + side * 2, head[1] + 5), (head[0] + side * 1, head[1] + 5),
                       (head[0] + side * 1.5, head[1] + 8)], fill=(255, 255, 255))
        if shield:                                                                  # Umhang vors Gesicht
            d.polygon([(x - 12, top - 2), (x + 14 * face, head[1] - 10), (x + 16 * face, head[1] + 8)],
                      fill=(24, 18, 30))
        return head

    def _cl_mummy(self, img, d, x, y, t, unwrap, gait, cover=False):
        """Mumie; unwrap 0…1 wickelt die Binden ab (darunter Unterhemd, Boxershorts, Ringelsocken)."""
        band, skin = (226, 214, 180), (196, 170, 132)
        hip = (x, y - 24)
        legs_band = unwrap < 0.55
        for side in (-1, 1):
            hj = (hip[0] + side * 4, hip[1])
            knee, foot = _ik(hj, (hj[0] + math.sin(gait) * 5 * side, y - 1), 12, 13, side)
            col = band if legs_band else skin
            self._limb(img, hj, knee, 6, col)
            self._limb(img, knee, foot, 5, col)
            if not legs_band:                                                       # Ringelsocken
                for k in range(3):
                    p = 0.62 + k * 0.12
                    sx, sy = knee[0] + (foot[0] - knee[0]) * p, knee[1] + (foot[1] - knee[1]) * p
                    d.line([(sx - 3, sy), (sx + 3, sy)], fill=(220, 40, 60) if k % 2 == 0 else (250, 250, 250),
                           width=2)
            self._blob(img, foot[0], foot[1], 8, 5, band if legs_band else (220, 40, 60), gloss=0.2)
        top = hip[1] - 21
        if unwrap < 0.3:
            self._blob(img, x, hip[1] - 11, 19, 25, band, gloss=0.2)
        else:
            self._blob(img, x, hip[1] - 11, 17, 24, skin, gloss=0.2)
            d.rectangle([x - 7, top + 2, x + 7, hip[1] - 2], fill=(246, 246, 240))   # Unterhemd
            d.line([(x - 4, top + 2), (x - 4, top - 1)], fill=(246, 246, 240), width=2)
            d.line([(x + 4, top + 2), (x + 4, top - 1)], fill=(246, 246, 240), width=2)
            d.rectangle([x - 8, hip[1] - 3, x + 8, hip[1] + 4], fill=(90, 140, 220))   # Boxershorts
            for k in range(3):
                d.ellipse([x - 6 + k * 5, hip[1] - 1, x - 4 + k * 5, hip[1] + 1], fill=(250, 230, 80))
        for k in range(5):                                                          # Bindenlinien
            yy = top + 2 + k * 5
            if unwrap < 0.3 or k == 4 and unwrap < 0.55:
                d.line([(x - 8, yy), (x + 8, yy + 2)], fill=(190, 178, 146))
        hands = []
        for side in (-1, 1):
            sh = (x + side * 8, top + 2)
            target = (x + side * 3, top + 10) if cover else \
                (sh[0] + side * 8, sh[1] - 12 + math.sin(t * 6 + side) * 6)
            elbow, hand = _ik(sh, target, 10, 10, -side)
            col = band if unwrap < 0.8 else skin
            self._limb(img, sh, elbow, 5, col)
            self._limb(img, elbow, hand, 4, col)
            hands.append(hand)
        head = (x, top - 11)
        self._blob(img, head[0], head[1], 15, 16, band if unwrap < 0.9 else skin, gloss=0.2)
        for k in range(3):
            d.line([(head[0] - 7, head[1] - 5 + k * 4), (head[0] + 7, head[1] - 4 + k * 4)], fill=(190, 178, 146))
        for side in (-1, 1):
            d.ellipse([head[0] + side * 3.5 - 1.5, head[1] - 2, head[0] + side * 3.5 + 1.5, head[1] + 1],
                      fill=(30, 20, 20))
        if unwrap > 0.05:                                                           # abgewickelte Binde am Boden
            ln = 10 + unwrap * 90
            pts = [(hip[0] + 6, hip[1] - 8)]
            for k in range(1, 9):
                q = k / 8
                pts.append((hip[0] + 6 + q * ln, min(y - 1, hip[1] - 8 + q * 40) + math.sin(t * 5 + k) * 1.5))
            d.line(pts, fill=band, width=3)
        return head

    def _cl_bat(self, img, d, x, y, t):
        flap = math.sin(t * 22) * 5
        self._blob(img, x, y, 7, 6, (30, 24, 36), gloss=0.3)
        for side in (-1, 1):
            d.polygon([(x + side * 2, y), (x + side * 11, y - 3 + flap), (x + side * 8, y + 2), (x + side * 5, y + 1)],
                      fill=(30, 24, 36))
        d.point((x - 1, y - 1), fill=(255, 60, 60))
        d.point((x + 1, y - 1), fill=(255, 60, 60))

    def _cl_closet(self, img, d, open_k):
        """Kellerschrank: Tür offen (open_k 0…1) zeigt das dunkle Innere."""
        x0, y0, x1, y1 = CL_CLOSET
        w = (x1 - x0 - 4) * (1 - open_k)
        if w > 1:
            d.rectangle([x0 + 2, y0 + 6, x0 + 2 + w, y1 - 4], fill=(116, 82, 54))
            d.rectangle([x0 + 5, y0 + 10, x0 + w - 1, y0 + 44], outline=(96, 66, 42))
            d.rectangle([x0 + 5, y0 + 50, x0 + w - 1, y1 - 10], outline=(96, 66, 42))
            d.ellipse([x0 + w - 4, y0 + 46, x0 + w, y0 + 50], fill=(210, 190, 110))
        if open_k > 0:                                                              # Tür steht seitlich ab
            ow = 10 * open_k
            d.polygon([(x1 - 2, y0 + 6), (x1 - 2 + ow, y0 + 2), (x1 - 2 + ow, y1), (x1 - 2, y1 - 4)],
                      fill=(108, 76, 50))

    # -- Ablauf ------------------------------------------------------------------ #
    def _cl_crew_new(self, st, t, level, demo):
        rng = st["rng"]
        crew = [{"kind": "skel", "x": 222.0, "goal": 222.0, "face": -1, "mode": "idle" if demo else "hidden",
                 "t0": t + 0.6, "next": t + 3, "arm": True}]
        n = CL_CREW.get(level, 2)
        for i in range(n):
            x = CL_ROAM[0] - 8 + (i + 0.5) * 70 / n                                # nebeneinander, links vom Schrank
            crew.append({"kind": "zombie", "x": x, "goal": x, "face": rng.choice((-1, 1)),
                         "mode": "idle" if demo else "under", "t0": t + 1.2 + 1.6 * i, "next": t + 4, "arm": True})
        st.update(crew=crew, crew_level=level, song=getattr(self, "_vis_song", ""), zerfall=-99.0, note=False,
                  jars=0, hand=None)

    def _cl_crew_can(self, st, name):
        """Kann der Gag gerade laufen? (Zombie-Gags brauchen einen Zombie, Skelett-Gags das Skelett draußen.)"""
        crew = st.get("crew") or []
        zombies = [c for c in crew if c["kind"] == "zombie" and c["mode"] == "idle"]
        skel = crew[0] if crew and crew[0]["mode"] == "idle" else None
        if name in ("arm", "glas", "polonaise"):
            return bool(zombies)
        if name in ("xylophon", "zerfall"):
            return skel is not None and st["t_now"] - st["zerfall"] > 8
        return True

    def _cl_crew(self, img, d, st, s, t, dt, level, gag, gl, boom, bt, talk, demo, bg):
        """Bewohner bewegen und zeichnen (vor dem Licht). Liefert Sprechblasen [(x, y, Text)] für danach."""
        if st.get("crew_level") != level:
            self._cl_crew_new(st, t, level, demo)
        st["t_now"] = t
        says = []
        crew = st["crew"]
        rng = st["rng"]
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        ph = ((t - s.get("beat_t", t)) / period) % 1.0
        # Liedwechsel: ein Zombie taucht ab und anderswo wieder auf (ohne Zombies: nur eine Hand)
        song = getattr(self, "_vis_song", "")
        if song != st["song"]:
            st["song"] = song
            if not demo and song and not talk and not boom:
                zs = [c for c in crew if c["kind"] == "zombie" and c["mode"] == "idle"]
                if zs:
                    z = zs[rng.randrange(len(zs))]
                    z.update(mode="sink", t0=t, respawn=True)
                else:
                    st["hand"] = (rng.uniform(150, 236), t)
        # Skelett zerfällt bei sehr kräftigem Bass (Sperre 25 s)
        skel = crew[0]
        if not demo and gag is None and skel["mode"] == "idle" and not talk and not boom and s["bass"] > 0.92 \
                and s["beats"] != st.get("zbeat") and t - st["zerfall"] > 25:
            st["zerfall"] = t
        st["zbeat"] = s["beats"]
        if gag and gag[0] == "zerfall" and gl < 0.1 and t - st["zerfall"] > 6:
            st["zerfall"] = t
        zf = t - st["zerfall"]
        # Wer gehört gerade zu einem Gag?
        zombies = [c for c in crew if c["kind"] == "zombie"]
        actor = None
        if gag and gag[0] in ("arm", "glas", "polonaise") and zombies:
            actor = zombies[0] if gag[0] != "glas" else zombies[-1]
        for i, c in enumerate(crew):
            lt = t - c["t0"]
            # Höhepunkt: Zombies in den Boden, Skelett in den Schrank; danach kommen alle wieder
            if boom and bt >= 2.2 and c["mode"] in ("idle", "rise", "out"):
                c.update(mode="sink" if c["kind"] == "zombie" else "flee", t0=t, respawn=False)
                lt = 0.0
            if not boom and c["mode"] == "gone":
                c.update(mode="under" if c["kind"] == "zombie" else "hidden", t0=t + 1.5 + i * 1.2)
                lt = t - c["t0"]
            if c["mode"] == "under" and lt >= 0:
                c.update(mode="rise", t0=t)
                lt = 0.0
            if c["mode"] == "hidden" and lt >= 0:
                c.update(mode="out", t0=t, x=219.0)
                lt = 0.0
            if c["mode"] == "rise" and lt >= CL_RISE:
                c["mode"] = "idle"
            if c["mode"] == "out" and lt >= 1.4:
                c["mode"] = "idle"
            if c["mode"] == "sink" and lt >= CL_SINK:
                if c.get("respawn"):
                    x = rng.uniform(*CL_ROAM)
                    c.update(mode="rise", t0=t + 0.6, x=x, goal=x, respawn=False)
                else:
                    c["mode"] = "gone"
            if c["mode"] == "flee" and abs(c["x"] - 219) < 1:
                c["mode"] = "gone"
            # Ziel
            if c is actor:
                continue                                                            # zeichnet der Gag
            speed = 16 if c["kind"] == "zombie" else 24
            if talk and c["mode"] in ("idle",):
                c["goal"] = CL_SEATS[i % len(CL_SEATS)]
                speed = 40
            elif c["mode"] == "flee":
                c["goal"], speed = 219.0, 70
            elif c["mode"] == "idle":
                if c["goal"] < CL_ROAM[0] - 1:                                     # von der Treppe zurück
                    c["goal"] = self._cl_lane(i, len(crew), rng)
                if abs(c["goal"] - c["x"]) < 1 and t >= c["next"] and not demo:
                    c["goal"] = self._cl_lane(i, len(crew), rng) if c["kind"] == "zombie" else rng.uniform(176, 232)
                    c["next"] = t + rng.uniform(2.5, 6)
            moving = c["mode"] in ("idle", "flee") and abs(c["goal"] - c["x"]) > 1
            if moving:
                step = max(-speed * dt, min(speed * dt, c["goal"] - c["x"]))
                c["x"] += step
                c["face"] = 1 if step > 0 else -1
            seated = talk and c["mode"] == "idle" and not moving and c["x"] < CL_ROAM[0]
            y = _cl_surface(c["x"])
            if c["kind"] == "zombie":
                if c["mode"] in ("under", "gone"):
                    continue
                gait = t * 8 if moving else math.sin(2 * math.pi * ph) * 0.5
                sway = 0 if moving or seated else math.sin(2 * math.pi * ph) * 1.5
                rise = 1.0
                if c["mode"] == "rise":
                    rise = _smooth(max(0.0, (lt - 0.6) / (CL_RISE - 0.6)))
                elif c["mode"] == "sink":
                    rise = 1 - _smooth(lt / CL_SINK)
                if c["mode"] == "rise" and lt < 0.6:                               # erst greift eine Hand heraus
                    self._cl_ground_hand(img, d, c["x"], lt / 0.6, t)
                    self._cl_cracks(d, c["x"])
                    continue
                yy = y + (1 - rise) * CL_ZOMBIE_H
                head, _ = self._cl_zombie(img, d, c["x"] + sway, yy, t, c["face"], gait, level, arm=c["arm"],
                                          sit=seated, mouth=0.5 + 0.5 * math.sin(t * 3 + i))
                if rise < 1:
                    img.paste(bg.crop((int(c["x"]) - 16, CL_FLOOR, int(c["x"]) + 16, VIS_H)),
                              (int(c["x"]) - 16, CL_FLOOR))
                    self._cl_cracks(d, c["x"])
                if c["mode"] == "sink" and boom and lt < 0.6 and c is zombies[0]:
                    says.append((head[0], head[1] - 22, "Iiih, Staubsauger!"))
                elif c["mode"] == "idle" and not talk and int(t / 9 + i * 3) % 7 == 0 and (t % 9) < 2:
                    says.append((head[0], head[1] - 22, CL_ZOMBIE_SAY[(int(t / 9) + i) % len(CL_ZOMBIE_SAY)]))
            else:
                if c["mode"] in ("hidden", "gone"):
                    continue
                k = st.get("sk_k", 0)
                if s["beats"] != st.get("sk_beat"):
                    st["sk_beat"] = s["beats"]
                    st["sk_k"] = k = k + 1
                pose = CL_SK_POSES[k % len(CL_SK_POSES)]
                jitter = math.sin(t * 60) * 1.2 if 0 <= t - s.get("hat_t", -9) < 0.1 else 0.0
                jaw = abs(math.sin(t * 9)) if s.get("active") else 0.0
                xylo = gag and gag[0] == "xylophon"
                if xylo:
                    hit = (s.get("hats", 0) % 2) and 0 <= t - s.get("hat_t", -9) < 0.15
                    pose = {"lh": (6, 10 if hit else 4), "rh": (-6, 4 if hit else 10), "lf": (-5, 24), "rf": (5, 24)}
                if moving or c["mode"] == "out":
                    pose = CL_SK_POSES[0 if int(t * 4) % 2 else 3]
                if seated:
                    pose = {"lh": (2, 12), "rh": (-2, 12), "lf": (-5, 24), "rf": (5, 24)}
                if 0 <= zf < 1.2:                                                   # zerfallen: Knochenhaufen
                    self._cl_bonepile(img, d, c["x"], y, zf)
                    if zf < 0.8:
                        says.append((c["x"], y - 40, "KLAPPER!"))
                    continue
                scramble = 1.2 <= zf < 4.6
                sk, _ = self._cl_skeleton(img, d, c["x"] + jitter, y, t, pose, sit=seated, scramble=scramble,
                                          jaw=jaw, sticks=bool(xylo))
                if scramble and zf >= 2.2:
                    says.append((c["x"], y - 74, "Moment …"))
                if xylo and 0 <= t - s.get("hat_t", -9) < 0.4:
                    d.text((c["x"] + 6 + (s.get("hats", 0) % 3) * 4, y - 58 - (t - s.get("hat_t", t)) * 30), "♪",
                           font=self.f_tiny, fill=(250, 240, 200))
                if xylo and 2.0 <= gl < 4.5:
                    says.append((c["x"], y - 74, "Tusch!"))
        if actor is not None:
            says += self._cl_zombie_gag(img, d, st, s, t, dt, level, gag, gl, actor, bg)
        if st.get("hand"):
            hx, ht = st["hand"]
            k = t - ht
            if k > 2.0:
                st["hand"] = None
            else:
                self._cl_ground_hand(img, d, hx, min(1.0, k / 0.5) * (1 - max(0.0, (k - 1.5) / 0.5)), t, wave=True)
                self._cl_cracks(d, hx)
        return says

    @staticmethod
    def _cl_lane(i, n, rng):
        """Jeder Zombie schlurft in seinem eigenen Streifen (damit die Horde nicht auf einem Haufen steht)."""
        lo, hi = CL_ROAM[0] - 8, CL_ROAM[1] + 2
        w = (hi - lo) / max(1, n - 1)
        a = lo + (i - 1) * w
        return rng.uniform(max(lo, a - 6), min(hi, a + w + 6))

    def _cl_ground_hand(self, img, d, x, k, t, wave=False):
        """Hand greift aus dem Boden (k 0…1)."""
        if k <= 0.02:
            return
        base = (x, CL_FLOOR + 2)
        tip = (x + math.sin(t * 6) * 3 * wave, CL_FLOOR - 4 - 18 * k)
        self._limb(img, base, tip, 5, (124, 158, 104))
        for j in range(4):
            a = -1.2 + j * 0.8 + math.sin(t * 8 + j) * 0.2
            d.line([tip, (tip[0] + math.sin(a) * 5, tip[1] - math.cos(a) * 5)], fill=(124, 158, 104), width=2)

    @staticmethod
    def _cl_cracks(d, x):
        for a in (-1, 1):
            d.line([(x + a * 2, CL_FLOOR + 1), (x + a * 9, CL_FLOOR + 4), (x + a * 14, CL_FLOOR + 3)], fill=(40, 36, 34))
        d.line([(x - 6, CL_FLOOR + 1), (x + 6, CL_FLOOR + 1)], fill=(30, 26, 24), width=2)

    def _cl_bonepile(self, img, d, x, y, k):
        """Skelett fällt auseinander (k = Sekunden seit dem Zerfall)."""
        bone = (232, 228, 212)
        rng = random.Random(5)
        fall = min(1.0, k / 0.5)
        for j in range(9):
            a = rng.uniform(0, math.tau)
            sx = x + math.cos(a) * 14 * fall + rng.uniform(-3, 3)
            sy = y - 30 * (1 - fall) - rng.uniform(0, 30) * (1 - fall) - rng.uniform(0, 6) * fall
            ln = rng.uniform(6, 11)
            ang = a + k * 6 * (1 - fall)
            d.line([(sx, sy), (sx + math.cos(ang) * ln, sy + math.sin(ang) * ln * 0.5)], fill=bone, width=3)
        self._blob(img, x + 2, y - 8 - 30 * (1 - fall), 15, 14, bone, gloss=0.35)
        for side in (-1, 1):
            cx, cy = x + 2 + side * 3.5, y - 9 - 30 * (1 - fall)
            d.ellipse([cx - 2.5, cy - 2, cx + 2.5, cy + 2], fill=(30, 26, 24))

    def _cl_zombie_gag(self, img, d, st, s, t, dt, level, gag, gl, z, bg):
        """Gags mit einem Zombie: Arm verloren, Einmachglas, Polonaise."""
        says = []
        name = gag[0]
        if name == "arm":
            # 0–1,4 Arm fällt ab, 1,4–3,6 sucht („Mein Arm?!“), 3,6–7 Maus schleppt ihn weg, Zombie hinterher,
            # 7–9 kommt mit Arm zurück (falsch herum angesetzt)
            x0 = z.setdefault("gag_x", z["x"])
            ax = x0 + 12 * z["face"] if gl < 3.6 else x0 + 12 * z["face"] + (gl - 3.6) * 34
            if gl < 3.6:
                zx = x0
            elif gl < 7:
                zx = x0 + (gl - 3.6) * 26
            else:
                zx = x0 + 3.4 * 26 - (gl - 7) / 2 * 3.4 * 26
            face = 1 if 3.6 <= gl < 7 else (-1 if gl >= 7 else z["face"])
            has_arm = gl < 0.4 or gl >= 7
            y = CL_FLOOR
            if not has_arm and gl < 7:                                             # Arm am Boden
                fy = y - 2 if gl > 0.9 else y - 30 + (gl - 0.4) / 0.5 * 28
                self._limb(img, (ax - 8, fy), (ax + 6, fy), 4, (124, 158, 104))
                self._blob(img, ax + 8, fy, 6, 6, (124, 158, 104))
            if 3.6 <= gl < 7:
                self._cl_mouse(img, d, ax + 14, y, t, None)
            look = math.sin(t * 4) if 1.4 <= gl < 3.6 else 0
            head, _ = self._cl_zombie(img, d, zx, y, t, face if look == 0 else (1 if look > 0 else -1),
                                      t * 8 if 3.6 <= gl < 9 else 0.0, level, arm=has_arm)
            if 1.4 <= gl < 3.6:
                says.append((head[0], head[1] - 22, "Mein Arm?!"))
            elif 7.2 <= gl < 9:
                says.append((head[0], head[1] - 22, "Passt schon."))
            z["x"], z["goal"] = zx, zx
            if gl >= CL_GAGS["arm"] - dt * 1.5:
                z.pop("gag_x", None)
        elif name == "glas":
            # Zombie geht zum Regal, greift ein Einmachglas, futtert („Mampf … Gurken von 1987!“)
            x0 = z.setdefault("gag_x", z["x"])
            gx = 250.0
            if gl < 3:
                zx = x0 + (gx - x0) * _smooth(gl / 3)
            elif gl < 7:
                zx = gx
            else:
                zx = gx + (x0 - gx) * _smooth((gl - 7) / 2)
            reach = None
            if 3 <= gl < 4.2:
                reach = (258, 112)
            elif 4.2 <= gl < 7:
                reach = (zx + 4, CL_FLOOR - 50 + abs(math.sin(t * 8)) * 3)
            face = 1 if gl < 7 else -1
            head, hands = self._cl_zombie(img, d, zx, CL_FLOOR, t, face, t * 8 if gl < 3 or gl >= 7 else 0.0, level,
                                          reach=reach, mouth=abs(math.sin(t * 8)) if 4.2 <= gl < 7 else 0.4)
            if 4.2 <= gl < 7 and hands[1]:                                          # Glas in der Hand
                hx, hy = hands[1]
                d.rectangle([hx - 4, hy - 9, hx + 4, hy + 2], fill=(110, 150, 70))
                d.rectangle([hx - 5, hy - 11, hx + 5, hy - 9], fill=(200, 196, 180))
            if 4.4 <= gl < 7:
                says.append((head[0], head[1] - 22, "Mampf … Gurken von 1987!"))
            if gl >= 4.2:
                st["jars"] = max(st["jars"], 1)
            z["x"], z["goal"], z["face"] = zx, zx, face
            if gl >= CL_GAGS["glas"] - dt * 1.5:
                z.pop("gag_x", None)
        elif name == "polonaise":
            # Zombie hüpft hinter den Mäusen her nach rechts hinaus und steigt dann wieder aus dem Boden
            hats = [(230, 60, 100), (60, 170, 230), (250, 200, 60), (110, 200, 90)]
            span = CL_GAGS["polonaise"] - 1.6
            ph = (t - s.get("beat_t", t)) / max(0.3, s.get("period") or 0.5)
            xs = []
            for j in range(4):
                mx = -20 + (WIDTH + 90) * min(1.0, gl / span) - j * 18
                hop = abs(math.sin(min(1.0, ph) * math.pi)) * 5 if (j + s["beats"]) % 2 else 0
                self._cl_mouse(img, d, mx, CL_FLOOR - hop, t, hats[j])
                xs.append(mx)
            zx = xs[-1] - 26
            hop = abs(math.sin(min(1.0, ph) * math.pi)) * 6
            if -20 < zx < WIDTH + 20:
                head, _ = self._cl_zombie(img, d, zx, CL_FLOOR - hop, t, 1, t * 10, level,
                                          reach=(zx + 20, CL_FLOOR - 14))
                if 2 <= gl < 4.5:
                    says.append((head[0], head[1] - 22, "Polonääääse!"))
            if gl >= span:
                x = st["rng"].uniform(*CL_ROAM)
                z.update(x=x, goal=x, mode="rise", t0=t)
        return says

    def _cl_visitor(self, img, d, st, s, t, level, gag, gl, bx, by):
        """Besuch über die Kellertür: Hausverwalter-Zombie, Graf Kellerstein, Mumie (kommt von rechts)."""
        says = []
        name = gag[0]
        if name == "hausverwalter":
            # 0–4 herunter, 4–7,5 Nebenkosten an das Skelett/den Zombie, 7,5–9 Zettel an die Wand, 9–12 wieder hinauf
            if gl < 4:
                x = CL_DOOR_X + (170 - CL_DOOR_X) * _smooth(gl / 4)
                face = 1
            elif gl < 7.5:
                x, face = 170.0, 1
            elif gl < 9:
                x, face = 170 - (170 - 126) * _smooth((gl - 7.5) / 1.5), -1
            else:
                x, face = 126 - (126 - CL_DOOR_X) * _smooth((gl - 9) / 3), -1
            duck = 1.0 if CL_BEAM[0] - 10 < x < CL_BEAM[2] + 4 and _cl_surface(x) < 130 else 0.0
            reach = None
            if 4.6 <= gl < 7.0:
                reach = (x + 18, CL_FLOOR - 40)
            elif 7.8 <= gl < 9:
                reach = (118, 92)
            head, hands = self._cl_zombie(img, d, x, _cl_surface(x), t, face, t * 7 if gl < 4 or gl >= 7.5 else 0.0,
                                          level, suit=True, duck=duck, reach=reach, mouth=0.3)
            if hands[0] and not reach:                                             # Aktentasche
                hx, hy = hands[0]
                d.rectangle([hx - 6, hy + 2, hx + 6, hy + 11], fill=(90, 56, 36))
                d.rectangle([hx - 2, hy - 1, hx + 2, hy + 2], outline=(60, 36, 24))
            if reach and 4.6 <= gl < 7.0:                                           # Abrechnung
                d.rectangle([reach[0] - 2, reach[1] - 8, reach[0] + 8, reach[1] + 4], fill=(250, 250, 244))
                for k in range(3):
                    d.line([(reach[0], reach[1] - 5 + k * 3), (reach[0] + 6, reach[1] - 5 + k * 3)],
                           fill=(120, 120, 130))
            if 4.6 <= gl < 7.2:
                says.append((head[0], head[1] - 22, "Nebenkosten! Nachzahlung: 3 Seelen."))
            elif 7.6 <= gl < 9.2:
                says.append((head[0], head[1] - 22, "Ruhezeiten beachten!"))
            if gl >= 8.6:
                st["note"] = True
        elif name == "vampir":
            # 0–1,6 aus der Tür, BONK am Balken, 1,6–4 Sterne („Au! Wer baut so niedrige Keller?!“), geduckt hinunter,
            # 7–8,6 Licht! (Umhang vors Gesicht), dann als Fledermaus zum Fenster hinaus
            if gl < 1.6:
                x = CL_DOOR_X + (36 - CL_DOOR_X) * gl / 1.6
            elif gl < 4:
                x = 36.0
            elif gl < 7:
                x = 36 + (170 - 36) * _smooth((gl - 4) / 3)
            else:
                x = 170.0
            if gl < 8.6:
                duck = 1.0 if gl >= 4 and x < CL_BEAM[2] + 4 else 0.0
                head = self._cl_vampire(img, d, x, _cl_surface(x), t, 1 if gl < 7 else (1 if bx > x else -1),
                                        t * 7 if gl < 1.6 or 4 <= gl < 7 else 0.0, duck=duck, shield=gl >= 7)
                if 1.6 <= gl < 3.2:                                                 # Sterne um den Kopf
                    for j in range(4):
                        a = t * 6 + j * math.pi / 2
                        sx, sy = head[0] + math.cos(a) * 12, head[1] - 8 + math.sin(a) * 4
                        d.text((sx - 3, sy - 5), "*", font=self.f_tiny, fill=(255, 230, 80))
                if 1.6 <= gl < 2.3:
                    says.append((head[0] + 30, CL_BEAM[3] + 8, "BONK!"))
                elif 2.3 <= gl < 4.2:
                    says.append((head[0] + 40, head[1] - 4, "Au! Wer baut so niedrige Keller?!"))
                elif 7.0 <= gl < 8.6:
                    says.append((head[0], head[1] - 22, "Licht! Aaargh!"))
            else:
                k = (gl - 8.6) / (CL_GAGS["vampir"] - 8.6)
                wx = (CL_WINDOW[0] + CL_WINDOW[2]) / 2
                self._cl_bat(img, d, 170 + (wx - 170) * k, CL_FLOOR - 50 - (CL_FLOOR - 50 - 18) * k
                             - math.sin(k * math.pi) * 20, t)
        elif name == "mumie":
            # tanzt von rechts herein, wickelt sich beim Tanzen ab, „Huch!“ und läuft davon
            if gl < 2.4:
                x = WIDTH + 20 - (WIDTH + 20 - 196) * _smooth(gl / 2.4)
            elif gl < 9:
                x = 196 + math.sin((gl - 2.4) * 2) * 10
            else:
                x = 196 + (gl - 9) * 90
            unwrap = max(0.0, min(1.0, (gl - 2.6) / 6))
            head = self._cl_mummy(img, d, x, CL_FLOOR, t, unwrap, t * 8, cover=gl >= 8.6)
            if 8.6 <= gl < 10:
                says.append((head[0], head[1] - 22, "Huch!"))
            elif 3.5 <= gl < 5.5:
                says.append((head[0], head[1] - 22, "Ich bin so frei!"))
        return says
