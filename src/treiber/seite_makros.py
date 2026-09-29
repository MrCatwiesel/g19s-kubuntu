"""Displayseite „Makros“: Belegung der zwölf G-Tasten in der aktiven Ebene."""


class MacrosPage:
    @page("macros")
    def page_macros(self, profile, macros):
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        color = PROFILE_COLOR.get(profile, self.FG)
        if self.profile_name:
            name_font = self.f_big if d.textlength(f"{self.profile_name} · {profile}", font=self.f_big) <= WIDTH - 24 else self.f_title
            suffix = f" · {profile}"
            name = self._fit(d, self.profile_name, name_font, WIDTH - 24 - d.textlength(suffix, font=name_font))
            d.text((12, 8 if name_font is self.f_big else 12), name + suffix, font=name_font, fill=color)
        else:
            d.text((12, 8), f"Makros {profile}", font=self.f_big, fill=color)
        profile_macros = macros.get(profile, {}) if isinstance(macros, dict) else {}
        col_w = (WIDTH - 24) // 2
        for i in range(12):
            gkey = f"G{i + 1}"
            col, row = divmod(i, 6)
            x = 12 + col * (col_w + 8) - (4 if col else 0)
            y = 46 + row * 28
            m = profile_macros.get(gkey)
            d.text((x, y), gkey, font=self.f_small_b, fill=self.FG)
            if isinstance(m, dict) and entry_label(m, self.settings):
                label = self._fit(d, entry_label(m, self.settings), self.f_small, col_w - 48)
                d.text((x + 42, y), label, font=self.f_small, fill=self.FG)
            else:
                d.text((x + 42, y), f"F{13 + i}", font=self.f_small, fill=self.DIM)
        return img
