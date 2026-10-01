// ---------------------------------------------------------------- Tasten: Editor
function renderEditor() {
  const d = UI.draft, box = $("#editor"); box.replaceChildren();
  if (!d) return;
  box.append(el("div", {class: "edhead"},
    el("h2", {text: `${UI.gkey} · ${P().name} · ${UI.profile}`}),
    el("span", {class: "swatch", style: {background: profileColor(UI.profile)}})));
  const types = el("div", {class: "types"});
  for (const t of TYPES) types.append(el("button", {class: d.type === t.id ? "active" : "",
    onclick: () => { stopRecording(false); d.type = t.id; touchDraft(); renderEditor(); }},
    el("span", {class: "ti", text: t.icon}), t.label));
  box.append(types);
  box.append(el("label", {class: "field"}, el("span", {text: "Name auf dem Display (optional)"}),
    el("input", {type: "text", value: d.name, maxlength: 40, placeholder: autoName(d) || "z. B. Firefox",
      oninput: e => { d.name = e.target.value; touchDraft(); }})));
  const body = el("div");
  ({default: edDefault, text: edText, combo: edCombo, steps: edSteps, open: edOpen, run: edRun,
    radio: edRadio, media: edMedia, volume: edVolume, snippets: edSnippets, timer: edTimer, sleep: edSleep, mic: edMic})[d.type](body, d);
  box.append(body);
  const exists = !!layerKeys()[UI.gkey];
  box.append(el("div", {class: "actions"},
    el("button", {class: "btn primary", id: "applyBtn", onclick: applyDraft}, "Übernehmen"),
    el("button", {class: "btn", id: "revertBtn", onclick: () => { selectKey(UI.gkey, true); renderEditor(); }}, "Verwerfen"),
    el("div", {class: "spacer"}),
    exists ? el("button", {class: "btn danger", onclick: clearKey}, "Belegung entfernen") : null));
  updateApplyState();
}
function updateApplyState() {
  const a = $("#applyBtn"), r = $("#revertBtn");
  if (a) a.disabled = !UI.draftDirty; if (r) r.disabled = !UI.draftDirty;
}
function autoName(d) { const e = draftToEntry(Object.assign({}, d, {name: ""})); return e ? entryLabel(e) : ""; }

