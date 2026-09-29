// ---------------------------------------------------------------- Abgleich im Hintergrund
$("#extReload").addEventListener("click", async () => {
  const d = await api("/api/state"); S.macros = d.macros; S.mtimes.macros = d.mtimes.macros; S.active = d.active;
  UI.pidx = Math.min(UI.pidx, S.macros.profiles.length - 1);
  afterProfileChange(); $("#extBanner").classList.remove("show");
});
async function poll() {
  let d; try { d = await api("/api/poll"); } catch (e) { return; }
  if (d.service.active !== S.service.active || d.service.enabled !== S.service.enabled) { S.service = d.service; renderServiceInfo(); }
  if (d.mtimes.macros !== S.mtimes.macros) {
    if (UI.draftDirty) $("#extBanner").classList.add("show");
    else { const s = await api("/api/state"); S.macros = s.macros; S.mtimes.macros = s.mtimes.macros; S.active = s.active;
      UI.pidx = Math.min(UI.pidx, S.macros.profiles.length - 1);
      afterProfileChange(); toast("Tastenbelegung wurde aktualisiert (z. B. durch MR-Aufnahme)."); }
  }
  if (d.active !== S.active) { S.active = d.active; renderProfileCard(); }
  if (d.mtimes.settings !== S.mtimes.settings && !UI.sDirty) {
    const s = await api("/api/state"); S.settings = s.settings; S.mtimes.settings = s.mtimes.settings; UI.sdraft = clone(S.settings); renderAll();
  }
  const cur = d.radio ? d.radio.url : null;
  if ((UI.testing && UI.testing.url) !== cur) { UI.testing = d.radio; renderStations(); renderResults(); }
}
setInterval(poll, 3000);
window.addEventListener("beforeunload", e => {
  fetch("/api/bye", {method: "POST", headers: {"X-Token": TOKEN}, keepalive: true}).catch(() => {});
  if (UI.draftDirty || UI.sDirty) { e.preventDefault(); e.returnValue = ""; }
});
if (!TOKEN) lost("Sitzung fehlt", "Bitte die Verwaltung über das Anwendungsmenü „G19s-Verwaltung“ öffnen.");
else loadState().catch(e => toast(e.message, true));
