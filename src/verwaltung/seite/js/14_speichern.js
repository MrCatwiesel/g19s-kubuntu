// ---------------------------------------------------------------- Speichern (Einstellungen + Sender)
function renderSavebar() {
  const show = UI.sDirty && ["radio", "snippets", "settings", "slides", "info", "service"].includes(UI.tab);
  $("#savebar").classList.toggle("show", show);
}
$("#saveSettings").addEventListener("click", async () => {
  const bad = UI.sdraft.stations.find(s => s.url && !/^https?:\/\//i.test(s.url));
  if (bad) { toast(`Die Stream-Adresse von „${bad.name || bad.url}“ muss mit http:// oder https:// beginnen.`, true); return; }
  const empty = UI.sdraft.stations.filter(s => !s.url).length;
  try {
    const r = await api("/api/settings", {body: {settings: UI.sdraft}});
    S.settings = r.settings; S.mtimes.settings = r.mtime; UI.sdraft = clone(r.settings); UI.sDirty = false;
    markTabs(); renderAll();
    toast("Gespeichert – der Treiber übernimmt die Einstellungen sofort." + (empty ? ` (${empty} Sender ohne Adresse entfernt)` : ""));
  } catch (e) { toast(e.message, true); }
});
$("#discardSettings").addEventListener("click", () => {
  UI.sdraft = clone(S.settings); UI.sDirty = false; markTabs(); renderAll(); refreshPreview();
});
