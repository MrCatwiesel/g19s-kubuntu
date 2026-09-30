"""Hardware-Werte: Temperaturen und Lüfter (hwmon, nvidia-smi), Netzwerk, Datenträger, CPU/RAM."""


# --- Hardware-Sensoren (hwmon) ------------------------------------------------
class Hardware:
    def __init__(self, sys_root="/sys", proc_root="/proc"):
        self.sys, self.proc = sys_root, proc_root
        self._net = None
        self._nvidia = (0.0, None)

    def _read(self, path):
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return None

    def sensors(self):
        """{"cpu": °C, "gpu": °C, "gpu_load": %, "nvme": °C, "fans": [(Name, U/min)]}"""
        import glob
        out = {"cpu": None, "gpu": None, "gpu_load": None, "nvme": None, "fans": []}
        for hw in sorted(glob.glob(os.path.join(self.sys, "class/hwmon/hwmon*"))):
            name = self._read(os.path.join(hw, "name")) or ""
            temps = {}
            for f in sorted(glob.glob(os.path.join(hw, "temp*_input"))):
                v = self._read(f)
                label = self._read(f.replace("_input", "_label")) or os.path.basename(f).split("_")[0]
                if v and v.lstrip("-").isdigit():
                    temps[label] = int(v) / 1000
            if name in ("k10temp", "zenpower", "coretemp", "cpu_thermal") and temps and out["cpu"] is None:
                for pref in ("Tctl", "Tdie", "Package id 0", "Tccd1"):
                    if pref in temps:
                        out["cpu"] = temps[pref]
                        break
                else:
                    out["cpu"] = max(temps.values())
            elif name in ("amdgpu", "nouveau", "radeon") and temps and out["gpu"] is None:
                out["gpu"] = temps.get("edge") or temps.get("junction") or max(temps.values())
            elif name == "nvme" and temps and out["nvme"] is None:
                out["nvme"] = temps.get("Composite") or max(temps.values())
            for f in sorted(glob.glob(os.path.join(hw, "fan*_input"))):
                v = self._read(f)
                if v and v.isdigit() and int(v) > 0:
                    label = self._read(f.replace("_input", "_label")) or f"Lüfter {os.path.basename(f)[3:-6]}"
                    out["fans"].append((label, int(v)))
        for f in sorted(glob.glob(os.path.join(self.sys, "class/drm/card*/device/gpu_busy_percent"))):
            v = self._read(f)
            if v and v.isdigit():
                out["gpu_load"] = int(v)
                break
        if out["gpu"] is None:
            self._nvidia_query(out)
        return out

    def _nvidia_query(self, out):
        import shutil
        now = time.monotonic()
        if now - self._nvidia[0] > 30:          # nvidia-smi ist teuer und kann die Grafikkarte wecken
            val = None
            if shutil.which("nvidia-smi"):
                try:
                    r = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
                                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
                    t, u = [x.strip() for x in r.stdout.splitlines()[0].split(",")[:2]]
                    val = (float(t), int(float(u)))
                except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                    val = None
            self._nvidia = (now, val)
        if self._nvidia[1]:
            out["gpu"], out["gpu_load"] = self._nvidia[1]

    def network(self):
        """Datenrate in Bytes/s (empfangen, gesendet) seit dem letzten Aufruf."""
        rx = tx = 0
        try:
            with open(os.path.join(self.proc, "net/dev")) as f:
                for line in f.readlines()[2:]:
                    iface, data = line.split(":", 1)
                    iface = iface.strip()
                    if iface == "lo" or iface.startswith(("docker", "veth", "virbr", "br-")):
                        continue
                    v = data.split()
                    rx += int(v[0])
                    tx += int(v[8])
        except (OSError, ValueError, IndexError):
            return None
        now = time.monotonic()
        prev, self._net = self._net, (now, rx, tx)
        if not prev or now - prev[0] <= 0:
            return 0.0, 0.0
        dt_ = now - prev[0]
        return max(0.0, (rx - prev[1]) / dt_), max(0.0, (tx - prev[2]) / dt_)

    @staticmethod
    def disks():
        seen, out = set(), []
        for label, path in (("System", "/"), ("Home", os.path.expanduser("~"))):
            try:
                st = os.statvfs(path)
                dev = os.stat(path).st_dev
            except OSError:
                continue
            if dev in seen:
                continue
            seen.add(dev)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            if total:
                out.append((label, (total - free) / total * 100, total))
        return out


# --------------------------------------------------------------------------- #
# Systemwerte (ohne Zusatzpakete, direkt aus /proc)
# --------------------------------------------------------------------------- #
class Stats:
    def __init__(self):
        self._prev = self._cpu_times()

    @staticmethod
    def _cpu_times():
        with open("/proc/stat") as f:
            vals = [int(x) for x in f.readline().split()[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return sum(vals), idle

    def cpu_percent(self):
        total, idle = self._cpu_times()
        pt, pi = self._prev
        self._prev = (total, idle)
        dt = total - pt
        return 0.0 if dt <= 0 else max(0.0, min(100.0, 100.0 * (1 - (idle - pi) / dt)))

    @staticmethod
    def memory():
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, val = line.split(":", 1)
                info[key] = int(val.split()[0])  # kB
        total = info["MemTotal"]
        used = total - info.get("MemAvailable", info.get("MemFree", 0))
        return used / 1048576, total / 1048576, 100.0 * used / total

    @staticmethod
    def load():
        return os.getloadavg()
