"""Start der Verwaltung: vorhandene Instanz finden, Server starten, Browserfenster öffnen, Neustart nach Update."""


# --------------------------------------------------------------------------- #
# Start
# --------------------------------------------------------------------------- #
def open_window(url, browser=None):
    if browser:
        cmd = shlex.split(browser) + [url]
    else:
        cmd = None
        for b in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                  "brave-browser", "microsoft-edge"):
            if shutil.which(b):
                cmd = [b, f"--app={url}", "--window-size=1200,860"]
                break
        if cmd is None:
            cmd = ["xdg-open", url]
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as ex:
        print(f"Browser konnte nicht geöffnet werden ({ex}). Adresse: {url}")


def _local(path, info, data=None, timeout=2):
    req = urllib.request.Request(f"http://127.0.0.1:{info['port']}{path}", data=data,
                                 headers={"X-Token": info["token"]})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def existing_instance():
    """Laufende Verwaltung derselben Version finden. Eine ältere Version wird beendet,
    damit nach einem Update nicht versehentlich die alte Oberfläche erscheint."""
    try:
        with open(INSTANCE_FILE) as f:
            info = json.load(f)
        state = _local("/api/poll", info)
    except Exception:
        return None
    if state.get("version") == VERSION:
        return info
    print(f"Ältere Verwaltung ({state.get('version') or 'ohne Version'}) wird beendet …", flush=True)
    try:
        _local("/api/quit", info, data=b"{}")
    except Exception:
        try:
            os.kill(int(info.get("pid")), signal.SIGTERM)    # alte Versionen ohne /api/quit
        except (OSError, TypeError, ValueError):
            pass
    for _ in range(30):
        time.sleep(0.2)
        try:
            _local("/api/poll", info, timeout=0.5)
        except Exception:
            break
    return None


def bind_server(port, tries=40):
    """Beim Neustart nach einem Update ist der Port evtl. noch kurz belegt."""
    for i in range(tries):
        try:
            return http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            if not port or i == tries - 1:
                raise
            time.sleep(0.25)


def restart_after_update(app, args):
    """Neue Verwaltung mit gleicher Adresse starten; startet sie nicht, alte Version zurückholen."""
    script = os.path.realpath(__file__)
    cmd = [sys.executable, script, "--restarted", "--port", str(app.port), "--token", app.token]
    backup = (app.restart or {}).get("backup")
    for attempt in ("neu", "zurück"):
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Neue Verwaltung läuft." if attempt == "neu" else "Alte Verwaltung wiederhergestellt.", flush=True)
            return
        if attempt == "neu" and backup and os.path.exists(backup):
            print("Neue Verwaltung startet nicht – stelle die vorherige Version wieder her.", flush=True)
            shutil.copy2(backup, script)
        else:
            return


def install_desktop():
    path = os.path.join(HOME, ".local/share/applications/g19s-gui.desktop")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    script = os.path.realpath(__file__)
    with open(path, "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\n"
                "Type=Application\n"
                "Name=G19s-Verwaltung\n"
                "GenericName=Tastatur-Einstellungen\n"
                "Comment=Logitech G19s: G-Tasten, Makros, Radiosender und Display verwalten\n"
                f"Exec=/usr/bin/python3 {shlex.quote(script)}\n"
                "Icon=input-keyboard\n"
                "Terminal=false\n"
                "Categories=Settings;HardwareSettings;Utility;\n"
                "Keywords=Logitech;G19;Tastatur;Makro;Radio;\n")
    subprocess.run(["update-desktop-database", os.path.dirname(path)],
                   capture_output=True) if shutil.which("update-desktop-database") else None
    print(f"Menüeintrag angelegt: {path}")


def main():
    ap = argparse.ArgumentParser(description="Grafische Verwaltung für die Logitech G19s")
    ap.add_argument("--no-browser", action="store_true", help="Browser nicht öffnen")
    ap.add_argument("--browser", help="Browserbefehl, z. B. 'firefox --new-window'")
    ap.add_argument("--port", type=int, default=0, help="fester Port (Standard: zufällig)")
    ap.add_argument("--token", help=argparse.SUPPRESS)
    ap.add_argument("--restarted", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--install-desktop", action="store_true",
                    help="Eintrag im Anwendungsmenü anlegen")
    args = ap.parse_args()

    if args.install_desktop:
        install_desktop()
        return

    if args.restarted:
        args.no_browser = True
    info = None if args.no_browser else existing_instance()
    if info:
        open_window(f"http://127.0.0.1:{info['port']}/#{info['token']}", args.browser)
        return

    try:
        g.migrate_files()                   # ältere settings.json/macros.json umstellen (wie der Treiber)
    except (OSError, ValueError) as ex:
        print(f"Umstellung älterer Dateien nicht möglich: {ex}")
    app = App(args.token or secrets.token_urlsafe(24))
    Handler.app = app
    server = bind_server(args.port)
    server.daemon_threads = True
    app.port = server.server_address[1]
    app.server = server
    url = f"http://127.0.0.1:{app.port}/#{app.token}"

    try:
        fd = os.open(INSTANCE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"port": app.port, "token": app.token, "pid": os.getpid()}, f)
    except OSError:
        pass

    def watchdog():
        while True:
            time.sleep(3)
            now = time.monotonic()
            if app.first_contact is None:
                if (args.restarted or not args.no_browser) and now - app.started > FIRST_CONTACT_TIMEOUT:
                    break
            elif now - app.last_contact > IDLE_TIMEOUT:
                break
        server.shutdown()

    threading.Thread(target=watchdog, daemon=True).start()
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown).start())

    print(f"G19s-Verwaltung läuft: {url}", flush=True)
    if not args.no_browser:
        open_window(url, args.browser)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        test_radio.stop()
        server.server_close()
        try:
            with open(INSTANCE_FILE) as f:
                if json.load(f).get("pid") == os.getpid():
                    os.remove(INSTANCE_FILE)
        except (OSError, ValueError):
            pass
        if app.restart:
            restart_after_update(app, args)
        else:
            print("G19s-Verwaltung beendet.")


PAGE_HTML = r'''@@PAGE_HTML@@'''

if __name__ == "__main__":
    main()
