"""The first-launch tour: the main page dimmed, one control at a time lit up, with a card
saying what it's for.

It runs over the real page, so it points at real controls in their real places, whatever
the screen size. It shows once, on the first launch (prefs "tour_done"), and again from
Settings -> "Show the tour again". Skip, Done, or the back button all end it.
"""
from kivy.animation import Animation
from kivy.core.window import Window
import math

from kivy.graphics import Color, Line, Mesh, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from . import theme
from .widgets import RoundButton

# (what to light up on the main page, title, text). None = no spotlight, a centred card.
STEPS = [
    (None, "Welcome to Sketch Assistant",
     "Turn any photo into a drawing lesson. Here's how it works, in five quick steps."),
    ("mode_bar", "Choose what to draw",
     "Portraits, eyes, noses, hands, posture, cartoons or objects. Each has its own guides and lessons."),
    ("box", "Add a photo",
     "Take one, or pick one from your gallery. The app finds the face, hand or person for you: "
     "tap it to begin."),
    ("style_holder", "Pick a style",
     "From simple line art to realistic shading. Your sketch appears next to the photo."),
    ("guide_btn", "Then draw it step by step",
     "The guide adds proportion lines you can measure. Then the lesson tells you which pencil "
     "to pick up and what to draw next."),
    ("gear", "Settings",
     "Keep the screen on while you draw, send us feedback, or watch this tour again."),
]
PAD = dp(6)          # spotlight margin round the control
DIM = (0.05, 0.05, 0.06, 0.66)


def target_box(home, name):
    """(x, y, w, h) in window coordinates of a main-page control, padded; None for no target."""
    if name is None:
        return None
    w = home.logo_bar.gear if name == "gear" else getattr(home, name)
    x0, y0 = w.to_window(w.x, w.y)
    x1, y1 = w.to_window(w.x + w.width, w.y + w.height)
    x0, y0 = max(0, x0 - PAD), max(0, y0 - PAD)
    x1, y1 = min(Window.width, x1 + PAD), min(Window.height, y1 + PAD)
    return x0, y0, x1 - x0, y1 - y0


def _corner(sx, sy, r, ox, oy, n=10):
    """Fill the part of the r x r square at (sx, sy) that lies outside the circle of radius r
    centred on (ox, oy): one rounded corner of the spotlight's surround."""
    # the square's corner farthest from the circle's centre
    fx = sx if ox > sx else sx + r
    fy = sy if oy > sy else sy + r
    a0 = math.atan2(fy - oy, fx - ox)
    pts = [(ox + r * math.cos(a0 + math.pi / 4 * (k / n - 0.5) * 2), oy + r * math.sin(a0 + math.pi / 4 * (k / n - 0.5) * 2))
           for k in range(n + 1)]
    verts = [fx, fy, 0, 0]
    for px, py in pts:
        verts += [px, py, 0, 0]
    Mesh(vertices=verts, indices=list(range(len(pts) + 1)), mode="triangle_fan")


class TourCard(BoxLayout):
    """White card: "2 of 6", title, text, then Skip / Back / Next."""

    def __init__(self, tour, **kw):
        super().__init__(orientation="vertical", size_hint=(None, None), spacing=dp(8),
                         padding=(dp(20), dp(16), dp(20), dp(14)), **kw)
        self.tour = tour
        self.count = self._label(12, theme.ACCENT_DARK, bold=True)
        self.title = self._label(19, theme.TEXT, bold=True)
        self.body = self._label(14, theme.MUTED)
        for lb in (self.count, self.title, self.body):
            self.add_widget(lb)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.skip = RoundButton(text="Skip", font_size=sp(14), fill=theme.SURFACE, size_hint_x=None, width=dp(76),
                                radii=[dp(23)] * 4, on_release=lambda *_: tour.finish())
        self.back = RoundButton(text="Back", font_size=sp(14), size_hint_x=None, width=dp(80),
                                radii=[dp(23)] * 4, on_release=lambda *_: tour.go(tour.i - 1))
        self.next = RoundButton(text="Next", bold=True, font_size=sp(14), active=True, radii=[dp(23)] * 4,
                                on_release=lambda *_: tour.go(tour.i + 1))
        row.add_widget(self.skip); row.add_widget(Widget()); row.add_widget(self.back); row.add_widget(self.next)
        self.next.size_hint_x, self.next.width = None, dp(104)
        self.row = row
        self.add_widget(row)
        self.bind(minimum_height=self.setter("height"), pos=self._bg, size=self._bg)

    def _label(self, size, color, bold=False):
        lb = Label(font_size=sp(size), color=color, bold=bold, size_hint_y=None, halign="left", valign="top")
        lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                texture_size=lambda w, v: setattr(w, "height", v[1]))
        return lb

    def _bg(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.18)
            RoundedRectangle(pos=(self.x, self.y - dp(3)), size=self.size, radius=[dp(22)])
            Color(*theme.SURFACE)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(22)])

    def fill(self, i, n, title, body):
        self.count.text = f"{i + 1} of {n}"
        self.title.text, self.body.text = title, body
        # nothing to go back to on the first card: take the button out of the row
        if i == 0 and self.back.parent is not None:
            self.row.remove_widget(self.back)
        elif i > 0 and self.back.parent is None:
            self.row.add_widget(self.back, index=1)     # children run right to left: before Next
        self.next.text = "Show me" if i == 0 else ("Start drawing" if i == n - 1 else "Next")
        self.next.width = dp(140) if i == n - 1 else dp(104)


