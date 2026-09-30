"""Den systemd-Benutzerdienst des Treibers steuern und sein Protokoll lesen."""


# --------------------------------------------------------------------------- #
# Dienst
# --------------------------------------------------------------------------- #
def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]} nicht gefunden"
    except subprocess.TimeoutExpired:
        return 124, "Zeitüberschreitung"


_service_cache = [0.0, None]


def service_status(max_age=0.0):
    """Zustand des Dienstes; max_age > 0: so lange zwischengespeichert (für die regelmäßige Abfrage)."""
    now = time.monotonic()
    if _service_cache[1] is not None and now - _service_cache[0] < max_age:
        return _service_cache[1]
    _, active = run(["systemctl", "--user", "is-active", SERVICE])
    _, enabled = run(["systemctl", "--user", "is-enabled", SERVICE])
    st = {"active": active.splitlines()[0] if active else "unbekannt",
          "enabled": enabled.splitlines()[0] if enabled else "unbekannt"}
    _service_cache[:] = [now, st]
    return st


def service_log(lines=80):
    _, out = run(["journalctl", "--user", "-u", SERVICE, "-n", str(lines), "--no-pager",
                  "-o", "short"])
    return out


def service_action(action):
    cmds = {
        "start": ["systemctl", "--user", "start", SERVICE],
        "stop": ["systemctl", "--user", "stop", SERVICE],
        "restart": ["systemctl", "--user", "restart", SERVICE],
        "enable": ["systemctl", "--user", "enable", SERVICE],
        "disable": ["systemctl", "--user", "disable", SERVICE],
    }
    if action not in cmds:
        raise ValueError("Unbekannte Aktion")
    code, out = run(cmds[action], timeout=20)
    if code != 0:
        raise RuntimeError(out or f"systemctl meldet Fehler {code}")
