"""Kleine Hilfsfunktionen ohne eigenes Thema."""


def domain_of(url):
    return re.sub(r"^[a-z]+://(www\.)?", "", str(url), flags=re.I).split("/")[0]


def xmas_season(day=None):
    """Weihnachtszeit (1. Advent bis 6. Januar)? Liefert das Jahr des Advents oder None."""
    import datetime as _dt
    day = day or _dt.date.today()
    if day.month == 1 and day.day <= 6:
        return day.year - 1
    xmas = _dt.date(day.year, 12, 25)
    advent1 = xmas - _dt.timedelta(days=(xmas.weekday() + 1) % 7 or 7) - _dt.timedelta(weeks=3)
    return day.year if day >= advent1 else None


def visual_fps(base, draw_ms=None, quiet=False):
    """Anpassende Bildrate: bei Stille oder Wortbeiträgen höchstens VISUAL_FPS_QUIET; braucht das Zeichnen mehr als
    VISUAL_LOAD_SHARE der Bildzeit, so weit herunter, dass es passt (nicht unter VISUAL_FPS_MIN)."""
    fps = max(1, int(base))
    if quiet:
        fps = min(fps, VISUAL_FPS_QUIET)
    if draw_ms and draw_ms > VISUAL_LOAD_SHARE * 1000.0 / fps:
        fps = max(min(fps, VISUAL_FPS_MIN), int(VISUAL_LOAD_SHARE * 1000.0 / draw_ms))
    return fps


def own_rss_mb():
    """Arbeitsspeicher des eigenen Prozesses (MB) oder None."""
    try:
        with open("/proc/self/statm") as f:
            return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576
    except (OSError, ValueError, IndexError):
        return None


def fest_today():
    """Heutiges Datum für den Festkalender (in Tests ersetzbar)."""
    import datetime as _dt
    return _dt.date.today()


def fest_now():
    """Aktuelle Uhrzeit für Countdown-Anzeigen (in Tests ersetzbar)."""
    import datetime as _dt
    return _dt.datetime.now()


def oktoberfest_days(year):
    """Oktoberfest: vom Samstag nach dem 15. September bis zum ersten Sonntag im Oktober (mindestens bis 3.10.)."""
    import datetime as _dt
    start = _dt.date(year, 9, 16)
    start += _dt.timedelta(days=(5 - start.weekday()) % 7)
    end = _dt.date(year, 10, 1)
    end += _dt.timedelta(days=(6 - end.weekday()) % 7)
    return start, max(end, _dt.date(year, 10, 3))


def birthdays_today(birthdays, day=None):
    """Wer hat heute Geburtstag? Liste von (Name, Alter oder None). Am 29.2. Geborene feiern in Nicht-Schaltjahren
    am 28.2."""
    import calendar
    day = day or fest_today()
    out = []
    for b in birthdays if isinstance(birthdays, list) else []:
        if not isinstance(b, dict) or not str(b.get("name") or "").strip():
            continue
        try:
            bd, bm, by = int(b.get("day") or 0), int(b.get("month") or 0), int(b.get("year") or 0)
        except (TypeError, ValueError):
            continue
        if bm == 2 and bd == 29 and not calendar.isleap(day.year):
            bd = 28
        if (bd, bm) == (day.day, day.month):
            age = day.year - by if 1900 <= by <= day.year else None
            out.append((str(b["name"]).strip(), age))
    return out


def fest_occasion(vis, day=None):
    """Festkalender der Visualisierung: (Stil, Anlass) für heute oder None. Geburtstag (Liste der Überraschungsparty)
    vor Freitag, dem 13. (Kellertreppe, nur wenn eingeschaltet). Der Anlass (z. B. "geb:2026-11-16") merkt sich,
    ob der Nutzer an diesem Tag am Display einen anderen Stil gewählt hat (visual.fest_skip)."""
    vis = vis if isinstance(vis, dict) else {}
    day = day or fest_today()
    party = vis.get("party") if isinstance(vis.get("party"), dict) else {}
    if party.get("auto", True) and birthdays_today(party.get("birthdays"), day):
        bday = vis.get("birthday") if isinstance(vis.get("birthday"), dict) else {}
        style = "birthday" if bday.get("auto") and "birthday" in VISUAL_STYLES else "party"
        return style, f"geb:{day.isoformat()}"
    cellar = vis.get("cellar") if isinstance(vis.get("cellar"), dict) else {}
    if cellar.get("fri13") and day.day == 13 and day.weekday() == 4:
        return "cellar", f"f13:{day.isoformat()}"
    if vis.get("fest_auto", True):
        for style, key in fest_days(day):
            if style in VISUAL_STYLES:                  # Stil schon gebaut? (Festtage für spätere Stile vorgemerkt)
                return style, key
    return None


def easter_sunday(year):
    """Ostersonntag (gregorianisch, Algorithmus nach Gauß/Meeus)."""
    import datetime as _dt
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return _dt.date(year, month, day + 1)


def fest_days(day):
    """Festtage des Kalenders an diesem Tag: [(Stil, Anlass)] – Fasching (Weiberfastnacht bis Faschingsdienstag),
    Valentinstag (14.2.), Ostern (Gründonnerstag bis Ostermontag), Männertag (Christi Himmelfahrt), Muttertag
    (2. Sonntag im Mai), Oktoberfest, Halloween (25.10.–1.11.), St. Martin (11.11.), Silvester (31.12.).
    Mehrtägige Anlässe haben einen Schlüssel je Jahr (eine Abwahl am Display gilt für den ganzen Zeitraum)."""
    import datetime as _dt
    out = []
    easter = easter_sunday(day.year)
    if easter - _dt.timedelta(days=52) <= day <= easter - _dt.timedelta(days=47):
        out.append(("carnival", f"fasching:{day.year}"))
    if day.month == 2 and day.day == 14:
        out.append(("valentine", f"valentin:{day.year}"))
    if easter - _dt.timedelta(days=3) <= day <= easter + _dt.timedelta(days=1):
        out.append(("easter", f"ostern:{day.year}"))
    if day == easter + _dt.timedelta(days=39):
        out.append(("father", f"maenner:{day.isoformat()}"))
    if (day.month == 10 and day.day >= 25) or (day.month == 11 and day.day == 1):
        out.append(("halloween", f"halloween:{day.year}"))
    if day.month == 5 and day.weekday() == 6 and 8 <= day.day <= 14:
        out.append(("mother", f"mutter:{day.isoformat()}"))
    wiesn = oktoberfest_days(day.year)
    if wiesn[0] <= day <= wiesn[1]:
        out.append(("oktoberfest", f"wiesn:{day.year}"))
    if day.month == 11 and day.day == 11:
        out.append(("martin", f"martin:{day.year}"))
    if day.month == 12 and day.day == 31:
        out.append(("newyear", f"silvester:{day.year}"))
    return out


def in_time_window(now_hm, start, end):
    """Liegt die Uhrzeit (HH:MM) im Zeitraum? Funktioniert auch über Mitternacht."""
    def mins(s):
        h, m = str(s).split(":")
        return int(h) * 60 + int(m)
    try:
        n, a, b = mins(now_hm), mins(start), mins(end)
    except (ValueError, AttributeError):
        return False
    if a == b:
        return False
    return a <= n < b if a < b else (n >= a or n < b)
