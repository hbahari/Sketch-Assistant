"""Drive the real UI headlessly:  PYTHONPATH=. xvfb-run python scripts/ui_smoke_test.py photo.jpg [object]  -> ./shots"""
import os, sys
os.environ.setdefault("KIVY_NO_ARGS", "1")
from pathlib import Path
from kivy.config import Config
Config.set("graphics", "width", "420"); Config.set("graphics", "height", "800")
from kivy.clock import Clock
from kivy.core.window import Window
from sketch_assistant.app import SketchApp

PHOTO, OBJECT = sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "object"
OUT = Path("shots"); OUT.mkdir(exist_ok=True)
app = SketchApp()
shot = lambda name: Window.screenshot(name=str(OUT / f"{name}.png"))
later = lambda fn, t=0.4: Clock.schedule_once(lambda dt: fn(), t)


class T:  # minimal touch stand-in
    def __init__(self, x, y): self.pos, self.x, self.y = (x, y), x, y
    def __getattr__(self, k): return None


def start(dt):
    home = app.root.get_screen("home")
    if OBJECT:
        home.set_mode("object")
    home._load(PHOTO)
    later(lambda: after_load(home))


def after_load(home):
    if not OBJECT:
        f = home.selector.faces[0]; sc, ox, oy = home.selector._scale_origin()
        print("tap handled:", home.selector.on_touch_down(T(ox + (f.x + f.w / 2) * sc, oy + (home.selector._size[1] - f.y - f.h / 2) * sc)))
    later(lambda: (shot("1_main"), home.on_style("obj_shapes" if OBJECT else "crosshatch"), later(lambda: step3(home))))


def step3(home):
    later(lambda: (shot("2_detail_high"), app.root.switch_to_guide(), later(lambda: step4(), 1.5)))


def step4():
    g = app.root.get_screen("guide")
    g.select("obj_contour" if OBJECT else "line_art")
    g.on_detail(0.15)  # what the slider does when released
    later(lambda: (shot("3_guide"), app.stop()), 1.0)


Clock.schedule_once(start, 0.5)
app.run()
