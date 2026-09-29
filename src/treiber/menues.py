"""Auswahllisten auf dem Display: Profile, Kalender, Alben und allgemeine Listen (Sender, Textbausteine)."""


class MenuViews:
    def render_album_menu(self, albums, selected, cursor, recursive, color, status=None):
        """Albenauswahl der Bilderseite: albums = [{id, name, level, total, parent}]."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), "Alben", font=self.f_big, fill=self.FG)
        if status or not albums:
            d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
            self._center(d, HEIGHT - 20, "BACK zurück", self.f_tiny, self.DIM)
            lines = self._wrap(d, status or "Keine Alben gefunden", self.f_small, WIDTH - 32, 5)
            for i, line in enumerate(lines):
                self._center(d, 90 + i * 20, line, self.f_small, self.DIM)
            return img
        by_id = {a["id"]: a for a in albums}

        def implied(a):                    # über ein gewähltes Oberalbum enthalten
            p, seen = a.get("parent"), set()
            while recursive and p in by_id and p not in seen:
                if p in selected:
                    return True
                seen.add(p)
                p = by_id[p].get("parent")
            return False
        cnt = f"{sum(1 for a in albums if a['id'] in selected)} gewählt"
        d.text((WIDTH - 12 - d.textlength(cnt, font=self.f_small), 14), cnt, font=self.f_small, fill=self.DIM)
        row_h, top, rows = 24, 44, 7
        first = max(0, min(cursor - rows // 2, len(albums) - rows))
        for n, a in enumerate(albums[first:first + rows]):
            i = first + n
            y = top + n * row_h
            on, inh = a["id"] in selected, implied(a)
            if i == cursor:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + row_h - 4], radius=5, fill=(40, 48, 66))
            x = 14 + min(int(a.get("level") or 0), 3) * 12
            box = [x, y + 2, x + 16, y + 18]
            if on:
                d.rounded_rectangle(box, radius=3, fill=color)
                d.line([(x + 4, y + 10), (x + 7, y + 14), (x + 13, y + 6)], fill=self.BG, width=2)
            elif inh:
                d.rounded_rectangle(box, radius=3, outline=color, width=2)
                d.rectangle([x + 5, y + 7, x + 11, y + 13], fill=color)
            else:
                d.rounded_rectangle(box, radius=3, outline=(110, 116, 130), width=2)
            num = str(a.get("total") or 0)
            nw = d.textlength(num, font=self.f_tiny)
            d.text((WIDTH - 16 - nw, y + 3), num, font=self.f_tiny, fill=self.DIM)
            d.text((x + 26, y), self._fit(d, a["name"], self.f_small, WIDTH - x - 50 - nw), font=self.f_small,
                   fill=self.FG if (on or inh) else (150, 156, 170))
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ wählen · OK ein/aus · BACK fertig", self.f_tiny, self.DIM)
        self._scroll_marks(d, first > 0, first + rows < len(albums))
        return img

    def render_list_menu(self, title, items, cursor, hint, info="", color=None):
        """Allgemeine Auswahlliste: items = [{"label", "sub"?, "mark"?, "color"?, "dim"?}]."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), title, font=self.f_big, fill=self.FG)
        if info:
            d.text((WIDTH - 12 - d.textlength(info, font=self.f_small), 14), info, font=self.f_small, fill=self.DIM)
        if not items:
            self._center(d, 100, "Keine Einträge", self.f_mid, self.DIM)
        row_h, top, rows = 24, 44, 7
        first = max(0, min(cursor - rows // 2, len(items) - rows))
        for n, it in enumerate(items[first:first + rows]):
            i = first + n
            y = top + n * row_h
            if i == cursor:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + row_h - 4], radius=5, fill=(40, 48, 66))
            mark = it.get("mark") or ""
            mcol = tuple(it.get("color") or color or self.FG)
            if mark:
                d.text((14, y), mark, font=self.f_small_b, fill=mcol)
            sub = it.get("sub") or ""
            sw = d.textlength(sub, font=self.f_tiny) if sub else 0
            if sub:
                d.text((WIDTH - 16 - sw, y + 3), sub, font=self.f_tiny, fill=self.DIM)
            fill = (110, 116, 130) if it.get("dim") else (self.FG if i == cursor else (200, 205, 215))
            d.text((34, y), self._fit(d, it["label"], self.f_small, WIDTH - 50 - sw), font=self.f_small, fill=fill)
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, hint, self.f_tiny, self.DIM)
        self._scroll_marks(d, first > 0, first + rows < len(items))
        return img

    def render_calendar_menu(self, cals, hidden, cursor):
        """Kalenderauswahl der Terminseite: cals = [{key, name, color}]."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), "Kalender", font=self.f_big, fill=self.FG)
        on = sum(1 for c in cals if c["key"] not in hidden)
        cnt = f"{on} von {len(cals)} sichtbar"
        d.text((WIDTH - 12 - d.textlength(cnt, font=self.f_small), 14), cnt, font=self.f_small, fill=self.DIM)
        row_h, top, rows = 24, 44, 7
        first = max(0, min(cursor - rows // 2, len(cals) - rows))
        for n, c in enumerate(cals[first:first + rows]):
            i = first + n
            y = top + n * row_h
            visible = c["key"] not in hidden
            color = tuple(c.get("color") or self.CAL_COLORS[i % len(self.CAL_COLORS)])
            if i == cursor:
                d.rounded_rectangle([6, y - 2, WIDTH - 6, y + row_h - 4], radius=5, fill=(40, 48, 66))
            box = [16, y + 2, 32, y + 18]
            if visible:
                d.rounded_rectangle(box, radius=3, fill=color)
                d.line([(20, y + 10), (23, y + 14), (29, y + 6)], fill=self.BG, width=2)
            else:
                d.rounded_rectangle(box, radius=3, outline=color, width=2)
            d.text((42, y), self._fit(d, c["name"], self.f_small, WIDTH - 56), font=self.f_small,
                   fill=(self.FG if i == cursor else (200, 205, 215)) if visible else (110, 116, 130))
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ wählen · OK ein/aus · BACK fertig", self.f_tiny, self.DIM)
        self._scroll_marks(d, first > 0, first + rows < len(cals))
        return img

    def render_profile_menu(self, profiles, cursor, active, colors_of):
        """Profilauswahl: profiles = Liste der Namen, colors_of(i) = Farben des Profils."""
        img = Image.new("RGB", (WIDTH, HEIGHT), self.BG)
        d = ImageDraw.Draw(img)
        d.text((12, 6), "Profil wählen", font=self.f_big, fill=self.FG)
        n = len(profiles)
        row_h = 17 if n > 8 else 21
        top = 42
        for i, name in enumerate(profiles):
            y = top + i * row_h
            if i == cursor:
                d.rounded_rectangle([6, y - 1, WIDTH - 6, y + row_h - 3], radius=5, fill=(40, 48, 66))
            cols = colors_of(i)
            for j, layer in enumerate(LAYERS):
                d.rectangle([14 + j * 7, y + 3, 19 + j * 7, y + row_h - 7], fill=tuple(cols[layer]))
            num = f"{i + 1}"
            d.text((62 - d.textlength(num, font=self.f_small_b), y), num, font=self.f_small_b, fill=self.DIM)
            d.text((72, y), self._fit(d, name, self.f_small, WIDTH - 112), font=self.f_small,
                   fill=self.FG if i == cursor else (200, 205, 215))
            if i == active:
                d.text((WIDTH - 30, y), "✓", font=self.f_small_b, fill=(80, 220, 130))
        d.rectangle([0, HEIGHT - 22, WIDTH, HEIGHT], fill=(20, 24, 34))
        self._center(d, HEIGHT - 20, "▲▼ wählen · OK aktivieren · BACK zurück", self.f_tiny, self.DIM)
        return img
