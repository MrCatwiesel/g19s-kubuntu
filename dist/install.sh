#!/usr/bin/env bash
# G19s-Treiber für Linux – Installer (Version 2026.11.07-9)
#
#   Installieren/Aktualisieren:  bash install.sh
#   ohne Rückfragen:             bash install.sh --ja
#   Pakete selbst installieren:  bash install.sh --ohne-pakete
#   Entfernen:                   bash install.sh --deinstallieren [--alles]
#
# Direkt aus dem Netz:
#   curl -fsSL https://github.com/MrCatwiesel/g19s-kubuntu/releases/latest/download/install.sh | bash
#
# Installiert für den angemeldeten Benutzer: Programme nach ~/.local/bin, Autostart als systemd-
# Benutzerdienst, Menüeintrag „G19s-Verwaltung“. Mit sudo (fragt nach dem Passwort): benötigte Pakete,
# udev-Regel (Zugriff auf die Tastatur) und die Gruppe „input“ (Makroaufnahme).
set -euo pipefail

VERSION="2026.11.07-9"
REPO="MrCatwiesel/g19s-kubuntu"
BIN="$HOME/.local/bin"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"
UNIT_DIR="$CONF/systemd/user"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/g19s"
UDEV_DIR="${G19S_UDEV_DIR:-/etc/udev/rules.d}"          # für Tests umlenkbar
SRC_URL="${G19S_DOWNLOAD_URL:-https://github.com/$REPO/releases/download/v$VERSION}"
END_MARKER="# G19S-DATEIENDE"

USER="${USER:-$(id -un)}"
YES=0; PACKAGES=1; MODE=install; ALL=0
for arg in "$@"; do
  case "$arg" in
    --ja|-y) YES=1 ;;
    --ohne-pakete) PACKAGES=0 ;;
    --deinstallieren|--uninstall) MODE=uninstall ;;
    --alles) ALL=1 ;;
    --hilfe|-h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unbekannte Option: $arg (Hilfe: --hilfe)" >&2; exit 2 ;;
  esac
done

if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B=; G=; Y=; R=; N=; fi
step() { echo; echo "${B}▶ $*${N}"; }
ok()   { echo "  ${G}✓${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; NOTES+=("$*"); }
die()  { echo "${R}✗ $*${N}" >&2; exit 1; }
NOTES=()
RELOGIN=0

ask() {   # ask "Frage" → 0 = ja; liest von der Tastatur, auch wenn das Skript per „curl | bash“ läuft
  [ "$YES" = 1 ] && return 0
  local answer=""
  if [ -r /dev/tty ]; then read -r -p "$1 [J/n] " answer < /dev/tty || answer=""; else return 0; fi
  case "${answer,,}" in ""|j|ja|y|yes) return 0 ;; *) return 1 ;; esac
}

[ "$(id -u)" -ne 0 ] || [ -n "${G19S_INSTALL_TEST:-}" ] || die "Bitte als normaler Benutzer starten (nicht mit sudo) – das Skript fragt selbst nach, wo nötig."
command -v python3 >/dev/null || die "python3 fehlt – bitte zuerst installieren."
command -v systemctl >/dev/null || die "systemd fehlt – der Treiber startet als systemd-Benutzerdienst."

USER_BUS=1
systemctl --user show-environment >/dev/null 2>&1 || USER_BUS=0

# --------------------------------------------------------------------------- Deinstallieren
if [ "$MODE" = uninstall ]; then
  echo "${B}G19s-Treiber entfernen${N}"
  ask "Treiber, Verwaltung, Autostart, Menüeintrag und udev-Regel entfernen?" || exit 0
  step "Autostart"
  if [ "$USER_BUS" = 1 ]; then systemctl --user disable --now g19s.service >/dev/null 2>&1 || true; fi
  rm -f "$UNIT_DIR/g19s.service"
  [ "$USER_BUS" = 1 ] && systemctl --user daemon-reload || true
  ok "Dienst gestoppt und entfernt"
  step "Programme und Menüeintrag"
  rm -f "$BIN/g19s.py" "$BIN/g19s-gui.py" "$APPS/g19s-gui.desktop"
  ok "entfernt"
  step "udev-Regel"
  if [ -f "$UDEV_DIR/70-g19s.rules" ]; then
    sudo rm -f "$UDEV_DIR/70-g19s.rules" && sudo udevadm control --reload-rules || true
  fi
  ok "entfernt"
  if [ "$ALL" = 1 ]; then
    step "Einstellungen und Daten"
    if ask "Auch Einstellungen, Makros, Sicherungskopien alter Versionen löschen ($CONF/g19s, $DATA)?"; then
      rm -rf "$CONF/g19s" "$DATA" "${XDG_CACHE_HOME:-$HOME/.cache}/g19s"
      ok "gelöscht"
    fi
  else
    echo "  Einstellungen und Makros bleiben in $CONF/g19s (alles löschen: --deinstallieren --alles)."
  fi
  echo
  echo "Fertig. Pakete (mpv, playerctl …) und die Gruppe „input“ bleiben erhalten;"
  echo "die Gruppe entfernt bei Bedarf: sudo gpasswd -d $USER input"
  exit 0
