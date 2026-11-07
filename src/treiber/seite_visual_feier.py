"""Visualisierung „Weihnachten“, Option „Feierabend“: Weihnachtsmann und Weihnachtsfrau trinken Glühwein über
den Durst (derber Humor, Standard aus; visual.xmas.party = off/on/evening).

Ablauf einer Runde (Länge visual.xmas.party_len, gezählt wird nur Zeit mit Musik):
- Auftakt: tanzen und prosten. Jedes Prosten hebt den Pegel (0…1); bei wilder Musik prosten sie öfter, bei ruhiger
  schunkeln sie nur (der Pegel steigt dann kaum).
- Mitte: Gags aus PARTY_GAGS in zufälliger Reihenfolge, je Runde höchstens einmal; manche erst ab einem Pegel oder
  nach einem anderen Gag (Ausrede erst nach der Pfütze …). Je höher der Pegel, desto kürzer die Pausen.
  Läuft im Radio ein Weihnachtslied (Titel), grölen beide mit. Dazwischen kleine Zwischengags (stolpern, Becher
  verschütten, Takt verpassen, Schluckauf, nachts gähnen).
- Schluss (Pegel voll oder Runde fast um): grünes Gesicht → Bescherung → Kater auf der Bank → Morgen danach →
  „Nur noch einen …“, dann von vorn (Spuren sind weggeräumt).
Sprechblasen wählen je Gag zufällig aus PARTY_LINES. Silvester (31.12. ab 23 Uhr) gibt es Feuerwerk.
"""

PARTY_PAIR = {"santa": 160, "mrs": 226}
PARTY_POT_X = 300                         # Glühweintopf am rechten Rand
PARTY_SACK_X = 268                        # Geschenkesack (Bescherung)
PARTY_PUDDLE_X = XMAS_TREE_X + 56         # Pfütze rechts neben dem Baum
PARTY_SNOWMAN_X = 118
PARTY_SIGN = "HO HO H"                    # in den Schnee geschrieben (beim letzten O geht es aus)
PARTY_SIGN_X = 150
PARTY_GREEN = (150, 205, 120)
PARTY_BENCH = {"santa": XMAS_BENCH_X + 24, "mrs": XMAS_BENCH_X - 18}    # Kater: er sitzt rechts (kam von rechts)
PARTY_OPEN = 20.0                         # Sekunden Musik nur mit Prosten, bevor Gags kommen
PARTY_KATER_MIN = 20.0
# Gags der Mitte: Dauer (s), Mindestpegel, nötige Spuren (alle), Spuren (eine davon), Varianten
PARTY_GAGS = {
    "pipi": {"dur": 10, "min": 0.3},
    "baum": {"dur": 15, "min": 0.35},                                   # er, dann sie hinter den Baum
    "rentier": {"dur": 6, "min": 0.35, "needs": ("puddle",)},           # „War das Rentier!“
    "signatur": {"dur": 9, "min": 0.4},
    "gelb": {"dur": 7, "min": 0.45},
    "wichtel": {"dur": 11, "min": 0.3, "any": ("puddle", "sign")},
    "ruelps": {"dur": 6, "min": 0.2},
    "pups": {"dur": 7, "min": 0.4},
    "rutsch": {"dur": 8, "min": 0.4, "needs": ("puddle",)},
    "baumcrash": {"dur": 8, "min": 0.6},
    "mistel": {"dur": 9, "min": 0.2},
    "sietanzt": {"dur": 9, "min": 0.5, "vars": ("bank", "singt")},
    "handy": {"dur": 7, "min": 0.3},
    "schneemann": {"dur": 10, "min": 0.3, "vars": ("nase", "gluehwein")},
    "rentierbesuch": {"dur": 13, "min": 0.3},
    "groelen": {"dur": 10, "min": 0.0, "song": True},                 # nur bei Weihnachtsliedern im Radio
    "schneeball": {"dur": 8, "min": 0.2},
    "lichterkette": {"dur": 7, "min": 0.5},
    "schneeengel": {"dur": 10, "min": 0.55},
    "geschenk": {"dur": 9, "min": 0.25},
    "topf": {"dur": 11, "min": 0.65},
    "polonaise": {"dur": 20, "min": 0.45},
    "taxi": {"dur": 13, "min": 0.7},
    "nachbar": {"dur": 7, "min": 0.3},
    "stiefel": {"dur": 9, "min": 0.0, "needs": ("noboot",)},            # Wichtel bringt den Stiefel zurück
    "muetze": {"dur": 8, "min": 0.0, "storm": True},                   # nur bei Sturm (Wetterseite)
}
PARTY_ELF_MAX = 3                         # so oft kommt der Wichtel je Runde (die Liste wird länger)
PARTY_END = [("gruen", 6), ("bescherung", 8), ("kater", None), ("morgen", 10), ("noch", 7)]
PARTY_END_FIXED = sum(d for _n, d in PARTY_END if d)
PARTY_SONG_WORDS = ("christmas", "xmas", "weihnacht", "jingle", "santa", "snow", "schnee", "noel", "navidad",
                    "sleigh", "winter wonderland", "tannenbaum", "stille nacht", "advent", "mistletoe", "rentier",
                    "reindeer", "nikolaus", "feliz")
PARTY_LINES = {
    "prost": ["Prost!", "Zum Wohl!", "Hoch die Becher!", "Ex!", "Auf uns!"],
    "toll": ["Toller Schritt!", "Den lern ich auch!", "Ui, neu?"],
    "machhin": ["Mach hin!", "Wird's bald?", "Ich muss auch!"],
    "ahh": ["Ahh …", "Herrlich …", "Puuh …"],
    "werwar": ["Wer war das?!", "Was ist DAS?!", "Schatz?!"],
    "ausrede": ["War das Rentier!", "Das war schon so!", "Tauwetter!", "Der Hund vom Nachbarn!"],
    "typisch": ["Typisch.", "Männer …", "Ernsthaft?"],
    "gelb": ["Nicht den gelben!", "Halt! Nicht den!", "Pfui, spuck aus!"],
    "uebel": ["Mir ist nicht gut …", "Uuuh …", "Der Glühwein war schlecht!"],
    "bescherung": ["Na, schöne Bescherung!", "Frohe Weihnachten …", "Der Sack war neu!"],
    "noch": ["Nur noch einen …", "Einer geht noch!", "Für den Heimweg!"],
    "ruelps": ["BUÄÄRP!", "RÖÖÖLPS!", "BRÖÖAP!"],
    "fan": ["Charmant.", "Igitt!", "Gesundheit?"],
    "pups_mrs": ["Puh!", "Wer war DAS?", "Fenster auf!"],
    "pups_santa": ["Ich war's nicht.", "Das Rentier!", "♪ ♫"],
    "uff": ["Uff!", "Autsch!", "Wer hat hier gewischt?"],
    "lachen": ["Hahaha!", "Hihihi!", "Nochmal!"],
    "star": ["Ich bin der Star!", "Steht mir, oder?", "Ta-daa!"],
    "ohoh": ["Oh oh …", "Vorsicht!", "Der Baum!"],
    "nope": ["Vergiss es!", "Nicht mit der Fahne!", "Zähne geputzt?"],
    "mwah": ["Mwah!", "Na du …", "Hallo, Hübscher …"],
    "juhu": ["Juhuu!", "Party!", "Wuhuu!"],
    "ohnein": ["Oh nein …", "Schatz, die Nachbarn!", "Ich seh nichts!"],
    "autsch": ["Autsch!", "Meine Ohren!", "Schief!"],
    "handy": ["Das kommt in die Familiengruppe!", "Lächeln!", "Fürs Familienalbum!"],
    "passt": ["Passt!", "Steht mir!", "Jetzt seh ich gut aus."],
    "vertraegt": ["Der verträgt nix!", "Schwächling!", "Prost, Kumpel!"],
    "meiner": ["Hey, das ist meiner!", "Kauf dir selber einen!", "Unser Glühwein!"],
    "unartig": ["Unartig!", "Notiert.", "Ab auf die Liste!"],
    "psst": ["Psst!", "Ich kann das erklären!", "Der gehört nicht zu mir!"],
    "kopf": ["Nicht so laut …", "Mein Kopf …", "Wer hat das Licht an?"],
    "sing": ["♪ Lalalaaa ♪", "♪ O Tannenbaum ♪", "♪ Hoho-hooo ♪"],
    "sing2": ["♪ Lalalaaa ♪", "♪ O Tannenbaum ♪", "♪ Hoho-hooo ♪"],
    "hoppla": ["Hoppla!", "Huch!", "Ups!"],
    "takt": ["Äh …", "Wo waren wir?", "Moment!"],
    "spill": ["Ups!", "Schade drum!", "Der gute Glühwein!"],
    "gaehn": ["Gähn …", "Hmpf …"],
    "neujahr": ["Frohes Neues!", "Prosit Neujahr!"],
    "unartig2": ["Schon wieder!", "Noch mehr …", "Seite 2 …"],
    "unartig3": ["Seite 3 …", "Das wird teuer!", "Kohle statt Geschenke!"],
    "treffer": ["Hey!", "Aua!", "Foul!"],
    "erwischt": ["Erwischt!", "Treffer!", "Hihi!"],
    "leuchte": ["Ich leuchte!", "Festbeleuchtung!", "Bin ich schön?"],
    "stehtdir": ["Steht dir!", "Mein Weihnachtsbaum!", "Hübsch!"],
    "engel": ["Ich bleib hier!", "Schön weich …", "Ich bin ein Engel!"],
    "hoch": ["Hoch mit dir!", "Aufstehen!", "Komm jetzt!"],
    "socken": ["Socken …", "Schon wieder Socken!", "Die kratzen!"],
    "gestrickt": ["Die hab ich gestrickt!", "Sind doch schön!", "Warme Füße!"],
    "bong": ["BONG!", "Wer hat den Baum hier hingestellt?", "Autsch …"],
    "schatz": ["Schatz?!", "Was machst du da?", "Ich seh's nicht!"],
    "polonaise": ["Polonäääse!", "Alle mitmachen!", "Hände an die Schultern!"],
    "gutenacht": ["Gute Nacht!", "Schlaf gut!", "Bring ihn heim!"],
    "vergessen": ["Hab was vergessen!", "Bin wieder da!", "Ohne mich nicht!"],
    "ruhe": ["Ruhe da unten!", "Es ist mitten in der Nacht!", "Ich ruf die Polizei!"],
    "psst2": ["Psst!", "Pschhh!"],
    "meinstiefel": ["Mein Stiefel!", "Der war neu!", "Gib her!"],
    "stiefel_da": ["Gefunden!", "Hier, bitte.", "Der lag im Schnee."],
    "danke": ["Danke!", "Endlich warme Füße!", "Braver Wichtel!"],
    "muetze": ["Meine Mütze!", "Halt, stehen bleiben!", "Komm zurück!"],
    "schmilzt": ["Mein Schneemann …", "Nein, nicht schmelzen!", "Tauwetter!"],
    "lauter": ["Jaaa!", "Lauter!", "Das ist mein Lied!"],
    "leiser": ["Ooch …", "Spielverderber!", "Lass an!"],
    "meinlied": ["Das ist mein Lied!", "Oh, das kenn ich!", "Dreh auf!"],
    "laber": ["Laber nicht, spiel was!", "Musik!", "Weniger reden!"],
}


def party_active(opts, hour=None):
    """Option „Feierabend“: an, aus oder nur abends (20 bis 4 Uhr)."""
    mode = opts.get("party", "off")
    if mode == "on":
        return True
    if mode == "evening":
        hour = party_clock().tm_hour if hour is None else hour
        return hour >= 20 or hour < 4
    return False


def party_clock():
    """Ortszeit (für Nacht, Silvester; in Tests ersetzbar)."""
    return time.localtime()


def party_song_xmas(text):
    low = (text or "").lower()
    return any(w in low for w in PARTY_SONG_WORDS)


def party_mood(energy, period):
    """Musik: „wild“ (laut und schnell), „ruhig“ (leise) oder „normal“."""
    if energy >= 0.62 and period <= 0.55:
        return "wild"
    if energy < 0.3:
        return "ruhig"
    return "normal"


def party_budget(length):
    """Musikzeit, in der der Pegel bei normalem Prosten von 0 auf 1 steigt."""
    return max(60.0, length - PARTY_END_FIXED - PARTY_KATER_MIN - PARTY_OPEN)


