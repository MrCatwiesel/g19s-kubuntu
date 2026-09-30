#!/usr/bin/env python3
"""Alle Tests mit einem Befehl.

    python3 tests/run_tests.py              # alles
    python3 tests/run_tests.py bilder sim   # nur Teile: einheit, bilder, sim, gui
    python3 tests/run_tests.py --referenz   # Referenzen (Bilder, Simulationen) neu schreiben
    python3 tests/run_tests.py sim=s09      # nur Simulationen, deren Name so beginnt

Getestet werden dist/g19s.py und dist/g19s-gui.py (vorher build.py ausführen)
oder die Dateien aus G19S_DRIVER / G19S_GUI.
"""
import glob
import json
import os
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.environ.setdefault("G19S_TEST_ROOT", "/tmp/g19s-test")
DRIVER = os.environ.setdefault("G19S_DRIVER", os.path.join(PROJ, "dist", "g19s.py"))
GUI = os.environ.setdefault("G19S_GUI", os.path.join(PROJ, "dist", "g19s-gui.py"))
FAKETIME_DIR = os.path.join(HERE, ".werkzeuge", "libfaketime")
FAKETIME = os.path.join(FAKETIME_DIR, "src", "libfaketime.so.1")
TIME = "2026-10-01 09:30:00"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
REF = "--referenz" in sys.argv
parts = [a.split("=")[0] for a in args] or ["einheit", "bilder", "sim", "gui"]
SIM_FILTER = next((a.split("=", 1)[1] for a in args if a.startswith("sim=")), "")
results = []                 # (Teil, Name, ok, Hinweis)
env = dict(os.environ, TZ="Europe/Berlin", NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost",
           PYTHONPATH=os.path.join(HERE, "stubs"), PYTHONDONTWRITEBYTECODE="1")


def report(part, name, ok, hint=""):
    results.append((part, name, ok, hint))
    print(f"{'OK  ' if ok else 'FEHL'} [{part}] {name}" + (f" – {hint}" if hint else ""), flush=True)


def prepare():
    shutil.rmtree(ROOT, ignore_errors=True)
    os.makedirs(os.path.join(ROOT, "state"))
    shutil.copytree(os.path.join(HERE, "fakes", "bin"), os.path.join(ROOT, "bin"))
    for p in (DRIVER, GUI):
        if not os.path.exists(p):
            sys.exit(f"{p} fehlt – zuerst python3 build.py ausführen")


def ensure_faketime():
    if os.path.exists(FAKETIME):
        return
    os.makedirs(os.path.dirname(FAKETIME_DIR), exist_ok=True)
    if not os.path.isdir(FAKETIME_DIR):
        subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/wolfcw/libfaketime.git", FAKETIME_DIR], check=True)
    subprocess.run(["make", "-s", "-C", os.path.join(FAKETIME_DIR, "src"), "libfaketime.so.1"], check=True,
                   stdout=subprocess.DEVNULL)


servers = []


def _kill_stale(names):
    """Übrig gebliebene Nachbau-Server früherer (abgebrochener) Läufe beenden – per PID, nicht per pkill -f."""
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
        except OSError:
            continue
        if len(cmd) > 1 and cmd[0].endswith(b"python3") and any(c.endswith(n.encode()) for c in cmd[1:2] for n in names):
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError:
                pass


