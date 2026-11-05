# Neuigkeiten

Was sich je Version geändert hat. Der Abschnitt einer Version erscheint in der Verwaltung unter
„Nach Updates suchen → Was ist neu“ und als Text des GitHub-Releases.

## 2026.11.05-15
- Visualisierung „Weihnachten“: Weihnachtsmann und Weihnachtsfrau verschwinden nicht mehr einfach. Wechselt der Tanz (Paar, er allein, sie allein), winkt die eine Figur zum Abschied und geht aus dem Bild – er nach links, sie nach rechts –, die andere kommt herein und winkt beim Ankommen. Zum Paartanz reichen sie sich die Hand, sobald beide da sind.
- Bei Wortbeiträgen gehen beide zur Bank und setzen sich (auch wer gerade nicht im Bild war, kommt dazu); bei Musik stehen sie wieder auf und tanzen weiter. Die Bank blendet weich ein und aus.
- Beim Öffnen der Visualisierungsseite kommen die beiden ins Bild gelaufen, Schritt für Schritt im Takt der Musik.

## 2026.11.05-14
- Installer: Liegen Treiber und Verwaltung neben `install.sh`, erkennt er sie jetzt am Inhalt – auch wenn der Browser sie z. B. als `g19s(1).py` gespeichert hat. Ist eine Version auf GitHub noch nicht fertig, sagt er das verständlich.

## 2026.11.05-13
- Nachtmodus „gedimmt“ ist nicht mehr träge: Bewegte Zifferblätter und die Visualisierung laufen nachts flüssig weiter (bisher nur 1 Bild pro Sekunde), das Display ist nur dunkler.
- Im gedimmten Nachtmodus wirkt der erste Tastendruck sofort (bisher machte er nur das Display hell). Bei „Display aus“ weckt der erste Druck weiterhin nur.

## 2026.11.05-12
- Visualisierung braucht deutlich weniger Rechenzeit: Bühne der Tänzerin und Lichtshow werden sparsamer gezeichnet (Tänzerin etwa halb so viel CPU), die Klanganalyse rechnet alle Frequenzbänder in einem Schritt.
- Neue Einstellung „Bildrate“ (10, 15, 20 oder 25 Bilder je Sekunde). Standard ist jetzt 15 statt 20 – wer es flüssiger mag, stellt 20 oder 25 ein.
- Erkennung von Wortbeiträgen nach Messwerten vom echten Radio verbessert: Moderation über Musik mit Bass gilt nicht mehr als Musik, ein kurzer Break im Song nicht als Sprache. Im Protokoll steht zusätzlich die Zahl der Lücken.

## 2026.11.05-11
- Neu: „Vorherige Version wiederherstellen“ unter „Dienst & Sicherung“. Die Verwaltung zeigt die zuletzt gesicherten Versionen und spielt die gewählte geprüft wieder ein – die jetzige Version wird dabei gesichert, man kann also auch wieder zurück.
- Aufgehoben werden die zehn neuesten Sicherungen je Programmteil; ältere werden automatisch gelöscht.

## 2026.11.05-10
- Neu: Installer für Linux. Ein Befehl genügt: `curl -fsSL https://github.com/MrCatwiesel/g19s-kubuntu/releases/latest/download/install.sh | bash` – er installiert Pakete (apt, dnf, pacman, zypper), Treiber, Verwaltung, Zugriffsrechte, Autostart und Menüeintrag und prüft die Tastatur. Erneut ausgeführt, aktualisiert er.
- Entfernen mit `bash ~/.local/share/g19s/install.sh --deinstallieren` (Einstellungen bleiben, mit `--alles` werden auch sie gelöscht).

## 2026.11.05-9
- Der Treiber bleibt kostenlos. Wer das Projekt unterstützen möchte, findet in der Verwaltung unter „Dienst & Sicherung“ (und in README und Wiki) einen freiwilligen Spendenlink über PayPal.

## 2026.11.05-8
- Neuer Stil „Weihnachten“: Weihnachtsmann und Weihnachtsfrau tanzen neben einem geschmückten Weihnachtsbaum im Schneefall – räumlich gezeichnet mit Licht und Schatten. Einzeln oder als Paar (sie dreht sich unter seinem Arm), auf Wunsch abwechselnd jede Minute.
- Die Lichterkette blinkt im Takt, der Stern leuchtet mit dem Bass, kräftige Schläge wirbeln den Schnee auf. Die Tastatur pulsiert rot und grün.
- Bei Nachrichten und Werbung setzen sich die beiden auf eine Bank: er liest die Wunschliste, sie trinkt Kakao.
- Vom 1. Advent bis zum 6. Januar zeigt die Visualisierung automatisch „Weihnachten“ (abschaltbar). Alles einstellbar unter „Beleuchtung & Display → Visualisierung“.

## 2026.11.05-7
- Visualisierung erkennt Wortbeiträge: Nachrichten und Moderation am Klang (Sprache statt Musik, nach etwa 4–6 Sekunden), Nachrichten und Werbung zusätzlich an Stichwörtern im Titel des Senders (einstellbar unter „Beleuchtung & Display → Visualisierung“).
- Bei Wortbeiträgen langweilt sich das tanzende Mädchen: Arme verschränken, gähnen, auf die Uhr schauen, mit dem Fuß tippen – nach 30 Sekunden setzt es sich auf den Bühnenrand und döst. Kommt wieder Musik, tanzt es weiter.
- Während eines Wortbeitrags pulsiert die Tastatur nicht.

