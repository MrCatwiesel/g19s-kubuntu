"""Countdown, Stoppuhr und Pomodoro (Zustand und Zeitrechnung, ohne Anzeige)."""


def timer_label(cfg):
    mode = cfg.get("mode")
    if mode == "stopwatch":
        return "Stoppuhr"
    if mode == "pomodoro":
        return f"Pomodoro {_num(cfg.get('work'), 25):g}/{_num(cfg.get('break'), 5):g}"
    return f"Timer {fmt_minutes(cfg.get('minutes') or 5)}"


def _num(v, default):
    try:
        return float(v) if v else default
    except (TypeError, ValueError):
        return default


def fmt_minutes(m):
    m = _num(m, 5)
    return f"{m:g} min" if m >= 1 else f"{round(m * 60)} s"


def fmt_clock(seconds):
    seconds = max(0, int(round(seconds)))
    h, rest = divmod(seconds, 3600)
    return f"{h}:{rest // 60:02d}:{rest % 60:02d}" if h else f"{rest // 60:02d}:{rest % 60:02d}"


class Timer:
    """Countdown, Stoppuhr oder Pomodoro – wird von der Hauptschleife fortgeschrieben."""

    def __init__(self):
        self.cfg = None            # Aktionseintrag {"mode", "minutes" | "work", "break"}
        self.mode = None
        self.running = False
        self.alarm = False         # Countdown abgelaufen, wartet auf Bestätigung
        self.phase = "work"        # Pomodoro: work / break
        self.rounds = 0            # abgeschlossene Arbeitsphasen
        self.total = 0.0           # Länge der aktuellen Phase (s)
        self.acc = 0.0             # bisher gelaufene Zeit (s), ohne laufenden Abschnitt
        self.since = None          # Start des laufenden Abschnitts (monotonic)

    @property
    def active(self):
        return self.mode is not None

    def _phase_len(self):
        c = self.cfg or {}
        if self.mode == "pomodoro":
            return 60 * max(1 / 60, float(c.get("work" if self.phase == "work" else "break") or (25 if self.phase == "work" else 5)))
        if self.mode == "timer":
            return 60 * max(1 / 60, float(c.get("minutes") or 5))
        return 0.0

    def start(self, cfg):
        self.cfg = dict(cfg)
        self.mode = cfg.get("mode") if cfg.get("mode") in ("timer", "stopwatch", "pomodoro") else "timer"
        self.phase, self.rounds, self.alarm = "work", 0, False
        self.total, self.acc = self._phase_len(), 0.0
        self.running, self.since = True, time.monotonic()

    def same(self, cfg):
        return self.active and self.cfg == dict(cfg)

    def elapsed(self, now=None):
        now = now or time.monotonic()
        return self.acc + (now - self.since if self.running and self.since else 0.0)

    def remaining(self, now=None):
        return max(0.0, self.total - self.elapsed(now))

    def toggle(self):
        if not self.active or self.alarm:
            return
        if self.running:
            self.acc, self.running = self.elapsed(), False
        else:
            self.running, self.since = True, time.monotonic()

    def reset(self):
        """Stoppuhr auf 0 bzw. Timer/Pomodoro beenden."""
        if self.mode == "stopwatch":
            self.acc, self.since = 0.0, time.monotonic()
            return True
        self.stop()
        return False

    def stop(self):
        self.__init__()

    def add_minute(self):
        if self.mode in ("timer", "pomodoro") and not self.alarm:
            self.total += 60

    def tick(self, now):
        """Liefert "done" (Timer abgelaufen) bzw. "work"/"break" (Pomodoro-Phase gewechselt)."""
        if not self.running or self.mode == "stopwatch":
            return None
        if self.elapsed(now) < self.total:
            return None
        if self.mode == "timer":
            self.acc, self.running, self.alarm = self.total, False, True
            return "done"
        if self.phase == "work":
            self.rounds += 1
            self.phase = "break"
        else:
            self.phase = "work"
        self.total, self.acc, self.since = self._phase_len(), 0.0, now
        return self.phase

    def display_value(self, now=None):
        return self.elapsed(now) if self.mode == "stopwatch" else self.remaining(now)

    def badge(self, now=None):
        if not self.active:
            return ""
        if self.alarm:
            return "!00:00"
        state = "=" if not self.running else ("~" if self.mode == "pomodoro" and self.phase == "break" else "+")
        return state + fmt_clock(self.display_value(now))
