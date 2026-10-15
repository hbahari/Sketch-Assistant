"""Second page: medium-sized sketch with guide lines, then pencil tips and steps."""
import cv2
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ..core.guides import draw_guides
from ..core.styles import STYLES, render
from ..data.tips import tips_markup
from ..platform_utils import export_dir
from . import theme
from .widgets import Card, Header, RoundButton, to_texture

IMG_WIDTH = 0.72   # sketch width as a fraction of the window (medium size)
IMG_MAX_H = 0.48   # ...and never taller than this fraction of the window height


class GuideScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app_ref, self.show_guides, self._shown = app, True, None
        root = BoxLayout(orientation="vertical", spacing=dp(10))
        root.add_widget(Header("Drawing guide", "Follow the lines, then the steps"))
        # style tabs: same attached/segmented look as the Portrait / Object bar on the main page
        tabs = BoxLayout(size_hint_y=None, height=dp(44), spacing=0, padding=(dp(14), 0))
        r, n = theme.radius(), len(STYLES)
        self.tabs = {}
        for i, (key, st) in enumerate(STYLES.items()):
            first, last = i == 0, i == n - 1
            b = RoundButton(text=st.short, bold=True, font_size=sp(12),
                            radii=[r if first else 0, r if last else 0, r if last else 0, r if first else 0],
                            on_release=lambda _b, k=key: self.select(k))
            self.tabs[key] = b
            tabs.add_widget(b)
        root.add_widget(tabs)
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14), padding=(dp(14), 0))
        col.bind(minimum_height=col.setter("height"))

        self.holder = AnchorLayout(size_hint_y=None)
        self.img_card = Card(size_hint=(None, None))
        self.image = Image(fit_mode="contain")
        self.img_card.add_widget(self.image); self.holder.add_widget(self.img_card)

        self.text = Label(markup=True, size_hint_y=None, halign="left", valign="top", color=theme.TEXT, padding=(dp(6), dp(6)))
        self.text.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                       texture_size=lambda w, v: setattr(w, "height", v[1] + dp(12)))
        self.tips_card = Card(size_hint_y=None, padding=dp(10))
        self.tips_card.add_widget(self.text)
        self.text.bind(height=lambda w, v: setattr(self.tips_card, "height", v + dp(20)))

        col.add_widget(self.holder); col.add_widget(self.tips_card)
        scroll = ScrollView(); scroll.add_widget(col)
        row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8), padding=(dp(14), 0, dp(14), dp(10)))
        row.height = dp(60)
        row.add_widget(RoundButton(text="Back", radii=[dp(25)] * 4, on_release=lambda *_: self.go_back()))
        self.guide_btn = RoundButton(text="Guides: ON", active=True, radii=[dp(25)] * 4, on_release=lambda *_: self.toggle())
        row.add_widget(self.guide_btn)
        row.add_widget(RoundButton(text="Save PNG", radii=[dp(25)] * 4, on_release=lambda *_: self.save()))
        root.add_widget(scroll); root.add_widget(row)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.update_tabs()
        self.text.text = tips_markup(self.app_ref.style_key)
        self.refresh()

    def update_tabs(self):
        for k, b in self.tabs.items():
            b.active = k == self.app_ref.style_key

    def select(self, key):
        """Switch style without leaving the page."""
        a = self.app_ref
        a.style_key, a.sketch = key, render(key, a.face_img)
        self.update_tabs()
        self.text.text = tips_markup(key)
        self.refresh()

    def go_back(self):
        a = self.app_ref
        self.manager.get_screen("home").apply(a.style_key, a.sketch)  # keep main page in sync
        self.manager.current = "home"

    def toggle(self):
        self.show_guides = not self.show_guides
        self.guide_btn.text, self.guide_btn.active = f"Guides: {'ON' if self.show_guides else 'OFF'}", self.show_guides
        self.refresh()

    def refresh(self):
        a = self.app_ref
        self._shown = draw_guides(a.sketch, a.style_key) if self.show_guides else a.sketch
        h, w = self._shown.shape[:2]
        self.image.texture = to_texture(self._shown)
        iw = Window.width * IMG_WIDTH
        iw = min(iw, Window.height * IMG_MAX_H * w / h)  # keep tall portraits from getting too big
        self.img_card.size = (iw + dp(16), iw * h / w + dp(16))
        self.holder.height = self.img_card.height

    def save(self):
        path = export_dir() / f"sketch_{self.app_ref.style_key}{'_guides' if self.show_guides else ''}.png"
        cv2.imwrite(str(path), self._shown)
        self.text.text = f"[b]Saved to:[/b] {path}\n\n" + tips_markup(self.app_ref.style_key)
