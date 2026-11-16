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
  $("#visFps").value = v.fps || "15";
  $("#visAdaptive").checked = v.adaptive !== false;
  $("#visXmas").checked = v.xmas_auto !== false;
  $("#visTalkWords").value = v.talk_words || "";
  renderVisualOptions();
  renderVisualScenes();
  visualPreview();
}
function renderVisualOptions() {
  const v = UI.sdraft.visual, style = v.style;
  if (!v[style]) v[style] = {};
  const opts = S.visualOptions[style] || [];
  const deps = new Set(opts.filter(o => o.when).map(o => o.when.key));
  $("#visOpts").replaceChildren(...optionFields(opts, v[style],
    key => { touchSettings(); visualPreview(); if (deps.has(key)) renderVisualOptions(); }));
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
$("#visStyle").addEventListener("change", e => { UI.sdraft.visual.style = e.target.value; touchSettings(); stopVisualScene();
  renderVisualOptions(); renderVisualScenes(); visualPreview(); });
$("#visBacklight").addEventListener("change", e => { UI.sdraft.visual.backlight = e.target.checked; touchSettings(); });
$("#visTitle").addEventListener("change", e => { UI.sdraft.visual.title = e.target.checked; touchSettings(); visualPreview(); });
$("#visTalkWords").addEventListener("input", e => { UI.sdraft.visual.talk_words = e.target.value; touchSettings(); });
$("#visXmas").addEventListener("change", e => { UI.sdraft.visual.xmas_auto = e.target.checked; UI.sdraft.visual.xmas_skip = 0; touchSettings(); });
$("#visFps").addEventListener("change", e => { UI.sdraft.visual.fps = e.target.value; touchSettings(); });
$("#visAdaptive").addEventListener("change", e => { UI.sdraft.visual.adaptive = e.target.checked; touchSettings(); });
// Bewegte Vorschau: Szene (Abspielen, Höhepunkt, Wortbeitrag, Gag) etwa 12 Sekunden lang Bild für Bild abrufen
let visScene = null;
function renderVisualScenes() {
  const style = UI.sdraft && UI.sdraft.visual.style;
  const gags = (S.visualScenes && S.visualScenes[style] || []).filter(([id]) => id.includes(":"));
  $("#visGag").replaceChildren(...(gags.length ? gags.map(([id, label]) => el("option", {value: id, text: label}))
    : [el("option", {value: "", text: "keine Gags in diesem Stil"})]));
  $("#visGag").disabled = $("#visGagGo").disabled = !gags.length;
}
function stopVisualScene() {
  if (visScene) visScene.stop = true;
  visScene = null;
  $("#visStop").hidden = true;
}
async function playVisualScene(scene, seconds = 12) {
  stopVisualScene();
  const run = visScene = {stop: false};
  $("#visStop").hidden = false;
  for (let step = 0; step < seconds * 10 && !run.stop; step++) {
    const t0 = performance.now();
    try {
      const r = await api("/api/vis_scene", {body: {style: UI.sdraft.visual.style, settings: UI.sdraft, scene, step}});
      if (run.stop) break;
      $("#visLcd").src = r.image;
    } catch (e) { break; }
    await new Promise(res => setTimeout(res, Math.max(0, 100 - (performance.now() - t0))));
  }
  if (visScene === run) { stopVisualScene(); visualPreview(); }
}
$("#visPlay").addEventListener("click", () => playVisualScene("play"));
$("#visBoom").addEventListener("click", () => playVisualScene("boom", 10));
$("#visTalk").addEventListener("click", () => playVisualScene("talk", 10));
$("#visGagGo").addEventListener("click", () => { if ($("#visGag").value) playVisualScene($("#visGag").value, 13); });
$("#visStop").addEventListener("click", () => { stopVisualScene(); visualPreview(); });

// Fertige Kombinationen: Stil und passende Optionen auf einen Klick (danach wie gewohnt speichern)
const VIS_PRESETS = [
  ["Ruhiger Abend", {style: "dancer", fps: "10", dancer: {show: "ballet", strobe: "off", keys: "stage"}}],
  ["Party", {style: "lights", fps: "20", lights: {fx: "show", flash: true, strobe: "off"}}],
  ["Weihnachtsfeier", {style: "xmas", xmas_auto: true, xmas: {dance: "pair", gags: true, party: "evening"}}],
  ["Gruselabend", {style: "cellar", cellar: {level: "3", keys: "red"}}],
  ["Ritterfest", {style: "metal", fps: "15", metal: {pyro: "dragon", crowd: true, gags: true, keys: "fire"}}],
];
$("#visPresets").replaceChildren(...VIS_PRESETS.map(([name, p]) => el("button", {class: "btn", type: "button", text: name,
  title: "Stil und Optionen setzen – danach speichern", onclick: () => {
    const v = UI.sdraft.visual;
    for (const [k, val] of Object.entries(p)) {
      if (val && typeof val === "object") v[k] = Object.assign({}, v[k] || {}, val); else v[k] = val;
    }
    touchSettings(); renderVisual(); toast(`„${name}“ eingestellt – noch speichern.`);
  }})));
