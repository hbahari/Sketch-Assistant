"""Reusable Kivy widgets: texture helper, face selector, rounded buttons, cards, header."""
import cv2
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse, InstructionGroup, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider

from . import theme


def to_texture(arr):
    rgb = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB if arr.ndim == 2 else cv2.COLOR_BGR2RGB)
    rgb = cv2.flip(rgb, 0)  # Kivy textures are bottom-up
    tex = Texture.create(size=(rgb.shape[1], rgb.shape[0]), colorfmt="rgb")
    tex.blit_buffer(rgb.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
    return tex


class FaceSelector(Image):
    """Shows a photo with boxes around detected faces; tapping a box selects it."""

    def __init__(self, on_select=None, **kw):
        super().__init__(fit_mode="contain", **kw)
        self.on_select, self.faces, self.selected, self._size = on_select, [], -1, (1, 1)
        self.bind(pos=self._redraw, size=self._redraw, texture_size=self._redraw)

    def set_photo(self, img_bgr, faces):
        self.faces, self.selected = faces, -1
        self._size = (img_bgr.shape[1], img_bgr.shape[0])
        self.texture = to_texture(img_bgr)
        self._redraw()

    def _scale_origin(self):
        nw, nh = self.norm_image_size
        return nw / self._size[0], self.x + (self.width - nw) / 2, self.y + (self.height - nh) / 2

    def _redraw(self, *_):
        self.canvas.after.clear()
        if not self.faces:
            return
        s, ox, oy = self._scale_origin()
        with self.canvas.after:
            for i, f in enumerate(self.faces):
                Color(*(theme.AMBER if i == self.selected else theme.WHITE))
                Line(rounded_rectangle=(ox + f.x * s, oy + (self._size[1] - f.y - f.h) * s, f.w * s, f.h * s, dp(8)), width=dp(2.2))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.faces:
            s, ox, oy = self._scale_origin()
            px, py = (touch.x - ox) / s, self._size[1] - (touch.y - oy) / s
            for i, f in enumerate(self.faces):
                if f.contains(px, py):
                    self.selected = i
                    self._redraw()
                    if self.on_select:
                        self.on_select(i, f)
                    return True
        return super().on_touch_down(touch)


class BoxSelector(Image):
    """A photo with a selection rectangle the user can redraw by dragging.

    Object mode needs this because segmentation cannot be told which object was meant.
    GrabCut is seeded from a rectangle; left to guess it seeds the middle of the frame,
    which is right for a single centred object and wrong for a still life of several --
    it returns some union of objects and background. Letting the user draw the rectangle
    turns an unanswerable question into a one-second gesture.

    The box is reported in image pixels, so the caller can crop to it the same way
    Portrait mode crops to a detected face.
    """
    HANDLE = 10          # dp, corner marks
    MIN_FRAC = 0.05      # a drag smaller than this is a tap, not a new box

    def __init__(self, on_select=None, **kw):
        super().__init__(fit_mode="contain", **kw)
        self.on_select, self._size = on_select, (1, 1)
        self.box = None                   # (x, y, w, h) in image pixels
        self._drag = None
        self.bind(pos=self._redraw, size=self._redraw, texture_size=self._redraw)

    def set_photo(self, img_bgr, default=0.85):
        """Show a photo and start from a box covering `default` of it, centred.

        The default is deliberately close to the whole frame: it keeps the result for
        photos that already worked unchanged, so dragging is purely an improvement rather
        than a new thing to get right.
        """
        h, w = img_bgr.shape[:2]
        self._size = (w, h)
        self.texture = to_texture(img_bgr)
        bw, bh = w * default, h * default
        self.box = ((w - bw) / 2, (h - bh) / 2, bw, bh)
        self._redraw()

    def _scale_origin(self):
        nw, nh = self.norm_image_size
        return nw / self._size[0], self.x + (self.width - nw) / 2, self.y + (self.height - nh) / 2

    def _to_image(self, sx, sy):
        s, ox, oy = self._scale_origin()
        return ((sx - ox) / s, self._size[1] - (sy - oy) / s)

    def _redraw(self, *_):
        self.canvas.after.clear()
        if not self.box:
            return
        s, ox, oy = self._scale_origin()
        x, y, w, h = self.box
        sx, sy = ox + x * s, oy + (self._size[1] - y - h) * s
        sw, sh = w * s, h * s
        hl = dp(self.HANDLE)
        with self.canvas.after:
            Color(0, 0, 0, 0.35)                       # dim what falls outside the box
            Rectangle(pos=(ox, oy), size=(self.norm_image_size[0], sy - oy))
            Rectangle(pos=(ox, sy + sh), size=(self.norm_image_size[0],
                                               oy + self.norm_image_size[1] - sy - sh))
            Rectangle(pos=(ox, sy), size=(sx - ox, sh))
            Rectangle(pos=(sx + sw, sy), size=(ox + self.norm_image_size[0] - sx - sw, sh))
            Color(*theme.AMBER)
            Line(rectangle=(sx, sy, sw, sh), width=dp(2))
            for cx, cy in ((sx, sy), (sx + sw, sy), (sx, sy + sh), (sx + sw, sy + sh)):
                Line(points=[cx - hl / 2, cy, cx + hl / 2, cy], width=dp(2))
                Line(points=[cx, cy - hl / 2, cx, cy + hl / 2], width=dp(2))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.texture is not None:
            self._drag = self._to_image(*touch.pos)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._drag is None:
            return super().on_touch_move(touch)
        self._set_from(self._drag, self._to_image(*touch.pos))
        return True

    def on_touch_up(self, touch):
        if self._drag is None:
            return super().on_touch_up(touch)
        start, end = self._drag, self._to_image(*touch.pos)
        self._drag = None
        w, h = self._size
        if abs(end[0] - start[0]) < w * self.MIN_FRAC or abs(end[1] - start[1]) < h * self.MIN_FRAC:
            self._redraw()                 # a tap: leave the box where it was
            return True
        self._set_from(start, end)
        if self.on_select:
            self.on_select(self.box)
        return True

    def _set_from(self, a, b):
        w, h = self._size
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        x0, y0 = max(0.0, x0), max(0.0, y0)
        x1, y1 = min(float(w), x1), min(float(h), y1)
        self.box = (x0, y0, max(1.0, x1 - x0), max(1.0, y1 - y0))
        self._redraw()


_grad = {}


def gradient_texture(c1=None, c2=None):
    """Horizontal gradient texture (cached) from c1 to c2, default indigo -> violet."""
    c1, c2 = c1 or theme.ACCENT, c2 or theme.ACCENT_2
    key = (tuple(c1), tuple(c2))
    if key not in _grad:
        n = 64
        buf = bytearray()
        for i in range(n):
            t = i / (n - 1)
            buf += bytes(int(255 * (c1[k] * (1 - t) + c2[k] * t)) for k in range(3)) + b"\xff"
        tex = Texture.create(size=(n, 1), colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = tex.min_filter = "linear"
        _grad[key] = tex
    return _grad[key]


def _tile_texture(source):
    """Load a style-tile thumbnail, or None if it is missing or unreadable.

    A missing thumbnail must not take the app down: the tiles are regenerated from
    whatever reference photos are to hand (scripts/make_examples.py), so a newly added
    style can legitimately have none yet. Without a texture the tile falls back to a
    plain labelled button, which still works.
    """
    if not source:
        return None
    try:
        from pathlib import Path
        if not Path(source).exists():
            return None
        return CoreImage(source).texture
    except Exception:
        return None


def _shadowed(widget, color, radii):
    """Soft fake drop-shadow + filled rounded rect."""
    Color(0, 0, 0, 0.07); RoundedRectangle(pos=(widget.x, widget.y - dp(2)), size=widget.size, radius=radii)
    Color(*color); RoundedRectangle(pos=widget.pos, size=widget.size, radius=radii)


class RoundButton(ButtonBehavior, Label):
    """Rounded button. `radii` = [top-left, top-right, bottom-right, bottom-left] so segmented
    controls can round only their outer corners. With `source` it becomes an image tile card."""
    active = BooleanProperty(False)

    def __init__(self, radii=None, source=None, fit=False, **kw):
        self.fill = kw.pop("fill", None)   # solid custom colour (e.g. the amber "New photo" button)
        kw.setdefault("color", theme.TEXT); kw.setdefault("disabled_color", theme.MUTED)
        kw.setdefault("halign", "center"); kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.radii = radii or [theme.radius()] * 4
        self.tex = _tile_texture(source)
        # `fit` buttons size themselves to their label and must NOT have text_size chased
        # to the widget size: that binding plus a width driven by texture_size is a loop
        # (width -> size -> text_size -> texture_size -> width) that hangs the clock.
        if not fit:
            self.bind(size=lambda *_: setattr(self, "text_size", self.size))
        self.bind(pos=self._draw, size=self._draw, state=self._draw, active=self._draw, disabled=self._draw)
        self._draw()

    def _draw(self, *_):
        self.opacity = 0.6 if self.disabled else 1
        self.canvas.before.clear(); self.canvas.after.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if self.tex:  # image tile: photo on top, label underneath
            p = dp(6); side = min(w - 2 * p, h - dp(30) - p)
            with self.canvas.before:
                _shadowed(self, theme.SURFACE, self.radii)
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=(x + (w - side) / 2, y + h - p - side), size=(side, side), radius=[dp(12)] * 4, texture=self.tex)
            if self.active:
                with self.canvas.after:
                    Color(*theme.ACCENT); Line(rounded_rectangle=(x, y, w, h, self.radii[0]), width=dp(2.5))
            self.color = theme.ACCENT_DARK if self.active else theme.TEXT
        else:
            base = theme.SURFACE_HI if self.state == "down" else theme.SURFACE
            with self.canvas.before:
                if self.fill:
                    _shadowed(self, self.fill, self.radii)
                elif self.active:
                    Color(*theme.ACCENT[:3], 0.28)  # soft coloured glow under gradient buttons
                    RoundedRectangle(pos=(x, y - dp(3)), size=self.size, radius=self.radii)
                    Color(1, 1, 1, 1)
                    RoundedRectangle(pos=self.pos, size=self.size, radius=self.radii, texture=gradient_texture())
                else:
                    _shadowed(self, base, self.radii)
            self.color = theme.WHITE if (self.active and not self.fill) else theme.TEXT


class UploadCard(RoundButton):
    """Big white card with a dashed teal border and a '+' badge (scales with the card height)."""

    def __init__(self, **kw):
        kw.setdefault("valign", "bottom"); kw.setdefault("padding", (0, dp(26)))
        super().__init__(**kw)

    def _draw(self, *_):
        super()._draw()
        x, y, w, h = self.x, self.y, self.width, self.height
        rad = min(dp(32), h * 0.13)
        cx, cy = x + w / 2, y + h * 0.62
        with self.canvas.after:
            Color(*theme.ACCENT[:3], 0.55)
            Line(rounded_rectangle=(x + dp(8), y + dp(8), w - dp(16), h - dp(16), dp(20)), dash_length=dp(6), dash_offset=dp(5), width=dp(1.5))
            Color(*theme.ACCENT); Ellipse(pos=(cx - rad, cy - rad), size=(2 * rad, 2 * rad))
            Color(1, 1, 1, 1)
            Rectangle(pos=(cx - rad * 0.45, cy - dp(2)), size=(rad * 0.9, dp(4)))
            Rectangle(pos=(cx - dp(2), cy - rad * 0.45), size=(dp(4), rad * 0.9))


class Card(BoxLayout):
    """White rounded container with a soft shadow."""

    def __init__(self, **kw):
        kw.setdefault("padding", dp(8))
        super().__init__(**kw)
        self.bind(pos=self._d, size=self._d)
        self._d()

    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            _shadowed(self, theme.SURFACE, [dp(20)] * 4)


class LogoBar(BoxLayout):
    """Slim top bar with the app logo (replaces the old text banner)."""

    def __init__(self, **kw):
        from pathlib import Path
        super().__init__(size_hint_y=None, height=dp(62), padding=(dp(18), dp(10), dp(18), 0), **kw)
        logo = Path(__file__).resolve().parent.parent / "assets" / "brand" / "logo.png"
        self.add_widget(Image(source=str(logo), fit_mode="contain", size_hint_x=None, width=dp(215), mipmap=True))
        self.add_widget(Label())  # spacer pushes the logo to the left


class TitleBar(BoxLayout):
    """Page title with a round back button (chevron)."""

    def __init__(self, title, on_back, **kw):
        super().__init__(size_hint_y=None, height=dp(62), padding=(dp(14), dp(10), dp(14), dp(2)), spacing=dp(12), **kw)
        self.back = BackButton(on_release=lambda *_: on_back())
        lb = Label(text=title, bold=True, font_size=sp(20), color=theme.TEXT, halign="left", valign="middle")
        lb.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.add_widget(self.back); self.add_widget(lb)


class BackButton(ButtonBehavior, BoxLayout):
    """40dp round white button with a chevron-left icon."""

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), size=(dp(42), dp(42)), **kw)
        self.bind(pos=self._d, size=self._d, state=self._d)
        self._d()

    def _d(self, *_):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        with self.canvas.before:
            Color(0, 0, 0, 0.07); Ellipse(pos=(x, y - dp(2)), size=(w, h))
            Color(*(theme.SURFACE_HI if self.state == "down" else theme.SURFACE)); Ellipse(pos=self.pos, size=self.size)
            Color(*theme.TEXT); Line(points=[x + w * .56, y + h * .30, x + w * .40, y + h * .50, x + w * .56, y + h * .70], width=dp(2), cap="round", joint="round")


