// ---------------------------------------------------------------- Übernehmen
function draftToEntry(d) {
  const e = {};
  if (d.name && d.name.trim()) e.name = d.name.trim();
  switch (d.type) {
    case "text": if (d.text) { e.text = d.text; if (d.paste) e.paste = d.paste; } break;
    case "combo": if (d.combo.length) e.combo = d.combo.join("+"); break;
    case "steps": if (d.steps.length) e.steps = d.steps; break;
    case "open": if (d.open) e.open = /^[a-z]+:\/\//i.test(d.open) ? d.open : "https://" + d.open; break;
    case "run": if (d.run.trim()) e.run = d.run.trim(); break;
    case "radio": if (d.radio) e.radio = d.radio; break;
    case "media": if (d.media) e.media = d.media; break;
    case "volume": if (d.volume) e.volume = d.volume; break;
    case "snippets": e.snippets = d.snippets || "*"; break;
    case "sleep": e.sleep = d.sleep || 30; break;
    case "mic": e.mic = "toggle"; break;
    case "timer": {
      const t = d.timer;
      e.timer = t.mode === "stopwatch" ? {mode: "stopwatch"} :
        t.mode === "pomodoro" ? {mode: "pomodoro", work: t.work, break: t.break} : {mode: "timer", minutes: t.minutes};
      break; }
  }
  return Object.keys(e).length ? e : null;
}
function draftProblem(d) {
  const need = {text: [d.text, "Bitte einen Text eingeben."], combo: [d.combo.length, "Bitte eine Tastenkombination aufnehmen oder auswählen."],
    steps: [d.steps.length, "Das Makro hat noch keine Schritte."], open: [d.open, "Bitte eine Webadresse eingeben."],
    run: [d.run.trim(), "Bitte einen Befehl eingeben."], radio: [d.radio, "Bitte einen Sender wählen."]}[d.type];
  return need && !need[0] ? need[1] : null;
}
async function saveMacros(macros, msg) {
  const r = await api("/api/macros", {body: {macros}});
  S.macros = r.macros; S.mtimes.macros = r.mtime;
  $("#extBanner").classList.remove("show");
  toast(msg);
}
async function applyDraft() {
  stopRecording(true);
  const d = UI.draft, problem = draftProblem(d);
  if (problem) { toast(problem, true); return; }
  const m = clone(S.macros), e = draftToEntry(d), keys = m.profiles[UI.pidx].keys;
  keys[UI.profile] = keys[UI.profile] || {};
  if (e) keys[UI.profile][UI.gkey] = e; else delete keys[UI.profile][UI.gkey];
  try {
    await saveMacros(m, `${UI.gkey} (${P().name}, ${UI.profile}) gespeichert – der Treiber übernimmt es sofort.`);
    selectKey(UI.gkey, true); renderKeypad(); renderEditor();
  } catch (err) { toast(err.message, true); }
}
async function clearKey() {
  if (!confirm(`Belegung von ${UI.gkey} (${P().name}, ${UI.profile}) entfernen? Die Taste sendet danach wieder ${fKeyText(UI.gkey, UI.profile)}.`)) return;
  const m = clone(S.macros), keys = m.profiles[UI.pidx].keys;
  if (keys[UI.profile]) delete keys[UI.profile][UI.gkey];
  try { await saveMacros(m, `${UI.gkey} (${P().name}, ${UI.profile}) zurückgesetzt.`); selectKey(UI.gkey, true); renderKeypad(); renderEditor(); }
  catch (err) { toast(err.message, true); }
}
