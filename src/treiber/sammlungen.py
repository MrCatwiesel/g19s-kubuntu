"""Gemerkte Songs und Lieblingsbilder (songs.json, favorites.json)."""


# --------------------------------------------------------------------------- #
# Gemerkte Songs, Lieblingsbilder, Sicherung
# --------------------------------------------------------------------------- #
def load_list(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def remember_song(info, station=None):
    """Aktuellen Titel an songs.json anhängen. Liefert den Eintrag oder None (nichts läuft / schon gemerkt)."""
    if not info or not (info.get("title") or info.get("artist")):
        return None
    title, artist = str(info.get("title") or "").strip(), str(info.get("artist") or "").strip()
    if not artist and " - " in title:
        artist, title = [x.strip() for x in title.split(" - ", 1)]
    songs = load_list(SONGS_FILE)
    entry = {"time": time.strftime("%Y-%m-%d %H:%M"), "artist": artist, "title": title,
             "source": (station or {}).get("name") or str(info.get("player") or "")}
    if songs and songs[-1].get("artist") == artist and songs[-1].get("title") == title:
        return None
    songs.append(entry)
    save_json(SONGS_FILE, songs[-500:])
    return entry


def toggle_favorite(info, source):
    """Bild zu den Lieblingsbildern hinzufügen bzw. entfernen. True = ist jetzt Favorit."""
    favs = load_list(FAVORITES_FILE)
    key = str(info["id"])
    rest = [f for f in favs if str(f.get("id")) != key]
    if len(rest) != len(favs):
        save_json(FAVORITES_FILE, rest)
        return False
    rest.append({"id": info["id"], "name": info.get("name", ""), "url": info.get("url", ""),
                 "local": bool(info.get("local")), "source": source, "page": info.get("page", ""),
                 "time": time.strftime("%Y-%m-%d %H:%M")})
    save_json(FAVORITES_FILE, rest)
    return True
