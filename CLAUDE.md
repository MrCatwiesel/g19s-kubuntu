# Hinweise für Claude (Projektgedächtnis)

Kurzfassung für neue Sitzungen. Details zu Aufbau, Erweitern und Tests stehen in
[ENTWICKLUNG.md](ENTWICKLUNG.md), die Anleitung für Nutzer in `doku/wiki_vorlage.txt`.

## Zusammenarbeit
- Immer **auf Deutsch** antworten.
- Nutzer: Kubuntu 26.04, KDE Plasma (Wayland), echte Logitech G19s, Home `/home/mde`.
  Er testet am echten Gerät und schickt `journalctl --user -u g19s -n 150 --no-pager`.
- Größere Änderungen erst vorschlagen und besprechen, dann umsetzen („Leg los“/„Ja“ = umsetzen).
- Nach jeder fertigen Version: `dist/g19s.py`, `dist/g19s-gui.py` und
  `dist/G19s_unter_Kubuntu.wiki` an den Nutzer senden, dazu eine knappe Zusammenfassung.

## Ablauf einer Version
1. Quellen in `src/` ändern (nie `dist/` direkt).
2. Version in **beiden** Dateien erhöhen: `src/treiber/kopf.py` und `src/verwaltung/server/kopf.py`
   (Schema `JJJJ.MM.TT-N`, N ab 1 je Tag).
3. Doku nachziehen: `doku/wiki_vorlage.txt`, ggf. `README.md`, `ENTWICKLUNG.md`, und in
   **`NEUIGKEITEN.md`** einen Abschnitt `## <Version>` mit Stichpunkten für Nutzer anlegen
   (wird Release-Text und „Was ist neu“; ohne ihn schlägt der Release-Job fehl).
4. `python3 build.py && python3 tests/run_tests.py` – alle Testgruppen müssen grün sein.
   Gewollte Anzeigeänderung: `run_tests.py bilder --referenz` (neue PNGs ansehen!),
   neue Simulation: `run_tests.py sim=s14 --referenz`.
5. Commit mit `git -c user.name="G19s" commit`, Nachricht deutsch, mit den Attributionszeilen
   der Sitzung; `git push origin main`. GitHub Actions testet und legt auf `main` das Release
   `v<Version>` an – erst dann findet „Nach Updates suchen“ die Version.

## Stolperfallen
- `pkill -f` mit einem Muster, das in der eigenen Befehlszeile steht, beendet die Shell –
  Muster mit `[.]` schreiben (z. B. `g19s-gui[.]py`).
- `run_tests.py` räumt alte Fake-Server (Ports 8811/8812) und Verwaltungen (8799) selbst ab.
- Tests brauchen `pip install -r tests/anforderungen.txt` und `fonts-dejavu-extra` (sonst weichen
  12 Uhren-Bilder ab); in der Sandbox ggf. `apt-get install -y fonts-dejavu-extra`.
- Aus der Sandbox ist `raw.githubusercontent.com` nicht erreichbar; die Update-Suche wird
  mit dem Fake-GitHub (`G19S_UPDATE_URL`, `tests/fakes/infodienste.py`) getestet.

## Stand (2026.11.05-5)
- Alle Punkte der Prüfung Sicherheit/Lesbarkeit/Performance umgesetzt; L7 (Umbenennung
  profile→layer) bewusst verworfen.
- 2026.09.30-5: Update direkt von GitHub (Dienst & Sicherung → „Nach Updates suchen“),
  Live-Vorschau der Zifferblätter im Uhr-MENU.
- 2026.10.01-1: Tastatur abziehen/Ruhezustand ohne Treiber-Neustart (`Keyboard` in
  `src/treiber/geraet.py`), Sim `s14_abziehen`. Am echten Gerät bestätigt: Abziehen bei
  laufendem Radio (Ton läuft weiter, Seite kommt wieder), Zifferblatt-Vorschau,
  „Nach Updates suchen“ gegen echtes GitHub, Ruhezustand.
- 2026.10.01-2: Update-Suche über GitHub-Releases mit „Was ist neu“ (`NEUIGKEITEN.md`),
  GitHub Actions (`.github/workflows/tests.yml`: Tests bei jedem Push, Release auf `main`).