fi

# --------------------------------------------------------------------------- Installieren
echo "${B}G19s-Treiber $VERSION installieren${N}"
OLD=""
[ -f "$BIN/g19s.py" ] && OLD=$(sed -nE 's/^VERSION = "([^"]+)"/\1/p' "$BIN/g19s.py" | head -n1)
[ -n "$OLD" ] && echo "Installiert ist $OLD – wird auf $VERSION aktualisiert."
ask "Fortfahren?" || exit 0

# Pakete -----------------------------------------------------------------------
PM=""; REQ=(); OPT=()
if command -v apt-get >/dev/null; then
  PM=apt; REQ=(python3-usb python3-evdev python3-pil python3-numpy)
  OPT=(playerctl mpv mpv-mpris libnotify-bin smbclient pipewire-bin)
elif command -v dnf >/dev/null; then
  PM=dnf; REQ=(python3-pyusb python3-evdev python3-pillow python3-numpy)
  OPT=(playerctl mpv mpv-mpris libnotify samba-client pipewire-utils)
elif command -v pacman >/dev/null; then
  PM=pacman; REQ=(python-pyusb python-evdev python-pillow python-numpy)
  OPT=(playerctl mpv mpv-mpris libnotify smbclient pipewire)
elif command -v zypper >/dev/null; then
  PM=zypper; REQ=(python3-pyusb python3-evdev python3-Pillow python3-numpy)
  OPT=(playerctl mpv mpv-mpris libnotify-tools samba-client pipewire-tools)
fi

pm_install() {   # pm_install paket… → 0 = alle installiert
  case "$PM" in
    apt) sudo apt-get install -y "$@" ;;
    dnf) sudo dnf install -y "$@" ;;
    pacman) sudo pacman -S --needed --noconfirm "$@" ;;
    zypper) sudo zypper --non-interactive install "$@" ;;
    *) return 1 ;;
  esac
}

step "Pakete"
if [ "$PACKAGES" = 0 ]; then
  echo "  übersprungen (--ohne-pakete)"
elif [ -z "$PM" ]; then
  warn "Paketverwaltung nicht erkannt – bitte selbst installieren: Python-Module usb (pyusb), evdev, PIL (Pillow), numpy; dazu playerctl, mpv, mpv-mpris, pw-record (PipeWire)"
else
  [ "$PM" = apt ] && { sudo apt-get update -qq || warn "apt-get update meldete Fehler"; }
  pm_install "${REQ[@]}" >/dev/null || warn "Nicht alle Grundpakete ließen sich installieren: ${REQ[*]}"
  if ! pm_install "${OPT[@]}" >/dev/null 2>&1; then
    for p in "${OPT[@]}"; do pm_install "$p" >/dev/null 2>&1 || warn "Paket „$p“ nicht installiert (optional)"; done
  fi
  ok "Paketverwaltung: $PM"
fi
python3 -c "import usb, evdev, PIL, numpy" 2>/dev/null \
  || die "Python-Module fehlen (usb, evdev, PIL, numpy) – bitte installieren und das Skript erneut starten."
ok "Python-Module vorhanden"

