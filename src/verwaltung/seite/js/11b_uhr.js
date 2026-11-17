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
  box.replaceChildren(...optionFields(opts, d, () => { touchSettings(); clockPreview(); }));
}
// Formularfelder für Optionen (CLOCK_OPTIONS/VISUAL_OPTIONS): d = Entwurf des Zifferblatts bzw. Stils
// Wirkt die Option bei den aktuellen Werten? (when: {key, in} bzw. {key, not}; sonst ausgeblendet)
function optionVisible(o, d, opts) {
  const w = o.when; if (!w) return true;
  const ref = opts.find(x => x.key === w.key);
  const v = w.key in d ? d[w.key] : ref && ref.default;
  return w.in ? w.in.includes(v) : !(w.not || []).includes(v);
}
function helpMark(o) { return o.help ? el("i", {class: "helpi", title: o.help, text: "i"}) : null; }
function optionFields(opts, d, changed) {
  let group = null;
  const groups = new Set(opts.map(o => o.group).filter(Boolean));
  return opts.flatMap(o => {
    if (!optionVisible(o, d, opts)) return [];
    const head = groups.size > 1 && o.group && o.group !== group ? [el("div", {class: "optgroup", text: o.group})] : [];
    if (o.group) group = o.group;
    const field = optionField(o, d, () => changed(o.key));
    return field ? [...head, field] : head;
  });
}
function optionField(o, d, changed) {
  {
    const val = o.key in d ? d[o.key] : o.default;
    if (o.type === "bool")
      return el("label", {class: "check clkopt"}, el("input", {type: "checkbox", checked: !!val,
        onchange: e => { d[o.key] = e.target.checked; changed(); }}), " " + o.label, helpMark(o));
    if (o.type === "choice")
      return el("label", {class: "field clkopt", style: {maxWidth: "300px"}}, el("span", {}, o.label, helpMark(o)),
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
    if (o.type === "birthdays") return birthdayFields(o, d, changed);
    if (o.type === "photos") return waltzPhotoFields(o);
    return null;
  }
}
// Geburtstagsliste (Überraschungsparty, Festkalender): Name, Tag, Monat, Geburtsjahr (leer = Alter unbekannt)
function birthdayFields(o, d, changed) {
  const box = el("div", {class: "field clkopt"});
  const list = () => (d[o.key] = Array.isArray(d[o.key]) ? d[o.key] : (o.default || []).slice());
  const num = (b, k, min, max, w, ph) => el("input", {type: "number", min, max, value: b[k] || "", placeholder: ph,
    style: {width: w}, oninput: e => { b[k] = parseInt(e.target.value, 10) || (k === "year" ? 0 : 1); changed(); }});
  function draw() {
    const rows = list().map((b, i) => el("div", {class: "row bdayrow"},
      el("input", {type: "text", value: b.name || "", maxlength: 20, placeholder: "Name", style: {width: "150px"},
        oninput: e => { b.name = e.target.value; changed(); }}),
      num(b, "day", 1, 31, "64px", "Tag"), num(b, "month", 1, 12, "64px", "Monat"),
      num(b, "year", 1900, 2100, "84px", "Jahr"),
      el("button", {class: "btn", type: "button", text: "✕", title: "Entfernen",
        onclick: () => { list().splice(i, 1); changed(); draw(); }})));
    box.replaceChildren(el("span", {text: o.label + " (Jahr freiwillig – dann steht das Alter auf den Ballons)"}),
      ...rows,
      el("button", {class: "btn", type: "button", text: "+ Geburtstag", onclick: () => {
        const now = new Date();
        list().push({name: "", day: now.getDate(), month: now.getMonth() + 1, year: 0}); changed(); draw(); }}));
  }
  draw();
  return box;
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
