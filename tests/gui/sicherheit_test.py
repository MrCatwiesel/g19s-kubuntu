"""Verwaltung: Einmal-Code statt Schlüssel in der Adresse, Content-Security-Policy, Schlüssel nie in der URL."""
import json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
import os as _os
ROOT = _os.environ.get("G19S_TEST_ROOT", "/tmp/g19s-test")
BASE = "http://127.0.0.1:8799"
def ok(c, m): print(("OK   " if c else "FEHL ") + m)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def req(path, data=None, token=None):
    r = urllib.request.Request(BASE + path, data=data, headers={"X-Token": token} if token else {})
    try:
        with opener.open(r, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as ex:
        return ex.code, dict(ex.headers), ex.read()


code, headers, body = req("/")
csp = headers.get("Content-Security-Policy", "")
ok("script-src 'self'" in csp and "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
   and "frame-ancestors 'none'" in csp, "CSP: nur eigenes Skript, kein Einbetten: " + csp[:80])
ok(b"<script>" not in body and b'<script src="/app.js">' in body, "kein Inline-Skript in der Seite")
ok(req("/app.js")[0] == 200, "Skript ohne Schlüssel abrufbar (enthält keine Geheimnisse)")
ok(req("/api/state?token=testtoken")[0] == 401, "Schlüssel in der Adresse wird nicht angenommen")
ok(req("/api/state", token="testtoken")[0] == 200, "Schlüssel in der Kopfzeile geht")
code, _, body = req("/api/ticket", data=json.dumps({"ticket": "falsch"}).encode())
ok(code == 403, "falscher Einmal-Code abgelehnt")
ticket = json.loads(req("/api/newticket", data=b"{}", token="testtoken")[2])["ticket"]
errors, csp_msgs = [], []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.on("pageerror", lambda e: (errors.append(str(e)), print("SEITENFEHLER", e)))
    pg.on("console", lambda m: csp_msgs.append(m.text) if "Content Security Policy" in m.text else None)
    pg.goto(f"{BASE}/#k={ticket}"); pg.wait_for_selector(".gkey", timeout=10000)
    ok(pg.locator(".gkey").count() == 12, "Anmeldung mit Einmal-Code")
    ok(pg.evaluate("location.hash") == "", "Code aus der Adresszeile entfernt")
    pg.reload(); pg.wait_for_selector(".gkey", timeout=10000)
    ok(pg.locator(".gkey").count() == 12, "Neuladen bleibt angemeldet (Schlüssel im Tab)")
    pg2 = b.new_page(); pg2.goto(f"{BASE}/#k={ticket}"); pg2.wait_for_timeout(1500)
    ok(pg2.locator(".gkey").count() == 0 and pg2.is_visible("#overlay"), "Code ein zweites Mal ungültig")
    pg.click("nav >> text=Beleuchtung"); pg.wait_for_timeout(800)
    b.close()
ok(not csp_msgs, "keine CSP-Verstöße: " + "; ".join(csp_msgs)[:200])
ok(not errors, "keine JavaScript-Fehler")
