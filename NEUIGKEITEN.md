# Neuigkeiten

Was sich je Version geändert hat. Der Abschnitt einer Version erscheint in der Verwaltung unter
„Nach Updates suchen → Was ist neu“ und als Text des GitHub-Releases.

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
