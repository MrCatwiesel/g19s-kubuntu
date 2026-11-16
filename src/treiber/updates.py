"""Verfügbare Systemupdates (apt, Flatpak) und „Neustart erforderlich“."""


# --- Systemupdates (apt, Flatpak) -----------------------------------------------
G19S_RELEASES_URL = os.environ.get("G19S_UPDATE_URL",
                                   "https://api.github.com/repos/MrCatwiesel/g19s-kubuntu/releases")


def g19s_version_key(v):
    """„2026.09.30-5“ → (2026, 9, 30, 5); unbekannt → ()."""
    return tuple(int(x) for x in re.findall(r"\d+", v or "")) if re.match(r"\d", v or "") else ()


def g19s_newest(raw, current=None):
    """Neueste veröffentlichte G19s-Version aus der Antwort von GitHub, wenn sie neuer ist als current; sonst None."""
    try:
        data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except (ValueError, UnicodeDecodeError):
        return None
    best = None
    for r in data if isinstance(data, list) else []:
        if not isinstance(r, dict) or r.get("draft") or r.get("prerelease"):
            continue
        v = str(r.get("tag_name") or "").lstrip("vV")
        if g19s_version_key(v) and (best is None or g19s_version_key(v) > g19s_version_key(best)):
            best = v
    if best and g19s_version_key(best) > g19s_version_key(current or VERSION):
        return best
    return None


class UpdatesPoller(Poller):
    FLATPAK_INTERVAL = 6 * 3600     # flatpak remote-ls fragt die Server im Netz ab – seltener als apt
    G19S_INTERVAL = 24 * 3600       # neue G19s-Version: einmal am Tag bei GitHub nachsehen

    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 3600, log)
        self._flatpak = (-1e9, None)             # (Zeitpunkt, Anzahl)
        self._g19s = (-1e9, None)                # (Zeitpunkt, neuere Version oder None)

    def refresh(self):
        self._flatpak = (-1e9, None)             # MENU auf der Seite: alles neu abfragen
        self._g19s = (-1e9, None)
        super().refresh()

    def _check_g19s(self):
        """Täglicher Hinweis auf eine neue G19s-Version (Einstellung updates.g19s, Standard an)."""
        if not (self.get_settings().get("updates") or {}).get("g19s", True):
            return None
        if time.monotonic() - self._g19s[0] < self.G19S_INTERVAL:
            return self._g19s[1]
        try:
            newest = g19s_newest(http_get(G19S_RELEASES_URL + "?per_page=10", timeout=15, limit=4 * 1024 * 1024))
        except Exception as ex:                 # kein Netz: morgen wieder
            self.log(f"Updates: GitHub nicht erreichbar ({err_text(ex)})")
            newest = None
        if newest and newest != self._g19s[1]:
            self.log(f"Updates: neue G19s-Version {newest} verfügbar")
        self._g19s = (time.monotonic(), newest)
        return newest

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
                "reboot": reboot, "g19s": self._check_g19s(), "checked": time.strftime("%H:%M"), "apt_ok": bool(shutil.which("apt"))}
