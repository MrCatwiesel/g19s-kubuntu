"""Verfügbare Systemupdates (apt, Flatpak) und „Neustart erforderlich“."""


# --- Systemupdates (apt, Flatpak) -----------------------------------------------
class UpdatesPoller(Poller):
    FLATPAK_INTERVAL = 6 * 3600     # flatpak remote-ls fragt die Server im Netz ab – seltener als apt

    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 3600, log)
        self._flatpak = (-1e9, None)             # (Zeitpunkt, Anzahl)

    def refresh(self):
        self._flatpak = (-1e9, None)             # MENU auf der Seite: alles neu abfragen
        super().refresh()

    def enabled(self):
        return "updates" in (self.get_settings().get("pages") or [])

    def fetch(self):
        env = dict(os.environ, LC_ALL="C")
        pkgs, security = [], 0
        if shutil.which("apt"):
            r = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True, timeout=120, env=env)
            for line in r.stdout.splitlines():
                if "/" in line and "[upgradable" in line:
                    pkgs.append(line.split("/", 1)[0])
                    if "-security" in line.split(" ", 1)[0]:
                        security += 1
        flatpak = None
        if (self.get_settings().get("updates") or {}).get("flatpak", True) and shutil.which("flatpak"):
            if time.monotonic() - self._flatpak[0] < self.FLATPAK_INTERVAL:
                flatpak = self._flatpak[1]
            else:
                try:
                    r = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application"],
                                       capture_output=True, text=True, timeout=120, env=env)
                    flatpak = len([l for l in r.stdout.splitlines() if l.strip()]) if r.returncode == 0 else None
                except (OSError, subprocess.TimeoutExpired):
                    flatpak = None
                if flatpak is not None:
                    self._flatpak = (time.monotonic(), flatpak)
        reboot = os.path.exists("/var/run/reboot-required")
        return {"apt": len(pkgs), "security": security, "packages": pkgs[:60], "flatpak": flatpak,
                "reboot": reboot, "checked": time.strftime("%H:%M"), "apt_ok": bool(shutil.which("apt"))}
