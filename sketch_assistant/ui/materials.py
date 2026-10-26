"""Object-mode material guide: chips + labelled example image + instructions."""
from pathlib import Path
from types import SimpleNamespace
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from ..data.materials import MATERIALS, material_markup
from . import theme
from .widgets import Card, segmented

IMAGES = Path(__file__).resolve().parent.parent / "assets" / "materials"


class MaterialGuide(Card):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, padding=dp(12), spacing=dp(10), **kw)
        self.bind(minimum_height=self.setter("height"))
        head = Label(text="[b][color=a66a00]Material guide[/color][/b]\nWhat is your object made of?", markup=True, size_hint_y=None,
                     height=dp(44), halign="left", valign="middle", color=theme.MUTED, font_size=sp(13))
        head.bind(size=lambda w, v: setattr(w, "text_size", v))
        bar, self.tabs = segmented({k: SimpleNamespace(short=m["tab"]) for k, m in MATERIALS.items()}, self.show, height=38, font=11)
        self.image = Image(fit_mode="contain", size_hint_y=None, height=dp(200))
        self.body = Label(markup=True, size_hint_y=None, halign="left", valign="top", color=theme.TEXT)
        self.body.bind(width=lambda w, v: setattr(w, "text_size", (v, None)), texture_size=lambda w, v: setattr(w, "height", v[1] + dp(8)))
        for w in (head, bar, self.image, self.body):
            self.add_widget(w)
        self.show(next(iter(MATERIALS)))

    def show(self, key):
        self.image.source = str(IMAGES / f"{key}.png")
        self.image.reload()
        self.body.text = material_markup(key)
        for k, b in self.tabs.items():
            b.active = k == key
