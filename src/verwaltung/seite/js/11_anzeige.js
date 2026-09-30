// ---------------------------------------------------------------- Beleuchtung & Display
function renderSettings() {
  const sd = UI.sdraft; if (!sd) return;
  $("#keepBacklight").checked = !!sd.keep_backlight;
  const on = sd.brightness !== null && sd.brightness !== undefined;
  $("#brightOn").checked = on; $("#bright").disabled = !on;
  $("#bright").value = on ? sd.brightness : 100;
  $("#brightVal").textContent = on ? sd.brightness + " %" : "unverändert";
  const enabled = layerPages().M1;
  const sp = $("#startPage");
  sp.replaceChildren(...enabled.map(id => { const i = S.pageIds.indexOf(id);
    return el("option", {value: i, text: S.pages[i], selected: i === sd.start_page}); }));
  if (!enabled.includes(S.pageIds[sd.start_page])) sp.selectedIndex = 0;
  $("#pvPages").replaceChildren(...S.pages.map((n, i) => el("option", {value: i, text: "Vorschau: " + n, selected: i === UI.pvPage})));
  renderPageList();
  renderClock();
  const n = sd.night;
  $("#nightOn").checked = !!n.enabled; $("#nightStart").value = n.start; $("#nightEnd").value = n.end;
  document.querySelectorAll("#nightMode button").forEach(b => b.classList.toggle("active", b.dataset.mode === n.mode));
  $("#nightDimRow").style.display = n.mode === "dim" ? "" : "none";
  $("#nightBright").value = n.brightness; $("#nightBrightVal").textContent = n.brightness + " %";
  $("#nightBacklight").checked = !!n.backlight_off;
  const ss = sd.screensaver;
  $("#saverOn").checked = !!ss.enabled; $("#saverMin").value = ss.minutes;
  $("#saverPage").replaceChildren(...S.pageIds.map((id, i) => el("option", {value: id, text: S.pages[i], selected: id === ss.page})));
  $("#volStep").value = sd.volume_step;
  $("#timerSound").checked = sd.timer_sound;
  $("#pvProfiles").replaceChildren(...PROFILES.map(p => el("button", {class: p === UI.pvProfile ? "active" : "", text: p,
    onclick: () => { UI.pvProfile = p; renderSettings(); refreshPreview(); }})));
}
function layerPages() { return UI.sdraft.layer_pages; }   // vom Server immer für M1–M3 vollständig
function pageTarget() {
  const profs = S.macros.profiles;
  if (UI.pageScope === undefined || UI.pageScope >= profs.length) UI.pageScope = -1;
  if (UI.pageScope === -1) return {lp: layerPages(), commit: () => { touchSettings(); renderSettings(); refreshPreview(); }};
  const p = profs[UI.pageScope];
  if (!p.pages) return {lp: null, profile: p};
  const lp = clone(p.pages);
  return {lp, profile: p, commit: () => setProfilePages(UI.pageScope, lp)};
}
async function setProfilePages(i, pages) {
  const m = clone(S.macros), p = m.profiles[i];
  if (pages) p.pages = pages; else delete p.pages;
  await saveProfiles(m, pages ? `Displayseiten für „${p.name}“ gespeichert.` : `„${p.name}“ verwendet wieder die Standard-Seiten.`, UI.pidx, S.active);
  renderSettings(); refreshPreview();
}
function renderPageList() {
  const L = UI.pvProfile, t = pageTarget(), profs = S.macros.profiles;
  $("#plScope").replaceChildren(el("option", {value: -1, text: "Alle Profile (Standard)", selected: UI.pageScope === -1}),
    ...profs.map((p, i) => el("option", {value: i, text: `Profil ${i + 1}: ${p.name}` + (p.pages ? " – eigene Seiten" : ""), selected: UI.pageScope === i})));
  $("#plOwnOff").style.display = t.lp && t.profile ? "" : "none";
  $("#plCopy").style.display = t.lp ? "" : "none";
  $("#plLayers").replaceChildren(...PROFILES.map(p => el("button", {class: p === L ? "active" : "", text: p,
    onclick: () => { UI.pvProfile = p; renderSettings(); refreshPreview(); }})));
  if (!t.lp) {
    $("#pageList").replaceChildren(el("div", {class: "empty"},
      `„${t.profile.name}“ verwendet die Standard-Seiten (Alle Profile). `,
      el("button", {class: "btn small primary", onclick: () => setProfilePages(UI.pageScope, clone(layerPages()))}, "Eigene Seiten für dieses Profil festlegen")));
    return;
  }
  const lp = t.lp, on = lp[L];
  const order = [...on, ...S.pageIds.filter(id => !on.includes(id))];
  $("#pageList").replaceChildren(...order.map(id => {
    const enabled = on.includes(id), pos = on.indexOf(id);
    return el("div", {class: "pagerow" + (enabled ? "" : " off")},
      el("input", {type: "checkbox", checked: enabled, onchange: e => {
        if (e.target.checked) lp[L].push(id);
        else if (lp[L].length > 1) lp[L] = lp[L].filter(x => x !== id);
        else { e.target.checked = true; toast("Mindestens eine Seite muss eingeschaltet bleiben.", true); return; }
        t.commit(); }}),
      el("span", {class: "pn", text: S.pages[S.pageIds.indexOf(id)]}),
      el("button", {class: "btn icon small", title: "nach oben", disabled: !enabled || pos === 0,
        onclick: () => { [lp[L][pos - 1], lp[L][pos]] = [lp[L][pos], lp[L][pos - 1]]; t.commit(); }}, "↑"),
      el("button", {class: "btn icon small", title: "nach unten", disabled: !enabled || pos === on.length - 1,
        onclick: () => { [lp[L][pos + 1], lp[L][pos]] = [lp[L][pos], lp[L][pos + 1]]; t.commit(); }}, "↓"));
  }));
}
$("#plScope").addEventListener("change", e => { UI.pageScope = parseInt(e.target.value); renderSettings(); });
$("#plOwnOff").addEventListener("click", () => { if (confirm("Eigene Seiten dieses Profils löschen und wieder die Standard-Seiten verwenden?")) setProfilePages(UI.pageScope, null); });
$("#plCopy").addEventListener("click", () => {
  const t = pageTarget(); if (!t.lp) return;
  const src = t.lp[UI.pvProfile];
  for (const l of PROFILES) t.lp[l] = [...src];
  t.commit(); toast(`Seiten von ${UI.pvProfile} für alle Ebenen übernommen.`);
});
$("#keepBacklight").addEventListener("change", e => { UI.sdraft.keep_backlight = e.target.checked; touchSettings(); });
$("#brightOn").addEventListener("change", e => { UI.sdraft.brightness = e.target.checked ? 100 : null; touchSettings(); renderSettings(); });
$("#bright").addEventListener("input", e => { UI.sdraft.brightness = parseInt(e.target.value); $("#brightVal").textContent = e.target.value + " %"; touchSettings(); });
$("#startPage").addEventListener("change", e => { UI.sdraft.start_page = parseInt(e.target.value); touchSettings(); });
$("#pvPages").addEventListener("change", e => { UI.pvPage = parseInt(e.target.value); refreshPreview(); });
$("#nightOn").addEventListener("change", e => { UI.sdraft.night.enabled = e.target.checked; touchSettings(); });
$("#nightStart").addEventListener("change", e => { UI.sdraft.night.start = e.target.value; touchSettings(); });
$("#nightEnd").addEventListener("change", e => { UI.sdraft.night.end = e.target.value; touchSettings(); });
$("#nightMode").addEventListener("click", e => { const b = e.target.closest("button[data-mode]"); if (!b) return;
  UI.sdraft.night.mode = b.dataset.mode; touchSettings(); renderSettings(); });
