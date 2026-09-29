#!/usr/bin/env python3
"""Zifferblätter der Uhr als Bild ansehen (zum Entwickeln neuer Zifferblätter).

    python3 tests/uhren_vorschau.py pendulum cuckoo --out /tmp/x.png
    python3 tests/uhren_vorschau.py astro --zeiten "2026-12-21 08:05:12,2026-06-21 21:47:03"
    python3 tests/uhren_vorschau.py binary --opt '{"binary": {"mode": "binary"}}' --ebene M3 --gross

Baut den Treiber aus src/treiber in eine temporäre Datei (dist/ bleibt unberührt),
zeichnet jedes Zifferblatt zu jeder Zeit (Europe/Berlin) und legt die Bilder als
Raster ab: Zeilen = Zifferblätter, Spalten = Zeiten. Gibt die Zeichenzeit je Bild aus.
--frames N --dt 0.2  zeichnet zusätzlich N Bilder im Abstand dt Sekunden (Animation prüfen).
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, PROJ)
sys.path.insert(0, os.path.join(HERE, "stubs"))
os.environ["TZ"] = "Europe/Berlin"
time.tzset()

ap = argparse.ArgumentParser()
ap.add_argument("faces", nargs="+")
ap.add_argument("--zeiten", default="2026-10-01 09:30:00,2026-12-24 18:47:23,2026-06-21 03:12:48")
ap.add_argument("--ebene", default="M1")
ap.add_argument("--opt", default="{}", help="JSON für settings['clock'], z. B. '{\"binary\": {\"digits\": false}}'")
ap.add_argument("--settings", default="{}", help="JSON, das in die Einstellungen gemischt wird (z. B. weather)")
ap.add_argument("--frames", type=int, default=1)
ap.add_argument("--dt", type=float, default=0.2)
ap.add_argument("--gross", action="store_true", help="doppelte Größe")
ap.add_argument("--out", default=None)
a = ap.parse_args()

import build  # noqa: E402

text, _ = build.bundle(os.path.join("src", "treiber"), "kopf")
build.check("g19s.py", text)
fd, path = tempfile.mkstemp(suffix="_g19s.py")
os.write(fd, text.encode())
os.close(fd)
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp())
spec = importlib.util.spec_from_file_location("g19s_vorschau", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
from PIL import Image  # noqa: E402

settings = g.load_settings("/nonexistent")
extra = json.loads(a.settings)
for k, v in extra.items():
    settings[k] = dict(settings.get(k) or {}, **v) if isinstance(v, dict) and isinstance(settings.get(k), dict) else v
for face, o in json.loads(a.opt).items():
    settings["clock"].setdefault(face, {}).update(o)
r = g.Renderer()
r.settings = settings
r.profile_name = "Vorschau"
r.visible = list(range(len(g.PAGE_IDS)))
times = [dt.datetime.strptime(z.strip(), "%Y-%m-%d %H:%M:%S").timestamp() for z in a.zeiten.split(",")]
cols = [t + k * a.dt for t in times for k in range(a.frames)]
scale = 2 if a.gross else 1
W, H = 320 * scale, 240 * scale
sheet = Image.new("RGB", (len(cols) * (W + 6) + 6, len(a.faces) * (H + 6) + 6), (70, 70, 70))
for row, face in enumerate(a.faces):
    if face not in g.CLOCK_RENDERERS:
        print(f"{face}: nicht angemeldet (vorhanden: {', '.join(g.CLOCK_RENDERERS)})")
        continue
    r.clock_face = face
    for col, t in enumerate(cols):
        r.fixed_time = t
        t0 = time.perf_counter()
        img = r.render(0, a.ebene, {})
        ms = (time.perf_counter() - t0) * 1000
        print(f"{face:10s} {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))}  {ms:6.1f} ms"
              f"  (fps {g.clock_fps(face, settings)})")
        if scale > 1:
            img = img.resize((W, H), Image.LANCZOS)
        sheet.paste(img, (6 + col * (W + 6), 6 + row * (H + 6)))
out = a.out or os.path.join(tempfile.gettempdir(), "uhren_vorschau.png")
sheet.save(out)
os.remove(path)
print("Bild:", out)
