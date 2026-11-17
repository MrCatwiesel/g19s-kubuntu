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
  $("#visFest").checked = v.fest_auto !== false;
  $("#visCover").checked = !!v.cover_colors;
  $("#visWeather").checked = v.weather_fx !== false;
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
// Walzer: eigenes Foto je Ort (wird sofort gespeichert – unabhängig von „Speichern“, wie eine Datei)
function waltzPhotoFields(o) {
  const box = el("div", {class: "field clkopt"}, el("span", {}, o.label, helpMark(o)));
  const grid = el("div", {class: "wzphotos"});
  box.append(grid, el("p", {class: "hint", text: "Das Foto wird auf Displaygröße zugeschnitten (320 × 214) und " +
    "sofort gespeichert. Nachts und in der Dämmerung wird es automatisch abgedunkelt."}));
  api("/api/waltz_photos").then(r => {
    grid.replaceChildren(...S.waltzPlaces.map(([id, label]) => {
      const img = el("img", {class: "wzthumb", alt: "", src: r.photos[id] || ""});
      img.hidden = !r.photos[id];
      const none = el("span", {class: "hint", text: "gemalt"}); none.hidden = !!r.photos[id];
      const del = el("button", {class: "btn", type: "button", text: "✕", title: "Foto entfernen", hidden: !r.photos[id]});
      const file = el("input", {type: "file", accept: "image/*", hidden: true});
      const set = url => { img.src = url || ""; img.hidden = !url; none.hidden = !!url; del.hidden = !url; visualPreview(); };
      file.addEventListener("change", async () => {
        const f = file.files[0]; file.value = ""; if (!f) return;
        try { set((await api("/api/waltz_photo", {body: {place: id, image: await shrinkImage(f)}})).photo);
              toast(`Foto für „${label}“ gespeichert.`); }
        catch (e) { toast(e.message, true); }
      });
      del.addEventListener("click", async () => {
        try { set((await api("/api/waltz_photo", {body: {place: id, image: null}})).photo); } catch (e) { toast(e.message, true); }
      });
      return el("div", {class: "wzphoto"}, el("b", {text: label}), img, none,
        el("div", {class: "row"}, el("button", {class: "btn", type: "button", text: "Foto wählen …", onclick: () => file.click()}), del, file));
    }));
  }).catch(e => grid.replaceChildren(el("p", {class: "hint", text: e.message})));
  return box;
}
// Großes Foto vor dem Hochladen verkleinern (höchstens 1280 Pixel breit, JPEG)
async function shrinkImage(file) {
  const bmp = await createImageBitmap(file);
  const k = Math.min(1, 1280 / bmp.width, 1280 / bmp.height);
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.9);
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
$("#visCover").addEventListener("change", e => { UI.sdraft.visual.cover_colors = e.target.checked; touchSettings(); });
$("#visWeather").addEventListener("change", e => { UI.sdraft.visual.weather_fx = e.target.checked; touchSettings(); });
$("#visFest").addEventListener("change", e => { UI.sdraft.visual.fest_auto = e.target.checked; UI.sdraft.visual.fest_skip = ""; touchSettings(); });
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
  ["Walzerabend", {style: "waltz", fps: "15", waltz: {place: "ballroom", daytime: "evening", clothes: "ball", gags: true}}],
];
$("#visPresets").replaceChildren(...VIS_PRESETS.map(([name, p]) => el("button", {class: "btn", type: "button", text: name,
  title: "Stil und Optionen setzen – danach speichern", onclick: () => {
    const v = UI.sdraft.visual;
    for (const [k, val] of Object.entries(p)) {
      if (val && typeof val === "object") v[k] = Object.assign({}, v[k] || {}, val); else v[k] = val;
    }
    touchSettings(); renderVisual(); toast(`„${name}“ eingestellt – noch speichern.`);
  }})));
