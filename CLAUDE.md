# Hinweise für Claude

Kurzfassung für neue Sitzungen. Details zu Aufbau, Erweitern und Tests stehen in
[ENTWICKLUNG.md](ENTWICKLUNG.md), die Anleitung für Nutzer in `doku/wiki_vorlage.txt`,
die Änderungen je Version in [NEUIGKEITEN.md](NEUIGKEITEN.md).

## Projektgedächtnis
Versionsgeschichte mit Hintergründen, Beobachtungen am echten Gerät und offene Punkte stehen
**nicht** hier (das Repository ist öffentlich), sondern in der privaten Projekt-Doku des
claude.ai-Projekts: `claude/g19s-projektgedaechtnis.md` – zu Beginn mit dem Projects-Werkzeug
lesen (`project_read`) und nach jeder Version fortschreiben (`project_write` auf denselben Pfad).
Ohne Zugriff darauf: nur aus Code, Tests und NEUIGKEITEN.md arbeiten.

## Zusammenarbeit
- Immer **auf Deutsch** antworten.
- Der Nutzer testet am echten Gerät und schickt `journalctl --user -u g19s -n 150 --no-pager`.
- Größere Änderungen erst vorschlagen und besprechen, dann umsetzen („Leg los“/„Ja“ = umsetzen).
- Nach jeder fertigen Version: `dist/g19s.py`, `dist/g19s-gui.py` und
  `dist/G19s_unter_Kubuntu.wiki` an den Nutzer senden, dazu eine knappe Zusammenfassung.
- Keine persönlichen Angaben (Pfade, Rechnernamen, Journalauszüge) in Dateien des Repositorys schreiben.

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
6. Projektgedächtnis (siehe oben) um einen Eintrag zur Version ergänzen.

## Stolperfallen
- `pkill -f` mit einem Muster, das in der eigenen Befehlszeile steht, beendet die Shell –
  Muster mit `[.]` schreiben (z. B. `g19s-gui[.]py`).
- `run_tests.py` räumt alte Fake-Server (Ports 8811/8812) und Verwaltungen (8799) selbst ab.
- Tests brauchen `pip install -r tests/anforderungen.txt` und `fonts-dejavu-extra` (sonst weichen
  12 Uhren-Bilder ab); in der Sandbox ggf. `apt-get install -y fonts-dejavu-extra`.
- Aus der Sandbox ist `raw.githubusercontent.com` nicht erreichbar; die Update-Suche wird
  mit dem Fake-GitHub (`G19S_UPDATE_URL`, `tests/fakes/infodienste.py`) getestet.
- Die Visualisierung hört den Ausgang über `pw-record` mit; in den Tests ersetzt
  `tests/fakes/bin/pw-record` das Programm (Musik, Stille `$S/pw-record.still`, Sprache `$S/pw-record.speech`).