# Programme --------------------------------------------------------------------
step "Programme"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
local_file() {   # local_file driver|gui → passende Datei neben dem Skript (Name egal, z. B. „g19s(1).py“)
  local c
  [ -n "$HERE" ] || return 1
  for c in "$HERE"/*.py; do
    [ -f "$c" ] || continue
    grep -q "^G19S_COMPONENT = \"$1\"" "$c" && grep -q "^VERSION = \"$VERSION\"" "$c" && { echo "$c"; return 0; }
  done
  return 1
}
fetch_failed() {
  die "$1 der Version $VERSION ist auf GitHub nicht abrufbar. Ist die Version gerade erst erschienen, ein paar
  Minuten warten (GitHub baut sie noch) – oder g19s.py und g19s-gui.py derselben Version neben install.sh legen."
}
for f in g19s.py g19s-gui.py; do
  comp=driver; [ "$f" = g19s-gui.py ] && comp=gui
  if src=$(local_file "$comp"); then
    cp "$src" "$TMP/$f"
    ok "$f aus $(basename "$src")"
  elif command -v curl >/dev/null; then
    curl -fsSL "$SRC_URL/$f" -o "$TMP/$f" || fetch_failed "$f"
  elif command -v wget >/dev/null; then
    wget -q "$SRC_URL/$f" -O "$TMP/$f" || fetch_failed "$f"
  else
    die "Weder curl noch wget gefunden – bitte eines davon installieren."
  fi
  tail -n 1 "$TMP/$f" | grep -q "^$END_MARKER" || die "$f ist unvollständig (Download abgebrochen?)"
  python3 -c "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1], 'exec')" "$TMP/$f" \
    || die "$f ist beschädigt"
done
mkdir -p "$BIN" "$DATA/alte-versionen"
STAMP=$(date +%Y%m%d-%H%M%S)
for f in g19s.py g19s-gui.py; do
  [ -f "$BIN/$f" ] && cp -p "$BIN/$f" "$DATA/alte-versionen/$f.$STAMP"
  install -m 755 "$TMP/$f" "$BIN/$f"
done
if [ -n "$OLD" ]; then ok "nach $BIN (vorherige Version $OLD gesichert in $DATA/alte-versionen)"; else ok "nach $BIN"; fi
python3 "$BIN/g19s-gui.py" --install-desktop >/dev/null && ok "Menüeintrag „G19s-Verwaltung“"

# udev-Regel und Gruppe ---------------------------------------------------------
step "Zugriffsrechte"
RULES_TMP="$TMP/70-g19s.rules"
cat > "$RULES_TMP" <<'G19S_EOF'
# Logitech G19/G19s: Zugriff auf Display/G-Tasten und uinput für den angemeldeten Benutzer
SUBSYSTEM=="usb", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c229", MODE="0660", TAG+="uaccess"
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", TAG+="uaccess", OPTIONS+="static_node=uinput"
# Makroaufnahme: Lesezugriff auf die normale G19-Tastatur (046d:c228)
SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c228", TAG+="uaccess"
G19S_EOF
if [ -f "$UDEV_DIR/70-g19s.rules" ] && cmp -s "$RULES_TMP" "$UDEV_DIR/70-g19s.rules"; then
  ok "udev-Regel ist aktuell"
else
  sudo install -m 644 "$RULES_TMP" "$UDEV_DIR/70-g19s.rules"
  sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=usb --subsystem-match=misc || true
  ok "udev-Regel $UDEV_DIR/70-g19s.rules"
  RELOGIN=1
fi
if id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  ok "Gruppe „input“ (Makroaufnahme)"
else
  sudo usermod -aG input "$USER" && ok "zur Gruppe „input“ hinzugefügt (Makroaufnahme)"
  RELOGIN=1
fi

# Autostart --------------------------------------------------------------------
step "Autostart"
mkdir -p "$UNIT_DIR"
cat > "$UNIT_DIR/g19s.service" <<'G19S_EOF'
[Unit]
Description=Logitech G19s Treiber (Display + G-Tasten)
After=graphical-session.target

[Service]
ExecStart=/usr/bin/python3 %h/.local/bin/g19s.py
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
G19S_EOF
if [ "$USER_BUS" = 1 ]; then
  systemctl --user daemon-reload
  systemctl --user enable g19s.service >/dev/null 2>&1 && ok "Dienst g19s.service startet bei der Anmeldung"
  if systemctl --user is-active --quiet g19s.service; then
    systemctl --user restart g19s.service && ok "Treiber neu gestartet"
  elif [ "$RELOGIN" = 0 ]; then
    systemctl --user start g19s.service && ok "Treiber gestartet"
  fi
else
  warn "Keine Benutzersitzung erreichbar (z. B. per SSH) – nach der Anmeldung: systemctl --user enable --now g19s.service"
fi

# Tastatur ---------------------------------------------------------------------
step "Tastatur"
FOUND=0
for p in /sys/bus/usb/devices/*/idProduct; do
  [ -f "$p" ] || continue
  d=$(dirname "$p")
  if [ "$(cat "$p")" = "c229" ] && [ "$(cat "$d/idVendor" 2>/dev/null)" = "046d" ]; then FOUND=1; fi
done
if [ "$FOUND" = 1 ]; then ok "Logitech G19s gefunden"; else warn "Keine G19s (046d:c229) gefunden – ist die Tastatur eingesteckt?"; fi

# Zusammenfassung --------------------------------------------------------------
echo
echo "${G}${B}Fertig: G19s-Treiber $VERSION ist installiert.${N}"
if [ "$RELOGIN" = 1 ]; then
  echo "${Y}${B}Bitte den Rechner einmal neu starten${N} – erst dann greifen die neuen Zugriffsrechte, und der"
  echo "Treiber startet automatisch."
fi
for n in "${NOTES[@]+"${NOTES[@]}"}"; do echo "  ${Y}!${N} $n"; done
echo "Einstellungen: Startmenü → „G19s-Verwaltung“. Protokoll: journalctl --user -u g19s -n 50"
# Installer für späteres Entfernen aufheben (bei „curl | bash“ gibt es keine Datei – dann neu laden)
SELF="${BASH_SOURCE[0]:-}"
if [ -n "$SELF" ] && [ -f "$SELF" ]; then
  [ "$SELF" -ef "$DATA/install.sh" ] || cp "$SELF" "$DATA/install.sh"
elif command -v curl >/dev/null; then
  curl -fsSL "$SRC_URL/install.sh" -o "$DATA/install.sh" 2>/dev/null || true
fi
[ -f "$DATA/install.sh" ] && echo "Entfernen: bash $DATA/install.sh --deinstallieren"
exit 0