- 2026.10.01-3: Texte über die Zwischenablage einfügen (`src/treiber/zwischenablage.py`, Klipper per
  `qdbus6`, ersatzweise `wl-copy`; `"paste": "ctrl+v"|"ctrl+shift+v"` bei G-Taste „Text“ und Textbausteinen,
  Zurückholen per `paste_restore`), Sim `s15_zwischenablage`. Klipper-D-Bus am echten Gerät geprüft (qdbus6 + Strg+V ok).
- 2026.10.01-4: Text bleibt nach dem Einfügen in der Zwischenablage (`paste_restore` Standard aus –
  Nutzer fügt mehrfach selbst mit Strg+V ein, auch per RDP), Mehrfachdruck ohne Sperre (Generationszähler),
  0,3 s vor Strg+V, Version beim Start und jedes Einfügen im Protokoll; Sim `s16_zwischenablage_bleibt`.
- 2026.10.01-5: Einzelner Textbaustein direkt auf G-Taste (`{"snippets": "*", "snippet": "<Name>"}`, jeder Druck
  fügt ein; Verweis über den Namen wie in `snippet_list`), Liste bleibt nach OK offen (`"keep_open": true`);
  Sim `s17_textbaustein_direkt`. Anlass: Nutzer erwartete bei G-Taste „Textbausteine“ Einfügen bei jedem Druck.
- 2026.10.01-6: Ursache „G-Taste nur einmal“ gefunden (am echten Gerät mit --debug): Die G19s meldet das
  Loslassen einer G-Taste nicht in Report 0x02 – derselbe Report `02 01 00 40` kommt beim nächsten Druck erneut,
  M-Tasten melden das Loslassen normal. Treiber: gleicher Report 0x02 = erneuter Druck, Report 0x03 nur Nullen =
  G-Tasten los (`handle_gm_report`/`_apply_gm` in `src/treiber/app_tasten.py`); --debug zeigt jetzt auch 0x03.
  Sim `s18_g19s_loslassen`.
- 2026.10.01-7: Eigentliche Ursache (Protokoll --debug 2026-10-02): Die G19s schickt oft **zwei Reports in einem Paket**,
  0x03 (7 Bytes) + 0x02 (4 Bytes), z. B. `03 3a 00 00 00 00 00 02 00 00 40` (F1 + los) oder `03 00 … 02 80 00 40`
  (leer + G8 gedrückt). Der alte Code las nur den ersten Report → G8 (unbelegt, F20) 4× gedrückt = 1× F20.
  `split_gm_reports` in `src/treiber/app_tasten.py` zerlegt nach `GM_REPORT_LEN`; Regeln aus -6 bleiben als Rückfall.
  --debug trennt Reports mit `|`. Sim `s19_reports_geklebt` (echte Pakete). Am Gerät bestätigt mit -6: G1 mehrfach
  (getippt und Klipper), Liste „offen lassen“ (mehrmals OK), Einfügen per G-Taste in RDP.
- 2026.10.01-8: Medientasten (Rad, Stumm, Play/Pause, Next, Prev, Stop) übernimmt der Treiber exklusiv
  (`src/treiber/medientasten.py`, `MediaKeys`: evdev-Gerät „G19s Gaming Keyboard Consumer Control“ 046d:c228 ohne
  KEY_A, `grab()`), damit sie im RDP (xfreerdp schaltet KDE-Kürzel ab) lokal wirken. Ausführung in
  `handle_media_key` (app_tasten): `volume_change` (aktionen, Display + KDE-OSD per qdbus6 osdService),
  Medien über `media.control` bzw. `playerctl_any`; fremde Tasten des Geräts über uinput weiter. Einstellung
  `media_keys` (Standard an, Verwaltung „Beleuchtung & Display → Lautstärke“). Nutzer wählte Variante A (immer)
  statt B (nur bei aktivem RDP-Fenster, bräuchte KWin-Skript). Sim `s20_medientasten`; im Harness läuft der
  Faden nur mit `media_keys=True`. Geräte am echten Rechner: event3 Tastatur, event4 Consumer Control.
  Am echten Gerät bestätigt (2026-10-02): Medientasten im RDP, Zwischenablage weiter ok.
