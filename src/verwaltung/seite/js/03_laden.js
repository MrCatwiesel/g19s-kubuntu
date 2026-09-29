// ---------------------------------------------------------------- Laden
async function loadState() {
  const d = await api("/api/state");
  S.macros = d.macros; S.settings = d.settings; S.keys = d.keys; S.media = d.media; S.pages = d.pages; S.pageIds = d.page_ids; S.volume = d.volume;
  S.clockFaces = d.clock_faces; S.clockOptions = d.clock_options; S.worldCities = d.world_cities;
  S.active = d.active; S.maxProfiles = d.max_profiles;
  if (UI.pidx === undefined) UI.pidx = d.active;
  UI.pidx = Math.min(UI.pidx, S.macros.profiles.length - 1);
  S.keyLabel = Object.fromEntries(d.keys.map(k => [k.name, k.label]));
  S.chars = new Set([...d.chars, ...d.dead]); S.mtimes = d.mtimes; S.service = d.service;
  S.tools = d.tools; S.paths = d.paths;
  if (d.macros_error) toast(d.macros_error, true);
  UI.sdraft = clone(S.settings); UI.sDirty = false;
  selectKey(UI.gkey, true);
  renderAll();
}
function renderAll() {
  renderProfiles(); renderKeypad(); renderEditor(); renderStations(); renderAlarmClock(); renderSnippets(); renderSettings(); renderSlides(); renderInfo();
  renderAutoBackup(); renderFavs();
  renderServiceInfo(); renderSavebar(); renderPaths();
}
