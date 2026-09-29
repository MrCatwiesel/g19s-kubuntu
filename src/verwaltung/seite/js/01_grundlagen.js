"use strict";
const TOKEN = location.hash.slice(1);
const GKEYS = Array.from({length: 12}, (_, i) => "G" + (i + 1));
const PROFILES = ["M1", "M2", "M3"];
const TYPES = [
  {id: "default", label: "KDE-Kurzbefehl", icon: "⌨"},
  {id: "text", label: "Text tippen", icon: "✎"},
  {id: "combo", label: "Tastenkombination", icon: "⌘"},
  {id: "steps", label: "Makro", icon: "⏺"},
  {id: "open", label: "Webseite", icon: "🌐"},
  {id: "run", label: "Programm", icon: "▶"},
  {id: "radio", label: "Radiosender", icon: "📻"},
  {id: "media", label: "Musiksteuerung", icon: "♫"},
  {id: "volume", label: "Lautstärke", icon: "🔊"},
  {id: "snippets", label: "Textbausteine", icon: "☰"},
  {id: "timer", label: "Timer", icon: "⏱"},
  {id: "sleep", label: "Einschlaftimer", icon: "☾"},
  {id: "mic", label: "Mikrofon stumm", icon: "🎙"},
];
const TYPE_BY_ID = Object.fromEntries(TYPES.map(t => [t.id, t]));
// KeyboardEvent.code -> evdev-Name (Position auf der Tastatur, unabhängig vom Layout)
const CODE_MAP = (() => {
  const m = {Enter: "KEY_ENTER", Space: "KEY_SPACE", Tab: "KEY_TAB", Backspace: "KEY_BACKSPACE",
    Escape: "KEY_ESC", Delete: "KEY_DELETE", Insert: "KEY_INSERT", Home: "KEY_HOME", End: "KEY_END",
    PageUp: "KEY_PAGEUP", PageDown: "KEY_PAGEDOWN", ArrowUp: "KEY_UP", ArrowDown: "KEY_DOWN",
    ArrowLeft: "KEY_LEFT", ArrowRight: "KEY_RIGHT", ShiftLeft: "KEY_LEFTSHIFT", ShiftRight: "KEY_RIGHTSHIFT",
    ControlLeft: "KEY_LEFTCTRL", ControlRight: "KEY_RIGHTCTRL", AltLeft: "KEY_LEFTALT", AltRight: "KEY_RIGHTALT",
    MetaLeft: "KEY_LEFTMETA", MetaRight: "KEY_RIGHTMETA", OSLeft: "KEY_LEFTMETA", OSRight: "KEY_RIGHTMETA",
    ContextMenu: "KEY_COMPOSE", CapsLock: "KEY_CAPSLOCK", Minus: "KEY_MINUS", Equal: "KEY_EQUAL",
    BracketLeft: "KEY_LEFTBRACE", BracketRight: "KEY_RIGHTBRACE", Backslash: "KEY_BACKSLASH",
    Semicolon: "KEY_SEMICOLON", Quote: "KEY_APOSTROPHE", Backquote: "KEY_GRAVE", Comma: "KEY_COMMA",
    Period: "KEY_DOT", Slash: "KEY_SLASH", IntlBackslash: "KEY_102ND", NumpadAdd: "KEY_KPPLUS",
    NumpadSubtract: "KEY_KPMINUS", NumpadMultiply: "KEY_KPASTERISK", NumpadDivide: "KEY_KPSLASH",
    NumpadDecimal: "KEY_KPDOT", NumpadEnter: "KEY_KPENTER", NumLock: "KEY_NUMLOCK", ScrollLock: "KEY_SCROLLLOCK",
    Pause: "KEY_PAUSE", PrintScreen: "KEY_SYSRQ", AudioVolumeMute: "KEY_MUTE", AudioVolumeUp: "KEY_VOLUMEUP",
    AudioVolumeDown: "KEY_VOLUMEDOWN", MediaPlayPause: "KEY_PLAYPAUSE", MediaTrackNext: "KEY_NEXTSONG",
    MediaTrackPrevious: "KEY_PREVIOUSSONG", MediaStop: "KEY_STOPCD"};
  for (const c of "ABCDEFGHIJKLMNOPQRSTUVWXYZ") m["Key" + c] = "KEY_" + c;
  for (let i = 0; i < 10; i++) { m["Digit" + i] = "KEY_" + i; m["Numpad" + i] = "KEY_KP" + i; }
  for (let i = 1; i <= 24; i++) m["F" + i] = "KEY_F" + i;
  return m;
})();

const S = {macros: {}, settings: null, keys: [], keyLabel: {}, chars: new Set(), media: {}, pages: [],
  mtimes: {}, service: {}, tools: {}, paths: {}};
const UI = {tab: "keys", profile: "M1", gkey: "G1", draft: null, draftDirty: false,
  sdraft: null, sDirty: false, recording: null, pvPage: 3, pvProfile: "M1", testing: null};
