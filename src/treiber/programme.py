"""Programme und Webseiten starten (mit der Umgebung der Desktop-Sitzung), mpv-mpris finden."""


class Launcher:
    """Startet Webseiten/Befehle in der laufenden Desktop-Sitzung."""

    SESSION_VARS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
                    "XDG_RUNTIME_DIR", "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE",
                    "XDG_DATA_DIRS", "XDG_CONFIG_DIRS", "KDE_FULL_SESSION",
                    "KDE_SESSION_VERSION", "DESKTOP_SESSION", "PATH", "LANG", "LANGUAGE")

    def __init__(self, log=print):
        self.log = log
        self.children = []

    def _env(self):
        env = dict(os.environ)
        try:
            out = subprocess.run(["systemctl", "--user", "show-environment"],
                                 capture_output=True, text=True, timeout=3).stdout
        except (OSError, subprocess.SubprocessError):
            return env
        for line in out.splitlines():
            key, sep, value = line.partition("=")
            if sep and key in self.SESSION_VARS and not value.startswith("$'"):
                env[key] = value
        return env

    def start(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd, shell=isinstance(cmd, str), env=self._env(),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
                cwd=os.path.expanduser("~"))
        except OSError as ex:
            self.log(f"Start fehlgeschlagen: {ex}")
            return False
        self.children.append(proc)
        return True

    def reap(self):
        self.children = [p for p in self.children if p.poll() is None]


def find_mpris_plugin():
    """Sucht das mpv-Plugin (Paket mpv-mpris), mit dem sich mpv bei KDE als Player anmeldet."""
    import glob
    patterns = ["/etc/mpv/scripts/mpris.so", "/usr/share/mpv/scripts/mpris.so",
                "/usr/lib/mpv-mpris/mpris.so", "/usr/lib/*/mpv-mpris/mpris.so",
                "/usr/lib/*/mpv/scripts/mpris.so", "/usr/local/lib/mpv-mpris/mpris.so",
                os.path.expanduser("~/.config/mpv/scripts/mpris.so")]
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            if os.path.isfile(path):
                return path
    return None
