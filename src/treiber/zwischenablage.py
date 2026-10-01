"""Texte über die Zwischenablage einfügen statt sie Zeichen für Zeichen zu tippen: Text in die
Zwischenablage (KDE-Klipper über D-Bus, sonst wl-copy), Strg+V drücken, danach den vorherigen
Inhalt der Zwischenablage zurückholen."""


# Einfügeart eines Textes ("paste" in macros.json und bei Textbausteinen); "" = tippen
PASTE_KEYS = {"ctrl+v": ["KEY_LEFTCTRL", "KEY_V"],
              "ctrl+shift+v": ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_V"]}   # Konsole
PASTE_SETTLE_S = 0.15        # Pause zwischen Zwischenablage setzen und Strg+V
PASTE_RESTORE_S = 1.0        # so lange nach Strg+V bleibt der Text in der Zwischenablage
KLIPPER = ["org.kde.klipper", "/klipper"]
KLIPPER_IF = "org.kde.klipper.klipper."


class Clipboard:
    """Zwischenablage der Desktop-Sitzung. Bevorzugt Klipper (qdbus6/qdbus), ersatzweise wl-copy/wl-paste."""

    def __init__(self, env, log=print):
        self.env, self.log = env, log          # env(): Umgebung der Desktop-Sitzung
        self.lock = threading.Lock()           # immer nur ein Einfügen gleichzeitig

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
        """Text in die Zwischenablage legen. False = weder Klipper noch wl-copy erreichbar."""
        env = self.env()
        q = self._qdbus(env)
        try:
            if q and subprocess.run([q, *KLIPPER, KLIPPER_IF + "setClipboardContents", text], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode == 0:
                return True
            if shutil.which("wl-copy", path=env.get("PATH")):
                # wl-copy bleibt im Hintergrund und liefert den Text aus – seine Ausgaben nicht in eine
                # Pipe leiten (capture_output), sonst wartet run() auf das Ende dieses Hintergrundprozesses
                return subprocess.run(["wl-copy", "--type", "text/plain;charset=utf-8"], input=text.encode(), env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode == 0
        except (OSError, subprocess.SubprocessError):
            pass
        return False


def paste_mode(entry):
    """Einfügeart eines Eintrags (G-Taste „Text“ oder Textbaustein): Schlüssel aus PASTE_KEYS oder None = tippen."""
    mode = entry.get("paste") if isinstance(entry, dict) else None
    return mode if mode in PASTE_KEYS else None


def insert_text(app, text, mode, what="Text"):
    """Text ins aktive Fenster bringen: mode None = tippen, sonst über die Zwischenablage einfügen.
    False = es läuft schon ein Makro bzw. Einfügen."""
    if not mode:
        return app.player.play(compile_steps({"text": text}, app.log))
    clip = app.clipboard
    if app.player.busy or not clip.lock.acquire(blocking=False):
        return False

    def work():
        try:
            restore = app.settings().get("clipboard_restore", True)
            old = clip.get() if restore else None
            if not clip.set(text):
                app.log(f"{what}: Zwischenablage nicht erreichbar (Klipper/wl-copy fehlen) – Text wird getippt")
                app.player.play(compile_steps({"text": text}, app.log))
                return
            time.sleep(PASTE_SETTLE_S)
            if not app.player.play(compile_steps({"combo": PASTE_KEYS[mode]}, app.log)):
                app.log("Es läuft bereits ein Makro – ignoriert")
                return
            app.player.thread.join(5)
            if old:                                   # nur Text zurückholen (ein Bild liefert hier "")
                time.sleep(PASTE_RESTORE_S)           # das Zielprogramm liest die Zwischenablage verzögert
                if clip.get() == text:                # inzwischen nichts Neues kopiert?
                    clip.set(old)
        finally:
            clip.lock.release()

    threading.Thread(target=work, daemon=True).start()
    return True
