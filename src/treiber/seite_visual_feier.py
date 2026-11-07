"""Visualisierung „Weihnachten“, Option „Feierabend“: Weihnachtsmann und Weihnachtsfrau trinken Glühwein über
den Durst. Eine Runde (Einstellung visual.xmas.party_len) läuft als feste Folge von Schritten (PARTY_STEPS):
prosten → Schluckauf → Pipi-Tanz → hinter den Baum (beide nacheinander) → „War das Rentier!“ → „HO HO H“ in den
Schnee → gelber Schnee → grünes Gesicht → „Schöne Bescherung“ in den Geschenkesack → Kater auf der Bank →
„Nur noch einen …“, dann beginnt die Runde von vorn. Die Zeit der Runde läuft nur, solange Musik spielt.
Bei einem Wortbeitrag nach dem grünen Gesicht schlafen beide auf der Bank ein (mit Kater), danach folgt
„Nur noch einen …“. Alles bleibt comichaft; Standard ist aus (Option party = off/on/evening).
"""

PARTY_PAIR = {"santa": 160, "mrs": 226}
PARTY_POT_X = 300                         # Glühweintopf am rechten Rand
PARTY_SACK_X = 268                        # Geschenkesack (Bescherung)
PARTY_PUDDLE_X = XMAS_TREE_X + 56         # Pfütze rechts neben dem Baum
PARTY_SIGN = "HO HO H"                    # in den Schnee geschrieben (beim letzten O geht es aus)
PARTY_SIGN_X = 150
# Schritte einer Runde: (Name, feste Dauer in Sekunden) oder (Name, None, Gewicht, Mindestdauer) – die
# Schritte ohne feste Dauer teilen sich den Rest der eingestellten Rundenlänge im Verhältnis der Gewichte.
PARTY_STEPS = [
    ("prost", None, 3, 20), ("hicks", None, 2, 20), ("pipi", 10), ("baum", 8), ("baum2", 7), ("rentier", 6),
    ("signatur", 9), ("gelb", 7), ("gruen", 6), ("bescherung", 8), ("kater", None, 1, 20), ("noch", 7),
]
PARTY_SICK_FROM = "gruen"                 # ab hier schlafen beide bei einem Wortbeitrag ein
PARTY_BENCH = {"santa": XMAS_BENCH_X + 24, "mrs": XMAS_BENCH_X - 18}    # er sitzt jetzt rechts (kam von rechts)
PARTY_GREEN = (150, 205, 120)


def party_timeline(length):
    """[(Name, Beginn, Dauer)] einer Runde von length Sekunden."""
    fixed = sum(s[1] for s in PARTY_STEPS if s[1] is not None)
    weights = sum(s[2] for s in PARTY_STEPS if s[1] is None)
    rest = max(0.0, length - fixed)
    out, t0 = [], 0.0
    for s in PARTY_STEPS:
        dur = s[1] if s[1] is not None else max(s[3], rest * s[2] / weights)
        out.append((s[0], t0, dur))
        t0 += dur
    return out


def party_active(opts, hour=None):
    """Option „Feierabend“: an, aus oder nur abends (20 bis 4 Uhr)."""
    mode = opts.get("party", "off")
    if mode == "on":
        return True
    if mode == "evening":
        hour = time.localtime().tm_hour if hour is None else hour
        return hour >= 20 or hour < 4
    return False


