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
      piwigo … sicherung      Dienste (Radio, Diashow, Wetter, Kalender, RSS, Unwetter, …)
      anzeige_basis           Renderer-Grundlage, @page / @page_keys
      seite_*.py              je Displayseite: Zeichnen + Tasten
      uhr_basis, uhr_*.py     Zifferblätter der Seite „Uhr“ (@clock_face), 25 Stück
      menues, einblendungen   Zeichnen von Menüs und Einblendungen
      menue_logik             Menü-Klassen (Tasten + draw)
      aktionen                G-Tasten-Aktionen (@gkey_action)
      app_kern / app_tasten / app_zeit / app
                              App = AppCore + KeyHandling + TimedTasks
    src/verwaltung/server/  Module der Verwaltung (HTTP-Handler aus Api*-Mixins)
    src/verwaltung/seite/   geruest.html + stil.css + js/*.js (nach Dateiname sortiert)
    doku/wiki_vorlage.txt   Wiki-Text mit Platzhaltern @@G19S_PY@@, @@GUI_PY@@, …
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
| `gui` | Verwaltung im Browser (Playwright/Chromium) | `gui/*_test.py` |

Einzelne Teile: `run_tests.py bilder sim`, `run_tests.py sim=s05`.
Nach einer gewollten Änderung der Anzeige: `run_tests.py --referenz` (danach die neuen
PNGs ansehen!). Die Tests laufen ohne Tastatur: `tests/stubs` ersetzt evdev,
`tests/fakes` spielt Piwigo, CalDAV/RSS/Bright Sky, GitHub (Update-Suche über
`G19S_UPDATE_URL`, Dateien aus `$G19S_TEST_ROOT/upd/gh/`) und Programme wie `apt`, `ping`, `wpctl`.
libfaketime wird beim ersten Lauf nach `tests/.werkzeuge/` gebaut.

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
