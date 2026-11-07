"""Klanganalyse für die Seite „Visualisierung“: hört den Ausgang (Monitor) von PipeWire mit.

Aufnahme mit pw-record (stream.capture.sink = Monitor des Standard-Ausgangs), ersatzweise parec.
Nur solange want() regelmäßig aufgerufen wird (Seite sichtbar); danach endet die Aufnahme.
Wortbeiträge (Nachrichten, Moderation): Sprache hat viele kurze Pausen, schwankt stark in der Lautstärke
und hat kaum Bass – Musik läuft durch. Hält das gut 5 s an, meldet snapshot() "talk" (Tänzerin langweilt sich),
nach 2 s Musik wieder nicht. Werbung mit Musik darunter erkennt nur der Titel des Senders (seite_visual).
Der Monitor bekommt Stummschalten und Lautstärke des Ausgangs nicht mit – deshalb wird jede Sekunde
nachgefragt (change_volume "get"); ist der Ausgang stumm oder auf 0 %, gilt das wie Stille.
Es wird nichts gespeichert, das Mikrofon wird nicht benutzt. snapshot() liefert Bänder (0…1),
Pegel links/rechts, Bass/Mitten/Höhen, Wellenform und einen Taktzähler (Bass) sowie hohe Schläge (Hi-Hat, Snare: hats/hat_t/hat) für die Zeichenfunktionen.
demo_snapshot() erzeugt dieselben Werte künstlich (Vorschau der Verwaltung, Leerlauf, Tests).
"""
import select

AUDIO_RATE = 22050
AUDIO_FFT = 2048
AUDIO_BANDS = 64
AUDIO_HAT_BAND = 47                     # ab hier (≈ 2,5 kHz) zählen Hi-Hat, Snare, Klatschen als „hohe Schläge“
AUDIO_CMDS = [
    ["pw-record", "--rate", str(AUDIO_RATE), "--channels", "2", "--format", "s16",
     "-P", '{ stream.capture.sink = true node.name = "g19s-visualisierung" media.name = "G19s Visualisierung" }', "-"],
    ["parec", "-d", "@DEFAULT_MONITOR@", "--format=s16le", f"--rate={AUDIO_RATE}", "--channels=2", "--raw",
     "--client-name=G19s Visualisierung"],
]


def _band_edges():
    """FFT-Bins je Band, logarithmisch von 40 Hz bis 11 kHz (jedes Band mindestens ein Bin)."""
    freqs = np.geomspace(40, min(11000, AUDIO_RATE / 2 - 1), AUDIO_BANDS + 1)
    bins = np.round(freqs * AUDIO_FFT / AUDIO_RATE).astype(int)
    edges = []
    for i in range(AUDIO_BANDS):
        lo = int(bins[i])
        hi = max(int(bins[i + 1]), lo + 1)
        edges.append((lo, hi))
    return edges


def _empty_snapshot(t=0.0):
    return {"t": t, "bands": np.zeros(AUDIO_BANDS), "left": 0.0, "right": 0.0, "level": 0.0, "bass": 0.0,
            "mid": 0.0, "treble": 0.0, "wave": np.zeros(640), "wave_l": np.zeros(256), "wave_r": np.zeros(256),
            "beats": 0, "beat_t": -10.0, "period": 0.5, "active": False, "error": None, "demo": False, "muted": False, "volume": None,
            "talk": False, "talk_t": 0.0, "hats": 0, "hat_t": -10.0, "hat": 0.0}


def demo_snapshot(t, amp=1.0):
    """Künstliche Musik (120 Schläge/min) für Vorschau, Leerlauf und Referenzbilder; nur abhängig von t."""
    beat_phase = (t * 2.0) % 1.0
    kick = math.exp(-beat_phase * 7.0)
    x = np.linspace(0, 1, AUDIO_BANDS)
    bands = (0.75 - 0.45 * x + 0.18 * np.sin(x * 19 + t * 3.1) + 0.12 * np.sin(x * 41 - t * 5.3))
    bands[:8] += 0.35 * kick
    bands[20:34] += 0.15 * (0.5 + 0.5 * math.sin(t * 2.7))
    bands = np.clip(bands * (0.55 + 0.45 * kick) * amp, 0, 1)
    n = np.arange(640)
    wave = amp * (0.55 * (0.4 + 0.6 * kick) * np.sin(n * 0.03 + t * 40) + 0.22 * np.sin(n * 0.11 + t * 13)
                  + 0.08 * np.sin(n * 0.47 - t * 7))
    k = np.arange(256)
    wl = amp * (0.6 * np.sin(k * 0.11 + t * 3) + 0.2 * np.sin(k * 0.53))
    wr = amp * (0.6 * np.sin(k * 0.11 + t * 3 + 1.1) + 0.2 * np.cos(k * 0.47))
    level = float(np.clip((0.55 + 0.4 * kick) * amp, 0, 1))
    snap = _empty_snapshot(t)
    snap.update(bands=bands, wave=wave, wave_l=wl, wave_r=wr, level=level,
                left=float(np.clip(level * (0.95 + 0.05 * math.sin(t * 1.3)), 0, 1)),
                right=float(np.clip(level * (0.9 + 0.08 * math.cos(t * 1.1)), 0, 1)),
                bass=float(np.clip((0.35 + 0.65 * kick) * amp, 0, 1)), mid=float(np.mean(bands[16:40])),
                treble=float(np.mean(bands[40:])), beats=int(t * 2.0), beat_t=math.floor(t * 2.0) / 2.0, period=0.5,
                active=amp > 0.5, demo=True,
                hats=int(t * 4.0), hat_t=math.floor(t * 4.0) / 4.0,     # Hi-Hat in Achteln, Snare auf 2 und 4
                hat=(1.0 if int(t * 4.0) % 4 == 2 else 0.55) * min(1.0, amp * 1.2))
    return snap


