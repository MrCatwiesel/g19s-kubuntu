// ---------------------------------------------------------------- Reiter
$("#nav").addEventListener("click", e => {
  const b = e.target.closest("button[data-tab]"); if (!b) return;
  UI.tab = b.dataset.tab;
  document.querySelectorAll("#nav button").forEach(x => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.id === "tab-" + UI.tab));
  if (UI.tab === "service") { refreshService(); loadBackupStatus(); }
  if (UI.tab === "radio") loadSongs();
  if (UI.tab === "slides") loadFavs();
  if (UI.tab === "settings") { refreshPreview(); clockPreview(); }
  if (UI.tab === "info") refreshHardware();
  if (UI.tab === "slides" && !UI.albums && slCfg().url && slCfg().source !== "folder") loadAlbums(true);
  renderSavebar();
});
function markTabs() {
  const n = id => $(`#nav button[data-tab=${id}]`);
  n("keys").classList.toggle("dirty", UI.draftDirty);
  n("radio").classList.toggle("dirty", UI.sDirty);
  n("snippets").classList.toggle("dirty", UI.sDirty);
  n("settings").classList.toggle("dirty", UI.sDirty);
  n("slides").classList.toggle("dirty", UI.sDirty);
  n("info").classList.toggle("dirty", UI.sDirty);
}

// Unterreiter in „Beleuchtung & Display“ (der zuletzt gewählte bleibt gemerkt)
function store(key, val) { try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); } catch (e) { return null; } }
function showSub(sub) {
  sub = ["display", "clock", "visual", "night"].includes(sub) ? sub : "display";
  document.querySelectorAll("#setSub button[data-sub]").forEach(b => b.classList.toggle("active", b.dataset.sub === sub));
  document.querySelectorAll("#tab-settings .card[data-sub]").forEach(c => { c.hidden = c.dataset.sub !== sub; });
  store("g19s.sub", sub);
  if (sub === "clock") clockPreview();
  if (sub === "visual" && typeof visualPreview === "function") visualPreview();
  if (sub === "display") refreshPreview();
}
$("#setSub").addEventListener("click", e => {
  const b = e.target.closest("button[data-sub]"); if (!b) return;
  $("#setSearch").value = ""; applySearch(""); showSub(b.dataset.sub);
});
showSub(store("g19s.sub"));
// Suche über alle Karten von „Beleuchtung & Display“ (Überschrift, Beschriftungen, Hinweise)
function applySearch(q) {
  q = q.trim().toLowerCase();
  document.querySelectorAll("#tab-settings .card[data-sub]").forEach(c => {
    if (!q) { c.classList.remove("nomatch"); return; }
    const hit = c.textContent.toLowerCase().includes(q) ||
      [...c.querySelectorAll("option")].some(o => o.textContent.toLowerCase().includes(q));
    c.hidden = false; c.classList.toggle("nomatch", !hit);
    if (hit) c.classList.remove("collapsed");
  });
  if (!q) showSub(store("g19s.sub"));
}
$("#setSearch").addEventListener("input", e => applySearch(e.target.value));
// Karten einklappen (Klick auf die Überschrift, gemerkt) und Änderungspunkt je Karte
function cardKey(c) { const h = c.querySelector("h2"); return h ? h.firstChild.textContent.trim() : ""; }
const collapsed = new Set(JSON.parse(store("g19s.collapsed") || "[]"));
document.querySelectorAll(".card").forEach(c => {
  const h = c.querySelector("h2"); if (!h) return;
  h.append(el("span", {class: "dot", title: "Ungespeicherte Änderung"}));
  if (collapsed.has(cardKey(c))) c.classList.add("collapsed");
  h.addEventListener("click", e => {
    if (e.target.closest("button, input, select")) return;
    c.classList.toggle("collapsed");
    c.classList.contains("collapsed") ? collapsed.add(cardKey(c)) : collapsed.delete(cardKey(c));
    store("g19s.collapsed", JSON.stringify([...collapsed]));
  });
  const mark = e => { if (!e.target.closest(".subnav")) { c.classList.add("dirty"); markSubs(); } };
  c.addEventListener("input", mark); c.addEventListener("change", mark); c.addEventListener("click", e => {
    if (e.target.closest("button.btn") && !e.target.closest(".visscene, #visPresets")) mark(e); });
});
function markSubs() {
  document.querySelectorAll("#setSub button[data-sub]").forEach(b => b.classList.toggle("dirty",
    !!document.querySelector(`#tab-settings .card.dirty[data-sub=${b.dataset.sub}]`)));
}
function clearCardDirty() { document.querySelectorAll(".card.dirty").forEach(c => c.classList.remove("dirty")); markSubs(); }
