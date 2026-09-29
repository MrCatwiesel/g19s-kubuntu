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