def _lerp(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


class XmasParty:
    vis_green = False                  # Feierabend: grünes Gesicht – Tastatur bei „Rot und Grün“ grün
    # -- Ablauf -------------------------------------------------------------- #
    def _xmas_party(self, st, t, dt, o, moving, talk, new_beat, enter):
        """Stand der Feierabend-Runde: Ziele und Zustände der Figuren, Pegel, grünes Gesicht, Requisiten.
        None = Option aus."""
        if not party_active(o):
            st.pop("party", None)
            self.vis_green = False
            return None
        length = int(o["party_len"]) if str(o.get("party_len")).isdigit() else 600
        steps = party_timeline(max(120, length))
        total = steps[-1][1] + steps[-1][2]
        ps = st.setdefault("party", {"p": 0.0, "sleep": False, "prost_t": -9.0, "hic": None, "n": 0})
        names = [s[0] for s in steps]
        idx = next((i for i, s in enumerate(steps) if s[1] <= ps["p"] < s[1] + s[2]), 0)
        if talk:
            if names.index(PARTY_SICK_FROM) <= idx < names.index("noch"):
                ps["sleep"] = True                                  # zu viel getrunken: Schlaf auf der Bank
        else:
            if ps["sleep"]:
                ps["sleep"] = False
                ps["p"] = steps[names.index("noch")][1]             # aufgewacht: „Nur noch einen …“
            elif moving:
                ps["p"] += dt
            if ps["p"] >= total:
                ps["p"] = 0.0
        idx = next((i for i, s in enumerate(steps) if s[1] <= ps["p"] < s[1] + s[2]), 0)
        name, start, dur = steps[idx]
        lt = ps["p"] - start
        P = {"step": name, "idx": idx, "lt": lt, "dur": dur, "goals": dict(PARTY_PAIR), "states": {},
             "back": {}, "say": [], "hat": True, "green": 0.0, "mugs": False, "stream": None, "puke": None,
             "flake": None, "cat": None, "zzz": False, "flicker": False, "after": set()}
        P["lvl"] = {"prost": 0.1 + 0.4 * lt / dur, "hicks": 0.5 + 0.4 * lt / dur,
                    "kater": 1.0 - 0.6 * lt / dur, "noch": 0.4}.get(name, 1.0)
        for i, (n, _s, _d) in enumerate(steps):                     # was schon geschehen ist (Pfütze, Schrift …)
            if i < idx:
                P["after"].add(n)
        if name in ("prost", "hicks"):
            P["mugs"] = True
            self._xmas_party_beats(ps, P, t, new_beat, name)
        getattr(self, "_party_" + name, lambda P, lt: None)(P, lt)
        if talk:
            bench = PARTY_BENCH if ps["sleep"] else {"santa": XMAS_BENCH_X - 18, "mrs": XMAS_BENCH_X + 24}
            P["goals"], P["back"], P["mugs"] = dict(bench), {}, False
            P["states"] = {"santa": "p_sleep", "mrs": "p_sleep"} if ps["sleep"] else {}
            P["stream"] = P["puke"] = P["flake"] = None
            P["say"], P["hat"], P["flicker"] = [], True, False
            if ps["sleep"]:
                P["zzz"], P["cat"] = True, 1.0
        if name == "noch":                                          # neuer Morgen: Spuren sind weggeräumt
            P["after"] = set()
        self.vis_green = P["green"] > 0.5
        return P

    def _xmas_party_beats(self, ps, P, t, new_beat, name):
        """Auf den Takt: alle 8 Schläge prosten, beim Schluckauf jeden 3. Schlag „Hicks!“."""
        if new_beat:
            ps["n"] += 1
            if ps["n"] % 8 == 4:
                ps["prost_t"] = t
            elif name == "hicks" and ps["n"] % 3 == 0 and t - ps["prost_t"] > 1.8:
                ps["hic"] = ("mrs" if (ps["n"] // 3) % 3 == 2 else "santa", t)
        k = t - ps["prost_t"]
        if 0 <= k < 1.8:
            P["prost"] = k
            if k < 0.9:
                P["say"].append(("mid", "Prost!"))
        if ps["hic"] and 0 <= t - ps["hic"][1] < 0.8:
            P["hic"] = (ps["hic"][0], t - ps["hic"][1])
            P["say"].append((ps["hic"][0], "Hicks!"))

    # Die einzelnen Schritte: Ziele (x), Zustände (p_*) und was dazu gezeichnet wird
    @staticmethod
    def _party_pipi(P, lt):
        P["states"] = {"santa": "p_pipi", "mrs": "p_clap" if lt < 4 else "p_pipi"}
        if 1.0 <= lt < 3.6:
            P["say"].append(("mrs", "Toller Schritt!"))

    @staticmethod
    def _party_baum(P, lt):
        P["goals"] = {"santa": XMAS_TREE_X, "mrs": 128}
        P["states"] = {"santa": "p_behind", "mrs": "p_wait"}
        if 2.2 <= lt < 6.6:
            P["stream"] = ("tree", lt - 2.2)
            P["flicker"] = True
        if 4.6 <= lt < 7.2:
            P["say"].append(("mrs", "Mach hin!"))

    @staticmethod
    def _party_baum2(P, lt):
        P["goals"] = {"santa": 200, "mrs": XMAS_TREE_X}
        P["states"] = {"santa": "p_whistle", "mrs": "p_behind"}
        P["say"].append(("santa", "♪ ♫"))
        if 2.8 <= lt < 6.2:
            P["say"].append(("tree", "Ahh …"))
            P["flicker"] = True

    @staticmethod
    def _party_rentier(P, lt):
        P["goals"] = {"santa": 210, "mrs": 128}
        P["states"] = {"santa": "p_excuse" if lt >= 2.8 else "p_whistle", "mrs": "p_point"}
        if 0.6 <= lt < 2.8:
            P["say"].append(("mrs", "Wer war das?!"))
        elif lt >= 3.0:
            P["say"].append(("santa", "War das Rentier!"))

    @staticmethod
    def _party_signatur(P, lt):
        P["goals"] = {"santa": 246, "mrs": 96}
        P["states"] = {"santa": "p_write", "mrs": "p_tsk"}
        if 1.0 <= lt < 7.0:
            P["stream"] = ("sign", lt - 1.0)
        if lt >= 7.0:
            P["say"].append(("mrs", "Typisch."))

    @staticmethod
    def _party_gelb(P, lt):
        P["goals"] = {"santa": 246 if lt < 2.2 else 182 if lt < 4.2 else 226, "mrs": 128 if lt < 4.2 else 176}
        P["states"] = {"santa": "p_grab" if lt < 4.2 else None, "mrs": "p_tongue" if lt < 4.2 else "p_worry"}
        P["flake"] = lt
        if 3.4 <= lt < 6.0:
            P["say"].append(("santa", "Nicht den gelben!"))

    @staticmethod
    def _party_gruen(P, lt):
        P["goals"] = {"santa": 226, "mrs": 176}
        P["states"] = {"santa": "p_sick", "mrs": "p_worry"}
        P["green"] = min(1.0, lt / 4.0)
        if 1.0 <= lt < 5.0:
            P["say"].append(("santa", "Mir ist nicht gut …"))

    @staticmethod
    def _party_bescherung(P, lt):
        P["goals"] = {"santa": 226, "mrs": 176}
        P["states"] = {"santa": "p_vomit" if lt >= 0.6 else "p_sick", "mrs": "p_hat" if lt >= 1.0 else "p_worry"}
        P["green"] = 1.0
        P["hat"] = lt < 1.0
        for a in (1.6, 3.2, 4.6):                                   # drei Schwalle
            if a <= lt < a + 0.8:
                P["puke"] = (lt - a) / 0.8
        if lt >= 5.6:
            P["say"].append(("mrs", "Na, schöne Bescherung!"))

    @staticmethod
    def _party_kater(P, lt):
        P["goals"] = dict(PARTY_BENCH)
        P["states"] = {"santa": "p_sleep", "mrs": "p_sleep"}
        P["green"] = max(0.0, 1.0 - lt / 8.0)
        P["zzz"] = True
        if lt >= 3.0:
            P["cat"] = min(1.0, (lt - 3.0) / 0.6)

    @staticmethod
    def _party_noch(P, lt):
        if lt < 3.6:
            P["goals"] = {"santa": 276, "mrs": 226 if lt >= 1.4 else PARTY_BENCH["mrs"]}
            P["states"] = {"santa": "p_stagger", "mrs": "p_pull"}
            if lt < 3.0:
                P["say"].append(("santa", "Nur noch einen …"))
        else:
            P["back"] = {"santa": True}                             # sie zieht ihn rückwärts zurück

    # -- Haltungen ----------------------------------------------------------- #
    @staticmethod
    def _xmas_party_pose(who, state, t, lt):
        """Haltung für die Zustände p_* (Hände/Füße wie SANTA_POSES/MRS_POSES)."""
        base = {"bob": 0.0, "dx": 0.0, "spin": 0.0}
        sw = math.sin(t * 7)
        if state in ("p_pipi", "p_wait", "p_behind"):               # Knie zusammen, von einem Bein aufs andere
            tap = max(0.0, math.sin(t * 9))
            if who == "santa":
                return dict(base, lh=(16, 36), rh=(-16, 36), lf=(5, 40 - 6 * max(0.0, sw)),
                            rf=(-5, 40 - 6 * max(0.0, -sw)), lean=sw * 3, head=10, bob=abs(sw) * 2)
            pose = dict(base, lh=(10, 30), rh=(-10, 30), lf=(3, 22 - 4 * max(0.0, sw)), rf=(-3, 22 - 4 * max(0.0, -sw)),
                        lean=sw * 3, head=-8, bob=abs(sw) * 1.5)
            if state == "p_wait":
                pose.update(rf=(6, 22 - 6 * tap), lf=(-2, 22))      # tippt mit dem Fuß
            return pose
        if state == "p_clap":
            c = 4 * abs(math.sin(t * 6))
            return dict(MRS_POSES[3], lh=(14 + c, 8), rh=(-14 - c, 8), **base)
        if state == "p_whistle":
            return dict(base, lh=(-4, 34), rh=(4, 34), lf=(-3, 40), rf=(3, 40), lean=math.sin(t * 2) * 3,
                        head=math.sin(t * 4) * 8)
        if state == "p_point":
            return dict(base, lh=(-28, 18), rh=(6, 28), lf=(-3, 22), rf=(3, 22), lean=-6, head=-10)
        if state == "p_excuse":
            return dict(base, lh=(14, 22), rh=(32, -4), lf=(-4, 40), rf=(4, 40), lean=4, head=10)
        if state == "p_write":
            return dict(base, lh=(16, 36), rh=(-16, 36), lf=(-10, 39), rf=(10, 39), lean=-3, head=-12,
                        bob=math.sin(t * 3))
        if state == "p_tsk":
            return dict(base, lh=(6, 28), rh=(-6, 28), lf=(-3, 22), rf=(3, 22), lean=0, head=math.sin(t * 6) * 10)
        if state == "p_tongue":
            return dict(base, lh=(-24, -6), rh=(24, -6), lf=(-4, 22), rf=(4, 22), lean=-2, head=0)
        if state == "p_grab":
            return dict(base, lh=(-32, 4), rh=(14, 22), lf=(-8, 39), rf=(6, 40), lean=-8, head=-8)
        if state == "p_sick":
            return dict(base, lh=(14, 22), rh=(-14, 22), lf=(-4, 40), rf=(4, 40), lean=math.sin(t * 1.6) * 8,
                        head=math.sin(t * 2.1) * 12, bob=math.sin(t * 1.6) * 1.5)
        if state == "p_worry":
            return dict(base, lh=(10, 12), rh=(-10, 12), lf=(-3, 22), rf=(3, 22), lean=-2, head=8)
        if state == "p_vomit":
            return dict(base, lh=(14, 22), rh=(24, 20), lf=(-8, 39), rf=(10, 38), lean=18, head=22)
        if state == "p_hat":
            return dict(base, lh=(10, 14), rh=(18, -18), lf=(-3, 22), rf=(3, 22), lean=2, head=10)
        if state == "p_sleep":
            pose = {"lh": (14, 22), "rh": (-14, 22), "lf": (0, 0), "rf": (0, 0), "lean": 0,
                    "head": 22 if who == "santa" else -20, "bob": math.sin(t * 0.8) * 0.8, "dx": 0.0, "spin": 0.0}
            return pose if who == "santa" else dict(pose, lh=(10, 16), rh=(-10, 16))
        if state == "p_pull":
            return dict(base, lh=(-20, 10), rh=(28, 6), lf=(-8, 21), rf=(4, 22), lean=-10, head=-6)
        return dict(base, lh=(14, 22), rh=(-14, 22), lf=(-2, 40), rf=(2, 40), lean=0, head=4)   # p_stagger u. a.

    def _xmas_party_mods(self, P, who, pose, t):
        """Pegel: wackliger Stand; prosten (freie Hand hoch, dann zum Mund); Hüpfer beim Schluckauf."""
        lvl = P["lvl"]
        ph = 0.0 if who == "santa" else 1.7
        pose["lean"] = pose.get("lean", 0) + math.sin(t * 1.3 + ph) * 8 * lvl
        pose["dx"] = pose.get("dx", 0.0) + math.sin(t * 0.9 + ph) * 4 * lvl
        k = P.get("prost")
        if k is not None:
            if who == "santa":
                pose["lh"] = (-8, -30) if k < 0.9 else (21, -13)
            else:
                pose["rh"] = (8, -32) if k < 0.9 else (-14, -10)
        hic = P.get("hic")
        if hic and hic[0] == who and hic[1] < 0.2:
            pose["bob"] = pose.get("bob", 0.0) - 5
        return pose

    def _xmas_party_look(self, P, who, state):
        """Zusatzangaben fürs Zeichnen der Figur (Gesichtsfarbe, Mütze, Mund)."""
        if who == "santa":
            return {"green": P["green"], "red": P["lvl"], "hat": P["hat"], "snore": state == "p_sleep"}
        return {"mouth": state == "p_tongue", "asleep": state == "p_sleep"}

    # -- Requisiten ---------------------------------------------------------- #
    def _xmas_party_ground(self, img, d, P, floor, t):
        """Hinter den Figuren: Glühweintopf, Pfütze, Schrift im Schnee, gelber Fleck, Geschenkesack."""
        x = PARTY_POT_X                                             # Topf mit Dampf
        self._blob(img, x, floor + 1, 34, 8, (150, 165, 190), gloss=0)
        d.rectangle([x - 12, floor - 22, x + 12, floor], fill=(40, 36, 44))
        d.rectangle([x - 14, floor - 24, x + 14, floor - 20], fill=(70, 64, 78))
        d.rectangle([x - 10, floor - 16, x + 10, floor - 8], fill=(120, 30, 40))
        for k in range(3):
            pts = [(x - 6 + k * 6 + math.sin(t * 2.5 + yy * 0.25 + k) * 2.5, floor - 26 - yy) for yy in range(0, 22, 2)]
            d.line(pts, fill=(205, 205, 222), width=1)
        step, lt, after = P["step"], P["lt"], P["after"]
        grow = 1.0 if "baum" in after else min(1.0, max(0.0, lt - 2.2) / 4.0) if step == "baum" else 0.0
        if grow > 0:
            self._blob(img, PARTY_PUDDLE_X, floor + 6, 10 + 22 * grow, 3 + 4 * grow, (226, 200, 70), gloss=0.6)
        n = len(PARTY_SIGN) if "signatur" in after else \
            int(min(len(PARTY_SIGN), max(0.0, lt - 1.0) / 6.0 * (len(PARTY_SIGN) + 0.4))) if step == "signatur" else 0
        if n:
            font = self.__dict__.setdefault("_party_sign_font", load_font(13, bold=True))
            d.text((PARTY_SIGN_X, floor + 3), PARTY_SIGN[:n], font=font, fill=(222, 196, 64))
        if "gelb" in after or (step == "gelb" and lt >= 5.6):
            d.ellipse([124, floor + 6, 130, floor + 9], fill=(222, 196, 64))
        if "bescherung" in after or step == "bescherung":           # Sack
            sx = PARTY_SACK_X
            self._blob(img, sx, floor + 1, 40, 8, (150, 165, 190), gloss=0)
            self._blob(img, sx, floor - 14, 34, 30, (150, 100, 56), gloss=0.2)
            self._blob(img, sx, floor - 30, 16, 8, (120, 80, 44), gloss=0.2)
            d.line([(sx - 6, floor - 27), (sx + 6, floor - 27)], fill=(220, 40, 50), width=2)
            if "bescherung" in after or lt >= 1.6:
                self._blob(img, sx + 2, floor - 30, 12, 5, (130, 175, 70), gloss=0.5)

    def _xmas_party_over(self, img, d, P, acts, floor, t):
        """Vor den Figuren: Becher, Mütze in ihrer Hand, Strahl, Schwall, gelbe Flocke, Kater, Zzz, Sprechblasen."""
        heads = self.__dict__.get("_xmas_heads", {})
        hands = self.__dict__.get("_xmas_hands", {})
        visible = {w: -XMAS_OFF_MARGIN < acts[w]["x"] < WIDTH + XMAS_OFF_MARGIN and acts[w]["state"] != "p_behind"
                   for w in acts}
        if P["mugs"]:
            for who, i in (("santa", 0), ("mrs", 1)):
                if visible[who] and who in hands and acts[who]["state"] in ("dance", "walk"):
                    hx, hy = hands[who][i]
                    d.rectangle([hx + 3, hy - 5, hx + 7, hy - 1], outline=(240, 240, 240))
                    self._blob(img, hx, hy - 3, 9, 11, (178, 30, 42), gloss=0.9)
        if not P["hat"] and "mrs" in hands:
            hx, hy = hands["mrs"][1]
            self._xmas_party_hat(d, img, hx, hy - 6, t)
        stream = P["stream"]
        if stream and stream[0] == "tree":
            x0, y0 = XMAS_TREE_X + 28, floor - 14
            self._xmas_party_arc(d, (x0, y0), (PARTY_PUDDLE_X - 4, floor + 5), 10, t)
        if stream and stream[0] == "sign" and visible["santa"] and "santa" in heads:
            n = min(len(PARTY_SIGN) - 0.6, stream[1] / 6.0 * (len(PARTY_SIGN) + 0.4))
            tip = (PARTY_SIGN_X + 6 + n * 8.5, floor + 9 + math.sin(t * 9) * 2)
            hx = heads["santa"][0]
            self._xmas_party_arc(d, (hx - 6, floor - 34), tip, 14, t)
        if P["puke"] is not None and "santa" in heads:
            hx, hy = heads["santa"]
            k = P["puke"]
            mouth, sack = (hx + 4, hy + 8), (PARTY_SACK_X, floor - 30)
            for i in range(10):
                f = i / 9 * min(1.0, k * 2)
                x = mouth[0] + (sack[0] - mouth[0]) * f
                y = mouth[1] + (sack[1] - mouth[1]) * f - math.sin(f * math.pi) * 8
                r = 4 + 2 * math.sin(i * 1.7 + t * 12)
                self._blob(img, x, y, r * 2, r * 1.6, (128, 176, 66), gloss=0.6)
        fl = P["flake"]
        if fl is not None and fl < 5.6:                                     # erreicht den Mund, als sie weggezogen wird
            mouth = floor - 78
            y = fl / 4.6 * mouth if fl < 4.6 else mouth + (fl - 4.6) * (floor + 6 - mouth)
            x = 130 + math.sin(fl * 2) * 3
            d.ellipse([x - 2.4, y - 2.4, x + 2.4, y + 2.4], fill=(240, 214, 70))
        if P["cat"]:
            self._xmas_party_cat(img, d, XMAS_BENCH_X + 2, floor - 20, t, P["cat"])
        if P["zzz"]:
            font = self.__dict__.setdefault("_party_z_font", load_font(10, bold=True))
            for who in ("santa", "mrs"):
                if who in heads:
                    hx, hy = heads[who]
                    for i in range(3):
                        k = (t * 0.45 + i / 3 + (0.5 if who == "mrs" else 0)) % 1.0
                        v = int(230 * (1 - k))
                        d.text((hx + 8 + k * 14 + i * 3, hy - 14 - k * 30), "z", font=font, fill=(v, v, min(255, v + 25)))
        for who, text in P["say"]:
            if who == "mid":
                if not (visible["santa"] and visible["mrs"]):
                    continue
                x = (acts["santa"]["x"] + acts["mrs"]["x"]) / 2
                y = floor - 140
            elif who == "tree":
                x, y = XMAS_TREE_X + 6, floor - 64
            else:
                if not visible[who] or who not in heads:
                    continue
                x, y = heads[who][0], heads[who][1] - 34
            self._xmas_party_say(d, x, y, text)

    def _xmas_party_arc(self, d, p0, p1, height, t):
        """Gelber Bogen (leicht flatternd) von p0 nach p1."""
        pts = []
        for i in range(13):
            f = i / 12
            x = p0[0] + (p1[0] - p0[0]) * f
            y = p0[1] + (p1[1] - p0[1]) * f - math.sin(f * math.pi) * (height + math.sin(t * 11) * 1.5)
            pts.append((x, y))
        d.line(pts, fill=(236, 206, 60), width=2)

    def _xmas_party_hat(self, d, img, x, y, t):
        """Zipfelmütze in der Hand der Weihnachtsfrau, der Bommel wippt."""
        ang = math.radians(70 + math.sin(t * 5) * 25)
        tip = (x + math.cos(ang) * 22, y + math.sin(ang) * 22)
        d.polygon([(x - 10, y), (x + 10, y), tip], fill=XMAS_RED)
        self._blob(img, x, y, 24, 7, XMAS_FUR, gloss=0.1)
        self._blob(img, tip[0], tip[1], 8, 8, XMAS_FUR, gloss=0.2)

    def _xmas_party_cat(self, img, d, x, seat, t, k):
        """Grauer Kater auf der Bank, Augen zu, der Schwanz wedelt."""
        y = seat - 8 + (1 - k) * 6
        grey = (120, 122, 132)
        tail = [(x + 8 + i * 2.2, y + 4 - i * 2 + math.sin(t * 2.5 + i * 0.6) * i * 0.6) for i in range(8)]
        d.line(tail, fill=grey, width=3)
        self._blob(img, x, y, 18, 15, grey, gloss=0.3)
        hx, hy = x - 3, y - 10
        self._blob(img, hx, hy, 13, 11, grey, gloss=0.3)
        for side in (-1, 1):
            d.polygon([(hx + side * 6, hy - 2), (hx + side * 2, hy - 4), (hx + side * 6, hy - 9)], fill=grey)
            d.line([(hx + side * 3 - 1, hy), (hx + side * 3 + 1, hy)], fill=(30, 30, 36))
        d.point((hx, hy + 2), fill=(230, 140, 150))

    def _xmas_party_say(self, d, x, y, text):
        """Sprechblase mit Spitze nach unten, im Bild gehalten."""
        font = self.__dict__.setdefault("_party_say_font", load_font(11, bold=True))
        w = d.textlength(text, font=font) + 10
        bx = max(2, min(WIDTH - w - 2, x - w / 2))
        by = max(16, y - 18)
        d.rounded_rectangle([bx, by, bx + w, by + 17], radius=7, fill=(240, 240, 248))
        tx = max(bx + 6, min(bx + w - 6, x))
        d.polygon([(tx - 4, by + 16), (tx + 4, by + 16), (tx, by + 23)], fill=(240, 240, 248))
        d.text((bx + 5, by + 2), text, font=font, fill=(40, 40, 60))
