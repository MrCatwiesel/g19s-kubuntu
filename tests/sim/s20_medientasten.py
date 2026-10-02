"""Medientasten der Tastatur (Consumer-Control-Gerät 046d:c228): Der Treiber übernimmt das Gerät exklusiv,
Lautstärkerad und Stumm ändern die Systemlautstärke (Display + KDE-Anzeige), Play/Pause geht an einen
Player, andere Tasten des Geräts werden unverändert weitergegeben. Mit "media_keys": false gibt der Treiber
das Gerät frei und reagiert nicht mehr darauf."""
import json, os, types
import evdev
from harness import Sim, ROOT
S = os.path.join(ROOT, "state")
for f in ("vol", "wpctl.log", "osd.log"):
    try:
        os.remove(os.path.join(S, f))
    except FileNotFoundError:
        pass
s = Sim("s20_medientasten", macros={"profiles": [{"name": "P", "keys": {}}]},
        settings={"pages": ["clock"], "start_page": 0, "notifications": {"enabled": False}}, media_keys=True)
g, e = s.g, evdev.ecodes


class FakeDev:
    """Consumer-Control-Gerät: Ereignisse über eine Pipe, damit select() wie beim echten Gerät wartet."""
    name = "G19s Gaming Keyboard Consumer Control"

    def __init__(self):
        self.r, self.w = os.pipe()
        self.queue, self.grabs = [], []

    def fileno(self):
        return self.r

    def grab(self):
        self.grabs.append("grab")

    def ungrab(self):
        self.grabs.append("ungrab")

    def close(self):
        pass

    def push(self, code, value):
        self.queue.append(types.SimpleNamespace(type=e.EV_KEY, code=code, value=value))
        os.write(self.w, b"x")

    def read(self):
        os.read(self.r, 4096)
        out, self.queue = self.queue, []
        return out


dev = FakeDev()
g.MediaKeys.find_device = staticmethod(lambda: dev)
played = []
g.playerctl_any = lambda action, env=None: played.append(action) or True


def tap(code):
    return lambda sim: (dev.push(code, 1), dev.push(code, 0))


s.call(1.0, tap(e.KEY_VOLUMEUP))
s.call(1.3, tap(e.KEY_VOLUMEUP))
s.call(1.6, tap(e.KEY_VOLUMEDOWN))
s.call(1.9, tap(e.KEY_MUTE))
s.call(2.2, tap(e.KEY_PLAYPAUSE))
s.call(2.5, tap(e.KEY_NEXTSONG))
s.call(2.8, tap(e.KEY_CALC))                     # keine Medientaste: unverändert weitergeben


def disable(sim):
    st = json.load(open(g.SETTINGS_FILE))
    st["media_keys"] = False
    json.dump(st, open(g.SETTINGS_FILE, "w"))
    os.utime(g.SETTINGS_FILE, (os.path.getmtime(g.SETTINGS_FILE) + 5,) * 2)
s.call(3.5, disable)
s.call(7.0, tap(e.KEY_VOLUMEUP))                 # freigegeben: geht an KDE, nicht an den Treiber
s.run(8.0)


def read(name):
    try:
        return [l for l in open(os.path.join(S, name)).read().split("\n") if l]
    except FileNotFoundError:
        return []
s.finish(grabs=dev.grabs, volume=read("wpctl.log"), osd=read("osd.log"), played=played,
         sent=[f"{k}{'↓' if v else '↑'}" for k, v in evdev.SENT if v in (0, 1)],
         log=[l for l in s.log if "Medientaste" in l])
