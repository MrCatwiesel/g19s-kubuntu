"""HTTP-Routen: Treiberdienst, Sicherung, Update, Beenden."""


class ApiService:
    # -- API: Dienst ------------------------------------------------------- #
    def api_get_service(self, q):
        self._send(200, {"status": service_status(), "log": service_log()})

    def api_post_service(self, q):
        service_action(self._json().get("action"))
        time.sleep(0.8)
        self._send(200, {"status": service_status(), "log": service_log()})

    # -- API: Sicherung ---------------------------------------------------- #
    def api_get_backup(self, q):
        data = make_backup()
        name = f"g19s-sicherung-{datetime.datetime.now():%Y-%m-%d}.tar.gz"
        self._send(200, data, "application/gzip",
                   {"Content-Disposition": f'attachment; filename="{name}"'})

    def _backup_cfg(self):
        """Sicherungsziel aus der Anfrage (Formular, noch nicht gespeichert) oder aus settings.json."""
        body = self._json() if self.headers.get("Content-Length") not in (None, "0") else {}
        cfg = body.get("backup") if isinstance(body.get("backup"), dict) else {}
        if not cfg and body.get("folder"):                   # ältere Seite: nur Ordner
            cfg = {"target": "folder", "folder": body["folder"], "keep": body.get("keep")}
        return g.SCHEMA["backup"].clean(cfg or g.load_settings()["backup"], False)

    def api_post_backup_now(self, q):
        b = self._backup_cfg()
        try:
            path = g.auto_backup(b, b["keep"], HOME)
        except OSError as ex:
            g.save_state(last_backup_error=str(ex))
            raise RuntimeError(str(ex))
        g.save_state(last_backup=time.time(), last_backup_file=path, last_backup_error="")
        self._send(200, {"path": path})

    def api_post_backup_test(self, q):
        try:
            msg = g.test_backup_target(self._backup_cfg())
        except OSError as ex:
            raise RuntimeError(str(ex))
        self._send(200, {"message": msg})

    def api_get_backup_status(self, q):
        st = g.load_state()
        self._send(200, {"last": st.get("last_backup"), "file": st.get("last_backup_file", ""),
                         "error": st.get("last_backup_error", "")})

    def api_get_backupinfo(self, q):
        self._send(200, {"files": backup_members()})

    def api_post_restore(self, q):
        raw = self._body()
        if q.get("inspect") == ["1"]:
            return self._send(200, restore_backup(raw, inspect=True))
        restored, safety = restore_backup(raw, programs=q.get("programs") == ["1"])
        self._send(200, {"restored": restored, "safety": safety})

    def api_get_versions(self, q):
        self._send(200, {"driver": file_version(os.path.join(HERE, "g19s.py")),
                         "driver_running": getattr(g, "VERSION", "älter"),
                         "gui": VERSION, "backups": UPDATE_BACKUP_DIR})

    def api_post_update(self, q):
        body = self._json()
        files = []
        for f in body.get("files") or []:
            try:
                files.append((str(f.get("name") or "datei.py"), base64.b64decode(f.get("data") or "")))
            except (ValueError, TypeError):
                raise ValueError("Datei konnte nicht gelesen werden")
        if not files:
            raise ValueError("Keine Datei ausgewählt")
        result = install_update(files)
        comps = {r["component"] for r in result}
        if "driver" in comps:
            try:
                service_action("restart")
            except RuntimeError as ex:
                for r in result:
                    if r["component"] == "driver":
                        r["warning"] = f"Treiber-Neustart fehlgeschlagen: {ex}"
        restart_gui = "gui" in comps
        self._send(200, {"installed": result, "restart_gui": restart_gui})
        if restart_gui:
            backup = next(r["backup"] for r in result if r["component"] == "gui")
            self.app.restart = {"backup": backup}
            threading.Thread(target=lambda: (time.sleep(0.4), self.app.server.shutdown()),
                             daemon=True).start()

    def api_post_quit(self, q):
        self._send(200, {"ok": True})
        threading.Thread(target=lambda: (time.sleep(0.2), self.app.server.shutdown()), daemon=True).start()

    def api_post_bye(self, q):
        self.app.last_contact = time.monotonic() - IDLE_TIMEOUT + 5   # bald beenden
        self._send(200, {"ok": True})
