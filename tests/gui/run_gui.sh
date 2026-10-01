#!/bin/bash
# Browsertests der Verwaltung (Playwright + Chromium).
# Wird von tests/run_tests.py aufgerufen; erwartet G19S_TEST_ROOT, G19S_DRIVER, G19S_GUI.
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=${G19S_TEST_ROOT:-/tmp/g19s-test}
T=$ROOT/gui
mkdir -p $T $ROOT/shots
# Update-Testdateien aus den zu testenden Dateien erzeugen
U=$ROOT/upd; rm -rf $U; mkdir -p $U
sed -E 's/^VERSION = "[^"]+"/VERSION = "2026.09.27-test"/' "$G19S_DRIVER" > "$U/g19s(7).py"
sed -E 's/^VERSION = "[^"]+"/VERSION = "2026.09.27-test"/' "$G19S_GUI" > "$U/g19s-gui(4).py"
sed -E -e 's/^VERSION = "[^"]+"/VERSION = "2026.09.27-kaputt"/' -e '/^VERSION = /a raise SystemExit(3)' "$G19S_GUI" > "$U/g19s-gui-crash.py"
head -c 3000 "$G19S_DRIVER" > "$U/abgeschnitten.py"
cp "$HERE/../fixtures/fremd.py" "$U/fremd.py"

reset_and_start() {
  [ -n "$SERVER_PID" ] && kill $SERVER_PID 2>/dev/null
  pkill -f "g19s-gui[.]py.*--port 8799" 2>/dev/null; sleep 0.6
  rm -rf $T/home $ROOT/state; mkdir -p $ROOT/state $T/home/.local/bin $T/home/.config/g19s
  cp -r "$HERE/home_vorlage/." $T/home/
  cp "$G19S_GUI" $T/home/.local/bin/g19s-gui.py; cp "$G19S_DRIVER" $T/home/.local/bin/g19s.py
  cp "$HERE/../fixtures/macros_alt.json" $T/home/.config/g19s/macros.json
  cd $T/home
  HOME=$T/home XDG_CONFIG_HOME=$T/home/.config XDG_RUNTIME_DIR=$ROOT/state TZ=Europe/Berlin \
    G19S_WEATHER_URL=http://127.0.0.1:8812/v1/forecast G19S_GEOCODE_URL=http://127.0.0.1:8812/v1/search \
    G19S_ALERTS_URL=http://127.0.0.1:8812/alerts G19S_UPDATE_URL=http://127.0.0.1:8812/gh/api/releases NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
    PATH=$ROOT/bin:/usr/bin:/bin PYTHONPATH="$HERE/../stubs" \
    nohup python3 .local/bin/g19s-gui.py --no-browser --port 8799 --token testtoken > $T/server.log 2>&1 &
  SERVER_PID=$!
  for i in $(seq 1 40); do curl -s -o /dev/null --noproxy '*' http://127.0.0.1:8799/ && break; sleep 0.25; done
  cd $T
}
for t in ui_test profiles_test slides_test new_test pkg1_test pkg2_test pkg3_test uhr_test sicherheit_test update_test; do
  reset_and_start
  python3 "$HERE/$t.py" > $T/out_$t.txt 2>&1
  echo "ERGEBNIS $t $(grep -c '^OK' $T/out_$t.txt) $(grep -c '^FEHL' $T/out_$t.txt; true)"
  if grep -q Traceback $T/out_$t.txt; then echo "ERGEBNIS ${t}_absturz 0 1"; fi
done
pkill -f "g19s-gui[.]py.*--port 8799" 2>/dev/null
exit 0
