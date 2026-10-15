from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from .ui.guide import GuideScreen
from .ui import theme
from .ui.home import HomeScreen


class Screens(ScreenManager):
    def switch_to_guide(self):
        self.current = "guide"


class SketchApp(App):
    title = "Sketch Assistant"
    photo = face_img = sketch = None  # shared state between screens
    style_key = "line_art"

    def on_start(self):
        try:  # Android runtime permissions (no-op on desktop)
            from android.permissions import request_permissions
            request_permissions(["android.permission.CAMERA", "android.permission.READ_MEDIA_IMAGES"])
        except ImportError:
            pass

    def build(self):
        Window.clearcolor = theme.BG
        sm = Screens(transition=FadeTransition(duration=0.15))
        sm.add_widget(HomeScreen(self, name="home"))
        sm.add_widget(GuideScreen(self, name="guide"))
        return sm
