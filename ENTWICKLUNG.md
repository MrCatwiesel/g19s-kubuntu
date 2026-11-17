# Entwicklung: Projektquellen

Aus diesem Ordner entstehen die drei ausgelieferten Dateien:

| Datei | Inhalt |
|---|---|
| `dist/g19s.py` | Treiber (Display, G-/M-Tasten, Makros, Seiten, Dienste) |
| `dist/g19s-gui.py` | Verwaltung (lokaler HTTP-Server + Browser-Oberfläche) |
| `dist/G19s_unter_Kubuntu.wiki` | MediaWiki-Seite mit beiden Programmen eingebettet |

Ausgeliefert wird weiterhin **je eine Datei**; die Aufteilung in Module gibt es nur hier.

## Bauen

    python3 build.py

`build.py` hängt die Module in der Reihenfolge aus `REIHENFOLGE` aneinander, sammelt die
Importe oben, macht aus jedem Modul-Docstring einen Kommentarkopf (`# ═══…` / `# Modul <name>`)
und prüft das Ergebnis: Syntax, doppelte Namen auf oberster Ebene, undefinierte Namen,
gleiche `VERSION` in beiden Programmen, Endzeile `# G19S-DATEIENDE …`.
Die Version steht in `src/treiber/kopf.py` und `src/verwaltung/server/kopf.py`.

