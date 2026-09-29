// ---------------------------------------------------------------- Aufnahme im Fenster
function startRecording(mode, capEl, btn, done) {
  const rec = {mode, capEl, btn, done, steps: [], combo: [], held: new Set(), last: null, unknown: 0};
  UI.recording = rec;
  capEl.classList.add("on");
  capEl.textContent = mode === "combo" ? "● Jetzt die Kombination drücken …" : "● Aufnahme läuft – Tasten drücken …";
  btn.classList.add("rec"); btn.textContent = mode === "combo" ? "■ Abbrechen" : "■ Aufnahme beenden";
  document.activeElement && document.activeElement.blur();
}
function stopRecording(apply) {
  const rec = UI.recording; if (!rec) return;
  UI.recording = null;
  if (apply && rec.mode === "steps") {
    for (const k of rec.held) rec.steps.push([20, k, "up"]);
    if (rec.steps.length) rec.done(rec.steps);
  }
  if (rec.capEl.isConnected) {
    rec.capEl.classList.remove("on");
    rec.capEl.textContent = rec.unknown ? `Aufnahme beendet (${rec.unknown} unbekannte Tasten übersprungen).` : "Aufnahme beendet.";
    rec.btn.classList.remove("rec");
    rec.btn.textContent = rec.mode === "combo" ? "⏺ Kombination aufnehmen" : "⏺ Aufnehmen";
  }
}
function onKey(e) {
  const rec = UI.recording; if (!rec) return;
  e.preventDefault(); e.stopPropagation();
  if (e.repeat) return;
  const k = CODE_MAP[e.code];
  if (!k) { if (e.type === "keydown") rec.unknown++; return; }
  const now = performance.now();
  if (rec.mode === "combo") {
    if (e.type === "keydown") { if (!rec.combo.includes(k)) rec.combo.push(k); rec.held.add(k);
      rec.capEl.textContent = "● " + rec.combo.map(keyLabel).join(" + "); }
    else { rec.held.delete(k); if (!rec.held.size && rec.combo.length) { rec.done(rec.combo.slice()); stopRecording(false); } }
    return;
  }
  if (e.type === "keyup" && !rec.held.has(k)) return;
  const wait = rec.last === null ? 0 : Math.round(now - rec.last);
  rec.last = now;
  if (e.type === "keydown") rec.held.add(k); else rec.held.delete(k);
  rec.steps.push([Math.min(wait, 5000), k, e.type === "keydown" ? "down" : "up"]);
  const n = rec.steps.filter(s => s[2] === "down").length;
  rec.capEl.textContent = `● Aufnahme läuft – ${n} Tastendrücke …`;
}
window.addEventListener("keydown", onKey, true);
window.addEventListener("keyup", onKey, true);
