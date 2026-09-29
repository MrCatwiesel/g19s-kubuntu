// ---------------------------------------------------------------- Diashow (Piwigo)
UI.albums = null;
const slCfg = () => UI.sdraft.slideshow;
function renderSlides() {
  if (!UI.sdraft) return;
  const c = slCfg();
  $("#pwUrl").value = c.url || ""; $("#pwUser").value = c.user || ""; $("#pwPass").value = c.password || "";
  $("#slInterval").value = c.interval; $("#slShuffle").checked = !!c.shuffle;
  $("#slRecursive").checked = !!c.recursive; $("#slCaption").checked = !!c.caption;
  document.querySelectorAll("#slFit button").forEach(b => b.classList.toggle("active", b.dataset.fit === c.fit));
  renderSource();
  renderAlbums();
}
function renderSource() {
  const c = slCfg(), folder = c.source === "folder";
  document.querySelectorAll("#slSource button").forEach(b => b.classList.toggle("active", b.dataset.src === (c.source || "piwigo")));
  $("#folderBlock").style.display = folder ? "" : "none";
  $("#pwBlock").style.display = folder ? "none" : "";
  $("#fdPath").value = c.folder || "";
}
$("#slSource").addEventListener("click", e => { const b = e.target.closest("button[data-src]"); if (!b) return;
  slCfg().source = b.dataset.src; touchSettings(); renderSource(); });
$("#fdPath").addEventListener("input", e => { slCfg().folder = e.target.value.trim(); touchSettings(); });
async function browseFolder(path, opts) {
  opts = Object.assign({box: "#fdBrowser", images: true, pick: p => { slCfg().folder = p; touchSettings(); renderSource();
    toast("Ordner übernommen – zum Übernehmen unten speichern."); }}, opts || {});
  const box = $(opts.box);
  let r;
  try { r = await api("/api/folder/list?path=" + encodeURIComponent(path || "~")); }
  catch (err) { box.replaceChildren(el("div", {class: "warnbox", text: err.message})); return; }
  box.replaceChildren(el("div", {class: "fbrowser"},
    el("div", {class: "fhead"},
      r.parent ? el("button", {class: "btn small", onclick: () => browseFolder(r.parent, opts)}, "↑") : null,
      el("b", {style: {flex: "1", wordBreak: "break-all"}, text: r.path}),
      opts.images ? el("span", {class: "muted", text: r.images === 1 ? "1 Bild" : `${r.images} Bilder`}) : null,
      el("button", {class: "btn small primary", onclick: () => { box.replaceChildren(); opts.pick(r.path); }}, "Diesen Ordner wählen")),
    r.dirs.length ? r.dirs.map(dname => el("div", {class: "frow", onclick: () => browseFolder(r.path.replace(/\/$/, "") + "/" + dname, opts)},
      el("span", {text: "📁"}), el("span", {text: dname}))) : el("div", {class: "empty", text: "Keine Unterordner"})));
}
$("#fdBrowse").addEventListener("click", () => browseFolder(slCfg().folder || "~"));
function renderAlbums() {
  const c = slCfg(), box = $("#albums"), sel = new Set(c.albums || []);
  $("#albumSum").textContent = sel.size ? `${sel.size} ausgewählt` : "";
  if (!UI.albums) {
    box.replaceChildren(el("div", {class: "empty", text: sel.size
      ? `${sel.size} Alben ausgewählt – „Alben laden“ klicken, um sie anzuzeigen.` : "Zuerst „Alben laden“ klicken."}));
    return;
  }
  if (!UI.albums.length) { box.replaceChildren(el("div", {class: "empty", text: "Keine Alben sichtbar – bei privaten Alben Benutzer und Passwort eintragen."})); return; }
  const known = new Set(UI.albums.map(a => a.id));
  const rows = UI.albums.map(a => {
    const n = c.recursive ? a.total : a.images;
    return el("label", {class: "album", style: {paddingLeft: (12 + a.level * 22) + "px"}},
      el("input", {type: "checkbox", checked: sel.has(a.id), onchange: e => toggleAlbum(a.id, e.target.checked)}),
      el("span", {class: "an", text: a.name, title: a.path}),
      el("span", {class: "ac", text: n === 1 ? "1 Bild" : `${n} Bilder`}));
  });
  for (const id of sel) if (!known.has(id)) rows.push(el("label", {class: "album missing"},
    el("input", {type: "checkbox", checked: true, onchange: e => toggleAlbum(id, e.target.checked)}),
    el("span", {class: "an", text: `Album #${id} (nicht mehr gefunden)`}), el("span", {class: "ac"})));
  box.replaceChildren(...rows);
}
function toggleAlbum(id, on) {
  const s = new Set(slCfg().albums || []);
  on ? s.add(id) : s.delete(id);
  slCfg().albums = [...s].sort((a, b) => a - b); touchSettings(); renderAlbums();
}
async function loadAlbums(quiet) {
  const c = slCfg();
  if (!c.url) { if (!quiet) toast("Bitte die Adresse der Piwigo-Galerie eintragen.", true); return; }
  $("#pwState").textContent = "Lade Alben …";
  try {
    UI.albums = (await api("/api/piwigo/albums", {body: {url: c.url, user: c.user, password: c.password}})).albums;
    $("#pwState").textContent = `✓ ${UI.albums.length} Alben gefunden`;
  } catch (e) { UI.albums = null; $("#pwState").textContent = ""; if (!quiet) toast(e.message, true); else $("#pwState").textContent = "⚠ " + e.message; }
  renderAlbums();
}
[["#pwUrl", "url"], ["#pwUser", "user"], ["#pwPass", "password"]].forEach(([s, k]) =>
  $(s).addEventListener("input", e => { slCfg()[k] = k === "password" ? e.target.value : e.target.value.trim(); touchSettings(); }));