- 2026.11.04-1: SETTINGS kurz/lang (Wunsch Nutzer: „Optionstaste“ = SETTINGS). Lang (`LONG_PRESS` 0,6 s, ab 2026.11.05-1 auf Wunsch 1,0 s;
  `settings_key_tick` in `tick`, öffnet schon beim Halten) = Profilauswahl überall; kurz auf der Uhrseite =
  `ClockMenu`, sonst Profilauswahl. Entscheidung beim Loslassen (`settings_down` in app_tasten). s03/s09/s12 nutzen
  jetzt langen Druck, Sim `s21_settings_kurz_lang`. Idee für später (vorgeschlagen, nicht beauftragt): Optionen des
  Zifferblatts (CLOCK_OPTIONS) am Gerät ändern, z. B. aus der Zifferblatt-Vorschau heraus.
- 2026.11.05-2 (Nutzer wählte aus Vorschlägen 1+2+6+7+8): mpv-Puffer (`MPV_BUFFER` in `_build_cmd`, nicht bei eigenen
  `--cache`/`--demuxer-*`); Zifferblatt-Optionen am Gerät (`ClockOptionsMenu`, ► in `ClockMenu`, `clock_option_list`/
  `option_next`/`option_text`, Farben `CLOCK_COLOR_CHOICES`, Speichern über neues `save_setting(path, value)` in app_kern
  inkl. sofortigem reload/apply); Haltebalken (`settings_hold`, `render_hold_bar`, ab `HOLD_BAR_AFTER` 0,25 s);
  `QuickMenu` per MENU auf Seiten ohne eigenes MENU (macros, weather, hardware): Helligkeit ±10, Nachtmodus
  `night.enabled`, Diashow toggle, `start_screensaver`, Profil; Ebenen-Einblendung `_layer_overlay` →
  `render_layer_keys` (2 s, Einstellung `layer_overlay`, nicht auf Makros-Seite/nachts/bei Menü). s07 schaltet die
  Einblendung ab; Sim `s22_bedienung`. Idee (nicht umgesetzt): SETTINGS kurz außerhalb der Uhr = Schnellmenü statt Profil.
- 2026.11.05-3: Seite „Visualisierung“ (`visual`, letzte in PAGE_IDS, anfangs nicht in den Seitenlisten). `SoundAnalyzer`
  (`klanganalyse.py`): pw-record mit `-P '{ stream.capture.sink = true … }' -` (Monitor des Ausgangs; am echten Gerät
  noch NICHT geprüft, ob pw-record „-“ als stdout und die Eigenschaft so annimmt – sonst parec @DEFAULT_MONITOR@),
  nur solange `want()` (IDLE_STOP 2 s). 8 Stile in `seite_visual.py` (@vis_style), Stil global in settings.json
  `visual.style` (bewusst nicht je Profil/Ebene, um macros.json/Verwaltung nicht anzufassen), Optionen VISUAL_OPTIONS.
  `OptionsMenu(section, item, back)` ersetzt ClockOptionsMenu (für "clock" und "visual"), `VisualMenu`, SETTINGS kurz
  auf visual = Stile. Tastaturlicht im Takt `_visual_backlight` (visual.backlight, Standard an, Nutzerwunsch).
  Verwaltung: Karte „Visualisierung“ (`11c_visual.js`, `optionFields` aus 11b_uhr.js gemeinsam). Tests:
  Fake `tests/fakes/bin/pw-record` (Python, Kick alle 0,5 s), Sim `s23_visualisierung`, `test_klanganalyse.py`,
  Bilder `vis_*`. Footer-Punkte aller Referenzbilder geändert (12 Seiten).
- 2026.11.05-4: Nutzer: „nach Stumm zeigt Visualisierung weiterhin an“ – der PipeWire-Monitor ist vor Mute/Lautstärke
  (Beleg, dass der Ausgang und nicht das Mikrofon mitgehört wird). `SoundAnalyzer` fragt jede Sekunde
  `change_volume("get")`; stumm oder 0 % → `muted`, inaktiv, Seite zeigt „Ton stumm“. Fake-wpctl: `$S/sinkmute`.
- 2026.11.05-5: Nutzer: „Tanzendes Mädchen ziemlich träge“ (am Gerät mit Radio). Schlagerkennung `_detect_beat`
  (Verhältnis 1,3 + steigend ODER Fluss > Mittel+1,5σ; Tempo `period` = Median der Abstände), Tänzerin bewegt sich
  phasengekoppelt (Knie, Gewicht, Arme, Kopf) und macht ohne erkannten Schlag nach 1,6 Perioden selbst den nächsten
  Schritt. Am Gerät zuvor bestätigt: Visualisierung läuft, ruhige Leerlauf-Bewegung bei Stumm („leichte Bewegungen“).
  Nutzer gefragt, ob Leerlauf ganz still / Uhr / so bleiben soll – Antwort offen.
