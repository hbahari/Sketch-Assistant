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
                Color(*((1, 0.75, 0.1, 1) if i == self.selected else (0.1, 0.9, 0.8, 1)))
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


def _shadowed(widget, color, radii):
    """Soft fake drop-shadow + filled rounded rect."""
    Color(0, 0, 0, 0.07); RoundedRectangle(pos=(widget.x, widget.y - dp(2)), size=widget.size, radius=radii)
    Color(*color); RoundedRectangle(pos=widget.pos, size=widget.size, radius=radii)


class RoundButton(ButtonBehavior, Label):
    """Rounded button. `radii` = [top-left, top-right, bottom-right, bottom-left] so segmented
    controls can round only their outer corners. With `source` it becomes an image tile card."""
    active = BooleanProperty(False)

    def __init__(self, radii=None, source=None, **kw):
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
            base = theme.ACCENT if self.active else (theme.SURFACE_HI if self.state == "down" else theme.SURFACE)
            with self.canvas.before:
                if self.active:
                    Color(*base); RoundedRectangle(pos=self.pos, size=self.size, radius=self.radii)
                else:
                    _shadowed(self, base, self.radii)
            self.color = theme.WHITE if self.active else theme.TEXT


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


class Header(BoxLayout):
    """Teal banner with rounded bottom corners, title and tagline."""

    def __init__(self, title, subtitle, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(88), padding=(dp(20), dp(14)), spacing=dp(2), **kw)
        for text, size, col, bold in ((title, sp(22), theme.WHITE, True), (subtitle, sp(13), (1, 1, 1, 0.8), False)):
            lb = Label(text=text, font_size=size, color=col, bold=bold, halign="left", valign="middle")
            lb.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            self.add_widget(lb)
        self.bind(pos=self._d, size=self._d)
        self._d()

    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*theme.ACCENT)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[0, 0, dp(28), dp(28)])
