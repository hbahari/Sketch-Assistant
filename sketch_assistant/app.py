from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from .core.styles import ALL
from .ui import theme
from .ui.guide import GuideScreen
from .ui.home import HomeScreen
from .ui.steps import StepsScreen


class Screens(ScreenManager):
    def switch_to_guide(self):
        self.transition.direction = "left"   # push the guide page in from the right
        self.current = "guide"


class SketchApp(App):
    title = "Sketch Assistant"
    icon = str(__import__("pathlib").Path(__file__).resolve().parent / "assets" / "brand" / "icon.png")
    mode = "portrait"                         # "portrait" | "object"
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
        Window.bind(on_keyboard=lambda w, key, *a: self._back_key(sm, key))
        return sm

    @staticmethod
    def _back_key(sm, key):
        """Android back button / Esc: leave the guide page instead of quitting the app."""
        if key == 27 and sm.current in ("guide", "steps"):
            sm.get_screen(sm.current).go_back()
            return True
        return False
