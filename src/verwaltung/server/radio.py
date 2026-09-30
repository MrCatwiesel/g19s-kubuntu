"""Radiosender probehören und im Verzeichnis radio-browser.info suchen."""


# --------------------------------------------------------------------------- #
# Radio: Probehören und Suche im Radio-Browser-Verzeichnis
# --------------------------------------------------------------------------- #
class Launcher:
    """Umgebung der Desktop-Sitzung (für mpv usw.)."""

    @staticmethod
    def env():
        return dict(os.environ)


test_radio = g.RadioManager(Launcher.env, log=lambda m: print(m, flush=True))

RADIO_BROWSER_HOSTS = ["de1.api.radio-browser.info", "at1.api.radio-browser.info",
                       "nl1.api.radio-browser.info", "all.api.radio-browser.info"]


def radio_search(query):
    params = urllib.parse.urlencode({"name": query, "limit": 40, "hidebroken": "true",
                                     "order": "clickcount", "reverse": "true"})
    last = None
    for host in RADIO_BROWSER_HOSTS:
        url = f"https://{host}/json/stations/search?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": g.USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as r:
                items = json.load(r)
            break
        except Exception as ex:         # nächsten Server des Radio-Verzeichnisses versuchen
            last = ex
    else:
        raise RuntimeError(f"Radio-Verzeichnis nicht erreichbar: {last}")
    out, seen = [], set()
    for it in items:
        url = (it.get("url_resolved") or it.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append({"name": (it.get("name") or "").strip(), "url": url,
                    "logo": (it.get("favicon") or "").strip(),
                    "country": it.get("countrycode") or it.get("country") or "",
                    "codec": it.get("codec") or "", "bitrate": it.get("bitrate") or 0,
                    "tags": (it.get("tags") or "")[:60]})
    return out
