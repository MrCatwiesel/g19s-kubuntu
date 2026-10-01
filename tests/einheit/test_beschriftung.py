"""Art und Beschriftung von Tastenbelegungen: Treiber (Python) und Verwaltung (JavaScript) stimmen überein."""
import json, os, shutil, subprocess
from common import g, eq, ok, done, PROJ

stations = [{"name": "Rockantenne", "url": "https://stream.rockantenne.de/x"}, {"name": "", "url": "https://ohne-name.de/s"}]
entries = [
    {"name": "Eigener Name", "text": "x"}, {"text": "Hallo"}, {"combo": "KEY_LEFTCTRL+KEY_C"}, {"combo": ["KEY_LEFTALT", "KEY_F4", " "]},
    {"combo": "KEY_A+"}, {"steps": [[0, "KEY_A", "tap"]]}, {"open": "https://www.heise.de/news"}, {"open": "HTTPS://Example.org"},
    {"run": "konsole --new-tab"}, {"run": "   "}, {"radio": "stop"}, {"radio": "https://stream.rockantenne.de/x"},
    {"radio": "https://ohne-name.de/s"}, {"radio": "https://unbekannt.de/live"}, {"media": "play-pause"}, {"media": "remember"},
    {"media": "gibtsnicht"}, {"volume": "up"}, {"volume": "?"}, {"snippets": "*"}, {"snippets": "Büro"},
    {"timer": {"mode": "timer", "minutes": 0.5}}, {"timer": {"mode": "timer", "minutes": 1.5}}, {"timer": {"mode": "timer"}},
    {"timer": {"mode": "pomodoro", "work": 50, "break": 10}}, {"timer": {"mode": "pomodoro", "work": "x"}},
    {"timer": {"mode": "stopwatch"}}, {"timer": "kaputt", "text": "t"}, {"sleep": 30}, {"mic": True},
    {"text": "a", "combo": "KEY_B", "steps": [[0, "KEY_C", "tap"]]}, {}, {"text": ""}, {"steps": []},
    {"snippets": "*", "snippet": "Gruß"}, {"snippets": "Büro", "keep_open": True},
]
settings = {"stations": stations}
py = [[g.entry_type(e) or "default", g.entry_label(e, settings)] for e in entries]

# Einzelne Erwartungen (Python)
eq(py[3], ["combo", "Alt links+F4"] if g.key_label("KEY_LEFTALT") == "Alt links" else py[3], "Kombination aus Liste")
eq(py[21][1], "Timer 30 s", "Timer unter 1 Minute in Sekunden")
eq(py[12][1], "ohne-name.de", "Sender ohne Namen: Domain")
eq(py[13][1], "unbekannt.de", "unbekannter Sender: Domain")
eq(py[25][1], "Pomodoro 25/5", "ungültige Pomodoro-Zeit → Standard")
eq(py[30][0], "text", "mehrere Arten: Text vor Kombination vor Makro (wie bei der Ausführung)")
eq(py[9], ["run", ""], "Programm nur aus Leerzeichen stürzt nicht ab")
eq(py[-2], ["snippets", "Gruß"], "einzelner Textbaustein: dessen Name")
eq(py[-1], ["snippets", "Büro"], "Liste bleibt offen: Gruppe wie bisher")
ok(set(g.GKEY_ACTIONS) == set(g.ENTRY_TYPES), "jede Art hat eine Ausführung")

node = shutil.which("node")
if not node:
    ok(True, "Node.js fehlt – Vergleich mit der Verwaltung übersprungen")
else:
    keys = sorted({k for e in entries for k in g.combo_keys(e.get("combo"))})
    js_state = {"entryTypes": g.ENTRY_TYPES, "media": g.MEDIA_ACTIONS, "volume": g.VOLUME_ACTIONS,
                "keyLabel": {k: g.key_label(k) for k in keys}, "settings": settings}
    script = ("const vm = require('vm'), fs = require('fs');\n"
              f"globalThis.S = {json.dumps(js_state)}; globalThis.UI = {{}};\n"
              f"vm.runInThisContext(fs.readFileSync({json.dumps(os.path.join(PROJ, 'src/verwaltung/seite/js/02_hilfen.js'))}, 'utf8'));\n"
              f"const entries = {json.dumps(entries)};\n"
              "console.log(JSON.stringify(entries.map(e => [typeOf(e), entryLabel(e)])));\n")
    r = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    js = json.loads(r.stdout or "null") if r.returncode == 0 else None
    ok(js is not None, "JavaScript ausgeführt" + ("" if js is not None else ": " + r.stderr[-300:]))
    if js is not None:
        diff = [f"{json.dumps(e, ensure_ascii=False)}: Treiber {p} – Verwaltung {j}" for e, p, j in zip(entries, py, js) if p != j]
        eq(diff, [], f"Art und Beschriftung in Treiber und Verwaltung gleich ({len(entries)} Beispiele)")
done()
