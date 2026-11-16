"""Weihnachten: weitere Gags (Mixin XmasFun). Ohne „Feierabend“ laufen die jugendfreien Gags FUN_GAGS von allein
(Option gags, Standard an): Schornstein, Plätzchen, Geschenketurm, Wunschzettel, Schlitten einparken, Lebkuchenmann,
Katze im Baum, Stromausfall, Glatteis, Wichtel-Chor. Mit Feierabend kommen sie zusätzlich in den Topf, dazu
FEIER_EXTRA: Glühwein-Nachschub, Karaoke, Wichtel-Bar, vergessene Geschenke.
Die Gags benutzen den Plan P des Feierabends (Ziele, Zustände p_*, Sprechblasen); eigene Requisiten zeichnen
_xmas_fun_ground (hinter den Figuren), _xmas_fun_over (davor) und _xmas_fun_after (nach dem Abdunkeln)."""
import math
import random

FUN_GAGS = {"schornstein": 12.0, "plaetzchen": 11.0, "geschenketurm": 11.0, "wunschzettel": 10.0, "schlitten": 11.0,
            "lebkuchen": 10.0, "katze": 9.0, "stromausfall": 10.0, "glatteis": 8.0, "wichtelchor": 9.0}
FEIER_EXTRA = {"nachschub": {"dur": 13, "min": 0.4}, "karaoke": {"dur": 12, "min": 0.35},
               "wichtelbar": {"dur": 12, "min": 0.3}, "panik": {"dur": 10, "min": 0.2}}
FUN_FIRST = 18.0                        # erster Gag nach so vielen Sekunden Musik
FUN_PAUSE = (16.0, 26.0)                # Pause zwischen zwei Gags
FUN_COTTAGE_X = 250                     # Hütte mit Schornstein rechts
FUN_TOWER_X = 98                        # Geschenketurm
PARTY_GAGS.update({n: {"dur": d, "min": 0.0} for n, d in FUN_GAGS.items()})
PARTY_GAGS.update(FEIER_EXTRA)


