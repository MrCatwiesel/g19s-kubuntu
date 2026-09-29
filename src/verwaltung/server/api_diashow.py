"""HTTP-Routen: Piwigo-Alben und Diashow-Test."""


class ApiSlides:
    # -- API: Piwigo ------------------------------------------------------- #
    def api_post_piwigo_albums(self, q):
        body = self._json()
        try:
            client = g.PiwigoClient(body.get("url"), body.get("user"), body.get("password"))
            albums = client.albums()
        except g.PiwigoError as ex:
            raise RuntimeError(str(ex))
        self._send(200, {"albums": albums})

    def api_post_piwigo_test(self, q):
        self._send(200, piwigo_test(self._json().get("slideshow")))
