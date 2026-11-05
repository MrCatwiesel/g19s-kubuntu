"""Displaytaste SETTINGS: kurz auf der Uhrseite = Zifferblätter, lang (ab LONG_PRESS, schon während des
Haltens) = Profilauswahl, kurz auf anderen Seiten = Profilauswahl; SETTINGS schließt ein offenes Menü."""
import json
import time
from harness import Sim
s = Sim("s21_settings_kurz_lang", macros={"profiles": [{"name": "Büro", "keys": {}}, {"name": "Spiele", "keys": {}}]},
        settings={"pages": ["clock", "hardware"], "start_page": 0, "notifications": {"enabled": False}})
g = s.g
shown = []                                   # (Zeit, Menü) – welches Menü das Display zeigt


def spy(name, kind):
    orig = getattr(g.Renderer, name)

    def wrapped(r, *a, **k):
        shown.append((time.monotonic() - s.t0, kind))
        return orig(r, *a, **k)
    setattr(g.Renderer, name, wrapped)


spy("render_profile_menu", "profile")
spy("render_face_preview", "clocks")
s.key(1.0, "SETTINGS"); s.key(1.6, "DOWN"); s.key(2.0, "OK")                 # kurz auf der Uhr: Zifferblatt wählen
s.key(3.0, "SETTINGS", hold=1.6)                                             # lang: Profilauswahl, noch gehalten
s.key(4.9, "DOWN"); s.key(5.3, "OK")                                         # → Profil „Spiele“
s.key(6.0, "RIGHT"); s.key(6.6, "SETTINGS"); s.key(7.2, "BACK")              # Hardware-Seite: kurz = Profilauswahl
s.key(7.8, "LEFT"); s.key(8.4, "SETTINGS"); s.key(9.0, "SETTINGS")           # Uhr: Zifferblätter, SETTINGS schließt
s.run(10.5)
s.save({"zifferblaetter": 1.4, "lang_gehalten": 4.3, "hardware_profil": 7.0})


def at(t0, t1):
    """Menüs, die zwischen t0 und t1 gezeigt wurden (ohne Wiederholungen)."""
    out = []
    for t, k in shown:
        if t0 <= t < t1 and (not out or out[-1] != k):
            out.append(k)
    return out


m = json.load(open(g.MACRO_FILE))
s.finish(kurz_uhr=at(1.0, 2.0), lang_vor_schwelle=at(3.0, 3.9), lang_gehalten=at(3.9, 4.6),
         nach_ok=at(5.5, 6.0), kurz_hardware=at(6.6, 7.2), kurz_uhr_zu=at(8.4, 9.0), nach_zu=at(9.3, 10.5),
         faces=[p.get("clock") for p in m["profiles"]], log=s.log_lines(r"^(Uhr|Profil)"))
