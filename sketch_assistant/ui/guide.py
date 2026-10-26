"""Second page: medium-sized sketch with guide lines, then pencil tips and steps."""
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ..core.guides import draw_guides
from ..core.styles import render, styles_for
from ..data.tips import tips_markup
from ..platform_utils import reveal, save_png
from . import theme
from kivy.uix.popup import Popup
from .materials import MaterialGuide
from .widgets import Card, DetailSlider, RoundButton, TitleBar, segmented, to_texture

IMG_WIDTH = 0.72   # sketch width as a fraction of the window (medium size)
IMG_MAX_H = 0.48   # ...and never taller than this fraction of the window height


class GuideScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app_ref, self.show_guides, self._shown = app, True, None
        root = BoxLayout(orientation="vertical", spacing=dp(10))
        root.add_widget(TitleBar("Drawing guide", self.go_back))
        self.tabs_holder = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(14), 0))  # style tabs, rebuilt per mode
        root.add_widget(self.tabs_holder)
        self.slider = DetailSlider(self.on_detail)
        sl = BoxLayout(size_hint_y=None, height=dp(34), padding=(dp(14), 0)); sl.add_widget(self.slider)
        root.add_widget(sl)
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

        self.col, self.material_guide = col, MaterialGuide()
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

    # swipe right from the left edge to go back (like most social apps)
    def on_touch_down(self, touch):
        self._edge = touch.x < dp(28)
        self._x0 = touch.x
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if getattr(self, "_edge", False) and touch.x - self._x0 > dp(70):
            self._edge = False
            self.go_back()
            return True
        return super().on_touch_up(touch)

    def on_pre_enter(self, *_):
        a = self.app_ref
        self.tabs_holder.clear_widgets()
        bar, self.tabs = segmented(styles_for(a.mode), self.select)
        self.tabs_holder.add_widget(bar)
        if a.mode == "object" and self.material_guide.parent is None:
            self.col.add_widget(self.material_guide)
        elif a.mode != "object" and self.material_guide.parent is not None:
            self.col.remove_widget(self.material_guide)
        self.update_all()

    def update_all(self):
        a = self.app_ref
        for k, b in self.tabs.items():
            b.active = k == a.style_key
        self.slider.set_value(a.get_detail(a.style_key))
        self.text.text = tips_markup(a.style_key)
        self.refresh()

    def select(self, key):
        """Switch style without leaving the page."""
        a = self.app_ref
        a.style_key, a.sketch = key, render(key, a.source_img, a.get_detail(key))
        self.update_all()

    def on_detail(self, value):
        self.app_ref.detail[self.app_ref.style_key] = value
        self.select(self.app_ref.style_key)

    def go_back(self):
        a = self.app_ref
        self.manager.get_screen("home").apply(a.style_key, a.sketch)  # keep main page in sync
        self.manager.transition.direction = "right"
        self.manager.current = "home"

    def toggle(self):
        self.show_guides = not self.show_guides
        self.guide_btn.text, self.guide_btn.active = f"Guides: {'ON' if self.show_guides else 'OFF'}", self.show_guides
        self.refresh()

    def refresh(self):
        a = self.app_ref
        self._shown = draw_guides(a.sketch, a.style_key, a.landmarks, a.crop_shape) if self.show_guides else a.sketch
        h, w = self._shown.shape[:2]
        self.image.texture = to_texture(self._shown)
        iw = Window.width * IMG_WIDTH
        iw = min(iw, Window.height * IMG_MAX_H * w / h)  # keep tall portraits from getting too big
        self.img_card.size = (iw + dp(16), iw * h / w + dp(16))
        self.holder.height = self.img_card.height

    def save(self):
        name = f"sketch_{self.app_ref.style_key}{'_guides' if self.show_guides else ''}.png"
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        try:
            path = save_png(self._shown, name)
            msg, ok = f"Saved as [b]{name}[/b]\nin: {path.parent}", True
        except Exception as e:  # show the real reason instead of failing silently
            msg, ok = f"Could not save the image:\n{e}", False
        lab = Label(text=msg, markup=True, color=theme.TEXT, halign="center", valign="middle", font_size=sp(13))
        lab.bind(size=lambda w, v: setattr(w, "text_size", v))
        box.add_widget(lab)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        pop = Popup(title="Saved" if ok else "Save failed", content=box, size_hint=(0.9, 0.38), separator_height=0,
                    background="", background_color=theme.BG, title_color=theme.TEXT)
        if ok:
            row.add_widget(RoundButton(text="Open folder", on_release=lambda *_: reveal(path)))
        row.add_widget(RoundButton(text="OK", active=True, on_release=lambda *_: pop.dismiss()))
        box.add_widget(row)
        pop.open()
