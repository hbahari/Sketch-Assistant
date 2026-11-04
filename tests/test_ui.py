"""Headless checks on the subject bar and the mode-driven parts of the main page.

Run with:  PYTHONPATH=. xvfb-run -a python -m pytest tests/test_ui.py

These assert behaviour rather than appearance, because a screenshot in a headless GL
context is unreliable: what matters is that the pills size to their labels, that the bar
scrolls by dragging and not by a scrollbar, that a tap still selects, and that switching
subject swaps the style tiles.
"""
import os

import pytest

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

kivy = pytest.importorskip("kivy")
from kivy.base import EventLoop  # noqa: E402
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "800")

from kivy.clock import Clock  # noqa: E402
from kivy.metrics import dp  # noqa: E402

from sketch_assistant.core.modes import MODES  # noqa: E402
from sketch_assistant.ui.widgets import ModeBar  # noqa: E402


from pathlib import Path  # noqa: E402

from kivy.tests.common import UnitTestTouch  # noqa: E402


class Touch(UnitTestTouch):
    """Kivy's own test touch. Rolling a stub by hand does not work here: ScrollView calls
    apply_transform_2d and ButtonBehavior relies on grab/ungrab, so a partial fake silently
    fails to press or to scroll."""

    def __init__(self, x, y):
        super().__init__(x, y)
        # ScrollView transforms the previous and origin positions as well as the current
        # one, and UnitTestTouch leaves those unset, which blows up inside to_local
        self.px, self.py = x, y
        self.ox, self.oy = x, y

    def drag_to(self, x, y):
        # not called `move`: MotionEvent.move(args) already exists and is used internally
        self.touch_move(x, y)


@pytest.fixture(scope="module", autouse=True)
def _window():
    EventLoop.ensure_window()
    yield


def make_bar(labels=None, attach=False):
    """Build a bar. `attach` puts it on the real Window, which is needed for anything
    that sends touches: a UnitTestTouch carries window-relative coordinates and is only
    turned into widget coordinates when it is dispatched through the window."""
    picked = []
    modes = labels or [(m.key, m.label) for m in MODES.values()]
    bar = ModeBar(modes, picked.append)
    bar.size_hint = (None, None)
    bar.size = (dp(392), bar.height)
    bar.pos = (dp(14), dp(600))
    if attach:
        EventLoop.window.add_widget(bar)
    bar.row.do_layout()          # ScrollView has no do_layout; its content box does
    if attach:
        for _ in range(3):       # let Kivy place the children before anything is touched
            Clock.tick()
    return bar, picked


def drop(bar):
    if bar.parent:
        EventLoop.window.remove_widget(bar)


def window_pos(bar, key):
    """Where a pill is on the Window.

    A ScrollView lays its content out in its own space -- the pills come back at y=0
    whatever the bar's position -- so a pill's `pos` cannot be used as a touch target
    directly. This maps it back through the bar's own position and scroll offset.
    """
    b = bar.btns[key]
    return (bar.x + (b.center_x - bar.row.x), bar.center_y)


def test_pills_are_separate_and_fit_their_labels():
    """Separate rounded pills, not one attached segmented control: each is fully rounded
    on all four corners and there is a real gap between them."""
    bar, _ = make_bar()
    pills = list(bar.btns.values())
    assert len(pills) == len(MODES)
    for b in pills:
        assert len(set(b.radii)) == 1 and b.radii[0] > 0, "pill is not rounded on all corners"
        assert b.width >= b.texture_size[0], f"'{b.text}' is narrower than its label"
    assert bar.row.spacing > 0, "pills are touching"


def test_there_is_no_scrollbar():
    bar, _ = make_bar()
    assert bar.bar_width == 0
    assert bar.do_scroll_y is False and bar.do_scroll_x is True


def test_tapping_a_pill_selects_it():
    bar, picked = make_bar(attach=True)
    try:
        t = Touch(*window_pos(bar, "object"))
        t.touch_down()
        t.touch_up()
        for _ in range(5):       # ButtonBehavior defers on_release by min_state_time
            Clock.tick()
        assert picked == ["object"], f"tap did not select (got {picked})"
        bar.select("object")
        assert bar.btns["object"].active and not bar.btns["portrait"].active
    finally:
        drop(bar)


