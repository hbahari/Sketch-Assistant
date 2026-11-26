"""Trace mode: the drawing full-screen to trace through paper.

Run with:  PYTHONPATH=. xvfb-run -a python -m pytest tests/test_trace.py
"""
import os
import time
from pathlib import Path

import numpy as np
import pytest

from sketch_assistant.ui.trace import darken  # noqa: E402  (no window needed)

FIX = Path(__file__).resolve().parent / "fixtures"


def test_darker_lines_deepen_marks_and_leave_paper_white():
    grey = np.array([[255, 240, 200, 128, 0]], np.uint8)
    out = darken(grey)
    assert out[0, 0] == 255, "white paper must stay white"
    assert (out[0, 1:4] < grey[0, 1:4]).all(), "every mark gets darker"
    assert list(out[0]) == sorted(out[0], reverse=True), "light-to-dark order kept"
    colour = np.full((1, 1, 3), (230, 180, 120), np.uint8)       # a pale blue guide line (BGR)
    assert (darken(colour) < colour).all()


# --------------------------------------------------------------------------- with a window
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
        time.sleep(0.03)


def _tap(w):
    w.dispatch("on_press")
    w.dispatch("on_release")
    _tick()


def _drag(x, y, dx, dy):
    from kivy.tests.common import UnitTestTouch
    t = UnitTestTouch(x, y)
    t.touch_down()
    for k in range(1, 6):
        t.touch_move(x + dx * k / 5, y + dy * k / 5)
    t.touch_up()
    _tick()


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from kivy.core.window import Window
    from sketch_assistant import prefs
    from sketch_assistant.app import SketchApp
    from sketch_assistant.core.modes import build_stages
    prefs.use_file(tmp_path_factory.mktemp("prefs") / "prefs.json")
    prefs.set("tour_done", True)
    EventLoop.ensure_window()
    a = SketchApp()
    sm = a.build()
    a.root = sm
    Window.add_widget(sm)
    sm.transition.duration = 0
    _tick()
    home = sm.get_screen("home")
    home._load(str(FIX / "portraits_close" / "close_12.jpg"))
    _tick()
    home.on_face(0, home.regions["portrait"][0])
    a.stages = build_stages(a.mode, a.source_img, a.style_key, a.get_detail(a.style_key),
                            a.landmarks, a.crop_shape, a.crop_box)
    assert len(a.stages) >= 4
    yield a, sm
    Window.remove_widget(sm)


@pytest.fixture
def tracing(app, monkeypatch):
    """Steps page on step 3, then Trace. Records brightness calls."""
    from sketch_assistant.ui import trace as trace_mod
    a, sm = app
    calls = []
    monkeypatch.setattr(trace_mod, "set_brightness", lambda v: calls.append(v))
    sm.current = "steps"
    _tick()
    steps = sm.get_screen("steps")
    steps.jump(2)
    _tap(steps.trace_btn)
    tr = sm.get_screen("trace")
    yield a, sm, steps, tr, calls
    if sm.current == "trace":
        tr.go_back()
        _tick()


def test_trace_opens_on_the_step_being_viewed(tracing):
    a, sm, steps, tr, _ = tracing
    assert sm.current == "trace"
    assert tr.i == 2 and tr.title.text.startswith(f"Step 3 of {len(a.stages)}")
    _tap(tr.next_btn)
    assert tr.i == 3
    tr.show(0)
    assert tr.prev_btn.disabled and not tr.next_btn.disabled


def test_size_and_place_survive_moving_between_steps(tracing):
    """The paper hasn't moved, so the next step must land exactly where the last one was."""
    a, sm, steps, tr, _ = tracing
    tr.scatter.scale = 1.7
    tr.scatter.pos = (-40, 25)
    _tap(tr.next_btn)
    assert tr.scatter.scale == pytest.approx(1.7) and tuple(tr.scatter.pos) == pytest.approx((-40, 25))