class SoundAnalyzer:
    """Liest den Monitor des Standard-Ausgangs und wertet ihn aus (eigener Faden, nur bei Bedarf)."""
    BLOCK = 512                         # Frames je Auswertung (≈ 43 je Sekunde)
    IDLE_STOP = 2.0                     # so lange nach dem letzten want() läuft die Aufnahme weiter

    def __init__(self, env_func, log=print):
        self.env_func, self.log = env_func, log
        self.lock = threading.Lock()
        self.thread = None
        self.wanted_until = 0.0
        self.proc = None
        self.running = True
        self.edges = _band_edges()
        self.edge_lo = np.array([lo for lo, _ in self.edges])
        self.edge_hi = np.array([hi for _, hi in self.edges])
        self.edge_hat = AUDIO_HAT_BAND
        self.window = np.hanning(AUDIO_FFT)
        self._snap = _empty_snapshot()
        self._error_logged = None
        self.muted, self.mute_checked = False, 0.0
        self.volume = None                  # Lautstärke in Prozent (Weihnachten/Feierabend reagiert darauf)
        self.reset()

    def reset(self):
        self.ring = np.zeros(AUDIO_FFT)
        self.bands = np.zeros(AUDIO_BANDS)
        self.ref_db = -30.0             # gleitender Höchstwert der Bänder (automatische Verstärkung)
        self.bass_hist, self.flux_hist, self.intervals = [], [], []
        self.prev_log = None
        self.beats, self.beat_t = 0, -10.0
        self.prev_hi, self.hats, self.hat_t, self.hat = None, 0, -10.0, 0.0
        self.hat_hist = []                  # Höhen-Fluss der letzten ≈ 0,7 s
        self.env_rms, self.env_bass = [], []        # je Block (≈ 4 s): Lautstärke, Bassanteil
        self.talk, self.talk_t, self.talk_votes = False, 0.0, 0
        self.talk_feat = (0.0, 0.0, 0.0)
        self.vu = [0.0, 0.0]

    # -- öffentlich -------------------------------------------------------- #
    def want(self):
        """Seite (oder Vorschau im Menü) ist sichtbar: Aufnahme starten bzw. weiterlaufen lassen."""
        self.wanted_until = time.monotonic() + self.IDLE_STOP
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, daemon=True, name="Klanganalyse")
            self.thread.start()

    def snapshot(self):
        with self.lock:
            return dict(self._snap)

    def start(self):
        pass                            # startet erst mit want()

    def stop(self):
        self.running = False
        self.wanted_until = 0.0
        self._kill()

    # -- Faden ------------------------------------------------------------- #
    def _command(self):
        for cmd in AUDIO_CMDS:
            if shutil.which(cmd[0]):
                return cmd
        return None

    def _set_error(self, msg):
        with self.lock:
            self._snap = dict(_empty_snapshot(time.monotonic()), error=msg)
        if msg != self._error_logged:
            self._error_logged = msg
            self.log(f"Visualisierung: {msg}")

    def _kill(self):
        proc, self.proc = self.proc, None
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    proc.kill()
                except OSError:
                    pass

    def _run(self):
        frame_bytes = self.BLOCK * 4    # Stereo, 16 Bit
        buf = b""
        while self.running and time.monotonic() < self.wanted_until:
            if time.monotonic() >= self.mute_checked + 1.0:
                self.mute_checked = time.monotonic()
                vol = change_volume("get", env=self.env_func())
                self.muted = bool(vol and (vol[1] or vol[0] == 0))
                self.volume = vol[0] if vol else None
            if self.proc is None or self.proc.poll() is not None:
                if self.proc is not None:
                    self._set_error("Aufnahmeprogramm hat sich beendet – neuer Versuch in 5 s")
                    self.proc = None
                    time.sleep(5)
                    continue
                cmd = self._command()
                if not cmd:
                    self._set_error("pw-record fehlt (Paket pipewire-bin)")
                    time.sleep(5)
                    continue
                try:
                    self.proc = subprocess.Popen(cmd, env=self.env_func(), stdin=subprocess.DEVNULL,
                                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                                 start_new_session=True)
                except OSError as ex:
                    self._set_error(f"Aufnahme nicht möglich: {ex}")
                    time.sleep(5)
                    continue
                self.reset()
                buf = b""
                if self._error_logged != "ok":
                    self._error_logged = "ok"
                    self.log(f"Visualisierung: höre den Ausgang mit ({cmd[0]})")
            fd = self.proc.stdout.fileno()
            ready, _, _ = select.select([fd], [], [], 0.3)
            if not ready:
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                chunk = b""
            if not chunk:
                continue
            buf += chunk
            while len(buf) >= frame_bytes:
                block, buf = buf[:frame_bytes], buf[frame_bytes:]
                self.feed(np.frombuffer(block, dtype="<i2").astype(np.float32) / 32768.0, time.monotonic())
            if len(buf) > frame_bytes * 8:
                buf = buf[-frame_bytes:]        # hinkt hinterher: nur das Neueste auswerten
        self._kill()
        with self.lock:
            self._snap = _empty_snapshot(time.monotonic())

    # -- Auswertung -------------------------------------------------------- #
    def feed(self, samples, now):
        """Ein Block Stereo-Samples (L, R abwechselnd, −1…1) auswerten."""
        left, right = samples[0::2], samples[1::2]
        mono = (left + right) * 0.5
        n = len(mono)
        self.ring = np.concatenate([self.ring[n:], mono])
        spec = np.abs(np.fft.rfft(self.ring * self.window))
        csum = np.concatenate(([0.0], np.cumsum(spec)))   # Mittel je Band in einem Schritt
        raw = (csum[self.edge_hi] - csum[self.edge_lo]) / (self.edge_hi - self.edge_lo)
        db = 20 * np.log10(raw + 1e-9)
        peak = float(db.max())
        self.ref_db = max(peak, self.ref_db - 0.04, -60.0)       # Verstärkung passt sich langsam an
        val = np.clip((db - (self.ref_db - 48.0)) / 48.0, 0, 1)
        rms = float(np.sqrt(np.mean(mono ** 2)))
        active = rms > 2e-4 and not self.muted
        if not active:
            val = val * 0.0
        self.bands = np.maximum(val, self.bands * 0.82)         # schnell hoch, langsam runter
        levels = []
        for i, ch in enumerate((left, right)):
            r = float(np.sqrt(np.mean(ch ** 2)))
            target = float(np.clip((20 * math.log10(r + 1e-9) + 45.0) / 45.0, 0, 1))
            self.vu[i] += (target - self.vu[i]) * (0.5 if target > self.vu[i] else 0.15)
            levels.append(self.vu[i])
        self._detect_beat(float(np.mean(raw[:10] ** 2)), active, now)    # Bass bis ≈ 160 Hz
        hi = raw[self.edge_hat:]                                        # Höhen ab ≈ 2,5 kHz
        hi_flux = float(np.maximum(0.0, hi - self.prev_hi).sum() / (raw.sum() + 1e-9)) \
            if self.prev_hi is not None else 0.0                       # Anstieg im Verhältnis zum ganzen Klang
        self.prev_hi = hi
        self._detect_hat(hi_flux, active, now)
        if not self.muted:                  # auch stille Blöcke zählen (Sprechpausen)
            power = raw ** 2
            self._detect_talk(rms, float(power[:8].sum() / (power.sum() + 1e-12)), now)
        b = self.bands
        period = float(np.median(self.intervals)) if len(self.intervals) >= 3 else 0.5
        snap = {"t": now, "bands": b.copy(), "left": levels[0], "right": levels[1],
                "level": (levels[0] + levels[1]) / 2, "bass": float(b[:8].mean()), "mid": float(b[16:40].mean()),
                "treble": float(b[40:].mean()), "wave": self.ring[-640:].copy() * 3.0,
                "wave_l": left[-256:].copy() * 3.0, "wave_r": right[-256:].copy() * 3.0,
                "beats": self.beats, "beat_t": self.beat_t, "period": period, "active": active, "error": None, "demo": False,
                "talk": self.talk, "talk_t": self.talk_t,
                "muted": self.muted, "volume": self.volume,
                "hats": self.hats, "hat_t": self.hat_t, "hat": self.hat}
        with self.lock:
            self._snap = snap

    def _detect_beat(self, energy, active, now):
        """Schlag = Bassenergie steigt deutlich: über dem 1,3-Fachen des Mittels der letzten Sekunde (und steigend)
        oder ein ungewöhnlich starker Anstieg (Fluss) – so auch bei dichter Musik, in der der Bass nie leise wird.
        Aus den Abständen ergibt sich das Tempo (period)."""
        log_e = math.log10(energy + 1e-12)
        flux = max(0.0, log_e - self.prev_log) if self.prev_log is not None else 0.0
        self.prev_log = log_e
        hist, fh = self.bass_hist, self.flux_hist
        if active and len(hist) > 20 and now - self.beat_t > 0.25:
            avg = sum(hist) / len(hist)
            mf = sum(fh) / len(fh)
            sf = math.sqrt(sum((f - mf) ** 2 for f in fh) / len(fh))
            rising = energy > hist[-1] * 1.15
            if (energy > avg * 1.3 and rising) or (flux > mf + 1.5 * sf and flux > 0.05):
                gap = now - self.beat_t
                if 0.27 <= gap <= 1.2:
                    self.intervals = (self.intervals + [gap])[-8:]
                self.beats += 1
                self.beat_t = now
        hist.append(energy)
        fh.append(flux)
        if len(hist) > 43:
            hist.pop(0)
            fh.pop(0)

    def _detect_hat(self, flux, active, now):
        """Hoher Schlag (Hi-Hat, Snare, Klatschen): die Höhen ab ≈ 2,5 kHz springen deutlich nach oben – Fluss über
        Mittel + 1,5 Standardabweichungen der letzten ≈ 0,7 s; höchstens alle 70 ms. hat = Stärke 0…1."""
        hist = self.hat_hist
        if active and len(hist) > 12 and now - self.hat_t > 0.07:
            m = sum(hist) / len(hist)
            sd = math.sqrt(sum((f - m) ** 2 for f in hist) / len(hist))
            if flux > m + 1.5 * sd and flux > 0.004:
                self.hats += 1
                self.hat_t = now
                self.hat = float(min(1.0, (flux - m) / (4.0 * sd + 0.004)))
        hist.append(flux)
        if len(hist) > 30:
            hist.pop(0)

    TALK_WINDOW = 172                   # Blöcke ≈ 4 s
    TALK_ON, TALK_OFF = 2.0, 2.0        # so lange muss Sprache bzw. Musik nach vollem Fenster anhalten (s)

    def _detect_talk(self, rms, bass_share, now):
        """Sprache oder Musik? Pausenanteil (Blöcke unter 20 % des lauten Pegels), Schwankung der Lautstärke
        und Bassanteil (< 80 Hz) über die letzten ≈ 4 s; Wechsel erst, wenn das Urteil eine Weile anhält."""
        self.env_rms.append(rms)
        self.env_bass.append(bass_share)
        if len(self.env_rms) > self.TALK_WINDOW:
            self.env_rms.pop(0)
            self.env_bass.pop(0)
        if len(self.env_rms) < self.TALK_WINDOW or len(self.env_rms) % 4:
            return                              # erst bei vollem Fenster, dann ≈ 10× je Sekunde
        env = np.array(self.env_rms)
        loud = float(np.percentile(env, 90)) + 1e-9
        below = env < 0.2 * loud
        pause = float(np.mean(below))
        gaps = int(np.count_nonzero(below[1:] & ~below[:-1]))      # Anzahl einzelner Pausen (Sprache: viele kurze)
        cv = float(env.std() / (env.mean() + 1e-9))
        bass = float(np.mean(self.env_bass))
        self.talk_feat = (pause, cv, bass, gaps)
        # Am echten Radio (2026-11-05): Sprache Pausen 0,15–0,23 / Schwankung 0,52–0,68 / Bass 0,01–0,24 –
        # Moderation über Musikbett hat Bass, aber weiter Pausen. Gerockte Musik hat praktisch keine Pausen.
        speech = pause >= 0.15 and cv >= 0.5 and bass <= 0.3 and gaps >= 4
        music = pause <= 0.08 or (bass >= 0.35 and pause < 0.12)
        need = int((self.TALK_OFF if self.talk else self.TALK_ON) * 10.75)    # Prüfungen ≈ 10,75 je Sekunde
        if (speech and not self.talk) or (music and self.talk):
            self.talk_votes += 1
            if self.talk_votes >= need:
                self.talk, self.talk_votes = not self.talk, 0
                if self.talk:
                    self.talk_t = now
                self.log(f"Visualisierung: {'Wortbeitrag' if self.talk else 'Musik'} erkannt "
                         f"(Pausen {pause:.2f} in {gaps} Lücken, Schwankung {cv:.2f}, Bass {bass:.2f})")
        else:
            self.talk_votes = 0