class XmasFun:
    # -- Ablauf ohne Feierabend --------------------------------------------------- #
    def _xmas_fun(self, st, s, t, dt, o, moving, talk):
        """Jugendfreie Gags ohne Feierabend: Plan P während eines Gags, sonst None (normales Tanzen)."""
        fs = st.get("fun")
        if fs is None:
            fs = st["fun"] = {"p": 0.0, "next": FUN_FIRST, "cur": None, "done": set(), "rng": random.Random(7)}
        self.vis_green = False
        if talk:                                                        # Wortbeitrag: Gag abbrechen, Bank wie immer
            if fs["cur"]:
                fs["cur"] = None
                fs["next"] = fs["p"] + 6.0
            return None
        if moving:
            fs["p"] += dt
        cur = fs["cur"]
        if cur and fs["p"] - cur["t0"] >= cur["dur"]:
            fs["cur"] = cur = None
            fs["next"] = fs["p"] + fs["rng"].uniform(*FUN_PAUSE)
        if cur is None and fs["p"] >= fs["next"]:
            names = [n for n in FUN_GAGS if n not in fs["done"]]
            if not names:
                fs["done"].clear()
                names = list(FUN_GAGS)
            self._xmas_fun_start(fs, fs["rng"].choice(names))
            cur = fs["cur"]
        if cur is None:
            return None
        lt = fs["p"] - cur["t0"]
        P = self._xmas_fun_plan(cur["name"], lt, cur["dur"], s, t)
        getattr(self, "_party_" + cur["name"])(P, lt, cur)
        return P

    @staticmethod
    def _xmas_fun_start(fs, name):
        """Gag ohne Feierabend beginnen (auch für Tests und Referenzbilder)."""
        fs["done"].add(name)
        fs["cur"] = {"name": name, "t0": fs["p"], "dur": FUN_GAGS[name], "var": None, "rng": fs["rng"], "lines": {}}

    @staticmethod
    def _xmas_fun_plan(name, lt, dur, s, t):
        return {"step": name, "lt": lt, "dur": dur, "goals": dict(PARTY_PAIR), "states": {}, "back": {}, "say": [],
                "hat": True, "green": 0.0, "mugs": False, "stream": None, "puke": None, "flake": None, "cat": None,
                "zzz": False, "flicker": False, "props": set(), "snowman": None, "mood": "normal", "pegel": 0.0,
                "beat_age": t - s.get("beat_t", t), "beats": s.get("beats", 0), "star": "tree", "hide": set(),
                "weather": None, "warm": False, "elf_n": 0, "pot": False, "meter": False, "mugs_today": 0,
                "lvl": 0.0, "family": True, "carrot": False, "bass": s.get("bass", 0.0)}

    @staticmethod
    def _fsay(P, x, y, text, late=False):
        """Sprechblase an fester Stelle (late: erst nach dem Abdunkeln zeichnen)."""
        P.setdefault("late_say" if late else "fsay", []).append((x, y, text))

    # -- Gags ohne Alkohol ------------------------------------------------------------ #
    def _party_schornstein(self, P, lt, g):
        """Er steigt in den Schornstein der Hütte und bleibt stecken; sie zieht ihn heraus – Plopp, Ruß."""
        P["cottage"] = True
        P["goals"] = {"santa": FUN_COTTAGE_X + 18 if lt < 8 else 200, "mrs": 226 if lt < 4.6 else 244}
        if 1.6 <= lt < 8.0:
            P["hide"] = {"santa"}
            P["chimney_legs"] = lt - 1.6
        if 8.0 <= lt < 9.4:
            P["soot"] = (lt - 8.0) / 1.4
        if lt >= 8.0:
            P["sooty"] = True
        P["states"] = {"mrs": "p_pull" if 5.0 <= lt < 8.0 else "p_laugh" if 8.6 <= lt < 11 else None}
        cx, top = FUN_COTTAGE_X + 40, XMAS_FLOOR - 104
        if 2.4 <= lt < 5.0:
            self._fsay(P, cx, top - 26, "Hilfe! Zu viele Plätzchen!")
        if 5.2 <= lt < 7.6:
            P["say"].append(("mrs", "Halt dich fest!"))
        if 8.6 <= lt < 11.2:
            P["say"].append(("santa", "Ho … ho … hust!"))

    def _party_plaetzchen(self, P, lt, g):
        """Sie bringt ein Blech Plätzchen, er nascht; dann qualmt die zweite Ladung."""
        P["goals"] = {"santa": 176 if 1.8 <= lt < 6 else 160, "mrs": 222}
        P["tray"] = (max(0, 6 - int(max(0.0, lt - 2.0) / 0.6)) if lt < 6.5 else 6, lt >= 6.5)
        P["states"] = {"mrs": "p_offer" if lt < 6.5 else "p_worry",
                       "santa": "p_grab" if 2.0 <= lt < 4.8 else "p_innocent" if lt >= 8.4 else None}
        if 2.4 <= lt < 4.6:
            P["say"].append(("santa", "Mmmh!"))
        elif 4.8 <= lt < 6.4:
            P["say"].append(("mrs", "Finger weg!"))
        elif 6.6 <= lt < 8.4:
            P["say"].append(("mrs", "Die zweite Ladung …"))
        elif 8.6 <= lt < 10.6:
            P["say"].append(("santa", "Ich war's nicht!"))

    def _party_geschenketurm(self, P, lt, g):
        """Er stapelt Geschenke im Takt, der Turm wackelt immer mehr und kippt."""
        g.setdefault("b0", P["beats"])
        P["goals"] = {"santa": FUN_TOWER_X + 50, "mrs": 222}
        n = max(1, min(7, P["beats"] - g["b0"] + 1)) if lt < 7.5 else 7
        g["n"] = max(g.get("n", 1), n)
        P["tower"] = (g["n"], lt)
        P["states"] = {"santa": "p_present" if lt < 7.5 else "p_worry", "mrs": "p_laugh" if lt >= 8 else "p_clap"}
        if 7.6 <= lt < 9.6:
            P["say"].append(("santa", "Hoppla!"))
        elif 9.0 <= lt < 11:
            P["say"].append(("mrs", "Statik, Schatz!"))

    def _party_wunschzettel(self, P, lt, g):
        """Er rollt einen meterlangen Wunschzettel aus."""
        P["goals"] = {"santa": 186, "mrs": 236}
        P["scroll"] = min(1.0, max(0.0, (lt - 0.6) / 4.0))
        P["states"] = {"santa": "p_write" if lt < 5 else "p_proud", "mrs": "p_worry" if lt >= 4 else None}
        if 0.6 <= lt < 3.0:
            P["say"].append(("santa", "Mein Wunschzettel …"))
        elif 4.0 <= lt < 6.6:
            P["say"].append(("mrs", "Ein Pony?! Schon wieder?"))
        elif 7.0 <= lt < 9.6:
            P["say"].append(("santa", "Das ist nur Seite 1."))

    def _party_schlitten(self, P, lt, g):
        """Der Rentierschlitten landet und parkt rückwärts ein – er winkt ein, bis es kracht."""
        P["goals"] = {"santa": 176, "mrs": 236}
        if lt < 3.0:
            k = lt / 3.0
            P["sleigh_fly"] = (-80 + 230 * k, 90 * (1 - k) ** 2)
        elif lt < 6.6:
            k = (lt - 3.0) / 3.6
            P["sleigh_fly"] = (150 - 60 * k + math.sin(k * 9) * 6, 0.0)
        else:
            P["sleigh_fly"] = (90.0, 0.0)
        P["states"] = {"santa": "p_point" if lt < 6.6 else "p_worry",
                       "mrs": "p_covereyes" if 6.4 <= lt < 9 else None}
        if lt >= 6.6:
            P["star_wobble"] = math.sin((lt - 6.6) * 14) * 16 * math.exp(-(lt - 6.6) * 1.2)
        if 3.4 <= lt < 6.4:
            P["say"].append(("santa", "Weiter … weiter … weiter …"))
            if int(lt * 2) % 2:
                self._fsay(P, 120, XMAS_FLOOR - 40, "PIEP")
        elif 6.6 <= lt < 7.8:
            self._fsay(P, 70, XMAS_FLOOR - 60, "RUMMS!")
        elif 8.0 <= lt < 10.4:
            P["say"].append(("santa", "Passt doch!"))

    def _party_lebkuchen(self, P, lt, g):
        """Ein Lebkuchenmann haut ab, beide jagen ihn aus dem Bild – er kommt satt zurück."""
        if lt < 5.0:
            P["gingerbread"] = (WIDTH + 20 - (WIDTH + 50) * lt / 5.0, lt)
        if 2.0 <= lt < 6.6:
            P["goals"] = {"santa": -90, "mrs": -60}
        if 0.6 <= lt < 2.8:
            self._fsay(P, max(30, WIDTH + 20 - (WIDTH + 50) * lt / 5.0), XMAS_FLOOR - 44, "Fang mich doch!")
        if 2.6 <= lt < 4.4:
            P["say"].append(("santa", "Komm zurück, Krümel!"))
        if 8.4 <= lt < 10:
            P["say"].append(("santa", "Lecker."))
            P["states"] = {"mrs": "p_tsk"}

    def _party_katze(self, P, lt, g):
        """Die Katze klettert in den Baum, Kugeln fallen im Takt; am Ende springt sie ihm auf die Mütze."""
        g.setdefault("b0", P["beats"])
        P["goals"] = {"santa": 104 if lt >= 5.6 else 150, "mrs": 196}
        P["treecat"] = (lt, max(0, min(6, P["beats"] - g["b0"] - 4)) if lt >= 3 else 0)
        P["states"] = {"mrs": "p_worry" if lt >= 2.6 else None, "santa": "p_reach" if 5.8 <= lt < 7.4 else None}
        if 3.0 <= lt < 5.6:
            P["say"].append(("mrs", "Mieze, komm runter!"))
        elif 5.8 <= lt < 7.4:
            P["say"].append(("santa", "Ich hol sie!"))
        elif 7.6 <= lt < 9:
            P["say"].append(("santa", "Miau?"))

    def _party_stromausfall(self, P, lt, g):
        """Beim Nachbarn blinkt die Lichterkette immer greller – dann ist der Strom weg, nur der Stern leuchtet."""
        P["house"] = True
        P["houselights"] = min(1.0, lt / 5.5) if lt < 5.5 else 0.0 if lt < 8.6 else 1.0
        if 5.5 <= lt < 8.6:
            P["blackout"] = min(1.0, (lt - 5.5) / 0.15)
            P["dark"] = True
            if 6.0 <= lt < 8.4:
                self._fsay(P, 285, 92, "Ups! Sicherung!", late=True)
        P["states"] = {"santa": "p_worry" if 5.5 <= lt < 8.6 else None, "mrs": "p_clap" if lt >= 8.8 else None}
        if 2.0 <= lt < 5.0:
            P["say"].append(("mrs", "Ganz schön hell da drüben."))
        if 8.8 <= lt < 10:
            P["say"].append(("santa", "Geht wieder!"))

    def _party_glatteis(self, P, lt, g):
        """Glatteis: beide rutschen in Eiskunstlauf-Figuren aneinander vorbei."""
        P["ice"] = True
        if lt < 2.6:
            P["goals"] = {"santa": 236, "mrs": 150}
        elif lt < 5.2:
            P["goals"] = {"santa": 150, "mrs": 236}
        P["states"] = {"santa": "p_slip" if lt < 5.2 else "p_proud", "mrs": "p_pose" if lt >= 5.4 else None}
        if 0.6 <= lt < 2.6:
            P["say"].append(("mrs", "Doppelter Rittberger!"))
        elif 2.8 <= lt < 4.8:
            P["say"].append(("santa", "Huiiii!"))
        elif 5.6 <= lt < 7.8:
            P["say"].append(("mrs", "Sechs Punkte!"))

    def _party_wichtelchor(self, P, lt, g):
        """Drei Wichtel singen – ihre Münder gehen mit der Musik auf und zu."""
        P["choir"] = lt
        P["states"] = {"santa": "p_clap" if lt >= 6 else None, "mrs": "p_clap" if lt >= 6 else None}
        if 2.0 <= lt < 5.6:
            self._fsay(P, 114, XMAS_FLOOR - 64, "♪ O Tannenbaum ♪")
        if 6.2 <= lt < 8.6:
            P["say"].append(("mrs", "Zugabe!"))

    # -- Feierabend: zusätzliche Gags -------------------------------------------------- #
    def _party_nachschub(self, P, lt, g):
        """Der Topf ist leer: er holt mit dem Schlitten Nachschub und kommt schief zurück."""
        P["goals"] = {"santa": 120 if lt < 2.4 else 150, "mrs": 226}
        if lt < 2.4:
            P["pot_empty"] = True
        if 2.4 <= lt < 9.0:
            P["hide"] = {"santa"}
            x = 120 + 230 * (lt - 2.4) / 2.0 if lt < 4.4 else -80 + 200 * (lt - 6.4) / 2.6 if lt >= 6.4 else None
            if x is not None:
                P["sleigh_fly"] = (x, 0.0)
                P["barrel"] = lt >= 6.4
        elif lt < 2.4:
            P["sleigh_fly"] = (120.0, 0.0)
        P["states"] = {"santa": "p_stagger" if lt >= 9 else None, "mrs": "p_bye" if 2.6 <= lt < 4.4 else None}
        if 0.4 <= lt < 2.4:
            P["say"].append(("santa", "Leer! Ich hol Nachschub."))
        if 2.8 <= lt < 5.2:
            P["say"].append(("mrs", "Und Lebkuchen mitbringen!"))
        if 9.4 <= lt < 12:
            P["say"].append(("santa", "Nachschub! Hicks!"))

    def _party_karaoke(self, P, lt, g):
        """Karaoke: er singt schief ins Mikrofon, sie hält sich die Ohren zu, das Rentier auch."""
        P["goals"] = {"santa": 150, "mrs": 226}
        P["karaoke"] = lt
        P["states"] = {"santa": "p_sing", "mrs": "p_ears" if lt >= 2 else None}
        if lt >= 3.0:
            P["deer"] = (262, -1, "stand", lt)
        if 4.4 <= lt < 7.0:
            P["say"].append(("mrs", "Du triffst keinen Ton!"))
        elif 7.4 <= lt < 10:
            P["say"].append(("santa", "Ich bin Künstler!"))

    def _party_wichtelbar(self, P, lt, g):
        """Die Wichtel zimmern im Takt eine Bar; er bestellt – ohne Ausweis gibt's nichts."""
        g.setdefault("b0", P["beats"])
        P["bar"] = max(1, min(4, P["beats"] - g["b0"] + 1)) if lt < 5 else 4
        P["elf"] = (118, 1, "look" if 8.4 <= lt < 11 else "write", lt)
        P["goals"] = {"santa": 160, "mrs": 226}
        P["states"] = {"santa": "p_offer" if 5.6 <= lt < 8.2 else "p_nope" if lt >= 10.6 else None}
        if 5.8 <= lt < 8.2:
            P["say"].append(("santa", "Einen Doppelten!"))
        elif 8.4 <= lt < 11:
            P["say"].append(("elf", "Nur mit Nordpol-Ausweis!"))

    def _party_panik(self, P, lt, g):
        """Panik: Die Geschenke! Er rennt hin und her – sie weiß, wo sie liegen."""
        if lt < 7.6:
            P["goals"] = {"santa": (40, 290)[int(lt / 1.6) % 2], "mrs": 226}
        P["states"] = {"mrs": "p_laugh" if lt >= 3.6 else None}
        if 0.4 <= lt < 3.0:
            P["say"].append(("santa", "DIE GESCHENKE!"))
        if 4.0 <= lt < 7.4:
            P["say"].append(("mrs", "Liegen seit Oktober im Keller."))
        if 8.0 <= lt < 10:
            P["say"].append(("santa", "Puh."))

    # -- Zeichnen ----------------------------------------------------------------------- #
    def _xmas_fun_ground(self, img, d, P, floor, t):
        """Hinter den Figuren: Hütte mit Schornstein, Geschenketurm, Eisfläche, Schlitten, Wichtel-Chor, Bar,
        Karaoke-Bildschirm, Lichter am Nachbarhaus."""
        if P.get("cottage"):
            x0 = FUN_COTTAGE_X
            d.rectangle([x0, floor - 46, WIDTH, floor + 2], fill=(120, 78, 46))
            for y in range(int(floor - 42), int(floor), 7):
                d.line([(x0, y), (WIDTH, y)], fill=(96, 62, 36))
            d.rectangle([x0 + 14, floor - 34, x0 + 30, floor - 16], fill=(250, 210, 120))
            d.polygon([(x0 - 10, floor - 44), (WIDTH + 4, floor - 44), (WIDTH + 4, floor - 92)], fill=(150, 40, 40))
            d.polygon([(x0 - 10, floor - 44), (WIDTH + 4, floor - 92), (WIDTH + 4, floor - 86), (x0 - 6, floor - 48)],
                      fill=(246, 246, 252))                                       # Schnee auf dem Dach
            cx = x0 + 40
            d.rectangle([cx - 9, floor - 104, cx + 9, floor - 60], fill=(150, 64, 50))
            for y in range(int(floor - 100), int(floor - 60), 6):
                d.line([(cx - 9, y), (cx + 9, y)], fill=(110, 46, 36))
            d.rectangle([cx - 11, floor - 108, cx + 11, floor - 102], fill=(120, 52, 42))
            legs = P.get("chimney_legs")
            if legs is not None:
                k = min(1.0, legs / 0.4)
                for side in (-1, 1):
                    kick = math.sin(t * 14 + side) * 0.45 * k
                    a = side * 0.25 + kick
                    p0 = (cx + side * 3, floor - 106)
                    p1 = (p0[0] + math.sin(a) * 16 * k, p0[1] - math.cos(a) * 16 * k)
                    self._limb(img, p0, p1, 7, XMAS_RED)
                    self._blob(img, p1[0], p1[1] - 2, 9, 7, (30, 26, 26), gloss=0.8)
            if P.get("soot") is not None:
                k = P["soot"]
                for j in range(6):
                    a = j * 1.05
                    r = 6 + 26 * k
                    self._blob(img, cx + math.cos(a) * r, floor - 112 - k * 20 + math.sin(a) * r * 0.5, 14 + 10 * k,
                               12 + 8 * k, (70, 66, 70), alpha=0.7 * (1 - k), flat=True)
        if P.get("ice"):
            self._blob(img, 194, floor + 4, 150, 12, (200, 230, 250), gloss=0.9, alpha=0.8)
        if P.get("tower"):
            n, lt = P["tower"]
            cols = [(220, 40, 50), (60, 140, 230), (250, 200, 60), (70, 180, 90), (200, 80, 200), (250, 140, 40),
                    (90, 200, 220)]
            if lt < 7.5:
                wob = math.sin(t * 5) * n * 1.2 * (0.4 + P.get("bass", 0.5))
                y = floor
                for i in range(n):
                    w, h = 26 - i * 2, 14
                    x = FUN_TOWER_X + wob * (i / 6.0) ** 1.6 * 3
                    d.rectangle([x - w / 2, y - h, x + w / 2, y], fill=cols[i])
                    d.line([(x, y - h), (x, y)], fill=(250, 240, 200), width=2)
                    y -= h
            else:                                                                # gekippt: Pakete liegen verstreut
                k = min(1.0, (lt - 7.5) / 0.7)
                for i in range(n):
                    tx, ty = FUN_TOWER_X + 20 + i * 15, floor
                    sx, sy = FUN_TOWER_X, floor - 14 * i - 7
                    x = sx + (tx - sx) * k
                    y = sy + (ty - 7 - sy) * k - math.sin(k * math.pi) * 18
                    d.rectangle([x - 9, y - 7, x + 9, y + 7], fill=cols[i])
        if P.get("sleigh_fly"):
            x, h = P["sleigh_fly"]
            self._xmas_party_sleigh(img, d, x, floor - h, t, False)
            if P.get("barrel"):
                self._blob(img, x - 2, floor - h - 34, 22, 20, (130, 80, 44), gloss=0.4)
                d.line([(x - 12, floor - h - 38), (x + 8, floor - h - 38)], fill=(80, 60, 50), width=2)
        if P.get("choir") is not None:
            lt = P["choir"]
            for i, ex in enumerate((92, 114, 136)):
                x = min(ex, -20 + (ex + 20) * lt / 1.6)
                self._xmas_party_elf(img, d, (x, 1, "sing", lt), floor, t)
                if lt >= 1.6:
                    m = 1 + 3 * abs(math.sin(t * 7 + i * 1.3))
                    d.ellipse([x + 1, floor - 29, x + 4, floor - 29 + m], fill=(90, 20, 30))
                    if int(t * 3 + i) % 3 == 0:
                        d.text((x + 4, floor - 52 - (t * 20 + i * 7) % 14), "♪", font=self.f_tiny,
                               fill=(255, 240, 160))
        if P.get("bar"):
            n = P["bar"]
            for i in range(n):
                d.rectangle([96, floor - 6 - i * 7, 142, floor - 1 - i * 7], fill=(140, 92, 52))
                d.line([(96, floor - 6 - i * 7), (142, floor - 6 - i * 7)], fill=(170, 116, 70))
            if n >= 4:
                d.rectangle([92, floor - 34, 146, floor - 30], fill=(110, 70, 40))
                for j, c in enumerate(((240, 220, 120), (150, 40, 60), (120, 200, 230))):
                    d.rectangle([100 + j * 14, floor - 42, 106 + j * 14, floor - 34], fill=c)
        if P.get("karaoke") is not None:
            x, y = 104, floor - 70
            d.rectangle([x - 4, y + 36, x + 4, floor], fill=(60, 60, 70))
            d.rectangle([x - 28, y, x + 28, y + 36], fill=(30, 30, 40))
            d.rectangle([x - 25, y + 3, x + 25, y + 33], fill=(30, 50, 120))
            font = self.__dict__.setdefault("_fun_tv_font", load_font(8, bold=True))
            words = ["♪ LA LA", "LA LAAA ♪", "JINGLE …", "♪ HO HO"]
            w = words[int(P["karaoke"] / 1.5) % len(words)]
            d.text((x - 22, y + 8), w, font=font, fill=(255, 240, 120))
            d.text((x - 22, y + 20), "♪♪♪", font=font, fill=(160, 220, 255))

    def _xmas_fun_over(self, img, d, P, acts, floor, t):
        """Vor den Figuren: Plätzchenblech, Wunschzettel, Lebkuchenmann, Katze, Kugeln, Ruß, Mikrofon, feste
        Sprechblasen."""
        heads = self.__dict__.get("_xmas_heads", {})
        hands = self.__dict__.get("_xmas_hands", {})
        if P.get("tray") and "mrs" in hands:
            n, burnt = P["tray"]
            hx, hy = hands["mrs"][1]
            d.rectangle([hx - 26, hy - 4, hx, hy - 1], fill=(170, 170, 180))
            for i in range(n):
                cx = hx - 22 + i * 4
                d.ellipse([cx - 2, hy - 7, cx + 2, hy - 3], fill=(40, 30, 26) if burnt else (220, 170, 90))
            if burnt:
                for j in range(3):
                    k = (t * 0.8 + j / 3) % 1.0
                    self._blob(img, hx - 14 + j * 6, hy - 10 - k * 30, 8 + k * 10, 8 + k * 10, (90, 90, 96),
                               alpha=0.6 * (1 - k), flat=True)
        if P.get("scroll") and "santa" in hands:
            hx, hy = hands["santa"][0]
            k = P["scroll"]
            end = hx - 20 - k * 260
            d.line([(hx, hy), (hx - 8, floor - 2)], fill=(250, 246, 230), width=6)
            d.rectangle([end, floor - 4, hx - 8, floor + 2], fill=(250, 246, 230))
            for x in range(int(hx - 14), int(end), -9):
                d.line([(x, floor - 2), (x - 5, floor - 2)], fill=(150, 60, 60))
            self._blob(img, end, floor - 1, 7, 9, (240, 232, 210), gloss=0.3)
        if P.get("gingerbread"):
            x, lt = P["gingerbread"]
            hop = abs(math.sin(lt * 9)) * 8
            y = floor - 12 - hop
            brown = (178, 110, 50)
            for side in (-1, 1):
                d.line([(x + side * 3, y + 4), (x + side * 6 + math.sin(lt * 18) * 3 * side, y + 12)], fill=brown,
                       width=4)
                d.line([(x + side * 4, y - 4), (x + side * 10, y - 8 + math.sin(lt * 18) * 3)], fill=brown, width=4)
            self._blob(img, x, y, 12, 14, brown, gloss=0.3)
            self._blob(img, x, y - 12, 11, 11, brown, gloss=0.3)
            for j in range(2):
                d.ellipse([x - 1, y - 2 + j * 5, x + 1, y + j * 5], fill=(240, 60, 60))
            d.ellipse([x - 3, y - 14, x - 1, y - 12], fill=(255, 255, 255))
            d.ellipse([x + 1, y - 14, x + 3, y - 12], fill=(255, 255, 255))
            d.arc([x - 3, y - 12, x + 3, y - 8], 20, 160, fill=(255, 255, 255))
        if P.get("treecat"):
            lt, balls = P["treecat"]
            star = self.__dict__.get("_xmas_star_pos", (XMAS_TREE_X, 40))
            if lt < 3.0:
                cx, cy = XMAS_TREE_X + 10, floor - 8 - (floor - star[1] - 40) * lt / 3.0
            elif lt < 7.4 or "santa" not in heads:
                cx, cy = XMAS_TREE_X + 6 + math.sin(t * 2) * 3, star[1] + 32
            else:                                                                # auf seiner Mütze
                k = min(1.0, (lt - 7.4) / 0.4)
                hx, hy = heads["santa"]
                cx = XMAS_TREE_X + 6 + (hx - XMAS_TREE_X - 6) * k
                cy = star[1] + 32 + (hy - 22 - star[1] - 32) * k - math.sin(k * math.pi) * 20
            self._fun_cat(img, d, cx, cy, t)
            rng = random.Random(3)
            for i in range(balls):
                bx = XMAS_TREE_X - 20 + rng.uniform(0, 40)
                col = XMAS_LIGHT_COLORS[i % len(XMAS_LIGHT_COLORS)]
                self._blob(img, bx, floor + 3, 7, 7, col, gloss=0.9)
        if P.get("sooty") and "santa" in heads:
            hx, hy = heads["santa"]
            for j, (ox, oy) in enumerate(((-5, -2), (4, 1), (-1, 5), (6, -5))):
                d.ellipse([hx + ox - 2, hy + oy - 2, hx + ox + 2, hy + oy + 2], fill=(50, 46, 50))
        if P.get("karaoke") is not None and "santa" in hands:
            hx, hy = hands["santa"][0]
            d.line([(hx, hy), (hx + 4, hy - 8)], fill=(40, 40, 44), width=3)
            self._blob(img, hx + 5, hy - 10, 6, 6, (120, 120, 130), gloss=0.8)
            if "santa" in heads:
                sx, sy = heads["santa"]
                for j in range(3):
                    k = (t * 0.9 + j / 3) % 1.0
                    d.text((sx + 10 + k * 20 + math.sin(t * 9 + j) * 4, sy - 10 - k * 26), "♪", font=self.f_tiny,
                           fill=(255, 90, 90))
        if P.get("houselights") is not None:
            k = P["houselights"]
            for i in range(15):                                                  # entlang der Dachkante
                q = i / 14
                x = 256 + 58 * q
                y = 87 - 21 * (1 - abs(q - 0.5) * 2)
                on = (i + P["beats"]) % 2 == 0
                if k > 0 and on:
                    col = XMAS_LIGHT_COLORS[i % len(XMAS_LIGHT_COLORS)]
                    self._blob(img, x, y, 6 + 12 * k, 6 + 12 * k, col, alpha=round(0.3 + 0.5 * k, 1), flat=True)
                    d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(255, 255, 230))
        for x, y, text in P.get("fsay", []):
            self._xmas_party_say(d, x, y, text)

    def _xmas_fun_after(self, img, P):
        """Stromausfall: alles dunkel, nur der Stern leuchtet weiter; Sprechblasen danach."""
        if P.get("blackout"):
            img = Image.blend(img, Image.new("RGB", img.size, (4, 6, 18)), 0.78 * P["blackout"])
            star = self.__dict__.get("_xmas_star_pos")
            if star:
                self._blob(img, star[0], star[1], 30, 30, (255, 230, 120), alpha=0.6, flat=True)
                d = ImageDraw.Draw(img)
                pts = [(star[0] + math.cos(-math.pi / 2 + k * math.pi / 5) * (9 if k % 2 == 0 else 4),
                        star[1] + math.sin(-math.pi / 2 + k * math.pi / 5) * (9 if k % 2 == 0 else 4))
                       for k in range(10)]
                d.polygon(pts, fill=(255, 220, 70))
        if P.get("late_say"):
            d = ImageDraw.Draw(img)
            for x, y, text in P["late_say"]:
                self._xmas_party_say(d, x, y, text)
        return img

    def _fun_cat(self, img, d, x, y, t):
        grey = (120, 116, 122)
        self._blob(img, x, y, 16, 10, grey, gloss=0.3)
        self._blob(img, x - 8, y - 5, 10, 9, grey, gloss=0.3)
        for side in (-1, 1):
            d.polygon([(x - 8 + side * 4, y - 9), (x - 8 + side * 2, y - 13), (x - 8 + side * 1, y - 8)], fill=grey)
        d.line([(x + 7, y), (x + 13, y - 6 + math.sin(t * 5) * 3)], fill=grey, width=2)
        d.point((x - 10, y - 6), fill=(120, 230, 90))
        d.point((x - 6, y - 6), fill=(120, 230, 90))
