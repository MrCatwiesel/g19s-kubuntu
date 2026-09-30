#!/usr/bin/env python3
"""Baut aus den Quellmodulen die beiden Programmdateien und die Wiki-Seite.

    python3 build.py

Ergebnis in dist/:
    g19s.py                   Treiber        (aus src/treiber/, Reihenfolge in src/treiber/REIHENFOLGE)
    g19s-gui.py               Verwaltung     (aus src/verwaltung/server/ und src/verwaltung/seite/)
    G19s_unter_Kubuntu.wiki   Wiki-Seite     (aus doku/wiki_vorlage.txt, enthält beide Programme)

Die Module teilen sich nach dem Bündeln einen gemeinsamen Namensraum: Ein Modul
darf Namen aus jedem anderen Modul verwenden, ohne sie zu importieren.
build.py prüft deshalb, dass kein Name doppelt definiert ist und jeder
verwendete Name irgendwo definiert wird.
"""
import ast
import builtins
import os
import re
import shutil
import symtable
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
END_MARKER = "# G19S-DATEIENDE (diese Zeile zeigt, dass die Datei vollständig ist)"


def read(*parts):
    return open(os.path.join(HERE, *parts), encoding="utf-8").read()


def split_module(src):
    """(Modul-Docstring, führende Importzeilen, Rest) eines Quellmoduls."""
    tree = ast.parse(src)
    lines = src.split("\n")
    doc, imports, start = None, [], 0
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        doc = body[0].value.value.strip()
        start = body[0].end_lineno
        body = body[1:]
    for node in body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            break
        imports.append("\n".join(lines[node.lineno - 1:node.end_lineno]))
        start = node.end_lineno
    return doc, imports, "\n".join(lines[start:]).strip("\n")


def bundle(folder, head_module):
    order = [m.strip() for m in read(folder, "REIHENFOLGE").split("\n") if m.strip() and not m.startswith("#")]
    parts, imports = [], []
    for name in order:
        src = read(folder, name + ".py")
        if name == head_module:
            parts.append(src.rstrip("\n"))
            continue
        doc, imps, rest = split_module(src)
        for imp in imps:
            if imp not in imports:
                imports.append(imp)
        banner = f"# {'═' * 75}\n# Modul {name}"
        if doc:
            banner += "\n" + "\n".join("#   " + l if l else "#" for l in doc.split("\n"))
        banner += f"\n# {'═' * 75}"
        parts.append(banner + "\n\n" + rest)
    head = parts[0]
    present = set(re.findall(r"^(?:import .+|from \S+ import .+)$", head, re.M))
    extra = [i for i in imports if i not in present]
    if extra:
        head += "\n\n# Weitere Importe der Module\n" + "\n".join(extra)
    parts[0] = head
    return "\n\n\n".join(parts) + "\n\n\n" + END_MARKER + "\n", order


def build_page():
    """Seite der Verwaltung: Gerüst + stil.css + js/*.js (in Dateinamen-Reihenfolge)."""
    base = os.path.join("src", "verwaltung", "seite")
    js_dir = os.path.join(HERE, base, "js")
    js = "\n".join(read(base, "js", f) for f in sorted(os.listdir(js_dir)) if f.endswith(".js"))
    html = read(base, "geruest.html").replace("@@CSS@@", read(base, "stil.css"))
    if "\'\'\'" in html + js or js.rstrip().endswith("\\"):
        sys.exit("Seite oder Skript enthalten dreifache Anführungszeichen bzw. enden mit \\")
    node = shutil.which("node")
    if node:                                # JavaScript-Syntax prüfen (wenn Node.js vorhanden ist)
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
        os.remove(f.name)
        if r.returncode:
            sys.exit("JavaScript-Fehler in der Verwaltung:\n" + r.stderr.strip()[:1500])
    return html, js


