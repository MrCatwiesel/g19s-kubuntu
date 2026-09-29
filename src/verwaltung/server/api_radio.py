"""HTTP-Routen: Probehören und Sendersuche."""


class ApiRadio:
    # -- API: Radio -------------------------------------------------------- #
    def api_post_radio_play(self, q):
        body = self._json()
        station = {"name": str(body.get("name", "")), "url": str(body.get("url", "")).strip()}
        if not station["url"].startswith(("http://", "https://")):
            raise ValueError("Bitte eine Stream-Adresse mit http:// oder https:// angeben")
        player = str(body.get("player") or g.DEFAULT_SETTINGS["radio_player"])
        if not test_radio.play(station, player):
            raise RuntimeError("Der Radioplayer ließ sich nicht starten. Ist mpv installiert "
                               "(sudo apt install mpv)?")
        self._send(200, {"ok": True})

    def api_post_radio_stop(self, q):
        test_radio.stop()
        self._send(200, {"ok": True})

    def api_get_radio_search(self, q):
        query = q.get("q", [""])[0].strip()
        if len(query) < 2:
            raise ValueError("Bitte mindestens zwei Zeichen eingeben")
        self._send(200, {"results": radio_search(query)})
