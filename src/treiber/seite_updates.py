"""Displayseite „Updates“: verfügbare Paket- und Flatpak-Updates, Neustart-Hinweis."""


class UpdatesPage:
    # ---- Updates -------------------------------------------------------- #
    @page("updates")
    def page_updates(self, profile, macros):
        data, hint = self._poll_state(self.updates, "↻", "Updates")
        if hint:
            return hint
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        self._header(d, "Updates", "geprüft " + data.get("checked", ""))
        n = data.get("apt", 0) + (data.get("flatpak") or 0)
        color = (62, 207, 126) if n == 0 else PROFILE_COLOR.get(profile, self.FG)
        self._center(d, 30, str(n), self.f_huge, color)
        self._center(d, 112, "System ist aktuell" if n == 0 else ("Update verfügbar" if n == 1 else "Updates verfügbar"),
                     self.f_mid, self.FG)
        y = 142
        parts = [f"Pakete: {data.get('apt', 0)}"]
        if data.get("flatpak") is not None:
            parts.append(f"Flatpak: {data['flatpak']}")
        self._center(d, y, " · ".join(parts), self.f_small, self.DIM)
        y += 22
        if data.get("security"):
            self._center(d, y, f"davon {data['security']} Sicherheitsupdate{'s' if data['security'] != 1 else ''}",
                         self.f_small_b, (240, 120, 80))
            y += 22
        if data.get("reboot"):
            d.rounded_rectangle([40, y, WIDTH - 40, y + 22], radius=6, fill=(150, 40, 40))
            self._center(d, y + 2, "Neustart erforderlich", self.f_small_b, (255, 255, 255))
        return img


@page_keys("updates")
def keys_updates(app, pressed):
    """MENU = neu prüfen, OK = Aktualisierung öffnen (Discover)."""
    if pressed & LKEY_BITS["MENU"]:
        refresh_page(app, "updates")
        return True
    if pressed & LKEY_BITS["OK"]:
        cmd = "plasma-discover --mode update" if shutil.which("plasma-discover") else "konsole -e sudo apt full-upgrade"
        if app.launcher.start(cmd):
            app.show("Updates", ["Discover wird geöffnet"], PROFILE_COLOR[app.layer], 1.8)
        return True
    return False
