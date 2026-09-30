// ---------------------------------------------------------------- Dienst & Sicherung
function renderServiceInfo() {
  const s = S.service || {}, active = s.active === "active";
  $("#svcPill").replaceChildren(el("span", {class: "dot " + (active ? "ok" : (s.active === "activating" ? "warn" : "bad"))}),
    el("span", {text: active ? "Treiber läuft" : s.active === "activating" ? "Treiber startet …" : "Treiber gestoppt"}));
  $("#svcActive").replaceChildren(el("span", {class: "dot " + (active ? "ok" : "bad")}), " ",
    {active: "läuft", inactive: "gestoppt", failed: "abgestürzt", activating: "startet"}[s.active] || s.active || "?");
  const en = s.enabled === "enabled";
  $("#svcEnabled").textContent = en ? "an (startet bei der Anmeldung)" : "aus";
  $("#toggleAutostart").textContent = en ? "Autostart ausschalten" : "Autostart einschalten";
  $("#toolMpv").innerHTML = ""; $("#toolMpv").append(S.tools.mpv ? "installiert" : el("span", {}, "fehlt – ", el("code", {text: "sudo apt install mpv"})));
  $("#toolPlayerctl").innerHTML = ""; $("#toolPlayerctl").append(S.tools.playerctl ? "installiert" : el("span", {}, "fehlt – ", el("code", {text: "sudo apt install playerctl"})));
  $("#toolMpris").innerHTML = ""; $("#toolMpris").append(S.tools.mpris ? "aktiv (mpv-mpris installiert)" : el("span", {}, "aus – ", el("code", {text: "sudo apt install mpv-mpris"})));
}
async function refreshService() {
  try { const r = await api("/api/service"); S.service = r.status; renderServiceInfo(); $("#log").textContent = r.log || "(kein Protokoll)";
    const lg = $("#log"); lg.scrollTop = lg.scrollHeight; } catch (e) {}
  try { const v = await api("/api/versions");
    $("#versions").replaceChildren(
      el("div", {text: "Treiber"}), el("div", {}, v.driver, v.driver !== v.driver_running
        ? el("span", {class: "muted", text: " (Verwaltung kennt noch " + v.driver_running + " – wird beim nächsten Start übernommen)"}) : ""),
      el("div", {text: "Verwaltung"}), el("div", {text: v.gui}),
      el("div", {text: "Alte Versionen"}), el("div", {}, el("code", {text: v.backups})));
  } catch (e) {}
  try { const b = await api("/api/backupinfo");
    $("#backupFiles").replaceChildren("Enthält: ", ...b.files.map((f, i) => [i ? ", " : "", el("code", {text: "~/" + f})]).flat()); } catch (e) {}
}
document.querySelectorAll("[data-svc]").forEach(b => b.addEventListener("click", () => svc(b.dataset.svc)));
$("#toggleAutostart").addEventListener("click", () => svc(S.service.enabled === "enabled" ? "disable" : "enable"));
$("#logRefresh").addEventListener("click", refreshService);
async function svc(action) {
  try { const r = await api("/api/service", {body: {action}}); S.service = r.status; renderServiceInfo();
    $("#log").textContent = r.log || ""; const lg = $("#log"); lg.scrollTop = lg.scrollHeight;
    toast({start: "Treiber gestartet", stop: "Treiber gestoppt", restart: "Treiber neu gestartet",
      enable: "Autostart eingeschaltet", disable: "Autostart ausgeschaltet"}[action]); }
  catch (e) { toast(e.message, true); }
}
$("#restoreFile").addEventListener("change", async e => {
  const f = e.target.files[0]; e.target.value = ""; if (!f) return;
  if (!confirm(`Sicherung „${f.name}“ einspielen? Die aktuellen Dateien werden vorher automatisch gesichert.`)) return;
  try {
    const body = await f.arrayBuffer();
    const info = await api("/api/restore?inspect=1", {body, raw: true});
    let programs = false;
    if (info.programs.length)
      programs = confirm("Die Sicherung enthält auch Programmdateien und KDE-Kurzbefehle:\n\n" +
        info.programs.map(p => "~/" + p).join("\n") +
        "\n\nDiese nur einspielen, wenn die Sicherung sicher von dir stammt (z. B. nach einer Neuinstallation)." +
        "\n\nOK = mit einspielen · Abbrechen = nur Einstellungen und Makros");
    const r = await api("/api/restore?programs=" + (programs ? "1" : "0"), {body, raw: true});
    toast(`Wiederhergestellt: ${r.restored.length} Dateien. Treiber neu starten, damit alles greift.`);
    await loadState(); refreshService();
  } catch (err) { toast(err.message, true); }
});
function toBase64(buf) {
  const bytes = new Uint8Array(buf); let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
$("#updateFile").addEventListener("change", async e => {
  const files = [...e.target.files]; e.target.value = ""; if (!files.length) return;
  if (UI.draftDirty || UI.sDirty) { toast("Bitte zuerst die offenen Änderungen speichern oder verwerfen.", true); return; }
  if (!confirm(`${files.map(f => f.name).join(" und ")} einspielen? Treiber bzw. Verwaltung werden dabei neu gestartet.`)) return;
  const box = $("#updateResult"); box.replaceChildren(el("span", {class: "muted", text: "Spiele Update ein …"}));
  let r;
  try {
    const payload = [];
    for (const f of files) payload.push({name: f.name, data: toBase64(await f.arrayBuffer())});
    r = await api("/api/update", {body: {files: payload}});
  } catch (err) { box.replaceChildren(el("div", {class: "warnbox", text: err.message})); return; }
  box.replaceChildren(...r.installed.map(x => el("div", {class: "hint", style: {margin: "2px 0"}},
    "✓ ", el("b", {text: x.component === "driver" ? "Treiber" : "Verwaltung"}), ` aktualisiert: ${x.old} → ${x.new}`,
    x.warning ? el("span", {style: {color: "var(--danger)"}, text: " – " + x.warning}) : "")));
  if (!r.restart_gui) { toast("Update eingespielt, der Treiber wurde neu gestartet."); refreshService(); return; }
  $("#ovTitle").textContent = "Verwaltung wird neu gestartet …";
  $("#ovText").textContent = "Einen Moment bitte, die Seite lädt gleich von selbst neu.";
  $("#overlay").classList.add("show");
  const until = Date.now() + 30000;
  await new Promise(res => setTimeout(res, 1500));
  while (Date.now() < until) {
    try { const p = await fetch("/api/poll", {headers: {"X-Token": TOKEN}}); if (p.ok) { location.reload(); return; } } catch (err) {}
    await new Promise(res => setTimeout(res, 700));
  }
  $("#ovTitle").textContent = "Neustart dauert ungewöhnlich lange";
  $("#ovText").textContent = "Bitte die Verwaltung über das Anwendungsmenü neu öffnen.";
});
function renderPaths() {

  const p = S.paths || {};
  $("#paths").replaceChildren(
    el("div", {text: "Tastenbelegung"}), el("div", {}, el("code", {text: p.macros || ""})),
    el("div", {text: "Einstellungen"}), el("div", {}, el("code", {text: p.settings || ""})),
    el("div", {text: "Treiber"}), el("div", {}, el("code", {text: p.driver || ""})));
}
// Automatische Sicherung
const AB_HINTS = {
  folder: "Ein Ordner auf diesem Rechner. Ein NAS muss dafür eingebunden sein (z. B. per /etc/fstab unter /mnt/nas); ein Nextcloud-Ordner, den der Nextcloud-Client synchronisiert, funktioniert direkt (z. B. ~/Nextcloud/Sicherungen). Hinweis: Freigaben, die nur in Dolphin geöffnet sind (smb://…), sind kein Ordner – dafür „NAS – Windows-Freigabe“ wählen.",
  nextcloud: "Adresse deiner Nextcloud (z. B. https://cloud.example.de – auch die Adresse aus dem Browser geht), dein Benutzername und am besten ein App-Passwort: Nextcloud → Persönliche Einstellungen → Sicherheit → „Neues App-Passwort erstellen“. Der Ordner wird bei Bedarf angelegt.",
  smb: "Freigabe und Ordner wie im Dateimanager, z. B. \\\\nas\\backup\\G19s oder smb://nas/backup/G19s – der Ordner muss vorhanden sein. Benötigt das Programm smbclient (sudo apt install smbclient). Ohne smbclient wird KDEs kioclient benutzt – dann die Freigabe einmal in Dolphin öffnen und das Passwort speichern (das Passwort hier wird aus Sicherheitsgründen nicht an kioclient übergeben).",
  webdav: "Vollständige Adresse des Ordners, z. B. https://nas.local:5006/home/Sicherungen (Synology: Paket „WebDAV Server“, QNAP: WebDAV in den Freigabe-Einstellungen). Der Ordner muss vorhanden sein.",
};
const AB_URL = {nextcloud: ["Adresse der Nextcloud", "https://cloud.example.de"], smb: ["Freigabe und Ordner", "\\\\nas\\backup\\G19s"],
  webdav: ["Adresse des Ordners", "https://nas.local:5006/home/Sicherungen"]};
function renderAutoBackup() {
  const sd = UI.sdraft; if (!sd) return;
  const b = sd.backup, t = b.target || "folder";
  $("#abOn").checked = !!b.enabled; $("#abTarget").value = t;
  $("#abFolder").value = b.folder; $("#abDays").value = String(b.days); $("#abKeep").value = b.keep;
  $("#abFolderBox").style.display = t === "folder" ? "" : "none";
  $("#abRemoteBox").style.display = t === "folder" ? "none" : "";
  $("#abDirBox").style.display = t === "nextcloud" ? "" : "none";
  if (t !== "folder") {
    $("#abUrlLabel").textContent = AB_URL[t][0]; $("#abUrl").placeholder = AB_URL[t][1];
    $("#abPwLabel").textContent = t === "nextcloud" ? "App-Passwort" : "Passwort";
    $("#abUrl").value = b.url || ""; $("#abUser").value = b.user || ""; $("#abPw").value = b.password || "";
    $("#abDir").value = b.remote_dir || "";
  }
  $("#abHint").textContent = AB_HINTS[t];
}
async function loadBackupStatus() {
  try {
    const r = await api("/api/backup/status");
    $("#abStatus").replaceChildren(r.error ? el("div", {class: "warnbox", text: "Letzter Versuch fehlgeschlagen: " + r.error}) :
      r.last ? el("span", {text: `Letzte Sicherung: ${new Date(r.last * 1000).toLocaleString("de-DE")} – ${r.file}`}) : el("span", {text: "Noch keine automatische Sicherung."}));
  } catch (e) { /* nicht kritisch */ }
}
$("#abOn").addEventListener("change", e => { UI.sdraft.backup.enabled = e.target.checked; touchSettings(); });
$("#abFolder").addEventListener("input", e => { UI.sdraft.backup.folder = e.target.value.trim(); touchSettings(); });
$("#abTarget").addEventListener("change", e => { UI.sdraft.backup.target = e.target.value; touchSettings(); renderAutoBackup(); });
for (const [id, key] of [["#abUrl", "url"], ["#abUser", "user"], ["#abPw", "password"], ["#abDir", "remote_dir"]])
  $(id).addEventListener("input", e => { UI.sdraft.backup[key] = key === "password" ? e.target.value : e.target.value.trim(); touchSettings(); });
$("#abDays").addEventListener("change", e => { UI.sdraft.backup.days = parseInt(e.target.value); touchSettings(); });
$("#abKeep").addEventListener("input", e => { UI.sdraft.backup.keep = Math.max(1, Math.min(100, parseInt(e.target.value) || 8)); touchSettings(); });
$("#abBrowse").addEventListener("click", () => browseFolder(UI.sdraft.backup.folder || "~", {box: "#abBrowser", images: false,
  pick: path => { UI.sdraft.backup.folder = path; touchSettings(); renderAutoBackup(); toast("Ordner übernommen – zum Übernehmen unten speichern."); }}));
function abReady() {
  const b = UI.sdraft.backup;
  if ((b.target || "folder") === "folder" ? !b.folder : !b.url) { toast(b.target === "folder" || !b.target ? "Bitte zuerst einen Ordner wählen." : "Bitte zuerst die Adresse angeben.", true); return null; }
  return b;
}
$("#abNow").addEventListener("click", async () => {
  const b = abReady(); if (!b) return;
  $("#abNow").disabled = true;
  try { const r = await api("/api/backup/now", {body: {backup: b}}); toast("Gesichert: " + r.path); }
  catch (e) { toast(e.message, true); }
  finally { $("#abNow").disabled = false; loadBackupStatus(); }
});
$("#abTest").addEventListener("click", async () => {
  const b = abReady(); if (!b) return;
  $("#abTest").disabled = true; $("#abStatus").textContent = "Teste …";
  try { const r = await api("/api/backup/test", {body: {backup: b}});
    $("#abStatus").replaceChildren(el("div", {class: "okbox", text: "✓ " + r.message})); }
  catch (e) { $("#abStatus").replaceChildren(el("div", {class: "warnbox", text: "✗ " + e.message})); }
  finally { $("#abTest").disabled = false; }
});

// Sicherung herunterladen: per fetch mit Schlüssel in der Kopfzeile (nicht in der Adresse)
$("#backupLink").addEventListener("click", async e => {
  e.preventDefault();
  try {
    const r = await fetch("/api/backup", {headers: {"X-Token": TOKEN}});
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `Fehler ${r.status}`);
    const name = (/filename="([^"]+)"/.exec(r.headers.get("Content-Disposition") || "") || [])[1] || "g19s-sicherung.tar.gz";
    const url = URL.createObjectURL(await r.blob());
    const a = el("a", {href: url, download: name}); document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  } catch (err) { toast(err.message, true); }
});