$("#pwLoad").addEventListener("click", () => loadAlbums(false));
$("#albAll").addEventListener("click", () => { if (UI.albums) { slCfg().albums = UI.albums.map(a => a.id); touchSettings(); renderAlbums(); } });
$("#albNone").addEventListener("click", () => { slCfg().albums = []; touchSettings(); renderAlbums(); });
$("#slInterval").addEventListener("input", e => { slCfg().interval = Math.max(3, parseInt(e.target.value) || 10); touchSettings(); });
$("#slShuffle").addEventListener("change", e => { slCfg().shuffle = e.target.checked; touchSettings(); });
$("#slRecursive").addEventListener("change", e => { slCfg().recursive = e.target.checked; touchSettings(); renderAlbums(); });
$("#slCaption").addEventListener("change", e => { slCfg().caption = e.target.checked; touchSettings(); });
$("#slFit").addEventListener("click", e => { const b = e.target.closest("button[data-fit]"); if (!b) return;
  slCfg().fit = b.dataset.fit; touchSettings(); renderSlides(); });
$("#slTest").addEventListener("click", async () => {
  $("#slTestInfo").textContent = "Teste …";
  try {
    const r = await api("/api/piwigo/test", {body: {slideshow: slCfg()}});
    if (r.image) $("#slPreview").src = r.image;
    $("#slTestInfo").textContent = r.count ? `✓ ${r.count} Bilder gefunden` : "Keine Bilder in den gewählten Alben";
  } catch (e) { $("#slTestInfo").textContent = ""; toast(e.message, true); }
});
// Lieblingsbilder
async function loadFavs() {
  try { UI.favs = (await api("/api/favorites")).favorites; } catch (e) { UI.favs = []; }
  renderFavs();
}
function renderFavs() {
  const box = $("#favs"), favs = UI.favs || [];
  if (UI.sdraft) $("#favOnly").checked = !!slCfg().favorites_only;
  if (!favs.length) { box.replaceChildren(el("div", {class: "empty", text: "Noch keine Lieblingsbilder."})); return; }
  box.replaceChildren(el("div", {class: "muted", style: {margin: "6px 0"}, text: `${favs.length} Lieblingsbild${favs.length === 1 ? "" : "er"}`}),
    el("table", {class: "list"}, el("tbody", {}, ...favs.slice().reverse().map(f => el("tr", {},
      el("td", {style: {width: "1%"}, text: "♥"}),
      el("td", {}, el("b", {text: f.name || String(f.id)}), el("div", {class: "muted", text: (f.source === "folder" ? "Ordner" : "Piwigo") + " · " + (f.time || "")})),
      el("td", {style: {whiteSpace: "nowrap", width: "1%"}},
        f.page && /^https?:/.test(f.page) ? el("a", {class: "btn small", href: f.page, target: "_blank", rel: "noopener"}, "In Piwigo öffnen") : null,
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: async () => {
          try { UI.favs = (await api("/api/favorites", {body: {remove: [f.id]}})).favorites; renderFavs(); } catch (e) { toast(e.message, true); } }}, "✕")))))));
}
$("#favRefresh").addEventListener("click", loadFavs);
$("#favOnly").addEventListener("change", e => { slCfg().favorites_only = e.target.checked; touchSettings(); });