def check(name, text):
    """Syntax, doppelte Definitionen und undefinierte Namen prüfen."""
    problems = []
    try:
        tree = ast.parse(text)
    except SyntaxError as ex:
        sys.exit(f"{name}: Syntaxfehler Zeile {ex.lineno}: {ex.msg}")
    seen = {}
    for node in tree.body:
        names = []
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                names += [e.id for e in ast.walk(t) if isinstance(e, ast.Name)]
        for n in names:
            if n in seen and isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                problems.append(f"{n} doppelt definiert (Zeilen {seen[n]} und {node.lineno})")
            seen.setdefault(n, node.lineno)
    table = symtable.symtable(text, name, "exec")
    defined = {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()
               or s.is_namespace()} | set(dir(builtins)) | {"__file__", "__name__"}

    def walk(t):
        for s in t.get_symbols():
            if (s.is_global() or (t.get_type() == "module" and s.is_referenced())) and s.get_name() not in defined:
                problems.append(f"Name „{s.get_name()}“ wird in {t.get_name()} verwendet, aber nirgends definiert")
        for c in t.get_children():
            walk(c)
    walk(table)
    if problems:
        sys.exit(f"{name}:\n  " + "\n  ".join(sorted(set(problems))))


def driver_api(driver, gui):
    """Namen des Treibers, die die Verwaltung als g.<name> benutzt – jeder muss im Treiber existieren."""
    tree = ast.parse(driver)
    defined = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Assign):
            defined.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            defined.update((a.asname or a.name).split(".")[0] for a in node.names)
    used = sorted(set(re.findall(r"\bg\.([A-Za-z_]\w*)", gui)))
    unknown = [n for n in used if n not in defined]
    if unknown:
        sys.exit("Die Verwaltung benutzt Namen, die es im Treiber nicht gibt: " + ", ".join(unknown))
    return used


def main():
    os.makedirs(DIST, exist_ok=True)
    driver, order = bundle(os.path.join("src", "treiber"), "kopf")
    check("g19s.py", driver)
    html, js = build_page()
    gui, _ = bundle(os.path.join("src", "verwaltung", "server"), "kopf")
    gui = gui.replace("@@DRIVER_API@@", " ".join(driver_api(driver, gui)))   # vor dem Einsetzen der Seite
    gui = gui.replace("@@PAGE_HTML@@", html).replace("@@PAGE_JS@@", js)
    check("g19s-gui.py", gui)
    for fname, text in (("g19s.py", driver), ("g19s-gui.py", gui)):
        path = os.path.join(DIST, fname)
        open(path, "w", encoding="utf-8").write(text)
        os.chmod(path, 0o755)
    version = re.search(r'^VERSION = "([^"]+)"', driver, re.M).group(1)
    gui_version = re.search(r'^VERSION = "([^"]+)"', gui, re.M).group(1)
    if version != gui_version:
        sys.exit(f"Versionen passen nicht: Treiber {version}, Verwaltung {gui_version}")
    wiki = read("doku", "wiki_vorlage.txt")
    for key, text in (("G19S_PY", driver), ("GUI_PY", gui), ("RULES", read("dateien", "70-g19s.rules")),
                      ("SERVICE", read("dateien", "g19s.service")), ("MACROS", read("dateien", "macros_beispiel.json")),
                      ("VERSION", version)):
        wiki = wiki.replace(f"@@{key}@@", text.rstrip("\n"))
    if "@@" in wiki:
        sys.exit("Wiki-Vorlage enthält unbekannte Platzhalter: " + ", ".join(set(re.findall(r"@@\w+@@", wiki))))
    for text in (driver, gui):
        if "\nG19S_EOF\n" in text:
            sys.exit("Programmtext enthält die Heredoc-Endmarke G19S_EOF")
    open(os.path.join(DIST, "G19s_unter_Kubuntu.wiki"), "w", encoding="utf-8").write(wiki)
    print(f"Version {version}: g19s.py {driver.count(chr(10))} Zeilen aus {len(order)} Modulen, "
          f"g19s-gui.py {gui.count(chr(10))} Zeilen, Wiki {wiki.count(chr(10))} Zeilen")


if __name__ == "__main__":
    main()
