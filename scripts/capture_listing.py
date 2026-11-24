"""Drive the real app headlessly and screenshot every state the Play listing needs.

    PYTHONPATH=. xvfb-run -a -s "-screen 0 1080x1920x24" python scripts/capture_listing.py OUT_DIR [WIDTH HEIGHT DENSITY]

Nothing here is mocked: the photos are the test fixtures (Pexels licence, see
tests/fixtures/CREDITS.md, plus the owner's own hand photos), the sketches are the app's own
renders, and every screen is the app's own widget tree. Writes OUT_DIR/<name>.png and
OUT_DIR/shots.json, which gives, for each shot, where a tap landed (in image pixels, top-left
origin) so the video can draw a finger there.
"""
import json
import os
import shutil
import sys
from pathlib import Path

OUT = Path(sys.argv[1]).resolve()
W, H, DENSITY = (int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]) if len(sys.argv) > 4 else (1080, 1920, "2.625")
os.environ["KIVY_NO_ARGS"] = "1"
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
os.environ["KIVY_METRICS_DENSITY"] = DENSITY
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", str(W))
Config.set("graphics", "height", str(H))
Config.set("graphics", "resizable", "0")
from kivy.base import EventLoop  # noqa: E402
from kivy.clock import Clock  # noqa: E402

EventLoop.ensure_window()
from kivy.core.window import Window  # noqa: E402

from sketch_assistant.app import SketchApp  # noqa: E402
from sketch_assistant.core.modes import build_stages  # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
PHOTOS = {
    "portrait": FIX / "portraits_close" / "close_12.jpg",
    "eyes": FIX / "eyes" / "blue_macro.jpg",
    "nose": FIX / "noses" / "front_clear.jpg",
    "hands": FIX / "open_palm.jpg",
    "body": FIX / "bodies" / "two_people.jpg",
    "caricature": FIX / "portraits" / "front_pale_lowcontrast.jpg",
    "object": FIX / "objects" / "pale_on_pale.jpg",
}
ONLY = set(os.environ.get("ONLY", "").split(",")) - {""}

OUT.mkdir(parents=True, exist_ok=True)
meta = {}
app = SketchApp()
sm = app.build()
Window.add_widget(sm)
sm.transition.duration = 0
home, guide, steps = (sm.get_screen(n) for n in ("home", "guide", "steps"))


def tick(n=10):
    for _ in range(n):
        Clock.tick()
        EventLoop.idle()


def at(widget, fx=0.5, fy=0.5):
    """A point inside `widget`, in screenshot pixels (top-left origin)."""
    x, y = widget.to_window(widget.x + widget.width * fx, widget.y + widget.height * fy)
    return [round(x), round(H - y)]


def snap(name, tap=None, note=""):
    tick()
    made = Window.screenshot(name=str(OUT / f"{name}.png"))
    shutil.move(made, OUT / f"{name}.png")
    meta[name] = {"tap": tap, "screen": sm.current, "mode": app.mode, "style": app.style_key, "note": note}
    print(name, flush=True)


def go(name):
    sm.current = name
    tick()


def region_point(picker, region):
    """Screen point at the middle of a detected box on the photo card."""
    s, ox, oy = picker._scale_origin()
    cx = ox + (region.x + region.w / 2) * s
    cy = oy + (picker._size[1] - region.y - region.h / 2) * s
    x, y = picker.to_window(cx, cy)
    return [round(x), round(H - y)]


def load(mode):
    if app.mode != mode:
        home.set_mode(mode)
    home._load(str(PHOTOS[mode]))
    tick()


def walk_steps(prefix, max_steps=None):
    a = app
    a.stages = build_stages(a.mode, a.source_img, a.style_key, a.get_detail(a.style_key),
                            a.landmarks, a.crop_shape, a.crop_box)
    go("steps")
    n = len(a.stages)
    idx = list(range(n)) if max_steps is None else sorted(set(round(i * (n - 1) / (max_steps - 1)) for i in range(max_steps)))
    for k, i in enumerate(idx):
        steps.jump(i)
        snap(f"{prefix}_step{i + 1:02d}", tap=at(steps.next_btn) if k else at(guide_gen_btn()),
             note=f"{i + 1}/{n}")
    return n


def guide_gen_btn():
    # the "Generate drawing steps" button: the only active RoundButton in the guide's gen row
    root = guide.children[0]
    return root.children[1].children[0]


def wanted(mode):
    return mode in ONLY if ONLY else not mode.startswith("pro_") or os.environ.get("PRO", "1") == "1"


# ------------------------------------------------------------------ the tour
# Kivy swaps sys.stderr for its logger, so with the console log off a traceback vanishes and
# the script just exits 1. Send them to the real stderr.
sys.excepthook = lambda *e: __import__("traceback").print_exception(*e, file=sys.__stderr__)
go("home")
snap("00_home_empty", tap=at(home.upload_btn, 0.5, 0.62))    # on the + badge

if wanted("portrait"):
    load("portrait")
    regions = home.regions["portrait"]
    snap("10_portrait_found", tap=region_point(home.selector, regions[0]))
    home.on_face(0, regions[0])
    snap("11_portrait_line_art", tap=region_point(home.selector, regions[0]))
    for key in ("technical", "value_study", "crosshatch", "photoreal"):
        home.on_style(key)
        snap(f"12_portrait_{key}", tap=at(home.tiles[key]))
    home.on_style("technical")
    snap("13_portrait_technical_again", tap=at(home.tiles["technical"]))
    go("guide")
    snap("14_guide_technical", tap=at(home.guide_btn))
    for v in (0.15, 0.5, 0.9):
        guide.on_detail(v)
        s = guide.slider.slider
        snap(f"15_guide_detail_{int(v * 100):02d}", tap=at(s, v, 0.5))
    guide.on_detail(0.5)
    guide.toggle()
    snap("16_guide_guides_off", tap=at(guide.guide_btn))
    guide.toggle()
    walk_steps("17_portrait")
    go("home")

