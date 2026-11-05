// ---------------------------------------------------------------- Visualisierung: Stile
// Der gewählte Stil (UI.sdraft.visual.style) gilt auch am Display; Optionen je Stil aus VISUAL_OPTIONS
// (S.visualOptions) in UI.sdraft.visual[<stil>], gespeichert mit den übrigen Einstellungen.
function renderVisual() {
  const sd = UI.sdraft; if (!sd || !S.visualStyles) return;
  const v = sd.visual;
  $("#visStyle").replaceChildren(...S.visualStyles.map(([id, label]) =>
    el("option", {value: id, text: label, selected: id === v.style})));
  $("#visBacklight").checked = v.backlight !== false;
  $("#visTitle").checked = v.title !== false;
  $("#visTalkWords").value = v.talk_words || "";
  renderVisualOptions();
  visualPreview();
}
function renderVisualOptions() {
  const v = UI.sdraft.visual, style = v.style;
  if (!v[style]) v[style] = {};
  $("#visOpts").replaceChildren(...optionFields(S.visualOptions[style] || [], v[style],
    () => { touchSettings(); visualPreview(); }));
}
let visTimer = null;
function visualPreview() {
  clearTimeout(visTimer);
  visTimer = setTimeout(async () => {
    if (UI.tab !== "settings") return;
    try { $("#visLcd").src = (await api("/api/preview", {body: {page: S.pageIds.indexOf("visual"), profile: UI.pvProfile || "M1",
      settings: UI.sdraft, pidx: UI.pidx, style: UI.sdraft.visual.style}})).image; }
    catch (e) { /* Vorschau ist nicht kritisch */ }
  }, 200);
}
$("#visStyle").addEventListener("change", e => { UI.sdraft.visual.style = e.target.value; touchSettings(); renderVisualOptions(); visualPreview(); });
$("#visBacklight").addEventListener("change", e => { UI.sdraft.visual.backlight = e.target.checked; touchSettings(); });
$("#visTitle").addEventListener("change", e => { UI.sdraft.visual.title = e.target.checked; touchSettings(); visualPreview(); });
$("#visTalkWords").addEventListener("input", e => { UI.sdraft.visual.talk_words = e.target.value; touchSettings(); });