$("#nightBright").addEventListener("input", e => { UI.sdraft.night.brightness = parseInt(e.target.value);
  $("#nightBrightVal").textContent = e.target.value + " %"; touchSettings(); });
$("#nightBacklight").addEventListener("change", e => { UI.sdraft.night.backlight_off = e.target.checked; touchSettings(); });
$("#saverOn").addEventListener("change", e => { UI.sdraft.screensaver.enabled = e.target.checked; touchSettings(); });
$("#saverMin").addEventListener("input", e => { UI.sdraft.screensaver.minutes = Math.max(1, parseInt(e.target.value) || 5); touchSettings(); });
$("#saverPage").addEventListener("change", e => { UI.sdraft.screensaver.page = e.target.value; touchSettings(); });
$("#volStep").addEventListener("input", e => { UI.sdraft.volume_step = Math.max(1, Math.min(25, parseInt(e.target.value) || 5)); touchSettings(); });
// Vorschau nach Änderungen an den Einstellungen verzögert neu laden (touchSettings ruft das auf)
let pvTimer = null;
function schedulePreview() { clearTimeout(pvTimer); pvTimer = setTimeout(refreshPreview, 250); }
async function refreshPreview() {
  if (UI.tab !== "settings") return;
  try { $("#lcd").src = (await api("/api/preview", {body: {page: UI.pvPage, profile: UI.pvProfile, settings: UI.sdraft,
    pidx: UI.pidx}})).image; }
  catch (e) { /* Vorschau ist nicht kritisch */ }
}
$("#timerSound").addEventListener("change", e => { UI.sdraft.timer_sound = e.target.checked; touchSettings(); });
