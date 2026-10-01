# Neuigkeiten

Was sich je Version geändert hat. Der Abschnitt einer Version erscheint in der Verwaltung unter
„Nach Updates suchen → Was ist neu“ und als Text des GitHub-Releases.

## 2026.10.01-6
- Fehler behoben: Eine G-Taste löste manchmal nur beim ersten Druck aus und erst nach einem Wechsel der Ebene (M1/M2/M3) wieder einmal. Ursache: Die G19s meldet das Loslassen einer G-Taste nicht immer; der Treiber hielt die Taste deshalb für weiter gedrückt. Jetzt zählt jeder Druck – für Textbausteine, Texte und alle anderen Belegungen.
- Mit `--debug` erscheinen alle Tasten-Reports der Tastatur im Protokoll (auch Report 0x03).

## 2026.10.01-5
- Ein einzelner Textbaustein lässt sich jetzt direkt auf eine G-Taste legen: Jeder Druck fügt ihn sofort ein, ohne Liste und ohne OK. Im Tasten-Editor unter „Textbausteine“ den Eintrag „Direkt einfügen: <Name>“ wählen.
- Neue Option „Liste nach dem Einfügen offen lassen“ für G-Tasten mit Textbaustein-Liste: Nach OK bleibt die Liste stehen, so lässt sich mehrmals einfügen oder gleich der nächste Baustein wählen. BACK oder die G-Taste schließen sie.
- Wird ein direkt belegter Textbaustein gelöscht oder umbenannt, meldet das Display „… fehlt“, und die Verwaltung weist darauf hin.

## 2026.10.01-4
- Fehler behoben: Nach dem Einfügen über die Zwischenablage bleibt der Text jetzt in der Zwischenablage – wie beim Kopieren lässt er sich mit Strg+V beliebig oft an weiteren Stellen einfügen, auch im Remote-Desktop-Fenster. Bisher wurde nach einer Sekunde der vorherige Inhalt zurückgeholt; das ist jetzt ausgeschaltet und im Reiter „Textbausteine“ wieder einschaltbar.
- Mehrmals schnell hintereinander gedrückte G-Tasten fügen jeden Text ein, keiner wird mehr ignoriert.
- Etwas mehr Zeit vor Strg+V, damit Remote-Desktop-Programme die Zwischenablage sicher übernommen haben.
- Das Protokoll zeigt beim Start die Version und bei jedem Einfügen Taste, Weg und Zeichenzahl (nicht den Text).

## 2026.10.01-3
- Texte können jetzt über die Zwischenablage eingefügt werden statt Zeichen für Zeichen getippt – schnell und mit allen Zeichen, auch Emojis, „“ und –. Gilt für G-Tasten mit Text und für Textbausteine, wählbar je Text; neue Texte nutzen die Zwischenablage, bestehende werden weiter getippt.
- Für die Konsole gibt es die Einfügeart „Strg+Umschalt+V“.
- Der vorherige Inhalt der Zwischenablage wird nach dem Einfügen zurückgeholt (abschaltbar im Reiter „Textbausteine“).

## 2026.10.01-2
- „Nach Updates suchen“ holt neue Versionen jetzt aus den GitHub-Releases und zeigt unter „Was ist neu“, was sich geändert hat – auch über mehrere übersprungene Versionen hinweg.
- Eine Version wird erst veröffentlicht, wenn alle automatischen Tests auf GitHub bestanden sind.
- Die heruntergeladenen Dateien werden zusätzlich darauf geprüft, ob ihre Versionsnummer zum Release passt.
