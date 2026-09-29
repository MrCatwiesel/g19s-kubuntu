"""Aufruf von der Kommandozeile: Optionen, Vorschau-Bilder, Start des Treibers."""


def preview(prefix):
    r = Renderer()
    r.stats.cpu_percent()
    time.sleep(0.2)
    demo = {"M1": {"G1": {"name": "Test-Satz"}, "G2": {"open": "https://www.heise.de/news"},
                   "G3": {"name": "Golem", "open": "https://www.golem.de"},
                   "G5": {"name": "Makro G5"},
                   "G9": {"name": "Sehr langer Makroname zum Testen"}}}
    media = MediaWatcher(lambda: dict(os.environ))
    media._poll()          # einmal abfragen (zeigt echte Wiedergabe, falls vorhanden)
    r.media = media
    for p in range(Renderer.PAGES):
        path = f"{prefix}_{p + 1}.png"
        r.render(p, "M1", demo).save(path)
        print("gespeichert:", path)
    r.render_message("● Aufnahme G5", ["3 Tastendrücke", "Tasten jetzt tippen",
                                        "MR = speichern"], REC_COLOR).save(f"{prefix}_rec.png")
    print("gespeichert:", f"{prefix}_rec.png")


def main():
    ap = argparse.ArgumentParser(description="Treiber für Logitech G19/G19s (Display + G-Tasten)")
    ap.add_argument("--debug", action="store_true", help="Rohdaten der Tasten ausgeben")
    ap.add_argument("--brightness", type=int, metavar="0-100", help="Displayhelligkeit setzen")
    ap.add_argument("--keep-backlight", action="store_true",
                    help="Tastaturbeleuchtung nicht je Profil umfärben")
    ap.add_argument("--preview", metavar="PREFIX", help="Displayseiten als PNG speichern (ohne Tastatur)")
    args = ap.parse_args()
    if args.preview:
        preview(args.preview)
    else:
        run(args)


if __name__ == "__main__":
    main()
