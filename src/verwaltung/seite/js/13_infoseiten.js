// ---------------------------------------------------------------- Infoseiten
const NEWS_PRESETS = [["tagesschau", "https://www.tagesschau.de/index~rss2.xml"], ["heise", "https://www.heise.de/rss/heise-atom.xml"],
  ["SPIEGEL", "https://www.spiegel.de/schlagzeilen/index.rss"], ["Golem", "https://rss.golem.de/rss.php?feed=RSS2.0"]];
function renderNews() {
  const sd = UI.sdraft;
  const feeds = sd.news.feeds, box = $("#newsFeeds");
  box.replaceChildren(...feeds.map((f, i) => {
    const info = el("span", {class: "muted"});
    return el("div", {class: "feedrow"},
      el("div", {class: "row", style: {flexWrap: "nowrap"}},
        el("input", {type: "text", value: f.name || "", placeholder: "Name", style: {flex: "1"}, oninput: e => { f.name = e.target.value; touchSettings(); }}),
        el("input", {type: "url", value: f.url || "", placeholder: "https://…/rss.xml", style: {flex: "3"}, oninput: e => { f.url = e.target.value.trim(); touchSettings(); }}),
        el("button", {class: "btn small", onclick: async () => { info.textContent = "prüfe …";
          try { const r = await api("/api/news/test", {body: f}); info.textContent = `✓ ${r.count} Meldungen – „${r.first}“`; }
          catch (e) { info.textContent = "✗ " + e.message; } }}, "Testen"),
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => { feeds.splice(i, 1); touchSettings(); renderNews(); }}, "✕")),
      info);
  }));
  if (!feeds.length) box.append(el("div", {class: "empty", text: "Keine Feeds – unten hinzufügen."}));
  $("#newsPresets").replaceChildren(...NEWS_PRESETS.filter(([n, u]) => !feeds.some(f => f.url === u)).map(([n, u]) =>
    el("button", {class: "btn small", onclick: () => { feeds.push({name: n, url: u}); touchSettings(); renderNews(); }}, "+ " + n)));
}
$("#newsAdd").addEventListener("click", () => { UI.sdraft.news.feeds.push({name: "", url: ""}); touchSettings(); renderNews(); });
const VIDEO_PRESETS = [["Tagesschau in 100 Sekunden", "https://www.tagesschau.de/multimedia/sendung/tagesschau_in_100_sekunden/podcast-ts100-video-100~podcast.xml"]];
function renderVideo() {
  const sd = UI.sdraft;
  sd.video = sd.video || {feeds: []};
  const feeds = sd.video.feeds, box = $("#videoFeeds");
  box.replaceChildren(...feeds.map((f, i) => {
    const info = el("span", {class: "muted"});
    return el("div", {class: "feedrow"},
      el("div", {class: "row", style: {flexWrap: "nowrap"}},
        el("input", {type: "text", value: f.name || "", placeholder: "Name", style: {flex: "1"}, oninput: e => { f.name = e.target.value; touchSettings(); }}),
        el("input", {type: "url", value: f.url || "", placeholder: "https://…/podcast.xml", style: {flex: "3"}, oninput: e => { f.url = e.target.value.trim(); touchSettings(); }}),
        el("button", {class: "btn small", onclick: async () => { info.textContent = "prüfe …";
          try { const r = await api("/api/video/test", {body: f}); info.textContent = `✓ ${r.count} Videos – „${r.first}“`; }
          catch (e) { info.textContent = "✗ " + e.message; } }}, "Testen"),
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => { feeds.splice(i, 1); touchSettings(); renderVideo(); }}, "✕")),
      info);
  }));
  if (!feeds.length) box.append(el("div", {class: "empty", text: "Keine Video-Feeds – unten hinzufügen."}));
  $("#videoPresets").replaceChildren(...VIDEO_PRESETS.filter(([n, u]) => !feeds.some(f => f.url === u)).map(([n, u]) =>
    el("button", {class: "btn small", onclick: () => { feeds.push({name: n, url: u}); touchSettings(); renderVideo(); }}, "+ " + n)));
}
$("#videoAdd").addEventListener("click", () => { UI.sdraft.video.feeds.push({name: "", url: ""}); touchSettings(); renderVideo(); });
function ytId(url) {
  const m = /(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:watch\?(?:[^#]*&)?v=|embed\/|shorts\/|live\/|v\/))([A-Za-z0-9_-]{11})/.exec(url || "");
  return m ? m[1] : null;
}
function renderVideoLists() {
  const v = UI.sdraft.video;
  v.lists = v.lists || [];
  $("#videoMode").value = v.youtube || "browser";
  $("#videoAutonext").checked = v.autonext !== false;
  $("#ytdlpHint").hidden = (v.youtube || "browser") !== "display";
  const box = $("#videoLists");
  box.replaceChildren(...v.lists.map((lst, li) => {
    lst.items = lst.items || [];
    const msg = el("span", {class: "muted"});
    const rows = lst.items.map((it, i) => {
      const id = ytId(it.url);
      const move = d => { const j = i + d; if (j < 0 || j >= lst.items.length) return;
        [lst.items[i], lst.items[j]] = [lst.items[j], lst.items[i]]; touchSettings(); renderVideoLists(); };
      return el("div", {class: "row videoitem", style: {flexWrap: "nowrap", marginBottom: "4px", alignItems: "center"}},
        id ? el("img", {src: `https://i.ytimg.com/vi/${id}/default.jpg`, alt: "", onerror: e => { e.target.style.visibility = "hidden"; },
                        style: {width: "64px", height: "36px", objectFit: "cover", borderRadius: "4px"}})
           : el("span", {style: {width: "64px", textAlign: "center"}, text: "🎞"}),
        el("input", {type: "text", value: it.title || "", placeholder: "Titel", style: {flex: "3"}, title: it.url,
                     oninput: e => { it.title = e.target.value; touchSettings(); }}),
        el("span", {class: "muted", style: {flex: "1", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis"}, text: it.author || ""}),
        el("button", {class: "btn icon small", title: "nach oben", onclick: () => move(-1)}, "▲"),
        el("button", {class: "btn icon small", title: "nach unten", onclick: () => move(1)}, "▼"),
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => { lst.items.splice(i, 1); touchSettings(); renderVideoLists(); }}, "✕"));
    });
    const link = el("input", {type: "url", placeholder: "YouTube-Link oder Video-Adresse einfügen", style: {flex: "3"}});
    const add = async () => {
      const url = link.value.trim();
      if (!url) return;
      msg.textContent = "hole Titel …";
      try { const r = await api("/api/video/lookup", {body: {url}}); lst.items.push(r); touchSettings(); renderVideoLists(); }
      catch (e) { msg.textContent = "✗ " + e.message; }
    };
    link.addEventListener("keydown", e => { if (e.key === "Enter") add(); });
    const pl = el("input", {type: "url", placeholder: "Playlist-Link (…list=…)", style: {flex: "3"}});
    const takeOver = async () => {
      msg.textContent = "lese Playlist …";
      try {
        const r = await api("/api/video/playlist", {body: {url: pl.value.trim()}});
        const have = new Set(lst.items.map(x => ytId(x.url)));
        const fresh = r.items.filter(x => !have.has(ytId(x.url)));
        lst.items.push(...fresh); touchSettings(); renderVideoLists();
      } catch (e) { msg.textContent = "✗ " + e.message; }
    };
    return el("div", {class: "feedrow videolist"},
      el("div", {class: "row", style: {flexWrap: "nowrap"}},
        el("input", {type: "text", value: lst.name || "", placeholder: "Name der Liste (z. B. Musik)", style: {flex: "1", fontWeight: "600"},
                     oninput: e => { lst.name = e.target.value; touchSettings(); }}),
        el("span", {class: "muted", text: `${lst.items.length} Videos`}),
        el("button", {class: "btn icon small danger", title: "Liste löschen", onclick: () => {
          if (!lst.items.length || confirm(`Liste „${lst.name}“ mit ${lst.items.length} Videos löschen?`)) { v.lists.splice(li, 1); touchSettings(); renderVideoLists(); } }}, "✕")),
      ...rows,
      lst.items.length ? "" : el("div", {class: "empty", text: "Noch keine Videos – Link einfügen."}),
      el("div", {class: "row", style: {flexWrap: "nowrap", marginTop: "4px"}}, link, el("button", {class: "btn small", onclick: add}, "Hinzufügen")),
      el("div", {class: "row", style: {flexWrap: "nowrap", marginTop: "4px"}}, pl,
        el("button", {class: "btn small", onclick: takeOver, title: "Übernimmt die neuesten 15 Videos einer öffentlichen Playlist"}, "Aus Playlist übernehmen")),
      msg);
  }));
  if (!v.lists.length) box.append(el("div", {class: "empty", text: "Noch keine eigene Liste – unten anlegen."}));
}
async function checkYtdlp() {
  const st = $("#ytdlpState");
  try { const r = await api("/api/video/ytdlp"); st.textContent = r.found ? `✓ yt-dlp ${r.version}` : "yt-dlp nicht installiert"; }
  catch (e) { st.textContent = ""; }
}
$("#videoMode").addEventListener("change", e => { UI.sdraft.video.youtube = e.target.value; touchSettings(); renderVideoLists();
  if (e.target.value === "display") checkYtdlp(); });
$("#videoAutonext").addEventListener("change", e => { UI.sdraft.video.autonext = e.target.checked; touchSettings(); });
$("#videoListAdd").addEventListener("click", () => { UI.sdraft.video.lists = UI.sdraft.video.lists || [];
  UI.sdraft.video.lists.push({name: "Meine Videos", items: []}); touchSettings(); renderVideoLists(); });
function renderNet() {
  const sd = UI.sdraft;
  const hosts = sd.network.hosts, box = $("#netHosts");
  box.replaceChildren(...hosts.map((h, i) => el("div", {class: "row", style: {flexWrap: "nowrap", marginBottom: "6px"}},
    el("input", {type: "text", value: h.name || "", placeholder: "Name (z. B. NAS)", style: {flex: "1"}, oninput: e => { h.name = e.target.value; touchSettings(); }}),
    el("input", {type: "text", value: h.host || "", placeholder: "Adresse oder Name, z. B. 192.168.178.20", style: {flex: "2"}, oninput: e => { h.host = e.target.value.trim(); touchSettings(); }}),
    el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => { hosts.splice(i, 1); touchSettings(); renderNet(); }}, "✕"))));
  if (!hosts.length) box.append(el("div", {class: "empty", text: "Keine Geräte."}));
  const pw = (sd.slideshow || {}).url, m = pw && /^https?:\/\/([^/:]+)(?::(\d+))?/i.exec(pw);
  const pwHost = m ? m[1] + ":" + (m[2] || (/^https/i.test(pw) ? "443" : "80")) : "";
  $("#netPiwigo").style.display = pwHost && !hosts.some(h => h.host === pwHost) ? "" : "none";
  $("#netPiwigo").onclick = () => { hosts.push({name: "Piwigo", host: pwHost}); touchSettings(); renderNet(); };
}
$("#netAdd").addEventListener("click", () => { UI.sdraft.network.hosts.push({name: "", host: ""}); touchSettings(); renderNet(); });
$("#netTest").addEventListener("click", async () => {
  $("#netInfo").textContent = "prüfe …";
  try {
    const r = await api("/api/network/test", {body: {settings: UI.sdraft}});
    $("#netInfo").replaceChildren(el("div", {class: "kv"}, ...r.hosts.flatMap(h => [el("div", {text: h.name}),
      el("div", {text: h.ok ? `✓ ${h.host}${h.ms !== null ? " – " + Math.round(h.ms) + " ms" : ""}` : `✗ ${h.host} – nicht erreichbar`})]),
      el("div", {text: "Dieser PC"}), el("div", {text: r.ip || "–"})));
  } catch (e) { $("#netInfo").textContent = "✗ " + e.message; }
});
$("#warnPopup").addEventListener("change", e => { UI.sdraft.warnings = {popup: e.target.checked}; touchSettings(); });
$("#warnTest").addEventListener("click", async () => {
  $("#warnInfo").textContent = "prüfe …";
  try { const r = await api("/api/warnings/test", {body: {settings: UI.sdraft}});
    $("#warnInfo").textContent = `✓ ${r.place}: ` + (r.alerts.length ? r.alerts.join(", ") : "keine Warnungen"); }
  catch (e) { $("#warnInfo").textContent = "✗ " + e.message; }
});
$("#updFlatpak").addEventListener("change", e => { UI.sdraft.updates = {...UI.sdraft.updates, flatpak: e.target.checked}; touchSettings(); });
$("#updG19s").addEventListener("change", e => { UI.sdraft.updates = {...UI.sdraft.updates, g19s: e.target.checked}; touchSettings(); });
$("#updTest").addEventListener("click", async () => {
  $("#updInfo").textContent = "prüfe … (kann etwas dauern)";
  try { const r = await api("/api/updates/test", {body: {settings: UI.sdraft}});
    $("#updInfo").textContent = `✓ ${r.apt} Paket-Updates` + (r.security ? ` (davon ${r.security} Sicherheit)` : "") +
      (r.flatpak !== null ? `, ${r.flatpak} Flatpak` : "") + (r.reboot ? " – Neustart erforderlich" : ""); }
  catch (e) { $("#updInfo").textContent = "✗ " + e.message; }
});
function renderInfo() {
  const sd = UI.sdraft; if (!sd) return;
  renderNews(); renderVideo(); renderVideoLists(); renderNet();
  if ((UI.sdraft.video || {}).youtube === "display") checkYtdlp();
  $("#warnPopup").checked = sd.warnings.popup;
  $("#updFlatpak").checked = sd.updates.flatpak;
  $("#updG19s").checked = sd.updates.g19s !== false;
  const w = sd.weather;
  $("#wxName").textContent = w.lat !== null && w.lat !== undefined ? (w.name || `${w.lat}, ${w.lon}`) : "noch nicht eingestellt";
  renderCalSources();
  $("#calDays").value = String(sd.calendar.days);
  $("#calRemind").value = String(sd.calendar.remind);
  const n = sd.notifications;
  $("#ntOn").checked = !!n.enabled; $("#ntSec").value = n.seconds; $("#ntIgnore").value = n.ignore || "";
}
$("#wxForm").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("#wxQ").value.trim(); if (!q) return;
  $("#wxResults").replaceChildren(el("div", {class: "empty", text: "Suche …"}));
  let r;
  try { r = (await api("/api/weather/search?q=" + encodeURIComponent(q))).results; }
  catch (err) { $("#wxResults").replaceChildren(el("div", {class: "warnbox", text: err.message})); return; }
  if (!r.length) { $("#wxResults").replaceChildren(el("div", {class: "empty", text: "Kein Ort gefunden."})); return; }
  $("#wxResults").replaceChildren(...r.map(x => el("div", {class: "res", onclick: async () => {
    UI.sdraft.weather = {name: x.name, lat: x.lat, lon: x.lon}; touchSettings(); renderInfo();
    $("#wxResults").replaceChildren(); $("#wxTest").textContent = "prüfe …";
    try { const t = await api("/api/weather/test", {body: UI.sdraft.weather});
      $("#wxTest").textContent = `✓ jetzt ${Math.round(t.temp)}°, ${t.desc}`; }
    catch (err) { $("#wxTest").textContent = "⚠ " + err.message; }
  }}, el("div", {class: "grow"}, el("div", {class: "name", text: x.name}), el("div", {class: "meta", text: x.label})),
     el("span", {class: "btn small", text: "Wählen"}))));
});
function calColor(i, src) { return src.color ? hex(src.color) : ["#4c8dff", "#3ecf7e", "#f0a93b", "#eb5a96", "#a078ff", "#3cc8dc"][i % 6]; }
function renderCalSources() {
  const list = UI.sdraft.calendar.sources, box = $("#calSources");
  if (!list.length) { box.replaceChildren(el("div", {class: "empty", text: "Noch kein Kalender eingetragen."})); return; }
  box.replaceChildren(...list.map((src, i) => {
    const info = el("div", {class: "hint", style: {margin: "0 0 10px", gridColumn: "1 / -1"}});
    return el("div", {},
      el("div", {class: "srcrow"},
        el("input", {type: "text", value: src.name || "", placeholder: "Name", oninput: e => { src.name = e.target.value; touchSettings(); }}),
        el("input", {type: "url", value: src.url || "", placeholder: "https://…/basic.ics", oninput: e => { src.url = e.target.value.trim(); touchSettings(); }}),
        el("input", {type: "text", value: src.user || "", placeholder: "Benutzer (optional)", autocomplete: "off", oninput: e => { src.user = e.target.value.trim(); touchSettings(); }}),
        el("input", {type: "password", value: src.password || "", placeholder: "Passwort", autocomplete: "new-password", oninput: e => { src.password = e.target.value; touchSettings(); }}),
        el("input", {type: "color", value: calColor(i, src), title: "Farbe", oninput: e => { src.color = rgb(e.target.value); touchSettings(); }}),
        el("div", {class: "row", style: {flexWrap: "nowrap", gap: "4px"}},
          el("button", {class: "btn small", onclick: async () => {
            if (!src.url) { toast("Bitte zuerst die Adresse eintragen.", true); return; }
            info.textContent = "prüfe …";
            try { const r = await api("/api/calendar/test", {body: src});
              info.replaceChildren(`✓ ${r.count} Termine in den nächsten 30 Tagen`, ...(r.calendars && r.calendars.length ? [el("br"), `aus ${r.calendars.length} Kalendern: ${r.calendars.join(", ")}`] : []), ...r.next.map(t => [el("br"), "• " + t]).flat()); }
            catch (err) { info.textContent = "⚠ " + err.message; }
          }}, "Testen"),
          el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => {
            if (confirm(`Kalender „${src.name || src.url}“ entfernen?`)) { list.splice(i, 1); touchSettings(); renderCalSources(); } }}, "✕"))),
      info);
  }));
}
$("#calAdd").addEventListener("click", () => { UI.sdraft.calendar.sources.push({name: "", url: "", user: "", password: ""}); touchSettings(); renderCalSources(); });
$("#calDays").addEventListener("change", e => { UI.sdraft.calendar.days = parseInt(e.target.value); touchSettings(); });
$("#calRemind").addEventListener("change", e => { UI.sdraft.calendar.remind = parseInt(e.target.value); touchSettings(); });
$("#ntOn").addEventListener("change", e => { UI.sdraft.notifications.enabled = e.target.checked; touchSettings(); });
$("#ntSec").addEventListener("input", e => { UI.sdraft.notifications.seconds = Math.max(2, Math.min(30, parseInt(e.target.value) || 6)); touchSettings(); });
$("#ntIgnore").addEventListener("input", e => { UI.sdraft.notifications.ignore = e.target.value; touchSettings(); });
$("#ntTest").addEventListener("click", async () => {
  try { await api("/api/notify/test", {body: {}}); toast("Testbenachrichtigung gesendet – schau aufs Display."); }
  catch (e) { toast(e.message, true); }
});
async function refreshHardware() {
  try {
    const r = await api("/api/hardware"), s = r.sensors, t = v => v === null || v === undefined ? "nicht gefunden" : `${Math.round(v)} °C`;
    $("#hwInfo").replaceChildren(
      el("div", {text: "CPU"}), el("div", {text: t(s.cpu)}),
      el("div", {text: "Grafikkarte"}), el("div", {text: t(s.gpu) + (s.gpu_load !== null && s.gpu_load !== undefined ? ` · ${s.gpu_load} % Last` : "")}),
      el("div", {text: "SSD"}), el("div", {text: t(s.nvme)}),
      el("div", {text: "Lüfter"}), el("div", {text: s.fans.length ? s.fans.map(f => `${f[0]}: ${f[1]} U/min`).join(" · ") : "keine gefunden"}),
      el("div", {text: "Laufwerke"}), el("div", {text: r.disks.map(d => `${d[0]} ${d[1]} % von ${d[2]} GB`).join(" · ")}));
  } catch (e) { $("#hwInfo").replaceChildren(el("div", {class: "warnbox", text: e.message})); }
}
$("#hwRefresh").addEventListener("click", refreshHardware);