def start_servers():
    import socket
    scripts = {"piwigo.py": 8811, "infodienste.py": 8812}
    _kill_stale(["fakes/" + s for s in scripts])
    time.sleep(0.3)
    for script in scripts:
        servers.append(subprocess.Popen([sys.executable, os.path.join(HERE, "fakes", script)], env=env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for script, port in scripts.items():
        for _ in range(40):
            try:
                socket.create_connection(("127.0.0.1", port), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            sys.exit(f"Nachbau-Server {script} startet nicht (Port {port})")


def stop_servers():
    for p in servers:
        p.terminate()


# --------------------------------------------------------------------------- einheit
def run_unit():
    for f in sorted(glob.glob(os.path.join(HERE, "einheit", "test_*.py"))):
        r = subprocess.run([sys.executable, f], env=env, capture_output=True, text=True, timeout=300)
        lines = [l for l in r.stdout.splitlines() if l.startswith(("OK", "FEHL"))]
        bad = [l for l in lines if l.startswith("FEHL")]
        report("einheit", f"{os.path.basename(f)} ({len(lines)} Prüfungen)", r.returncode == 0 and not bad,
               "; ".join(bad)[:300] or (r.stderr.strip().splitlines() or [""])[-1][:300])


# --------------------------------------------------------------------------- bilder
def run_images():
    from PIL import Image, ImageChops
    ensure_faketime()
    out = os.path.join(ROOT, "bilder")
    fenv = dict(env, LD_PRELOAD=FAKETIME, FAKETIME=TIME)
    r = subprocess.run([sys.executable, os.path.join(HERE, "golden", "scenes.py"), DRIVER, out], env=fenv,
                       capture_output=True, text=True, timeout=300)
    if r.returncode:
        report("bilder", "Szenen erzeugen", False, r.stderr.strip()[-400:])
        return
    ref = os.path.join(HERE, "golden", "ref")
    if REF:
        shutil.rmtree(ref, ignore_errors=True)
        shutil.copytree(out, ref)
        report("bilder", f"Referenz geschrieben ({len(os.listdir(ref))} Bilder)", True)
        return
    names = sorted(set(os.listdir(ref)) | set(os.listdir(out)))
    diff = []
    for n in names:
        a, b = os.path.join(ref, n), os.path.join(out, n)
        if not (os.path.exists(a) and os.path.exists(b)):
            diff.append(n + " (fehlt)")
            continue
        box = ImageChops.difference(Image.open(a).convert("RGB"), Image.open(b).convert("RGB")).getbbox()
        if box:
            diff.append(f"{n} {box}")
    report("bilder", f"{len(names)} Szenen pixelgleich", not diff, ", ".join(diff)[:500])


# --------------------------------------------------------------------------- sim
def run_sims():
    ref_dir = os.path.join(HERE, "sim", "erwartet")
    os.makedirs(ref_dir, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(HERE, "sim", "s*.py"))):
        name = os.path.basename(f)[:-3]
        if not name.startswith(SIM_FILTER):
            continue
        senv = dict(env, PYTHONPATH=os.path.join(HERE, "stubs") + ":" + os.path.join(HERE, "sim"))
        r = subprocess.run([sys.executable, f], env=senv, capture_output=True, text=True, timeout=200, cwd=os.path.join(HERE, "sim"))
        line = next((l for l in r.stdout.splitlines() if l.startswith("ZUSAMMENFASSUNG ")), None)
        if r.returncode or line is None:
            report("sim", name, False, (r.stderr.strip().splitlines() or ["keine Zusammenfassung"])[-1][:300])
            continue
        got = json.loads(line[16:])
        path = os.path.join(ref_dir, name + ".json")
        if REF:
            json.dump(got, open(path, "w"), ensure_ascii=False, indent=1, sort_keys=True)
            report("sim", name + " (Referenz geschrieben)", True)
            continue
        want = json.load(open(path))
        diffs = [k for k in sorted(set(want) | set(got)) if want.get(k) != got.get(k)]
        report("sim", name, not diffs, "; ".join(f"{k}: erwartet {json.dumps(want.get(k), ensure_ascii=False)[:160]} "
                                               f"– ist {json.dumps(got.get(k), ensure_ascii=False)[:160]}" for k in diffs))


# --------------------------------------------------------------------------- gui
def run_gui():
    genv = dict(env, G19S_ALERTS_URL="http://127.0.0.1:8812/alerts")
    r = subprocess.run(["bash", os.path.join(HERE, "gui", "run_gui.sh")], env=genv, capture_output=True, text=True, timeout=1500)
    for line in r.stdout.splitlines():
        if line.startswith("ERGEBNIS "):
            _, name, ok, fail = line.split()
            out = open(os.path.join(ROOT, "gui", f"out_{name.removesuffix('_absturz')}.txt")).read()
            report("gui", f"{name}: {ok} OK, {fail} FEHL", fail == "0" and ok != "0",
                   "; ".join(l for l in out.splitlines() if l.startswith(("FEHL", "Traceback", "playwright.")))[:400])
    if r.returncode:
        report("gui", "Ablauf", False, r.stderr.strip()[-300:])


prepare()
if set(parts) != {"bilder"}:            # Bildvergleich braucht keine Nachbau-Server
    start_servers()
try:
    for p in parts:
        {"einheit": run_unit, "bilder": run_images, "sim": run_sims, "gui": run_gui}[p]()
finally:
    stop_servers()
bad = [r for r in results if not r[2]]
print(f"\n{len(results) - len(bad)} von {len(results)} Testgruppen bestanden.")
sys.exit(1 if bad else 0)
