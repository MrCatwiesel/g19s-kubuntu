"""Bedienung am Display: Haltebalken bei SETTINGS, Optionen eines Zifferblatts (Zifferblatt-Liste, ►),
Schnellmenü per MENU auf Seiten ohne eigenes MENU, Einblendung der G-Tasten beim Ebenenwechsel, kleiner mpv-Puffer."""
import json
import time
from harness import Sim
s = Sim("s22_bedienung", macros={"profiles": [{"name": "Büro", "keys": {"M2": {"G1": {"text": "Hallo"}}}}]},
        settings={"start_page": 0, "notifications": {"enabled": False},
                  "night": {"enabled": False, "start": "22:30", "end": "22:30"},     # Zeitfenster leer: nie aktiv
                  "layer_pages": {"M1": ["clock", "hardware"], "M2": ["clock"], "M3": ["clock"]}})
g = s.g
shown = []                                   # (Zeit, was) – Menüs/Einblendungen, die das Display zeigt


def spy(name, kind):
    orig = getattr(g.Renderer, name)

    def wrapped(r, *a, **k):
        shown.append((time.monotonic() - s.t0, kind))
        return orig(r, *a, **k)
    setattr(g.Renderer, name, wrapped)


for n, k in (("render_hold_bar", "halten"), ("render_face_preview", "zifferblaetter"),
             ("render_option_overlay", "optionen"), ("render_profile_menu", "profil"),
             ("render_layer_keys", "ebene")):
    spy(n, k)
orig_list = g.Renderer.render_list_menu


def list_spy(r, title, *a, **k):
    shown.append((time.monotonic() - s.t0, title))
    return orig_list(r, title, *a, **k)


g.Renderer.render_list_menu = list_spy
# SETTINGS 0,6 s gehalten: Balken erscheint, beim Loslassen (kurz) die Zifferblätter
s.key(1.0, "SETTINGS", hold=0.6)
# ► Optionen der Digitaluhr: Sekunden aus, Farbe Weiß → Rot; BACK zur Liste, BACK schließt
s.key(2.0, "RIGHT"); s.key(2.5, "RIGHT"); s.key(3.0, "DOWN"); s.key(3.4, "DOWN"); s.key(3.8, "RIGHT"); s.key(4.2, "RIGHT")
s.key(4.8, "BACK"); s.key(5.2, "BACK")
# Hardware-Seite: MENU = Schnellmenü; Helligkeit 100 → 90, Nachtmodus an, Diashow pausieren, Bildschirmschoner
s.key(6.0, "RIGHT"); s.key(6.6, "MENU"); s.key(7.0, "LEFT"); s.key(7.4, "DOWN"); s.key(7.8, "OK")
s.key(8.2, "DOWN"); s.key(8.6, "OK"); s.key(9.2, "DOWN"); s.key(9.6, "OK")
# Taste beendet den Bildschirmschoner; Schnellmenü → Profil wählen → BACK
s.key(10.6, "DOWN"); s.key(11.5, "MENU"); s.key(11.9, "UP"); s.key(12.3, "OK"); s.key(12.7, "BACK")
# Ebene M2: Belegung der G-Tasten wird eingeblendet
s.gkey(13.2, "M2")
s.run(16)
s.save({"haltebalken": 1.45, "optionen": 4.5, "schnellmenue": 8.9, "ebene": 13.7})


def at(t0, t1):
    out = []
    for t, k in shown:
        if t0 <= t < t1 and (not out or out[-1] != k):
            out.append(k)
    return out


st = json.load(open(g.SETTINGS_FILE))
cmd, _ = g.RadioManager._build_cmd(None, "mpv --no-video {url}", "http://127.0.0.1:9/x", [])
own, _ = g.RadioManager._build_cmd(None, "mpv --cache=no {url}", "http://127.0.0.1:9/x", [])
vlc, _ = g.RadioManager._build_cmd(None, "cvlc {url}", "http://127.0.0.1:9/x", [])
s.finish(halten=at(1.0, 2.0), optionen=at(2.2, 4.8), zurueck=at(4.9, 5.2), schnell=at(6.7, 9.6),
         schoner=[p for p, _ in s.page_seq()], profil=at(12.3, 12.7), ebene=at(13.2, 15.0), nach_ebene=at(15.5, 16),
         uhr=st.get("clock"), helligkeit=st.get("brightness"), nacht=st["night"]["enabled"],
         mpv=cmd, mpv_eigen=own, vlc=vlc,
         log=s.log_lines(r"^(Uhr-Option|Helligkeit|Nachtmodus \(|Diashow:|Bildschirmschoner)"))