def test_locked_ignores_touches_and_hides_the_controls(tracing):
    a, sm, steps, tr, _ = tracing
    cx, cy = tr.scatter.to_window(*tr.scatter.center)
    before = tuple(tr.scatter.pos)
    _drag(cx, cy, 60, 40)                     # unlocked: dragging moves it (the test can see moves)
    assert tuple(tr.scatter.pos) != before, "unlocked drag did nothing: can't test the lock"
    _tap(tr.lock_btn)
    assert tr.locked and tr.top_bar.opacity == 0 and tr.bottom_bar.opacity == 0 and tr.badge.opacity == 1
    moved = tuple(tr.scatter.pos)
    _drag(cx, cy, 80, -50)
    assert tuple(tr.scatter.pos) == moved, "a touch moved the locked drawing"
    i = tr.i
    nx, ny = tr.next_btn.to_window(*tr.next_btn.center)
    from kivy.tests.common import UnitTestTouch
    t = UnitTestTouch(nx, ny); t.touch_down(); t.touch_up(); _tick()
    assert tr.i == i, "a tap where Next was changed the step while locked"


def test_unlocking_needs_the_full_hold(tracing):
    a, sm, steps, tr, _ = tracing
    tr.lock()
    tr.badge.dispatch("on_press")
    _tick(wait=0.35)
    tr.badge.dispatch("on_release")
    _tick()
    assert tr.locked, "a short press unlocked it"
    tr.badge.dispatch("on_press")
    _tick(wait=1.25)
    tr.badge.dispatch("on_release")
    _tick()
    assert not tr.locked and tr.top_bar.opacity == 1


def test_bright_and_awake_while_tracing_then_put_back(tracing, monkeypatch):
    """Full brightness and screen on inside trace mode, whatever Settings says; leaving puts
    back the phone's brightness and the Settings choice (here: off)."""
    from kivy.core.window import Window
    from sketch_assistant import prefs
    a, sm, steps, tr, calls = tracing
    prefs.set("keep_screen_on", False)
    assert calls and calls[-1] == 1.0
    assert Window.allow_screensaver is False
    tr.go_back()
    _tick()
    assert calls[-1] is None, "brightness left forced after leaving trace mode"
    assert Window.allow_screensaver is True, "screen left forced on after leaving trace mode"


def test_back_returns_to_the_step_that_was_traced(tracing):
    """Done (or the back button) goes back to Steps, on the step trace mode ended on, and
    the back button doesn't close the app."""
    from kivy.core.window import Window
    a, sm, steps, tr, _ = tracing
    _tap(tr.next_btn)                         # traced on to step 4
    asked = []

    def refuse(*_a, **_k):
        asked.append(1)
        return True
    Window.bind(on_request_close=refuse)
    try:
        Window.dispatch("on_keyboard", 27, 0, None, [])
    finally:
        Window.unbind(on_request_close=refuse)
    _tick()
    assert asked == [] and sm.current == "steps"
    assert steps.i == 3, f"came back on step {steps.i + 1}, not 4"


def test_darker_lines_choice_is_remembered(tracing):
    from sketch_assistant import prefs
    a, sm, steps, tr, _ = tracing
    start = tr.darker
    _tap(tr.darker_btn)
    assert tr.darker is (not start) and prefs.get("trace_darker") is (not start)
    _tap(tr.darker_btn)


def test_guide_page_traces_the_drawing_as_shown(app):
    a, sm = app
    sm.current = "guide"
    _tick()
    g = sm.get_screen("guide")
    _tap(g.trace_btn)
    tr = sm.get_screen("trace")
    assert sm.current == "trace" and len(tr.pages) == 1 and tr.pages[0][1] is g._shown
    assert tr.next_btn.opacity == 0 and tr.prev_btn.opacity == 0
    tr.go_back()
    _tick()
    assert sm.current == "guide"