## 2026.11.05-6
- Visualisierung ohne Ton: Statt einer leichten Bewegung bleibt jetzt das letzte Bild abgedunkelt stehen, mit dem Hinweis „Keine Wiedergabe“ bzw. „Ton stumm“. Mit der Musik geht es sofort weiter.

## 2026.11.05-5
- Visualisierung: Schläge werden auch bei dichter Musik (z. B. Rock, bei dem der Bass nie leise wird) zuverlässig erkannt, dazu das Tempo.
- Das tanzende Mädchen tanzt jetzt durchgehend im Takt: Es geht auf jedem Schlag in die Knie, verlagert das Gewicht von Seite zu Seite, schwingt Arme und Kopf und wechselt die Pose schneller. Wird ein Schlag nicht erkannt, tanzt es im Tempo weiter. Je lauter, desto größer die Bewegungen.

## 2026.11.05-4
- Visualisierung: Ist der Ton stumm geschaltet (Stummtaste) oder auf 0 %, kommt die Seite zur Ruhe, zeigt „Ton stumm“, und die Tastatur pulsiert nicht mehr. Bisher lief sie weiter, weil das Radio im Hintergrund weiterspielt.

## 2026.11.05-3
- Neu: Displayseite „Visualisierung“ – bewegt sich zu allem, was der Rechner gerade abspielt (Radio, Spotify, Browser …). Acht Stile: Grafik-Equalizer, Tanzendes Mädchen, Lichtshow, Oszilloskop, Kreis-Spektrum, VU-Meter, Spektrogramm und Feuerwerk.
- Stil wählen am Display mit MENU oder SETTINGS kurz, Rechts öffnet die Optionen des Stils. In der Verwaltung unter „Beleuchtung & Display → Visualisierung“ mit Vorschau.
- Die Tastaturbeleuchtung pulsiert im Takt mit, solange die Seite zu sehen ist (abschaltbar).
- Die Seite ist anfangs aus: unter „Displayseiten“ einschalten oder als Bildschirmschoner wählen. Der Ton wird nur mitgehört, solange die Seite zu sehen ist, und nirgends gespeichert.

## 2026.11.05-2
- Neu: Optionen der Zifferblätter direkt am Display ändern – in der Zifferblatt-Liste (Uhr: MENU oder SETTINGS kurz) öffnet Rechts die Optionen des markierten Zifferblatts, z. B. Sekunden, Datum, Farbe oder Darstellung. Das Zifferblatt läuft dabei als Vorschau mit, jede Änderung gilt sofort.
- Neu: Schnellmenü per MENU auf den Seiten Makros, Wetter und Hardware – Helligkeit, Nachtmodus ein/aus, Diashow pausieren, Bildschirmschoner sofort, Profil wählen.
- Neu: Nach dem Druck auf M1/M2/M3 zeigt das Display 2 Sekunden lang die Belegung der G-Tasten dieser Ebene. Abschaltbar unter „Beleuchtung & Display → Display“.
- Neu: Hält man SETTINGS, füllt sich ein Balken bis zur Profilauswahl.
- Radio mit mpv braucht deutlich weniger Arbeitsspeicher (kleiner Puffer statt bis zu 150 MiB). Eigene Puffer-Angaben im Player-Befehl haben Vorrang.

## 2026.11.05-1
- SETTINGS muss jetzt 1 Sekunde gehalten werden, um die Profilauswahl zu öffnen (bisher 0,6 s) – so öffnet ein etwas längerer kurzer Druck auf der Uhrseite nicht versehentlich die Profile.

## 2026.11.04-1
- Neu: Die Displaytaste SETTINGS kennt jetzt kurz und lang. Lang drücken (0,6 Sekunden) öffnet auf jeder Seite die Profilauswahl – sie erscheint schon, während die Taste noch gehalten wird.
- Auf der Uhrseite öffnet ein kurzer Druck auf SETTINGS die Liste der Zifferblätter mit Live-Vorschau (wie MENU). Auf allen anderen Seiten bleibt es bei der Profilauswahl.

## 2026.10.01-8
- Neu: Lautstärkerad, Stumm- und Medientasten der Tastatur steuert jetzt der Treiber. Sie wirken dadurch auch im Remote-Desktop (z. B. xfreerdp) auf diesen Rechner – bisher gingen sie dort verloren. Die Lautstärke erscheint groß auf dem G19s-Display und, soweit möglich, auch in der KDE-Anzeige.
- Play/Pause, Weiter, Zurück und Stopp steuern den angezeigten Player bzw. das G19s-Radio.
- Tippen, Tastenkürzel und die Zwischenablage sind davon nicht betroffen.
- Abschaltbar unter „Beleuchtung & Display → Lautstärke“: Dann steuert KDE die Tasten wie bisher.

## 2026.10.01-7
- Fehler behoben: G-Tasten – besonders solche ohne Belegung (F13…F24) – lösten bei schnell wiederholtem Drücken manchmal nur einmal aus und galten danach als weiter gedrückt. Ursache: Die G19s schickt oft zwei Tasten-Meldungen in einem Paket, der Treiber las nur die erste. Jetzt wird jedes Paket vollständig ausgewertet, jeder Druck zählt.
- `--debug` zeigt die Meldungen eines Pakets getrennt an (durch `|`).
- Wiki: Hilfe für Remote-Desktop-Abbrüche mit xfreerdp beim Kopieren (`/clipboard:files-to:off`).

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
