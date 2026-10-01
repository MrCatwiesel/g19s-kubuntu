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
3. Doku nachziehen: `doku/wiki_vorlage.txt`, ggf. `README.md`, `ENTWICKLUNG.md`.
4. `python3 build.py && python3 tests/run_tests.py` – alle Testgruppen müssen grün sein.
   Gewollte Anzeigeänderung: `run_tests.py bilder --referenz` (neue PNGs ansehen!),
   neue Simulation: `run_tests.py sim=s14 --referenz`.
5. Commit mit `git -c user.name="G19s" commit`, Nachricht deutsch, mit den Attributionszeilen
   der Sitzung; `git push origin main`.

## Stolperfallen
- `pkill -f` mit einem Muster, das in der eigenen Befehlszeile steht, beendet die Shell –
  Muster mit `[.]` schreiben (z. B. `g19s-gui[.]py`).
- `run_tests.py` räumt alte Fake-Server (Ports 8811/8812) und Verwaltungen (8799) selbst ab.
- Aus der Sandbox ist `raw.githubusercontent.com` nicht erreichbar; die Update-Suche wird
  mit dem Fake-GitHub (`G19S_UPDATE_URL`, `tests/fakes/infodienste.py`) getestet.

## Stand (2026.10.01-1)
- Alle Punkte der Prüfung Sicherheit/Lesbarkeit/Performance umgesetzt; L7 (Umbenennung
  profile→layer) bewusst verworfen.
- 2026.09.30-5: Update direkt von GitHub (Dienst & Sicherung → „Nach Updates suchen“),
  Live-Vorschau der Zifferblätter im Uhr-MENU.
- 2026.10.01-1: Tastatur abziehen/Ruhezustand ohne Treiber-Neustart (`Keyboard` in
  `src/treiber/geraet.py`), Sim `s14_abziehen`.

## Offene Punkte
1. Rückmeldung vom echten Gerät zu 2026.10.01-1 abwarten: Abziehen bei laufendem Radio,
   Zifferblatt-Vorschau, „Nach Updates suchen“ (echtes GitHub), Ruhezustand.
2. GitHub-Releases statt Hauptzweig für die Update-Suche, mit „Was ist neu“ – zusammen mit
3. GitHub Actions (Tests bei jedem Push).
4. `install.sh` (mit `--deinstallieren`).
5. Knopf „Vorherige Version wiederherstellen“ (Sicherungen in `~/.local/share/g19s/alte-versionen`).
6. Optional: täglicher Update-Hinweis auf der Displayseite „Updates“ (abschaltbar).
