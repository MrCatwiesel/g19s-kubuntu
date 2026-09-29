// ---------------------------------------------------------------- Profile verwalten
function afterProfileChange() { selectKey(UI.gkey, true); renderProfiles(); renderKeypad(); renderEditor(); }
async function setActive(i, quiet) {
  const r = await api("/api/active", {body: {index: i}});
  S.active = r.active;
  if (!quiet) toast(`„${P(i).name}“ ist jetzt an der Tastatur aktiv.`);
  renderProfileCard();
}
async function activateProfile() { try { await setActive(UI.pidx); } catch (e) { toast(e.message, true); } }
async function saveProfiles(m, msg, newPidx, newActive) {
  try {
    await saveMacros(m, msg);
    UI.pidx = Math.max(0, Math.min(newPidx, S.macros.profiles.length - 1));
    if (newActive !== S.active) await setActive(Math.max(0, Math.min(newActive, S.macros.profiles.length - 1)), true);
    afterProfileChange();
  } catch (e) { toast(e.message, true); }
}
function askName(title, value) {
  const name = prompt(title, value);
  if (name === null) return null;
  const t = name.trim().slice(0, 30);
  if (!t) { toast("Der Name darf nicht leer sein.", true); return null; }
  return t;
}
$("#profSel").addEventListener("change", e => {
  if (!confirmLeave()) { e.target.value = UI.pidx; return; }
  UI.pidx = parseInt(e.target.value); afterProfileChange();
});
$("#profNew").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const name = askName("Name des neuen Profils:", `Profil ${S.macros.profiles.length + 1}`); if (!name) return;
  const m = clone(S.macros);
  m.profiles.push({name, colors: clone((UI.sdraft || S.settings).colors), keys: {}});
  saveProfiles(m, `Profil „${name}“ angelegt.`, m.profiles.length - 1, S.active);
});
$("#profCopy").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const name = askName("Name der Kopie:", `${P().name} (Kopie)`.slice(0, 30)); if (!name) return;
  const m = clone(S.macros), copy = clone(P());
  copy.name = name; copy.colors = clone(profColors());
  m.profiles.splice(UI.pidx + 1, 0, copy);
  saveProfiles(m, `Profil „${name}“ angelegt (Kopie von „${P().name}“).`, UI.pidx + 1, S.active > UI.pidx ? S.active + 1 : S.active);
});
$("#profRename").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const name = askName("Neuer Name des Profils:", P().name); if (!name) return;
  const m = clone(S.macros); m.profiles[UI.pidx].name = name;
  saveProfiles(m, `Profil umbenannt in „${name}“.`, UI.pidx, S.active);
});
$("#profDel").addEventListener("click", () => {
  if (!confirmLeave()) return;
  const cnt = Object.values(P().keys || {}).reduce((a, l) => a + Object.keys(l).length, 0);
  if (!confirm(`Profil „${P().name}“ mit ${cnt} Belegungen löschen?`)) return;
  const m = clone(S.macros), i = UI.pidx; m.profiles.splice(i, 1);
  const act = S.active === i ? 0 : (S.active > i ? S.active - 1 : S.active);
  saveProfiles(m, `Profil „${P().name}“ gelöscht.`, Math.max(0, i - 1), act);
});
function moveProfile(dir) {
  if (!confirmLeave()) return;
  const i = UI.pidx, j = i + dir, m = clone(S.macros);
  if (j < 0 || j >= m.profiles.length) return;
  [m.profiles[i], m.profiles[j]] = [m.profiles[j], m.profiles[i]];
  const act = S.active === i ? j : (S.active === j ? i : S.active);
  saveProfiles(m, "Reihenfolge geändert.", j, act);
}
$("#profUp").addEventListener("click", () => moveProfile(-1));
$("#profDown").addEventListener("click", () => moveProfile(1));
function setProfileColor(layer, value) {
  if (!confirmLeave()) { renderProfileCard(); return; }
  const m = clone(S.macros), p = m.profiles[UI.pidx];
  p.colors = clone(profColors()); p.colors[layer] = rgb(value);
  saveProfiles(m, `Farbe für ${layer} gespeichert.`, UI.pidx, S.active);
}
