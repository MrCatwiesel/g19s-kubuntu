"""KDE-Benachrichtigungen mitlesen (dbus-monitor)."""


# --------------------------------------------------------------------------- #
# Benachrichtigungen: KDE-Meldungen mitlesen (dbus-monitor)
# --------------------------------------------------------------------------- #
class NotificationWatcher(threading.Thread):
    """Beobachtet org.freedesktop.Notifications.Notify auf dem Sitzungsbus."""

    RULE = "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"

    def __init__(self, env_func, on_notify, log=print):
        super().__init__(daemon=True)
        self.env_func, self.on_notify, self.log = env_func, on_notify, log
        self.running = True
        self.proc = None

    def stop(self):
        self.running = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    @staticmethod
    def parse(lines):
        """Wertet dbus-monitor-Ausgabe aus und liefert (App, Titel, Text) je Meldung."""
        args, cur, active = [], None, False
        for line in lines:
            line = line.rstrip("\n")
            if cur is not None:                       # mehrzeiliger String
                if line.endswith('"'):
                    cur.append(line[:-1])
                    args.append("\n".join(cur))
                    cur = None
                else:
                    cur.append(line)
                continue
            if line.startswith(("method call", "signal", "method return", "error")):
                if active and len(args) >= 3:
                    yield NotificationWatcher._emit(args)
                active = "member=Notify" in line
                args = []
                continue
            if not active:
                continue
            m = re.match(r'^\s{3}string "(.*)$', line)
            if m and len(args) < 4:
                rest = m.group(1)
                if rest.endswith('"'):
                    args.append(rest[:-1])
                else:
                    cur = [rest]
                if len(args) == 4:
                    yield NotificationWatcher._emit(args)
                    active, args = False, []
        if active and len(args) >= 3:
            yield NotificationWatcher._emit(args)

    @staticmethod
    def _emit(args):
        # Reihenfolge bei Notify: app_name, (replaces_id), app_icon, summary, body
        app, _icon, summary = args[0], args[1], args[2]
        body = args[3] if len(args) > 3 else ""
        body = re.sub(r"<[^>]+>", "", body)             # einfache HTML-Auszeichnung entfernen
        return app.strip(), summary.strip(), " ".join(body.split())

    def run(self):
        import shutil
        if not shutil.which("dbus-monitor"):
            self.log("Benachrichtigungen: dbus-monitor fehlt (Paket dbus-bin)")
            return
        while self.running:
            try:
                self.proc = subprocess.Popen(["dbus-monitor", "--session", self.RULE], env=self.env_func(),
                                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                                             errors="replace")
                for app, summary, body in self.parse(self.proc.stdout):
                    try:
                        self.on_notify(app, summary, body)
                    except Exception as ex:  # Sicherheitsnetz für den Rückruf in die Hauptanwendung
                        self.log(f"Benachrichtigung nicht angezeigt: {ex}")
            except OSError as ex:
                self.log(f"Benachrichtigungen nicht verfügbar: {ex}")
            for _ in range(20):                         # nach Abbruch in 10 s neu verbinden
                if not self.running:
                    return
                time.sleep(0.5)
