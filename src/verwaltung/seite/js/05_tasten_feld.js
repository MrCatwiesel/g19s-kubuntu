// ---------------------------------------------------------------- Tasten: Profile & Tastenfeld
function renderProfiles() {
  renderProfileCard();
  const box = $("#profiles"); box.replaceChildren();
  for (const p of PROFILES) box.append(el("button", {class: p === UI.profile ? "active" : "",
    onclick: () => { if (confirmLeave()) { UI.profile = p; selectKey(UI.gkey, true); renderProfiles(); renderKeypad(); renderEditor(); } }},
    el("span", {class: "swatch", style: {background: profileColor(p)}}), p));
}
function renderProfileCard() {
  const list = S.macros.profiles, n = list.length;
  $("#profSel").replaceChildren(...list.map((p, i) => el("option", {value: i, selected: i === UI.pidx,
    text: `${i + 1}. ${p.name}${i === S.active ? "   ✓ aktiv" : ""}`})));
  $("#profUp").disabled = UI.pidx === 0; $("#profDown").disabled = UI.pidx === n - 1;
  $("#profDel").disabled = n <= 1; $("#profNew").disabled = $("#profCopy").disabled = n >= S.maxProfiles;
  const cols = profColors();
  $("#profColors").replaceChildren(...PROFILES.map(layer => el("label", {title: "Beleuchtungsfarbe für " + layer},
    el("input", {type: "color", value: hex(cols[layer]), onchange: e => setProfileColor(layer, e.target.value)}), layer)));
  $("#profActive").replaceChildren(UI.pidx === S.active
    ? el("span", {class: "activebadge"}, el("span", {class: "dot ok"}), "An der Tastatur aktiv")
    : el("button", {class: "btn small primary", onclick: activateProfile}, "An der Tastatur aktivieren"));
}
function renderKeypad() {
  const box = $("#keypad"); box.replaceChildren();
  const prof = layerKeys();
  for (const k of GKEYS) {
    const e = prof[k], t = typeOf(e), label = entryLabel(e);
    const b = el("button", {class: "gkey" + (k === UI.gkey ? " sel" : "") + (e ? " has" : ""),
      style: {"--pc": profileColor(UI.profile)}, title: TYPE_BY_ID[t].label,
      onclick: () => { if (k !== UI.gkey && confirmLeave()) { selectKey(k, true); renderKeypad(); renderEditor(); } }},
      el("span", {class: "gnum", text: k}),
      el("span", {class: "gic", text: e ? TYPE_BY_ID[t].icon : ""}),
      el("span", {class: "glabel", text: label || fKeyText(k, UI.profile)}),
      el("span", {class: "bar"}));
    box.append(b);
  }
}
function confirmLeave() {
  if (!UI.draftDirty) return true;
  if (confirm("Die Änderungen an " + UI.gkey + " wurden noch nicht übernommen. Verwerfen?")) { UI.draftDirty = false; markTabs(); return true; }
  return false;
}
function selectKey(k, reset) {
  stopRecording(false);
  UI.gkey = k;
  if (reset) {
    const e = layerKeys()[k];
    UI.draft = {name: (e && e.name) || "", type: typeOf(e), text: (e && e.text) || "",
      combo: comboList(e && e.combo), steps: clone((e && e.steps) || []), open: (e && e.open) || "",
      run: (e && e.run) || "", radio: (e && e.radio) || "", media: (e && e.media) || "play-pause",
      volume: (e && e.volume) || "up", snippets: (e && e.snippets) || "*",
      timer: Object.assign({mode: "timer", minutes: 5, work: 25, break: 5}, (e && e.timer) || {}),
      sleep: (e && e.sleep) || 30};
    UI.draftDirty = false; markTabs();
  }
}
function touchDraft() { UI.draftDirty = true; markTabs(); updateApplyState(); }
