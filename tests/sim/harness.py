"""Gemeinsames Gerüst für die Treiber-Simulationen.

Eine Simulation startet den echten Treiber (dist/g19s.py) mit einer
nachgebauten Tastatur. Zu festen Zeitpunkten werden G-/M-Tasten und
Displaytasten „gedrückt“. Aufgezeichnet werden Displaybilder, Beleuchtung,
getippte Tasten, Protokollzeilen und gestartete Programme.

Jede Simulation liefert am Ende eine Zusammenfassung ohne Zeitstempel.
tests/run_tests.py vergleicht sie mit tests/sim/erwartet/NAME.json –
so fällt jede Verhaltensänderung durch ein Refactoring auf.
"""
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import types

ROOT = os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DRIVER = os.environ.get("G19S_DRIVER", os.path.join(PROJ, "dist", "g19s.py"))

# Displaytasten und G-/M-Tasten (Report 0x02: Byte 1 = G1–G8, Byte 2 = G9–G12 + M-Tasten)
L = {"SETTINGS": 0x01, "BACK": 0x02, "MENU": 0x04, "OK": 0x08, "RIGHT": 0x10, "LEFT": 0x20, "DOWN": 0x40, "UP": 0x80}
GK = {f"G{i + 1}": 1 << i for i in range(12)}
GK.update({"M1": 0x1000, "M2": 0x2000, "M3": 0x4000, "MR": 0x8000})


class Tee(io.TextIOBase):
    """Fängt die Ausgabe ab. Zeilen werden je Thread gesammelt: print() schreibt Text und Zeilenende
    getrennt, sonst könnten Ausgaben zweier Threads in einer Zeile landen."""
    def __init__(self, lines):
        self.lines, self.local, self.lock = lines, threading.local(), threading.Lock()

    def write(self, s):
        sys.__stdout__.write(s)
        buf = getattr(self.local, "buf", "") + s
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            with self.lock:
                self.lines.append(line)
        self.local.buf = buf
        return len(s)

    def flush(self):
        sys.__stdout__.flush()


