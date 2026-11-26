"""Trace mode: the drawing full-screen on plain white, bright enough to show through paper.

Opened from the Steps page (any step, and you can move between steps here) or from the guide
page (the drawing as shown there). Before locking you can pinch to size the drawing to your
paper and drag it into place. Locking hides every control and ignores every touch, so the
paper and pencil can rest on the screen; holding the lock badge unlocks it. While trace mode
is open the screen stays on at full brightness. Leaving puts both back as they were.
"""
import math

import numpy as np
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from .. import prefs
from ..platform_utils import keep_screen_on, set_brightness
from . import theme
from .widgets import RoundButton, to_texture

HOLD = 1.0          # seconds to hold the badge to unlock
DARKEN = 1.9        # how much "Darker lines" deepens every mark (white stays white)


def darken(img):
    """Deepen every mark so it shows through paper; white stays white. Works on grey and colour."""
    ink = 255.0 - img.astype(np.float32)
    return (255.0 - np.clip(ink * DARKEN, 0, 255)).astype(np.uint8)


class LockBadge(ButtonBehavior, Widget):
    """The one thing that answers a touch while locked: hold it for HOLD seconds to unlock.
    A ring fills as you hold; letting go early resets it."""

    def __init__(self, on_unlock, **kw):
        super().__init__(size_hint=(None, None), size=(dp(64), dp(64)), **kw)
        self.on_unlock, self.progress, self._ev, self._t = on_unlock, 0.0, None, 0.0
        self.bind(pos=self._draw, size=self._draw)

    def on_press(self):
        self._t = 0.0
        self._ev = Clock.schedule_interval(self._tick, 1 / 30)

    def on_release(self):
        self._stop()

    def _tick(self, dt):
        self._t += dt
        self.progress = min(1.0, self._t / HOLD)
        self._draw()
        if self.progress >= 1.0:
            self._stop()
            self.on_unlock()

    def _stop(self):
        if self._ev is not None:
            self._ev.cancel()
            self._ev = None
        self.progress = 0.0
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        r = self.width / 2
        with self.canvas:
            Color(0.1, 0.1, 0.12, 0.55)
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
            if self.progress > 0:
                Color(*theme.AMBER)
                Line(circle=(cx, cy, r - dp(3), 0, 360 * self.progress), width=dp(3))
            Color(1, 1, 1, 0.95)                                 # a padlock
            bw, bh = dp(20), dp(15)
            RoundedRectangle(pos=(cx - bw / 2, cy - bh / 2 - dp(4)), size=(bw, bh), radius=[dp(3)])
            Line(ellipse=(cx - dp(7), cy - dp(1), dp(14), dp(18), -90, 90), width=dp(2))


class TraceScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app_ref = app
        self.pages, self.i, self.locked, self.came_from = [], 0, False, "steps"
        self.darker = bool(prefs.get("trace_darker"))
        root = FloatLayout()
        with root.canvas.before:
            Color(1, 1, 1, 1)                                    # paper-white, nothing else
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(self._bg, "pos", v), size=lambda w, v: setattr(self._bg, "size", v))

        self.scatter = Scatter(do_rotation=False, scale_min=0.3, scale_max=6, auto_bring_to_front=False,
                               size_hint=(None, None))
        self.image = Image(fit_mode="fill", size_hint=(None, None))
        self.scatter.add_widget(self.image)
        root.add_widget(self.scatter)

        # the controls, all hidden while locked
        self.top_bar = BoxLayout(size_hint=(1, None), height=dp(64), padding=(dp(12), dp(10)), spacing=dp(8),
                             pos_hint={"top": 1})
        self.done_btn = RoundButton(text="Done", bold=True, size_hint_x=None, width=dp(84), radii=[dp(22)] * 4,
                                    on_release=lambda *_: self.go_back())
        self.title = Label(color=theme.TEXT, bold=True, font_size=sp(14), halign="center", valign="middle",
                           shorten=True, shorten_from="right")
        self.title.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.darker_btn = RoundButton(text="Darker lines", font_size=sp(13), size_hint_x=None, width=dp(118),
                                      radii=[dp(22)] * 4, active=self.darker, on_release=lambda *_: self.toggle_darker())
        for w in (self.done_btn, self.title, self.darker_btn):
            self.top_bar.add_widget(w)
        self.hint = Label(text="Pinch to size it to your paper, drag to place it, then lock.",
                          color=theme.MUTED, font_size=sp(13), size_hint=(1, None), height=dp(28),
                          pos_hint={"x": 0}, y=dp(70), halign="center")
        self.bottom_bar = BoxLayout(size_hint=(1, None), height=dp(66), padding=(dp(14), dp(4), dp(14), dp(12)),
                                spacing=dp(8), pos_hint={"x": 0, "y": 0})
        self.prev_btn = RoundButton(text="Back", radii=[dp(25)] * 4, on_release=lambda *_: self.show(self.i - 1))
        self.lock_btn = RoundButton(text="Lock", bold=True, fill=theme.AMBER, radii=[dp(25)] * 4,
                                    on_release=lambda *_: self.lock())
        self.next_btn = RoundButton(text="Next", bold=True, active=True, radii=[dp(25)] * 4,
                                    on_release=lambda *_: self.show(self.i + 1))
        for w in (self.prev_btn, self.lock_btn, self.next_btn):
            self.bottom_bar.add_widget(w)
        self.badge = LockBadge(self.unlock, pos_hint={"right": 0.97, "y": 0.02})
        self.badge.opacity = 0
        self.badge.disabled = True
        for w in (self.top_bar, self.bottom_bar, self.hint, self.badge):
            root.add_widget(w)
        self.root_layout = root
        self.add_widget(root)

    # ---------------------------------------------------------------- opening
    def open(self, pages, index=0, came_from="steps"):
        """pages: [(title, image)]. Shows pages[index], fitted to the screen."""
        self.pages, self.came_from = list(pages), came_from
        self.unlock()
        self.show(index, refit=True)

    def on_enter(self, *_):
        keep_screen_on(True)                     # whatever the Settings switch says
        set_brightness(1.0)

    def on_leave(self, *_):
        set_brightness(None)                     # back to the phone's own brightness
        keep_screen_on(bool(prefs.get("keep_screen_on")))
        if self.locked:
            self.unlock()

    def go_back(self):
        if self.came_from == "steps":
            self.manager.get_screen("steps").resume_at = self.i
        self.manager.transition.direction = "right"
        self.manager.current = self.came_from

    # ---------------------------------------------------------------- pages
    def show(self, i, refit=False):
        if not self.pages:
            return
        self.i = max(0, min(len(self.pages) - 1, i))
        title, img = self.pages[self.i]
        self.image.texture = to_texture(darken(img) if self.darker else img)
        n = len(self.pages)
        self.title.text = f"Step {self.i + 1} of {n}  -  {title}" if n > 1 else title
        self.prev_btn.disabled = self.i == 0
        self.next_btn.disabled = self.i == n - 1
        self.prev_btn.opacity = self.next_btn.opacity = 1 if n > 1 else 0
        if refit or self.image.size == [100, 100]:
            self.fit(img)
        # otherwise keep the size and place: the paper hasn't moved between steps

    def fit(self, img=None):
        """Size the drawing to fill the screen's width (or height), centred, at scale 1."""
        if img is None:
            img = self.pages[self.i][1]
        h, w = img.shape[:2]
        W, H = Window.size
        s = min(W / w, H / h)
        self.scatter.scale = 1
        self.image.size = self.scatter.size = (w * s, h * s)
        self.scatter.pos = ((W - w * s) / 2, (H - h * s) / 2)

    def toggle_darker(self):
        self.darker = not self.darker
        self.darker_btn.active = self.darker
        prefs.set("trace_darker", self.darker)
        self.show(self.i)

    # ---------------------------------------------------------------- locking
    def lock(self):
        self.locked = True
        for w in (self.top_bar, self.bottom_bar, self.hint):
            w.opacity, w.disabled = 0, True
        self.scatter.do_translation = self.scatter.do_scale = False
        self.badge.opacity, self.badge.disabled = 1, False

    def unlock(self):
        self.locked = False
        for w in (self.top_bar, self.bottom_bar, self.hint):
            w.opacity, w.disabled = 1, False
        self.scatter.do_translation = self.scatter.do_scale = True
        self.badge.opacity, self.badge.disabled = 0, True

    def on_touch_down(self, touch):
        if self.locked and not self.badge.collide_point(*touch.pos):
            return True                          # paper and pencil change nothing
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.locked and touch.grab_current is not self.badge:
            return True
        return super().on_touch_move(touch)