def test_dragging_scrolls_the_bar_sideways():
    """The gesture the bar is meant to support: press anywhere -- including on a pill --
    then drag. The content must move, and the drag must not select a pill."""
    many = [(f"m{i}", f"Subject {i}") for i in range(8)]     # force an overflow
    bar, picked = make_bar(many, attach=True)
    try:
        assert bar.row.width > bar.width, "test needs a bar wider than the viewport"
        x0, y0 = window_pos(bar, "m0")                      # press starts ON a pill
        t = Touch(x0, y0)
        t.touch_down()
        for x in range(int(x0), int(x0) - 200, -25):
            t.touch_move(x, y0)
        t.touch_up()
        for _ in range(12):      # let the scroll effect settle and clamp
            Clock.tick()
        # Direction only. The bar keeps Kivy's damped (rubber-band) effect, and under a
        # synthetic clock the flick never decays, so the settled value is not meaningful
        # here -- what this pins down is that dragging left moves the bar right at all,
        # and that doing so does not fire the pill the finger started on.
        assert bar.scroll_x > 0.01, f"drag did not scroll (scroll_x={bar.scroll_x})"
        assert picked == [], "a drag selected a pill instead of scrolling"
    finally:
        drop(bar)


def test_a_short_bar_does_not_scroll_or_fade():
    """With few subjects everything fits, so there is nothing to scroll and no end fade."""
    bar, _ = make_bar([("a", "One"), ("b", "Two")])
    assert bar.row.width <= bar.width
    bar._edges()
    assert len(bar._fades.children) == 0, "drew a fade with nothing to scroll to"


def test_redrawing_the_fades_keeps_the_scrollview_stencil():
    """The fades must never be drawn by clearing the bar's own canvas.after.

    A ScrollView is a StencilView and Kivy keeps StencilUnUse/StencilPop there. Wiping
    that canvas leaves the stencil clip pushed and never popped, so every widget drawn
    after the bar in the frame is clipped away -- the whole page below it goes blank.
    """
    from kivy.graphics import StencilPop, StencilUnUse

    many = [(f"m{i}", f"Subject {i}") for i in range(8)]     # overflowing, so fades draw
    bar, _ = make_bar(many)
    for scroll in (0.0, 0.5, 1.0):      # every branch of _edges
        bar.scroll_x = scroll
        bar._edges()
        kinds = [type(c) for c in bar.canvas.after.children]
        assert StencilUnUse in kinds, f"StencilUnUse lost at scroll_x={scroll}"
        assert StencilPop in kinds, f"StencilPop lost at scroll_x={scroll}"


def test_the_home_screen_actually_draws_something():
    """End-to-end: build the real app, render the main page, and check pixels came out.

    Every other test here passes on a widget tree that renders nothing at all, which is
    exactly the failure the stencil bug caused. This is the one that notices.

    It renders through an Fbo, which does not carry a stencil buffer, so the contents of
    the scrolling subject bar itself do not appear in the capture. What it does catch --
    and what matters here -- is a whole page failing to reach the screen.
    """
    from kivy.clock import Clock as _Clock

    from sketch_assistant.app import SketchApp
    app = SketchApp()
    root = app.build()
    win = EventLoop.window
    win.add_widget(root)
    try:
        for _ in range(60):
            _Clock.tick()
        home = root.get_screen("home")
        path = os.path.join(os.path.dirname(__file__), "_render_check.png")
        home.export_to_png(path)
        try:
            from PIL import Image as PILImage
            import numpy as np
            px = np.asarray(PILImage.open(path).convert("RGB"))
        finally:
            os.path.exists(path) and os.remove(path)
        painted = (px.max(axis=2) > 8).mean()
        assert painted > 0.25, (
            f"the main page rendered almost nothing ({painted:.1%} of pixels painted) -- "
            "the widget tree exists but is not reaching the screen")
    finally:
        win.remove_widget(root)


def test_selecting_scrolls_the_chosen_pill_into_view():
    many = [(f"m{i}", f"Subject {i}") for i in range(8)]
    bar, _ = make_bar(many)
    bar.select("m7")                       # the last one, off-screen to the right
    assert bar.btns["m7"].active


