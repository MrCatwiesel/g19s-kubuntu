#!/usr/bin/env python3
"""
g19s-gui.py – Grafische Verwaltung für den Logitech-G19s-Treiber (g19s.py)

Startet einen kleinen Webserver nur auf diesem Rechner (127.0.0.1) und öffnet
die Oberfläche als App-Fenster im Browser. Damit lassen sich verwalten:
  * Belegung der G-Tasten je Profil (Text, Tastenkombination, Makro, Webseite,
    Programm, Radiosender, Musiksteuerung, KDE-Kurzbefehl)
  * Radiosender (inkl. Suche im Radio-Browser-Verzeichnis und Probehören)
  * Beleuchtungsfarben, Displayhelligkeit, Startseite (mit Display-Vorschau)
  * Treiber-Dienst (Start/Stopp/Autostart, Log) und Sicherung/Wiederherstellung

Aufruf:
  g19s-gui.py                    Oberfläche öffnen
  g19s-gui.py --install-desktop  Eintrag „G19s-Verwaltung“ im Anwendungsmenü anlegen
  g19s-gui.py --no-browser       nur Server starten und Adresse ausgeben

Benötigt: g19s.py im selben Ordner (dieselben Pakete wie der Treiber)
"""

import argparse
import base64
import datetime
import http.server
import importlib.util
import io
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
import urllib.parse
import urllib.request

G19S_COMPONENT = "gui"        # Kennung für den Update-Knopf
VERSION = "2026.09.30-5"

HERE = os.path.dirname(os.path.realpath(__file__))
SERVICE = "g19s.service"
HOME = os.path.expanduser("~")
# Laufzeitordner des Benutzers; ohne XDG_RUNTIME_DIR nicht /tmp (dort könnte ein anderer Benutzer
# die Instanzdatei vorher anlegen), sondern der eigene Cache-Ordner
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or os.path.join(
    os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache")), "g19s")
INSTANCE_FILE = os.path.join(RUNTIME_DIR, "g19s-gui.json")
IDLE_TIMEOUT = 45          # Sekunden ohne Lebenszeichen der Seite -> Server beenden
FIRST_CONTACT_TIMEOUT = 180


def load_driver():
    path = os.path.join(HERE, "g19s.py")
    if not os.path.exists(path):
        sys.exit(f"g19s.py nicht gefunden (erwartet in {HERE})")
    spec = importlib.util.spec_from_file_location("g19s", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [name for name in DRIVER_API if not hasattr(mod, name)]
    if missing:
        sys.exit("Die installierte g19s.py ist zu alt für die Oberfläche – bitte aktualisieren "
                 f"(es fehlt: {', '.join(missing[:5])}).")
    return mod


# Alle Namen des Treibers, die die Verwaltung benutzt (g.<name>) – build.py trägt sie beim Bauen ein
DRIVER_API = "@@DRIVER_API@@".split()


g = load_driver()
