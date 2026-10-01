// ---------------------------------------------------------------- Hilfen
const $ = (s, r = document) => r.querySelector(s);
function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  let value;
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "value") value = v;          // erst nach den Kindern setzen (select, textarea)
    else if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e && typeof v !== "string") e[k] = v;
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false)
    e.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  if (value !== undefined) e.value = value;
  return e;
}
const clone = o => JSON.parse(JSON.stringify(o));
const hex = rgb => "#" + rgb.map(c => c.toString(16).padStart(2, "0")).join("");
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
// Profile: S.macros = {profiles: [{name, colors, keys: {M1: {...}, M2: {...}, M3: {...}}}]}
const P = (i = UI.pidx) => S.macros.profiles[i];
const layerKeys = () => (P().keys || {})[UI.profile] || {};
function profColors(i = UI.pidx) {
  const p = S.macros.profiles[i];
  return (p && p.colors) || ((UI.sdraft || S.settings) || {}).colors || {M1: [0, 110, 255], M2: [0, 255, 90], M3: [255, 70, 0]};
}
function profileColor(layer) { return hex(profColors()[layer] || [80, 120, 200]); }
function toast(msg, err = false) {
  const t = el("div", {class: "toast" + (err ? " err" : ""), text: msg});
  const box = $("#toasts");
  box.append(t);
  while (box.children.length > 3) box.firstChild.remove();
  setTimeout(() => t.remove(), err ? 7000 : 3500);
}
async function api(path, opts = {}) {
  const o = {method: opts.method || (opts.body !== undefined ? "POST" : "GET"),
    headers: {"X-Token": TOKEN}, keepalive: !!opts.keepalive};
  if (opts.body !== undefined) {
    if (opts.raw) o.body = opts.body;
    else { o.body = JSON.stringify(opts.body); o.headers["Content-Type"] = "application/json"; }
  }
  let r;
  try { r = await fetch(path, o); }
  catch (e) { lost("Verbindung verloren", "Die Verwaltung läuft nicht mehr. Bitte über das Anwendungsmenü „G19s-Verwaltung“ neu öffnen."); throw e; }
  const data = await r.json().catch(() => ({}));
  if (r.status === 401) { lost("Sitzung ungültig", data.error || ""); throw new Error(data.error); }
  if (!r.ok) throw new Error(data.error || ("Fehler " + r.status));
  return data;
}
function lost(title, text) { $("#ovTitle").textContent = title; $("#ovText").textContent = text; $("#overlay").classList.add("show"); }
const keyLabel = name => S.keyLabel[name] || String(name).replace(/^KEY_/, "");
function fKeyText(gkey, p) {
  const f = "F" + (12 + parseInt(gkey.slice(1)));
  return {M1: f, M2: "Strg+" + f, M3: "Alt+" + f}[p];
}
function domainOf(u) { return String(u).replace(/^[a-z]+:\/\/(www\.)?/i, "").split("/")[0]; }
function stationName(url) {
  const s = ((UI.sdraft || S.settings).stations || []).find(x => x.url === url);
  return (s && s.name) || domainOf(url);
}
// Art und Beschriftung einer Belegung: dieselben Regeln wie entry_type/entry_label im Treiber (makros.py);
// die Reihenfolge der Arten kommt vom Treiber (S.entryTypes), tests/einheit/test_beschriftung.py vergleicht beide.
function typeOf(e) {
  if (!e) return "default";
  for (const t of S.entryTypes) {
    const v = e[t];
    if (t === "timer" && (typeof v !== "object" || v === null || Array.isArray(v))) continue;
    if (v && (!Array.isArray(v) || v.length)) return t;
  }
  return "default";
}
function num(v, dflt) { const n = parseFloat(v); return isNaN(n) || !v ? dflt : n; }
function fmtMinutes(m) { m = num(m, 5); return m >= 1 ? `${m} min` : `${Math.round(m * 60)} s`; }
function timerLabel(t) {
  t = t || {};
  if (t.mode === "stopwatch") return "Stoppuhr";
  if (t.mode === "pomodoro") return `Pomodoro ${num(t.work, 25)}/${num(t.break, 5)}`;
  return `Timer ${fmtMinutes(t.minutes)}`;
}
function snippetGroups() {
  const sd = UI.sdraft || S.settings;
  return [...new Set(sd.snippets.map(x => (x.group || "").trim()).filter(Boolean))].sort();
}
// Namen der Textbausteine wie im Treiber (snippet_list): Name oder erste Textzeile; G-Tasten verweisen darauf
function snippetNames() {
  const sd = UI.sdraft || S.settings;
  return [...new Set((sd.snippets || []).filter(x => x.text).map(x =>
    (x.name || "").trim() || [...x.text.split("\n")[0]].slice(0, 40).join("")))];
}
function comboList(c) { return (Array.isArray(c) ? c : String(c || "").split("+")).map(s => String(s).trim()).filter(Boolean); }
function entryLabel(e) {
  if (!e) return "";
  if (e.name) return e.name;
  const t = typeOf(e);
  if (t === "open") return domainOf(e.open);
  if (t === "radio") return e.radio === "stop" ? "Radio aus" : stationName(e.radio);
  if (t === "media") return S.media[e.media] || "Musik";
  if (t === "volume") return S.volume[e.volume] || "Lautstärke";
  if (t === "snippets") return e.snippet ? String(e.snippet) : e.snippets === "*" ? "Textbausteine" : String(e.snippets);
  if (t === "timer") return timerLabel(e.timer);
  if (t === "sleep") return `Einschlafen ${e.sleep} min`;
  if (t === "mic") return "Mikrofon";
  if (t === "run") return String(e.run).trim().split(/\s+/)[0];
  if (t === "text") return "Text";
  if (t === "combo") return comboList(e.combo).map(keyLabel).join("+");
  if (t === "steps") return "Makro";
  return "";
}
// Einfügeart eines Textes (G-Taste „Text“, Textbaustein): "" = tippen, sonst Tasten zum Einfügen
const PASTE_MODES = [["ctrl+v", "Über die Zwischenablage einfügen (Strg+V)"],
  ["ctrl+shift+v", "Über die Zwischenablage, Strg+Umschalt+V (Konsole)"], ["", "Zeichen für Zeichen tippen"]];
function pasteSelect(value, onchange) {
  return el("select", {class: "pasteMode", onchange: e => onchange(e.target.value)},
    ...PASTE_MODES.map(([v, t]) => el("option", {value: v, text: t, selected: (value || "") === v})));
}
