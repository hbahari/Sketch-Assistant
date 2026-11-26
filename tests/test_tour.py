"""The first-launch tour over the main page.

Run with:  PYTHONPATH=. xvfb-run -a python -m pytest tests/test_tour.py
"""
import os
import time

import pytest

pytest.importorskip("kivy")
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "800")
from kivy.base import EventLoop  # noqa: E402
from kivy.clock import Clock  # noqa: E402


def _tick(n=6, wait=0.0):
    end = time.time() + wait
    while True:
        for _ in range(n):
            Clock.tick()
            EventLoop.idle()
        if time.time() >= end:
            break
        time.sleep(0.05)


def _tap(widget):
    widget.dispatch("on_press")
    widget.dispatch("on_release")
    _tick()


@pytest.fixture
def app(tmp_path):
    from kivy.core.window import Window
    from sketch_assistant import prefs
    from sketch_assistant.app import SketchApp
    prefs.use_file(tmp_path / "prefs.json")            # a fresh install every test
    EventLoop.ensure_window()
    a = SketchApp()
    sm = a.build()
    a.root = sm
    Window.add_widget(sm)
    sm.transition.duration = 0
    _tick()
    yield a, sm
    t = getattr(a, "tour", None)
    if t is not None and t.parent is not None:
        t.finish()
    Window.remove_widget(sm)


def test_shows_on_first_launch_only(app):
    from sketch_assistant import prefs
    a, sm = app
    a.on_start()
    _tick(wait=0.8)
    assert a.tour is not None and a.tour.parent is not None, "no tour on first launch"
    _tap(a.tour.card.skip)
    assert prefs.get("tour_done") is True
    a.on_start()                                       # the next launch
    _tick(wait=0.8)
    assert a.tour is None, "tour shown again after it was skipped"


def test_next_walks_every_step_then_ends(app):
    from kivy.core.window import Window
    from sketch_assistant import prefs
    from sketch_assistant.ui.tour import STEPS
    a, sm = app
    t = a.start_tour()
    seen = []
    for _ in range(len(STEPS)):
        seen.append(t.card.title.text)
        _tap(t.card.next)
    assert seen == [s[1] for s in STEPS]
    assert t.parent is None and t not in Window.children and a.tour is None
    assert prefs.get("tour_done") is True


def test_back_button_leaves_the_tour_not_the_app(app):
    from kivy.core.window import Window
    from sketch_assistant import prefs
    a, sm = app
    t = a.start_tour()
    _tap(t.card.next)
    # If the key falls through, Kivy's own handling asks to close the window (on Android:
    # the app). Record that, and refuse it so the test window survives either way.
    asked = []

    def refuse(*_a, **_k):
        asked.append(1)
        return True
    Window.bind(on_request_close=refuse)
    try:
        Window.dispatch("on_keyboard", 27, 0, None, [])
    finally:
        Window.unbind(on_request_close=refuse)
    assert asked == [], "back key fell through: the app would have closed"
    assert t.parent is None and prefs.get("tour_done") is True and sm.current == "home"


def test_the_page_cannot_be_used_during_the_tour(app, monkeypatch):
    """A tap that lands on a lit-up control must not reach it: the tour explains, it doesn't
    act. Tapped on 'Add a photo' while step 3 lights it up."""
    from kivy.core.window import Window
    from kivy.tests.common import UnitTestTouch
    a, sm = app
    home = sm.get_screen("home")
    hit = []
    monkeypatch.setattr(home, "choose_source", lambda: hit.append(1))
    t = a.start_tour()
    t.go(2)
    _tick()
    x, y = home.upload_btn.to_window(*home.upload_btn.center)
    touch = UnitTestTouch(x, y)
    touch.touch_down(); touch.touch_up()
    _tick()
    assert hit == [], "the tap went through to the page"


def test_every_card_is_on_screen_and_clear_of_its_spotlight(app):
    from kivy.core.window import Window
    from sketch_assistant.ui.tour import STEPS
    a, sm = app
    home = sm.get_screen("home")
    t = a.start_tour()
    for i, (name, title, _) in enumerate(STEPS):
        t.go(i)
        _tick(10)
        c = t.card
        assert 0 <= c.x and c.right <= Window.width and 0 <= c.y and c.top <= Window.height, f"{title}: card off screen"
        if name is None:
            continue
        w = home.logo_bar.gear if name == "gear" else getattr(home, name)
        wx, wy = w.to_window(w.x, w.y)
        bx, by, bw, bh = t.box
        assert bx <= wx + 1 and by <= wy + 1 and bx + bw >= wx + w.width - 1 and by + bh >= wy + w.height - 1, \
            f"{title}: spotlight misses its control"
        overlap = not (c.top <= by or c.y >= by + bh)
        assert not overlap, f"{title}: card covers the control it's about"


def test_the_spotlight_is_lit_and_the_rest_dimmed(app, tmp_path):
    """Read back from the screen. The first version cut the hole with a stencil whose test
    came out inverted: the control being explained was the dark part and the rest of the page
    stayed bright. Seen to fail with that version."""
    from PIL import Image
    from kivy.core.window import Window
    a, sm = app
    home = sm.get_screen("home")
    t = a.start_tour()
    t.opacity = 1
    t.go(2)                                            # lights up the photo card
    _tick(10)
    shot = Image.open(Window.screenshot(name=str(tmp_path / "s.png"))).convert("L")

    def grey(widget, fx, fy):
        x, y = widget.to_window(widget.x + widget.width * fx, widget.y + widget.height * fy)
        return shot.getpixel((int(x), int(Window.height - y)))
    inside = grey(home.upload_btn, 0.5, 0.85)          # white card, top part (no + badge)
    outside = grey(home.preview_card, 0.5, 0.85)       # the sketch card beside it, also white
    assert inside > 225, f"the lit control reads {inside}: it's been dimmed"
    assert outside < 140, f"the rest reads {outside}: it isn't dimmed"


def test_settings_can_show_it_again(app):
    from sketch_assistant import prefs
    a, sm = app
    prefs.set("tour_done", True)
    sm.current = "settings"
    _tick()
    _tap(sm.get_screen("settings").rows["tour"])
    _tick(wait=0.6)
    assert sm.current == "home" and a.tour is not None and a.tour.parent is not None
