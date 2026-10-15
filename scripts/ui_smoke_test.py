"""Drives the real UI headlessly (use with xvfb-run) and saves screenshots to ./shots."""
import os, sys
os.environ.setdefault("KIVY_NO_ARGS", "1")
from pathlib import Path
from kivy.config import Config
Config.set("graphics", "width", "420"); Config.set("graphics", "height", "800")
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.input.motionevent import MotionEvent
from sketch_assistant.app import SketchApp

PHOTO = sys.argv[1]; OUT = Path("shots"); OUT.mkdir(exist_ok=True)
app = SketchApp()

def shot(name):
    Window.screenshot(name=str(OUT / f"{name}.png"))

def tap(widget_x, widget_y):
    class T:  # minimal touch stand-in
        pos = (widget_x, widget_y); x, y = pos
        def __getattr__(self, k): return None
    from kivy.uix.widget import Widget
    return T()

def steps(dt):
    sm = app.root; home = sm.get_screen("home")
    home._load(PHOTO); Clock.schedule_once(lambda d: s2(home, sm), 0.3)

def s2(home, sm):
    shot("1_faces")
    f = home.selector.faces[0]; sc, ox, oy = home.selector._scale_origin()
    t = tap(ox + (f.x + f.w / 2) * sc, oy + (home.selector._size[1] - f.y - f.h / 2) * sc)
    print("tap handled:", home.selector.on_touch_down(t), "faces:", len(home.selector.faces))
    Clock.schedule_once(lambda d: s3(home, sm), 0.3)

def s3(home, sm):
    shot("2_line_art")
    for k in ("technical", "value_study", "crosshatch", "photoreal"):
        home.on_style(k); Clock.schedule_once(lambda d, k=k: shot(f"3_{k}"), 0.2)
    Clock.schedule_once(lambda d: s4(sm), 1.0)

def s4(sm):
    sm.switch_to_guide(); g = sm.get_screen("guide")
    Clock.schedule_once(lambda d: (g.select("crosshatch"), Clock.schedule_once(lambda d2: (shot("4_guide"), app.stop()), 1.0)), 1.5)

Clock.schedule_once(steps, 0.5)
app.run()
