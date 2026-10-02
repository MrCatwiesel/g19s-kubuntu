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

## Stand (2026.10.01-7)
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
- Beobachtet: Benachrichtigungen erscheinen im Journal doppelt (vermutlich sendet Plasma zweimal) – harmlos.
- Beobachtet (2026-10-02): RDP-Sitzung (xfreerdp/sdl-freerdp 3.32.0 → Windows-PC) brach beim Kopieren bzw.
  ~10 s nach dem Login ab: `cliprdr … Error was 1359 → Network disconnect`. Ursache ist ein FreeRDP-Fehler bei
  **Dateien** in der Zwischenablage (Windows meldet FileGroupDescriptorW/FileContents, KDE fragt text/uri-list an).
  Nicht der G19s-Treiber. Lösung: `/clipboard:files-to:off` beim xfreerdp-Aufruf, Text geht weiter in beide
  Richtungen (nötig für Einfügen per G-Taste in RDP). `direction-to:remote` hilft nicht, `-clipboard` verhindert
  das Einfügen. Bei Ärger mit Einfügen in RDP zuerst den xfreerdp-Aufruf prüfen.

## Offene Punkte
1. Rückmeldung zu 2026.10.01-7: mit --debug G1 und eine unbelegte G-Taste (z. B. G8) je mehrmals schnell drücken –
   jeder Druck muss genau einmal „gedrückt“ und „losgelassen“ zeigen.
2. Hoher Verbrauch beobachtet (2026-10-02): 24 min CPU in 68 min, bis 599 MB Speicher (normal: ~100 MB, wenig CPU);
   lief u. a. Diashow (13 Bilder). Ursache noch unklar – Nutzer fragen, welche Seite lief, dann Code prüfen.
3. `install.sh` (mit `--deinstallieren`).
4. Knopf „Vorherige Version wiederherstellen“ (Sicherungen in `~/.local/share/g19s/alte-versionen`).
5. Optional: täglicher Update-Hinweis auf der Displayseite „Updates“ (abschaltbar).
