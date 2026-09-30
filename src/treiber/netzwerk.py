"""Erreichbarkeit von Geräten (Ping oder TCP-Port), Router und eigene Adresse ermitteln."""


# --- Netzwerk: Erreichbarkeit von Geräten ---------------------------------------
def default_gateway(proc_root="/proc"):
    try:
        with open(os.path.join(proc_root, "net/route")) as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) > 3 and parts[1] == "00000000" and int(parts[3], 16) & 2:
                    g = bytes.fromhex(parts[2])[::-1]
                    return ".".join(str(b) for b in g)
    except (OSError, ValueError):
        pass
    return None


def local_ip():
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))           # sendet nichts, ermittelt nur die eigene Adresse
            return s.getsockname()[0]
    except OSError:
        return ""


def check_host(host, timeout=2):
    """(erreichbar, Millisekunden). host = Name/IP (Ping) oder Name:Port (TCP-Verbindung)."""
    import socket
    m = re.fullmatch(r"(.+):(\d{1,5})", host)
    if m and not host.count(":") > 1:
        t0 = time.monotonic()
        try:
            with socket.create_connection((m.group(1), int(m.group(2))), timeout=timeout):
                return True, (time.monotonic() - t0) * 1000
        except OSError:
            return False, None
    if host.startswith("-"):
        return False, None                   # wäre eine ping-Option
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", str(timeout), "--", host], capture_output=True, text=True,
                           timeout=timeout + 3, env=dict(os.environ, LC_ALL="C"))
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    ms = re.search(r"time[=<]([\d.]+)\s*ms", r.stdout)
    return r.returncode == 0, float(ms.group(1)) if ms else None


class NetworkPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 60, log)

    def enabled(self):
        return "network" in (self.get_settings().get("pages") or [])

    def signature(self):
        return json.dumps((self.get_settings().get("network") or {}).get("hosts"), sort_keys=True)

    def fetch(self):
        hosts = [h for h in (self.get_settings().get("network") or {}).get("hosts") or []
                 if isinstance(h, dict) and str(h.get("host") or "").strip()][:12]
        results = [None] * len(hosts)

        def work(i, h):
            host = str(h["host"]).strip()
            if host == "gateway":
                host = default_gateway() or ""
            ok, ms = check_host(host) if host else (False, None)
            results[i] = {"name": h.get("name") or host, "host": host or "(kein Router gefunden)", "ok": ok, "ms": ms}
        threads = [threading.Thread(target=work, args=(i, h), daemon=True) for i, h in enumerate(hosts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        return {"hosts": [r for r in results if r], "ip": local_ip()}
