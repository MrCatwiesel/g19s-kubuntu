"""Texte über die Zwischenablage einfügen statt sie Zeichen für Zeichen zu tippen: Text in die
Zwischenablage (KDE-Klipper über D-Bus, sonst wl-copy), dann Strg+V drücken. Der Text bleibt danach
in der Zwischenablage (wie Kopieren) – auf Wunsch wird der vorherige Inhalt zurückgeholt."""


# Einfügeart eines Textes ("paste" in macros.json und bei Textbausteinen); "" = tippen
PASTE_KEYS = {"ctrl+v": ["KEY_LEFTCTRL", "KEY_V"],
              "ctrl+shift+v": ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_V"]}   # Konsole
PASTE_SETTLE_S = 0.3         # Pause zwischen Zwischenablage setzen und Strg+V (RDP gleicht verzögert ab)
PASTE_RESTORE_S = 1.0        # so lange nach Strg+V bleibt der Text mindestens in der Zwischenablage
KLIPPER = ["org.kde.klipper", "/klipper"]
KLIPPER_IF = "org.kde.klipper.klipper."


class Clipboard:
    """Zwischenablage der Desktop-Sitzung. Bevorzugt Klipper (qdbus6/qdbus), ersatzweise wl-copy/wl-paste."""

    def __init__(self, env, log=print):
        self.env, self.log = env, log          # env(): Umgebung der Desktop-Sitzung
        self.lock = threading.Lock()           # setzen + Strg+V nie gleichzeitig
        self.generation = 0                    # zählt Einfügevorgänge (Zurückholen nur nach dem letzten)
        self.saved = None                      # vorheriger Inhalt, solange ein Zurückholen aussteht

    def _qdbus(self, env):
        return next((q for q in ("qdbus6", "qdbus") if shutil.which(q, path=env.get("PATH"))), None)

    def get(self):
        """Text der Zwischenablage oder None (nicht lesbar)."""
        env = self.env()
        q = self._qdbus(env)
        try:
            if q:
                r = subprocess.run([q, *KLIPPER, KLIPPER_IF + "getClipboardContents"], env=env,
                                   capture_output=True, text=True, timeout=3)
                if r.returncode == 0:
                    return r.stdout[:-1] if r.stdout.endswith("\n") else r.stdout   # qdbus hängt \n an
            if shutil.which("wl-paste", path=env.get("PATH")):
                r = subprocess.run(["wl-paste", "--no-newline", "--type", "text"], env=env,
                                   capture_output=True, text=True, timeout=3)
                if r.returncode == 0:
                    return r.stdout
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
            pass
        return None

    def set(self, text):
        """Text in die Zwischenablage legen. Rückgabe: "Klipper", "wl-copy" oder None (beides nicht erreichbar)."""
        env = self.env()
        q = self._qdbus(env)
        try:
            if q:
                r = subprocess.run([q, *KLIPPER, KLIPPER_IF + "setClipboardContents", text], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=3)
                if r.returncode == 0:
                    return "Klipper"
                self.log(f"Klipper: {(r.stderr or '').strip()[:150] or f'Fehler {r.returncode}'}")
            if shutil.which("wl-copy", path=env.get("PATH")):
                # wl-copy bleibt im Hintergrund und liefert den Text aus – seine Ausgaben nicht in eine
                # Pipe leiten (capture_output), sonst wartet run() auf das Ende dieses Hintergrundprozesses
                if subprocess.run(["wl-copy", "--type", "text/plain;charset=utf-8"], input=text.encode(), env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode == 0:
                    return "wl-copy"
        except (OSError, subprocess.SubprocessError) as ex:
            self.log(f"Zwischenablage: {ex}")
        return None


def paste_mode(entry):
    """Einfügeart eines Eintrags (G-Taste „Text“ oder Textbaustein): Schlüssel aus PASTE_KEYS oder None = tippen."""
    mode = entry.get("paste") if isinstance(entry, dict) else None
    return mode if mode in PASTE_KEYS else None


def insert_text(app, text, mode, what="Text"):
    """Text ins aktive Fenster bringen: mode None = tippen, sonst über die Zwischenablage einfügen.
    False = es läuft gerade ein Makro."""
    if not mode:
        return app.player.play(compile_steps({"text": text}, app.log))
    if app.player.busy:
        return False
    clip = app.clipboard
    with clip.lock:
        clip.generation += 1
        gen = clip.generation

    def work():
        with clip.lock:                               # wartet höchstens auf ein laufendes Setzen + Strg+V
            if gen != clip.generation:
                return                                # inzwischen erneut gedrückt: der neuere Druck gewinnt
            restore = app.settings().get("paste_restore", False)
            if restore and clip.saved is None:
                clip.saved = clip.get()               # vorherigen Inhalt nur beim ersten von mehreren Drücken merken
            how = clip.set(text)
            if not how:
                app.log(f"{what}: Zwischenablage nicht erreichbar (Klipper/wl-copy fehlen) – Text wird getippt")
                app.player.play(compile_steps({"text": text}, app.log))
                return
            time.sleep(PASTE_SETTLE_S)
            if not app.player.play(compile_steps({"combo": PASTE_KEYS[mode]}, app.log)):
                app.log("Es läuft bereits ein Makro – ignoriert")
                return
            app.player.thread.join(5)
            app.log(f"{what}: eingefügt über {how} ({len(text)} Zeichen)")
        if not restore:
            clip.saved = None
            return
        time.sleep(PASTE_RESTORE_S)                   # das Zielprogramm liest die Zwischenablage verzögert
        with clip.lock:
            old, clip.saved = clip.saved, None
            if gen != clip.generation:
                clip.saved = old                      # ein neuerer Druck holt später zurück
            elif old and clip.get() == text:          # nur Text zurückholen, nicht wenn Neues kopiert wurde
                clip.set(old)

    threading.Thread(target=work, daemon=True).start()
    return True
