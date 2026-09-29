"""Signalton, Lautstärke und Mikrofon (PipeWire/wpctl, sonst PulseAudio/pactl)."""


ALARM_SOUNDS = ["/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
                "/usr/share/sounds/freedesktop/stereo/complete.oga",
                "/usr/share/sounds/freedesktop/stereo/bell.oga",
                "/usr/share/sounds/Oxygen-Im-Nudge.ogg"]


def play_alarm(env, repeat=2):
    """Signalton über PipeWire/PulseAudio (im Hintergrund, Fehler werden ignoriert)."""
    sound = next((f for f in ALARM_SOUNDS if os.path.exists(f)), None)
    player = next((p for p in ("pw-play", "paplay", "canberra-gtk-play") if shutil.which(p)), None)
    if not sound or not player:
        return False

    def work():
        for _ in range(repeat):
            args = [player, "-f", sound] if player == "canberra-gtk-play" else [player, sound]
            try:
                subprocess.run(args, env=env, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (OSError, subprocess.TimeoutExpired):
                return
    threading.Thread(target=work, daemon=True).start()
    return True


# --------------------------------------------------------------------------- #
# Lautstärke (PipeWire/wpctl, sonst PulseAudio/pactl)
# --------------------------------------------------------------------------- #
def change_volume(action, step=5, env=None):
    """action: up, down, mute. Gibt (Prozent, stumm) zurück oder None."""
    import shutil
    run = lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env)
    step = max(1, min(25, int(step or 5)))
    try:
        if shutil.which("wpctl"):
            sink = "@DEFAULT_AUDIO_SINK@"
            if action == "mute":
                run(["wpctl", "set-mute", sink, "toggle"])
            elif action in ("up", "down"):
                run(["wpctl", "set-volume", "-l", "1.0", sink, f"{step}%{'+' if action == 'up' else '-'}"])
            out = run(["wpctl", "get-volume", sink]).stdout
            m = re.search(r"Volume:\s*([\d.]+)", out)
            return (round(float(m.group(1)) * 100), "MUTED" in out) if m else None
        if shutil.which("pactl"):
            sink = "@DEFAULT_SINK@"
            if action == "mute":
                run(["pactl", "set-sink-mute", sink, "toggle"])
            elif action in ("up", "down"):
                run(["pactl", "set-sink-volume", sink, f"{'+' if action == 'up' else '-'}{step}%"])
            vol = re.search(r"(\d+)%", run(["pactl", "get-sink-volume", sink]).stdout)
            mute = "yes" in run(["pactl", "get-sink-mute", sink]).stdout
            return (int(vol.group(1)), mute) if vol else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return None


def mic_state(env=None, toggle=False):
    """Mikrofon (Standardquelle) abfragen bzw. umschalten. True = stumm, None = unbekannt."""
    run = lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=3, env=env)
    try:
        if shutil.which("wpctl"):
            src = "@DEFAULT_AUDIO_SOURCE@"
            if toggle:
                run(["wpctl", "set-mute", src, "toggle"])
            out = run(["wpctl", "get-volume", src]).stdout
            return "MUTED" in out if "Volume" in out else None
        if shutil.which("pactl"):
            src = "@DEFAULT_SOURCE@"
            if toggle:
                run(["pactl", "set-source-mute", src, "toggle"])
            out = run(["pactl", "get-source-mute", src]).stdout
            return ("yes" in out) if out else None
    except (OSError, subprocess.SubprocessError):
        return None
    return None
