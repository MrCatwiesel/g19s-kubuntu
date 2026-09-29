"""Nachrichten: RSS/Atom einlesen und regelmäßig abrufen."""


# --- Nachrichten (RSS/Atom) ---------------------------------------------------
def parse_feed(raw, source=""):
    """RSS 2.0, RSS 1.0 (RDF) und Atom: [{title, link, time, source}]"""
    import email.utils
    import datetime as dt
    import xml.etree.ElementTree as ET
    root = ET.fromstring(raw)
    local = lambda tag: tag.rsplit("}", 1)[-1]
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title, link, when = "", "", None
        for ch in el:
            name = local(ch.tag)
            if name == "title":
                import html
                title = re.sub(r"<[^>]+>", "", html.unescape("".join(ch.itertext()))).strip()
            elif name == "link":
                href = ch.get("href")
                if href and (ch.get("rel") in (None, "alternate") or not link):
                    link = href
                elif (ch.text or "").strip() and not link:
                    link = ch.text.strip()
            elif name in ("pubDate", "date", "updated", "published") and ch.text and when is None:
                t = ch.text.strip()
                try:
                    when = email.utils.parsedate_to_datetime(t)
                    if when.tzinfo is None:           # RFC 822 ohne Zone („-0000“) = UTC
                        when = when.replace(tzinfo=dt.timezone.utc)
                except (TypeError, ValueError, IndexError):
                    try:
                        when = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
                        if when.tzinfo is None:
                            when = when.astimezone()
                    except ValueError:
                        when = None
        if title:
            out.append({"title": " ".join(title.split()), "link": link, "time": when, "source": source})
    return out


class NewsPoller(Poller):
    def __init__(self, get_settings, log=print):
        super().__init__(get_settings, 900, log)

    def cfg(self):
        return self.get_settings().get("news") or {}

    def enabled(self):
        return bool(self.cfg().get("feeds")) and "news" in (self.get_settings().get("pages") or [])

    def signature(self):
        return json.dumps(self.cfg().get("feeds"), sort_keys=True)

    def fetch(self):
        import datetime as dt
        items, errors = [], []
        for f in self.cfg().get("feeds") or []:
            url = str(f.get("url") or "").strip()
            if not url:
                continue
            name = str(f.get("name") or domain_of(url))
            try:
                items += parse_feed(http_get(url, timeout=20), name)
            except FEED_ERRORS as ex:
                errors.append(f"{name}: {getattr(ex, 'reason', None) or ex}")
        if errors and not items:
            raise RuntimeError("; ".join(errors))
        old = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        items.sort(key=lambda x: x["time"] or old, reverse=True)
        return {"items": items[:max(5, min(100, int(self.cfg().get("count") or 30)))], "errors": errors}
