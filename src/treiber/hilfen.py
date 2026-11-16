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
        return "party", f"geb:{day.isoformat()}"
    cellar = vis.get("cellar") if isinstance(vis.get("cellar"), dict) else {}
    if cellar.get("fri13") and day.day == 13 and day.weekday() == 4:
        return "cellar", f"f13:{day.isoformat()}"
    return None


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
