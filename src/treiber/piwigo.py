"""Piwigo-Galerie: Anmeldung, Alben, Bildlisten, Bilder laden; Bild ins Display einpassen."""


# --------------------------------------------------------------------------- #
# Piwigo: Alben und Bilder über die Web-API (ws.php) abrufen
# --------------------------------------------------------------------------- #
class PiwigoError(Exception):
    pass


class PiwigoClient:
    """Minimaler Client für die Piwigo-API. Funktioniert mit öffentlichen
    Alben ohne Anmeldung und mit privaten Alben über Benutzer/Passwort."""

    SIZES = ("medium", "large", "small", "xlarge", "2small", "xsmall", "thumb")

    def __init__(self, url, user="", password="", timeout=15):
        import http.cookiejar
        import urllib.request
        url = str(url or "").strip().rstrip("/")
        if not url:
            raise PiwigoError("Keine Piwigo-Adresse eingetragen")
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + url
        url = re.sub(r"/(ws\.php|index\.php)$", "", url)
        self.base = url
        self.user, self.password, self.timeout = user or "", password or "", timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", USER_AGENT)]
        self.logged_in = False

    def _call(self, method, params=None, post=False):
        import urllib.error
        import urllib.parse
        query = [("format", "json"), ("method", method)]
        body = None
        items = []
        for k, v in (params or {}).items():
            if isinstance(v, (list, tuple)):
                items += [(f"{k}[]", str(x)) for x in v]
            else:
                items.append((k, str(v).lower() if isinstance(v, bool) else str(v)))
        if post:
            body = urllib.parse.urlencode(items).encode()
        else:
            query += items
        url = f"{self.base}/ws.php?{urllib.parse.urlencode(query)}"
        try:
            with self.opener.open(url, data=body, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as ex:
            raise PiwigoError(f"Piwigo antwortet mit Fehler {ex.code} ({url.split('?')[0]})")
        except NET_ERRORS as ex:
            reason = err_text(ex)
            if "WRONG_VERSION_NUMBER" in reason or "wrong version number" in reason:
                raise PiwigoError("Die Galerie unterstützt kein https – Adresse mit http:// eintragen")
            if "CERTIFICATE_VERIFY_FAILED" in reason:
                raise PiwigoError("Das Zertifikat der Galerie ist ungültig oder selbst signiert")
            raise PiwigoError(f"Piwigo nicht erreichbar: {reason}")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            raise PiwigoError("Keine gültige Antwort – ist die Adresse eine Piwigo-Galerie?")
        if data.get("stat") != "ok":
            raise PiwigoError(f"Piwigo: {data.get('message') or data.get('err') or 'Fehler'}")
        return data.get("result")

    def login(self):
        if self.logged_in or not self.user:
            return
        try:
            self._call("pwg.session.login", {"username": self.user, "password": self.password}, post=True)
        except PiwigoError as ex:
            raise PiwigoError(f"Anmeldung fehlgeschlagen – Benutzer oder Passwort prüfen ({ex})")
        self.logged_in = True

    def albums(self):
        """Alle sichtbaren Alben: [{id, name, parent, level, images, total, path}]"""
        self.login()
        res = self._call("pwg.categories.getList", {"recursive": True, "fullname": False})
        cats = res.get("categories", []) if isinstance(res, dict) else res or []
        by_id = {}
        for c in cats:
            try:
                cid = int(c["id"])
            except (KeyError, TypeError, ValueError):
                continue
            parent = c.get("id_uppercat")
            by_id[cid] = {"id": cid, "name": re.sub(r"<[^>]+>", "", str(c.get("name", ""))).strip(),
                          "parent": int(parent) if str(parent or "").isdigit() else None,
                          "images": int(c.get("nb_images") or 0),
                          "total": int(c.get("total_nb_images") or c.get("nb_images") or 0),
                          "rank": str(c.get("global_rank") or "")}

        def path(cid, seen=()):
            a = by_id[cid]
            if a["parent"] in by_id and a["parent"] not in seen:
                return path(a["parent"], seen + (cid,)) + [a["name"]]
            return [a["name"]]

        out = []
        for cid, a in by_id.items():
            p = path(cid)
            out.append(dict(a, path=" / ".join(p), level=len(p) - 1))
        # Baumreihenfolge: nach global_rank, sonst nach Pfad
        out.sort(key=lambda a: ([int(x) for x in a["rank"].split(".") if x.isdigit()] or [9999], a["path"].lower()))
        for a in out:
            a.pop("rank", None)
        return out

    def images(self, album_ids, recursive=True, limit=5000):
        """Bilder der Alben: [{id, name, url, album}] – url zeigt auf eine passende Größe."""
        self.login()
        out, seen = [], set()
        for aid in album_ids:
            page = 0
            while len(out) < limit:
                res = self._call("pwg.categories.getImages",
                                 {"cat_id": int(aid), "recursive": bool(recursive),
                                  "per_page": 500, "page": page})
                imgs = res.get("images", []) if isinstance(res, dict) else []
                for im in imgs:
                    iid = im.get("id")
                    if iid in seen:
                        continue
                    seen.add(iid)
                    url = None
                    der = im.get("derivatives") or {}
                    for size in self.SIZES:
                        if isinstance(der.get(size), dict) and der[size].get("url"):
                            url = der[size]["url"]
                            break
                    url = url or im.get("element_url")
                    if url:
                        out.append({"id": iid, "name": str(im.get("name") or im.get("file") or ""),
                                    "url": url})
                paging = res.get("paging", {}) if isinstance(res, dict) else {}
                count = int(paging.get("count") or len(imgs))
                if count < 500 or not imgs:
                    break
                page += 1
        return out

    def fetch(self, url, limit=20 * 1024 * 1024):
        import urllib.parse
        if not re.match(r"^https?://", url, re.I):
            url = urllib.parse.urljoin(self.base + "/", url)
        if not re.match(r"^https?://", url, re.I):        # z. B. file:// aus der Serverantwort
            raise PiwigoError("Ungültige Bildadresse vom Server")
        try:
            with self.opener.open(url, timeout=self.timeout) as r:
                return r.read(limit)
        except NET_ERRORS as ex:
            raise PiwigoError(f"Bild nicht abrufbar: {err_text(ex)}")


def fit_photo(img, size, mode="contain"):
    """Bild auf die Displayfläche bringen: contain = ganz sichtbar mit unscharfem
    Hintergrund, cover = Fläche füllen (Ränder werden abgeschnitten)."""
    from PIL import ImageEnhance, ImageFilter, ImageOps
    img = ImageOps.exif_transpose(img).convert("RGB")
    if mode == "cover":
        return ImageOps.fit(img, size, Image.LANCZOS)
    bg = ImageOps.fit(img, size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(12))
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    fg = ImageOps.contain(img, size, Image.LANCZOS)
    bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
    return bg
