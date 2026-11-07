"""Verwaltung: Fenstergröße passt zum Bildschirm (Taskleiste darf die Speicherleiste nicht verdecken)."""
import importlib.util
import json
import os
from common import eq, done, PROJ

spec = importlib.util.spec_from_file_location("gui", os.environ.get("G19S_GUI", os.path.join(PROJ, "dist", "g19s-gui.py")))
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)

eq(gui.window_size(None), (1200, 860), "Bildschirm unbekannt: wie bisher 1200 × 860")
eq(gui.window_size((2560, 1440)), (1200, 860), "Großer Bildschirm: 1200 × 860")
eq(gui.window_size((1536, 864)), (1200, 724), "1536 × 864: niedriger, Platz für Taskleiste")
eq(gui.window_size((1024, 600)), (984, 460), "Kleiner Bildschirm")
ks = {"outputs": [
    {"enabled": False, "connected": True, "priority": 0, "size": {"width": 800, "height": 600}, "scale": 1},
    {"enabled": True, "connected": True, "priority": 2, "currentModeId": "3", "scale": 1,
     "modes": [{"id": "3", "size": {"width": 3840, "height": 2160}}]},
    {"enabled": True, "connected": True, "priority": 1, "currentModeId": "7", "scale": 1.25, "rotation": 1,
     "modes": [{"id": "6", "size": {"width": 1280, "height": 720}}, {"id": "7", "size": {"width": 1920, "height": 1200}}]}]}
eq(gui.parse_kscreen(json.dumps(ks)), (1536, 960), "kscreen-doctor: Hauptbildschirm, Skalierung 125 %")
eq(gui.parse_kscreen(json.dumps({"outputs": []})), None, "kscreen-doctor ohne Bildschirm")
eq(gui.parse_xrandr("Screen 0: minimum 16 x 16, current 1920 x 1080, maximum 32767 x 32767"), (1920, 1080), "xrandr")
eq(gui.parse_xrandr("Unsinn"), None, "xrandr ohne Angabe")
done()