function edDefault(box) {
  box.append(el("div", {class: "note"}, "Diese Taste sendet ", el("b", {text: fKeyText(UI.gkey, UI.profile)}),
    ". Belege sie in den ", el("b", {text: "KDE-Systemeinstellungen → Tastatur → Kurzbefehle"}),
    " oder direkt in einem Programm (Spiele, OBS …). Ein Name hier erscheint nur als Beschriftung auf dem Display."));
}
function edText(box, d) {
  const warn = el("div");
  const check = () => {
    const bad = d.paste ? [] : [...new Set([...d.text].filter(c => !S.chars.has(c) && c !== "\r"))];
    warn.replaceChildren(bad.length ? el("div", {class: "warnbox"}, "Diese Zeichen können nicht getippt werden und werden übersprungen: ",
      el("b", {text: bad.join(" ")})) : "");
  };
  const hint = el("p", {class: "hint"});
  const explain = () => hint.textContent = d.paste
    ? "Der Text kommt in die Zwischenablage und wird mit einem Tastendruck eingefügt – schnell, mit allen Zeichen (auch Emojis) und Zeilenumbrüchen. Der Text bleibt danach in der Zwischenablage – mit Strg+V lässt er sich beliebig oft selbst einfügen."
    : "Der Text wird Zeichen für Zeichen getippt (Zeilenumbruch = Enter). Umlaute, ß, @, € und Sonderzeichen werden für das deutsche Tastaturlayout umgesetzt.";
  box.append(el("label", {class: "field"}, el("span", {text: "Text"}),
    el("textarea", {value: d.text, placeholder: "z. B. Mit freundlichen Grüßen\nMax Mustermann",
      oninput: e => { d.text = e.target.value; touchDraft(); check(); }})),
    el("label", {class: "field"}, el("span", {text: "Einfügen"}),
      pasteSelect(d.paste, v => { d.paste = v; touchDraft(); check(); explain(); })), warn, hint);
  check(); explain();
}
function edCombo(box, d) {
  const chips = el("div", {class: "chips"});
  const draw = () => {
    chips.replaceChildren();
    d.combo.forEach((k, i) => {
      if (i) chips.append(el("span", {class: "plus", text: "+"}));
      chips.append(el("span", {class: "chip"}, keyLabel(k),
        el("button", {title: "entfernen", onclick: () => { d.combo.splice(i, 1); touchDraft(); draw(); }}, "×")));
    });
    if (!d.combo.length) chips.append(el("span", {class: "muted", text: "noch keine Taste"}));
  };
  draw();
  const cap = el("div", {class: "capture", id: "capture"}, "Klicke auf „Kombination aufnehmen“ und drücke die Tasten gleichzeitig, z. B. Strg+Umschalt+T.");
  const recBtn = el("button", {class: "btn", onclick: () => {
    if (UI.recording) { stopRecording(true); return; }
    startRecording("combo", cap, recBtn, keys => { d.combo = keys; touchDraft(); draw(); });
  }}, "⏺ Kombination aufnehmen");
  box.append(el("label", {class: "field"}, el("span", {text: "Tastenkombination"}), chips),
    el("div", {class: "row"}, recBtn, keySelect("", k => { if (k && !d.combo.includes(k)) { d.combo.push(k); touchDraft(); draw(); } }, "+ Taste hinzufügen …")),
    cap);
}
function edSteps(box, d) {
  const tbody = el("tbody");
  const count = el("span", {class: "muted"});
  const draw = () => {
    tbody.replaceChildren();
    d.steps.forEach((s, i) => {
      tbody.append(el("tr", {},
        el("td", {class: "n", text: i + 1}),
        el("td", {}, el("input", {type: "number", min: 0, max: 5000, step: 10, value: s[0],
          oninput: e => { s[0] = Math.max(0, Math.min(5000, parseInt(e.target.value) || 0)); touchDraft(); }})),
        el("td", {}, keySelect(s[1], k => { s[1] = k; touchDraft(); })),
        el("td", {}, actionSelect(s[2], a => { s[2] = a; touchDraft(); })),
        el("td", {style: {whiteSpace: "nowrap"}},
          el("button", {class: "btn icon small", title: "nach oben", disabled: i === 0,
            onclick: () => { [d.steps[i - 1], d.steps[i]] = [d.steps[i], d.steps[i - 1]]; touchDraft(); draw(); }}, "↑"),
          el("button", {class: "btn icon small", title: "nach unten", disabled: i === d.steps.length - 1,
            onclick: () => { [d.steps[i + 1], d.steps[i]] = [d.steps[i], d.steps[i + 1]]; touchDraft(); draw(); }}, "↓"),
          el("button", {class: "btn icon small danger", title: "löschen",
            onclick: () => { d.steps.splice(i, 1); touchDraft(); draw(); }}, "✕"))));
    });
    if (!d.steps.length) tbody.append(el("tr", {}, el("td", {colspan: 5, class: "empty", text: "Noch keine Schritte – aufnehmen oder hinzufügen."})));
    const downs = d.steps.filter(s => s[2] !== "up").length;
    const total = d.steps.reduce((a, s) => a + (s[0] || 0), 0);
    count.textContent = `${d.steps.length} Schritte · ${downs} Tastendrücke · Dauer ca. ${(total / 1000).toFixed(1)} s`;
  };
  const cap = el("div", {class: "capture", id: "capture"}, "„Aufnehmen“ klicken, Tasten drücken, dann „Aufnahme beenden“ klicken. Pausen werden mit aufgezeichnet.");
  const recBtn = el("button", {class: "btn", onclick: () => {
    if (UI.recording) { stopRecording(true); return; }
    startRecording("steps", cap, recBtn, steps => { d.steps = d.steps.concat(steps); touchDraft(); draw(); });
  }}, "⏺ Aufnehmen");
  const pause = el("input", {type: "number", value: 30, min: 0, max: 5000, step: 10, title: "Pause in ms"});
  box.append(
    el("div", {class: "tools"}, recBtn,
      el("button", {class: "btn", onclick: () => { d.steps.push([50, "KEY_A", "tap"]); touchDraft(); draw(); }}, "+ Schritt"),
      el("span", {class: "muted", style: {marginLeft: "8px"}, text: "Alle Pausen auf"}), pause,
      el("span", {class: "muted", text: "ms"}),
      el("button", {class: "btn small", onclick: () => { const v = Math.max(0, parseInt(pause.value) || 0);
        d.steps.forEach((s, i) => s[0] = i === 0 ? 0 : v); touchDraft(); draw(); }}, "angleichen"),
      el("button", {class: "btn small", title: "Drücken+Loslassen derselben Taste zu einem Tipp zusammenfassen",
        onclick: () => { d.steps = compactSteps(d.steps); touchDraft(); draw(); }}, "vereinfachen"),
      el("button", {class: "btn small danger", onclick: () => { if (confirm("Alle Schritte löschen?")) { d.steps = []; touchDraft(); draw(); } }}, "alle löschen")),
    cap,
    el("div", {class: "stepsbox"}, el("table", {class: "steps"},
      el("thead", {}, el("tr", {}, el("th", {}, "#"), el("th", {}, "Pause (ms)"), el("th", {}, "Taste"), el("th", {}, "Aktion"), el("th", {}))),
      tbody)),
    el("p", {class: "hint", style: {marginTop: "8px"}}, count,
      el("br"), "„Tippen“ = kurz drücken. Für gehaltene Tasten (z. B. Umschalt) „drücken“ und später „loslassen“ verwenden."));
  draw();
}
function compactSteps(steps) {
  const out = [];
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i], n = steps[i + 1];
    if (s[2] === "down" && n && n[2] === "up" && n[1] === s[1]) { out.push([s[0], s[1], "tap"]); i++; }
    else out.push(s.slice());
  }
  return out;
}
function edOpen(box, d) {
  const inp = el("input", {type: "url", value: d.open, placeholder: "https://www.example.de",
    oninput: e => { d.open = e.target.value.trim(); touchDraft(); }});
  box.append(el("label", {class: "field"}, el("span", {text: "Adresse der Webseite"}), inp),
    el("div", {class: "row"}, el("button", {class: "btn", onclick: () => {
      let u = inp.value.trim(); if (!u) return;
      if (!/^[a-z]+:\/\//i.test(u)) { u = "https://" + u; inp.value = u; d.open = u; touchDraft(); }
      window.open(u, "_blank", "noopener");
    }}, "Testen")),
    el("p", {class: "hint", style: {marginTop: "10px"}, text: "Öffnet sich im Standardbrowser."}));
}
function edRun(box, d) {
  const inp = el("input", {type: "text", value: d.run, placeholder: "z. B. konsole",
    oninput: e => { d.run = e.target.value; touchDraft(); }});
  const ex = [["Terminal", "konsole"], ["Dateimanager", "dolphin"], ["Bildschirmfoto", "spectacle"],
    ["Rechner", "kcalc"], ["Stumm schalten", "pactl set-sink-mute @DEFAULT_SINK@ toggle"],
    ["Bildschirm sperren", "loginctl lock-session"], ["Firefox privat", "firefox --private-window"]];
  box.append(el("label", {class: "field"}, el("span", {text: "Befehl"}), inp),
    el("div", {class: "hint", text: "Beispiele (anklicken zum Übernehmen):"}),
    el("div", {class: "row"}, ex.map(([n, c]) => el("button", {class: "btn small", title: c,
      onclick: () => { inp.value = c; d.run = c; if (!d.name) d.name = n; touchDraft(); renderEditor(); }}, n))));
}
function edRadio(box, d) {
  const st = (UI.sdraft || S.settings).stations || [];
  if (!st.length) {
    box.append(el("div", {class: "note"}, "Noch keine Radiosender angelegt. Lege sie im Reiter ", el("b", {text: "Radiosender"}), " an."));
  }
  const sel = el("select", {onchange: e => { d.radio = e.target.value; touchDraft(); }},
    el("option", {value: "", text: "– Sender wählen –"}),
    st.map(s => el("option", {value: s.url, text: s.name || s.url, selected: s.url === d.radio})),
    el("option", {value: "stop", text: "■ Radio ausschalten", selected: d.radio === "stop"}));
  if (d.radio && d.radio !== "stop" && !st.some(s => s.url === d.radio))
    sel.append(el("option", {value: d.radio, text: domainOf(d.radio) + " (nicht in der Liste)", selected: true}));
  box.append(el("label", {class: "field"}, el("span", {text: "Radiosender"}), sel),
    el("p", {class: "hint", text: "Drücken startet den Sender, nochmal drücken schaltet ihn aus. Der aktuelle Song erscheint auf der Musikseite des Displays."}));
  if (!S.tools.mpv) box.append(el("div", {class: "warnbox"}, "Für Radiosender wird ", el("b", {text: "mpv"}), " benötigt: ", el("code", {text: "sudo apt install mpv"})));
}
function edMedia(box, d) {
  box.append(el("label", {class: "field"}, el("span", {text: "Aktion"}),
    el("select", {onchange: e => { d.media = e.target.value; touchDraft(); }},
      Object.entries(S.media).map(([k, v]) => el("option", {value: k, text: v, selected: d.media === k})))),
    el("p", {class: "hint", text: "Steuert den gerade laufenden Player (Elisa, Spotify, VLC, Browser …) bzw. das eigene Radio."}));
}
function edVolume(box, d) {
  box.append(el("label", {class: "field"}, el("span", {text: "Aktion"}),
    el("select", {onchange: e => { d.volume = e.target.value; touchDraft(); }},
      Object.entries(S.volume).map(([k, v]) => el("option", {value: k, text: v, selected: d.volume === k})))),
    el("p", {class: "hint", text: `Ändert die Systemlautstärke um ${(UI.sdraft || S.settings).volume_step || 5} % und zeigt sie kurz groß auf dem Display. Die Schrittweite stellst du unter „Beleuchtung & Display“ ein.`}));
}
function edSnippets(box, d) {
  const groups = snippetGroups(), names = snippetNames(), n = ((UI.sdraft || S.settings).snippets || []).length;
  const missing = d.snippet && !names.includes(d.snippet);
  const value = d.snippet ? "s:" + d.snippet : d.snippets === "*" ? "*" : "g:" + d.snippets;
  const extra = el("div");
  const explain = () => extra.replaceChildren(d.snippet
    ? el("p", {class: "hint", text: "Jeder Druck auf die G-Taste fügt diesen Textbaustein sofort ins aktive Fenster ein – ohne Liste. Wie eingefügt wird (Zwischenablage oder tippen), stellst du beim Baustein im Reiter „Textbausteine“ ein."})
    : el("div", {},
      el("label", {class: "check"}, el("input", {type: "checkbox", id: "snipKeepOpen", checked: d.keepOpen,
        onchange: e => { d.keepOpen = e.target.checked; touchDraft(); }}), " Liste nach dem Einfügen offen lassen"),
      el("p", {class: "hint", text: "Ein Druck auf die G-Taste zeigt die Liste auf dem Display: Hoch/Runter wählen, OK fügt den Text ins aktive Fenster ein. Bleibt die Liste offen, kannst du mehrmals OK drücken oder gleich den nächsten Baustein wählen. BACK oder die G-Taste schließen die Liste. Die Texte legst du im Reiter „Textbausteine“ an."})));
  box.append(el("label", {class: "field"}, el("span", {text: "Welche Textbausteine?"}),
    el("select", {id: "snipSel", onchange: e => {
      const v = e.target.value;
      d.snippet = v.startsWith("s:") ? v.slice(2) : ""; d.snippets = v.startsWith("g:") ? v.slice(2) : "*";
      touchDraft(); explain(); }},
      el("option", {value: "*", text: `Liste: alle (${n})`, selected: value === "*"}),
      ...groups.map(g => el("option", {value: "g:" + g, text: "Liste: Gruppe " + g, selected: value === "g:" + g})),
      ...[...names, ...(missing ? [d.snippet] : [])].map(nm => el("option", {value: "s:" + nm,
        text: "Direkt einfügen: " + nm + (missing && nm === d.snippet ? " (fehlt)" : ""), selected: value === "s:" + nm})))),
    extra);
  explain();
  if (!n) box.append(el("div", {class: "warnbox"}, "Es gibt noch keine Textbausteine – im Reiter „Textbausteine“ anlegen."));
  else if (missing) box.append(el("div", {class: "warnbox"}, `Den Textbaustein „${d.snippet}“ gibt es nicht mehr – bitte einen anderen wählen.`));
}
function edSleep(box, d) {
  box.append(el("label", {class: "field", style: {maxWidth: "220px"}}, el("span", {text: "Musik ausschalten nach … Minuten"}),
    el("input", {type: "number", min: 1, max: 240, value: d.sleep, oninput: e => {
      d.sleep = Math.max(1, Math.min(240, parseInt(e.target.value) || 30)); touchDraft(); }})),
    el("p", {class: "hint", text: "Startet den Einschlaftimer (läuft nichts, startet der zuletzt gehörte bzw. erste Radiosender). Nach Ablauf wird das Radio bzw. der Player ausgeschaltet. Die restlichen Minuten stehen mit Mondsymbol in der Fußzeile. Nochmal drücken = abbrechen."}));
}
function edMic(box, d) {
  box.append(el("p", {class: "hint", text: "Schaltet das Mikrofon (Standard-Eingang) stumm bzw. wieder an – praktisch für Videokonferenzen. Solange es stumm ist, leuchtet die MR-Taste und die Fußzeile zeigt ein rotes Mikrofon. Das funktioniert auch, wenn das Mikrofon in KDE oder in einem Programm stummgeschaltet wurde."}));
}
function edTimer(box, d) {
  const t = d.timer;
  const num = (key, label, min, max) => el("label", {class: "field", style: {maxWidth: "200px"}}, el("span", {text: label}),
    el("input", {type: "number", min, max, value: t[key], oninput: e => {
      t[key] = Math.max(min, Math.min(max, parseInt(e.target.value) || min)); touchDraft(); }}));
  box.append(el("div", {class: "seg", style: {marginBottom: "12px"}},
    ...[["timer", "Countdown"], ["stopwatch", "Stoppuhr"], ["pomodoro", "Pomodoro"]].map(([m, l]) =>
      el("button", {class: t.mode === m ? "active" : "", text: l, onclick: () => { t.mode = m; touchDraft(); renderEditor(); }}))));
  if (t.mode === "timer") box.append(num("minutes", "Minuten", 1, 600));
  if (t.mode === "pomodoro") box.append(el("div", {class: "row"}, num("work", "Arbeiten (Minuten)", 1, 180), num("break", "Pause (Minuten)", 1, 60)));
  box.append(el("p", {class: "hint", text: {
    timer: "Startet den Countdown und zeigt ihn groß auf dem Display. Am Ende: Signalton, Beleuchtung blinkt, Displaytaste bestätigt. Während der Anzeige: OK = Pause, Hoch = +1 Minute, Runter = beenden, BACK = zurück (der Timer läuft in der Fußzeile weiter).",
    stopwatch: "Startet die Stoppuhr. OK = Start/Stopp, Runter = auf 0, BACK = zurück (läuft in der Fußzeile weiter).",
    pomodoro: "Wechselt automatisch zwischen Arbeits- und Pausenphase und zählt die Runden. Bei jedem Wechsel: Signalton und kurze Einblendung. Runter = beenden."}[t.mode]}),
    el("p", {class: "hint", text: "Ein zweiter Druck auf dieselbe G-Taste hält an bzw. zeigt den Timer wieder an."}));
}
function keySelect(value, onchange, placeholder) {
  const sel = el("select", {onchange: e => { onchange(e.target.value); if (placeholder) e.target.value = ""; }});
  if (placeholder) sel.append(el("option", {value: "", text: placeholder}));
  const groups = {};
  for (const k of S.keys) (groups[k.group] = groups[k.group] || []).push(k);
  if (value && !S.keyLabel[value]) sel.append(el("option", {value, text: value, selected: true}));
  for (const [g, ks] of Object.entries(groups))
    sel.append(el("optgroup", {label: g}, ks.map(k => el("option", {value: k.name, text: k.label, selected: k.name === value}))));
  if (!placeholder) sel.style.minWidth = "150px";
  return sel;
}
function actionSelect(value, onchange) {
  return el("select", {onchange: e => onchange(e.target.value)},
    [["tap", "tippen"], ["down", "drücken"], ["up", "loslassen"]].map(([v, t]) => el("option", {value: v, text: t, selected: v === value})));
}
