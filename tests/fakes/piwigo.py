# Simulierter Piwigo-Server (Auszug der ws.php-API) für Tests
import http.server, json, urllib.parse, io, sys
from PIL import Image, ImageDraw
CATS = [  # id, name, parent, privat
    (1, "Urlaub 2025", None, False), (2, "Italien", 1, False), (3, "Familie (privat)", None, True)]
IMAGES = {1: [101, 102], 2: [201, 202, 203], 3: [301]}
COLORS = {101: (200, 60, 40), 102: (40, 160, 90), 201: (30, 90, 200), 202: (220, 180, 30), 203: (120, 40, 160), 301: (240, 240, 240)}
def img_bytes(iid, w, h):
    im = Image.new("RGB", (w, h), COLORS[iid]); d = ImageDraw.Draw(im)
    d.ellipse([w//4, h//4, 3*w//4, 3*h//4], outline=(255, 255, 255), width=12); d.text((20, 20), f"Bild {iid}", fill=(0, 0, 0))
    b = io.BytesIO(); im.save(b, "JPEG"); return b.getvalue()
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def logged(self): return "pwg_id=ok" in (self.headers.get("Cookie") or "")
    def send(self, obj, cookie=None, code=200, ctype="application/json"):
        body = json.dumps(obj).encode() if not isinstance(obj, bytes) else obj
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", len(body))
        if cookie: self.send_header("Set-Cookie", cookie)
        self.end_headers(); self.wfile.write(body)
    def visible(self): return [c for c in CATS if not c[3] or self.logged()]
    def do_POST(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode())
        if q.get("method") == ["pwg.session.login"]:
            if form.get("username") == ["max"] and form.get("password") == ["geheim"]:
                return self.send({"stat": "ok", "result": True}, cookie="pwg_id=ok; Path=/")
            return self.send({"stat": "fail", "err": 999, "message": "Invalid username/password"})
        self.send({"stat": "fail", "message": "unknown"})
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path.endswith("/i.php"):
            iid = int(u.query.split("-")[0].split("/")[-1]); cat = next(c for c, ims in IMAGES.items() if iid in ims)
            if dict((c[0], c[3]) for c in CATS)[cat] and not self.logged(): return self.send(b"forbidden", code=403, ctype="text/plain")
            return self.send(img_bytes(iid, 792, 594), ctype="image/jpeg")
        if not u.path.endswith("/ws.php"): return self.send(b"<html>nope</html>", ctype="text/html")
        m = q.get("method", [""])[0]
        if m == "pwg.categories.getList":
            cats = [{"id": c[0], "name": c[1], "id_uppercat": c[2], "nb_images": len(IMAGES[c[0]]),
                     "total_nb_images": len(IMAGES[c[0]]) + sum(len(IMAGES[x[0]]) for x in CATS if x[2] == c[0]),
                     "global_rank": ".".join(str(i) for i in ([1, 1] if c[0] == 2 else [c[0] if c[0] != 3 else 2]))} for c in self.visible()]
            return self.send({"stat": "ok", "result": {"categories": cats}})
        if m == "pwg.categories.getImages":
            ids = [int(x) for x in q.get("cat_id[]", q.get("cat_id", []))]; rec = q.get("recursive", ["false"])[0] == "true"
            vis = {c[0] for c in self.visible()}
            cats = set(i for i in ids if i in vis)
            if rec: cats |= {c[0] for c in CATS if c[2] in cats and c[0] in vis}
            imgs = [{"id": i, "file": f"IMG_{i}.jpg", "name": f"Foto {i}", "element_url": f"http://127.0.0.1:8811/upload/{i}.jpg",
                     "derivatives": {"thumb": {"url": f"http://127.0.0.1:8811/i.php?/{i}-th.jpg"},
                                     "medium": {"url": f"http://127.0.0.1:8811/i.php?/{i}-me.jpg"}}}
                    for c in sorted(cats) for i in IMAGES[c]]
            return self.send({"stat": "ok", "result": {"paging": {"page": 0, "per_page": 500, "count": len(imgs)}, "images": imgs}})
        self.send({"stat": "fail", "message": "Method name is not valid"})
http.server.ThreadingHTTPServer(("127.0.0.1", 8811), H).serve_forever()
