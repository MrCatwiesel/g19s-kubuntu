"""Displayseite „Netzwerk“: Erreichbarkeit der eingetragenen Geräte mit Antwortzeit."""


class NetworkPage:
    # ---- Netzwerk ------------------------------------------------------- #
    @page("network")
    def page_network(self, profile, macros):
        data, hint = self._poll_state(self.net, "◎", "Netzwerk")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        hosts = data.get("hosts") or []
        up = sum(1 for h in hosts if h["ok"])
        self._header(d, "Netzwerk", f"{up}/{len(hosts)} erreichbar")
        y = 34
        for h in hosts[:8]:
            col = (62, 207, 126) if h["ok"] else (235, 80, 80)
            d.ellipse([14, y + 4, 26, y + 16], fill=col)
            ms = (f"{h['ms']:.0f} ms" if h["ms"] is not None else "ok") if h["ok"] else "offline"
            mw = d.textlength(ms, font=self.f_small)
            d.text((WIDTH - 12 - mw, y), ms, font=self.f_small, fill=col if not h["ok"] else self.DIM)
            d.text((34, y), self._fit(d, h["name"], self.f_small_b, 110), font=self.f_small_b, fill=self.FG)
            d.text((150, y + 2), self._fit(d, h["host"], self.f_tiny, WIDTH - 170 - mw), font=self.f_tiny, fill=self.DIM)
            y += 22
        if data.get("ip"):
            d.text((12, HEIGHT - 48), f"Dieser PC: {data['ip']}", font=self.f_small, fill=self.DIM)
        return img


@page_keys("network")
def keys_network(app, pressed):
    """MENU = neu prüfen."""
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, "network")
        return True
    return False