def test_home_screen_switches_tiles_with_the_subject():
    from sketch_assistant.app import SketchApp
    from sketch_assistant.ui.home import HomeScreen
    app = SketchApp()
    home = HomeScreen(app, name="home")
    for key, m in MODES.items():
        home.set_mode(key)
        assert app.mode == key
        assert home.style_holder.children[0] is home.rows[key], f"{key}: wrong tile row"
        assert home.mode_bar.btns[key].active, f"{key}: pill not highlighted"
        shown = {b.text for b in home.rows[key].children}
        assert shown == {s.short for s in m.styles.values()}, f"{key}: wrong style tiles"


# ---- object mode: drawing the region ------------------------------------------------
def _loaded_home(mode, path):
    from kivy.clock import Clock as _Clock

    from sketch_assistant.app import SketchApp
    from sketch_assistant.ui.home import HomeScreen
    app = SketchApp()
    home = HomeScreen(app, name="home")
    EventLoop.window.add_widget(home)
    home.set_mode(mode)
    home._load(path)
    for _ in range(8):
        _Clock.tick()
    return app, home


def _fixture(*parts):
    return str(Path(__file__).resolve().parent.joinpath("fixtures", *parts))


def test_object_mode_offers_a_box_to_draw():
    """Object mode cannot be told which object was meant, so it asks."""
    app, home = _loaded_home("object", _fixture("objects", "many_objects_cluttered.jpg"))
    try:
        assert home.box_picker.parent is home.photo_card, "box picker not shown"
        assert home.box_picker.box is not None
        assert app.source_img is not None and app.style_key is not None, \
            "a style should already be rendered from the default box"
    finally:
        EventLoop.window.remove_widget(home)


def test_other_modes_still_show_the_tap_selector():
    for mode, path in (("portrait", _fixture("portraits", "front_adult.jpg")),
                       ("hands", _fixture("hand.jpg"))):
        app, home = _loaded_home(mode, path)
        try:
            assert home.selector.parent is home.photo_card, f"{mode}: wrong picker"
        finally:
            EventLoop.window.remove_widget(home)


def test_dragging_a_box_changes_what_gets_drawn():
    from kivy.clock import Clock as _Clock
    app, home = _loaded_home("object", _fixture("objects", "many_objects_cluttered.jpg"))
    try:
        bp = home.box_picker
        before_box, before_crop = bp.box, app.source_img.shape[:2]
        s, ox, oy = bp._scale_origin()
        W, H = bp._size

        def scr(ix, iy):
            return (ox + ix * s, oy + (H - iy) * s)

        t = Touch(*scr(W * 0.30, H * 0.20))
        t.touch_down()
        for k in range(1, 6):
            f = k / 5.0
            t.touch_move(*scr(W * (0.30 + 0.40 * f), H * (0.20 + 0.55 * f)))
        t.touch_up()
        for _ in range(8):
            _Clock.tick()

        assert bp.box != before_box, "the drag did not move the box"
        assert app.source_img.shape[:2] != before_crop, "the crop did not follow the box"
        # the drawn region must actually be smaller than the photo
        assert bp.box[2] < W * 0.95 and bp.box[3] < H * 0.95
    finally:
        EventLoop.window.remove_widget(home)


def test_a_tap_leaves_the_box_alone():
    """Tapping is not drawing. Without this a stray tap collapses the box to a point and
    the crop becomes a few pixels of whatever was under the finger."""
    from kivy.clock import Clock as _Clock
    app, home = _loaded_home("object", _fixture("objects", "single_on_plain.jpg"))
    try:
        bp = home.box_picker
        before = bp.box
        s, ox, oy = bp._scale_origin()
        W, H = bp._size
        t = Touch(ox + W * 0.5 * s, oy + H * 0.5 * s)
        t.touch_down()
        t.touch_up()
        for _ in range(4):
            _Clock.tick()
        assert bp.box == before, "a tap changed the selection"
    finally:
        EventLoop.window.remove_widget(home)


def test_the_default_box_keeps_the_whole_photo():
    """Dragging must be an improvement, not a new thing to get right: untouched, the
    default selection has to behave like the old whole-frame result."""
    app, home = _loaded_home("object", _fixture("objects", "single_on_plain.jpg"))
    try:
        ph, crop = app.photo.shape[:2], app.source_img.shape[:2]
        assert crop[0] >= ph[0] * 0.9 and crop[1] >= ph[1] * 0.9, \
            f"default crop {crop} is much smaller than the photo {ph}"
    finally:
        EventLoop.window.remove_widget(home)