def party_end_due(ps, length):
    """Schluss: Pegel voll (frühestens nach 60 % der Runde) oder die Runde ist fast um."""
    limit = length - PARTY_END_FIXED - PARTY_KATER_MIN
    return (ps["pegel"] >= 1.0 and ps["p"] >= 0.6 * limit) or ps["p"] >= limit


def party_eligible(ps, name, song="", ordered=False):
    """Darf der Gag jetzt kommen? (noch nicht dran gewesen, Pegel, Spuren, Weihnachtslied, Sturm)
    ordered = auf Bestellung (OK-Taste): Pegel und „schon dran gewesen“ zählen nicht."""
    gag = PARTY_GAGS[name]
    if gag.get("song"):
        return party_song_xmas(song) and (ordered or song != ps["sung"])
    if gag.get("storm") and ps.get("weather") != "storm":
        return False
    if not ordered and (name in ps["done"] or ps["pegel"] < gag["min"]):
        return False
    if any(p not in ps["props"] for p in gag.get("needs", ())):
        return False
    return not gag.get("any") or any(p in ps["props"] for p in gag["any"])


def _lerp(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


def _win(lt, a, b):
    return a <= lt < b


class XmasParty:
    vis_green = False                  # Feierabend: grünes Gesicht – Tastatur bei „Rot und Grün“ grün

    # -- Ablauf -------------------------------------------------------------- #
    @staticmethod
    def _party_new(seed, energy=0.5, sung=""):
        return {"p": 0.0, "pegel": 0.0, "phase": "open", "cur": None, "done": set(), "props": set(),
                "next": PARTY_OPEN, "micro": None, "micro_at": PARTY_OPEN, "prost_t": -9.0, "n": 0, "sleep": False,
                "end_i": -1, "seed": seed, "rng": random.Random(seed), "energy": energy, "sung": sung,
                "snowman": None, "weather": None, "warm": False, "sleepy": False, "elf_n": 0}

    def _xmas_party_start(self, ps, name, var=None):
        """Gag bzw. Schritt des Schlusses beginnen (auch für Tests und Referenzbilder)."""
        gag = PARTY_GAGS.get(name, {})
        if var is None and name == "schneemann" and ps.get("warm"):
            var = "schmilzt"                                            # Tauwetter (Wetterseite)
        if var is None and gag.get("vars"):
            var = ps["rng"].choice(gag["vars"])
        dur = gag.get("dur") or dict(PARTY_END).get(name)
        if name == "kater":
            length = ps.get("length", 600)
            dur = min(45.0, max(PARTY_KATER_MIN, length - ps["p"] - PARTY_END_FIXED + 6 + 8))
        ps["cur"] = {"name": name, "t0": ps["p"], "dur": dur, "var": var, "rng": ps["rng"], "lines": {}}
        ps["micro"] = None
        if name == "noch":                                              # neuer Morgen: aufgeräumt
            ps["props"].clear()
            ps["snowman"] = None

    def _xmas_party_finish(self, ps, length):
        cur = ps["cur"]
        name = cur["name"]
        ps["cur"] = None
        gain = {"baum": "puddle", "signatur": "sign", "gelb": "spot", "baumcrash": "star_head",
                "bescherung": "sack", "rutsch": "noboot", "lichterkette": "wrapped", "schneeengel": "angel"}.get(name)
        if gain:
            ps["props"].add(gain)
        if name == "stiefel":
            ps["props"].discard("noboot")
        if name == "schneemann":
            ps["snowman"] = {"nase": "nonose", "gluehwein": "fallen", "schmilzt": "melted"}[cur["var"]]
            if cur["var"] == "nase":
                ps["props"].add("carrot")
        if name == "groelen":
            ps["sung"] = self.__dict__.get("_vis_song") or ""
        elif name == "wichtel":
            ps["elf_n"] = ps.get("elf_n", 0) + 1
            if ps["elf_n"] >= PARTY_ELF_MAX:
                ps["done"].add(name)
        elif name in PARTY_GAGS:
            ps["done"].add(name)
        if ps["phase"] == "end":
            ps["end_i"] += 1
            if ps.get("monday") and name == "morgen":                  # Montag früh: nur Kater
                ps["end_i"] = [n for n, _d in PARTY_END].index("kater")
            if ps["end_i"] < len(PARTY_END):
                self._xmas_party_start(ps, PARTY_END[ps["end_i"]][0])
            else:                                                       # neue Runde
                new = self._party_new(ps["seed"] + 1, ps["energy"], ps["sung"])
                new.update(length=length, weather=ps.get("weather"), warm=ps.get("warm", False),
                           sleepy=ps.get("sleepy", False), monday=ps.get("monday", False), vol=ps.get("vol"),
                           song_prev=ps.get("song_prev"))
                ps.clear()
                ps.update(new)
        else:
            gap = 24 - 18 * ps["pegel"]
            ps["next"] = ps["p"] + gap * (1.6 if ps.get("sleepy") else 1.0)

    def _xmas_party_begin_end(self, ps, at="gruen"):
        ps["phase"] = "end"
        ps["end_i"] = [n for n, _d in PARTY_END].index(at)
        self._xmas_party_start(ps, at)

    def _party_weather(self):
        """Wetter der Wetterseite: (Art, Temperatur, Wind) – Art rain/snow/… oder None (zwischengespeichert)."""
        now = time.monotonic()
        cached = self.__dict__.get("_party_wx")
        if cached and now - cached[0] < 5:
            return cached[1]
        out = (None, None, None)
        try:
            data = self.weather.snapshot()[0] if self.weather else None
            cur = (data or {}).get("current") or {}
            if cur:
                kind = WEATHER_CODES.get(int(cur.get("weather_code") or 0), ("", None))[1]
                out = (kind, cur.get("temperature_2m"), cur.get("wind_speed_10m"))
        except Exception:                                               # Wetter ist nur Beiwerk
            pass
        self._party_wx = (now, out)
        return out

    def _xmas_party(self, st, s, t, dt, o, moving, talk, new_beat, enter):
        """Stand der Feierabend-Runde → Plan P (Ziele, Zustände p_*, Requisiten, Sprechblasen …). None = aus."""
        if not party_active(o):
            st.pop("party", None)
            self.vis_green = False
            return None
        clock = party_clock()
        hour, wday = clock.tm_hour, getattr(clock, "tm_wday", 3)
        length = max(120, int(o["party_len"]) if str(o.get("party_len")).isdigit() else 600)
        if wday in (4, 5):                                              # Freitag/Samstag: länger feiern
            length = int(length * 1.5)
        ps = st.get("party")
        if ps is None:
            ps = st["party"] = self._party_new(1)
        ps["length"] = length
        ps["sleepy"] = hour < 5
        kind, temp, wind = self._party_weather()
        ps["weather"] = "storm" if (wind or 0) >= 50 else "rain" if kind in ("rain", "drizzle", "thunder") else None
        ps["warm"] = temp is not None and temp > 2
        song = self.__dict__.get("_vis_song") or ""
        period = max(0.3, min(1.2, s.get("period") or 0.5))
        ps["energy"] += (s.get("level", 0.5) - ps["energy"]) * min(1.0, dt / 3.0)
        mood = party_mood(ps["energy"], period)
        muted = bool(s.get("muted"))
        monday = wday == 0 and hour < 12
        if monday and not ps.get("monday") and not talk:                 # Montag früh: gleich der Kater
            ps["monday"] = True
            self._xmas_party_begin_end(ps, "kater")
        elif not monday and ps.get("monday"):
            ps["monday"] = False
        vol = s.get("volume")                                           # Lautstärke geändert?
        if vol is not None and ps.get("vol") is not None and abs(vol - ps["vol"]) >= 3:
            ps["volev"] = ("lauter" if vol > ps["vol"] else "leiser", t)
        if vol is not None:
            ps["vol"] = vol
        if song and ps.get("song_prev") not in (None, song):           # neues Lied
            ps["songev"] = (ps["rng"].choice(("santa", "mrs")), t)
        ps["song_prev"] = song
        talk = talk or muted
        if talk:
            ps["talk_for"] = ps.get("talk_for", 0.0) + dt
            sick = (ps["phase"] == "end" and ps["cur"] and ps["cur"]["name"] in ("gruen", "bescherung", "kater")) \
                or ps["pegel"] >= 0.85 or muted
            if sick:
                ps["sleep"] = True
        else:
            ps["talk_for"] = 0.0
            if ps["sleep"]:
                ps["sleep"] = False
                self._xmas_party_begin_end(ps, "morgen")                # aufgewacht: Morgen danach
            elif moving:
                ps["p"] += dt
                ps["pegel"] = min(1.0, ps["pegel"] + dt / (party_budget(length) * 3))   # auch beim Schunkeln
            cur = ps["cur"]
            if cur and ps["p"] - cur["t0"] >= cur["dur"]:
                self._xmas_party_finish(ps, length)
            poke = self.__dict__.pop("_party_poke", False)
            if ps["cur"] is None and ps["phase"] != "end":
                if ps["phase"] == "open" and (ps["p"] >= PARTY_OPEN or poke):
                    ps["phase"] = "mid"
                if party_end_due(ps, length) and not poke:
                    self._xmas_party_begin_end(ps)
                elif ps["phase"] == "mid" and (ps["p"] >= ps["next"] or poke):
                    names = [n for n in PARTY_GAGS if party_eligible(ps, n, song, ordered=poke)]
                    if names:
                        loud = (vol or 0) >= 85
                        weights = [8 if PARTY_GAGS[n].get("song") or PARTY_GAGS[n].get("storm") else
                                   6 if n == "nachbar" and loud else 1 for n in names]
                        self._xmas_party_start(ps, ps["rng"].choices(names, weights)[0])
                    else:
                        ps["next"] = ps["p"] + 3
        cur = ps["cur"]
        lt = ps["p"] - cur["t0"] if cur else 0.0
        name = cur["name"] if cur else ps["phase"]
        P = {"step": name, "lt": lt, "dur": cur["dur"] if cur else 0, "goals": dict(PARTY_PAIR), "states": {},
             "back": {}, "say": [], "hat": True, "green": 0.0, "mugs": False, "stream": None, "puke": None,
             "flake": None, "cat": None, "zzz": False, "flicker": False, "props": set(ps["props"]),
             "snowman": ps["snowman"], "mood": mood, "pegel": ps["pegel"], "beat_age": t - s.get("beat_t", t),
             "beats": s.get("beats", 0), "star": "head" if "star_head" in ps["props"] else "tree", "hide": set(),
             "weather": ps["weather"], "warm": ps["warm"], "elf_n": ps.get("elf_n", 0), "pot": True,
             "meter": o.get("party_meter", True), "mugs_today": self._party_mug_count()}
        P["lvl"] = {"kater": 1.0 - 0.4 * lt / max(1, P["dur"]), "morgen": 0.5, "noch": 0.4}.get(name, ps["pegel"])
        if ps["phase"] == "end" and name in ("gruen", "bescherung"):
            P["lvl"] = 1.0
        free = cur is None and ps["phase"] in ("open", "mid") and not talk
        if free:
            P["mugs"] = True
            P["schunkel"] = mood == "ruhig"
            self._xmas_party_beats(ps, P, t, new_beat, mood, period, length)
            self._xmas_party_micro(ps, P, t)
            ev = ps.get("volev")                                        # Jubel bzw. Enttäuschung
            if ev and t - ev[1] < 2.5:
                P["cheer"] = ev[0]
                P["say"].append(("santa" if ev[0] == "lauter" else "mrs", self._party_line(ps, ev[0], ev[1])))
            ev = ps.get("songev")
            if ev and t - ev[1] < 2.5:
                P["say"].append((ev[0], self._party_line(ps, "meinlied", ev[1])))
            if ps["weather"] == "rain":
                P["umbrella"] = True
        elif cur:
            getattr(self, "_party_" + cur["name"])(P, lt, cur)
        if ps["weather"] == "rain":
            P["rain"] = True
        if talk:
            bench = PARTY_BENCH if ps["sleep"] else {"santa": XMAS_BENCH_X - 18, "mrs": XMAS_BENCH_X + 24}
            P.update(goals=dict(bench), back={}, mugs=False, stream=None, puke=None, flake=None, say=[], hat=True,
                     flicker=False, schunkel=False, micro=None, hide=set(), pot=True, cheer=None)
            P["states"] = {"santa": "p_sleep", "mrs": "p_sleep"} if ps["sleep"] else {}
            for k in ("elf", "deer", "mistle", "hearts", "cloud", "boot", "flash", "notes", "shock", "treesnow",
                      "cat_run", "dark", "offer", "phone", "carrot_move", "tilt", "sleigh", "ball", "flyhat",
                      "gift", "lie", "pot_head", "line", "window", "wire", "melt"):
                P.pop(k, None)
            if ps["sleep"]:
                P["zzz"], P["cat"] = True, 1.0
            elif ps["talk_for"] > 20 and int(ps["talk_for"] / 4) % 3 == 0:  # lange Moderation
                P["say"].append(("santa", self._party_line(ps, "laber", int(ps["talk_for"] / 12))))
            if muted:
                P["instant"] = True                                     # Stumm: sofort eingeschlafen
        if (clock.tm_mon == 12 and clock.tm_mday == 31 and hour >= 23) or (clock.tm_mon == 1 and clock.tm_mday == 1
                                                                            and hour < 1):
            P["fireworks"] = True
            if clock.tm_mon == 1 and hour == 0 and clock.tm_min < 10 and not talk and int(t / 6) % 2 == 0:
                P["say"].append(("mid", PARTY_LINES["neujahr"][int(t / 12) % 2]))
        P["carrot"] = "carrot" in P["props"] or P.get("carrot_on", False)
        self.vis_green = P["green"] > 0.5
        return P

    @staticmethod
    def _party_line(ps, key, salt):
        lines = PARTY_LINES[key]
        return lines[(ps["seed"] * 7 + int(salt * 10)) % len(lines)]

    def _party_mug_count(self, add=0):
        """Becher heute (für den Zähler am Barometer)."""
        today = time.strftime("%Y-%m-%d")
        day, n = self.__dict__.get("_party_mugs", (today, 0))
        if day != today:
            n = 0
        self._party_mugs = (today, n + add)
        return n + add

    def _xmas_party_beats(self, ps, P, t, new_beat, mood, period, length):
        """B: auf den Takt prosten (wild alle 8, sonst alle 12 Schläge, ruhig gar nicht); jedes Prosten hebt den
        Pegel. C: Trinkspruch wechselt."""
        if new_beat:
            ps["n"] += 1
            every = 8 if mood == "wild" else 12
            if mood != "ruhig" and ps["n"] % every == every // 2:
                ps["prost_t"] = t
                ps["pegel"] = min(1.0, ps["pegel"] + 12 * period / (party_budget(length) * 0.7))
                ps["prost_line"] = ps["rng"].choice(PARTY_LINES["prost"])
                P["mugs_today"] = self._party_mug_count(2)             # zwei Becher je Prosten
        k = t - ps["prost_t"]
        if 0 <= k < 1.8:
            P["prost"] = k
            if k < 0.9:
                P["say"].append(("mid", ps.get("prost_line", "Prost!")))

    def _xmas_party_micro(self, ps, P, t):
        """E: kleine Zwischengags beim Tanzen (stolpern, Takt verpassen, verschütten, Schluckauf, nachts gähnen)."""
        rng = ps["rng"]
        if ps["micro"] is None and ps["phase"] == "mid" and ps["pegel"] >= 0.15 and ps["p"] >= ps["micro_at"] \
                and P.get("prost") is None:
            kinds = ["stolpern", "takt", "spill"] + (["hicks", "hicks"] if ps["pegel"] >= 0.25 else []) + \
                (["gaehn", "gaehn"] if ps["sleepy"] else [])
            ps["micro"] = (rng.choice(kinds), rng.choice(("santa", "mrs")), t, rng.randrange(9))
            ps["micro_at"] = ps["p"] + rng.uniform(3, 8) / (0.4 + ps["pegel"]) * (1.4 if ps["sleepy"] else 1.0)
        m = ps["micro"]
        if m is None:
            return
        kind, who, t0, n = m
        k = t - t0
        if k >= 1.0 or k < 0:
            ps["micro"] = None
            return
        P["micro"] = (kind, who, k)
        key = {"stolpern": "hoppla", "takt": "takt", "spill": "spill", "gaehn": "gaehn"}.get(kind)
        if kind == "hicks":
            P["say"].append((who, "Hicks!"))
        elif key and k < 0.95:
            lines = PARTY_LINES[key]
            P["say"].append((who, lines[n % len(lines)]))

    # -- Gags: Ziele (x), Zustände (p_*) und was dazu gezeichnet wird ---------- #
    @staticmethod
    def _line(g, key):
        if key not in g["lines"]:
            g["lines"][key] = g["rng"].choice(PARTY_LINES[key])
        return g["lines"][key]

    def _say(self, P, g, who, key):
        P["say"].append((who, self._line(g, key)))

    def _party_pipi(self, P, lt, g):
        P["states"] = {"santa": "p_pipi", "mrs": "p_clap" if lt < 4 else "p_pipi"}
        if _win(lt, 1.0, 3.6):
            self._say(P, g, "mrs", "toll")

    def _party_baum(self, P, lt, g):
        if lt < 8:                                                     # erst er …
            P["goals"] = {"santa": XMAS_TREE_X, "mrs": 128}
            P["states"] = {"santa": "p_behind", "mrs": "p_wait"}
            if _win(lt, 2.2, 6.6):
                P["stream"] = ("tree", lt - 2.2)
                P["flicker"] = True
            if _win(lt, 4.6, 7.2):
                self._say(P, g, "mrs", "machhin")
            return
        lt -= 8                                                         # … dann sie, er pfeift
        P["goals"] = {"santa": 200, "mrs": XMAS_TREE_X}
        P["states"] = {"santa": "p_whistle", "mrs": "p_behind"}
        P["say"].append(("santa", "♪ ♫"))
        if _win(lt, 2.8, 6.2):
            self._say(P, g, "tree", "ahh")
            P["flicker"] = True

    def _party_rentier(self, P, lt, g):
        P["goals"] = {"santa": 210, "mrs": 128}
        P["states"] = {"santa": "p_excuse" if lt >= 2.8 else "p_whistle", "mrs": "p_point"}
        if _win(lt, 0.6, 2.8):
            self._say(P, g, "mrs", "werwar")
        elif lt >= 3.0:
            self._say(P, g, "santa", "ausrede")

    def _party_signatur(self, P, lt, g):
        P["goals"] = {"santa": 246, "mrs": 96}
        P["states"] = {"santa": "p_write", "mrs": "p_tsk"}
        if _win(lt, 1.0, 7.0):
            P["stream"] = ("sign", lt - 1.0)
        if lt >= 7.0:
            self._say(P, g, "mrs", "typisch")

    def _party_gelb(self, P, lt, g):
        P["goals"] = {"santa": 246 if lt < 2.2 else 182 if lt < 4.2 else 226, "mrs": 128 if lt < 4.2 else 176}
        P["states"] = {"santa": "p_grab" if lt < 4.2 else None, "mrs": "p_tongue" if lt < 4.2 else "p_worry"}
        P["flake"] = lt
        if _win(lt, 3.4, 6.0):
            self._say(P, g, "santa", "gelb")

    def _party_wichtel(self, P, lt, g):
        """1: Ein Wichtel sieht die Spuren und schreibt ihn auf die Unartig-Liste."""
        P["states"] = {"santa": "p_innocent" if lt >= 3.0 else None, "mrs": None}
        P["goals"] = {"santa": 176, "mrs": 236}
        if lt < 2.2:
            P["elf"] = (-16 + 136 * lt / 2.2, 1, "walk", lt)
        elif lt < 7.5:
            P["elf"] = (120, 1, "write" if lt >= 3.5 else "look", lt)
        else:
            P["elf"] = (120 - 136 * (lt - 7.5) / 3.0, -1, "walk", lt)
        if _win(lt, 4.0, 7.2):
            P["say"].append(("elf", self._line(g, ("unartig", "unartig2", "unartig3")[min(2, P["elf_n"])])))
        if _win(lt, 6.8, 9.5):
            self._say(P, g, "santa", "psst")

    def _party_ruelps(self, P, lt, g):
        """2: Rülpser – Schnee rieselt vom Baum, der Stern wackelt, sie fächelt."""
        P["states"] = {"santa": "p_burp" if lt < 3.0 else None, "mrs": "p_fan" if lt >= 1.6 else None}
        if _win(lt, 0.8, 2.0):
            P["shock"] = (lt - 0.8) / 1.2
        if _win(lt, 0.9, 3.4):
            P["treesnow"] = (lt - 0.9) / 2.5
        if lt >= 0.9:
            P["star_wobble"] = math.sin((lt - 0.9) * 14) * 18 * math.exp(-(lt - 0.9) * 1.2)
        if _win(lt, 0.8, 2.6):
            self._say(P, g, "santa", "ruelps")
        if _win(lt, 2.6, 5.6):
            self._say(P, g, "mrs", "fan")

    def _party_pups(self, P, lt, g):
        """3: Pupswolke – Lichter kurz aus, eine Katze flüchtet, er tut unschuldig."""
        P["goals"] = {"santa": 160, "mrs": 226 if lt < 1.0 else 254}
        P["states"] = {"santa": "p_innocent", "mrs": "p_nose" if lt >= 1.0 else None}
        if _win(lt, 0.6, 4.2):
            P["cloud"] = (lt - 0.6) / 3.6
        if _win(lt, 1.2, 2.4):
            P["dark"] = True
        if _win(lt, 1.0, 2.8):
            P["cat_run"] = (lt - 1.0) / 1.8
        if _win(lt, 1.5, 3.8):
            self._say(P, g, "mrs", "pups_mrs")
        if _win(lt, 4.0, 6.6):
            self._say(P, g, "santa", "pups_santa")

    def _party_rutsch(self, P, lt, g):
        """4: Auf der gefrorenen Pfütze ausgerutscht, ein Stiefel fliegt."""
        if lt < 4.8:
            P["goals"] = {"santa": PARTY_PUDDLE_X + 6, "mrs": 226}
            P["states"] = {"santa": "p_slip", "mrs": "p_laugh" if lt >= 2.0 else None}
        if _win(lt, 1.0, 2.4):
            P["boot"] = (lt - 1.0) / 1.4
        if _win(lt, 1.3, 3.6):
            self._say(P, g, "santa", "uff")
        if _win(lt, 2.0, 4.6):
            self._say(P, g, "mrs", "lachen")

    def _party_baumcrash(self, P, lt, g):
        """5: Er schwankt gegen den Baum, der Stern fällt ihm auf den Kopf – er trägt ihn stolz."""
        if lt < 4.5:
            P["goals"] = {"santa": XMAS_TREE_X + 46, "mrs": 210}
            P["states"] = {"santa": "p_bump", "mrs": "p_worry"}
        else:
            P["states"] = {"santa": "p_proud"}
        if _win(lt, 0.8, 2.6):
            self._say(P, g, "mrs", "ohoh")
        if _win(lt, 1.4, 2.4):
            P["flicker"] = True
        if _win(lt, 1.6, 2.6):
            P["star"] = ("fall", lt - 1.6)
        elif lt >= 2.6:
            P["star"] = "head"
        if _win(lt, 5.2, 7.8):
            self._say(P, g, "santa", "star")

    def _party_mistel(self, P, lt, g):
        """6: Mistelzweig – er will sie küssen, sie weicht aus, er küsst den Baum."""
        if lt < 6.5:
            P["mistle"] = 1.0
        P["goals"] = {"santa": 176 if lt < 3.6 else XMAS_TREE_X + 44 if lt < 8.2 else 160,
                      "mrs": 226 if lt < 1.6 else 256 if lt < 8.2 else 226}
        P["states"] = {"santa": "p_pucker" if lt < 3.6 else "p_kisstree", "mrs": "p_nope" if lt >= 1.6 else None}
        if _win(lt, 1.8, 4.0):
            self._say(P, g, "mrs", "nope")
        if _win(lt, 4.8, 8.4):
            P["hearts"] = lt - 4.8
        if _win(lt, 5.0, 7.6):
            self._say(P, g, "santa", "mwah")

    def _party_sietanzt(self, P, lt, g):
        """7: Sie hat auch einen sitzen – tanzt auf der Bank oder singt schief."""
        if g["var"] == "bank":
            P["goals"] = {"santa": 140, "mrs": XMAS_BENCH_X}
            P["states"] = {"santa": "p_covereyes", "mrs": "p_benchdance"}
            if _win(lt, 1.5, 4.2):
                self._say(P, g, "mrs", "juhu")
            if _win(lt, 4.5, 7.8):
                self._say(P, g, "santa", "ohnein")
            return
        P["states"] = {"santa": "p_ears" if lt >= 2.0 else None, "mrs": "p_sing"}
        P["notes"] = ("mrs",)
        if _win(lt, 0.5, 3.4):
            self._say(P, g, "mrs", "sing")
        if _win(lt, 3.6, 6.6):
            self._say(P, g, "santa", "autsch")

    def _party_handy(self, P, lt, g):
        """8: Sie filmt ihn mit Blitz für die Familiengruppe."""
        P["states"] = {"santa": "p_pose", "mrs": "p_phone"}
        P["phone"] = True
        for a in (1.5, 2.2, 3.0):
            if _win(lt, a, a + 0.16):
                P["flash"] = 1 - (lt - a) / 0.16
        if _win(lt, 3.4, 6.6):
            self._say(P, g, "mrs", "handy")

    def _party_schneemann(self, P, lt, g):
        """9: Schneemann – er klaut die Karottennase oder bietet ihm Glühwein an (der kippt um)."""
        P["snowman"] = "stand"
        P["goals"] = {"santa": 150 if lt < 8 else 160, "mrs": 226}
        if g["var"] == "nase":
            P["states"] = {"santa": "p_reach" if lt < 2.4 else "p_proud", "mrs": "p_laugh" if lt >= 3.4 else None}
            if lt >= 2.0:
                P["snowman"] = "nonose"
                P["carrot_on"] = True
            if _win(lt, 3.0, 6.0):
                self._say(P, g, "santa", "passt")
            if _win(lt, 3.6, 6.2):
                self._say(P, g, "mrs", "lachen")
            return
        if g["var"] == "schmilzt":
            P["states"] = {"santa": "p_worry", "mrs": "p_worry"}
            P["snowman"] = ("melt", min(1.0, max(0.0, (lt - 1.0) / 6.0)))
            if _win(lt, 3.0, 6.6):
                self._say(P, g, "santa", "schmilzt")
            return
        P["states"] = {"santa": "p_offer" if lt < 4.0 else None}
        P["offer"] = lt < 4.0
        if lt >= 2.5:
            P["snowman"] = ("tilt", min(1.0, (lt - 2.5) / 0.9))
        if _win(lt, 4.0, 7.0):
            self._say(P, g, "santa", "vertraegt")

    def _party_rentierbesuch(self, P, lt, g):
        """10: Ein Rentier schleckt am Glühweintopf, die Nase blinkt im Takt, es torkelt davon."""
        P["goals"] = {"santa": 150, "mrs": 206}
        if lt < 1.4:
            P["deer"] = (360 - 98 * lt / 1.4, -1, "walk", lt)
        elif lt < 5.0:
            P["deer"] = (262, 1, "drink", lt)
        elif lt < 8.5:
            P["deer"] = (262, 1, "stand", lt)
        else:
            P["deer"] = (262 + 110 * (lt - 8.5) / 4.5, 1, "stagger", lt)
        if "noboot" in P["props"]:
            P["deer_boot"] = True
            if _win(lt, 5.2, 8.2):
                self._say(P, g, "santa", "meinstiefel")
        if _win(lt, 2.0, 4.6):
            self._say(P, g, "santa", "meiner")

    def _party_groelen(self, P, lt, g):
        """D: Weihnachtslied im Radio – beide grölen schief mit."""
        P["states"] = {"santa": "p_sing", "mrs": "p_sing"}
        P["notes"] = ("santa", "mrs")
        if _win(lt, 0.5, 3.6):
            self._say(P, g, "santa", "sing")
        if _win(lt, 4.0, 7.2):
            self._say(P, g, "mrs", "sing2")

    def _party_schneeball(self, P, lt, g):
        """Schneeballschlacht: sie trifft ihn (Mütze fliegt), er wirft zurück und trifft den Wichtel."""
        P["states"] = {"mrs": "p_throw" if _win(lt, 0.3, 1.3) else None,
                       "santa": "p_throw" if _win(lt, 2.6, 3.6) else "p_pickup" if _win(lt, 4.6, 6.4) else None}
        P["goals"] = {"santa": 124 if _win(lt, 4.6, 6.4) else 160, "mrs": 226}
        if _win(lt, 1.0, 1.5):
            P["ball"] = ("mrs", "santa", (lt - 1.0) / 0.5)
        if _win(lt, 3.4, 4.0):
            P["ball"] = ("santa", "elf", (lt - 3.4) / 0.6)
        if _win(lt, 1.5, 6.4):
            P["hat"] = False
            P["flyhat"] = ("fall", min(1.0, (lt - 1.5) / 1.0))
        if lt < 2.0:
            pass
        elif lt < 3.9:
            P["elf"] = (-16 + 86 * min(1.0, (lt - 2.0) / 1.4), 1, "walk" if lt < 3.4 else "look", lt)
        elif lt < 6.2:
            P["elf"] = (70, 1, "hit", lt)
        else:
            P["elf"] = (70 - 90 * (lt - 6.2) / 1.8, -1, "walk", lt)
        if _win(lt, 1.6, 3.4):
            self._say(P, g, "mrs", "erwischt")
        if _win(lt, 4.0, 6.0):
            P["say"].append(("elf", self._line(g, "treffer")))

    def _party_lichterkette(self, P, lt, g):
        """In der Lichterkette verheddert – danach blinkt er bunt, der Baum bleibt dunkel."""
        if lt < 2.8:
            P["goals"] = {"santa": XMAS_TREE_X + 46, "mrs": 226}
            P["states"] = {"santa": "p_bump"}
        else:
            P["states"] = {"santa": "p_proud"}
        if _win(lt, 1.4, 2.4):
            P["wire"] = (lt - 1.4) / 1.0
        if lt >= 1.6:
            P["props"].add("wrapped")
        if _win(lt, 3.6, 6.0):
            self._say(P, g, "santa", "leuchte")
        if _win(lt, 4.4, 6.8):
            self._say(P, g, "mrs", "stehtdir")

    def _party_schneeengel(self, P, lt, g):
        """Schneeengel – er bleibt liegen, sie zieht ihn am Bart wieder hoch."""
        P["goals"] = {"santa": 196, "mrs": 128 if lt >= 4.6 else 236}
        if _win(lt, 1.2, 7.2):
            P["hide"] = {"santa"}
            P["lie"] = lt - 1.2
            P["lie_x"] = 196
            if _win(lt, 2.5, 4.8):
                P["say"].append(("lie", self._line(g, "engel")))
        if lt >= 4.0:
            P["props"].add("angel")
        P["states"] = {"mrs": "p_tug" if _win(lt, 5.0, 7.2) else None}
        if _win(lt, 5.0, 7.2):
            self._say(P, g, "mrs", "hoch")

    def _party_geschenk(self, P, lt, g):
        """Geschenk heimlich schütteln, auspacken: Socken. Tränchen."""
        if lt < 7.5:
            P["goals"] = {"santa": XMAS_TREE_X + 46, "mrs": 170}
            P["states"] = {"santa": "p_present" if lt < 3.6 else "p_socks", "mrs": "p_worry" if lt >= 5 else None}
        if _win(lt, 0.8, 3.6):
            P["gift"] = ("box", 1.0 <= lt < 3.0)
        elif _win(lt, 3.6, 7.5):
            P["gift"] = ("socks", False)
        if _win(lt, 4.0, 8.0):
            P["tears"] = lt - 4.0
        if _win(lt, 4.0, 6.8):
            self._say(P, g, "santa", "socken")
        if _win(lt, 6.0, 8.6):
            self._say(P, g, "mrs", "gestrickt")

    def _party_topf(self, P, lt, g):
        """Topf leer: über den Kopf gestülpt, blind gegen den Baum."""
        P["goals"] = {"santa": PARTY_POT_X - 24 if lt < 3.4 else XMAS_TREE_X + 46 if lt < 8.6 else 160, "mrs": 226}
        P["states"] = {"santa": "p_drinkpot" if lt < 3.4 else "p_blind" if lt < 8.6 else None,
                       "mrs": "p_worry" if _win(lt, 3.6, 8.6) else None}
        if _win(lt, 2.2, 8.6):
            P["pot"] = False
            P["pot_head"] = "up" if lt < 3.4 else "on"
        if lt >= 6.3:
            P["star_wobble"] = math.sin((lt - 6.3) * 14) * 16 * math.exp(-(lt - 6.3) * 1.2)
        if _win(lt, 6.3, 8.4):
            self._say(P, g, "santa", "bong")
        if _win(lt, 3.8, 6.0):
            self._say(P, g, "mrs", "schatz")

    def _party_polonaise(self, P, lt, g):
        """Polonaise: Wichtel, Rentier, Katze und die beiden ziehen quer durchs Bild."""
        if lt < 6.0:
            P["goals"] = {"santa": -132, "mrs": -166}
        elif lt < 15.1:
            lead = -40 + 60 * (lt - 6.0)
            P["goals"] = {"santa": lead - 92, "mrs": lead - 126}
            P["line"] = lead
            P["follow"] = True
            if _win(lt, 8.0, 11.0):
                P["say"].append(("line", self._line(g, "polonaise")))

    def _party_taxi(self, P, lt, g):
        """Taxi nach Hause: Das Rentier zieht ihn im Schlitten weg – er kommt aber wieder."""
        P["goals"] = {"santa": 160 if lt < 2.4 else 124 if lt < 3.6 else 420 if lt < 8.6 else 160, "mrs": 226}
        if lt < 2.4:
            P["sleigh"] = (-70 + 190 * lt / 2.4, False)
        elif lt < 8.6:
            P["sleigh"] = (None, lt >= 3.2)
            if lt >= 3.2:
                P["hide"] = {"santa"}
        P["states"] = {"mrs": "p_bye" if _win(lt, 3.8, 7.2) else None}
        if _win(lt, 4.0, 7.0):
            self._say(P, g, "mrs", "gutenacht")
        if _win(lt, 9.6, 12.4):
            self._say(P, g, "santa", "vergessen")

    def _party_nachbar(self, P, lt, g):
        """Im Haus auf dem Hügel geht ein Fenster auf: „Ruhe da unten!“ – „Psst!“."""
        if _win(lt, 0.5, 6.5):
            P["window"] = lt - 0.5
        if _win(lt, 1.2, 3.4):
            P["say"].append(("window", self._line(g, "ruhe")))
        if lt >= 3.2:
            P["states"] = {"santa": "p_shush", "mrs": "p_shush"}
        if _win(lt, 3.4, 5.4):
            self._say(P, g, "santa", "psst2")

    def _party_stiefel(self, P, lt, g):
        """Der Wichtel bringt den Stiefel zurück."""
        P["goals"] = {"santa": 150, "mrs": 226}
        if lt < 2.2:
            P["elf"] = (-16 + 122 * lt / 2.2, 1, "carry", lt)
        elif lt < 6.0:
            P["elf"] = (106, 1, "carry" if lt < 4.0 else "look", lt)
        else:
            P["elf"] = (106 - 122 * (lt - 6.0) / 2.2, -1, "walk", lt)
        if lt >= 4.0:
            P["props"].discard("noboot")
        if _win(lt, 2.4, 4.4):
            P["say"].append(("elf", self._line(g, "stiefel_da")))
        if _win(lt, 4.6, 7.0):
            self._say(P, g, "santa", "danke")

    def _party_muetze(self, P, lt, g):
        """Sturm: Die Mütze fliegt davon, er rennt hinterher."""
        P["goals"] = {"santa": 380 if _win(lt, 1.0, 4.0) else 160, "mrs": 226}
        P["states"] = {"mrs": "p_laugh" if _win(lt, 2.0, 4.5) else None}
        if _win(lt, 0.5, 4.0):
            P["hat"] = False
            P["flyhat"] = ("wind", min(1.0, (lt - 0.5) / 1.7))
        if _win(lt, 0.8, 3.0):
            self._say(P, g, "santa", "muetze")
        if _win(lt, 2.0, 4.5):
            self._say(P, g, "mrs", "lachen")

    def _party_gruen(self, P, lt, g):
        P["goals"] = {"santa": 226, "mrs": 176}
        P["states"] = {"santa": "p_sick", "mrs": "p_worry"}
        P["green"] = min(1.0, lt / 4.0)
        if _win(lt, 1.0, 5.0):
            self._say(P, g, "santa", "uebel")

    def _party_bescherung(self, P, lt, g):
        P["goals"] = {"santa": 226, "mrs": 176}
        P["states"] = {"santa": "p_vomit" if lt >= 0.6 else "p_sick", "mrs": "p_hat" if lt >= 1.0 else "p_worry"}
        P["green"] = 1.0
        P["hat"] = lt < 1.0
        for a in (1.6, 3.2, 4.6):                                   # drei Schwalle
            if _win(lt, a, a + 0.8):
                P["puke"] = (lt - a) / 0.8
        if lt >= 5.6:
            self._say(P, g, "mrs", "bescherung")

    def _party_kater(self, P, lt, g):
        P["goals"] = dict(PARTY_BENCH)
        P["states"] = {"santa": "p_sleep", "mrs": "p_sleep"}
        P["green"] = max(0.0, 1.0 - lt / 8.0)
        P["zzz"] = True
        if lt >= 3.0:
            P["cat"] = min(1.0, (lt - 3.0) / 0.6)

    def _party_morgen(self, P, lt, g):
        """11: Der Morgen danach – Sonnenbrille, Kopf halten, jeder Schlag tut weh; der Stern dimmt sich."""
        P["states"] = {"santa": "p_hangover", "mrs": "p_worry"}
        P["shades"] = True
        P["star_dim"] = True
        if _win(lt, 1.0, 4.6):
            self._say(P, g, "santa", "kopf")

    def _party_noch(self, P, lt, g):
        if lt < 3.6:
            P["goals"] = {"santa": 276, "mrs": 226 if lt >= 1.4 else PARTY_BENCH["mrs"]}
            P["states"] = {"santa": "p_stagger", "mrs": "p_pull"}
            if lt < 3.0:
                self._say(P, g, "santa", "noch")
        else:
            P["back"] = {"santa": True}                             # sie zieht ihn rückwärts zurück

    # -- Haltungen ----------------------------------------------------------- #
    @staticmethod
    def _xmas_party_pose(who, state, t, lt):
        """Haltung für die Zustände p_* (Hände/Füße wie SANTA_POSES/MRS_POSES)."""
        base = {"bob": 0.0, "dx": 0.0, "spin": 0.0}
        sw = math.sin(t * 7)
        santa = who == "santa"
        feet = {"lf": (-4, 40), "rf": (4, 40)} if santa else {"lf": (-3, 22), "rf": (3, 22)}
        if state in ("p_pipi", "p_wait", "p_behind"):               # Knie zusammen, von einem Bein aufs andere
            tap = max(0.0, math.sin(t * 9))
            if santa:
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
        if state in ("p_whistle", "p_innocent"):
            return dict(base, lh=(-4, 34), rh=(4, 34), lean=math.sin(t * 2) * 3, head=math.sin(t * 4) * 8 - 6, **feet)
        if state == "p_point":
            return dict(base, lh=(-28, 18), rh=(6, 28), lean=-6, head=-10, **feet)
        if state == "p_excuse":
            return dict(base, lh=(14, 22), rh=(32, -4), lean=4, head=10, **feet)
        if state == "p_write":
            return dict(base, lh=(16, 36), rh=(-16, 36), lf=(-10, 39), rf=(10, 39), lean=-3, head=-12,
                        bob=math.sin(t * 3))
        if state == "p_tsk":
            return dict(base, lh=(6, 28), rh=(-6, 28), lean=0, head=math.sin(t * 6) * 10, **feet)
        if state == "p_tongue":
            return dict(base, lh=(-24, -6), rh=(24, -6), lf=(-4, 22), rf=(4, 22), lean=-2, head=0)
        if state == "p_grab":
            return dict(base, lh=(-32, 4), rh=(14, 22), lf=(-8, 39), rf=(6, 40), lean=-8, head=-8)
        if state in ("p_sick", "p_stagger"):
            return dict(base, lh=(14, 22), rh=(-14, 22), lean=math.sin(t * 1.6) * 8, head=math.sin(t * 2.1) * 12,
                        bob=math.sin(t * 1.6) * 1.5, **feet)
        if state == "p_worry":
            return dict(base, lh=(10, 12), rh=(-10, 12), lean=-2, head=8, **feet)
        if state == "p_vomit":
            return dict(base, lh=(14, 22), rh=(24, 20), lf=(-8, 39), rf=(10, 38), lean=18, head=22)
        if state == "p_hat":
            return dict(base, lh=(10, 14), rh=(18, -18), lean=2, head=10, **feet)
        if state == "p_sleep":
            pose = {"lh": (14, 22), "rh": (-14, 22), "lf": (0, 0), "rf": (0, 0), "lean": 0,
                    "head": 22 if santa else -20, "bob": math.sin(t * 0.8) * 0.8, "dx": 0.0, "spin": 0.0}
            return pose if santa else dict(pose, lh=(10, 16), rh=(-10, 16))
        if state == "p_slip":                                       # auf dem Hintern im Schnee
            return {"lh": (-26, 14), "rh": (26, 14), "lf": (0, 0), "rf": (0, 0), "lean": -6, "head": -10,
                    "bob": 0.0, "dx": 0.0, "spin": 0.0}
        if state == "p_pull":
            return dict(base, lh=(-20, 10), rh=(28, 6), lf=(-8, 21), rf=(4, 22), lean=-10, head=-6)
        if state == "p_burp":
            return dict(base, lh=(-12, 30), rh=(12, 30), lean=-10, head=-16, bob=-2 * abs(math.sin(t * 20)), **feet)
        if state == "p_fan":
            return dict(base, lh=(10, 16), rh=(-12 + math.sin(t * 16) * 5, -12), lean=6, head=12, **feet)
        if state == "p_nose":
            return dict(base, lh=(-22, 8), rh=(-14, -10), lean=8, head=14, **feet)
        if state == "p_laugh":
            sh = abs(math.sin(t * 14))
            if santa:
                return dict(base, lh=(14, 26), rh=(-14, 26), lean=-6, head=-12 + sh * 6, bob=sh * 2, **feet)
            return dict(base, lh=(8, 26), rh=(-8, 26), lean=-6, head=-12 + sh * 6, bob=sh * 2, **feet)
        if state == "p_bump":
            return dict(base, lh=(-30, -2), rh=(-12, 10), lf=(-10, 39), rf=(6, 40), lean=-22, head=-18)
        if state == "p_proud":
            return dict(SANTA_POSES[5], lean=-4, head=-6 + math.sin(t * 3) * 4, **base)
        if state == "p_pucker":
            return dict(base, lh=(14, 22), rh=(24, 4), lf=(-6, 40), rf=(8, 39), lean=16, head=14)
        if state == "p_nope":
            return dict(base, lh=(-8, 28), rh=(-26, -18), lean=8, head=12, **feet)
        if state == "p_kisstree":
            return dict(base, lh=(-26, -6), rh=(-12, -10), lf=(-8, 40), rf=(8, 40), lean=-20, head=-16)
        if state == "p_benchdance":
            p = MRS_POSES[int(t * 3) % len(MRS_POSES)]
            return dict(p, bob=abs(math.sin(t * 9)) * 4, dx=0.0, spin=0.0, lean=p["lean"] + math.sin(t * 6) * 8)
        if state == "p_covereyes":
            return dict(base, lh=(17, -17), rh=(-17, -17), lean=-4, head=-6, **feet)
        if state == "p_sing":
            w = math.sin(t * 4)
            if santa:
                return dict(SANTA_POSES[1], lh=(-10, -30 + w * 4), rh=(10, -30 - w * 4), lean=w * 8, head=-w * 10, **base)
            return dict(MRS_POSES[2], lean=w * 8, head=-w * 12, **base)
        if state == "p_ears":
            return dict(base, lh=(10, -18), rh=(-10, -18), lean=-6, head=-10 + math.sin(t * 8) * 4, **feet)
        if state == "p_phone":
            return dict(base, lh=(8, 16), rh=(-6, -18), lean=-2, head=6, **feet)
        if state == "p_pose":
            k = int(t * 1.4) % 3
            return dict(SANTA_POSES[(1, 3, 5)[k]], **base)
        if state == "p_reach":
            return dict(base, lh=(-32, -12), rh=(14, 22), lf=(-8, 39), rf=(6, 40), lean=-10, head=-10)
        if state == "p_offer":
            return dict(base, lh=(-30, -4), rh=(14, 22), lf=(-8, 39), rf=(6, 40), lean=-8, head=-6)
        if state == "p_throw":
            k = (t * 2.2) % 1.0
            if santa:
                return dict(base, lh=(-30 + 50 * k, -24 + 30 * k), rh=(14, 22), lean=-6 + 12 * k, head=-8, **feet)
            return dict(base, lh=(10, 16), rh=(30 - 50 * k, -24 + 30 * k), lean=6 - 12 * k, head=-8, **feet)
        if state == "p_pickup":
            return dict(base, lh=(-20, 36), rh=(14, 26), lf=(-8, 38), rf=(8, 38), lean=-18, head=-14, bob=4)
        if state == "p_tug":
            return dict(base, lh=(10, 16), rh=(30, 22), lean=-12 + math.sin(t * 6) * 4, head=-8, **feet)
        if state == "p_present":
            sh = math.sin(t * 22) * 3
            return dict(base, lh=(12 + sh, 6), rh=(-12 + sh, 6), lean=0, head=8, **feet)
        if state == "p_socks":
            return dict(base, lh=(8, -12), rh=(-8, -12), lean=0, head=12 + math.sin(t * 3) * 4, **feet)
        if state == "p_drinkpot":
            return dict(base, lh=(-4, -30), rh=(4, -30), lean=-6, head=-16, **feet)
        if state == "p_blind":
            return dict(base, lh=(-30, -2), rh=(-26, 6), lean=-6 + math.sin(t * 3) * 4, head=0, **feet)
        if state == "p_bye":
            w = math.sin(t * 10)
            return dict(MRS_POSES[2], rh=(10 + w * 7, -34), **base)
        if state == "p_shush":
            if santa:
                return dict(base, lh=(21, -12), rh=(-14, 22), lean=0, head=4, **feet)
            return dict(base, lh=(10, 16), rh=(-14, -9), lean=0, head=-4, **feet)
        if state == "p_hangover":
            return dict(base, lh=(17, -20), rh=(-17, -20), lean=math.sin(t * 1.2) * 4, head=8, **feet)
        return dict(base, lh=(14, 22), rh=(-14, 22), lean=0, head=4, **feet)

    def _xmas_party_mods(self, P, who, pose, t):
        """Pegel: wackliger Stand; schunkeln; prosten; Zwischengags; Schluckauf; beim Kater jeder Schlag ein Zucken."""
        lvl = P["lvl"]
        ph = 0.0 if who == "santa" else 1.7
        pose["lean"] = pose.get("lean", 0) + math.sin(t * 1.3 + ph) * 8 * lvl
        pose["dx"] = pose.get("dx", 0.0) + math.sin(t * 0.9 + ph) * 4 * lvl
        if P.get("schunkel"):                                         # ruhige Musik: beide wiegen sich mit
            w = math.sin(t * 1.6)
            pose["lean"] = pose.get("lean", 0) * 0.3 + w * 14
            pose["dx"] = pose.get("dx", 0.0) * 0.3 + w * 6
            pose["bob"] = pose.get("bob", 0.0) * 0.3
        k = P.get("prost")
        if k is not None:
            if who == "santa":
                pose["lh"] = (-8, -30) if k < 0.9 else (21, -13)
            else:
                pose["rh"] = (8, -32) if k < 0.9 else (-14, -10)
        m = P.get("micro")
        if m and m[1] == who:
            kind, _w, k = m
            if kind == "stolpern":
                f = math.sin(min(1.0, k / 0.7) * math.pi)
                pose["lean"] = pose.get("lean", 0) + 22 * f
                pose["dx"] = pose.get("dx", 0.0) + 10 * f
                pose["bob"] = pose.get("bob", 0.0) + 3 * f
            elif kind == "hicks" and k < 0.2:
                pose["bob"] = pose.get("bob", 0.0) - 5
            elif kind == "gaehn":
                if who == "santa":
                    pose["lh"] = (21, -13)
                else:
                    pose["rh"] = (-14, -10)
                pose["head"] = -14
        if P.get("cheer") == "lauter":                                 # lauter gedreht: Jubel
            pose["lh"], pose["rh"] = (-10, -32), (10, -32)
            if who == "mrs":
                pose["lh"], pose["rh"] = (-12, -34), (12, -34)
            pose["bob"] = pose.get("bob", 0.0) - 3 * abs(math.sin(t * 9))
        elif P.get("cheer") == "leiser":                               # leiser: enttäuscht
            pose["head"] = 16 if who == "santa" else -16
            pose["lean"] = pose.get("lean", 0) * 0.3
        if who == "santa" and "noboot" in P["props"]:                  # ohne Stiefel: hinkt
            pose["bob"] = pose.get("bob", 0.0) + 2 * abs(math.sin(t * 4))
        if P["step"] == "morgen" and who == "santa" and P["beat_age"] < 0.15:
            pose["bob"] = pose.get("bob", 0.0) - 3                  # jeder Schlag tut weh
            pose["head"] = pose.get("head", 0) + 10
        return pose

    def _xmas_party_look(self, P, who, state):
        """Zusatzangaben fürs Zeichnen der Figur (Gesichtsfarbe, Mütze, Mund, Sonnenbrille, Karottennase)."""
        if who == "santa":
            return {"green": P["green"], "red": P["lvl"], "hat": P["hat"], "snore": state == "p_sleep",
                    "shades": P.get("shades", False), "carrot": P.get("carrot", False),
                    "mouth": state in ("p_sing", "p_burp"), "sock": "noboot" in P["props"],
                    "pot": P.get("pot_head") == "on"}
        return {"mouth": state in ("p_tongue", "p_sing"), "asleep": state == "p_sleep"}

    # -- Requisiten ---------------------------------------------------------- #
    def _xmas_party_sky(self, img, d, P, t):
        """Himmel: Feuerwerk an Silvester."""
        if not P.get("fireworks"):
            return
        cols = [(255, 90, 80), (255, 220, 90), (110, 190, 255), (140, 255, 140), (255, 130, 230)]
        for i in range(4):
            per = 2.6 + i * 0.37
            k = ((t + i * 1.13) % per) / per
            seed = int((t + i * 1.13) // per) * 7 + i
            cx, cy = 150 + ((seed * 53) % 150), 22 + ((seed * 29) % 50)
            col = cols[seed % len(cols)]
            if k < 0.3:                                             # Rakete steigt
                y = VIS_H - (VIS_H - cy) * (k / 0.3)
                d.line([(cx, y), (cx, y + 6)], fill=(255, 230, 180), width=1)
                continue
            r = (k - 0.3) / 0.7 * 26
            fade = 1 - (k - 0.3) / 0.7
            c = tuple(int(v * fade) for v in col)
            for j in range(12):
                a = j * math.pi / 6
                x, y = cx + math.cos(a) * r, cy + math.sin(a) * r + r * r * 0.012
                d.ellipse([x - 1.2, y - 1.2, x + 1.2, y + 1.2], fill=c)

    def _xmas_party_ground(self, img, d, P, floor, t):
        """Hinter den Figuren: Haus des Nachbarn, Glühweintopf, Pfütze, Schrift im Schnee, gelber Fleck, Sack,
        Schneeengel, Schneemann, Rentier, er liegend im Schnee."""
        self._xmas_party_house(img, d, P.get("window"), t)
        if P.get("meter"):
            self._xmas_party_meter(img, d, P)
        x = PARTY_POT_X                                             # Topf mit Dampf
        self._blob(img, x, floor + 1, 34, 8, (150, 165, 190), gloss=0)
        if P.get("pot", True):
            d.rectangle([x - 12, floor - 22, x + 12, floor], fill=(40, 36, 44))
            d.rectangle([x - 14, floor - 24, x + 14, floor - 20], fill=(70, 64, 78))
            d.rectangle([x - 10, floor - 16, x + 10, floor - 8], fill=(120, 30, 40))
            for k in range(3):
                pts = [(x - 6 + k * 6 + math.sin(t * 2.5 + yy * 0.25 + k) * 2.5, floor - 26 - yy)
                       for yy in range(0, 22, 2)]
                d.line(pts, fill=(205, 205, 222), width=1)
        step, lt, props = P["step"], P["lt"], P["props"]
        grow = 1.0 if "puddle" in props else min(1.0, max(0.0, lt - 2.2) / 4.0) if step == "baum" else 0.0
        if grow > 0:
            self._blob(img, PARTY_PUDDLE_X, floor + 6, 10 + 22 * grow, 3 + 4 * grow, (226, 200, 70), gloss=0.6)
        n = len(PARTY_SIGN) if "sign" in props else \
            int(min(len(PARTY_SIGN), max(0.0, lt - 1.0) / 6.0 * (len(PARTY_SIGN) + 0.4))) if step == "signatur" else 0
        if n:
            font = self.__dict__.setdefault("_party_sign_font", load_font(13, bold=True))
            d.text((PARTY_SIGN_X, floor + 3), PARTY_SIGN[:n], font=font, fill=(222, 196, 64))
        if "spot" in props or (step == "gelb" and lt >= 5.6):
            d.ellipse([124, floor + 6, 130, floor + 9], fill=(222, 196, 64))
        if "sack" in props or step == "bescherung":
            sx = PARTY_SACK_X
            self._blob(img, sx, floor + 1, 40, 8, (150, 165, 190), gloss=0)
            self._blob(img, sx, floor - 14, 34, 30, (150, 100, 56), gloss=0.2)
            self._blob(img, sx, floor - 30, 16, 8, (120, 80, 44), gloss=0.2)
            d.line([(sx - 6, floor - 27), (sx + 6, floor - 27)], fill=(220, 40, 50), width=2)
            if "sack" in props or lt >= 1.6:
                self._blob(img, sx + 2, floor - 30, 12, 5, (130, 175, 70), gloss=0.5)
        if "angel" in props:                                        # Abdruck des Schneeengels
            ax = 196
            self._blob(img, ax, floor + 6, 46, 10, (200, 210, 232), gloss=0)
            for side in (-1, 1):
                self._blob(img, ax - 4, floor + 6 + side * 4, 22, 6, (205, 214, 235), ang=side * 25, gloss=0)
        if P.get("snowman"):
            self._xmas_party_snowman(img, d, PARTY_SNOWMAN_X, floor, P["snowman"])
        if P.get("deer"):
            self._xmas_party_deer(img, d, P["deer"], floor, t, P["beats"], P.get("deer_boot"))
        if P.get("lie") is not None:
            self._xmas_party_lying(img, d, P["lie_x"], floor, t, P["lie"], P)

    def _xmas_party_snowman(self, img, d, x, floor, state):
        if isinstance(state, tuple) and state[0] == "melt" or state == "melted":
            k = 1.0 if state == "melted" else state[1]
            self._blob(img, x, floor + 4, 18 + 26 * k, 4 + 4 * k, (170, 200, 235), gloss=0.8)       # Pfütze
            sc = 1 - 0.8 * k
            for h, r in ((0, 11), (19, 8), (33, 6)):
                r2 = max(1.0, r * sc)
                self._blob(img, x, floor - 2 - (h * sc + r2), r2 * 2.2, r2 * 2, (244, 246, 252), gloss=0.2)
            if k > 0.7:                                               # übrig: Karotte und Kohle
                d.polygon([(x + 8, floor + 2), (x + 8, floor + 5), (x + 18, floor + 4)], fill=(240, 130, 30))
                d.ellipse([x - 6, floor + 2, x - 4, floor + 4], fill=(30, 30, 36))
            return
        tilt = 0.0
        if isinstance(state, tuple):
            state, tilt = "stand", state[1]
        if state == "fallen":
            tilt = 1.0
        ang = tilt * math.pi / 2                                     # kippt nach links um
        parts = [(0, 11, 24), (19, 8, 18), (33, 6, 13)]             # Höhe über dem Boden, Radius, Durchmesser
        pts = []
        for h, r, w in parts:
            cx = x - math.sin(ang) * (h + r)
            cy = floor - 2 - math.cos(ang) * (h + r) - math.sin(ang) * r * 0.8
            self._blob(img, cx, cy, w, w, (244, 246, 252), gloss=0.2)
            pts.append((cx, cy))
        hx, hy = pts[2]
        for side in (-1, 1):                                        # Kohleaugen
            ex, ey = hx + side * 2.5 * math.cos(ang) - 1.5 * math.sin(ang), hy - 2 * math.cos(ang)
            d.ellipse([ex - 1, ey - 1, ex + 1, ey + 1], fill=(30, 30, 36))
        if state != "nonose":
            d.polygon([(hx - 1, hy + 1), (hx - 1, hy + 3), (hx - 9 * math.cos(ang) - 2, hy + 2 + 8 * math.sin(ang))],
                      fill=(240, 130, 30))
        bx, by = pts[1]
        for side in (-1, 1):                                        # Zweigarme
            d.line([(bx + side * 6 * math.cos(ang), by), (bx + side * 16 * math.cos(ang), by - 8 + abs(math.sin(ang)) * 8)],
                   fill=(110, 76, 44), width=2)

    def _xmas_party_deer(self, img, d, deer, floor, t, beats, boot=False):
        """Rentier: Körper, Beine, Kopf mit Geweih; die Nase leuchtet (blinkt im Takt, sobald es getrunken hat)."""
        x, face, mode, lt = deer
        wob = math.sin(t * 3) * 6 if mode == "stagger" else 0
        x += wob
        brown, dark = (150, 98, 58), (96, 62, 36)
        body_y = floor - 30
        step = math.sin(t * 10) * (4 if mode in ("walk", "stagger") else 0)
        for i, lx in enumerate((-12, -6, 8, 14)):                     # Beine
            off = step * (1 if i % 2 else -1)
            d.line([(x + lx, body_y + 6), (x + lx + off, floor)], fill=dark, width=3)
        self._blob(img, x, body_y, 42, 20, brown, gloss=0.3)
        self._blob(img, x - face * 20, body_y - 4, 8, 6, (240, 236, 230), gloss=0.1)   # Schwanz
        drink = mode == "drink"
        hx = x + face * (24 if not drink else 28)
        hy = body_y - 16 if not drink else body_y - 4 + math.sin(t * 9) * 1.5
        d.line([(x + face * 12, body_y - 4), (hx - face * 3, hy + 3)], fill=brown, width=7)    # Hals
        self._blob(img, hx, hy, 15, 11, brown, gloss=0.3)
        for side in (-1, 1):                                        # Geweih
            ax = hx - face * 3 + side * 3
            d.line([(ax, hy - 4), (ax + side * 4, hy - 14), (ax + side * 9, hy - 18)], fill=(200, 170, 120), width=2)
            d.line([(ax + side * 4, hy - 14), (ax + side * 1, hy - 20)], fill=(200, 170, 120), width=2)
        d.ellipse([hx + face * 1 - 1, hy - 3, hx + face * 1 + 1, hy - 1], fill=(20, 20, 24))
        drunk = mode in ("stand", "stagger") or (drink and lt > 3.5)
        on = (beats % 2 == 0) if drunk else True
        nose = (255, 50, 50) if on else (110, 30, 30)
        if on and drunk:
            self._blob(img, hx + face * 8, hy + 2, 16, 16, (255, 60, 60), alpha=0.45, flat=True)
        self._blob(img, hx + face * 8, hy + 2, 6, 6, nose, gloss=0.9)
        if boot and mode in ("stand", "stagger"):                   # kaut auf seinem Stiefel
            self._blob(img, hx + face * 6, hy + 7 + math.sin(t * 8), 14, 8, (34, 26, 24), gloss=0.9)

    def _xmas_party_over(self, img, d, P, acts, floor, t):
        """Vor den Figuren: Becher, Requisiten in den Händen, Strahl, Schwall, Flocke, Wolke, Katzen, Wichtel,
        Mistelzweig, Herzen, Noten, Blitz, Zzz, Sprechblasen."""
        heads = self.__dict__.get("_xmas_heads", {})
        hands = self.__dict__.get("_xmas_hands", {})
        visible = {w: -XMAS_OFF_MARGIN < acts[w]["x"] < WIDTH + XMAS_OFF_MARGIN and acts[w]["state"] != "p_behind"
                   and w not in P["hide"] for w in acts}
        if P["mugs"] or P.get("offer"):
            for who, i in (("santa", 0), ("mrs", 1)):
                ok_state = acts[who]["state"] in ("dance", "walk") or (who == "santa" and P.get("offer"))
                if visible[who] and who in hands and ok_state:
                    hx, hy = hands[who][i]
                    d.rectangle([hx + 3, hy - 5, hx + 7, hy - 1], outline=(240, 240, 240))
                    self._blob(img, hx, hy - 3, 9, 11, (178, 30, 42), gloss=0.9)
                    m = P.get("micro")
                    if m and m[0] == "spill" and m[1] == who:       # verschüttet
                        for j in range(4):
                            dy = m[2] * 60 + j * 7
                            d.ellipse([hx - 4 + j * 2, hy + dy - 2, hx - 2 + j * 2, hy + dy + 1], fill=(190, 30, 46))
        if not P["hat"] and "mrs" in hands and P["step"] == "bescherung":
            hx, hy = hands["mrs"][1]
            self._xmas_party_hat(d, img, hx, hy - 6, t)
        self._xmas_party_extras(img, d, P, acts, floor, t, heads, hands, visible)
        if P.get("phone") and "mrs" in hands:
            hx, hy = hands["mrs"][1]
            d.rounded_rectangle([hx - 4, hy - 10, hx + 4, hy + 2], radius=2, fill=(30, 32, 40), outline=(140, 150, 170))
        stream = P["stream"]
        if stream and stream[0] == "tree":
            self._xmas_party_arc(d, (XMAS_TREE_X + 28, floor - 14), (PARTY_PUDDLE_X - 4, floor + 5), 10, t)
        if stream and stream[0] == "sign" and visible["santa"] and "santa" in heads:
            n = min(len(PARTY_SIGN) - 0.6, stream[1] / 6.0 * (len(PARTY_SIGN) + 0.4))
            tip = (PARTY_SIGN_X + 6 + n * 8.5, floor + 9 + math.sin(t * 9) * 2)
            self._xmas_party_arc(d, (heads["santa"][0] - 6, floor - 34), tip, 14, t)
        if P["puke"] is not None and "santa" in heads:
            hx, hy = heads["santa"]
            mouth, sack = (hx + 4, hy + 8), (PARTY_SACK_X, floor - 30)
            for i in range(10):
                f = i / 9 * min(1.0, P["puke"] * 2)
                x = mouth[0] + (sack[0] - mouth[0]) * f
                y = mouth[1] + (sack[1] - mouth[1]) * f - math.sin(f * math.pi) * 8
                r = 4 + 2 * math.sin(i * 1.7 + t * 12)
                self._blob(img, x, y, r * 2, r * 1.6, (128, 176, 66), gloss=0.6)
        fl = P["flake"]
        if fl is not None and fl < 5.6:                             # erreicht den Mund, als sie weggezogen wird
            mouth = floor - 78
            y = fl / 4.6 * mouth if fl < 4.6 else mouth + (fl - 4.6) * (floor + 6 - mouth)
            x = 130 + math.sin(fl * 2) * 3
            d.ellipse([x - 2.4, y - 2.4, x + 2.4, y + 2.4], fill=(240, 214, 70))
        if P.get("shock") is not None and "santa" in heads:         # Rülpser: Druckwellen
            hx, hy = heads["santa"]
            for j in range(3):
                r = (P["shock"] * 70) - j * 12
                if r > 2:
                    v = int(220 * (1 - P["shock"]))
                    d.arc([hx - r, hy + 6 - r, hx + r, hy + 6 + r], 120, 240, fill=(v, v, min(255, v + 30)), width=2)
        if P.get("treesnow") is not None:                           # Schnee fällt von den Zweigen
            k = P["treesnow"]
            for j in range(26):
                bx = XMAS_TREE_X - 42 + (j * 37) % 84
                by = floor - 104 + (j * 23) % 84 + k * 80
                if by < floor:
                    d.ellipse([bx - 2.2, by - 2.2, bx + 2.2, by + 2.2], fill=(250, 252, 255), outline=(190, 200, 225))
        if P.get("cloud") is not None and "santa" in heads:         # Pupswolke
            k = P["cloud"]
            cx = acts["santa"]["x"] - 18 - k * 10
            for j in range(5):
                r = 9 + k * 14 + j * 2
                self._blob(img, cx + math.sin(j * 2.1 + t) * 9, floor - 30 - k * 40 - j * 6, r * 2.4, r * 2,
                           (130, 190, 70), alpha=round(0.9 * (1 - k * 0.7), 1), flat=True)
        if P.get("cat_run") is not None:                            # Katze flüchtet
            k = P["cat_run"]
            self._xmas_party_cat(img, d, 150 + k * 200, floor + 6, t * 3, 1.0)
        if P.get("boot") is not None and "santa" in hands:          # Stiefel fliegt
            k = P["boot"]
            bx = acts["santa"]["x"] - 10 - k * 120
            by = floor - 10 - math.sin(k * math.pi) * 90 + k * 30
            self._blob(img, bx, by, 18, 11, (34, 26, 24), ang=k * 720, gloss=0.9)
        if P.get("elf"):
            self._xmas_party_elf(img, d, P["elf"], floor, t)
        if P.get("mistle"):                                          # Mistelzweig von oben
            mx = 193
            d.line([(mx, 14), (mx, 34)], fill=(200, 40, 50), width=2)
            for j, (dx, dy) in enumerate(((-6, 38), (5, 37), (0, 42), (-3, 46), (4, 45))):
                self._blob(img, mx + dx, dy, 9, 5, (40, 130, 60), ang=dx * 8, gloss=0.3)
            for dx, dy in ((-1, 40), (2, 41), (0, 44)):
                d.ellipse([mx + dx - 1.5, dy - 1.5, mx + dx + 1.5, dy + 1.5], fill=(250, 250, 240))
        if P.get("hearts") is not None:
            k = P["hearts"]
            for j in range(3):
                kk = (k * 0.5 + j / 3) % 1.0
                self._xmas_party_heart(d, XMAS_TREE_X + 30 + j * 6, floor - 70 - kk * 40, 3 + kk * 2)
        star = P.get("star")
        if isinstance(star, tuple) and "santa" in heads:            # Stern fällt
            k = min(1.0, star[1])
            sx0, sy0 = self.__dict__.get("_xmas_star_pos", (XMAS_TREE_X, 60))
            hx, hy = heads["santa"]
            self._xmas_party_star(d, sx0 + (hx - sx0) * k, sy0 + (hy - 30 - sy0) * k * k, k * 400)
        elif star == "head" and "santa" in heads and visible["santa"]:
            hx, hy = heads["santa"]
            self._xmas_party_star(d, hx + 2, hy - 30, 0)
        for who in P.get("notes", ()):                              # schiefe Noten
            if who in heads and visible[who]:
                hx, hy = heads[who]
                font = self.__dict__.setdefault("_party_note_font", load_font(12, bold=True))
                cols = [(255, 120, 120), (255, 220, 90), (120, 200, 255)]
                for j in range(3):
                    k = (t * 0.7 + j / 3) % 1.0
                    d.text((hx + 8 + k * 16 + math.sin(t * 5 + j) * 4, hy - 10 - k * 34),
                           "♪♫♬"[j], font=font, fill=cols[j])
        if P.get("cat"):
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
                x, y = (acts["santa"]["x"] + acts["mrs"]["x"]) / 2, floor - 140
            elif who == "tree":
                x, y = XMAS_TREE_X + 6, floor - 64
            elif who == "elf":
                if not P.get("elf"):
                    continue
                x, y = P["elf"][0], floor - 52
            elif who == "lie":
                x, y = P.get("lie_x", 196) - 34, floor - 40
            elif who == "window":
                x, y = 276, 62
            elif who == "line":
                x, y = max(40, min(WIDTH - 40, P.get("line", 160) - 92)), floor - 140
            else:
                if not visible[who] or who not in heads:
                    continue
                x, y = heads[who][0], heads[who][1] - 34
            self._xmas_party_say(d, x, y, text)

    def _xmas_party_after(self, img, P):
        """Ganz zuletzt: Blitzlicht des Handys, Licht aus (Pupswolke)."""
        if P.get("flash"):
            img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.65 * P["flash"])
        return img

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

    @staticmethod
    def _xmas_party_star(d, x, y, rot):
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5 + math.radians(rot)
            rr = 8 if k % 2 == 0 else 3.5
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        d.polygon(pts, fill=(255, 220, 70), outline=(200, 150, 30))

    @staticmethod
    def _xmas_party_heart(d, x, y, r):
        d.ellipse([x - r, y - r, x, y], fill=(255, 80, 120))
        d.ellipse([x, y - r, x + r, y], fill=(255, 80, 120))
        d.polygon([(x - r, y - r / 2), (x + r, y - r / 2), (x, y + r)], fill=(255, 80, 120))

    def _xmas_party_elf(self, img, d, elf, floor, t):
        """Wichtel: grünes Gewand, Zipfelmütze, spitze Ohren; schaut, schreibt auf seine Liste."""
        x, face, mode, lt = elf
        if mode == "hit":                                           # getroffen: sitzt im Schnee, Sternchen
            floor += 8
            for j in range(3):
                a = t * 4 + j * 2.1
                d.text((x - 3 + math.cos(a) * 10, floor - 48 + math.sin(a) * 3), "*", fill=(255, 230, 90))
        step = math.sin(t * 12) * 3 if mode in ("walk", "carry") else 0
        green, skin = (40, 150, 70), (246, 206, 176)
        for side in (-1, 1):
            d.line([(x + side * 3, floor - 12), (x + side * 3 + step * side, floor - 1)], fill=(40, 90, 50), width=3)
            self._blob(img, x + side * 3 + step * side + face * 2, floor, 8, 4, (180, 30, 36), gloss=0.7)
        self._blob(img, x, floor - 18, 16, 16, green, gloss=0.3)
        hy = floor - 32
        shake = math.sin(t * 10) * 3 if mode == "look" else 0
        self._blob(img, x + shake, hy, 13, 12, skin, gloss=0.3)
        for side in (-1, 1):
            d.polygon([(x + shake + side * 6, hy - 1), (x + shake + side * 11, hy - 5), (x + shake + side * 6, hy + 3)],
                      fill=skin)
        d.polygon([(x + shake - 7, hy - 4), (x + shake + 7, hy - 4), (x + shake - face * 10, hy - 18)], fill=green)
        self._blob(img, x + shake - face * 10, hy - 18, 5, 5, (230, 40, 50), gloss=0.4)
        d.ellipse([x + shake + face * 2 - 1, hy - 1, x + shake + face * 2 + 1, hy + 1], fill=(20, 20, 24))
        if mode == "carry":                                          # trägt den Stiefel
            self._blob(img, x + face * 9, floor - 20, 16, 10, (34, 26, 24), gloss=0.9)
        if mode == "write":                                          # Liste und Stift
            px = x + face * 10
            d.rectangle([px - 4, floor - 26, px + 4, floor - 12], fill=(248, 242, 222))
            for j in range(3):
                d.line([(px - 2, floor - 23 + j * 4), (px + 2, floor - 23 + j * 4)], fill=(150, 60, 60))
            d.line([(px + 3, floor - 20 + math.sin(t * 14) * 2), (px + 7, floor - 26)], fill=(60, 60, 70), width=1)

    def _xmas_party_cat(self, img, d, x, seat, t, k):
        """Grauer Kater (auf der Bank: Augen zu, Schwanz wedelt)."""
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

    # -- Zusätze (8 Gags der dritten Runde, Wetter, Anzeige) ----------------- #
    def _xmas_party_extras(self, img, d, P, acts, floor, t, heads, hands, visible):
        """Schneeball, fliegende Mütze, Lichterkette um ihn, Geschenk/Socken/Tränen, Topf über dem Kopf, Schlitten,
        Polonaise, Regenschirm, Regen."""
        if P.get("ball"):
            src, dst, k = P["ball"]
            p0 = hands.get(src, [(160, 120)] * 2)[1 if src == "mrs" else 0] if src in hands else (160, 120)
            if dst == "elf":
                p1 = (70, floor - 32)
            else:
                p1 = heads.get(dst, (160, 90))
            x = p0[0] + (p1[0] - p0[0]) * k
            y = p0[1] + (p1[1] - p0[1]) * k - math.sin(k * math.pi) * 24
            self._blob(img, x, y, 8, 8, (248, 250, 255), gloss=0.4)
        fh = P.get("flyhat")
        if fh and "santa" in heads:
            mode, k = fh
            hx, hy = heads["santa"]
            if mode == "fall":                                      # Mütze fliegt nach links in den Schnee
                x, y = hx + (124 - hx) * k, hy - 14 + (floor - 4 - (hy - 14)) * k - math.sin(k * math.pi) * 30
            else:                                                   # Sturm: nach rechts davon
                x, y = hx + (WIDTH + 40 - hx) * k, hy - 14 - math.sin(k * math.pi) * 40
            self._xmas_party_hat(d, img, x, y, t * 3)
        wrapped = "wrapped" in P["props"]
        if (wrapped or P.get("wire") is not None) and "santa" in heads and visible["santa"]:
            hx, hy = heads["santa"]
            k = 1.0 if P.get("wire") is None else P["wire"]
            for j in range(int(3 * k + 0.999)):                    # Kabel in Schlingen um den Bauch
                cy = hy + 30 + j * 12
                d.arc([hx - 26, cy - 6, hx + 26, cy + 6], 0, 180, fill=(30, 80, 40), width=2)
                for i in range(5):
                    a = math.pi * (i + 0.5) / 5
                    bx, by = hx + math.cos(a) * 26, cy + math.sin(a) * 6
                    c = XMAS_LIGHT_COLORS[(i + j + P["beats"]) % len(XMAS_LIGHT_COLORS)]
                    if wrapped:
                        self._blob(img, bx, by, 8, 8, c, alpha=0.5, flat=True)
                    d.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=c)
        gift = P.get("gift")
        if gift and "santa" in hands:
            (x1, y1), (x2, y2) = hands["santa"]
            gx, gy = (x1 + x2) / 2, (y1 + y2) / 2
            if gift[0] == "box":
                sh = math.sin(t * 22) * 3 if gift[1] else 0
                d.rectangle([gx - 9 + sh, gy - 14, gx + 9 + sh, gy + 2], fill=(60, 120, 220))
                d.rectangle([gx - 1 + sh, gy - 14, gx + 1 + sh, gy + 2], fill=(250, 220, 70))
                d.rectangle([gx - 9 + sh, gy - 7, gx + 9 + sh, gy - 5], fill=(250, 220, 70))
            else:                                                   # Socken
                for side in (-1, 1):
                    sx = gx + side * 7
                    d.rectangle([sx - 3, gy - 2, sx + 3, gy + 12], fill=(120, 170, 90))
                    d.rectangle([min(sx - 3, sx + 7 * side), gy + 9, max(sx + 3, sx + 7 * side), gy + 14],
                                fill=(120, 170, 90))
                    for k in range(3):
                        d.line([(sx - 3, gy + 1 + k * 4), (sx + 3, gy + 1 + k * 4)], fill=(230, 80, 80))
        if P.get("tears") is not None and "santa" in heads:
            hx, hy = heads["santa"]
            for side in (-1, 1):
                for j in range(2):
                    k = (P["tears"] * 1.4 + j * 0.5) % 1.0
                    d.ellipse([hx + side * 6 - 1.5, hy - 2 + k * 18 - 2, hx + side * 6 + 1.5, hy - 2 + k * 18 + 2],
                              fill=(120, 180, 255))
        if P.get("pot_head") == "up" and "santa" in hands:          # Topf über dem Kopf, letzte Tropfen
            (x1, y1), (x2, y2) = hands["santa"]
            px, py = (x1 + x2) / 2, min(y1, y2) - 6
            d.polygon([(px - 14, py - 10), (px + 12, py - 16), (px + 14, py + 6), (px - 12, py + 12)], fill=(40, 36, 44))
            for j in range(3):
                k = (t * 2 + j / 3) % 1.0
                d.ellipse([px - 2, py + 12 + k * 14, px + 1, py + 15 + k * 14], fill=(170, 30, 46))
        if P.get("sleigh"):
            sx, inside = P["sleigh"]
            if sx is None:
                sx = acts["santa"]["x"]
            self._xmas_party_sleigh(img, d, sx, floor, t, inside)
        if P.get("line") is not None:                               # Polonaise: Wichtel, Rentier, Katze vorneweg
            lead = P["line"]
            self._xmas_party_elf(img, d, (lead, 1, "walk", 0.0), floor, t)
            self._xmas_party_deer(img, d, (lead - 34, 1, "walk", 0.0), floor, t, P["beats"])
            self._xmas_party_cat(img, d, lead - 62, floor + 6, t * 3, 1.0)
        if P.get("umbrella") and "mrs" in hands and visible["mrs"] and acts["mrs"]["state"] in ("dance", "walk"):
            hx, hy = hands["mrs"][1]
            top = hy - 34
            d.line([(hx, hy), (hx, top)], fill=(80, 70, 70), width=2)
            d.pieslice([hx - 24, top - 14, hx + 24, top + 14], 180, 360, fill=(70, 120, 210))
            for j in range(4):
                d.line([(hx, top), (hx - 24 + j * 16, top)], fill=(40, 80, 160), width=1)
        if P.get("rain"):                                           # Regen statt Schnee
            for j in range(60):
                x = (j * 53 + t * 140) % (WIDTH + 40) - 20
                y = (j * 97 + t * 380) % VIS_H
                d.line([(x, y), (x - 3, y + 9)], fill=(150, 170, 210), width=1)

    def _xmas_party_house(self, img, d, window, t):
        """Kleines Haus auf dem Hügel rechts; bei „Nachbar“ geht ein Fenster auf."""
        x0, y0, w, h = 262, 86, 46, 32
        d.rectangle([x0, y0, x0 + w, y0 + h], fill=(46, 50, 70))
        d.polygon([(x0 - 6, y0 + 1), (x0 + w / 2, y0 - 20), (x0 + w + 6, y0 + 1)], fill=(36, 38, 54))
        d.line([(x0 - 6, y0 + 1), (x0 + w / 2, y0 - 20), (x0 + w + 6, y0 + 1)], fill=(230, 236, 250), width=2)
        for i, wx in enumerate((x0 + 7, x0 + 28)):
            lit = window is not None and i == 1
            d.rectangle([wx, y0 + 9, wx + 11, y0 + 22], fill=(250, 220, 120) if lit else (70, 64, 50))
            if lit:
                op = min(1.0, window / 0.5)                          # Fensterläden klappen auf
                d.rectangle([wx - 5 * op, y0 + 9, wx, y0 + 22], fill=(90, 60, 40))
                d.rectangle([wx + 11, y0 + 9, wx + 11 + 5 * op, y0 + 22], fill=(90, 60, 40))
                if _win(window, 0.5, 4.6):                          # Nachbar mit Schlafmütze
                    self._blob(img, wx + 5.5, y0 + 18, 9, 9, (240, 210, 180), gloss=0.2)
                    d.polygon([(wx + 1, y0 + 15), (wx + 10, y0 + 15), (wx + 14, y0 + 8)], fill=(60, 120, 200))

    def _xmas_party_lying(self, img, d, x, floor, t, k, P):
        """Er liegt im Schnee (Schneeengel): Kopf links, Arme und Beine wedeln."""
        flap = math.sin(k * 7) * 0.5 + 0.5 if k < 3.0 else 0.0
        y = floor - 8
        for side in (-1, 1):                                        # Beine nach rechts
            ang = side * (0.15 + 0.35 * flap)
            fx, fy = x + 22 + math.cos(ang) * 26, y + math.sin(ang) * 18
            self._limb(img, (x + 18, y + side * 4), (fx, fy), 13, XMAS_RED)
            self._blob(img, fx + 4, fy, 11, 18, (34, 26, 24), gloss=0.9)
        for side in (-1, 1):                                        # Arme
            ang = side * (1.2 + 0.9 * flap)
            hx, hy = x - 14 + math.cos(ang + math.pi) * -18, y + math.sin(ang) * 22
            self._limb(img, (x - 12, y + side * 6), (hx, hy), 11, XMAS_RED)
            self._blob(img, hx, hy, 10, 10, (240, 240, 244), gloss=0.3)
        self._blob(img, x, y, 50, 34, XMAS_RED, gloss=0.4)          # Bauch
        self._blob(img, x + 4, y, 9, 30, (30, 24, 22), gloss=0.7)   # Gürtel
        self._blob(img, x + 4, y, 10, 11, (240, 196, 60), gloss=1.2)
        skin = _lerp(XMAS_SKIN, PARTY_GREEN, P.get("green", 0.0))
        self._blob(img, x - 32, y, 26, 26, skin, gloss=0.3)          # Kopf
        self._blob(img, x - 26, y - 10, 24, 18, XMAS_FUR, gloss=0.15)  # Bart nach oben
        d.ellipse([x - 38, y - 3, x - 35, y + 0], fill=(30, 30, 40))
        d.ellipse([x - 38, y + 3, x - 35, y + 6], fill=(30, 30, 40))
        self._blob(img, x - 31, y + 1, 6, 6, (232, 90, 90), gloss=0.8)
        tip = (x - 64, y + math.sin(t * 2) * 4)                     # Mütze liegt am Kopf
        d.polygon([(x - 44, y - 12), (x - 44, y + 12), tip], fill=XMAS_RED)
        self._blob(img, x - 44, y, 8, 26, XMAS_FUR, gloss=0.1)
        self._blob(img, tip[0], tip[1], 9, 9, XMAS_FUR, gloss=0.2)

    def _xmas_party_sleigh(self, img, d, x, floor, t, inside):
        """Schlitten mit Rentier davor (fährt nach rechts); inside = er sitzt drin, nur Kopf und Mütze sichtbar."""
        self._xmas_party_deer(img, d, (x + 50, 1, "walk", 0.0), floor, t, 0)
        d.line([(x + 22, floor - 22), (x + 36, floor - 26)], fill=(110, 76, 44), width=2)   # Zugleine
        if inside:                                                  # Kopf schaut heraus, schläft
            hy = floor - 40
            self._blob(img, x, hy, 24, 24, XMAS_SKIN, gloss=0.3)
            self._blob(img, x, hy + 9, 28, 20, XMAS_FUR, gloss=0.15)
            d.polygon([(x - 12, hy - 8), (x + 12, hy - 8), (x - 26, hy - 18)], fill=XMAS_RED)
            self._blob(img, x, hy - 8, 28, 8, XMAS_FUR, gloss=0.1)
            d.text((x + 12, hy - 22), "z", fill=(220, 220, 240))
        d.polygon([(x - 26, floor - 30), (x + 22, floor - 30), (x + 26, floor - 10), (x - 22, floor - 10)],
                  fill=(190, 24, 32))
        d.line([(x - 26, floor - 30), (x + 22, floor - 30)], fill=(240, 200, 70), width=2)
        d.line([(x - 28, floor - 2), (x + 28, floor - 2)], fill=(200, 170, 70), width=2)       # Kufen
        d.arc([x + 20, floor - 10, x + 34, floor + 2], 270, 90, fill=(200, 170, 70), width=2)
        for lx in (x - 16, x + 14):
            d.line([(lx, floor - 10), (lx, floor - 2)], fill=(200, 170, 70), width=2)

    def _xmas_party_meter(self, img, d, P):
        """Glühwein-Barometer (Pegel) mit Becherzähler am rechten Rand."""
        x, y0, y1 = WIDTH - 11, 20, 50
        d.rounded_rectangle([x - 4, y0, x + 4, y1], radius=4, fill=(30, 34, 46), outline=(150, 160, 190))
        lvl = max(0.0, min(1.0, P["pegel"]))
        if lvl > 0.01:
            d.rounded_rectangle([x - 2, y1 - 2 - (y1 - y0 - 4) * lvl, x + 2, y1 - 2], radius=2, fill=(220, 40, 60))
        d.ellipse([x - 7, y1 - 2, x + 7, y1 + 12], fill=(220, 40, 60), outline=(150, 160, 190))
        font = self.__dict__.setdefault("_party_meter_font", load_font(9, bold=True))
        text = f"{P['mugs_today']}×"
        w = d.textlength(text, font=font)
        d.text((x - w / 2, y1 + 13), text, font=font, fill=(235, 220, 200))
        d.rectangle([x - 4, y1 + 25, x + 2, y1 + 31], fill=(178, 30, 42))                   # Becher
        d.arc([x + 1, y1 + 26, x + 5, y1 + 30], 270, 90, fill=(235, 235, 240))
