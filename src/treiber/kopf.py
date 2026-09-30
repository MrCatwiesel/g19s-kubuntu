#!/usr/bin/env python3
"""
g19s.py – Userspace-Treiber für die Logitech G19 / G19s unter Linux

  * Display (320×240): Uhr, Musik/Radio, Wetter, Termine, System, Hardware, Makros,
    Diashow, Nachrichten, Unwetter, Netzwerk, Updates – Auswahl je Ebene und Profil.
  * G1–G12: Makros, Text, Tastenkombinationen, Webseiten, Programme, Radio,
    Musiksteuerung, Lautstärke, Mikrofon, Timer, Textbausteine, Einschlaftimer –
    sonst F13–F24 (M2: Strg+, M3: Alt+) für KDE-Kurzbefehle.
  * M1/M2/M3: Ebenen, SETTINGS: bis zu 10 Profile, MR: Makro aufnehmen.
  * Nachtmodus, Bildschirmschoner, Benachrichtigungen, Terminerinnerung, Radiowecker,
    automatische Sicherung.

Dateien: ~/.config/g19s/macros.json (Belegung), settings.json (Einstellungen),
state.json (Zustand), songs.json, favorites.json. Bearbeiten am einfachsten mit
der Verwaltung g19s-gui.py; Änderungen übernimmt der Treiber sofort.

Aufruf:
  python3 g19s.py              normaler Betrieb
  python3 g19s.py --debug      zeigt die Rohdaten jeder Taste (zum Prüfen der Belegung)
  python3 g19s.py --preview x  rendert die Displayseiten als PNG (ohne Tastatur)

Benötigt: python3-usb python3-evdev python3-pil python3-numpy playerctl mpv

Diese Datei wird aus den Modulen in src/treiber/ zusammengesetzt (build.py);
jedes Modul beginnt unten mit einer Überschrift „Modul …“.
"""

import argparse
import json
import os
import re
import shutil
import signal
import sys
import subprocess
import threading
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

G19S_COMPONENT = "driver"     # Kennung für den Update-Knopf der Verwaltung
VERSION = "2026.09.30-4"
