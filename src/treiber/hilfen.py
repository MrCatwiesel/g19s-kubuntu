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