class DetailSlider(BoxLayout):
    """'Less detail <-> More detail' tuner. Calls on_commit(value) when the finger is lifted (so we re-render once)."""

    def __init__(self, on_commit, **kw):
        super().__init__(size_hint_y=None, height=dp(34), spacing=dp(8), **kw)
        self.on_commit, self._down = on_commit, False
        lab = lambda t: Label(text=t, size_hint_x=None, width=dp(78), color=theme.MUTED, font_size=sp(11))
        self.slider = Slider(min=0, max=1, value=0.5, step=0.05, value_track=True, value_track_color=theme.AMBER,
                             value_track_width=dp(4), background_width=dp(4), cursor_size=(dp(22), dp(22)), disabled=True)
        for w in (lab("Less detail"), self.slider, lab("More detail")):
            self.add_widget(w)
        self.slider.bind(on_touch_down=self._dn, on_touch_up=self._up)

    def _dn(self, s, t):
        self._down = s.collide_point(*t.pos)

    def _up(self, s, t):
        if self._down:
            self._down = False
            self.on_commit(s.value)

    def set_value(self, v, enabled=True):
        self.slider.value, self.slider.disabled = v, not enabled
        self.opacity = 1 if enabled else 0.5


_fade = {}


def fade_texture(color, reverse=False):
    """Horizontal gradient from `color` to fully transparent, for softening a scroll edge."""
    key = (tuple(color), reverse)
    if key not in _fade:
        n = 32
        buf = bytearray()
        for i in range(n):
            t = i / (n - 1)
            a = 1 - t if not reverse else t
            buf += bytes(int(255 * color[k]) for k in range(3)) + bytes([int(255 * a)])
        tex = Texture.create(size=(n, 1), colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = tex.min_filter = "linear"
        _fade[key] = tex
    return _fade[key]


class ModeBar(ScrollView):
    """The subject bar: separate rounded pills that drag-scroll sideways, with no scrollbar.

    `bar_width=0` hides the scrollbar. The timeout is raised well above Kivy's 55 ms
    default so that pressing a pill and *then* dragging scrolls the bar instead of being
    read as a tap -- which is how the gesture actually gets made with a thumb. Kivy still
    cancels the pill's press once the finger passes `scroll_distance`, so a tap selects
    and a drag scrolls.

    A fade at each end stands in for the missing scrollbar: it only appears on the side
    that has more content, so there is still a cue that the bar continues off-screen.
    The fades live in an InstructionGroup of their own. A ScrollView is a StencilView, and
    Kivy keeps the matching StencilUnUse/StencilPop in `canvas.after`; clearing that canvas
    to redraw the fades deletes them, the stencil clip is never popped, and every widget
    drawn after this one in the frame is clipped away -- a blank page below the bar.
    """
    PILL_H, GAP, SIDE = 46, 10, 14          # dp
    FADE = 22                                # dp of gradient at each end

    def __init__(self, modes, on_select, **kw):
        super().__init__(size_hint_y=None, height=dp(self.PILL_H + 6), do_scroll_y=False,
                         bar_width=0, scroll_type=["content"], scroll_timeout=250,
                         scroll_distance=dp(14), **kw)
        self.row = BoxLayout(size_hint=(None, 1), spacing=dp(self.GAP),
                             padding=(dp(self.SIDE), 0, dp(self.SIDE), 0))
        self.row.bind(minimum_width=self.row.setter("width"))
        self.btns = {}
        for key, label in modes:
            b = RoundButton(text=label, bold=True, font_size=sp(14), fit=True,
                            size_hint=(None, None), height=dp(self.PILL_H),
                            radii=[dp(self.PILL_H / 2)] * 4,
                            on_release=lambda _b, k=key: on_select(k))
            # Width follows the label, measured once: nothing is ever truncated, and the
            # bar overflows -- and so becomes scrollable -- exactly when the labels stop
            # fitting. Mode labels never change, so this needs no binding.
            b.texture_update()
            b.width = max(dp(96), b.texture_size[0] + dp(34))
            self.btns[key] = b
            self.row.add_widget(b)
        self.add_widget(self.row)
        self._fades = InstructionGroup()      # appended once; never clear canvas.after
        self.canvas.after.add(self._fades)
        self.bind(pos=self._edges, size=self._edges, scroll_x=self._edges)
        self.row.bind(width=self._edges)
        self._edges()

    def select(self, key):
        for k, b in self.btns.items():
            b.active = k == key
        if key in self.btns:
            self.scroll_to(self.btns[key], padding=dp(24), animate=True)

    def _edges(self, *_):
        """Draw the end fades, each only when there is content hidden on that side.

        Only `self._fades` is ever emptied. Clearing `canvas.after` instead would take
        the ScrollView's own stencil instructions with it (see the class docstring).
        """
        self._fades.clear()
        if self.row.width - self.width <= 1:          # everything fits; nothing to fade
            return
        f = dp(self.FADE)
        if self.scroll_x > 0.01:
            self._fades.add(Color(1, 1, 1, 1))
            self._fades.add(Rectangle(pos=(self.x, self.y), size=(f, self.height),
                                      texture=fade_texture(theme.BG)))
        if self.scroll_x < 0.99:
            self._fades.add(Color(1, 1, 1, 1))
            self._fades.add(Rectangle(pos=(self.right - f, self.y), size=(f, self.height),
                                      texture=fade_texture(theme.BG, reverse=True)))


def segmented(styles, on_select, height=44, font=12, padding=(0, 0)):
    """Attached, rounded-ends tab bar (like the mode bar). Returns (bar, {key: button})."""
    bar = BoxLayout(size_hint_y=None, height=dp(height), spacing=0, padding=padding)
    r, n, btns = theme.radius(), len(styles), {}
    for i, (key, st) in enumerate(styles.items()):
        first, last = i == 0, i == n - 1
        btns[key] = RoundButton(text=st.short, bold=True, font_size=sp(font),
                                radii=[r if first else 0, r if last else 0, r if last else 0, r if first else 0],
                                on_release=lambda _b, k=key: on_select(k))
        bar.add_widget(btns[key])
    return bar, btns