class Sim:
    def __init__(self, name, macros=None, settings=None, files=None):
        self.name = name
        self.home = os.path.join(ROOT, "sim", name)
        shutil.rmtree(self.home, ignore_errors=True)
        for d in (".config/g19s", "run", "cache"):
            os.makedirs(os.path.join(self.home, d))
        os.environ.update(XDG_CONFIG_HOME=self.home + "/.config", XDG_CACHE_HOME=self.home + "/cache",
                          XDG_RUNTIME_DIR=self.home + "/run", HOME=self.home)
        os.environ["PATH"] = os.path.join(ROOT, "bin") + ":" + os.environ["PATH"]
        spec = importlib.util.spec_from_file_location("g19s", DRIVER)
        self.g = g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g)
        if macros is not None:
            json.dump(macros, open(g.MACRO_FILE, "w"))
        if settings is not None:
            json.dump(settings, open(g.SETTINGS_FILE, "w"))
        for rel, content in (files or {}).items():
            path = os.path.join(self.home, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if isinstance(content, bytes):
                open(path, "wb").write(content)
            else:
                open(path, "w").write(content if isinstance(content, str) else json.dumps(content))
        self.script = []           # (t, "l"|"g"|"call", Wert)
        self.frames, self.backlight, self.leds, self.brightness = [], [], [], []
        self.log, self.opened, self.sounds, self.pages = [], [], [], []
        self.summary = {}

    # ---- Ablauf festlegen ----
    def key(self, t, name, hold=0.15):
        self.script += [(t, "l", L[name]), (t + hold, "l", 0)]

    def gkey(self, t, name, hold=0.15):
        self.script += [(t, "g", GK[name]), (t + hold, "g", 0)]

    def call(self, t, fn):
        self.script.append((t, "call", fn))

    # ---- Ausführen ----
    def run(self, seconds, patch_launcher=True, patch_sound=True, spy_pages=True):
        g, sim = self.g, self
        self.script.sort(key=lambda x: x[0])

        class FakeG19:
            def __init__(self):
                self.t0 = time.monotonic()
                self.i = 0
                sim.t0 = self.t0

            lock = threading.Lock()

            def read(self, ep, size, timeout_ms):
                """Wie das echte Gerät: blockiert bis ein Report für diesen Endpunkt fällig ist
                oder das Zeitlimit abläuft (wird ggf. aus zwei Lese-Threads gleichzeitig benutzt)."""
                end = time.monotonic() + timeout_ms / 1000
                while True:
                    with self.lock:
                        now = time.monotonic() - self.t0
                        while self.i < len(sim.script) and now >= sim.script[self.i][0]:
                            t, kind, val = sim.script[self.i]
                            if kind == "call":
                                self.i += 1
                                val(sim)
                                continue
                            if (kind == "g") != (ep == g.EP_GKEYS):
                                break
                            self.i += 1
                            if kind == "g":
                                return bytes([2, val & 0xFF, (val >> 8) & 0xFF, 0])
                            return bytes([val, 0x80])
                    if time.monotonic() >= end:
                        return None
                    time.sleep(0.005)

            def send_frame(self, img):
                sim.frames.append((time.monotonic() - self.t0, img))

            def set_backlight(self, r, gg, b):
                sim.backlight.append((time.monotonic() - self.t0, (r, gg, b)))

            def set_m_leds(self, m):
                sim.leds.append((time.monotonic() - self.t0, m))

            def set_brightness(self, v):
                sim.brightness.append((time.monotonic() - self.t0, v))

            def close(self):
                pass
        g.G19 = FakeG19
        g.ActivityWatcher._open_devices = lambda self: []
        if patch_sound:
            g.play_alarm = lambda env, repeat=2: sim.sounds.append(repeat) or True
        if patch_launcher:
            g.Launcher.start = lambda self, cmd: sim.opened.append(cmd) or True
        if spy_pages:
            orig = g.Renderer.render

            def spy(r, page, profile, *a, **k):
                sim.pages.append((time.monotonic() - sim.t0, g.PAGE_IDS[page % len(g.PAGE_IDS)], profile))
                return orig(r, page, profile, *a, **k)
            g.Renderer.render = spy
        threading.Thread(target=lambda: (time.sleep(seconds), os.kill(os.getpid(), 15)), daemon=True).start()
        old = sys.stdout
        sys.stdout = Tee(self.log)
        try:
            g.run(types.SimpleNamespace(debug=False, brightness=None, keep_backlight=False))
        finally:
            sys.stdout = old
        return self

    # ---- Auswertung ----
    def typed(self):
        import evdev
        return [k for k, v in evdev.SENT if v == 1]

    def page_seq(self):
        out = []
        for _, p, prof in self.pages:
            if not out or out[-1] != [p, prof]:
                out.append([p, prof])
        return out

    def seq(self, items):
        out = []
        for _, v in items:
            v = list(v) if isinstance(v, tuple) else v
            if not out or out[-1] != v:
                out.append(v)
        return out

    def log_lines(self, pattern=None, drop=(r"^Radio-Titel nicht abrufbar", r"^Bildschirmschoner:", r"^Makrodatei:")):
        out = []
        for line in self.log:
            if any(re.search(d, line) for d in drop):
                continue
            if pattern is None or re.search(pattern, line):
                line = re.sub(r"\d{4}-\d\d-\d\d[_ ]\d{2}:?\d{2}", "DATUM", line)
                out.append(re.sub(r"\b\d{1,2}:\d{2}\b", "hh:mm", line))
        return out

    def frame_at(self, t):
        return min((f for f in self.frames if f[0] <= t), key=lambda f: t - f[0])[1]

    def save(self, names):
        """Displaybilder zu bestimmten Zeitpunkten speichern (für die Sichtkontrolle)."""
        d = os.path.join(ROOT, "shots", "sim", self.name)
        os.makedirs(d, exist_ok=True)
        for n, t in names.items():
            self.frame_at(t).save(os.path.join(d, n + ".png"))

    def finish(self, **facts):
        """Zusammenfassung ausgeben (letzte Zeile = JSON) und mit der Referenz vergleichen."""
        self.summary.update(facts)
        text = json.dumps(self.summary, ensure_ascii=False, sort_keys=True, default=str)
        out = os.path.join(ROOT, "sim", self.name + ".json")
        open(out, "w").write(text)
        print("ZUSAMMENFASSUNG " + text, file=sys.__stdout__)