class Tour(FloatLayout):
    """Lies over the whole window and takes every touch, so the page can't be used mid-tour."""

    def __init__(self, home, on_done=None, **kw):
        super().__init__(**kw)
        self.home, self.on_done, self.i, self.box = home, on_done, 0, None
        self.card = TourCard(self)
        self.add_widget(self.card)
        self.size = Window.size
        Window.bind(size=self._resize, on_keyboard=self._key)
        self.opacity = 0

    def start(self):
        Window.add_widget(self)
        self.go(0)
        Animation(opacity=1, d=0.25).start(self)
        return self

    # ---------------------------------------------------------------- moving through
    def go(self, i):
        if i >= len(STEPS):
            self.finish()
            return
        self.i = max(0, i)
        name, title, body = STEPS[self.i]
        self.box = target_box(self.home, name)
        self.card.fill(self.i, len(STEPS), title, body)
        self._layout()

    def finish(self):
        from .. import prefs
        prefs.set("tour_done", True)
        Window.unbind(size=self._resize, on_keyboard=self._key)
        if self.parent is not None:
            self.parent.remove_widget(self)
        if self.on_done:
            self.on_done()

    def _key(self, _w, key, *_):
        if key == 27:                       # back button: leave the tour, not the app
            self.finish()
            return True
        return False

    def _resize(self, *_):
        self.size = Window.size
        self.box = target_box(self.home, STEPS[self.i][0])
        self._layout()

    # ---------------------------------------------------------------- drawing
    def _layout(self, *_):
        W, H = Window.size
        c = self.card
        c.width = min(W - 2 * dp(18), dp(380))
        c.do_layout()
        x = (W - c.width) / 2
        if self.box is None:
            y = (H - c.height) / 2
        else:
            bx, by, bw, bh = self.box
            gap = dp(14)
            if by - gap - c.height >= dp(12):            # room below the spotlight
                y = by - gap - c.height
            else:                                       # otherwise above it
                y = min(by + bh + gap, H - c.height - dp(12))
        c.pos = (x, y)
        self._draw()
        # the card's height settles a frame later once the labels have wrapped
        c.unbind(height=self._relayout)
        c.bind(height=self._relayout)

    def _relayout(self, *_):
        self.card.unbind(height=self._relayout)
        self._layout()

    def _draw(self):
        W, H = Window.size
        self.canvas.before.clear()
        with self.canvas.before:
            if self.box is None:
                Color(*DIM)
                Rectangle(pos=(0, 0), size=(W, H))
                return
            x, y, w, h = self.box
            r = min(dp(20), h / 2)
            # The dimming everywhere except a rounded hole. Drawn as four bands round the
            # hole plus its four corners, not with a stencil: Kivy's stencil test came out
            # inverted (only the hole got dimmed), and plain shapes behave the same on
            # every phone's GPU.
            Color(*DIM)
            Rectangle(pos=(0, 0), size=(W, y))                       # below
            Rectangle(pos=(0, y + h), size=(W, H - y - h))           # above
            Rectangle(pos=(0, y), size=(x, h))                       # left
            Rectangle(pos=(x + w, y), size=(W - x - w, h))           # right
            for cx, cy, a0 in ((x, y, 180), (x + w, y, 90), (x + w, y + h, 0), (x, y + h, 270)):
                # each corner: the square r x r minus the quarter circle inside it
                sx = cx if cx == x else cx - r
                sy = cy if cy == y else cy - r
                ox = sx + r if cx == x else sx                       # quarter circle's centre
                oy = sy + r if cy == y else sy
                _corner(sx, sy, r, ox, oy)
            Color(*theme.AMBER)
            Line(rounded_rectangle=(x, y, w, h, r), width=dp(2))

    def on_touch_down(self, touch):
        super().on_touch_down(touch)
        return True                                     # nothing reaches the page underneath

    def on_touch_move(self, touch):
        super().on_touch_move(touch)
        return True

    def on_touch_up(self, touch):
        super().on_touch_up(touch)
        return True
