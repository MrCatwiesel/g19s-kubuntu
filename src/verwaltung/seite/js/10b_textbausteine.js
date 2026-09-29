// ---------------------------------------------------------------- Textbausteine
function renderSnippets() {
  const sd = UI.sdraft, box = $("#snippetList"); if (!sd) return;
  const groups = snippetGroups();
  box.replaceChildren(el("datalist", {id: "snipGroups"}, ...groups.map(g => el("option", {value: g}))));
  if (!sd.snippets.length) box.append(el("div", {class: "empty", text: "Noch keine Textbausteine."}));
  sd.snippets.forEach((sn, i) => {
    box.append(el("div", {class: "snip"},
      el("div", {class: "row", style: {flexWrap: "nowrap"}},
        el("input", {type: "text", value: sn.name || "", placeholder: "Name auf dem Display", style: {flex: "2"}, maxlength: 40,
          oninput: e => { sn.name = e.target.value; touchSettings(); }}),
        el("input", {type: "text", value: sn.group || "", placeholder: "Gruppe (optional)", list: "snipGroups", style: {flex: "1"}, maxlength: 30,
          oninput: e => { sn.group = e.target.value; touchSettings(); }}),
        el("button", {class: "btn icon small", title: "nach oben", disabled: i === 0,
          onclick: () => { [sd.snippets[i - 1], sd.snippets[i]] = [sd.snippets[i], sd.snippets[i - 1]]; touchSettings(); renderSnippets(); }}, "↑"),
        el("button", {class: "btn icon small", title: "nach unten", disabled: i === sd.snippets.length - 1,
          onclick: () => { [sd.snippets[i + 1], sd.snippets[i]] = [sd.snippets[i], sd.snippets[i + 1]]; touchSettings(); renderSnippets(); }}, "↓"),
        el("button", {class: "btn icon small danger", title: "löschen",
          onclick: () => { if (confirm(`Textbaustein „${sn.name || sn.text.slice(0, 30)}“ löschen?`)) { sd.snippets.splice(i, 1); touchSettings(); renderSnippets(); } }}, "✕")),
      el("textarea", {rows: 3, placeholder: "Text, der eingefügt wird (Umlaute, ß, @, € und Zeilenumbrüche sind möglich)",
        oninput: e => { sn.text = e.target.value; touchSettings(); }}, sn.text || "")));
  });
}
$("#addSnippet").addEventListener("click", () => {
  UI.sdraft.snippets.push({name: "", group: "", text: ""}); touchSettings(); renderSnippets();
  const ins = $("#snippetList").querySelectorAll(".snip input[type=text]"); ins[ins.length - 2].focus(); });
