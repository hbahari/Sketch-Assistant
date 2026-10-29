"""The drawing sequence: one stage at a time, with the pencil and technique for each."""
import cv2
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ..core.steps import contact_sheet
from ..data.steps_text import step_markup
from ..platform_utils import reveal, save_png
from . import theme
from .widgets import Card, RoundButton, TitleBar, to_texture

IMG_WIDTH, IMG_MAX_H = 0.74, 0.44


class StageThumb(ButtonBehavior, Image):
    """Small tappable preview of one stage in the filmstrip."""

    def __init__(self, stage, index, on_pick, **kw):
        super().__init__(fit_mode="contain", size_hint=(None, 1), width=dp(64), **kw)
        self.texture = to_texture(stage.image)
        self.index = index
        self.on_release = lambda *_: on_pick(index)


class StepsScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app_ref, self.i = app, 0
        root = BoxLayout(orientation="vertical", spacing=dp(8))
        self.bar = TitleBar("Drawing steps", self.go_back)
        root.add_widget(self.bar)

        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(dp(14), 0))
        col.bind(minimum_height=col.setter("height"))
        self.holder = AnchorLayout(size_hint_y=None)
        self.img_card = Card(size_hint=(None, None))
        self.image = Image(fit_mode="contain")
        self.img_card.add_widget(self.image)
        self.holder.add_widget(self.img_card)

        self.caption = Label(markup=True, size_hint_y=None, height=dp(30), color=theme.TEXT,
                             font_size=sp(16), bold=True, halign="center", valign="middle")
        self.caption.bind(size=lambda w, v: setattr(w, "text_size", v))

        self.text = Label(markup=True, size_hint_y=None, halign="left", valign="top",
                          color=theme.TEXT, padding=(dp(6), dp(6)))
        self.text.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                       texture_size=lambda w, v: setattr(w, "height", v[1] + dp(12)))
        self.text_card = Card(size_hint_y=None, padding=dp(10))
        self.text_card.add_widget(self.text)
        self.text.bind(height=lambda w, v: setattr(self.text_card, "height", v + dp(20)))

        for w in (self.holder, self.caption, self.text_card):
            col.add_widget(w)
        scroll = ScrollView()
        scroll.add_widget(col)
        root.add_widget(scroll)

        # filmstrip
        self.strip_scroll = ScrollView(size_hint_y=None, height=dp(72), do_scroll_y=False, bar_width=0)
        self.strip = BoxLayout(size_hint=(None, 1), spacing=dp(6), padding=(dp(14), dp(4)))
        self.strip.bind(minimum_width=self.strip.setter("width"))
        self.strip_scroll.add_widget(self.strip)
        root.add_widget(self.strip_scroll)

        nav = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8), padding=(dp(14), 0, dp(14), dp(10)))
        self.prev_btn = RoundButton(text="Back", radii=[dp(25)] * 4, on_release=lambda *_: self.step(-1))
        self.next_btn = RoundButton(text="Next", bold=True, active=True, radii=[dp(25)] * 4,
                                    on_release=lambda *_: self.step(1))
        nav.add_widget(self.prev_btn)
        nav.add_widget(RoundButton(text="Save sheet", radii=[dp(25)] * 4, on_release=lambda *_: self.save_sheet()))
        nav.add_widget(self.next_btn)
        root.add_widget(nav)
        self.add_widget(root)

    # ---- navigation ------------------------------------------------------------------
    def on_pre_enter(self, *_):
        self.i = 0
        self.strip.clear_widgets()
        for n, st in enumerate(self.app_ref.stages):
            self.strip.add_widget(StageThumb(st, n, self.jump))
        self.refresh()

    def jump(self, index):
        self.i = index
        self.refresh()

    def step(self, delta):
        self.i = max(0, min(len(self.app_ref.stages) - 1, self.i + delta))
        self.refresh()

    def refresh(self):
        stages = self.app_ref.stages
        st = stages[self.i]
        self.image.texture = to_texture(st.image)
        h, w = st.image.shape[:2]
        iw = min(Window.width * IMG_WIDTH, Window.height * IMG_MAX_H * w / h)
        self.img_card.size = (iw + dp(16), iw * h / w + dp(16))
        self.holder.height = self.img_card.height
        self.caption.text = f"Step {self.i + 1} of {len(stages)}  -  {st.title}"
        self.text.text = step_markup(st.key, self.app_ref.style_key)
        self.prev_btn.disabled = self.i == 0
        self.next_btn.disabled = self.i == len(stages) - 1
        for t in self.strip.children:
            t.opacity = 1 if t.index == self.i else 0.45
        self.strip_scroll.scroll_to(self.strip.children[len(stages) - 1 - self.i], padding=dp(20), animate=True)

    def go_back(self):
        self.manager.transition.direction = "right"
        self.manager.current = "guide"

    # swipe from the left edge, like the guide page
    def on_touch_down(self, touch):
        self._edge, self._x0 = touch.x < dp(28), touch.x
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if getattr(self, "_edge", False) and touch.x - self._x0 > dp(70):
            self._edge = False
            self.go_back()
            return True
        return super().on_touch_up(touch)

    def save_sheet(self):
        a = self.app_ref
        name = f"steps_{a.style_key}.png"
        try:
            path = save_png(contact_sheet(a.stages), name)
            self.caption.text = f"Saved [b]{name}[/b]"
            reveal(path)
        except Exception as e:
            self.caption.text = f"Could not save: {e}"
