"""Tippen im deutschen Layout, Tastenkombinationen, Beschriftungen."""
from common import g, eq, ok, done

steps, unknown = g.text_to_steps("Grüße @ 5€!")
keys = [s[1] for s in steps if s[2] in ("down", "tap")]
eq(keys[:3], ["KEY_LEFTSHIFT", "KEY_G", "KEY_R"], "Großbuchstabe mit Umschalt")
ok("KEY_LEFTBRACE" in keys and "KEY_MINUS" in keys, "ü und ß")
ok("KEY_RIGHTALT" in keys and "KEY_Q" in keys and "KEY_E" in keys, "@ und € über AltGr")
eq(unknown, [], "keine unbekannten Zeichen")
eq(g.text_to_steps("✓")[1], ["✓"], "unbekanntes Zeichen gemeldet")
eq(g.combo_to_steps(["KEY_LEFTCTRL", "KEY_C"]), [[0, "KEY_LEFTCTRL", "down"], [5, "KEY_C", "down"], [g.TAP_MS, "KEY_C", "up"], [5, "KEY_LEFTCTRL", "up"]], "Kombination")
eq(g.entry_label({"open": "https://www.heise.de/x"}), "heise.de", "Beschriftung Webseite")
eq(g.entry_label({"timer": {"mode": "pomodoro", "work": 50, "break": 10}}), "Pomodoro 50/10", "Beschriftung Pomodoro")
eq(g.entry_label({"snippets": "*"}), "Textbausteine", "Beschriftung Textbausteine")
eq(g.entry_label({"sleep": 30}), "Einschlafen 30 min", "Beschriftung Einschlaftimer")
eq(g.entry_label({"volume": "mute"}), "Stumm", "Beschriftung Lautstärke")
eq(g.entry_label({"radio": "u"}, {"stations": [{"url": "u", "name": "BOB"}]}), "BOB", "Beschriftung Radiosender")
eq(g.key_label("KEY_LEFTCTRL"), "Strg", "Tastenname deutsch")
ok(len(g.compile_steps({"text": "ab"})) == 4, "Schritte übersetzt")
done()
