"""Hilfen für die Unit-Tests: Treiber laden, Prüfungen zählen."""
import importlib.util
import os
import sys
import tempfile

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TMP = tempfile.mkdtemp(prefix="g19s-einheit-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(TMP, "config")
os.environ["XDG_CACHE_HOME"] = os.path.join(TMP, "cache")
sys.path.insert(0, os.path.join(PROJ, "tests", "stubs"))
spec = importlib.util.spec_from_file_location("g19s", os.environ.get("G19S_DRIVER", os.path.join(PROJ, "dist", "g19s.py")))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
FAILS = []


def ok(cond, msg):
    print(("OK   " if cond else "FEHL ") + msg)
    if not cond:
        FAILS.append(msg)


def eq(got, want, msg):
    ok(got == want, msg if got == want else f"{msg}: erwartet {want!r}, ist {got!r}")


def done():
    sys.exit(1 if FAILS else 0)
