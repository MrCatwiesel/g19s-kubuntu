// ---------------------------------------------------------------- Radiosender
function touchSettings() { UI.sDirty = true; markTabs(); renderSavebar(); }
function renderStations() {
  const t = $("#stations"), sd = UI.sdraft; if (!sd) return;
  t.replaceChildren(el("thead", {}, el("tr", {}, el("th", {}), el("th", {}, "Name"), el("th", {}, "Stream-Adresse"), el("th", {}, "Logo (optional)"), el("th", {}))));
  const tb = el("tbody");
  sd.stations.forEach((s, i) => {
    const playing = UI.testing && UI.testing.url === s.url;
    const img = el("img", {class: "logo", src: s.logo || "", alt: "", onerror: e => e.target.style.visibility = "hidden"});
    tb.append(el("tr", {class: playing ? "playing" : ""},
      el("td", {style: {width: "44px"}}, img),
      el("td", {style: {width: "22%"}}, el("input", {type: "text", value: s.name, placeholder: "Name",
        oninput: e => { s.name = e.target.value; touchSettings(); }})),
      el("td", {}, el("input", {type: "url", value: s.url, placeholder: "https://…",
        oninput: e => { s.url = e.target.value.trim(); touchSettings(); }})),
      el("td", {style: {width: "22%"}}, el("input", {type: "url", value: s.logo || "", placeholder: "https://…/logo.png",
        oninput: e => { s.logo = e.target.value.trim(); img.style.visibility = ""; img.src = s.logo; touchSettings(); }})),
      el("td", {style: {whiteSpace: "nowrap"}},
        el("button", {class: "btn icon small", title: playing ? "Probehören beenden" : "Probehören",
          onclick: () => playing ? stopTest() : testStation(s)}, playing ? "■" : "▶"),
        el("button", {class: "btn icon small", title: "nach oben", disabled: i === 0,
          onclick: () => { [sd.stations[i - 1], sd.stations[i]] = [sd.stations[i], sd.stations[i - 1]]; touchSettings(); renderStations(); }}, "↑"),
        el("button", {class: "btn icon small", title: "nach unten", disabled: i === sd.stations.length - 1,
          onclick: () => { [sd.stations[i + 1], sd.stations[i]] = [sd.stations[i], sd.stations[i + 1]]; touchSettings(); renderStations(); }}, "↓"),
        el("button", {class: "btn icon small danger", title: "löschen",
          onclick: () => { if (confirm(`Sender „${s.name || s.url}“ löschen?`)) { sd.stations.splice(i, 1); touchSettings(); renderStations(); } }}, "✕"))));
  });
  if (!sd.stations.length) tb.append(el("tr", {}, el("td", {colspan: 5, class: "empty", text: "Noch keine Sender – unten suchen oder hinzufügen."})));
  t.append(tb);
  $("#player").value = sd.radio_player || "";
  $("#stopTest").style.display = UI.testing ? "" : "none";
  $("#mpvHint").replaceChildren(
    S.tools.mpv ? el("p", {class: "hint", text: "✓ mpv ist installiert."}) :
      el("div", {class: "warnbox"}, "mpv ist nicht installiert. Installieren mit ", el("code", {text: "sudo apt install mpv"})),
    S.tools.mpris ? el("p", {class: "hint", text: "✓ Medientasten der Tastatur steuern das Radio (Play/Pause, Vor/Zurück = Sender wechseln, Stop)."}) :
      el("div", {class: "warnbox"}, "Damit die Medientasten der Tastatur das Radio steuern: ", el("code", {text: "sudo apt install mpv-mpris"})));
  renderAlarmClock();
}
// Radiowecker und gemerkte Songs
const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
function renderAlarmClock() {
  const sd = UI.sdraft; if (!sd) return;
  const a = sd.alarm_clock;                 // vollständig vom Server (Schema im Treiber)
  $("#acOn").checked = !!a.enabled; $("#acTime").value = a.time;
  const st = sd.stations.filter(x => x.url);
  $("#acStation").replaceChildren(...(st.length ? st.map(x => el("option", {value: x.url, text: x.name || domainOf(x.url), selected: x.url === a.station}))
    : [el("option", {value: "", text: "– erst Sender anlegen –"})]));
  if (st.length && !st.some(x => x.url === a.station)) a.station = st[0].url;
  $("#acDays").replaceChildren(...WEEKDAYS.map((n, i) => el("button", {class: a.days.includes(i) ? "active" : "", text: n,
    onclick: () => { a.days = a.days.includes(i) ? a.days.filter(x => x !== i) : [...a.days, i].sort(); touchSettings(); renderAlarmClock(); }})));
}
$("#acOn").addEventListener("change", e => { UI.sdraft.alarm_clock.enabled = e.target.checked; touchSettings(); });
$("#acTime").addEventListener("change", e => { UI.sdraft.alarm_clock.time = e.target.value || "07:00"; touchSettings(); });
$("#acStation").addEventListener("change", e => { UI.sdraft.alarm_clock.station = e.target.value; touchSettings(); });
async function loadSongs() {
  try { UI.songs = (await api("/api/songs")).songs; } catch (e) { UI.songs = []; }
  renderSongs();
}
function renderSongs() {
  const box = $("#songs"), songs = UI.songs || [];
  if (!songs.length) { box.replaceChildren(el("div", {class: "empty", text: "Noch keine Songs gemerkt."})); return; }
  box.replaceChildren(el("table", {class: "list"}, el("tbody", {}, ...songs.slice().reverse().map(sg => {
    const q = encodeURIComponent(`${sg.artist} ${sg.title}`.trim());
    return el("tr", {},
      el("td", {class: "muted", style: {whiteSpace: "nowrap", width: "1%"}, text: sg.time}),
      el("td", {}, el("b", {text: sg.title || "–"}), el("div", {class: "muted", text: [sg.artist, sg.source].filter(Boolean).join(" · ")})),
      el("td", {style: {whiteSpace: "nowrap", width: "1%"}},
        el("a", {class: "btn small", href: `https://www.youtube.com/results?search_query=${q}`, target: "_blank", rel: "noopener"}, "YouTube"),
        el("a", {class: "btn small", href: `https://open.spotify.com/search/${q}`, target: "_blank", rel: "noopener"}, "Spotify"),
        el("button", {class: "btn icon small danger", title: "entfernen", onclick: () => saveSongs(songs.filter(x => x !== sg))}, "✕")));
  }))));
}
async function saveSongs(list) {
  try { UI.songs = (await api("/api/songs", {body: {songs: list}})).songs; renderSongs(); } catch (e) { toast(e.message, true); }
}
$("#songsRefresh").addEventListener("click", loadSongs);
$("#songsClear").addEventListener("click", () => { if ((UI.songs || []).length && confirm("Alle gemerkten Songs löschen?")) saveSongs([]); });
$("#addStation").addEventListener("click", () => { UI.sdraft.stations.push({name: "", url: "", logo: ""}); touchSettings(); renderStations();
  const rows = $("#stations").querySelectorAll("tbody tr"); rows[rows.length - 1].querySelector("input").focus(); });
