// ---------------------------------------------------------------- Uhr: Zifferblätter
// Optionen je Zifferblatt kommen aus CLOCK_OPTIONS des Treibers (S.clockOptions) und werden
// in UI.sdraft.clock[<zifferblatt>] bearbeitet; gespeichert wird mit den übrigen Einstellungen.
function clockDraft(face) {
  const c = UI.sdraft.clock;
  if (!c[face]) c[face] = {};
  return c[face];
}
function renderClock() {
  const sd = UI.sdraft; if (!sd || !S.clockFaces) return;
  if (!UI.clkFace) UI.clkFace = "digital";
  $("#clkFace").replaceChildren(...S.clockFaces.map(([id, label]) =>
    el("option", {value: id, text: label + (S.clockOptions[id] ? "" : " (ohne Einstellungen)"), selected: id === UI.clkFace})));
  renderClockOptions();
  const menu = sd.clock.menu && sd.clock.menu.length ? sd.clock.menu : S.clockFaces.map(f => f[0]);
  $("#clkMenu").replaceChildren(...S.clockFaces.map(([id, label]) => el("label", {},
    el("input", {type: "checkbox", checked: menu.includes(id), onchange: e => {
      let m = S.clockFaces.map(f => f[0]).filter(f => f === id ? e.target.checked : menu.includes(f));
      if (!m.length) { e.target.checked = true; toast("Mindestens ein Zifferblatt muss angeboten werden.", true); return; }
      sd.clock.menu = m.length === S.clockFaces.length ? [] : m;     // leer = alle
      touchSettings(); renderClock(); }}),
    el("span", {text: label}))));
  clockPreview();
}
function renderClockOptions() {
  const face = UI.clkFace, opts = S.clockOptions[face] || [], d = clockDraft(face);
  const box = $("#clkOpts");
  if (!opts.length) { box.replaceChildren(el("p", {class: "hint", text: "Für dieses Zifferblatt gibt es keine Einstellungen."})); return; }
  const changed = () => { touchSettings(); clockPreview(); };
  box.replaceChildren(...opts.map(o => {
    const val = o.key in d ? d[o.key] : o.default;
    if (o.type === "bool")
      return el("label", {class: "check clkopt"}, el("input", {type: "checkbox", checked: !!val,
        onchange: e => { d[o.key] = e.target.checked; changed(); }}), " " + o.label);
    if (o.type === "choice")
      return el("label", {class: "field clkopt", style: {maxWidth: "300px"}}, el("span", {text: o.label}),
        el("select", {value: val, onchange: e => { d[o.key] = e.target.value; changed(); }},
          o.choices.map(([v, l]) => el("option", {value: v, text: l}))));
    if (o.type === "color") {
      const pick = el("input", {type: "color", value: hex(val || [255, 255, 255]), disabled: !val,
        oninput: e => { d[o.key] = rgb(e.target.value); changed(); }});
      const sel = el("select", {value: val ? "own" : "std", style: {width: "auto"}, onchange: e => {
        d[o.key] = e.target.value === "own" ? rgb(pick.value) : null;
        pick.disabled = e.target.value !== "own"; changed(); }},
        el("option", {value: "std", text: o.none_label}), el("option", {value: "own", text: "Eigene Farbe"}));
      return el("div", {class: "field clkopt"}, el("span", {text: o.label}), el("div", {class: "row"}, sel, pick));
    }
    if (o.type === "cities") {
      const list = (val && val.length ? val : o.default).slice();
      const opts6 = [...list, ...Array(Math.max(0, 6 - list.length)).fill(null)].slice(0, 6);
      return el("div", {class: "field clkopt"}, el("span", {text: o.label + " (bis zu 6)"}),
        el("div", {class: "clkcities"}, opts6.map((c, i) => el("select", {value: c ? c.tz : "", onchange: e => {
          opts6[i] = e.target.value ? {name: S.worldCities.find(w => w[1] === e.target.value)[0], tz: e.target.value} : null;
          const next = opts6.filter(Boolean);
          if (!next.length) { toast("Mindestens eine Stadt wählen.", true); e.target.value = c ? c.tz : ""; return; }
          d[o.key] = next; changed(); }},
          el("option", {value: "", text: "—"}),
          S.worldCities.map(([n, tz]) => el("option", {value: tz, text: n}))))));
    }
    return null;
  }));
}
let clkTimer = null;
function clockPreview() {
  clearTimeout(clkTimer);
  clkTimer = setTimeout(async () => {
    if (UI.tab !== "settings") return;
    try { $("#clkLcd").src = (await api("/api/preview", {body: {page: S.pageIds.indexOf("clock"), profile: UI.pvProfile || "M1",
      settings: UI.sdraft, pidx: UI.pidx, face: UI.clkFace}})).image; }
    catch (e) { /* Vorschau ist nicht kritisch */ }
  }, 200);
}
$("#clkFace").addEventListener("change", e => { UI.clkFace = e.target.value; renderClockOptions(); clockPreview(); });
$("#clkAll").addEventListener("click", () => { UI.sdraft.clock.menu = []; touchSettings(); renderClock(); });
