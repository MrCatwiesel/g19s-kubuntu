"""Kleine Hilfsfunktionen ohne eigenes Thema."""


def domain_of(url):
    return re.sub(r"^[a-z]+://(www\.)?", "", str(url)).split("/")[0]


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
