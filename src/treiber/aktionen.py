"""G-Tasten-Aktionen: welcher Eintrag in macros.json was auslöst.

Die Art eines Eintrags bestimmt entry_type() (Reihenfolge in ENTRY_TYPES, makros.py);
GKEY_ACTIONS ordnet jeder Art ihre Ausführung zu. Ohne Art sendet die Taste F13–F24
(bzw. mit Strg/Alt in M2/M3) für KDE-Kurzbefehle. Neue Aktion: Art in ENTRY_TYPES
eintragen und hier mit @gkey_action("art") anmelden.
"""

GKEY_ACTIONS = {}


def gkey_action(*types):
    """Ausführung für Einträge der Art(en) types anmelden."""
    def deco(fn):
        for t in types:
            GKEY_ACTIONS[t] = fn
        return fn
    return deco


@gkey_action("timer")
def act_timer(app, macro, name):
    tcfg = macro["timer"]
    if app.timer.alarm:
        app.dismiss_alarm()
    elif app.timer.same(tcfg):
        if app.menu is not None and app.menu.kind == "timer":
            app.timer.toggle()
        else:
            app.menu = TimerView()
    else:
        app.timer.start(tcfg)
        app.log(f"{timer_label(tcfg)} gestartet")
        app.menu = TimerView()
    app.flash = None
    app.next_draw = 0


@gkey_action("snippets")
def act_snippets(app, macro, name):
    if app.menu is not None and app.menu.kind == "snippets":
        app.menu = None                     # zweiter Druck schließt die Liste
    elif app.snippet_list(macro["snippets"]):
        app.menu = SnippetMenu(macro["snippets"], entry_label(macro, app.settings()))
        app.flash = None
    else:
        app.show("Textbausteine", ["keine Textbausteine", "in der Verwaltung anlegen"], PROFILE_COLOR[app.layer], 2.5)
    app.next_draw = 0


@gkey_action("open", "run")
def act_open_run(app, macro, name):
    label = str(macro.get("name") or macro.get("open") or "Befehl")
    if macro.get("open"):
        cmd, verb = ["xdg-open", str(macro["open"])], "Öffne"
    else:
        cmd, verb = str(macro["run"]), "Starte"
    if app.launcher.start(cmd):
        app.show(verb, [label], PROFILE_COLOR[app.layer], 1.5)
        app.log(f"{name}: {verb} {label}")
    else:
        app.show("Fehler", [f"{label} ließ sich", "nicht starten"], REC_COLOR, 3)


@gkey_action("radio")
def act_radio(app, macro, name):
    cur = app.radio.current()
    if macro["radio"] == "stop" or (cur and cur["url"] == macro["radio"]):
        app.radio.stop()                    # „Radio aus“ bzw. gleiche Taste nochmal = aus
        app.show("Radio", ["ausgeschaltet"], app.renderer.DIM, 1.5)
    else:
        station = next((s for s in app.settings().get("stations", []) if s.get("url") == macro["radio"]),
                       {"name": macro.get("name", ""), "url": macro["radio"]})
        app.radio_play(station)
    app.media.wake.set()


def act_remember_song(app, macro, name):
    app.media.refresh()                     # aktuellen Titel holen (im Hintergrund evtl. 5 s alt)
    info = app.media.snapshot()[0]
    entry = remember_song(info, app.radio.current())
    if entry:
        app.log(f"Song gemerkt: {entry['artist']} – {entry['title']}")
        app.show("♥ Gemerkt", [entry["title"] or entry["artist"], entry["artist"] if entry["title"] else ""],
                 PROFILE_COLOR[app.layer], 2.5)
    else:
        app.show("Song merken", ["schon gemerkt" if info else "es läuft nichts"], PROFILE_COLOR[app.layer], 1.8)


@gkey_action("media")
def act_media(app, macro, name):
    if macro["media"] == "remember":
        return act_remember_song(app, macro, name)
    threading.Thread(target=app.media.control, args=(macro["media"],), daemon=True).start()


@gkey_action("mic")
def act_mic(app, macro, name):
    color = PROFILE_COLOR[app.layer]

    def work():
        state = mic_state(app.launcher._env(), toggle=True)
        if state is None:
            app.show("Mikrofon", ["wpctl/pactl nicht gefunden"], REC_COLOR, 3)
            return
        app.mic.update(muted=state, known=True, changed=True)
        app.renderer.mic_muted = state
        app.log("Mikrofon " + ("stumm" if state else "an"))
        app.popup(lambda: app.renderer.render_mic(state, color), 1.5)
    threading.Thread(target=work, daemon=True).start()


@gkey_action("sleep")
def act_sleep(app, macro, name):
    sleep = app.sleep
    if sleep["until"]:
        sleep["until"] = 0.0
        app.renderer.sleep_badge = ""
        app.show("Einschlaftimer", ["aus"], PROFILE_COLOR[app.layer], 1.8)
        app.log("Einschlaftimer aus")
    else:
        try:
            minutes = max(1, min(240, int(macro["sleep"])))
        except (TypeError, ValueError):
            minutes = 30
        sleep.update(until=time.monotonic() + minutes * 60, minutes=minutes)
        info = app.media.snapshot()[0]
        if not app.radio.playing and not (info and info.get("status") == "Playing"):
            args = ("play-pause",) if app.last_station else ("next",)   # zuletzt gehörten bzw. ersten Sender starten
            threading.Thread(target=app.radio_control, args=args, daemon=True).start()
        app.show("Einschlaftimer", [f"Musik aus in {minutes} Min.", "gleiche Taste = abbrechen"], PROFILE_COLOR[app.layer], 2.5)
        app.log(f"Einschlaftimer: {minutes} Minuten")
    app.next_draw = 0


@gkey_action("volume")
def act_volume(app, macro, name):
    action, color = macro["volume"], PROFILE_COLOR[app.layer]

    def work():
        res = change_volume(action, app.settings().get("volume_step", 5), app.launcher._env())
        if res:
            pct, muted = res
            app.popup(lambda: app.renderer.render_volume(pct, muted, color), 1.6)
        else:
            app.show("Lautstärke", ["wpctl/pactl nicht gefunden"], REC_COLOR, 3)
    threading.Thread(target=work, daemon=True).start()


@gkey_action("text", "combo", "steps")
def act_keys(app, macro, name):
    if app.args.debug:
        print(f"  {name} -> „{entry_label(macro, app.settings())}“")
    if not app.player.play(compile_steps(macro, app.log)):
        app.log("Es läuft bereits ein Makro – ignoriert")


def run_gkey_action(app, macro, name):
    """Passende Aktion ausführen. False = keine Aktion (Taste sendet F13–F24)."""
    fn = GKEY_ACTIONS.get(entry_type(macro))
    if fn is None:
        return False
    fn(app, macro, name)
    return True


assert set(GKEY_ACTIONS) == set(ENTRY_TYPES), \
    f"G-Tasten-Arten ohne Ausführung: {set(ENTRY_TYPES) - set(GKEY_ACTIONS)}"