$("#player").addEventListener("input", e => { UI.sdraft.radio_player = e.target.value; touchSettings(); });
$("#stopTest").addEventListener("click", () => stopTest());
async function testStation(s) {
  if (!s.url) { toast("Bitte zuerst eine Stream-Adresse eingeben.", true); return; }
  try { await api("/api/radio/play", {body: {name: s.name, url: s.url, player: UI.sdraft.radio_player}});
    UI.testing = {url: s.url, name: s.name}; toast("Probehören: " + (s.name || s.url)); }
  catch (e) { toast(e.message, true); }
  renderStations(); renderResults();
}
async function stopTest() { try { await api("/api/radio/stop", {body: {}}); } catch (e) {} UI.testing = null; renderStations(); renderResults(); }
let lastResults = [];
$("#searchForm").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("#searchQ").value.trim(); if (!q) return;
  $("#results").replaceChildren(el("div", {class: "empty", text: "Suche …"}));
  try { lastResults = (await api("/api/radio/search?q=" + encodeURIComponent(q))).results; renderResults(); }
  catch (err) { $("#results").replaceChildren(el("div", {class: "warnbox", text: err.message})); }
});
function renderResults() {
  const box = $("#results"); if (!lastResults.length) { if (box.querySelector(".res")) box.replaceChildren(); return; }
  box.replaceChildren();
  for (const r of lastResults) {
    const have = UI.sdraft.stations.some(s => s.url === r.url);
    const playing = UI.testing && UI.testing.url === r.url;
    box.append(el("div", {class: "res"},
      el("img", {class: "logo", src: r.logo || "", alt: "", onerror: e => e.target.style.visibility = "hidden"}),
      el("div", {class: "grow"}, el("div", {class: "name", text: r.name || r.url}),
        el("div", {class: "meta", text: [r.country, r.codec && (r.codec + (r.bitrate ? " " + r.bitrate + " kbit/s" : "")), r.tags].filter(Boolean).join(" · ")})),
      el("button", {class: "btn icon small", title: playing ? "Probehören beenden" : "Probehören",
        onclick: () => playing ? stopTest() : testStation(r)}, playing ? "■" : "▶"),
      el("button", {class: "btn small" + (have ? "" : " primary"), disabled: have,
        onclick: () => { UI.sdraft.stations.push({name: r.name, url: r.url, logo: r.logo}); touchSettings(); renderStations(); renderResults();
          toast(`„${r.name}“ hinzugefügt – zum Übernehmen unten speichern.`); }}, have ? "✓ in der Liste" : "+ Hinzufügen")));
  }
}
