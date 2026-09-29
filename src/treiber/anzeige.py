"""Renderer: setzt Grundlagen, alle Displayseiten, Menüs und Einblendungen zu einer Klasse zusammen.

render(page, profile, macros) zeichnet eine Seite samt Fußzeile; render_*() zeichnet Menüs und Einblendungen."""


class Renderer(RendererBase,
               ClockPage, ClockBase, StandardFaces, MechanicalFaces, SkyFaces, DisplayFaces, InfoFaces,
               MacrosPage, MusicPage, SlidesPage, WeatherPage, CalendarPage, HardwarePage,
               NewsPage, WarningsPage, NetworkPage, UpdatesPage,
               MenuViews, OverlayViews):
    PAGES = len(PAGE_IDS)
    MUSIC_PAGE = PAGE_IDS.index("music")
    SLIDES_PAGE = PAGE_IDS.index("slides")

    def render(self, page, profile, macros=None):
        page %= len(PAGE_IDS)
        img = PAGE_RENDERERS[PAGE_IDS[page]](self, profile, macros or {})
        visible = self.visible or list(range(len(PAGE_IDS)))
        pos = visible.index(page) if page in visible else -1
        self._footer(ImageDraw.Draw(img), profile, pos, len(visible))
        return img


assert all(f in CLOCK_RENDERERS for f in CLOCK_FACES), \
    f"Zifferblätter ohne Zeichenfunktion: {[f for f in CLOCK_FACES if f not in CLOCK_RENDERERS]}"
assert all(p in PAGE_RENDERERS for p in PAGE_IDS), \
    f"Displayseiten ohne Zeichenfunktion: {[p for p in PAGE_IDS if p not in PAGE_RENDERERS]}"