- Beobachtet: Benachrichtigungen erscheinen im Journal doppelt (vermutlich sendet Plasma zweimal) – harmlos.
- Beobachtet (2026-10-02): RDP-Sitzung (xfreerdp/sdl-freerdp 3.32.0 → Windows-PC) brach beim Kopieren bzw.
  ~10 s nach dem Login ab: `cliprdr … Error was 1359 → Network disconnect`. Ursache ist ein FreeRDP-Fehler bei
  **Dateien** in der Zwischenablage (Windows meldet FileGroupDescriptorW/FileContents, KDE fragt text/uri-list an).
  Nicht der G19s-Treiber. Lösung: `/clipboard:files-to:off` beim xfreerdp-Aufruf, Text geht weiter in beide
  Richtungen (nötig für Einfügen per G-Taste in RDP). `direction-to:remote` hilft nicht, `-clipboard` verhindert
  das Einfügen. Bei Ärger mit Einfügen in RDP zuerst den xfreerdp-Aufruf prüfen.

## Offene Punkte
1. Zu 2026.11.05-3 (Journal 2026-11-05 13:41): pw-record startet und läuft (kein „hat sich beendet“) – „-“ als stdout
   wird also angenommen. NOCH OFFEN: hört es wirklich den Ausgang (Monitor) und nicht das Mikrofon? Test erbeten:
   Radio aus + ins Mikrofon sprechen → muss „Keine Wiedergabe“ bleiben; `pactl list source-outputs | grep -iE
   'source|G19s'` bzw. `wpctl status` (Streams). Außerdem Takt/Tastaturlicht, CPU (`ps -o pcpu,rss,args -C python3,pw-record`).
   Beobachtet im selben Journal (Lauf 12:17–13:39, Version -2): 6:51 min CPU in 82 min, memory peak 945 MB (cgroup,
   inkl. mpv und Seitencache – Diashow lädt 1217 Piwigo-Bilder); viele Timeouts von Piwigo/Radio-Titel und einmal
   DNS-Fehler → Netzproblem, nicht Treiber. Nutzer hat im Schnellmenü „Nachtmodus (Zeitplan)“ auf an gelassen.
   Zu 2026.11.05-2: Haltebalken, Zifferblatt-Optionen (►), Schnellmenü (Makros/Wetter/Hardware),
   Einblendung bei M1/M2/M3, mpv-Speicher am Gerät BESTÄTIGT (2026-11-05: nach 1:18 h 84 MB RSS statt
   ~311 MB, Befehlszeile endet mit den --demuxer-Optionen).
   Zu 2026.11.04-1: SETTINGS kurz/lang (Haltezeit seit -05-1 1 s).
   Offen zu 2026.10.01-8: erscheint außerhalb von RDP auch die KDE-Lautstärkeanzeige (osdService unter Plasma 6)?
   Nutzer bestätigte nur die Prozentanzeige auf dem G19s-Display.
   Dazu aus -7: G1 und unbelegte G-Taste mit --debug mehrmals schnell – je ein „gedrückt“/„losgelassen“.
2. Verbrauch (2026-10-02): Messung 18:23–20:18 – g19s.py 150 MB und g19s-gui.py 92 MB stabil (kein Leck); mpv
   158→311 MB = Demuxer-Cache (Standard 150 MiB) läuft beim Radio voll → in 2026.11.05-2 begrenzt (bestätigt: 84 MB nach 1:18 h). systemd „Consumed“ zählt Treiber + mpv + Hilfs-
   programme. Die 24 min CPU in 68 min am Vormittag sind damit nicht erklärt – bei Wiederholung `ps -o etime,time,
   rss,pcpu,args -C python3,mpv` erbitten.
3. `install.sh` (mit `--deinstallieren`).
4. Knopf „Vorherige Version wiederherstellen“ (Sicherungen in `~/.local/share/g19s/alte-versionen`).
5. Optional: täglicher Update-Hinweis auf der Displayseite „Updates“ (abschaltbar).
