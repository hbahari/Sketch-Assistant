"""Reusable Kivy widgets: texture helper, face selector, rounded buttons, cards, header."""
import cv2
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
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


def _shadowed(widget, color, radii):
    """Soft fake drop-shadow + filled rounded rect."""
    Color(0, 0, 0, 0.07); RoundedRectangle(pos=(widget.x, widget.y - dp(2)), size=widget.size, radius=radii)
    Color(*color); RoundedRectangle(pos=widget.pos, size=widget.size, radius=radii)


class RoundButton(ButtonBehavior, Label):
    """Rounded button. `radii` = [top-left, top-right, bottom-right, bottom-left] so segmented
    controls can round only their outer corners. With `source` it becomes an image tile card."""
    active = BooleanProperty(False)

    def __init__(self, radii=None, source=None, **kw):
        self.fill = kw.pop("fill", None)   # solid custom colour (e.g. the amber "New photo" button)
        kw.setdefault("color", theme.TEXT); kw.setdefault("disabled_color", theme.MUTED)
        kw.setdefault("halign", "center"); kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.radii = radii or [theme.radius()] * 4
        self.tex = CoreImage(source).texture if source else None
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
