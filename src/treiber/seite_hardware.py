"""Displayseite „Hardware“: Prozessor (Temperatur, Auslastung), Grafikkarte, SSD, Arbeitsspeicher,
Lüfter, Netzwerkdurchsatz, Datenträger. (Enthält auch die frühere Seite „System“.)"""


class HardwarePage:
    # ---- Hardware ------------------------------------------------------- #
    def _temp_row(self, d, y, label, temp, extra=""):
        d.text((12, y), label, font=self.f_small_b, fill=self.FG)
        if temp is None:
            d.text((80, y), "nicht verfügbar", font=self.f_small, fill=self.DIM)
            return
        pct = max(0.0, min(1.0, (temp - 20) / 70))
        color = (62, 207, 126) if temp < 60 else (240, 169, 59) if temp < 80 else (235, 80, 80)
        txt = f"{temp:.0f} °C" + (f" · {extra}" if extra else "")
        tx = WIDTH - 12 - d.textlength(txt, font=self.f_small)
        end = int(min(230, tx - 10))
        d.rounded_rectangle([80, y + 5, end, y + 13], radius=4, fill=(35, 40, 55))
        if pct > 0.03:
            d.rounded_rectangle([80, y + 5, 80 + int((end - 80) * pct), y + 13], radius=4, fill=color)
        d.text((tx, y), txt, font=self.f_small, fill=self.FG)

    @staticmethod
    def _rate(b):
        for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
            if b < 1000 or unit == "GB/s":
                return f"{b:.0f} {unit}" if unit == "B/s" else f"{b:.1f} {unit}"
            b /= 1000

    def _usage_row(self, d, y, label, pct, txt, profile):
        """Zeile mit Balken in der Farbe der Ebene (rot ab 90 %) und Text rechts."""
        d.text((12, y), label, font=self.f_small_b, fill=self.FG)
        tx = WIDTH - 12 - d.textlength(txt, font=self.f_tiny)
        end = int(min(230, tx - 10))
        d.rounded_rectangle([80, y + 5, end, y + 13], radius=4, fill=(35, 40, 55))
        color = PROFILE_COLOR.get(profile, self.FG) if pct < 90 else (235, 80, 80)
        d.rounded_rectangle([80, y + 5, 80 + max(8, int((end - 80) * min(100, pct) / 100)), y + 13], radius=4, fill=color)
        d.text((tx, y + 2), txt, font=self.f_tiny, fill=self.DIM)

    @page("hardware")
    def page_hardware(self, profile, macros):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        s, row = self.hw.sensors(), 22
        self._temp_row(d, 8, "CPU", s["cpu"], f"{self.stats.cpu_percent():.0f} %")
        self._temp_row(d, 8 + row, "GPU", s["gpu"], f"{s['gpu_load']} %" if s["gpu_load"] is not None else "")
        y = 8 + 2 * row
        if s["nvme"] is not None:
            self._temp_row(d, y, "SSD", s["nvme"])
            y += row
        used, total, mem_pct = self.stats.memory()
        self._usage_row(d, y, "RAM", mem_pct, f"{used:.1f} / {total:.1f} GiB", profile)
        y += row
        if s["fans"]:
            fans = " · ".join(f"{rpm} U/min" for _, rpm in s["fans"][:3])
            d.text((12, y), "Lüfter", font=self.f_small_b, fill=self.FG)
            d.text((80, y), self._fit(d, fans, self.f_small, WIDTH - 92), font=self.f_small, fill=self.FG)
            y += row
        net = self.hw.network()
        if net:
            d.text((12, y), "Netz", font=self.f_small_b, fill=self.FG)
            d.text((80, y), f"↓ {self._rate(net[0])}   ↑ {self._rate(net[1])}", font=self.f_small, fill=self.FG)
            y += row
        for label, pct, total in self.hw.disks()[:2]:
            if y > HEIGHT - 48:
                break
            self._usage_row(d, y, label, pct, f"{pct:.0f} % v. {total / 1e9:.0f} GB", profile)
            y += row
        l1, l5, l15 = self.stats.load()
        if y <= HEIGHT - 48:
            d.text((12, y), "Last", font=self.f_small_b, fill=self.FG)
            d.text((80, y), f"{l1:.2f}  {l5:.2f}  {l15:.2f}", font=self.f_small, fill=self.DIM)
        return img