if wanted("eyes"):
    load("eyes")
    snap("20_eyes_box", tap=at(home.mode_bar.btns["eyes"]))
    go("guide")
    snap("21_eyes_guide", tap=at(home.guide_btn))
    walk_steps("22_eyes")
    go("home")

if wanted("nose"):
    load("nose")
    snap("30_nose_box", tap=at(home.mode_bar.btns["nose"]))
    go("guide")
    snap("31_nose_guide", tap=at(home.guide_btn))
    walk_steps("32_nose", max_steps=6)
    go("home")

if wanted("hands"):
    load("hands")                       # the whole photo is the hand: nothing to tap
    snap("41_hands_construct", tap=at(home.mode_bar.btns["hands"]))
    home.on_style("hand_contour")
    snap("41_hands_contour", tap=at(home.tiles["hand_contour"]))
    home.on_style("hand_construct")
    go("guide")
    snap("42_hands_guide", tap=at(home.guide_btn))
    walk_steps("43_hands", max_steps=6)
    go("home")

if wanted("body"):
    load("body")
    snap("50_posture_gesture", tap=at(home.mode_bar.btns["body"]))
    regions = home.regions["body"]
    if len(regions) > 1:                  # tap the second person too: one composition
        home.multi_selector.chosen = [0, 1]
        home.multi_selector._redraw()
        home.on_people([0, 1], regions[:2])
        snap("50_posture_gesture_both", tap=region_point(home.multi_selector, regions[1]))
    for key in ("body_mannequin", "body_contour"):
        home.on_style(key)
        snap(f"51_posture_{key}", tap=at(home.tiles[key]))
    home.on_style("body_mannequin")
    go("guide")
    snap("52_posture_guide", tap=at(home.guide_btn))
    walk_steps("53_posture", max_steps=6)
    go("home")

if wanted("caricature"):
    load("caricature")
    regions = home.regions["caricature"]
    snap("60_cartoon_found", tap=at(home.mode_bar.btns["caricature"]))
    home.on_face(0, regions[0])
    snap("61_cartoon_lines", tap=region_point(home.selector, regions[0]))
    home.on_style("car_hatch")
    snap("62_cartoon_hatch", tap=at(home.tiles["car_hatch"]))
    go("guide")
    for v in (0.0, 0.35, 0.8):
        guide.on_detail(v)
        snap(f"63_cartoon_exaggerate_{int(v * 100):02d}", tap=at(guide.slider.slider, v, 0.5))
    guide.on_detail(0.35)
    walk_steps("64_cartoon", max_steps=6)
    go("home")

if wanted("object"):
    load("object")
    snap("70_object_box", tap=at(home.mode_bar.btns["object"]))
    home.on_style("obj_contour")
    snap("71_object_contour", tap=at(home.tiles["obj_contour"]))
    home.on_style("obj_shapes")
    go("guide")
    snap("72_object_guide", tap=at(home.guide_btn))
    scroll = guide.col.parent
    tick(20)
    mg, col = guide.material_guide, guide.col
    scroll.scroll_y = max(0.0, 1 - (col.height - mg.top + 12) / max(1, col.height - scroll.height))
    tick(20)
    snap("73_object_materials", note="scrolled to the material guide")
    scroll.scroll_y = 1
    go("home")

# ------------------------------------------------------------------ the rendered styles
# Value, hatching and realism: the finished drawings, on the guide page and partway
# through their steps. Named 9x_ so the tour above is unaffected.
def pro(mode, styles, prefix, tap_first=None):
    load(mode)
    if tap_first is not None:
        regions = home.regions[mode]
        home.on_face(0, regions[0])
    for key in styles:
        home.on_style(key)
        snap(f"{prefix}_home_{key}", tap=at(home.tiles[key]))
        go("guide")
        snap(f"{prefix}_guide_{key}", tap=at(home.guide_btn))
        guide.toggle()
        snap(f"{prefix}_guide_{key}_clean", tap=at(guide.guide_btn))
        guide.toggle()
        walk_steps(f"{prefix}_{key}")
        go("home")


if wanted("pro_portrait"):
    pro("portrait", ("photoreal", "crosshatch", "value_study"), "90_portrait", tap_first=True)
if wanted("pro_eyes"):
    pro("eyes", ("eye_realistic", "eye_hatch"), "91_eyes")
if wanted("pro_hands"):
    pro("hands", ("hand_realistic", "hand_hatch"), "92_hands")
if wanted("pro_body"):
    pro("body", ("body_realistic", "body_formhatch"), "93_posture")
if wanted("pro_nose"):
    pro("nose", ("nose_realistic", "nose_hatch"), "94_nose")

go("home")
gear = home.logo_bar.gear
gear.dispatch("on_release")
tick()
snap("80_settings", tap=at(gear))

(OUT / "shots.json").write_text(json.dumps({"size": [W, H], "density": DENSITY, "shots": meta}, indent=1))
print("done", len(meta))
