from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from .core.modes import DEFAULT as DEFAULT_MODE
from .core.styles import ALL
from .ui import theme
from .ui.guide import GuideScreen
from .ui.home import HomeScreen
from .ui.settings import SettingsScreen
from .ui.steps import StepsScreen
from .ui.textpage import TextScreen


class Screens(ScreenManager):
    def switch_to_guide(self):
        self.transition.direction = "left"   # push the guide page in from the right
        self.current = "guide"

    def go(self, name):
        self.transition.direction = "left"
        self.current = name

    def back_to(self, name):
        self.transition.direction = "right"
        self.current = name

    def show_text(self, title, text):
        self.get_screen("text").show(title, text)
        self.go("text")


class SketchApp(App):
    title = "Sketch Assistant"
    icon = str(__import__("pathlib").Path(__file__).resolve().parent / "assets" / "brand" / "icon.png")
    mode = DEFAULT_MODE                       # a key of core.modes.MODES
    photo = source_img = sketch = style_key = crop_shape = crop_box = None
    stages = ()   # shared state between screens
    landmarks = ()

    def __init__(self, **kw):
        super().__init__(**kw)
        self.detail = {}                      # style key -> detail slider value

    def get_detail(self, key):
        return self.detail.get(key, ALL[key].default)

    def build(self):
        Window.clearcolor = theme.BG
        sm = Screens(transition=SlideTransition(duration=0.28, direction="left"))
        sm.add_widget(HomeScreen(self, name="home"))
        sm.add_widget(GuideScreen(self, name="guide"))
        sm.add_widget(StepsScreen(self, name="steps"))
        sm.add_widget(SettingsScreen(self, on_back=lambda: sm.back_to("home"), show_text=sm.show_text,
                                     name="settings"))
        sm.add_widget(TextScreen(on_back=lambda: sm.back_to("settings"), name="text"))
        Window.bind(on_keyboard=lambda w, key, *a: self._back_key(sm, key))
        return sm

    def on_start(self):
        from . import prefs
        from .platform_utils import keep_screen_on
        if prefs.get("keep_screen_on"):              # the Settings switch, remembered
            keep_screen_on(True)

    @staticmethod
    def _back_key(sm, key):
        """Android back button / Esc: leave the current page instead of quitting the app."""
        if key == 27 and sm.current in ("guide", "steps", "settings", "text"):
            sm.get_screen(sm.current).go_back()
            return True
        return False