## Aufbau

    src/treiber/            Module des Treibers, Reihenfolge in REIHENFOLGE
      kopf, konstanten        Version, Pfade, USB-Konstanten, Seitenliste
      einstellungen           SCHEMA: ein Schema für alle Einstellungen
      makros, tastatur, …     Makrodatei, Tastennamen, Makro-Abspieler
      zwischenablage          Texte über die Zwischenablage einfügen (Klipper/wl-copy, Strg+V)
      medientasten            Lautstärkerad/Medientasten exklusiv übernehmen (Consumer-Control-Gerät, grab)
      piwigo … sicherung      Dienste (Radio, Diashow, Wetter, Kalender, RSS, Unwetter, …)
      videos                  Video-Feeds (VideoPoller, parse_video_feed) und VideoPlayer: ffmpeg → Rohbilder 320×180;
                              eigene Listen (video_list_items), YouTube (youtube_id, youtube_lookup/oEmbed, parse_youtube_feed),
                              yt-dlp (ytdlp_path, ytdlp_resolve, VideoPlayer.play_youtube), ThumbCache (Vorschaubilder, reduce statt resize)
                              über eine Pipe + Ton an PulseAudio; Pause/Spulen = Neustart mit -ss
      seite_video             Seite „Video“: Quellen (video_sources, MENU wechselt), Folgen-/Listenansicht, Wiedergabe, Tasten;
                              video_open (Browser oder Display), _video_next (automatisch weiter), video_play_list (G-Taste list:Name)
      klanganalyse            Ausgang mithören (pw-record), FFT/Bänder/Takt/Sprache für die Visualisierung
      anzeige_basis           Renderer-Grundlage, @page / @page_keys
      seite_*.py              je Displayseite: Zeichnen + Tasten
      uhr_basis, uhr_*.py     Zifferblätter der Seite „Uhr“ (@clock_face), 25 Stück
      seite_visual            Seite „Visualisierung“, 12 Stile (@vis_style), Optionen VISUAL_OPTIONS
      seite_visual_xmas       Stil „Weihnachten“: schattierte Figuren (_blob/_limb, IK _ik), Baum, Schnee,
                              Auftritte (_xmas_actors: Ziel/Zustand je Figur, Seite neu = _vis_enter)
      seite_visual_licht      Bühnenlicht-Effekte (Mixin StageFx): FX_ALL, Programme FX_PROGRAMS (Tänzerin) und
                              FX_LIGHTS (Lichtshow), _fx_update/_fx_back/_fx_figure/_fx_front, vis_stage_color
      seite_visual_ballett    Stil „Tänzerin“ (dancer, Mixin BalletVisual): Studio, Figur aus _blob/_ik, Haltungen
                              BAL_POSES/BAL_CHOREO, Langeweile BAL_BORED, Rock mit Feder/Dämpfung (_bal_skirt)
      seite_visual_feier      Weihnachten, Option „Feierabend“ (Mixin XmasParty): Runde mit Pegel (Prosten),
                              zufälligen Gags PARTY_GAGS (party_eligible), Schluss PARTY_END, Sprüche PARTY_LINES;
                              je Gag _party_<name> (Ziele/Zustände p_*, Requisiten); Uhrzeit über party_clock()
      seite_visual_xmasfun    Weihnachten: jugendfreie Gags FUN_GAGS ohne Feierabend (_xmas_fun, Plan P mit
                              family=True) und Feierabend-Gags FEIER_EXTRA; Requisiten _xmas_fun_ground/_over/_after
      seite_visual_burg       Stil „Mittelalter-Metal“ (metal, Mixin MetalVisual): Band MT_BAND, Feuerkörbe, Publikum,
                              Pyro/Drache beim Höhepunkt, Gags MT_GAGS, Herold, Hofnarr, Blitz bei Gewitter
      seite_visual_ostern     Stil „Ostern“ (easter, Mixin EasterVisual): Eierfabrik, ES_GAGS; Festkalender fest_days()
      seite_visual_halloween  Stil „Halloween“ (halloween, Mixin HalloweenVisual): Skelettband HW_BAND, Kürbischor, HW_GAGS
      seite_visual_horror     Stil „Horror“ (horror, Mixin HorrorVisual): Haus (_hr_house) und Puppenzimmer (_hr_dolls), HR_GAGS je Schauplatz
      seite_visual_geburtstag Stil „Geburtstag“ (birthday, Mixin BirthdayVisual): lebende Torte, _bd_person(Altersstufe), BD_GAGS
      seite_visual_muttertag  Stil „Muttertag“ (mother, Mixin MotherVisual): Küche, Arme je Lautstärke (st["extra"]), MO_GAGS
      seite_visual_maennertag Stil „Männertag“ (father, Mixin FatherVisual): Grill, Bollerwagen (_fa_cart), FA_GAGS
      seite_visual_figur      FigureKit: _fig (Person mit Pose, Hut, Mund), fig_dance_pose, Feuerwerk _fx_burst/_fx_step/_fx_draw
      seite_visual_silvester  Stil „Silvester“ (newyear): Tafel mit Countdown (fest_now), Raketen, NY_GAGS
      seite_visual_fasching   Stil „Fasching“ (carnival): Umzugswagen, Funkengarde, Kamelle, CV_GAGS
      seite_visual_oktoberfest Stil „Oktoberfest“: Blaskapelle, schunkelnde Gäste, OK_GAGS
      seite_visual_martin     Stil „St. Martin“ (martin): Laternenumzug, Martinsfeuer, SM_GAGS
      seite_visual_valentin   Stil „Valentinstag“ (valentine): Dinner, Amor, VL_GAGS
      seite_visual_unterwasser Stil „Unterwasser-Band“ (underwater): Oktopus, Quallen, Fischschwarm, UW_GAGS
      seite_visual_bauernhof  Stil „Bauernhof-Band“ (farm): Kuh, Schwein, Hühner, Traktor, FM_GAGS
      seite_visual_weltraum   Stil „Weltraum-Disco“ (space): Ringplanet, Astronauten, SP_GAGS
      seite_visual_arcade     Stil „Retro-Arcade“ (arcade): halbe Auflösung (AR_W×AR_H), Aliens, AR_GAGS
      seite_visual_western    Stil „Western-Saloon“ (western): Klavier, Schwingtüren, Tresen, WS_GAGS
      seite_visual_lagerfeuer Stil „Lagerfeuer“ (campfire): ruhig, ohne Gags; Feuer st["flame"], Glühwürmchen, Eule
      seite_visual_katzen     Stil „Katzenchor“ (cats): vier Katzen = Frequenzbänder, KC_GAGS
      seite_visual_jazz       Stil „Lounge / Jazz-Club“ (jazz): Kontrabass, Solist, Bistrotisch, JZ_GAGS, vis_col_jazz
      seite_visual_walzer_orte Walzer, Orte (Mixin WaltzPlaces): je Ort Ebenen (_wz_paint_<ort> → Landschaft, Leuchten,
                              Schnee-, Wassermaske), _wz_backdrop setzt Himmel/Licht/Wetter zusammen (Cache je Lichtstufe),
                              eigene Fotos WALTZ_PHOTO_DIR/<ort>.jpg (_wz_photo; Verwaltung: save_waltz_photo)
      seite_visual_walzer     Stil „Walzer“ (waltz, Mixin WaltzVisual): Paar _wz_couple/_wz_person (Blickrichtung als
                              Vektor, Figurenebene mit Licht eingefärbt), Kleidung WZ_OUTFITS, Gags WZ_GAGS/WZ_PLACE_GAG;
                              Paar in WZ_SS-facher Auflösung (_wz_ss_begin/_wz_ss_pose/_wz_ss_end), Taktphase st["ph"]
                              läuft gleichmäßig, Schläge ziehen sie nur nach (WZ_PHASE_PULL), Tempo geglättet
      seite_visual_stimmung   Stimmungsbilder silk, ember, pulse (Mixin MoodVisual): ruhig, ohne Gags, Bass träge (_mood_state)
      seite_visual_auto       Pseudo-Stil „auto“ (AutoVisual): auto_mood, AUTO_POOLS, vis_auto_inner; cover_color/COVER_STYLES; _vis_weather_fx/WEATHER_FX_STYLES
      seite_visual_szenen     Szenen der bewegten Vorschau (vis_scenes, vis_force; Server: vorschau.render_scene)
      seite_visual_party      Stil „Überraschungsparty“ (party, Mixin PartyVisual): Phasen hide/surprise/party
                              (_pt_new_round), Gags PT_GAGS, Gäste _pt_guest, Hund, Torte, Kastenteufel, Konfetti
      seite_visual_keller     Stil „Kellertreppe“ (cellar, Mixin CellarVisual): Pendel der Glühbirne, Licht als
                              Maske mit Wandschatten (_cl_light), Augen CL_EYES, Höhepunkt CL_BOOM, Gags CL_GAGS
      seite_visual_gruft      Bewohner der Kellertreppe (Mixin CellarCrew): Zombies/Skelett je Stufe (CL_CREW,
                              Zustände under/rise/idle/sink/gone bzw. hidden/out/flee), Treppenhöhe _cl_surface,
                              Zombie-Gags _cl_zombie_gag, Besuch _cl_visitor (Hausverwalter, Vampir, Mumie)
      hilfen                  u. a. Festkalender: fest_today() (Tests ersetzen), birthdays_today, fest_occasion
      menues, einblendungen   Zeichnen von Menüs und Einblendungen
      menue_logik             Menü-Klassen (Tasten + draw)
      aktionen                G-Tasten-Aktionen (@gkey_action)
      app_kern / app_tasten / app_zeit / app
                              App = AppCore + KeyHandling + TimedTasks
    src/verwaltung/server/  Module der Verwaltung (HTTP-Handler aus Api*-Mixins)
    src/verwaltung/seite/   geruest.html + stil.css + js/*.js (nach Dateiname sortiert)
    doku/wiki_vorlage.txt   Wiki-Text mit Platzhaltern @@G19S_PY@@, @@GUI_PY@@, …
    src/installer/install.sh  Vorlage des Installers (→ dist/install.sh, Release-Datei; Test: tests/einheit/test_installer.py)
    dateien/                udev-Regel, systemd-Dienst, Beispiel-Makros
    tests/                  siehe unten

Die Verwaltung lädt den Treiber als Modul (`load_driver` in `server/kopf.py`) und benutzt
dessen Schema, Renderer und Dienste – es gibt keine doppelten Prüfregeln.

## Erweitern

**Neue Displayseite**
1. ID und Namen in `konstanten.py` eintragen (`PAGE_IDS`, `PAGE_NAMES`, ggf. `DEFAULT_PAGE_ORDER`).
2. `src/treiber/seite_xyz.py` anlegen: Mixin-Klasse mit
   `@page("xyz") def render_xyz(self, layer, keys): …` und optional
   `@page_keys("xyz") def keys_xyz(app, pressed): … return True` (True = Taste verbraucht).
3. Modul in `REIHENFOLGE` vor `menues` eintragen und die Klasse in `anzeige.py` bei `Renderer` ergänzen.
   `anzeige.py` prüft beim Start, dass jede Seite angemeldet ist.
4. In der Verwaltung erscheint die Seite automatisch in der Seitenauswahl.

**Neue G-Tasten-Aktion** – in `aktionen.py`:

    @gkey_action(lambda m: m.get("meine_aktion"))
    def act_meine(app, macro, name):
        …

Die Reihenfolge der Einträge ist die Priorität. In der Verwaltung kommt die Auswahl in
`seite/js/` (Aktionsliste) und die Prüfung in `clean_macros` (`makros.py`).

**Neue Einstellung** – ein Feld in `SCHEMA` (`einstellungen.py`), z. B.
`"meins": Section({"an": Bool(False), "wert": Int(5, 1, 60, zero=False)})`.
Standardwert, Treiber (tolerant) und Verwaltung (streng) sind damit fertig; nur das
Formular in `seite/js/` fehlt noch. Regeln über mehrere Felder: `Section(..., check)` oder
`@_strict_rule`.

**Neues Zifferblatt für die Uhr**
1. Name in `CLOCK_FACES` (`konstanten.py`) eintragen – die Reihenfolge ist die des Displaymenüs.
2. In einem `uhr_*.py`-Modul eine Methode `@clock_face("id", fps=1) def face_id(self, profile)`;
   Zeit nur über `self._clock_now()`, Optionen über `self._copt("id")` (siehe Docstring in `uhr_basis.py`).
3. Optional Einstellungen in `CLOCK_OPTIONS` – Schema und Formular der Verwaltung entstehen daraus.
4. Ansehen: `python3 tests/uhren_vorschau.py id --gross` (baut in eine Temp-Datei, zeigt Zeichenzeiten).
   `anzeige.py` prüft beim Start, dass jedes Zifferblatt eine Zeichenfunktion hat.

**Neuer Menüpunkt am Display** – Klasse aus `Menu`/`PickMenu` in `menue_logik.py`
(`on_key`, `draw`) und `app.menu = MeinMenu()` setzen.

## Tests

    python3 build.py && python3 tests/run_tests.py

| Teil | Was | Dateien |
|---|---|---|
| `einheit` | Kalender, Texte, Einstellungen/Schema, Dienste, Uhren (jedes Zifferblatt zu Grenzzeiten), Sicherung (Ordner/Nextcloud/WebDAV/SMB), Sicherheit | `einheit/test_*.py` |
| `bilder` | jede Displayseite, jedes Zifferblatt, Einblendungen als PNG, pixelgenau gegen `golden/ref` (feste Zeit per libfaketime) | `golden/scenes.py` |
| `sim` | Bediensimulationen (Tasten, Menüs, Timer, Profile, Aufnahme, Zifferblatt) gegen `sim/erwartet` | `sim/s*.py` |

In den Simulationen läuft der Medientasten-Faden nur mit `Sim(..., media_keys=True)` (s20).
| `gui` | Verwaltung im Browser (Playwright/Chromium) | `gui/*_test.py` |

Einzelne Teile: `run_tests.py bilder sim`, `run_tests.py sim=s05`.
Nach einer gewollten Änderung der Anzeige: `run_tests.py --referenz` (danach die neuen
PNGs ansehen!). Die Tests laufen ohne Tastatur: `tests/stubs` ersetzt evdev,
`tests/fakes` spielt Piwigo, CalDAV/RSS/Bright Sky, `ffmpeg` (Testbilder statt Video, `$G19S_TEST_ROOT/state/ffmpeg.log`), Video-Feed `/video.xml`, YouTube-oEmbed `/oembed` und Playlist-Feed `/feeds/videos.xml` (`G19S_YOUTUBE_URL`),
Klipper/`wl-copy` (`qdbus6`, `wl-copy`, `wl-paste`; Inhalt in `$G19S_TEST_ROOT/state/zwischenablage`),
GitHub (Release-API für die Update-Suche über
`G19S_UPDATE_URL`: Liste aus `$G19S_TEST_ROOT/upd/gh/releases.json`, Dateien aus `upd/gh/<tag>/`,
Download per Weiterleitung auf einen anderen Host wie bei GitHub) und Programme wie `apt`, `ping`, `wpctl`.
libfaketime wird beim ersten Lauf nach `tests/.werkzeuge/` gebaut.

**Voraussetzungen:** Python-Pakete aus `tests/anforderungen.txt` (feste Versionen, damit die
Referenzbilder pixelgleich bleiben), Chromium für Playwright und die Schriften `fonts-dejavu-core`
und `fonts-dejavu-extra` – fehlt `fonts-dejavu-extra`, weichen die Uhren-Bilder ab.

### GitHub Actions und Releases

`.github/workflows/tests.yml` baut bei jedem Push, prüft, dass `dist/` zu `src/` passt, und führt
alle Tests aus (bei Fehlern liegen Bilder und Protokolle als Artefakt „testergebnisse“ bereit).
Auf `main` legt der Job `release` danach ein Release `v<VERSION>` mit `g19s.py`, `g19s-gui.py` und
der Wiki-Datei an – nur wenn es das Tag noch nicht gibt. Der Text kommt aus dem Abschnitt
`## <VERSION>` in `NEUIGKEITEN.md`; fehlt er, schlägt der Job fehl. Die Update-Suche der
Verwaltung liest nur veröffentlichte Releases (keine Entwürfe, keine Vorabversionen).

## Konventionen

- **Gemeinsamer Namensraum:** Treiber-Module importieren einander nicht. Standardbibliotheken, die
  mehrere Module brauchen, stehen in `kopf.py`; nur-lokale Importe im Modul selbst. Ein Modul darf Namen
  aus später geladenen Modulen nur *innerhalb von Funktionen* benutzen (zur Ladezeit gibt es sie noch nicht).
- **Neue Displayseiten-IDs nur hinten** an `PAGE_IDS` anhängen – die Startseite wird als Nummer gespeichert.
- **Verwaltung ↔ Treiber:** Die Verwaltung benutzt Treiber-Namen als `g.<name>`; `build.py` prüft, dass es
  jeden davon im Treiber gibt, und trägt die Liste in `DRIVER_API` ein (Meldung „zu alt“ bei alter `g19s.py`).
- **Daten von außen:** Abrufe über `http_get`/`open_url` (keine Zugangsdaten bei Weiterleitung auf fremde
  Server), Bilder über `open_remote_image` (Größenlimit), Fehlertexte über `err_text`.
- **Breite `except Exception`** nur mit Kommentar, warum hier jeder Fehler abgefangen wird.
- Nach `python3 build.py` immer `python3 tests/run_tests.py`; `dist/` wird mit eingecheckt.
